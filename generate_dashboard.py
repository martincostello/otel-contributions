#!/usr/bin/env python3
"""
Grafana Dashboard Generator

Generates grafana/dashboards/github-contributions.json from the template,
substituting organization-specific columns based on the provided orgs.
Org display names are fetched from the GitHub API.
"""

import json
import os

import requests
from github_utils import github_get

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "grafana", "dashboards", "github-contributions.template.json"
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "grafana", "dashboards", "github-contributions.json"
)

DEFAULT_ORGS = ["open-telemetry", "prometheus", "grafana"]


def fetch_org_display_name(org, headers):
    """Fetch the display name of a GitHub org via the API. Falls back to the org slug."""
    try:
        response = github_get(
            f"https://api.github.com/orgs/{org}",
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            name = response.json().get("name")
            if name:
                return name
    except (requests.RequestException, ValueError):
        pass
    return org


def org_key(org):
    """Convert org slug to CSV column key (e.g. 'open-telemetry' -> 'open_telemetry')."""
    return org.replace("-", "_")


def build_org_columns(orgs, metric_prefix, headers):
    """Build Grafana column definitions for the given orgs and metric prefix."""
    columns = []
    for org in orgs:
        display_name = fetch_org_display_name(org, headers)
        columns.append({
            "selector": f"{metric_prefix}_{org_key(org)}",
            "text": display_name,
            "type": "number",
        })
    return columns


def expand_placeholders(columns, orgs, headers):
    """Replace placeholder column entries with org-specific column definitions."""
    result = []
    for col in columns:
        if "_placeholder" in col:
            metric_prefix = col["_placeholder"]
            result.extend(build_org_columns(orgs, metric_prefix, headers))
        else:
            result.append(col)
    return result


def generate_dashboard(orgs, token=None, template_path=TEMPLATE_PATH, output_path=OUTPUT_PATH):
    """
    Generate dashboard JSON from template, substituting org-specific columns.

    Args:
        orgs: List of GitHub organization slugs.
        token: GitHub API token (uses GITHUB_TOKEN env var if not provided).
        template_path: Path to the template JSON file.
        output_path: Path to write the generated dashboard JSON.

    Returns:
        Path to the generated dashboard file.
    """
    if token is None:
        token = os.environ.get("GITHUB_TOKEN")

    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    with open(template_path) as f:
        dashboard = json.load(f)

    for panel in dashboard.get("panels", []):
        for target in panel.get("targets", []):
            if "columns" in target and any("_placeholder" in col for col in target["columns"]):
                target["columns"] = expand_placeholders(target["columns"], orgs, headers)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dashboard, f, indent=2)
        f.write("\n")

    print(f"Dashboard generated: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Grafana dashboard from template with dynamic org columns"
    )
    parser.add_argument(
        "--orgs",
        nargs="+",
        default=DEFAULT_ORGS,
        help=f"GitHub organizations (default: {' '.join(DEFAULT_ORGS)})",
    )
    args = parser.parse_args()

    generate_dashboard(args.orgs)

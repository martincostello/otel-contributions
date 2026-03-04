#!/usr/bin/env python3
"""
GitHub Contributions Performance Review Runner

This script runs the analysis and starts the Grafana dashboard.
"""

import os
import sys
import subprocess
from pathlib import Path
from generate_dashboard import generate_dashboard, DEFAULT_ORGS


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color


def print_colored(message, color):
    print(f"{color}{message}{Colors.NC}")


def print_header():
    print_colored("═" * 67, Colors.BLUE)
    print_colored("   GitHub Contributions Performance Review", Colors.BLUE)
    print_colored("═" * 67, Colors.BLUE)
    print()


def check_github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print_colored("Error: GITHUB_TOKEN environment variable not set", Colors.RED)
        print()
        print("Please set your GitHub token:")
        print('  export GITHUB_TOKEN="your_github_token_here"')
        print()
        sys.exit(1)
    return token


def check_docker():
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_analysis(args):
    print_colored("📊 Running contribution analysis...", Colors.BLUE)
    print()

    try:
        subprocess.run(
            [sys.executable, 'performance-review.py'] + args,
            check=True
        )

        print()
        print_colored("✅ Analysis complete!", Colors.GREEN)
        print()
        return True
    except subprocess.CalledProcessError as e:
        print()
        print_colored(f"❌ Analysis failed with exit code {e.returncode}", Colors.RED)
        return False
    except Exception as e:
        print()
        print_colored(f"❌ Analysis failed: {e}", Colors.RED)
        return False


def extract_orgs(args):
    """Extract --orgs values from the argument list, returning defaults if not present."""
    try:
        idx = args.index("--orgs")
    except ValueError:
        return DEFAULT_ORGS

    orgs = []
    for arg in args[idx + 1:]:
        if arg.startswith("--"):
            break
        orgs.append(arg)
    return orgs if orgs else DEFAULT_ORGS


def generate_grafana_dashboard(orgs):
    """Generate the Grafana dashboard JSON for the GitHub organizations that were searched."""
    print_colored("📋 Generating Grafana dashboard...", Colors.BLUE)
    try:
        generate_dashboard(orgs)
        print_colored("✅ Dashboard generated!", Colors.GREEN)
        print()
        return True
    except Exception as e:
        print_colored(f"❌ Dashboard generation failed: {e}", Colors.RED)
        return False


def start_dashboard():
    """Start Grafana dashboard with Docker Compose"""
    print_colored("🚀 Starting Grafana dashboard...", Colors.BLUE)

    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            capture_output=True,
            text=True,
            check=True
        )

        print()
        print_colored("═" * 67, Colors.GREEN)
        print_colored("   Dashboard Ready!", Colors.GREEN)
        print_colored("═" * 67, Colors.GREEN)
        print()
        print(f"📊 Dashboard URL: {Colors.BLUE}http://localhost:3000{Colors.NC}")
        print(f"👤 Username:      {Colors.BLUE}admin{Colors.NC}")
        print(f"🔑 Password:      {Colors.BLUE}admin{Colors.NC}")
        print()
        print_colored("Note: It may take 10-20 seconds for Grafana to fully start.", Colors.YELLOW)
        print()
        print("To stop the dashboard:")
        print("  docker-compose down")
        print()
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"Failed to start dashboard: {e}", Colors.RED)
        if e.stderr:
            print(e.stderr)
        return False
    except FileNotFoundError:
        print_colored("Error: docker-compose command not found", Colors.RED)
        return False


def main():
    """Main entry point"""
    print_header()

    # Check prerequisites
    check_github_token()

    docker_available = check_docker()
    if not docker_available:
        print_colored(
            "Warning: docker is not installed. Dashboard won't start automatically.",
            Colors.YELLOW
        )
        print()

    # Run analysis with all command line arguments
    args = sys.argv[1:]
    if not run_analysis(args):
        sys.exit(1)

    # Generate Grafana dashboard for the configured organizations
    orgs = extract_orgs(args)
    if not generate_grafana_dashboard(orgs):
        sys.exit(1)

    # Start dashboard if Docker is available
    if docker_available:
        start_dashboard()
    else:
        print_colored(
            "Docker not available. Please install Docker to use the dashboard.",
            Colors.YELLOW
        )


if __name__ == '__main__':
    main()
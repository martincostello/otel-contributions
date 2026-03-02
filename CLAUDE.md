# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python project for analyzing GitHub contributions across multiple organizations. It uses the GitHub API to fetch commit, pull request, review, and comment data for a specific user across repositories in the `open-telemetry`, `prometheus`, and `grafana` organizations.

## Running the Scripts

This project uses `uv` for package management and dependency handling.

First-time setup:
```bash
# Install uv if you haven't already (https://docs.astral.sh/uv/)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up the GitHub token
export GITHUB_TOKEN="your_github_token_here"

# uv will automatically install dependencies on first run
```

Run the main contribution summary script:
```bash
uv run python main.py
```

Run the detailed PR listing script:
```bash
uv run python contributions-detail.py
```

Run the comprehensive performance review script (with CLI):
```bash
uv run python performance-review.py --start-date 2025-07-01 --end-date 2026-01-31
```

Run everything with the wrapper script (includes Grafana dashboard):
```bash
uv run python run_analysis.py --start-date 2025-07-01 --end-date 2026-01-31
```

Access the Grafana dashboard:
- URL: http://localhost:3000
- Username: admin
- Password: admin

## Dependencies

Dependencies are managed by `uv` and defined in `pyproject.toml`. The project requires:
- Python 3.8+
- requests library (automatically installed by uv)

## Architecture

### main.py
Main script that calculates contribution statistics (commits, additions, deletions) across all OpenTelemetry repositories for the configured user. It:
- Fetches all repositories from the `open-telemetry` organization
- For each repository, fetches all commits authored by the specified user
- Fetches detailed commit stats (additions/deletions) for each commit
- Outputs summary statistics organized by repository

### contributions-detail.py
Similar to main.py but focused on listing pull requests instead of commit statistics. It:
- Fetches all repositories from the `open-telemetry` organization (sorted by creation date)
- For each repository where the user has commits, fetches all closed PRs
- Filters PRs to only those authored by the specified user
- Outputs PR titles and URLs in markdown format, organized by repository

### performance-review.py
Enhanced performance review script with CLI arguments, intelligent caching, and timeseries data generation. It uses the GitHub Search API to collect comprehensive contribution data.

**Key Features:**
- **CLI Arguments**: Fully configurable via command line (username, date range, organizations)
- **Smart Caching**: API responses cached to `review_cache/` to avoid redundant calls
- **Multiple Output Formats**:
  - Detailed JSON report (`output/performance_review_TIMESTAMP.json`)
  - Daily timeseries CSV (`output/timeseries_daily.csv`)
  - Event stream JSON (`output/events.json`)
  - Summary statistics (`output/summary.json`)

**Data Collected:**
- **Merged PRs**: All pull requests authored by the user that were merged
- **PRs Reviewed**: Pull requests reviewed with state breakdown (APPROVED, CHANGES_REQUESTED, COMMENTED)
  - Bot vs human author detection
  - Separate counts for human and bot PRs reviewed
- **PR Comments**: Review comments made on pull requests
- **Issue Comments**: Comments made on issues
- **Repository Breakdown**: Contributions organized by repository
- **Daily Aggregates**: Activity aggregated by day for timeseries visualization
- **Bot Detection**: Automatically identifies bot contributors (dependabot, renovate, github-actions, etc.)

**Usage:**
```bash
python performance-review.py \
  --start-date 2025-07-01 \
  --end-date 2026-01-31 \
  --orgs open-telemetry prometheus grafana
```

The script searches across specified organizations and produces formatted console output plus multiple data files optimized for different use cases (reporting, visualization, analysis).

### run_analysis.py
Python wrapper script that provides a seamless experience for running analysis and starting the dashboard. It:
- Validates environment (GITHUB_TOKEN, Python, Docker)
- Runs the performance-review.py script with provided arguments
- Automatically starts Grafana dashboard with Docker Compose
- Displays connection information and next steps
- Cross-platform compatible (replaces the old bash-based run-analysis.sh)

### docker-compose.yml
Container orchestration for the visualization stack:
- **file-server**: Python HTTP server serving data files from `output/` directory
- **grafana**: Grafana instance with Infinity plugin pre-installed and provisioned

### grafana/
Directory containing Grafana configuration and dashboards:
- **provisioning/datasources/**: Infinity datasource configuration
- **provisioning/dashboards/**: Dashboard provisioning config
- **dashboards/github-contributions.json**: Pre-built performance review dashboard

**Dashboard Panels:**
- Summary statistics (stat panels):
  - Total Merged PRs
  - Total Reviews
  - Total Comments (PR + Issue)
  - Unique Contributors Reviewed
- Bot detection metrics (stat panels):
  - Reviews of Human PRs
  - Reviews of Bot PRs
  - Human Contributors Reviewed
  - Bot Contributors Reviewed
- Daily activity timeline (timeseries):
  - Merged PRs by Organization
  - Reviews Submitted by Organization

**Dashboard Features:**
- Fully editable in the Grafana UI
- Auto-refreshing data from output files
- Bot detection and filtering capabilities

### github_cache/
Directory containing cached JSON responses from the GitHub API, one file per repository. This reduces API calls during development. The cache files store commit data fetched from the GitHub API.

### review_cache/
Directory containing cached API responses from performance-review.py script.

**Caching Strategy:**
- Search queries: Cache keys include date range (changes when dates change)
- PR reviews/comments: Cache keys are time-independent (reused across different date ranges)
- Live cache statistics displayed during execution
- Enables fast re-runs without hitting GitHub API rate limits

**Cache Performance:**
The improved caching strategy means subsequent runs with overlapping date ranges will have high cache hit rates for PR details, dramatically reducing API calls.

### output/
Directory containing all generated reports and data files:
- `performance_review_TIMESTAMP.json`: Complete raw data
- `timeseries_daily.csv`: Daily aggregated metrics
- `events.json`: Timestamped event stream
- `summary.json`: High-level statistics
- `dashboard-screenshot.png`: Dashboard screenshot for reference

## Configuration

### Legacy Scripts (main.py, contributions-detail.py)
These have hardcoded configuration at the top:
- `username`: GitHub username to analyze (currently set to 'jaydeluca')
- `org_name`: GitHub organization to analyze (currently set to 'open-telemetry')
- `token`: Read from GITHUB_TOKEN environment variable for API authentication

### performance-review.py
Fully configurable via CLI arguments (recommended) or by modifying the config dictionary:
- `--username`: GitHub username to analyze (defaults to the user associated with `GITHUB_TOKEN`)
- `--start-date`: Analysis start date (YYYY-MM-DD format)
- `--end-date`: Analysis end date (YYYY-MM-DD format)
- `--orgs`: List of organizations (default: open-telemetry prometheus grafana)
- `--output-dir`: Output directory (default: output)
- `--cache-dir`: Cache directory (default: review_cache)
- Token: Always read from `GITHUB_TOKEN` environment variable

### Docker Services
Configuration in docker-compose.yml:
- Grafana admin password: `admin` (changeable via GF_SECURITY_ADMIN_PASSWORD)
- Grafana port: 3000 (changeable via ports mapping)
- File server port: 8000 (internal, no need to expose)
- Infinity plugin: Auto-installed via GF_INSTALL_PLUGINS

## Troubleshooting

### Dashboard Shows "No Data"
If you see "No data" in dashboard panels:
1. Check Grafana logs: `docker logs github-contributions-grafana`
2. Verify file-server is accessible: `docker logs github-contributions-fileserver`
3. Confirm data files exist: `ls -la output/`
4. Verify the output files contain data: `cat output/summary.json`
5. Dashboard is editable in Grafana UI - you can modify queries and settings directly

### API Rate Limiting
- GitHub API allows 5,000 authenticated requests/hour
- Script implements caching to minimize API calls
- Clear cache with: `rm -rf review_cache/`
- Reduce date range or limit organizations if hitting limits

### Docker Issues
- Ensure Docker daemon is running
- Check port 3000 isn't already in use: `lsof -i :3000`
- Recreate containers: `docker-compose down -v && docker-compose up -d`
- Check container logs: `docker-compose logs`
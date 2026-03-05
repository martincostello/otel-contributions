# GitHub Contributions Dashboard

A tool for analyzing and visualizing GitHub contributions.
Generate eports with timeseries data and interactive Grafana dashboards.

## Quick Start

### Setup

1. **Set GitHub Token**
   ```bash
   export GITHUB_TOKEN="your_github_token_here"
   ```

2. **Run Analysis**
   ```bash
   # uv automatically installs dependencies on first run
   uv run python run_analysis.py --start-date 2025-07-01 --end-date 2026-02-21
   ```

   Or directly run the performance review script:
   ```bash
   uv run python performance-review.py --start-date 2025-07-01 --end-date 2026-01-31
   ```

3. **View Dashboard**

   The wrapper script automatically starts Grafana. Access it at:
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: `admin`

## Usage

### Command Line Options

```bash
uv run python performance-review.py [OPTIONS]

Required:
  --start-date YYYY-MM-DD     Analysis start date

Optional:
  --end-date YYYY-MM-DD       Analysis end date (defaults to today)
  --username USERNAME         GitHub username to analyze (defaults to the user associated with `GITHUB_TOKEN`)
  --orgs ORG1 ORG2 ...        Organizations to analyze
                              (default: open-telemetry prometheus grafana)
  --output-dir DIR            Output directory (default: output)
  --cache-dir DIR             Cache directory (default: review_cache)
```

### Examples

**Basic Usage:**
```bash
uv run python performance-review.py \
  --start-date 2025-07-01 \
  --end-date 2026-01-31
```

**With Wrapper Script:**
```bash
uv run python run_analysis.py \
  --start-date 2025-07-01 \
  --end-date 2026-01-31
```

**Custom Username:**
```bash
uv run python performance-review.py \
  --start-date 2025-07-01 \
  --end-date 2026-01-31 \
  --username otel-contributor
```

**Custom Organizations:**
```bash
uv run python performance-review.py \
  --start-date 2025-01-01 \
  --end-date 2025-12-31 \
  --orgs kubernetes docker helm
```

**Custom Output Directory:**
```bash
uv run python performance-review.py \
  --start-date 2025-07-01 \
  --end-date 2026-01-31 \
  --output-dir ./my-reports
```

### Starting the Dashboard

**Using the wrapper script:**
```bash
uv run python run_analysis.py --username jaydeluca --start-date 2025-07-01 --end-date 2026-01-31
```

**Manual start:**
```bash
docker-compose up -d
```

**Stopping the dashboard:**
```bash
docker-compose down
```

## Architecture

### Components

```
┌─────────────────────────┐
│  performance-review.py  │  ← Main analysis script
└───────────┬─────────────┘
            │
            ├→ GitHub API (with caching)
            │
            ├→ output/
            │   ├── performance_review_*.json
            │   ├── timeseries_daily.csv
            │   ├── events.json
            │   └── summary.json
            │
┌───────────▼─────────────┐
│   Docker Compose        │
├─────────────────────────┤
│  ┌─────────────────┐    │
│  │ File Server     │    │  ← Serves data files
│  │ (Python HTTP)   │    │
│  └─────────────────┘    │
│  ┌─────────────────┐    │
│  │ Grafana         │    │  ← Visualization
│  │ + Infinity      │    │
│  └─────────────────┘    │
└─────────────────────────┘
```

### Data Flow

1. **Collection**: Script queries GitHub API across specified organizations
2. **Caching**: API responses cached to `review_cache/` directory
3. **Processing**: Raw data aggregated into timeseries and summary formats
4. **Storage**: Multiple output formats saved to `output/` directory
5. **Serving**: Python HTTP server exposes data files to Grafana
6. **Visualization**: Grafana Infinity plugin queries files and renders dashboard

## Caching

The script implements intelligent caching to avoid redundant API calls:

- **Cache Location**: `review_cache/` directory
- **Cache Key**: Based on query type, date range, and parameters
- **Cache Behavior**: If data exists in cache for the same date range, it's reused
- **Cache Invalidation**: Change date range or delete cache files to force refresh

**Clear cache:**
```bash
rm -rf review_cache/
```

## Configuration

### Modifying Date Range

Pass different dates via CLI arguments:
```bash
uv run python performance-review.py \
  --start-date 2025-08-01 \
  --end-date 2026-02-28
```

### Adding Organizations

```bash
uv run python performance-review.py \
  --start-date 2025-01-01 \
  --end-date 2025-12-31 \
  --orgs open-telemetry prometheus grafana kubernetes docker
```

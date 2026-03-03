import requests
import os
from datetime import datetime
from collections import defaultdict
import json
import hashlib
import argparse
import csv

config = {
    'username': None,
    'token': None,
    'headers': None,
    'organizations': [],
    'start_date': None,
    'end_date': None,
    'cache_dir': None,
    'output_dir': None,
}

cache_stats = {
    'hits': 0,
    'misses': 0,
    'api_calls': 0,
    'last_printed': '',  # Track last printed line for updates
}


def print_cache_stats_inline():
    """Print cache statistics on the same line (updates in place)"""
    total = cache_stats['hits'] + cache_stats['misses']
    if total == 0:
        return

    hit_rate = (cache_stats['hits'] / total) * 100 if total > 0 else 0

    status = f"    [Cache: {cache_stats['hits']} hits, {cache_stats['misses']} misses ({hit_rate:.1f}% hit rate) | API calls: {cache_stats['api_calls']}]"

    if status != cache_stats['last_printed']:
        print(f"\r{' ' * len(cache_stats['last_printed'])}\r{status}", end='', flush=True)
        cache_stats['last_printed'] = status


def clear_cache_stats_line():
    """Clear the inline cache stats line"""
    if cache_stats['last_printed']:
        print(f"\r{' ' * len(cache_stats['last_printed'])}\r", end='', flush=True)
        cache_stats['last_printed'] = ''


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Analyze GitHub contributions for performance review',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze contributions for a specific period
  python performance-review.py --start-date 2025-07-01 --end-date 2026-01-31

  # Custom organizations
  python performance-review.py --start-date 2025-01-01 --end-date 2025-12-31 --orgs kubernetes docker
        """
    )

    parser.add_argument('--username', help='GitHub username to analyze (defaults to the user associated with GITHUB_TOKEN)')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--orgs', nargs='+', default=['open-telemetry', 'prometheus', 'grafana'],
                        help='GitHub organizations to analyze (default: open-telemetry prometheus grafana)')
    parser.add_argument('--output-dir', default='output', help='Output directory (default: output)')
    parser.add_argument('--cache-dir', default='review_cache', help='Cache directory (default: review_cache)')

    return parser.parse_args()


def init_config(args):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        exit(1)

    config['token'] = token
    config['headers'] = {'Authorization': f'token {token}'}
    config['organizations'] = args.orgs
    config['start_date'] = args.start_date
    config['end_date'] = args.end_date
    config['cache_dir'] = args.cache_dir
    config['output_dir'] = args.output_dir

    if args.username:
        username = args.username
    else:
        cache_stats['api_calls'] += 1
        print_cache_stats_inline()
        response = requests.get('https://api.github.com/user', headers=config['headers'], timeout=10)

        if response.status_code != 200:
            clear_cache_stats_line()
            try:
                error_message = response.json().get('message', 'Unknown error')
            except ValueError:
                # Fallback for non-JSON or empty error bodies
                error_message = response.text or 'Unknown error (non-JSON response)'
            print(f"    [API ERROR] {response.status_code} - {error_message}")
            exit(1)

        try:
            data = response.json()
        except ValueError:
            clear_cache_stats_line()
            print("    [API ERROR] 200 - Unable to parse JSON from GitHub user response")
            exit(1)
        username = data.get('login')
        if not username:
            print("Error: Unable to determine username from GitHub login associated with GITHUB_TOKEN")
            exit(1)

    config['username'] = username

    # Create directories
    os.makedirs(config['cache_dir'], exist_ok=True)
    os.makedirs(config['output_dir'], exist_ok=True)

    print(f"Analyzing contributions for: {config['username']}")
    print(f"Period: {config['start_date']} to {config['end_date']}")
    print(f"Organizations: {', '.join(config['organizations'])}\n")


def get_cache_key(query_type, *args, include_dates=True):
    """Generate a cache key based on query type and parameters

    Args:
        query_type: Type of query (e.g., 'search', 'reviews')
        *args: Additional parameters for the cache key
        include_dates: Whether to include date range in cache key (default True)
                      Set to False for time-independent data like PR reviews
    """
    if include_dates:
        key_parts = [config['start_date'], config['end_date'], query_type] + list(args)
    else:
        key_parts = [query_type] + list(args)
    key_string = '_'.join(str(p) for p in key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def load_from_cache(cache_key):
    """Load data from cache if it exists"""
    cache_file = os.path.join(config['cache_dir'], f'{cache_key}.json')
    if os.path.exists(cache_file):
        cache_stats['hits'] += 1
        print_cache_stats_inline()
        with open(cache_file, 'r') as f:
            return json.load(f)
    cache_stats['misses'] += 1
    print_cache_stats_inline()
    return None


def save_to_cache(cache_key, data):
    """Save data to cache"""
    cache_file = os.path.join(config['cache_dir'], f'{cache_key}.json')
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=2)


def is_bot(username):
    """Detect if a username belongs to a bot

    Common bot patterns:
    - Ends with [bot]
    - Ends with -bot
    - Known bot names
    """
    username_lower = username.lower()

    # Common bot suffixes
    if username_lower.endswith('[bot]') or username_lower.endswith('-bot'):
        return True

    # Known bot usernames
    known_bots = {
        'dependabot', 'renovate', 'renovate-bot', 'github-actions',
        'dependabot-preview', 'greenkeeper', 'snyk-bot', 'imgbot',
        'codecov-io', 'codecov-commenter', 'coveralls', 'stalebot',
        'allcontributors', 'mergify', 'netlify', 'vercel', 'deepsource-autofix',
        'restyled-io', 'semantic-release-bot', 'release-drafter',
        'pre-commit-ci', 'codesandbox', 'gitpod-io', 'pyup-bot',
        'whitesource-bolt-for-github', 'lgtm-com', 'fossabot',
        'linguist-bot', 'github-learning-lab', 'github-classroom',
    }

    return username_lower in known_bots


def search_github(query, per_page=100):
    """Search GitHub using the search API with pagination and caching"""
    cache_key = get_cache_key('search', query)
    cached_data = load_from_cache(cache_key)
    if cached_data is not None:
        return cached_data

    all_items = []
    page = 1

    while True:
        url = f'https://api.github.com/search/issues?q={query}&per_page={per_page}&page={page}'
        cache_stats['api_calls'] += 1
        print_cache_stats_inline()
        response = requests.get(url, headers=config['headers'])

        if response.status_code != 200:
            clear_cache_stats_line()
            print(f"    [API ERROR] {response.status_code} - {response.json().get('message', 'Unknown error')}")
            break

        data = response.json()
        items = data.get('items', [])

        if not items:
            break

        all_items.extend(items)

        if len(items) < per_page or data.get('total_count', 0) <= len(all_items):
            break

        page += 1

    save_to_cache(cache_key, all_items)
    return all_items


def get_pr_reviews(repo_full_name, pr_number):
    """Get all reviews for a specific PR with caching

    Note: PR reviews are static data, so we don't include date range in cache key.
    This allows cache reuse across different time range queries.
    """
    cache_key = get_cache_key('reviews', repo_full_name, pr_number, include_dates=False)
    cached_data = load_from_cache(cache_key)
    if cached_data is not None:
        return cached_data

    url = f'https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/reviews'
    cache_stats['api_calls'] += 1
    print_cache_stats_inline()
    response = requests.get(url, headers=config['headers'])

    if response.status_code == 200:
        data = response.json()
        save_to_cache(cache_key, data)
        return data
    return []


def get_pr_review_comments(repo_full_name, pr_number):
    """Get all review comments for a specific PR with caching

    Note: PR review comments are static data, so we don't include date range in cache key.
    This allows cache reuse across different time range queries.
    """
    cache_key = get_cache_key('review_comments', repo_full_name, pr_number, include_dates=False)
    cached_data = load_from_cache(cache_key)
    if cached_data is not None:
        return cached_data

    url = f'https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/comments'
    cache_stats['api_calls'] += 1
    print_cache_stats_inline()
    response = requests.get(url, headers=config['headers'])

    if response.status_code == 200:
        data = response.json()
        save_to_cache(cache_key, data)
        return data
    return []


def analyze_contributions():
    """Main function to analyze all contributions"""

    stats = {
        'merged_prs': [],
        'prs_reviewed': [],
        'pr_comments_made': [],
        'issue_comments_made': [],
        'reviews_by_state': defaultdict(int),
        'repos_contributed_to': set(),
        'unique_pr_authors': set(),
        'unique_pr_authors_non_bot': set(),
        'bot_pr_authors': set(),
    }

    print("=" * 80)
    print("GATHERING DATA - This may take a few minutes...")
    print("=" * 80)

    for org in config['organizations']:
        clear_cache_stats_line()
        print(f"\nProcessing organization: {org}")

        print(f"  - Fetching merged PRs...")
        query = f'is:pr author:{config["username"]} is:merged merged:{config["start_date"]}..{config["end_date"]} org:{org}'
        merged_prs = search_github(query)
        clear_cache_stats_line()
        org_merged_count = len(merged_prs)

        for pr in merged_prs:
            repo_name = pr['repository_url'].split('/')[-2] + '/' + pr['repository_url'].split('/')[-1]
            stats['merged_prs'].append({
                'title': pr['title'],
                'url': pr['html_url'],
                'repo': repo_name,
                'org': org,
                'merged_at': pr.get('closed_at'),
            })
            stats['repos_contributed_to'].add(repo_name)

        clear_cache_stats_line()
        print(f"  - Fetching reviewed PRs...")
        query = f'is:pr reviewed-by:{config["username"]} org:{org} updated:{config["start_date"]}..{config["end_date"]}'
        reviewed_prs = search_github(query)
        clear_cache_stats_line()
        org_reviews_before = len(stats['prs_reviewed'])

        for pr in reviewed_prs:
            # Skip PRs authored by the user (those show up in reviewed-by)
            if pr['user']['login'] == config['username']:
                continue

            repo_name = pr['repository_url'].split('/')[-2] + '/' + pr['repository_url'].split('/')[-1]
            pr_number = pr['number']

            reviews = get_pr_reviews(repo_name, pr_number)
            user_reviews = [r for r in reviews if r.get('user') and r['user'].get('login') == config['username']]

            if user_reviews:
                pr_author = pr['user']['login']
                author_is_bot = is_bot(pr_author)

                stats['unique_pr_authors'].add(pr_author)
                if author_is_bot:
                    stats['bot_pr_authors'].add(pr_author)
                else:
                    stats['unique_pr_authors_non_bot'].add(pr_author)

                for review in user_reviews:
                    stats['reviews_by_state'][review['state']] += 1
                    stats['prs_reviewed'].append({
                        'title': pr['title'],
                        'url': pr['html_url'],
                        'repo': repo_name,
                        'org': org,
                        'submitted_at': review.get('submitted_at'),
                        'state': review['state'],
                        'author': pr_author,
                        'author_is_bot': author_is_bot,
                    })

        clear_cache_stats_line()
        print(f"  - Fetching PR comments...")
        query = f'is:pr commenter:{config["username"]} org:{org} updated:{config["start_date"]}..{config["end_date"]}'
        commented_prs = search_github(query)
        clear_cache_stats_line()

        for pr in commented_prs:
            repo_name = pr['repository_url'].split('/')[-2] + '/' + pr['repository_url'].split('/')[-1]
            pr_number = pr['number']

            # Get review comments to count actual comments made
            comments = get_pr_review_comments(repo_name, pr_number)
            user_comments = [c for c in comments if c['user'] and c['user'].get('login') == config['username']]

            if user_comments:
                stats['pr_comments_made'].append({
                    'title': pr['title'],
                    'url': pr['html_url'],
                    'repo': repo_name,
                    'comment_count': len(user_comments),
                })

        clear_cache_stats_line()
        print(f"  - Fetching issue comments...")
        query = f'is:issue commenter:{config["username"]} org:{org} updated:{config["start_date"]}..{config["end_date"]}'
        commented_issues = search_github(query)
        clear_cache_stats_line()

        for issue in commented_issues:
            repo_name = issue['repository_url'].split('/')[-2] + '/' + issue['repository_url'].split('/')[-1]

            stats['issue_comments_made'].append({
                'title': issue['title'],
                'url': issue['html_url'],
                'repo': repo_name,
                'comments': issue['comments'],
            })

        clear_cache_stats_line()
        org_reviewed_count = len(stats['prs_reviewed']) - org_reviews_before
        print(f"  ✓ Found {org_merged_count} merged PRs, {org_reviewed_count} reviews for {org}")

    return stats


def extract_timeseries_events(stats):
    """
    Extract timestamped events from raw stats for timeseries analysis
    Returns list of events with timestamp, type, and metadata
    """
    events = []

    # Merged PRs - use merged_at timestamp
    for pr in stats['merged_prs']:
        if pr.get('merged_at'):
            events.append({
                'timestamp': pr['merged_at'],
                'event_type': 'pr_merged',
                'repo': pr['repo'],
                'metric_value': 1,
                'metadata': {
                    'url': pr['url'],
                    'title': pr['title']
                }
            })

    # Reviews - each review is already a separate entry with timestamp
    for review in stats['prs_reviewed']:
        events.append({
            'timestamp': review.get('submitted_at'),
            'event_type': 'pr_review',
            'repo': review['repo'],
            'metric_value': 1,
            'metadata': {
                'url': review['url'],
                'title': review['title'],
                'state': review['state']
            }
        })

    for pr_comment in stats['pr_comments_made']:
        events.append({
            'timestamp': None,  # We'll estimate from the PR data
            'event_type': 'pr_comment',
            'repo': pr_comment['repo'],
            'metric_value': pr_comment['comment_count'],
            'metadata': {
                'url': pr_comment['url'],
                'title': pr_comment['title']
            }
        })

    # Issue Comments
    for issue_comment in stats['issue_comments_made']:
        events.append({
            'timestamp': None,
            'event_type': 'issue_comment',
            'repo': issue_comment['repo'],
            'metric_value': 1,
            'metadata': {
                'url': issue_comment['url'],
                'title': issue_comment['title']
            }
        })

    # Sort by timestamp (None values will go to end)
    events_with_time = [e for e in events if e['timestamp'] is not None]
    events_without_time = [e for e in events if e['timestamp'] is None]

    return sorted(events_with_time, key=lambda x: x['timestamp']) + events_without_time


def generate_daily_timeseries(stats):
    """
    Generate daily aggregated metrics from stats with per-org breakdown
    Returns list of daily data points
    """
    from datetime import datetime, timedelta

    start = datetime.fromisoformat(config['start_date'])
    end = datetime.fromisoformat(config['end_date'])

    daily_data = {}
    current_date = start
    while current_date <= end:
        date_str = current_date.strftime('%Y-%m-%d')
        data_point = {'date': date_str}

        for org in config['organizations']:
            org_key = org.replace('-', '_')
            data_point[f'merged_prs_{org_key}'] = 0
            data_point[f'reviews_submitted_{org_key}'] = 0

        daily_data[date_str] = data_point
        current_date += timedelta(days=1)

    # Aggregate merged PRs by day and org
    for pr in stats['merged_prs']:
        if pr.get('merged_at'):
            date_str = pr['merged_at'][:10]  # Extract YYYY-MM-DD
            org = pr.get('org', 'unknown')
            org_key = org.replace('-', '_')
            if date_str in daily_data:
                daily_data[date_str][f'merged_prs_{org_key}'] += 1

    # Aggregate reviews by day and org using actual timestamps
    for review in stats['prs_reviewed']:
        if review.get('submitted_at'):
            date_str = review['submitted_at'][:10]  # Extract YYYY-MM-DD
            org = review.get('org', 'unknown')
            org_key = org.replace('-', '_')
            if date_str in daily_data:
                daily_data[date_str][f'reviews_submitted_{org_key}'] += 1

    result = []
    for date_str in sorted(daily_data.keys()):
        result.append(daily_data[date_str])

    return result


def save_timeseries_outputs(stats):
    """Save all timeseries data formats"""
    clear_cache_stats_line()
    print("\n📈 Generating timeseries data...")

    daily_data = generate_daily_timeseries(stats)
    csv_path = os.path.join(config['output_dir'], 'timeseries_daily.csv')

    with open(csv_path, 'w', newline='') as f:
        if daily_data:
            writer = csv.DictWriter(f, fieldnames=daily_data[0].keys())
            writer.writeheader()
            writer.writerows(daily_data)

    print(f"   ✓ Daily timeseries saved to: {csv_path}")

    events = extract_timeseries_events(stats)
    events_path = os.path.join(config['output_dir'], 'events.json')

    with open(events_path, 'w') as f:
        json.dump(events, f, indent=2)

    print(f"   ✓ Events data saved to: {events_path}")

    non_bot_reviews = [pr for pr in stats['prs_reviewed'] if not pr.get('author_is_bot', False)]

    summary = {
        'period': {
            'start': config['start_date'],
            'end': config['end_date']
        },
        'username': config['username'],
        'organizations': config['organizations'],
        'totals': {
            'merged_prs': len(stats['merged_prs']),
            'reviews_submitted': len(stats['prs_reviewed']),
            'reviews_submitted_non_bot': len(non_bot_reviews),
            'reviews_submitted_bot': len(stats['prs_reviewed']) - len(non_bot_reviews),
            'pr_comments': len(stats['pr_comments_made']),
            'issue_comments': len(stats['issue_comments_made']),
            'repositories': len(stats['repos_contributed_to']),
            'unique_contributors': len(stats['unique_pr_authors']),
            'unique_contributors_non_bot': len(stats['unique_pr_authors_non_bot']),
            'unique_contributors_bot': len(stats['bot_pr_authors'])
        },
        'reviews_by_state': dict(stats['reviews_by_state']),
        'repositories': list(stats['repos_contributed_to']),
        'bot_contributors': list(stats['bot_pr_authors'])
    }

    # Calculate daily averages
    total_days = (datetime.fromisoformat(config['end_date']) - datetime.fromisoformat(config['start_date'])).days + 1
    if total_days > 0:
        summary['daily_averages'] = {
            'merged_prs': round(len(stats['merged_prs']) / total_days, 2),
            'reviews_per_day': round(len(stats['prs_reviewed']) / total_days, 2)
        }

    summary_path = os.path.join(config['output_dir'], 'summary.json')

    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"   ✓ Summary data saved to: {summary_path}")


def print_summary(stats):
    """Print a formatted summary of contributions"""
    clear_cache_stats_line()

    print("\n")
    print("=" * 80)
    print("PERFORMANCE REVIEW SUMMARY")
    print(f"Period: {config['start_date']} to {config['end_date']}")
    print("=" * 80)

    print("\n📊 HIGH-LEVEL METRICS")
    print("-" * 80)
    print(f"Total Merged PRs:                    {len(stats['merged_prs'])}")
    print(f"Total PRs Reviewed:                  {len(stats['prs_reviewed'])}")

    non_bot_reviews = [pr for pr in stats['prs_reviewed'] if not pr.get('author_is_bot', False)]
    print(f"  └─ Reviews of Non-Bot PRs:         {len(non_bot_reviews)}")
    print(f"  └─ Reviews of Bot PRs:             {len(stats['prs_reviewed']) - len(non_bot_reviews)}")

    print(f"Unique Contributors Reviewed:        {len(stats['unique_pr_authors'])}")
    print(f"  └─ Human Contributors:             {len(stats['unique_pr_authors_non_bot'])}")
    print(f"  └─ Bot Contributors:               {len(stats['bot_pr_authors'])}")

    print(f"Total PR Comments:                   {len(stats['pr_comments_made'])}")
    print(f"Total Issue Comments:                {len(stats['issue_comments_made'])}")
    print(f"Repositories Contributed To:         {len(stats['repos_contributed_to'])}")

    print("\n🔍 CODE REVIEW BREAKDOWN")
    print("-" * 80)
    for state, count in stats['reviews_by_state'].items():
        print(f"{state.upper():30} {count}")

    if stats['bot_pr_authors']:
        print(f"\n🤖 BOT CONTRIBUTORS DETECTED ({len(stats['bot_pr_authors'])})")
        print("-" * 80)
        for bot in sorted(stats['bot_pr_authors']):
            print(f"  • {bot}")

    print(f"\n📦 CONTRIBUTIONS BY REPOSITORY")
    print("-" * 80)
    repo_stats = defaultdict(lambda: {'merged_prs': 0, 'reviewed_prs': 0})

    for pr in stats['merged_prs']:
        repo_stats[pr['repo']]['merged_prs'] += 1

    for pr in stats['prs_reviewed']:
        repo_stats[pr['repo']]['reviewed_prs'] += 1

    for repo, counts in sorted(repo_stats.items(), key=lambda x: x[1]['merged_prs'] + x[1]['reviewed_prs'], reverse=True):
        print(f"{repo:50} Merged: {counts['merged_prs']:3}  Reviewed: {counts['reviewed_prs']:3}")

    if stats['merged_prs']:
        print(f"\n✅ MERGED PULL REQUESTS ({len(stats['merged_prs'])})")
        print("-" * 80)

    if stats['prs_reviewed']:
        print(f"\n👀 PULL REQUESTS REVIEWED ({len(stats['prs_reviewed'])})")
        print("-" * 80)


def save_detailed_report(stats):
    """Save detailed statistics to a JSON file for further analysis"""
    clear_cache_stats_line()
    filename = f'performance_review_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    filepath = os.path.join(config['output_dir'], filename)

    stats_copy = stats.copy()
    stats_copy['repos_contributed_to'] = list(stats['repos_contributed_to'])
    stats_copy['unique_pr_authors'] = list(stats['unique_pr_authors'])
    stats_copy['unique_pr_authors_non_bot'] = list(stats['unique_pr_authors_non_bot'])
    stats_copy['bot_pr_authors'] = list(stats['bot_pr_authors'])
    stats_copy['reviews_by_state'] = dict(stats['reviews_by_state'])

    with open(filepath, 'w') as f:
        json.dump(stats_copy, f, indent=2)

    print(f"\n💾 Detailed report saved to: {filepath}")


def main():
    """Main entry point for the script"""
    args = parse_args()
    init_config(args)

    stats = analyze_contributions()
    print_summary(stats)
    save_detailed_report(stats)
    save_timeseries_outputs(stats)

    clear_cache_stats_line()
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)
    print("\nCache Statistics:")
    print(f"  Cache Hits:   {cache_stats['hits']}")
    print(f"  Cache Misses: {cache_stats['misses']}")
    print(f"  API Calls:    {cache_stats['api_calls']}")
    if cache_stats['hits'] + cache_stats['misses'] > 0:
        hit_rate = (cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses'])) * 100
        print(f"  Hit Rate:     {hit_rate:.1f}%")
    print("=" * 80)


if __name__ == '__main__':
    main()

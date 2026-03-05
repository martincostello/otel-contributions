import time
import requests
from datetime import datetime


def github_get(url, headers, **kwargs):
    """Make a GitHub API GET request, waiting automatically when rate limits are hit.

    Handles both primary rate limits (x-ratelimit-reset header) and secondary
    rate limits (retry-after header) by sleeping until the reset time before
    retrying the request.
    """
    while True:
        response = requests.get(url, headers=headers, **kwargs)

        if response.status_code not in (403, 429):
            return response

        retry_after = response.headers.get('retry-after')
        reset_time = response.headers.get('x-ratelimit-reset')
        remaining = response.headers.get('x-ratelimit-remaining')

        # Secondary rate limit: retry-after header is present
        if retry_after:
            wait_seconds = int(retry_after) + 1
            resume_at = datetime.fromtimestamp(time.time() + wait_seconds).strftime('%H:%M:%S')
            print(f"\n[Rate Limited] Secondary rate limit hit. Waiting {wait_seconds}s (resumes ~{resume_at})...")
            time.sleep(wait_seconds)
            continue

        # Primary rate limit: quota exhausted
        if reset_time and remaining == '0':
            wait_seconds = max(1, int(reset_time) - int(time.time()) + 1)
            resume_at = datetime.fromtimestamp(int(reset_time)).strftime('%H:%M:%S')
            print(f"\n[Rate Limited] Primary rate limit hit. Waiting {wait_seconds}s until {resume_at}...")
            time.sleep(wait_seconds)
            continue

        # Non-rate-limit 403 — return as-is so callers can handle it
        return response

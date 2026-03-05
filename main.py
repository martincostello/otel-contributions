import requests
import os
from github_utils import github_get


username = 'jaydeluca'
token = os.environ.get("GITHUB_TOKEN")
headers = {'Authorization': f'token {token}'}

org_name = 'open-telemetry'


def load_or_fetch_repo_data(repo_name):
    all_commits = []
    page = 1
    while True:
        print(f"Fetching commits for {repo_name} page {page}")
        commits_url = f'https://api.github.com/repos/{org_name}/{repo_name}/commits?author={username}&page={page}&per_page=100'
        commits_response = github_get(commits_url, headers=headers)
        commit_data = commits_response.json()
        if not commit_data:
            break
        all_commits.extend(commit_data)
        page += 1

    return all_commits


def print_results(total_commits, total_additions, total_deletions, repo_info):
    print(f"\nSummary of Contributions to the {org_name} Organization\n")
    print(f"Total commits: {total_commits}")
    print(f"Total lines added: {total_additions}")
    print(f"Total lines deleted: {total_deletions}\n")

    print("Detailed Contributions by Repository:\n")
    for repo, stats in repo_info.items():
        print(f"Repository: {repo}")
        print(f"  Commits: {stats['commits']}")
        print(f"  Lines added: {stats['additions']}")
        print(f"  Lines deleted: {stats['deletions']}\n")


if __name__ == '__main__':

    page = 0
    repos = []
    while True:
        repos_url = f'https://api.github.com/orgs/{org_name}/repos?page={page}&per_page=100'
        repos_response = github_get(repos_url, headers=headers)
        new_repos = repos_response.json()
        repos.extend(new_repos)
        if len(new_repos) < 100:
            break
        page += 1

    total_commits = 0
    total_additions = 0
    total_deletions = 0

    repo_info = {}

    for repo in repos:
        repo_name = repo['name']

        commits = load_or_fetch_repo_data(repo_name)

        local_commits = 0
        local_additions = 0
        local_deletions = 0

        for commit in commits:
            commit_url = commit['url']
            commit_details = github_get(commit_url, headers=headers).json()
            stats = commit_details.get('stats', {})
            local_commits += 1
            local_additions += stats.get('additions', 0)
            local_deletions += stats.get('deletions', 0)

        total_commits += local_commits
        total_additions += local_additions
        total_deletions += local_deletions

        if local_commits > 0:
            repo_info[repo_name] = {
                "commits": local_commits,
                "additions": local_additions,
                "deletions": local_deletions
            }

    print_results(total_commits, total_additions, total_deletions, repo_info)

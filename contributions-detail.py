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
        # print(f"Fetching commits for {repo_name} page {page}")
        commits_url = f'https://api.github.com/repos/{org_name}/{repo_name}/commits?author={username}&page={page}&per_page=100'
        commits_response = github_get(commits_url, headers=headers)
        commit_data = commits_response.json()
        if not commit_data:
            break
        all_commits.extend(commit_data)
        page += 1

    return all_commits


def load_or_fetch_prs(repo_name):
    all_prs = []
    page = 1
    while True:
        # print(f"Fetching PRs for {repo_name} page {page}")
        url = f'https://api.github.com/repos/{org_name}/{repo_name}/pulls?state=closed&page={page}&per_page=1000'
        commits_response = github_get(url, headers=headers)
        commit_data = commits_response.json()
        if not commit_data:
            break
        for item in commit_data:
            if item["user"]["login"] == "jaydeluca":
                all_prs.append({
                    "url": item["html_url"],
                    "title": item["title"],
                })
        page += 1

    return all_prs


if __name__ == '__main__':
    page = 0
    repos = []
    while True:
        repos_url = f'https://api.github.com/orgs/{org_name}/repos?sort=created&direction=desc&page={page}&per_page=100'
        repos_response = github_get(repos_url, headers=headers)
        new_repos = repos_response.json()
        repos.extend(new_repos)
        if len(new_repos) < 100:
            break
        page += 1

    repo_info = {}

    for repo in repos:
        repo_name = repo['name']

        commits = load_or_fetch_repo_data(repo_name)
        if len(commits) > 0:
            prs = load_or_fetch_prs(repo_name)
            if len(prs) > 0:
                print(f"#### {repo_name}")
                for pr in prs:
                    print(f"* [{pr['title']}]({pr['url']})")
                print("\n")



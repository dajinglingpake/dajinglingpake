#!/usr/bin/env python3
import json
import os
import sys
import urllib.request


LOGIN = os.getenv("GITHUB_LOGIN", "dajinglingpake")
README_PATH = os.getenv("README_PATH", "README.md")
MIN_STARS = int(os.getenv("MIN_STARS", "1000"))
MAX_REPOS = int(os.getenv("MAX_REPOS", "6"))
START = "<!-- CONTRIBUTED-REPOS:START -->"
END = "<!-- CONTRIBUTED-REPOS:END -->"


QUERY = """
query($login: String!) {
  user(login: $login) {
    repositoriesContributedTo(
      first: 100
      includeUserRepositories: false
      contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]
    ) {
      nodes {
        name
        nameWithOwner
        url
        stargazerCount
        isPrivate
      }
    }
  }
}
"""


def github_token() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN or GH_TOKEN is required")
    return token


def fetch_contributed_repos() -> list[dict]:
    request_body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=request_body,
        headers={
            "Authorization": f"Bearer {github_token()}",
            "Content-Type": "application/json",
            "User-Agent": "dajinglingpake-profile-updater",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())

    if payload.get("errors"):
        raise RuntimeError(payload["errors"])

    nodes = payload["data"]["user"]["repositoriesContributedTo"]["nodes"]
    repos = [repo for repo in nodes if not repo["isPrivate"] and repo["stargazerCount"] >= MIN_STARS]
    return sorted(repos, key=lambda repo: (-repo["stargazerCount"], repo["nameWithOwner"].lower()))[:MAX_REPOS]


def render_repo_cards(repos: list[dict]) -> str:
    if not repos:
        return "暂未发现符合展示阈值的开源贡献项目。"

    blocks = []
    for repo in repos:
        owner, name = repo["nameWithOwner"].split("/", 1)
        blocks.append(
            "\n".join(
                [
                    f'<a href="{repo["url"]}">',
                    f'  <img src="https://github-readme-stats.vercel.app/api/pin/?username={owner}&repo={name}&theme=tokyonight&hide_border=true" alt="{repo["nameWithOwner"]}" />',
                    "</a>",
                ]
            )
        )
    return "\n".join(blocks)


def replace_block(readme: str, content: str) -> str:
    start_index = readme.find(START)
    end_index = readme.find(END)
    if start_index == -1 or end_index == -1 or start_index > end_index:
        raise RuntimeError(f"README must contain {START} and {END} markers")

    before = readme[: start_index + len(START)]
    after = readme[end_index:]
    return f"{before}\n{content}\n{after}"


def main() -> int:
    repos = fetch_contributed_repos()
    with open(README_PATH, "r", encoding="utf-8") as file:
        readme = file.read()

    updated = replace_block(readme, render_repo_cards(repos))
    with open(README_PATH, "w", encoding="utf-8") as file:
        file.write(updated)

    print(f"Updated {len(repos)} contributed repos with min stars {MIN_STARS}.")
    for repo in repos:
        print(f'- {repo["nameWithOwner"]}: {repo["stargazerCount"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Render recent open source PRs and issues into README.md between the OSS-LIST markers."""

import json
import os
import re
import urllib.parse
import urllib.request

USER = "selimaytac"
LIMIT = 6
# Only established public projects count; small personal or team repos are skipped.
MIN_STARS = 100
# Order shown in the table: merged work first, then open PRs, fixed issues, open reports.
RANK = {"Merged": 0, "PR open": 1, "Fixed": 2, "Reported": 3}
# GitHub's own colors for each state, rendered as small static badges.
BADGE = {"Merged": "8957e5", "PR open": "238636", "Fixed": "1f6feb", "Reported": "6e7681"}


def get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    })
    return json.load(urllib.request.urlopen(req, timeout=30))


def search():
    q = f"author:{USER} -user:{USER}"
    return get("https://api.github.com/search/issues?" + urllib.parse.urlencode(
        {"q": q, "sort": "created", "order": "desc", "per_page": 100}
    ))["items"]


_repos = {}


def established(repo):
    """Public, not archived, and at least MIN_STARS stars."""
    if repo not in _repos:
        _repos[repo] = get(f"https://api.github.com/repos/{repo}")
    info = _repos[repo]
    return (not info["private"] and info["visibility"] == "public"
            and not info["archived"] and info["stargazers_count"] >= MIN_STARS)


def status(item):
    pr = item.get("pull_request")
    if pr:
        if pr.get("merged_at"):
            return "Merged"
        return "PR open" if item["state"] == "open" else None
    if item["state"] == "open":
        return "Reported"
    return "Fixed" if item.get("state_reason") == "completed" else None


def cell(text, limit=72):
    # Backticks are dropped so truncation can never leave a broken code span.
    text = text.strip().replace("`", "").replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def badge(s):
    label = urllib.parse.quote(s)
    return f'<img src="https://img.shields.io/badge/{label}-{BADGE[s]}?style=flat-square" alt="{s}">'


def summary(rows):
    prs = [r for r in rows if r[5] in ("Merged", "PR open")]
    issues = [r for r in rows if r[5] in ("Fixed", "Reported")]
    merged = sum(r[5] == "Merged" for r in rows)
    fixed = sum(r[5] == "Fixed" for r in rows)
    projects = len({r[2] for r in rows})
    pr_part = f"**{len(prs)}** pull requests" + (f" (**{merged}** merged)" if merged else "")
    issue_part = f"**{len(issues)}** issues reported" + (f", **{fixed}** fixed upstream" if fixed else "")
    return f"{pr_part} · {issue_part} · **{projects}** projects"


def main():
    rows = []
    for item in search():
        s = status(item)
        if s:
            repo = item["repository_url"].split("/repos/", 1)[1]
            if not established(repo):
                continue
            rows.append((RANK[s], item["created_at"], repo, item["title"], item["html_url"], s))
    head = summary(rows)
    rows.sort(key=lambda r: (r[0], [-ord(c) for c in r[1]]))
    rows = sorted(rows[:LIMIT], key=lambda r: r[1], reverse=True)

    lines = [head, "", "| Contribution | Status |", "|---|:---:|"]
    for _, _, repo, title, url, s in rows:
        lines.append(f"| **[{repo}](https://github.com/{repo})** · [{cell(title)}]({url}) | {badge(s)} |")

    readme = open("README.md", encoding="utf-8").read()
    readme = re.sub(
        r"(<!-- OSS-LIST:START -->).*?(<!-- OSS-LIST:END -->)",
        lambda m: m.group(1) + "\n" + "\n".join(lines) + "\n" + m.group(2),
        readme,
        flags=re.S,
    )
    open("README.md", "w", encoding="utf-8").write(readme)


if __name__ == "__main__":
    main()

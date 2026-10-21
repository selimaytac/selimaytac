"""Render the latest Substack posts into README.md between the BLOG-POST-LIST markers.

Substack sometimes blocks CI runner IPs, so two sources are tried in order. If both fail,
the current list is kept and the step exits cleanly so the rest of the job still runs.
"""

import json
import re
import urllib.parse
import urllib.request

SITE = "https://aytacs.substack.com"
LIMIT = 3
UA = {"User-Agent": "Mozilla/5.0 (profile-readme-bot)"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=30))


def from_substack_api():
    posts = fetch(f"{SITE}/api/v1/archive?sort=new&limit={LIMIT}")
    return [(p["title"], p["canonical_url"]) for p in posts]


def from_rss2json():
    feed = urllib.parse.quote(f"{SITE}/feed", safe="")
    data = fetch(f"https://api.rss2json.com/v1/api.json?rss_url={feed}")
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", data.get("status")))
    return [(i["title"], i["link"]) for i in data["items"]]


def main():
    for source in (from_substack_api, from_rss2json):
        try:
            posts = source()[:LIMIT]
            if posts:
                break
        except Exception as e:  # noqa: BLE001 - any failure moves on to the next source
            print(f"::warning::{source.__name__} failed: {e}")
    else:
        print("::warning::no feed source worked; keeping the current list")
        return

    lines = "\n".join(f"- [{t.strip()}]({u})" for t, u in posts)
    readme = open("README.md", encoding="utf-8").read()
    readme = re.sub(
        r"(<!-- BLOG-POST-LIST:START -->).*?(<!-- BLOG-POST-LIST:END -->)",
        lambda m: m.group(1) + "\n" + lines + "\n" + m.group(2),
        readme,
        flags=re.S,
    )
    open("README.md", "w", encoding="utf-8").write(readme)
    print(f"rendered {len(posts)} posts from {source.__name__}")


if __name__ == "__main__":
    main()

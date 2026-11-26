#!/usr/bin/env python3
"""
Re-render every blog post, the blog index, sitemap.xml and the RSS feed with
the current theme in scripts/blog_theme.py.

Run after changing the blog theme:
    python3 scripts/rebuild_blog.py

Reads each post's body (between the <!-- post-body --> markers, or the
<article> element of the old layout) and its metadata from blog/posts.json
(falling back to the page itself), then rewrites blog/posts.json in full.
Article text is never changed.
"""

import datetime
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog_theme as T  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog"


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse(path, known):
    s = path.read_text(encoding="utf-8")
    m = re.search(r"<!-- post-body -->\n?(.*?)\n?<!-- /post-body -->", s, re.S) \
        or re.search(r"<article>(.*?)</article>", s, re.S)
    if not m:
        raise ValueError(f"no body found in {path.name}")
    body = m.group(1).strip()

    meta = dict(known.get(path.name, {}))
    meta["filename"] = path.name
    if "title" not in meta:
        meta["title"] = text(re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S).group(1))
    if "meta_description" not in meta:
        meta["meta_description"] = html.unescape(
            re.search(r'<meta name="description" content="(.*?)"', s).group(1))
    meta.setdefault("date", path.name[:10])
    if "category" not in meta:
        eb = re.search(r'class="eyebrow">(.*?)</', s, re.S)
        cat = text(eb.group(1)) if eb else "AI & Entertainment"
        cat = re.sub(r"\s*·\s*[A-Z][a-z]+ \d{1,2}, \d{4}\s*$", "", cat)
        cat = cat.replace(" · ", " & ").strip()
        meta["category"] = cat or "AI & Entertainment"
    if not meta.get("tags"):
        md = re.search(r'class="meta">(.*?)</div>', s, re.S)
        meta["tags"] = re.findall(r"#([\w-]+)", md.group(1)) if md else []
    if "image" not in meta:
        im = re.search(r'<img src="(/blog/images/[^"]+)"[^>]*class="hero-img"', s) \
            or re.search(r'class="post-hero"><img src="(/blog/images/[^"]+)"', s)
        meta["image"] = im.group(1) if im and (ROOT / im.group(1).lstrip("/")).exists() else None
    return meta, body


def main():
    manifest_path = BLOG / "posts.json"
    known = {}
    if manifest_path.exists():
        for p in json.loads(manifest_path.read_text(encoding="utf-8")):
            known[p["filename"]] = p

    posts = []
    for path in sorted(BLOG.glob("20*.html")):
        meta, body = parse(path, known)
        posts.append((meta, body))

    posts.sort(key=lambda x: (x[0]["date"], x[0]["filename"]), reverse=True)
    manifest = [m for m, _ in posts]

    for meta, body in posts:
        (BLOG / meta["filename"]).write_text(T.render_post(meta, body, manifest), encoding="utf-8")

    (BLOG / "index.html").write_text(T.render_index(manifest), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (BLOG / "feed.xml").write_text(T.render_feed(manifest), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(T.render_sitemap(manifest), encoding="utf-8")
    print(f"Rebuilt {len(posts)} posts, blog/index.html, blog/posts.json, blog/feed.xml, sitemap.xml")


if __name__ == "__main__":
    main()

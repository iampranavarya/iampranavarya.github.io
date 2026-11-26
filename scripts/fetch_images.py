#!/usr/bin/env python3
"""
Download new blog hero images listed in blog/images/incoming.json, save them as
1200x675 JPEGs in blog/images/, point each post at its image in blog/posts.json,
then re-render the blog (scripts/rebuild_blog.py also makes the WebP sizes).

incoming.json format: [{"post": "2026-10-14-some-post.html", "url": "https://..."}]
Runs in GitHub Actions (.github/workflows/blog-images.yml), which has the
network access needed to fetch the generated images.
"""

import io
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog"
INCOMING = BLOG / "images" / "incoming.json"
W, H = 1200, 675


def fit_16x9(im):
    im = im.convert("RGB")
    target = W / H
    w, h = im.size
    if w / h > target:  # too wide: crop sides
        nw = round(h * target)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    elif w / h < target:  # too tall: crop top and bottom
        nh = round(w / target)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return im.resize((W, H), Image.LANCZOS)


def main():
    if not INCOMING.exists():
        print("No incoming.json, nothing to do")
        return
    items = json.loads(INCOMING.read_text(encoding="utf-8"))
    manifest_path = BLOG / "posts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_file = {p["filename"]: p for p in manifest}

    done, failed = 0, []
    for it in items:
        post = by_file.get(it["post"])
        if not post:
            failed.append((it["post"], "post not in posts.json"))
            continue
        slug = it["post"][11:].removesuffix(".html")
        rel = f"/blog/images/{slug}.jpg"
        try:
            req = urllib.request.Request(it["url"], headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=60).read()
            im = fit_16x9(Image.open(io.BytesIO(data)))
            im.save(ROOT / rel.lstrip("/"), "JPEG", quality=84, optimize=True, progressive=True)
            post["image"] = rel
            done += 1
        except Exception as e:  # keep going; report at the end
            failed.append((it["post"], str(e)))

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {done} images")
    for f, why in failed:
        print(f"FAILED {f}: {why}")

    subprocess.run([sys.executable, str(ROOT / "scripts" / "rebuild_blog.py")], check=True)
    # keep only the failures so they can be retried; remove the file when all worked
    retry = [it for it in items if it["post"] in {f for f, _ in failed}]
    if retry:
        INCOMING.write_text(json.dumps(retry, indent=1), encoding="utf-8")
    else:
        INCOMING.unlink()


if __name__ == "__main__":
    main()

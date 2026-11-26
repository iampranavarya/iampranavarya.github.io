"""
Shared look and SEO markup for every page under pranavarya.com/blog/.

Used by:
  scripts/generate_post.py  (daily bot: renders the new post, then rebuilds
                             the blog index and sitemap from blog/posts.json)
  scripts/rebuild_blog.py   (re-renders every existing post with this theme)

blog/posts.json is the single source of truth for post metadata
(newest first). Styling lives in /assets/blog.css and /assets/blog.js so
every blog page shares one cached file.
"""

import datetime
import html
import json
import re

SITE = "https://pranavarya.com"
WA_NUMBER = "491744257711"
FONTS = ("https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
         "&family=Inter+Tight:wght@300;400;500;600;700&display=swap")
DEFAULT_OG = f"{SITE}/assets/og.jpg"
ASSET_V = "3"  # bump to bust the CSS/JS cache after style changes

PERSON = {
    "@type": "Person", "@id": f"{SITE}/#person", "name": "Pranav Arya",
    "url": f"{SITE}/", "image": f"{SITE}/pranavarya.jpg",
    "jobTitle": "Filmmaker, Creative Director and AI Video Producer",
    "sameAs": ["https://instagram.com/iampranavarya", "https://t.me/iampranavarya28"],
}
ORG = {
    "@type": "Organization", "@id": f"{SITE}/#organization",
    "name": "PAFP | Pranav Arya Film Production", "url": f"{SITE}/",
    "logo": {"@type": "ImageObject", "url": f"{SITE}/pranavarya.jpg"},
}


# ---------------------------------------------------------------- helpers
def esc(s):
    """Escape text for HTML (titles and descriptions may contain & or quotes)."""
    return html.escape(html.unescape(str(s)), quote=True)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", html.unescape(s).lower()).strip("-")


def human_date(iso):
    d = datetime.date.fromisoformat(iso)
    return d.strftime("%B %-d, %Y")


def word_count(body_html):
    return len(re.sub(r"<[^>]+>", " ", body_html).split())


def read_minutes(body_html):
    return max(1, round(word_count(body_html) / 230))


def jsonld(obj):
    # "</" must never appear raw inside a script tag
    return json.dumps(obj, ensure_ascii=False, indent=1).replace("</", "<\\/")


def wa_link(text):
    from urllib.parse import quote
    return f"https://wa.me/{WA_NUMBER}?text={quote(text)}"


# ---------------------------------------------------------------- shared chrome
def head(title, description, canonical, og_type, og_image, ld, extra=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<meta name="author" content="Pranav Arya">
<meta name="theme-color" content="#060509">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/pranavarya.jpg" type="image/jpeg">
<link rel="alternate" type="application/rss+xml" title="PAFP Blog" href="{SITE}/blog/feed.xml">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="PAFP | Pranav Arya Film Production">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{esc(title.replace(' | PAFP Blog', ''))}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title.replace(' | PAFP Blog', ''))}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{og_image}">
{extra}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="/assets/blog.css?v={ASSET_V}">
<script type="application/ld+json">
{jsonld(ld)}
</script>
</head>
"""


NAV = """<body>
<a class="skip" href="#content">Skip to content</a>
<div class="aurora" aria-hidden="true"><i></i><i></i><i></i></div>
<div class="grain" aria-hidden="true"></div>
<div class="progress" aria-hidden="true"><i id="progress"></i></div>

<nav class="top wrap" id="nav" aria-label="Main">
  <a href="/" class="logo" aria-label="PAFP home"><b></b>PAFP <small>Pranav Arya</small></a>
  <div class="nav-links">
    <a href="/#work">Work</a>
    <a href="/#process">Process</a>
    <a href="/#about">About</a>
    <a href="/blog/" aria-current="page">Blog</a>
    <a href="/#media-kit">Media Kit</a>
  </div>
  <a href="/#contact" class="btn btn-glow nav-cta">Start a project</a>
  <button class="burger" id="burger" aria-label="Open menu" aria-expanded="false" aria-controls="menu"><span></span><span></span></button>
</nav>

<div id="menu" aria-hidden="true">
  <a href="/#work">Work</a>
  <a href="/#process">Process</a>
  <a href="/#about">About</a>
  <a href="/#media-kit">Media Kit</a>
  <a href="/blog/">Blog</a>
  <a href="/#contact" class="btn btn-glow">Start a project</a>
</div>
"""

WA_ICON = ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.64.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.03-.52-.07-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.21 3.08c.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.22 1.36.19 1.87.12.57-.09 1.76-.72 2.01-1.41.25-.7.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35zM12.05 21.5h-.01a9.4 9.4 0 0 1-4.8-1.32l-.34-.2-3.57.94.95-3.48-.22-.36a9.4 9.4 0 0 1-1.44-5.02c0-5.2 4.23-9.43 9.44-9.43 2.52 0 4.89.98 6.67 2.77a9.37 9.37 0 0 1 2.76 6.67c0 5.2-4.24 9.43-9.44 9.43zm8.03-17.46A11.3 11.3 0 0 0 12.05.71C5.79.71.7 5.8.7 12.06c0 2 .52 3.95 1.52 5.67L.6 23.3l5.7-1.5a11.3 11.3 0 0 0 5.74 1.47h.01c6.26 0 11.35-5.09 11.35-11.35 0-3.03-1.18-5.88-3.32-8.03z"/></svg>')

ARROW = ('<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">'
         '<path d="M3 8h10M9 4l4 4-4 4"/></svg>')

FOOTER = f"""
<footer class="site">
  <span>&copy; {datetime.date.today().year} PAFP &middot; Pranav Arya Film Production &middot; Berlin</span>
  <div class="foot-links"><a href="/">Home</a><a href="/blog/">Blog</a><a href="/#media-kit">Media Kit</a><a href="https://instagram.com/iampranavarya" target="_blank" rel="noopener">Instagram</a><a href="https://t.me/iampranavarya28" target="_blank" rel="noopener">Telegram</a><a href="mailto:collab.pranavarya@gmail.com">Email</a></div>
</footer>

<a class="wa-float" href="{wa_link('Hi Pranav, I found you through your blog on pranavarya.com and would like to talk about a project.')}" target="_blank" rel="noopener" aria-label="Chat with Pranav on WhatsApp">{WA_ICON}</a>

<script src="/assets/blog.js?v={ASSET_V}" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- cards
def thumb(post, cls="pc-media", eager=False):
    cat = esc(post.get("category") or "Blog")
    if post.get("image"):
        load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
        return (f'<div class="{cls}"><img src="{post["image"]}" alt="{esc(post["title"])}" '
                f'width="1200" height="675" {load}></div>')
    hue = sum(ord(c) for c in post["filename"]) % 360
    return (f'<div class="{cls} ph" style="--h:{hue}" aria-hidden="true">'
            f'<span class="serif">{cat}</span></div>')


def card(post, heading="h2", eager=False):
    cat = post.get("category") or "Blog"
    return f"""<a href="/blog/{post['filename']}" class="post-card" data-cat="{slugify(cat)}">
  {thumb(post, eager=eager)}
  <div class="pc-body">
    <span class="pc-meta">{esc(cat)} &middot; <time datetime="{post['date']}">{human_date(post['date'])}</time></span>
    <{heading}>{esc(post['title'])}</{heading}>
    <p>{esc(post['meta_description'])}</p>
    <span class="pc-more">Read article {ARROW}</span>
  </div>
</a>
"""


def pick_related(manifest, post, n=3):
    tags = set(post.get("tags") or [])
    others = [p for p in manifest if p["filename"] != post["filename"]]

    def score(p):
        shared = len(tags & set(p.get("tags") or []))
        same_cat = 1 if p.get("category") == post.get("category") else 0
        # closeness in time as a gentle tie-breaker
        gap = abs((datetime.date.fromisoformat(p["date"]) -
                   datetime.date.fromisoformat(post["date"])).days)
        return (shared * 3 + same_cat * 2, -gap)

    return sorted(others, key=score, reverse=True)[:n]


# ---------------------------------------------------------------- post page
def render_post(post, body_html, manifest):
    """post: dict with filename, title, meta_description, tags, date, category, image."""
    canonical = f"{SITE}/blog/{post['filename']}"
    cat = post.get("category") or "AI & Entertainment"
    img_abs = f"{SITE}{post['image']}" if post.get("image") else DEFAULT_OG
    img_w, img_h = (1200, 675) if post.get("image") else (1200, 630)
    words = word_count(body_html)
    mins = read_minutes(body_html)
    tags = post.get("tags") or []
    date = post["date"]
    modified = post.get("modified") or date

    ld = {"@context": "https://schema.org", "@graph": [
        {
            "@type": "BlogPosting", "@id": f"{canonical}#article",
            "headline": html.unescape(post["title"]),
            "description": html.unescape(post["meta_description"]),
            "image": {"@type": "ImageObject", "url": img_abs, "width": img_w, "height": img_h},
            "datePublished": date, "dateModified": modified,
            "author": PERSON, "publisher": ORG,
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
            "isPartOf": {"@type": "Blog", "@id": f"{SITE}/blog/#blog", "name": "PAFP Blog"},
            "articleSection": html.unescape(cat),
            "keywords": ", ".join(tags),
            "wordCount": words, "inLanguage": "en",
        },
        {
            "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{SITE}/blog/"},
                {"@type": "ListItem", "position": 3, "name": html.unescape(post["title"]), "item": canonical},
            ],
        },
    ]}

    extra = (f'<meta property="og:image:width" content="{img_w}">\n'
             f'<meta property="og:image:height" content="{img_h}">\n'
             f'<meta property="og:image:alt" content="{esc(post["title"])}">\n'
             f'<meta property="article:published_time" content="{date}">\n'
             f'<meta property="article:modified_time" content="{modified}">\n'
             f'<meta property="article:author" content="{SITE}/">\n'
             f'<meta property="article:section" content="{esc(cat)}">\n'
             + "".join(f'<meta property="article:tag" content="{esc(t)}">\n' for t in tags))
    if post.get("image"):
        extra += f'<link rel="preload" as="image" href="{post["image"]}" fetchpriority="high">\n'

    hero = ""
    if post.get("image"):
        hero = (f'<figure class="post-hero">'
                f'<img src="{post["image"]}" alt="{esc(post["title"])}" width="1200" height="675" '
                f'fetchpriority="high" loading="eager" decoding="async"></figure>')

    tag_html = "".join(f"<li>#{esc(t)}</li>" for t in tags)
    related = "".join(card(p, heading="h3") for p in pick_related(manifest, post))

    out = head(f"{post['title']} | PAFP Blog", post["meta_description"], canonical,
               "article", img_abs, ld, extra)
    out += NAV
    out += f"""
<main id="content">
<article class="post">
  <header class="post-head wrap">
    <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/blog/">Blog</a></li><li aria-current="page">{esc(cat)}</li></ol></nav>
    <span class="eyebrow">{esc(cat)}</span>
    <h1>{esc(post['title'])}</h1>
    <p class="dek">{esc(post['meta_description'])}</p>
    <div class="byline">
      <img src="/pranavarya.jpg" alt="Pranav Arya" width="44" height="44" loading="eager">
      <div><a href="/#about" rel="author"><b>Pranav Arya</b></a><span><time datetime="{date}">{human_date(date)}</time> &middot; {mins} min read</span></div>
    </div>
  </header>
  {hero}
  <div class="prose wrap">
<!-- post-body -->
{body_html.strip()}
<!-- /post-body -->
  </div>
  <div class="post-foot wrap">
    <ul class="tags" aria-label="Topics">{tag_html}</ul>
    <div class="share">
      <span>Share</span>
      <a href="https://www.linkedin.com/sharing/share-offsite/?url={canonical}" target="_blank" rel="noopener">LinkedIn</a>
      <a href="https://twitter.com/intent/tweet?url={canonical}" target="_blank" rel="noopener">X</a>
      <a href="https://wa.me/?text={canonical}" target="_blank" rel="noopener">WhatsApp</a>
      <button type="button" class="copy" data-url="{canonical}">Copy link</button>
    </div>
  </div>
</article>

<section class="author-card wrap" aria-label="About the author">
  <div class="ac-inner">
    <img src="/pranavarya.jpg" alt="Pranav Arya, filmmaker and founder of PAFP" width="96" height="96" loading="lazy">
    <div>
      <span class="eyebrow">Written by</span>
      <h2>Pranav Arya</h2>
      <p>Berlin-based filmmaker and founder of PAFP. With 10+ years behind the camera, his team shoots <a href="/#work">events, brands, fashion, food and travel</a> worldwide, and he makes <a href="/#work">cinematic AI films</a> for businesses in every industry. Clients include Formula 1, Token2049 and OMR.</p>
    </div>
  </div>
</section>

<section class="cta-band wrap" aria-label="Work together">
  <div class="cta-inner">
    <span class="eyebrow">Work together</span>
    <h2>Need a film <span class="serif grad">for your brand?</span></h2>
    <p>Real shoots on location by our team, or AI films made from scratch. Tell us what you have in mind and we will get back to you within a day.</p>
    <div class="cta-btns">
      <a href="/#contact" class="btn btn-glow">Start a project {ARROW}</a>
      <a href="{wa_link('Hi Pranav, I just read ' + html.unescape(post['title']) + ' on your blog and would like to talk about a project.')}" class="btn btn-ghost" target="_blank" rel="noopener">{WA_ICON} WhatsApp</a>
    </div>
  </div>
</section>

<section class="related wrap" aria-labelledby="rel-h">
  <div class="rel-head"><span class="eyebrow">Keep reading</span><h2 id="rel-h">More from the blog</h2></div>
  <div class="rel-grid">
{related}  </div>
  <a href="/blog/" class="btn btn-ghost all-posts">All articles {ARROW}</a>
</section>
</main>
"""
    out += FOOTER
    return out


# ---------------------------------------------------------------- index page
def render_index(manifest):
    canonical = f"{SITE}/blog/"
    desc = ("Notes on AI filmmaking, AI video models, cameras, smart glasses, editing and "
            "production craft from Berlin filmmaker Pranav Arya and the PAFP team.")
    cats = []
    for p in manifest:
        c = p.get("category") or "Blog"
        if c not in cats:
            cats.append(c)
    counts = {c: sum(1 for p in manifest if (p.get("category") or "Blog") == c) for c in cats}
    cats.sort(key=lambda c: -counts[c])

    ld = {"@context": "https://schema.org", "@graph": [
        {
            "@type": "Blog", "@id": f"{SITE}/blog/#blog", "url": canonical,
            "name": "PAFP Blog", "description": desc, "inLanguage": "en",
            "author": {"@id": f"{SITE}/#person"}, "publisher": ORG,
            "blogPost": [{
                "@type": "BlogPosting", "headline": html.unescape(p["title"]),
                "url": f"{SITE}/blog/{p['filename']}", "datePublished": p["date"],
                **({"image": f"{SITE}{p['image']}"} if p.get("image") else {}),
            } for p in manifest[:40]],
        },
        {
            "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": "Blog", "item": canonical},
            ],
        },
    ]}

    chips = '<button type="button" class="chip on" data-f="all">All <i>%d</i></button>' % len(manifest)
    chips += "".join(f'<button type="button" class="chip" data-f="{slugify(c)}">{esc(c)} <i>{counts[c]}</i></button>'
                     for c in cats)
    cards = "".join(card(p, eager=(i == 0)) for i, p in enumerate(manifest))

    out = head("Blog: AI Filmmaking, Cameras and Production Notes | PAFP", desc, canonical,
               "website", DEFAULT_OG, ld,
               '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n')
    out += NAV
    out += f"""
<main id="content">
<header class="blog-hero wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li aria-current="page">Blog</li></ol></nav>
  <span class="eyebrow">PAFP Blog</span>
  <h1>Notes on <span class="serif grad">AI film,</span> cameras and craft.</h1>
  <p class="dek">What we learn making films for brands, on set and with AI. New models, gear tests, workflows and the trends shaping production, written by Pranav Arya.</p>
</header>

<section class="blog-list wrap" aria-label="All articles">
  <div class="chips" role="toolbar" aria-label="Filter by topic">{chips}</div>
<div class="post-list">
{cards}</div>
</section>

<section class="cta-band wrap" aria-label="Work together">
  <div class="cta-inner">
    <span class="eyebrow">Work together</span>
    <h2>Need a film <span class="serif grad">for your brand?</span></h2>
    <p>Real shoots on location or AI films made from scratch, for brands in every industry.</p>
    <div class="cta-btns">
      <a href="/#contact" class="btn btn-glow">Start a project {ARROW}</a>
      <a href="/#work" class="btn btn-ghost">See the work</a>
    </div>
  </div>
</section>
</main>
"""
    out += FOOTER
    return out


# ---------------------------------------------------------------- sitemap + feed
def render_sitemap(manifest, home_lastmod=None):
    latest = manifest[0]["date"] if manifest else datetime.date.today().isoformat()
    home_lastmod = home_lastmod or datetime.date.today().isoformat()
    rows = [
        f"  <url>\n    <loc>{SITE}/</loc>\n    <lastmod>{home_lastmod}</lastmod>\n"
        f"    <image:image><image:loc>{SITE}/assets/og.jpg</image:loc></image:image>\n  </url>",
        f"  <url>\n    <loc>{SITE}/blog/</loc>\n    <lastmod>{latest}</lastmod>\n  </url>",
    ]
    for p in manifest:
        img = (f"\n    <image:image><image:loc>{SITE}{p['image']}</image:loc></image:image>"
               if p.get("image") else "")
        rows.append(f"  <url>\n    <loc>{SITE}/blog/{p['filename']}</loc>\n"
                    f"    <lastmod>{p.get('modified') or p['date']}</lastmod>{img}\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def render_feed(manifest, n=30):
    from email.utils import format_datetime
    def rfc(d):
        return format_datetime(datetime.datetime.fromisoformat(d + "T09:00:00+00:00"))
    items = "".join(
        f"""  <item>
    <title>{esc(p['title'])}</title>
    <link>{SITE}/blog/{p['filename']}</link>
    <guid isPermaLink="true">{SITE}/blog/{p['filename']}</guid>
    <pubDate>{rfc(p['date'])}</pubDate>
    <category>{esc(p.get('category') or 'Blog')}</category>
    <description>{esc(p['meta_description'])}</description>
  </item>
""" for p in manifest[:n])
    last = rfc(manifest[0]["date"]) if manifest else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>PAFP Blog</title>
  <link>{SITE}/blog/</link>
  <atom:link href="{SITE}/blog/feed.xml" rel="self" type="application/rss+xml"/>
  <description>Notes on AI filmmaking, cameras and production craft from Pranav Arya.</description>
  <language>en</language>
  <lastBuildDate>{last}</lastBuildDate>
{items}</channel>
</rss>
"""

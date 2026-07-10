#!/usr/bin/env python3
"""
Daily AI-in-entertainment blog post generator for pranavarya.com/blog/
Pipeline: research (web search) -> draft -> humanize/polish -> publish as HTML
Runs via GitHub Actions on a daily schedule. See .github/workflows/daily-blog.yml
"""

import os
import re
import sys
import json
import time
import random
import datetime
from pathlib import Path

import anthropic

# ---------- CONFIG ----------
MODEL = os.environ.get("BLOG_MODEL", "claude-sonnet-5")
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
BLOG_INDEX_PATH = BLOG_DIR / "index.html"
SITE_BASE_URL = "https://pranavarya.com"

# Publish-time randomization: the GitHub Actions workflow triggers this script
# hourly across WINDOW_START_HOUR-WINDOW_END_HOUR (UTC). Each run checks whether
# today's post already exists; if not, it uses reservoir sampling so exactly one
# of the remaining hourly check-ins gets chosen at random to actually publish,
# then sleeps a random number of minutes within that hour. Net effect: one post
# per day, at a different unpredictable time each day, instead of a fixed cron time.
WINDOW_START_HOUR = 6   # 06:00 UTC ~ 07:00-08:00 Berlin depending on DST
WINDOW_END_HOUR = 21    # 21:00 UTC ~ 22:00-23:00 Berlin depending on DST

if not API_KEY:
    print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

TODAY = datetime.date.today()
TODAY_STR = TODAY.strftime("%Y-%m-%d")
TODAY_HUMAN = TODAY.strftime("%B %d, %Y")

# Rotating topic angles so consecutive days don't read as templated/identical.
# The research step still finds whatever is actually newsworthy that day;
# this just biases the angle when there's no single dominant news story.
TOPIC_ANGLES = [
    "a breaking model release or major update in AI video/image generation",
    "a practical how-to tutorial for a specific AI filmmaking workflow",
    "a deep dive on prompt techniques or tricks for a specific tool",
    "an analysis of a trend or shift in AI-powered entertainment production",
    "a comparison of two or more AI tools relevant to filmmakers",
    "an explainer on a technique (e.g. frame chaining, motion graphics, AI avatars)",
    "curated roundup of the week's notable AI entertainment news",
]
angle_index = TODAY.toordinal() % len(TOPIC_ANGLES)
TODAY_ANGLE = TOPIC_ANGLES[angle_index]


# ---------- TIMING GATE ----------
def already_published_today():
    if not BLOG_DIR.exists():
        return False
    return any(f.name.startswith(TODAY_STR) for f in BLOG_DIR.glob("*.html"))


def should_publish_this_run():
    """Reservoir sampling across the remaining hourly check-ins today: gives a
    uniformly random hour, then adds a random minute-level delay so it never
    lands on a suspiciously exact clock time."""
    now_utc = datetime.datetime.utcnow()
    current_hour = now_utc.hour

    if current_hour < WINDOW_START_HOUR or current_hour > WINDOW_END_HOUR:
        print(f"Outside publish window ({WINDOW_START_HOUR}-{WINDOW_END_HOUR} UTC). Skipping.")
        return False

    if already_published_today():
        print(f"Already published a post today ({TODAY_STR}). Skipping this check-in.")
        return False

    remaining_checks = WINDOW_END_HOUR - current_hour + 1
    probability = 1.0 / remaining_checks
    roll = random.random()
    chosen = roll < probability
    print(f"Hour {current_hour} UTC: {remaining_checks} check-ins left today, "
          f"probability {probability:.2f}, roll {roll:.2f} -> {'PUBLISH' if chosen else 'skip'}")

    if chosen:
        jitter_seconds = random.randint(0, 55 * 60)  # random delay within the hour
        jitter_minutes = jitter_seconds // 60
        print(f"Selected this hour to publish. Sleeping {jitter_minutes} min for natural timing...")
        time.sleep(jitter_seconds)

    return chosen


def call_claude(system, user_content, tools=None, max_tokens=4000):
    kwargs = dict(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    if tools:
        kwargs["tools"] = tools
    resp = client.messages.create(**kwargs)
    # Concatenate all text blocks (search results interleave tool_use/tool_result blocks)
    text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "\n".join(text_parts).strip()


# ---------- STEP 1: RESEARCH ----------
def research():
    system = (
        "You are a research assistant for a filmmaker's blog about AI in the "
        "entertainment industry. Use web search to find genuinely current, "
        "specific, and interesting material -- not generic background info."
    )
    user = f"""Search the web for the latest news, releases, and discussion in AI-powered
entertainment production as of {TODAY_HUMAN}. Focus on: new or updated AI video/image
models (e.g. Kling, Runway, Veo, Sora, Higgsfield, Midjourney, HeyGen, ElevenLabs),
notable AI-generated films/campaigns getting attention, prompt techniques, workflow
tricks, or tutorials that are circulating right now.

Today's angle should lean toward: {TODAY_ANGLE}

Return a concise research brief (bullet points) with the 3-5 most useful, specific,
sourced findings you can use to write an original blog post. Include names, version
numbers, and concrete details -- avoid vague generalities."""
    return call_claude(
        system,
        user,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        max_tokens=3000,
    )


# ---------- STEP 2: DRAFT ----------
def draft(research_brief):
    system = (
        "You are writing for Pranav Arya's (PAFP) blog -- a Berlin-based filmmaker and "
        "AI video producer who works hands-on with tools like Higgsfield, Kling, Runway, "
        "and Nano Banana Pro on real client projects (F1, Web3 summits, brand campaigns). "
        "Write with the voice of someone who actually uses these tools daily, not a "
        "generic tech blogger. Be specific, opinionated where warranted, and useful."
    )
    user = f"""Using this research brief, write an original 700-1000 word blog post about
AI in the entertainment industry for today, {TODAY_HUMAN}.

RESEARCH BRIEF:
{research_brief}

Structure requirements:
- Open with a specific hook (a fact, a claim, a question) -- not "In today's world..."
- Structure with 2-4 H2-style subheadings that break up the content logically
- Include at least one concrete, actionable takeaway (a tip, a prompt idea, a workflow note)
- Write with a real point of view -- react to things, don't just report them neutrally.
  "This is genuinely impressive but also a little unsettling" beats "This is impressive."
- End on a specific closing thought, not a summary recap paragraph

Hard rules against AI-sounding writing:
- NEVER use em dashes (—) or en dashes for dramatic pauses. Use a period, comma, or
  parenthetical instead. Zero em dashes in the entire piece.
- Vary sentence length aggressively. Mix short, punchy sentences with longer ones that
  take their time. Do not settle into an even, mid-length rhythm.
- Ban these words/phrases entirely: "testament", "landscape" (as in "the AI landscape"),
  "showcasing", "serves as", "boasts", "delve", "dive into", "unlock", "seamless",
  "robust", "cutting-edge", "game-changer", "in today's fast-paced world", "moreover",
  "furthermore", "additionally" (as a paragraph opener), "it's not just X, it's Y",
  "in conclusion", "the future looks bright", "the possibilities are endless"
- No "rule of three" list padding (e.g. "faster, smarter, and more efficient") unless
  each item is doing real, distinct work
- No inflated significance framing ("marks a pivotal moment", "represents a turning point")
  -- state what actually happened instead

Output ONLY the article body in clean HTML using <p>, <h2>, <ul>/<li>, and <strong> tags
as appropriate. No <html>, <head>, <body>, or <h1> tags -- just the inner content."""
    return call_claude(system, user, max_tokens=3000)


# ---------- STEP 3: HUMANIZE / POLISH ----------
BANNED_PHRASES = [
    "testament", "showcasing", "serves as", "boasts", "delve", "dive into",
    "unlock", "seamless", "robust", "cutting-edge", "game-changer", "game changer",
    "moreover", "furthermore", "in conclusion", "the future looks bright",
    "possibilities are endless", "pivotal moment", "turning point",
    "fast-paced world", "it's not just", "in today's",
]


def humanize(draft_html):
    system = (
        "You are a sharp human editor polishing a blog draft. Your job is to remove "
        "every trace of AI-generated writing patterns -- em dashes used for dramatic "
        "pauses, generic AI vocabulary, uniform sentence rhythm, formulaic openers and "
        "closers -- while keeping every factual claim intact and making it read like a "
        "specific person wrote it in one sitting."
    )
    user = f"""Edit this draft. Apply every rule below without exception:

1. DELETE every em dash (—) or en dash used as a pause. Replace each with a period,
   comma, or parenthetical rewrite. Search the text for the — character specifically
   and remove all instances.
2. Rewrite any sentence containing these words/phrases, replacing with plain language:
   {", ".join(BANNED_PHRASES)}
3. Vary sentence length hard -- if you see three sentences in a row of similar length,
   break the pattern. Mix short and long deliberately.
4. Remove any "rule of three" list that's just padding (three adjectives/nouns doing
   the same job). Cut to what's actually distinct.
5. If a paragraph reports a fact neutrally with no reaction, add a genuine point of
   view to at least one paragraph in the piece.
6. Read it as if aloud -- if any sentence sounds like marketing copy, flatten it to
   something a person would actually say.

Keep the HTML tags intact and keep it roughly the same length. Do not add new claims,
facts, or numbers that weren't in the original.

DRAFT:
{draft_html}

Output ONLY the edited HTML, nothing else."""
    return call_claude(system, user, max_tokens=3000)


# ---------- STEP 3B: SELF-AUDIT PASS (catches what step 3 missed) ----------
def audit_and_fix(body_html):
    audit_system = (
        "You are a blunt editor whose only job is spotting residual AI-writing tells."
    )
    audit_user = f"""What makes the following text sound obviously AI-generated, if
anything? List specific tells briefly (em dashes, vocabulary, rhythm, structure).
If it genuinely reads as human-written, say "CLEAN" and nothing else.

TEXT:
{body_html}"""
    critique = call_claude(audit_system, audit_user, max_tokens=600)

    if critique.strip().upper().startswith("CLEAN"):
        return body_html

    fix_system = "You are a sharp human editor making a final pass on a blog draft."
    fix_user = f"""A previous review of this draft found these remaining AI-writing tells:

{critique}

Fix every issue listed. Keep HTML tags intact, keep the same approximate length,
don't add new facts. Output ONLY the corrected HTML.

DRAFT:
{body_html}"""
    return call_claude(fix_system, fix_user, max_tokens=3000)


def strip_stray_em_dashes(text):
    """Belt-and-suspenders: force any surviving em/en dashes to a period, since this
    is the single most common tell readers notice first."""
    text = re.sub(r"\s*[—–]\s*", ". ", text)
    text = re.sub(r"\.\s*\.", ".", text)  # clean up any doubled periods from the swap
    # capitalize the letter immediately following each ". " we just inserted
    text = re.sub(r"(\.\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text


# ---------- STEP 4: METADATA ----------
def generate_metadata(body_html):
    system = "You generate concise, accurate metadata for a blog post."
    user = f"""Given this blog post body, output ONLY a JSON object (no markdown fences,
no commentary) with these exact keys:
- "title": a compelling title, under 65 characters
- "meta_description": under 155 characters, no quotes inside
- "slug": lowercase-hyphenated, no dates, 3-6 words, url-safe
- "tags": array of 2-4 short lowercase tags (e.g. "kling", "prompts", "news", "tutorial")

BODY:
{body_html[:2000]}"""
    raw = call_claude(system, user, max_tokens=500)
    raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Safe fallback so the pipeline never hard-fails on a parsing hiccup
        return {
            "title": f"AI in Entertainment — {TODAY_HUMAN}",
            "meta_description": "Daily notes on AI tools, models, and techniques in film and content production.",
            "slug": f"ai-entertainment-{TODAY_STR}",
            "tags": ["ai", "filmmaking"],
        }


# ---------- STEP 5: BUILD HTML PAGE ----------
POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title} | PAFP Blog</title>
<meta name="description" content="{meta_description}"/>
<meta name="robots" content="index, follow"/>
<link rel="canonical" href="{canonical_url}"/>
<meta property="og:type" content="article"/>
<meta property="og:url" content="{canonical_url}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{meta_description}"/>
<meta property="og:image" content="{site_base}/pranavarya.jpg"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{title}"/>
<meta name="twitter:description" content="{meta_description}"/>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,200;0,400;0,700;0,900;1,900&family=Space+Grotesk:wght@300;400;500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet"/>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": {title_json},
  "description": {meta_description_json},
  "datePublished": "{date_iso}",
  "author": {{"@type": "Person", "name": "Pranav Arya", "url": "{site_base}/"}},
  "publisher": {{"@type": "Organization", "name": "PAFP", "url": "{site_base}/"}}
}}
</script>
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{--ink:#0C0B0A;--paper:#F2F0EB;--red:#E63A1E;--gray:#8A887F;
--font-head:'Barlow Condensed',sans-serif;--font-body:'Space Grotesk',sans-serif;--font-mono:'Space Mono',monospace}}
body{{background:var(--ink);color:var(--paper);font-family:var(--font-body);font-weight:300;line-height:1.8;max-width:760px;margin:0 auto;padding:64px 24px 100px}}
a{{color:var(--red)}}
.back{{font-family:var(--font-mono);font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;text-decoration:none;color:var(--gray);display:inline-block;margin-bottom:40px}}
.back:hover{{color:var(--red)}}
.eyebrow{{font-family:var(--font-mono);font-size:0.5rem;letter-spacing:0.24em;color:var(--red);text-transform:uppercase;margin-bottom:16px}}
h1{{font-family:var(--font-head);font-size:clamp(2.2rem,6vw,3.6rem);font-weight:900;line-height:1;text-transform:uppercase;margin-bottom:20px}}
.meta{{font-family:var(--font-mono);font-size:0.55rem;letter-spacing:0.1em;color:var(--gray);text-transform:uppercase;margin-bottom:48px}}
article h2{{font-family:var(--font-head);font-size:1.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.02em;margin:40px 0 16px}}
article p{{margin-bottom:20px;color:rgba(242,240,235,0.85);font-size:1.02rem}}
article ul{{margin:0 0 20px 20px}}
article li{{margin-bottom:8px;color:rgba(242,240,235,0.85)}}
article strong{{color:var(--red);font-weight:500}}
footer{{margin-top:64px;padding-top:24px;border-top:1px solid rgba(255,255,255,0.08);font-family:var(--font-mono);font-size:0.5rem;letter-spacing:0.14em;color:var(--gray);text-transform:uppercase}}
footer a{{color:var(--gray);text-decoration:none}}
footer a:hover{{color:var(--red)}}
</style>
</head>
<body>
<a href="/blog/" class="back">&larr; Back to Blog</a>
<div class="eyebrow">AI &middot; Entertainment &middot; {date_human}</div>
<h1>{title}</h1>
<div class="meta">By Pranav Arya &middot; PAFP &middot; {tags_display}</div>
<article>
{body}
</article>
<footer>
  <p>&copy; 2026 Pranav Arya Film Production &middot; <a href="/">pranavarya.com</a> &middot; <a href="https://instagram.com/iampranavarya" target="_blank" rel="noopener noreferrer">Instagram</a></p>
</footer>
</body>
</html>
"""


def build_post_html(title, meta_description, body_html, tags, canonical_url):
    return POST_TEMPLATE.format(
        title=title,
        meta_description=meta_description,
        title_json=json.dumps(title),
        meta_description_json=json.dumps(meta_description),
        canonical_url=canonical_url,
        site_base=SITE_BASE_URL,
        date_iso=TODAY.isoformat(),
        date_human=TODAY_HUMAN,
        body=body_html,
        tags_display=" &middot; ".join(f"#{t}" for t in tags),
    )


# ---------- STEP 6: UPDATE BLOG INDEX ----------
CARD_TEMPLATE = """<a href="/blog/{filename}" class="post-card">
  <span class="post-date">{date_human}</span>
  <h2>{title}</h2>
  <p>{meta_description}</p>
  <span class="post-tags">{tags_display}</span>
</a>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>AI &amp; Entertainment Blog | PAFP</title>
<meta name="description" content="Daily notes on AI models, news, tutorials, and prompt tricks for AI-powered filmmaking and entertainment production, from Pranav Arya (PAFP)."/>
<link rel="canonical" href="https://pranavarya.com/blog/"/>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,200;0,400;0,700;0,900;1,900&family=Space+Grotesk:wght@300;400;500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{--ink:#0C0B0A;--paper:#F2F0EB;--red:#E63A1E;--gray:#8A887F;
--font-head:'Barlow Condensed',sans-serif;--font-body:'Space Grotesk',sans-serif;--font-mono:'Space Mono',monospace}}
body{{background:var(--ink);color:var(--paper);font-family:var(--font-body);font-weight:300;max-width:900px;margin:0 auto;padding:64px 24px 100px}}
.back{{font-family:var(--font-mono);font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;text-decoration:none;color:var(--gray);display:inline-block;margin-bottom:40px}}
.back:hover{{color:var(--red)}}
.eyebrow{{font-family:var(--font-mono);font-size:0.5rem;letter-spacing:0.24em;color:var(--red);text-transform:uppercase;margin-bottom:16px}}
h1{{font-family:var(--font-head);font-size:clamp(2.5rem,7vw,4.5rem);font-weight:900;line-height:0.9;text-transform:uppercase;margin-bottom:16px}}
.sub{{color:rgba(242,240,235,0.6);max-width:520px;margin-bottom:56px;line-height:1.7}}
.post-list{{display:flex;flex-direction:column;gap:0}}
.post-card{{display:block;text-decoration:none;color:var(--paper);padding:28px 0;border-bottom:1px solid rgba(255,255,255,0.08);transition:padding-left 0.2s}}
.post-card:hover{{padding-left:12px}}
.post-date{{font-family:var(--font-mono);font-size:0.46rem;letter-spacing:0.18em;color:var(--red);text-transform:uppercase}}
.post-card h2{{font-family:var(--font-head);font-size:1.6rem;font-weight:700;text-transform:uppercase;margin:8px 0 8px;transition:color 0.2s}}
.post-card:hover h2{{color:var(--red)}}
.post-card p{{color:rgba(242,240,235,0.55);font-size:0.9rem;margin-bottom:8px}}
.post-tags{{font-family:var(--font-mono);font-size:0.44rem;letter-spacing:0.12em;color:var(--gray);text-transform:uppercase}}
</style>
</head>
<body>
<a href="/" class="back">&larr; Back to Home</a>
<div class="eyebrow">PAFP Blog</div>
<h1>AI &amp; Entertainment</h1>
<p class="sub">Daily notes on models, news, tutorials, and prompt tricks in AI-powered filmmaking and content production.</p>
<div class="post-list">
{posts}
</div>
</body>
</html>
"""


def update_blog_index(filename, title, meta_description, tags):
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    card = CARD_TEMPLATE.format(
        filename=filename,
        date_human=TODAY_HUMAN,
        title=title,
        meta_description=meta_description,
        tags_display=" &middot; ".join(f"#{t}" for t in tags),
    )

    if BLOG_INDEX_PATH.exists():
        existing = BLOG_INDEX_PATH.read_text(encoding="utf-8")
        marker_start = existing.find('<div class="post-list">')
        marker_end = existing.find("</div>", marker_start)
        if marker_start != -1 and marker_end != -1:
            insert_at = existing.index("\n", marker_start) + 1
            new_content = existing[:insert_at] + card + existing[insert_at:]
            BLOG_INDEX_PATH.write_text(new_content, encoding="utf-8")
            return

    # First run: no index exists yet, or marker not found -- build fresh
    BLOG_INDEX_PATH.write_text(INDEX_TEMPLATE.format(posts=card), encoding="utf-8")


# ---------- STEP 7: UPDATE SITEMAP ----------
def update_sitemap(canonical_url):
    entry = f"""  <url>
    <loc>{canonical_url}</loc>
    <lastmod>{TODAY.isoformat()}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
"""
    if SITEMAP_PATH.exists():
        content = SITEMAP_PATH.read_text(encoding="utf-8")
        if "</urlset>" in content:
            content = content.replace("</urlset>", entry + "</urlset>")
            SITEMAP_PATH.write_text(content, encoding="utf-8")
            return
    # Fallback: create a minimal sitemap if missing entirely
    fresh = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{TODAY.isoformat()}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
{entry}</urlset>
"""
    SITEMAP_PATH.write_text(fresh, encoding="utf-8")


# ---------- MAIN ----------
def main():
    # Manual test runs (workflow_dispatch) always publish immediately, no waiting.
    # Scheduled runs go through the randomized timing gate.
    is_manual_trigger = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    if not is_manual_trigger:
        if not should_publish_this_run():
            print("Not publishing this run. Exiting cleanly.")
            return
    else:
        if already_published_today():
            print(f"Note: a post for {TODAY_STR} already exists, but proceeding "
                  f"anyway since this was manually triggered.")

    print(f"[{TODAY_STR}] Researching (angle: {TODAY_ANGLE})...")
    brief = research()
    print("Research brief:\n", brief[:500], "...\n")

    print("Drafting article...")
    draft_html = draft(brief)

    print("Humanizing / polishing...")
    final_body = humanize(draft_html)

    print("Running self-audit pass for remaining AI tells...")
    final_body = audit_and_fix(final_body)

    print("Applying hard em-dash safety net...")
    final_body = strip_stray_em_dashes(final_body)

    print("Generating metadata...")
    meta = generate_metadata(final_body)
    title = meta["title"]
    meta_description = meta["meta_description"]
    slug = meta["slug"]
    tags = meta.get("tags", ["ai", "filmmaking"])

    filename = f"{TODAY_STR}-{slug}.html"
    canonical_url = f"{SITE_BASE_URL}/blog/{filename}"

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    post_html = build_post_html(title, meta_description, final_body, tags, canonical_url)
    (BLOG_DIR / filename).write_text(post_html, encoding="utf-8")
    print(f"Wrote {BLOG_DIR / filename}")

    update_blog_index(filename, title, meta_description, tags)
    print("Updated blog/index.html")

    update_sitemap(canonical_url)
    print("Updated sitemap.xml")

    print(f"DONE: {title}")


if __name__ == "__main__":
    main()

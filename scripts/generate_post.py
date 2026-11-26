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
from google import genai as google_genai
from PIL import Image
import io

# ---------- CONFIG ----------
MODEL = os.environ.get("BLOG_MODEL", "claude-sonnet-5")
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gemini-2.5-flash-image")
REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
BLOG_INDEX_PATH = BLOG_DIR / "index.html"
SITE_BASE_URL = "https://pranavarya.com"

WINDOW_START_HOUR = 6
WINDOW_END_HOUR = 21

if not API_KEY:
    print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

TODAY = datetime.date.today()
TODAY_STR = TODAY.strftime("%Y-%m-%d")
TODAY_HUMAN = TODAY.strftime("%B %d, %Y")

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


def already_published_today():
    if not BLOG_DIR.exists():
        return False
    return any(f.name.startswith(TODAY_STR) for f in BLOG_DIR.glob("*.html"))


def should_publish_this_run():
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
        jitter_seconds = random.randint(0, 55 * 60)
        jitter_minutes = jitter_seconds // 60
        print(f"Selected this hour to publish. Sleeping {jitter_minutes} min for natural timing...")
        time.sleep(jitter_seconds)

    return chosen


# ---------- CLAUDE CALL WRAPPER ----------
# Claude Sonnet 5 runs with adaptive thinking ON BY DEFAULT, and thinking tokens
# count against max_tokens. For formulaic rewrite/edit tasks (humanize, audit,
# metadata) we don't need deep reasoning -- we need output. Without disabling
# thinking explicitly, the model can burn the entire max_tokens budget "thinking"
# about how to edit the draft and return zero characters of actual text, which is
# exactly what was happening (stop_reason=max_tokens, content block types=['thinking']).
# Manual budget_tokens control (thinking: {"type": "enabled", "budget_tokens": N})
# is not supported on Sonnet 5 and returns a 400 error -- disabling is the reliable
# lever here. Sonnet 5's tokenizer also produces ~30% more tokens for the same text
# than what these budgets were originally tuned for, so budgets are padded up too.
def strip_code_fences(text):
    """Models sometimes wrap HTML/text output in a markdown code fence
    (```html ... ```) even when explicitly told to output raw HTML only.
    Left unstripped, the literal ```html text gets published straight onto
    the page. Strip a leading fence (with optional language tag) and a
    trailing fence if present."""
    if not text:
        return text
    stripped = text.strip()
    stripped = re.sub(r"^```[a-zA-Z]*\s*\n?", "", stripped)
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def call_claude(system, user_content, tools=None, max_tokens=6000, disable_thinking=True):
    kwargs = dict(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    if disable_thinking:
        kwargs["thinking"] = {"type": "disabled"}
    if tools:
        kwargs["tools"] = tools
    resp = client.messages.create(**kwargs)
    text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    result = "\n".join(text_parts).strip()
    result = strip_code_fences(result)

    if not result:
        block_types = [getattr(b, "type", "?") for b in resp.content]
        print(f"    [call_claude] EMPTY result. stop_reason={resp.stop_reason}, "
              f"content block types={block_types}, max_tokens was {max_tokens}, "
              f"thinking_disabled={disable_thinking}")

    return result


BROKEN_OUTPUT_MARKERS = [
    "no draft text", "please paste", "missing draft", "i don't see any draft",
    "wasn't included", "was not included", "no content was provided",
    "please provide the", "i don't see the", "no text was provided",
]


def looks_broken(text, min_length=300):
    if not text or len(text.strip()) < min_length:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in BROKEN_OUTPUT_MARKERS)


def call_claude_validated(step_name, system, user_content, tools=None, max_tokens=4000,
                           retries=2, disable_thinking=True):
    last_result = ""
    for attempt in range(1, retries + 1):
        result = call_claude(system, user_content, tools=tools, max_tokens=max_tokens,
                              disable_thinking=disable_thinking)
        print(f"  [{step_name}] attempt {attempt}: {len(result)} chars")
        if not looks_broken(result):
            return result
        print(f"  [{step_name}] attempt {attempt} looked broken, retrying with a larger budget...")
        last_result = result
        # If it looked broken because thinking (even disabled) or long input ate the
        # budget, give the retry more room rather than repeating the exact same call.
        max_tokens = int(max_tokens * 1.5)
    raise RuntimeError(
        f"'{step_name}' produced broken/empty output after {retries} attempts. "
        f"Last output preview: {last_result[:300]!r}"
    )


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
    # Research benefits from a little reasoning to synthesize search results well,
    # and it has tool calls in play, so leave thinking on here (Sonnet 5 default).
    return call_claude(
        system,
        user,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        max_tokens=6000,
        disable_thinking=False,
    )


# ---------- STEP 2: DRAFT ----------
def draft(research_brief):
    if looks_broken(research_brief, min_length=50):
        raise RuntimeError(
            f"Research step produced unusable output, aborting before drafting. "
            f"Preview: {research_brief[:300]!r}"
        )

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
    return call_claude_validated("draft", system, user, max_tokens=8000, disable_thinking=True)


# ---------- STEP 3: HUMANIZE / POLISH ----------
BANNED_PHRASES = [
    "testament", "showcasing", "serves as", "boasts", "delve", "dive into",
    "unlock", "seamless", "robust", "cutting-edge", "game-changer", "game changer",
    "moreover", "furthermore", "in conclusion", "the future looks bright",
    "possibilities are endless", "pivotal moment", "turning point",
    "fast-paced world", "it's not just", "in today's",
]


def humanize(draft_html):
    if looks_broken(draft_html):
        raise RuntimeError(
            f"Draft step produced unusable output, aborting before humanizing. "
            f"Preview: {draft_html[:300]!r}"
        )

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
    return call_claude_validated("humanize", system, user, max_tokens=8000, disable_thinking=True)


# ---------- STEP 3B: SELF-AUDIT PASS (catches what step 3 missed) ----------
def audit_and_fix(body_html):
    if looks_broken(body_html):
        raise RuntimeError(
            f"Humanize step produced unusable output, aborting before audit pass. "
            f"Preview: {body_html[:300]!r}"
        )

    audit_system = (
        "You are a blunt editor whose only job is spotting residual AI-writing tells."
    )
    audit_user = f"""What makes the following text sound obviously AI-generated, if
anything? List specific tells briefly (em dashes, vocabulary, rhythm, structure).
If it genuinely reads as human-written, say "CLEAN" and nothing else.

TEXT:
{body_html}"""
    critique = call_claude(audit_system, audit_user, max_tokens=1200, disable_thinking=True)

    if critique.strip().upper().startswith("CLEAN"):
        return body_html

    fix_system = "You are a sharp human editor making a final pass on a blog draft."
    fix_user = f"""A previous review of this draft found these remaining AI-writing tells:

{critique}

Fix every issue listed. Keep HTML tags intact, keep the same approximate length,
don't add new facts. Output ONLY the corrected HTML.

DRAFT:
{body_html}"""
    try:
        return call_claude_validated("audit-fix", fix_system, fix_user, max_tokens=8000,
                                      disable_thinking=True)
    except RuntimeError as e:
        print(f"  [audit-fix] failed validation, keeping pre-fix content instead: {e}")
        return body_html


def strip_stray_em_dashes(text):
    text = re.sub(r"\s*[—–]\s*", ". ", text)
    text = re.sub(r"\.\s*\.", ".", text)
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
    raw = call_claude(system, user, max_tokens=1200, disable_thinking=True)
    raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "title": f"AI in Entertainment — {TODAY_HUMAN}",
            "meta_description": "Daily notes on AI tools, models, and techniques in film and content production.",
            "slug": f"ai-entertainment-{TODAY_STR}",
            "tags": ["ai", "filmmaking"],
        }


# ---------- STEP 4B: HERO IMAGE ----------
IMAGES_DIR = BLOG_DIR / "images"
MAX_IMAGE_WIDTH = 1200
JPEG_QUALITY = 82


def compress_and_save(raw_bytes, output_path):
    img = Image.open(io.BytesIO(raw_bytes))

    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (12, 11, 10))
        img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1])
        img = background
    else:
        img = img.convert("RGB")

    if img.width > MAX_IMAGE_WIDTH:
        ratio = MAX_IMAGE_WIDTH / img.width
        new_size = (MAX_IMAGE_WIDTH, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    img.save(output_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return output_path.stat().st_size


def generate_hero_image(title, tags, slug):
    if not GOOGLE_API_KEY:
        print("No GOOGLE_API_KEY set -- skipping image generation.")
        return None

    prompt = f"""Cinematic editorial photograph illustrating the concept: "{title}".
Style: moody dark near-black background, a single deep red/orange accent light
source somewhere in frame, shallow depth of field, 35mm film grain aesthetic,
professional film-production quality, high contrast. Subject should relate to:
{', '.join(tags)}. No text, no logos, no watermarks, no readable UI screenshots."""

    try:
        gclient = google_genai.Client(api_key=GOOGLE_API_KEY)
        response = gclient.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
        )
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None) is not None:
                IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                image_path = IMAGES_DIR / f"{slug}.jpg"
                raw_size = len(part.inline_data.data)
                final_size = compress_and_save(part.inline_data.data, image_path)
                print(f"Generated hero image: {image_path} "
                      f"(raw: {raw_size/1024:.0f}KB -> compressed: {final_size/1024:.0f}KB)")
                return f"/blog/images/{slug}.jpg"
        print("Image generation returned no image data.")
        return None
    except Exception as e:
        print(f"Image generation failed ({e}). Continuing without an image.")
        return None



# ---------- STEP 6: RENDER WITH THE SITE THEME ----------
# Look and SEO markup live in scripts/blog_theme.py (shared with
# scripts/rebuild_blog.py). blog/posts.json is the source of truth: the new
# post is added there, then the post page, blog index, RSS feed and
# sitemap.xml are rendered from it.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog_theme  # noqa: E402

BLOG_INDEX_PATH = BLOG_DIR / "index.html"
MANIFEST_PATH = BLOG_DIR / "posts.json"
FEED_PATH = BLOG_DIR / "feed.xml"
DEFAULT_CATEGORY = "AI & Entertainment"


def load_manifest():
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return []


def publish(filename, title, meta_description, body_html, tags, image_url=None):
    manifest = [p for p in load_manifest() if p.get("filename") != filename]
    entry = {
        "filename": filename,
        "title": title,
        "meta_description": meta_description,
        "tags": tags,
        "date": TODAY.isoformat(),
        "category": DEFAULT_CATEGORY,
        "image": image_url,
    }
    manifest.insert(0, entry)

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    (BLOG_DIR / filename).write_text(blog_theme.render_post(entry, body_html, manifest), encoding="utf-8")
    print(f"Wrote {BLOG_DIR / filename}")

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Updated blog/posts.json")

    BLOG_INDEX_PATH.write_text(blog_theme.render_index(manifest), encoding="utf-8")
    print("Updated blog/index.html")

    FEED_PATH.write_text(blog_theme.render_feed(manifest), encoding="utf-8")
    print("Updated blog/feed.xml")

    SITEMAP_PATH.write_text(blog_theme.render_sitemap(manifest), encoding="utf-8")
    print("Updated sitemap.xml")


# ---------- MAIN ----------
def main():
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
    try:
        brief = research()
        print("Research brief:\n", brief[:500], "...\n")

        print("Drafting article...")
        draft_html = draft(brief)

        print("Humanizing / polishing...")
        final_body = humanize(draft_html)

        print("Running self-audit pass for remaining AI tells...")
        final_body = audit_and_fix(final_body)
    except RuntimeError as e:
        print(f"\nFATAL: pipeline aborted, nothing will be published today.\n{e}")
        sys.exit(1)

    print("Applying hard em-dash safety net...")
    final_body = strip_stray_em_dashes(final_body)

    print("Generating metadata...")
    meta = generate_metadata(final_body)
    title = meta["title"]
    meta_description = meta["meta_description"]
    slug = meta["slug"]
    tags = meta.get("tags", ["ai", "filmmaking"])

    filename = f"{TODAY_STR}-{slug}.html"

    print("Generating hero image...")
    image_url = generate_hero_image(title, tags, slug)

    publish(filename, title, meta_description, final_body, tags, image_url)

    print(f"DONE: {title}")


if __name__ == "__main__":
    main()

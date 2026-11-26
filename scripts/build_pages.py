#!/usr/bin/env python3
"""
Build the landing pages (AI video by industry + real-shoot services in Berlin)
from scripts/site_pages_content.py, then refresh sitemap.xml.

    python3 scripts/build_pages.py

Pages:
  /ai-video/                       hub of all AI industry films
  /ai-video/<industry>/            one page per industry, video as main content
  /<service-slug>/                 real-shoot services (event, food, brand, podcast)
"""

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog_theme as T  # noqa: E402
from site_pages_content import AI_INDUSTRIES, SERVICES, UPDATED  # noqa: E402

ROOT = T.ROOT
SITE = T.SITE
esc = T.esc


def crumbs_html(items):
    lis = []
    for name, url in items:
        lis.append(f'<li><a href="{url}">{esc(name)}</a></li>' if url else f'<li aria-current="page">{esc(name)}</li>')
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(lis)}</ol></nav>'


def crumbs_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE}{u or ''}"}
        for i, (n, u) in enumerate(items)]}


def faq_html(faq):
    return "".join(f'<details><summary>{esc(q)}<i></i></summary><div class="ans">{esc(a)}</div></details>' for q, a in faq)


def faq_ld(faq, url):
    return {"@type": "FAQPage", "@id": f"{url}#faq", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}


def h1_html(parts):
    return f'{esc(parts[0])} <span class="serif grad">{esc(parts[1])}</span>'


def wa(text):
    return T.wa_link(text)


STEPS = [
    ("Quick call", "Tell us about your project, your audience and where the film will run."),
    ("Concept & plan", "You get a concept and script or shot list. Nothing is produced until you approve it."),
    ("Production", "AI films are directed shot by shot with the latest generative video tools. Real shoots: my team comes on location."),
    ("Edit & delivery", "Editing, colour and sound design, delivered in every format you need, with feedback rounds included."),
]


def steps_html():
    return "".join(f'<li><span class="st-n">0{i + 1}</span><h3>{esc(t)}</h3><p>{esc(d)}</p></li>' for i, (t, d) in enumerate(STEPS))


def page(path, title, desc, canonical, og_image, graph, body, extra=""):
    ld = {"@context": "https://schema.org", "@graph": graph}
    out = T.head(title, desc, canonical, "website", og_image, ld,
                 extra + f'<meta name="pafp:updated" content="{UPDATED}">\n')
    out += T.NAV.replace(' aria-current="page"', '')
    out += body
    out += T.FOOTER
    dest = ROOT / path.strip("/") / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out, encoding="utf-8")
    return dest


def cta_band(heading_a, heading_b, text, wa_text):
    return f"""
<section class="cta-band wrap" aria-label="Start a project">
  <div class="cta-inner">
    <span class="eyebrow">Start a project</span>
    <h2>{esc(heading_a)} <span class="serif grad">{esc(heading_b)}</span></h2>
    <p>{esc(text)}</p>
    <div class="cta-btns">
      <a href="/#contact" class="btn btn-glow">Start a project {T.ARROW}</a>
      <a href="{wa(wa_text)}" class="btn btn-ghost" target="_blank" rel="noopener">{T.WA_ICON} WhatsApp</a>
    </div>
  </div>
</section>
"""


# ---------------------------------------------------------------- AI industry pages
def video_obj(ind, url):
    v = ind["video"]
    return {
        "@type": "VideoObject", "@id": f"{url}#video",
        "name": f"{ind['name']}: AI commercial by PAFP",
        "description": f"AI-generated commercial for the {ind['name'].lower()} industry, directed by Pranav Arya (PAFP). {ind['shows']}",
        "thumbnailUrl": f"{SITE}/assets/posters/{v}.webp",
        "contentUrl": f"{SITE}/assets/videos/{v}.mp4",
        "uploadDate": "2026-11-26T10:00:00+01:00",
        "duration": "PT10S",
        "creator": {"@id": f"{SITE}/#person"},
        "publisher": T.ORG,
    }


def ind_card(ind, h="h3"):
    v = ind["video"]
    return f"""<a class="ind-card" href="/ai-video/{ind['slug']}/">
  <div class="ic-media"><img src="/assets/posters/{v}.webp" alt="" width="1280" height="720" loading="lazy" decoding="async">
    <video muted loop playsinline preload="none" data-hover src="/assets/videos/{v}.mp4" aria-hidden="true"></video></div>
  <div class="ic-body"><span class="pc-meta">AI film</span><{h}>{esc(ind['name'])}</{h}><span class="pc-more">See the film {T.ARROW}</span></div>
</a>
"""


def build_ai_page(ind):
    url = f"{SITE}/ai-video/{ind['slug']}/"
    v = ind["video"]
    crumbs = [("Home", "/"), ("AI video", "/ai-video/"), (ind["name"], None)]
    others = [o for o in AI_INDUSTRIES if o["slug"] != ind["slug"]]
    idx = AI_INDUSTRIES.index(ind)
    related = (others[idx:] + others[:idx])[:3]
    graph = [
        {"@type": "Service", "@id": f"{url}#service", "name": f"AI video production for {ind['name'].lower()}",
         "serviceType": "AI video production", "description": ind["desc"], "url": url,
         "provider": T.ORG, "areaServed": [{"@type": "Place", "name": "Europe"}, {"@type": "Place", "name": "Worldwide"}],
         "subjectOf": {"@id": f"{url}#video"}},
        video_obj(ind, url),
        faq_ld(ind["faq"], url),
        crumbs_ld(crumbs),
    ]
    uses = "".join(f"<li>{esc(u)}</li>" for u in ind["uses"])
    need = "".join(f"<li>{esc(u)}</li>" for u in ind["need"])
    body = f"""
<main id="content">
<header class="lp-hero wrap">
  <div class="lp-text">
    {crumbs_html(crumbs)}
    <span class="eyebrow">AI video · {esc(ind['name'])}</span>
    <h1>{h1_html(ind['h1'])}</h1>
    <p class="dek">{esc(ind['intro'])}</p>
    <div class="cta-btns">
      <a href="/#contact" class="btn btn-glow">Get a film like this {T.ARROW}</a>
      <a href="{wa('Hi Pranav, I would like an AI film for my ' + ind['noun'] + '.')}" class="btn btn-ghost" target="_blank" rel="noopener">{T.WA_ICON} WhatsApp</a>
    </div>
  </div>
  <figure class="lp-video">
    <video controls muted loop playsinline autoplay preload="metadata" poster="/assets/posters/{v}.webp" width="1280" height="720">
      <source src="/assets/videos/{v}.mp4" type="video/mp4">
    </video>
    <figcaption>{esc(ind['shows'])} <span>Made with AI by PAFP.</span></figcaption>
  </figure>
</header>

<section class="lp-split wrap">
  <div>
    <span class="eyebrow">Where it works</span>
    <h2>Built for how {esc(ind['short'].lower())} brands sell.</h2>
    <ul class="ticks">{uses}</ul>
  </div>
  <div>
    <span class="eyebrow">What we need from you</span>
    <h2>Three things to get started.</h2>
    <ul class="ticks">{need}</ul>
    <p class="note">You approve the concept and script before anything is produced. Every film is delivered in vertical 9:16, square and widescreen.</p>
  </div>
</section>

<section class="lp-steps wrap" aria-labelledby="steps-h">
  <span class="eyebrow">How it works</span>
  <h2 id="steps-h">From idea to premiere in four steps.</h2>
  <ol class="steps">{steps_html()}</ol>
</section>

<section class="lp-faq wrap" id="faq" aria-labelledby="faq-h">
  <div><span class="eyebrow">Questions</span><h2 id="faq-h">AI films for {esc(ind['name'].lower())}, <span class="serif grad">answered.</span></h2></div>
  <div class="faq-list">{faq_html(ind['faq'])}</div>
</section>

{cta_band('Want a film like this', 'for your brand?', 'Tell us about your ' + ind['noun'] + ' and where the film will run. We reply within a day.', 'Hi Pranav, I would like an AI film for my ' + ind['noun'] + '.')}

<section class="related wrap" aria-labelledby="more-h">
  <div class="rel-head"><span class="eyebrow">More AI films</span><h2 id="more-h">Other industries</h2></div>
  <div class="ind-grid">{''.join(ind_card(o) for o in related)}</div>
  <a href="/ai-video/" class="btn btn-ghost all-posts">All industries {T.ARROW}</a>
</section>
</main>
"""
    extra = (f'<meta property="og:video" content="{SITE}/assets/videos/{v}.mp4">\n'
             f'<meta property="og:video:type" content="video/mp4">\n'
             f'<link rel="preload" as="image" href="/assets/posters/{v}.webp" fetchpriority="high">\n')
    return page(f"/ai-video/{ind['slug']}/", ind["title"], ind["desc"], url,
                f"{SITE}/assets/posters/{v}.webp", graph, body, extra)


def build_ai_hub():
    url = f"{SITE}/ai-video/"
    crumbs = [("Home", "/"), ("AI video", None)]
    title = "AI Video Production for Businesses | AI Commercials by Industry | PAFP"
    desc = ("Cinematic AI commercials for hotels, real estate, restaurants, fashion, beauty, cars and more. "
            "AI video production by Pranav Arya, Berlin, for brands across Europe and worldwide.")
    graph = [
        {"@type": "Service", "@id": f"{url}#service", "name": "AI video production", "serviceType": "AI video production",
         "description": desc, "url": url, "provider": T.ORG,
         "areaServed": [{"@type": "Place", "name": "Europe"}, {"@type": "Place", "name": "Worldwide"}]},
        {"@type": "ItemList", "name": "AI films by industry", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": f"{SITE}/ai-video/{ind['slug']}/", "name": ind["name"]}
            for i, ind in enumerate(AI_INDUSTRIES)]},
        crumbs_ld(crumbs),
    ]
    faq = [
        ("What is an AI commercial?", "A film made with generative video tools instead of a camera crew. I write and direct every shot, then edit, grade and add sound like a real commercial."),
        ("Will it look like my brand?", "Yes. Your name, logo, colours and products are built into the concept before production starts, and you approve the script first."),
        ("How long does it take?", "AI films are much faster than a traditional production. You get a clear delivery date after our first call."),
        ("Real shoot or AI film: which do I need?", "If it is about real people and real moments, go for a real shoot. If you want a big-budget look for a product, brand or place without the logistics, AI is perfect. Many clients combine both."),
    ]
    graph.append(faq_ld(faq, url))
    body = f"""
<main id="content">
<header class="blog-hero wrap">
  {crumbs_html(crumbs)}
  <span class="eyebrow">AI video production</span>
  <h1>AI films for <span class="serif grad">every industry.</span></h1>
  <p class="dek">Cinematic commercials with no crew, no location and no limits. Pick your industry to see a film made for it, then tell us about your brand. Made in Berlin for businesses across Europe and worldwide.</p>
</header>
<section class="wrap ai-hub" aria-label="Industries">
  <div class="ind-grid">{''.join(ind_card(i, 'h2') for i in AI_INDUSTRIES)}</div>
</section>
<section class="lp-steps wrap" aria-labelledby="steps-h">
  <span class="eyebrow">How it works</span>
  <h2 id="steps-h">From idea to premiere in four steps.</h2>
  <ol class="steps">{steps_html()}</ol>
</section>
<section class="lp-faq wrap" id="faq" aria-labelledby="faq-h">
  <div><span class="eyebrow">Questions</span><h2 id="faq-h">AI video, <span class="serif grad">answered.</span></h2></div>
  <div class="faq-list">{faq_html(faq)}</div>
</section>
{cta_band('Your industry,', 'your film.', 'Do not see your industry? AI works for almost any product, place or service. Ask us.', 'Hi Pranav, I would like an AI film for my business.')}
<section class="related wrap" aria-labelledby="real-h">
  <div class="rel-head"><span class="eyebrow">Prefer a real shoot?</span><h2 id="real-h">We film on location too</h2></div>
  <div class="svc-links">{''.join(f'<a href="/{s["slug"]}/">{esc(s["name"])} {T.ARROW}</a>' for s in SERVICES)}</div>
</section>
</main>
"""
    return page("/ai-video/", title, desc, url, T.DEFAULT_OG, graph, body)


# ---------------------------------------------------------------- service pages
def reel(n):
    return (f'<div class="reel-v"><video muted loop playsinline preload="none" data-auto '
            f'poster="/assets/real/posters/real-{n:02d}.webp" width="720" height="1280" aria-label="Real shoot reel by PAFP">'
            f'<source src="/assets/real/previews/real-{n:02d}.mp4" type="video/mp4"></video></div>')


def build_service(svc):
    url = f"{SITE}/{svc['slug']}/"
    crumbs = [("Home", "/"), (svc["name"], None)]
    graph = [
        {"@type": "Service", "@id": f"{url}#service", "name": svc["name"], "serviceType": svc["name"].split(" in ")[0],
         "description": svc["desc"], "url": url, "provider": T.ORG,
         "areaServed": [{"@type": "City", "name": "Berlin"}, {"@type": "Country", "name": "Germany"},
                        {"@type": "Place", "name": "Europe"}]},
        faq_ld(svc["faq"], url),
        crumbs_ld(crumbs),
    ]
    covers = "".join(f'<li><h3>{esc(t)}</h3><p>{esc(d)}</p></li>' for t, d in svc["covers"])
    deliver = "".join(f"<li>{esc(d)}</li>" for d in svc["deliver"])
    reels = ""
    if svc["reels"]:
        reels = f'<section class="reel-row wrap" aria-label="Recent real shoots"><div class="reels-4">{"".join(reel(n) for n in svc["reels"])}</div></section>'
    clients = ""
    if svc["clients"]:
        clients = ('<section class="wrap clients-row" aria-label="Selected work"><span class="eyebrow">Selected work</span><ul>'
                   + "".join(f"<li>{esc(c)}</li>" for c in svc["clients"]) + "</ul></section>")
    others = [s for s in SERVICES if s["slug"] != svc["slug"]]
    body = f"""
<main id="content">
<header class="blog-hero wrap">
  {crumbs_html(crumbs)}
  <span class="eyebrow">{esc(svc['eyebrow'])}</span>
  <h1>{h1_html(svc['h1'])}</h1>
  <p class="dek">{esc(svc['intro'])}</p>
  <div class="cta-btns">
    <a href="/#contact" class="btn btn-glow">Check availability {T.ARROW}</a>
    <a href="{wa('Hi Pranav, I am interested in ' + svc['name'].lower() + '.')}" class="btn btn-ghost" target="_blank" rel="noopener">{T.WA_ICON} WhatsApp</a>
  </div>
</header>
{reels}
<section class="lp-covers wrap" aria-labelledby="cov-h">
  <span class="eyebrow">What we film</span>
  <h2 id="cov-h">What we cover.</h2>
  <ul class="cover-grid">{covers}</ul>
</section>
<section class="lp-split wrap">
  <div>
    <span class="eyebrow">What you get</span>
    <h2>Delivered ready to post.</h2>
    <ul class="ticks">{deliver}</ul>
  </div>
  <div>
    <span class="eyebrow">How it works</span>
    <h2>Simple from the first call.</h2>
    <ol class="steps compact">{steps_html()}</ol>
  </div>
</section>
{clients}
<section class="lp-faq wrap" id="faq" aria-labelledby="faq-h">
  <div><span class="eyebrow">Questions</span><h2 id="faq-h">Good to <span class="serif grad">know.</span></h2></div>
  <div class="faq-list">{faq_html(svc['faq'])}</div>
</section>
{cta_band('Tell us about', 'your project.', 'Share the date, the place and what matters most. We reply within a day with availability and a plan.', 'Hi Pranav, I am interested in ' + svc['name'].lower() + '.')}
<section class="related wrap" aria-labelledby="more-h">
  <div class="rel-head"><span class="eyebrow">More services</span><h2 id="more-h">What else we do</h2></div>
  <div class="svc-links">{''.join(f'<a href="/{s["slug"]}/">{esc(s["name"])} {T.ARROW}</a>' for s in others)}<a href="/ai-video/">AI films for businesses {T.ARROW}</a></div>
</section>
</main>
"""
    og = f"{SITE}/assets/real/posters/real-{svc['reels'][0]:02d}.webp" if svc["reels"] else T.DEFAULT_OG
    return page(f"/{svc['slug']}/", svc["title"], svc["desc"], url, og, graph, body)


def main():
    built = [build_ai_hub()]
    built += [build_ai_page(i) for i in AI_INDUSTRIES]
    built += [build_service(s) for s in SERVICES]
    manifest = json.loads((ROOT / "blog" / "posts.json").read_text(encoding="utf-8"))
    (ROOT / "sitemap.xml").write_text(T.render_sitemap(manifest), encoding="utf-8")
    print(f"Built {len(built)} pages and refreshed sitemap.xml")


if __name__ == "__main__":
    main()

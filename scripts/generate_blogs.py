"""
generate_blogs.py  FINAL
─────────────────────────────────────────────────────────────
Runs daily via GitHub Actions at 12:30 PM IST.

What it does:
  1. Calls Claude API → generates 10 SEO blog posts
  2. Saves each as blog/posts/SLUG.html  (full styled page)
  3. Rebuilds blog/index.html            (full blog listing)
  4. Updates index.html blog preview     (latest 6 shown on homepage)
  5. Generates sitemap.xml               (for Google Search Console)
─────────────────────────────────────────────────────────────
"""

import anthropic
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────
BLOG_DIR      = Path("blog/posts")
INDEX_FILE    = Path("blog/index.html")
MAIN_INDEX    = Path("index.html")
SITEMAP_FILE  = Path("sitemap.xml")
MANIFEST_FILE = Path("blog/manifest.json")
TODAY         = datetime.now()
DATE_STR      = TODAY.strftime("%Y-%m-%d")
DATE_NICE     = TODAY.strftime("%d %B %Y")
SITE_URL      = "https://jayeshparab.com"

MARKER_START  = "<!-- BLOG_PREVIEW_START -->"
MARKER_END    = "<!-- BLOG_PREVIEW_END -->"

TOPIC_BUCKETS = [
    "Goa's startup ecosystem and investment climate in 2025–2030",
    "Clean energy and CleanTech innovations in coastal India",
    "EdTech trends transforming education in tier-2 and tier-3 Indian cities",
    "Real estate development and smart city planning in Goa",
    "Pharmaceutical innovation and India's role in global healthcare",
    "Technology leadership and the future of AI in Indian businesses",
    "Sustainable tourism and eco-friendly business models in Goa",
    "Entrepreneurship lessons and building startups from scratch in India",
    "International trade, exports, and India's growing global footprint",
    "Environmental policy, carbon credits, and green finance in India",
]

SYSTEM_PROMPT = """You are an expert content writer for Jayesh Parab — a Goa-based entrepreneur,
investor and visionary working across Technology, CleanTech, Real Estate, EdTech, Pharma and Trade.
His website is jayeshparab.com.

Write in his authoritative yet approachable voice. Blogs must be insightful, data-rich,
and forward-looking — always from a Goa/India perspective.

Naturally mention "Jayesh Parab" by name at least 2–3 times within the blog body
— for example as the author's perspective, a quote attribution, or a closing reflection.
Respond ONLY with a valid JSON object. No markdown fences, no preamble, no explanation."""

POST_PROMPT = """Write a detailed SEO-optimised blog post on this topic:

TOPIC: {topic}
DATE:  {date}
SLUG:  {slug}

Return ONLY a valid JSON object with these exact keys:
{{
  "title":       "Compelling, clear title under 65 characters",
  "slug":        "{slug}",
  "date":        "{date}",
  "category":    "One of: Technology | CleanTech | EdTech | Real Estate | Pharma | Trade | Entrepreneurship | Goa 2030",
  "excerpt":     "SEO meta description, exactly 140-160 characters",
  "read_time":   "X min read",
  "keywords":    ["Jayesh Parab", "keyword2", "keyword3", "keyword4", "keyword5"],
  "body_html":   "Full blog body in HTML. Use only <h2>, <h3>, <p>, <ul>, <li>, <strong>. Minimum 950 words. No inline styles."
}}"""

# ── HELPERS ───────────────────────────────────────────────────

def log(msg): print(msg, flush=True)

def safe_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$",    "", raw)
    return json.loads(raw)

def generate_post(client, topic: str, idx: int) -> dict | None:
    slug   = f"{DATE_STR}-blog-{idx+1:02d}"
    prompt = POST_PROMPT.format(topic=topic, date=DATE_NICE, slug=slug)
    try:
        log(f"    Calling Claude API...")
        msg = client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 2800,
            system     = SYSTEM_PROMPT,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw  = msg.content[0].text
        log(f"    Response: {len(raw)} chars. Parsing...")
        data = safe_json(raw)
        # Always guarantee "Jayesh Parab" is first keyword for SEO
        kw = data.get("keywords", [])
        if "Jayesh Parab" not in kw:
            kw.insert(0, "Jayesh Parab")
        data["keywords"] = kw
        if "Jayesh Parab" not in data.get("excerpt", ""):
            data["excerpt"] = data["excerpt"].rstrip(".") + " — by Jayesh Parab."
        data["slug"]     = slug
        data["date_raw"] = DATE_STR
        log(f"    ✓ {data.get('title','')[:60]}")
        return data
    except anthropic.AuthenticationError:
        log("  ✗ AUTH ERROR — check ANTHROPIC_API_KEY secret")
        return None
    except anthropic.RateLimitError:
        log("  ✗ RATE LIMIT — retry tomorrow")
        return None
    except json.JSONDecodeError as e:
        log(f"  ✗ JSON parse failed: {e}")
        return None
    except Exception as e:
        log(f"  ✗ Error: {type(e).__name__}: {e}")
        return None

# ── HTML: INDIVIDUAL POST PAGE ────────────────────────────────

def post_html(p: dict) -> str:
    kw_meta = ", ".join(p.get("keywords", []))
    kw_tags = "".join(f'<span class="kw-tag">{k}</span>' for k in p.get("keywords", []))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{p['title']} | Jayesh Parab</title>
  <meta name="description"               content="{p['excerpt']}">
  <meta name="keywords"                  content="{kw_meta}">
  <meta name="author"                    content="Jayesh Parab">
  <meta property="og:title"             content="{p['title']}">
  <meta property="og:description"       content="{p['excerpt']}">
  <meta property="og:url"               content="{SITE_URL}/blog/posts/{p['slug']}.html">
  <meta property="og:type"              content="article">
  <meta property="article:published_time" content="{p['date_raw']}">
  <link rel="canonical"                  href="{SITE_URL}/blog/posts/{p['slug']}.html">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": "{p['title']}",
    "description": "{p['excerpt']}",
    "datePublished": "{p['date_raw']}",
    "author": {{
      "@type": "Person",
      "name": "Jayesh Parab",
      "url": "{SITE_URL}"
    }},
    "publisher": {{
      "@type": "Person",
      "name": "Jayesh Parab",
      "url": "{SITE_URL}"
    }},
    "keywords": "{kw_meta}"
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Cormorant+Garamond:wght@400;600;700&family=Outfit:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root{{--navy:#061427;--navy2:#0a1f3a;--gold:#C49A3C;--white:#FFFFFF;--muted:rgba(255,255,255,0.58);--border:rgba(196,154,60,0.22);--border2:rgba(255,255,255,0.08);}}
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
    html{{scroll-behavior:smooth;}}
    body{{background:var(--navy);color:var(--white);font-family:'Outfit',sans-serif;font-size:17px;line-height:1.82;}}
    a{{text-decoration:none;color:inherit;}}
    nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(6,20,39,0.92);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);padding:0 5%;height:64px;display:flex;align-items:center;justify-content:space-between;}}
    .nav-logo{{font-family:'Playfair Display',serif;font-size:1.3rem;font-weight:700;color:var(--gold);letter-spacing:.05em;}}
    .nav-links{{display:flex;gap:2rem;list-style:none;}}
    .nav-links a{{color:var(--muted);font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;font-family:'DM Mono',monospace;transition:color .2s;}}
    .nav-links a:hover,.nav-links a.active{{color:var(--gold);}}
    .post-hero{{margin-top:64px;padding:60px 5% 50px;border-bottom:1px solid var(--border);background:var(--navy2);}}
    .post-meta{{display:flex;gap:1.2rem;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap;}}
    .cat-pill{{background:rgba(196,154,60,.12);border:1px solid rgba(196,154,60,.4);color:var(--gold);font-family:'DM Mono',monospace;font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;padding:4px 14px;border-radius:100px;}}
    .post-date,.post-read{{font-family:'DM Mono',monospace;font-size:.72rem;color:var(--muted);letter-spacing:.06em;}}
    .post-title{{font-family:'Playfair Display',serif;font-size:clamp(1.9rem,5vw,3rem);font-weight:700;line-height:1.18;color:var(--white);margin-bottom:1.2rem;}}
    .post-excerpt{{font-size:1.05rem;color:var(--muted);max-width:700px;line-height:1.72;}}
    .post-body{{max-width:780px;margin:0 auto;padding:56px 5% 88px;}}
    .back-btn{{display:inline-flex;align-items:center;gap:.5rem;color:var(--gold);font-size:.8rem;letter-spacing:.06em;font-family:'DM Mono',monospace;margin-bottom:2.8rem;transition:opacity .2s;}}
    .back-btn:hover{{opacity:.7;}}
    .byline{{font-family:'DM Mono',monospace;font-size:.75rem;letter-spacing:.08em;color:rgba(255,255,255,.45);margin-bottom:2rem;}}
    .byline strong{{color:var(--gold);}}
    .post-body h2{{font-family:'Cormorant Garamond',serif;font-size:1.85rem;font-weight:700;color:var(--white);margin:2.8rem 0 1rem;padding-bottom:.6rem;border-bottom:1px solid var(--border);}}
    .post-body h3{{font-family:'Cormorant Garamond',serif;font-size:1.35rem;font-weight:600;color:var(--gold);margin:2rem 0 .8rem;}}
    .post-body p{{margin-bottom:1.3rem;color:rgba(255,255,255,.84);}}
    .post-body strong{{color:var(--gold);font-weight:600;}}
    .post-body ul{{margin:1rem 0 1.6rem 1.6rem;}}
    .post-body li{{color:rgba(255,255,255,.8);margin-bottom:.55rem;line-height:1.72;}}
    .post-body li::marker{{color:var(--gold);}}
    .kw-row{{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:2.5rem;padding-top:2rem;border-top:1px solid var(--border);}}
    .kw-tag{{font-family:'DM Mono',monospace;font-size:.68rem;letter-spacing:.08em;color:var(--muted);background:rgba(255,255,255,.05);border:1px solid var(--border2);padding:4px 12px;border-radius:100px;}}
    .author-card{{margin-top:3rem;padding:2rem;background:var(--navy2);border:1px solid var(--border);border-radius:10px;display:flex;gap:1.5rem;align-items:center;}}
    .author-init{{font-family:'Playfair Display',serif;font-size:1.8rem;font-weight:700;color:var(--gold);background:rgba(196,154,60,.1);width:60px;height:60px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
    .author-name{{font-family:'Outfit',sans-serif;font-weight:600;font-size:1rem;margin-bottom:.25rem;}}
    .author-bio{{font-size:.86rem;color:var(--muted);line-height:1.6;}}
    footer{{text-align:center;padding:2.5rem;border-top:1px solid var(--border);font-size:.78rem;color:var(--muted);font-family:'DM Mono',monospace;letter-spacing:.06em;}}
    footer a{{color:var(--gold);}}
    @media(max-width:768px){{.nav-links{{display:none;}}}}
  </style>
</head>
<body>
  <nav>
    <a href="/" class="nav-logo">JP</a>
    <ul class="nav-links">
      <li><a href="/">Home</a></li>
      <li><a href="/blog/" class="active">Blog</a></li>
      <li><a href="/#connect">Connect</a></li>
    </ul>
  </nav>

  <section class="post-hero">
    <div class="post-meta">
      <span class="cat-pill">{p['category']}</span>
      <span class="post-date">{p['date']}</span>
      <span class="post-read">{p['read_time']}</span>
    </div>
    <h1 class="post-title">{p['title']}</h1>
    <p class="post-excerpt">{p['excerpt']}</p>
  </section>

  <article class="post-body">
    <a href="/blog/" class="back-btn">&#8592; All Posts</a>
    <p class="byline">By <strong>Jayesh Parab</strong> &mdash; {p['date']}</p>

    {p['body_html']}

    <div class="kw-row">{kw_tags}</div>

    <div class="author-card">
      <div class="author-init">JP</div>
      <div>
        <div class="author-name">Jayesh Parab</div>
        <div class="author-bio">Goa-based entrepreneur and investor working across Technology, CleanTech, Real Estate, EdTech, Pharma and Trade. Driving the Goa 2030 vision from Panaji, India.</div>
      </div>
    </div>
  </article>

  <footer>
    <p>&copy; {TODAY.year} <a href="/">Jayesh Parab</a> &mdash; Panaji, Goa, India</p>
  </footer>
</body>
</html>"""


# ── HTML: BLOG INDEX PAGE ─────────────────────────────────────

def blog_index_html(all_posts: list) -> str:
    posts_sorted = sorted(all_posts, key=lambda x: x.get("date_raw",""), reverse=True)
    total = len(posts_sorted)

    cards = ""
    for p in posts_sorted:
        cards += f"""
      <a href="/blog/posts/{p['slug']}.html" class="blog-card">
        <div class="card-meta">
          <span class="cat-pill">{p['category']}</span>
          <span class="card-date">{p['date']}</span>
          <span class="card-read">{p['read_time']}</span>
        </div>
        <h2 class="card-title">{p['title']}</h2>
        <p class="card-excerpt">{p['excerpt']}</p>
        <span class="read-more">Read Article &#8594;</span>
      </a>"""

    no_posts = """
      <div class="no-posts">
        Daily blogs publish at 12:30 PM IST — check back soon.
      </div>""" if not cards else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog — Perspectives & Insights | Jayesh Parab</title>
  <meta name="description" content="Daily insights on Technology, CleanTech, EdTech, Real Estate, Pharma and Goa 2030 by Jayesh Parab — entrepreneur and investor based in Goa, India.">
  <meta name="keywords" content="Jayesh Parab, Jayesh Parab blog, Goa entrepreneur, CleanTech India, startup investor Goa">
  <meta name="author" content="Jayesh Parab">
  <link rel="canonical" href="{SITE_URL}/blog/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Cormorant+Garamond:wght@400;600;700&family=Outfit:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root{{--navy:#061427;--navy2:#0a1f3a;--gold:#C49A3C;--white:#FFFFFF;--muted:rgba(255,255,255,0.58);--border:rgba(196,154,60,0.22);--border2:rgba(255,255,255,0.08);}}
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:var(--navy);color:var(--white);font-family:'Outfit',sans-serif;}}
    a{{text-decoration:none;color:inherit;}}
    nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(6,20,39,0.92);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);padding:0 5%;height:64px;display:flex;align-items:center;justify-content:space-between;}}
    .nav-logo{{font-family:'Playfair Display',serif;font-size:1.3rem;font-weight:700;color:var(--gold);letter-spacing:.05em;}}
    .nav-links{{display:flex;gap:2rem;list-style:none;}}
    .nav-links a{{color:var(--muted);font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;font-family:'DM Mono',monospace;transition:color .2s;}}
    .nav-links a:hover,.nav-links a.active{{color:var(--gold);}}
    .page-hero{{margin-top:64px;padding:80px 5% 64px;background:var(--navy2);border-bottom:1px solid var(--border);}}
    .hero-label{{font-family:'DM Mono',monospace;font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);margin-bottom:1rem;display:block;}}
    .page-title{{font-family:'Playfair Display',serif;font-size:clamp(2.5rem,6vw,4.2rem);font-weight:700;line-height:1.08;margin-bottom:1rem;}}
    .page-sub{{color:var(--muted);font-size:1.05rem;max-width:560px;line-height:1.72;}}
    .post-count{{font-family:'DM Mono',monospace;font-size:.75rem;color:var(--muted);margin-top:1.5rem;letter-spacing:.08em;}}
    .blog-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1.5rem;padding:48px 5% 88px;max-width:1400px;margin:0 auto;}}
    .blog-card{{background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:12px;padding:2rem;display:flex;flex-direction:column;gap:.9rem;transition:border-color .25s,transform .25s,background .25s;}}
    .blog-card:hover{{border-color:var(--gold);transform:translateY(-4px);background:rgba(196,154,60,.04);}}
    .card-meta{{display:flex;gap:.8rem;align-items:center;flex-wrap:wrap;}}
    .cat-pill{{background:rgba(196,154,60,.1);border:1px solid rgba(196,154,60,.35);color:var(--gold);font-family:'DM Mono',monospace;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;padding:3px 10px;border-radius:100px;}}
    .card-date,.card-read{{font-family:'DM Mono',monospace;font-size:.68rem;color:var(--muted);}}
    .card-title{{font-family:'Cormorant Garamond',serif;font-size:1.45rem;font-weight:700;line-height:1.3;color:var(--white);transition:color .2s;}}
    .blog-card:hover .card-title{{color:var(--gold);}}
    .card-excerpt{{font-size:.88rem;color:var(--muted);line-height:1.68;flex:1;}}
    .read-more{{color:var(--gold);font-size:.78rem;letter-spacing:.06em;font-family:'DM Mono',monospace;margin-top:.25rem;}}
    .no-posts{{grid-column:1/-1;text-align:center;padding:5rem;border:1px dashed var(--border);border-radius:12px;color:var(--muted);font-family:'DM Mono',monospace;font-size:.84rem;letter-spacing:.08em;}}
    footer{{text-align:center;padding:2.5rem;border-top:1px solid var(--border);font-size:.78rem;color:var(--muted);font-family:'DM Mono',monospace;letter-spacing:.06em;}}
    footer a{{color:var(--gold);}}
    @media(max-width:768px){{.nav-links{{display:none;}}}}
  </style>
</head>
<body>
  <nav>
    <a href="/" class="nav-logo">JP</a>
    <ul class="nav-links">
      <li><a href="/">Home</a></li>
      <li><a href="/blog/" class="active">Blog</a></li>
      <li><a href="/#connect">Connect</a></li>
    </ul>
  </nav>

  <section class="page-hero">
    <span class="hero-label">Jayesh Parab &mdash; Perspectives &amp; Insights</span>
    <h1 class="page-title">The Blog</h1>
    <p class="page-sub">Daily thoughts by Jayesh Parab on Technology, CleanTech, Real Estate, EdTech, Pharma, Trade and the Goa 2030 vision.</p>
    <p class="post-count">{total} articles by Jayesh Parab &middot; Updated daily at 12:30 PM IST</p>
  </section>

  <main class="blog-grid">
    {cards}{no_posts}
  </main>

  <footer>
    <p>&copy; {TODAY.year} <a href="/">Jayesh Parab</a> &mdash; Panaji, Goa, India</p>
  </footer>
</body>
</html>"""


# ── HTML: HOMEPAGE BLOG PREVIEW ───────────────────────────────

def homepage_preview_cards(all_posts: list) -> str:
    latest = sorted(all_posts, key=lambda x: x.get("date_raw",""), reverse=True)[:6]
    if not latest:
        return '\n<div class="blog-preview-placeholder">Daily blogs by Jayesh Parab publish at 12:30 PM IST — <a href="/blog/" style="color:var(--gold)">visit the full blog</a>.</div>\n'

    cards = ""
    for p in latest:
        cards += f"""
<a href="/blog/posts/{p['slug']}.html" class="blog-preview-card">
  <div class="bp-meta">
    <span class="bp-category">{p['category']}</span>
    <span class="bp-date">{p['date']}</span>
  </div>
  <div class="bp-title">{p['title']}</div>
  <p class="bp-excerpt">{p['excerpt'][:120]}...</p>
  <span class="bp-read">{p['read_time']} &#8594;</span>
</a>"""
    return cards


# ── XML: SITEMAP ──────────────────────────────────────────────

def generate_sitemap(all_posts: list) -> str:
    urls = f"""  <url>
    <loc>{SITE_URL}/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
    <lastmod>{DATE_STR}</lastmod>
  </url>
  <url>
    <loc>{SITE_URL}/blog/</loc>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
    <lastmod>{DATE_STR}</lastmod>
  </url>"""

    for p in sorted(all_posts, key=lambda x: x.get("date_raw",""), reverse=True):
        urls += f"""
  <url>
    <loc>{SITE_URL}/blog/posts/{p['slug']}.html</loc>
    <lastmod>{p.get('date_raw', DATE_STR)}</lastmod>
    <changefreq>never</changefreq>
    <priority>0.7</priority>
  </url>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""


# ── MAIN ──────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log(f"Blog Generator — {DATE_NICE}")
    log("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log("✗ FATAL: ANTHROPIC_API_KEY is not set in GitHub Secrets.")
        sys.exit(1)
    log(f"✓ API key present ({api_key[:8]}...)")

    client = anthropic.Anthropic(api_key=api_key)
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    log(f"✓ blog/posts/ folder ready")

    new_posts = []
    for i, topic in enumerate(TOPIC_BUCKETS):
        log(f"\n[{i+1}/10] {topic[:55]}...")
        post = generate_post(client, topic, i)
        if not post:
            continue
        fp = BLOG_DIR / f"{post['slug']}.html"
        fp.write_text(post_html(post), encoding="utf-8")
        log(f"  ✓ Saved: {fp}")
        new_posts.append(post)

    log(f"\n{'='*60}")
    log(f"Generated today: {len(new_posts)}/10 posts")

    all_posts = []
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, encoding="utf-8") as f:
            all_posts = json.load(f)
        log(f"Loaded {len(all_posts)} existing posts from manifest")

    all_posts = [p for p in all_posts if p.get("date_raw") != DATE_STR]
    all_posts.extend(new_posts)

    MANIFEST_FILE.write_text(json.dumps(all_posts, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"✓ manifest.json saved ({len(all_posts)} total posts)")

    INDEX_FILE.write_text(blog_index_html(all_posts), encoding="utf-8")
    log(f"✓ blog/index.html rebuilt")

    if MAIN_INDEX.exists():
        main_html = MAIN_INDEX.read_text(encoding="utf-8")
        if MARKER_START in main_html and MARKER_END in main_html:
            preview_html = homepage_preview_cards(all_posts)
            before  = main_html.split(MARKER_START)[0]
            after   = main_html.split(MARKER_END)[1]
            updated = before + MARKER_START + "\n" + preview_html + "\n" + MARKER_END + after
            MAIN_INDEX.write_text(updated, encoding="utf-8")
            log(f"✓ index.html blog preview updated (latest {min(6, len(all_posts))} posts)")
        else:
            log("⚠ index.html markers not found — skipping homepage update")
    else:
        log("⚠ index.html not found — skipping homepage update")

    SITEMAP_FILE.write_text(generate_sitemap(all_posts), encoding="utf-8")
    log(f"✓ sitemap.xml generated ({len(all_posts)+2} URLs)")

    log(f"\n✅ DONE! {len(new_posts)} new posts live at {SITE_URL}/blog/")
    log(f"   Jayesh Parab keyword embedded in all meta tags, body and structured data.")

if __name__ == "__main__":
    main()

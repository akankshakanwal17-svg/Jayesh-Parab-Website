"""
generate_blogs.py  v2  — with verbose logging so you can debug in GitHub Actions
"""

import anthropic
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────

BLOG_DIR   = Path("blog/posts")
INDEX_FILE = Path("blog/index.html")
TODAY      = datetime.now()
DATE_STR   = TODAY.strftime("%Y-%m-%d")
DATE_NICE  = TODAY.strftime("%d %B %Y")

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
His personal website is jayeshparab.com.

Write each blog post in his authoritative yet approachable voice.
Blogs should be insightful, data-rich, and forward-looking.
Always write from a Goa / India perspective when relevant.

Respond ONLY with a JSON object — no markdown fences, no preamble.
"""

POST_PROMPT = """Write a detailed, SEO-optimised blog post on this topic:

TOPIC: {topic}
DATE:  {date}
SLUG:  {slug}

Return ONLY a valid JSON object with these exact keys:
{{
  "title":       "Compelling 60-char max title",
  "slug":        "{slug}",
  "date":        "{date}",
  "category":    "One of: Technology | CleanTech | EdTech | Real Estate | Pharma | Trade | Entrepreneurship | Goa 2030",
  "excerpt":     "160-char SEO meta description",
  "read_time":   "X min read",
  "keywords":    ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "body_html":   "Full blog body as HTML — use <h2>, <h3>, <p>, <ul>, <li>, <strong> only. Min 900 words. No inline styles."
}}
"""

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def log(msg): print(msg, flush=True)

def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:60]

def safe_json(raw):
    raw = raw.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$",    "", raw)
    return json.loads(raw)

def generate_post(client, topic, idx):
    slug   = f"{DATE_STR}-blog-{idx+1:02d}"
    prompt = POST_PROMPT.format(topic=topic, date=DATE_NICE, slug=slug)
    try:
        log(f"    Calling Claude API for post {idx+1}...")
        msg = client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 2500,
            system     = SYSTEM_PROMPT,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw  = msg.content[0].text
        log(f"    Response received ({len(raw)} chars). Parsing JSON...")
        data = safe_json(raw)
        data["slug"]     = slug
        data["date_raw"] = DATE_STR
        log(f"    ✓ Parsed: {data.get('title','')[:60]}")
        return data
    except anthropic.AuthenticationError:
        log("  ✗ AUTHENTICATION ERROR — Your ANTHROPIC_API_KEY is invalid or missing.")
        log("    Fix: Go to GitHub repo → Settings → Secrets → Actions → check ANTHROPIC_API_KEY")
        return None
    except anthropic.RateLimitError:
        log("  ✗ RATE LIMIT — Too many requests. Will retry tomorrow.")
        return None
    except json.JSONDecodeError as e:
        log(f"  ✗ JSON parse error: {e}")
        return None
    except Exception as e:
        log(f"  ✗ Unexpected error: {type(e).__name__}: {e}")
        return None

# ─── HTML TEMPLATES ───────────────────────────────────────────────────────────

def post_html(p):
    keywords_meta = ", ".join(p.get("keywords", []))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{p['title']} | Jayesh Parab</title>
  <meta name="description"       content="{p['excerpt']}">
  <meta name="keywords"          content="{keywords_meta}">
  <meta name="author"            content="Jayesh Parab">
  <meta property="og:title"      content="{p['title']}">
  <meta property="og:description"content="{p['excerpt']}">
  <meta property="og:url"        content="https://jayeshparab.com/blog/posts/{p['slug']}.html">
  <meta property="og:type"       content="article">
  <link rel="canonical"          href="https://jayeshparab.com/blog/posts/{p['slug']}.html">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Outfit:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root{{--navy:#061427;--gold:#C49A3C;--white:#FFFFFF;--muted:rgba(255,255,255,0.55);--border:rgba(196,154,60,0.25);}}
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
    html{{scroll-behavior:smooth;}}
    body{{background:var(--navy);color:var(--white);font-family:'Outfit',sans-serif;font-size:17px;line-height:1.8;}}
    nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(6,20,39,0.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:0 5%;height:64px;display:flex;align-items:center;justify-content:space-between;}}
    .nav-logo{{font-family:'Cormorant Garamond',serif;font-size:1.4rem;font-weight:700;color:var(--gold);text-decoration:none;letter-spacing:.03em;}}
    .nav-links{{display:flex;gap:2rem;list-style:none;}}
    .nav-links a{{color:var(--muted);text-decoration:none;font-size:.85rem;letter-spacing:.08em;text-transform:uppercase;transition:color .2s;}}
    .nav-links a:hover{{color:var(--gold);}}
    .post-hero{{margin-top:64px;padding:64px 5% 48px;border-bottom:1px solid var(--border);}}
    .post-meta{{display:flex;gap:1.5rem;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap;}}
    .category-pill{{background:rgba(196,154,60,.15);border:1px solid var(--gold);color:var(--gold);font-family:'DM Mono',monospace;font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;padding:4px 14px;border-radius:100px;}}
    .post-date,.post-read{{font-family:'DM Mono',monospace;font-size:.75rem;color:var(--muted);letter-spacing:.06em;}}
    .post-title{{font-family:'Cormorant Garamond',serif;font-size:clamp(2rem,5vw,3.2rem);font-weight:700;line-height:1.2;color:var(--white);margin-bottom:1.25rem;}}
    .post-excerpt{{font-size:1.1rem;color:var(--muted);max-width:680px;line-height:1.7;}}
    .post-body{{max-width:760px;margin:0 auto;padding:56px 5% 80px;}}
    .post-body h2{{font-family:'Cormorant Garamond',serif;font-size:1.9rem;font-weight:700;color:var(--white);margin:2.5rem 0 1rem;padding-bottom:.5rem;border-bottom:1px solid var(--border);}}
    .post-body h3{{font-family:'Cormorant Garamond',serif;font-size:1.4rem;font-weight:600;color:var(--gold);margin:1.8rem 0 .75rem;}}
    .post-body p{{margin-bottom:1.2rem;color:rgba(255,255,255,.85);}}
    .post-body strong{{color:var(--gold);font-weight:600;}}
    .post-body ul{{margin:1rem 0 1.5rem 1.5rem;}}
    .post-body li{{color:rgba(255,255,255,.82);margin-bottom:.5rem;line-height:1.7;}}
    .post-body li::marker{{color:var(--gold);}}
    .keywords-row{{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:2rem;padding-top:2rem;border-top:1px solid var(--border);}}
    .kw-tag{{font-family:'DM Mono',monospace;font-size:.72rem;letter-spacing:.08em;color:var(--muted);background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);padding:4px 12px;border-radius:100px;}}
    .back-btn{{display:inline-flex;align-items:center;gap:.5rem;color:var(--gold);text-decoration:none;font-size:.85rem;letter-spacing:.06em;font-family:'DM Mono',monospace;margin-bottom:2.5rem;transition:opacity .2s;}}
    .back-btn:hover{{opacity:.7;}}
    footer{{text-align:center;padding:2.5rem;border-top:1px solid var(--border);font-size:.8rem;color:var(--muted);font-family:'DM Mono',monospace;}}
    footer a{{color:var(--gold);text-decoration:none;}}
  </style>
</head>
<body>
  <nav>
    <a href="/" class="nav-logo">JP</a>
    <ul class="nav-links">
      <li><a href="/">Home</a></li>
      <li><a href="/blog/">Blog</a></li>
      <li><a href="/#connect">Connect</a></li>
    </ul>
  </nav>
  <section class="post-hero">
    <div class="post-meta">
      <span class="category-pill">{p['category']}</span>
      <span class="post-date">{p['date']}</span>
      <span class="post-read">{p['read_time']}</span>
    </div>
    <h1 class="post-title">{p['title']}</h1>
    <p class="post-excerpt">{p['excerpt']}</p>
  </section>
  <article class="post-body">
    <a href="/blog/" class="back-btn">&#8592; All Posts</a>
    {p['body_html']}
    <div class="keywords-row">
      {"".join(f'<span class="kw-tag">{k}</span>' for k in p.get("keywords",[]))}
    </div>
  </article>
  <footer>
    <p>&copy; {TODAY.year} <a href="/">Jayesh Parab</a> &mdash; Goa, India</p>
  </footer>
</body>
</html>"""


def index_html(all_posts):
    all_posts_sorted = sorted(all_posts, key=lambda x: x.get("date_raw",""), reverse=True)
    cards = ""
    for p in all_posts_sorted:
        cards += f"""
    <article class="blog-card">
      <div class="card-meta">
        <span class="category-pill">{p['category']}</span>
        <span class="card-date">{p['date']}</span>
        <span class="card-read">{p['read_time']}</span>
      </div>
      <h2 class="card-title">
        <a href="/blog/posts/{p['slug']}.html">{p['title']}</a>
      </h2>
      <p class="card-excerpt">{p['excerpt']}</p>
      <a href="/blog/posts/{p['slug']}.html" class="read-more">Read Article &#8594;</a>
    </article>"""
    total = len(all_posts_sorted)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog | Jayesh Parab</title>
  <meta name="description" content="Insights on Technology, CleanTech, EdTech, Real Estate, and Goa's future by Jayesh Parab.">
  <link rel="canonical" href="https://jayeshparab.com/blog/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Outfit:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root{{--navy:#061427;--gold:#C49A3C;--white:#FFFFFF;--muted:rgba(255,255,255,0.55);--border:rgba(196,154,60,0.25);}}
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:var(--navy);color:var(--white);font-family:'Outfit',sans-serif;}}
    nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(6,20,39,0.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:0 5%;height:64px;display:flex;align-items:center;justify-content:space-between;}}
    .nav-logo{{font-family:'Cormorant Garamond',serif;font-size:1.4rem;font-weight:700;color:var(--gold);text-decoration:none;}}
    .nav-links{{display:flex;gap:2rem;list-style:none;}}
    .nav-links a{{color:var(--muted);text-decoration:none;font-size:.85rem;letter-spacing:.08em;text-transform:uppercase;transition:color .2s;}}
    .nav-links a:hover{{color:var(--gold);}}
    .page-hero{{margin-top:64px;padding:80px 5% 60px;border-bottom:1px solid var(--border);}}
    .hero-label{{font-family:'DM Mono',monospace;font-size:.75rem;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);margin-bottom:1rem;display:block;}}
    .hero-title{{font-family:'Cormorant Garamond',serif;font-size:clamp(2.5rem,6vw,4rem);font-weight:700;line-height:1.1;margin-bottom:1rem;}}
    .hero-subtitle{{color:var(--muted);font-size:1.05rem;max-width:560px;}}
    .post-count{{font-family:'DM Mono',monospace;font-size:.78rem;color:var(--muted);margin-top:1.5rem;letter-spacing:.08em;}}
    .blog-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1.5rem;padding:48px 5% 80px;max-width:1400px;margin:0 auto;}}
    .blog-card{{background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:12px;padding:2rem;transition:border-color .25s,transform .25s;display:flex;flex-direction:column;gap:.85rem;}}
    .blog-card:hover{{border-color:var(--gold);transform:translateY(-3px);}}
    .card-meta{{display:flex;gap:1rem;align-items:center;flex-wrap:wrap;}}
    .category-pill{{background:rgba(196,154,60,.15);border:1px solid var(--gold);color:var(--gold);font-family:'DM Mono',monospace;font-size:.65rem;letter-spacing:.1em;text-transform:uppercase;padding:3px 10px;border-radius:100px;}}
    .card-date,.card-read{{font-family:'DM Mono',monospace;font-size:.72rem;color:var(--muted);}}
    .card-title{{font-family:'Cormorant Garamond',serif;font-size:1.45rem;font-weight:700;line-height:1.3;}}
    .card-title a{{color:var(--white);text-decoration:none;transition:color .2s;}}
    .card-title a:hover{{color:var(--gold);}}
    .card-excerpt{{color:var(--muted);font-size:.92rem;line-height:1.65;flex:1;}}
    .read-more{{color:var(--gold);text-decoration:none;font-size:.82rem;letter-spacing:.06em;font-family:'DM Mono',monospace;transition:opacity .2s;margin-top:.5rem;}}
    .read-more:hover{{opacity:.7;}}
    .no-posts{{text-align:center;padding:4rem;color:var(--muted);font-family:'DM Mono',monospace;font-size:.9rem;}}
    footer{{text-align:center;padding:2.5rem;border-top:1px solid var(--border);font-size:.8rem;color:var(--muted);font-family:'DM Mono',monospace;}}
    footer a{{color:var(--gold);text-decoration:none;}}
  </style>
</head>
<body>
  <nav>
    <a href="/" class="nav-logo">JP</a>
    <ul class="nav-links">
      <li><a href="/">Home</a></li>
      <li><a href="/blog/">Blog</a></li>
      <li><a href="/#connect">Connect</a></li>
    </ul>
  </nav>
  <section class="page-hero">
    <span class="hero-label">Perspectives &amp; Insights</span>
    <h1 class="hero-title">The Blog</h1>
    <p class="hero-subtitle">Thoughts on Technology, CleanTech, Real Estate, EdTech, Pharma, and building a better Goa — published daily.</p>
    <p class="post-count">{total} articles published</p>
  </section>
  <main class="blog-grid">
    {cards if cards else '<p class="no-posts">No posts yet — check back soon.</p>'}
  </main>
  <footer>
    <p>&copy; {TODAY.year} <a href="/">Jayesh Parab</a> &mdash; Goa, India</p>
  </footer>
</body>
</html>"""

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log(f"Blog Generator starting — {DATE_NICE}")
    log("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log("✗ FATAL: ANTHROPIC_API_KEY environment variable is not set.")
        log("  Fix: GitHub repo → Settings → Secrets → Actions → Add ANTHROPIC_API_KEY")
        sys.exit(1)

    log(f"✓ API key found (starts with: {api_key[:8]}...)")

    client = anthropic.Anthropic(api_key=api_key)
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    log(f"✓ Output folder ready: {BLOG_DIR}")

    new_posts = []
    for i, topic in enumerate(TOPIC_BUCKETS):
        log(f"\n[{i+1}/10] Topic: {topic[:55]}...")
        post = generate_post(client, topic, i)
        if not post:
            log(f"  ✗ Skipping post {i+1}")
            continue
        filepath = BLOG_DIR / f"{post['slug']}.html"
        filepath.write_text(post_html(post), encoding="utf-8")
        log(f"  ✓ Saved: {filepath}")
        new_posts.append(post)

    log(f"\n{'='*60}")
    log(f"Posts generated today: {len(new_posts)}/10")

    # Load existing manifest
    manifest_path = Path("blog/manifest.json")
    all_posts = []
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            all_posts = json.load(f)
        log(f"Loaded {len(all_posts)} existing posts from manifest")

    # Remove today's entries to avoid duplicates on re-run
    all_posts = [p for p in all_posts if p.get("date_raw") != DATE_STR]
    all_posts.extend(new_posts)

    # Save manifest and rebuild index
    manifest_path.write_text(json.dumps(all_posts, indent=2, ensure_ascii=False), encoding="utf-8")
    INDEX_FILE.write_text(index_html(all_posts), encoding="utf-8")

    log(f"✓ manifest.json updated ({len(all_posts)} total posts)")
    log(f"✓ blog/index.html rebuilt")
    log(f"\n✅ All done! {len(new_posts)} new posts live on jayeshparab.com/blog/")

if __name__ == "__main__":
    main()

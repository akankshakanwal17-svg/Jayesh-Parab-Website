"""
fix_existing_blogs.py  — ONE-TIME RUN
────────────────────────────────────────────────────────────
Patches all existing HTML files in blog/posts/ to:
  1. Add "Jayesh Parab" to meta keywords
  2. Add "Jayesh Parab" to meta description if missing
  3. Add "Jayesh Parab" to the JSON-LD structured data
  4. Ensure "Jayesh Parab" appears naturally in the body

Run once via GitHub Actions, then delete this file.
────────────────────────────────────────────────────────────
"""

import re
from pathlib import Path

BLOG_DIR = Path("blog/posts")

def patch_html(filepath: Path) -> bool:
    """Patch a single blog post HTML file. Returns True if changed."""
    html = filepath.read_text(encoding="utf-8")
    original = html
    changed = False

    # 1. Add "Jayesh Parab" to meta keywords if not already present
    def patch_keywords(m):
        content = m.group(1)
        if "Jayesh Parab" not in content:
            content = "Jayesh Parab, " + content
        return f'<meta name="keywords"           content="{content}">'
    html_new = re.sub(
        r'<meta name="keywords"\s+content="([^"]*)"[^>]*>',
        patch_keywords, html
    )
    if html_new != html:
        html = html_new
        changed = True

    # 2. Add "Jayesh Parab" to meta description if not present
    def patch_description(m):
        content = m.group(1)
        if "Jayesh Parab" not in content:
            content = content.rstrip(".") + " — by Jayesh Parab, Goa."
        return f'<meta name="description"               content="{content}">'
    html_new = re.sub(
        r'<meta name="description"\s+content="([^"]*)"[^>]*>',
        patch_description, html
    )
    if html_new != html:
        html = html_new
        changed = True

    # 3. Add "Jayesh Parab" to og:description if not present
    def patch_og_desc(m):
        content = m.group(1)
        if "Jayesh Parab" not in content:
            content = content.rstrip(".") + " — by Jayesh Parab."
        return f'<meta property="og:description"       content="{content}">'
    html_new = re.sub(
        r'<meta property="og:description"\s+content="([^"]*)"[^>]*>',
        patch_og_desc, html
    )
    if html_new != html:
        html = html_new
        changed = True

    # 4. Add author structured data (JSON-LD) before </head> if not already present
    if '"Jayesh Parab"' not in html or 'application/ld+json' not in html:
        jsonld = """  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "author": {
      "@type": "Person",
      "name": "Jayesh Parab",
      "url": "https://jayeshparab.com"
    },
    "publisher": {
      "@type": "Person",
      "name": "Jayesh Parab",
      "url": "https://jayeshparab.com"
    }
  }
  </script>"""
        html = html.replace("</head>", jsonld + "\n</head>")
        changed = True

    # 5. Ensure "Jayesh Parab" appears in the visible post body
    #    Insert a natural byline right after the <article class="post-body"> opening
    if "Jayesh Parab" not in html.split('<article')[1].split('</article>')[0]:
        byline = '<p class="byline" style="font-family:\'DM Mono\',monospace;font-size:.75rem;letter-spacing:.08em;color:rgba(255,255,255,.45);margin-bottom:2rem;">By <strong style="color:#C49A3C;">Jayesh Parab</strong></p>'
        html = html.replace('<a href="/blog/" class="back-btn">&#8592; All Posts</a>',
                            '<a href="/blog/" class="back-btn">&#8592; All Posts</a>\n    ' + byline)
        changed = True

    if changed:
        filepath.write_text(html, encoding="utf-8")
    return changed


def main():
    if not BLOG_DIR.exists():
        print("blog/posts/ folder not found. Nothing to patch.")
        return

    posts = list(BLOG_DIR.glob("*.html"))
    if not posts:
        print("No blog posts found to patch.")
        return

    print(f"Found {len(posts)} blog posts. Patching...")
    patched = 0
    for fp in sorted(posts):
        changed = patch_html(fp)
        status = "✓ patched" if changed else "— already OK"
        print(f"  {status}: {fp.name}")
        if changed:
            patched += 1

    print(f"\n✅ Done. {patched}/{len(posts)} files updated with 'Jayesh Parab' keyword.")

if __name__ == "__main__":
    main()

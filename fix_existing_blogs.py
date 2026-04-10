"""
fix_existing_blogs.py  v2  — ROBUST VERSION
────────────────────────────────────────────
Patches every HTML file in blog/posts/ to add
"Jayesh Parab" in 6 places per post:

  1. meta keywords   — first keyword
  2. meta description — "by Jayesh Parab"
  3. og:description  — "by Jayesh Parab"
  4. Visible byline  — "By Jayesh Parab" at top of article
  5. Closing line    — "— Jayesh Parab, Goa" at bottom
  6. JSON-LD         — structured author data Google reads

Uses plain string find/replace — no regex, guaranteed to work.
────────────────────────────────────────────
"""

from pathlib import Path

BLOG_DIR = Path("blog/posts")


def set_meta_content(html, attr_name, prepend="", append=""):
    """Find meta tag by name/property and update its content value."""
    search_key = f'"{attr_name}"'
    pos = html.find(search_key)
    if pos == -1:
        return html

    content_pos = html.find('content="', pos)
    if content_pos == -1:
        return html

    value_start = content_pos + len('content="')
    value_end   = html.find('"', value_start)
    if value_end == -1:
        return html

    current = html[value_start:value_end]
    new_val = current

    if prepend and prepend not in current:
        new_val = prepend + new_val

    if append and append not in current:
        new_val = new_val.rstrip(". ") + append

    if new_val == current:
        return html

    return html[:value_start] + new_val + html[value_end:]


def inject_byline(html):
    """Insert visible byline after the back button."""
    byline = (
        '\n    <p class="byline" style="font-family:\'DM Mono\','
        'monospace;font-size:.75rem;letter-spacing:.08em;'
        'color:rgba(255,255,255,.42);margin-bottom:2rem;">'
        'By <strong style="color:#C49A3C;">Jayesh Parab</strong></p>'
    )
    marker = '<a href="/blog/" class="back-btn">&#8592; All Posts</a>'
    if marker in html and "By <strong" not in html:
        html = html.replace(marker, marker + byline)
    return html


def inject_closing(html):
    """Add closing signature before the keywords row."""
    closing = (
        '\n    <p style="font-family:\'Cormorant Garamond\',serif;'
        'font-style:italic;font-size:1rem;color:rgba(255,255,255,.5);'
        'margin-top:2rem;padding-top:1.5rem;'
        'border-top:1px solid rgba(196,154,60,.15);">'
        '&#8212; <strong style="color:#C49A3C;font-style:normal;">'
        'Jayesh Parab</strong>, Goa</p>'
    )
    marker = '<div class="kw-row">'
    if marker in html and "Jayesh Parab</strong>, Goa" not in html:
        html = html.replace(marker, closing + "\n    " + marker, 1)
    return html


def add_jsonld(html, filepath):
    """Add JSON-LD structured data with Jayesh Parab as author."""
    if "application/ld+json" in html:
        return html

    slug  = filepath.stem
    parts = slug.split("-")
    date  = "-".join(parts[:3]) if len(parts) >= 3 else "2026-01-01"

    jsonld = f"""  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "datePublished": "{date}",
    "url": "https://jayeshparab.com/blog/posts/{slug}.html",
    "author": {{
      "@type": "Person",
      "name": "Jayesh Parab",
      "url": "https://jayeshparab.com"
    }},
    "publisher": {{
      "@type": "Person",
      "name": "Jayesh Parab",
      "url": "https://jayeshparab.com"
    }}
  }}
  </script>"""

    return html.replace("</head>", jsonld + "\n</head>", 1)


def patch_file(filepath):
    html = filepath.read_text(encoding="utf-8")
    original = html

    html = set_meta_content(html, "keywords",       prepend="Jayesh Parab, ")
    html = set_meta_content(html, "description",    append=" — by Jayesh Parab.")
    html = set_meta_content(html, "og:description", append=" — by Jayesh Parab.")
    html = inject_byline(html)
    html = inject_closing(html)
    html = add_jsonld(html, filepath)

    if html != original:
        filepath.write_text(html, encoding="utf-8")
        return True
    return False


def main():
    if not BLOG_DIR.exists():
        print(f"Folder '{BLOG_DIR}' not found.")
        return

    posts = sorted(BLOG_DIR.glob("*.html"))
    if not posts:
        print("No blog posts found in blog/posts/")
        return

    print(f"Found {len(posts)} posts. Patching...\n")
    patched = 0

    for fp in posts:
        changed = patch_file(fp)
        if changed:
            print(f"  PATCHED : {fp.name}")
            patched += 1
        else:
            print(f"  SKIPPED : {fp.name} (already has keyword)")

    print(f"\n{'='*50}")
    print(f"Done. {patched}/{len(posts)} files updated.")
    print("Each post now has 'Jayesh Parab' in:")
    print("  meta keywords / meta description / og:description")
    print("  visible byline / closing signature / JSON-LD")


if __name__ == "__main__":
    main()

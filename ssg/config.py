"""Site-wide configuration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONTENT_DIR = ROOT / "content"
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
OUTPUT_DIR = ROOT / "dist"

SITE_TITLE = "4n86rakam1"
# For <title> and og:site_name, where a search result is the only context the
# reader has. The header keeps the handle alone.
SITE_LONG_TITLE = "Shinya Murakami (4n86rakam1)"
SITE_URL = "https://4n86rakam1.com"
SITE_DESCRIPTION = "Security engineering notes and CTF writeups."
SITE_AUTHOR = "4n86rakam1"
SITE_LANGUAGE = "en"

# The order here is the order in the header.
NAV = (
    ("Blog", "/blog/"),
    ("Writeup", "/writeup/"),
    ("Search", "/search/"),
)

# Counted by fetching an image rather than by the script GoatCounter hands out:
# the pages here run no JavaScript, and tests/test_browser holds that as an
# invariant rather than an intention. The pixel cannot see a referrer or a
# screen size, which the script would have read from the browser.
ANALYTICS_COUNT_URL = "https://aut7phoo0aip.goatcounter.com/count"

# The footer holds two kinds of link and reads left to right: this site's own
# pages, then the only things on the page that lead away from it. Left is where
# everything belonging to the site already sits — the masthead, the trail, the
# headings — so the exits go at the far end of the last line.
FOOTER_PAGES = (("Privacy", "/privacy/"),)
FOOTER_PROFILES = (
    ("GitHub", "https://github.com/4n86rakam1"),
    ("LinkedIn", "https://www.linkedin.com/in/shinyamurakami/"),
)

# Both mean "this page is the directory itself"; the writeups use README.md.
INDEX_STEMS = ("index", "README")
MARKDOWN_SUFFIX = ".md"

BLOG_SEGMENT = "blog"
WRITEUP_SEGMENT = "writeup"
SEARCH_SEGMENT = "search"

# An allowlist rather than a skip list: the writeups arrive from a repository
# this one does not control. A missing entry here leaves a file unpublished; a
# missing entry in the other kind of list publishes one.
PUBLISHED_ASSET_SUFFIXES = frozenset(
    {".gif", ".ipynb", ".jpeg", ".jpg", ".png", ".py", ".svg", ".txt", ".webp"}
)

# Republished as WebP on the way out. GIF is left out because an animated one
# would arrive as a still, and SVG because it is already the smaller of the two.
# Which of WebP's two encodings each image gets is decided per file, in
# `ssg.images`, from what the file turns out to weigh either way.
IMAGE_SOURCE_SUFFIXES = frozenset({".jpeg", ".jpg", ".png"})
IMAGE_TARGET_SUFFIX = ".webp"
IMAGE_LOSSY_QUALITY = 82
# A lossy encoding has to be clearly smaller to be worth what it throws away,
# not smaller by a byte.
IMAGE_LOSSY_SIZE_RATIO = 2 / 3

INDEX_FILENAME = "index.html"
SITEMAP_FILENAME = "sitemap.xml"
NOT_FOUND_FILENAME = "404.html"

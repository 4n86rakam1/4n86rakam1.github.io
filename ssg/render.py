"""Markdown to HTML conversion.

The extension set mirrors what MkDocs enabled: `toc` derives the heading anchor
IDs, and keeping its default slugify leaves the ~350 in-page links inside the
existing writeups resolving unchanged.
"""

import re
from urllib.parse import unquote

import markdown

from .config import (
    IMAGE_SOURCE_SUFFIXES,
    IMAGE_TARGET_SUFFIX,
    INDEX_STEMS,
    MARKDOWN_SUFFIX,
)
from .content import slugify_segment

# Links between writeups name the other page's Markdown file, the way MkDocs
# resolved them; published pages are directories.
SOURCE_LINK_PATTERN = re.compile(
    rf'(?<=href=")([^"]+?){re.escape(MARKDOWN_SUFFIX)}(#[^"]*)?(?=")'
)
# Anything with a scheme, and protocol-relative links, belong to another host.
EXTERNAL_LINK_PATTERN = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//", re.IGNORECASE)

# Spelled the way IMAGE_TAG_PATTERN spells a tag, for the same reason: an
# attribute value may hold the `>` that would otherwise end the match early.
ANCHOR_TAG_PATTERN = re.compile(
    r"""<a\b((?:[^>"']|"[^"]*"|'[^']*')*)>""", re.IGNORECASE
)
HREF_PATTERN = re.compile(
    r"""(?<![-\w])href\s*=\s*(?P<quote>["'])(?P<url>[^"']*)(?P=quote)""", re.IGNORECASE
)
# `noreferrer` is left off: the sites these writeups cite deserve to see where
# the reader came from, and `noopener` alone is what closes the opener handle.
EXTERNAL_LINK_ATTRIBUTES = ' target="_blank" rel="noopener"'

HIGHLIGHT_CSS_CLASS = "highlight"

# Markdown writes these tags, so the hints go on after conversion; the templates'
# own images are layout and stay eager. The tag ends at the first `>` outside a
# quoted value, so an alt text of `a > b` does not cut it in half.
IMAGE_TAG_PATTERN = re.compile(
    r"""<img\b((?:[^>"']|"[^"]*"|'[^']*')*)>""", re.IGNORECASE
)
IMAGE_LOADING_HINTS = (("loading", "lazy"), ("decoding", "async"))

# The build republishes the writeups' images as WebP, so the tag has to name
# what was written rather than what the Markdown wrote. Spelled the way
# IMAGE_TAG_PATTERN and the loading hints already spell an attribute — either
# quote, space around the `=` — because a tag this misses is a tag that still
# gets its hints and then points at a file the build renamed. `(?<![-\w])`
# keeps `data-src` out, which nothing converts. The suffix ends the path,
# before any query or fragment: `shot.png?v=2` keeps its query, and
# `notes.png.txt` is not an image. The suffixes come from the set the build
# converts from, so that half cannot drift.
IMAGE_SOURCE_PATTERN = re.compile(
    r"(?<![-\w])(?P<name>src)(?P<gap>\s*=\s*)(?P<quote>[\"'])(?P<path>[^\"'?#]*)(?:"
    + "|".join(re.escape(suffix) for suffix in sorted(IMAGE_SOURCE_SUFFIXES))
    + r")(?=[?#]|(?P=quote))",
    re.IGNORECASE,
)

# md_in_html hands a raw HTML block through untouched unless its tag asks for the
# contents to be parsed, and the writeups are written without the attribute. Only
# a block starting its line is touched: md_in_html cannot lift an indented one out
# of a list item, and leaks the attribute into the output instead.
DETAILS_TAG_PATTERN = re.compile(r"^<details\b(?![^>]*\bmarkdown=)", re.IGNORECASE)
DETAILS_MARKDOWN_ATTRIBUTE = '<details markdown="1"'
# Skipped rather than rewritten, so a writeup showing HTML in a code block does
# not display an attribute nobody wrote.
FENCE_PATTERN = re.compile(r"^\s*(?:```|~~~)")

# A heading a reader can link to without reading the URL bar. `#` rather than
# the conventional pilcrow because the headings already wear their Markdown
# level, and the class is the one `toc` writes.
PERMALINK_GLYPH = "#"
PERMALINK_CLASS = "headerlink"
# Read in place of a bare "#", and shown as the tooltip, from one string.
PERMALINK_LABEL = "Permanent link to this heading"
PERMALINK_ANCHOR_PATTERN = re.compile(rf'<a class="{PERMALINK_CLASS}"')
# The anchor sits inside `data-pagefind-body`, so without the first attribute
# the glyph joins the heading in the search index and in the excerpt printed
# under a result.
PERMALINK_ANCHOR_REPLACEMENT = (
    f'<a data-pagefind-ignore aria-label="{PERMALINK_LABEL}" class="{PERMALINK_CLASS}"'
)

# The anchor is a child of the heading, so a reader skimming by heading hears the
# anchor's name run onto the end of the heading's own: "Overview" arrives as
# "OverviewPermanent link to this heading", once per heading. Naming the heading
# outright settles it, and unlike hiding the anchor it leaves the anchor to the
# readers who would use it. Spelled the way the image tags are, because a heading
# carrying an attr_list class is still a tag whose value may hold a `>`. The
# lazy quantifier stops at the right anchor: a heading holds at most one.
HEADING_WITH_PERMALINK_PATTERN = re.compile(
    r"<h(?P<level>[1-6])(?P<attributes>(?:[^>\"']|\"[^\"]*\"|'[^']*')*)>"
    rf'(?P<text>.*?)(?=<a[^>]*class="{PERMALINK_CLASS}")',
    re.DOTALL,
)
MARKUP_PATTERN = re.compile(r"<[^>]+>")
# Markdown escapes `<`, `>` and `&` in text but leaves `"` alone, and the name is
# going into a double-quoted attribute.
ATTRIBUTE_UNSAFE = {'"': "&quot;"}

MARKDOWN_EXTENSIONS = (
    "toc",
    "tables",
    "fenced_code",
    "codehilite",
    "attr_list",
    "footnotes",
    "md_in_html",
    # The writeups indent fences inside list items and <details>; plain
    # fenced_code drops the code in 22 of them, measured against MkDocs output.
    "pymdownx.superfences",
)

# Guessing turns unlabelled fences into arbitrary languages, and the writeups
# label theirs. The css_class matches superfences, so one stylesheet covers both.
MARKDOWN_EXTENSION_CONFIGS = {
    "codehilite": {"guess_lang": False, "css_class": HIGHLIGHT_CSS_CLASS},
    # No slugify here: the default is what the ~350 in-page links in the
    # writeups were written against.
    "toc": {
        "permalink": PERMALINK_GLYPH,
        "permalink_title": PERMALINK_LABEL,
    },
}

PYGMENTS_STYLE = "default"

# A colour in the generated sheet, so it is read off the sheet rather than off
# the whole stylesheet: `background-color` ends in the same eight characters.
HIGHLIGHT_COLOR_PATTERN = re.compile(r"(?<![-\w])color:\s*(#[0-9A-Fa-f]{3,6})")
# The default style leaves four token colours short of 4.5:1 against the code
# background this site sets. Three sit a hair under and are darkened by the
# smallest step that clears it — a shift of well under the difference a trained
# eye can pick out, so the highlighting reads as it did.
#
# The fourth is left alone. Text.Whitespace, at 1.77:1, colours the whitespace
# characters themselves rather than anything a reader has to make out, and
# taking it to 4.5:1 would run visible grey marks through every code block.
PYGMENTS_COLOR_OVERRIDES = {
    "#3D7B7B": "#3d7a7a",
    "#A2F": "#a822fc",
    "#767600": "#757500",
}


def make_renderer():
    return markdown.Markdown(
        extensions=list(MARKDOWN_EXTENSIONS),
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )


def _slugify_link_path(path):
    """Apply the slug rules the link's target directories went through.

    Markdown percent-encodes what it finds, so the segments are decoded first.
    """
    # Splitting on "/" drops the leading slash that marks a site-absolute link.
    root = "/" if path.startswith("/") else ""
    return root + "/".join(
        slugify_segment(unquote(part)) for part in path.split("/") if part
    )


def _rewrite_source_link(match):
    target, fragment = match.group(1), match.group(2) or ""
    if EXTERNAL_LINK_PATTERN.match(target):
        return match.group(0)
    head, _, stem = target.rpartition("/")
    directory = _slugify_link_path(head if stem in INDEX_STEMS else target)
    return f"{directory}/{fragment}" if directory else f"./{fragment}"


def rewrite_source_links(html):
    """Point links at published URLs instead of the Markdown files they name."""
    return SOURCE_LINK_PATTERN.sub(_rewrite_source_link, html)


def _open_in_a_new_tab(match):
    attributes = match.group(1)
    href = HREF_PATTERN.search(attributes)
    if href is None or not EXTERNAL_LINK_PATTERN.match(href.group("url")):
        return match.group(0)
    # An author who set one decided where the link opens on purpose.
    if re.search(r"(?:^|\s)target\s*=", attributes, re.IGNORECASE):
        return match.group(0)
    return f"<a{attributes}{EXTERNAL_LINK_ATTRIBUTES}>"


def open_external_links_in_a_new_tab(html):
    """Send a link to another host to its own tab, marked as one in the sheet."""
    return ANCHOR_TAG_PATTERN.sub(_open_in_a_new_tab, html)


def label_permalinks(html):
    """Name the heading anchors for a reader who hears them, and hide them from
    the search index."""
    return PERMALINK_ANCHOR_PATTERN.sub(PERMALINK_ANCHOR_REPLACEMENT, html)


def _name_the_heading(match):
    text = MARKUP_PATTERN.sub("", match.group("text")).strip()
    if not text:
        return match.group(0)
    for character, escape in ATTRIBUTE_UNSAFE.items():
        text = text.replace(character, escape)
    return (
        f"<h{match.group('level')}{match.group('attributes')} "
        f'aria-label="{text}">{match.group("text")}'
    )


def name_headings_carrying_a_permalink(html):
    """Give a heading its own text as its name, so the anchor inside it stops
    being read as part of it."""
    return HEADING_WITH_PERMALINK_PATTERN.sub(_name_the_heading, html)


def _add_loading_hints(match):
    attributes = match.group(1)
    # An author who set one of these decided it on purpose. The name has to start
    # an attribute: a src of `shot.png?loading=1` is not a loading attribute.
    missing = " ".join(
        f'{name}="{value}"'
        for name, value in IMAGE_LOADING_HINTS
        if not re.search(rf"(?:^|\s){name}\s*=", attributes, re.IGNORECASE)
    )
    return f"<img {missing}{attributes}>" if missing else match.group(0)


def add_loading_hints(html):
    """Defer the images until the reader scrolls to them."""
    return IMAGE_TAG_PATTERN.sub(_add_loading_hints, html)


def _published_image_source(match):
    path = match.group("path")
    # An image on another host was not ours to convert, and neither is a
    # site-absolute one: the writeups name their images by relative path, while
    # `/static/` holds the files the build copies verbatim. Renaming
    # og-image.png there would leave the share card pointing at nothing.
    if EXTERNAL_LINK_PATTERN.match(path) or path.startswith("/"):
        return match.group(0)
    return (
        f"{match.group('name')}{match.group('gap')}{match.group('quote')}"
        f"{path}{IMAGE_TARGET_SUFFIX}"
    )


def _point_image_at_published_file(match):
    return f"<img{IMAGE_SOURCE_PATTERN.sub(_published_image_source, match.group(1))}>"


def point_images_at_published_files(html):
    """Name the WebP the build wrote, not the file the Markdown named."""
    return IMAGE_TAG_PATTERN.sub(_point_image_at_published_file, html)


def raise_highlight_contrast(css):
    """Lift the highlighting colours that fall short of the contrast ratio."""
    return HIGHLIGHT_COLOR_PATTERN.sub(
        lambda match: (
            "color: " + PYGMENTS_COLOR_OVERRIDES.get(match.group(1), match.group(1))
        ),
        css,
    )


def mark_details_contents_as_markdown(text):
    """Ask the parser to read what is inside a <details> block as Markdown."""
    inside_fence = False
    lines = []
    for line in text.splitlines(keepends=True):
        if FENCE_PATTERN.match(line):
            inside_fence = not inside_fence
        elif not inside_fence:
            line = DETAILS_TAG_PATTERN.sub(DETAILS_MARKDOWN_ATTRIBUTE, line)
        lines.append(line)
    return "".join(lines)


def render(renderer, text):
    """The renderer is reset so one document's state cannot leak into the next."""
    renderer.reset()
    html = renderer.convert(mark_details_contents_as_markdown(text))
    # In execution order, because the order is load-bearing: the image passes
    # run after the link rewrite that may have moved an address, and the heading
    # is named after the anchor inside it is there to be excluded.
    html = rewrite_source_links(html)
    html = point_images_at_published_files(html)
    html = add_loading_hints(html)
    html = open_external_links_in_a_new_tab(html)
    html = label_permalinks(html)
    return name_headings_carrying_a_permalink(html)

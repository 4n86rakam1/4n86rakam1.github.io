"""Markdown to HTML conversion.

The extension set mirrors what MkDocs enabled: `toc` derives the heading anchor
IDs, and keeping its default slugify leaves the ~350 in-page links inside the
existing writeups resolving unchanged.
"""

import re
from urllib.parse import unquote

import markdown

from .config import INDEX_STEMS, MARKDOWN_SUFFIX
from .content import slugify_segment

# Links between writeups name the other page's Markdown file, the way MkDocs
# resolved them; published pages are directories.
SOURCE_LINK_PATTERN = re.compile(
    rf'(?<=href=")([^"]+?){re.escape(MARKDOWN_SUFFIX)}(#[^"]*)?(?=")'
)
# Anything with a scheme, and protocol-relative links, belong to another host.
EXTERNAL_LINK_PATTERN = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//", re.IGNORECASE)

HIGHLIGHT_CSS_CLASS = "highlight"

# Markdown writes these tags, so the hints go on after conversion; the templates'
# own images are layout and stay eager. The tag ends at the first `>` outside a
# quoted value, so an alt text of `a > b` does not cut it in half.
IMAGE_TAG_PATTERN = re.compile(
    r"""<img\b((?:[^>"']|"[^"]*"|'[^']*')*)>""", re.IGNORECASE
)
IMAGE_LOADING_HINTS = (("loading", "lazy"), ("decoding", "async"))

# md_in_html hands a raw HTML block through untouched unless its tag asks for the
# contents to be parsed, and the writeups are written without the attribute. Only
# a block starting its line is touched: md_in_html cannot lift an indented one out
# of a list item, and leaks the attribute into the output instead.
DETAILS_TAG_PATTERN = re.compile(r"^<details\b(?![^>]*\bmarkdown=)", re.IGNORECASE)
DETAILS_MARKDOWN_ATTRIBUTE = '<details markdown="1"'
# Skipped rather than rewritten, so a writeup showing HTML in a code block does
# not display an attribute nobody wrote.
FENCE_PATTERN = re.compile(r"^\s*(?:```|~~~)")

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
}

PYGMENTS_STYLE = "default"


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
    return add_loading_hints(rewrite_source_links(html))

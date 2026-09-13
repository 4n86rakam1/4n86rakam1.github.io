"""Markdown to HTML conversion.

The extension set deliberately mirrors what MkDocs enables, because `toc` is
what derives heading anchor IDs. Keeping its default slugify means the ~350
in-page links inside the existing writeups resolve unchanged after migration.
"""

import re
from urllib.parse import unquote

import markdown

from .config import INDEX_STEMS, MARKDOWN_SUFFIX
from .content import slugify_segment

# Links between writeups point at the other page's Markdown file, which is what
# MkDocs used to resolve. Published pages are directories, so the extension has
# to be turned back into the URL it stands for.
SOURCE_LINK_PATTERN = re.compile(
    rf'(?<=href=")([^"]+?){re.escape(MARKDOWN_SUFFIX)}(#[^"]*)?(?=")'
)
# Anything with a scheme, and protocol-relative links, belong to another host.
EXTERNAL_LINK_PATTERN = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//", re.IGNORECASE)

HIGHLIGHT_CSS_CLASS = "highlight"

MARKDOWN_EXTENSIONS = (
    "toc",
    "tables",
    "fenced_code",
    "codehilite",
    "attr_list",
    "footnotes",
    "md_in_html",
    # The writeups indent fences inside list items and wrap them in <details>.
    # Plain fenced_code drops the code in 22 of them; superfences keeps all of
    # them intact, measured against the published MkDocs output.
    "pymdownx.superfences",
)

# Guessing turns unlabelled fences into arbitrary languages; the writeups label
# theirs, so an unlabelled fence is better left as plain text. The css_class
# matches what superfences emits, so one stylesheet covers both extensions.
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
    """Apply the URL slug rules a link's target directories went through.

    Markdown percent-encodes what it finds in the source, so the segments are
    decoded first and then slugified the same way the pages themselves were.
    """
    # A leading slash is the difference between a site-absolute link and a
    # relative one, and splitting on "/" drops it.
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


def render(renderer, text):
    """The renderer is reset so one document's state cannot leak into the next."""
    renderer.reset()
    return rewrite_source_links(renderer.convert(text))

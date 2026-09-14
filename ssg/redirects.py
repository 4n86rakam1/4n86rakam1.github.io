"""Receivers for the URLs the MkDocs-era site published.

GitHub Pages serves static files only, so a 301 is not on offer.
"""

from pathlib import Path

from .config import INDEX_FILENAME

# `?` opens a query string and `#` a fragment, so nothing placed after one is
# ever requested. This broke twelve links on the MkDocs site.
UNREQUESTABLE = frozenset("?#")


def is_requestable(parts):
    return not any(UNREQUESTABLE & set(part) for part in parts)


def moved(pages):
    """Pages whose published URL differs from the path the source spells."""
    return [page for page in pages if page.source_parts != page.url_parts]


def unrequestable(pages):
    """The old paths `collect` drops, named so a test can pin which they are."""
    return [page for page in moved(pages) if not is_requestable(page.source_parts)]


def collect(pages):
    """Return (output path, destination URL) per old path, sorted for a stable build.

    Slugifying a slug changes nothing, so no receiver lands on a published page.
    """
    return sorted(
        (Path(*page.source_parts, INDEX_FILENAME), page.url)
        for page in moved(pages)
        if is_requestable(page.source_parts)
    )

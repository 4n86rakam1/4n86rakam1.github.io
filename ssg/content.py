"""Content discovery and the page model.

The source tree mirrors the published URL tree, so routing stays a single rule
and no page needs per-file path configuration.
"""

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

from .config import CONTENT_DIR, INDEX_FILENAME, INDEX_STEMS, MARKDOWN_SUFFIX

# Writeup pages carry no front matter, so their title has to come from the
# leading `# ` heading.
HEADING_PATTERN = re.compile(r"^#[ \t]+(.+?)[ \t]*$", re.MULTILINE)

# A directory named `Where's skat?` becomes a URL whose `?` starts a query
# string, and every relative link on that page then resolves against the parent
# directory. Drop what changes how a URL parses, and fold the rest into `_`.
DROPPED_IN_SEGMENT = re.compile(r"[\"'?#]+")
SEPARATOR_IN_SEGMENT = re.compile(r"[^A-Za-z0-9._()-]+")


def slugify_segment(segment):
    cleaned = DROPPED_IN_SEGMENT.sub("", segment)
    return SEPARATOR_IN_SEGMENT.sub("_", cleaned).strip("_") or segment


@dataclass
class Page:
    source: Path
    meta: dict = field(default_factory=dict)
    body: str = ""
    html: str = ""

    @property
    def url_parts(self):
        parts = list(self.source.relative_to(CONTENT_DIR).with_suffix("").parts)
        if parts and parts[-1] in INDEX_STEMS:
            parts.pop()
        return [slugify_segment(part) for part in parts]

    @property
    def url(self):
        return "/" + "".join(f"{part}/" for part in self.url_parts)

    @property
    def output_path(self):
        return Path(*self.url_parts, INDEX_FILENAME)

    @property
    def title(self):
        heading = HEADING_PATTERN.search(self.body)
        return (
            self.meta.get("title")
            or (heading.group(1) if heading else None)
            or self.source.stem
        )

    @property
    def description(self):
        return self.meta.get("description", "")

    @property
    def date(self):
        value = self.meta.get("date")
        if isinstance(value, dt.datetime):
            return value.date()
        return value

    @property
    def tags(self):
        # Recorded but not published: the tag pages come back when there are
        # enough posts for them to help rather than pad.
        return list(self.meta.get("tags") or [])

    @property
    def is_draft(self):
        return bool(self.meta.get("draft"))

    @property
    def section(self):
        # A page directly under the content root belongs to no section: the
        # front page and any top-level page stand on their own.
        parts = self.url_parts
        return parts[0] if len(parts) > 1 else ""


def load_page(path):
    post = frontmatter.load(path)
    return Page(source=path, meta=dict(post.metadata), body=post.content)


def discover(content_dir):
    pages = [
        load_page(path) for path in sorted(content_dir.rglob(f"*{MARKDOWN_SUFFIX}"))
    ]
    return [page for page in pages if not page.is_draft]

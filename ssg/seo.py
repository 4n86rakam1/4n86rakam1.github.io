"""Metadata derived from a page: its summary line and its JSON-LD block.

The JSON-LD is assembled here rather than in a template because escaping into an
HTML attribute and escaping into a script element are different rules, and Jinja
only knows the first.
"""

import json
import re

from .config import (
    BLOG_SEGMENT,
    SITE_AUTHOR,
    SITE_DESCRIPTION,
    SITE_LONG_TITLE,
    SITE_TITLE,
    SITE_URL,
    WRITEUP_SEGMENT,
)

# Short enough that a search result shows all of it rather than cutting mid-word.
SUMMARY_LIMIT = 160
ELLIPSIS = "…"

FENCE_PATTERN = re.compile(r"^(?:```|~~~)")
# Stripped rather than skipped: a writeup opens with the challenge text quoted,
# which is the best summary the page has.
QUOTE_MARKER_PATTERN = re.compile(r"^>[ \t]?")
# Headings, tables, raw HTML, list items and standalone images are structure.
SKIPPED_LINE_PATTERN = re.compile(r"^(?:#|\||<|!\[|[-*+][ \t]|\d+\.[ \t])")
# A flag on a line of its own is the answer, not a sentence about it: 14 writeups
# would otherwise be shared with one as their description. A sentence that
# mentions the flag format is prose and stays.
FLAG_LINE_PATTERN = re.compile(r"^[A-Za-z0-9_]{2,}\{[^{}]*\}$")

IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
FOOTNOTE_PATTERN = re.compile(r"\[\^[^\]]*\]")
LINK_PATTERN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
# Underscores hold identifiers such as country_db together, and underscore
# emphasis is not how these documents are written.
EMPHASIS_PATTERN = re.compile(r"[*`~]+")
WHITESPACE_PATTERN = re.compile(r"\s+")

SCHEMA_CONTEXT = "https://schema.org"
WEBSITE_TYPE = "WebSite"
PERSON_TYPE = "Person"
# A writeup is a technical article; a post is not necessarily one.
ARTICLE_TYPES = {BLOG_SEGMENT: "BlogPosting", WRITEUP_SEGMENT: "TechArticle"}

FRONT_PAGE_URL = "/"
SHARE_IMAGE_PATH = "/static/og-image.png"

# `<` would end the script element early and `&` starts an entity in the markup
# around it; JSON reads the escapes back as the characters.
SCRIPT_UNSAFE = {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026"}


def absolute_url(path):
    return SITE_URL + path


def _flatten(text):
    text = IMAGE_PATTERN.sub("", text)
    text = FOOTNOTE_PATTERN.sub("", text)
    text = LINK_PATTERN.sub(r"\1", text)
    text = HTML_TAG_PATTERN.sub("", text)
    text = EMPHASIS_PATTERN.sub("", text)
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def _truncate(text, limit):
    if len(text) <= limit:
        return text
    head, space, _ = text[: limit - 1].rstrip().rpartition(" ")
    return (head if space else text[: limit - 1]).rstrip() + ELLIPSIS


def summarize(body, limit=SUMMARY_LIMIT):
    """Flatten the first prose paragraph of a document into one line."""
    paragraph = []
    inside_fence = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if FENCE_PATTERN.match(line):
            inside_fence = not inside_fence
            continue
        if inside_fence:
            continue
        line = QUOTE_MARKER_PATTERN.sub("", line).strip()
        if (
            not line
            or SKIPPED_LINE_PATTERN.match(line)
            or FLAG_LINE_PATTERN.match(line)
        ):
            if paragraph:
                break
            continue
        paragraph.append(line)
    return _truncate(_flatten(" ".join(paragraph)), limit)


def _author():
    return {"@type": PERSON_TYPE, "name": SITE_AUTHOR}


def _website_data(page):
    return {
        "@context": SCHEMA_CONTEXT,
        "@type": WEBSITE_TYPE,
        "name": SITE_LONG_TITLE,
        "alternateName": SITE_TITLE,
        "url": absolute_url(page.url),
        "description": page.description or SITE_DESCRIPTION,
        "author": _author(),
    }


def _article_data(page, schema_type):
    data = {
        "@context": SCHEMA_CONTEXT,
        "@type": schema_type,
        "headline": page.title,
        "url": absolute_url(page.url),
        "image": absolute_url(SHARE_IMAGE_PATH),
        "author": _author(),
        "publisher": _author(),
    }
    if page.description:
        data["description"] = page.description
    # Only the posts carry a date: a writeup is dated by its CTF, which is not
    # when the page was written.
    if page.date:
        data["datePublished"] = page.date.isoformat()
    return data


def as_script_json(data):
    """Serialise for embedding directly in a script element."""
    text = json.dumps(data, ensure_ascii=False)
    for character, escape in SCRIPT_UNSAFE.items():
        text = text.replace(character, escape)
    return text


def structured_data(page):
    """The JSON-LD for a page, or an empty string when schema.org names nothing
    the page is: a listing, or a standalone page that is neither."""
    if page.url == FRONT_PAGE_URL:
        return as_script_json(_website_data(page))
    schema_type = ARTICLE_TYPES.get(page.section)
    if not schema_type:
        return ""
    return as_script_json(_article_data(page, schema_type))

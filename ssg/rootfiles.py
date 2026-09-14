"""The files at the site root that are read by machines rather than people.

All three are generated: each carries a page list or a date that a hand-written
copy would get wrong by the next commit without anything failing to say so.
"""

import datetime as dt
from pathlib import Path

from .config import (
    SITE_DESCRIPTION,
    SITE_LONG_TITLE,
    SITE_TITLE,
    SITE_URL,
    SITEMAP_FILENAME,
)

ROBOTS_FILENAME = "robots.txt"
LLMS_FILENAME = "llms.txt"
WELL_KNOWN_DIR = ".well-known"
SECURITY_FILENAME = "security.txt"
SECURITY_PATH = Path(WELL_KNOWN_DIR, SECURITY_FILENAME)

# The advisory form, so no mailbox is published here to be scraped.
SECURITY_CONTACT = (
    "https://github.com/4n86rakam1/4n86rakam1.github.io/security/advisories/new"
)
# RFC 9116 asks for a year at most. Taking it from the build date is the point:
# a literal in the file expires while the site keeps serving it.
SECURITY_LIFETIME = dt.timedelta(days=365)
SECURITY_LANGUAGES = "en, ja"
EXPIRES_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def absolute(url):
    return SITE_URL + url


def build_robots():
    """Nothing is withheld, so the file exists for the sitemap line alone."""
    return "\n".join(
        (
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {absolute('/' + SITEMAP_FILENAME)}",
            "",
        )
    )


def build_security(issued):
    """Return the security.txt for a build run on `issued` (a date)."""
    expires = dt.datetime.combine(issued + SECURITY_LIFETIME, dt.time(tzinfo=dt.UTC))
    return "\n".join(
        (
            f"Contact: {SECURITY_CONTACT}",
            f"Expires: {expires.strftime(EXPIRES_FORMAT)}",
            f"Preferred-Languages: {SECURITY_LANGUAGES}",
            f"Canonical: {absolute('/' + SECURITY_PATH.as_posix())}",
            "",
        )
    )


def link_line(url, title, note):
    line = f"- [{title}]({absolute(url)})"
    return f"{line}: {note}" if note else line


def build_llms(posts, ctfs):
    """Return the llms.txt index: a curated entry point, not a copy of the
    sitemap.

    The 200-odd challenge pages are reached through their CTF, which is how a
    reader reaches them too. `/search/` is a box that only fills in once a
    browser has run its script.
    """
    lines = [
        f"# {SITE_TITLE}",
        "",
        f"> {SITE_DESCRIPTION}",
        "",
        f"Written by {SITE_LONG_TITLE}. Every published URL is listed in "
        f"{absolute('/' + SITEMAP_FILENAME)}; this file links the pages worth "
        "starting from.",
    ]
    if posts:
        lines += ["", "## Blog", ""]
        lines += [
            link_line(post.url, post.title, post.description or str(post.date))
            for post in posts
        ]
    if ctfs:
        lines += ["", "## Writeup", ""]
        lines += [
            link_line(
                ctf["page"].url,
                ctf["page"].title,
                f"{ctf['count']} writeups" if ctf["count"] != 1 else "1 writeup",
            )
            for ctf in ctfs
        ]
    lines += [
        "",
        "## Optional",
        "",
        link_line(f"/{SITEMAP_FILENAME}", "Sitemap", "every published URL"),
        "",
    ]
    return "\n".join(lines)

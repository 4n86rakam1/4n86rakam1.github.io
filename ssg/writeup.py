"""Writeup collections: the CTF index.

Depth decides what a page is. /writeup/<ctf>/ is a CTF index and anything below
it is a challenge, which is the one rule the source tree already encodes.
"""

import datetime as dt
import re
from collections import defaultdict
from urllib.parse import urljoin

from .config import WRITEUP_SEGMENT

CTF_DEPTH = 2
LINK_PATTERN = re.compile(r'href="([^"]+)"')


def is_writeup(page):
    return page.section == WRITEUP_SEGMENT


def start_date(page):
    """Return the CTF start date, or None when the source does not record one."""
    value = page.meta.get("start_at")
    if isinstance(value, str):
        try:
            value = dt.datetime.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else None


def is_ctf_index(page):
    return is_writeup(page) and len(page.url_parts) == CTF_DEPTH


def collect_ctfs(pages):
    """Return CTF index pages, newest first; undated ones last, by name."""
    ctfs = [page for page in pages if is_ctf_index(page)]
    dated = [ctf for ctf in ctfs if start_date(ctf)]
    undated = [ctf for ctf in ctfs if not start_date(ctf)]
    dated.sort(key=start_date, reverse=True)
    undated.sort(key=lambda ctf: ctf.title.lower())
    return dated + undated


def challenges_of(ctf, pages):
    return [
        page
        for page in pages
        if is_writeup(page) and page.url != ctf.url and page.url.startswith(ctf.url)
    ]


def ctf_titles(pages):
    return {ctf.url: ctf.title for ctf in collect_ctfs(pages)}


def trail_within(page, titles):
    """The CTF and genre levels between /writeup/ and a challenge. The genre has
    no page of its own, so it comes back with no URL and shows as plain text."""
    if not is_writeup(page):
        return []
    parts = page.url_parts
    if len(parts) <= CTF_DEPTH:
        return []
    ctf_url = "/" + "/".join(parts[:CTF_DEPTH]) + "/"
    # A CTF whose sources carry no README has no index page to link to.
    title = titles.get(ctf_url)
    trail = [(title or parts[CTF_DEPTH - 1], ctf_url if title else None)]
    if len(parts) > CTF_DEPTH + 1:
        trail.append((parts[CTF_DEPTH], None))
    return trail


def unlinked_writeups(ctf, challenges):
    """The writeups beneath a CTF that its own text does not already link to.

    Most READMEs carry a hand-written list, so generating a second one would
    print everything twice; a partial list would strand what it leaves out.
    """
    linked = {
        urljoin(ctf.url, href.split("#")[0]) for href in LINK_PATTERN.findall(ctf.html)
    }
    return [challenge for challenge in challenges if challenge.url not in linked]


def group_by_genre(challenges):
    """Pages that skip the genre level group under an empty name, sorting first."""
    groups = defaultdict(list)
    for page in challenges:
        parts = page.url_parts
        genre = parts[CTF_DEPTH] if len(parts) > CTF_DEPTH + 1 else ""
        groups[genre].append(page)
    for grouped in groups.values():
        grouped.sort(key=lambda page: page.title.lower())
    return sorted(groups.items())


def index_entries(pages, challenges_by_ctf):
    return [
        {
            "page": ctf,
            "date": start_date(ctf),
            "count": len(challenges_by_ctf[ctf.url]),
        }
        for ctf in collect_ctfs(pages)
    ]

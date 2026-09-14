"""What only a browser can tell us about the built site.

Two kinds of check. Layout invariants are measured, so they hold regardless of
which fonts the machine running them happens to have. Structure is pinned with
ARIA snapshots, which describe the accessibility tree rather than the pixels,
so a colour or spacing change does not make them fail and a change in meaning
does.
"""

import os
import re
from pathlib import Path

import pytest

from ssg.config import CONTENT_DIR, OUTPUT_DIR

SOURCE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

pytestmark = pytest.mark.browser

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
UPDATE = os.environ.get("UPDATE_SNAPSHOTS") == "1"

# Written out rather than imported, so it cannot agree with any address at all.
SITE_URL = "https://4n86rakam1.com"

PHONE = {"width": 375, "height": 812}
DESKTOP = {"width": 1280, "height": 900}

PAGES = [
    pytest.param("/", id="front"),
    pytest.param("/writeup/", id="writeup-index"),
    pytest.param("/blog/", id="blog-index"),
    pytest.param("/search/", id="search"),
]

# Only pages whose content does not move with the writeup repository: a listing
# would change on every new writeup and be reported as a regression.
SNAPSHOT_PAGES = [("front", "/"), ("search", "/search/")]

VIEWPORTS = [pytest.param(PHONE, id="phone"), pytest.param(DESKTOP, id="desktop")]


def writeup_sources_are_present():
    """Whether this checkout has the writeups at all.

    The sources, not the output: a skip decided by the output is a skip the
    build can cause, which is the failure these checks are here to catch.
    """
    return any((CONTENT_DIR / "writeup").glob("*/"))


def source_images_are_present():
    return any(
        path.suffix.lower() in SOURCE_IMAGE_SUFFIXES for path in CONTENT_DIR.rglob("*")
    )


def visit(page, site, path, viewport):
    page.set_viewport_size(viewport)
    response = page.goto(site + path)
    assert response is not None and response.ok, f"{path} did not load"
    return page


def horizontal_overflow(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth"
        " - document.documentElement.clientWidth"
    )


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_the_page_does_not_scroll_sideways(page, site, path, viewport):
    visit(page, site, path, viewport)
    overflow = horizontal_overflow(page)
    assert overflow <= 0, f"{path} overflows its viewport by {overflow}px"


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_a_writeup_holds_its_code_in_its_own_scroller(page, site, viewport):
    """The page not scrolling is covered elsewhere; what matters here is that
    something inside it does, which is what keeps the page still."""
    path = "/writeup/CakeCTF_2023/web/Country_DB/"
    if not page.request.get(site + path).ok:
        # Decided by this page's source: it may be absent or renamed, but if it
        # is here and the site does not serve it, the build lost it.
        assert not (
            CONTENT_DIR / "writeup" / "CakeCTF_2023" / "web" / "Country_DB"
        ).is_dir(), "the source of that writeup is here and the site does not serve it"
        pytest.skip("the writeup sources are not checked out")
    visit(page, site, path, viewport)
    scrollable = page.evaluate(
        "() => [...document.querySelectorAll('pre')]"
        ".filter(el => el.scrollWidth > el.clientWidth).length"
    )
    assert scrollable >= 1, "no code block scrolls, so nothing was constrained"
    assert horizontal_overflow(page) <= 0


# One of the ten MkDocs-era paths, named rather than looked up so the test fails
# if the receiver stops being written.
MOVED_URL = "/writeup/CSAW-CTF-2023-Quals/rev/rebug 1/"
MOVED_TO = "/writeup/CSAW-CTF-2023-Quals/rev/rebug_1/"


def writeups_are_checked_out(page, site):
    """Probes the destination, never the receiver.

    Probing the receiver would turn the one failure these tests exist to catch
    — it stopped being written — into a skip, because a missing receiver and
    absent sources 404 alike.
    """
    return page.request.get(site + MOVED_TO).ok


def test_an_old_url_lands_on_the_page_it_moved_to(page, site):
    if not writeups_are_checked_out(page, site):
        pytest.skip("the writeup sources are not checked out")
    page.goto(site + MOVED_URL)
    page.wait_for_url(site + MOVED_TO, timeout=10_000)


def test_an_old_url_moves_with_no_javascript(page, browser, site):
    """The meta refresh on its own. The script is the fast path, not the only
    one, and a reader who blocks scripts is exactly who follows an old link."""
    if not writeups_are_checked_out(page, site):
        pytest.skip("the writeup sources are not checked out")
    context = browser.new_context(java_script_enabled=False)
    try:
        scriptless = context.new_page()
        scriptless.goto(site + MOVED_URL)
        scriptless.wait_for_url(site + MOVED_TO, timeout=10_000)
    finally:
        context.close()


def test_the_search_box_renders(page, site):
    """Pagefind builds the input, so this fails if its index is missing."""
    if not (OUTPUT_DIR / "pagefind" / "pagefind-ui.js").is_file():
        pytest.fail(
            "the Pagefind index is missing, so the search page is empty; "
            "the build wipes dist, so run `uv run python -m pagefind --site dist` after it"
        )
    visit(page, site, "/search/", DESKTOP)
    page.wait_for_selector("#search input", timeout=10_000)


def test_the_tap_targets_are_reachable_on_a_phone(page, site):
    visit(page, site, "/", PHONE)
    heights = page.evaluate(
        "() => [...document.querySelectorAll('.site-nav a, .site-footer a')]"
        ".map(el => el.getBoundingClientRect().height)"
    )
    assert heights, "no navigation links were found"
    assert min(heights) >= 30, f"smallest tap target is {min(heights)}px tall"


@pytest.mark.parametrize("path", PAGES)
def test_the_page_is_canonical_at_the_address_it_was_served_from(page, site, path):
    """The built site is read here rather than a template, so this is what a
    crawler would be told after the whole build ran."""
    visit(page, site, path, DESKTOP)
    links = page.evaluate(
        "() => [...document.querySelectorAll('link[rel=canonical]')]"
        ".map(el => el.getAttribute('href'))"
    )
    assert links == [SITE_URL + path]


def a_page_nested_deep_in_the_writeups():
    """The four pages above sit at the top of the site; a writeup's address is
    slugified from directory names, which is the part that could go wrong."""
    for path in sorted(OUTPUT_DIR.rglob("index.html")):
        directory = path.relative_to(OUTPUT_DIR).parent
        if len(directory.parts) >= 3:
            return f"/{directory.as_posix()}/"
    return None


def test_a_writeup_is_canonical_at_its_slugified_address(page, site):
    path = a_page_nested_deep_in_the_writeups()
    if path is None:
        # Decided by the sources, not the output: asking the output whether it
        # has a nested page turns the build losing all of them into a skip.
        assert not writeup_sources_are_present(), (
            "the writeup sources are checked out and no nested page was built"
        )
        pytest.skip("the writeup sources are not checked out")
    visit(page, site, path, DESKTOP)
    link = page.evaluate(
        "() => document.querySelector('link[rel=canonical]').getAttribute('href')"
    )
    assert link == SITE_URL + path


def test_the_icon_and_the_share_image_are_published(page, site):
    for asset in ("/static/favicon.svg", "/static/og-image.png"):
        assert page.request.get(site + asset).ok, f"{asset} is missing from the output"


def test_the_front_page_describes_itself_in_a_way_a_parser_accepts(page, site):
    visit(page, site, "/", DESKTOP)
    data = page.evaluate(
        "() => JSON.parse("
        "document.querySelector('script[type=\"application/ld+json\"]').textContent)"
    )
    assert data["@type"] == "WebSite"
    assert data["url"] == SITE_URL + "/"


@pytest.mark.parametrize("path", PAGES)
def test_only_the_search_page_runs_javascript(page, site, path):
    """The structured data sits in a script element but is never executed;
    this is what keeps that from becoming an excuse to add a real one."""
    visit(page, site, path, DESKTOP)
    executable = page.evaluate(
        "() => [...document.querySelectorAll('script')]"
        ".filter(el => el.type !== 'application/ld+json').length"
    )
    if path == "/search/":
        assert executable >= 1, "the search page lost its script"
    else:
        assert executable == 0


def a_page_carrying_images():
    """The writeups decide which pages have screenshots, so the page to look at
    is found in the output rather than named here."""
    for path in sorted(OUTPUT_DIR.rglob("index.html")):
        if "<img" in path.read_text(encoding="utf-8"):
            directory = path.relative_to(OUTPUT_DIR).parent
            return "/" if directory == Path(".") else f"/{directory.as_posix()}/"
    return None


def test_the_images_in_a_writeup_load_when_they_are_reached(page, site):
    path = a_page_carrying_images()
    if path is None:
        # Same reason as above: a generator that stopped rendering images would
        # leave this test with nothing to look at and say so as a skip.
        assert not source_images_are_present(), (
            "the sources carry images and no page shows one"
        )
        pytest.skip("the writeup sources are not checked out")
    visit(page, site, path, DESKTOP)
    images = page.evaluate(
        "() => [...document.querySelectorAll('article img')].map(el => ({"
        "src: el.getAttribute('src'), loading: el.loading, decoding: el.decoding}))"
    )
    # Without this the check passes on any page that simply has no images.
    assert images, f"{path} was chosen for its images and the browser found none"
    eager = [
        image["src"]
        for image in images
        if image["loading"] != "lazy" or image["decoding"] != "async"
    ]
    assert not eager, f"images that are not deferred: {eager[:3]}"


# The footer links to personal profiles; the structure is what this pins.
EXTERNAL_URL = re.compile(r"(- /url: )https?://\S+")


def structure(snapshot):
    return EXTERNAL_URL.sub(r"\1<external>", snapshot.rstrip("\n"))


@pytest.mark.parametrize("name,path", SNAPSHOT_PAGES)
def test_the_page_structure_is_unchanged(page, site, name, path):
    visit(page, site, path, DESKTOP)
    actual = structure(page.locator("body").aria_snapshot())
    expected_file = SNAPSHOT_DIR / f"{name}.yaml"
    # Writing only under the flag keeps a run from changing the repository.
    if UPDATE:
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        expected_file.write_text(actual + "\n", encoding="utf-8")
        return
    if not expected_file.exists():
        pytest.fail(
            f"no snapshot for {name}; run with UPDATE_SNAPSHOTS=1, review it, commit it"
        )
    assert actual == expected_file.read_text(encoding="utf-8").rstrip("\n")

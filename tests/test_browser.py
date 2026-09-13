"""What only a browser can tell us about the built site.

Two kinds of check. Layout invariants are measured, so they hold regardless of
which fonts the machine running them happens to have. Structure is pinned with
ARIA snapshots, which describe the accessibility tree rather than the pixels,
so a colour or spacing change does not make them fail and a change in meaning
does.
"""

import os
from pathlib import Path

import pytest

from ssg.config import OUTPUT_DIR

pytestmark = pytest.mark.browser

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
UPDATE = os.environ.get("UPDATE_SNAPSHOTS") == "1"

PHONE = {"width": 375, "height": 812}
DESKTOP = {"width": 1280, "height": 900}

PAGES = [
    pytest.param("/", id="front"),
    pytest.param("/writeup/", id="writeup-index"),
    pytest.param("/blog/", id="blog-index"),
    pytest.param("/search/", id="search"),
]

# Only pages whose content does not move with the writeup repository are
# pinned; a listing would change on every new writeup and the snapshot would
# report that as a regression.
SNAPSHOT_PAGES = [("front", "/"), ("search", "/search/")]

VIEWPORTS = [pytest.param(PHONE, id="phone"), pytest.param(DESKTOP, id="desktop")]


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
        pytest.skip("the writeup sources are not checked out")
    visit(page, site, path, viewport)
    scrollable = page.evaluate(
        "() => [...document.querySelectorAll('pre')]"
        ".filter(el => el.scrollWidth > el.clientWidth).length"
    )
    assert scrollable >= 1, "no code block scrolls, so nothing was constrained"
    assert horizontal_overflow(page) <= 0


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


@pytest.mark.parametrize("name,path", SNAPSHOT_PAGES)
def test_the_page_structure_is_unchanged(page, site, name, path):
    visit(page, site, path, DESKTOP)
    actual = page.locator("body").aria_snapshot().rstrip("\n")
    expected_file = SNAPSHOT_DIR / f"{name}.yaml"
    # Writing only under the flag keeps a test run from leaving changes in the
    # repository behind it.
    if UPDATE:
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        expected_file.write_text(actual + "\n", encoding="utf-8")
        return
    if not expected_file.exists():
        pytest.fail(
            f"no snapshot for {name}; run with UPDATE_SNAPSHOTS=1, review it, commit it"
        )
    assert actual == expected_file.read_text(encoding="utf-8").rstrip("\n")

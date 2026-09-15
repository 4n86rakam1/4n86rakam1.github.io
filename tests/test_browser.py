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


LOCAL = "http://127.0.0.1"


def keep_the_network_out(context):
    """The suite serves the built site from 127.0.0.1 and has nothing to fetch
    from anywhere else, so any other address is a bug whatever it is. Today it
    is the counter, and a test run is not a visit: unblocked, every local run
    and every push files real page views against the live dashboard.

    Fitted to the context rather than the page. A route on a page covers that
    page, which left the one test below building its own context to count
    itself on every run.
    """
    context.route(lambda url: not url.startswith(LOCAL), lambda route: route.abort())
    return context


@pytest.fixture(autouse=True)
def keep_the_network_out_of_every_test(context):
    keep_the_network_out(context)


@pytest.fixture
def scriptless_context(browser):
    """The suite's only second context, so a new one cannot be opened without
    the block — which is the mistake that let the counter out the first time."""
    context = keep_the_network_out(browser.new_context(java_script_enabled=False))
    try:
        yield context
    finally:
        context.close()


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


def test_an_old_url_moves_with_no_javascript(page, scriptless_context, site):
    """The meta refresh on its own. The script is the fast path, not the only
    one, and a reader who blocks scripts is exactly who follows an old link."""
    if not writeups_are_checked_out(page, site):
        pytest.skip("the writeup sources are not checked out")
    scriptless = scriptless_context.new_page()
    scriptless.goto(site + MOVED_URL)
    scriptless.wait_for_url(site + MOVED_TO, timeout=10_000)


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


ARTICLE = re.compile(r"<article\b.*?</article>", re.DOTALL | re.IGNORECASE)


def a_page_carrying_images():
    """The writeups decide which pages have screenshots, so the page to look at
    is found in the output rather than named here. Only what the article holds
    is looked at, which is what the checks below go on to query: the pixel that
    counts the visit is an image too, and it is outside the article on every
    page, so a sweep of the whole file lands on the first page in the output."""
    for path in sorted(OUTPUT_DIR.rglob("index.html")):
        article = ARTICLE.search(path.read_text(encoding="utf-8"))
        if article and "<img" in article.group(0):
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


def test_the_images_in_a_writeup_are_really_there(page, site):
    """The tag's address and the file the build wrote are decided in two
    different places. Disagreeing is a broken image, which every check that
    reads the markup alone reports as fine."""
    path = a_page_carrying_images()
    if path is None:
        assert not source_images_are_present(), (
            "the sources carry images and no page shows one"
        )
        pytest.skip("the writeup sources are not checked out")
    visit(page, site, path, DESKTOP)
    # Deferred images do not fetch until they are reached, so the page is taken
    # to the bottom first and given the loads a moment to finish.
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_load_state("networkidle")
    missing = page.evaluate(
        "() => [...document.querySelectorAll('article img')]"
        ".filter(el => !el.complete || el.naturalWidth === 0)"
        ".map(el => el.getAttribute('src'))"
    )
    assert not missing, f"images the browser could not load: {missing[:3]}"


def test_the_first_tab_reaches_a_way_past_the_furniture(page, site):
    """Every page opens with the same header, nav and trail. The skip link is
    only any use if it is the first thing Tab reaches and is visible once it
    has been: hidden in a way that leaves it in the tab order is a link a
    keyboard reader lands on and cannot see."""
    visit(page, site, "/", DESKTOP)
    page.keyboard.press("Tab")
    focused = page.locator(":focus")
    assert focused.get_attribute("class") == "skip-link"
    assert focused.is_visible()
    target = focused.get_attribute("href")
    assert page.locator(target).count() == 1, f"{target} is not on the page"


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


def test_no_context_in_the_suite_files_a_page_view(page, scriptless_context, site):
    """What says the block still works, on both kinds of context the suite makes.
    An aborted request never finishes, so a finished one is a real view filed by
    a test — the failure that reading the fixture alone cannot detect, and the
    one that got past the first version of this test by watching only a page."""
    reached = []

    def watch(request):
        if "goatcounter" in request.url:
            reached.append(request.url)

    page.on("requestfinished", watch)
    visit(page, site, "/", DESKTOP)
    page.wait_for_load_state("networkidle")

    scriptless = scriptless_context.new_page()
    scriptless.on("requestfinished", watch)
    scriptless.goto(site + "/")
    scriptless.wait_for_load_state("networkidle")

    assert not reached, f"the test run counted itself: {reached}"


def test_no_test_opens_a_context_the_block_does_not_reach():
    """The block is fitted to a context, so a context built anywhere but the two
    fixtures above is one nothing blocks. That is exactly how the counter
    reached the live dashboard on every run of the suite once already."""
    source = Path(__file__).read_text(encoding="utf-8")
    built = re.findall(r"browser\.new_context\(", source)
    assert len(built) == 1, (
        f"{len(built)} contexts are built here; scriptless_context should be the"
        " only one, so that every context passes through keep_the_network_out"
    )


def test_a_heading_is_not_read_with_its_permalink_glued_on(page, site):
    """The anchor is a child of the heading, so the heading's name is computed
    from it too: unnamed, every heading reads as its text with "Permanent link
    to this heading" run onto the end, which is what a reader skimming with the
    H key hears on each one. Structural rather than a quoted string, so the page
    can be reworded without this needing an edit."""
    visit(page, site, "/privacy/", DESKTOP)
    snapshot = page.locator("article h2").first.aria_snapshot()
    name = re.search(r'- heading "([^"]*)"', snapshot).group(1)
    text = re.search(r"- text: (.*)", snapshot).group(1)
    assert name == text.strip(), snapshot

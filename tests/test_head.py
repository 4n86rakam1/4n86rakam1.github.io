"""What every template puts in the document head.

The templates are rendered directly rather than through a build, so a case is
one template and the context it is given. The addresses are written out here:
deriving them from the configuration would make the test agree with whatever
the generator produced.
"""

import datetime as dt
import json
import re

import pytest
from conftest import page

from ssg.build import make_environment

SITE = "https://4n86rakam1.com"

CANONICAL_PATTERN = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"')
ICON_PATTERN = re.compile(r'<link\s+rel="icon"\s+href="([^"]+)"[^>]*>')
JSON_LD_PATTERN = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
)


def built(relative_path, body="", **meta):
    """A page as the build hands it to a template: converted, with its source
    still attached for the URL and the description."""
    subject = page(relative_path, body=body, **meta)
    subject.html = "<p>Rendered.</p>"
    return subject


CASES = [
    {
        "id": "front",
        "template": "page.html",
        "context": {"page": built("index.md", body="Notes on security engineering.")},
        "path": "/",
        "og_type": "website",
        "json_ld": True,
        "og_description": True,
    },
    {
        "id": "post",
        "template": "post.html",
        "context": {
            "page": built(
                "blog/hello-world.md",
                body="A post about the site.",
                date=dt.date(2026, 9, 13),
            )
        },
        "path": "/blog/hello-world/",
        "og_type": "article",
        "json_ld": True,
        "og_description": True,
    },
    {
        "id": "writeup",
        "template": "writeup.html",
        "context": {
            "page": built(
                "writeup/SomeCTF_2023/web/Some_Page/index.md",
                body="# Some Page\n\n> Which country code is 'CA'?\n",
            )
        },
        "path": "/writeup/SomeCTF_2023/web/Some_Page/",
        "og_type": "article",
        "json_ld": True,
        "og_description": True,
    },
    {
        # A CTF index is links and nothing else, so its card may lack a description.
        "id": "ctf-index",
        "template": "writeup_ctf.html",
        "context": {
            "page": built(
                "writeup/SomeCTF_2023/README.md",
                body="# SomeCTF 2023\n\n- [Some Page](web/Some_Page/index.md)\n",
            ),
            "genres": [],
        },
        "path": "/writeup/SomeCTF_2023/",
        "og_type": "article",
        "json_ld": True,
        "og_description": False,
    },
    {
        "id": "blog-index",
        "template": "post_list.html",
        "context": {"title": "Blog", "posts": []},
        "path": "/blog/",
        "og_type": "website",
        "json_ld": False,
        "og_description": False,
    },
    {
        "id": "writeup-index",
        "template": "writeup_index.html",
        "context": {"title": "Writeup", "entries": []},
        "path": "/writeup/",
        "og_type": "website",
        "json_ld": False,
        "og_description": False,
    },
    {
        "id": "search",
        "template": "search.html",
        "context": {},
        "path": "/search/",
        "og_type": "website",
        "json_ld": False,
        "og_description": True,
    },
    {
        "id": "not-found",
        "template": "not_found.html",
        "context": {},
        "path": "/404.html",
        "og_type": "website",
        "json_ld": False,
        "og_description": False,
    },
]

PAGES = [pytest.param(case, id=case["id"]) for case in CASES]


@pytest.fixture(scope="module")
def environment():
    return make_environment()


def head_of(environment, case):
    return environment.get_template(case["template"]).render(**case["context"])


def meta_content(html, attribute, name):
    match = re.search(rf'{attribute}="{re.escape(name)}"\s+content="([^"]*)"', html)
    return match.group(1) if match else None


@pytest.mark.parametrize("case", PAGES)
def test_a_page_is_canonical_at_its_own_address(environment, case):
    html = head_of(environment, case)
    match = CANONICAL_PATTERN.search(html)
    assert match, f"{case['template']} declares no canonical address"
    assert match.group(1) == SITE + case["path"]


@pytest.mark.parametrize("case", PAGES)
def test_the_shared_link_points_where_the_canonical_does(environment, case):
    html = head_of(environment, case)
    assert meta_content(html, "property", "og:url") == SITE + case["path"]


@pytest.mark.parametrize("case", PAGES)
def test_an_article_says_so_and_a_listing_does_not(environment, case):
    html = head_of(environment, case)
    assert meta_content(html, "property", "og:type") == case["og_type"]


@pytest.mark.parametrize("case", PAGES)
def test_a_shared_link_carries_a_title_and_an_image(environment, case):
    html = head_of(environment, case)
    assert meta_content(html, "property", "og:title")
    assert meta_content(html, "property", "og:image") == f"{SITE}/static/og-image.png"
    assert (
        meta_content(html, "property", "og:site_name") == "Shinya Murakami (4n86rakam1)"
    )
    assert meta_content(html, "name", "twitter:card") == "summary_large_image"


@pytest.mark.parametrize("case", PAGES)
def test_a_card_describes_the_page_or_says_nothing(environment, case):
    """Repeating the site's description on every card tells a reader who was
    sent a link nothing, so a page that cannot describe itself sends none."""
    html = head_of(environment, case)
    description = meta_content(html, "property", "og:description")
    assert (description is not None) is case["og_description"]
    if description is not None:
        assert description == meta_content(html, "name", "description")


@pytest.mark.parametrize("case", PAGES)
def test_a_page_that_says_nothing_about_itself_still_has_a_search_result(
    environment, case
):
    html = head_of(environment, case)
    description = meta_content(html, "name", "description")
    assert description, "no description at all"
    if not case["og_description"]:
        assert description == "Security engineering notes and CTF writeups."


@pytest.mark.parametrize("case", PAGES)
def test_every_page_names_the_icon(environment, case):
    html = head_of(environment, case)
    match = ICON_PATTERN.search(html)
    assert match and match.group(1) == "/static/favicon.svg"


@pytest.mark.parametrize("case", PAGES)
def test_structured_data_is_there_for_a_page_and_absent_from_a_listing(
    environment, case
):
    html = head_of(environment, case)
    match = JSON_LD_PATTERN.search(html)
    assert bool(match) is case["json_ld"]
    if match:
        assert json.loads(match.group(1))["url"] == SITE + case["path"]


def test_the_structured_data_agrees_with_the_open_graph_type(environment):
    """Two places name what the page is; a page where they disagree is worse
    than one that claims nothing."""
    for case in CASES:
        if not case["json_ld"]:
            continue
        html = head_of(environment, case)
        schema_type = json.loads(JSON_LD_PATTERN.search(html).group(1))["@type"]
        # Both sides come from the rendered page; the table would only check itself.
        is_article = schema_type in {"BlogPosting", "TechArticle"}
        rendered_type = meta_content(html, "property", "og:type")
        assert is_article == (rendered_type == "article"), (
            f"{case['template']} calls itself {schema_type} and {rendered_type}"
        )


def case_named(name):
    return next(case for case in CASES if case["id"] == name)


def test_the_search_page_keeps_its_own_description(environment):
    html = head_of(environment, case_named("search"))
    assert "Search the writeups" in meta_content(html, "property", "og:description")


def test_no_page_declares_an_empty_meta_value(environment):
    for case in CASES:
        assert 'content=""' not in head_of(environment, case), (
            f"{case['template']} declares an empty value"
        )

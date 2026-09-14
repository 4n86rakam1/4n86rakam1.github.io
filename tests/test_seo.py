"""The metadata derived from a page, checked against literal expectations.

The URLs are spelled out rather than built from the configuration, because a
test that reads SITE_URL would pass whatever SITE_URL said.
"""

import datetime as dt
import json

from conftest import page

from ssg.seo import as_script_json, summarize

SITE = "https://4n86rakam1.github.io"


def test_the_first_paragraph_becomes_the_summary():
    assert summarize("# Title\n\nThe first line.\n\nThe second.\n") == "The first line."


def test_a_quoted_challenge_description_is_the_summary():
    # The writeups quote the challenge text, the only prose most of them have.
    body = "# Some Page\n\n## Description\n\n> Which country code is 'CA'?\n>\n> Search here!\n"
    assert summarize(body) == "Which country code is 'CA'?"


def test_code_is_not_prose():
    body = "# Title\n\n```console\n$ tree\nnot a summary\n```\n\nThe real one.\n"
    assert summarize(body) == "The real one."


def test_a_list_is_not_prose():
    assert summarize("# Title\n\n- source code: somewhere\n") == ""


def test_a_table_is_not_prose():
    assert summarize("# Title\n\n| a | b |\n| - | - |\n") == ""


def test_a_standalone_image_is_not_prose():
    assert (
        summarize("# Title\n\n![screenshot](shot.png)\n\nAfterwards.\n")
        == "Afterwards."
    )


def test_a_link_keeps_its_text_and_loses_its_target():
    assert summarize("Search country codes [here](http://example.com/)!") == (
        "Search country codes here!"
    )


def test_inline_code_markers_are_dropped_but_identifiers_survive():
    assert summarize("The `country_db` app is a Flask app.") == (
        "The country_db app is a Flask app."
    )


def test_a_flag_on_its_own_is_not_a_description():
    # As a preview line it says nothing, and it is the answer to the challenge.
    assert summarize("# Title\n\n## Flag\n\nsomectf{redacted____}\n") == ""


def test_a_sentence_that_mentions_the_flag_format_is_still_prose():
    body = "# Title\n\nThe flag is in the format TUCTF{...} and hides in the cookie.\n"
    assert summarize(body).startswith("The flag is in the format")


def test_a_body_with_nothing_to_say_summarises_to_nothing():
    assert summarize("# Title\n") == ""


def test_a_long_paragraph_is_cut_at_a_word():
    body = " ".join(["alpha"] * 60)
    summary = summarize(body)
    assert len(summary) <= 160
    assert summary.endswith("alpha…")


def test_a_short_paragraph_is_left_whole():
    assert summarize("Short enough.") == "Short enough."


def test_front_matter_wins_over_the_body():
    built = page("blog/post.md", body="Body lead.", description="From front matter")
    assert built.description == "From front matter"


def test_a_page_without_front_matter_describes_itself_from_its_body():
    built = page("writeup/X/y/index.md", body="# y\n\nBody lead.\n")
    assert built.description == "Body lead."


def test_the_front_page_is_a_website():
    built = page("index.md", body="Notes.", title="4n86rakam1")
    data = json.loads(built.json_ld)
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "WebSite"
    assert data["url"] == f"{SITE}/"
    assert data["author"] == {"@type": "Person", "name": "4n86rakam1"}


def test_a_post_is_a_blog_posting():
    built = page(
        "blog/hello-world.md",
        body="Body lead.",
        title="Hello world",
        date=dt.date(2026, 9, 13),
    )
    data = json.loads(built.json_ld)
    assert data["@type"] == "BlogPosting"
    assert data["headline"] == "Hello world"
    assert data["url"] == f"{SITE}/blog/hello-world/"
    assert data["datePublished"] == "2026-09-13"
    assert data["image"] == f"{SITE}/static/og-image.png"


def test_a_writeup_is_a_technical_article():
    built = page("writeup/SomeCTF_2023/web/Some_Page/index.md", body="# Some Page\n")
    data = json.loads(built.json_ld)
    assert data["@type"] == "TechArticle"
    assert data["url"] == f"{SITE}/writeup/SomeCTF_2023/web/Some_Page/"


def test_an_undated_article_claims_no_date():
    built = page("writeup/X/index.md", body="# X\n")
    assert "datePublished" not in json.loads(built.json_ld)


def test_a_description_it_could_not_derive_is_left_out():
    built = page("writeup/X/index.md", body="# X\n\n- only a list\n")
    assert "description" not in json.loads(built.json_ld)


def test_a_standalone_page_is_nothing_schema_org_names():
    assert page("about/index.md", body="About me.").json_ld == ""


def test_markup_in_a_description_cannot_end_the_script_element():
    escaped = as_script_json({"description": "</script><script>alert(1)</script>"})
    assert "</script>" not in escaped
    assert "<" not in escaped
    assert json.loads(escaped)["description"] == ("</script><script>alert(1)</script>")

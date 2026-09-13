import datetime as dt

from conftest import page

from ssg import content
from ssg.content import slugify_segment


def test_index_drops_out_of_the_url():
    assert page("about/index.md").url == "/about/"


def test_readme_is_an_index_too():
    assert page("writeup/SomeCTF_2023/README.md").url == "/writeup/SomeCTF_2023/"


def test_a_named_file_keeps_its_name_as_a_directory():
    assert page("blog/first-post.md").url == "/blog/first-post/"


def test_the_root_index_is_the_front_page():
    assert page("index.md").url == "/"


def test_output_path_is_always_an_index_file():
    assert (
        page("blog/first-post.md").output_path.as_posix()
        == "blog/first-post/index.html"
    )


def test_section_is_the_first_segment_of_a_nested_page():
    assert page("writeup/SomeCTF_2023/web/Some_Page/index.md").section == "writeup"


def test_a_top_level_page_has_no_section():
    assert page("about/index.md").section == ""


def test_title_prefers_front_matter():
    built = page("blog/post.md", body="# From the heading", title="From front matter")
    assert built.title == "From front matter"


def test_title_falls_back_to_the_first_heading():
    built = page("writeup/x/y/z/index.md", body="# Some Page\n\nBody text.")
    assert built.title == "Some Page"


def test_title_falls_back_to_the_file_name_last():
    assert page("blog/untitled.md").title == "untitled"


def test_a_heading_deeper_in_the_body_is_still_found():
    built = page("writeup/x/y/z/index.md", body="Intro.\n\n# Real Title\n")
    assert built.title == "Real Title"


def test_question_marks_are_dropped_from_segments():
    assert slugify_segment("Where's_it?") == "Wheres_it"


def test_spaces_fold_to_underscores():
    assert slugify_segment("Some Prices") == "Some_Prices"


def test_brackets_are_kept():
    assert slugify_segment("Over_the_Wire_(part_1)") == "Over_the_Wire_(part_1)"


def test_repeated_separators_collapse():
    assert slugify_segment("Who?_What's_that?") == "Who_Whats_that"


def test_a_segment_of_only_unsafe_characters_is_left_alone():
    # Returning an empty segment would silently merge two directories.
    assert slugify_segment("???") == "???"


def test_slugified_segments_reach_the_url():
    built = page("writeup/OtherCTF_2024/Networks/Where's_it?/index.md")
    assert built.url == "/writeup/OtherCTF_2024/Networks/Wheres_it/"


def test_a_datetime_in_front_matter_becomes_a_date():
    built = page("blog/post.md", date=dt.datetime(2026, 5, 1, 12, 30))
    assert built.date == dt.date(2026, 5, 1)


def test_a_page_without_a_date_has_none():
    assert page("blog/post.md").date is None


def test_discovery_finds_every_markdown_file(tmp_path, monkeypatch):
    monkeypatch.setattr(content, "CONTENT_DIR", tmp_path)
    (tmp_path / "one.md").write_text("---\ntitle: One\n---\n")
    (tmp_path / "two.md").write_text("---\ntitle: Two\n---\n")
    assert [p.title for p in content.discover(tmp_path)] == ["One", "Two"]

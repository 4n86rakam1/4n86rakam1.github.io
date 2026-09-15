import re

import pytest
from conftest import CODE_BACKGROUND, MINIMUM_CONTRAST, contrast_ratio

from ssg.render import (
    add_loading_hints,
    label_permalinks,
    make_renderer,
    mark_details_contents_as_markdown,
    open_external_links_in_a_new_tab,
    point_images_at_published_files,
    raise_highlight_contrast,
    render,
    rewrite_source_links,
)

COLOUR_PATTERN = re.compile(r"(?<![-\w])color:\s*(#[0-9A-Fa-f]{3,6})")


def test_a_sibling_index_becomes_its_directory():
    assert (
        rewrite_source_links('<a href="web/Some_Page/index.md">x</a>')
        == '<a href="web/Some_Page/">x</a>'
    )


def test_a_readme_is_an_index_too():
    assert (
        rewrite_source_links('<a href="../SomeCTF_2023/README.md">x</a>')
        == '<a href="../SomeCTF_2023/">x</a>'
    )


def test_a_named_file_becomes_a_directory():
    assert rewrite_source_links('<a href="notes.md">x</a>') == '<a href="notes/">x</a>'


def test_a_bare_index_points_at_the_current_directory():
    assert rewrite_source_links('<a href="index.md">x</a>') == '<a href="./">x</a>'


def test_a_fragment_survives():
    assert (
        rewrite_source_links('<a href="web/x/index.md#flag">x</a>')
        == '<a href="web/x/#flag">x</a>'
    )


def test_external_links_are_left_alone():
    link = '<a href="https://example.com/notes.md">x</a>'
    assert rewrite_source_links(link) == link


def test_links_without_a_markdown_suffix_are_left_alone():
    link = '<a href="https://example.com/">x</a>'
    assert rewrite_source_links(link) == link


def test_percent_encoded_segments_are_slugified():
    assert (
        rewrite_source_links('<a href="Networks/Where%27s_it%3F/index.md">x</a>')
        == '<a href="Networks/Wheres_it/">x</a>'
    )


def test_spaces_in_a_target_fold_like_the_directories_they_name():
    assert (
        rewrite_source_links('<a href="rev/thing 1/index.md">x</a>')
        == '<a href="rev/thing_1/">x</a>'
    )


def test_a_fence_inside_a_list_item_stays_code():
    # Plain fenced_code drops these; superfences is what keeps them.
    html = render(make_renderer(), "- item\n\n  ```python\n  x = 1\n  ```\n")
    assert "<pre" in html


def test_the_renderer_does_not_leak_state_between_documents():
    # toc suffixes a repeated heading's id, which is what a stateful renderer does.
    renderer = make_renderer()
    render(renderer, "# Title\n")
    html = render(renderer, "# Title\n")
    assert 'id="title"' in html


def test_a_site_absolute_target_keeps_its_leading_slash():
    assert (
        rewrite_source_links('<a href="/writeup/X/index.md">x</a>')
        == '<a href="/writeup/X/">x</a>'
    )


def test_a_protocol_relative_link_is_left_alone():
    link = '<a href="//example.com/notes.md">x</a>'
    assert rewrite_source_links(link) == link


def test_an_image_is_deferred_and_decoded_off_the_main_thread():
    assert (
        add_loading_hints('<img alt="a" src="shot.png" />')
        == '<img loading="lazy" decoding="async" alt="a" src="shot.png" />'
    )


def test_an_image_that_already_defers_is_left_alone():
    tag = '<img loading="eager" decoding="async" src="shot.png">'
    assert add_loading_hints(tag) == tag


def test_a_tag_is_read_to_its_end_even_with_an_angle_bracket_in_a_value():
    # Cut short at the bracket, the author's loading goes unseen and is doubled.
    tag = '<img alt="a > b" loading="eager" src="x.png">'
    assert (
        add_loading_hints(tag)
        == '<img decoding="async" alt="a > b" loading="eager" src="x.png">'
    )


def test_a_query_string_is_not_an_attribute():
    html = add_loading_hints('<img src="shot.png?loading=1">')
    assert html == '<img loading="lazy" decoding="async" src="shot.png?loading=1">'


def test_only_the_missing_hint_is_added():
    assert (
        add_loading_hints('<img decoding="sync" src="shot.png">')
        == '<img loading="lazy" decoding="sync" src="shot.png">'
    )


def test_every_image_in_a_document_is_deferred():
    html = add_loading_hints('<p><img src="a.png"><img src="b.png"></p>')
    assert html.count('loading="lazy"') == 2


def test_nothing_but_an_image_is_touched():
    html = '<p>text</p><a href="x"><img src="a.png"></a>'
    assert add_loading_hints(html).count('loading="lazy"') == 1


def test_a_rendered_image_carries_the_hints():
    html = render(make_renderer(), "![a screenshot](shot.png)\n")
    assert 'loading="lazy"' in html
    assert 'decoding="async"' in html


def test_a_details_block_is_asked_to_parse_what_is_inside_it():
    assert (
        mark_details_contents_as_markdown("<details><summary>s</summary>\n")
        == '<details markdown="1"><summary>s</summary>\n'
    )


def test_a_details_block_indented_into_a_list_item_is_left_alone():
    # md_in_html cannot lift one out of a list item; the attribute would leak.
    source = "1. step\n\n   <details><summary>s</summary>\n"
    assert mark_details_contents_as_markdown(source) == source


def test_a_details_block_that_already_asks_is_left_alone():
    source = '<details markdown="block"><summary>s</summary>\n'
    assert mark_details_contents_as_markdown(source) == source


def test_a_details_tag_shown_inside_a_fence_is_left_alone():
    source = "```html\n<details><summary>s</summary>\n```\n"
    assert mark_details_contents_as_markdown(source) == source


def test_an_image_inside_a_details_block_reaches_the_page_as_an_image():
    html = render(
        make_renderer(),
        "<details><summary>s</summary>\n\n![w1.png](img/w1.png)\n\n</details>\n",
    )
    # The alt text is the author's words and stays as written; only the address
    # follows the file the build published.
    assert (
        '<img loading="lazy" decoding="async" alt="w1.png" src="img/w1.webp" />' in html
    )
    assert "![w1.png]" not in html


def test_a_link_inside_a_details_block_reaches_the_page_as_a_link():
    html = render(
        make_renderer(),
        "<details><summary>s</summary>\n\n[text](https://example.com/)\n\n</details>\n",
    )
    assert (
        '<a href="https://example.com/" target="_blank" rel="noopener">text</a>' in html
    )


def test_code_inside_a_details_block_is_still_code():
    # 60 of the writeups' blocks hold nothing but a fence, which must not change.
    html = render(
        make_renderer(),
        "<details><summary>s</summary>\n\n```console\n$ ls\n```\n\n</details>\n",
    )
    assert "<pre" in html
    assert "```" not in html


def test_an_image_points_at_the_file_the_build_published():
    assert (
        point_images_at_published_files('<img alt="a" src="img/shot.png">')
        == '<img alt="a" src="img/shot.webp">'
    )


def test_the_suffix_is_matched_however_it_is_spelled():
    assert 'src="a.webp"' in point_images_at_published_files('<img src="a.PNG">')
    assert 'src="b.webp"' in point_images_at_published_files('<img src="b.JPEG">')


def test_a_query_or_fragment_survives_the_rewrite():
    # The suffix ends the path, not the address: `shot.png?v=2` is still a PNG.
    assert (
        point_images_at_published_files('<img src="shot.png?v=2">')
        == '<img src="shot.webp?v=2">'
    )


def test_an_image_on_another_host_is_left_alone():
    # Nothing here converted it, so nothing here may rename it.
    tag = '<img src="https://example.com/a.png">'
    assert point_images_at_published_files(tag) == tag


def test_a_file_that_only_looks_like_an_image_is_left_alone():
    tag = '<img src="notes.png.txt">'
    assert point_images_at_published_files(tag) == tag


def test_a_format_that_is_published_as_it_stands_is_left_alone():
    for tag in ('<img src="a.gif">', '<img src="a.svg">', '<img src="a.webp">'):
        assert point_images_at_published_files(tag) == tag


def test_an_alt_text_naming_a_png_is_not_an_address():
    html = point_images_at_published_files('<img alt="w1.png" src="img/w1.png">')
    assert 'alt="w1.png"' in html
    assert 'src="img/w1.webp"' in html


def test_the_highlight_colours_short_of_the_minimum_are_lifted():
    css = ".c { color: #3D7B7B } .nd { color: #A2F } .nl { color: #767600 }"
    for colour in COLOUR_PATTERN.findall(raise_highlight_contrast(css)):
        ratio = contrast_ratio(colour, CODE_BACKGROUND)
        assert ratio >= MINIMUM_CONTRAST, f"{colour} is {ratio:.2f}:1"


def test_the_whitespace_marker_is_left_where_it_is():
    """Text.Whitespace draws the whitespace characters themselves. Lifting it to
    the minimum would run visible grey marks through every code block."""
    css = ".w { color: #BBB }"
    assert raise_highlight_contrast(css) == css


def test_a_background_colour_is_not_mistaken_for_a_foreground_one():
    # `background-color` ends in the same eight characters as `color`.
    css = ".hll { background-color: #3D7B7B }"
    assert raise_highlight_contrast(css) == css


@pytest.mark.parametrize(
    "tag,expected",
    [
        ("<img src='a.png'>", "<img src='a.webp'>"),
        ('<img src = "a.png">', '<img src = "a.webp">'),
        ('<img SRC="a.png">', '<img SRC="a.webp">'),
    ],
)
def test_an_attribute_is_matched_however_it_is_written(tag, expected):
    """The loading hints already accept every one of these spellings. A tag this
    missed would be deferred and then point at a file the build renamed."""
    assert point_images_at_published_files(tag) == expected


def test_a_site_absolute_address_is_left_alone():
    """The writeups name their images by relative path. `/static/` is the build's
    own directory, copied verbatim, and og-image.png there is what the share
    card points at."""
    tag = '<img src="/static/og-image.png">'
    assert point_images_at_published_files(tag) == tag


def test_an_attribute_that_only_ends_in_src_is_left_alone():
    # Nothing converts what `data-src` names, so renaming it moves the breakage.
    tag = '<img data-src="a.png">'
    assert point_images_at_published_files(tag) == tag


def test_the_closing_quote_has_to_match_the_opening_one():
    tag = "<img src=\"a.png'>"
    assert point_images_at_published_files(tag) == tag


def test_a_link_to_another_host_opens_in_its_own_tab():
    assert (
        open_external_links_in_a_new_tab('<a href="https://example.com/x">x</a>')
        == '<a href="https://example.com/x" target="_blank" rel="noopener">x</a>'
    )


def test_a_protocol_relative_link_leaves_the_site_as_well():
    assert (
        open_external_links_in_a_new_tab('<a href="//example.com/x">x</a>')
        == '<a href="//example.com/x" target="_blank" rel="noopener">x</a>'
    )


@pytest.mark.parametrize(
    "tag",
    [
        '<a href="../writeup/">x</a>',
        '<a href="/search/">x</a>',
        '<a href="#flag">x</a>',
        # No `//`, so it never leaves for a tab of its own.
        '<a href="mailto:nobody@example.com">x</a>',
    ],
)
def test_a_link_that_stays_on_the_site_keeps_the_tab_it_is_in(tag):
    assert open_external_links_in_a_new_tab(tag) == tag


def test_a_link_that_already_names_a_target_is_left_alone():
    tag = '<a href="https://example.com" target="_self">x</a>'
    assert open_external_links_in_a_new_tab(tag) == tag


def test_an_anchor_is_read_to_its_end_even_with_an_angle_bracket_in_a_value():
    assert (
        open_external_links_in_a_new_tab('<a href="https://example.com" title="a > b">')
        == '<a href="https://example.com" title="a > b" target="_blank"'
        ' rel="noopener">'
    )


def test_an_attribute_that_only_ends_in_href_is_not_the_address():
    tag = '<a data-href="https://example.com" href="/search/">x</a>'
    assert open_external_links_in_a_new_tab(tag) == tag


def test_a_rendered_link_to_another_host_carries_the_attributes():
    assert (
        '<a href="https://example.com" target="_blank" rel="noopener">x</a>'
        in render(make_renderer(), "[x](https://example.com)")
    )


def test_a_heading_anchor_is_named_for_a_reader_who_hears_it():
    assert (
        label_permalinks('<a class="headerlink" href="#x">#</a>')
        == '<a data-pagefind-ignore aria-label="Permanent link to this heading"'
        ' class="headerlink" href="#x">#</a>'
    )


def test_a_heading_carries_an_anchor_pointing_at_itself():
    html = render(make_renderer(), "## The flag")
    assert 'id="the-flag"' in html
    assert 'class="headerlink" href="#the-flag"' in html


def test_a_heading_is_named_by_its_own_text_rather_than_its_anchor():
    """The anchor is a child, so its name would otherwise be read as part of the
    heading's: "The flagPermanent link to this heading"."""
    assert '<h2 id="the-flag" aria-label="The flag">' in render(
        make_renderer(), "## The flag"
    )


def test_a_heading_name_keeps_the_words_and_drops_the_markup():
    assert 'aria-label="ls in a heading"' in render(
        make_renderer(), "## `ls` in a heading"
    )


def test_a_quote_in_a_heading_does_not_end_the_name():
    """Markdown escapes `<`, `>` and `&` in text and leaves `"` alone, and the
    name goes into a double-quoted attribute."""
    assert 'aria-label="He said &quot;hi&quot;"' in render(
        make_renderer(), '## He said "hi"'
    )


def test_a_heading_with_no_permalink_is_left_as_it_is():
    assert "aria-label" not in label_permalinks("<h2>Plain</h2>")


def test_the_heading_id_is_the_one_the_writeups_already_link_to():
    """The anchor is new; the slug it points at is what ~350 in-page links in
    the writeups were written against, so it has to be the same slug."""
    html = render(make_renderer(), "## Step 1: Find the Bug")
    assert 'id="step-1-find-the-bug"' in html


def test_a_heading_anchor_is_kept_out_of_the_search_index():
    assert "data-pagefind-ignore" in render(make_renderer(), "## The flag")

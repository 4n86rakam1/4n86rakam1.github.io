from ssg.render import (
    add_loading_hints,
    make_renderer,
    mark_details_contents_as_markdown,
    render,
    rewrite_source_links,
)


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
    assert (
        '<img loading="lazy" decoding="async" alt="w1.png" src="img/w1.png" />' in html
    )
    assert "![w1.png]" not in html


def test_a_link_inside_a_details_block_reaches_the_page_as_a_link():
    html = render(
        make_renderer(),
        "<details><summary>s</summary>\n\n[text](https://example.com/)\n\n</details>\n",
    )
    assert '<a href="https://example.com/">text</a>' in html


def test_code_inside_a_details_block_is_still_code():
    # 60 of the writeups' blocks hold nothing but a fence, which must not change.
    html = render(
        make_renderer(),
        "<details><summary>s</summary>\n\n```console\n$ ls\n```\n\n</details>\n",
    )
    assert "<pre" in html
    assert "```" not in html

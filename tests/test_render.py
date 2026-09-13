from ssg.render import make_renderer, render, rewrite_source_links


def test_a_sibling_index_becomes_its_directory():
    assert (
        rewrite_source_links('<a href="web/Country_DB/index.md">x</a>')
        == '<a href="web/Country_DB/">x</a>'
    )


def test_a_readme_is_an_index_too():
    assert (
        rewrite_source_links('<a href="../CakeCTF_2023/README.md">x</a>')
        == '<a href="../CakeCTF_2023/">x</a>'
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
        rewrite_source_links('<a href="Networks/Where%27s_skat%3F/index.md">x</a>')
        == '<a href="Networks/Wheres_skat/">x</a>'
    )


def test_spaces_in_a_target_fold_like_the_directories_they_name():
    assert (
        rewrite_source_links('<a href="rev/rebug 1/index.md">x</a>')
        == '<a href="rev/rebug_1/">x</a>'
    )


def test_a_fence_inside_a_list_item_stays_code():
    # Plain fenced_code drops these; superfences is what keeps them.
    html = render(make_renderer(), "- item\n\n  ```python\n  x = 1\n  ```\n")
    assert "<pre" in html


def test_the_renderer_does_not_leak_state_between_documents():
    # The toc extension disambiguates a repeated heading by suffixing its id,
    # which is what a renderer carrying state from the previous document does.
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

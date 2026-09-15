import re
from urllib.parse import unquote

import pytest
from conftest import CODE_BACKGROUND, MINIMUM_CONTRAST, contrast_ratio, page
from PIL import Image

from ssg import build as build_module
from ssg import content as content_module
from ssg.build import DuplicateOutputError, MissingFrontPageError, breadcrumbs_for
from ssg.config import INDEX_FILENAME, OUTPUT_DIR

HIGHLIGHT_COLOUR_PATTERN = re.compile(r"(?<![-\w])color:\s*(#[0-9A-Fa-f]{3,6})")
# Text.Whitespace colours the whitespace characters themselves rather than
# anything a reader has to make out, and lifting it to the minimum would run
# visible grey marks through every code block.
UNLIFTED_HIGHLIGHT_COLOURS = {"#BBB"}


def test_the_front_page_has_no_trail():
    assert breadcrumbs_for(page("index.md"), {}) == []


def test_a_top_level_page_names_only_home_before_itself():
    assert breadcrumbs_for(page("about/index.md", title="About"), {}) == [
        ("Home", "/"),
        ("About", "/about/"),
    ]


def test_a_section_takes_its_label_from_the_nav():
    trail = breadcrumbs_for(page("blog/a-post.md", title="A post"), {})
    assert trail == [("Home", "/"), ("Blog", "/blog/"), ("A post", "/blog/a-post/")]


def test_a_section_outside_the_nav_falls_back_to_its_own_name():
    trail = breadcrumbs_for(page("notes/one/index.md", title="One"), {})
    assert trail[1] == ("Notes", "/notes/")


def an_image_at(path):
    """A real image: the build decodes what it republishes, so a placeholder
    byte string is no longer a stand-in for one."""
    Image.new("RGB", (64, 48), "#ffffff").save(path)
    return path


@pytest.fixture
def isolated_site(tmp_path, monkeypatch):
    """Point the build at an empty content tree and a throwaway output."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    output_dir = tmp_path / "dist"
    monkeypatch.setattr(build_module, "CONTENT_DIR", content_dir)
    monkeypatch.setattr(build_module, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(content_module, "CONTENT_DIR", content_dir)
    return content_dir, output_dir


def test_a_build_with_no_front_page_is_an_error(isolated_site):
    # Without the check, this build exits zero and publishes no way in.
    with pytest.raises(MissingFrontPageError):
        build_module.build()


def test_a_build_with_a_front_page_succeeds(isolated_site):
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n\nBody.\n")
    build_module.build()
    assert (output_dir / "index.html").is_file()
    assert (output_dir / "sitemap.xml").is_file()
    assert (output_dir / "404.html").is_file()


def test_the_sitemap_lists_the_front_page_as_the_root(isolated_site):
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n\nBody.\n")
    build_module.build()
    sitemap = (output_dir / "sitemap.xml").read_text()
    assert "<loc>https://4n86rakam1.com/</loc>" in sitemap
    # 404.html is not an index.html, so it never reaches the sitemap.
    assert "404" not in sitemap


def with_a_moved_page(content_dir):
    """A source directory the slug rules rewrite, so the build has an old URL
    to leave a receiver at."""
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    moved = content_dir / "writeup" / "X" / "thing 1"
    moved.mkdir(parents=True)
    (moved / "index.md").write_text("# Thing 1\n")
    return "writeup/X/thing 1", "/writeup/X/thing_1/"


def test_an_old_url_is_served_a_page_that_points_at_the_new_one(isolated_site):
    content_dir, output_dir = isolated_site
    old, new = with_a_moved_page(content_dir)
    build_module.build()
    written = (output_dir / old / "index.html").read_text()
    assert f'content="0; url={new}"' in written
    assert f'rel="canonical" href="https://4n86rakam1.com{new}"' in written
    assert f'location.replace("{new}")' in written
    # The reader with no JavaScript and a browser ignoring meta refresh still
    # needs something to click.
    assert f'href="{new}"' in written


def test_an_old_url_stays_out_of_the_sitemap(isolated_site):
    # Every receiver names another page as its canonical, so listing one asks
    # a crawler to index a page that disclaims itself.
    content_dir, output_dir = isolated_site
    _, new = with_a_moved_page(content_dir)
    build_module.build()
    sitemap = (output_dir / "sitemap.xml").read_text()
    assert f"<loc>https://4n86rakam1.com{new}</loc>" in sitemap
    assert "thing 1" not in sitemap and "thing%201" not in sitemap


def test_an_old_url_stays_out_of_the_search_index(isolated_site):
    """Pagefind indexes only what carries data-pagefind-body once any page
    does, and a receiver is the one page that carries none."""
    content_dir, output_dir = isolated_site
    old, _ = with_a_moved_page(content_dir)
    build_module.build()
    assert "data-pagefind-body" not in (output_dir / old / "index.html").read_text()


def test_an_unrequestable_old_url_gets_no_receiver(isolated_site):
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    moved = content_dir / "writeup" / "X" / "Where's it?"
    moved.mkdir(parents=True)
    (moved / "index.md").write_text("# One\n")
    build_module.build()
    assert not (output_dir / "writeup" / "X" / "Where's it?").exists()


def test_the_root_files_are_written(isolated_site):
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    build_module.build()
    assert (output_dir / "robots.txt").is_file()
    assert (output_dir / "llms.txt").is_file()
    assert (output_dir / ".well-known" / "security.txt").is_file()


def test_the_root_files_stay_out_of_the_sitemap(isolated_site):
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    build_module.build()
    sitemap = (output_dir / "sitemap.xml").read_text()
    assert "robots" not in sitemap and "well-known" not in sitemap


def test_images_keep_their_names_while_their_directories_are_slugified(isolated_site):
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n\nBody.\n")
    nested = content_dir / "writeup" / "X" / "Where's it?"
    nested.mkdir(parents=True)
    (nested / "index.md").write_text("# One\n")
    an_image_at(nested / "chal.png")
    build_module.build()
    # The suffix follows the re-encoding; the stem is the author's name for it.
    assert (output_dir / "writeup" / "X" / "Wheres_it" / "chal.webp").is_file()


def test_a_checkout_left_in_the_content_tree_is_not_published(isolated_site):
    # The writeups arrive as a checkout whose .git holds the token that made it.
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    git_dir = content_dir / "writeup" / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "config").write_text("[http]\n  extraheader = AUTHORIZATION: basic x\n")
    build_module.build()
    assert not (output_dir / "writeup" / ".git").exists()


def test_two_sources_that_slugify_alike_are_an_error(isolated_site):
    content_dir, _ = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    for name in ("Where's it?", "Wheres it"):
        page_dir = content_dir / "writeup" / "X" / name
        page_dir.mkdir(parents=True)
        (page_dir / "index.md").write_text(f"# {name}\n")
    with pytest.raises(DuplicateOutputError):
        build_module.build()


def test_the_generated_writeup_index_replaces_the_imported_readme(isolated_site):
    # emit_pages writes /writeup/ from the imported README; emit_writeup_index
    # overwrites it. Reversing those two calls would restore the README.
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    writeup_dir = content_dir / "writeup"
    writeup_dir.mkdir()
    (writeup_dir / "README.md").write_text("# writeup\n\nImported text.\n")
    ctf = writeup_dir / "SomeCTF"
    ctf.mkdir()
    (ctf / "README.md").write_text("---\nstart_at: 2026-01-01\n---\n\n# Some CTF\n")
    build_module.build()
    index = (output_dir / "writeup" / "index.html").read_text()
    assert "Some CTF" in index
    assert "Imported text" not in index


def test_only_publishable_asset_types_are_copied(isolated_site):
    # The writeups carry editor backups, scratch notes with flags, and caches.
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    source = content_dir / "writeup" / "X"
    source.mkdir(parents=True)
    (source / "index.md").write_text("# X\n")
    an_image_at(source / "shot.png")
    (source / "notes.md~").write_text("editor backup")
    (source / "cache.sqlite").write_bytes(b"sqlite")
    (source / "scratch.md.tmp").write_text("a flag someone left lying around")

    build_module.build()

    published = output_dir / "writeup" / "X"
    assert (published / "shot.webp").is_file()
    for withheld in ("notes.md~", "cache.sqlite", "scratch.md.tmp"):
        assert not (published / withheld).exists()


def published_pages():
    """Built pages with code blocks removed: a fence showing Markdown is
    showing it on purpose."""
    for path in sorted(OUTPUT_DIR.rglob("*.html")):
        yield (
            path,
            re.sub(
                r"<pre.*?</pre>", "", path.read_text(encoding="utf-8"), flags=re.DOTALL
            ),
        )


def test_the_real_output_shows_no_markdown_that_was_meant_to_be_rendered():
    """The writeups wrap screenshots in <details>, and a block the parser is
    not asked to read reaches the reader as the text that was typed."""
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        pytest.skip("no built site; run `uv run python -m ssg` first")
    unrendered = [
        str(path.relative_to(OUTPUT_DIR))
        for path, page in published_pages()
        if re.search(r"!\[[^\]]*\]\([^)]*\)", page)
    ]
    assert not unrendered, f"image syntax reached the page: {unrendered[:5]}"


def test_the_real_output_carries_no_parser_instructions():
    """The attribute the generator adds to a <details> tag is for the parser;
    a page that still shows it is one the parser did not read."""
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        pytest.skip("no built site; run `uv run python -m ssg` first")
    leaked = [
        str(path.relative_to(OUTPUT_DIR))
        for path, page in published_pages()
        if "markdown=" in page
    ]
    assert not leaked, f"pages carrying the attribute into the output: {leaked[:5]}"


# Spelled out rather than imported: a test reading the same allowlist the build
# reads would pass whatever it said.
EXPECTED_OUTPUT_SUFFIXES = {
    ".html",
    ".css",
    ".xml",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".py",
    ".ipynb",
    ".txt",
}


def test_the_real_output_carries_no_unexpected_file_types():
    """The real build, not a fixture: another repository decides what lands in
    the content tree."""
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        pytest.skip("no built site; run `uv run python -m ssg` first")
    unexpected = sorted(
        {
            path.suffix.lower()
            for path in OUTPUT_DIR.rglob("*")
            # Pagefind writes its own index formats under one directory.
            if path.is_file()
            and "pagefind" not in path.parts
            and path.name != ".nojekyll"
        }
        - EXPECTED_OUTPUT_SUFFIXES
    )
    assert not unexpected, f"unexpected file types in the output: {unexpected}"


# Written out for the same reason as the suffixes above. A dot entry is one of
# these two or an accident: `.git` arrived that way once.
EXPECTED_DOT_ENTRIES = {".nojekyll", ".well-known"}


def test_the_real_output_holds_no_unexpected_dot_files():
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        pytest.skip("no built site; run `uv run python -m ssg` first")
    hidden = sorted(
        {path.relative_to(OUTPUT_DIR).as_posix() for path in OUTPUT_DIR.rglob(".*")}
        - EXPECTED_DOT_ENTRIES
    )
    assert not hidden, f"dot files reached the output: {hidden[:5]}"


def test_the_real_output_puts_nothing_but_security_txt_under_well_known():
    """`.well-known` is exempt from the check above, so it needs its own."""
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        pytest.skip("no built site; run `uv run python -m ssg` first")
    well_known = OUTPUT_DIR / ".well-known"
    assert sorted(path.name for path in well_known.rglob("*")) == ["security.txt"]


def with_an_image(content_dir, name="shot.png"):
    """A front page holding one image, which the build has to republish."""
    (content_dir / "index.md").write_text(
        f"---\ntitle: Home\n---\n\n![a screenshot](img/{name})\n"
    )
    directory = content_dir / "img"
    directory.mkdir(exist_ok=True)
    return an_image_at(directory / name)


def test_an_image_is_republished_as_a_webp(isolated_site):
    content_dir, output_dir = isolated_site
    with_an_image(content_dir)
    build_module.build()
    assert (output_dir / "img" / "shot.webp").is_file()
    # Publishing both would undo what the conversion was for.
    assert not (output_dir / "img" / "shot.png").exists()


def test_the_page_points_at_the_image_that_was_published(isolated_site):
    content_dir, output_dir = isolated_site
    with_an_image(content_dir)
    build_module.build()
    html = (output_dir / INDEX_FILENAME).read_text()
    assert 'src="img/shot.webp"' in html
    # The head's own share image is a static file the build does not convert,
    # so the name of the converted one is what has to be gone.
    assert "shot.png" not in html


def test_a_file_that_is_not_an_image_is_copied_as_it_stands(isolated_site):
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    (content_dir / "notes.txt").write_text("kept\n")
    build_module.build()
    assert (output_dir / "notes.txt").read_text() == "kept\n"


def test_two_images_converging_on_one_name_are_an_error(isolated_site):
    """`a.png` and `a.jpg` both publish as `a.webp`. The writeups come from a
    repository this one does not control, so the second would replace the first
    without a word."""
    content_dir, _ = isolated_site
    with_an_image(content_dir, "a.png")
    with_an_image(content_dir, "a.jpg")
    with pytest.raises(DuplicateOutputError):
        build_module.build()


def test_the_published_highlighting_clears_the_contrast_minimum(isolated_site):
    """Read off the sheet the build wrote, not off the function that fixes it:
    this is the check that fails if the build stops calling it."""
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    build_module.build()
    css = (output_dir / "static" / "pygments.css").read_text()
    lifted = [
        colour
        for colour in HIGHLIGHT_COLOUR_PATTERN.findall(css)
        if colour not in UNLIFTED_HIGHLIGHT_COLOURS
    ]
    assert lifted, "no colours found; the sheet is not what this reads"
    for colour in lifted:
        ratio = contrast_ratio(colour, CODE_BACKGROUND)
        assert ratio >= MINIMUM_CONTRAST, f"{colour} is {ratio:.2f}:1"


# Written out rather than imported from the renderer: an expectation taken from
# the code it judges agrees with whatever that code does.
ANOTHER_HOST = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//", re.IGNORECASE)
# The tag first, then its attributes: one pass over the whole page finds only
# the first address in each tag, so a `src` sitting after a `srcset` goes
# unswept. The tag ends at the first `>` outside a quoted value.
IMAGE_TAG = re.compile(r"""<img\b((?:[^>"']|"[^"]*"|'[^']*')*)>""", re.IGNORECASE)
IMAGE_ATTRIBUTE = re.compile(
    r"(?<![-\w])(src|srcset)\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE
)


def image_addresses(html):
    """Every address an <img> on the page would fetch, srcset candidates and
    all: a candidate is an address followed by an optional descriptor."""
    for attributes in IMAGE_TAG.findall(html):
        for attribute, value in IMAGE_ATTRIBUTE.findall(attributes):
            if attribute.lower() != "srcset":
                yield value
                continue
            for candidate in value.split(","):
                if candidate.split():
                    yield candidate.split()[0]


@pytest.mark.parametrize(
    "tag,addresses",
    [
        ('<img src="a.webp">', ["a.webp"]),
        ("<img srcset='a.webp' src='b.webp'>", ["a.webp", "b.webp"]),
        (
            '<img srcset=" c.webp 480w , d.webp 800w " src="c.webp">',
            ["c.webp", "d.webp", "c.webp"],
        ),
        ('<img data-src="skipped.webp" src="e.webp">', ["e.webp"]),
        ("<p>no image here</p>", []),
    ],
)
def test_the_sweep_sees_every_address_in_a_tag(tag, addresses):
    """The sweep below is only as good as this: an address it does not collect
    is an address nothing checks. None of these spellings appear in the writeups
    today, which is exactly why the reading of them is pinned here."""
    assert list(image_addresses(tag)) == addresses


def test_every_image_a_page_names_is_a_file_that_was_written():
    """The address in the tag and the name of the file are decided in two
    different places — the renderer rewrites one, the asset pass writes the
    other — and a disagreement is a broken image that every check reading only
    the markup reports as fine. Swept across the whole output rather than a
    sampled page, because which page a sample lands on is decided by the
    writeup repository's sort order."""
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        pytest.skip("no built site; run `uv run python -m ssg` first")
    checked = 0
    missing = []
    for page in OUTPUT_DIR.rglob("*.html"):
        for address in image_addresses(page.read_text(encoding="utf-8")):
            if ANOTHER_HOST.match(address) or address.startswith("data:"):
                continue
            named = unquote(address.split("?")[0].split("#")[0])
            target = (
                OUTPUT_DIR / named.lstrip("/")
                if named.startswith("/")
                else page.parent / named
            )
            checked += 1
            if not target.is_file():
                missing.append(f"{page.relative_to(OUTPUT_DIR)} -> {address}")
    # Without this the sweep passes by finding nothing to sweep.
    assert checked, "no local images in the output; this read the wrong thing"
    assert not missing, f"images pointing at nothing: {missing[:5]}"

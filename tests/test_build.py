import pytest
from conftest import page

from ssg import build as build_module
from ssg import content as content_module
from ssg.build import DuplicateOutputError, MissingFrontPageError, breadcrumbs_for
from ssg.config import INDEX_FILENAME, OUTPUT_DIR


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
    # The whole point of the check: without it this build exits zero and
    # publishes a site with no way in.
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
    assert "<loc>https://4n86rakam1.github.io/</loc>" in sitemap
    # 404.html is not an index.html, so it never reaches the sitemap.
    assert "404" not in sitemap


def test_images_keep_their_names_while_their_directories_are_slugified(isolated_site):
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n\nBody.\n")
    nested = content_dir / "writeup" / "X" / "Where's it?"
    nested.mkdir(parents=True)
    (nested / "index.md").write_text("# One\n")
    (nested / "chal.png").write_bytes(b"png")
    build_module.build()
    assert (output_dir / "writeup" / "X" / "Wheres_it" / "chal.png").is_file()


def test_a_checkout_left_in_the_content_tree_is_not_published(isolated_site):
    # The writeups arrive as a checkout whose .git holds the token that made
    # it; copying that into the output would publish it.
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
    # The writeups come from a repository this one does not control, and carry
    # editor backups, scratch notes with flags in them, and caches.
    content_dir, output_dir = isolated_site
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n")
    source = content_dir / "writeup" / "X"
    source.mkdir(parents=True)
    (source / "index.md").write_text("# X\n")
    (source / "shot.png").write_bytes(b"png")
    (source / "notes.md~").write_text("editor backup")
    (source / "cache.sqlite").write_bytes(b"sqlite")
    (source / "scratch.md.tmp").write_text("a flag someone left lying around")

    build_module.build()

    published = output_dir / "writeup" / "X"
    assert (published / "shot.png").is_file()
    for withheld in ("notes.md~", "cache.sqlite", "scratch.md.tmp"):
        assert not (published / withheld).exists()


# Spelled out here rather than imported from the generator: a test that reads
# the same allowlist the build reads would pass no matter what the allowlist
# said.
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
    """Checks the actual build rather than a fixture, because what lands in
    the content tree is decided by another repository."""
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


def test_the_real_output_holds_no_dot_files():
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        pytest.skip("no built site; run `uv run python -m ssg` first")
    hidden = [
        str(path.relative_to(OUTPUT_DIR))
        for path in OUTPUT_DIR.rglob(".*")
        if path.name != ".nojekyll"
    ]
    assert not hidden, f"dot files reached the output: {hidden[:5]}"

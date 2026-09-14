"""Build orchestration: render the content tree and emit the derived views."""

import datetime as dt
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pygments.formatters import HtmlFormatter

from . import blog, content, redirects, render, rootfiles, sitemap, writeup
from .config import (
    BLOG_SEGMENT,
    CONTENT_DIR,
    FOOTER_LINKS,
    INDEX_FILENAME,
    NAV,
    NOT_FOUND_FILENAME,
    OUTPUT_DIR,
    PUBLISHED_ASSET_SUFFIXES,
    SEARCH_SEGMENT,
    SITE_AUTHOR,
    SITE_DESCRIPTION,
    SITE_LANGUAGE,
    SITE_LONG_TITLE,
    SITE_TITLE,
    SITE_URL,
    SITEMAP_FILENAME,
    STATIC_DIR,
    TEMPLATE_DIR,
    WRITEUP_SEGMENT,
)

PYGMENTS_CSS_NAME = "pygments.css"

SECTION_TEMPLATES = {
    BLOG_SEGMENT: "post.html",
    WRITEUP_SEGMENT: "writeup.html",
}
DEFAULT_TEMPLATE = "page.html"
CTF_TEMPLATE = "writeup_ctf.html"
POST_LIST_TEMPLATE = "post_list.html"
SEARCH_TEMPLATE = "search.html"
NOT_FOUND_TEMPLATE = "not_found.html"
REDIRECT_TEMPLATE = "redirect.html"

NAV_LABELS = {url.strip("/"): label for label, url in NAV}


class MissingFrontPageError(Exception):
    pass


class DuplicateOutputError(Exception):
    pass


def make_environment():
    # StrictUndefined turns a template typo into a failure, not a blank page.
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals.update(
        site={
            "title": SITE_TITLE,
            "long_title": SITE_LONG_TITLE,
            "url": SITE_URL,
            "description": SITE_DESCRIPTION,
            "author": SITE_AUTHOR,
            "language": SITE_LANGUAGE,
        },
        nav=NAV,
        footer_links=FOOTER_LINKS,
    )
    return env


def write(relative_path, text):
    destination = OUTPUT_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def breadcrumbs_for(page, titles):
    """Entries are (label, url); a url of None marks a level with no page of its
    own. Home is implicit on the front page, so it only appears deeper in."""
    if not page.url.strip("/"):
        return []
    trail = [("Home", "/")]
    if page.section:
        trail.append(
            (NAV_LABELS.get(page.section, page.section.title()), f"/{page.section}/")
        )
    trail.extend(writeup.trail_within(page, titles))
    trail.append((page.title, page.url))
    return trail


def emit_pages(env, pages, challenges_by_ctf):
    titles = writeup.ctf_titles(pages)
    published = {}
    for page in pages:
        # Two sources can slugify to one URL; the second would replace the first.
        if page.output_path in published:
            raise DuplicateOutputError(
                f"{page.source} and {published[page.output_path]} both publish "
                f"at {page.url}"
            )
        published[page.output_path] = page.source

        name = SECTION_TEMPLATES.get(page.section, DEFAULT_TEMPLATE)
        context = {"page": page, "breadcrumbs": breadcrumbs_for(page, titles)}
        if writeup.is_ctf_index(page):
            name = CTF_TEMPLATE
            context["genres"] = writeup.group_by_genre(
                writeup.unlinked_writeups(page, challenges_by_ctf[page.url])
            )
        write(page.output_path, env.get_template(name).render(**context))


def emit_writeup_index(env, entries):
    """Replace the imported writeup README with a generated list of CTFs."""
    write(
        Path(WRITEUP_SEGMENT, INDEX_FILENAME),
        env.get_template("writeup_index.html").render(title="Writeup", entries=entries),
    )


def emit_blog_index(env, posts):
    write(
        Path(BLOG_SEGMENT, INDEX_FILENAME),
        env.get_template(POST_LIST_TEMPLATE).render(title="Blog", posts=posts),
    )


def emit_content_assets():
    """Copy the publishable non-page files, keeping their place in the source
    tree: the writeups reference their images by relative path."""
    for path in CONTENT_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in PUBLISHED_ASSET_SUFFIXES:
            continue
        relative = path.relative_to(CONTENT_DIR)
        # Redundant with the allowlist, but this is the check that would have
        # kept the checkout's .git, and its token, out of the output.
        if any(part.startswith(".") for part in relative.parts):
            continue
        # Directories follow the slugified pages; the file name does not,
        # because the Markdown names it as it is written on disk.
        destination = OUTPUT_DIR / Path(
            *(content.slugify_segment(part) for part in relative.parent.parts),
            relative.name,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def emit_assets():
    if STATIC_DIR.is_dir():
        shutil.copytree(STATIC_DIR, OUTPUT_DIR / "static", dirs_exist_ok=True)
    emit_content_assets()
    formatter = HtmlFormatter(
        style=render.PYGMENTS_STYLE, cssclass=render.HIGHLIGHT_CSS_CLASS
    )
    write(Path("static", PYGMENTS_CSS_NAME), formatter.get_style_defs())
    # Without this, Pages runs the output through Jekyll, which drops any
    # directory whose name starts with an underscore.
    write(".nojekyll", "")


def emit_search(env):
    write(
        Path(SEARCH_SEGMENT, INDEX_FILENAME),
        env.get_template(SEARCH_TEMPLATE).render(),
    )


def emit_not_found(env):
    write(NOT_FOUND_FILENAME, env.get_template(NOT_FOUND_TEMPLATE).render())


def emit_redirects(env, pages):
    """Write a receiver at every old URL the slug rules moved, and return the
    paths written so the sitemap can leave them out."""
    template = env.get_template(REDIRECT_TEMPLATE)
    written = []
    for path, target in redirects.collect(pages):
        write(path, template.render(target=target))
        written.append(path)
    return written


def emit_root_files(posts, entries, today):
    write(rootfiles.ROBOTS_FILENAME, rootfiles.build_robots())
    write(rootfiles.LLMS_FILENAME, rootfiles.build_llms(posts, entries))
    write(rootfiles.SECURITY_PATH, rootfiles.build_security(today))


def published_urls(withheld=()):
    """Taken from the output, not the page list, so copied files count and
    anything that failed to write does not. Sorted to keep the sitemap stable."""
    withheld = set(withheld)
    for path in sorted(OUTPUT_DIR.rglob(INDEX_FILENAME)):
        relative = path.relative_to(OUTPUT_DIR)
        if relative in withheld:
            continue
        directory = relative.parent
        yield "/" if directory == Path(".") else f"/{directory.as_posix()}/"


def emit_sitemap(withheld):
    """The redirects are withheld: a sitemap is a list of pages to index, and
    every one of them names another page as its canonical."""
    write(SITEMAP_FILENAME, sitemap.build_sitemap(published_urls(withheld)))


def build():
    # Wiping keeps a renamed or deleted page from lingering. It also removes the
    # Pagefind index, which is written here afterwards and has to be rebuilt.
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    renderer = render.make_renderer()
    pages = content.discover(CONTENT_DIR)
    for page in pages:
        page.html = render.render(renderer, page.body)
    posts = blog.collect_posts(pages)
    challenges_by_ctf = {
        ctf.url: writeup.challenges_of(ctf, pages)
        for ctf in writeup.collect_ctfs(pages)
    }

    entries = writeup.index_entries(pages, challenges_by_ctf)

    env = make_environment()
    emit_pages(env, pages, challenges_by_ctf)
    emit_writeup_index(env, entries)
    emit_blog_index(env, posts)
    emit_search(env)
    emit_not_found(env)
    redirected = emit_redirects(env, pages)
    # UTC, so the expiry it dates does not turn on where the build ran.
    emit_root_files(posts, entries, dt.datetime.now(dt.UTC).date())
    emit_assets()

    # A build with no content would otherwise exit zero with no way in.
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        raise MissingFrontPageError(
            f"no front page was generated: {CONTENT_DIR}/index.md is missing"
        )

    # Last, so it lists everything the build wrote.
    emit_sitemap(redirected)

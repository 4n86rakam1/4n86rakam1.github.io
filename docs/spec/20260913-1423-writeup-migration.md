# Migrating the writeups to the self-built generator

Written 2026-09-13. Removes MkDocs and makes the self-built generator the owner of every page.

## Goal

Move ownership of the 210 pages under `/writeup/` from MkDocs to the self-built generator, and remove MkDocs along with its configuration and dependencies. Fill the gaps in the output that publishing requires, and settle the parts of the design whose dimensions were never decided.

## Background

Material for MkDocs reaches end of life on 2026-11-05. Being a static generator, the build does not stop that day; it stops one or two Python releases later. The alternatives have already been evaluated and rejected: Zensical has no successor to `mkdocs-gen-files`; Hugo interprets shortcodes even inside code fences, so the `{{ }}` in the SSTI writeups takes the whole build down; Astro's glob loader cannot read paths containing `?`, and pages disappear silently while the build still exits zero.

The generator itself was written in Phase 1. Today MkDocs owns `/writeup/` and the generator merges its output. This spec covers Phase 2.

## Decisions

### URLs

The directory layout under `content/` is the URL layout. There is no routing configuration. `index.md` and `README.md` both mean "this page is the directory itself" and drop out of the URL. Output is always `<url>/index.html`.

URL segments are slugified: `?`, `#`, `"` and `'` are dropped, anything outside `[A-Za-z0-9._()-]` folds to `_`, and leading and trailing underscores are trimmed. Brackets stay — they are permitted as sub-delims by RFC 3986 and cause no trouble in practice.

**Compatibility with the MkDocs-era URLs is not kept.** Fourteen page URLs change. Ten of them can still be requested and are served a redirect page; the other four carry a `?` and never could be requested, so nothing placed there would ever be asked for. Nine image directories move as well and get nothing, a redirect page being no substitute for an image. This drops a constraint, but it is also a bug fix: a directory named `Where's skat?` produces a URL whose `?` opens a query string, and every relative link on that page then resolves against the parent directory. Twelve links are broken through that path on the published MkDocs site today.

This section said nineteen until the tree was counted. Nineteen is ten plus nine — the requestable page URLs plus the image directories — which applies the reachability test to the pages and withholds it from the directories, four of which carry the same `?`. Counted under one rule the figure is fourteen, or twenty-three with the image directories included. The writeup sources and `gh-pages`, the only surviving copy of the MkDocs-era site, agree on every one of those numbers.

Non-Markdown files (images) have their directories slugified but keep their file names as written on disk, because the Markdown refers to them by relative path.

### The writeup data model

Depth decides what a page is. `/writeup/` is the index, `/writeup/<ctf>/` is a CTF index, anything deeper is a challenge. The source tree already encodes this rule, so no extra metadata is needed.

CTFs are ordered by `start_at` from the front matter of the writeup repository's `README.md`, newest first; those without one sort by name at the end. **The ordering has a single source of truth in the writeup repository and is not duplicated here.** Keeping two copies would let one of them go stale, and the failure would be silent — the CTF would simply drop to the end as undated.

A challenge's genre is the third segment of its URL. Pages without a genre level group under an empty key, which sorts first.

The index lists the 22 CTFs that have a `README.md`. The five without one (`Grey_Cat_The_Flag_2024_Qualifiers`, `picoCTF`, `pwnable.tw`, `RPISEC`, `vlc-cybercontest`) are left out. That mirrors the state of the writeup repository rather than papering over it here.

**Two pages under those CTFs are consequently reachable only from the sitemap and the search index** (`/writeup/RPISEC/MBE/setup/` and `/writeup/picoCTF/Binary_Exploitation/Stonks/`): with no CTF index page, nothing links to them. The fix belongs in the writeup repository — a README for those directories — rather than in a generator that invents index pages for sources that do not have them.

A CTF index page lists the writeups its own text does not already link to. Most CTF READMEs carry a complete hand-written list, and those pages generate nothing. Some carry none, and some carry a partial one — `1753CTF_2024` links 10 of its 11 — so comparing the two sets rather than asking whether any link exists is what keeps the remainder reachable.

**There is no prev/next.** Ordering by genre name and then title is mechanical — it is neither difficulty order nor the order things were solved. Placing previous and next links on a sequence that carries no meaning suggests a continuity to the reader that does not exist. A secondary benefit: adding one writeup then rewrites only the new page and its CTF index, so a diff of the output stays small enough to read, which is what made the old navigation's non-determinism visible in the first place.

Three ways to navigate remain: breadcrumbs, the CTF index listing, and `/search/`. Breadcrumbs run `Home / Writeup / <CTF> / <genre> / <title>`. The genre level has no page of its own, so it is shown as plain text rather than a link.

### Rendering

python-markdown with `toc`, `tables`, `fenced_code`, `codehilite`, `attr_list`, `footnotes`, `md_in_html` and `pymdownx.superfences`.

**`pymdownx.superfences` is required.** Measured against the published MkDocs output, 22 files indent fences inside list items or wrap them in `<details>`, and plain `fenced_code` drops the code in all of them. With superfences the counts match exactly (22/22 for list-nested fences, 67/67 for `<details>` blocks).

`pymdown-extensions` therefore moves **from a transitive dependency of `mkdocs-material` to a direct one**. Forgetting this breaks the build the moment MkDocs is removed.

The Pygments CSS class is `highlight` throughout: superfences emits that, so codehilite's `css_class` is pointed at it rather than maintaining two stylesheets.

Links to other pages' Markdown are rewritten to the URLs those pages publish at, passing through the slug rules. Markdown percent-encodes what it finds in the source, so segments are decoded before being slugified.

Images are copied to the output keeping their place in the source tree.

### Design

**Structure is monospace, prose is proportional.** The header, breadcrumbs, headings, meta lines and table headers are set in the same monospace the sources are written in; only running prose is proportional. The material is Markdown and terminal output, so the furniture is built out of it rather than dressed over it.

This direction was chosen because the first pass, assembled entirely from safe defaults, left no trace of a decision anywhere: white ground, system UI, hairline grey rules, muted blue links — each individually reasonable, together indistinguishable from a generic blog template. Borrowing from the subject gives the site a handle that belongs to it.

Headings are prefixed with `##` and `###` as generated content. The marks never enter the HTML, so copying text does not pick them up, and their alternative text is empty (`content: "## " / ""`) so they stay out of the accessibility tree. With the structure in monospace the heading sizes sit close together, and the marks carry the level at a glance.

Light only. There is no dark mode.

- ground `#ffffff`
- text `#12151a`
- muted `#5d6673`
- rules `#e3e7ec`
- links `#12507f`
- code ground `#f4f6f8`

Prose is set in the system UI stack (`system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif`), structure in `ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, monospace`. No web fonts are loaded.

Dimensions run on scales: spacing in six steps (`0.2`, `0.4`, `0.7`, `1.1`, `1.8`, `3rem`), type in five (`0.74`, `0.84`, `0.95`, `1.05`, `1.4rem`), and one corner radius of `3px`. Nothing outside these is added.

**The step between heading levels is carried by the space above them, not by size** — `--s6` above an h2, `--s5` above an h3 — so section breaks stay findable while scrolling a long writeup. Weights are all 500, since monospace at 600 reads heavy. The bottom edge of the site header is a 2px rule, which sets it apart from the 1px rules elsewhere.

**Responsive behaviour.** One measure, 92ch, on every page. It is wider than a reading measure because the pages are mostly terminal output, code and tables, which a prose measure cuts off; their nesting — tables inside blockquotes, code inside `<details>` — rules out letting individual blocks break past the measure instead. Applying the same width everywhere keeps the layout from shifting as you move between a writeup and the pages around it.

Below that the column simply narrows, with a gutter of `--s4` either side. There is one breakpoint, at 34rem: the root size drops to 16px, the post list stacks its date above its title, and the structural links — nav, breadcrumbs, footer — gain vertical padding, since at 0.74rem to 0.84rem their tap target would otherwise be only as tall as the text. Nothing in the stylesheet sets a fixed width. What can outgrow the screen handles it in its own container: code blocks and tables scroll horizontally on their own, images cap at `max-width: 100%`, and long URLs break with `overflow-wrap`.

### Naming

The header carries the handle alone, `4n86rakam1`. `<title>` and `og:site_name` carry `Shinya Murakami (4n86rakam1)`, because a search result or a shared link is the only context a reader has there. The footer links to GitHub and LinkedIn.

### Output

Generate `sitemap.xml` listing every page URL except the redirect pages, **without `lastmod`**. A redirect page names another page as its canonical, so listing it would ask a crawler to index a page that disclaims itself. Source mtimes are rewritten by clone and rsync so they cannot be trusted, and the writeups carry no date, which would leave `lastmod` on the blog entries alone.

Generate `404.html`. GitHub Pages serves `/404.html` from the root.

Generate `robots.txt`, `/llms.txt` and `/.well-known/security.txt`, none of them written by hand. Nothing is withheld from crawlers, so `robots.txt` exists for its `Sitemap:` line alone. `llms.txt` is built from the page list — the posts and the CTF indexes, with the sitemap named for everything below them — because a hand-written index goes stale on the next writeup. `security.txt` reports through the repository's advisory form, which keeps a mailbox out of a file that is there to be scraped, and its `Expires` is computed from the build date. RFC 9116 caps that field at a year, so the workflow also runs on a monthly schedule: a site that is never rebuilt would otherwise serve an expired one.

Put search at `/search/` with Pagefind. Only that page and the redirect pages load JavaScript; article pages stay at zero. The index is built after the site with `uv run python -m pagefind --site dist`. Pagefind publishes a Python wrapper, so its binary is pinned in `uv.lock` with a hash like every other dependency, and the build needs no Node toolchain. Article templates mark their `<article>` with `data-pagefind-body`, which both narrows the index to the writing and keeps the listings, the search page, the 404 page and the redirect pages out of it. One `Search` entry joins the header nav. Pagefind's widget is restyled through the CSS variables it exposes so it does not arrive as a second design.

**Verify at the end of `build()` that a front page was written, and exit non-zero if not.** Measured: with the content missing the build still exits zero and produces a site with no entry point. That is the failure Astro was rejected for, and it should not be reproduced here.

### Tests

Tests run in three layers, all under `tests/` with pytest.

**Pure functions.** URL derivation, slugification, title resolution, link rewriting, post ordering, and the writeup collections. No I/O, so they run in under a tenth of a second.

**Stylesheet invariants.** The stylesheet is read as text and checked for the mistakes that render correctly on the machine that made them and wrong elsewhere: a font stack must end in a family that always resolves, emoji faces must sit behind it, and no fixed width may be declared. This layer exists because one such regression — emoji faces ahead of the generic family, which takes over `#` and the digits through their keycap glyphs — rendered identically on the machine that introduced it.

**The built site in a browser**, marked `browser` and run after the build and the search index. Layout invariants are measured rather than compared to an image, so they hold whichever fonts are installed: no page scrolls sideways at 375px or 1280px, code blocks scroll inside themselves, the search box is actually built by Pagefind, tap targets clear 30px. Structure is pinned with Playwright's ARIA snapshots, which describe the accessibility tree rather than the pixels, so a change of colour or spacing does not fail them. Only the front and search pages are snapshotted; a listing moves with the writeup repository and would report every new writeup as a regression.

Screenshot comparison is deliberately absent. The fonts differ between CI and a workstation, so it would report differences that are not regressions while missing ones that are.

- `content` — URL derivation (index/README dropping out, slugification), and title resolution falling back from front matter to the leading heading to the file name
- `render` — link rewriting (`index.md`, a plain `.md`, with a fragment, an external URL left alone, percent-encoded segments)
- `blog` — ordering newest first, and the error raised on a post with no date
- `writeup` — parsing `start_at` (string, datetime, date, absent), CTF ordering, genre grouping, and whether a page already links to what sits beneath it

### CI and removal

Check the writeup repository out into `content/writeup` instead of `docs/writeup`, and replace `uv run mkdocs gh-deploy --force` with build, then Pagefind, then the tests, then the browser checks, then an upload of `dist` as a Pages artifact that a second job deploys. The tests come after both builds, not before them: the checks that read the real output skip themselves when nothing is built, and a fresh runner has nothing built.

**Deploy through the Pages artifact, not a branch.** `actions/upload-pages-artifact` and `actions/deploy-pages` are published by GitHub, so the Actions policy admits them — it rejects only third parties, which rules out something like `peaceiris/actions-gh-pages`. The permission model is the reason to prefer them: the workflow keeps `contents: read` throughout, and only the deploy job holds `pages: write` and `id-token: write`, which it uses to request a deployment identity at run time. Pushing to a branch would instead need `contents: write` over the whole repository, and would commit build output back into git on every writeup change.

This reverses an earlier decision in this same document. The artifact route was avoided because the writeup paths carried spaces, `?` and `'`, which risked breaking in the tar the action builds. Slugification removed the condition: the built site now has no path containing a space or a shell-hostile character, and none outside ASCII.

The switch also needs the repository's Pages source changed from a branch to GitHub Actions. That is a settings change, not a commit, and the deploy fails until it is made.

Removal happens in the same commit: delete `mkdocs.yml`, `docs/gen_nav.py` and `docs/index.md`, drop the four MkDocs packages (`mkdocs`, `mkdocs-gen-files`, `mkdocs-literate-nav`, `mkdocs-material`) from pyproject, and add `content/writeup/` to `.gitignore`.

Sequence the work so the dependency swap and the tests land first and **the CI switch is the last commit**. Until it runs, main keeps deploying through `mkdocs gh-deploy`.

## Non-goals

- An RSS feed. Phase 1 had one; it is removed. Nothing subscribes to it, and maintaining a second output format costs more than restoring it would if that changes. The footer went with it, having held nothing else
- Tag and year listings for the blog. The generator can group by both, but with one post the classification pages outnumber the writing, and 210 writeups get by with a single index. Revisit when the listing itself is hard to scan
- An image pipeline (resizing, format conversion). Phase 1 decided against one and that holds
- Incremental builds. The whole site builds in under two seconds
- Linting the output HTML
- Migrating the four Hatena Blog posts, and cross-posting to dev.to with a canonical link. Separate work
- A dark mode toggle, a copy button on code blocks, an in-page table of contents. Each needs JavaScript and conflicts with article pages carrying none. Revisit if the need becomes real

## Verification

- The internal link check reports no breakage originating in the generator. Every `href` and `src` in the output is resolved against the output tree, skipping external schemes, `mailto:` and bare fragments; two of 2612 internal links fail, both in the article text — a relative link pointing below the page that carries it, and a PowerShell variable that Markdown read as a link. Both are broken in the MkDocs output too
- `uv run python -m ssg` exits zero and writes 224 pages: 214 of its own, and ten redirect pages standing at the MkDocs-era URLs. Pagefind indexes the 211 that carry writing
- Nothing in the output begins with a dot but `.nojekyll` and `.well-known/`, which holds `security.txt` and nothing else: the writeups arrive as a checkout, and its `.git` holds the token that made it
- pytest passes
- After the switch, the published front page, the URLs containing symbols, and the images all return HTTP 200

## Open questions

- Focus ring styling, a skip link, and measured contrast ratios
- Date formats differ: `13 September 2026` on the blog, `2026-09` in the writeup index
- External links: whether to mark them, and whether to open them in a new tab
- A visible permalink control on headings. Headings rendered from Markdown carry an `id`, so a deep link can be written by hand; there is nothing on the page to click to obtain one

## Status

Implemented on branch `review/ssg-phase1`, MkDocs removed. One step is not yet exercised: the deploy itself. The PAT available on this machine carries no Actions write permission, so the workflow cannot be started by hand, and the first run will be whatever push lands on main. Each deployment is recorded under the repository's Pages environment, so a bad one can be rolled back to the previous deployment from there.

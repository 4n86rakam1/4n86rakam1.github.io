---
name: serve
description: Build the site and serve it locally so it can be opened in a browser. Use when asked to run, preview, or look at the built site.
---

# Serving the site locally

Three steps. Each one fails quietly rather than loudly, which is why they are
written down.

## 1. The writeups have to be there

`content/writeup` is a separate repository, ignored by git and checked out by
CI. Without it the build still succeeds — it publishes the few pages that live
in this repository, and the browser tests skip their checks rather than fail
them, so nothing says the output is a fraction of the site.

```bash
ls content/writeup
```

The main checkout has them; a worktree starts with none, and only a worktree
needs this step. Copy the pages and leave the rest: that directory is a
checkout of its own wherever CI made it, and a checkout's `.git` — holding the
token that fetched it — has reached the published output here once already.

```bash
# from .claude/worktrees/<name>/
rsync -a --exclude .git ../../../content/writeup/ content/writeup/
```

Do not symlink: `Path.rglob` will not descend into a symlinked directory, and
the build finds nothing to publish.

## 2. Build, then index

The build wipes `dist` before writing to it, so an index made first is deleted
along with everything else. In the wrong order the search page is empty and
nothing says so.

```bash
uv run python -m ssg
uv run python -m pagefind --site dist
```

## 3. Serve

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Run it in the background and leave it up. Nothing watches `dist`, but nothing
caches it either, so a rebuild shows up on the next request.

## What to open

The front page survives every failure worth catching, so open what does not.
Take the addresses from the output rather than from a list here, which would go
stale as the writeups change:

```bash
# receivers left at the pre-slug URLs: each must answer, not 404
grep -rl 'content="0; url=' dist --include=index.html | sed 's|^dist||'

# and the pages they send the reader to
grep -rho 'content="0; url=[^"]*' dist --include=index.html | sed 's/.*url=//'
```

The search index is the other thing that goes missing without a word:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/pagefind/pagefind-ui.js
```

`python -m http.server` answers an unknown path with its own 404 rather than
`404.html`. That is the server, not the site.

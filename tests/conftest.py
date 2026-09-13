"""Helpers for the tests.

`Page` derives its URL from where its source sits under the content directory,
so the unit tests name paths rather than writing real files. The `site` fixture
serves the built site over HTTP, which the browser tests need.
"""

import http.server
import threading
from functools import partial

import pytest

from ssg.config import CONTENT_DIR, INDEX_FILENAME, OUTPUT_DIR
from ssg.content import Page


def page(relative_path, body="", **meta):
    return Page(source=CONTENT_DIR / relative_path, meta=meta, body=body)


def rendered(relative_path, html):
    built = page(relative_path)
    built.html = html
    return built


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        # The test run does not need a request log.
        pass


@pytest.fixture(scope="session")
def site():
    """Serve the built site, or skip when there is nothing built to serve."""
    if not (OUTPUT_DIR / INDEX_FILENAME).is_file():
        pytest.skip("no built site; run `uv run python -m ssg` first")
    handler = partial(QuietHandler, directory=str(OUTPUT_DIR))
    # Chromium opens several connections at once, and a single-threaded server
    # serialises them into timeouts.
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{server.server_address[1]}"
        server.shutdown()

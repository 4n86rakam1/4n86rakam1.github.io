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


# WCAG 2.1 AA for body-sized text, and the code background style.css sets.
# Shared by the checks in three files so there is one value to keep true, and
# pinned against the sheet by test_stylesheet: a ground taken from the thing it
# judges would re-measure every new colour against itself.
MINIMUM_CONTRAST = 4.5
CODE_BACKGROUND = "#f4f6f8"


def _channels(colour):
    digits = colour.lstrip("#")
    if len(digits) == 3:
        digits = "".join(digit * 2 for digit in digits)
    return [int(digits[at : at + 2], 16) / 255 for at in (0, 2, 4)]


def relative_luminance(colour):
    """WCAG 2.1's definition, written out here rather than taken from anything
    the site ships: a ratio measured with the site's own arithmetic would agree
    with whatever that arithmetic said."""
    linear = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in _channels(colour)
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(one, other):
    lighter, darker = sorted(
        (relative_luminance(one), relative_luminance(other)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


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

"""Render static/og-image.svg into the PNG that og:image points at.

Run with `uv run python -m ssg.og_image` after editing the SVG. The networks
will not fetch an SVG, so the PNG is the artefact, and this is what rendered
the committed one: the same source through another path would change every
pixel of it.
"""

import sys

from playwright.sync_api import sync_playwright

from .config import STATIC_DIR

SOURCE_NAME = "og-image.svg"
TARGET_NAME = "og-image.png"
# The viewBox, so the shape tests/test_assets.py checks holds.
WIDTH = 1200
HEIGHT = 630


def document(markup):
    # No margin, so the screenshot is the drawing and nothing around it.
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:#fff}</style>"
        f"{markup}"
    )


def render(source, target):
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(
            viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1
        )
        page.set_content(document(source.read_text(encoding="utf-8")))
        page.screenshot(path=target)
        browser.close()


def main():
    source = STATIC_DIR / SOURCE_NAME
    if not source.is_file():
        print(f"{source} is missing", file=sys.stderr)
        return 1
    render(source, STATIC_DIR / TARGET_NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main())

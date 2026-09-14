"""Invariants of the images the head points at.

Like the stylesheet checks, these are about the file itself: a share image of
the wrong shape or an icon that pulls in something from elsewhere looks fine
locally and is wrong once a crawler or another site fetches it.
"""

import struct
import xml.etree.ElementTree as ElementTree

import pytest

from ssg.config import STATIC_DIR

SVG_NAMESPACE = "http://www.w3.org/2000/svg"

# The names the templates and the JSON-LD spell out; a rename that misses one
# of them leaves a head pointing at nothing.
ICON_NAME = "favicon.svg"
SHARE_IMAGE_NAME = "og-image.png"
SHARE_IMAGE_SOURCE_NAME = "og-image.svg"

# 1.91:1 is what the open graph documentation asks for, and what the networks
# crop to when they are given something else.
SHARE_IMAGE_WIDTH = 1200
SHARE_IMAGE_HEIGHT = 630

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IHDR_OFFSET = 16

EXTERNAL_REFERENCE_MARKERS = ("http://", "https://", "//", "xlink:href")


def png_size(data):
    assert data[:8] == PNG_SIGNATURE, "not a PNG"
    return struct.unpack(">II", data[IHDR_OFFSET : IHDR_OFFSET + 8])


def view_box(path):
    root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    assert root.tag == f"{{{SVG_NAMESPACE}}}svg"
    return [float(value) for value in root.get("viewBox").split()]


@pytest.mark.parametrize("name", [ICON_NAME, SHARE_IMAGE_NAME, SHARE_IMAGE_SOURCE_NAME])
def test_the_head_points_at_a_file_that_exists(name):
    assert (STATIC_DIR / name).is_file()


def test_the_icon_is_square():
    # A viewBox of another shape is padded by the browser, off centre.
    _, _, width, height = view_box(STATIC_DIR / ICON_NAME)
    assert width == height


def test_the_icon_draws_itself():
    """An icon is fetched in contexts that run no scripts and load nothing
    else, so anything it refers to is simply missing."""
    markup = (STATIC_DIR / ICON_NAME).read_text(encoding="utf-8")
    assert "<script" not in markup
    for marker in EXTERNAL_REFERENCE_MARKERS:
        assert marker not in markup.replace(SVG_NAMESPACE, "")


def test_the_share_image_has_the_shape_the_networks_crop_to():
    data = (STATIC_DIR / SHARE_IMAGE_NAME).read_bytes()
    assert png_size(data) == (SHARE_IMAGE_WIDTH, SHARE_IMAGE_HEIGHT)


def test_the_share_image_matches_the_source_it_was_rendered_from():
    # The networks will not fetch an SVG, so the PNG is what the tag points at.
    _, _, width, height = view_box(STATIC_DIR / SHARE_IMAGE_SOURCE_NAME)
    assert (width, height) == (SHARE_IMAGE_WIDTH, SHARE_IMAGE_HEIGHT)

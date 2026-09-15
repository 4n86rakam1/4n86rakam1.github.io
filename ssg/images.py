"""Republishing the writeups' images as WebP.

Every image is encoded both ways, and the lossless file is published unless the
lossy one is clearly smaller. One rule cannot serve this content. A screenshot
of code or a terminal is a flat synthetic picture: it comes out smaller
losslessly than it does at quality 82, and lossy WebP subsamples chroma, which
drains the colour out of syntax-highlighted text at any quality setting —
raising the quality grows the file without recovering it. Photographs invert
both facts.

The margin is what makes the rule worth the arithmetic. Over the writeups as
they stand, publishing whichever file is merely smaller keeps 131 of them
lossless at 6.71 MB; asking the lossy one to be a third smaller before it wins
keeps 192 at 6.92 MB. A fifth of a megabyte buys back 61 screenshots, which is
the whole reason for encoding twice.
"""

import io

from PIL import Image

from .config import (
    IMAGE_LOSSY_QUALITY,
    IMAGE_LOSSY_SIZE_RATIO,
    IMAGE_SOURCE_SUFFIXES,
    IMAGE_TARGET_SUFFIX,
)

# libwebp's own default. The step up buys about a percent and costs several
# times the build.
ENCODER_METHOD = 4
# Under `lossless` Pillow reads `quality` as how hard to look for a shorter
# encoding rather than how much to throw away, so the lossy number would mean
# the opposite thing here.
LOSSLESS_EFFORT = 80


class UnreadableImageError(Exception):
    pass


def is_convertible(path):
    return path.suffix.lower() in IMAGE_SOURCE_SUFFIXES


def published_path(path):
    return path.with_suffix(IMAGE_TARGET_SUFFIX)


def _encoded(image, **options):
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", method=ENCODER_METHOD, **options)
    return buffer.getvalue()


def prefer_lossy(lossy_size, lossless_size):
    """Whether a lossy encoding is small enough to be worth what it throws away.

    The threshold, not a plain comparison: see the margin in the module
    docstring.
    """
    return lossy_size < lossless_size * IMAGE_LOSSY_SIZE_RATIO


def encode(path):
    """Return the WebP bytes to publish in place of the image at `path`."""
    try:
        with Image.open(path) as opened:
            # A palette or greyscale source cannot be saved as WebP as it
            # stands. Transparency reaches a palette image through a separate
            # key, so the bands alone do not say whether widening it may drop
            # anything.
            transparent = "A" in opened.getbands() or "transparency" in opened.info
            image = opened.convert("RGBA" if transparent else "RGB")
        lossless = _encoded(image, lossless=True, quality=LOSSLESS_EFFORT)
        lossy = _encoded(image, lossless=False, quality=IMAGE_LOSSY_QUALITY)
    except (OSError, Image.DecompressionBombError) as error:
        # The writeups come from a repository this one does not control. A file
        # named .png that no decoder recognises, or one too large for the WebP
        # encoder, would otherwise stop the build with a traceback that does not
        # say which file it was. Encoding is inside the guard as well as
        # decoding: the limits that bite are the encoder's.
        raise UnreadableImageError(
            f"{path} could not be republished as WebP"
        ) from error
    return lossy if prefer_lossy(len(lossy), len(lossless)) else lossless

"""How an image is chosen an encoding.

The interesting behaviour is not that a WebP comes out, but which of WebP's two
encodings each picture gets. A screenshot has to survive intact: lossy WebP
subsamples chroma, which drains the colour out of highlighted text, and the
writeups use those screenshots as evidence. A photograph has no such claim and
is much smaller lossily.
"""

import io
from random import Random

import pytest
from PIL import Image, ImageDraw

from ssg import images

# A WebP file announces itself in its first twelve bytes.
RIFF_HEADER = b"RIFF"
WEBP_FORM = b"WEBP"

SIZE = (320, 240)


def decoded(data):
    with Image.open(io.BytesIO(data)) as image:
        return image.convert("RGB").tobytes()


def screenshot():
    """Flat fields and hard edges, the way a terminal or an editor renders."""
    image = Image.new("RGB", SIZE, "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, SIZE[0], 24), fill="#2b3a2b")
    for row in range(6):
        top = 40 + row * 28
        draw.rectangle((16, top, 180, top + 10), fill="#c00000")
        draw.rectangle((190, top, 300, top + 10), fill="#0000c0")
    return image


def photograph():
    """No two neighbouring pixels alike, which is what lossy encoding is for."""
    noise = Random(0)
    image = Image.new("RGB", SIZE)
    image.putdata(
        [
            (noise.randrange(256), noise.randrange(256), noise.randrange(256))
            for _ in range(SIZE[0] * SIZE[1])
        ]
    )
    return image


@pytest.mark.parametrize("name", ["a.png", "a.PNG", "a.jpg", "a.jpeg"])
def test_an_image_is_converted(tmp_path, name):
    assert images.is_convertible(tmp_path / name)


@pytest.mark.parametrize("name", ["a.gif", "a.svg", "a.webp", "a.txt", "a"])
def test_everything_else_is_published_as_it_stands(tmp_path, name):
    # An animated GIF would arrive as a still, and an SVG is already smaller.
    assert not images.is_convertible(tmp_path / name)


def test_the_published_name_keeps_everything_but_the_suffix(tmp_path):
    assert images.published_path(tmp_path / "img" / "a.b.png").name == "a.b.webp"


def test_the_output_is_a_webp(tmp_path):
    source = tmp_path / "shot.png"
    screenshot().save(source)
    data = images.encode(source)
    assert data[:4] == RIFF_HEADER
    assert data[8:12] == WEBP_FORM


def test_a_screenshot_is_published_without_loss(tmp_path):
    """The colour of highlighted text in a screenshot is part of what the
    writeup is showing, and lossy WebP takes it whatever the quality."""
    source = tmp_path / "shot.png"
    original = screenshot()
    original.save(source)
    assert decoded(images.encode(source)) == original.convert("RGB").tobytes()


def test_a_photograph_is_published_lossily(tmp_path):
    source = tmp_path / "photo.png"
    original = photograph()
    original.save(source)
    data = images.encode(source)
    assert decoded(data) != original.convert("RGB").tobytes()
    # And the loss has to have bought something.
    assert len(data) < source.stat().st_size


def test_a_palette_image_survives_the_widening(tmp_path):
    """A palette source cannot be saved as WebP as it stands, and converting it
    is where a transparent one loses its transparency."""
    source = tmp_path / "flat.png"
    screenshot().convert("P", palette=Image.Palette.ADAPTIVE).save(source)
    with Image.open(io.BytesIO(images.encode(source))) as published:
        assert published.size == SIZE


def test_transparency_is_carried_through(tmp_path):
    source = tmp_path / "cut.png"
    cut = Image.new("RGBA", SIZE, (255, 0, 0, 0))
    ImageDraw.Draw(cut).rectangle((40, 40, 200, 160), fill=(0, 0, 255, 255))
    cut.save(source)
    with Image.open(io.BytesIO(images.encode(source))) as published:
        assert published.convert("RGBA").getpixel((0, 0))[3] == 0


# A thousand bytes losslessly, so the last lossy size that wins is 666 and the
# first that loses is 667. Written out rather than derived from the ratio: the
# two fixtures above sit so far apart that any threshold between about 0.24 and
# 1.0 encodes both of them the same way, which leaves the constant carrying the
# whole policy unconstrained by them.
LOSSLESS_SIZE = 1000


@pytest.mark.parametrize(
    "lossy_size,chosen",
    [(400, True), (666, True), (667, False), (999, False), (1200, False)],
)
def test_a_lossy_encoding_has_to_be_clearly_smaller_to_win(lossy_size, chosen):
    """Merely smaller is not enough. Relaxing this to a plain comparison moves
    61 of the writeups' screenshots onto the lossy path to save a fifth of a
    megabyte, which is the trade this threshold exists to refuse."""
    assert images.prefer_lossy(lossy_size, LOSSLESS_SIZE) is chosen

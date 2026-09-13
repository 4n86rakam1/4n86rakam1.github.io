"""Invariants of the stylesheet itself: the class of mistake that renders fine
on the machine that made it and wrong somewhere else, which a screenshot
comparison run on one machine cannot see."""

import re

import pytest

from ssg.config import STATIC_DIR

# Only families that always resolve end a stack: system-ui and the ui-* keywords
# are generic too, but can fail to resolve.
GENERIC_FAMILIES = {"sans-serif", "serif", "monospace", "cursive", "fantasy"}
# Emoji faces carry keycap glyphs for `#` and the digits, so ahead of the generic
# family they win the fallback for ordinary text.
EMOJI_FAMILIES = {"apple color emoji", "segoe ui emoji", "noto color emoji"}

# 1px is the visually-hidden idiom, not a layout width.
FIXED_WIDTH_PATTERN = re.compile(r"(?<!-)\bwidth:\s*(?!1px)\d+(?:\.\d+)?(px|rem|em)")


@pytest.fixture(scope="module")
def stylesheet():
    return (STATIC_DIR / "style.css").read_text(encoding="utf-8")


def font_stacks(css):
    """Yield (declaration, families) for every font stack in the sheet."""
    for match in re.finditer(r"--(?:sans|mono|struct|emoji):\s*([^;]+);", css):
        yield match.group(0), [part.strip() for part in match.group(1).split(",")]


def resolved_stack(css, name):
    """Expand one custom property, following var() all the way down: --struct is
    var(--mono), which ends in var(--emoji), so one level finds no emoji face."""
    stacks = {
        declaration.split(":")[0].strip(): families
        for declaration, families in font_stacks(css)
    }

    def expand(key, seen):
        assert key not in seen, f"{key} refers to itself"
        out = []
        for family in stacks[key]:
            reference = re.fullmatch(r"var\((--[\w-]+)\)", family)
            out.extend(
                expand(reference.group(1), seen | {key}) if reference else [family]
            )
        return out

    return expand(name, frozenset())


@pytest.mark.parametrize("name", ["--sans", "--mono", "--struct"])
def test_a_font_stack_names_a_generic_family(stylesheet, name):
    stack = resolved_stack(stylesheet, name)
    generics = [f for f in stack if f in GENERIC_FAMILIES]
    assert generics, f"{name} names no generic family"


@pytest.mark.parametrize("name", ["--sans", "--mono", "--struct"])
def test_emoji_faces_come_after_the_generic_family(stylesheet, name):
    stack = resolved_stack(stylesheet, name)
    first_generic = next(i for i, f in enumerate(stack) if f in GENERIC_FAMILIES)
    emoji = [i for i, f in enumerate(stack) if f.strip('"').lower() in EMOJI_FAMILIES]
    assert all(i > first_generic for i in emoji), (
        f"{name} lists an emoji face before its generic family, "
        "which takes over ordinary text where the named faces are absent"
    )


def test_no_fixed_width_is_declared(stylesheet):
    # A fixed width is what makes a page scroll sideways on a phone.
    assert not FIXED_WIDTH_PATTERN.findall(stylesheet)


def test_the_measure_is_the_only_max_width_on_the_body(stylesheet):
    body = re.search(r"\nbody\s*\{([^}]*)\}", stylesheet).group(1)
    assert "max-width: var(--measure)" in body
    assert body.count("max-width") == 1

"""Invariants of the stylesheet itself: the class of mistake that renders fine
on the machine that made it and wrong somewhere else, which a screenshot
comparison run on one machine cannot see."""

import re

import pytest
from conftest import CODE_BACKGROUND, MINIMUM_CONTRAST, contrast_ratio

from ssg.config import STATIC_DIR

# Only families that always resolve end a stack: system-ui and the ui-* keywords
# are generic too, but can fail to resolve.
GENERIC_FAMILIES = {"sans-serif", "serif", "monospace", "cursive", "fantasy"}
# Emoji faces carry keycap glyphs for `#` and the digits, so ahead of the generic
# family they win the fallback for ordinary text.
EMOJI_FAMILIES = {"apple color emoji", "segoe ui emoji", "noto color emoji"}

# 1px is the visually-hidden idiom, not a layout width.
FIXED_WIDTH_PATTERN = re.compile(r"(?<!-)\bwidth:\s*(?!1px)\d+(?:\.\d+)?(px|rem|em)")

# The palette as the sheet sets it, copied here by hand. A colour changed there
# and not here fails the first check below rather than quietly re-measuring the
# new value against itself. The code background lives in conftest because the
# highlight checks in two other files measure against it too, and this is where
# it is held to what the sheet actually declares.
PAGE_BACKGROUND = "#ffffff"
TEXT_COLOURS = {"--fg": "#12151a", "--link": "#12507f", "--muted": "#5d6673"}
# WCAG 2.1 AA asks 3:1 of a mark that carries meaning without being read, which
# is what the breadcrumb separator is: the ordered list already tells a screen
# reader where the page sits. Only the page background, the one ground a mark
# in this colour is ever drawn on.
MINIMUM_NON_TEXT_CONTRAST = 3
NON_TEXT_COLOURS = {"--faint": "#8d939c"}


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


def test_the_palette_is_the_one_the_contrast_checks_measure(stylesheet):
    """Without this the checks below go on passing after a colour changes, by
    measuring whatever the sheet now says against itself."""
    declared = dict(
        TEXT_COLOURS,
        **NON_TEXT_COLOURS,
        **{"--bg": PAGE_BACKGROUND, "--code-bg": CODE_BACKGROUND},
    )
    for token, value in declared.items():
        assert f"{token}: {value};" in stylesheet, f"{token} is no longer {value}"


@pytest.mark.parametrize("token", sorted(TEXT_COLOURS))
@pytest.mark.parametrize(
    "ground", [PAGE_BACKGROUND, CODE_BACKGROUND], ids=["page", "code"]
)
def test_every_text_colour_clears_the_contrast_minimum(token, ground):
    ratio = contrast_ratio(TEXT_COLOURS[token], ground)
    assert ratio >= MINIMUM_CONTRAST, f"{token} on {ground} is {ratio:.2f}:1"


@pytest.mark.parametrize("token", sorted(NON_TEXT_COLOURS))
def test_every_non_text_colour_clears_its_own_minimum(token):
    ratio = contrast_ratio(NON_TEXT_COLOURS[token], PAGE_BACKGROUND)
    assert ratio >= MINIMUM_NON_TEXT_CONTRAST, (
        f"{token} on {PAGE_BACKGROUND} is {ratio:.2f}:1"
    )


def test_no_glyph_is_drawn_in_the_border_colour(stylesheet):
    """--rule is for lines. A character drawn in it reads as an artefact rather
    than a mark, which is what the breadcrumb separator was."""
    for block in re.findall(r"\{[^}]*\}", stylesheet):
        # Either quote: a separator respelled with single quotes is the same
        # glyph and would otherwise walk past this.
        if re.search(r"content:\s*[\"']\S", block):
            assert "var(--rule)" not in block, block.strip()


def test_the_sheet_draws_its_own_focus_ring(stylesheet):
    """Left to the browser, the ring is drawn against assumptions this palette
    does not share. :focus alone would leave one behind after a mouse click."""
    assert ":focus-visible" in stylesheet


def test_the_skip_link_keeps_its_place_in_the_tab_order(stylesheet):
    """A skip link is only reachable by the Tab that needs it, and either of
    these takes it out of the tab order altogether. Every rule that hides it is
    checked, not one named block: it shares the hiding with a utility class, and
    a later rule could add one of them back."""
    rules = [
        declarations
        for selectors, declarations in re.findall(r"([^{}]*)\{([^}]*)\}", stylesheet)
        if ".skip-link" in selectors and ":focus" not in selectors
    ]
    assert rules, "nothing in the sheet hides the skip link"
    for declarations in rules:
        assert "display: none" not in declarations
        assert "visibility: hidden" not in declarations


def test_the_heading_anchor_is_drawn_as_text_rather_than_as_a_mark(stylesheet):
    """The permalink is a link whose text is the character itself, so it is held
    to the text minimum. --faint clears 3:1 and no more, which is the ground a
    decorative mark stands on, not this one."""
    rule = re.search(r"\n\.headerlink\s*\{([^}]*)\}", stylesheet)
    assert rule is not None, "the sheet no longer has a .headerlink rule to check"
    token = re.search(r"color:\s*var\((--[\w-]+)\)", rule.group(1))
    assert token is not None, ".headerlink names no colour"
    assert token.group(1) in TEXT_COLOURS, f".headerlink is drawn in {token.group(1)}"

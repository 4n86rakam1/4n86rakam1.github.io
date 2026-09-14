"""Which old URLs get a receiver, and which cannot have one.

The old paths are literals read off the `gh-pages` branch, the only copy of the
MkDocs-era site. Deriving them the way the generator does would make this file
agree with it by construction and notice nothing.
"""

from pathlib import Path

from conftest import page

from ssg import redirects

# Every old page directory whose URL the slug rules change. Ten can still be
# requested; the four carrying a `?` cannot.
MOVED_ON_THE_OLD_SITE = {
    "writeup/CSAW-CTF-2023-Quals/pwn/target practice": (
        "/writeup/CSAW-CTF-2023-Quals/pwn/target_practice/"
    ),
    "writeup/CSAW-CTF-2023-Quals/rev/rebug 1": (
        "/writeup/CSAW-CTF-2023-Quals/rev/rebug_1/"
    ),
    "writeup/CSAW-CTF-2023-Quals/rev/rebug 2": (
        "/writeup/CSAW-CTF-2023-Quals/rev/rebug_2/"
    ),
    "writeup/CSAW-CTF-2023-Quals/web/MTA Prices": (
        "/writeup/CSAW-CTF-2023-Quals/web/MTA_Prices/"
    ),
    "writeup/IrisCTF_2024/Forensics/skat's_SD_Card": (
        "/writeup/IrisCTF_2024/Forensics/skats_SD_Card/"
    ),
    "writeup/IrisCTF_2024/Networks/skat's_Network_History": (
        "/writeup/IrisCTF_2024/Networks/skats_Network_History/"
    ),
    "writeup/IrisCTF_2024/Reverse_Engineering/The_Johnson's": (
        "/writeup/IrisCTF_2024/Reverse_Engineering/The_Johnsons/"
    ),
    "writeup/UofTCTF_2024/IoT/Baby's_First_IoT_Flag_1": (
        "/writeup/UofTCTF_2024/IoT/Babys_First_IoT_Flag_1/"
    ),
    "writeup/UofTCTF_2024/IoT/Baby's_First_IoT_Flag_2": (
        "/writeup/UofTCTF_2024/IoT/Babys_First_IoT_Flag_2/"
    ),
    "writeup/UofTCTF_2024/Jail/Baby's_First_Pyjail": (
        "/writeup/UofTCTF_2024/Jail/Babys_First_Pyjail/"
    ),
}

UNREQUESTABLE_ON_THE_OLD_SITE = (
    "writeup/IrisCTF_2024/Networks/Where's_skat?",
    "writeup/IrisCTF_2024/Open-Source_Intelligence/Czech_Where?",
    "writeup/IrisCTF_2024/Reverse_Engineering/Rune?_What's_that?",
    "writeup/IrisCTF_2024/Web_Exploitation/What's_My_Password?",
)

OLD_SITE_PAGES = [
    page(f"{directory}/index.md")
    for directory in (*MOVED_ON_THE_OLD_SITE, *UNREQUESTABLE_ON_THE_OLD_SITE)
]


def test_a_path_the_slug_rules_leave_alone_gets_no_receiver():
    assert redirects.collect([page("writeup/X/plain/index.md")]) == []


def test_every_requestable_old_path_of_the_old_site_gets_one():
    written = dict(redirects.collect(OLD_SITE_PAGES))
    assert {
        path.parent.as_posix(): target for path, target in written.items()
    } == MOVED_ON_THE_OLD_SITE


def test_a_receiver_is_an_index_html_at_the_old_path():
    ((path, _),) = redirects.collect([page("writeup/X/thing 1/index.md")])
    assert path == Path("writeup", "X", "thing 1", "index.html")


def test_a_question_mark_leaves_the_path_with_no_receiver():
    # The `?` starts a query string, which is why the slug rules drop it.
    unreachable = [page(f"{d}/index.md") for d in UNREQUESTABLE_ON_THE_OLD_SITE]
    assert redirects.collect(unreachable) == []
    assert len(redirects.unrequestable(unreachable)) == len(
        UNREQUESTABLE_ON_THE_OLD_SITE
    )


def test_a_fragment_leaves_the_path_with_no_receiver():
    assert redirects.collect([page("writeup/X/a#b/index.md")]) == []


def test_no_receiver_lands_on_a_page_of_the_sites_own():
    """What lets `collect` skip checking: a receiver sits at a path the slug
    rules rewrite, and no published page does."""
    published = {page.output_path for page in OLD_SITE_PAGES}
    assert not published & {path for path, _ in redirects.collect(OLD_SITE_PAGES)}


def test_the_receivers_do_not_come_back_in_the_order_the_pages_arrived():
    # Asserting it is sorted would pass off `sorted(...)` as a property of the
    # result. What matters is that the order does not follow the input.
    assert redirects.collect(OLD_SITE_PAGES) == redirects.collect(
        list(reversed(OLD_SITE_PAGES))
    )

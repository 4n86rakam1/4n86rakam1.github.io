import datetime as dt

from conftest import page, rendered

from ssg.writeup import (
    collect_ctfs,
    ctf_titles,
    group_by_genre,
    index_entries,
    is_ctf_index,
    unlinked_writeups,
    start_date,
    trail_within,
)


def ctf(name, start_at=None, title=None):
    meta = {"start_at": start_at} if start_at is not None else {}
    body = f"# {title}\n" if title else ""
    return page(f"writeup/{name}/README.md", body=body, **meta)


def challenge(ctf_name, genre, name):
    return page(f"writeup/{ctf_name}/{genre}/{name}/index.md", body=f"# {name}\n")


def test_start_at_is_read_from_an_iso_string():
    assert start_date(ctf("X", "2026-09-13T10:00:00")) == dt.date(2026, 9, 13)


def test_start_at_accepts_a_date():
    assert start_date(ctf("X", dt.date(2026, 9, 13))) == dt.date(2026, 9, 13)


def test_start_at_accepts_a_datetime():
    assert start_date(ctf("X", dt.datetime(2026, 9, 13, 10))) == dt.date(2026, 9, 13)


def test_a_missing_start_at_is_not_a_date():
    assert start_date(ctf("X")) is None


def test_an_unparseable_start_at_is_not_a_date():
    assert start_date(ctf("X", "last summer")) is None


def test_a_ctf_index_sits_two_levels_deep():
    assert is_ctf_index(ctf("X")) is True
    assert is_ctf_index(challenge("X", "web", "chall")) is False


def test_ctfs_come_back_newest_first():
    older = ctf("Older", "2025-01-01", title="Older")
    newer = ctf("Newer", "2026-01-01", title="Newer")
    assert collect_ctfs([older, newer]) == [newer, older]


def test_undated_ctfs_sort_by_name_at_the_end():
    dated = ctf("Dated", "2026-01-01", title="Dated")
    zeta = ctf("Zeta", title="Zeta")
    alpha = ctf("Alpha", title="Alpha")
    assert collect_ctfs([zeta, alpha, dated]) == [dated, alpha, zeta]


def test_challenges_group_under_their_genre():
    web = challenge("X", "web", "one")
    pwn = challenge("X", "pwn", "two")
    assert group_by_genre([web, pwn]) == [("pwn", [pwn]), ("web", [web])]


def test_a_challenge_without_a_genre_groups_under_an_empty_name():
    flat = page("writeup/X/The_Mission/index.md", body="# The Mission\n")
    assert group_by_genre([flat]) == [("", [flat])]


def test_a_writeup_the_page_already_links_is_left_out():
    chall = challenge("X", "web", "one")
    index = rendered("writeup/X/README.md", '<a href="web/one/">one</a>')
    assert unlinked_writeups(index, [chall]) == []


def test_a_page_linking_only_elsewhere_leaves_everything_unlinked():
    chall = challenge("X", "web", "one")
    index = rendered("writeup/X/README.md", '<a href="https://example.com/">x</a>')
    assert unlinked_writeups(index, [chall]) == [chall]


def test_a_partial_list_leaves_only_what_it_omits():
    # A README that links some of its writeups used to suppress the generated
    # list entirely, leaving the rest reachable from nowhere.
    listed = challenge("X", "web", "one")
    missing = challenge("X", "misc", "two")
    index = rendered("writeup/X/README.md", '<a href="web/one/">one</a>')
    assert unlinked_writeups(index, [listed, missing]) == [missing]


def test_the_count_of_writeups_reaches_the_index_row():
    index = ctf("X", "2026-01-01", title="X")
    chall = challenge("X", "web", "one")
    entries = index_entries([index, chall], {index.url: [chall]})
    assert entries[0]["count"] == 1


def test_a_trail_names_the_ctf_and_the_genre():
    index = ctf("X", "2026-01-01", title="X CTF")
    titles = ctf_titles([index])
    assert trail_within(challenge("X", "web", "one"), titles) == [
        ("X CTF", "/writeup/X/"),
        ("web", None),
    ]


def test_a_ctf_without_an_index_page_is_not_linked():
    # Five CTFs carry no README, so there is no page to point at.
    assert trail_within(challenge("X", "web", "one"), {}) == [
        ("X", None),
        ("web", None),
    ]


def test_a_ctf_index_has_nothing_below_it_in_the_trail():
    assert trail_within(ctf("X"), {}) == []

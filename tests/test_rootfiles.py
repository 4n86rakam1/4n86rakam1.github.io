"""robots.txt, llms.txt and security.txt.

The expected strings are written out rather than read back from the module: a
test that formats its expectation the way the generator does passes anything.
"""

import datetime as dt

from conftest import page

from ssg import rootfiles


def ctf(relative_path, title, count):
    entry = page(relative_path, f"# {title}\n")
    return {"page": entry, "date": None, "count": count}


def fields(text):
    return dict(
        line.split(": ", 1) for line in text.splitlines() if line and ":" in line
    )


def test_robots_points_at_the_sitemap():
    assert "Sitemap: https://4n86rakam1.github.io/sitemap.xml" in (
        rootfiles.build_robots()
    )


def test_robots_withholds_nothing():
    assert "Disallow:" not in rootfiles.build_robots()


def test_security_expires_a_year_after_the_build():
    written = fields(rootfiles.build_security(dt.date(2026, 9, 13)))
    assert written["Expires"] == "2027-09-13T00:00:00Z"


def test_security_expires_within_the_year_rfc_9116_asks_for():
    issued = dt.date(2026, 9, 13)
    expires = dt.datetime.strptime(
        fields(rootfiles.build_security(issued))["Expires"], "%Y-%m-%dT%H:%M:%SZ"
    ).date()
    assert issued < expires <= issued.replace(year=issued.year + 1)


def test_security_moves_with_the_build_date():
    first = fields(rootfiles.build_security(dt.date(2026, 9, 13)))["Expires"]
    second = fields(rootfiles.build_security(dt.date(2027, 3, 1)))["Expires"]
    assert first != second


def test_security_carries_the_two_required_fields():
    written = fields(rootfiles.build_security(dt.date(2026, 9, 13)))
    assert set(written) >= {"Contact", "Expires"}


def test_security_publishes_no_mail_address():
    assert "@" not in rootfiles.build_security(dt.date(2026, 9, 13))


def test_security_names_where_it_is_served_from():
    written = fields(rootfiles.build_security(dt.date(2026, 9, 13)))
    assert (
        written["Canonical"] == "https://4n86rakam1.github.io/.well-known/security.txt"
    )


def test_llms_opens_with_the_site_as_its_heading_and_summary():
    written = rootfiles.build_llms([], []).splitlines()
    assert written[0] == "# 4n86rakam1"
    assert written[2] == "> Security engineering notes and CTF writeups."


def test_llms_links_a_post_with_its_description():
    post = page("blog/hello.md", "# Hello", title="Hello", description="A first post")
    assert (
        "- [Hello](https://4n86rakam1.github.io/blog/hello/): A first post"
        in rootfiles.build_llms([post], [])
    )


def test_llms_falls_back_to_the_date_when_a_post_has_no_description():
    post = page("blog/hello.md", title="Hello", date=dt.date(2026, 9, 13))
    assert "/blog/hello/): 2026-09-13" in rootfiles.build_llms([post], [])


def test_llms_counts_the_writeups_under_each_ctf():
    written = rootfiles.build_llms([], [ctf("writeup/SomeCTF/README.md", "Some", 12)])
    assert (
        "- [Some](https://4n86rakam1.github.io/writeup/SomeCTF/): 12 writeups"
        in written
    )


def test_llms_does_not_say_one_writeups():
    written = rootfiles.build_llms([], [ctf("writeup/SomeCTF/README.md", "Some", 1)])
    assert ": 1 writeup" in written and "1 writeups" not in written


def test_llms_leaves_out_a_section_it_has_nothing_for():
    assert "## Blog" not in rootfiles.build_llms([], [])


def test_llms_points_at_the_sitemap_for_everything_it_leaves_out():
    assert "https://4n86rakam1.github.io/sitemap.xml" in rootfiles.build_llms([], [])

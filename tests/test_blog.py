import datetime as dt

import pytest
from conftest import page

from ssg.blog import MissingDateError, collect_posts


def post(name, date):
    return page(f"blog/{name}.md", date=date)


def test_posts_come_back_newest_first():
    older = post("older", dt.date(2025, 1, 1))
    newer = post("newer", dt.date(2026, 1, 1))
    assert collect_posts([older, newer]) == [newer, older]


def test_pages_outside_the_blog_are_not_posts():
    assert collect_posts([page("about/index.md")]) == []


def test_a_post_without_a_date_is_an_error():
    # Ordering it last silently would hide a content mistake.
    with pytest.raises(MissingDateError, match="undated.md"):
        collect_posts([page("blog/undated.md")])

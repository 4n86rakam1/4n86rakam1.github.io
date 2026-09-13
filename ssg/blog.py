"""Blog collections. A post without a date is a content error rather than
something to guess at, so it is reported instead of being ordered last."""

from .config import BLOG_SEGMENT


class MissingDateError(Exception):
    pass


def collect_posts(pages):
    posts = [page for page in pages if page.section == BLOG_SEGMENT]
    undated = [post.source.name for post in posts if post.date is None]
    if undated:
        raise MissingDateError(
            "blog posts without a `date` front matter field: "
            + ", ".join(sorted(undated))
        )
    return sorted(posts, key=lambda post: post.date, reverse=True)

"""Command line entry point: `uv run python -m ssg`."""

import sys

from .blog import MissingDateError
from .build import DuplicateOutputError, MissingFrontPageError, build


def main():
    try:
        build()
    except (DuplicateOutputError, MissingDateError, MissingFrontPageError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

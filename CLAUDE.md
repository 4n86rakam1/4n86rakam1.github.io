# CLAUDE.md

Three things that go wrong quietly here.

- `content/writeup` is another repository: git ignores it, CI checks it out. A
  build without it succeeds and publishes a fraction of the site, and the
  browser tests skip rather than fail. `.claude/skills/serve` has the steps.
- `python -m ssg` wipes `dist` first, so index and test after it, never before.
  Tests run first skip every check that reads real output, including the guard
  against publishing a checkout's `.git`.
- No test takes its expectation from the code under test. Literals, not
  imports: a test that reads `config.SITE_URL` passes whatever it says.

import mkdocs_gen_files
import os
import glob
import re
from dataclasses import dataclass, field
from datetime import datetime
import frontmatter


@dataclass
class Challenge:
    md_path: str
    nav_keys: list[str] = field(default_factory=list)

    def __post_init__(self):
        parts = self.md_path.split("/")
        self.genre, self.challenge_name, _ = parts[-3:]

        if self.genre:
            self.nav_keys.append(self.genre)
        self.nav_keys.append(self.challenge_name)


@dataclass
class CTF:
    md_path: str
    nav_keys: list[str] = field(default_factory=list)
    challenges: list[Challenge] = field(default_factory=list)

    def __post_init__(self):
        with open(self.md_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("# "):
                    self.name = line[2:].strip()
                    break
            else:
                self.name = self.md_path.split("/")[-2]

        self.start_at = self._extract_start_at()
        self.nav_keys = ["Writeup", self.sort_key, self.name]

    @property
    def sort_key(self):
        if self.start_at:
            return f"{self.start_at.year}/{self.start_at.month:02d}"

        return "Other"

    @property
    def directory(self):
        return os.path.dirname(self.md_path)

    def __gt__(self, other):
        if self.start_at is None:
            return False
        if other.start_at is None:
            return True
        return self.start_at > other.start_at

    def _extract_start_at(self):
        try:
            with open(self.md_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                start_at = post.get("start_at")
                if not start_at:
                    return None
                return datetime.fromisoformat(start_at)
        except Exception as e:
            print(f"Error parsing {self.md_path}: {e}")
        return None


nav = mkdocs_gen_files.Nav()
nav["Home"] = "index.md"

ctfs = []
for ctf_md_path in glob.glob("docs/writeup/*/*.md"):
    ctf = CTF(ctf_md_path)
    for challenge_md_path in glob.glob(f"{ctf.directory}/**/*.md", recursive=True):
        if challenge_md_path == ctf_md_path:
            continue

        challenge = Challenge(challenge_md_path, ctf.nav_keys.copy())
        ctf.challenges.append(challenge)

    ctfs.append(ctf)

ctfs.sort(reverse=True)

if ctfs:
    nav["Writeup"] = "writeup/README.md"

for ctf in ctfs:
    nav[ctf.nav_keys] = os.path.relpath(ctf.md_path, "docs")

    for challenge in ctf.challenges:
        nav[challenge.nav_keys] = os.path.relpath(challenge.md_path, "docs")

with mkdocs_gen_files.open("SUMMARY.md", "w") as f:
    print("".join(nav.build_literate_nav()), file=f)

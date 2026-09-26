"""PHASE 1 · Parse the regulation into provisions (articles and annexes).

Read first: notes Days 53 (documents) and 56 (parsing & chunking).

After html_to_text(), the Act is one line per text block. The structure you need looks like:

    ...recitals...
    HAVE ADOPTED THIS REGULATION:
    CHAPTER I
    GENERAL PROVISIONS
    Article 1
    Subject matter
    1. The purpose of this Regulation is ...
    2. This Regulation lays down ...
    Article 2
    Scope
    ...
    CHAPTER II
    PROHIBITED AI PRACTICES
    Article 5
    Prohibited AI practices
    ...
    ANNEX III
    High-risk AI systems referred to in Article 6(2)
    1. Biometrics, in so far as ...

Legal structure is your best chunking signal: people cite "Article 5" or "Annex III", and
answers must cite them too. Keep that structure as metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Provision:
    id: str  # "art-5", "art-6a", "annex-iii"
    kind: str  # "article" | "annex"
    number: str  # "5", "6a", "III"
    title: str  # "Prohibited AI practices"
    chapter: str = ""  # "CHAPTER II · PROHIBITED AI PRACTICES" (articles only; "" for annexes)
    lines: list[str] = field(default_factory=list)  # body lines, in order (title excluded)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


ARTICLE_RE = re.compile(r"^Article (\d+[a-z]?)$")
CHAPTER_RE = re.compile(r"^CHAPTER ([IVXLC]+)$")
ANNEX_RE = re.compile(r"^ANNEX ([IVXLC]+)$")
START_MARKER = "HAVE ADOPTED THIS REGULATION"


def parse_act(text: str) -> list[Provision]:
    """Split the Act's text into Provisions, in document order.

    Rules:
    - If START_MARKER appears, ignore everything up to and including that line (recitals).
      Recitals mention "Article 5" in running text, but only whole lines matching the regexes count.
    - A line matching CHAPTER_RE starts a new chapter: the chapter label is
      f"CHAPTER {roman} · {next line}", and that next line is not body text.
      The chapter applies to the articles that follow, until the next chapter.
    - A line matching ARTICLE_RE starts an article; the NEXT line is its title.
      id = f"art-{number}" (lower case), kind = "article".
    - A line matching ANNEX_RE starts an annex; the next line is its title.
      id = f"annex-{roman.lower()}", kind = "annex", chapter = "".
    - Every other line is appended to the current provision's lines (ignore lines before
      the first provision).
    - Cross-references inside text ("as referred to in Article 6(2)") never match, because
      the regexes require the whole line.
    - If an id repeats (e.g. a table of contents), keep the FIRST provision with content
      and drop later empty duplicates; if the first one is empty, use the later one.
    """
    provisions: list[Provision] = []
    started = START_MARKER not in text  # no marker → parse from the first line

    chapter = ""  # label of the chapter we're currently in
    chapter_roman = ""  # "II" from "CHAPTER II", kept until we see its name
    current: Provision | None = None
    expect_title = False  # the next line is an article/annex title
    expect_chapter_name = False  # the next line is a chapter name

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # 1. Skip the recitals, including the marker line itself
        if not started:
            if START_MARKER in line:
                started = True
            continue

        # 2. Lines that a previous heading told us to expect
        if expect_chapter_name:
            chapter = f"CHAPTER {chapter_roman} · {line}"
            expect_chapter_name = False
            continue

        if expect_title and current is not None:
            current.title = line
            expect_title = False
            continue

        # 3. Headings
        if m := CHAPTER_RE.match(line):
            chapter_roman = m.group(1)
            expect_chapter_name = True
            continue

        if m := ARTICLE_RE.match(line):
            number = m.group(1)
            current = Provision(
                id=f"art-{number.lower()}", kind="article", number=number, title="", chapter=chapter
            )
            provisions.append(current)
            expect_title = True
            continue

        if m := ANNEX_RE.match(line):
            number = m.group(1)
            current = Provision(id=f"annex-{number.lower()}", kind="annex", number=number, title="")
            provisions.append(current)
            expect_title = True
            continue

        # 4. Everything else is body text of the current provision
        if current is not None:
            current.lines.append(line)

    # 5. Remove duplicates: keep the first one with content
    result: list[Provision] = []
    position: dict[str, int] = {}  # id -> index in result
    for p in provisions:
        if p.id not in position:
            position[p.id] = len(result)
            result.append(p)
        elif not result[position[p.id]].lines and p.lines:
            result[position[p.id]] = p  # first was empty, use this one instead

    return result

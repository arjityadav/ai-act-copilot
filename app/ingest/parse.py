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
    id: str                    # "art-5", "art-6a", "annex-iii"
    kind: str                  # "article" | "annex"
    number: str                # "5", "6a", "III"
    title: str                 # "Prohibited AI practices"
    chapter: str = ""          # "CHAPTER II · PROHIBITED AI PRACTICES" (articles only; "" for annexes)
    lines: list[str] = field(default_factory=list)   # body lines, in order (title excluded)

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
    # YOUR CODE
    raise NotImplementedError

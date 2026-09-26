"""PHASE 1 · Chunk provisions for retrieval.

Read first: notes Day 56 (chunking) and the contextual-retrieval idea (Day 56, 62).

Legal-aware chunking: split an article at its numbered paragraphs ("1.", "2.", ...), pack
paragraphs together up to a size limit, and give every chunk a header saying where it comes
from. A chunk like "the provider shall ensure..." is useless without knowing it's Article 16.
"""

from __future__ import annotations

import re

from app.ingest.parse import Provision
from app.retrieval.store import Chunk

PARA_RE = re.compile(r"^(\d+)\.(\s|$)")


def split_paragraphs(lines: list[str]) -> list[str]:
    """Group body lines into paragraphs.

    - A line matching PARA_RE ("1. text" or a bare "1.") starts a new paragraph.
    - Other lines continue the current paragraph (joined with a single space).
    - If a paragraph number stands alone on its line ("1."), the text on the next line belongs to it:
      produce "1. text", not "1." and "text" separately.
    - Lines before the first numbered line form a paragraph of their own.
    - If there are no numbered lines at all (e.g. short articles), return one paragraph per line.
    Return a list of non-empty paragraph strings.
    """
    # Clean up: strip whitespace and drop empty lines
    lines = [ln.strip() for ln in lines if ln.strip()]

    # No numbered lines at all → one paragraph per line
    if not any(PARA_RE.match(ln) for ln in lines):
        return lines

    paragraphs: list[str] = []
    current: list[str] = []  # parts of the paragraph being built
    for line in lines:
        # A numbered line closes the previous paragraph and starts a new one
        if PARA_RE.match(line) and current:
            paragraphs.append(" ".join(current))
            current = []
        current.append(line)

    # The last paragraph is still open when the loop ends
    if current:
        paragraphs.append(" ".join(current))

    return paragraphs


def header_for(p: Provision) -> str:
    """Context header prepended to every chunk. (Given.)"""
    where = f"Article {p.number}" if p.kind == "article" else f"Annex {p.number}"
    return f"EU AI Act · {where} · {p.title}" + (f" · {p.chapter}" if p.chapter else "")


def _split_sentences(text: str, max_chars: int) -> list[str]:
    """Split one long paragraph at '. ' into pieces of at most max_chars (where possible)."""
    parts = text.split(". ")
    # split() removed the ". ": put the full stop back on every part except the last
    sentences = [s + "." for s in parts[:-1]] + [parts[-1]]

    pieces: list[str] = []
    current = ""
    for s in sentences:
        candidate = f"{current} {s}" if current else s
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = s  # a single sentence longer than max_chars stays whole
    if current:
        pieces.append(current)
    return pieces


def chunk_provision(p: Provision, max_chars: int = 1800) -> list[Chunk]:
    """Turn one provision into Chunks.

    - paragraphs = split_paragraphs(p.lines). If there are none, use [p.title].
    - Pack consecutive paragraphs into a chunk while len(joined body) <= max_chars
      (join paragraphs with "\\n"). A single paragraph longer than max_chars becomes its own
      chunk, split at sentence ends (". ") into pieces of at most max_chars where possible.
    - Chunk i: id = f"{p.id}-{i}" (i from 0), text = header_for(p) + "\\n\\n" + body,
      provision_id = p.id, kind/number/title/chapter copied from p,
      metadata = {"chunk_index": i, "n_chunks": total}.
    """
    paragraphs = split_paragraphs(p.lines) or [p.title]

    # 1. Pack paragraphs into bodies of at most max_chars
    bodies: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # Too long on its own: close the open body, then split this one at sentences
            if current:
                bodies.append(current)
                current = ""
            bodies.extend(_split_sentences(para, max_chars))
            continue

        candidate = f"{current}\n{para}" if current else para
        if len(candidate) <= max_chars:
            current = candidate  # still fits: keep packing
        else:
            bodies.append(current)  # full: close it and start a new body
            current = para
    if current:
        bodies.append(current)

    # 2. Turn each body into a Chunk with a header and metadata
    total = len(bodies)
    return [
        Chunk(
            id=f"{p.id}-{i}",
            provision_id=p.id,
            kind=p.kind,
            number=p.number,
            title=p.title,
            chapter=p.chapter,
            text=header_for(p) + "\n\n" + body,
            metadata={"chunk_index": i, "n_chunks": total},
        )
        for i, body in enumerate(bodies)
    ]

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
    # YOUR CODE
    raise NotImplementedError


def header_for(p: Provision) -> str:
    """Context header prepended to every chunk. (Given.)"""
    where = f"Article {p.number}" if p.kind == "article" else f"Annex {p.number}"
    return f"EU AI Act · {where} · {p.title}" + (f" · {p.chapter}" if p.chapter else "")


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
    # YOUR CODE
    raise NotImplementedError

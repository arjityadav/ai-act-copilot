"""PHASE 3 · Grounded answers with verifiable citations.

Read first: notes Days 59 (grounded generation & citations), 55 (RAG architecture).

The contract with the model: numbered documents in, an answer with [n] markers out. Then we
CHECK the markers in code: citing a document that doesn't exist is a hallucination signal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.llmops.prompts import get_prompt
from app.retrieval.search import hybrid_search
from app.retrieval.store import Chunk

REFUSAL = "I couldn't find this in the AI Act text I have."


@dataclass
class RagAnswer:
    answer: str
    sources: list[dict] = field(default_factory=list)     # [{"n": 1, "citation": "Article 5", "chunk_id": ..., "title": ...}]
    citations_valid: bool = True
    refused: bool = False
    prompt_version: str = ""


def build_user_message(question: str, chunks: list[Chunk]) -> str:
    """Documents first, question last (notes Day 59). Format exactly:

        <documents>
        <document n="1" citation="Article 5">
        ...chunk text...
        </document>
        <document n="2" citation="Annex III">
        ...
        </document>
        </documents>

        <question>{question}</question>

    Numbering starts at 1, in the order of `chunks`. If there are no chunks, the documents
    block is "<documents>\\n</documents>" (the model should then refuse).
    """
    # YOUR CODE
    raise NotImplementedError


def extract_citations(text: str) -> list[int]:
    """All citation numbers in order of appearance, without duplicates.
    Handles "[2]", "[1][3]" and "[1, 3]" / "[1,3]" styles. Ignore brackets without only digits/commas."""
    # YOUR CODE
    raise NotImplementedError


def citations_are_valid(text: str, n_sources: int) -> bool:
    """True if the answer is a refusal (contains REFUSAL), or if it cites at least one source and
    every cited number is between 1 and n_sources."""
    # YOUR CODE
    raise NotImplementedError


def answer_question(question: str, store, embedder, provider, k: int = 6) -> RagAnswer:
    """Retrieve -> prompt -> generate -> verify.

    - chunks = hybrid_search(question, store, embedder, k=k)
    - prompt = get_prompt("rag_answer"); result = provider.complete(
          [{"role": "user", "content": build_user_message(question, chunks)}], system=prompt.system, temperature=0.0)
    - sources: one dict per chunk: {"n": i, "citation": chunk.citation, "chunk_id": chunk.id, "title": chunk.title}
    - refused = REFUSAL in the answer; citations_valid = citations_are_valid(answer, len(chunks))
    - return RagAnswer(answer, sources, citations_valid, refused, prompt.version)
    """
    # YOUR CODE
    raise NotImplementedError

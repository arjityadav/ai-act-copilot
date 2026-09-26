"""PHASE 3 · Input guardrails.

Read first: notes Days 76 (prompt injection) and 88 (security & guardrails, OWASP LLM Top 10).

Users paste descriptions of their AI systems. That text goes into prompts, so treat it as
untrusted: limit size, flag obvious injection attempts, and redact personal data before it
reaches a model or the logs. Heuristics catch the lazy attacks; real defence comes from
least privilege and architecture (Phase 5 and 8), not from these checks alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (all |the )?(previous|prior|above)",
    r"you are now\b",
    r"system prompt",
    r"reveal (your|the) (instructions|prompt)",
    r"</?(system|instructions|document|documents)>",
]


@dataclass
class GuardResult:
    ok: bool
    reason: str = ""


def check_input(text: str, max_chars: int = 8000) -> GuardResult:
    """- empty or whitespace only        -> GuardResult(False, "empty")
    - longer than max_chars            -> GuardResult(False, "too_long")
    - matches any INJECTION_PATTERNS   -> GuardResult(False, "possible_injection")  (case-insensitive)
    - otherwise                        -> GuardResult(True)"""
    # YOUR CODE
    raise NotImplementedError


def redact_pii(text: str) -> str:
    """Replace personal data with placeholders:
    - email addresses                          -> "[EMAIL]"
    - IBANs (2 letters, 2 digits, then 11–30 letters/digits, spaces allowed, e.g. "DE89 3704 0044 0532 0130 00") -> "[IBAN]"
    - phone numbers: start with "+" or "0", then 7+ digits in total, possibly separated by spaces,
      dashes, slashes or parentheses (e.g. "+49 30 1234567", "030/123 4567") -> "[PHONE]".
      (Starting with + or 0 keeps legal references like "Regulation 2024/1689" intact.)
    Replace IBANs before phone numbers (an IBAN contains long digit runs)."""
    # YOUR CODE
    raise NotImplementedError

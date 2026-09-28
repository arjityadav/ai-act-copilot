"""Versioned prompts (given). Prompts live in prompts/*.yaml, not in code, so they can be reviewed,
diffed and evaluated like any other artifact; every LLM call logs the prompt name + version."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import yaml

PROMPT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "prompts"
)


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    system: str
    template: str = ""

    def render(self, **kwargs) -> str:
        return self.template.format(**kwargs)


@lru_cache
def get_prompt(name: str) -> Prompt:
    with open(os.path.join(PROMPT_DIR, f"{name}.yaml"), encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return Prompt(
        name=d["name"], version=str(d["version"]), system=d["system"].strip(), template=d.get("template", "")
    )

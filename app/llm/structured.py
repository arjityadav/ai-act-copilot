"""Structured output for any provider (given): JSON schema in the request, Pydantic validation, retries.

    profile = complete_structured(provider, messages, SystemProfile, system="...")
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from app.llm.provider import LLMProvider, Message


class StructuredOutputError(ValueError):
    pass


def _extract_json(text: str) -> str:
    """Models sometimes wrap JSON in ```json fences or add a sentence; take the outermost {...}."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def complete_structured(provider: LLMProvider, messages: list[Message], model_cls: type[BaseModel], *,
                        system: str | None = None, max_attempts: int = 3, temperature: float = 0.0):
    schema = model_cls.model_json_schema()
    instruction = ("\n\nRespond ONLY with a JSON object that matches this JSON schema:\n"
                   + json.dumps(schema, ensure_ascii=False))
    sys_prompt = (system or "") + instruction
    msgs = list(messages)
    last_error: Exception | None = None
    for _ in range(max_attempts):
        result = provider.complete(msgs, system=sys_prompt, json_schema=schema, temperature=temperature)
        try:
            return model_cls.model_validate_json(_extract_json(result.text))
        except ValidationError as e:
            last_error = e
            msgs = msgs + [{"role": "assistant", "content": result.text},
                           {"role": "user", "content": f"Your JSON was invalid: {e.errors()[:3]}. Return corrected JSON only."}]
    raise StructuredOutputError(f"No valid {model_cls.__name__} after {max_attempts} attempts: {last_error}")

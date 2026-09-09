"""LLM-backed New York Salsa practice-plan generation."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from server.salsa_context import SALSA_STYLE_NAME, salsa_style_context

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
OPENAI_MODEL = "gpt-4o-mini"

PRACTICE_SYSTEM_PROMPT = f"""\
You are a precise dance-practice coach for {SALSA_STYLE_NAME}.

{salsa_style_context()}

Build one executable practice session from the student's request and supplied
evidence. Use the latest instructor cues and weak-skill evidence instead of
inventing generic choreography. Keep every drill physically concrete: counts,
foot, direction, repetitions or elapsed time, and a visible success check.
Assume solo/air-partner practice unless the request explicitly says a partner
is available. Treat the supplied class evidence as authoritative for the
specific technique mechanics. Do not invent angles, foot placements, count
timing, or quoted cues that the evidence does not support; when the evidence
does not specify a detail, give a safe observation task instead of guessing.
Never convert words such as "halfway" or "fully" into degree measurements
unless that exact number appears in the supplied evidence. Do not include any
degree measurement in this plan when the evidence contains none.
The minutes assigned to the warmup, drills, and music round must add up to the
requested total.

Return ONLY valid JSON:
{{
  "title": "short plan title",
  "focus_summary": "one sentence",
  "why_today": "how this follows from the request and evidence",
  "total_minutes": 25,
  "warmup": {{
    "minutes": 4,
    "instructions": ["concrete instruction"]
  }},
  "drills": [
    {{
      "name": "drill name",
      "minutes": 6,
      "technique": "technique slug",
      "counts": "1-2-3, 5-6-7",
      "instructions": ["step-by-step instruction"],
      "success_check": "observable pass condition"
    }}
  ],
  "music_round": {{
    "minutes": 4,
    "instructions": ["how to apply the drills with New York On2 music"]
  }},
  "self_checks": ["question the student can answer after practicing"],
  "class_cues_used": ["exact or close class cue used in the plan"]
}}
"""


class PracticeLLMError(RuntimeError):
    """Raised when no configured LLM can generate a practice plan."""


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("LLM did not return a JSON object")
    return json.loads(text[start:end])


def _post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def _generate_with_anthropic(user_payload: dict) -> tuple[dict, str]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise PracticeLLMError("ANTHROPIC_API_KEY is not configured")
    payload = {
        "model": os.environ.get("PRACTICE_ANTHROPIC_MODEL", ANTHROPIC_MODEL),
        "max_tokens": 2200,
        "temperature": 0.2,
        "system": PRACTICE_SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            }
        ],
    }
    result = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        payload,
    )
    text = "".join(
        block.get("text", "")
        for block in result.get("content", [])
        if block.get("type") == "text"
    )
    return _extract_json(text), payload["model"]


def _generate_with_openai(user_payload: dict) -> tuple[dict, str]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise PracticeLLMError("OPENAI_API_KEY is not configured")
    payload = {
        "model": os.environ.get("PRACTICE_OPENAI_MODEL", OPENAI_MODEL),
        "temperature": 0.2,
        "max_tokens": 2200,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": PRACTICE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ],
    }
    result = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "authorization": f"Bearer {key}",
            "content-type": "application/json",
        },
        payload,
    )
    text = result["choices"][0]["message"]["content"]
    return _extract_json(text), payload["model"]


def _normalize_plan(plan: dict, requested_minutes: int) -> dict:
    """Keep the response shape safe and explicit for the browser."""
    normalized = dict(plan or {})
    normalized["style"] = SALSA_STYLE_NAME
    normalized["total_minutes"] = requested_minutes
    normalized.setdefault("title", "New York On2 practice")
    normalized.setdefault("focus_summary", "")
    normalized.setdefault("why_today", "")
    normalized.setdefault("warmup", {"minutes": 0, "instructions": []})
    normalized.setdefault("drills", [])
    normalized.setdefault("music_round", {"minutes": 0, "instructions": []})
    normalized.setdefault("self_checks", [])
    normalized.setdefault("class_cues_used", [])
    return normalized


def generate_practice_plan(
    student_prompt: str,
    requested_minutes: int,
    evidence: dict[str, Any],
) -> tuple[dict, str]:
    """Generate a plan with Claude first and OpenAI as a fallback."""
    user_payload = {
        "student_request": student_prompt,
        "available_minutes": requested_minutes,
        "dance_style": SALSA_STYLE_NAME,
        "evidence": evidence,
    }
    errors = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            plan, model = _generate_with_anthropic(user_payload)
            return _normalize_plan(plan, requested_minutes), model
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Claude: {exc}")

    if os.environ.get("OPENAI_API_KEY"):
        try:
            plan, model = _generate_with_openai(user_payload)
            return _normalize_plan(plan, requested_minutes), model
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OpenAI: {exc}")

    detail = "; ".join(errors) or "no LLM API key is configured"
    raise PracticeLLMError(f"Practice generation failed: {detail}")

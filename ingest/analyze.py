"""LLM analysis of class recording transcripts.

Uses Claude (Anthropic) as primary, OpenAI as fallback.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    for env_path in [ROOT / ".env.secrets", ROOT.parent / "Cooking" / ".env.secrets"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                m = re.match(r"^([A-Z_0-9]+)=(.*)$", line)
                if m and m.group(1) not in os.environ:
                    val = m.group(2).strip()
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                        val = val[1:-1]
                    os.environ[m.group(1)] = val


_load_env()


SYSTEM_PROMPT = """\
You are analyzing the transcript of a NY On2 salsa dance class.
The transcript was auto-generated from a recording with loud music,
so expect noise: repeated counting (1-2-3, 5-6-7), song lyrics, cross-talk.
Focus ONLY on the instructor's teaching content. Ignore counting reps,
filler, greetings, and class logistics (line rotation, partner switching).

Return JSON with these fields:
{
  "techniques_covered": ["basic_step", "right_turn", ...],
  "teaching_points": [
    {"technique": "slug", "tip": "actionable instruction", "context": "what the instructor was demonstrating"}
  ],
  "class_structure": [
    {"section": "name", "description": "what happened", "approx_minutes": 5}
  ],
  "key_phrases": ["quick, quick, slow", ...],
  "topics": ["timing", "footwork", ...],
  "summary": "2-3 sentence summary"
}

Rules for teaching_points:
- Write as clear, actionable instructions a student can practice
- Each tip should be ONE concrete thing to do or remember
- Tag each tip with the correct technique slug
- Extract 10-20 tips from a typical 50-minute class
- Include hand hold details, footwork patterns, timing cues, body mechanics
"""


def _analyze_anthropic(user_prompt: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], timeout=120.0
    )
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.2,
    )
    text = resp.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end]) if start >= 0 else {}


def _analyze_openai(user_prompt: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=120.0)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=4000,
    )
    return json.loads(resp.choices[0].message.content or "{}")


def analyze_class(
    transcript_text: str,
    class_date: str,
    known_techniques: list[str],
    class_number: int | None = None,
) -> dict:
    user_prompt = (
        f"Class date: {class_date}"
        + (f" (class #{class_number})" if class_number else "")
        + f"\n\nKnown techniques in our curriculum (use these slugs): {json.dumps(known_techniques)}"
        + f"\n\nFull transcript ({len(transcript_text)} chars):\n\n{transcript_text}"
    )

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _analyze_anthropic(user_prompt)
        except Exception as e:
            print(f"  Anthropic failed ({e}), trying OpenAI...")

    if os.environ.get("OPENAI_API_KEY"):
        return _analyze_openai(user_prompt)

    raise RuntimeError("No API key available (ANTHROPIC_API_KEY or OPENAI_API_KEY)")


def load_known_techniques() -> list[str]:
    tech_file = ROOT / "data" / "techniques.json"
    if not tech_file.exists():
        return []
    data = json.loads(tech_file.read_text())
    return [
        t["name"].lower().replace(" ", "_")
        for t in data.get("techniques", [])
    ]

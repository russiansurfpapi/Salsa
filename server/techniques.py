"""Technique normalization and promotion helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TECHNIQUE_ALIASES = {
    "half step": "half_step",
    "half-step": "half_step",
    "half_step": "half_step",
    "half of 1": "half_step",
    "half of one": "half_step",
    "half_of_1": "half_step",
    "half_of_one": "half_step",
    "halfway around the world": "half_step",
    "halfway_around_the_world": "half_step",
    "around the world": "around_the_world",
    "around-the-world": "around_the_world",
    "around_the_world": "around_the_world",
    "around the world basic": "around_the_world",
    "around_the_world_basic": "around_the_world",
    "circular basic": "around_the_world",
    "circular_basic": "around_the_world",
    "circular basic step": "around_the_world",
    "circular_basic_step": "around_the_world",
    "single right turn": "right_turn",
    "single_right_turn": "right_turn",
}

# Tutorial catalogs are keyed by the exact technique slug. Missing techniques
# are populated by ingest.youtube_tutorials using LLM-generated searches and
# LLM candidate ranking; do not silently substitute a parent technique.
VIDEO_KEYS: dict[str, str] = {}

DEFAULT_NAMES = {
    "around_the_world": "Around the World",
    "half_step": "Half Step",
}

DEFAULT_CATEGORIES = {
    "around_the_world": "fundamentals",
    "half_step": "fundamentals",
    "suzy_q": "footwork",
    "right_turn": "stationary_turns",
}

DEFAULT_CONTENT = {
    "around_the_world": {
        "name": "Around the World",
        "slug": "around_the_world",
        "level": 1,
        "order": 21,
        "description": "A directional variation of the On2 basic where you keep the same 1-2-3, 5-6-7 timing while rotating through clock-face positions instead of staying on one line.",
        "breakdown": [
            "Keep the normal On2 basic rhythm: step 1-2-3, hold 4, step 5-6-7, hold 8.",
            "Use counts 3 and 7 as anchors. Settle your weight before changing direction.",
            "Turn your body to the next clock position only after the anchor is stable.",
            "Keep the steps compact. The rotation comes from controlled redirection, not from traveling far across the floor.",
        ],
        "common_mistakes": [
            "Changing direction before the anchor is stable on 3 or 7.",
            "Making the basic too large and losing balance during the rotation.",
            "Treating it as a new timing instead of the same basic step redirected through space.",
        ],
        "key_details": [
            "The technique is still built from the basic step.",
            "The important skill is directional control: rotate without losing the count.",
            "Use the instructor's clock-face cues, such as 12, 9, and 6 o'clock, to know where your body should face next.",
        ],
        "flashcards": [
            {
                "question": "What stays the same during Around the World?",
                "answer": "The On2 basic timing stays the same: 1-2-3, hold 4, 5-6-7, hold 8.",
                "type": "recall",
            },
            {
                "question": "Which counts anchor the Around the World direction changes?",
                "answer": "Counts 3 and 7.",
                "type": "recall",
            },
        ],
        "class_tips": [
            "Practice the basic step around the world by moving through all directional angles.",
            "Anchor counts 3 and 7 before redirecting to the next clock-face position.",
        ],
        "connects_to": ["basic_step", "half_step", "suzy_q"],
        "video_keys": ["around_the_world"],
    },
    "half_step": {
        "name": "Half Step",
        "slug": "half_step",
        "level": 1,
        "order": 22,
        "description": "A shortened Around the World transition where you take only half of the full directional change before anchoring and redirecting into the next phrase.",
        "breakdown": [
            "Start from the same compact basic or circular basic base.",
            "Take only the first half of the Around the World direction change.",
            "Anchor clearly before continuing. Do not let the half transition drift into the next count.",
            "Use the half-step as a connector, not as a separate timing system.",
        ],
        "common_mistakes": [
            "Skipping the anchor after the half direction change.",
            "Counting it like a brand-new step instead of a shortened transition.",
            "Over-rotating and accidentally doing the full Around the World.",
        ],
        "key_details": [
            "This is a transition skill attached to Around the World and the basic step.",
            "The useful practice target is control: stop halfway, anchor, then continue on count.",
            "If the count gets unstable, return to basic step first, then add the half transition again.",
        ],
        "flashcards": [
            {
                "question": "Is Half Step a new timing or a shortened transition?",
                "answer": "A shortened transition. Keep the On2 timing and anchor before continuing.",
                "type": "recall",
            },
            {
                "question": "What should you do immediately after the half direction change?",
                "answer": "Anchor your weight before redirecting into the next movement.",
                "type": "recall",
            },
        ],
        "class_tips": [
            "Treat the half-step as half of the Around the World direction change, then anchor before continuing.",
            "Practice stopping the rotation halfway without losing the On2 count.",
        ],
        "connects_to": ["basic_step", "around_the_world", "suzy_q"],
        "video_keys": ["half_step"],
    },
    "suzy_q": {
        "name": "Suzy Q",
        "slug": "suzy_q",
        "level": 1,
        "order": 6,
        "description": "A salsa shine built from a cross-step-cross rhythm. You cross one foot in front, take a small side step, then replace/cross again while keeping the upper body quiet and the weight transfers clear.",
        "breakdown": [
            "Start with knees soft and weight centered on the balls of your feet.",
            "Cross one foot in front of the other and fully transfer weight.",
            "Take a small side step to reset the base without drifting too wide.",
            "Cross again cleanly, keeping the crossing foot in front and the rhythm even.",
            "Repeat to the other side, keeping the action compact and grounded.",
        ],
        "common_mistakes": [
            "Letting the side step get too large, which makes the shine hard to reverse.",
            "Crossing behind instead of in front.",
            "Twisting the shoulders instead of letting the hip action come from the weight transfer.",
            "Rushing the three weight changes so the pattern becomes muddy.",
        ],
        "key_details": [
            "The useful verbal pattern is cross, step, cross.",
            "Keep each weight change complete; do not stay split-weight between feet.",
            "The back foot stays close behind the front foot so the pattern can reverse quickly.",
            "Hip styling should come naturally from the crosses, not from forcing the upper body.",
        ],
        "flashcards": [
            {
                "question": "What is the basic Suzy Q footwork pattern?",
                "answer": "Cross, step, cross.",
                "type": "recall",
            },
            {
                "question": "In Suzy Q, should the crossing foot go in front or behind?",
                "answer": "In front.",
                "type": "recall",
            },
            {
                "question": "What common Suzy Q mistake makes the movement hard to reverse?",
                "answer": "Taking the side step too wide.",
                "type": "recall",
            },
        ],
        "class_tips": [
            "Execute the Suzy Q as cross, step, cross with three clear weight changes.",
            "Keep the side step small and cross in front cleanly.",
        ],
        "connects_to": ["basic_step", "around_the_world", "half_step"],
        "video_keys": ["suzy_q"],
    },
}


def _clean_slug(value: str) -> str:
    text = value.strip().lower()
    chunks: list[str] = []
    current: list[str] = []
    for ch in text:
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                chunks.append("".join(current))
                current = []
    if current:
        chunks.append("".join(current))
    return "_".join(chunks)


def normalize_technique_slug(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if raw in TECHNIQUE_ALIASES:
        return TECHNIQUE_ALIASES[raw]
    cleaned = _clean_slug(raw)
    return TECHNIQUE_ALIASES.get(cleaned, cleaned)


def canonicalize_techniques(techniques: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for tech in techniques:
        slug = normalize_technique_slug(tech)
        if slug and slug not in seen:
            result.append(slug)
            seen.add(slug)
    return result


def video_key_for_technique(slug: str) -> str:
    normalized = normalize_technique_slug(slug)
    return VIDEO_KEYS.get(normalized, normalized)


def display_name_for_slug(slug: str, techniques_json: dict[str, Any] | None = None) -> str:
    normalized = normalize_technique_slug(slug)
    if techniques_json:
        for tech in techniques_json.get("techniques", []):
            if normalize_technique_slug(tech.get("name", "")) == normalized:
                return tech.get("name", DEFAULT_NAMES.get(normalized, normalized.replace("_", " ").title()))
    return DEFAULT_NAMES.get(normalized, normalized.replace("_", " ").title())


def normalize_teaching_points(teaching_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for point in teaching_points:
        item = dict(point)
        item["technique"] = normalize_technique_slug(str(item.get("technique", "")))
        normalized.append(item)
    return normalized


def normalize_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    result = dict(analysis or {})
    result["techniques_covered"] = canonicalize_techniques(result.get("techniques_covered", []))
    result["teaching_points"] = normalize_teaching_points(result.get("teaching_points", []))
    return result


def normalize_study_guide(guide: dict[str, Any]) -> dict[str, Any]:
    techniques = []
    seen: set[str] = set()
    for tech in guide.get("techniques", []):
        item = dict(tech)
        slug = normalize_technique_slug(str(item.get("slug") or item.get("name") or ""))
        if not slug:
            continue
        item["slug"] = slug
        item.setdefault("name", display_name_for_slug(slug))
        if slug in DEFAULT_NAMES and item["name"].replace(" ", "_").lower() == slug:
            item["name"] = DEFAULT_NAMES[slug]
        if slug not in seen:
            techniques.append(item)
            seen.add(slug)
    guide["techniques"] = techniques
    return guide


def default_technique_content(slug: str, name: str | None = None, class_tips: list[str] | None = None) -> dict[str, Any]:
    normalized = normalize_technique_slug(slug)
    if normalized in DEFAULT_CONTENT:
        content = json.loads(json.dumps(DEFAULT_CONTENT[normalized]))
    else:
        display_name = name or display_name_for_slug(normalized)
        content = {
            "name": display_name,
            "slug": normalized,
            "level": 1,
            "order": 99,
            "description": f"{display_name} was detected in a class upload. This page collects class tips, lesson images, drills, and related videos as they are added.",
            "breakdown": [],
            "common_mistakes": [],
            "key_details": [],
            "flashcards": [],
            "class_tips": [],
            "connects_to": ["basic_step"],
            "video_keys": [video_key_for_technique(normalized)],
        }
    if name:
        content["name"] = name
    if class_tips:
        existing = content.setdefault("class_tips", [])
        for tip in class_tips:
            if tip and tip not in existing:
                existing.append(tip)
    return content


def promote_detected_techniques(
    data_dir: Path,
    techniques: list[str],
    teaching_points: list[dict[str, Any]] | None = None,
    names: dict[str, str] | None = None,
) -> list[str]:
    normalized = canonicalize_techniques(techniques)
    if not normalized:
        return []

    names = names or {}
    teaching_points = normalize_teaching_points(teaching_points or [])
    tips_by_slug: dict[str, list[str]] = {}
    for point in teaching_points:
        slug = point.get("technique", "")
        tip = point.get("tip", "")
        if slug and tip:
            tips_by_slug.setdefault(slug, []).append(tip)

    techniques_file = data_dir / "techniques.json"
    if techniques_file.exists():
        techniques_json = json.loads(techniques_file.read_text())
        existing = {
            normalize_technique_slug(t.get("name", "")): t
            for t in techniques_json.get("techniques", [])
        }
        next_id = max([t.get("id", 0) for t in techniques_json.get("techniques", [])] or [0]) + 1
        for slug in normalized:
            if slug in existing:
                continue
            techniques_json.setdefault("techniques", []).append({
                "id": next_id,
                "name": names.get(slug, display_name_for_slug(slug)),
                "category": DEFAULT_CATEGORIES.get(slug, "lesson_techniques"),
                "description": default_technique_content(slug, names.get(slug)).get("description", ""),
            })
            next_id += 1
        techniques_file.write_text(json.dumps(techniques_json, indent=2))

    content_file = data_dir / "technique_content.json"
    if content_file.exists():
        content_json = json.loads(content_file.read_text())
        content = content_json.get("techniques", content_json)
        for slug in normalized:
            if slug not in content:
                content[slug] = default_technique_content(slug, names.get(slug), tips_by_slug.get(slug, []))
            else:
                class_tips = content[slug].setdefault("class_tips", [])
                for tip in tips_by_slug.get(slug, []):
                    if tip not in class_tips:
                        class_tips.append(tip)
        content_file.write_text(json.dumps(content_json, indent=2))

    sub_skills_file = data_dir / "sub_skills.json"
    if sub_skills_file.exists():
        sub_skills = json.loads(sub_skills_file.read_text())
        for slug in normalized:
            if slug in sub_skills:
                continue
            sub_skills[slug] = [{
                "id": "class_notes",
                "name": "Class Notes",
                "description": "Technique was detected from a lesson upload. Rate this after reviewing the class notes and lesson frames.",
                "drill_template": "Review the class page, pick one instructor cue, and drill it slowly for 5 minutes before adding music.",
                "video_focus": video_key_for_technique(slug),
            }]
        sub_skills_file.write_text(json.dumps(sub_skills, indent=2))

    return normalized

"""Normalize and centralize class-video lecture breakdowns."""
from __future__ import annotations

import copy
import re
from collections import defaultdict
from typing import Any


TECHNIQUE_NAMES = {
    "around_the_world": "Around the World",
    "basic_step": "Basic Step",
    "cross_body_lead": "Cross Body Lead",
    "half_step": "Half Step",
    "inside_turn": "Inside Turn",
    "prep_step": "Prep Step",
    "right_turn": "Right Turn",
    "side_to_side": "Side to Side",
    "suzy_q": "Suzy Q",
    "transition_basic": "Transition Basic",
    "general": "Class Context",
}

_ALIASES = {
    "around_the_world": ("around_the_world", "circular_arc", "full_circle", "6_o_clock_arc"),
    "basic_step": ("basic_step", "partner_basic"),
    "cross_body_lead": ("cross_body_lead",),
    "half_step": ("half_step",),
    "inside_turn": ("inside_turn", "left_turn"),
    "prep_step": ("prep_step",),
    "right_turn": ("right_turn",),
    "side_to_side": ("side_to_side", "side_step"),
    "suzy_q": ("suzy_q",),
    "transition_basic": ("transition_basic", "transition_back_to_basic"),
}


def _searchable(value: str) -> str:
    value = value.lower().replace("—", "_").replace("–", "_")
    value = value.replace("o'clock", "o_clock")
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def _ordered_direct_tags(text: str) -> list[str]:
    matches: list[tuple[int, int, str]] = []
    for technique, aliases in _ALIASES.items():
        for alias in aliases:
            position = text.find(alias)
            if position >= 0:
                matches.append((position, -len(alias), technique))
                break
    matches.sort()
    result: list[str] = []
    for _, _, technique in matches:
        if technique not in result:
            result.append(technique)
    return result


def normalize_video_part(
    part: dict[str, Any],
    class_techniques: list[str] | None = None,
) -> dict[str, Any]:
    """Attach canonical technique tags to one video-breakdown part.

    The original descriptive label is preserved as ``technique_label`` while
    ``technique`` becomes the primary canonical slug and ``techniques`` holds
    every technique visible in a transition or combined sequence.
    """
    normalized = dict(part)
    original_label = str(
        part.get("technique_label")
        or part.get("technique")
        or part.get("move")
        or ""
    )
    label = _searchable(original_label)
    tags = _ordered_direct_tags(label)
    for existing_tag in part.get("techniques", []):
        if existing_tag in TECHNIQUE_NAMES and existing_tag != "general":
            tags.append(existing_tag)

    # Descriptive labels from older analyses did not always contain a canonical
    # technique name. These rules map the recorded segment meaning without
    # discarding the human-readable label.
    if "quarter_beats" in label:
        tags.append("suzy_q")
    if any(token in label for token in ("post_turn", "turn_around", "card_out")):
        tags.append("inside_turn")
    if label in {"combo_around"}:
        tags.append("around_the_world")
    if "anchor" in label:
        tags.append("basic_step")
    if "hands_in_air" in label:
        tags.append("suzy_q")
    if any(token in label for token in ("starting_position", "open_hold_reset", "final_position")):
        tags.append("basic_step")

    # If the label is phase-level rather than move-level, use the actual part
    # description to recover the named moves present in that part.
    if not tags or any(token in label for token in ("full_speed", "sequence_repeat", "closing_pass")):
        detail = _searchable(
            " ".join(
                str(part.get(field, ""))
                for field in ("instruction", "instructor_tip", "position")
            )
        )
        for technique in _ordered_direct_tags(detail):
            tags.append(technique)
        if "quarter_beats" in detail:
            tags.append("suzy_q")
        if "left_turn" in detail:
            tags.append("inside_turn")

    # Connection/setup parts belong to the immediately named class pattern when
    # possible. Otherwise retain an explicit general tag instead of pretending
    # that a technique was visible.
    available = set(class_techniques or [])
    if not tags and any(token in label for token in ("partner_connection", "establishing_connection")):
        if "cross_body_lead" in available:
            tags.append("cross_body_lead")
        elif "basic_step" in available:
            tags.append("basic_step")

    deduped: list[str] = []
    for tag in tags:
        if tag in TECHNIQUE_NAMES and tag not in deduped:
            deduped.append(tag)
    if not deduped:
        deduped = ["general"]

    normalized["technique_label"] = original_label or TECHNIQUE_NAMES[deduped[0]]
    normalized["technique"] = deduped[0]
    normalized["techniques"] = deduped
    return normalized


def tag_video_breakdowns(
    breakdowns: dict[str, Any],
    class_notes: list[dict[str, Any]] | None = None,
    study_guides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a copy with canonical tags on every lecture and part."""
    tagged = copy.deepcopy(breakdowns)
    techniques_by_date: dict[str, list[str]] = {}
    for note in class_notes or []:
        techniques_by_date[note.get("class_date", "")] = [
            technique
            for technique in note.get("techniques_covered", [])
            if isinstance(technique, str)
        ]
    techniques_by_frame: dict[tuple[str, str], list[str]] = defaultdict(list)
    for class_date, guide in (study_guides or {}).items():
        for technique in guide.get("techniques", []):
            slug = str(technique.get("slug", "")).lower().replace(" ", "_")
            if slug not in TECHNIQUE_NAMES:
                continue
            for frame in technique.get("frames", []):
                filename = frame.get("frame", "")
                key = (class_date, filename)
                if filename and slug not in techniques_by_frame[key]:
                    techniques_by_frame[key].append(slug)

    for lecture_id, entry in tagged.items():
        if not isinstance(entry, dict) or not entry.get("video_breakdown"):
            continue
        lecture = entry["video_breakdown"]
        class_techniques = techniques_by_date.get(lecture.get("class_date", ""), [])
        parts = []
        for part in lecture.get("steps", []):
            if not isinstance(part, dict):
                continue
            normalized = normalize_video_part(part, class_techniques)
            frame_tags = techniques_by_frame.get(
                (lecture.get("class_date", ""), normalized.get("frame", "")),
                [],
            )
            tags = [
                tag
                for tag in normalized.get("techniques", [])
                if tag != "general" or not frame_tags
            ]
            for tag in frame_tags:
                if tag not in tags:
                    tags.append(tag)
            normalized["techniques"] = tags or ["general"]
            normalized["technique"] = normalized["techniques"][0]
            parts.append(normalized)
        # Closing/stop frames often contain no new motion name. Keep them with
        # the immediately preceding demonstrated technique(s) so every saved
        # part remains reachable from the technique that produced that state.
        previous_tags: list[str] = []
        for part in parts:
            if part["techniques"] == ["general"] and previous_tags:
                part["techniques"] = list(previous_tags)
                part["technique"] = previous_tags[0]
            if part["techniques"] != ["general"]:
                previous_tags = list(part["techniques"])
        # Opening setup frames belong to the first demonstrated movement. Walk
        # backward once so a lecture never strands its ready position under a
        # meaningless "general" filter.
        next_tags: list[str] = []
        for part in reversed(parts):
            if part["techniques"] == ["general"] and next_tags:
                part["techniques"] = list(next_tags)
                part["technique"] = next_tags[0]
            if part["techniques"] != ["general"]:
                next_tags = list(part["techniques"])
        lecture_techniques: list[str] = []
        for part in parts:
            for technique in part["techniques"]:
                if technique != "general" and technique not in lecture_techniques:
                    lecture_techniques.append(technique)
        lecture["lecture_id"] = lecture_id
        lecture["techniques"] = lecture_techniques
        lecture["steps"] = parts
    return tagged


def build_video_lecture_library(
    breakdowns: dict[str, Any],
    study_guides: dict[str, Any] | None = None,
    class_notes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the centralized, filterable class-video lecture index."""
    tagged = tag_video_breakdowns(breakdowns, class_notes, study_guides)
    guides = study_guides or {}
    notes_by_date = {
        note.get("class_date", ""): note
        for note in class_notes or []
        if isinstance(note, dict)
    }
    parts_by_technique: dict[str, list[dict[str, Any]]] = defaultdict(list)
    lecture_ids_by_technique: dict[str, set[str]] = defaultdict(set)
    lectures: list[dict[str, Any]] = []

    for lecture_id, entry in tagged.items():
        video = entry.get("video_breakdown") if isinstance(entry, dict) else None
        if not video:
            continue
        class_date = video.get("class_date", "")
        guide = guides.get(class_date, {})
        note = notes_by_date.get(class_date, {})
        frame_slug = video.get("frame_slug") or guide.get("video_slug", "")
        parts: list[dict[str, Any]] = []
        for index, raw_part in enumerate(video.get("steps", []), start=1):
            part_number = raw_part.get("step_number") or index
            part_id = f"{lecture_id}-part-{part_number}"
            part = {
                **raw_part,
                "id": part_id,
                "part_number": part_number,
                "lecture_id": lecture_id,
                "class_date": class_date,
                "class_number": note.get("class_number") or guide.get("class_number"),
                "frame_url": (
                    f"/api/frames/{frame_slug}/{raw_part.get('frame')}"
                    if frame_slug and raw_part.get("frame")
                    else ""
                ),
            }
            parts.append(part)
            for technique in part.get("techniques", []):
                if technique == "general":
                    continue
                parts_by_technique[technique].append(part)
                lecture_ids_by_technique[technique].add(lecture_id)

        lectures.append(
            {
                "id": lecture_id,
                "title": guide.get("title") or f"Class video — {class_date}",
                "subtitle": guide.get("subtitle", ""),
                "class_date": class_date,
                "class_number": note.get("class_number") or guide.get("class_number"),
                "source_video": video.get("source", ""),
                "frame_slug": frame_slug,
                "description": video.get("description", ""),
                "techniques": video.get("techniques", []),
                "part_count": len(parts),
                "parts": parts,
            }
        )

    lectures.sort(key=lambda lecture: (lecture.get("class_date", ""), lecture.get("id", "")), reverse=True)
    technique_index = []
    for technique, parts in parts_by_technique.items():
        technique_index.append(
            {
                "slug": technique,
                "name": TECHNIQUE_NAMES.get(technique, technique.replace("_", " ").title()),
                "part_count": len(parts),
                "lecture_count": len(lecture_ids_by_technique[technique]),
            }
        )
    technique_index.sort(key=lambda item: item["name"])

    return {
        "source": "Centralized NYC Salsa class-video breakdowns",
        "lecture_count": len(lectures),
        "part_count": sum(lecture["part_count"] for lecture in lectures),
        "techniques": technique_index,
        "lectures": lectures,
    }


def video_parts_for_technique(
    library: dict[str, Any],
    technique: str,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Return newest tagged parts for one practice/technique."""
    matches: list[dict[str, Any]] = []
    for lecture in library.get("lectures", []):
        for part in lecture.get("parts", []):
            if technique not in part.get("techniques", []):
                continue
            matches.append(
                {
                    **part,
                    "lecture_title": lecture.get("title", ""),
                    "source_video": lecture.get("source_video", ""),
                }
            )
            if len(matches) >= limit:
                return matches
    return matches

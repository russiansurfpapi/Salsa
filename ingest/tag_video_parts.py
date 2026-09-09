"""Backfill canonical technique tags on all saved class-video parts.

Usage:
    python -m ingest.tag_video_parts
"""
from __future__ import annotations

import json
from pathlib import Path

from server.video_lectures import tag_video_breakdowns


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main() -> None:
    breakdown_path = DATA / "technique_breakdowns.json"
    notes_path = DATA / "class_notes.json"
    guides_path = DATA / "study_guides.json"
    breakdowns = json.loads(breakdown_path.read_text()) if breakdown_path.exists() else {}
    class_notes = json.loads(notes_path.read_text()) if notes_path.exists() else []
    study_guides = json.loads(guides_path.read_text()) if guides_path.exists() else {}
    tagged = tag_video_breakdowns(breakdowns, class_notes, study_guides)
    breakdown_path.write_text(json.dumps(tagged, indent=2) + "\n")

    lecture_count = 0
    part_count = 0
    for entry in tagged.values():
        lecture = entry.get("video_breakdown") if isinstance(entry, dict) else None
        if not lecture:
            continue
        lecture_count += 1
        part_count += len(lecture.get("steps", []))
    print(f"Tagged {part_count} parts across {lecture_count} class-video lectures.")


if __name__ == "__main__":
    main()

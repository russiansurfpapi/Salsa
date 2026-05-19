"""Class recording ingest pipeline.

Usage:
  python -m ingest.pipeline ~/Desktop/Salsa518.m4a --date 2026-05-18 --class-number 2
  python -m ingest.pipeline                        # process all new .m4a in videos/
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ingest.transcribe import (
    TRANSCRIPTS,
    VIDEOS,
    extract_frames,
    generate_bullets,
    section_transcript,
    slugify,
    transcribe_video,
    update_transcript_steps,
    FRAMES,
)
from ingest.analyze import analyze_class, load_known_techniques

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _ingest_one(audio_path: Path, class_date: str, class_number: int | None) -> dict:
    slug = slugify(audio_path.stem)
    transcript_file = TRANSCRIPTS / f"{slug}.json"

    # Step 1: Transcribe (whisper-large for class recordings)
    if transcript_file.exists():
        print(f"  Transcript exists: {transcript_file.name}")
        t = json.loads(transcript_file.read_text())
    else:
        print(f"  Transcribing with whisper-large...")
        result = transcribe_video(audio_path, model="whisper-large")
        alt = result["results"]["channels"][0]["alternatives"][0]
        sections = section_transcript(result)
        t = {
            "text": alt.get("transcript", ""),
            "duration": result.get("metadata", {}).get("duration", 0),
            "words": alt.get("words", []),
            "sections": sections,
        }
        transcript_file.write_text(json.dumps(t, indent=2))
        print(f"    {len(sections)} sections, {len(t['text'])} chars")

        # Extract frames if source is video
        if audio_path.suffix == ".mp4":
            frame_dir = FRAMES / slug
            extract_frames(audio_path, sections, frame_dir)

        # Generate bullets
        if t["text"] and len(t["text"]) > 100:
            bullets = generate_bullets(sections)
            update_transcript_steps(slug, bullets)
            print(f"    {sum(len(b) for b in bullets)} bullets")

    # Step 2: LLM analysis
    print(f"  Analyzing with gpt-4o-mini...")
    known = load_known_techniques()
    analysis = analyze_class(t["text"], class_date, known, class_number)
    print(f"    {len(analysis.get('teaching_points', []))} teaching points extracted")
    print(f"    Techniques: {analysis.get('techniques_covered', [])}")

    # Step 3: Store to MongoDB
    print(f"  Saving to MongoDB...")
    from server.mongo import classes, class_tips

    doc = {
        "class_date": class_date,
        "class_number": class_number,
        "transcript_file": f"{slug}.json",
        "transcript_text": t["text"],
        "duration": t.get("duration", 0),
        "techniques_covered": analysis.get("techniques_covered", []),
        "teaching_points": analysis.get("teaching_points", []),
        "class_structure": analysis.get("class_structure", []),
        "key_phrases": analysis.get("key_phrases", []),
        "topics": analysis.get("topics", []),
        "summary": analysis.get("summary", ""),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-4o-mini",
    }

    classes().update_one(
        {"class_date": class_date},
        {"$set": doc},
        upsert=True,
    )
    print(f"    Saved class doc for {class_date}")

    # Denormalize tips per technique
    tips_coll = class_tips()
    tips_coll.delete_many({"class_date": class_date})
    tip_docs = []
    for tp in analysis.get("teaching_points", []):
        tip_docs.append({
            "technique": tp.get("technique", ""),
            "tip": tp.get("tip", ""),
            "context": tp.get("context", ""),
            "class_date": class_date,
            "class_number": class_number,
        })
    if tip_docs:
        tips_coll.insert_many(tip_docs)
        print(f"    Inserted {len(tip_docs)} tips")

    # Step 4: Update JSON files (backward compat)
    _update_class_notes_json(doc)
    _update_technique_content_json(analysis.get("teaching_points", []))

    return doc


def _update_class_notes_json(doc: dict) -> None:
    notes_file = DATA / "class_notes.json"
    existing = json.loads(notes_file.read_text()) if notes_file.exists() else []
    existing = [n for n in existing if n.get("class_date") != doc["class_date"]]
    existing.append({
        "class_date": doc["class_date"],
        "class_number": doc["class_number"],
        "transcript_file": doc["transcript_file"],
        "matched_techniques": [
            {"name": t.replace("_", " ").title(), "slug": t}
            for t in doc.get("techniques_covered", [])
        ],
        "topics": doc.get("topics", []),
        "extracted_tips": [tp["tip"] for tp in doc.get("teaching_points", [])],
        "summary": doc.get("summary", ""),
        "key_phrases": doc.get("key_phrases", []),
    })
    notes_file.write_text(json.dumps(existing, indent=2))


def _update_technique_content_json(teaching_points: list[dict]) -> None:
    tc_file = DATA / "technique_content.json"
    if not tc_file.exists():
        return
    tc = json.loads(tc_file.read_text())
    techs = tc.get("techniques", tc)

    by_technique: dict[str, list[str]] = {}
    for tp in teaching_points:
        slug = tp.get("technique", "")
        if slug and slug in techs:
            by_technique.setdefault(slug, []).append(tp["tip"])

    for slug, tips in by_technique.items():
        techs[slug]["class_tips"] = tips

    tc_file.write_text(json.dumps(tc, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Ingest a salsa class recording")
    parser.add_argument("audio", nargs="?", help="Path to .m4a class recording")
    parser.add_argument("--date", help="Class date (YYYY-MM-DD)")
    parser.add_argument("--class-number", type=int, help="Class number")
    args = parser.parse_args()

    if args.audio:
        audio_path = Path(args.audio).resolve()
        if not audio_path.exists():
            print(f"ERROR: {audio_path} not found")
            return
        # Copy to videos/ if not already there
        dest = VIDEOS / audio_path.name
        if not dest.exists():
            shutil.copy2(audio_path, dest)
            print(f"Copied to {dest}")
        class_date = args.date or datetime.now().strftime("%Y-%m-%d")
        _ingest_one(dest, class_date, args.class_number)
    else:
        # Process all standalone .m4a files in videos/
        mp4_stems = {f.stem for f in VIDEOS.glob("*.mp4")}
        recordings = sorted(
            f for f in VIDEOS.glob("*.m4a") if f.stem not in mp4_stems
        )
        if not recordings:
            print("No new class recordings found in videos/")
            return
        for rec in recordings:
            slug = slugify(rec.stem)
            from server.mongo import classes as classes_coll
            existing = classes_coll().find_one({"transcript_file": f"{slug}.json"})
            if existing:
                print(f"SKIP (already in MongoDB): {rec.name}")
                continue
            date = args.date or datetime.now().strftime("%Y-%m-%d")
            print(f"\nProcessing: {rec.name}")
            _ingest_one(rec, date, args.class_number)

    print("\nDone.")


if __name__ == "__main__":
    main()

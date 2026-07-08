"""Background ingest worker for cloud uploads.

Wraps the existing ingest pipelines to run in background threads
with status tracking.
"""
from __future__ import annotations

import base64
import json
import shutil
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _update(job_id: str, **kwargs):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def get_job(job_id: str) -> Optional[dict]:
    with _lock:
        return _jobs.get(job_id, {}).copy() if job_id in _jobs else None


def _run_audio(job_id: str, audio_path: Path, class_date: str, class_number: Optional[int]):
    _update(job_id, step="transcribing audio")

    from ingest.transcribe import (
        TRANSCRIPTS, slugify, transcribe_video,
        section_transcript, generate_bullets, update_transcript_steps,
    )
    from ingest.analyze import analyze_class, load_known_techniques

    slug = slugify(audio_path.stem)
    transcript_file = TRANSCRIPTS / f"{slug}.json"

    if transcript_file.exists():
        t = json.loads(transcript_file.read_text())
    else:
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

        if t["text"] and len(t["text"]) > 100:
            bullets = generate_bullets(sections)
            update_transcript_steps(slug, bullets)

    _update(job_id, step="analyzing transcript")
    known = load_known_techniques()
    analysis = analyze_class(t["text"], class_date, known, class_number)

    _update(job_id, step="saving to database")
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
        "model": "claude-haiku-4-5",
    }

    classes().update_one({"class_date": class_date}, {"$set": doc}, upsert=True)

    tips_coll = class_tips()
    tips_coll.delete_many({"class_date": class_date})
    tip_docs = [
        {
            "technique": tp.get("technique", ""),
            "tip": tp.get("tip", ""),
            "context": tp.get("context", ""),
            "class_date": class_date,
            "class_number": class_number,
        }
        for tp in analysis.get("teaching_points", [])
    ]
    if tip_docs:
        tips_coll.insert_many(tip_docs)

    from ingest.pipeline import _update_class_notes_json, _update_technique_content_json
    _update_class_notes_json(doc)
    _update_technique_content_json(analysis.get("teaching_points", []))


def _run_video(job_id: str, video_path: Path, class_date: str, class_number: Optional[int]):
    _update(job_id, step="extracting frames")

    from ingest.video_study import (
        extract_dense_frames, get_duration,
        analyze_frames_with_claude, save_study_guide,
        update_breakdowns, update_mongo,
    )
    from ingest.transcribe import (
        TRANSCRIPTS, slugify, transcribe_video, section_transcript,
    )

    slug = slugify(video_path.stem)
    frame_dir = DATA / "frames" / slug

    duration = get_duration(video_path)
    fps = 1.0 if duration < 60 else 0.5
    if not list(frame_dir.glob("frame_*.jpg")):
        frame_dir.mkdir(parents=True, exist_ok=True)
        extract_dense_frames(video_path, frame_dir, fps)

    _update(job_id, step="transcribing video audio")
    transcript_file = TRANSCRIPTS / f"{slug}.json"
    if transcript_file.exists():
        t = json.loads(transcript_file.read_text())
    else:
        result = transcribe_video(video_path, model="whisper-large")
        alt = result["results"]["channels"][0]["alternatives"][0]
        sections = section_transcript(result)
        t = {
            "text": alt.get("transcript", ""),
            "duration": result.get("metadata", {}).get("duration", 0),
            "words": alt.get("words", []),
            "sections": sections,
        }
        transcript_file.write_text(json.dumps(t, indent=2))

    _update(job_id, step="analyzing frames with Claude Vision")
    from server.mongo import classes as classes_coll

    class_doc = classes_coll().find_one(
        {"class_date": class_date},
        {"_id": 0, "words": 0, "transcript_text": 0},
    )
    if not class_doc:
        class_doc = {"teaching_points": [], "techniques_covered": [], "key_phrases": []}

    videos_data = json.loads((DATA / "videos.json").read_text()) if (DATA / "videos.json").exists() else {}

    guide = analyze_frames_with_claude(
        frame_dir=frame_dir,
        frame_slug=slug,
        transcript_text=t.get("text", ""),
        teaching_points=class_doc.get("teaching_points", []),
        techniques_covered=class_doc.get("techniques_covered", []),
        key_phrases=class_doc.get("key_phrases", []),
        videos_data=videos_data,
        class_date=class_date,
        class_number=class_number,
    )

    _update(job_id, step="saving study guide")
    save_study_guide(guide, class_date, class_number, slug)
    update_breakdowns(guide, slug, class_date, video_path.name)
    update_mongo(class_date, video_path.name, slug)

    # Store referenced frames in MongoDB so they survive without disk
    _update(job_id, step="storing key frames")
    _store_frames_in_mongo(guide, frame_dir, slug)


def _store_frames_in_mongo(guide: dict, frame_dir: Path, slug: str):
    """Store frames referenced in the study guide into MongoDB."""
    from server.mongo import frames as frames_coll

    referenced = set()
    for tech in guide.get("techniques", []):
        for f in tech.get("frames", []):
            referenced.add(f.get("frame", ""))
    for kf in guide.get("key_frames", []):
        referenced.add(kf.get("frame", ""))
    for phase in guide.get("choreography", {}).get("phases", []):
        for step in phase.get("steps", []):
            referenced.add(step.get("frame", ""))
    referenced.discard("")

    coll = frames_coll()
    for fname in referenced:
        fpath = frame_dir / fname
        if not fpath.exists():
            continue
        b64 = base64.b64encode(fpath.read_bytes()).decode("ascii")
        coll.update_one(
            {"slug": slug, "filename": fname},
            {"$set": {"slug": slug, "filename": fname, "data": b64}},
            upsert=True,
        )


def _cleanup(audio_path: Optional[Path], video_path: Optional[Path]):
    """Remove uploaded files after processing."""
    for p in [audio_path, video_path]:
        if p and p.exists():
            try:
                p.unlink()
            except Exception:
                pass


def _run(job_id: str, audio_path: Optional[Path], video_path: Optional[Path],
         class_date: str, class_number: Optional[int]):
    try:
        _update(job_id, status="running")

        if audio_path:
            _run_audio(job_id, audio_path, class_date, class_number)

        if video_path:
            _run_video(job_id, video_path, class_date, class_number)

        result = {"class_date": class_date}
        if audio_path:
            result["lesson_url"] = f"/classes/{class_date}"
        if video_path:
            result["study_url"] = f"/study/{class_date}"

        _update(job_id, status="done", step="complete", result=result)

    except Exception as e:
        _update(job_id, status="error", step="failed", error=str(e))
        traceback.print_exc()
    finally:
        _cleanup(audio_path, video_path)


def start_ingest(
    audio_path: Optional[Path],
    video_path: Optional[Path],
    class_date: str,
    class_number: Optional[int],
) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "step": "waiting",
            "class_date": class_date,
            "class_number": class_number,
            "has_audio": audio_path is not None,
            "has_video": video_path is not None,
            "created": datetime.now(timezone.utc).isoformat(),
            "error": None,
            "result": None,
        }
    thread = threading.Thread(
        target=_run,
        args=(job_id, audio_path, video_path, class_date, class_number),
        daemon=True,
    )
    thread.start()
    return job_id

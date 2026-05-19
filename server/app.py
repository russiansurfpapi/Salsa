"""Salsa learning server — FastAPI backend + web UI."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import mongo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB = Path(__file__).resolve().parent / "web"
VIDEOS = ROOT / "videos"

app = FastAPI(title="Salsa Learning")

if VIDEOS.exists():
    try:
        app.mount("/video", StaticFiles(directory=VIDEOS), name="videos")
    except Exception:
        pass
_frames_dir = DATA / "frames"
if _frames_dir.exists():
    try:
        app.mount("/frames", StaticFiles(directory=_frames_dir), name="frames")
    except Exception:
        pass
if WEB.exists():
    app.mount("/web", StaticFiles(directory=WEB), name="web")


def _load_json(name: str) -> Any:
    p = DATA / name
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _save_json(name: str, data: Any) -> None:
    (DATA / name).write_text(json.dumps(data, indent=2))


# ── Pages ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/technique/{tech_id}", response_class=HTMLResponse)
def technique_page(tech_id: str) -> FileResponse:
    return FileResponse(WEB / "technique.html")


@app.get("/practice", response_class=HTMLResponse)
def practice_page() -> FileResponse:
    return FileResponse(WEB / "practice.html")


@app.get("/quiz", response_class=HTMLResponse)
def quiz_page() -> FileResponse:
    return FileResponse(WEB / "quiz.html")


# ── API: Techniques ────────────────────────────────────────────────────

@app.get("/api/techniques")
def list_techniques() -> dict:
    techniques = _load_json("techniques.json") or {}
    content = _get_content()
    progression = _load_json("progression.json") or {}

    learned = set()
    for phase in progression.get("phases", []):
        for sess in phase.get("practice_sessions", []):
            if sess.get("completed"):
                for t in phase.get("techniques", []):
                    learned.add(t)

    for t in techniques.get("techniques", []):
        slug = t["name"].lower().replace(" ", "_")
        t["slug"] = slug
        t["has_content"] = slug in content
        t["learned"] = t["name"] in learned

    return techniques


def _get_content() -> dict:
    raw = _load_json("technique_content.json") or {}
    return raw.get("techniques", raw)


@app.get("/api/technique/{slug}")
def get_technique(slug: str) -> dict:
    content = _get_content()
    if slug not in content:
        raise HTTPException(404, f"no content for {slug}")

    tech = content[slug]
    videos = _load_json("videos.json") or {}

    video_list = []
    slug_to_video_key = {
        "basic_step": "basic_step",
        "inside_turn": "inside_turn",
        "cross_body_lead": "cross_body_lead",
        "right_turn": "right_turn",
        "prep_step": "prep_step",
    }
    vkey = slug_to_video_key.get(slug, slug)
    import urllib.parse
    for v in videos.get(vkey, []):
        local_match = None
        vtitle = v.get("title", "").lower()
        best_score = 0
        for f in VIDEOS.glob("*.mp4"):
            stem = f.stem.lower()
            score = sum(1 for w in vtitle.split() if len(w) > 3 and w in stem)
            if score > best_score:
                best_score = score
                local_match = f"/video/{urllib.parse.quote(f.name)}"
        if best_score < 3:
            local_match = None
        video_list.append({**v, "local_url": local_match})

    tech["videos"] = video_list

    # Add transcript sections with frame URLs for each video
    transcripts_with_frames = []
    tdir = DATA / "transcripts"
    fdir = DATA / "frames"
    all_steps = _load_json("transcript_steps.json") or {}
    generic = {"salsa", "beginner", "lesson", "tutorial", "partnerwork", "basics"}
    for v in video_list:
        title = v.get("title", "")
        content_words = [w.lower() for w in title.split() if len(w) > 3 and w.lower() not in generic]
        best_file, best_score = None, 0
        for tf in tdir.glob("*.json"):
            score = sum(1 for w in content_words if w in tf.stem.lower())
            if score > best_score:
                best_score = score
                best_file = tf
        if best_file and best_score >= 2:
            t = json.loads(best_file.read_text())
            sections = t.get("sections", [])
            frame_slug = best_file.stem
            for i, sec in enumerate(sections):
                frame_path = fdir / frame_slug / f"section_{i}.jpg"
                sec["frame_url"] = f"/frames/{frame_slug}/section_{i}.jpg" if frame_path.exists() else None
            step_entry = all_steps.get(f"{frame_slug}.json", {})
            step_bullets = step_entry.get("steps", [])
            for i, sec in enumerate(sections):
                if i < len(step_bullets):
                    sec["steps"] = step_bullets[i]
            transcripts_with_frames.append({
                "instructor": v.get("channel", ""),
                "title": title,
                "sections": sections,
                "slug": frame_slug,
            })
    tech["transcripts"] = transcripts_with_frames

    # Add detailed breakdowns if available
    breakdowns = _load_json("technique_breakdowns.json") or {}
    if slug in breakdowns:
        tech["breakdown_detail"] = breakdowns[slug]

    return tech


# ── API: Progression ───────────────────────────────────────────────────

@app.get("/api/progression")
def get_progression() -> dict:
    return _load_json("progression.json") or {}


class PracticeCompleteReq(BaseModel):
    phase: int
    session: int
    notes: str = ""


@app.post("/api/progression/complete")
def complete_practice(req: PracticeCompleteReq) -> dict:
    prog = _load_json("progression.json") or {}
    phases = prog.get("phases", [])
    if req.phase >= len(phases):
        raise HTTPException(400, "bad phase")
    sessions = phases[req.phase].get("practice_sessions", [])
    if req.session >= len(sessions):
        raise HTTPException(400, "bad session")

    sessions[req.session]["completed"] = datetime.now(timezone.utc).isoformat()
    sessions[req.session]["notes"] = req.notes or None
    _save_json("progression.json", prog)
    return {"ok": True}


# ── API: Quiz / Flashcards ─────────────────────────────────────────────

@app.get("/api/quiz/all/cards")
def get_all_cards() -> list:
    content = _get_content()
    cards = []
    for slug, tech in content.items():
        if not isinstance(tech, dict):
            continue
        for card in tech.get("flashcards", []):
            cards.append({**card, "technique": slug, "technique_name": tech.get("name", slug)})
    return cards


@app.get("/api/quiz/{slug}")
def get_quiz(slug: str) -> dict:
    content = _get_content()
    if slug not in content:
        raise HTTPException(404, f"no content for {slug}")
    return {
        "technique": slug,
        "name": content[slug].get("name", slug),
        "flashcards": content[slug].get("flashcards", []),
    }


# ── Voice memo ingestion ───────────────────────────────────────────────

@app.get("/notes", response_class=HTMLResponse)
def notes_page() -> FileResponse:
    return FileResponse(WEB / "notes.html")


class VoiceMemoReq(BaseModel):
    transcript: str
    class_date: str = ""
    class_number: Optional[int] = None


@app.post("/api/notes/ingest")
def ingest_voice_memo(req: VoiceMemoReq) -> dict:
    techniques = _load_json("techniques.json") or {}
    content = _get_content()

    tech_names = [t["name"].lower() for t in techniques.get("techniques", [])]
    tech_lookup = {t["name"].lower(): t for t in techniques.get("techniques", [])}

    transcript_lower = req.transcript.lower()

    matched = []
    for name in tech_names:
        if name in transcript_lower:
            t = tech_lookup[name]
            matched.append({"id": t["id"], "name": t["name"], "slug": t["name"].lower().replace(" ", "_")})

    keywords = {
        "timing": ["count", "beat", "on2", "on 2", "1-2-3", "5-6-7", "rhythm", "break"],
        "footwork": ["step", "foot", "feet", "weight", "heel", "toe", "ball"],
        "frame": ["frame", "arm", "elbow", "shoulder", "hand", "grip", "hold"],
        "lead_follow": ["lead", "follow", "signal", "push", "pull", "connection", "tension"],
        "turns": ["turn", "spin", "spot", "spotting", "rotate", "pivot"],
        "posture": ["posture", "straight", "core", "hip", "center", "balance"],
    }

    topics = []
    for topic, words in keywords.items():
        if any(w in transcript_lower for w in words):
            topics.append(topic)

    sentences = [s.strip() for s in req.transcript.replace(".", "\n").replace("!", "\n").replace("?", "\n").split("\n") if s.strip()]
    tips = []
    tip_keywords = ["remember", "don't", "make sure", "important", "always", "never", "key", "trick", "tip", "mistake"]
    for s in sentences:
        if any(k in s.lower() for k in tip_keywords):
            tips.append(s.strip())

    note = {
        "class_date": req.class_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "class_number": req.class_number,
        "transcript": req.transcript,
        "matched_techniques": matched,
        "topics": topics,
        "extracted_tips": tips[:10],
    }

    notes_file = DATA / "class_notes.json"
    existing = json.loads(notes_file.read_text()) if notes_file.exists() else []
    existing.append(note)
    notes_file.write_text(json.dumps(existing, indent=2))

    return note


@app.get("/api/notes")
def get_notes() -> list:
    return _load_json("class_notes.json") or []


# ── Classes (MongoDB-backed) ──────────────────────────────────────────

@app.get("/classes", response_class=HTMLResponse)
def classes_page() -> FileResponse:
    return FileResponse(WEB / "classes.html")


@app.get("/classes/{class_date}", response_class=HTMLResponse)
def class_detail_page(class_date: str) -> FileResponse:
    return FileResponse(WEB / "classes.html")


@app.get("/api/classes")
def list_classes() -> list:
    try:
        rows = list(mongo.classes().find({}, {"_id": 0}).sort("class_date", -1))
        for r in rows:
            r.pop("transcript_text", None)
            r.pop("words", None)
            r["teaching_point_count"] = len(r.get("teaching_points", []))
        return rows
    except Exception:
        notes = _load_json("class_notes.json") or []
        return notes


@app.get("/api/classes/{class_date}")
def get_class(class_date: str) -> dict:
    try:
        doc = mongo.classes().find_one({"class_date": class_date}, {"_id": 0})
        if doc:
            return doc
    except Exception:
        pass
    notes = _load_json("class_notes.json") or []
    match = next((n for n in notes if n.get("class_date") == class_date), None)
    if not match:
        raise HTTPException(404, f"no class for {class_date}")
    return match


@app.get("/api/technique/{slug}/class-tips")
def technique_class_tips(slug: str) -> list:
    try:
        tips = list(mongo.class_tips().find(
            {"technique": slug}, {"_id": 0}
        ).sort("class_date", -1))
        return tips
    except Exception:
        content = _get_content()
        if slug in content:
            return [{"tip": t, "technique": slug} for t in content[slug].get("class_tips", [])]
        return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8788)

"""Salsa learning server — FastAPI backend + web UI."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import base64

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
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
# Frames served via /api/frames/{slug}/{filename} endpoint (disk + MongoDB fallback)
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
                sec["frame_url"] = f"/api/frames/{frame_slug}/section_{i}.jpg" if frame_path.exists() else None
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

    # If this technique has a class video breakdown, attach the combo steps
    bd = breakdowns.get(slug, {})
    class_vid = bd.get("class_video")
    if class_vid:
        combo = breakdowns.get(class_vid.get("combo_key", ""), {})
        vb = combo.get("video_breakdown", {})
        if vb:
            frame_slug = vb.get("frame_slug", "")
            steps = vb.get("steps", [])
            relevant = [s for s in steps if s.get("technique") == slug]
            for s in relevant:
                s["frame_url"] = f"/api/frames/{frame_slug}/{s['frame']}"
            tech["class_video_breakdown"] = {
                "class_date": class_vid.get("class_date", ""),
                "frame_slug": frame_slug,
                "source": vb.get("source", ""),
                "description": vb.get("description", ""),
                "steps": relevant,
                "all_steps": [{**s, "frame_url": f"/api/frames/{frame_slug}/{s['frame']}"} for s in steps],
            }

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


@app.get("/study/{class_date}", response_class=HTMLResponse)
def study_page(class_date: str) -> FileResponse:
    return FileResponse(WEB / "study.html")


@app.get("/api/study/{class_date}")
def get_study_guide(class_date: str) -> dict:
    guides = _load_json("study_guides.json") or {}
    if class_date not in guides:
        raise HTTPException(404, f"no study guide for {class_date}")
    return guides[class_date]


@app.get("/api/classes/{class_date}/video-breakdown")
def get_class_video_breakdown(class_date: str) -> list:
    breakdowns = _load_json("technique_breakdowns.json") or {}
    results = []
    for key, bd in breakdowns.items():
        vb = bd.get("video_breakdown")
        if vb and vb.get("class_date") == class_date:
            frame_slug = vb.get("frame_slug", "")
            steps = [{**s, "frame_url": f"/api/frames/{frame_slug}/{s['frame']}"} for s in vb.get("steps", [])]
            results.append({
                "key": key,
                "description": vb.get("description", ""),
                "source": vb.get("source", ""),
                "frame_slug": frame_slug,
                "steps": steps,
            })
    return results


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


# ── Skills / Sub-skill ratings ───────────────────────────────────────

@app.get("/progress", response_class=HTMLResponse)
def progress_page() -> FileResponse:
    return FileResponse(WEB / "progress.html")


def _get_sub_skills() -> dict:
    return _load_json("sub_skills.json") or {}


def _get_skill_ratings_json() -> dict:
    return _load_json("skill_ratings.json") or {"ratings": {}, "history": []}


def _save_skill_ratings_json(data: dict) -> None:
    _save_json("skill_ratings.json", data)


@app.get("/api/skills")
def list_skills() -> dict:
    taxonomy = _get_sub_skills()
    try:
        ratings = {r["skill_id"]: r for r in mongo.skill_ratings().find({}, {"_id": 0})}
    except Exception:
        sr = _get_skill_ratings_json()
        ratings = {k: {"rating": v["rating"], "notes": v.get("notes", ""), "updated_at": v.get("updated_at", "")} for k, v in sr.get("ratings", {}).items()}

    result = {}
    for tech, skills in taxonomy.items():
        sub_skills = []
        for s in skills:
            sid = f"{tech}.{s['id']}"
            r = ratings.get(sid, {})
            sub_skills.append({
                **s,
                "skill_id": sid,
                "rating": r.get("rating", 0),
                "notes": r.get("notes", ""),
                "updated_at": r.get("updated_at", ""),
            })
        rated = [s["rating"] for s in sub_skills if s["rating"] > 0]
        result[tech] = {
            "sub_skills": sub_skills,
            "avg_rating": round(sum(rated) / len(rated), 1) if rated else 0,
        }
    return {"techniques": result}


@app.get("/api/skills/weak")
def get_weak_skills() -> dict:
    taxonomy = _get_sub_skills()
    try:
        weak_docs = list(mongo.skill_ratings().find({"rating": {"$lte": 2}}, {"_id": 0}))
    except Exception:
        sr = _get_skill_ratings_json()
        weak_docs = [{"skill_id": k, "rating": v["rating"], "notes": v.get("notes", "")} for k, v in sr.get("ratings", {}).items() if v["rating"] <= 2]

    weak_skills = []
    for doc in weak_docs:
        parts = doc["skill_id"].split(".", 1)
        if len(parts) != 2:
            continue
        technique, sub_skill_id = parts
        skills = taxonomy.get(technique, [])
        match = next((s for s in skills if s["id"] == sub_skill_id), None)
        if match:
            weak_skills.append({
                "skill_id": doc["skill_id"],
                "technique": technique,
                "name": match["name"],
                "rating": doc["rating"],
                "drill": match.get("drill_template", ""),
                "video_focus": match.get("video_focus", technique),
            })

    return {"weak_skills": weak_skills}


@app.get("/api/skills/progress")
def get_skill_progress() -> dict:
    try:
        history = list(mongo.skill_rating_history().find({}, {"_id": 0}).sort("rated_at", 1))
    except Exception:
        sr = _get_skill_ratings_json()
        history = sr.get("history", [])
    return {"history": history}


@app.get("/api/skills/{technique}")
def get_skill_detail(technique: str) -> dict:
    taxonomy = _get_sub_skills()
    if technique not in taxonomy:
        raise HTTPException(404, f"no skills for {technique}")

    skills = taxonomy[technique]
    try:
        ratings = {r["skill_id"]: r for r in mongo.skill_ratings().find({"technique": technique}, {"_id": 0})}
    except Exception:
        sr = _get_skill_ratings_json()
        ratings = {k: {"rating": v["rating"], "notes": v.get("notes", ""), "updated_at": v.get("updated_at", "")} for k, v in sr.get("ratings", {}).items() if k.startswith(f"{technique}.")}

    try:
        tips = list(mongo.class_tips().find({"technique": technique}, {"_id": 0}))
    except Exception:
        tips = []

    sub_skills = []
    for s in skills:
        sid = f"{technique}.{s['id']}"
        r = ratings.get(sid, {})
        sub_skills.append({
            **s,
            "skill_id": sid,
            "rating": r.get("rating", 0),
            "notes": r.get("notes", ""),
            "updated_at": r.get("updated_at", ""),
        })

    rated = [s["rating"] for s in sub_skills if s["rating"] > 0]
    return {
        "technique": technique,
        "sub_skills": sub_skills,
        "avg_rating": round(sum(rated) / len(rated), 1) if rated else 0,
        "class_tips": tips,
    }


class SkillRating(BaseModel):
    skill_id: str
    rating: int
    notes: str = ""


class RateRequest(BaseModel):
    ratings: list[SkillRating]
    source: str = "self_assessment"


@app.post("/api/skills/rate")
def rate_skills(req: RateRequest) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    sr = _get_skill_ratings_json()

    for r in req.ratings:
        parts = r.skill_id.split(".", 1)
        if len(parts) != 2:
            continue
        technique, sub_skill = parts

        doc = {
            "skill_id": r.skill_id,
            "technique": technique,
            "sub_skill": sub_skill,
            "rating": r.rating,
            "notes": r.notes,
            "updated_at": now,
            "source": req.source,
        }

        try:
            mongo.skill_ratings().update_one(
                {"skill_id": r.skill_id}, {"$set": doc}, upsert=True,
            )
            mongo.skill_rating_history().insert_one({
                **doc, "rated_at": now,
            })
        except Exception:
            pass

        sr["ratings"][r.skill_id] = {"rating": r.rating, "notes": r.notes, "updated_at": now}
        sr["history"].append({"skill_id": r.skill_id, "rating": r.rating, "rated_at": now})

    _save_skill_ratings_json(sr)
    return {"ok": True, "updated": len(req.ratings)}


# ── Frames (MongoDB-backed for cloud, filesystem fallback) ────────────

@app.get("/api/frames/{slug}/{filename}")
def get_frame_from_db(slug: str, filename: str) -> Response:
    frame_path = DATA / "frames" / slug / filename
    if frame_path.exists():
        return FileResponse(frame_path, media_type="image/jpeg")
    try:
        doc = mongo.frames().find_one({"slug": slug, "filename": filename})
        if doc:
            data = base64.b64decode(doc["data"])
            return Response(content=data, media_type="image/jpeg")
    except Exception:
        pass
    raise HTTPException(404, "Frame not found")


# ── Upload & Cloud Ingest ─────────────────────────────────────────────

UPLOAD_PIN = os.environ.get("UPLOAD_PIN", "")
UPLOADS = ROOT / "uploads"
try:
    UPLOADS.mkdir(exist_ok=True)
except OSError:
    pass


@app.get("/upload", response_class=HTMLResponse)
def upload_page() -> FileResponse:
    return FileResponse(WEB / "upload.html")


@app.post("/api/ingest/upload")
async def ingest_upload(
    class_date: str = Form(...),
    class_number: int = Form(1),
    pin: str = Form(...),
    audio: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
) -> dict:
    if not UPLOAD_PIN or pin != UPLOAD_PIN:
        raise HTTPException(403, "Invalid PIN")

    if not audio and not video:
        raise HTTPException(400, "No file uploaded")

    audio_path = None
    video_path = None

    if audio and audio.filename:
        dest = UPLOADS / f"{class_date}_audio_{audio.filename}"
        with open(dest, "wb") as f:
            while chunk := await audio.read(1024 * 1024):
                f.write(chunk)
        audio_path = dest

    if video and video.filename:
        dest = UPLOADS / f"{class_date}_video_{video.filename}"
        with open(dest, "wb") as f:
            while chunk := await video.read(1024 * 1024):
                f.write(chunk)
        video_path = dest

    from server.ingest_worker import start_ingest
    job_id = start_ingest(audio_path, video_path, class_date, class_number)
    return {"job_id": job_id}


@app.get("/api/ingest/status/{job_id}")
def ingest_status(job_id: str) -> dict:
    from server.ingest_worker import get_job
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8788)

"""Transcribe all salsa tutorial videos using DeepGram API.

Outputs JSON transcripts with word-level timestamps to data/transcripts/.
Then sections them into logical chunks and extracts key frames via ffmpeg.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
VIDEOS = ROOT / "videos"
TRANSCRIPTS = ROOT / "data" / "transcripts"
FRAMES = ROOT / "data" / "frames"
TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
FRAMES.mkdir(parents=True, exist_ok=True)

# Load key from Cooking .env.local
for env_file in [ROOT / ".env.local", ROOT.parent / "Cooking" / ".env.local"]:
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DEEPGRAM_API_KEY"):
                os.environ["DEEPGRAM_API_KEY"] = line.split("=", 1)[1].strip()

DG_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
DG_URL = "https://api.deepgram.com/v1/listen"


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def transcribe_video(video_path: Path) -> dict:
    audio_path = video_path.with_suffix(".m4a")
    if not audio_path.exists():
        subprocess.run([
            "ffmpeg", "-i", str(video_path), "-vn", "-acodec", "aac",
            "-b:a", "64k", str(audio_path), "-y"
        ], capture_output=True)

    with open(audio_path, "rb") as f:
        resp = requests.post(
            DG_URL,
            headers={"Authorization": f"Token {DG_KEY}", "Content-Type": "audio/m4a"},
            params={
                "model": "nova-2",
                "smart_format": "true",
                "utterances": "true",
                "punctuate": "true",
                "paragraphs": "true",
            },
            data=f,
            timeout=300,
        )
    resp.raise_for_status()
    return resp.json()


def section_transcript(result: dict) -> list[dict]:
    paragraphs = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("paragraphs", {}).get("paragraphs", [])

    if paragraphs:
        sections = []
        for i, para in enumerate(paragraphs):
            sentences = para.get("sentences", [])
            text = " ".join(s.get("text", "") for s in sentences)
            start = sentences[0].get("start", 0) if sentences else 0
            end = sentences[-1].get("end", 0) if sentences else 0
            sections.append({
                "start": start,
                "end": end,
                "heading": f"Part {i + 1}",
                "text": text.strip(),
            })
        return sections

    # Fallback: use utterances
    utterances = result.get("results", {}).get("utterances", [])
    if utterances:
        sections = []
        current_text = ""
        current_start = utterances[0].get("start", 0)
        for i, utt in enumerate(utterances):
            current_text += utt.get("transcript", "") + " "
            is_break = (
                i == len(utterances) - 1 or
                len(current_text) > 500 or
                (i < len(utterances) - 1 and utterances[i + 1].get("start", 0) - utt.get("end", 0) > 3.0)
            )
            if is_break:
                sections.append({
                    "start": current_start,
                    "end": utt.get("end", 0),
                    "heading": f"Part {len(sections) + 1}",
                    "text": current_text.strip(),
                })
                current_text = ""
                if i < len(utterances) - 1:
                    current_start = utterances[i + 1].get("start", 0)
        return sections

    # Last fallback
    alt = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0]
    return [{"start": 0, "heading": "Full Video", "text": alt.get("transcript", "")}]


def generate_bullets(sections: list[dict]) -> list[list[str]]:
    """Extract clean action-step bullets from transcript sections.

    Uses keyword patterns to pull out instructional content and skip filler.
    """
    filler = {"subscribe", "like", "comment", "channel", "welcome back",
              "thank you", "see you", "don't forget", "hit the bell", "link below"}
    action_cues = {"step", "foot", "count", "weight", "turn", "lead", "follow",
                   "hand", "arm", "hold", "break", "basic", "cross body", "lift",
                   "push", "pull", "frame", "shoulder", "hip", "knee", "toe",
                   "heel", "ball", "spin", "spot", "rotate", "pivot", "forward",
                   "back", "left", "right", "partner", "slow", "quick"}

    all_bullets = []
    for sec in sections:
        text = sec.get("text", "")
        if len(text) < 30:
            all_bullets.append([])
            continue

        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        bullets = []
        for sent in sentences:
            lower = sent.lower()
            if any(f in lower for f in filler):
                continue
            if any(a in lower for a in action_cues) and len(sent) > 15:
                clean = sent[0].upper() + sent[1:] if sent else sent
                if len(clean) > 150:
                    clean = clean[:147] + "..."
                bullets.append(clean)
        if not bullets and len(text) > 50:
            bullets = [text[:120].strip() + "..."]
        all_bullets.append(bullets[:8])
    return all_bullets


def update_transcript_steps(slug: str, bullets: list[list[str]], technique: str = "") -> None:
    """Merge new bullets into the master transcript_steps.json."""
    steps_file = ROOT / "data" / "transcript_steps.json"
    existing = json.loads(steps_file.read_text()) if steps_file.exists() else {}
    existing[f"{slug}.json"] = {
        "technique": technique,
        "steps": bullets,
    }
    steps_file.write_text(json.dumps(existing, indent=2))


TECHNIQUE_KEYWORDS = {
    "basic_step": ["basic-step", "basic-steps", "eddie-torres", "core-basic"],
    "inside_turn": ["inside-turn", "traveling-left", "free-spin"],
    "cross_body_lead": ["cross-body-lead"],
    "right_turn": ["right-turn", "single-right"],
    "prep_step": ["open-break", "5-simple"],
    "fundamentals": ["fundamental", "mambo-shine"],
}


def detect_technique(slug: str) -> str:
    for tech, keywords in TECHNIQUE_KEYWORDS.items():
        if any(kw in slug for kw in keywords):
            return tech
    return ""


def extract_frames(video_path: Path, sections: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, sec in enumerate(sections):
        out_file = output_dir / f"section_{i}.jpg"
        if out_file.exists():
            continue
        timestamp = sec.get("start", 0) + 2
        subprocess.run([
            "ffmpeg", "-ss", str(timestamp), "-i", str(video_path),
            "-frames:v", "1", "-q:v", "3", str(out_file), "-y"
        ], capture_output=True)


def main():
    if not DG_KEY:
        print("ERROR: DEEPGRAM_API_KEY not found")
        return

    video_files = sorted(VIDEOS.glob("*.mp4"))
    print(f"Found {len(video_files)} videos to transcribe")

    for vf in video_files:
        slug = slugify(vf.stem)
        out_file = TRANSCRIPTS / f"{slug}.json"

        if out_file.exists():
            print(f"  SKIP (exists): {vf.stem[:50]}")
            t = json.loads(out_file.read_text())
            sections = t.get("sections", [])
            frame_dir = FRAMES / slug
            if sections and not (frame_dir / "section_0.jpg").exists():
                print(f"    Extracting {len(sections)} frames...")
                extract_frames(vf, sections, frame_dir)
            continue

        print(f"  Transcribing: {vf.stem[:50]}...")
        try:
            result = transcribe_video(vf)

            alt = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0]
            full_text = alt.get("transcript", "")
            words = alt.get("words", [])
            duration = result.get("metadata", {}).get("duration", 0)

            sections = section_transcript(result)

            output = {
                "text": full_text,
                "duration": duration,
                "words": words,
                "sections": sections,
            }

            out_file.write_text(json.dumps(output, indent=2))
            print(f"    {len(sections)} sections, {len(full_text)} chars")

            frame_dir = FRAMES / slug
            print(f"    Extracting {len(sections)} frames...")
            extract_frames(vf, sections, frame_dir)

            # Auto-generate bullets
            if full_text and len(full_text) > 100:
                bullets = generate_bullets(sections)
                technique = detect_technique(slug)
                update_transcript_steps(slug, bullets, technique)
                total_bullets = sum(len(b) for b in bullets)
                print(f"    {total_bullets} bullets generated → {technique or 'untagged'}")

        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\nDone. Transcripts: {TRANSCRIPTS}, Frames: {FRAMES}")


if __name__ == "__main__":
    main()

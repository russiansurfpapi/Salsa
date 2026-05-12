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

        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\nDone. Transcripts: {TRANSCRIPTS}, Frames: {FRAMES}")


if __name__ == "__main__":
    main()

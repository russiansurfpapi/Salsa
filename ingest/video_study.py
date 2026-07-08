"""Analyze a class video frame-by-frame and generate a structured study guide.

Usage:
  python -m ingest.video_study ~/Desktop/IMG_8043.MOV --date 2026-05-26 --class-number 3
  python -m ingest.video_study                        # auto-detect latest video + class
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VIDEOS = ROOT / "videos"
FRAMES = DATA / "frames"

from ingest.transcribe import transcribe_video, section_transcript, slugify, DG_KEY
from ingest.analyze import _load_env

_load_env()


def extract_dense_frames(video_path: Path, frame_dir: Path, fps: float = 1.0) -> int:
    frame_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-i", str(video_path), "-vf", f"fps={fps}",
        "-q:v", "3", str(frame_dir / "frame_%03d.jpg"), "-y"
    ], capture_output=True)
    return len(list(frame_dir.glob("frame_*.jpg")))


def get_duration(video_path: Path) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path)
    ], capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration", 0))


def load_frame_as_base64(frame_path: Path) -> str:
    with open(frame_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def analyze_frames_with_claude(
    frame_dir: Path,
    frame_slug: str,
    transcript_text: str,
    teaching_points: list[dict],
    techniques_covered: list[str],
    key_phrases: list[str],
    videos_data: dict,
    class_date: str,
    class_number: int | None,
) -> dict:
    import anthropic

    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], timeout=300.0
    )

    frames = sorted(frame_dir.glob("frame_*.jpg"))
    if not frames:
        frames = sorted(frame_dir.glob("hd_*.jpg"))
    if not frames:
        raise RuntimeError(f"No frames found in {frame_dir}")

    # Sample frames: every frame for short videos, every 2nd for longer
    if len(frames) > 40:
        sampled = frames[::2]
    else:
        sampled = frames

    # Build image content blocks (batch all frames)
    image_blocks = []
    frame_list = []
    for f in sampled:
        b64 = load_frame_as_base64(f)
        image_blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        })
        sec = int(re.search(r'\d+', f.stem).group())
        image_blocks.append({
            "type": "text",
            "text": f"[{f.name} — {sec}s]",
        })
        frame_list.append(f.name)

    # Build the prompt
    techniques_str = ", ".join(techniques_covered)
    tips_str = "\n".join(f"- [{tp.get('technique', '?')}] {tp['tip']}" for tp in teaching_points)
    phrases_str = ", ".join(f'"{p}"' for p in key_phrases[:15])

    videos_section = ""
    for slug in techniques_covered:
        vids = videos_data.get(slug, [])
        if not vids and slug == "inside_turn":
            vids = videos_data.get("left_turn", [])
        if vids:
            videos_section += f"\n{slug}:\n"
            for v in vids[:3]:
                videos_section += f"  - {v['title']} ({v.get('channel', '?')}): {v['url']}\n"
                if v.get("note"):
                    videos_section += f"    Note: {v['note']}\n"

    prompt_text = f"""You are analyzing a salsa dance class video frame-by-frame. The video is from Class #{class_number or '?'} on {class_date}.

AUDIO TRANSCRIPT (instructor counting over music):
{transcript_text[:800]}

TECHNIQUES COVERED IN THIS CLASS: {techniques_str}

TEACHING POINTS FROM THE VOICE MEMO:
{tips_str}

KEY PHRASES: {phrases_str}

YOUTUBE TUTORIAL VIDEOS AVAILABLE:
{videos_section}

FRAMES: I'm showing you {len(sampled)} frames from the video (1 frame per second). Each frame is labeled with its filename and timestamp.

YOUR TASK: Analyze every frame and produce a structured JSON study guide. You must:

1. Map each frame to the specific technique being performed and the count (1-2-3 or 5-6-7)
2. Identify the 3 phases of the video: slow walk-through, full speed, partner work
3. For each frame, describe: body position, foot placement, hand/arm position, what count this is
4. Match what you SEE in the frames to the teaching points from the voice memo
5. Identify the KEY frames — the most important ones to freeze on and study
6. Note the hard transitions — where one technique ends and the next begins

Return ONLY valid JSON with this structure:
{{
  "title": "Short title for the study guide",
  "subtitle": "Studio name and class level",
  "techniques": [
    {{
      "slug": "technique_slug",
      "name": "Display Name",
      "tagline": "Short description",
      "what": "One paragraph explaining the technique",
      "mechanics": [{{"counts": "1-2", "action": "description"}}],
      "arm_styling": [{{"counts": "1-2-3", "action": "description"}}],
      "instructor_quotes": ["exact quote from teaching points"],
      "frames": [{{"frame": "frame_NNN.jpg", "caption": "what this frame shows"}}],
      "drill": "Practice instructions",
      "common_error": "Most common beginner mistake"
    }}
  ],
  "choreography": {{
    "sequence": "BASIC -> LEFT TURN -> SUZY Q -> etc",
    "phases": [
      {{
        "name": "Phase 1: Solo Choreo (slow)",
        "time": "0:00 - 0:30",
        "steps": [
          {{
            "frame": "frame_NNN.jpg",
            "time": "0:03",
            "counts": "1-2-3",
            "move": "Move Name",
            "body": "What you see in the frame — body position, feet, arms",
            "cue": "Instructor quote or count cue"
          }}
        ]
      }}
    ],
    "hard_transitions": [
      {{
        "from": "Move A",
        "to": "Move B",
        "frames": "NNN -> NNN",
        "why": "Why this transition is hard and what to watch for"
      }}
    ]
  }},
  "practice": {{
    "total_minutes": 25,
    "sections": [
      {{
        "name": "Section Name",
        "minutes": 10,
        "drills": [{{"name": "Drill", "minutes": 4, "instructions": "What to do"}}]
      }}
    ]
  }},
  "key_frames": [
    {{"frame": "frame_NNN.jpg", "label": "Short Label", "description": "Why this frame matters"}}
  ]
}}

IMPORTANT:
- Use ONLY frame filenames from this list: {json.dumps(frame_list)}
- Include 10+ key frames, covering every technique
- The choreography phases should have the frame for EVERY major position change
- Include YouTube video info in your analysis but NOT in the JSON (videos are added separately)
- Write in second person ("you", "your") for instructions
- Use the instructor's exact phrases as cues"""

    content = image_blocks + [{"type": "text", "text": prompt_text}]

    print(f"  Sending {len(sampled)} frames to Claude for analysis...")
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": content}],
        temperature=0.2,
    )

    text = resp.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0:
        raise RuntimeError("Claude did not return JSON")

    raw_json = text[start:end]
    try:
        guide = json.loads(raw_json)
    except json.JSONDecodeError:
        # Ask Claude to fix the JSON
        print("  JSON parse failed, requesting repair...")
        fix_resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8000,
            messages=[{"role": "user", "content": f"Fix this broken JSON so it parses. Return ONLY valid JSON, nothing else:\n\n{raw_json}"}],
            temperature=0,
        )
        fixed = fix_resp.content[0].text
        fs = fixed.find("{")
        fe = fixed.rfind("}") + 1
        guide = json.loads(fixed[fs:fe])

    # Add video links from videos.json
    for tech in guide.get("techniques", []):
        slug = tech.get("slug", "")
        vids = videos_data.get(slug, [])
        if not vids and slug == "inside_turn":
            vids = videos_data.get("left_turn", [])
        tech["videos"] = [
            {
                "title": v.get("title", ""),
                "url": v.get("url", ""),
                "channel": v.get("channel", ""),
                "why": v.get("note", ""),
            }
            for v in vids[:5]
        ]

    return guide


def save_study_guide(guide: dict, class_date: str, class_number: int | None, frame_slug: str) -> None:
    guide["class_date"] = class_date
    guide["class_number"] = class_number
    guide["video_slug"] = frame_slug

    guides_file = DATA / "study_guides.json"
    existing = json.loads(guides_file.read_text()) if guides_file.exists() else {}
    existing[class_date] = guide
    guides_file.write_text(json.dumps(existing, indent=2))
    print(f"  Saved study guide for {class_date}")


def update_breakdowns(guide: dict, frame_slug: str, class_date: str, video_filename: str) -> None:
    bd_file = DATA / "technique_breakdowns.json"
    breakdowns = json.loads(bd_file.read_text()) if bd_file.exists() else {}

    combo_key = f"class_{class_date.replace('-', '')}_combo"
    choreo = guide.get("choreography", {})

    # Build flat steps list from phases
    all_steps = []
    for phase in choreo.get("phases", []):
        for i, step in enumerate(phase.get("steps", [])):
            all_steps.append({
                "step_number": len(all_steps) + 1,
                "timestamp": step.get("time", ""),
                "frame": step.get("frame", ""),
                "count": step.get("counts", ""),
                "technique": step.get("move", "").lower().replace(" ", "_"),
                "position": step.get("body", ""),
                "instruction": step.get("body", ""),
                "instructor_tip": step.get("cue", ""),
                "what_to_watch": "",
            })

    breakdowns[combo_key] = {
        "video_breakdown": {
            "source": video_filename,
            "class_date": class_date,
            "frame_slug": frame_slug,
            "description": choreo.get("sequence", ""),
            "steps": all_steps,
        }
    }

    # Cross-reference from individual techniques
    technique_slugs = set()
    for tech in guide.get("techniques", []):
        slug = tech.get("slug", "")
        if slug:
            technique_slugs.add(slug)
    for slug in technique_slugs:
        if slug not in breakdowns:
            breakdowns[slug] = {}
        breakdowns[slug]["class_video"] = {
            "combo_key": combo_key,
            "frame_slug": frame_slug,
            "class_date": class_date,
        }

    bd_file.write_text(json.dumps(breakdowns, indent=2))
    print(f"  Updated technique_breakdowns.json ({len(technique_slugs)} techniques)")


def update_mongo(class_date: str, video_filename: str, frame_slug: str) -> None:
    from server.mongo import classes
    classes().update_one(
        {"class_date": class_date},
        {"$set": {
            "video_file": video_filename,
            "video_frame_slug": frame_slug,
            "has_video_breakdown": True,
        }},
    )
    print(f"  Updated MongoDB for {class_date}")


def main():
    parser = argparse.ArgumentParser(description="Analyze a class video and generate a study guide")
    parser.add_argument("video", nargs="?", help="Path to video file")
    parser.add_argument("--date", help="Class date (YYYY-MM-DD)")
    parser.add_argument("--class-number", type=int, help="Class number")
    parser.add_argument("--frames", help="Path to existing frame directory (skip extraction)")
    args = parser.parse_args()

    # Determine class info
    class_date = args.date
    if not class_date:
        from server.mongo import classes as classes_coll
        latest = classes_coll().find_one(sort=[("class_date", -1)])
        class_date = latest["class_date"] if latest else datetime.now().strftime("%Y-%m-%d")

    class_number = args.class_number
    if not class_number:
        notes = json.loads((DATA / "class_notes.json").read_text()) if (DATA / "class_notes.json").exists() else []
        match = next((n for n in notes if n.get("class_date") == class_date), None)
        class_number = match.get("class_number") if match else None

    # --frames mode: use existing frame directory, no video needed
    if args.frames:
        frame_dir = Path(args.frames).resolve()
        if not frame_dir.exists():
            print(f"ERROR: {frame_dir} not found")
            return
        slug = frame_dir.name
        video_path = None
        video_filename = f"{slug}.mp4"
        n_frames = len(list(frame_dir.glob("*.jpg")))
        print(f"\nFrames: {frame_dir} ({n_frames} frames)")
        print(f"Class: #{class_number} on {class_date}")
        print(f"Slug: {slug}")

        # Try to find a matching transcript
        transcript_file = DATA / "transcripts" / f"{slug}.json"
        # Also check the class transcript from MongoDB
        if not transcript_file.exists():
            from server.mongo import classes as classes_coll
            class_doc_t = classes_coll().find_one({"class_date": class_date}, {"transcript_file": 1})
            if class_doc_t:
                alt_tf = DATA / "transcripts" / class_doc_t["transcript_file"]
                if alt_tf.exists():
                    transcript_file = alt_tf
        if transcript_file.exists():
            print(f"  Using transcript: {transcript_file.name}")
            t = json.loads(transcript_file.read_text())
        else:
            print(f"  No transcript found, using empty")
            t = {"text": "", "sections": []}
    else:
        # Find video
        if args.video:
            video_path = Path(args.video).resolve()
        else:
            desktop = Path.home() / "Desktop"
            candidates = sorted(
                list(desktop.glob("*.MOV")) + list(desktop.glob("*.mov")) + list(desktop.glob("*.mp4")),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if not candidates:
                print("ERROR: No video found on Desktop and no --frames given")
                return
            video_path = candidates[0]
            print(f"Auto-detected: {video_path.name}")

        if not video_path.exists():
            print(f"ERROR: {video_path} not found")
            return

        slug = slugify(video_path.stem)
        frame_dir = FRAMES / slug
        video_filename = video_path.name

        print(f"\nVideo: {video_path.name}")
        print(f"Class: #{class_number} on {class_date}")
        print(f"Slug: {slug}")

        # Copy video
        dest = VIDEOS / video_path.name
        if not dest.exists():
            shutil.copy2(video_path, dest)
            print(f"Copied to {dest}")

        # Get duration
        duration = get_duration(video_path)
        fps = 1.0 if duration < 60 else 0.5
        print(f"Duration: {duration:.1f}s, extracting at {fps} fps")

        # Extract frames
        if not list(frame_dir.glob("frame_*.jpg")):
            n_frames = extract_dense_frames(video_path, frame_dir, fps)
            print(f"  Extracted {n_frames} frames")
        else:
            n_frames = len(list(frame_dir.glob("frame_*.jpg")))
            print(f"  {n_frames} frames already exist")

        # Transcribe audio
        transcript_file = DATA / "transcripts" / f"{slug}.json"
        if transcript_file.exists():
            print(f"  Transcript exists")
            t = json.loads(transcript_file.read_text())
        else:
            print(f"  Transcribing with whisper-large...")
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
            print(f"    {len(t['text'])} chars")

    # Load class context
    print("  Loading class context...")
    from server.mongo import classes as classes_coll
    class_doc = classes_coll().find_one({"class_date": class_date}, {"_id": 0, "words": 0, "transcript_text": 0})
    if not class_doc:
        print("  WARNING: No class doc found in MongoDB, using empty context")
        class_doc = {"teaching_points": [], "techniques_covered": [], "key_phrases": []}

    # Load videos
    videos_data = json.loads((DATA / "videos.json").read_text()) if (DATA / "videos.json").exists() else {}

    # Analyze with Claude Vision
    print("  Analyzing frames with Claude Vision...")
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

    # Save everything
    save_study_guide(guide, class_date, class_number, slug)
    update_breakdowns(guide, slug, class_date, video_filename)
    update_mongo(class_date, video_filename, slug)

    print(f"\nDone! Study guide: https://salsa-on2.vercel.app/study/{class_date}")
    print(f"Deploy with: cd {ROOT} && vercel deploy --prod")


if __name__ == "__main__":
    main()

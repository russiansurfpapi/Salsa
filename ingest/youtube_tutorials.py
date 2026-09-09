"""Discover technique-specific salsa tutorials with an LLM.

YouTube search supplies candidates. An LLM generates the search queries and
decides which candidates actually teach the class technique. This deliberately
does not use title regexes or parent-technique aliases for semantic matching.

Usage:
  python -m ingest.youtube_tutorials half_step --class-date 2026-07-21
  python -m ingest.youtube_tutorials half_step --class-date 2026-07-21 --refresh
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from ingest.analyze import _load_env
from server.salsa_context import SALSA_STYLE_NAME, salsa_style_context
from server.techniques import display_name_for_slug, normalize_technique_slug

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VIDEOS_FILE = DATA / "videos.json"
STUDY_GUIDES_FILE = DATA / "study_guides.json"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
OPENAI_MODEL = "gpt-4o-mini"

_load_env()


def _llm_json(system: str, user: str, *, max_tokens: int = 1200) -> dict:
    errors = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic

            client = anthropic.Anthropic(
                api_key=os.environ["ANTHROPIC_API_KEY"],
                timeout=120.0,
            )
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=0.1,
            )
            text = response.content[0].text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError("Claude did not return a JSON object")
            return json.loads(text[start:end])
        except Exception as exc:
            errors.append(f"Claude: {exc}")
            print(f"  Claude matching failed ({exc}); trying OpenAI")

    if os.environ.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                timeout=120.0,
            )
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=max_tokens,
            )
            return json.loads(response.choices[0].message.content or "{}")
        except Exception as exc:
            errors.append(f"OpenAI: {exc}")

    detail = "; ".join(errors) or "no Anthropic or OpenAI API key is configured"
    raise RuntimeError(f"No LLM was available for YouTube tutorial matching: {detail}")


def load_technique_context(slug: str, class_date: str | None = None) -> dict:
    """Load the meaning and class-specific cues for a technique."""
    slug = normalize_technique_slug(slug)
    context: dict[str, Any] = {
        "slug": slug,
        "name": display_name_for_slug(slug),
        "description": "",
        "breakdown": [],
        "class_tips": [],
    }

    content_file = DATA / "technique_content.json"
    if content_file.exists():
        raw = json.loads(content_file.read_text())
        content = raw.get("techniques", raw).get(slug, {})
        for key in ("name", "description", "breakdown", "key_details"):
            if content.get(key):
                context[key] = content[key]
        context["class_tips"] = list(content.get("class_tips", []))

    notes_file = DATA / "class_notes.json"
    if class_date and notes_file.exists():
        notes = json.loads(notes_file.read_text())
        class_note = next(
            (note for note in notes if note.get("class_date") == class_date),
            None,
        )
        if class_note:
            matching_points = [
                point
                for point in class_note.get("teaching_points", [])
                if normalize_technique_slug(point.get("technique", "")) == slug
            ]
            context["class_date"] = class_date
            context["class_teaching_points"] = matching_points
            context["class_summary"] = class_note.get("summary", "")

    return context


def generate_search_queries(context: dict) -> list[str]:
    """Ask the LLM how dancers and instructors would name this move on YouTube."""
    result = _llm_json(
        (
            f"You generate precise YouTube search queries for {SALSA_STYLE_NAME}. "
            f"{salsa_style_context()} "
            "The class may use an internal studio name that public tutorials do not use. "
            "Reason from the mechanics and class cues, then translate the move into likely "
            "public instructor terminology. Return JSON with a `queries` array of exactly "
            "3 concise queries: one with the class name, one with the most likely standard "
            "synonym, and one plain-language mechanics query that omits the class name. "
            "Do not stuff internal jargon into every query. Each query must target the "
            "specific move, not generic salsa basics."
        ),
        json.dumps(context, ensure_ascii=False),
        max_tokens=500,
    )
    queries = result.get("queries", [])
    return [str(query).strip() for query in queries if str(query).strip()][:3]


def search_youtube(query: str, limit: int = 10) -> list[dict]:
    """Retrieve YouTube candidates without deciding whether they are relevant."""
    executable = shutil.which("yt-dlp")
    if executable:
        cmd = [executable]
    else:
        cmd = [sys.executable, "-m", "yt_dlp"]
    cmd.extend([
        f"ytsearch{limit}:{query}",
        "--flat-playlist",
        "--dump-single-json",
        "--no-warnings",
    ])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        raise RuntimeError(f"YouTube search failed for {query!r}: {result.stderr.strip()}")

    payload = json.loads(result.stdout)
    candidates = []
    for entry in payload.get("entries", []):
        video_id = entry.get("id")
        if not video_id:
            continue
        candidates.append({
            "youtube_id": video_id,
            "title": entry.get("title", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": entry.get("channel") or entry.get("uploader") or "",
            "description": entry.get("description") or "",
            "duration_seconds": entry.get("duration"),
            "view_count": entry.get("view_count"),
            "search_query": query,
        })
    return candidates


def collect_candidates(queries: list[str], limit_per_query: int = 10) -> list[dict]:
    """Search all LLM queries and deduplicate candidates by YouTube ID."""
    by_id: dict[str, dict] = {}
    for query in queries:
        for candidate in search_youtube(query, limit_per_query):
            by_id.setdefault(candidate["youtube_id"], candidate)
    return list(by_id.values())


def rank_candidates_with_llm(context: dict, candidates: list[dict]) -> list[dict]:
    """Use semantic judgment to select tutorials that teach the exact move."""
    if not candidates:
        return []

    compact_candidates = [
        {
            "youtube_id": candidate["youtube_id"],
            "title": candidate["title"],
            "channel": candidate["channel"],
            "description": candidate["description"][:500],
            "duration_seconds": candidate["duration_seconds"],
            "view_count": candidate["view_count"],
        }
        for candidate in candidates
    ]
    result = _llm_json(
        (
            f"You select YouTube tutorials for a student's {SALSA_STYLE_NAME} class. "
            f"{salsa_style_context()} "
            "Judge semantic technique fit from the supplied mechanics, class teaching "
            "points, title, channel, and description. Relevance to the exact move is "
            "mandatory and matters more than popularity. A generic basic-step video is "
            "NOT a match for a named variation such as Half Step or Around the World "
            "unless its metadata explicitly shows that variation. Reject similarly named "
            "but mechanically different moves. Prefer clear instructional videos and On2 "
            "when available. Return JSON as {\"selected\": [{\"youtube_id\": \"...\", "
            "\"why\": \"specific evidence of fit\"}]}. Select at most 3. Return an empty "
            "array when the candidates do not provide evidence for the exact technique."
        ),
        json.dumps(
            {"technique": context, "candidates": compact_candidates},
            ensure_ascii=False,
        ),
        max_tokens=1000,
    )

    candidates_by_id = {
        candidate["youtube_id"]: candidate for candidate in candidates
    }
    selected = []
    seen: set[str] = set()
    for choice in result.get("selected", []):
        video_id = str(choice.get("youtube_id", ""))
        candidate = candidates_by_id.get(video_id)
        if not candidate or video_id in seen:
            continue
        seen.add(video_id)
        selected.append({
            "title": candidate["title"],
            "url": candidate["url"],
            "channel": candidate["channel"],
            "note": str(choice.get("why", "")).strip(),
            "match_method": "llm",
            "matched_technique": context["slug"],
        })
        if len(selected) == 3:
            break
    return selected


def discover_tutorials(slug: str, class_date: str | None = None) -> list[dict]:
    """Generate queries, search YouTube, and LLM-rank exact tutorials."""
    context = load_technique_context(slug, class_date)
    queries = generate_search_queries(context)
    if not queries:
        raise RuntimeError(f"LLM returned no search queries for {slug}")
    print(f"  LLM queries for {context['name']}:")
    for query in queries:
        print(f"    - {query}")

    candidates = collect_candidates(queries)
    print(f"  Found {len(candidates)} unique candidates; asking LLM to rank exact matches")
    selected = rank_candidates_with_llm(context, candidates)
    for video in selected:
        print(f"    -> {video['title']} ({video['channel']})")
    if not selected:
        print("    No exact tutorial had enough evidence; leaving the video list empty")
    return selected


def ensure_tutorials_for_techniques(
    videos_data: dict,
    techniques: list[str],
    *,
    class_date: str | None = None,
) -> dict:
    """Discover videos for missing exact technique keys and persist the catalog."""
    updated = dict(videos_data)
    changed = False
    for raw_slug in techniques:
        slug = normalize_technique_slug(raw_slug)
        if not slug or updated.get(slug):
            continue
        print(f"  No exact YouTube tutorials cached for {slug}; running LLM discovery")
        selected = discover_tutorials(slug, class_date)
        if selected:
            updated[slug] = selected
            changed = True
    if changed:
        VIDEOS_FILE.write_text(json.dumps(updated, indent=2))
    return updated


def apply_catalog_to_study_guides(
    slug: str,
    videos: list[dict],
    class_date: str | None = None,
) -> int:
    """Refresh already-generated study guides with the exact LLM matches."""
    if not STUDY_GUIDES_FILE.exists():
        return 0
    slug = normalize_technique_slug(slug)
    guides = json.loads(STUDY_GUIDES_FILE.read_text())
    changed = 0
    for date, guide in guides.items():
        if class_date and date != class_date:
            continue
        for technique in guide.get("techniques", []):
            if normalize_technique_slug(technique.get("slug", "")) != slug:
                continue
            technique["videos"] = [
                {
                    "title": video.get("title", ""),
                    "url": video.get("url", ""),
                    "channel": video.get("channel", ""),
                    "why": video.get("note", ""),
                    "match_method": video.get("match_method", "llm"),
                }
                for video in videos
            ]
            changed += 1
    if changed:
        STUDY_GUIDES_FILE.write_text(json.dumps(guides, indent=2))
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Use an LLM to find exact YouTube tutorials for a salsa technique"
    )
    parser.add_argument("technique", help="Technique name or slug")
    parser.add_argument("--class-date", help="Use teaching points from this class")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Replace an existing video set instead of using the cache",
    )
    args = parser.parse_args()

    slug = normalize_technique_slug(args.technique)
    videos_data = (
        json.loads(VIDEOS_FILE.read_text()) if VIDEOS_FILE.exists() else {}
    )
    if videos_data.get(slug) and not args.refresh:
        selected = videos_data[slug]
        print(f"Using {len(selected)} cached exact tutorial(s) for {slug}")
    else:
        selected = discover_tutorials(slug, args.class_date)
        videos_data[slug] = selected
        VIDEOS_FILE.write_text(json.dumps(videos_data, indent=2))
        print(f"Saved {len(selected)} tutorial(s) under videos.json[{slug!r}]")

    changed = apply_catalog_to_study_guides(slug, selected, args.class_date)
    noun = "entry" if changed == 1 else "entries"
    print(f"Updated {changed} study-guide technique {noun}")


if __name__ == "__main__":
    main()

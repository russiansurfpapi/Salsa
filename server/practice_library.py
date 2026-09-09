"""Deterministic practice sessions built from identified class techniques.

The sessions in this module are deliberately premade rather than generated at
request time.  Class notes decide which techniques are exposed and provide the
source cues shown beside every practice.
"""
from __future__ import annotations

from typing import Any

from server.salsa_context import SALSA_STYLE_NAME
from server.video_lectures import video_parts_for_technique


PREMADE_PRACTICES: dict[str, dict[str, Any]] = {
    "side_to_side": {
        "focus_summary": (
            "Lock in Class 6's first fundamental: a compact lateral weight "
            "transfer on 5-6-7 and the opposite side on 1-2-3, then connect it "
            "to the right-turn combination shown in the lecture."
        ),
        "warmup": {
            "minutes": 3,
            "instructions": [
                "Face the mirror with soft knees and mark 1-2-3, 5-6-7 for eight phrases.",
                "Shift your full weight laterally without letting either step grow wider than one foot-width.",
            ],
        },
        "drills": [
            {
                "name": "Class 6 lateral transfer",
                "minutes": 7,
                "counts": "5-6-7, 1-2-3",
                "instructions": [
                    "Step side on 5, then use 6-7 to return toward center with the class's quick-quick-slow feel.",
                    "Repeat the action toward the opposite side on 1-2-3.",
                    "Complete 12 phrases slowly, settling your hip over the standing leg before changing direction.",
                ],
                "success_check": "You stay in a narrow slot and complete every weight transfer without a tap or recovery step.",
                "class_date": "2026-07-28",
            },
            {
                "name": "Side-to-side into the class turn",
                "minutes": 6,
                "counts": "Side-to-side phrase, then right turn",
                "instructions": [
                    "Dance one side-to-side phrase exactly as shown in the Class 6 lecture.",
                    "Add the stationary right turn from the combination, then return to a compact basic.",
                    "Repeat eight times and freeze after the turn to check balance.",
                ],
                "success_check": "The lateral phrase, turn, and return to basic remain distinct and on time.",
                "class_date": "2026-07-28",
            },
        ],
        "music_round": {
            "minutes": 5,
            "instructions": [
                "Alternate two side-to-side phrases with one Class 6 turn combination to a slow On2 song.",
                "Reduce the step size whenever the return to center starts to rush.",
            ],
        },
        "self_checks": [
            "Did I fully move my weight rather than only reaching the free foot?",
            "Could I enter the turn without widening or speeding up the side-to-side?",
        ],
    },
    "basic_step": {
        "focus_summary": (
            "Clean up the 3-and-7 anchors and make the latest class's 6-7-1 "
            "transition deliberate without rushing the On2 phrase."
        ),
        "warmup": {
            "minutes": 3,
            "instructions": [
                "Mark 1-2-3, pause on 4, then 5-6-7, pause on 8 for eight phrases.",
                "Say “quick, quick, slow” and make each foot strike land with the beat.",
            ],
        },
        "drills": [
            {
                "name": "Anchor 3 and 7",
                "minutes": 6,
                "counts": "1-2-3, 5-6-7",
                "instructions": [
                    "Travel on 1 and 2, then plant your weight on 3 without moving that foot.",
                    "Travel back on 5 and 6, then plant your weight on 7 without moving that foot.",
                    "Repeat 12 phrases with small steps; reset whenever either anchor travels.",
                ],
                "success_check": "Counts 3 and 7 stay planted for five phrases in a row.",
                "class_date": "2026-07-07",
            },
            {
                "name": "The 7 and the 6-7-1 handoff",
                "minutes": 6,
                "counts": "6-7-1",
                "instructions": [
                    "On 7, bend both knees and drop your weight onto the back foot while keeping your posture lifted.",
                    "Continue into 1 smoothly; do not hurry the feet or skip the weight change.",
                    "Loop 6-7-1 eight times, then place it back inside the full basic for eight phrases.",
                ],
                "success_check": "The direction change into 1 feels smooth and every 7 has a complete weight change.",
                "class_date": "2026-07-21",
            },
        ],
        "music_round": {
            "minutes": 5,
            "instructions": [
                "Dance only the basic to one slow song.",
                "For the first half, audit the anchors on 3 and 7; for the second half, audit 6-7-1.",
            ],
        },
        "self_checks": [
            "Did either foot slide or take an extra step on 3 or 7?",
            "Did I finish the weight change on 7 before moving into 1?",
        ],
    },
    "right_turn": {
        "focus_summary": (
            "Finish the leader's right turn on time with an open right shoulder, "
            "an early rotation, and a stable final position."
        ),
        "warmup": {
            "minutes": 3,
            "instructions": [
                "Dance eight relaxed basics, keeping the full 1-2-3, 5-6-7 phrase.",
                "On the final four basics, open the right shoulder without starting a turn.",
            ],
        },
        "drills": [
            {
                "name": "Full-count right turn",
                "minutes": 7,
                "counts": "5-6-7, 1-2-3, 4-5",
                "instructions": [
                    "Count aloud: 5, 6, 7, 1, 2, 3, 4, 5.",
                    "As the leader, initiate the right turn early in 5-6; keep the right shoulder open and follow it through.",
                    "Repeat four turns, holding the final position each time; complete three sets.",
                ],
                "success_check": "You face the partner position by count 1 and can hold the finish without taking a recovery step.",
                "class_date": "2026-07-21",
            },
            {
                "name": "Spot and hold",
                "minutes": 5,
                "counts": "Leader spots by 1",
                "instructions": [
                    "Choose a partner-height target in front of you.",
                    "Complete six right turns and find the target by count 1 each time.",
                    "Freeze the finish for one beat before beginning the next movement.",
                ],
                "success_check": "The target is clear by 1 on four consecutive turns and the final position is balanced.",
                "class_date": "2026-07-21",
            },
        ],
        "music_round": {
            "minutes": 5,
            "instructions": [
                "Repeat basic → leader right turn → basic to a slow song.",
                "If the turn finishes after 1, stop, find the phrase, and restart instead of rushing the next basic.",
            ],
        },
        "self_checks": [
            "Did the turn begin during 5-6 instead of at the last moment?",
            "Was I facing the partner position by 1 with enough balance to hold?",
        ],
    },
    "inside_turn": {
        "focus_summary": (
            "Practice the two partner-turn jobs recorded under Inside Turn: a "
            "clear follower right-turn lead and the leader's own left-turn timing."
        ),
        "evidence_note": (
            "Your class analyzer uses Inside Turn for both the follower turn led "
            "on 1 and the leader/follower left-turn timing. The drills keep those "
            "two class uses separate."
        ),
        "warmup": {
            "minutes": 3,
            "instructions": [
                "Dance eight basics and keep your hands relaxed with no thumbs in the connection.",
                "Choose a fixed partner-height point to use for spotting.",
            ],
        },
        "drills": [
            {
                "name": "Lead the follower's right turn",
                "minutes": 7,
                "counts": "Signal on 1; follower turns on 2-3",
                "instructions": [
                    "Use one hand and raise it on count 1 while your own feet continue the basic.",
                    "Guide an air partner to the right on 2-3; keep the hand path compact and rotate the wrist without using the thumb.",
                    "Keep your 7 away from the partner position. Repeat 10 times.",
                ],
                "success_check": "The signal is visible on 1 and your own basic never changes while the follower turns.",
                "class_date": "2026-07-07",
            },
            {
                "name": "Leader left-turn clock",
                "minutes": 6,
                "counts": "Leader turns on 5-6-7; faces partner by 1",
                "instructions": [
                    "Start from the partner-facing position and count one full On2 phrase aloud.",
                    "As the leader, make the left turn during 5-6-7 and spot the partner position by 1.",
                    "Repeat eight times, resetting if the spot arrives late.",
                ],
                "success_check": "You complete the leader timing on 7 and face the partner position by 1 for four turns in a row.",
                "class_date": "2026-07-21",
            },
        ],
        "music_round": {
            "minutes": 4,
            "instructions": [
                "Alternate one follower right-turn lead and one leader left turn, with a basic between them.",
                "Keep the two timing jobs distinct instead of blending their signals or counts.",
            ],
        },
        "self_checks": [
            "Did I signal the follower turn on 1 without changing my basic?",
            "On my own left turn, was I facing the partner position by 1?",
        ],
    },
    "suzy_q": {
        "focus_summary": (
            "Make every Suzy Q weight change distinct, keep the crosses in front, "
            "and then carry the same compact footwork through the circular class variation."
        ),
        "warmup": {
            "minutes": 3,
            "instructions": [
                "March the six On2 steps for four phrases, lifting each free foot instead of dragging it.",
                "Without music, say “cross, step, cross, cross, step, cross” twice before moving.",
            ],
        },
        "drills": [
            {
                "name": "Isolated Suzy Q",
                "minutes": 7,
                "counts": "Cross-step-cross; cross-step-cross",
                "instructions": [
                    "Cross in front, take a compact step, and cross in front again; never place the cross behind.",
                    "Say the full pattern aloud and complete eight slow repetitions.",
                    "Lift the free leg after each cross so the next weight change is clean.",
                ],
                "success_check": "All crosses stay in front and each of the three weight changes is visible without a dragged foot.",
                "class_date": "2026-07-07",
            },
            {
                "name": "Circular class variation",
                "minutes": 5,
                "counts": "Keep the class's Suzy Q phrase",
                "instructions": [
                    "Use the four room targets from class: bathroom, wall, door, and mirror.",
                    "Complete one Suzy Q toward each target, making a smooth curve between directions rather than a sharp corner.",
                    "Complete two circles, then reverse by starting with the left foot as taught in class.",
                ],
                "success_check": "You reach each class target without changing the compact cross-step-cross pattern.",
                "class_date": "2026-07-07",
            },
        ],
        "music_round": {
            "minutes": 5,
            "instructions": [
                "Alternate four basics with one isolated Suzy Q for one slow song.",
                "Use the latest class check on the final cross: face forward and cross cleanly.",
            ],
        },
        "self_checks": [
            "Did every cross land in front rather than behind?",
            "Could I change direction without making the Suzy Q wider?",
        ],
    },
    "half_step": {
        "focus_summary": (
            "Keep basic-step timing while taking only the shortened Around the "
            "World direction change, then anchor before continuing."
        ),
        "warmup": {
            "minutes": 4,
            "instructions": [
                "Dance eight basics on 1-2-3, 5-6-7.",
                "Audit the anchor on 3 and 7 before adding any direction change.",
            ],
        },
        "drills": [
            {
                "name": "Half change and anchor",
                "minutes": 8,
                "counts": "1-2-3, 5-6-7",
                "instructions": [
                    "Take the half step to the right with exactly the same timing as your basic.",
                    "Stop at the shortened direction change instead of continuing the full Around the World rotation.",
                    "Anchor before continuing. Repeat 12 times without music.",
                ],
                "success_check": "The direction change stops at the class's halfway point and the next phrase begins from a stable anchor.",
                "class_date": "2026-07-21",
            },
            {
                "name": "Half versus full",
                "minutes": 4,
                "counts": "One On2 phrase per version",
                "instructions": [
                    "Alternate one full Around the World direction change with one Half Step.",
                    "Say “full” or “half” before moving so the two class variations remain distinct.",
                ],
                "success_check": "A viewer could tell which version you chose before the next phrase begins.",
                "class_date": "2026-07-14",
            },
        ],
        "music_round": {
            "minutes": 4,
            "instructions": [
                "Dance basic → Half Step right → basic to a slow song.",
                "Keep the original 1-2-3, 5-6-7 timing; only the amount of direction change should differ.",
            ],
        },
        "self_checks": [
            "Did I preserve the basic timing throughout the Half Step?",
            "Did I anchor after the shortened change instead of continuing the full rotation?",
        ],
    },
    "around_the_world": {
        "focus_summary": (
            "Carry the On2 basic through the class's 12, 9, and 6 o'clock "
            "directions while keeping counts 3 and 7 anchored."
        ),
        "warmup": {
            "minutes": 4,
            "instructions": [
                "Face 12 o'clock and dance eight basics on 1-2-3, 5-6-7.",
                "Keep 3 and 7 planted so the anchor is clear before changing direction.",
            ],
        },
        "drills": [
            {
                "name": "Class clock-face route",
                "minutes": 10,
                "counts": "1-2-3, 5-6-7",
                "instructions": [
                    "Mark the class's three named targets: 12, 9, and 6 o'clock.",
                    "Take one complete basic phrase toward each target in that order.",
                    "Anchor before redirecting, then repeat the route four times.",
                ],
                "success_check": "You arrive at each named target on time without moving either anchor count.",
                "class_date": "2026-07-14",
            },
        ],
        "music_round": {
            "minutes": 6,
            "instructions": [
                "Repeat the 12 → 9 → 6 route to a slow song.",
                "Reduce the size of the direction change if an anchor starts to travel.",
            ],
        },
        "self_checks": [
            "Did I preserve 1-2-3, 5-6-7 while changing direction?",
            "Was I balanced at the anchor before aiming at the next clock position?",
        ],
    },
    "prep_step": {
        "focus_summary": (
            "Build the rightward body twist that prepares the class's left turn, "
            "then release that preparation into the turn on count 3."
        ),
        "warmup": {
            "minutes": 4,
            "instructions": [
                "Dance eight basics with relaxed joints and compact steps.",
                "Keep the feet quiet while rotating the torso gently right and returning to center eight times.",
            ],
        },
        "drills": [
            {
                "name": "Right twist to left release",
                "minutes": 8,
                "counts": "Release into the left twist on 3",
                "instructions": [
                    "Before the left turn, twist the body to the right as taught in class.",
                    "Count 1-2-3 and let the right twist unlock into the left twist on 3.",
                    "Reset without adding extra footwork and repeat 12 times.",
                ],
                "success_check": "The direction change happens from the stored right twist on 3 rather than from an arm pull.",
                "class_date": "2026-05-26",
            },
            {
                "name": "Prep inside the phrase",
                "minutes": 4,
                "counts": "1-2-3, 5-6-7",
                "instructions": [
                    "Dance one basic, add one right-twist preparation before the left turn, then return to basic.",
                    "Repeat six times slowly and stop if the prep changes the On2 count.",
                ],
                "success_check": "The preparation is visible in the torso while the count remains unchanged.",
                "class_date": "2026-05-26",
            },
        ],
        "music_round": {
            "minutes": 4,
            "instructions": [
                "Alternate a plain basic with one prepared left-turn phrase.",
                "Use a slow song and prioritize the right-to-left body action over turn size.",
            ],
        },
        "self_checks": [
            "Could I feel the right twist storing the preparation?",
            "Did the leftward release occur on 3 without an arm yank?",
        ],
    },
    "cross_body_lead": {
        "focus_summary": (
            "Make the recorded partner-direction signal compact and readable "
            "without stepping into the follower's space."
        ),
        "evidence_note": (
            "The class analyzer filed the May 26 partner-direction and left-turn "
            "lead cues under Cross Body Lead. This practice uses those recorded "
            "cues and does not invent an unrelated slot pattern."
        ),
        "warmup": {
            "minutes": 3,
            "instructions": [
                "Dance eight small basics while keeping an air partner's space clear.",
                "Set a compact frame at shoulder width; keep the hands relaxed.",
            ],
        },
        "drills": [
            {
                "name": "Subtle count-2 direction signal",
                "minutes": 7,
                "counts": "Signal on 2",
                "instructions": [
                    "Take a normal forward step without entering the follower's space.",
                    "Add the subtle hip and arm twist on count 2; do not exaggerate it.",
                    "Bring the right hand closer to you and the left hand closer to the air partner. Repeat 10 times.",
                ],
                "success_check": "The direction signal is clear on 2 while your step size and the follower's space stay unchanged.",
                "class_date": "2026-05-26",
            },
            {
                "name": "Compact hand path and frame",
                "minutes": 6,
                "counts": "Keep the signal inside the phrase",
                "instructions": [
                    "Keep the right hand centered and lift the left hand up and out.",
                    "Keep the arms near shoulder width around the air partner's head instead of widening them.",
                    "Repeat eight signals, then eight more with a partner if one is available.",
                ],
                "success_check": "The hands give one consistent direction without a mixed or oversized signal.",
                "class_date": "2026-05-26",
            },
        ],
        "music_round": {
            "minutes": 4,
            "instructions": [
                "Use four basics between each compact count-2 signal.",
                "Stay with the exact class mechanics; do not add a larger pattern that was not recorded.",
            ],
        },
        "self_checks": [
            "Did I keep a normal step instead of moving into the follower's space?",
            "Were the hands compact and unambiguous on count 2?",
        ],
    },
    "transition_basic": {
        "focus_summary": (
            "Let the turn land on the class's count-8 pause, then continue through "
            "1-2-3 without rushing or dropping the right-to-right connection."
        ),
        "warmup": {
            "minutes": 4,
            "instructions": [
                "Dance eight basics and make the pause between 7 and 1 audible in your count.",
                "Hold an air partner's right hand with your right hand and keep the connection relaxed.",
            ],
        },
        "drills": [
            {
                "name": "Land, pause, continue",
                "minutes": 8,
                "counts": "Turn on 6; land on 8; continue 1-2-3",
                "instructions": [
                    "Mark the turn on 6, then arrive and pause on count 8.",
                    "Continue with 1, 2, 3 only after the landing is stable.",
                    "Repeat 10 times; restart any repetition that rushes through 8.",
                ],
                "success_check": "Count 8 is a controlled landing and 1 begins from balance rather than momentum.",
                "class_date": "2026-07-07",
            },
            {
                "name": "Keep the hand connection",
                "minutes": 4,
                "counts": "6-8-1-2-3",
                "instructions": [
                    "Repeat the landing drill while maintaining a right-to-right hand hold.",
                    "Do not switch back to the original hand position after the turn.",
                ],
                "success_check": "The right-to-right connection remains continuous through the pause and return to basic.",
                "class_date": "2026-07-07",
            },
        ],
        "music_round": {
            "minutes": 4,
            "instructions": [
                "Dance basic → turn transition → basic to a slow song.",
                "Make the count-8 landing visible before continuing into 1-2-3.",
            ],
        },
        "self_checks": [
            "Did I pause and balance on 8 instead of rushing into 1?",
            "Did the right-to-right connection stay intact through the transition?",
        ],
    },
}


def _technique_slugs(class_note: dict[str, Any]) -> list[str]:
    """Return normalized-enough technique slugs from either class-note shape."""
    result: list[str] = []
    for technique in class_note.get("techniques_covered", []):
        if isinstance(technique, str) and technique and technique not in result:
            result.append(technique)
    for technique in class_note.get("matched_techniques", []):
        slug = technique.get("slug", "") if isinstance(technique, dict) else ""
        if slug and slug not in result:
            result.append(slug)
    return result


def _fallback_practice(technique_name: str, latest_source: dict[str, Any]) -> dict[str, Any]:
    """Give newly detected techniques a safe class-cue practice immediately."""
    date = latest_source.get("date", "")
    return {
        "focus_summary": (
            f"Rehearse {technique_name} from the latest class cue without adding "
            "mechanics that were not recorded."
        ),
        "evidence_note": (
            "This technique was newly identified and does not yet have a curated "
            "multi-drill session. The observation practice below stays inside "
            "the available class evidence."
        ),
        "warmup": {
            "minutes": 3,
            "instructions": [
                "Mark the New York On2 phrase slowly: 1-2-3, pause, 5-6-7, pause.",
                "Review the exact class cue shown below before moving.",
            ],
        },
        "drills": [
            {
                "name": "Class-cue isolation",
                "minutes": 8,
                "counts": "Use only the counts named in the class cue",
                "instructions": [
                    f"Practice only the {technique_name} action described by the instructor cue.",
                    "Work slowly for eight repetitions and stop whenever the movement requires an unrecorded guess.",
                ],
                "success_check": "Your repetition matches the recorded cue and adds no unsupported timing or placement.",
                "class_date": date,
            },
        ],
        "music_round": {
            "minutes": 4,
            "instructions": [
                "With slow On2 music, observe where the recorded action belongs.",
                "If the class cue does not specify enough detail, mark the count and save the physical question for class.",
            ],
        },
        "self_checks": [
            "What part of the instructor cue could I reproduce exactly?",
            "What unresolved mechanic should I ask about in the next class?",
        ],
    }



def _sortable_date(class_date: str) -> int:
    """YYYY-MM-DD -> 20260908, for newest-first sorting.

    Only the leading ISO date is read, so a session-suffixed key such as
    "2026-09-08-advanced" (a second class on the same night) sorts with its
    own date instead of raising. Anything unparseable sorts oldest.
    """
    digits = class_date[:10].replace("-", "")
    return int(digits) if digits.isdigit() else 0

def build_practice_library(
    class_notes: list[dict[str, Any]],
    technique_catalog: dict[str, Any] | None = None,
    lecture_library: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one premade, source-linked practice for every identified technique."""
    catalog = technique_catalog or {}
    names: dict[str, str] = {}
    categories: dict[str, str] = {}
    for technique in catalog.get("techniques", []):
        name = technique.get("name", "")
        slug = name.lower().replace(" ", "_")
        if slug:
            names[slug] = name
            categories[slug] = technique.get("category", "")

    sorted_notes = sorted(
        (note for note in class_notes if isinstance(note, dict)),
        key=lambda note: note.get("class_date", ""),
    )
    latest_note = sorted_notes[-1] if sorted_notes else {}
    latest_techniques = _technique_slugs(latest_note)

    sources_by_technique: dict[str, list[dict[str, Any]]] = {}
    cues_by_technique: dict[str, list[dict[str, Any]]] = {}
    for note in sorted_notes:
        slugs = _technique_slugs(note)
        source = {
            "date": note.get("class_date", ""),
            "number": note.get("class_number"),
        }
        for slug in slugs:
            sources_by_technique.setdefault(slug, []).append(source)
        for point in note.get("teaching_points", []):
            slug = point.get("technique", "")
            tip = point.get("tip", "")
            if not slug or not tip:
                continue
            cues_by_technique.setdefault(slug, []).append(
                {
                    "tip": tip,
                    "context": point.get("context", ""),
                    "class_date": note.get("class_date", ""),
                    "class_number": note.get("class_number"),
                }
            )

    practices: list[dict[str, Any]] = []
    for slug, sources in sources_by_technique.items():
        technique_name = names.get(slug, slug.replace("_", " ").title())
        template = PREMADE_PRACTICES.get(slug)
        if template is None:
            template = _fallback_practice(technique_name, sources[-1])

        warmup = dict(template.get("warmup", {}))
        drills = [dict(drill) for drill in template.get("drills", [])]
        music_round = dict(template.get("music_round", {}))
        total_minutes = (
            int(warmup.get("minutes", 0))
            + sum(int(drill.get("minutes", 0)) for drill in drills)
            + int(music_round.get("minutes", 0))
        )
        latest_cues = list(reversed(cues_by_technique.get(slug, [])))[:4]

        practices.append(
            {
                "id": slug,
                "technique": slug,
                "technique_name": technique_name,
                "category": categories.get(slug, ""),
                "title": f"{technique_name}: class practice",
                "style": SALSA_STYLE_NAME,
                "total_minutes": total_minutes,
                "focus_summary": template.get("focus_summary", ""),
                "evidence_note": template.get("evidence_note", ""),
                "warmup": warmup,
                "drills": drills,
                "music_round": music_round,
                "self_checks": list(template.get("self_checks", [])),
                "class_cues": latest_cues,
                "class_sources": list(reversed(sources)),
                "latest_class": sources[-1],
                "video_parts": video_parts_for_technique(
                    lecture_library or {},
                    slug,
                ),
                "is_latest_class_technique": slug in latest_techniques,
                "is_curated": slug in PREMADE_PRACTICES,
            }
        )

    latest_index = {slug: index for index, slug in enumerate(latest_techniques)}
    practices.sort(
        key=lambda practice: (
            0 if practice["is_latest_class_technique"] else 1,
            latest_index.get(practice["technique"], 999),
            -_sortable_date(practice["latest_class"].get("date", "")),
            practice["technique_name"],
        )
    )

    return {
        "style": SALSA_STYLE_NAME,
        "source": "NYC Salsa class notes",
        "latest_class": {
            "date": latest_note.get("class_date", ""),
            "number": latest_note.get("class_number"),
            "techniques": latest_techniques,
        },
        "count": len(practices),
        "practices": practices,
    }

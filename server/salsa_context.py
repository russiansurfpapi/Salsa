"""Canonical dance-style context shared by every Salsa LLM workflow."""
from __future__ import annotations

SALSA_STYLE_NAME = "New York-style salsa (NY On2 / Eddie Torres-style mambo)"

SALSA_STYLE_CONTEXT = """\
This product teaches and practices New York-style salsa: NY On2 / Eddie
Torres-style mambo. Treat that as a hard constraint, not a preference.

- Keep the 1-2-3, 5-6-7 phrase and the curriculum's On2 break/change-of-
  direction emphasis on counts 2 and 6.
- Never silently substitute On1/LA-style timing, Cuban/casino mechanics, or
  generic salsa advice.
- Prefer New York slot/line mechanics, compact weight transfers, partner
  connection, shines, and the leader/follower timing taught in the student's
  class evidence.
- When terminology differs across studios, preserve the mechanics and the
  instructor's class cues. Say when a public name is only an approximate alias.
- If source material conflicts with the student's class evidence, prioritize
  the class evidence and explicitly flag the conflict.
"""


def salsa_style_context() -> str:
    """Return the canonical instruction block for prompts and API responses."""
    return f"STYLE: {SALSA_STYLE_NAME}\n\n{SALSA_STYLE_CONTEXT.strip()}"

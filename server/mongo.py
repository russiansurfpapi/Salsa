"""MongoDB client for the Salsa project.

Connects to the FUM cluster in the `salsa` database.

Collections:
  classes       — one doc per class recording (transcript, analysis, tips)
  class_tips    — denormalized tips per technique (for fast per-technique queries)
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    for env_path in [ROOT / ".env.secrets", ROOT.parent / "Cooking" / ".env.secrets"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                m = re.match(r"^([A-Z_0-9]+)=(.*)$", line)
                if m and m.group(1) not in os.environ:
                    val = m.group(2).strip()
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                        val = val[1:-1]
                    os.environ[m.group(1)] = val


_load_env()

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is not None:
        return _db
    from pymongo import MongoClient

    uri = os.environ.get("MONGODB_URI")
    name = os.environ.get("MONGODB_DB", "salsa")
    if not uri:
        raise RuntimeError("MONGODB_URI not set in .env.secrets")
    _client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    _db = _client[name]
    return _db


def classes():
    coll = get_db()["classes"]
    try:
        coll.create_index("class_date", unique=True)
    except Exception:
        pass
    return coll


def class_tips():
    return get_db()["class_tips"]


def skill_ratings():
    coll = get_db()["skill_ratings"]
    try:
        coll.create_index("skill_id", unique=True)
    except Exception:
        pass
    return coll


def skill_rating_history():
    return get_db()["skill_rating_history"]


def frames():
    return get_db()["frames"]

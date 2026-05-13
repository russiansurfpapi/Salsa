"""Vercel serverless entry point — re-exports the FastAPI app."""
import sys
from pathlib import Path

# Add project root to path so imports work
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.app import app

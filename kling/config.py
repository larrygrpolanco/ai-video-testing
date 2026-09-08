"""Configuration loading (reads the project-root .env)."""

# Dependencies live in the project `.venv` (see requirements.txt / pyrightconfig.json).
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = parent of the kling/ package directory.
ROOT = Path(__file__).resolve().parent.parent

# Load .env from the project root regardless of the current working directory.
load_dotenv(ROOT / ".env")

# Global (Singapore) Kling API endpoint.
BASE_URL = os.getenv("KLING_BASE_URL", "https://api-singapore.klingai.com")

_PLACEHOLDERS = {
    "",
    "your_api_key_here",
    "your_api_key",
    "sk-your-api-key",
    "changeme",
    "xxxxx",
}


def api_key() -> str:
    key = os.getenv("KLING_API_KEY", "").strip()
    if key.lower() in _PLACEHOLDERS:
        raise RuntimeError(
            "KLING_API_KEY is not set. Add it to the .env file "
            "(see .env.example) or set the KLING_API_KEY environment variable."
        )
    return key

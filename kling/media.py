"""Helpers for turning local files into API inputs."""

from __future__ import annotations

import base64
from pathlib import Path


def image_input(path_or_url: str) -> str:
    """Return a value usable in Kling `url` fields.

    URLs are passed through unchanged; local files are base64-encoded
    (raw bytes, no ``data:`` URI prefix, per Kling's docs).
    """
    s = str(path_or_url)
    if s.startswith(("http://", "https://")):
        return s
    p = Path(s)
    if not p.is_file():
        raise FileNotFoundError(f"Image not found: {p}")
    return base64.b64encode(p.read_bytes()).decode("ascii")

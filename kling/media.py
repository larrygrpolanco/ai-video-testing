"""Helpers for turning local files into API inputs."""

from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import urlsplit


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


def url_suffix(url: str, default: str = "") -> str:
    """Extension of a URL's path, ignoring any query string or fragment.

    Kling's generated asset URLs are hotlink-protected and carry a long
    ``?cacheKey=...&Signature=...`` query string. Calling ``Path(url).suffix``
    naively would fold that query string into the filename (and blow past the
    OS filename length limit), so derive the extension from the path only.
    """
    return Path(urlsplit(url).path).suffix or default

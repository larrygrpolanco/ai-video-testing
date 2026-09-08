"""Pricing helpers (list prices from https://kling.ai/dev/pricing, 2026-05).

These are estimates for cost-tracking in the playground — treat them as
approximate and re-check the live pricing page for exact figures.
"""

from __future__ import annotations

# USD per second of video, keyed by (model, resolution, audio).
VIDEO_PPS: dict[tuple[str, str, str], float] = {
    ("kling-3.0", "720p", "off"): 0.084,
    ("kling-3.0", "1080p", "off"): 0.112,
    ("kling-3.0", "4k", "off"): 0.42,
    ("kling-3.0", "720p", "native"): 0.126,
    ("kling-3.0", "1080p", "native"): 0.168,
    ("kling-3.0", "4k", "native"): 0.42,
    ("kling-3.0-turbo", "720p", "native"): 0.112,
    ("kling-3.0-turbo", "1080p", "native"): 0.14,
    ("kling-3.0-omni", "720p", "off"): 0.084,
    ("kling-3.0-omni", "1080p", "off"): 0.112,
    ("kling-3.0-omni", "4k", "off"): 0.42,
    ("kling-3.0-omni", "720p", "native"): 0.112,
    ("kling-3.0-omni", "1080p", "native"): 0.14,
    ("kling-3.0-omni", "4k", "native"): 0.42,
}

# USD per image.
IMAGE_PRICE_USD: dict[str, float] = {
    "kling-v3": 0.028,  # 1K / 2K
    "kling-v3-omni": 0.028,  # 1K / 2K (4K is 0.056)
    "kling-image-o1": 0.028,
    "kling-v2-1": 0.014,  # text-to-image (cheapest)
    "kling-v2": 0.014,
    "kling-v1-5": 0.014,
    "kling-v1": 0.0035,
}


def estimate_video_cost(model: str, resolution: str, audio: str, duration: int) -> float | None:
    """Estimated USD for one video, or None if the combination is unknown."""
    pps = VIDEO_PPS.get((model, resolution, audio))
    if pps is None:
        return None
    return round(pps * duration, 4)


def estimate_image_cost(model_name: str, n: int = 1) -> float | None:
    """Estimated USD for n images, or None if the model is unknown."""
    price = IMAGE_PRICE_USD.get(model_name)
    if price is None:
        return None
    return round(price * n, 4)

"""Minimal Kling AI client for the playground.

Implements Kling's *new* path-style API for the 3.x video models plus the
legacy-shaped image-generation endpoint. See kling-api-essentials.md for the
full reference and model/pricing tables.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from . import config


class KlingError(RuntimeError):
    """Raised when the Kling API returns a non-zero business code or HTTP error."""


@dataclass
class VideoSettings:
    """Video output settings for the Kling 3.x models."""

    resolution: str = "720p"  # 720p | 1080p | 4k
    aspect_ratio: str = "16:9"  # 16:9 | 9:16 | 1:1  (text-to-video only)
    duration: int = 5  # 3..15
    audio: str = "off"  # off | native
    multi_shot: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution": self.resolution,
            "aspect_ratio": self.aspect_ratio,
            "duration": self.duration,
            "audio": self.audio,
            "multi_shot": self.multi_shot,
        }


class KlingClient:
    """Thin wrapper around the Kling AI HTTP API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or config.api_key()
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------ low-level
    def _post(self, path: str, payload: dict) -> dict:
        resp = self.session.post(f"{self.base_url}{path}", json=payload)
        return self._check(resp)

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self.session.get(f"{self.base_url}{path}", params=params)
        return self._check(resp)

    @staticmethod
    def _check(resp: requests.Response) -> dict:
        try:
            body = resp.json()
        except ValueError as err:
            resp.raise_for_status()
            raise KlingError(f"Non-JSON response ({resp.status_code}): {resp.text[:300]}") from err
        code = body.get("code")
        if resp.status_code >= 400 or code not in (0, None):
            raise KlingError(
                f"HTTP {resp.status_code}, code={code}, message={body.get('message')!r}"
            )
        return body

    # --------------------------------------------------------------- task polling
    def get_tasks(self, task_ids=None, external_task_ids=None) -> list[dict]:
        params: dict[str, str] = {}
        if task_ids:
            params["task_ids"] = ",".join(task_ids)
        elif external_task_ids:
            params["external_task_ids"] = ",".join(external_task_ids)
        return self._get("/tasks", params).get("data", [])

    def wait_for_task(self, task_id: str, interval: float = 3.0, timeout: float = 600.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            tasks = self.get_tasks([task_id])
            if not tasks:
                raise KlingError(f"Task {task_id} not found")
            task = tasks[0]
            status = task.get("status")
            if status == "succeeded":
                return task
            if status == "failed":
                raise KlingError(f"Task {task_id} failed: {task.get('message')}")
            time.sleep(interval)
        raise TimeoutError(f"Task {task_id} not finished within {timeout}s")

    # --------------------------------------------- video generation (path-style API)
    def text_to_video(
        self,
        prompt: str,
        model: str = "kling-3.0",
        settings: VideoSettings | None = None,
        callback_url: str = "",
        external_task_id: str = "",
    ) -> dict:
        s = (settings or VideoSettings()).to_dict()
        payload = {
            "prompt": prompt,
            "settings": s,
            "options": {
                "callback_url": callback_url,
                "external_task_id": external_task_id,
                "watermark_info": {"enabled": False},
            },
        }
        return self._post(f"/text-to-video/{model}", payload)

    def image_to_video(
        self,
        image_url: str,
        prompt: str = "",
        model: str = "kling-3.0",
        settings: VideoSettings | None = None,
        last_frame_url: str = "",
        callback_url: str = "",
        external_task_id: str = "",
    ) -> dict:
        s = settings or VideoSettings()
        # Note: image-to-video has no `aspect_ratio` (it inherits from the input image).
        settings_dict = {
            "resolution": s.resolution,
            "duration": s.duration,
            "audio": s.audio,
            "multi_shot": s.multi_shot,
        }
        contents: list[dict[str, str]] = []
        if prompt:
            contents.append({"type": "prompt", "text": prompt})
        contents.append({"type": "first_frame", "url": image_url})
        if last_frame_url:
            contents.append({"type": "last_frame", "url": last_frame_url})
        payload = {
            "contents": contents,
            "settings": settings_dict,
            "options": {
                "callback_url": callback_url,
                "external_task_id": external_task_id,
                "watermark_info": {"enabled": False},
            },
        }
        return self._post(f"/image-to-video/{model}", payload)

    # ----------------------------------------------- image generation (legacy shape)
    def text_to_image(
        self,
        prompt: str,
        model_name: str = "kling-v3",
        n: int = 1,
        resolution: str = "1k",
        aspect_ratio: str = "16:9",
        **extra: Any,
    ) -> dict:
        payload = {
            "model_name": model_name,
            "prompt": prompt,
            "n": n,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            **extra,
        }
        return self._post("/v1/images/generations", payload)

    def get_image_task(self, task_id: str) -> dict:
        return self._get(f"/v1/images/generations/{task_id}").get("data", {})

    def wait_for_image_task(
        self, task_id: str, interval: float = 2.0, timeout: float = 300.0
    ) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = self.get_image_task(task_id)
            status = data.get("task_status")
            if status == "succeed":
                return data
            if status == "failed":
                raise KlingError(f"Image task {task_id} failed: {data.get('task_status_msg')}")
            time.sleep(interval)
        raise TimeoutError(f"Image task {task_id} not finished within {timeout}s")

    # -------------------------------------------------------------------- utilities
    @staticmethod
    def outputs_of(task: dict, type_: str = "video") -> list[dict]:
        """Return task outputs of a given type (video/image/audio/element/voice)."""
        return [o for o in task.get("outputs", []) if o.get("type") == type_]

    def download(self, url: str, dest: str | Path) -> Path:
        """Download a generated asset (uses the auth session for hotlink protection)."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(url, stream=True, timeout=180) as resp:
            resp.raise_for_status()
            try:
                with open(dest, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        fh.write(chunk)
            except OSError as err:
                raise KlingError(f"Failed to write {dest}: {err}") from err
        return dest

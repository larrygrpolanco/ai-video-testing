#!/usr/bin/env python3
"""Experiment 00 — image-to-image "inspiration art" keyframes.

Take a reference picture + a style prompt and produce a stylized image
(image-to-image) that is a better starting frame for image-to-video than the
raw photo. With ``--to-video`` you can chain straight into image-to-video and
compare the raw-photo route (experiment 01) against the restyled route.

A case may omit ``image`` to run as plain text-to-image — handy for characters
or objects (a mount, a patron, a beast) that aren't in your source picture.

Usage:
    python run.py                 # run all cases (image-to-image only)
    python run.py --name ink      # only cases whose name contains "ink"
    python run.py --to-video      # also animate each generated keyframe
    python run.py --dry-run       # print plan + estimated cost, no API calls
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Make the project root importable regardless of the current working directory.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from kling import (  # noqa: E402
    KlingClient,
    KlingError,
    VideoSettings,
    estimate_image_cost,
    estimate_video_cost,
)
from kling.media import image_input, url_suffix  # noqa: E402

EXPERIMENT_DIR = Path(__file__).resolve().parent
CASES_FILE = EXPERIMENT_DIR / "cases.json"
ASSETS_DIR = EXPERIMENT_DIR / "assets"
OUTPUT_DIR = EXPERIMENT_DIR / "output"

# Settings keys we accept from cases.json (kept explicit so typos are ignored
# instead of silently passed to the API).
IMAGE_SETTING_FIELDS = {
    "resolution",
    "aspect_ratio",
    "image_reference",
    "n",
    "image_fidelity",
    "human_fidelity",
}
VIDEO_SETTING_FIELDS = set(VideoSettings.__dataclass_fields__)


def make_settings(defaults: dict, overrides: dict | None, allowed: set) -> dict:
    merged = {k: v for k, v in defaults.items() if k in allowed}
    if overrides:
        merged.update({k: v for k, v in overrides.items() if k in allowed})
    return merged


def load_cases() -> tuple[str, dict, str, dict, list[dict]]:
    try:
        data = json.loads(CASES_FILE.read_text())
    except FileNotFoundError as err:
        raise SystemExit(f"Cases file not found: {CASES_FILE}") from err
    except json.JSONDecodeError as err:
        raise SystemExit(f"Invalid JSON in {CASES_FILE}: {err}") from err
    model = data.get("model", "kling-v2-1")
    defaults = data.get("default_settings", {})
    video_model = data.get("video_model", "kling-3.0")
    video_defaults = data.get("default_video_settings", {})
    cases = list(data.get("cases", []))

    matrix = data.get("matrix")
    if matrix:
        for img in matrix.get("images", []):
            for i, prompt in enumerate(matrix.get("prompts", []), start=1):
                cases.append(
                    {
                        "name": f"{Path(img).stem}-p{i}",
                        "image": img,
                        "prompt": prompt,
                    }
                )

    if not cases:
        raise SystemExit("No cases found in cases.json (define 'cases' or 'matrix').")
    return model, defaults, video_model, video_defaults, cases


def resolve_image(image: str | None) -> tuple[str | None, str]:
    """Return (api_input, display_path) for an image ref.

    ``None`` / ``""`` means the case is text-to-image (no reference image).
    """
    if image in (None, ""):
        return None, "(text-to-image)"
    s = str(image)
    if s.startswith(("http://", "https://")):
        return s, s
    p = Path(s) if Path(s).is_absolute() else ASSETS_DIR / s
    return image_input(str(p)), str(p)


def slugify(name: str) -> str:
    out = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")
    return out or "case"


def parse_int(value, default: int) -> int:
    """Coerce a JSON value to int, falling back to ``default`` on bad input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def fmt_cost(v) -> str:
    return f"${v:.4f}" if v is not None else "$? (unknown)"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--name", help="run only cases whose name contains this substring")
    ap.add_argument("--dry-run", action="store_true", help="print plan + cost, no API calls")
    ap.add_argument(
        "--to-video", action="store_true", help="animate each keyframe after generating"
    )
    ap.add_argument("--poll-interval", type=float, default=3.0, help="seconds between polls")
    ap.add_argument("--timeout", type=float, default=600.0, help="max seconds to wait per task")
    args = ap.parse_args()

    model, defaults, video_model, video_defaults, cases = load_cases()
    selected = [c for c in cases if not args.name or args.name.lower() in c["name"].lower()]
    if not selected:
        raise SystemExit(f"No cases matched --name {args.name!r}")

    # Build the resolved plan (image settings + video settings + cost).
    plan = []
    total = 0.0
    for c in selected:
        s = make_settings(defaults, c.get("settings"), IMAGE_SETTING_FIELDS)
        icost = estimate_image_cost(model, parse_int(s.get("n", 1), 1))
        vs = make_settings(video_defaults, c.get("video_settings"), VIDEO_SETTING_FIELDS)
        vcost = (
            estimate_video_cost(
                video_model,
                vs.get("resolution", "720p"),
                vs.get("audio", "off"),
                parse_int(vs.get("duration", 5), 5),
            )
            if args.to_video
            else None
        )
        total += (icost or 0.0) + (vcost or 0.0)
        plan.append((c, s, icost, vs, vcost))

    mode = "img2img + i2v" if args.to_video else "img2img"
    print(
        f"Model: {model}  |  Mode: {mode}  |  Cases: {len(plan)}  |  Est. total: {fmt_cost(total)}"
    )
    for c, s, icost, vs, vcost in plan:
        if vcost is not None:
            extra = (
                f"  → {video_model} {vs.get('resolution')}/{vs.get('audio')} "
                f"{vs.get('duration')}s {fmt_cost(vcost)}"
            )
        else:
            extra = ""
        if c.get("image"):
            ref = f"{s.get('resolution', '1k')}/{s.get('image_reference', 'subject')}"
        else:
            ref = f"{s.get('resolution', '1k')}/text"
        print(f"  - {c['name']:<30} {ref} x{s.get('n', 1)} {fmt_cost(icost)}{extra}")

    if args.dry_run:
        return

    client = KlingClient()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest = {"runs": []}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError) as err:
            raise SystemExit(f"Could not read {manifest_path}: {err}") from err

    for c, s, icost, vs, vcost in plan:
        run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + slugify(c["name"])
        run_dir = OUTPUT_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        api_input, display_path = resolve_image(c.get("image"))
        print(f"\n▶ {c['name']} ({fmt_cost(icost)} est.) — image: {display_path}")

        meta = {
            "run_id": run_id,
            "name": c["name"],
            "model": model,
            "mode": "text-to-image" if api_input is None else "image-to-image",
            "image": display_path,
            "prompt": c.get("prompt", ""),
            "settings": s,
            "created_at": time.time(),
        }
        try:
            n = parse_int(s.get("n", 1), 1)
            resolution = s.get("resolution", "1k")
            aspect_ratio = s.get("aspect_ratio", "16:9")
            if api_input is None:
                resp = client.text_to_image(
                    prompt=c.get("prompt", ""),
                    model_name=model,
                    n=n,
                    resolution=resolution,
                    aspect_ratio=aspect_ratio,
                    external_task_id=run_id,
                )
            else:
                resp = client.image_to_image(
                    image_url=api_input,
                    prompt=c.get("prompt", ""),
                    model_name=model,
                    image_reference=s.get("image_reference", ""),
                    image_fidelity=s.get("image_fidelity"),
                    human_fidelity=s.get("human_fidelity"),
                    n=n,
                    resolution=resolution,
                    aspect_ratio=aspect_ratio,
                    external_task_id=run_id,
                )
            task_id = resp["data"]["task_id"]
            meta["task_id"] = task_id
            print(f"   image task {task_id} submitted…")

            task = client.wait_for_image_task(task_id, args.poll_interval, args.timeout)
            images = task.get("task_result", {}).get("images", [])
            meta["status"] = "succeeded"
            meta["image_files"] = []
            for i, img in enumerate(images):
                ext = url_suffix(img.get("url", ""), ".png")
                dest = client.download(img["url"], run_dir / f"image{i}{ext}")
                meta["image_files"].append(dest.name)
                print(f"   ✓ saved {dest.name}")

            if args.to_video and meta["image_files"]:
                keyframe = run_dir / meta["image_files"][0]
                vprompt = c.get("video_prompt") or c.get("prompt", "")
                print(f"   → animating {keyframe.name} ({fmt_cost(vcost)} est.)")
                vresp = client.image_to_video(
                    image_url=image_input(str(keyframe)),
                    prompt=vprompt,
                    model=video_model,
                    settings=VideoSettings(**vs),
                    external_task_id=run_id + "-video",
                )
                vtask_id = vresp["data"]["id"]
                meta["video_task_id"] = vtask_id
                meta["video_prompt"] = vprompt
                meta["video_settings"] = vs

                vtask = client.wait_for_task(vtask_id, args.poll_interval, args.timeout)
                videos = client.outputs_of(vtask, "video")
                meta["video_files"] = []
                for i, v in enumerate(videos):
                    ext = url_suffix(v.get("url", ""), ".mp4")
                    dest = client.download(v["url"], run_dir / f"video{i}{ext}")
                    meta["video_files"].append(dest.name)
                    print(f"   ✓ saved {dest.name}")
                if vtask.get("billing"):
                    meta["video_billing"] = vtask["billing"]

            meta["finished_at"] = time.time()
        except (KlingError, TimeoutError) as e:
            meta["status"] = "failed"
            meta["error"] = str(e)
            print(f"   ✗ {e}")

        (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        manifest["runs"].append(meta)

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nDone. Results in {OUTPUT_DIR}/ (summary: manifest.json)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Experiment 01 — image-to-video from reference pictures.

For each case in cases.json: submit an image-to-video task, poll until done,
download the video, and save a metadata file with the prompt + inputs so you
can compare how Kling reacts to different images and prompts.

Usage:
    python run.py                 # run all cases
    python run.py --name NAME     # run only cases whose name contains NAME
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

from kling import KlingClient, KlingError, VideoSettings, estimate_video_cost  # noqa: E402
from kling.media import image_input, url_suffix  # noqa: E402

EXPERIMENT_DIR = Path(__file__).resolve().parent
CASES_FILE = EXPERIMENT_DIR / "cases.json"
ASSETS_DIR = EXPERIMENT_DIR / "assets"
OUTPUT_DIR = EXPERIMENT_DIR / "output"

_SETTING_FIELDS = set(VideoSettings.__dataclass_fields__)


def make_settings(defaults: dict, overrides: dict | None = None) -> VideoSettings:
    merged = {k: v for k, v in defaults.items() if k in _SETTING_FIELDS}
    if overrides:
        merged.update({k: v for k, v in overrides.items() if k in _SETTING_FIELDS})
    return VideoSettings(**merged)


def load_cases() -> tuple[str, dict, list[dict]]:
    try:
        data = json.loads(CASES_FILE.read_text())
    except FileNotFoundError as err:
        raise SystemExit(f"Cases file not found: {CASES_FILE}") from err
    except json.JSONDecodeError as err:
        raise SystemExit(f"Invalid JSON in {CASES_FILE}: {err}") from err
    model = data.get("model", "kling-3.0")
    defaults = data.get("default_settings", {})
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
    return model, defaults, cases


def resolve_image(image: str) -> tuple[str, str]:
    """Return (api_input, display_path) for an image ref."""
    s = str(image)
    if s.startswith(("http://", "https://")):
        return s, s
    p = Path(s) if Path(s).is_absolute() else ASSETS_DIR / s
    return image_input(str(p)), str(p)


def slugify(name: str) -> str:
    out = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")
    return out or "case"


def fmt_cost(v) -> str:
    return f"${v:.4f}" if v is not None else "$? (unknown)"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--name", help="run only cases whose name contains this substring")
    ap.add_argument("--dry-run", action="store_true", help="print plan + cost, no API calls")
    ap.add_argument("--poll-interval", type=float, default=3.0, help="seconds between polls")
    ap.add_argument("--timeout", type=float, default=600.0, help="max seconds to wait per task")
    args = ap.parse_args()

    model, defaults, cases = load_cases()
    selected = [c for c in cases if not args.name or args.name.lower() in c["name"].lower()]
    if not selected:
        raise SystemExit(f"No cases matched --name {args.name!r}")

    # Build resolved plan (settings + cost) for every selected case.
    plan = []
    total = 0.0
    for c in selected:
        s = make_settings(defaults, c.get("settings"))
        cost = estimate_video_cost(model, s.resolution, s.audio, s.duration)
        total += cost or 0.0
        plan.append((c, s, cost))

    print(f"Model: {model}  |  Cases: {len(plan)}  |  Estimated total: {fmt_cost(total)}")
    for c, s, cost in plan:
        print(f"  - {c['name']:<30} {s.resolution}/{s.audio} {s.duration}s  {fmt_cost(cost)}")

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

    for c, s, cost in plan:
        run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + slugify(c["name"])
        run_dir = OUTPUT_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        api_input, display_path = resolve_image(c["image"])
        print(f"\n▶ {c['name']} ({fmt_cost(cost)} est.) — image: {display_path}")

        meta = {
            "run_id": run_id,
            "name": c["name"],
            "model": model,
            "image": display_path,
            "prompt": c.get("prompt", ""),
            "settings": s.to_dict(),
            "created_at": time.time(),
        }
        try:
            resp = client.image_to_video(
                image_url=api_input,
                prompt=c.get("prompt", ""),
                model=model,
                settings=s,
                external_task_id=run_id,
            )
            task_id = resp["data"]["id"]
            meta["task_id"] = task_id
            print(f"   task {task_id} submitted…")

            task = client.wait_for_task(task_id, args.poll_interval, args.timeout)
            videos = client.outputs_of(task, "video")
            meta["status"] = "succeeded"
            meta["video_files"] = []
            for i, v in enumerate(videos):
                ext = url_suffix(v.get("url", ""), ".mp4")
                dest = client.download(v["url"], run_dir / f"video{i}{ext}")
                meta["video_files"].append(dest.name)
                print(f"   ✓ saved {dest.name}")
            if task.get("billing"):
                meta["billing"] = task["billing"]
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

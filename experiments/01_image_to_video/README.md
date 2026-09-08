# Experiment 01 — Image-to-video from reference pictures

Goal: learn how Kling animates reference images and how prompt wording changes
the result. Each run saves the video next to a `meta.json` (prompt + inputs),
so you can review and compare.

## Run

1. Drop reference images into `assets/` (`.jpg` / `.jpeg` / `.png`).
2. Edit `cases.json` — add a case per (image, prompt) you want to try.
3. Preview cost without spending anything:

   ```bash
   python run.py --dry-run
   ```

4. Run:

   ```bash
   python run.py                 # all cases
   python run.py --name mountain # only cases whose name contains "mountain"
   ```

## cases.json

- `model`: which Kling model to use (default `kling-3.0`).
- `default_settings`: resolution / duration / audio / multi_shot applied to every case.
- `cases`: list of `{ "name", "image", "prompt", "settings"? }`.
- `matrix` (optional): instead of explicit `cases`, a cross-product of
  `{ "images": [...], "prompts": [...] }` — every image × every prompt.

`image` may be a URL or a path relative to `assets/`. Local files are
base64-encoded automatically, so you don't need to host them publicly.

## Output

`output/<run_id>-<name>/` contains `video0.mp4` plus `meta.json`.
`output/manifest.json` accumulates a summary of every run (id, prompt, image,
settings, task id, status, billing).

## Cost

Kling 3.0 @ 720p / no audio = **$0.084/sec** (5s ≈ $0.42, 10s ≈ $0.84).
`--dry-run` prints the estimated total before you spend anything.

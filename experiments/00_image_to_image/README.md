# Experiment 00 — Image-to-image "inspiration art" keyframes

Goal: turn a raw reference photo into a *stylized keyframe* that is a better
starting frame for image-to-video than the untouched photo. Kling's
image-to-image keeps your subject (`image_reference: "subject"`) while the
prompt re-renders it in whatever style you describe — ink wash, neon noir, oil
painting, whatever.

Optionally chain straight into image-to-video with `--to-video`, so you can
compare "raw photo → video" (experiment 01) against "restyled art → video"
(this experiment).

## Run

1. Drop reference images into `assets/` (`.jpg` / `.jpeg` / `.png`).
2. Edit `cases.json` — one case per (image, style prompt) pair. Omit `image`
   on a case to run it as plain text-to-image (for characters or beasts that
   aren't in your source picture, like the Veiled Seer below).
3. Preview cost without spending anything:

   ```bash
   python run.py --dry-run
   python run.py --dry-run --to-video   # also see the video cost
   ```

4. Run:

   ```bash
   python run.py                    # image-to-image only
   python run.py --to-video         # generate keyframe, then animate it
   python run.py --name ink         # only cases whose name contains "ink"
   ```

## cases.json

- `model`: image model. Default **`kling-v2-1`** — the newest model that
  supports `image_reference` (subject/face) for image-to-image. **$0.014/image.**
  Other options: `kling-v1-5` (supports `image_fidelity`/`human_fidelity`),
  `kling-v3` (uses the omni endpoint instead — see below).
- `default_settings`: applied to every case:
  - `resolution`: `1k` | `2k`
  - `aspect_ratio`: `16:9` | `9:16` | `1:1` | `4:3` | `3:4` | `3:2` | `2:3` | `21:9`
  - `image_reference`: `subject` (keep the subject) | `face` (keep the face,
    single face only) | `""` (loose style reference)
  - `n`: how many variations to generate (1–9) — bump this to explore
  - `image_fidelity` / `human_fidelity`: 0–1 strength knobs (kling-v1 / v1-5 only)
- `cases`: list of `{ "name", "prompt", "image"?, "settings"? }`.
  - `image` (optional): a URL or a path relative to `assets/`. Omit it (or set
    it to `""`) to run the case as **text-to-image** — the prompt alone
    generates the image, with no reference.
  - `prompt`: the **style** prompt (what the output should look like).
  - `video_prompt` (optional): the **motion** prompt used by `--to-video`.
    Falls back to `prompt` if omitted.
  - `video_settings` (optional): per-case overrides for the video step.
- `matrix` (optional): cross-product of `{ "images": [...], "prompts": [...] }`.
- `video_model` / `default_video_settings`: used only with `--to-video`.

`image` may be a URL or a path relative to `assets/`. Local files are
base64-encoded automatically, so you don't need to host them publicly.

## Output

`output/<run_id>-<name>/` contains `image0.png` (the keyframe) plus `meta.json`
(prompt, reference image, settings, task id). With `--to-video` it also has
`video0.mp4`. `output/manifest.json` accumulates a summary of every run.

## Cost

| Step | Model | Price |
| --- | --- | --- |
| image-to-image | `kling-v2-1` | **$0.014/image** |
| image-to-video | `kling-3.0` 720p/no audio | $0.084/sec (5s ≈ $0.42) |

`--dry-run` prints the estimated total before you spend anything.

## Notes & next steps

- `image_reference: "subject"` keeps *character/subject features* while the
  prompt controls style — that's the "restyle my photo" dial. For portraits,
  `"face"` pins facial identity instead (image must contain exactly one face).
- `image_fidelity` / `human_fidelity` only apply to `kling-v1` / `kling-v1-5`;
  they're ignored by `kling-v2-1`.
- **Multiple reference pictures** ("blend these into one art piece") need the
  Omni endpoint (`POST /v1/images/omni-image`, models `kling-v3-omni` /
  `kling-image-o1`) which takes an `image_list` and references images in the
  prompt as `<<<image_1>>>`. Not wired into this experiment yet — see
  `kling-api-essentials.md` and the Kling docs if you want to extend it.

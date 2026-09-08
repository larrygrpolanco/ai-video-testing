# AI Video Testing — Playground

Experiments with Kling AI's video/image generation API. See
[`kling-api-essentials.md`](kling-api-essentials.md) for the full API reference
(endpoints, models, pricing, storyboarding).

## Setup

1. Create a virtualenv and install deps:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Add your API key:

   ```bash
   cp .env.example .env
   # edit .env and set KLING_API_KEY=<your key>
   ```

   Get a key at <https://kling.ai/dev/api-key>

## Lint

[Ruff](https://docs.astral.sh/ruff/) keeps the Python consistent:

```bash
pip install -r requirements-dev.txt
ruff check .       # lint
ruff format .      # format
```

Config lives in [`pyproject.toml`](pyproject.toml).

## Structure

```
kling/                  shared helpers (client, pricing, media)
experiments/            one isolated folder per experiment
  01_image_to_video/    reference pictures -> video, prompts saved alongside
```

## Philosophy

Each experiment folder is self-contained: its own inputs (`assets/`,
`cases.json`), its own entrypoint (`run.py`), and its own `output/`
(gitignored). Every generated video is saved next to a `meta.json` containing
the exact prompt, input image, model, and settings, so you can diff how Kling
responds to different inputs.

Start small and cheap (720p, no audio, 5s ≈ **$0.42/clip**). Use `--dry-run`
to preview cost before spending.

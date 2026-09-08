# Kling AI API — Essentials (for prototyping)

> Researched from Kling AI's **official** docs on 2026-05-29.
> Primary sources: `https://kling.ai/document-api` (all pages are also served as Markdown — append `.md` to any docs URL), `https://kling.ai/document-api/llms.txt`, and `https://kling.ai/dev/pricing`.

---

## TL;DR — what you actually need to know

- **Product**: Kling AI (Kuaishou) generative video/image API. Async: you submit a task, poll for it, then download the result.
- **Base URL (global)**: `https://api-singapore.klingai.com`
- **Auth**: one **API Key**, sent as `Authorization: Bearer <API_KEY>`. Get it at `https://kling.ai/dev/api-key`.
- **Models are billed per second of video** (not per video). You pre-buy a "resource package" of **Units** (1 video Unit = **$0.14** list price).
- **Cheapest current-gen option (your target)**: **Kling 3.0 (`kling-3.0`), 720p, no audio = $0.084/sec** → a 5s clip ≈ **$0.42**, 10s ≈ **$0.84**.
- **Two API "generations" coexist** — see the gotcha section. Use the **new path-style API** (`/text-to-video/kling-3.0`), not the legacy `model_name` endpoints.
- **Results expire after 30 days.** Download them to your own storage immediately.
- **Multi-shot storyboarding is built into the prompt** (`shot 1, 3s, …; shot 2, 3s, …;`) — up to 6 shots in one call.

---

## 1. Getting started (one-time setup)

1. Sign up / log in at **<https://kling.ai/dev>** (same account as the Kling web app).
2. Buy a resource package (there's a cheap **Trial package** for onboarding) at **<https://kling.ai/dev/pricing>**.
3. Open **<https://kling.ai/dev/api-key>** → **"+ Create a new API Key"** → name it → copy it (shown only once).
4. Store it in an env var, e.g. `KLING_API_KEY`.

```bash
export KLING_API_KEY="sk-..."
```

---

## 2. Authentication

Every request needs this header:

```
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

**Legacy alternative** (only for the old `model_name` endpoints): sign a short-lived **JWT (HS256)** from an AccessKey + SecretKey pair:

```python
import time, jwt

token = jwt.encode(
    {"iss": ak, "exp": int(time.time()) + 1800, "nbf": int(time.time()) - 5},
    sk,
    headers={"alg": "HS256", "typ": "JWT"},
)
# send as: Authorization: Bearer <token>
```

For prototyping, **just use the API Key** — it's the recommended method and works for all models.

---

## 3. ⚠️ The big gotcha: two API generations

Kling runs **two different API conventions at once**. This is the #1 source of confusion in third-party tutorials.

| | **New API (use this)** | **Legacy API** |
|---|---|---|
| Model is specified | **in the URL path** | in the body via `model_name` |
| Text-to-video | `POST /text-to-video/kling-3.0` | `POST /v1/videos/text2video` |
| Image-to-video | `POST /image-to-video/kling-3.0` | `POST /v1/videos/image2video` |
| Query task | `GET /tasks?task_ids=…` | `GET /v1/videos/text2video/{id}` |
| Task id field | `data.id` | `data.task_id` |
| Status field | `data.status` | `data.task_status` |
| Status values | `submitted / processing / succeeded / failed` | `submitted / processing / succeed / failed` |
| Result field | `data.outputs[]` | `data.task_result` |
| Applies to | **Kling 3.0 / 3.0 Turbo / 3.0 Omni** | v1.x / v2.x models |

Rule of thumb: **if you're using a Kling 3.x model, use the new path-style API.** The legacy endpoints are for older models (and the image API still uses the legacy shape even for newer image models — see §6).

---

## 4. Core endpoints (new API, Kling 3.x)

Base URL: `https://api-singapore.klingai.com`

| Purpose | Method + Path |
|---|---|
| Text → video | `POST /text-to-video/kling-3.0` |
| Text → video (fast) | `POST /text-to-video/kling-3.0-turbo` |
| Image → video | `POST /image-to-video/kling-3.0` |
| Video / multi-input → video (Omni: video refs, editing) | `POST /omni-video/kling-3.0-omni` |
| Query task(s) by id | `GET /tasks?task_ids=a,b` (or `?external_task_ids=…`) |
| List/search tasks (cursor) | `POST /tasks` |
| Image generation (legacy shape) | `POST /v1/images/generations` |

Pattern: `/text-to-video/{model}` where `{model}` ∈ `kling-3.0`, `kling-3.0-turbo`, `kling-3.0-omni`. Same idea for `/image-to-video/{model}`.

### 4.1 Text-to-video — request body

```jsonc
{
  "prompt": "A girl sits on a train, looking out the window, melancholic, head swaying with the train.",
  "settings": {
    "resolution": "720p",        // "720p" | "1080p" | "4k"   (default 720p)
    "aspect_ratio": "16:9",      // "16:9" | "9:16" | "1:1"   (default 16:9)
    "duration": 5,               // 3..15 seconds              (default 5)
    "audio": "off",              // "off" | "native"           (default off)
    "multi_shot": true           // allow multi-shot prompts   (default true)
  },
  "options": {
    "callback_url": "",          // optional webhook on status change
    "external_task_id": "",      // your own id, must be unique per account
    "watermark_info": { "enabled": false }
  }
}
```

- `prompt`: ≤ 3072 chars (recommend ≤ 2500).
- `duration` is an **int** 3–15.
- `audio: "native"` costs more (see pricing) — leave `off` while you're learning.

### 4.2 Image-to-video — request body

```jsonc
{
  "contents": [
    { "type": "prompt", "text": "The camera slowly pushes in as the character turns toward the lens." },
    { "type": "first_frame", "url": "https://…/keyframe.png" },   // required for i2v
    { "type": "last_frame", "url": "https://…/endframe.png" }     // optional (start+end frame control)
  ],
  "settings": {
    "resolution": "720p",
    "duration": 5,
    "audio": "off",
    "multi_shot": false
  },
  "options": { "callback_url": "", "external_task_id": "", "watermark_info": { "enabled": false } }
}
```

- `contents[].type` values: `prompt`, `first_frame`, `last_frame`, `element` (Element library refs, referenced in the prompt as `@name`).
- Image format: `.jpg/.jpeg/.png`, ≤ 50 MB, ≥ 300px, aspect ratio between 1:2.5 and 2.5:1.
- First-frame-only is fine; last-frame-only is **not** supported.

### 4.3 Response (create task)

```json
{
  "code": 0,
  "message": "string",
  "request_id": "string",
  "data": {
    "id": "893605946402811985",   // <-- the task id you poll with
    "status": "submitted",
    "create_time": 1781080778802,
    "update_time": 1781080794151,
    "external_id": ""
  }
}
```

`code: 0` = success. Grab `data.id`.

### 4.4 Poll for the result

```bash
curl -s 'https://api-singapore.klingai.com/tasks?task_ids=893605946402811985' \
  -H 'Authorization: Bearer $KLING_API_KEY'
```

When `data[0].status == "succeeded"`, the video is in:

```
data[0].outputs[0].url        # the video file (expires in 30 days — download it!)
data[0].outputs[0].duration   # seconds
data[0].outputs[0].watermark_url   # if you asked for a watermark
```

`outputs[]` items have a `type`: `video`, `image`, `audio`, `element`, `voice` — so the same task shape covers audio and element results too. There's also a `billing[]` array telling you exactly how many units/cash were deducted.

---

## 5. The async pattern (this is the whole mental model)

```
1. POST /text-to-video/kling-3.0      →  { data.id }
2. loop: GET /tasks?task_ids=<id>     →  data[0].status
       submitted → processing → succeeded | failed
3. on "succeeded": download outputs[0].url  (30-day expiry)
```

Typical generation times: Standard-mode clips finish in ~30–60s; 4K/long clips take minutes. Use a **callback_url** if you don't want to poll, or poll every ~2–5s.

---

## 6. Image generation (for storyboard keyframes)

Image gen still uses the **legacy** endpoint shape with a `model_name` field:

```bash
curl -s 'https://api-singapore.klingai.com/v1/images/generations' \
  -H 'Authorization: Bearer $KLING_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model_name": "kling-v3",
    "prompt": "Film still, wide shot, a small boat on a misty lake at dawn, cinematic lighting",
    "aspect_ratio": "16:9",
    "resolution": "1k",
    "n": 1
  }'
```

- `model_name` ∈ `kling-v1`, `kling-v1-5`, `kling-v2`, `kling-v2-new`, `kling-v2-1`, `kling-v3`.
- `resolution`: `1k` | `2k`. `n`: 1–9 images. `aspect_ratio`: `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3`, `21:9`.
- Poll via `GET /v1/images/generations/{id}` → `data.task_result.images[].url`.
- `image` (url or base64) + `image_reference` (`subject`/`face`) enables image-to-image.

---

## 7. Models & pricing (video)

Official pricing, billed **per second**. Video unit: **1 Unit = $0.14**.

### Kling 3.0 — `kling-3.0` (current generation, your default)

| Config | 720p | 1080p | 4K |
|---|---|---|---|
| No audio | **$0.084/s** | $0.112/s | $0.42/s |
| Native audio | $0.126/s | $0.168/s | $0.42/s |

### Kling 3.0 Turbo — `kling-3.0-turbo` (faster iteration, audio always on)

| Config | 720p | 1080p |
|---|---|---|
| Native audio | $0.112/s | $0.14/s |

### Kling 3.0 Omni — `kling-3.0-omni` (adds video input / editing / element consistency)

| Config | 720p | 1080p | 4K |
|---|---|---|---|
| No video input, no audio | $0.084/s | $0.112/s | $0.42/s |
| No video input, native audio | $0.112/s | $0.14/s | $0.42/s |
| With video input, no audio | $0.126/s | $0.168/s | $0.42/s |

### Older models (legacy endpoints, for context — you can ignore these while learning)

- `kling-v2-6` (Dec 2025, first with native audio): std ≈ $0.042/s no audio — cheapest in absolute terms, but previous generation.
- `kling-v2-5-turbo`, `kling-v2-1`, `kling-v1-6`, … : progressively older/cheaper, superseded.

### Image pricing (1 Unit = $0.0035)

| Model | Price |
|---|---|
| `kling-v3` (1K/2K) | $0.028 / image |
| `kling-v3-omni` (1K/2K) | $0.028 / image (4K: $0.056) |
| `kling-v2-1` text-to-image | $0.014 / image (cheapest images) |

**Cost cheat-sheet (Kling 3.0, 720p, no audio):**

| Duration | Cost |
|---|---|
| 5s | $0.42 |
| 10s | $0.84 |
| 15s | $1.26 |

---

## 8. Storyboarding (the feature you care about)

Kling 3.0 does **multi-shot in one request** via a templated prompt. Format:

```
shot <n>, <m>s, <words>; shot <n>, <m>s, <words>; ...
```

- `n` = shot number (1–6 shots supported).
- `m` = that shot's duration in seconds (≥ 1s each; **sum must equal `settings.duration`**).
- `words` = that shot's prompt (≤ 512 chars).

Example (a 10s, 4-shot storyboard):

```
shot 1, 3s, wide establishing shot of a lighthouse on a cliff at golden hour, waves crashing;
shot 2, 2s, medium shot of a woman in a yellow raincoat walking up the cliff path, wind in her hair;
shot 3, 2s, close-up of her face as she looks up at the lighthouse, determined expression;
shot 4, 3s, she reaches the top and the lighthouse beam sweeps across the sea, dramatic
```

Set `settings.duration: 10` and `settings.multi_shot: true`.

Two storyboarding styles to experiment with:

1. **Prompt-only multi-shot** — one text-to-video call, the model invents continuity between your shots. Fastest, cheapest.
2. **Keyframe-driven** — generate each keyframe with the image API (§6), then animate each with image-to-video (§4.2), optionally using `first_frame` + `last_frame` to control start and end exactly. More control, more calls (more cost), better for precise boards.

For **consistent characters** across shots, use the **Elements** system (Kling 3.0 Omni): create an Element from reference images, then reference it in prompts as `@name`. See `https://kling.ai/document-api/api/video/3-0-omni/elements`.

---

## 9. Suggested experiment ladder (small → big)

Start cheap, keep everything 720p / no audio / 5s until you're confident:

1. **Smoke test** — one 5s text-to-video (`kling-3.0`), 720p, no audio. Verify create → poll → download works end-to-end. (~$0.42)
2. **Param sweep** — same prompt, vary `aspect_ratio` (16:9 vs 9:16 vs 1:1) and `duration` (5 vs 10). Learn what "good" output looks like.
3. **Image-to-video** — generate a keyframe (image API), animate it. Compare prompt-only vs keyframe-driven.
4. **Two-shot storyboard** — the `shot n, m, …;` format with 2 shots. Then scale to 4–6 shots.
5. **Start+end frame** — add `last_frame` to image-to-video for exact start/end control.
6. **Quality bump** — same storyboard at 1080p ($0.112/s), then add `audio: "native"` to hear the difference.
7. **Elements (character consistency)** — switch to `kling-3.0-omni`, create an Element, reuse the character across shots.
8. **Production plumbing** — add `callback_url`, `external_task_id`, persistent storage of results, and a retry loop.

---

## 10. Error codes (condensed)

| HTTP | Code | Meaning |
|---|---|---|
| 200 | 0 | Success |
| 401 | 1000–1004 | Auth missing/invalid/expired |
| 429 | 1100–1102 | Account issue: arrears, resource pack exhausted/expired |
| 403 | 1103 | No permission for this API/model |
| 400 | 1200–1201 | Invalid request parameters |
| 404 | 1202–1203 | Wrong method / resource (model) not found |
| 400 | 1300–1301 | Blocked by policy / content safety |
| 429 | 1302–1304 | Rate limit / concurrency / IP whitelist |
| 5xx | 5000–5002 | Server error / maintenance / timeout (retry) |

Note: failed generations do **not** deduct units.

---

## 11. Gotchas & tips

- **Download results immediately** — URLs are "hotlink protected" and deleted after 30 days.
- **The `duration` must equal the sum of multi-shot durations** — mismatches cause `1200/1201` errors.
- **`external_task_id` must be unique per account** — useful to reconcile async results later.
- **Resource packages don't roll over** and expire — don't over-buy while prototyping; the Trial package + a small package is plenty.
- **Concurrency is capped by your package** — hitting it returns `1303`. Poll with backoff, don't fire a hundred tasks at once.
- **Watermark**: `watermark_info.enabled` — Kling is generally watermark-free by default (`false`); custom watermarks aren't supported.
- **Docs are LLM-friendly**: every page has a `.md` version, and the full index is at `https://kling.ai/document-api/llms.txt`.

---

## 12. Reference links

- Developer console / API keys: <https://kling.ai/dev/api-key>
- Pricing: <https://kling.ai/dev/pricing>
- Docs index (Markdown): <https://kling.ai/document-api/llms.txt>
- Auth: <https://kling.ai/document-api/api/get-started/authentication>
- Error codes: <https://kling.ai/document-api/api/get-started/error-codes>
- Text-to-video (3.0/3.0 Omni): <https://kling.ai/document-api/api/video/3-0-omni/text-to-video>
- Image-to-video (3.0/3.0 Omni): <https://kling.ai/document-api/api/video/3-0-omni/image-to-video>
- Omni video generation: <https://kling.ai/document-api/api/video/3-0-omni/video-omni>
- Kling 3.0 model user guide (multi-shot format): <https://kling.ai/quickstart/klingai-video-3-model-user-guide>

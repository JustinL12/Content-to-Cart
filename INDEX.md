# Grocery List AI — Project Index

Index of project source files (excluding `venv`).

---

## Entry point

| File | Description |
|------|-------------|
| **main.py** | Entry point. Accepts YouTube, YouTube Shorts, TikTok, or Instagram Reels URL. Downloads video, gets transcript (API or Whisper), extracts ingredients, frames, YOLO cross-ref, prints grocery list. |

---

## Transcript & ingredients

| File | Description |
|------|-------------|
| **url_detection.py** | `get_platform(url)` — detects YouTube, YouTube Shorts, TikTok, Instagram Reels. `has_native_transcript(platform)` for API vs Whisper. |
| **transcript.py** | Unified `get_transcript(url, video_path=None)`: YouTube uses `youtube_transcript_api` when available; TikTok/Reels and fallback use Whisper on downloaded file. `extract_youtube_video_id(url)` for watch/shorts. |
| **whisper_transcript.py** | `transcribe_with_whisper(video_or_audio_path, model_name="base")` — OpenAI Whisper for TikTok, Reels, and YouTube when captions missing. |
| **ingredient_extractor.py** | Extracts grocery ingredients and quantities from transcript text via Ollama (e.g. `llama3`). Returns a list of `{"ingredient", "quantity"}`. Handles substitutes and generalization. |

---

## Video & frames

| File | Description |
|------|-------------|
| **video_utils.py** | `download_video(url, output="video.mp4", cookies_file=None)` via yt-dlp. Uses flexible format for TikTok/Instagram; optional `YT_DLP_COOKIES_FILE` or `cookies_file` for Instagram (and sometimes TikTok) when login is required. `extract_frames(...)` with shorter interval for videos &lt; 90s. |

---

## Vision / detection

| File | Description |
|------|-------------|
| **yolo_detector.py** | Roboflow FOOD-INGREDIENTS model (120 classes): `detect_food(image_path)` returns list of detected ingredient class names (egg, rice, vegetables, etc.). Uses `inference` package; set `ROBOFLOW_API_KEY` for first-time model download. |
| **vision_pipline.py** | `process_frames(frame_folder)` runs YOLO on each frame and aggregates detections with a `Counter` (vote-style). |

---

## Data / output (runtime)

- **video.mp4** — Downloaded video (from main flow).
- **frames/** — Extracted frame images (e.g. `frame_0.jpg`, `frame_1.jpg`, …).

---

## Dependencies (from code)

- `youtube_transcript_api` — YouTube transcript when available
- `openai-whisper` — transcript for TikTok, Instagram Reels, and YouTube when captions disabled
- `requests` — Ollama API (ingredient_extractor)
- `yt-dlp` — video download (YouTube, Shorts, TikTok, Instagram)
- `opencv-python` (cv2) — frame extraction
- `inference` — Roboflow inference (yolo_detector; food-ingredients model)

Ollama must be running locally (e.g. `http://localhost:11434`) for ingredient extraction. For first-time use of the food-ingredient model, set `ROBOFLOW_API_KEY` (get a free key at roboflow.com). FFmpeg is required for Whisper. **TikTok/Instagram:** If download fails with “login required”, export cookies from your browser (Netscape format) and set `YT_DLP_COOKIES_FILE` to the file path, or pass `cookies_file=...` to `download_video`. Keep yt-dlp updated (`pip install -U yt-dlp`) for best compatibility.

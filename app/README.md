# Ingredient Extractor — Web App

Web UI: paste a **YouTube, YouTube Shorts, TikTok, or Instagram Reels** URL and get a bullet list of ingredients extracted from the video’s transcript (with quantities when available).

- **Frontend:** React (Vite)
- **Backend:** Python FastAPI — uses Neon PostgreSQL cache (per-platform) when `DATABASE_URL_*` are set in `.env`; checks cache first, then downloads video when needed, gets transcript (YouTube API or Whisper), runs `ingredient_extractor`, and saves results to the database for future requests

**TikTok / Instagram Reels:** If download fails with “login required”, set env `YT_DLP_COOKIES_FILE` to the path of a Netscape-format cookies file (export from your browser after logging in). Keep yt-dlp updated: `pip install -U yt-dlp`.

---

## Requirements

- **Backend:** Python 3.10+ with the project’s virtualenv (so `ingredient_extractor` and its deps are available). Ollama running locally with a model (e.g. `llama3`) for the extractor.
- **Frontend:** Node.js 18+ and npm.

---

## Dependencies

### Backend (`app/backend/`)

- `fastapi` — API server
- `uvicorn[standard]` — ASGI server
- `requests` — used by `ingredient_extractor` (Ollama)
- `youtube_transcript_api` — used by `transcript.get_transcript` (YouTube)
- `psycopg2-binary` — used by `db` for Neon PostgreSQL cache
- `yt-dlp` — used by `description_fetcher` for video metadata (title/thumbnail) when saving to cache
- `python-dotenv` — loads `.env` from project root for `DATABASE_URL_*`

The backend also uses `transcript`, `ingredient_extractor`, `db`, and `description_fetcher` from the **project root** (no copy of that logic). Ensure `.env` in the project root contains `DATABASE_URL_YOUTUBE`, `DATABASE_URL_SHORTS`, `DATABASE_URL_TIKTOK`, and `DATABASE_URL_INSTAGRAM` (or a single `DATABASE_URL`) for the cache to be used.

### Frontend (`app/frontend/`)

- `react`, `react-dom` — UI
- `vite`, `@vitejs/plugin-react` — build and dev server

---

## How to run

Run **both** backend and frontend (two terminals).

### 1. Backend

From the **project root** (parent of `app/`), with your venv activated:

```bash
# From project root (Grocery_List-ai)
pip install -r app/backend/requirements.txt
uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000
```

API will be at `http://localhost:8000`. Docs: `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/extract` and `/health` to the backend.

### 3. Optional: run backend from `app/backend`

If you prefer to run from `app/backend`, the app still imports from the project root:

```bash
cd app/backend
pip install -r requirements.txt
# From project root: python -m uvicorn app.backend.main:app --reload --port 8000
# Or from app/backend with PYTHONPATH set to project root:
# Windows (PowerShell): $env:PYTHONPATH="D:\Grocery_List-ai"; uvicorn main:app --reload --port 8000
# Linux/macOS: PYTHONPATH=/path/to/Grocery_List-ai uvicorn main:app --reload --port 8000
```

Recommended: run `uvicorn` from **project root** as in step 1 so the import works without extra env.

---

## Example request

**Endpoint:** `POST /extract`  
**Body (JSON):** Send a YouTube video URL. The backend fetches the transcript, then runs the ingredient extractor.

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Example response:**

```json
{
  "ingredients": [
    { "ingredient": "eggs", "quantity": "2" },
    { "ingredient": "flour", "quantity": "1 cup" },
    { "ingredient": "butter", "quantity": "1 tbsp" },
    { "ingredient": "salt", "quantity": "unknown" }
  ]
}
```

**cURL example:**

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://www.youtube.com/watch?v=VIDEO_ID\"}"
```

---

## Project structure

```
app/
  README.md           # This file
  backend/
    main.py           # FastAPI app: get_transcript(url) then extract_ingredients_with_quantity(transcript)
    requirements.txt
  frontend/
    index.html
    package.json
    vite.config.js
    src/
      main.jsx
      App.jsx
      App.css
      index.css
```

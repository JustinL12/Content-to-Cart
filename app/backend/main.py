"""
FastAPI backend for ingredient extraction.
Supports YouTube, YouTube Shorts, TikTok, and Instagram Reels.
Uses Neon PostgreSQL cache (per-platform) when configured; otherwise runs transcript + extraction.
Downloads video when needed and uses Whisper for transcript when no API is available.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add project root for imports and load .env from project root
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env so DATABASE_URL_* are available for db module
_env_file = _ROOT / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_env_file), override=False, encoding="utf-8")
    except ImportError:
        pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from transcript import get_transcript
from ingredient_extractor import extract_ingredients_with_quantity
from url_detection import get_platform
from video_utils import download_video

try:
    from db import get_cached_ingredients, save_video_result, init_db
    _db_available = True
except Exception:
    _db_available = False

try:
    from description_fetcher import get_video_metadata
except Exception:
    get_video_metadata = None

app = FastAPI(title="Ingredient Extractor API")


@app.on_event("startup")
def startup():
    """Ensure video_cache tables exist on each configured Neon branch."""
    if _db_available:
        try:
            init_db()
        except Exception:
            pass


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    url: str


class IngredientItem(BaseModel):
    ingredient: str
    quantity: str


class ExtractResponse(BaseModel):
    ingredients: list[IngredientItem]
    title: str | None = None
    thumbnail: str | None = None


def _ingredient_list_to_response(
    items: list, title: str | None = None, thumbnail: str | None = None
) -> ExtractResponse:
    """Build API response from list of dicts with ingredient/quantity."""
    ingredients = [
        IngredientItem(
            ingredient=item.get("ingredient", ""),
            quantity=item.get("quantity", "unknown"),
        )
        for item in (items or [])
        if isinstance(item, dict) and item.get("ingredient")
    ]
    return ExtractResponse(ingredients=ingredients, title=title, thumbnail=thumbnail)


@app.post("/extract", response_model=ExtractResponse)
def extract_ingredients(req: ExtractRequest):
    """Get transcript from URL (YouTube, Shorts, TikTok, Instagram Reels), then extract ingredients.
    Uses database cache when configured: returns cached result if URL was processed before; otherwise
    runs extraction and saves to the platform's Neon branch."""
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    platform = get_platform(url)
    if platform == "unknown":
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL. Use YouTube, YouTube Shorts, TikTok, or Instagram Reels.",
        )

    # Database cache: if this URL was processed before, return cached ingredients (no download, no AI)
    if _db_available:
        cached = get_cached_ingredients(url, platform)
        if cached and cached.get("ingredients"):
            return _ingredient_list_to_response(
                cached["ingredients"],
                title=cached.get("title"),
                thumbnail=cached.get("thumbnail") or None,
            )

    temp_path = None
    try:
        # YouTube: try API first (no download); TikTok/Reels or API failure → download and Whisper
        transcript = None
        if platform in ("youtube", "youtube_shorts"):
            try:
                transcript = get_transcript(url)  # API only; no video_path
            except (ValueError, Exception):
                transcript = None
        if not transcript:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                temp_path = f.name
            download_video(url, output=temp_path)
            if not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0:
                raise HTTPException(status_code=502, detail="Failed to download video")
            transcript = get_transcript(url, video_path=temp_path)
        if not (transcript or transcript.strip()):
            raise HTTPException(status_code=422, detail="No speech detected in video")
        raw = extract_ingredients_with_quantity(transcript)
        ingredients = [
            IngredientItem(
                ingredient=item.get("ingredient", ""),
                quantity=item.get("quantity", "unknown"),
            )
            for item in raw
            if isinstance(item, dict) and item.get("ingredient")
        ]
        # Save to database for future cache hits (title/thumbnail from metadata when available)
        title, thumbnail = "(no title)", ""
        if _db_available and ingredients:
            if get_video_metadata:
                try:
                    meta = get_video_metadata(url)
                    title = (meta.get("title") or "").strip() or title
                    thumbnail = (meta.get("thumbnail") or "").strip()
                except Exception:
                    pass
            save_video_result(
                url,
                title,
                [{"ingredient": i.ingredient, "quantity": i.quantity} for i in ingredients],
                thumbnail,
                platform,
            )
        return ExtractResponse(ingredients=ingredients, title=title or None, thumbnail=thumbnail or None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


@app.get("/health")
def health():
    return {"status": "ok", "database": "connected" if _db_available else "disabled"}

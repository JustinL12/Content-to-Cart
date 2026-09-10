"""
Neon PostgreSQL cache for video results.
One Neon branch per platform (YouTube, Shorts, TikTok, Instagram) for faster lookups.
Each branch has one video_cache table. Stores: URL, title, thumbnail, ingredient_list (JSON).
"""

import os
import re
import json
from pathlib import Path
from typing import Optional

# Platform identifier for branch selection (must match url_detection.get_platform)
Platform = str  # "youtube" | "youtube_shorts" | "tiktok" | "instagram_reels"

_env_path = Path(__file__).resolve().parent / ".env"
_ENV_KEYS = (
    "DATABASE_URL",
    "DATABASE_URL_YOUTUBE",
    "DATABASE_URL_SHORTS",
    "DATABASE_URL_TIKTOK",
    "DATABASE_URL_INSTAGRAM",
)

def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip().lstrip("\ufeff")
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip().upper().replace("-", "_")
                value = value.strip().strip("'\"")
                if key in _ENV_KEYS and value:
                    os.environ[key] = value
    except Exception:
        pass

_load_env_file(_env_path)
if not os.environ.get("DATABASE_URL"):
    _load_env_file(Path.cwd() / ".env")

try:
    from dotenv import load_dotenv
    load_dotenv(str(_env_path), override=True, encoding="utf-8")
except ImportError:
    pass

# Per-platform branch URLs; fallback to DATABASE_URL if a branch is not set
def _get_url_for_platform(platform: Platform) -> Optional[str]:
    key = {
        "youtube": "DATABASE_URL_YOUTUBE",
        "youtube_shorts": "DATABASE_URL_SHORTS",
        "tiktok": "DATABASE_URL_TIKTOK",
        "instagram_reels": "DATABASE_URL_INSTAGRAM",
    }.get(platform)
    url = (os.environ.get(key) if key else "").strip() or os.environ.get("DATABASE_URL", "").strip()
    return url or None

# Canonical URL form for cache key: same video => same key (e.g. shorts vs watch)
_YOUTUBE_VIDEO_ID = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


def _normalize_cache_url(url: str) -> str:
    """Normalize URL to a canonical form so lookup and store match (e.g. shorts vs watch)."""
    url = (url or "").strip()
    if not url:
        return url
    m = _YOUTUBE_VIDEO_ID.search(url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return url

# Ingredient list is stored as JSON: list of {"ingredient": str, "quantity": str, "caption_seen": bool|None}


def get_connection(platform: Platform):
    """Return a connection to the Neon branch for this platform. Raises if no URL configured."""
    url = _get_url_for_platform(platform)
    if not url:
        raise ValueError(
            f"No DATABASE_URL for platform '{platform}'. Set DATABASE_URL_{platform.upper()} or DATABASE_URL in .env."
        )
    import psycopg2
    return psycopg2.connect(url)


def init_db():
    """Create the video_cache table on each configured Neon branch (one per platform)."""
    import psycopg2
    for platform in ("youtube", "youtube_shorts", "tiktok", "instagram_reels"):
        url = _get_url_for_platform(platform)
        if not url:
            continue
        try:
            conn = psycopg2.connect(url)
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS video_cache (
                            url TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            thumbnail TEXT,
                            ingredient_list JSONB NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
                    cur.execute("""
                        DO $$ BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'video_cache' AND column_name = 'thumbnail'
                            ) THEN
                                ALTER TABLE video_cache ADD COLUMN thumbnail TEXT;
                            END IF;
                        END $$
                    """)
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass


def get_cached_ingredients(url: str, platform: Platform) -> Optional[list]:
    """
    If this URL was processed before on the platform's branch, return the stored ingredient list.
    Otherwise return None.
    """
    url = _normalize_cache_url(url)
    if not url:
        return None
    if not _get_url_for_platform(platform):
        return None
    try:
        conn = get_connection(platform)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT title, thumbnail, ingredient_list FROM video_cache WHERE url = %s",
                    (url,),
                )
                row = cur.fetchone()
            if row is None:
                return None
            title, thumbnail, ingredient_list_json = row
            data = json.loads(ingredient_list_json) if isinstance(ingredient_list_json, str) else ingredient_list_json
            return {"title": title, "thumbnail": thumbnail or "", "ingredients": data}
        finally:
            conn.close()
    except Exception:
        return None


def save_video_result(
    url: str, title: str, ingredient_list: list, thumbnail: str = "", platform: Optional[Platform] = None
) -> None:
    """Store URL, title, thumbnail, and ingredient list on the platform's Neon branch."""
    if not platform:
        return
    url = _normalize_cache_url(url)
    title = (title or "").strip() or "(no title)"
    thumbnail = (thumbnail or "").strip()
    if not url or not _get_url_for_platform(platform):
        return
    payload = [
        {
            "ingredient": item.get("ingredient", ""),
            "quantity": item.get("quantity", "unknown"),
            "caption_seen": item.get("caption_seen"),
        }
        for item in ingredient_list
    ]
    json_str = json.dumps(payload)
    try:
        conn = get_connection(platform)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO video_cache (url, title, thumbnail, ingredient_list)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (url) DO UPDATE SET
                        title = EXCLUDED.title,
                        thumbnail = EXCLUDED.thumbnail,
                        ingredient_list = EXCLUDED.ingredient_list,
                        created_at = NOW()
                    """,
                    (url, title, thumbnail or None, json_str),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

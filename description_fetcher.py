"""
Fetch video description via yt-dlp (metadata only, no download).
Works for YouTube, Shorts, TikTok, Instagram Reels.
Detect when description has an explicit ingredient/recipe list (header + list format).
"""

import re
import yt_dlp

# Section headers that indicate an explicit recipe/ingredient list
_EXPLICIT_HEADERS = re.compile(
    r"\b(Recipe|Ingredients|Ingredient\s+list|For\s+the\s+\w+)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Lines that look like ingredient entries: quantity then item (e.g. "900g Chicken", "2 tbsp oil", "Pinch salt", "12 grams cilantro")
_INGREDIENT_LINE = re.compile(
    r"^\s*"
    r"(?:\d+\.?\d*\s*(?:g|grams?|kg|ml|tbsp|tsp|cup|cups|oz)\b|"
    r"\d+\s+(?:medium|large|small)\s+|"
    r"\(?\s*\d+\s*(?:g|tbsp|tsp|cloves?|each)\s*\)?|"
    r"[Pp]inch\b)"
    r".{2,}",  # at least some ingredient text after
    re.MULTILINE,
)


def has_explicit_ingredient_list(description: str) -> bool:
    """
    Return True if the description contains an explicit ingredient/recipe list:
    a clear section header (Recipe, Ingredients, For the X:) and multiple
    list-style lines with quantities (e.g. "900g chicken", "2 tbsp oil").
    """
    if not description or not description.strip():
        return False
    text = description.strip()
    if not _EXPLICIT_HEADERS.search(text):
        return False
    ingredient_lines = _INGREDIENT_LINE.findall(text)
    return len(ingredient_lines) >= 3


def get_video_metadata(url: str) -> dict:
    """
    Return dict with 'description' and 'title' for the given URL.
    Does not download the video. Empty strings on error/unavailable.
    """
    url = (url or "").strip()
    if not url:
        return {"description": "", "title": "", "thumbnail": ""}
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return {"description": "", "title": "", "thumbnail": ""}
        thumbnail = (info.get("thumbnail") or "").strip()
        if not thumbnail and info.get("thumbnails"):
            # Prefer highest resolution
            thumbs = sorted(
                (t for t in info["thumbnails"] if t.get("url")),
                key=lambda t: (t.get("width") or 0) * (t.get("height") or 0),
                reverse=True,
            )
            if thumbs:
                thumbnail = (thumbs[0].get("url") or "").strip()
        return {
            "description": (info.get("description") or "").strip(),
            "title": (info.get("title") or "").strip(),
            "thumbnail": thumbnail,
        }
    except Exception:
        return {"description": "", "title": "", "thumbnail": ""}


def get_video_description(url: str) -> str:
    """
    Return the video description for the given URL, or empty string if
    unavailable or on error. Does not download the video.
    """
    return get_video_metadata(url).get("description", "")

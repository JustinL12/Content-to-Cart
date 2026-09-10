"""
Detect supported media platform from URL: YouTube (long + Shorts), TikTok, Instagram Reels.
"""

import re
from typing import Literal

Platform = Literal["youtube", "youtube_shorts", "tiktok", "instagram_reels", "unknown"]

# Patterns (order can matter for overlapping domains)
_YOUTUBE_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&\s]+)",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([^/?&\s]+)",
    r"(?:https?://)?youtu\.be/([^/?&\s]+)",
]
_TIKTOK_PATTERNS = [
    r"(?:https?://)?(?:www\.)?tiktok\.com/[^/]+/video/(\d+)",
    r"(?:https?://)?(?:vm\.)?tiktok\.com/([A-Za-z0-9]+)",
]
_INSTAGRAM_PATTERNS = [
    r"(?:https?://)?(?:www\.)?instagram\.com/reel/([A-Za-z0-9_-]+)",
    r"(?:https?://)?(?:www\.)?instagram\.com/p/([A-Za-z0-9_-]+)",
]


def get_platform(url: str) -> Platform:
    """Return platform identifier for the given URL."""
    if not url or not url.strip():
        return "unknown"
    u = url.strip().lower()
    for _ in _YOUTUBE_PATTERNS:
        if re.search(_, u, re.IGNORECASE):
            return "youtube_shorts" if "/shorts/" in u else "youtube"
    for _ in _TIKTOK_PATTERNS:
        if re.search(_, u):
            return "tiktok"
    for _ in _INSTAGRAM_PATTERNS:
        if re.search(_, u):
            return "instagram_reels"
    return "unknown"


def has_native_transcript(platform: Platform) -> bool:
    """True if we can try a native transcript API (e.g. YouTube) before Whisper."""
    return platform == "youtube" or platform == "youtube_shorts"


def is_youtube(platform: Platform) -> bool:
    return platform in ("youtube", "youtube_shorts")

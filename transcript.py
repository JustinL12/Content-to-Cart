"""
Unified transcript: YouTube (long + Shorts) via API when available;
TikTok, Instagram Reels, and fallback use Whisper on downloaded video.
"""

import re
from url_detection import get_platform, has_native_transcript
from whisper_transcript import transcribe_with_whisper


def extract_youtube_video_id(url: str) -> str:
    """Extract video ID from YouTube watch or Shorts URL."""
    url = (url or "").strip()
    # watch: ?v=ID
    m = re.search(r"[?&]v=([^&\s]+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    # shorts: /shorts/ID
    m = re.search(r"/shorts/([^/?&\s]+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    # youtu.be/ID
    m = re.search(r"youtu\.be/([^/?&\s]+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    raise ValueError("Invalid or unsupported YouTube URL")


def get_transcript_youtube(url: str) -> str | None:
    """Fetch transcript from YouTube API if available. Returns None on failure."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        video_id = extract_youtube_video_id(url)
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        return " ".join([item.text for item in transcript]) if transcript else None
    except Exception:
        return None


def get_transcript(
    url: str,
    video_path: str | None = None,
    *,
    use_whisper_if_no_api: bool = True,
    whisper_model: str = "base",
) -> str:
    """
    Get transcript for a media URL.

    - YouTube (long + Shorts): tries YouTube transcript API first; if that fails
      and video_path is provided, falls back to Whisper.
    - TikTok / Instagram Reels: requires video_path; uses Whisper.

    Raises ValueError if video_path is required but not provided or file missing.
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("URL is required")

    platform = get_platform(url)

    # Try native API for YouTube
    if has_native_transcript(platform):
        text = get_transcript_youtube(url)
        if text:
            return text
        if not use_whisper_if_no_api:
            raise ValueError("YouTube transcript not available (captions may be disabled)")
        # Fall through to Whisper if video_path provided

    # Whisper path: need local file
    if not video_path:
        raise ValueError(
            "Transcript for this URL requires a downloaded video file. "
            "Download the video first and pass video_path."
        )
    return transcribe_with_whisper(video_path, model_name=whisper_model, language="en")

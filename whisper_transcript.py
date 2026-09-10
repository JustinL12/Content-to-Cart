"""
Transcribe audio/video file using OpenAI Whisper when native transcript isn't available
(TikTok, Instagram Reels, or YouTube when captions are disabled).
"""

import os
import shutil


def _ensure_ffmpeg_on_path():
    """
    Ensure ffmpeg is available for Whisper's subprocess.
    Returns the ffmpeg executable path to use, or None if system ffmpeg is on PATH.
    When using imageio-ffmpeg's bundled binary (e.g. in a venv), we must pass this
    path to Whisper because on Windows the bundle is named e.g. ffmpeg-win-x86_64-v7.1.exe,
    so adding its dir to PATH does not make the "ffmpeg" command work.
    """
    if shutil.which("ffmpeg"):
        return None
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    raise RuntimeError(
        "FFmpeg is required for transcription but was not found. "
        "Install FFmpeg and add it to your system PATH (https://ffmpeg.org/download.html), "
        "or install the imageio-ffmpeg package in this environment: pip install imageio-ffmpeg"
    )


def transcribe_with_whisper(
    video_or_audio_path: str,
    model_name: str = "base",
    language: str | None = "en",
) -> str:
    """
    Transcribe a local video or audio file with Whisper.
    Requires: pip install openai-whisper; FFmpeg on PATH.
    """
    if not os.path.isfile(video_or_audio_path):
        raise FileNotFoundError(f"Media file not found: {video_or_audio_path}")

    ffmpeg_exe = _ensure_ffmpeg_on_path()

    try:
        import whisper
        import whisper.audio as whisper_audio
    except ImportError:
        raise ImportError(
            "openai-whisper is required for TikTok/Instagram/Reels. "
            "Install with: pip install openai-whisper"
        )

    if ffmpeg_exe is not None:
        _orig_run = whisper_audio.run
        def _patched_run(cmd, *args, **kwargs):
            if isinstance(cmd, (list, tuple)) and len(cmd) > 0 and cmd[0] == "ffmpeg":
                cmd = [ffmpeg_exe] + list(cmd)[1:]
            return _orig_run(cmd, *args, **kwargs)
        whisper_audio.run = _patched_run

    device = "cuda" if _cuda_available() else "cpu"
    model = whisper.load_model(model_name, device=device)
    fp16 = device == "cuda"

    try:
        result = model.transcribe(
            video_or_audio_path,
            language=language,
            fp16=fp16,
            verbose=False,
        )
    except (FileNotFoundError, OSError) as e:
        if getattr(e, "winerror", None) == 2 or getattr(e, "errno", None) == 2:
            raise RuntimeError(
                "FFmpeg is required for transcription but was not found. "
                "Install FFmpeg and add it to your system PATH (https://ffmpeg.org/download.html)."
            ) from e
        raise

    text = (result.get("text") or "").strip()
    return text


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False

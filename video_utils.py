import json
import os
import subprocess
import sys
import time

import cv2


# Prefer mp4; merge video+audio if needed; fallback to best available (TikTok/Instagram often use different format IDs)
_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"

# Minimum size (bytes) to consider a file a valid video (avoid fragments/audio-only misnamed as .mp4)
_MIN_VIDEO_SIZE = 50 * 1024


def _find_ytdlp_output(requested_path: str, out_dir: str) -> str | None:
    """
    When yt-dlp merges formats or picks a single format, it may write to e.g.
    video.f401.mp4, video.f299.mp4, video.fdash-xxx.mp4 instead of video.mp4.
    Find the actual .mp4 file with the same stem and return its path, or None.
    """
    base = os.path.splitext(os.path.basename(requested_path))[0]
    if not os.path.isdir(out_dir):
        return None
    candidates = []
    for name in os.listdir(out_dir):
        if not name.startswith(base) or not name.endswith(".mp4"):
            continue
        path = os.path.join(out_dir, name)
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        if size < _MIN_VIDEO_SIZE:
            continue
        candidates.append((path, size))
    if not candidates:
        return None
    # Prefer the single file that matches the requested name; else pick largest (merged/best)
    for path, _ in candidates:
        if os.path.normpath(path) == os.path.normpath(requested_path):
            return path
    candidates.sort(key=lambda x: -x[1])
    return candidates[0][0]


# #region agent log
def _dlog(location, message, data, hypothesis_id):
    try:
        with open("debug-8cd382.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "8cd382", "runId": "run1", "hypothesisId": hypothesis_id, "location": location, "message": message, "data": data, "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception:
        pass
# #endregion


def download_video(url, output="video.mp4", cookies_file=None):
    """
    Download video with yt-dlp. Supports YouTube, Shorts, TikTok, Instagram Reels.

    For Instagram (and sometimes TikTok), login may be required. Set cookies_file to
    a Netscape-format cookies file, or set env YT_DLP_COOKIES_FILE to its path.
    Export cookies from your browser (e.g. with an extension) after logging in.
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("URL is required")

    output_abs = os.path.abspath(output)
    cwd = os.getcwd()
    cookies = cookies_file or os.environ.get("YT_DLP_COOKIES_FILE")
    # #region agent log
    _dlog("video_utils.py:download_video(entry)", "download_video called", {"output": output, "output_abs": output_abs, "cwd": cwd, "cookies_set": bool(cookies and os.path.isfile(cookies)), "url_domain": url[:50] + "..." if len(url) > 50 else url}, "H1")
    _dlog("video_utils.py:download_video(entry)", "cwd and path hypothesis", {"output_is_absolute": os.path.isabs(output), "output_dir": os.path.dirname(output_abs), "output_dir_exists": os.path.isdir(os.path.dirname(output_abs))}, "H3")
    # #endregion

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "-f", _FORMAT,
        "--merge-output-format", "mp4",
        "-o", output_abs,
        "--no-warnings",
        "--force-overwrite",
    ]
    if cookies and os.path.isfile(cookies):
        cmd.extend(["--cookies", os.path.abspath(cookies)])

    cmd.append(url)

    # #region agent log
    _exe = cmd[0]
    _dlog("video_utils.py:download_video(before run)", "subprocess executable", {"executable": _exe, "executable_exists": os.path.isfile(_exe) if _exe else False, "executable_abs": os.path.abspath(_exe) if _exe else None, "cmd_len": len(cmd)}, "WinError2")
    # #endregion

    # Use same Python as current process so yt-dlp from pip is found (no CLI fallback on Windows)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (FileNotFoundError, OSError) as e:
        # #region agent log
        _dlog("video_utils.py:download_video(except)", "subprocess failed", {"err_type": type(e).__name__, "err_msg": str(e), "errno": getattr(e, "errno", None), "winerror": getattr(e, "winerror", None), "filename": getattr(e, "filename", None)}, "WinError2")
        # #endregion
        raise RuntimeError(
            "Could not run yt-dlp. Use the project venv and install it: pip install yt-dlp"
        ) from e

    out_dir = os.path.dirname(output_abs)
    out_exists = os.path.isfile(output_abs)
    out_size = os.path.getsize(output_abs) if out_exists else 0
    dir_list = os.listdir(out_dir) if os.path.isdir(out_dir) else []
    stderr_preview = (result.stderr or "")[:800] if result.stderr else ""
    stdout_preview = (result.stdout or "")[:800] if result.stdout else ""
    # #region agent log
    _dlog("video_utils.py:download_video(after run)", "yt-dlp result and file state", {"returncode": result.returncode, "output_path_exists": out_exists, "output_path_size": out_size, "files_in_output_dir": dir_list, "stderr_len": len(result.stderr or ""), "stdout_len": len(result.stdout or ""), "stderr_preview": stderr_preview, "stdout_preview": stdout_preview}, "H1")
    _dlog("video_utils.py:download_video(after run)", "merge/format hypothesis", {"returncode": result.returncode, "has_part_file": any("part" in f or ".part" in f for f in dir_list), "any_mp4_in_dir": any(f.endswith(".mp4") for f in dir_list)}, "H2")
    _dlog("video_utils.py:download_video(after run)", "format selection", {"stderr_contains_format": "format" in (result.stderr or "").lower() or "requested" in (result.stderr or "").lower()}, "H4")
    # #endregion

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        if "login required" in err.lower() or "cookies" in err.lower():
            raise RuntimeError(
                "Download failed (login/cookies may be required). "
                "For Instagram Reels (and sometimes TikTok), export cookies from your browser "
                "and set YT_DLP_COOKIES_FILE to the file path, or pass cookies_file=..."
            ) from None
        raise RuntimeError(f"yt-dlp failed: {err or result.returncode}")

    # yt-dlp often writes merged/single format to a different name (e.g. video.f401.mp4,
    # video.f299.mp4, video.fdash-xxx.mp4) on YouTube, Shorts, Instagram. TikTok usually
    # writes directly to the requested path. Normalize so the pipeline always gets output_abs.
    if not os.path.isfile(output_abs) or os.path.getsize(output_abs) == 0:
        actual = _find_ytdlp_output(output_abs, out_dir)
        if actual:
            if os.path.isfile(output_abs):
                try:
                    os.remove(output_abs)
                except OSError:
                    pass
            os.rename(actual, output_abs)
        else:
            raise RuntimeError("Download produced no file or empty file")


def extract_frames(
    video_path,
    output_folder="frames",
    interval=10,
    short_video_interval=3,
    short_video_max_seconds=90,
):
    """
    Extract frames every `interval` seconds (default 10).
    For short videos (duration < short_video_max_seconds), use short_video_interval
    (default 3s) so we get enough frames from Shorts/TikTok/Reels.
    """
    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = frame_count / fps if fps else 0

    use_interval = short_video_interval if duration_sec > 0 and duration_sec < short_video_max_seconds else interval
    frame_interval = max(1, int(fps * use_interval))

    count = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if count % frame_interval == 0:
            path = f"{output_folder}/frame_{saved}.jpg"
            cv2.imwrite(path, frame)
            saved += 1
        count += 1

    cap.release()
    return output_folder
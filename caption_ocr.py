"""
Extract on-screen text (captions) from video frames using Ollama GLM-OCR.

GLM-OCR is a lightweight (~0.9B param) model optimized for text recognition,
ideal for processing many frames when captions move fast. Use the q8_0 tag
for smallest size and fastest inference: ollama pull glm-ocr:q8_0
"""

import os
import re

# Optional: only require ollama when this module is used
try:
    from ollama import chat
except ImportError:
    chat = None

# Lightweight model: 1.6GB, fast. Use "glm-ocr" for default 2.2GB if preferred.
DEFAULT_OCR_MODEL = "glm-ocr:q8_0"

# Prompt per GLM-OCR docs for text recognition
TEXT_RECOGNITION_PROMPT = "Text Recognition:"


def _normalize_for_match(text: str) -> set[str]:
    """Lowercase, split on non-alpha, return set of tokens (words)."""
    if not text or not text.strip():
        return set()
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return set(t for t in tokens if len(t) > 1)


def extract_text_from_image(image_path: str, model: str = DEFAULT_OCR_MODEL) -> str:
    """
    Run GLM-OCR text recognition on a single image. Returns raw text from the image.
    """
    if chat is None:
        raise RuntimeError("ollama package required for caption OCR. Install with: pip install ollama")
    if not os.path.isfile(image_path):
        return ""
    response = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": TEXT_RECOGNITION_PROMPT,
                "images": [image_path],
            }
        ],
    )
    out = getattr(response, "message", None) or response
    content = getattr(out, "content", None) or (out if isinstance(out, str) else "")
    return (content or "").strip()


def extract_captions_from_frames(
    frame_folder: str,
    model: str = DEFAULT_OCR_MODEL,
    *,
    max_frames: int | None = None,
) -> tuple[set[str], list[str]]:
    """
    Run OCR on all frame images in frame_folder. Returns:
      - set of normalized words (for cross-referencing with ingredients)
      - list of raw text per frame (for debugging / merging)

    Use max_frames to cap work when there are many frames (e.g. 50).
    """
    if chat is None:
        raise RuntimeError("ollama package required for caption OCR. Install with: pip install ollama")

    files = sorted(
        [f for f in os.listdir(frame_folder) if f.endswith(".jpg")],
        key=lambda f: f,
    )
    if max_frames is not None and len(files) > max_frames:
        # Sample evenly across the video
        step = len(files) / max_frames
        indices = [min(int(i * step), len(files) - 1) for i in range(max_frames)]
        files = [files[i] for i in sorted(set(indices))]

    all_words: set[str] = set()
    raw_texts: list[str] = []

    for f in files:
        path = os.path.join(frame_folder, f)
        try:
            text = extract_text_from_image(path, model=model)
            raw_texts.append(text)
            all_words |= _normalize_for_match(text)
        except Exception:
            raw_texts.append("")
            continue

    return all_words, raw_texts


def caption_words_from_frames(
    frame_folder: str,
    model: str = DEFAULT_OCR_MODEL,
    max_frames: int | None = 50,
) -> set[str]:
    """
    Convenience: return only the set of words found in on-screen captions.
    Limits to max_frames (default 50) to keep runs light when there are many frames.
    """
    words, _ = extract_captions_from_frames(frame_folder, model=model, max_frames=max_frames)
    return words

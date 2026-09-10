import os

try:
    from caption_ocr import caption_words_from_frames
except ImportError:
    caption_words_from_frames = None


def _ingredient_matches_caption(ingredient: str, caption_words: set[str]) -> bool:
    """True if any word in the ingredient appears in on-screen caption words."""
    ing = ingredient.lower().strip()
    words = set(w for w in ing.split() if len(w) > 1)
    if not words:
        return ing in caption_words or (ing.rstrip("s") in caption_words)
    return bool(words & caption_words) or ing in caption_words or ing.rstrip("s") in caption_words


def cross_reference_with_captions(transcript_list, caption_words: set[str]):
    """
    Cross-reference transcript ingredients with OCR caption words.
    Sets caption_seen for items whose words appear in on-screen text (creator captions).
    """
    result = []
    for item in transcript_list:
        ing = item["ingredient"]
        qty = item.get("quantity", "unknown")
        caption_seen = _ingredient_matches_caption(ing, caption_words) if caption_words else False
        result.append({
            "ingredient": ing,
            "quantity": qty,
            "caption_seen": caption_seen,
        })
    return result


def process_frames_for_captions(frame_folder, model="glm-ocr:q8_0", max_frames=50):
    """
    Run lightweight OCR (GLM-OCR) on frames to get on-screen words.
    Returns set of words found in captions. Use max_frames to limit work.
    """
    if caption_words_from_frames is None:
        return set()
    return caption_words_from_frames(frame_folder, model=model, max_frames=max_frames)
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from transcript import get_transcript
from ingredient_extractor import extract_ingredients_with_quantity
from ingredient_merger import IngredientMerger
from video_utils import download_video, extract_frames
from vision_pipline import (
    process_frames_for_captions,
    cross_reference_with_captions,
)
from url_detection import get_platform
from description_fetcher import get_video_metadata, has_explicit_ingredient_list

try:
    from db import get_cached_ingredients, save_video_result, init_db
    _db_available = True
except Exception:
    _db_available = False


def main():
    url = input(
        "Paste URL (YouTube, YouTube Shorts, TikTok, or Instagram Reels): "
    ).strip()
    if not url:
        print("No URL entered.")
        return

    platform = get_platform(url)
    if platform == "unknown":
        print("Unsupported URL. Use YouTube, Shorts, TikTok, or Instagram Reels.")
        return

    # Check DB first: if URL already processed, return cached list (no download, no AI)
    if _db_available:
        cached = get_cached_ingredients(url, platform)
        if cached:
            title, ingredients = cached["title"], cached["ingredients"]
            print("URL already in database — using cached result (skipping video & AI).\n")
            print(f"Video: {title or '(no title)'}\n")
            print("Grocery List:\n")
            for item in ingredients:
                mark = " ✓" if item.get("caption_seen") else ""
                print(f"  {item.get('ingredient', '')}: {item.get('quantity', 'unknown')}{mark}")
            return

    # Fetch description and title (metadata only, no download)
    print("Fetching video description...")
    metadata = get_video_metadata(url)
    description = metadata.get("description", "")
    title = metadata.get("title", "")
    thumbnail = metadata.get("thumbnail", "")
    if description:
        print(f"Description length: {len(description)} chars")

    # Explicit ingredient list (Recipe / Ingredients / For the X: + list format) → description only, no video/transcript
    if description and has_explicit_ingredient_list(description):
        print("Explicit ingredient list found in description; using description only (skipping video and transcript).")
        description_ing = extract_ingredients_with_quantity(description)
        raw = [
            {"ingredient": x["ingredient"], "quantity": x.get("quantity", "unknown")}
            for x in description_ing
        ]
        final = IngredientMerger().merge(raw)
        if _db_available:
            save_video_result(url, title, final, thumbnail, platform)
        print("\nFinal Grocery List (from description):\n")
        for item in final:
            print(f"  {item['ingredient']}: {item['quantity']}")
        return

    if not description:
        print("No description available.")

    print("Downloading video...")
    download_video(url)

    print("Extracting transcript...")
    transcript = get_transcript(url, video_path="video.mp4")

    print("\nTRANSCRIPT SAMPLE:\n")
    print(transcript[:1000])
    print("\n--- END SAMPLE ---\n")

    print("Extracting ingredients from transcript...")
    transcript_ing = extract_ingredients_with_quantity(transcript)
    description_ing = []
    if description:
        print("Extracting ingredients from description...")
        description_ing = extract_ingredients_with_quantity(description)

    print("\nDEBUG INGREDIENT OUTPUT (transcript):")
    print(transcript_ing)
    if description_ing:
        print("DEBUG INGREDIENT OUTPUT (description):")
        print(description_ing)

    # Extract frames; use denser sampling for short videos so we catch fast-moving captions
    print("Extracting frames...")
    frames_folder = extract_frames(
        "video.mp4",
        short_video_interval=1.5,
    )

    # Merge transcript + description: same ingredient → prefer transcript quantity, else description
    merged = {}
    for item in transcript_ing:
        ing = item["ingredient"].lower()
        qty = item.get("quantity", "unknown")
        merged[ing] = qty
    for item in description_ing:
        ing = item["ingredient"].lower()
        if ing not in merged:
            merged[ing] = item.get("quantity", "unknown")

    transcript_list = [{"ingredient": k, "quantity": v} for k, v in merged.items()]
    transcript_list = IngredientMerger().merge(transcript_list)

    # Cross-reference with on-screen captions (OCR via GLM-OCR; lightweight, many frames)
    print("Reading on-screen captions (GLM-OCR)...")
    caption_words = process_frames_for_captions(frames_folder, max_frames=50)
    final = cross_reference_with_captions(transcript_list, caption_words)

    if _db_available:
        save_video_result(url, title, final, thumbnail, platform)

    print("\nFinal Grocery List (✓ = also seen in on-screen captions):\n")
    for item in final:
        mark = " ✓" if item.get("caption_seen") else ""
        print(f"  {item['ingredient']}: {item['quantity']}{mark}")


if __name__ == "__main__":
    if _db_available:
        try:
            init_db()
        except Exception:
            pass  # Run without DB if not configured
    main()
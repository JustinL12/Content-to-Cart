import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"


def extract_ingredients_with_quantity(transcript):
    prompt = f"""
    Extract the grocery ingredients needed to cook the recipe from the text below.
    The text may be a video transcript (speech) or a video description/caption (written).
    Include every ingredient that is clearly part of the recipe. Do not omit any listed ingredient,
    including common ones like onion, garlic, oil, or herbs when they appear in the recipe or list.

    Rules:
    - For speech/transcript: focus on ingredients mentioned with words like
    "add", "use", "put in", "mix in", "season with", "pour", "stir in".
    - For descriptions/captions: include every ingredient that appears in the written list or recipe.
    - Ignore ingredients mentioned only as examples or discussion.

    Substitute handling:
    - If multiple substitutes are listed with words like "or", choose ONE general ingredient.
    - Example: "sunflower oil or soybean oil or olive oil" → "vegetable oil"
    - Example: "butter or margarine" → "butter"

    Generalization:
    - Prefer the most common grocery category when many variants are given.
    - Example:
    "green onions or chives" → "green onions"
    "soy sauce or tamari" → "soy sauce"

    Quantities:
    - If a quantity is given, include it.
    - If not mentioned, use "unknown".

    Ignore:
    - cooking tools
    - temperatures
    - actions
    - garnish suggestions unless clearly required

    Return ONLY valid JSON in this format:

    [
    {{"ingredient":"eggs","quantity":"2"}},
    {{"ingredient":"vegetable oil","quantity":"2 tbsp"}}
    ]

    Text (transcript or description):
    {transcript[:3000]}
    """

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    text = response.json()["response"]

    # Extract JSON portion
    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        return []

    json_text = text[start:end+1]

    try:
        return json.loads(json_text)
    except Exception:
        return []
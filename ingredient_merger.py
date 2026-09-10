"""
Merge ingredient list: deduplicate and combine subset ingredients
(e.g. "chicken" + "chicken thigh" → "chicken thigh") into the more specific variant.
Also normalize away preparation styles like "sliced", "diced", "boiled", "baked"
so they are classified under the base ingredient (e.g. "sliced potatoes" →
"potato").
"""

_PREP_WORDS = {
    "sliced",
    "slice",
    "diced",
    "dice",
    "boiled",
    "boil",
    "baked",
    "bake",
    "roasted",
    "roast",
    "fried",
    "fry",
    "grilled",
    "grill",
    "steamed",
    "steam",
    "mashed",
    "mash",
    "crushed",
    "crush",
    "ground",
    "grind",
    "minced",
    "mince",
    "chopped",
    "chop",
    "shredded",
    "shred",
    "sauteed",
    "sautéed",
    "saute",
    "sauté",
    "cooked",
}


def _normalize_for_compare(name: str) -> str:
    """
    Normalize for comparison:
    - lowercase, trim
    - drop leading preparation words (sliced, diced, boiled, baked, etc.)
    - crude singularization of the last token (potatoes → potato, thighs → thigh)
    """
    text = (name or "").strip().lower()
    if not text:
        return ""

    for ch in ",;":
        text = text.replace(ch, " ")
    parts = [p for p in text.split() if p]

    # Drop leading prep words so "sliced potatoes", "diced potatoes", "boiled potato"
    # all normalize under the base ingredient.
    while parts and parts[0] in _PREP_WORDS:
        parts.pop(0)

    if not parts:
        return ""

    # Very simple plural handling on the last token
    last = parts[-1]
    if last.endswith("oes") and len(last) > 3:
        last = last[:-3] + "o"
    elif last.endswith("s") and len(last) > 3:
        last = last[:-1]
    parts[-1] = last

    return " ".join(parts)


def _is_same_ingredient(a: str, b: str) -> bool:
    """Treat as same if equal or one is plural of the other (X vs Xs)."""
    na, nb = _normalize_for_compare(a), _normalize_for_compare(b)
    if na == nb:
        return True
    if na and nb:
        if na + "s" == nb or nb + "s" == na:
            return True
        if na.rstrip("s") == nb.rstrip("s"):
            return True
    return False


def _is_subset_of(less_specific: str, more_specific: str) -> bool:
    """True if less_specific is a proper substring of more_specific (or same)."""
    ln = _normalize_for_compare(less_specific)
    mn = _normalize_for_compare(more_specific)
    if ln == mn:
        return True
    # "chicken" in "chicken thigh" -> chicken is subset
    if len(ln) < len(mn) and ln in mn:
        # Require word boundary so "egg" isn't subset of "eggs"
        idx = mn.find(ln)
        if idx == 0:  # at start: "chicken" in "chicken thigh"
            return True
        if idx + len(ln) == len(mn):  # at end: "thigh" in "chicken thigh"
            return True
        if idx > 0 and idx + len(ln) < len(mn) and mn[idx - 1] in " -" and (idx + len(ln) >= len(mn) or mn[idx + len(ln)] in " -"):
            return True
    return False


def _prefer_quantity(qty_a: str, qty_b: str) -> str:
    """Prefer non-unknown; else first."""
    u = "unknown"
    if (qty_a or u).lower().strip() != u and (qty_b or u).lower().strip() != u:
        return qty_a or qty_b
    if (qty_a or u).lower().strip() != u:
        return qty_a
    return qty_b or qty_a or u


class IngredientMerger:
    """
    Combines duplicate ingredients and subset ingredients into the more specific
    variant (e.g. "chicken" and "chicken thigh" → one entry "chicken thigh").
    Preserves extra keys (e.g. yolo_seen) on the kept item.
    """

    def merge(
        self,
        items: list[dict],
        *,
        quantity_key: str = "quantity",
        ingredient_key: str = "ingredient",
    ) -> list[dict]:
        """
        Merge items: same name (or plural) → one entry; if A is substring of B,
        keep B (more specific) and drop A. Returns new list; does not mutate input.
        """
        if not items:
            return []

        # Keep first occurrence's extra keys; we'll overwrite ingredient/quantity when merging
        def item_dict(ing: str, qty: str, template: dict) -> dict:
            out = {k: v for k, v in template.items() if k not in (ingredient_key, quantity_key)}
            out[ingredient_key] = ing
            out[quantity_key] = qty
            return out

        # Sort by name length descending so we see "chicken thigh" before "chicken"
        with_keys = [
            (item.get(ingredient_key, ""), item.get(quantity_key, "unknown"), item)
            for item in items
        ]
        with_keys.sort(key=lambda x: -len(_normalize_for_compare(x[0])))

        kept: list[dict] = []

        for name, qty, template in with_keys:
            name_norm = _normalize_for_compare(name)
            if not name_norm:
                continue

            merged_into = None
            for i, existing in enumerate(kept):
                ename = existing.get(ingredient_key, "")
                ename_norm = _normalize_for_compare(ename)

                if _is_same_ingredient(name, ename):
                    # Exact duplicate (or plural): merge quantity, keep one name (prefer longer)
                    new_name = ename if len(ename_norm) >= len(name_norm) else name
                    new_qty = _prefer_quantity(
                        existing.get(quantity_key, "unknown"),
                        qty,
                    )
                    kept[i] = item_dict(new_name, new_qty, template)
                    merged_into = i
                    break

                if _is_subset_of(name, ename):
                    # Existing is more specific (e.g. "chicken thigh"); we're "chicken" → drop, but keep quantity if we have one and existing doesn't
                    existing_qty = existing.get(quantity_key, "unknown")
                    if _prefer_quantity(existing_qty, qty) != existing_qty:
                        kept[i] = item_dict(ename, _prefer_quantity(existing_qty, qty), existing)
                    merged_into = i
                    break

                if _is_subset_of(ename, name):
                    # We're more specific (e.g. we're "chicken thigh", existing is "chicken") → replace
                    new_qty = _prefer_quantity(qty, existing.get(quantity_key, "unknown"))
                    kept[i] = item_dict(name, new_qty, template)
                    merged_into = i
                    break

            if merged_into is None:
                kept.append(item_dict(name, qty, template))

        return kept

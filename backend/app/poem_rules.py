# Lightweight Hindi chhand/matra heuristics.
# These are intentionally conservative: exact Hindi मात्रा scansion is
# linguistically nuanced, so the validator reports a heuristic score rather
# than falsely claiming formal publication-grade prosody.

DEVANAGARI_MATRA = {
    "ा": 2, "ि": 1, "ी": 2, "ु": 1, "ू": 2,
    "ृ": 1, "े": 2, "ै": 2, "ो": 2, "ौ": 2,
    "ं": 1, "ः": 1,
}

VOWEL_SIGNS = set(DEVANAGARI_MATRA)
HALANT = "्"


def line_matra_count(line: str) -> int:
    count = 0
    prev_base = False
    for ch in line:
        if ch in DEVANAGARI_MATRA:
            count += DEVANAGARI_MATRA[ch]
            prev_base = False
        elif ch == HALANT:
            prev_base = False
        elif "\u0900" <= ch <= "\u097F":
            # A consonant with no explicit matra is normally a short
            # inherent vowel for this heuristic.
            if ch not in VOWEL_SIGNS:
                count += 1
            prev_base = True
        else:
            prev_base = False
    return count


def validate_poem(poem: str, style: str) -> dict:
    lines = [x.strip() for x in poem.splitlines() if x.strip()]
    counts = [line_matra_count(x) for x in lines]
    result = {
        "line_count": len(lines),
        "matra_counts": counts,
        "meter": style,
        "heuristic_balanced": False,
        "notes": [],
    }
    if not counts:
        result["notes"].append("No poem lines found.")
        return result

    if style == "doha":
        # Doha commonly uses 13/11 matra pattern in each half-line.
        targets = [13, 11]
        checks = []
        for i, c in enumerate(counts):
            checks.append(c in targets)
        result["heuristic_balanced"] = sum(checks) >= max(1, len(checks) * 0.75)
        result["notes"].append("Doha validation uses a simplified 13/11 heuristic.")
    elif style == "chaupai":
        result["heuristic_balanced"] = all(15 <= c <= 17 for c in counts)
        result["notes"].append("Chaupai validation uses a simplified ~16-matra heuristic.")
    else:
        spread = max(counts) - min(counts)
        result["heuristic_balanced"] = spread <= 6
        result["notes"].append("Modern/free verse is judged mainly on rhythmic consistency.")

    return result

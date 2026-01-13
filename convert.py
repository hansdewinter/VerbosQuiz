#!/usr/bin/env python3
import argparse
import json
import re
import unicodedata
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.esfacil.eu/nl/werkwoorden/vervoeging.html"

# Present tense of "estar"
ESTAR_PRESENT = ["estoy", "estás", "está", "estamos", "estáis", "están"]
# Reflexive pronouns aligned with person order
REFLEXIVE_PRONOUNS = ["me", "te", "se", "nos", "os", "se"]
# Desired output order
OUTPUT_FIELD_ORDER = [
    "verbo",
    "presente",
    "preterito-perfecto",
    "preterito-indefinido",
    "presente-progresivo",
    "dutch",
]


def remove_accents(text: str) -> str:
    """Strip accents from a string while keeping other characters intact."""
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def extract_infinitive(verbo: str) -> str:
    """Best-effort extraction of the infinitive from the verbo field."""
    token = verbo.split()[0] if verbo else ""
    token = token.strip('"\'' )
    token = re.sub(r"[^\wáéíóúñüÁÉÍÓÚÑÜ]", "", token)
    return token


def is_reflexive(infinitive: str) -> bool:
    return infinitive.endswith("se")


def strip_reflexive_suffix(infinitive: str) -> str:
    return infinitive[:-2] if is_reflexive(infinitive) else infinitive


def fetch_gerundio_from_site(verb: str) -> Optional[str]:
    """Query esfacil.eu for a verb gerundio. Returns None on failure."""
    params = {"verb": verb, "option": "com_verb", "task": "conjugate"}
    # Try with verification first, then retry without if needed.
    for verify in (True, False):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15, verify=verify)
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            continue
        except requests.RequestException:
            continue

        gerund = parse_gerundio(resp.text)
        if gerund:
            return gerund
    return None


def parse_gerundio(html: str) -> Optional[str]:
    """Parse gerundio from the conjugation page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table:
        for row in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) >= 2 and cells[0].lower().startswith("gerund"):
                return cells[1]

    # Fallback: text search
    text = soup.get_text(" ", strip=True)
    match = re.search(r"gerund\w*\s*[:\-]?\s*([a-záéíóúñü]+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def derive_regular_gerundio(infinitive: str) -> Optional[str]:
    """Simple regular gerund builder as a fallback when scraping fails."""
    base = strip_reflexive_suffix(infinitive)
    base = re.sub(r"[^\wáéíóúñüÁÉÍÓÚÑÜ]", "", base)
    if base.endswith("ar"):
        return base[:-2] + "ando"
    if base.endswith(("er", "ir")):
        stem = base[:-2]
        last = stem[-1].lower() if stem else ""
        if last in "aeiou" or base.endswith("uir"):
            return stem + "yendo"
        return stem + "iendo"
    return None


def fetch_gerundio(infinitive: str) -> Optional[str]:
    """
    Fetch gerundio with fallbacks:
    - Try non-reflexive form first (covers declarándose vs declarando).
    - Try original infinitive.
    - Fall back to a regular gerund derivation.
    """
    candidates = []
    stripped = strip_reflexive_suffix(infinitive)
    if stripped:
        candidates.append(stripped)
    if infinitive and infinitive != stripped:
        candidates.append(infinitive)

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        ger = fetch_gerundio_from_site(candidate)
        if ger:
            return ger

    return derive_regular_gerundio(infinitive)


def strip_reflexive_from_gerundio(gerundio: str) -> str:
    """Remove trailing reflexive pronouns from a gerundio and normalize accents."""
    lowered = gerundio.lower()
    for pronoun in ("se", "me", "te", "nos", "os"):
        if lowered.endswith(pronoun):
            trimmed = gerundio[: -len(pronoun)]
            return remove_accents(trimmed)
    return gerundio


def build_presente_progresivo(gerundio: str, reflexive: bool) -> List[str]:
    if reflexive:
        clean_ger = strip_reflexive_from_gerundio(gerundio)
        return [
            f"{pron} {estar} {clean_ger}"
            for pron, estar in zip(REFLEXIVE_PRONOUNS, ESTAR_PRESENT)
        ]
    return [f"{estar} {gerundio}" for estar in ESTAR_PRESENT]


def process_verbs(data: Iterable[dict]) -> List[dict]:
    def ordered_entry(entry: dict, progressive: List[str]) -> dict:
        """
        Return a new dict whose keys follow OUTPUT_FIELD_ORDER.
        Any unexpected keys are appended in their original order.
        """
        # Copy to avoid mutating the input reference
        temp = dict(entry)
        temp["presente-progresivo"] = progressive

        ordered: dict = {}
        for key in OUTPUT_FIELD_ORDER:
            if key in temp:
                ordered[key] = temp[key]

        # Append any extra fields not in the predefined order
        for key, value in temp.items():
            if key not in OUTPUT_FIELD_ORDER:
                ordered[key] = value

        return ordered

    enriched = []
    for entry in data:
        verbo = entry.get("verbo", "")
        infinitive = extract_infinitive(verbo)
        gerundio = fetch_gerundio(infinitive)
        if not gerundio:
            raise RuntimeError(f"Unable to derive gerundio for verb: {verbo}")

        progressive = build_presente_progresivo(
            gerundio=gerundio, reflexive=is_reflexive(infinitive)
        )
        enriched.append(ordered_entry(entry, progressive))
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append presente progresivo to Spanish verbs JSON."
    )
    parser.add_argument(
        "--input",
        default="Verbos.json",
        help="Input JSON file path (default: Verbos.json)",
    )
    parser.add_argument(
        "--output",
        default="Verbos-out.json",
        help="Output JSON file path (default: Verbos-out.json)",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched = process_verbs(data)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=4)

    print(
        f"Wrote {len(enriched)} verbs with presente-progresivo to {args.output}"
    )


if __name__ == "__main__":
    main()


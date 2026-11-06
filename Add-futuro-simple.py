#!/usr/bin/env python3
import argparse
import json
import re
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.esfacil.eu/nl/werkwoorden/vervoeging.html"
FUTURO_SIMPLE_SECTION_ID = "indicativo-futuro"

# Reflexive pronouns aligned with person order
REFLEXIVE_PRONOUNS = ["me", "te", "se", "nos", "os", "se"]

# Desired output order
OUTPUT_FIELD_ORDER = [
    "verbo",
    "presente",
    "preterito-perfecto",
    "preterito-indefinido",
    "preterito-imperfecto",
    "futuro-simple",
    "presente-progresivo",
    "imperativo-afirmativo",
    "imperativo-negativo",
    "dutch",
]


def extract_infinitive(verbo: str) -> str:
    """Best-effort extraction of the infinitive from the verbo field."""
    token = verbo.split()[0] if verbo else ""
    token = token.strip("\"'")
    token = re.sub(r"[^\wáéíóúñüÁÉÍÓÚÑÜ]", "", token)
    return token


def is_reflexive(infinitive: str) -> bool:
    return infinitive.endswith("se")


def strip_reflexive_suffix(infinitive: str) -> str:
    return infinitive[:-2] if is_reflexive(infinitive) else infinitive


def fetch_futuro_simple_from_site(verb: str) -> Optional[List[str]]:
    """Query esfacil.eu for futuro simple conjugations."""
    params = {"verb": verb, "option": "com_verb", "task": "conjugate"}
    for verify in (True, False):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15, verify=verify)
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            continue
        except requests.RequestException:
            continue

        forms = parse_futuro_simple(resp.text)
        if forms:
            return forms
    return None


def parse_futuro_simple(html: str) -> Optional[List[str]]:
    """Parse futuro simple forms from the conjugation page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find("h3", id=FUTURO_SIMPLE_SECTION_ID)
    if not section:
        return None

    table = section.find_next("table")
    if not table:
        return None

    forms: List[str] = []
    for row in table.find_all("tr"):
        td = row.find("td")
        if not td:
            continue

        conjugation_spans = td.find_all(
            "span", class_=lambda x: x and x.startswith("conjugation-")
        )
        if not conjugation_spans:
            continue

        if len(conjugation_spans) == 1:
            form = conjugation_spans[0].get_text(strip=True)
        else:
            form = td.get_text(" ", strip=True)

        if form:
            forms.append(form)

    return forms or None


def build_reflexive_forms(forms: List[str]) -> List[str]:
    """Prefix reflexive pronouns to the non-reflexive conjugations."""
    return [f"{pron} {form}" for pron, form in zip(REFLEXIVE_PRONOUNS, forms)]


def fetch_futuro_simple(infinitive: str) -> Optional[List[str]]:
    """
    Fetch futuro simple with fallbacks:
    - Try non-reflexive form first.
    - Try original infinitive.
    """
    candidates: List[str] = []
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
        forms = fetch_futuro_simple_from_site(candidate)
        if forms:
            return forms
    return None


def process_verbs(data: Iterable[dict]) -> List[dict]:
    def ordered_entry(entry: dict, futuro_simple: List[str]) -> dict:
        """
        Return a new dict whose keys follow OUTPUT_FIELD_ORDER.
        Any unexpected keys are appended in their original order.
        """
        temp = dict(entry)
        temp["futuro-simple"] = futuro_simple

        ordered: dict = {}
        for key in OUTPUT_FIELD_ORDER:
            if key in temp:
                ordered[key] = temp[key]

        for key, value in temp.items():
            if key not in OUTPUT_FIELD_ORDER:
                ordered[key] = value

        return ordered

    enriched = []
    for entry in data:
        verbo = entry.get("verbo", "")
        infinitive = extract_infinitive(verbo)
        if not infinitive:
            raise RuntimeError(f"Unable to extract infinitive from verbo: {verbo}")

        forms = fetch_futuro_simple(infinitive)
        if not forms or len(forms) != 6:
            raise RuntimeError(
                f"Unable to derive futuro simple for verb: {verbo}"
            )

        if is_reflexive(infinitive):
            forms = build_reflexive_forms(forms)

        enriched.append(ordered_entry(entry, forms))
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append futuro simple to Spanish verbs JSON."
    )
    parser.add_argument(
        "--input",
        default="Verbos.json",
        help="Input JSON file path (default: Verbos.json)",
    )
    parser.add_argument(
        "--output",
        default="Verbos-futuro-simple.json",
        help="Output JSON file path (default: Verbos-futuro-simple.json)",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched = process_verbs(data)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=4)

    print(
        f"Wrote {len(enriched)} verbs with futuro simple to {args.output}"
    )


if __name__ == "__main__":
    main()

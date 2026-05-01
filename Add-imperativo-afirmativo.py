#!/usr/bin/env python3
import argparse
import json
import re
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.esfacil.eu/nl/werkwoorden/vervoeging.html"
IMPERATIVO_AFIRMATIVO_SECTION_ID = "imperativo-afirmativo"

# Labels in the affirmative-imperative table (non-reflexive vs reflexive)
TÚ_LABELS = frozenset({"(tú)", "(te)"})
VOSOTROS_LABELS = frozenset({"(vosotros/-as)", "(os)"})

OUTPUT_FIELD_ORDER = [
    "verbo",
    "presente",
    "preterito-perfecto",
    "preterito-indefinido",
    "preterito-imperfecto",
    "presente-progresivo",
    "imperativo-afirmativo",
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


def fetch_imperativo_from_site(verb: str) -> Optional[Dict[str, str]]:
    params = {"verb": verb, "option": "com_verb", "task": "conjugate"}
    for verify in (True, False):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15, verify=verify)
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            continue
        except requests.RequestException:
            continue

        forms = parse_imperativo_afirmativo(resp.text)
        if forms:
            return forms
    return None


def parse_imperativo_afirmativo(html: str) -> Optional[Dict[str, str]]:
    """Parse imperativo afirmativo (tú and vosotros only) from conjugation HTML."""
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find("h3", id=IMPERATIVO_AFIRMATIVO_SECTION_ID)
    if not section:
        return None

    table = section.find_next("table")
    if not table:
        return None

    tu_form: Optional[str] = None
    vosotros_form: Optional[str] = None

    for row in table.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue

        pronoun_span = th.find("span", class_="pronoun")
        label = pronoun_span.get_text(strip=True) if pronoun_span else th.get_text(strip=True)

        conjugation_spans = td.find_all(
            "span", class_=lambda x: x and x.startswith("conjugation-")
        )
        if not conjugation_spans:
            continue
        if len(conjugation_spans) == 1:
            form = conjugation_spans[0].get_text(strip=True)
        else:
            form = td.get_text(" ", strip=True)

        if not form:
            continue

        if label in TÚ_LABELS:
            tu_form = form
        elif label in VOSOTROS_LABELS:
            vosotros_form = form

    if tu_form and vosotros_form:
        return {"tu": tu_form, "vosotros": vosotros_form}
    return None


def imperativo_fetch_candidates(infinitive: str) -> List[str]:
    """
    URL query order:
    - Reflexive verbs: full infinitive first (site gives enclitic forms like lávate).
    - Non-reflexive: stripped stem first, then full (same as pretérito imperfecto script).
    """
    stripped = strip_reflexive_suffix(infinitive)
    candidates: List[str] = []
    if is_reflexive(infinitive):
        if infinitive:
            candidates.append(infinitive)
        if stripped and stripped != infinitive:
            candidates.append(stripped)
    else:
        if stripped:
            candidates.append(stripped)
        if infinitive and infinitive != stripped:
            candidates.append(infinitive)
    return candidates


def fetch_imperativo(infinitive: str) -> Optional[Dict[str, str]]:
    seen = set()
    for candidate in imperativo_fetch_candidates(infinitive):
        if candidate in seen:
            continue
        seen.add(candidate)
        forms = fetch_imperativo_from_site(candidate)
        if forms:
            return forms
    return None


def process_verbs(data: Iterable[dict]) -> List[dict]:
    def ordered_entry(entry: dict, imperativo: Dict[str, str]) -> dict:
        temp = dict(entry)
        temp["imperativo-afirmativo"] = imperativo

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

        forms = fetch_imperativo(infinitive)
        if not forms:
            raise RuntimeError(
                f"Unable to derive imperativo afirmativo (tú/vosotros) for verb: {verbo}"
            )

        enriched.append(ordered_entry(entry, forms))
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append imperativo afirmativo (tú, vosotros) to Spanish verbs JSON."
    )
    parser.add_argument(
        "--input",
        default="Verbos.json",
        help="Input JSON file path (default: Verbos.json)",
    )
    parser.add_argument(
        "--output",
        default="Verbos-imperativo-afirmativo.json",
        help="Output JSON file path (default: Verbos-imperativo-afirmativo.json)",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched = process_verbs(data)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=4)

    print(
        f"Wrote {len(enriched)} verbs with imperativo afirmativo to {args.output}"
    )


if __name__ == "__main__":
    main()

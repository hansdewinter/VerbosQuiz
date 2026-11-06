#!/usr/bin/env python3
import argparse
import json
import re
import unicodedata
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.esfacil.eu/nl/werkwoorden/vervoeging.html"
IMPERATIVO_AFIRMATIVO_SECTION_ID = "imperativo-afirmativo"
IMPERATIVO_NEGATIVO_SECTION_ID = "imperativo-negativo"

# Neither imperative stores yo or nosotros. Reflexive rows label usted and
# ustedes the same ("(se)" / "no se"), so the title distinguishes them.
SLOT_BY_TITLE = {
    "2e persoon enkelvoud": "tú",
    "3e persoon enkelvoud": "usted",
    "2e persoon meervoud": "vosotros",
    "3e persoon meervoud": "ustedes",
}
IMPERATIVO_KEYS = ("tú", "usted", "vosotros", "ustedes")
# Proclitic pronouns for a reflexive negative imperative built from the base verb.
REFLEXIVE_NEGATIVO_PREFIX = {
    "tú": "no te",
    "usted": "no se",
    "vosotros": "no os",
    "ustedes": "no se",
}

OUTPUT_FIELD_ORDER = [
    "verbo",
    "presente",
    "preterito-perfecto",
    "preterito-indefinido",
    "preterito-imperfecto",
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


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def conjugation_form(spans) -> str:
    """Pick one conjugation. When the site lists a spelling variant, keep the accented one."""
    if len(spans) == 1:
        return spans[0].get_text(strip=True)
    corrected = [
        span
        for span in spans
        if "conjugation-2" in (span.get("class") or [])
    ]
    chosen = corrected[-1] if corrected else spans[0]
    return chosen.get_text(strip=True)


def negativo_phrase(label: str, form: str) -> str:
    """Join the site's negation (and reflexive pronoun, when present) to the verb."""
    label = " ".join(label.split())
    if label.startswith("no "):
        return f"{label} {form}"
    return f"no {form}"


def parse_imperativo_table(html: str, section_id: str, negative: bool) -> Optional[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find("h3", id=section_id)
    if not section:
        return None

    table = section.find_next("table")
    if not table:
        return None

    forms: Dict[str, str] = {}

    for row in table.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue

        pronoun_span = th.find("span", class_="pronoun")
        title = pronoun_span.get("title", "") if pronoun_span else ""
        slot = SLOT_BY_TITLE.get(title)
        if not slot:
            continue

        conjugation_spans = td.find_all(
            "span", class_=lambda x: x and x.startswith("conjugation-")
        )
        if not conjugation_spans:
            continue
        form = conjugation_form(conjugation_spans)
        if not form:
            continue
        if negative:
            label = pronoun_span.get_text(strip=True) if pronoun_span else ""
            form = negativo_phrase(label, form)
        forms[slot] = form

    if all(key in forms for key in IMPERATIVO_KEYS):
        return {key: forms[key] for key in IMPERATIVO_KEYS}
    return None


def parse_imperativo_afirmativo(html: str) -> Optional[Dict[str, str]]:
    """Parse imperativo afirmativo (tú, usted, vosotros, ustedes) from conjugation HTML."""
    return parse_imperativo_table(html, IMPERATIVO_AFIRMATIVO_SECTION_ID, negative=False)


def parse_imperativo_negativo(html: str) -> Optional[Dict[str, str]]:
    """Parse imperativo negativo. Forms include 'no' and, for reflexives, the pronoun."""
    return parse_imperativo_table(html, IMPERATIVO_NEGATIVO_SECTION_ID, negative=True)


def fetch_page(verb: str) -> Optional[str]:
    params = {"verb": verb, "option": "com_verb", "task": "conjugate"}
    for verify in (True, False):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15, verify=verify)
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            continue
        except requests.RequestException:
            continue
        return resp.text
    return None


def fetch_imperativo_from_site(verb: str) -> Optional[Dict[str, Dict[str, str]]]:
    html = fetch_page(verb)
    if not html:
        return None
    afirmativo = parse_imperativo_afirmativo(html)
    negativo = parse_imperativo_negativo(html)
    if afirmativo and negativo:
        return {
            "imperativo-afirmativo": afirmativo,
            "imperativo-negativo": negativo,
        }
    return None


def fix_negativo_orthography(forms: Dict[str, str]) -> Dict[str, str]:
    """esfacil drops the tilde on some -ar vosotros forms (crieis for criéis)."""
    tu = forms["tú"].split()[-1]
    words = forms["vosotros"].split()
    vos = words[-1]
    if tu.endswith("es") and any(ch in tu for ch in "áéíóú") and vos.endswith("eis"):
        words[-1] = vos[:-3] + "éis"
        forms = dict(forms)
        forms["vosotros"] = " ".join(words)
    return forms


def reconcile_reflexive_negativo(
    reflexive_forms: Dict[str, str], base_forms: Dict[str, str]
) -> Dict[str, str]:
    """
    Some reflexive pages regularize a stem-changing verb (reñirse → reñas).
    When the usted stem disagrees with the base verb, rebuild from the base verb.
    """
    reflexive_usted = reflexive_forms["usted"].split()[-1]
    base_usted = base_forms["usted"].split()[-1]
    if strip_accents(reflexive_usted) == strip_accents(base_usted):
        return reflexive_forms
    return {
        slot: f"{REFLEXIVE_NEGATIVO_PREFIX[slot]} {base_forms[slot].split()[-1]}"
        for slot in IMPERATIVO_KEYS
    }


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


def with_reflexive_pronouns(base_negativo: Dict[str, str]) -> Dict[str, str]:
    return {
        slot: f"{REFLEXIVE_NEGATIVO_PREFIX[slot]} {base_negativo[slot].split()[-1]}"
        for slot in IMPERATIVO_KEYS
    }


def fetch_imperativo(infinitive: str) -> Optional[Dict[str, Dict[str, str]]]:
    seen = set()
    found: Optional[Dict[str, Dict[str, str]]] = None
    chosen: Optional[str] = None
    for candidate in imperativo_fetch_candidates(infinitive):
        if candidate in seen:
            continue
        seen.add(candidate)
        forms = fetch_imperativo_from_site(candidate)
        if forms:
            found = forms
            chosen = candidate
            break
    if not found:
        return None

    if is_reflexive(infinitive):
        base = strip_reflexive_suffix(infinitive)
        base_forms = found if chosen == base else fetch_imperativo_from_site(base)
        if base_forms:
            base_negativo = base_forms["imperativo-negativo"]
            if chosen == infinitive:
                found["imperativo-negativo"] = reconcile_reflexive_negativo(
                    found["imperativo-negativo"],
                    base_negativo,
                )
            else:
                found["imperativo-negativo"] = with_reflexive_pronouns(base_negativo)
    found["imperativo-negativo"] = fix_negativo_orthography(found["imperativo-negativo"])
    return found


def process_verbs(data: Iterable[dict]) -> List[dict]:
    def ordered_entry(entry: dict, forms: Dict[str, Dict[str, str]]) -> dict:
        temp = dict(entry)
        temp["imperativo-afirmativo"] = forms["imperativo-afirmativo"]
        temp["imperativo-negativo"] = forms["imperativo-negativo"]

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
                f"Unable to derive imperativo afirmativo/negativo "
                f"(tú/usted/vosotros/ustedes) for verb: {verbo}"
            )

        enriched.append(ordered_entry(entry, forms))
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Append imperativo afirmativo and negativo "
            "(tú, usted, vosotros, ustedes) to Spanish verbs JSON."
        )
    )
    parser.add_argument(
        "--input",
        default="Verbos.json",
        help="Input JSON file path (default: Verbos.json)",
    )
    parser.add_argument(
        "--output",
        default="Verbos-imperativo.json",
        help="Output JSON file path (default: Verbos-imperativo.json)",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched = process_verbs(data)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=4)

    print(
        f"Wrote {len(enriched)} verbs with imperativo afirmativo and negativo to {args.output}"
    )


if __name__ == "__main__":
    main()

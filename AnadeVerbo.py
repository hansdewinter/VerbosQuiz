#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import re
import unicodedata
import requests
from bs4 import BeautifulSoup
import deepl


JSON_FILE = "/Users/hans/Dropbox/Spaans/Verbos.json"
os.environ['DEEPL_API_KEY'] = '3f709804-413d-48ca-aa5c-ce0691c38bfc:fx'

BASE_URL = "https://www.esfacil.eu/nl/werkwoorden/vervoeging.html"
# Present tense of "estar"
ESTAR_PRESENT = ["estoy", "estás", "está", "estamos", "estáis", "están"]
# Reflexive pronouns aligned with person order
REFLEXIVE_PRONOUNS = ["me", "te", "se", "nos", "os", "se"]

# Ensure stdout uses UTF-8 encoding (Python 3.7+)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def translate_verb(translator, spanish_verb):
    """
    Translate a Spanish verb to Dutch using DeepL API.
    
    Args:
        translator: DeepL Translator instance
        spanish_verb: Spanish verb string to translate
        
    Returns:
        Dutch translation string, or None if translation fails
    """
    try:
        result = translator.translate_text(
            spanish_verb,
            source_lang="ES",
            target_lang="NL"
        )
        return result.text
    except deepl.exceptions.DeepLException as e:
        print(f"Error translating '{spanish_verb}': {e}")
        return None
    except Exception as e:
        print(f"Unexpected error translating '{spanish_verb}': {e}")
        return None


def extract_conjugations(verb, tiempo):
    """
    Extract conjugations for a verb and tense from esfacil.eu.
    
    Args:
        verb: Spanish verb string
        tiempo: Tense identifier (e.g., "indicativo-presente")
        
    Returns:
        List of conjugations, each as either:
        - Tuple (pronoun, conjugation) for reflexive verbs
        - String (conjugation only) for non-reflexive verbs
    """
    # Get the data
    url = f"https://www.esfacil.eu/nl/werkwoorden/vervoeging.html?verb={verb}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Ensure UTF-8 encoding
        response.encoding = 'utf-8'
        html_content = response.text
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the section with the specified tiempo
    tiempo_section = soup.find('h3', id=tiempo)
    
    if not tiempo_section:
        print(f"Could not find {tiempo} section for verb '{verb}'")
        return []
    
    # Find the table following this h3 tag
    table = tiempo_section.find_next('table')
    
    if not table:
        print(f"Could not find table in {tiempo} section for verb '{verb}'")
        return []
    
    # Find all table rows
    rows = table.find_all('tr')
    conjugations = []
    
    # Extract conjugations from each row
    for row in rows:
        # Find the th element (pronoun cell) and td element (conjugation cell)
        th = row.find('th')
        td = row.find('td')
        
        # Extract pronoun if present
        pronoun = None
        if th:
            pronoun_span = th.find('span', class_='pronoun')
            if pronoun_span:
                pronoun = pronoun_span.get_text(strip=True)
        
        if td:
            # Find all spans with class starting with "conjugation-"
            conjugation_spans = td.find_all('span', class_=lambda x: x and x.startswith('conjugation-'))
            
            if conjugation_spans:
                # For simple conjugations, get the text directly
                # For compound forms, get the full text from the td
                if len(conjugation_spans) == 1:
                    # Simple conjugation
                    conj_text = conjugation_spans[0].get_text(strip=True)
                else:
                    # Compound form - get all text from td
                    conj_text = td.get_text(strip=False)
                
                if conj_text:
                    # Strip whitespace from conj_text
                    conj_text = conj_text.strip()
                    # Add pronoun if available
                    if pronoun:
                        conjugations.append((pronoun, conj_text))
                    else:
                        conjugations.append(conj_text)
    
    return conjugations


def process_conjugations(conjugations, is_reflexive):
    """
    Process raw conjugations from extract_conjugations into final format.
    
    Args:
        conjugations: List from extract_conjugations (tuples or strings)
        is_reflexive: Boolean indicating if verb is reflexive
        
    Returns:
        List of conjugation strings
    """
    processed = []
    for conj in conjugations:
        if isinstance(conj, tuple):
            # Has pronoun (expected case)
            pronoun, conjugation = conj
            if is_reflexive:
                # For reflexive verbs, include the pronoun
                processed.append(f"{pronoun} {conjugation}".strip())
            else:
                # For non-reflexive verbs, use only the conjugation
                processed.append(conjugation.strip())
        else:
            # No pronoun (unexpected but handle gracefully)
            conjugation = conj.strip()
            if is_reflexive:
                print(f"Warning: Reflexive verb conjugation missing pronoun: {conjugation}")
            processed.append(conjugation)
    return processed


def remove_accents(text):
    """Strip accents from a string while keeping other characters intact."""
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def is_reflexive(infinitive):
    """Return True if the infinitive is reflexive (ends with 'se')."""
    return infinitive.endswith("se")


def strip_reflexive_suffix(infinitive):
    """Remove trailing 'se' from a reflexive infinitive."""
    return infinitive[:-2] if is_reflexive(infinitive) else infinitive


def fetch_gerundio_from_site(verb):
    """Query esfacil.eu for a verb gerundio. Returns None on failure."""
    params = {"verb": verb, "option": "com_verb", "task": "conjugate"}
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


def parse_gerundio(html):
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


def derive_regular_gerundio(infinitive):
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


def fetch_gerundio(infinitive):
    """
    Fetch gerundio with fallbacks:
    - Try non-reflexive form first.
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


def strip_reflexive_from_gerundio(gerundio):
    """Remove trailing reflexive pronouns from a gerundio and normalize accents."""
    lowered = gerundio.lower()
    for pronoun in ("se", "me", "te", "nos", "os"):
        if lowered.endswith(pronoun):
            trimmed = gerundio[: -len(pronoun)]
            return remove_accents(trimmed)
    return gerundio


def build_presente_progresivo(gerundio, reflexive):
    """Build presente progresivo for the verb, handling reflexive forms."""
    if reflexive:
        clean_ger = strip_reflexive_from_gerundio(gerundio)
        return [
            f"{pron} {estar} {clean_ger}"
            for pron, estar in zip(REFLEXIVE_PRONOUNS, ESTAR_PRESENT)
        ]
    return [f"{estar} {gerundio}" for estar in ESTAR_PRESENT]


def check_verb_exists(verb_data, verb):
    """
    Check if a verb already exists in the JSON data (case-sensitive).
    
    Args:
        verb_data: List of verb dictionaries
        verb: Verb string to check
        
    Returns:
        True if verb exists, False otherwise
    """
    for entry in verb_data:
        if isinstance(entry, dict) and entry.get("verbo") == verb:
            return True
    return False


def main():
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Error: Please provide a Spanish verb as an argument.")
        print("Usage: python AnadeVerbo.py <verb>")
        sys.exit(1)
    
    verb = sys.argv[1].strip()
    if not verb:
        print("Error: Verb cannot be empty.")
        sys.exit(1)
    
    # Load Verbos.json
    json_file = JSON_FILE
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found in current directory.")
        sys.exit(1)
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            verb_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {json_file}: {e}")
        sys.exit(1)
    
    if not isinstance(verb_data, list):
        print(f"Error: {json_file} should contain a JSON array.")
        sys.exit(1)
    
    # Check if verb already exists
    if check_verb_exists(verb_data, verb):
        print(f"The verb '{verb}' already exists in {json_file}.")
        print("Aborting. Please use a different verb or check the existing entry.")
        sys.exit(1)
    
    print(f"Adding new verb: {verb}")
    print("Fetching data...")
    
    # Check for DeepL API key
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        print("Error: DEEPL_API_KEY environment variable is not set.")
        print("Please set it using: export DEEPL_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Initialize DeepL translator
    try:
        translator = deepl.Translator(api_key)
    except Exception as e:
        print(f"Error initializing DeepL translator: {e}")
        sys.exit(1)
    
    # Get Dutch translation
    print("  - Getting Dutch translation...")
    dutch_translation = translate_verb(translator, verb)
    if not dutch_translation:
        print("Error: Could not get Dutch translation. Aborting.")
        sys.exit(1)
    
    # Determine if verb is reflexive
    verb_is_reflexive = is_reflexive(verb)

    # Get presente progresivo
    print("  - Getting presente-progresivo...")
    gerundio = fetch_gerundio(verb)
    if not gerundio:
        print("Error: Could not determine gerundio. Aborting.")
        sys.exit(1)
    presente_progresivo = build_presente_progresivo(
        gerundio=gerundio,
        reflexive=verb_is_reflexive
    )
    
    # Get conjugations for three tenses
    tiempo_mapping = {
        "indicativo-presente": "presente",
        "indicativo-preterito-perfecto": "preterito-perfecto",
        "indicativo-preterito-indefinido": "preterito-indefinido"
    }
    
    conjugations_data = {}
    for tiempo_id, json_key in tiempo_mapping.items():
        print(f"  - Getting {json_key} conjugations...")
        raw_conjugations = extract_conjugations(verb, tiempo_id)
        
        if not raw_conjugations:
            print(f"Error: Could not extract {json_key} conjugations. Aborting.")
            sys.exit(1)
        
        processed_conjugations = process_conjugations(raw_conjugations, verb_is_reflexive)
        
        # Ensure we have exactly 6 conjugations
        if len(processed_conjugations) != 6:
            print(f"Warning: Expected 6 conjugations for {json_key}, got {len(processed_conjugations)}")
            # Continue anyway, but show the count
        
        conjugations_data[json_key] = processed_conjugations
    
    # Create the new verb entry
    new_entry = {
        "verbo": verb,
        "presente": conjugations_data["presente"],
        "preterito-perfecto": conjugations_data["preterito-perfecto"],
        "preterito-indefinido": conjugations_data["preterito-indefinido"],
        "presente-progresivo": presente_progresivo,
        "dutch": dutch_translation
    }
    
    # Display the entry and ask for confirmation
    print("\n" + "="*70)
    print("New verb entry to be added:")
    print("="*70)
    print(json.dumps(new_entry, indent=4, ensure_ascii=False))
    print("="*70)
    
    # Ask for confirmation
    while True:
        response = input("\nDo you want to add this verb to Verbos.json? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            break
        elif response in ['n', 'no']:
            print("Aborted. Verb not added.")
            sys.exit(0)
        else:
            print("Please enter 'y' or 'n'.")
    
    # Add the entry to the data at the start of the array
    verb_data.insert(0, new_entry)
    
    # Save back to JSON file
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(verb_data, f, indent=4, ensure_ascii=False)
        print(f"\nSuccessfully added '{verb}' to {json_file}!")
    except Exception as e:
        print(f"\nError writing to {json_file}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

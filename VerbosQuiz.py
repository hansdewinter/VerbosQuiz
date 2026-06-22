#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spanish Verb Conjugation Quiz
Reads verbs from Verbos.json and provides interactive quiz with color-coded feedback
"""

import argparse
import json
import random
import sys
import unicodedata
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.worksheet import Worksheet

APP_VERSION = "1.2.0"

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

# Person labels for Spanish conjugations
PERSONS = [
    "yo",
    "tú",
    "él/ella/usted",
    "nosotros",
    "vosotros",
    "ellos/ellas/ustedes"
]

# Tense labels mapping
TENSE_LABELS = {
    "presente": "Present",
    "preterito-perfecto": "Pretérito Perfecto",
    "preterito-indefinido": "Pretérito Indefinido",
    "preterito-imperfecto": "Pretérito Imperfecto",
    "futuro-simple": "Futuro Simple",
    "presente-progresivo": "Presente Progresivo",
    "imperativo-afirmativo": "Imperativo afirmativo",
}


def capitalize_first(text: str) -> str:
    """Capitalize only the first character, leaving the rest intact."""
    return text[:1].upper() + text[1:] if text else ""


def normalize_verb(name: str) -> str:
    """Normalize verb strings for matching (remove hints/quotes, lowercase)."""
    cleaned = name.strip()
    for sep in ['"', " "]:
        idx = cleaned.find(sep)
        if idx != -1:
            cleaned = cleaned[:idx].strip()
            break
    return cleaned.lower()


def sanitize_sheet_title(raw_title: str, fallback: str = "Sheet") -> str:
    """Excel sheet titles max 31 chars and forbid certain characters."""
    title = raw_title.replace('"', " ")
    for ch in r"[]:*?/\\":  # forbidden chars
        title = title.replace(ch, " ")
    title = title.strip() or fallback
    if len(title) > 31:
        title = title[:31]
    return title


def populate_sheet(ws: Worksheet, verb_entry: dict) -> None:
    """Build sheet layout and fill conjugations (no template dependency)."""
    verb_name = capitalize_first(verb_entry.get("verbo", ""))

    headers = [
        ("A1", verb_name),
        ("B1", "Present"),
        ("C1", "Pretérito Perfecto"),
        ("D1", "Pretérito Indefinido"),
        ("E1", "Pretérito Imperfecto"),
        ("F1", "Futuro Simple"),
        ("G1", "Presente Progresivo"),
        ("H1", "Imperativo afirmativo (tú / vosotros)"),
    ]
    header_font = Font(bold=True)
    center = Alignment(horizontal="center")
    for cell_ref, value in headers:
        cell = ws[cell_ref]
        cell.value = value
        cell.font = header_font
        cell.alignment = center

    pronouns = [
        "yo",
        "tú",
        "él/ella/usted",
        "nosotros",
        "vosotros",
        "ellos/ellas/ustedes",
    ]
    for idx, pronoun in enumerate(pronouns, start=2):
        ws.cell(row=idx, column=1, value=pronoun)

    tenses = [
        ("presente", 2),  # column B
        ("preterito-perfecto", 3),  # column C
        ("preterito-indefinido", 4),  # column D
        ("preterito-imperfecto", 5),  # column E
        ("futuro-simple", 6),  # column F
        ("presente-progresivo", 7),  # column G
    ]

    for row_idx in range(6):  # rows 2-7 contain pronoun lines
        excel_row = row_idx + 2
        for key, col in tenses:
            forms = verb_entry.get(key, [])
            value = forms[row_idx] if row_idx < len(forms) else ""
            ws.cell(row=excel_row, column=col, value=value)

    imperativo = verb_entry.get("imperativo-afirmativo")
    if isinstance(imperativo, dict):
        # rows: 2=yo, 3=tú, 4=él…, 5=nosotros, 6=vosotros, 7=ellos…
        ws.cell(row=3, column=8, value=imperativo.get("tu", ""))
        ws.cell(row=6, column=8, value=imperativo.get("vosotros", ""))

    widths = {"A": 18, "B": 18, "C": 22, "D": 22, "E": 22, "F": 22, "G": 22, "H": 26}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def build_verb_lookup(verbs):
    """Map verbs by normalized infinitive for quick lookup."""
    lookup = {}
    for entry in verbs:
        norm = normalize_verb(entry.get("verbo", ""))
        if not norm:
            continue
        lookup.setdefault(norm, entry)
    return lookup


def build_workbook(entries):
    """Create a workbook with one sheet per verb entry."""
    wb = Workbook()
    default_ws = wb.active
    wb.remove(default_ws)

    for entry in entries:
        title = sanitize_sheet_title(entry.get("verbo", ""))
        ws = wb.create_sheet(title=title)
        populate_sheet(ws, entry)

    return wb


def export_incorrect_verbs_excel(incorrect_verbs, verbs, output_path: Path) -> None:
    """Write incorrect verbs to an Excel workbook (one sheet per verb)."""
    if not incorrect_verbs:
        return

    lookup = build_verb_lookup(verbs)
    missing = []
    entries = []
    for verb in sorted(incorrect_verbs, key=normalize_verb):
        entry = lookup.get(normalize_verb(verb))
        if entry is None:
            missing.append(verb)
            continue
        entries.append(entry)

    if missing:
        missing_str = ", ".join(missing)
        print(f"Warning: Verbs not found in JSON: {missing_str}")

    if not entries:
        print("No incorrect verbs could be exported.")
        return

    wb = build_workbook(entries)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    print(f"Created {output_path} with {len(entries)} sheets.")


def load_verbs():
    """Load verbs from Verbos.json file with UTF-8 encoding."""
    json_path = Path(__file__).resolve().parent / "Verbos.json"
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            verbs = json.load(f)
        if not verbs:
            print(f"Error: {json_path} is empty.")
            sys.exit(1)
        return verbs
    except FileNotFoundError:
        print(f"Error: {json_path} file not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_path}: {e}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error: Encoding issue when reading {json_path}: {e}")
        sys.exit(1)


def get_random_verb(verbs):
    """Select a random verb from the list."""
    return random.choice(verbs)


def find_verb(verbs, verb_name):
    """
    Find a verb by name (case-insensitive, normalized).
    Returns the verb dictionary if found, None otherwise.
    """
    verb_name_norm = normalize_string(verb_name)
    for verb in verbs:
        if normalize_string(verb['verbo']) == verb_name_norm:
            return verb
    return None


def get_random_person():
    """Return random person index and label."""
    index = random.randint(0, 5)
    return index, PERSONS[index]


def normalize_string(s):
    """Normalize string for comparison (case-insensitive, NFC normalization)."""
    return unicodedata.normalize('NFC', s.lower().strip())


REFLEXIVE_PRONOUNS = ("nos", "os", "me", "te", "se")
ESTAR_FORMS = frozenset({"estoy", "estás", "está", "estamos", "estáis", "están"})


def strip_accents(text: str) -> str:
    """Remove diacritics to allow accent-insensitive comparisons."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


ESTAR_FORMS_NORMALIZED = frozenset(strip_accents(f) for f in ESTAR_FORMS)


def detach_reflexive_pronoun(word: str) -> tuple[str, str | None]:
    """Strip a trailing reflexive pronoun from a gerund token."""
    lowered = word.lower()
    for pronoun in REFLEXIVE_PRONOUNS:
        if lowered.endswith(pronoun):
            return word[: -len(pronoun)], pronoun
    return word, None


def parse_presente_progresivo(answer: str) -> tuple[str, str, str] | None:
    """
    Parse a reflexive presente progresivo answer into (pronoun, estar, gerund).
    Accepts prefix form (se están enfermando) or suffix form (están enfermándose).
    """
    parts = normalize_string(answer).split()
    if len(parts) == 3:
        pronoun, estar, gerund = parts
        if pronoun in REFLEXIVE_PRONOUNS and strip_accents(estar) in ESTAR_FORMS_NORMALIZED:
            return pronoun, strip_accents(estar), strip_accents(gerund)
    elif len(parts) == 2:
        estar, gerund_with_pronoun = parts
        if strip_accents(estar) in ESTAR_FORMS_NORMALIZED:
            gerund, pronoun = detach_reflexive_pronoun(gerund_with_pronoun)
            if pronoun is not None:
                return pronoun, strip_accents(estar), strip_accents(gerund)
    return None


def answers_match(correct: str, user: str, tense: str) -> bool:
    """Compare answers; accept both reflexive pronoun placements in presente progresivo."""
    if normalize_string(correct) == normalize_string(user):
        return True
    if tense == "presente-progresivo":
        parsed_correct = parse_presente_progresivo(correct)
        parsed_user = parse_presente_progresivo(user)
        if parsed_correct and parsed_user:
            return parsed_correct == parsed_user
    return False


def feedback_reference(correct: str, user: str, tense: str) -> str:
    """Pick the best reference string for color-coded feedback."""
    if normalize_string(correct) == normalize_string(user):
        return correct
    if tense == "presente-progresivo":
        parsed_correct = parse_presente_progresivo(correct)
        parsed_user = parse_presente_progresivo(user)
        if parsed_correct and parsed_user and parsed_correct == parsed_user:
            return user
    return correct


def compare_answers(correct, user_input):
    """
    Compare two strings character by character and return color-coded result for the correct answer.
    Returns a string with green for characters that match the user input and red for incorrect ones.
    """
    correct_norm = normalize_string(correct)
    user_norm = normalize_string(user_input)
    
    result = []
    max_len = max(len(correct_norm), len(user_norm))
    
    for i in range(max_len):
        if i < len(correct_norm) and i < len(user_norm):
            if correct_norm[i] == user_norm[i]:
                result.append(f"{GREEN}{correct[i] if i < len(correct) else ''}{RESET}")
            else:
                result.append(f"{RED}{correct[i] if i < len(correct) else ''}{RESET}")
        elif i < len(correct_norm):
            result.append(f"{RED}{correct[i]}{RESET}")
        else:
            pass
    
    return ''.join(result)


def print_usage_summary(usage_counts):
    """Print a summary of how many times each verb was used."""
    if not usage_counts:
        print("No verb usage recorded.")
        return
    
    print("\nVerb usage summary (alphabetical):")
    longest = max(len(name) for name in usage_counts)
    for verb_name in sorted(usage_counts):
        count = usage_counts[verb_name]
        padded = verb_name.ljust(longest)
        print(f"  {padded}  {count}")


def print_incorrect_summary(usage_counts, incorrect_verbs):
    """Print a list of verbs answered incorrectly at least once."""
    if not incorrect_verbs:
        print("\nIncorrect verbs: none 🎉")
        return
    
    print("\nIncorrect verbs (alphabetical):")
    longest = max(len(name) for name in incorrect_verbs)
    for verb_name in sorted(incorrect_verbs):
        count = usage_counts.get(verb_name, 0)
        padded = verb_name.ljust(longest)
        print(f"  {RED}{padded}{RESET}  {count}")


def ask_question(verb, tense, person_label, correct_answer, show_dutch=False):
    """
    Ask a conjugation question and return True if correct, False otherwise.
    """
    verb_name = verb['verbo']
    dutch_translation = verb['dutch']

    tense_label = TENSE_LABELS.get(tense, tense).lower()
    display_name = dutch_translation if show_dutch else verb_name

    print("\n" + "=" * 60)
    print(f"Conjugate '{display_name}' in '{tense_label}':")
    
    while True:
        try:
            user_answer = input(f"{person_label}: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise

        if show_dutch and user_answer == '?':
            print(f"Hint: the Spanish verb is '{verb_name}'")
            continue

        break
    
    is_correct = answers_match(correct_answer, user_answer, tense)
    reference = feedback_reference(correct_answer, user_answer, tense)

    print(
        f"\nCorrect answer ({verb_name}): {compare_answers(reference, user_answer)}"
    )
    print(f"Your answer:    {user_answer}")
    if (
        is_correct
        and tense == "presente-progresivo"
        and normalize_string(correct_answer) != normalize_string(user_answer)
    ):
        print(f"Also accepted: {correct_answer}")

    if is_correct:
        print(f"{GREEN}✓ Correct!{RESET}")
    else:
        print(f"{RED}✗ Incorrect{RESET}")
    
    return is_correct


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Spanish Verb Conjugation Quiz - Practice Spanish verb conjugations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Use random tense (default)
  %(prog)s --tense=present           # Practice present tense only
  %(prog)s --tense=perfecto          # Practice Pretérito Perfecto only
  %(prog)s --tense=indefinido        # Practice Pretérito Indefinido only
  %(prog)s --tense=imperfecto        # Practice Pretérito Imperfecto only
  %(prog)s --tense=futuro            # Practice Futuro Simple only
  %(prog)s --tense=progresivo        # Practice Presente Progresivo (estar + gerundio) only
  %(prog)s --tense=imperativo        # Practice imperativo afirmativo (tú and vosotros only)
  %(prog)s --verb=hablar             # Practice only 'hablar' with all tenses
  %(prog)s --verb=ser                # Practice only 'ser' with all tenses
  %(prog)s --dutch                   # Show Dutch translation instead of Spanish verb
  %(prog)s --dutch --tense=present   # Show Dutch translation with present tense only
        """
    )
    
    parser.add_argument(
        '--tense',
        choices=[
            'random',
            'present',
            'perfecto',
            'indefinido',
            'imperfecto',
            'futuro',
            'progresivo',
            'imperativo',
        ],
        default='random',
        help='Select tense mode: random (default), present, perfecto, indefinido, imperfecto, futuro, progresivo, or imperativo (tú/vosotros)'
    )
    
    parser.add_argument(
        '--verb',
        type=str,
        default=None,
        help='Practice a specific verb only (uses all tenses and persons)'
    )
    
    parser.add_argument(
        '--dutch',
        action='store_true',
        help='Show Dutch translation instead of Spanish verb name in prompts'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f"%(prog)s {APP_VERSION}",
        help='Display the current version and exit'
    )
    
    return parser.parse_args()


def run_quiz(verbs, tense_mode='random', specific_verb=None, show_dutch=False):
    """Main quiz loop."""
    if specific_verb is not None:
        verb_list = [specific_verb]
        tense_mode = 'random'
    else:
        verb_list = verbs

    has_imperativo_data = any(
        isinstance(v.get("imperativo-afirmativo"), dict)
        and v["imperativo-afirmativo"].get("tu")
        and v["imperativo-afirmativo"].get("vosotros")
        for v in verb_list
    )

    if tense_mode == "imperativo" and not has_imperativo_data:
        print(
            "Error: No verbs in the practice set have imperativo-afirmativo "
            "(tú and vosotros). Update Verbos.json or pick another tense."
        )
        sys.exit(1)

    if tense_mode == 'random':
        random_tenses = [
            "presente",
            "preterito-perfecto",
            "preterito-indefinido",
            "preterito-imperfecto",
            "futuro-simple",
            "presente-progresivo",
            "imperativo-afirmativo",
        ]
        if not has_imperativo_data:
            random_tenses = [
                t for t in random_tenses if t != "imperativo-afirmativo"
            ]

        def get_tense():
            return random.choice(random_tenses)
    elif tense_mode == 'present':
        def get_tense():
            return "presente"
    elif tense_mode == 'perfecto':
        def get_tense():
            return "preterito-perfecto"
    elif tense_mode == 'indefinido':
        def get_tense():
            return "preterito-indefinido"
    elif tense_mode == 'imperfecto':
        def get_tense():
            return "preterito-imperfecto"
    elif tense_mode == 'futuro':
        def get_tense():
            return "futuro-simple"
    elif tense_mode == 'progresivo':
        def get_tense():
            return "presente-progresivo"
    elif tense_mode == 'imperativo':
        def get_tense():
            return "imperativo-afirmativo"

    total_questions = 0
    correct_answers = 0
    usage_counts = {}
    incorrect_verbs = set()
    output_path = Path(__file__).resolve().parent / "VerbosErrores.xlsx"
    
    try:
        while True:
            verb = get_random_verb(verb_list)
            verb_name = verb['verbo']
            tense = get_tense()

            if tense == "imperativo-afirmativo":
                imper = verb.get("imperativo-afirmativo")
                if not imper or not isinstance(imper, dict):
                    continue
                slot = random.choice(["tu", "vosotros"])
                person_label = "tú" if slot == "tu" else "vosotros"
                correct_answer = imper.get(slot)
                if not correct_answer:
                    continue
            else:
                person_index, person_label = get_random_person()
                forms = verb.get(tense)
                if not forms or not isinstance(forms, list) or person_index >= len(forms):
                    continue
                correct_answer = forms[person_index]

            try:
                is_correct = ask_question(
                    verb, tense, person_label, correct_answer, show_dutch
                )
                usage_counts[verb_name] = usage_counts.get(verb_name, 0) + 1
                total_questions += 1
                if is_correct:
                    correct_answers += 1
                else:
                    incorrect_verbs.add(verb_name)
                percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
                print(f"\n{GREEN}Score: {correct_answers}/{total_questions} ({percentage:.1f}%){RESET}\n")
            except (EOFError, KeyboardInterrupt):
                raise
            
    except KeyboardInterrupt:
        print("\n")
        print("Quiz interrupted by user")
        print("=" * 60)
        if total_questions > 0:
            percentage = (correct_answers / total_questions * 100)
            print(f"Final Score: {correct_answers}/{total_questions} ({percentage:.1f}%)")
        else:
            print("No questions answered.")
        print("=" * 60)
        print_usage_summary(usage_counts)
        print_incorrect_summary(usage_counts, incorrect_verbs)
        export_incorrect_verbs_excel(incorrect_verbs, verbs, output_path)
        sys.exit(0)
    except EOFError:
        print("\n\n" + "=" * 60)
        print("Quiz ended")
        print("=" * 60)
        if total_questions > 0:
            percentage = (correct_answers / total_questions * 100)
            print(f"Final Score: {correct_answers}/{total_questions} ({percentage:.1f}%)")
        else:
            print("No questions answered.")
        print("=" * 60)
        print_usage_summary(usage_counts)
        print_incorrect_summary(usage_counts, incorrect_verbs)
        export_incorrect_verbs_excel(incorrect_verbs, verbs, output_path)
        sys.exit(0)


def main():
    """Main entry point."""
    try:
        args = parse_arguments()

        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stdin, 'reconfigure') and sys.stdin.encoding != 'utf-8':
            sys.stdin.reconfigure(encoding='utf-8')

        json_path = Path(__file__).resolve().parent / "Verbos.json"
        print(f"Loading verbs from {json_path}...")
        verbs = load_verbs()
        print(f"Loaded {len(verbs)} verbs.")

        specific_verb = None
        if args.verb:
            specific_verb = find_verb(verbs, args.verb)
            if specific_verb is None:
                print(f"Error: Verb '{args.verb}' not found in {json_path}.")
                print("Please check the spelling and try again.")
                sys.exit(1)
            print(f"Practicing verb: {specific_verb['verbo']} ({specific_verb.get('dutch', 'N/A')})")
            print("Using all tenses; imperativo afirmativo only asks tú and vosotros.")
        else:
            tense_display = {
                'random': 'Random tense',
                'present': 'Present tense',
                'perfecto': 'Pretérito Perfecto',
                'indefinido': 'Pretérito Indefinido',
                'imperfecto': 'Pretérito Imperfecto',
                'futuro': 'Futuro Simple',
                'progresivo': 'Presente Progresivo',
                'imperativo': 'Imperativo afirmativo (tú / vosotros)',
            }
            print(f"Tense mode: {tense_display[args.tense]}")
        
        print(
            "\nNote: In most terminals you can type accents by entering the accent key first,\n"
            "then the letter (e.g., ' + a = á). An umlaut is entered with the \" character.\n"
            "You can also paste accented characters.\n"
        )
        if args.dutch:
            print("Tip: Enter '?' to reveal the Spanish verb before answering.\n")
        
        run_quiz(verbs, args.tense, specific_verb, args.dutch)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

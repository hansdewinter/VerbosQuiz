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

APP_VERSION = "1.0.0"

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
    "presente-progresivo": "Presente Progresivo"
}


def load_verbs():
    """Load verbs from Verbos.json file with UTF-8 encoding."""
    try:
        with open('/Users/hans/Dropbox/Spaans/Verbos.json', 'r', encoding='utf-8') as f:
            verbs = json.load(f)
        if not verbs:
            print("Error: /Users/hans/Dropbox/Spaans/Verbos.json is empty.")
            sys.exit(1)
        return verbs
    except FileNotFoundError:
        print("Error: /Users/hans/Dropbox/Spaans/Verbos.json file not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in /Users/hans/Dropbox/Spaans/Verbos.json: {e}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error: Encoding issue when reading /Users/hans/Dropbox/Spaans/Verbos.json: {e}")
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


def get_random_tense():
    """Return random tense key."""
    tenses = [
        "presente",
        "preterito-perfecto",
        "preterito-indefinido",
        "presente-progresivo",
    ]
    return random.choice(tenses)


def normalize_string(s):
    """Normalize string for comparison (case-insensitive, NFC normalization)."""
    return unicodedata.normalize('NFC', s.lower().strip())


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


def ask_question(verb, tense, person_index, person_label, show_dutch=False):
    """
    Ask a conjugation question and return True if correct, False otherwise.
    """
    verb_name = verb['verbo']
    dutch_translation = verb['dutch']
    correct_answer = verb[tense][person_index]
    
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
    
    is_correct = normalize_string(correct_answer) == normalize_string(user_answer)

    print(f"\nCorrect answer: {compare_answers(correct_answer, user_answer)}")
    print(f"Your answer:    {user_answer}")
    
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
  %(prog)s --tense=progresivo        # Practice Presente Progresivo (estar + gerundio) only
  %(prog)s --verb=hablar             # Practice only 'hablar' with all tenses
  %(prog)s --verb=ser                # Practice only 'ser' with all tenses
  %(prog)s --dutch                   # Show Dutch translation instead of Spanish verb
  %(prog)s --dutch --tense=present   # Show Dutch translation with present tense only
        """
    )
    
    parser.add_argument(
        '--tense',
        choices=['random', 'present', 'perfecto', 'indefinido', 'progresivo'],
        default='random',
        help='Select tense mode: random (default), present, perfecto, indefinido, or progresivo'
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

    if tense_mode == 'random':
        def get_tense():
            return get_random_tense()
    elif tense_mode == 'present':
        def get_tense():
            return "presente"
    elif tense_mode == 'perfecto':
        def get_tense():
            return "preterito-perfecto"
    elif tense_mode == 'indefinido':
        def get_tense():
            return "preterito-indefinido"
    elif tense_mode == 'progresivo':
        def get_tense():
            return "presente-progresivo"
    
    total_questions = 0
    correct_answers = 0
    usage_counts = {}
    incorrect_verbs = set()
    
    try:
        while True:
            verb = get_random_verb(verb_list)
            verb_name = verb['verbo']
            person_index, person_label = get_random_person()
            tense = get_tense()

            try:
                is_correct = ask_question(verb, tense, person_index, person_label, show_dutch)
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
        sys.exit(0)


def main():
    """Main entry point."""
    try:
        args = parse_arguments()

        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stdin, 'reconfigure') and sys.stdin.encoding != 'utf-8':
            sys.stdin.reconfigure(encoding='utf-8')

        print("Loading verbs from /Users/hans/Dropbox/Spaans/Verbos.json...")
        verbs = load_verbs()
        print(f"Loaded {len(verbs)} verbs.")

        specific_verb = None
        if args.verb:
            specific_verb = find_verb(verbs, args.verb)
            if specific_verb is None:
                print(f"Error: Verb '{args.verb}' not found in /Users/hans/Dropbox/Spaans/Verbos.json.")
                print("Please check the spelling and try again.")
                sys.exit(1)
            print(f"Practicing verb: {specific_verb['verbo']} ({specific_verb.get('dutch', 'N/A')})")
            print("Using all tenses and persons.")
        else:
            tense_display = {
                'random': 'Random tense',
                'present': 'Present tense',
                'perfecto': 'Pretérito Perfecto',
                'indefinido': 'Pretérito Indefinido',
                'progresivo': 'Presente Progresivo'
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

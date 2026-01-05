#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spanish Verb Conjugation Quiz
Reads verbs from Verbos.json and provides interactive quiz with color-coded feedback
"""

APP_VERSION = "1.0.0"

import argparse
import json
import random
import sys
import unicodedata
import termios
import tty

# On macOS, Option key combinations produce:
# Option+e → combining acute accent (U+0301) then vowel → á, é, í, ó, ú
# Option+a → å (U+00E5) - convert to á
# Option+i → î (U+00EE) - convert to í
# Option+o → ø (U+00F8) - convert to ó
# Option+u → combining diaeresis (U+0308) then u → ü, or directly ü (U+00FC)
# Option+n → ñ (U+00F1) - already correct for Spanish

def get_input(prompt_text=""):
    """
    Custom input function that handles Option+key combinations for accented characters.
    Supports: á, é, í, ó, ú, ü, ñ (and their uppercase variants)
    
    macOS Option key combinations:
    - Option+e then vowel → á, é, í, ó, ú
    - Option+a → å → á
    - Option+i → î → í
    - Option+o → ø → ó
    - Option+u then u → ü
    - Option+n → ñ (already correct)
    """
    if sys.platform == 'win32':
        # On Windows, use standard input
        return input(prompt_text)
    
    # For Unix/macOS, use custom input handler with raw mode
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        # Set terminal to raw mode for character-by-character input
        tty.setraw(fd)
        
        sys.stdout.write(prompt_text)
        sys.stdout.flush()
        
        result = []
        waiting_for_vowel = False  # True when Option+e was pressed (waiting for vowel)
        waiting_for_u = False  # True when Option+u was pressed (waiting for u to make ü)
        
        # Accent mappings for vowels after Option+e
        accent_map = {
            'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ú',
            'A': 'Á', 'E': 'É', 'I': 'Í', 'O': 'Ó', 'U': 'Ú'
        }
        
        def get_char_code(char):
            """Safely get character code, handling empty strings and errors."""
            if not char:
                return None
            try:
                return ord(char)
            except (TypeError, ValueError):
                return None
        
        def convert_option_char(char):
            """Convert characters from Option key combinations to Spanish accents."""
            if not char:
                return char
            
            ch_ord = get_char_code(char)
            if ch_ord is None:
                return char
            
            # Option+a → å (U+00E5) → convert to á
            if ch_ord == 0x00E5 or char == 'å':
                return 'á'
            if ch_ord == 0x00C5 or char == 'Å':
                return 'Á'
            
            # Option+i → î (U+00EE) → convert to í
            if ch_ord == 0x00EE or char == 'î':
                return 'í'
            if ch_ord == 0x00CE or char == 'Î':
                return 'Í'
            
            # Option+o → ø (U+00F8) → convert to ó
            if ch_ord == 0x00F8 or char == 'ø':
                return 'ó'
            if ch_ord == 0x00D8 or char == 'Ø':
                return 'Ó'
            
            # Option+u → combining diaeresis then u → ü (handled separately)
            # Direct ü (U+00FC) - already correct for Spanish, keep as-is
            # Option+n → ñ (U+00F1) - already correct for Spanish, keep as-is
            
            return char
        
        def is_combining_acute(char):
            """Check if character is a combining acute accent (from Option+e)."""
            ch_ord = get_char_code(char)
            if ch_ord is None:
                return False
            # U+0301 = Combining Acute Accent
            # U+00B4 = Acute Accent (might be used in some terminals)
            return (ch_ord == 0x0301 or ch_ord == 0x00B4)
        
        def is_combining_diaeresis(char):
            """Check if character is a combining diaeresis (from Option+u)."""
            ch_ord = get_char_code(char)
            if ch_ord is None:
                return False
            # U+0308 = Combining Diaeresis
            # U+00A8 = Diaeresis (might be used in some terminals)
            return (ch_ord == 0x0308 or ch_ord == 0x00A8)
        
        while True:
            try:
                # Read one character (handles UTF-8 multi-byte sequences correctly)
                ch = sys.stdin.read(1)
                
                # Handle empty/EOF
                if not ch:
                    break
                
                # Handle control characters
                if ch == '\r' or ch == '\n':  # Enter key
                    break
                elif ch in ('\x7f', '\x08', '\b'):  # Backspace (DEL or BS key)
                    if result:
                        result.pop()
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                    waiting_for_vowel = False
                    waiting_for_u = False
                    continue
                elif ch == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                elif ch == '\x04':  # Ctrl+D
                    raise EOFError
                
                # Check if this is a combining acute accent (Option+e sends this)
                if is_combining_acute(ch):
                    # Option+e was pressed - wait for next character (should be vowel)
                    waiting_for_vowel = True
                    continue
                
                # Check if this is a combining diaeresis (Option+u sends this)
                if is_combining_diaeresis(ch):
                    # Option+u was pressed - wait for next character (should be u to make ü)
                    waiting_for_u = True
                    continue
                
                # Handle if we're waiting for a vowel after Option+e
                if waiting_for_vowel:
                    if len(ch) > 0 and ch.lower() in 'aeiou':
                        # Apply accent to the vowel
                        accented = accent_map.get(ch, ch)
                        result.append(accented)
                        sys.stdout.write(accented)
                        sys.stdout.flush()
                    else:
                        # Not a vowel - convert and add the character as-is
                        converted = convert_option_char(ch)
                        result.append(converted)
                        sys.stdout.write(converted)
                        sys.stdout.flush()
                    waiting_for_vowel = False
                    continue
                
                # Handle if we're waiting for u after Option+u (to make ü)
                if waiting_for_u:
                    if len(ch) > 0 and ch.lower() == 'u':
                        # Apply diaeresis to u → ü
                        umlaut = 'ü' if ch == 'u' else 'Ü'
                        result.append(umlaut)
                        sys.stdout.write(umlaut)
                        sys.stdout.flush()
                    else:
                        # Not u - convert and add the character as-is
                        converted = convert_option_char(ch)
                        result.append(converted)
                        sys.stdout.write(converted)
                        sys.stdout.flush()
                    waiting_for_u = False
                    continue
                
                # Check for characters that need conversion (Option+a, Option+i, Option+o)
                converted = convert_option_char(ch)
                if converted != ch:
                    result.append(converted)
                    sys.stdout.write(converted)
                    sys.stdout.flush()
                else:
                    # Normal character (including ü, ñ, regular letters, and numbers)
                    result.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                    
            except (EOFError, KeyboardInterrupt):
                raise
            except Exception as e:
                # Handle any unexpected errors gracefully
                # Still add the character if possible
                if ch:
                    result.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                waiting_for_vowel = False
                waiting_for_u = False
        
        sys.stdout.write('\n')
        sys.stdout.flush()
        return ''.join(result)
        
    finally:
        # Restore terminal settings
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

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
    "preterito-indefinido": "Pretérito Indefinido"
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
    tenses = ["presente", "preterito-perfecto", "preterito-indefinido"]
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
    
    # Build color-coded string for the correct answer
    result = []
    max_len = max(len(correct_norm), len(user_norm))
    
    for i in range(max_len):
        if i < len(correct_norm) and i < len(user_norm):
            if correct_norm[i] == user_norm[i]:
                result.append(f"{GREEN}{correct[i] if i < len(correct) else ''}{RESET}")
            else:
                result.append(f"{RED}{correct[i] if i < len(correct) else ''}{RESET}")
        elif i < len(correct_norm):
            # Extra characters in correct answer (missing in user input)
            result.append(f"{RED}{correct[i]}{RESET}")
        else:
            # User input has extra characters (not shown in correct answer)
            # Don't add anything for these positions
            pass
    
    return ''.join(result)


def print_usage_summary(usage_counts, incorrect_verbs=None):
    """Print a summary of how many times each verb was used."""
    incorrect_verbs = incorrect_verbs or set()
    if not usage_counts:
        print("No verb usage recorded.")
        return
    
    print("\nVerb usage summary (alphabetical):")
    longest = max(len(name) + (1 if name in incorrect_verbs else 0) for name in usage_counts)
    for verb_name in sorted(usage_counts):
        count = usage_counts[verb_name]
        flagged = verb_name in incorrect_verbs
        display_name = f"{verb_name}*" if flagged else verb_name
        padded = display_name.ljust(longest)
        if flagged:
            print(f"  {RED}{padded}{RESET}  {count}")
        else:
            print(f"  {padded}  {count}")


def ask_question(verb, tense, person_index, person_label, show_dutch=False):
    """
    Ask a conjugation question and return True if correct, False otherwise.
    """
    verb_name = verb['verbo']
    dutch_translation = verb['dutch']
    correct_answer = verb[tense][person_index]
    
    # Get tense label in lowercase
    tense_label = TENSE_LABELS.get(tense, tense).lower()
    
    # Display verb name or Dutch translation based on show_dutch flag
    display_name = dutch_translation if show_dutch else verb_name
    
    print(f"\n" + "="*60)
    print(f"Conjugate '{display_name}' in '{tense_label}':")
    
    while True:
        try:
            user_answer = get_input(f"{person_label}: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise

        if show_dutch and user_answer == '?':
            print(f"Hint: the Spanish verb is '{verb_name}'")
            continue

        break
    
    # Compare answers
    is_correct = normalize_string(correct_answer) == normalize_string(user_answer)
    
    # Display feedback
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
  %(prog)s --verb=hablar             # Practice only 'hablar' with all tenses
  %(prog)s --verb=ser                # Practice only 'ser' with all tenses
  %(prog)s --dutch                   # Show Dutch translation instead of Spanish verb
  %(prog)s --dutch --tense=present   # Show Dutch translation with present tense only
        """
    )
    
    parser.add_argument(
        '--tense',
        choices=['random', 'present', 'perfecto', 'indefinido'],
        default='random',
        help='Select tense mode: random (default), present, perfecto, or indefinido'
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
    # If a specific verb is provided, use only that verb and random tense
    if specific_verb is not None:
        verb_list = [specific_verb]
        # Force random tense mode when using a specific verb
        tense_mode = 'random'
    else:
        verb_list = verbs
    
    # Determine tense selection function based on tense_mode
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
    
    total_questions = 0
    correct_answers = 0
    usage_counts = {}
    incorrect_verbs = set()
    
    try:
        while True:
            # Select verb, person, and tense
            verb = get_random_verb(verb_list)
            verb_name = verb['verbo']
            person_index, person_label = get_random_person()
            tense = get_tense()
            
            # Ask question
            try:
                is_correct = ask_question(verb, tense, person_index, person_label, show_dutch)
                usage_counts[verb_name] = usage_counts.get(verb_name, 0) + 1
                total_questions += 1
                if is_correct:
                    correct_answers += 1
                else:
                    incorrect_verbs.add(verb_name)
                
                # Display current score
                percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
                print(f"\n{GREEN}Score: {correct_answers}/{total_questions} ({percentage:.1f}%){RESET}\n")
            except (EOFError, KeyboardInterrupt):
                raise
            
    except KeyboardInterrupt:
        # Handle Ctrl-C gracefully
        print("\n")
        print("Quiz interrupted by user")
        print("="*60)
        if total_questions > 0:
            percentage = (correct_answers / total_questions * 100)
            print(f"Final Score: {correct_answers}/{total_questions} ({percentage:.1f}%)")
        else:
            print("No questions answered.")
        print("="*60)
        print_usage_summary(usage_counts, incorrect_verbs)
        sys.exit(0)
    except EOFError:
        # Handle EOF (Ctrl-D)
        print("\n\n" + "="*60)
        print("Quiz ended")
        print("="*60)
        if total_questions > 0:
            percentage = (correct_answers / total_questions * 100)
            print(f"Final Score: {correct_answers}/{total_questions} ({percentage:.1f}%)")
        else:
            print("No questions answered.")
        print("="*60)
        print_usage_summary(usage_counts, incorrect_verbs)
        sys.exit(0)


def main():
    """Main entry point."""
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Ensure stdout and stdin use UTF-8 encoding
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stdin, 'reconfigure') and sys.stdin.encoding != 'utf-8':
            sys.stdin.reconfigure(encoding='utf-8')
        
        print("Loading verbs from /Users/hans/Dropbox/Spaans/Verbos.json...")
        verbs = load_verbs()
        print(f"Loaded {len(verbs)} verbs.")
        
        # Handle specific verb option
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
            # Display tense mode
            tense_display = {
                'random': 'Random tense',
                'present': 'Present tense',
                'perfecto': 'Pretérito Perfecto',
                'indefinido': 'Pretérito Indefinido'
            }
            print(f"Tense mode: {tense_display[args.tense]}")
        
        print("\nNote: To enter accented characters, use Option key combinations:")
        print("  Option+e then vowel = á, é, í, ó, ú")
        print("  Option+a = á, Option+i = í, Option+o = ó, Option+u then u = ü, Option+n = ñ\n")
        if args.dutch:
            print("Tip: Enter '?' to reveal the Spanish verb before answering.\n")
        
        run_quiz(verbs, args.tense, specific_verb, args.dutch)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

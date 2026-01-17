#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple CLI quiz for Spanish↔Dutch vocabulary stored in Palabras.json."""

from __future__ import annotations

import argparse
import json
import random
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DATA_FILE = Path(__file__).with_name("Palabras.json")


class Colors:
    """ANSI color helper that only activates when stdout is a TTY."""

    def __init__(self) -> None:
        enabled = sys.stdout.isatty()
        self.green = "\033[92m" if enabled else ""
        self.red = "\033[91m" if enabled else ""
        self.cyan = "\033[96m" if enabled else ""
        self.bold = "\033[1m" if enabled else ""
        self.reset = "\033[0m" if enabled else ""


colors = Colors()


def load_words(path: Path = DATA_FILE) -> List[Dict[str, str]]:
    """Load word pairs from JSON, returning an empty list on failure."""
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, list):
            raise ValueError("JSON is not a list")
        words: List[Dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            dutch = item.get("dutch")
            spanish = item.get("spanish")
            if isinstance(dutch, str) and isinstance(spanish, str):
                words.append({"dutch": dutch.strip(), "spanish": spanish.strip()})
        return words
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Kon {path.name} niet lezen: {exc}")
        return []


def save_words(words: List[Dict[str, str]], path: Path = DATA_FILE) -> None:
    """Persist word pairs to JSON with readable formatting."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(words, handle, ensure_ascii=False, indent=4)


def strip_accents(text: str) -> str:
    """Remove diacritics to allow accent-insensitive comparisons."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize(text: str) -> str:
    return strip_accents(text.strip()).casefold()


def answers_match(user_answer: str, expected: str) -> bool:
    """Compare answers ignoring case/accents; accept multiple variants."""
    user_norm = normalize(user_answer)
    if not user_norm:
        return False
    if normalize(expected) == user_norm:
        return True
    variants = [part.strip() for part in expected.replace(";", "/").split("/") if part.strip()]
    return any(normalize(variant) == user_norm for variant in variants)


def ask_direction() -> Tuple[str, str, str]:
    """Prompt for quiz direction; default is Dutch→Spanish."""
    prompt = (
        "Kies richting: [D] Nederlands → Spaans (standaard) of "
        "[S] Spaans → Nederlands? (d/s): "
    )
    choice = input(prompt).strip().lower()
    if choice == "s":
        return ("spanish", "dutch", "Spaans → Nederlands")
    return ("dutch", "spanish", "Nederlands → Spaans")


def pick_pair(words: List[Dict[str, str]]) -> Dict[str, str]:
    return random.choice(words)


def direction_from_cli(mode: str) -> Tuple[str, str, str]:
    if mode == "es-nl":
        return ("spanish", "dutch", "Spaans → Nederlands")
    return ("dutch", "spanish", "Nederlands → Spaans")


def quiz(words: List[Dict[str, str]], source_key: str, target_key: str) -> Tuple[int, int]:
    """Run the quiz loop; returns (correct, total)."""
    if not words:
        print("Geen woorden gevonden in Palabras.json. Voeg eerst woorden toe.")
        return (0, 0)

    remaining = words.copy()
    random.shuffle(remaining)

    correct = 0
    total = 0
    print("\nTyp 'q' om te stoppen met de quiz.")
    print()

    try:
        while True:
            if not remaining:
                remaining = words.copy()
                random.shuffle(remaining)

            pair = remaining.pop()
            question = pair[source_key]
            expected = pair[target_key]
            answer_raw = input(
                f"Vertaal '{question}' naar {target_key} (q om te stoppen): "
            ).strip()
            if answer_raw.casefold() in {"q", "quit", "exit"}:
                break
            total += 1

            if answers_match(answer_raw, expected):
                correct += 1
                print(f"{colors.green}✔ Goed!{colors.reset}\n")
            else:
                print(
                    f"{colors.red}✘ Jammer. Juiste antwoord: {expected}{colors.reset}\n"
                )
    except KeyboardInterrupt:
        print("\nOnderbroken met Ctrl-C.\n")

    print(f"Eindsaldo: {colors.bold}{correct}{colors.reset} van {total} goed.\n")
    return (correct, total)


def add_word_pair(words: List[Dict[str, str]], path: Path = DATA_FILE) -> bool:
    """Add new Dutch/Spanish pairs in a loop; returns True if any were added."""
    print("\nNieuw woordpaar toevoegen. Typ 'q' om te stoppen.")
    print("Gebruik accenten zoals je ze in de terminal kunt typen.")

    added_any = False
    try:
        while True:
            dutch_raw = input("Nederlands: ").strip()
            if dutch_raw.casefold() in {"q", "quit"}:
                break

            spanish_raw = input("Spaans: ").strip()
            if spanish_raw.casefold() in {"q", "quit"}:
                break

            dutch = dutch_raw
            spanish = spanish_raw

            if not dutch or not spanish:
                print("Lege invoer overgeslagen.\n")
                continue

            dutch_norm = normalize(dutch)
            spanish_norm = normalize(spanish)

            exists = any(
                normalize(item["dutch"]) == dutch_norm and normalize(item["spanish"]) == spanish_norm
                for item in words
            )
            if exists:
                print("Dit woordpaar bestaat al.\n")
                continue

            words.append({"dutch": dutch, "spanish": spanish})
            save_words(words, path=path)
            added_any = True
            print("Toegevoegd en opgeslagen.\n")
    except KeyboardInterrupt:
        print("\nOnderbroken met Ctrl-C.\n")

    return added_any


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Spaans ↔ Nederlands woordquiz",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["nl-es", "es-nl"],
        help="Kies richting: nl-es (Nederlands → Spaans) of es-nl (Spaans → Nederlands).",
    )
    parser.add_argument(
        "-a",
        "--add",
        action="store_true",
        help="Voeg een nieuw woordpaar toe en sluit daarna af.",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=DATA_FILE,
        help="Pad naar Palabras.json",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    data_file = args.file
    words = load_words(data_file)
    total_correct = 0
    total_questions = 0

    print("Spaans ↔ Nederlands woordquiz.")
    print(
        "Let op: in de meeste terminals typ je accenten door eerst het accent te "
        "typen en daarna de letter (bijv. ' + a = á). Een umlaut typ je met het \" "
        "teken. Je kunt ook geaccentueerde tekens plakken.\n"
    )

    # Non-interactive actions
    if args.add:
        add_word_pair(words, path=data_file)
        return

    if args.mode:
        source_key, target_key, label = direction_from_cli(args.mode)
        print(f"Richting gekozen: {label}")
        correct, total = quiz(words, source_key, target_key)
        total_correct += correct
        total_questions += total
    else:
        try:
            while True:
                action = input(
                    "Kies: [1] Quiz starten, [2] Nieuw woordpaar toevoegen, [3] Stoppen (standaard 1): "
                ).strip().lower()

                if action in {"", "1"}:
                    source_key, target_key, label = ask_direction()
                    print(f"Richting gekozen: {label}")
                    correct, total = quiz(words, source_key, target_key)
                    total_correct += correct
                    total_questions += total
                elif action in {"2", "a"}:
                    add_word_pair(words, path=data_file)
                elif action in {"3", "q", "quit", "exit"}:
                    break
                else:
                    print("Onbekende keuze, probeer opnieuw.\n")
        except KeyboardInterrupt:
            print("\nOnderbroken met Ctrl-C.\n")

    if total_questions:
        print(
            f"Totaalscore deze sessie: {colors.bold}{total_correct}{colors.reset} "
            f"van {total_questions} goed."
        )
    print("Tot de volgende keer!")


if __name__ == "__main__":
    main()
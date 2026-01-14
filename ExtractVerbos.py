#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate an Excel workbook with one sheet per verb from a reference JSON.

Usage (defaults shown):
    python3 ExtractVerbos.py \
        --verbs-file /Users/hans/Desktop/verbos-errores.txt \
        --json-file Verbos.json \
        --output-file VerbosErrores.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet


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


def read_verb_list(path: Path) -> List[str]:
    """Load verbs from a text file, trimming, skipping blanks, and deduping."""
    if not path.exists():
        raise FileNotFoundError(f"Verb list not found: {path}")

    verbs: List[str] = []
    seen = set()
    for line in path.read_text().splitlines():
        verb = line.strip()
        if not verb:
            continue
        key = verb.lower()
        if key in seen:
            continue
        seen.add(key)
        verbs.append(verb)
    return verbs


def load_verb_lookup(path: Path) -> Dict[str, dict]:
    """Load JSON verbs and map them by normalized infinitive."""
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    data = json.loads(path.read_text())
    lookup: Dict[str, dict] = {}
    for entry in data:
        norm = normalize_verb(entry.get("verbo", ""))
        if not norm:
            continue
        # Keep the first occurrence; later duplicates are ignored.
        lookup.setdefault(norm, entry)
    return lookup


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

    # Headers
    headers = [
        ("A1", verb_name),
        ("B1", "Present"),
        ("C1", "Pretérito Perfecto"),
        ("D1", "Pretérito Indefinido"),
        ("E1", "Presente Progresivo"),
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
        ("presente-progresivo", 5),  # column E
    ]

    for row_idx in range(6):  # rows 2-7 contain pronoun lines
        excel_row = row_idx + 2
        for key, col in tenses:
            forms = verb_entry.get(key, [])
            value = forms[row_idx] if row_idx < len(forms) else ""
            ws.cell(row=excel_row, column=col, value=value)

    # Slightly widen columns for readability.
    widths = {"A": 18, "B": 18, "C": 22, "D": 22, "E": 22}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def build_workbook(
    verbs: List[str],
    lookup: Dict[str, dict],
) -> Workbook:
    wb = Workbook()
    # Remove the default empty sheet; we'll create per-verb sheets.
    default_ws = wb.active
    wb.remove(default_ws)

    for verb in verbs:
        entry = lookup[normalize_verb(verb)]
        new_ws = wb.create_sheet(
            title=sanitize_sheet_title(entry.get("verbo", verb))
        )
        populate_sheet(new_ws, entry)

    return wb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract verbs into Excel sheets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--verbs-file",
        default="/Users/hans/Desktop/verbos-errores.txt",
        help="Path to text file with verbs (one per line).",
    )
    parser.add_argument(
        "--json-file",
        default="Verbos.json",
        help="Path to Verbos.json data file.",
    )
    parser.add_argument(
        "--output-file",
        default="VerbosErrores.xlsx",
        help="Output Excel file path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    verbs_file = Path(args.verbs_file).expanduser()
    json_file = Path(args.json_file).expanduser()
    output_file = Path(args.output_file).expanduser()

    verbs = read_verb_list(verbs_file)
    if not verbs:
        raise SystemExit(f"No verbs found in {verbs_file}")

    lookup = load_verb_lookup(json_file)
    missing = [v for v in verbs if normalize_verb(v) not in lookup]
    if missing:
        missing_str = ", ".join(missing)
        raise SystemExit(f"Verbs not found in JSON: {missing_str}")

    wb = build_workbook(verbs, lookup)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_file)
    print(f"Created {output_file} with {len(verbs)} sheets.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - simple CLI error surfacing
        print(exc, file=sys.stderr)
        sys.exit(1)

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal Spanish-learning toolkit: two interactive CLI quizzes plus a set of
one-off scraper/enrichment scripts that build and maintain the verb/vocabulary
data files, plus a Claude Code skill for a conversational drill. There is no
package structure, build step, or test suite — each `.py` file at the repo
root is a standalone script run directly with `python3`.

## Running the quizzes

```bash
python3 VerbosQuiz.py                      # verb conjugation quiz, random tense (default)
python3 VerbosQuiz.py --tense=imperfecto   # drill one tense only (see --help for all choices)
python3 VerbosQuiz.py --verb=hablar        # drill a single verb across all tenses
python3 VerbosQuiz.py --dutch              # show Dutch translation instead of the Spanish verb;
                                            # '?' during a question reveals the Spanish verb (hint)
python3 PalabrasQuiz.py                    # Dutch<->Spanish vocabulary quiz (interactive menu, Dutch UI text)
python3 PalabrasQuiz.py -m es-nl           # force direction instead of the interactive prompt
python3 PalabrasQuiz.py -a                 # add a new Dutch/Spanish word pair, then exit
```

Dependencies: `pip install -r requirements.txt` (requests, beautifulsoup4, deepl —
only needed for the data-enrichment scripts; the quizzes themselves have no
third-party dependencies beyond `openpyxl`, used by `VerbosQuiz.py` to export errors).

## Claude Code skill

`.claude/skills/spaanse-werkwoorden/SKILL.md` — a conversational (non-script)
drill: Claude shows a Dutch sentence and the user translates it to Spanish,
inferring the correct tense/conjugation from context (no tense is ever named
outright). Invoked as `/spaanse-werkwoorden` (optionally with a tense name
and/or a count, e.g. `/spaanse-werkwoorden imperfecto 10`; defaults to a
random mix of 30). It samples verbs live from `Verbos.json` at session start
(via an inline `python3` snippet, not a separate data file), so verbs added to
`Verbos.json` later are automatically available. Target level: A2. To extend
the pool, just add the verb to `Verbos.json` (via `AnadeVerbo.py`, see below)
— the skill itself has no verb list to maintain.

## Data model

- `Verbos.json` — array of verb entries, each with `verbo` (infinitive, sometimes
  annotated with a usage hint in quotes, e.g. `agradecer "algo / a alguien"`),
  six-form conjugation arrays for `presente`, `preterito-perfecto`,
  `preterito-indefinido`, `preterito-imperfecto`, `futuro-simple`,
  `presente-progresivo` (in person order yo/tú/él-ella-usted/nosotros/vosotros/ellos),
  an `imperativo-afirmativo` dict with only `tu` and `vosotros` keys (imperative
  has no first-person form), and a `dutch` translation. Reflexive verbs (infinitive
  ends in `-se`) embed the reflexive pronoun in each conjugated form.
- `Palabras.json` — flat array of `{"dutch": ..., "spanish": ...}` pairs used by
  `PalabrasQuiz.py`. Multiple accepted translations are written as `/`- or
  `;`-separated variants inside one string value.
- `VerbosErrores.json` — persistent per-verb error/hint counters written by
  `VerbosQuiz.py --dutch` sessions (used to weight which verbs resurface). Verbs
  return to zero and are pruned from this file once answered correctly again.
  `VerbosErrores.xlsx` is a generated report (one sheet per missed verb) rebuilt
  on quiz exit — don't hand-edit either file.
- Not every verb entry has every key — older entries predate later enrichment
  passes (e.g. `futuro-simple` or `imperativo-afirmativo` may be absent). Scripts
  that consume `Verbos.json` must tolerate missing keys instead of assuming the
  full schema.

## Data-enrichment scripts

These all scrape conjugation tables from `esfacil.eu` (`BASE_URL` in each file)
and share near-identical helper logic (gerund/futuro/imperativo fetch with a
verify=True→False SSL retry, reflexive-infinitive handling, an
`OUTPUT_FIELD_ORDER` list used to re-key each JSON entry consistently). Each
targets one missing field and is run once over the whole file, not imported as
a library:

- `AnadeVerbo.py <verb>` — the main "add a new verb" flow: looks up the verb on
  esfacil.eu for every tense, gets a Dutch translation via the DeepL API,
  prints the new entry, asks for y/n confirmation, then inserts it at the start
  of `Verbos.json` and rewrites the file in place.
- `Add-futuro-simple.py`, `Add-preterito-imperfecto.py`,
  `Add-imperativo-afirmativo.py` — batch-backfill one additional tense/field
  onto every entry in an input JSON file, writing a *new* output file
  (`--input`/`--output` flags; never overwrite `Verbos.json` directly). Used
  historically to migrate the dataset forward as new fields were added.
- `convert.py`, `extract_conjugations.py` — earlier/ad-hoc versions of the same
  scraping approach (different default filenames, less consistent field
  handling); kept for reference rather than active use.
- `Verbos-ejemplo-inp.json` / `Verbos-ejemplo-out.json` — a small before/after
  sample showing what one of these backfill passes does to a couple of entries.

When adding a new enrichment script for another field, follow the existing
pattern: fetch with the verify=True-then-False retry, derive a fallback when
scraping fails (see `derive_regular_gerundio`), take `--input`/`--output`
rather than mutating `Verbos.json` directly, and preserve `OUTPUT_FIELD_ORDER`
semantics so diffs on `Verbos.json` stay minimal.

## Conventions

- Dutch-facing user strings (prompts/messages in `PalabrasQuiz.py`) stay in
  Dutch; English is used for `VerbosQuiz.py`'s own UI text and for all code
  identifiers/docstrings across the repo.
- Answer matching is always accent- and case-insensitive via NFD-strip-combining
  normalization (see `strip_accents`/`normalize_string` in `VerbosQuiz.py`,
  `normalize` in `PalabrasQuiz.py`) — reuse these helpers rather than adding new
  comparison logic.
- Commit messages are typically just the verb (or short phrase) that was
  added/changed in `Verbos.json` for that commit (e.g. `tumbarse`, `brindar`),
  not conventional-commit style.

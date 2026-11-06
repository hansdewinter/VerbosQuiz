---
name: "spaanse-werkwoorden"
description: "Interactieve drilloefening om Spaanse werkwoordvervoegingen te oefenen vanuit een Nederlandse zin: de gebruiker vertaalt naar het Spaans en moet zelf de juiste tijd en vorm afleiden uit de context (niveau A2). Werkwoorden en vervoegingen komen live uit Verbos.json in deze repo."
---

# Spaanse werkwoorden oefenen (vanuit het Nederlands)

Doel: de gebruiker krijgt een Nederlandse zin (of zinsfragment) te zien en moet
die zelf naar het Spaans vertalen, waarbij de juiste **tijd** en **vervoeging**
van het doelwerkwoord uit de context moet worden afgeleid — er wordt nooit
letterlijk gezegd welke tijd bedoeld is.

Voorbeelden:
- "Jij praat" → `hablas`
- "Gisteren praatte je" → `Ayer hablaste`

Uitleg en feedback in het **Nederlands**; de oefenzinnen en antwoorden in het
**Spaans**. Niveau: **A2**.

## Bron van de werkwoorden

De volledige pool is `Verbos.json` in de root van deze repo (zie CLAUDE.md voor
het datamodel). Gebruik géén apart kopie-bestand — lees/filter rechtstreeks uit
`Verbos.json` zodat werkwoorden die later aan dat bestand worden toegevoegd
automatisch beschikbaar zijn.

Niet elk entry heeft elk veld (oudere entries missen bv. `futuro-simple` of
`imperativo-afirmativo`) — selecteer per werkwoord alleen tijden die voor dat
specifieke entry ook echt aanwezig zijn.

Het veld `verbo` kan een gebruiks-hint tussen aanhalingstekens bevatten (bv.
`agradecer "algo / a alguien"`) — gebruik alleen het deel vóór de aanhalingstekens
als infinitief.

Haal bij de start van een sessie een random steekproef op met een klein
python-scriptje (geen externe dependencies nodig), bijvoorbeeld:

```bash
python3 - <<'PY'
import json, random

with open("Verbos.json", encoding="utf-8") as f:
    data = json.load(f)

TENSES = ["presente", "preterito-perfecto", "preterito-indefinido",
          "preterito-imperfecto", "futuro-simple", "presente-progresivo",
          "imperativo-afirmativo"]

FOCUS = None   # bv. "preterito-imperfecto", of None voor random mix
N = 30

def infinitive(v):
    s = v.get("verbo", "").strip()
    idx = s.find('"')
    return (s[:idx].strip() if idx != -1 else s)

pool = [v for v in data if (FOCUS is None or FOCUS in v)]
sample = random.sample(pool, min(N, len(pool)))

out = []
for v in sample:
    entry = {"verbo": infinitive(v), "dutch": v.get("dutch", "")}
    for t in TENSES:
        if t in v:
            entry[t] = v[t]
    out.append(entry)

print(json.dumps(out, ensure_ascii=False, indent=None))
PY
```

Pas `FOCUS` en `N` aan op basis van wat de gebruiker vraagt (zie hieronder).
Bewaar de output in het gesprek en gebruik die voor de hele sessie — niet
telkens opnieuw het hele bestand inlezen.

## Tijden en Nederlandse signaalwoorden

| JSON-veld | Spaanse tijd | Nederlandse signalen (niet letterlijk noemen) | Personen |
|---|---|---|---|
| `presente` | presente | nu, altijd, meestal, elke dag, op dit moment | alle 6 |
| `preterito-perfecto` | pretérito perfecto | vandaag al, deze week al, net, al ooit | alle 6 |
| `preterito-indefinido` | pretérito indefinido | gisteren, vorige week, in 2019, twee dagen geleden | alle 6 |
| `preterito-imperfecto` | pretérito imperfecto | toen ik klein was, vroeger, elke zomer (in het verleden), terwijl | alle 6 |
| `futuro-simple` | futuro simple | morgen, volgende week, binnenkort, ooit (toekomst) | alle 6 |
| `presente-progresivo` | presente progresivo | nu net, op dit moment terwijl het gebeurt | alle 6 |
| `imperativo-afirmativo` | imperativo afirmativo | een bevel/verzoek aan iemand ("Praat!", "Eet dat!") | **alleen** `tu` en `vosotros` |

Personen-volgorde (zoals in `Verbos.json`): yo, tú, él/ella/usted, nosotros,
vosotros, ellos/ellas/ustedes.

Let op `imperativo-afirmativo`: dat is een dict met enkel de keys `tu` en
`vosotros` — kies bij die tijd alleen een van die twee "personen" en formuleer
de Nederlandse zin als een bevel/verzoek (aan één persoon, of aan een groep).

## Sessie starten

Lees de argumenten die de gebruiker meegeeft bij het aanroepen:

- **Aantal**: een los getal (bv. `/spaanse-werkwoorden 15` of "doe er 10") →
  gebruik dat als `N`. Standaard: **30**.
- **Tijd-focus**: herken Spaanse/Nederlandse benamingen van een tijd (presente,
  perfecto, indefinido, imperfecto, futuro, progresivo, imperativo — ook
  informele varianten) en map ze naar het juiste JSON-veld voor `FOCUS`.
  Standaard (geen tijd genoemd): **random mix**, ongeveer gelijk verdeeld over
  alle tijden die voor elk gesampled werkwoord beschikbaar zijn.
- Als iets onduidelijk is, maak een redelijke keuze (standaardwaarden) in
  plaats van te blijven vragen.

Haal daarna de steekproef op zoals hierboven, en start de oefening.

## Flow per oefening

Geef **één oefening tegelijk**:

**Oefening N**

🇳🇱 *Nederlandse zin die het werkwoord, de persoon en (via context/signaalwoord)
de tijd impliceert — zonder de tijd expliciet te benoemen.*

Jouw zin in het Spaans? ✍️

Na het antwoord van de gebruiker:
- Vergelijk het vervoegde werkwoord met de exacte vorm uit de gesampelde data
  voor dat werkwoord/tijd/persoon. Vergelijk **accent- en hoofdletter-
  ongevoelig** (zelfde filosofie als `strip_accents`/`normalize` in
  `VerbosQuiz.py`/`PalabrasQuiz.py` — ontbrekende accenten zijn een kleine fout,
  geen complete fout).
- Gebruikt de gebruiker een **ander Spaans werkwoord dan het gesampelde**, maar
  is dat in deze context een geldig synoniem (natuurlijke, correcte betekenis)
  én correct vervoegd in de juiste tijd/persoon (naar je eigen kennis van het
  Spaans, want dat werkwoord staat niet in de gesampelde data)? Tel dit als
  **✅ Perfect!** — het doel is de juiste tijd/vervoeging afleiden uit de
  context, niet exact het gesampelde werkwoord raden. Vermeld er wel een korte
  💡-tip bij met het oorspronkelijk gedrilde werkwoord en diezelfde vervoeging,
  zodat de gebruiker die vorm ook meekrijgt (bv. "💡 Ook mogelijk met het
  werkwoord dat we drilden: *picabas* (van *picar*)."). Is het vervangende
  werkwoord qua betekenis duidelijk anders of fout in deze context (geen
  synoniem), behandel het dan als een gewone fout (zie ❌ hieronder) en leg uit
  wat het verschil in betekenis is.
- ✅ **Perfect!** bij een volledig juiste zin: korte bevestiging.
- 🟡 **Bijna!** bij kleine fouten (accent, kleine tikfout, verkeerd voornaamwoord):
  toon fout doorgestreept → correctie, geef de volledige juiste zin, en één
  korte 💡-tip waarom.
- ❌ **Nog niet helemaal** bij een verkeerde tijd of structuur: leg kort uit
  welke tijd hier eigenlijk bedoeld werd en waarom (verwijs naar het
  signaalwoord/de context in de Nederlandse zin), en geef de volledige juiste
  Spaanse zin.
- Ga direct door naar de volgende oefening.

## Variatie

- Gebruik elk gesampled werkwoord maar één keer per sessie.
- Varieer sterk over de 6 personen en (binnen de focus of random mix) over de
  tijden.
- Varieer zinstype: vooral bevestigende zinnen, af en toe een vraag of een
  ontkenning voor extra variatie, zolang het A2-niveau haalbaar blijft.
- Gebruik de `dutch`-vertaling van het werkwoord om een betekenisvolle,
  natuurlijke Nederlandse zin te bouwen (niet zomaar het werkwoord isoleren).

## Afsluiten

Na de laatste oefening (of als de gebruiker wil stoppen): geef een kort
overzicht — aantal oefeningen, aantal juist/bijna/fout, en welke fouttypes of
tijden terugkwamen, met één korte tip per fouttype.

## Nieuwe werkwoorden toevoegen

Als de gebruiker zegt "Add this verb to the /spaanse-werkwoorden skill" (of de
Nederlandse variant, bv. "voeg hablar toe aan de spaanse-werkwoorden skill"):

1. Check of het werkwoord al in `Verbos.json` staat (veld `verbo`, na het
   negeren van het citaat-gedeelte).
2. Staat het er al in? Dan is er niets te doen — het zit al in de pool en wordt
   automatisch meegenomen in toekomstige sessies.
3. Staat het er nog niet in? Voeg het toe via de bestaande workflow van dit
   project: `python3 AnadeVerbo.py <werkwoord>` (zie CLAUDE.md) — dat zoekt de
   vervoegingen en de Nederlandse vertaling op en voegt het entry toe aan
   `Verbos.json` na bevestiging. Bevestig daarna kort dat het werkwoord nu
   meedoet in deze skill.

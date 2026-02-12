# Plan: Gradio Sustainability App i18n Translation (ES/CA)

## Overview

The sustainability challenge has **5 Gradio apps** (not 4) deployed to Cloud Run as 15 separate services (5 apps x 3 languages). Only the `_en` versions are production-ready. The existing `_es` and `_ca` files are divergent (different structure, line counts, incomplete translations) and will be **replaced** by fresh translations from the `_en` sources.

**Goal:** Create production-ready Spanish and Catalan versions of all 5 Gradio apps, using the `_en` files as the canonical source of truth.

**Deployment model:** Each language variant deploys as a separate Cloud Run service via `deploy_gradio_apps_sustainability.yml`. The Vue parent passes `?lang=en|es|ca` to select the correct Cloud Run service URL. The language is baked into each file — apps don't read a `lang` query param.

---

## App Inventory

| # | App | EN Source File | Lines | Est. Strings | Activity |
|---|-----|---------------|-------|-------------|----------|
| 1 | **Bias Detective** | `bias_detective_en_sustainability.py` | 1,725 | ~400 | Activity 5 |
| 2 | **Fairness Fixer** | `fairness_fixer_en_sustainability.py` | 1,864 | ~350 | Activity 6 |
| 3 | **Model Building** | `model_building_app_en_sustainability.py` | 2,041 | ~500 | Activity 4 (first encounter) |
| 4 | **Model Building Final** | `model_building_app_en_final_sustainability.py` | 3,823 | ~500 | Activity 9 (advanced replay) |
| 5 | **Sustainability Upgrade** | `sustainability_upgrade_en.py` | 884 | ~300 | Activity 10 (certificate/review) |

**Key clarification:** The `_final` variant is a **separate activity** (Activity 9), not a replacement for the base model building app (Activity 4). Students play the base version first to learn, then return in Activity 9 for the advanced `_final` variant. **Both need ES/CA translations.**

---

## Model Building Translation Artifact Inventory (CRITICAL)

The model building apps have a complex multi-layer translation architecture that goes far beyond team names. **All of these artifacts must be preserved** when creating new ES/CA files from the EN source.

### Architecture Overview

The model building apps use a **Gradio tuple pattern** to separate display labels from internal values:
```python
# Gradio shows "El Generalista Equilibrat" to user, returns "The Balanced Generalist" to Python
MODEL_RADIO_CHOICES = [(catalan_label, english_key) for key, label in MODEL_DISPLAY_MAP.items()]
```

This means: **display language = target language, internal values = always English.** Cache keys, API submissions, sklearn column names all use English values.

### Artifact 1: TEAM_NAME_TRANSLATIONS (Local dict)

Two separate team name sets exist across the sustainability apps:

**Set A: Standard Teams** (Bias Detective, Fairness Fixer, Sustainability Upgrade)
- Source: centralized `team_name_i18n.py` in parent `/apps/` directory
- Import: `from .team_name_i18n import translate_team_name_for_display`

**Set B: Climate Teams** (Model Building apps ONLY — both base and final)
- Source: Local `TEAM_NAME_TRANSLATIONS` dict in each file
- 6 teams with en/es/ca mappings

| English (canonical) | Spanish | Catalan |
|---|---|---|
| The Climate Guardians | Los Guardianes del Clima | Els Guardians del Clima |
| United Eco-Architects | Eco-Arquitectos Unidos | Eco-Arquitectes Units |
| The Energy Detectives | Los Detectivos de la Energia | Els Detectius de l'Energia |
| The Sustainability League | La Liga de la Sostenibilidad | La Lliga de la Sostenibilitat |
| Green Future Engineers | Ingenieros del Futuro Verde | Enginyers del Futur Verd |
| Zero Carbon Avengers | Los Vengadores del Carbono Cero | Els Venjadors del Carboni Zero |

**Data flow rule:** Storage/API = always English canonical. Display = translated. Comparisons = English.

### Artifact 2: MODEL_DISPLAY_MAP (Model name translations)

Maps English model keys to localized display labels. Used with Gradio tuples so internal values stay English.

| English Key | Spanish | Catalan |
|---|---|---|
| The Balanced Generalist | El Generalista Equilibrado | El Generalista Equilibrat |
| The Rule-Maker | El Creador de Reglas | El Creador de Regles |
| The 'Nearest Neighbor' | El 'Vecino Mas Cercano' | El 'Vei mes Proper' |
| The Deep Pattern-Finder | El Buscador de Patrones Profundo | El Detector de Patrons Profunds |
| The Majority Vote (final only) | El Voto Mayoritario | El Vot Majoritari |

**Usage:** `MODEL_RADIO_CHOICES = [(label, key) for key, label in MODEL_DISPLAY_MAP.items()]`

### Artifact 3: MODEL_TYPES card descriptions

Each model has a localized description card. Key naming differs between base and final:
- **Base files:** use `"card"` key with localized text
- **Final files:** use `"card_es"` / `"card_ca"` key with localized text
- `get_model_card()` must reference the correct key

### Artifact 4: FEATURE_SET_ALL_OPTIONS (Feature name translations)

Gradio tuples: `(localized_display_label, english_column_name)`. Identical in base and final.

| Catalan Display | Spanish Display | English Column |
|---|---|---|
| Superficie (peus quadrats) | Superficie (pies cuadrados) | floor_area |
| Any de construccio | Ano de construccion | year_built |
| Classe d'edifici | Clase de edificio | building_class |
| Tipus d'instal-lacio | Tipo de instalacion | facility_type |
| Factor d'estat | Factor de estado | State_Factor |
| Factor d'any | Factor de ano | Year_Factor |
| Elevacio | Elevacion | ELEVATION |
| Dies de calefaccio | Dias de calefaccion | heating_degree_days |
| Dies de refrigeracio | Dias de refrigeracion | cooling_degree_days |
| Temp. mitjana anual | Temp. media anual | avg_temp |
| Temp. minima de gener | Temp. minima de enero | january_min_temp |
| Temp. maxima de juliol | Temp. maxima de julio | july_max_temp |
| Temp. mitjana d'abril | Temp. media de abril | april_avg_temp |
| Temp. mitjana d'octubre | Temp. media de octubre | october_avg_temp |

### Artifact 5: DATA_SIZE translations (DIFFERENT between base and final!)

**Base files** use Gradio tuples (display → English value returned to Python):
```python
DATA_SIZE_DISPLAY_MAP = {"Small (20%)": "Petita (20%)", ...}
DATA_SIZE_RADIO_CHOICES = [(catalan_label, english_key) for ...]
# data_size_str arrives in Python as English → goes directly into cache key
```

**Final files** use plain localized strings + reverse-mapping dict:
```python
DATA_SIZE_MAP = {"Petita (20%)": 0.2, ...}  # Catalan keys
DATA_SIZE_DB_MAP = {"Petita (20%)": "Small (20%)", ...}  # Catalan → English
# data_size_str arrives in Python as Catalan → must map through DATA_SIZE_DB_MAP for cache key
db_data_size = DATA_SIZE_DB_MAP.get(data_size_str, "Small (20%)")
```

| English | Spanish | Catalan |
|---|---|---|
| Small (20%) | Pequeno (20%) | Petita (20%) |
| Medium (60%) | Medio (60%) | Mitjana (60%) |
| Large (80%) | Grande (80%) | Gran (80%) |
| Full (100%) | Completo (100%) | Completa (100%) |

### Artifact 6: Rank name translations

Inline in `compute_rank_settings()` and `build_final_conclusion_html()`.

**Base files** (4 progressive ranks):

| English | Spanish | Catalan |
|---|---|---|
| Trainee | Practicante / Ingeniero en Practicas | Practicant / Enginyer en Practiques |
| Junior | Junior / Ingeniero Junior | Junior / Enginyer Junior |
| Senior | Senior / Ingeniero Senior | Senior / Enginyer Senior |
| Lead | Jefe / Ingeniero Jefe | Cap / Enginyer Cap |

**Final files** (single rank, all tools unlocked):

| English | Spanish | Catalan |
|---|---|---|
| Chief Climate Architect | Arquitecto/a Climatico/a Jefe | Arquitecte/a Climatic/a en Cap |

### Artifact 7: Translation helper functions

Must be defined locally in each model building ES/CA file:

```python
UI_TEAM_LANG = "es"  # or "ca"

def translate_team_name_for_display(team_en: str, lang: str = "es") -> str:
    # Forward lookup: English → localized display name

def translate_team_name_to_english(display_name: str, lang: str = "es") -> str:
    # Reverse lookup: localized → English (final files only)

def _format_leaderboard_for_display(df, lang: str = "es"):
    # DataFrame display helper (final files only)
```

**Critical:** Default `lang` parameter must match the file's language.

### Artifact 8: Login/welcome team name display

**Base files have a bug:** show raw English team names in login and welcome messages.
**Final files are correct:** call `translate_team_name_for_display()` before display.

When creating new files from EN source, must add translation calls:
```python
display_team_name = translate_team_name_for_display(team_name, UI_TEAM_LANG)
team_message = f"Te han asignado: <b>{display_team_name}</b>"  # NOT {team_name}
```

### Known Bugs in Current Files

1. `model_building_app_es_final_sustainability.py` — wrong default `lang: str = "ca"` in all 3 helper functions (should be `"es"`)
2. Both ES and CA **base** files show raw English team names in login/welcome messages (missing `translate_team_name_for_display()` calls)
3. ES Final `TEAM_NAME_TRANSLATIONS` is missing the "ca" block (has only "en"+"es"), while ES Base has all three ("en"+"es"+"ca")

---

## Deployment Infrastructure (Existing)

### GitHub Actions Workflow
**File:** `.github/workflows/deploy_gradio_apps_sustainability.yml`
- **Trigger:** Manual `workflow_dispatch`
- **Build:** Single Docker image from `Dockerfile_sustainability`, pushed to Artifact Registry (`sustainability-apps` repo in `us-central1`)
- **Deploy:** 15 Cloud Run services, each with `APP_NAME` env var selecting the app
- **Resources:** 2 CPU, 2-4 Gi RAM (4Gi for model-building), concurrency 20, max 150 instances
- **Image tag:** `gradio-universal:{github.sha}`

### Dockerfile
**File:** `Dockerfile_sustainability` (root of repo)
- Base: `python:3.12-slim`
- Installs from `requirements-apps.txt`
- Downloads WiDS prediction caches (base + full models) → converts to SQLite
- Downloads COMPAS dataset at build time
- Entrypoint: `python launch_entrypoint.py`

### Launch Entrypoint
**File:** `launch_entrypoint.py`
- Reads `APP_NAME` env var → imports correct app factory → launches with Uvicorn
- Already has mappings for all 15 sustainability services
- Queue concurrency: 40 for model-building variants, none for others

### Cloud Run Service Names (15 services)
```
model-building-game-en-sustainability
model-building-game-es-sustainability
model-building-game-ca-sustainability
model-building-game-en-final-sustainability
model-building-game-es-final-sustainability
model-building-game-ca-final-sustainability
bias-detective-en-sustainability
bias-detective-es-sustainability
bias-detective-ca-sustainability
fairness-fixer-en-sustainability
fairness-fixer-es-sustainability
fairness-fixer-ca-sustainability
sustainability-upgrade-en
sustainability-upgrade-es
sustainability-upgrade-ca
```

---

## String Categories to Translate

### A. HTML Content Blocks (largest volume)
- `MODULES` list entries: `title` (str) + `html` (large multi-line HTML string with embedded CSS/JS)
- Contains: headings, paragraphs, button labels, tooltip text, animated stat labels, scenario descriptions
- **Challenge:** HTML strings have embedded JavaScript. JS function names and CSS class names must NOT be translated.

### B. Quiz Configuration
- `QUIZ_CONFIG` dict: `question`, `options` (list of 3-4 strings), `answer` (must match one option), `success` message
- **Critical:** `answer` must exactly match one translated `options` entry.

### C. Gradio Component Labels
- `gr.Button(value="...")`, `gr.Markdown("...")`, `gr.Radio(label="...", choices=[...])`, `gr.Accordion(label="...")`, `gr.HTML("...")`

### D. Dynamic Python Strings
- f-strings: success messages, error messages, leaderboard headers
- `generate_success_message()`, `render_top_dashboard()`, `render_leaderboard_card()`
- Alert/error messages in auth flow

### E. Team Name Integration
- **Bias Detective, Fairness Fixer, Sustainability Upgrade:** Import from `team_name_i18n.py`, call `translate_team_name_for_display(team_en, lang='es'|'ca')`
- **Model Building (both variants):** Define local `TEAM_NAME_TRANSLATIONS` dict + local `translate_team_name_for_display()` function with correct `UI_TEAM_LANG` and default `lang` parameter

---

## Pre-Work: Branch Setup

Before any changes:
```bash
cd /home/michael/Documents/repos/aimodelshare
git checkout -b feat/sustainability-gradio-i18n
```

---

## Phase 0: Delete Old Divergent Files

Delete all existing `_es` and `_ca` files (they'll be recreated fresh from `_en`):

```
bias_detective_es_sustainability.py        (2,819 lines — divergent)
bias_detective_ca_sustainability.py        (2,819 lines — divergent)
fairness_fixer_es_sustainability.py        (1,916 lines — divergent)
fairness_fixer_ca_sustainability.py        (1,916 lines — divergent)
model_building_app_es_sustainability.py    (4,085 lines — divergent)
model_building_app_ca_sustainability.py    (4,084 lines — divergent)
model_building_app_es_final_sustainability.py  (3,701 lines — divergent + bug)
model_building_app_ca_final_sustainability.py  (3,901 lines — divergent)
sustainability_upgrade_es.py               (825 lines — divergent)
sustainability_upgrade_ca.py               (824 lines — divergent)
```

**Before deleting:** Extract and preserve the team name translation tables from the model building `_es`/`_ca` files — these are the authoritative Climate Team translations (Set B above).

---

## Phase 1: Model Building Base (ES + CA) — Activity 4

### 1.1 Create `model_building_app_es_sustainability.py`
- Copy from `model_building_app_en_sustainability.py` (2,041 lines)
- Rename: `create_model_building_game_es_sustainability_app()`, `launch_model_building_game_es_sustainability_app()`
- **Add all translation artifacts** (preserve from old ES file):
  - `TEAM_NAME_TRANSLATIONS` dict (Artifact 1 — Climate Teams Set B)
  - `UI_TEAM_LANG = "es"`
  - `translate_team_name_for_display()` with default `lang: str = "es"` (Artifact 7)
  - `MODEL_DISPLAY_MAP` — 4 model names EN→ES (Artifact 2)
  - `MODEL_RADIO_CHOICES` — Gradio tuples `[(spanish_label, english_key)]`
  - `MODEL_TYPES` card descriptions in Spanish, using `"card"` key (Artifact 3)
  - `FEATURE_SET_ALL_OPTIONS` — 14 features as `(spanish_label, english_column)` tuples (Artifact 4)
  - `DATA_SIZE_DISPLAY_MAP` + `DATA_SIZE_RADIO_CHOICES` — Gradio tuples for data sizes (Artifact 5, base pattern)
  - Rank names in `compute_rank_settings()` — 4 progressive ranks in Spanish (Artifact 6)
  - `tier_names` in `build_final_conclusion_html()` — Spanish rank labels
- **Fix base file bug:** Add `translate_team_name_for_display()` calls in login/welcome messages (Artifact 8)
- Translate all MODULE content (6-step onboarding + model building arena)
- Translate QUIZ_CONFIG entries
- Translate Gradio UI strings, dynamic strings, leaderboard text
- **Keep dataset column names in English** (sklearn code uses English column names from Gradio tuple values)
- **Keep cache keys in English** (data_size_str from Gradio tuples is already English in base pattern)

### 1.2 Create `model_building_app_ca_sustainability.py`
- Same as 1.1 with Catalan equivalents, `UI_TEAM_LANG = "ca"`, default `lang: str = "ca"`

### 1.3 Verification
- Verify QUIZ_CONFIG `answer` matches translated `options`
- Verify team name translation default `lang` matches file language
- Verify `MODEL_DISPLAY_MAP` keys match `MODEL_TYPES` keys exactly
- Verify `FEATURE_SET_ALL_OPTIONS` tuple values match EN column names exactly
- Verify `DATA_SIZE_DISPLAY_MAP` keys match `DATA_SIZE_MAP` keys exactly
- Verify function names have correct language suffix
- Verify ML pipeline still works (feature column names untouched in Gradio tuple values)

---

## Phase 2: Model Building Final (ES + CA) — Activity 9

### 2.1 Create `model_building_app_es_final_sustainability.py`
- Copy from `model_building_app_en_final_sustainability.py` (3,823 lines)
- Rename functions with `_es_final_` suffix
- **Add all translation artifacts** (preserve from old ES Final file):
  - `TEAM_NAME_TRANSLATIONS` dict (Artifact 1 — include all 3 langs: en+es+ca)
  - `UI_TEAM_LANG = "es"`
  - `translate_team_name_for_display()` with default `lang: str = "es"` (**fix the "ca" bug**)
  - `translate_team_name_to_english()` with default `lang: str = "es"` (Artifact 7)
  - `_format_leaderboard_for_display()` with default `lang: str = "es"` (Artifact 7)
  - `MODEL_DISPLAY_MAP` — 5 model names EN→ES (includes Majority Vote) (Artifact 2)
  - `MODEL_RADIO_CHOICES` — Gradio tuples
  - `MODEL_TYPES` card descriptions in Spanish, using `"card_es"` key (Artifact 3)
  - `FEATURE_SET_ALL_OPTIONS` — 14 features as `(spanish_label, english_column)` tuples (Artifact 4)
  - **`DATA_SIZE_DB_MAP`** — Spanish→English reverse mapping for cache keys (Artifact 5, **final pattern**)
  - `DATA_SIZE_MAP` with **Spanish keys** (not English) (Artifact 5)
  - `DEFAULT_DATA_SIZE` in Spanish (e.g., `"Pequeno (20%)"`)
  - Single rank name: "Arquitecto/a Climatico/a Jefe" (Artifact 6)
- Add `translate_team_name_for_display()` calls in login/welcome messages (Artifact 8)
- Translate all MODULE content — this is the most complex file
- Translate achievement messages, certification text
- **Keep cache key construction in English** via `DATA_SIZE_DB_MAP` reverse mapping
- **Keep Gradio tuple values in English** for model names and features

### 2.2 Create `model_building_app_ca_final_sustainability.py`
- Same with Catalan, `UI_TEAM_LANG = "ca"`, all defaults `lang: str = "ca"`
- Catalan equivalents: `DATA_SIZE_DB_MAP`, `DATA_SIZE_MAP`, `DEFAULT_DATA_SIZE`, `"card_ca"` key

### 2.3 Verification
- Same checks as Phase 1, plus:
- Verify `DATA_SIZE_DB_MAP` correctly maps all localized data size strings back to English
- Verify `get_model_card()` references `"card_es"` / `"card_ca"` (not `"card"`)
- Verify cache DB paths unchanged (`prediction_cache.sqlite`, `prediction_cache_full.sqlite`)
- Verify `Majority Vote` model is included in `MODEL_DISPLAY_MAP` and `MODEL_TYPES`

---

## Phase 3: Bias Detective (ES + CA) — Activity 5

### 3.1 Create `bias_detective_es_sustainability.py`
- Copy from `bias_detective_en_sustainability.py` (1,725 lines)
- Rename functions with `_es_` suffix
- Add `from .team_name_i18n import translate_team_name_for_display` import
- Add team name translation calls in `render_leaderboard_card()` with `lang='es'`
- Translate 6 MODULES:
  - Module 0: "What Does AI Cost the Planet?" intro
  - Module 1: "Every Single Prompt" (per-prompt cost calculator with slider JS)
  - Module 2: "Training the Beast" (model selector JS)
  - Module 3: "Water: The Hidden Cost" (animated bars JS)
  - Module 4: "Zoom Out" (stat tabs JS)
  - Module 5: "Your Move" (action plan checkboxes)
- Translate QUIZ_CONFIG (t1-t4)
- Translate Gradio UI strings and dynamic strings

### 3.2 Create `bias_detective_ca_sustainability.py`
- Same with Catalan, `lang='ca'`

### 3.3 Verification
- Same checks, plus verify team_name_i18n import works

---

## Phase 4: Fairness Fixer (ES + CA) — Activity 6

### 4.1 Create `fairness_fixer_es_sustainability.py`
- Copy from `fairness_fixer_en_sustainability.py` (1,864 lines)
- Rename functions
- Add `from .team_name_i18n import translate_team_name_for_display` import
- Translate 7 MODULE entries (title screen + 5 CTO rounds + results)
- Translate `_round_html()` helper strings
- Translate QUIZ_CONFIG (t12-t17)
- Translate Gradio UI strings and dynamic strings

### 4.2 Create `fairness_fixer_ca_sustainability.py`
- Same with Catalan

### 4.3 Verification
- Same checks

---

## Phase 5: Sustainability Upgrade (ES + CA) — Activity 10

### 5.1 Create `sustainability_upgrade_es.py`
- Copy from `sustainability_upgrade_en.py` (884 lines — smallest app)
- Rename functions
- Add `from .team_name_i18n import translate_team_name_for_display` import
- Translate certificate text, leaderboard headers, completion summary, error messages
- Use `translate_team_name_for_display(team_name, lang='es')` for certificate team display

### 5.2 Create `sustainability_upgrade_ca.py`
- Same with Catalan

### 5.3 Verification
- Verify certificate renders correctly in ES/CA
- Verify team names display translated on certificate

---

## Phase 6: Integration & Update Entry Points

### 6.1 Update `__init__.py`
- Ensure all new ES/CA app factory functions are importable

### 6.2 Verify `launch_entrypoint.py` mappings
- Confirm all 15 `APP_NAME` → factory function mappings are correct for the new files
- The entrypoint already has mappings for all 15 services — verify function names match

### 6.3 Verify `deploy_gradio_apps_sustainability.yml`
- All 15 Cloud Run service deploy jobs already exist
- No changes needed unless function names changed

---

## Phase 7: Testing

### 7.1 Local smoke test
For each of the 10 new files (5 apps x 2 languages):
```bash
python -c "
from aimodelshare.moral_compass.apps.sustainability.[module] import create_[app]_[lang]_sustainability_app
app = create_[app]_[lang]_sustainability_app()
print('App created successfully')
"
```

### 7.2 Visual review
- Launch each app locally and verify:
  - All visible text is in the target language
  - No English strings leaking through
  - Quiz answers match their options
  - Leaderboard team names display in correct language
  - Button labels, section headers, feedback messages all translated

### 7.3 Cross-language consistency
- Verify team name English → ES/CA → English round-trips correctly
- Verify score submissions always use English team names
- Verify the same quiz task IDs (t1-t4, t12-t17, etc.) are used across all languages

---

## Translation Guidelines

### Spanish (ES) — Spain Spanish
- Use vosotros/vuestro forms (not Latin American ustedes)
- Use Spain-specific terminology where relevant
- Maintain formal but engaging tone matching the educational context

### Catalan (CA) — Standard Catalan
- Use standard Central Catalan
- Follow IEC (Institut d'Estudis Catalans) orthographic norms
- Use tu/vosaltres forms (informal, matching educational context)

### General Rules
- **Never translate:** variable names, function names, CSS classes, JS function names, API keys, localStorage keys, dataset column names, HTML element IDs, `APP_NAME` values
- **Always translate:** text visible to users (headings, paragraphs, buttons, labels, quiz content, feedback messages, error messages)
- **Preserve HTML structure:** Only change text content within HTML tags, never the tags/attributes
- **Match quiz answers:** After translating QUIZ_CONFIG `options`, ensure `answer` matches the translated correct option exactly
- **Preserve emojis:** Keep all emoji characters as-is (language-neutral)
- **Preserve numbers/units:** Keep numerical values, units (kWh, tonnes CO2, etc.) unchanged
- **Preserve formatting:** Maintain `<strong>`, `<em>`, `<br>` tags and placement
- **Team names:** Always store/submit as English canonical; translate only at display layer

---

## Estimated Effort

| Phase | App | Files Created | Est. Strings per File |
|-------|-----|--------------|----------------------|
| 0 | Cleanup | 0 (10 deleted) | — |
| 1 | Model Building Base | 2 (ES + CA) | ~500 |
| 2 | Model Building Final | 2 (ES + CA) | ~500 |
| 3 | Bias Detective | 2 (ES + CA) | ~400 |
| 4 | Fairness Fixer | 2 (ES + CA) | ~350 |
| 5 | Sustainability Upgrade | 2 (ES + CA) | ~300 |
| **Total** | | **10 new files** | **~2,050 strings x 2 langs** |

---

## Priority Order

1. **Model Building Base** (Activity 4) — first Gradio app students encounter
2. **Model Building Final** (Activity 9) — advanced replay, shares team infrastructure
3. **Bias Detective** (Activity 5) — content-heavy but straightforward
4. **Fairness Fixer** (Activity 6) — CTO simulation with decision rounds
5. **Sustainability Upgrade** (Activity 10) — smallest, certificate/review only

---

## Resolved Questions

1. **`_final` vs base model building?** Both are separate activities (4 and 9). Both need translation.
2. **Old ES/CA files?** Delete them (on a new branch). Preserve Climate Team name translations first.
3. **Team names?** Two separate sets: Standard Teams (centralized `team_name_i18n.py`) and Climate Teams (local to model building apps). Both already have ES/CA translations to preserve.
4. **Deployment config?** `deploy_gradio_apps_sustainability.yml` already deploys all 15 services. No changes needed.
5. **Dockerfile?** `Dockerfile_sustainability` at repo root. Universal image, app selected by `APP_NAME` env var at runtime.

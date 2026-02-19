"""
Preserved Translation Artifacts
================================
Extracted from the ES/CA model building files before migration/deletion.
Each section identifies the source file and the exact artifact preserved.

Source files:
  1. model_building_app_es_sustainability.py          (ES base)
  2. model_building_app_ca_sustainability.py          (CA base)
  3. model_building_app_es_final_sustainability.py    (ES final)
  4. model_building_app_ca_final_sustainability.py    (CA final)

Date preserved: 2026-02-12
"""

# =========================================================================
# FILE 1: model_building_app_es_sustainability.py  (ES base)
# =========================================================================

# --- TEAM_NAME_TRANSLATIONS (lines 569-594) ---
ES_BASE_TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Climate Guardians": "The Climate Guardians",
        "United Eco-Architects": "United Eco-Architects",
        "The Energy Detectives": "The Energy Detectives",
        "The Sustainability League": "The Sustainability League",
        "Green Future Engineers": "Green Future Engineers",
        "Zero Carbon Avengers": "Zero Carbon Avengers"
    },
    "ca": {
        "The Climate Guardians": "Els Guardians del Clima",
        "United Eco-Architects": "Eco-Arquitectes Units",
        "The Energy Detectives": "Els Detectius de l'Energia",
        "The Sustainability League": "La Lliga de la Sostenibilitat",
        "Green Future Engineers": "Enginyers del Futur Verd",
        "Zero Carbon Avengers": "Els Venjadors del Carboni Zero"
    },
    "es": {
        "The Climate Guardians": "Los Guardianes del Clima",
        "United Eco-Architects": "Eco-Arquitectos Unidos",
        "The Energy Detectives": "Los Detectivos de la Energía",
        "The Sustainability League": "La Liga de la Sostenibilidad",
        "Green Future Engineers": "Ingenieros del Futuro Verde",
        "Zero Carbon Avengers": "Los Vengadores del Carbono Cero"
    }
}
# UI_TEAM_LANG = "es"

# --- MODEL_DISPLAY_MAP (lines 555-561) ---
ES_BASE_MODEL_DISPLAY_MAP = {
    "The Balanced Generalist": "El Generalista Equilibrado",
    "The Rule-Maker": "El Creador de Reglas",
    "The 'Nearest Neighbor'": "El 'Vecino más Próximo'",
    "The Deep Pattern-Finder": "El Buscador de Patrones Profundos"
}

# --- MODEL_TYPES card descriptions (lines 521-544) — "card" values only ---
ES_BASE_MODEL_CARDS = {
    "The Balanced Generalist": "Un modelo rápido, fiable y equilibrado. Un buen punto de partida; menos propenso al sobreajuste.",
    "The Rule-Maker": "Aprende reglas simples de tipo 'si/entonces'. Fácil de interpretar, pero puede pasar por alto patrones sutiles.",
    "The 'Nearest Neighbor'": "Analiza los ejemplos pasados más cercanos. 'Te pareces a estos otros; predeciré según su comportamiento'.",
    "The Deep Pattern-Finder": "Un conjunto de muchos árboles de decisión. Potente, puede captar patrones profundos; vigila la complejidad."
}

# --- FEATURE_SET_ALL_OPTIONS (lines 599-614) ---
ES_BASE_FEATURE_SET_ALL_OPTIONS = [
    ("Superficie (pies cuadrados)", "floor_area"),
    ("Año de construcción", "year_built"),
    ("Clase de edificio", "building_class"),
    ("Tipo de instalación", "facility_type"),
    ("Factor de estado", "State_Factor"),
    ("Factor de año", "Year_Factor"),
    ("Elevación", "ELEVATION"),
    ("Días de calefacción", "heating_degree_days"),
    ("Días de refrigeración", "cooling_degree_days"),
    ("Temp. media anual", "avg_temp"),
    ("Temp. mínima de enero", "january_min_temp"),
    ("Temp. máxima de julio", "july_max_temp"),
    ("Temp. media de abril", "april_avg_temp"),
    ("Temp. media de octubre", "october_avg_temp"),
]

# --- DATA_SIZE_DISPLAY_MAP (lines 635-648) ---
ES_BASE_DATA_SIZE_DISPLAY_MAP = {
    "Small (20%)": "Pequeña (20%)",
    "Medium (60%)": "Mediana (60%)",
    "Large (80%)": "Grande (80%)",
    "Full (100%)": "Completa (100%)"
}

# --- tier_names from build_final_conclusion_html (line 2165) ---
ES_BASE_TIER_NAMES = ["Practicante", "Junior", "Senior", "Jefe"]

# --- Rank names from compute_rank_settings (lines 1275, 1290, 1305, 1320) ---
ES_BASE_RANK_NAMES = {
    0: "Ingeniero en Prácticas",       # submission_count == 0
    1: "Ingeniero Junior",             # submission_count == 1
    2: "Ingeniero Senior",             # submission_count == 2
    3: "Ingeniero Jefe",               # submission_count >= 3
}
ES_BASE_RANK_MESSAGES = {
    0: "# 🧑‍🎓 Rango: Ingeniero en Prácticas\n<p style='font-size:24px; line-height:1.4;'>¡Para tu primer envío, simplemente haz clic en el botón '🔬 Construye y Envía Modelo' de abajo!</p>",
    1: "# 🎉 ¡Has Subido de Rango! Ingeniero Junior\n<p style='font-size:24px; line-height:1.4;'>¡Se han desbloqueado nuevos modelos, tamaños de datos e ingredientes!</p>",
    2: "# 🌟 ¡Has Subido de Rango! Ingeniero Senior\n<p style='font-size:24px; line-height:1.4;'>¡Ingredientes de datos más potentes desbloqueados! Los predictores más fuertes (como 'Temp. media anual') ya están disponibles. Recuerda que a menudo están ligados a factores geográficos fuera del control del edificio.</p>",
    3: "# 👑 Rango: Ingeniero Jefe\n<p style='font-size:24px; line-height:1.4;'>¡Todas las herramientas desbloqueadas — optimiza libremente!</p>",
}


# =========================================================================
# FILE 2: model_building_app_ca_sustainability.py  (CA base)
# =========================================================================

# --- TEAM_NAME_TRANSLATIONS (lines 563-580) ---
# NOTE: This file has only "en" and "ca" keys (no "es" key).
CA_BASE_TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Climate Guardians": "The Climate Guardians",
        "United Eco-Architects": "United Eco-Architects",
        "The Energy Detectives": "The Energy Detectives",
        "The Sustainability League": "The Sustainability League",
        "Green Future Engineers": "Green Future Engineers",
        "Zero Carbon Avengers": "Zero Carbon Avengers"
    },
    "ca": {
        "The Climate Guardians": "Els Guardians del Clima",
        "United Eco-Architects": "Eco-Arquitectes Units",
        "The Energy Detectives": "Els Detectius de l'Energia",
        "The Sustainability League": "La Lliga de la Sostenibilitat",
        "Green Future Engineers": "Enginyers del Futur Verd",
        "Zero Carbon Avengers": "Els Venjadors del Carboni Zero"
    }
}
# UI_TEAM_LANG = "ca"

# --- MODEL_DISPLAY_MAP (lines 549-554) ---
CA_BASE_MODEL_DISPLAY_MAP = {
    "The Balanced Generalist": "El Generalista Equilibrat",
    "The Rule-Maker": "El Creador de Regles",
    "The 'Nearest Neighbor'": "El 'Veí més Proper'",
    "The Deep Pattern-Finder": "El Detector de Patrons Profunds"
}

# --- MODEL_TYPES card descriptions (lines 521-544) — "card" values only ---
CA_BASE_MODEL_CARDS = {
    "The Balanced Generalist": "Un model ràpid, fiable i equilibrat. Un bon punt de partida; menys propens al sobreajustament.",
    "The Rule-Maker": "Aprèn regles simples de tipus 'si/aleshores'. Fàcil d'interpretar, però pot passar per alt patrons subtils.",
    "The 'Nearest Neighbor'": "Analitza els exemples passats més propers. 'T'assembles a aquests altres; prediré segons el seu comportament'.",
    "The Deep Pattern-Finder": "Un conjunt de molts arbres de decisió. Potent, pot captar patrons profunds; vigila la complexitat."
}

# --- FEATURE_SET_ALL_OPTIONS (lines 585-600) ---
CA_BASE_FEATURE_SET_ALL_OPTIONS = [
    ("Superfície (peus quadrats)", "floor_area"),
    ("Any de construcció", "year_built"),
    ("Classe d'edifici", "building_class"),
    ("Tipus d'instal·lació", "facility_type"),
    ("Factor d'estat", "State_Factor"),
    ("Factor d'any", "Year_Factor"),
    ("Elevació", "ELEVATION"),
    ("Dies de calefacció", "heating_degree_days"),
    ("Dies de refrigeració", "cooling_degree_days"),
    ("Temp. mitjana anual", "avg_temp"),
    ("Temp. mínima de gener", "january_min_temp"),
    ("Temp. màxima de juliol", "july_max_temp"),
    ("Temp. mitjana d'abril", "april_avg_temp"),
    ("Temp. mitjana d'octubre", "october_avg_temp"),
]

# --- DATA_SIZE_DISPLAY_MAP (lines 627-632) ---
CA_BASE_DATA_SIZE_DISPLAY_MAP = {
    "Small (20%)": "Petita (20%)",
    "Medium (60%)": "Mitjana (60%)",
    "Large (80%)": "Gran (80%)",
    "Full (100%)": "Completa (100%)"
}

# --- tier_names from build_final_conclusion_html (line 2157) ---
CA_BASE_TIER_NAMES = ["Practicant", "Junior", "Senior", "Cap"]

# --- Rank names from compute_rank_settings (lines 1267, 1282, 1297, 1312) ---
CA_BASE_RANK_NAMES = {
    0: "Enginyer en Pràctiques",        # submission_count == 0
    1: "Enginyer Junior",               # submission_count == 1
    2: "Enginyer Senior",               # submission_count == 2
    3: "Enginyer Cap",                  # submission_count >= 3
}
CA_BASE_RANK_MESSAGES = {
    0: "# 🧑‍🎓 Rang: Enginyer en Pràctiques\n<p style='font-size:24px; line-height:1.4;'>Per al teu primer enviament, simplement clica el botó '🔬 Construeix i Envia Model' a sota!</p>",
    1: "# 🎉 Has Pujat de Rang! Enginyer Junior\n<p style='font-size:24px; line-height:1.4;'>S'han desbloquejat nous models, mides de dades i ingredients!</p>",
    2: "# 🌟 Has Pujat de Rang! Enginyer Senior\n<p style='font-size:24px; line-height:1.4;'>Ingredients de dades més potents desbloquejats! Els predictors més forts (com 'Temp. mitjana anual') ja estan disponibles. Recorda que sovint estan lligats a factors geogràfics fora del control de l'edifici.</p>",
    3: "# 👑 Rang: Enginyer Cap\n<p style='font-size:24px; line-height:1.4;'>Totes les eines desbloquejades — optimitza lliurement!</p>",
}


# =========================================================================
# FILE 3: model_building_app_es_final_sustainability.py  (ES final)
# =========================================================================

# --- TEAM_NAME_TRANSLATIONS (lines 783-800) ---
# NOTE: This file has only "en" and "es" keys (no "ca" key).
ES_FINAL_TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Climate Guardians": "The Climate Guardians",
        "United Eco-Architects": "United Eco-Architects",
        "The Energy Detectives": "The Energy Detectives",
        "The Sustainability League": "The Sustainability League",
        "Green Future Engineers": "Green Future Engineers",
        "Zero Carbon Avengers": "Zero Carbon Avengers"
    },
    "es": {
        "The Climate Guardians": "Los Guardianes del Clima",
        "United Eco-Architects": "Eco-Arquitectos Unidos",
        "The Energy Detectives": "Detectives de la Energía",
        "The Sustainability League": "La Liga de la Sostenibilidad",
        "Green Future Engineers": "Ingenieros del Futuro Verde",
        "Zero Carbon Avengers": "Vengadores del Carbono Cero"
    }
}
# UI_TEAM_LANG = "es"

# --- MODEL_DISPLAY_MAP (lines 641-647) — includes Majority Vote ---
ES_FINAL_MODEL_DISPLAY_MAP = {
    "The Balanced Generalist": "El Generalista Equilibrado",
    "The Rule-Maker": "El Creador de Reglas",
    "The 'Nearest Neighbor'": "El 'Vecino Más Cercano'",
    "The Deep Pattern-Finder": "El Buscador de Patrones Profundo",
    "The Majority Vote": "El Voto Mayoritario"
}

# --- MODEL_TYPES card descriptions (lines 606-634) — "card_es" values ---
ES_FINAL_MODEL_CARDS_ES = {
    "The Balanced Generalist": "Modelo rápido, fiable y equilibrado. Ideal para identificar tendencias generales en el uso de energía de los edificios.",
    "The Rule-Maker": "Crea reglas lógicas basadas en umbrales (ej: 'Si el edificio es anterior a 1970 Y tiene más de 10 plantas...'). Muy fácil de explicar.",
    "The 'Nearest Neighbor'": "Compara cada edificio con casos similares en los datos. Si edificios parecidos son ineficientes, predirá lo mismo para este.",
    "The Deep Pattern-Finder": "Analiza multitud de subgrupos para captar ineficiencias energéticas complejas. El más potente para maximizar el impacto climático.",
    "The Majority Vote": "Combina las predicciones de los cuatro modelos y selecciona la más frecuente. ¡Tu mejor opción para liderar el ranking!"
}

# --- FEATURE_SET_ALL_OPTIONS (lines 807-822) ---
ES_FINAL_FEATURE_SET_ALL_OPTIONS = [
    ("Superficie (pies cuadrados)", "floor_area"),
    ("Año de construcción", "year_built"),
    ("Clase de edificio", "building_class"),
    ("Tipo de instalación", "facility_type"),
    ("Factor de estado", "State_Factor"),
    ("Factor de año", "Year_Factor"),
    ("Elevación", "ELEVATION"),
    ("Días de calefacción", "heating_degree_days"),
    ("Días de refrigeración", "cooling_degree_days"),
    ("Temp. media anual", "avg_temp"),
    ("Temp. mínima de enero", "january_min_temp"),
    ("Temp. máxima de julio", "july_max_temp"),
    ("Temp. media de abril", "april_avg_temp"),
    ("Temp. media de octubre", "october_avg_temp"),
]

# --- DATA_SIZE_DB_MAP (lines 654-659) — Spanish UI keys -> English DB keys ---
ES_FINAL_DATA_SIZE_DB_MAP = {
    "Pequeño (20%)": "Small (20%)",
    "Medio (60%)": "Medium (60%)",
    "Grande (80%)": "Large (80%)",
    "Completo (100%)": "Full (100%)"
}

# --- DATA_SIZE_MAP (lines 843-848) — with Spanish keys ---
ES_FINAL_DATA_SIZE_MAP = {
    "Pequeño (20%)": 0.2,
    "Medio (60%)": 0.6,
    "Grande (80%)": 0.8,
    "Completo (100%)": 1.0
}
# DEFAULT_DATA_SIZE = "Pequeño (20%)"

# --- Rank name from compute_rank_settings (line 1529) ---
# NOTE: The ES final file has a single-tier structure (all tools unlocked).
ES_FINAL_RANK_NAME = "Arquitecto/a Climático/a Jefe"
ES_FINAL_RANK_MESSAGE = "# 👑 Rango: Arquitecto/a Climático/a Jefe\n<p style='font-size:24px; line-height:1.4;'>¡Todas las herramientas desbloqueadas — optimiza con libertad!</p>"

# --- build_final_conclusion_html (line 2091+) ---
# NOTE: The ES final file does NOT use tier_names in build_final_conclusion_html.
# Instead it produces a certification-style conclusion. Key translated strings:
ES_FINAL_CONCLUSION_STRINGS = {
    "title": "Certificación obtenida",
    "subtitle": "IA Sostenible: Ingeniería de Vanguardia",
    "results_heading": "Resultados del desafío final",
    "registration_line": "Tu sistema final de IA para identificar edificios energéticamente ineficientes ha sido enviado. Este modelo ayuda a priorizar los esfuerzos de rehabilitación climática.",
    "final_accuracy_label": "Precisión final:",
    "global_ranking_label": "Ranking global:",
    "ranking_pending": "Pendiente",
    "improvement_label": "Mejora en esta sesión:",
    "improvement_suffix": "ganancia de optimización",
    "iterations_label": "Iteraciones totales:",
    "iterations_suffix": "versiones del modelo probadas",
    "journey_heading": "El Viaje Continúa",
}


# =========================================================================
# FILE 4: model_building_app_ca_final_sustainability.py  (CA final)
# =========================================================================

# --- TEAM_NAME_TRANSLATIONS (lines 783-800) ---
# NOTE: This file has only "en" and "ca" keys (no "es" key).
CA_FINAL_TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Climate Guardians": "The Climate Guardians",
        "United Eco-Architects": "United Eco-Architects",
        "The Energy Detectives": "The Energy Detectives",
        "The Sustainability League": "The Sustainability League",
        "Green Future Engineers": "Green Future Engineers",
        "Zero Carbon Avengers": "Zero Carbon Avengers"
    },
    "ca": {
        "The Climate Guardians": "Els Guardians del Clima",
        "United Eco-Architects": "Eco-Arquitectes Units",
        "The Energy Detectives": "Els Detectius de l'Energia",
        "The Sustainability League": "La Lliga de la Sostenibilitat",
        "Green Future Engineers": "Enginyers del Futur Verd",
        "Zero Carbon Avengers": "Els Venjadors del Carboni Zero"
    }
}
# UI_TEAM_LANG = "ca"

# --- MODEL_DISPLAY_MAP (lines 641-647) — includes Majority Vote ---
CA_FINAL_MODEL_DISPLAY_MAP = {
    "The Balanced Generalist": "El Generalista Equilibrat",
    "The Rule-Maker": "El Creador de Regles",
    "The 'Nearest Neighbor'": "El 'Veí més Proper'",
    "The Deep Pattern-Finder": "El Detector de Patrons Profunds",
    "The Majority Vote": "El Vot Majoritari"
}

# --- MODEL_TYPES card descriptions (lines 606-634) — "card_ca" values ---
CA_FINAL_MODEL_CARDS_CA = {
    "The Balanced Generalist": "Aquest model és ràpid, fiable i equilibrat. Un punt de partida ideal per identificar tendències generals en l'ús d'energia.",
    "The Rule-Maker": "Estableix regles lògiques basades en llindars d'energia (ex: 'Si l'edifici té > 50 anys AND la calefacció és de gas...'). Fàcil d'explicar als propietaris.",
    "The 'Nearest Neighbor'": "Compara cada edifici amb edificis similars del conjunt de dades. Si un edifici actua com un altre d'ineficient, el prediu com a tal.",
    "The Deep Pattern-Finder": "Analitza multitud de subgrups de dades per captar ineficiències complexes. El més potent per maximitzar l'estalvi climàtic.",
    "The Majority Vote": "Combina les prediccions dels quatre models anteriors. Sovint més precís que qualsevol model individual per guanyar el repte!"
}

# --- FEATURE_SET_ALL_OPTIONS (lines 808-823) ---
CA_FINAL_FEATURE_SET_ALL_OPTIONS = [
    ("Superfície (peus quadrats)", "floor_area"),
    ("Any de construcció", "year_built"),
    ("Classe d'edifici", "building_class"),
    ("Tipus d'instal·lació", "facility_type"),
    ("Factor d'estat", "State_Factor"),
    ("Factor d'any", "Year_Factor"),
    ("Elevació", "ELEVATION"),
    ("Dies de calefacció", "heating_degree_days"),
    ("Dies de refrigeració", "cooling_degree_days"),
    ("Temp. mitjana anual", "avg_temp"),
    ("Temp. mínima de gener", "january_min_temp"),
    ("Temp. màxima de juliol", "july_max_temp"),
    ("Temp. mitjana d'abril", "april_avg_temp"),
    ("Temp. mitjana d'octubre", "october_avg_temp"),
]

# --- DATA_SIZE_DB_MAP (lines 654-659) — Catalan UI keys -> English DB keys ---
CA_FINAL_DATA_SIZE_DB_MAP = {
    "Petita (20%)": "Small (20%)",
    "Mitjana (60%)": "Medium (60%)",
    "Gran (80%)": "Large (80%)",
    "Completa (100%)": "Full (100%)"
}

# --- DATA_SIZE_MAP (lines 844-849) — with Catalan keys ---
CA_FINAL_DATA_SIZE_MAP = {
    "Petita (20%)": 0.2,
    "Mitjana (60%)": 0.6,
    "Gran (80%)": 0.8,
    "Completa (100%)": 1.0
}
# DEFAULT_DATA_SIZE = "Petita (20%)"

# --- Rank name from compute_rank_settings (line 1519) ---
# NOTE: The CA final file has a single-tier structure (all tools unlocked).
CA_FINAL_RANK_NAME = "Arquitecte/a Climàtic/a en Cap"
CA_FINAL_RANK_MESSAGE = "# 👑 Rang: Arquitecte/a Climàtic/a en Cap\n<p style='font-size:24px; line-height:1.4;'>Totes les eines desbloquejades — optimitza amb llibertat!</p>"

# --- build_final_conclusion_html (line 2081+) ---
# NOTE: The CA final file does NOT use tier_names in build_final_conclusion_html.
# Instead it produces a certification-style conclusion. Key translated strings:
CA_FINAL_CONCLUSION_STRINGS = {
    "title": "Certificació Assolida",
    "subtitle": "IA Sostenible: Enginyeria de Vanguardia",
    "results_heading": "Resultats del Repte Final",
    "registration_line": "El teu sistema final d'IA per identificar edificis energèticament ineficients ha estat enviat. Aquest model ajuda a prioritzar els esforços de rehabilitació climàtica.",
    "final_accuracy_label": "Precisió Final:",
    "global_ranking_label": "Rànquing Global:",
    "ranking_pending": "Pendent",
    "improvement_label": "Millora en aquesta sessió:",
    "improvement_suffix": "de guany d'optimització",
    "iterations_label": "Iteracions Totals:",
    "iterations_suffix": "versions del model provades",
    "journey_heading": "El Viatge Continua",
}


# =========================================================================
# CROSS-FILE COMPARISON NOTES
# =========================================================================
#
# 1. TEAM_NAME_TRANSLATIONS differences:
#    - ES base has all three keys: "en", "ca", "es"
#    - CA base has only "en", "ca" (no "es")
#    - ES final has only "en", "es" (no "ca")
#    - CA final has only "en", "ca" (no "es")
#    - Minor wording differences between ES base and ES final:
#      ES base: "Los Detectivos de la Energía" vs ES final: "Detectives de la Energía"
#      ES base: "Los Vengadores del Carbono Cero" vs ES final: "Vengadores del Carbono Cero"
#
# 2. MODEL_DISPLAY_MAP differences:
#    - Base files have 4 models; final files add "The Majority Vote"
#    - ES base: "El 'Vecino más Próximo'" vs ES final: "El 'Vecino Más Cercano'"
#    - ES base: "El Buscador de Patrones Profundos" vs ES final: "El Buscador de Patrones Profundo"
#
# 3. MODEL_TYPES card descriptions:
#    - Base files use key "card"; final files use "card_es" / "card_ca"
#    - Card text was substantially rewritten for the final versions
#    - Final files include a 5th model: "The Majority Vote"
#
# 4. DATA_SIZE maps:
#    - Base files use English keys in DATA_SIZE_MAP + a separate DATA_SIZE_DISPLAY_MAP
#    - Final files use localized keys directly in DATA_SIZE_MAP + a DATA_SIZE_DB_MAP
#      for reverse-mapping localized labels back to English DB keys
#    - ES base: "Pequeña / Mediana / Grande / Completa"
#    - ES final: "Pequeño / Medio / Grande / Completo" (different gender agreement)
#
# 5. Rank system:
#    - Base files have 4 progressive ranks (0=Trainee, 1=Junior, 2=Senior, 3=Chief)
#    - Final files have a single rank (all tools unlocked from the start)
#    - ES base rank: "Ingeniero Jefe" vs ES final rank: "Arquitecto/a Climático/a Jefe"
#    - CA base rank: "Enginyer Cap" vs CA final rank: "Arquitecte/a Climàtic/a en Cap"
#
# 6. build_final_conclusion_html:
#    - Base files use tier_names progression display
#    - Final files use a certification-style conclusion (no tiers)

"""
The Moral Compass Challenge - Gradio application for the Justice & Equity Challenge.
Updated with i18n support for English (en), Spanish (es), and Catalan (ca).
"""

import os
import random
import time
import threading
from typing import Optional, Dict, Any, Tuple
from functools import lru_cache
import gradio as gr
import pandas as pd

try:
    from aimodelshare.playground import Competition
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    # Mock/Pass if not available locally
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]

# NEW: Team name translations for UI display only
# Internal logic (ranking, caching, grouping) always uses canonical English names
TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Justice League": "The Justice League",
        "The Moral Champions": "The Moral Champions",
        "The Data Detectives": "The Data Detectives",
        "The Ethical Explorers": "The Ethical Explorers",
        "The Fairness Finders": "The Fairness Finders",
        "The Accuracy Avengers": "The Accuracy Avengers"
    },
    "es": {
        "The Justice League": "La Liga de la Justicia",
        "The Moral Champions": "Los Campeones Morales",
        "The Data Detectives": "Los Detectives de Datos",
        "The Ethical Explorers": "Los Exploradores Éticos",
        "The Fairness Finders": "Los Buscadores de Equidad",
        "The Accuracy Avengers": "Los Vengadores de Precisión"
    },
    "ca": {
        "The Justice League": "La Lliga de la Justícia",
        "The Moral Champions": "Els Campions Morals",
        "The Data Detectives": "Els Detectives de Dades",
        "The Ethical Explorers": "Els Exploradors Ètics",
        "The Fairness Finders": "Els Cercadors d'Equitat",
        "The Accuracy Avengers": "Els Venjadors de Precisió"
    }
}

# ---------------------------------------------------------------------------
# In-memory caches
# ---------------------------------------------------------------------------
_cache_lock = threading.Lock()
_leaderboard_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

# ---------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# ---------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "title": "⚖️ The Moral Compass Challenge",
        "loading": "⏳ Loading...",
        "loading_session": "🔒 Loading your session...",
        # Step 1 (Standing)
        "s1_title_auth": "You've Built an Accurate Model",
        "s1_sub_auth": "By experimenting and refining your model, you've achieved impressive results:",
        "lbl_best_acc": "Your Best Accuracy",
        "lbl_ind_rank": "Your Individual Rank",
        "lbl_team": "Your Team",
        "lbl_team_rank": "Team Rank:",
        "s1_li1": "✅ Mastered the model-building process",
        "s1_li2": "✅ Climbed the accuracy leaderboard",
        "s1_li3": "✅ Competed with fellow engineers",
        "s1_li4": "✅ Earned promotions and unlocked tools",
        "s1_congrats": "🏆 Congratulations on your technical achievement!",
        "s1_box_title": "But now you know the full story...",
        "s1_box_text": "High accuracy isn't enough. Real-world AI systems must also be <strong>fair, equitable, and <span class='emph-harm'>minimize harm</span></strong> across all groups of people.",
        "s1_title_guest": "Ready to Begin Your Journey",
        "s1_sub_guest": "You've learned about the model-building process and are ready to take on the challenge:",
        "s1_li1_guest": "✅ Understood the AI model-building process",
        "s1_li2_guest": "✅ Learned about accuracy and performance",
        "s1_li3_guest": "✅ Discovered real-world bias in AI systems",
        "s1_ready": "🎯 Ready to learn about ethical AI!",
        "btn_new_std": "Introduce the New Standard ▶️",
        # Step 2 (Gauge)
        "s2_title": "We Need a Higher Standard",
        "s2_sub": "While your model is accurate, a higher standard is needed to prevent <span class='emph-harm'>real-world harm</span>. To incentivize this new focus, we're introducing a new score.",
        "s2_box_head": "Watch Your Score",
        "lbl_acc_score": "Accuracy Score",
        "s2_box_emph_head": "This score measures only <strong>one dimension</strong> of success.",
        "s2_box_emph_text": "It's time to add a second, equally important dimension: <strong class='emph-fairness'>Ethics</strong>.",
        "btn_back": "◀️ Back",
        "btn_reset": "Reset and Improve ▶️",
        # Step 3 (Reset)
        "s3_title": "Your Accuracy Score Is Being Reset",
        "lbl_score_reset": "Score Reset",
        "s3_why_head": "⚠️ Why This Reset?",
        "s3_why_text": "We reset your score to emphasize a critical truth: your previous success was measured by only <strong>one dimension</strong> — prediction accuracy. So far, you <strong>have not demonstrated</strong> that you know how to make your AI system <span class='emph-fairness'>safe for society</span>. You don’t yet know whether the model you built is <strong class='emph-harm'>just as biased</strong> as the harmful examples we studied in the previous activity. Moving forward, you’ll need to excel on <strong>two fronts</strong>: technical performance <em>and</em> ethical responsibility.",
        "s3_worry_head": "✅ Don't Worry!",
        "s3_worry_text": "As you make your AI more ethical through the upcoming lessons and challenges, <strong>your score will be restored</strong>—and could climb even higher than before.",
        "btn_intro_mc": "Introduce Moral Compass ▶️",
        # Step 4 (Formula)
        "s4_title": "A New Way to Win",
        "s4_sub": "Your new goal is to climb the leaderboard by increasing your <strong>Moral Compass Score</strong>.",
        "s4_formula_head": "📐 The Scoring Formula",
        "s4_formula_text": "<strong>Moral Compass Score</strong> =<br><br>[ Current Model Accuracy ] × [ Ethical Progress % ]",
        "s4_where": "Where:",
        "s4_li1": "<strong>Current Model Accuracy:</strong> Your technical performance",
        "s4_li2": "<strong>Ethical Progress %:</strong> Percentage of:",
        "s4_li2_sub1": "✅ Ethical learning tasks completed",
        "s4_li2_sub2": "✅ Check-in questions answered correctly",
        "s4_mean_head": "💡 What This Means:",
        "s4_mean_text": "You <strong>cannot</strong> win by accuracy alone—you must also demonstrate <strong class='emph-fairness'>ethical understanding</strong>. And you <strong>cannot</strong> win by just completing lessons—you need a working model too. <strong class='emph-risk'>Both dimensions matter</strong>.",
        "btn_see_chal": "See Challenge Ahead ▶️",
        # Step 6 (Path)
        "s6_title": "📍 Your New Starting Point",
        "s6_pos_auth": "You were previously ranked #{rank} on the accuracy leaderboard.",
        "s6_pos_guest": "You will establish your position as you build ethically aware models.",
        "s6_mc_rank": "Current Moral Compass Rank: <span style='color:#b91c1c;'>Not Yet Established</span>",
        "s6_mc_score": "(Moral Compass Score = 0 initially)",
        "s6_path_head": "🛤️ Path Forward",
        "s6_li1": "🔍 Detect and measure bias",
        "s6_li2": "⚖️ Apply fairness metrics",
        "s6_li3": "🔧 Redesign models to minimize harm",
        "s6_li4": "📊 Balance performance & ethics",
        "s6_ach_head": "🏆 Achievement",
        "s6_ach_text": "Improve your Moral Compass Score to earn certification.",
        "s6_scroll": "👇 Continue to the next activity below — or click <span style='white-space:nowrap;'>Next (top bar)</span> in expanded view ➡️",
        "s6_proceed": "Proceed to ethical tooling & evaluation modules."
    },
    "es": {
        "title": "⚖️ El reto de la Brújula Moral",
        "loading": "⏳ Cargando...",
        "loading_session": "🔒 Cargando tu sesión...",
        "s1_title_auth": "Has construido un modelo preciso",
        "s1_sub_auth": "Con experimentación y ajustes continuos, has logrado resultados impresionantes:",
        "lbl_best_acc": "Tu mejor precisión",
        "lbl_ind_rank": "Tu rango individual",
        "lbl_team": "Tu equipo",
        "lbl_team_rank": "Rango de Equipo:",
        "s1_li1": "✅ Dominaste el proceso de construcción de modelos",
        "s1_li2": "✅ Escalaste en la tabla de clasificación de precisión",
        "s1_li3": "✅ Competiste con otros ingenieros e ingenieras",
        "s1_li4": "✅ Ganaste promociones y desbloqueaste herramientas",
        "s1_congrats": "🏆 ¡Felicidades por tu logro técnico!",
        "s1_box_title": "Pero ahora conoces la historia completa...",
        "s1_box_text": "La alta precisión no es suficiente. Los sistemas de IA del mundo real también deben ser <strong>justos, equitativos y <span class='emph-harm'>minimizar el daño</span></strong> para todos los grupos de personas.",
        "s1_title_guest": "Listo para comenzar tu viaje",
        "s1_sub_guest": "Ya conoces cómo se construye un modelo de IA y estás listo para aceptar el desafío:",
        "s1_li1_guest": "✅ Entendiste el proceso de construcción de modelos de IA",
        "s1_li2_guest": "✅ Aprendiste sobre precisión y rendimiento",
        "s1_li3_guest": "✅ Descubriste cómo aparece el sesgo en sistemas reales",
        "s1_ready": "🎯 ¡Listo para aprender sobre IA ética!",
        "btn_new_std": "Introducir el nuevo estándar ▶️",
        "s2_title": "Necesitamos un estándar más alto",
        "s2_sub": "Si bien tu modelo es preciso, se necesita un estándar más alto para prevenir <span class='emph-harm'>daños reales</span>. Para incentivar este nuevo enfoque, introducimos una nueva puntuación.",
        "s2_box_head": "Observa tu puntuación",
        "lbl_acc_score": "Puntuación de precisión",
        "s2_box_emph_head": "Esta puntuación mide solo <strong>una dimensión</strong> del éxito.",
        "s2_box_emph_text": "Es hora de agregar una segunda dimensión igualmente importante: <strong class='emph-fairness'>Ética</strong>.",
        "btn_back": "◀️ Atrás",
        "btn_reset": "Reiniciar y mejorar ▶️",
        "s3_title": "Vamos a reiniciar tu puntuación de precisión",
        "lbl_score_reset": "Puntuación reiniciada",
        "s3_why_head": "⚠️ ¿Por qué este reinicio?",
        "s3_why_text": "Hemos reiniciado tu puntuación para subrayar una verdad importante: tu éxito anterior solo medía <strong>una dimensión</strong> — precisión de predicción. Todavía, <strong>no has demostrado</strong> que sabes cómo diseñar un sistema de IA que sea <span class='emph-fairness'>seguro para la sociedad</span>. Tampoco sabes si el modelo que construiste está <strong class='emph-harm'>tan sesgado</strong> como los ejemplos dañinos que estudiamos en la actividad anterior. A partir de ahora, tendrás que destacar en <strong>dos frentes</strong>: rendimiento técnico <em>y</em> responsabilidad ética.",
        "s3_worry_head": "✅ ¡No te preocupes!",
        "s3_worry_text": "A medida que hagas que tu IA sea más ética a través de las próximas lecciones y desafíos, <strong>recuperarás tu puntuación</strong>—y podría llegar a ser incluso más alta que antes.",
        "btn_intro_mc": "Introducir Brújula Moral ▶️",
        "s4_title": "Una nueva forma de ganar",
        "s4_sub": "Tu nuevo objetivo es escalar en la clasificación gracias a tu <strong>Puntuación de Brújula Moral</strong>.",
        "s4_formula_head": "📐 La fórmula de puntuación",
        "s4_formula_text": "<strong>Puntuación de Brújula Moral</strong> =<br><br>[ Precisión del Modelo Actual ] × [ Progreso Ético % ]",
        "s4_where": "Donde:",
        "s4_li1": "<strong>Precisión del Modelo Actual:</strong> Tu rendimiento técnico",
        "s4_li2": "<strong>Progreso Ético %:</strong> Porcentaje de:",
        "s4_li2_sub1": "✅ Tareas de aprendizaje ético completadas",
        "s4_li2_sub2": "✅ Preguntas de control respondidas correctamente",
        "s4_mean_head": "💡 Qué significa esto:",
        "s4_mean_text": "<strong>No puedes</strong> ganar solo con precisión—también debes demostrar <strong class='emph-fairness'>comprensión ética</strong>. Y <strong>no puedes</strong> ganar solo completando lecciones—también necesitas un modelo que funcione. <strong class='emph-risk'>Ambas dimensiones importan</strong>.",
        "btn_see_chal": "Ver el desafío ▶️",
        "s6_title": "📍 Tu nuevo punto de partida",
        "s6_pos_auth": "Antes ocupabas el puesto #{rank} en la tabla de clasificación de precisión.",
        "s6_pos_guest": "Establecerás tu posición a medida que construyas modelos éticamente conscientes.",
        "s6_mc_rank": "Rango actual de Brújula Moral: <span style='color:#b91c1c;'>Aún no establecido</span>",
        "s6_mc_score": "(Puntuación de Brújula Moral = 0 inicialmente)",
        "s6_path_head": "🛤️ Camino a seguir",
        "s6_li1": "🔍 Detectar y medir sesgos",
        "s6_li2": "⚖️ Aplicar métricas de equidad",
        "s6_li3": "🔧 Rediseñar modelos para minimizar daños",
        "s6_li4": "📊 Equilibrar rendimiento y ética",
        "s6_ach_head": "🏆 Logro",
        "s6_ach_text": "Mejora tu Puntuación de Brújula Moral para obtener la certificación.",
        "s6_scroll": "👇 Continúa con la siguiente actividad abajo — o haz clic en <span style='white-space:nowrap;'>Siguiente (barra superior)</span> en vista ampliada ➡️",
        "s6_proceed": "Proceder a herramientas y evaluación ética."
    },
    "ca": {
        "title": "⚖️ El repte de la Brúixola Moral",
        "loading": "⏳ Carregant...",
        "loading_session": "🔒 Carregant la teva sessió...",
        "s1_title_auth": "Has construït un model precís",
        "s1_sub_auth": "Amb experimentació i ajustos constants, has aconseguit resultats impressionants:",
        "lbl_best_acc": "La teva millor precisió",
        "lbl_ind_rank": "El teu rang individual",
        "lbl_team": "El teu equip",
        "lbl_team_rank": "Rang d'equip:",
        "s1_li1": "✅ Has dominat el procés de construcció de models",
        "s1_li2": "✅ Has escalat a la taula de classificació de precisió",
        "s1_li3": "✅ Has competit amb altres enginyers i enginyeres",
        "s1_li4": "✅ Has guanyat promocions i desbloquejat eines",
        "s1_congrats": "🏆 Felicitats pel teu èxit tècnic!",
        "s1_box_title": "Però ara ja coneixes tota la història...",
        "s1_box_text": "L'alta precisió no és suficient. Els sistemes d'IA del món real també han de ser <strong>justos, equitatius i <span class='emph-harm'>minimitzar el dany</span></strong> per a tots els grups de persones.",
        "s1_title_guest": "A punt per començar el teu viatge",
        "s1_sub_guest": "Ja saps com es construeix un model d’IA i estàs preparat/ada per afrontar el repte:",
        "s1_li1_guest": "✅ Has entès el procés de construcció de models d'IA",
        "s1_li2_guest": "✅ Has après sobre precisió i rendiment",
        "s1_li3_guest": "✅ Has descobert com apareix el biaix en sistemes reals",
        "s1_ready": "🎯 A punt per aprendre sobre IA ètica!",
        "btn_new_std": "Introduir el nou estàndard ▶️",
        "s2_title": "Necessitem un estàndard més alt",
        "s2_sub": "Tot i que el teu model és precís, cal un estàndard més alt per prevenir <span class='emph-harm'>danys reals</span>. Per impulsar aquest nou enfocament, introduïm una nova puntuació.",
        "s2_box_head": "Observa la teva puntuació",
        "lbl_acc_score": "Puntuació de precisió",
        "s2_box_emph_head": "Aquesta puntuació mesura només <strong>una dimensió</strong> de l'èxit.",
        "s2_box_emph_text": "És hora d'afegir una segona dimensió igualment important: <strong class='emph-fairness'>Ètica</strong>.",
        "btn_back": "◀️ Enrere",
        "btn_reset": "Reiniciar i millorar ▶️",
        "s3_title": "Reiniciarem la teva puntuació de precisió",
        "lbl_score_reset": "Puntuació reiniciada",
        "s3_why_head": "⚠️ Per què aquest reinici?",
        "s3_why_text": "Hem reiniciat la teva puntuació per subratllar una veritat important: el teu èxit anterior només mesurava <strong>una dimensió</strong> — precisió de predicció. Encara <strong>no has demostrat</strong> que saps com dissenyar un sistema d’IA <span class='emph-fairness'>segur per a la societat</span>. Tampoc saps si el model que has construït és <strong class='emph-harm'>tan esbiaixat</strong> com els exemples perjudicials que hem estudiat en l'activitat anterior. D'ara endavant, hauràs de destacar en <strong>dos fronts</strong>: rendiment tècnic <em>i</em> responsabilitat ètica.",
        "s3_worry_head": "✅ No et preocupis!",
        "s3_worry_text": "A mesura que facis que la teva IA sigui més ètica a través de les properes lliçons i reptes, <strong>recuperaràs la teva puntuació</strong>—i fins i tot podria arribar a ser més alta que abans.",
        "btn_intro_mc": "Introduir Brúixola Moral ▶️",
        "s4_title": "Una nova manera de guanyar",
        "s4_sub": "El teu nou objectiu és pujar en la classificació gràcies a la teva <strong>Puntuació de Brúixola Moral</strong>.",
        "s4_formula_head": "📐 La fórmula de puntuació",
        "s4_formula_text": "<strong>Puntuació de Brúixola Moral</strong> =<br><br>[ Precisió del Model Actual ] × [ Progrés Ètic % ]",
        "s4_where": "On:",
        "s4_li1": "<strong>Precisió del Model Actual:</strong> El teu rendiment tècnic",
        "s4_li2": "<strong>Progrés Ètic %:</strong> Percentatge de:",
        "s4_li2_sub1": "✅ Tasques d'aprenentatge ètic completades",
        "s4_li2_sub2": "✅ Preguntes de control respostes correctament",
        "s4_mean_head": "💡 Què significa això:",
        "s4_mean_text": "<strong>No pots</strong> guanyar només amb precisió—també has de demostrar <strong class='emph-fairness'>comprensió ètica</strong>. I <strong>no pots</strong> guanyar només completant lliçons—també necessites un model que funcioni. <strong class='emph-risk'>Les dues dimensions són importants</strong>.",
        "btn_see_chal": "Veure el repte ▶️",
        "s6_title": "📍 El teu nou punt de partida",
        "s6_pos_auth": "Abans ocupaves la posició #{rank} a la taula de classificació de precisió.",
        "s6_pos_guest": "Establiràs la teva posició a mesura que construeixis models èticament conscients.",
        "s6_mc_rank": "Rang actual de Brúixola Moral: <span style='color:#b91c1c;'>Encara no establert</span>",
        "s6_mc_score": "(Puntuació de Brúixola Moral = 0 inicialment)",
        "s6_path_head": "🛤️ Camí a seguir",
        "s6_li1": "🔍 Detectar i mesurar biaixos",
        "s6_li2": "⚖️ Aplicar mètriques d'equitat",
        "s6_li3": "🔧 Redissenyar models per minimitzar danys",
        "s6_li4": "📊 Equilibrar rendiment i ètica",
        "s6_ach_head": "🏆 Assoliment",
        "s6_ach_text": "Millora la teva Puntuació de Brúixola Moral per obtenir la certificació.",
        "s6_scroll": "👇 Continua amb la següent activitat a sota — o fes clic a <span style='white-space:nowrap;'>Següent (barra superior)</span> en vista ampliada ➡️",
        "s6_proceed": "Procedir a eines i avaluació ètica."
    }
}

# ---------------------------------------------------------------------------
# Logic / Helpers
# ---------------------------------------------------------------------------

def _log(msg: str):
    if DEBUG_LOG:
        print(f"[MoralCompassApp] {msg}")

def _normalize_team_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(str(name).strip().split())

# NEW: Team name translation helpers for UI display
def translate_team_name_for_display(team_en: str, lang: str = "en") -> str:
    """
    Translate a canonical English team name to the specified language for UI display.
    Fallback to English if translation not found.
    """
    if lang not in TEAM_NAME_TRANSLATIONS:
        lang = "en"
    return TEAM_NAME_TRANSLATIONS[lang].get(team_en, team_en)

# NEW: Reverse lookup for future use (e.g., if user input needs to be normalized back to English)
def translate_team_name_to_english(display_name: str, lang: str = "en") -> str:
    """
    Reverse lookup: given a localized team name, return the canonical English name.
    Returns the original display_name if not found.
    """
    if lang not in TEAM_NAME_TRANSLATIONS:
        return display_name  # Already English or unknown
    
    translations = TEAM_NAME_TRANSLATIONS[lang]
    for english_name, localized_name in translations.items():
        if localized_name == display_name:
            return english_name
    return display_name  # UPDATED: Return display_name instead of None for consistency

# NEW: Format leaderboard DataFrame with localized team names (non-destructive copy)
def _format_leaderboard_for_display(df: Optional[pd.DataFrame], lang: str = "en") -> Optional[pd.DataFrame]:
    """
    Create a copy of the leaderboard DataFrame with team names translated for display.
    Does not mutate the original DataFrame.
    For potential future use when displaying full leaderboard.
    """
    if df is None:
        return None  # UPDATED: Handle None explicitly
    
    if df.empty or "Team" not in df.columns:
        return df.copy()  # UPDATED: Return copy for empty or missing Team column
    
    df_display = df.copy()
    df_display["Team"] = df_display["Team"].apply(lambda t: translate_team_name_for_display(t, lang))
    return df_display

def _fetch_leaderboard(token: str) -> Optional[pd.DataFrame]:
    now = time.time()
    with _cache_lock:
        if (
            _leaderboard_cache["data"] is not None
            and now - _leaderboard_cache["timestamp"] < LEADERBOARD_CACHE_SECONDS
        ):
            return _leaderboard_cache["data"]

    try:
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        df = playground.get_leaderboard(token=token)
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
    except Exception as e:
        _log(f"Leaderboard fetch failed: {e}")
        df = None

    with _cache_lock:
        _leaderboard_cache["data"] = df
        _leaderboard_cache["timestamp"] = time.time()
    return df

def _get_or_assign_team(username: str, leaderboard_df: Optional[pd.DataFrame]) -> Tuple[str, bool]:
    try:
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(
                            user_submissions["timestamp"], errors="coerce"
                        )
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                    except Exception as ts_err:
                        _log(f"Timestamp sort error: {ts_err}")
                existing_team = user_submissions.iloc[0]["Team"]
                if pd.notna(existing_team) and str(existing_team).strip():
                    return _normalize_team_name(existing_team), False
        return _normalize_team_name(random.choice(TEAM_NAMES)), True
    except Exception as e:
        _log(f"Team assignment error: {e}")
        return _normalize_team_name(random.choice(TEAM_NAMES)), True

def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id:
            return False, None, None
        token = get_token_from_session(session_id)
        if not token:
            return False, None, None
        username = _get_username_from_token(token)
        if not username:
            return False, None, None
        return True, username, token
    except Exception as e:
        _log(f"Session auth failed: {e}")
        return False, None, None

def _compute_user_stats(username: str, token: str) -> Dict[str, Any]:
    now = time.time()
    cached = _user_stats_cache.get(username)
    if cached and (now - cached.get("_ts", 0) < USER_STATS_TTL):
        return cached

    leaderboard_df = _fetch_leaderboard(token)
    team_name, _ = _get_or_assign_team(username, leaderboard_df)
    best_score = None
    rank = None
    team_rank = None

    try:
        if leaderboard_df is not None and not leaderboard_df.empty:
            if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
                user_submissions = leaderboard_df[leaderboard_df["username"] == username]
                if not user_submissions.empty:
                    best_score = user_submissions["accuracy"].max()

                # Individual rank
                user_bests = leaderboard_df.groupby("username")["accuracy"].max()
                summary_df = user_bests.reset_index()
                summary_df.columns = ["Engineer", "Best_Score"]
                summary_df = summary_df.sort_values("Best_Score", ascending=False).reset_index(drop=True)
                summary_df.index = summary_df.index + 1
                my_row = summary_df[summary_df["Engineer"] == username]
                if not my_row.empty:
                    rank = my_row.index[0]

                # Team rank
                if "Team" in leaderboard_df.columns and team_name:
                    team_summary_df = (
                        leaderboard_df.groupby("Team")["accuracy"]
                        .agg(Best_Score="max")
                        .reset_index()
                        .sort_values("Best_Score", ascending=False)
                        .reset_index(drop=True)
                    )
                    team_summary_df.index = team_summary_df.index + 1
                    my_team_row = team_summary_df[team_summary_df["Team"] == team_name]
                    if not my_team_row.empty:
                        team_rank = my_team_row.index[0]
    except Exception as e:
        _log(f"User stats error for {username}: {e}")

    stats = {
        "username": username,
        "best_score": best_score,
        "rank": rank,
        "team_name": team_name,
        "team_rank": team_rank,
        "is_signed_in": True,
        "_ts": now
    }
    _user_stats_cache[username] = stats
    return stats

# ---------------------------------------------------------------------------
# HTML Helpers (I18N)
# ---------------------------------------------------------------------------

def t(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

def build_standing_html(user_stats, lang="en"):
    if user_stats["is_signed_in"] and user_stats["best_score"] is not None:
        best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
        rank_text = f"#{user_stats['rank']}" if user_stats["rank"] else "N/A"
        # UPDATED: Translate team name for display based on selected language
        team_text = translate_team_name_for_display(user_stats["team_name"], lang) if user_stats["team_name"] else "N/A"
        team_rank_text = f"#{user_stats['team_rank']}" if user_stats["team_rank"] else "N/A"
        return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                {t(lang, 's1_title_auth')}
            </h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    {t(lang, 's1_sub_auth')}
                </p>
                <div class='stat-grid'>
                    <div class='stat-card stat-card--success'>
                        <p class='stat-card__label'>{t(lang, 'lbl_best_acc')}</p>
                        <p class='stat-card__value'>{best_score_pct}</p>
                    </div>
                    <div class='stat-card stat-card--accent'>
                        <p class='stat-card__label'>{t(lang, 'lbl_ind_rank')}</p>
                        <p class='stat-card__value'>{rank_text}</p>
                    </div>
                </div>
                <div class='team-card'>
                    <p class='team-card__label'>{t(lang, 'lbl_team')}</p>
                    <p class='team-card__value'>🛡️ {team_text}</p>
                    <p class='team-card__rank'>{t(lang, 'lbl_team_rank')} {team_rank_text}</p>
                </div>
                <ul class='bullet-list'>
                    <li>{t(lang, 's1_li1')}</li>
                    <li>{t(lang, 's1_li2')}</li>
                    <li>{t(lang, 's1_li3')}</li>
                    <li>{t(lang, 's1_li4')}</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>
                    {t(lang, 's1_congrats')}
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    {t(lang, 's1_box_title')}
                </p>
                <p>
                    {t(lang, 's1_box_text')}
                </p>
            </div>
        </div>
        """
    elif user_stats["is_signed_in"]:
        return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                {t(lang, 's1_title_guest')}
            </h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    {t(lang, 's1_sub_guest')}
                </p>
                <ul class='bullet-list'>
                    <li>{t(lang, 's1_li1_guest')}</li>
                    <li>{t(lang, 's1_li2_guest')}</li>
                    <li>{t(lang, 's1_li3_guest')}</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>
                    {t(lang, 's1_ready')}
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    {t(lang, 's1_box_title')}
                </p>
                <p>
                    {t(lang, 's1_box_text')}
                </p>
            </div>
        </div>
        """
    else:
        return f"""
        <div class='slide-shell slide-shell--warning' style='text-align:center;'>
            <h2 class='slide-shell__title'>
                {t(lang, 'loading_session')}
            </h2>
        </div>
        """

def build_step2_html(user_stats, lang="en"):
    if user_stats.get("is_signed_in") and user_stats.get("best_score") is not None:
        gauge_value = int(user_stats["best_score"] * 100)
    else:
        gauge_value = 75
    gauge_percent = f"{gauge_value}%"
    return f"""
    <div class='slide-shell slide-shell--warning'>
        <h3 class='slide-shell__title'>{t(lang, 's2_title')}</h3>
        <p class='slide-shell__subtitle'>
            {t(lang, 's2_sub')}
        </p>
        <div class='content-box'>
            <h4 class='content-box__heading'>{t(lang, 's2_box_head')}</h4>
            <div class='score-gauge-container'>
                <div class='score-gauge' style='--fill-percent:{gauge_percent};'>
                    <div class='score-gauge-inner'>
                        <div class='score-gauge-value'>{gauge_value}</div>
                        <div class='score-gauge-label'>{t(lang, 'lbl_acc_score')}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class='content-box content-box--emphasis'>
            <p class='content-box__heading'>
                {t(lang, 's2_box_emph_head')}
            </p>
            <p>
                {t(lang, 's2_box_emph_text')}
            </p>
        </div>
    </div>
    """

def _get_step3_html(lang):
    return f"""
    <div class='slide-shell slide-shell--warning'>
        <div style='text-align:center;'>
            <h3 class='slide-shell__title'>
                {t(lang, 's3_title')}
            </h3>
            <div class='score-gauge-container'>
                <div class='score-gauge gauge-dropped' style='--fill-percent: 0%;'>
                    <div class='score-gauge-inner'>
                        <div class='score-gauge-value' style='color:#dc2626;'>0</div>
                        <div class='score-gauge-label'>{t(lang, 'lbl_score_reset')}</div>
                    </div>
                </div>
            </div>
            <div class='content-box content-box--danger'>
                <h4 class='content-box__heading'>
                    {t(lang, 's3_why_head')}
                </h4>
                <p class='slide-teaching-body' style='text-align:left;'>
                    {t(lang, 's3_why_text')}
                </p>
            </div>
            <div class='content-box content-box--success'>
                <h4 class='content-box__heading'>
                    {t(lang, 's3_worry_head')}
                </h4>
                <p class='slide-teaching-body'>
                    {t(lang, 's3_worry_text')}
                </p>
            </div>
        </div>
    </div>
    """

def _get_step4_html(lang):
    return f"""
    <div class='slide-shell slide-shell--info'>
        <h3 class='slide-shell__title'>
            {t(lang, 's4_title')}
        </h3>
        <p class='slide-shell__subtitle'>
            {t(lang, 's4_sub')}
        </p>
        <div class='content-box formula-box'>
            <h4 class='content-box__heading' style='text-align:center;'>{t(lang, 's4_formula_head')}</h4>
            <div class='formula-math'>
                {t(lang, 's4_formula_text')}
            </div>
            <div class='content-box' style='margin-top:20px;'>
                <p class='content-box__heading'>{t(lang, 's4_where')}</p>
                <ul class='bullet-list'>
                    <li>{t(lang, 's4_li1')}</li>
                    <li>
                        {t(lang, 's4_li2')}
                        <ul class='bullet-list' style='margin-top:8px;'>
                            <li>{t(lang, 's4_li2_sub1')}</li>
                            <li>{t(lang, 's4_li2_sub2')}</li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
        <div class='content-box content-box--success'>
            <h4 class='content-box__heading'>{t(lang, 's4_mean_head')}</h4>
            <p class='slide-teaching-body'>
                {t(lang, 's4_mean_text')}
            </p>
        </div>
    </div>
    """

def build_step6_html(user_stats, lang="en"):
    if user_stats.get("is_signed_in") and user_stats.get("rank"):
        position_msg = t(lang, 's6_pos_auth').replace("{rank}", str(user_stats['rank']))
    else:
        position_msg = t(lang, 's6_pos_guest')

    proceed_line = t(lang, 's6_proceed')

    return f"""
    <div class='slide-shell slide-shell--info'>
        <h3 class='slide-shell__title'>{t(lang, 's6_title')}</h3>
        <div class='content-box'>
            <p>{position_msg}</p>
            <div class='content-box content-box--danger'>
                <p class='content-box__heading'>
                    {t(lang, 's6_mc_rank')}
                </p>
                <p>{t(lang, 's6_mc_score')}</p>
            </div>
        </div>
        <div class='content-box content-box--success'>
            <h4 class='content-box__heading'>{t(lang, 's6_path_head')}</h4>
            <ul class='bullet-list'>
                <li>{t(lang, 's6_li1')}</li>
                <li>{t(lang, 's6_li2')}</li>
                <li>{t(lang, 's6_li3')}</li>
                <li>{t(lang, 's6_li4')}</li>
            </ul>
        </div>
        <div class='content-box content-box--emphasis'>
            <p class='content-box__heading'>
                {t(lang, 's6_ach_head')}
            </p>
            <p>{t(lang, 's6_ach_text')}</p>
        </div>
        <h1 class='final-instruction' style='margin:32px 0 16px 0;'>{t(lang, 's6_scroll')}</h1>
        {f"<p style='text-align:center;'>{proceed_line}</p>" if proceed_line else ""}
    </div>
    """

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = """
.large-text { font-size: 20px !important; }
/* Slide + containers */
.slide-shell {
  padding: 28px;
  border-radius: 16px;
  background-color: var(--block-background-fill);
  color: var(--body-text-color);
  border: 2px solid var(--border-color-primary);
  box-shadow: 0 8px 20px rgba(0,0,0,0.05);
  max-width: 900px;
  margin: 0 auto 24px auto;
  font-size: 20px;
}
.slide-shell--info { border-color: var(--color-accent); }
.slide-shell--warning { border-color: var(--color-accent); }
.slide-shell__title {
  font-size: 2rem; margin: 0 0 16px 0; text-align: center;
}
.slide-shell__subtitle {
  font-size: 1.1rem; margin-top: 8px; text-align: center; color: var(--secondary-text-color); line-height: 1.7;
}
.content-box {
  background-color: var(--block-background-fill); border-radius: 12px; border: 1px solid var(--border-color-primary); padding: 24px; margin: 24px 0;
}
.content-box__heading {
  margin-top: 0; font-weight: 600; font-size: 1.2rem;
}
.content-box--emphasis { border-left: 6px solid var(--color-accent); }
.content-box--danger { border-left: 6px solid #dc2626; }
.content-box--success { border-left: 6px solid #16a34a; }
.bullet-list {
  list-style: none; padding-left: 0; margin: 16px auto 0 auto; max-width: 600px; font-size: 1.05rem;
}
.bullet-list li { padding: 6px 0; }
/* Stats cards */
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 24px auto; max-width: 600px; }
.stat-card, .team-card {
  text-align: center; padding: 16px; border-radius: 10px; border: 1px solid var(--border-color-primary); background-color: var(--block-background-fill);
}
.stat-card__label, .team-card__label { margin: 0; font-size: 0.9rem; color: var(--secondary-text-color); }
.stat-card__value { margin: 8px 0 0 0; font-size: 2.2rem; font-weight: 800; }
.stat-card--success .stat-card__value { color: #16a34a; }
.stat-card--accent .stat-card__value { color: var(--color-accent); }
.team-card__value { margin: 8px 0 4px 0; font-size: 1.5rem; font-weight: 700; }
.team-card__rank { margin: 0; font-size: 1rem; color: var(--secondary-text-color); }
/* Teaching body */
.slide-teaching-body { font-size: 1.1rem; line-height: 1.8; margin-top: 1rem; }
/* Emphasis */
.emph-harm { color: #b91c1c; font-weight: 700; }
.emph-risk { color: #b45309; font-weight: 600; }
.emph-fairness { color: var(--color-accent); font-weight: 600; }
@media (prefers-color-scheme: dark) {
  .emph-harm { color: #fca5a5; }
  .emph-risk { color: #fed7aa; }
}
/* Gauge */
.score-gauge-container { position: relative; width: 260px; height: 260px; margin: 24px auto; }
.score-gauge {
  width: 100%; height: 100%; border-radius: 50%;
  background: conic-gradient(from 180deg, #16a34a 0%, #16a34a var(--fill-percent, 0%), var(--border-color-primary) var(--fill-percent, 0%), var(--border-color-primary) 100%);
  display: flex; align-items: center; justify-content: center; position: relative; box-shadow: 0 10px 30px rgba(0,0,0,0.12);
}
.score-gauge-inner {
  width: 70%; height: 70%; border-radius: 50%; background-color: var(--block-background-fill);
  display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 2; border: 1px solid var(--border-color-primary);
}
.score-gauge-value { font-size: 3.2rem; font-weight: 800; color: var(--body-text-color); line-height: 1; }
.score-gauge-label { font-size: 0.95rem; color: var(--secondary-text-color); margin-top: 8px; }
/* Gauge reset animation */
@keyframes gauge-drop {
  0% { background: conic-gradient(from 180deg,#16a34a 0%,#16a34a 75%,var(--border-color-primary) 75%,var(--border-color-primary) 100%); }
  100% { background: conic-gradient(from 180deg,#dc2626 0%,#dc2626 0%,var(--border-color-primary) 0%,var(--border-color-primary) 100%); }
}
/* Compact, responsive CTA sizing */
.final-instruction {
  font-size: clamp(1.5rem, 2vw + 0.6rem, 2rem);
  line-height: 1.25;
  margin: 16px 0;
}
.gauge-dropped { animation: gauge-drop 2s ease-out forwards; }
/* Navigation overlay */
#nav-loading-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background-color: var(--body-background-fill); z-index:9999; display:none; flex-direction:column; align-items:center; justify-content:center; opacity:0; transition:opacity .25s ease; }
.nav-spinner { width:50px; height:50px; border:5px solid var(--block-background-fill); border-top:5px solid var(--color-accent); border-radius:50%; animation: nav-spin 1s linear infinite; margin-bottom:20px; }
@keyframes nav-spin { to { transform: rotate(360deg); } }
#nav-loading-text { font-size:1.3rem; font-weight:600; color: var(--body-text-color); }
@media (prefers-color-scheme: dark) { .slide-shell, .content-box, .alert { box-shadow:none; } .score-gauge { box-shadow:none; } }
"""

# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------
def create_moral_compass_challenge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=CSS) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)
        
        # --- Components ---
        c_title = gr.Markdown("<h1 style='text-align:center;'>⚖️ The Moral Compass Challenge</h1>")

        # Initial loading (visible first)
        with gr.Column(visible=True, elem_id="initial-loading") as initial_loading:
            c_loading = gr.Markdown("<div style='text-align:center; padding:80px 0;'><h2>⏳ Loading...</h2></div>")

        # Step 1
        with gr.Column(visible=False, elem_id="step-1") as step_1:
            stats_display = gr.HTML() # Built dynamically
            step_1_next = gr.Button(t('en', 'btn_new_std'), variant="primary", size="lg")

        # Step 2
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            step_2_html_comp = gr.HTML() # Built dynamically
            with gr.Row():
                step_2_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_2_next = gr.Button(t('en', 'btn_reset'), variant="primary", size="lg")

        # Step 3
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            step_3_html_comp = gr.HTML(_get_step3_html('en'))
            with gr.Row():
                step_3_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_3_next = gr.Button(t('en', 'btn_intro_mc'), variant="primary", size="lg")

        # Step 4
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            step_4_html_comp = gr.HTML(_get_step4_html('en'))
            with gr.Row():
                step_4_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_4_next = gr.Button(t('en', 'btn_see_chal'), variant="primary", size="lg")

        # Step 6
        with gr.Column(visible=False, elem_id="step-6") as step_6:
            step_6_html_comp = gr.HTML() # Built dynamically
            with gr.Row():
                step_6_back = gr.Button(t('en', 'btn_back'), size="lg")

        loading_screen = gr.Column(visible=False)
        all_steps = [step_1, step_2, step_3, step_4, step_6, loading_screen, initial_loading]

        # -------------------------------------------------------------------------
        # HYBRID CACHING LOGIC (OPTIMIZED)
        # -------------------------------------------------------------------------

        # 1. Define update targets (Order must match the return list below)
        update_targets = [
            initial_loading, step_1,
            c_title, c_loading,
            stats_display, step_2_html_comp, step_6_html_comp, # Dynamic HTML
            step_3_html_comp, step_4_html_comp,                # Static HTML
            step_1_next, step_2_back, step_2_next, step_3_back, step_3_next, step_4_back, step_4_next, step_6_back
        ]

        # 2. Cached Generator for Static Content (Steps 3 & 4 + Buttons)
        @lru_cache(maxsize=16)
        def get_cached_static_content(lang):
            """
            Generates the heavy static HTML for Steps 3 & 4 and all buttons once per language.
            """
            return [
                # Static HTML Steps
                _get_step3_html(lang),
                _get_step4_html(lang),
                
                # All Buttons
                gr.Button(value=t(lang, 'btn_new_std')), # step_1_next
                gr.Button(value=t(lang, 'btn_back')),    # step_2_back
                gr.Button(value=t(lang, 'btn_reset')),   # step_2_next
                gr.Button(value=t(lang, 'btn_back')),    # step_3_back
                gr.Button(value=t(lang, 'btn_intro_mc')),# step_3_next
                gr.Button(value=t(lang, 'btn_back')),    # step_4_back
                gr.Button(value=t(lang, 'btn_see_chal')),# step_4_next
                gr.Button(value=t(lang, 'btn_back'))     # step_6_back
            ]

        # 3. Hybrid Load Function
        def initial_load(request: gr.Request):
            # 1. Language
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS: lang = "en"
            
            # 2. Auth (Dynamic)
            success, username, token = _try_session_based_auth(request)
            
            # 3. Stats (Dynamic)
            stats = {"is_signed_in": False, "best_score": None}
            if success and username:
                stats = _compute_user_stats(username, token)
            
            # 4. Build Dynamic HTML
            html_standing = build_standing_html(stats, lang)
            html_step2 = build_step2_html(stats, lang)
            html_step6 = build_step6_html(stats, lang)
            
            # 5. Fetch Static Content from Cache
            static_content = get_cached_static_content(lang)
            
            # 6. Combine
            return [
                gr.update(visible=False), # initial_loading
                gr.update(visible=True),  # step_1
                
                # Text Updates
                f"<h1 style='text-align:center;'>{t(lang, 'title')}</h1>",
                f"<div style='text-align:center; padding:80px 0;'><h2>{t(lang, 'loading')}</h2></div>",
                
                # Dynamic HTML
                html_standing,
                html_step2,
                html_step6,
                
                # Static HTML & Buttons (Unpacked from cache)
                *static_content
            ]

        demo.load(fn=initial_load, inputs=None, outputs=update_targets)

        # --- Navigation ---
        def _nav_generator(target):
            def go():
                yield {**{s: gr.update(visible=False) for s in all_steps}, loading_screen: gr.update(visible=True)}
                yield {**{s: gr.update(visible=False) for s in all_steps}, target: gr.update(visible=True)}
            return go

        def _nav_js(target_id: str, message: str) -> str:
            return f"""
            ()=>{{
              try {{
                const overlay=document.getElementById('nav-loading-overlay');
                const msg=document.getElementById('nav-loading-text');
                if(overlay && msg){{ msg.textContent='{message}'; overlay.style.display='flex'; setTimeout(()=>overlay.style.opacity='1',10); }}
                const start=Date.now();
                setTimeout(()=>{{ window.scrollTo({{top:0, behavior:'smooth'}}); }},40);
                const poll=setInterval(()=>{{
                  const elapsed=Date.now()-start;
                  const target=document.getElementById('{target_id}');
                  const visible=target && target.offsetParent!==null;
                  if((visible && elapsed>=600) || elapsed>5000){{
                    clearInterval(poll);
                    if(overlay){{ overlay.style.opacity='0'; setTimeout(()=>overlay.style.display='none',300); }}
                  }}
                }},90);
              }} catch(e){{}}
            }}
            """

        step_1_next.click(fn=_nav_generator(step_2), outputs=all_steps, js=_nav_js("step-2", "Loading..."))
        step_2_back.click(fn=_nav_generator(step_1), outputs=all_steps, js=_nav_js("step-1", "Loading..."))
        step_2_next.click(fn=_nav_generator(step_3), outputs=all_steps, js=_nav_js("step-3", "Loading..."))
        step_3_back.click(fn=_nav_generator(step_2), outputs=all_steps, js=_nav_js("step-2", "Loading..."))
        step_3_next.click(fn=_nav_generator(step_4), outputs=all_steps, js=_nav_js("step-4", "Loading..."))
        step_4_back.click(fn=_nav_generator(step_3), outputs=all_steps, js=_nav_js("step-3", "Loading..."))
        step_4_next.click(fn=_nav_generator(step_6), outputs=all_steps, js=_nav_js("step-6", "Loading..."))
        step_6_back.click(fn=_nav_generator(step_4), outputs=all_steps, js=_nav_js("step-4", "Loading..."))

    return demo

def launch_moral_compass_challenge_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_moral_compass_challenge_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

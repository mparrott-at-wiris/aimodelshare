"""
The Ethical Revelation: Real-World Impact - Gradio application for the Justice & Equity Challenge.
Updated with i18n support for English (en), Spanish (es), and Catalan (ca).
"""

import os
import random
import time
import threading
from typing import Optional, Dict, Any, Tuple
from functools import lru_cache
import pandas as pd
import gradio as gr

# --- AI Model Share Imports ---
try:
    from aimodelshare.playground import Competition
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Configuration & Caching
# ---------------------------------------------------------------------------
LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]

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

_cache_lock = threading.Lock()
_leaderboard_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

# ---------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# ---------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "title": "🚀 The Ethical Revelation: Real-World Impact",
        "loading_personal": "⏳ Loading your personalized experience...",
        # Stats Screen
        "stats_title": "🏆 Great Work, Engineer! 🏆",
        "stats_subtitle": "Here's your performance summary.",
        "stats_heading": "Your Stats",
        "lbl_accuracy": "Best Accuracy",
        "lbl_rank": "Your Rank",
        "lbl_team": "Team",
        "stats_footer": "Ready to share your model and explore its real-world impact?",
        "btn_deploy": "🌍 Share Your AI Model (Simulation Only)",
        "guest_title": "🚀 You're Signed In!",
        "guest_subtitle": "You haven't submitted a model yet, but you're all set to continue learning.",
        "guest_body": "Once you submit a model in the Model Building Game, your accuracy and ranking will appear here.",
        "guest_footer": "Continue to the next section when you're ready.",
        "loading_session": "🔒 Loading your session...",
        
        # Step 2 (Context)
        "s2_title": "🏛️ The Real-World Parallel",
        "s2_intro": "Your model works just like a real system used in the US justice system.",
        "s2_box_title": "What is COMPAS?",
        "s2_p1": "<strong>COMPAS</strong> is an AI system designed to predict the <strong>risk of reoffending</strong> (recidivism).",
        "s2_p2": "Judges across the United States used these risk scores to help decide who stayed in jail and who was released.",
        "s2_p3": "But in 2016, <strong>journalists at ProPublica</strong> discovered a serious problem...",
        "btn_back": "◀️ Back",
        "btn_reveal": "See What They Found ▶️",
        
        # Step 3 (ProPublica)
        "s3_title": "📰 Investigative Report",
        "s3_head": "The Hidden Bias",
        "s3_p1": "The journalists analyzed <strong>7,000 real cases</strong>. They compared the AI's predictions vs. reality.",
        "s3_chart_title": "ERROR RATE: Incorrectly Flagged as 'High Risk'",
        "s3_bar_black": "Black Defendants",
        "s3_bar_white": "White Defendants",
        "s3_alert": "The System Was Rigged.",
        "s3_mean_p1": "The AI was <strong>twice as likely</strong> to falsely accuse Black defendants of being dangerous.",
        "s3_mean_p2": "<strong>What Does This Mean?</strong><br>The AI system was systematically biased. It didn't just make random errors—it made different kinds of errors for different groups of people.",
        "btn_eu": "Could it happen here? ▶️",
        
        # Step 4 EU - UPDATED DESCRIPTIONS
        "s4eu_title": "🇪🇺 Closer Than You Think",
        "s4eu_head": "This isn't just a US problem.",
        "s4eu_intro": "Europe is building similar tools right now. Have you heard of these?",
        
        "s4eu_c1_title": "🇬🇧 UK: HART",
        "s4eu_c1_body": "Used by <strong>Durham Police</strong> to predict who will reoffend. It uses variables like age, gender, and <strong>postcode</strong>—socio-economic proxies that can unfairly target people based on where they live.",
        
        "s4eu_c2_title": "🇪🇸 Spain: VioGén",
        "s4eu_c2_body": "A risk tool for gender-violence cases. It operates as a <strong>'Black Box'</strong>, meaning officers rely heavily on its scores for protection decisions without being able to check the algorithm for errors.",
        
        "s4eu_c3_title": "🇳🇱 Netherlands: CAS",
        "s4eu_c3_body": "The <em>Crime Anticipation System</em> uses demographic data to predict crime hotspots. This risks creating <strong>feedback loops</strong> that steer policing toward specific communities again and again.",
        
        "s4eu_note": "<strong>Reality Check:</strong> These systems are being debated in our courts and parliaments <em>today</em>.",
        "btn_back_invest": "◀️ Back",
        "btn_zoom": "The Critical Lesson ▶️",
        
        # Step 4 Lesson
        "s4_title": "💡 The Reality Check",
        "s4_c1_title": "The Accuracy Trap",
        "s4_c1_body": "90% accuracy sounds good. But if the 10% errors all hit one specific group, it's <strong>discrimination</strong>.",
        "s4_c2_title": "The Echo Chamber",
        "s4_c2_body": "AI learns from the past. If history was unfair, the AI will <strong>repeat it</strong>—faster and at scale.",
        "s4_c3_title": "Real Human Cost",
        "s4_c3_body": "A 'False Warning' isn't just a number. It's a person losing their job, their home, or their freedom.",
        "btn_back_eu": "◀️ Back",
        "btn_what_do": "What Can We Do? ▶️",
        
        # Step 5 Path
        "s5_title": "🛤️ The Path Forward",
        "s5_head": "From Accuracy to Ethics",
        "s5_intro": "You've now seen both sides of the AI story:",
        "s5_li1": "✅ You built models that achieved higher accuracy scores",
        "s5_li2": "⚠️ You learned how similar models caused real-world harm",
        "s5_li3": "🤔 You understand that accuracy alone is not enough",
        "s5_box_title": "What You'll Do Next:",
        "s5_p1": "In the next section, you'll be introduced to a <strong class='emph-key'>new way of measuring success</strong>—one that balances performance with fairness and ethics.",
        "s5_p2": "You'll learn techniques to <strong class='emph-key'>detect bias</strong> in your models, <strong class='emph-key'>measure fairness</strong> across different groups, and <strong class='emph-key'>redesign your AI</strong> to minimize harm.",
        "s5_mission": "🎯 Your new mission: Build AI that is not just accurate, but also <strong class='emph-key'>fair, equitable, and ethically sound</strong>.",
        "s5_scroll": "👇 Continue to the next activity below — or click <span style='white-space:nowrap;'>Next (top bar)</span> in expanded view ➡️",
        "s5_continue": "",
        "btn_review": "◀️ Review the Investigation"
    },
    "es": {
        "title": "🚀 La revelación ética: impacto real",
        "loading_personal": "⏳ Cargando tu experiencia personalizada...",
        "stats_title": "🏆 ¡Gran trabajo, ingeniero/a! 🏆",
        "stats_subtitle": "Aquí tienes el resumen de tu rendimiento.",
        "stats_heading": "Tus estadísticas",
        "lbl_accuracy": "Mejor precisión",
        "lbl_rank": "Tu rango",
        "lbl_team": "Equipo",
        "stats_footer": "¿Listo para compartir tu modelo y explorar su impacto en el mundo real?",
        "btn_deploy": "🌍 Compartir tu modelo de IA (simulación)",
        "guest_title": "🚀 ¡Has iniciado sesión!",
        "guest_subtitle": "Aún no has enviado un modelo, pero estás listo para seguir aprendiendo.",
        "guest_body": "Una vez que envíes un modelo en el Juego de Construcción de Modelos, tu precisión y clasificación aparecerán aquí.",
        "guest_footer": "Continúa a la siguiente sección cuando estés listo.",
        "loading_session": "🔒 Cargando tu sesión...",
        
        # Step 2 REVISED (Spanish)
        "s2_title": "🏛️ El paralelo en el mundo real",
        "s2_intro": "Tu modelo funciona igual que un sistema real usado en la justicia de EE. UU.",
        "s2_box_title": "¿Qué es COMPAS?",
        "s2_p1": "<strong>COMPAS</strong> es un sistema de IA diseñado para predecir el <strong>riesgo de reincidencia</strong>.",
        "s2_p2": "Jueces de todo Estados Unidos usaron estas puntuaciones para decidir quién permanecía en la cárcel y quién quedaba libre.",
        "s2_p3": "Pero en 2016, <strong>periodistas de ProPublica</strong> descubrieron un problema grave...",
        "btn_back": "◀️ Atrás",
        "btn_reveal": "Ver lo que encontraron ▶️",
        
        # Step 3 REVISED
        "s3_title": "📰 Informe de Investigación",
        "s3_head": "El Sesgo Oculto",
        "s3_p1": "Los periodistas analizaron <strong>7,000 casos reales</strong>. Compararon las predicciones de la IA vs. la realidad.",
        "s3_chart_title": "TASA DE ERROR: Marcado incorrectamente como 'Alto Riesgo'",
        "s3_bar_black": "Acusados Negros",
        "s3_bar_white": "Acusados Blancos",
        "s3_alert": "El sistema estaba amañado.",
        "s3_mean_p1": "La IA tenía <strong>el doble de probabilidades</strong> de acusar falsamente a los acusados negros.",
        "s3_mean_p2": "<strong>¿Qué significa esto?</strong><br>El sistema de IA estaba sistemáticamente sesgado. No solo cometía errores aleatorios, sino que cometía diferentes tipos de errores para diferentes grupos de personas.",
        "btn_eu": "¿Podría pasar aquí? ▶️",
        
        # Step 4 EU - UPDATED DESCRIPTIONS
        "s4eu_title": "🇪🇺 Más cerca de lo que crees",
        "s4eu_head": "No es solo un problema de EE. UU.",
        "s4eu_intro": "Europa está construyendo herramientas similares ahora mismo. ¿Te suenan?",
        
        "s4eu_c1_title": "🇬🇧 Reino Unido: HART",
        "s4eu_c1_body": "Usado por la <strong>Policía de Durham</strong> para predecir la reincidencia. Utiliza variables como el <strong>código postal</strong>, lo que puede perjudicar injustamente a las personas según dónde vivan.",
        
        "s4eu_c2_title": "🇪🇸 España: VioGén",
        "s4eu_c2_body": "Herramienta para casos de violencia de género. Funciona como una <strong>'Caja Negra'</strong>: la policía confía en sus puntuaciones para decidir medidas de protección sin poder auditar el algoritmo.",
        
        "s4eu_c3_title": "🇳🇱 Países Bajos: CAS",
        "s4eu_c3_body": "El sistema <em>CAS</em> usa datos demográficos para predecir zonas de crimen. Esto crea <strong>bucles de retroalimentación</strong> que dirigen la vigilancia policial hacia comunidades específicas una y otra vez.",
        
        "s4eu_note": "<strong>Realidad:</strong> Estos sistemas se están debatiendo en nuestros tribunales y parlamentos <em>hoy</em>.",
        "btn_back_invest": "◀️ Atrás",
        "btn_zoom": "La Lección Crítica ▶️",
        
        # Step 4 Lesson REVISED
        "s4_title": "💡 La Realidad",
        "s4_c1_title": "La Trampa de la Precisión",
        "s4_c1_body": "90% de precisión suena bien. Pero si el 10% de errores golpea a un solo grupo, es <strong>discriminación</strong>.",
        "s4_c2_title": "La Cámara de Eco",
        "s4_c2_body": "La IA aprende del pasado. Si la historia fue injusta, la IA lo <strong>repetirá</strong>, más rápido y a gran escala.",
        "s4_c3_title": "Coste Humano Real",
        "s4_c3_body": "Una 'Falsa Alarma' no es solo un número. Es una persona perdiendo su trabajo, su hogar o su libertad.",
        "btn_back_eu": "◀️ Atrás",
        "btn_what_do": "¿Qué podemos hacer? ▶️",
        
        # Step 5 Path
        "s5_title": "🛤️ El camino a seguir",
        "s5_head": "De la precisión a la ética",
        "s5_intro": "Ya has visto los dos lados de la IA:",
        "s5_li1": "✅ Has construido modelos con altos niveles de precisión",
        "s5_li2": "⚠️ Has aprendido cómo modelos similares han causado daños reales",
        "s5_li3": "🤔 Entiendes que la precisión por sí sola no es suficiente",
        "s5_box_title": "Lo que harás a continuación:",
        "s5_p1": "En la siguiente sección, se te presentará una <strong class='emph-key'>nueva forma de medir el éxito</strong>, una que equilibra el rendimiento con la equidad y la ética.",
        "s5_p2": "Aprenderás técnicas para <strong class='emph-key'>detectar sesgos</strong> en tus modelos, <strong class='emph-key'>medir la equidad</strong> en diferentes grupos y <strong class='emph-key'>rediseñar tu IA</strong> para minimizar el daño.",
        "s5_mission": "🎯 Tu nueva misión: Construir una IA que no solo sea precisa, sino también <strong class='emph-key'>justa, equitativa y éticamente sólida</strong>.",
        "s5_scroll": "👇 Continúa con la siguiente actividad abajo — o haz clic en <span style='white-space:nowrap;'>Siguiente (barra superior)</span> en vista ampliada ➡️",
        "s5_continue": "",
        "btn_review": "◀️ Revisar la Investigación"
    },
    "ca": {
        "title": "🚀 La revelació ètica: impacte real",
        "loading_personal": "⏳ Carregant la teva experiència personalitzada...",
        "stats_title": "🏆 Bona feina, enginyer/a! 🏆",
        "stats_subtitle": "Aquí tens el teu resum de rendiment.",
        "stats_heading": "Les teves estadístiques",
        "lbl_accuracy": "Millor precisió",
        "lbl_rank": "El teu rang",
        "lbl_team": "Equip",
        "stats_footer": "A punt per compartir el teu model i explorar el seu impacte al món real?",
        "btn_deploy": "🌍 Compartir el teu model d'IA (simulació)",
        "guest_title": "🚀 Has iniciat sessió!",
        "guest_subtitle": "Encara no has enviat un model, però estàs a punt per continuar aprenent.",
        "guest_body": "Un cop enviïs un model al Joc de Construcció de Models, la teva precisió i classificació apareixeran aquí.",
        "guest_footer": "Continua a la següent secció quan estiguis a punt.",
        "loading_session": "🔒 Carregant la teva sessió...",
        
        # Step 2 REVISED (Catalan)
        "s2_title": "🏛️ El paral·lel al món real",
        "s2_intro": "El teu model funciona igual que un sistema real utilitzat en la justícia dels EUA.",
        "s2_box_title": "Què és COMPAS?",
        "s2_p1": "<strong>COMPAS</strong> és un sistema d'IA dissenyat per predir el <strong>risc de reincidència</strong>.",
        "s2_p2": "Jutges de tot els Estats Units utilitzaven aquestes puntuacions per decidir qui es quedava a la presó i qui quedava lliure.",
        "s2_p3": "Però el 2016, <strong>periodistes de ProPublica</strong> van descobrir un problema greu...",
        "btn_back": "◀️ Enrere",
        "btn_reveal": "Veure què van trobar ▶️",
        
        # Step 3 REVISED
        "s3_title": "📰 Informe d'Investigació",
        "s3_head": "El Biaix Ocult",
        "s3_p1": "Els periodistes van analitzar <strong>7.000 casos reals</strong>. Van comparar les prediccions de la IA vs. la realitat.",
        "s3_chart_title": "TAXA D'ERROR: Marcat incorrectament com 'Alt Risc'",
        "s3_bar_black": "Acusats Negres",
        "s3_bar_white": "Acusats Blancos",
        "s3_alert": "El sistema estava manipulat.",
        "s3_mean_p1": "La IA tenia <strong>el doble de probabilitats</strong> d'acusar falsament els acusats negres.",
        "s3_mean_p2": "<strong>Què significa això?</strong><br>El sistema d'IA estava sistemàticament esbiaixat. No només cometia errors aleatoris, sinó que cometia diferents tipus d'errors per a diferents grups de persones.",
        "btn_eu": "Podria passar aquí? ▶️",
        
        # Step 4 EU - UPDATED DESCRIPTIONS
        "s4eu_title": "🇪🇺 Més a prop del que creus",
        "s4eu_head": "No és només un problema dels EUA.",
        "s4eu_intro": "Europa està construint eines similars ara mateix. Et sonen?",
        
        "s4eu_c1_title": "🇬🇧 Regne Unit: HART",
        "s4eu_c1_body": "Utilitzat per la <strong>Policia de Durham</strong> per predir la reincidència. Fa servir variables com el <strong>codi postal</strong>, cosa que pot perjudicar injustament les persones segons on visquin.",
        
        "s4eu_c2_title": "🇪🇸 Espanya: VioGén",
        "s4eu_c2_body": "Eina per a casos de violència de gènere. Funciona com una <strong>'Caixa Negra'</strong>: la policia confia en les seves puntuacions per decidir la protecció sense poder auditar l'algoritme.",
        
        "s4eu_c3_title": "🇳🇱 Països Baixos: CAS",
        "s4eu_c3_body": "El sistema <em>CAS</em> utilitza dades demogràfiques per predir zones de risc. Això crea <strong>bucles de retroalimentació</strong> que dirigeixen la vigilància policial cap a comunitats específiques una vegada i una altra.",
        
        "s4eu_note": "<strong>Realitat:</strong> Aquests sistemes s'estan debatent als nostres tribunals i parlaments <em>avui</em>.",
        "btn_back_invest": "◀️ Enrere",
        "btn_zoom": "La Lliçó Crítica ▶️",
        
        # Step 4 Lesson REVISED
        "s4_title": "💡 La Realitat",
        "s4_c1_title": "La Trampa de la Precisió",
        "s4_c1_body": "90% de precisió sona bé. Però si el 10% d'errors colpeja un sol grup, és <strong>discriminació</strong>.",
        "s4_c2_title": "La Cambra d'Eco",
        "s4_c2_body": "La IA aprèn del passat. Si la història va ser injusta, la IA ho <strong>repetirà</strong>, més ràpid i a gran escala.",
        "s4_c3_title": "Cost Humà Real",
        "s4_c3_body": "Una 'Falsa Alarma' no és només un número. És una persona perdent la seva feina, la seva llar o la seva llibertat.",
        "btn_back_eu": "◀️ Enrere",
        "btn_what_do": "Què podem fer? ▶️",
        
        # Step 5 Path
        "s5_title": "🛤️ El camí a seguir",
        "s5_head": "De la precisió a l'ètica",
        "s5_intro": "Ara ja has vist els dos costats de la IA:",
        "s5_li1": "✅ Has construït models amb alts nivells de precisió",
        "s5_li2": "⚠️ Has après com models similars han causat danys reals",
        "s5_li3": "🤔 Entens que la precisió per si sola no és suficient",
        "s5_box_title": "Què faràs a continuació:",
        "s5_p1": "En la següent secció, se't presentarà una <strong class='emph-key'>nova manera de mesurar l'èxit</strong>, una que equilibra el rendiment amb l'equitat i l'ètica.",
        "s5_p2": "Aprendràs tècniques per <strong class='emph-key'>detectar biaixos</strong> en els teus models, <strong class='emph-key'>mesurar l'equitat</strong> en diferents grups i <strong class='emph-key'>redissenyar la teva IA</strong> per minimitzar el dany.",
        "s5_mission": "🎯 La teva nova missió: Construir una IA que no només sigui precisa, sinó també <strong class='emph-key'>justa, equitativa i èticament sòlida</strong>.",
        "s5_scroll": "👇 Continua amb la següent activitat a sota — o fes clic a <span style='white-space:nowrap;'>Següent (barra superior)</span> en vista ampliada ➡️",
        "s5_continue": "",
        "btn_review": "◀️ Revisar la Investigació"
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

def translate_team_name_for_display(team_en: str, lang: str = "en") -> str:
    if lang not in TEAM_NAME_TRANSLATIONS:
        lang = "en"
    return TEAM_NAME_TRANSLATIONS[lang].get(team_en, team_en)

def translate_team_name_to_english(display_name: str, lang: str = "en") -> str:
    if lang not in TEAM_NAME_TRANSLATIONS:
        return display_name
    translations = TEAM_NAME_TRANSLATIONS[lang]
    for english_name, localized_name in translations.items():
        if localized_name == display_name:
            return english_name
    return display_name

def _format_leaderboard_for_display(df: Optional[pd.DataFrame], lang: str = "en") -> Optional[pd.DataFrame]:
    if df is None: return None
    if df.empty or "Team" not in df.columns: return df.copy()
    df_display = df.copy()
    df_display["Team"] = df_display["Team"].apply(lambda t: translate_team_name_for_display(t, lang))
    return df_display

def _fetch_leaderboard(token: str) -> Optional[pd.DataFrame]:
    now = time.time()
    with _cache_lock:
        if (_leaderboard_cache["data"] is not None and now - _leaderboard_cache["timestamp"] < LEADERBOARD_CACHE_SECONDS):
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
                        user_submissions["timestamp"] = pd.to_datetime(user_submissions["timestamp"], errors="coerce")
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
        if not session_id: return False, None, None
        token = get_token_from_session(session_id)
        if not token: return False, None, None
        username = _get_username_from_token(token)
        if not username: return False, None, None
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
                user_bests = leaderboard_df.groupby("username")["accuracy"].max()
                summary_df = user_bests.reset_index()
                summary_df.columns = ["Engineer", "Best_Score"]
                summary_df = summary_df.sort_values("Best_Score", ascending=False).reset_index(drop=True)
                summary_df.index = summary_df.index + 1
                my_row = summary_df[summary_df["Engineer"] == username]
                if not my_row.empty:
                    rank = my_row.index[0]
                if "Team" in leaderboard_df.columns and team_name:
                    team_summary_df = (leaderboard_df.groupby("Team")["accuracy"].agg(Best_Score="max").reset_index().sort_values("Best_Score", ascending=False).reset_index(drop=True))
                    team_summary_df.index = team_summary_df.index + 1
                    my_team_row = team_summary_df[team_summary_df["Team"] == team_name]
                    if not my_team_row.empty:
                        team_rank = my_team_row.index[0]
    except Exception as e:
        _log(f"User stats error for {username}: {e}")

    stats = { "username": username, "best_score": best_score, "rank": rank, "team_name": team_name, "team_rank": team_rank, "is_signed_in": True, "_ts": now }
    _user_stats_cache[username] = stats
    return stats

# ---------------------------------------------------------------------------
# HTML Helpers (I18N)
# ---------------------------------------------------------------------------

def t(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

def build_stats_html(user_stats: Dict[str, Any], lang="en") -> str:
    if user_stats.get("best_score") is not None:
        best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
        rank_text = f"#{user_stats['rank']}" if user_stats['rank'] else "N/A"
        team_text = translate_team_name_for_display(user_stats['team_name'], lang) if user_stats['team_name'] else "N/A"
        return f"""
        <div class='slide-shell slide-shell--primary'>
            <div style='text-align:center;'>
                <h2 class='slide-shell__title'>{t(lang, 'stats_title')}</h2>
                <p class='slide-shell__subtitle'>{t(lang, 'stats_subtitle')}</p>
                <div class='content-box'>
                    <h3 class='content-box__heading'>{t(lang, 'stats_heading')}</h3>
                    <div class='stat-grid'>
                        <div class='stat-card'>
                            <p class='stat-card__label'>{t(lang, 'lbl_accuracy')}</p>
                            <p class='stat-card__value'>{best_score_pct}</p>
                        </div>
                        <div class='stat-card'>
                            <p class='stat-card__label'>{t(lang, 'lbl_rank')}</p>
                            <p class='stat-card__value'>{rank_text}</p>
                        </div>
                    </div>
                    <div class='team-card'>
                        <p class='team-card__label'>{t(lang, 'lbl_team')}</p>
                        <p class='team-card__value'>🛡️ {team_text}</p>
                    </div>
                </div>
                <p class='slide-shell__subtitle' style='font-weight:500;'>{t(lang, 'stats_footer')}</p>
            </div>
        </div>
        """
    else:
        return f"""
        <div class='slide-shell slide-shell--primary'>
            <div style='text-align:center;'>
                <h2 class='slide-shell__title'>{t(lang, 'guest_title')}</h2>
                <p class='slide-shell__subtitle'>{t(lang, 'guest_subtitle')}</p>
                <div class='content-box'><p style='margin:0;'>{t(lang, 'guest_body')}</p></div>
                <p class='slide-shell__subtitle' style='font-weight:500;'>{t(lang, 'guest_footer')}</p>
            </div>
        </div>
        """

# --- REVISED HTML GENERATORS ---

def _get_step2_html(lang):
    # Updated to remove "Confidential Case File" and use standard layout
    return f"""
    <div class='slide-shell slide-shell--primary'>
        <div style='text-align:center; margin-bottom:20px;'>
            <p class='large-text' style='font-weight:600; margin:0;'>{t(lang, 's2_intro')}</p>
        </div>
        <div class='content-box'>
            <h3 class='content-box__heading' style='font-size:1.5rem;'>{t(lang, 's2_box_title')}</h3>
            <p class='slide-warning-body'>{t(lang, 's2_p1')}</p>
            <p class='slide-warning-body' style='margin-top:16px;'>{t(lang, 's2_p2')}</p>
        </div>
        <p class='slide-warning-body' style='margin-top:20px; font-weight:700; text-align:center; font-size:1.3rem; color: #dc2626;'>
            {t(lang, 's2_p3')}
        </p>
    </div>
    """

def _get_step3_html(lang):
    return f"""
    <div class='revelation-box' style='border-left:none; padding:0;'>
        <div style='text-align:center; margin-bottom:30px;'>
            <h3 style='margin:0; font-size:2rem; font-weight:800;'>{t(lang, 's3_head')}</h3>
            <p style='font-size:1.2rem; margin-top:10px;'>{t(lang, 's3_p1')}</p>
        </div>
        
        <div class='content-box content-box--emphasis' style='border-left:none; border-top:6px solid var(--color-accent);'>
            <h4 class='content-box__heading' style='text-align:center; margin-bottom:25px;'>{t(lang, 's3_chart_title')}</h4>
            
            <div style='margin-bottom:25px;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:5px; font-weight:bold; color:#b91c1c;'>
                    <span>{t(lang, 's3_bar_black')}</span>
                    <span>45%</span>
                </div>
                <div style='background:#fee2e2; border-radius:10px; height:30px; width:100%;'>
                    <div style='background:#dc2626; width:45%; height:100%; border-radius:10px;'></div>
                </div>
            </div>

            <div style='margin-bottom:30px;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:5px; font-weight:bold; color:#1e293b;'>
                    <span>{t(lang, 's3_bar_white')}</span>
                    <span>24%</span>
                </div>
                <div style='background:#f1f5f9; border-radius:10px; height:30px; width:100%;'>
                    <div style='background:#64748b; width:24%; height:100%; border-radius:10px;'></div>
                </div>
            </div>

            <div class='bg-danger-soft' style='text-align:center;'>
                <h3 class='emph-danger' style='margin:0; font-size:1.4rem;'>{t(lang, 's3_alert')}</h3>
                <p style='margin:10px 0 0 0; font-size:1.1rem;'>{t(lang, 's3_mean_p1')}</p>
                <p style='margin:10px 0 0 0; font-size:1.1rem;'>{t(lang, 's3_mean_p2')}</p>
            </div>
        </div>
    </div>
    """

def _get_step4_eu_html(lang):
    return f"""
    <div class='eu-panel' style='background:transparent; border:none; padding:0;'>
        <div style='text-align:center; margin-bottom:30px;'>
            <h3 class='emph-eu' style='font-size:2.2rem;'>{t(lang, 's4eu_head')}</h3>
            <p style='font-size:1.2rem;'>{t(lang, 's4eu_intro')}</p>
        </div>
        
        <div class='grid-3-col'>
            <div class='stat-card' style='text-align:left; border-top:4px solid #2563eb;'>
                <h4 style='margin:0 0 10px 0; font-size:1.2rem;'>{t(lang, 's4eu_c1_title')}</h4>
                <p style='font-size:1rem; margin:0;'>{t(lang, 's4eu_c1_body')}</p>
            </div>
            <div class='stat-card' style='text-align:left; border-top:4px solid #db2777;'>
                <h4 style='margin:0 0 10px 0; font-size:1.2rem;'>{t(lang, 's4eu_c2_title')}</h4>
                <p style='font-size:1rem; margin:0;'>{t(lang, 's4eu_c2_body')}</p>
            </div>
            <div class='stat-card' style='text-align:left; border-top:4px solid #ea580c;'>
                <h4 style='margin:0 0 10px 0; font-size:1.2rem;'>{t(lang, 's4eu_c3_title')}</h4>
                <p style='font-size:1rem; margin:0;'>{t(lang, 's4eu_c3_body')}</p>
            </div>
        </div>

        <div class='eu-panel__note' style='background:#f0f9ff; padding:20px; border-radius:12px; border-left:5px solid #0ea5e9; margin-top:30px;'>
            <p style='margin:0; font-size:1.1rem;'>{t(lang, 's4eu_note')}</p>
        </div>
    </div>
    """

def _get_step4_lesson_html(lang):
    return f"""
    <div style='max-width:900px; margin:auto;'>
        <h2 style='text-align:center; font-size:2.2rem; margin-bottom:30px;'>{t(lang, 's4_title')}</h2>
        
        <div class='grid-3-col'>
            <div class='lesson-emphasis-box' style='margin-top:0; border-left:none; border-top:6px solid #8b5cf6;'>
                <span class='lesson-item-title' style='color:#7c3aed;'>1. {t(lang, 's4_c1_title')}</span>
                <p style='margin-top:10px; font-size:1rem; line-height:1.5;'>{t(lang, 's4_c1_body')}</p>
            </div>
            <div class='lesson-emphasis-box' style='margin-top:0; border-left:none; border-top:6px solid #ec4899;'>
                <span class='lesson-item-title' style='color:#db2777;'>2. {t(lang, 's4_c2_title')}</span>
                <p style='margin-top:10px; font-size:1rem; line-height:1.5;'>{t(lang, 's4_c2_body')}</p>
            </div>
            <div class='lesson-emphasis-box' style='margin-top:0; border-left:none; border-top:6px solid #ef4444;'>
                <span class='lesson-item-title' style='color:#dc2626;'>3. {t(lang, 's4_c3_title')}</span>
                <p style='margin-top:10px; font-size:1rem; line-height:1.5;'>{t(lang, 's4_c3_body')}</p>
            </div>
        </div>
    </div>
    """

def _get_step5_html(lang):
    return f"""
    <div style='text-align:center;'>
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>{t(lang, 's5_head')}</h3>
            <p style='line-height:1.8; text-align:left;'>{t(lang, 's5_intro')}</p>
            <ul style='text-align:left; line-height:2; font-size:1.1rem; margin:24px 0;'>
                <li>{t(lang, 's5_li1')}</li>
                <li>{t(lang, 's5_li2')}</li>
                <li>{t(lang, 's5_li3')}</li>
            </ul>
            <div class='content-box'>
                <h4 class='content-box__heading'>{t(lang, 's5_box_title')}</h4>
                <p style='font-size:1.1rem; line-height:1.8;'>{t(lang, 's5_p1')}</p>
                <p style='font-size:1.1rem; line-height:1.8; margin-top:16px;'>{t(lang, 's5_p2')}</p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p style='font-size:1.15rem; font-weight:600; margin:0;'>{t(lang, 's5_mission')}</p>
            </div>
            <h1 class='final-instruction' style='margin:32px 0 16px 0;'>{t(lang, 's5_scroll')}</h1>
            <p style='font-size:1.2rem;'>{t(lang, 's5_continue')}</p>
        </div>
    </div>
    """

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = """
.large-text { font-size: 20px !important; }
.slide-shell, .celebration-box {
  padding:24px; border-radius:16px;
  background-color: var(--block-background-fill);
  color: var(--body-text-color);
  border:2px solid var(--border-color-primary);
  max-width:900px; margin:auto;
}
.slide-shell--primary, .slide-shell--warning, .slide-shell--info { border-color: var(--color-accent); }
.slide-shell__title { font-size:2.3rem; margin:0; text-align:center; }
.slide-shell__subtitle { font-size:1.2rem; margin-top:16px; text-align:center; color: var(--secondary-text-color); }
.stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; }
.stat-card, .team-card { text-align:center; padding:16px; border-radius:8px; border:1px solid var(--border-color-primary); background-color: var(--block-background-fill); }
.stat-card__label, .team-card__label { margin:0; font-size:0.9rem; color: var(--secondary-text-color); }
.stat-card__value { margin:4px 0 0 0; font-size:1.8rem; font-weight:700; }
.team-card__value { margin:4px 0 0 0; font-size:1.3rem; font-weight:600; }
.content-box { background-color: var(--block-background-fill); border-radius:12px; border:1px solid var(--border-color-primary); padding:24px; margin:24px 0; }
.content-box--emphasis { border-left:6px solid var(--color-accent); }
.revelation-box { background-color: var(--block-background-fill); border-left:6px solid var(--color-accent); border-radius:8px; padding:24px; margin-top:24px; }
.eu-panel { font-size:20px; padding:32px; border-radius:16px; border:3px solid var(--border-color-primary); background-color: var(--block-background-fill); max-width:900px; margin:auto; }
.bg-danger-soft { background-color:#fee2e2; border-left:6px solid #dc2626; padding:16px; border-radius:8px; }
.emph-danger { color:#b91c1c; font-weight:700; }
.emph-key { color: var(--color-accent); font-weight:700; }
.lesson-emphasis-box { background-color: var(--block-background-fill); border-left:6px solid var(--color-accent); padding:18px 20px; border-radius:10px; margin-top:1.5rem; }
.lesson-item-title { font-size:1.35em; font-weight:700; margin-bottom:0.25rem; display:block; }
.lesson-badge { display:inline-block; background-color: var(--color-accent); color: var(--button-text-color); padding:6px 12px; border-radius:10px; font-weight:700; margin-right:10px; font-size:0.9em; }
.slide-warning-body, .slide-teaching-body { font-size:1.25em; line-height:1.75; }
#nav-loading-overlay { position:fixed; top:0; left:0; width:100%; height:100%; background-color: var(--body-background-fill); z-index:9999; display:none; flex-direction:column; align-items:center; justify-content:center; opacity:0; transition:opacity .3s ease; }
.nav-spinner { width:50px; height:50px; border:5px solid var(--block-background-fill); border-top:5px solid var(--color-accent); border-radius:50%; animation: nav-spin 1s linear infinite; margin-bottom:20px; }
@keyframes nav-spin { 0%{transform:rotate(0deg);} 100%{transform:rotate(360deg);} }
.bg-eu-soft { background-color: color-mix(in srgb, var(--color-accent) 15%, transparent); border-radius: 8px; padding: 16px; margin: 20px 0; }
.emph-eu { color: var(--color-accent); font-weight: 700; }
.emph-harm { color: #b91c1c; font-weight: 700; }
.final-instruction {
  font-size: clamp(1.5rem, 2vw + 0.6rem, 2rem);
  line-height: 1.25;
  margin: 16px 0;
}
/* New CSS for Cards */
.grid-3-col {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}
@media (max-width: 768px) {
    .grid-3-col {
        grid-template-columns: 1fr;
    }
}
@media (prefers-color-scheme: dark) {
    .bg-danger-soft { background-color: #450a0a; border-color: #dc2626; }
    .emph-danger { color: #f87171; }
    .emph-harm { color: #f87171; }
}
"""

def create_ethical_revelation_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=CSS) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)
        
        c_title = gr.Markdown("<h1 style='text-align:center;'>🚀 The Ethical Revelation: Real-World Impact</h1>")

        with gr.Column(visible=True, elem_id="initial-loading") as initial_loading:
            c_loading_text = gr.Markdown("<div style='text-align:center; padding:80px 0;'><h2>⏳ Loading...</h2></div>")

        with gr.Column(visible=False, elem_id="step-1") as step_1:
            stats_display = gr.HTML()
            deploy_button = gr.Button(t('en', 'btn_deploy'), variant="primary", size="lg", scale=1)

        with gr.Column(visible=False, elem_id="step-2") as step_2:
            c_s2_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's2_title')}</h2>")
            c_s2_html = gr.HTML(_get_step2_html("en"))
            with gr.Row():
                step_2_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_2_next = gr.Button(t('en', 'btn_reveal'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-3") as step_3:
            c_s3_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's3_title')}</h2>")
            c_s3_html = gr.HTML(_get_step3_html("en"))
            with gr.Row():
                step_3_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_3_next = gr.Button(t('en', 'btn_eu'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-4-eu") as step_4_eu:
            c_s4eu_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's4eu_title')}</h2>")
            c_s4eu_html = gr.HTML(_get_step4_eu_html("en"))
            with gr.Row():
                step_4_eu_back = gr.Button(t('en', 'btn_back_invest'), size="lg")
                step_4_eu_next = gr.Button(t('en', 'btn_zoom'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-4") as step_4:
            c_s4_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's4_title')}</h2>")
            c_s4_html = gr.HTML(_get_step4_lesson_html("en"))
            with gr.Row():
                step_4_back = gr.Button(t('en', 'btn_back_eu'), size="lg")
                step_4_next = gr.Button(t('en', 'btn_what_do'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-5") as step_5:
            c_s5_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's5_title')}</h2>")
            c_s5_html = gr.HTML(_get_step5_html("en"))
            back_to_lesson_btn = gr.Button(t('en', 'btn_review'), size="lg")

        loading_screen = gr.Column(visible=False)
        all_steps = [step_1, step_2, step_3, step_4_eu, step_4, step_5, loading_screen, initial_loading]

        update_targets = [
            initial_loading, step_1, stats_display, c_title, c_loading_text,
            deploy_button,
            c_s2_title, c_s2_html, step_2_back, step_2_next,
            c_s3_title, c_s3_html, step_3_back, step_3_next,
            c_s4eu_title, c_s4eu_html, step_4_eu_back, step_4_eu_next,
            c_s4_title, c_s4_html, step_4_back, step_4_next,
            c_s5_title, c_s5_html, back_to_lesson_btn
        ]

        @lru_cache(maxsize=16)
        def get_cached_static_content(lang):
            return [
                gr.Button(value=t(lang, 'btn_deploy')),
                f"<h2 style='text-align:center;'>{t(lang, 's2_title')}</h2>", _get_step2_html(lang), gr.Button(value=t(lang, 'btn_back')), gr.Button(value=t(lang, 'btn_reveal')),
                f"<h2 style='text-align:center;'>{t(lang, 's3_title')}</h2>", _get_step3_html(lang), gr.Button(value=t(lang, 'btn_back')), gr.Button(value=t(lang, 'btn_eu')),
                f"<h2 style='text-align:center;'>{t(lang, 's4eu_title')}</h2>", _get_step4_eu_html(lang), gr.Button(value=t(lang, 'btn_back_invest')), gr.Button(value=t(lang, 'btn_zoom')),
                f"<h2 style='text-align:center;'>{t(lang, 's4_title')}</h2>", _get_step4_lesson_html(lang), gr.Button(value=t(lang, 'btn_back_eu')), gr.Button(value=t(lang, 'btn_what_do')),
                f"<h2 style='text-align:center;'>{t(lang, 's5_title')}</h2>", _get_step5_html(lang), gr.Button(value=t(lang, 'btn_review'))
            ]

        def initial_load(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS: lang = "en"
            success, username, token = _try_session_based_auth(request)
            stats_html = ""
            if success and username:
                stats = _compute_user_stats(username, token)
                stats_html = build_stats_html(stats, lang)
            else:
                stats_html = f"<div class='slide-shell slide-shell--primary' style='text-align:center;'><h2 class='slide-shell__title'>{t(lang, 'loading_session')}</h2></div>"
            static_updates = get_cached_static_content(lang)
            return [gr.update(visible=False), gr.update(visible=True), gr.update(value=stats_html), f"<h1 style='text-align:center;'>{t(lang, 'title')}</h1>", f"<div style='text-align:center; padding:80px 0;'><h2>{t(lang, 'loading_personal')}</h2></div>"] + static_updates

        demo.load(fn=initial_load, inputs=None, outputs=update_targets)

        def create_nav_generator(current_step, next_step):
            def navigate():
                updates = {loading_screen: gr.update(visible=True)}
                for s in all_steps:
                    if s != loading_screen: updates[s] = gr.update(visible=False)
                yield updates
                updates = {next_step: gr.update(visible=True)}
                for s in all_steps:
                    if s != next_step: updates[s] = gr.update(visible=False)
                yield updates
            return navigate

        def nav_js(target_id: str, message: str, min_show_ms: int = 900) -> str:
            return f"()=>{{ try {{ const overlay=document.getElementById('nav-loading-overlay'); const msg=document.getElementById('nav-loading-text'); if(overlay && msg){{ msg.textContent='{message}'; overlay.style.display='flex'; setTimeout(()=>overlay.style.opacity='1',10); }} const start=Date.now(); setTimeout(()=>{{ window.scrollTo({{top:0, behavior:'smooth'}}); }},40); const poll=setInterval(()=>{{ const elapsed=Date.now()-start; const target=document.getElementById('{target_id}'); const visible=target && target.offsetParent!==null; if((visible && elapsed>={min_show_ms}) || elapsed>6000){{ clearInterval(poll); if(overlay){{ overlay.style.opacity='0'; setTimeout(()=>overlay.style.display='none',320); }} }} }},100); }} catch(e){{}} }}"

        deploy_button.click(fn=create_nav_generator(step_1, step_2), inputs=None, outputs=all_steps, js=nav_js("step-2", "Sharing model..."))
        step_2_back.click(fn=create_nav_generator(step_2, step_1), inputs=None, outputs=all_steps, js=nav_js("step-1", "Returning..."))
        step_2_next.click(fn=create_nav_generator(step_2, step_3), inputs=None, outputs=all_steps, js=nav_js("step-3", "Loading investigation..."))
        step_3_back.click(fn=create_nav_generator(step_3, step_2), inputs=None, outputs=all_steps, js=nav_js("step-2", "Going back..."))
        step_3_next.click(fn=create_nav_generator(step_3, step_4_eu), inputs=None, outputs=all_steps, js=nav_js("step-4-eu", "Exploring European context..."))
        step_4_eu_back.click(fn=create_nav_generator(step_4_eu, step_3), inputs=None, outputs=all_steps, js=nav_js("step-3", "Reviewing findings..."))
        step_4_eu_next.click(fn=create_nav_generator(step_4_eu, step_4), inputs=None, outputs=all_steps, js=nav_js("step-4", "Zooming out..."))
        step_4_back.click(fn=create_nav_generator(step_4, step_4_eu), inputs=None, outputs=all_steps, js=nav_js("step-4-eu", "European context..."))
        step_4_next.click(fn=create_nav_generator(step_4, step_5), inputs=None, outputs=all_steps, js=nav_js("step-5", "Exploring solutions..."))
        back_to_lesson_btn.click(fn=create_nav_generator(step_5, step_4), inputs=None, outputs=all_steps, js=nav_js("step-4", "Reviewing lesson..."))

    return demo

def launch_ethical_revelation_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_ethical_revelation_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)


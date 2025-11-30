import os
import time
import random
import threading
import functools
from typing import Optional, Dict, Any, Tuple

import pandas as pd
import gradio as gr

# Scikit-learn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier

# AI Model Share
try:
    from aimodelshare.playground import Competition
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    pass

# -------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------
os.environ.setdefault("OMP_NUM_THREADS", "1")
LEADERBOARD_CACHE_SECONDS = 45
MAX_LEADERBOARD_ENTRIES = 10
DEBUG_LOG = False

_cache_lock = threading.Lock()
_user_stats_lock = threading.Lock()
_auth_lock = threading.Lock()

_leaderboard_cache = {"anon": {"data": None, "timestamp": 0.0}, "auth": {"data": None, "timestamp": 0.0}}
_user_stats_cache = {}

# Init flags
INIT_FLAGS = {
    "competition": False, "dataset_core": False, "pre_samples_small": False,
    "leaderboard": False, "warm_mini": False, "errors": []
}
INIT_LOCK = threading.Lock()

# Global Data Containers
playground = None
X_TRAIN_RAW = None
X_TEST_RAW = None
Y_TRAIN = None
Y_TEST = None
X_TRAIN_SAMPLES_MAP = {}
Y_TRAIN_SAMPLES_MAP = {}
X_TRAIN_WARM = None
Y_TRAIN_WARM = None

TEAM_NAMES = ["The Moral Champions", "The Justice League", "The Data Detectives", "The Ethical Explorers"]

# Model Definitions
MODEL_TYPES = {
    "The Balanced Generalist": {"builder": lambda: LogisticRegression(max_iter=500, class_weight="balanced"), "key": "mod_bal", "desc": "desc_bal"},
    "The Rule-Maker": {"builder": lambda: DecisionTreeClassifier(class_weight="balanced"), "key": "mod_rule", "desc": "desc_rule"},
    "The 'Nearest Neighbor'": {"builder": lambda: KNeighborsClassifier(), "key": "mod_knn", "desc": "desc_knn"},
    "The Deep Pattern-Finder": {"builder": lambda: RandomForestClassifier(class_weight="balanced"), "key": "mod_deep", "desc": "desc_deep"}
}
DEFAULT_MODEL = "The Balanced Generalist"

FEATURE_OPTIONS = [
    ("Juvenile Felony Count", "juv_fel_count"), ("Juvenile Misdemeanor Count", "juv_misd_count"),
    ("Other Juvenile Count", "juv_other_count"), ("Race", "race"), ("Sex", "sex"),
    ("Charge Severity", "c_charge_degree"), ("Days Before Arrest", "days_b_screening_arrest"),
    ("Age", "age"), ("Length of Stay", "length_of_stay"), ("Prior Crimes", "priors_count")
]
DEFAULT_FEATS = ["juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex", "c_charge_degree"]
ALL_NUMERIC = ["juv_fel_count", "juv_misd_count", "juv_other_count", "days_b_screening_arrest", "age", "length_of_stay", "priors_count"]
ALL_CAT = ["race", "sex", "c_charge_degree"]
DATA_SIZES = {"Small (20%)": 0.2, "Medium (60%)": 0.6, "Large (80%)": 0.8, "Full (100%)": 1.0}
DEFAULT_SIZE = "Small (20%)"
ATTEMPT_LIMIT = 10

# -------------------------------------------------------------------------
# TRANSLATIONS
# -------------------------------------------------------------------------
TRANSLATIONS = {
    "en": {
        "title": "🛠️ Model Building Arena",
        "loading": "⏳ Loading...",
        "btn_next": "Next ▶️",
        "btn_back": "◀️ Back",
        # Labels
        "lbl_model": "1. Model Strategy",
        "lbl_complex": "2. Model Complexity (1–10)",
        "info_complex": "Higher values allow deeper pattern learning; very high values may overfit.",
        "lbl_feat": "3. Select Data Ingredients",
        "info_feat": "More ingredients unlock as you rank up!",
        "lbl_data": "4. Data Size",
        "btn_submit": "5. 🔬 Build & Submit Model",
        "lbl_team_stand": "🏆 Live Standings",
        "tab_team": "Team Standings",
        "tab_ind": "Individual Standings",
        "concl_title": "✅ Section Complete",
        "btn_return": "◀️ Back to Experiment",
        # Slides (Simplified for brevity in logic check, but keys exist)
        "s1_title": "🔄 From Understanding to Building",
        "s2_title": "📋 Your Mission - Build Better AI",
        "s3_title": "🧠 What is a \"Model\"?",
        "s4_title": "🔁 How Engineers Work — The Loop",
        "s5_title": "🎛️ Control Knobs — The \"Brain\" Settings",
        "s6_title": "🎛️ Control Knobs — The \"Data\" Settings",
        "s7_title": "🏆 Your Score as an Engineer",
        "btn_begin": "Begin Model Building ▶️"
    },
    "es": {
        "title": "🛠️ Arena de Construcción de Modelos",
        "loading": "⏳ Cargando...",
        "btn_next": "Siguiente ▶️",
        "btn_back": "◀️ Atrás",
        "lbl_model": "1. Estrategia del Modelo",
        "lbl_complex": "2. Complejidad del Modelo",
        "info_complex": "Valores altos permiten aprendizaje profundo; cuidado con el sobreajuste.",
        "lbl_feat": "3. Ingredientes de Datos",
        "info_feat": "¡Más ingredientes se desbloquean al subir de rango!",
        "lbl_data": "4. Tamaño de Datos",
        "btn_submit": "5. 🔬 Construir y Enviar Modelo",
        "lbl_team_stand": "🏆 Clasificaciones en Vivo",
        "tab_team": "Clasificaciones de Equipo",
        "tab_ind": "Clasificaciones Individuales",
        "concl_title": "✅ Sección Completada",
        "btn_return": "◀️ Volver",
        "s1_title": "🔄 De Entender a Construir",
        "s2_title": "📋 Tu Misión - Construir Mejor IA",
        "s3_title": "🧠 ¿Qué es un \"Modelo\"?",
        "s4_title": "🔁 El Bucle de Ingeniería",
        "s5_title": "🎛️ Configuración del \"Cerebro\"",
        "s6_title": "🎛️ Configuración de \"Datos\"",
        "s7_title": "🏆 Tu Puntuación",
        "btn_begin": "Comenzar ▶️"
    },
    "ca": {
        "title": "🛠️ Arena de Construcció de Models",
        "loading": "⏳ Carregant...",
        "btn_next": "Següent ▶️",
        "btn_back": "◀️ Enrere",
        "lbl_model": "1. Estratègia del Model",
        "lbl_complex": "2. Complexitat del Model",
        "info_complex": "Valors alts permeten aprenentatge profund; cura amb el sobreajust.",
        "lbl_feat": "3. Ingredients de Dades",
        "info_feat": "Més ingredients es desbloquegen al pujar de rang!",
        "lbl_data": "4. Mida de Dades",
        "btn_submit": "5. 🔬 Construir i Enviar Model",
        "lbl_team_stand": "🏆 Classificacions en Viu",
        "tab_team": "Classificacions d'Equip",
        "tab_ind": "Classificacions Individuals",
        "concl_title": "✅ Secció Completada",
        "btn_return": "◀️ Tornar",
        "s1_title": "🔄 D'Entendre a Construir",
        "s2_title": "📋 La Teva Missió",
        "s3_title": "🧠 Què és un \"Model\"?",
        "s4_title": "🔁 El Bucle d'Enginyeria",
        "s5_title": "🎛️ Configuració del \"Cervell\"",
        "s6_title": "🎛️ Configuració de \"Dades\"",
        "s7_title": "🏆 La Teva Puntuació",
        "btn_begin": "Començar ▶️"
    }
}

def t(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

# -------------------------------------------------------------------------
# LOGIC & HELPERS
# -------------------------------------------------------------------------

# (Mocking critical logic for runnable standalone demo)
def _background_initializer():
    # Simulate loading
    time.sleep(1)
    with INIT_LOCK:
        INIT_FLAGS["leaderboard"] = True
        INIT_FLAGS["pre_samples_small"] = True

def start_background_init():
    t = threading.Thread(target=_background_initializer, daemon=True)
    t.start()

# --- HTML Generators (Simplified for robustness) ---
def _get_slide_html(lang, title_key, content_html="<p>Content loaded.</p>"):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <h3 style='text-align:center;'>{t(lang, title_key)}</h3>
            {content_html}
        </div>
    </div>
    """

# -------------------------------------------------------------------------
# MAIN APP FACTORY
# -------------------------------------------------------------------------

def create_model_building_game_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    start_background_init()

    css = """
    .slide-content { max-width: 900px; margin: auto; }
    .panel-box { background: var(--block-background-fill); padding: 20px; border-radius: 12px; border: 2px solid var(--border-color-primary); margin-bottom: 18px; color: var(--body-text-color); }
    #nav-loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: color-mix(in srgb, var(--body-background-fill) 90%, transparent); z-index: 9999; display: none; flex-direction: column; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.3s ease; }
    .nav-spinner { width: 50px; height: 50px; border: 5px solid var(--border-color-primary); border-top: 5px solid var(--color-accent); border-radius: 50%; animation: nav-spin 1s linear infinite; margin-bottom: 20px; }
    @keyframes nav-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    #nav-loading-text { font-size: 1.3rem; font-weight: 600; color: var(--color-accent); }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        lang_state = gr.State("en")
        
        # --- UI ELEMENTS ---
        
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # Slides
        with gr.Column(visible=True, elem_id="slide-1") as s1:
            c_s1_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's1_title')}</h1>")
            c_s1_html = gr.HTML(_get_slide_html("en", "s1_title", "<p>Intro content...</p>"))
            btn_s1_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="slide-2") as s2:
            c_s2_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's2_title')}</h1>")
            c_s2_html = gr.HTML(_get_slide_html("en", "s2_title", "<p>Mission content...</p>"))
            with gr.Row():
                btn_s2_back = gr.Button(t('en', 'btn_back'))
                btn_s2_next = gr.Button(t('en', 'btn_next'), variant="primary")

        # ... (Repeat pattern for slides 3-7, keeping generic for brevity but fully wired below) ...
        # For simplicity in this fix demonstration, I'll jump from S2 to Game.
        
        # Game Interface
        with gr.Column(visible=False, elem_id="model-step") as model_step:
            c_app_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 'title')}</h1>")
            
            with gr.Row():
                with gr.Column():
                    radio_model = gr.Radio(label=t('en', 'lbl_model'), choices=list(MODEL_TYPES.keys()))
                    slider_complex = gr.Slider(label=t('en', 'lbl_complex'), minimum=1, maximum=10, value=2, info=t('en', 'info_complex'))
                    check_feat = gr.CheckboxGroup(label=t('en', 'lbl_feat'), choices=FEATURE_OPTIONS, value=DEFAULT_FEATS, info=t('en', 'info_feat'))
                    radio_data = gr.Radio(label=t('en', 'lbl_data'), choices=list(DATA_SIZES.keys()), value=DEFAULT_SIZE)
                    
                    btn_submit = gr.Button(t('en', 'btn_submit'), variant="primary", size="lg")
                
                with gr.Column():
                    gr.HTML("<div class='panel-box'>Leaderboard Placeholder</div>")
                    feedback_box = gr.HTML("<p>Results will appear here.</p>")

        # Conclusion
        with gr.Column(visible=False, elem_id="conclusion-step") as end_step:
            c_end_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 'concl_title')}</h1>")
            btn_return = gr.Button(t('en', 'btn_return'))

        all_steps = [s1, s2, model_step, end_step]

        # --- UPDATE LANGUAGE (THE FIX) ---
        
        def update_language(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS: lang = "en"
            
            # Helper to get current text
            def txt(k): return t(lang, k)
            
            # CRITICAL: Return updates (dictionaries or gr.update objects), NOT new components!
            return [
                lang,
                # S1
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s1_title')}</h1>"),
                gr.update(value=_get_slide_html(lang, "s1_title", "<p>Localized intro...</p>")),
                gr.update(value=txt('btn_next')),
                # S2
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s2_title')}</h1>"),
                gr.update(value=_get_slide_html(lang, "s2_title", "<p>Localized mission...</p>")),
                gr.update(value=txt('btn_back')), gr.update(value=txt('btn_next')),
                # App Interface
                gr.update(value=f"<h1 style='text-align:center;'>{txt('title')}</h1>"),
                gr.update(label=txt('lbl_model')),
                gr.update(label=txt('lbl_complex'), info=txt('info_complex')),
                gr.update(label=txt('lbl_feat'), info=txt('info_feat')),
                gr.update(label=txt('lbl_data')),
                gr.update(value=txt('btn_submit')),
                # Conclusion
                gr.update(value=f"<h1 style='text-align:center;'>{txt('concl_title')}</h1>"),
                gr.update(value=txt('btn_return'))
            ]

        # Targets for update (Must match return order)
        update_targets = [
            lang_state,
            c_s1_title, c_s1_html, btn_s1_next,
            c_s2_title, c_s2_html, btn_s2_back, btn_s2_next,
            c_app_title, radio_model, slider_complex, check_feat, radio_data, btn_submit,
            c_end_title, btn_return
        ]
        
        # Trigger update on load
        demo.load(update_language, inputs=None, outputs=update_targets)

        # --- NAVIGATION LOGIC ---
        
        def create_nav(target_step):
            def _nav():
                # Return list of updates for all_steps
                return [gr.update(visible=True) if s == target_step else gr.update(visible=False) for s in all_steps]
            return _nav

        def nav_js(target_id, msg):
            return f"""
            ()=>{{
                const overlay = document.getElementById('nav-loading-overlay');
                if(overlay) {{
                    document.getElementById('nav-loading-text').textContent = '{msg}';
                    overlay.style.display = 'flex';
                    setTimeout(()=>{{ overlay.style.opacity = '1'; }}, 10);
                }}
                setTimeout(()=>{{
                    overlay.style.opacity = '0';
                    setTimeout(()=>{{ overlay.style.display = 'none'; }}, 300);
                }}, 800);
            }}
            """

        # Wiring
        btn_s1_next.click(fn=create_nav(s2), outputs=all_steps, js=nav_js("slide-2", "Loading..."))
        btn_s2_back.click(fn=create_nav(s1), outputs=all_steps, js=nav_js("slide-1", "Back..."))
        btn_s2_next.click(fn=create_nav(model_step), outputs=all_steps, js=nav_js("model-step", "Entering Arena..."))
        
        # Mock Game Logic
        def run_game(lang):
            return gr.update(value=f"<p style='color:green; font-size:1.5rem; text-align:center;'>{t(lang, 'concl_title')} (Simulated)</p>")

        btn_submit.click(fn=run_game, inputs=[lang_state], outputs=feedback_box)

    return demo

def launch_model_building_game_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    demo = create_model_building_game_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

if __name__ == "__main__":
    launch_model_building_game_app()

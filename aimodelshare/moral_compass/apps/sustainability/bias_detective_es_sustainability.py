import os
import sys
import subprocess
import time
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://bhtrtkrbf4.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "sustainabilitymc"
FALLBACK_TABLE_ID = "sustainabilitymcfallback"
TOTAL_COURSE_TASKS = 10  # Score calculated against full course
LOCAL_TEST_SESSION_ID = None

# --- Team Name Translations ---
TEAM_NAME_TRANSLATIONS = {
    "es": {
        "The Climate Guardians": "Los Guardianes del Clima",
        "United Eco-Architects": "Eco-Arquitectos Unidos",
        "The Energy Detectives": "Los Detectivos de la Energía",
        "The Sustainability League": "La Liga de la Sostenibilidad",
        "Green Future Engineers": "Ingenieros del Futuro Verde",
        "Zero Carbon Avengers": "Los Vengadores del Carbono Cero",
    },
}
UI_TEAM_LANG = "es"


def translate_team_name_for_display(english_name: str, lang: str = "es") -> str:
    return TEAM_NAME_TRANSLATIONS.get(lang, {}).get(english_name, english_name)


# --- 2. SETUP & DEPENDENCIES ---
def install_dependencies():
    packages = ["gradio>=5.0.0", "aimodelshare", "pandas"]
    for package in packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])


try:
    import gradio as gr
    import pandas as pd
    from aimodelshare.playground import Competition
    from aimodelshare.moral_compass import MoralcompassApiClient
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    print("Installing dependencies...")
    install_dependencies()
    import gradio as gr
    import pandas as pd
    from aimodelshare.playground import Competition
    from aimodelshare.moral_compass import MoralcompassApiClient
    from aimodelshare.aws import get_token_from_session, _get_username_from_token

# --- 3. AUTH & HISTORY HELPERS ---
def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id and LOCAL_TEST_SESSION_ID:
            session_id = LOCAL_TEST_SESSION_ID
        if not session_id:
            return False, None, None
        token = get_token_from_session(session_id)
        if not token:
            return False, None, None
        username = _get_username_from_token(token)
        if not username:
            return False, None, None
        return True, username, token
    except Exception:
        return False, None, None


def fetch_user_history(username, token):
    default_acc = 0.0
    default_team = "Team-Unassigned"
    try:
        playground = Competition(ORIGINAL_PLAYGROUND_URL)
        df = playground.get_leaderboard(token=token)
        if df is None or df.empty:
            return default_acc, default_team
        if "username" in df.columns and "accuracy" in df.columns:
            user_rows = df[df["username"] == username]
            if not user_rows.empty:
                best_acc = user_rows["accuracy"].max()
                if "timestamp" in user_rows.columns and "Team" in user_rows.columns:
                    try:
                        user_rows = user_rows.copy()
                        user_rows["timestamp"] = pd.to_datetime(
                            user_rows["timestamp"], errors="coerce"
                        )
                        user_rows = user_rows.sort_values("timestamp", ascending=False)
                        found_team = user_rows.iloc[0]["Team"]
                        if pd.notna(found_team) and str(found_team).strip():
                            default_team = str(found_team).strip()
                    except Exception:
                        pass
                return float(best_acc), default_team
    except Exception:
        pass
    return default_acc, default_team


# ============================================================================
# 4. MODULE DEFINITIONS — 7-PAGE AI COST EXPLORER
# ============================================================================
# Page 0: Intro/Hook — no quiz
# Page 1: Guiding Principle (OEIAC) — no quiz
# Page 2: Per-Prompt Cost (slider) — quiz t1
# Page 3: Training Costs (model selector) — quiz t2
# Page 4: Water Crisis (animated bars) — quiz t3
# Page 5: Global Scale (stat tabs) — quiz t4
# Page 6: Action Plan (checkboxes) — no quiz
# ============================================================================

MODULES = [
    # ─────────────────────────────────────────────
    # MODULE 0 — INTRO: What Does AI Cost the Planet?
    # ─────────────────────────────────────────────
    {
        "id": 0,
        "title": "El coste oculto de la IA",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-intro-page">
                    <div class="ace-reveal" style="animation-delay:0s;">
                        <div style="font-size:0.875rem; font-weight:800; letter-spacing:3px; color:var(--ace-accent); text-transform:uppercase; margin-bottom:24px; text-align:center;">
                            Experiencia de aprendizaje interactiva
                        </div>
                    </div>
                    <div class="ace-reveal" style="animation-delay:0.3s;">
                        <h1 style="font-size:clamp(2rem, 7vw, 3.2rem); font-weight:800; text-align:center; line-height:1.1; letter-spacing:-1px; color:var(--ace-text); margin:0 0 28px 0;">
                            &iquest;Cu&aacute;nto le cuesta<br/>realmente la IA <span style="color:var(--ace-accent);">al planeta?</span>
                        </h1>
                    </div>
                    <div class="ace-reveal" style="animation-delay:0.7s;">
                        <p id="ace-typewriter-container" style="font-size:1.2rem; color:var(--ace-text-dim); text-align:center; margin-top:0; max-width:500px; line-height:1.6; margin-left:auto; margin-right:auto;">
                            <span id="ace-typewriter-text"></span><span class="ace-blink" style="color:var(--ace-accent);">|</span>
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 1 — YOUR GUIDING PRINCIPLE
    # ─────────────────────────────────────────────
    {
        "id": 1,
        "title": "Tu principio rector",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div style="background:var(--ace-accent-highlight); border-left:4px solid var(--ace-accent); border-radius:16px; padding:20px 24px; margin-bottom:8px;">
                        <p style="margin:0; font-size:1.05rem; line-height:1.6; color:var(--ace-text);">
                            <strong style="color:var(--ace-accent);">Sostenibilidad: Tu principio rector.</strong><br>
                            La IA es poderosa, pero el poder conlleva responsabilidad. Antes de construir IA, debemos preguntarnos: &iquest;es esto bueno para las personas y el planeta? Expertos del Observatorio de &Eacute;tica en Inteligencia Artificial de Catalu&ntilde;a <strong>OEIAC (UdG)</strong> crearon 7 principios para construir IA de forma segura. En esta investigaci&oacute;n, te centrar&aacute;s en uno:
                        </p>
                        <p style="margin:16px 0 0 0; font-size:1.1rem; line-height:1.6; color:var(--ace-text);">
                            <strong>Sostenibilidad</strong> &mdash; Una parte fundamental del principio de sostenibilidad es que los sistemas de IA no deben causar da&ntilde;os a largo plazo al medio ambiente.
                        </p>
                        <p style="margin:16px 0 0 0; font-size:1.05rem; line-height:1.6; color:var(--ace-accent); font-weight:600;">
                            &iquest;Tu misi&oacute;n? Descubrir cu&aacute;nto le cuesta realmente la IA al planeta.
                        </p>
                    </div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.15s;">
                    <details style="background:var(--ace-input-bg); border:1px solid var(--ace-border-color); border-radius:16px; padding:16px 20px; cursor:pointer;">
                        <summary style="font-weight:700; color:var(--ace-text-dim); font-size:0.95rem;">&#128736;&#65039; Referencia: Otros principios de &eacute;tica en IA (OEIAC)</summary>
                        <div style="margin-top:15px; font-size:0.9rem; display:grid; grid-template-columns:1fr 1fr; gap:15px; color:var(--ace-text);">
                            <div>
                                <strong>Justicia y equidad</strong><br>Asegurar que la IA trate a todos los grupos de manera justa y no discrimine.<br><br>
                                <strong>Transparencia y explicabilidad</strong><br>Hacer que el razonamiento de la IA sea claro para que las decisiones puedan ser inspeccionadas.<br><br>
                                <strong>Seguridad y no maleficencia</strong><br>Minimizar errores da&ntilde;inos; planificar para fallos.
                            </div>
                            <div>
                                <strong>Responsabilidad y rendici&oacute;n de cuentas</strong><br>Asignar propietarios claros y mantener rastros de auditor&iacute;a.<br><br>
                                <strong>Autonom&iacute;a</strong><br>Proporcionar procesos de apelaci&oacute;n y alternativas a las decisiones de la IA.<br><br>
                                <strong>Privacidad</strong><br>Utilizar solo los datos necesarios; justificar el uso de atributos sensibles.
                            </div>
                        </div>
                    </details>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 2 — EVERY SINGLE PROMPT
    # ─────────────────────────────────────────────
    {
        "id": 2,
        "title": "Cada consulta cuenta",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">01 / Cada consulta cuenta</div>
                    <h2 class="ace-heading" style="min-height:2.4em;"><span id="ace-m1-typewriter-text"></span><span style="display:inline-block; width:2px; height:1.1em; background:var(--ace-accent); margin-left:2px; animation:aceBlink 0.7s step-end infinite; vertical-align:text-bottom;"></span></h2>
                </div>
                <div id="ace-m1-reveal-content" style="opacity:0; transform:translateY(20px); transition:opacity 0.6s ease, transform 0.6s ease;">
                    <p class="ace-paragraph">Investigadores de UC Riverside descubrieron que una consulta de IA (una pregunta o instrucci&oacute;n que escribes a un chatbot como ChatGPT) de ~100 palabras consume aproximadamente <strong style="color:var(--ace-text); font-weight:600;">medio litro de agua</strong> &mdash; m&aacute;s o menos una botella est&aacute;ndar. Esa agua refrigera los enormes chips de los servidores. Y en cuanto a la energ&iacute;a, el consumo es similar al de ver la televisi&oacute;n durante unos <strong style="color:var(--ace-text); font-weight:600;">9 segundos</strong>.</p>
                    <p class="ace-paragraph" style="font-size:1rem;">&iquest;No parece mucho, verdad? Pero piensa en cu&aacute;ntas consultas env&iacute;as al d&iacute;a...</p>
                    <div class="ace-card">
                        <label style="display:block; font-size:1rem; color:var(--ace-text-dim); margin-bottom:16px; font-weight:600;">&iquest;Cu&aacute;ntas consultas de IA env&iacute;as al d&iacute;a?</label>
                        <input type="range" id="ace-prompt-slider" min="1" max="200" value="1" style="width:100%; cursor:pointer;" oninput="aceUpdatePromptCalc(this.value)">
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:var(--ace-text-dim); margin-top:8px;">
                            <span>1</span><span>50</span><span>100</span><span>150</span><span>200</span>
                        </div>
                        <div id="ace-prompt-count" style="font-size:2.5rem; font-weight:800; color:var(--ace-accent); text-align:center; margin-top:20px;">1 consulta/d&iacute;a</div>
                        <div id="ace-prompt-stats" style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-top:20px;">
                        </div>
                    </div>
                    <button onclick="aceToggleComparison()" id="ace-compare-btn" style="margin-top:20px; padding:12px 20px; font-size:0.95rem; font-weight:600; background:transparent; border:1px solid var(--ace-input-border); border-radius:12px; color:var(--ace-accent); cursor:pointer; transition:all 0.3s; font-family:'Outfit',sans-serif;">
                        Mostrar comparaci&oacute;n con B&uacute;squeda de Google
                    </button>
                    <div id="ace-comparison-card" style="display:none; margin-top:16px;">
                        <div class="ace-card">
                            <div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
                                <div style="flex:1; min-width:150px;">
                                    <div style="font-size:0.85rem; color:var(--ace-text-dim); font-weight:600; text-transform:uppercase; letter-spacing:1px;">B&uacute;squeda en Google</div>
                                    <div style="display:flex; align-items:center; gap:8px; margin-top:8px;">
                                        <div style="height:22px; width:40px; background:var(--ace-success); border-radius:4px;"></div>
                                        <span style="color:var(--ace-text-dim); font-size:1rem;">~0,3 Wh</span>
                                    </div>
                                </div>
                                <div style="flex:1; min-width:150px;">
                                    <div style="font-size:0.85rem; color:var(--ace-text-dim); font-weight:600; text-transform:uppercase; letter-spacing:1px;">Consulta de IA</div>
                                    <div style="display:flex; align-items:center; gap:8px; margin-top:8px;">
                                        <div style="height:22px; width:200px; background:var(--ace-accent); border-radius:4px;"></div>
                                        <span style="color:var(--ace-text-dim); font-size:1rem;">~10 Wh</span>
                                    </div>
                                </div>
                            </div>
                            <p class="ace-paragraph" style="margin-top:16px; margin-bottom:0; font-size:1rem;">Una consulta de IA consume aproximadamente <strong style="color:var(--ace-text); font-weight:600;">30 veces m&aacute;s energ&iacute;a</strong> que una b&uacute;squeda tradicional en Google.</p>
                        </div>
                    </div>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 3 — TRAINING THE BEAST
    # ─────────────────────────────────────────────
    {
        "id": 3,
        "title": "Entrenar a la bestia",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">02 / Entrenar a la bestia</div>
                    <h2 class="ace-heading">Antes de escribir tu primera consulta, <span style="color:var(--ace-error);">ya se hab&iacute;an consumido millones de MWh</span></h2>
                </div>
                <div class="ace-reveal" style="animation-delay:0.2s;">
                    <p class="ace-paragraph">Entrenar un gran modelo de IA implica alimentarlo con enormes cantidades de datos &mdash; libros, p&aacute;ginas web, c&oacute;digo &mdash; durante semanas, utilizando miles de GPU funcionando las 24 horas del d&iacute;a. Solo el entrenamiento de GPT-3 consumi&oacute; suficiente electricidad para <strong style="color:var(--ace-text); font-weight:600;">abastecer 120 hogares de Estados Unidos durante un a&ntilde;o</strong>.</p>
                    <p class="ace-paragraph">Pero el entrenamiento solo ocurre una vez. Despu&eacute;s, 200 millones de personas lo usan cada d&iacute;a &mdash; y todas esas peque&ntilde;as consultas suman <strong style="color:var(--ace-text); font-weight:600;">mucha m&aacute;s energ&iacute;a</strong> de la que cost&oacute; el entrenamiento.</p>
                </div>
                <div class="ace-reveal" style="animation-delay:0.4s;">
                    <div style="font-size:1rem; color:var(--ace-text-dim); margin-bottom:12px; font-weight:600;">Pulsa un modelo para ver su huella de entrenamiento</div>
                    <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px;">
                        <button onclick="aceSelectModel(0)" id="ace-model-btn-0" class="ace-model-btn">
                            <div style="font-size:2rem;">&#129302;</div>
                            <div style="font-size:1.2rem; font-weight:800; margin-top:8px;">GPT-3</div>
                            <div style="font-size:0.85rem; color:var(--ace-text-dim); margin-top:4px;">2020</div>
                        </button>
                        <button onclick="aceSelectModel(1)" id="ace-model-btn-1" class="ace-model-btn">
                            <div style="font-size:2rem;">&#129504;</div>
                            <div style="font-size:1.2rem; font-weight:800; margin-top:8px;">GPT-4</div>
                            <div style="font-size:0.85rem; color:var(--ace-text-dim); margin-top:4px;">2023</div>
                        </button>
                        <button onclick="aceSelectModel(2)" id="ace-model-btn-2" class="ace-model-btn">
                            <div style="font-size:2rem;">&#129433;</div>
                            <div style="font-size:1.2rem; font-weight:800; margin-top:8px;">Llama 3</div>
                            <div style="font-size:0.85rem; color:var(--ace-text-dim); margin-top:4px;">2024</div>
                        </button>
                    </div>
                    <div id="ace-model-detail" style="display:none; margin-top:20px;"></div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.6s;">
                    <div style="margin-top:32px; font-size:1rem; color:var(--ace-text-dim); margin-bottom:16px; font-weight:600;">El consumo energ&eacute;tico del entrenamiento se ha disparado:</div>
                    <div id="ace-training-bars"></div>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 4 — WATER: THE HIDDEN COST
    # ─────────────────────────────────────────────
    {
        "id": 4,
        "title": "Agua: el coste oculto",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">03 / Agua: el coste oculto</div>
                    <h2 class="ace-heading">La IA podr&iacute;a consumir tanta agua como <span style="color:var(--ace-accent);">toda el agua embotellada del mundo</span></h2>
                </div>
                <div class="ace-reveal" style="animation-delay:0.2s;">
                    <p class="ace-paragraph">Un estudio de 2025 estima que la huella h&iacute;drica global de la IA podr&iacute;a situarse entre <strong style="color:var(--ace-text); font-weight:600;">312 y 764 mil millones de litros anuales</strong> &mdash; una cantidad comparable al consumo mundial de agua embotellada en un a&ntilde;o.</p>
                    <p class="ace-paragraph">Gran parte de esta demanda proviene de los centros de datos, que utilizan cada vez m&aacute;s agua dulce para refrigerar sus sistemas, aumentando la presi&oacute;n sobre los recursos h&iacute;dricos locales.</p>
                    <p class="ace-paragraph">Y todo esto cuando solo el <strong style="color:var(--ace-accent); font-weight:700;">0,5% del agua del mundo</strong> es dulce y accesible.</p>
                </div>
                <div class="ace-reveal" style="animation-delay:0.4s;">
                    <div class="ace-card">
                        <div style="text-align:center; font-size:1rem; color:var(--ace-text-dim); margin-bottom:20px; font-weight:600;">Uso anual de agua por la IA, visualizado</div>
                        <div id="ace-water-bars" style="display:flex; justify-content:center; gap:3px; flex-wrap:wrap;"></div>
                        <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:0.8rem; color:var(--ace-text-dim);">
                            <span>0</span><span>Cada barra = ~15 mil millones de litros</span><span>764 000 M L</span>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:20px;">
                            <div style="padding:16px; border-radius:12px; background:var(--ace-input-bg); border:1px solid var(--ace-border-color); text-align:center;">
                                <div style="font-size:1.8rem;">&#127963;&#65039;</div>
                                <div style="font-size:1.1rem; font-weight:700; color:var(--ace-text); margin-top:6px;">19 M litros/d&iacute;a</div>
                                <div style="font-size:0.8rem; color:var(--ace-text-dim); margin-top:4px;">Un gran centro de datos</div>
                                <div style="font-size:0.8rem; color:var(--ace-accent); margin-top:2px;">= una ciudad de 50 000 habitantes</div>
                            </div>
                            <div style="padding:16px; border-radius:12px; background:var(--ace-input-bg); border:1px solid var(--ace-border-color); text-align:center;">
                                <div style="font-size:1.8rem;">&#127758;</div>
                                <div style="font-size:1.1rem; font-weight:700; color:var(--ace-text); margin-top:6px;">56% de d&eacute;ficit para 2030</div>
                                <div style="font-size:0.8rem; color:var(--ace-text-dim); margin-top:4px;">Brecha global de agua dulce</div>
                                <div style="font-size:0.8rem; color:var(--ace-accent); margin-top:2px;">La IA lo est&aacute; empeorando</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.6s;">
                    <div class="ace-card" style="margin-top:24px;">
                        <div style="font-size:1.1rem; font-weight:700; color:var(--ace-text); margin-bottom:12px;">Pregunta r&aacute;pida: &iquest;De d&oacute;nde viene el agua de refrigeraci&oacute;n de los centros de datos?</div>
                        <div id="ace-water-quiz" style="display:grid; gap:8px;"></div>
                        <div id="ace-water-quiz-result" style="display:none; margin-top:16px;"></div>
                    </div>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 5 — ZOOM OUT: GLOBAL SCALE
    # ─────────────────────────────────────────────
    {
        "id": 5,
        "title": "Visi\u00f3n global",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">04 / Visi&oacute;n global</div>
                    <h2 class="ace-heading">El consumo energ&eacute;tico de la IA es comparable a la de <span style="color:var(--ace-warning);">pa&iacute;ses enteros</span></h2>
                </div>
                <div class="ace-reveal" style="animation-delay:0.2s;">
                    <p class="ace-paragraph">Los centros de datos ya consumen aproximadamente el <strong style="color:var(--ace-text); font-weight:600;">1,5% de la electricidad mundial</strong> &mdash; y se prev&eacute; que casi se triplique para 2030. Solo EE. UU. alberga el 45,6% de los centros de datos del mundo.</p>
                </div>
                <div class="ace-reveal" style="animation-delay:0.4s;">
                    <div class="ace-card">
                        <div id="ace-scale-tabs" style="display:flex; gap:8px; margin-bottom:20px;"></div>
                        <div id="ace-scale-display" style="text-align:center;"></div>
                    </div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.6s;">
                    <div style="margin-top:28px; font-size:1rem; color:var(--ace-text-dim); margin-bottom:16px; font-weight:600;">&iquest;A d&oacute;nde va la energ&iacute;a dentro de un centro de datos?</div>
                    <div id="ace-energy-breakdown"></div>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 6 — YOUR MOVE: ACTION PLAN
    # ─────────────────────────────────────────────
    {
        "id": 6,
        "title": "Tu turno",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">05 / Tu turno</div>
                    <h2 class="ace-heading">Ahora que conoces el impacto, <span style="color:var(--ace-success);">&iquest;qu&eacute; puedes hacer realmente?</span></h2>
                </div>
                <div class="ace-reveal" style="animation-delay:0.2s;">
                    <p class="ace-paragraph">Nadie dice que dejes de usar la IA &mdash; es incre&iacute;blemente potente. Pero ser <strong style="color:var(--ace-text); font-weight:600;">consciente</strong> de c&oacute;mo la usas marca una diferencia real cuando se multiplica por miles de millones de usuarios.</p>
                </div>
                <div class="ace-reveal" style="animation-delay:0.4s;">
                    <div id="ace-actions" style="display:grid; gap:10px;"></div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.6s;">
                    <div class="ace-card" style="margin-top:24px; text-align:center;" id="ace-score-card">
                        <div style="font-size:0.8rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:3px;">Tu reducci&oacute;n potencial de huella</div>
                        <div id="ace-action-score" style="font-size:3.5rem; font-weight:800; color:var(--ace-text-dim); margin-top:8px; transition:color 0.3s;">0%</div>
                        <p id="ace-action-message" class="ace-paragraph" style="margin-top:8px; margin-bottom:0; text-align:center; font-size:1rem;">&iexcl;Selecciona algunas acciones arriba para ver tu impacto!</p>
                    </div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.8s;">
                    <div class="ace-card" style="margin-top:24px; text-align:center; border:2px solid var(--ace-success);">
                        <div style="font-size:1.2rem; font-weight:800; color:var(--ace-text);">La conclusi&oacute;n</div>
                        <p class="ace-paragraph" style="margin-top:12px; margin-bottom:0; text-align:center; max-width:480px; margin-left:auto; margin-right:auto;">La IA es potente. La IA es &uacute;til. Pero la IA <strong style="color:var(--ace-accent); font-weight:700;">no es gratuita</strong>. Cada consulta cuesta agua y energ&iacute;a reales. Ser consciente es el primer paso &mdash; y t&uacute; acabas de darlo.</p>
                        <div style="font-size:0.8rem; color:var(--ace-text-dim); margin-top:16px;">Fuentes: UC Riverside, IEA, MIT, VU Amsterdam (2024&ndash;2025)</div>
                    </div>
                </div>
            </div>
        """,
    },
]


# ============================================================================
# 5. QUIZ CONFIG — 4 QUIZZES ON MODULES 2-5, TASK IDs t1-t4
# ============================================================================

QUIZ_CONFIG = {
    2: {
        "t": "t1",
        "q": "Un amigo dice: *\u2018Una pregunta a la IA solo gasta una botella de agua \u2014 \u00bfa qui\u00e9n le importa?\u2019* \u00bfPor qu\u00e9 deber\u00eda importarte?",
        "o": [
            "A) Tu amigo tiene raz\u00f3n \u2014 una botella no es nada.",
            "B) Una pregunta es peque\u00f1a, pero 200 millones de personas haciendo m\u00e1s de 50 preguntas al d\u00eda suman miles de millones de botellas de agua cada a\u00f1o. Las cosas peque\u00f1as se vuelven enormes cuando todos las hacen.",
            "C) El agua no importa \u2014 el verdadero problema es solo la electricidad.",
        ],
        "a": "B) Una pregunta es peque\u00f1a, pero 200 millones de personas haciendo m\u00e1s de 50 preguntas al d\u00eda suman miles de millones de botellas de agua cada a\u00f1o. Las cosas peque\u00f1as se vuelven enormes cuando todos las hacen.",
        "success": "<strong>\u00a1Acertaste!</strong> Una pregunta es peque\u00f1a. \u00bfPero 200 millones de personas haciendo m\u00e1s de 50 preguntas al d\u00eda? Eso se acumula r\u00e1pido.",
    },
    3: {
        "t": "t2",
        "q": "Entrenar un modelo de IA como GPT-4 usa una cantidad enorme de energ\u00eda \u2014 como dar electricidad a 6.000 casas durante un a\u00f1o. Pero despu\u00e9s del entrenamiento, 200 millones de personas lo usan cada d\u00eda. \u00bfQu\u00e9 gasta m\u00e1s energ\u00eda con el tiempo \u2014 construir la IA o que todos la usen?",
        "o": [
            "A) Construirla gasta m\u00e1s \u2014 el entrenamiento es la parte cara.",
            "B) Que todos la usen gasta much\u00edsimo m\u00e1s. Cada pregunta cuesta un poco de energ\u00eda, pero millones de personas preguntando todo el d\u00eda, todos los d\u00edas, suman mucho m\u00e1s que el entrenamiento.",
            "C) Son m\u00e1s o menos iguales.",
        ],
        "a": "B) Que todos la usen gasta much\u00edsimo m\u00e1s. Cada pregunta cuesta un poco de energ\u00eda, pero millones de personas preguntando todo el d\u00eda, todos los d\u00edas, suman mucho m\u00e1s que el entrenamiento.",
        "success": "<strong>\u00a1Exacto!</strong> Entrenar GPT-3 cost\u00f3 meses de energ\u00eda. Una vez que la gente empez\u00f3 a usarlo, gastaron esa misma cantidad en solo 11 d\u00edas.",
    },
    4: {
        "t": "t3",
        "q": "Un solo centro de datos consume 19 millones de litros de agua dulce cada d\u00eda. Esa agua viene de los mismos r\u00edos y pozos de los que bebe la gente de la zona. \u00bfPor qu\u00e9 es un problema?",
        "o": [
            "A) No lo es \u2014 el centro de datos paga por el agua, as\u00ed que es justo.",
            "B) En lugares donde el agua escasea, las familias ya est\u00e1n recortando. Un centro de datos bebiendo millones de litros al d\u00eda lo hace a\u00fan m\u00e1s dif\u00edcil para todos los dem\u00e1s.",
            "C) El agua vuelve al aire como vapor, as\u00ed que en realidad no se pierde.",
        ],
        "a": "B) En lugares donde el agua escasea, las familias ya est\u00e1n recortando. Un centro de datos bebiendo millones de litros al d\u00eda lo hace a\u00fan m\u00e1s dif\u00edcil para todos los dem\u00e1s.",
        "success": "<strong>As\u00ed es.</strong> En Mesa, Arizona, las familias acortaban sus duchas durante una gran sequ\u00eda \u2014 mientras un centro de datos de Microsoft cercano convert\u00eda 212 millones de litros de su agua en vapor cada a\u00f1o.",
    },
    5: {
        "t": "t4",
        "q": "Los centros de datos de IA ya consumen alrededor del 1,5% de toda la electricidad del mundo \u2014 y se espera que casi se triplique para 2030. En 2022, Dubl\u00edn (la capital de Irlanda) prohibi\u00f3 nuevos centros de datos porque estaban usando tanta electricidad que los hogares y negocios podr\u00edan quedarse sin suficiente. **\u00bfQu\u00e9 nos dice esto?**",
        "o": [
            "A) Los centros de datos deber\u00edan prohibirse en todas partes \u2014 usan demasiada electricidad y no vale la pena.",
            "B) La IA ya usa tanta electricidad que compite con pa\u00edses enteros por la energ\u00eda, y los gobiernos tienen que tomar decisiones dif\u00edciles al respecto.",
            "C) Dubl\u00edn reaccion\u00f3 de forma exagerada \u2014 el 1,5% no es tanto, y la energ\u00eda solar y e\u00f3lica crecer\u00e1n lo suficiente por s\u00ed solas.",
        ],
        "a": "B) La IA ya usa tanta electricidad que compite con pa\u00edses enteros por la energ\u00eda, y los gobiernos tienen que tomar decisiones dif\u00edciles al respecto.",
        "success": "La IA ya consume tanta electricidad como pa\u00edses enteros \u2014 y crece m\u00e1s r\u00e1pido de lo que las energ\u00edas renovables pueden seguir.",
    },
}


# ============================================================================
# 6. LEADERBOARD & API LOGIC
# ============================================================================

def get_leaderboard_data(client, username, team_name, local_task_list=None, override_score=None):
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])

        if override_score is not None:
            found = False
            for u in users:
                if u.get("username") == username:
                    u["moralCompassScore"] = override_score
                    found = True
                    break
            if not found:
                users.append(
                    {"username": username, "moralCompassScore": override_score, "teamName": team_name}
                )

        users_sorted = sorted(
            users, key=lambda x: float(x.get("moralCompassScore", 0) or 0), reverse=True
        )

        my_user = next((u for u in users_sorted if u.get("username") == username), None)
        score = float(my_user.get("moralCompassScore", 0) or 0) if my_user else 0.0
        rank = users_sorted.index(my_user) + 1 if my_user else 0

        completed_task_ids = (
            local_task_list
            if local_task_list is not None
            else (my_user.get("completedTaskIds", []) if my_user else [])
        )

        team_map = {}
        for u in users:
            t = u.get("teamName")
            s = float(u.get("moralCompassScore", 0) or 0)
            if t:
                if t not in team_map:
                    team_map[t] = {"sum": 0, "count": 0}
                team_map[t]["sum"] += s
                team_map[t]["count"] += 1
        teams_sorted = []
        for t, d in team_map.items():
            teams_sorted.append({"team": t, "avg": d["sum"] / d["count"]})
        teams_sorted.sort(key=lambda x: x["avg"], reverse=True)
        my_team = next((t for t in teams_sorted if t["team"] == team_name), None)
        team_rank = teams_sorted.index(my_team) + 1 if my_team else 0
        return {
            "score": score,
            "rank": rank,
            "team_rank": team_rank,
            "all_users": users_sorted,
            "all_teams": teams_sorted,
            "completed_task_ids": completed_task_ids,
        }
    except Exception:
        return None


def ensure_table_and_get_data(username, token, team_name, task_list_state=None):
    global TABLE_ID
    if not username or not token:
        return None, username
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    try:
        client.get_table(TABLE_ID)
    except Exception:
        try:
            client.get_table(FALLBACK_TABLE_ID)
            TABLE_ID = FALLBACK_TABLE_ID
        except Exception:
            pass
    return get_leaderboard_data(client, username, team_name, task_list_state), username


def trigger_api_update(
    username, token, team_name, module_id, user_real_accuracy, task_list_state, append_task_id=None
):
    if not username or not token:
        return None, None, username, task_list_state
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

    acc = float(user_real_accuracy) if user_real_accuracy is not None else 0.0

    old_task_list = list(task_list_state) if task_list_state else []
    new_task_list = list(old_task_list)
    if append_task_id and append_task_id not in new_task_list:
        new_task_list.append(append_task_id)
        try:
            new_task_list.sort(
                key=lambda x: int(x[1:]) if x.startswith("t") and x[1:].isdigit() else 0
            )
        except Exception:
            pass

    tasks_completed = len(new_task_list)
    client.update_moral_compass(
        table_id=TABLE_ID,
        username=username,
        team_name=team_name,
        metrics={"accuracy": acc},
        tasks_completed=tasks_completed,
        total_tasks=TOTAL_COURSE_TASKS,
        primary_metric="accuracy",
        completed_task_ids=new_task_list,
    )

    old_score_calc = acc * (len(old_task_list) / TOTAL_COURSE_TASKS)
    new_score_calc = acc * (len(new_task_list) / TOTAL_COURSE_TASKS)

    prev_data = get_leaderboard_data(
        client, username, team_name, old_task_list, override_score=old_score_calc
    )
    lb_data = get_leaderboard_data(
        client, username, team_name, new_task_list, override_score=new_score_calc
    )

    return prev_data, lb_data, username, new_task_list


# ============================================================================
# 7. SUCCESS MESSAGE RENDERER
# ============================================================================

def generate_success_message(prev, curr, specific_text):
    old_score = float(prev.get("score", 0) or 0) if prev else 0.0
    new_score = float(curr.get("score", 0) or 0)
    diff_score = new_score - old_score

    old_rank = prev.get("rank", "\u2013") if prev else "\u2013"
    new_rank = curr.get("rank", "\u2013")

    ranks_are_int = isinstance(old_rank, int) and isinstance(new_rank, int)
    rank_diff = old_rank - new_rank if ranks_are_int else 0

    if old_score == 0 and new_score > 0:
        style_key = "first"
    else:
        if ranks_are_int:
            if rank_diff >= 3:
                style_key = "major"
            elif rank_diff > 0:
                style_key = "climb"
            elif diff_score > 0 and new_rank == old_rank:
                style_key = "solid"
            else:
                style_key = "tight"
        else:
            style_key = "solid" if diff_score > 0 else "tight"

    card_class = "profile-card success-card"

    if style_key == "first":
        card_class += " first-score"
        header_emoji = "\U0001f389"
        header_title = "\u00a1Ya est\u00e1s en la clasificaci\u00f3n!"
        summary_line = "Acabas de obtener tu primera puntuaci\u00f3n de Br\u00fajula Moral \u2014 ya formas parte del ranking global."
        cta_line = "Sigue investigando para escalar en la clasificaci\u00f3n."
    elif style_key == "major":
        header_emoji = "\U0001f525"
        header_title = "\u00a1Gran impulso en la Br\u00fajula Moral!"
        summary_line = "Tu an\u00e1lisis ha tenido un gran impacto \u2014 acabas de adelantar a otros detectives."
        cta_line = "Contin\u00faa tu investigaci\u00f3n para mantener el impulso."
    elif style_key == "climb":
        header_emoji = "\U0001f680"
        header_title = "Est\u00e1s escalando en la clasificaci\u00f3n"
        summary_line = "Buen trabajo \u2014 has superado a otros participantes."
        cta_line = "Pulsa SIGUIENTE para continuar tu investigaci\u00f3n."
    elif style_key == "tight":
        header_emoji = "\U0001f4ca"
        header_title = "La clasificaci\u00f3n est\u00e1 cambiando"
        summary_line = "Otros equipos tambi\u00e9n se mueven. Unas cuantas respuestas m\u00e1s s\u00f3lidas te diferenciar\u00e1n."
        cta_line = "Afronta el siguiente paso para fortalecer tu posici\u00f3n."
    else:
        header_emoji = "\u2705"
        header_title = "Progreso registrado"
        summary_line = "Tu conocimiento sobre sostenibilidad ha aumentado tu puntuaci\u00f3n de Br\u00fajula Moral."
        cta_line = "Prueba el siguiente paso para seguir escalando."

    if style_key == "first":
        score_line = f"\U0001f9ed Puntuaci\u00f3n: <strong>{new_score:.3f}</strong>"
        rank_line = f"\U0001f3c5 Posici\u00f3n inicial: <strong>#{new_rank}</strong>"
    else:
        score_line = (
            f"\U0001f9ed Puntuaci\u00f3n: {old_score:.3f} \u2192 <strong>{new_score:.3f}</strong> "
            f"(+{diff_score:.3f})"
        )
        if ranks_are_int:
            if old_rank == new_rank:
                rank_line = f"\U0001f4ca Posici\u00f3n: <strong>#{new_rank}</strong> (manteni\u00e9ndose)"
            elif rank_diff > 0:
                rank_line = f"\U0001f4c8 Posici\u00f3n: #{old_rank} \u2192 <strong>#{new_rank}</strong> (+{rank_diff} puestos)"
            else:
                rank_line = f"\U0001f53b Posici\u00f3n: #{old_rank} \u2192 <strong>#{new_rank}</strong> ({rank_diff} puestos)"
        else:
            rank_line = f"\U0001f4ca Posici\u00f3n: <strong>#{new_rank}</strong>"

    return f"""
    <div class="{card_class}">
        <div class="success-header">
            <div>
                <div class="success-title">{header_emoji} {header_title}</div>
                <div class="success-summary">{summary_line}</div>
            </div>
            <div class="success-delta">+{diff_score:.3f}</div>
        </div>
        <div class="success-metrics">
            <div class="success-metric-line">{score_line}</div>
            <div class="success-metric-line">{rank_line}</div>
        </div>
        <div class="success-body">
            <p class="success-body-text">{specific_text}</p>
            <p class="success-cta">{cta_line}</p>
        </div>
    </div>
    """


# ============================================================================
# 8. DASHBOARD & LEADERBOARD RENDERERS
# ============================================================================

def render_top_dashboard(data, module_id):
    display_score = 0.0
    count_completed = 0
    rank_display = "\u2013"
    team_rank_display = "\u2013"
    if data:
        display_score = float(data.get("score", 0.0))
        rank_display = f"#{data.get('rank', '\u2013')}"
        team_rank_display = f"#{data.get('team_rank', '\u2013')}"
        count_completed = len(data.get("completed_task_ids", []) or [])
    progress_pct = min(100, int((count_completed / TOTAL_COURSE_TASKS) * 100))

    if module_id <= 4:
        phase_label = "FASE 1: Impacto individual"
        phase_color = "#6366f1"
    else:
        phase_label = "FASE 2: Escala global"
        phase_color = "#ef4444"

    return f"""
    <div class="summary-box">
        <div class="summary-box-inner">
            <div class="summary-metrics">
                <div style="text-align:center;">
                    <div class="label-text">Puntuaci\u00f3n Br\u00fajula Moral</div>
                    <div class="score-text-primary">\U0001f9ed {display_score:.3f}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Posici\u00f3n del equipo</div>
                    <div class="score-text-team">{team_rank_display}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Posici\u00f3n global</div>
                    <div class="score-text-global">{rank_display}</div>
                </div>
            </div>
            <div class="summary-progress">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="progress-label">Progreso de la investigaci\u00f3n: {progress_pct}%</div>
                    <div style="font-size:0.75rem; font-weight:700; color:{phase_color}; background:rgba(0,0,0,0.05); padding:2px 8px; border-radius:10px;">{phase_label}</div>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{progress_pct}%;"></div>
                </div>
            </div>
        </div>
    </div>
    """


def render_leaderboard_card(data, username, team_name):
    team_rows = ""
    user_rows = ""
    if data and data.get("all_teams"):
        for i, t in enumerate(data["all_teams"]):
            cls = "row-highlight-team" if t["team"] == team_name else "row-normal"
            team_rows += (
                f"<tr class='{cls}'><td style='padding:8px;text-align:center;'>{i+1}</td>"
                f"<td style='padding:8px;'>{translate_team_name_for_display(t['team'], UI_TEAM_LANG)}</td>"
                f"<td style='padding:8px;text-align:right;'>{t['avg']:.3f}</td></tr>"
            )
    if data and data.get("all_users"):
        for i, u in enumerate(data["all_users"]):
            cls = "row-highlight-me" if u.get("username") == username else "row-normal"
            sc = float(u.get("moralCompassScore", 0))
            if u.get("username") == username and data.get("score") != sc:
                sc = data.get("score")
            user_rows += (
                f"<tr class='{cls}'><td style='padding:8px;text-align:center;'>{i+1}</td>"
                f"<td style='padding:8px;'>{u.get('username','')}</td>"
                f"<td style='padding:8px;text-align:right;'>{sc:.3f}</td></tr>"
            )
    return f"""
    <div class="scenario-box leaderboard-card">
        <h3 class="slide-title" style="margin-bottom:10px;">\U0001f4ca Clasificaci\u00f3n en directo</h3>
        <div class="lb-tabs">
            <input type="radio" id="lb-tab-team" name="lb-tabs" checked>
            <label for="lb-tab-team" class="lb-tab-label">\U0001f3c6 Equipo</label>
            <input type="radio" id="lb-tab-user" name="lb-tabs">
            <label for="lb-tab-user" class="lb-tab-label">\U0001f464 Individual</label>
            <div class="lb-tab-panels">
                <div class="lb-panel panel-team">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Posici\u00f3n</th><th>Equipo</th><th style='text-align:right;'>Media \U0001f9ed</th></tr>
                            </thead>
                            <tbody>{team_rows}</tbody>
                        </table>
                    </div>
                </div>
                <div class="lb-panel panel-user">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Posici\u00f3n</th><th>Detective</th><th style='text-align:right;'>Punt. \U0001f9ed</th></tr>
                            </thead>
                            <tbody>{user_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """


# ============================================================================
# 9. CSS — New design system from JSX + Gradio integration styles
# ============================================================================

css = """
/* ========== AI Cost Explorer Design System ========== */

/* ACE CSS variables — scoped with ace- prefix to avoid Gradio collisions */
/* Light mode is the default (Gradio Soft theme default) */
:root {
    --ace-bg: #f8fafc;
    --ace-card-bg: rgba(255, 255, 255, 0.9);
    --ace-accent: #0284c7;
    --ace-accent-glow: rgba(2, 132, 199, 0.2);
    --ace-success: #059669;
    --ace-warning: #d97706;
    --ace-error: #dc2626;
    --ace-text: #0f172a;
    --ace-text-dim: #64748b;
    --ace-bg-gradient-1: rgba(2, 132, 199, 0.08);
    --ace-bg-gradient-2: rgba(5, 150, 105, 0.08);
    --ace-card-shadow: rgba(0, 0, 0, 0.1);
    --ace-border-color: rgba(0, 0, 0, 0.08);
    --ace-input-bg: rgba(0, 0, 0, 0.02);
    --ace-input-border: rgba(0, 0, 0, 0.1);
    --ace-hover-bg: rgba(0, 0, 0, 0.05);
    --ace-progress-line: rgba(0, 0, 0, 0.1);
    --ace-bar-text: #0f172a;
    --ace-success-bg: rgba(5, 150, 105, 0.08);
    --ace-error-bg: rgba(220, 38, 38, 0.08);
    --ace-success-highlight: rgba(5, 150, 105, 0.15);
    --ace-error-highlight: rgba(220, 38, 38, 0.15);
    --ace-accent-highlight: rgba(2, 132, 199, 0.1);
}
@media (prefers-color-scheme: dark) {
    :root {
        --ace-bg: #0f172a;
        --ace-card-bg: rgba(30, 41, 59, 0.7);
        --ace-accent: #38bdf8;
        --ace-accent-glow: rgba(56, 189, 248, 0.3);
        --ace-success: #10b981;
        --ace-warning: #fbbf24;
        --ace-error: #f43f5e;
        --ace-text: #f8fafc;
        --ace-text-dim: #94a3b8;
        --ace-bg-gradient-1: rgba(56, 189, 248, 0.05);
        --ace-bg-gradient-2: rgba(16, 185, 129, 0.05);
        --ace-card-shadow: rgba(0, 0, 0, 0.5);
        --ace-border-color: rgba(255, 255, 255, 0.05);
        --ace-input-bg: rgba(255, 255, 255, 0.05);
        --ace-input-border: rgba(255, 255, 255, 0.1);
        --ace-hover-bg: rgba(255, 255, 255, 0.08);
        --ace-progress-line: rgba(255, 255, 255, 0.1);
        --ace-bar-text: #fff;
        --ace-success-bg: rgba(16, 185, 129, 0.08);
        --ace-error-bg: rgba(244, 63, 94, 0.08);
        --ace-success-highlight: rgba(16, 185, 129, 0.15);
        --ace-error-highlight: rgba(244, 63, 94, 0.15);
        --ace-accent-highlight: rgba(56, 189, 248, 0.1);
    }
}
.dark {
    --ace-bg: #0f172a;
    --ace-card-bg: rgba(30, 41, 59, 0.7);
    --ace-accent: #38bdf8;
    --ace-accent-glow: rgba(56, 189, 248, 0.3);
    --ace-success: #10b981;
    --ace-warning: #fbbf24;
    --ace-error: #f43f5e;
    --ace-text: #f8fafc;
    --ace-text-dim: #94a3b8;
    --ace-bg-gradient-1: rgba(56, 189, 248, 0.05);
    --ace-bg-gradient-2: rgba(16, 185, 129, 0.05);
    --ace-card-shadow: rgba(0, 0, 0, 0.5);
    --ace-border-color: rgba(255, 255, 255, 0.05);
    --ace-input-bg: rgba(255, 255, 255, 0.05);
    --ace-input-border: rgba(255, 255, 255, 0.1);
    --ace-hover-bg: rgba(255, 255, 255, 0.08);
    --ace-progress-line: rgba(255, 255, 255, 0.1);
    --ace-bar-text: #fff;
    --ace-success-bg: rgba(16, 185, 129, 0.08);
    --ace-error-bg: rgba(244, 63, 94, 0.08);
    --ace-success-highlight: rgba(16, 185, 129, 0.15);
    --ace-error-highlight: rgba(244, 63, 94, 0.15);
    --ace-accent-highlight: rgba(56, 189, 248, 0.1);
}

/* ACE Animations */
@keyframes aceSlideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes aceBlink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* ACE reveal animation */
.ace-reveal {
    opacity: 0;
    transform: translateY(30px);
    animation: aceSlideUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* ACE blink cursor */
.ace-blink { animation: aceBlink 1s infinite; }

/* ACE Intro page */
.ace-intro-page {
    min-height: 65vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 60px 20px;
    max-width: 900px;
    margin: 0 auto;
}

/* ACE Section label */
.ace-section-label {
    font-size: 0.875rem;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--ace-accent);
    margin-bottom: 12px;
}

/* ACE Heading */
.ace-heading {
    font-weight: 800;
    font-size: clamp(1.6rem, 4.5vw, 2.2rem);
    line-height: 1.2;
    color: var(--ace-text);
    margin: 0 0 20px 0;
    font-family: 'Outfit', sans-serif;
}

/* ACE Paragraph */
.ace-paragraph {
    font-size: 1.125rem;
    line-height: 1.7;
    color: var(--ace-text-dim);
    margin-bottom: 20px;
    font-family: 'Outfit', sans-serif;
}

/* ACE Card — glassmorphism */
.ace-card {
    background: var(--ace-card-bg);
    backdrop-filter: blur(16px);
    border-radius: 24px;
    padding: 32px 28px;
    border: 1px solid var(--ace-border-color);
    box-shadow: 0 25px 50px -12px var(--ace-card-shadow);
}

/* ACE Model toggle buttons */
.ace-model-btn {
    padding: 20px;
    border-radius: 16px;
    cursor: pointer;
    text-align: center;
    background: var(--ace-input-bg);
    border: 2px solid var(--ace-border-color);
    color: var(--ace-text);
    transition: all 0.3s;
    font-family: 'Outfit', sans-serif;
}
.ace-model-btn:hover {
    border-color: var(--ace-accent);
}

/* ACE Quiz option buttons (in-page MCQ) */
.ace-quiz-option {
    padding: 14px 16px;
    border-radius: 12px;
    text-align: left;
    cursor: pointer;
    font-size: 1rem;
    background: var(--ace-input-bg);
    border: 1px solid var(--ace-input-border);
    color: var(--ace-text);
    transition: all 0.3s;
    font-family: 'Outfit', sans-serif;
    width: 100%;
}
.ace-quiz-option:hover {
    border-color: var(--ace-accent);
}

/* ACE Range slider styling */
.ace-card input[type="range"] {
    -webkit-appearance: none;
    background: var(--ace-input-bg);
    border-radius: 6px;
    outline: none;
    height: 8px;
}
.ace-card input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: var(--ace-accent);
    cursor: pointer;
    box-shadow: 0 0 10px var(--ace-accent-glow);
}

/* Module container backgrounds for ACE */
.module-container .scenario-box {
    font-family: 'Outfit', sans-serif;
}

/* ========== Gradio Integration Styles (from Activity 6) ========== */

/* Layout + containers */
.summary-box {
    background: var(--block-background-fill);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid var(--border-color-primary);
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}
.summary-box-inner { display: flex; align-items: center; justify-content: space-between; gap: 30px; }
.summary-metrics { display: flex; gap: 30px; align-items: center; }
.summary-progress { width: 560px; max-width: 100%; }

/* Scenario cards */
.scenario-box {
    padding: 24px;
    border-radius: 14px;
    background: var(--block-background-fill);
    border: 1px solid var(--border-color-primary);
    margin-bottom: 22px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.08);
}
.slide-title { margin-top: 0; font-size: 1.9rem; font-weight: 800; }
.slide-body { font-size: 1.12rem; line-height: 1.65; }

/* Hint boxes */
.hint-box {
    padding: 12px;
    border-radius: 10px;
    background: var(--background-fill-secondary);
    border: 1px solid var(--border-color-primary);
    margin-top: 10px;
    font-size: 0.98rem;
}

/* Success / profile card */
.profile-card.success-card {
    padding: 20px;
    border-radius: 14px;
    border-left: 6px solid var(--ace-success);
    background: linear-gradient(135deg, var(--ace-success-bg), var(--block-background-fill));
    margin-top: 16px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    font-size: 1.04rem;
    line-height: 1.55;
}
.profile-card.first-score {
    border-left-color: var(--ace-warning);
    background: linear-gradient(135deg, rgba(250,204,21,0.18), var(--block-background-fill));
}
.success-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 8px; }
.success-title { font-size: 1.26rem; font-weight: 900; color: var(--ace-success); }
.success-summary { font-size: 1.06rem; color: var(--body-text-color-subdued); margin-top: 4px; }
.success-delta { font-size: 1.5rem; font-weight: 800; color: var(--ace-success); }
.success-metrics { margin-top: 10px; padding: 10px 12px; border-radius: 10px; background: var(--background-fill-secondary); font-size: 1.06rem; }
.success-metric-line { margin-bottom: 4px; }
.success-body { margin-top: 10px; font-size: 1.06rem; }
.success-body-text { margin: 0 0 6px 0; }
.success-cta { margin: 4px 0 0 0; font-weight: 700; font-size: 1.06rem; }

/* Numbers + labels */
.score-text-primary { font-size: 2.05rem; font-weight: 900; color: var(--color-accent); }
.score-text-team { font-size: 2.05rem; font-weight: 900; color: var(--color-accent); }
.score-text-global { font-size: 2.05rem; font-weight: 900; }
.label-text { font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--body-text-color-subdued, #6b7280); }

/* Progress bar */
.progress-bar-bg { width: 100%; height: 10px; background: var(--border-color-primary, #e5e7eb); border-radius: 6px; overflow: hidden; margin-top: 8px; }
.progress-bar-fill { height: 100%; background: var(--color-accent); transition: width 280ms ease; }

/* Leaderboard tabs + tables */
.leaderboard-card input[type="radio"] { display: none; }
.lb-tab-label {
    display: inline-block; padding: 8px 16px; margin-right: 8px; border-radius: 20px;
    cursor: pointer; border: 1px solid var(--border-color-primary); font-weight: 700; font-size: 0.94rem;
}
#lb-tab-team:checked + label, #lb-tab-user:checked + label {
    background: var(--color-accent); color: white; border-color: var(--color-accent);
    box-shadow: 0 3px 8px rgba(99,102,241,0.25);
}
.lb-panel { display: none; margin-top: 10px; }
#lb-tab-team:checked ~ .lb-tab-panels .panel-team { display: block; }
#lb-tab-user:checked ~ .lb-tab-panels .panel-user { display: block; }
.table-container { height: 320px; overflow-y: auto; border: 1px solid var(--border-color-primary); border-radius: 10px; }
.leaderboard-table { width: 100%; border-collapse: collapse; }
.leaderboard-table th {
    position: sticky; top: 0; background: var(--background-fill-secondary);
    padding: 10px; text-align: left; border-bottom: 2px solid var(--border-color-primary);
    font-weight: 800;
}
.leaderboard-table td { padding: 10px; border-bottom: 1px solid var(--border-color-primary); }
.row-highlight-me, .row-highlight-team { background: var(--ace-accent-highlight); font-weight: 700; }

/* Small utility */
.divider-vertical { width: 1px; height: 48px; background: var(--border-color-primary); opacity: 0.6; }

/* Radio sizes */
.quiz-radio-large label { font-size: 1.06rem; }

/* Navigation loading overlay */
#nav-loading-overlay {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: color-mix(in srgb, var(--body-background-fill) 95%, transparent);
    z-index: 9999; display: none; flex-direction: column; align-items: center;
    justify-content: center; opacity: 0; transition: opacity 0.3s ease;
}
.nav-spinner {
    width: 50px; height: 50px; border: 5px solid var(--border-color-primary);
    border-top: 5px solid var(--color-accent); border-radius: 50%;
    animation: nav-spin 1s linear infinite; margin-bottom: 20px;
}
@keyframes nav-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
#nav-loading-text {
    font-size: 1.3rem; font-weight: 600; color: var(--color-accent);
}
@media (prefers-color-scheme: dark) {
    #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); }
    .nav-spinner { border-color: rgba(148, 163, 184, 0.4); border-top-color: var(--color-accent); }
}
.dark #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); }
.dark .nav-spinner { border-color: rgba(148, 163, 184, 0.4); border-top-color: var(--color-accent); }

/* Points chip + quiz CTA */
.points-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-weight: 800;
    font-size: 0.8rem;
    background: var(--color-accent-soft);
    color: var(--color-accent);
    border: 1px solid color-mix(in srgb, var(--color-accent) 35%, transparent);
}
.quiz-cta {
    margin: 8px 0 10px 0;
    font-size: 0.9rem;
    color: var(--body-text-color-subdued);
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}
"""


# ============================================================================
# 9b. CLIENT-SIDE JAVASCRIPT — Consolidated (Gradio 6 head injection)
# ============================================================================
# Gradio 6 Svelte {@html} does NOT execute <script> tags inside gr.HTML().
# All JS is injected via gr.Blocks(head=...) into the document <head>.

CLIENT_JS = """
// === Dynamically load Outfit font ===
(function(){
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap';
    document.head.appendChild(link);
})();

// === Module 0: Typewriter ===
function aceInitTypewriter(){
    var el = document.getElementById('ace-typewriter-text');
    if (!el) { setTimeout(aceInitTypewriter, 200); return; }
    if (el.dataset.init === '1') return;
    el.dataset.init = '1';
    var full = "Cada vez que usas la IA, algo invisible sucede...";
    var i = 0;
    var iv = setInterval(function(){
        i++;
        el.textContent = full.slice(0, i);
        if (i >= full.length) clearInterval(iv);
    }, 45);
} aceInitTypewriter();

// === Module 1: Heading Typewriter ===
function aceInitM1Typewriter(){
    var el = document.getElementById('ace-m1-typewriter-text');
    if (!el) { setTimeout(aceInitM1Typewriter, 200); return; }
    if (el.dataset.init === '1') return;
    el.dataset.init = '1';
    var part1 = "Una pregunta a ChatGPT = ";
    var part2 = "una botella de agua";
    var i = 0, total = part1.length + part2.length;
    var iv = setInterval(function(){
        i++;
        if (i <= part1.length) {
            el.innerHTML = part1.slice(0, i);
        } else {
            el.innerHTML = part1 + '<span style="color:var(--ace-accent);">' + part2.slice(0, i - part1.length) + '</span>';
        }
        if (i >= total) {
            clearInterval(iv);
            var content = document.getElementById('ace-m1-reveal-content');
            if (content) { content.style.opacity = '1'; content.style.transform = 'translateY(0)'; }
        }
    }, 45);
} aceInitM1Typewriter();

// === Module 1: Prompt Calculator ===
function aceUpdatePromptCalc(val) {
    var countEl = document.getElementById('ace-prompt-count');
    var statsEl = document.getElementById('ace-prompt-stats');
    if (!countEl || !statsEl) return;
    var pc = parseInt(val);
    var w = (pc * 0.519).toFixed(1);
    var e = (pc * 0.01).toFixed(2);
    var tv = pc * 9;
    var bottles = Math.round(w / 0.5);
    var co2 = (pc * 0.4).toFixed(1);
    var yearKm = ((co2 * 365) / 121).toFixed(1);
    countEl.textContent = pc + ' consulta' + (pc > 1 ? 's' : '') + '/d\\u00eda';
    var stats = [
        {l:'Agua usada', v:w+'L', i:'\\ud83d\\udca7', s:bottles+' botellas'},
        {l:'Energ\\u00eda usada', v:e+' kWh', i:'\\u26a1', s:tv+'s de TV'},
        {l:'CO\\u2082 emitido', v:co2+'g', i:'\\ud83c\\udf2b\\ufe0f', s:yearKm+' km conducidos/a\\u00f1o'}
    ];
    var html = '';
    for (var idx = 0; idx < stats.length; idx++) {
        var x = stats[idx];
        html += '<div style="padding:16px; border-radius:12px; background:var(--ace-input-bg); border:1px solid var(--ace-border-color); text-align:center;">'
            + '<div style="font-size:1.6rem;">' + x.i + '</div>'
            + '<div style="font-size:1.3rem; font-weight:800; color:var(--ace-text); margin-top:6px;">' + x.v + '</div>'
            + '<div style="font-size:0.8rem; color:var(--ace-text-dim); margin-top:4px; text-transform:uppercase; letter-spacing:1px;">' + x.l + '</div>'
            + '<div style="font-size:0.8rem; color:var(--ace-accent); margin-top:4px;">' + x.s + '</div>'
            + '</div>';
    }
    statsEl.innerHTML = html;
}
function aceToggleComparison() {
    var card = document.getElementById('ace-comparison-card');
    var btn = document.getElementById('ace-compare-btn');
    if (!card || !btn) return;
    if (card.style.display === 'none') {
        card.style.display = 'block';
        btn.textContent = 'Ocultar comparaci\\u00f3n con B\\u00fasqueda de Google';
        btn.style.background = 'var(--ace-hover-bg)';
    } else {
        card.style.display = 'none';
        btn.textContent = 'Mostrar comparaci\\u00f3n con B\\u00fasqueda de Google';
        btn.style.background = 'transparent';
    }
}
function aceInitPrompt(){
    var el = document.getElementById('ace-prompt-count');
    if (!el) { setTimeout(aceInitPrompt, 200); return; }
    if (el.dataset.init === '1') return;
    el.dataset.init = '1';
    aceUpdatePromptCalc(1);
} aceInitPrompt();

// === Module 2: Training ===
function aceInitTraining(){
    var barsEl = document.getElementById('ace-training-bars');
    if (!barsEl) { setTimeout(aceInitTraining, 200); return; }
    if (barsEl.dataset.init === '1') return;
    barsEl.dataset.init = '1';
    var models = [
        {name:'GPT-3', energy:1287, water:700000, co2:502, year:2020, icon:'\\u{1F916}', fact:"Equivale a conducir un coche alrededor de la Tierra 60 veces"},
        {name:'GPT-4', energy:62000, water:34000000, co2:24000, year:2023, icon:'\\u{1F9E0}', fact:"Equivalente a la electricidad anual de ~6000 hogares de EE. UU."},
        {name:'Llama 3', energy:39000, water:21000000, co2:15000, year:2024, icon:'\\u{1F999}', fact:'Podr\\u00eda llenar 8 piscinas ol\\u00edmpicas con el agua utilizada'}
    ];
    var selected = -1;
    window.aceSelectModel = function(idx) {
        var btns = document.querySelectorAll('.ace-model-btn');
        var detailEl = document.getElementById('ace-model-detail');
        if (!detailEl) return;
        if (selected === idx) {
            selected = -1;
            for (var b = 0; b < btns.length; b++) {
                btns[b].style.background = 'var(--ace-input-bg)';
                btns[b].style.borderColor = 'var(--ace-border-color)';
            }
            detailEl.style.display = 'none';
            return;
        }
        selected = idx;
        for (var b = 0; b < btns.length; b++) {
            if (b === idx) {
                btns[b].style.background = 'var(--ace-accent-highlight)';
                btns[b].style.borderColor = 'var(--ace-accent)';
            } else {
                btns[b].style.background = 'var(--ace-input-bg)';
                btns[b].style.borderColor = 'var(--ace-border-color)';
            }
        }
        var m = models[idx];
        var waterM = (m.water / 1e6).toFixed(1);
        var detail = '<div class="ace-card" style="animation:aceSlideUp 0.4s ease;">'
            + '<h3 style="font-size:1.3rem; font-weight:800; color:var(--ace-accent); margin:0 0 16px 0;">' + m.icon + ' Coste de entrenamiento de ' + m.name + '</h3>'
            + '<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;">'
            + '<div style="text-align:center;"><div style="font-size:0.75rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:2px;">Energ\\u00eda</div><div style="font-size:1.6rem; font-weight:800; color:var(--ace-text); margin-top:8px;">' + m.energy.toLocaleString() + '</div><div style="font-size:0.85rem; color:var(--ace-text-dim);">MWh</div></div>'
            + '<div style="text-align:center;"><div style="font-size:0.75rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:2px;">Agua</div><div style="font-size:1.6rem; font-weight:800; color:var(--ace-text); margin-top:8px;">' + waterM + 'M</div><div style="font-size:0.85rem; color:var(--ace-text-dim);">litros</div></div>'
            + '<div style="text-align:center;"><div style="font-size:0.75rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:2px;">CO\\u2082</div><div style="font-size:1.6rem; font-weight:800; color:var(--ace-text); margin-top:8px;">' + m.co2.toLocaleString() + '</div><div style="font-size:0.85rem; color:var(--ace-text-dim);">toneladas</div></div>'
            + '</div>'
            + '<div style="margin-top:16px; padding:12px 16px; border-radius:10px; background:var(--ace-input-bg); text-align:center; font-size:1rem; color:var(--ace-text-dim);">' + m.fact + '</div>'
            + '</div>';
        detailEl.innerHTML = detail;
        detailEl.style.display = 'block';
    };
    // Training bars
    var bars = [
        {l:'GPT-3 (2020)', w:2, v:'1.287 MWh', striped:false},
        {l:'GPT-4 (2023)', w:48, v:'~62.000 MWh', striped:false},
        {l:'Siguiente gen. (2025+)', w:100, v:'???', striped:true}
    ];
    var barHtml = '';
    for (var i = 0; i < bars.length; i++) {
        var b = bars[i];
        var bg = b.striped
            ? 'repeating-linear-gradient(45deg,var(--ace-error),var(--ace-error) 10px,var(--ace-error) 10px,var(--ace-error) 20px)'
            : 'var(--ace-error)';
        barHtml += '<div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">'
            + '<div style="width:130px; font-size:0.85rem; color:var(--ace-text-dim); flex-shrink:0;">' + b.l + '</div>'
            + '<div style="flex:1; height:28px; background:var(--ace-input-bg); border-radius:6px; overflow:hidden;">'
            + '<div style="width:' + b.w + '%; height:100%; border-radius:6px; background:' + bg + '; display:flex; align-items:center; justify-content:flex-end; padding-right:8px;">'
            + '<span style="font-size:0.75rem; color:var(--ace-bar-text); font-weight:700;">' + b.v + '</span></div></div></div>';
    }
    barsEl.innerHTML = barHtml;
} aceInitTraining();

// === Module 3: Water Crisis ===
function aceInitWater(){
    var barContainer = document.getElementById('ace-water-bars');
    var quizEl = document.getElementById('ace-water-quiz');
    if (!barContainer || !quizEl) { setTimeout(aceInitWater, 200); return; }
    if (barContainer.dataset.init === '1') return;
    barContainer.dataset.init = '1';
    // Animated water bars
    var html = '';
    for (var i = 0; i < 50; i++) {
        var opacity = (0.2 + (i/50) * 0.8).toFixed(2);
        html += '<div style="width:14px; height:44px; border-radius:4px; background:var(--ace-accent); opacity:' + opacity + '; transform:scaleY(0); transform-origin:bottom; transition:transform 0.5s ease ' + (i * 0.03).toFixed(2) + 's;" class="ace-water-bar"></div>';
    }
    barContainer.innerHTML = html;
    setTimeout(function(){
        var allBars = document.querySelectorAll('.ace-water-bar');
        for (var j = 0; j < allBars.length; j++) {
            allBars[j].style.transform = 'scaleY(1)';
        }
    }, 500);
    // Water MCQ quiz
    var opts = [
        {id:'a', t:'Solo agua reciclada del oc\\u00e9ano', correct:false},
        {id:'b', t:'Agua dulce de r\\u00edos, aguas subterr\\u00e1neas y suministros municipales', correct:true},
        {id:'c', t:'Es toda agua sint\\u00e9tica fabricada en laboratorios', correct:false},
        {id:'d', t:'Agua de lluvia recogida en tejados', correct:false}
    ];
    var resultEl = document.getElementById('ace-water-quiz-result');
    var qHtml = '';
    for (var k = 0; k < opts.length; k++) {
        var o = opts[k];
        qHtml += '<button onclick="aceWaterQuizAnswer(\\'' + o.id + '\\')" id="ace-wq-' + o.id + '" class="ace-quiz-option">'
            + '<strong style="color:var(--ace-text-dim);">' + o.id.toUpperCase() + '.</strong> ' + o.t + '</button>';
    }
    quizEl.innerHTML = qHtml;
    window.aceWaterQuizAnswer = function(id) {
        var chosen = opts.filter(function(o){ return o.id === id; })[0];
        if (!chosen) return;
        for (var k = 0; k < opts.length; k++) {
            var btn = document.getElementById('ace-wq-' + opts[k].id);
            if (!btn) continue;
            if (opts[k].id === id) {
                btn.style.background = chosen.correct ? 'var(--ace-success-highlight)' : 'var(--ace-error-highlight)';
                btn.style.borderColor = chosen.correct ? 'var(--ace-success)' : 'var(--ace-error)';
            } else {
                btn.style.background = 'var(--ace-input-bg)';
                btn.style.borderColor = 'var(--ace-input-border)';
            }
        }
        if (resultEl) {
            resultEl.style.display = 'block';
            if (chosen.correct) {
                resultEl.innerHTML = '<div style="padding:16px; border-radius:12px; font-size:1rem; line-height:1.6; background:var(--ace-success-bg); color:var(--ace-success); border:1px solid var(--ace-success);">\\u00a1Correcto! La mayor\\u00eda de los centros de datos utilizan agua dulce: r\\u00edos, acu\\u00edferos subterr\\u00e1neos y suministros de agua municipales.</div>';
            } else {
                resultEl.innerHTML = '<div style="padding:16px; border-radius:12px; font-size:1rem; line-height:1.6; background:var(--ace-error-bg); color:var(--ace-error); border:1px solid var(--ace-error);">No exactamente. Los centros de datos dependen principalmente de agua dulce real de fuentes locales, la misma agua que bebe tu comunidad.</div>';
            }
        }
    };
} aceInitWater();

// === Module 4: Global Scale ===
function aceInitScale(){
    var tabsEl = document.getElementById('ace-scale-tabs');
    var bdEl = document.getElementById('ace-energy-breakdown');
    if (!tabsEl || !bdEl) { setTimeout(aceInitScale, 200); return; }
    if (tabsEl.dataset.init === '1') return;
    tabsEl.dataset.init = '1';
    var categories = [
        {l:"Energ\\u00eda total de la IA en 2025", v:'~200 TWh/a\\u00f1o', d:"Toda la electricidad del Reino Unido", i:'\\ud83c\\uddec\\ud83c\\udde7'},
        {l:"Emisiones de CO\\u2082 de la IA", v:'~56M ton/a\\u00f1o', d:"Las emisiones totales anuales de Nueva York", i:'\\ud83d\\uddfd'},
        {l:"Huella h\\u00eddrica de la IA", v:'~540 000 M L/a\\u00f1o', d:"Consumo mundial de agua embotellada", i:'\\ud83e\\uddf4'},
        {l:'Centros de datos en 2030', v:'~945 TWh', d:"Entre el total de Jap\\u00f3n y Rusia", i:'\\u26a1'}
    ];
    var activeTab = 0;
    function renderTabs() {
        var displayEl = document.getElementById('ace-scale-display');
        if (!displayEl) return;
        var tabHtml = '';
        for (var i = 0; i < categories.length; i++) {
            var isActive = i === activeTab;
            tabHtml += '<button onclick="aceSetScaleTab(' + i + ')" style="flex:1; padding:10px 4px; border-radius:10px; cursor:pointer; background:'
                + (isActive ? 'var(--ace-hover-bg)' : 'transparent')
                + '; border:2px solid ' + (isActive ? 'var(--ace-accent)' : 'var(--ace-border-color)')
                + '; color:' + (isActive ? 'var(--ace-accent)' : 'var(--ace-text-dim)')
                + '; font-size:1.3rem; transition:all 0.3s; font-family:inherit;">' + categories[i].i + '</button>';
        }
        tabsEl.innerHTML = tabHtml;
        var c = categories[activeTab];
        displayEl.innerHTML = '<div style="font-size:0.8rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:3px;">' + c.l + '</div>'
            + '<div style="font-size:clamp(2rem,6vw,3rem); font-weight:800; color:var(--ace-accent); margin-top:8px;">' + c.v + '</div>'
            + '<div style="font-size:1.1rem; color:var(--ace-text); margin-top:12px; padding:10px 20px; border-radius:12px; background:var(--ace-input-bg); display:inline-block;">' + c.d + '</div>';
    }
    window.aceSetScaleTab = function(idx) {
        activeTab = idx;
        renderTabs();
    };
    renderTabs();
    // Energy breakdown bars
    var breakdownItems = [
        {l:'Servidores (GPUs, CPUs)', p:60, c:'var(--ace-warning)'},
        {l:'Sistemas de refrigeraci\\u00f3n', p:25, c:'var(--ace-accent)'},
        {l:'Redes', p:5, c:'var(--ace-success)'},
        {l:'Almacenamiento', p:5, c:'#a78bfa'},
        {l:'Otros (iluminaci\\u00f3n, etc.)', p:5, c:'var(--ace-text-dim)'}
    ];
    var bdHtml = '';
    for (var j = 0; j < breakdownItems.length; j++) {
        var x = breakdownItems[j];
        bdHtml += '<div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">'
            + '<div style="width:140px; font-size:0.9rem; color:var(--ace-text-dim); flex-shrink:0;">' + x.l + '</div>'
            + '<div style="flex:1; height:26px; background:var(--ace-input-bg); border-radius:6px; overflow:hidden;">'
            + '<div style="width:' + x.p + '%; height:100%; background:' + x.c + '; border-radius:6px; display:flex; align-items:center; justify-content:flex-end; padding-right:8px;">'
            + '<span style="font-size:0.75rem; color:var(--ace-bar-text); font-weight:700;">' + x.p + '%</span></div></div></div>';
    }
    bdEl.innerHTML = bdHtml;
} aceInitScale();

// === Module 5: Action Plan ===
function aceInitActions(){
    var container = document.getElementById('ace-actions');
    if (!container) { setTimeout(aceInitActions, 200); return; }
    if (container.dataset.init === '1') return;
    container.dataset.init = '1';
    var actions = [
        {id:'search', l:'B\\u00fascalo en Google primero', d:"Usa un buscador normal cuando no necesites IA", p:30, i:'\\ud83d\\udd0d'},
        {id:'specific', l:'S\\u00e9 espec\\u00edfico', d:'Consultas claras = menos seguimientos = menos energ\\u00eda', p:15, i:'\\ud83c\\udfaf'},
        {id:'local', l:'Usa modelos m\\u00e1s peque\\u00f1os', d:'Los modelos de IA m\\u00e1s peque\\u00f1os consumen mucha menos energ\\u00eda para tareas simples', p:25, i:'\\ud83d\\udcf1'},
        {id:'aware', l:'Mantente informado', d:'Exige transparencia a las empresas tecnol\\u00f3gicas', p:20, i:'\\ud83d\\udce2'},
        {id:'share', l:'Cu\\u00e9ntaselo a un amigo', d:'La mayor\\u00eda de la gente no tiene ni idea de que la IA consume tanto', p:10, i:'\\ud83d\\udcac'}
    ];
    var pledged = {};
    function renderActions() {
        var html = '';
        for (var i = 0; i < actions.length; i++) {
            var a = actions[i];
            var checked = !!pledged[a.id];
            html += '<button onclick="aceToggleAction(\\'' + a.id + '\\')" style="display:flex; align-items:center; gap:14px; padding:16px 18px; border-radius:14px; cursor:pointer; text-align:left; width:100%; background:'
                + (checked ? 'var(--ace-success-highlight)' : 'var(--ace-input-bg)')
                + '; border:2px solid ' + (checked ? 'var(--ace-success)' : 'var(--ace-border-color)')
                + '; color:var(--ace-text); transition:all 0.3s; font-family:inherit; font-size:inherit;">'
                + '<div style="width:28px; height:28px; border-radius:8px; flex-shrink:0; background:' + (checked ? 'var(--ace-success)' : 'var(--ace-input-bg)') + '; border:2px solid ' + (checked ? 'var(--ace-success)' : 'var(--ace-input-border)') + '; display:flex; align-items:center; justify-content:center; color:var(--ace-bar-text); font-size:0.85rem; font-weight:700;">' + (checked ? '\\u2713' : '') + '</div>'
                + '<div style="flex:1;"><div style="font-size:1.05rem; font-weight:700;">' + a.i + ' ' + a.l + '</div><div style="font-size:0.9rem; color:var(--ace-text-dim); margin-top:2px;">' + a.d + '</div></div>'
                + '<div style="font-size:0.85rem; color:var(--ace-success); font-weight:700; opacity:' + (checked ? '1' : '0.3') + ';">-' + a.p + '%</div>'
                + '</button>';
        }
        container.innerHTML = html;
        updateScore();
    }
    function updateScore() {
        var total = 0;
        for (var key in pledged) {
            if (pledged[key]) {
                var act = actions.filter(function(a){ return a.id === key; })[0];
                if (act) total += act.p;
            }
        }
        var scoreEl = document.getElementById('ace-action-score');
        var msgEl = document.getElementById('ace-action-message');
        if (scoreEl) {
            scoreEl.textContent = total + '%';
            if (total > 50) scoreEl.style.color = 'var(--ace-success)';
            else if (total > 20) scoreEl.style.color = 'var(--ace-warning)';
            else scoreEl.style.color = 'var(--ace-text-dim)';
        }
        if (msgEl) {
            if (total === 0) msgEl.textContent = '\\u00a1Selecciona algunas acciones arriba para ver tu impacto!';
            else if (total <= 30) msgEl.textContent = '\\u00a1Buen comienzo! Cada gesto cuenta cuando miles de millones usan IA.';
            else if (total <= 60) msgEl.textContent = '\\u00a1Genial! Est\\u00e1s marcando una diferencia real.';
            else if (total <= 90) msgEl.textContent = '\\u00a1Pr\\u00e1cticamente eres un defensor de la IA sostenible!';
            else msgEl.textContent = '\\u00a1Impacto m\\u00e1ximo! Liderando el uso responsable de la IA.';
        }
    }
    window.aceToggleAction = function(id) {
        pledged[id] = !pledged[id];
        renderActions();
    };
    renderActions();
} aceInitActions();

// === Re-init after back-navigation (Gradio may re-render HTML, wiping dynamic content) ===
function _aceDoReinit(){
    var tw = document.getElementById('ace-typewriter-text');
    if (tw && !tw.textContent.trim()) { delete tw.dataset.init; aceInitTypewriter(); }
    var m1tw = document.getElementById('ace-m1-typewriter-text');
    if (m1tw && !m1tw.textContent.trim()) {
        delete m1tw.dataset.init;
        var m1c = document.getElementById('ace-m1-reveal-content');
        if (m1c) { m1c.style.opacity = '0'; m1c.style.transform = 'translateY(20px)'; }
        aceInitM1Typewriter();
    }
    var pc = document.getElementById('ace-prompt-count');
    var ps = document.getElementById('ace-prompt-stats');
    if (pc && ps && ps.children.length === 0) { delete pc.dataset.init; aceInitPrompt(); }
    var bars = document.getElementById('ace-training-bars');
    if (bars && bars.children.length === 0) { delete bars.dataset.init; aceInitTraining(); }
    var wb = document.getElementById('ace-water-bars');
    if (wb && wb.children.length === 0) { delete wb.dataset.init; aceInitWater(); }
    var tabs = document.getElementById('ace-scale-tabs');
    if (tabs && tabs.children.length === 0) { delete tabs.dataset.init; aceInitScale(); }
    var acts = document.getElementById('ace-actions');
    if (acts && acts.children.length === 0) { delete acts.dataset.init; aceInitActions(); }
}
function aceReinitAll(){
    _aceDoReinit();
    setTimeout(_aceDoReinit, 800);
}
"""

HEAD_HTML = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap">\n'
    '<script>\n' + CLIENT_JS + '\n</script>'
)


# ============================================================================
# 10. APP FACTORY
# ============================================================================

def create_bias_detective_es_sustainability_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue=theme_primary_hue),
        css=css,
        head=HEAD_HTML,
    ) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        module0_done = gr.State(value=False)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

        # Top anchor + loading overlay
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Cargando...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>Autenticando...</h2>"
                "<p>Sincronizando datos de Br\u00fajula Moral...</p>"
                "</div>"
            )

        # --- MAIN APP VIEW ---
        with gr.Column(visible=False) as main_app_col:
            # Top dashboard
            out_top = gr.HTML()

            # Module containers
            module_ui_elements = {}
            quiz_wiring_queue = []

            for i, mod in enumerate(MODULES):
                with gr.Column(
                    elem_id=f"module-{i}",
                    elem_classes=["module-container"],
                    visible=(i == 0),
                ) as mod_col:
                    gr.HTML(mod["html"])

                    # Quiz content — only for modules in QUIZ_CONFIG (2-5)
                    if i in QUIZ_CONFIG:
                        q_data = QUIZ_CONFIG[i]

                        gr.HTML(
                            "<div class='quiz-cta'>"
                            "<span class='points-chip'>\U0001f9ed Puntos de Br\u00fajula Moral disponibles</span>"
                            "<span>Responde para aumentar tu puntuaci\u00f3n</span>"
                            "</div>"
                        )

                        gr.Markdown(f"### \U0001f9e0 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Selecciona tu respuesta:",
                            elem_classes=["quiz-radio-large"],
                        )
                        feedback = gr.HTML("")
                        quiz_wiring_queue.append((i, radio, feedback))

                    # Navigation buttons
                    with gr.Row():
                        btn_prev = gr.Button("\u2b05\ufe0f Anterior", visible=(i > 0))
                        next_label = (
                            "Siguiente \u25b6\ufe0f"
                            if i < len(MODULES) - 1
                            else "CONTINUAR A LA ACTIVIDAD 7 →"
                        )
                        btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            gr.HTML("""
                <details style="background:var(--background-fill-secondary); border-radius:16px;
                                border:1px solid var(--border-color-primary); margin:8px 0 12px 0; opacity:0.7;">
                    <summary style="padding:14px 24px; cursor:pointer; text-transform:uppercase; letter-spacing:1.5px;
                                    color:var(--body-text-color-subdued); font-size:0.78rem; font-weight:700;
                                    text-align:center; list-style:none;">
                        &#9656; La F&oacute;rmula de la Br&uacute;jula Moral
                    </summary>
                    <div style="padding:0 24px 24px 24px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:700; margin:12px 0; font-family:'Outfit',sans-serif;">
                            Puntuaci&oacute;n Br&uacute;jula Moral =
                            <span style="background:rgba(5,150,105,0.15); color:var(--ace-success); padding:4px 10px; border-radius:6px;">
                                [ Precisi&oacute;n ]</span>
                            &times;
                            <span style="background:rgba(2,132,199,0.15); color:var(--ace-accent); padding:4px 10px; border-radius:6px;">
                                [ Sostenibilidad % ]</span>
                        </div>
                        <p style="font-size:0.95rem; margin:12px 0 0 0; color:var(--body-text-color-subdued);">
                            <strong>Sostenibilidad %</strong> refleja tu progreso de Br&uacute;jula Moral a trav&eacute;s de la investigaci&oacute;n.<br/>
                            Si tu Sostenibilidad % es <strong>0%</strong>, tu Puntuaci&oacute;n Br&uacute;jula Moral es <strong>0</strong>.
                        </p>
                    </div>
                </details>
            """)

            # Leaderboard at bottom
            leaderboard_html = gr.HTML()

            # --- WIRING: QUIZ LOGIC ---
            for mod_id, radio_comp, feedback_comp in quiz_wiring_queue:

                def quiz_logic_wrapper(
                    user, tok, team, acc_val, task_list, ans, mid=mod_id
                ):
                    cfg = QUIZ_CONFIG[mid]
                    if ans == cfg["a"]:
                        prev, curr, _, new_tasks = trigger_api_update(
                            user, tok, team, mid, acc_val, task_list, cfg["t"]
                        )
                        msg = generate_success_message(prev, curr, cfg["success"])
                        return (
                            render_top_dashboard(curr, mid),
                            render_leaderboard_card(curr, user, team),
                            msg,
                            new_tasks,
                        )
                    else:
                        return (
                            gr.update(),
                            gr.update(),
                            "<div class='hint-box' style='border-color:red;'>"
                            "\u274c No del todo. Relee las pruebas anteriores y piensa en lo que los datos muestran espec\u00edficamente.</div>",
                            task_list,
                        )

                radio_comp.change(
                    fn=quiz_logic_wrapper,
                    inputs=[username_state, token_state, team_state, accuracy_state, task_list_state, radio_comp],
                    outputs=[out_top, leaderboard_html, feedback_comp, task_list_state],
                )

        # --- LOAD HANDLER ---
        def handle_load(request: gr.Request):
            ok, uname, tok = _try_session_based_auth(request)
            if ok:
                best_acc, fetched_team = fetch_user_history(uname, tok)
                team = "Team-Unassigned"
                fetched_tasks: List[str] = []

                os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
                client = MoralcompassApiClient(
                    api_base_url=DEFAULT_API_URL, auth_token=tok
                )

                # Resolve team from existing server record
                def get_or_assign_team(client_obj, username_val):
                    try:
                        user_data = client_obj.get_user(
                            table_id=TABLE_ID, username=username_val
                        )
                    except Exception:
                        user_data = None
                    if user_data and isinstance(user_data, dict):
                        if user_data.get("teamName"):
                            return user_data["teamName"]
                    return "team-a"

                exist_team = get_or_assign_team(client, uname)
                if fetched_team != "Team-Unassigned":
                    team = fetched_team
                elif exist_team != "team-a":
                    team = exist_team
                else:
                    team = "team-a"

                # Fetch completedTaskIds from server via get_user()
                try:
                    user_stats = client.get_user(table_id=TABLE_ID, username=uname)
                except Exception:
                    user_stats = None

                if user_stats:
                    if isinstance(user_stats, dict):
                        fetched_tasks = user_stats.get("completedTaskIds") or []
                    else:
                        fetched_tasks = getattr(
                            user_stats, "completed_task_ids", []
                        ) or []

                # Sync baseline moral compass record
                try:
                    client.update_moral_compass(
                        table_id=TABLE_ID,
                        username=uname,
                        team_name=team,
                        metrics={"accuracy": best_acc},
                        tasks_completed=len(fetched_tasks),
                        total_tasks=TOTAL_COURSE_TASKS,
                        primary_metric="accuracy",
                        completed_task_ids=fetched_tasks,
                    )
                    time.sleep(1.0)
                except Exception:
                    pass

                data, _ = ensure_table_and_get_data(
                    uname, tok, team, fetched_tasks
                )
                return (
                    uname, tok, team, False,
                    render_top_dashboard(data, 0),
                    render_leaderboard_card(data, uname, team),
                    best_acc, fetched_tasks,
                    gr.update(visible=False),
                    gr.update(visible=True),
                )
            return (
                None, None, None, False,
                "<div class='hint-box'>Autenticaci\u00f3n fallida. Por favor, accede desde el enlace del curso.</div>",
                "", 0.0, [],
                gr.update(visible=False),
                gr.update(visible=True),
            )

        demo.load(
            handle_load, None,
            [
                username_state, token_state, team_state, module0_done,
                out_top, leaderboard_html, accuracy_state, task_list_state,
                loader_col, main_app_col,
            ],
        )

        # --- JAVASCRIPT HELPER ---
        def nav_js(target_id: str, message: str) -> str:
            return f"""
            ()=>{{
              try {{
                const overlay = document.getElementById('nav-loading-overlay');
                const messageEl = document.getElementById('nav-loading-text');
                if(overlay && messageEl) {{
                  messageEl.textContent = '{message}';
                  overlay.style.display = 'flex';
                  setTimeout(() => {{ overlay.style.opacity = '1'; }}, 10);
                }}
                const startTime = Date.now();
                setTimeout(() => {{
                  const anchor = document.getElementById('app_top_anchor');
                  if(anchor) anchor.scrollIntoView({{behavior:'smooth', block:'start'}});
                }}, 40);
                const targetId = '{target_id}';
                const pollInterval = setInterval(() => {{
                  const elapsed = Date.now() - startTime;
                  const target = document.getElementById(targetId);
                  const isVisible = target && target.offsetParent !== null &&
                                   window.getComputedStyle(target).display !== 'none';
                  if((isVisible && elapsed >= 1200) || elapsed > 7000) {{
                    clearInterval(pollInterval);
                    if(overlay) {{
                      overlay.style.opacity = '0';
                      setTimeout(() => {{ overlay.style.display = 'none'; }}, 300);
                    }}
                    setTimeout(function(){{ if(typeof aceReinitAll==='function') aceReinitAll(); }}, 300);
                  }}
                }}, 90);
              }} catch(e) {{ console.warn('nav-js error', e); }}
            }}
            """

        # --- NAVIGATION ---
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]

            if i > 0:
                prev_col = module_ui_elements[i - 1][0]
                prev_target_id = f"module-{i-1}"

                def make_prev_dashboard_handler(prev_idx):
                    def wrapper_prev(user, tok, team, tasks):
                        data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                        return render_top_dashboard(data, prev_idx)
                    return wrapper_prev

                def make_prev_nav_generator(p_col, c_col):
                    def navigate_prev():
                        yield gr.update(visible=False), gr.update(visible=False)
                        yield gr.update(visible=True), gr.update(visible=False)
                    return navigate_prev

                prev_btn.click(
                    fn=make_prev_dashboard_handler(i - 1),
                    inputs=[username_state, token_state, team_state, task_list_state],
                    outputs=[out_top],
                    js=nav_js(prev_target_id, "Cargando..."),
                ).then(
                    fn=make_prev_nav_generator(prev_col, curr_col),
                    outputs=[prev_col, curr_col],
                )

            if i < len(MODULES) - 1:
                next_col = module_ui_elements[i + 1][0]
                next_target_id = f"module-{i+1}"

                def make_next_handler(c_col, n_col, next_idx):
                    def wrapper_next(user, tok, team, tasks):
                        data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                        dash_html = render_top_dashboard(data, next_idx)
                        return dash_html
                    return wrapper_next

                def make_nav_generator(c_col, n_col):
                    def navigate_next():
                        yield gr.update(visible=False), gr.update(visible=False)
                        yield gr.update(visible=False), gr.update(visible=True)
                    return navigate_next

                next_btn.click(
                    fn=make_next_handler(curr_col, next_col, i + 1),
                    inputs=[username_state, token_state, team_state, task_list_state],
                    outputs=[out_top],
                    js=nav_js(next_target_id, "Cargando..."),
                ).then(
                    fn=make_nav_generator(curr_col, next_col),
                    outputs=[curr_col, next_col],
                )

        # Navigate to next activity from last module
        last_idx = len(MODULES) - 1
        _, _, last_next = module_ui_elements[last_idx]
        last_next.click(
            fn=None,
            js="() => { try { window.parent.postMessage('navigate-to-activity-7', '*'); } catch(e) {} }"
        )

        return demo

# ============================================================================
# LAUNCH
# ============================================================================

def launch_bias_detective_es_sustainability_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    app = create_bias_detective_es_sustainability_app(theme_primary_hue=theme_primary_hue)
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        **kwargs
    )


if __name__ == "__main__":
    launch_bias_detective_es_sustainability_app(share=False, debug=True, height=1000)

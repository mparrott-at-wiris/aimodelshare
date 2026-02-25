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
    "ca": {
        "The Climate Guardians": "Els Guardians del Clima",
        "United Eco-Architects": "Eco-Arquitectes Units",
        "The Energy Detectives": "Els Detectius de l'Energia",
        "The Sustainability League": "La Lliga de la Sostenibilitat",
        "Green Future Engineers": "Enginyers del Futur Verd",
        "Zero Carbon Avengers": "Els Venjadors del Carboni Zero",
    },
}
UI_TEAM_LANG = "ca"


def translate_team_name_for_display(english_name: str, lang: str = "ca") -> str:
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
        "title": "El cost ocult de la IA",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-intro-page">
                    <div class="ace-reveal" style="animation-delay:0s;">
                        <div style="font-size:0.875rem; font-weight:800; letter-spacing:3px; color:var(--ace-accent); text-transform:uppercase; margin-bottom:24px; text-align:center;">
                            Experi&egrave;ncia d'aprenentatge interactiva
                        </div>
                    </div>
                    <div class="ace-reveal" style="animation-delay:0.3s;">
                        <h1 style="font-size:clamp(2rem, 7vw, 3.2rem); font-weight:800; text-align:center; line-height:1.1; letter-spacing:-1px; color:var(--ace-text); margin:0 0 28px 0;">
                            Qu&egrave; li costa<br/>realment la IA <span style="color:var(--ace-accent);">al planeta?</span>
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
        "title": "El teu principi rector",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div style="background:var(--ace-accent-highlight); border-left:4px solid var(--ace-accent); border-radius:16px; padding:20px 24px; margin-bottom:8px;">
                        <p style="margin:0; font-size:1.05rem; line-height:1.6; color:var(--ace-text);">
                            <strong style="color:var(--ace-accent);">Sostenibilitat: El teu principi rector.</strong><br>
                            La IA &eacute;s poderosa, per&ograve; el poder comporta responsabilitat. Abans de construir IA, ens hem de preguntar: aix&ograve; &eacute;s bo per a les persones i el planeta? Experts de l'Observatori d'&Egrave;tica en Intel&middot;lig&egrave;ncia Artificial de Catalunya <strong>OEIAC (UdG)</strong> van crear 7 principis per construir IA de manera segura. En aquesta investigaci&oacute;, et centrar&agrave;s en un:
                        </p>
                        <p style="margin:16px 0 0 0; font-size:1.1rem; line-height:1.6; color:var(--ace-text);">
                            <strong>Sostenibilitat</strong> &mdash; Una part fonamental del principi de sostenibilitat &eacute;s que els sistemes d'IA no han de causar danys a llarg termini al medi ambient.
                        </p>
                        <p style="margin:16px 0 0 0; font-size:1.05rem; line-height:1.6; color:var(--ace-accent); font-weight:600;">
                            La teva missi&oacute;? Descobrir qu&egrave; li costa realment la IA al planeta.
                        </p>
                    </div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.15s;">
                    <details style="background:var(--ace-input-bg); border:1px solid var(--ace-border-color); border-radius:16px; padding:16px 20px; cursor:pointer;">
                        <summary style="font-weight:700; color:var(--ace-text-dim); font-size:0.95rem;">&#128736;&#65039; Refer&egrave;ncia: Altres principis d'&egrave;tica en IA (OEIAC)</summary>
                        <div style="margin-top:15px; font-size:0.9rem; display:grid; grid-template-columns:1fr 1fr; gap:15px; color:var(--ace-text);">
                            <div>
                                <strong>Just&iacute;cia i equitat</strong><br>Assegurar que la IA tracti tots els grups de manera justa i no discrimini.<br><br>
                                <strong>Transpar&egrave;ncia i explicabilitat</strong><br>Fer que el raonament de la IA sigui clar perqu&egrave; les decisions es puguin inspeccionar.<br><br>
                                <strong>Seguretat i no-malefic&egrave;ncia</strong><br>Minimitzar errors nocius; planificar per a fallades.
                            </div>
                            <div>
                                <strong>Responsabilitat i rendici&oacute; de comptes</strong><br>Assignar propietaris clars i mantenir rastres d'auditoria.<br><br>
                                <strong>Autonomia</strong><br>Proporcionar processos d'apel&middot;laci&oacute; i alternatives a les decisions de la IA.<br><br>
                                <strong>Privacitat</strong><br>Utilitzar nom&eacute;s les dades necess&agrave;ries; justificar l'&uacute;s d'atributs sensibles.
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
        "title": "Cada consulta compta",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">01 / Cada consulta compta</div>
                    <h2 class="ace-heading" style="min-height:2.4em;"><span id="ace-m1-typewriter-text"></span><span style="display:inline-block; width:2px; height:1.1em; background:var(--ace-accent); margin-left:2px; animation:aceBlink 0.7s step-end infinite; vertical-align:text-bottom;"></span></h2>
                </div>
                <div id="ace-m1-reveal-content" style="opacity:0; transform:translateY(20px); transition:opacity 0.6s ease, transform 0.6s ease;">
                    <p class="ace-paragraph">Investigadors de la UC Riverside van descobrir que una consulta d'IA (una pregunta o instrucci&oacute; que escrius a un xatbot com ChatGPT) de ~100 paraules consumeix aproximadament <strong style="color:var(--ace-text); font-weight:600;">mig litre d'aigua</strong> &mdash; m&eacute;s o menys una ampolla est&agrave;ndard. Aquesta aigua refrigera els enormes xips dels servidors. I pel que fa a l'energia, el consum &eacute;s similar al de mirar la televisi&oacute; durant uns <strong style="color:var(--ace-text); font-weight:600;">9 segons</strong>.</p>
                    <p class="ace-paragraph" style="font-size:1rem;">No sembla gaire, oi? Per&ograve; pensa en quantes consultes envies al dia...</p>
                    <div class="ace-card">
                        <label style="display:block; font-size:1rem; color:var(--ace-text-dim); margin-bottom:16px; font-weight:600;">Quantes consultes d'IA envies al dia?</label>
                        <input type="range" id="ace-prompt-slider" min="1" max="200" value="1" style="width:100%; cursor:pointer;" oninput="aceUpdatePromptCalc(this.value)">
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:var(--ace-text-dim); margin-top:8px;">
                            <span>1</span><span>50</span><span>100</span><span>150</span><span>200</span>
                        </div>
                        <div id="ace-prompt-count" style="font-size:2.5rem; font-weight:800; color:var(--ace-accent); text-align:center; margin-top:20px;">1 consulta/dia</div>
                        <div id="ace-prompt-stats" style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-top:20px;">
                        </div>
                    </div>
                    <button onclick="aceToggleComparison()" id="ace-compare-btn" style="margin-top:20px; padding:12px 20px; font-size:0.95rem; font-weight:600; background:transparent; border:1px solid var(--ace-input-border); border-radius:12px; color:var(--ace-accent); cursor:pointer; transition:all 0.3s; font-family:'Outfit',sans-serif;">
                        Mostra comparaci&oacute; amb la Cerca de Google
                    </button>
                    <div id="ace-comparison-card" style="display:none; margin-top:16px;">
                        <div class="ace-card">
                            <div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
                                <div style="flex:1; min-width:150px;">
                                    <div style="font-size:0.85rem; color:var(--ace-text-dim); font-weight:600; text-transform:uppercase; letter-spacing:1px;">Cerca a Google</div>
                                    <div style="display:flex; align-items:center; gap:8px; margin-top:8px;">
                                        <div style="height:22px; width:40px; background:var(--ace-success); border-radius:4px;"></div>
                                        <span style="color:var(--ace-text-dim); font-size:1rem;">~0,3 Wh</span>
                                    </div>
                                </div>
                                <div style="flex:1; min-width:150px;">
                                    <div style="font-size:0.85rem; color:var(--ace-text-dim); font-weight:600; text-transform:uppercase; letter-spacing:1px;">Consulta d'IA</div>
                                    <div style="display:flex; align-items:center; gap:8px; margin-top:8px;">
                                        <div style="height:22px; width:200px; background:var(--ace-accent); border-radius:4px;"></div>
                                        <span style="color:var(--ace-text-dim); font-size:1rem;">~10 Wh</span>
                                    </div>
                                </div>
                            </div>
                            <p class="ace-paragraph" style="margin-top:16px; margin-bottom:0; font-size:1rem;">Una consulta d'IA consumeix aproximadament <strong style="color:var(--ace-text); font-weight:600;">30 vegades m&eacute;s energia</strong> que una cerca tradicional a Google.</p>
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
        "title": "Entrenar la b\u00e8stia",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">02 / Entrenar la b&egrave;stia</div>
                    <h2 class="ace-heading">Abans d'escriure la teva primera consulta, <span style="color:var(--ace-error);">ja s'havien consumit milions de MWh</span></h2>
                </div>
                <div class="ace-reveal" style="animation-delay:0.2s;">
                    <p class="ace-paragraph">Entrenar un gran model d'IA implica alimentar-lo amb enormes quantitats de dades &mdash; llibres, p&agrave;gines web, codi &mdash; durant setmanes, utilitzant milers de GPU funcionant les 24 hores del dia. Nom&eacute;s l'entrenament de GPT-3 va consumir prou electricitat per <strong style="color:var(--ace-text); font-weight:600;">abastir 120 llars dels Estats Units durant un any</strong>.</p>
                    <p class="ace-paragraph">Per&ograve; l'entrenament nom&eacute;s passa un cop. Despr&eacute;s, 200 milions de persones el fan servir cada dia &mdash; i totes aquelles petites consultes sumen <strong style="color:var(--ace-text); font-weight:600;">molta m&eacute;s energia</strong> de la que va costar l'entrenament.</p>
                </div>
                <div class="ace-reveal" style="animation-delay:0.4s;">
                    <div style="font-size:1rem; color:var(--ace-text-dim); margin-bottom:12px; font-weight:600;">Prem un model per veure la seva petjada d'entrenament</div>
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
                    <div style="margin-top:32px; font-size:1rem; color:var(--ace-text-dim); margin-bottom:16px; font-weight:600;">El consum energ&egrave;tic de l'entrenament s'ha disparat:</div>
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
        "title": "Aigua: el cost ocult",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">03 / Aigua: el cost ocult</div>
                    <h2 class="ace-heading">La IA podria consumir tanta aigua com <span style="color:var(--ace-accent);">tota l'aigua embotellada del m&oacute;n</span></h2>
                </div>
                <div class="ace-reveal" style="animation-delay:0.2s;">
                    <p class="ace-paragraph">Un estudi de 2025 estima que la petjada h&iacute;drica global de la IA podria situar-se entre <strong style="color:var(--ace-text); font-weight:600;">312 i 764 mil milions de litres anuals</strong> &mdash; una quantitat comparable al consum mundial d'aigua embotellada en un any.</p>
                    <p class="ace-paragraph">Al mateix temps, els centres de dades utilitzen cada cop m&eacute;s aigua dol&ccedil;a per refrigerar els seus sistemes, incrementant la pressi&oacute; sobre els recursos locals.</p>
                    <p class="ace-paragraph">I tot aix&ograve; quan nom&eacute;s el <strong style="color:var(--ace-accent); font-weight:700;">0,5% de l'aigua del m&oacute;n</strong> &eacute;s dol&ccedil;a i accessible.</p>
                </div>
                <div class="ace-reveal" style="animation-delay:0.4s;">
                    <div class="ace-card">
                        <div style="text-align:center; font-size:1rem; color:var(--ace-text-dim); margin-bottom:20px; font-weight:600;">&Uacute;s anual d'aigua per la IA, visualitzat</div>
                        <div id="ace-water-bars" style="display:flex; justify-content:center; gap:3px; flex-wrap:wrap;"></div>
                        <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:0.8rem; color:var(--ace-text-dim);">
                            <span>0</span><span>Cada barra = ~15 mil milions de litres</span><span>764 000 M L</span>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:20px;">
                            <div style="padding:16px; border-radius:12px; background:var(--ace-input-bg); border:1px solid var(--ace-border-color); text-align:center;">
                                <div style="font-size:1.8rem;">&#127963;&#65039;</div>
                                <div style="font-size:1.1rem; font-weight:700; color:var(--ace-text); margin-top:6px;">19 M litres/dia</div>
                                <div style="font-size:0.8rem; color:var(--ace-text-dim); margin-top:4px;">Un gran centre de dades</div>
                                <div style="font-size:0.8rem; color:var(--ace-accent); margin-top:2px;">= una ciutat de 50 000 habitants</div>
                            </div>
                            <div style="padding:16px; border-radius:12px; background:var(--ace-input-bg); border:1px solid var(--ace-border-color); text-align:center;">
                                <div style="font-size:1.8rem;">&#127758;</div>
                                <div style="font-size:1.1rem; font-weight:700; color:var(--ace-text); margin-top:6px;">56% de d&egrave;ficit per al 2030</div>
                                <div style="font-size:0.8rem; color:var(--ace-text-dim); margin-top:4px;">Bretxa global d'aigua dol&ccedil;a</div>
                                <div style="font-size:0.8rem; color:var(--ace-accent); margin-top:2px;">La IA ho est&agrave; empitjorant</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.6s;">
                    <div class="ace-card" style="margin-top:24px;">
                        <div style="font-size:1.1rem; font-weight:700; color:var(--ace-text); margin-bottom:12px;">Pregunta r&agrave;pida: D'on ve l'aigua de refrigeraci&oacute; dels centres de dades?</div>
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
        "title": "Visi\u00f3 global",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">04 / Visi&oacute; global</div>
                    <h2 class="ace-heading">El consum energ&egrave;tic de la IA &eacute;s comparable a la de <span style="color:var(--ace-warning);">pa&iuml;sos sencers</span></h2>
                </div>
                <div class="ace-reveal" style="animation-delay:0.2s;">
                    <p class="ace-paragraph">Els centres de dades ja consumeixen aproximadament l'<strong style="color:var(--ace-text); font-weight:600;">1,5% de l'electricitat mundial</strong> &mdash; i es preveu que gaireb&eacute; es tripliqui per al 2030. Nom&eacute;s els EUA allotgen el 45,6% dels centres de dades del m&oacute;n.</p>
                </div>
                <div class="ace-reveal" style="animation-delay:0.4s;">
                    <div class="ace-card">
                        <div id="ace-scale-tabs" style="display:flex; gap:8px; margin-bottom:20px;"></div>
                        <div id="ace-scale-display" style="text-align:center;"></div>
                    </div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.6s;">
                    <div style="margin-top:28px; font-size:1rem; color:var(--ace-text-dim); margin-bottom:16px; font-weight:600;">On va l'energia dins d'un centre de dades?</div>
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
        "title": "El teu torn",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="ace-reveal" style="animation-delay:0s;">
                    <div class="ace-section-label">05 / El teu torn</div>
                    <h2 class="ace-heading">Ara que coneixes l'impacte, <span style="color:var(--ace-success);">qu&egrave; pots fer realment?</span></h2>
                </div>
                <div class="ace-reveal" style="animation-delay:0.2s;">
                    <p class="ace-paragraph">Ning&uacute; diu que deixis d'usar la IA &mdash; &eacute;s incre&iuml;blement potent. Per&ograve; ser <strong style="color:var(--ace-text); font-weight:600;">conscient</strong> de com la fas servir marca una difer&egrave;ncia real quan es multiplica per milers de milions d'usuaris.</p>
                </div>
                <div class="ace-reveal" style="animation-delay:0.4s;">
                    <div id="ace-actions" style="display:grid; gap:10px;"></div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.6s;">
                    <div class="ace-card" style="margin-top:24px; text-align:center;" id="ace-score-card">
                        <div style="font-size:0.8rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:3px;">La teva reducci&oacute; potencial de petjada</div>
                        <div id="ace-action-score" style="font-size:3.5rem; font-weight:800; color:var(--ace-text-dim); margin-top:8px; transition:color 0.3s;">0%</div>
                        <p id="ace-action-message" class="ace-paragraph" style="margin-top:8px; margin-bottom:0; text-align:center; font-size:1rem;">Selecciona algunes accions a dalt per veure el teu impacte!</p>
                    </div>
                </div>
                <div class="ace-reveal" style="animation-delay:0.8s;">
                    <div class="ace-card" style="margin-top:24px; text-align:center; border:2px solid var(--ace-success);">
                        <div style="font-size:1.2rem; font-weight:800; color:var(--ace-text);">La conclusi&oacute;</div>
                        <p class="ace-paragraph" style="margin-top:12px; margin-bottom:0; text-align:center; max-width:480px; margin-left:auto; margin-right:auto;">La IA &eacute;s potent. La IA &eacute;s &uacute;til. Per&ograve; la IA <strong style="color:var(--ace-accent); font-weight:700;">no &eacute;s gratu&iuml;ta</strong>. Cada consulta costa aigua i energia reals. Ser conscient &eacute;s el primer pas &mdash; i tu acabes de fer-lo.</p>
                        <div style="font-size:0.8rem; color:var(--ace-text-dim); margin-top:16px;">Fonts: UC Riverside, IEA, MIT, VU Amsterdam (2024&ndash;2025)</div>
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
        "q": "Un amic diu: *\u2018Una pregunta a la IA nom\u00e9s gasta una ampolla d\u2019aigua \u2014 a qui li importa?\u2019* Per qu\u00e8 t\u2019hauria d\u2019importar?",
        "o": [
            "A) El teu amic t\u00e9 ra\u00f3 \u2014 una ampolla no \u00e9s res.",
            "B) Una pregunta \u00e9s petita, per\u00f2 200 milions de persones fent m\u00e9s de 50 preguntes al dia sumen milers de milions d\u2019ampolles d\u2019aigua cada any. Les coses petites es tornen enormes quan tothom les fa.",
            "C) L\u2019aigua no importa \u2014 el veritable problema \u00e9s nom\u00e9s l\u2019electricitat.",
        ],
        "a": "B) Una pregunta \u00e9s petita, per\u00f2 200 milions de persones fent m\u00e9s de 50 preguntes al dia sumen milers de milions d\u2019ampolles d\u2019aigua cada any. Les coses petites es tornen enormes quan tothom les fa.",
        "success": "<strong>Encertat!</strong> Una pregunta \u00e9s petita. Per\u00f2 200 milions de persones fent m\u00e9s de 50 preguntes al dia? Aix\u00f2 s\u2019acumula r\u00e0pid.",
    },
    3: {
        "t": "t2",
        "q": "Entrenar un model d\u2019IA com GPT-4 fa servir una quantitat enorme d\u2019energia \u2014 com donar electricitat a 6.000 cases durant un any. Per\u00f2 despr\u00e9s de l\u2019entrenament, 200 milions de persones el fan servir cada dia. Qu\u00e8 gasta m\u00e9s energia amb el temps \u2014 construir la IA o que tothom la faci servir?",
        "o": [
            "A) Construir-la gasta m\u00e9s \u2014 l\u2019entrenament \u00e9s la part cara.",
            "B) Que tothom la faci servir gasta molt\u00edssim m\u00e9s. Cada pregunta costa una mica d\u2019energia, per\u00f2 milions de persones preguntant tot el dia, cada dia, sumen molt m\u00e9s que l\u2019entrenament.",
            "C) S\u00f3n m\u00e9s o menys iguals.",
        ],
        "a": "B) Que tothom la faci servir gasta molt\u00edssim m\u00e9s. Cada pregunta costa una mica d\u2019energia, per\u00f2 milions de persones preguntant tot el dia, cada dia, sumen molt m\u00e9s que l\u2019entrenament.",
        "success": "<strong>Exacte!</strong> Entrenar GPT-3 va costar mesos d\u2019energia. Un cop la gent va comen\u00e7ar a fer-lo servir, van gastar la mateixa quantitat en nom\u00e9s 11 dies.",
    },
    4: {
        "t": "t3",
        "q": "Un sol centre de dades consumeix 19 milions de litres d\u2019aigua dol\u00e7a cada dia. Aquesta aigua ve dels mateixos rius i pous dels quals beu la gent de la zona. Per qu\u00e8 \u00e9s un problema?",
        "o": [
            "A) No ho \u00e9s \u2014 el centre de dades paga per l\u2019aigua, aix\u00ed que \u00e9s just.",
            "B) En llocs on l\u2019aigua escasseja, les fam\u00edlies ja estan retallant. Un centre de dades bevent milions de litres al dia ho fa encara m\u00e9s dif\u00edcil per a tothom.",
            "C) L\u2019aigua torna a l\u2019aire com a vapor, aix\u00ed que en realitat no es perd.",
        ],
        "a": "B) En llocs on l\u2019aigua escasseja, les fam\u00edlies ja estan retallant. Un centre de dades bevent milions de litres al dia ho fa encara m\u00e9s dif\u00edcil per a tothom.",
        "success": "<strong>Aix\u00ed \u00e9s.</strong> A Mesa, Arizona, les fam\u00edlies escur\u00e7aven les dutxes durant una gran sequera \u2014 mentre un centre de dades de Microsoft a prop convertia 212 milions de litres de la seva aigua en vapor cada any.",
    },
    5: {
        "t": "t4",
        "q": "Els centres de dades d'IA ja consumeixen al voltant de l'1,5% de tota l'electricitat del m\u00f3n \u2014 i s'espera que gaireb\u00e9 es tripliqui per al 2030. El 2022, Dubl\u00edn (la capital d'Irlanda) va prohibir nous centres de dades perqu\u00e8 estaven fent servir tanta electricitat que les llars i els negocis podrien quedar-se sense prou. **Qu\u00e8 ens diu aix\u00f2?**",
        "o": [
            "A) Els centres de dades s'haurien de prohibir a tot arreu \u2014 fan servir massa electricitat i no val la pena.",
            "B) La IA ja fa servir tanta electricitat que competeix amb pa\u00efsos sencers per l'energia, i els governs han de prendre decisions dif\u00edcils al respecte.",
            "C) Dubl\u00edn va reaccionar de manera exagerada \u2014 l'1,5% no \u00e9s tant, i l'energia solar i e\u00f2lica creixeran prou per si soles.",
        ],
        "a": "B) La IA ja fa servir tanta electricitat que competeix amb pa\u00efsos sencers per l'energia, i els governs han de prendre decisions dif\u00edcils al respecte.",
        "success": "La IA ja consumeix tanta electricitat com pa\u00efsos sencers \u2014 i creix m\u00e9s r\u00e0pidament del que les energies renovables poden seguir.",
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
        header_title = "Ja ets a la classificaci\u00f3!"
        summary_line = "Acabes d'obtenir la teva primera puntuaci\u00f3 de Br\u00faix. Moral \u2014 ja formes part del r\u00e0nquing global."
        cta_line = "Segueix investigant per escalar a la classificaci\u00f3."
    elif style_key == "major":
        header_emoji = "\U0001f525"
        header_title = "Gran impuls a la Br\u00faixola Moral!"
        summary_line = "La teva an\u00e0lisi ha tingut un gran impacte \u2014 acabes d'avan\u00e7ar altres detectius."
        cta_line = "Continua la teva investigaci\u00f3 per mantenir l'impuls."
    elif style_key == "climb":
        header_emoji = "\U0001f680"
        header_title = "Est\u00e0s pujant a la classificaci\u00f3"
        summary_line = "Bona feina \u2014 has superat altres participants."
        cta_line = "Prem SEG\u00dcENT per continuar la teva investigaci\u00f3."
    elif style_key == "tight":
        header_emoji = "\U0001f4ca"
        header_title = "La classificaci\u00f3 est\u00e0 canviant"
        summary_line = "Altres equips tamb\u00e9 es mouen. Unes quantes respostes m\u00e9s s\u00f2lides et diferenciaran."
        cta_line = "Afronta el seg\u00fcent pas per enfortir la teva posici\u00f3."
    else:
        header_emoji = "\u2705"
        header_title = "Progr\u00e9s registrat"
        summary_line = "El teu coneixement sobre sostenibilitat ha augmentat la teva puntuaci\u00f3 de Br\u00faixola Moral."
        cta_line = "Prova el seg\u00fcent pas per seguir escalant."

    if style_key == "first":
        score_line = f"\U0001f9ed Puntuaci\u00f3: <strong>{new_score:.3f}</strong>"
        rank_line = f"\U0001f3c5 Posici\u00f3 inicial: <strong>#{new_rank}</strong>"
    else:
        score_line = (
            f"\U0001f9ed Puntuaci\u00f3: {old_score:.3f} \u2192 <strong>{new_score:.3f}</strong> "
            f"(+{diff_score:.3f})"
        )
        if ranks_are_int:
            if old_rank == new_rank:
                rank_line = f"\U0001f4ca Posici\u00f3: <strong>#{new_rank}</strong> (mantenint-se)"
            elif rank_diff > 0:
                rank_line = f"\U0001f4c8 Posici\u00f3: #{old_rank} \u2192 <strong>#{new_rank}</strong> (+{rank_diff} llocs)"
            else:
                rank_line = f"\U0001f53b Posici\u00f3: #{old_rank} \u2192 <strong>#{new_rank}</strong> ({rank_diff} llocs)"
        else:
            rank_line = f"\U0001f4ca Posici\u00f3: <strong>#{new_rank}</strong>"

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
        phase_label = "FASE 1: Impacte individual"
        phase_color = "#6366f1"
    else:
        phase_label = "FASE 2: Escala global"
        phase_color = "#ef4444"

    return f"""
    <div class="summary-box">
        <div class="summary-box-inner">
            <div class="summary-metrics">
                <div style="text-align:center;">
                    <div class="label-text">Puntuaci\u00f3 Br\u00faixola Moral</div>
                    <div class="score-text-primary">\U0001f9ed {display_score:.3f}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Posici\u00f3 de l'equip</div>
                    <div class="score-text-team">{team_rank_display}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Posici\u00f3 global</div>
                    <div class="score-text-global">{rank_display}</div>
                </div>
            </div>
            <div class="summary-progress">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="progress-label">Progr\u00e9s de la investigaci\u00f3: {progress_pct}%</div>
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
        <h3 class="slide-title" style="margin-bottom:10px;">\U0001f4ca Classificaci\u00f3 en directe</h3>
        <div class="lb-tabs">
            <input type="radio" id="lb-tab-team" name="lb-tabs" checked>
            <label for="lb-tab-team" class="lb-tab-label">\U0001f3c6 Equip</label>
            <input type="radio" id="lb-tab-user" name="lb-tabs">
            <label for="lb-tab-user" class="lb-tab-label">\U0001f464 Individual</label>
            <div class="lb-tab-panels">
                <div class="lb-panel panel-team">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Posici\u00f3</th><th>Equip</th><th style='text-align:right;'>Mitjana \U0001f9ed</th></tr>
                            </thead>
                            <tbody>{team_rows}</tbody>
                        </table>
                    </div>
                </div>
                <div class="lb-panel panel-user">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Posici\u00f3</th><th>Detectiu</th><th style='text-align:right;'>Punt. \U0001f9ed</th></tr>
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
    var full = "Cada vegada que fas servir la IA, alguna cosa invisible passa...";
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
    var part2 = "una ampolla d'aigua";
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
    countEl.textContent = pc + ' consult' + (pc > 1 ? 'es' : 'a') + '/dia';
    var stats = [
        {l:'Aigua usada', v:w+'L', i:'\\ud83d\\udca7', s:bottles+' ampolles'},
        {l:'Energia usada', v:e+' kWh', i:'\\u26a1', s:tv+'s de TV'},
        {l:'CO\\u2082 em\\u00e8s', v:co2+'g', i:'\\ud83c\\udf2b\\ufe0f', s:yearKm+' km conduits/any'}
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
        btn.textContent = 'Amaga comparaci\\u00f3 amb la Cerca de Google';
        btn.style.background = 'var(--ace-hover-bg)';
    } else {
        card.style.display = 'none';
        btn.textContent = 'Mostra comparaci\\u00f3 amb la Cerca de Google';
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
        {name:'GPT-3', energy:1287, water:700000, co2:502, year:2020, icon:'\\u{1F916}', fact:"Equivalent a conduir un cotxe al voltant de la Terra 60 vegades"},
        {name:'GPT-4', energy:62000, water:34000000, co2:24000, year:2023, icon:'\\u{1F9E0}', fact:"Equivalent a l'electricitat anual de ~6000 llars dels EUA"},
        {name:'Llama 3', energy:39000, water:21000000, co2:15000, year:2024, icon:'\\u{1F999}', fact:"Podria omplir 8 piscines ol\\u00edmpiques amb l'aigua utilitzada"}
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
            + '<h3 style="font-size:1.3rem; font-weight:800; color:var(--ace-accent); margin:0 0 16px 0;">' + m.icon + " Cost d'entrenament de " + m.name + '</h3>'
            + '<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;">'
            + '<div style="text-align:center;"><div style="font-size:0.75rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:2px;">Energia</div><div style="font-size:1.6rem; font-weight:800; color:var(--ace-text); margin-top:8px;">' + m.energy.toLocaleString() + '</div><div style="font-size:0.85rem; color:var(--ace-text-dim);">MWh</div></div>'
            + '<div style="text-align:center;"><div style="font-size:0.75rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:2px;">Aigua</div><div style="font-size:1.6rem; font-weight:800; color:var(--ace-text); margin-top:8px;">' + waterM + 'M</div><div style="font-size:0.85rem; color:var(--ace-text-dim);">litres</div></div>'
            + '<div style="text-align:center;"><div style="font-size:0.75rem; color:var(--ace-text-dim); text-transform:uppercase; letter-spacing:2px;">CO\\u2082</div><div style="font-size:1.6rem; font-weight:800; color:var(--ace-text); margin-top:8px;">' + m.co2.toLocaleString() + '</div><div style="font-size:0.85rem; color:var(--ace-text-dim);">tones</div></div>'
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
        {l:'Seg\\u00fcent gen. (2025+)', w:100, v:'???', striped:true}
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
        {id:'a', t:"Nom\\u00e9s aigua reciclada de l'oce\\u00e0", correct:false},
        {id:'b', t:"Aigua dol\\u00e7a de rius, aig\\u00fces subterr\\u00e0nies i subministraments municipals", correct:true},
        {id:'c', t:"\\u00c9s tota aigua sint\\u00e8tica fabricada en laboratoris", correct:false},
        {id:'d', t:"Aigua de pluja recollida als terrats", correct:false}
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
                resultEl.innerHTML = '<div style="padding:16px; border-radius:12px; font-size:1rem; line-height:1.6; background:var(--ace-success-bg); color:var(--ace-success); border:1px solid var(--ace-success);">Correcte! La majoria dels centres de dades utilitzen aigua dol\\u00e7a: rius, aqu\\u00edfers subterranis i subministraments d\\u2019aigua municipals.</div>';
            } else {
                resultEl.innerHTML = '<div style="padding:16px; border-radius:12px; font-size:1rem; line-height:1.6; background:var(--ace-error-bg); color:var(--ace-error); border:1px solid var(--ace-error);">No exactament. Els centres de dades depenen principalment d\\u2019aigua dol\\u00e7a real de fonts locals, la mateixa aigua que beu la teva comunitat.</div>';
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
        {l:"Energia total de la IA el 2025", v:'~200 TWh/any', d:"Tota l'electricitat del Regne Unit", i:'\\ud83c\\uddec\\ud83c\\udde7'},
        {l:"Emissions de CO\\u2082 de la IA", v:'~56M ton/any', d:"Les emissions totals anuals de Nova York", i:'\\ud83d\\uddfd'},
        {l:"Petjada h\\u00eddrica de la IA", v:'~540 000 M L/any', d:"Consum mundial d'aigua embotellada", i:'\\ud83e\\uddf4'},
        {l:'Centres de dades el 2030', v:'~945 TWh', d:"Entre el total del Jap\\u00f3 i R\\u00fassia", i:'\\u26a1'}
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
        {l:'Servidors (GPUs, CPUs)', p:60, c:'var(--ace-warning)'},
        {l:'Sistemes de refrigeraci\\u00f3', p:25, c:'var(--ace-accent)'},
        {l:'Xarxes', p:5, c:'var(--ace-success)'},
        {l:'Emmagatzematge', p:5, c:'#a78bfa'},
        {l:"Altres (il\\u00b7luminaci\\u00f3, etc.)", p:5, c:'var(--ace-text-dim)'}
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
        {id:'search', l:'Busca-ho a Google primer', d:"Fes servir un cercador normal quan no necessitis IA", p:30, i:'\\ud83d\\udd0d'},
        {id:'specific', l:'Sigues espec\\u00edfic', d:'Consultes clares = menys seguiments = menys energia', p:15, i:'\\ud83c\\udfaf'},
        {id:'local', l:'Fes servir models m\\u00e9s petits', d:"Els models d'IA m\\u00e9s petits consumeixen molta menys energia per a tasques simples", p:25, i:'\\ud83d\\udcf1'},
        {id:'aware', l:'Mant\\u00e9n-te informat', d:'Exigeix transpar\\u00e8ncia a les empreses tecnol\\u00f2giques', p:20, i:'\\ud83d\\udce2'},
        {id:'share', l:"Explica-ho a un amic", d:"La majoria de la gent no t\\u00e9 ni idea que la IA consumeix tant", p:10, i:'\\ud83d\\udcac'}
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
            if (total === 0) msgEl.textContent = 'Selecciona algunes accions a dalt per veure el teu impacte!';
            else if (total <= 30) msgEl.textContent = 'Bon comen\\u00e7ament! Cada gest compta quan milers de milions fan servir la IA.';
            else if (total <= 60) msgEl.textContent = 'Genial! Est\\u00e0s marcant una difer\\u00e8ncia real.';
            else if (total <= 90) msgEl.textContent = "Pr\\u00e0cticament ets un defensor de la IA sostenible!";
            else msgEl.textContent = 'Impacte m\\u00e0xim! Liderant l\\u2019\\u00fas responsable de la IA!';
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

def create_bias_detective_ca_sustainability_app(theme_primary_hue: str = "indigo"):
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
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Carregant...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>Autenticant...</h2>"
                "<p>Sincronitzant dades de Br\u00faixola Moral...</p>"
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
                            "<span class='points-chip'>\U0001f9ed Punts de Br\u00faixola Moral disponibles</span>"
                            "<span>Respon per augmentar la teva puntuaci\u00f3</span>"
                            "</div>"
                        )

                        gr.Markdown(f"### \U0001f9e0 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Selecciona la teva resposta:",
                            elem_classes=["quiz-radio-large"],
                        )
                        feedback = gr.HTML("")
                        quiz_wiring_queue.append((i, radio, feedback))

                    # Navigation buttons
                    with gr.Row():
                        btn_prev = gr.Button("\u2b05\ufe0f Anterior", visible=(i > 0))
                        next_label = (
                            "Seg\u00fcent \u25b6\ufe0f"
                            if i < len(MODULES) - 1
                            else "CONTINUAR A L'ACTIVITAT 7 →"
                        )
                        btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            gr.HTML("""
                <details style="background:var(--background-fill-secondary); border-radius:16px;
                                border:1px solid var(--border-color-primary); margin:8px 0 12px 0; opacity:0.7;">
                    <summary style="padding:14px 24px; cursor:pointer; text-transform:uppercase; letter-spacing:1.5px;
                                    color:var(--body-text-color-subdued); font-size:0.78rem; font-weight:700;
                                    text-align:center; list-style:none;">
                        &#9656; La F&oacute;rmula de la Br&uacute;ixola Moral
                    </summary>
                    <div style="padding:0 24px 24px 24px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:700; margin:12px 0; font-family:'Outfit',sans-serif;">
                            Puntuaci&oacute; Br&uacute;ixola Moral =
                            <span style="background:rgba(5,150,105,0.15); color:var(--ace-success); padding:4px 10px; border-radius:6px;">
                                [ Precisi&oacute; ]</span>
                            &times;
                            <span style="background:rgba(2,132,199,0.15); color:var(--ace-accent); padding:4px 10px; border-radius:6px;">
                                [ Sostenibilitat % ]</span>
                        </div>
                        <p style="font-size:0.95rem; margin:12px 0 0 0; color:var(--body-text-color-subdued);">
                            <strong>Sostenibilitat %</strong> reflecteix el teu progr&eacute;s de Br&uacute;ixola Moral a trav&eacute;s de la investigaci&oacute;.<br/>
                            Si la teva Sostenibilitat % &eacute;s <strong>0%</strong>, la teva Puntuaci&oacute; Br&uacute;ixola Moral &eacute;s <strong>0</strong>.
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
                            "\u274c No del tot. Rellegeix les proves anteriors i pensa en qu\u00e8 mostren espec\u00edficament les dades.</div>",
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
                "<div class='hint-box'>Autenticaci\u00f3 fallida. Si us plau, accedeix des de l'enlla\u00e7 del curs.</div>",
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
                    js=nav_js(prev_target_id, "Carregant..."),
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
                    js=nav_js(next_target_id, "Carregant..."),
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

def launch_bias_detective_ca_sustainability_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    app = create_bias_detective_ca_sustainability_app(theme_primary_hue=theme_primary_hue)
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        **kwargs
    )


if __name__ == "__main__":
    launch_bias_detective_ca_sustainability_app(share=False, debug=True, height=1000)

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
# 4. MODULE DEFINITIONS — 7-PAGE GREEN AI CTO SIMULATION
# ============================================================================
# Page 0: Title Screen — no quiz
# Page 1: Round 1 — Cooling Crisis — quiz t12
# Page 2: Round 2 — Power Source Reckoning — quiz t13
# Page 3: Round 3 — Model Efficiency Overhaul — quiz t14
# Page 4: Round 4 — Location Decision — quiz t15
# Page 5: Round 5 — Transparency Report — quiz t16
# Page 6: Results — quiz t17
# ============================================================================

def _round_html(round_idx, emoji, title, brief, question, choices):
    """Generate HTML for a game round (modules 1-5)."""
    total = 5
    progress_segments = ""
    for seg in range(total):
        if seg < round_idx:
            color = "var(--cto-success)"
        elif seg == round_idx:
            color = "var(--cto-warning)"
        else:
            color = "var(--cto-progress-line)"
        progress_segments += (
            f'<div style="flex:1; height:4px; border-radius:2px; '
            f'background:{color}; transition:background 0.5s;"></div>'
        )

    choice_cards = ""
    for ci, ch in enumerate(choices):
        choice_cards += (
            f'<button class="cto-choice-card" id="cto-choice-{round_idx}-{ci}" '
            f'onclick="ctoSelectChoice({round_idx},{ci})" '
            f'style="display:flex; align-items:flex-start; gap:14px; padding:18px 16px; '
            f'border-radius:16px; cursor:pointer; text-align:left; width:100%; '
            f'background:var(--cto-input-bg); border:2px solid var(--cto-border-color); '
            f'color:var(--cto-text); transition:all 0.3s; font-family:\'Outfit\',sans-serif; font-size:inherit;">'
            f'<div style="width:44px; height:44px; border-radius:12px; flex-shrink:0; '
            f'background:var(--cto-input-bg); display:flex; align-items:center; justify-content:center; '
            f'font-size:1.4rem;" id="cto-choice-icon-{round_idx}-{ci}">{ch["icon"]}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:1.05rem; font-weight:700;">{ch["label"]}</div>'
            f'<div style="font-size:0.95rem; color:var(--cto-text-dim); margin-top:4px; line-height:1.6;">{ch["desc"]}</div>'
            f'</div>'
            f'<div style="width:24px; height:24px; border-radius:50%; flex-shrink:0; margin-top:2px; '
            f'border:2px solid var(--cto-input-border); background:transparent; '
            f'display:flex; align-items:center; justify-content:center; transition:all 0.3s;" '
            f'id="cto-choice-radio-{round_idx}-{ci}"></div>'
            f'</button>'
        )

    return f"""
        <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
            <div class="cto-reveal" style="animation-delay:0s;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                    <span style="font-size:0.875rem; color:var(--cto-text-dim); font-weight:600; letter-spacing:3px; text-transform:uppercase;">Ronda {round_idx} / {total}</span>
                    <span style="font-size:0.875rem; color:var(--cto-text-dim);">NovaMind AI &mdash; La Teva Revisi&oacute;</span>
                </div>
                <div class="cto-stats-wrapper">
                    <div class="cto-stats-header">&#127961;&#65039; La Contaminaci&oacute; de la Teva Ciutat</div>
                    <div id="cto-stats-{round_idx}" class="cto-stats-grid"></div>
                </div>
                <div style="display:flex; gap:6px; margin-top:16px;">
                    {progress_segments}
                </div>
            </div>

            <div class="cto-reveal" style="animation-delay:0.2s;">
                <div class="cto-card" style="margin-top:28px;">
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                        <span style="font-size:2rem;">{emoji}</span>
                        <div>
                            <div style="font-size:0.75rem; color:var(--cto-warning); font-weight:800; letter-spacing:3px; text-transform:uppercase;">Qu&egrave; Est&agrave; Passant</div>
                            <h2 style="font-size:1.5rem; font-weight:800; color:var(--cto-text); margin:0;">{title}</h2>
                        </div>
                    </div>
                    <p style="font-size:1.125rem; color:var(--cto-text-dim); line-height:1.7; margin:0;">{brief}</p>
                </div>
            </div>

            <div class="cto-reveal" style="animation-delay:0.4s;">
                <h3 style="margin-top:24px; font-size:1.2rem; font-weight:700; color:var(--cto-text);">{question}</h3>
            </div>

            <div class="cto-reveal" style="animation-delay:0.6s;" id="cto-choices-container-{round_idx}">
                <div style="display:grid; gap:10px; margin-top:16px;">
                    {choice_cards}
                </div>
                <button id="cto-confirm-btn-{round_idx}" class="cto-confirm-btn"
                    onclick="ctoConfirmDecision({round_idx})" style="display:none;">
                    Confirmar La Meva Elecci&oacute; &rarr;
                </button>
            </div>

            <div id="cto-feedback-{round_idx}" style="margin-top:24px;"></div>
        </div>
    """


MODULES = [
    # ─────────────────────────────────────────────
    # MODULE 0 — TITLE SCREEN
    # ─────────────────────────────────────────────
    {
        "id": 0,
        "title": "ASSESSOR/A D'IA VERDA",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="cto-title-page">
                    <div class="cto-reveal" style="animation-delay:0s;">
                        <div style="font-size:0.875rem; font-weight:800; letter-spacing:3px; color:var(--cto-error); text-transform:uppercase; margin-bottom:24px; text-align:center;">
                            &#127758; Informe de Missi&oacute;
                        </div>
                    </div>
                    <div class="cto-reveal" style="animation-delay:0.3s;">
                        <h1 style="font-size:clamp(2.2rem, 8vw, 3.5rem); font-weight:800; text-align:center; line-height:1.1; letter-spacing:-1px; color:var(--cto-text); margin:0;">
                            ASSESSOR/A D&#39;IA<br/><span style="color:var(--cto-accent);">VERDA</span>
                        </h1>
                    </div>
                    <div class="cto-reveal" style="animation-delay:0.6s;">
                        <p style="font-size:1.125rem; color:var(--cto-text-dim); text-align:center; max-width:480px; margin:28px auto 0; line-height:1.7;">
                            L&#39;alcaldessa acaba de triar-TE com a <strong style="color:var(--cto-text); font-weight:600;">Assessor/a d&#39;IA Verda</strong> de la ciutat.
                            Una empresa anomenada NovaMind vol construir un centre de dades gegant aqu&iacute;. Mira els n&uacute;meros de contaminaci&oacute; de sota &mdash; <strong style="color:var(--cto-error); font-weight:700;">aix&ograve; &eacute;s el que LA TEVA ciutat haur&agrave; d&#39;enfrontar</strong> si no actues.
                        </p>
                    </div>
                    <div class="cto-reveal" style="animation-delay:0.9s;">
                        <div class="cto-stats-wrapper" style="margin-top:32px; max-width:420px; margin-left:auto; margin-right:auto;">
                            <div class="cto-stats-header">&#127961;&#65039; La Contaminaci&oacute; de NovaMind a la Teva Ciutat</div>
                            <div class="cto-stats-grid">
                                <div style="text-align:center; padding:8px 4px;">
                                    <div style="font-size:0.75rem; color:var(--cto-text-dim); text-transform:uppercase; letter-spacing:1px;">&#9889; Energia de Fam&iacute;lies</div>
                                    <div style="font-size:1.1rem; font-weight:800; color:var(--cto-text); margin-top:4px;">14.400</div>
                                    <div style="font-size:0.7rem; color:var(--cto-text-dim);">llars/any</div>
                                </div>
                                <div style="text-align:center; padding:8px 4px;">
                                    <div style="font-size:0.75rem; color:var(--cto-text-dim); text-transform:uppercase; letter-spacing:1px;">&#128167; &Uacute;s d&#39;Aigua</div>
                                    <div style="font-size:1.1rem; font-weight:800; color:var(--cto-text); margin-top:4px;">89</div>
                                    <div style="font-size:0.7rem; color:var(--cto-text-dim);">piscines/any</div>
                                </div>
                                <div style="text-align:center; padding:8px 4px;">
                                    <div style="font-size:0.75rem; color:var(--cto-text-dim); text-transform:uppercase; letter-spacing:1px;">&#128663; Contaminaci&oacute; CO&#8322;</div>
                                    <div style="font-size:1.1rem; font-weight:800; color:var(--cto-text); margin-top:4px;">4.800</div>
                                    <div style="font-size:0.7rem; color:var(--cto-text-dim);">cotxes/any</div>
                                </div>
                                <div style="text-align:center; padding:8px 4px;">
                                    <div style="font-size:0.75rem; color:var(--cto-text-dim); text-transform:uppercase; letter-spacing:1px;">&#127793; Puntuaci&oacute; Verda</div>
                                    <div style="font-size:1.1rem; font-weight:800; color:var(--cto-text); margin-top:4px;">8 / 100 &#128561;</div>
                                    <div style="font-size:0.7rem; color:var(--cto-text-dim);">/100</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="cto-reveal" style="animation-delay:1.1s;">
                        <p style="font-size:1.05rem; font-weight:700; color:var(--cto-accent); text-align:center; margin-top:20px;">Redueix cada n&uacute;mero a nivells verds i protegeix la teva ciutat!</p>
                    </div>
                    <div class="cto-reveal" style="animation-delay:1.3s;">
                        <div style="text-align:center; margin-top:12px;">
                            <p style="font-size:0.875rem; color:var(--cto-text-dim);">5 rondes &middot; Decisions reals &middot; La teva ciutat compta amb tu! &#127758;</p>
                        </div>
                    </div>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 1 — ROUND 1: THE COOLING CRISIS
    # ─────────────────────────────────────────────
    {
        "id": 1,
        "title": "Ronda 1: La Crisi de Refrigeraci\u00f3",
        "html": _round_html(
            round_idx=1,
            emoji="\U0001f321\ufe0f",
            title="La Crisi de Refrigeraci\u00f3",
            brief="Imagina un edifici que fa servir 89 piscines d&#39;aigua CADA ANY nom\u00e9s per mantenir els seus ordinadors freds. Aquest \u00e9s el pla de NovaMind &mdash; i la teva ciutat s&#39;est\u00e0 quedant sense aigua.",
            question="Com hauria NovaMind de refredar els seus ordinadors?",
            choices=[
                {"icon": "\U0001f9ca", "label": "Submergir Servidors en L\u00edquid Especial", "desc": "Posar els ordinadors en un bany fred en lloc de ruixar aigua. Costa m\u00e9s instal\u00b7lar-ho, per\u00f2 no fa servir gaireb\u00e9 gens d&#39;aigua."},
                {"icon": "\u267b\ufe0f", "label": "Reutilitzar Aigua + Usar Aire Fred", "desc": "Reciclar l&#39;aigua i deixar que l&#39;aire fred de fora ajudi. Estalvia aproximadament la meitat de l&#39;aigua."},
                {"icon": "\U0001f527", "label": "Nom\u00e9s Afegir Sensors al que Hi Ha", "desc": "Mantenir el mateix sistema per\u00f2 afegir sensors per malbaratar una mica menys. El m\u00e9s barat, per\u00f2 gaireb\u00e9 no canvia res."},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 2 — ROUND 2: POWER SOURCE RECKONING
    # ─────────────────────────────────────────────
    {
        "id": 2,
        "title": "Ronda 2: D\u2019On Ve l\u2019Energia?",
        "html": _round_html(
            round_idx=2,
            emoji="\u26a1",
            title="D&#39;On Ve l&#39;Energia?",
            brief="Ara mateix, NovaMind es connectaria directament a energia bruta &mdash; el 65% ve de cremar gas i carb\u00f3. Cada cop que alg\u00fa li fa una pregunta a la IA, es cremen m\u00e9s combustibles f\u00f2ssils.",
            question="D&#39;on hauria NovaMind d&#39;obtenir la seva electricitat?",
            choices=[
                {"icon": "\u2600\ufe0f", "label": "Construir una Granja Solar + Bateries", "desc": "Cobrir la teulada i els aparcaments amb panells solars. Afegir bateries gegants per a la nit. Car, per\u00f2 NovaMind ho posseeix per sempre."},
                {"icon": "\U0001f32c\ufe0f", "label": "Comprar Energia Neta d&#39;un Parc E\u00f2lic/Solar", "desc": "Signar un acord per obtenir electricitat d&#39;un parc e\u00f2lic o solar proper en lloc de la xarxa bruta."},
                {"icon": "\U0001f4dc", "label": "Pagar per Compensacions de Carboni", "desc": "Continuar cremant combustibles f\u00f2ssils, per\u00f2 pagar perqu\u00e8 plantin arbres en un altre lloc. Aix\u00f2 s&#39;anomena una &lt;strong&gt;compensaci\u00f3 de carboni&lt;/strong&gt; &mdash; queda b\u00e9 sobre el paper, per\u00f2 la contaminaci\u00f3 segueix igual."},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 3 — ROUND 3: MODEL EFFICIENCY OVERHAUL
    # ─────────────────────────────────────────────
    {
        "id": 3,
        "title": "Ronda 3: IA de la Mida Adequada",
        "html": _round_html(
            round_idx=3,
            emoji="\U0001f9e0",
            title="IA de la Mida Adequada",
            brief="NovaMind fa servir el seu model d&#39;IA m\u00e9s gran i potent per a CADA pregunta &mdash; fins i tot les f\u00e0cils com &#39;Quin temps fa?&#39; Pensa en els models d&#39;IA com cervells de mides diferents: alguns s\u00f3n enormes i potents, altres s\u00f3n petits i r\u00e0pids. 8 de cada 10 preguntes no necessiten el m\u00e9s gran.",
            question="Com hauria NovaMind de gestionar les preguntes f\u00e0cils vs. les dif\u00edcils?",
            choices=[
                {"icon": "\U0001fa9c", "label": "Ajustar la Mida del Model a la Dificultat", "desc": "Fer servir un model petit per a preguntes f\u00e0cils, un de mitj\u00e0 per a les complicades, i el m\u00e9s gran nom\u00e9s per a les m\u00e9s dif\u00edcils. Com triar l&#39;eina correcta per a cada feina."},
                {"icon": "\U0001f9ec", "label": "Entrenar una IA M\u00e9s Petita i Llesta", "desc": "Ensenyar a un model mitj\u00e0 a fer gaireb\u00e9 tot el que pot el gegant. Un model que \u00e9s suficient per al 90% de les preguntes."},
                {"icon": "\U0001f4be", "label": "Nom\u00e9s Guardar Respostes Repetides", "desc": "Recordar respostes comunes perqu\u00e8 la IA no les repeteixi. Per\u00f2 el model m\u00e9s gran segueix funcionant per a tot el nou."},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 4 — ROUND 4: LOCATION DECISION
    # ─────────────────────────────────────────────
    {
        "id": 4,
        "title": "Ronda 4: Ubicaci\u00f3, Ubicaci\u00f3, Ubicaci\u00f3",
        "html": _round_html(
            round_idx=4,
            emoji="\U0001f4cd",
            title="Ubicaci\u00f3, Ubicaci\u00f3, Ubicaci\u00f3",
            brief="NovaMind vol construir en un desert calor\u00f3s perqu\u00e8 el terreny \u00e9s barat. Per\u00f2 la calor del desert significa que els ordinadors necessiten MOLTA m\u00e9s refrigeraci\u00f3. I la xarxa el\u00e8ctrica local funciona principalment amb gas.",
            question="On hauria de construir NovaMind?",
            choices=[
                {"icon": "\U0001f1f8\U0001f1ea", "label": "Construir a la Freda Escandin\u00e0via", "desc": "Su\u00e8cia i Finl\u00e0ndia s\u00f3n gelades &mdash; la natura refreda els ordinadors gratis. A m\u00e9s, el 95% de l&#39;electricitat all\u00e0 ja \u00e9s neta."},
                {"icon": "\U0001f332", "label": "Construir a la Plujosa Oregon", "desc": "El clima suau significa menys refrigeraci\u00f3 necess\u00e0ria. Molta energia hidroel\u00e8ctrica dels rius. Altres grans empreses tecnol\u00f2giques ja hi s\u00f3n."},
                {"icon": "\U0001f3dc\ufe0f", "label": "Quedar-se al Desert Calor\u00f3s", "desc": "El terreny \u00e9s super barat. Per\u00f2 fa una calor abrasadora i la xarxa el\u00e8ctrica crema gas."},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 5 — ROUND 5: THE TRANSPARENCY REPORT
    # ─────────────────────────────────────────────
    {
        "id": 5,
        "title": "Ronda 5: Control d\u2019Honestedat",
        "html": _round_html(
            round_idx=5,
            emoji="\U0001f4ca",
            title="Control d&#39;Honestedat",
            brief="La majoria de les empreses d&#39;IA mantenen les seves xifres de contaminaci\u00f3 en secret. Estan arribant noves lleis que les obligaran a compartir-les. Hauria NovaMind de donar exemple o amagar-se com tots els altres?",
            question="Quant hauria NovaMind de compartir amb el p\u00fablic?",
            choices=[
                {"icon": "\U0001f4e1", "label": "Marcador P\u00fablic en Viu", "desc": "Mostrar a tothom exactament quanta energia i aigua fa servir NovaMind, actualitzat en viu. Honestedat total."},
                {"icon": "\U0001f4c4", "label": "Informe Anual", "desc": "Publicar un informe un cop l&#39;any amb els n\u00fameros grans. \u00c9s el que fan la majoria de les empreses &mdash; el m\u00ednim."},
                {"icon": "\U0001f512", "label": "Nom\u00e9s Compartir el que la Llei Obligui", "desc": "Amagar tot el possible. Dir-ne un &#39;secret empresarial.&#39;"},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 6 — RESULTS
    # ─────────────────────────────────────────────
    {
        "id": 6,
        "title": "El Teu Informe d'Assessor/a",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div id="cto-results-container" style="padding:20px 0; max-width:900px; margin:0 auto;">
                    <div style="text-align:center; padding:40px;">
                        <div style="font-size:1.2rem; color:var(--cto-text-dim);">Sumant les teves decisions...</div>
                    </div>
                </div>
            </div>
        """,
    },
]


# ============================================================================
# 5. QUIZ CONFIG — 6 QUIZZES ON MODULES 1-6, TASK IDs t5-t10
# ============================================================================

QUIZ_CONFIG = {
    1: {
        "t": "t5",
        "q": "Alg\u00fa diu: *\u2018Els sensors s\u00f3n m\u00e9s barats \u2014 per qu\u00e8 gastar m\u00e9s en refrigeraci\u00f3?\u2019* Quin \u00e9s el millor argument en contra?",
        "o": [
            "A) Els sensors nom\u00e9s estalvien una mica d\u2019aigua. El sistema segueix malbaratant milions de litres durant una sequera \u2014 un peda\u00e7 petit en un sistema trencat no \u00e9s suficient.",
            "B) La refrigeraci\u00f3 l\u00edquida \u00e9s massa nova i arriscada. Les petites millores s\u00f3n l\u2019opci\u00f3 m\u00e9s segura.",
            "C) El cost no importa perqu\u00e8 el govern ho pagar\u00e0 de totes maneres.",
        ],
        "a": "A) Els sensors nom\u00e9s estalvien una mica d\u2019aigua. El sistema segueix malbaratant milions de litres durant una sequera \u2014 un peda\u00e7 petit en un sistema trencat no \u00e9s suficient.",
        "success": "<strong>Coneixement de Refrigeraci\u00f3 Desbloquejat!</strong> Microsoft ja est\u00e0 provant aix\u00f2. Un peda\u00e7 petit en un sistema trencat no resol el veritable problema.",
    },
    2: {
        "t": "t6",
        "q": "Una empresa compra compensacions de carboni i diu: *\u2018Ja som verds!\u2019* Qu\u00e8 t\u00e9 de dolent aquesta afirmaci\u00f3?",
        "o": [
            "A) Pagar per arbres plantats en un altre lloc funciona igual de b\u00e9 que fer servir panells solars.",
            "B) Les compensacions de carboni no canvien el que alimenta l\u2019edifici \u2014 segueix cremant combustibles f\u00f2ssils. La contaminaci\u00f3 \u00e9s real. L\u2019etiqueta de \u2018verd\u2019 \u00e9s nom\u00e9s matem\u00e0tiques en un paper.",
            "C) L\u2019\u00fanic problema \u00e9s que les compensacions costen massa \u2014 l\u2019energia solar seria m\u00e9s barata a llarg termini.",
        ],
        "a": "B) Les compensacions de carboni no canvien el que alimenta l\u2019edifici \u2014 segueix cremant combustibles f\u00f2ssils. La contaminaci\u00f3 \u00e9s real. L\u2019etiqueta de \u2018verd\u2019 \u00e9s nom\u00e9s matem\u00e0tiques en un paper.",
        "success": "<strong>Claredat sobre la Font d\u2019Energia!</strong> La contaminaci\u00f3 segueix igual \u2014 nom\u00e9s canvia la comptabilitat. El canvi real significa passar-se a energia neta.",
    },
    3: {
        "t": "t7",
        "q": "Alg\u00fa diu: *\u2018Els usuaris volen la millor IA sempre!\u2019* Per qu\u00e8 fer servir la IA m\u00e9s gran per a cada pregunta \u00e9s mala idea?",
        "o": [
            "A) Per a preguntes f\u00e0cils, una IA petita funciona igual de b\u00e9 \u2014 i fa servir 50 vegades menys energia. Per qu\u00e8 fer servir un coet per anar a la botiga de la cantonada?",
            "B) Haur\u00edem de fer servir sempre la IA m\u00e9s petita, encara que doni males respostes a preguntes dif\u00edcils.",
            "C) La mida de la IA no canvia quanta energia fa servir \u2014 l\u2019ordinador fa servir la mateixa pot\u00e8ncia sense importar qu\u00e8.",
        ],
        "a": "A) Per a preguntes f\u00e0cils, una IA petita funciona igual de b\u00e9 \u2014 i fa servir 50 vegades menys energia. Per qu\u00e8 fer servir un coet per anar a la botiga de la cantonada?",
        "success": "<strong>Efici\u00e8ncia Desbloquejada!</strong> Aix\u00ed \u00e9s com treballen les empreses d\u2019IA m\u00e9s intel\u00b7ligents \u2014 ajusten la mida del model a cada pregunta.",
    },
    4: {
        "t": "t8",
        "q": "Alg\u00fa diu: *\u2018El terreny del desert \u00e9s barat \u2014 ens estalviarem milions!\u2019* Qu\u00e8 estan oblidant?",
        "o": [
            "A) Els deserts estan b\u00e9 si fas servir energia neta \u2014 la calor no importa realment amb bona refrigeraci\u00f3.",
            "B) La calor extrema significa 3 vegades m\u00e9s costos de refrigeraci\u00f3, la xarxa de gas anul\u00b7la el teu progr\u00e9s verd, i no hi ha prou aigua \u2014 estalviar diners ara causa problemes m\u00e9s grans despr\u00e9s.",
            "C) L\u2019\u00fanic problema \u00e9s la mala premsa \u2014 els costos reals s\u00f3n m\u00e9s o menys iguals que construir en un lloc fred.",
        ],
        "a": "B) La calor extrema significa 3 vegades m\u00e9s costos de refrigeraci\u00f3, la xarxa de gas anul\u00b7la el teu progr\u00e9s verd, i no hi ha prou aigua \u2014 estalviar diners ara causa problemes m\u00e9s grans despr\u00e9s.",
        "success": "<strong>Intel\u00b7lig\u00e8ncia d\u2019Ubicaci\u00f3!</strong> Meta i Google van triar llocs freds exactament per aquesta ra\u00f3 \u2014 refrigeraci\u00f3 gratis + energia neta = m\u00e9s barat al final.",
    },
    5: {
        "t": "t9",
        "q": "Una empresa rival diu: *\u2018Compartir les nostres xifres de contaminaci\u00f3 perjudica el nostre negoci.\u2019* Per qu\u00e8 amagar-se \u00e9s mala idea?",
        "o": [
            "A) Compartir xifres \u00e9s nom\u00e9s per a publicitat \u2014 realment no ajuda el medi ambient.",
            "B) Les noves lleis arribaran de totes maneres. Les empreses que comparteixen primer generen confian\u00e7a i estableixen les regles \u2014 les que s\u2019amaguen es comparen amb petrolieres que oculten la contaminaci\u00f3.",
            "C) \u00c9s impossible reportar aquests n\u00fameros amb precisi\u00f3 perqu\u00e8 cada edifici \u00e9s diferent.",
        ],
        "a": "B) Les noves lleis arribaran de totes maneres. Les empreses que comparteixen primer generen confian\u00e7a i estableixen les regles \u2014 les que s\u2019amaguen es comparen amb petrolieres que oculten la contaminaci\u00f3.",
        "success": "<strong>Est\u00e0ndard de Transpar\u00e8ncia Establert!</strong> Les empreses que comparteixen primer estableixen les regles. Amagar-se nom\u00e9s fa que la gent confi\u00ef menys en tu.",
    },
    6: {
        "t": "t10",
        "q": "Despr\u00e9s de les 5 rondes, per qu\u00e8 importen aquestes decisions individuals per a tot el planeta?",
        "o": [
            "A) Una sola empresa \u00e9s massa petita per importar \u2014 nom\u00e9s els governs poden arreglar aquest problema.",
            "B) Cada decisi\u00f3 \u2014 refrigeraci\u00f3, energia, mida d\u2019IA, ubicaci\u00f3, honestedat \u2014 se suma a trav\u00e9s de milions d\u2019usuaris. Quan una empresa lidera, les altres senten la pressi\u00f3 de seguir.",
            "C) La tecnologia es tornar\u00e0 m\u00e9s eficient sola, aix\u00ed que les decisions d\u2019avui no importen realment a llarg termini.",
        ],
        "a": "B) Cada decisi\u00f3 \u2014 refrigeraci\u00f3, energia, mida d\u2019IA, ubicaci\u00f3, honestedat \u2014 se suma a trav\u00e9s de milions d\u2019usuaris. Quan una empresa lidera, les altres senten la pressi\u00f3 de seguir.",
        "success": "<strong>Ho Has Aconseguit!</strong> La sostenibilitat de la IA no \u00e9s una gran decisi\u00f3 \u2014 s\u00f3n cinc decisions intel\u00b7ligents que se sumen i canvien com funciona tota una ind\u00fastria.",
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
        header_title = "Ets Oficialment a la Classificaci\u00f3!"
        summary_line = "Acabes d\u2019obtenir la teva primera Puntuaci\u00f3 de Br\u00faixola Moral \u2014 ara formes part del r\u00e0nquing global."
        cta_line = "Continua fent recomanacions per escalar a la classificaci\u00f3."
    elif style_key == "major":
        header_emoji = "\U0001f525"
        header_title = "Gran Impuls a la Br\u00faixola Moral!"
        summary_line = "La teva recomanaci\u00f3 ha tingut un gran impacte \u2014 acabes d\u2019avançar per davant d\u2019altres assessors."
        cta_line = "Continua la teva simulaci\u00f3 per mantenir l\u2019impuls."
    elif style_key == "climb":
        header_emoji = "\U0001f680"
        header_title = "Est\u00e0s Escalant a la Classificaci\u00f3"
        summary_line = "Bona feina \u2014 has superat altres participants."
        cta_line = "Fes clic a SEG\u00dcENT per continuar la teva simulaci\u00f3."
    elif style_key == "tight":
        header_emoji = "\U0001f4ca"
        header_title = "La Classificaci\u00f3 Est\u00e0 Canviant"
        summary_line = "Els altres equips tamb\u00e9 es mouen. Unes quantes respostes m\u00e9s fortes et diferenciaran."
        cta_line = "Afronta la seg\u00fcent ronda per enfortir la teva posici\u00f3."
    else:
        header_emoji = "\u2705"
        header_title = "Progr\u00e9s Registrat"
        summary_line = "El teu coneixement en sostenibilitat ha augmentat la teva Puntuaci\u00f3 de Br\u00faixola Moral."
        cta_line = "Prova la seg\u00fcent ronda per continuar escalant."

    if style_key == "first":
        score_line = f"\U0001f9ed Puntuaci\u00f3: <strong>{new_score:.3f}</strong>"
        rank_line = f"\U0001f3c5 Posici\u00f3 Inicial: <strong>#{new_rank}</strong>"
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

    if module_id <= 3:
        phase_label = "RONDES 1\u20133: Eleccions de Construcci\u00f3"
        phase_color = "#6366f1"
    else:
        phase_label = "RONDES 4\u20135: Grans Decisions"
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
                    <div class="label-text">R\u00e0nquing d\u2019Equip</div>
                    <div class="score-text-team">{team_rank_display}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">R\u00e0nquing Global</div>
                    <div class="score-text-global">{rank_display}</div>
                </div>
            </div>
            <div class="summary-progress">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="progress-label">Progr\u00e9s de la Simulaci\u00f3: {progress_pct}%</div>
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
        <h3 class="slide-title" style="margin-bottom:10px;">\U0001f4ca Classificaci\u00f3 en Viu</h3>
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
                                <tr><th>Pos.</th><th>Equip</th><th style='text-align:right;'>Mitjana \U0001f9ed</th></tr>
                            </thead>
                            <tbody>{team_rows}</tbody>
                        </table>
                    </div>
                </div>
                <div class="lb-panel panel-user">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Pos.</th><th>Assessor/a</th><th style='text-align:right;'>Punt. \U0001f9ed</th></tr>
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
# 9. CSS — CTO design system + Gradio integration
# ============================================================================

css = """
/* ========== Green AI CTO Design System ========== */

/* CTO CSS variables — scoped with cto- prefix to avoid Gradio collisions */
/* Light mode is the default (Gradio Soft theme default) */
:root {
    --cto-bg: #f8fafc;
    --cto-card-bg: rgba(255, 255, 255, 0.9);
    --cto-accent: #0284c7;
    --cto-accent-glow: rgba(2, 132, 199, 0.2);
    --cto-success: #059669;
    --cto-warning: #d97706;
    --cto-error: #dc2626;
    --cto-text: #0f172a;
    --cto-text-dim: #64748b;
    --cto-bg-gradient-1: rgba(2, 132, 199, 0.08);
    --cto-bg-gradient-2: rgba(5, 150, 105, 0.08);
    --cto-card-shadow: rgba(0, 0, 0, 0.1);
    --cto-border-color: rgba(0, 0, 0, 0.08);
    --cto-input-bg: rgba(0, 0, 0, 0.02);
    --cto-input-border: rgba(0, 0, 0, 0.1);
    --cto-hover-bg: rgba(0, 0, 0, 0.05);
    --cto-progress-line: rgba(0, 0, 0, 0.1);
}
@media (prefers-color-scheme: dark) {
    :root {
        --cto-bg: #0f172a;
        --cto-card-bg: rgba(30, 41, 59, 0.7);
        --cto-accent: #38bdf8;
        --cto-accent-glow: rgba(56, 189, 248, 0.3);
        --cto-success: #10b981;
        --cto-warning: #fbbf24;
        --cto-error: #f43f5e;
        --cto-text: #f8fafc;
        --cto-text-dim: #94a3b8;
        --cto-bg-gradient-1: rgba(56, 189, 248, 0.05);
        --cto-bg-gradient-2: rgba(16, 185, 129, 0.05);
        --cto-card-shadow: rgba(0, 0, 0, 0.5);
        --cto-border-color: rgba(255, 255, 255, 0.05);
        --cto-input-bg: rgba(255, 255, 255, 0.05);
        --cto-input-border: rgba(255, 255, 255, 0.1);
        --cto-hover-bg: rgba(255, 255, 255, 0.08);
        --cto-progress-line: rgba(255, 255, 255, 0.1);
    }
}
.dark {
    --cto-bg: #0f172a;
    --cto-card-bg: rgba(30, 41, 59, 0.7);
    --cto-accent: #38bdf8;
    --cto-accent-glow: rgba(56, 189, 248, 0.3);
    --cto-success: #10b981;
    --cto-warning: #fbbf24;
    --cto-error: #f43f5e;
    --cto-text: #f8fafc;
    --cto-text-dim: #94a3b8;
    --cto-bg-gradient-1: rgba(56, 189, 248, 0.05);
    --cto-bg-gradient-2: rgba(16, 185, 129, 0.05);
    --cto-card-shadow: rgba(0, 0, 0, 0.5);
    --cto-border-color: rgba(255, 255, 255, 0.05);
    --cto-input-bg: rgba(255, 255, 255, 0.05);
    --cto-input-border: rgba(255, 255, 255, 0.1);
    --cto-hover-bg: rgba(255, 255, 255, 0.08);
    --cto-progress-line: rgba(255, 255, 255, 0.1);
}

/* CTO Animations */
@keyframes ctoSlideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes ctoSpin {
    to { transform: rotate(360deg); }
}

/* CTO reveal animation */
.cto-reveal {
    opacity: 0;
    transform: translateY(30px);
    animation: ctoSlideUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* CTO Title page */
.cto-title-page {
    min-height: 65vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 60px 20px;
    max-width: 900px;
    margin: 0 auto;
}

/* CTO Card — glassmorphism */
.cto-card {
    background: var(--cto-card-bg);
    backdrop-filter: blur(16px);
    border-radius: 24px;
    padding: 32px 28px;
    border: 1px solid var(--cto-border-color);
    box-shadow: 0 25px 50px -12px var(--cto-card-shadow);
}

/* CTO Stats grid */
.cto-stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    padding: 12px 16px 16px;
}
.cto-stats-wrapper {
    border-radius: 16px;
    background: var(--cto-card-bg);
    border: 1px solid var(--cto-border-color);
    backdrop-filter: blur(16px);
    overflow: hidden;
}
.cto-stats-header {
    text-align: center;
    padding: 10px 16px 0;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--cto-error);
}

/* CTO Choice cards */
.cto-choice-card:hover {
    border-color: var(--cto-accent) !important;
}

/* CTO Confirm button */
.cto-confirm-btn {
    margin-top: 20px;
    padding: 16px 36px;
    font-size: 1.05rem;
    font-weight: 700;
    background: var(--cto-accent);
    color: var(--cto-bg);
    border: none;
    border-radius: 12px;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 8px 25px var(--cto-accent-glow);
    transition: all 0.3s;
    font-family: 'Outfit', sans-serif;
}
.cto-confirm-btn:hover {
    filter: brightness(1.08);
    transform: translateY(-2px);
}

/* CTO Feedback tiers */
.cto-feedback-best { border-color: var(--cto-success) !important; }
.cto-feedback-good { border-color: var(--cto-warning) !important; }
.cto-feedback-poor { border-color: var(--cto-error) !important; }

/* CTO Results tier badge */
.cto-tier-badge {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 700;
    background: var(--cto-input-bg);
    border: 1px solid var(--cto-border-color);
}

/* CTO Certification card */
.cto-cert-card {
    margin-top: 24px;
    text-align: center;
    background: var(--cto-card-bg);
    backdrop-filter: blur(16px);
    border-radius: 24px;
    padding: 32px 28px;
    box-shadow: 0 25px 50px -12px var(--cto-card-shadow);
}

/* Module container backgrounds for CTO */
.module-container .scenario-box {
    font-family: 'Outfit', sans-serif;
}

/* ========== Gradio Integration Styles ========== */

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
    border-left: 6px solid var(--cto-success);
    background: linear-gradient(135deg, rgba(5,150,105,0.08), var(--block-background-fill));
    margin-top: 16px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    font-size: 1.04rem;
    line-height: 1.55;
}
.profile-card.first-score {
    border-left-color: var(--cto-warning);
    background: linear-gradient(135deg, rgba(250,204,21,0.18), var(--block-background-fill));
}
.success-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 8px; }
.success-title { font-size: 1.26rem; font-weight: 900; color: var(--cto-success); }
.success-summary { font-size: 1.06rem; color: var(--body-text-color-subdued); margin-top: 4px; }
.success-delta { font-size: 1.5rem; font-weight: 800; color: var(--cto-success); }
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
.progress-label { font-size: 0.82rem; font-weight: 700; }

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
.row-highlight-me, .row-highlight-team { background: rgba(2, 132, 199, 0.1); font-weight: 700; }

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

/* Impact reveal cards (sequential post-choice reveal) */
.cto-impact-card {
    display: flex; align-items: center; gap: 16px;
    padding: 16px 20px; border-radius: 14px; margin-top: 10px;
    background: var(--cto-input-bg); border: 1px solid var(--cto-border-color);
    opacity: 0; transform: translateY(20px);
    animation: ctoSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.cto-impact-card .cto-impact-icon { font-size: 2rem; flex-shrink: 0; }
.cto-impact-card .cto-impact-text { font-size: 1.05rem; font-weight: 700; color: var(--cto-text); }
.cto-impact-card .cto-impact-detail { font-size: 0.9rem; color: var(--cto-text-dim); margin-top: 2px; }
"""


# ============================================================================
# 9b. CLIENT-SIDE JAVASCRIPT — Consolidated game engine (Gradio 6 head injection)
# ============================================================================

CLIENT_JS = """
// === Dynamically load Outfit font ===
(function(){
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap';
    document.head.appendChild(link);
})();

// =============================================
// GREEN AI CTO — Game Engine
// =============================================

// --- Global State ---
window.ctoState = {energy:4200, water:18500000, co2:1680, cost:2800000, greenScore:8, reputation:12};
window.ctoPrevState = null;
window.ctoChoices = [];
window.ctoSelectedChoice = {};

// --- Round Data (from JSX) ---
window.CTO_ROUNDS = [
    null, // index 0 unused (rounds are 1-5)
    { id:"cooling", title:"La Crisi de Refrigeraci\\u00f3", emoji:"\\ud83c\\udf21\\ufe0f",
      choices:[
        { id:"a", label:"Submergir Servidors en L\\u00edquid Especial", icon:"\\ud83e\\uddf2",
          fx:{energy:-35,water:-70,co2:-30,cost:-20,greenScore:28,reputation:22},
          fb:"Incre\\u00edble! La ciutat conserva la seva aigua. Microsoft ja est\\u00e0 provant aquesta mateixa idea. Acabes d\\u2019estalviar a la ciutat gaireb\\u00e9 60 piscines d\\u2019aigua cada any!", tier:"best" },
        { id:"b", label:"Reutilitzar Aigua + Usar Aire Fred", icon:"\\u267b\\ufe0f",
          fx:{energy:-15,water:-45,co2:-12,cost:-8,greenScore:15,reputation:14},
          fb:"Bona jugada! Reciclar l\\u2019aigua significa que la ciutat conserva aproximadament la meitat del seu subministrament. Els dies freds, la natura fa la refrigeraci\\u00f3 gratis.", tier:"good" },
        { id:"c", label:"Nom\\u00e9s Afegir Sensors al que Hi Ha", icon:"\\ud83d\\udd27",
          fx:{energy:-5,water:-8,co2:-4,cost:-3,greenScore:4,reputation:-5},
          fb:"Ui... Els sensors gaireb\\u00e9 no ajuden \\u2014 segueix sent el mateix sistema malbaratador. Les not\\u00edcies locals publiquen: \\u2018Empresa d\\u2019IA devora aigua durant la sequera.\\u2019", tier:"poor" },
      ],
    },
    { id:"energy", title:"D\\u2019On Ve l\\u2019Energia?", emoji:"\\u26a1",
      choices:[
        { id:"a", label:"Construir una Granja Solar + Bateries", icon:"\\u2600\\ufe0f",
          fx:{energy:-10,water:-5,co2:-55,cost:-15,greenScore:25,reputation:20},
          fb:"Moviment audaç! Els panells solars absorbeixen el sol tot el dia, les bateries mantenen tot funcionant de nit. La contaminaci\\u00f3 de CO\\u2082 de la ciutat cau en picat. L\\u2019alcaldessa est\\u00e0 encantada!", tier:"best" },
        { id:"b", label:"Comprar Energia Neta d\\u2019un Parc E\\u00f2lic/Solar", icon:"\\ud83c\\udf2c\\ufe0f",
          fx:{energy:-3,water:-3,co2:-35,cost:-5,greenScore:16,reputation:12},
          fb:"Bona elecci\\u00f3 \\u2014 aix\\u00f2 \\u00e9s el que fan Google i Apple realment. L\\u2019electricitat de NovaMind ara ve del vent i el sol en lloc de cremar carb\\u00f3 i gas.", tier:"good" },
        { id:"c", label:"Pagar per Compensacions de Carboni", icon:"\\ud83d\\udcdc",
          fx:{energy:0,water:0,co2:-10,cost:-1,greenScore:3,reputation:-8},
          fb:"Plantar arbres est\\u00e0 b\\u00e9, per\\u00f2 NovaMind SEGUEIX cremant combustibles f\\u00f2ssils. Els grups ecologistes ho anomenen fals. La contaminaci\\u00f3 no ha canviat realment gens.", tier:"poor" },
      ],
    },
    { id:"models", title:"IA de la Mida Adequada", emoji:"\\ud83e\\udde0",
      choices:[
        { id:"a", label:"Ajustar la Mida del Model a la Dificultat", icon:"\\ud83e\\udea9",
          fx:{energy:-40,water:-30,co2:-38,cost:-35,greenScore:22,reputation:15},
          fb:"Genial! 8 de cada 10 preguntes ara fan servir el model d\\u2019IA petit \\u2014 fa servir 50 vegades menys energia, i ning\\u00fa nota la difer\\u00e8ncia. Aix\\u00ed \\u00e9s exactament com treballen les empreses d\\u2019IA m\\u00e9s intel\\u00b7ligents.", tier:"best" },
        { id:"b", label:"Entrenar una IA M\\u00e9s Petita i Llesta", icon:"\\ud83e\\uddec",
          fx:{energy:-25,water:-18,co2:-22,cost:-20,greenScore:14,reputation:10},
          fb:"Bona idea! El model d\\u2019IA m\\u00e9s petit ha apr\\u00e8s la majoria dels trucs del gran. Gestiona 9 de cada 10 preguntes perfectament, fent servir molta menys energia.", tier:"good" },
        { id:"c", label:"Nom\\u00e9s Guardar Respostes Repetides", icon:"\\ud83d\\udcbe",
          fx:{energy:-10,water:-5,co2:-8,cost:-10,greenScore:5,reputation:3},
          fb:"Guardar respostes ajuda una mica, per\\u00f2 la majoria de preguntes s\\u00f3n \\u00faniques \\u2014 el model m\\u00e9s gran segueix funcionant gaireb\\u00e9 sempre. \\u00c9s com posar una tireta petita en un problema gran.", tier:"poor" },
      ],
    },
    { id:"location", title:"Ubicaci\\u00f3, Ubicaci\\u00f3, Ubicaci\\u00f3", emoji:"\\ud83d\\udccd",
      choices:[
        { id:"a", label:"Construir a la Freda Escandin\\u00e0via", icon:"\\ud83c\\uddf8\\ud83c\\uddea",
          fx:{energy:-20,water:-40,co2:-30,cost:-18,greenScore:20,reputation:18},
          fb:"Aix\\u00f2 \\u00e9s el que van fer Meta i Google realment! L\\u2019aire gelat refreda els ordinadors gratis. Gaireb\\u00e9 tota l\\u2019electricitat \\u00e9s neta. Elecci\\u00f3 brillant!", tier:"best" },
        { id:"b", label:"Construir a la Plujosa Oregon", icon:"\\ud83c\\udf32",
          fx:{energy:-10,water:-20,co2:-18,cost:-10,greenScore:12,reputation:10},
          fb:"Bona elecci\\u00f3! Amazon i Google ja tenen grans edificis all\\u00e0. Els rius proporcionen energia hidroel\\u00e8ctrica neta, i el clima suau significa menys refrigeraci\\u00f3 necess\\u00e0ria.", tier:"good" },
        { id:"c", label:"Quedar-se al Desert Calor\\u00f3s", icon:"\\ud83c\\udfdc\\ufe0f",
          fx:{energy:5,water:10,co2:5,cost:5,greenScore:-3,reputation:-10},
          fb:"El terreny barat sona genial, per\\u00f2 la calor abrasadora significa 3 vegades m\\u00e9s costos de refrigeraci\\u00f3. La xarxa de gas anul\\u00b7la els teus guanys anteriors. NovaMind apareix en una llista de \\u2018pitjors contaminadors\\u2019.", tier:"poor" },
      ],
    },
    { id:"transparency", title:"Control d\\u2019Honestedat", emoji:"\\ud83d\\udcca",
      choices:[
        { id:"a", label:"Marcador P\\u00fablic en Viu", icon:"\\ud83d\\udce1",
          fx:{energy:-5,water:-3,co2:-5,cost:2,greenScore:18,reputation:25},
          fb:"NovaMind es converteix en la PRIMERA empresa d\\u2019IA en mostrar els seus n\\u00fameros en viu! Cient\\u00edfics, periodistes i altres ciutats elogien el teu lideratge. Acabes d\\u2019establir un nou est\\u00e0ndard per a tota la ind\\u00fastria!", tier:"best" },
        { id:"b", label:"Informe Anual", icon:"\\ud83d\\udcc4",
          fx:{energy:-2,water:-1,co2:-2,cost:0,greenScore:8,reputation:10},
          fb:"Un informe anual \\u00e9s el que ja fan Google i Microsoft. Est\\u00e0 b\\u00e9, per\\u00f2 un cop l\\u2019any no \\u00e9s suficient per mantenir les empreses realment honestes.", tier:"good" },
        { id:"c", label:"Nom\\u00e9s Compartir el que la Llei Obligui", icon:"\\ud83d\\udd12",
          fx:{energy:0,water:0,co2:0,cost:0,greenScore:-2,reputation:-15},
          fb:"Els investigadors denuncien NovaMind. Una publicaci\\u00f3 viral els compara amb empreses petrolieres que amaguen dades de contaminaci\\u00f3. La gent deixa de confiar-hi.", tier:"poor" },
      ],
    },
];

// --- INIT STATE ---
window.CTO_INIT = {energy:50400, water:222000000, co2:20160, cost:33600000, greenScore:8, reputation:12};

// --- Apply effects (percentage-based) ---
function ctoApply(stats, fx) {
    return {
        energy: Math.max(0, Math.round(stats.energy * (1 + fx.energy / 100))),
        water: Math.max(0, Math.round(stats.water * (1 + fx.water / 100))),
        co2: Math.max(0, Math.round(stats.co2 * (1 + fx.co2 / 100))),
        cost: Math.max(0, Math.round(stats.cost * (1 + fx.cost / 100))),
        greenScore: Math.min(100, Math.max(0, stats.greenScore + fx.greenScore)),
        reputation: Math.min(100, Math.max(0, stats.reputation + fx.reputation)),
    };
}

// --- Grade calculator ---
function ctoGrade(s) {
    if (s >= 90) return { l:"A+", c:"var(--cto-success)", t:"Llegendari" };
    if (s >= 75) return { l:"A", c:"var(--cto-success)", t:"Excel\\u00b7lent" };
    if (s >= 60) return { l:"B", c:"var(--cto-accent)", t:"Genial" };
    if (s >= 45) return { l:"C", c:"var(--cto-warning)", t:"Acceptable" };
    if (s >= 30) return { l:"D", c:"var(--cto-warning)", t:"Cal Millorar" };
    return { l:"F", c:"var(--cto-error)", t:"Cr\\u00edtic" };
}

// --- Number formatter ---
function ctoFmt(n) {
    return n >= 1e6 ? (n/1e6).toFixed(1)+"M" : n >= 1e3 ? (n/1e3).toFixed(0)+"K" : String(n);
}

// --- Render stats grid ---
function ctoRenderStats(containerId, stats, prev) {
    var el = document.getElementById(containerId);
    if (!el) return;
    var items = [
        {k:"energy", l:"Energia de Fam\\u00edlies", u:"llars/any", i:"\\u26a1", conv:3.5, up:false},
        {k:"water", l:"\\u00das d\\u2019Aigua", u:"piscines/any", i:"\\ud83d\\udca7", conv:2500000, up:false},
        {k:"co2", l:"Contaminaci\\u00f3 CO\\u2082", u:"cotxes/any", i:"\\ud83d\\ude97", conv:4.2, up:false},
        {k:"greenScore", l:"Puntuaci\\u00f3 Verda", u:"/100", i:"\\ud83c\\udf31", conv:1, up:true},
    ];
    var html = "";
    for (var idx = 0; idx < items.length; idx++) {
        var it = items[idx];
        var raw = stats[it.k];
        var v = it.k === "greenScore" ? raw : (it.conv >= 1 ? Math.round(raw / it.conv) : Math.round(raw / it.conv));
        var valStr = it.k === "greenScore" ? String(v) : v.toLocaleString();
        var deltaHtml = "";
        if (prev) {
            var prevRaw = prev[it.k];
            var diff = raw - prevRaw;
            if (diff !== 0) {
                var dv = it.k === "greenScore" ? diff : (it.conv >= 1 ? Math.round(diff / it.conv) : Math.round(diff / it.conv));
                var improved = it.up ? diff > 0 : diff < 0;
                var dColor = improved ? "var(--cto-success)" : "var(--cto-error)";
                var arrow = diff > 0 ? "\\u2191" : "\\u2193";
                var absDv = Math.abs(dv);
                var dLabel = it.k === "greenScore" ? (arrow + " " + absDv + " pts") : (arrow + " " + absDv.toLocaleString());
                deltaHtml = '<div style="font-size:0.75rem; margin-top:2px; color:' + dColor + ';">' + dLabel + '</div>';
            }
        }
        html += '<div style="text-align:center; padding:8px 4px;">'
            + '<div style="font-size:0.75rem; color:var(--cto-text-dim); text-transform:uppercase; letter-spacing:1px;">' + it.i + ' ' + it.l + '</div>'
            + '<div style="font-size:1.1rem; font-weight:800; color:var(--cto-text); margin-top:4px;">' + valStr + '</div>'
            + '<div style="font-size:0.7rem; color:var(--cto-text-dim);">' + it.u + '</div>'
            + deltaHtml
            + '</div>';
    }
    el.innerHTML = html;
}

// --- Select a choice card ---
function ctoSelectChoice(roundIdx, choiceIdx) {
    // Deselect all choices in this round
    for (var i = 0; i < 3; i++) {
        var card = document.getElementById('cto-choice-' + roundIdx + '-' + i);
        var radio = document.getElementById('cto-choice-radio-' + roundIdx + '-' + i);
        var icon = document.getElementById('cto-choice-icon-' + roundIdx + '-' + i);
        if (card) {
            card.style.background = 'var(--cto-input-bg)';
            card.style.borderColor = 'var(--cto-border-color)';
        }
        if (radio) {
            radio.style.borderColor = 'var(--cto-input-border)';
            radio.style.background = 'transparent';
            radio.innerHTML = '';
        }
        if (icon) {
            icon.style.background = 'var(--cto-input-bg)';
        }
    }
    // Select the clicked choice
    var selCard = document.getElementById('cto-choice-' + roundIdx + '-' + choiceIdx);
    var selRadio = document.getElementById('cto-choice-radio-' + roundIdx + '-' + choiceIdx);
    var selIcon = document.getElementById('cto-choice-icon-' + roundIdx + '-' + choiceIdx);
    if (selCard) {
        selCard.style.background = 'rgba(56,189,248,0.08)';
        selCard.style.borderColor = 'var(--cto-accent)';
    }
    if (selRadio) {
        selRadio.style.borderColor = 'var(--cto-accent)';
        selRadio.style.background = 'var(--cto-accent)';
        selRadio.innerHTML = '<span style="color:var(--cto-bg); font-size:0.85rem; font-weight:700;">\\u2713</span>';
    }
    if (selIcon) {
        selIcon.style.background = 'var(--cto-hover-bg)';
    }
    window.ctoSelectedChoice[roundIdx] = choiceIdx;
    // Show confirm button
    var btn = document.getElementById('cto-confirm-btn-' + roundIdx);
    if (btn) btn.style.display = 'inline-block';
}

// --- Confirm decision ---
function ctoConfirmDecision(roundIdx) {
    var choiceIdx = window.ctoSelectedChoice[roundIdx];
    if (choiceIdx === undefined || choiceIdx === null) return;

    var roundData = window.CTO_ROUNDS[roundIdx];
    if (!roundData) return;
    var choice = roundData.choices[choiceIdx];
    if (!choice) return;

    // Save previous state
    window.ctoPrevState = JSON.parse(JSON.stringify(window.ctoState));

    // Apply effects
    window.ctoState = ctoApply(window.ctoState, choice.fx);
    window.ctoChoices.push(choice);

    // Hide choices container
    var choicesContainer = document.getElementById('cto-choices-container-' + roundIdx);
    if (choicesContainer) choicesContainer.style.display = 'none';

    // Build feedback
    var tc = {best:"var(--cto-success)", good:"var(--cto-warning)", poor:"var(--cto-error)"};
    var tl = {best:"\\ud83c\\udf1f Elecci\\u00f3 Incre\\u00edble!", good:"\\ud83d\\udc4d Bona Elecci\\u00f3!", poor:"\\u26a0\\ufe0f Oi..."};

    // Compute relatable impact values
    var prevState = window.ctoPrevState;
    var newState = window.ctoState;
    var energyDelta = prevState.energy - newState.energy;
    var waterDelta = prevState.water - newState.water;
    var co2Delta = prevState.co2 - newState.co2;
    var homesVal = Math.abs(Math.round(energyDelta / 3.5));
    var poolsVal = Math.abs(waterDelta / 2500000).toFixed(1);
    var carsVal = Math.abs(co2Delta / 4.2).toFixed(0);
    var prevGreen = prevState.greenScore;
    var newGreen = newState.greenScore;

    // Determine positive/negative language
    var energyGood = energyDelta > 0;
    var waterGood = waterDelta > 0;
    var co2Good = co2Delta > 0;
    var energyText = energyGood ? "Has estalviat prou energia per a " + homesVal + " fam\\u00edlies!" : "Has afegit " + homesVal + " llars d\\u2019\\u00fas d\\u2019energia.";
    var waterText = waterGood ? "Has estalviat " + poolsVal + " piscines d\\u2019aigua!" : "Has gastat " + poolsVal + " piscines m\\u00e9s d\\u2019aigua.";
    var co2Text = co2Good ? "Aix\\u00f2 \\u00e9s com treure " + carsVal + " cotxes de la carretera!" : "Aix\\u00f2 \\u00e9s com afegir " + carsVal + " cotxes a la carretera.";
    var energyColor = energyGood ? "var(--cto-success)" : "var(--cto-error)";
    var waterColor = waterGood ? "var(--cto-success)" : "var(--cto-error)";
    var co2Color = co2Good ? "var(--cto-success)" : "var(--cto-error)";

    // Build feedback card + hidden impact reveal container
    var fbHtml = '<div class="cto-card cto-feedback-' + choice.tier + '" style="animation:ctoSlideUp 0.5s ease;">'
        + '<div style="font-size:1rem; font-weight:800; color:' + tc[choice.tier] + '; margin-bottom:8px;">' + tl[choice.tier] + '</div>'
        + '<p style="font-size:1.05rem; color:var(--cto-text-dim); line-height:1.7; margin:0;">' + choice.fb + '</p>'
        + '</div>'
        + '<div id="cto-impact-reveal-' + roundIdx + '">'
        + '<div id="cto-impact-energy-' + roundIdx + '" class="cto-impact-card" style="display:none;">'
        + '<div class="cto-impact-icon">\\u26a1</div>'
        + '<div><div class="cto-impact-text" style="color:' + energyColor + ';">' + energyText + '</div>'
        + '<div class="cto-impact-detail">\\u26a1 Energia</div></div></div>'
        + '<div id="cto-impact-water-' + roundIdx + '" class="cto-impact-card" style="display:none;">'
        + '<div class="cto-impact-icon">\\ud83d\\udca7</div>'
        + '<div><div class="cto-impact-text" style="color:' + waterColor + ';">' + waterText + '</div>'
        + '<div class="cto-impact-detail">\\ud83d\\udca7 Aigua</div></div></div>'
        + '<div id="cto-impact-co2-' + roundIdx + '" class="cto-impact-card" style="display:none;">'
        + '<div class="cto-impact-icon">\\ud83d\\ude97</div>'
        + '<div><div class="cto-impact-text" style="color:' + co2Color + ';">' + co2Text + '</div>'
        + '<div class="cto-impact-detail">\\ud83d\\ude97 CO\\u2082</div></div></div>'
        + '<div id="cto-impact-green-' + roundIdx + '" class="cto-impact-card" style="display:none;">'
        + '<div class="cto-impact-icon">\\ud83c\\udf31</div>'
        + '<div><div class="cto-impact-text" style="color:var(--cto-success);">Puntuaci\\u00f3 Verda: ' + prevGreen + ' \\u2192 ' + newGreen + '</div>'
        + '<div class="cto-impact-detail">\\ud83c\\udf31 Puntuaci\\u00f3 Verda</div></div></div>'
        + '<div id="cto-impact-done-' + roundIdx + '" style="display:none; margin-top:12px; font-size:0.9rem; color:var(--cto-accent); font-weight:700;">\\u2705 Fet! Fes clic a SEG\\u00dcENT per continuar.</div>'
        + '</div>';

    var fbContainer = document.getElementById('cto-feedback-' + roundIdx);
    if (fbContainer) fbContainer.innerHTML = fbHtml;

    // Sequential reveal with staggered delays
    function showCard(id, delay) {
        setTimeout(function() {
            var el = document.getElementById(id);
            if (el) { el.style.display = 'flex'; }
        }, delay);
    }
    showCard('cto-impact-energy-' + roundIdx, 800);
    showCard('cto-impact-water-' + roundIdx, 2000);
    showCard('cto-impact-co2-' + roundIdx, 3200);
    showCard('cto-impact-green-' + roundIdx, 4400);
    setTimeout(function() {
        var doneEl = document.getElementById('cto-impact-done-' + roundIdx);
        if (doneEl) { doneEl.style.display = 'block'; }
    }, 5200);
}

// --- Render Results ---
function ctoRenderResults() {
    var container = document.getElementById('cto-results-container');
    if (!container) return;

    var stats = window.ctoState;
    var choices = window.ctoChoices;
    var INIT = window.CTO_INIT;
    var g = ctoGrade(stats.greenScore);
    var ok = stats.greenScore >= 60;
    var er = Math.round((1 - stats.energy / INIT.energy) * 100);
    var wr = Math.round((1 - stats.water / INIT.water) * 100);
    var cr = Math.round((1 - stats.co2 / INIT.co2) * 100);
    var bc = 0;
    for (var i = 0; i < choices.length; i++) { if (choices[i].tier === "best") bc++; }

    // Status line
    var statusColor = ok ? "var(--cto-success)" : "var(--cto-warning)";
    var statusText = ok ? "\\u2705 Tot Fet!" : "\\u26a0\\ufe0f Tot Fet!";

    // Progress rings
    var ringItems = [
        {l:"Puntuaci\\u00f3 Verda", v:stats.greenScore, m:100},
        {l:"Millors Eleccions", v:bc, m:5}
    ];
    var ringsHtml = '';
    for (var ri = 0; ri < ringItems.length; ri++) {
        var x = ringItems[ri];
        var pct = Math.min(100, (x.v / x.m) * 100);
        var da = Math.round(pct * 2.14);
        ringsHtml += '<div style="text-align:center;">'
            + '<div style="font-size:0.75rem; color:var(--cto-text-dim); text-transform:uppercase; letter-spacing:2px;">' + x.l + '</div>'
            + '<div style="position:relative; width:80px; height:80px; margin:8px auto;">'
            + '<svg width="80" height="80" viewBox="0 0 80 80">'
            + '<circle cx="40" cy="40" r="34" fill="none" stroke="var(--cto-input-bg)" stroke-width="6"/>'
            + '<circle cx="40" cy="40" r="34" fill="none" stroke="var(--cto-accent)" stroke-width="6" '
            + 'stroke-dasharray="' + da + ' 214" stroke-linecap="round" transform="rotate(-90 40 40)" '
            + 'style="transition:stroke-dasharray 1.2s cubic-bezier(0.16,1,0.3,1);"/>'
            + '</svg>'
            + '<div style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:1.2rem; font-weight:800; color:var(--cto-text);">' + x.v + '</div>'
            + '</div></div>';
    }

    // Impact summary — relatable units
    var homesSaved = Math.round((INIT.energy - stats.energy) / 3.5);
    var poolsSaved = ((INIT.water - stats.water) / 2500000).toFixed(1);
    var carsRemoved = ((INIT.co2 - stats.co2) / 4.2).toFixed(0);
    var impactItems = [
        {l:"Llars d\\u2019Energia Estalviades", v:homesSaved, i:"\\u26a1"},
        {l:"Piscines d\\u2019Aigua Estalviades", v:poolsSaved, i:"\\ud83d\\udca7"},
        {l:"Cotxes de CO\\u2082 Eliminats", v:carsRemoved, i:"\\ud83d\\ude97"}
    ];
    var impactHtml = '';
    for (var ii = 0; ii < impactItems.length; ii++) {
        var imp = impactItems[ii];
        impactHtml += '<div style="text-align:center; padding:16px; border-radius:14px; background:var(--cto-input-bg);">'
            + '<div style="font-size:1.8rem; font-weight:800; color:var(--cto-accent);">' + imp.i + ' ' + imp.v + '</div>'
            + '<div style="font-size:0.8rem; color:var(--cto-text-dim); margin-top:8px; text-transform:uppercase; letter-spacing:1px;">' + imp.l + '</div>'
            + '</div>';
    }

    // Audit trail
    var tc2 = {best:"var(--cto-success)", good:"var(--cto-warning)", poor:"var(--cto-error)"};
    var tl2 = {best:"Millor", good:"Bona", poor:"Pobre"};
    var roundNames = [null, "Refrigeraci\\u00f3", "Font d\\u2019Energia", "Efici\\u00e8ncia d\\u2019IA", "Ubicaci\\u00f3", "Transpar\\u00e8ncia"];
    var roundEmojis = [null, "\\ud83c\\udf21\\ufe0f", "\\u26a1", "\\ud83e\\udde0", "\\ud83d\\udccd", "\\ud83d\\udcca"];
    var auditHtml = '';
    for (var ai = 0; ai < choices.length; ai++) {
        var ch = choices[ai];
        var borderBot = ai < choices.length - 1 ? "1px solid var(--cto-border-color)" : "none";
        auditHtml += '<div style="display:flex; align-items:center; gap:12px; padding:10px 0; border-bottom:' + borderBot + ';">'
            + '<span style="font-size:1.3rem;">' + roundEmojis[ai+1] + '</span>'
            + '<div style="flex:1;">'
            + '<div style="font-size:1rem; font-weight:600; color:var(--cto-text);">' + ch.label + '</div>'
            + '<div style="font-size:0.8rem; color:var(--cto-text-dim);">' + roundNames[ai+1] + '</div>'
            + '</div>'
            + '<div class="cto-tier-badge" style="color:' + tc2[ch.tier] + ';">' + tl2[ch.tier] + '</div>'
            + '</div>';
    }

    // Certification
    var certHtml = '';
    if (ok) {
        certHtml = '<div class="cto-cert-card" style="border:2px solid var(--cto-success);">'
            + '<div style="font-size:3rem;">\\ud83c\\udfc5</div>'
            + '<h2 style="font-size:1.6rem; font-weight:800; color:var(--cto-success); margin-top:12px;">APROVAT! \\ud83c\\udf89</h2>'
            + '<p style="font-size:1.05rem; color:var(--cto-text-dim); margin-top:8px; line-height:1.7; max-width:440px; margin-left:auto; margin-right:auto;">'
            + 'NovaMind ha superat els teus est\\u00e0ndards verds! L\\u2019aire, l\\u2019aigua i l\\u2019energia de la teva ciutat estan protegits \\u2014 gr\\u00e0cies a les TEVES decisions.</p>'
            + '<div style="margin-top:20px; display:inline-block; padding:12px 28px; border-radius:12px; background:rgba(16,185,129,0.1); border:1px solid var(--cto-success); font-size:1rem; color:var(--cto-success); font-weight:700;">'
            + '\\u2705 APROVAT PER CONSTRUIR</div>'
            + '</div>';
    } else {
        certHtml = '<div class="cto-cert-card" style="border:2px solid var(--cto-warning);">'
            + '<div style="font-size:3rem;">\\ud83d\\udd04</div>'
            + '<h2 style="font-size:1.6rem; font-weight:800; color:var(--cto-warning); margin-top:12px;">NECESSITA M\\u00c9S TREBALL</h2>'
            + '<p style="font-size:1.05rem; color:var(--cto-text-dim); margin-top:8px; line-height:1.7; max-width:440px; margin-left:auto; margin-right:auto;">'
            + 'NovaMind ha millorat, per\\u00f2 la contaminaci\\u00f3 de la teva ciutat segueix sent massa alta (Puntuaci\\u00f3 Verda per sota de 60). L\\u2019alcaldessa els envia de tornada \\u2014 la teva ciutat es mereix m\\u00e9s.</p>'
            + '<div style="margin-top:20px; display:inline-block; padding:12px 28px; border-radius:12px; background:rgba(251,191,36,0.1); border:1px solid var(--cto-warning); font-size:1rem; color:var(--cto-warning); font-weight:700;">'
            + '\\u23f3 ENVIAT DE TORNADA PER CANVIS</div>'
            + '</div>';
    }

    // What you learned
    var learnHtml = '<div class="cto-card" style="margin-top:24px; text-align:center;">'
        + '<div style="font-size:1.1rem; font-weight:800; color:var(--cto-text);">\\ud83d\\udca1 El Que Acabes d\\u2019Aprendre</div>'
        + '<p style="font-size:1rem; color:var(--cto-text-dim); line-height:1.7; margin-top:8px; max-width:480px; margin-left:auto; margin-right:auto;">'
        + 'Empreses reals com Google, Meta i Microsoft s\\u2019enfronten a aquestes mateixes decisions cada dia. Com refreden els ordinadors, d\\u2019on obtenen l\\u2019energia, quina mida d\\u2019IA fan servir, on construeixen i com d\\u2019honestos s\\u00f3n \\u2014 aquestes cinc coses decideixen si la IA ajuda o perjudica el nostre planeta.</p>'
        + '<div style="font-size:0.8rem; color:var(--cto-text-dim); margin-top:12px;">Basat en dades reals de IEA, MIT, UC Riverside, VU Amsterdam (2024\\u20132025)</div>'
        + '</div>';

    var climateHtml = '<div class="cto-card" style="margin-top:24px; text-align:center;">'
        + '<div style="font-size:1.1rem; font-weight:800; color:var(--cto-text);">\\ud83c\\udf0d La Visi\\u00f3 Global</div>'
        + '<p style="font-size:1rem; color:var(--cto-text-dim); line-height:1.7; margin-top:8px; max-width:480px; margin-left:auto; margin-right:auto;">'
        + 'Els centres de dades d\\u2019IA ja fan servir m\\u00e9s electricitat que alguns pa\\u00efsos sencers. Cada elecci\\u00f3 que acabes de fer \\u2014 refrigeraci\\u00f3, energia, mida del model, ubicaci\\u00f3, transpar\\u00e8ncia \\u2014 \\u00e9s una palanca real que decideix quant escalfa la IA el nostre planeta.</p>'
        + '<p style="font-size:1rem; color:var(--cto-success); font-weight:700; line-height:1.7; margin-top:12px; max-width:480px; margin-left:auto; margin-right:auto;">'
        + 'Pensar amb antelaci\\u00f3 sobre la sostenibilitat de la IA \\u00e9s una de les maneres m\\u00e9s grans en qu\\u00e8 la teva generaci\\u00f3 pot ajudar a lluitar contra el canvi clim\\u00e0tic.</p>'
        + '</div>';

    container.innerHTML = '<div style="text-align:center; font-size:0.875rem; font-weight:800; letter-spacing:3px; color:' + statusColor + '; text-transform:uppercase;">'
        + statusText + '</div>'
        + '<h1 style="text-align:center; font-size:clamp(2rem, 7vw, 3.2rem); font-weight:800; margin-top:16px; color:var(--cto-text);">'
        + '<span style="color:' + g.c + ';">' + g.l + '</span> \\u2014 ' + g.t + '</h1>'
        + '<div style="display:grid; grid-template-columns:repeat(2,1fr); gap:16px; margin-top:32px;">' + ringsHtml + '</div>'
        + '<div class="cto-card" style="margin-top:28px;">'
        + '<h3 style="font-size:1.2rem; font-weight:800; color:var(--cto-text); margin:0 0 16px 0;">El Que Han Canviat les Teves Decisions</h3>'
        + '<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px;">' + impactHtml + '</div></div>'
        + '<div class="cto-card" style="margin-top:20px;">'
        + '<h3 style="font-size:1.1rem; font-weight:800; color:var(--cto-text); margin:0 0 12px 0;">Les Teves 5 Eleccions</h3>'
        + auditHtml + '</div>'
        + certHtml
        + learnHtml
        + climateHtml;
}

// --- Init functions for each module ---
(function ctoInitStats1(){
    var el = document.getElementById('cto-stats-1');
    if (!el) { setTimeout(ctoInitStats1, 200); return; }
    ctoRenderStats('cto-stats-1', window.ctoState, window.ctoPrevState);
})();

(function ctoInitStats2(){
    var el = document.getElementById('cto-stats-2');
    if (!el) { setTimeout(ctoInitStats2, 200); return; }
    ctoRenderStats('cto-stats-2', window.ctoState, window.ctoPrevState);
})();

(function ctoInitStats3(){
    var el = document.getElementById('cto-stats-3');
    if (!el) { setTimeout(ctoInitStats3, 200); return; }
    ctoRenderStats('cto-stats-3', window.ctoState, window.ctoPrevState);
})();

(function ctoInitStats4(){
    var el = document.getElementById('cto-stats-4');
    if (!el) { setTimeout(ctoInitStats4, 200); return; }
    ctoRenderStats('cto-stats-4', window.ctoState, window.ctoPrevState);
})();

(function ctoInitStats5(){
    var el = document.getElementById('cto-stats-5');
    if (!el) { setTimeout(ctoInitStats5, 200); return; }
    ctoRenderStats('cto-stats-5', window.ctoState, window.ctoPrevState);
})();

(function ctoInitResults(){
    var el = document.getElementById('cto-results-container');
    if (!el) { setTimeout(ctoInitResults, 200); return; }
    // Only render if we have at least 5 choices (all rounds played)
    if (window.ctoChoices && window.ctoChoices.length >= 5) {
        ctoRenderResults();
    }
})();

// Re-render stats when modules become visible (navigation triggers this)
function ctoRefreshVisibleStats() {
    for (var r = 1; r <= 5; r++) {
        var el = document.getElementById('cto-stats-' + r);
        if (el && el.offsetParent !== null) {
            ctoRenderStats('cto-stats-' + r, window.ctoState, window.ctoPrevState);
        }
    }
    // Check if results container is visible and needs rendering
    var resEl = document.getElementById('cto-results-container');
    if (resEl && resEl.offsetParent !== null && window.ctoChoices && window.ctoChoices.length >= 5) {
        ctoRenderResults();
    }
}

// Poll to refresh stats on navigation
setInterval(ctoRefreshVisibleStats, 500);
"""

HEAD_HTML = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap">\n'
    '<script>\n' + CLIENT_JS + '\n</script>'
)


# ============================================================================
# 10. APP FACTORY
# ============================================================================

def create_fairness_fixer_ca_sustainability_app(theme_primary_hue: str = "indigo"):
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
                "<h2>Preparant-se...</h2>"
                "<p>Carregant dades de la Br\u00faixola Moral...</p>"
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

                    # Quiz content — only for modules in QUIZ_CONFIG (1-6)
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
                            else "CONTINUAR A L'ACTIVITAT 8 →"
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
                            <strong>Sostenibilitat %</strong> reflecteix el teu progr&eacute;s de Br&uacute;ixola Moral a trav&eacute;s de la simulaci&oacute;.<br/>
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
                            "\u274c No del tot! Torna a llegir la informaci\u00f3 de la ronda i intenta-ho de nou.</div>",
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
                "<div class='hint-box'>Autenticaci\u00f3 fallida. Si us plau, accedeix des de l\u2019enlla\u00e7 del curs.</div>",
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
                if(targetId === 'module-6' && typeof ctoRenderResults === 'function') {{
                  var _rp = setInterval(() => {{
                    var c = document.getElementById('cto-results-container');
                    if(c) {{ clearInterval(_rp); ctoRenderResults(); }}
                  }}, 100);
                }}
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

                def make_prev_handler(p_col, c_col, target_id):
                    def navigate_prev():
                        yield gr.update(visible=False), gr.update(visible=False)
                        yield gr.update(visible=True), gr.update(visible=False)
                    return navigate_prev

                prev_btn.click(
                    fn=make_prev_handler(prev_col, curr_col, prev_target_id),
                    outputs=[prev_col, curr_col],
                    js=nav_js(prev_target_id, "Carregant..."),
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
            js="() => { try { window.parent.postMessage('navigate-to-activity-8', '*'); } catch(e) {} }"
        )

        return demo

# ============================================================================
# LAUNCH
# ============================================================================

def launch_fairness_fixer_ca_sustainability_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8083,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    app = create_fairness_fixer_ca_sustainability_app(theme_primary_hue=theme_primary_hue)
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        theme=gr.themes.Soft(primary_hue=theme_primary_hue),
        css=css,
        head=HEAD_HTML,
        **kwargs
    )


if __name__ == "__main__":
    launch_fairness_fixer_ca_sustainability_app(share=False, debug=True, height=1000)

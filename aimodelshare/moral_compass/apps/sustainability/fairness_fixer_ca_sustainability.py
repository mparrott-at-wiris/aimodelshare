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
                    <span style="font-size:0.875rem; color:var(--cto-text-dim);">NovaMind AI &mdash; Tauler del CTO</span>
                </div>
                <div id="cto-stats-{round_idx}" class="cto-stats-grid"></div>
                <div style="display:flex; gap:6px; margin-top:16px;">
                    {progress_segments}
                </div>
            </div>

            <div class="cto-reveal" style="animation-delay:0.2s;">
                <div class="cto-card" style="margin-top:28px;">
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                        <span style="font-size:2rem;">{emoji}</span>
                        <div>
                            <div style="font-size:0.75rem; color:var(--cto-warning); font-weight:800; letter-spacing:3px; text-transform:uppercase;">Informe Entrant</div>
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
                    Confirmar Decisi&oacute; &rarr;
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
        "title": "IA VERDA CTO",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="cto-title-page">
                    <div class="cto-reveal" style="animation-delay:0s;">
                        <div style="font-size:0.875rem; font-weight:800; letter-spacing:3px; color:var(--cto-error); text-transform:uppercase; margin-bottom:24px; text-align:center;">
                            &#9888;&#65039; Simulaci&oacute; Activa
                        </div>
                    </div>
                    <div class="cto-reveal" style="animation-delay:0.3s;">
                        <h1 style="font-size:clamp(2.2rem, 8vw, 3.5rem); font-weight:800; text-align:center; line-height:1.1; letter-spacing:-1px; color:var(--cto-text); margin:0;">
                            IA VERDA<br/><span style="color:var(--cto-accent);">CTO</span>
                        </h1>
                    </div>
                    <div class="cto-reveal" style="animation-delay:0.6s;">
                        <p style="font-size:1.125rem; color:var(--cto-text-dim); text-align:center; max-width:480px; margin:28px auto 0; line-height:1.7;">
                            Acabes de ser ascendit/da a <strong style="color:var(--cto-text); font-weight:600;">Director/a de Tecnologia (CTO)</strong> de NovaMind AI.
                            La teva plataforma serveix 50 milions d&#39;usuaris &mdash; i est&agrave; <strong style="color:var(--cto-error); font-weight:700;">destruint el planeta</strong>.
                            La junta directiva t&#39;ha donat 5 rondes per solucionar-ho.
                        </p>
                    </div>
                    <div class="cto-reveal" style="animation-delay:0.9s;">
                        <div style="display:flex; gap:12px; margin-top:32px; flex-wrap:wrap; justify-content:center;">
                            <div style="padding:14px 20px; border-radius:12px; background:var(--cto-input-bg); border:1px solid var(--cto-border-color); text-align:center; min-width:120px;">
                                <div style="font-size:0.85rem; color:var(--cto-warning); font-weight:600;">&#9889; Energia</div>
                                <div style="font-size:1.15rem; font-weight:800; color:var(--cto-text); margin-top:4px;">4.200 MWh/mes</div>
                            </div>
                            <div style="padding:14px 20px; border-radius:12px; background:var(--cto-input-bg); border:1px solid var(--cto-border-color); text-align:center; min-width:120px;">
                                <div style="font-size:0.85rem; color:var(--cto-error); font-weight:600;">&#128167; Aigua</div>
                                <div style="font-size:1.15rem; font-weight:800; color:var(--cto-text); margin-top:4px;">18,5M L/mes</div>
                            </div>
                            <div style="padding:14px 20px; border-radius:12px; background:var(--cto-input-bg); border:1px solid var(--cto-border-color); text-align:center; min-width:120px;">
                                <div style="font-size:0.85rem; color:var(--cto-text-dim); font-weight:600;">&#127793; Puntuaci&oacute; Verda</div>
                                <div style="font-size:1.15rem; font-weight:800; color:var(--cto-text); margin-top:4px;">8 / 100</div>
                            </div>
                        </div>
                    </div>
                    <div class="cto-reveal" style="animation-delay:1.2s;">
                        <div style="text-align:center; margin-top:16px;">
                            <p style="font-size:0.875rem; color:var(--cto-text-dim);">5 decisions &middot; Conseq&uuml;&egrave;ncies reals &middot; Pots salvar NovaMind?</p>
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
            brief="El teu centre de dades a Phoenix funciona 24/7 amb torres de refrigeraci\u00f3 per aire tradicionals que consumeixen milions de litres d&#39;aigua de la ciutat. La comunitat local est\u00e0 furiosa &mdash; estan en sequera. La refrigeraci\u00f3 consumeix el 40% de la teva factura energ\u00e8tica.",
            question="Com a CTO, com redissenyes la refrigeraci\u00f3?",
            choices=[
                {"icon": "\U0001f9ca", "label": "Refrigeraci\u00f3 per Immersi\u00f3 L\u00edquida", "desc": "Submergir els servidors en fluid no conductor. Gran cost inicial, per\u00f2 elimina l\u2019\u00fas d\u2019aigua per a refrigeraci\u00f3."},
                {"icon": "\u267b\ufe0f", "label": "H\u00edbrid: Aire + Aigua Reciclada", "desc": "Canviar a aigua grisa reciclada i afegir refrigeraci\u00f3 per aire lliure els mesos m\u00e9s frescos."},
                {"icon": "\U0001f527", "label": "Optimitzar el Sistema Actual", "desc": "Simplement ajustar les torres de refrigeraci\u00f3 actuals &mdash; afegir sensors i controls intel\u00b7ligents. L\u2019opci\u00f3 m\u00e9s barata."},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 2 — ROUND 2: POWER SOURCE RECKONING
    # ─────────────────────────────────────────────
    {
        "id": 2,
        "title": "Ronda 2: El Rendiment de Comptes Energ\u00e8tic",
        "html": _round_html(
            round_idx=2,
            emoji="\u26a1",
            title="El Rendiment de Comptes Energ\u00e8tic",
            brief="El teu centre de dades obt\u00e9 el 100% de la xarxa regional &mdash; 65% gas natural i carb\u00f3. Cada consulta d\u2019IA funciona amb combustibles f\u00f2ssils. Els inversors pregunten pel teu pla de carboni.",
            question="Com fas verda la teva font d\u2019energia?",
            choices=[
                {"icon": "\u2600\ufe0f", "label": "Solar In Situ + Emmagatzematge amb Bateries", "desc": "Construir una granja solar amb bateries per a cobertura 24/7. Car per\u00f2 de propietat total."},
                {"icon": "\U0001f32c\ufe0f", "label": "Acord de Compra d\u2019Energia Renovable", "desc": "Signar un contracte a llarg termini d\u2019energia e\u00f2lica/solar amb un prove\u00efdor renovable."},
                {"icon": "\U0001f4dc", "label": "Comprar Compensacions de Carboni", "desc": "Adquirir cr\u00e8dits de carboni per &#39;neutralitzar&#39; les emissions sobre el paper. El m\u00e9s barat i r\u00e0pid."},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 3 — ROUND 3: MODEL EFFICIENCY OVERHAUL
    # ─────────────────────────────────────────────
    {
        "id": 3,
        "title": "Ronda 3: Revisi\u00f3 d\u2019Efici\u00e8ncia del Model",
        "html": _round_html(
            round_idx=3,
            emoji="\U0001f9e0",
            title="Revisi\u00f3 d\u2019Efici\u00e8ncia del Model",
            brief="El teu equip executa un model de 400B par\u00e0metres per a CADA consulta &mdash; fins i tot les senzilles com &#39;quin temps fa?&#39; \u00c9s com fer servir un coet per anar al supermercat. El 80% de les consultes no necessiten tanta pot\u00e8ncia.",
            question="Com optimitzes el desplegament del model?",
            choices=[
                {"icon": "\U0001fa9c", "label": "Cascada Intel\u00b7ligent de Models", "desc": "Dirigir consultes simples al model de 7B, mitjanes al de 70B, complexes al de 400B. Construir un enrutador intel\u00b7ligent."},
                {"icon": "\U0001f9ec", "label": "Destil\u00b7lar a un Model M\u00e9s Petit", "desc": "Entrenar un \u00fanic model eficient de 70B que capturi la major part de les capacitats del model de 400B."},
                {"icon": "\U0001f4be", "label": "Nom\u00e9s Afegir Cau de Respostes", "desc": "Emmagatzemar en cau respostes comunes perqu\u00e8 les consultes repetides no passin pel model. Mantenir el model gran per a la resta."},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 4 — ROUND 4: LOCATION DECISION
    # ─────────────────────────────────────────────
    {
        "id": 4,
        "title": "Ronda 4: Decisi\u00f3 d\u2019Ubicaci\u00f3",
        "html": _round_html(
            round_idx=4,
            emoji="\U0001f4cd",
            title="Ubicaci\u00f3, Ubicaci\u00f3, Ubicaci\u00f3",
            brief="El teu pr\u00f2xim centre de dades est\u00e0 planificat en una regi\u00f3 des\u00e8rtica amb terrenys barats per\u00f2 calor extrema i una xarxa el\u00e8ctrica a gas. Gaireb\u00e9 7.000 dels 8.800 centres de dades del m\u00f3n estan constru\u00efts en el clima equivocat.",
            question="On construeixes el teu pr\u00f2xim centre de dades?",
            choices=[
                {"icon": "\U0001f1f8\U0001f1ea", "label": "Regi\u00f3 N\u00f2rdica (Su\u00e8cia/Finl\u00e0ndia)", "desc": "Clima fred = refrigeraci\u00f3 gaireb\u00e9 gratu\u00efta. Xarxa el\u00e8ctrica 95%+ renovable. Major cost del terreny per\u00f2 enormes estalvis operatius."},
                {"icon": "\U0001f332", "label": "Nord-oest del Pac\u00edfic (Oregon)", "desc": "Clima moderat, forta energia hidroel\u00e8ctrica, infraestructura tecnol\u00f2gica establerta."},
                {"icon": "\U0001f3dc\ufe0f", "label": "Mantenir el Pla del Desert", "desc": "Terreny barat, avantatges fiscals, a prop de la seu central. Ja t\u2019ho apanyar\u00e0s amb la calor."},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 5 — ROUND 5: THE TRANSPARENCY REPORT
    # ─────────────────────────────────────────────
    {
        "id": 5,
        "title": "Ronda 5: L\u2019Informe de Transpar\u00e8ncia",
        "html": _round_html(
            round_idx=5,
            emoji="\U0001f4ca",
            title="L\u2019Informe de Transpar\u00e8ncia",
            brief="La UE est\u00e0 impulsant regulacions que exigeixen als centres de dades divulgar m\u00e8triques d\u2019energia i aigua. Els teus competidors guarden silenci. Un investigador acaba de publicar un estudi que diu que la majoria de les empreses tecnol\u00f2giques no comparteixen gaireb\u00e9 res sobre el cost mediambiental de la IA.",
            question="Quin nivell de transpar\u00e8ncia dones a les teves operacions?",
            choices=[
                {"icon": "\U0001f4e1", "label": "Tauler P\u00fablic en Temps Real", "desc": "Construir un tauler p\u00fablic en temps real mostrant energia, aigua, CO\u2082 per consulta. Alliberar les teves eines d\u2019efici\u00e8ncia com a codi obert."},
                {"icon": "\U0001f4c4", "label": "Informe Anual de Sostenibilitat", "desc": "Publicar un informe anual amb dades agregades. Pr\u00e0ctica est\u00e0ndard de les grans tecnol\u00f2giques."},
                {"icon": "\U0001f512", "label": "Compliment Legal M\u00ednim", "desc": "Nom\u00e9s compartir el que els reguladors t\u2019obliguin. Mantenir la resta com a &#39;secrets comercials.&#39;"},
            ],
        ),
    },
    # ─────────────────────────────────────────────
    # MODULE 6 — RESULTS
    # ─────────────────────────────────────────────
    {
        "id": 6,
        "title": "El Teu Informe de CTO",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div id="cto-results-container" style="padding:20px 0; max-width:900px; margin:0 auto;">
                    <div style="text-align:center; padding:40px;">
                        <div style="font-size:1.2rem; color:var(--cto-text-dim);">Calculant els teus resultats...</div>
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
        "q": "La refrigeraci\u00f3 per immersi\u00f3 elimina l\u2019\u00fas d\u2019aigua per\u00f2 costa m\u00e9s inicialment. Un director financer diu: *'No podem justificar el cost \u2014 l\u2019optimitzaci\u00f3 amb sensors \u00e9s suficient.'* Quin \u00e9s el contraargument m\u00e9s s\u00f2lid?",
        "o": [
            "A) L\u2019ajust de sensors redueix el malbaratament en un ~5\u201310%, per\u00f2 el sistema b\u00e0sic continua evaporant milions de litres d\u2019aigua dolça durant una sequera \u2014 una millora del 5% en un sistema fonamentalment defectu\u00f3s no \u00e9s suficient.",
            "B) La refrigeraci\u00f3 per immersi\u00f3 \u00e9s una tecnologia no provada i massa arriscada per al desplegament empresarial. Les millores incrementals s\u00f3n l\u2019opci\u00f3 responsable.",
            "C) El cost inicial no importa perqu\u00e8 les subvencions del govern cobriran la major part de la despesa d\u2019instal\u00b7laci\u00f3.",
        ],
        "a": "A) L\u2019ajust de sensors redueix el malbaratament en un ~5\u201310%, per\u00f2 el sistema b\u00e0sic continua evaporant milions de litres d\u2019aigua dolça durant una sequera \u2014 una millora del 5% en un sistema fonamentalment defectu\u00f3s no \u00e9s suficient.",
        "success": "<strong>Coneixement de Refrigeraci\u00f3 Desbloquejat!</strong> Microsoft ja est\u00e0 provant la refrigeraci\u00f3 per immersi\u00f3. Les correccions marginals en sistemes ineficients no resolen el problema subjacent.",
    },
    2: {
        "t": "t6",
        "q": "Una empresa compra compensacions de carboni en lloc d\u2019invertir en energia solar in situ. L\u2019equip de comunicaci\u00f3 diu: *'Ja som neutres en carboni.'* Quin \u00e9s el defecte cr\u00edtic d\u2019aquesta afirmaci\u00f3?",
        "o": [
            "A) Les compensacions de carboni financen la plantaci\u00f3 d\u2019arbres i projectes renovables en altres llocs, la qual cosa \u00e9s igualment efica\u00e7 que l\u2019energia solar in situ per reduir emissions.",
            "B) Les compensacions de carboni no canvien la font d\u2019energia real del centre de dades \u2014 continua funcionant amb combustibles f\u00f2ssils. Les emissions s\u00f3n reals; la \u2018neutralitat\u2019 \u00e9s comptabilitat.",
            "C) El defecte \u00e9s que les compensacions de carboni s\u00f3n massa cares \u2014 els panells solars serien m\u00e9s barats a llarg termini.",
        ],
        "a": "B) Les compensacions de carboni no canvien la font d\u2019energia real del centre de dades \u2014 continua funcionant amb combustibles f\u00f2ssils. Les emissions s\u00f3n reals; la \u2018neutralitat\u2019 \u00e9s comptabilitat.",
        "success": "<strong>Claredat sobre la Font Energ\u00e8tica!</strong> Les compensacions s\u00f3n controvertides perqu\u00e8 les emissions reals no canvien. La veritable descarbonitzaci\u00f3 significa canviar la font d\u2019energia.",
    },
    3: {
        "t": "t7",
        "q": "Executar un model de 400B per a cada consulta malbarata el 80% de la computaci\u00f3. Un cap de producte diu: *'Els usuaris esperen el millor model sempre.'* Quin \u00e9s el contraargument m\u00e9s fort?",
        "o": [
            "A) Els usuaris no noten la difer\u00e8ncia en consultes simples \u2014 un model de 7B respon \u2018Quin temps fa?\u2019 igual de b\u00e9, fent servir 50 vegades menys energia. L\u2019enrutament intel\u00b7ligent dona la millor resposta al cost adequat.",
            "B) Haur\u00edem de fer servir nom\u00e9s el model m\u00e9s petit per a tot i maximitzar l\u2019estalvi energ\u00e8tic, encara que la qualitat de les respostes baixi significativament.",
            "C) La mida del model no afecta el consum energ\u00e8tic \u2014 el maquinari GPU consumeix la mateixa energia independentment del model que s\u2019executi.",
        ],
        "a": "A) Els usuaris no noten la difer\u00e8ncia en consultes simples \u2014 un model de 7B respon \u2018Quin temps fa?\u2019 igual de b\u00e9, fent servir 50 vegades menys energia. L\u2019enrutament intel\u00b7ligent dona la millor resposta al cost adequat.",
        "success": "<strong>Arquitectura d\u2019Efici\u00e8ncia Desbloquejada!</strong> Aix\u00ed \u00e9s exactament com operen les empreses l\u00edders en IA \u2014 l\u2019enrutament en cascada ajusta la mida del model a la complexitat de la consulta.",
    },
    4: {
        "t": "t8",
        "q": "Un directiu de centres de dades defensa construir al desert: *'Els terrenys barats i els avantatges fiscals ens estalvien milions.'* Qu\u00e8 ignora aix\u00f2?",
        "o": [
            "A) Les ubicacions des\u00e8rtiques estan b\u00e9 sempre que facis servir energia renovable \u2014 la calor no impacta significativament en les operacions amb refrigeraci\u00f3 moderna.",
            "B) La calor extrema suposa 3 vegades m\u00e9s costos de refrigeraci\u00f3, la xarxa el\u00e8ctrica a gas anul\u00b7la els guanys en carboni i l\u2019escassetat d\u2019aigua crea conflictes amb la comunitat \u2014 els estalvis a curt termini causen costos operatius i reputacionals a llarg termini.",
            "C) El problema \u00e9s nom\u00e9s reputacional \u2014 els costos operatius reals en ubicacions des\u00e8rtiques s\u00f3n comparables als dels pa\u00efsos n\u00f2rdics.",
        ],
        "a": "B) La calor extrema suposa 3 vegades m\u00e9s costos de refrigeraci\u00f3, la xarxa el\u00e8ctrica a gas anul\u00b7la els guanys en carboni i l\u2019escassetat d\u2019aigua crea conflictes amb la comunitat \u2014 els estalvis a curt termini causen costos operatius i reputacionals a llarg termini.",
        "success": "<strong>Intel\u00b7lig\u00e8ncia d\u2019Ubicaci\u00f3!</strong> Meta i Google van triar ubicacions n\u00f2rdiques exactament per aquestes raons \u2014 refrigeraci\u00f3 natural + xarxes renovables = menor cost total.",
    },
    5: {
        "t": "t9",
        "q": "La majoria de les empreses d\u2019IA gaireb\u00e9 no comparteixen dades mediambientals. Un competidor diu: *'La transpar\u00e8ncia \u00e9s un desavantatge competitiu.'* Per qu\u00e8 \u00e9s una visi\u00f3 curta de mires?",
        "o": [
            "A) La transpar\u00e8ncia nom\u00e9s \u00e9s \u00fatil per al m\u00e0rqueting \u2014 no canvia l\u2019impacte mediambiental real ni impulsa una rendici\u00f3 de comptes real.",
            "B) Les regulacions de la UE arribaran de totes maneres. Les empreses que lideren en transpar\u00e8ncia estableixen l\u2019est\u00e0ndard, generen confian\u00e7a i atrauen talent \u2014 mentre que les endarrerides es comparen amb empreses de combustibles f\u00f2ssils que oculten emissions.",
            "C) La transpar\u00e8ncia total \u00e9s t\u00e8cnicament impossible perqu\u00e8 les m\u00e8triques energ\u00e8tiques varien massa entre centres de dades per informar amb precisi\u00f3.",
        ],
        "a": "B) Les regulacions de la UE arribaran de totes maneres. Les empreses que lideren en transpar\u00e8ncia estableixen l\u2019est\u00e0ndard, generen confian\u00e7a i atrauen talent \u2014 mentre que les endarrerides es comparen amb empreses de combustibles f\u00f2ssils que oculten emissions.",
        "success": "<strong>Est\u00e0ndard de Transpar\u00e8ncia Establert!</strong> Els pioners en informes de sostenibilitat defineixen les regles. El secretisme erosiona la confian\u00e7a i convida a una regulaci\u00f3 m\u00e9s estricta.",
    },
    6: {
        "t": "t10",
        "q": "Despr\u00e9s de jugar les 5 rondes, quina afirmaci\u00f3 captura millor per qu\u00e8 les decisions individuals d\u2019un CTO importen per a la sostenibilitat global de la IA?",
        "o": [
            "A) Les empreses individuals s\u00f3n massa petites per importar \u2014 nom\u00e9s la regulaci\u00f3 governamental pot arreglar l\u2019impacte mediambiental de la IA a l\u2019escala necess\u00e0ria.",
            "B) Cada decisi\u00f3 d\u2019infraestructura \u2014 refrigeraci\u00f3, energia, models, ubicaci\u00f3, transpar\u00e8ncia \u2014 s\u2019acumula a trav\u00e9s de milions d\u2019usuaris i estableix normes industrials que altres empreses segueixen o es veuen pressionades a igualar.",
            "C) La tecnologia es tornar\u00e0 naturalment m\u00e9s eficient amb el temps, de manera que les decisions d\u2019avui no tenen un impacte durador en la sostenibilitat.",
        ],
        "a": "B) Cada decisi\u00f3 d\u2019infraestructura \u2014 refrigeraci\u00f3, energia, models, ubicaci\u00f3, transpar\u00e8ncia \u2014 s\u2019acumula a trav\u00e9s de milions d\u2019usuaris i estableix normes industrials que altres empreses segueixen o es veuen pressionades a igualar.",
        "success": "<strong>Certificaci\u00f3 de CTO Completada!</strong> Ara entens que la sostenibilitat de la IA no \u00e9s una gran decisi\u00f3 \u2014 s\u00f3n cinc decisions d\u2019infraestructura que s\u2019acumulen i transformen tota una ind\u00fastria.",
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
        cta_line = "Continua prenent decisions de CTO per escalar a la classificaci\u00f3."
    elif style_key == "major":
        header_emoji = "\U0001f525"
        header_title = "Gran Impuls a la Br\u00faixola Moral!"
        summary_line = "La teva decisi\u00f3 com a CTO ha tingut un gran impacte \u2014 acabes d\u2019avançar per davant d\u2019altres l\u00edders."
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
        phase_label = "FASE 1: Decisions d\u2019Infraestructura"
        phase_color = "#6366f1"
    else:
        phase_label = "FASE 2: Estrat\u00e8gia i Avaluaci\u00f3"
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
                f"<td style='padding:8px;'>{t['team']}</td>"
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
                                <tr><th>Pos.</th><th>CTO</th><th style='text-align:right;'>Punt. \U0001f9ed</th></tr>
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
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    padding: 16px;
    border-radius: 16px;
    background: var(--cto-card-bg);
    border: 1px solid var(--cto-border-color);
    backdrop-filter: blur(16px);
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
        { id:"a", label:"Refrigeraci\\u00f3 per Immersi\\u00f3 L\\u00edquida", icon:"\\ud83e\\uddf2",
          fx:{energy:-35,water:-70,co2:-30,cost:-20,greenScore:28,reputation:22},
          fb:"Moviment incre\\u00edble. La refrigeraci\\u00f3 per immersi\\u00f3 \\u00e9s d\\u2019avantguarda \\u2014 Microsoft ja l\\u2019est\\u00e0 provant. Has eliminat la major part de l\\u2019\\u00fas d\\u2019aigua i has redu\\u00eft l\\u2019energia un 35%.", tier:"best" },
        { id:"b", label:"H\\u00edbrid: Aire + Aigua Reciclada", icon:"\\u267b\\ufe0f",
          fx:{energy:-15,water:-45,co2:-12,cost:-8,greenScore:15,reputation:14},
          fb:"Intel\\u00b7ligent i pr\\u00e0ctic. Gaireb\\u00e9 has redu\\u00eft a la meitat el consum d\\u2019aigua dolça en canviar a aigua reciclada, i la refrigeraci\\u00f3 per aire lliure estalvia energia els dies m\\u00e9s frescos.", tier:"good" },
        { id:"c", label:"Optimitzar el Sistema Actual", icon:"\\ud83d\\udd27",
          fx:{energy:-5,water:-8,co2:-4,cost:-3,greenScore:4,reputation:-5},
          fb:"Els sensors ajuden, per\\u00f2 continues fent servir el mateix sistema ineficient. Les not\\u00edcies locals publiquen un reportatge sobre el teu \\u00fas d\\u2019aigua durant la sequera.", tier:"poor" },
      ],
    },
    { id:"energy", title:"El Rendiment de Comptes Energ\\u00e8tic", emoji:"\\u26a1",
      choices:[
        { id:"a", label:"Solar In Situ + Emmagatzematge amb Bateries", icon:"\\u2600\\ufe0f",
          fx:{energy:-10,water:-5,co2:-55,cost:-15,greenScore:25,reputation:20},
          fb:"Inversi\\u00f3 audaç. La teva granja solar cobreix el 80% de la c\\u00e0rrega di\\u00fcrna, les bateries s\\u2019encarreguen de la nit. El CO\\u2082 cau dr\\u00e0sticament. Als inversors els encanten els estalvis a llarg termini.", tier:"best" },
        { id:"b", label:"Acord de Compra d\\u2019Energia Renovable", icon:"\\ud83c\\udf2c\\ufe0f",
          fx:{energy:-3,water:-3,co2:-35,cost:-5,greenScore:16,reputation:12},
          fb:"Un PPA \\u00e9s el que fan la majoria de les grans tecnol\\u00f2giques \\u2014 efica\\u00e7 i relativament f\\u00e0cil. El teu mix energ\\u00e8tic canvia significativament cap a renovables.", tier:"good" },
        { id:"c", label:"Comprar Compensacions de Carboni", icon:"\\ud83d\\udcdc",
          fx:{energy:0,water:0,co2:-10,cost:-1,greenScore:3,reputation:-8},
          fb:"Les compensacions de carboni s\\u00f3n controvertides \\u2014 moltes es consideren \\u2018greenwashing.\\u2019 Els grups ecologistes et senyalen. Les teves emissions reals no han canviat.", tier:"poor" },
      ],
    },
    { id:"models", title:"Revisi\\u00f3 d\\u2019Efici\\u00e8ncia del Model", emoji:"\\ud83e\\udde0",
      choices:[
        { id:"a", label:"Cascada Intel\\u00b7ligent de Models", icon:"\\ud83e\\udea9",
          fx:{energy:-40,water:-30,co2:-38,cost:-35,greenScore:22,reputation:15},
          fb:"Arquitectura genial. El 80% de les consultes ara van al model petit (50 vegades menys energia), i els usuaris no noten la difer\\u00e8ncia. Aix\\u00ed \\u00e9s com operen les millors empreses d\\u2019IA.", tier:"best" },
        { id:"b", label:"Destil\\u00b7lar a un Model M\\u00e9s Petit", icon:"\\ud83e\\uddec",
          fx:{energy:-25,water:-18,co2:-22,cost:-20,greenScore:14,reputation:10},
          fb:"La destil\\u00b7laci\\u00f3 de models est\\u00e0 provada. El teu nou model de 70B gestiona el 90% de les tasques b\\u00e9, redu\\u00efnt l\\u2019energia significativament.", tier:"good" },
        { id:"c", label:"Nom\\u00e9s Afegir Cau de Respostes", icon:"\\ud83d\\udcbe",
          fx:{energy:-10,water:-5,co2:-8,cost:-10,greenScore:5,reputation:3},
          fb:"El cau ajuda per a consultes repetides, per\\u00f2 la majoria dels prompts d\\u2019IA s\\u00f3n \\u00fanics \\u2014 el model enorme continua executant-se per a la gran majoria. Un pedaç, no una soluci\\u00f3.", tier:"poor" },
      ],
    },
    { id:"location", title:"Ubicaci\\u00f3, Ubicaci\\u00f3, Ubicaci\\u00f3", emoji:"\\ud83d\\udccd",
      choices:[
        { id:"a", label:"Regi\\u00f3 N\\u00f2rdica (Su\\u00e8cia/Finl\\u00e0ndia)", icon:"\\ud83c\\uddf8\\ud83c\\uddea",
          fx:{energy:-20,water:-40,co2:-30,cost:-18,greenScore:20,reputation:18},
          fb:"Aix\\u00f2 \\u00e9s exactament el que han fet Meta i Google. L\\u2019aire fred n\\u00f2rdic proporciona refrigeraci\\u00f3 natural, i la xarxa renovable significa gaireb\\u00e9 zero carboni.", tier:"best" },
        { id:"b", label:"Nord-oest del Pac\\u00edfic (Oregon)", icon:"\\ud83c\\udf32",
          fx:{energy:-10,water:-20,co2:-18,cost:-10,greenScore:12,reputation:10},
          fb:"Oregon \\u00e9s popular \\u2014 Amazon i Google hi tenen grans instal\\u00b7lacions. L\\u2019energia hidroel\\u00e8ctrica ajuda amb les xifres de carboni, el clima suau redueix la refrigeraci\\u00f3.", tier:"good" },
        { id:"c", label:"Mantenir el Pla del Desert", icon:"\\ud83c\\udfdc\\ufe0f",
          fx:{energy:5,water:10,co2:5,cost:5,greenScore:-3,reputation:-10},
          fb:"El terreny barat \\u00e9s temptador, per\\u00f2 la calor extrema suposa 3 vegades m\\u00e9s costos de refrigeraci\\u00f3. La xarxa a gas anul\\u00b7la els guanys. Els grups ecologistes t\\u2019afegeixen a una llista d\\u2019\\u2018infractors clim\\u00e0tics\\u2019.", tier:"poor" },
      ],
    },
    { id:"transparency", title:"L\\u2019Informe de Transpar\\u00e8ncia", emoji:"\\ud83d\\udcca",
      choices:[
        { id:"a", label:"Tauler P\\u00fablic en Temps Real", icon:"\\ud83d\\udce1",
          fx:{energy:-5,water:-3,co2:-5,cost:2,greenScore:18,reputation:25},
          fb:"Revolucionari. Ets la primera empresa d\\u2019IA amb un tauler de sostenibilitat en viu. Desenvolupadors, investigadors i mitjans t\\u2019elogien. Estableixes un nou est\\u00e0ndard a la ind\\u00fastria.", tier:"best" },
        { id:"b", label:"Informe Anual de Sostenibilitat", icon:"\\ud83d\\udcc4",
          fx:{energy:-2,water:-1,co2:-2,cost:0,greenScore:8,reputation:10},
          fb:"Els informes anuals s\\u00f3n el m\\u00ednim que publiquen Google i Microsoft. Compleix el tr\\u00e0mit per\\u00f2 no impulsa una rendici\\u00f3 de comptes real.", tier:"good" },
        { id:"c", label:"Compliment Legal M\\u00ednim", icon:"\\ud83d\\udd12",
          fx:{energy:0,water:0,co2:0,cost:0,greenScore:-2,reputation:-15},
          fb:"Els investigadors senyalen la teva empresa per falta de transpar\\u00e8ncia. Una publicaci\\u00f3 viral compara el teu secretisme amb el de les empreses de combustibles f\\u00f2ssils que oculten dades d\\u2019emissions. La confian\\u00e7a s\\u2019erosiona.", tier:"poor" },
      ],
    },
];

// --- INIT STATE ---
window.CTO_INIT = {energy:4200, water:18500000, co2:1680, cost:2800000, greenScore:8, reputation:12};

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
        {k:"energy", l:"Energia", u:"MWh/mes", i:"\\u26a1"},
        {k:"water", l:"Aigua", u:"L/mes", i:"\\ud83d\\udca7"},
        {k:"co2", l:"CO\\u2082", u:"t/mes", i:"\\ud83d\\udca8"},
        {k:"cost", l:"Cost", u:"$/mes", i:"\\ud83d\\udcb0"},
        {k:"greenScore", l:"Verd", u:"/100", i:"\\ud83c\\udf31"},
        {k:"reputation", l:"Rep", u:"/100", i:"\\u2b50"},
    ];
    var html = "";
    for (var idx = 0; idx < items.length; idx++) {
        var it = items[idx];
        var v = stats[it.k];
        var d = null;
        if (prev) {
            var pv = prev[it.k] || 1;
            d = Math.round((v - prev[it.k]) / pv * 100);
        }
        var valStr = it.k === "cost" ? "$" + ctoFmt(v) : (it.k === "greenScore" || it.k === "reputation") ? String(v) : ctoFmt(v);
        var deltaHtml = "";
        if (d !== null && d !== 0) {
            var dColor = d < 0 ? "var(--cto-success)" : "var(--cto-error)";
            // For greenScore and reputation, positive is good
            if (it.k === "greenScore" || it.k === "reputation") {
                dColor = d > 0 ? "var(--cto-success)" : "var(--cto-error)";
            }
            var arrow = d < 0 ? "\\u2193" : "\\u2191";
            deltaHtml = '<div style="font-size:0.75rem; margin-top:2px; color:' + dColor + ';">' + arrow + Math.abs(d) + '%</div>';
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
    var tl = {best:"\\ud83c\\udf1f Excel\\u00b7lent Elecci\\u00f3", good:"\\ud83d\\udc4d Bona Elecci\\u00f3", poor:"\\u26a0\\ufe0f Elecci\\u00f3 Arriscada"};

    var impactChips = [
        {l:"Energia",v:(choice.fx.energy>0?"+":"") + choice.fx.energy + "%", g:choice.fx.energy<0},
        {l:"Aigua",v:(choice.fx.water>0?"+":"") + choice.fx.water + "%", g:choice.fx.water<0},
        {l:"CO\\u2082",v:(choice.fx.co2>0?"+":"") + choice.fx.co2 + "%", g:choice.fx.co2<0},
        {l:"Verd +",v:"+" + choice.fx.greenScore, g:choice.fx.greenScore>0}
    ];
    var chipsHtml = '';
    for (var ci = 0; ci < impactChips.length; ci++) {
        var chip = impactChips[ci];
        var chipBg = chip.g ? "rgba(16,185,129,0.1)" : "rgba(244,63,94,0.1)";
        var chipColor = chip.g ? "var(--cto-success)" : "var(--cto-error)";
        chipsHtml += '<div style="padding:6px 12px; border-radius:8px; background:' + chipBg + '; font-size:0.85rem; color:' + chipColor + '; font-weight:600;">' + chip.l + ': ' + chip.v + '</div>';
    }

    var fbHtml = '<div class="cto-card cto-feedback-' + choice.tier + '" style="animation:ctoSlideUp 0.5s ease;">'
        + '<div style="font-size:1rem; font-weight:800; color:' + tc[choice.tier] + '; margin-bottom:8px;">' + tl[choice.tier] + '</div>'
        + '<p style="font-size:1.05rem; color:var(--cto-text-dim); line-height:1.7; margin:0;">' + choice.fb + '</p>'
        + '<div style="display:flex; gap:10px; margin-top:16px; flex-wrap:wrap;">' + chipsHtml + '</div>'
        + '<div id="cto-spinner-' + roundIdx + '" style="margin-top:20px; font-size:0.9rem; color:var(--cto-text-dim); display:flex; align-items:center; gap:8px;">'
        + '<div style="width:16px; height:16px; border:2px solid var(--cto-text-dim); border-top:2px solid var(--cto-accent); border-radius:50%; animation:ctoSpin 1s linear infinite;"></div>'
        + 'Aplicant canvis als sistemes de NovaMind...'
        + '</div>'
        + '</div>';

    var fbContainer = document.getElementById('cto-feedback-' + roundIdx);
    if (fbContainer) fbContainer.innerHTML = fbHtml;

    // After 1.2s, hide spinner (the "continue" is handled by Gradio's Next button)
    setTimeout(function() {
        var spinner = document.getElementById('cto-spinner-' + roundIdx);
        if (spinner) {
            spinner.innerHTML = '<div style="font-size:0.9rem; color:var(--cto-accent); font-weight:700;">\\u2705 Canvis aplicats. Fes clic a SEG\\u00dcENT per continuar.</div>';
        }
    }, 1200);
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
    var statusText = ok ? "\\u2705 Avaluaci\\u00f3 Completada" : "\\u26a0\\ufe0f Avaluaci\\u00f3 Completada";

    // Progress rings
    var ringItems = [
        {l:"Punt. Verda", v:stats.greenScore, m:100},
        {l:"Reputaci\\u00f3", v:stats.reputation, m:100},
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

    // Impact summary
    var impactItems = [
        {l:"Energia Redu\\u00efda", v:er+"%", f:INIT.energy.toLocaleString(), t:stats.energy.toLocaleString(), u:"MWh/mes"},
        {l:"Aigua Estalviada", v:wr+"%", f:(INIT.water/1e6).toFixed(1)+"M", t:(stats.water/1e6).toFixed(1)+"M", u:"L/mes"},
        {l:"CO\\u2082 Redu\\u00eft", v:cr+"%", f:INIT.co2.toLocaleString(), t:stats.co2.toLocaleString(), u:"t/mes"}
    ];
    var impactHtml = '';
    for (var ii = 0; ii < impactItems.length; ii++) {
        var imp = impactItems[ii];
        impactHtml += '<div style="text-align:center; padding:16px; border-radius:14px; background:var(--cto-input-bg);">'
            + '<div style="font-size:1.8rem; font-weight:800; color:var(--cto-accent);">\\u2193' + imp.v + '</div>'
            + '<div style="font-size:0.8rem; color:var(--cto-text-dim); margin-top:8px; text-transform:uppercase; letter-spacing:1px;">' + imp.l + '</div>'
            + '<div style="font-size:0.75rem; color:var(--cto-text-dim); margin-top:4px;">' + imp.f + ' \\u2192 ' + imp.t + ' ' + imp.u + '</div>'
            + '</div>';
    }

    // Audit trail
    var tc2 = {best:"var(--cto-success)", good:"var(--cto-warning)", poor:"var(--cto-error)"};
    var tl2 = {best:"Millor", good:"Bona", poor:"Pobre"};
    var roundNames = [null, "La Crisi de Refrigeraci\\u00f3", "El Rendiment de Comptes Energ\\u00e8tic", "Revisi\\u00f3 d\\u2019Efici\\u00e8ncia del Model", "Decisi\\u00f3 d\\u2019Ubicaci\\u00f3", "L\\u2019Informe de Transpar\\u00e8ncia"];
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
            + '<h2 style="font-size:1.6rem; font-weight:800; color:var(--cto-success); margin-top:12px;">IA VERDA CERTIFICADA</h2>'
            + '<p style="font-size:1.05rem; color:var(--cto-text-dim); margin-top:8px; line-height:1.7; max-width:440px; margin-left:auto; margin-right:auto;">'
            + 'NovaMind AI ha estat aprovada per al redesplegament sota el Marc d\\u2019IA Verda. La teva plataforma ara compleix els est\\u00e0ndards de sostenibilitat.</p>'
            + '<div style="margin-top:20px; display:inline-block; padding:12px 28px; border-radius:12px; background:rgba(16,185,129,0.1); border:1px solid var(--cto-success); font-size:1rem; color:var(--cto-success); font-weight:700;">'
            + '\\u2705 APROVADA PER AL REDESPLEGAMENT</div>'
            + '</div>';
    } else {
        certHtml = '<div class="cto-cert-card" style="border:2px solid var(--cto-warning);">'
            + '<div style="font-size:3rem;">\\ud83d\\udd04</div>'
            + '<h2 style="font-size:1.6rem; font-weight:800; color:var(--cto-warning); margin-top:12px;">ESTAT PROVISIONAL</h2>'
            + '<p style="font-size:1.05rem; color:var(--cto-text-dim); margin-top:8px; line-height:1.7; max-width:440px; margin-left:auto; margin-right:auto;">'
            + 'NovaMind ha millorat per\\u00f2 no ha assolit la certificaci\\u00f3 d\\u2019IA Verda (puntuaci\\u00f3 60+). La junta et dona una altra oportunitat.</p>'
            + '<div style="margin-top:20px; display:inline-block; padding:12px 28px; border-radius:12px; background:rgba(251,191,36,0.1); border:1px solid var(--cto-warning); font-size:1rem; color:var(--cto-warning); font-weight:700;">'
            + '\\u23f3 REDESPLEGAMENT PENDENT</div>'
            + '</div>';
    }

    // What you learned
    var learnHtml = '<div class="cto-card" style="margin-top:24px; text-align:center;">'
        + '<div style="font-size:1.1rem; font-weight:800; color:var(--cto-text);">\\ud83d\\udca1 El Que Acabes d\\u2019Aprendre</div>'
        + '<p style="font-size:1rem; color:var(--cto-text-dim); line-height:1.7; margin-top:8px; max-width:480px; margin-left:auto; margin-right:auto;">'
        + 'Les empreses reals d\\u2019IA s\\u2019enfronten a aquestes mateixes decisions cada dia. Refrigeraci\\u00f3, fonts d\\u2019energia, efici\\u00e8ncia del model, ubicaci\\u00f3 i transpar\\u00e8ncia s\\u00f3n les palanques que determinen si la IA ajuda o perjudica el planeta.</p>'
        + '<div style="font-size:0.8rem; color:var(--cto-text-dim); margin-top:12px;">Basat en dades reals de IEA, MIT, UC Riverside, VU Amsterdam (2024\\u20132025)</div>'
        + '</div>';

    container.innerHTML = '<div style="text-align:center; font-size:0.875rem; font-weight:800; letter-spacing:3px; color:' + statusColor + '; text-transform:uppercase;">'
        + statusText + '</div>'
        + '<h1 style="text-align:center; font-size:clamp(2rem, 7vw, 3.2rem); font-weight:800; margin-top:16px; color:var(--cto-text);">'
        + '<span style="color:' + g.c + ';">' + g.l + '</span> \\u2014 ' + g.t + '</h1>'
        + '<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:32px;">' + ringsHtml + '</div>'
        + '<div class="cto-card" style="margin-top:28px;">'
        + '<h3 style="font-size:1.2rem; font-weight:800; color:var(--cto-text); margin:0 0 16px 0;">El Teu Impacte com a CTO</h3>'
        + '<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px;">' + impactHtml + '</div></div>'
        + '<div class="cto-card" style="margin-top:20px;">'
        + '<h3 style="font-size:1.1rem; font-weight:800; color:var(--cto-text); margin:0 0 12px 0;">Les Teves Decisions</h3>'
        + auditHtml + '</div>'
        + certHtml
        + learnHtml;
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
                "<h2>Autenticant...</h2>"
                "<p>Sincronitzant dades de la Br\u00faixola Moral...</p>"
                "</div>"
            )

        # --- MAIN APP VIEW ---
        with gr.Column(visible=False) as main_app_col:
            # Top dashboard
            out_top = gr.HTML()

            gr.HTML("""
                <div style="background:var(--background-fill-secondary); padding:24px; border-radius:16px;
                            text-align:center; border:2px dashed var(--color-accent); margin:8px 0 16px 0;">
                    <div style="text-transform:uppercase; letter-spacing:2px; color:var(--body-text-color-subdued);
                                font-size:0.85rem; margin-bottom:10px; font-weight:700;">
                        La F&oacute;rmula de la Br&uacute;ixola Moral
                    </div>
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
            """)

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
                            else "\U0001f389 Simulaci\u00f3 Completada!"
                        )
                        btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

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
                            "\u274c No del tot. Torna a llegir l\u2019escenari anterior i pensa en qu\u00e8 mostren espec\u00edficament les dades.</div>",
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

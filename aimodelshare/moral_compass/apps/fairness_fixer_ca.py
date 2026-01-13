import os
import sys
import subprocess
import time
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"
TOTAL_COURSE_TASKS = 20  # Combined count across apps
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
    print("📦 Installing dependencies...")
    install_dependencies()
    import gradio as gr
    import pandas as pd
    from aimodelshare.playground import Competition
    from aimodelshare.moral_compass import MoralcompassApiClient
    from aimodelshare.aws import get_token_from_session, _get_username_from_token

# Import team name translation utilities
from .team_name_i18n import translate_team_name_for_display

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

# --- 4. MODULE DEFINITIONS (FAIRNESS FIXER) ---
MODULES = [
    # --- MODULE 0: THE PROMOTION ---
    {
        "id": 0,
        "title": "Mòdul 0: El Banc de treball de l'enginyer/a d'equitat",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="
                            display:inline-flex;
                            align-items:center;
                            gap:10px;
                            padding:10px 18px;
                            border-radius:999px;
                            background:rgba(16, 185, 129, 0.1);
                            border:1px solid #10b981;
                            font-size:0.95rem;
                            text-transform:uppercase;
                            letter-spacing:0.08em;
                            font-weight:700;
                            color:#065f46;">
                            <span style="font-size:1.1rem;">🎓</span>
                            <span>PROMOCIÓ: ENGINYER/A D'EQUITAT</span>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center;">🔧 Fase final: La reparació</h2>

                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 20px auto; text-align:center;">
                        <strong>Benvingut de nou.</strong> Has posat en evidència el biaix en el sistema d'IA de predicció de risc COMPAS i n'has impedit el desplegament. Bona feina.
                    </p>

                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 24px auto; text-align:center;">
                        Però el tribunal encara espera una eina per ajudar a gestionar l'acumulació de casos. La teva nova missió és agafar aquest model defectuós i <strong>arreglar-lo</strong> perquè sigui segur d'utilitzar.
                    </p>

                    <div class="ai-risk-container" style="border-left:4px solid var(--color-accent);">
                        <h4 style="margin-top:0; font-size:1.15rem;">El repte: "Biaix persistent"</h4>
                        <p style="font-size:1.0rem; margin-bottom:0;">
                            No pots simplement esborrar la columna "origen ètnic" i donar-ho per resolt. El biaix s'amaga en <strong>variables proxy</strong>—dades com el <em>codi postal</em> o els <em>ingressos</em>
                            que es correlacionen amb l'origen ètnic. Si esborres l'etiqueta però mantens els proxies, el model aprèn el biaix igualment.
                        </p>
                    </div>

                    <div class="ai-risk-container" style="margin-top:16px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">📋 Ordre de treball d'enginyeria</h4>
                        <p style="text-align:center; margin-bottom:12px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                            Has de completar aquests tres protocols per certificar el model abans del llançament:
                        </p>

                        <div style="display:grid; gap:10px; margin-top:12px;">

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">✂️</div>
                                <div>
                                    <div style="font-weight:700;">Protocol 1: Sanejament de les entrades</div>
                                    <div style="font-size:0.9rem;">Eliminar classes protegides i detectar les variables proxy ocultes.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Pendent</div>
                            </div>

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">🔗</div>
                                <div>
                                    <div style="font-weight:700;">Protocol 2: Causa vs. correlació</div>
                                    <div style="font-size:0.9rem;">Filtrar dades per comportament real, no només segons correlacions.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Bloquejat</div>
                            </div>

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">⚖️</div>
                                <div>
                                    <div style="font-weight:700;">Protocol 3: Representació i mostreig</div>
                                    <div style="font-size:0.9rem;">Equilibrar les dades perquè reflecteixin la població local.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Bloquejat</div>
                            </div>

                        </div>
                    </div>

                   <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 A PUNT PER COMENÇAR LA REPARACIÓ?
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Fes clic a <strong>Següent</strong> per començar a arreglar el model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 1: SANITIZE INPUTS (Protected Classes) ---
    {
        "id": 1,
        "title": "Protocol 1: Sanejar les entrades",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOL 1: SANEJAR ENTRADES</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Missió: Eliminar classes protegides i proxies ocults.</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">PAS 1 DE 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        <strong>Equitat a través de la ceguesa.</strong>
                        Legalment i èticament, no es poden utilitzar <strong>classes protegides</strong> (característiques amb què neix una persona, com l'origen ètnic o l’edat) per calcular la puntuació de risc.
                    </p>

                    <div class="ai-risk-container">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <h4 style="margin:0;">📂 Inspector de columnes del conjunt de dades</h4>
                            <div style="font-size:0.8rem; font-weight:700; color:#ef4444;">⚠ CONTÉ CARACTERÍSTIQUES NO PERMESES</div>
                        </div>

                        <p style="font-size:0.95rem; margin-bottom:12px;">
                            Revisa les capçaleres següents i identifica les columnes que vulneren les lleis d'equitat.
                        </p>

                        <div style="display:flex; gap:8px; flex-wrap:wrap; background:rgba(0,0,0,0.05); padding:12px; border-radius:8px; border:1px solid var(--border-color-primary);">

                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Origen ètnic
                            </div>
                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Gènere
                            </div>
                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Edat
                            </div>

                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Condemnes prèvies</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Situació laboral</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Codi postal</div>
                        </div>
                    </div>


            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓ NECESSÀRIA: SUPRIMIR DADES D'ENTRADA PROTEGIDES
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Utilitza el tauler de comandament de sota per executar la supressió.
                            Després fes clic a <strong>Següent</strong> per continuar arreglant el model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 2: SANITIZE INPUTS (Proxy Variables) ---
    {
        "id": 2,
        "title": "Protocol 1: Caçant Proxies",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                   <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOL 1: SANEJAMENT DE LES ENTRADES</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Missió: Eliminar classes protegides i proxies ocults.</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">PAS 2 DE 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        <strong>El problema del "biaix persistent".</strong>
                        Has eliminat origen ètnic i gènere. Perfecte. Però el biaix sovint s'amaga en <strong>variables proxy</strong>—dades aparentment neutrals que revelen indirectament informació protegida, com l’origen ètnic.
                    </p>

                    <div class="hint-box" style="border-left:4px solid #f97316;">
                        <div style="font-weight:700;">Per què el "codi postal" és un Proxy</div>

                        <p style="margin:6px 0 0 0;">
                            Històricament, moltes ciutats han estat segregades per llei o per classe social. Fins i tot avui, el <strong>codi postal</strong> sovint es correlaciona fortament amb l'origen ètnic.
                            </p>
                        <p style="margin-top:8px; font-weight:600; color:#c2410c;">
                            🚨 El risc: Si proporciones dades d'ubicació a la IA, pot "endevinar", per exemple, l'origen ètnic d'una persona molta precisió i tornar a aprendre exactament el mateix biaix que acabes d’intentar eliminar.
                        </p>
                    </div>

                    <div class="ai-risk-container" style="margin-top:16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h4 style="margin:0;">📂 Inspector de columnes del conjunt de dades</h4>
                            <div style="font-size:0.8rem; font-weight:700; color:#f97316;">⚠️ 1 VARIABLE PROXY DETECTADA</div>
                        </div>

                        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; padding:12px; background:rgba(0,0,0,0.05); border-radius:8px;">
                            <div style="padding:6px 12px; background:#e5e7eb; color:#9ca3af; text-decoration:line-through; border-radius:6px;">Origen ètnic</div>
                            <div style="padding:6px 12px; background:#e5e7eb; color:#9ca3af; text-decoration:line-through; border-radius:6px;">Gènere</div>

                            <div style="padding:6px 12px; background:#ffedd5; border:1px solid #f97316; border-radius:6px; font-weight:700; color:#9a3412;">
                                ⚠️ Codi Postal
                            </div>

                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Condemnes prèvies</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Situació laboral</div>
                        </div>
                    </div>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓ NECESSÀRIA: SUPRIMIR DADES D'ENTRADA PROXY
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Selecciona la variable proxy de sota per eliminar-la.
                            Després fes clic a <strong>Següent</strong> per continuar arreglant el model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 3: THE ACCURACY CRASH (The Pivot) ---
    {
        "id": 3,
        "title": "Alerta del Sistema: Verificació del Model",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:white; width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOL 1: SANEJAMENT DE LES ENTRADES</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Fase: Verificació i reentrenament del model</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">PAS 3 DE 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">🤖 L'execució de verificació</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        Has eliminat amb èxit <strong>origen ètnic, gènere, edat i codi postal</strong>.
                        Hem "sanejat" el conjunt de dades, eliminant les etiquetes demogràfiques. Ara executem la simulació per veure si el model continua funcionat.
                    </p>

                    <details style="border:none; margin-top:20px;">
                        <summary style="
                            background:var(--color-accent);
                            color:white;
                            padding:16px 24px;
                            border-radius:12px;
                            font-weight:800;
                            font-size:1.1rem;
                            text-align:center;
                            cursor:pointer;
                            list-style:none;
                            box-shadow:0 4px 12px rgba(59,130,246,0.3);
                            transition:transform 0.1s ease;">
                            ▶️ FES CLIC PER REENTRENAR EL MODEL AMB EL CONJUNT DE DADES REPARAT
                        </summary>

                        <div style="margin-top:24px; animation: fadeIn 0.6s ease-in-out;">

                            <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:20px; background:rgba(0,0,0,0.02);">

                                <div style="text-align:center; padding:10px; border-right:1px solid var(--border-color-primary);">
                                    <div style="font-size:2.2rem; font-weight:800; color:#ef4444;">📉 78%</div>
                                    <div style="font-weight:bold; font-size:0.9rem; text-transform:uppercase; color:var(--body-text-color-subdued); margin-bottom:6px;">Precisió (EN COL·LAPSE)</div>
                                    <div style="font-size:0.9rem; line-height:1.4;">
                                        <strong>Diagnòstic:</strong> El model ha perdut les seves "dreceres" (com el codi Postal). Està confós i té problemes per predir el risc amb precisió.
                                    </div>
                                </div>

                                <div style="text-align:center; padding:10px;">
                                    <div style="font-size:2.2rem; font-weight:800; color:#f59e0b;">🧩 FALTEN</div>
                                    <div style="font-weight:bold; font-size:0.9rem; text-transform:uppercase; color:var(--body-text-color-subdued); margin-bottom:6px;">Dades Significatives</div>
                                    <div style="font-size:0.9rem; line-height:1.4;">
                                        <strong>Diagnòstic:</strong> Hem netejat les dades problemàtiques, però no les hem substituït per <strong>dades significatives</strong>. El model necessita millors senyals per poder aprendre.
                                    </div>
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:20px; border-left:4px solid var(--color-accent);">
                                <div style="font-weight:700; font-size:1.05rem;">💡 El gir d'enginyeria</div>
                                <p style="margin:6px 0 0 0;">
                                    Un model que no sap <em>res</em> és just, però inútil.
                                    Per recuperar la precisió sense comprometre l’equitat, cal deixar d’eliminar dades i començar a <strong>trobar patrons vàlids</strong>: dades significatives que expliquin <em>per què</em> es produeix el delicte.
                                </p>
                            </div>


                    </details>

                          <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓ NECESSÀRIA: Trobar dades significatives
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Respon la pregunta de sota per rebre Punts de Brúixola Moral.
                            Després fes clic a <strong>Següent</strong> per continuar arreglant el model.
                        </p>
                    </div>
                </div>
            </div>
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                /* Hide default arrow */
                details > summary { list-style: none; }
                details > summary::-webkit-details-marker { display: none; }
            </style>
        """,
    },
    # --- MODULE 4: CAUSAL VALIDITY (Big Foot) ---
    {
        "id": 4,
        "title": "Protocol 2: Validesa Causal",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(16, 185, 129, 0.1); border:2px solid #10b981; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🔗</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#10b981; letter-spacing:0.05em;">
                                PROTOCOL 2: CAUSA VS. CORRELACIÓ
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Missió: Aprendre a distingir quan un patró <strong>causa realment</strong> un resultat — i quan és només una coincidència.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#10b981;">PAS 1 DE 2</div>
                            <div style="height:4px; width:60px; background:rgba(16, 185, 129, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:#10b981; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🧠 La trampa del "peu gran": quan la correlació t'enganya
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        Per millorar un model, sovint afegim més dades.
                        <br>
                        Però aquí hi ha el problema: el model detecta <strong>correlacions</strong> (relacions entre dues variables) i assumeix erròniament que una <strong>causa</strong> l'altra.
                        <br>
                        Considera aquest patró estadístic real:
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding:20px; border:2px solid #ef4444; background:rgba(239, 68, 68, 0.1);">
                        <div style="font-size:3rem; margin-bottom:10px;">🦶 📈 📖</div>
                        <h3 style="margin:0; color:#ef4444;">
                            La dada: "La gent amb peus més grans té millors puntuacions de lectura."
                        </h3>
                        <p style="font-size:1.0rem; margin-top:8px; color:var(--body-text-color);">
                            De mitjana, les persones amb <strong>peus grans</strong> obté puntuacions molt més altes en proves de lectura que les persones amb <strong>peus petits</strong>.
                        </p>
                    </div>

                    <details style="border:none; margin-top:16px;">
                        <summary style="
                            background:var(--color-accent);
                            color:white;
                            padding:12px 20px;
                            border-radius:8px;
                            font-weight:700;
                            text-align:center;
                            cursor:pointer;
                            list-style:none;
                            width:fit-content;
                            margin:0 auto;
                            box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                            🤔 Per què passa això? (Fes clic per revelar)
                        </summary>

                        <div style="margin-top:20px; animation: fadeIn 0.5s ease-in-out;">
                            
                            <div class="hint-box" style="border-left:4px solid #16a34a; background:rgba(22, 163, 74, 0.1);">
                                <div style="font-weight:800; font-size:1.1rem; color:#16a34a;">
                                    La tercera variable oculta: EDAT
                                </div>
                                <p style="margin-top:8px; color:var(--body-text-color);">
                                    Tenir els peus més grans <em>causa</em> que una persona llegeixi millor? <strong>No.</strong>
                                    <br>
                                    Els infants tenen peus més petits i encara estan aprenent a llegir.
                                    <br>
                                    Els adults tenen peus més grans i han tingut molts més anys de pràctica lectora.
                                </p>
                                <p style="margin-bottom:0; color:var(--body-text-color);">
                                    <strong>La idea clau:</strong> l'edat és la causa de <em>totes dues coses</em>: la mida del peu i la capacitat lectora.
                                    <br>
                                    La talla de sabates és un <em>indicador correlacionat</em>: una dada que sembla predictiva, però que no és la causa real del resultat.
                                </p>
                            </div>

                            <p style="font-size:1.05rem; text-align:center; margin-top:20px;">
                                <strong>Per què això importa:</strong>
                                <br>
                                En molts conjunts de dades reals, algunes variables semblen predictives només perquè estan relacionades amb factors de fons.
                                <br>
                                Els bons models se centren en <strong>el que realment causa els resultats</strong>, no només en allò que passa al mateix temps.
                            </p>
                        </div>
                    </details>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓ NECESSÀRIA: Pots detectar una altra "trampa del peu gran" a les dades següents?
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Respon aquesta pregunta per augmentar la teva puntuació de la Brúixola Moral.
                            Després fes clic a <strong>Següent</strong> per continuar arreglant el model.
                        </p>
                    </div>
                </div>
            </div>
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-5px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                details > summary { list-style: none; }
                details > summary::-webkit-details-marker { display: none; }
            </style>
        """,
    },
    # --- MODULE 5: APPLYING RESEARCH ---
    {
        "id": 5,
        "title": "Protocol 2: Causa vs. correlació",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(16, 185, 129, 0.1); border:2px solid #10b981; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🔗</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#10b981; letter-spacing:0.05em;">
                                PROTOCOL 2: CAUSA VS. CORRELACIÓ
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Missió: Eliminar variables que <strong>es correlacionen</strong> amb els resultats però no en són <strong>la causa</strong>.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#10b981;">PAS 2 DE 2</div>
                            <div style="height:4px; width:60px; background:rgba(16, 185, 129, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:#10b981; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🔬 Comprovació amb evidència: Triant variables justes
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        Ja ho tens tot a punt per continuar construint una versió més justa del model. Aquí tens quatre variables a tenir en compte.
                        <br>
                        Utilitza la regla següent per identificar quines variables representen <strong>causes reals</strong> de comportament — i quines són només correlacions circumstancials.
                    </p>

                    <div class="hint-box" style="border-left:4px solid var(--color-accent); background:var(--background-fill-secondary); border:1px solid var(--border-color-primary);">
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                            <div style="font-size:1.2rem;">📋</div>
                            <div style="font-weight:800; color:var(--color-accent); text-transform:uppercase; letter-spacing:0.05em;">
                                La regla d'enginyeria
                            </div>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                            
                            <div style="padding:10px; background:rgba(239, 68, 68, 0.1); border-radius:6px; border:1px solid rgba(239, 68, 68, 0.3);">
                                <div style="font-weight:700; color:#ef4444; font-size:0.9rem; margin-bottom:4px;">
                                    🚫 REBUTJAR: REREFONS
                                </div>
                                <div style="font-size:0.85rem; line-height:1.4; color:var(--body-text-color);">
                                    Variables que descriuen la situació o l'entorn d'una persona (ex: riquesa, barri).
                                    <br><strong>Es correlacionen amb el delicte però no en són la causa.</strong>
                                </div>
                            </div>
                            
                            <div style="padding:10px; background:rgba(22, 163, 74, 0.1); border-radius:6px; border:1px solid rgba(22, 163, 74, 0.3);">
                                <div style="font-weight:700; color:#16a34a; font-size:0.9rem; margin-bottom:4px;">
                                    ✅ MANTENIR: CONDUCTA
                                </div>
                                <div style="font-size:0.85rem; line-height:1.4; color:var(--body-text-color);">
                                    Variables que descriuen accions documentades fetes per la persona (ex: incompareixença judicial).
                                    <br><strong>Reflecteixen el comportament real.</strong>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="ai-risk-container" style="margin-top:20px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary);">
                        <h4 style="margin:0 0 12px 0; color:var(--body-text-color); text-align:center; font-size:1.1rem;">📂 Variables candidates d'entrada</h4>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Situació laboral</div>
                                <div style="font-size:0.85rem; background:var(--background-fill-secondary); padding:4px 8px; border-radius:4px; color:var(--body-text-color); display:inline-block;">
                                    Categoria: <strong>Condició de rerefons</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Condemnes prèvies</div>
                                <div style="font-size:0.85rem; background:rgba(22, 163, 74, 0.1); padding:4px 8px; border-radius:4px; color:#16a34a; display:inline-block;">
                                    Categoria: <strong>Historial de conducta</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Índex del barri</div>
                                <div style="font-size:0.85rem; background:var(--background-fill-secondary); padding:4px 8px; border-radius:4px; color:var(--body-text-color); display:inline-block;">
                                    Categoria: <strong>Entorn</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Incompareixença judicial</div>
                                <div style="font-size:0.85rem; background:rgba(22, 163, 74, 0.1); padding:4px 8px; border-radius:4px; color:#16a34a; display:inline-block;">
                                    Categoria: <strong>Historial de conducta</strong>
                                </div>
                            </div>

                        </div>
                    </div>

                    <div class="hint-box" style="margin-top:20px; border-left:4px solid #8b5cf6; background:linear-gradient(to right, rgba(139, 92, 246, 0.05), var(--background-fill-primary)); color:var(--body-text-color);">
                        <div style="font-weight:700; color:#8b5cf6; font-size:1.05rem;">💡 Per què això importa per a l'equitat</div>
                        <p style="margin:8px 0 0 0; font-size:0.95rem; line-height:1.5;">
                            Quan una IA jutja les persones basant-se en <strong>correlacions</strong> (com el barri o la pobresa), pot acabar penalitzant-les per les seves <strong>circumstàncies</strong> que sovint no poden controlar.
                            <br><br>
                            Quan una IA jutja basant-se en <strong>Causes</strong> (com la conducta), fa que les persones siguin responsables de les seves <strong>accions</strong>.
                            <br>
                            <strong>Equitat real = Ser jutjat per les teves eleccions, no pel teu context.</strong>
                        </p>
                    </div>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓ NECESSÀRIA: 
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Selecciona les variables que representen <strong>conducta</strong> real per construir el model just.
                            Després fes clic a <strong>Següent</strong> per continuar arreglant el model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 6,
        "title": "Protocol 3: La representació és clau",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(139, 92, 246, 0.1); border:2px solid #8b5cf6; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🌍</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#7c3aed; letter-spacing:0.05em;">
                                PROTOCOL 3: REPRESENTACIÓ
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Missió: Assegurar que les dades d'entrenament coincideixen amb el lloc on s'utilitzarà el model.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#7c3aed;">PAS 1 DE 2</div>
                            <div style="height:4px; width:60px; background:rgba(139, 92, 246, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:#8b5cf6; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🗺️ El mapa correcte
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:820px; margin:0 auto 15px auto;">
                        Hem corregit les <strong>variables</strong> (les columnes). Ara hem de comprovar l'<strong>entorn</strong> (les files).
                    </p>

                    <div style="background:var(--background-fill-secondary); border:2px dashed #94a3b8; border-radius:12px; padding:20px; text-align:center; margin-bottom:25px;">
                        <div style="font-weight:700; color:#64748b; font-size:0.9rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">L'ESCENARI</div>
                        <p style="font-size:1.15rem; font-weight:600; color:var(--body-text-color); margin:0; line-height:1.5;">
                            Aquest conjunt de dades es va construir utilitzant dades històriques del <span style="color:#ef4444;">comtat de Broward, Florida (EUA)</span>.
                            <br><br>
                            Imagina agafar aquest model de Florida i fer-lo servir en un sistema judicial completament diferent—com <span style="color:#3b82f6;">Barcelona</span> (o la teva ciutat).
                        </p>
                    </div>

                    <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">

                        <div class="hint-box" style="margin:0; border-left:4px solid #ef4444; background:rgba(239, 68, 68, 0.1);">
                            <div style="font-weight:800; color:#ef4444; margin-bottom:6px;">
                                🇺🇸 L'ORIGEN: FLORIDA
                            </div>
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color);">
                                Context d'entrenament: Sistema judicial EUA
                            </div>
                            <ul style="font-size:0.85rem; margin-top:8px; padding-left:16px; line-height:1.4; color:var(--body-text-color);">
                                <li><strong>Categories demogràfiques:</strong> definides utilitzant etiquetes i agrupacions específiques dels EUA.</li>
                                <li><strong>Crim i llei:</strong> lleis i processos judicials diferents (per exemple, normes de fiança.</li>
                                <li><strong>Geografia:</strong> ciutats pensades per moure’s en cotxe i amb expansió suburbana.</li>
                            </ul>
                        </div>

                        <div class="hint-box" style="margin:0; border-left:4px solid #3b82f6; background:rgba(59, 130, 246, 0.1);">
                            <div style="font-weight:800; color:#3b82f6; margin-bottom:6px;">
                                📍 L'OBJECTIU: BARCELONA
                            </div>
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color);">
                                Context de desplegament: Sistema judicial de la UE
                            </div>
                            <ul style="font-size:0.85rem; margin-top:8px; padding-left:16px; line-height:1.4; color:var(--body-text-color);">
                                <li><strong>Categories demogràfiques:</strong> definides diferent que als conjunts de dades dels EUA.</li>
                                <li><strong>Crim i llei:</strong> marc legal i pràctiques policials diferents, i altres tipus de delictes més habituals.</li>
                                <li><strong>Geografia:</strong> entorn urbà dens i fàcil de recórrer a peu.</li>
                            </ul>
                        </div>
                    </div>

                    <div class="hint-box" style="border-left:4px solid #8b5cf6; background:transparent;">
                        <div style="font-weight:700; color:#8b5cf6;">
                            Per què això falla
                        </div>
                        <p style="margin-top:6px;">
                            El model ha après patrons de Florida.
                            <br>
                            Quan l'entorn del món real és diferent, el model pot cometre <strong>més errors</strong> — i aquests errors poden afectar <strong>de manera desigual</strong> alguns grups.
                            <br>
                            En enginyeria d'IA, això s'anomena <strong>desplaçament del conjunt de dades</strong> (o <strong>canvi de domini</strong>).
                            <br>
                            És com intentar trobar la Sagrada Família utilitzant un mapa de Miami.
                        </p>
                    </div>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓ NECESSÀRIA:
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Respon la pregunta de sota per augmentar la teva puntuació de Brúixola Moral.
                            Després fes clic a <strong>Següent</strong> per continuar arreglant el problema de representació de dades.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 7: THE DATA SWAP ---
    {
        "id": 7,
        "title": "Protocol 3: Corregint la representació",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(139, 92, 246, 0.1); border:2px solid #8b5cf6; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🌍</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#7c3aed; letter-spacing:0.05em;">PROTOCOL 3: REPRESENTACIÓ</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Missió: Substituir les "dades drecera" amb "dades locals".</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#7c3aed;">PAS 2 DE 2</div>
                            <div style="height:4px; width:60px; background:rgba(139, 92, 246, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:#8b5cf6; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">🔄 L'intercanvi de dades</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        No podem utilitzar el conjunt de dades de Florida. Són <strong>"dades drecera"</strong>—escollides només perquè eren fàcils de trobar.
                        <br>
                        Per construir un model just per a <strong>qualsevol ubicació</strong> (sigui Barcelona, Berlín o Boston), hem de rebutjar el camí fàcil.
                        <br>
                        Hem de recollir <strong>dades locals</strong> que reflecteixin la realitat real d'aquell lloc.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; border:2px solid #ef4444; background:rgba(239, 68, 68, 0.1); padding:16px; margin-bottom:20px;">
                        <div style="font-weight:800; color:#ef4444; font-size:1.1rem; margin-bottom:8px;">⚠️ CONJUNT DE DADES ACTUAL: FLORIDA (INVÀLID)</div>

                        <p style="font-size:0.9rem; margin:0; color:var(--body-text-color);">
                            El conjunt de dades no coincideix amb el context local on s'utilitzarà el model.
                        </p>
                    </div>

                    <details style="border:none; margin-top:20px;">
                        <summary style="
                            background:#7c3aed;
                            color:white;
                            padding:16px 24px;
                            border-radius:12px;
                            font-weight:800;
                            font-size:1.1rem;
                            text-align:center;
                            cursor:pointer;
                            list-style:none;
                            box-shadow:0 4px 12px rgba(124, 58, 237, 0.3);
                            transition:transform 0.1s ease;">
                            🔄 FES CLIC PER IMPORTAR DADES LOCALS DE BARCELONA
                        </summary>

                        <div style="margin-top:24px; animation: fadeIn 0.6s ease-in-out;">

                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">
                                <div style="padding:12px; border:1px solid #22c55e; background:rgba(34, 197, 94, 0.1); border-radius:8px; text-align:center;">
                                    <div style="font-size:2rem;">📍</div>
                                    <div style="font-weight:700; color:#22c55e; font-size:0.9rem;">GEOGRAFIA COMPATIBLE</div>
                                    <div style="font-size:0.8rem; color:var(--body-text-color);">Font de dades: Dept. de Justícia de Catalunya</div>
                                </div>
                                <div style="padding:12px; border:1px solid #22c55e; background:rgba(34, 197, 94, 0.1); border-radius:8px; text-align:center;">
                                    <div style="font-size:2rem;">⚖️</div>
                                    <div style="font-weight:700; color:#22c55e; font-size:0.9rem;">LLEIS SINCRONITZADES</div>
                                    <div style="font-size:0.8rem; color:var(--body-text-color);">S'han eliminat delictes específics dels EUA</div>
                                </div>
                            </div>

                            <div class="hint-box" style="border-left:4px solid #22c55e;">
                                <div style="font-weight:700; color:#15803d;">Actualització del sistema completada</div>
                                <p style="margin-top:6px;">
                                    El model ara aprèn de les persones a qui realment afectarà. La precisió ara és útil perquè reflecteix la realitat local.
                                </p>
                            </div>

                        </div>
                    </details>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓ NECESSÀRIA:
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Respon la pregunta de sota per augmentar la teva puntuació de Brúixola Moral.
                            Després fes clic a <strong>Següent</strong> per revisar i certificar que el model està arreglat!
                        </p>
                    </div>
                </div>
            </div>
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                details > summary { list-style: none; }
                details > summary::-webkit-details-marker { display: none; }
            </style>
        """,
    },
    # --- MODULE 8: FINAL REPORT (Before & After) ---
    {
        "id": 8,
        "title": "Informe final d'equitat",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🏁</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#15803d; letter-spacing:0.05em;">AUDITORIA COMPLETADA</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Estat del sistema: A PUNT PER A LA CERTIFICACIÓ.</div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">📊 Informe final: abans i després"</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        Has sanejat les dades amb èxit, filtrat per causalitat i has adaptat el model al context local.
                        <br>Comparem el teu nou model amb el model original per revisar què ha canviat.
                    </p>

                    <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">

                        <div>
                            <div style="font-weight:800; color:#ef4444; margin-bottom:8px; text-transform:uppercase;">🚫 El model original</div>

                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">ENTRADES</div>
                                <div style="color:var(--body-text-color);">Origen ètnic, gènere, codi postal</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">LÒGICA</div>
                                <div style="color:var(--body-text-color);">Estatus i estereotips</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">CONTEXT</div>
                                <div style="color:var(--body-text-color);">Florida (Mapa equivocat)</div>
                            </div>
                            <div style="padding:10px; background:rgba(239, 68, 68, 0.2); margin-top:10px; border-radius:6px; color:#ef4444; font-weight:700; text-align:center;">
                                RISC DE BIAIX: CRÍTIC
                            </div>
                        </div>

                        <div style="transform:scale(1.02); box-shadow:0 4px 12px rgba(0,0,0,0.1); border:2px solid #22c55e; border-radius:8px; overflow:hidden;">
                            <div style="background:#22c55e; color:white; padding:6px; font-weight:800; text-align:center; text-transform:uppercase;">✅ El teu model millorat</div>

                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">ENTRADES</div>
                                <div style="color:var(--body-text-color);">Només variables de conducta</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">LÒGICA</div>
                                <div style="color:var(--body-text-color);">Conducta basada en causes</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">CONTEXT</div>
                                <div style="color:var(--body-text-color);">Barcelona (context local)</div>
                            </div>
                            <div style="padding:10px; background:rgba(34, 197, 94, 0.2); margin-top:0; color:#15803d; font-weight:700; text-align:center;">
                                RISC DE BIAIX: MINIMITZAT
                            </div>
                        </div>
                    </div>

                    <div class="hint-box" style="border-left:4px solid #f59e0b;">
                        <div style="font-weight:700; color:#b45309;">🚧 Una nota sobre la perfecció"</div>
                        <p style="margin-top:6px;">
                            És perfecte aquest model? <strong>No.</strong>
                            <br>Les dades del món real (com les detencions) encara poden arrossegar biaixos del passat.
                            Però has passat d'un sistema que <em>amplifica</em> el prejudici a un que <em>mesura l'equitat</em> utilitzant conducta i context Local.
                        </p>
                    </div>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 GAIREBÉ ACABAT!
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Respon la pregunta de sota per augmentar la teva Puntuació de Brúixola Moral.
                            <br>
                            Fes clic a <strong>Següent</strong> per completar les aprovacions finals del model i certificar-lo.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 9: CERTIFICATION ---
    {
        "id": 9,
        "title": "Protocol complet: ètica assegurada",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title" style="margin-bottom:10px; color:#15803d;">🚀 ARQUITECTURA ÈTICA VERIFICADA</h2>
                        <p style="font-size:1.1rem; max-width:700px; margin:0 auto; color:var(--body-text-color);">
                            Has refactoritzat la IA amb èxit. Ja no depèn de <strong>proxies ocults i dreceres injustes</strong>—ara és una eina transparent construïda sobre principis justos.
                        </p>
                    </div>
                    
                    <div class="ai-risk-container" style="background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; padding:25px; border-radius:12px; box-shadow:0 4px 20px rgba(34, 197, 94, 0.15);">
                        
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #bbf7d0; padding-bottom:15px; margin-bottom:20px;">
                            <div style="font-weight:900; font-size:1.3rem; color:#15803d; letter-spacing:0.05em;">DIAGNÒSTIC DEL SISTEMA</div>
                            <div style="background:#22c55e; color:white; font-weight:800; padding:6px 12px; border-radius:6px;">SEGURETAT: 100%</div>
                        </div>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">ENTRADES</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Sanejades</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">LÒGICA</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Causal</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">CONTEXT</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Localitzat</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">ESTAT</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Ètic</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top:30px; padding:20px; background:rgba(245, 158, 11, 0.1); border:2px solid #fcd34d; border-radius:12px;">
                        <div style="display:flex; gap:15px;">
                            <div style="font-size:2.5rem;">🎓</div>
                            <div>
                                <h3 style="margin:0; color:#b45309;">Següent Objectiu: certificació i rendiment</h3>
                                <p style="font-size:1.05rem; line-height:1.5; color:var(--body-text-color); margin-top:8px;">
                                    Ara que has fet el teu model <strong>ètic</strong>, pots continuar millorant la <strong>precisió</strong> del model en l'activitat final de sota.
                                    <br><br>
                                    Però abans d'optimitzar la potència, has d'assegurar les teves credencials.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:25px;">
                        <p style="font-size:1.1rem; font-weight:600; color:var(--body-text-color); margin-bottom:15px;">
                            ⬇️ <strong>Pas Següent Immediat</strong> ⬇️
                        </p>
                        
                        <div style="display:inline-block; padding:15px 30px; background:linear-gradient(to right, #f59e0b, #d97706); border-radius:50px; color:white; font-weight:800; font-size:1.1rem; box-shadow:0 4px 15px rgba(245, 158, 11, 0.4);">
                            Reclama el teu certificat oficial d'"Ètica en joc" en la següent activitat.
                        </div>
                    </div>

                </div>
            </div>
        """,
    },
]

# --- 5. INTERACTIVE CONTENT CONFIGURATION (APP 2) ---
QUIZ_CONFIG = {
    1: {
        "t": "t12",
        "q": "Acció: Selecciona les variables que s'han d'esborrar immediatament perquè són Classes Protegides.",
        "o": [
            "A) Codi postal i barri",
            "B) Origen ètnic, gènere, edat",
            "C) Condemnes prèvies",
        ],
        "a": "B) Origen ètnic, gènere, edat",
        "success": "Tasca Completada. Columnes eliminades. El model ara és cec a dades demogràfiques explícites.",
    },
    2: {
        "t": "t13",
        "q": "Per què hem d'eliminar també el 'codi postal' si ja hem eliminat l'origen ètnic?",
        "o": [
            "A) Perquè els codis postals ocupen massa memòria.",
            "B) És una Variable Proxy que reintrodueix el biaix per origen ètnic degut a la segregació històrica.",
            "C) Els codis postals no són precisos.",
        ],
        "a": "B) És una Variable Proxy que reintrodueix el biaix per origen ètnic degut a la segregació històrica.",
        "success": "Proxy identificat. Dades d'ubicació eliminades per prevenir el biaix de segregació.",
    },
    3: {
        "t": "t14",
        "q": "Després d'eliminar origen ètnic i codi postal, el model és just però la precisió ha caigut. Per què?",
        "o": [
            "A) El model està no funciona.",
            "B) Un model que no sap res és just però inútil. Necessitem millors dades, no només menys dades.",
            "C) Hauríem de tornar a posar la columna d'origen ètnic.",
        ],
        "a": "B) Un model que no sap res és just però inútil. Necessitem millors dades, no només menys dades.",
        "success": "Gir confirmat. Hem de passar d' 'eliminar' a 'seleccionar' millors característiques.",
    },
    4: {
        "t": "t15",
        "q": "Basat en l'exemple del “peu gran”, per què pot ser enganyós deixar que una IA depengui de variables com la talla de sabates?",
        "o": [
            "A) Perquè són físicament difícils de mesurar.",
            "B) Perquè sovint només es correlacionen amb resultats i són causades per un tercer factor ocult, en lloc de causar el resultat elles mateixes."
        ],
        "a": "B) Perquè sovint només es correlacionen amb resultats i són causades per un tercer factor ocult, en lloc de causar el resultat elles mateixes.",
        "success": "Filtre calibrat. Ara estàs comprovant si un patró és causat per una tercera variable oculta — no confonent correlació amb causalitat."
    },

    5: {
        "t": "t16",
        "q": "Quina d’aquestes variables ajuda a predir el delicte per un motiu real (i no per coincidència)?",
        "o": [
            "A) Ocupació (condició de context)",
            "B) Estat Civil (estil de vida)",
            "C) Incompareixença al tribunal (conducta)",
        ],
        "a": "C) Incompareixença al tribunal (conducta)",
        "success": "Característica seleccionada. 'Incompareixença' reflecteix una acció específica rellevant per al risc de fuga.",
    },
    6: {
        "t": "t17",
        "q": "Per què un model entrenat a Florida pot fer prediccions poc fiables quan s'utilitza a Barcelona?",
        "o": [
            "A) Perquè el software està en anglès i s'ha de traduir.",
            "B) Desajust de context: el model va aprendre patrons lligats a lleis, sistemes i entorns dels EUA que no coincideixen amb la realitat de Barcelona.",
            "C) Perquè el nombre de persones a Barcelona és diferent de la mida del dataset d'entrenament."
        ],
        "a": "B) Desajust de context: el model va aprendre patrons lligats a lleis, sistemes i entorns dels EUA que no coincideixen amb la realitat de Barcelona.",
        "success": "Correcte! Això és un desplaçament de conjunt de dades (o domini). Quan les dades d'entrenament no coincideixen amb on s'usa un model, les prediccions es tornen menys precises i poden fallar de manera desigual entre grups."
    },

    7: {
        "t": "t18",
        "q": "Acabes de rebutjar un dataset massiu i gratuït (Florida) per un de més petit i difícil d'aconseguir (Localment rellevant). Per què ha estat l'elecció d'enginyeria correcta?",
        "o": [
            "A) No ho era. Més dades sempre és millor, independentment d'on vinguin.",
            "B) Perquè la 'rellevància' és més important que el 'volum'. Un mapa petit i precís és millor que un mapa enorme i equivocat.",
            "C) Perquè el conjunt de dades de Florida era massa car.",
        ],
        "a": "B) Perquè la 'rellevància' és més important que el 'volum'. Un mapa petit i precís és millor que un mapa enorme i equivocat.",
        "success": "Taller completat! Has auditat, filtrat i localitzat el model d'IA amb èxit.",
    },
    8: {
        "t": "t19",
        "q": "Has arreglat les entrades, la lògica i el context. El teu nou model és ara 100% perfectament just?",
        "o": [
            "A) Sí. Les matemàtiques són objectives, així que si les dades estan netes, el model és perfecte.",
            "B) No. És més segur perquè hem prioritzat 'conducta' sobre 'estatus' i 'realitat local' sobre 'dades fàcils', però sempre hem d'estar vigilants.",
        ],
        "a": "B) No. És més segur perquè hem prioritzat 'conducta' sobre 'estatus' i 'realitat local' sobre 'dades fàcils', però sempre hem d'estar vigilants.",
        "success": "Bona feina. A continuació pots revisar oficialment aquest model per al seu ús.",
    },
    9: {
        "t": "t20",
        "q": "Has sanejat entrades, filtrat per causalitat i reponderat per representació. Estàs llest per aprovar aquest sistema d'IA reparat?",
        "o": [
            "A) Sí, el model ara és segur i autoritzo l'ús d'aquest sistema d'IA reparat.",
            "B) No, espera un model perfecte.",
        ],
        "a": "A) Sí, el model ara és segur i autoritzo l'ús d'aquest sistema d'IA reparat.",
        "success": "Missió complerta. Has dissenyat un sistema més segur i just.",
    },
}

# --- 6. CSS (Shared with App 1 for consistency) ---
css = """
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
  border-left: 6px solid #22c55e;
  background: linear-gradient(135deg, rgba(34,197,94,0.08), var(--block-background-fill));
  margin-top: 16px;
  box-shadow: 0 4px 18px rgba(0,0,0,0.08);
  font-size: 1.04rem;
  line-height: 1.55;
}
.profile-card.first-score {
  border-left-color: #facc15;
  background: linear-gradient(135deg, rgba(250,204,21,0.18), var(--block-background-fill));
}
.success-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 8px; }
.success-title { font-size: 1.26rem; font-weight: 900; color: #16a34a; }
.success-summary { font-size: 1.06rem; color: var(--body-text-color-subdued); margin-top: 4px; }
.success-delta { font-size: 1.5rem; font-weight: 800; color: #16a34a; }
.success-metrics { margin-top: 10px; padding: 10px 12px; border-radius: 10px; background: var(--background-fill-secondary); font-size: 1.06rem; }
.success-metric-line { margin-bottom: 4px; }
.success-body { margin-top: 10px; font-size: 1.06rem; }
.success-body-text { margin: 0 0 6px 0; }
.success-cta { margin: 4px 0 0 0; font-weight: 700; font-size: 1.06rem; }

/* Numbers + labels */
.score-text-primary { font-size: 2.05rem; font-weight: 900; color: var(--color-accent); }
.score-text-team { font-size: 2.05rem; font-weight: 900; color: #60a5fa; }
.score-text-global { font-size: 2.05rem; font-weight: 900; }
.label-text { font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #6b7280; }

/* Progress bar */
.progress-bar-bg { width: 100%; height: 10px; background: #e5e7eb; border-radius: 6px; overflow: hidden; margin-top: 8px; }
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
.row-highlight-me, .row-highlight-team { background: rgba(96,165,250,0.18); font-weight: 700; }

/* Containers */
.ai-risk-container { margin-top: 16px; padding: 16px; background: var(--body-background-fill); border-radius: 10px; border: 1px solid var(--border-color-primary); }

/* Interactive blocks (text size tuned for 17–20 age group) */
.interactive-block { font-size: 1.06rem; }
.interactive-block .hint-box { font-size: 1.02rem; }
.interactive-text { font-size: 1.06rem; }

/* Radio sizes */
.scenario-radio-large label { font-size: 1.06rem; }
.quiz-radio-large label { font-size: 1.06rem; }

/* Small utility */
.divider-vertical { width: 1px; height: 48px; background: var(--border-color-primary); opacity: 0.6; }

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

/* --- COMPACT CTA STYLES FOR QUIZ SLIDES --- */
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
.quiz-submit { 
  min-width: 200px; 
}
/* Hide gradient CTA banners for slides > 0, keep slide 0 Mission CTA */
.module-container[id^="module-"]:not(#module-0) div[style*="linear-gradient(to right"] {
  display: none !important;
}
"""

# --- 7. LEADERBOARD & API LOGIC (Reused) ---
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
    if not username or not token:
        return None, username
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    try:
        client.get_table(TABLE_ID)
    except Exception:
        try:
            client.create_table(
                table_id=TABLE_ID,
                display_name="LMS",
                playground_url="https://example.com",
            )
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

# --- 8. SUCCESS MESSAGE / DASHBOARD RENDERING ---
def generate_success_message(prev, curr, specific_text):
    old_score = float(prev.get("score", 0) or 0) if prev else 0.0
    new_score = float(curr.get("score", 0) or 0)
    diff_score = new_score - old_score

    old_rank = prev.get("rank", "–") if prev else "–"
    new_rank = curr.get("rank", "–")

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
        header_emoji = "🎉"
        header_title = "Estàs Oficialment a la Classificació!"
        summary_line = (
            "Acabes de guanyar la teva primera Puntuació de Brúixola Moral — ara ets part de la classificació global."
        )
        cta_line = "Desplaça't cap avall per fer el teu proper pas i començar a escalar."
    elif style_key == "major":
        header_emoji = "🔥"
        header_title = "Gran Impuls de Brúixola Moral!"
        summary_line = (
            "La teva decisió ha tingut un gran impacte — acabes d'avançar altres participants."
        )
        cta_line = "Desplaça't cap avall per enfrontar el teu proper repte i mantenir l'impuls."
    elif style_key == "climb":
        header_emoji = "🚀"
        header_title = "Estàs Escalant la Classificació"
        summary_line = "Bona feina — has superat alguns altres participants."
        cta_line = "Desplaça't cap avall per continuar la teva investigació i pujar encara més."
    elif style_key == "tight":
        header_emoji = "📊"
        header_title = "La Classificació està Canviant"
        summary_line = (
            "Altres equips també es mouen. Necessitaràs unes quantes decisions més fortes per destacar."
        )
        cta_line = "Respon la següent pregunta per enfortir la teva posició."
    else:
        header_emoji = "✅"
        header_title = "Progrés Registrat"
        summary_line = "La teva perspectiva ètica ha augmentat la teva Puntuació de Brúixola Moral."
        cta_line = "Prova el següent escenari per arribar al següent nivell."

    if style_key == "first":
        score_line = f"🧭 Puntuació: <strong>{new_score:.3f}</strong>"
        if ranks_are_int:
            rank_line = f"🏅 Rang Inicial: <strong>#{new_rank}</strong>"
        else:
            rank_line = f"🏅 Rang Inicial: <strong>#{new_rank}</strong>"
    else:
        score_line = (
            f"🧭 Puntuació: {old_score:.3f} → <strong>{new_score:.3f}</strong> "
            f"(+{diff_score:.3f})"
        )

        if ranks_are_int:
            if old_rank == new_rank:
                rank_line = f"📊 Rang: <strong>#{new_rank}</strong> (mantenen-se estable)"
            elif rank_diff > 0:
                rank_line = (
                    f"📈 Rang: #{old_rank} → <strong>#{new_rank}</strong> "
                    f"(+{rank_diff} posicions)"
                )
            else:
                rank_line = (
                    f"🔻 Rang: #{old_rank} → <strong>#{new_rank}</strong> "
                    f"({rank_diff} posicions)"
                )
        else:
            rank_line = f"📊 Rang: <strong>#{new_rank}</strong>"

    return f"""
    <div class="{card_class}">
        <div class="success-header">
            <div>
                <div class="success-title">{header_emoji} {header_title}</div>
                <div class="success-summary">{summary_line}</div>
            </div>
            <div class="success-delta">
                +{diff_score:.3f}
            </div>
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

def render_top_dashboard(data, module_id):
    display_score = 0.0
    count_completed = 0
    rank_display = "–"
    team_rank_display = "–"
    if data:
        display_score = float(data.get("score", 0.0))
        rank_display = f"#{data.get('rank', '–')}"
        team_rank_display = f"#{data.get('team_rank', '–')}"
        count_completed = len(data.get("completed_task_ids", []) or [])
    progress_pct = min(100, int((count_completed / TOTAL_COURSE_TASKS) * 100))
    return f"""
    <div class="summary-box">
        <div class="summary-box-inner">
            <div class="summary-metrics">
                <div style="text-align:center;">
                    <div class="label-text">Moral Compass Score</div>
                    <div class="score-text-primary">🧭 {display_score:.3f}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Team Rank</div>
                    <div class="score-text-team">{team_rank_display}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Global Rank</div>
                    <div class="score-text-global">{rank_display}</div>
                </div>
            </div>
            <div class="summary-progress">
                <div class="progress-label">Mission Progress: {progress_pct}%</div>
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
            # Translate team name for display
            team_label = translate_team_name_for_display(t['team'], lang='ca')
            team_rows += (
                f"<tr class='{cls}'><td style='padding:8px;text-align:center;'>{i+1}</td>"
                f"<td style='padding:8px;'>{team_label}</td>"
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
        <h3 class="slide-title" style="margin-bottom:10px;">📊 Live Standings</h3>
        <div class="lb-tabs">
            <input type="radio" id="lb-tab-team" name="lb-tabs" checked>
            <label for="lb-tab-team" class="lb-tab-label">🏆 Team</label>
            <input type="radio" id="lb-tab-user" name="lb-tabs">
            <label for="lb-tab-user" class="lb-tab-label">👤 Individual</label>
            <div class="lb-tab-panels">
                <div class="lb-panel panel-team">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Rank</th><th>Team</th><th style='text-align:right;'>Avg 🧭</th></tr>
                            </thead>
                            <tbody>{team_rows}</tbody>
                        </table>
                    </div>
                </div>
                <div class="lb-panel panel-user">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Rank</th><th>Agent</th><th style='text-align:right;'>Score 🧭</th></tr>
                            </thead>
                            <tbody>{user_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

# --- 9. APP FACTORY (FAIRNESS FIXER) ---
def create_fairness_fixer_ca_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

        # --- TOP ANCHOR & LOADING OVERLAY ---
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Carregant...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>🕵️‍♀️ Autenticant...</h2>"
                "<p>Sincronitzant Perfil d'Enginyer d'Equitat...</p>"
                "</div>"
            )

        # --- MAIN APP VIEW ---
        with gr.Column(visible=False) as main_app_col:
            # Top summary dashboard
            out_top = gr.HTML()

            # Dynamic modules container
            module_ui_elements = {}
            quiz_wiring_queue = []

            # --- DYNAMIC MODULE GENERATION ---
            for i, mod in enumerate(MODULES):
                with gr.Column(
                    elem_id=f"module-{i}",
                    elem_classes=["module-container"],
                    visible=(i == 0),
                ) as mod_col:
                    # Core slide HTML
                    gr.HTML(mod["html"])

                    # --- QUIZ CONTENT ---
                    if i in QUIZ_CONFIG:
                        q_data = QUIZ_CONFIG[i]

                        # Compact points chip and hint above the question
                        gr.HTML(
                            "<div class='quiz-cta'>"
                            "<span class='points-chip'>🧭 Punts de Brúixola Moral disponibles</span>"
                            "<span>Respon per millorar la teva puntuació</span>"
                            "</div>"
                        )

                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Selecciona una Acció:",
                            elem_classes=["quiz-radio-large"],
                        )
                        feedback = gr.HTML("")
                        quiz_wiring_queue.append((i, radio, feedback))

                    # --- NAVIGATION BUTTONS ---
                    with gr.Row():
                        btn_prev = gr.Button("⬅️ Anterior", visible=(i > 0))
                        next_label = (
                            "Següent ▶️"
                            if i < len(MODULES) - 1
                            else "🎉 Model Autoritzat! Desplaça't cap avall per rebre el teu Certificat oficial d'Ètica en Joc!"
                        )
                        btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            # Leaderboard card
            leaderboard_html = gr.HTML()

            # --- WIRING: QUIZ LOGIC ---
            for mod_id, radio_comp, feedback_comp in quiz_wiring_queue:
                def quiz_logic_wrapper(user, tok, team, acc_val, task_list, ans, mid=mod_id):
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
                            "<div class='hint-box' style='border-color:red;'>❌ Incorrecte. Torna-ho a intentar.</div>",
                            task_list,
                        )

                radio_comp.change(
                    fn=quiz_logic_wrapper,
                    inputs=[username_state, token_state, team_state, accuracy_state, task_list_state, radio_comp],
                    outputs=[out_top, leaderboard_html, feedback_comp, task_list_state],
                )

        # --- GLOBAL LOAD HANDLER ---
        def handle_load(req: gr.Request):
            success, user, token = _try_session_based_auth(req)
            team = "Team-Unassigned"
            acc = 0.0
            fetched_tasks: List[str] = []

            if success and user and token:
                acc, fetched_team = fetch_user_history(user, token)
                os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
                client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

                def get_or_assign_team(client_obj, username_val):
                    try:
                        user_data = client_obj.get_user(table_id=TABLE_ID, username=username_val)
                    except Exception:
                        user_data = None
                    if user_data and isinstance(user_data, dict):
                        if user_data.get("teamName"):
                            return user_data["teamName"]
                    return "team-a"

                exist_team = get_or_assign_team(client, user)
                if fetched_team != "Team-Unassigned":
                    team = fetched_team
                elif exist_team != "team-a":
                    team = exist_team
                else:
                    team = "team-a"

                try:
                    user_stats = client.get_user(table_id=TABLE_ID, username=user)
                except Exception:
                    user_stats = None

                if user_stats:
                    if isinstance(user_stats, dict):
                        fetched_tasks = user_stats.get("completedTaskIds") or []
                    else:
                        fetched_tasks = getattr(user_stats, "completed_task_ids", []) or []

                try:
                    client.update_moral_compass(
                        table_id=TABLE_ID,
                        username=user,
                        team_name=team,
                        metrics={"accuracy": acc},
                        tasks_completed=len(fetched_tasks),
                        total_tasks=TOTAL_COURSE_TASKS,
                        primary_metric="accuracy",
                        completed_task_ids=fetched_tasks,
                    )
                    time.sleep(1.0)
                except Exception:
                    pass

                data, _ = ensure_table_and_get_data(user, token, team, fetched_tasks)
                return (
                    user, token, team, False,
                    render_top_dashboard(data, 0),
                    render_leaderboard_card(data, user, team),
                    acc, fetched_tasks,
                    gr.update(visible=False), gr.update(visible=True),
                )

            return (
                None, None, None, False,
                "<div class='hint-box'>⚠️ Auth Failed. Please launch from the course link.</div>",
                "", 0.0, [],
                gr.update(visible=False), gr.update(visible=True),
            )

        demo.load(
            handle_load, None,
            [username_state, token_state, team_state, gr.State(False), out_top, leaderboard_html, accuracy_state, task_list_state, loader_col, main_app_col],
        )

        # --- JAVASCRIPT NAVIGATION ---
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
                  }}
                }}, 90);
              }} catch(e) {{ console.warn('nav-js error', e); }}
            }}
            """

        # --- NAV BUTTON WIRING ---
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]
            if i > 0:
                prev_col = module_ui_elements[i - 1][0]
                prev_target_id = f"module-{i-1}"
                def make_prev_handler(p_col, c_col):
                    def navigate_prev():
                        yield gr.update(visible=False), gr.update(visible=False)
                        yield gr.update(visible=True), gr.update(visible=False)
                    return navigate_prev
                prev_btn.click(
                    fn=make_prev_handler(prev_col, curr_col),
                    outputs=[prev_col, curr_col],
                    js=nav_js(prev_target_id, "Carregant..."),
                )

            if i < len(MODULES) - 1:
                next_col = module_ui_elements[i + 1][0]
                next_target_id = f"module-{i+1}"
                def make_next_handler(c_col, n_col, next_idx):
                    def wrapper_next(user, tok, team, tasks):
                        data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                        return render_top_dashboard(data, next_idx)
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

# --- 10. LAUNCHER ---
def launch_fairness_fixer_ca_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    app = create_fairness_fixer_ca_app(theme_primary_hue=theme_primary_hue)
    app.launch(share=share, server_name=server_name,
               server_port=server_port,
               **kwargs)

if __name__ == "__main__":
    launch_fairness_fixer_ca_app(share=False, debug=True, height=1000)

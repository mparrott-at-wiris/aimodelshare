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
TOTAL_COURSE_TASKS = 20 # Score calculated against full course
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

# --- 4. MODULE DEFINITIONS (APP 1: 0-10) ---
MODULES = [
    # --- MODULE 0: THE HOOK (Mission Dossier) ---
  {
        "id": 0,
        "title": "Expedient de la Missió",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">
                    <h2 class="slide-title" style="margin-bottom:25px; text-align:center; font-size: 2.2rem;">🕵️ EXPEDIENT DE LA MISSIÓ</h2>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:25px; margin-bottom:30px; align-items:stretch;">
                        <div style="background:var(--background-fill-secondary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary);">
                            <div style="margin-bottom:15px;">
                                <div style="font-size:0.9rem; font-weight:800; color:var(--body-text-color-subdued); letter-spacing:1px;">EL TEU ROL</div>
                                <div style="font-size:1.3rem; font-weight:700; color:var(--color-accent);">Detectiu Principal de Biaixos</div>
                            </div>
                            <div>
                                <div style="font-size:0.9rem; font-weight:800; color:var(--body-text-color-subdued); letter-spacing:1px;">EL TEU OBJECTIU</div>
                                <div style="font-size:1.3rem; font-weight:700;">Algoritme d'IA "Compas"</div>
                                <div style="font-size:1.0rem; margin-top:5px; opacity:0.8;">Utilitzat pels jutges per decidir la llibertat sota fiança.</div>
                            </div>
                        </div>
                        <div style="background:rgba(239,68,68,0.1); padding:20px; border-radius:12px; border:2px solid #fca5a5; display:flex; flex-direction:column; justify-content:center;">
                            <div style="font-size:0.9rem; font-weight:800; color:#ef4444; letter-spacing:1px;">🚨 L'AMENAÇA</div>
                            <div style="font-size:1.15rem; font-weight:600; line-height:1.4; color:var(--body-text-color);">
                                El model té un 92% d'exactitud, però sospitem que hi ha un <strong style="color:#ef4444;">biaix sistemàtic ocult</strong>.
                                <br><br>
                                El teu objectiu: Exposar els defectes abans que aquest model es desplegui a tot el país.
                            </div>
                        </div>
                    </div>

                    <hr style="opacity:0.2; margin:25px 0; border-color:var(--body-text-color);">

                    <p style="text-align:center; font-weight:800; color:var(--body-text-color-subdued); margin-bottom:20px; font-size:1.0rem; letter-spacing:1px;">
                        👇 FES CLIC A LES TARGETES PER DESBLOQUEJAR INFORMACIÓ
                    </p>

                    <div style="display:grid; gap:20px;">
                        <details class="evidence-card" style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-left: 6px solid #ef4444; padding:0; border-radius:8px; overflow:hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <summary style="padding:20px; font-weight:800; font-size:1.2rem; color:var(--body-text-color); cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; background:rgba(239,68,68,0.1);">
                                <div style="display:flex; align-items:center; gap:15px;">
                                    <span style="font-size:1.8rem;">⚠️</span>
                                    <span>RISC: L'"efecte ona"</span>
                                </div>
                                <span style="font-size:0.9rem; color:#ef4444; text-transform:uppercase;">Fes clic per simular</span>
                            </summary>
                            <div style="padding:25px; border-top:1px solid var(--border-color-primary);">
                                <div style="display:flex; gap:30px; align-items:center;">
                                    <div style="font-size:3.5rem; line-height:1;">🌊</div>
                                    <div>
                                        <div style="font-weight:900; font-size:2.0rem; color:#ef4444; line-height:1;">15.000+</div>
                                        <div style="font-weight:700; font-size:1.1rem; color:var(--body-text-color); margin-bottom:5px;">Casos processats per any</div>
                                        <div style="font-size:1.1rem; color:var(--body-text-color-subdued); line-height:1.5;">
                                            Un humà comet un error una vegada. Un sistema d'IA repetirà el mateix biaix <strong style="color:var(--body-text-color);">15.000+ vegades a l'any</strong>.
                                            <br>Si no ho arreglem, automatitzarem la injustícia a gran escala.
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </details>

                        <details class="evidence-card" style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-left: 6px solid #22c55e; padding:0; border-radius:8px; overflow:hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <summary style="padding:20px; font-weight:800; font-size:1.2rem; color:var(--body-text-color); cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; background:rgba(34,197,94,0.1);">
                                <div style="display:flex; align-items:center; gap:15px;">
                                    <span style="font-size:1.8rem;">🧭</span>
                                    <span>OBJECTIU: Com guanyar</span>
                                </div>
                                <span style="font-size:0.9rem; color:#22c55e; text-transform:uppercase;">Fes clic per calcular</span>
                            </summary>
                            <div style="padding:25px; border-top:1px solid var(--border-color-primary);">
                                <div style="text-align:center; margin-bottom:20px;">
                                    <div style="font-size:1.4rem; font-weight:800; background:var(--background-fill-primary); border:1px solid var(--border-color-primary); padding:15px; border-radius:10px; display:inline-block; color:var(--body-text-color);">
                                        <span style="color:#6366f1;">[ Precisió ]</span>
                                        <span style="color:var(--body-text-color-subdued); margin:0 10px;">×</span>
                                        <span style="color:#22c55e;">[ % Progrés ètic ]</span>
                                        <span style="color:var(--body-text-color-subdued); margin:0 10px;">=</span>
                                        PUNTUACIÓ
                                    </div>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                                    <div style="padding:15px; background:rgba(254,226,226,0.1); border:2px solid #fecaca; border-radius:10px; text-align:center;">
                                        <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">Escenari A: Ètica ignorada</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">Alta precisió (92%)</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">0% Ètica</div>
                                        <div style="margin-top:10px; border-top:1px solid #fecaca; padding-top:5px;">
                                            <div style="font-size:0.8rem; text-transform:uppercase; color:#ef4444;">Puntuació final</div>
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444;">0</div>
                                        </div>
                                    </div>
                                    <div style="padding:15px; background:rgba(220,252,231,0.1); border:2px solid #bbf7d0; border-radius:10px; text-align:center;">
                                        <div style="font-weight:700; color:#22c55e; margin-bottom:5px;">Escenari B: Detectiu rigorós</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">Alta precisió (92%)</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">100% Ètica</div>
                                        <div style="margin-top:10px; border-top:1px solid #bbf7d0; padding-top:5px;">
                                            <div style="font-size:0.8rem; text-transform:uppercase; color:#15803d;">Puntuació final</div>
                                            <div style="font-size:2.5rem; font-weight:900; color:#22c55e;">92</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </details>
                    </div>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 INICI DE LA MISSIÓ
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Respon a la pregunta següent per rebre el teu primer <strong>augment de la Puntuació de Brúixola Moral</strong>.
                            <br>Després fes clic a <strong>Següent</strong> per començar la investigació.
                        </p>
                    </div> 
                </div>
            </div>
        """,
    },

    # --- MODULE 1: THE MAP (Mission Roadmap) ---
    {
        "id": 1,
        "title": "Full de ruta de la missió",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <h2 class="slide-title" style="text-align:center; margin-bottom:15px;">🗺️ FULL DE RUTA DE LA MISSIÓ</h2>

                    <p style="font-size:1.1rem; max-width:800px; margin:0 auto 25px auto; text-align:center; color:var(--body-text-color);">
                        <strong>La teva missió és clara:</strong> Descobrir el biaix amagat dins del 
                        sistema d'IA abans que faci mal a persones reals. Si no pots trobar el biaix, no el podem corregir.
                    </p>

                    <div class="ai-risk-container" style="background:transparent; border:none; padding:0;">

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">

                            <div style="border: 3px solid #3b82f6; background: rgba(59, 130, 246, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#3b82f6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PAS 1: REGLES</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">📜</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#3b82f6; margin-bottom:5px;">Establir les regles</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Defineix l'estàndard ètic: <strong>Justícia i Equitat</strong>. Què es considera exactament biaix en aquesta investigació?
                                </div>
                            </div>

                            <div style="border: 3px solid #14b8a6; background: rgba(20, 184, 166, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#14b8a6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PAS 2: EVIDÈNCIES EN LES DADES</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">🔍</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#14b8a6; margin-bottom:5px;">Anàlisi forense de les dades d'entrada</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Escaneja les <strong>dades d'entrada</strong> per trobar injustícies històriques, buits de representació i biaixos d'exclusió.
                                </div>
                            </div>

                            <div style="border: 3px solid #8b5cf6; background: rgba(139, 92, 246, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#8b5cf6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PAS 3: PROVES D'ERROR</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">🎯</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#8b5cf6; margin-bottom:5px;">Proves dels errors de sortida</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Posa a prova les prediccions del model. Demostra que els errors (com les falses alarmes) són <strong>desiguals</strong> entre grups.
                                </div>
                            </div>

                            <div style="border: 3px solid #f97316; background: rgba(249, 115, 22, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#f97316; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PAS 4: INFORME D'IMPACTE</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">⚖️</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#f97316; margin-bottom:5px;">Informe final</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Diagnostica el dany sistemàtic i emet la teva recomanació final al tribunal: <strong>desplegar el sistema d'IA o aturar-lo per reparar-lo.</strong>
                                </div>
                            </div>

                        </div>
                    </div>


                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 CONTINUAR LA MISSIÓ
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Respon a la pregunta següent per rebre el teu proper <strong>augment de la Puntuació de Brúixola Moral</strong>.
                            <br>Després fes clic a <strong>Següent</strong> per continuar la investigació.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },

    # --- MODULE 2: RULES (Interactive) ---
    {
        "id": 2,
        "title": "Pas 1: Aprèn les Regles",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step active">1. REGLES</div>
                    <div class="tracker-step">2. EVIDÈNCIES</div>
                    <div class="tracker-step">3. ERRORS</div>
                    <div class="tracker-step">4. VEREDICTE</div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h2 class="slide-title" style="margin:0;">PAS 1: APRÈN LES REGLES</h2>
                    <div style="font-size:2rem;">⚖️</div>
                </div>

                <div class="slide-body">

                    <div style="background:rgba(59, 130, 246, 0.1); border-left:4px solid #3b82f6; padding:15px; margin-bottom:20px; border-radius:4px; color: var(--body-text-color);">
                        <p style="margin:0; font-size:1.05rem; line-height:1.5;">
                            <strong style="color:var(--color-accent);">Justícia i Equitat: La teva regla principal.</strong><br>
                            L’ètica guia les nostres accions. Seguim l’assessorament expert de l'Observatori d'Ètica en Intel·ligència Artificial de Catalunya <strong>OEIAC (UdG)</strong> per garantir que els sistemes d’IA siguin justos.
                            Dels seus set principis clau per a una IA segura, aquest cas se centra en una possible vulneració de la <strong>Justícia i Equitat</strong>.
                        </p>
                    </div>

                    <div style="text-align:center; margin-bottom:20px;">
                        <p style="font-size:1rem; font-weight:700; color:var(--color-accent); background:rgba(59, 130, 246, 0.1); display:inline-block; padding:6px 16px; border-radius:20px; border:1px solid var(--border-color-primary);">
                            👇 Fes clic a cada targeta per revelar què es considera biaix
                        </p>
                    </div>

                    <p style="text-align:center; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:10px; font-size:0.9rem; letter-spacing:1px;">
                        🧩 JUSTÍCIA I EQUITAT: QUÈ ES CONSIDERA BIAIX?
                    </p>

                    <div class="ai-risk-container" style="background:transparent; border:none; padding:0;">
                        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:15px;">

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #3b82f6; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#3b82f6; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">📊</div>
                                    Biaix de representació
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Què comprova:</strong> Si el conjunt de dades reflecteix la població real.
                                    <br><br>
                                    Si un grup apareix molt més o molt menys (p. ex., només el 10% dels casos són del Grup A, però són el 71% de la població) que la realitat, la IA probablement aprendrà patrons esbiaixats.
                                </div>
                            </details>

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #ef4444; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#ef4444; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">🎯</div>
                                    Diferències d'error
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Què comprova:</strong> Si la IA comet més errors amb un grup que amb un altre.
                                    <br><br>
                                    Taxes d’error més altes per a un grup (com ara falsos positius) indiquen que el model pot ser menys just o fiable per a aquest grup.
                                </div>
                            </details>

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #22c55e; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#22c55e; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">⛓️</div>
                                    Desigualtats en els resultats
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Què comprova:</strong> Si les decisions de la IA provoquen pitjors resultats reals per a determinats grups (per exemple, sentències més severes).
                                    <br><br>
                                    El biaix no és només una qüestió de dades: afecta la vida de les persones.
                                </div>
                            </details>
                        </div>
                    </div>

                    <hr style="opacity:0.2; margin:25px 0; border-color:var(--body-text-color);">

                    <details class="hint-box" style="margin-top:0; cursor:pointer;">
                        <summary style="font-weight:700; color:var(--body-text-color-subdued);">🧭 Referència: Altres principis d'ètica en IA (OEIAC)</summary>
                        <div style="margin-top:15px; font-size:0.9rem; display:grid; grid-template-columns: 1fr 1fr; gap:15px; color:var(--body-text-color);">
                            <div>
                                <strong>Transparència i explicabilitat</strong><br>Assegurar que el raonament de la IA i el judici final siguin clars perquè les decisions es puguin inspeccionar i la gent pugui apel·lar.<br>
                                <strong>Seguretat i no-maleficència</strong><br>Minimitzar els errors nocius i tenir sempre un pla sòlid per a fallades del sistema.<br>
                                <strong>Responsabilitat i rendició de comptes</strong><br>Assignar propietaris clars per a la IA i mantenir un registre detallat de les decisions (rastre d'auditoria).
                            </div>
                            <div>
                                <strong>Autonomia</strong><br>Proporcionar als individus processos clars d'apel·lació i alternatives a la decisió de la IA.<br>
                                <strong>Privacitat</strong><br>Utilitzar només les dades necessàries i justificar sempre qualsevol necessitat d'utilitzar atributs sensibles.<br>
                                <strong>Sostenibilitat</strong><br>Evitar danys a llarg termini a la societat o al medi ambient (p. ex., ús massiu d'energia o desestabilització del mercat).
                            </div>
                        </div>
                    </details>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 SESSIÓ INFORMATIVA DE REGLES COMPLETADA: CONTINUAR MISSIÓ
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Respon a la pregunta següent per rebre el teu proper <strong>augment de la Puntuació de Brúixola Moral</strong>.
                            <br>Després fes clic a <strong>Següent</strong> per continuar la teva missió.
                        </p>
                    </div>
                </div>
            </div>
        """
    },

    {
        "id": 3,
        "title": "Pas 2: Reconeixement de Patrons",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step active">2. EVIDÈNCIES</div>
                    <div class="tracker-step">3. ERRORS</div>
                    <div class="tracker-step">4. VEREDICTE</div>
                </div>

        <div class="slide-body">
            <h2 class="slide-title" style="margin:0;">PAS 2: BUSCA EVIDÈNCIES</h2>

            <div style="text-align:center; margin-bottom:20px;">

                <h2 class="slide-title header-accent" style="margin-top:10px;">A la recerca de patrons demogràfics esbiaixats</h2>
                <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                    Els sistemes d’IA aprenen a partir de les dades. Si les dades estan esbiaixades, el sistema també ho estarà.
                    <br>La primera tasca és identificar el <strong>biaix de representació,</strong> comprovant quins <strong>grups demogràfics</strong> apareixen més o menys sovint en les dades.
                </p>
            </div>

            <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:16px; padding:25px; margin-bottom:20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px;">
                    <div style="font-size:1.5rem;">🚩</div>
                    <div>
                        <strong style="color:#0ea5e9; font-size:1.1rem; text-transform:uppercase; letter-spacing:1px;">PATRÓ: "EL MIRALL DISTORSIONAT"</strong>
                        <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">(Biaix de representació en grups protegits)</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
                    
                    <div style="color: var(--body-text-color);">
                        <p style="font-size:1rem; line-height:1.6;">
                            <strong>El concepte del mirall:</strong> Idealment, un conjunt de dades hauria de ser com un "mirall" de la població real. 
                            Si un grup constitueix el 50% de la població, hauria d’aparèixer en una proporció similar en les dades.
                        </p>
                        <p style="font-size:1rem; line-height:1.6;">
                            <strong>Senyal d'alerta:</strong> Busca <strong>grans desequilibris</strong> en característiques protegides com l'origen ètnic, el gènere o l'edat.
                        </p>
                        <ul style="font-size:0.95rem; color:var(--body-text-color-subdued); margin-top:10px; padding-left:20px; line-height:1.5;">
                            <li><strong>Sobrerrepresentació:</strong> Un grup domina les dades (p. ex., el 80% dels registres d'arrest són Homes). El sistema pot acabar tractant aquest grup de manera injusta.</li>
                            <li><strong>Infrarrepresentació:</strong> Un grup és molt petit o no apareix. El sistema no pot aprendre patrons fiables per a aquest grup.</li>
                        </ul>
                    </div>

                    <div style="background:var(--background-fill-primary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary); display:flex; flex-direction:column; justify-content:center;">
                        
                        <div style="margin-bottom:20px;">
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:5px;">REALITAT (La població)</div>
                            <div style="display:flex; width:100%; height:24px; border-radius:4px; overflow:hidden;">
                                <div style="width:33%; background:#94a3b8; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grup A</div>
                                <div style="width:34%; background:#64748b; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grup B</div>
                                <div style="width:33%; background:#475569; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grup C</div>
                            </div>
                        </div>

                        <div>
                            <div style="font-size:0.85rem; font-weight:700; color:#0ea5e9; margin-bottom:5px;">LES DADES D'ENTRENAMENT (El mirall distorsionat)</div>
                            <div style="display:flex; width:100%; height:24px; border-radius:4px; overflow:hidden;">
                                <div style="width:80%; background:linear-gradient(90deg, #f43f5e, #be123c); display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem; font-weight:700;">GRUP A (80%)</div>
                                <div style="width:10%; background:#cbd5e1;"></div>
                                <div style="width:10%; background:#94a3b8;"></div>
                            </div>
                            <div style="font-size:0.8rem; color:#ef4444; margin-top:5px; font-weight:600;">
                                ⚠️ Alerta: El Grup A està massivament sobrerrepresentat.
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <div style="margin-bottom: 25px; padding: 0 10px;">
                <p style="font-size:1.1rem; line-height:1.5; color:var(--body-text-color);">
                    <strong>🕵️ El següent pas:</strong> Revisa les dades demogràfiques al laboratori d’anàlisi forense de dades. Si veus un "mirall distorsionat", les dades probablement estan esbiaixades.
                </p>
            </div>

            <details style="margin-bottom:30px; cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; padding:12px;">
                <summary style="font-weight:700; color:var(--body-text-color-subdued); font-size:0.95rem;">🧭 Referència: Com esdevenen esbiaixats els conjunts de dades d'IA?</summary>
                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color-subdued); line-height:1.5; padding:0 5px;">
                    <p style="margin-bottom:10px;"><strong>Exemple:</strong> Quan un conjunt de dades es construeix a partir de <strong>registres històrics d'arrests</strong>.</p>
                    <p>L'excés de vigilància policial sistèmic en barris específics podria distorsionar els recomptes en el conjunt de dades per atributs com <strong>Origen ètnic o ingressos</strong>.
                     La IA llavors aprèn aquesta distorsió com a "veritat".</p>
                </div>
            </details>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 PATRONS D'EVIDÈNCIA ESTABLERTS: CONTINUAR MISSIÓ
                </p>
                <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                    Respon a la pregunta següent per rebre el teu proper <strong>augment de la Puntuació de Brúixola Moral</strong>.
                    <br>Després fes clic a <strong>Següent</strong> per començar a <strong>analitzar l'evidència al Laboratori Forense de Dades.</strong>
                </p>
            </div>
        </div>
    </div>
    """
    },

    # --- MODULE 4: DATA FORENSICS LAB (The Action) ---
    {
        "id": 4, 
        "title": "Pas 2: Laboratori forense de dades",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step active">2. EVIDÈNCIES</div>
                    <div class="tracker-step">3. ERRORS</div>
                    <div class="tracker-step">4. VEREDICTE</div>
                </div>

           <h2 class="slide-title" style="margin:0;">PAS 2: BUSCA EVIDÈNCIES</h2>

            <div style="text-align:center; margin-bottom:20px;">

                <h2 class="slide-title header-accent" style="margin-top:10px;">El laboratori forense de dades</h2>                
                <div class="slide-body">

                    <p style="text-align:center; max-width:700px; margin:0 auto 15px auto; font-size:1.1rem; color:var(--body-text-color);">
                        Busca evidències de biaix de representació.
                        Compara la població del <strong>món real</strong> amb les dades d’<strong>entrada</strong> del sistema d’IA.
                        <br>El sistema "veu" el món tal com és realment o veus evidències de representació distorsionada?
                    </p>

                <div style="text-align:center; margin-bottom:20px;">
                    <p style="font-size:1rem; font-weight:700; color:var(--color-accent); background:rgba(59, 130, 246, 0.1); display:inline-block; padding:6px 16px; border-radius:20px; border:1px solid var(--border-color-primary);">
                        👇 Fes clic per escanejar cada categoria demogràfica i revelar evidències
                    </p>
               </div>

                    <div style="margin-top:20px;">
                        <input type="radio" id="scan-race" name="scan-tabs" class="scan-radio" checked>
                        <input type="radio" id="scan-gender" name="scan-tabs" class="scan-radio">
                        <input type="radio" id="scan-age" name="scan-tabs" class="scan-radio">

                        <div class="forensic-tabs" style="display:flex; justify-content:center; gap:10px; margin-bottom:0;">
                            <label for="scan-race" class="tab-label-styled" style="flex:1; text-align:center;">ESCANEIG: ÈTNIA</label>
                            <label for="scan-gender" class="tab-label-styled" style="flex:1; text-align:center;">ESCANEIG: GÈNERE</label>
                            <label for="scan-age" class="tab-label-styled" style="flex:1; text-align:center;">ESCANEIG: EDAT</label>
                        </div>

                        <div class="scan-content" style="border-top: 3px solid var(--color-accent);">

                            <div class="scan-pane pane-race">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">ESCANEJANT: DISTRIBUCIÓ ÈTNICA</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ ANOMALIA DETECTADA</span>
                                </div>

                                <div style="display:grid; grid-template-columns: 1fr 0.2fr 1fr; align-items:center; gap:10px;">

                                    <div style="text-align:center; background:var(--background-fill-secondary); padding:15px; border-radius:8px; border:1px solid var(--border-color-primary);">
                                        <div style="font-size:0.9rem; font-weight:700; color:var(--body-text-color-subdued); letter-spacing:1px;">MÓN REAL</div>
                                        <div style="font-size:2rem; font-weight:900; color:#3b82f6; margin:5px 0;">28%</div>
                                        <div style="font-size:0.9rem; margin-bottom:10px; color: var(--body-text-color);">Població afroamericana</div>
                                        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; max-width:80px; margin:0 auto;">
                                            <span style="color:#3b82f6;">●</span><span style="color:#3b82f6;">●</span><span style="color:#3b82f6;">●</span><span style="color:var(--border-color-primary);">●</span>
                                            <span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span>
                                            <span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span>
                                        </div>
                                    </div>

                                    <div style="text-align:center; font-size:1.5rem; color:var(--body-text-color-subdued);">👉</div>

                                    <div style="text-align:center; background:rgba(239, 68, 68, 0.1); padding:15px; border-radius:8px; border:2px solid #ef4444;">
                                        <div style="font-size:0.9rem; font-weight:700; color:#ef4444; letter-spacing:1px;">DADES D'ENTRADA</div>
                                        <div style="font-size:2rem; font-weight:900; color:#ef4444; margin:5px 0;">51%</div>
                                        <div style="font-size:0.9rem; margin-bottom:10px; color: var(--body-text-color);">Registres afroamericans</div>
                                        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; max-width:80px; margin:0 auto;">
                                            <span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span>
                                            <span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span>
                                            <span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span>
                                        </div>
                                    </div>

                                </div>

                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:var(--background-fill-secondary);">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDÈNCIA REGISTRADA: Biaix de representació d'origen ètnic</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        El sistema d’IA veu aquest grup ètnic massa sovint (51% vs 28%). Pot associar “alt risc” amb les persones d’aquest grup només perquè apareixen més en els registres d’arrestos.
                                    </div>
                                </div>
                            </div>

                            <div class="scan-pane pane-gender">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">ESCANEJANT: EQUILIBRI DE GÈNERE</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ ABSÈNCIA DE DADAS TROBADA</span>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                                    <div style="text-align:center; padding:20px; background:var(--background-fill-secondary); border-radius:8px; border:1px solid var(--border-color-primary);">
                                        <div style="font-size:4rem; line-height:1;">♂️</div>
                                        <div style="font-size:2.2rem; font-weight:900; color:#3b82f6;">81%</div>
                                        <div style="font-weight:700; color:var(--body-text-color-subdued);">HOMES</div>
                                        <div style="font-size:0.85rem; color:#16a34a; font-weight:600; margin-top:5px;">✅ Ben representats</div>
                                    </div>
                                    <div style="text-align:center; padding:20px; background:rgba(225, 29, 72, 0.1); border-radius:8px; border:2px solid #fda4af;">
                                        <div style="font-size:4rem; line-height:1; opacity:0.5;">♀️</div>
                                        <div style="font-size:2.2rem; font-weight:900; color:#e11d48;">19%</div>
                                        <div style="font-weight:700; color:#fb7185;">DONES</div>
                                        <div style="font-size:0.85rem; color:#e11d48; font-weight:600; margin-top:5px;">⚠️ Dades insuficients</div>
                                    </div>
                                </div>
                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:var(--background-fill-secondary);">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDÈNCIA REGISTRADA: Biaix de representació de gènere</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        Les dones són una classe minoritària en aquest conjunt de dades, tot i que representen aproximadament el 50 % de la població real. El model probablement tindrà dificultats per aprendre patrons precisos per a aquest grup, fet que comportarà <strong>taxes d'error més altes</strong> en les prediccions sobre dones preses.
                                    </div>
                                </div>
                            </div>

                            <div class="scan-pane pane-age">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">ESCANEJANT: DISTRIBUCIÓ D'EDAT</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ PIC DE DISTRIBUCIÓ</span>
                                </div>

                                <div style="padding:20px; background:var(--background-fill-secondary); border-radius:8px; border:1px solid var(--border-color-primary); height:200px; display:flex; align-items:flex-end; justify-content:space-around;">

                                    <div style="width:20%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:var(--body-text-color-subdued); margin-bottom:5px;">Baix</div>
                                        <div style="height:60px; background:var(--border-color-primary); border-radius:4px 4px 0 0; width:100%;"></div>
                                        <div style="margin-top:10px; font-size:0.85rem; font-weight:700; color: var(--body-text-color);">Joves (<25)</div>
                                    </div>

                                    <div style="width:35%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">ALT</div>
                                        <div style="height:120px; background:#ef4444; border-radius:4px 4px 0 0; width:100%; box-shadow:0 4px 10px rgba(239,68,68,0.3);"></div>
                                        <div style="margin-top:10px; font-size:0.9rem; font-weight:800; color:#ef4444;">25-45 (BOMBOLLA)</div>
                                    </div>

                                    <div style="width:20%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:var(--body-text-color-subdued); margin-bottom:5px;">Baix</div>
                                        <div style="height:50px; background:var(--border-color-primary); border-radius:4px 4px 0 0; width:100%;"></div>
                                        <div style="margin-top:10px; font-size:0.85rem; font-weight:700; color: var(--body-text-color);">Grans (>45)</div>
                                    </div>

                                </div>

                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:var(--background-fill-secondary);">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDÈNCIA REGISTRADA: Biaix de representació d'edat</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        Les dades estan concentrades principalment en persones de 25 a 45 anys, la “bombolla d’edat.” El model té un punt cec amb els més joves i els més grans, així que les prediccions per a aquests grups probablement no seran fiables (error de generalització).
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 EVIDÈNCIA DE BIAIX DE REPRESENTACIÓ ESTABLERTA: CONTINUAR MISSIÓ
                </p>
                <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                    Respon a la pregunta següent per rebre el teu proper <strong>augment de la Puntuació de Brúixola Moral</strong>.
                    <br>Després fes clic a <strong>Següent</strong> per <strong>resumir les troballes del laboratori forense de dades.</strong>
                </p>
            </div>

                </div>
            </div>
        """,
    },

    # --- MODULE 4: EVIDENCE REPORT (Input Flaws) ---
    {
        "id":5,
        "title": "Informe d'evidències: Defectes d'entrada",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">✓ REGLES</div>
                    <div class="tracker-step completed">✓ EVIDÈNCIES</div>
                    <div class="tracker-step active">3. ERRORS</div>
                    <div class="tracker-step">4. VEREDICTE</div>
                </div>
                <h2 class="slide-title" style="font-size:1.6rem; text-align:center; margin-bottom:15px;">Informe forense de dades: Defectes d'entrada</h2>
                <div class="ai-risk-container" style="border: 2px solid #ef4444; background: rgba(239,68,68,0.05); padding: 20px;">
                    <h4 style="margin-top:0; font-size:1.2rem; color:#b91c1c; text-align:center;">📋 RESUM D'EVIDÈNCIES</h4>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                        <thead>
                            <tr style="background: rgba(239,68,68,0.1); border-bottom: 2px solid #ef4444;">
                                <th style="padding: 8px; text-align: left;">SECTOR</th>
                                <th style="padding: 8px; text-align: left;">TROBALLA</th>
                                <th style="padding: 8px; text-align: left;">IMPACTE</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style="border-bottom: 1px solid var(--border-color-primary);">
                                <td style="padding: 8px; font-weight:700;">Ètnia</td>
                                <td style="padding: 8px;">Sobrerrepresentada (51%)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risc d'augment de l'error de predicció</td>
                            </tr>
                            <tr style="border-bottom: 1px solid var(--border-color-primary);">
                                <td style="padding: 8px; font-weight:700;">Gènere</td>
                                <td style="padding: 8px;">Infrarrepresentat (19%)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risc d'augment de l'error de predicció</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight:700;">Edat</td>
                                <td style="padding: 8px;">Grups Exclosos (Menys de 25/Més de 45)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risc d'augment de l'error de predicció</td>
                            </tr>
                        </tbody>
                    </table>
                </div>


                <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 SEGÜENT: INVESTIGAR ERRORS EN SORTIDES - CONTINUAR MISSIÓ
                </p>
                <p style="font-size:1.05rem; margin:0;">
                    Respon a la pregunta següent per rebre el teu proper <strong>augment de la Puntuació de Brúixola Moral</strong>.
                    <br>Fes clic a <strong>Següent</strong> per procedir al Pas 3 per trobar proves de danys reals: Les Bretxes d'Error.
                </p>
            </div>
                </div>
            </div>
        """
    },

# --- MODULE 5: INTRO TO PREDICTION ERROR ---
    {
        "id": 6,
        "title": "Part II: Pas 3 — Demostrant l'Error de Predicció",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step completed">2. EVIDÈNCIES</div>
                    <div class="tracker-step active">3. ERRORS</div>
                    <div class="tracker-step">4. VEREDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 3: AVALUAR ERRORS</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">A la recerca d'errors de predicció</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Hem trobat evidències que les dades d'entrada estan esbiaixades. Ara hem d'investigar si aquest biaix ha influït en les <strong>decisions del model</strong>.
                            <br>Busquem el segon senyal d’alerta del nostre manual: les <strong>bretxes d'error</strong>.
                        </p>
                    </div>

                    <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:16px; padding:25px; margin-bottom:25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                        
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px;">
                            <div style="font-size:1.5rem;">🚩</div>
                            <div>
                                <strong style="color:#f43f5e; font-size:1.1rem; text-transform:uppercase; letter-spacing:1px;">PATRÓ: "EL DOBLE RASER"</strong>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">(Impacte desigual dels errors)</div>
                            </div>
                        </div>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
                            
                            <div>
                                <p style="font-size:1rem; line-height:1.6; margin-top:0; color:var(--body-text-color);">
                                    <strong>El concepte:</strong> El “doble raser” vol dir que els errors del sistema d’IA afecten algunes persones més que d’altres, i que persones reals poden resultar perjudicades.
                                </p>

                                <div style="margin-top:15px; margin-bottom:15px;">
                                    <div style="background:rgba(255, 241, 242, 0.1); padding:12px; border-radius:8px; border:1px solid #fda4af; margin-bottom:10px;">
                                        <div style="font-weight:700; color:#fb7185; margin-bottom:4px; font-size:0.95rem;">⚠️ TIPUS 1: FALSES ALARMES (falsos positius)</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); line-height:1.4;">Classificar una persona de baix risc com a <strong>Alt Risc</strong>.</div>
                                        <div style="font-size:0.85rem; font-weight:700; color:#f43f5e; margin-top:4px;">Dany: Detenció injusta.</div>
                                    </div>

                                    <div style="background:rgba(240, 249, 255, 0.1); padding:12px; border-radius:8px; border:1px solid #bae6fd;">
                                        <div style="font-weight:700; color:#38bdf8; margin-bottom:4px; font-size:0.95rem;">⚠️ TIPUS 2: ALERTES NO DETECTADES (Falsos negatius)</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); line-height:1.4;">Classificar una persona d'alt risc com a <strong>Baix Risc</strong>.</div>
                                        <div style="font-size:0.85rem; font-weight:700; color:#0ea5e9; margin-top:4px;">Dany: Risc per a la seguretat pública.</div>
                                    </div>
                                </div>

                                <div style="background:rgba(255, 241, 242, 0.1); color:var(--body-text-color); padding:10px; border-radius:6px; font-size:0.9rem; border-left:4px solid #db2777; margin-top:15px;">
                                    <strong>Pista clau:</strong> Busca una diferència significativa en la <strong>taxa de falses alarmes</strong>. Si el Grup A és assenyalat incorrectament molt més sovint que el Grup B, hi ha una bretxa d’error.
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary); display:flex; flex-direction:column; justify-content:center;">
                                
                                <div style="text-align:center; margin-bottom:10px; font-weight:700; color:var(--body-text-color); font-size:0.9rem;">
                                    "FALSES ALARMES" (Persones innocents classificades com a de risc)
                                </div>

                                <div style="margin-bottom:15px;">
                                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:700; color:#ec4899; margin-bottom:4px;">
                                        <span>GRUP A (Objectiu)</span>
                                        <span>60% ERROR</span>
                                    </div>
                                    <div style="width:100%; background:var(--border-color-primary); height:12px; border-radius:10px; overflow:hidden;">
                                        <div style="width:60%; background:#db2777; height:100%;"></div>
                                    </div>
                                </div>

                                <div>
                                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:4px;">
                                        <span>GRUP B (Referència)</span>
                                        <span>30% ERROR</span>
                                    </div>
                                    <div style="width:100%; background:var(--border-color-primary); height:12px; border-radius:10px; overflow:hidden;">
                                        <div style="width:30%; background:#94a3b8; height:100%;"></div>
                                    </div>
                                </div>

                                <div style="text-align:center; margin-top:15px; font-size:0.85rem; color:#db2777; font-weight:700; background:rgba(255, 241, 242, 0.1); padding:5px; border-radius:4px;">
                                    ⚠️ BRETXA DETECTADA: +30 punts percentuals de diferència
                                </div>

                            </div>
                        </div>
                    </div>

                    <details style="margin-bottom:25px; cursor:pointer; background:rgba(255, 241, 242, 0.1); border:1px solid #fda4af; border-radius:8px; padding:12px;">
                        <summary style="font-weight:700; color:#fb7185; font-size:0.95rem;">🔬 Com el biaix de representació provoca errors de predicció</summary>
                        <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); line-height:1.5; padding:0 5px;">
                            <p style="margin-bottom:10px;"><strong>Connecta els punts:</strong> Al Pas 2, hem detectat que les dades d’entrada sobrerrepresentaven determinats grups.</p>
                            <p><strong>La Teoria:</strong> Com que el sistema de la IA veu aquests grups amb més freqüència als registres de detencions, l’estructura de les dades pot portar el model a cometre errors de predicció específics per grup. El model pot generar moltes més <strong>falses alarmes</strong> per a persones innocents d’aquests grups.</p>
                        </div>
                    </details>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p class="text-danger-adaptive" style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#f43f5e;">
                            🚀 PATRÓ D'ERROR ESTABLERT: CONTINUAR MISSIÓ
                        </p>
                        <p class="text-body-danger-adaptive" style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Respon a la pregunta següent per confirmar el teu objectiu.
                            <br>Després fes clic a <strong>Següent</strong> per obrir el <strong>Laboratori d'error de predicció</strong> i provar les taxes de falses alarmes.
                        </p>
                    </div>

                </div>
            </div>
        """
    },

    # --- MODULE 6: RACE ERROR GAP LAB ---
    {
        "id": 7,
        "title": "Pas 3: Laboratori de Bretxa d'Error Racial",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step completed">2. EVIDÈNCIES</div>
                    <div class="tracker-step active">3. ERRORS</div>
                    <div class="tracker-step">4. VEREDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 3: AVALUAR ERRORS</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">El laboratori d'errors de predicció - Anàlisi per origen ètnic</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Sospitàvem que el model podia generar errors de predicció desiguals entre grups. Ara ho analitzarem.
                            <br>Fes clic per revelar les taxes d'error a continuació. Els errors del sistema de la IA afecten per igual les persones preses blanques i afroamericanes?
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom:25px;">
                        
                        <div class="ai-risk-container" style="padding:0; border:2px solid #ef4444; overflow:hidden; border-radius:12px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.1); background:transparent;">
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af;">
                                <h3 style="margin:0; font-size:1.25rem; color:#ef4444;">📡 ESCANEIG 1: FALSES ALARMES</h3>
                                <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(Persones innocents classificades erròniament com a "Alt Risc")</p>
                            </div>
                            
                            <details style="cursor:pointer; background:var(--background-fill-secondary);">
                                <summary style="list-style:none; padding:20px; font-weight:800; text-align:center; color:#ef4444; font-size:1.1rem; transition:background 0.2s;">
                                    👇 FES CLIC PER REVELAR DADES
                                </summary>
                                <div style="padding:0 20px 25px 20px; text-align:center; border-top:1px solid var(--border-color-primary);">
                                    
                                    <div style="display:flex; justify-content:center; gap:30px; margin-bottom:20px;">
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444; line-height:1;">45%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-top:5px;">AFROAMERICÀ</div>
                                        </div>
                                        <div style="width:1px; background:var(--border-color-primary);"></div>
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#3b82f6; line-height:1;">23%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-top:5px;">BLANC</div>
                                        </div>
                                    </div>

                                    <div class="hint-box" style="border-left:4px solid #ef4444; background:rgba(239, 68, 68, 0.1); text-align:left;">
                                        <div style="font-weight:800; color:#ef4444; font-size:0.95rem;">❌ VEREDICTE: BIAIX PUNITIU</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); margin-top:3px;">
                                            Les persones preses afroamericanes tenen gairebé <strong style="color:#ef4444;">el doble de probabilitats</strong> de ser classificades erròniament com a perillosos en comparació amb les persones preses blanques.
                                        </div>
                                    </div>

                                </div>
                            </details>
                        </div>

                        <div class="ai-risk-container" style="padding:0; border:2px solid #3b82f6; overflow:hidden; border-radius:12px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1); background:transparent;">
                            <div style="background:rgba(59, 130, 246, 0.1); padding:15px; text-align:center; border-bottom:1px solid #bfdbfe;">
                                <h3 style="margin:0; font-size:1.25rem; color:#3b82f6;">📡 ESCANEIG 2: ALERTES NO DETECTADES</h3>
                                <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(Persones que reincideixen classificades erròniament com a "segures")</p>
                            </div>
                            
                            <details style="cursor:pointer; background:var(--background-fill-secondary);">
                                <summary style="list-style:none; padding:20px; font-weight:800; text-align:center; color:#3b82f6; font-size:1.1rem; transition:background 0.2s;">
                                    👇 FES CLIC PER REVELAR DADES
                                </summary>
                                <div style="padding:0 20px 25px 20px; text-align:center; border-top:1px solid var(--border-color-primary);">
                                    
                                    <div style="display:flex; justify-content:center; gap:30px; margin-bottom:20px;">
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444; line-height:1;">28%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-top:5px;">AFROAMERICÀ</div>
                                        </div>
                                        <div style="width:1px; background:var(--border-color-primary);"></div>
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#3b82f6; line-height:1;">48%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-top:5px;">BLANC</div>
                                        </div>
                                    </div>

                                    <div class="hint-box" style="border-left:4px solid #3b82f6; background:rgba(59, 130, 246, 0.1); text-align:left;">
                                        <div style="font-weight:800; color:#3b82f6; font-size:0.95rem;">❌ VEREDICTE: BIAIX DE BENEVOLÈNCIA</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); margin-top:3px;">
                                            Les persones preses blanques que reincideixen tenen moltes més probabilitats de <strong style="color:#3b82f6;">no ser detectades</strong> pel sistema que les persones preses afroamericanes.
                                        </div>
                                    </div>

                                </div>
                            </details>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:20px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#ef4444;">
                            🚀 BRETXA D'ERROR ORIGEN ÈTNIC CONFIRMADA
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Hem demostrat que el model té un "doble raser" per origen ètnic. 
                            <br>Respon a la pregunta següent per certificar les teves troballes, després procedeix al <strong>Pas 4: Analitzar Bretxes d'Error per Gènere, Edat i Geografia.</strong>
                        </p>
                    </div>

                </div>
            </div>
        """
    },

    # --- MODULE 7: GENERALIZATION & PROXY SCAN ---
    {
        "id": 8,
        "title": "Pas 3: Laboratori d'Escaneig de Generalització",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step completed">2. EVIDÈNCIES</div>
                    <div class="tracker-step active">3. ERRORS</div>
                    <div class="tracker-step">4. VEREDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 3: AVALUAR ERRORS</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">El laboratori de predicció d'errors - Gènere, edat i geografia</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Hem revelat la bretxa d’error per origen ètnic. Però el biaix també pot aparèixer en altres llocs.
                            <br>Utilitza l'escàner a continuació per comprovar <strong>errors de representació</strong> de gènere i edat (a causa de manca de dades) i <strong>biaix proxy</strong> (quan dades aparentment neutres substitueixen informació sensible i generen resultats injustos).
                        </p>
                    </div>

                    <div style="margin-top:20px;">
                        <input type="radio" id="scan-gender-err" name="error-tabs" class="scan-radio" checked>
                        <input type="radio" id="scan-age-err" name="error-tabs" class="scan-radio">
                        <input type="radio" id="scan-geo-err" name="error-tabs" class="scan-radio">

                        <div class="forensic-tabs" style="display:flex; justify-content:center; gap:10px; margin-bottom:0;">
                            <label for="scan-gender-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCANEIG: GÈNERE</label>
                            <label for="scan-age-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCANEIG: EDAT</label>
                            <label for="scan-geo-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCANEIG: GEOGRAFIA</label>
                        </div>

                        <div class="scan-content" style="border-top: 3px solid #db2777;">

                            <div class="scan-pane pane-gender-err">
                                <div style="background:rgba(255, 241, 242, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#f43f5e;">📡 ESCAN GÈNERE: ERROR DE PREDICCIÓ</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(La "manca de dades" condueix a més errors?)</p>
                                </div>

                                <details style="cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:rgba(255, 241, 242, 0.1);">
                                        👇 FES CLIC PER REVELAR TAXES DE FALSES ALARMES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#f43f5e;">DONES (classe minoritària)</span>
                                                <span style="font-weight:700; color:#f43f5e;">32% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:32%; background:#db2777; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">HOMES (ben representats)</span>
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">18% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:18%; background:#94a3b8; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:rgba(255, 241, 242, 0.1);">
                                            <div style="font-weight:800; color:#f43f5e;">❌ VEREDICTE: PUNT CEC CONFIRMAT</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                Com que el model disposa de poques dades sobre aquest grup, no ha après patrons fiables i acaba equivocant-se més sovint. 
                                                Aquesta taxa elevada d’error és molt probablement conseqüència de la <strong>manca de dades</strong> que hem detectat al Pas 2. Quan un grup està infrarrepresentat, el model té un punt cec.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <div class="scan-pane pane-age-err">
                                <div style="background:rgba(255, 241, 242, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#f43f5e;">📡 ESCAN EDAT: ERROR DE PREDICCIÓ</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(El model falla fora de la bombolla "25-45"?)</p>
                                </div>

                                <details style="cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:rgba(255, 241, 242, 0.1);">
                                        👇 FES CLIC PER REVELAR TAXES DE FALSES ALARMES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="display:flex; align-items:flex-end; justify-content:space-around; height:100px; margin-bottom:15px; padding-bottom:10px; border-bottom:1px solid var(--border-color-primary);">
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#ef4444; margin-bottom:2px;">33%</div>
                                                <div style="height:60px; background:#ef4444; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px; color:var(--body-text-color);">Menys de 25</div>
                                            </div>
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#16a34a; margin-bottom:2px;">18%</div>
                                                <div style="height:30px; background:#16a34a; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px; color:var(--body-text-color);">25-45</div>
                                            </div>
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#ef4444; margin-bottom:2px;">27%</div>
                                                <div style="height:50px; background:#ef4444; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px; color:var(--body-text-color);">Més de 45</div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:rgba(255, 241, 242, 0.1);">
                                            <div style="font-weight:800; color:#f43f5e;">❌ VEREDICTE: LA FALLADA EN FORMA D'U</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                El model funciona bé dins la bombolla d’edat amb més dades (25–45), però falla clarament fora d’aquest rang. 
                                                Això passa perquè no pot predir amb precisió el risc per a grups d’edat que no ha estudiat prou.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <div class="scan-pane pane-geo-err">
                                <div style="background:rgba(255, 241, 242, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#f43f5e;">📡 ESCAN GEOGRAFIA: LA COMPROVACIÓ PROXY</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(El "codi postal" està creant un doble raser per origen ètnic?)</p>
                                </div>

                                <details style="cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:rgba(255, 241, 242, 0.1);">
                                        👇 FES CLIC PER REVELAR TAXES DE FALSES ALARMES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#f43f5e;">ZONES URBANES (Alta pob. minoritària)</span>
                                                <span style="font-weight:700; color:#f43f5e;">58% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:58%; background:#db2777; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">ZONES RURALS</span>
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">22% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:22%; background:#94a3b8; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:rgba(255, 241, 242, 0.1);">
                                            <div style="font-weight:800; color:#f43f5e;">❌ VEREDICTE: BIAIX PROXY (RELACIÓ OCULTA) CONFIRMAT</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                La taxa d'error a les zones urbanes és molt elevada (58%). 
                                                Encara que s’hagi eliminat la variable d’origen ètnic, el model està utilitzant la <strong>ubicació</strong> com a substitut indirecte per aplicar el mateix criteri. 
                                                En la pràctica, tracta el fet de viure en una zona urbana com un indicador d’alt risc, generant un doble raser per origen ètnic.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                        </div>
                    </div>

                    <div style="text-align:center; margin-top:25px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p class="text-danger-adaptive" style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#f43f5e;">
                            🚀 TOTS ELS SISTEMES ESCANEJATS
                        </p>
                        <p class="text-body-danger-adaptive" style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Has recopilat tota l'evidència forense. El biaix és sistemàtic.
                            <br>Fes clic a <strong>Següent</strong> per fer la teva recomanació final sobre el sistema d'IA.
                        </p>
                    </div>

                </div>
            </div>
        """
    },

    # --- MODULE 8: PREDICTION AUDIT SUMMARY ---
    {
        "id": 9,
        "title": "Pas 3: Resum de l'Informe d'Auditoria",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step completed">2. EVIDÈNCIES</div>
                    <div class="tracker-step active">3. ERRORS</div>
                    <div class="tracker-step">4. VEREDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 3: AVALUAR ERRORS</h2>

                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">Informe d'errors de predicció</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Revisa els teus registres forenses. Has descobert fallades sistemàtiques en múltiples dimensions.
                            <br>Aquestes evidències mostren que el model vulnera el principi bàsic de <strong>Justícia i Equitat</strong>.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:25px; margin-bottom:30px;">

                        <div style="background:rgba(239, 68, 68, 0.1); border:2px solid #ef4444; border-radius:12px; padding:20px; box-shadow: 0 4px 10px rgba(239,68,68,0.1);">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #fda4af; padding-bottom:10px; margin-bottom:15px;">
                                <strong style="color:#ef4444; font-size:1.1rem;">🚨 AMENAÇA PRINCIPAL</strong>
                                <span style="background:#ef4444; color:white; font-size:0.75rem; font-weight:800; padding:4px 8px; border-radius:4px;">CONFIRMAT</span>
                            </div>
                            <h3 style="margin:0 0 10px 0; color:#f87171; font-size:1.25rem;">Doble raser ètnic</h3>
                            <p style="font-size:0.95rem; line-height:1.5; color:var(--body-text-color);">
                                <strong>L'Evidència:</strong> Les persones preses afroamericanes s'enfronten a una <strong style="color:#ef4444;">taxa de falses alarmes del 45%</strong> (vs. 23% per a les persones preses blanques).
                            </p>
                            <div style="background:var(--background-fill-secondary); padding:10px; border-radius:6px; border:1px solid #fda4af; margin-top:10px;">
                                <strong style="color:#ef4444; font-size:0.9rem;">L'Impacte:</strong> 
                                <span style="font-size:0.9rem; color:var(--body-text-color);">Biaix Punitiu. Persones innocents són classificades erròniament com d’alt risc gairebé el doble de vegades que altres grups.</span>
                            </div>
                        </div>

                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px; margin-bottom:15px;">
                                <strong style="color:var(--body-text-color-subdued); font-size:1.1rem;">📍 FALLADA PROXY</strong>
                                <span style="background:#f59e0b; color:white; font-size:0.75rem; font-weight:800; padding:4px 8px; border-radius:4px;">DETECTADA</span>
                            </div>
                            <h3 style="margin:0 0 10px 0; color:var(--body-text-color); font-size:1.25rem;">Discriminació Geogràfica</h3>
                            <p style="font-size:0.95rem; line-height:1.5; color:var(--body-text-color);">
                                <strong>L'Evidència:</strong> Les zones urbanes mostren una <strong style="color:#f59e0b;">taxa d'error molt elevada (58%)</strong>.
                            </p>
                            <div style="background:var(--background-fill-primary); padding:10px; border-radius:6px; border:1px solid var(--border-color-primary); margin-top:10px;">
                                <strong style="color:var(--body-text-color-subdued); font-size:0.9rem;">El mecanisme:</strong> 
                                <span style="font-size:0.9rem; color:var(--body-text-color);">Tot i haver eliminat la variable d’origen ètnic, el sistema de la IA utilitza la ubicació geogràfica (codi postal) com a substitut indirecte, reproduint els mateixos patrons discriminatoris sobre les mateixes comunitats.</span>
                            </div>
                        </div>

                        <div style="grid-column: span 2; background:rgba(14, 165, 233, 0.1); border:2px solid #38bdf8; border-radius:12px; padding:20px;">
                            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                                <span style="font-size:1.5rem;">📉</span>
                                <h3 style="margin:0; color:#38bdf8; font-size:1.2rem;">Fallada secundària: Errors de predicció deguts al biaix de representació</h3>
                            </div>
                            <p style="font-size:1rem; margin-bottom:0; color:var(--body-text-color);">
                                <strong>Evidències:</strong> Alta inestabilitat en les prediccions per a <strong style="color:#38bdf8;">dones i grups d'edat més joves/més grans</strong>.
                                <br>
                                <span style="color:var(--body-text-color-subdued); font-size:0.95rem;"><strong>Per què passa:</strong> Les dades d’entrada no contenien exemples suficients per a aquests grups (el mirall distorsionat), fet que impedeix que el model aprengui patrons fiables i el porta a “endevinar” en lloc de predir.</span>
                            </p>
                        </div>

                    </div>


                    <div style="text-align:center; margin-top:25px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#ef4444;">
                            🚀 EXPEDIENT D'INVESTIGACIÓ TANCAT. EVIDÈNCIA FINAL BLOQUEJADA.
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Has investigat amb èxit les Dades d'Entrada i els Errors de Sortida.
                            <br>Respon a la pregunta següent per augmentar la teva puntuació de Brúixola Moral. Després fes clic a <strong>Següent</strong> per presentar el teu informe final sobre el sistema d'IA.
                        </p>
                    </div>
                </div>
            </div>
        """
    },

    # --- MODULE 9: FINAL VERDICT & REPORT GENERATION ---
{
        "id": 10,
        "title": "Pas 4: El veredicte final",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step completed">2. EVIDÈNCIES</div>
                    <div class="tracker-step completed">3. ERRORS</div>
                    <div class="tracker-step active">4. VEREDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 4: PRESENTA L'INFORME FINAL</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">Construeix l'expedient del cas</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Has completat l'auditoria. Ara cal elaborar l'informe final per al tribunal i altres parts interessades.
                            <br><strong>Selecciona les troballes que estan avalades per evidències</strong> per incorporar-les al registre oficial. Compte: no totes les hipòtesis són vàlides.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:30px;">

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "El Mirall Distorsionat"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AFEGIT A L'INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmat: Les dades d’entrada no reflecteixen la població real. Alguns grups hi apareixen sobrerrepresentats, probablement a causa de biaixos històrics.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Intenció maliciosa del programador"
                            </summary>
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; border-top:1px solid #fecaca; color:var(--body-text-color);">
                                <strong style="color:#ef4444;">❌ REBUTJAT</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">No s’ha trobat cap evidència de codi maliciós ni d’intencionalitat individual. El biaix prové de les <em>dades</em> i els <em>proxies</em>, no de la persona que va desenvolupar el sistema.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Doble raser ètnic"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AFEGIT A L'INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmat: Les persones preses afroamericanes presenten una taxa de falses alarmes aproximadament dues vegades superior a la de les persones preses blanques.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Filtració de Variable Proxy"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AFEGIT A L'INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmat: Tot i eliminar l’origen ètnic com a variable explícita, el sistema utilitza el codi postal com a substitut indirecte, reintroduint el mateix biaix en els resultats.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Error de Càlcul de Hardware"
                            </summary>
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; border-top:1px solid #fecaca; color:var(--body-text-color);">
                                <strong style="color:#ef4444;">❌ REBUTJAT</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Irrellevant. Els sistemes funcionen correctament i els càlculs són consistents. El problema no és tècnic, sinó que els <em>patrons</em> apresos pel model són injustos.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Punts Cecs de Generalització"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AFEGIT A L'INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmat: La manca de dades per a dones, i persones preses més joves i més grans genera prediccions poc fiables per aquests grups.</p>
                            </div>
                        </details>

                    </div>

                    <div style="background:var(--background-fill-primary); border-top:2px solid var(--border-color-primary); padding:25px; text-align:center; border-radius:0 0 12px 12px; margin-top:-15px;">
                        <h3 style="margin-top:0; color:var(--body-text-color);">⚖️ PRESENTA LA TEVA RECOMANACIÓ (responent la pregunta de la Brúixola Moral que trobaràs a continuació)</h3>
                        <p style="font-size:1.05rem; margin-bottom:20px; color:var(--body-text-color-subdued);">
                            Basant-te en l'evidència arxivada anteriorment, quina és la teva recomanació oficial respecte a aquest sistema d'IA?
                        </p>

                        <div style="display:flex; justify-content:center; gap:20px; flex-wrap:wrap;">
                            <div style="background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); padding:15px 25px; border-radius:8px; cursor:pointer; max-width:250px; opacity:0.8; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                                <div style="font-size:2rem; margin-bottom:10px;">✅</div>
                                <div style="font-weight:700; color:#166534; margin-bottom:5px;">CERTIFICAR COM A SEGUR</div>
                                <div style="font-size:0.85rem; color:var(--body-text-color-subdued);">Els biaixos són tecnicismes menors. Continuar utilitzant el sistema.</div>
                            </div>

                            <div style="background:var(--background-fill-secondary); border:2px solid #ef4444; padding:15px 25px; border-radius:8px; cursor:pointer; max-width:250px; box-shadow:0 4px 12px rgba(239,68,68,0.2);">
                                <div style="font-size:2rem; margin-bottom:10px;">🚨</div>
                                <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">SENYAL D'ALERTA: PAUSAR I REPARAR</div>
                                <div style="font-size:0.85rem; color:#ef4444;">El sistema vulnera el principi de Justícia i Equitat. Aturar immediatament.</div>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:30px;">
                        <p style="font-size:0.95rem; color:var(--body-text-color);">
                            Selecciona la teva recomanació final a continuació per presentar oficialment el teu informe i completar la teva investigació.
                        </p>
                    </div>

                </div>
            </div>
        """,
    },


    # --- MODULE 10: PROMOTION ---
{
        "id": 11,
        "title": "Missió Complida: Promoció Desbloquejada",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">✓ REGLES</div>
                    <div class="tracker-step completed">✓ EVIDÈNCIES</div>
                    <div class="tracker-step completed">✓ ERRORS</div>
                    <div class="tracker-step completed">✓ VEREDICTE</div>
                </div>

                <div class="slide-body">
                    
                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#22c55e;">🎉 MISSIÓ COMPLERTA</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Informe Presentat. El tribunal ha acceptat la teva recomanació de posar en <strong>PAUSA</strong> el sistema.
                        </p>
                    </div>

                    <div style="background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; border-radius:12px; padding:20px; margin-bottom:30px; text-align:center; box-shadow: 0 4px 15px rgba(34, 197, 94, 0.1);">
                        <div style="font-size:1.2rem; font-weight:800; color:#22c55e; letter-spacing:1px; text-transform:uppercase;">
                            ✅ DECISIÓ VALIDADA
                        </div>
                        <p style="font-size:1.05rem; color:var(--body-text-color); margin:10px 0 0 0;">
                            La decisió està fonamentada en evidència i raonament, d’acord amb el principi de <strong>Justícia i Equitat</strong>.
                        </p>
                    </div>

                    <div style="background:linear-gradient(135deg, rgba(14, 165, 233, 0.1) 0%, rgba(20, 184, 166, 0.1) 100%); border:2px solid #0ea5e9; border-radius:16px; padding:0; overflow:hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                        
                        <div style="background:#0ea5e9; padding:15px; text-align:center; color:white;">
                            <h3 style="margin:0; font-size:1.3rem; letter-spacing:1px;">🎖️ PROMOCIÓ DESBLOQUEJADA</h3>
                            <div style="font-size:0.9rem; opacity:0.9;">PUJADA DE NIVELL: DE DETECTIU A CONSTRUCTOR</div>
                        </div>

                        <div style="padding:25px;">
                            <p style="text-align:center; font-size:1.1rem; margin-bottom:20px; color:var(--body-text-color);">
                                Detectar el biaix és només el primer pas. Amb l’evidència recollida, el focus passa ara a la millora del sistema.
                                <br><strong>Ara canvies la lupa per una clau anglesa.</strong>
                            </p>

                            <div style="background:var(--background-fill-secondary); border-radius:12px; padding:20px; border:1px solid #bae6fd;">
                                <h4 style="margin-top:0; color:#38bdf8; text-align:center; margin-bottom:15px;">🎓 NOU ROL: ENGINYER D'EQUITAT</h4>
                                
                                <ul style="list-style:none; padding:0; margin:0; font-size:1rem; color:var(--body-text-color);">
                                    <li style="margin-bottom:12px; display:flex; gap:10px; align-items:start;">
                                        <span>🔧</span>
                                        <span><strong style="color:#38bdf8;">Tasca 1:</strong> Identificar i reduir l’ús de variables proxy (com el codi postal).</span>
                                    </li>
                                    <li style="margin-bottom:12px; display:flex; gap:10px; align-items:start;">
                                        <span>📊</span>
                                        <span><strong style="color:#38bdf8;">Tasca 2:</strong> Millorar la representació de les dades i la seva cobertura.</span>
                                    </li>
                                    <li style="display:flex; gap:10px; align-items:start;">
                                        <span>🗺️</span>
                                        <span><strong style="color:#38bdf8;">Tasca 3:</strong> Definir un full de ruta per al monitoratge continu del sistema.</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:30px;">
                        <p style="font-size:1.1rem; font-weight:600; color:var(--body-text-color);">
                            👉 La teva propera missió comença a l'<strong>Activitat 8: L'enginyer d'equitat en acció</strong>.
                            <br>
                            <span style="font-size:0.95rem; font-weight:400; color:var(--body-text-color-subdued);">
                              <strong>Continua amb la següent activitat a sota</strong> per concloure aquesta auditoria i començar a reparar el sistema — o fes clic a <span style="white-space:nowrap;">Següent (barra superior)</span> en vista ampliada ➡️
                            </span>
                        </p>
                    </div>

                </div>
            </div>
        """,
    },]
# --- 5. INTERACTIVE CONTENT CONFIGURATION (APP 1) ---
QUIZ_CONFIG = {
      0: {
        "t": "t1",
        # Added bold incentive text to the question
        "q": "🚀 **Primera oportunitat de puntuació:** Per què multipliquem la teva precisió pel progrés ètic? (Respon correctament per guanyar el teu primer augment de Puntuació de Brúixola Moral!)",
        "o": [
            "A) Perquè la simple precisió ignora el biaix potencial i el dany que pot causar.",
            "B) Per fer les matemàtiques de la classificació més complicades.",
            "C) La precisió és l'única mètrica que realment importa.",
        ],
        "a": "A) Perquè la simple precisió ignora el biaix potencial i el dany que pot causar.",
        # Updated success message to confirm the 'win'
        "success": "<strong>Puntuació Desbloquejada!</strong> Calibratge complet. Ara estàs oficialment a la classificació.",
    },
    1: {
        "t": "t2",
        "q": "Quin és el millor primer pas abans de començar a examinar les dades del model?",
        "o": [
            "Saltar directament a les dades i buscar patrons.",
            "Aprendre les regles que defineixen què compta com a biaix.",
            "Deixar que el model expliqui les seves pròpies decisions.",
        ],
        "a": "Aprendre les regles que defineixen què compta com a biaix.",
        "success": "Sessió informativa completada. Estàs començant la teva investigació amb les regles correctes al cap.",
    },
    2: {
        "t": "t3",
        "q": "Què requereix la Justícia i Equitat?",
        "o": [
            "Explicar les decisions del model",
            "Comprovar els errors de predicció a nivell de grup per prevenir danys sistemàtics",
            "Minimitzar la taxa d'error",
        ],
        "a": "Comprovar els errors de predicció a nivell de grup per prevenir danys sistemàtics",
        "success": "Protocol Actiu. Ara estàs auditant per Justícia i Equitat.",
    },
    3: {
        "t": "t4",
        "q": "Detectiu, sospitem que les dades d'entrada són un 'mirall distorsionat' de la realitat. Per confirmar si existeix biaix de representació, quin és el teu objectiu forense principal?",
        "o": [
            "A) Necessito llegir les entrades del diari personal del jutge.",
            "B) Necessito comprovar si l'ordinador està endollat correctament.",
            "C) Necessito comparar les distribucions demogràfiques (origen ètnic/gènere) de les dades amb les estadístiques de la població real.",
        ],
        "a": "C) Necessito comparar les distribucions demogràfiques (origen ètnic/gènere) de les dades amb les estadístiques de la població real.",
        "success": "Objectiu Adquirit. Estàs preparat per entrar al laboratori forense de dades.",
    },
    4: {
        "t": "t5",
        "q": "Revisió de l'anàlisi forense: Has marcat les dades de gènere com un 'buit de dades' (només 19% dones). Segons el teu registre d'evidències, quin és el risc tècnic específic per a aquest grup?",
        "o": [
            "A) El model tindrà un 'punt cec' perquè no ha vist prou exemples per aprendre patrons precisos.",
            "B) La IA apuntarà automàticament a aquest grup a causa de l'excés de vigilància històrica.",
            "C) El model utilitzarà per defecte les estadístiques del 'món real' per omplir els números que falten.",
        ],
        "a": "A) El model tindrà un 'punt cec' perquè no ha vist prou exemples per aprendre patrons precisos.",
        "success": "Evidència Bloquejada. Entens que les dades que falten creen punts cecs, fent que les prediccions per a aquest grup siguin menys fiables.",
    },
    # --- QUESTION 4 (Evidence Report Summary) ---
    5: {
        "t": "t6",
        "q": "Detectiu, revisa la teva taula de resum d'evidències. Has trobat casos tant de sobrerrepresentació (origen ètnic) com d'infrarrepresentació (gènere/edat). Quina és la teva conclusió general sobre com el biaix de representació afecta un sistema d'IA?",
        "o": [
            "A) Confirma que el conjunt de dades és neutral, ja que les categories 'Sobre' i 'Infra' es cancel·len matemàticament entre si.",
            "B) Crea un 'risc d'augment de l'error de predicció' en AMBDUES direccions: tant si un grup s'exagera com si s'ignora, la visió de la realitat del sistema de l'IA es deforma.",
            "C) Només crea risc quan falten dades (Infrarrepresentació); tenir dades extra (Sobrerrepresentació) en realitat fa que el model sigui més precís.",
        ],
        "a": "B) Crea un 'risc d'augment de l'error de predicció' en AMBDUES direccions: tant si un grup s'exagera com si s'ignora, la visió de la realitat del sistema de l'IA es deforma.",
        "success": "Conclusió Verificada. Les dades distorsionades, tant si estan inflades com si falten, poden portar a una justícia distorsionada.",
    },
    6: {
        "t": "t7",
        "q": "Detectiu, has trobat el patró del 'doble raser'. Quina peça específica d'evidència representa aquesta senyal d'alerta?",
        "o": [
            "A) El model comet zero errors per a cap grup.",
            "B) Un grup pateix una taxa de 'falses alarmes' significativament més alta que un altre grup.",
            "C) Les dades d'entrada contenen més homes que dones.",
        ],
        "a": "B) Un grup pateix una taxa de 'falses alarmes' significativament més alta que un altre grup.",
        "success": "Patró Confirmat. Quan la taxa d'error està desequilibrada, és un doble raser.",
    },
    # --- QUESTION 6 (Race Error Gap) ---
    7: {
        "t": "t8",
        "q": "Revisa el teu registre de dades. Què ha revelat l'escaneig de 'falses alarmes' sobre el tractament dels acusats afroamericans?",
        "o": [
            "A) Són tractats exactament igual que els acusats blancs.",
            "B) Són omesos pel sistema més sovint (biaix de benevolència).",
            "C) Tenen gairebé el doble de probabilitats de ser marcats erròniament com a 'Alt Risc' (biaix punitiu).",
        ],
        "a": "C) Tenen gairebé el doble de probabilitats de ser marcats erròniament com a 'Alt Risc' (biaix punitiu).",
        "success": "Evidència Registrada. El sistema està castigant persones innocents basant-se en l'origen ètnic.",
    },

    # --- QUESTION 7 (Generalization & Proxy Scan) ---
    8: {
        "t": "t9",
        "q": "L'escaneig geogràfic ha mostrat una taxa d'error massiva a les zones urbanes. Què revela això sobre els 'codis postals'?",
        "o": [
            "A) Els codis postals actuen com una variable proxy (indicadors indirectes d’altres característiques), fins i tot quan variables com l'origen ètnic s'han eliminat del conjunt de dades.",
            "B) La IA és simplement dolenta llegint mapes i dades d'ubicació.",
            "C) La gent a les ciutats genera naturalment més errors informàtics que la gent a les zones rurals.",
        ],
        "a": "A) Els codis postals actuen com una variable proxy (indicadors indirectes d’altres característiques), fins i tot quan variables com l'origen ètnic s'han eliminat del conjunt de dades.",
        "success": "Proxy Identificat. Amagar una variable no funciona si deixes un proxy enrere.",
    },

    # --- QUESTION 8 (Audit Summary) ---
    9: {
        "t": "t10",
        "q": "Has tancat l'expedient del cas. Quina de les següents opcions està CONFIRMADA com l''amenaça principal' al teu informe final?",
        "o": [
            "A) Un doble raser d'origen ètnic on els acusats negres innocents són penalitzats el doble de vegades.",
            "B) Codi maliciós escrit per hackers per trencar el sistema.",
            "C) Una fallada de hardware a la sala de servidors causant errors matemàtics aleatoris.",
        ],
        "a": "A) Un doble raser d'origen ètnic on els acusats negres innocents són penalitzats el doble de vegades.",
        "success": "Amenaça avaluada. El biaix està confirmat i documentat.",
    },

    # --- QUESTION 9 (Final Verdict) ---
    10: {
        "t": "t11",
        "q": "Basant-te en les violacions de Justícia i Equitat trobades a la teva auditoria, quina és la teva recomanació final al tribunal?",
        "o": [
            "A) CERTIFICAR: El sistema està majoritàriament bé, els errors menors són acceptables.",
            "B) AVÍS VERMELL: Pausar immediatament el sistema per fer-hi reparacions, ja que és insegur i esbiaixat.",
            "C) ADVERTÈNCIA: Utilitzar el sistema d'IA només els caps de setmana quan el crim és més baix.",
        ],
        "a": "B) AVÍS VERMELL: Pausar immediatament el sistema per fer-hi reparacions, ja que és insegur i esbiaixat.",
        "success": "Veredicte Lliurat. Has aturat amb èxit un sistema nociu.",
    },
}


# --- 6. SCENARIO CONFIG (for Module 0) ---
SCENARIO_CONFIG = {
    "Criminal risk prediction": {
        "q": (
            "A system predicts who might reoffend.\n"
            "Why isn’t accuracy alone enough?"
        ),
        "summary": "Even tiny bias can repeat across thousands of bail/sentencing calls — real lives, real impact.",
        "a": "Accuracy can look good overall while still being unfair to specific groups affected by the model.",
        "rationale": "Bias at scale means one pattern can hurt many people quickly. We must check subgroup fairness, not just the top-line score."
    },
    "Loan approval system": {
        "q": (
            "A model decides who gets a loan.\n"
            "What’s the biggest risk if it learns from biased history?"
        ),
        "summary": "Some groups get blocked over and over, shutting down chances for housing, school, and stability.",
        "a": "It can repeatedly deny the same groups, copying old patterns and locking out opportunity.",
        "rationale": "If past approvals were unfair, the model can mirror that and keep doors closed — not just once, but repeatedly."
    },
    "College admissions screening": {
        "q": (
            "A tool ranks college applicants using past admissions data.\n"
            "What’s the main fairness risk?"
        ),
        "summary": "It can favor the same profiles as before, overlooking great candidates who don’t ‘match’ history.",
        "a": "It can amplify past preferences and exclude talented students who don’t fit the old mold.",
        "rationale": "Models trained on biased patterns can miss potential. We need checks to ensure diverse, fair selection."
    }
}

# --- 7. SLIDE 3 RIPPLE EFFECT SLIDER HELPER ---
def simulate_ripple_effect_cases(cases_per_year):
    try:
        c = float(cases_per_year)
    except (TypeError, ValueError):
        c = 0.0
    c_int = int(c)
    if c_int <= 0:
        message = (
            "Si el sistema no s'utilitza en cap cas, el seu biaix no pot fer mal a ningú encara — "
            "però un cop entri en funcionament, cada decisió esbiaixada pot escalar ràpidament."
        )
    elif c_int < 5000:
        message = (
            f"Fins i tot amb <strong>{c_int}</strong> casos per any, un model esbiaixat pot afectar "
            "silenciosament centenars de persones amb el temps."
        )
    elif c_int < 15000:
        message = (
            f"Amb al voltant de <strong>{c_int}</strong> casos per any, un model esbiaixat podria etiquetar injustament "
            "milers de persones com a 'alt risc'."
        )
    else:
        message = (
            f"Amb <strong>{c_int}</strong> casos per any, un algoritme defectuós pot donar forma al futur "
            "de tota una regió — convertint el biaix ocult en milers de decisions injustes."
        )

    return f"""
    <div class="hint-box interactive-block">
        <p style="margin-bottom:4px; font-size:1.05rem;">
            <strong>Estimated cases processed per year:</strong> {c_int}
        </p>
        <p style="margin-bottom:0; font-size:1.05rem;">
            {message}
        </p>
    </div>
    """

# --- 7b. STATIC SCENARIOS RENDERER (Module 0) ---
def render_static_scenarios():
    cards = []
    for name, cfg in SCENARIO_CONFIG.items():
        q_html = cfg["q"].replace("\\n", "<br>")
        cards.append(f"""
            <div class="hint-box" style="margin-top:12px;">
                <div style="font-weight:700; font-size:1.05rem;">📘 {name}</div>
                <p style="margin:8px 0 6px 0;">{q_html}</p>
                <p style="margin:0;"><strong>Key takeaway:</strong> {cfg["a"]}</p>
                <p style="margin:6px 0 0 0; color:var(--body-text-color-subdued);">{cfg["f_correct"]}</p>
            </div>
        """)
    return "<div class='interactive-block'>" + "".join(cards) + "</div>"

def render_scenario_card(name: str):
    cfg = SCENARIO_CONFIG.get(name)
    if not cfg:
        return "<div class='hint-box'>Selecciona un escenari per veure els detalls.</div>"
    q_html = cfg["q"].replace("\n", "<br>")
    return f"""
    <div class="scenario-box">
        <h3 class="slide-title" style="font-size:1.4rem; margin-bottom:8px;">📘 {name}</h3>
        <div class="slide-body">
            <div class="hint-box">
                <p style="margin:0 0 6px 0; font-size:1.05rem;">{q_html}</p>
                <p style="margin:0 0 6px 0;"><strong>Key takeaway:</strong> {cfg['a']}</p>
                <p style="margin:0; color:var(--body-text-color-subdued);">{cfg['rationale']}</p>
            </div>
        </div>
    </div>
    """

def render_scenario_buttons():
    # Stylized, high-contrast buttons optimized for 17–20 age group
    btns = []
    for name in SCENARIO_CONFIG.keys():
        btns.append(gr.Button(
            value=f"🎯 {name}",
            variant="primary",
            elem_classes=["scenario-choice-btn"]
        ))
    return btns

# --- 8. LEADERBOARD & API LOGIC ---
def get_leaderboard_data(client, username, team_name, local_task_list=None, override_score=None):
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])

        # 1. OPTIMISTIC UPDATE
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

        # 2. SORT with new score
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
            # Fallback to alternative table name
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

    # 1. Update Lists
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

    # 2. Write to Server
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

    # 3. Calculate Scores Locally (Simulate Before/After)
    old_score_calc = acc * (len(old_task_list) / TOTAL_COURSE_TASKS)
    new_score_calc = acc * (len(new_task_list) / TOTAL_COURSE_TASKS)

    # 4. Get Data with Override to force rank re-calculation
    prev_data = get_leaderboard_data(
        client, username, team_name, old_task_list, override_score=old_score_calc
    )
    lb_data = get_leaderboard_data(
        client, username, team_name, new_task_list, override_score=new_score_calc
    )

    return prev_data, lb_data, username, new_task_list

# --- 9. SUCCESS MESSAGE RENDERER (approved version) ---
# --- 8. SUCCESS MESSAGE / DASHBOARD RENDERING ---
def generate_success_message(prev, curr, specific_text):
    old_score = float(prev.get("score", 0) or 0) if prev else 0.0
    new_score = float(curr.get("score", 0) or 0)
    diff_score = new_score - old_score

    old_rank = prev.get("rank", "–") if prev else "–"
    new_rank = curr.get("rank", "–")

    # Are ranks integers? If yes, we can reason about direction.
    ranks_are_int = isinstance(old_rank, int) and isinstance(new_rank, int)
    rank_diff = old_rank - new_rank if ranks_are_int else 0  # positive => rank improved

    # --- STYLE SELECTION -------------------------------------------------
    # First-time score: special "on the board" moment
    if old_score == 0 and new_score > 0:
        style_key = "first"
    else:
        if ranks_are_int:
            if rank_diff >= 3:
                style_key = "major"   # big rank jump
            elif rank_diff > 0:
                style_key = "climb"   # small climb
            elif diff_score > 0 and new_rank == old_rank:
                style_key = "solid"   # better score, same rank
            else:
                style_key = "tight"   # leaderboard shifted / no visible rank gain
        else:
            # When we can't trust rank as an int, lean on score change
            style_key = "solid" if diff_score > 0 else "tight"

    # --- TEXT + CTA BY STYLE --------------------------------------------
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
    else:  # "solid"
        header_emoji = "✅"
        header_title = "Progrés Registrat"
        summary_line = "La teva perspectiva ètica ha augmentat la teva Puntuació de Brúixola Moral."
        cta_line = "Prova el següent escenari per arribar al següent nivell."

    # --- SCORE / RANK LINES ---------------------------------------------

    # First-time: different wording (no previous score)
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
                rank_line = f"📊 Rang: <strong>#{new_rank}</strong> (mantenint-se estable)"
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

    # --- HTML COMPOSITION -----------------------------------------------
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

# --- 10. DASHBOARD & LEADERBOARD RENDERERS ---
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

def check_audit_report_selection(selected_biases: List[str]) -> Tuple[str, str]:
    # Define the correct findings (matching the choices defined in the front-end)
    CORRECT_FINDINGS = [
        "Choice A: Punitive Bias (Race): AA defendants were twice as likely to be falsely labeled 'High Risk.'",
        "Choice B: Generalization (Gender): The model made more False Alarm errors for women than for men.",
        "Choice C: Leniency Pattern (Race): White defendants who re-offended were more likely to be labeled 'Low Risk.'",
        "Choice E: Proxy Bias (Geography): Location acted as a proxy, doubling False Alarms in high-density areas.",
    ]

    # Define the incorrect finding
    INCORRECT_FINDING = "Choice D: FALSE STATEMENT: The model achieved an equal False Negative Rate (FNR) across all races."

    # Separate correct from incorrect selections
    correctly_selected = [s for s in selected_biases if s in CORRECT_FINDINGS]
    incorrectly_selected = [s for s in selected_biases if s == INCORRECT_FINDING]

    # Check if any correct finding was missed
    missed_correct = [s for s in CORRECT_FINDINGS if s not in selected_biases]

    # --- Generate Feedback ---
    feedback_html = ""
    if incorrectly_selected:
        feedback_html = f"<div class='hint-box' style='border-left:4px solid #ef4444; color:#b91c1c;'>❌ ERROR: L'afirmació '{INCORRECT_FINDING.split(':')[0]}' NO és una troballa veritable. Comprova els resultats del teu laboratori i torna-ho a intentar.</div>"
    elif missed_correct:
        feedback_html = f"<div class='hint-box' style='border-left:4px solid #f97316; color:#f97316;'>⚠️ INCOMPLET: T'has perdut {len(missed_correct)} peça/es d'evidència clau. El teu informe final ha d'estar complet.</div>"
    elif len(selected_biases) == len(CORRECT_FINDINGS):
        feedback_html = "<div class='hint-box' style='border-left:4px solid #22c55e; color:#16a34a;'>✅ EVIDÈNCIA ASSEGURADA: Aquest és un diagnòstic complet i precís de l'error sistemàtic del model.</div>"
    else:
        feedback_html = "<div class='hint-box' style='border-left:4px solid var(--color-accent);'>Recopilant evidència...</div>"

    # --- Build Markdown Report Preview ---
    if not correctly_selected:
        report_markdown = "Selecciona les targetes d'evidència de dalt per començar a redactar el teu informe. (L'esborrany de l'informe apareixerà aquí.)"
    else:
        lines = []
        lines.append("### 🧾 Esborrany de l'Informe d'Auditoria")
        lines.append("\n**Troballes d'Error Sistemàtic:**")

        # Map short findings to the markdown report
        finding_map = {
            "Choice A": "Punitive Bias (Race): The model is twice as harsh on AA defendants.",
            "Choice B": "Generalization (Gender): Higher False Alarm errors for women.",
            "Choice C": "Leniency Pattern (Race): More missed warnings for White defendants.",
            "Choice E": "Proxy Bias (Geography): Location acts as a stand-in for race/class.",
        }

        for i, choice in enumerate(CORRECT_FINDINGS):
            if choice in correctly_selected:
                short_key = choice.split(':')[0]
                lines.append(f"{i+1}. {finding_map[short_key]}")

        if len(correctly_selected) == len(CORRECT_FINDINGS) and not incorrectly_selected:
             lines.append("\n**CONCLUSION:** The evidence proves the system creates unequal harm and violates Justice & Equity.")

        report_markdown = "\n".join(lines)

    return report_markdown, feedback_html

# --- 11. CSS ---
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
/* Add these new classes to your existing CSS block (Section 11) */

/* --- PROGRESS TRACKER STYLES --- */
.tracker-container {
  display: flex;
  justify-content: space-around;
  align-items: center;
  margin-bottom: 25px;
  background: var(--background-fill-secondary);
  padding: 10px 0;
  border-radius: 8px;
  border: 1px solid var(--border-color-primary);
}
.tracker-step {
  text-align: center;
  font-weight: 700;
  font-size: 0.85rem;
  padding: 5px 10px;
  border-radius: 4px;
  color: var(--body-text-color-subdued);
  transition: all 0.3s ease;
}
.tracker-step.completed {
  color: #10b981; /* Green */
  background: rgba(16, 185, 129, 0.1);
}
.tracker-step.active {
  color: var(--color-accent); /* Primary Hue */
  background: var(--color-accent-soft);
  box-shadow: 0 0 5px rgba(99, 102, 241, 0.3);
}

/* --- FORENSICS TAB STYLES --- */
.forensic-tabs {
  display: flex;
  border-bottom: 2px solid var(--border-color-primary);
  margin-bottom: 0;
}
.tab-label-styled {
  padding: 10px 15px;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--body-text-color-subdued);
  border-bottom: 2px solid transparent;
  margin-bottom: -2px; /* Align with border */
  transition: color 0.2s ease;
}

/* Hide the radio buttons */
.scan-radio { display: none; }

/* Content panel styling */
.scan-content {
  background: var(--body-background-fill); /* Light gray or similar */
  padding: 20px;
  border-radius: 0 8px 8px 8px;
  border: 1px solid var(--border-color-primary);
  min-height: 350px;
  position: relative;
}

/* Hide all panes by default */
.scan-pane { display: none; }

/* Show active tab content */
#scan-race:checked ~ .scan-content .pane-race,
#scan-gender:checked ~ .scan-content .pane-gender,
#scan-age:checked ~ .scan-content .pane-age {
  display: block;
}

/* Highlight active tab label */
#scan-race:checked ~ .forensic-tabs label[for="scan-race"],
#scan-gender:checked ~ .forensic-tabs label[for="scan-gender"],
#scan-age:checked ~ .forensic-tabs label[for="scan-age"] {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

/* Utility for danger color */
:root {
    --color-danger-light: rgba(239, 68, 68, 0.1);
    --color-accent-light: rgba(99, 102, 241, 0.15); /* Reusing accent color for general bars */
}
/* --- NEW SELECTORS FOR MODULE 8 (Generalization Scan Lab) --- */

/* Show active tab content in Module 8 */
#scan-gender-err:checked ~ .scan-content .pane-gender-err,
#scan-age-err:checked ~ .scan-content .pane-age-err,
#scan-geo-err:checked ~ .scan-content .pane-geo-err {
  display: block;
}

/* Highlight active tab label in Module 8 */
#scan-gender-err:checked ~ .forensic-tabs label[for="scan-gender-err"],
#scan-age-err:checked ~ .forensic-tabs label[for="scan-age-err"],
#scan-geo-err:checked ~ .forensic-tabs label[for="scan-geo-err"] {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

/* If you used .data-scan-tabs instead of .forensic-tabs in Module 8 HTML,
   the selectors above need to target the parent container correctly.
   Assuming you used the structure from the draft: */

.data-scan-tabs input[type="radio"]:checked + .tab-label-styled {
    color: var(--color-accent);
    border-bottom-color: var(--color-accent);
}

.data-scan-tabs .scan-content .scan-pane {
    display: none;
}
.data-scan-tabs #scan-gender-err:checked ~ .scan-content .pane-gender-err,
.data-scan-tabs #scan-age-err:checked ~ .scan-content .pane-age-err,
.data-scan-tabs #scan-geo-err:checked ~ .scan-content .pane-geo-err {
    display: block;
}
/* --- DARK MODE TEXT FIXES --- */

/* Class to force dark text on elements inside white/light cards so they stay readable */
.force-dark-text {
    color: #1f2937 !important;
}

/* Adaptive Header Color */
/* Light Mode Default */
.header-accent {
    color: #0c4a6e;
}
/* Dark Mode Override (Light Blue) */
body.dark .header-accent, .dark .header-accent {
    color: #e0f2fe;
}

/* Adaptive Red Text for Footers */
/* Light Mode (Dark Red) */
.text-danger-adaptive {
    color: #9f1239;
}
/* Dark Mode (Light Pink) */
body.dark .text-danger-adaptive, .dark .text-danger-adaptive {
    color: #fda4af;
}

/* Adaptive Body Red Text */
/* Light Mode (Darker Red) */
.text-body-danger-adaptive {
    color: #881337;
}
/* Dark Mode (Lighter Pink) */
body.dark .text-body-danger-adaptive, .dark .text-body-danger-adaptive {
    color: #fecdd3;
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

# --- 12. HELPER: SLIDER FOR MORAL COMPASS SCORE (MODULE 0) ---
def simulate_moral_compass_score(acc, progress_pct):
    try:
        acc_val = float(acc)
    except (TypeError, ValueError):
        acc_val = 0.0
    try:
        prog_val = float(progress_pct)
    except (TypeError, ValueError):
        prog_val = 0.0

    score = acc_val * (prog_val / 100.0)
    return f"""
    <div class="hint-box interactive-block">
        <p style="margin-bottom:4px; font-size:1.05rem;">
            <strong>Your current accuracy (from the leaderboard):</strong> {acc_val:.3f}
        </p>
        <p style="margin-bottom:4px; font-size:1.05rem;">
            <strong>Simulated Ethical Progress %:</strong> {prog_val:.0f}%
        </p>
        <p style="margin-bottom:0; font-size:1.08rem;">
            <strong>Simulated Moral Compass Score:</strong> 🧭 {score:.3f}
        </p>
    </div>
    /* --- DARK MODE FIXES --- */
    
    /* Class to force dark text on elements inside white cards */
    /* This ensures text inside white boxes stays readable in Dark Mode */
    .force-dark-text {
        color: #1f2937 !important;
    }
    
    /* Adaptive header color */
    /* Default (Light Mode) */
    .header-accent {
        color: #0c4a6e;
    }
    
    /* Dark Mode Override */
    /* Changes header to light blue when Gradio is in Dark Mode */
    body.dark .header-accent, .dark .header-accent {
        color: #e0f2fe;
    }
    """


# --- 13. APP FACTORY (APP 1) ---
def create_bias_detective_ca_sustainability_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        module0_done = gr.State(value=False)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

        # --- TOP ANCHOR & LOADING OVERLAY FOR NAVIGATION ---
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Carregant...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>🕵️‍♀️ Autenticant...</h2>"
                "<p>Sincronitzant dades de Brúixola Moral...</p>"
                "</div>"
            )

        # --- MAIN APP VIEW ---
        with gr.Column(visible=False) as main_app_col:
            # Title
            #gr.Markdown("# 🕵️‍♀️ Bias Detective: Part 1 - Data Forensics")

            # Top summary dashboard (progress bar & score)
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



                    # --- QUIZ CONTENT FOR MODULES WITH QUIZ_CONFIG ---
                    if i in QUIZ_CONFIG:
                        q_data = QUIZ_CONFIG[i]

                        # Compact points chip and hint above the question
                        gr.HTML(
                            "<div class='quiz-cta'>"
                            "<span class='points-chip'>🧭 Punts de la Brúixola Moral disponibles</span>"
                            "<span>Respon per augmentar la teva puntuació</span>"
                            "</div>"
                        )

                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Selecciona una resposta:",
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
                            else "🎉 Has completat la part 1! (Passa a la següent activitat)"
                        )
                        btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            # Leaderboard card appears AFTER content & interactions
            leaderboard_html = gr.HTML()

            # --- WIRING: QUIZ LOGIC ---
            for mod_id, radio_comp, feedback_comp in quiz_wiring_queue:

                def quiz_logic_wrapper(
                    user,
                    tok,
                    team,
                    acc_val,
                    task_list,
                    ans,
                    mid=mod_id,
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
                            "❌ Incorrecte. Revisa l'evidència anterior.</div>",
                            task_list,
                        )

                radio_comp.change(
                    fn=quiz_logic_wrapper,
                    inputs=[
                        username_state,
                        token_state,
                        team_state,
                        accuracy_state,
                        task_list_state,
                        radio_comp,
                    ],
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
                client = MoralcompassApiClient(
                    api_base_url=DEFAULT_API_URL, auth_token=token
                )

                # Simple team assignment helper
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
                        fetched_tasks = getattr(
                            user_stats, "completed_task_ids", []
                        ) or []

                # Sync baseline moral compass record
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

                data, _ = ensure_table_and_get_data(
                    user, token, team, fetched_tasks
                )
                return (
                    user,
                    token,
                    team,
                    False,
                    render_top_dashboard(data, 0),
                    render_leaderboard_card(data, user, team),
                    acc,
                    fetched_tasks,
                    gr.update(visible=False),
                    gr.update(visible=True),
                )

            # Auth failed / no session
            return (
                None,
                None,
                None,
                False,
                "<div class='hint-box'>⚠️ Error d’autenticació. Inicia l’activitat des de l’enllaç del curs.</div>",
                "",
                0.0,
                [],
                gr.update(visible=False),
                gr.update(visible=True),
            )

        # Attach load event
        demo.load(
            handle_load,
            None,
            [
                username_state,
                token_state,
                team_state,
                module0_done,
                out_top,
                leaderboard_html,
                accuracy_state,
                task_list_state,
                loader_col,
                main_app_col,
            ],
        )

        # --- JAVASCRIPT HELPER FOR NAVIGATION ---
        def nav_js(target_id: str, message: str) -> str:
            """Generate JavaScript for smooth navigation with loading overlay."""
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

        # --- NAVIGATION BETWEEN MODULES ---
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]

            # Previous button
            if i > 0:
                prev_col = module_ui_elements[i - 1][0]
                prev_target_id = f"module-{i-1}"

                def make_prev_handler(p_col, c_col, target_id):
                    def navigate_prev():
                        # First yield: hide current, show nothing (transition state)
                        yield gr.update(visible=False), gr.update(visible=False)
                        # Second yield: show previous, hide current
                        yield gr.update(visible=True), gr.update(visible=False)
                    return navigate_prev

                prev_btn.click(
                    fn=make_prev_handler(prev_col, curr_col, prev_target_id),
                    outputs=[prev_col, curr_col],
                    js=nav_js(prev_target_id, "Carregant..."),
                )

            # Next button
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
                        # First yield: hide current, show nothing (transition state)
                        yield gr.update(visible=False), gr.update(visible=False)
                        # Second yield: hide current, show next
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




def launch_bias_detective_ca_sustainability_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    """
    Launch the Bias Detective V2 app.

    Args:
        share: Whether to create a public link
        server_name: Server hostname
        server_port: Server port
        theme_primary_hue: Primary color hue
        **kwargs: Additional Gradio launch arguments
    """
    app = create_bias_detective_ca_sustainability_app(theme_primary_hue=theme_primary_hue)
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        **kwargs
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    launch_bias_detective_ca_app(share=False, debug=True, height=1000)

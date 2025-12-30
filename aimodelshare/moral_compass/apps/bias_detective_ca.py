import os
import sys
import subprocess
import time
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"
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
                                El teu objectiu: Exposar els defectes abans que aquest model es desplegui a nivell nacional.
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
                                    <span>RISC: L'"Efecte Ona"</span>
                                </div>
                                <span style="font-size:0.9rem; color:#ef4444; text-transform:uppercase;">Fes clic per simular</span>
                            </summary>
                            <div style="padding:25px; border-top:1px solid var(--border-color-primary);">
                                <div style="display:flex; gap:30px; align-items:center;">
                                    <div style="font-size:3.5rem; line-height:1;">🌊</div>
                                    <div>
                                        <div style="font-weight:900; font-size:2.0rem; color:#ef4444; line-height:1;">15.000+</div>
                                        <div style="font-weight:700; font-size:1.1rem; color:var(--body-text-color); margin-bottom:5px;">Casos Processats per Any</div>
                                        <div style="font-size:1.1rem; color:var(--body-text-color-subdued); line-height:1.5;">
                                            Un humà comet un error una vegada. Aquesta IA repetirà el mateix biaix <strong style="color:var(--body-text-color);">15.000+ vegades a l'any</strong>.
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
                                    <span>OBJECTIU: Com Guanyar</span>
                                </div>
                                <span style="font-size:0.9rem; color:#22c55e; text-transform:uppercase;">Fes clic per calcular</span>
                            </summary>
                            <div style="padding:25px; border-top:1px solid var(--border-color-primary);">
                                <div style="text-align:center; margin-bottom:20px;">
                                    <div style="font-size:1.4rem; font-weight:800; background:var(--background-fill-primary); border:1px solid var(--border-color-primary); padding:15px; border-radius:10px; display:inline-block; color:var(--body-text-color);">
                                        <span style="color:#6366f1;">[ Exactitud ]</span>
                                        <span style="color:var(--body-text-color-subdued); margin:0 10px;">×</span>
                                        <span style="color:#22c55e;">[ % Progrés Ètic ]</span>
                                        <span style="color:var(--body-text-color-subdued); margin:0 10px;">=</span>
                                        PUNTUACIÓ
                                    </div>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                                    <div style="padding:15px; background:rgba(254,226,226,0.1); border:2px solid #fecaca; border-radius:10px; text-align:center;">
                                        <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">Escenari A: Ètica Ignorada</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">Alta Exactitud (92%)</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">0% Ètica</div>
                                        <div style="margin-top:10px; border-top:1px solid #fecaca; padding-top:5px;">
                                            <div style="font-size:0.8rem; text-transform:uppercase; color:#ef4444;">Puntuació Final</div>
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444;">0</div>
                                        </div>
                                    </div>
                                    <div style="padding:15px; background:rgba(220,252,231,0.1); border:2px solid #bbf7d0; border-radius:10px; text-align:center;">
                                        <div style="font-weight:700; color:#22c55e; margin-bottom:5px;">Escenari B: Veritable Detectiu</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">Alta Exactitud (92%)</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">100% Ètica</div>
                                        <div style="margin-top:10px; border-top:1px solid #bbf7d0; padding-top:5px;">
                                            <div style="font-size:0.8rem; text-transform:uppercase; color:#15803d;">Puntuació Final</div>
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
        "title": "Full de Ruta de la Missió",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <h2 class="slide-title" style="text-align:center; margin-bottom:15px;">🗺️ FULL DE RUTA DE LA MISSIÓ</h2>

                    <p style="font-size:1.1rem; max-width:800px; margin:0 auto 25px auto; text-align:center; color:var(--body-text-color);">
                        <strong>La teva missió és clara:</strong> Descobrir el biaix amagat dins del 
                        sistema d'IA abans que faci mal a persones reals. Si no pots trobar el biaix, no el podem arreglar.
                    </p>

                    <div class="ai-risk-container" style="background:transparent; border:none; padding:0;">

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">

                            <div style="border: 3px solid #3b82f6; background: rgba(59, 130, 246, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#3b82f6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PAS 1: REGLES</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">📜</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#3b82f6; margin-bottom:5px;">Establir les Regles</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Defineix l'estàndard ètic: <strong>Justícia i Equitat</strong>. Què compta específicament com a biaix en aquesta investigació?
                                </div>
                            </div>

                            <div style="border: 3px solid #14b8a6; background: rgba(20, 184, 166, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#14b8a6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PAS 2: EVIDÈNCIA DE DADES</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">🔍</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#14b8a6; margin-bottom:5px;">Forensia de Dades d'Entrada</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Escaneja les <strong>Dades d'Entrada</strong> per trobar injustícies històriques, buits de representació i biaixos d'exclusió.
                                </div>
                            </div>

                            <div style="border: 3px solid #8b5cf6; background: rgba(139, 92, 246, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#8b5cf6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PAS 3: PROVAR ERROR</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">🎯</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#8b5cf6; margin-bottom:5px;">Proves d'Error de Sortida</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Prova les prediccions del model. Demostra que els errors (Falses Alarmes) són <strong>desiguals</strong> entre grups.
                                </div>
                            </div>

                            <div style="border: 3px solid #f97316; background: rgba(249, 115, 22, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#f97316; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PAS 4: REPORTAR IMPACTE</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">⚖️</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#f97316; margin-bottom:5px;">L'Informe Final</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Diagnostica el dany sistemàtic i emet la teva recomanació final al tribunal: <strong>Desplegar el Sistema d'IA o Pausar per Reparar.</strong>
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
                    <div class="tracker-step">2. EVIDÈNCIA</div>
                    <div class="tracker-step">3. ERROR</div>
                    <div class="tracker-step">4. VERDICTE</div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h2 class="slide-title" style="margin:0;">PAS 1: APRÈN LES REGLES</h2>
                    <div style="font-size:2rem;">⚖️</div>
                </div>

                <div class="slide-body">

                    <div style="background:rgba(59, 130, 246, 0.1); border-left:4px solid #3b82f6; padding:15px; margin-bottom:20px; border-radius:4px; color: var(--body-text-color);">
                        <p style="margin:0; font-size:1.05rem; line-height:1.5;">
                            <strong style="color:var(--color-accent);">Justícia i Equitat: La Teva Regla Principal.</strong><br>
                            L'ètica no és abstracta aquí, és la nostra guia de camp per a l'acció. Confiem en l'assessorament expert de l'Observatori d'Ètica en Intel·ligència Artificial de Catalunya <strong>OEIAC (UdG)</strong> per assegurar que els sistemes d'IA siguin justos.
                            Tot i que han definit 7 principis bàsics d'IA segura, la nostra informació suggereix que aquest cas específic implica una violació de <strong>Justícia i Equitat</strong>.
                        </p>
                    </div>

                    <div style="text-align:center; margin-bottom:20px;">
                        <p style="font-size:1rem; font-weight:700; color:var(--color-accent); background:rgba(59, 130, 246, 0.1); display:inline-block; padding:6px 16px; border-radius:20px; border:1px solid var(--border-color-primary);">
                            👇 Fes clic a cada targeta per revelar què compta com a biaix
                        </p>
                    </div>

                    <p style="text-align:center; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:10px; font-size:0.9rem; letter-spacing:1px;">
                        🧩 JUSTÍCIA I EQUITAT: QUÈ COMPTA COM A BIAIX?
                    </p>

                    <div class="ai-risk-container" style="background:transparent; border:none; padding:0;">
                        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:15px;">

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #3b82f6; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#3b82f6; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">📊</div>
                                    Biaix de Representació
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Definició:</strong> Compara la distribució del conjunt de dades amb la distribució real del món real.
                                    <br><br>
                                    Si un grup apareix molt menys (p. ex., només el 10% dels casos són del Grup A, però són el 71% de la població) o molt més que la realitat, la IA probablement aprendrà patrons esbiaixats.
                                </div>
                            </details>

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #ef4444; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#ef4444; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">🎯</div>
                                    Bretxes d'Error
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Definició:</strong> Comprova els errors de predicció de la IA per subgrup (p. ex., Taxa de Falsos Positius per al Grup A vs. Grup B).
                                    <br><br>
                                    Un error més alt per a un grup indica risc de tracte injust, mostrant que el model pot ser menys fiable per a aquest grup específic.
                                </div>
                            </details>

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #22c55e; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#22c55e; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">⛓️</div>
                                    Disparitats de Resultats
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Definició:</strong> Busca pitjors resultats al món real després de les prediccions de la IA (p. ex., sentències més dures).
                                    <br><br>
                                    El biaix no són només números: canvia els resultats del món real per a les persones.
                                </div>
                            </details>
                        </div>
                    </div>

                    <hr style="opacity:0.2; margin:25px 0; border-color:var(--body-text-color);">

                    <details class="hint-box" style="margin-top:0; cursor:pointer;">
                        <summary style="font-weight:700; color:var(--body-text-color-subdued);">🧭 Referència: Altres Principis d'Ètica en IA (OEIAC)</summary>
                        <div style="margin-top:15px; font-size:0.9rem; display:grid; grid-template-columns: 1fr 1fr; gap:15px; color:var(--body-text-color);">
                            <div>
                                <strong>Transparència i Explicabilitat</strong><br>Assegurar que el raonament de la IA i el judici final siguin clars perquè les decisions es puguin inspeccionar i la gent pugui apel·lar.<br>
                                <strong>Seguretat i No-maleficència</strong><br>Minimitzar els errors nocius i tenir sempre un pla sòlid per a fallades del sistema.<br>
                                <strong>Responsabilitat i Rendició de Comptes</strong><br>Assignar propietaris clars per a la IA i mantenir un registre detallat de les decisions (rastre d'auditoria).
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
                    <div class="tracker-step active">2. EVIDÈNCIA</div>
                    <div class="tracker-step">3. ERROR</div>
                    <div class="tracker-step">4. VERDICTE</div>
                </div>

        <div class="slide-body">
            <h2 class="slide-title" style="margin:0;">PAS 2: CERCA DE L'EVIDÈNCIA</h2>

            <div style="text-align:center; margin-bottom:20px;">

                <h2 class="slide-title header-accent" style="margin-top:10px;">La Recerca de Patrons Demogràfics Esbiaixats</h2>
                <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                    Una IA només és tan justa com les dades de les quals aprèn. Si les dades d'entrada distorsionen la realitat, la IA probablement distorsionarà la justícia.
                    <br>El primer pas és buscar patrons que revelin <strong>Biaix de Representació.</strong>  Per trobar biaix de representació hem d'inspeccionar la <strong>Demografia.</strong>.
                </p>
            </div>

            <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:16px; padding:25px; margin-bottom:20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px;">
                    <div style="font-size:1.5rem;">🚩</div>
                    <div>
                        <strong style="color:#0ea5e9; font-size:1.1rem; text-transform:uppercase; letter-spacing:1px;">PATRÓ: "EL MIRALL DISTORSIONAT"</strong>
                        <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">(Biaix de Representació en Grups Protegits)</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
                    
                    <div style="color: var(--body-text-color);">
                        <p style="font-size:1rem; line-height:1.6;">
                            <strong>El Concepte:</strong> Idealment, un conjunt de dades hauria de semblar un "Mirall" de la població real. 
                            Si un grup constitueix el 50% de la població, generalment hauria de constituir ~50% de les dades.
                        </p>
                        <p style="font-size:1rem; line-height:1.6;">
                            <strong>La Bandera Vermella:</strong> Busca <strong>Desequilibris Dràstics</strong> en Característiques Protegides (Raça, Gènere, Edat).
                        </p>
                        <ul style="font-size:0.95rem; color:var(--body-text-color-subdued); margin-top:10px; padding-left:20px; line-height:1.5;">
                            <li><strong>Sobrerrepresentació:</strong> Un grup té una "Barra Gegant" (p. ex., el 80% dels registres d'arrest són Homes). La IA aprèn a apuntar a aquest grup.</li>
                            <li><strong>Infrarrepresentació:</strong> Un grup falta o és petit. La IA no aconsegueix aprendre patrons precisos per a ells.</li>
                        </ul>
                    </div>

                    <div style="background:var(--background-fill-primary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary); display:flex; flex-direction:column; justify-content:center;">
                        
                        <div style="margin-bottom:20px;">
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:5px;">REALITAT (La Població)</div>
                            <div style="display:flex; width:100%; height:24px; border-radius:4px; overflow:hidden;">
                                <div style="width:33%; background:#94a3b8; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grup A</div>
                                <div style="width:34%; background:#64748b; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grup B</div>
                                <div style="width:33%; background:#475569; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grup C</div>
                            </div>
                        </div>

                        <div>
                            <div style="font-size:0.85rem; font-weight:700; color:#0ea5e9; margin-bottom:5px;">LES DADES D'ENTRENAMENT (El Mirall Distorsionat)</div>
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
                    <strong>🕵️ El Teu Proper Pas:</strong> Has d'entrar al Laboratori Forense de Dades i comprovar les dades per a categories demogràfiques específiques. Si els patrons s'assemblen al "Mirall Distorsionat" de dalt, les dades probablement són insegures.
                </p>
            </div>

            <details style="margin-bottom:30px; cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; padding:12px;">
                <summary style="font-weight:700; color:var(--body-text-color-subdued); font-size:0.95rem;">🧭 Referència: Com esdevenen esbiaixats els conjunts de dades d'IA?</summary>
                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color-subdued); line-height:1.5; padding:0 5px;">
                    <p style="margin-bottom:10px;"><strong>Exemple:</strong> Quan un conjunt de dades es construeix a partir de <strong>registres històrics d'arrests</strong>.</p>
                    <p>L'excés de vigilància policial sistèmic en barris específics podria distorsionar els recomptes en el conjunt de dades per atributs com <strong>Raça o Ingressos</strong>.
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
        "title": "Pas 2: Laboratori Forense de Dades",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step active">2. EVIDÈNCIA</div>
                    <div class="tracker-step">3. ERROR</div>
                    <div class="tracker-step">4. VERDICTE</div>
                </div>

           <h2 class="slide-title" style="margin:0;">PAS 2: CERCA DE L'EVIDÈNCIA</h2>

            <div style="text-align:center; margin-bottom:20px;">

                <h2 class="slide-title header-accent" style="margin-top:10px;">El Laboratori Forense de Dades</h2>                
                <div class="slide-body">

                    <p style="text-align:center; max-width:700px; margin:0 auto 15px auto; font-size:1.1rem; color:var(--body-text-color);">
                        Busca evidències de Biaix de Representació.
                        Compara la població del **Món Real** amb les **Dades d'Entrada** de la IA.
                        <br>La IA "veu" el món tal com és realment o veus evidència de representació distorsionada?
                    </p>

                <div style="text-align:center; margin-bottom:20px;">
                    <p style="font-size:1rem; font-weight:700; color:var(--color-accent); background:rgba(59, 130, 246, 0.1); display:inline-block; padding:6px 16px; border-radius:20px; border:1px solid var(--border-color-primary);">
                        👇 Fes clic per escanejar cada categoria demogràfica i revelar l'evidència
                    </p>
               </div>

                    <div style="margin-top:20px;">
                        <input type="radio" id="scan-race" name="scan-tabs" class="scan-radio" checked>
                        <input type="radio" id="scan-gender" name="scan-tabs" class="scan-radio">
                        <input type="radio" id="scan-age" name="scan-tabs" class="scan-radio">

                        <div class="forensic-tabs" style="display:flex; justify-content:center; gap:10px; margin-bottom:0;">
                            <label for="scan-race" class="tab-label-styled" style="flex:1; text-align:center;">ESCAN: RAÇA</label>
                            <label for="scan-gender" class="tab-label-styled" style="flex:1; text-align:center;">ESCAN: GÈNERE</label>
                            <label for="scan-age" class="tab-label-styled" style="flex:1; text-align:center;">ESCAN: EDAT</label>
                        </div>

                        <div class="scan-content" style="border-top: 3px solid var(--color-accent);">

                            <div class="scan-pane pane-race">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">ESCANEJANT: DISTRIBUCIÓ RACIAL</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ ANOMALIA DETECTADA</span>
                                </div>

                                <div style="display:grid; grid-template-columns: 1fr 0.2fr 1fr; align-items:center; gap:10px;">

                                    <div style="text-align:center; background:var(--background-fill-secondary); padding:15px; border-radius:8px; border:1px solid var(--border-color-primary);">
                                        <div style="font-size:0.9rem; font-weight:700; color:var(--body-text-color-subdued); letter-spacing:1px;">MÓN REAL</div>
                                        <div style="font-size:2rem; font-weight:900; color:#3b82f6; margin:5px 0;">28%</div>
                                        <div style="font-size:0.9rem; margin-bottom:10px; color: var(--body-text-color);">Població Afroamericana</div>
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
                                        <div style="font-size:0.9rem; margin-bottom:10px; color: var(--body-text-color);">Registres Afroamericans</div>
                                        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; max-width:80px; margin:0 auto;">
                                            <span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span>
                                            <span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span>
                                            <span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span>
                                        </div>
                                    </div>

                                </div>

                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:var(--background-fill-secondary);">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDÈNCIA REGISTRADA: Biaix de Representació Racial</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        La IA està **sobre-exposada** a aquest grup (51% vs 28%). Pot aprendre a associar "Alt Risc" amb aquesta demografia simplement perquè els veu més sovint als registres d'arrest.
                                    </div>
                                </div>
                            </div>

                            <div class="scan-pane pane-gender">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">ESCANEJANT: EQUILIBRI DE GÈNERE</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ BUID DE DADES TROBAT</span>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                                    <div style="text-align:center; padding:20px; background:var(--background-fill-secondary); border-radius:8px; border:1px solid var(--border-color-primary);">
                                        <div style="font-size:4rem; line-height:1;">♂️</div>
                                        <div style="font-size:2.2rem; font-weight:900; color:#3b82f6;">81%</div>
                                        <div style="font-weight:700; color:var(--body-text-color-subdued);">HOMES</div>
                                        <div style="font-size:0.85rem; color:#16a34a; font-weight:600; margin-top:5px;">✅ Ben Representats</div>
                                    </div>
                                    <div style="text-align:center; padding:20px; background:rgba(225, 29, 72, 0.1); border-radius:8px; border:2px solid #fda4af;">
                                        <div style="font-size:4rem; line-height:1; opacity:0.5;">♀️</div>
                                        <div style="font-size:2.2rem; font-weight:900; color:#e11d48;">19%</div>
                                        <div style="font-weight:700; color:#fb7185;">DONES</div>
                                        <div style="font-size:0.85rem; color:#e11d48; font-weight:600; margin-top:5px;">⚠️ Dades Insuficients</div>
                                    </div>
                                </div>
                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:var(--background-fill-secondary);">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDÈNCIA REGISTRADA: Biaix de Representació de Gènere</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        Les dones són una "classe minoritària" en aquest conjunt de dades tot i que típicament constitueixen el 50% de la població real. El model probablement tindrà dificultats per aprendre patrons precisos per a elles, donant lloc a **taxes d'error més altes** per a les acusades.
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
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDÈNCIA REGISTRADA: Biaix de Representació d'Edat</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        Les dades es concentren en la "Bombolla" d'edat de 25-45. El model té un **punt cec** per a persones més joves i més grans, el que significa que les prediccions per a aquests grups seran poc fiables (Error de Generalització).
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
        "title": "Informe d'Evidència: Defectes d'Entrada",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">✓ REGLES</div>
                    <div class="tracker-step completed">✓ EVIDÈNCIA</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICTE</div>
                </div>
                <h2 class="slide-title" style="font-size:1.6rem; text-align:center; margin-bottom:15px;">Informe Forense de Dades: Defectes d'Entrada</h2>
                <div class="ai-risk-container" style="border: 2px solid #ef4444; background: rgba(239,68,68,0.05); padding: 20px;">
                    <h4 style="margin-top:0; font-size:1.2rem; color:#b91c1c; text-align:center;">📋 RESUM D'EVIDÈNCIA</h4>
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
                                <td style="padding: 8px; font-weight:700;">Raça</td>
                                <td style="padding: 8px;">Sobrerrepresentada (51%)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risc d'Augment de l'Error de Predicció</td>
                            </tr>
                            <tr style="border-bottom: 1px solid var(--border-color-primary);">
                                <td style="padding: 8px; font-weight:700;">Gènere</td>
                                <td style="padding: 8px;">Infrarrepresentat (19%)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risc d'Augment de l'Error de Predicció</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight:700;">Edat</td>
                                <td style="padding: 8px;">Grups Exclosos (Menys de 25/Més de 45)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risc d'Augment de l'Error de Predicció</td>
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
                    <br>Fes clic a <strong>Següent</strong> per procedir al **Pas 3** per trobar proves de danys reals: **Les Bretxes d'Error**.
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
                    <div class="tracker-step completed">2. EVIDÈNCIA</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 3: AVALUAR ERRORS DE PREDICCIÓ</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">La Recerca d'Errors de Predicció</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Hem trobat proves que les Dades d'Entrada estan esbiaixades. Ara hem d'investigar si aquest biaix ha influït en les <strong>Decisions del Model</strong>.
                            <br>Estem buscant la segona Bandera Vermella del nostre Reglament: <strong>Bretxes d'Error</strong>.
                        </p>
                    </div>

                    <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:16px; padding:25px; margin-bottom:25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                        
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px;">
                            <div style="font-size:1.5rem;">🚩</div>
                            <div>
                                <strong style="color:#f43f5e; font-size:1.1rem; text-transform:uppercase; letter-spacing:1px;">PATRÓ: "EL DOBLE ESTÀNDARD"</strong>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">(Impacte Desigual dels Errors)</div>
                            </div>
                        </div>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
                            
                            <div>
                                <p style="font-size:1rem; line-height:1.6; margin-top:0; color:var(--body-text-color);">
                                    <strong>El Concepte:</strong> La predicció d'un model dóna forma al futur d'una persona. Quan comet un error, la gent real pateix.
                                </p>

                                <div style="margin-top:15px; margin-bottom:15px;">
                                    <div style="background:rgba(255, 241, 242, 0.1); padding:12px; border-radius:8px; border:1px solid #fda4af; margin-bottom:10px;">
                                        <div style="font-weight:700; color:#fb7185; margin-bottom:4px; font-size:0.95rem;">⚠️ TIPUS 1: FALSES ALARMES</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); line-height:1.4;">Etiquetar una persona de baix risc com a <strong>Alt Risc</strong>.</div>
                                        <div style="font-size:0.85rem; font-weight:700; color:#f43f5e; margin-top:4px;">Dany: Detenció Injusta.</div>
                                    </div>

                                    <div style="background:rgba(240, 249, 255, 0.1); padding:12px; border-radius:8px; border:1px solid #bae6fd;">
                                        <div style="font-weight:700; color:#38bdf8; margin-bottom:4px; font-size:0.95rem;">⚠️ TIPUS 2: ADVERTÈNCIES OMESES</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); line-height:1.4;">Etiquetar una persona d'alt risc com a <strong>Baix Risc</strong>.</div>
                                        <div style="font-size:0.85rem; font-weight:700; color:#0ea5e9; margin-top:4px;">Dany: Risc per a la Seguretat Pública.</div>
                                    </div>
                                </div>

                                <div style="background:rgba(255, 241, 242, 0.1); color:var(--body-text-color); padding:10px; border-radius:6px; font-size:0.9rem; border-left:4px solid #db2777; margin-top:15px;">
                                    <strong>Pista Clau:</strong> Busca una bretxa significativa en la <strong>Taxa de Falses Alarmes</strong>. Si el Grup A és marcat incorrectament substancialment més que el Grup B, això és una Bretxa d'Error.
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary); display:flex; flex-direction:column; justify-content:center;">
                                
                                <div style="text-align:center; margin-bottom:10px; font-weight:700; color:var(--body-text-color); font-size:0.9rem;">
                                    "FALSES ALARMES" (Persones Innocents Marcades com a Arriscades)
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
                                    ⚠️ BRETXA DETECTADA: +30 Punts Percentuals de Diferència
                                </div>

                            </div>
                        </div>
                    </div>

                    <details style="margin-bottom:25px; cursor:pointer; background:rgba(255, 241, 242, 0.1); border:1px solid #fda4af; border-radius:8px; padding:12px;">
                        <summary style="font-weight:700; color:#fb7185; font-size:0.95rem;">🔬 La Hipòtesi: Com està connectat el Biaix de Representació amb l'Error de Predicció?</summary>
                        <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); line-height:1.5; padding:0 5px;">
                            <p style="margin-bottom:10px;"><strong>Uneix els punts:</strong> Al Pas 2, vam trobar que les dades d'entrada sobrerepresentaven grups específics.</p>
                            <p><strong>La Teoria:</strong> Com que la IA veia aquests grups més sovint en els registres d'arrest, l'estructura de les dades pot portar el model a cometre errors de predicció específics per a grups. El model pot generar més <strong>Falses Alarmes</strong> per a persones innocents d'aquests grups a una taxa molt més alta.</p>
                        </div>
                    </details>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p class="text-danger-adaptive" style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#f43f5e;">
                            🚀 PATRÓ D'ERROR ESTABLERT: CONTINUAR MISSIÓ
                        </p>
                        <p class="text-body-danger-adaptive" style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Respon a la pregunta següent per confirmar el teu objectiu.
                            <br>Després fes clic a <strong>Següent</strong> per obrir el <strong>Laboratori d'Error de Predicció</strong> i provar les Taxes de Falses Alarmes.
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
                    <div class="tracker-step completed">2. EVIDÈNCIA</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 3: ANALITZAR LA BRETXA D'ERROR DE PREDICCIÓ</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">El Laboratori d'Error de Predicció - Anàlisi de Raça</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Sospitàvem que el model genera quantitats injustes d'errors de predicció per a grups específics. Ara, executem l'anàlisi.
                            <br>Fes clic per revelar les taxes d'error a continuació. Els errors de la IA cauen igualment entre acusats blancs i negres?
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom:25px;">
                        
                        <div class="ai-risk-container" style="padding:0; border:2px solid #ef4444; overflow:hidden; border-radius:12px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.1); background:transparent;">
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af;">
                                <h3 style="margin:0; font-size:1.25rem; color:#ef4444;">📡 ESCAN 1: FALSES ALARMES</h3>
                                <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(Persones innocents marcades erròniament com a "Alt Risc")</p>
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
                                        <div style="font-weight:800; color:#ef4444; font-size:0.95rem;">❌ VERDICTE: BIAIX PUNITIU</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); margin-top:3px;">
                                            Els acusats negres tenen gairebé <strong style="color:#ef4444;">el doble de probabilitats</strong> de ser etiquetats erròniament com a perillosos en comparació amb els acusats blancs.
                                        </div>
                                    </div>

                                </div>
                            </details>
                        </div>

                        <div class="ai-risk-container" style="padding:0; border:2px solid #3b82f6; overflow:hidden; border-radius:12px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1); background:transparent;">
                            <div style="background:rgba(59, 130, 246, 0.1); padding:15px; text-align:center; border-bottom:1px solid #bfdbfe;">
                                <h3 style="margin:0; font-size:1.25rem; color:#3b82f6;">📡 ESCAN 2: ADVERTÈNCIES OMESES</h3>
                                <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(Persones arriscades marcades erròniament com a "Segures")</p>
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
                                        <div style="font-weight:800; color:#3b82f6; font-size:0.95rem;">❌ VERDICTE: BIAIX DE BENEVOLÈNCIA</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); margin-top:3px;">
                                            Els acusats blancs que reincideixen tenen moltes més probabilitats de ser <strong style="color:#3b82f6;">omesos</strong> pel sistema que els acusats negres.
                                        </div>
                                    </div>

                                </div>
                            </details>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:20px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#ef4444;">
                            🚀 BRETXA D'ERROR RACIAL CONFIRMADA
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Hem demostrat que el model té un "Doble Estàndard" per raça. 
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
                    <div class="tracker-step completed">2. EVIDÈNCIA</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 3: ANALITZAR LA BRETXA D'ERROR DE PREDICCIÓ</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">Escanejos d'Error de Gènere, Edat i Geografia</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Hem revelat la Bretxa d'Error Racial. Però el biaix s'amaga també en altres llocs.
                            <br>Utilitza l'escàner a continuació per comprovar <strong>Errors de Representació</strong> de gènere i edat (degut a buits de dades) i <strong>Biaix Proxy</strong> (variables ocultes).
                        </p>
                    </div>

                    <div style="margin-top:20px;">
                        <input type="radio" id="scan-gender-err" name="error-tabs" class="scan-radio" checked>
                        <input type="radio" id="scan-age-err" name="error-tabs" class="scan-radio">
                        <input type="radio" id="scan-geo-err" name="error-tabs" class="scan-radio">

                        <div class="forensic-tabs" style="display:flex; justify-content:center; gap:10px; margin-bottom:0;">
                            <label for="scan-gender-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCAN: GÈNERE</label>
                            <label for="scan-age-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCAN: EDAT</label>
                            <label for="scan-geo-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCAN: GEOGRAFIA</label>
                        </div>

                        <div class="scan-content" style="border-top: 3px solid #db2777;">

                            <div class="scan-pane pane-gender-err">
                                <div style="background:rgba(255, 241, 242, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#f43f5e;">📡 ESCAN GÈNERE: ERROR DE PREDICCIÓ</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(El "Buit de Dades" condueix a més errors?)</p>
                                </div>

                                <details style="cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:rgba(255, 241, 242, 0.1);">
                                        👇 FES CLIC PER REVELAR TAXES DE FALSES ALARMES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#f43f5e;">DONES (La Classe Minoritària)</span>
                                                <span style="font-weight:700; color:#f43f5e;">32% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:32%; background:#db2777; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">HOMES (Ben Representats)</span>
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">18% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:18%; background:#94a3b8; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:rgba(255, 241, 242, 0.1);">
                                            <div style="font-weight:800; color:#f43f5e;">❌ VERDICTE: PUNT CEC CONFIRMAT</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                Com que el model té menys dades sobre dones, està "endevinant" més sovint. 
                                                Aquesta alta taxa d'error és molt probablement el resultat del <strong>Buit de Dades</strong> que vam trobar al Pas 2.
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
                                            <div style="font-weight:800; color:#f43f5e;">❌ VERDICTE: LA FALLADA EN FORMA D'U</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                El model funciona bé per a la "Bombolla" (25-45) amb més dades però falla significativament per a les categories d'edat de menys de 25 i més de 45. 
                                                No pot predir amb precisió el risc per a grups d'edat que no ha estudiat prou.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <div class="scan-pane pane-geo-err">
                                <div style="background:rgba(255, 241, 242, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#f43f5e;">📡 ESCAN GEOGRAFIA: LA COMPROVACIÓ PROXY</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(Està el "Codi Postal" creant un doble estàndard racial?)</p>
                                </div>

                                <details style="cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:rgba(255, 241, 242, 0.1);">
                                        👇 FES CLIC PER REVELAR TAXES DE FALSES ALARMES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#f43f5e;">ZONES URBANES (Alta Pob. Minoritària)</span>
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
                                            <div style="font-weight:800; color:#f43f5e;">❌ VERDICTE: BIAIX PROXY (RELACIÓ OCULTA) CONFIRMAT</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                La taxa d'error en Zones Urbanes és massiva (58%). 
                                                Fins i tot si es va eliminar "Raça", el model està utilitzant la <strong>Ubicació</strong> per apuntar als mateixos grups. 
                                                Està tractant "Resident de Ciutat" com un sinònim d'"Alt Risc".
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
                    <div class="tracker-step completed">2. EVIDÈNCIA</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 3: RESUM DE L'INFORME D'AUDITORIA</h2>

                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">Anàlisi Final de Predicció</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Revisa els teus registres forenses. Has descobert fallades sistemàtiques en múltiples dimensions.
                            <br>Aquesta evidència mostra que el model viola el principi bàsic de <strong>Justícia i Equitat</strong>.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:25px; margin-bottom:30px;">

                        <div style="background:rgba(239, 68, 68, 0.1); border:2px solid #ef4444; border-radius:12px; padding:20px; box-shadow: 0 4px 10px rgba(239,68,68,0.1);">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #fda4af; padding-bottom:10px; margin-bottom:15px;">
                                <strong style="color:#ef4444; font-size:1.1rem;">🚨 AMENAÇA PRINCIPAL</strong>
                                <span style="background:#ef4444; color:white; font-size:0.75rem; font-weight:800; padding:4px 8px; border-radius:4px;">CONFIRMAT</span>
                            </div>
                            <h3 style="margin:0 0 10px 0; color:#f87171; font-size:1.25rem;">Doble Estàndard Racial</h3>
                            <p style="font-size:0.95rem; line-height:1.5; color:var(--body-text-color);">
                                <strong>L'Evidència:</strong> Els acusats afroamericans s'enfronten a una <strong style="color:#ef4444;">Taxa de Falses Alarmes del 45%</strong> (vs. 23% per als acusats blancs).
                            </p>
                            <div style="background:var(--background-fill-secondary); padding:10px; border-radius:6px; border:1px solid #fda4af; margin-top:10px;">
                                <strong style="color:#ef4444; font-size:0.9rem;">L'Impacte:</strong> 
                                <span style="font-size:0.9rem; color:var(--body-text-color);">Biaix Punitiu. Persones innocents estan sent marcades erròniament per a detenció al doble de la taxa que altres.</span>
                            </div>
                        </div>

                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px; margin-bottom:15px;">
                                <strong style="color:var(--body-text-color-subdued); font-size:1.1rem;">📍 FALLADA PROXY</strong>
                                <span style="background:#f59e0b; color:white; font-size:0.75rem; font-weight:800; padding:4px 8px; border-radius:4px;">DETECTAT</span>
                            </div>
                            <h3 style="margin:0 0 10px 0; color:var(--body-text-color); font-size:1.25rem;">Discriminació Geogràfica</h3>
                            <p style="font-size:0.95rem; line-height:1.5; color:var(--body-text-color);">
                                <strong>L'Evidència:</strong> Les Zones Urbanes mostren una massiva <strong style="color:#f59e0b;">Taxa d'Error del 58%</strong>.
                            </p>
                            <div style="background:var(--background-fill-primary); padding:10px; border-radius:6px; border:1px solid var(--border-color-primary); margin-top:10px;">
                                <strong style="color:var(--body-text-color-subdued); font-size:0.9rem;">El Mecanisme:</strong> 
                                <span style="font-size:0.9rem; color:var(--body-text-color);">Tot i que "Raça" estava oculta, la IA va utilitzar el "Codi Postal" com a escletxa per apuntar a les mateixes comunitats.</span>
                            </div>
                        </div>

                        <div style="grid-column: span 2; background:rgba(14, 165, 233, 0.1); border:2px solid #38bdf8; border-radius:12px; padding:20px;">
                            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                                <span style="font-size:1.5rem;">📉</span>
                                <h3 style="margin:0; color:#38bdf8; font-size:1.2rem;">Fallada Secundària: Errors de Predicció Deguts al Biaix de Representació</h3>
                            </div>
                            <p style="font-size:1rem; margin-bottom:0; color:var(--body-text-color);">
                                <strong>L'Evidència:</strong> Alta inestabilitat en les prediccions per a <strong style="color:#38bdf8;">Dones i Grups d'Edat Més Joves/Més Grans</strong>.
                                <br>
                                <span style="color:var(--body-text-color-subdued); font-size:0.95rem;"><strong>Per què?</strong> Les dades d'entrada mancaven d'exemples suficients per a aquests grups (El Mirall Distorsionat), fent que el model "endevini" en lloc d'aprendre.</span>
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
        "title": "Pas 4: El Verdicte Final",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLES</div>
                    <div class="tracker-step completed">2. EVIDÈNCIA</div>
                    <div class="tracker-step completed">3. ERROR</div>
                    <div class="tracker-step active">4. VERDICTE</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PAS 4: PRESENTA EL TEU INFORME FINAL</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">Munta l'Expedient del Cas</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Has completat l'auditoria. Ara has de construir l'informe final per al tribunal i altres parts interessades.
                            <br><strong>Selecciona les troballes vàlides a continuació</strong> per afegir-les al registre oficial. Aneu amb compte: no inclogueu proves falses.
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
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmat: Les Dades d'Entrada sobrerepresenten incorrectament grups demogràfics específics probablement degut en part a un biaix històric.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Intenció Maliciosa del Programador"
                            </summary>
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; border-top:1px solid #fecaca; color:var(--body-text-color);">
                                <strong style="color:#ef4444;">❌ REBUTJAT</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Incorrecte. No hem trobat cap evidència de codi maliciós. El biaix provenia de les <em>dades</em> i els <em>proxies</em>, no de la personalitat del programador.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Doble Estàndard Racial"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AFEGIT A L'INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmat: Els acusats afroamericans pateixen una taxa de Falses Alarmes 2x més alta que els acusats blancs.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Filtració de Variable Proxy"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AFEGIT A L'INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmat: El "Codi Postal" funciona com un proxy per a la Raça, reintroduint el biaix fins i tot quan variables com la Raça s'eliminen.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Error de Càlcul de Hardware"
                            </summary>
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; border-top:1px solid #fecaca; color:var(--body-text-color);">
                                <strong style="color:#ef4444;">❌ REBUTJAT</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Irrellevant. Els servidors funcionen bé. Les matemàtiques són correctes; els <em>patrons</em> que ha après són injustos.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Troballa: "Punts Cecs de Generalització"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AFEGIT A L'INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmat: La manca de dades per a Dones, i acusats més Joves i més Grans crea prediccions poc fiables.</p>
                            </div>
                        </details>

                    </div>

                    <div style="background:var(--background-fill-primary); border-top:2px solid var(--border-color-primary); padding:25px; text-align:center; border-radius:0 0 12px 12px; margin-top:-15px;">
                        <h3 style="margin-top:0; color:var(--body-text-color);">⚖️ PRESENTA LA TEVA RECOMANACIÓ (Utilitzant la Pregunta de Brúixola Moral sota aquestes targetes.)</h3>
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
                                <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">AVÍS VERMELL: PAUSAR I REPARAR</div>
                                <div style="font-size:0.85rem; color:#ef4444;">El sistema viola els principis de Justícia i Equitat. Aturar immediatament.</div>
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
                    <div class="tracker-step completed">✓ EVIDÈNCIA</div>
                    <div class="tracker-step completed">✓ ERROR</div>
                    <div class="tracker-step completed">✓ VERDICTE</div>
                </div>

                <div class="slide-body">
                    
                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#22c55e;">🎉 MISSIÓ COMPLIDA</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Informe Presentat. El tribunal ha acceptat la teva recomanació de <strong>PAUSAR</strong> el sistema.
                        </p>
                    </div>

                    <div style="background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; border-radius:12px; padding:20px; margin-bottom:30px; text-align:center; box-shadow: 0 4px 15px rgba(34, 197, 94, 0.1);">
                        <div style="font-size:1.2rem; font-weight:800; color:#22c55e; letter-spacing:1px; text-transform:uppercase;">
                            ✅ DECISIÓ VALIDADA
                        </div>
                        <p style="font-size:1.05rem; color:var(--body-text-color); margin:10px 0 0 0;">
                            Vas triar el camí responsable. Aquesta decisió requeria evidència, judici i un profund compromís amb el principi de <strong>Justícia i Equitat</strong>.
                        </p>
                    </div>

                    <div style="background:linear-gradient(135deg, rgba(14, 165, 233, 0.1) 0%, rgba(20, 184, 166, 0.1) 100%); border:2px solid #0ea5e9; border-radius:16px; padding:0; overflow:hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                        
                        <div style="background:#0ea5e9; padding:15px; text-align:center; color:white;">
                            <h3 style="margin:0; font-size:1.3rem; letter-spacing:1px;">🎖️ PROMOCIÓ DESBLOQUEJADA</h3>
                            <div style="font-size:0.9rem; opacity:0.9;">PUJADA DE NIVELL: DE DETECTIU A CONSTRUCTOR</div>
                        </div>

                        <div style="padding:25px;">
                            <p style="text-align:center; font-size:1.1rem; margin-bottom:20px; color:var(--body-text-color);">
                                Exposar el biaix és només la primera meitat de la missió. Ara que tens l'evidència, comença la feina real.
                                <br><strong>Estàs canviant la teva Lupa per una Clau Anglesa.</strong>
                            </p>

                            <div style="background:var(--background-fill-secondary); border-radius:12px; padding:20px; border:1px solid #bae6fd;">
                                <h4 style="margin-top:0; color:#38bdf8; text-align:center; margin-bottom:15px;">🎓 NOU ROL: ENGINYER D'EQUITAT</h4>
                                
                                <ul style="list-style:none; padding:0; margin:0; font-size:1rem; color:var(--body-text-color);">
                                    <li style="margin-bottom:12px; display:flex; gap:10px; align-items:start;">
                                        <span>🔧</span>
                                        <span><strong style="color:#38bdf8;">La Teva Tasca 1:</strong> Desmantellar les "Variables Proxy" (Eliminar el biaix de Codi Postal).</span>
                                    </li>
                                    <li style="margin-bottom:12px; display:flex; gap:10px; align-items:start;">
                                        <span>📊</span>
                                        <span><strong style="color:#38bdf8;">La Teva Tasca 2:</strong> Arreglar el "Mirall Distorsionat" redissenyant l'estratègia de dades.</span>
                                    </li>
                                    <li style="display:flex; gap:10px; align-items:start;">
                                        <span>🗺️</span>
                                        <span><strong style="color:#38bdf8;">La Teva Tasca 3:</strong> Construir un full de ruta ètic per al monitoratge continu.</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:30px;">
                        <p style="font-size:1.1rem; font-weight:600; color:var(--body-text-color);">
                            👉 La teva propera missió comença a l'<strong>Activitat 8: El Reparador d'Equitat</strong>.
                            <br>
                            <span style="font-size:0.95rem; font-weight:400; color:var(--body-text-color-subdued);"><strong>Fes scroll cap avall a la següent aplicació</strong> per concloure aquesta auditoria i començar les reparacions.</span>
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
        "q": "🚀 **Primera Oportunitat de Puntuació:** Per què multipliquem la teva Exactitud pel Progrés Ètic? (Respon correctament per guanyar el teu primer augment de Puntuació de Brúixola Moral!)",
        "o": [
            "A) Perquè la simple exactitud ignora el biaix potencial i el dany.",
            "B) Per fer les matemàtiques de la classificació més complicades.",
            "C) L'exactitud és l'única mètrica que realment importa.",
        ],
        "a": "A) Perquè la simple exactitud ignora el biaix potencial i el dany.",
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
        "q": "Detectiu, sospitem que les dades d'entrada són un 'Mirall Distorsionat' de la realitat. Per confirmar si existeix Biaix de Representació, quin és el teu objectiu forense principal?",
        "o": [
            "A) Necessito llegir les entrades del diari personal del jutge.",
            "B) Necessito comprovar si l'ordinador està endollat correctament.",
            "C) Necessito comparar les Distribucions Demogràfiques (Raça/Gènere) de les dades amb les estadístiques de població del món real.",
        ],
        "a": "C) Necessito comparar les Distribucions Demogràfiques (Raça/Gènere) de les dades amb les estadístiques de població del món real.",
        "success": "Objectiu Adquirit. Estàs preparat per entrar al Laboratori Forense de Dades.",
    },
    4: {
        "t": "t5",
        "q": "Revisió de l'Anàlisi Forense: Has marcat les dades de Gènere com un 'Buit de Dades' (només 19% Dones). Segons el teu registre d'evidències, quin és el risc tècnic específic per a aquest grup?",
        "o": [
            "A) El model tindrà un 'Punt Cec' perquè no ha vist prou exemples per aprendre patrons precisos.",
            "B) La IA apuntarà automàticament a aquest grup a causa de l'excés de vigilància històrica.",
            "C) El model utilitzarà per defecte les estadístiques del 'Món Real' per omplir els números que falten.",
        ],
        "a": "A) El model tindrà un 'Punt Cec' perquè no ha vist prou exemples per aprendre patrons precisos.",
        "success": "Evidència Bloquejada. Entens que les 'Dades que Falten' creen punts cecs, fent que les prediccions per a aquest grup siguin menys fiables.",
    },
    # --- QUESTION 4 (Evidence Report Summary) ---
    5: {
        "t": "t6",
        "q": "Detectiu, revisa la teva taula de Resum d'Evidència. Has trobat casos tant de Sobrerrepresentació (Raça) com d'Infrarrepresentació (Gènere/Edat). Quina és la teva conclusió general sobre com el Biaix de Representació afecta la IA?",
        "o": [
            "A) Confirma que el conjunt de dades és neutral, ja que les categories 'Sobre' i 'Infra' es cancel·len matemàticament entre si.",
            "B) Crea un 'Risc d'Augment de l'Error de Predicció' en AMBDUES direccions: tant si un grup s'exagera com si s'ignora, la visió de la realitat de la IA es deforma.",
            "C) Només crea risc quan falten dades (Infrarrepresentació); tenir dades extra (Sobrerrepresentació) en realitat fa que el model sigui més precís.",
        ],
        "a": "B) Crea un 'Risc d'Augment de l'Error de Predicció' en AMBDUES direccions: tant si un grup s'exagera com si s'ignora, la visió de la realitat de la IA es deforma.",
        "success": "Conclusió Verificada. Les dades distorsionades, tant si estan inflades com si falten, poden portar a una justícia distorsionada.",
    },
    6: {
        "t": "t7",
        "q": "Detectiu, estàs caçant el patró del 'Doble Estàndard'. Quina peça específica d'evidència representa aquesta Bandera Vermella?",
        "o": [
            "A) El model comet zero errors per a cap grup.",
            "B) Un grup pateix una taxa de 'Falses Alarmes' significativament més alta que un altre grup.",
            "C) Les dades d'entrada contenen més homes que dones.",
        ],
        "a": "B) Un grup pateix una taxa de 'Falses Alarmes' significativament més alta que un altre grup.",
        "success": "Patró Confirmat. Quan la taxa d'error està desequilibrada, és un Doble Estàndard.",
    },
    # --- QUESTION 6 (Race Error Gap) ---
    7: {
        "t": "t8",
        "q": "Revisa el teu registre de dades. Què va revelar l'escaneig de 'Falses Alarmes' sobre el tractament dels acusats afroamericans?",
        "o": [
            "A) Són tractats exactament igual que els acusats blancs.",
            "B) Són omesos pel sistema més sovint (Biaix de Benevolència).",
            "C) Tenen gairebé el doble de probabilitats de ser marcats erròniament com a 'Alt Risc' (Biaix Punitiu).",
        ],
        "a": "C) Tenen gairebé el doble de probabilitats de ser marcats erròniament com a 'Alt Risc' (Biaix Punitiu).",
        "success": "Evidència Registrada. El sistema està castigant persones innocents basant-se en la raça.",
    },

    # --- QUESTION 7 (Generalization & Proxy Scan) ---
    8: {
        "t": "t9",
        "q": "L'Escaneig de Geografia va mostrar una taxa d'error massiva a les Zones Urbanes. Què demostra això sobre els 'Codis Postals'?",
        "o": [
            "A) Els Codis Postals actuen com una 'Variable Proxy' per apuntar a grups específics, fins i tot si variables com la Raça s'eliminen del conjunt de dades.",
            "B) La IA és simplement dolenta llegint mapes i dades d'ubicació.",
            "C) La gent a les ciutats genera naturalment més errors informàtics que la gent a les zones rurals.",
        ],
        "a": "A) Els Codis Postals actuen com una 'Variable Proxy' per apuntar a grups específics, fins i tot si variables com la Raça s'eliminen del conjunt de dades.",
        "success": "Proxy Identificat. Amagar una variable no funciona si deixes un proxy enrere.",
    },

    # --- QUESTION 8 (Audit Summary) ---
    9: {
        "t": "t10",
        "q": "Has tancat l'expedient del cas. Quina de les següents opcions està CONFIRMADA com l''Amenaça Principal' al teu informe final?",
        "o": [
            "A) Un Doble Estàndard Racial on els acusats negres innocents són penalitzats el doble de vegades.",
            "B) Codi maliciós escrit per hackers per trencar el sistema.",
            "C) Una fallada de hardware a la sala de servidors causant errors matemàtics aleatoris.",
        ],
        "a": "A) Un Doble Estàndard Racial on els acusats negres innocents són penalitzats el doble de vegades.",
        "success": "Amenaça Avaluada. El biaix està confirmat i documentat.",
    },

    # --- QUESTION 9 (Final Verdict) ---
    10: {
        "t": "t11",
        "q": "Basant-te en les greus violacions de Justícia i Equitat trobades a la teva auditoria, quina és la teva recomanació final al tribunal?",
        "o": [
            "A) CERTIFICAR: El sistema està majoritàriament bé, els errors menors són acceptables.",
            "B) AVÍS VERMELL: Pausar el sistema per a reparacions immediatament perquè és insegur i esbiaixat.",
            "C) ADVERTÈNCIA: Utilitzar la IA només els caps de setmana quan el crim és més baix.",
        ],
        "a": "B) AVÍS VERMELL: Pausar el sistema per a reparacions immediatament perquè és insegur i esbiaixat.",
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
            "If the system isn't used on any cases, its bias can't hurt anyone yet — "
            "but once it goes live, each biased decision can scale quickly."
        )
    elif c_int < 5000:
        message = (
            f"Even at <strong>{c_int}</strong> cases per year, a biased model can quietly "
            "affect hundreds of people over time."
        )
    elif c_int < 15000:
        message = (
            f"At around <strong>{c_int}</strong> cases per year, a biased model could unfairly label "
            "thousands of people as 'high risk.'"
        )
    else:
        message = (
            f"At <strong>{c_int}</strong> cases per year, one flawed algorithm can shape the futures "
            "of an entire region — turning hidden bias into thousands of unfair decisions."
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
        return "<div class='hint-box'>Select a scenario to view details.</div>"
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
        header_title = "You're Officially on the Board!"
        summary_line = (
            "You just earned your first Moral Compass Score — you're now part of the global rankings."
        )
        cta_line = "Scroll down to take your next step and start climbing."
    elif style_key == "major":
        header_emoji = "🔥"
        header_title = "Major Moral Compass Boost!"
        summary_line = (
            "Your decision made a big impact — you just moved ahead of other participants."
        )
        cta_line = "Scroll down to take on your next challenge and keep the boost going."
    elif style_key == "climb":
        header_emoji = "🚀"
        header_title = "You're Climbing the Leaderboard"
        summary_line = "Nice work — you edged out a few other participants."
        cta_line = "Scroll down to continue your investigation and push even higher."
    elif style_key == "tight":
        header_emoji = "📊"
        header_title = "The Leaderboard Is Shifting"
        summary_line = (
            "Other teams are moving too. You'll need a few more strong decisions to stand out."
        )
        cta_line = "Take on the next question to strengthen your position."
    else:  # "solid"
        header_emoji = "✅"
        header_title = "Progress Logged"
        summary_line = "Your ethical insight increased your Moral Compass Score."
        cta_line = "Try the next scenario to break into the next tier."

    # --- SCORE / RANK LINES ---------------------------------------------

    # First-time: different wording (no previous score)
    if style_key == "first":
        score_line = f"🧭 Score: <strong>{new_score:.3f}</strong>"
        if ranks_are_int:
            rank_line = f"🏅 Initial Rank: <strong>#{new_rank}</strong>"
        else:
            rank_line = f"🏅 Initial Rank: <strong>#{new_rank}</strong>"
    else:
        score_line = (
            f"🧭 Score: {old_score:.3f} → <strong>{new_score:.3f}</strong> "
            f"(+{diff_score:.3f})"
        )

        if ranks_are_int:
            if old_rank == new_rank:
                rank_line = f"📊 Rank: <strong>#{new_rank}</strong> (holding steady)"
            elif rank_diff > 0:
                rank_line = (
                    f"📈 Rank: #{old_rank} → <strong>#{new_rank}</strong> "
                    f"(+{rank_diff} places)"
                )
            else:
                rank_line = (
                    f"🔻 Rank: #{old_rank} → <strong>#{new_rank}</strong> "
                    f"({rank_diff} places)"
                )
        else:
            rank_line = f"📊 Rank: <strong>#{new_rank}</strong>"

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
        feedback_html = f"<div class='hint-box' style='border-left:4px solid #ef4444; color:#b91c1c;'>❌ ERROR: The statement '{INCORRECT_FINDING.split(':')[0]}' is NOT a true finding. Check your lab results and try again.</div>"
    elif missed_correct:
        feedback_html = f"<div class='hint-box' style='border-left:4px solid #f97316; color:#f97316;'>⚠️ INCOMPLETE: You missed {len(missed_correct)} piece(s) of key evidence. Your final report must be complete.</div>"
    elif len(selected_biases) == len(CORRECT_FINDINGS):
        feedback_html = "<div class='hint-box' style='border-left:4px solid #22c55e; color:#16a34a;'>✅ EVIDENCE SECURED: This is a complete and accurate diagnosis of the model's systematic failure.</div>"
    else:
        feedback_html = "<div class='hint-box' style='border-left:4px solid var(--color-accent);'>Gathering evidence...</div>"

    # --- Build Markdown Report Preview ---
    if not correctly_selected:
        report_markdown = "Select the evidence cards above to start drafting your report. (The draft report will appear here.)"
    else:
        lines = []
        lines.append("### 🧾 Draft Audit Report")
        lines.append("\n**Findings of Systemic Error:**")

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
def create_bias_detective_ca_app(theme_primary_hue: str = "indigo"):
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
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>🕵️‍♀️ Authenticating...</h2>"
                "<p>Syncing Moral Compass Data...</p>"
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
                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Select Answer:",
                            elem_classes=["quiz-radio-large"],
                        )
                        feedback = gr.HTML("")
                        quiz_wiring_queue.append((i, radio, feedback))

                    # --- NAVIGATION BUTTONS ---
                    with gr.Row():
                        btn_prev = gr.Button("⬅️ Previous", visible=(i > 0))
                        next_label = (
                            "Next ▶️"
                            if i < len(MODULES) - 1
                            else "🎉 You Have Completed Part 1!! (Please Proceed to the Next Activity)"
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
                            "❌ Incorrect. Review the evidence above.</div>",
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
                "<div class='hint-box'>⚠️ Auth Failed. Please launch from the course link.</div>",
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
                    js=nav_js(prev_target_id, "Loading..."),
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
                    js=nav_js(next_target_id, "Loading..."),
                ).then(
                    fn=make_nav_generator(curr_col, next_col),
                    outputs=[curr_col, next_col],
                )

        return demo




def launch_bias_detective_ca_app(
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
    app = create_bias_detective_ca_app(theme_primary_hue=theme_primary_hue)
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

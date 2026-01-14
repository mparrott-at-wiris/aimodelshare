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
        "title": "Expediente de la misión",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">
                    <h2 class="slide-title" style="margin-bottom:25px; text-align:center; font-size: 2.2rem;">🕵️ EXPEDIENTE DE LA MISIÓN</h2>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:25px; margin-bottom:30px; align-items:stretch;">
                        <div style="background:var(--background-fill-secondary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary);">
                            <div style="margin-bottom:15px;">
                                <div style="font-size:0.9rem; font-weight:800; color:var(--body-text-color-subdued); letter-spacing:1px;">TU ROL</div>
                                <div style="font-size:1.3rem; font-weight:700; color:var(--color-accent);">Detective Principal de Sesgos</div>
                            </div>
                            <div>
                                <div style="font-size:0.9rem; font-weight:800; color:var(--body-text-color-subdued); letter-spacing:1px;">TU OBJETIVO</div>
                                <div style="font-size:1.3rem; font-weight:700;">Algoritmo de IA "Compas"</div>
                                <div style="font-size:1.0rem; margin-top:5px; opacity:0.8;">Utilizado por tribunales para decidir la libertad bajo fianza.</div>
                            </div>
                        </div>
                        <div style="background:rgba(239,68,68,0.1); padding:20px; border-radius:12px; border:2px solid #fca5a5; display:flex; flex-direction:column; justify-content:center;">
                            <div style="font-size:0.9rem; font-weight:800; color:#ef4444; letter-spacing:1px;">🚨 LA AMENAZA</div>
                            <div style="font-size:1.15rem; font-weight:600; line-height:1.4; color:var(--body-text-color);">
                                El modelo tiene un 92% de exactitud, pero sospechamos que hay un <strong style="color:#ef4444;">sesgo sistemático oculto</strong>.
                                <br><br>
                                Tu objetivo: Exponer los fallos antes de que este modelo se despliegue en todo el país.
                            </div>
                        </div>
                    </div>

                    <hr style="opacity:0.2; margin:25px 0; border-color:var(--body-text-color);">

                    <p style="text-align:center; font-weight:800; color:var(--body-text-color-subdued); margin-bottom:20px; font-size:1.0rem; letter-spacing:1px;">
                        👇 HAZ CLIC EN LAS TARJETAS PARA DESBLOQUEAR INFORMACIÓN
                    </p>

                    <div style="display:grid; gap:20px;">
                        <details class="evidence-card" style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-left: 6px solid #ef4444; padding:0; border-radius:8px; overflow:hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <summary style="padding:20px; font-weight:800; font-size:1.2rem; color:var(--body-text-color); cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; background:rgba(239,68,68,0.1);">
                                <div style="display:flex; align-items:center; gap:15px;">
                                    <span style="font-size:1.8rem;">⚠️</span>
                                    <span>RIESGO: El "efecto onda"</span>
                                </div>
                                <span style="font-size:0.9rem; color:#ef4444; text-transform:uppercase;">Haz clic para simular</span>
                            </summary>
                            <div style="padding:25px; border-top:1px solid var(--border-color-primary);">
                                <div style="display:flex; gap:30px; align-items:center;">
                                    <div style="font-size:3.5rem; line-height:1;">🌊</div>
                                    <div>
                                        <div style="font-weight:900; font-size:2.0rem; color:#ef4444; line-height:1;">15.000+</div>
                                        <div style="font-weight:700; font-size:1.1rem; color:var(--body-text-color); margin-bottom:5px;">Casos procesados por año</div>
                                        <div style="font-size:1.1rem; color:var(--body-text-color-subdued); line-height:1.5;">
                                            Un humano comete un error una vez. Esta IA repetirá el mismo sesgo <strong style="color:var(--body-text-color);">15.000+ veces al año</strong>.
                                            <br>Si no lo arreglamos, automatizaremos la injusticia a gran escala.
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </details>

                        <details class="evidence-card" style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-left: 6px solid #22c55e; padding:0; border-radius:8px; overflow:hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <summary style="padding:20px; font-weight:800; font-size:1.2rem; color:var(--body-text-color); cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; background:rgba(34,197,94,0.1);">
                                <div style="display:flex; align-items:center; gap:15px;">
                                    <span style="font-size:1.8rem;">🧭</span>
                                    <span>OBJETIVO: Cómo ganar</span>
                                </div>
                                <span style="font-size:0.9rem; color:#22c55e; text-transform:uppercase;">Haz clic para calcular</span>
                            </summary>
                            <div style="padding:25px; border-top:1px solid var(--border-color-primary);">
                                <div style="text-align:center; margin-bottom:20px;">
                                    <div style="font-size:1.4rem; font-weight:800; background:var(--background-fill-primary); border:1px solid var(--border-color-primary); padding:15px; border-radius:10px; display:inline-block; color:var(--body-text-color);">
                                        <span style="color:#6366f1;">[ Exactitud ]</span>
                                        <span style="color:var(--body-text-color-subdued); margin:0 10px;">×</span>
                                        <span style="color:#22c55e;">[ % Progreso ético ]</span>
                                        <span style="color:var(--body-text-color-subdued); margin:0 10px;">=</span>
                                        PUNTUACIÓN
                                    </div>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                                    <div style="padding:15px; background:rgba(254,226,226,0.1); border:2px solid #fecaca; border-radius:10px; text-align:center;">
                                        <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">Escenario A: Ética ignorada</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">Alta exactitud (92%)</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">0% Ética</div>
                                        <div style="margin-top:10px; border-top:1px solid #fecaca; padding-top:5px;">
                                            <div style="font-size:0.8rem; text-transform:uppercase; color:#ef4444;">Puntuación final</div>
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444;">0</div>
                                        </div>
                                    </div>
                                    <div style="padding:15px; background:rgba(220,252,231,0.1); border:2px solid #bbf7d0; border-radius:10px; text-align:center;">
                                        <div style="font-weight:700; color:#22c55e; margin-bottom:5px;">Escenario B: Detective rigoroso</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">Alta Exactitud (92%)</div>
                                        <div style="font-size:0.95rem; color:var(--body-text-color);">100% Ética</div>
                                        <div style="margin-top:10px; border-top:1px solid #bbf7d0; padding-top:5px;">
                                            <div style="font-size:0.8rem; text-transform:uppercase; color:#15803d;">Puntuación final</div>
                                            <div style="font-size:2.5rem; font-weight:900; color:#22c55e;">92</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </details>
                    </div>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 INICIO DE MISIÓN
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Responde a la siguiente pregunta para recibir tu primer <strong>aumento de Puntuación de Brújula Moral</strong>.
                            <br>Luego haz clic en <strong>Siguiente</strong> para comenzar la investigación.
                        </p>
                    </div> 
                </div>
            </div>
        """,
    },

    # --- MODULE 1: THE MAP (Mission Roadmap) ---
    {
        "id": 1,
        "title": "Hoja de ruta de la misión",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <h2 class="slide-title" style="text-align:center; margin-bottom:15px;">🗺️ HOJA DE RUTA DE LA MISIÓN</h2>

                    <p style="font-size:1.1rem; max-width:800px; margin:0 auto 25px auto; text-align:center; color:var(--body-text-color);">
                        <strong>Tu misión es clara:</strong> Descubrir el sesgo escondido dentro del 
                        sistema de IA antes de que dañe a personas reales. Si no puedes encontrar el sesgo, no podemos corregirlo.
                    </p>

                    <div class="ai-risk-container" style="background:transparent; border:none; padding:0;">

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">

                            <div style="border: 3px solid #3b82f6; background: rgba(59, 130, 246, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#3b82f6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PASO 1: REGLAS</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">📜</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#3b82f6; margin-bottom:5px;">Establecer las reglas</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Define el estándar ético: <strong>Justicia y Equidad</strong>. ¿Qué se considera exactamente sesgo en esta investigación?
                                </div>
                            </div>

                            <div style="border: 3px solid #14b8a6; background: rgba(20, 184, 166, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#14b8a6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PASO 2: EVIDENCIAS EN LOS DATOS</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">🔍</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#14b8a6; margin-bottom:5px;">Análisis forense de los datos de entrada</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Escanea los <strong>datos de entrada</strong> para detectar injusticias históricas, brechas de representación y sesgos de exclusión.
                                </div>
                            </div>

                            <div style="border: 3px solid #8b5cf6; background: rgba(139, 92, 246, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#8b5cf6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PASO 3: PRUEBAS DE ERROR</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">🎯</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#8b5cf6; margin-bottom:5px;">Pruebas de errores de salida</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Pon a prueba las predicciones del modelo. Demuestra que los errores (falsas alarmas) son <strong>desiguales</strong> entre grupos.
                                </div>
                            </div>

                            <div style="border: 3px solid #f97316; background: rgba(249, 115, 22, 0.1); border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                <div style="position:absolute; top:-15px; left:15px; background:#f97316; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">PASO 4: INFORME DE IMPACTO</div>
                                <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">⚖️</div>
                                <div style="font-weight:800; font-size:1.2rem; color:#f97316; margin-bottom:5px;">Informe final</div>
                                <div style="font-size:1.0rem; color:var(--body-text-color); font-weight:500; line-height:1.4;">
                                    Diagnostica el daño sistemático y emite tu recomendación final al tribunal: <strong>desplegar el sistema de IA o pausar para reparar.</strong>
                                </div>
                            </div>

                        </div>
                    </div>


                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 CONTINUAR MISIÓN
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Responde a la siguiente pregunta para recibir tu próximo <strong>aumento de Puntuación de Brújula Moral</strong>.
                            <br>Luego haz clic en <strong>Siguiente</strong> para continuar la investigación.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },

    # --- MODULE 2: RULES (Interactive) ---
    {
        "id": 2,
        "title": "Paso 1: Aprender las Reglas",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step active">1. REGLAS</div>
                    <div class="tracker-step">2. EVIDENCIAS</div>
                    <div class="tracker-step">3. ERRORES</div>
                    <div class="tracker-step">4. VEREDICTO</div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h2 class="slide-title" style="margin:0;">PASO 1: APRENDE LAS REGLAS</h2>
                    <div style="font-size:2rem;">⚖️</div>
                </div>

                <div class="slide-body">

                    <div style="background:rgba(59, 130, 246, 0.1); border-left:4px solid #3b82f6; padding:15px; margin-bottom:20px; border-radius:4px; color: var(--body-text-color);">
                        <p style="margin:0; font-size:1.05rem; line-height:1.5;">
                            <strong style="color:var(--color-accent);">Justicia y Equidad: Tu regla principal.</strong><br>
                            La ética guía nuestras acciones. Seguimos el asesoramiento experto del Observatorio de Ética en Inteligencia Artificial de Cataluña <strong>OEIAC (UdG)</strong> para asegurar que los sistemas de IA sean justos.
                            De sus siete principios clave para una IA segura, este caso se centra en una posible vulneración de la <strong>Justicia y Equidad</strong>.
                        </p>
                    </div>

                    <div style="text-align:center; margin-bottom:20px;">
                        <p style="font-size:1rem; font-weight:700; color:var(--color-accent); background:rgba(59, 130, 246, 0.1); display:inline-block; padding:6px 16px; border-radius:20px; border:1px solid var(--border-color-primary);">
                            👇 Haz clic en cada tarjeta para revelar qué se considera sesgo
                        </p>
                    </div>

                    <p style="text-align:center; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:10px; font-size:0.9rem; letter-spacing:1px;">
                        🧩 JUSTICIA Y EQUIDAD: ¿QUÉ SE CONSIDERA SESGO?
                    </p>

                    <div class="ai-risk-container" style="background:transparent; border:none; padding:0;">
                        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:15px;">

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #3b82f6; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#3b82f6; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">📊</div>
                                    Sesgo de Representación
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Qué comprueba:</strong> si el conjunto de datos refleja a la población real.
                                    <br><br>
                                    Si un grupo aparece mucho más o mucho menos de lo que corresponde a la realidad (p. ej. solo el 10% de los casos son del Grupo A, pero son el 71% de la población), la IA probablemente aprenderá patrones sesgados.
                                </div>
                            </details>

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #ef4444; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#ef4444; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">🎯</div>
                                    Brechas de error
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Qué comprueba:</strong> si la IA comete más errores con un grupo que con otro.
                                    <br><br>
                                    Tasas de error más altas para un grupo (como las falsas alarmas) indican que el modelo puede ser menos justo o fiable para ese grupo.
                                </div>
                            </details>

                            <details style="cursor:pointer; background:var(--background-fill-secondary); padding:15px; border-radius:10px; border:1px solid #22c55e; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#22c55e; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">⛓️</div>
                                    Desigualdades en los resultados
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); border-top:1px solid var(--border-color-primary); padding-top:10px; line-height:1.4;">
                                    <strong>Qué comprueba:</strong> Si las decisiones de la IA provocan peores resultados en el mundo real para ciertos grupos (por ejemplo, sentencias más duras).
                                    <br><br>
                                    El sesgo no es solo una cuestión de datos: afecta a la vida de las personas.
                                </div>
                            </details>
                        </div>
                    </div>

                    <hr style="opacity:0.2; margin:25px 0; border-color:var(--body-text-color);">

                    <details class="hint-box" style="margin-top:0; cursor:pointer;">
                        <summary style="font-weight:700; color:var(--body-text-color-subdued);">🧭 Referencia: Otros principios de ética en IA (OEIAC)</summary>
                        <div style="margin-top:15px; font-size:0.9rem; display:grid; grid-template-columns: 1fr 1fr; gap:15px; color:var(--body-text-color);">
                            <div>
                                <strong>Transparencia y explicabilidad</strong><br>Asegurar que el razonamiento de la IA y el juicio final sean claros para que las decisiones puedan ser inspeccionadas y las personas puedan apelar.<br>
                                <strong>Seguridad y no maleficencia</strong><br>Minimizar los errores dañinos y tener siempre un plan sólido para fallos del sistema.<br>
                                <strong>Responsabilidad y rendición de Cuentas</strong><br>Asignar propietarios claros para la IA y mantener un registro detallado de las decisiones (rastro de auditoría).
                            </div>
                            <div>
                                <strong>Autonomía</strong><br>Proporcionar a los individuos procesos claros de apelación y alternativas a la decisión de la IA.<br>
                                <strong>Privacidad</strong><br>Utilizar solo los datos necesarios y justificar siempre cualquier necesidad de usar atributos sensibles.<br>
                                <strong>Sostenibilidad</strong><br>Evitar daños a largo plazo a la sociedad o al medio ambiente (p. ej. uso masivo de energía o desestabilización del mercado).
                            </div>
                        </div>
                    </details>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 SESIÓN INFORMATIVA DE REGLAS COMPLETADA: CONTINUAR MISIÓN
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Responde a la siguiente pregunta para recibir tu próximo <strong>aumento de Puntuación de Brújula Moral</strong>.
                            <br>Luego haz clic en <strong>Siguiente</strong> para continuar tu misión.
                        </p>
                    </div>
                </div>
            </div>
        """
    },

    {
        "id": 3,
        "title": "Paso 2: Reconocimiento de patrones",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLAS</div>
                    <div class="tracker-step active">2. EVIDENCIAS</div>
                    <div class="tracker-step">3. ERRORES</div>
                    <div class="tracker-step">4. VEREDICTO</div>
                </div>

        <div class="slide-body">
            <h2 class="slide-title" style="margin:0;">PASO 2: BUSCA EVIDENCIAS</h2>

            <div style="text-align:center; margin-bottom:20px;">

                <h2 class="slide-title header-accent" style="margin-top:10px;">A la búsqueda de patrones demográficos sesgados</h2>
                <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                    Los sistemas de IA aprenden a partir de los datos. Si los datos están sesgados, el sistema también lo estará.
                    <br>La primera tarea es identificar el <strong>sesgo de representación</strong> comprobando qué <strong>grupos demográficos</strong>aparecen con mayor o menor frecuencia en los datos.
                </p>
            </div>

            <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:16px; padding:25px; margin-bottom:20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px;">
                    <div style="font-size:1.5rem;">🚩</div>
                    <div>
                        <strong style="color:#0ea5e9; font-size:1.1rem; text-transform:uppercase; letter-spacing:1px;">PATRÓN: "EL ESPEJO DISTORSIONADO"</strong>
                        <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">(Sesgo de representación en grupos protegidos)</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
                    
                    <div style="color: var(--body-text-color);">
                        <p style="font-size:1rem; line-height:1.6;">
                            <strong>El concepto del espejo:</strong> Idealmente, un conjunto de datos debería ser un "espejo" de la población real. 
                            Si un grupo constituye el 50% de la población, debería aparecer en una proporción similar en los datos.
                        </p>
                        <p style="font-size:1rem; line-height:1.6;">
                            <strong>Señal de alerta:</strong> Busca <strong>grandes desequilibrios</strong> en características protegidas como el origen étnico, el género o la edad.
                        </p>
                        <ul style="font-size:0.95rem; color:var(--body-text-color-subdued); margin-top:10px; padding-left:20px; line-height:1.5;">
                            <li><strong>Sobrerrepresentación:</strong> Un grupo domina los datos (ej. el 80% de los registros de arresto son de hombres). El sistema de IA puede acabar tratando a este grupo de forma injusta.</li>
                            <li><strong>Infrarrepresentación:</strong> Un grupo es muy pequeño o no aparece. El sistema no puede aprender patrones fiables para ese grupo.</li>
                        </ul>
                    </div>

                    <div style="background:var(--background-fill-primary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary); display:flex; flex-direction:column; justify-content:center;">
                        
                        <div style="margin-bottom:20px;">
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:5px;">REALIDAD (la población)</div>
                            <div style="display:flex; width:100%; height:24px; border-radius:4px; overflow:hidden;">
                                <div style="width:33%; background:#94a3b8; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grupo A</div>
                                <div style="width:34%; background:#64748b; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grupo B</div>
                                <div style="width:33%; background:#475569; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Grupo C</div>
                            </div>
                        </div>

                        <div>
                            <div style="font-size:0.85rem; font-weight:700; color:#0ea5e9; margin-bottom:5px;">LOS DATOS DE ENTRENAMIENTO (El espejo distorsionado)</div>
                            <div style="display:flex; width:100%; height:24px; border-radius:4px; overflow:hidden;">
                                <div style="width:80%; background:linear-gradient(90deg, #f43f5e, #be123c); display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem; font-weight:700;">GRUPO A (80%)</div>
                                <div style="width:10%; background:#cbd5e1;"></div>
                                <div style="width:10%; background:#94a3b8;"></div>
                            </div>
                            <div style="font-size:0.8rem; color:#ef4444; margin-top:5px; font-weight:600;">
                                ⚠️ Alerta: El Grupo A está masivamente sobrerrepresentado.
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <div style="margin-bottom: 25px; padding: 0 10px;">
                <p style="font-size:1.1rem; line-height:1.5; color:var(--body-text-color);">
                    <strong>🕵️ El siguiente paso:</strong> Revisa los datos demográficos en el laboratorio de análisis forense de datos. Si ves un "espejo distorsionado", los datos probablemente estén sesgados.
                </p>
            </div>

            <details style="margin-bottom:30px; cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; padding:12px;">
                <summary style="font-weight:700; color:var(--body-text-color-subdued); font-size:0.95rem;">🧭 Referencia: ¿Cómo se sesgan los conjuntos de datos de IA?</summary>
                <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color-subdued); line-height:1.5; padding:0 5px;">
                    <p style="margin-bottom:10px;"><strong>Ejemplo:</strong> Cuando un conjunto de datos se construye a partir de <strong>registros históricos de arrestos</strong>.</p>
                    <p>El exceso de vigilancia policial sistémico en barrios específicos podría distorsionar los recuentos en el conjunto de datos para atributos como <strong>origen étnico o ingresos</strong>.
                     La IA entonces aprende esta distorsión como "verdad".</p>
                </div>
            </details>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 PATRONES DE EVIDENCIA ESTABLECIDOS: CONTINUAR MISIÓN
                </p>
                <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                    Responde a la siguiente pregunta para recibir tu próximo <strong>aumento de Puntuación de Brújula Moral</strong>.
                    <br>Luego haz clic en <strong>Siguiente</strong> para comenzar a <strong>analizar la evidencia en el Laboratorio Forense de Datos.</strong>
                </p>
            </div>
        </div>
    </div>
    """
    },

    # --- MODULE 4: DATA FORENSICS LAB (The Action) ---
    {
        "id": 4, 
        "title": "Paso 2: Laboratorio forense de datos",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLAS</div>
                    <div class="tracker-step active">2. EVIDENCIAS</div>
                    <div class="tracker-step">3. ERRORES</div>
                    <div class="tracker-step">4. VEREDICTO</div>
                </div>

           <h2 class="slide-title" style="margin:0;">PASO 2: BUSCA EVIDENCIAS</h2>

            <div style="text-align:center; margin-bottom:20px;">

                <h2 class="slide-title header-accent" style="margin-top:10px;">El laboratorio forense de datos</h2>                
                <div class="slide-body">

                    <p style="text-align:center; max-width:700px; margin:0 auto 15px auto; font-size:1.1rem; color:var(--body-text-color);">
                        Busca evidencias de sesgo de representación.
                        Compara la población del <strong>mundo real</strong> con los datos de <strong>entrada</strong> del sistema de IA.
                        <br>¿La IA "ve" el mundo tal como es realmente o ves evidencia de representación distorsionada?
                    </p>

                <div style="text-align:center; margin-bottom:20px;">
                    <p style="font-size:1rem; font-weight:700; color:var(--color-accent); background:rgba(59, 130, 246, 0.1); display:inline-block; padding:6px 16px; border-radius:20px; border:1px solid var(--border-color-primary);">
                        👇 Haz clic para escanear cada categoría demográfica y revelar evidencias
                    </p>
               </div>

                    <div style="margin-top:20px;">
                        <input type="radio" id="scan-race" name="scan-tabs" class="scan-radio" checked>
                        <input type="radio" id="scan-gender" name="scan-tabs" class="scan-radio">
                        <input type="radio" id="scan-age" name="scan-tabs" class="scan-radio">

                        <div class="forensic-tabs" style="display:flex; justify-content:center; gap:10px; margin-bottom:0;">
                            <label for="scan-race" class="tab-label-styled" style="flex:1; text-align:center;">ESCANEAR: ETNIA</label>
                            <label for="scan-gender" class="tab-label-styled" style="flex:1; text-align:center;">ESCANEAR: GÉNERO</label>
                            <label for="scan-age" class="tab-label-styled" style="flex:1; text-align:center;">ESCANEAR: EDAD</label>
                        </div>

                        <div class="scan-content" style="border-top: 3px solid var(--color-accent);">

                            <div class="scan-pane pane-race">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">ESCANEANDO: DISTRIBUCIÓN ÉTNICA</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ ANOMALÍA DETECTADA</span>
                                </div>

                                <div style="display:grid; grid-template-columns: 1fr 0.2fr 1fr; align-items:center; gap:10px;">

                                    <div style="text-align:center; background:var(--background-fill-secondary); padding:15px; border-radius:8px; border:1px solid var(--border-color-primary);">
                                        <div style="font-size:0.9rem; font-weight:700; color:var(--body-text-color-subdued); letter-spacing:1px;">MUNDO REAL</div>
                                        <div style="font-size:2rem; font-weight:900; color:#3b82f6; margin:5px 0;">28%</div>
                                        <div style="font-size:0.9rem; margin-bottom:10px; color: var(--body-text-color);">Población afroamericana</div>
                                        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; max-width:80px; margin:0 auto;">
                                            <span style="color:#3b82f6;">●</span><span style="color:#3b82f6;">●</span><span style="color:#3b82f6;">●</span><span style="color:var(--border-color-primary);">●</span>
                                            <span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span>
                                            <span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span><span style="color:var(--border-color-primary);">●</span>
                                        </div>
                                    </div>

                                    <div style="text-align:center; font-size:1.5rem; color:var(--body-text-color-subdued);">👉</div>

                                    <div style="text-align:center; background:rgba(239, 68, 68, 0.1); padding:15px; border-radius:8px; border:2px solid #ef4444;">
                                        <div style="font-size:0.9rem; font-weight:700; color:#ef4444; letter-spacing:1px;">DATOS DE ENTRADA</div>
                                        <div style="font-size:2rem; font-weight:900; color:#ef4444; margin:5px 0;">51%</div>
                                        <div style="font-size:0.9rem; margin-bottom:10px; color: var(--body-text-color);">Registros de afroamericanos</div>
                                        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; max-width:80px; margin:0 auto;">
                                            <span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span>
                                            <span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span>
                                            <span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span><span style="color:rgba(239, 68, 68, 0.3);">●</span>
                                        </div>
                                    </div>

                                </div>

                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:var(--background-fill-secondary);">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDENCIA REGISTRADA: Sesgo de representación por origen étnico</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        El sistema de IA ve a este grupo con mucha más frecuencia en los datos de lo que corresponde a la población real (51 % frente a 28 %). Esto puede llevar al modelo a asociar “alto riesgo” con personas de este grupo simplemente porque aparecen más en los registros históricos de arrestos.
                                    </div>
                                </div>
                            </div>

                            <div class="scan-pane pane-gender">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">ESCANEANDO: EQUILIBRIO DE GÉNERO</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ FALTA DE DATOS ENCONTRADA</span>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                                    <div style="text-align:center; padding:20px; background:var(--background-fill-secondary); border-radius:8px; border:1px solid var(--border-color-primary);">
                                        <div style="font-size:4rem; line-height:1;">♂️</div>
                                        <div style="font-size:2.2rem; font-weight:900; color:#3b82f6;">81%</div>
                                        <div style="font-weight:700; color:var(--body-text-color-subdued);">HOMBRES</div>
                                        <div style="font-size:0.85rem; color:#16a34a; font-weight:600; margin-top:5px;">✅ Bien representados</div>
                                    </div>
                                    <div style="text-align:center; padding:20px; background:rgba(225, 29, 72, 0.1); border-radius:8px; border:2px solid #fda4af;">
                                        <div style="font-size:4rem; line-height:1; opacity:0.5;">♀️</div>
                                        <div style="font-size:2.2rem; font-weight:900; color:#e11d48;">19%</div>
                                        <div style="font-weight:700; color:#fb7185;">MUJERES</div>
                                        <div style="font-size:0.85rem; color:#e11d48; font-weight:600; margin-top:5px;">⚠️ Datos insuficientes</div>
                                    </div>
                                </div>
                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:var(--background-fill-secondary);">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDENCIA REGISTRADA: Sesgo de representación de género</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        Las mujeres son una clase minoritaria en este conjunto de datos, a pesar de representar aproximadamente el 50 % de la población real. El modelo probablemente tendrá dificultades para aprender patrones fiables para este grupo, lo que dará lugar a **tasas de error más altass** en las predicciones sobre mujeres detenidas.
                                    </div>
                                </div>
                            </div>

                            <div class="scan-pane pane-age">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">ESCANEANDO: DISTRIBUCIÓN DE EDAD</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ PICO DE DISTRIBUCIÓN</span>
                                </div>

                                <div style="padding:20px; background:var(--background-fill-secondary); border-radius:8px; border:1px solid var(--border-color-primary); height:200px; display:flex; align-items:flex-end; justify-content:space-around;">

                                    <div style="width:20%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:var(--body-text-color-subdued); margin-bottom:5px;">Bajo</div>
                                        <div style="height:60px; background:var(--border-color-primary); border-radius:4px 4px 0 0; width:100%;"></div>
                                        <div style="margin-top:10px; font-size:0.85rem; font-weight:700; color: var(--body-text-color);">Jóvenes (<25)</div>
                                    </div>

                                    <div style="width:35%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">ALTO</div>
                                        <div style="height:120px; background:#ef4444; border-radius:4px 4px 0 0; width:100%; box-shadow:0 4px 10px rgba(239,68,68,0.3);"></div>
                                        <div style="margin-top:10px; font-size:0.9rem; font-weight:800; color:#ef4444;">25-45 (BURBUJA)</div>
                                    </div>

                                    <div style="width:20%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:var(--body-text-color-subdued); margin-bottom:5px;">Bajo</div>
                                        <div style="height:50px; background:var(--border-color-primary); border-radius:4px 4px 0 0; width:100%;"></div>
                                        <div style="margin-top:10px; font-size:0.85rem; font-weight:700; color: var(--body-text-color);">Mayores (>45)</div>
                                    </div>

                                </div>

                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:var(--background-fill-secondary);">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDENCIA REGISTRADA: Sesgo de representación de edad</div>
                                    <div style="font-size:0.95rem; margin-top:5px; color: var(--body-text-color);">
                                        Los datos están concentrados principalmente en personas de 25 a 45 años, la “burbuja de edad.” El modelo tiene un **punto ciego** con los más jóvenes y los mayores, por lo que sus predicciones para estos grupos probablemente no serán fiables (error de generalización).
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 EVIDENCIA DE SESGO DE REPRESENTACIÓN ESTABLECIDA: CONTINUAR MISIÓN
                </p>
                <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                    Responde a la siguiente pregunta para recibir tu próximo <strong>aumento de Puntuación de Brújula Moral</strong>.
                    <br>Luego haz clic en <strong>Siguiente</strong> para <strong>resumir los hallazgos del laboratorio forense de datos.</strong>
                </p>
            </div>

                </div>
            </div>
        """,
    },

    # --- MODULE 4: EVIDENCE REPORT (Input Flaws) ---
    {
        "id":5,
        "title": "Informe de evidencia: Fallos de Entrada",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">✓ REGLAS</div>
                    <div class="tracker-step completed">✓ EVIDENCIAS</div>
                    <div class="tracker-step active">3. ERRORES</div>
                    <div class="tracker-step">4. VEREDICTO</div>
                </div>
                <h2 class="slide-title" style="font-size:1.6rem; text-align:center; margin-bottom:15px;">Informe forense de datos: fallos de entrada</h2>
                <div class="ai-risk-container" style="border: 2px solid #ef4444; background: rgba(239,68,68,0.05); padding: 20px;">
                    <h4 style="margin-top:0; font-size:1.2rem; color:#b91c1c; text-align:center;">📋 RESUMEN DE EVIDENCIAS</h4>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                        <thead>
                            <tr style="background: rgba(239,68,68,0.1); border-bottom: 2px solid #ef4444;">
                                <th style="padding: 8px; text-align: left;">SECTOR</th>
                                <th style="padding: 8px; text-align: left;">HALLAZGO</th>
                                <th style="padding: 8px; text-align: left;">IMPACTO</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style="border-bottom: 1px solid var(--border-color-primary);">
                                <td style="padding: 8px; font-weight:700;">Etnia</td>
                                <td style="padding: 8px;">Sobrerrepresentada (51%)</td>
                                <td style="padding: 8px; color:#b91c1c;">Riesgo de aumento de error de predicción</td>
                            </tr>
                            <tr style="border-bottom: 1px solid var(--border-color-primary);">
                                <td style="padding: 8px; font-weight:700;">Género</td>
                                <td style="padding: 8px;">Infrarrepresentado (19%)</td>
                                <td style="padding: 8px; color:#b91c1c;">Riesgo de aumento de error de predicción</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight:700;">Edad</td>
                                <td style="padding: 8px;">Grupos Excluidos (Menos de 25/Más de 45)</td>
                                <td style="padding: 8px; color:#b91c1c;">Riesgo de aumento de error de predicción</td>
                            </tr>
                        </tbody>
                    </table>
                </div>


                <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 SIGUIENTE: INVESTIGAR ERRORES EN SALIDAS - CONTINUAR MISIÓN
                </p>
                <p style="font-size:1.05rem; margin:0;">
                    Responde a la siguiente pregunta para recibir tu próximo <strong>aumento de Puntuación de Brújula Moral</strong>.
                    <br>Haz clic en <strong>Siguiente</strong> para proceder al **Paso 3** para encontrar pruebas de daños reales: **Las Brechas de Error**.
                </p>
            </div>
                </div>
            </div>
        """
    },

# --- MODULE 5: INTRO TO PREDICTION ERROR ---
    {
        "id": 6,
        "title": "Parte II: Paso 3 — Demostrando el Error de Predicción",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLAS</div>
                    <div class="tracker-step completed">2. EVIDENCIA</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VEREDICTO</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PASO 3: EVALUAR ERRORES</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">En busca de errores de predicción</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Hemos encontrado evidencias de que los datos de entrada están sesgados. Ahora debemos investigar si este sesgo ha influido en las <strong>decisiones del modelo</strong>.
                            <br>Buscamos la segunda señal de alerta del manual: las <strong>brechas de error</strong>.
                        </p>
                    </div>

                    <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:16px; padding:25px; margin-bottom:25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                        
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px;">
                            <div style="font-size:1.5rem;">🚩</div>
                            <div>
                                <strong style="color:#f43f5e; font-size:1.1rem; text-transform:uppercase; letter-spacing:1px;">PATRÓN: "EL DOBLE RASERO"</strong>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">(Impacto desigual de los errores)</div>
                            </div>
                        </div>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
                            
                            <div>
                                <p style="font-size:1rem; line-height:1.6; margin-top:0; color:var(--body-text-color);">
                                    <strong>El concepto:</strong> El “doble rasero” significa que los errores del sistema de IA afectan a unas personas más que a otras, causando daños reales.
                                </p>

                                <div style="margin-top:15px; margin-bottom:15px;">
                                    <div style="background:rgba(255, 241, 242, 0.1); padding:12px; border-radius:8px; border:1px solid #fda4af; margin-bottom:10px;">
                                        <div style="font-weight:700; color:#fb7185; margin-bottom:4px; font-size:0.95rem;">⚠️ TIPO 1: FALSAS ALARMAS (falsos positivos)</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); line-height:1.4;">Clasificar a una persona de bajo riesgo como de <strong>Alto Riesgo</strong>.</div>
                                        <div style="font-size:0.85rem; font-weight:700; color:#f43f5e; margin-top:4px;">Daño: Detención injusta.</div>
                                    </div>

                                    <div style="background:rgba(240, 249, 255, 0.1); padding:12px; border-radius:8px; border:1px solid #bae6fd;">
                                        <div style="font-weight:700; color:#38bdf8; margin-bottom:4px; font-size:0.95rem;">⚠️ TIPO 2: ALERTAS NO DETECTADAS (falsos negativos)</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); line-height:1.4;">Clasificar a una persona de alto riesgo como de <strong>Bajo Riesgo</strong>.</div>
                                        <div style="font-size:0.85rem; font-weight:700; color:#0ea5e9; margin-top:4px;">Daño: Riesgo para la seguridad pública.</div>
                                    </div>
                                </div>

                                <div style="background:rgba(255, 241, 242, 0.1); color:var(--body-text-color); padding:10px; border-radius:6px; font-size:0.9rem; border-left:4px solid #db2777; margin-top:15px;">
                                    <strong>Pista clave:</strong> Busca una brecha significativa en la <strong>tasa de falsas alarmas</strong>. Si el Grupo A es señalado incorrectamente mucho más que el Grupo B, existe una brecha de error.
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary); display:flex; flex-direction:column; justify-content:center;">
                                
                                <div style="text-align:center; margin-bottom:10px; font-weight:700; color:var(--body-text-color); font-size:0.9rem;">
                                    "FALSAS ALARMAS" (Personas inocentes clasificadas como de riesgo)
                                </div>

                                <div style="margin-bottom:15px;">
                                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:700; color:#ec4899; margin-bottom:4px;">
                                        <span>GRUPO A (Objetivo)</span>
                                        <span>60% ERROR</span>
                                    </div>
                                    <div style="width:100%; background:var(--border-color-primary); height:12px; border-radius:10px; overflow:hidden;">
                                        <div style="width:60%; background:#db2777; height:100%;"></div>
                                    </div>
                                </div>

                                <div>
                                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:4px;">
                                        <span>GRUPO B (Referencia)</span>
                                        <span>30% ERROR</span>
                                    </div>
                                    <div style="width:100%; background:var(--border-color-primary); height:12px; border-radius:10px; overflow:hidden;">
                                        <div style="width:30%; background:#94a3b8; height:100%;"></div>
                                    </div>
                                </div>

                                <div style="text-align:center; margin-top:15px; font-size:0.85rem; color:#db2777; font-weight:700; background:rgba(255, 241, 242, 0.1); padding:5px; border-radius:4px;">
                                    ⚠️ BRECHA DETECTADA: +30 puntos porcentuales de diferencia
                                </div>

                            </div>
                        </div>
                    </div>

                    <details style="margin-bottom:25px; cursor:pointer; background:rgba(255, 241, 242, 0.1); border:1px solid #fda4af; border-radius:8px; padding:12px;">
                        <summary style="font-weight:700; color:#fb7185; font-size:0.95rem;">🔬 Cómo el sesgo de representación provoca errores de predicción</summary>
                        <div style="margin-top:12px; font-size:0.95rem; color:var(--body-text-color); line-height:1.5; padding:0 5px;">
                            <p style="margin-bottom:10px;"><strong>Conecta los puntos:</strong> En el Paso 2, detectamos que los datos de entrada sobrerepresentaban a determinados grupos.</p>
                            <p><strong>La Teoría:</strong> Como la IA veía estos grupos más a menudo en los registros de arresto, la estructura de los datos puede llevar al modelo a cometer errores de predicción específicos para grupos. El modelo puede generar más <strong>Falsas Alarmas</strong> para personas inocentes de estos grupos a una tasa mucho más alta.</p>
                        </div>
                    </details>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p class="text-danger-adaptive" style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#f43f5e;">
                            🚀 PATRÓN DE ERROR ESTABLECIDO: CONTINUAR MISIÓN
                        </p>
                        <p class="text-body-danger-adaptive" style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Responde a la siguiente pregunta para confirmar tu objetivo.
                            <br>Luego haz clic en <strong>Siguiente</strong> para abrir el <strong>Laboratorio de Error de Predicción</strong> y probar las Tasas de Falsas Alarmas.
                        </p>
                    </div>

                </div>
            </div>
        """
    },

    # --- MODULE 6: RACE ERROR GAP LAB ---
    {
        "id": 7,
        "title": "Paso 3: Laboratorio de Brecha de Error Racial",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLAS</div>
                    <div class="tracker-step completed">2. EVIDENCIAS</div>
                    <div class="tracker-step active">3. ERRORES</div>
                    <div class="tracker-step">4. VEREDICTO</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PASO 3: EVALUAR ERRORES</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">El laboratorio de errores de predicción - Análisis por origen étnico</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Sospechábamos que el modelo podía generar errores desiguales entre grupos. Ahora, lo analizaremos.
                            <br>Haz clic para revelar las tasas de error a continuación. ¿Los errores de la IA afectan por igual a personas detenidas blancas y afroamericanas?
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom:25px;">
                        
                        <div class="ai-risk-container" style="padding:0; border:2px solid #ef4444; overflow:hidden; border-radius:12px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.1); background:transparent;">
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af;">
                                <h3 style="margin:0; font-size:1.25rem; color:#ef4444;">📡 ESCANEO 1: FALSAS ALARMAS</h3>
                                <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(Personas inocentes marcadas erróneamente como de "Alto Riesgo")</p>
                            </div>
                            
                            <details style="cursor:pointer; background:var(--background-fill-secondary);">
                                <summary style="list-style:none; padding:20px; font-weight:800; text-align:center; color:#ef4444; font-size:1.1rem; transition:background 0.2s;">
                                    👇 HAZ CLIC PARA REVELAR DATOS
                                </summary>
                                <div style="padding:0 20px 25px 20px; text-align:center; border-top:1px solid var(--border-color-primary);">
                                    
                                    <div style="display:flex; justify-content:center; gap:30px; margin-bottom:20px;">
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444; line-height:1;">45%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-top:5px;">AFROAMERICANO</div>
                                        </div>
                                        <div style="width:1px; background:var(--border-color-primary);"></div>
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#3b82f6; line-height:1;">23%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-top:5px;">BLANCO</div>
                                        </div>
                                    </div>

                                    <div class="hint-box" style="border-left:4px solid #ef4444; background:rgba(239, 68, 68, 0.1); text-align:left;">
                                        <div style="font-weight:800; color:#ef4444; font-size:0.95rem;">❌ VEREDICTO: SESGO PUNITIVO</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); margin-top:3px;">
                                            Las personas detenidas afroamericanas tienen casi <strong style="color:#ef4444;">el doble de probabilidades</strong> de ser clasificadas erróneamente como peligrosos en comparación con las personas blancas detenidas.
                                        </div>
                                    </div>

                                </div>
                            </details>
                        </div>

                        <div class="ai-risk-container" style="padding:0; border:2px solid #3b82f6; overflow:hidden; border-radius:12px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1); background:transparent;">
                            <div style="background:rgba(59, 130, 246, 0.1); padding:15px; text-align:center; border-bottom:1px solid #bfdbfe;">
                                <h3 style="margin:0; font-size:1.25rem; color:#3b82f6;">📡 ESCANEO 2: ADVERTENCIAS OMITIDAS</h3>
                                <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(Personas que reinciden clasificadas erróneamente como "seguras")</p>
                            </div>
                            
                            <details style="cursor:pointer; background:var(--background-fill-secondary);">
                                <summary style="list-style:none; padding:20px; font-weight:800; text-align:center; color:#3b82f6; font-size:1.1rem; transition:background 0.2s;">
                                    👇 HAZ CLIC PARA REVELAR DATOS
                                </summary>
                                <div style="padding:0 20px 25px 20px; text-align:center; border-top:1px solid var(--border-color-primary);">
                                    
                                    <div style="display:flex; justify-content:center; gap:30px; margin-bottom:20px;">
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444; line-height:1;">28%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-top:5px;">AFROAMERICANO</div>
                                        </div>
                                        <div style="width:1px; background:var(--border-color-primary);"></div>
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#3b82f6; line-height:1;">48%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color-subdued); margin-top:5px;">BLANCO</div>
                                        </div>
                                    </div>

                                    <div class="hint-box" style="border-left:4px solid #3b82f6; background:rgba(59, 130, 246, 0.1); text-align:left;">
                                        <div style="font-weight:800; color:#3b82f6; font-size:0.95rem;">❌ VEREDICTO: SESGO DE INDULGENCIA</div>
                                        <div style="font-size:0.9rem; color:var(--body-text-color); margin-top:3px;">
                                            Las personas blancas que reinciden tienen muchas más probabilidades de no ser detectadas por el sistema.
                                        </div>
                                    </div>

                                </div>
                            </details>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:20px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#ef4444;">
                            🚀 BRECHA DE ERROR POR ORIGEN ÉTNICO CONFIRMADA
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Hemos demostrado que el modelo tiene un "Doble rasero" por origen étnico. 
                            <br>Responde a la siguiente pregunta para certificar tus hallazgos, luego procede al <strong>Paso 4: Analizar Brechas de Error por Género, Edad y Geografía.</strong>
                        </p>
                    </div>

                </div>
            </div>
        """
    },

    # --- MODULE 7: GENERALIZATION & PROXY SCAN ---
    {
        "id": 8,
        "title": "Paso 3: Laboratorio de Escaneo de Generalización",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLAS</div>
                    <div class="tracker-step completed">2. EVIDENCIAS</div>
                    <div class="tracker-step active">3. ERRORES</div>
                    <div class="tracker-step">4. VEREDICTO</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PASO 3: EVALUAR ERRORES</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">El laboratorio de errores de predicción - Género, edad y geografía</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Hemos revelado la brecha de error por origen étnico. Pero el sesgo se esconde también en otros lugares.
                            <br>Utiliza el escáner a continuación para comprobar <strong>errores de representación</strong> de género y edad (debidos a la falta de datos) y <strong>sesgo proxy</strong> (cuando datos aparentemente neutros sustituyen información sensible y generan resultados injustos).
                        </p>
                    </div>

                    <div style="margin-top:20px;">
                        <input type="radio" id="scan-gender-err" name="error-tabs" class="scan-radio" checked>
                        <input type="radio" id="scan-age-err" name="error-tabs" class="scan-radio">
                        <input type="radio" id="scan-geo-err" name="error-tabs" class="scan-radio">

                        <div class="forensic-tabs" style="display:flex; justify-content:center; gap:10px; margin-bottom:0;">
                            <label for="scan-gender-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCANEAR: GÉNERO</label>
                            <label for="scan-age-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCANEAR: EDAD</label>
                            <label for="scan-geo-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#fb7185;">ESCANEAR: GEOGRAFÍA</label>
                        </div>

                        <div class="scan-content" style="border-top: 3px solid #db2777;">

                            <div class="scan-pane pane-gender-err">
                                <div style="background:rgba(255, 241, 242, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#f43f5e;">📡 ESCANEO DE GÉNERO: ERROR DE PREDICCIÓN</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(¿La falta de datos conduce a más errores?)</p>
                                </div>

                                <details style="cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:rgba(255, 241, 242, 0.1);">
                                        👇 HAZ CLIC PARA REVELAR TASAS DE FALSAS ALARMAS
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#f43f5e;">MUJERES (clase minoritaria)</span>
                                                <span style="font-weight:700; color:#f43f5e;">32% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:32%; background:#db2777; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">HOMBRES (bien representados)</span>
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">18% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:18%; background:#94a3b8; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:rgba(255, 241, 242, 0.1);">
                                            <div style="font-weight:800; color:#f43f5e;">❌ VEREDICTO: PUNTO CIEGO CONFIRMADO</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                Como el modelo dispone de pocos datos sobre este grupo, no ha aprendido patrones fiables y acaba equivocándose más a menudo. 
                                                Esta tasa elevada de error es muy probablemente consecuencia de la <strong>brecha de datos</strong> que hemos encontrado en el Paso 2. Cuando un grupo está infrarrepresentado, el modelo tiene un punto ciego.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <div class="scan-pane pane-age-err">
                                <div style="background:rgba(255, 241, 242, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#f43f5e;">📡 ESCANEO DE EDAD: ERROR DE PREDICCIÓN</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(¿El modelo falla fuera de la burbuja "25-45"?)</p>
                                </div>

                                <details style="cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:rgba(255, 241, 242, 0.1);">
                                        👇 HAZ CLIC PARA REVELAR TASAS DE FALSAS ALARMES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="display:flex; align-items:flex-end; justify-content:space-around; height:100px; margin-bottom:15px; padding-bottom:10px; border-bottom:1px solid var(--border-color-primary);">
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#ef4444; margin-bottom:2px;">33%</div>
                                                <div style="height:60px; background:#ef4444; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px; color:var(--body-text-color);">Menos de 25</div>
                                            </div>
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#16a34a; margin-bottom:2px;">18%</div>
                                                <div style="height:30px; background:#16a34a; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px; color:var(--body-text-color);">25-45</div>
                                            </div>
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#ef4444; margin-bottom:2px;">27%</div>
                                                <div style="height:50px; background:#ef4444; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px; color:var(--body-text-color);">Más de 45</div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:rgba(255, 241, 242, 0.1);">
                                            <div style="font-weight:800; color:#f43f5e;">❌ VEREDICTO: EL FALLO EN FORMA DE "U"</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                El modelo funciona bien dentro de la burbuja de edad con más datos (25–45), pero falla claramente fuera de este rango. 
                                                Esto ocurre porque no puede predecir con precisión el riesgo para grupos de edad que no ha estudiado lo suficiente.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <div class="scan-pane pane-geo-err">
                                <div style="background:rgba(255, 241, 242, 0.1); padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#f43f5e;">📡 ESCANEO DE GEOGRAFÍA: LA COMPROBACIÓN DE PROXY</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:var(--body-text-color);">(¿El “código postal” está creando un doble rasero por origen étnico?)</p>
                                </div>

                                <details style="cursor:pointer; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:rgba(255, 241, 242, 0.1);">
                                        👇 HAZ CLIC PARA REVELAR TASAS DE FALSAS ALARMAS
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#f43f5e;">ZONAS URBANAS (alta población minoritaria)</span>
                                                <span style="font-weight:700; color:#f43f5e;">58% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:58%; background:#db2777; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">ZONAS RURALES</span>
                                                <span style="font-weight:700; color:var(--body-text-color-subdued);">22% Error</span>
                                            </div>
                                            <div style="width:100%; background:var(--border-color-primary); height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:22%; background:#94a3b8; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:rgba(255, 241, 242, 0.1);">
                                            <div style="font-weight:800; color:#f43f5e;">❌ VEREDICTO: SESGO DE PROXY (RELACIÓN OCULTA) CONFIRMADO</div>
                                            <div style="font-size:0.95rem; margin-top:5px; color:var(--body-text-color);">
                                                La tasa de error en las zonas urbanas es muy elevada (58%). 
                                                Aunque se haya eliminado la variable de origen étnico, el modelo está utilizando la <strong>ubicación</strong> como sustituto indirecto para aplicar el mismo criterio. 
                                                En la práctica, trata el hecho de vivir en una zona urbana como un indicador de alto riesgo, generando un doble rasero por origen étnico.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                        </div>
                    </div>

                    <div style="text-align:center; margin-top:25px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p class="text-danger-adaptive" style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#f43f5e;">
                            🚀 TODOS LOS SISTEMAS ESCANEADOS
                        </p>
                        <p class="text-body-danger-adaptive" style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Has recopilado toda la evidencia forense. El sesgo es sistemático.
                            <br>Haz clic en <strong>Siguiente</strong> para hacer tu recomendación final sobre el sistema de IA.
                        </p>
                    </div>

                </div>
            </div>
        """
    },

    # --- MODULE 8: PREDICTION AUDIT SUMMARY ---
    {
        "id": 9,
        "title": "Paso 3: Resumen del Informe de Auditoría",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLAS</div>
                    <div class="tracker-step completed">2. EVIDENCIAS</div>
                    <div class="tracker-step active">3. ERRORES</div>
                    <div class="tracker-step">4. VEREDICTO</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PASO 3: EVALUAR ERRORES</h2>

                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">Informe de errores de predicción</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Revisa tus registros forenses. Has descubierto fallos sistemáticos en múltiples dimensiones.
                            <br>Estas evidencias muestran que el modelo vulnera el principio básico de <strong>Justicia y Equidad</strong>.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:25px; margin-bottom:30px;">

                        <div style="background:rgba(239, 68, 68, 0.1); border:2px solid #ef4444; border-radius:12px; padding:20px; box-shadow: 0 4px 10px rgba(239,68,68,0.1);">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #fda4af; padding-bottom:10px; margin-bottom:15px;">
                                <strong style="color:#ef4444; font-size:1.1rem;">🚨 AMENAZA PRINCIPAL</strong>
                                <span style="background:#ef4444; color:white; font-size:0.75rem; font-weight:800; padding:4px 8px; border-radius:4px;">CONFIRMADA</span>
                            </div>
                            <h3 style="margin:0 0 10px 0; color:#f87171; font-size:1.25rem;">Doble rasero étnico</h3>
                            <p style="font-size:0.95rem; line-height:1.5; color:var(--body-text-color);">
                                <strong>La Evidencia:</strong> Las personas presas afroamericanas se enfrentan a una <strong style="color:#ef4444;">tasa de falsas alarmas del 45%</strong> (vs. 23% para las personas presas blancas).
                            </p>
                            <div style="background:var(--background-fill-secondary); padding:10px; border-radius:6px; border:1px solid #fda4af; margin-top:10px;">
                                <strong style="color:#ef4444; font-size:0.9rem;">El Impacto:</strong> 
                                <span style="font-size:0.9rem; color:var(--body-text-color);">Sesgo punitivo. Personas inocentes están siendo clasificadas erróneamente como de alto riesgo casi el doble de veces que otros grupos.</span>
                            </div>
                        </div>

                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color-primary); padding-bottom:10px; margin-bottom:15px;">
                                <strong style="color:var(--body-text-color-subdued); font-size:1.1rem;">📍 FALLO DE PROXY</strong>
                                <span style="background:#f59e0b; color:white; font-size:0.75rem; font-weight:800; padding:4px 8px; border-radius:4px;">DETECTADO</span>
                            </div>
                            <h3 style="margin:0 0 10px 0; color:var(--body-text-color); font-size:1.25rem;">Discriminación geográfica</h3>
                            <p style="font-size:0.95rem; line-height:1.5; color:var(--body-text-color);">
                                <strong>La Evidencia:</strong> Las zonas urbanas muestran una elevada <strong style="color:#f59e0b;">tasa de error (el 58%)</strong>.
                            </p>
                            <div style="background:var(--background-fill-primary); padding:10px; border-radius:6px; border:1px solid var(--border-color-primary); margin-top:10px;">
                                <strong style="color:var(--body-text-color-subdued); font-size:0.9rem;">El mecanismo:</strong> 
                                <span style="font-size:0.9rem; color:var(--body-text-color);">Aunque se eliminó la variable de origen étnico, el sistema de IA utiliza la ubicación geográfica (código postal) como un sustituto indirecto, reproduciendo los mismos patrones discriminatorios sobre las mismas comunidades.</span>
                            </div>
                        </div>

                        <div style="grid-column: span 2; background:rgba(14, 165, 233, 0.1); border:2px solid #38bdf8; border-radius:12px; padding:20px;">
                            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                                <span style="font-size:1.5rem;">📉</span>
                                <h3 style="margin:0; color:#38bdf8; font-size:1.2rem;">Fallo Secundario: Errores de predicción debidos al sesgo de representación</h3>
                            </div>
                            <p style="font-size:1rem; margin-bottom:0; color:var(--body-text-color);">
                                <strong>La Evidencia:</strong> Alta inestabilidad en las predicciones para <strong style="color:#38bdf8;">Mujeres y grupos de edad más jóvenes/mayores</strong>.
                                <br>
                                <span style="color:var(--body-text-color-subdued); font-size:0.95rem;"><strong>¿Por qué pasa?</strong> Los datos de entrada no incluían ejemplos suficientes para estos grupos (el espejo distorsionado), lo que impide que el modelo aprenda patrones fiables y lo lleva a “adivinar” en lugar de predecir.</span>
                            </p>
                        </div>

                    </div>


                    <div style="text-align:center; margin-top:25px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; margin-bottom:5px; color:#ef4444;">
                            🚀 EXPEDIENTE DE INVESTIGACIÓN CERRADO. EVIDENCIA FINAL BLOQUEADA.
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:var(--body-text-color);">
                            Has investigado con éxito los Datos de Entrada y los Errores de Salida.
                            <br>Responde a la siguiente pregunta para aumentar tu puntuación de Brújula Moral. Luego haz clic en <strong>Siguiente</strong> para presentar tu informe final sobre el sistema de IA.
                        </p>
                    </div>
                </div>
            </div>
        """
    },

    # --- MODULE 9: FINAL VERDICT & REPORT GENERATION ---
{
        "id": 10,
        "title": "Paso 4: El Veredicto Final",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. REGLAS</div>
                    <div class="tracker-step completed">2. EVIDENCIAS</div>
                    <div class="tracker-step completed">3. ERRORES</div>
                    <div class="tracker-step active">4. VEREDICTO</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">PASO 4: PRESENTA EL INFORME FINAL</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title header-accent" style="margin-top:10px;">Construye el expediente del caso</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Has completado la auditoría. Ahora debes elaborar el informe final para el tribunal y otras partes interesadas.
                            <br><strong>Selecciona los hallazgos válidos a continuación</strong> para añadirlos al registro oficial. Atención: no todas las hipótesis están respaldadas por evidencia.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:30px;">

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Hallazgo: "El espejo distorsionado"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AÑADIDO AL INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmado: Los datos de entrada no reflejan correctamente la población real. Algunos grupos aparecen claramente sobrerrepresentados, probablemente como consecuencia de sesgos históricos.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Hallazgo: "Intención maliciosa del programador"
                            </summary>
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; border-top:1px solid #fecaca; color:var(--body-text-color);">
                                <strong style="color:#ef4444;">❌ RECHAZADO</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Incorrecto. No encontramos evidencia de código malicioso. El sesgo provenía de los <em>datos</em> y los <em>proxies</em>, no de la persona que desarrolló el sistema.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Hallazgo: "Doble rasero étnico"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AÑADIDO AL INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmado: Los personas presas afroamericanas sufren una tasa de falsas alarmas 2x más alta que las personas presas blancas.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Hallazgo: "Fuga de variable proxy"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AÑADIDO AL INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmado: Aunque se ha eliminado la variable de origen étnico, el sistema utiliza el código postal como un sustituto indirecto, reintroduciendo el mismo sesgo en los resultados.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Hallazgo: "Error de Cálculo de Hardware"
                            </summary>
                            <div style="background:rgba(239, 68, 68, 0.1); padding:15px; border-top:1px solid #fecaca; color:var(--body-text-color);">
                                <strong style="color:#ef4444;">❌ RECHAZADO</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">rrelevante. Los sistemas funcionan correctamente y los cálculos son consistentes. El problema no es técnico: los <em>patrones</em> que ha aprendido el modelo son injustos.</p>
                            </div>
                        </details>

                        <details style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:var(--body-text-color); display:flex; align-items:center; gap:10px;">
                                <div style="background:var(--background-fill-primary); width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">+</div>
                                Hallazgo: "Puntos ciegos de generalización"
                            </summary>
                            <div style="background:rgba(34, 197, 94, 0.1); padding:15px; border-top:1px solid #bbf7d0; color:var(--body-text-color);">
                                <strong style="color:#22c55e;">✅ AÑADIDO AL INFORME</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmado: La falta de datos para mujeres y personas más jóvenes y mayor de edad genera predicciones poco fiables para estos grupos.</p>
                            </div>
                        </details>

                    </div>

                    <div style="background:var(--background-fill-primary); border-top:2px solid var(--border-color-primary); padding:25px; text-align:center; border-radius:0 0 12px 12px; margin-top:-15px;">
                        <h3 style="margin-top:0; color:var(--body-text-color);">⚖️ ENVÍA TU RECOMENDACIÓN (respondiendo a la pregunta de Brújula Moral de a continuación)</h3>
                        <p style="font-size:1.05rem; margin-bottom:20px; color:var(--body-text-color-subdued);">
                            Basándote en la evidencia archivada anteriormente, ¿cuál es tu recomendación oficial respecto a este sistema de IA?
                        </p>

                        <div style="display:flex; justify-content:center; gap:20px; flex-wrap:wrap;">
                            <div style="background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); padding:15px 25px; border-radius:8px; cursor:pointer; max-width:250px; opacity:0.8; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                                <div style="font-size:2rem; margin-bottom:10px;">✅</div>
                                <div style="font-weight:700; color:#166534; margin-bottom:5px;">CERTIFICAR COMO SEGURO</div>
                                <div style="font-size:0.85rem; color:var(--body-text-color-subdued);">Los sesgos son tecnicismos menores. Continuar usando el sistema.</div>
                            </div>

                            <div style="background:var(--background-fill-secondary); border:2px solid #ef4444; padding:15px 25px; border-radius:8px; cursor:pointer; max-width:250px; box-shadow:0 4px 12px rgba(239,68,68,0.2);">
                                <div style="font-size:2rem; margin-bottom:10px;">🚨</div>
                                <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">SEÑAL DE ALERTA: PAUSAR Y REPARAR</div>
                                <div style="font-size:0.85rem; color:#ef4444;">El sistema vulnera el principio de Justicia y Equidad. Detener inmediatamente.</div>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:30px;">
                        <p style="font-size:0.95rem; color:var(--body-text-color);">
                            Selecciona tu recomendación final a continuación para presentar oficialmente tu informe y completar tu investigación.
                        </p>
                    </div>

                </div>
            </div>
        """,
    },


    # --- MODULE 10: PROMOTION ---
{
        "id": 11,
        "title": "Misión Cumplida: Promoción Desbloqueada",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">✓ REGLAS</div>
                    <div class="tracker-step completed">✓ EVIDENCIA</div>
                    <div class="tracker-step completed">✓ ERROR</div>
                    <div class="tracker-step completed">✓ VEREDICTO</div>
                </div>

                <div class="slide-body">
                    
                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#22c55e;">🎉 MISIÓN CUMPLIDA</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:var(--body-text-color);">
                            Informe presentado. El tribunal ha aceptado tu recomendación de poner en <strong>PAUSA</strong> el sistema.
                        </p>
                    </div>

                    <div style="background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; border-radius:12px; padding:20px; margin-bottom:30px; text-align:center; box-shadow: 0 4px 15px rgba(34, 197, 94, 0.1);">
                        <div style="font-size:1.2rem; font-weight:800; color:#22c55e; letter-spacing:1px; text-transform:uppercase;">
                            ✅ DECISIÓN VALIDADA
                        </div>
                        <p style="font-size:1.05rem; color:var(--body-text-color); margin:10px 0 0 0;">
                            Tu decisión se apoya en evidencia y razonamiento, de acuerdo con el principio de <strong>Justicia y Equidad</strong>.
                        </p>
                    </div>

                    <div style="background:linear-gradient(135deg, rgba(14, 165, 233, 0.1) 0%, rgba(20, 184, 166, 0.1) 100%); border:2px solid #0ea5e9; border-radius:16px; padding:0; overflow:hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                        
                        <div style="background:#0ea5e9; padding:15px; text-align:center; color:white;">
                            <h3 style="margin:0; font-size:1.3rem; letter-spacing:1px;">🎖️ PROMOCIÓN DESBLOQUEADA</h3>
                            <div style="font-size:0.9rem; opacity:0.9;">SUBIDA DE NIVEL: DE DETECTIVE A CONSTRUCTOR</div>
                        </div>

                        <div style="padding:25px;">
                            <p style="text-align:center; font-size:1.1rem; margin-bottom:20px; color:var(--body-text-color);">
                                Detectar el sesgo es solo el primer paso. Con la evidencia recopilada, el foco pasa ahora a la mejora del sistema.
                                <br><strong>Ahora cambias tu lupa por una llave inglesa.</strong>
                            </p>

                            <div style="background:var(--background-fill-secondary); border-radius:12px; padding:20px; border:1px solid #bae6fd;">
                                <h4 style="margin-top:0; color:#38bdf8; text-align:center; margin-bottom:15px;">🎓 NUEVO ROL: INGENIERO/A DE EQUIDAD</h4>
                                
                                <ul style="list-style:none; padding:0; margin:0; font-size:1rem; color:var(--body-text-color);">
                                    <li style="margin-bottom:12px; display:flex; gap:10px; align-items:start;">
                                        <span>🔧</span>
                                        <span><strong style="color:#38bdf8;">Tarea 1:</strong> Identificar y reducir el uso de variables proxy (como el código postal).</span>
                                    </li>
                                    <li style="margin-bottom:12px; display:flex; gap:10px; align-items:start;">
                                        <span>📊</span>
                                        <span><strong style="color:#38bdf8;">Tarea 2:</strong> Mejorar la representación de los datos y su cobertura.</span>
                                    </li>
                                    <li style="display:flex; gap:10px; align-items:start;">
                                        <span>🗺️</span>
                                        <span><strong style="color:#38bdf8;">Tarea 3:</strong> Definir una hoja de ruta para el monitoreo continuo del sistema.</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:30px;">
                        <p style="font-size:1.1rem; font-weight:600; color:var(--body-text-color);">
                            👉 Tu próxima misión comienza en la <strong>Actividad 8: El ingeniero/a de la equidad en acción</strong>.
                            <br>
                            <span style="font-size:0.95rem; font-weight:400; color:var(--body-text-color-subdued);">
                              <strong>Continúa con la siguiente actividad abajo</strong> para concluir esta auditoría e iniciar las mejoras — o haz clic en <span style="white-space:nowrap;">Siguiente (barra superior)</span> en vista ampliada ➡️
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
        "q": "🚀 **Primera Oportunidad de Puntuación:** ¿Por qué multiplicamos tu Exactitud por el Progreso Ético? (¡Responde correctamente para ganar tu primer aumento de Puntuación de Brújula Moral!)",
        "o": [
            "A) Porque la simple exactitud ignora el sesgo potencial y el daño.",
            "B) Para hacer las matemáticas de la clasificación más complicadas.",
            "C) La exactitud es la única métrica que realmente importa.",
        ],
        "a": "A) Porque la simple exactitud ignora el sesgo potencial y el daño.",
        # Updated success message to confirm the 'win'
        "success": "<strong>¡Puntuación Desbloqueada!</strong> Calibración completa. Ahora estás oficialmente en la clasificación.",
    },
    1: {
        "t": "t2",
        "q": "¿Cuál es el mejor primer paso antes de comenzar a examinar los datos del modelo?",
        "o": [
            "Saltar directamente a los datos y buscar patrones.",
            "Aprender las reglas que definen qué cuenta como sesgo.",
            "Dejar que el modelo explique sus propias decisiones.",
        ],
        "a": "Aprender las reglas que definen qué cuenta como sesgo.",
        "success": "Sesión informativa completada. Estás comenzando tu investigación con las reglas correctas en mente.",
    },
    2: {
        "t": "t3",
        "q": "¿Qué requieren la Justicia y la Equidad?",
        "o": [
            "Explicar las decisiones del modelo",
            "Comprobar los errores de predicción a nivel de grupo para prevenir daños sistemáticos",
            "Minimizar la tasa de error",
        ],
        "a": "Comprobar los errores de predicción a nivel de grupo para prevenir daños sistemáticos",
        "success": "Protocolo activo. Ahora estás auditando para Justicia y Equidad.",
    },
    3: {
        "t": "t4",
        "q": "Detective, sospechamos que los datos de entrada son un 'espejo distorsionado' de la realidad. Para confirmar si existe Sesgo de Representación, ¿cuál es tu objetivo forense principal?",
        "o": [
            "A) Necesito leer las entradas del diario personal del juez.",
            "B) Necesito comprobar si la computadora está enchufada correctamente.",
            "C) Necesito comparar las distribuciones demográficas (origen étnico/género) de los datos con las estadísticas de población del mundo real.",
        ],
        "a": "C) Necesito comparar las distribuciones demográficas (origen étnico/género) de los datos con las estadísticas de población del mundo real.",
        "success": "Objetivo Adquirido. Estás preparado para entrar al laboratorio forense de datos.",
    },
    4: {
        "t": "t5",
        "q": "Revisión del análisis forense: Has marcado los datos de género como una 'brecha de datos' (solo 19% mujeres). Según tu registro de evidencias, ¿cuál es el riesgo técnico específico para este grupo?",
        "o": [
            "A) El modelo tendrá un 'punto ciego' porque no ha visto suficientes ejemplos para aprender patrones precisos.",
            "B) La IA apuntará automáticamente a este grupo debido al exceso de vigilancia histórica.",
            "C) El modelo utilizará por defecto las estadísticas del 'mundo Real' para llenar los números que faltan.",
        ],
        "a": "A) El modelo tendrá un 'punto ciego' porque no ha visto suficientes ejemplos para aprender patrones precisos.",
        "success": "Evidencia Bloqueada. Entiendes que la 'Falta de Datos' crea puntos ciegos, haciendo que las predicciones para este grupo sean menos fiables.",
    },
    # --- QUESTION 4 (Evidence Report Summary) ---
    5: {
        "t": "t6",
        "q": "Detective, revisa tu tabla de Resumen de Evidencia. Has encontrado casos tanto de sobrerrepresentación (origen étnico) como de infrarrepresentación (género/edad). ¿Cuál es tu conclusión general sobre cómo el sesgo de representación afecta a la IA?",
        "o": [
            "A) Confirma que el conjunto de datos es neutral, ya que las categorías 'sobre' e 'infra' se cancelan matemáticamente entre sí.",
            "B) Crea un 'riesgo de aumento de error de predicción' en AMBAS direcciones: tanto si un grupo se exagera como si se ignora, la visión de la realidad de la IA se deforma.",
            "C) Solo crea riesgo cuando faltan datos (infrarrepresentación); tener datos extra (sobrerrepresentación) en realidad hace que el modelo sea más preciso.",
        ],
        "a": "B) Crea un 'riesgo de aumento de error de predicción' en AMBAS direcciones: tanto si un grupo se exagera como si se ignora, la visión de la realidad de la IA se deforma.",
        "success": "conclusión verificada. Los datos distorsionados, tanto si están inflados como si faltan, pueden llevar a una justicia distorsionada.",
    },
    6: {
        "t": "t7",
        "q": "Detective, estás cazando el patrón del 'doble rasero'. ¿Qué pieza específica de evidencia representa esta señal de alerta?",
        "o": [
            "A) El modelo comete cero errores para ningún grupo.",
            "B) Un grupo sufre una tasa de 'falsas alarmas' significativamente más alta que otro grupo.",
            "C) Los datos de entrada contienen más hombres que mujeres.",
        ],
        "a": "B) Un grupo sufre una tasa de 'falsas alarmas' significativamente más alta que otro grupo.",
        "success": "Patrón confirmado. Cuando la tasa de error está desequilibrada, es un doble rasero.",
    },
    # --- QUESTION 6 (Race Error Gap) ---
    7: {
        "t": "t8",
        "q": "Revisa tu registro de datos. ¿Qué reveló el escaneo de 'Falsas Alarmas' sobre el tratamiento de los acusados afroamericanos?",
        "o": [
            "A) Son tratados exactamente igual que los acusados blancos.",
            "B) Son omitidos por el sistema más a menudo (Sesgo de Indulgencia).",
            "C) Tienen casi el doble de probabilidades de ser marcados erróneamente como de 'Alto Riesgo' (Sesgo punitivo).",
        ],
        "a": "C) Tienen casi el doble de probabilidades de ser marcados erróneamente como de 'Alto Riesgo' (Sesgo punitivo).",
        "success": "Evidencia registrada. El sistema está castigando a personas inocentes basándose en el origen étnico.",
    },

    # --- QUESTION 7 (Generalization & Proxy Scan) ---
    8: {
        "t": "t9",
        "q": "El escaneo de geografía mostró una tasa de error muy elevada en las zonas Urbanas. ¿Qué demuestra esto sobre los 'códigos Postales'?",
        "o": [
            "A) Los Códigos Postales actúan como una 'Variable Proxy' para apuntar a grupos específicos, incluso si variables como el origen étnico se eliminan del conjunto de datos.",
            "B) La IA es simplemente mala leyendo mapas y datos de ubicación.",
            "C) La gente en las ciudades genera naturalmente más errores informáticos que la gente en las zonas rurales.",
        ],
        "a": "A) Los Códigos Postales actúan como una 'Variable Proxy' para apuntar a grupos específicos, incluso si variables como el origen étnico se eliminan del conjunto de datos.",
        "success": "Proxy identificado. Esconder una variable no funciona si dejas un proxy atrás.",
    },

    # --- QUESTION 8 (Audit Summary) ---
    9: {
        "t": "t10",
        "q": "Has cerrado el expediente del caso. ¿Cuál de las siguientes opciones está CONFIRMADA como la 'Amenaza Principal' en tu informe final?",
        "o": [
            "A) Un doble rasero por origen étnico donde las personas presas afroamericanas inocentes son penalizadas el doble de veces.",
            "B) Código malicioso escrito por hackers para romper el sistema.",
            "C) Un fallo de hardware en la sala de servidores causando errores matemáticos aleatorios.",
        ],
        "a": "A) Un doble rasero por origen étnico donde las personas presas afroamericanas inocentes son penalizadas el doble de veces.",
        "success": "Amenaza Evaluada. El sesgo está confirmado y documentado.",
    },

    # --- QUESTION 9 (Final Verdict) ---
    10: {
        "t": "t11",
        "q": "Basándote en las graves vulneraciones de Justicia y Equidad encontradas en tu auditoría, ¿cuál es tu recomendación final al tribunal?",
        "o": [
            "A) CERTIFICAR: El sistema está mayoritariamente bien, los errores menores son aceptables.",
            "B) SEÑAL DE ALERTA: Poner en pausa el sistema inmediatamente porque es inseguro y sesgado y para repararlo.",
            "C) ADVERTENCIA: Utilizar el sistema de IA solo los fines de semana cuando el crimen es más bajo.",
        ],
        "a": "B) SEÑAL DE ALERTA: Poner en pausa el sistema inmediatamente porque es inseguro y sesgado y para repararlo.",
        "success": "Veredicto Entregado. Has detenido con éxito un sistema dañino.",
    },
}


# --- 6. SCENARIO CONFIG (for Module 0) ---
SCENARIO_CONFIG = {
    "Predicción de riesgo criminal": {
        "q": (
            "A system predicts who might reoffend.\n"
            "Why isn’t accuracy alone enough?"
        ),
        "summary": "Incluso un sesgo pequeño puede repetirse en miles de decisiones de fianza/sentencia — vidas reales, impacto real.",
        "a": "La exactitud puede parecer buena en general mientras sigue siendo injusta para grupos específicos afectados por el modelo.",
        "rationale": "El sesgo a escala significa que un patrón puede dañar a muchas personas rápidamente. Debemos comprobar la equidad por subgrupos, no solo la puntuación general."
    },
    "Sistema de aprobación de préstamos": {
        "q": (
            "A model decides who gets a loan.\n"
            "What’s the biggest risk if it learns from biased history?"
        ),
        "summary": "Algunos grupos son bloqueados una y otra vez, cerrando oportunidades de vivienda, educación y estabilidad.",
        "a": "Puede negar repetidamente a los mismos grupos, copiando viejos patrones y bloqueando oportunidades.",
        "rationale": "Si las aprobaciones pasadas fueron injustas, el modelo puede reflejarlo y mantener puertas cerradas — no solo una vez, sino repetidamente."
    },
    "Selección de admisiones universitarias": {
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
            "Si el sistema no se usa en ningún caso, su sesgo no puede dañar a nadie todavía — "
            "pero una vez que se ponga en marcha, cada decisión sesgada puede escalar rápidamente."
        )
    elif c_int < 5000:
        message = (
            f"Incluso con <strong>{c_int}</strong> casos por año, un modelo sesgado puede afectar silenciosamente "
            "a cientos de personas con el tiempo."
        )
    elif c_int < 15000:
        message = (
            f"Con alrededor de <strong>{c_int}</strong> casos por año, un modelo sesgado podría etiquetar injustamente "
            "a miles de personas como 'alto riesgo'."
        )
    else:
        message = (
            f"Con <strong>{c_int}</strong> casos por año, un algoritmo defectuoso puede moldear los futuros "
            "de toda una región — convirtiendo el sesgo oculto en miles de decisiones injustas."
        )

    return f"""
    <div class="hint-box interactive-block">
        <p style="margin-bottom:4px; font-size:1.05rem;">
            <strong>Casos estimados procesados por año:</strong> {c_int}
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
                <p style="margin:0;"><strong>Conclusión clave:</strong> {cfg["a"]}</p>
                <p style="margin:6px 0 0 0; color:var(--body-text-color-subdued);">{cfg["f_correct"]}</p>
            </div>
        """)
    return "<div class='interactive-block'>" + "".join(cards) + "</div>"

def render_scenario_card(name: str):
    cfg = SCENARIO_CONFIG.get(name)
    if not cfg:
        return "<div class='hint-box'>Selecciona un escenario para ver detalles.</div>"
    q_html = cfg["q"].replace("\n", "<br>")
    return f"""
    <div class="scenario-box">
        <h3 class="slide-title" style="font-size:1.4rem; margin-bottom:8px;">📘 {name}</h3>
        <div class="slide-body">
            <div class="hint-box">
                <p style="margin:0 0 6px 0; font-size:1.05rem;">{q_html}</p>
                <p style="margin:0 0 6px 0;"><strong>Conclusión clave:</strong> {cfg['a']}</p>
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
        header_title = "¡Estás Oficialmente en la Clasificación!"
        summary_line = (
            "Acabas de ganar tu primera Puntuación de Brújula Moral — ahora eres parte de la clasificación global."
        )
        cta_line = "Desplázate hacia abajo para dar tu próximo paso y comenzar a escalar."
    elif style_key == "major":
        header_emoji = "🔥"
        header_title = "¡Gran Impulso de Brújula Moral!"
        summary_line = (
            "Tu decisión tuvo un gran impacto — acabas de adelantar a otros participantes."
        )
        cta_line = "Desplázate hacia abajo para enfrentar tu próximo desafío y mantener el impulso."
    elif style_key == "climb":
        header_emoji = "🚀"
        header_title = "Estás Escalando en la Clasificación"
        summary_line = "Buen trabajo — has superado a algunos otros participantes."
        cta_line = "Desplázate hacia abajo para continuar tu investigación y llegar aún más alto."
    elif style_key == "tight":
        header_emoji = "📊"
        header_title = "La Clasificación Está Cambiando"
        summary_line = (
            "Otros equipos también se están moviendo. Necesitarás algunas decisiones más fuertes para destacar."
        )
        cta_line = "Responde la siguiente pregunta para fortalecer tu posición."
    else:  # "solid"
        header_emoji = "✅"
        header_title = "Progreso Registrado"
        summary_line = "Tu perspectiva ética aumentó tu Puntuación de Brújula Moral."
        cta_line = "Prueba el siguiente escenario para alcanzar el próximo nivel."

    # --- SCORE / RANK LINES ---------------------------------------------

    # First-time: different wording (no previous score)
    if style_key == "first":
        score_line = f"🧭 Puntuación: <strong>{new_score:.3f}</strong>"
        if ranks_are_int:
            rank_line = f"🏅 Rango Inicial: <strong>#{new_rank}</strong>"
        else:
            rank_line = f"🏅 Rango Inicial: <strong>#{new_rank}</strong>"
    else:
        score_line = (
            f"🧭 Puntuación: {old_score:.3f} → <strong>{new_score:.3f}</strong> "
            f"(+{diff_score:.3f})"
        )

        if ranks_are_int:
            if old_rank == new_rank:
                rank_line = f"📊 Rango: <strong>#{new_rank}</strong> (manteniéndose estable)"
            elif rank_diff > 0:
                rank_line = (
                    f"📈 Rango: #{old_rank} → <strong>#{new_rank}</strong> "
                    f"(+{rank_diff} posiciones)"
                )
            else:
                rank_line = (
                    f"🔻 Rango: #{old_rank} → <strong>#{new_rank}</strong> "
                    f"({rank_diff} posiciones)"
                )
        else:
            rank_line = f"📊 Rango: <strong>#{new_rank}</strong>"

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
                    <div class="label-text">Puntuación de Brújula Moral</div>
                    <div class="score-text-primary">🧭 {display_score:.3f}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Rango de Equipo</div>
                    <div class="score-text-team">{team_rank_display}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Rango Global</div>
                    <div class="score-text-global">{rank_display}</div>
                </div>
            </div>
            <div class="summary-progress">
                <div class="progress-label">Progreso de la Misión: {progress_pct}%</div>
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
            team_label = translate_team_name_for_display(t['team'], lang='es')
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
        <h3 class="slide-title" style="margin-bottom:10px;">📊 Clasificación en Vivo</h3>
        <div class="lb-tabs">
            <input type="radio" id="lb-tab-team" name="lb-tabs" checked>
            <label for="lb-tab-team" class="lb-tab-label">🏆 Equipo</label>
            <input type="radio" id="lb-tab-user" name="lb-tabs">
            <label for="lb-tab-user" class="lb-tab-label">👤 Individual</label>
            <div class="lb-tab-panels">
                <div class="lb-panel panel-team">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Rango</th><th>Equipo</th><th style='text-align:right;'>Promedio 🧭</th></tr>
                            </thead>
                            <tbody>{team_rows}</tbody>
                        </table>
                    </div>
                </div>
                <div class="lb-panel panel-user">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Rango</th><th>Agente</th><th style='text-align:right;'>Puntuación 🧭</th></tr>
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
        feedback_html = f"<div class='hint-box' style='border-left:4px solid #ef4444; color:#b91c1c;'>❌ ERROR: La afirmación '{INCORRECT_FINDING.split(':')[0]}' NO es un hallazgo verdadero. Comprueba los resultados de tu laboratorio e inténtalo de nuevo.</div>"
    elif missed_correct:
        feedback_html = f"<div class='hint-box' style='border-left:4px solid #f97316; color:#f97316;'>⚠️ INCOMPLETO: Te falta {len(missed_correct)} pieza(s) de evidencia clave. Tu informe final debe estar completo.</div>"
    elif len(selected_biases) == len(CORRECT_FINDINGS):
        feedback_html = "<div class='hint-box' style='border-left:4px solid #22c55e; color:#16a34a;'>✅ EVIDENCIA ASEGURADA: Este es un diagnóstico completo y preciso del fallo sistemático del modelo.</div>"
    else:
        feedback_html = "<div class='hint-box' style='border-left:4px solid var(--color-accent);'>Recopilando evidencia...</div>"

    # --- Build Markdown Report Preview ---
    if not correctly_selected:
        report_markdown = "Selecciona las tarjetas de evidencia de arriba para comenzar a redactar tu informe. (El borrador del informe aparecerá aquí.)"
    else:
        lines = []
        lines.append("### 🧾 Borrador de Informe de Auditoría")
        lines.append("\n**Hallazgos de Error Sistemático:**")

        # Map short findings to the markdown report
        finding_map = {
            "Choice A": "Sesgo Punitivo (Origen étnico): El modelo es el doble de severo con los acusados AA.",
            "Choice B": "Generalización (Género): Errores de falsa Alarma más altos para mujeres.",
            "Choice C": "Patrón de indulgencia (Origen étnico): Más advertencias omitidas para acusados blancos.",
            "Choice E": "Sesgo de proxy (Geografía): La ubicación actúa como sustituto de origen étnico/clase.",
        }

        for i, choice in enumerate(CORRECT_FINDINGS):
            if choice in correctly_selected:
                short_key = choice.split(':')[0]
                lines.append(f"{i+1}. {finding_map[short_key]}")

        if len(correctly_selected) == len(CORRECT_FINDINGS) and not incorrectly_selected:
             lines.append("\n**CONCLUSIÓN:** La evidencia demuestra que el sistema crea daño desigual y viola la Justicia y la Equidad.")

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
def create_bias_detective_es_app(theme_primary_hue: str = "indigo"):
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
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Cargando...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>🕵️‍♀️ Autenticando...</h2>"
                "<p>Sincronizando Datos de Brújula Moral...</p>"
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
                            "<span class='points-chip'>🧭 Puntos de la Brújula Moral disponibles</span>"
                            "<span>Responde para aumentar tu puntuación</span>"
                            "</div>"
                        )

                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Selecciona una Respuesta:",
                            elem_classes=["quiz-radio-large"],
                        )
                        feedback = gr.HTML("")
                        quiz_wiring_queue.append((i, radio, feedback))

                    # --- NAVIGATION BUTTONS ---
                    with gr.Row():
                        btn_prev = gr.Button("⬅️ Anterior", visible=(i > 0))
                        next_label = (
                            "Siguiente ▶️"
                            if i < len(MODULES) - 1
                            else "🎉 ¡Has completado la Parte 1! (Por favor, continúa con la siguiente actividad)"
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
                            "❌ Incorrecto. Revisa la evidencia anterior.</div>",
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
                "<div class='hint-box'>⚠️ Error de Autenticación. Por favor, inicia desde el enlace del curso.</div>",
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
                    js=nav_js(prev_target_id, "Cargando..."),
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
                    js=nav_js(next_target_id, "Cargando..."),
                ).then(
                    fn=make_nav_generator(curr_col, next_col),
                    outputs=[curr_col, next_col],
                )

        return demo




def launch_bias_detective_es_app(
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
    app = create_bias_detective_es_app(theme_primary_hue=theme_primary_hue)
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
    launch_bias_detective_es_app(share=False, debug=True, height=1000)

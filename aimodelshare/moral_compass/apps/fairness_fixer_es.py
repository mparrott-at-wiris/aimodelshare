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
        "title": "Módulo 0: El Banco de Trabajo del Ingeniero de Equidad",
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
                            <span>PROMOCIÓN: INGENIERO DE EQUIDAD</span>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center;">🔧 Fase Final: La Corrección</h2>

                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 20px auto; text-align:center;">
                        <strong>Bienvenido de nuevo.</strong> Has expuesto con éxito el sesgo en el sistema de IA de predicción de riesgo COMPAS y has bloqueado su despliegue. Buen trabajo.
                    </p>

                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 24px auto; text-align:center;">
                        Pero el tribunal todavía espera una herramienta para ayudar a gestionar el retraso de casos. Tu nueva misión es tomar ese modelo roto y <strong>arreglarlo</strong> para que sea seguro de usar.
                    </p>

                    <div class="ai-risk-container" style="border-left:4px solid var(--color-accent);">
                        <h4 style="margin-top:0; font-size:1.15rem;">El Desafío: "Sesgo Persistente"</h4>
                        <p style="font-size:1.0rem; margin-bottom:0;">
                            No puedes simplemente eliminar la columna "Raza" y marcharte. El sesgo se esconde en <strong>Variables Proxy</strong>—datos como el <em>Código Postal</em> o los <em>Ingresos</em>
                            que se correlacionan con la raza. Si eliminas la etiqueta pero mantienes los proxies, el modelo aprende el sesgo de todos modos.
                        </p>
                    </div>

                    <div class="ai-risk-container" style="margin-top:16px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">📋 Orden de Trabajo de Ingeniería</h4>
                        <p style="text-align:center; margin-bottom:12px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                            Debes completar estos tres protocolos para certificar el modelo para su lanzamiento:
                        </p>

                        <div style="display:grid; gap:10px; margin-top:12px;">

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">✂️</div>
                                <div>
                                    <div style="font-weight:700;">Protocolo 1: Sanear Entradas</div>
                                    <div style="font-size:0.9rem;">Eliminar clases protegidas y cazar proxies ocultos.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Pendiente</div>
                            </div>

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">🔗</div>
                                <div>
                                    <div style="font-weight:700;">Protocolo 2: Causa versus Correlación</div>
                                    <div style="font-size:0.9rem;">Filtrar datos por comportamiento real, no solo correlación.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Bloqueado</div>
                            </div>

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">⚖️</div>
                                <div>
                                    <div style="font-weight:700;">Protocolo 3: Representación y Muestreo</div>
                                    <div style="font-size:0.9rem;">Equilibrar los datos para coincidir con la población local.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Bloqueado</div>
                            </div>

                        </div>
                    </div>

                   <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ¿LISTO PARA COMENZAR LA CORRECCIÓN?
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Haz clic en <strong>Siguiente</strong> para comenzar a arreglar el modelo.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 1: SANITIZE INPUTS (Protected Classes) ---
    {
        "id": 1,
        "title": "Protocolo 1: Sanear Entradas",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOLO 1: SANEAR ENTRADAS</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Misión: Eliminar clases protegidas y proxies ocultos.</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">PASO 1 DE 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        <strong>Equidad a través de la Ceguera.</strong>
                        Legal y éticamente, no podemos usar <strong>Clases Protegidas</strong> (características con las que naces, como raza o edad) para calcular la puntuación de riesgo de alguien.
                    </p>

                    <div class="ai-risk-container">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <h4 style="margin:0;">📂 Inspector de Columnas del Dataset</h4>
                            <div style="font-size:0.8rem; font-weight:700; color:#ef4444;">⚠ CONTIENE CARACTERÍSTICAS ILEGALES</div>
                        </div>

                        <p style="font-size:0.95rem; margin-bottom:12px;">
                            Revisa los encabezados a continuación. Identifica las columnas que violan las leyes de equidad.
                        </p>

                        <div style="display:flex; gap:8px; flex-wrap:wrap; background:rgba(0,0,0,0.05); padding:12px; border-radius:8px; border:1px solid var(--border-color-primary);">

                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Raza
                            </div>
                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Género
                            </div>
                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Edad
                            </div>

                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Condenas Previas</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Estado Laboral</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Código Postal</div>
                        </div>
                    </div>


            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓN REQUERIDA: ELIMINAR DATOS DE ENTRADA PROTEGIDOS
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Usa el Panel de Comandos a continuación para ejecutar la eliminación.
                            Luego haz clic en <strong>Siguiente</strong> para continuar arreglando el modelo.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 2: SANITIZE INPUTS (Proxy Variables) ---
    {
        "id": 2,
        "title": "Protocolo 1: Cazando Proxies",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                   <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOLO 1: SANEAR ENTRADAS</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Misión: Eliminar clases protegidas y proxies ocultos.</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">PASO 2 DE 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        <strong>El Problema del "Sesgo Persistente".</strong>
                        Has eliminado Raza y Género. Genial. Pero el sesgo a menudo se esconde en <strong>Variables Proxy</strong>—puntos de datos neutrales que actúan como un sustituto secreto de la raza.
                    </p>

                    <div class="hint-box" style="border-left:4px solid #f97316;">
                        <div style="font-weight:700;">Por qué el "Código Postal" es un Proxy</div>

                        <p style="margin:6px 0 0 0;">
                            Históricamente, muchas ciudades fueron segregadas por ley o clase. Incluso hoy, el <strong>Código Postal</strong> a menudo se correlaciona fuertemente con el origen.
                            </p>
                        <p style="margin-top:8px; font-weight:600; color:#c2410c;">
                            🚨 El Riesgo: Si das datos de ubicación a la IA, puede "adivinar" la raza de una persona con alta precisión, re-aprendiendo el sesgo exacto que acabas de intentar borrar.
                        </p>
                    </div>

                    <div class="ai-risk-container" style="margin-top:16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h4 style="margin:0;">📂 Inspector de Columnas del Dataset</h4>
                            <div style="font-size:0.8rem; font-weight:700; color:#f97316;">⚠️ 1 PROXY DETECTADO</div>
                        </div>

                        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; padding:12px; background:rgba(0,0,0,0.05); border-radius:8px;">
                            <div style="padding:6px 12px; background:#e5e7eb; color:#9ca3af; text-decoration:line-through; border-radius:6px;">Raza</div>
                            <div style="padding:6px 12px; background:#e5e7eb; color:#9ca3af; text-decoration:line-through; border-radius:6px;">Género</div>

                            <div style="padding:6px 12px; background:#ffedd5; border:1px solid #f97316; border-radius:6px; font-weight:700; color:#9a3412;">
                                ⚠️ Código Postal
                            </div>

                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Condenas Previas</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Empleo</div>
                        </div>
                    </div>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓN REQUERIDA: ELIMINAR DATOS DE ENTRADA PROXY
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Selecciona la Variable Proxy a continuación para borrarla.
                            Luego haz clic en <strong>Siguiente</strong> para continuar arreglando el modelo.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 3: THE ACCURACY CRASH (The Pivot) ---
    {
        "id": 3,
        "title": "Alerta del Sistema: Verificación del Modelo",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:white; width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOLO 1: SANEAR ENTRADAS</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Fase: Verificación y Reentrenamiento del Modelo</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">PASO 3 DE 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">🤖 La Ejecución de Verificación</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        Has eliminado con éxito <strong>Raza, Género, Edad y Código Postal</strong>.
                        El dataset está "saneado" (sin etiquetas demográficas). Ahora ejecutamos la simulación para ver si el modelo todavía funciona.
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
                            ▶️ CLIC PARA ARREGLAR EL MODELO CON DATASET REPARADO
                        </summary>

                        <div style="margin-top:24px; animation: fadeIn 0.6s ease-in-out;">

                            <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:20px; background:rgba(0,0,0,0.02);">

                                <div style="text-align:center; padding:10px; border-right:1px solid var(--border-color-primary);">
                                    <div style="font-size:2.2rem; font-weight:800; color:#ef4444;">📉 78%</div>
                                    <div style="font-weight:bold; font-size:0.9rem; text-transform:uppercase; color:var(--body-text-color-subdued); margin-bottom:6px;">Precisión (COLAPSADA)</div>
                                    <div style="font-size:0.9rem; line-height:1.4;">
                                        <strong>Diagnóstico:</strong> El modelo ha perdido sus "atajos" (como el Código Postal). Está confundido y tiene problemas para predecir el riesgo con precisión.
                                    </div>
                                </div>

                                <div style="text-align:center; padding:10px;">
                                    <div style="font-size:2.2rem; font-weight:800; color:#f59e0b;">🧩 FALTAN</div>
                                    <div style="font-weight:bold; font-size:0.9rem; text-transform:uppercase; color:var(--body-text-color-subdued); margin-bottom:6px;">Datos Significativos</div>
                                    <div style="font-size:0.9rem; line-height:1.4;">
                                        <strong>Diagnóstico:</strong> Hemos limpiado los datos malos, pero no los hemos reemplazado por <strong>Datos Significativos</strong>. El modelo necesita mejores señales para aprender.
                                    </div>
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:20px; border-left:4px solid var(--color-accent);">
                                <div style="font-weight:700; font-size:1.05rem;">💡 El Pivote de Ingeniería</div>
                                <p style="margin:6px 0 0 0;">
                                    Un modelo que no sabe <em>nada</em> es justo, pero inútil.
                                    Para arreglar la precisión con seguridad, debemos dejar de eliminar y comenzar a <strong>encontrar patrones válidos</strong>: datos significativos que expliquen <em>por qué</em> ocurre el delito.
                                </p>
                            </div>


                    </details>

                          <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓN REQUERIDA: Encontrar Datos Significativos
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Responde la pregunta a continuación para recibir Puntos de Brújula Moral.
                            Luego haz clic en <strong>Siguiente</strong> para continuar arreglando el modelo.
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
        "title": "Protocolo 2: Validez Causal",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(16, 185, 129, 0.1); border:2px solid #10b981; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🔗</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#10b981; letter-spacing:0.05em;">
                                PROTOCOLO 2: CAUSA VS. CORRELACIÓN
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Misión: Aprender a distinguir cuándo un patrón <strong>causa realmente</strong> un resultado — y cuándo es solo una coincidencia.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#10b981;">PASO 1 DE 2</div>
                            <div style="height:4px; width:60px; background:rgba(16, 185, 129, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:#10b981; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🧠 La Trampa de "Pie Grande": Cuando la Correlación Te Engaña
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        Para mejorar un modelo, a menudo añadimos más datos.
                        <br>
                        Pero aquí está el problema: el modelo encuentra <strong>Correlaciones</strong> (una relación entre dos variables de datos) y asume erróneamente que una <strong>Causa</strong> la otra.
                        <br>
                        Considera este patrón estadístico real:
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding:20px; border:2px solid #ef4444; background:rgba(239, 68, 68, 0.1);">
                        <div style="font-size:3rem; margin-bottom:10px;">🦶 📈 📖</div>
                        <h3 style="margin:0; color:#ef4444;">
                            El Dato: "La gente con pies más grandes tiene mejores puntuaciones de lectura."
                        </h3>
                        <p style="font-size:1.0rem; margin-top:8px; color:var(--body-text-color);">
                            En promedio, la gente con <strong>pies grandes</strong> obtiene puntuaciones mucho más altas en tests de lectura que la gente con <strong>pies pequeños</strong>.
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
                            🤔 ¿Por qué pasa esto? (Haz clic para revelar)
                        </summary>

                        <div style="margin-top:20px; animation: fadeIn 0.5s ease-in-out;">
                            
                            <div class="hint-box" style="border-left:4px solid #16a34a; background:rgba(22, 163, 74, 0.1);">
                                <div style="font-weight:800; font-size:1.1rem; color:#16a34a;">
                                    La Tercera Variable Oculta: EDAD
                                </div>
                                <p style="margin-top:8px; color:var(--body-text-color);">
                                    ¿Tener los pies más grandes <em>causa</em> que la gente lea mejor? <strong>No.</strong>
                                    <br>
                                    Los niños tienen pies más pequeños y aún están aprendiendo a leer.
                                    <br>
                                    Los adultos tienen pies más grandes y han tenido muchos más años de práctica lectora.
                                </p>
                                <p style="margin-bottom:0; color:var(--body-text-color);">
                                    <strong>La Idea Clave:</strong> La edad causa <em>ambas cosas</em>: el tamaño del pie y la capacidad lectora.
                                    <br>
                                    La talla de zapatos es una <em>señal correlacionada</em>, no una causa.
                                </p>
                            </div>

                            <p style="font-size:1.05rem; text-align:center; margin-top:20px;">
                                <strong>Por qué esto importa:</strong>
                                <br>
                                En muchos datasets reales, algunas variables parecen predictivas solo porque están vinculadas a causas más profundas.
                                <br>
                                Los buenos modelos se centran en <strong>lo que realmente causa los resultados</strong>, no solo en lo que sucede al mismo tiempo.
                            </p>
                        </div>
                    </details>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓN REQUERIDA: ¿Puedes detectar la siguiente trampa de "Pie Grande" en los datos a continuación?
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Responde esta pregunta para aumentar tu puntuación de Brújula Moral.
                            Luego haz clic en <strong>Siguiente</strong> para continuar arreglando el modelo.
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
        "title": "Protocolo 2: Causa vs. Correlación",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(16, 185, 129, 0.1); border:2px solid #10b981; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🔗</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#10b981; letter-spacing:0.05em;">
                                PROTOCOLO 2: CAUSA VS. CORRELACIÓN
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Misión: Eliminar variables que <strong>correlacionan</strong> con los resultados pero no los <strong>causan</strong>.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#10b981;">PASO 2 DE 2</div>
                            <div style="height:4px; width:60px; background:rgba(16, 185, 129, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:#10b981; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🔬 Verificación de Investigación: Eligiendo Características Justas
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        Estás listo para continuar construyendo una versión más justa del modelo. Aquí hay cuatro variables a considerar.
                        <br>
                        Usa la regla a continuación para descubrir qué variables representan <strong>causas reales</strong> de comportamiento — y cuáles son solo correlaciones circunstanciales.
                    </p>

                    <div class="hint-box" style="border-left:4px solid var(--color-accent); background:var(--background-fill-secondary); border:1px solid var(--border-color-primary);">
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                            <div style="font-size:1.2rem;">📋</div>
                            <div style="font-weight:800; color:var(--color-accent); text-transform:uppercase; letter-spacing:0.05em;">
                                La Regla de Ingeniería
                            </div>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                            
                            <div style="padding:10px; background:rgba(239, 68, 68, 0.1); border-radius:6px; border:1px solid rgba(239, 68, 68, 0.3);">
                                <div style="font-weight:700; color:#ef4444; font-size:0.9rem; margin-bottom:4px;">
                                    🚫 RECHAZAR: ENTORNO
                                </div>
                                <div style="font-size:0.85rem; line-height:1.4; color:var(--body-text-color);">
                                    Variables que describen la situación o entorno de una persona (ej: riqueza, vecindario).
                                    <br><strong>Estas correlacionan con el delito pero no lo causan.</strong>
                                </div>
                            </div>
                            
                            <div style="padding:10px; background:rgba(22, 163, 74, 0.1); border-radius:6px; border:1px solid rgba(22, 163, 74, 0.3);">
                                <div style="font-weight:700; color:#16a34a; font-size:0.9rem; margin-bottom:4px;">
                                    ✅ MANTENER: CONDUCTA
                                </div>
                                <div style="font-size:0.85rem; line-height:1.4; color:var(--body-text-color);">
                                    Variables que describen acciones documentadas tomadas por la persona (ej: incomparecencia judicial).
                                    <br><strong>Estas reflejan comportamiento real.</strong>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="ai-risk-container" style="margin-top:20px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary);">
                        <h4 style="margin:0 0 12px 0; color:var(--body-text-color); text-align:center; font-size:1.1rem;">📂 Candidatos de Datos de Entrada</h4>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Estado Laboral</div>
                                <div style="font-size:0.85rem; background:var(--background-fill-secondary); padding:4px 8px; border-radius:4px; color:var(--body-text-color); display:inline-block;">
                                    Categoría: <strong>Condición de Entorno</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Condenas Previas</div>
                                <div style="font-size:0.85rem; background:rgba(22, 163, 74, 0.1); padding:4px 8px; border-radius:4px; color:#16a34a; display:inline-block;">
                                    Categoría: <strong>Historial de Conducta</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Puntuación del Vecindario</div>
                                <div style="font-size:0.85rem; background:var(--background-fill-secondary); padding:4px 8px; border-radius:4px; color:var(--body-text-color); display:inline-block;">
                                    Categoría: <strong>Entorno</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Incomparecencia</div>
                                <div style="font-size:0.85rem; background:rgba(22, 163, 74, 0.1); padding:4px 8px; border-radius:4px; color:#16a34a; display:inline-block;">
                                    Categoría: <strong>Historial de Conducta</strong>
                                </div>
                            </div>

                        </div>
                    </div>

                    <div class="hint-box" style="margin-top:20px; border-left:4px solid #8b5cf6; background:linear-gradient(to right, rgba(139, 92, 246, 0.05), var(--background-fill-primary)); color:var(--body-text-color);">
                        <div style="font-weight:700; color:#8b5cf6; font-size:1.05rem;">💡 Por qué esto importa para la Equidad</div>
                        <p style="margin:8px 0 0 0; font-size:0.95rem; line-height:1.5;">
                            Cuando una IA juzga a las personas basándose en <strong>Correlaciones</strong> (como el vecindario o la pobreza), las castiga por sus <strong>circunstancias</strong>—cosas que a menudo no pueden controlar.
                            <br><br>
                            Cuando una IA juzga basándose en <strong>Causas</strong> (como la Conducta), las hace responsables de sus <strong>acciones</strong>.
                            <br>
                            <strong>Equidad Real = Ser juzgado por tus elecciones, no por tu entorno.</strong>
                        </p>
                    </div>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓN REQUERIDA: 
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Selecciona las variables que representan <strong>Conducta</strong> real para construir el modelo justo.
                            Luego haz clic en <strong>Siguiente</strong> para continuar arreglando el modelo.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 6,
        "title": "Protocolo 3: La Representación Importa",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(139, 92, 246, 0.1); border:2px solid #8b5cf6; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🌍</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#7c3aed; letter-spacing:0.05em;">
                                PROTOCOLO 3: REPRESENTACIÓN
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Misión: Asegurarse de que los datos de entrenamiento coinciden con el lugar donde se utilizará el modelo.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#7c3aed;">PASO 1 DE 2</div>
                            <div style="height:4px; width:60px; background:rgba(139, 92, 246, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:#8b5cf6; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🗺️ El Problema del "Mapa Incorrecto"
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:820px; margin:0 auto 15px auto;">
                        Hemos arreglado las <strong>variables</strong> (las columnas). Ahora debemos comprobar el <strong>entorno</strong> (las filas).
                    </p>

                    <div style="background:var(--background-fill-secondary); border:2px dashed #94a3b8; border-radius:12px; padding:20px; text-align:center; margin-bottom:25px;">
                        <div style="font-weight:700; color:#64748b; font-size:0.9rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">EL ESCENARIO</div>
                        <p style="font-size:1.15rem; font-weight:600; color:var(--body-text-color); margin:0; line-height:1.5;">
                            Este dataset se construyó utilizando datos históricos del <span style="color:#ef4444;">Condado de Broward, Florida (EE. UU.)</span>.
                            <br><br>
                            Imagina tomar este modelo de Florida y forzarlo a juzgar personas en un sistema judicial completamente diferente—como <span style="color:#3b82f6;">Barcelona</span> (o tu propia ciudad).
                        </p>
                    </div>

                    <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">

                        <div class="hint-box" style="margin:0; border-left:4px solid #ef4444; background:rgba(239, 68, 68, 0.1);">
                            <div style="font-weight:800; color:#ef4444; margin-bottom:6px;">
                                🇺🇸 EL ORIGEN: FLORIDA
                            </div>
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color);">
                                Contexto de Entrenamiento: Sistema Judicial EE. UU.
                            </div>
                            <ul style="font-size:0.85rem; margin-top:8px; padding-left:16px; line-height:1.4; color:var(--body-text-color);">
                                <li><strong>Categorías demográficas:</strong> Definidas usando etiquetas y agrupaciones específicas de EE. UU.</li>
                                <li><strong>Crimen y ley:</strong> Leyes y procesos judiciales diferentes (por ejemplo, reglas de fianza).</li>
                                <li><strong>Geografía:</strong> Ciudades centradas en el coche y expansión suburbana.</li>
                            </ul>
                        </div>

                        <div class="hint-box" style="margin:0; border-left:4px solid #3b82f6; background:rgba(59, 130, 246, 0.1);">
                            <div style="font-weight:800; color:#3b82f6; margin-bottom:6px;">
                                📍 EL OBJETIVO: BARCELONA
                            </div>
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color);">
                                Contexto de Despliegue: Sistema Judicial UE
                            </div>
                            <ul style="font-size:0.85rem; margin-top:8px; padding-left:16px; line-height:1.4; color:var(--body-text-color);">
                                <li><strong>Categorías demográficas:</strong> Definidas diferente que en los datasets de EE. UU.</li>
                                <li><strong>Crimen y ley:</strong> Reglas legales diferentes, prácticas policiales y tipos de delitos comunes.</li>
                                <li><strong>Geografía:</strong> Entorno urbano denso y transitable.</li>
                            </ul>
                        </div>
                    </div>

                    <div class="hint-box" style="border-left:4px solid #8b5cf6; background:transparent;">
                        <div style="font-weight:700; color:#8b5cf6;">
                            Por qué esto falla
                        </div>
                        <p style="margin-top:6px;">
                            El modelo aprendió patrones de Florida.
                            <br>
                            Cuando el entorno del mundo real es diferente, el modelo puede cometer <strong>más errores</strong> — y esos errores pueden ser <strong>desiguales entre grupos</strong>.
                            <br>
                            En equipos de ingeniería de IA, a esto se le llama un <strong>desplazamiento del dataset (o dominio)</strong>.
                            <br>
                            Es como intentar encontrar la Sagrada Familia usando un mapa de Miami.
                        </p>
                    </div>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓN REQUERIDA:
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Responde la pregunta a continuación para aumentar tu puntuación de Brújula Moral.
                            Luego haz clic en <strong>Siguiente</strong> para continuar arreglando el problema de representación de datos.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 7: THE DATA SWAP ---
    {
        "id": 7,
        "title": "Protocolo 3: Arreglando la Representación",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(139, 92, 246, 0.1); border:2px solid #8b5cf6; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🌍</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#7c3aed; letter-spacing:0.05em;">PROTOCOLO 3: REPRESENTACIÓN</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Misión: Reemplazar "Datos Atajo" con "Datos Locales".</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#7c3aed;">PASO 2 DE 2</div>
                            <div style="height:4px; width:60px; background:rgba(139, 92, 246, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:#8b5cf6; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">🔄 El Intercambio de Datos</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        No podemos usar el dataset de Florida. Son <strong>"Datos Atajo"</strong>—elegidos solo porque eran fáciles de encontrar.
                        <br>
                        Para construir un modelo justo para <strong>Cualquier Ubicación</strong> (sea Barcelona, Berlín o Boston), debemos rechazar el camino fácil.
                        <br>
                        Debemos recopilar <strong>Datos Locales</strong> que reflejen la realidad real de ese lugar.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; border:2px solid #ef4444; background:rgba(239, 68, 68, 0.1); padding:16px; margin-bottom:20px;">
                        <div style="font-weight:800; color:#ef4444; font-size:1.1rem; margin-bottom:8px;">⚠️ DATASET ACTUAL: FLORIDA (INVÁLIDO)</div>

                        <p style="font-size:0.9rem; margin:0; color:var(--body-text-color);">
                            El dataset no coincide con el contexto local donde se usará el modelo.
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
                            🔄 CLIC PARA IMPORTAR DATOS LOCALES DE BARCELONA
                        </summary>

                        <div style="margin-top:24px; animation: fadeIn 0.6s ease-in-out;">

                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">
                                <div style="padding:12px; border:1px solid #22c55e; background:rgba(34, 197, 94, 0.1); border-radius:8px; text-align:center;">
                                    <div style="font-size:2rem;">📍</div>
                                    <div style="font-weight:700; color:#22c55e; font-size:0.9rem;">GEOGRAFÍA COINCIDENTE</div>
                                    <div style="font-size:0.8rem; color:var(--body-text-color);">Fuente de datos: Dept. de Justicia Local</div>
                                </div>
                                <div style="padding:12px; border:1px solid #22c55e; background:rgba(34, 197, 94, 0.1); border-radius:8px; text-align:center;">
                                    <div style="font-size:2rem;">⚖️</div>
                                    <div style="font-weight:700; color:#22c55e; font-size:0.9rem;">LEYES SINCRONIZADAS</div>
                                    <div style="font-size:0.8rem; color:var(--body-text-color);">Eliminados delitos específicos de EE. UU.</div>
                                </div>
                            </div>

                            <div class="hint-box" style="border-left:4px solid #22c55e;">
                                <div style="font-weight:700; color:#15803d;">Actualización del Sistema Completada</div>
                                <p style="margin-top:6px;">
                                    El modelo ahora está aprendiendo de la gente a la que realmente afectará. La precisión ahora es significativa porque refleja la verdad local.
                                </p>
                            </div>

                        </div>
                    </details>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACCIÓN REQUERIDA:
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Responde la pregunta a continuación para aumentar tu puntuación de Brújula Moral.
                            Luego haz clic en <strong>Siguiente</strong> para revisar y certificar que el modelo está arreglado!
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
        "title": "Informe Final de Equidad",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🏁</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#15803d; letter-spacing:0.05em;">AUDITORÍA COMPLETADA</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Estado del Sistema: LISTO PARA CERTIFICACIÓN.</div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">📊 El Informe "Antes y Después"</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        Has saneado los datos con éxito, filtrado por causalidad y localizado el contexto.
                        <br>Comparemos tu nuevo modelo con el modelo original para revisar qué ha cambiado.
                    </p>

                    <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">

                        <div>
                            <div style="font-weight:800; color:#ef4444; margin-bottom:8px; text-transform:uppercase;">🚫 El Modelo Original</div>

                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">ENTRADAS</div>
                                <div style="color:var(--body-text-color);">Raza, Género, Código Postal</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">LÓGICA</div>
                                <div style="color:var(--body-text-color);">Estatus y Estereotipos</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">CONTEXTO</div>
                                <div style="color:var(--body-text-color);">Florida (Mapa Equivocado)</div>
                            </div>
                            <div style="padding:10px; background:rgba(239, 68, 68, 0.2); margin-top:10px; border-radius:6px; color:#ef4444; font-weight:700; text-align:center;">
                                RIESGO DE SESGO: CRÍTICO
                            </div>
                        </div>

                        <div style="transform:scale(1.02); box-shadow:0 4px 12px rgba(0,0,0,0.1); border:2px solid #22c55e; border-radius:8px; overflow:hidden;">
                            <div style="background:#22c55e; color:white; padding:6px; font-weight:800; text-align:center; text-transform:uppercase;">✅ Tu Modelo Diseñado</div>

                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">ENTRADAS</div>
                                <div style="color:var(--body-text-color);">Solo Comportamiento</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">LÓGICA</div>
                                <div style="color:var(--body-text-color);">Conducta Causal</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">CONTEXTO</div>
                                <div style="color:var(--body-text-color);">Barcelona (Local)</div>
                            </div>
                            <div style="padding:10px; background:rgba(34, 197, 94, 0.2); margin-top:0; color:#15803d; font-weight:700; text-align:center;">
                                RIESGO DE SESGO: MINIMIZADO
                            </div>
                        </div>
                    </div>

                    <div class="hint-box" style="border-left:4px solid #f59e0b;">
                        <div style="font-weight:700; color:#b45309;">🚧 Una Nota sobre la "Perfección"</div>
                        <p style="margin-top:6px;">
                            ¿Es este modelo perfecto? <strong>No.</strong>
                            <br>Los datos del mundo real (como las detenciones) aún pueden tener sesgos ocultos de la historia humana.
                            Pero has pasado de un sistema que <em>amplifica</em> el prejuicio a uno que <em>mide la equidad</em> utilizando Conducta y Contexto Local.
                        </p>
                    </div>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ¡CASI TERMINADO!
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Responde la pregunta a continuación para aumentar tu Puntuación de Brújula Moral.
                            <br>
                            Haz clic en <strong>Siguiente</strong> para completar las aprobaciones finales del modelo y certificarlo.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 9: CERTIFICATION ---
    {
        "id": 9,
        "title": "Protocolo Completo: Ética Asegurada",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title" style="margin-bottom:10px; color:#15803d;">🚀 ARQUITECTURA ÉTICA VERIFICADA</h2>
                        <p style="font-size:1.1rem; max-width:700px; margin:0 auto; color:var(--body-text-color);">
                            Has refactorizado la IA con éxito. Ya no depende de <strong>proxies ocultos y atajos injustos</strong>—ahora es una herramienta transparente construida sobre principios justos.
                        </p>
                    </div>
                    
                    <div class="ai-risk-container" style="background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; padding:25px; border-radius:12px; box-shadow:0 4px 20px rgba(34, 197, 94, 0.15);">
                        
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #bbf7d0; padding-bottom:15px; margin-bottom:20px;">
                            <div style="font-weight:900; font-size:1.3rem; color:#15803d; letter-spacing:0.05em;">DIAGNÓSTICO DEL SISTEMA</div>
                            <div style="background:#22c55e; color:white; font-weight:800; padding:6px 12px; border-radius:6px;">SEGURIDAD: 100%</div>
                        </div>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">ENTRADAS</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Saneadas</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">LÓGICA</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Causal</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">CONTEXTO</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Localizado</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">ESTADO</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Ético</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top:30px; padding:20px; background:rgba(245, 158, 11, 0.1); border:2px solid #fcd34d; border-radius:12px;">
                        <div style="display:flex; gap:15px;">
                            <div style="font-size:2.5rem;">🎓</div>
                            <div>
                                <h3 style="margin:0; color:#b45309;">Siguiente Objetivo: Certificación y Rendimiento</h3>
                                <p style="font-size:1.05rem; line-height:1.5; color:var(--body-text-color); margin-top:8px;">
                                    Ahora que has hecho tu modelo <strong>ético</strong>, puedes continuar mejorando la <strong>precisión</strong> del modelo en la actividad final de abajo.
                                    <br><br>
                                    Pero antes de optimizar la potencia, debes asegurar tus credenciales.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:25px;">
                        <p style="font-size:1.1rem; font-weight:600; color:var(--body-text-color); margin-bottom:15px;">
                            ⬇️ <strong>Paso Siguiente Inmediato</strong> ⬇️
                        </p>
                        
                        <div style="display:inline-block; padding:15px 30px; background:linear-gradient(to right, #f59e0b, #d97706); border-radius:50px; color:white; font-weight:800; font-size:1.1rem; box-shadow:0 4px 15px rgba(245, 158, 11, 0.4);">
                            Reclama tu Certificado oficial "Ethics at Play" en la siguiente actividad.
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
        "q": "Acción: Selecciona las variables que deben borrarse inmediatamente porque son Clases Protegidas.",
        "o": [
            "A) Código Postal y Vecindario",
            "B) Raza, Género, Edad",
            "C) Condenas Previas",
        ],
        "a": "B) Raza, Género, Edad",
        "success": "Tarea Completada. Columnas eliminadas. El modelo ahora es ciego a datos demográficos explícitos.",
    },
    2: {
        "t": "t13",
        "q": "¿Por qué debemos eliminar también el 'Código Postal' si ya hemos eliminado la 'Raza'?",
        "o": [
            "A) Porque los Códigos Postales ocupan demasiada memoria.",
            "B) Es una Variable Proxy que reintroduce el sesgo racial debido a la segregación histórica.",
            "C) Los Códigos Postales no son precisos.",
        ],
        "a": "B) Es una Variable Proxy que reintroduce el sesgo racial debido a la segregación histórica.",
        "success": "Proxy Identificado. Datos de ubicación eliminados para prevenir el sesgo de segregación.",
    },
    3: {
        "t": "t14",
        "q": "Después de eliminar Raza y Código Postal, el modelo es justo pero la precisión ha caído. ¿Por qué?",
        "o": [
            "A) El modelo está roto.",
            "B) Un modelo que no sabe nada es justo pero inútil. Necesitamos mejores datos, no solo menos datos.",
            "C) Deberíamos volver a poner la columna de Raza.",
        ],
        "a": "B) Un modelo que no sabe nada es justo pero inútil. Necesitamos mejores datos, no solo menos datos.",
        "success": "Giro Confirmado. Debemos pasar de 'Eliminar' a 'Seleccionar' mejores características.",
    },
    4: {
        "t": "t15",
        "q": "Basado en el ejemplo de “Pie Grande”, ¿por qué puede ser engañoso dejar que una IA dependa de variables como la talla de zapatos?",
        "o": [
            "A) Porque son físicamente difíciles de medir.",
            "B) Porque a menudo solo se correlacionan con resultados y son causadas por un tercer factor oculto, en lugar de causar el resultado ellas mismas."
        ],
        "a": "B) Porque a menudo solo se correlacionan con resultados y son causadas por un tercer factor oculto, en lugar de causar el resultado ellas mismas.",
        "success": "Filtro Calibrado. Ahora estás comprobando si un patrón es causado por una tercera variable oculta — no confundiendo correlación con causalidad."
    },

    5: {
        "t": "t16",
        "q": "¿Cuál de estas características restantes es un Predictor Causal Válido de conducta criminal?",
        "o": [
            "A) Empleo (Condición de Entorno)",
            "B) Estado Civil (Estilo de vida)",
            "C) Incomparecencia ante el Tribunal (Conducta)",
        ],
        "a": "C) Incomparecencia ante el Tribunal (Conducta)",
        "success": "Característica Seleccionada. 'Incomparecencia' refleja una acción específica relevante para el riesgo de fuga.",
    },
    6: {
        "t": "t17",
        "q": "¿Por qué un modelo entrenado en Florida puede hacer predicciones poco fiables cuando se usa en Barcelona?",
        "o": [
            "A) Porque el software está en inglés y debe traducirse.",
            "B) Desajuste de contexto: el modelo aprendió patrones ligados a leyes, sistemas y entornos de EE. UU. que no coinciden con la realidad de Barcelona.",
            "C) Porque el número de personas en Barcelona es diferente del tamaño del dataset de entrenamiento."
        ],
        "a": "B) Desajuste de contexto: el modelo aprendió patrones ligados a leyes, sistemas y entornos de EE. UU. que no coinciden con la realidad de Barcelona.",
        "success": "¡Correcto! Esto es un desplazamiento de dataset (o dominio). Cuando los datos de entrenamiento no coinciden con dónde se usa un modelo, las predicciones se vuelven menos precisas y pueden fallar de manera desigual entre grupos."
    },

    7: {
        "t": "t18",
        "q": "Acabas de rechazar un dataset masivo y gratuito (Florida) por uno más pequeño y difícil de conseguir (Localmente relevante). ¿Por qué ha sido la elección de ingeniería correcta?",
        "o": [
            "A) No lo era. Más datos siempre es mejor, independientemente de dónde vengan.",
            "B) Porque la 'Relevancia' es más importante que el 'Volumen'. Un mapa pequeño y preciso es mejor que un mapa enorme y equivocado.",
            "C) Porque el dataset de Florida era demasiado caro.",
        ],
        "a": "B) Porque la 'Relevancia' es más importante que el 'Volumen'. Un mapa pequeño y preciso es mejor que un mapa enorme y equivocado.",
        "success": "¡Taller Completado! Has auditado, filtrado y localizado el modelo de IA con éxito.",
    },
    8: {
        "t": "t19",
        "q": "Has arreglado las Entradas, la Lógica y el Contexto. ¿Tu nuevo modelo es ahora 100% perfectamente justo?",
        "o": [
            "A) Sí. Las matemáticas son objetivas, así que si los datos están limpios, el modelo es perfecto.",
            "B) No. Es más seguro porque hemos priorizado 'Conducta' sobre 'Estatus' y 'Realidad Local' sobre 'Datos Fáciles', pero siempre debemos estar vigilantes.",
        ],
        "a": "B) No. Es más seguro porque hemos priorizado 'Conducta' sobre 'Estatus' y 'Realidad Local' sobre 'Datos Fáciles', pero siempre debemos estar vigilantes.",
        "success": "Buen trabajo. A continuación puedes revisar oficialmente este modelo para su uso.",
    },
    9: {
        "t": "t20",
        "q": "Has saneado entradas, filtrado por causalidad y reponderado por representación. ¿Estás listo para aprobar este sistema de IA reparado?",
        "o": [
            "A) Sí, el modelo ahora es seguro y autorizo el uso de este sistema de IA reparado.",
            "B) No, espera un modelo perfecto.",
        ],
        "a": "A) Sí, el modelo ahora es seguro y autorizo el uso de este sistema de IA reparado.",
        "success": "Misión Conseguida. Has diseñado un sistema más seguro y justo.",
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
    else:
        header_emoji = "✅"
        header_title = "Progreso Registrado"
        summary_line = "Tu perspectiva ética aumentó tu Puntuación de Brújula Moral."
        cta_line = "Prueba el siguiente escenario para alcanzar el próximo nivel."

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

# --- 9. APP FACTORY (FAIRNESS FIXER) ---
def create_fairness_fixer_es_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

        # --- TOP ANCHOR & LOADING OVERLAY ---
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Cargando...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>🕵️‍♀️ Autenticando...</h2>"
                "<p>Sincronizando Perfil de Ingeniero de Equidad...</p>"
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
                            "<span class='points-chip'>🧭 Puntos de Brújula Moral disponibles</span>"
                            "<span>Responde para mejorar tu puntuación</span>"
                            "</div>"
                        )

                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Selecciona una Acción:",
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
                            else "🎉 ¡Modelo autorizado! Desplázate hacia abajo para recibir tu certificado oficial de 'Ethics at Play'."
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
                            "<div class='hint-box' style='border-color:red;'>❌ Incorrecto. Inténtalo de nuevo.</div>",
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
                "<div class='hint-box'>⚠️ Error de Autenticación. Por favor, inicia desde el enlace del curso.</div>",
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
                    js=nav_js(prev_target_id, "Cargando..."),
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
                    js=nav_js(next_target_id, "Cargando..."),
                ).then(
                    fn=make_nav_generator(curr_col, next_col),
                    outputs=[curr_col, next_col],
                )

    return demo

# --- 10. LAUNCHER ---
def launch_fairness_fixer_es_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    app = create_fairness_fixer_es_app(theme_primary_hue=theme_primary_hue)
    app.launch(share=share, server_name=server_name,
               server_port=server_port,
               **kwargs)

if __name__ == "__main__":
    launch_fairness_fixer_es_app(share=False, debug=True, height=1000)

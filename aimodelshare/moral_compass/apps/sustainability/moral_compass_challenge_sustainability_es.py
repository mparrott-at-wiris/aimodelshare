import gradio as gr
import os
import time
import threading
import pandas as pd
from typing import Optional, Dict, Any, Tuple

try:
    from aimodelshare.playground import Competition
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    pass

# --- Configuration ---
LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None

# --- Cache ---
_cache_lock = threading.Lock()
_leaderboard_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}

# --- HTML Template ---
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Actividad 5: El Coste de la Sostenibilidad</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        /* Dark Mode (Default) - Matches Activity 1 & 2 styles */
        :root {
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.8);
            --accent: #f59e0b;
            /* Amber/Orange for Caution/Energy */
            --accent-glow: rgba(245, 158, 11, 0.3);
            --success: #10b981;
            --warning: #ef4444;
            /* Red for alert */
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --bg-gradient-1: rgba(245, 158, 11, 0.05);
            --bg-gradient-2: rgba(239, 68, 68, 0.05);
            --card-shadow: rgba(0, 0, 0, 0.5);
            --border-color: rgba(255, 255, 255, 0.1);
            --input-bg: rgba(255, 255, 255, 0.05);
            --input-border: rgba(255, 255, 255, 0.1);
            --hover-bg: rgba(255, 255, 255, 0.08);
            --progress-line: rgba(255, 255, 255, 0.1);
            --step-border: rgba(255, 255, 255, 0.2);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            min-height: 100vh;
            background-image:
                radial-gradient(circle at 10% 20%, var(--bg-gradient-1) 0%, transparent 20%),
                radial-gradient(circle at 90% 80%, var(--bg-gradient-2) 0%, transparent 20%);
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        /* PROGRESS BAR */
        .mission-progress {
            display: flex;
            justify-content: space-between;
            margin-bottom: 40px;
            position: relative;
        }

        .mission-progress::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--progress-line);
            z-index: 1;
            transform: translateY(-50%);
        }

        .step-node {
            width: 35px;
            height: 35px;
            border-radius: 50%;
            background: var(--bg);
            border: 2px solid var(--step-border);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2;
            color: var(--text-dim);
            font-weight: 600;
            font-size: 0.875rem;
            transition: all 0.3s ease;
        }

        .step-node.active {
            border-color: var(--accent);
            color: var(--accent);
            box-shadow: 0 0 15px var(--accent-glow);
        }

        .step-node.completed {
            background: var(--success);
            border-color: var(--success);
            color: white;
        }

        /* CARDS & CONTENT */
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border-radius: 24px;
            padding: 40px;
            border: 1px solid var(--border-color);
            box-shadow: 0 25px 50px -12px var(--card-shadow);
            min-height: 500px;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
        }

        .mission-step {
            display: none;
            height: 100%;
            flex-direction: column;
            animation: fadeIn 0.6s ease;
        }

        .mission-step.active {
            display: flex;
        }

        h1,
        h2,
        h3 {
            font-weight: 800;
            margin-bottom: 20px;
            color: var(--text);
        }

        h1 {
            font-size: 2.2rem;
            letter-spacing: -1px;
            text-transform: uppercase;
        }

        h1.neon-text {
            color: var(--accent);
            text-shadow: 0 0 20px var(--accent-glow);
        }

        h2 {
            font-size: 1.8rem;
        }

        p {
            line-height: 1.6;
            color: var(--text-dim);
            margin-bottom: 20px;
            font-size: 1.125rem;
        }

        .highlight-text {
            color: var(--text);
            font-weight: 600;
        }

        .emph-harm {
            color: var(--warning);
            font-weight: 700;
        }

        /* BUTTONS */
        .btn-group {
            display: flex;
            gap: 15px;
            margin-top: auto;
            flex-wrap: wrap;
        }

        .btn {
            background: var(--accent);
            color: var(--bg);
            border: none;
            padding: 16px 28px;
            border-radius: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 1rem;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px var(--accent-glow);
        }

        .btn.secondary {
            background: var(--input-bg);
            color: var(--text);
            border: 1px solid var(--border-color);
        }

        .btn.secondary:hover {
            background: var(--hover-bg);
        }

        .btn.danger {
            background: var(--warning);
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
        }

        /* STAT CARDS */
        .stat-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 30px 0;
        }

        .stat-card {
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            padding: 20px;
            border-radius: 16px;
            text-align: center;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--success);
        }

        .stat-label {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-dim);
            margin-top: 5px;
        }

        /* GAUGE */
        .score-gauge-container {
            position: relative;
            width: 200px;
            height: 200px;
            margin: 0 auto 30px auto;
        }

        .score-gauge {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: conic-gradient(from 180deg, var(--success) 0%, var(--success) 100%, var(--border-color) 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 30px rgba(16, 185, 129, 0.2);
            transition: background 2s ease-in-out;
        }

        .score-gauge-inner {
            width: 80%;
            height: 80%;
            border-radius: 50%;
            background-color: var(--bg);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 2;
        }

        .gauge-value {
            font-size: 3rem;
            font-weight: 800;
            color: var(--text);
        }

        /* REVELATION STYLES */
        .revelation-box {
            border-left: 4px solid var(--accent);
            background: rgba(245, 158, 11, 0.1);
            padding: 20px;
            border-radius: 0 12px 12px 0;
            margin: 20px 0;
        }

        .energy-fact {
            display: flex;
            align-items: center;
            gap: 20px;
            margin: 15px 0;
            padding: 15px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }

        .energy-icon {
            font-size: 2rem;
        }

        /* FORMULA BOX */
        .formula-box {
            background: var(--input-bg);
            padding: 30px;
            border-radius: 16px;
            text-align: center;
            border: 2px dashed var(--accent);
            margin: 30px 0;
        }

        .formula-text {
            font-size: 1.5rem;
            font-weight: 700;
            margin: 15px 0;
            color: var(--text);
        }

        .formula-part {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 6px;
        }

        .part-acc {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
        }

        .part-sus {
            background: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes gaugeDrop {
            0% {
                background: conic-gradient(from 180deg, var(--success) 0%, var(--success) 100%, var(--border-color) 100%);
            }

            100% {
                background: conic-gradient(from 180deg, var(--warning) 0%, var(--warning) 0%, var(--border-color) 0%, var(--border-color) 100%);
            }
        }

        .gauge-dropping {
            animation: gaugeDrop 2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }

        .blink-red {
            animation: blinkRed 1s infinite;
        }

        @keyframes blinkRed {

            0%,
            100% {
                color: var(--text);
            }

            50% {
                color: var(--warning);
            }
        }

        /* Light Mode */
        @media (prefers-color-scheme: light) {
            :root {
                --bg: #f8fafc;
                --card-bg: rgba(255, 255, 255, 0.9);
                --accent: #d97706;
                --accent-glow: rgba(217, 119, 6, 0.2);
                --success: #059669;
                --warning: #dc2626;
                --text: #0f172a;
                --text-dim: #64748b;
                --bg-gradient-1: rgba(217, 119, 6, 0.05);
                --bg-gradient-2: rgba(220, 38, 38, 0.05);
                --card-shadow: rgba(0, 0, 0, 0.1);
                --border-color: rgba(0, 0, 0, 0.1);
                --input-bg: rgba(0, 0, 0, 0.03);
                --input-border: rgba(0, 0, 0, 0.1);
                --hover-bg: rgba(0, 0, 0, 0.05);
                --progress-line: rgba(0, 0, 0, 0.1);
                --step-border: rgba(0, 0, 0, 0.2);
            }
        }
    </style>
</head>

<body>
    <div class="container">
        <!-- PROGRESS -->
        <div class="mission-progress">
            <div class="step-node completed">1</div>
            <div class="step-node completed">2</div>
            <div class="step-node completed">3</div>
            <div class="step-node completed">4</div>
            <div class="step-node active">5</div>
            <div class="step-node">6</div>
        </div>

        <div class="card">

            <!-- STEP 1: CONGRATULATIONS -->
            <div class="mission-step active" id="step-1">
                <div style="text-align: center;">
                    <h2 style="color: var(--success); text-transform: uppercase; letter-spacing: 2px;">Entrenamiento del
                        Modelo Completado</h2>
                    <h1 class="neon-text" style="color: var(--success); text-shadow: 0 0 20px rgba(16, 185, 129, 0.4);">
                        &iexcl;Precisi&oacute;n Excepcional!</h1>
                </div>

                <p style="text-align: center;">Tu modelo ha superado nuestros puntos de referencia. Has utilizado con
                    &eacute;xito el conjunto de datos NREL para predecir la eficiencia energ&eacute;tica de edificios.</p>

                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-value">94.2%</div>
                        <div class="stat-label">Precisi&oacute;n del Modelo</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">#3</div>
                        <div class="stat-label">Clasificaci&oacute;n Global</div>
                    </div>
                </div>

                <div class="revelation-box"
                    style="border-left-color: var(--success); background: rgba(16, 185, 129, 0.1);">
                    <p style="margin-bottom: 0; color: var(--text);"><strong>LOGRO DESBLOQUEADO:</strong> Has dominado
                        el aspecto t&eacute;cnico de la IA. Tu modelo realiza predicciones precisas que podr&iacute;an ahorrar dinero
                        y energ&iacute;a en el futuro.</p>
                </div>

                <div class="btn-group" style="justify-content: center;">
                    <button class="btn" style="width: 100%;" onclick="goToStep(2)">PUBLICAR MODELO Y CERTIFICAR</button>
                </div>
            </div>

            <!-- STEP 2: THE REVELATION -->
            <div class="mission-step" id="step-2">
                <h1 style="color: var(--warning);">PROYECCI&Oacute;N DETENIDA</h1>
                <p>Antes de poder certificar tu modelo, debemos auditar el <span class="highlight-text">coste oculto</span>
                    de tu proceso de entrenamiento.</p>

                <div style="background: rgba(255,255,255,0.05); border-radius: 16px; padding: 25px; margin: 20px 0;">
                    <h3 style="margin-bottom: 20px;">La Huella Invisible</h3>

                    <div class="energy-fact">
                        <div class="energy-icon">&#128267;</div>
                        <div>
                            <strong style="color: var(--text);">Consumo Masivo de Energ&iacute;a</strong>
                            <p style="margin: 0; font-size: 0.95rem;">Entrenar un solo modelo grande de IA puede consumir
                                tanta electricidad como <strong>la que usan 100 hogares en un a&ntilde;o</strong>.</p>
                        </div>
                    </div>

                    <div class="energy-fact">
                        <div class="energy-icon">&#9729;&#65039;</div>
                        <div>
                            <strong style="color: var(--text);">Emisiones de Carbono</strong>
                            <p style="margin: 0; font-size: 0.95rem;">Los grandes modelos de IA como GPT-4 pueden generar CO2
                                equivalente a <strong>conducir un coche de un extremo a otro del pa&iacute;s</strong> durante el entrenamiento.
                                Incluso los modelos m&aacute;s peque&ntilde;os tienen una huella medible.</p>
                        </div>
                    </div>

                    <div class="energy-fact">
                        <div class="energy-icon">&#128167;</div>
                        <div>
                            <strong style="color: var(--text);">Consumo de Agua</strong>
                            <p style="margin: 0; font-size: 0.95rem;">Los centros de datos evaporan millones de litros de agua
                                para refrigerar los servidores que entrenan tu IA.</p>
                        </div>
                    </div>
                </div>

                <p class="emph-harm">No podemos resolver la crisis clim&aacute;tica con herramientas que la empeoran.</p>

                <div class="btn-group">
                    <button class="btn secondary" onclick="goToStep(1)">ATR&Aacute;S</button>
                    <button class="btn danger" onclick="goToStep(3)">RECONOCER EL IMPACTO</button>
                </div>
            </div>

            <!-- STEP 3: THE RESET -->
            <div class="mission-step" id="step-3">
                <div style="text-align: center; margin-top: 40px;">
                    <h2 class="blink-red">RECALCULANDO PUNTUACI&Oacute;N...</h2>

                    <div class="score-gauge-container">
                        <div class="score-gauge" id="mainGauge">
                            <div class="score-gauge-inner">
                                <div class="gauge-value" id="scoreValue">94</div>
                                <div class="stat-label">PUNTUACI&Oacute;N</div>
                            </div>
                        </div>
                    </div>

                    <div id="resetMessage" style="opacity: 0; transition: opacity 1s;">
                        <h3 style="color: var(--warning);">FACTOR DE SOSTENIBILIDAD: A&Uacute;N NO MEDIDO</h3>
                        <p>Tu precisi&oacute;n se mantiene, pero tu <strong>puntuaci&oacute;n total</strong> ahora incluye un componente de sostenibilidad.</p>
                        <p>Hasta que demuestres pr&aacute;cticas sostenibles, ese componente es <strong>cero</strong> &mdash; arrastrando tu total hacia abajo.</p>
                    </div>
                </div>

                <div class="btn-group" id="btnContinueReset"
                    style="justify-content: center; opacity: 0; pointer-events: none;">
                    <button class="btn" onclick="goToStep(4)">INTRODUCIR NUEVA M&Eacute;TRICA</button>
                </div>
            </div>

            <!-- STEP 4: THE NEW STANDARD -->
            <div class="mission-step" id="step-4">
                <h1 style="color: var(--accent);">La Br&uacute;jula Moral</h1>
                <p>A partir de ahora, ser&aacute;s evaluado con un nuevo est&aacute;ndar. No basta con ser inteligente; tu IA
                    debe ser <span class="highlight-text" style="color: var(--success);">Sostenible</span>.</p>

                <div class="formula-box">
                    <div
                        style="text-transform: uppercase; letter-spacing: 2px; color: var(--text-dim); margin-bottom: 10px;">
                        La Nueva F&oacute;rmula</div>
                    <div class="formula-text">
                        Puntuaci&oacute;n Total = <span class="formula-part part-acc">[ Precisi&oacute;n ]</span> x <span
                            class="formula-part part-sus">[ Sostenibilidad % ]</span>
                    </div>
                    <p style="font-size: 1rem; margin-top: 15px;">
                        Si tu Puntuaci&oacute;n de Sostenibilidad es <strong>0%</strong>, tu Puntuaci&oacute;n Total es <strong>0</strong>.
                    </p>
                </div>

                <div class="revelation-box"
                    style="background: rgba(16, 185, 129, 0.1); border-left-color: var(--success);">
                    <h3 style="color: var(--success); margin-bottom: 10px;">Actualizaci&oacute;n de tu Misi&oacute;n</h3>
                    <ul style="margin-left: 20px; line-height: 1.8;">
                        <li><strong>Paso 1:</strong> Medir la huella de carbono de tu modelo actual.</li>
                        <li><strong>Paso 2:</strong> Optimizar la arquitectura para reducir el consumo energ&eacute;tico.</li>
                        <li><strong>Paso 3:</strong> Mantener una alta precisi&oacute;n mientras se reducen las emisiones.</li>
                    </ul>
                </div>

                <div class="btn-group">
                    <button class="btn" style="width: 100%;" onclick="showTransition()">INICIAR AUDITOR&Iacute;A DE
                        SOSTENIBILIDAD</button>
                </div>
            </div>

        </div>
    </div>

    <div id="transitionOverlay"
        style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15, 23, 42, 0.95); backdrop-filter:blur(10px); z-index:999; flex-direction:column; align-items:center; justify-content:center; text-align:center;">
        <div style="font-size:4rem; margin-bottom:20px;">&#127793;</div>
        <h2 style="color:var(--success); font-size:2rem; margin-bottom:10px;">Actividad Completada</h2>
        <p style="color:var(--text); font-size:1.2rem; max-width:600px;">
            Has visto el coste oculto. <b>A continuaci&oacute;n:</b> Investigar&aacute;s la huella medioambiental completa de la IA &mdash; desde la pantalla de tu m&oacute;vil hasta la escala global &mdash; como Detective de IA Verde.
        </p>
        <button class="btn secondary" style="margin-top:40px;"
            onclick="document.getElementById('transitionOverlay').style.display='none'">CERRAR</button>
    </div>

    <script>
        function goToStep(step) {
            // Hide all steps
            document.querySelectorAll('.mission-step').forEach(el => el.classList.remove('active'));

            // Show target step
            const target = document.getElementById(`step-${step}`);
            if (target) target.classList.add('active');

            // Special logic for Step 3 (Animation)
            if (step === 3) {
                setTimeout(runResetAnimation, 500);
            }
        }

        function runResetAnimation() {
            const gauge = document.getElementById('mainGauge');
            const scoreVal = document.getElementById('scoreValue');
            const msg = document.getElementById('resetMessage');
            const btn = document.getElementById('btnContinueReset');

            // Add dropping class to gauge ring
            gauge.classList.add('gauge-dropping');

            // Animate number countdown
            let score = 94;
            const interval = setInterval(() => {
                score -= 2;
                if (score <= 0) {
                    score = 0;
                    clearInterval(interval);
                    // Show message
                    scoreVal.style.color = '#ef4444';
                    msg.style.opacity = '1';

                    // Show button
                    setTimeout(() => {
                        btn.style.opacity = '1';
                        btn.style.pointerEvents = 'all';
                    }, 1000);
                }
                scoreVal.textContent = score;
            }, 30);
        }

        function showTransition() {
            document.getElementById('transitionOverlay').style.display = 'flex';
            // Also try postMessage just in case
            try { window.parent.postMessage('activity_complete', '*'); } catch (e) { }
        }
    </script>
</body>

</html>
"""

def _fetch_leaderboard(token: str) -> Optional[pd.DataFrame]:
    now = time.time()
    with _cache_lock:
        if (
            _leaderboard_cache["data"] is not None
            and now - _leaderboard_cache["timestamp"] < LEADERBOARD_CACHE_SECONDS
        ):
            return _leaderboard_cache["data"]

    try:
        playground_id = "https://bhtrtkrbf4.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        df = playground.get_leaderboard(token=token)
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
    except Exception:
        df = None

    with _cache_lock:
        _leaderboard_cache["data"] = df
        _leaderboard_cache["timestamp"] = time.time()
    return df

def _compute_user_stats(username: str, token: str) -> Dict[str, Any]:
    leaderboard_df = _fetch_leaderboard(token)
    best_score = 0
    rank = None

    if leaderboard_df is not None and not leaderboard_df.empty:
        if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                best_score = user_submissions["accuracy"].max()

            # Rank
            user_bests = leaderboard_df.groupby("username")["accuracy"].max()
            summary_df = user_bests.reset_index().sort_values("accuracy", ascending=False).reset_index(drop=True)
            summary_df.index = summary_df.index + 1
            my_row = summary_df[summary_df["username"] == username]
            if not my_row.empty:
                rank = my_row.index[0]

    return {"best_score": best_score, "rank": rank}

def get_html_content(best_score_pct, rank_str, is_demo=False):
    score_int = int(best_score_pct)

    html = HTML_TEMPLATE

    # Replace static placeholders with dynamic values
    html = html.replace("94.2%", f"{best_score_pct:.1f}%")
    html = html.replace("#3", f"#{rank_str}")
    html = html.replace('id="scoreValue">94<', f'id="scoreValue">{score_int}<')
    html = html.replace('let score = 94;', f'let score = {score_int};')

    if is_demo:
        demo_banner = """<div style="background:rgba(251,191,36,0.15); border:2px solid #f59e0b; padding:12px; border-radius:8px; margin-bottom:20px; text-align:center;">
            <strong style="color:#d97706;">Modo Demo:</strong> <span style="color:var(--text-dim);">No se pudo cargar la puntuaci&oacute;n real de tu modelo. Se muestran valores de ejemplo.</span>
        </div>"""
        html = html.replace('<div class="card">', f'<div class="card">{demo_banner}')

    return html

def _app_interface(request: gr.Request):
    best_score = 75.0
    rank = "N/A"
    is_demo = True

    try:
        session_id = request.query_params.get("sessionid")
        if session_id:
            token = get_token_from_session(session_id)
            username = _get_username_from_token(token)
            if username:
                stats = _compute_user_stats(username, token)
                if stats["best_score"]:
                    best_score = stats["best_score"] * 100
                    is_demo = False
                if stats["rank"]:
                    rank = str(stats["rank"])
    except Exception as e:
        print(f"Auth failed: {e}")
        pass

    return get_html_content(best_score, rank, is_demo=is_demo)


def create_moral_compass_challenge_sustainability_es_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(title="Actividad 5: El Coste de la Sostenibilidad") as demo:
        html = gr.HTML()
        demo.load(_app_interface, outputs=html)
    return demo


def launch_moral_compass_challenge_sustainability_es_app(share=False, server_port=8080, **kwargs):
    app = create_moral_compass_challenge_sustainability_es_app()
    app.launch(share=share, server_port=server_port, **kwargs)


if __name__ == "__main__":
    launch_moral_compass_challenge_sustainability_es_app()

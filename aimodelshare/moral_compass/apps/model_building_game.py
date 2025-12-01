"""
Model Building Game - Gradio application for the Justice & Equity Challenge.

Session-based authentication with leaderboard caching and progressive rank unlocking.

Concurrency Notes:
- This app is designed to run in a multi-threaded environment (Cloud Run).
- Per-user state is stored in gr.State objects, NOT in os.environ.
- Caches are protected by locks to ensure thread safety.
- Linear algebra libraries are constrained to single-threaded mode to prevent
  CPU oversubscription in containerized deployments.
"""

import os

# -------------------------------------------------------------------------
# Thread Limit Configuration (MUST be set before importing numpy/sklearn)
# Prevents CPU oversubscription in containerized environments like Cloud Run.
# -------------------------------------------------------------------------
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import time
import random
import requests
import contextlib
from io import StringIO
import threading
import functools
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, Callable, TypeVar

import numpy as np
import pandas as pd
import gradio as gr

# --- Scikit-learn Imports ---
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier

# --- AI Model Share Imports ---
try:
    from aimodelshare.playground import Competition
except ImportError:
    raise ImportError(
        "The 'aimodelshare' library is required. Install with: pip install aimodelshare"
    )


# -------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# -------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        # --- General & Nav ---
        "title": "🛠️ Model Building Arena",
        "loading": "⏳ Loading...",
        "btn_next": "Next ▶️",
        "btn_back": "◀️ Back",
        "btn_return": "◀️ Back to Experiment",
        "btn_finish": "Finish & Reflect ▶️",
        "btn_begin": "Begin Model Building ▶️",
        "btn_submit": "5. 🔬 Build & Submit Model",
        
        # --- Login ---
        "login_title": "🔐 Sign in to submit & rank",
        "login_desc": "This is a preview run only. Sign in to publish your score to the live leaderboard.",
        "login_new": "New user? Create a free account at",

        # --- Welcome Screen ---
        "welcome_header": "Welcome to <b>{team}</b>!",
        "welcome_body": "Your team is waiting for your help to improve the AI.",
        "welcome_cta": "👈 Click 'Build & Submit Model' to Start Playing!",
        "lb_submit_to_rank": "Submit your model to see where you rank!",

        # --- Slides 1-7 ---
        "s1_title": "🔄 From Understanding to Building",
        "s1_intro": "Great progress! You've now:",
        "s1_li1": "Made tough decisions as a judge using AI predictions",
        "s1_li2": "Learned about false positives and false negatives",
        "s1_li3": "Understood how AI works:",
        "s1_in": "INPUT",
        "s1_mod": "MODEL",
        "s1_out": "OUTPUT",
        "s1_chal_title": "Now it's time to step into the shoes of an AI Engineer.",
        "s1_chal_body": "<strong>Your New Challenge:</strong> Build AI models that are more accurate than the one you used as a judge.",
        "s1_rem": "Remember: You experienced firsthand how AI predictions affect real people's lives. Use that knowledge to build something better.",

        "s2_title": "📋 Your Mission - Build Better AI",
        "s2_miss_head": "The Mission",
        "s2_miss_body": "Build an AI model that helps judges make better decisions. The model you used previously gave you imperfect advice. Your job now is to build a new model that predicts risk more accurately, providing judges with the reliable insights they need to be fair.",
        "s2_comp_head": "The Competition",
        "s2_comp_body": "To do this, you will compete against other engineers! To help you in your mission, you will join an engineering team. Your results will be tracked both individually and as a group in the Live Standings Leaderboards.",
        "s2_join": "You will join a team like...",
        "s2_data_head": "The Data Challenge",
        "s2_data_intro": "To compete, you have access to thousands of old case files. You have two distinct types of information:",
        "s2_li1": "<strong>Defendant Profiles:</strong> This is like what the judge saw at the time of arrest.",
        "s2_li1_sub": "<em>Age, Number of Prior Offenses, Type of Charge.</em>",
        "s2_li2": "<strong>Historical Outcomes:</strong> This is what actually happened to those people later.",
        "s2_li2_sub": "<em>Did they re-offend within 2 years? (Yes/No)</em>",
        "s2_core_head": "The Core Task",
        "s2_core_body": "You need to teach your AI to look at the \"Profiles\" and accurately predict the \"Outcome.\"",
        "s2_ready": "<strong>Ready to build something that could change how justice works?</strong>",

        "s3_title": "🧠 What is a \"Model\"?",
        "s3_p1": "Before we start competing, let's break down exactly what you are building.",
        "s3_head1": "Think of a Model as a \"Prediction Machine.\"",
        "s3_p2": "You already know the flow:",
        "s3_eng_note": "As an engineer, you don't need to write complex code from scratch. Instead, you assemble this machine using three main components.",
        "s3_comp_head": "The 3 Components:",
        "s3_c1": "<strong>1. The Inputs (Data)</strong><br>The information you feed the machine.<br><em>* Examples: Age, Prior Crimes, Charge Details.</em>",
        "s3_c2": "<strong>2. The Model (Prediction Machine)</strong><br>The mathematical \"brain\" that looks for patterns in the inputs.<br><em>* Examples: You will choose different \"brains\" that learn in different ways (e.g., simple rules vs. deep patterns).</em>",
        "s3_c3": "<strong>3. The Output (Prediction)</strong><br>The model's best guess.<br><em>* Example: Risk Level: High or Low.</em>",
        "s3_learn": "<strong>How it learns:</strong> You show the model thousands of old cases (Inputs) + what actually happened (Outcomes). It studies them to find the rules, so it can make predictions on new cases it hasn't seen before.",

        "s4_title": "🔁 How Engineers Work — The Loop",
        "s4_p1": "Now that you know the components of a model, how do you build a better one?",
        "s4_sec_head": "Here is the secret:",
        "s4_sec_body": "Real AI teams almost never get it right on the first try. Instead, they follow a continuous loop of experimentation: <strong>Try, Test, Learn, Repeat.</strong>",
        "s4_loop_head": "The Experiment Loop:",
        "s4_l1": "<strong>Build a Model:</strong> Assemble your components and get a starting prediction accuracy score.",
        "s4_l2": "<strong>Ask a Question:</strong> (e.g., \"What happens if I change the 'Brain' type?\")",
        "s4_l3": "<strong>Test & Compare:</strong> Did the score get better... or did it get worse?",
        "s4_same": "You will do the exact same thing in a competition!",
        "s4_v1": "<b>1. Configure</b><br/>Use Control Knobs to select Strategy and Data.",
        "s4_v2": "<b>2. Submit</b><br/>Click \"Build & Submit\" to train your model.",
        "s4_v3": "<b>3. Analyze</b><br/>Check your rank on the Live Leaderboard.",
        "s4_v4": "<b>4. Refine</b><br/>Change one setting and submit again!",
        "s4_tip": "<strong>Pro Tip:</strong> Try to change only one thing at a time. If you change too many things at once, you won't know what made your model better or worse!",

        "s5_title": "🎛️ Control Knobs — The \"Brain\" Settings",
        "s5_intro": "To build your model, you will use Control Knobs to configure your Prediction Machine. The first two knobs allow you to choose a type of model and adjust how it learns patterns in data.",
        "s5_k1": "1. Model Strategy (Type of Model)",
        "s5_k1_desc": "<b>What it is:</b> The specific mathematical method the machine uses to find patterns.",
        "s5_m1": "<b>The Balanced Generalist:</b> A reliable, all-purpose algorithm. It provides stable results across most data.",
        "s5_m2": "<b>The Rule-Maker:</b> Creates strict \"If... Then...\" logic (e.g., If prior crimes > 2, then High Risk).",
        "s5_m3": "<b>The Deep Pattern-Finder:</b> A complex algorithm designed to detect subtle, hidden connections in the data.",
        "s5_k2": "2. Model Complexity (Fitting Level)",
        "s5_range": "Range: Level 1 ─── ● ─── 10",
        "s5_k2_desc1": "<b>What it is:</b> Tunes how tightly the machine fits its logic to find patterns in the data.",
        "s5_k2_desc2": "<b>The Trade-off:</b>",
        "s5_low": "<b>Low (Level 1):</b> Captures only the broad, obvious trends.",
        "s5_high": "<b>High (Level 5):</b> Captures every tiny detail and variation.",
        "s5_warn": "Warning: Setting this too high causes the machine to \"memorize\" random, irrelevant details or random coincidences (noise) in the past data rather than learning the general rule.",

        "s6_title": "🎛️ Control Knobs — The \"Data\" Settings",
        "s6_intro": "Now that you have set up your prediction machine, you must decide what information the machine processes. These next knobs control the Inputs (Data).",
        "s6_k3": "3. Data Ingredients",
        "s6_k3_desc": "<b>What it is:</b> The specific data points the machine is allowed to access.<br><b>Why it matters:</b> The machine's output depends largely on its input.",
        "s6_behav": "<b>Behavioral Inputs:</b> Data like <i>Juvenile Felony Count</i> may help the logic find valid risk patterns.",
        "s6_demo": "<b>Demographic Inputs:</b> Data like <i>Race</i> may help the model learn, but they may also replicate human bias.",
        "s6_job": "<b>Your Job:</b> Check ☑ or uncheck ☐ the boxes to select the inputs to feed your model.",
        "s6_k4": "4. Data Size (Training Volume)",
        "s6_k4_desc": "<b>What it is:</b> The amount of historical cases the machine uses to learn patterns.",
        "s6_small": "<b>Small (20%):</b> Fast processing. Great for running quick tests to check your settings.",
        "s6_full": "<b>Full (100%):</b> Maximum data processing. It takes longer to build, but gives the machine the best chance to calibrate its accuracy.",

        "s7_title": "🏆 Your Score as an Engineer",
        "s7_p1": "You now know more about how to build a model. But how do we know if it works?",
        "s7_head1": "How You Are Scored",
        "s7_acc": "<strong>Prediction Accuracy:</strong> Your model is tested on <strong>Hidden Data</strong> (cases kept in a \"secret vault\" that your model has never seen). This simulates predicting the future to ensure you get a real-world prediction accuracy score.",
        "s7_lead": "<strong>The Leaderboard:</strong> Live Standings track your progress individually and as a team.",
        "s7_head2": "How You Improve: The Game",
        "s7_comp": "<strong>Compete to Improve:</strong> Refine your model to beat your personal best score.",
        "s7_promo": "<strong>Get Promoted as an Engineer & Unlock Tools:</strong> As you submit more models, you rise in rank and unlock better analysis tools:",
        "s7_ranks": "Trainee → Junior → Senior → Lead Engineer",
        "s7_head3": "Begin Your Mission",
        "s7_final": "You are now ready. Use the experiment loop, get promoted, unlock all the tools, and find the best combination to get the highest score.",
        "s7_rem": "<strong>Remember: You've seen how these predictions affect real life decisions. Build accordingly.</strong>",

        # --- App Interface ---
        "app_title": "🛠️ Model Building Arena",
        "lbl_model": "1. Model Strategy",
        "lbl_complex": "2. Model Complexity (1–10)",
        "info_complex": "Higher values allow deeper pattern learning; very high values may overfit.",
        "lbl_feat": "3. Select Data Ingredients",
        "info_feat": "More ingredients unlock as you rank up!",
        "lbl_data": "4. Data Size",
        "lbl_team_stand": "🏆 Live Standings",
        "lbl_team_sub": "Submit a model to see your rank.",
        "tab_team": "Team Standings",
        "tab_ind": "Individual Standings",
        
        # --- Ranks ---
        "rank_trainee": "# 🧑‍🎓 Rank: Trainee Engineer\n<p style='font-size:24px; line-height:1.4;'>For your first submission, just click the big '🔬 Build & Submit Model' button below!</p>",
        "rank_junior": "# 🎉 Rank Up! Junior Engineer\n<p style='font-size:24px; line-height:1.4;'>New models, data sizes, and data ingredients unlocked!</p>",
        "rank_senior": "# 🌟 Rank Up! Senior Engineer\n<p style='font-size:24px; line-height:1.4;'>Strongest Data Ingredients Unlocked! The most powerful predictors (like 'Age' and 'Prior Crimes Count') are now available in your list. These will likely boost your accuracy, but remember they often carry the most societal bias.</p>",
        "rank_lead": "# 👑 Rank: Lead Engineer\n<p style='font-size:24px; line-height:1.4;'>All tools unlocked — optimize freely!</p>",

        # --- Model Types ---
        "mod_bal": "The Balanced Generalist",
        "mod_rule": "The Rule-Maker",
        "mod_knn": "The 'Nearest Neighbor'",
        "mod_deep": "The Deep Pattern-Finder",
        "desc_bal": "A fast, reliable, well-rounded model. Good starting point; less prone to overfitting.",
        "desc_rule": "Learns simple 'if/then' rules. Easy to interpret, but can miss subtle patterns.",
        "desc_knn": "Looks at the closest past examples. 'You look like these others; I'll predict like they behave.'",
        "desc_deep": "An ensemble of many decision trees. Powerful, can capture deep patterns; watch complexity.",

        # --- KPI Card ---
        "kpi_new_acc": "New Accuracy",
        "kpi_rank": "Your Rank",
        "kpi_no_change": "No Change (↔)",
        "kpi_dropped": "Dropped",
        "kpi_moved_up": "Moved up",
        "kpi_spot": "spot",
        "kpi_spots": "spots",
        "kpi_on_board": "You're on the board!",
        "kpi_preview": "Preview only - not submitted",
        "kpi_success": "✅ Submission Successful",
        "kpi_first": "🎉 First Model Submitted!",
        "kpi_lower": "📉 Score Dropped",
        "summary_empty": "No team submissions yet.",

        # --- Leaderboard Table Headers (New) ---
        "lbl_rank": "Rank",
        "lbl_team": "Team",
        "lbl_best_acc": "Best Accuracy",
        
        # --- Final Conclusion Screen ---
        "concl_title": "✅ Section Complete",
        "concl_prep": "<p>Preparing final summary...</p>",
        "tier_trainee": "Trainee", 
        "tier_junior": "Junior", 
        "tier_senior": "Senior", 
        "tier_lead": "Lead",
        "none_yet": "None yet",
        "tip_label": "Tip:",
        "concl_tip_body": "Try at least 2–3 submissions changing ONE setting at a time to see clear cause/effect.",
        "limit_title": "Attempt Limit Reached",
        "limit_body": "You used all {limit} allowed submission attempts for this session. We will open up submissions again after you complete some new activities next.",
        "concl_snapshot": "Your Performance Snapshot",
        "concl_rank_achieved": "Rank Achieved",
        "concl_subs_made": "Submissions Made This Session",
        "concl_improvement": "Improvement Over First Score",
        "concl_tier_prog": "Tier Progress",
        "concl_strong_pred": "Strong Predictors Used",
        "concl_eth_ref": "Ethical Reflection",
        "concl_eth_body": "You unlocked powerful predictors. Consider: Would removing demographic fields change fairness? In the next section we will begin to investigate this question further.",
        "concl_next_title": "Next: Real-World Consequences",
        "concl_next_body": "Scroll below this app to continue. You'll examine how models like yours shape judicial outcomes.",
        "s6_scroll": "👇 SCROLL DOWN 👇"
    },
    "es": {
        "title": "🛠️ Arena de Construcción de Modelos",
        "loading": "⏳ Cargando...",
        "btn_next": "Siguiente ▶️",
        "btn_back": "◀️ Atrás",
        "btn_return": "◀️ Volver",
        "btn_finish": "Terminar y Reflexionar ▶️",
        "btn_begin": "Comenzar ▶️",
        "btn_submit": "5. 🔬 Construir y Enviar Modelo",

        # Login
        "login_title": "🔐 Iniciar sesión para clasificar",
        "login_desc": "Esta es solo una vista previa. Inicia sesión para publicar tu puntuación.",
        "login_new": "¿Nuevo usuario? Crea una cuenta gratis en",

        # Welcome
        "welcome_header": "¡Bienvenido a <b>{team}</b>!",
        "welcome_body": "Tu equipo espera tu ayuda para mejorar la IA.",
        "welcome_cta": "👈 ¡Haz clic en 'Construir y Enviar' para Jugar!",
        "lb_submit_to_rank": "¡Envía tu modelo para ver tu clasificación!",

        # Slides
        "s1_title": "🔄 De Entender a Construir",
        "s1_intro": "¡Gran progreso! Ahora has:",
        "s1_li1": "Tomado decisiones difíciles como juez usando predicciones de IA",
        "s1_li2": "Aprendido sobre falsos positivos y falsos negativos",
        "s1_li3": "Entendido cómo funciona la IA:",
        "s1_in": "ENTRADA",
        "s1_mod": "MODELO",
        "s1_out": "SALIDA",
        "s1_chal_title": "Ahora es el momento de ponerse en los zapatos de un Ingeniero de IA.",
        "s1_chal_body": "<strong>Tu Nuevo Desafío:</strong> Construir modelos de IA que sean más precisos que el que usaste como juez.",
        "s1_rem": "Recuerda: Experimentaste de primera mano cómo las predicciones de IA afectan la vida de personas reales. Usa ese conocimiento para construir algo mejor.",
        "s2_title": "📋 Tu Misión - Construir Mejor IA",
        "s2_miss_head": "La Misión",
        "s2_miss_body": "Construye un modelo de IA que ayude a los jueces a tomar mejores decisiones. El modelo que usaste anteriormente te dio consejos imperfectos. Tu trabajo ahora es construir un nuevo modelo que prediga el riesgo con mayor precisión, proporcionando a los jueces las ideas confiables que necesitan para ser justos.",
        "s2_comp_head": "La Competencia",
        "s2_comp_body": "¡Para hacer esto, competirás contra otros ingenieros! Para ayudarte en tu misión, te unirás a un equipo de ingeniería. Tus resultados serán rastreados tanto individualmente como en grupo en las Tablas de Clasificación en Vivo.",
        "s2_join": "Te unirás a un equipo como...",
        "s2_data_head": "El Desafío de Datos",
        "s2_data_intro": "Para competir, tienes acceso a miles de archivos de casos antiguos. Tienes dos tipos distintos de información:",
        "s2_li1": "<strong>Perfiles de Acusados:</strong> Esto es como lo que vio el juez en el momento del arresto.",
        "s2_li1_sub": "<em>Edad, Número de Delitos Previos, Tipo de Cargo.</em>",
        "s2_li2": "<strong>Resultados Históricos:</strong> Esto es lo que realmente les sucedió a esas personas después.",
        "s2_li2_sub": "<em>¿Reincidieron dentro de 2 años? (Sí/No)</em>",
        "s2_core_head": "La Tarea Principal",
        "s2_core_body": "Necesitas enseñar a tu IA a mirar los \"Perfiles\" y predecir con precisión el \"Resultado.\"",
        "s2_ready": "<strong>¿Listo para construir algo que podría cambiar cómo funciona la justicia?</strong>",
        "s3_title": "🧠 ¿Qué es un \"Modelo\"?",
        "s3_p1": "Antes de comenzar a competir, desglosemos exactamente lo que estás construyendo.",
        "s3_head1": "Piensa en un Modelo como una \"Máquina de Predicción\".",
        "s3_p2": "Ya conoces el flujo:",
        "s3_eng_note": "Como ingeniero, no necesitas escribir código complejo desde cero. En cambio, ensamblas esta máquina usando tres componentes principales.",
        "s3_comp_head": "Los 3 Componentes:",
        "s3_c1": "<strong>1. Las Entradas (Datos)</strong><br>La información que alimentas a la máquina.<br><em>* Ejemplos: Edad, Crímenes Previos, Detalles del Cargo.</em>",
        "s3_c2": "<strong>2. El Modelo (Máquina de Predicción)</strong><br>El \"cerebro\" matemático que busca patrones en las entradas.<br><em>* Ejemplos: Elegirás diferentes \"cerebros\" que aprenden de diferentes maneras (por ejemplo, reglas simples vs. patrones profundos).</em>",
        "s3_c3": "<strong>3. La Salida (Predicción)</strong><br>La mejor suposición del modelo.<br><em>* Ejemplo: Nivel de Riesgo: Alto o Bajo.</em>",
        "s3_learn": "<strong>Cómo aprende:</strong> Muestras al modelo miles de casos antiguos (Entradas) + lo que realmente sucedió (Resultados). Los estudia para encontrar las reglas, para que pueda hacer predicciones sobre nuevos casos que no ha visto antes.",
        "s4_title": "🔁 Cómo Trabajan los Ingenieros — El Bucle",
        "s4_p1": "Ahora que conoces los componentes de un modelo, ¿cómo construyes uno mejor?",
        "s4_sec_head": "Aquí está el secreto:",
        "s4_sec_body": "Los equipos de IA reales casi nunca lo hacen bien en el primer intento. En cambio, siguen un bucle continuo de experimentación: <strong>Probar, Testear, Aprender, Repetir.</strong>",
        "s4_loop_head": "El Bucle de Experimentación:",
        "s4_l1": "<strong>Construir un Modelo:</strong> Ensambla tus componentes y obtén una puntuación de precisión de predicción inicial.",
        "s4_l2": "<strong>Hacer una Pregunta:</strong> (por ejemplo, \"¿Qué pasa si cambio el tipo de 'Cerebro'?\")",
        "s4_l3": "<strong>Probar y Comparar:</strong> ¿Mejoró la puntuación... o empeoró?",
        "s4_same": "¡Harás exactamente lo mismo en una competencia!",
        "s4_v1": "<b>1. Configurar</b><br/>Usa Perillas de Control para seleccionar Estrategia y Datos.",
        "s4_v2": "<b>2. Enviar</b><br/>Haz clic en \"Construir y Enviar\" para entrenar tu modelo.",
        "s4_v3": "<b>3. Analizar</b><br/>Revisa tu rango en la Tabla de Clasificación en Vivo.",
        "s4_v4": "<b>4. Refinar</b><br/>¡Cambia una configuración y envía de nuevo!",
        "s4_tip": "<strong>Consejo Pro:</strong> Intenta cambiar solo una cosa a la vez. Si cambias demasiadas cosas a la vez, ¡no sabrás qué hizo que tu modelo fuera mejor o peor!",
        "s5_title": "🎛️ Configuración del \"Cerebro\"",
        "s5_intro": "Para construir tu modelo, usarás Perillas de Control para configurar tu Máquina de Predicción. Las primeras dos perillas te permiten elegir un tipo de modelo y ajustar cómo aprende patrones en los datos.",
        "s5_k1": "1. Estrategia del Modelo (Tipo de Modelo)",
        "s5_k1_desc": "<b>Qué es:</b> El método matemático específico que la máquina usa para encontrar patrones.",
        "s5_m1": "<b>El Generalista Equilibrado:</b> Un algoritmo confiable y multipropósito. Proporciona resultados estables en la mayoría de los datos.",
        "s5_m2": "<b>El Creador de Reglas:</b> Crea lógica estricta \"Si... Llavors...\" (por ejemplo, Si crímenes previos > 2, entonces Alto Riesgo).",
        "s5_m3": "<b>El Buscador de Patrones Profundos:</b> Un algoritmo complejo diseñado para detectar conexiones sutiles y ocultas en los datos.",
        "s5_k2": "2. Complejidad del Modelo (Nivel de Ajuste)",
        "s5_range": "Rango: Nivel 1 ─── ● ─── 10",
        "s5_k2_desc1": "<b>Qué es:</b> Ajusta qué tan ajustadamente la máquina ajusta su lógica para encontrar patrones en los datos.",
        "s5_k2_desc2": "<b>El Intercambio:</b>",
        "s5_low": "<b>Bajo (Nivel 1):</b> Captura solo las tendencias amplias y obvias.",
        "s5_high": "<b>Alto (Nivel 5):</b> Captura cada pequeño detalle y variación.",
        "s5_warn": "Advertencia: Configurar esto demasiado alto hace que la máquina \"memorice\" detalles aleatorios e irrelevantes o coincidencias aleatorias (ruido) en los datos pasados en lugar de aprender la regla general.",
        "s6_title": "🎛️ Configuración de \"Datos\"",
        "s6_intro": "Ahora que has configurado tu máquina de predicción, debes decidir qué información procesa la máquina. Estas siguientes perillas controlan las Entradas (Datos).",
        "s6_k3": "3. Ingredientes de Datos",
        "s6_k3_desc": "<b>Qué es:</b> Los puntos de datos específicos a los que la máquina tiene permitido acceder.<br><b>Por qué importa:</b> La salida de la máquina depende en gran medida de su entrada.",
        "s6_behav": "<b>Entradas de Comportamiento:</b> Datos como <i>Conteo de Delitos Juveniles</i> pueden ayudar a la lógica a encontrar patrones de riesgo válidos.",
        "s6_demo": "<b>Entradas Demográficas:</b> Datos como <i>Raza</i> pueden ayudar al modelo a aprender, pero también pueden replicar el sesgo humano.",
        "s6_job": "<b>Tu Trabajo:</b> Marca ☑ o desmarca ☐ las casillas para seleccionar las entradas para alimentar tu modelo.",
        "s6_k4": "4. Tamaño de Datos (Volumen de Entrenamiento)",
        "s6_k4_desc": "<b>Qué es:</b> La cantidad de casos históricos que la máquina usa para aprender patrones.",
        "s6_small": "<b>Pequeño (20%):</b> Procesamiento rápido. Genial para ejecutar pruebas rápidas para verificar tu configuración.",
        "s6_full": "<b>Completo (100%):</b> Procesamiento máximo de datos. Tarda más en construirse, pero le da a la máquina la mejor oportunidad de calibrar su precisión.",
        "s7_title": "🏆 Tu Puntuación",
        "s7_p1": "Ahora sabes más sobre cómo construir un modelo. Pero, ¿cómo sabemos si funciona?",
        "s7_head1": "Cómo eres Puntuado",
        "s7_acc": "<strong>Precisión de Predicción:</strong> Tu modelo se prueba en <strong>Datos Ocultos</strong> (casos guardados en una \"bóveda secreta\" que tu modelo nunca ha visto). Esto simula predecir el futuro para asegurar que obtengas una puntuación de precisión de predicción del mundo real.",
        "s7_lead": "<strong>La Tabla de Clasificación:</strong> Las Clasificaciones en Vivo rastrean tu progreso individualmente y como equipo.",
        "s7_head2": "Cómo Mejoras: El Juego",
        "s7_comp": "<strong>Compite para Mejorar:</strong> Refina tu modelo para superar tu mejor puntuación personal.",
        "s7_promo": "<strong>Sé Promovido como Ingeniero y Desbloquea Herramientas:</strong> A medida que envías más modelos, subes de rango y desbloqueas mejores herramientas de análisis:",
        "s7_ranks": "Aprendiz → Junior → Senior → Ingeniero Principal",
        "s7_head3": "Comienza Tu Misión",
        "s7_final": "Ahora estás listo. Usa el bucle de experimentación, sé promovido, desbloquea todas las herramientas y encuentra la mejor combinación para obtener la puntuación más alta.",
        "s7_rem": "<strong>Recuerda: Has visto cómo estas predicciones afectan las decisiones de la vida real. Construye en consecuencia.</strong>",
        "btn_begin": "Comenzar ▶️",
        
        "lbl_model": "1. Estrategia del Modelo",
        "lbl_complex": "2. Complejidad del Modelo",
        "info_complex": "Valores altos permiten aprendizaje profundo; cuidado con el sobreajuste.",
        "lbl_feat": "3. Ingredientes de Datos",
        "info_feat": "¡Más ingredientes se desbloquean al subir de rango!",
        "lbl_data": "4. Tamaño de Datos",
        "lbl_team_stand": "🏆 Clasificaciones en Vivo",
        "lbl_team_sub": "Envía un modelo para ver tu rango.",
        "tab_team": "Clasificaciones de Equipo",
        "tab_ind": "Clasificaciones Individuales",
        "concl_title": "✅ Sección Completada",
        "concl_prep": "<p>Preparando resumen final...</p>",

        "rank_trainee": "# 🧑‍🎓 Rango: Ingeniero Aprendiz\n<p style='font-size:24px; line-height:1.4;'>¡Haz clic en 'Construir y Enviar' para comenzar!</p>",
        "rank_junior": "# 🎉 ¡Subida de Rango! Ingeniero Junior\n<p style='font-size:24px; line-height:1.4;'>¡Nuevos modelos y datos desbloqueados!</p>",
        "rank_senior": "# 🌟 ¡Subida de Rango! Ingeniero Senior\n<p style='font-size:24px; line-height:1.4;'>¡Ingredientes de Datos Más Fuertes Desbloqueados!</p>",
        "rank_lead": "# 👑 Rango: Ingeniero Principal\n<p style='font-size:24px; line-height:1.4;'>¡Todas las herramientas desbloqueadas!</p>",

        "mod_bal": "El Generalista Equilibrado",
        "mod_rule": "El Creador de Reglas",
        "mod_knn": "El 'Vecino Más Cercano'",
        "mod_deep": "El Buscador de Patrones Profundos",
        "desc_bal": "Un modelo rápido, confiable y completo. Buen punto de partida; menos propenso al sobreajuste.",
        "desc_rule": "Aprende reglas simples 'si/entonces'. Fácil de interpretar, pero puede perder patrones sutiles.",
        "desc_knn": "Mira los ejemplos pasados más cercanos. 'Te pareces a estos otros; predeciré como ellos se comportan.'",
        "desc_deep": "Un conjunto de muchos árboles de decisión. Poderoso, puede capturar patrones profundos; cuidado con la complejidad.",

        "kpi_new_acc": "Nueva Precisión",
        "kpi_rank": "Tu Rango",
        "kpi_no_change": "Sin Cambio (↔)",
        "kpi_dropped": "Bajó",
        "kpi_moved_up": "Subió",
        "kpi_spot": "puesto",
        "kpi_spots": "puestos",
        "kpi_on_board": "¡Estás en el tablero!",
        "kpi_preview": "Vista previa - no enviado",
        "kpi_success": "✅ Envío Exitoso",
        "kpi_first": "🎉 Primer Modelo Enviado!",
        "kpi_lower": "📉 Puntuación Bajó",
        "summary_empty": "Aún no hay envíos de equipo.",

        # --- Leaderboard ---
        "lbl_rank": "Rango",
        "lbl_team": "Equipo",
        "lbl_best_acc": "Mejor Precisión",

        # --- Conclusion ---
        "tier_trainee": "Aprendiz", "tier_junior": "Junior", "tier_senior": "Senior", "tier_lead": "Líder",
        "none_yet": "Ninguno aún",
        "tip_label": "Consejo:",
        "concl_tip_body": "Intenta al menos 2–3 envíos cambiando UNA configuración a la vez para ver causa/efecto claro.",
        "limit_title": "Límite de Intentos Alcanzado",
        "limit_body": "Has usado los {limit} intentos permitidos. Abriremos los envíos nuevamente después de que completes nuevas actividades.",
        "concl_snapshot": "Tu Resumen de Rendimiento",
        "concl_rank_achieved": "Rango Logrado",
        "concl_subs_made": "Envíos Hechos Esta Sesión",
        "concl_improvement": "Mejora Sobre la Primera Puntuación",
        "concl_tier_prog": "Progreso de Nivel",
        "concl_strong_pred": "Predictores Fuertes Usados",
        "concl_eth_ref": "Reflexión Ética",
        "concl_eth_body": "Desbloqueaste predictores poderosos. Considera: ¿Eliminar campos demográficos cambiaría la equidad? Investigaremos esto más a fondo a continuación.",
        "concl_next_title": "Siguiente: Consecuencias en el Mundo Real",
        "concl_next_body": "Desplázate hacia abajo. Examinarás cómo modelos como el tuyo dan forma a los resultados judiciales.",
        "s6_scroll": "👇 DESPLÁZATE HACIA ABAJO 👇",

        # --- Team Names ---
        "The Moral Champions": "Los Campeones Morales",
        "The Justice League": "La Liga de la Justicia",
        "The Data Detectives": "Los Detectives de Datos",
        "The Ethical Explorers": "Los Exploradores Éticos",
        "The Fairness Finders": "Los Buscadores de Equidad",
        "The Accuracy Avengers": "Los Vengadores de la Precisión"
    },
    "ca": {
        "title": "🛠️ Arena de Construcció de Models",
        "loading": "⏳ Carregant...",
        "btn_next": "Següent ▶️",
        "btn_back": "◀️ Enrere",
        "btn_return": "◀️ Tornar",
        "btn_finish": "Acabar i Reflexionar ▶️",
        "btn_begin": "Començar ▶️",
        "btn_submit": "5. 🔬 Construir i Enviar Model",

        # Login
        "login_title": "🔐 Inicia sessió per classificar",
        "login_desc": "Això és només una vista prèvia. Inicia sessió per publicar la teva puntuació.",
        "login_new": "Nou usuari? Crea un compte gratuït a",

        # Welcome
        "welcome_header": "Benvingut a <b>{team}</b>!",
        "welcome_body": "El teu equip espera la teva ajuda per millorar la IA.",
        "welcome_cta": "👈 Fes clic a 'Construir i Enviar' per Jugar!",
        "lb_submit_to_rank": "Envia el teu model per veure la teva classificació!",

        # Slides
        "s1_title": "🔄 D'Entendre a Construir",
        "s1_intro": "Gran progrés! Ara has:",
        "s1_li1": "Pres decisions difícils com a jutge utilitzant prediccions d'IA",
        "s1_li2": "Après sobre falsos positius i falsos negatius",
        "s1_li3": "Entès com funciona la IA:",
        "s1_in": "ENTRADA",
        "s1_mod": "MODEL",
        "s1_out": "SORTIDA",
        "s1_chal_title": "Ara és el moment de posar-se a la pell d'un Enginyer d'IA.",
        "s1_chal_body": "<strong>El Teu Nou Repte:</strong> Construir models d'IA que siguin més precisos que el que vas utilitzar com a jutge.",
        "s1_rem": "Recorda: Vas experimentar de primera mà com les prediccions d'IA afecten la vida de persones reals. Utilitza aquest coneixement per construir alguna cosa millor.",
        "s2_title": "📋 La Teva Missió - Construir Millor IA",
        "s2_miss_head": "La Missió",
        "s2_miss_body": "Construeix un model d'IA que ajudi els jutges a prendre millors decisions. El model que vas utilitzar anteriorment et va donar consells imperfectes. La teva feina ara és construir un nou model que predigui el risc amb més precisió, proporcionant als jutges les idees fiables que necessiten per ser justos.",
        "s2_comp_head": "La Competició",
        "s2_comp_body": "Per fer això, competiràs contra altres enginyers! Per ajudar-te en la teva missió, t'uniràs a un equip d'enginyeria. Els teus resultats seran rastrejats tant individualment com en grup a les Taules de Classificació en Viu.",
        "s2_join": "T'uniràs a un equip com...",
        "s2_data_head": "El Repte de Dades",
        "s2_data_intro": "Per competir, tens accés a milers d'arxius de casos antics. Tens dos tipus diferents d'informació:",
        "s2_li1": "<strong>Perfils d'Acusats:</strong> Això és com el que va veure el jutge en el moment de l'arrest.",
        "s2_li1_sub": "<em>Edat, Nombre de Delictes Previs, Tipus de Càrrec.</em>",
        "s2_li2": "<strong>Resultats Històrics:</strong> Això és el que realment els va passar a aquestes persones després.",
        "s2_li2_sub": "<em>Van reincidir en 2 anys? (Sí/No)</em>",
        "s2_core_head": "La Tasca Principal",
        "s2_core_body": "Necessites ensenyar a la teva IA a mirar els \"Perfils\" i predir amb precisió el \"Resultat.\"",
        "s2_ready": "<strong>A punt per construir alguna cosa que podria canviar com funciona la justícia?</strong>",
        "s3_title": "🧠 Què és un \"Model\"?",
        "s3_p1": "Abans de començar a competir, desglossem exactament el que estàs construint.",
        "s3_head1": "Pensa en un Model com una \"Màquina de Predicció\".",
        "s3_p2": "Ja coneixes el flux:",
        "s3_eng_note": "Com a enginyer, no necessites escriure codi complex des de zero. En canvi, muntes aquesta màquina utilitzant tres components principals.",
        "s3_comp_head": "Els 3 Components:",
        "s3_c1": "<strong>1. Les Entrades (Dades)</strong><br>La informació que alimentes a la màquina.<br><em>* Exemples: Edat, Crims Previs, Detalls del Càrrec.</em>",
        "s3_c2": "<strong>2. El Model (Màquina de Predicció)</strong><br>El \"cervell\" matemàtic que busca patrons en les entrades.<br><em>* Exemples: Triaràs diferents \"cervells\" que aprenen de diferents maneres (per exemple, regles simples vs. patrons profunds).</em>",
        "s3_c3": "<strong>3. La Sortida (Predicció)</strong><br>La millor suposició del model.<br><em>* Exemple: Nivell de Risc: Alt o Baix.</em>",
        "s3_learn": "<strong>Com aprèn:</strong> Mostres al model milers de casos antics (Entrades) + el que realment va passar (Resultats). Els estudia per trobar les regles, per tal que pugui fer prediccions sobre nous casos que no ha vist abans.",
        "s4_title": "🔁 Com Treballen els Enginyers — El Bucle",
        "s4_p1": "Ara que coneixes els components d'un model, com en construeixes un de millor?",
        "s4_sec_head": "Aquí està el secret:",
        "s4_sec_body": "Els equips d'IA reals gairebé mai ho fan bé al primer intent. En canvi, segueixen un bucle continu d'experimentació: <strong>Provar, Testejar, Aprendre, Repetir.</strong>",
        "s4_loop_head": "El Bucle d'Experimentació:",
        "s4_l1": "<strong>Construir un Model:</strong> Munta els teus components i obtén una puntuació de precisió de predicció inicial.",
        "s4_l2": "<strong>Fer una Pregunta:</strong> (per exemple, \"Què passa si canvio el tipus de 'Cervell'?\")",
        "s4_l3": "<strong>Provar i Comparar:</strong> Ha millorat la puntuació... o ha empitjorat?",
        "s4_same": "Faràs exactament el mateix en una competició!",
        "s4_v1": "<b>1. Configurar</b><br/>Utilitza Perilles de Control per seleccionar Estratègia i Dades.",
        "s4_v2": "<b>2. Enviar</b><br/>Fes clic a \"Construir i Enviar\" per entrenar el teu model.",
        "s4_v3": "<b>3. Analitzar</b><br/>Revisa el teu rang a la Taula de Classificació en Viu.",
        "s4_v4": "<b>4. Refinar</b><br/>Canvia una configuració i envia de nou!",
        "s4_tip": "<strong>Consell Pro:</strong> Intenta canviar només una cosa a la vegada. Si canvies massa coses a la vegada, no sabràs què va fer que el teu model fos millor o pitjor!",
        "s5_title": "🎛️ Configuració del \"Cervell\"",
        "s5_intro": "Per construir el teu model, utilitzaràs Perilles de Control per configurar la teva Màquina de Predicció. Les primeres dues perilles et permeten triar un tipus de model i ajustar com aprèn patrons en les dades.",
        "s5_k1": "1. Estratègia del Model (Tipus de Model)",
        "s5_k1_desc": "<b>Què és:</b> El mètode matemàtic específic que la màquina utilitza per trobar patrons.",
        "s5_m1": "<b>El Generalista Equilibrat:</b> Un algorisme fiable i multipropòsit. Proporciona resultats estables en la majoria de les dades.",
        "s5_m2": "<b>El Creador de Regles:</b> Crea lògica estricta \"Si... Llavors...\" (per exemple, Si crims previs > 2, llavors Alt Risc).",
        "s5_m3": "<b>El Cercador de Patrons Profunds:</b> Un algorisme complex dissenyat per detectar connexions subtils i ocultes en les dades.",
        "s5_k2": "2. Complexitat del Model (Nivell d'Ajust)",
        "s5_range": "Rang: Nivell 1 ─── ● ─── 10",
        "s5_k2_desc1": "<b>Què és:</b> Ajusta com d'ajustadament la màquina ajusta la seva lògica per trobar patrons en les dades.",
        "s5_k2_desc2": "<b>L'Intercanvi:</b>",
        "s5_low": "<b>Baix (Nivell 1):</b> Captura només les tendències àmplies i òbvies.",
        "s5_high": "<b>Alt (Nivell 5):</b> Captura cada petit detall i variació.",
        "s5_warn": "Advertència: Configurar això massa alt fa que la màquina \"memoritzi\" detalls aleatoris i irrellevants o coincidències aleatòries (soroll) en les dades passades en lloc d'aprendre la regla general.",
        "s6_title": "🎛️ Configuració de \"Dades\"",
        "s6_intro": "Ara que has configurat la teva màquina de predicció, has de decidir quina informació processa la màquina. Aquestes següents perilles controlen les Entrades (Dades).",
        "s6_k3": "3. Ingredients de Dades",
        "s6_k3_desc": "<b>Què és:</b> Els punts de dades específics als quals la màquina té permès accedir.<br><b>Per què importa:</b> La sortida de la màquina depèn en gran mesura de la seva entrada.",
        "s6_behav": "<b>Entrades de Comportament:</b> Dades com <i>Recompte de Delictes Juvenils</i> poden ajudar a la lògica a trobar patrons de risc vàlids.",
        "s6_demo": "<b>Entrades Demogràfiques:</b> Dades com <i>Raça</i> poden ajudar al model a aprendre, però també poden replicar el biaix humà.",
        "s6_job": "<b>La Teva Feina:</b> Marca ☑ o desmarca ☐ les caselles per seleccionar les entrades per alimentar el teu model.",
        "s6_k4": "4. Mida de Dades (Volum d'Entrenament)",
        "s6_k4_desc": "<b>Què és:</b> La quantitat de casos històrics que la màquina utilitza per aprendre patrons.",
        "s6_small": "<b>Petit (20%):</b> Processament ràpid. Genial per executar proves ràpides per verificar la teva configuració.",
        "s6_full": "<b>Complet (100%):</b> Processament màxim de dades. Triga més a construir-se, però li dóna a la màquina la millor oportunitat de calibrar la seva precisió.",
        "s7_title": "🏆 La Teva Puntuació",
        "s7_p1": "Ara saps més sobre com construir un model. Però, com sabem si funciona?",
        "s7_head1": "Com ets Puntuat",
        "s7_acc": "<strong>Precisió de Predicció:</strong> El teu model es prova en <strong>Dades Ocultes</strong> (casos guardats en una \"cambra secreta\" que el teu model mai ha vist). Això simula predir el futur per assegurar que obtinguis una puntuació de precisió de predicció del món real.",
        "s7_lead": "<strong>La Taula de Classificació:</strong> Les Classificacions en Viu rastregen el teu progrés individualment i com a equip.",
        "s7_head2": "Com Millores: El Joc",
        "s7_comp": "<strong>Competeix per Millorar:</strong> Refina el teu model per superar la teva millor puntuació personal.",
        "s7_promo": "<strong>Sigues Promogut com a Enginyer i Desbloqueja Eines:</strong> A mesura que envies més models, puges de rang i desbloqueges millors eines d'anàlisi:",
        "s7_ranks": "Aprenent → Junior → Senior → Enginyer Principal",
        "s7_head3": "Comença La Teva Missió",
        "s7_final": "Ara estàs llest. Utilitza el bucle d'experimentació, sigues promogut, desbloqueja totes les eines i troba la millor combinació per obtenir la puntuació més alta.",
        "s7_rem": "<strong>Recorda: Has vist com aquestes prediccions afecten les decisions de la vida real. Construeix en conseqüència.</strong>",
        "btn_begin": "Començar ▶️",
        
        "lbl_model": "1. Estratègia del Model",
        "lbl_complex": "2. Complexitat del Model",
        "info_complex": "Valors alts permeten aprenentatge profund; cura amb el sobreajust.",
        "lbl_feat": "3. Ingredients de Dades",
        "info_feat": "Més ingredients es desbloquegen al pujar de rang!",
        "lbl_data": "4. Mida de Dades",
        "lbl_team_stand": "🏆 Classificacions en Viu",
        "lbl_team_sub": "Envia un model per veure el teu rang.",
        "tab_team": "Classificacions d'Equip",
        "tab_ind": "Classificacions Individuals",
        "concl_title": "✅ Secció Completada",
        "concl_prep": "<p>Preparant resum final...</p>",
        "rank_trainee": "# 🧑‍🎓 Rang: Enginyer Aprenent\n<p style='font-size:24px; line-height:1.4;'>Fes clic a 'Construir i Enviar' per començar!</p>",
        "rank_junior": "# 🎉 Pujada de Rang! Enginyer Junior\n<p style='font-size:24px; line-height:1.4;'>Nous models i dades desbloquejats!</p>",
        "rank_senior": "# 🌟 Pujada de Rang! Enginyer Senior\n<p style='font-size:24px; line-height:1.4;'>Ingredients de Dades Més Forts Desbloquejats!</p>",
        "rank_lead": "# 👑 Rang: Enginyer Principal\n<p style='font-size:24px; line-height:1.4;'>Totes les eines desbloquejades!</p>",
        "mod_bal": "El Generalista Equilibrat",
        "mod_rule": "El Creador de Reglas",
        "mod_knn": "El 'Veí Més Proper'",
        "mod_deep": "El Cercador de Patrons Profunds",
        "desc_bal": "Un model ràpid, fiable i complet. Bon punt de partida; menys propens al sobreajust.",
        "desc_rule": "Aprèn regles simples 'si/llavors'. Fàcil d'interpretar, però pot perdre patrons subtils.",
        "desc_knn": "Mira els exemples passats més propers. 'T'assembles a aquests altres; prediré com ells es comporten.'",
        "desc_deep": "Un conjunt de molts arbres de decisió. Potent, pot capturar patrons profunds; cura amb la complexitat.",
        "kpi_new_acc": "Nova Precisió",
        "kpi_rank": "El Teu Rang",
        "kpi_no_change": "Sense Canvi (↔)",
        "kpi_dropped": "Va baixar",
        "kpi_moved_up": "Va pujar",
        "kpi_spot": "lloc",
        "kpi_spots": "llocs",
        "kpi_on_board": "Estàs al tauler!",
        "kpi_preview": "Vista prèvia - no enviat",
        "kpi_success": "✅ Enviament Exitós",
        "kpi_first": "🎉 Primer Model Enviat!",
        "kpi_lower": "📉 Puntuació Va Baixar",
        "summary_empty": "Encara no hi ha enviaments d'equip.",

        # --- Leaderboard ---
        "lbl_rank": "Rang",
        "lbl_team": "Equip",
        "lbl_best_acc": "Millor Precisió",

        # --- Conclusion ---
        "tier_trainee": "Aprenent", "tier_junior": "Junior", "tier_senior": "Senior", "tier_lead": "Líder",
        "none_yet": "Cap encara",
        "tip_label": "Consell:",
        "concl_tip_body": "Intenta almenys 2–3 enviaments canviant UNA configuració a la vegada per veure causa/efecte clar.",
        "limit_title": "Límit d'Intents Assolit",
        "limit_body": "Has utilitzat tots els {limit} intents permesos. Obrirem els enviaments de nou després que completis noves activitats.",
        "concl_snapshot": "El Teu Resum de Rendiment",
        "concl_rank_achieved": "Rang Assolit",
        "concl_subs_made": "Enviaments Fets Aquesta Sessió",
        "concl_improvement": "Millora Sobre la Primera Puntuació",
        "concl_tier_prog": "Progrés de Nivell",
        "concl_strong_pred": "Predictors Forts Utilitzats",
        "concl_eth_ref": "Reflexió Ètica",
        "concl_eth_body": "Has desbloquejat predictors potents. Considera: Eliminar camps demogràfics canviaria l'equitat? Investigarem això més a fons a continuació.",
        "concl_next_title": "Següent: Conseqüències al Món Real",
        "concl_next_body": "Desplaça't cap avall. Examinaràs com models com el teu donen forma als resultats judicials.",
        "s6_scroll": "👇 DESPLAÇA'T CAP AVALL 👇",

        # --- Team Names ---
        "The Moral Champions": "Els Campions Morals",
        "The Justice League": "La Lliga de la Justícia",
        "The Data Detectives": "Els Detectius de Dades",
        "The Ethical Explorers": "Els Exploradors Ètics",
        "The Fairness Finders": "Els Cercadors d'Equitat",
        "The Accuracy Avengers": "Els Venjadors de la Precisió"
    }
}
# -------------------------------------------------------------------------
# Configuration & Caching Infrastructure
# -------------------------------------------------------------------------

LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

# In-memory caches (per container instance)
# Each cache has its own lock for thread safety under concurrent requests
_cache_lock = threading.Lock()  # Protects _leaderboard_cache
_user_stats_lock = threading.Lock()  # Protects _user_stats_cache
_auth_lock = threading.Lock()  # Protects get_aws_token() credential injection

# Auth-aware leaderboard cache: separate entries for authenticated vs anonymous
# Structure: {"anon": {"data": df, "timestamp": float}, "auth": {"data": df, "timestamp": float}}
_leaderboard_cache: Dict[str, Dict[str, Any]] = {
    "anon": {"data": None, "timestamp": 0.0},
    "auth": {"data": None, "timestamp": 0.0},
}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

# -------------------------------------------------------------------------
# Retry Helper for External API Calls
# -------------------------------------------------------------------------
def t(lang, key):
    """Helper to get translation with fallback to English."""
    # TRANSLATIONS must be defined globally before this is called
    if lang not in TRANSLATIONS:
        lang = "en"
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

def t_team(team_name_english, lang):
    """
    Translates an English team name into the target language.
    If no translation is found, returns the original English name.
    """
    if not team_name_english:
        return ""
    
    # Normal lookup
    if lang in TRANSLATIONS and team_name_english in TRANSLATIONS[lang]:
        return TRANSLATIONS[lang][team_name_english]
    
    # Fallback
    return team_name_english
  
T = TypeVar("T")

def on_initial_load(username, token=None, team_name="", lang="en"):
    """
    Updated to handle I18n for the Welcome screen, Team Name translation, and Rank settings.
    """
    # 1. Compute initial UI settings (Model choices, sliders) based on rank 0 (Trainee)
    # Pass lang so the "Trainee" rank message is translated
    initial_ui = compute_rank_settings(
        0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE, lang=lang
    )

    # 2. Translate the Team Name for display
    # The backend uses English names ("The Moral Champions"), but we want to show 
    # "Los Campeones Morales" if lang is 'es'.
    display_team = team_name
    if team_name and lang in TRANSLATIONS and team_name in TRANSLATIONS[lang]:
        display_team = TRANSLATIONS[lang][team_name]
    elif not display_team:
        display_team = t(lang, "lbl_team") # Fallback to generic "Team" label

    # 3. Prepare the Welcome HTML (Localized)
    welcome_html = f"""
    <div style='text-align:center; padding: 30px 20px;'>
        <div style='font-size: 3rem; margin-bottom: 10px;'>👋</div>
        <h3 style='margin: 0 0 8px 0; color: #111827; font-size: 1.5rem;'>{t(lang, 'welcome_header').format(team=display_team)}</h3>
        <p style='font-size: 1.1rem; color: #4b5563; margin: 0 0 20px 0;'>
            {t(lang, 'welcome_body')}
        </p>
        
        <div style='background:#eff6ff; padding:16px; border-radius:12px; border:2px solid #bfdbfe; display:inline-block;'>
            <p style='margin:0; color:#1e40af; font-weight:bold; font-size:1.1rem;'>
                {t(lang, 'welcome_cta')}
            </p>
        </div>
    </div>
    """

    # 4. Check background data readiness
    with INIT_LOCK:
        background_ready = INIT_FLAGS["leaderboard"]
    
    should_attempt_fetch = background_ready or (token is not None)
    full_leaderboard_df = None
    
    if should_attempt_fetch:
        try:
            if playground:
                full_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
        except Exception as e:
            print(f"Error on initial load fetch: {e}")
            full_leaderboard_df = None

    # 5. Check if THIS user has submitted anything
    user_has_submitted = False
    if full_leaderboard_df is not None and not full_leaderboard_df.empty:
        if "username" in full_leaderboard_df.columns and username:
            user_has_submitted = username in full_leaderboard_df["username"].values

    # 6. Decision Logic: Which HTML to return?
    if not user_has_submitted:
        # CASE 1: New User -> Show Welcome Screen
        team_html = welcome_html
        individual_html = f"<p style='text-align:center; color:#6b7280; padding-top:40px;'>{t(lang, 'lb_submit_to_rank')}</p>"
        
    elif full_leaderboard_df is None or full_leaderboard_df.empty:
        # CASE 2: Returning user, but data fetch failed -> Show Skeleton
        team_html = _build_skeleton_leaderboard(rows=6, is_team=True)
        individual_html = _build_skeleton_leaderboard(rows=6, is_team=False)
        
    else:
        # CASE 3: Returning user WITH data -> Show Real Tables
        try:
            # Generate summaries
            # CRITICAL: Pass 'lang' here so column headers and rank rows are translated
            team_html, individual_html, _, _, _, _ = generate_competitive_summary(
                full_leaderboard_df,
                team_name,
                username,
                0, 0, -1,
                lang=lang
            )
        except Exception as e:
            print(f"Error generating summary HTML: {e}")
            team_html = "<p style='text-align:center; color:red; padding-top:20px;'>Error rendering leaderboard.</p>"
            individual_html = "<p style='text-align:center; color:red; padding-top:20px;'>Error rendering leaderboard.</p>"

    # 7. Return all UI updates
    return (
        get_model_card(DEFAULT_MODEL, lang), # Translated Model Card
        team_html,
        individual_html,
        initial_ui["rank_message"], # Translated Rank Message
        gr.update(choices=initial_ui["model_choices"], value=initial_ui["model_value"], interactive=initial_ui["model_interactive"]),
        gr.update(minimum=1, maximum=initial_ui["complexity_max"], value=initial_ui["complexity_value"]),
        gr.update(choices=[f[0] for f in initial_ui["feature_set_choices"]], value=initial_ui["feature_set_value"], interactive=initial_ui["feature_set_interactive"]),
        gr.update(choices=initial_ui["data_size_choices"], value=initial_ui["data_size_value"], interactive=initial_ui["data_size_interactive"]),
    )
  
def _retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 0.5,
    description: str = "operation"
) -> T:
    """
    Execute a function with exponential backoff retry on failure.
    
    Concurrency Note: This helper provides resilience against transient
    network failures when calling external APIs (Competition.get_leaderboard,
    playground.submit_model). Essential for Cloud Run deployments where
    network calls may occasionally fail under load.
    
    Args:
        func: Callable to execute (should take no arguments)
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds, doubled each retry (default: 0.5)
        description: Human-readable description for logging
    
    Returns:
        Result from successful function call
    
    Raises:
        Last exception if all attempts fail
    """
    last_exception: Optional[Exception] = None
    delay = base_delay
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts:
                _log(f"{description} attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                _log(f"{description} failed after {max_attempts} attempts: {e}")
    
    # Loop always runs at least once (max_attempts >= 1), so last_exception is set
    raise last_exception  # type: ignore[misc]

def _log(msg: str):
    """Log message if DEBUG_LOG is enabled."""
    if DEBUG_LOG:
        print(f"[ModelBuildingGame] {msg}")

def _normalize_team_name(name: str) -> str:
    """Normalize team name for consistent comparison and storage."""
    if not name:
        return ""
    return " ".join(str(name).strip().split())

def _get_leaderboard_with_optional_token(playground_instance: Optional["Competition"], token: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Fetch fresh leaderboard with optional token authentication and retry logic.
    
    This is a helper function that centralizes the pattern of fetching
    a fresh (non-cached) leaderboard with optional token authentication.
    Use this for user-facing flows that require fresh, full data.
    
    Concurrency Note: Uses _retry_with_backoff for resilience against
    transient network failures.
    
    Args:
        playground_instance: The Competition playground instance (or None)
        token: Optional authentication token for the fetch
    
    Returns:
        DataFrame with leaderboard data, or None if fetch fails or playground is None
    """
    if playground_instance is None:
        return None
    
    def _fetch():
        if token:
            return playground_instance.get_leaderboard(token=token)
        return playground_instance.get_leaderboard()
    
    try:
        return _retry_with_backoff(_fetch, description="leaderboard fetch")
    except Exception as e:
        _log(f"Leaderboard fetch failed after retries: {e}")
        return None

def _fetch_leaderboard(token: Optional[str]) -> Optional[pd.DataFrame]:
    """
    Fetch leaderboard with auth-aware caching (TTL: LEADERBOARD_CACHE_SECONDS).
    
    Concurrency Note: Cache is keyed by auth scope ("anon" vs "auth") to prevent
    cross-user data leakage. Authenticated users share a single "auth" cache entry
    to avoid unbounded cache growth. Protected by _cache_lock.
    """
    # Determine cache key based on authentication status
    cache_key = "auth" if token else "anon"
    now = time.time()
    
    with _cache_lock:
        cache_entry = _leaderboard_cache[cache_key]
        if (
            cache_entry["data"] is not None
            and now - cache_entry["timestamp"] < LEADERBOARD_CACHE_SECONDS
        ):
            _log(f"Leaderboard cache hit ({cache_key})")
            return cache_entry["data"]

    _log(f"Fetching fresh leaderboard ({cache_key})...")
    df = None
    try:
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground_instance = Competition(playground_id)
        
        def _fetch():
            return playground_instance.get_leaderboard(token=token) if token else playground_instance.get_leaderboard()
        
        df = _retry_with_backoff(_fetch, description="leaderboard fetch")
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
        _log(f"Leaderboard fetched ({cache_key}): {len(df) if df is not None else 0} entries")
    except Exception as e:
        _log(f"Leaderboard fetch failed ({cache_key}): {e}")
        df = None

    with _cache_lock:
        _leaderboard_cache[cache_key]["data"] = df
        _leaderboard_cache[cache_key]["timestamp"] = time.time()
    return df

def _get_or_assign_team(username: str, leaderboard_df: Optional[pd.DataFrame]) -> Tuple[str, bool]:
    """Get existing team from leaderboard or assign random team."""
    # TEAM_NAMES is defined in configuration section below
    try:
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(
                            user_submissions["timestamp"], errors="coerce"
                        )
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                        _log(f"Sorted {len(user_submissions)} submissions by timestamp for {username}")
                    except Exception as ts_err:
                        _log(f"Timestamp sort error: {ts_err}")
                existing_team = user_submissions.iloc[0]["Team"]
                if pd.notna(existing_team) and str(existing_team).strip():
                    normalized = _normalize_team_name(existing_team)
                    _log(f"Found existing team for {username}: {normalized}")
                    return normalized, False
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        _log(f"Assigning new team to {username}: {new_team}")
        return new_team, True
    except Exception as e:
        _log(f"Team assignment error: {e}")
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        return new_team, True

def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    """Attempt to authenticate via session token. Returns (success, username, token)."""
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id:
            _log("No sessionid in request")
            return False, None, None
        
        from aimodelshare.aws import get_token_from_session, _get_username_from_token
        
        token = get_token_from_session(session_id)
        if not token:
            _log("Failed to get token from session")
            return False, None, None
            
        username = _get_username_from_token(token)
        if not username:
            _log("Failed to extract username from token")
            return False, None, None
        
        _log(f"Session auth successful for {username}")
        return True, username, token
        
    except Exception as e:
        _log(f"Session auth failed: {e}")
        return False, None, None

def _compute_user_stats(username: str, token: str) -> Dict[str, Any]:
    """
    Compute user statistics with caching.
    
    Concurrency Note: Protected by _user_stats_lock for thread-safe
    cache reads and writes.
    """
    now = time.time()
    
    # Thread-safe cache check
    with _user_stats_lock:
        cached = _user_stats_cache.get(username)
        if cached and (now - cached.get("_ts", 0) < USER_STATS_TTL):
            _log(f"User stats cache hit for {username}")
            # Return shallow copy to prevent caller mutations from affecting cache.
            # Stats dict contains only primitives (float, int, str), so shallow copy is sufficient.
            return cached.copy()

    _log(f"Computing fresh stats for {username}")
    leaderboard_df = _fetch_leaderboard(token)
    team_name, _ = _get_or_assign_team(username, leaderboard_df)
    
    stats = {
        "best_score": 0.0,
        "rank": 0,
        "team_name": team_name,
        "submission_count": 0,
        "last_score": 0.0,
        "_ts": time.time()
    }

    try:
        if leaderboard_df is not None and not leaderboard_df.empty:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                stats["submission_count"] = len(user_submissions)
                if "accuracy" in user_submissions.columns:
                    stats["best_score"] = float(user_submissions["accuracy"].max())
                    if "timestamp" in user_submissions.columns:
                        try:
                            user_submissions = user_submissions.copy()
                            user_submissions["timestamp"] = pd.to_datetime(
                                user_submissions["timestamp"], errors="coerce"
                            )
                            recent = user_submissions.sort_values("timestamp", ascending=False).iloc[0]
                            stats["last_score"] = float(recent["accuracy"])
                        except:
                            stats["last_score"] = stats["best_score"]
                    else:
                        stats["last_score"] = stats["best_score"]
            
            if "accuracy" in leaderboard_df.columns:
                user_bests = leaderboard_df.groupby("username")["accuracy"].max()
                ranked = user_bests.sort_values(ascending=False)
                try:
                    stats["rank"] = int(ranked.index.get_loc(username) + 1)
                except KeyError:
                    stats["rank"] = 0
    except Exception as e:
        _log(f"Error computing stats for {username}: {e}")

    # Thread-safe cache update
    with _user_stats_lock:
        _user_stats_cache[username] = stats
    _log(f"Stats for {username}: {stats}")
    return stats
def _build_attempts_tracker_html(current_count, limit=10):
    """
    Generate HTML for the attempts tracker display.
    Shows current attempt count vs limit with color coding.
    
    Args:
        current_count: Number of attempts used so far
        limit: Maximum allowed attempts (default: ATTEMPT_LIMIT)
    
    Returns:
        str: HTML string for the tracker display
    """
    if current_count >= limit:
        # Limit reached - red styling
        bg_color = "#f0f9ff"
        border_color = "#bae6fd"
        text_color = "#0369a1"
        icon = "🛑"
        label = f"Last chance (for now) to boost your score!: {current_count}/{limit}"
    else:
        # Normal - blue styling
        bg_color = "#f0f9ff"
        border_color = "#bae6fd"
        text_color = "#0369a1"
        icon = "📊"
        label = f"Attempts used: {current_count}/{limit}"

    return f"""<div style='text-align:center; padding:8px; margin:8px 0; background:{bg_color}; border-radius:8px; border:1px solid {border_color};'>
        <p style='margin:0; color:{text_color}; font-weight:600; font-size:1rem;'>{icon} {label}</p>
    </div>"""
    
def check_attempt_limit(submission_count: int, limit: int = None) -> Tuple[bool, str]:
    """Check if submission count exceeds limit."""
    # ATTEMPT_LIMIT is defined in configuration section below
    if limit is None:
        limit = ATTEMPT_LIMIT
    
    if submission_count >= limit:
        msg = f"⚠️ Attempt limit reached ({submission_count}/{limit})"
        return False, msg
    return True, f"Attempts: {submission_count}/{limit}"

# -------------------------------------------------------------------------
# Future: Fairness Metrics
# -------------------------------------------------------------------------

# def compute_fairness_metrics(y_true, y_pred, sensitive_attrs):
#     """
#     Compute fairness metrics for model predictions.
#     
#     Args:
#         y_true: Ground truth labels
#         y_pred: Model predictions
#         sensitive_attrs: DataFrame with sensitive attributes (race, sex, age)
#     
#     Returns:
#         dict: Fairness metrics including demographic parity, equalized odds
#     
#     TODO: Implement using fairlearn or aif360
#     """
#     pass



# -------------------------------------------------------------------------
# 1. Configuration
# -------------------------------------------------------------------------

MY_PLAYGROUND_ID = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"

# --- Submission Limit Configuration ---
# Maximum number of successful leaderboard submissions per user per session.
# Preview runs (pre-login) and failed/invalid attempts do NOT count toward this limit.
# Only actual successful playground.submit_model() calls increment the count.
#
# TODO: Server-side persistent enforcement recommended
# The current attempt limit is stored in gr.State (per-session) and can be bypassed
# by refreshing the browser. For production use with 100+ concurrent users,
# consider implementing server-side persistence via Redis or Firestore to track
# attempt counts per user across sessions.
ATTEMPT_LIMIT = 10

# --- Leaderboard Polling Configuration ---
# After a real authenticated submission, we poll the leaderboard to detect eventual consistency.
# This prevents the "stuck on first preview KPI" issue where the leaderboard hasn't updated yet.
# Increased from 12 to 60 to better tolerate backend latency and cold starts.
# If polling times out, optimistic fallback logic will provide provisional UI updates.
LEADERBOARD_POLL_TRIES = 60  # Number of polling attempts (increased to handle backend latency/cold starts)
LEADERBOARD_POLL_SLEEP = 1.0  # Sleep duration between polls (seconds)
ENABLE_AUTO_RESUBMIT_AFTER_READY = False  # Future feature flag for auto-resubmit

# -------------------------------------------------------------------------
# MODEL DEFINITIONS (Updated for I18n)
# -------------------------------------------------------------------------

MODEL_TYPES = {
    "The Balanced Generalist": {
        "model_builder": lambda: LogisticRegression(
            max_iter=500, random_state=42, class_weight="balanced"
        ),
        "key": "mod_bal",
        "desc_key": "desc_bal"  # <--- This key is required for translations
    },
    "The Rule-Maker": {
        "model_builder": lambda: DecisionTreeClassifier(
            random_state=42, class_weight="balanced"
        ),
        "key": "mod_rule",
        "desc_key": "desc_rule"
    },
    "The 'Nearest Neighbor'": {
        "model_builder": lambda: KNeighborsClassifier(),
        "key": "mod_knn",
        "desc_key": "desc_knn"
    },
    "The Deep Pattern-Finder": {
        "model_builder": lambda: RandomForestClassifier(
            random_state=42, class_weight="balanced"
        ),
        "key": "mod_deep",
        "desc_key": "desc_deep"
    }
}

DEFAULT_MODEL = "The Balanced Generalist"

TEAM_NAMES = [
    "The Moral Champions", "The Justice League", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]
CURRENT_TEAM_NAME = random.choice(TEAM_NAMES)


# --- Feature groups for scaffolding (Weak -> Medium -> Strong) ---
FEATURE_SET_ALL_OPTIONS = [
    ("Juvenile Felony Count", "juv_fel_count"),
    ("Juvenile Misdemeanor Count", "juv_misd_count"),
    ("Other Juvenile Count", "juv_other_count"),
    ("Race", "race"),
    ("Sex", "sex"),
    ("Charge Severity (M/F)", "c_charge_degree"),
    ("Days Before Arrest", "days_b_screening_arrest"),
    ("Age", "age"),
    ("Length of Stay", "length_of_stay"),
    ("Prior Crimes Count", "priors_count"),
]
FEATURE_SET_GROUP_1_VALS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex",
    "c_charge_degree", "days_b_screening_arrest"
]
FEATURE_SET_GROUP_2_VALS = ["c_charge_desc", "age"]
FEATURE_SET_GROUP_3_VALS = ["length_of_stay", "priors_count"]
ALL_NUMERIC_COLS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count",
    "days_b_screening_arrest", "age", "length_of_stay", "priors_count"
]
ALL_CATEGORICAL_COLS = [
    "race", "sex", "c_charge_degree"
]
DEFAULT_FEATURE_SET = FEATURE_SET_GROUP_1_VALS


# --- Data Size config ---
DATA_SIZE_MAP = {
    "Small (20%)": 0.2,
    "Medium (60%)": 0.6,
    "Large (80%)": 0.8,
    "Full (100%)": 1.0
}
DEFAULT_DATA_SIZE = "Small (20%)"


MAX_ROWS = 4000
TOP_N_CHARGE_CATEGORICAL = 50
WARM_MINI_ROWS = 300  # Small warm dataset for instant preview
CACHE_MAX_AGE_HOURS = 24  # Cache validity duration
np.random.seed(42)

# Global state containers (populated during initialization)
playground = None
X_TRAIN_RAW = None # Keep this for 100%
X_TEST_RAW = None
Y_TRAIN = None
Y_TEST = None
# Add a container for our pre-sampled data
X_TRAIN_SAMPLES_MAP = {}
Y_TRAIN_SAMPLES_MAP = {}

# Warm mini dataset for instant preview
X_TRAIN_WARM = None
Y_TRAIN_WARM = None

# Cache for transformed test sets (for future performance improvements)
TEST_CACHE = {}

# Initialization flags to track readiness state
INIT_FLAGS = {
    "competition": False,
    "dataset_core": False,
    "pre_samples_small": False,
    "pre_samples_medium": False,
    "pre_samples_large": False,
    "pre_samples_full": False,
    "leaderboard": False,
    "default_preprocessor": False,
    "warm_mini": False,
    "errors": []
}

# Lock for thread-safe flag updates
INIT_LOCK = threading.Lock()

# -------------------------------------------------------------------------
# 2. Data & Backend Utilities
# -------------------------------------------------------------------------

def _get_cache_dir():
    """Get or create the cache directory for datasets."""
    cache_dir = Path.home() / ".aimodelshare_cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

def _safe_request_csv(url, cache_filename="compas.csv"):
    """
    Request CSV from URL with local caching.
    Reuses cached file if it exists and is less than CACHE_MAX_AGE_HOURS old.
    """
    cache_dir = _get_cache_dir()
    cache_path = cache_dir / cache_filename
    
    # Check if cache exists and is fresh
    if cache_path.exists():
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - file_time < timedelta(hours=CACHE_MAX_AGE_HOURS):
            return pd.read_csv(cache_path)
    
    # Download fresh data
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))
    
    # Save to cache
    df.to_csv(cache_path, index=False)
    
    return df

def safe_int(value, default=1):
    """
    Safely coerce a value to int, returning default if value is None or invalid.
    Protects against TypeError when Gradio sliders receive None.
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def load_and_prep_data(use_cache=True):
    """
    Load, sample, and prepare raw COMPAS dataset.
    NOW PRE-SAMPLES ALL DATA SIZES and creates warm mini dataset.
    """
    url = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"

    # Use cached version if available
    if use_cache:
        try:
            df = _safe_request_csv(url)
        except Exception as e:
            print(f"Cache failed, fetching directly: {e}")
            response = requests.get(url)
            df = pd.read_csv(StringIO(response.text))
    else:
        response = requests.get(url)
        df = pd.read_csv(StringIO(response.text))

    # Calculate length_of_stay
    try:
        df['c_jail_in'] = pd.to_datetime(df['c_jail_in'])
        df['c_jail_out'] = pd.to_datetime(df['c_jail_out'])
        df['length_of_stay'] = (df['c_jail_out'] - df['c_jail_in']).dt.total_seconds() / (24 * 60 * 60) # in days
    except Exception:
        df['length_of_stay'] = np.nan

    if df.shape[0] > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42)

    feature_columns = ALL_NUMERIC_COLS + ALL_CATEGORICAL_COLS
    feature_columns = sorted(list(set(feature_columns)))

    target_column = "two_year_recid"

    if "c_charge_desc" in df.columns:
        top_charges = df["c_charge_desc"].value_counts().head(TOP_N_CHARGE_CATEGORICAL).index
        df["c_charge_desc"] = df["c_charge_desc"].apply(
            lambda x: x if pd.notna(x) and x in top_charges else "OTHER"
        )

    for col in feature_columns:
        if col not in df.columns:
            if col == 'length_of_stay' and 'length_of_stay' in df.columns:
                continue
            df[col] = np.nan

    X = df[feature_columns].copy()
    y = df[target_column].copy()

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # Pre-sample all data sizes
    global X_TRAIN_SAMPLES_MAP, Y_TRAIN_SAMPLES_MAP, X_TRAIN_WARM, Y_TRAIN_WARM

    X_TRAIN_SAMPLES_MAP["Full (100%)"] = X_train_raw
    Y_TRAIN_SAMPLES_MAP["Full (100%)"] = y_train

    for label, frac in DATA_SIZE_MAP.items():
        if frac < 1.0:
            X_train_sampled = X_train_raw.sample(frac=frac, random_state=42)
            y_train_sampled = y_train.loc[X_train_sampled.index]
            X_TRAIN_SAMPLES_MAP[label] = X_train_sampled
            Y_TRAIN_SAMPLES_MAP[label] = y_train_sampled

    # Create warm mini dataset for instant preview
    warm_size = min(WARM_MINI_ROWS, len(X_train_raw))
    X_TRAIN_WARM = X_train_raw.sample(n=warm_size, random_state=42)
    Y_TRAIN_WARM = y_train.loc[X_TRAIN_WARM.index]



    return X_train_raw, X_test_raw, y_train, y_test


# [NEW]
def _get_slide1_html(lang):
    return f"""
    <div class='slide-content'>
    <div class='panel-box'>
    <h3 style='font-size: 1.5rem; text-align:center; margin-top:0;'>{t(lang, 's1_intro')}</h3>
    <ul style='list-style: none; padding-left: 0; margin-top: 24px; margin-bottom: 24px;'>
        <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'><span style='font-size: 1.5rem; vertical-align: middle;'>✅</span> {t(lang, 's1_li1')}</li>
        <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'><span style='font-size: 1.5rem; vertical-align: middle;'>✅</span> {t(lang, 's1_li2')}</li>
        <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'><span style='font-size: 1.5rem; vertical-align: middle;'>✅</span> {t(lang, 's1_li3')}</li>
    </ul>
    <div style='background:white; padding:16px; border-radius:12px; margin:12px 0; text-align:center;'>
        <div style='display:inline-block; background:#dbeafe; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#0369a1;'>{t(lang, 's1_in')}</h3></div>
        <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
        <div style='display:inline-block; background:#fef3c7; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#92400e;'>{t(lang, 's1_mod')}</h3></div>
        <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
        <div style='display:inline-block; background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#15803d;'>{t(lang, 's1_out')}</h3></div>
    </div>
    <hr style='margin: 24px 0; border-top: 2px solid #c7d2fe;'>
    <h3 style='font-size: 1.5rem; text-align:center;'>{t(lang, 's1_chal_title')}</h3>
    <p style='font-size: 1.1rem; text-align:center; margin-top: 12px;'>{t(lang, 's1_chal_body')}</p>
    <p style='font-size: 1.1rem; text-align:center; margin-top: 12px;'>{t(lang, 's1_rem')}</p>
    </div>
    </div>
    """

# [NEW]
def _get_slide2_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <h3>{t(lang, 's2_miss_head')}</h3>
            <p>{t(lang, 's2_miss_body')}</p>
            <h3>{t(lang, 's2_comp_head')}</h3>
            <p>{t(lang, 's2_comp_body')}</p>
        </div>
        <div class='leaderboard-box' style='max-width: 600px; margin: 16px auto; text-align: center; padding: 16px;'>
            <p style='font-size: 1.1rem; margin:0;'>{t(lang, 's2_join')}</p>
            <h3 style='font-size: 1.75rem; color: #6b7280; margin: 8px 0;'>🛡️ The Ethical Explorers</h3>
        </div>
        <div class='mock-ui-box'>
            <h3>{t(lang, 's2_data_head')}</h3>
            <p>{t(lang, 's2_data_intro')}</p>
            <ol style='list-style-position: inside; padding-left: 20px;'>
                <li>{t(lang, 's2_li1')}
                    <ul style='margin-left: 20px; list-style-type: disc;'><li>{t(lang, 's2_li1_sub')}</li></ul>
                </li>
                <li>{t(lang, 's2_li2')}
                    <ul style='margin-left: 20px; list-style-type: disc;'><li>{t(lang, 's2_li2_sub')}</li></ul>
                </li>
            </ol>
            <h3>{t(lang, 's2_core_head')}</h3>
            <p>{t(lang, 's2_core_body')}</p>
            <p>{t(lang, 's2_ready')}</p>
        </div>
    </div>
    """

# [NEW]
def _get_slide3_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <p>{t(lang, 's3_p1')}</p>
            <h3>{t(lang, 's3_head1')}</h3>
            <p>{t(lang, 's3_p2')}</p>
            <div style='background:white; padding:16px; border-radius:12px; margin:12px 0; text-align:center;'>
                <div style='display:inline-block; background:#dbeafe; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#0369a1;'>{t(lang, 's1_in')}</h3></div>
                <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                <div style='display:inline-block; background:#fef3c7; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#92400e;'>{t(lang, 's1_mod')}</h3></div>
                <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                <div style='display:inline-block; background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#15803d;'>{t(lang, 's1_out')}</h3></div>
            </div>
            <p>{t(lang, 's3_eng_note')}</p>
        </div>
        <div class='mock-ui-box'>
            <h3>{t(lang, 's3_comp_head')}</h3>
            <p>{t(lang, 's3_c1')}</p>
            <p>{t(lang, 's3_c2')}</p>
            <p>{t(lang, 's3_c3')}</p>
            <hr>
            <p>{t(lang, 's3_learn')}</p>
        </div>
    </div>
    """

# [NEW]
def _get_slide4_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <p>{t(lang, 's4_p1')}</p>
            <h3>{t(lang, 's4_sec_head')}</h3>
            <p>{t(lang, 's4_sec_body')}</p>
            <h3>{t(lang, 's4_loop_head')}</h3>
            <ol style='list-style-position: inside;'>
                <li>{t(lang, 's4_l1')}</li>
                <li>{t(lang, 's4_l2')}</li>
                <li>{t(lang, 's4_l3')}</li>
            </ol>
        </div>
        <h3>{t(lang, 's4_same')}</h3>
        <div class='step-visual'>
            <div class='step-visual-box'>{t(lang, 's4_v1')}</div><div class='step-visual-arrow'>→</div>
            <div class='step-visual-box'>{t(lang, 's4_v2')}</div><div class='step-visual-arrow'>→</div>
            <div class='step-visual-box'>{t(lang, 's4_v3')}</div><div class='step-visual-arrow'>→</div>
            <div class='step-visual-box'>{t(lang, 's4_v4')}</div>
        </div>
        <div class='leaderboard-box' style='text-align:center;'>
            <p>{t(lang, 's4_tip')}</p>
        </div>
    </div>
    """

# [NEW]
def _get_slide5_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='mock-ui-inner'>
            <p>{t(lang, 's5_intro')}</p>
            <hr style='margin: 16px 0;'>
            <h3 style='margin-top:0;'>{t(lang, 's5_k1')}</h3>
            <div style='font-size: 1rem; margin-bottom:12px;'>{t(lang, 's5_k1_desc')}</div>
            <div class='mock-ui-control-box'>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-on'>◉</span> {t(lang, 's5_m1')}</p>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-off'>○</span> {t(lang, 's5_m2')}</p>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-off'>○</span> {t(lang, 's5_m3')}</p>
            </div>
            <hr style='margin: 24px 0;'>
            <h3>{t(lang, 's5_k2')}</h3>
            <div class='mock-ui-control-box' style='text-align: center;'><p style='font-size: 1.1rem; margin:0;'>{t(lang, 's5_range')}</p></div>
            <div style='margin-top: 16px; font-size: 1rem;'>
                <ul style='list-style-position: inside;'>
                    <li>{t(lang, 's5_k2_desc1')}</li>
                    <li>{t(lang, 's5_k2_desc2')}
                        <ul style='list-style-position: inside; margin-left: 20px;'>
                            <li>{t(lang, 's5_low')}</li>
                            <li>{t(lang, 's5_high')}</li>
                        </ul>
                    </li>
                </ul>
                <p style='color:#b91c1c; font-weight:bold; margin-top:10px;'>{t(lang, 's5_warn')}</p>
            </div>
        </div>
    </div>
    """

# [NEW]
def _get_slide6_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='mock-ui-inner'>
            <p>{t(lang, 's6_intro')}</p>
            <hr style='margin: 16px 0;'>
            <h3 style='margin-top:0;'>{t(lang, 's6_k3')}</h3>
            <div style='font-size: 1rem; margin-bottom:12px;'>{t(lang, 's6_k3_desc')}</div>
            <div class='mock-ui-control-box'>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-on'>☑</span> {t(lang, 's6_behav')}</p>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-off'>☐</span> {t(lang, 's6_demo')}</p>
            </div>
            <p style='margin-top:10px;'>{t(lang, 's6_job')}</p>
            <hr style='margin: 24px 0;'>
            <h3>{t(lang, 's6_k4')}</h3>
            <div style='font-size: 1rem; margin-bottom:12px;'>{t(lang, 's6_k4_desc')}</div>
            <div class='mock-ui-control-box'>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-on'>◉</span> {t(lang, 's6_small')}</p>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-off'>○</span> {t(lang, 's6_full')}</p>
            </div>
        </div>
    </div>
    """

# [NEW]
def _get_slide7_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <p>{t(lang, 's7_p1')}</p>
            <h3>{t(lang, 's7_head1')}</h3>
            <ul style='list-style-position: inside;'>
                <li>{t(lang, 's7_acc')}</li>
                <li>{t(lang, 's7_lead')}</li>
            </ul>
            <h3>{t(lang, 's7_head2')}</h3>
            <ul style='list-style-position: inside;'>
                <li>{t(lang, 's7_comp')}</li>
                <li>{t(lang, 's7_promo')}</li>
            </ul>
            <div style='text-align:center; font-weight:bold; font-size:1.2rem; color:#4f46e5; margin:16px 0;'>
                {t(lang, 's7_ranks')}
            </div>
            <h3>{t(lang, 's7_head3')}</h3>
            <p>{t(lang, 's7_final')}</p>
            <p>{t(lang, 's7_rem')}</p>
        </div>
    </div>
    """
  
def build_login_prompt_html(lang="en"):
    """
    Generate HTML for the login prompt text *only*.
    The styled preview card will be prepended to this.
    """
    return f"""
    <h2 style='color: #111827; margin-top:20px; border-top: 2px solid #e5e7eb; padding-top: 20px;'>{t(lang, 'login_title')}</h2>
    <div style='margin-top:16px; text-align:left; font-size:1rem; line-height:1.6; color:#374151;'>
        <p style='margin:12px 0;'>
            {t(lang, 'login_desc')}
        </p>
        <p style='margin:12px 0;'>
            <strong>{t(lang, 'login_new')}</strong>
            <a href='https://www.modelshare.ai/login' target='_blank' 
                style='color:#4f46e5; text-decoration:underline;'>modelshare.ai/login</a>
        </p>
    </div>
    """
  
def _background_initializer():
    """
    Background thread that performs sequential initialization tasks.
    Updates INIT_FLAGS dict with readiness booleans and captures errors.
    
    Initialization sequence:
    1. Competition object connection
    2. Dataset cached download and core split
    3. Warm mini dataset creation
    4. Progressive sampling: small -> medium -> large -> full
    5. Leaderboard prefetch
    6. Default preprocessor fit on small sample
    """
    global playground, X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST
    
    try:
        # Step 1: Connect to competition
        with INIT_LOCK:
            if playground is None:
                playground = Competition(MY_PLAYGROUND_ID)
            INIT_FLAGS["competition"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Competition connection failed: {str(e)}")
    
    try:
        # Step 2: Load dataset core (train/test split)
        X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_and_prep_data(use_cache=True)
        with INIT_LOCK:
            INIT_FLAGS["dataset_core"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Dataset loading failed: {str(e)}")
        return  # Cannot proceed without data
    
    try:
        # Step 3: Warm mini dataset (already created in load_and_prep_data)
        if X_TRAIN_WARM is not None and len(X_TRAIN_WARM) > 0:
            with INIT_LOCK:
                INIT_FLAGS["warm_mini"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Warm mini dataset failed: {str(e)}")
    
    # Progressive sampling - samples are already created in load_and_prep_data
    # Just mark them as ready sequentially with delays to simulate progressive loading
    
    try:
        # Step 4a: Small sample (20%)
        time.sleep(0.5)  # Simulate processing
        with INIT_LOCK:
            INIT_FLAGS["pre_samples_small"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Small sample failed: {str(e)}")
    
    try:
        # Step 4b: Medium sample (60%)
        time.sleep(0.5)
        with INIT_LOCK:
            INIT_FLAGS["pre_samples_medium"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Medium sample failed: {str(e)}")
    
    try:
        # Step 4c: Large sample (80%)
        time.sleep(0.5)
        with INIT_LOCK:
            INIT_FLAGS["pre_samples_large"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Large sample failed: {str(e)}")
        print(f"✗ Large sample failed: {e}")
    
    try:
        # Step 4d: Full sample (100%)
        print("Background init: Full sample (100%)...")
        time.sleep(0.5)
        with INIT_LOCK:
            INIT_FLAGS["pre_samples_full"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Full sample failed: {str(e)}")
    
    try:
        # Step 5: Leaderboard prefetch (best-effort, unauthenticated)
        # Concurrency Note: Do NOT use os.environ for ambient token - prefetch
        # anonymously to warm the cache for initial page loads.
        if playground is not None:
            _ = _get_leaderboard_with_optional_token(playground, None)
            with INIT_LOCK:
                INIT_FLAGS["leaderboard"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Leaderboard prefetch failed: {str(e)}")
    
    try:
        # Step 6: Default preprocessor on small sample
        _fit_default_preprocessor()
        with INIT_LOCK:
            INIT_FLAGS["default_preprocessor"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Default preprocessor failed: {str(e)}")
        print(f"✗ Default preprocessor failed: {e}")
    

def _fit_default_preprocessor():
    """
    Pre-fit a default preprocessor on the small sample with default features.
    Uses memoized preprocessor builder for efficiency.
    """
    if "Small (20%)" not in X_TRAIN_SAMPLES_MAP:
        return
    
    X_sample = X_TRAIN_SAMPLES_MAP["Small (20%)"]
    
    # Use default feature set
    numeric_cols = [f for f in DEFAULT_FEATURE_SET if f in ALL_NUMERIC_COLS]
    categorical_cols = [f for f in DEFAULT_FEATURE_SET if f in ALL_CATEGORICAL_COLS]
    
    if not numeric_cols and not categorical_cols:
        return
    
    # Use memoized builder
    preprocessor, selected_cols = build_preprocessor(numeric_cols, categorical_cols)
    preprocessor.fit(X_sample[selected_cols])

def start_background_init():
    """
    Start the background initialization thread.
    Should be called once at app creation.
    """
    thread = threading.Thread(target=_background_initializer, daemon=True)
    thread.start()

def poll_init_status():
    """
    Poll the initialization status and return readiness bool.
    Returns empty string for HTML so users don't see the checklist.
    
    Returns:
        tuple: (status_html, ready_bool)
    """
    with INIT_LOCK:
        flags = INIT_FLAGS.copy()
    
    # Determine if minimum requirements met
    ready = flags["competition"] and flags["dataset_core"] and flags["pre_samples_small"]
    
    return "", ready

def get_available_data_sizes():
    """
    Return list of data sizes that are currently available based on init flags.
    """
    with INIT_LOCK:
        flags = INIT_FLAGS.copy()
    
    available = []
    if flags["pre_samples_small"]:
        available.append("Small (20%)")
    if flags["pre_samples_medium"]:
        available.append("Medium (60%)")
    if flags["pre_samples_large"]:
        available.append("Large (80%)")
    if flags["pre_samples_full"]:
        available.append("Full (100%)")
    
    return available if available else ["Small (20%)"]  # Fallback

def _is_ready() -> bool:
    """
    Check if initialization is complete and system is ready for real submissions.
    
    Returns:
        bool: True if competition, dataset, and small sample are initialized
    """
    with INIT_LOCK:
        flags = INIT_FLAGS.copy()
    return flags["competition"] and flags["dataset_core"] and flags["pre_samples_small"]

def _get_user_latest_accuracy(df: Optional[pd.DataFrame], username: str) -> Optional[float]:
    """
    Extract the user's latest submission accuracy from the leaderboard.
    
    Uses timestamp sorting when available; otherwise assumes last row is latest.
    
    Args:
        df: Leaderboard DataFrame
        username: Username to extract accuracy for
    
    Returns:
        float: Latest submission accuracy, or None if not found/invalid
    """
    if df is None or df.empty:
        return None
    
    try:
        user_rows = df[df["username"] == username]
        if user_rows.empty or "accuracy" not in user_rows.columns:
            return None
        
        # Try timestamp-based sorting if available
        if "timestamp" in user_rows.columns:
            user_rows = user_rows.copy()
            user_rows["__parsed_ts"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
            valid_ts = user_rows[user_rows["__parsed_ts"].notna()]
            
            if not valid_ts.empty:
                # Sort by timestamp and get latest
                latest_row = valid_ts.sort_values("__parsed_ts", ascending=False).iloc[0]
                return float(latest_row["accuracy"])
        
        # Fallback: assume last row is latest (append order)
        return float(user_rows.iloc[-1]["accuracy"])
        
    except Exception as e:
        _log(f"Error extracting latest accuracy for {username}: {e}")
        return None

def _get_user_latest_ts(df: Optional[pd.DataFrame], username: str) -> Optional[float]:
    """
    Extract the user's latest valid timestamp from the leaderboard.
    
    Args:
        df: Leaderboard DataFrame
        username: Username to extract timestamp for
    
    Returns:
        float: Latest timestamp as unix epoch, or None if not found/invalid
    """
    if df is None or df.empty:
        return None
    
    try:
        user_rows = df[df["username"] == username]
        if user_rows.empty or "timestamp" not in user_rows.columns:
            return None
        
        # Parse timestamps and get the latest
        user_rows = user_rows.copy()
        user_rows["__parsed_ts"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
        valid_ts = user_rows[user_rows["__parsed_ts"].notna()]
        
        if valid_ts.empty:
            return None
        
        latest_ts = valid_ts["__parsed_ts"].max()
        return latest_ts.timestamp() if pd.notna(latest_ts) else None
    except Exception as e:
        _log(f"Error extracting latest timestamp for {username}: {e}")
        return None

def _user_rows_changed(
    refreshed_leaderboard: Optional[pd.DataFrame],
    username: str,
    old_row_count: int,
    old_best_score: float,
    old_latest_ts: Optional[float] = None,
    old_latest_score: Optional[float] = None
) -> bool:
    """
    Check if user's leaderboard entries have changed after submission.
    
    Used after polling to detect if the leaderboard has updated with the new submission.
    Checks row count (new submission added), best score (score improved), latest timestamp,
    and latest accuracy (handles backend overwrite without append).
    
    Args:
        refreshed_leaderboard: Fresh leaderboard data
        username: Username to check for
        old_row_count: Previous number of submissions for this user
        old_best_score: Previous best accuracy score
        old_latest_ts: Previous latest timestamp (unix epoch), optional
        old_latest_score: Previous latest submission accuracy, optional
    
    Returns:
        bool: True if user has more rows, better score, newer timestamp, or changed latest accuracy
    """
    if refreshed_leaderboard is None or refreshed_leaderboard.empty:
        return False
    
    try:
        user_rows = refreshed_leaderboard[refreshed_leaderboard["username"] == username]
        if user_rows.empty:
            return False
        
        new_row_count = len(user_rows)
        new_best_score = float(user_rows["accuracy"].max()) if "accuracy" in user_rows.columns else 0.0
        new_latest_ts = _get_user_latest_ts(refreshed_leaderboard, username)
        new_latest_score = _get_user_latest_accuracy(refreshed_leaderboard, username)
        
        # Changed if we have more submissions, better score, newer timestamp, or changed latest accuracy
        changed = (new_row_count > old_row_count) or (new_best_score > old_best_score + 0.0001)
        
        # Check timestamp if available
        if old_latest_ts is not None and new_latest_ts is not None:
            changed = changed or (new_latest_ts > old_latest_ts)
        
        # Check latest accuracy change (handles overwrite-without-append case)
        if old_latest_score is not None and new_latest_score is not None:
            accuracy_changed = abs(new_latest_score - old_latest_score) >= 0.00001
            if accuracy_changed:
                _log(f"Latest accuracy changed: {old_latest_score:.4f} -> {new_latest_score:.4f}")
            changed = changed or accuracy_changed
        
        if changed:
            _log(f"User rows changed for {username}:")
            _log(f"  Row count: {old_row_count} -> {new_row_count}")
            _log(f"  Best score: {old_best_score:.4f} -> {new_best_score:.4f}")
            _log(f"  Latest score: {old_latest_score if old_latest_score else 'N/A'} -> {new_latest_score if new_latest_score else 'N/A'}")
            _log(f"  Timestamp: {old_latest_ts} -> {new_latest_ts}")
        
        return changed
    except Exception as e:
        _log(f"Error checking user rows: {e}")
        return False

@functools.lru_cache(maxsize=32)
def _get_cached_preprocessor_config(numeric_cols_tuple, categorical_cols_tuple):
    """
    Create and return preprocessor configuration (memoized).
    Uses tuples for hashability in lru_cache.
    
    Concurrency Note: Uses sparse_output=True for OneHotEncoder to reduce memory
    footprint under concurrent requests. Downstream models that require dense
    arrays (DecisionTree, RandomForest) will convert via .toarray() as needed.
    LogisticRegression and KNeighborsClassifier handle sparse matrices natively.
    
    Returns tuple of (transformers_list, selected_columns) ready for ColumnTransformer.
    """
    numeric_cols = list(numeric_cols_tuple)
    categorical_cols = list(categorical_cols_tuple)
    
    transformers = []
    selected_cols = []
    
    if numeric_cols:
        num_tf = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ])
        transformers.append(("num", num_tf, numeric_cols))
        selected_cols.extend(numeric_cols)
    
    if categorical_cols:
        # Use sparse_output=True to reduce memory footprint
        cat_tf = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))
        ])
        transformers.append(("cat", cat_tf, categorical_cols))
        selected_cols.extend(categorical_cols)
    
    return transformers, selected_cols

def build_preprocessor(numeric_cols, categorical_cols):
    """
    Build a preprocessor using cached configuration.
    The configuration (pipeline structure) is memoized; the actual fit is not.
    
    Note: Returns sparse matrices when categorical columns are present.
    Use _ensure_dense() helper if model requires dense input.
    """
    # Convert to tuples for caching
    numeric_tuple = tuple(sorted(numeric_cols))
    categorical_tuple = tuple(sorted(categorical_cols))
    
    transformers, selected_cols = _get_cached_preprocessor_config(numeric_tuple, categorical_tuple)
    
    # Create new ColumnTransformer with cached config
    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    
    return preprocessor, selected_cols

def _ensure_dense(X):
    """
    Convert sparse matrix to dense if necessary.
    
    Helper function for models that don't support sparse input
    (DecisionTree, RandomForest). LogisticRegression and KNN
    handle sparse matrices natively.
    """
    from scipy import sparse
    if sparse.issparse(X):
        return X.toarray()
    return X

def tune_model_complexity(model, level):
    """
    Map a 1–10 slider value to model hyperparameters.
    Levels 1–3: Conservative / simple
    Levels 4–7: Balanced
    Levels 8–10: Aggressive / risk of overfitting
    """
    level = int(level)
    if isinstance(model, LogisticRegression):
        c_map = {1: 0.01, 2: 0.025, 3: 0.05, 4: 0.1, 5: 0.25, 6: 0.5, 7: 1.0, 8: 2.0, 9: 5.0, 10: 10.0}
        model.C = c_map.get(level, 1.0)
        model.max_iter = max(getattr(model, "max_iter", 0), 500)
    elif isinstance(model, RandomForestClassifier):
        depth_map = {1: 3, 2: 5, 3: 7, 4: 9, 5: 11, 6: 15, 7: 20, 8: 25, 9: None, 10: None}
        est_map = {1: 20, 2: 30, 3: 40, 4: 60, 5: 80, 6: 100, 7: 120, 8: 150, 9: 180, 10: 220}
        model.max_depth = depth_map.get(level, 10)
        model.n_estimators = est_map.get(level, 100)
    elif isinstance(model, DecisionTreeClassifier):
        depth_map = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 8, 7: 10, 8: 12, 9: 15, 10: None}
        model.max_depth = depth_map.get(level, 6)
    elif isinstance(model, KNeighborsClassifier):
        k_map = {1: 100, 2: 75, 3: 60, 4: 50, 5: 40, 6: 30, 7: 25, 8: 15, 9: 7, 10: 3}
        model.n_neighbors = k_map.get(level, 25)
    return model

# --- New Helper Functions for HTML Generation ---

def _normalize_team_name(name: str) -> str:
    """
    Normalize team name for consistent comparison and storage.
    
    Strips leading/trailing whitespace and collapses multiple spaces into single spaces.
    This ensures consistent formatting across environment variables, state, and leaderboard rendering.
    
    Args:
        name: Team name to normalize (can be None or empty)
    
    Returns:
        str: Normalized team name, or empty string if input is None/empty
    
    Examples:
        >>> _normalize_team_name("  The Ethical Explorers  ")
        'The Ethical Explorers'
        >>> _normalize_team_name("The  Moral   Champions")
        'The Moral Champions'
        >>> _normalize_team_name(None)
        ''
    """
    if not name:
        return ""
    return " ".join(str(name).strip().split())



def _build_skeleton_leaderboard(rows=6, is_team=True, submit_button_label="5. 🔬 Build & Submit Model"):
    context_label = "Team" if is_team else "Individual"
    return f"""
    <div class='lb-placeholder' aria-live='polite'>
        <div class='lb-placeholder-title'>{context_label} Standings Pending</div>
        <div class='lb-placeholder-sub'>
            <p style='margin:0 0 6px 0;'>Submit your first model to populate this table.</p>
            <p style='margin:0;'><strong>Click “{submit_button_label}” (bottom-left)</strong> to begin!</p>
        </div>
    </div>
    """
def build_login_prompt_html(lang="en"):
    """
    Generate HTML for the login prompt text *only*.
    The styled preview card will be prepended to this.
    """
    return f"""
    <h2 style='color: #111827; margin-top:20px; border-top: 2px solid #e5e7eb; padding-top: 20px;'>{t(lang, 'login_title')}</h2>
    <div style='margin-top:16px; text-align:left; font-size:1rem; line-height:1.6; color:#374151;'>
        <p style='margin:12px 0;'>
            {t(lang, 'login_desc')}
        </p>
        <p style='margin:12px 0;'>
            <strong>{t(lang, 'login_new')}</strong>
            <a href='https://www.modelshare.ai/login' target='_blank' 
                style='color:#4f46e5; text-decoration:underline;'>modelshare.ai/login</a>
        </p>
    </div>
    """

# [CHANGED] - Added lang parameter and t() calls
def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count, is_preview=False, is_pending=False, local_test_accuracy=None, lang="en"):
    """Generates the HTML for the KPI feedback card with translations."""

    if is_pending:
        title = "⏳ Processing..."
        acc_color = "#3b82f6"
        acc_text = f"{(local_test_accuracy * 100):.2f}%" if local_test_accuracy is not None else "N/A"
        acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Pending update...</p>"
        border_color = acc_color
        rank_color = "#6b7280"
        rank_text = "..."
        rank_diff_html = ""

    elif is_preview:
        title = "🔬 " + t(lang, 'kpi_preview')
        acc_color = "#16a34a"
        acc_text = f"{(new_score * 100):.2f}%" if new_score > 0 else "N/A"
        acc_diff_html = ""
        border_color = acc_color
        rank_color = "#3b82f6"
        rank_text = "N/A"
        rank_diff_html = ""

    elif submission_count == 0:
        title = t(lang, 'kpi_first')
        acc_color = "#16a34a"
        acc_text = f"{(new_score * 100):.2f}%"
        acc_diff_html = ""
        rank_color = "#3b82f6"
        rank_text = f"#{new_rank}"
        rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>{t(lang, 'kpi_on_board')}</p>"
        border_color = acc_color

    else:
        score_diff = new_score - last_score
        if abs(score_diff) < 0.0001:
            title = t(lang, 'kpi_success')
            acc_color = "#6b7280"
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>{t(lang, 'kpi_no_change')}</p>"
            border_color = acc_color
        elif score_diff > 0:
            title = t(lang, 'kpi_success')
            acc_color = "#16a34a"
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>+{(score_diff * 100):.2f} (⬆️)</p>"
            border_color = acc_color
        else:
            title = t(lang, 'kpi_lower')
            acc_color = "#ef4444"
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>{(score_diff * 100):.2f} (⬇️)</p>"
            border_color = acc_color

        rank_diff = last_rank - new_rank
        rank_color = "#3b82f6"
        rank_text = f"#{new_rank}"
        if last_rank == 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>{t(lang, 'kpi_on_board')}</p>"
        elif rank_diff > 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #16a34a; margin:0;'>🚀 {t(lang, 'kpi_moved_up')} {rank_diff}!</p>"
        elif rank_diff < 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #ef4444; margin:0;'>🔻 {t(lang, 'kpi_dropped')} {abs(rank_diff)}</p>"
        else:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {rank_color}; margin:0;'>{t(lang, 'kpi_no_change')}</p>"

    return f"""
    <div class='kpi-card' style='border-color: {border_color};'>
        <h2 style='color: #111827; margin-top:0;'>{title}</h2>
        <div class='kpi-card-body'>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>{t(lang, 'kpi_new_acc')}</p>
                <p class='kpi-score' style='color: {acc_color};'>{acc_text}</p>
                {acc_diff_html}
            </div>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>{t(lang, 'kpi_rank')}</p>
                <p class='kpi-score' style='color: {rank_color};'>{rank_text}</p>
                {rank_diff_html}
            </div>
        </div>
    </div>
    """
  
def build_standing_html(user_stats, lang="en"):
    """
    Generates the HTML for Slide 1 (User Standing/Stats).
    Includes logic to translate Team Names.
    """
    # Helper to translate team names specifically
    def get_team_name(name):
        if not name: return "N/A"
        # Try to find the team name in the current language dictionary
        # If not found (e.g. custom team or english fallback), return original
        if lang in TRANSLATIONS and name in TRANSLATIONS[lang]:
            return TRANSLATIONS[lang][name]
        return name

    # 1. Authenticated View (User has a score)
    if user_stats.get("is_signed_in") and user_stats.get("best_score") is not None:
        best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
        rank_text = f"#{user_stats['rank']}" if user_stats.get("rank") else "N/A"
        
        # Translate the team name
        raw_team = user_stats.get("team_name", "")
        team_text = get_team_name(raw_team)
        
        team_rank_text = f"#{user_stats['team_rank']}" if user_stats.get("team_rank") else "N/A"
        
        return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                {t(lang, 's1_title_auth')}
            </h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    {t(lang, 's1_sub_auth')}
                </p>
                <div class='stat-grid'>
                    <div class='stat-card stat-card--success'>
                        <p class='stat-card__label'>{t(lang, 'lbl_best_acc')}</p>
                        <p class='stat-card__value'>{best_score_pct}</p>
                    </div>
                    <div class='stat-card stat-card--accent'>
                        <p class='stat-card__label'>{t(lang, 'lbl_ind_rank')}</p>
                        <p class='stat-card__value'>{rank_text}</p>
                    </div>
                </div>
                <div class='team-card'>
                    <p class='team-card__label'>{t(lang, 'lbl_team')}</p>
                    <p class='team-card__value'>🛡️ {team_text}</p>
                    <p class='team-card__rank'>{t(lang, 'lbl_team_rank')} {team_rank_text}</p>
                </div>
                <ul class='bullet-list'>
                    <li>{t(lang, 's1_li1')}</li>
                    <li>{t(lang, 's1_li2')}</li>
                    <li>{t(lang, 's1_li3')}</li>
                    <li>{t(lang, 's1_li4')}</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>
                    {t(lang, 's1_congrats')}
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    {t(lang, 's1_box_title')}
                </p>
                <p>
                    {t(lang, 's1_box_text')}
                </p>
            </div>
        </div>
        """
        
    # 2. Guest/Pre-submission View (Logged in but no score)
    elif user_stats.get("is_signed_in"):
        return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                {t(lang, 's1_title_guest')}
            </h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    {t(lang, 's1_sub_guest')}
                </p>
                <ul class='bullet-list'>
                    <li>{t(lang, 's1_li1_guest')}</li>
                    <li>{t(lang, 's1_li2_guest')}</li>
                    <li>{t(lang, 's1_li3_guest')}</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>
                    {t(lang, 's1_ready')}
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    {t(lang, 's1_box_title')}
                </p>
                <p>
                    {t(lang, 's1_box_text')}
                </p>
            </div>
        </div>
        """
        
    # 3. No Session View (Not logged in)
    else:
        return f"""
        <div class='slide-shell slide-shell--warning' style='text-align:center;'>
            <h2 class='slide-shell__title'>
                {t(lang, 'loading_session')}
            </h2>
        </div>
        """
      
def _build_team_html(team_summary_df, team_name, lang="en"):
    """
    Generates the HTML for the team leaderboard with TRANSLATED names.
    """
    if team_summary_df is None or team_summary_df.empty:
        return f"<p style='text-align:center; color:#6b7280; padding-top:20px;'>{t(lang, 'summary_empty')}</p>" # Assuming you have this key, or use hardcoded text

    # Normalize the current user's team name for comparison logic
    normalized_user_team = _normalize_team_name(team_name).lower()

    header = f"""
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>{t(lang, 'lbl_rank')}</th> <th>{t(lang, 'lbl_team')}</th> <th>{t(lang, 'lbl_best_acc')}</th> <th>Avg Score</th> 
                <th>Submissions</th>
            </tr>
        </thead>
        <tbody>
    """

    body = ""
    for index, row in team_summary_df.iterrows():
        # 1. Get English Name from Data
        raw_team_name = row['Team']
        
        # 2. Translate it for Display
        display_team_name = t_team(raw_team_name, lang)

        # 3. Logic Check (Use RAW English name for comparison)
        normalized_row_team = _normalize_team_name(raw_team_name).lower()
        is_user_team = normalized_row_team == normalized_user_team
        
        row_class = "class='user-row-highlight'" if is_user_team else ""
        
        body += f"""
        <tr {row_class}>
            <td>{index}</td>
            <td>{display_team_name}</td>
            <td>{(row['Best_Score'] * 100):.2f}%</td>
            <td>{(row['Avg_Score'] * 100):.2f}%</td>
            <td>{row['Submissions']}</td>
        </tr>
        """

    footer = "</tbody></table>"
    return header + body + footer
  

def _build_individual_html(individual_summary_df, username):
    """Generates the HTML for the individual leaderboard."""
    if individual_summary_df is None or individual_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>No individual submissions yet.</p>"

    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Engineer</th>
                <th>Best_Score</th>
                <th>Submissions</th>
            </tr>
        </thead>
        <tbody>
    """

    body = ""
    for index, row in individual_summary_df.iterrows():
        is_user = row["Engineer"] == username
        row_class = "class='user-row-highlight'" if is_user else ""
        body += f"""
        <tr {row_class}>
            <td>{index}</td>
            <td>{row['Engineer']}</td>
            <td>{(row['Best_Score'] * 100):.2f}%</td>
            <td>{row['Submissions']}</td>
        </tr>
        """

    footer = "</tbody></table>"
    return header + body + footer




# --- End Helper Functions ---

def generate_competitive_summary(leaderboard_df, team_name, username, last_submission_score, last_rank, submission_count, lang="en"):
    """
    Build summaries, HTML, and KPI card.
    
    Concurrency Note: Uses the team_name parameter directly for team highlighting,
    NOT os.environ, to prevent cross-user data leakage under concurrent requests.
    
    Returns (team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score).
    """
    team_summary_df = pd.DataFrame(columns=["Team", "Best_Score", "Avg_Score", "Submissions"])
    individual_summary_df = pd.DataFrame(columns=["Engineer", "Best_Score", "Submissions"])

    # 1. Handle Empty Leaderboard
    if leaderboard_df is None or leaderboard_df.empty or "accuracy" not in leaderboard_df.columns:
        return (
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Leaderboard empty.</p>",
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Leaderboard empty.</p>",
            # Pass lang to KPI builder for "Preview/N/A" text localization
            _build_kpi_card_html(0, 0, 0, 0, 0, is_preview=False, is_pending=False, local_test_accuracy=None, lang=lang), 
            0.0, 0, 0.0
        )

    # 2. Generate Team Summary
    if "Team" in leaderboard_df.columns:
        team_summary_df = (
            leaderboard_df.groupby("Team")["accuracy"]
            .agg(Best_Score="max", Avg_Score="mean", Submissions="count")
            .reset_index()
            .sort_values("Best_Score", ascending=False)
            .reset_index(drop=True)
        )
        team_summary_df.index = team_summary_df.index + 1

    # 3. Generate Individual Summary
    user_bests = leaderboard_df.groupby("username")["accuracy"].max()
    user_counts = leaderboard_df.groupby("username")["accuracy"].count()
    individual_summary_df = pd.DataFrame(
        {"Engineer": user_bests.index, "Best_Score": user_bests.values, "Submissions": user_counts.values}
    ).sort_values("Best_Score", ascending=False).reset_index(drop=True)
    individual_summary_df.index = individual_summary_df.index + 1

    # 4. Extract Stats for KPI Card
    new_rank = 0
    new_best_accuracy = 0.0
    this_submission_score = 0.0

    try:
        # Get all submissions for this user
        user_rows = leaderboard_df[leaderboard_df["username"] == username].copy()

        if not user_rows.empty:
            # Attempt robust timestamp parsing to find the absolute latest score
            if "timestamp" in user_rows.columns:
                parsed_ts = pd.to_datetime(user_rows["timestamp"], errors="coerce")

                if parsed_ts.notna().any():
                    # At least one valid timestamp → use parsed ordering
                    user_rows["__parsed_ts"] = parsed_ts
                    user_rows = user_rows.sort_values("__parsed_ts", ascending=False)
                    this_submission_score = float(user_rows.iloc[0]["accuracy"])
                else:
                    # All timestamps invalid → assume append order, take last as "latest"
                    this_submission_score = float(user_rows.iloc[-1]["accuracy"])
            else:
                # No timestamp column → fallback to last row
                this_submission_score = float(user_rows.iloc[-1]["accuracy"])

        # Get Rank & Best Accuracy from the pre-calculated summary
        my_rank_row = individual_summary_df[individual_summary_df["Engineer"] == username]
        if not my_rank_row.empty:
            new_rank = my_rank_row.index[0]
            new_best_accuracy = float(my_rank_row["Best_Score"].iloc[0])

    except Exception as e:
        _log(f"Latest submission score extraction failed: {e}")

    # 5. Generate HTML outputs
    team_html = _build_team_html(team_summary_df, team_name, lang=lang)
    individual_html = _build_individual_html(individual_summary_df, username)
    
    # Pass lang to KPI builder
    kpi_card_html = _build_kpi_card_html(
        new_score=this_submission_score,
        last_score=last_submission_score,
        new_rank=new_rank,
        last_rank=last_rank,
        submission_count=submission_count,
        is_preview=False,
        is_pending=False,
        local_test_accuracy=None,
        lang=lang
    )

    return team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score


def get_model_card(model_name, lang="en"):
    """Get localized model description."""
    if model_name not in MODEL_TYPES:
        return "No description available."
    # MODEL_TYPES now contains "desc_key" instead of raw text
    key = MODEL_TYPES[model_name]["desc_key"]
    return t(lang, key)

def compute_rank_settings(submission_count, current_model, current_complexity, current_feature_set, current_data_size, lang="en"):
    """Returns rank gating settings with localized messages."""
    
    if submission_count == 0:
        return {
            "rank_message": t(lang, 'rank_trainee'),
            "model_choices": ["The Balanced Generalist"],
            "model_value": "The Balanced Generalist",
            "model_interactive": False,
            "complexity_max": 3,
            "complexity_value": min(current_complexity, 3),
            "feature_set_choices": [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in FEATURE_SET_GROUP_1_VALS],
            "feature_set_value": FEATURE_SET_GROUP_1_VALS,
            "feature_set_interactive": False,
            "data_size_choices": ["Small (20%)"],
            "data_size_value": "Small (20%)",
            "data_size_interactive": False,
        }
    elif submission_count == 1:
        return {
            "rank_message": t(lang, 'rank_junior'),
            "model_choices": ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"],
            "model_value": current_model if current_model in ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"] else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 6,
            "complexity_value": min(current_complexity, 6),
            "feature_set_choices": [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in (FEATURE_SET_GROUP_1_VALS + FEATURE_SET_GROUP_2_VALS)],
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)"],
            "data_size_value": current_data_size if current_data_size in ["Small (20%)", "Medium (60%)"] else "Small (20%)",
            "data_size_interactive": True,
        }
    elif submission_count == 2:
        return {
            "rank_message": t(lang, 'rank_senior'),
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Deep Pattern-Finder",
            "model_interactive": True,
            "complexity_max": 8,
            "complexity_value": min(current_complexity, 8),
            "feature_set_choices": FEATURE_SET_ALL_OPTIONS,
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)",
            "data_size_interactive": True,
        }
    else:
        return {
            "rank_message": t(lang, 'rank_lead'),
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 10,
            "complexity_value": current_complexity,
            "feature_set_choices": FEATURE_SET_ALL_OPTIONS,
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)",
            "data_size_interactive": True,
        }

# Find components by name to yield updates
# --- Existing global component placeholders ---
submit_button = None
submission_feedback_display = None
team_leaderboard_display = None
individual_leaderboard_display = None
last_submission_score_state = None 
last_rank_state = None 
best_score_state = None
submission_count_state = None
rank_message_display = None
model_type_radio = None
complexity_slider = None
feature_set_checkbox = None
data_size_radio = None
attempts_tracker_display = None
team_name_state = None
# Login components
login_username = None
login_password = None
login_submit = None
login_error = None
# Add missing placeholders for auth states (FIX)
username_state = None
token_state = None
first_submission_score_state = None  # (already commented as "will be assigned globally")
# Add state placeholders for readiness gating and preview tracking
readiness_state = None
was_preview_state = None
kpi_meta_state = None
last_seen_ts_state = None  # Track last seen user timestamp from leaderboard


def get_or_assign_team(username, token=None):
    """
    Get the existing team for a user from the leaderboard, or assign a new random team.
    
    Queries the playground leaderboard to check if the user has prior submissions with
    a team assignment. If found, returns that team (most recent if multiple submissions).
    Otherwise assigns a random team. All team names are normalized for consistency.
    
    Args:
        username: str, the username to check for existing team
        token: str, optional authentication token for leaderboard fetch
    
    Returns:
        tuple: (team_name: str, is_new: bool)
            - team_name: The normalized team name (existing or newly assigned)
            - is_new: True if newly assigned, False if existing team recovered
    """
    try:
        # Query the leaderboard
        if playground is None:
            # Fallback to random assignment if playground not available
            print("Playground not available, assigning random team")
            new_team = _normalize_team_name(random.choice(TEAM_NAMES))
            return new_team, True
        
        # Use centralized helper for authenticated leaderboard fetch
        leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
        
        # Check if leaderboard has data and Team column
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            # Filter for this user's submissions
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            
            if not user_submissions.empty:
                # Sort by timestamp (most recent first) if timestamp column exists
                # Use contextlib.suppress for resilient timestamp parsing
                if "timestamp" in user_submissions.columns:
                    try:
                        # Attempt to coerce timestamp column to datetime and sort descending
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(user_submissions["timestamp"], errors='coerce')
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                        print(f"Sorted {len(user_submissions)} submissions by timestamp for {username}")
                    except Exception as ts_error:
                        # If timestamp parsing fails, continue with unsorted DataFrame
                        print(f"Warning: Could not sort by timestamp for {username}: {ts_error}")
                
                # Get the most recent team assignment (first row after sorting)
                existing_team = user_submissions.iloc[0]["Team"]
                
                # Check if team value is valid (not null/empty)
                if pd.notna(existing_team) and existing_team and str(existing_team).strip():
                    normalized_team = _normalize_team_name(existing_team)
                    print(f"Found existing team for {username}: {normalized_team}")
                    return normalized_team, False
        
        # No existing team found - assign random
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        print(f"Assigning new team to {username}: {new_team}")
        return new_team, True
        
    except Exception as e:
        # On any error, fall back to random assignment
        print(f"Error checking leaderboard for team: {e}")
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        print(f"Fallback: assigning random team to {username}: {new_team}")
        return new_team, True

def perform_inline_login(username_input, password_input):
    """
    Perform inline authentication and return credentials via gr.State updates.
    
    Concurrency Note: This function NO LONGER stores per-user credentials in
    os.environ to prevent cross-user data leakage. Authentication state is
    returned exclusively via gr.State updates (username_state, token_state,
    team_name_state). Password is never stored server-side.
    
    Args:
        username_input: str, the username entered by user
        password_input: str, the password entered by user
    
    Returns:
        dict: Gradio component updates for login UI elements and submit button
            - On success: hides login form, shows success message, enables submit
            - On failure: keeps login form visible, shows error with signup link
    """
    from aimodelshare.aws import get_aws_token
    
    # Validate inputs
    if not username_input or not username_input.strip():
        error_html = """
        <div style='background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:500;'>⚠️ Username is required</p>
        </div>
        """
        return {
            login_username: gr.update(),
            login_password: gr.update(),
            login_submit: gr.update(),
            login_error: gr.update(value=error_html, visible=True),
            submit_button: gr.update(),
            submission_feedback_display: gr.update(),
            team_name_state: gr.update(),
            username_state: gr.update(),
            token_state: gr.update()
        }
    
    if not password_input or not password_input.strip():
        error_html = """
        <div style='background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:500;'>⚠️ Password is required</p>
        </div>
        """
        return {
            login_username: gr.update(),
            login_password: gr.update(),
            login_submit: gr.update(),
            login_error: gr.update(value=error_html, visible=True),
            submit_button: gr.update(),
            submission_feedback_display: gr.update(),
            team_name_state: gr.update(),
            username_state: gr.update(),
            token_state: gr.update()
        }
    
    # Concurrency Note: get_aws_token() reads credentials from os.environ, which creates
    # a race condition in multi-threaded environments. We use _auth_lock to serialize
    # credential injection, preventing concurrent requests from seeing each other's
    # credentials. The password is immediately cleared after the auth attempt.
    # 
    # FUTURE: Ideally get_aws_token() would be refactored to accept credentials as
    # parameters instead of reading from os.environ. This lock is a workaround.
    username_clean = username_input.strip()
    
    # Attempt to get AWS token with serialized credential injection
    try:
        with _auth_lock:
            os.environ["username"] = username_clean
            os.environ["password"] = password_input.strip()  # Only for get_aws_token() call
            try:
                token = get_aws_token()
            finally:
                # SECURITY: Always clear credentials from environment, even on exception
                # Also clear stale env vars from previous implementations within the lock
                # to prevent any race conditions during cleanup
                os.environ.pop("password", None)
                os.environ.pop("username", None)
                os.environ.pop("AWS_TOKEN", None)
                os.environ.pop("TEAM_NAME", None)
        
        # Get or assign team for this user with explicit token (already normalized by get_or_assign_team)
        team_name, is_new_team = get_or_assign_team(username_clean, token=token)
        # Normalize team name before storing (defensive - already normalized by get_or_assign_team)
        team_name = _normalize_team_name(team_name)
        
        # Build success message based on whether team is new or existing
        if is_new_team:
            team_message = f"You have been assigned to a new team: <b>{team_name}</b> 🎉"
        else:
            team_message = f"Welcome back! You remain on team: <b>{team_name}</b> ✅"
        
        # Success: hide login form, show success message with team info, enable submit button
        success_html = f"""
        <div style='background:#f0fdf4; padding:16px; border-radius:8px; border-left:4px solid #16a34a; margin-top:12px;'>
            <p style='margin:0; color:#15803d; font-weight:600; font-size:1.1rem;'>✓ Signed in successfully!</p>
            <p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>
                {team_message}
            </p>
            <p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>
                Click "Build & Submit Model" again to publish your score.
            </p>
        </div>
        """
        return {
            login_username: gr.update(visible=False),
            login_password: gr.update(visible=False),
            login_submit: gr.update(visible=False),
            login_error: gr.update(value=success_html, visible=True),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            submission_feedback_display: gr.update(visible=False),
            team_name_state: gr.update(value=team_name),
            username_state: gr.update(value=username_clean),
            token_state: gr.update(value=token)
        }
        
    except Exception as e:
        # Note: Credentials are already cleaned up by the finally block in the try above.
        # The lock ensures no race condition during cleanup.
        
        # Authentication failed: show error with signup link
        error_html = f"""
        <div style='background:#fef2f2; padding:16px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:600; font-size:1.1rem;'>⚠️ Authentication failed</p>
            <p style='margin:8px 0; color:#7f1d1d; font-size:0.95rem;'>
                Could not verify your credentials. Please check your username and password.
            </p>
            <p style='margin:8px 0 0 0; color:#7f1d1d; font-size:0.95rem;'>
                <strong>New user?</strong> Create a free account at 
                <a href='https://www.modelshare.ai/login' target='_blank' 
                   style='color:#dc2626; text-decoration:underline;'>modelshare.ai/login</a>
            </p>
            <details style='margin-top:12px; font-size:0.85rem; color:#7f1d1d;'>
                <summary style='cursor:pointer;'>Technical details</summary>
                <pre style='margin-top:8px; padding:8px; background:#fee; border-radius:4px; overflow-x:auto;'>{str(e)}</pre>
            </details>
        </div>
        """
        return {
            login_username: gr.update(visible=True),
            login_password: gr.update(visible=True),
            login_submit: gr.update(visible=True),
            login_error: gr.update(value=error_html, visible=True),
            submit_button: gr.update(),
            submission_feedback_display: gr.update(),
            team_name_state: gr.update(),
            username_state: gr.update(),
            token_state: gr.update()
        }



# -------------------------------------------------------------------------
# Conclusion helpers (dark/light mode aware)
# -------------------------------------------------------------------------
def build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set, lang="en"):
    """
    Build the final conclusion HTML with performance summary.
    Colors are handled via CSS classes so that light/dark mode work correctly.
    """
    # 1. Calculate Tier Progress
    # Tiers: 0=Trainee, 1=Junior, 2=Senior, 3=Lead
    unlocked_tiers = min(3, max(0, submissions - 1))
    
    # Localized Tier Names (Add these keys to your TRANSLATIONS dict)
    tier_labels = [
        t(lang, "tier_trainee"), 
        t(lang, "tier_junior"), 
        t(lang, "tier_senior"), 
        t(lang, "tier_lead")
    ]
    
    # Build the visual "Trainee -> Junior -> ..." line
    reached = tier_labels[: unlocked_tiers + 1]
    tier_line_html = " → ".join([f"{label}{' ✅' if label in reached else ''}" for label in tier_labels])

    # 2. Calculate Improvement
    improvement = (best_score - first_score) if (first_score is not None and submissions > 1) else 0.0
    
    # 3. Check Strong Predictors
    strong_predictors = {"age", "length_of_stay", "priors_count", "age_cat"}
    strong_used = [f for f in feature_set if f in strong_predictors]
    strong_txt = ", ".join(strong_used) if strong_used else t(lang, "none_yet")

    # 4. Dynamic Tip (if few submissions)
    tip_html = ""
    if submissions < 2:
        tip_html = f"""
        <div class="final-conclusion-tip">
          <b>{t(lang, 'tip_label')}</b> {t(lang, 'concl_tip_body')}
        </div>
        """

    # 5. Attempt Cap Message (if limit reached)
    attempt_cap_html = ""
    if submissions >= ATTEMPT_LIMIT:
        attempt_cap_html = f"""
        <div class="final-conclusion-attempt-cap">
          <p style="margin:0;">
            <b>📊 {t(lang, 'limit_title')}:</b> {t(lang, 'limit_body').format(limit=ATTEMPT_LIMIT)}
          </p>
        </div>
        """

    # 6. Return Full HTML
    return f"""
    <div class="final-conclusion-root">
      <h1 class="final-conclusion-title">{t(lang, 'concl_title')}</h1>
      
      <div class="final-conclusion-card">
        <h2 class="final-conclusion-subtitle">{t(lang, 'concl_snapshot')}</h2>
        
        <ul class="final-conclusion-list">
          <li>🏁 <b>{t(lang, 'lbl_best_acc')}:</b> {(best_score * 100):.2f}%</li>
          <li>📊 <b>{t(lang, 'concl_rank_achieved')}:</b> {('#' + str(rank)) if rank > 0 else '—'}</li>
          <li>🔁 <b>{t(lang, 'concl_subs_made')}:</b> {submissions}{' / ' + str(ATTEMPT_LIMIT) if submissions >= ATTEMPT_LIMIT else ''}</li>
          <li>🧗 <b>{t(lang, 'concl_improvement')}:</b> {(improvement * 100):+.2f}</li>
          <li>🎖️ <b>{t(lang, 'concl_tier_prog')}:</b> {tier_line_html}</li>
          <li>🧪 <b>{t(lang, 'concl_strong_pred')}:</b> {len(strong_used)} ({strong_txt})</li>
        </ul>

        {tip_html}

        <div class="final-conclusion-ethics">
          <p style="margin:0;"><b>{t(lang, 'concl_eth_ref')}:</b> {t(lang, 'concl_eth_body')}</p>
        </div>

        {attempt_cap_html}

        <hr class="final-conclusion-divider" />

        <div class="final-conclusion-next">
          <h2>➡️ {t(lang, 'concl_next_title')}</h2>
          <p>{t(lang, 'concl_next_body')}</p>
          <h1 class="final-conclusion-scroll">{t(lang, 's6_scroll')}</h1>
        </div>
      </div>
    </div>
    """


def build_conclusion_from_state(best_score, submissions, rank, first_score, feature_set, lang="en"):
    return build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set, lang)
  
def create_model_building_game_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """
    Create (but do not launch) the model building game app.
    """
    start_background_init()

    # Add missing globals (FIX)
    global submit_button, submission_feedback_display, team_leaderboard_display
    global individual_leaderboard_display, last_submission_score_state, last_rank_state
    global best_score_state, submission_count_state, first_submission_score_state
    global rank_message_display, model_type_radio, complexity_slider
    global feature_set_checkbox, data_size_radio
    global login_username, login_password, login_submit, login_error
    global attempts_tracker_display, team_name_state
    global username_state, token_state  # <-- Added
    global readiness_state, was_preview_state, kpi_meta_state  # <-- Added for parameter shadowing guards
    global last_seen_ts_state  # <-- Added for timestamp tracking
    
    css = """
    /* ------------------------------
      Shared Design Tokens (local)
      ------------------------------ */

    /* We keep everything driven by Gradio theme vars:
      --body-background-fill, --body-text-color, --secondary-text-color,
      --border-color-primary, --block-background-fill, --color-accent,
      --shadow-drop, --prose-background-fill
    */

    :root {
        --slide-radius-md: 12px;
        --slide-radius-lg: 16px;
        --slide-radius-xl: 18px;
        --slide-spacing-lg: 24px;

        /* Local, non-brand tokens built *on top of* theme vars */
        --card-bg-soft: var(--block-background-fill);
        --card-bg-strong: var(--prose-background-fill, var(--block-background-fill));
        --card-border-subtle: var(--border-color-primary);
        --accent-strong: var(--color-accent);
        --text-main: var(--body-text-color);
        --text-muted: var(--secondary-text-color);
    }

    /* ------------------------------------------------------------------
      Base Layout Helpers
      ------------------------------------------------------------------ */

    .slide-content {
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Shared card-like panels used throughout slides */
    .panel-box {
        background: var(--card-bg-soft);
        padding: 20px;
        border-radius: var(--slide-radius-lg);
        border: 2px solid var(--card-border-subtle);
        margin-bottom: 18px;
        color: var(--text-main);
        box-shadow: var(--shadow-drop, 0 2px 4px rgba(0,0,0,0.04));
    }

    .leaderboard-box {
        background: var(--card-bg-soft);
        padding: 20px;
        border-radius: var(--slide-radius-lg);
        border: 1px solid var(--card-border-subtle);
        margin-top: 12px;
        color: var(--text-main);
    }

    /* For “explanatory UI” scaffolding */
    .mock-ui-box {
        background: var(--card-bg-strong);
        border: 2px solid var(--card-border-subtle);
        padding: 24px;
        border-radius: var(--slide-radius-lg);
        color: var(--text-main);
    }

    .mock-ui-inner {
        background: var(--block-background-fill);
        border: 1px solid var(--card-border-subtle);
        padding: 24px;
        border-radius: var(--slide-radius-md);
    }

    /* “Control box” inside the mock UI */
    .mock-ui-control-box {
        padding: 12px;
        background: var(--block-background-fill);
        border-radius: 8px;
        border: 1px solid var(--card-border-subtle);
    }

    /* Little radio / check icons */
    .mock-ui-radio-on {
        font-size: 1.5rem;
        vertical-align: middle;
        color: var(--accent-strong);
    }

    .mock-ui-radio-off {
        font-size: 1.5rem;
        vertical-align: middle;
        color: var(--text-muted);
    }

    .mock-ui-slider-text {
        font-size: 1.5rem;
        margin: 0;
        color: var(--accent-strong);
        letter-spacing: 4px;
    }

    .mock-ui-slider-bar {
        color: var(--text-muted);
    }

    /* Simple mock button representation */
    .mock-button {
        width: 100%;
        font-size: 1.25rem;
        font-weight: 600;
        padding: 16px 24px;
        background-color: var(--accent-strong);
        color: var(--body-background-fill);
        border: none;
        border-radius: 8px;
        cursor: not-allowed;
    }

    /* Step visuals on slides */
    .step-visual {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        align-items: center;
        margin: 24px 0;
        text-align: center;
        font-size: 1rem;
    }

    .step-visual-box {
        padding: 16px;
        background: var(--block-background-fill);   /* ✅ theme-aware */
        border-radius: 8px;
        border: 2px solid var(--border-color-primary);
        margin: 5px;
        color: var(--body-text-color);              /* optional, safe */
    }

    .step-visual-arrow {
        font-size: 2rem;
        margin: 5px;
        /* no explicit color – inherit from theme or override in dark mode */
    }

    /* ------------------------------------------------------------------
      KPI Card (score feedback)
      ------------------------------------------------------------------ */

    .kpi-card {
        background: var(--card-bg-strong);
        border: 2px solid var(--accent-strong);
        padding: 24px;
        border-radius: var(--slide-radius-lg);
        text-align: center;
        max-width: 600px;
        margin: auto;
        color: var(--text-main);
        box-shadow: var(--shadow-drop, 0 4px 6px -1px rgba(0,0,0,0.08));
        min-height: 200px; /* prevent layout shift */
    }

    .kpi-card-body {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        align-items: flex-end;
        margin-top: 24px;
    }

    .kpi-metric-box {
        min-width: 150px;
        margin: 10px;
    }

    .kpi-label {
        font-size: 1rem;
        color: var(--text-muted);
        margin: 0;
    }

    .kpi-score {
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.1;
        color: var(--accent-strong);
    }

    .kpi-subtext-muted {
        font-size: 1.2rem;
        font-weight: 500;
        color: var(--text-muted);
        margin: 0;
        padding-top: 8px;
    }

    /* Small variants to hint semantic state without hard-coded colors */
    .kpi-card--neutral {
        border-color: var(--card-border-subtle);
    }

    .kpi-card--subtle-accent {
        border-color: var(--accent-strong);
    }

    .kpi-score--muted {
        color: var(--text-muted);
    }

    /* ------------------------------------------------------------------
      Leaderboard Table + Placeholder
      ------------------------------------------------------------------ */

    .leaderboard-html-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        font-size: 1rem;
        color: var(--text-main);
        min-height: 300px; /* Stable height */
    }

    .leaderboard-html-table thead {
        background: var(--block-background-fill);
    }

    .leaderboard-html-table th {
        padding: 12px 16px;
        font-size: 0.9rem;
        color: var(--text-muted);
        font-weight: 500;
    }

    .leaderboard-html-table tbody tr {
        border-bottom: 1px solid var(--card-border-subtle);
    }

    .leaderboard-html-table td {
        padding: 12px 16px;
    }

    .leaderboard-html-table .user-row-highlight {
        background: rgba( var(--color-accent-rgb, 59,130,246), 0.1 );
        font-weight: 600;
        color: var(--accent-strong);
    }

    /* Static placeholder (no shimmer, no animation) */
    .lb-placeholder {
        min-height: 300px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: var(--block-background-fill);
        border: 1px solid var(--card-border-subtle);
        border-radius: 12px;
        padding: 40px 20px;
        text-align: center;
    }

    .lb-placeholder-title {
        font-size: 1.25rem;
        font-weight: 500;
        color: var(--text-muted);
        margin-bottom: 8px;
    }

    .lb-placeholder-sub {
        font-size: 1rem;
        color: var(--text-muted);
    }

    /* ------------------------------------------------------------------
      Processing / “Experiment running” status
      ------------------------------------------------------------------ */

    .processing-status {
        background: var(--block-background-fill);
        border: 2px solid var(--accent-strong);
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        box-shadow: var(--shadow-drop, 0 4px 6px rgba(0,0,0,0.12));
        animation: pulse-indigo 2s infinite;
        color: var(--text-main);
    }

    .processing-icon {
        font-size: 4rem;
        margin-bottom: 10px;
        display: block;
        animation: spin-slow 3s linear infinite;
    }

    .processing-text {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--accent-strong);
    }

    .processing-subtext {
        font-size: 1.1rem;
        color: var(--text-muted);
        margin-top: 8px;
    }

    /* Pulse & spin animations */
    @keyframes pulse-indigo {
        0%   { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
        70%  { box-shadow: 0 0 0 15px rgba(99, 102, 241, 0); }
        100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
    }

    @keyframes spin-slow {
        from { transform: rotate(0deg); }
        to   { transform: rotate(360deg); }
    }

    /* Conclusion arrow pulse */
    @keyframes pulseArrow {
        0%   { transform: scale(1);     opacity: 1; }
        50%  { transform: scale(1.08);  opacity: 0.85; }
        100% { transform: scale(1);     opacity: 1; }
    }

    @media (prefers-reduced-motion: reduce) {
        [style*='pulseArrow'] {
            animation: none !important;
        }
        .processing-status,
        .processing-icon {
            animation: none !important;
        }
    }

    /* ------------------------------------------------------------------
      Attempts Tracker + Init Banner + Alerts
      ------------------------------------------------------------------ */

    .init-banner {
        background: var(--card-bg-strong);
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 16px;
        border: 1px solid var(--card-border-subtle);
        color: var(--text-main);
    }

    .init-banner__text {
        margin: 0;
        font-weight: 500;
        color: var(--text-muted);
    }

    /* Attempts tracker shell */
    .attempts-tracker {
        text-align: center;
        padding: 8px;
        margin: 8px 0;
        background: var(--block-background-fill);
        border-radius: 8px;
        border: 1px solid var(--card-border-subtle);
    }

    .attempts-tracker__text {
        margin: 0;
        font-weight: 600;
        font-size: 1rem;
        color: var(--accent-strong);
    }

    /* Limit reached variant – we *still* stick to theme colors */
    .attempts-tracker--limit .attempts-tracker__text {
        color: var(--text-main);
    }

    /* Generic alert helpers used in inline login messages */
    .alert {
        padding: 12px 16px;
        border-radius: 8px;
        margin-top: 12px;
        text-align: left;
        font-size: 0.95rem;
    }

    .alert--error {
        border-left: 4px solid var(--accent-strong);
        background: var(--block-background-fill);
        color: var(--text-main);
    }

    .alert--success {
        border-left: 4px solid var(--accent-strong);
        background: var(--block-background-fill);
        color: var(--text-main);
    }

    .alert__title {
        margin: 0;
        font-weight: 600;
        color: var(--text-main);
    }

    .alert__body {
        margin: 8px 0 0 0;
        color: var(--text-muted);
    }

    /* ------------------------------------------------------------------
      Navigation Loading Overlay
      ------------------------------------------------------------------ */

    #nav-loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: color-mix(in srgb, var(--body-background-fill) 90%, transparent);
        z-index: 9999;
        display: none;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .nav-spinner {
        width: 50px;
        height: 50px;
        border: 5px solid var(--card-border-subtle);
        border-top: 5px solid var(--accent-strong);
        border-radius: 50%;
        animation: nav-spin 1s linear infinite;
        margin-bottom: 20px;
    }

    @keyframes nav-spin {
        0%   { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    #nav-loading-text {
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--accent-strong);
    }

    /* ------------------------------------------------------------------
      Utility: Image inversion for dark mode (if needed)
      ------------------------------------------------------------------ */

    .dark-invert-image {
        filter: invert(0);
    }

    @media (prefers-color-scheme: dark) {
        .dark-invert-image {
            filter: invert(1) hue-rotate(180deg);
        }
    }

    /* ------------------------------------------------------------------
      Dark Mode Specific Fine Tuning
      ------------------------------------------------------------------ */

    @media (prefers-color-scheme: dark) {
        .panel-box,
        .leaderboard-box,
        .mock-ui-box,
        .mock-ui-inner,
        .processing-status,
        .kpi-card {
            background: color-mix(in srgb, var(--block-background-fill) 85%, #000 15%);
            border-color: color-mix(in srgb, var(--card-border-subtle) 70%, var(--accent-strong) 30%);
        }

        .leaderboard-html-table thead {
            background: color-mix(in srgb, var(--block-background-fill) 75%, #000 25%);
        }

        .lb-placeholder {
            background: color-mix(in srgb, var(--block-background-fill) 75%, #000 25%);
        }

        #nav-loading-overlay {
            background: color-mix(in srgb, #000 70%, var(--body-background-fill) 30%);
        }
    }
    
    /* ---------- Conclusion Card Theme Tokens ---------- */

    /* Light theme defaults */
    :root,
    :root[data-theme="light"] {
        --conclusion-card-bg: #e0f2fe;          /* light sky */
        --conclusion-card-border: #0369a1;      /* sky-700 */
        --conclusion-card-fg: #0f172a;          /* slate-900 */

        --conclusion-tip-bg: #fef9c3;           /* amber-100 */
        --conclusion-tip-border: #f59e0b;       /* amber-500 */
        --conclusion-tip-fg: #713f12;           /* amber-900 */

        --conclusion-ethics-bg: #fef2f2;        /* red-50 */
        --conclusion-ethics-border: #ef4444;    /* red-500 */
        --conclusion-ethics-fg: #7f1d1d;        /* red-900 */

        --conclusion-attempt-bg: #fee2e2;       /* red-100 */
        --conclusion-attempt-border: #ef4444;   /* red-500 */
        --conclusion-attempt-fg: #7f1d1d;       /* red-900 */

        --conclusion-next-fg: #0f172a;          /* main text color */
    }

    /* Dark theme overrides – keep contrast high on dark background */
    [data-theme="dark"] {
        --conclusion-card-bg: #020617;          /* slate-950 */
        --conclusion-card-border: #38bdf8;      /* sky-400 */
        --conclusion-card-fg: #e5e7eb;          /* slate-200 */

        --conclusion-tip-bg: rgba(250, 204, 21, 0.08);   /* soft amber tint */
        --conclusion-tip-border: #facc15;                /* amber-400 */
        --conclusion-tip-fg: #facc15;

        --conclusion-ethics-bg: rgba(248, 113, 113, 0.10); /* soft red tint */
        --conclusion-ethics-border: #f97373;               /* red-ish */
        --conclusion-ethics-fg: #fecaca;

        --conclusion-attempt-bg: rgba(248, 113, 113, 0.16);
        --conclusion-attempt-border: #f97373;
        --conclusion-attempt-fg: #fee2e2;

        --conclusion-next-fg: #e5e7eb;
    }

    /* ---------- Conclusion Layout ---------- */

    .app-conclusion-wrapper {
        text-align: center;
    }

    .app-conclusion-title {
        font-size: 2.4rem;
        margin: 0;
    }

    .app-conclusion-card {
        margin-top: 24px;
        max-width: 950px;
        margin-left: auto;
        margin-right: auto;
        padding: 28px;
        border-radius: 18px;
        border-width: 3px;
        border-style: solid;
        background: var(--conclusion-card-bg);
        border-color: var(--conclusion-card-border);
        color: var(--conclusion-card-fg);
        box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
    }

    .app-conclusion-subtitle {
        margin-top: 0;
        font-size: 1.5rem;
    }

    .app-conclusion-metrics {
        list-style: none;
        padding: 0;
        font-size: 1.05rem;
        text-align: left;
        max-width: 640px;
        margin: 20px auto;
    }

    /* ---------- Generic panel helpers reused here ---------- */

    .app-panel-tip,
    .app-panel-critical,
    .app-panel-warning {
        padding: 16px;
        border-radius: 12px;
        border-left-width: 6px;
        border-left-style: solid;
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.4;
        margin-top: 16px;
    }

    .app-panel-title {
        margin: 0 0 4px 0;
        font-weight: 700;
    }

    .app-panel-body {
        margin: 0;
    }

    /* Specific variants */

    .app-conclusion-tip.app-panel-tip {
        background: var(--conclusion-tip-bg);
        border-left-color: var(--conclusion-tip-border);
        color: var(--conclusion-tip-fg);
    }

    .app-conclusion-ethics.app-panel-critical {
        background: var(--conclusion-ethics-bg);
        border-left-color: var(--conclusion-ethics-border);
        color: var(--conclusion-ethics-fg);
    }

    .app-conclusion-attempt-cap.app-panel-warning {
        background: var(--conclusion-attempt-bg);
        border-left-color: var(--conclusion-attempt-border);
        color: var(--conclusion-attempt-fg);
    }

    /* Divider + next section */

    .app-conclusion-divider {
        margin: 28px 0;
        border: 0;
        border-top: 2px solid rgba(148, 163, 184, 0.8); /* slate-400-ish */
    }

    .app-conclusion-next-title {
        margin: 0;
        color: var(--conclusion-next-fg);
    }

    .app-conclusion-next-body {
        font-size: 1rem;
        color: var(--conclusion-next-fg);
    }

    /* Arrow inherits the same color, keeps pulse animation defined earlier */
    .app-conclusion-arrow {
        margin: 12px 0;
        font-size: 3rem;
        animation: pulseArrow 2.5s infinite;
        color: var(--conclusion-next-fg);
    }

    /* ---------------------------------------------------- */
    /* Final Conclusion Slide (Light Mode Defaults)         */
    /* ---------------------------------------------------- */

    .final-conclusion-root {
        text-align: center;
        color: var(--body-text-color);
    }

    .final-conclusion-title {
        font-size: 2.4rem;
        margin: 0;
    }

    .final-conclusion-card {
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        padding: 28px;
        border-radius: 18px;
        border: 2px solid var(--border-color-primary);
        margin-top: 24px;
        max-width: 950px;
        margin-left: auto;
        margin-right: auto;
        box-shadow: var(--shadow-drop, 0 4px 10px rgba(15, 23, 42, 0.08));
    }

    .final-conclusion-subtitle {
        margin-top: 0;
        margin-bottom: 8px;
    }

    .final-conclusion-list {
        list-style: none;
        padding: 0;
        font-size: 1.05rem;
        text-align: left;
        max-width: 640px;
        margin: 20px auto;
    }

    .final-conclusion-list li {
        margin: 4px 0;
    }

    .final-conclusion-tip {
        margin-top: 16px;
        padding: 16px;
        border-radius: 12px;
        border-left: 6px solid var(--color-accent);
        background-color: color-mix(in srgb, var(--color-accent) 12%, transparent);
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.4;
    }

    .final-conclusion-ethics {
        margin-top: 16px;
        padding: 18px;
        border-radius: 12px;
        border-left: 6px solid #ef4444;
        background-color: color-mix(in srgb, #ef4444 10%, transparent);
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.4;
    }

    .final-conclusion-attempt-cap {
        margin-top: 16px;
        padding: 16px;
        border-radius: 12px;
        border-left: 6px solid #ef4444;
        background-color: color-mix(in srgb, #ef4444 16%, transparent);
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.4;
    }

    .final-conclusion-divider {
        margin: 28px 0;
        border: 0;
        border-top: 2px solid var(--border-color-primary);
    }

    .final-conclusion-next h2 {
        margin: 0;
    }

    .final-conclusion-next p {
        font-size: 1rem;
        margin-top: 4px;
        margin-bottom: 0;
    }

    .final-conclusion-scroll {
        margin: 12px 0 0 0;
        font-size: 3rem;
        animation: pulseArrow 2.5s infinite;
    }

    /* ---------------------------------------------------- */
    /* Dark Mode Overrides for Final Slide                  */
    /* ---------------------------------------------------- */

    @media (prefers-color-scheme: dark) {
        .final-conclusion-card {
            background-color: #0b1120;        /* deep slate */
            color: white;                     /* 100% contrast confidence */
            border-color: #38bdf8;
            box-shadow: none;
        }

        .final-conclusion-tip {
            background-color: rgba(56, 189, 248, 0.18);
        }

        .final-conclusion-ethics {
            background-color: rgba(248, 113, 113, 0.18);
        }

        .final-conclusion-attempt-cap {
            background-color: rgba(248, 113, 113, 0.26);
        }
    }
    /* ---------------------------------------------------- */
    /* Slide 3: INPUT → MODEL → OUTPUT flow (theme-aware)   */
    /* ---------------------------------------------------- */


    .model-flow {
        text-align: center;
        font-weight: 600;
        font-size: 1.2rem;
        margin: 20px 0;
        /* No explicit color – inherit from the card */
    }

    .model-flow-label {
        padding: 0 0.1rem;
        /* No explicit color – inherit */
    }

    .model-flow-arrow {
        margin: 0 0.35rem;
        font-size: 1.4rem;
        /* No explicit color – inherit */
    }

    @media (prefers-color-scheme: dark) {
        .model-flow {
            color: var(--body-text-color);
        }
        .model-flow-arrow {
            /* In dark mode, nudge arrows toward accent for contrast/confidence */
            color: color-mix(in srgb, var(--color-accent) 75%, var(--body-text-color) 25%);
        }
    }
    """


    # Define globals for yield
    global submit_button, submission_feedback_display, team_leaderboard_display
    # --- THIS IS THE FIXED LINE ---
    global individual_leaderboard_display, last_submission_score_state, last_rank_state, best_score_state, submission_count_state, first_submission_score_state
    # --- END OF FIX ---
    global rank_message_display, model_type_radio, complexity_slider
    global feature_set_checkbox, data_size_radio
    global login_username, login_password, login_submit, login_error
    global attempts_tracker_display, team_name_state

    with gr.Blocks(theme=gr.themes.Soft(primary_hue="indigo"), css=css) as demo:
# -----------------------------------------------------------------
        # 1. STATE DEFINITIONS (Must be first!)
        # -----------------------------------------------------------------
        lang_state = gr.State("en")
        
        # Authentication & User States
        username_state = gr.State(None)
        token_state = gr.State(None)
        team_name_state = gr.State(None)
        
        # Game Logic States
        last_submission_score_state = gr.State(0.0)
        last_rank_state = gr.State(0)
        best_score_state = gr.State(0.0)
        submission_count_state = gr.State(0)
        first_submission_score_state = gr.State(None)
        
        # Experiment Logic States (The ones causing your error)
        model_type_state = gr.State(DEFAULT_MODEL)
        complexity_state = gr.State(2)
        feature_set_state = gr.State(DEFAULT_FEATURE_SET) # <--- This fixes the NameError
        data_size_state = gr.State(DEFAULT_DATA_SIZE)
        
        # Control Flags
        readiness_state = gr.State(False)
        was_preview_state = gr.State(False)
        kpi_meta_state = gr.State({})
        last_seen_ts_state = gr.State(None)
        # Persistent top anchor for scroll-to-top navigation
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        
        # Navigation loading overlay with spinner and dynamic message
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        # Concurrency Note: Do NOT read per-user state from os.environ here.
        # Username and other per-user data are managed via gr.State objects
        # and populated during handle_load_with_session_auth.

        # Loading screen
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding:100px 0;'>
                    <h2 style='font-size:2rem; color:#6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )

        # ---------------------------------------------------------
        #  Step 6: Briefing Slideshow Definitions
        # ---------------------------------------------------------
        
        # Slide 1
        with gr.Column(visible=True, elem_id="slide-1") as briefing_slide_1:
            c_s1_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's1_title')}</h1>")
            c_s1_html = gr.HTML(_get_slide1_html("en"))
            briefing_1_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 2
        with gr.Column(visible=False, elem_id="slide-2") as briefing_slide_2:
            c_s2_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's2_title')}</h1>")
            c_s2_html = gr.HTML(_get_slide2_html("en"))
            with gr.Row():
                briefing_2_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_2_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 3
        with gr.Column(visible=False, elem_id="slide-3") as briefing_slide_3:
            c_s3_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's3_title')}</h1>")
            c_s3_html = gr.HTML(_get_slide3_html("en"))
            with gr.Row():
                briefing_3_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_3_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 4
        with gr.Column(visible=False, elem_id="slide-4") as briefing_slide_4:
            c_s4_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's4_title')}</h1>")
            c_s4_html = gr.HTML(_get_slide4_html("en"))
            with gr.Row():
                briefing_4_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_4_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 5
        with gr.Column(visible=False, elem_id="slide-5") as briefing_slide_5:
            c_s5_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's5_title')}</h1>")
            c_s5_html = gr.HTML(_get_slide5_html("en"))
            with gr.Row():
                briefing_5_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_5_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 6
        with gr.Column(visible=False, elem_id="slide-6") as briefing_slide_6:
            c_s6_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's6_title')}</h1>")
            c_s6_html = gr.HTML(_get_slide6_html("en"))
            with gr.Row():
                briefing_6_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_6_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 7
        with gr.Column(visible=False, elem_id="slide-7") as briefing_slide_7:
            c_s7_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's7_title')}</h1>")
            c_s7_html = gr.HTML(_get_slide7_html("en"))
            with gr.Row():
                briefing_7_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_7_next = gr.Button(t('en', 'btn_begin'), variant="primary", size="lg")

        # --- End Briefing Slideshow ---



        #  Step 7: Main Model Building Arena Interface
        # ---------------------------------------------------------
        
        with gr.Column(visible=False, elem_id="model-step") as model_building_step:
            c_app_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 'app_title')}</h1>")
            
            # Status panel for initialization progress - HIDDEN
            init_status_display = gr.HTML(value="", visible=False)
            
            # Banner for UI state
            init_banner = gr.HTML(
              value=(
                  "<div class='init-banner'>"
                  "<p class='init-banner__text'>"
                  "⏳ Initializing data & leaderboard… you can explore but must wait for readiness to submit."
                  "</p>"
                  "</div>"
              ),
              visible=True)

            # Note: State objects defined at top of function (Step 5) are available here.

            rank_message_display = gr.Markdown(t('en', 'rank_trainee'))

            with gr.Row():
                with gr.Column(scale=1):

                    model_type_radio = gr.Radio(
                        label=t('en', 'lbl_model'),
                        choices=list(MODEL_TYPES.keys()),
                        value=DEFAULT_MODEL,
                        interactive=False
                    )
                    # Note: Passing "en" to get_model_card ensures initial load is English
                    model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL, "en"))

                    gr.Markdown("---") # Separator

                    complexity_slider = gr.Slider(
                        label=t('en', 'lbl_complex'),
                        minimum=1, maximum=3, step=1, value=2,
                        info=t('en', 'info_complex')
                    )

                    gr.Markdown("---") # Separator

                    # --- CRITICAL FIX HERE ---
                    feature_set_checkbox = gr.CheckboxGroup(
                        label=t('en', 'lbl_feat'),
                        choices=FEATURE_SET_ALL_OPTIONS, # Uses tuples ("Label", "column_name")
                        value=DEFAULT_FEATURE_SET,       # Uses ["column_name", ...]
                        interactive=False,
                        info=t('en', 'info_feat')
                    )
                    # -------------------------

                    gr.Markdown("---") # Separator

                    data_size_radio = gr.Radio(
                        label=t('en', 'lbl_data'),
                        choices=list(DATA_SIZE_MAP.keys()),
                        value=DEFAULT_DATA_SIZE,
                        interactive=False
                    )

                    gr.Markdown("---") # Separator

                    # Attempt tracker display
                    attempts_tracker_display = gr.HTML(
                        value=_build_attempts_tracker_html(0),
                        visible=True
                    )

                    submit_button = gr.Button(
                        value=t('en', 'btn_submit'),
                        variant="primary",
                        size="lg"
                    )

                with gr.Column(scale=1):
                    with gr.Tabs():
                        with gr.TabItem(t('en', 'tab_team')):
                            team_leaderboard_display = gr.HTML(_build_skeleton_leaderboard(rows=6, is_team=True))
                        with gr.TabItem(t('en', 'tab_ind')):
                            individual_leaderboard_display = gr.HTML(_build_skeleton_leaderboard(rows=6, is_team=False))
                    
                    # KPI Card
                    submission_feedback_display = gr.HTML(
                        f"<p style='text-align:center; color:#6b7280; padding:20px 0;'>Submit your first model to get feedback!</p>"
                    )
                    
                    # Inline Login Components (initially hidden)
                    # Using a Group keeps the layout tidy if you toggle visibility
                    with gr.Group(visible=False) as login_group:
                        login_username = gr.Textbox(
                            label="Username",
                            placeholder="Enter your modelshare.ai username",
                            visible=False
                        )
                        login_password = gr.Textbox(
                            label="Password",
                            type="password",
                            placeholder="Enter your password",
                            visible=False
                        )
                        login_submit = gr.Button(
                            "Sign In & Submit",
                            variant="primary",
                            visible=False
                        )
                        login_error = gr.HTML(
                            value="",
                            visible=False
                        )

            step_2_next = gr.Button(t('en', 'btn_finish'), variant="secondary")
          
        # ---------------------------------------------------------
        #  Step 8: Conclusion Step
        # ---------------------------------------------------------
        
        with gr.Column(visible=False, elem_id="conclusion-step") as conclusion_step:
            # 1. Title (Must match variable c_concl_title used in update_language)
            c_concl_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 'concl_title')}</h1>")
            
            # 2. Final Score Display (Must match variable final_score_display)
            # Initially shows "Preparing..." text until logic replaces it
            final_score_display = gr.HTML(t('en', 'concl_prep'))
            
            # 3. Return Button (Must match variable btn_return used in update_language)
            # Note: We assign it to 'btn_return' for the updater, but we can also 
            # alias it as 'step_3_back' if your navigation logic uses that name.
            btn_return = gr.Button(t('en', 'btn_return'), size="lg")
            step_3_back = btn_return # Alias for navigation compatibility
        # ---------------------------------------------------------
        #  Language Update Logic (Fixed for Responsiveness)
        # ---------------------------------------------------------
        
        def update_language(request: gr.Request):
            """
            Updates all UI text based on ?lang= query param.
            Uses gr.update() to preserve event listeners.
            """
            params = request.query_params
            lang = params.get("lang", "en")
            # Fallback if lang code not found
            if lang not in TRANSLATIONS:
                lang = "en"
            
            # Short helper for cleaner code below
            def txt(k): 
                return t(lang, k)
            
            # Return list must match the order of 'update_targets' exactly
            return [
                # 0. State
                lang,
                
                # 1. Slide 1
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s1_title')}</h1>"),
                gr.update(value=_get_slide1_html(lang)),
                gr.update(value=txt('btn_next')),
                
                # 2. Slide 2
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s2_title')}</h1>"),
                gr.update(value=_get_slide2_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 3. Slide 3
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s3_title')}</h1>"),
                gr.update(value=_get_slide3_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 4. Slide 4
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s4_title')}</h1>"),
                gr.update(value=_get_slide4_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 5. Slide 5
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s5_title')}</h1>"),
                gr.update(value=_get_slide5_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 6. Slide 6
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s6_title')}</h1>"),
                gr.update(value=_get_slide6_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 7. Slide 7
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s7_title')}</h1>"),
                gr.update(value=_get_slide7_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_begin')),
                
                # 8. Main App Interface
                gr.update(value=f"<h1 style='text-align:center;'>{txt('app_title')}</h1>"),
                gr.update(label=txt('lbl_model')),
                gr.update(label=txt('lbl_complex'), info=txt('info_complex')),
                gr.update(label=txt('lbl_feat'), info=txt('info_feat')),
                gr.update(label=txt('lbl_data')),
                gr.update(value=txt('btn_submit')),
                
                # 9. Conclusion
                gr.update(value=f"<h1 style='text-align:center;'>{txt('concl_title')}</h1>"),
                gr.update(value=txt('concl_prep')),
                gr.update(value=txt('btn_return'))
            ]
        # --- Navigation Logic ---
        all_steps_nav = [
            briefing_slide_1, briefing_slide_2, briefing_slide_3,
            briefing_slide_4, briefing_slide_5, briefing_slide_6, briefing_slide_7,
            model_building_step, conclusion_step, loading_screen
        ]

        def create_nav(current_step, next_step):
            """
            Simplified navigation: directly switches visibility without artificial loading screen.
            Loading screen only shown when entering arena if not yet ready.
            """
            def _nav():
                # Direct single-step navigation
                updates = {next_step: gr.update(visible=True)}
                for s in all_steps_nav:
                    if s != next_step:
                        updates[s] = gr.update(visible=False)
                return updates
            return _nav

        def finalize_and_show_conclusion(best_score, submissions, rank, first_score, feature_set):
            """Build dynamic conclusion HTML and navigate to conclusion step."""
            html = build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set)
            updates = {
                conclusion_step: gr.update(visible=True),
                final_score_display: gr.update(value=html)
            }
            for s in all_steps_nav:
                if s != conclusion_step:
                    updates[s] = gr.update(visible=False)
            return [updates[s] if s in updates else gr.update() for s in all_steps_nav] + [html]

        # Helper function to generate navigation JS with loading overlay
        def nav_js(target_id: str, message: str, min_show_ms: int = 1200) -> str:
            """
            Generate JavaScript for enhanced slide navigation with loading overlay.
            
            Args:
                target_id: Element ID of the target slide (e.g., 'slide-2', 'model-step')
                message: Loading message to display during transition
                min_show_ms: Minimum time to show overlay (prevents flicker)
            
            Returns:
                JavaScript arrow function string for Gradio's js parameter
            """
            return f"""
()=>{{
  try {{
    // Show overlay immediately
    const overlay = document.getElementById('nav-loading-overlay');
    const messageEl = document.getElementById('nav-loading-text');
    if(overlay && messageEl) {{
      messageEl.textContent = '{message}';
      overlay.style.display = 'flex';
      setTimeout(() => {{ overlay.style.opacity = '1'; }}, 10);
    }}
    
    const startTime = Date.now();
    
    // Scroll to top after brief delay
    setTimeout(() => {{
      const anchor = document.getElementById('app_top_anchor');
      const container = document.querySelector('.gradio-container') || document.scrollingElement || document.documentElement;
      
      function doScroll() {{
        if(anchor) {{ anchor.scrollIntoView({{behavior:'smooth', block:'start'}}); }}
        else {{ container.scrollTo({{top:0, behavior:'smooth'}}); }}
        
        // Best-effort Colab iframe scroll
        try {{
          if(window.parent && window.parent !== window && window.frameElement) {{
            const top = window.frameElement.getBoundingClientRect().top + window.parent.scrollY;
            window.parent.scrollTo({{top: Math.max(top - 10, 0), behavior:'smooth'}});
          }}
        }} catch(e2) {{}}
      }}
      
      doScroll();
      // Retry scroll to combat layout shifts
      let scrollAttempts = 0;
      const scrollInterval = setInterval(() => {{
        scrollAttempts++;
        doScroll();
        if(scrollAttempts >= 3) clearInterval(scrollInterval);
      }}, 130);
    }}, 40);
    
    // Poll for target visibility and minimum display time
    const targetId = '{target_id}';
    const minShowMs = {min_show_ms};
    let pollCount = 0;
    const maxPolls = 77; // ~7 seconds max
    
    const pollInterval = setInterval(() => {{
      pollCount++;
      const elapsed = Date.now() - startTime;
      const target = document.getElementById(targetId);
      const isVisible = target && target.offsetParent !== null && 
                       window.getComputedStyle(target).display !== 'none';
      
      // Hide overlay when target is visible AND minimum time elapsed
      if((isVisible && elapsed >= minShowMs) || pollCount >= maxPolls) {{
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


        # Wire up slide buttons with enhanced navigation
        briefing_1_next.click(
            fn=create_nav(briefing_slide_1, briefing_slide_2),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-2", "Loading mission overview...")
        )
        briefing_2_back.click(
            fn=create_nav(briefing_slide_2, briefing_slide_1),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-1", "Returning to introduction...")
        )
        briefing_2_next.click(
            fn=create_nav(briefing_slide_2, briefing_slide_3),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-3", "Exploring model concept...")
        )
        briefing_3_back.click(
            fn=create_nav(briefing_slide_3, briefing_slide_2),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-2", "Going back one step...")
        )
        briefing_3_next.click(
            fn=create_nav(briefing_slide_3, briefing_slide_4),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-4", "Understanding the experiment loop...")
        )
        briefing_4_back.click(
            fn=create_nav(briefing_slide_4, briefing_slide_3),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-3", "Reviewing previous concepts...")
        )
        briefing_4_next.click(
            fn=create_nav(briefing_slide_4, briefing_slide_5),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-5", "Configuring brain settings...")
        )
        briefing_5_back.click(
            fn=create_nav(briefing_slide_5, briefing_slide_4),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-4", "Revisiting the loop...")
        )
        briefing_5_next.click(
            fn=create_nav(briefing_slide_5, briefing_slide_6),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-6", "Configuring data inputs...")
        )
        briefing_6_back.click(
            fn=create_nav(briefing_slide_6, briefing_slide_5),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-5", "Adjusting model strategy...")
        )
        briefing_6_next.click(
            fn=create_nav(briefing_slide_6, briefing_slide_7),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-7", "Preparing scoring overview...")
        )
        briefing_7_back.click(
            fn=create_nav(briefing_slide_7, briefing_slide_6),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-6", "Reviewing data knobs...")
        )
        # Slide 7 -> App
        briefing_7_next.click(
            fn=create_nav(briefing_slide_7, model_building_step),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("model-step", "Entering model arena...")
        )

        # App -> Conclusion
        step_2_next.click(
            fn=finalize_and_show_conclusion,
            inputs=[
                best_score_state,
                submission_count_state,
                last_rank_state,
                first_submission_score_state,
                feature_set_state
            ],
            outputs=all_steps_nav + [final_score_display],
            js=nav_js("conclusion-step", "Generating performance summary...")
        )

        # Conclusion -> App
        step_3_back.click(
            fn=create_nav(conclusion_step, model_building_step),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("model-step", "Returning to experiment workspace...")
        )

        # Events
        model_type_radio.change(
            fn=get_model_card,
            inputs=model_type_radio,
            outputs=model_card_display
        )
        model_type_radio.change(
            fn=lambda v: v or DEFAULT_MODEL,
            inputs=model_type_radio,
            outputs=model_type_state
        )
        complexity_slider.change(fn=lambda v: v, inputs=complexity_slider, outputs=complexity_state)

        feature_set_checkbox.change(
            fn=lambda v: v or [],
            inputs=feature_set_checkbox,
            outputs=feature_set_state
        )
        data_size_radio.change(
            fn=lambda v: v or DEFAULT_DATA_SIZE,
            inputs=data_size_radio,
            outputs=data_size_state
        )

        all_outputs = [
            submission_feedback_display,
            team_leaderboard_display,
            individual_leaderboard_display,
            last_submission_score_state,
            last_rank_state,
            best_score_state,
            submission_count_state,
            first_submission_score_state,
            rank_message_display,
            model_type_radio,
            complexity_slider,
            feature_set_checkbox,
            data_size_radio,
            submit_button,
            login_username,
            login_password,
            login_submit,
            login_error,
            attempts_tracker_display,
            was_preview_state,
            kpi_meta_state,
            last_seen_ts_state
        ]

        # Wire up login button
        login_submit.click(
            fn=perform_inline_login,
            inputs=[login_username, login_password],
            outputs=[
                login_username, 
                login_password, 
                login_submit, 
                login_error, 
                submit_button, 
                submission_feedback_display, 
                team_name_state,
                username_state,  # NEW
                token_state      # NEW
            ]
        )

        # Removed gr.State(username) from the inputs list
        submit_button.click(
            fn=run_experiment,
            inputs=[
                model_type_state,             # 1. model_name_key
                complexity_state,             # 2. complexity_level
                feature_set_state,            # 3. feature_set
                data_size_state,              # 4. data_size_str
                team_name_state,              # 5. team_name
                last_submission_score_state,  # 6. last_score
                last_rank_state,              # 7. last_rank
                submission_count_state,       # 8. submission_count
                first_submission_score_state, # 9. first_score
                best_score_state,             # 10. best_score
                username_state,               # 11. username
                token_state,                  # 12. token
                readiness_state,              # 13. readiness (renamed from flag)
                was_preview_state,            # 14. was_preview
                lang_state                    # 15. lang (NEW)
            ],
            outputs=all_outputs,
            show_progress="full",
            js=nav_js("model-step", "Running experiment...", 500)
        )

        # Timer for polling initialization status
        status_timer = gr.Timer(value=0.5, active=True)  # Poll every 0.5 seconds
        
        def update_init_status():
            """
            Poll initialization status and update UI elements.
            Returns status HTML, banner visibility, submit button state, data size choices, and readiness_state.
            """
            status_html, ready = poll_init_status()
            
            # Update banner visibility - hide when ready
            banner_visible = not ready
            
            # Update submit button
            if ready:
                submit_label = "5. 🔬 Build & Submit Model"
                submit_interactive = True
            else:
                submit_label = "⏳ Waiting for data..."
                submit_interactive = False
            
            # Get available data sizes based on init progress
            available_sizes = get_available_data_sizes()
            
            # Stop timer once fully initialized
            timer_active = not (ready and INIT_FLAGS.get("pre_samples_full", False))
            
            return (
                status_html,
                gr.update(visible=banner_visible),
                gr.update(value=submit_label, interactive=submit_interactive),
                gr.update(choices=available_sizes),
                timer_active,
                ready  # readiness_state
            )
        
        status_timer.tick(
            fn=update_init_status,
            inputs=None,
            outputs=[init_status_display, init_banner, submit_button, data_size_radio, status_timer, readiness_state]
        )

        # Handle session-based authentication on page load
        # ---------------------------------------------------------------------
        # Initial Load Logic (Auth + Language + Stats)
        # ---------------------------------------------------------------------
        
# ---------------------------------------------------------------------
        # Initial Load Logic (Auth + Language + Stats + Merge)
        # ---------------------------------------------------------------------
        
        def handle_load(request: gr.Request):
            """
            Unified handler: 
            1. Determines Language
            2. checks Authentication
            3. Computes User Stats
            4. Merges Translated Labels with Logic-Driven Values
            """
            
            # 1. Get visual updates (Labels & Text in correct language)
            visual_updates = update_language(request)
            lang = visual_updates[0] # Extract detected language
            
            # 2. Try Authentication
            success, username, token = _try_session_based_auth(request)
            
            # 3. Compute Stats (if logged in)
            stats = {"best_score": 0.0, "rank": 0, "team_name": "", "submission_count": 0}
            if success and username and token:
                stats = _compute_user_stats(username, token)
                
                # OVERWRITE Slide 1 (Index 2) with Personalized Stats HTML
                # (Index 2 corresponds to c_s1_html in the visual_updates list)
                visual_updates[2] = gr.update(value=build_standing_html(stats, lang))

            # 4. Get Logic Updates (Values, Choices, Interactivity based on Rank)
            # on_initial_load returns: 
            # [0]Card, [1]TeamLB, [2]IndLB, [3]RankMsg, [4]ModelRadio, [5]Cplx, [6]Feat, [7]Data
            logic_results = on_initial_load(username, token, stats["team_name"], lang)

            # 5. MERGE Logic with Translations
            # We need the Labels from 'visual_updates' AND the Values/Choices from 'logic_results'.
            # We merge them manually to avoid overwriting one with the other.
            
            def merge_updates(lbl_upd, val_upd):
                """Combine label translation with value/interactive logic."""
                # Convert both to dicts if they aren't already (gr.update returns dict-like objects)
                l_dict = lbl_upd if isinstance(lbl_upd, dict) else lbl_upd.__dict__
                v_dict = val_upd if isinstance(val_upd, dict) else val_upd.__dict__
                
                # We want Label/Info from Translation, and everything else from Logic
                merged = v_dict.copy()
                merged['label'] = l_dict.get('label')
                if l_dict.get('info'):
                    merged['info'] = l_dict.get('info')
                return gr.update(**merged)

            # Apply merge to the 4 input components
            # Indices based on update_language return order:
            # 29: Model Radio
            # 30: Complexity Slider
            # 31: Feature Checkbox
            # 32: Data Radio
            
            visual_updates[29] = merge_updates(visual_updates[29], logic_results[4])
            visual_updates[30] = merge_updates(visual_updates[30], logic_results[5])
            visual_updates[31] = merge_updates(visual_updates[31], logic_results[6])
            visual_updates[32] = merge_updates(visual_updates[32], logic_results[7])

            # 6. Construct Final Return List
            # Must match the 'load_targets' list structure exactly:
            # [Visuals (37 items)] + [States (8 items)] + [Extra Logic (4 items)]
            
            state_updates = [
                username, 
                token, 
                stats["team_name"], 
                stats.get("last_score", 0.0), 
                stats["rank"], 
                stats["best_score"], 
                stats["submission_count"], 
                None # first_submission_score
            ]
            
            extra_logic_updates = [
                logic_results[0], # Model Card Display
                logic_results[1], # Team Leaderboard
                logic_results[2], # Individual Leaderboard
                logic_results[3]  # Rank Message
            ]

            return visual_updates + state_updates + extra_logic_updates

        # ---------------------------------------------------------------------
        # Load Targets Definition
        # ---------------------------------------------------------------------
        
        # This list maps the output of handle_load to the actual UI components
        load_targets = [
            # --- Visual Targets (Matches update_language order) ---
            lang_state,
            c_s1_title, c_s1_html, briefing_1_next,
            c_s2_title, c_s2_html, briefing_2_back, briefing_2_next,
            c_s3_title, c_s3_html, briefing_3_back, briefing_3_next,
            c_s4_title, c_s4_html, briefing_4_back, briefing_4_next,
            c_s5_title, c_s5_html, briefing_5_back, briefing_5_next,
            c_s6_title, c_s6_html, briefing_6_back, briefing_6_next,
            c_s7_title, c_s7_html, briefing_7_back, briefing_7_next,
            c_app_title, model_type_radio, complexity_slider, feature_set_checkbox, data_size_radio, submit_button,
            c_concl_title, final_score_display, step_3_back,
            
            # --- State Targets ---
            username_state, token_state, team_name_state,
            last_submission_score_state, last_rank_state, best_score_state, submission_count_state, first_submission_score_state,
            
            # --- Extra Logic Targets ---
            model_card_display, 
            team_leaderboard_display, 
            individual_leaderboard_display,
            rank_message_display
        ]
        
        # Trigger on Page Load
        demo.load(handle_load, inputs=None, outputs=load_targets)
        # CORE EXPERIMENT LOGIC (Updated for I18n)
        # ---------------------------------------------------------------------
        def run_experiment(
            model_name_key, complexity_level, feature_set, data_size_str,
            team_name, last_score, last_rank, submission_count, first_score, best_score,
            username, token, readiness, was_preview, lang,
            progress=gr.Progress()
        ):
            """
            Full experiment logic:
            1. Validates inputs
            2. Runs preview on warm dataset if not ready/logged in
            3. Trains full model on requested data size
            4. Submits to cloud (if logged in)
            5. Updates UI with results
            """
            # A. Validate & Setup
            if not model_name_key: model_name_key = DEFAULT_MODEL
            feature_set = feature_set or []
            complexity_level = safe_int(complexity_level, 2)
            
            # Define helper for localized status updates
            def status(step, title_en, sub_en):
                # (Optional) You could add translation keys for these status messages 
                # in the dictionary if you want strict localization for the loading spinner too.
                return f"""
                <div class='processing-status'>
                    <span class='processing-icon'>⚙️</span>
                    <div class='processing-text'>Step {step}/5: {title_en}</div>
                    <div class='processing-subtext'>{sub_en}</div>
                </div>
                """

            # B. Initial Feedback
            progress(0.1, desc="Initializing...")
            yield {
                submission_feedback_display: gr.update(value=status(1, "Initializing", "Preparing data ingredients..."), visible=True),
                submit_button: gr.update(value="⏳ Running...", interactive=False),
                login_error: gr.update(visible=False)
            }

            # C. Check Features
            numeric_cols = [f for f in feature_set if f in ALL_NUMERIC_COLS]
            categorical_cols = [f for f in feature_set if f in ALL_CATEGORICAL_COLS]
            
            if not numeric_cols and not categorical_cols:
                # Error state
                yield {
                    submission_feedback_display: gr.update(value="<p style='color:red; text-align:center;'>⚠️ Error: No features selected.</p>"),
                    submit_button: gr.update(value=t(lang, 'btn_submit'), interactive=True)
                }
                return

            # D. Determine if Preview or Full Run
            # Use warm mini if: Not logged in OR Playground not ready
            is_preview_run = (token is None) or (playground is None)
            
            # Select Data
            if is_preview_run:
                X_train_curr = X_TRAIN_WARM
                y_train_curr = Y_TRAIN_WARM
                # If warm data isn't ready yet, stop
                if X_train_curr is None:
                    yield { submission_feedback_display: gr.update(value="<p style='color:red;'>⚠️ Data not yet loaded. Please wait...</p>"), submit_button: gr.update(interactive=True) }
                    return
            else:
                # Full Run
                X_train_curr = X_TRAIN_SAMPLES_MAP.get(data_size_str, X_TRAIN_SAMPLES_MAP[DEFAULT_DATA_SIZE])
                y_train_curr = Y_TRAIN_SAMPLES_MAP.get(data_size_str, Y_TRAIN_SAMPLES_MAP[DEFAULT_DATA_SIZE])

            # E. Train Model
            progress(0.3, desc="Training...")
            yield { submission_feedback_display: gr.update(value=status(2, "Training", "Learning patterns from history...")) }

            # Build & Fit
            try:
                preprocessor, selected_cols = build_preprocessor(tuple(sorted(numeric_cols)), tuple(sorted(categorical_cols)))
                
                X_train_processed = preprocessor.fit_transform(X_train_curr[selected_cols])
                # Ensure dense if needed
                base_model = MODEL_TYPES[model_name_key]["model_builder"]()
                tuned_model = tune_model_complexity(base_model, complexity_level)
                
                if isinstance(tuned_model, (DecisionTreeClassifier, RandomForestClassifier)):
                    from scipy import sparse
                    if sparse.issparse(X_train_processed): X_train_processed = X_train_processed.toarray()
                
                tuned_model.fit(X_train_processed, y_train_curr)
            except Exception as e:
                print(f"Train Error: {e}")
                yield { submission_feedback_display: gr.update(value=f"<p style='color:red;'>Training Error: {e}</p>"), submit_button: gr.update(interactive=True) }
                return

            # F. Evaluate / Submit
            progress(0.6, desc="Evaluating...")
            
            # Preprocess Test Set
            X_test_processed = preprocessor.transform(X_TEST_RAW[selected_cols])
            if isinstance(tuned_model, (DecisionTreeClassifier, RandomForestClassifier)):
                from scipy import sparse
                if sparse.issparse(X_test_processed): X_test_processed = X_test_processed.toarray()
            
            predictions = tuned_model.predict(X_test_processed)
            local_score = accuracy_score(Y_TEST, predictions)

            # Logic Branch: Preview vs Submit
            if is_preview_run:
                # --- PREVIEW MODE ---
                # Pass lang here
                preview_card = _build_kpi_card_html(local_score, 0, 0, 0, -1, is_preview=True, lang=lang)
                
                # Append Login Prompt if not logged in
                if token is None:
                    preview_card += build_login_prompt_html(lang)

                # Settings for next run (Rank calculation)
                # Preview doesn't increment submission count, so we pass current count
                settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str, lang)

                yield {
                    submission_feedback_display: gr.update(value=preview_card),
                    submit_button: gr.update(value=t(lang, 'btn_submit'), interactive=True),
                    login_username: gr.update(visible=True), login_password: gr.update(visible=True),
                    login_submit: gr.update(visible=True),
                    rank_message_display: gr.update(value=settings["rank_message"]),
                    # Update inputs based on rank
                    model_type_radio: gr.update(choices=settings["model_choices"], interactive=settings["model_interactive"]),
                    complexity_slider: gr.update(maximum=settings["complexity_max"]),
                    feature_set_checkbox: gr.update(choices=[f[0] for f in settings["feature_set_choices"]], interactive=settings["feature_set_interactive"]),
                    data_size_radio: gr.update(choices=settings["data_size_choices"], interactive=settings["data_size_interactive"]),
                    was_preview_state: True
                }
            
            else:
                # --- SUBMISSION MODE ---
                progress(0.8, desc="Submitting...")
                yield { submission_feedback_display: gr.update(value=status(3, "Submitting", "Sending results to leaderboard...")) }
                
                # Submit to Cloud
                try:
                    desc = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})"
                    playground.submit_model(
                        model=tuned_model, preprocessor=preprocessor, prediction_submission=predictions,
                        input_dict={'description': desc}, custom_metadata={'Team': team_name}, token=token
                    )
                except Exception as e:
                    print(f"Submission Warning: {e}") # Non-fatal if local score exists

                # Update Stats
                new_count = submission_count + 1
                new_first_score = first_score if first_score is not None else local_score
                
                # Generate Result Card (Pass lang)
                result_card = _build_kpi_card_html(
                    new_score=local_score, last_score=last_score, 
                    new_rank=0, last_rank=last_rank, # Rank would be updated by next fetch
                    submission_count=new_count, is_preview=False, lang=lang
                )
                
                # Check Limits
                if new_count >= ATTEMPT_LIMIT:
                    result_card += f"<div style='margin-top:15px; border:2px solid red; padding:10px; border-radius:8px; background:#fee;'><b>{t(lang, 'limit_title')}</b></div>"
                    btn_state = gr.update(value="🛑 Limit Reached", interactive=False)
                else:
                    btn_state = gr.update(value=t(lang, 'btn_submit'), interactive=True)

                settings = compute_rank_settings(new_count, model_name_key, complexity_level, feature_set, data_size_str, lang)

                yield {
                    submission_feedback_display: gr.update(value=result_card),
                    submit_button: btn_state,
                    submission_count_state: new_count,
                    last_submission_score_state: local_score,
                    best_score_state: max(best_score, local_score),
                    first_submission_score_state: new_first_score,
                    # Update UI Permissions
                    rank_message_display: gr.update(value=settings["rank_message"]),
                    model_type_radio: gr.update(choices=settings["model_choices"], interactive=settings["model_interactive"]),
                    complexity_slider: gr.update(maximum=settings["complexity_max"]),
                    feature_set_checkbox: gr.update(choices=[f[0] for f in settings["feature_set_choices"]], interactive=settings["feature_set_interactive"]),
                    data_size_radio: gr.update(choices=settings["data_size_choices"], interactive=settings["data_size_interactive"]),
                    # Hide login
                    login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False)
                }
        # ---------------------------------------------------------------------
        # Navigation Logic (Fixed List Return)
        # ---------------------------------------------------------------------
        
        def create_nav(next_step):
            def navigate():
                # Return a list of updates for ALL steps in 'all_steps_nav'
                # 1. Hide everything except the target
                return [gr.update(visible=True) if s == next_step else gr.update(visible=False) for s in all_steps_nav]
            return navigate

        def nav_js(target_id, msg):
            return f"""
            ()=>{{
              const overlay = document.getElementById('nav-loading-overlay');
              if(overlay) {{
                document.getElementById('nav-loading-text').textContent = '{msg}';
                overlay.style.display = 'flex';
                setTimeout(()=>{{ overlay.style.opacity = '1'; }}, 10);
              }}
              setTimeout(()=>{{
                  overlay.style.opacity = '0';
                  setTimeout(()=>{{ overlay.style.display = 'none'; }}, 300);
                  const anchor = document.getElementById('app_top_anchor');
                  if(anchor) anchor.scrollIntoView({{behavior:'smooth', block:'start'}});
              }}, 800);
            }}
            """

        # --- Wiring Navigation Buttons ---
        briefing_1_next.click(fn=create_nav(briefing_slide_2), outputs=all_steps_nav, js=nav_js("slide-2", "Loading..."))
        
        briefing_2_back.click(fn=create_nav(briefing_slide_1), outputs=all_steps_nav, js=nav_js("slide-1", "Back..."))
        briefing_2_next.click(fn=create_nav(briefing_slide_3), outputs=all_steps_nav, js=nav_js("slide-3", "Loading..."))
        
        briefing_3_back.click(fn=create_nav(briefing_slide_2), outputs=all_steps_nav, js=nav_js("slide-2", "Back..."))
        briefing_3_next.click(fn=create_nav(briefing_slide_4), outputs=all_steps_nav, js=nav_js("slide-4", "Loading..."))
        
        briefing_4_back.click(fn=create_nav(briefing_slide_3), outputs=all_steps_nav, js=nav_js("slide-3", "Back..."))
        briefing_4_next.click(fn=create_nav(briefing_slide_5), outputs=all_steps_nav, js=nav_js("slide-5", "Loading..."))
        
        briefing_5_back.click(fn=create_nav(briefing_slide_4), outputs=all_steps_nav, js=nav_js("slide-4", "Back..."))
        briefing_5_next.click(fn=create_nav(briefing_slide_6), outputs=all_steps_nav, js=nav_js("slide-6", "Loading..."))
        
        briefing_6_back.click(fn=create_nav(briefing_slide_5), outputs=all_steps_nav, js=nav_js("slide-5", "Back..."))
        briefing_6_next.click(fn=create_nav(briefing_slide_7), outputs=all_steps_nav, js=nav_js("slide-7", "Loading..."))
        
        briefing_7_back.click(fn=create_nav(briefing_slide_6), outputs=all_steps_nav, js=nav_js("slide-6", "Back..."))
        briefing_7_next.click(fn=create_nav(model_building_step), outputs=all_steps_nav, js=nav_js("model-step", "Entering Arena..."))
        
        # Conclusion Navigation
        step_2_next.click(
            fn=finalize_and_show_conclusion,
            inputs=[best_score_state, submission_count_state, last_rank_state, first_submission_score_state, feature_set_state, lang_state],
            outputs=all_steps_nav + [final_score_display],
            js=nav_js("conclusion-step", "Calculating...")
        )
        
        step_3_back.click(fn=create_nav(model_building_step), outputs=all_steps_nav, js=nav_js("model-step", "Returning..."))

        # --- Logic Wiring ---
        
        # 1. Poll init status (updates banner/button when data is ready)
        status_timer = gr.Timer(value=0.5, active=True)
        status_timer.tick(
            fn=update_init_status,
            outputs=[init_status_display, init_banner, submit_button, data_size_radio, status_timer, readiness_state]
        )

        # 2. Input Events (State Updates)
        # Update model description based on selection AND current language
        model_type_radio.change(lambda m, l: get_model_card(m, l), inputs=[model_type_radio, lang_state], outputs=model_card_display)
        model_type_radio.change(lambda m: m or DEFAULT_MODEL, inputs=model_type_radio, outputs=model_type_state)
        
        complexity_slider.change(lambda v: v, inputs=complexity_slider, outputs=complexity_state)
        feature_set_checkbox.change(lambda v: v or [], inputs=feature_set_checkbox, outputs=feature_set_state)
        data_size_radio.change(lambda v: v or DEFAULT_DATA_SIZE, inputs=data_size_radio, outputs=data_size_state)
        
        # 3. Login Logic
        login_submit.click(
            fn=perform_inline_login,
            inputs=[login_username, login_password],
            outputs=[login_username, login_password, login_submit, login_error, submit_button, submission_feedback_display, team_name_state, username_state, token_state]
        )

        # 4. Submit Experiment Logic (Crucial: lang_state added to inputs)
        submit_button.click(
            fn=run_experiment,
            inputs=[
                model_type_state, 
                complexity_state, 
                feature_set_state, 
                data_size_state,
                team_name_state, 
                last_submission_score_state, 
                last_rank_state,
                submission_count_state, 
                first_submission_score_state, 
                best_score_state,
                username_state, 
                token_state, 
                readiness_state, 
                was_preview_state, 
                lang_state  # <--- I18n support
            ],
            outputs=[
                submission_feedback_display, team_leaderboard_display, individual_leaderboard_display,
                last_submission_score_state, last_rank_state, best_score_state,
                submission_count_state, first_submission_score_state,
                rank_message_display, model_type_radio, complexity_slider, feature_set_checkbox,
                data_size_radio, submit_button, login_username, login_password, login_submit,
                login_error, attempts_tracker_display, was_preview_state, kpi_meta_state, last_seen_ts_state
            ],
            js=nav_js("model-step", "Running Experiment..."),
            show_progress="full"
        )

    return demo
"""
Model Building Game - Gradio application for the Justice & Equity Challenge.

Session-based authentication with leaderboard caching and progressive rank unlocking.

Concurrency Notes:
- This app is designed to run in a multi-threaded environment (Cloud Run).
- Per-user state is stored in gr.State objects, NOT in os.environ.
- Caches are protected by locks to ensure thread safety.
- Linear algebra libraries are constrained to single-threaded mode to prevent
  CPU oversubscription in containerized deployments.
"""

import os

# -------------------------------------------------------------------------
# Thread Limit Configuration (MUST be set before importing numpy/sklearn)
# Prevents CPU oversubscription in containerized environments like Cloud Run.
# -------------------------------------------------------------------------
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import time
import random
import requests
import contextlib
from io import StringIO
import threading
import functools
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, Callable, TypeVar

import numpy as np
import pandas as pd
import gradio as gr

# --- Scikit-learn Imports ---
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier

# --- AI Model Share Imports ---
try:
    from aimodelshare.playground import Competition
except ImportError:
    raise ImportError(
        "The 'aimodelshare' library is required. Install with: pip install aimodelshare"
    )


# -------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# -------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        # --- General & Nav ---
        "title": "🛠️ Model Building Arena",
        "loading": "⏳ Loading...",
        "btn_next": "Next ▶️",
        "btn_back": "◀️ Back",
        "btn_return": "◀️ Back to Experiment",
        "btn_finish": "Finish & Reflect ▶️",
        "btn_begin": "Begin Model Building ▶️",
        "btn_submit": "5. 🔬 Build & Submit Model",
        
        # --- Login ---
        "login_title": "🔐 Sign in to submit & rank",
        "login_desc": "This is a preview run only. Sign in to publish your score to the live leaderboard.",
        "login_new": "New user? Create a free account at",

        # --- Welcome Screen ---
        "welcome_header": "Welcome to <b>{team}</b>!",
        "welcome_body": "Your team is waiting for your help to improve the AI.",
        "welcome_cta": "👈 Click 'Build & Submit Model' to Start Playing!",
        "lb_submit_to_rank": "Submit your model to see where you rank!",

        # --- Slides 1-7 ---
        "s1_title": "🔄 From Understanding to Building",
        "s1_intro": "Great progress! You've now:",
        "s1_li1": "Made tough decisions as a judge using AI predictions",
        "s1_li2": "Learned about false positives and false negatives",
        "s1_li3": "Understood how AI works:",
        "s1_in": "INPUT",
        "s1_mod": "MODEL",
        "s1_out": "OUTPUT",
        "s1_chal_title": "Now it's time to step into the shoes of an AI Engineer.",
        "s1_chal_body": "<strong>Your New Challenge:</strong> Build AI models that are more accurate than the one you used as a judge.",
        "s1_rem": "Remember: You experienced firsthand how AI predictions affect real people's lives. Use that knowledge to build something better.",

        "s2_title": "📋 Your Mission - Build Better AI",
        "s2_miss_head": "The Mission",
        "s2_miss_body": "Build an AI model that helps judges make better decisions. The model you used previously gave you imperfect advice. Your job now is to build a new model that predicts risk more accurately, providing judges with the reliable insights they need to be fair.",
        "s2_comp_head": "The Competition",
        "s2_comp_body": "To do this, you will compete against other engineers! To help you in your mission, you will join an engineering team. Your results will be tracked both individually and as a group in the Live Standings Leaderboards.",
        "s2_join": "You will join a team like...",
        "s2_data_head": "The Data Challenge",
        "s2_data_intro": "To compete, you have access to thousands of old case files. You have two distinct types of information:",
        "s2_li1": "<strong>Defendant Profiles:</strong> This is like what the judge saw at the time of arrest.",
        "s2_li1_sub": "<em>Age, Number of Prior Offenses, Type of Charge.</em>",
        "s2_li2": "<strong>Historical Outcomes:</strong> This is what actually happened to those people later.",
        "s2_li2_sub": "<em>Did they re-offend within 2 years? (Yes/No)</em>",
        "s2_core_head": "The Core Task",
        "s2_core_body": "You need to teach your AI to look at the \"Profiles\" and accurately predict the \"Outcome.\"",
        "s2_ready": "<strong>Ready to build something that could change how justice works?</strong>",

        "s3_title": "🧠 What is a \"Model\"?",
        "s3_p1": "Before we start competing, let's break down exactly what you are building.",
        "s3_head1": "Think of a Model as a \"Prediction Machine.\"",
        "s3_p2": "You already know the flow:",
        "s3_eng_note": "As an engineer, you don't need to write complex code from scratch. Instead, you assemble this machine using three main components.",
        "s3_comp_head": "The 3 Components:",
        "s3_c1": "<strong>1. The Inputs (Data)</strong><br>The information you feed the machine.<br><em>* Examples: Age, Prior Crimes, Charge Details.</em>",
        "s3_c2": "<strong>2. The Model (Prediction Machine)</strong><br>The mathematical \"brain\" that looks for patterns in the inputs.<br><em>* Examples: You will choose different \"brains\" that learn in different ways (e.g., simple rules vs. deep patterns).</em>",
        "s3_c3": "<strong>3. The Output (Prediction)</strong><br>The model's best guess.<br><em>* Example: Risk Level: High or Low.</em>",
        "s3_learn": "<strong>How it learns:</strong> You show the model thousands of old cases (Inputs) + what actually happened (Outcomes). It studies them to find the rules, so it can make predictions on new cases it hasn't seen before.",

        "s4_title": "🔁 How Engineers Work — The Loop",
        "s4_p1": "Now that you know the components of a model, how do you build a better one?",
        "s4_sec_head": "Here is the secret:",
        "s4_sec_body": "Real AI teams almost never get it right on the first try. Instead, they follow a continuous loop of experimentation: <strong>Try, Test, Learn, Repeat.</strong>",
        "s4_loop_head": "The Experiment Loop:",
        "s4_l1": "<strong>Build a Model:</strong> Assemble your components and get a starting prediction accuracy score.",
        "s4_l2": "<strong>Ask a Question:</strong> (e.g., \"What happens if I change the 'Brain' type?\")",
        "s4_l3": "<strong>Test & Compare:</strong> Did the score get better... or did it get worse?",
        "s4_same": "You will do the exact same thing in a competition!",
        "s4_v1": "<b>1. Configure</b><br/>Use Control Knobs to select Strategy and Data.",
        "s4_v2": "<b>2. Submit</b><br/>Click \"Build & Submit\" to train your model.",
        "s4_v3": "<b>3. Analyze</b><br/>Check your rank on the Live Leaderboard.",
        "s4_v4": "<b>4. Refine</b><br/>Change one setting and submit again!",
        "s4_tip": "<strong>Pro Tip:</strong> Try to change only one thing at a time. If you change too many things at once, you won't know what made your model better or worse!",

        "s5_title": "🎛️ Control Knobs — The \"Brain\" Settings",
        "s5_intro": "To build your model, you will use Control Knobs to configure your Prediction Machine. The first two knobs allow you to choose a type of model and adjust how it learns patterns in data.",
        "s5_k1": "1. Model Strategy (Type of Model)",
        "s5_k1_desc": "<b>What it is:</b> The specific mathematical method the machine uses to find patterns.",
        "s5_m1": "<b>The Balanced Generalist:</b> A reliable, all-purpose algorithm. It provides stable results across most data.",
        "s5_m2": "<b>The Rule-Maker:</b> Creates strict \"If... Then...\" logic (e.g., If prior crimes > 2, then High Risk).",
        "s5_m3": "<b>The Deep Pattern-Finder:</b> A complex algorithm designed to detect subtle, hidden connections in the data.",
        "s5_k2": "2. Model Complexity (Fitting Level)",
        "s5_range": "Range: Level 1 ─── ● ─── 10",
        "s5_k2_desc1": "<b>What it is:</b> Tunes how tightly the machine fits its logic to find patterns in the data.",
        "s5_k2_desc2": "<b>The Trade-off:</b>",
        "s5_low": "<b>Low (Level 1):</b> Captures only the broad, obvious trends.",
        "s5_high": "<b>High (Level 5):</b> Captures every tiny detail and variation.",
        "s5_warn": "Warning: Setting this too high causes the machine to \"memorize\" random, irrelevant details or random coincidences (noise) in the past data rather than learning the general rule.",

        "s6_title": "🎛️ Control Knobs — The \"Data\" Settings",
        "s6_intro": "Now that you have set up your prediction machine, you must decide what information the machine processes. These next knobs control the Inputs (Data).",
        "s6_k3": "3. Data Ingredients",
        "s6_k3_desc": "<b>What it is:</b> The specific data points the machine is allowed to access.<br><b>Why it matters:</b> The machine's output depends largely on its input.",
        "s6_behav": "<b>Behavioral Inputs:</b> Data like <i>Juvenile Felony Count</i> may help the logic find valid risk patterns.",
        "s6_demo": "<b>Demographic Inputs:</b> Data like <i>Race</i> may help the model learn, but they may also replicate human bias.",
        "s6_job": "<b>Your Job:</b> Check ☑ or uncheck ☐ the boxes to select the inputs to feed your model.",
        "s6_k4": "4. Data Size (Training Volume)",
        "s6_k4_desc": "<b>What it is:</b> The amount of historical cases the machine uses to learn patterns.",
        "s6_small": "<b>Small (20%):</b> Fast processing. Great for running quick tests to check your settings.",
        "s6_full": "<b>Full (100%):</b> Maximum data processing. It takes longer to build, but gives the machine the best chance to calibrate its accuracy.",

        "s7_title": "🏆 Your Score as an Engineer",
        "s7_p1": "You now know more about how to build a model. But how do we know if it works?",
        "s7_head1": "How You Are Scored",
        "s7_acc": "<strong>Prediction Accuracy:</strong> Your model is tested on <strong>Hidden Data</strong> (cases kept in a \"secret vault\" that your model has never seen). This simulates predicting the future to ensure you get a real-world prediction accuracy score.",
        "s7_lead": "<strong>The Leaderboard:</strong> Live Standings track your progress individually and as a team.",
        "s7_head2": "How You Improve: The Game",
        "s7_comp": "<strong>Compete to Improve:</strong> Refine your model to beat your personal best score.",
        "s7_promo": "<strong>Get Promoted as an Engineer & Unlock Tools:</strong> As you submit more models, you rise in rank and unlock better analysis tools:",
        "s7_ranks": "Trainee → Junior → Senior → Lead Engineer",
        "s7_head3": "Begin Your Mission",
        "s7_final": "You are now ready. Use the experiment loop, get promoted, unlock all the tools, and find the best combination to get the highest score.",
        "s7_rem": "<strong>Remember: You've seen how these predictions affect real life decisions. Build accordingly.</strong>",

        # --- App Interface ---
        "app_title": "🛠️ Model Building Arena",
        "lbl_model": "1. Model Strategy",
        "lbl_complex": "2. Model Complexity (1–10)",
        "info_complex": "Higher values allow deeper pattern learning; very high values may overfit.",
        "lbl_feat": "3. Select Data Ingredients",
        "info_feat": "More ingredients unlock as you rank up!",
        "lbl_data": "4. Data Size",
        "lbl_team_stand": "🏆 Live Standings",
        "lbl_team_sub": "Submit a model to see your rank.",
        "tab_team": "Team Standings",
        "tab_ind": "Individual Standings",
        
        # --- Ranks ---
        "rank_trainee": "# 🧑‍🎓 Rank: Trainee Engineer\n<p style='font-size:24px; line-height:1.4;'>For your first submission, just click the big '🔬 Build & Submit Model' button below!</p>",
        "rank_junior": "# 🎉 Rank Up! Junior Engineer\n<p style='font-size:24px; line-height:1.4;'>New models, data sizes, and data ingredients unlocked!</p>",
        "rank_senior": "# 🌟 Rank Up! Senior Engineer\n<p style='font-size:24px; line-height:1.4;'>Strongest Data Ingredients Unlocked! The most powerful predictors (like 'Age' and 'Prior Crimes Count') are now available in your list. These will likely boost your accuracy, but remember they often carry the most societal bias.</p>",
        "rank_lead": "# 👑 Rank: Lead Engineer\n<p style='font-size:24px; line-height:1.4;'>All tools unlocked — optimize freely!</p>",

        # --- Model Types ---
        "mod_bal": "The Balanced Generalist",
        "mod_rule": "The Rule-Maker",
        "mod_knn": "The 'Nearest Neighbor'",
        "mod_deep": "The Deep Pattern-Finder",
        "desc_bal": "A fast, reliable, well-rounded model. Good starting point; less prone to overfitting.",
        "desc_rule": "Learns simple 'if/then' rules. Easy to interpret, but can miss subtle patterns.",
        "desc_knn": "Looks at the closest past examples. 'You look like these others; I'll predict like they behave.'",
        "desc_deep": "An ensemble of many decision trees. Powerful, can capture deep patterns; watch complexity.",

        # --- KPI Card ---
        "kpi_new_acc": "New Accuracy",
        "kpi_rank": "Your Rank",
        "kpi_no_change": "No Change (↔)",
        "kpi_dropped": "Dropped",
        "kpi_moved_up": "Moved up",
        "kpi_spot": "spot",
        "kpi_spots": "spots",
        "kpi_on_board": "You're on the board!",
        "kpi_preview": "Preview only - not submitted",
        "kpi_success": "✅ Submission Successful",
        "kpi_first": "🎉 First Model Submitted!",
        "kpi_lower": "📉 Score Dropped",
        "summary_empty": "No team submissions yet.",

        # --- Leaderboard Table Headers (New) ---
        "lbl_rank": "Rank",
        "lbl_team": "Team",
        "lbl_best_acc": "Best Accuracy",
        
        # --- Final Conclusion Screen ---
        "concl_title": "✅ Section Complete",
        "concl_prep": "<p>Preparing final summary...</p>",
        "tier_trainee": "Trainee", 
        "tier_junior": "Junior", 
        "tier_senior": "Senior", 
        "tier_lead": "Lead",
        "none_yet": "None yet",
        "tip_label": "Tip:",
        "concl_tip_body": "Try at least 2–3 submissions changing ONE setting at a time to see clear cause/effect.",
        "limit_title": "Attempt Limit Reached",
        "limit_body": "You used all {limit} allowed submission attempts for this session. We will open up submissions again after you complete some new activities next.",
        "concl_snapshot": "Your Performance Snapshot",
        "concl_rank_achieved": "Rank Achieved",
        "concl_subs_made": "Submissions Made This Session",
        "concl_improvement": "Improvement Over First Score",
        "concl_tier_prog": "Tier Progress",
        "concl_strong_pred": "Strong Predictors Used",
        "concl_eth_ref": "Ethical Reflection",
        "concl_eth_body": "You unlocked powerful predictors. Consider: Would removing demographic fields change fairness? In the next section we will begin to investigate this question further.",
        "concl_next_title": "Next: Real-World Consequences",
        "concl_next_body": "Scroll below this app to continue. You'll examine how models like yours shape judicial outcomes.",
        "s6_scroll": "👇 SCROLL DOWN 👇"
    },
    "es": {
        "title": "🛠️ Arena de Construcción de Modelos",
        "loading": "⏳ Cargando...",
        "btn_next": "Siguiente ▶️",
        "btn_back": "◀️ Atrás",
        "btn_return": "◀️ Volver",
        "btn_finish": "Terminar y Reflexionar ▶️",
        "btn_begin": "Comenzar ▶️",
        "btn_submit": "5. 🔬 Construir y Enviar Modelo",

        # Login
        "login_title": "🔐 Iniciar sesión para clasificar",
        "login_desc": "Esta es solo una vista previa. Inicia sesión para publicar tu puntuación.",
        "login_new": "¿Nuevo usuario? Crea una cuenta gratis en",

        # Welcome
        "welcome_header": "¡Bienvenido a <b>{team}</b>!",
        "welcome_body": "Tu equipo espera tu ayuda para mejorar la IA.",
        "welcome_cta": "👈 ¡Haz clic en 'Construir y Enviar' para Jugar!",
        "lb_submit_to_rank": "¡Envía tu modelo para ver tu clasificación!",

        # Slides
        "s1_title": "🔄 De Entender a Construir",
        "s1_intro": "¡Gran progreso! Ahora has:",
        "s1_li1": "Tomado decisiones difíciles como juez usando predicciones de IA",
        "s1_li2": "Aprendido sobre falsos positivos y falsos negativos",
        "s1_li3": "Entendido cómo funciona la IA:",
        "s1_in": "ENTRADA",
        "s1_mod": "MODELO",
        "s1_out": "SALIDA",
        "s1_chal_title": "Ahora es el momento de ponerse en los zapatos de un Ingeniero de IA.",
        "s1_chal_body": "<strong>Tu Nuevo Desafío:</strong> Construir modelos de IA que sean más precisos que el que usaste como juez.",
        "s1_rem": "Recuerda: Experimentaste de primera mano cómo las predicciones de IA afectan la vida de personas reales. Usa ese conocimiento para construir algo mejor.",
        "s2_title": "📋 Tu Misión - Construir Mejor IA",
        "s2_miss_head": "La Misión",
        "s2_miss_body": "Construye un modelo de IA que ayude a los jueces a tomar mejores decisiones. El modelo que usaste anteriormente te dio consejos imperfectos. Tu trabajo ahora es construir un nuevo modelo que prediga el riesgo con mayor precisión, proporcionando a los jueces las ideas confiables que necesitan para ser justos.",
        "s2_comp_head": "La Competencia",
        "s2_comp_body": "¡Para hacer esto, competirás contra otros ingenieros! Para ayudarte en tu misión, te unirás a un equipo de ingeniería. Tus resultados serán rastreados tanto individualmente como en grupo en las Tablas de Clasificación en Vivo.",
        "s2_join": "Te unirás a un equipo como...",
        "s2_data_head": "El Desafío de Datos",
        "s2_data_intro": "Para competir, tienes acceso a miles de archivos de casos antiguos. Tienes dos tipos distintos de información:",
        "s2_li1": "<strong>Perfiles de Acusados:</strong> Esto es como lo que vio el juez en el momento del arresto.",
        "s2_li1_sub": "<em>Edad, Número de Delitos Previos, Tipo de Cargo.</em>",
        "s2_li2": "<strong>Resultados Históricos:</strong> Esto es lo que realmente les sucedió a esas personas después.",
        "s2_li2_sub": "<em>¿Reincidieron dentro de 2 años? (Sí/No)</em>",
        "s2_core_head": "La Tarea Principal",
        "s2_core_body": "Necesitas enseñar a tu IA a mirar los \"Perfiles\" y predecir con precisión el \"Resultado.\"",
        "s2_ready": "<strong>¿Listo para construir algo que podría cambiar cómo funciona la justicia?</strong>",
        "s3_title": "🧠 ¿Qué es un \"Modelo\"?",
        "s3_p1": "Antes de comenzar a competir, desglosemos exactamente lo que estás construyendo.",
        "s3_head1": "Piensa en un Modelo como una \"Máquina de Predicción\".",
        "s3_p2": "Ya conoces el flujo:",
        "s3_eng_note": "Como ingeniero, no necesitas escribir código complejo desde cero. En cambio, ensamblas esta máquina usando tres componentes principales.",
        "s3_comp_head": "Los 3 Componentes:",
        "s3_c1": "<strong>1. Las Entradas (Datos)</strong><br>La información que alimentas a la máquina.<br><em>* Ejemplos: Edad, Crímenes Previos, Detalles del Cargo.</em>",
        "s3_c2": "<strong>2. El Modelo (Máquina de Predicción)</strong><br>El \"cerebro\" matemático que busca patrones en las entradas.<br><em>* Ejemplos: Elegirás diferentes \"cerebros\" que aprenden de diferentes maneras (por ejemplo, reglas simples vs. patrones profundos).</em>",
        "s3_c3": "<strong>3. La Salida (Predicción)</strong><br>La mejor suposición del modelo.<br><em>* Ejemplo: Nivel de Riesgo: Alto o Bajo.</em>",
        "s3_learn": "<strong>Cómo aprende:</strong> Muestras al modelo miles de casos antiguos (Entradas) + lo que realmente sucedió (Resultados). Los estudia para encontrar las reglas, para que pueda hacer predicciones sobre nuevos casos que no ha visto antes.",
        "s4_title": "🔁 Cómo Trabajan los Ingenieros — El Bucle",
        "s4_p1": "Ahora que conoces los componentes de un modelo, ¿cómo construyes uno mejor?",
        "s4_sec_head": "Aquí está el secreto:",
        "s4_sec_body": "Los equipos de IA reales casi nunca lo hacen bien en el primer intento. En cambio, siguen un bucle continuo de experimentación: <strong>Probar, Testear, Aprender, Repetir.</strong>",
        "s4_loop_head": "El Bucle de Experimentación:",
        "s4_l1": "<strong>Construir un Modelo:</strong> Ensambla tus componentes y obtén una puntuación de precisión de predicción inicial.",
        "s4_l2": "<strong>Hacer una Pregunta:</strong> (por ejemplo, \"¿Qué pasa si cambio el tipo de 'Cerebro'?\")",
        "s4_l3": "<strong>Probar y Comparar:</strong> ¿Mejoró la puntuación... o empeoró?",
        "s4_same": "¡Harás exactamente lo mismo en una competencia!",
        "s4_v1": "<b>1. Configurar</b><br/>Usa Perillas de Control para seleccionar Estrategia y Datos.",
        "s4_v2": "<b>2. Enviar</b><br/>Haz clic en \"Construir y Enviar\" para entrenar tu modelo.",
        "s4_v3": "<b>3. Analizar</b><br/>Revisa tu rango en la Tabla de Clasificación en Vivo.",
        "s4_v4": "<b>4. Refinar</b><br/>¡Cambia una configuración y envía de nuevo!",
        "s4_tip": "<strong>Consejo Pro:</strong> Intenta cambiar solo una cosa a la vez. Si cambias demasiadas cosas a la vez, ¡no sabrás qué hizo que tu modelo fuera mejor o peor!",
        "s5_title": "🎛️ Configuración del \"Cerebro\"",
        "s5_intro": "Para construir tu modelo, usarás Perillas de Control para configurar tu Máquina de Predicción. Las primeras dos perillas te permiten elegir un tipo de modelo y ajustar cómo aprende patrones en los datos.",
        "s5_k1": "1. Estrategia del Modelo (Tipo de Modelo)",
        "s5_k1_desc": "<b>Qué es:</b> El método matemático específico que la máquina usa para encontrar patrones.",
        "s5_m1": "<b>El Generalista Equilibrado:</b> Un algoritmo confiable y multipropósito. Proporciona resultados estables en la mayoría de los datos.",
        "s5_m2": "<b>El Creador de Reglas:</b> Crea lógica estricta \"Si... Llavors...\" (por ejemplo, Si crímenes previos > 2, entonces Alto Riesgo).",
        "s5_m3": "<b>El Buscador de Patrones Profundos:</b> Un algoritmo complejo diseñado para detectar conexiones sutiles y ocultas en los datos.",
        "s5_k2": "2. Complejidad del Modelo (Nivel de Ajuste)",
        "s5_range": "Rango: Nivel 1 ─── ● ─── 10",
        "s5_k2_desc1": "<b>Qué es:</b> Ajusta qué tan ajustadamente la máquina ajusta su lógica para encontrar patrones en los datos.",
        "s5_k2_desc2": "<b>El Intercambio:</b>",
        "s5_low": "<b>Bajo (Nivel 1):</b> Captura solo las tendencias amplias y obvias.",
        "s5_high": "<b>Alto (Nivel 5):</b> Captura cada pequeño detalle y variación.",
        "s5_warn": "Advertencia: Configurar esto demasiado alto hace que la máquina \"memorice\" detalles aleatorios e irrelevantes o coincidencias aleatorias (ruido) en los datos pasados en lugar de aprender la regla general.",
        "s6_title": "🎛️ Configuración de \"Datos\"",
        "s6_intro": "Ahora que has configurado tu máquina de predicción, debes decidir qué información procesa la máquina. Estas siguientes perillas controlan las Entradas (Datos).",
        "s6_k3": "3. Ingredientes de Datos",
        "s6_k3_desc": "<b>Qué es:</b> Los puntos de datos específicos a los que la máquina tiene permitido acceder.<br><b>Por qué importa:</b> La salida de la máquina depende en gran medida de su entrada.",
        "s6_behav": "<b>Entradas de Comportamiento:</b> Datos como <i>Conteo de Delitos Juveniles</i> pueden ayudar a la lógica a encontrar patrones de riesgo válidos.",
        "s6_demo": "<b>Entradas Demográficas:</b> Datos como <i>Raza</i> pueden ayudar al modelo a aprender, pero también pueden replicar el sesgo humano.",
        "s6_job": "<b>Tu Trabajo:</b> Marca ☑ o desmarca ☐ las casillas para seleccionar las entradas para alimentar tu modelo.",
        "s6_k4": "4. Tamaño de Datos (Volumen de Entrenamiento)",
        "s6_k4_desc": "<b>Qué es:</b> La cantidad de casos históricos que la máquina usa para aprender patrones.",
        "s6_small": "<b>Pequeño (20%):</b> Procesamiento rápido. Genial para ejecutar pruebas rápidas para verificar tu configuración.",
        "s6_full": "<b>Completo (100%):</b> Procesamiento máximo de datos. Tarda más en construirse, pero le da a la máquina la mejor oportunidad de calibrar su precisión.",
        "s7_title": "🏆 Tu Puntuación",
        "s7_p1": "Ahora sabes más sobre cómo construir un modelo. Pero, ¿cómo sabemos si funciona?",
        "s7_head1": "Cómo eres Puntuado",
        "s7_acc": "<strong>Precisión de Predicción:</strong> Tu modelo se prueba en <strong>Datos Ocultos</strong> (casos guardados en una \"bóveda secreta\" que tu modelo nunca ha visto). Esto simula predecir el futuro para asegurar que obtengas una puntuación de precisión de predicción del mundo real.",
        "s7_lead": "<strong>La Tabla de Clasificación:</strong> Las Clasificaciones en Vivo rastrean tu progreso individualmente y como equipo.",
        "s7_head2": "Cómo Mejoras: El Juego",
        "s7_comp": "<strong>Compite para Mejorar:</strong> Refina tu modelo para superar tu mejor puntuación personal.",
        "s7_promo": "<strong>Sé Promovido como Ingeniero y Desbloquea Herramientas:</strong> A medida que envías más modelos, subes de rango y desbloqueas mejores herramientas de análisis:",
        "s7_ranks": "Aprendiz → Junior → Senior → Ingeniero Principal",
        "s7_head3": "Comienza Tu Misión",
        "s7_final": "Ahora estás listo. Usa el bucle de experimentación, sé promovido, desbloquea todas las herramientas y encuentra la mejor combinación para obtener la puntuación más alta.",
        "s7_rem": "<strong>Recuerda: Has visto cómo estas predicciones afectan las decisiones de la vida real. Construye en consecuencia.</strong>",
        "btn_begin": "Comenzar ▶️",
        
        "lbl_model": "1. Estrategia del Modelo",
        "lbl_complex": "2. Complejidad del Modelo",
        "info_complex": "Valores altos permiten aprendizaje profundo; cuidado con el sobreajuste.",
        "lbl_feat": "3. Ingredientes de Datos",
        "info_feat": "¡Más ingredientes se desbloquean al subir de rango!",
        "lbl_data": "4. Tamaño de Datos",
        "lbl_team_stand": "🏆 Clasificaciones en Vivo",
        "lbl_team_sub": "Envía un modelo para ver tu rango.",
        "tab_team": "Clasificaciones de Equipo",
        "tab_ind": "Clasificaciones Individuales",
        "concl_title": "✅ Sección Completada",
        "concl_prep": "<p>Preparando resumen final...</p>",

        "rank_trainee": "# 🧑‍🎓 Rango: Ingeniero Aprendiz\n<p style='font-size:24px; line-height:1.4;'>¡Haz clic en 'Construir y Enviar' para comenzar!</p>",
        "rank_junior": "# 🎉 ¡Subida de Rango! Ingeniero Junior\n<p style='font-size:24px; line-height:1.4;'>¡Nuevos modelos y datos desbloqueados!</p>",
        "rank_senior": "# 🌟 ¡Subida de Rango! Ingeniero Senior\n<p style='font-size:24px; line-height:1.4;'>¡Ingredientes de Datos Más Fuertes Desbloqueados!</p>",
        "rank_lead": "# 👑 Rango: Ingeniero Principal\n<p style='font-size:24px; line-height:1.4;'>¡Todas las herramientas desbloqueadas!</p>",

        "mod_bal": "El Generalista Equilibrado",
        "mod_rule": "El Creador de Reglas",
        "mod_knn": "El 'Vecino Más Cercano'",
        "mod_deep": "El Buscador de Patrones Profundos",
        "desc_bal": "Un modelo rápido, confiable y completo. Buen punto de partida; menos propenso al sobreajuste.",
        "desc_rule": "Aprende reglas simples 'si/entonces'. Fácil de interpretar, pero puede perder patrones sutiles.",
        "desc_knn": "Mira los ejemplos pasados más cercanos. 'Te pareces a estos otros; predeciré como ellos se comportan.'",
        "desc_deep": "Un conjunto de muchos árboles de decisión. Poderoso, puede capturar patrones profundos; cuidado con la complejidad.",

        "kpi_new_acc": "Nueva Precisión",
        "kpi_rank": "Tu Rango",
        "kpi_no_change": "Sin Cambio (↔)",
        "kpi_dropped": "Bajó",
        "kpi_moved_up": "Subió",
        "kpi_spot": "puesto",
        "kpi_spots": "puestos",
        "kpi_on_board": "¡Estás en el tablero!",
        "kpi_preview": "Vista previa - no enviado",
        "kpi_success": "✅ Envío Exitoso",
        "kpi_first": "🎉 Primer Modelo Enviado!",
        "kpi_lower": "📉 Puntuación Bajó",
        "summary_empty": "Aún no hay envíos de equipo.",

        # --- Leaderboard ---
        "lbl_rank": "Rango",
        "lbl_team": "Equipo",
        "lbl_best_acc": "Mejor Precisión",

        # --- Conclusion ---
        "tier_trainee": "Aprendiz", "tier_junior": "Junior", "tier_senior": "Senior", "tier_lead": "Líder",
        "none_yet": "Ninguno aún",
        "tip_label": "Consejo:",
        "concl_tip_body": "Intenta al menos 2–3 envíos cambiando UNA configuración a la vez para ver causa/efecto claro.",
        "limit_title": "Límite de Intentos Alcanzado",
        "limit_body": "Has usado los {limit} intentos permitidos. Abriremos los envíos nuevamente después de que completes nuevas actividades.",
        "concl_snapshot": "Tu Resumen de Rendimiento",
        "concl_rank_achieved": "Rango Logrado",
        "concl_subs_made": "Envíos Hechos Esta Sesión",
        "concl_improvement": "Mejora Sobre la Primera Puntuación",
        "concl_tier_prog": "Progreso de Nivel",
        "concl_strong_pred": "Predictores Fuertes Usados",
        "concl_eth_ref": "Reflexión Ética",
        "concl_eth_body": "Desbloqueaste predictores poderosos. Considera: ¿Eliminar campos demográficos cambiaría la equidad? Investigaremos esto más a fondo a continuación.",
        "concl_next_title": "Siguiente: Consecuencias en el Mundo Real",
        "concl_next_body": "Desplázate hacia abajo. Examinarás cómo modelos como el tuyo dan forma a los resultados judiciales.",
        "s6_scroll": "👇 DESPLÁZATE HACIA ABAJO 👇",

        # --- Team Names ---
        "The Moral Champions": "Los Campeones Morales",
        "The Justice League": "La Liga de la Justicia",
        "The Data Detectives": "Los Detectives de Datos",
        "The Ethical Explorers": "Los Exploradores Éticos",
        "The Fairness Finders": "Los Buscadores de Equidad",
        "The Accuracy Avengers": "Los Vengadores de la Precisión"
    },
    "ca": {
        "title": "🛠️ Arena de Construcció de Models",
        "loading": "⏳ Carregant...",
        "btn_next": "Següent ▶️",
        "btn_back": "◀️ Enrere",
        "btn_return": "◀️ Tornar",
        "btn_finish": "Acabar i Reflexionar ▶️",
        "btn_begin": "Començar ▶️",
        "btn_submit": "5. 🔬 Construir i Enviar Model",

        # Login
        "login_title": "🔐 Inicia sessió per classificar",
        "login_desc": "Això és només una vista prèvia. Inicia sessió per publicar la teva puntuació.",
        "login_new": "Nou usuari? Crea un compte gratuït a",

        # Welcome
        "welcome_header": "Benvingut a <b>{team}</b>!",
        "welcome_body": "El teu equip espera la teva ajuda per millorar la IA.",
        "welcome_cta": "👈 Fes clic a 'Construir i Enviar' per Jugar!",
        "lb_submit_to_rank": "Envia el teu model per veure la teva classificació!",

        # Slides
        "s1_title": "🔄 D'Entendre a Construir",
        "s1_intro": "Gran progrés! Ara has:",
        "s1_li1": "Pres decisions difícils com a jutge utilitzant prediccions d'IA",
        "s1_li2": "Après sobre falsos positius i falsos negatius",
        "s1_li3": "Entès com funciona la IA:",
        "s1_in": "ENTRADA",
        "s1_mod": "MODEL",
        "s1_out": "SORTIDA",
        "s1_chal_title": "Ara és el moment de posar-se a la pell d'un Enginyer d'IA.",
        "s1_chal_body": "<strong>El Teu Nou Repte:</strong> Construir models d'IA que siguin més precisos que el que vas utilitzar com a jutge.",
        "s1_rem": "Recorda: Vas experimentar de primera mà com les prediccions d'IA afecten la vida de persones reals. Utilitza aquest coneixement per construir alguna cosa millor.",
        "s2_title": "📋 La Teva Missió - Construir Millor IA",
        "s2_miss_head": "La Missió",
        "s2_miss_body": "Construeix un model d'IA que ajudi els jutges a prendre millors decisions. El model que vas utilitzar anteriorment et va donar consells imperfectes. La teva feina ara és construir un nou model que predigui el risc amb més precisió, proporcionant als jutges les idees fiables que necessiten per ser justos.",
        "s2_comp_head": "La Competició",
        "s2_comp_body": "Per fer això, competiràs contra altres enginyers! Per ajudar-te en la teva missió, t'uniràs a un equip d'enginyeria. Els teus resultats seran rastrejats tant individualment com en grup a les Taules de Classificació en Viu.",
        "s2_join": "T'uniràs a un equip com...",
        "s2_data_head": "El Repte de Dades",
        "s2_data_intro": "Per competir, tens accés a milers d'arxius de casos antics. Tens dos tipus diferents d'informació:",
        "s2_li1": "<strong>Perfils d'Acusats:</strong> Això és com el que va veure el jutge en el moment de l'arrest.",
        "s2_li1_sub": "<em>Edat, Nombre de Delictes Previs, Tipus de Càrrec.</em>",
        "s2_li2": "<strong>Resultats Històrics:</strong> Això és el que realment els va passar a aquestes persones després.",
        "s2_li2_sub": "<em>Van reincidir en 2 anys? (Sí/No)</em>",
        "s2_core_head": "La Tasca Principal",
        "s2_core_body": "Necessites ensenyar a la teva IA a mirar els \"Perfils\" i predir amb precisió el \"Resultat.\"",
        "s2_ready": "<strong>A punt per construir alguna cosa que podria canviar com funciona la justícia?</strong>",
        "s3_title": "🧠 Què és un \"Model\"?",
        "s3_p1": "Abans de començar a competir, desglossem exactament el que estàs construint.",
        "s3_head1": "Pensa en un Model com una \"Màquina de Predicció\".",
        "s3_p2": "Ja coneixes el flux:",
        "s3_eng_note": "Com a enginyer, no necessites escriure codi complex des de zero. En canvi, muntes aquesta màquina utilitzant tres components principals.",
        "s3_comp_head": "Els 3 Components:",
        "s3_c1": "<strong>1. Les Entrades (Dades)</strong><br>La informació que alimentes a la màquina.<br><em>* Exemples: Edat, Crims Previs, Detalls del Càrrec.</em>",
        "s3_c2": "<strong>2. El Model (Màquina de Predicció)</strong><br>El \"cervell\" matemàtic que busca patrons en les entrades.<br><em>* Exemples: Triaràs diferents \"cervells\" que aprenen de diferents maneres (per exemple, regles simples vs. patrons profunds).</em>",
        "s3_c3": "<strong>3. La Sortida (Predicció)</strong><br>La millor suposició del model.<br><em>* Exemple: Nivell de Risc: Alt o Baix.</em>",
        "s3_learn": "<strong>Com aprèn:</strong> Mostres al model milers de casos antics (Entrades) + el que realment va passar (Resultats). Els estudia per trobar les regles, per tal que pugui fer prediccions sobre nous casos que no ha vist abans.",
        "s4_title": "🔁 Com Treballen els Enginyers — El Bucle",
        "s4_p1": "Ara que coneixes els components d'un model, com en construeixes un de millor?",
        "s4_sec_head": "Aquí està el secret:",
        "s4_sec_body": "Els equips d'IA reals gairebé mai ho fan bé al primer intent. En canvi, segueixen un bucle continu d'experimentació: <strong>Provar, Testejar, Aprendre, Repetir.</strong>",
        "s4_loop_head": "El Bucle d'Experimentació:",
        "s4_l1": "<strong>Construir un Model:</strong> Munta els teus components i obtén una puntuació de precisió de predicció inicial.",
        "s4_l2": "<strong>Fer una Pregunta:</strong> (per exemple, \"Què passa si canvio el tipus de 'Cervell'?\")",
        "s4_l3": "<strong>Provar i Comparar:</strong> Ha millorat la puntuació... o ha empitjorat?",
        "s4_same": "Faràs exactament el mateix en una competició!",
        "s4_v1": "<b>1. Configurar</b><br/>Utilitza Perilles de Control per seleccionar Estratègia i Dades.",
        "s4_v2": "<b>2. Enviar</b><br/>Fes clic a \"Construir i Enviar\" per entrenar el teu model.",
        "s4_v3": "<b>3. Analitzar</b><br/>Revisa el teu rang a la Taula de Classificació en Viu.",
        "s4_v4": "<b>4. Refinar</b><br/>Canvia una configuració i envia de nou!",
        "s4_tip": "<strong>Consell Pro:</strong> Intenta canviar només una cosa a la vegada. Si canvies massa coses a la vegada, no sabràs què va fer que el teu model fos millor o pitjor!",
        "s5_title": "🎛️ Configuració del \"Cervell\"",
        "s5_intro": "Per construir el teu model, utilitzaràs Perilles de Control per configurar la teva Màquina de Predicció. Les primeres dues perilles et permeten triar un tipus de model i ajustar com aprèn patrons en les dades.",
        "s5_k1": "1. Estratègia del Model (Tipus de Model)",
        "s5_k1_desc": "<b>Què és:</b> El mètode matemàtic específic que la màquina utilitza per trobar patrons.",
        "s5_m1": "<b>El Generalista Equilibrat:</b> Un algorisme fiable i multipropòsit. Proporciona resultats estables en la majoria de les dades.",
        "s5_m2": "<b>El Creador de Regles:</b> Crea lògica estricta \"Si... Llavors...\" (per exemple, Si crims previs > 2, llavors Alt Risc).",
        "s5_m3": "<b>El Cercador de Patrons Profunds:</b> Un algorisme complex dissenyat per detectar connexions subtils i ocultes en les dades.",
        "s5_k2": "2. Complexitat del Model (Nivell d'Ajust)",
        "s5_range": "Rang: Nivell 1 ─── ● ─── 10",
        "s5_k2_desc1": "<b>Què és:</b> Ajusta com d'ajustadament la màquina ajusta la seva lògica per trobar patrons en les dades.",
        "s5_k2_desc2": "<b>L'Intercanvi:</b>",
        "s5_low": "<b>Baix (Nivell 1):</b> Captura només les tendències àmplies i òbvies.",
        "s5_high": "<b>Alt (Nivell 5):</b> Captura cada petit detall i variació.",
        "s5_warn": "Advertència: Configurar això massa alt fa que la màquina \"memoritzi\" detalls aleatoris i irrellevants o coincidències aleatòries (soroll) en les dades passades en lloc d'aprendre la regla general.",
        "s6_title": "🎛️ Configuració de \"Dades\"",
        "s6_intro": "Ara que has configurat la teva màquina de predicció, has de decidir quina informació processa la màquina. Aquestes següents perilles controlen les Entrades (Dades).",
        "s6_k3": "3. Ingredients de Dades",
        "s6_k3_desc": "<b>Què és:</b> Els punts de dades específics als quals la màquina té permès accedir.<br><b>Per què importa:</b> La sortida de la màquina depèn en gran mesura de la seva entrada.",
        "s6_behav": "<b>Entrades de Comportament:</b> Dades com <i>Recompte de Delictes Juvenils</i> poden ajudar a la lògica a trobar patrons de risc vàlids.",
        "s6_demo": "<b>Entrades Demogràfiques:</b> Dades com <i>Raça</i> poden ajudar al model a aprendre, però també poden replicar el biaix humà.",
        "s6_job": "<b>La Teva Feina:</b> Marca ☑ o desmarca ☐ les caselles per seleccionar les entrades per alimentar el teu model.",
        "s6_k4": "4. Mida de Dades (Volum d'Entrenament)",
        "s6_k4_desc": "<b>Què és:</b> La quantitat de casos històrics que la màquina utilitza per aprendre patrons.",
        "s6_small": "<b>Petit (20%):</b> Processament ràpid. Genial per executar proves ràpides per verificar la teva configuració.",
        "s6_full": "<b>Complet (100%):</b> Processament màxim de dades. Triga més a construir-se, però li dóna a la màquina la millor oportunitat de calibrar la seva precisió.",
        "s7_title": "🏆 La Teva Puntuació",
        "s7_p1": "Ara saps més sobre com construir un model. Però, com sabem si funciona?",
        "s7_head1": "Com ets Puntuat",
        "s7_acc": "<strong>Precisió de Predicció:</strong> El teu model es prova en <strong>Dades Ocultes</strong> (casos guardats en una \"cambra secreta\" que el teu model mai ha vist). Això simula predir el futur per assegurar que obtinguis una puntuació de precisió de predicció del món real.",
        "s7_lead": "<strong>La Taula de Classificació:</strong> Les Classificacions en Viu rastregen el teu progrés individualment i com a equip.",
        "s7_head2": "Com Millores: El Joc",
        "s7_comp": "<strong>Competeix per Millorar:</strong> Refina el teu model per superar la teva millor puntuació personal.",
        "s7_promo": "<strong>Sigues Promogut com a Enginyer i Desbloqueja Eines:</strong> A mesura que envies més models, puges de rang i desbloqueges millors eines d'anàlisi:",
        "s7_ranks": "Aprenent → Junior → Senior → Enginyer Principal",
        "s7_head3": "Comença La Teva Missió",
        "s7_final": "Ara estàs llest. Utilitza el bucle d'experimentació, sigues promogut, desbloqueja totes les eines i troba la millor combinació per obtenir la puntuació més alta.",
        "s7_rem": "<strong>Recorda: Has vist com aquestes prediccions afecten les decisions de la vida real. Construeix en conseqüència.</strong>",
        "btn_begin": "Començar ▶️",
        
        "lbl_model": "1. Estratègia del Model",
        "lbl_complex": "2. Complexitat del Model",
        "info_complex": "Valors alts permeten aprenentatge profund; cura amb el sobreajust.",
        "lbl_feat": "3. Ingredients de Dades",
        "info_feat": "Més ingredients es desbloquegen al pujar de rang!",
        "lbl_data": "4. Mida de Dades",
        "lbl_team_stand": "🏆 Classificacions en Viu",
        "lbl_team_sub": "Envia un model per veure el teu rang.",
        "tab_team": "Classificacions d'Equip",
        "tab_ind": "Classificacions Individuals",
        "concl_title": "✅ Secció Completada",
        "concl_prep": "<p>Preparant resum final...</p>",
        "rank_trainee": "# 🧑‍🎓 Rang: Enginyer Aprenent\n<p style='font-size:24px; line-height:1.4;'>Fes clic a 'Construir i Enviar' per començar!</p>",
        "rank_junior": "# 🎉 Pujada de Rang! Enginyer Junior\n<p style='font-size:24px; line-height:1.4;'>Nous models i dades desbloquejats!</p>",
        "rank_senior": "# 🌟 Pujada de Rang! Enginyer Senior\n<p style='font-size:24px; line-height:1.4;'>Ingredients de Dades Més Forts Desbloquejats!</p>",
        "rank_lead": "# 👑 Rang: Enginyer Principal\n<p style='font-size:24px; line-height:1.4;'>Totes les eines desbloquejades!</p>",
        "mod_bal": "El Generalista Equilibrat",
        "mod_rule": "El Creador de Reglas",
        "mod_knn": "El 'Veí Més Proper'",
        "mod_deep": "El Cercador de Patrons Profunds",
        "desc_bal": "Un model ràpid, fiable i complet. Bon punt de partida; menys propens al sobreajust.",
        "desc_rule": "Aprèn regles simples 'si/llavors'. Fàcil d'interpretar, però pot perdre patrons subtils.",
        "desc_knn": "Mira els exemples passats més propers. 'T'assembles a aquests altres; prediré com ells es comporten.'",
        "desc_deep": "Un conjunt de molts arbres de decisió. Potent, pot capturar patrons profunds; cura amb la complexitat.",
        "kpi_new_acc": "Nova Precisió",
        "kpi_rank": "El Teu Rang",
        "kpi_no_change": "Sense Canvi (↔)",
        "kpi_dropped": "Va baixar",
        "kpi_moved_up": "Va pujar",
        "kpi_spot": "lloc",
        "kpi_spots": "llocs",
        "kpi_on_board": "Estàs al tauler!",
        "kpi_preview": "Vista prèvia - no enviat",
        "kpi_success": "✅ Enviament Exitós",
        "kpi_first": "🎉 Primer Model Enviat!",
        "kpi_lower": "📉 Puntuació Va Baixar",
        "summary_empty": "Encara no hi ha enviaments d'equip.",

        # --- Leaderboard ---
        "lbl_rank": "Rang",
        "lbl_team": "Equip",
        "lbl_best_acc": "Millor Precisió",

        # --- Conclusion ---
        "tier_trainee": "Aprenent", "tier_junior": "Junior", "tier_senior": "Senior", "tier_lead": "Líder",
        "none_yet": "Cap encara",
        "tip_label": "Consell:",
        "concl_tip_body": "Intenta almenys 2–3 enviaments canviant UNA configuració a la vegada per veure causa/efecte clar.",
        "limit_title": "Límit d'Intents Assolit",
        "limit_body": "Has utilitzat tots els {limit} intents permesos. Obrirem els enviaments de nou després que completis noves activitats.",
        "concl_snapshot": "El Teu Resum de Rendiment",
        "concl_rank_achieved": "Rang Assolit",
        "concl_subs_made": "Enviaments Fets Aquesta Sessió",
        "concl_improvement": "Millora Sobre la Primera Puntuació",
        "concl_tier_prog": "Progrés de Nivell",
        "concl_strong_pred": "Predictors Forts Utilitzats",
        "concl_eth_ref": "Reflexió Ètica",
        "concl_eth_body": "Has desbloquejat predictors potents. Considera: Eliminar camps demogràfics canviaria l'equitat? Investigarem això més a fons a continuació.",
        "concl_next_title": "Següent: Conseqüències al Món Real",
        "concl_next_body": "Desplaça't cap avall. Examinaràs com models com el teu donen forma als resultats judicials.",
        "s6_scroll": "👇 DESPLAÇA'T CAP AVALL 👇",

        # --- Team Names ---
        "The Moral Champions": "Els Campions Morals",
        "The Justice League": "La Lliga de la Justícia",
        "The Data Detectives": "Els Detectius de Dades",
        "The Ethical Explorers": "Els Exploradors Ètics",
        "The Fairness Finders": "Els Cercadors d'Equitat",
        "The Accuracy Avengers": "Els Venjadors de la Precisió"
    }
}
# -------------------------------------------------------------------------
# Configuration & Caching Infrastructure
# -------------------------------------------------------------------------

LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

# In-memory caches (per container instance)
# Each cache has its own lock for thread safety under concurrent requests
_cache_lock = threading.Lock()  # Protects _leaderboard_cache
_user_stats_lock = threading.Lock()  # Protects _user_stats_cache
_auth_lock = threading.Lock()  # Protects get_aws_token() credential injection

# Auth-aware leaderboard cache: separate entries for authenticated vs anonymous
# Structure: {"anon": {"data": df, "timestamp": float}, "auth": {"data": df, "timestamp": float}}
_leaderboard_cache: Dict[str, Dict[str, Any]] = {
    "anon": {"data": None, "timestamp": 0.0},
    "auth": {"data": None, "timestamp": 0.0},
}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

# -------------------------------------------------------------------------
# Retry Helper for External API Calls
# -------------------------------------------------------------------------
def t(lang, key):
    """Helper to get translation with fallback to English."""
    # TRANSLATIONS must be defined globally before this is called
    if lang not in TRANSLATIONS:
        lang = "en"
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

def t_team(team_name_english, lang):
    """
    Translates an English team name into the target language.
    If no translation is found, returns the original English name.
    """
    if not team_name_english:
        return ""
    
    # Normal lookup
    if lang in TRANSLATIONS and team_name_english in TRANSLATIONS[lang]:
        return TRANSLATIONS[lang][team_name_english]
    
    # Fallback
    return team_name_english
  
T = TypeVar("T")

def on_initial_load(username, token=None, team_name="", lang="en"):
    """
    Updated to handle I18n for the Welcome screen, Team Name translation, and Rank settings.
    """
    # 1. Compute initial UI settings (Model choices, sliders) based on rank 0 (Trainee)
    # Pass lang so the "Trainee" rank message is translated
    initial_ui = compute_rank_settings(
        0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE, lang=lang
    )

    # 2. Translate the Team Name for display
    # The backend uses English names ("The Moral Champions"), but we want to show 
    # "Los Campeones Morales" if lang is 'es'.
    display_team = team_name
    if team_name and lang in TRANSLATIONS and team_name in TRANSLATIONS[lang]:
        display_team = TRANSLATIONS[lang][team_name]
    elif not display_team:
        display_team = t(lang, "lbl_team") # Fallback to generic "Team" label

    # 3. Prepare the Welcome HTML (Localized)
    welcome_html = f"""
    <div style='text-align:center; padding: 30px 20px;'>
        <div style='font-size: 3rem; margin-bottom: 10px;'>👋</div>
        <h3 style='margin: 0 0 8px 0; color: #111827; font-size: 1.5rem;'>{t(lang, 'welcome_header').format(team=display_team)}</h3>
        <p style='font-size: 1.1rem; color: #4b5563; margin: 0 0 20px 0;'>
            {t(lang, 'welcome_body')}
        </p>
        
        <div style='background:#eff6ff; padding:16px; border-radius:12px; border:2px solid #bfdbfe; display:inline-block;'>
            <p style='margin:0; color:#1e40af; font-weight:bold; font-size:1.1rem;'>
                {t(lang, 'welcome_cta')}
            </p>
        </div>
    </div>
    """

    # 4. Check background data readiness
    with INIT_LOCK:
        background_ready = INIT_FLAGS["leaderboard"]
    
    should_attempt_fetch = background_ready or (token is not None)
    full_leaderboard_df = None
    
    if should_attempt_fetch:
        try:
            if playground:
                full_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
        except Exception as e:
            print(f"Error on initial load fetch: {e}")
            full_leaderboard_df = None

    # 5. Check if THIS user has submitted anything
    user_has_submitted = False
    if full_leaderboard_df is not None and not full_leaderboard_df.empty:
        if "username" in full_leaderboard_df.columns and username:
            user_has_submitted = username in full_leaderboard_df["username"].values

    # 6. Decision Logic: Which HTML to return?
    if not user_has_submitted:
        # CASE 1: New User -> Show Welcome Screen
        team_html = welcome_html
        individual_html = f"<p style='text-align:center; color:#6b7280; padding-top:40px;'>{t(lang, 'lb_submit_to_rank')}</p>"
        
    elif full_leaderboard_df is None or full_leaderboard_df.empty:
        # CASE 2: Returning user, but data fetch failed -> Show Skeleton
        team_html = _build_skeleton_leaderboard(rows=6, is_team=True)
        individual_html = _build_skeleton_leaderboard(rows=6, is_team=False)
        
    else:
        # CASE 3: Returning user WITH data -> Show Real Tables
        try:
            # Generate summaries
            # CRITICAL: Pass 'lang' here so column headers and rank rows are translated
            team_html, individual_html, _, _, _, _ = generate_competitive_summary(
                full_leaderboard_df,
                team_name,
                username,
                0, 0, -1,
                lang=lang
            )
        except Exception as e:
            print(f"Error generating summary HTML: {e}")
            team_html = "<p style='text-align:center; color:red; padding-top:20px;'>Error rendering leaderboard.</p>"
            individual_html = "<p style='text-align:center; color:red; padding-top:20px;'>Error rendering leaderboard.</p>"

    # 7. Return all UI updates
    return (
        get_model_card(DEFAULT_MODEL, lang), # Translated Model Card
        team_html,
        individual_html,
        initial_ui["rank_message"], # Translated Rank Message
        gr.update(choices=initial_ui["model_choices"], value=initial_ui["model_value"], interactive=initial_ui["model_interactive"]),
        gr.update(minimum=1, maximum=initial_ui["complexity_max"], value=initial_ui["complexity_value"]),
        gr.update(choices=[f[0] for f in initial_ui["feature_set_choices"]], value=initial_ui["feature_set_value"], interactive=initial_ui["feature_set_interactive"]),
        gr.update(choices=initial_ui["data_size_choices"], value=initial_ui["data_size_value"], interactive=initial_ui["data_size_interactive"]),
    )
  
def _retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 0.5,
    description: str = "operation"
) -> T:
    """
    Execute a function with exponential backoff retry on failure.
    
    Concurrency Note: This helper provides resilience against transient
    network failures when calling external APIs (Competition.get_leaderboard,
    playground.submit_model). Essential for Cloud Run deployments where
    network calls may occasionally fail under load.
    
    Args:
        func: Callable to execute (should take no arguments)
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds, doubled each retry (default: 0.5)
        description: Human-readable description for logging
    
    Returns:
        Result from successful function call
    
    Raises:
        Last exception if all attempts fail
    """
    last_exception: Optional[Exception] = None
    delay = base_delay
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts:
                _log(f"{description} attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                _log(f"{description} failed after {max_attempts} attempts: {e}")
    
    # Loop always runs at least once (max_attempts >= 1), so last_exception is set
    raise last_exception  # type: ignore[misc]

def _log(msg: str):
    """Log message if DEBUG_LOG is enabled."""
    if DEBUG_LOG:
        print(f"[ModelBuildingGame] {msg}")

def _normalize_team_name(name: str) -> str:
    """Normalize team name for consistent comparison and storage."""
    if not name:
        return ""
    return " ".join(str(name).strip().split())

def _get_leaderboard_with_optional_token(playground_instance: Optional["Competition"], token: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Fetch fresh leaderboard with optional token authentication and retry logic.
    
    This is a helper function that centralizes the pattern of fetching
    a fresh (non-cached) leaderboard with optional token authentication.
    Use this for user-facing flows that require fresh, full data.
    
    Concurrency Note: Uses _retry_with_backoff for resilience against
    transient network failures.
    
    Args:
        playground_instance: The Competition playground instance (or None)
        token: Optional authentication token for the fetch
    
    Returns:
        DataFrame with leaderboard data, or None if fetch fails or playground is None
    """
    if playground_instance is None:
        return None
    
    def _fetch():
        if token:
            return playground_instance.get_leaderboard(token=token)
        return playground_instance.get_leaderboard()
    
    try:
        return _retry_with_backoff(_fetch, description="leaderboard fetch")
    except Exception as e:
        _log(f"Leaderboard fetch failed after retries: {e}")
        return None

def _fetch_leaderboard(token: Optional[str]) -> Optional[pd.DataFrame]:
    """
    Fetch leaderboard with auth-aware caching (TTL: LEADERBOARD_CACHE_SECONDS).
    
    Concurrency Note: Cache is keyed by auth scope ("anon" vs "auth") to prevent
    cross-user data leakage. Authenticated users share a single "auth" cache entry
    to avoid unbounded cache growth. Protected by _cache_lock.
    """
    # Determine cache key based on authentication status
    cache_key = "auth" if token else "anon"
    now = time.time()
    
    with _cache_lock:
        cache_entry = _leaderboard_cache[cache_key]
        if (
            cache_entry["data"] is not None
            and now - cache_entry["timestamp"] < LEADERBOARD_CACHE_SECONDS
        ):
            _log(f"Leaderboard cache hit ({cache_key})")
            return cache_entry["data"]

    _log(f"Fetching fresh leaderboard ({cache_key})...")
    df = None
    try:
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground_instance = Competition(playground_id)
        
        def _fetch():
            return playground_instance.get_leaderboard(token=token) if token else playground_instance.get_leaderboard()
        
        df = _retry_with_backoff(_fetch, description="leaderboard fetch")
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
        _log(f"Leaderboard fetched ({cache_key}): {len(df) if df is not None else 0} entries")
    except Exception as e:
        _log(f"Leaderboard fetch failed ({cache_key}): {e}")
        df = None

    with _cache_lock:
        _leaderboard_cache[cache_key]["data"] = df
        _leaderboard_cache[cache_key]["timestamp"] = time.time()
    return df

def _get_or_assign_team(username: str, leaderboard_df: Optional[pd.DataFrame]) -> Tuple[str, bool]:
    """Get existing team from leaderboard or assign random team."""
    # TEAM_NAMES is defined in configuration section below
    try:
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(
                            user_submissions["timestamp"], errors="coerce"
                        )
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                        _log(f"Sorted {len(user_submissions)} submissions by timestamp for {username}")
                    except Exception as ts_err:
                        _log(f"Timestamp sort error: {ts_err}")
                existing_team = user_submissions.iloc[0]["Team"]
                if pd.notna(existing_team) and str(existing_team).strip():
                    normalized = _normalize_team_name(existing_team)
                    _log(f"Found existing team for {username}: {normalized}")
                    return normalized, False
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        _log(f"Assigning new team to {username}: {new_team}")
        return new_team, True
    except Exception as e:
        _log(f"Team assignment error: {e}")
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        return new_team, True

def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    """Attempt to authenticate via session token. Returns (success, username, token)."""
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id:
            _log("No sessionid in request")
            return False, None, None
        
        from aimodelshare.aws import get_token_from_session, _get_username_from_token
        
        token = get_token_from_session(session_id)
        if not token:
            _log("Failed to get token from session")
            return False, None, None
            
        username = _get_username_from_token(token)
        if not username:
            _log("Failed to extract username from token")
            return False, None, None
        
        _log(f"Session auth successful for {username}")
        return True, username, token
        
    except Exception as e:
        _log(f"Session auth failed: {e}")
        return False, None, None

def _compute_user_stats(username: str, token: str) -> Dict[str, Any]:
    """
    Compute user statistics with caching.
    
    Concurrency Note: Protected by _user_stats_lock for thread-safe
    cache reads and writes.
    """
    now = time.time()
    
    # Thread-safe cache check
    with _user_stats_lock:
        cached = _user_stats_cache.get(username)
        if cached and (now - cached.get("_ts", 0) < USER_STATS_TTL):
            _log(f"User stats cache hit for {username}")
            # Return shallow copy to prevent caller mutations from affecting cache.
            # Stats dict contains only primitives (float, int, str), so shallow copy is sufficient.
            return cached.copy()

    _log(f"Computing fresh stats for {username}")
    leaderboard_df = _fetch_leaderboard(token)
    team_name, _ = _get_or_assign_team(username, leaderboard_df)
    
    stats = {
        "best_score": 0.0,
        "rank": 0,
        "team_name": team_name,
        "submission_count": 0,
        "last_score": 0.0,
        "_ts": time.time()
    }

    try:
        if leaderboard_df is not None and not leaderboard_df.empty:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                stats["submission_count"] = len(user_submissions)
                if "accuracy" in user_submissions.columns:
                    stats["best_score"] = float(user_submissions["accuracy"].max())
                    if "timestamp" in user_submissions.columns:
                        try:
                            user_submissions = user_submissions.copy()
                            user_submissions["timestamp"] = pd.to_datetime(
                                user_submissions["timestamp"], errors="coerce"
                            )
                            recent = user_submissions.sort_values("timestamp", ascending=False).iloc[0]
                            stats["last_score"] = float(recent["accuracy"])
                        except:
                            stats["last_score"] = stats["best_score"]
                    else:
                        stats["last_score"] = stats["best_score"]
            
            if "accuracy" in leaderboard_df.columns:
                user_bests = leaderboard_df.groupby("username")["accuracy"].max()
                ranked = user_bests.sort_values(ascending=False)
                try:
                    stats["rank"] = int(ranked.index.get_loc(username) + 1)
                except KeyError:
                    stats["rank"] = 0
    except Exception as e:
        _log(f"Error computing stats for {username}: {e}")

    # Thread-safe cache update
    with _user_stats_lock:
        _user_stats_cache[username] = stats
    _log(f"Stats for {username}: {stats}")
    return stats
def _build_attempts_tracker_html(current_count, limit=10):
    """
    Generate HTML for the attempts tracker display.
    Shows current attempt count vs limit with color coding.
    
    Args:
        current_count: Number of attempts used so far
        limit: Maximum allowed attempts (default: ATTEMPT_LIMIT)
    
    Returns:
        str: HTML string for the tracker display
    """
    if current_count >= limit:
        # Limit reached - red styling
        bg_color = "#f0f9ff"
        border_color = "#bae6fd"
        text_color = "#0369a1"
        icon = "🛑"
        label = f"Last chance (for now) to boost your score!: {current_count}/{limit}"
    else:
        # Normal - blue styling
        bg_color = "#f0f9ff"
        border_color = "#bae6fd"
        text_color = "#0369a1"
        icon = "📊"
        label = f"Attempts used: {current_count}/{limit}"

    return f"""<div style='text-align:center; padding:8px; margin:8px 0; background:{bg_color}; border-radius:8px; border:1px solid {border_color};'>
        <p style='margin:0; color:{text_color}; font-weight:600; font-size:1rem;'>{icon} {label}</p>
    </div>"""
    
def check_attempt_limit(submission_count: int, limit: int = None) -> Tuple[bool, str]:
    """Check if submission count exceeds limit."""
    # ATTEMPT_LIMIT is defined in configuration section below
    if limit is None:
        limit = ATTEMPT_LIMIT
    
    if submission_count >= limit:
        msg = f"⚠️ Attempt limit reached ({submission_count}/{limit})"
        return False, msg
    return True, f"Attempts: {submission_count}/{limit}"

# -------------------------------------------------------------------------
# Future: Fairness Metrics
# -------------------------------------------------------------------------

# def compute_fairness_metrics(y_true, y_pred, sensitive_attrs):
#     """
#     Compute fairness metrics for model predictions.
#     
#     Args:
#         y_true: Ground truth labels
#         y_pred: Model predictions
#         sensitive_attrs: DataFrame with sensitive attributes (race, sex, age)
#     
#     Returns:
#         dict: Fairness metrics including demographic parity, equalized odds
#     
#     TODO: Implement using fairlearn or aif360
#     """
#     pass



# -------------------------------------------------------------------------
# 1. Configuration
# -------------------------------------------------------------------------

MY_PLAYGROUND_ID = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"

# --- Submission Limit Configuration ---
# Maximum number of successful leaderboard submissions per user per session.
# Preview runs (pre-login) and failed/invalid attempts do NOT count toward this limit.
# Only actual successful playground.submit_model() calls increment the count.
#
# TODO: Server-side persistent enforcement recommended
# The current attempt limit is stored in gr.State (per-session) and can be bypassed
# by refreshing the browser. For production use with 100+ concurrent users,
# consider implementing server-side persistence via Redis or Firestore to track
# attempt counts per user across sessions.
ATTEMPT_LIMIT = 10

# --- Leaderboard Polling Configuration ---
# After a real authenticated submission, we poll the leaderboard to detect eventual consistency.
# This prevents the "stuck on first preview KPI" issue where the leaderboard hasn't updated yet.
# Increased from 12 to 60 to better tolerate backend latency and cold starts.
# If polling times out, optimistic fallback logic will provide provisional UI updates.
LEADERBOARD_POLL_TRIES = 60  # Number of polling attempts (increased to handle backend latency/cold starts)
LEADERBOARD_POLL_SLEEP = 1.0  # Sleep duration between polls (seconds)
ENABLE_AUTO_RESUBMIT_AFTER_READY = False  # Future feature flag for auto-resubmit

# -------------------------------------------------------------------------
# MODEL DEFINITIONS (Updated for I18n)
# -------------------------------------------------------------------------

MODEL_TYPES = {
    "The Balanced Generalist": {
        "model_builder": lambda: LogisticRegression(
            max_iter=500, random_state=42, class_weight="balanced"
        ),
        "key": "mod_bal",
        "desc_key": "desc_bal"  # <--- This key is required for translations
    },
    "The Rule-Maker": {
        "model_builder": lambda: DecisionTreeClassifier(
            random_state=42, class_weight="balanced"
        ),
        "key": "mod_rule",
        "desc_key": "desc_rule"
    },
    "The 'Nearest Neighbor'": {
        "model_builder": lambda: KNeighborsClassifier(),
        "key": "mod_knn",
        "desc_key": "desc_knn"
    },
    "The Deep Pattern-Finder": {
        "model_builder": lambda: RandomForestClassifier(
            random_state=42, class_weight="balanced"
        ),
        "key": "mod_deep",
        "desc_key": "desc_deep"
    }
}

DEFAULT_MODEL = "The Balanced Generalist"

TEAM_NAMES = [
    "The Moral Champions", "The Justice League", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]
CURRENT_TEAM_NAME = random.choice(TEAM_NAMES)


# --- Feature groups for scaffolding (Weak -> Medium -> Strong) ---
FEATURE_SET_ALL_OPTIONS = [
    ("Juvenile Felony Count", "juv_fel_count"),
    ("Juvenile Misdemeanor Count", "juv_misd_count"),
    ("Other Juvenile Count", "juv_other_count"),
    ("Race", "race"),
    ("Sex", "sex"),
    ("Charge Severity (M/F)", "c_charge_degree"),
    ("Days Before Arrest", "days_b_screening_arrest"),
    ("Age", "age"),
    ("Length of Stay", "length_of_stay"),
    ("Prior Crimes Count", "priors_count"),
]
FEATURE_SET_GROUP_1_VALS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex",
    "c_charge_degree", "days_b_screening_arrest"
]
FEATURE_SET_GROUP_2_VALS = ["c_charge_desc", "age"]
FEATURE_SET_GROUP_3_VALS = ["length_of_stay", "priors_count"]
ALL_NUMERIC_COLS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count",
    "days_b_screening_arrest", "age", "length_of_stay", "priors_count"
]
ALL_CATEGORICAL_COLS = [
    "race", "sex", "c_charge_degree"
]
DEFAULT_FEATURE_SET = FEATURE_SET_GROUP_1_VALS


# --- Data Size config ---
DATA_SIZE_MAP = {
    "Small (20%)": 0.2,
    "Medium (60%)": 0.6,
    "Large (80%)": 0.8,
    "Full (100%)": 1.0
}
DEFAULT_DATA_SIZE = "Small (20%)"


MAX_ROWS = 4000
TOP_N_CHARGE_CATEGORICAL = 50
WARM_MINI_ROWS = 300  # Small warm dataset for instant preview
CACHE_MAX_AGE_HOURS = 24  # Cache validity duration
np.random.seed(42)

# Global state containers (populated during initialization)
playground = None
X_TRAIN_RAW = None # Keep this for 100%
X_TEST_RAW = None
Y_TRAIN = None
Y_TEST = None
# Add a container for our pre-sampled data
X_TRAIN_SAMPLES_MAP = {}
Y_TRAIN_SAMPLES_MAP = {}

# Warm mini dataset for instant preview
X_TRAIN_WARM = None
Y_TRAIN_WARM = None

# Cache for transformed test sets (for future performance improvements)
TEST_CACHE = {}

# Initialization flags to track readiness state
INIT_FLAGS = {
    "competition": False,
    "dataset_core": False,
    "pre_samples_small": False,
    "pre_samples_medium": False,
    "pre_samples_large": False,
    "pre_samples_full": False,
    "leaderboard": False,
    "default_preprocessor": False,
    "warm_mini": False,
    "errors": []
}

# Lock for thread-safe flag updates
INIT_LOCK = threading.Lock()

# -------------------------------------------------------------------------
# 2. Data & Backend Utilities
# -------------------------------------------------------------------------

def _get_cache_dir():
    """Get or create the cache directory for datasets."""
    cache_dir = Path.home() / ".aimodelshare_cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

def _safe_request_csv(url, cache_filename="compas.csv"):
    """
    Request CSV from URL with local caching.
    Reuses cached file if it exists and is less than CACHE_MAX_AGE_HOURS old.
    """
    cache_dir = _get_cache_dir()
    cache_path = cache_dir / cache_filename
    
    # Check if cache exists and is fresh
    if cache_path.exists():
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - file_time < timedelta(hours=CACHE_MAX_AGE_HOURS):
            return pd.read_csv(cache_path)
    
    # Download fresh data
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))
    
    # Save to cache
    df.to_csv(cache_path, index=False)
    
    return df

def safe_int(value, default=1):
    """
    Safely coerce a value to int, returning default if value is None or invalid.
    Protects against TypeError when Gradio sliders receive None.
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def load_and_prep_data(use_cache=True):
    """
    Load, sample, and prepare raw COMPAS dataset.
    NOW PRE-SAMPLES ALL DATA SIZES and creates warm mini dataset.
    """
    url = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"

    # Use cached version if available
    if use_cache:
        try:
            df = _safe_request_csv(url)
        except Exception as e:
            print(f"Cache failed, fetching directly: {e}")
            response = requests.get(url)
            df = pd.read_csv(StringIO(response.text))
    else:
        response = requests.get(url)
        df = pd.read_csv(StringIO(response.text))

    # Calculate length_of_stay
    try:
        df['c_jail_in'] = pd.to_datetime(df['c_jail_in'])
        df['c_jail_out'] = pd.to_datetime(df['c_jail_out'])
        df['length_of_stay'] = (df['c_jail_out'] - df['c_jail_in']).dt.total_seconds() / (24 * 60 * 60) # in days
    except Exception:
        df['length_of_stay'] = np.nan

    if df.shape[0] > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42)

    feature_columns = ALL_NUMERIC_COLS + ALL_CATEGORICAL_COLS
    feature_columns = sorted(list(set(feature_columns)))

    target_column = "two_year_recid"

    if "c_charge_desc" in df.columns:
        top_charges = df["c_charge_desc"].value_counts().head(TOP_N_CHARGE_CATEGORICAL).index
        df["c_charge_desc"] = df["c_charge_desc"].apply(
            lambda x: x if pd.notna(x) and x in top_charges else "OTHER"
        )

    for col in feature_columns:
        if col not in df.columns:
            if col == 'length_of_stay' and 'length_of_stay' in df.columns:
                continue
            df[col] = np.nan

    X = df[feature_columns].copy()
    y = df[target_column].copy()

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # Pre-sample all data sizes
    global X_TRAIN_SAMPLES_MAP, Y_TRAIN_SAMPLES_MAP, X_TRAIN_WARM, Y_TRAIN_WARM

    X_TRAIN_SAMPLES_MAP["Full (100%)"] = X_train_raw
    Y_TRAIN_SAMPLES_MAP["Full (100%)"] = y_train

    for label, frac in DATA_SIZE_MAP.items():
        if frac < 1.0:
            X_train_sampled = X_train_raw.sample(frac=frac, random_state=42)
            y_train_sampled = y_train.loc[X_train_sampled.index]
            X_TRAIN_SAMPLES_MAP[label] = X_train_sampled
            Y_TRAIN_SAMPLES_MAP[label] = y_train_sampled

    # Create warm mini dataset for instant preview
    warm_size = min(WARM_MINI_ROWS, len(X_train_raw))
    X_TRAIN_WARM = X_train_raw.sample(n=warm_size, random_state=42)
    Y_TRAIN_WARM = y_train.loc[X_TRAIN_WARM.index]



    return X_train_raw, X_test_raw, y_train, y_test


# [NEW]
def _get_slide1_html(lang):
    return f"""
    <div class='slide-content'>
    <div class='panel-box'>
    <h3 style='font-size: 1.5rem; text-align:center; margin-top:0;'>{t(lang, 's1_intro')}</h3>
    <ul style='list-style: none; padding-left: 0; margin-top: 24px; margin-bottom: 24px;'>
        <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'><span style='font-size: 1.5rem; vertical-align: middle;'>✅</span> {t(lang, 's1_li1')}</li>
        <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'><span style='font-size: 1.5rem; vertical-align: middle;'>✅</span> {t(lang, 's1_li2')}</li>
        <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'><span style='font-size: 1.5rem; vertical-align: middle;'>✅</span> {t(lang, 's1_li3')}</li>
    </ul>
    <div style='background:white; padding:16px; border-radius:12px; margin:12px 0; text-align:center;'>
        <div style='display:inline-block; background:#dbeafe; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#0369a1;'>{t(lang, 's1_in')}</h3></div>
        <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
        <div style='display:inline-block; background:#fef3c7; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#92400e;'>{t(lang, 's1_mod')}</h3></div>
        <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
        <div style='display:inline-block; background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#15803d;'>{t(lang, 's1_out')}</h3></div>
    </div>
    <hr style='margin: 24px 0; border-top: 2px solid #c7d2fe;'>
    <h3 style='font-size: 1.5rem; text-align:center;'>{t(lang, 's1_chal_title')}</h3>
    <p style='font-size: 1.1rem; text-align:center; margin-top: 12px;'>{t(lang, 's1_chal_body')}</p>
    <p style='font-size: 1.1rem; text-align:center; margin-top: 12px;'>{t(lang, 's1_rem')}</p>
    </div>
    </div>
    """

# [NEW]
def _get_slide2_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <h3>{t(lang, 's2_miss_head')}</h3>
            <p>{t(lang, 's2_miss_body')}</p>
            <h3>{t(lang, 's2_comp_head')}</h3>
            <p>{t(lang, 's2_comp_body')}</p>
        </div>
        <div class='leaderboard-box' style='max-width: 600px; margin: 16px auto; text-align: center; padding: 16px;'>
            <p style='font-size: 1.1rem; margin:0;'>{t(lang, 's2_join')}</p>
            <h3 style='font-size: 1.75rem; color: #6b7280; margin: 8px 0;'>🛡️ The Ethical Explorers</h3>
        </div>
        <div class='mock-ui-box'>
            <h3>{t(lang, 's2_data_head')}</h3>
            <p>{t(lang, 's2_data_intro')}</p>
            <ol style='list-style-position: inside; padding-left: 20px;'>
                <li>{t(lang, 's2_li1')}
                    <ul style='margin-left: 20px; list-style-type: disc;'><li>{t(lang, 's2_li1_sub')}</li></ul>
                </li>
                <li>{t(lang, 's2_li2')}
                    <ul style='margin-left: 20px; list-style-type: disc;'><li>{t(lang, 's2_li2_sub')}</li></ul>
                </li>
            </ol>
            <h3>{t(lang, 's2_core_head')}</h3>
            <p>{t(lang, 's2_core_body')}</p>
            <p>{t(lang, 's2_ready')}</p>
        </div>
    </div>
    """

# [NEW]
def _get_slide3_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <p>{t(lang, 's3_p1')}</p>
            <h3>{t(lang, 's3_head1')}</h3>
            <p>{t(lang, 's3_p2')}</p>
            <div style='background:white; padding:16px; border-radius:12px; margin:12px 0; text-align:center;'>
                <div style='display:inline-block; background:#dbeafe; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#0369a1;'>{t(lang, 's1_in')}</h3></div>
                <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                <div style='display:inline-block; background:#fef3c7; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#92400e;'>{t(lang, 's1_mod')}</h3></div>
                <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                <div style='display:inline-block; background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:4px;'><h3 style='margin:0; color:#15803d;'>{t(lang, 's1_out')}</h3></div>
            </div>
            <p>{t(lang, 's3_eng_note')}</p>
        </div>
        <div class='mock-ui-box'>
            <h3>{t(lang, 's3_comp_head')}</h3>
            <p>{t(lang, 's3_c1')}</p>
            <p>{t(lang, 's3_c2')}</p>
            <p>{t(lang, 's3_c3')}</p>
            <hr>
            <p>{t(lang, 's3_learn')}</p>
        </div>
    </div>
    """

# [NEW]
def _get_slide4_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <p>{t(lang, 's4_p1')}</p>
            <h3>{t(lang, 's4_sec_head')}</h3>
            <p>{t(lang, 's4_sec_body')}</p>
            <h3>{t(lang, 's4_loop_head')}</h3>
            <ol style='list-style-position: inside;'>
                <li>{t(lang, 's4_l1')}</li>
                <li>{t(lang, 's4_l2')}</li>
                <li>{t(lang, 's4_l3')}</li>
            </ol>
        </div>
        <h3>{t(lang, 's4_same')}</h3>
        <div class='step-visual'>
            <div class='step-visual-box'>{t(lang, 's4_v1')}</div><div class='step-visual-arrow'>→</div>
            <div class='step-visual-box'>{t(lang, 's4_v2')}</div><div class='step-visual-arrow'>→</div>
            <div class='step-visual-box'>{t(lang, 's4_v3')}</div><div class='step-visual-arrow'>→</div>
            <div class='step-visual-box'>{t(lang, 's4_v4')}</div>
        </div>
        <div class='leaderboard-box' style='text-align:center;'>
            <p>{t(lang, 's4_tip')}</p>
        </div>
    </div>
    """

# [NEW]
def _get_slide5_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='mock-ui-inner'>
            <p>{t(lang, 's5_intro')}</p>
            <hr style='margin: 16px 0;'>
            <h3 style='margin-top:0;'>{t(lang, 's5_k1')}</h3>
            <div style='font-size: 1rem; margin-bottom:12px;'>{t(lang, 's5_k1_desc')}</div>
            <div class='mock-ui-control-box'>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-on'>◉</span> {t(lang, 's5_m1')}</p>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-off'>○</span> {t(lang, 's5_m2')}</p>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-off'>○</span> {t(lang, 's5_m3')}</p>
            </div>
            <hr style='margin: 24px 0;'>
            <h3>{t(lang, 's5_k2')}</h3>
            <div class='mock-ui-control-box' style='text-align: center;'><p style='font-size: 1.1rem; margin:0;'>{t(lang, 's5_range')}</p></div>
            <div style='margin-top: 16px; font-size: 1rem;'>
                <ul style='list-style-position: inside;'>
                    <li>{t(lang, 's5_k2_desc1')}</li>
                    <li>{t(lang, 's5_k2_desc2')}
                        <ul style='list-style-position: inside; margin-left: 20px;'>
                            <li>{t(lang, 's5_low')}</li>
                            <li>{t(lang, 's5_high')}</li>
                        </ul>
                    </li>
                </ul>
                <p style='color:#b91c1c; font-weight:bold; margin-top:10px;'>{t(lang, 's5_warn')}</p>
            </div>
        </div>
    </div>
    """

# [NEW]
def _get_slide6_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='mock-ui-inner'>
            <p>{t(lang, 's6_intro')}</p>
            <hr style='margin: 16px 0;'>
            <h3 style='margin-top:0;'>{t(lang, 's6_k3')}</h3>
            <div style='font-size: 1rem; margin-bottom:12px;'>{t(lang, 's6_k3_desc')}</div>
            <div class='mock-ui-control-box'>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-on'>☑</span> {t(lang, 's6_behav')}</p>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-off'>☐</span> {t(lang, 's6_demo')}</p>
            </div>
            <p style='margin-top:10px;'>{t(lang, 's6_job')}</p>
            <hr style='margin: 24px 0;'>
            <h3>{t(lang, 's6_k4')}</h3>
            <div style='font-size: 1rem; margin-bottom:12px;'>{t(lang, 's6_k4_desc')}</div>
            <div class='mock-ui-control-box'>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-on'>◉</span> {t(lang, 's6_small')}</p>
                <p style='font-size: 1.1rem; margin: 8px 0;'><span class='mock-ui-radio-off'>○</span> {t(lang, 's6_full')}</p>
            </div>
        </div>
    </div>
    """

# [NEW]
def _get_slide7_html(lang):
    return f"""
    <div class='slide-content'>
        <div class='panel-box'>
            <p>{t(lang, 's7_p1')}</p>
            <h3>{t(lang, 's7_head1')}</h3>
            <ul style='list-style-position: inside;'>
                <li>{t(lang, 's7_acc')}</li>
                <li>{t(lang, 's7_lead')}</li>
            </ul>
            <h3>{t(lang, 's7_head2')}</h3>
            <ul style='list-style-position: inside;'>
                <li>{t(lang, 's7_comp')}</li>
                <li>{t(lang, 's7_promo')}</li>
            </ul>
            <div style='text-align:center; font-weight:bold; font-size:1.2rem; color:#4f46e5; margin:16px 0;'>
                {t(lang, 's7_ranks')}
            </div>
            <h3>{t(lang, 's7_head3')}</h3>
            <p>{t(lang, 's7_final')}</p>
            <p>{t(lang, 's7_rem')}</p>
        </div>
    </div>
    """
  
  # [NEW]
def build_login_prompt_html(lang="en"):
    """
    Generate HTML for the login prompt text *only*.
    The styled preview card will be prepended to this.
    """
    return f"""
    <h2 style='color: #111827; margin-top:20px; border-top: 2px solid #e5e7eb; padding-top: 20px;'>{t(lang, 'login_title')}</h2>
    <div style='margin-top:16px; text-align:left; font-size:1rem; line-height:1.6; color:#374151;'>
        <p style='margin:12px 0;'>
            {t(lang, 'login_desc')}
        </p>
        <p style='margin:12px 0;'>
            <strong>{t(lang, 'login_new')}</strong>
            <a href='https://www.modelshare.ai/login' target='_blank' 
                style='color:#4f46e5; text-decoration:underline;'>modelshare.ai/login</a>
        </p>
    </div>
    """
def _background_initializer():
    """
    Background thread that performs sequential initialization tasks.
    Updates INIT_FLAGS dict with readiness booleans and captures errors.
    
    Initialization sequence:
    1. Competition object connection
    2. Dataset cached download and core split
    3. Warm mini dataset creation
    4. Progressive sampling: small -> medium -> large -> full
    5. Leaderboard prefetch
    6. Default preprocessor fit on small sample
    """
    global playground, X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST
    
    try:
        # Step 1: Connect to competition
        with INIT_LOCK:
            if playground is None:
                playground = Competition(MY_PLAYGROUND_ID)
            INIT_FLAGS["competition"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Competition connection failed: {str(e)}")
    
    try:
        # Step 2: Load dataset core (train/test split)
        X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_and_prep_data(use_cache=True)
        with INIT_LOCK:
            INIT_FLAGS["dataset_core"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Dataset loading failed: {str(e)}")
        return  # Cannot proceed without data
    
    try:
        # Step 3: Warm mini dataset (already created in load_and_prep_data)
        if X_TRAIN_WARM is not None and len(X_TRAIN_WARM) > 0:
            with INIT_LOCK:
                INIT_FLAGS["warm_mini"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Warm mini dataset failed: {str(e)}")
    
    # Progressive sampling - samples are already created in load_and_prep_data
    # Just mark them as ready sequentially with delays to simulate progressive loading
    
    try:
        # Step 4a: Small sample (20%)
        time.sleep(0.5)  # Simulate processing
        with INIT_LOCK:
            INIT_FLAGS["pre_samples_small"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Small sample failed: {str(e)}")
    
    try:
        # Step 4b: Medium sample (60%)
        time.sleep(0.5)
        with INIT_LOCK:
            INIT_FLAGS["pre_samples_medium"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Medium sample failed: {str(e)}")
    
    try:
        # Step 4c: Large sample (80%)
        time.sleep(0.5)
        with INIT_LOCK:
            INIT_FLAGS["pre_samples_large"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Large sample failed: {str(e)}")
        print(f"✗ Large sample failed: {e}")
    
    try:
        # Step 4d: Full sample (100%)
        print("Background init: Full sample (100%)...")
        time.sleep(0.5)
        with INIT_LOCK:
            INIT_FLAGS["pre_samples_full"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Full sample failed: {str(e)}")
    
    try:
        # Step 5: Leaderboard prefetch (best-effort, unauthenticated)
        # Concurrency Note: Do NOT use os.environ for ambient token - prefetch
        # anonymously to warm the cache for initial page loads.
        if playground is not None:
            _ = _get_leaderboard_with_optional_token(playground, None)
            with INIT_LOCK:
                INIT_FLAGS["leaderboard"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Leaderboard prefetch failed: {str(e)}")
    
    try:
        # Step 6: Default preprocessor on small sample
        _fit_default_preprocessor()
        with INIT_LOCK:
            INIT_FLAGS["default_preprocessor"] = True
    except Exception as e:
        with INIT_LOCK:
            INIT_FLAGS["errors"].append(f"Default preprocessor failed: {str(e)}")
        print(f"✗ Default preprocessor failed: {e}")
    

def _fit_default_preprocessor():
    """
    Pre-fit a default preprocessor on the small sample with default features.
    Uses memoized preprocessor builder for efficiency.
    """
    if "Small (20%)" not in X_TRAIN_SAMPLES_MAP:
        return
    
    X_sample = X_TRAIN_SAMPLES_MAP["Small (20%)"]
    
    # Use default feature set
    numeric_cols = [f for f in DEFAULT_FEATURE_SET if f in ALL_NUMERIC_COLS]
    categorical_cols = [f for f in DEFAULT_FEATURE_SET if f in ALL_CATEGORICAL_COLS]
    
    if not numeric_cols and not categorical_cols:
        return
    
    # Use memoized builder
    preprocessor, selected_cols = build_preprocessor(numeric_cols, categorical_cols)
    preprocessor.fit(X_sample[selected_cols])

def start_background_init():
    """
    Start the background initialization thread.
    Should be called once at app creation.
    """
    thread = threading.Thread(target=_background_initializer, daemon=True)
    thread.start()

def poll_init_status():
    """
    Poll the initialization status and return readiness bool.
    Returns empty string for HTML so users don't see the checklist.
    
    Returns:
        tuple: (status_html, ready_bool)
    """
    with INIT_LOCK:
        flags = INIT_FLAGS.copy()
    
    # Determine if minimum requirements met
    ready = flags["competition"] and flags["dataset_core"] and flags["pre_samples_small"]
    
    return "", ready

def get_available_data_sizes():
    """
    Return list of data sizes that are currently available based on init flags.
    """
    with INIT_LOCK:
        flags = INIT_FLAGS.copy()
    
    available = []
    if flags["pre_samples_small"]:
        available.append("Small (20%)")
    if flags["pre_samples_medium"]:
        available.append("Medium (60%)")
    if flags["pre_samples_large"]:
        available.append("Large (80%)")
    if flags["pre_samples_full"]:
        available.append("Full (100%)")
    
    return available if available else ["Small (20%)"]  # Fallback

def _is_ready() -> bool:
    """
    Check if initialization is complete and system is ready for real submissions.
    
    Returns:
        bool: True if competition, dataset, and small sample are initialized
    """
    with INIT_LOCK:
        flags = INIT_FLAGS.copy()
    return flags["competition"] and flags["dataset_core"] and flags["pre_samples_small"]

def _get_user_latest_accuracy(df: Optional[pd.DataFrame], username: str) -> Optional[float]:
    """
    Extract the user's latest submission accuracy from the leaderboard.
    
    Uses timestamp sorting when available; otherwise assumes last row is latest.
    
    Args:
        df: Leaderboard DataFrame
        username: Username to extract accuracy for
    
    Returns:
        float: Latest submission accuracy, or None if not found/invalid
    """
    if df is None or df.empty:
        return None
    
    try:
        user_rows = df[df["username"] == username]
        if user_rows.empty or "accuracy" not in user_rows.columns:
            return None
        
        # Try timestamp-based sorting if available
        if "timestamp" in user_rows.columns:
            user_rows = user_rows.copy()
            user_rows["__parsed_ts"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
            valid_ts = user_rows[user_rows["__parsed_ts"].notna()]
            
            if not valid_ts.empty:
                # Sort by timestamp and get latest
                latest_row = valid_ts.sort_values("__parsed_ts", ascending=False).iloc[0]
                return float(latest_row["accuracy"])
        
        # Fallback: assume last row is latest (append order)
        return float(user_rows.iloc[-1]["accuracy"])
        
    except Exception as e:
        _log(f"Error extracting latest accuracy for {username}: {e}")
        return None

def _get_user_latest_ts(df: Optional[pd.DataFrame], username: str) -> Optional[float]:
    """
    Extract the user's latest valid timestamp from the leaderboard.
    
    Args:
        df: Leaderboard DataFrame
        username: Username to extract timestamp for
    
    Returns:
        float: Latest timestamp as unix epoch, or None if not found/invalid
    """
    if df is None or df.empty:
        return None
    
    try:
        user_rows = df[df["username"] == username]
        if user_rows.empty or "timestamp" not in user_rows.columns:
            return None
        
        # Parse timestamps and get the latest
        user_rows = user_rows.copy()
        user_rows["__parsed_ts"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
        valid_ts = user_rows[user_rows["__parsed_ts"].notna()]
        
        if valid_ts.empty:
            return None
        
        latest_ts = valid_ts["__parsed_ts"].max()
        return latest_ts.timestamp() if pd.notna(latest_ts) else None
    except Exception as e:
        _log(f"Error extracting latest timestamp for {username}: {e}")
        return None

def _user_rows_changed(
    refreshed_leaderboard: Optional[pd.DataFrame],
    username: str,
    old_row_count: int,
    old_best_score: float,
    old_latest_ts: Optional[float] = None,
    old_latest_score: Optional[float] = None
) -> bool:
    """
    Check if user's leaderboard entries have changed after submission.
    
    Used after polling to detect if the leaderboard has updated with the new submission.
    Checks row count (new submission added), best score (score improved), latest timestamp,
    and latest accuracy (handles backend overwrite without append).
    
    Args:
        refreshed_leaderboard: Fresh leaderboard data
        username: Username to check for
        old_row_count: Previous number of submissions for this user
        old_best_score: Previous best accuracy score
        old_latest_ts: Previous latest timestamp (unix epoch), optional
        old_latest_score: Previous latest submission accuracy, optional
    
    Returns:
        bool: True if user has more rows, better score, newer timestamp, or changed latest accuracy
    """
    if refreshed_leaderboard is None or refreshed_leaderboard.empty:
        return False
    
    try:
        user_rows = refreshed_leaderboard[refreshed_leaderboard["username"] == username]
        if user_rows.empty:
            return False
        
        new_row_count = len(user_rows)
        new_best_score = float(user_rows["accuracy"].max()) if "accuracy" in user_rows.columns else 0.0
        new_latest_ts = _get_user_latest_ts(refreshed_leaderboard, username)
        new_latest_score = _get_user_latest_accuracy(refreshed_leaderboard, username)
        
        # Changed if we have more submissions, better score, newer timestamp, or changed latest accuracy
        changed = (new_row_count > old_row_count) or (new_best_score > old_best_score + 0.0001)
        
        # Check timestamp if available
        if old_latest_ts is not None and new_latest_ts is not None:
            changed = changed or (new_latest_ts > old_latest_ts)
        
        # Check latest accuracy change (handles overwrite-without-append case)
        if old_latest_score is not None and new_latest_score is not None:
            accuracy_changed = abs(new_latest_score - old_latest_score) >= 0.00001
            if accuracy_changed:
                _log(f"Latest accuracy changed: {old_latest_score:.4f} -> {new_latest_score:.4f}")
            changed = changed or accuracy_changed
        
        if changed:
            _log(f"User rows changed for {username}:")
            _log(f"  Row count: {old_row_count} -> {new_row_count}")
            _log(f"  Best score: {old_best_score:.4f} -> {new_best_score:.4f}")
            _log(f"  Latest score: {old_latest_score if old_latest_score else 'N/A'} -> {new_latest_score if new_latest_score else 'N/A'}")
            _log(f"  Timestamp: {old_latest_ts} -> {new_latest_ts}")
        
        return changed
    except Exception as e:
        _log(f"Error checking user rows: {e}")
        return False

@functools.lru_cache(maxsize=32)
def _get_cached_preprocessor_config(numeric_cols_tuple, categorical_cols_tuple):
    """
    Create and return preprocessor configuration (memoized).
    Uses tuples for hashability in lru_cache.
    
    Concurrency Note: Uses sparse_output=True for OneHotEncoder to reduce memory
    footprint under concurrent requests. Downstream models that require dense
    arrays (DecisionTree, RandomForest) will convert via .toarray() as needed.
    LogisticRegression and KNeighborsClassifier handle sparse matrices natively.
    
    Returns tuple of (transformers_list, selected_columns) ready for ColumnTransformer.
    """
    numeric_cols = list(numeric_cols_tuple)
    categorical_cols = list(categorical_cols_tuple)
    
    transformers = []
    selected_cols = []
    
    if numeric_cols:
        num_tf = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ])
        transformers.append(("num", num_tf, numeric_cols))
        selected_cols.extend(numeric_cols)
    
    if categorical_cols:
        # Use sparse_output=True to reduce memory footprint
        cat_tf = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))
        ])
        transformers.append(("cat", cat_tf, categorical_cols))
        selected_cols.extend(categorical_cols)
    
    return transformers, selected_cols

def build_preprocessor(numeric_cols, categorical_cols):
    """
    Build a preprocessor using cached configuration.
    The configuration (pipeline structure) is memoized; the actual fit is not.
    
    Note: Returns sparse matrices when categorical columns are present.
    Use _ensure_dense() helper if model requires dense input.
    """
    # Convert to tuples for caching
    numeric_tuple = tuple(sorted(numeric_cols))
    categorical_tuple = tuple(sorted(categorical_cols))
    
    transformers, selected_cols = _get_cached_preprocessor_config(numeric_tuple, categorical_tuple)
    
    # Create new ColumnTransformer with cached config
    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    
    return preprocessor, selected_cols

def _ensure_dense(X):
    """
    Convert sparse matrix to dense if necessary.
    
    Helper function for models that don't support sparse input
    (DecisionTree, RandomForest). LogisticRegression and KNN
    handle sparse matrices natively.
    """
    from scipy import sparse
    if sparse.issparse(X):
        return X.toarray()
    return X

def tune_model_complexity(model, level):
    """
    Map a 1–10 slider value to model hyperparameters.
    Levels 1–3: Conservative / simple
    Levels 4–7: Balanced
    Levels 8–10: Aggressive / risk of overfitting
    """
    level = int(level)
    if isinstance(model, LogisticRegression):
        c_map = {1: 0.01, 2: 0.025, 3: 0.05, 4: 0.1, 5: 0.25, 6: 0.5, 7: 1.0, 8: 2.0, 9: 5.0, 10: 10.0}
        model.C = c_map.get(level, 1.0)
        model.max_iter = max(getattr(model, "max_iter", 0), 500)
    elif isinstance(model, RandomForestClassifier):
        depth_map = {1: 3, 2: 5, 3: 7, 4: 9, 5: 11, 6: 15, 7: 20, 8: 25, 9: None, 10: None}
        est_map = {1: 20, 2: 30, 3: 40, 4: 60, 5: 80, 6: 100, 7: 120, 8: 150, 9: 180, 10: 220}
        model.max_depth = depth_map.get(level, 10)
        model.n_estimators = est_map.get(level, 100)
    elif isinstance(model, DecisionTreeClassifier):
        depth_map = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 8, 7: 10, 8: 12, 9: 15, 10: None}
        model.max_depth = depth_map.get(level, 6)
    elif isinstance(model, KNeighborsClassifier):
        k_map = {1: 100, 2: 75, 3: 60, 4: 50, 5: 40, 6: 30, 7: 25, 8: 15, 9: 7, 10: 3}
        model.n_neighbors = k_map.get(level, 25)
    return model

# --- New Helper Functions for HTML Generation ---

def _normalize_team_name(name: str) -> str:
    """
    Normalize team name for consistent comparison and storage.
    
    Strips leading/trailing whitespace and collapses multiple spaces into single spaces.
    This ensures consistent formatting across environment variables, state, and leaderboard rendering.
    
    Args:
        name: Team name to normalize (can be None or empty)
    
    Returns:
        str: Normalized team name, or empty string if input is None/empty
    
    Examples:
        >>> _normalize_team_name("  The Ethical Explorers  ")
        'The Ethical Explorers'
        >>> _normalize_team_name("The  Moral   Champions")
        'The Moral Champions'
        >>> _normalize_team_name(None)
        ''
    """
    if not name:
        return ""
    return " ".join(str(name).strip().split())



def _build_skeleton_leaderboard(rows=6, is_team=True, submit_button_label="5. 🔬 Build & Submit Model"):
    context_label = "Team" if is_team else "Individual"
    return f"""
    <div class='lb-placeholder' aria-live='polite'>
        <div class='lb-placeholder-title'>{context_label} Standings Pending</div>
        <div class='lb-placeholder-sub'>
            <p style='margin:0 0 6px 0;'>Submit your first model to populate this table.</p>
            <p style='margin:0;'><strong>Click “{submit_button_label}” (bottom-left)</strong> to begin!</p>
        </div>
    </div>
    """
# --- FIX APPLIED HERE ---
def build_login_prompt_html(lang="en"):
    """
    Generate HTML for the login prompt text *only*.
    The styled preview card will be prepended to this.
    """
    return f"""
    <h2 style='color: #111827; margin-top:20px; border-top: 2px solid #e5e7eb; padding-top: 20px;'>{t(lang, 'login_title')}</h2>
    <div style='margin-top:16px; text-align:left; font-size:1rem; line-height:1.6; color:#374151;'>
        <p style='margin:12px 0;'>
            {t(lang, 'login_desc')}
        </p>
        <p style='margin:12px 0;'>
            <strong>{t(lang, 'login_new')}</strong>
            <a href='https://www.modelshare.ai/login' target='_blank' 
                style='color:#4f46e5; text-decoration:underline;'>modelshare.ai/login</a>
        </p>
    </div>
    """
# --- END OF FIX ---

# [CHANGED] - Added lang parameter and t() calls
def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count, is_preview=False, is_pending=False, local_test_accuracy=None, lang="en"):
    """Generates the HTML for the KPI feedback card with translations."""

    if is_pending:
        title = "⏳ Processing..."
        acc_color = "#3b82f6"
        acc_text = f"{(local_test_accuracy * 100):.2f}%" if local_test_accuracy is not None else "N/A"
        acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Pending update...</p>"
        border_color = acc_color
        rank_color = "#6b7280"
        rank_text = "..."
        rank_diff_html = ""

    elif is_preview:
        title = "🔬 " + t(lang, 'kpi_preview')
        acc_color = "#16a34a"
        acc_text = f"{(new_score * 100):.2f}%" if new_score > 0 else "N/A"
        acc_diff_html = ""
        border_color = acc_color
        rank_color = "#3b82f6"
        rank_text = "N/A"
        rank_diff_html = ""

    elif submission_count == 0:
        title = t(lang, 'kpi_first')
        acc_color = "#16a34a"
        acc_text = f"{(new_score * 100):.2f}%"
        acc_diff_html = ""
        rank_color = "#3b82f6"
        rank_text = f"#{new_rank}"
        rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>{t(lang, 'kpi_on_board')}</p>"
        border_color = acc_color

    else:
        score_diff = new_score - last_score
        if abs(score_diff) < 0.0001:
            title = t(lang, 'kpi_success')
            acc_color = "#6b7280"
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>{t(lang, 'kpi_no_change')}</p>"
            border_color = acc_color
        elif score_diff > 0:
            title = t(lang, 'kpi_success')
            acc_color = "#16a34a"
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>+{(score_diff * 100):.2f} (⬆️)</p>"
            border_color = acc_color
        else:
            title = t(lang, 'kpi_lower')
            acc_color = "#ef4444"
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>{(score_diff * 100):.2f} (⬇️)</p>"
            border_color = acc_color

        rank_diff = last_rank - new_rank
        rank_color = "#3b82f6"
        rank_text = f"#{new_rank}"
        if last_rank == 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>{t(lang, 'kpi_on_board')}</p>"
        elif rank_diff > 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #16a34a; margin:0;'>🚀 {t(lang, 'kpi_moved_up')} {rank_diff}!</p>"
        elif rank_diff < 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #ef4444; margin:0;'>🔻 {t(lang, 'kpi_dropped')} {abs(rank_diff)}</p>"
        else:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {rank_color}; margin:0;'>{t(lang, 'kpi_no_change')}</p>"

    return f"""
    <div class='kpi-card' style='border-color: {border_color};'>
        <h2 style='color: #111827; margin-top:0;'>{title}</h2>
        <div class='kpi-card-body'>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>{t(lang, 'kpi_new_acc')}</p>
                <p class='kpi-score' style='color: {acc_color};'>{acc_text}</p>
                {acc_diff_html}
            </div>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>{t(lang, 'kpi_rank')}</p>
                <p class='kpi-score' style='color: {rank_color};'>{rank_text}</p>
                {rank_diff_html}
            </div>
        </div>
    </div>
    """
  
def build_standing_html(user_stats, lang="en"):
    """
    Generates the HTML for Slide 1 (User Standing/Stats).
    Includes logic to translate Team Names.
    """
    # Helper to translate team names specifically
    def get_team_name(name):
        if not name: return "N/A"
        # Try to find the team name in the current language dictionary
        # If not found (e.g. custom team or english fallback), return original
        if lang in TRANSLATIONS and name in TRANSLATIONS[lang]:
            return TRANSLATIONS[lang][name]
        return name

    # 1. Authenticated View (User has a score)
    if user_stats.get("is_signed_in") and user_stats.get("best_score") is not None:
        best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
        rank_text = f"#{user_stats['rank']}" if user_stats.get("rank") else "N/A"
        
        # Translate the team name
        raw_team = user_stats.get("team_name", "")
        team_text = get_team_name(raw_team)
        
        team_rank_text = f"#{user_stats['team_rank']}" if user_stats.get("team_rank") else "N/A"
        
        return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                {t(lang, 's1_title_auth')}
            </h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    {t(lang, 's1_sub_auth')}
                </p>
                <div class='stat-grid'>
                    <div class='stat-card stat-card--success'>
                        <p class='stat-card__label'>{t(lang, 'lbl_best_acc')}</p>
                        <p class='stat-card__value'>{best_score_pct}</p>
                    </div>
                    <div class='stat-card stat-card--accent'>
                        <p class='stat-card__label'>{t(lang, 'lbl_ind_rank')}</p>
                        <p class='stat-card__value'>{rank_text}</p>
                    </div>
                </div>
                <div class='team-card'>
                    <p class='team-card__label'>{t(lang, 'lbl_team')}</p>
                    <p class='team-card__value'>🛡️ {team_text}</p>
                    <p class='team-card__rank'>{t(lang, 'lbl_team_rank')} {team_rank_text}</p>
                </div>
                <ul class='bullet-list'>
                    <li>{t(lang, 's1_li1')}</li>
                    <li>{t(lang, 's1_li2')}</li>
                    <li>{t(lang, 's1_li3')}</li>
                    <li>{t(lang, 's1_li4')}</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>
                    {t(lang, 's1_congrats')}
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    {t(lang, 's1_box_title')}
                </p>
                <p>
                    {t(lang, 's1_box_text')}
                </p>
            </div>
        </div>
        """
        
    # 2. Guest/Pre-submission View (Logged in but no score)
    elif user_stats.get("is_signed_in"):
        return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                {t(lang, 's1_title_guest')}
            </h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    {t(lang, 's1_sub_guest')}
                </p>
                <ul class='bullet-list'>
                    <li>{t(lang, 's1_li1_guest')}</li>
                    <li>{t(lang, 's1_li2_guest')}</li>
                    <li>{t(lang, 's1_li3_guest')}</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>
                    {t(lang, 's1_ready')}
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    {t(lang, 's1_box_title')}
                </p>
                <p>
                    {t(lang, 's1_box_text')}
                </p>
            </div>
        </div>
        """
        
    # 3. No Session View (Not logged in)
    else:
        return f"""
        <div class='slide-shell slide-shell--warning' style='text-align:center;'>
            <h2 class='slide-shell__title'>
                {t(lang, 'loading_session')}
            </h2>
        </div>
        """
      
def _build_team_html(team_summary_df, team_name, lang="en"):
    """
    Generates the HTML for the team leaderboard with TRANSLATED names.
    """
    if team_summary_df is None or team_summary_df.empty:
        return f"<p style='text-align:center; color:#6b7280; padding-top:20px;'>{t(lang, 'summary_empty')}</p>" # Assuming you have this key, or use hardcoded text

    # Normalize the current user's team name for comparison logic
    normalized_user_team = _normalize_team_name(team_name).lower()

    header = f"""
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>{t(lang, 'lbl_rank')}</th> <th>{t(lang, 'lbl_team')}</th> <th>{t(lang, 'lbl_best_acc')}</th> <th>Avg Score</th> 
                <th>Submissions</th>
            </tr>
        </thead>
        <tbody>
    """

    body = ""
    for index, row in team_summary_df.iterrows():
        # 1. Get English Name from Data
        raw_team_name = row['Team']
        
        # 2. Translate it for Display
        display_team_name = t_team(raw_team_name, lang)

        # 3. Logic Check (Use RAW English name for comparison)
        normalized_row_team = _normalize_team_name(raw_team_name).lower()
        is_user_team = normalized_row_team == normalized_user_team
        
        row_class = "class='user-row-highlight'" if is_user_team else ""
        
        body += f"""
        <tr {row_class}>
            <td>{index}</td>
            <td>{display_team_name}</td>
            <td>{(row['Best_Score'] * 100):.2f}%</td>
            <td>{(row['Avg_Score'] * 100):.2f}%</td>
            <td>{row['Submissions']}</td>
        </tr>
        """

    footer = "</tbody></table>"
    return header + body + footer
  

def _build_individual_html(individual_summary_df, username):
    """Generates the HTML for the individual leaderboard."""
    if individual_summary_df is None or individual_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>No individual submissions yet.</p>"

    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Engineer</th>
                <th>Best_Score</th>
                <th>Submissions</th>
            </tr>
        </thead>
        <tbody>
    """

    body = ""
    for index, row in individual_summary_df.iterrows():
        is_user = row["Engineer"] == username
        row_class = "class='user-row-highlight'" if is_user else ""
        body += f"""
        <tr {row_class}>
            <td>{index}</td>
            <td>{row['Engineer']}</td>
            <td>{(row['Best_Score'] * 100):.2f}%</td>
            <td>{row['Submissions']}</td>
        </tr>
        """

    footer = "</tbody></table>"
    return header + body + footer




# --- End Helper Functions ---

def generate_competitive_summary(leaderboard_df, team_name, username, last_submission_score, last_rank, submission_count, lang="en"):
    """
    Build summaries, HTML, and KPI card.
    
    Concurrency Note: Uses the team_name parameter directly for team highlighting,
    NOT os.environ, to prevent cross-user data leakage under concurrent requests.
    
    Returns (team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score).
    """
    team_summary_df = pd.DataFrame(columns=["Team", "Best_Score", "Avg_Score", "Submissions"])
    individual_summary_df = pd.DataFrame(columns=["Engineer", "Best_Score", "Submissions"])

    # 1. Handle Empty Leaderboard
    if leaderboard_df is None or leaderboard_df.empty or "accuracy" not in leaderboard_df.columns:
        return (
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Leaderboard empty.</p>",
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Leaderboard empty.</p>",
            # Pass lang to KPI builder for "Preview/N/A" text localization
            _build_kpi_card_html(0, 0, 0, 0, 0, is_preview=False, is_pending=False, local_test_accuracy=None, lang=lang), 
            0.0, 0, 0.0
        )

    # 2. Generate Team Summary
    if "Team" in leaderboard_df.columns:
        team_summary_df = (
            leaderboard_df.groupby("Team")["accuracy"]
            .agg(Best_Score="max", Avg_Score="mean", Submissions="count")
            .reset_index()
            .sort_values("Best_Score", ascending=False)
            .reset_index(drop=True)
        )
        team_summary_df.index = team_summary_df.index + 1

    # 3. Generate Individual Summary
    user_bests = leaderboard_df.groupby("username")["accuracy"].max()
    user_counts = leaderboard_df.groupby("username")["accuracy"].count()
    individual_summary_df = pd.DataFrame(
        {"Engineer": user_bests.index, "Best_Score": user_bests.values, "Submissions": user_counts.values}
    ).sort_values("Best_Score", ascending=False).reset_index(drop=True)
    individual_summary_df.index = individual_summary_df.index + 1

    # 4. Extract Stats for KPI Card
    new_rank = 0
    new_best_accuracy = 0.0
    this_submission_score = 0.0

    try:
        # Get all submissions for this user
        user_rows = leaderboard_df[leaderboard_df["username"] == username].copy()

        if not user_rows.empty:
            # Attempt robust timestamp parsing to find the absolute latest score
            if "timestamp" in user_rows.columns:
                parsed_ts = pd.to_datetime(user_rows["timestamp"], errors="coerce")

                if parsed_ts.notna().any():
                    # At least one valid timestamp → use parsed ordering
                    user_rows["__parsed_ts"] = parsed_ts
                    user_rows = user_rows.sort_values("__parsed_ts", ascending=False)
                    this_submission_score = float(user_rows.iloc[0]["accuracy"])
                else:
                    # All timestamps invalid → assume append order, take last as "latest"
                    this_submission_score = float(user_rows.iloc[-1]["accuracy"])
            else:
                # No timestamp column → fallback to last row
                this_submission_score = float(user_rows.iloc[-1]["accuracy"])

        # Get Rank & Best Accuracy from the pre-calculated summary
        my_rank_row = individual_summary_df[individual_summary_df["Engineer"] == username]
        if not my_rank_row.empty:
            new_rank = my_rank_row.index[0]
            new_best_accuracy = float(my_rank_row["Best_Score"].iloc[0])

    except Exception as e:
        _log(f"Latest submission score extraction failed: {e}")

    # 5. Generate HTML outputs
    team_html = _build_team_html(team_summary_df, team_name, lang=lang)
    individual_html = _build_individual_html(individual_summary_df, username)
    
    # Pass lang to KPI builder
    kpi_card_html = _build_kpi_card_html(
        new_score=this_submission_score,
        last_score=last_submission_score,
        new_rank=new_rank,
        last_rank=last_rank,
        submission_count=submission_count,
        is_preview=False,
        is_pending=False,
        local_test_accuracy=None,
        lang=lang
    )

    return team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score


def get_model_card(model_name, lang="en"):
    """Get localized model description."""
    if model_name not in MODEL_TYPES:
        return "No description available."
    # MODEL_TYPES now contains "desc_key" instead of raw text
    key = MODEL_TYPES[model_name]["desc_key"]
    return t(lang, key)

def compute_rank_settings(submission_count, current_model, current_complexity, current_feature_set, current_data_size, lang="en"):
    """Returns rank gating settings with localized messages."""
    
    if submission_count == 0:
        return {
            "rank_message": t(lang, 'rank_trainee'),
            "model_choices": ["The Balanced Generalist"],
            "model_value": "The Balanced Generalist",
            "model_interactive": False,
            "complexity_max": 3,
            "complexity_value": min(current_complexity, 3),
            "feature_set_choices": [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in FEATURE_SET_GROUP_1_VALS],
            "feature_set_value": FEATURE_SET_GROUP_1_VALS,
            "feature_set_interactive": False,
            "data_size_choices": ["Small (20%)"],
            "data_size_value": "Small (20%)",
            "data_size_interactive": False,
        }
    elif submission_count == 1:
        return {
            "rank_message": t(lang, 'rank_junior'),
            "model_choices": ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"],
            "model_value": current_model if current_model in ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"] else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 6,
            "complexity_value": min(current_complexity, 6),
            "feature_set_choices": [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in (FEATURE_SET_GROUP_1_VALS + FEATURE_SET_GROUP_2_VALS)],
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)"],
            "data_size_value": current_data_size if current_data_size in ["Small (20%)", "Medium (60%)"] else "Small (20%)",
            "data_size_interactive": True,
        }
    elif submission_count == 2:
        return {
            "rank_message": t(lang, 'rank_senior'),
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Deep Pattern-Finder",
            "model_interactive": True,
            "complexity_max": 8,
            "complexity_value": min(current_complexity, 8),
            "feature_set_choices": FEATURE_SET_ALL_OPTIONS,
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)",
            "data_size_interactive": True,
        }
    else:
        return {
            "rank_message": t(lang, 'rank_lead'),
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 10,
            "complexity_value": current_complexity,
            "feature_set_choices": FEATURE_SET_ALL_OPTIONS,
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)",
            "data_size_interactive": True,
        }

# Find components by name to yield updates
# --- Existing global component placeholders ---
submit_button = None
submission_feedback_display = None
team_leaderboard_display = None
individual_leaderboard_display = None
last_submission_score_state = None 
last_rank_state = None 
best_score_state = None
submission_count_state = None
rank_message_display = None
model_type_radio = None
complexity_slider = None
feature_set_checkbox = None
data_size_radio = None
attempts_tracker_display = None
team_name_state = None
# Login components
login_username = None
login_password = None
login_submit = None
login_error = None
# Add missing placeholders for auth states (FIX)
username_state = None
token_state = None
first_submission_score_state = None  # (already commented as "will be assigned globally")
# Add state placeholders for readiness gating and preview tracking
readiness_state = None
was_preview_state = None
kpi_meta_state = None
last_seen_ts_state = None  # Track last seen user timestamp from leaderboard


def get_or_assign_team(username, token=None):
    """
    Get the existing team for a user from the leaderboard, or assign a new random team.
    
    Queries the playground leaderboard to check if the user has prior submissions with
    a team assignment. If found, returns that team (most recent if multiple submissions).
    Otherwise assigns a random team. All team names are normalized for consistency.
    
    Args:
        username: str, the username to check for existing team
        token: str, optional authentication token for leaderboard fetch
    
    Returns:
        tuple: (team_name: str, is_new: bool)
            - team_name: The normalized team name (existing or newly assigned)
            - is_new: True if newly assigned, False if existing team recovered
    """
    try:
        # Query the leaderboard
        if playground is None:
            # Fallback to random assignment if playground not available
            print("Playground not available, assigning random team")
            new_team = _normalize_team_name(random.choice(TEAM_NAMES))
            return new_team, True
        
        # Use centralized helper for authenticated leaderboard fetch
        leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
        
        # Check if leaderboard has data and Team column
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            # Filter for this user's submissions
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            
            if not user_submissions.empty:
                # Sort by timestamp (most recent first) if timestamp column exists
                # Use contextlib.suppress for resilient timestamp parsing
                if "timestamp" in user_submissions.columns:
                    try:
                        # Attempt to coerce timestamp column to datetime and sort descending
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(user_submissions["timestamp"], errors='coerce')
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                        print(f"Sorted {len(user_submissions)} submissions by timestamp for {username}")
                    except Exception as ts_error:
                        # If timestamp parsing fails, continue with unsorted DataFrame
                        print(f"Warning: Could not sort by timestamp for {username}: {ts_error}")
                
                # Get the most recent team assignment (first row after sorting)
                existing_team = user_submissions.iloc[0]["Team"]
                
                # Check if team value is valid (not null/empty)
                if pd.notna(existing_team) and existing_team and str(existing_team).strip():
                    normalized_team = _normalize_team_name(existing_team)
                    print(f"Found existing team for {username}: {normalized_team}")
                    return normalized_team, False
        
        # No existing team found - assign random
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        print(f"Assigning new team to {username}: {new_team}")
        return new_team, True
        
    except Exception as e:
        # On any error, fall back to random assignment
        print(f"Error checking leaderboard for team: {e}")
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        print(f"Fallback: assigning random team to {username}: {new_team}")
        return new_team, True

def perform_inline_login(username_input, password_input):
    """
    Perform inline authentication and return credentials via gr.State updates.
    
    Concurrency Note: This function NO LONGER stores per-user credentials in
    os.environ to prevent cross-user data leakage. Authentication state is
    returned exclusively via gr.State updates (username_state, token_state,
    team_name_state). Password is never stored server-side.
    
    Args:
        username_input: str, the username entered by user
        password_input: str, the password entered by user
    
    Returns:
        dict: Gradio component updates for login UI elements and submit button
            - On success: hides login form, shows success message, enables submit
            - On failure: keeps login form visible, shows error with signup link
    """
    from aimodelshare.aws import get_aws_token
    
    # Validate inputs
    if not username_input or not username_input.strip():
        error_html = """
        <div style='background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:500;'>⚠️ Username is required</p>
        </div>
        """
        return {
            login_username: gr.update(),
            login_password: gr.update(),
            login_submit: gr.update(),
            login_error: gr.update(value=error_html, visible=True),
            submit_button: gr.update(),
            submission_feedback_display: gr.update(),
            team_name_state: gr.update(),
            username_state: gr.update(),
            token_state: gr.update()
        }
    
    if not password_input or not password_input.strip():
        error_html = """
        <div style='background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:500;'>⚠️ Password is required</p>
        </div>
        """
        return {
            login_username: gr.update(),
            login_password: gr.update(),
            login_submit: gr.update(),
            login_error: gr.update(value=error_html, visible=True),
            submit_button: gr.update(),
            submission_feedback_display: gr.update(),
            team_name_state: gr.update(),
            username_state: gr.update(),
            token_state: gr.update()
        }
    
    # Concurrency Note: get_aws_token() reads credentials from os.environ, which creates
    # a race condition in multi-threaded environments. We use _auth_lock to serialize
    # credential injection, preventing concurrent requests from seeing each other's
    # credentials. The password is immediately cleared after the auth attempt.
    # 
    # FUTURE: Ideally get_aws_token() would be refactored to accept credentials as
    # parameters instead of reading from os.environ. This lock is a workaround.
    username_clean = username_input.strip()
    
    # Attempt to get AWS token with serialized credential injection
    try:
        with _auth_lock:
            os.environ["username"] = username_clean
            os.environ["password"] = password_input.strip()  # Only for get_aws_token() call
            try:
                token = get_aws_token()
            finally:
                # SECURITY: Always clear credentials from environment, even on exception
                # Also clear stale env vars from previous implementations within the lock
                # to prevent any race conditions during cleanup
                os.environ.pop("password", None)
                os.environ.pop("username", None)
                os.environ.pop("AWS_TOKEN", None)
                os.environ.pop("TEAM_NAME", None)
        
        # Get or assign team for this user with explicit token (already normalized by get_or_assign_team)
        team_name, is_new_team = get_or_assign_team(username_clean, token=token)
        # Normalize team name before storing (defensive - already normalized by get_or_assign_team)
        team_name = _normalize_team_name(team_name)
        
        # Build success message based on whether team is new or existing
        if is_new_team:
            team_message = f"You have been assigned to a new team: <b>{team_name}</b> 🎉"
        else:
            team_message = f"Welcome back! You remain on team: <b>{team_name}</b> ✅"
        
        # Success: hide login form, show success message with team info, enable submit button
        success_html = f"""
        <div style='background:#f0fdf4; padding:16px; border-radius:8px; border-left:4px solid #16a34a; margin-top:12px;'>
            <p style='margin:0; color:#15803d; font-weight:600; font-size:1.1rem;'>✓ Signed in successfully!</p>
            <p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>
                {team_message}
            </p>
            <p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>
                Click "Build & Submit Model" again to publish your score.
            </p>
        </div>
        """
        return {
            login_username: gr.update(visible=False),
            login_password: gr.update(visible=False),
            login_submit: gr.update(visible=False),
            login_error: gr.update(value=success_html, visible=True),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            submission_feedback_display: gr.update(visible=False),
            team_name_state: gr.update(value=team_name),
            username_state: gr.update(value=username_clean),
            token_state: gr.update(value=token)
        }
        
    except Exception as e:
        # Note: Credentials are already cleaned up by the finally block in the try above.
        # The lock ensures no race condition during cleanup.
        
        # Authentication failed: show error with signup link
        error_html = f"""
        <div style='background:#fef2f2; padding:16px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:600; font-size:1.1rem;'>⚠️ Authentication failed</p>
            <p style='margin:8px 0; color:#7f1d1d; font-size:0.95rem;'>
                Could not verify your credentials. Please check your username and password.
            </p>
            <p style='margin:8px 0 0 0; color:#7f1d1d; font-size:0.95rem;'>
                <strong>New user?</strong> Create a free account at 
                <a href='https://www.modelshare.ai/login' target='_blank' 
                   style='color:#dc2626; text-decoration:underline;'>modelshare.ai/login</a>
            </p>
            <details style='margin-top:12px; font-size:0.85rem; color:#7f1d1d;'>
                <summary style='cursor:pointer;'>Technical details</summary>
                <pre style='margin-top:8px; padding:8px; background:#fee; border-radius:4px; overflow-x:auto;'>{str(e)}</pre>
            </details>
        </div>
        """
        return {
            login_username: gr.update(visible=True),
            login_password: gr.update(visible=True),
            login_submit: gr.update(visible=True),
            login_error: gr.update(value=error_html, visible=True),
            submit_button: gr.update(),
            submission_feedback_display: gr.update(),
            team_name_state: gr.update(),
            username_state: gr.update(),
            token_state: gr.update()
        }



# -------------------------------------------------------------------------
# Conclusion helpers (dark/light mode aware)
# -------------------------------------------------------------------------
def build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set, lang="en"):
    """
    Build the final conclusion HTML with performance summary.
    Colors are handled via CSS classes so that light/dark mode work correctly.
    """
    # 1. Calculate Tier Progress
    # Tiers: 0=Trainee, 1=Junior, 2=Senior, 3=Lead
    unlocked_tiers = min(3, max(0, submissions - 1))
    
    # Localized Tier Names (Add these keys to your TRANSLATIONS dict)
    tier_labels = [
        t(lang, "tier_trainee"), 
        t(lang, "tier_junior"), 
        t(lang, "tier_senior"), 
        t(lang, "tier_lead")
    ]
    
    # Build the visual "Trainee -> Junior -> ..." line
    reached = tier_labels[: unlocked_tiers + 1]
    tier_line_html = " → ".join([f"{label}{' ✅' if label in reached else ''}" for label in tier_labels])

    # 2. Calculate Improvement
    improvement = (best_score - first_score) if (first_score is not None and submissions > 1) else 0.0
    
    # 3. Check Strong Predictors
    strong_predictors = {"age", "length_of_stay", "priors_count", "age_cat"}
    strong_used = [f for f in feature_set if f in strong_predictors]
    strong_txt = ", ".join(strong_used) if strong_used else t(lang, "none_yet")

    # 4. Dynamic Tip (if few submissions)
    tip_html = ""
    if submissions < 2:
        tip_html = f"""
        <div class="final-conclusion-tip">
          <b>{t(lang, 'tip_label')}</b> {t(lang, 'concl_tip_body')}
        </div>
        """

    # 5. Attempt Cap Message (if limit reached)
    attempt_cap_html = ""
    if submissions >= ATTEMPT_LIMIT:
        attempt_cap_html = f"""
        <div class="final-conclusion-attempt-cap">
          <p style="margin:0;">
            <b>📊 {t(lang, 'limit_title')}:</b> {t(lang, 'limit_body').format(limit=ATTEMPT_LIMIT)}
          </p>
        </div>
        """

    # 6. Return Full HTML
    return f"""
    <div class="final-conclusion-root">
      <h1 class="final-conclusion-title">{t(lang, 'concl_title')}</h1>
      
      <div class="final-conclusion-card">
        <h2 class="final-conclusion-subtitle">{t(lang, 'concl_snapshot')}</h2>
        
        <ul class="final-conclusion-list">
          <li>🏁 <b>{t(lang, 'lbl_best_acc')}:</b> {(best_score * 100):.2f}%</li>
          <li>📊 <b>{t(lang, 'concl_rank_achieved')}:</b> {('#' + str(rank)) if rank > 0 else '—'}</li>
          <li>🔁 <b>{t(lang, 'concl_subs_made')}:</b> {submissions}{' / ' + str(ATTEMPT_LIMIT) if submissions >= ATTEMPT_LIMIT else ''}</li>
          <li>🧗 <b>{t(lang, 'concl_improvement')}:</b> {(improvement * 100):+.2f}</li>
          <li>🎖️ <b>{t(lang, 'concl_tier_prog')}:</b> {tier_line_html}</li>
          <li>🧪 <b>{t(lang, 'concl_strong_pred')}:</b> {len(strong_used)} ({strong_txt})</li>
        </ul>

        {tip_html}

        <div class="final-conclusion-ethics">
          <p style="margin:0;"><b>{t(lang, 'concl_eth_ref')}:</b> {t(lang, 'concl_eth_body')}</p>
        </div>

        {attempt_cap_html}

        <hr class="final-conclusion-divider" />

        <div class="final-conclusion-next">
          <h2>➡️ {t(lang, 'concl_next_title')}</h2>
          <p>{t(lang, 'concl_next_body')}</p>
          <h1 class="final-conclusion-scroll">{t(lang, 's6_scroll')}</h1>
        </div>
      </div>
    </div>
    """


def build_conclusion_from_state(best_score, submissions, rank, first_score, feature_set, lang="en"):
    return build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set, lang)
  
def create_model_building_game_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """
    Create (but do not launch) the model building game app.
    """
    start_background_init()

    # Add missing globals (FIX)
    global submit_button, submission_feedback_display, team_leaderboard_display
    global individual_leaderboard_display, last_submission_score_state, last_rank_state
    global best_score_state, submission_count_state, first_submission_score_state
    global rank_message_display, model_type_radio, complexity_slider
    global feature_set_checkbox, data_size_radio
    global login_username, login_password, login_submit, login_error
    global attempts_tracker_display, team_name_state
    global username_state, token_state  # <-- Added
    global readiness_state, was_preview_state, kpi_meta_state  # <-- Added for parameter shadowing guards
    global last_seen_ts_state  # <-- Added for timestamp tracking
    
    css = """
    /* ------------------------------
      Shared Design Tokens (local)
      ------------------------------ */

    /* We keep everything driven by Gradio theme vars:
      --body-background-fill, --body-text-color, --secondary-text-color,
      --border-color-primary, --block-background-fill, --color-accent,
      --shadow-drop, --prose-background-fill
    */

    :root {
        --slide-radius-md: 12px;
        --slide-radius-lg: 16px;
        --slide-radius-xl: 18px;
        --slide-spacing-lg: 24px;

        /* Local, non-brand tokens built *on top of* theme vars */
        --card-bg-soft: var(--block-background-fill);
        --card-bg-strong: var(--prose-background-fill, var(--block-background-fill));
        --card-border-subtle: var(--border-color-primary);
        --accent-strong: var(--color-accent);
        --text-main: var(--body-text-color);
        --text-muted: var(--secondary-text-color);
    }

    /* ------------------------------------------------------------------
      Base Layout Helpers
      ------------------------------------------------------------------ */

    .slide-content {
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Shared card-like panels used throughout slides */
    .panel-box {
        background: var(--card-bg-soft);
        padding: 20px;
        border-radius: var(--slide-radius-lg);
        border: 2px solid var(--card-border-subtle);
        margin-bottom: 18px;
        color: var(--text-main);
        box-shadow: var(--shadow-drop, 0 2px 4px rgba(0,0,0,0.04));
    }

    .leaderboard-box {
        background: var(--card-bg-soft);
        padding: 20px;
        border-radius: var(--slide-radius-lg);
        border: 1px solid var(--card-border-subtle);
        margin-top: 12px;
        color: var(--text-main);
    }

    /* For “explanatory UI” scaffolding */
    .mock-ui-box {
        background: var(--card-bg-strong);
        border: 2px solid var(--card-border-subtle);
        padding: 24px;
        border-radius: var(--slide-radius-lg);
        color: var(--text-main);
    }

    .mock-ui-inner {
        background: var(--block-background-fill);
        border: 1px solid var(--card-border-subtle);
        padding: 24px;
        border-radius: var(--slide-radius-md);
    }

    /* “Control box” inside the mock UI */
    .mock-ui-control-box {
        padding: 12px;
        background: var(--block-background-fill);
        border-radius: 8px;
        border: 1px solid var(--card-border-subtle);
    }

    /* Little radio / check icons */
    .mock-ui-radio-on {
        font-size: 1.5rem;
        vertical-align: middle;
        color: var(--accent-strong);
    }

    .mock-ui-radio-off {
        font-size: 1.5rem;
        vertical-align: middle;
        color: var(--text-muted);
    }

    .mock-ui-slider-text {
        font-size: 1.5rem;
        margin: 0;
        color: var(--accent-strong);
        letter-spacing: 4px;
    }

    .mock-ui-slider-bar {
        color: var(--text-muted);
    }

    /* Simple mock button representation */
    .mock-button {
        width: 100%;
        font-size: 1.25rem;
        font-weight: 600;
        padding: 16px 24px;
        background-color: var(--accent-strong);
        color: var(--body-background-fill);
        border: none;
        border-radius: 8px;
        cursor: not-allowed;
    }

    /* Step visuals on slides */
    .step-visual {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        align-items: center;
        margin: 24px 0;
        text-align: center;
        font-size: 1rem;
    }

    .step-visual-box {
        padding: 16px;
        background: var(--block-background-fill);   /* ✅ theme-aware */
        border-radius: 8px;
        border: 2px solid var(--border-color-primary);
        margin: 5px;
        color: var(--body-text-color);              /* optional, safe */
    }

    .step-visual-arrow {
        font-size: 2rem;
        margin: 5px;
        /* no explicit color – inherit from theme or override in dark mode */
    }

    /* ------------------------------------------------------------------
      KPI Card (score feedback)
      ------------------------------------------------------------------ */

    .kpi-card {
        background: var(--card-bg-strong);
        border: 2px solid var(--accent-strong);
        padding: 24px;
        border-radius: var(--slide-radius-lg);
        text-align: center;
        max-width: 600px;
        margin: auto;
        color: var(--text-main);
        box-shadow: var(--shadow-drop, 0 4px 6px -1px rgba(0,0,0,0.08));
        min-height: 200px; /* prevent layout shift */
    }

    .kpi-card-body {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        align-items: flex-end;
        margin-top: 24px;
    }

    .kpi-metric-box {
        min-width: 150px;
        margin: 10px;
    }

    .kpi-label {
        font-size: 1rem;
        color: var(--text-muted);
        margin: 0;
    }

    .kpi-score {
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.1;
        color: var(--accent-strong);
    }

    .kpi-subtext-muted {
        font-size: 1.2rem;
        font-weight: 500;
        color: var(--text-muted);
        margin: 0;
        padding-top: 8px;
    }

    /* Small variants to hint semantic state without hard-coded colors */
    .kpi-card--neutral {
        border-color: var(--card-border-subtle);
    }

    .kpi-card--subtle-accent {
        border-color: var(--accent-strong);
    }

    .kpi-score--muted {
        color: var(--text-muted);
    }

    /* ------------------------------------------------------------------
      Leaderboard Table + Placeholder
      ------------------------------------------------------------------ */

    .leaderboard-html-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        font-size: 1rem;
        color: var(--text-main);
        min-height: 300px; /* Stable height */
    }

    .leaderboard-html-table thead {
        background: var(--block-background-fill);
    }

    .leaderboard-html-table th {
        padding: 12px 16px;
        font-size: 0.9rem;
        color: var(--text-muted);
        font-weight: 500;
    }

    .leaderboard-html-table tbody tr {
        border-bottom: 1px solid var(--card-border-subtle);
    }

    .leaderboard-html-table td {
        padding: 12px 16px;
    }

    .leaderboard-html-table .user-row-highlight {
        background: rgba( var(--color-accent-rgb, 59,130,246), 0.1 );
        font-weight: 600;
        color: var(--accent-strong);
    }

    /* Static placeholder (no shimmer, no animation) */
    .lb-placeholder {
        min-height: 300px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: var(--block-background-fill);
        border: 1px solid var(--card-border-subtle);
        border-radius: 12px;
        padding: 40px 20px;
        text-align: center;
    }

    .lb-placeholder-title {
        font-size: 1.25rem;
        font-weight: 500;
        color: var(--text-muted);
        margin-bottom: 8px;
    }

    .lb-placeholder-sub {
        font-size: 1rem;
        color: var(--text-muted);
    }

    /* ------------------------------------------------------------------
      Processing / “Experiment running” status
      ------------------------------------------------------------------ */

    .processing-status {
        background: var(--block-background-fill);
        border: 2px solid var(--accent-strong);
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        box-shadow: var(--shadow-drop, 0 4px 6px rgba(0,0,0,0.12));
        animation: pulse-indigo 2s infinite;
        color: var(--text-main);
    }

    .processing-icon {
        font-size: 4rem;
        margin-bottom: 10px;
        display: block;
        animation: spin-slow 3s linear infinite;
    }

    .processing-text {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--accent-strong);
    }

    .processing-subtext {
        font-size: 1.1rem;
        color: var(--text-muted);
        margin-top: 8px;
    }

    /* Pulse & spin animations */
    @keyframes pulse-indigo {
        0%   { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
        70%  { box-shadow: 0 0 0 15px rgba(99, 102, 241, 0); }
        100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
    }

    @keyframes spin-slow {
        from { transform: rotate(0deg); }
        to   { transform: rotate(360deg); }
    }

    /* Conclusion arrow pulse */
    @keyframes pulseArrow {
        0%   { transform: scale(1);     opacity: 1; }
        50%  { transform: scale(1.08);  opacity: 0.85; }
        100% { transform: scale(1);     opacity: 1; }
    }

    @media (prefers-reduced-motion: reduce) {
        [style*='pulseArrow'] {
            animation: none !important;
        }
        .processing-status,
        .processing-icon {
            animation: none !important;
        }
    }

    /* ------------------------------------------------------------------
      Attempts Tracker + Init Banner + Alerts
      ------------------------------------------------------------------ */

    .init-banner {
        background: var(--card-bg-strong);
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 16px;
        border: 1px solid var(--card-border-subtle);
        color: var(--text-main);
    }

    .init-banner__text {
        margin: 0;
        font-weight: 500;
        color: var(--text-muted);
    }

    /* Attempts tracker shell */
    .attempts-tracker {
        text-align: center;
        padding: 8px;
        margin: 8px 0;
        background: var(--block-background-fill);
        border-radius: 8px;
        border: 1px solid var(--card-border-subtle);
    }

    .attempts-tracker__text {
        margin: 0;
        font-weight: 600;
        font-size: 1rem;
        color: var(--accent-strong);
    }

    /* Limit reached variant – we *still* stick to theme colors */
    .attempts-tracker--limit .attempts-tracker__text {
        color: var(--text-main);
    }

    /* Generic alert helpers used in inline login messages */
    .alert {
        padding: 12px 16px;
        border-radius: 8px;
        margin-top: 12px;
        text-align: left;
        font-size: 0.95rem;
    }

    .alert--error {
        border-left: 4px solid var(--accent-strong);
        background: var(--block-background-fill);
        color: var(--text-main);
    }

    .alert--success {
        border-left: 4px solid var(--accent-strong);
        background: var(--block-background-fill);
        color: var(--text-main);
    }

    .alert__title {
        margin: 0;
        font-weight: 600;
        color: var(--text-main);
    }

    .alert__body {
        margin: 8px 0 0 0;
        color: var(--text-muted);
    }

    /* ------------------------------------------------------------------
      Navigation Loading Overlay
      ------------------------------------------------------------------ */

    #nav-loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: color-mix(in srgb, var(--body-background-fill) 90%, transparent);
        z-index: 9999;
        display: none;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .nav-spinner {
        width: 50px;
        height: 50px;
        border: 5px solid var(--card-border-subtle);
        border-top: 5px solid var(--accent-strong);
        border-radius: 50%;
        animation: nav-spin 1s linear infinite;
        margin-bottom: 20px;
    }

    @keyframes nav-spin {
        0%   { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    #nav-loading-text {
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--accent-strong);
    }

    /* ------------------------------------------------------------------
      Utility: Image inversion for dark mode (if needed)
      ------------------------------------------------------------------ */

    .dark-invert-image {
        filter: invert(0);
    }

    @media (prefers-color-scheme: dark) {
        .dark-invert-image {
            filter: invert(1) hue-rotate(180deg);
        }
    }

    /* ------------------------------------------------------------------
      Dark Mode Specific Fine Tuning
      ------------------------------------------------------------------ */

    @media (prefers-color-scheme: dark) {
        .panel-box,
        .leaderboard-box,
        .mock-ui-box,
        .mock-ui-inner,
        .processing-status,
        .kpi-card {
            background: color-mix(in srgb, var(--block-background-fill) 85%, #000 15%);
            border-color: color-mix(in srgb, var(--card-border-subtle) 70%, var(--accent-strong) 30%);
        }

        .leaderboard-html-table thead {
            background: color-mix(in srgb, var(--block-background-fill) 75%, #000 25%);
        }

        .lb-placeholder {
            background: color-mix(in srgb, var(--block-background-fill) 75%, #000 25%);
        }

        #nav-loading-overlay {
            background: color-mix(in srgb, #000 70%, var(--body-background-fill) 30%);
        }
    }
    
    /* ---------- Conclusion Card Theme Tokens ---------- */

    /* Light theme defaults */
    :root,
    :root[data-theme="light"] {
        --conclusion-card-bg: #e0f2fe;          /* light sky */
        --conclusion-card-border: #0369a1;      /* sky-700 */
        --conclusion-card-fg: #0f172a;          /* slate-900 */

        --conclusion-tip-bg: #fef9c3;           /* amber-100 */
        --conclusion-tip-border: #f59e0b;       /* amber-500 */
        --conclusion-tip-fg: #713f12;           /* amber-900 */

        --conclusion-ethics-bg: #fef2f2;        /* red-50 */
        --conclusion-ethics-border: #ef4444;    /* red-500 */
        --conclusion-ethics-fg: #7f1d1d;        /* red-900 */

        --conclusion-attempt-bg: #fee2e2;       /* red-100 */
        --conclusion-attempt-border: #ef4444;   /* red-500 */
        --conclusion-attempt-fg: #7f1d1d;       /* red-900 */

        --conclusion-next-fg: #0f172a;          /* main text color */
    }

    /* Dark theme overrides – keep contrast high on dark background */
    [data-theme="dark"] {
        --conclusion-card-bg: #020617;          /* slate-950 */
        --conclusion-card-border: #38bdf8;      /* sky-400 */
        --conclusion-card-fg: #e5e7eb;          /* slate-200 */

        --conclusion-tip-bg: rgba(250, 204, 21, 0.08);   /* soft amber tint */
        --conclusion-tip-border: #facc15;                /* amber-400 */
        --conclusion-tip-fg: #facc15;

        --conclusion-ethics-bg: rgba(248, 113, 113, 0.10); /* soft red tint */
        --conclusion-ethics-border: #f97373;               /* red-ish */
        --conclusion-ethics-fg: #fecaca;

        --conclusion-attempt-bg: rgba(248, 113, 113, 0.16);
        --conclusion-attempt-border: #f97373;
        --conclusion-attempt-fg: #fee2e2;

        --conclusion-next-fg: #e5e7eb;
    }

    /* ---------- Conclusion Layout ---------- */

    .app-conclusion-wrapper {
        text-align: center;
    }

    .app-conclusion-title {
        font-size: 2.4rem;
        margin: 0;
    }

    .app-conclusion-card {
        margin-top: 24px;
        max-width: 950px;
        margin-left: auto;
        margin-right: auto;
        padding: 28px;
        border-radius: 18px;
        border-width: 3px;
        border-style: solid;
        background: var(--conclusion-card-bg);
        border-color: var(--conclusion-card-border);
        color: var(--conclusion-card-fg);
        box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
    }

    .app-conclusion-subtitle {
        margin-top: 0;
        font-size: 1.5rem;
    }

    .app-conclusion-metrics {
        list-style: none;
        padding: 0;
        font-size: 1.05rem;
        text-align: left;
        max-width: 640px;
        margin: 20px auto;
    }

    /* ---------- Generic panel helpers reused here ---------- */

    .app-panel-tip,
    .app-panel-critical,
    .app-panel-warning {
        padding: 16px;
        border-radius: 12px;
        border-left-width: 6px;
        border-left-style: solid;
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.4;
        margin-top: 16px;
    }

    .app-panel-title {
        margin: 0 0 4px 0;
        font-weight: 700;
    }

    .app-panel-body {
        margin: 0;
    }

    /* Specific variants */

    .app-conclusion-tip.app-panel-tip {
        background: var(--conclusion-tip-bg);
        border-left-color: var(--conclusion-tip-border);
        color: var(--conclusion-tip-fg);
    }

    .app-conclusion-ethics.app-panel-critical {
        background: var(--conclusion-ethics-bg);
        border-left-color: var(--conclusion-ethics-border);
        color: var(--conclusion-ethics-fg);
    }

    .app-conclusion-attempt-cap.app-panel-warning {
        background: var(--conclusion-attempt-bg);
        border-left-color: var(--conclusion-attempt-border);
        color: var(--conclusion-attempt-fg);
    }

    /* Divider + next section */

    .app-conclusion-divider {
        margin: 28px 0;
        border: 0;
        border-top: 2px solid rgba(148, 163, 184, 0.8); /* slate-400-ish */
    }

    .app-conclusion-next-title {
        margin: 0;
        color: var(--conclusion-next-fg);
    }

    .app-conclusion-next-body {
        font-size: 1rem;
        color: var(--conclusion-next-fg);
    }

    /* Arrow inherits the same color, keeps pulse animation defined earlier */
    .app-conclusion-arrow {
        margin: 12px 0;
        font-size: 3rem;
        animation: pulseArrow 2.5s infinite;
        color: var(--conclusion-next-fg);
    }

    /* ---------------------------------------------------- */
    /* Final Conclusion Slide (Light Mode Defaults)         */
    /* ---------------------------------------------------- */

    .final-conclusion-root {
        text-align: center;
        color: var(--body-text-color);
    }

    .final-conclusion-title {
        font-size: 2.4rem;
        margin: 0;
    }

    .final-conclusion-card {
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        padding: 28px;
        border-radius: 18px;
        border: 2px solid var(--border-color-primary);
        margin-top: 24px;
        max-width: 950px;
        margin-left: auto;
        margin-right: auto;
        box-shadow: var(--shadow-drop, 0 4px 10px rgba(15, 23, 42, 0.08));
    }

    .final-conclusion-subtitle {
        margin-top: 0;
        margin-bottom: 8px;
    }

    .final-conclusion-list {
        list-style: none;
        padding: 0;
        font-size: 1.05rem;
        text-align: left;
        max-width: 640px;
        margin: 20px auto;
    }

    .final-conclusion-list li {
        margin: 4px 0;
    }

    .final-conclusion-tip {
        margin-top: 16px;
        padding: 16px;
        border-radius: 12px;
        border-left: 6px solid var(--color-accent);
        background-color: color-mix(in srgb, var(--color-accent) 12%, transparent);
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.4;
    }

    .final-conclusion-ethics {
        margin-top: 16px;
        padding: 18px;
        border-radius: 12px;
        border-left: 6px solid #ef4444;
        background-color: color-mix(in srgb, #ef4444 10%, transparent);
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.4;
    }

    .final-conclusion-attempt-cap {
        margin-top: 16px;
        padding: 16px;
        border-radius: 12px;
        border-left: 6px solid #ef4444;
        background-color: color-mix(in srgb, #ef4444 16%, transparent);
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.4;
    }

    .final-conclusion-divider {
        margin: 28px 0;
        border: 0;
        border-top: 2px solid var(--border-color-primary);
    }

    .final-conclusion-next h2 {
        margin: 0;
    }

    .final-conclusion-next p {
        font-size: 1rem;
        margin-top: 4px;
        margin-bottom: 0;
    }

    .final-conclusion-scroll {
        margin: 12px 0 0 0;
        font-size: 3rem;
        animation: pulseArrow 2.5s infinite;
    }

    /* ---------------------------------------------------- */
    /* Dark Mode Overrides for Final Slide                  */
    /* ---------------------------------------------------- */

    @media (prefers-color-scheme: dark) {
        .final-conclusion-card {
            background-color: #0b1120;        /* deep slate */
            color: white;                     /* 100% contrast confidence */
            border-color: #38bdf8;
            box-shadow: none;
        }

        .final-conclusion-tip {
            background-color: rgba(56, 189, 248, 0.18);
        }

        .final-conclusion-ethics {
            background-color: rgba(248, 113, 113, 0.18);
        }

        .final-conclusion-attempt-cap {
            background-color: rgba(248, 113, 113, 0.26);
        }
    }
    /* ---------------------------------------------------- */
    /* Slide 3: INPUT → MODEL → OUTPUT flow (theme-aware)   */
    /* ---------------------------------------------------- */


    .model-flow {
        text-align: center;
        font-weight: 600;
        font-size: 1.2rem;
        margin: 20px 0;
        /* No explicit color – inherit from the card */
    }

    .model-flow-label {
        padding: 0 0.1rem;
        /* No explicit color – inherit */
    }

    .model-flow-arrow {
        margin: 0 0.35rem;
        font-size: 1.4rem;
        /* No explicit color – inherit */
    }

    @media (prefers-color-scheme: dark) {
        .model-flow {
            color: var(--body-text-color);
        }
        .model-flow-arrow {
            /* In dark mode, nudge arrows toward accent for contrast/confidence */
            color: color-mix(in srgb, var(--color-accent) 75%, var(--body-text-color) 25%);
        }
    }
    """


    # Define globals for yield
    global submit_button, submission_feedback_display, team_leaderboard_display
    # --- THIS IS THE FIXED LINE ---
    global individual_leaderboard_display, last_submission_score_state, last_rank_state, best_score_state, submission_count_state, first_submission_score_state
    # --- END OF FIX ---
    global rank_message_display, model_type_radio, complexity_slider
    global feature_set_checkbox, data_size_radio
    global login_username, login_password, login_submit, login_error
    global attempts_tracker_display, team_name_state

    with gr.Blocks(theme=gr.themes.Soft(primary_hue="indigo"), css=css) as demo:
# -----------------------------------------------------------------
        # 1. STATE DEFINITIONS (Must be first!)
        # -----------------------------------------------------------------
        lang_state = gr.State("en")
        
        # Authentication & User States
        username_state = gr.State(None)
        token_state = gr.State(None)
        team_name_state = gr.State(None)
        
        # Game Logic States
        last_submission_score_state = gr.State(0.0)
        last_rank_state = gr.State(0)
        best_score_state = gr.State(0.0)
        submission_count_state = gr.State(0)
        first_submission_score_state = gr.State(None)
        
        # Experiment Logic States (The ones causing your error)
        model_type_state = gr.State(DEFAULT_MODEL)
        complexity_state = gr.State(2)
        feature_set_state = gr.State(DEFAULT_FEATURE_SET) # <--- This fixes the NameError
        data_size_state = gr.State(DEFAULT_DATA_SIZE)
        
        # Control Flags
        readiness_state = gr.State(False)
        was_preview_state = gr.State(False)
        kpi_meta_state = gr.State({})
        last_seen_ts_state = gr.State(None)
        # Persistent top anchor for scroll-to-top navigation
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        
        # Navigation loading overlay with spinner and dynamic message
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        # Concurrency Note: Do NOT read per-user state from os.environ here.
        # Username and other per-user data are managed via gr.State objects
        # and populated during handle_load_with_session_auth.

        # Loading screen
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding:100px 0;'>
                    <h2 style='font-size:2rem; color:#6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )

        # ---------------------------------------------------------
        #  Step 6: Briefing Slideshow Definitions
        # ---------------------------------------------------------
        
        # Slide 1
        with gr.Column(visible=True, elem_id="slide-1") as briefing_slide_1:
            c_s1_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's1_title')}</h1>")
            c_s1_html = gr.HTML(_get_slide1_html("en"))
            briefing_1_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 2
        with gr.Column(visible=False, elem_id="slide-2") as briefing_slide_2:
            c_s2_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's2_title')}</h1>")
            c_s2_html = gr.HTML(_get_slide2_html("en"))
            with gr.Row():
                briefing_2_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_2_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 3
        with gr.Column(visible=False, elem_id="slide-3") as briefing_slide_3:
            c_s3_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's3_title')}</h1>")
            c_s3_html = gr.HTML(_get_slide3_html("en"))
            with gr.Row():
                briefing_3_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_3_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 4
        with gr.Column(visible=False, elem_id="slide-4") as briefing_slide_4:
            c_s4_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's4_title')}</h1>")
            c_s4_html = gr.HTML(_get_slide4_html("en"))
            with gr.Row():
                briefing_4_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_4_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 5
        with gr.Column(visible=False, elem_id="slide-5") as briefing_slide_5:
            c_s5_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's5_title')}</h1>")
            c_s5_html = gr.HTML(_get_slide5_html("en"))
            with gr.Row():
                briefing_5_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_5_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 6
        with gr.Column(visible=False, elem_id="slide-6") as briefing_slide_6:
            c_s6_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's6_title')}</h1>")
            c_s6_html = gr.HTML(_get_slide6_html("en"))
            with gr.Row():
                briefing_6_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_6_next = gr.Button(t('en', 'btn_next'), variant="primary", size="lg")

        # Slide 7
        with gr.Column(visible=False, elem_id="slide-7") as briefing_slide_7:
            c_s7_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 's7_title')}</h1>")
            c_s7_html = gr.HTML(_get_slide7_html("en"))
            with gr.Row():
                briefing_7_back = gr.Button(t('en', 'btn_back'), size="lg")
                briefing_7_next = gr.Button(t('en', 'btn_begin'), variant="primary", size="lg")

        # --- End Briefing Slideshow ---



        #  Step 7: Main Model Building Arena Interface
        # ---------------------------------------------------------
        
        with gr.Column(visible=False, elem_id="model-step") as model_building_step:
            c_app_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 'app_title')}</h1>")
            
            # Status panel for initialization progress - HIDDEN
            init_status_display = gr.HTML(value="", visible=False)
            
            # Banner for UI state
            init_banner = gr.HTML(
              value=(
                  "<div class='init-banner'>"
                  "<p class='init-banner__text'>"
                  "⏳ Initializing data & leaderboard… you can explore but must wait for readiness to submit."
                  "</p>"
                  "</div>"
              ),
              visible=True)

            # Note: State objects defined at top of function (Step 5) are available here.

            rank_message_display = gr.Markdown(t('en', 'rank_trainee'))

            with gr.Row():
                with gr.Column(scale=1):

                    model_type_radio = gr.Radio(
                        label=t('en', 'lbl_model'),
                        choices=list(MODEL_TYPES.keys()),
                        value=DEFAULT_MODEL,
                        interactive=False
                    )
                    # Note: Passing "en" to get_model_card ensures initial load is English
                    model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL, "en"))

                    gr.Markdown("---") # Separator

                    complexity_slider = gr.Slider(
                        label=t('en', 'lbl_complex'),
                        minimum=1, maximum=3, step=1, value=2,
                        info=t('en', 'info_complex')
                    )

                    gr.Markdown("---") # Separator

                    # --- CRITICAL FIX HERE ---
                    feature_set_checkbox = gr.CheckboxGroup(
                        label=t('en', 'lbl_feat'),
                        choices=FEATURE_SET_ALL_OPTIONS, # Uses tuples ("Label", "column_name")
                        value=DEFAULT_FEATURE_SET,       # Uses ["column_name", ...]
                        interactive=False,
                        info=t('en', 'info_feat')
                    )
                    # -------------------------

                    gr.Markdown("---") # Separator

                    data_size_radio = gr.Radio(
                        label=t('en', 'lbl_data'),
                        choices=list(DATA_SIZE_MAP.keys()),
                        value=DEFAULT_DATA_SIZE,
                        interactive=False
                    )

                    gr.Markdown("---") # Separator

                    # Attempt tracker display
                    attempts_tracker_display = gr.HTML(
                        value=_build_attempts_tracker_html(0),
                        visible=True
                    )

                    submit_button = gr.Button(
                        value=t('en', 'btn_submit'),
                        variant="primary",
                        size="lg"
                    )

                with gr.Column(scale=1):
                    with gr.Tabs():
                        with gr.TabItem(t('en', 'tab_team')):
                            team_leaderboard_display = gr.HTML(_build_skeleton_leaderboard(rows=6, is_team=True))
                        with gr.TabItem(t('en', 'tab_ind')):
                            individual_leaderboard_display = gr.HTML(_build_skeleton_leaderboard(rows=6, is_team=False))
                    
                    # KPI Card
                    submission_feedback_display = gr.HTML(
                        f"<p style='text-align:center; color:#6b7280; padding:20px 0;'>Submit your first model to get feedback!</p>"
                    )
                    
                    # Inline Login Components (initially hidden)
                    # Using a Group keeps the layout tidy if you toggle visibility
                    with gr.Group(visible=False) as login_group:
                        login_username = gr.Textbox(
                            label="Username",
                            placeholder="Enter your modelshare.ai username",
                            visible=False
                        )
                        login_password = gr.Textbox(
                            label="Password",
                            type="password",
                            placeholder="Enter your password",
                            visible=False
                        )
                        login_submit = gr.Button(
                            "Sign In & Submit",
                            variant="primary",
                            visible=False
                        )
                        login_error = gr.HTML(
                            value="",
                            visible=False
                        )

            step_2_next = gr.Button(t('en', 'btn_finish'), variant="secondary")
          
        # ---------------------------------------------------------
        #  Step 8: Conclusion Step
        # ---------------------------------------------------------
        
        with gr.Column(visible=False, elem_id="conclusion-step") as conclusion_step:
            # 1. Title (Must match variable c_concl_title used in update_language)
            c_concl_title = gr.Markdown(f"<h1 style='text-align:center;'>{t('en', 'concl_title')}</h1>")
            
            # 2. Final Score Display (Must match variable final_score_display)
            # Initially shows "Preparing..." text until logic replaces it
            final_score_display = gr.HTML(t('en', 'concl_prep'))
            
            # 3. Return Button (Must match variable btn_return used in update_language)
            # Note: We assign it to 'btn_return' for the updater, but we can also 
            # alias it as 'step_3_back' if your navigation logic uses that name.
            btn_return = gr.Button(t('en', 'btn_return'), size="lg")
            step_3_back = btn_return # Alias for navigation compatibility
        # ---------------------------------------------------------
        #  Language Update Logic (Fixed for Responsiveness)
        # ---------------------------------------------------------
        
        def update_language(request: gr.Request):
            """
            Updates all UI text based on ?lang= query param.
            Uses gr.update() to preserve event listeners.
            """
            params = request.query_params
            lang = params.get("lang", "en")
            # Fallback if lang code not found
            if lang not in TRANSLATIONS:
                lang = "en"
            
            # Short helper for cleaner code below
            def txt(k): 
                return t(lang, k)
            
            # Return list must match the order of 'update_targets' exactly
            return [
                # 0. State
                lang,
                
                # 1. Slide 1
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s1_title')}</h1>"),
                gr.update(value=_get_slide1_html(lang)),
                gr.update(value=txt('btn_next')),
                
                # 2. Slide 2
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s2_title')}</h1>"),
                gr.update(value=_get_slide2_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 3. Slide 3
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s3_title')}</h1>"),
                gr.update(value=_get_slide3_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 4. Slide 4
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s4_title')}</h1>"),
                gr.update(value=_get_slide4_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 5. Slide 5
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s5_title')}</h1>"),
                gr.update(value=_get_slide5_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 6. Slide 6
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s6_title')}</h1>"),
                gr.update(value=_get_slide6_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_next')),
                
                # 7. Slide 7
                gr.update(value=f"<h1 style='text-align:center;'>{txt('s7_title')}</h1>"),
                gr.update(value=_get_slide7_html(lang)),
                gr.update(value=txt('btn_back')),
                gr.update(value=txt('btn_begin')),
                
                # 8. Main App Interface
                gr.update(value=f"<h1 style='text-align:center;'>{txt('app_title')}</h1>"),
                gr.update(label=txt('lbl_model')),
                gr.update(label=txt('lbl_complex'), info=txt('info_complex')),
                gr.update(label=txt('lbl_feat'), info=txt('info_feat')),
                gr.update(label=txt('lbl_data')),
                gr.update(value=txt('btn_submit')),
                
                # 9. Conclusion
                gr.update(value=f"<h1 style='text-align:center;'>{txt('concl_title')}</h1>"),
                gr.update(value=txt('concl_prep')),
                gr.update(value=txt('btn_return'))
            ]
# ---------------------------------------------------------------------
        # NAVIGATION & WIRING LOGIC (Consolidated)
        # ---------------------------------------------------------------------
        
        # 1. Define all steps for visibility toggling
        all_steps_nav = [
            briefing_slide_1, briefing_slide_2, briefing_slide_3,
            briefing_slide_4, briefing_slide_5, briefing_slide_6, briefing_slide_7,
            model_building_step, conclusion_step, loading_screen
        ]

        # 2. Define Conclusion Finalizer (Must be defined before wiring)
        def finalize_and_show_conclusion(best_score, submissions, rank, first_score, feature_set, lang):
            """Build dynamic conclusion HTML and navigate to conclusion step."""
            html = build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set, lang)
            
            # Create list of updates for all steps (hide all except conclusion)
            updates = [gr.update(visible=True) if s == conclusion_step else gr.update(visible=False) for s in all_steps_nav]
            
            # Append the HTML update for the final score display
            return updates + [gr.update(value=html)]

        # 3. Define Navigation Creator (1-Argument Version)
        def create_nav(next_step):
            def navigate():
                # Return list of updates: Visible=True for next_step, False for others
                return [gr.update(visible=True) if s == next_step else gr.update(visible=False) for s in all_steps_nav]
            return navigate

        # 4. Define JS Helper
        def nav_js(target_id, msg):
            return f"""
            ()=>{{
              const overlay = document.getElementById('nav-loading-overlay');
              if(overlay) {{
                document.getElementById('nav-loading-text').textContent = '{msg}';
                overlay.style.display = 'flex';
                setTimeout(()=>{{ overlay.style.opacity = '1'; }}, 10);
              }}
              setTimeout(()=>{{
                  overlay.style.opacity = '0';
                  setTimeout(()=>{{ overlay.style.display = 'none'; }}, 300);
                  const anchor = document.getElementById('app_top_anchor');
                  if(anchor) anchor.scrollIntoView({{behavior:'smooth', block:'start'}});
              }}, 800);
            }}
            """

        # 5. Wire Navigation Buttons
        briefing_1_next.click(fn=create_nav(briefing_slide_2), outputs=all_steps_nav, js=nav_js("slide-2", "Loading..."))
        
        briefing_2_back.click(fn=create_nav(briefing_slide_1), outputs=all_steps_nav, js=nav_js("slide-1", "Back..."))
        briefing_2_next.click(fn=create_nav(briefing_slide_3), outputs=all_steps_nav, js=nav_js("slide-3", "Loading..."))
        
        briefing_3_back.click(fn=create_nav(briefing_slide_2), outputs=all_steps_nav, js=nav_js("slide-2", "Back..."))
        briefing_3_next.click(fn=create_nav(briefing_slide_4), outputs=all_steps_nav, js=nav_js("slide-4", "Loading..."))
        
        briefing_4_back.click(fn=create_nav(briefing_slide_3), outputs=all_steps_nav, js=nav_js("slide-3", "Back..."))
        briefing_4_next.click(fn=create_nav(briefing_slide_5), outputs=all_steps_nav, js=nav_js("slide-5", "Loading..."))
        
        briefing_5_back.click(fn=create_nav(briefing_slide_4), outputs=all_steps_nav, js=nav_js("slide-4", "Back..."))
        briefing_5_next.click(fn=create_nav(briefing_slide_6), outputs=all_steps_nav, js=nav_js("slide-6", "Loading..."))
        
        briefing_6_back.click(fn=create_nav(briefing_slide_5), outputs=all_steps_nav, js=nav_js("slide-5", "Back..."))
        briefing_6_next.click(fn=create_nav(briefing_slide_7), outputs=all_steps_nav, js=nav_js("slide-7", "Loading..."))
        
        briefing_7_back.click(fn=create_nav(briefing_slide_6), outputs=all_steps_nav, js=nav_js("slide-6", "Back..."))
        briefing_7_next.click(fn=create_nav(model_building_step), outputs=all_steps_nav, js=nav_js("model-step", "Entering Arena..."))
        
        # Conclusion Navigation
        step_2_next.click(
            fn=finalize_and_show_conclusion,
            inputs=[best_score_state, submission_count_state, last_rank_state, first_submission_score_state, feature_set_state, lang_state],
            outputs=all_steps_nav + [final_score_display],
            js=nav_js("conclusion-step", "Calculating...")
        )
        
        step_3_back.click(fn=create_nav(model_building_step), outputs=all_steps_nav, js=nav_js("model-step", "Returning..."))

# ---------------------------------------------------------------------
        # CORE EXPERIMENT LOGIC (The Missing Function)
        # ---------------------------------------------------------------------
        def run_experiment(
            model_name_key, complexity_level, feature_set, data_size_str,
            team_name, last_score, last_rank, submission_count, first_score, best_score,
            username, token, readiness, was_preview, lang,
            progress=gr.Progress()
        ):
            """
            Full experiment logic:
            1. Validates inputs
            2. Runs preview on warm dataset if not ready/logged in
            3. Trains full model on requested data size
            4. Submits to cloud (if logged in)
            5. Updates UI with results
            """
            # A. Validate & Setup
            if not model_name_key: model_name_key = DEFAULT_MODEL
            feature_set = feature_set or []
            complexity_level = safe_int(complexity_level, 2)
            
            # Define helper for localized status updates
            def status(step, title_en, sub_en):
                return f"""
                <div class='processing-status'>
                    <span class='processing-icon'>⚙️</span>
                    <div class='processing-text'>Step {step}/5: {title_en}</div>
                    <div class='processing-subtext'>{sub_en}</div>
                </div>
                """

            # B. Initial Feedback
            progress(0.1, desc="Initializing...")
            yield {
                submission_feedback_display: gr.update(value=status(1, "Initializing", "Preparing data ingredients..."), visible=True),
                submit_button: gr.update(value="⏳ Running...", interactive=False),
                login_error: gr.update(visible=False)
            }

            # C. Check Features
            numeric_cols = [f for f in feature_set if f in ALL_NUMERIC_COLS]
            categorical_cols = [f for f in feature_set if f in ALL_CATEGORICAL_COLS]
            
            if not numeric_cols and not categorical_cols:
                # Error state
                yield {
                    submission_feedback_display: gr.update(value="<p style='color:red; text-align:center;'>⚠️ Error: No features selected.</p>"),
                    submit_button: gr.update(value=t(lang, 'btn_submit'), interactive=True)
                }
                return

            # D. Determine if Preview or Full Run
            # Use warm mini if: Not logged in OR Playground not ready
            is_preview_run = (token is None) or (playground is None)
            
            # Select Data
            if is_preview_run:
                X_train_curr = X_TRAIN_WARM
                y_train_curr = Y_TRAIN_WARM
                # If warm data isn't ready yet, stop
                if X_train_curr is None:
                    yield { submission_feedback_display: gr.update(value="<p style='color:red;'>⚠️ Data not yet loaded. Please wait...</p>"), submit_button: gr.update(interactive=True) }
                    return
            else:
                # Full Run
                X_train_curr = X_TRAIN_SAMPLES_MAP.get(data_size_str, X_TRAIN_SAMPLES_MAP[DEFAULT_DATA_SIZE])
                y_train_curr = Y_TRAIN_SAMPLES_MAP.get(data_size_str, Y_TRAIN_SAMPLES_MAP[DEFAULT_DATA_SIZE])

            # E. Train Model
            progress(0.3, desc="Training...")
            yield { submission_feedback_display: gr.update(value=status(2, "Training", "Learning patterns from history...")) }

            # Build & Fit
            try:
                preprocessor, selected_cols = build_preprocessor(tuple(sorted(numeric_cols)), tuple(sorted(categorical_cols)))
                
                X_train_processed = preprocessor.fit_transform(X_train_curr[selected_cols])
                # Ensure dense if needed
                base_model = MODEL_TYPES[model_name_key]["model_builder"]()
                tuned_model = tune_model_complexity(base_model, complexity_level)
                
                if isinstance(tuned_model, (DecisionTreeClassifier, RandomForestClassifier)):
                    from scipy import sparse
                    if sparse.issparse(X_train_processed): X_train_processed = X_train_processed.toarray()
                
                tuned_model.fit(X_train_processed, y_train_curr)
            except Exception as e:
                print(f"Train Error: {e}")
                yield { submission_feedback_display: gr.update(value=f"<p style='color:red;'>Training Error: {e}</p>"), submit_button: gr.update(interactive=True) }
                return

            # F. Evaluate / Submit
            progress(0.6, desc="Evaluating...")
            
            # Preprocess Test Set
            try:
                X_test_processed = preprocessor.transform(X_TEST_RAW[selected_cols])
                if isinstance(tuned_model, (DecisionTreeClassifier, RandomForestClassifier)):
                    from scipy import sparse
                    if sparse.issparse(X_test_processed): X_test_processed = X_test_processed.toarray()
                
                predictions = tuned_model.predict(X_test_processed)
                from sklearn.metrics import accuracy_score
                local_score = accuracy_score(Y_TEST, predictions)
            except Exception as e:
                 print(f"Eval Error: {e}")
                 yield { submission_feedback_display: gr.update(value=f"<p style='color:red;'>Eval Error: {e}</p>"), submit_button: gr.update(interactive=True) }
                 return

            # Logic Branch: Preview vs Submit
            if is_preview_run:
                # --- PREVIEW MODE ---
                # Pass lang here
                preview_card = _build_kpi_card_html(local_score, 0, 0, 0, -1, is_preview=True, lang=lang)
                
                # Append Login Prompt if not logged in
                if token is None:
                    preview_card += build_login_prompt_html(lang)

                # Settings for next run (Rank calculation)
                # Preview doesn't increment submission count, so we pass current count
                settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str, lang)

                yield {
                    submission_feedback_display: gr.update(value=preview_card),
                    submit_button: gr.update(value=t(lang, 'btn_submit'), interactive=True),
                    login_username: gr.update(visible=True), login_password: gr.update(visible=True),
                    login_submit: gr.update(visible=True),
                    rank_message_display: gr.update(value=settings["rank_message"]),
                    # Update inputs based on rank
                    model_type_radio: gr.update(choices=settings["model_choices"], interactive=settings["model_interactive"]),
                    complexity_slider: gr.update(maximum=settings["complexity_max"]),
                    feature_set_checkbox: gr.update(choices=[f[0] for f in settings["feature_set_choices"]], interactive=settings["feature_set_interactive"]),
                    data_size_radio: gr.update(choices=settings["data_size_choices"], interactive=settings["data_size_interactive"]),
                    was_preview_state: True
                }
            
            else:
                # --- SUBMISSION MODE ---
                progress(0.8, desc="Submitting...")
                yield { submission_feedback_display: gr.update(value=status(3, "Submitting", "Sending results to leaderboard...")) }
                
                # Submit to Cloud
                try:
                    desc = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})"
                    playground.submit_model(
                        model=tuned_model, preprocessor=preprocessor, prediction_submission=predictions,
                        input_dict={'description': desc}, custom_metadata={'Team': team_name}, token=token
                    )
                except Exception as e:
                    print(f"Submission Warning: {e}") # Non-fatal if local score exists

                # Update Stats
                new_count = submission_count + 1
                new_first_score = first_score if first_score is not None else local_score
                
                # Generate Result Card (Pass lang)
                result_card = _build_kpi_card_html(
                    new_score=local_score, last_score=last_score, 
                    new_rank=0, last_rank=last_rank, # Rank would be updated by next fetch
                    submission_count=new_count, is_preview=False, lang=lang
                )
                
                # Check Limits
                btn_state = gr.update(value=t(lang, 'btn_submit'), interactive=True)
                if new_count >= ATTEMPT_LIMIT:
                    result_card += f"<div style='margin-top:15px; border:2px solid red; padding:10px; border-radius:8px; background:#fee;'><b>{t(lang, 'limit_title')}</b></div>"
                    btn_state = gr.update(value="🛑 Limit Reached", interactive=False)

                settings = compute_rank_settings(new_count, model_name_key, complexity_level, feature_set, data_size_str, lang)

                yield {
                    submission_feedback_display: gr.update(value=result_card),
                    submit_button: btn_state,
                    submission_count_state: new_count,
                    last_submission_score_state: local_score,
                    best_score_state: max(best_score, local_score),
                    first_submission_score_state: new_first_score,
                    # Update UI Permissions
                    rank_message_display: gr.update(value=settings["rank_message"]),
                    model_type_radio: gr.update(choices=settings["model_choices"], interactive=settings["model_interactive"]),
                    complexity_slider: gr.update(maximum=settings["complexity_max"]),
                    feature_set_checkbox: gr.update(choices=[f[0] for f in settings["feature_set_choices"]], interactive=settings["feature_set_interactive"]),
                    data_size_radio: gr.update(choices=settings["data_size_choices"], interactive=settings["data_size_interactive"]),
                    # Hide login
                    login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False)
                }
# --- Timer & Initialization Logic ---
        
        # 1. Define the Timer Component
        status_timer = gr.Timer(value=0.5, active=True)

        # 2. Define the Update Function
        def update_init_status():
            """
            Poll initialization status and update UI elements.
            Returns status HTML, banner visibility, submit button state, data size choices, and readiness_state.
            """
            status_html, ready = poll_init_status()
            
            # Update banner visibility - hide when ready
            banner_visible = not ready
            
            # Update submit button
            if ready:
                submit_label = "5. 🔬 Build & Submit Model"
                submit_interactive = True
            else:
                submit_label = "⏳ Waiting for data..."
                submit_interactive = False
            
            # Get available data sizes based on init progress
            available_sizes = get_available_data_sizes()
            
            # Stop timer once fully initialized (optional optimization)
            timer_active = not (ready and INIT_FLAGS.get("pre_samples_full", False))
            
            return (
                status_html,
                gr.update(visible=banner_visible),
                gr.update(value=submit_label, interactive=submit_interactive),
                gr.update(choices=available_sizes),
                timer_active,
                ready  # readiness_state
            )

        # 3. Wire the Tick Event
        status_timer.tick(
            fn=update_init_status,
            inputs=None,
            outputs=[init_status_display, init_banner, submit_button, data_size_radio, status_timer, readiness_state]
        )

        # Input Events
        model_type_radio.change(lambda m, l: get_model_card(m, l), inputs=[model_type_radio, lang_state], outputs=model_card_display)
        model_type_radio.change(lambda m: m or DEFAULT_MODEL, inputs=model_type_radio, outputs=model_type_state)
        complexity_slider.change(lambda v: v, inputs=complexity_slider, outputs=complexity_state)
        feature_set_checkbox.change(lambda v: v or [], inputs=feature_set_checkbox, outputs=feature_set_state)
        data_size_radio.change(lambda v: v or DEFAULT_DATA_SIZE, inputs=data_size_radio, outputs=data_size_state)
        
        # Login Logic
        login_submit.click(
            fn=perform_inline_login,
            inputs=[login_username, login_password],
            outputs=[login_username, login_password, login_submit, login_error, submit_button, submission_feedback_display, team_name_state, username_state, token_state]
        )

        # Submit Experiment Logic
        submit_button.click(
            fn=run_experiment,
            inputs=[
                model_type_state, complexity_state, feature_set_state, data_size_state,
                team_name_state, last_submission_score_state, last_rank_state,
                submission_count_state, first_submission_score_state, best_score_state,
                username_state, token_state, readiness_state, was_preview_state, lang_state
            ],
            outputs=[
                submission_feedback_display, team_leaderboard_display, individual_leaderboard_display,
                last_submission_score_state, last_rank_state, best_score_state,
                submission_count_state, first_submission_score_state,
                rank_message_display, model_type_radio, complexity_slider, feature_set_checkbox,
                data_size_radio, submit_button, login_username, login_password, login_submit,
                login_error, attempts_tracker_display, was_preview_state, kpi_meta_state, last_seen_ts_state
            ],
            js=nav_js("model-step", "Running Experiment..."),
            show_progress="full"
        )
        return demo  # <--- ADD THIS LINE HERE (Indent: 4 spaces)
# -------------------------------------------------------------------------
# 4. Convenience Launcher
# -------------------------------------------------------------------------

def launch_model_building_game_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    """
    Create and directly launch the Model Building Game app inline (e.g., in notebooks).
    """
    global playground, X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST
    if playground is None:
        try:
            playground = Competition(MY_PLAYGROUND_ID)
        except Exception as e:
            print(f"WARNING: Could not connect to playground: {e}")
            playground = None

    if X_TRAIN_RAW is None:
        X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_and_prep_data()

    demo = create_model_building_game_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

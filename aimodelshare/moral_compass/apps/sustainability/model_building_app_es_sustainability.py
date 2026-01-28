"""
Model Building Game - Aplicación Gradio para el reto de Sostenibilidad e IA.

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
# Configuration & Caching Infrastructure
# -------------------------------------------------------------------------


# -------------------------------------------------------------------------
# CACHE CONFIGURATION (Optimized: Thread-Safe SQLite)
# -------------------------------------------------------------------------
import sqlite3

CACHE_DB_FILE = "prediction_cache.sqlite"

def get_cached_prediction(key):
    """
    Lightning-fast lookup from SQLite database.
    THREAD-SAFE FIX: Opens a new connection for every lookup.
    """
    if not os.path.exists(CACHE_DB_FILE):
        return None

    try:
        with sqlite3.connect(CACHE_DB_FILE, timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cache WHERE key=?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"⚠️ DB READ ERROR: {e}", flush=True)
        return None

# -------------------------------------------------------------------------
# Lightweight Label Loader
# -------------------------------------------------------------------------
_Y_TEST = None
_Y_TEST_LOCK = threading.Lock()

def get_test_labels(csv_path: str = "datasets/recreated_wids_v2_ny_10k.csv") -> pd.Series:
    """Load test labels from CSV file for local accuracy computation."""
    df = pd.read_csv(csv_path)
    if df.shape[0] > 4000:
        df = df.sample(n=4000, random_state=42)
    
    all_numeric_cols = ["floor_area", "year_built", "ELEVATION", "heating_degree_days", 
                        "cooling_degree_days", "january_min_temp", "july_max_temp", 
                        "avg_temp", "april_avg_temp", "october_avg_temp"]
    all_categorical_cols = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
    feature_columns = all_numeric_cols + all_categorical_cols
    
    for col in feature_columns:
        if col not in df.columns:
            df[col] = np.nan
    
    y = df["high_energy_usage"].copy()
    _, _, _, y_test = train_test_split(df[feature_columns], y, test_size=0.25, random_state=42, stratify=y)
    return y_test

def _ensure_y_test_loaded():
    global _Y_TEST
    with _Y_TEST_LOCK:
        if _Y_TEST is None:
            _Y_TEST = get_test_labels()

LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

_cache_lock = threading.Lock()
_user_stats_lock = threading.Lock()
_auth_lock = threading.Lock()

_leaderboard_cache: Dict[str, Dict[str, Any]] = {
    "anon": {"data": None, "timestamp": 0.0},
    "auth": {"data": None, "timestamp": 0.0},
}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}

def _log(msg: str):
    if DEBUG_LOG:
        print(f"[ModelBuildingGame] {msg}")

def _retry_with_backoff(func, max_attempts=3, base_delay=0.5, description="operation"):
    last_exception = None
    delay = base_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts:
                time.sleep(delay)
                delay *= 2
    raise last_exception

def _normalize_team_name(name: str) -> str:
    if not name: return ""
    return " ".join(str(name).strip().split())

def _fetch_leaderboard(token: Optional[str]) -> Optional[pd.DataFrame]:
    cache_key = "auth" if token else "anon"
    now = time.time()
    with _cache_lock:
        cache_entry = _leaderboard_cache[cache_key]
        if cache_entry["data"] is not None and now - cache_entry["timestamp"] < LEADERBOARD_CACHE_SECONDS:
            return cache_entry["data"]

    try:
        playground_id = "https://bhtrtkrbf4.execute-api.us-east-1.amazonaws.com/prod/m"
        p = Competition(playground_id)
        df = _retry_with_backoff(lambda: p.get_leaderboard(token=token) if token else p.get_leaderboard())
    except Exception as e:
        _log(f"Leaderboard fetch failed: {e}")
        df = None

    with _cache_lock:
        _leaderboard_cache[cache_key]["data"] = df
        _leaderboard_cache[cache_key]["timestamp"] = time.time()
    return df

def _get_leaderboard_with_optional_token(playground_instance: Optional["Competition"], token: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Fetch fresh leaderboard with optional token authentication and retry logic."""
    if playground_instance is None:
        return None
    def _fetch():
        if token: return playground_instance.get_leaderboard(token=token)
        return playground_instance.get_leaderboard()
    try: return _retry_with_backoff(_fetch, description="leaderboard fetch")
    except Exception as e:
        _log(f"Leaderboard fetch failed after retries: {e}")
        return None

USER_STATS_TTL = int(os.environ.get("USER_STATS_TTL", "60"))

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

def get_or_assign_team(username: str, token: Optional[str] = None) -> Tuple[str, bool]:
    df = _fetch_leaderboard(token)
    if df is not None and not df.empty and "username" in df.columns:
        user_rows = df[df["username"] == username]
        if not user_rows.empty and "Team" in user_rows.columns:
            team = user_rows.iloc[0]["Team"]
            if pd.notna(team) and str(team).strip():
                return _normalize_team_name(team), False
    return _normalize_team_name(random.choice(TEAM_NAMES)), True

def _compute_user_stats(username: str, token: str) -> Dict[str, Any]:
    now = time.time()
    with _user_stats_lock:
        cached = _user_stats_cache.get(username)
        if cached and (now - cached.get("_ts", 0) < USER_STATS_TTL):
            return cached.copy()

    df = _fetch_leaderboard(token)
    team_name, _ = get_or_assign_team(username, token)
    stats = {"best_score": 0.0, "rank": 0, "team_name": team_name, "submission_count": 0, "last_score": 0.0, "_ts": time.time()}
    try:
        if df is not None and not df.empty:
            user_rows = df[df["username"] == username]
            if not user_rows.empty:
                stats["submission_count"] = len(user_rows)
                if "accuracy" in user_rows.columns:
                    stats["best_score"] = float(user_rows["accuracy"].max())
                    if "timestamp" in user_rows.columns:
                        try:
                            user_rows = user_rows.copy()
                            user_rows["timestamp"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
                            recent = user_rows.sort_values("timestamp", ascending=False).iloc[0]
                            stats["last_score"] = float(recent["accuracy"])
                        except: stats["last_score"] = stats["best_score"]
                    else: stats["last_score"] = stats["best_score"]
            
            if "accuracy" in df.columns:
                user_bests = df.groupby("username")["accuracy"].max().sort_values(ascending=False)
                try: stats["rank"] = int(user_bests.index.get_loc(username) + 1)
                except KeyError: stats["rank"] = 0
    except Exception as e:
        _log(f"Error computing stats for {username}: {e}")
    
    with _user_stats_lock:
        _user_stats_cache[username] = stats
    return stats

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

MY_PLAYGROUND_ID = "https://bhtrtkrbf4.execute-api.us-east-1.amazonaws.com/prod/m"
ATTEMPT_LIMIT = 10

MODEL_TYPES = {
    "The Balanced Generalist": {
        "model_builder": lambda: LogisticRegression(max_iter=500, random_state=42, class_weight="balanced"),
        "card_es": "### ⚖️ El Generalista Equilibrado\nUn modelo de **Regresión Logística** fiable y rápido. Funciona bien como punto de partida para identificar tendencias generales en el consumo energético sin complicar demasiado las predicciones."
    },
    "The Rule-Maker": {
        "model_builder": lambda: DecisionTreeClassifier(random_state=42, class_weight="balanced"),
        "card_es": "### 📐 El Creador de Reglas\nUn **Árbol de Decisión** que crea reglas lógicas (ej: 'si el edificio es de antes de 1950, entonces...'). Es muy transparente, pero puede ser demasiado rígido si los datos cambian mucho."
    },
    "The 'Nearest Neighbor'": {
        "model_builder": lambda: KNeighborsClassifier(),
        "card_es": "### 🫂 El 'Vecino más Cercano'\nEste modelo (**KNN**) busca edificios similares en el pasado para predecir el futuro. Es excelente para captar comportamientos locales, aunque requiere que los edificios sean realmente comparables."
    },
    "The Deep Pattern-Finder": {
        "model_builder": lambda: RandomForestClassifier(random_state=42, class_weight="balanced"),
        "card_es": "### 🌲 El Buscador de Patrones Profundo\nUn **Random Forest** que combina cientos de árboles para encontrar patrones sutiles. Es el más potente para detectar ineficiencias energéticas complejas, pero cuidado con el sobreajuste."
    }
}

MODEL_DISPLAY_MAP = {
    "The Balanced Generalist": "El Generalista Equilibrado",
    "The Rule-Maker": "El Creador de Reglas",
    "The 'Nearest Neighbor'": "El 'Vecino más Cercano'",
    "The Deep Pattern-Finder": "El Buscador de Patrones Profundos"
}
MODEL_RADIO_CHOICES = [(label, key) for key, label in MODEL_DISPLAY_MAP.items()]
DEFAULT_MODEL = "The Balanced Generalist"

TEAM_NAMES = [
    "The Climate Guardians", "United Eco-Architects", "The Energy Detectives",
    "The Sustainability League", "Green Future Engineers", "Zero Carbon Avengers"
]

# Feature Groups for Progressive Unlocking
FEATURE_SET_GROUP_1_VALS = ["floor_area", "year_built", "building_class", "facility_type"]
FEATURE_SET_GROUP_2_VALS = ["State_Factor", "Year_Factor", "ELEVATION"]

FEATURE_SET_ALL_OPTIONS = [
    ("Superficie (pies cuadrados)", "floor_area"),
    ("Año de construcción", "year_built"),
    ("Clase de edificio", "building_class"),
    ("Tipo de instalación", "facility_type"),
    ("Zona geográfica (State Factor)", "State_Factor"),
    ("Año del registro (Year Factor)", "Year_Factor"),
    ("Elevación", "ELEVATION"),
    ("Días de calefacción", "heating_degree_days"),
    ("Días de refrigeración", "cooling_degree_days"),
    ("Temp. media anual", "avg_temp"),
    ("Temp. mínima de enero", "january_min_temp"),
    ("Temp. máxima de julio", "july_max_temp"),
    ("Temp. media de abril", "april_avg_temp"),
    ("Temp. media de octubre", "october_avg_temp"),
]

DATA_SIZE_DB_MAP = {
    "Pequeño (20%)": "Small (20%)",
    "Medio (60%)": "Medium (60%)",
    "Grande (80%)": "Large (80%)",
    "Completo (100%)": "Full (100%)"
}

DATA_SIZE_MAP = {
    "Small (20%)": 0.2,
    "Medium (60%)": 0.6,
    "Large (80%)": 0.8,
    "Full (100%)": 1.0
}
DATA_SIZE_DISPLAY_MAP = {
    "Small (20%)": "Pequeño (20%)",
    "Medium (60%)": "Medio (60%)",
    "Large (80%)": "Grande (80%)",
    "Full (100%)": "Completo (100%)"
}
DATA_SIZE_RADIO_CHOICES = [(label, key) for key, label in DATA_SIZE_DISPLAY_MAP.items()]
DEFAULT_DATA_SIZE = "Pequeño (20%)"

TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Climate Guardians": "The Climate Guardians",
        "United Eco-Architects": "United Eco-Architects",
        "The Energy Detectives": "The Energy Detectives",
        "The Sustainability League": "The Sustainability League",
        "Green Future Engineers": "Green Future Engineers",
        "Zero Carbon Avengers": "Zero Carbon Avengers"
    },
    "es": {
        "The Climate Guardians": "Los Guardianes del Clima",
        "United Eco-Architects": "Eco-Arquitectos Unidos",
        "The Energy Detectives": "Detectives de la Energía",
        "The Sustainability League": "La Liga de la Sostenibilidad",
        "Green Future Engineers": "Ingenieros del Futuro Verde",
        "Zero Carbon Avengers": "Vengadores del Carbono Cero"
    }
}
UI_TEAM_LANG = "es"

# -------------------------------------------------------------------------
# UI Helpers
# -------------------------------------------------------------------------

def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count, is_preview=False, is_pending=False, local_test_accuracy=None):
    diff = new_score - last_score
    diff_color = "#10b981" if diff >= 0 else "#ef4444"
    diff_symbol = "+" if diff >= 0 else ""
    
    status_tag = ""
    if is_preview: status_tag = "<span class='kpi-tag preview'>VISTA PREVIA</span>"
    elif is_pending: status_tag = "<span class='kpi-tag pending'>PROCESANDO...</span>"
    
    rank_html = f"#{new_rank}" if new_rank > 0 else "—"
    
    return f"""
    <div class='kpi-card {"preview-mode" if is_preview else ""}'>
        <div class='kpi-header'>
            <h2 class='kpi-title'>{'Puntuación de Vista Previa' if is_preview else 'Resultado del Experimento'}</h2>
            {status_tag}
        </div>
        <div class='kpi-card-body'>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>Precisión</p>
                <p class='kpi-score'>{(new_score*100):.2f}%</p>
                <p class='kpi-diff' style='color:{diff_color}'>{diff_symbol}{(diff*100):.2f}% vs anterior</p>
            </div>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>Posición Global</p>
                <p class='kpi-score'>{rank_html}</p>
                <p class='kpi-diff'>basado en el mejor histórico</p>
            </div>
        </div>
    </div>
    """

def _build_attempts_tracker_html(count, limit=10):
    color = "#ef4444" if count >= limit else "#0369a1"
    icon = "🛑" if count >= limit else "📊"
    label = f"Intentos usados: {count}/{limit}"
    return f"<div style='text-align:center; padding:8px; margin:8px 0; background:#f0f9ff; border-radius:8px; border:1px solid #bae6fd;'><p style='margin:0; color:{color}; font-weight:600; font-size:1rem;'>{icon} {label}</p></div>"

def _build_skeleton_leaderboard(rows=5, is_team=False):
    header = "Equipos" if is_team else "Arquitectos"
    items = "".join([f"<div class='skeleton-row'></div>" for _ in range(rows)])
    return f"<div class='skeleton-container'><h3>Cargando {header}...</h3>{items}</div>"

def _build_team_html(team_summary_df, team_name):
    if team_summary_df is None or team_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Aún no hay envíos de equipos.</p>"
    
    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Posición</th>
                <th>Equipo</th>
                <th>Mejor Puntuación</th>
                <th>Puntaje Promedio</th>
                <th>Envíos</th>
            </tr>
        </thead>
        <tbody>
    """
    body = ""
    for index, row in team_summary_df.iterrows():
        is_user_team = _normalize_team_name(row["Team"]).lower() == _normalize_team_name(team_name).lower()
        row_class = "class='user-row-highlight'" if is_user_team else ""
        body += f"<tr {row_class}><td>{index}</td><td>{row['Team']}</td><td>{(row['Best_Score']*100):.2f}%</td><td>{(row['Avg_Score']*100):.2f}%</td><td>{row['Submissions']}</td></tr>"
    return header + body + "</tbody></table>"

def _build_individual_html(individual_summary_df, username):
    if individual_summary_df is None or individual_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Aún no hay envíos individuales.</p>"
    
    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Posición</th>
                <th>Arquitecto</th>
                <th>Mejor Puntuación</th>
                <th>Envíos</th>
            </tr>
        </thead>
        <tbody>
    """
    body = ""
    for index, row in individual_summary_df.iterrows():
        is_user = row["Engineer"] == username
        row_class = "class='user-row-highlight'" if is_user else ""
        body += f"<tr {row_class}><td>{index}</td><td>{row['Engineer']}</td><td>{(row['Best_Score']*100):.2f}%</td><td>{row['Submissions']}</td></tr>"
    return header + body + "</tbody></table>"

def compute_rank_settings(count, model, complexity, features, size):
    def get_choices_for_rank(rank_level):
        if rank_level == 0: return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in ["floor_area", "year_built", "building_class", "facility_type"]]
        if rank_level == 1: return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in ["floor_area", "year_built", "building_class", "facility_type", "State_Factor", "Year_Factor", "ELEVATION"]]
        return FEATURE_SET_ALL_OPTIONS

    if count == 0:
        return {
            "rank_message": "# 🧑‍🎓 Rango: Practicante\n<p style='font-size:24px; line-height:1.4;'>Para tu primer envío, simplemente haz clic en el botón '🔬 Construir y Enviar Modelo' abajo.</p>",
            "model_choices": [MODEL_RADIO_CHOICES[0]], "model_value": "The Balanced Generalist", "model_interactive": False,
            "complexity_max": 3, "complexity_value": min(complexity, 3),
            "feature_set_choices": get_choices_for_rank(0), "feature_set_value": ["floor_area", "year_built", "building_class", "facility_type"], "feature_set_interactive": False,
            "data_size_choices": [DATA_SIZE_RADIO_CHOICES[0]], "data_size_value": "Small (20%)", "data_size_interactive": False
        }
    elif count == 1:
        return {
            "rank_message": "# 🎉 ¡Subiste de Rango! Arquitecto Junior\n<p style='font-size:24px; line-height:1.4;'>¡Se han desbloqueado nuevos modelos, tamaños de datos e ingredientes!</p>",
            "model_choices": MODEL_RADIO_CHOICES[:3], "model_value": model if model in ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"] else "The Balanced Generalist", "model_interactive": True,
            "complexity_max": 6, "complexity_value": min(complexity, 6),
            "feature_set_choices": get_choices_for_rank(1), "feature_set_value": features, "feature_set_interactive": True,
            "data_size_choices": DATA_SIZE_RADIO_CHOICES[:2], "data_size_value": size if size in ["Small (20%)", "Medium (60%)"] else "Small (20%)", "data_size_interactive": True
        }
    elif count == 2:
        return {
            "rank_message": "# 🌟 ¡Subiste de Rango! Arquitecto Senior\n<p style='font-size:24px; line-height:1.4;'>¡Ingredientes de datos más potentes desbloqueados! Los predictores más fuertes ahora están disponibles.</p>",
            "model_choices": MODEL_RADIO_CHOICES, "model_value": model if model in MODEL_TYPES else "The Deep Pattern-Finder", "model_interactive": True,
            "complexity_max": 8, "complexity_value": min(complexity, 8),
            "feature_set_choices": get_choices_for_rank(2), "feature_set_value": features, "feature_set_interactive": True,
            "data_size_choices": DATA_SIZE_RADIO_CHOICES, "data_size_value": size if any(key == size for _, key in DATA_SIZE_RADIO_CHOICES) else "Small (20%)", "data_size_interactive": True
        }
    else:
        return {
            "rank_message": "# 👑 Rango: Arquitecto Jefe\n<p style='font-size:24px; line-height:1.4;'>Todas las herramientas desbloqueadas — ¡optimiza libremente!</p>",
            "model_choices": MODEL_RADIO_CHOICES, "model_value": model if model in MODEL_TYPES else "The Balanced Generalist", "model_interactive": True,
            "complexity_max": 10, "complexity_value": complexity,
            "feature_set_choices": get_choices_for_rank(3), "feature_set_value": features, "feature_set_interactive": True,
            "data_size_choices": DATA_SIZE_RADIO_CHOICES, "data_size_value": size if any(key == size for _, key in DATA_SIZE_RADIO_CHOICES) else "Small (20%)", "data_size_interactive": True
        }

# Component Placeholders
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
login_username = None
login_password = None
login_submit = None
login_error = None
username_state = None
token_state = None
first_submission_score_state = None
readiness_state = None
was_preview_state = None
kpi_meta_state = None
last_seen_ts_state = None

# -------------------------------------------------------------------------
# 2. Data & Backend Utilities
# -------------------------------------------------------------------------

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


# Team name translation helpers for UI display (Catalan)
def translate_team_name_for_display(team_en: str, lang: str = "ca") -> str:
    """
    Translate a canonical English team name to the specified language for UI display.
    Fallback to English if translation not found.
    
    Internal logic always uses canonical English names. This is only for UI display.
    """
    if lang not in TEAM_NAME_TRANSLATIONS:
        lang = "en"
    return TEAM_NAME_TRANSLATIONS[lang].get(team_en, team_en)


def translate_team_name_to_english(display_name: str, lang: str = "ca") -> str:
    """
    Reverse lookup: given a localized team name, return the canonical English name.
    Returns the original display_name if not found.
    
    For future use if user input needs to be normalized back to English.
    """
    if lang not in TEAM_NAME_TRANSLATIONS:
        return display_name  # Already English or unknown
    
    translations = TEAM_NAME_TRANSLATIONS[lang]
    for english_name, localized_name in translations.items():
        if localized_name == display_name:
            return english_name
    return display_name


def _format_leaderboard_for_display(df: Optional[pd.DataFrame], lang: str = "ca") -> Optional[pd.DataFrame]:
    """
    Create a copy of the leaderboard DataFrame with team names translated for display.
    Does not mutate the original DataFrame.
    
    For potential future use when displaying full leaderboard.
    Internal logic should always use the original DataFrame with English team names.
    """
    if df is None:
        return None
    
    if df.empty or "Team" not in df.columns:
        return df.copy()
    
    df_display = df.copy()
    df_display["Team"] = df_display["Team"].apply(lambda t: translate_team_name_for_display(t, lang))
    return df_display


def _build_skeleton_leaderboard(rows=6, is_team=True, submit_button_label="5. 🔬 Construir y enviar el modelo"):
    context_label = "Equipo" if is_team else "Individual"
    return f"""
    <div class='lb-placeholder' aria-live='polite'>
        <div class='lb-placeholder-title'>{context_label} · Clasificación pendiente</div>
        <div class='lb-placeholder-sub'>
            <p style='margin:0 0 6px 0;'>¡Envía tu primer modelo para desbloquear la clasificación!</p>
            <p style='margin:0;'><strong>Haz clic en «{submit_button_label}» (abajo a la izquierda)</strong> para comenzar!</p>
        </div>
    </div>
    """
# --- FIX APPLIED HERE ---
def build_login_prompt_html():
    """
    Generate HTML for the login prompt text *only*.
    The styled preview card will be prepended to this.
    """
    return f"""
    <h2 style='color: #111827; margin-top:20px; border-top: 2px solid #e5e7eb; padding-top: 20px;'>🔐 Inicia sesión para enviar y clasificarte</h2>
    <div style='margin-top:16px; text-align:left; font-size:1rem; line-height:1.6; color:#374151;'>
        <p style='margin:12px 0;'>
            This is a preview run only. Sign in to publish your score to the live leaderboard, 
            earn promotions, and contribute team points.
        </p>
        <p style='margin:12px 0;'>
            <strong>New user?</strong> Create a free account at 
            <a href='https://www.modelshare.ai/login' target='_blank' 
                style='color:#4f46e5; text-decoration:underline;'>modelshare.ai/login</a>
        </p>
    </div>
    """
# --- END OF FIX ---

def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count, is_preview=False, is_pending=False, local_test_accuracy=None):
    """Generates the HTML for the KPI feedback card. Supports preview mode label and pending state."""

    # Handle pending state - show processing message with provisional diff
    if is_pending:
        title = "⏳ Procesando el envío"
        acc_color = "#3b82f6"  # Blue
        acc_text = f"{(local_test_accuracy * 100):.2f}%" if local_test_accuracy is not None else "N/A"
        
        # Compute provisional diff between local (new) and last score
        if local_test_accuracy is not None and last_score is not None and last_score > 0:
            score_diff = local_test_accuracy - last_score
            if abs(score_diff) < 0.0001:
                acc_diff_html = "<p style='font-size: 1.5rem; font-weight: 600; color: #6b7280; margin:0;'>Sin cambios (↔) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Actualización de la clasificación pendiente...</p>"
            elif score_diff > 0:
                acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #16a34a; margin:0;'>+{(score_diff * 100):.2f} (⬆️) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Actualización de la clasificación pendiente...</p>"
            else:
                acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #ef4444; margin:0;'>{(score_diff * 100):.2f} (⬇️) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Actualización de la clasificación pendiente...</p>"
        else:
            # No last score available - just show pending message
            acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Pending leaderboard update...</p>"
        
        border_color = acc_color
        rank_color = "#6b7280"  # Gray
        rank_text = "Pendiente"
        rank_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0;'>Calculando la posición...</p>"
        
    # Handle preview mode - Styled to match "success" card
    elif is_preview:
        title = "🔬 Prueba de vista previa finalizada!"
        acc_color = "#16a34a"  # Green (like success)
        acc_text = f"{(new_score * 100):.2f}%" if new_score > 0 else "N/A"
        acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>(Solo vista previa - no se ha enviado)</p>" # Neutral color
        border_color = acc_color # Green border
        rank_color = "#3b82f6" # Blue (like rank)
        rank_text = "N/A" # Placeholder
        rank_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0;'>Sin posición (vista previa)</p>" # Neutral color
    
    # 1. Handle First Submission
    elif submission_count == 0:
        title = "🎉 ¡Primer modelo enviado!"
        acc_color = "#16a34a" # green
        acc_text = f"{(new_score * 100):.2f}%"
        acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>(¡Tu primera puntuación!)</p>"

        rank_color = "#3b82f6" # blue
        rank_text = f"#{new_rank}"
        rank_diff_html = "<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>¡¡Ya estás en la tabla!!</p>"
        border_color = acc_color

    else:
        # 2. Handle Score Changes
        score_diff = new_score - last_score
        if abs(score_diff) < 0.0001:
            title = "✅ Envío completado!"
            acc_color = "#6b7280" # gray
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>Sin cambios (↔)</p>"
            border_color = acc_color
        elif score_diff > 0:
            title = "✅ Envío completado!"
            acc_color = "#16a34a" # green
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>+{(score_diff * 100):.2f} (⬆️)</p>"
            border_color = acc_color
        else:
            title = "📉 La puntuación ha bajado"
            acc_color = "#ef4444" # red
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>{(score_diff * 100):.2f} (⬇️)</p>"
            border_color = acc_color

        # 3. Handle Rank Changes
        rank_diff = last_rank - new_rank
        rank_color = "#3b82f6" # blue
        rank_text = f"#{new_rank}"
        if last_rank == 0: # Handle first rank
             rank_diff_html = "<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>¡¡Ya estás en la tabla!!</p>"
        elif rank_diff > 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #16a34a; margin:0;'>🚀 ¡Has subido {rank_diff} posición/es!</p>"
        elif rank_diff < 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #ef4444; margin:0;'>🔻 Has bajado {abs(rank_diff)} posición/es!</p>"
        else:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {rank_color}; margin:0;'>Mantienes tu posición (↔)</p>"

    return f"""
    <div class='kpi-card' style='border-color: {border_color};'>
        <h2 style='color: var(--body-text-color); margin-top:0;'>{title}</h2>
        <div class='kpi-card-body'>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>Nueva precisión</p>
                <p class='kpi-score' style='color: {acc_color};'>{acc_text}</p>
                {acc_diff_html}
            </div>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>Tu posición</p>
                <p class='kpi-score' style='color: {rank_color};'>{rank_text}</p>
                {rank_diff_html}
            </div>
        </div>
    </div>
    """

def _build_team_html(team_summary_df, team_name):
    """
    Generates the HTML for the team leaderboard.
    
    Uses normalized, case-insensitive comparison to highlight the user's team row,
    ensuring reliable highlighting even with whitespace or casing variations.
    
    Team names are translated to Catalan for display only. Internal comparisons
    use the unmodified English team names from the DataFrame.
    """
    if team_summary_df is None or team_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Todavía no hay envíos por equipos.</p>"

    # Normalize the current user's team name for comparison (using English names)
    normalized_user_team = _normalize_team_name(team_name).lower()

    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Posición</th>
                <th>Equipo</th>
                <th>Mejor Puntuación</th>
                <th>Medio</th>
                <th>Envíos</th>
            </tr>
        </thead>
        <tbody>
    """

    body = ""
    for index, row in team_summary_df.iterrows():
        # Normalize the row's team name and compare case-insensitively (using English names)
        normalized_row_team = _normalize_team_name(row["Team"]).lower()
        is_user_team = normalized_row_team == normalized_user_team
        row_class = "class='user-row-highlight'" if is_user_team else ""
        
        # Translate team name to Catalan for display only
        display_team_name = translate_team_name_for_display(row["Team"], UI_TEAM_LANG)
        
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
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Todavía no hay envíos individuales.</p>"

    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Posición</th>
                <th>Ingeniero/a</th>
                <th>Mejor Puntuación</th>
                <th>Envíos</th>
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


def generate_competitive_summary(leaderboard_df, team_name, username, last_submission_score, last_rank, submission_count):
    """
    Build summaries, HTML, and KPI card.
    
    Concurrency Note: Uses the team_name parameter directly for team highlighting,
    NOT os.environ, to prevent cross-user data leakage under concurrent requests.
    
    Returns (team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score).
    """
    team_summary_df = pd.DataFrame(columns=["Team", "Best_Score", "Avg_Score", "Submissions"])
    individual_summary_df = pd.DataFrame(columns=["Engineer", "Best_Score", "Submissions"])

    if leaderboard_df is None or leaderboard_df.empty or "accuracy" not in leaderboard_df.columns:
        return (
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>La clasificación está vacía.</p>",
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>La clasificación está vacía.</p>",
            _build_kpi_card_html(0, 0, 0, 0, 0, is_preview=False, is_pending=False, local_test_accuracy=None), 
            0.0, 0, 0.0
        )

    # Team summary
    if "Team" in leaderboard_df.columns:
        team_summary_df = (
            leaderboard_df.groupby("Team")["accuracy"]
            .agg(Best_Score="max", Avg_Score="mean", Submissions="count")
            .reset_index()
            .sort_values("Best_Score", ascending=False)
            .reset_index(drop=True)
        )
        team_summary_df.index = team_summary_df.index + 1

    # Individual summary
    user_bests = leaderboard_df.groupby("username")["accuracy"].max()
    user_counts = leaderboard_df.groupby("username")["accuracy"].count()
    individual_summary_df = pd.DataFrame(
        {"Engineer": user_bests.index, "Best_Score": user_bests.values, "Submissions": user_counts.values}
    ).sort_values("Best_Score", ascending=False).reset_index(drop=True)
    individual_summary_df.index = individual_summary_df.index + 1

    # Get stats for KPI card
    new_rank = 0
    new_best_accuracy = 0.0
    this_submission_score = 0.0

    try:
        # All submissions for this user
        user_rows = leaderboard_df[leaderboard_df["username"] == username].copy()

        if not user_rows.empty:
            # Attempt robust timestamp parsing
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

        # Rank & best accuracy (unchanged logic, but make sure we use the same best row)
        my_rank_row = None
        # Build individual summary before this block (already done above)
        my_rank_row = individual_summary_df[individual_summary_df["Engineer"] == username]
        if not my_rank_row.empty:
            new_rank = my_rank_row.index[0]
            new_best_accuracy = float(my_rank_row["Best_Score"].iloc[0])

    except Exception as e:
        _log(f"Latest submission score extraction failed: {e}")

    # Generate HTML outputs
    # Concurrency Note: Use team_name parameter directly, not os.environ
    team_html = _build_team_html(team_summary_df, team_name)
    individual_html = _build_individual_html(individual_summary_df, username)
    kpi_card_html = _build_kpi_card_html(
        this_submission_score, last_submission_score, new_rank, last_rank, submission_count,
        is_preview=False, is_pending=False, local_test_accuracy=None
    )

    return team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score


def get_model_card(model_name):
    return MODEL_TYPES.get(model_name, {}).get("card_es", "Descripción no disponible.")

def compute_rank_settings(
    submission_count,
    current_model,
    current_complexity,
    current_feature_set,
    current_data_size
):
    """
    Returns rank gating settings (updated for 1–10 complexity scale).
    Adapted for Spanish UI: Returns Tuple choices [(Display, Value)]
    """

    # Helper to generate feature choices
    def get_choices_for_rank(rank):
        if rank == 0: # Trainee
            return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in FEATURE_SET_GROUP_1_VALS]
        if rank == 1: # Junior
            return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in (FEATURE_SET_GROUP_1_VALS + FEATURE_SET_GROUP_2_VALS)]
        return FEATURE_SET_ALL_OPTIONS # Senior+

    # Helper to generate Model Radio Tuples [(Spanish, English)]
    def get_model_tuples(available_english_keys):
        return [(MODEL_DISPLAY_MAP[k], k) for k in available_english_keys if k in MODEL_DISPLAY_MAP]

    # Rank 0: Trainee
    if submission_count == 0:
        avail_keys = ["The Balanced Generalist"]
        return {
            "rank_message": "# 🧑‍🎓 Rango: Practicante de Sostenibilidad\n<p style='font-size:24px; line-height:1.4;'>¡Bienvenido/a a bordo! Para tu primer envío, simplemente haz clic en el botón grande '🔬 Construir y enviar el modelo' abajo para establecer tu primera puntuación.</p>",
            "model_choices": get_model_tuples(avail_keys),
            "model_value": "The Balanced Generalist",
            "model_interactive": False,
            "complexity_max": 3,
            "complexity_value": min(current_complexity, 3),
            "feature_set_choices": get_choices_for_rank(0),
            "feature_set_value": FEATURE_SET_GROUP_1_VALS,
            "feature_set_interactive": False,
            "data_size_choices": ["Pequeño (20%)"],
            "data_size_value": "Pequeño (20%)",
            "data_size_interactive": False,
        }
        
    # Rank 1: Junior
    elif submission_count == 1:
        avail_keys = ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"]
        
        return {
            "rank_message": "# 🎉 ¡Subiste de rango! Arquitecto Junior\n<p style='font-size:24px; line-height:1.4;'>¡Se han desbloqueado nuevos modelos, tamaños de datos y variables! Ahora puedes explorar más allá de los datos básicos del edificio.</p>",
            "model_choices": get_model_tuples(avail_keys),
            "model_value": current_model if current_model in avail_keys else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 6,
            "complexity_value": min(current_complexity, 6),
            "feature_set_choices": get_choices_for_rank(1),
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Pequeño (20%)", "Medio (60%)"],
            "data_size_value": current_data_size if current_data_size in ["Pequeño (20%)", "Medio (60%)"] else "Pequeño (20%)",
            "data_size_interactive": True,
        }

    # Rank 2: Senior
    elif submission_count == 2:
        avail_keys = list(MODEL_TYPES.keys()) # All models
        
        return {
            "rank_message": "# 🌟 ¡Subiste de rango! Arquitecto Sénior\n<p style='font-size:24px; line-height:1.4;'>¡Variables meteorológicas y geográficas desbloqueadas! Ahora puedes analizar el impacto del clima exterior en la eficiencia del edificio.</p>",
            "model_choices": get_model_tuples(avail_keys),
            "model_value": current_model if current_model in avail_keys else "The Deep Pattern-Finder",
            "model_interactive": True,
            "complexity_max": 8,
            "complexity_value": min(current_complexity, 8),
            "feature_set_choices": get_choices_for_rank(2),
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Pequeño (20%)", "Medio (60%)", "Grande (80%)", "Completo (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_DB_MAP else "Pequeño (20%)",
            "data_size_interactive": True,
        }
        
    # Rank 3+: Lead
    else:
        avail_keys = list(MODEL_TYPES.keys()) # All models

        return {
            "rank_message": "# 👑 Rango: Arquitecto Principal\n<p style='font-size:24px; line-height:1.4;'>¡Todas las herramientas desbloqueadas! Tienes acceso total a la potencia de cálculo y a todo el historial de datos climáticos.</p>",
            "model_choices": get_model_tuples(avail_keys),
            "model_value": current_model if current_model in avail_keys else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 10,
            "complexity_value": current_complexity,
            "feature_set_choices": get_choices_for_rank(3),
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Pequeño (20%)", "Medio (60%)", "Grande (80%)", "Completo (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_DB_MAP else "Pequeño (20%)",
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
    from aimodelshare.aws import get_aws_token
    if not username_input or not username_input.strip():
        error_html = "<div class='alert alert--error'><p class='alert__title'>⚠️ El usuario es obligatorio</p></div>"
        return {login_error: gr.update(value=error_html, visible=True)}
    if not password_input or not password_input.strip():
        error_html = "<div class='alert alert--error'><p class='alert__title'>⚠️ La contraseña es obligatoria</p></div>"
        return {login_error: gr.update(value=error_html, visible=True)}
    
    username_clean = username_input.strip()
    try:
        with _auth_lock:
            os.environ["username"] = username_clean
            os.environ["password"] = password_input.strip()
            token = get_aws_token()
            os.environ.pop("password", None)
            os.environ.pop("username", None)
        
        team_name, is_new = get_or_assign_team(username_clean, token=token)
        display_team = translate_team_name_for_display(team_name, UI_TEAM_LANG)
        team_msg = f"¡Te hemos asignado a un nuevo equipo: <b>{display_team}</b>! 🎉" if is_new else f"¡Hola de nuevo! Sigues en el equipo: <b>{display_team}</b> ✅"
        
        success_html = f"""
        <div class='alert alert--success'>
            <p class='alert__title'>✓ ¡Sesión iniciada correctamente!</p>
            <p class='alert__body'>{team_msg}<br>Haz clic en "Construir y enviar modelo" de nuevo para guardar tu puntuación.</p>
        </div>
        """
        return {
            login_username: gr.update(visible=False), login_password: gr.update(visible=False),
            login_submit: gr.update(visible=False), login_error: gr.update(value=success_html, visible=True),
            submit_button: gr.update(value="🔬 Construir y enviar modelo", interactive=True),
            team_name_state: team_name, username_state: username_clean, token_state: token
        }
    except Exception as e:
        error_html = f"<div class='alert alert--error'><p class='alert__title'>⚠️ Error de autenticación</p><p class='alert__body'>{str(e)}</p></div>"
        return {login_error: gr.update(value=error_html, visible=True)}

def run_experiment(model_name_key, complexity, features, size_str, team, last_score, last_rank, count, first_score, best_score, username=None, token=None, progress=gr.Progress()):
    def get_status_html(step, title, sub):
        return f"<div class='processing-status'><span class='processing-icon'>⚙️</span><div class='processing-text'>Paso {step}/5: {title}</div><div class='processing-subtext'>{sub}</div></div>"
    
    yield {submit_button: gr.update(value="⏳ Experimento en curso...", interactive=False), submission_feedback_display: gr.update(value=get_status_html(1, "Inicializando", "Preparando variables de datos..."), visible=True)}
    
    _ensure_y_test_loaded()
    sanitized = sorted([str(f[1] if isinstance(f, tuple) else f) for f in (features or [])])
    cache_key = f"{model_name_key}|{safe_int(complexity, 2)}|{DATA_SIZE_DB_MAP.get(size_str, 'Small (20%)')}|{','.join(sanitized)}"
    
    yield {submission_feedback_display: gr.update(value=get_status_html(2, "Cargando predicciones", "⚡ Recuperando resultados precomputados..."))}
    cached = get_cached_prediction(cache_key)
    if not cached:
        error_html = "<div class='alert alert--error'><p class='alert__title'>⚠️ Configuración no encontrada</p><p class='alert__body'>Esta combinación no está en nuestra base de datos precomputada. Por favor, ajusta los parámetros.</p></div>"
        yield {submission_feedback_display: gr.update(value=error_html), submit_button: gr.update(value="🔬 Construir y enviar modelo", interactive=True)}
        return

    predictions = np.array([int(c) for c in cached], dtype=np.uint8)
    from sklearn.metrics import accuracy_score
    this_acc = accuracy_score(_Y_TEST, predictions)

    if token is None:
        card = _build_kpi_card_html(this_acc, 0, 0, 0, -1, is_preview=True)
        login_prompt = """
        <div style='margin-top:20px; border-top:2px solid var(--border-color-primary); padding-top:20px;'>
            <h2 style='margin:0;'>🔐 Inicia sesión para guardar tu puntuación</h2>
            <p>Este es un modelo de prueba. Inicia sesión para subir al ranking y ganar puntos para tu equipo.</p>
        </div>
        """
        yield {
            submission_feedback_display: gr.update(value=f"{card}{login_prompt}"),
            login_username: gr.update(visible=True), login_password: gr.update(visible=True), login_submit: gr.update(visible=True),
            submit_button: gr.update(value="Inicio de sesión necesario", interactive=False),
            was_preview_state: True
        }
        return

    if count >= ATTEMPT_LIMIT:
        yield {submit_button: gr.update(value="🛑 Límite alcanzado", interactive=False)}
        return

    yield {submission_feedback_display: gr.update(value=get_status_html(3, "Enviando", "Enviando modelo al servidor..."))}
    def _submit():
        return playground.submit_model(model=None, preprocessor=None, prediction_submission=predictions.tolist(), input_dict={'description': f"{model_name_key} (Cplx:{complexity} Size:{size_str})"}, custom_metadata={'Team': team}, token=token, return_metrics=["accuracy"])
    
    try:
        res = _retry_with_backoff(_submit)
        server_acc = float(res[2].get("accuracy", this_acc)) if res and len(res)==3 else this_acc
    except:
        server_acc = this_acc

    new_count = count + 1
    new_first = server_acc if count == 0 else (first_score or server_acc)
    
    baseline_df = _get_leaderboard_with_optional_token(playground, token)
    sim_df = pd.concat([baseline_df, pd.DataFrame([{"username": username, "accuracy": server_acc, "Team": team, "timestamp": pd.Timestamp.now()}])]) if baseline_df is not None else pd.DataFrame([{"username": username, "accuracy": server_acc, "Team": team, "timestamp": pd.Timestamp.now()}])
    
    t_html, i_html, _, new_best, new_rank, _ = generate_competitive_summary(sim_df, team, username, last_score, last_rank, count)
    card = _build_kpi_card_html(server_acc, last_score, new_rank, last_rank, count)
    
    if new_count >= ATTEMPT_LIMIT:
        card += f"<div class='alert alert--error'><p class='alert__title'>🛑 Límite alcanzado ({ATTEMPT_LIMIT}/{ATTEMPT_LIMIT})</p></div>"
    
    settings = compute_rank_settings(new_count, model_name_key, complexity, features, size_str)
    yield {
        submission_feedback_display: gr.update(value=card), team_leaderboard_display: t_html, individual_leaderboard_display: i_html,
        last_submission_score_state: server_acc, best_score_state: new_best, submission_count_state: new_count, first_submission_score_state: new_first, last_rank_state: new_rank,
        rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"] and (new_count < ATTEMPT_LIMIT)),
        complexity_slider: gr.update(maximum=settings["complexity_max"], value=settings["complexity_value"], interactive=(new_count < ATTEMPT_LIMIT)),
        feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"] and (new_count < ATTEMPT_LIMIT)),
        data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"] and (new_count < ATTEMPT_LIMIT)),
        submit_button: gr.update(value="🛑 Límite alcanzado" if new_count >= ATTEMPT_LIMIT else "🔬 Construir y enviar modelo", interactive=(new_count < ATTEMPT_LIMIT)),
        attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(new_count))
    }


def on_initial_load(username, token=None, team_name=""):
    _ensure_y_test_loaded()
    initial_ui = compute_rank_settings(0, DEFAULT_MODEL, 2, ["floor_area", "year_built", "building_class", "facility_type"], DEFAULT_DATA_SIZE)
    display_team = translate_team_name_for_display(team_name, UI_TEAM_LANG) if team_name else "tu equipo"
    
    welcome_html = f"""
    <div style='text-align:center; padding: 30px 20px;'>
        <div style='font-size: 3rem; margin-bottom: 10px;'>👋</div>
        <h3 style='margin: 0 0 8px 0; color: #111827; font-size: 1.5rem;'>¡Bienvenido al equipo <b>{display_team}</b>!</h3>
        <p style='font-size: 1.1rem; color: #4b5563; margin: 0 0 20px 0;'>Tu equipo necesita tu ayuda para mejorar la IA.</p>
        <div style='background:#eff6ff; padding:16px; border-radius:12px; border:2px solid #bfdbfe; display:inline-block;'>
            <p style='margin:0; color:#1e40af; font-weight:bold; font-size:1.1rem;'>👈 Haz clic en 'Construir y enviar modelo' para comenzar!</p>
        </div>
    </div>
    """
    
    try:
        df = _fetch_leaderboard(token)
        if df is not None and username in df["username"].values:
            t_html, i_html, _, _, _, _ = generate_competitive_summary(df, team_name, username, 0, 0, -1)
        else:
            t_html, i_html = welcome_html, "<p style='text-align:center; color:#6b7280; padding-top:40px;'>¡Envía tu modelo para ver tu posición!</p>"
    except:
        t_html, i_html = welcome_html, ""

    return (get_model_card(DEFAULT_MODEL), t_html, i_html, initial_ui["rank_message"],
            gr.update(choices=initial_ui["model_choices"], value=initial_ui["model_value"], interactive=initial_ui["model_interactive"]),
            gr.update(minimum=1, maximum=initial_ui["complexity_max"], value=initial_ui["complexity_value"]),
            gr.update(choices=initial_ui["feature_set_choices"], value=initial_ui["feature_set_value"], interactive=initial_ui["feature_set_interactive"]),
            gr.update(choices=initial_ui["data_size_choices"], value=initial_ui["data_size_value"], interactive=initial_ui["data_size_interactive"]))


# -------------------------------------------------------------------------
# Conclusion helpers (dark/light mode aware)
# -------------------------------------------------------------------------
def build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set):
    tier_names = ["En prácticas", "Júnior", "Sénior", "Principal"]
    tier = tier_names[min(3, max(0, submissions - 1))]
    improvement = (best_score - first_score) if (first_score is not None and submissions > 1) else 0.0
    strong_preds = {"avg_temp", "heating_degree_days", "cooling_degree_days", "january_min_temp"}
    used_strong = [f for f in feature_set if f in strong_preds]

    return f"""
    <div class="final-conclusion-root">
      <h1 class="final-conclusion-title">🎉 Fase de ingeniería completada</h1>
      <div class="final-conclusion-card">
        <h2 class="final-conclusion-subtitle">Resumen de tu rendimiento</h2>
        <ul class="final-conclusion-list">
          <li>🏁 <b>Mejor precisión:</b> {(best_score * 100):.2f}%</li>
          <li>📊 <b>Posición alcanzada:</b> {('#' + str(rank)) if rank > 0 else '—'}</li>
          <li>🔁 <b>Envíos en esta sesión:</b> {submissions}</li>
          <li>🧗 <b>Mejora respecto a la primera puntuación:</b> {(improvement * 100):+.2f}%</li>
          <li>🎖️ <b>Rango alcanzado:</b> {tier}</li>
          <li>🧪 <b>Variables climáticas utilizadas:</b> {len(used_strong)}</li>
        </ul>
        <div class="final-conclusion-ethics">
          <p><b>Reflexión ética:</b> Los edificios representan el 40% de las emisiones. Tu IA ayuda a priorizar rehabilitaciones donde más se necesitan.</p>
        </div>
        <div class="final-conclusion-next">
          <h1 class="final-instruction">👇 Continúa con la siguiente actividad abajo</h1>
        </div>
      </div>
    </div>
    """



def build_conclusion_from_state(best_score, submissions, rank, first_score, feature_set):
    return build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set)
def create_model_building_game_es_sustainability_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    # Initialize playground connection
    global playground
    if playground is None:
        try:
            playground = Competition(MY_PLAYGROUND_ID)
            print("✅ Playground connected", flush=True)
        except Exception as e:
            print(f"⚠️ Playground connection failed: {e}", flush=True)

    global submit_button, submission_feedback_display, team_leaderboard_display, individual_leaderboard_display
    global last_submission_score_state, last_rank_state, best_score_state, submission_count_state, first_submission_score_state
    global rank_message_display, model_type_radio, complexity_slider, feature_set_checkbox, data_size_radio
    global login_username, login_password, login_submit, login_error, attempts_tracker_display, team_name_state
    global username_state, token_state, readiness_state, was_preview_state, kpi_meta_state, last_seen_ts_state
    
    css = """
    .processing-status { background: var(--block-background-fill); border: 2px solid var(--accent-strong); border-radius: 16px; padding: 30px; text-align: center; animation: pulse-indigo 2s infinite; }
    .processing-icon { font-size: 4rem; margin-bottom: 10px; display: block; animation: spin-slow 3s linear infinite; }
    @keyframes pulse-indigo { 0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); } 70% { box-shadow: 0 0 0 15px rgba(99, 102, 241, 0); } 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); } }
    @keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .kpi-card { background: var(--block-background-fill); border: 2px solid var(--accent-strong); padding: 24px; border-radius: 16px; text-align: center; margin-bottom: 16px; }
    .kpi-score { font-size: 3rem; font-weight: 700; color: var(--accent-strong); }
    .panel-box { background: var(--block-background-fill); padding: 20px; border-radius: 12px; border: 1px solid var(--border-color-primary); margin-bottom: 18px; }
    .alert { padding: 12px; border-radius: 8px; border-left: 4px solid #ef4444; background: #fee2e2; color: #991b1b; }
    .alert--success { border-left-color: #10b981; background: #ecfdf5; color: #065f46; }
    
    #nav-loading-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(255, 255, 255, 0.8); display: none; flex-direction: column;
        align-items: center; justify-content: center; z-index: 9999; opacity: 0; transition: opacity 0.3s;
    }
    .nav-spinner {
        width: 50px; height: 50px; border: 5px solid #e5e7eb; border-top: 5px solid #4f46e5;
        border-radius: 50%; animation: spin 1s linear infinite;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    
    .lb-placeholder { text-align: center; padding: 40px 20px; border: 2px dashed var(--border-color-primary); border-radius: 12px; }
    .lb-placeholder-title { font-size: 1.5rem; font-weight: bold; margin-bottom: 10px; }
    
    .leaderboard-html-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .leaderboard-html-table th { background: var(--table-even-background-fill); padding: 12px; text-align: left; }
    .leaderboard-html-table td { padding: 12px; border-bottom: 1px solid var(--border-color-primary); }
    .user-row-highlight { background: rgba(99, 102, 241, 0.1); font-weight: bold; }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue="indigo"), css=css) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text' style='margin-top:15px; font-weight:bold;'>Cargando...</span></div>")

        username_state = gr.State("")
        token_state = gr.State(None)
        team_name_state = gr.State("")
        last_submission_score_state = gr.State(0.0)
        best_score_state = gr.State(0.0)
        submission_count_state = gr.State(0)
        last_rank_state = gr.State(0)
        first_submission_score_state = gr.State(None)
        was_preview_state = gr.State(False)
        readiness_state = gr.State(True)
        kpi_meta_state = gr.State({})
        last_seen_ts_state = gr.State(None)
        
        # Slides 1-6
        with gr.Column(visible=True, elem_id="slide-1") as briefing_slide_1:
            gr.Markdown("<h1 style='text-align:center;'>🔄 Arquitecto de IA Climática</h1>")
            gr.HTML("""
                <div class='panel-box'>
                    <h3>Tu Impacto</h3>
                    <p>Los edificios emiten el 40% del CO2 mundial. Para combatir el cambio climático, debemos identificar cuáles consumen energía de forma ineficiente.</p>
                    <p>Tu misión es crear una <b>IA</b> que aprenda a predecir la intensidad energética basándose en datos de edificios reales. ¡Ayúdanos a priorizar dónde intervenir!</p>
                </div>
            """)
            btn_1_next = gr.Button("Aceptar Misión ▶️", variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="slide-2") as briefing_slide_2:
            gr.Markdown("<h1 style='text-align:center;'>💰 Tu desafío corporativo</h1>")
            gr.HTML("""
                <div class='panel-box'>
                    <p>Te unirás a un equipo de élite para optimizar los recursos de rehabilitación. Competirás con otros departamentos por la mejor precisión.</p>
                    <p>Tus modelos subirán a la clasificación global. ¡Lleva a tu equipo a la cima de la eficiencia!</p>
                    <div style='background:rgba(99,102,241,0.1); padding:10px; border-radius:8px; border:1px solid var(--color-accent); text-align:center;'>
                        Serás asignado a un equipo como: <b>🛡️ Guardianes del Clima</b>
                    </div>
                </div>
            """)
            with gr.Row():
                btn_2_back = gr.Button("◀️ Atrás")
                btn_2_next = gr.Button("Siguiente ▶️", variant="primary")

        with gr.Column(visible=False, elem_id="slide-3") as briefing_slide_3:
            gr.Markdown("<h1 style='text-align:center;'>🤖 ¿Qué es un modelo de IA?</h1>")
            gr.HTML("""
                <div class='panel-box'>
                    <p>Imagínate la IA como una "máquina de predicción". Para el clima, funciona así:</p>
                    <p>1. <b>Entradas (Datos):</b> Superficie, año de construcción, clima local.</p>
                    <p>2. <b>El Cerebro (Algoritmo):</b> Encuentra patrones de desperdicio energético.</p>
                    <p>3. <b>Salida (Predicción):</b> Nivel de consumo esperado (EUI).</p>
                </div>
            """)
            with gr.Row():
                btn_3_back = gr.Button("◀️ Atrás")
                btn_3_next = gr.Button("Siguiente ▶️", variant="primary")

        with gr.Column(visible=False, elem_id="slide-4") as briefing_slide_4:
            gr.Markdown("<h1 style='text-align:center;'>🔁 El Ciclo de Ingeniería</h1>")
            gr.HTML("""
                <div class='panel-box'>
                    <p>Los grandes sistemas no se construyen en un día. Seguirás este proceso:</p>
                    <p><b>Configura</b> (elige modelo) → <b>Envía</b> (mide precisión) → <b>Analiza</b> (mira la tabla) → <b>Refina</b> (mejora los ingredientes).</p>
                </div>
            """)
            with gr.Row():
                btn_4_back = gr.Button("◀️ Atrás")
                btn_4_next = gr.Button("Siguiente ▶️", variant="primary")

        with gr.Column(visible=False, elem_id="slide-5") as briefing_slide_5:
            gr.Markdown("<h1 style='text-align:center;'>🔧 Los Controles</h1>")
            gr.HTML("""
                <div class='panel-box'>
                    <p>Tendrás 4 controles clave:</p>
                    <p>1. <b>Estrategia:</b> El tipo de "lógica" que usa la IA.</p>
                    <p>2. <b>Complejidad:</b> ¿Cuánto detalle debe memorizar?</p>
                    <p>3. <b>Variables:</b> ¿Qué datos le permitimos ver?</p>
                    <p>4. <b>Tamaño:</b> ¿Cuántos ejemplos históricos lee?</p>
                </div>
            """)
            with gr.Row():
                btn_5_back = gr.Button("◀️ Atrás")
                btn_5_next = gr.Button("Siguiente ▶️", variant="primary")

        with gr.Column(visible=False, elem_id="slide-6") as briefing_slide_6:
            gr.Markdown("<h1 style='text-align:center;'>🚀 Veredicto Final</h1>")
            gr.HTML("""
                <div class='panel-box'>
                    <p>Tu IA será evaluada contra una "Caja Fuerte" de datos que nunca ha visto. Solo la precisión real contará para la clasificación.</p>
                    <p><b>Objetivo:</b> Superar el 70% de precisión para ser considerado un experto.</p>
                </div>
            """)
            with gr.Row():
                btn_6_back = gr.Button("◀️ Atrás")
                btn_6_next = gr.Button("Comenzar construcción ▶️", variant="primary")

        # Main Arena
        with gr.Column(visible=False, elem_id="model-step") as model_building_step:
            gr.Markdown("<h1 style='text-align:center;'>🛠️ Área de Modelado Energético</h1>")
            rank_message_display = gr.Markdown("### Cargando...")
            
            with gr.Row():
                with gr.Column(scale=1):
                    model_type_radio = gr.Radio(label="1. Estrategia del modelo", choices=MODEL_RADIO_CHOICES, value=DEFAULT_MODEL, interactive=True)
                    model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL))
                    gr.Markdown("---")
                    complexity_slider = gr.Slider(label="2. Complejidad del modelo (1–10)", minimum=1, maximum=3, step=1, value=2)
                    gr.Markdown("---")
                    feature_set_checkbox = gr.CheckboxGroup(label="3. Variables de datos", choices=FEATURE_SET_ALL_OPTIONS, value=FEATURE_SET_GROUP_1_VALS, interactive=True)
                    gr.Markdown("---")
                    data_size_radio = gr.Radio(label="4. Tamaño de los datos", choices=[DATA_SIZE_RADIO_CHOICES[0]], value=DEFAULT_DATA_SIZE, interactive=True)
                    gr.Markdown("---")
                    attempts_tracker_display = gr.HTML("<p>Intentos usados: 0/10</p>")
                    submit_button = gr.Button("5. 🔬 Construir y enviar modelo", variant="primary", size="lg")

                with gr.Column(scale=1):
                    gr.HTML("<div class='leaderboard-box'><h3>🏆 Clasificación en directo</h3></div>")
                    submission_feedback_display = gr.HTML("<p style='text-align:center; color:#6b7280;'>Envía tu modelo para recibir valoración.</p>")
                    
                    login_username = gr.Textbox(label="Usuario", visible=False)
                    login_password = gr.Textbox(label="Contraseña", type="password", visible=False)
                    login_submit = gr.Button("Entrar y Enviar", variant="primary", visible=False)
                    login_error = gr.HTML(visible=False)

                    with gr.Tabs():
                        with gr.Tab("Equipos"): team_leaderboard_display = gr.HTML("<p style='text-align:center;'>Cargando equipos...</p>")
                        with gr.Tab("Individual"): individual_leaderboard_display = gr.HTML("<p style='text-align:center;'>Cargando ranking...</p>")

            with gr.Row():
                arena_to_briefing = gr.Button("◀️ Ver instrucciones", size="lg")
                arena_to_finish = gr.Button("Finalizar y resumir ▶️", variant="secondary", size="lg")

        # Conclusion
        with gr.Column(visible=False, elem_id="conclusion-step") as conclusion_step:
            gr.Markdown("<h1 style='text-align:center;'>✅ Resumen de la Misión</h1>")
            final_summary_display = gr.HTML()
            conclusion_back = gr.Button("◀️ Volver al Área de Modelado")

        # --- Navigation Logic ---
        all_steps = [briefing_slide_1, briefing_slide_2, briefing_slide_3, briefing_slide_4, briefing_slide_5, briefing_slide_6, model_building_step, conclusion_step]
        
        def nav_js(target_id, message):
            return f"""()=>{{
                const overlay = document.getElementById('nav-loading-overlay');
                const text = document.getElementById('nav-loading-text');
                if(overlay && text) {{
                    text.innerText = '{message}';
                    overlay.style.display = 'flex';
                    setTimeout(() => overlay.style.opacity = '1', 10);
                }}
                window.scrollTo({{top: 0, behavior: 'smooth'}});
                setTimeout(() => {{
                    if(overlay) {{
                        overlay.style.opacity = '0';
                        setTimeout(() => overlay.style.display = 'none', 300);
                    }}
                }}, 1000);
            }}"""

        def switch_step(target_idx):
            return [gr.update(visible=(i == target_idx)) for i in range(len(all_steps))]

        btn_1_next.click(lambda: switch_step(1), outputs=all_steps, js=nav_js("slide-2", "Preparando misión..."))
        btn_2_next.click(lambda: switch_step(2), outputs=all_steps, js=nav_js("slide-3", "Entendiendo la IA...")); btn_2_back.click(lambda: switch_step(0), outputs=all_steps)
        btn_3_next.click(lambda: switch_step(3), outputs=all_steps, js=nav_js("slide-4", "Definiendo el flujo...")); btn_3_back.click(lambda: switch_step(1), outputs=all_steps)
        btn_4_next.click(lambda: switch_step(4), outputs=all_steps, js=nav_js("slide-5", "Configurando mandos...")); btn_4_back.click(lambda: switch_step(2), outputs=all_steps)
        btn_5_next.click(lambda: switch_step(5), outputs=all_steps, js=nav_js("slide-6", "Últimos detalles...")); btn_5_back.click(lambda: switch_step(3), outputs=all_steps)
        btn_6_next.click(lambda: switch_step(6), outputs=all_steps, js=nav_js("model-step", "Entrando a la arena...")); btn_6_back.click(lambda: switch_step(4), outputs=all_steps)
        
        arena_to_briefing.click(lambda: switch_step(5), outputs=all_steps)
        arena_to_finish.click(
            fn=lambda s1, s2, s3, s4, s5: switch_step(7) + [build_final_conclusion_html(s1, s2, s3, s4, s5)],
            inputs=[best_score_state, submission_count_state, last_rank_state, first_submission_score_state, feature_set_checkbox],
            outputs=all_steps + [final_summary_display],
            js=nav_js("conclusion-step", "Generando veredicto...")
        )
        conclusion_back.click(lambda: switch_step(6), outputs=all_steps)

        # Event Handlers
        model_type_radio.change(get_model_card, inputs=model_type_radio, outputs=model_card_display)
        
        login_submit.click(
            perform_inline_login, 
            inputs=[login_username, login_password], 
            outputs=[login_username, login_password, login_submit, login_error, submit_button, submission_feedback_display, team_name_state, username_state, token_state]
        )

        all_arena_outputs = [
            submission_feedback_display, team_leaderboard_display, individual_leaderboard_display,
            last_submission_score_state, last_rank_state, best_score_state, submission_count_state, first_submission_score_state,
            rank_message_display, model_type_radio, complexity_slider, feature_set_checkbox, data_size_radio,
            submit_button, attempts_tracker_display, was_preview_state, kpi_meta_state, last_seen_ts_state
        ]

        submit_button.click(
            run_experiment,
            inputs=[model_type_radio, complexity_slider, feature_set_checkbox, data_size_radio, team_name_state, last_submission_score_state, last_rank_state, submission_count_state, first_submission_score_state, best_score_state, username_state, token_state],
            outputs=all_arena_outputs,
            show_progress="full",
            js=nav_js("model-step", "Ejecutando simulación...")
        ).then(
            fn=None, js="() => { try { window.parent.postMessage('model-updated', '*'); } catch(e) {} }"
        )

        # Init Load
        def handle_load(request: gr.Request):
            success, user, token = _try_session_based_auth(request)
            results = on_initial_load(user, token) # [m_card, t_lb, i_lb, r_msg, m_rad, c_sld, f_chk, d_rad]
            
            if success:
                stats = _compute_user_stats(user, token)
                return results + (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), user, token, stats.get("team_name", ""))
            
            return results + (gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), "", None, "")

        demo.load(
            handle_load,
            outputs=[model_card_display, team_leaderboard_display, individual_leaderboard_display, rank_message_display, model_type_radio, complexity_slider, feature_set_checkbox, data_size_radio, login_username, login_password, login_submit, login_error, username_state, token_state, team_name_state]
        )

    return demo
# -------------------------------------------------------------------------
# 4. Convenience Launcher
# -------------------------------------------------------------------------

def launch_model_building_game_es_sustainability_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    """
    Create and directly launch the Model Building Game app inline (e.g., in notebooks).
    """
    global playground
    if playground is None:
        try:
            playground = Competition(MY_PLAYGROUND_ID)
        except Exception as e:
            print(f"WARNING: Could not connect to playground: {e}")
            playground = None

    demo = create_model_building_game_es_sustainability_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

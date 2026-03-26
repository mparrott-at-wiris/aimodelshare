"""
Activity 4 V2 — Interactive Onboarding + Model Building Arena.

Replaces the briefing slides with a fast, interactive onboarding converted
from onboarding.jsx.  The arena and conclusion use the REAL Gradio-powered
model building code from Activity 4 (SQLite cache, session auth,
run_experiment, playground API, leaderboard, rank gating).

Port: 8081
"""

import os

# Thread limits (MUST be set before importing numpy/sklearn)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import time
import random
import hashlib
import threading
import functools
from typing import Optional, Dict, Any, Tuple, Callable, TypeVar

import numpy as np
import pandas as pd
import gradio as gr

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

try:
    from aimodelshare.playground import Competition
except ImportError:
    raise ImportError("The 'aimodelshare' library is required. Install with: pip install aimodelshare")

from aimodelshare.moral_compass.apps.sustainability.dataset_path_resolver import get_wids_dataset_path

# ---------------------------------------------------------------------------
# Cache Configuration (Thread-Safe SQLite)
# ---------------------------------------------------------------------------
import sqlite3

CACHE_DB_FILE = "prediction_cache.sqlite"


def get_cached_prediction(key):
    _log(f"CACHE LOOKUP: key={repr(key)}")
    search_roots = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        "/app"]
    db_path = None
    for root in search_roots:
        p = os.path.join(root, CACHE_DB_FILE)
        if os.path.exists(p):
            db_path = p
            break
    if not db_path:
        _log(f"{CACHE_DB_FILE} NOT FOUND. Searched roots: {search_roots}")
        return None
    _log(f"Using DB at: {db_path}")
    try:
        hashed_key = hashlib.md5(key.encode('utf-8')).hexdigest()
        conn_str = f"file:{db_path}?mode=ro"
        with sqlite3.connect(conn_str, uri=True, timeout=10.0) as conn:
            conn.execute("PRAGMA cache_size = -2000")
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cache WHERE key=?", (hashed_key,))
            result = cursor.fetchone()
            if result:
                _log("CACHE HIT")
                raw_value = result[0]
                if isinstance(raw_value, bytes):
                    unpacked = np.unpackbits(np.frombuffer(raw_value, dtype=np.uint8))
                    if len(unpacked) > 1000:
                        unpacked = unpacked[:1000]
                    return unpacked
                else:
                    return np.array([int(c) for c in raw_value], dtype=np.uint8)
            else:
                _log(f"CACHE MISS (Hashed: {hashed_key})")
                return None
    except Exception as e:
        _log(f"DB ERROR: {e}")
        return None


# ---------------------------------------------------------------------------
# Test Label Loader
# ---------------------------------------------------------------------------
_Y_TEST = None
_Y_TEST_LOCK = threading.Lock()


# -------------------------------------------------------------------------
# Lightweight Label Loader (No Training, Only Test Accuracy Computation)
# -------------------------------------------------------------------------
_Y_TEST = None
_Y_TEST_LOCK = threading.Lock()

def get_test_labels(csv_path: Optional[str] = None) -> pd.Series:
    """
    Load test labels from CSV file for local accuracy computation.
    Matches the exact sampling and splitting logic from precompute_wids_cache.py.
    
    Args:
        csv_path: Optional path to dataset csv. If not provided, uses get_wids_dataset_path()
                  to automatically resolve the path.
    Returns:
        pd.Series: Test labels (y_test)
    """
    # Resolve dataset path if not explicitly provided
    if csv_path is None:
        csv_path = get_wids_dataset_path()
    
    # Load data
    df = pd.read_csv(csv_path)
    
    # Sample MAX_ROWS
    if df.shape[0] > 4000:  # MAX_ROWS = 4000
        df = df.sample(n=4000, random_state=42)
    
    # Extract features and target (matching precompute_wids_cache.py)
    all_numeric_cols = ["floor_area", "year_built", "ELEVATION", "heating_degree_days", 
                        "cooling_degree_days", "january_min_temp", "july_max_temp", 
                        "avg_temp", "april_avg_temp", "october_avg_temp"]
    all_categorical_cols = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
    feature_columns = all_numeric_cols + all_categorical_cols
    
    # Ensure all columns exist
    for col in feature_columns:
        if col not in df.columns:
            df[col] = np.nan
    
    X = df[feature_columns].copy()
    y = df["high_energy_usage"].copy()
    
    # Split (matching precompute_wids_cache.py: test_size=0.25, random_state=42, stratify=y)
    _, _, _, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    
    return y_test

def _ensure_y_test_loaded():
    """Ensure test labels are loaded into memory (thread-safe, cached)."""
    global _Y_TEST
    with _Y_TEST_LOCK:
        if _Y_TEST is None:
            print("Loading test labels for local accuracy computation...", flush=True)
            _Y_TEST = get_test_labels()
            print(f"✅ Test labels loaded: {len(_Y_TEST)} samples", flush=True)


# ---------------------------------------------------------------------------
# Leaderboard / Stats Caching
# ---------------------------------------------------------------------------
LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

_cache_lock = threading.Lock()
_user_stats_lock = threading.Lock()
_auth_lock = threading.Lock()

_leaderboard_cache: Dict[str, Dict[str, Any]] = {
    "anon": {"data": None, "timestamp": 0.0},
    "auth": {"data": None, "timestamp": 0.0},
}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

T = TypeVar("T")


def _retry_with_backoff(func: Callable[[], T], max_attempts: int = 3, base_delay: float = 0.5, description: str = "operation") -> T:
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
                delay *= 2
            else:
                _log(f"{description} failed after {max_attempts} attempts: {e}")
    raise last_exception  # type: ignore[misc]


def _log(msg: str):
    if DEBUG_LOG:
        print(f"[A4V2] {msg}")


def _normalize_team_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(str(name).strip().split())


def _get_leaderboard_with_optional_token(playground_instance, token=None):
    if playground_instance is None:
        return None
    def _fetch():
        try:
            if token:
                return playground_instance.get_leaderboard(token=token)
            return playground_instance.get_leaderboard()
        except Exception as e:
            if "scalar values" in str(e):
                return pd.DataFrame(columns=["username", "accuracy", "Team", "timestamp"])
            raise e
    try:
        return _retry_with_backoff(_fetch, description="leaderboard fetch")
    except Exception as e:
        _log(f"Leaderboard fetch failed after retries: {e}")
        return None


def _fetch_leaderboard(token: Optional[str]) -> Optional[pd.DataFrame]:
    cache_key = "auth" if token else "anon"
    now = time.time()
    with _cache_lock:
        cache_entry = _leaderboard_cache[cache_key]
        if cache_entry["data"] is not None and now - cache_entry["timestamp"] < LEADERBOARD_CACHE_SECONDS:
            return cache_entry["data"]
    df = None
    try:
        playground_id = "https://bhtrtkrbf4.execute-api.us-east-1.amazonaws.com/prod/m"
        playground_instance = Competition(playground_id)
        def _fetch():
            try:
                if token:
                    return playground_instance.get_leaderboard(token=token)
                return playground_instance.get_leaderboard()
            except Exception as e:
                if "scalar values" in str(e):
                    return pd.DataFrame(columns=["username", "accuracy", "Team", "timestamp"])
                raise e
        df = _retry_with_backoff(_fetch, description="leaderboard fetch")
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
    except Exception as e:
        _log(f"Leaderboard fetch failed: {e}")
        df = None
    with _cache_lock:
        _leaderboard_cache[cache_key]["data"] = df
        _leaderboard_cache[cache_key]["timestamp"] = time.time()
    return df


def _get_or_assign_team(username: str, leaderboard_df) -> Tuple[str, bool]:
    try:
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(user_submissions["timestamp"], errors="coerce")
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                    except Exception:
                        pass
                existing_team = user_submissions.iloc[0]["Team"]
                if pd.notna(existing_team) and str(existing_team).strip():
                    return _normalize_team_name(existing_team), False
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        return new_team, True
    except Exception:
        return _normalize_team_name(random.choice(TEAM_NAMES)), True


def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id:
            return False, None, None
        from aimodelshare.aws import get_token_from_session, _get_username_from_token
        token = get_token_from_session(session_id)
        if not token:
            return False, None, None
        username = _get_username_from_token(token)
        if not username:
            return False, None, None
        return True, username, token
    except Exception:
        return False, None, None


def _compute_user_stats(username: str, token: str) -> Dict[str, Any]:
    now = time.time()
    with _user_stats_lock:
        cached = _user_stats_cache.get(username)
        if cached and (now - cached.get("_ts", 0) < USER_STATS_TTL):
            return cached.copy()
    leaderboard_df = _fetch_leaderboard(token)
    team_name, _ = _get_or_assign_team(username, leaderboard_df)
    stats: Dict[str, Any] = {"best_score": 0.0, "rank": 0, "team_name": team_name, "submission_count": 0, "last_score": 0.0, "_ts": time.time()}
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
                            user_submissions["timestamp"] = pd.to_datetime(user_submissions["timestamp"], errors="coerce")
                            recent = user_submissions.sort_values("timestamp", ascending=False).iloc[0]
                            stats["last_score"] = float(recent["accuracy"])
                        except Exception:
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
    with _user_stats_lock:
        _user_stats_cache[username] = stats
    return stats


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MY_PLAYGROUND_ID = "https://bhtrtkrbf4.execute-api.us-east-1.amazonaws.com/prod/m"
ATTEMPT_LIMIT = 10
LEADERBOARD_POLL_TRIES = 60
LEADERBOARD_POLL_SLEEP = 1.0

MODEL_TYPES = {
    "The Balanced Generalist": {
        "model_builder": lambda: LogisticRegression(max_iter=500, random_state=42, class_weight="balanced"),
        "card": "Un model ràpid, fiable i equilibrat. Un bon punt de partida; menys propens al sobreajustament.",
    },
    "The Rule-Maker": {
        "model_builder": lambda: DecisionTreeClassifier(random_state=42, class_weight="balanced"),
        "card": "Aprèn regles simples de tipus 'si/aleshores'. Fàcil d'interpretar, però pot passar per alt patrons subtils.",
    },
    "The 'Nearest Neighbor'": {
        "model_builder": lambda: KNeighborsClassifier(),
        "card": "Analitza els exemples passats més propers. 'T'assembles a aquests altres; prediré segons el seu comportament'.",
    },
    "The Deep Pattern-Finder": {
        "model_builder": lambda: RandomForestClassifier(random_state=42, class_weight="balanced"),
        "card": "Un conjunt de molts arbres de decisió. Potent, pot captar patrons profunds; vigila la complexitat.",
    },
}

DEFAULT_MODEL = "The Balanced Generalist"

TEAM_NAMES = [
    "The Climate Guardians", "United Eco-Architects", "The Energy Detectives",
    "The Sustainability League", "Green Future Engineers", "Zero Carbon Avengers",
]

TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Climate Guardians": "The Climate Guardians",
        "United Eco-Architects": "United Eco-Architects",
        "The Energy Detectives": "The Energy Detectives",
        "The Sustainability League": "The Sustainability League",
        "Green Future Engineers": "Green Future Engineers",
        "Zero Carbon Avengers": "Zero Carbon Avengers"
    },
    "ca": {
        "The Climate Guardians": "Els Guardians del Clima",
        "United Eco-Architects": "Eco-Arquitectes Units",
        "The Energy Detectives": "Els Detectius de l'Energia",
        "The Sustainability League": "La Lliga de la Sostenibilitat",
        "Green Future Engineers": "Enginyers del Futur Verd",
        "Zero Carbon Avengers": "Els Venjadors del Carboni Zero"
    }
}
UI_TEAM_LANG = "ca"

MODEL_DISPLAY_MAP = {
    "The Balanced Generalist": "El Generalista Equilibrat",
    "The Rule-Maker": "El Creador de Regles",
    "The 'Nearest Neighbor'": "El 'Veí més Proper'",
    "The Deep Pattern-Finder": "El Detector de Patrons Profunds"
}


def translate_team_name_for_display(english_name: str, lang: str = "ca") -> str:
    return TEAM_NAME_TRANSLATIONS.get(lang, TEAM_NAME_TRANSLATIONS["en"]).get(english_name, english_name)


FEATURE_SET_ALL_OPTIONS = [
    ("Superfície (m²)", "floor_area"),
    ("Any de construcció", "year_built"),
    ("Classe d'edifici", "building_class"),
    ("Tipus d'instal·lació", "facility_type"),
    ("Factor d'estat", "State_Factor"),
    ("Factor d'any", "Year_Factor"),
    ("Elevació", "ELEVATION"),
    ("Dies de calefacció", "heating_degree_days"),
    ("Dies de refrigeració", "cooling_degree_days"),
    ("Temp. mitjana anual", "avg_temp"),
    ("Temp. mínima de gener", "january_min_temp"),
    ("Temp. màxima de juliol", "july_max_temp"),
    ("Temp. mitjana d'abril", "april_avg_temp"),
    ("Temp. mitjana d'octubre", "october_avg_temp"),
]
FEATURE_SET_GROUP_1_VALS = ["floor_area", "year_built", "building_class", "facility_type"]
FEATURE_SET_GROUP_2_VALS = ["State_Factor", "Year_Factor", "ELEVATION"]
FEATURE_SET_GROUP_3_VALS = [
    "avg_temp", "heating_degree_days", "cooling_degree_days",
    "january_min_temp", "july_max_temp", "april_avg_temp", "october_avg_temp",
]
ALL_NUMERIC_COLS = [
    "floor_area", "year_built", "ELEVATION", "heating_degree_days",
    "cooling_degree_days", "january_min_temp", "july_max_temp",
    "avg_temp", "april_avg_temp", "october_avg_temp",
]
ALL_CATEGORICAL_COLS = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
DEFAULT_FEATURE_SET = FEATURE_SET_GROUP_1_VALS

DATA_SIZE_MAP = {"Small (20%)": 0.2, "Medium (60%)": 0.6, "Large (80%)": 0.8, "Full (100%)": 1.0}
DATA_SIZE_DISPLAY_MAP = {
    "Small (20%)": "Petita (20%)",
    "Medium (60%)": "Mitjana (60%)",
    "Large (80%)": "Gran (80%)",
    "Full (100%)": "Completa (100%)"
}
DEFAULT_DATA_SIZE = "Small (20%)"

MAX_ROWS = 4000
np.random.seed(42)

playground = None


# ---------------------------------------------------------------------------
# Data & Backend Utilities
# ---------------------------------------------------------------------------
def safe_int(value, default=1):
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _get_user_latest_accuracy(df, username):
    if df is None or df.empty:
        return None
    try:
        user_rows = df[df["username"] == username]
        if user_rows.empty or "accuracy" not in user_rows.columns:
            return None
        if "timestamp" in user_rows.columns:
            user_rows = user_rows.copy()
            user_rows["__parsed_ts"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
            valid_ts = user_rows[user_rows["__parsed_ts"].notna()]
            if not valid_ts.empty:
                return float(valid_ts.sort_values("__parsed_ts", ascending=False).iloc[0]["accuracy"])
        return float(user_rows.iloc[-1]["accuracy"])
    except Exception:
        return None


def _get_user_latest_ts(df, username):
    if df is None or df.empty:
        return None
    try:
        user_rows = df[df["username"] == username]
        if user_rows.empty or "timestamp" not in user_rows.columns:
            return None
        user_rows = user_rows.copy()
        user_rows["__parsed_ts"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
        valid_ts = user_rows[user_rows["__parsed_ts"].notna()]
        if valid_ts.empty:
            return None
        latest_ts = valid_ts["__parsed_ts"].max()
        return latest_ts.timestamp() if pd.notna(latest_ts) else None
    except Exception:
        return None


@functools.lru_cache(maxsize=32)
def _get_cached_preprocessor_config(numeric_cols_tuple, categorical_cols_tuple):
    numeric_cols = list(numeric_cols_tuple)
    categorical_cols = list(categorical_cols_tuple)
    transformers = []
    selected_cols = []
    if numeric_cols:
        num_tf = Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
        transformers.append(("num", num_tf, numeric_cols))
        selected_cols.extend(numeric_cols)
    if categorical_cols:
        cat_tf = Pipeline(steps=[("imputer", SimpleImputer(strategy="constant", fill_value="missing")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))])
        transformers.append(("cat", cat_tf, categorical_cols))
        selected_cols.extend(categorical_cols)
    return transformers, selected_cols


def build_preprocessor(numeric_cols, categorical_cols):
    numeric_tuple = tuple(sorted(numeric_cols))
    categorical_tuple = tuple(sorted(categorical_cols))
    transformers, selected_cols = _get_cached_preprocessor_config(numeric_tuple, categorical_tuple)
    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    return preprocessor, selected_cols


def _ensure_dense(X):
    from scipy import sparse
    if sparse.issparse(X):
        return X.toarray()
    return X


def tune_model_complexity(model, level):
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


# ---------------------------------------------------------------------------
# HTML Builder Helpers
# ---------------------------------------------------------------------------
def _build_attempts_tracker_html(current_count, limit=10):
    bg_color = "#f0f9ff"
    border_color = "#bae6fd"
    text_color = "#0369a1"
    if current_count >= limit:
        icon = "🛑"
        label = f"Última oportunitat (de moment) per millorar la teva puntuació!: {current_count}/{limit}"
    else:
        icon = "📊"
        label = f"Intents utilitzats: {current_count}/{limit}"
    return f"<div style='text-align:center; padding:8px; margin:8px 0; background:{bg_color}; border-radius:8px; border:1px solid {border_color};'><p style='margin:0; color:{text_color}; font-weight:600; font-size:1rem;'>{icon} {label}</p></div>"


def check_attempt_limit(submission_count, limit=None):
    if limit is None:
        limit = ATTEMPT_LIMIT
    if submission_count >= limit:
        return False, f"Attempt limit reached ({submission_count}/{limit})"
    return True, f"Attempts: {submission_count}/{limit}"


def _build_skeleton_leaderboard(rows=6, is_team=True, submit_button_label="5. 🔬 Construeix i Envia Model"):
    context_label = "Equip" if is_team else "Individual"
    return f"""<div class='lb-placeholder' aria-live='polite'><div class='lb-placeholder-title'>Classificació {context_label} Pendent</div><div class='lb-placeholder-sub'><p style='margin:0 0 6px 0;'>Envia el teu primer model per omplir aquesta taula.</p><p style='margin:0;'><strong>Clica "{submit_button_label}" (a baix a l'esquerra)</strong> per començar!</p></div></div>"""


def build_login_prompt_html():
    return """<h2 style='color: var(--body-text-color, #111827); margin-top:20px; border-top: 2px solid var(--border-color-primary, #e5e7eb); padding-top: 20px;'>🔐 Inicia sessió per enviar i classificar-te</h2><div style='margin-top:16px; text-align:left; font-size:1rem; line-height:1.6; color:var(--secondary-text-color, #374151);'><p style='margin:12px 0;'>Aquesta és només una previsualització. Inicia sessió per publicar la teva puntuació a la classificació en viu, pujar de rang i contribuir punts al teu equip.</p><p style='margin:12px 0;'><strong>Nou usuari?</strong> Crea un compte gratuït a <a href='https://www.modelshare.ai/login' target='_blank' style='color:#4f46e5; text-decoration:underline;'>modelshare.ai/login</a></p></div>"""


def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count, is_preview=False, is_pending=False, local_test_accuracy=None):
    if is_pending:
        title = "⏳ Processant Enviament"
        acc_color = "#3b82f6"
        acc_text = f"{(local_test_accuracy * 100):.2f}%" if local_test_accuracy is not None else "N/A"
        if local_test_accuracy is not None and last_score is not None and last_score > 0:
            score_diff = local_test_accuracy - last_score
            if abs(score_diff) < 0.0001:
                acc_diff_html = "<p style='font-size:1.5rem; font-weight:600; color:var(--secondary-text-color, #6b7280); margin:0;'>Sense Canvi (Estimat)</p>"
            elif score_diff > 0:
                acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:#16a34a; margin:0;'>+{(score_diff*100):.2f} (Estimat)</p>"
            else:
                acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:#ef4444; margin:0;'>{(score_diff*100):.2f} (Estimat)</p>"
        else:
            acc_diff_html = "<p style='font-size:1.2rem; font-weight:500; color:var(--secondary-text-color, #6b7280); margin:0;'>Actualització de classificació pendent...</p>"
        border_color = acc_color
        rank_color = "#6b7280"
        rank_text = "Pendent"
        rank_diff_html = "<p style='font-size:1.2rem; font-weight:500; color:var(--secondary-text-color, #6b7280); margin:0;'>Calculant posició...</p>"
    elif is_preview:
        title = "🔬 Previsualització Exitosa!"
        acc_color = "#16a34a"
        acc_text = f"{(new_score*100):.2f}%" if new_score > 0 else "N/A"
        acc_diff_html = "<div style='background:var(--color-accent-soft, #eff6ff); border:2px solid #3b82f6; padding:10px 14px; border-radius:8px; margin-top:8px;'><p style='margin:0; color:var(--color-accent, #1e40af); font-weight:600; font-size:1rem;'>NOMÉS PREVISUALITZACIÓ — no s'ha enviat a la classificació. Inicia sessió per enviar de veritat.</p></div>"
        border_color = acc_color
        rank_color = "#3b82f6"
        rank_text = "N/A"
        rank_diff_html = "<p style='font-size:1.2rem; font-weight:500; color:var(--secondary-text-color, #6b7280); margin:0;'>Sense classificació (previsualització)</p>"
    elif submission_count == 0:
        title = "🎉 Primer Model Enviat!"
        acc_color = "#16a34a"
        acc_text = f"{(new_score*100):.2f}%"
        acc_diff_html = "<p style='font-size:1.2rem; font-weight:500; color:var(--secondary-text-color, #6b7280); margin:0; padding-top:8px;'>(La teva primera puntuació!)</p>"
        rank_color = "#3b82f6"
        rank_text = f"#{new_rank}"
        rank_diff_html = "<p style='font-size:1.5rem; font-weight:600; color:#3b82f6; margin:0;'>Ets a la classificació!</p>"
        border_color = acc_color
    else:
        score_diff = new_score - last_score
        if abs(score_diff) < 0.0001:
            title = "✅ Enviament Correcte"
            acc_color = "#6b7280"
            acc_text = f"{(new_score*100):.2f}%"
            acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:{acc_color}; margin:0;'>Sense Canvi</p>"
            border_color = acc_color
        elif score_diff > 0:
            title = "✅ Enviament Correcte!"
            acc_color = "#16a34a"
            acc_text = f"{(new_score*100):.2f}%"
            acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:{acc_color}; margin:0;'>+{(score_diff*100):.2f}</p>"
            border_color = acc_color
        else:
            title = "📉 Puntuació Baixada"
            acc_color = "#ef4444"
            acc_text = f"{(new_score*100):.2f}%"
            acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:{acc_color}; margin:0;'>{(score_diff*100):.2f}</p>"
            border_color = acc_color
        rank_diff = last_rank - new_rank
        rank_color = "#3b82f6"
        rank_text = f"#{new_rank}"
        if last_rank == 0:
            rank_diff_html = "<p style='font-size:1.5rem; font-weight:600; color:#3b82f6; margin:0;'>Ets a la classificació!</p>"
        elif rank_diff > 0:
            rank_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:#16a34a; margin:0;'>Has pujat {rank_diff} posició{'ns' if rank_diff > 1 else ''}!</p>"
        elif rank_diff < 0:
            rank_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:#ef4444; margin:0;'>Has baixat {abs(rank_diff)} posició{'ns' if abs(rank_diff) > 1 else ''}</p>"
        else:
            rank_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:{rank_color}; margin:0;'>Sense Canvi</p>"
    return f"""<div class='kpi-card' style='border-color:{border_color};'><h2 style='color:var(--body-text-color); margin-top:0;'>{title}</h2><div class='kpi-card-body'><div class='kpi-metric-box'><p class='kpi-label'>Nova Precisió</p><p style='font-size:0.8rem; color:var(--secondary-text-color, #6b7280); margin:0;'>% d'edificis que la teva IA ha predit correctament</p><p class='kpi-score' style='color:{acc_color};'>{acc_text}</p>{acc_diff_html}<p style='font-size:0.75rem; color:var(--secondary-text-color, #9ca3af); margin:8px 0 0;'>Per sota del 60% = Cal Millorar &middot; 60-70% = Acceptable &middot; 70-80% = Bo &middot; 80%+ = Excel·lent</p></div><div class='kpi-metric-box'><p class='kpi-label'>El Teu Rànquing</p><p class='kpi-score' style='color:{rank_color};'>{rank_text}</p>{rank_diff_html}</div></div></div>"""


def _build_team_html(team_summary_df, team_name):
    if team_summary_df is None or team_summary_df.empty:
        return "<p style='text-align:center; color:var(--secondary-text-color, #6b7280); padding-top:20px;'>Encara no hi ha enviaments d'equip.</p>"
    normalized_user_team = _normalize_team_name(team_name).lower()
    header = "<table class='leaderboard-html-table'><thead><tr><th>Posició</th><th>Equip</th><th>Millor Puntuació</th><th>Puntuació Mitjana</th><th>Enviaments</th></tr></thead><tbody>"
    body = ""
    for index, row in team_summary_df.iterrows():
        normalized_row_team = _normalize_team_name(row["Team"]).lower()
        is_user_team = normalized_row_team == normalized_user_team
        row_class = "class='user-row-highlight'" if is_user_team else ""
        body += f"<tr {row_class}><td>{index}</td><td>{translate_team_name_for_display(row['Team'], UI_TEAM_LANG)}</td><td>{(row['Best_Score']*100):.2f}%</td><td>{(row['Avg_Score']*100):.2f}%</td><td>{row['Submissions']}</td></tr>"
    return header + body + "</tbody></table>"


def _build_individual_html(individual_summary_df, username):
    if individual_summary_df is None or individual_summary_df.empty:
        return "<p style='text-align:center; color:var(--secondary-text-color, #6b7280); padding-top:20px;'>Encara no hi ha enviaments individuals.</p>"
    header = "<table class='leaderboard-html-table'><thead><tr><th>Posició</th><th>Enginyer/a</th><th>Millor Puntuació</th><th>Enviaments</th></tr></thead><tbody>"
    body = ""
    for index, row in individual_summary_df.iterrows():
        is_user = row["Engineer"] == username
        row_class = "class='user-row-highlight'" if is_user else ""
        body += f"<tr {row_class}><td>{index}</td><td>{row['Engineer']}</td><td>{(row['Best_Score']*100):.2f}%</td><td>{row['Submissions']}</td></tr>"
    return header + body + "</tbody></table>"


def generate_competitive_summary(leaderboard_df, team_name, username, last_submission_score, last_rank, submission_count):
    team_summary_df = pd.DataFrame(columns=["Team", "Best_Score", "Avg_Score", "Submissions"])
    individual_summary_df = pd.DataFrame(columns=["Engineer", "Best_Score", "Submissions"])
    if leaderboard_df is None or leaderboard_df.empty or "accuracy" not in leaderboard_df.columns:
        return ("<p style='text-align:center; color:var(--secondary-text-color, #6b7280);'>Classificació buida.</p>", "<p style='text-align:center; color:var(--secondary-text-color, #6b7280);'>Classificació buida.</p>", _build_kpi_card_html(0, 0, 0, 0, 0), 0.0, 0, 0.0)
    if "Team" in leaderboard_df.columns:
        team_summary_df = leaderboard_df.groupby("Team")["accuracy"].agg(Best_Score="max", Avg_Score="mean", Submissions="count").reset_index().sort_values("Best_Score", ascending=False).reset_index(drop=True)
        team_summary_df.index = team_summary_df.index + 1
    user_bests = leaderboard_df.groupby("username")["accuracy"].max()
    user_counts = leaderboard_df.groupby("username")["accuracy"].count()
    individual_summary_df = pd.DataFrame({"Engineer": user_bests.index, "Best_Score": user_bests.values, "Submissions": user_counts.values}).sort_values("Best_Score", ascending=False).reset_index(drop=True)
    individual_summary_df.index = individual_summary_df.index + 1
    new_rank = 0
    new_best_accuracy = 0.0
    this_submission_score = 0.0
    try:
        user_rows = leaderboard_df[leaderboard_df["username"] == username].copy()
        if not user_rows.empty:
            if "timestamp" in user_rows.columns:
                parsed_ts = pd.to_datetime(user_rows["timestamp"], errors="coerce")
                if parsed_ts.notna().any():
                    user_rows["__parsed_ts"] = parsed_ts
                    user_rows = user_rows.sort_values("__parsed_ts", ascending=False)
                    this_submission_score = float(user_rows.iloc[0]["accuracy"])
                else:
                    this_submission_score = float(user_rows.iloc[-1]["accuracy"])
            else:
                this_submission_score = float(user_rows.iloc[-1]["accuracy"])
        my_rank_row = individual_summary_df[individual_summary_df["Engineer"] == username]
        if not my_rank_row.empty:
            new_rank = my_rank_row.index[0]
            new_best_accuracy = float(my_rank_row["Best_Score"].iloc[0])
    except Exception:
        pass
    team_html = _build_team_html(team_summary_df, team_name)
    individual_html = _build_individual_html(individual_summary_df, username)
    kpi_card_html = _build_kpi_card_html(this_submission_score, last_submission_score, new_rank, last_rank, submission_count)
    return team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score


def get_model_card(model_name):
    return MODEL_TYPES.get(model_name, {}).get("card", "Descripció no disponible.")


def compute_rank_settings(submission_count, current_model, current_complexity, current_feature_set, current_data_size):
    def get_choices_for_rank(rank):
        if rank == 0:
            return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in FEATURE_SET_GROUP_1_VALS]
        if rank == 1:
            return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in (FEATURE_SET_GROUP_1_VALS + FEATURE_SET_GROUP_2_VALS)]
        return FEATURE_SET_ALL_OPTIONS
    def _model_tuples(keys):
        return [(MODEL_DISPLAY_MAP.get(k, k), k) for k in keys]
    def _data_size_tuples(keys):
        return [(DATA_SIZE_DISPLAY_MAP.get(k, k), k) for k in keys]
    if submission_count == 0:
        return {"rank_message": "# \U0001f9d1\u200d\U0001f393 Rang: Enginyer en Pràctiques\n<p style='font-size:24px; line-height:1.4;'>Per al teu primer enviament, simplement clica el botó '🔬 Construeix i Envia Model' a sota!</p>", "model_choices": _model_tuples(["The Balanced Generalist"]), "model_value": "The Balanced Generalist", "model_interactive": False, "complexity_max": 3, "complexity_value": min(current_complexity, 3), "feature_set_choices": get_choices_for_rank(0), "feature_set_value": ["floor_area", "year_built", "building_class", "facility_type"], "feature_set_interactive": False, "data_size_choices": _data_size_tuples(["Small (20%)"]), "data_size_value": "Small (20%)", "data_size_interactive": False}
    elif submission_count == 1:
        return {"rank_message": "# 🎉 Has Pujat de Rang! Enginyer Junior\n<p style='font-size:24px; line-height:1.4;'>S'han desbloquejat nous models, mides de dades i ingredients!</p>", "model_choices": _model_tuples(["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"]), "model_value": current_model if current_model in ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"] else "The Balanced Generalist", "model_interactive": True, "complexity_max": 6, "complexity_value": min(current_complexity, 6), "feature_set_choices": get_choices_for_rank(1), "feature_set_value": current_feature_set, "feature_set_interactive": True, "data_size_choices": _data_size_tuples(["Small (20%)", "Medium (60%)"]), "data_size_value": current_data_size if current_data_size in ["Small (20%)", "Medium (60%)"] else "Small (20%)", "data_size_interactive": True}
    elif submission_count == 2:
        return {"rank_message": "# 🌟 Has Pujat de Rang! Enginyer Senior\n<p style='font-size:24px; line-height:1.4;'>Ingredients de dades més potents desbloquejats! Els predictors més forts (com 'Temp. mitjana anual') ja estan disponibles. Recorda que sovint estan lligats a factors geogràfics fora del control de l'edifici.</p>", "model_choices": _model_tuples(list(MODEL_TYPES.keys())), "model_value": current_model if current_model in MODEL_TYPES else "The Deep Pattern-Finder", "model_interactive": True, "complexity_max": 8, "complexity_value": min(current_complexity, 8), "feature_set_choices": get_choices_for_rank(2), "feature_set_value": current_feature_set, "feature_set_interactive": True, "data_size_choices": _data_size_tuples(["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"]), "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)", "data_size_interactive": True}
    else:
        return {"rank_message": "# 👑 Rang: Enginyer Cap\n<p style='font-size:24px; line-height:1.4;'>Totes les eines desbloquejades — optimitza lliurement!</p>", "model_choices": _model_tuples(list(MODEL_TYPES.keys())), "model_value": current_model if current_model in MODEL_TYPES else "The Balanced Generalist", "model_interactive": True, "complexity_max": 10, "complexity_value": current_complexity, "feature_set_choices": get_choices_for_rank(3), "feature_set_value": current_feature_set, "feature_set_interactive": True, "data_size_choices": _data_size_tuples(["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"]), "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)", "data_size_interactive": True}


# ---------------------------------------------------------------------------
# Global component placeholders (populated inside app factory)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Core functions: get_or_assign_team, perform_inline_login, run_experiment
# ---------------------------------------------------------------------------
def get_or_assign_team(username, token=None):
    try:
        if playground is None:
            return _normalize_team_name(random.choice(TEAM_NAMES)), True
        leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(user_submissions["timestamp"], errors="coerce")
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                    except Exception:
                        pass
                existing_team = user_submissions.iloc[0]["Team"]
                if pd.notna(existing_team) and str(existing_team).strip():
                    return _normalize_team_name(existing_team), False
        return _normalize_team_name(random.choice(TEAM_NAMES)), True
    except Exception:
        return _normalize_team_name(random.choice(TEAM_NAMES)), True


def perform_inline_login(username_input, password_input):
    from aimodelshare.aws import get_aws_token
    if not username_input or not username_input.strip():
        error_html = "<div style='background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'><p style='margin:0; color:#991b1b; font-weight:500;'>Cal indicar el nom d'usuari</p></div>"
        return {login_username: gr.update(), login_password: gr.update(), login_submit: gr.update(), login_error: gr.update(value=error_html, visible=True), submit_button: gr.update(), submission_feedback_display: gr.update(), team_name_state: gr.update(), username_state: gr.update(), token_state: gr.update()}
    if not password_input or not password_input.strip():
        error_html = "<div style='background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'><p style='margin:0; color:#991b1b; font-weight:500;'>Cal indicar la contrasenya</p></div>"
        return {login_username: gr.update(), login_password: gr.update(), login_submit: gr.update(), login_error: gr.update(value=error_html, visible=True), submit_button: gr.update(), submission_feedback_display: gr.update(), team_name_state: gr.update(), username_state: gr.update(), token_state: gr.update()}
    username_clean = username_input.strip()
    try:
        with _auth_lock:
            os.environ["username"] = username_clean
            os.environ["password"] = password_input.strip()
            try:
                token = get_aws_token()
            finally:
                os.environ.pop("password", None)
                os.environ.pop("username", None)
                os.environ.pop("AWS_TOKEN", None)
                os.environ.pop("TEAM_NAME", None)
        team_name, is_new_team = get_or_assign_team(username_clean, token=token)
        team_name = _normalize_team_name(team_name)
        display_team = translate_team_name_for_display(team_name, UI_TEAM_LANG)
        if is_new_team:
            team_message = f"Has estat assignat/da aleatòriament a l'equip: <b>{display_team}</b>."
        else:
            team_message = f"Benvingut/da de nou! Continues a l'equip: <b>{display_team}</b>"
        success_html = f"<div style='background:#f0fdf4; padding:16px; border-radius:8px; border-left:4px solid #16a34a; margin-top:12px;'><p style='margin:0; color:#15803d; font-weight:600;'>Sessió iniciada correctament!</p><p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>{team_message}</p><p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>Clica \"Construeix i Envia Model\" de nou per publicar la teva puntuació.</p></div>"
        return {login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(value=success_html, visible=True), submit_button: gr.update(value="🔬 Construeix i Envia Model", interactive=True), submission_feedback_display: gr.update(visible=False), team_name_state: gr.update(value=team_name), username_state: gr.update(value=username_clean), token_state: gr.update(value=token)}
    except Exception as e:
        error_html = f"<div style='background:#fef2f2; padding:16px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'><p style='margin:0; color:#991b1b; font-weight:600;'>Error d'autenticació</p><p style='margin:8px 0; color:#7f1d1d;'>No s'han pogut verificar les teves credencials.</p><p style='margin:8px 0 0 0; color:#7f1d1d;'><strong>Nou usuari?</strong> Crea un compte gratuït a <a href='https://www.modelshare.ai/login' target='_blank' style='color:#dc2626; text-decoration:underline;'>modelshare.ai/login</a></p></div>"
        return {login_username: gr.update(visible=True), login_password: gr.update(visible=True), login_submit: gr.update(visible=True), login_error: gr.update(value=error_html, visible=True), submit_button: gr.update(), submission_feedback_display: gr.update(), team_name_state: gr.update(), username_state: gr.update(), token_state: gr.update()}


def run_experiment(model_name_key, complexity_level, feature_set, data_size_str, team_name, last_submission_score, last_rank, submission_count, first_submission_score, best_score, username=None, token=None, readiness_flag=None, was_preview_prev=None, progress=gr.Progress()):
    """Core experiment: Uses 'yield' for visual updates and progress bar."""
    if isinstance(submit_button, dict) or isinstance(submission_feedback_display, dict):
        yield {submission_feedback_display: gr.update(value="<p style='color:red;'>Error de Configuració</p>", visible=True), submit_button: gr.update(value="🔬 Construeix i Envia Model", interactive=True)}
        return
    sanitized_feature_set = []
    for feat in (feature_set or []):
        if isinstance(feat, dict):
            sanitized_feature_set.append(feat.get("value", str(feat)))
        elif isinstance(feat, tuple):
            sanitized_feature_set.append(feat[1] if len(feat) > 1 else str(feat))
        else:
            sanitized_feature_set.append(str(feat))
    feature_set = sanitized_feature_set
    ready = readiness_flag if readiness_flag is not None else True
    if not username:
        username = "Unknown_User"

    def get_status_html(step_num, title, subtitle):
        return f"<div class='processing-status'><span class='processing-icon'>⚙️</span><div class='processing-text'>Pas {step_num}/5: {title}</div><div class='processing-subtext'>{subtitle}</div></div>"

    progress(0.1, desc="Iniciant Experiment...")
    yield {submit_button: gr.update(value="⏳ Experiment en Curs...", interactive=False), submission_feedback_display: gr.update(value=get_status_html(1, "Inicialitzant", "Preparant els teus ingredients de dades..."), visible=True), login_error: gr.update(visible=False), attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))}

    if not model_name_key or model_name_key not in MODEL_TYPES:
        model_name_key = DEFAULT_MODEL
    complexity_level = safe_int(complexity_level, 2)

    if playground is None:
        settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
        error_msg = "<p style='text-align:center; color:red; padding:20px 0;'>No es pot connectar amb el servidor de la competició ara mateix. Torna-ho a intentar d'aquí un moment.</p>"
        yield {submission_feedback_display: gr.update(value=error_msg, visible=True), submit_button: gr.update(value="🔬 Construeix i Envia Model", interactive=True), team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True), individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False), last_submission_score_state: last_submission_score, last_rank_state: last_rank, best_score_state: best_score, submission_count_state: submission_count, first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]), login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(visible=False), attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)), was_preview_state: False, kpi_meta_state: {}, last_seen_ts_state: None}
        return

    try:
        progress(0.3, desc="Recuperant Prediccions...")
        _ensure_y_test_loaded()
        feature_tuple = tuple(sorted(feature_set))
        feature_key = ",".join(feature_tuple)
        cache_key = f"{model_name_key}|{complexity_level}|{data_size_str}|{feature_key}"
        yield {submission_feedback_display: gr.update(value=get_status_html(2, "Carregant Prediccions", "Cercant les prediccions de la teva IA..."), visible=True), login_error: gr.update(visible=False)}
        predictions = get_cached_prediction(cache_key)
        if predictions is None:
            error_html = "<div style='background:#fee2e2; padding:16px; border-radius:8px; border:2px solid #ef4444; color:#991b1b; text-align:center;'><h3 style='margin:0;'>Configuració No Trobada</h3><p style='margin:8px 0;'>Aquesta combinació de configuracions no s'ha trobat. Ajusta els paràmetres i torna-ho a intentar.</p></div>"
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            yield {submission_feedback_display: gr.update(value=error_html, visible=True), submit_button: gr.update(value="🔬 Construeix i Envia Model", interactive=True), login_error: gr.update(visible=False), rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"])}
            return
        from sklearn.metrics import accuracy_score
        local_test_accuracy = accuracy_score(_Y_TEST, predictions)

        if token is None:
            progress(0.6, desc="Calculant Puntuació de Previsualització...")
            preview_score = local_test_accuracy
            preview_card_html = _build_kpi_card_html(new_score=preview_score, last_score=0, new_rank=0, last_rank=0, submission_count=-1, is_preview=True)
            login_prompt_text_html = build_login_prompt_html()
            closing_div_index = preview_card_html.rfind("</div>")
            combined_html = preview_card_html[:closing_div_index] + login_prompt_text_html + "</div>" if closing_div_index != -1 else preview_card_html + login_prompt_text_html
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            yield {submission_feedback_display: gr.update(value=combined_html, visible=True), submit_button: gr.update(value="Cal Iniciar Sessió", interactive=False), login_username: gr.update(visible=True), login_password: gr.update(visible=True), login_submit: gr.update(visible=True), login_error: gr.update(value="", visible=False), team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True), individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False), last_submission_score_state: last_submission_score, last_rank_state: last_rank, best_score_state: best_score, submission_count_state: submission_count, first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]), attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)), was_preview_state: True, kpi_meta_state: {"was_preview": True, "preview_score": preview_score}, last_seen_ts_state: None}
            return

        if submission_count >= ATTEMPT_LIMIT:
            limit_warning_html = f"<div class='kpi-card' style='border-color:#ef4444;'><h2 style='color:var(--body-text-color, #111827); margin-top:0;'>🛑 Límit d'Enviaments Assolit</h2><div class='kpi-card-body'><div class='kpi-metric-box'><p class='kpi-label'>Intents Utilitzats</p><p class='kpi-score' style='color:#ef4444;'>{ATTEMPT_LIMIT}/{ATTEMPT_LIMIT}</p></div></div></div>"
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            yield {submission_feedback_display: gr.update(value=limit_warning_html, visible=True), submit_button: gr.update(value="🛑 Límit Assolit", interactive=False), model_type_radio: gr.update(interactive=False), complexity_slider: gr.update(interactive=False), feature_set_checkbox: gr.update(interactive=False), data_size_radio: gr.update(interactive=False), attempts_tracker_display: gr.update(value=f"<div style='text-align:center; padding:8px; margin:8px 0; background:#fef2f2; border-radius:8px; border:1px solid #ef4444;'><p style='margin:0; color:#991b1b; font-weight:600;'>🛑 Intents: {ATTEMPT_LIMIT}/{ATTEMPT_LIMIT}</p></div>"), last_submission_score_state: last_submission_score, last_rank_state: last_rank, best_score_state: best_score, submission_count_state: submission_count, first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"], login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(visible=False), was_preview_state: False, kpi_meta_state: {}, last_seen_ts_state: None}
            return

        progress(0.5, desc="Enviant al Núvol...")
        yield {submission_feedback_display: gr.update(value=get_status_html(3, "Enviant", "Enviant el model al servidor de la competició..."), visible=True), login_error: gr.update(visible=False)}
        description = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})"
        tags = f"team:{team_name},model:{model_name_key}"
        baseline_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)

        def _submit():
            return playground.submit_model(model=None, preprocessor=None, prediction_submission=predictions.tolist(), input_dict={"description": description, "tags": tags}, custom_metadata={"Team": team_name, "Moral_Compass": 0}, token=token, return_metrics=["accuracy"])

        try:
            submit_result = _retry_with_backoff(_submit, description="model submission")
            if isinstance(submit_result, tuple) and len(submit_result) == 3:
                _, _, metrics = submit_result
                this_submission_score = float(metrics["accuracy"]) if metrics and "accuracy" in metrics and metrics["accuracy"] is not None else local_test_accuracy
            else:
                this_submission_score = local_test_accuracy
        except Exception:
            this_submission_score = local_test_accuracy

        try:
            playground.get_leaderboard(token=token)
        except Exception:
            pass

        new_submission_count = submission_count + 1
        new_first_submission_score = first_submission_score
        if submission_count == 0 and first_submission_score is None:
            new_first_submission_score = this_submission_score

        progress(0.9, desc="Calculant Posició...")
        simulated_df = baseline_leaderboard_df.copy() if baseline_leaderboard_df is not None else pd.DataFrame()
        new_row = pd.DataFrame([{"username": username, "accuracy": this_submission_score, "Team": team_name, "timestamp": pd.Timestamp.now(), "version": "latest"}])
        simulated_df = pd.concat([simulated_df, new_row], ignore_index=True) if not simulated_df.empty else new_row
        team_html, individual_html, _, new_best_accuracy, new_rank, _ = generate_competitive_summary(simulated_df, team_name, username, last_submission_score, last_rank, submission_count)
        kpi_card_html = _build_kpi_card_html(new_score=this_submission_score, last_score=last_submission_score, new_rank=new_rank, last_rank=last_rank, submission_count=submission_count)

        progress(1.0, desc="Completat!")
        settings = compute_rank_settings(new_submission_count, model_name_key, complexity_level, feature_set, data_size_str)
        limit_reached = new_submission_count >= ATTEMPT_LIMIT
        if limit_reached:
            limit_html = f"<div style='margin-top:16px; border:2px solid #ef4444; background:#fef2f2; padding:16px; border-radius:12px;'><h3 style='margin:0 0 8px 0; color:#991b1b;'>🛑 Límit d'Enviaments Assolit ({ATTEMPT_LIMIT}/{ATTEMPT_LIMIT})</h3><p style='margin:0; color:#7f1d1d;'>Revisa els teus resultats i després desplaça't cap avall fins a \"Finalitzar i Reflexionar\".</p></div>"
            final_html_display = kpi_card_html + limit_html
            button_update = gr.update(value="🛑 Límit Assolit", interactive=False)
            interactive_state = False
            tracker_html = f"<div style='text-align:center; padding:8px; margin:8px 0; background:#fef2f2; border-radius:8px; border:1px solid #ef4444;'><p style='margin:0; color:#991b1b; font-weight:600;'>🛑 Intents: {ATTEMPT_LIMIT}/{ATTEMPT_LIMIT}</p></div>"
        else:
            final_html_display = kpi_card_html
            button_update = gr.update(value="🔬 Construeix i Envia Model", interactive=True)
            interactive_state = True
            tracker_html = _build_attempts_tracker_html(new_submission_count)
        yield {submission_feedback_display: gr.update(value=final_html_display, visible=True), team_leaderboard_display: team_html, individual_leaderboard_display: individual_html, last_submission_score_state: this_submission_score, last_rank_state: new_rank, best_score_state: new_best_accuracy, submission_count_state: new_submission_count, first_submission_score_state: new_first_submission_score, rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=(settings["model_interactive"] and interactive_state)), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"], interactive=interactive_state), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=(settings["feature_set_interactive"] and interactive_state)), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=(settings["data_size_interactive"] and interactive_state)), submit_button: button_update, login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(visible=False), attempts_tracker_display: gr.update(value=tracker_html), was_preview_state: False, kpi_meta_state: {"this_submission_score": this_submission_score, "new_best_accuracy": new_best_accuracy, "rank": new_rank}, last_seen_ts_state: time.time()}
    except Exception as e:
        error_msg = f"ERROR: {e}"
        _log(f"Exception in run_experiment: {error_msg}")
        settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
        yield {submission_feedback_display: gr.update(value=f"<p style='text-align:center; color:red; padding:20px 0;'>S'ha produït un error: {error_msg}</p>", visible=True), team_leaderboard_display: f"<p style='text-align:center; color:red;'>Error: {error_msg}</p>", individual_leaderboard_display: f"<p style='text-align:center; color:red;'>Error: {error_msg}</p>", last_submission_score_state: last_submission_score, last_rank_state: last_rank, best_score_state: best_score, submission_count_state: submission_count, first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]), submit_button: gr.update(value="🔬 Construeix i Envia Model", interactive=True), login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(visible=False), attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)), was_preview_state: False, kpi_meta_state: {}, last_seen_ts_state: None}


def on_initial_load(username, token=None, team_name=""):
    _ensure_y_test_loaded()
    # submission_count is always 0 on load — the limit is per-session, not lifetime.
    submission_count = 0
    if username:
        stats = _compute_user_stats(username, token)
        best_score = stats.get("best_score", 0.0)
        last_score = stats.get("last_score", 0.0)
        rank = stats.get("rank", 0)
        has_historical_submissions = stats.get("submission_count", 0) > 0
        initial_ui = compute_rank_settings(submission_count, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE)
    else:
        best_score = 0.0
        last_score = 0.0
        rank = 0
        has_historical_submissions = False
        initial_ui = compute_rank_settings(0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE)
    display_team = translate_team_name_for_display(team_name, UI_TEAM_LANG) if team_name else "El Teu Equip"
    welcome_html = f"<div style='text-align:center; padding:30px 20px;'><h3 style='margin:0 0 8px 0;'>Benvingut/da a <b>{display_team}</b>!</h3><p style='font-size:1.1rem; color:var(--secondary-text-color, #4b5563); margin:0 0 20px 0;'>El teu equip t'espera per millorar la IA.</p><div style='background:var(--color-accent-soft, #eff6ff); padding:16px; border-radius:12px; border:2px solid color-mix(in srgb, var(--color-accent, #3b82f6) 40%, transparent); display:inline-block;'><p style='margin:0; color:var(--color-accent, #1e40af); font-weight:bold;'>Clica \"Construeix i Envia Model\" per Començar!</p></div></div>"
    full_leaderboard_df = None
    try:
        if playground:
            full_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
    except Exception:
        full_leaderboard_df = None
    user_has_submitted = has_historical_submissions
    if not user_has_submitted:
        team_html = welcome_html
        individual_html = "<p style='text-align:center; color:var(--secondary-text-color, #6b7280); padding-top:40px;'>Envia el teu model per veure la teva posició!</p>"
    elif full_leaderboard_df is None or full_leaderboard_df.empty:
        team_html = _build_skeleton_leaderboard(rows=6, is_team=True)
        individual_html = _build_skeleton_leaderboard(rows=6, is_team=False)
    else:
        try:
            team_html, individual_html, _, _, _, _ = generate_competitive_summary(full_leaderboard_df, team_name, username, last_score, rank, submission_count)
        except Exception:
            team_html = "<p style='text-align:center; color:red;'>Error en renderitzar la classificació.</p>"
            individual_html = team_html
    return (get_model_card(initial_ui["model_value"]), team_html, individual_html, initial_ui["rank_message"], gr.update(choices=initial_ui["model_choices"], value=initial_ui["model_value"], interactive=initial_ui["model_interactive"]), gr.update(minimum=1, maximum=initial_ui["complexity_max"], value=initial_ui["complexity_value"]), gr.update(choices=initial_ui["feature_set_choices"], value=initial_ui["feature_set_value"], interactive=initial_ui["feature_set_interactive"]), gr.update(choices=initial_ui["data_size_choices"], value=initial_ui["data_size_value"], interactive=initial_ui["data_size_interactive"]), initial_ui["model_value"], initial_ui["complexity_value"], initial_ui["feature_set_value"], initial_ui["data_size_value"], submission_count, best_score, rank, last_score, True)


# ---------------------------------------------------------------------------
# Conclusion helpers
# ---------------------------------------------------------------------------
def build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set):
    unlocked_tiers = min(3, max(0, submissions - 1))
    tier_names = ["Practicant", "Junior", "Senior", "Cap"]
    reached = tier_names[:unlocked_tiers + 1]
    tier_line = " -> ".join([f"{t}{' (fet)' if t in reached else ''}" for t in tier_names])
    improvement = (best_score - first_score) if (first_score is not None and submissions > 1) else 0.0
    strong_predictors = {"avg_temp", "heating_degree_days", "cooling_degree_days", "january_min_temp"}
    strong_used = [f for f in feature_set if f in strong_predictors]
    tip_html = ""
    if submissions < 2:
        tip_html = "<div class='final-conclusion-tip'><b>Consell:</b> Prova almenys 2-3 enviaments canviant UN sol paràmetre cada vegada per veure causa/efecte clarament.</div>"
    attempt_cap_html = ""
    if submissions >= ATTEMPT_LIMIT:
        attempt_cap_html = f"<div class='final-conclusion-attempt-cap'><p style='margin:0;'><b>Límit d'Intents Assolit:</b> Has utilitzat els {ATTEMPT_LIMIT} intents permesos. Obrirem els enviaments de nou després de completar noves activitats.</p></div>"
    return f"""<div class="final-conclusion-root"><h1 class="final-conclusion-title">Fase d'Enginyeria Completada</h1><div class="final-conclusion-card"><h2 class="final-conclusion-subtitle">Resum del Teu Rendiment</h2><ul class="final-conclusion-list"><li>Millor Precisió: {(best_score*100):.2f}%</li><li>Posició Aconseguida: {'#' + str(rank) if rank > 0 else 'N/A'}</li><li>Enviaments Realitzats: {submissions}{' / ' + str(ATTEMPT_LIMIT) if submissions >= ATTEMPT_LIMIT else ''}</li><li>Millora sobre la Primera Puntuació: {(improvement*100):+.2f}%</li><li>Progrés de Rang: {tier_line}</li><li>Dades Més Útils Utilitzades: {len(strong_used)} ({', '.join(strong_used) if strong_used else 'Cap encara'})</li></ul>{tip_html}{attempt_cap_html}<div style="background:rgba(245,158,11,0.1); border:2px solid #f59e0b; padding:18px; border-radius:12px; margin-top:20px;"><p style="margin:0; font-size:1.05rem; line-height:1.5;"><b>Abans de celebrar...</b> Cada model d'IA té un cost més enllà de la seva puntuació de precisió. A la propera activitat, mesurarem el que el teu model realment ha costat al medi ambient.</p></div><hr class="final-conclusion-divider" /><div class="final-conclusion-next"><p style="margin:0; font-size:1.1rem; text-align:center;"><b>A continuació:</b> Descobriràs el cost ambiental ocult del model d'IA que acabes de construir.</p></div></div></div>"""


def build_conclusion_from_state(best_score, submissions, rank, first_score, feature_set):
    return build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set)


# ============================================================================
# MODULES — 6 onboarding HTML pages (converted from JSX steps 0-5)
# ============================================================================

MODULES = [
    # --- Module 0: Welcome ---
    {
        "id": 0,
        "title": "Benvinguda",
        "html": """
<div style="text-align:center; padding-top:40px;">
  <div style="font-size:64px; margin-bottom:16px;" class="ob-float">&#127959;</div>
  <div style="font-family:'Space Mono',monospace; font-size:12px; letter-spacing:4px; color:var(--a4-success); text-transform:uppercase; margin-bottom:8px;">// la teva missió</div>
  <h1 style="font-size:clamp(1.8rem,5vw,2.4rem); font-weight:800; margin:0 0 16px; background:linear-gradient(135deg,var(--a4-grad-from),var(--a4-grad-to)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; line-height:1.2; letter-spacing:-1px;">Enginyer/a d'IA</h1>
  <div style="background:var(--a4-term-bg); border:1px solid var(--a4-term-border); border-radius:16px; padding:20px 24px; margin-bottom:24px; text-align:left; color:var(--a4-text); line-height:1.6; font-size:15px;">
    <div style="font-family:'Space Mono',monospace; font-size:12px; color:var(--a4-term-text); margin-bottom:8px;">&gt; INFORME_DE_MISSIÓ</div>
    <span id="ob-typewriter-text"></span><span class="ob-blink" style="color:var(--a4-accent);">|</span>
  </div>
  <div id="ob-counter-cards" style="display:none; animation:a4FadeSlideUp 0.5s ease;">
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:20px;">
      <div class="ob-scard"><div style="font-size:28px; font-weight:800; color:var(--a4-warning);"><span id="ob-counter-emissions">0</span>%</div><div style="font-size:13px; color:var(--a4-text-dim); margin-top:4px;">de les emissions globals dels edificis</div></div>
      <div class="ob-scard"><div style="font-size:28px; font-weight:800; color:var(--a4-accent);"><span id="ob-counter-grant">0</span></div><div style="font-size:13px; color:var(--a4-text-dim); margin-top:4px;">intents per construir el millor model</div></div>
    </div>
  </div>
</div>
""",
    },
    # --- Module 1: Mission ---
    {
        "id": 1,
        "title": "La Teva Missió",
        "html": """
<div style="padding-top:24px;">
  <h2 style="font-size:24px; font-weight:800; margin:0 0 6px; color:var(--a4-accent);">&#127970; La Teva Missió</h2>
  <p style="color:var(--a4-text-dim); font-size:15px; margin:0 0 20px; line-height:1.6;">No pots auditar cada edifici manualment. La teva IA predirà quins edificis malgasten més energia utilitzant una mètrica anomenada <strong style="color:var(--a4-warning);">Site EUI</strong> (Intensitat d'Ús Energètic &mdash; una puntuació de quanta energia utilitza un edifici per metre quadrat).</p>
  <div style="background:var(--a4-card-bg); border:1px solid var(--a4-border-color); border-radius:16px; padding:20px; margin-bottom:16px; box-shadow:0 8px 24px var(--a4-card-shadow);">
    <div style="font-family:'Space Mono',monospace; font-size:12px; color:var(--a4-accent); margin-bottom:10px;">// fórmula d'intensitat d'ús energètic</div>
    <div style="background:var(--a4-formula-bg); border-radius:10px; padding:14px 20px; text-align:center; font-family:'Space Mono',monospace; font-size:15px; color:var(--a4-formula-text); font-weight:700; letter-spacing:1px;">(Electricitat + Gas) &divide; Superfície = EUI</div>
    <div style="display:flex; justify-content:space-around; margin-top:16px; text-align:center;">
      <div><div style="font-size:24px;">&#128994;</div><div style="font-size:14px; font-weight:600; color:var(--a4-success);">EUI Baix</div><div style="font-size:13px; color:var(--a4-text-dim);">Eficient</div></div>
      <div style="font-size:22px; color:var(--a4-text-dim); align-self:center;">vs</div>
      <div><div style="font-size:24px;">&#128308;</div><div style="font-size:14px; font-weight:600; color:var(--a4-error);">EUI Alt</div><div style="font-size:13px; color:var(--a4-text-dim);">Malbaratador &rarr; rehabilitar!</div></div>
    </div>
  </div>
  <div style="background:var(--a4-accent-glow); border:1px solid var(--a4-accent); border-left:4px solid var(--a4-accent); border-radius:12px; padding:14px 16px; font-size:14px; color:var(--a4-text); line-height:1.6;">&#128101; Seràs assignat/da aleatòriament a un <strong>equip</strong> d'enginyers/es. Les teves puntuacions contribueixen a la posició del teu equip a la classificació en viu.</div>
</div>
""",
    },
    # --- Module 2: Engineering Loop + Controls Explorer ---
    {
        "id": 2,
        "title": "Els Teus 4 Controls",
        "html": """
<div style="padding-top:24px;">

  <!-- Section A: El Bucle d'Enginyeria (motivació) -->
  <h2 style="font-size:24px; font-weight:800; margin:0 0 6px; color:var(--a4-accent);">&#128640; Com Millorar la Teva IA (i Pujar a la Classificació!)</h2>
  <p style="color:var(--a4-text-dim); font-size:15px; margin:0 0 16px; line-height:1.6;">Així és com treballen els enginyers d'IA reals &mdash; i així és exactament com jugaràs tu. A cada intent, ajustaràs els teus paràmetres, provaràs el resultat, aprendràs què ha funcionat i ho tornaràs a intentar.</p>

  <div style="background:var(--a4-card-bg); border:1px solid var(--a4-border-color); border-radius:16px; padding:20px; margin-bottom:16px;">
    <div style="font-family:'Space Mono',monospace; font-size:12px; color:var(--a4-accent); margin-bottom:10px;">// el bucle d'enginyeria</div>
    <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap; margin-bottom:12px;">
      <div style="background:var(--a4-term-bg); border-radius:10px; padding:10px 14px; text-align:center;"><div style="font-size:22px;">&#128295;</div><div style="font-size:13px; font-weight:700; color:var(--a4-accent); margin-top:4px;">Prova</div></div>
      <span style="color:var(--a4-text-dim); font-size:18px; align-self:center;">&rarr;</span>
      <div style="background:var(--a4-term-bg); border-radius:10px; padding:10px 14px; text-align:center;"><div style="font-size:22px;">&#128300;</div><div style="font-size:13px; font-weight:700; color:var(--a4-warning); margin-top:4px;">Testa</div></div>
      <span style="color:var(--a4-text-dim); font-size:18px; align-self:center;">&rarr;</span>
      <div style="background:var(--a4-term-bg); border-radius:10px; padding:10px 14px; text-align:center;"><div style="font-size:22px;">&#128161;</div><div style="font-size:13px; font-weight:700; color:var(--a4-success); margin-top:4px;">Aprèn</div></div>
      <span style="color:var(--a4-text-dim); font-size:18px; align-self:center;">&rarr;</span>
      <div style="background:var(--a4-term-bg); border-radius:10px; padding:10px 14px; text-align:center;"><div style="font-size:22px;">&#128257;</div><div style="font-size:13px; font-weight:700; color:var(--a4-ctrl-model); margin-top:4px;">Repeteix</div></div>
    </div>
    <div style="background:var(--a4-accent-glow); border:1px solid var(--a4-accent); border-left:4px solid var(--a4-accent); border-radius:12px; padding:12px 14px; font-size:13px; color:var(--a4-text); line-height:1.5;">&#128161; <strong>Consell pro:</strong> Canvia <strong>UN SOL</strong> paràmetre cada vegada perquè sàpigues què ha fet la diferència.</div>
  </div>

  <!-- Section B: Els Teus 4 Controls -->
  <h3 style="font-size:20px; font-weight:800; margin:0 0 6px; color:var(--a4-accent);">&#128295; Els Teus 4 Controls</h3>
  <p style="color:var(--a4-text-dim); font-size:15px; margin:0 0 16px; line-height:1.6;">Coneix els 4 paràmetres que ajustaràs a cada ronda. <strong style="color:var(--a4-warning);">&#128071; Toca cada targeta a sota</strong> per descobrir què fa &mdash; cal que exploris les 4 per continuar.</p>
  <div id="ob-ctrl-grid" style="display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-bottom:16px;"></div>
  <div id="ob-ctrl-progress" style="font-size:13px; text-align:center; color:var(--a4-text-dim); margin-bottom:12px; line-height:1.5;"></div>
  <div id="ob-ctrl-detail"></div>

</div>
""",
    },
    # --- Module 3: Rank System + Quizzes ---
    {
        "id": 3,
        "title": "Sistema de Rangs",
        "html": """
<div style="padding-top:24px;">
  <h2 style="font-size:24px; font-weight:800; margin:0 0 6px; color:var(--a4-accent);">&#127894; Puja de Rang per Desbloquejar Més</h2>
  <p style="color:var(--a4-text-dim); font-size:15px; margin:0 0 16px; line-height:1.6;">Cada enviament desbloqueja noves eines. La teva IA és avaluada amb <strong style="color:var(--a4-warning);">edificis no vistos</strong> &mdash; el 25% de les dades estan amagades en un conjunt de test.</p>
  <div id="ob-rank-bar" style="display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:20px;"></div>
  <p style="color:var(--a4-accent); font-size:14px; font-weight:600; margin:0 0 12px;">Comprovació ràpida de coneixements &mdash; respon per continuar:</p>
  <div id="ob-quiz-2"></div>
</div>
""",
    },
    # --- Module 4: Ready ---
    {
        "id": 4,
        "title": "Sistemes en Línia",
        "html": """
<div style="padding-top:24px;">
  <div style="text-align:center;">
    <div style="font-size:72px; margin-bottom:16px; animation:a4Pulse 2s ease-in-out infinite;">&#128640;</div>
    <h2 style="font-size:30px; font-weight:800; margin:0 0 20px; background:linear-gradient(135deg,var(--a4-grad-launch-from),var(--a4-grad-launch-to)); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Sistemes en Línia</h2>
  </div>

  <!-- Section 1: Workflow recap + tips -->
  <p style="color:var(--a4-text-dim); font-size:15px; margin:0 0 8px; line-height:1.6; text-align:center;">Coneixes la missió. Has practicat els controls. És hora de construir el teu primer model.</p>
  <p style="color:var(--a4-text-dim); font-size:14px; margin:0 0 12px; line-height:1.6; text-align:center;">Consell: El teu primer enviament utilitza els valors per defecte &mdash; simplement prem el botó! Després experimenta per pujar de rang.</p>
  <p style="color:var(--a4-warning); font-size:14px; font-weight:600; margin:0 0 20px; line-height:1.6; text-align:center;">Tens 10 intents per construir la millor IA possible. Fes que cada un compti!</p>
  <div style="background:var(--a4-card-bg); border:1px solid var(--a4-border-color); border-radius:20px; padding:24px; margin-bottom:24px; overflow:hidden;">
    <div style="display:flex; justify-content:center; gap:24px; flex-wrap:wrap;">
      <div style="display:flex; align-items:center; gap:8px;"><div style="text-align:center;"><div style="font-size:28px;">&#129504;</div><div style="font-size:13px; color:var(--a4-text-dim); margin-top:2px;">Tria un model</div></div><span style="color:var(--a4-text-dim); font-size:18px;">&rarr;</span></div>
      <div style="display:flex; align-items:center; gap:8px;"><div style="text-align:center;"><div style="font-size:28px;">&#9881;&#65039;</div><div style="font-size:13px; color:var(--a4-text-dim); margin-top:2px;">Ajusta la complexitat</div></div><span style="color:var(--a4-text-dim); font-size:18px;">&rarr;</span></div>
      <div style="display:flex; align-items:center; gap:8px;"><div style="text-align:center;"><div style="font-size:28px;">&#128230;</div><div style="font-size:13px; color:var(--a4-text-dim); margin-top:2px;">Tria les dades</div></div><span style="color:var(--a4-text-dim); font-size:18px;">&rarr;</span></div>
      <div style="text-align:center;"><div style="font-size:28px;">&#128300;</div><div style="font-size:13px; color:var(--a4-text-dim); margin-top:2px;">Construeix i Envia!</div></div>
    </div>
  </div>

  <!-- Section 2: La Competició -->
  <div style="background:var(--a4-card-bg); border:1px solid var(--a4-border-color); border-radius:16px; padding:20px; margin-bottom:16px;">
    <div style="font-family:'Space Mono',monospace; font-size:12px; color:var(--a4-accent); margin-bottom:10px;">// la competició</div>
    <p style="color:var(--a4-text); font-size:14px; margin:0 0 10px; line-height:1.6;">Cada enviament actualitza <strong style="color:var(--a4-accent);">dues classificacions en viu</strong> en temps real:</p>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:10px;">
      <div style="background:var(--a4-term-bg); border-radius:10px; padding:12px; text-align:center;"><div style="font-size:22px;">&#128100;</div><div style="font-size:13px; font-weight:700; color:var(--a4-accent); margin-top:4px;">Individual</div><div style="font-size:12px; color:var(--a4-text-dim); margin-top:2px;">La teva millor precisió</div></div>
      <div style="background:var(--a4-term-bg); border-radius:10px; padding:12px; text-align:center;"><div style="font-size:22px;">&#128101;</div><div style="font-size:13px; font-weight:700; color:var(--a4-success); margin-top:4px;">Equip</div><div style="font-size:12px; color:var(--a4-text-dim); margin-top:2px;">p. ex. &ldquo;Enginyers del Futur Verd&rdquo;</div></div>
    </div>
    <p style="color:var(--a4-text-dim); font-size:13px; margin:0; line-height:1.5;">La teva puntuació contribueix a la posició del teu equip &mdash; cada millora ajuda a tothom.</p>
  </div>

  <!-- Section 3: Com et Puntuen -->
  <div style="background:var(--a4-card-bg); border:1px solid var(--a4-border-color); border-radius:16px; padding:20px; margin-bottom:16px;">
    <div style="font-family:'Space Mono',monospace; font-size:12px; color:var(--a4-accent); margin-bottom:10px;">// com et puntuen</div>
    <p style="color:var(--a4-text); font-size:14px; margin:0 0 10px; line-height:1.6;">La teva IA es prova amb un <strong style="color:var(--a4-warning);">conjunt de test ocult</strong> &mdash; el 25% dels edificis que mai ha vist. Això simula el món real: el teu model ha de generalitzar a dades noves, no només memoritzar el conjunt d'entrenament.</p>
    <p style="color:var(--a4-text); font-size:14px; margin:0 0 10px; line-height:1.6;"><strong style="color:var(--a4-accent);">Precisió</strong> = el percentatge d'edificis del conjunt de test que la teva IA classifica correctament (alt vs. baix consum).</p>
    <div style="background:var(--a4-formula-bg); border-radius:10px; padding:12px 16px; text-align:center; font-family:'Space Mono',monospace; font-size:14px; color:var(--a4-formula-text); font-weight:700;">50% = atzar &nbsp;&#127922; &nbsp;&mdash;&nbsp; el teu objectiu és superar aquesta línia base</div>
  </div>
</div>
""",
    },
]


# ============================================================================
# CSS
# ============================================================================

css = r"""
/* === Onboarding CSS vars (--a4-* namespace) === */
/* Light mode is the default (matches bias detective pattern) */
:root {
  --a4-bg: #f8fafc;
  --a4-card-bg: rgba(255,255,255,0.9);
  --a4-accent: #0284c7;
  --a4-accent-glow: rgba(2,132,199,0.2);
  --a4-success: #059669;
  --a4-success-soft: rgba(5,150,105,0.12);
  --a4-warning: #d97706;
  --a4-warning-soft: rgba(217,119,6,0.12);
  --a4-error: #dc2626;
  --a4-error-soft: rgba(220,38,38,0.10);
  --a4-text: #0f172a;
  --a4-text-dim: #64748b;
  --a4-card-shadow: rgba(0,0,0,0.1);
  --a4-border-color: rgba(0,0,0,0.08);
  --a4-input-bg: rgba(0,0,0,0.02);
  --a4-hover-bg: rgba(0,0,0,0.05);
  --a4-ctrl-model: #6366f1;
  --a4-ctrl-complexity: #d97706;
  --a4-ctrl-features: #059669;
  --a4-ctrl-datasize: #db2777;
  --a4-grad-from: #0f172a; --a4-grad-to: #6366f1;
  --a4-grad-launch-from: #059669; --a4-grad-launch-to: #6366f1;
  --a4-term-bg: rgba(0,0,0,0.04); --a4-term-border: rgba(2,132,199,0.25); --a4-term-text: #0284c7;
  --a4-formula-bg: rgba(2,132,199,0.08); --a4-formula-text: #0c4a6e;
  --a4-btn-pri-bg: linear-gradient(135deg,#4f46e5,#6366f1); --a4-btn-pri-text: white; --a4-btn-pri-sh: rgba(79,70,229,0.25);
  --a4-btn-sec-bg: rgba(255,255,255,0.9); --a4-btn-sec-text: #64748b; --a4-btn-sec-bdr: rgba(0,0,0,0.1);
  --a4-btn-go-bg: linear-gradient(135deg,#047857,#059669); --a4-btn-go-text: white; --a4-btn-go-sh: rgba(5,150,105,0.25);
}

@media (prefers-color-scheme: dark) {
  :root {
    --a4-bg: #0f172a;
    --a4-card-bg: rgba(30,41,59,0.7);
    --a4-accent: #38bdf8;
    --a4-accent-glow: rgba(56,189,248,0.3);
    --a4-success: #10b981;
    --a4-success-soft: rgba(16,185,129,0.15);
    --a4-warning: #fbbf24;
    --a4-warning-soft: rgba(251,191,36,0.15);
    --a4-error: #f43f5e;
    --a4-error-soft: rgba(244,63,94,0.15);
    --a4-text: #f8fafc;
    --a4-text-dim: #94a3b8;
    --a4-card-shadow: rgba(0,0,0,0.5);
    --a4-border-color: rgba(255,255,255,0.05);
    --a4-input-bg: rgba(255,255,255,0.05);
    --a4-hover-bg: rgba(255,255,255,0.08);
    --a4-ctrl-model: #818cf8;
    --a4-ctrl-complexity: #fbbf24;
    --a4-ctrl-features: #34d399;
    --a4-ctrl-datasize: #f472b6;
    --a4-grad-from: #f8fafc; --a4-grad-to: #818cf8;
    --a4-grad-launch-from: #10b981; --a4-grad-launch-to: #818cf8;
    --a4-term-bg: rgba(0,0,0,0.3); --a4-term-border: rgba(56,189,248,0.2); --a4-term-text: #38bdf8;
    --a4-formula-bg: rgba(56,189,248,0.08); --a4-formula-text: #bae6fd;
    --a4-btn-pri-bg: linear-gradient(135deg,#6366f1,#818cf8); --a4-btn-pri-text: white; --a4-btn-pri-sh: rgba(99,102,241,0.3);
    --a4-btn-sec-bg: rgba(30,41,59,0.8); --a4-btn-sec-text: #94a3b8; --a4-btn-sec-bdr: rgba(255,255,255,0.1);
    --a4-btn-go-bg: linear-gradient(135deg,#059669,#10b981); --a4-btn-go-text: #022c22; --a4-btn-go-sh: rgba(16,185,129,0.3);
  }
}
.dark {
  --a4-bg: #0f172a;
  --a4-card-bg: rgba(30,41,59,0.7);
  --a4-accent: #38bdf8;
  --a4-accent-glow: rgba(56,189,248,0.3);
  --a4-success: #10b981;
  --a4-success-soft: rgba(16,185,129,0.15);
  --a4-warning: #fbbf24;
  --a4-warning-soft: rgba(251,191,36,0.15);
  --a4-error: #f43f5e;
  --a4-error-soft: rgba(244,63,94,0.15);
  --a4-text: #f8fafc;
  --a4-text-dim: #94a3b8;
  --a4-card-shadow: rgba(0,0,0,0.5);
  --a4-border-color: rgba(255,255,255,0.05);
  --a4-input-bg: rgba(255,255,255,0.05);
  --a4-hover-bg: rgba(255,255,255,0.08);
  --a4-ctrl-model: #818cf8;
  --a4-ctrl-complexity: #fbbf24;
  --a4-ctrl-features: #34d399;
  --a4-ctrl-datasize: #f472b6;
  --a4-grad-from: #f8fafc; --a4-grad-to: #818cf8;
  --a4-grad-launch-from: #10b981; --a4-grad-launch-to: #818cf8;
  --a4-term-bg: rgba(0,0,0,0.3); --a4-term-border: rgba(56,189,248,0.2); --a4-term-text: #38bdf8;
  --a4-formula-bg: rgba(56,189,248,0.08); --a4-formula-text: #bae6fd;
  --a4-btn-pri-bg: linear-gradient(135deg,#6366f1,#818cf8); --a4-btn-pri-text: white; --a4-btn-pri-sh: rgba(99,102,241,0.3);
  --a4-btn-sec-bg: rgba(30,41,59,0.8); --a4-btn-sec-text: #94a3b8; --a4-btn-sec-bdr: rgba(255,255,255,0.1);
  --a4-btn-go-bg: linear-gradient(135deg,#059669,#10b981); --a4-btn-go-text: #022c22; --a4-btn-go-sh: rgba(16,185,129,0.3);
}

/* Animations */
@keyframes a4FadeSlideUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
@keyframes a4FloatGlow { 0%,100% { transform:translateY(0); filter:drop-shadow(0 0 12px var(--a4-accent-glow)); } 50% { transform:translateY(-6px); filter:drop-shadow(0 0 20px var(--a4-accent-glow)); } }
@keyframes a4Pulse { 0%,100% { transform:scale(1); } 50% { transform:scale(1.05); } }
@keyframes a4Blink { 50% { opacity:0; } }

.ob-blink { animation: a4Blink 1s step-end infinite; }
.ob-float { animation: a4FloatGlow 3s ease-in-out infinite; }

/* Onboarding card */
.ob-scard { background:var(--a4-card-bg); border:1px solid var(--a4-border-color); border-radius:16px; padding:20px; text-align:center; box-shadow:0 4px 12px var(--a4-card-shadow); }

/* Gate: hidden Next buttons */
.ob-gate-hidden { display:none !important; }

/* Control explorer panels */
.ob-cpanel { background:var(--a4-card-bg); border:1px solid var(--a4-border-color); border-radius:14px; padding:16px; animation:a4FadeSlideUp 0.3s ease; }
.ob-cslider { -webkit-appearance:none; appearance:none; width:100%; height:8px; border-radius:4px; background:linear-gradient(90deg,var(--a4-success),var(--a4-warning),var(--a4-error)); outline:none; }
.ob-cslider::-webkit-slider-thumb { -webkit-appearance:none; appearance:none; width:24px; height:24px; border-radius:50%; background:var(--a4-text); border:3px solid var(--a4-bg); cursor:pointer; }
.ob-cslider::-moz-range-thumb { width:24px; height:24px; border-radius:50%; background:var(--a4-text); border:3px solid var(--a4-bg); cursor:pointer; }

/* Control grid buttons */
.ob-ctrl-btn {
  padding:16px 12px; background:var(--a4-card-bg); border:2px solid var(--a4-border-color);
  border-radius:14px; cursor:pointer; text-align:center; transition:all 0.3s ease;
  color:var(--a4-text); font-family:inherit; position:relative;
}
.ob-ctrl-btn.ob-ctrl-active { background:var(--a4-hover-bg); }

/* Quiz bubbles */
.ob-quiz-bubble { background:var(--a4-card-bg); border:2px solid var(--a4-border-color); border-radius:16px; padding:18px 20px; margin-bottom:12px; transition:border-color 0.3s ease; }
.ob-quiz-bubble.ob-quiz-correct { border-color:var(--a4-success); }
.ob-quiz-opt {
  padding:10px 14px; border-radius:10px; font-size:14px; cursor:pointer; border:2px solid var(--a4-border-color);
  background:var(--a4-input-bg); color:var(--a4-text); text-align:left; font-weight:500; transition:all 0.2s ease;
  font-family:inherit; line-height:1.5; width:100%; display:block; margin-bottom:6px;
}

/* Arena/leaderboard CSS from Activity 4 */
.kpi-card { background:var(--block-background-fill); border:2px solid var(--color-accent,#6366f1); padding:24px; border-radius:16px; text-align:center; max-width:600px; margin:auto; min-height:200px; }
.kpi-card-body { display:flex; flex-wrap:wrap; justify-content:space-around; align-items:flex-end; margin-top:24px; }
.kpi-metric-box { min-width:150px; margin:10px; }
.kpi-label { font-size:1rem; color:var(--secondary-text-color,#6b7280); margin:0; }
.kpi-score { font-size:3rem; font-weight:700; margin:0; line-height:1.1; }
.leaderboard-html-table { width:100%; border-collapse:collapse; text-align:left; font-size:1rem; min-height:300px; }
.leaderboard-html-table th { padding:12px 16px; font-size:0.9rem; font-weight:500; }
.leaderboard-html-table tbody tr { border-bottom:1px solid var(--border-color-primary,#e5e7eb); }
.leaderboard-html-table td { padding:12px 16px; }
.leaderboard-html-table .user-row-highlight { background:rgba(59,130,246,0.1); font-weight:600; }
.lb-placeholder { min-height:300px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:var(--block-background-fill); border:1px solid var(--border-color-primary,#e5e7eb); border-radius:12px; padding:40px 20px; text-align:center; }
.lb-placeholder-title { font-size:1.25rem; font-weight:500; color:var(--secondary-text-color,#6b7280); margin-bottom:8px; }
.lb-placeholder-sub { font-size:1rem; color:var(--secondary-text-color,#6b7280); }
.processing-status { background:var(--block-background-fill); border:2px solid var(--color-accent,#6366f1); border-radius:16px; padding:30px; text-align:center; animation:pulse-indigo 2s infinite; }
.processing-icon { font-size:4rem; margin-bottom:10px; display:block; animation:spin-slow 3s linear infinite; }
.processing-text { font-size:1.5rem; font-weight:700; color:var(--color-accent,#6366f1); }
.processing-subtext { font-size:1.1rem; color:var(--secondary-text-color,#6b7280); margin-top:8px; }
@keyframes pulse-indigo { 0%{box-shadow:0 0 0 0 rgba(99,102,241,0.4);} 70%{box-shadow:0 0 0 15px rgba(99,102,241,0);} 100%{box-shadow:0 0 0 0 rgba(99,102,241,0);} }
@keyframes spin-slow { from{transform:rotate(0deg);} to{transform:rotate(360deg);} }

/* Conclusion */
.final-conclusion-root { text-align:center; }
.final-conclusion-title { font-size:2.4rem; margin:0; }
.final-conclusion-card { background:var(--block-background-fill); padding:28px; border-radius:18px; border:2px solid var(--border-color-primary,#e5e7eb); margin-top:24px; max-width:950px; margin-left:auto; margin-right:auto; }
.final-conclusion-subtitle { margin-top:0; font-size:1.5rem; }
.final-conclusion-list { list-style:none; padding:0; font-size:1.05rem; text-align:left; max-width:640px; margin:20px auto; }
.final-conclusion-list li { margin:4px 0; }
.final-conclusion-tip { margin-top:16px; padding:16px; border-radius:12px; border-left:6px solid var(--color-accent,#6366f1); background:color-mix(in srgb, var(--color-accent,#6366f1) 12%, transparent); text-align:left; font-size:0.98rem; line-height:1.4; }
.final-conclusion-ethics { margin-top:16px; padding:18px; border-radius:12px; border-left:6px solid #ef4444; background:color-mix(in srgb, #ef4444 10%, transparent); text-align:left; font-size:0.98rem; line-height:1.4; }
.final-conclusion-attempt-cap { margin-top:16px; padding:16px; border-radius:12px; border-left:6px solid #ef4444; background:color-mix(in srgb, #ef4444 16%, transparent); text-align:left; font-size:0.98rem; line-height:1.4; }
.final-conclusion-divider { margin:28px 0; border:0; border-top:2px solid var(--border-color-primary,#e5e7eb); }

/* Nav loading overlay */
#nav-loading-overlay { position:fixed; top:0; left:0; width:100%; height:100%; background:color-mix(in srgb, var(--body-background-fill) 95%, transparent); z-index:9999; display:none; flex-direction:column; align-items:center; justify-content:center; opacity:0; transition:opacity 0.3s ease; }
.nav-spinner { width:50px; height:50px; border:5px solid var(--border-color-primary,#e5e7eb); border-top:5px solid var(--color-accent,#6366f1); border-radius:50%; animation:spin-slow 1s linear infinite; margin-bottom:20px; }
#nav-loading-text { font-size:1.3rem; font-weight:600; color:var(--color-accent,#6366f1); }
"""


# ============================================================================
# CLIENT_JS — onboarding interactivity (all ob-prefixed)
# ============================================================================

CLIENT_JS = r"""
/* --- Font loader --- */
(function(){
  if(!document.querySelector('link[href*="Outfit"]')){
    var l=document.createElement('link');l.rel='stylesheet';
    l.href='https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Mono:wght@400;700&display=swap';
    document.head.appendChild(l);
  }
})();

/* --- Typewriter --- */
function obTypewriter(elemId, text, speed, onDone){
  var el=document.getElementById(elemId); if(!el) return;
  var idx=0; el.textContent='';
  var t=setInterval(function(){
    idx++; el.textContent=text.slice(0,idx);
    if(idx>=text.length){clearInterval(t); if(onDone) onDone();}
  }, speed||30);
}

/* --- Counter --- */
function obCounter(elemId, target, duration, prefix, suffix){
  var el=document.getElementById(elemId); if(!el) return;
  prefix=prefix||''; suffix=suffix||'';
  var start=0, inc=target/((duration||1200)/16);
  var t=setInterval(function(){
    start+=inc;
    if(start>=target){el.textContent=prefix+target.toLocaleString()+suffix; clearInterval(t);}
    else el.textContent=prefix+Math.floor(start).toLocaleString()+suffix;
  },16);
}

/* --- Welcome init --- */
function obInitWelcome(){
  obTypewriter('ob-typewriter-text',
    "Ara et toca posar-te a la pell d'un/a Enginyer/a d'IA. La teva missió: construir un sistema d'IA que prediu quins edificis malgasten més energia — i competir amb altres enginyers/es en una classificació en viu.",
    22, function(){
      var cards=document.getElementById('ob-counter-cards');
      if(cards){cards.style.display='block';}
      obCounter('ob-counter-emissions',40,1200,'','');
      obCounter('ob-counter-grant',10,1200,'','');
    });
}

/* --- Control Explorer --- */
function obInitControlExplorer(){
  var grid=document.getElementById('ob-ctrl-grid');
  var prog=document.getElementById('ob-ctrl-progress');
  var detail=document.getElementById('ob-ctrl-detail');
  if(!grid || grid.dataset.init==='1') return;
  grid.dataset.init='1';
  var explored=new Set();
  var active=null;
  var sliderVal=5, selModel=null, selFeats=new Set(['floor_area','year_built']), selSize=null;
  var ctrls=[
    {id:'model',icon:'\uD83E\uDDE0',title:'Estrat\u00e8gia de Model',sub:'Tria el tipus de cervell de la teva IA',color:'var(--a4-ctrl-model)'},
    {id:'complexity',icon:'\u2699\uFE0F',title:'Complexitat',sub:'Fins a quin punt ha d\'aprendre?',color:'var(--a4-ctrl-complexity)'},
    {id:'features',icon:'\uD83D\uDCE6',title:'Ingredients de Dades',sub:'Quina info veu la teva IA?',color:'var(--a4-ctrl-features)'},
    {id:'datasize',icon:'\uD83D\uDCCA',title:'Mida de Dades',sub:'Quantes dades d\'entrenament?',color:'var(--a4-ctrl-datasize)'}
  ];
  function mark(id){explored.add(id); if(explored.size===4) setTimeout(function(){obUnlockNext(2);},600); renderProgress();}
  function renderProgress(){prog.innerHTML=explored.size+'/4 explorats \u2014 '+(explored.size<4?'toca cada control per aprendre\'l!':'\uD83C\uDF89 Tots explorats!');}
  function renderGrid(){
    grid.innerHTML='';
    ctrls.forEach(function(c){
      var btn=document.createElement('button');
      btn.className='ob-ctrl-btn'+(active===c.id?' ob-ctrl-active':'');
      btn.style.borderColor=(active===c.id?c.color:'var(--a4-border-color)');
      btn.innerHTML=(explored.has(c.id)?'<span style="position:absolute;top:6px;right:8px;color:var(--a4-success);font-size:14px;font-weight:700;">\u2713</span>':'')+'<div style="font-size:28px;">'+c.icon+'</div><div style="font-size:14px;font-weight:700;color:'+c.color+';margin-top:4px;">'+c.title+'</div><div style="font-size:13px;color:var(--a4-text-dim);margin-top:2px;line-height:1.4;">'+c.sub+'</div>';
      btn.onclick=function(){active=c.id; mark(c.id); renderGrid(); renderDetail();};
      grid.appendChild(btn);
    });
  }
  function renderDetail(){
    if(!active){detail.innerHTML=''; return;}
    var html='';
    if(active==='model'){
      var models=[{key:'g',name:'El Generalista Equilibrat',desc:'R\u00e0pid, fiable, equilibrat.',icon:'\u2696\uFE0F'},{key:'r',name:'El Creador de Regles',desc:'Regles simples si/aleshores.',icon:'\uD83D\uDCD0'},{key:'n',name:'El Ve\u00ed m\u00e9s Proper',desc:'Troba exemples passats similars.',icon:'\uD83D\uDD0D'},{key:'d',name:'El Detector de Patrons Profunds',desc:'Conjunt potent.',icon:'\uD83C\uDF32'}];
      html='<div class="ob-cpanel"><h4 style="margin:0 0 8px;color:var(--a4-ctrl-model);font-size:15px;">\uD83E\uDDE0 Tria un cervell per a la teva IA:</h4><div style="display:flex;flex-direction:column;gap:6px;">';
      models.forEach(function(m){
        var on=selModel===m.key;
        html+='<button onclick="window._obSelModel=\''+m.key+'\';obRefreshCtrl();" style="padding:12px 14px;background:'+(on?'var(--a4-accent-glow)':'var(--a4-input-bg)')+';border:2px solid '+(on?'var(--a4-accent)':'var(--a4-border-color)')+';border-radius:10px;cursor:pointer;text-align:left;display:flex;gap:10px;align-items:center;color:var(--a4-text);font-family:inherit;transition:all 0.2s ease;"><span style="font-size:22px;">'+m.icon+'</span><div><div style="font-size:14px;font-weight:600;">'+m.name+'</div><div style="font-size:13px;color:var(--a4-text-dim);line-height:1.4;">'+m.desc+'</div></div></button>';
      });
      html+='</div></div>';
    } else if(active==='complexity'){
      var cDesc=sliderVal<=3?'Conservador \u2014 apr\u00e8n patrons amplis. Segur i estable.':sliderVal<=7?'Equilibrat \u2014 patrons \u00fatils sense memoritzar soroll.':'Agressiu \u2014 arrisca memoritzar les respostes en lloc d\'aprendre!';
      var cColor=sliderVal<=3?'var(--a4-success)':sliderVal<=7?'var(--a4-warning)':'var(--a4-error)';
      html='<div class="ob-cpanel"><h4 style="margin:0 0 12px;color:var(--a4-ctrl-complexity);font-size:15px;">\u2699\uFE0F Fins a quin punt ha d\'aprendre la teva IA?</h4><input type="range" min="1" max="10" value="'+sliderVal+'" class="ob-cslider" oninput="window._obSliderVal=Number(this.value);obRefreshCtrl();"><div style="display:flex;justify-content:space-between;font-size:12px;color:var(--a4-text-dim);margin-top:4px;"><span>Simple</span><span>Equilibrat</span><span>Agressiu</span></div><div style="margin-top:12px;padding:10px 14px;border-radius:10px;background:var(--a4-input-bg);border:1px solid var(--a4-border-color);font-size:13px;color:'+cColor+';font-weight:500;line-height:1.5;">Nivell '+sliderVal+': '+cDesc+'</div></div>';
    } else if(active==='features'){
      var feats=[{key:'floor_area',name:'Superf\u00edcie'},{key:'year_built',name:'Any Construcci\u00f3'},{key:'building_class',name:'Tipus Edifici'},{key:'facility_type',name:'Tipus Instal\u00b7laci\u00f3'},{key:'State_Factor',name:'Info Ubicaci\u00f3'},{key:'ELEVATION',name:'Altitud'},{key:'avg_temp',name:'Temp. Mitjana'},{key:'heating_degree_days',name:'Dies Calefacci\u00f3'}];
      html='<div class="ob-cpanel"><h4 style="margin:0 0 8px;color:var(--a4-ctrl-features);font-size:15px;">\uD83D\uDCE6 Activa/desactiva ingredients de dades:</h4><div style="display:flex;flex-wrap:wrap;gap:6px;">';
      feats.forEach(function(f){
        var on=selFeats.has(f.key);
        html+='<button onclick="window._obToggleFeat(\''+f.key+'\');obRefreshCtrl();" style="padding:8px 12px;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;border:2px solid '+(on?'var(--a4-ctrl-features)':'var(--a4-border-color)')+';background:'+(on?'var(--a4-hover-bg)':'transparent')+';color:'+(on?'var(--a4-text)':'var(--a4-text-dim)')+';font-family:inherit;transition:all 0.2s ease;">'+(on?'\u2713 ':'')+f.name+'</button>';
      });
      html+='</div><div style="font-size:13px;color:var(--a4-text-dim);margin-top:8px;line-height:1.5;">\uD83D\uDD12 M\u00e9s ingredients es desbloquegen en pujar de rang!</div></div>';
    } else if(active==='datasize'){
      var sizes=[{key:'s',label:'Petita (20%)',desc:'Experiments r\u00e0pids',pct:20},{key:'m',label:'Mitjana (60%)',desc:'Velocitat i precisi\u00f3 equilibrades',pct:60},{key:'l',label:'Gran (80%)',desc:'Millors patrons',pct:80},{key:'f',label:'Completa (100%)',desc:'M\u00e0xim de dades',pct:100}];
      html='<div class="ob-cpanel"><h4 style="margin:0 0 8px;color:var(--a4-ctrl-datasize);font-size:15px;">\uD83D\uDCCA Quanta hist\u00f2ria ha d\'estudiar la teva IA?</h4><div style="display:flex;flex-direction:column;gap:6px;">';
      sizes.forEach(function(d){
        var on=selSize===d.key;
        html+='<button onclick="window._obSelSize=\''+d.key+'\';obRefreshCtrl();" style="padding:12px 14px;background:'+(on?'var(--a4-hover-bg)':'var(--a4-input-bg)')+';border:2px solid '+(on?'var(--a4-ctrl-datasize)':'var(--a4-border-color)')+';border-radius:10px;cursor:pointer;text-align:left;color:var(--a4-text);font-family:inherit;transition:all 0.2s ease;"><div style="display:flex;justify-content:space-between;align-items:center;"><div><div style="font-size:14px;font-weight:600;">'+d.label+'</div><div style="font-size:13px;color:var(--a4-text-dim);line-height:1.4;">'+d.desc+'</div></div><div style="width:44px;height:44px;border-radius:50%;background:conic-gradient(var(--a4-ctrl-datasize) '+(d.pct*3.6)+'deg, var(--a4-input-bg) '+(d.pct*3.6)+'deg);display:flex;align-items:center;justify-content:center;flex-shrink:0;"><span style="width:34px;height:34px;border-radius:50%;background:var(--a4-bg,#f8fafc);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:var(--a4-ctrl-datasize);">'+d.pct+'%</span></div></div></button>';
      });
      html+='</div><div style="font-size:13px;color:var(--a4-text-dim);margin-top:8px;line-height:1.5;">\uD83D\uDCA1 Consell: Usa "Petita" per provar r\u00e0pid. Usa "Completa" per una combinaci\u00f3 guanyadora.</div></div>';
    }
    detail.innerHTML=html;
  }
  // Expose helpers
  window._obSelModel=selModel; window._obSliderVal=sliderVal; window._obSelSize=selSize;
  window._obToggleFeat=function(key){if(selFeats.has(key)) selFeats.delete(key); else selFeats.add(key);};
  window.obRefreshCtrl=function(){
    selModel=window._obSelModel; sliderVal=window._obSliderVal; selSize=window._obSelSize;
    renderGrid(); renderDetail();
  };
  renderProgress(); renderGrid();
}

/* --- Quizzes --- */
function obInitQuizzes(){
  var q2=document.getElementById('ob-quiz-2');
  if(!q2 || q2.dataset.init==='1') return;
  q2.dataset.init='1';
  function buildQuiz(container, question, options, correctIdx, onCorrect){
    container.innerHTML='';
    var bubble=document.createElement('div'); bubble.className='ob-quiz-bubble';
    var p=document.createElement('p'); p.style.cssText='margin:0 0 10px;font-weight:600;font-size:15px;color:var(--a4-text);line-height:1.5;'; p.textContent=question;
    bubble.appendChild(p);
    var selected=null;
    options.forEach(function(opt,i){
      var btn=document.createElement('button'); btn.className='ob-quiz-opt'; btn.textContent=opt;
      btn.onclick=function(){
        if(selected===correctIdx) return;
        selected=i;
        // Reset all
        Array.from(bubble.querySelectorAll('.ob-quiz-opt')).forEach(function(b,j){
          if(j===i && j===correctIdx){b.style.borderColor='var(--a4-success)';b.style.background='var(--a4-success-soft)';b.style.color='var(--a4-success)';b.textContent='\u2705 '+opt;}
          else if(j===i){b.style.borderColor='var(--a4-error)';b.style.background='var(--a4-error-soft)';b.style.color='var(--a4-error)';b.textContent='\u274C '+options[j];}
          else{b.style.borderColor='var(--a4-border-color)';b.style.background='var(--a4-input-bg)';b.style.color='var(--a4-text)';b.textContent=options[j];}
        });
        if(i===correctIdx){bubble.classList.add('ob-quiz-correct'); setTimeout(function(){onCorrect();},500);}
        else{
          var err=bubble.querySelector('.ob-quiz-err');
          if(!err){err=document.createElement('p');err.className='ob-quiz-err';err.style.cssText='margin:8px 0 0;font-size:13px;color:var(--a4-warning);line-height:1.5;';bubble.appendChild(err);}
          err.textContent='No del tot \u2014 torna-ho a intentar!';
        }
      };
      bubble.appendChild(btn);
    });
    container.appendChild(bubble);
  }
  function checkQuiz(){ obUnlockNext(3); }
  buildQuiz(q2,"Qu\u00e8 passa quan puges de rang?",["Res no canvia","La teva puntuaci\u00f3 es reinicia a zero","Es desbloquegen nous models, ingredients i mides de dades"],2,checkQuiz);
}

/* --- Rank bar init --- */
function obInitRankBar(){
  var bar=document.getElementById('ob-rank-bar');
  if(!bar || bar.dataset.init==='1') return;
  bar.dataset.init='1';
  var ranks=[
    {i:'\uD83C\uDF31',r:'Enginyer/a Practicant',c:'var(--a4-text-dim)',d:'1 model, complexitat \u22643, dades petites'},
    {i:'\uD83C\uDFE2',r:'Enginyer/a Junior',c:'var(--a4-accent)',d:'3 models, complexitat \u22646, + ubicaci\u00f3'},
    {i:'\u2B50',r:'Enginyer/a Senior',c:'var(--a4-ctrl-model)',d:'Tots els models, complexitat \u22648, + clima'},
    {i:'\uD83D\uDC51',r:'Enginyer/a Cap',c:'var(--a4-warning)',d:'Totes les eines, complexitat \u226410'}
  ];
  var html='';
  ranks.forEach(function(x){
    html+='<div style="background:var(--a4-card-bg);border:2px solid var(--a4-border-color);border-radius:16px;padding:16px 10px;text-align:center;">'
      +'<div style="font-size:2rem;margin-bottom:6px;">'+x.i+'</div>'
      +'<div style="font-size:0.95rem;font-weight:800;color:'+x.c+';line-height:1.3;">'+x.r+'</div>'
      +'<div style="font-size:0.8rem;color:var(--a4-text-dim);margin-top:6px;line-height:1.4;">'+x.d+'</div>'
      +'</div>';
  });
  bar.innerHTML=html;
}

/* --- Gate unlock --- */
function obUnlockNext(moduleIdx){
  /* Find the Next button for this module and remove ob-gate-hidden */
  var btns=document.querySelectorAll('[class*="ob-gate-'+moduleIdx+'"]');
  btns.forEach(function(b){b.classList.remove('ob-gate-hidden');b.classList.remove('ob-gate-'+moduleIdx);});
  /* Also try by elem_classes pattern that Gradio renders */
  document.querySelectorAll('.ob-gate-'+moduleIdx).forEach(function(el){el.classList.remove('ob-gate-hidden');el.classList.remove('ob-gate-'+moduleIdx);});
}

/* --- Init polling IIFEs --- */
(function obPollWelcome(){
  if(document.getElementById('ob-typewriter-text')){obInitWelcome();}
  else{setTimeout(obPollWelcome,200);}
})();
(function obPollCtrl(){
  if(document.getElementById('ob-ctrl-grid') && !document.getElementById('ob-ctrl-grid').dataset.init){obInitControlExplorer();}
  else{setTimeout(obPollCtrl,300);}
})();
(function obPollQuiz(){
  if(document.getElementById('ob-quiz-2') && !document.getElementById('ob-quiz-2').dataset.init){obInitQuizzes(); obInitRankBar();}
  else{setTimeout(obPollQuiz,300);}
})();

/* --- Re-init after back-navigation (Gradio may re-render HTML, wiping dynamic content) --- */
function obReinitAll(){
  var tw=document.getElementById('ob-typewriter-text');
  if(tw && !tw.textContent.trim()){obInitWelcome();}
  var grid=document.getElementById('ob-ctrl-grid');
  if(grid && grid.children.length===0){delete grid.dataset.init; obInitControlExplorer();}
  var q2=document.getElementById('ob-quiz-2');
  if(q2 && q2.children.length===0){delete q2.dataset.init; obInitQuizzes(); obInitRankBar();}
}
"""


# ============================================================================
# HEAD_HTML
# ============================================================================

HEAD_HTML = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Mono:wght@400;700&display=swap">\n'
    '<script>\n' + CLIENT_JS + '\n</script>'
)


# ============================================================================
# APP FACTORY
# ============================================================================
def create_model_building_game_ca_sustainability_app(theme_primary_hue="indigo"):
    """Build the Gradio Blocks app with onboarding modules + arena + conclusion."""
    global playground
    if playground is None:
        try:
            playground = Competition(MY_PLAYGROUND_ID)
        except Exception as e:
            print(f"WARNING: Could not connect to playground: {e}")
            playground = None

    # Declare globals that run_experiment and perform_inline_login yield into
    global submit_button, submission_feedback_display, team_leaderboard_display
    global individual_leaderboard_display, last_submission_score_state, last_rank_state
    global best_score_state, submission_count_state, first_submission_score_state
    global rank_message_display, model_type_radio, complexity_slider
    global feature_set_checkbox, data_size_radio
    global login_username, login_password, login_submit, login_error
    global attempts_tracker_display, team_name_state
    global username_state, token_state, readiness_state
    global was_preview_state, kpi_meta_state, last_seen_ts_state

    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue=theme_primary_hue),
        css=css,
        head=HEAD_HTML,
    ) as demo:

        # Top anchor for scroll-to-top
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")

        # Navigation loading overlay
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Carregant...</span>
            </div>
        """)

        # ── Loader column (shown until JS kicks in) ──────────────────────
        with gr.Column(visible=True, elem_id="ob-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:120px 0;'>"
                "<h2 style='font-size:2rem; color:var(--a4-text-dim,#6b7280);'>Carregant...</h2>"
                "</div>"
            )

        # ── Main app column ──────────────────────────────────────────────
        with gr.Column(visible=False) as main_app_col:

            # ---------- Onboarding modules (0-5) ----------
            module_cols = []
            module_next_btns = []
            module_back_btns = []

            GATED_MODULES = {2, 3}  # controls, quizzes

            for i, mod in enumerate(MODULES):
                visible = (i == 0)
                with gr.Column(visible=visible, elem_id=f"ob-mod-{i}") as col:
                    gr.HTML(mod["html"])

                    with gr.Row():
                        if i > 0:
                            back_btn = gr.Button("Enrere", size="lg")
                        else:
                            back_btn = gr.Button("Enrere", size="lg", visible=False)

                        if i < len(MODULES) - 1:
                            extra_classes = [f"ob-gate-hidden", f"ob-gate-{i}"] if i in GATED_MODULES else []
                            next_btn = gr.Button("Següent", variant="primary", size="lg",
                                                 elem_classes=extra_classes if extra_classes else None)
                        else:
                            # Module 4 (Ready) → "Enter the Arena"
                            next_btn = gr.Button("Entrar a l'Arena", variant="primary", size="lg")

                    module_cols.append(col)
                    module_next_btns.append(next_btn)
                    module_back_btns.append(back_btn)

            # ---------- Arena column ----------
            with gr.Column(visible=False, elem_id="model-step") as arena_col:
                gr.Markdown("<h1 style='text-align:center;'>Arena de Construcció de Models</h1>")

                # Session auth state objects
                username_state = gr.State(None)
                token_state = gr.State(None)
                team_name_state = gr.State(None)
                last_submission_score_state = gr.State(0.0)
                last_rank_state = gr.State(0)
                best_score_state = gr.State(0.0)
                submission_count_state = gr.State(0)
                first_submission_score_state = gr.State(None)
                readiness_state = gr.State(False)
                was_preview_state = gr.State(False)
                kpi_meta_state = gr.State({})
                last_seen_ts_state = gr.State(None)

                # Buffered states for dynamic inputs
                model_type_state = gr.State(DEFAULT_MODEL)
                complexity_state = gr.State(2)
                feature_set_state = gr.State(DEFAULT_FEATURE_SET)
                data_size_state = gr.State(DEFAULT_DATA_SIZE)

                rank_message_display = gr.Markdown("### Carregant rang...")

                with gr.Row():
                    with gr.Column(scale=1):
                        model_type_radio = gr.Radio(
                            label="1. Estratègia de Model",
                            choices=[(MODEL_DISPLAY_MAP.get(k, k), k) for k in MODEL_TYPES.keys()],
                            value=DEFAULT_MODEL,
                            interactive=False
                        )
                        model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL))
                        gr.Markdown("---")

                        complexity_slider = gr.Slider(
                            label="2. Profunditat del Model (1 = regles simples, 10 = patrons molt detallats)",
                            minimum=1, maximum=3, step=1, value=2,
                            info="Baix = la teva IA aprèn regles simples i segures. Alt = intenta aprendre cada petit detall, però pot confondre's amb el soroll."
                        )
                        complexity_tooltip = gr.HTML(
                            value="<div style='background:var(--background-fill-secondary); padding:10px 14px; border-radius:8px; border:1px solid var(--border-color-primary); margin-top:4px; font-size:0.9rem;'><b>Nivell 2:</b> Equilibrat — el teu model aprèn patrons útils sense memoritzar les dades.</div>"
                        )
                        gr.Markdown("---")

                        feature_set_checkbox = gr.CheckboxGroup(
                            label="3. Selecciona Ingredients de Dades",
                            choices=FEATURE_SET_ALL_OPTIONS,
                            value=DEFAULT_FEATURE_SET,
                            interactive=False,
                            info="Més ingredients es desbloquegen en pujar de rang!"
                        )
                        gr.Markdown("---")

                        data_size_radio = gr.Radio(
                            label="4. Mida de Dades",
                            choices=[(DATA_SIZE_DISPLAY_MAP.get(DEFAULT_DATA_SIZE, DEFAULT_DATA_SIZE), DEFAULT_DATA_SIZE)],
                            value=DEFAULT_DATA_SIZE,
                            interactive=False
                        )
                        gr.Markdown("---")

                        attempts_tracker_display = gr.HTML(
                            value="<div style='text-align:center; padding:8px; margin:8px 0; background:#f0f9ff; border-radius:8px; border:1px solid #bae6fd;'>"
                            "<p style='margin:0; color:#0369a1; font-weight:600; font-size:1rem;'>Intents utilitzats: 0/10</p>"
                            "</div>",
                            visible=True
                        )

                        submit_button = gr.Button(
                            value="5. Construeix i Envia Model",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column(scale=1):
                        gr.HTML(
                            "<div class='leaderboard-box'>"
                            "<h3 style='margin-top:0;'>Classificació en Viu</h3>"
                            "<p style='margin:0;'>Envia un model per veure la teva posició.</p>"
                            "</div>"
                        )

                        submission_feedback_display = gr.HTML(
                            "<p style='text-align:center; color:var(--secondary-text-color, #6b7280); padding:20px 0;'>Envia el teu primer model per rebre comentaris!</p>"
                        )

                        # Inline login (hidden by default)
                        login_username = gr.Textbox(label="Nom d'usuari",
                                                    placeholder="Introdueix el teu nom d'usuari de modelshare.ai",
                                                    visible=False)
                        login_password = gr.Textbox(label="Contrasenya", type="password",
                                                    placeholder="Introdueix la teva contrasenya",
                                                    visible=False)
                        login_submit = gr.Button("Inicia Sessió i Envia", variant="primary",
                                                 visible=False)
                        login_error = gr.HTML(value="", visible=False)

                        with gr.Tabs():
                            with gr.TabItem("Classificació per Equips"):
                                team_leaderboard_display = gr.HTML(
                                    "<p style='text-align:center; color:var(--secondary-text-color, #6b7280); padding-top:20px;'>Envia un model per veure la classificació per equips.</p>"
                                )
                            with gr.TabItem("Classificació Individual"):
                                individual_leaderboard_display = gr.HTML(
                                    "<p style='text-align:center; color:var(--secondary-text-color, #6b7280); padding-top:20px;'>Envia un model per veure la classificació individual.</p>"
                                )

                with gr.Row():
                    arena_back_btn = gr.Button("Tornar a les Instruccions", size="lg")
                    arena_finish_btn = gr.Button("Finalitzar i Reflexionar", variant="secondary", size="lg")

            # ---------- Conclusion column ----------
            with gr.Column(visible=False, elem_id="conclusion-step") as conclusion_col:
                gr.Markdown("<h1 style='text-align:center;'>Secció Completada</h1>")
                final_score_display = gr.HTML(value="<p>Preparant resum final...</p>")
                conclusion_back_btn = gr.Button("Tornar a l'Experiment")
                proceed_next_btn = gr.Button("CONTINUAR A L'ACTIVITAT 5 →", variant="primary", size="lg")

        # ==================================================================
        # NAVIGATION WIRING
        # ==================================================================

        all_panels = module_cols + [arena_col, conclusion_col, loader_col]

        def make_nav(target):
            """Return fn that shows *target* and hides everything else."""
            def _nav():
                return [gr.update(visible=(p is target)) for p in all_panels]
            return _nav

        def nav_js(target_id, message, min_show_ms=1200, notify_parent=False):
            notification_code = ""
            if notify_parent:
                notification_code = "try { window.parent.postMessage('model-updated', '*'); } catch(e) { console.warn(e); }"
            return f"""
            ()=>{{
              {notification_code}
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
                  const container = document.querySelector('.gradio-container') || document.scrollingElement || document.documentElement;
                  function doScroll() {{
                    if(anchor) {{ anchor.scrollIntoView({{behavior:'smooth', block:'start'}}); }}
                    else {{ container.scrollTo({{top:0, behavior:'smooth'}}); }}
                    try {{
                      if(window.parent && window.parent !== window && window.frameElement) {{
                        const top = window.frameElement.getBoundingClientRect().top + window.parent.scrollY;
                        window.parent.scrollTo({{top: Math.max(top - 10, 0), behavior:'smooth'}});
                      }}
                    }} catch(e2) {{}}
                  }}
                  doScroll();
                  let scrollAttempts = 0;
                  const scrollInterval = setInterval(() => {{
                    scrollAttempts++;
                    doScroll();
                    if(scrollAttempts >= 3) clearInterval(scrollInterval);
                  }}, 130);
                }}, 40);
                const targetId = '{target_id}';
                const minShowMs = {min_show_ms};
                let pollCount = 0;
                const maxPolls = 77;
                const pollInterval = setInterval(() => {{
                  pollCount++;
                  const elapsed = Date.now() - startTime;
                  const target = document.getElementById(targetId);
                  const isVisible = target && target.offsetParent !== null &&
                                       window.getComputedStyle(target).display !== 'none';
                  if((isVisible && elapsed >= minShowMs) || pollCount >= maxPolls) {{
                    clearInterval(pollInterval);
                    if(overlay) {{
                      overlay.style.opacity = '0';
                      setTimeout(() => {{ overlay.style.display = 'none'; }}, 300);
                    }}
                    setTimeout(function(){{ if(typeof obReinitAll==='function') obReinitAll(); }}, 300);
                  }}
                }}, 90);
              }} catch(e) {{ console.warn('nav-js error', e); }}
            }}
            """

        # --- Module prev/next ---
        for i in range(len(MODULES)):
            # Next button
            if i < len(MODULES) - 1:
                module_next_btns[i].click(
                    fn=make_nav(module_cols[i + 1]),
                    inputs=None, outputs=all_panels,
                    show_progress="hidden",
                    js=nav_js(f"ob-mod-{i+1}", "Carregant la secció següent...")
                )
            else:
                # Last module → Arena
                module_next_btns[i].click(
                    fn=make_nav(arena_col),
                    inputs=None, outputs=all_panels,
                    show_progress="hidden",
                    js=nav_js("model-step", "Entrant a l'arena de models...")
                )
            # Back button
            if i > 0:
                module_back_btns[i].click(
                    fn=make_nav(module_cols[i - 1]),
                    inputs=None, outputs=all_panels,
                    show_progress="hidden",
                    js=nav_js(f"ob-mod-{i-1}", "Tornant enrere...")
                )

        # Arena back → last onboarding module
        arena_back_btn.click(
            fn=make_nav(module_cols[-1]),
            inputs=None, outputs=all_panels,
            show_progress="hidden",
            js=nav_js(f"ob-mod-{len(MODULES)-1}", "Tornant a les instruccions...")
        )

        # Arena finish → Conclusion
        def finalize_and_show_conclusion(best_score, submissions, rank, first_score, feature_set):
            html = build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set)
            vis = [gr.update(visible=(p is conclusion_col)) for p in all_panels]
            return vis + [html]

        arena_finish_btn.click(
            fn=finalize_and_show_conclusion,
            inputs=[best_score_state, submission_count_state, last_rank_state,
                    first_submission_score_state, feature_set_state],
            outputs=all_panels + [final_score_display],
            show_progress="hidden",
            js=nav_js("conclusion-step", "Generant resum de rendiment...")
        )

        # Conclusion back → Arena
        conclusion_back_btn.click(
            fn=make_nav(arena_col),
            inputs=None, outputs=all_panels,
            show_progress="hidden",
            js=nav_js("model-step", "Tornant a l'espai de treball de l'experiment...")
        )

        # Navigate to next activity
        proceed_next_btn.click(
            fn=None,
            js="() => { try { window.parent.postMessage('navigate-to-activity-5', '*'); } catch(e) {} }"
        )

        # ==================================================================
        # ARENA CONTROL EVENTS
        # ==================================================================

        model_type_radio.change(fn=get_model_card, inputs=model_type_radio, outputs=model_card_display, show_progress="hidden")
        model_type_radio.change(fn=lambda v: v or DEFAULT_MODEL, inputs=model_type_radio, outputs=model_type_state, show_progress="hidden")

        def _complexity_tooltip(v):
            if v <= 3:
                desc = "Patrons generals — el teu model aprèn regles àmplies. Punt de partida segur."
            elif v <= 7:
                desc = "Equilibrat — el teu model aprèn patrons útils sense memoritzar les dades."
            else:
                desc = "Memoritzant detalls — alta precisió amb dades d'entrenament, però arriscat amb edificis nous."
            return f"<div style='background:var(--background-fill-secondary); padding:10px 14px; border-radius:8px; border:1px solid var(--border-color-primary); margin-top:4px; font-size:0.9rem;'><b>Nivell {int(v)}:</b> {desc}</div>"

        complexity_slider.change(fn=lambda v: v, inputs=complexity_slider, outputs=complexity_state, show_progress="hidden")
        complexity_slider.change(fn=_complexity_tooltip, inputs=complexity_slider, outputs=complexity_tooltip, show_progress="hidden")
        feature_set_checkbox.change(fn=lambda v: v or [], inputs=feature_set_checkbox, outputs=feature_set_state, show_progress="hidden")
        data_size_radio.change(fn=lambda v: v or DEFAULT_DATA_SIZE, inputs=data_size_radio, outputs=data_size_state, show_progress="hidden")

        # All outputs that run_experiment yields into
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

        # Wire login
        login_submit.click(
            fn=perform_inline_login,
            inputs=[login_username, login_password],
            outputs=[
                login_username, login_password, login_submit, login_error,
                submit_button, submission_feedback_display,
                team_name_state, username_state, token_state
            ]
        )

        # Wire submit
        submit_button.click(
            fn=run_experiment,
            inputs=[
                model_type_state, complexity_state, feature_set_state, data_size_state,
                team_name_state, last_submission_score_state, last_rank_state,
                submission_count_state, first_submission_score_state, best_score_state,
                username_state, token_state, readiness_state, was_preview_state,
            ],
            outputs=all_outputs,
            show_progress="full",
            js=nav_js("model-step", "Executant experiment...", 500, notify_parent=False),
            api_name="predict"
        ).then(
            fn=None, inputs=None, outputs=None,
            js="() => { try { window.parent.postMessage('model-updated', '*'); console.log('Submission complete. Notifying parent.'); } catch(e) { console.warn(e); } }"
        )

        # ==================================================================
        # SESSION AUTH ON LOAD
        # ==================================================================

        def handle_load_with_session_auth(request: "gr.Request"):
            success, username, token = _try_session_based_auth(request)
            if success and username and token:
                _log(f"Session auth successful on load for {username}")
                stats = _compute_user_stats(username, token)
                team_name = stats.get("team_name", "")
                initial_results = on_initial_load(username, token=token, team_name=team_name)
                return initial_results + (
                    gr.update(visible=False),  # login_username
                    gr.update(visible=False),  # login_password
                    gr.update(visible=False),  # login_submit
                    gr.update(visible=False),  # login_error
                    username,                  # username_state
                    token,                     # token_state
                    team_name,                 # team_name_state
                    gr.update(visible=False),  # loader_col
                    gr.update(visible=True),   # main_app_col
                )
            else:
                _log("No valid session on load, showing login form")
                initial_results = on_initial_load(None, token=None, team_name="")
                return initial_results + (
                    gr.update(visible=True),   # login_username
                    gr.update(visible=True),   # login_password
                    gr.update(visible=True),   # login_submit
                    gr.update(visible=False),  # login_error
                    None,                      # username_state
                    None,                      # token_state
                    "",                        # team_name_state
                    gr.update(visible=False),  # loader_col
                    gr.update(visible=True),   # main_app_col
                )

        demo.load(
            fn=handle_load_with_session_auth,
            inputs=None,
            show_progress="hidden",
            outputs=[
                # on_initial_load returns 17 values:
                model_card_display,
                team_leaderboard_display,
                individual_leaderboard_display,
                rank_message_display,
                model_type_radio,
                complexity_slider,
                feature_set_checkbox,
                data_size_radio,
                model_type_state,
                complexity_state,
                feature_set_state,
                data_size_state,
                submission_count_state,
                best_score_state,
                last_rank_state,
                last_submission_score_state,
                readiness_state,
                # Session auth (7):
                login_username,
                login_password,
                login_submit,
                login_error,
                username_state,
                token_state,
                team_name_state,
                # Loader / main visibility (2):
                loader_col,
                main_app_col,
            ],
            js="() => { try { window.parent.postMessage('app-ready', '*'); } catch(e) {} }",
        )

    return demo


# -------------------------------------------------------------------------
# 4. Convenience Launcher
# -------------------------------------------------------------------------

def launch_model_building_game_ca_sustainability_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    """
    Create and directly launch the Model Building Game app v5.0 (Catalan).
    """
    global playground
    if playground is None:
        try:
            playground = Competition(MY_PLAYGROUND_ID)
        except Exception as e:
            print(f"WARNING: Could not connect to playground: {e}")
            playground = None

    demo = create_model_building_game_ca_sustainability_app()

    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

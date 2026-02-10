"""
Activity 9 V2 — Interactive Onboarding + Model Building Arena (Final Challenge).

Replaces the static intro slide with an interactive onboarding converted
from final_onboarding.jsx.  The arena and conclusion use the REAL Gradio-powered
model building code from Activity 9 (dual-DB SQLite cache, session auth,
run_experiment, majority vote ensemble, playground API, leaderboard).

All tools unlocked from the start. 5 models (incl. Majority Vote), 14 features,
4 data sizes, unlimited attempts. Rank is always "Chief Climate Architect".

Port: 8084
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

# ---------------------------------------------------------------------------
# Cache Configuration (Thread-Safe SQLite with Dual-DB Support)
# ---------------------------------------------------------------------------
import sqlite3

CACHE_DB_FILE_BASE = "prediction_cache.sqlite"
CACHE_DB_FILE_FULL = "prediction_cache_full.sqlite"


def _get_cached_prediction_from(db_file: str, key: str):
    if not os.path.exists(db_file):
        return None
    try:
        hashed_key = hashlib.md5(key.encode('utf-8')).hexdigest()
        conn_str = f"file:{db_file}?mode=ro"
        with sqlite3.connect(conn_str, uri=True, timeout=10.0) as conn:
            conn.execute("PRAGMA cache_size = -2000")
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cache WHERE key=?", (hashed_key,))
            result = cursor.fetchone()
            if result:
                raw_value = result[0]
                if isinstance(raw_value, bytes):
                    unpacked = np.unpackbits(np.frombuffer(raw_value, dtype=np.uint8))
                    if len(unpacked) > 1000:
                        unpacked = unpacked[:1000]
                    return unpacked
                else:
                    return np.array([int(c) for c in raw_value], dtype=np.uint8)
            else:
                return None
    except Exception as e:
        _log(f"DB READ ERROR ({db_file}): {e}")
        return None


def get_cached_prediction(key: str, data_size_str: str):
    db_file = CACHE_DB_FILE_FULL if data_size_str == "Full (100%)" else CACHE_DB_FILE_BASE
    return _get_cached_prediction_from(db_file, key)


# ---------------------------------------------------------------------------
# Test Label Loader
# ---------------------------------------------------------------------------
_Y_TEST = None
_Y_TEST_LOCK = threading.Lock()

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_test_labels(csv_path: str = None) -> pd.Series:
    if csv_path is None:
        csv_path = os.path.join(_SCRIPT_DIR, "datasets", "recreated_wids_v2_ny_10k.csv")
    df = pd.read_csv(csv_path)
    if df.shape[0] > 4000:
        df = df.sample(n=4000, random_state=42)
    all_numeric_cols = [
        "floor_area", "year_built", "ELEVATION", "heating_degree_days",
        "cooling_degree_days", "january_min_temp", "july_max_temp",
        "avg_temp", "april_avg_temp", "october_avg_temp",
    ]
    all_categorical_cols = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
    feature_columns = all_numeric_cols + all_categorical_cols
    for col in feature_columns:
        if col not in df.columns:
            df[col] = np.nan
    X = df[feature_columns].copy()
    y = df["high_energy_usage"].copy()
    _, _, _, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    return y_test


def _ensure_y_test_loaded():
    global _Y_TEST
    with _Y_TEST_LOCK:
        if _Y_TEST is None:
            print("Loading test labels for local accuracy computation...", flush=True)
            _Y_TEST = get_test_labels()
            print(f"Test labels loaded: {len(_Y_TEST)} samples", flush=True)


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
        print(f"[A9V2] {msg}")


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
ATTEMPT_LIMIT = 10000000000
LEADERBOARD_POLL_TRIES = 60
LEADERBOARD_POLL_SLEEP = 1.0

MAJORITY_MODEL_NAME = "The Majority Vote"
FULL_DATA_SIZE_LABEL = "Full (100%)"

BASE_MODEL_NAMES = [
    "The Balanced Generalist",
    "The Rule-Maker",
    "The Deep Pattern-Finder",
    "The 'Nearest Neighbor'",
]


def build_cache_key(model_name: str, complexity: int, feature_set: list, data_size_str: str = None) -> str:
    if data_size_str is None:
        data_size_str = FULL_DATA_SIZE_LABEL
    feature_key = ",".join(sorted(feature_set))
    return f"{model_name}|{complexity}|{data_size_str}|{feature_key}"


def _compute_majority_vote(pred_arrays: list, tie_break: str = "random", rng_seed: int = 42) -> np.ndarray:
    if len(pred_arrays) != 4:
        raise ValueError(f"Expected 4 base model arrays, got {len(pred_arrays)}")
    stack = np.vstack(pred_arrays)
    vote_sum = np.sum(stack, axis=0)
    majority = np.zeros(vote_sum.shape, dtype=np.uint8)
    majority[vote_sum > 2] = 1
    majority[vote_sum < 2] = 0
    ties = (vote_sum == 2)
    if np.any(ties):
        if tie_break == "random":
            rng = np.random.default_rng(rng_seed)
            majority[ties] = rng.choice([0, 1], size=np.count_nonzero(ties))
        else:
            majority[ties] = 0
    return majority


def _fetch_base_preds_for_majority(complexity: int, feature_set: list, data_size_str: str) -> Optional[list]:
    pred_arrays = []
    for m in BASE_MODEL_NAMES:
        k = build_cache_key(m, complexity, feature_set, data_size_str)
        s = get_cached_prediction(k, data_size_str)
        if s is None:
            break
        pred_arrays.append(s)
    if pred_arrays and len(pred_arrays) == 4:
        return pred_arrays
    if data_size_str == "Full (100%)":
        pred_arrays = []
        for m in BASE_MODEL_NAMES:
            k = build_cache_key(m, complexity, feature_set, data_size_str)
            s = _get_cached_prediction_from(CACHE_DB_FILE_BASE, k)
            if s is None:
                return None
            pred_arrays.append(s)
        return pred_arrays
    return None


MODEL_TYPES = {
    "The Balanced Generalist": {
        "model_builder": lambda: LogisticRegression(max_iter=500, random_state=42, class_weight="balanced"),
        "card": "### ⚖️ The Balanced Generalist\nA reliable, fast **Logistic Regression** model. Works well as a starting point to identify general trends in energy consumption.",
    },
    "The Rule-Maker": {
        "model_builder": lambda: DecisionTreeClassifier(random_state=42, class_weight="balanced"),
        "card": "### 📐 The Rule-Maker\nA **Decision Tree** that creates logical rules. Very transparent, but can be too rigid.",
    },
    "The 'Nearest Neighbor'": {
        "model_builder": lambda: KNeighborsClassifier(),
        "card": "### 🔍 The 'Nearest Neighbor'\nThis model (**KNN**) looks at closest past examples. Excellent for capturing local behaviors.",
    },
    "The Deep Pattern-Finder": {
        "model_builder": lambda: RandomForestClassifier(random_state=42, class_weight="balanced"),
        "card": "### 🌲 The Deep Pattern-Finder\nA **Random Forest** combining hundreds of trees. Most powerful for complex patterns.",
    },
    "The Majority Vote": {
        "card": "### 🗳️ The Majority Vote\nAn **Ensemble** that combines all four base models and picks the most frequent prediction. Often more robust.",
        "cache_only": True,
    },
}

DEFAULT_MODEL = "The Balanced Generalist"

TEAM_NAMES = [
    "The Climate Guardians", "United Eco-Architects", "The Energy Detectives",
    "The Sustainability League", "Green Future Engineers", "Zero Carbon Avengers",
]

FEATURE_SET_ALL_OPTIONS = [
    ("Surface Area (sq ft)", "floor_area"),
    ("Year Built", "year_built"),
    ("Building Class", "building_class"),
    ("Facility Type", "facility_type"),
    ("Geographic Zone (State Factor)", "State_Factor"),
    ("Record Year (Year Factor)", "Year_Factor"),
    ("Elevation", "ELEVATION"),
    ("Heating Degree Days", "heating_degree_days"),
    ("Cooling Degree Days", "cooling_degree_days"),
    ("Annual Avg Temp", "avg_temp"),
    ("January Min Temp", "january_min_temp"),
    ("July Max Temp", "july_max_temp"),
    ("April Avg Temp", "april_avg_temp"),
    ("October Avg Temp", "october_avg_temp"),
]
FEATURE_SET_GROUP_1_VALS = ["floor_area", "year_built", "building_class", "facility_type"]
ALL_NUMERIC_COLS = [
    "floor_area", "year_built", "ELEVATION", "heating_degree_days",
    "cooling_degree_days", "january_min_temp", "july_max_temp",
    "avg_temp", "april_avg_temp", "october_avg_temp",
]
ALL_CATEGORICAL_COLS = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
DEFAULT_FEATURE_SET = FEATURE_SET_GROUP_1_VALS

DATA_SIZE_MAP = {"Small (20%)": 0.2, "Medium (60%)": 0.6, "Large (80%)": 0.8, "Full (100%)": 1.0}
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
def _build_attempts_tracker_html(current_count, limit=10000000000):
    bg_color = "#f0f9ff"
    border_color = "#bae6fd"
    text_color = "#0369a1"
    if current_count >= limit:
        icon = "🛑"
        label = f"Last chance (for now) to boost your score!: {current_count}/{limit}"
    else:
        icon = "📊"
        label = f"Attempts used: {current_count}/{limit}"
    return f"<div style='text-align:center; padding:8px; margin:8px 0; background:{bg_color}; border-radius:8px; border:1px solid {border_color};'><p style='margin:0; color:{text_color}; font-weight:600; font-size:1rem;'>{icon} {label}</p></div>"


def check_attempt_limit(submission_count, limit=None):
    if limit is None:
        limit = ATTEMPT_LIMIT
    if submission_count >= limit:
        return False, f"Attempt limit reached ({submission_count}/{limit})"
    return True, f"Attempts: {submission_count}/{limit}"


def _build_skeleton_leaderboard(rows=6, is_team=True, submit_button_label="5. 🔬 Build & Submit Model"):
    context_label = "Team" if is_team else "Individual"
    return f"""<div class='lb-placeholder' aria-live='polite'><div class='lb-placeholder-title'>{context_label} Standings Pending</div><div class='lb-placeholder-sub'><p style='margin:0 0 6px 0;'>Submit your first model to populate this table.</p><p style='margin:0;'><strong>Click "{submit_button_label}" (bottom-left)</strong> to begin!</p></div></div>"""


def build_login_prompt_html():
    return """<h2 style='color: #111827; margin-top:20px; border-top: 2px solid #e5e7eb; padding-top: 20px;'>🔐 Sign in to submit & rank</h2><div style='margin-top:16px; text-align:left; font-size:1rem; line-height:1.6; color:#374151;'><p style='margin:12px 0;'>This is a preview run only. Sign in to publish your score to the live leaderboard, earn promotions, and contribute team points.</p><p style='margin:12px 0;'><strong>New user?</strong> Create a free account at <a href='https://www.modelshare.ai/login' target='_blank' style='color:#4f46e5; text-decoration:underline;'>modelshare.ai/login</a></p></div>"""


def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count, is_preview=False, is_pending=False, local_test_accuracy=None):
    if is_pending:
        title = "⏳ Submission Processing"
        acc_color = "#3b82f6"
        acc_text = f"{(local_test_accuracy * 100):.2f}%" if local_test_accuracy is not None else "N/A"
        if local_test_accuracy is not None and last_score is not None and last_score > 0:
            score_diff = local_test_accuracy - last_score
            if abs(score_diff) < 0.0001:
                acc_diff_html = "<p style='font-size:1.5rem; font-weight:600; color:#6b7280; margin:0;'>No Change (Provisional)</p>"
            elif score_diff > 0:
                acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:#16a34a; margin:0;'>+{(score_diff*100):.2f} (Provisional)</p>"
            else:
                acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:#ef4444; margin:0;'>{(score_diff*100):.2f} (Provisional)</p>"
        else:
            acc_diff_html = "<p style='font-size:1.2rem; font-weight:500; color:#6b7280; margin:0;'>Pending leaderboard update...</p>"
        border_color = acc_color
        rank_color = "#6b7280"
        rank_text = "Pending"
        rank_diff_html = "<p style='font-size:1.2rem; font-weight:500; color:#6b7280; margin:0;'>Calculating rank...</p>"
    elif is_preview:
        title = "🔬 Successful Preview Run!"
        acc_color = "#16a34a"
        acc_text = f"{(new_score*100):.2f}%" if new_score > 0 else "N/A"
        acc_diff_html = "<div style='background:#eff6ff; border:2px solid #3b82f6; padding:10px 14px; border-radius:8px; margin-top:8px;'><p style='margin:0; color:#1e40af; font-weight:600; font-size:1rem;'>PREVIEW ONLY — not submitted to the leaderboard. Log in to submit for real.</p></div>"
        border_color = acc_color
        rank_color = "#3b82f6"
        rank_text = "N/A"
        rank_diff_html = "<p style='font-size:1.2rem; font-weight:500; color:#6b7280; margin:0;'>Not ranked (preview)</p>"
    elif submission_count == 0:
        title = "🎉 First Model Submitted!"
        acc_color = "#16a34a"
        acc_text = f"{(new_score*100):.2f}%"
        acc_diff_html = "<p style='font-size:1.2rem; font-weight:500; color:#6b7280; margin:0; padding-top:8px;'>(Your first score!)</p>"
        rank_color = "#3b82f6"
        rank_text = f"#{new_rank}"
        rank_diff_html = "<p style='font-size:1.5rem; font-weight:600; color:#3b82f6; margin:0;'>You're on the board!</p>"
        border_color = acc_color
    else:
        score_diff = new_score - last_score
        if abs(score_diff) < 0.0001:
            title = "✅ Submission Successful"
            acc_color = "#6b7280"
            acc_text = f"{(new_score*100):.2f}%"
            acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:{acc_color}; margin:0;'>No Change</p>"
            border_color = acc_color
        elif score_diff > 0:
            title = "✅ Submission Successful!"
            acc_color = "#16a34a"
            acc_text = f"{(new_score*100):.2f}%"
            acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:{acc_color}; margin:0;'>+{(score_diff*100):.2f}</p>"
            border_color = acc_color
        else:
            title = "📉 Score Dropped"
            acc_color = "#ef4444"
            acc_text = f"{(new_score*100):.2f}%"
            acc_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:{acc_color}; margin:0;'>{(score_diff*100):.2f}</p>"
            border_color = acc_color
        rank_diff = last_rank - new_rank
        rank_color = "#3b82f6"
        rank_text = f"#{new_rank}"
        if last_rank == 0:
            rank_diff_html = "<p style='font-size:1.5rem; font-weight:600; color:#3b82f6; margin:0;'>You're on the board!</p>"
        elif rank_diff > 0:
            rank_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:#16a34a; margin:0;'>Moved up {rank_diff} spot{'s' if rank_diff > 1 else ''}!</p>"
        elif rank_diff < 0:
            rank_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:#ef4444; margin:0;'>Dropped {abs(rank_diff)} spot{'s' if abs(rank_diff) > 1 else ''}</p>"
        else:
            rank_diff_html = f"<p style='font-size:1.5rem; font-weight:600; color:{rank_color}; margin:0;'>No Change</p>"
    return f"""<div class='kpi-card' style='border-color:{border_color};'><h2 style='color:var(--body-text-color); margin-top:0;'>{title}</h2><div class='kpi-card-body'><div class='kpi-metric-box'><p class='kpi-label'>New Accuracy</p><p class='kpi-score' style='color:{acc_color};'>{acc_text}</p>{acc_diff_html}</div><div class='kpi-metric-box'><p class='kpi-label'>Your Rank</p><p class='kpi-score' style='color:{rank_color};'>{rank_text}</p>{rank_diff_html}</div></div></div>"""


def _build_team_html(team_summary_df, team_name):
    if team_summary_df is None or team_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>No team submissions yet.</p>"
    normalized_user_team = _normalize_team_name(team_name).lower()
    header = "<table class='leaderboard-html-table'><thead><tr><th>Rank</th><th>Team</th><th>Best_Score</th><th>Avg_Score</th><th>Submissions</th></tr></thead><tbody>"
    body = ""
    for index, row in team_summary_df.iterrows():
        normalized_row_team = _normalize_team_name(row["Team"]).lower()
        is_user_team = normalized_row_team == normalized_user_team
        row_class = "class='user-row-highlight'" if is_user_team else ""
        body += f"<tr {row_class}><td>{index}</td><td>{row['Team']}</td><td>{(row['Best_Score']*100):.2f}%</td><td>{(row['Avg_Score']*100):.2f}%</td><td>{row['Submissions']}</td></tr>"
    return header + body + "</tbody></table>"


def _build_individual_html(individual_summary_df, username):
    if individual_summary_df is None or individual_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>No individual submissions yet.</p>"
    header = "<table class='leaderboard-html-table'><thead><tr><th>Rank</th><th>Engineer</th><th>Best_Score</th><th>Submissions</th></tr></thead><tbody>"
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
        return ("<p style='text-align:center; color:#6b7280;'>Leaderboard empty.</p>", "<p style='text-align:center; color:#6b7280;'>Leaderboard empty.</p>", _build_kpi_card_html(0, 0, 0, 0, 0), 0.0, 0, 0.0)
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
    return MODEL_TYPES.get(model_name, {}).get("card", "No description available.")


def compute_rank_settings(submission_count, current_model, current_complexity, current_feature_set, current_data_size):
    """All tools unlocked from the start — always Chief Climate Architect."""
    all_models = list(MODEL_TYPES.keys())
    all_features = FEATURE_SET_ALL_OPTIONS
    all_data_sizes = list(DATA_SIZE_MAP.keys())
    model_value = current_model if current_model in all_models else DEFAULT_MODEL
    complexity_value = min(max(int(current_complexity or 2), 1), 10)
    feature_set_value = current_feature_set if current_feature_set else DEFAULT_FEATURE_SET
    data_size_value = current_data_size if current_data_size in all_data_sizes else DEFAULT_DATA_SIZE
    return {
        "rank_message": "# 👑 Rank: Chief Climate Architect\n<p style='font-size:24px; line-height:1.4;'>All tools unlocked — optimize for the planet!</p>",
        "model_choices": all_models,
        "model_value": model_value,
        "model_interactive": True,
        "complexity_max": 10,
        "complexity_value": complexity_value,
        "feature_set_choices": all_features,
        "feature_set_value": feature_set_value,
        "feature_set_interactive": True,
        "data_size_choices": all_data_sizes,
        "data_size_value": data_size_value,
        "data_size_interactive": True,
    }


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
        error_html = "<div style='background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'><p style='margin:0; color:#991b1b; font-weight:500;'>Username is required</p></div>"
        return {login_username: gr.update(), login_password: gr.update(), login_submit: gr.update(), login_error: gr.update(value=error_html, visible=True), submit_button: gr.update(), submission_feedback_display: gr.update(), team_name_state: gr.update(), username_state: gr.update(), token_state: gr.update()}
    if not password_input or not password_input.strip():
        error_html = "<div style='background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'><p style='margin:0; color:#991b1b; font-weight:500;'>Password is required</p></div>"
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
        if is_new_team:
            team_message = f"You have been randomly assigned to team: <b>{team_name}</b>."
        else:
            team_message = f"Welcome back! You remain on team: <b>{team_name}</b>"
        success_html = f"<div style='background:#f0fdf4; padding:16px; border-radius:8px; border-left:4px solid #16a34a; margin-top:12px;'><p style='margin:0; color:#15803d; font-weight:600;'>Signed in successfully!</p><p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>{team_message}</p><p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>Click \"Build & Submit Model\" again to publish your score.</p></div>"
        return {login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(value=success_html, visible=True), submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True), submission_feedback_display: gr.update(visible=False), team_name_state: gr.update(value=team_name), username_state: gr.update(value=username_clean), token_state: gr.update(value=token)}
    except Exception as e:
        error_html = f"<div style='background:#fef2f2; padding:16px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'><p style='margin:0; color:#991b1b; font-weight:600;'>Authentication failed</p><p style='margin:8px 0; color:#7f1d1d;'>Could not verify your credentials.</p><p style='margin:8px 0 0 0; color:#7f1d1d;'><strong>New user?</strong> Create a free account at <a href='https://www.modelshare.ai/login' target='_blank' style='color:#dc2626; text-decoration:underline;'>modelshare.ai/login</a></p></div>"
        return {login_username: gr.update(visible=True), login_password: gr.update(visible=True), login_submit: gr.update(visible=True), login_error: gr.update(value=error_html, visible=True), submit_button: gr.update(), submission_feedback_display: gr.update(), team_name_state: gr.update(), username_state: gr.update(), token_state: gr.update()}


def run_experiment(model_name_key, complexity_level, feature_set, data_size_str, team_name, last_submission_score, last_rank, submission_count, first_submission_score, best_score, username=None, token=None, readiness_flag=None, was_preview_prev=None, progress=gr.Progress()):
    """Core experiment: Uses 'yield' for visual updates and progress bar."""
    if isinstance(submit_button, dict) or isinstance(submission_feedback_display, dict):
        yield {submission_feedback_display: gr.update(value="<p style='color:red;'>Configuration Error</p>", visible=True), submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True)}
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
        return f"<div class='processing-status'><span class='processing-icon'>⚙️</span><div class='processing-text'>Step {step_num}/5: {title}</div><div class='processing-subtext'>{subtitle}</div></div>"

    progress(0.1, desc="Starting Experiment...")
    yield {submit_button: gr.update(value="⏳ Experiment Running...", interactive=False), submission_feedback_display: gr.update(value=get_status_html(1, "Initializing", "Preparing your data ingredients..."), visible=True), login_error: gr.update(visible=False), attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))}

    if not model_name_key or model_name_key not in MODEL_TYPES:
        model_name_key = DEFAULT_MODEL
    complexity_level = safe_int(complexity_level, 2)

    if playground is None:
        settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
        error_msg = "<p style='text-align:center; color:red; padding:20px 0;'>Playground not connected. Please try again later.</p>"
        yield {submission_feedback_display: gr.update(value=error_msg, visible=True), submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True), team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True), individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False), last_submission_score_state: last_submission_score, last_rank_state: last_rank, best_score_state: best_score, submission_count_state: submission_count, first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]), login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(visible=False), attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)), was_preview_state: False, kpi_meta_state: {}, last_seen_ts_state: None}
        return

    try:
        progress(0.3, desc="Retrieving Predictions...")
        _ensure_y_test_loaded()
        cache_key = build_cache_key(model_name_key, complexity_level, feature_set, data_size_str)
        yield {submission_feedback_display: gr.update(value=get_status_html(2, "Loading Predictions", "Fetching precomputed results..."), visible=True), login_error: gr.update(visible=False)}

        cached_predictions = get_cached_prediction(cache_key, data_size_str)

        # Majority vote fallback
        if model_name_key == MAJORITY_MODEL_NAME and cached_predictions is None:
            base_arrays = _fetch_base_preds_for_majority(complexity_level, feature_set, data_size_str)
            if base_arrays:
                cached_predictions = _compute_majority_vote(base_arrays, tie_break="random", rng_seed=42)

        if cached_predictions is None:
            error_html = "<div style='background:#fee2e2; padding:16px; border-radius:8px; border:2px solid #ef4444; color:#991b1b; text-align:center;'><h3 style='margin:0;'>Configuration Not Found</h3><p style='margin:8px 0;'>This combination of settings was not found. Please adjust and try again.</p></div>"
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            yield {submission_feedback_display: gr.update(value=error_html, visible=True), submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True), login_error: gr.update(visible=False), rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"])}
            return

        predictions = cached_predictions
        from sklearn.metrics import accuracy_score
        local_test_accuracy = accuracy_score(_Y_TEST, predictions)

        if token is None:
            progress(0.6, desc="Computing Preview Score...")
            preview_score = local_test_accuracy
            preview_card_html = _build_kpi_card_html(new_score=preview_score, last_score=0, new_rank=0, last_rank=0, submission_count=-1, is_preview=True)
            login_prompt_text_html = build_login_prompt_html()
            closing_div_index = preview_card_html.rfind("</div>")
            combined_html = preview_card_html[:closing_div_index] + login_prompt_text_html + "</div>" if closing_div_index != -1 else preview_card_html + login_prompt_text_html
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            yield {submission_feedback_display: gr.update(value=combined_html, visible=True), submit_button: gr.update(value="Sign In Required", interactive=False), login_username: gr.update(visible=True), login_password: gr.update(visible=True), login_submit: gr.update(visible=True), login_error: gr.update(value="", visible=False), team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True), individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False), last_submission_score_state: last_submission_score, last_rank_state: last_rank, best_score_state: best_score, submission_count_state: submission_count, first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]), attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)), was_preview_state: True, kpi_meta_state: {"was_preview": True, "preview_score": preview_score}, last_seen_ts_state: None}
            return

        if submission_count >= ATTEMPT_LIMIT:
            limit_warning_html = f"<div class='kpi-card' style='border-color:#ef4444;'><h2 style='color:#111827; margin-top:0;'>🛑 Submission Limit Reached</h2><div class='kpi-card-body'><div class='kpi-metric-box'><p class='kpi-label'>Attempts Used</p><p class='kpi-score' style='color:#ef4444;'>{ATTEMPT_LIMIT}/{ATTEMPT_LIMIT}</p></div></div></div>"
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            yield {submission_feedback_display: gr.update(value=limit_warning_html, visible=True), submit_button: gr.update(value="🛑 Limit Reached", interactive=False), model_type_radio: gr.update(interactive=False), complexity_slider: gr.update(interactive=False), feature_set_checkbox: gr.update(interactive=False), data_size_radio: gr.update(interactive=False), attempts_tracker_display: gr.update(value=f"<div style='text-align:center; padding:8px; margin:8px 0; background:#fef2f2; border-radius:8px; border:1px solid #ef4444;'><p style='margin:0; color:#991b1b; font-weight:600;'>🛑 Attempts: {ATTEMPT_LIMIT}/{ATTEMPT_LIMIT}</p></div>"), last_submission_score_state: last_submission_score, last_rank_state: last_rank, best_score_state: best_score, submission_count_state: submission_count, first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"], login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(visible=False), was_preview_state: False, kpi_meta_state: {}, last_seen_ts_state: None}
            return

        progress(0.5, desc="Submitting to Cloud...")
        yield {submission_feedback_display: gr.update(value=get_status_html(3, "Submitting", "Sending model to the competition server..."), visible=True), login_error: gr.update(visible=False)}
        description = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})"
        tags = f"team:{team_name},model:{model_name_key}"
        baseline_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)

        def _submit():
            return playground.submit_model(model=None, preprocessor=None, prediction_submission=predictions.tolist(), input_dict={"description": description, "tags": tags}, custom_metadata={"Team": team_name, "Energy_Efficiency": 0}, token=token, return_metrics=["accuracy"])

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

        progress(0.9, desc="Calculating Rank...")
        simulated_df = baseline_leaderboard_df.copy() if baseline_leaderboard_df is not None else pd.DataFrame()
        new_row = pd.DataFrame([{"username": username, "accuracy": this_submission_score, "Team": team_name, "timestamp": pd.Timestamp.now(), "version": "latest"}])
        simulated_df = pd.concat([simulated_df, new_row], ignore_index=True) if not simulated_df.empty else new_row
        team_html, individual_html, _, new_best_accuracy, new_rank, _ = generate_competitive_summary(simulated_df, team_name, username, last_submission_score, last_rank, submission_count)
        kpi_card_html = _build_kpi_card_html(new_score=this_submission_score, last_score=last_submission_score, new_rank=new_rank, last_rank=last_rank, submission_count=submission_count)

        progress(1.0, desc="Complete!")
        settings = compute_rank_settings(new_submission_count, model_name_key, complexity_level, feature_set, data_size_str)
        final_html_display = kpi_card_html
        button_update = gr.update(value="🔬 Build & Submit Model", interactive=True)
        tracker_html = _build_attempts_tracker_html(new_submission_count)
        yield {submission_feedback_display: gr.update(value=final_html_display, visible=True), team_leaderboard_display: team_html, individual_leaderboard_display: individual_html, last_submission_score_state: this_submission_score, last_rank_state: new_rank, best_score_state: new_best_accuracy, submission_count_state: new_submission_count, first_submission_score_state: new_first_submission_score, rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]), submit_button: button_update, login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(visible=False), attempts_tracker_display: gr.update(value=tracker_html), was_preview_state: False, kpi_meta_state: {"this_submission_score": this_submission_score, "new_best_accuracy": new_best_accuracy, "rank": new_rank}, last_seen_ts_state: time.time()}
    except Exception as e:
        error_msg = f"ERROR: {e}"
        _log(f"Exception in run_experiment: {error_msg}")
        settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
        yield {submission_feedback_display: gr.update(value=f"<p style='text-align:center; color:red; padding:20px 0;'>An error occurred: {error_msg}</p>", visible=True), team_leaderboard_display: f"<p style='text-align:center; color:red;'>Error: {error_msg}</p>", individual_leaderboard_display: f"<p style='text-align:center; color:red;'>Error: {error_msg}</p>", last_submission_score_state: last_submission_score, last_rank_state: last_rank, best_score_state: best_score, submission_count_state: submission_count, first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"], model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]), complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]), feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]), data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]), submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True), login_username: gr.update(visible=False), login_password: gr.update(visible=False), login_submit: gr.update(visible=False), login_error: gr.update(visible=False), attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)), was_preview_state: False, kpi_meta_state: {}, last_seen_ts_state: None}


def on_initial_load(username, token=None, team_name=""):
    """Load initial UI state. Returns 8 values."""
    _ensure_y_test_loaded()
    initial_ui = compute_rank_settings(0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE)
    display_team = team_name if team_name else "Your Team"
    welcome_html = f"<div style='text-align:center; padding:30px 20px;'><h3 style='margin:0 0 8px 0;'>Welcome to <b>{display_team}</b>!</h3><p style='font-size:1.1rem; color:#4b5563; margin:0 0 20px 0;'>Your team is waiting for your help to improve the AI.</p><div style='background:#eff6ff; padding:16px; border-radius:12px; border:2px solid #bfdbfe; display:inline-block;'><p style='margin:0; color:#1e40af; font-weight:bold;'>Click \"Build & Submit Model\" to Start!</p></div></div>"
    full_leaderboard_df = None
    try:
        if playground:
            full_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
    except Exception:
        full_leaderboard_df = None
    user_has_submitted = False
    if full_leaderboard_df is not None and not full_leaderboard_df.empty:
        if "username" in full_leaderboard_df.columns and username:
            user_has_submitted = username in full_leaderboard_df["username"].values
    if not user_has_submitted:
        team_html = welcome_html
        individual_html = "<p style='text-align:center; color:#6b7280; padding-top:40px;'>Submit your model to see where you rank!</p>"
    elif full_leaderboard_df is None or full_leaderboard_df.empty:
        team_html = _build_skeleton_leaderboard(rows=6, is_team=True)
        individual_html = _build_skeleton_leaderboard(rows=6, is_team=False)
    else:
        try:
            team_html, individual_html, _, _, _, _ = generate_competitive_summary(full_leaderboard_df, team_name, username, 0, 0, -1)
        except Exception:
            team_html = "<p style='text-align:center; color:red;'>Error rendering leaderboard.</p>"
            individual_html = team_html
    return (
        get_model_card(initial_ui["model_value"]),
        team_html,
        individual_html,
        initial_ui["rank_message"],
        gr.update(choices=initial_ui["model_choices"], value=initial_ui["model_value"], interactive=initial_ui["model_interactive"]),
        gr.update(minimum=1, maximum=initial_ui["complexity_max"], value=initial_ui["complexity_value"]),
        gr.update(choices=initial_ui["feature_set_choices"], value=initial_ui["feature_set_value"], interactive=initial_ui["feature_set_interactive"]),
        gr.update(choices=initial_ui["data_size_choices"], value=initial_ui["data_size_value"], interactive=initial_ui["data_size_interactive"]),
    )


# ---------------------------------------------------------------------------
# Conclusion helpers
# ---------------------------------------------------------------------------
def build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set):
    improvement = (best_score - first_score) if (first_score is not None and submissions > 1) else 0.0
    return f"""<div class="final-conclusion-root">
  <h1 class="final-conclusion-title">&#127891; Certification Earned</h1>
  <h2 style="margin-top:0; color:var(--text-muted);">Ethics at Play: Sustainable AI Engineering</h2>
  <div class="final-conclusion-card">
    <h3 class="final-conclusion-subtitle">&#127942; The Final Challenge Results</h3>
    <p style="text-align:left; margin-bottom:15px;">Your final AI system for identifying energy-inefficient buildings has been submitted. This model helps prioritize climate rehabilitation efforts.</p>
    <ul class="final-conclusion-list">
      <li>&#127937; <b>Final Accuracy:</b> {(best_score*100):.2f}%</li>
      <li>&#127758; <b>Global Rank:</b> {('#'+str(rank)) if rank > 0 else 'Pending'}</li>
      <li>&#128200; <b>Improvement This Session:</b> {(improvement*100):+.2f}% accuracy gain</li>
      <li>&#128290; <b>Total Iterations:</b> {submissions} model versions tested</li>
    </ul>
    <hr class="final-conclusion-divider" />
    <div class="final-conclusion-next">
      <h2>The Journey Continues</h2>
      <div style="text-align:left; margin-top:15px;">
        <p>Congratulations! You have completed the <b>Ethics at Play Certification in Sustainable AI</b> and seen how machine learning can address global climate challenges.</p>
        <p>Through this challenge, you have learned to:</p>
        <ul style="margin-bottom:15px;">
          <li>Identify energy consumption patterns in large datasets</li>
          <li>Optimize models for real-world environmental impact</li>
          <li>Balance predictive power with computational complexity (Green AI)</li>
          <li>Understand the role of data-driven decisions in urban sustainability</li>
        </ul>
        <div class="final-conclusion-ethics">
          <p style="margin:0;"><b>Final Thought:</b> AI is a powerful tool for the planet, but only if built with responsibility. You've shown how to create systems that don't just solve problems, but contribute to a more sustainable future.</p>
        </div>
        <p style="text-align:center; margin-top:25px; font-weight:bold; font-size:1.1rem;">Thank you for playing, and let's keep engineering a greener world. &#127758;</p>
      </div>
    </div>
  </div>
</div>"""


def build_conclusion_from_state(best_score, submissions, rank, first_score, feature_set):
    return build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set)


# ============================================================================
# MODULES — 1 HTML intro module (converted from JSX intro step)
# ============================================================================

MODULES = [
    {
        "id": 0,
        "title": "The Final Challenge",
        "html": """
<div style="text-align:center; padding-top:48px;">
  <div style="font-size:64px; margin-bottom:16px;" class="fnl-float">&#128640;</div>
  <h1 style="font-size:clamp(1.8rem,5vw,2rem); font-weight:800; margin:0 0 8px; background:linear-gradient(135deg,var(--a9-grad-from),var(--a9-grad-to)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; line-height:1.2; letter-spacing:-1px;">The Final Challenge</h1>
  <p style="font-size:16px; color:var(--a9-text-dim); margin:0 0 28px; line-height:1.6;">
    You've explored the data. You've identified energy patterns.<br>Now it's time to build your most optimized model.
  </p>
  <div style="background:var(--a9-card-bg); border:1px solid var(--a9-border-color); border-radius:20px; padding:28px; margin-bottom:24px; text-align:left; box-shadow:0 8px 24px var(--a9-card-shadow);">
    <h3 style="font-size:18px; font-weight:700; color:var(--a9-accent); margin:0 0 12px;">&#128295; The Sustainable AI Challenge</h3>
    <p style="font-size:15px; color:var(--a9-text); margin:0 0 12px; line-height:1.7;">
      Your final mission is to compete again against your peers by building the <strong style="color:var(--a9-warning);">most accurate AI system to identify inefficient buildings</strong>. With the climate at stake, every bit of precision counts.
    </p>
    <p style="font-size:15px; color:var(--a9-text); margin:0 0 16px; line-height:1.7;">
      Use what you've learned about Green AI and feature engineering to climb the leaderboard. Help us prioritize where rehabilitation is needed most!
    </p>
    <div style="display:flex; justify-content:center; gap:24px; flex-wrap:wrap; padding:12px 0;">
      <div style="text-align:center;"><div style="font-size:28px;">&#128081;</div><div style="font-size:13px; color:var(--a9-text-dim); margin-top:2px; line-height:1.4;">All tools unlocked</div></div>
      <div style="text-align:center;"><div style="font-size:28px;">&#128499;&#65039;</div><div style="font-size:13px; color:var(--a9-text-dim); margin-top:2px; line-height:1.4;">New: Majority Vote model</div></div>
      <div style="text-align:center;"><div style="font-size:28px;">&#127777;&#65039;</div><div style="font-size:13px; color:var(--a9-text-dim); margin-top:2px; line-height:1.4;">14 data ingredients</div></div>
      <div style="text-align:center;"><div style="font-size:28px;">&#9854;&#65039;</div><div style="font-size:13px; color:var(--a9-text-dim); margin-top:2px; line-height:1.4;">Unlimited attempts</div></div>
    </div>
  </div>
  <div style="text-align:center; margin-bottom:8px;">
    <p style="font-size:16px; font-weight:600; color:var(--a9-text); margin:0 0 4px;">Ready to optimize?</p>
    <p style="font-size:14px; color:var(--a9-text-dim); margin:0 0 20px;">&#128071; Click below to start.</p>
  </div>
</div>
""",
    },
]


# ============================================================================
# CSS — --a9-* variable namespace
# ============================================================================

css = r"""
/* === Onboarding CSS vars (--a9-* namespace) === */
:root {
  --a9-bg: #0f172a;
  --a9-card-bg: rgba(30,41,59,0.7);
  --a9-accent: #38bdf8;
  --a9-accent-glow: rgba(56,189,248,0.3);
  --a9-success: #10b981;
  --a9-success-soft: rgba(16,185,129,0.15);
  --a9-warning: #fbbf24;
  --a9-warning-soft: rgba(251,191,36,0.15);
  --a9-error: #f43f5e;
  --a9-error-soft: rgba(244,63,94,0.15);
  --a9-text: #f8fafc;
  --a9-text-dim: #94a3b8;
  --a9-card-shadow: rgba(0,0,0,0.5);
  --a9-border-color: rgba(255,255,255,0.05);
  --a9-input-bg: rgba(255,255,255,0.05);
  --a9-hover-bg: rgba(255,255,255,0.08);
  --a9-grad-from: #f8fafc; --a9-grad-to: #fbbf24;
}

@media (prefers-color-scheme: light) {
  :root {
    --a9-bg: #f8fafc;
    --a9-card-bg: rgba(255,255,255,0.9);
    --a9-accent: #0284c7;
    --a9-accent-glow: rgba(2,132,199,0.2);
    --a9-success: #059669;
    --a9-success-soft: rgba(5,150,105,0.12);
    --a9-warning: #d97706;
    --a9-warning-soft: rgba(217,119,6,0.12);
    --a9-error: #dc2626;
    --a9-error-soft: rgba(220,38,38,0.10);
    --a9-text: #0f172a;
    --a9-text-dim: #64748b;
    --a9-card-shadow: rgba(0,0,0,0.1);
    --a9-border-color: rgba(0,0,0,0.08);
    --a9-input-bg: rgba(0,0,0,0.02);
    --a9-hover-bg: rgba(0,0,0,0.05);
    --a9-grad-from: #0f172a; --a9-grad-to: #d97706;
  }
}

/* Animations */
@keyframes a9FloatGlow { 0%,100% { transform:translateY(0); filter:drop-shadow(0 0 12px var(--a9-accent-glow)); } 50% { transform:translateY(-6px); filter:drop-shadow(0 0 20px var(--a9-accent-glow)); } }
@keyframes a9FadeSlideUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }

.fnl-float { animation: a9FloatGlow 3s ease-in-out infinite; }

/* Arena/KPI/leaderboard CSS */
.kpi-card { background:var(--block-background-fill,#fff); border:2px solid var(--color-accent,#6366f1); padding:24px; border-radius:16px; text-align:center; max-width:600px; margin:auto; min-height:200px; }
.kpi-card-body { display:flex; flex-wrap:wrap; justify-content:space-around; align-items:flex-end; margin-top:24px; }
.kpi-metric-box { min-width:150px; margin:10px; }
.kpi-label { font-size:1rem; color:var(--secondary-text-color,#6b7280); margin:0; }
.kpi-score { font-size:3rem; font-weight:700; margin:0; line-height:1.1; }
.leaderboard-html-table { width:100%; border-collapse:collapse; text-align:left; font-size:1rem; min-height:300px; }
.leaderboard-html-table th { padding:12px 16px; font-size:0.9rem; font-weight:500; }
.leaderboard-html-table tbody tr { border-bottom:1px solid var(--border-color-primary,#e5e7eb); }
.leaderboard-html-table td { padding:12px 16px; }
.leaderboard-html-table .user-row-highlight { background:rgba(59,130,246,0.1); font-weight:600; }
.lb-placeholder { min-height:300px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:var(--block-background-fill,#fff); border:1px solid var(--border-color-primary,#e5e7eb); border-radius:12px; padding:40px 20px; text-align:center; }
.lb-placeholder-title { font-size:1.25rem; font-weight:500; color:var(--secondary-text-color,#6b7280); margin-bottom:8px; }
.lb-placeholder-sub { font-size:1rem; color:var(--secondary-text-color,#6b7280); }
.processing-status { background:var(--block-background-fill,#fff); border:2px solid var(--color-accent,#6366f1); border-radius:16px; padding:30px; text-align:center; animation:pulse-indigo 2s infinite; }
.processing-icon { font-size:4rem; margin-bottom:10px; display:block; animation:spin-slow 3s linear infinite; }
.processing-text { font-size:1.5rem; font-weight:700; color:var(--color-accent,#6366f1); }
.processing-subtext { font-size:1.1rem; color:var(--secondary-text-color,#6b7280); margin-top:8px; }
@keyframes pulse-indigo { 0%{box-shadow:0 0 0 0 rgba(99,102,241,0.4);} 70%{box-shadow:0 0 0 15px rgba(99,102,241,0);} 100%{box-shadow:0 0 0 0 rgba(99,102,241,0);} }
@keyframes spin-slow { from{transform:rotate(0deg);} to{transform:rotate(360deg);} }

/* Conclusion */
.final-conclusion-root { text-align:center; }
.final-conclusion-title { font-size:2.4rem; margin:0; }
.final-conclusion-card { background:var(--block-background-fill,#fff); padding:28px; border-radius:18px; border:2px solid var(--border-color-primary,#e5e7eb); margin-top:24px; max-width:950px; margin-left:auto; margin-right:auto; }
.final-conclusion-subtitle { margin-top:0; font-size:1.5rem; }
.final-conclusion-list { list-style:none; padding:0; font-size:1.05rem; text-align:left; max-width:640px; margin:20px auto; }
.final-conclusion-list li { margin:4px 0; }
.final-conclusion-ethics { margin-top:16px; padding:18px; border-radius:12px; border-left:6px solid #ef4444; background:color-mix(in srgb, #ef4444 10%, transparent); text-align:left; font-size:0.98rem; line-height:1.4; }
.final-conclusion-divider { margin:28px 0; border:0; border-top:2px solid var(--border-color-primary,#e5e7eb); }

/* Nav loading overlay */
#nav-loading-overlay { position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(255,255,255,0.9); z-index:9999; display:none; flex-direction:column; align-items:center; justify-content:center; opacity:0; transition:opacity 0.3s ease; }
.nav-spinner { width:50px; height:50px; border:5px solid #e5e7eb; border-top:5px solid var(--color-accent,#6366f1); border-radius:50%; animation:spin-slow 1s linear infinite; margin-bottom:20px; }
#nav-loading-text { font-size:1.3rem; font-weight:600; color:var(--color-accent,#6366f1); }
"""


# ============================================================================
# CLIENT_JS — minimal (font loader only, no interactive features needed)
# ============================================================================

CLIENT_JS = r"""
(function(){
  if(!document.querySelector('link[href*="Outfit"]')){
    var l=document.createElement('link');l.rel='stylesheet';
    l.href='https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Mono:wght@400;700&display=swap';
    document.head.appendChild(l);
  }
})();
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

def create_model_building_game_en_final_app(theme_primary_hue="indigo"):
    """Build the Gradio Blocks app with onboarding intro + arena + conclusion."""
    global playground
    if playground is None:
        try:
            playground = Competition(MY_PLAYGROUND_ID)
        except Exception as e:
            print(f"WARNING: Could not connect to playground: {e}")
            playground = None

    # Declare globals that run_experiment yields into
    global submit_button, submission_feedback_display, team_leaderboard_display
    global individual_leaderboard_display, last_submission_score_state, last_rank_state
    global best_score_state, submission_count_state, first_submission_score_state
    global rank_message_display, model_type_radio, complexity_slider
    global feature_set_checkbox, data_size_radio
    global login_username, login_password, login_submit, login_error
    global attempts_tracker_display, team_name_state

    with gr.Blocks() as demo:

        # Top anchor for scroll-to-top
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")

        # Navigation loading overlay
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        # ── Loader column (shown until JS kicks in) ──────────────────────
        with gr.Column(visible=True, elem_id="ob-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:120px 0;'>"
                "<h2 style='font-size:2rem; color:#6b7280;'>Loading...</h2>"
                "</div>"
            )

        # ── Main app column ──────────────────────────────────────────────
        with gr.Column(visible=False) as main_app_col:

            # ---------- Onboarding module 0 (Intro) ----------
            module_cols = []

            with gr.Column(visible=True, elem_id="ob-mod-0") as intro_col:
                gr.HTML(MODULES[0]["html"])
                enter_arena_btn = gr.Button("Enter the Arena ▶️", variant="primary", size="lg")

            module_cols.append(intro_col)

            # ---------- Arena column ----------
            with gr.Column(visible=False, elem_id="model-step") as arena_col:
                gr.Markdown("<h1 style='text-align:center;'>Model Building Arena</h1>")

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

                rank_message_display = gr.Markdown("### Rank loading...")

                with gr.Row():
                    with gr.Column(scale=1):
                        model_type_radio = gr.Radio(
                            label="1. Model Strategy",
                            choices=list(MODEL_TYPES.keys()),
                            value=DEFAULT_MODEL,
                            interactive=True
                        )
                        model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL))
                        gr.Markdown("---")

                        complexity_slider = gr.Slider(
                            label="2. Model Complexity (1-10)",
                            minimum=1, maximum=10, step=1, value=2,
                            info="Higher values allow deeper pattern learning; very high values may overfit."
                        )
                        complexity_tooltip = gr.HTML(
                            value="<div style='background:var(--background-fill-secondary); padding:10px 14px; border-radius:8px; border:1px solid var(--border-color-primary); margin-top:4px; font-size:0.9rem;'><b>Level 2:</b> Balanced — your model learns useful patterns without memorizing the data.</div>"
                        )
                        gr.Markdown("---")

                        feature_set_checkbox = gr.CheckboxGroup(
                            label="3. Select Data Ingredients",
                            choices=FEATURE_SET_ALL_OPTIONS,
                            value=DEFAULT_FEATURE_SET,
                            interactive=True,
                            info="All 14 data ingredients available!"
                        )
                        gr.Markdown("---")

                        data_size_radio = gr.Radio(
                            label="4. Data Size",
                            choices=list(DATA_SIZE_MAP.keys()),
                            value=DEFAULT_DATA_SIZE,
                            interactive=True
                        )
                        gr.Markdown("---")

                        attempts_tracker_display = gr.HTML(
                            value="",
                            visible=False
                        )

                        submit_button = gr.Button(
                            value="5. 🔬 Build & Submit Model",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column(scale=1):
                        gr.HTML(
                            "<div class='leaderboard-box' style='background:var(--block-background-fill); padding:20px; border-radius:16px; border:1px solid var(--border-color-primary); margin-top:12px;'>"
                            "<h3 style='margin-top:0;'>Live Standings</h3>"
                            "<p style='margin:0;'>Submit a model to see your rank.</p>"
                            "</div>"
                        )

                        submission_feedback_display = gr.HTML(
                            "<p style='text-align:center; color:#6b7280; padding:20px 0;'>Submit your first model to get feedback!</p>"
                        )

                        # Inline login (hidden by default)
                        login_username = gr.Textbox(label="Username",
                                                    placeholder="Enter your modelshare.ai username",
                                                    visible=False)
                        login_password = gr.Textbox(label="Password", type="password",
                                                    placeholder="Enter your password",
                                                    visible=False)
                        login_submit = gr.Button("Sign In & Submit", variant="primary",
                                                 visible=False)
                        login_error = gr.HTML(value="", visible=False)

                        with gr.Tabs():
                            with gr.TabItem("Team Standings"):
                                team_leaderboard_display = gr.HTML(
                                    "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see team rankings.</p>"
                                )
                            with gr.TabItem("Individual Standings"):
                                individual_leaderboard_display = gr.HTML(
                                    "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see individual rankings.</p>"
                                )

                with gr.Row():
                    arena_back_btn = gr.Button("← Back", size="lg")
                    arena_finish_btn = gr.Button("Finish & Reflect", variant="secondary", size="lg")

            # ---------- Conclusion column ----------
            with gr.Column(visible=False, elem_id="conclusion-step") as conclusion_col:
                gr.Markdown("<h1 style='text-align:center;'>Section Complete</h1>")
                final_score_display = gr.HTML(value="<p>Preparing final summary...</p>")
                conclusion_back_btn = gr.Button("← Back to Arena")

        # ==================================================================
        # NAVIGATION WIRING
        # ==================================================================

        all_panels = module_cols + [arena_col, conclusion_col, loader_col]

        def make_nav(target):
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
                  }}
                }}, 90);
              }} catch(e) {{ console.warn('nav-js error', e); }}
            }}
            """

        # Module 0 → Arena
        enter_arena_btn.click(
            fn=make_nav(arena_col),
            inputs=None, outputs=all_panels,
            js=nav_js("model-step", "Entering model arena...")
        )

        # Arena back → Module 0
        arena_back_btn.click(
            fn=make_nav(intro_col),
            inputs=None, outputs=all_panels,
            js=nav_js("ob-mod-0", "Going back...")
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
            js=nav_js("conclusion-step", "Generating performance summary...")
        )

        # Conclusion back → Arena
        conclusion_back_btn.click(
            fn=make_nav(arena_col),
            inputs=None, outputs=all_panels,
            js=nav_js("model-step", "Returning to experiment workspace...")
        )

        # ==================================================================
        # ARENA CONTROL EVENTS
        # ==================================================================

        model_type_radio.change(fn=get_model_card, inputs=model_type_radio, outputs=model_card_display)
        model_type_radio.change(fn=lambda v: v or DEFAULT_MODEL, inputs=model_type_radio, outputs=model_type_state)

        def _complexity_tooltip(v):
            if v <= 3:
                desc = "General patterns — your model learns broad rules. Safe starting point."
            elif v <= 7:
                desc = "Balanced — your model learns useful patterns without memorizing the data."
            else:
                desc = "Memorizing details — high accuracy on training data, but risky on new buildings."
            return f"<div style='background:var(--background-fill-secondary); padding:10px 14px; border-radius:8px; border:1px solid var(--border-color-primary); margin-top:4px; font-size:0.9rem;'><b>Level {int(v)}:</b> {desc}</div>"

        complexity_slider.change(fn=lambda v: v, inputs=complexity_slider, outputs=complexity_state)
        complexity_slider.change(fn=_complexity_tooltip, inputs=complexity_slider, outputs=complexity_tooltip)
        feature_set_checkbox.change(fn=lambda v: v or [], inputs=feature_set_checkbox, outputs=feature_set_state)
        data_size_radio.change(fn=lambda v: v or DEFAULT_DATA_SIZE, inputs=data_size_radio, outputs=data_size_state)

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
            js=nav_js("model-step", "Running experiment...", 500, notify_parent=False),
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
            outputs=[
                # on_initial_load returns 8 values:
                model_card_display,
                team_leaderboard_display,
                individual_leaderboard_display,
                rank_message_display,
                model_type_radio,
                complexity_slider,
                feature_set_checkbox,
                data_size_radio,
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
            ]
        )

    return demo

# -------------------------------------------------------------------------
# 4. Convenience Launcher
# -------------------------------------------------------------------------

def launch_model_building_game_en_final_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
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

    demo = create_model_building_game_en_final_app()

    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

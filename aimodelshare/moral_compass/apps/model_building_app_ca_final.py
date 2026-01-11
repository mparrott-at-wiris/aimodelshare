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
# Configuration & Caching Infrastructure
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# CACHE CONFIGURATION (Optimized: Thread-Safe SQLite with Dual-DB Support)
# -------------------------------------------------------------------------
import sqlite3

CACHE_DB_FILE_BASE = "prediction_cache.sqlite"
CACHE_DB_FILE_FULL = "prediction_cache_full.sqlite"

def _get_cached_prediction_from(db_file: str, key: str) -> Optional[str]:
    """
    Lightning-fast lookup from specified SQLite database.
    THREAD-SAFE: Opens a new connection for every lookup.
    
    Args:
        db_file: Path to the SQLite database file
        key: Cache key to lookup
    
    Returns:
        Cached prediction string or None if not found
    """
    if not os.path.exists(db_file):
        return None

    try:
        # Use a context manager ('with') to ensure the connection 
        # is ALWAYS closed, releasing file locks immediately.
        # timeout=10 ensures we don't wait forever if the file is busy.
        with sqlite3.connect(db_file, timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cache WHERE key=?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
            
    except sqlite3.OperationalError as e:
        # Handle locking errors gracefully
        print(f"⚠️ CACHE LOCK ERROR ({db_file}): {e}", flush=True)
        return None
        
    except Exception as e:
        print(f"⚠️ DB READ ERROR ({db_file}): {e}", flush=True)
        return None

def get_cached_prediction(key: str, data_size_str: str) -> Optional[str]:
    """
    Lookup prediction from appropriate database based on data size.
    Routes Full (100%) to prediction_cache_full.sqlite, others to prediction_cache.sqlite.
    
    Args:
        key: Cache key to lookup
        data_size_str: Data size label (e.g., "Small (20%)", "Full (100%)")
    
    Returns:
        Cached prediction string or None if not found
    """
    db_file = CACHE_DB_FILE_FULL if data_size_str == "Full (100%)" else CACHE_DB_FILE_BASE
    return _get_cached_prediction_from(db_file, key)

print("✅ App configured for Thread-Safe Dual-DB SQLite Cache.")

# -------------------------------------------------------------------------
# Lightweight Label Loader (No Training, Only Test Accuracy Computation)
# -------------------------------------------------------------------------
_Y_TEST = None
_Y_TEST_LOCK = threading.Lock()

def get_test_labels(csv_path: str = "compas.csv") -> pd.Series:
    """
    Load test labels from CSV file for local accuracy computation.
    Matches the exact sampling and splitting logic from precompute_cache.py.
    
    Args:
        csv_path: Path to compas.csv (downloaded at build time)
    
    Returns:
        pd.Series: Test labels (y_test)
    """
    # Load data
    df = pd.read_csv(csv_path)
    
    # Calculate length_of_stay
    try:
        df['c_jail_in'] = pd.to_datetime(df['c_jail_in'])
        df['c_jail_out'] = pd.to_datetime(df['c_jail_out'])
        df['length_of_stay'] = (df['c_jail_out'] - df['c_jail_in']).dt.total_seconds() / (24 * 60 * 60)
    except Exception:
        df['length_of_stay'] = np.nan
    
    # Sample MAX_ROWS
    if df.shape[0] > 4000:  # MAX_ROWS = 4000
        df = df.sample(n=4000, random_state=42)
    
    # Extract features and target (matching precompute_cache.py)
    all_numeric_cols = ["juv_fel_count", "juv_misd_count", "juv_other_count", 
                        "days_b_screening_arrest", "age", "length_of_stay", "priors_count"]
    all_categorical_cols = ["race", "sex", "c_charge_degree", "c_charge_desc"]
    feature_columns = all_numeric_cols + all_categorical_cols
    
    # Ensure all columns exist
    for col in feature_columns:
        if col not in df.columns:
            df[col] = np.nan
    
    # Process c_charge_desc
    if "c_charge_desc" in df.columns:
        top_charges = df["c_charge_desc"].value_counts().head(50).index
        df["c_charge_desc"] = df["c_charge_desc"].apply(
            lambda x: x if pd.notna(x) and x in top_charges else "OTHER"
        )
    
    X = df[feature_columns].copy()
    y = df["two_year_recid"].copy()
    
    # Split (matching precompute_cache.py: test_size=0.25, random_state=42, stratify=y)
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

T = TypeVar("T")

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


# -------------------------------------------------------------------------
# UPDATED FUNCTION
# -------------------------------------------------------------------------
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
  
def _build_attempts_tracker_html(current_count, limit=10000000000000):
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
        label = f"Última oportunitat (per ara) per pujar la teva puntuació!: {current_count}/{limit}"
    else:
        # Normal - blue styling
        bg_color = "#f0f9ff"
        border_color = "#bae6fd"
        text_color = "#0369a1"
        icon = "📊"
        label = f"Intents utilitzats: {current_count}/{limit}"

    return f"""<div style='text-align:center; padding:8px; margin:8px 0; background:{bg_color}; border-radius:8px; border:1px solid {border_color};'>
        <p style='margin:0; color:{text_color}; font-weight:600; font-size:1rem;'>{icon} {label}</p>
    </div>"""
    
def check_attempt_limit(submission_count: int, limit: int = None) -> Tuple[bool, str]:
    """Check if submission count exceeds limit."""
    # ATTEMPT_LIMIT is defined in configuration section below
    if limit is None:
        limit = ATTEMPT_LIMIT
    
    if submission_count >= limit:
        msg = f"⚠️ Límit d’intents assolit ({submission_count}/{limit})"
        return False, msg
    return True, f"Intents: {submission_count}/{limit}"

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
ATTEMPT_LIMIT = 10000000000000

# --- Leaderboard Polling Configuration ---
# After a real authenticated submission, we poll the leaderboard to detect eventual consistency.
# This prevents the "stuck on first preview KPI" issue where the leaderboard hasn't updated yet.
# Increased from 12 to 60 to better tolerate backend latency and cold starts.
# If polling times out, optimistic fallback logic will provide provisional UI updates.
LEADERBOARD_POLL_TRIES = 60  # Number of polling attempts (increased to handle backend latency/cold starts)
LEADERBOARD_POLL_SLEEP = 1.0  # Sleep duration between polls (seconds)
ENABLE_AUTO_RESUBMIT_AFTER_READY = False  # Future feature flag for auto-resubmit

# --- 1. MODEL CONFIGURATION (Keys match Database) ---
MODEL_TYPES = {
    "The Balanced Generalist": {
        "model_builder": lambda: LogisticRegression(
            max_iter=500, random_state=42, class_weight="balanced"
        ),
        # Store the Catalan description here for the UI
        "card_ca": "Aquest model és ràpid, fiable i equilibrat. Bon punt de partida; sol donar resultats més estables."
    },
    "The Rule-Maker": {
        "model_builder": lambda: DecisionTreeClassifier(
            random_state=42, class_weight="balanced"
        ),
        "card_ca": "Aquest model aprèn regles simples de tipus «si/aleshores». Fàcil d’interpretar, però li costa captar patrons complexos."
    },
    "The 'Nearest Neighbor'": {
        "model_builder": lambda: KNeighborsClassifier(),
        "card_ca": "Aquest model es basa en exemples semblants del passat. «Si t’assembles a aquests casos, prediré el mateix resultat»."
    },
    "The Deep Pattern-Finder": {
        "model_builder": lambda: RandomForestClassifier(
            random_state=42, class_weight="balanced"
        ),
        "card_ca": "Aquest model combina molts arbres de decisió per trobar patrons complexos. És potent, però cal vigilar no fer-lo massa complex."
    },
    "The Majority Vote": {
        "card_ca": "Aquest model combina les prediccions dels quatre models i selecciona la més freqüent.",
        "cache_only": True
    }
}

DEFAULT_MODEL = "The Balanced Generalist"  # Now using the English key

# --- 2. TRANSLATION MAPS (UI Display -> Database Key) ---

# Map English Keys to Catalan Display Names for the Radio Button
MODEL_DISPLAY_MAP = {
    "The Balanced Generalist": "El Generalista Equilibrat",
    "The Rule-Maker": "El Creador de Regles",
    "The 'Nearest Neighbor'": "El 'Veí més Proper'",
    "The Deep Pattern-Finder": "El Detector de Patrons Profunds",
    "The Majority Vote": "El Vot Majoritari"
}

# Create the Choices List as Tuples: [(Catalan Label, English Value)]
# This tells Gradio: "Show the user Catalan, but send Python the English key"
MODEL_RADIO_CHOICES = [(label, key) for key, label in MODEL_DISPLAY_MAP.items()]

# Map Catalan Data Sizes (UI) to English Keys (Database)
DATA_SIZE_DB_MAP = {
    "Petita (20%)": "Small (20%)",
    "Mitjana (60%)": "Medium (60%)",
    "Gran (80%)": "Large (80%)",
    "Completa (100%)": "Full (100%)"
}

# Constants for cache key building and majority vote
FULL_DATA_SIZE_LABEL = "Full (100%)"
MAJORITY_MODEL_NAME = "The Majority Vote"

# Base model names for majority vote fallback
BASE_MODEL_NAMES = [
    "The Balanced Generalist",
    "The Rule-Maker",
    "The Deep Pattern-Finder",
    "The 'Nearest Neighbor'",
]

def build_cache_key(model_name: str, complexity: int, feature_set: list, data_size_str: str = None) -> str:
    """
    Build cache key matching full-models cache format.
    
    Args:
        model_name: Model name (e.g., "The Balanced Generalist", "The Majority Vote")
        complexity: Complexity level (1-10)
        feature_set: List of feature names
        data_size_str: Data size label (defaults to FULL_DATA_SIZE_LABEL if not provided)
    
    Returns:
        Cache key string in format: model_name|complexity|data_size|feature_key
    """
    if data_size_str is None:
        data_size_str = FULL_DATA_SIZE_LABEL
    feature_key = ",".join(sorted(feature_set))
    return f"{model_name}|{complexity}|{data_size_str}|{feature_key}"

def _compute_majority_string(pred_strings: list, tie_break: str = "random", rng_seed: int = 42) -> str:
    """
    Compute majority vote over four base model prediction strings (matching generator logic).
    
    Args:
        pred_strings: List of 4 prediction strings from base models
        tie_break: Tie-breaking strategy ("random" or "zero")
        rng_seed: Random seed for deterministic tie-breaking (default: 42)
    
    Returns:
        Majority vote prediction string
    
    Raises:
        ValueError: If pred_strings doesn't contain exactly 4 strings or lengths mismatch
    """
    if len(pred_strings) != 4:
        raise ValueError(f"Expected 4 base model strings, got {len(pred_strings)}")
    lengths = {len(s) for s in pred_strings}
    if len(lengths) != 1:
        raise ValueError("Prediction strings have mismatched lengths.")
    n = lengths.pop()
    rng = np.random.default_rng(rng_seed)
    out = []
    for i in range(n):
        votes = [int(s[i]) for s in pred_strings]
        zeros = votes.count(0)
        ones = votes.count(1)
        if zeros > ones:
            out.append("0")
        elif ones > zeros:
            out.append("1")
        else:
            out.append(str(rng.choice([0, 1])) if tie_break == "random" else "0")
    return "".join(out)

def _fetch_base_pred_strings_for_majority(complexity: int, feature_set: list, data_size_str: str) -> Optional[list]:
    """
    Fetch the four base model predictions from cache for given settings.
    Implements cross-DB fallback for Full (100%) data size.
    
    Args:
        complexity: Complexity level (1-10)
        feature_set: List of feature names
        data_size_str: Data size label
    
    Returns:
        List of 4 prediction strings if all found, None if any missing
    """
    # First try: fetch from the primary database for this data size
    pred_strings = []
    for m in BASE_MODEL_NAMES:
        k = build_cache_key(m, complexity, feature_set, data_size_str)
        s = get_cached_prediction(k, data_size_str)
        if s is None:
            break
        pred_strings.append(s)
    
    if pred_strings and len(pred_strings) == 4:
        return pred_strings
    
    # Fallback for Full (100%): try base DB if full-models DB is missing any base model
    if data_size_str == "Full (100%)":
        pred_strings = []
        for m in BASE_MODEL_NAMES:
            k = build_cache_key(m, complexity, feature_set, data_size_str)
            s = _get_cached_prediction_from(CACHE_DB_FILE_BASE, k)
            if s is None:
                return None
            pred_strings.append(s)
        return pred_strings
    
    return None


TEAM_NAMES = [
    "The Moral Champions", "The Justice League", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]
CURRENT_TEAM_NAME = random.choice(TEAM_NAMES)

# Team name translations for UI display only (Catalan)
# Internal logic (ranking, caching, grouping) always uses canonical English names
TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Justice League": "The Justice League",
        "The Moral Champions": "The Moral Champions",
        "The Data Detectives": "The Data Detectives",
        "The Ethical Explorers": "The Ethical Explorers",
        "The Fairness Finders": "The Fairness Finders",
        "The Accuracy Avengers": "The Accuracy Avengers"
    },
    "ca": {
        "The Justice League": "La Lliga de la Justícia",
        "The Moral Champions": "Els Campions Morals",
        "The Data Detectives": "Els Detectius de Dades",
        "The Ethical Explorers": "Els Exploradors Ètics",
        "The Fairness Finders": "Els Cercadors d'Equitat",
        "The Accuracy Avengers": "Els Venjadors de Precisió"
    }
}

# UI language for team name display
UI_TEAM_LANG = "ca"


# --- Feature groups for scaffolding (Weak -> Medium -> Strong) ---
FEATURE_SET_ALL_OPTIONS = [
    ("Nombre de delictes greus juvenils", "juv_fel_count"),
    ("Nombre de delictes lleus juvenils", "juv_misd_count"),
    ("Altres delictes juvenils", "juv_other_count"),
    ("Origen ètnic", "race"),
    ("Sexe", "sex"),
    ("Gravetat del càrrec (lleu / greu)", "c_charge_degree"),
    ("Dies abans de l'arrest", "days_b_screening_arrest"),
    ("Edat", "age"),
    ("Dies a la presó", "length_of_stay"),
    ("Nombre de delictes previs", "priors_count"),
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
    "Petita (20%)": 0.2,
    "Mitjana (60%)": 0.6,
    "Gran (80%)": 0.8,
    "Completa (100%)": 1.0
}
DEFAULT_DATA_SIZE = "Petita (20%)"


MAX_ROWS = 4000
TOP_N_CHARGE_CATEGORICAL = 50
np.random.seed(42)

# Global state containers
playground = None

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


def _build_skeleton_leaderboard(rows=6, is_team=True, submit_button_label="5. 🔬 Construir i enviar el model"):
    context_label = "Equip" if is_team else "Individual"
    return f"""
    <div class='lb-placeholder' aria-live='polite'>
        <div class='lb-placeholder-title'>{context_label} · Classificació pendent</div>
        <div class='lb-placeholder-sub'>
            <p style='margin:0 0 6px 0;'>Envia el teu primer model i desbloqueja la classificació!</p>
            <p style='margin:0;'><strong>Fes clic a «{submit_button_label}» (a baix a l’esquerra)</strong> per començar!</p>
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
    <h2 style='color: #111827; margin-top:20px; border-top: 2px solid #e5e7eb; padding-top: 20px;'>🔐 Inicia sessió per enviar i classificar-te</h2>
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
        title = "⏳ Processant l'enviament"
        acc_color = "#3b82f6"  # Blue
        acc_text = f"{(local_test_accuracy * 100):.2f}%" if local_test_accuracy is not None else "N/A"
        
        # Compute provisional diff between local (new) and last score
        if local_test_accuracy is not None and last_score is not None and last_score > 0:
            score_diff = local_test_accuracy - last_score
            if abs(score_diff) < 0.0001:
                acc_diff_html = "<p style='font-size: 1.5rem; font-weight: 600; color: #6b7280; margin:0;'>Sense canvis (↔) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Actualització de la classificació pendent...</p>"
            elif score_diff > 0:
                acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #16a34a; margin:0;'>+{(score_diff * 100):.2f} (⬆️) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Actualització de la classificació pendent...</p>"
            else:
                acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #ef4444; margin:0;'>{(score_diff * 100):.2f} (⬇️) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Actualització de la classificació pendent...</p>"
        else:
            # No last score available - just show pending message
            acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Pending leaderboard update...</p>"
        
        border_color = acc_color
        rank_color = "#6b7280"  # Gray
        rank_text = "Pendent"
        rank_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0;'>Calculant la posició...</p>"
        
    # Handle preview mode - Styled to match "success" card
    elif is_preview:
        title = "🔬 Prova de vista prèvia finalitzada!"
        acc_color = "#16a34a"  # Green (like success)
        acc_text = f"{(new_score * 100):.2f}%" if new_score > 0 else "N/A"
        acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>(Només vista prèvia - no s'ha enviat)</p>" # Neutral color
        border_color = acc_color # Green border
        rank_color = "#3b82f6" # Blue (like rank)
        rank_text = "N/A" # Placeholder
        rank_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0;'>Sense posició (vista prèvia)</p>" # Neutral color
    

    else:
        # 2. Handle Score Changes
        score_diff = new_score - last_score
        if abs(score_diff) < 0.0001:
            title = "✅ Enviament completat!"
            acc_color = "#6b7280" # gray
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>Sense canvis (↔)</p>"
            border_color = acc_color
        elif score_diff > 0:
            title = "✅ Enviament completat!"
            acc_color = "#16a34a" # green
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>+{(score_diff * 100):.2f} (⬆️)</p>"
            border_color = acc_color
        else:
            title = "📉 La puntuació ha baixat"
            acc_color = "#ef4444" # red
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>{(score_diff * 100):.2f} (⬇️)</p>"
            border_color = acc_color

        # 3. Handle Rank Changes
        rank_diff = last_rank - new_rank
        rank_color = "#3b82f6" # blue
        rank_text = f"#{new_rank}"
        if last_rank == 0: # Handle first rank
             rank_diff_html = "<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>¡Ja ets a la taula!</p>"
        elif rank_diff > 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #16a34a; margin:0;'>🚀 ¡Has pujat {rank_diff} posició/ons!</p>"
        elif rank_diff < 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #ef4444; margin:0;'>🔻 Has baixat {abs(rank_diff)} posició/ons!</p>"
        else:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {rank_color}; margin:0;'>Mantens la teva posició (↔)</p>"

    return f"""
    <div class='kpi-card' style='border-color: {border_color};'>
        <h2 style='color: var(--body-text-color); margin-top:0;'>{title}</h2>
        <div class='kpi-card-body'>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>Nova precisió</p>
                <p class='kpi-score' style='color: {acc_color};'>{acc_text}</p>
                {acc_diff_html}
            </div>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>La teva posició</p>
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
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Encara no hi ha enviaments per equips.</p>"

    # Normalize the current user's team name for comparison (using English names)
    normalized_user_team = _normalize_team_name(team_name).lower()

    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Posició</th>
                <th>Equip</th>
                <th>Millor Puntuació</th>
                <th>Mitjana</th>
                <th>Enviaments</th>
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
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Encara no hi ha enviaments individuals.</p>"

    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Posició</th>
                <th>Enginyer/a</th>
                <th>Millor Puntuació</th>
                <th>Enviaments</th>
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
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>La classificació està buida.</p>",
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>La classificació està buida.</p>",
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
    return MODEL_TYPES.get(model_name, {}).get("card_ca", "Descripció no disponible.")

def compute_rank_settings(
    submission_count,
    current_model,
    current_complexity,
    current_feature_set,
    current_data_size
):
    """
    Returns rank gating settings (updated for 1–10 complexity scale).
    Adapted for Catalan UI: Returns Tuple choices [(Display, Value)]
    """

    # Helper to generate feature choices (unchanged logic)
    def get_choices_for_rank(rank):
        return FEATURE_SET_ALL_OPTIONS # Senior+

    # Helper to generate Model Radio Tuples [(Catalan, English)]
    def get_model_tuples(available_english_keys):
        # FIX: Use MODEL_DISPLAY_MAP
        return [(MODEL_DISPLAY_MAP[k], k) for k in available_english_keys if k in MODEL_DISPLAY_MAP]

        
    avail_keys = list(MODEL_TYPES.keys()) # All models

    return {
        "rank_message": "# 👑 Rang: Enginyer/a principal\n<p style='font-size:24px; line-height:1.4;'>Totes les eines desbloquejades — optimitza amb llibertat!</p>",
        "model_choices": get_model_tuples(avail_keys),
        "model_value": current_model if current_model in avail_keys else "The Balanced Generalist",
        "model_interactive": True,
        "complexity_max": 10,
        "complexity_value": current_complexity,
        "feature_set_choices": get_choices_for_rank(3),
        "feature_set_value": current_feature_set,
        "feature_set_interactive": True,
        "data_size_choices": ["Petita (20%)", "Mitjana (60%)", "Gran (80%)", "Completa (100%)"],
        "data_size_value": current_data_size if current_data_size in DATA_SIZE_DB_MAP else "Petita (20%)",
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
        
        # Translate team name for display only (keep team_name_state in English)
        display_team_name = translate_team_name_for_display(team_name, UI_TEAM_LANG)
        
        # Build success message based on whether team is new or existing
        if is_new_team:
            team_message = f"T'hem assignat a un nou equip: <b>{display_team_name}</b> 🎉"
        else:
            team_message = f"Hola de nou! Continues a l'equip: <b>{display_team_name}</b> ✅"
        
        # Success: hide login form, show success message with team info, enable submit button
        success_html = f"""
        <div style='background:#f0fdf4; padding:16px; border-radius:8px; border-left:4px solid #16a34a; margin-top:12px;'>
            <p style='margin:0; color:#15803d; font-weight:600; font-size:1.1rem;'>✓ Signed in successfully!</p>
            <p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>
                {team_message}
            </p>
            <p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>
                Fes clic a "Construir i enviar el model" un altre cop per publicar la teva puntuació.
            </p>
        </div>
        """
        return {
            login_username: gr.update(visible=False),
            login_password: gr.update(visible=False),
            login_submit: gr.update(visible=False),
            login_error: gr.update(value=success_html, visible=True),
            submit_button: gr.update(value="🔬 Construir i enviar el model", interactive=True),
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

def run_experiment(
    model_name_key,
    complexity_level,
    feature_set,
    data_size_str,
    team_name,
    last_submission_score,
    last_rank,
    submission_count,
    first_submission_score,
    best_score,
    username=None,
    token=None,
    readiness_flag=None,
    was_preview_prev=None,
    progress=gr.Progress()
):
    """
    Core experiment using precomputed predictions.
    No runtime training or feature transformation.
    """
    progress(0.1, desc="Iniciant l'experiment...")
    def get_status_html(step_num, title, subtitle):
        return f"""
        <div class='processing-status'>
            <span class='processing-icon'>⚙️</span>
            <div class='processing-text'>Pas {step_num}/5: {title}</div>
            <div class='processing-subtext'>{subtitle}</div>
        </div>
        """
    yield {
        submit_button: gr.update(value="⏳ Experiment en curs...", interactive=False),
        submission_feedback_display: gr.update(value=get_status_html(1, "Iniciant", "Preparant les variables de dades..."), visible=True),
        login_error: gr.update(visible=False),
        attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
    }

    if not model_name_key or model_name_key not in MODEL_TYPES:
        model_name_key = DEFAULT_MODEL
    complexity_level = safe_int(complexity_level, 2)
    if not username:
        username = "Unknown_User"

    sanitized_features = []
    for f in (feature_set or []):
        if isinstance(f, dict):
            sanitized_features.append(f.get("value", str(f)))
        elif isinstance(f, tuple):
            sanitized_features.append(f[1] if len(f) > 1 else str(f))
        else:
            sanitized_features.append(str(f))
    sanitized_features = sorted(sanitized_features)

    db_data_size = DATA_SIZE_DB_MAP.get(data_size_str, "Small (20%)")
    
    _ensure_y_test_loaded()

    progress(0.3, desc="Carregant les prediccions...")
    
    # Build cache key using helper function for consistency
    cache_key = build_cache_key(model_name_key, complexity_level, sanitized_features, db_data_size)
    
    yield {submission_feedback_display: gr.update(value=get_status_html(2, "Carregant prediccions", "⚡ Recuperant resultats precomputats..."), visible=True)}
    
    # Fetch from cache
    cached_predictions = get_cached_prediction(cache_key, db_data_size)
    
    # Fallback: derive majority vote if selected and missing
    if model_name_key == MAJORITY_MODEL_NAME and not cached_predictions:
        base_strings = _fetch_base_pred_strings_for_majority(complexity_level, sanitized_features, db_data_size)
        if base_strings:
            cached_predictions = _compute_majority_string(base_strings, tie_break="random", rng_seed=42)
    
    if not cached_predictions:
        error_html = f"""
        <div style='background:#fee2e2; padding:16px; border-radius:8px; border:2px solid #ef4444; color:#991b1b; text-align:center;'>
            <h3 style='margin:0;'>⚠️ Configuració no trobada</h3>
            <p style='margin:8px 0;'>Aquesta combinació específica de paràmetres no s'ha trobat a la nostra base de dades.</p>
            <p style='font-size:0.9em;'>Si us plau, ajusta la configuració (per exemple, canvia la mida de les dades o l'estratègia del model) i torna-ho a provar.</p>
        </div>
        """
        settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
        yield {
            submission_feedback_display: gr.update(value=error_html, visible=True),
            submit_button: gr.update(value="🔬 Construir i enviar el model", interactive=True),
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
        }
        return

    predictions = np.array([int(c) for c in cached_predictions], dtype=np.uint8)
    from sklearn.metrics import accuracy_score
    local_test_accuracy = accuracy_score(_Y_TEST, predictions)

    if token is None:
        progress(0.6, desc="Calculant la vista prèvia...")
        preview_card_html = _build_kpi_card_html(
            new_score=local_test_accuracy, last_score=0, new_rank=0, last_rank=0,
            submission_count=-1, is_preview=True, is_pending=False, local_test_accuracy=None
        )
        login_prompt_text_html = build_login_prompt_html()
        closing_div_index = preview_card_html.rfind("</div>")
        combined_html = preview_card_html[:closing_div_index] + login_prompt_text_html + "</div>" if closing_div_index != -1 else preview_card_html + login_prompt_text_html
        settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
        yield {
            submission_feedback_display: gr.update(value=combined_html, visible=True),
            submit_button: gr.update(value="Sign In Required", interactive=False),
            login_username: gr.update(visible=True), login_password: gr.update(visible=True),
            login_submit: gr.update(visible=True), login_error: gr.update(value="", visible=False),
            team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True),
            individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False),
            last_submission_score_state: last_submission_score, last_rank_state: last_rank,
            best_score_state: best_score, submission_count_state: submission_count,
            first_submission_score_state: first_submission_score,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)),
            was_preview_state: True, kpi_meta_state: {"was_preview": True, "preview_score": local_test_accuracy, "local_test_accuracy": local_test_accuracy}, last_seen_ts_state: None
        }
        return


    progress(0.5, desc="S'està enviant al núvol...")
    yield {submission_feedback_display: gr.update(value=get_status_html(3, "Enviament en curs", "S'està enviant el model al servidor de la competició..."), visible=True)}
    baseline_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)

    def _submit():
        return playground.submit_model(
            model=None,
            preprocessor=None,
            prediction_submission=predictions.tolist(),
            input_dict={'description': f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})", 'tags': f"team:{team_name},model:{model_name_key}"},
            custom_metadata={'Team': team_name, 'Moral_Compass': 0},
            token=token,
            return_metrics=["accuracy"]
        )

    try:
        submit_result = _retry_with_backoff(_submit, description="model submission")
        if isinstance(submit_result, tuple) and len(submit_result) == 3:
            _, _, metrics = submit_result
            this_submission_score = float(metrics.get("accuracy", local_test_accuracy)) if metrics else local_test_accuracy
        else:
            this_submission_score = local_test_accuracy
    except Exception:
        this_submission_score = local_test_accuracy

    new_submission_count = submission_count + 1
    new_first_submission_score = first_submission_score if first_submission_score is not None else this_submission_score if submission_count == 0 else first_submission_score

    simulated_df = baseline_leaderboard_df.copy() if baseline_leaderboard_df is not None else pd.DataFrame()
    new_row = pd.DataFrame([{"username": username, "accuracy": this_submission_score, "Team": team_name, "timestamp": pd.Timestamp.now(), "version": "latest"}])
    simulated_df = pd.concat([simulated_df, new_row], ignore_index=True) if not simulated_df.empty else new_row

    team_html, individual_html, _, new_best_accuracy, new_rank, _ = generate_competitive_summary(simulated_df, team_name, username, last_submission_score, last_rank, submission_count)
    kpi_card_html = _build_kpi_card_html(new_score=this_submission_score, last_score=last_submission_score, new_rank=new_rank, last_rank=last_rank, submission_count=submission_count, is_preview=False, is_pending=False)

    progress(1.0, desc="Complet!")
    limit_reached = False
    if limit_reached:
        limit_html = f"""
        <div style='margin-top: 16px; border: 2px solid #ef4444; background:#fef2f2; padding:16px; border-radius:12px; text-align:left;'>
            <h3 style='margin:0 0 8px 0; color:#991b1b;'>🛑 Límit d'enviaments assolit ({ATTEMPT_LIMIT}/{ATTEMPT_LIMIT})</h3>
            <p style='margin:0; color:#7f1d1d; line-height:1.4;'>Revisa els teus resultats finals a dalt i baixa fins a «Finalitzar i reflexionar» per continuar.</p>
        </div>"""
        final_html_display = kpi_card_html + limit_html
        button_update = gr.update(value="🛑 Límit assolit", interactive=False)
        interactive_state = False
        tracker_html = _build_attempts_tracker_html(new_submission_count)
    else:
        final_html_display = kpi_card_html
        button_update = gr.update(value="🔬 Construir i enviar model", interactive=True)
        interactive_state = True
        tracker_html = _build_attempts_tracker_html(new_submission_count)

    settings = compute_rank_settings(new_submission_count, model_name_key, complexity_level, feature_set, data_size_str)
    yield {
        submission_feedback_display: gr.update(value=final_html_display, visible=True),
        team_leaderboard_display: team_html,
        individual_leaderboard_display: individual_html,
        last_submission_score_state: this_submission_score,
        last_rank_state: new_rank,
        best_score_state: new_best_accuracy,
        submission_count_state: new_submission_count,
        first_submission_score_state: new_first_submission_score,
        rank_message_display: settings["rank_message"],
        model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=(settings["model_interactive"] and interactive_state)),
        complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"], interactive=interactive_state),
        feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=(settings["feature_set_interactive"] and interactive_state)),
        data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=(settings["data_size_interactive"] and interactive_state)),
        submit_button: button_update,
        login_username: gr.update(visible=False), login_password: gr.update(visible=False),
        login_submit: gr.update(visible=False), login_error: gr.update(visible=False),
        attempts_tracker_display: gr.update(value=tracker_html),
        was_preview_state: False,
        kpi_meta_state: {"was_preview": False, "preview_score": None, "local_test_accuracy": local_test_accuracy, "this_submission_score": this_submission_score, "new_best_accuracy": new_best_accuracy, "rank": new_rank},
        last_seen_ts_state: time.time()
    }


def on_initial_load(username, token=None, team_name=""):
    """
    Load initial UI state. Immediately ready since predictions are precomputed.
    """
    _ensure_y_test_loaded()
    
    initial_ui = compute_rank_settings(
        0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE
    )

    # 1. Prepare the Welcome HTML
    # Translate team name to Catalan for display only (keep team_name in English for logic)
    display_team = translate_team_name_for_display(team_name, UI_TEAM_LANG) if team_name else "El teu equip"
    
    welcome_html = f"""
    <div style='text-align:center; padding: 30px 20px;'>
        <div style='font-size: 3rem; margin-bottom: 10px;'>👋</div>
        <h3 style='margin: 0 0 8px 0; color: #111827; font-size: 1.5rem;'>Ja formes part de l'equip: <b>{display_team}</b>!</h3>
        <p style='font-size: 1.1rem; color: #4b5563; margin: 0 0 20px 0;'>
            El teu equip necessita la teva ajuda per millorar la IA.
        </p>
        
        <div style='background:#eff6ff; padding:16px; border-radius:12px; border:2px solid #bfdbfe; display:inline-block;'>
            <p style='margin:0; color:#1e40af; font-weight:bold; font-size:1.1rem;'>
                👈 Fes clic a 'Construir i enviar model' per començar!
            </p>
        </div>
    </div>
    """

    full_leaderboard_df = None
    try:
        if playground:
            full_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
    except Exception as e:
        print(f"Error on initial load fetch: {e}")
        full_leaderboard_df = None

    # -------------------------------------------------------------------------
    # LOGIC UPDATE: Check if THIS user has submitted anything
    # -------------------------------------------------------------------------
    user_has_submitted = False
    if full_leaderboard_df is not None and not full_leaderboard_df.empty:
        if "username" in full_leaderboard_df.columns and username:
            # Check if the username exists in the dataframe
            user_has_submitted = username in full_leaderboard_df["username"].values

    # Decision Logic
    if not user_has_submitted:
        # CASE 1: New User (or first time loading session) -> FORCE WELCOME
        # regardless of whether the leaderboard has other people's data.
        team_html = welcome_html
        individual_html = "<p style='text-align:center; color:#6b7280; padding-top:40px;'>Envia el teu model per veure la teva posició a la classificació!</p>"
        
    elif full_leaderboard_df is None or full_leaderboard_df.empty:
        # CASE 2: Returning user, but data fetch failed -> Show Skeleton
        team_html = _build_skeleton_leaderboard(rows=6, is_team=True)
        individual_html = _build_skeleton_leaderboard(rows=6, is_team=False)
        
    else:
        # CASE 3: Returning user WITH data -> Show Real Tables
        try:
            team_html, individual_html, _, _, _, _ = generate_competitive_summary(
                full_leaderboard_df,
                team_name,
                username,
                0, 0, -1
            )
        except Exception as e:
            print(f"Error generating summary HTML: {e}")
            team_html = "<p style='text-align:center; color:red; padding-top:20px;'>S'ha produït un error en carregar la classificació.</p>"
            individual_html = "<p style='text-align:center; color:red; padding-top:20px;'>S'ha produït un error en mostrar la classificació.</p>"

    return (
        get_model_card(DEFAULT_MODEL),
        team_html,
        individual_html,
        initial_ui["rank_message"],
        gr.update(choices=initial_ui["model_choices"], value=initial_ui["model_value"], interactive=initial_ui["model_interactive"]),
        gr.update(minimum=1, maximum=initial_ui["complexity_max"], value=initial_ui["complexity_value"]),
        gr.update(choices=initial_ui["feature_set_choices"], value=initial_ui["feature_set_value"], interactive=initial_ui["feature_set_interactive"]),
        gr.update(choices=initial_ui["data_size_choices"], value=initial_ui["data_size_value"], interactive=initial_ui["data_size_interactive"]),
    )


# -------------------------------------------------------------------------
# Conclusion helpers (dark/light mode aware)
# -------------------------------------------------------------------------
def build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set):
    """
    Build the FINAL certification slide.
    Reflects the end of the course, the Barcelona competition, and the certification.
    """
    # Calculate improvement if valid
    improvement = (best_score - first_score) if (first_score is not None and submissions > 1) else 0.0

    # 1. Logic for the "Attempt Cap" (Modified to be final)
    attempt_msg = ""
    
    # 2. Logic for a "Low Submission" nudge (Optional, but kept for feedback)
    tip_html = ""

    # 3. Construct the HTML
    return f"""
    <div class="final-conclusion-root">
      
      <h1 class="final-conclusion-title">🎓 Certificació Assolida</h1>
      <h2 style="margin-top:0; color:var(--text-muted);">Ètica en Joc: Justícia i Equitat</h2>

      <div class="final-conclusion-card">
        
        <h3 class="final-conclusion-subtitle">🏆 Resultats del Repte Final</h3>
        <p style="text-align:left; margin-bottom: 15px;">
            El teu sistema d'IA final ha entrat al registre per a l'<b>EdTech Congress Barcelona 2026</b>.
        </p>

        <ul class="final-conclusion-list">
          <li>🏁 <b>Precisió Final:</b> {(best_score * 100):.2f}%</li>
          <li>🌍 <b>Rànquing Global:</b> {('#' + str(rank)) if rank > 0 else 'Pendent'}</li>
          <li>📈 <b>Millora en aquesta sessió:</b> {(improvement * 100):+.2f}% de guany en precisió</li>
          <li>🔢 <b>Iteracions Totals:</b> {submissions} versions del model provades</li>
        </ul>

        {tip_html}
        {attempt_msg}

        <hr class="final-conclusion-divider" />

        <div class="final-conclusion-next">
          <h2>El Viatge Continua</h2>
          
          <div style="text-align: left; margin-top: 15px;">
              <p>Enhorabona! Has completat la <b>Certificació Ètica en Joc en Justícia i Equitat</b> i has vist com la IA pot afectar les decisions del món real.</p>
              
              <p>A través d'aquest repte, has après a:</p>
              <ul style="margin-bottom: 15px;">
                  <li>Revisar dades per detectar biaixos</li>
                  <li>Entendre l'impacte de les decisions de la IA</li>
                  <li>Construir sistemes d'IA que siguin justos, no només precisos</li>
                  <li>Explicar l'equilibri entre eficiència i equitat</li>
              </ul>

              <div class="final-conclusion-ethics">
                <p style="margin:0;">
                    <b>Reflexió Final:</b> A mesura que avances, recorda que l'ètica no és una tasca puntual. 
                    És una cosa que has de tenir en compte en cada pas. Has demostrat com construir una IA que no només funcioni, sinó que funcioni per a tothom.
                </p>
              </div>

              <p style="text-align:center; margin-top: 25px; font-weight:bold; font-size:1.1rem;">
                Gràcies per jugar, i molta sort amb els teus reptes futurs.
              </p>
          </div>
        </div>

      </div>
    </div>
    """



def build_conclusion_from_state(best_score, submissions, rank, first_score, feature_set):
    return build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set)
def create_model_building_game_ca_final_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """
    Create (but do not launch) the model building game app.
    """
    # Initialize Competition once at startup
    global playground
    if playground is None:
        try:
            playground = Competition(MY_PLAYGROUND_ID)
            print("✅ Competition connection initialized successfully")
        except Exception as e:
            print(f"⚠️ WARNING: Could not connect to playground: {e}")
            playground = None

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
    /* ---------- NEW: Countdown & Interactive Slide Styles ---------- */

    /* 1. Launch Banner (Slide 1) */
    .launch-banner {
        background: #111827;
        color: #4ade80;
        font-family: monospace;
        text-align: center;
        padding: 8px;
        font-size: 0.9rem;
        letter-spacing: 2px;
        margin: -24px -24px 24px -24px; /* Stretch to edges of panel */
        border-bottom: 2px solid #4ade80;
        border-radius: var(--slide-radius-lg) var(--slide-radius-lg) 0 0;
    }

    /* 2. T-Minus Headers */
    .t-minus-header {
        text-align: center;
        margin-bottom: 24px;
        border-bottom: 2px solid var(--card-border-subtle);
        padding-bottom: 16px;
    }
    
    .t-minus-badge {
        display: inline-block;
        background: var(--text-main);
        color: var(--body-background-fill);
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }

    .t-minus-title {
        margin: 0;
        font-size: 2.2rem;
        color: var(--accent-strong);
        font-weight: 800;
    }

    /* 3. Styled Details/Summary (Click-to-reveal) */
    details.styled-details {
        margin-bottom: 12px;
        background: var(--block-background-fill);
        border-radius: 10px;
        border: 1px solid var(--card-border-subtle);
        overflow: hidden;
    }

    details.styled-details > summary {
        list-style: none;
        cursor: pointer;
        padding: 16px;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: var(--prose-background-fill);
        transition: background 0.2s;
        color: var(--text-main);
    }

    details.styled-details > summary:hover {
        background: var(--block-background-fill);
        color: var(--accent-strong);
    }

    /* Hide default triangle */
    details.styled-details > summary::-webkit-details-marker {
        display: none;
    }

    /* Custom +/- indicator */
    details.styled-details > summary::after {
        content: '+';
        font-size: 1.5rem;
        font-weight: 400;
        color: var(--text-muted);
    }

    details.styled-details[open] > summary::after {
        content: '−';
        color: var(--accent-strong);
    }

    details.styled-details > div.content {
        padding: 16px;
        border-top: 1px solid var(--card-border-subtle);
        background: var(--block-background-fill);
        color: var(--text-main);
    }

    /* 4. Mock UI Widgets (for Slide 4) */
    .widget-row { display: flex; align-items: center; margin-bottom: 8px; color: var(--text-main); font-size: 1rem; }
    
    .radio-circle { 
        width: 16px; height: 16px; border-radius: 50%; 
        border: 2px solid var(--text-muted); margin-right: 10px; display: inline-block; 
    }
    .radio-circle.selected { 
        border-color: var(--accent-strong); 
        background: radial-gradient(circle, var(--accent-strong) 40%, transparent 50%); 
    }
    
    .check-square { 
        width: 16px; height: 16px; border-radius: 4px; 
        border: 2px solid var(--text-muted); margin-right: 10px; display: inline-block; 
    }
    .check-square.checked { 
        background: var(--accent-strong); border-color: var(--accent-strong); position: relative; 
    }
    
    .slider-track { 
        height: 6px; background: var(--border-color-primary); border-radius: 3px; 
        width: 100%; position: relative; margin: 12px 0; 
    }
    .slider-thumb { 
        width: 18px; height: 18px; background: var(--accent-strong); 
        border-radius: 50%; position: absolute; left: 20%; top: -6px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.3); 
    }
    
    .risk-tag { 
        background: #fef2f2; color: #ef4444; border: 1px solid #fecaca; 
        font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; 
        margin-left: 8px; vertical-align: middle; font-weight: 700; 
    }
    
    /* Pop-up info box inside details */
    .info-popup {
        background: color-mix(in srgb, var(--color-accent) 5%, transparent);
        border-left: 4px solid var(--color-accent);
        padding: 12px;
        margin-top: 12px;
        border-radius: 4px;
        font-size: 0.95rem;
        color: var(--text-main);
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
                    <h2 style='font-size:2rem; color:#6b7280;'>⏳ Carregant...</h2>
                </div>
                """
            )

        # --- Briefing Slideshow (Updated with New Cards) ---
  
        with gr.Column(visible=True, elem_id="intro-slide") as intro_slide:
                    gr.Markdown("<h1 style='text-align:center;'>🚀 El repte final</h1>")
                    
                    gr.HTML(
                        """
                        <div class='slide-content'>
                            <div class='panel-box'>
                                
                                <div class="final-intro-wrapper">
                                    <p class="final-intro-text">
                                        Has analitzat els aspectes ètics del sistema. Has identificat i corregit biaixos.
                                        <br>
                                        Ara és el moment de posar-ho tot en pràctica.
                                    </p>
                                </div>
                
                                <div class="final-mission-card">
                                    <h3 class="final-mission-title">🛠️ La competició d'IA ètica</h3>
                                    <div class="final-mission-body">
                                        <p>La teva missió final és tornar a competir contra els teus companys construint un <strong>sistema d'IA més precís dins dels estàndards ètics</strong>. Un cop tractat el biaix, la precisió torna a ser prioritària.</p>
                                        
                                        <p>Utilitza el que has après per escalar posicions a la classificació de manera responsable, perquè el rendiment importa, però també les conseqüències de les decisions de disseny.</p>
                                    </div>
                                </div>
        
                                <div class="t-minus-header" style="margin-top:12px;">
                                    <span class="t-minus-badge">Novetats</span>
                                    <h2 class="t-minus-title">Més dades i una nova estratègia de model</h2>
                                </div>
                                <ul style="margin:0 0 12px 0;">
                                    <li><b>Complet (100%)</b> ara inclou <b>més de 3.000 casos addicionals</b>.</li>
                                    <li>Estratègia de model de <b>Vot majoritari</b> (Un model de vot majoritari selecciona la predicció majoritària entre les prediccions dels quatre models base).</li>
                                </ul>
                
                                <div class="final-cta-wrapper">
                                    <p class="final-cta-head">
                                        A punt per començar?
                                    </p>
                                    <p class="final-cta-sub">
                                        👇 Fes clic a <b>“Entrar a la competició”</b> per començar.
                                    </p>
                                </div>
                
                            </div>
                        </div>
                        """
                    )
                    
                    # Only ONE button needed now
                    intro_next_btn = gr.Button("Entrar a la competició ▶️", variant="primary", size="lg")
  
        # Slide 2: Mission
        with gr.Column(visible=False, elem_id="slide-2") as briefing_slide_2:
            gr.Markdown("<h1 style='text-align:center;'>📋 La teva missió: Crear un sistema d'IA millor</h1>")
            gr.HTML("""
                <div class='slide-content'>
                    <div class='panel-box'>
                        <h3>La missió</h3>
                        <p>Construeix un sistema d'IA que ajudi a millorar les decisions judicials. El teu objectiu és predir el risc de reincidència amb més precisió que el sistema anterior.</p>
                        
                        <h3>La competició</h3>
                        <p>Per fer-ho, competiràs amb altres professionals d'enginyeria! T'uniràs a un equip i podràs seguir tant el rendiment individual com el d’equip a les classificacions en temps real.</p>
                        <div style="background:var(--background-fill-secondary); padding:8px 12px; border-radius:8px; margin-bottom:12px; border:1px solid var(--border-color-primary);">
                             T'uniràs a un equip com ara… <b>🛡️ Els Exploradors Ètics</b>
                        </div>
  
                        <h3>El repte de les dades</h3>
                        <p>Per competir, tindràs accés a milers d'arxius de casos antics que contenen <b>perfils de persones acusades</b> (edat, historial) i <b>resultats històrics</b> (hi ha reincidència o no).</p>
                        <p>La teva tasca és crear un sistema d'IA que aprengui dels perfils i predigui el resultat amb precisió. A punt per construir alguna cosa que podria canviar la manera com funciona la justícia?</p>
                    </div>
                </div>
            """)
            with gr.Row():
                briefing_2_back = gr.Button("◀️ Enrere", size="lg")
                briefing_2_next = gr.Button("Següent ▶️", variant="primary", size="lg")
  
        # Slide 3: Concept
        with gr.Column(visible=False, elem_id="slide-3") as briefing_slide_3:
            gr.Markdown("<h1 style='text-align:center;'>🧠 Què és un sistema d'IA?</h1>")
            gr.HTML("""
                <div class='slide-content'>
                    <div class='panel-box'>
                        <p>Imagina't un sistema d'IA com una "màquina de predicció". Es construeix amb tres components principals:</p>
                        <p><strong>1. Les entrades:</strong> Les dades que li subministres (ex: edat, delictes).</p>
                        <p><strong>2. El model (el "cervell"):</strong> Les matemàtiques (algorisme) que troben patrons.</p>
                        <p><strong>3. La sortida:</strong> La predicció (ex: nivell de risc).</p>
                    </div>
                </div>
            """)
            with gr.Row():
                briefing_3_back = gr.Button("◀️ Enrere", size="lg")
                briefing_3_next = gr.Button("Següent ▶️", variant="primary", size="lg")
  
        # Slide 4: The Loop
        with gr.Column(visible=False, elem_id="slide-4") as briefing_slide_4:
            gr.Markdown("<h1 style='text-align:center;'>🔁 Com treballen els equips d'enginyeria: el cicle</h1>")
            gr.HTML("""
                <div class='slide-content'>
                    <div class='panel-box'>
                        <p>Els equips d’IA reals gairebé mai ho encerten a la primera. Segueixen un cicle: <strong>provar, avaluar, aprendre, repetir.</strong></p>
                        <p>Faràs exactament el mateix en aquesta competició:</p>
                        <div class='step-visual'>
                            <div class='step-visual-box'><b>1. Configura</b><br><span style='font-size:0.85rem'>tria el model i les dades</span></div>→
                            <div class='step-visual-box'><b>2. Envia</b><br><span style='font-size:0.85rem'>entrena el teu sistema</span></div>→
                            <div class='step-visual-box'><b>3. Analitza</b><br><span style='font-size:0.85rem'>consulta la classificació</span></div>→
                            <div class='step-visual-box'><b>4. Refina</b><br><span style='font-size:0.85rem'>ajusta i torna-ho a provar</span></div>
                        </div>
                    </div>
                </div>
            """)
            
            with gr.Row():
                briefing_4_back = gr.Button("◀️ Enrere", size="lg")
                briefing_4_next = gr.Button("Següent ▶️", variant="primary", size="lg")
  
        # Slide 5: Systems Check (Controls)
        with gr.Column(visible=False, elem_id="slide-5") as briefing_slide_5:
            gr.HTML(
                """
                <div class='slide-content'>
                    <div class='panel-box'>
                        <div class='t-minus-header'>
                            <h2 class='t-minus-title' style='color: var(--body-text-color);'>🔧 Revisió dels controls d'enginyeria</h2>
                        </div>
            
                        <div style='background: color-mix(in srgb, var(--color-accent) 10%, transparent); border:1px solid var(--color-accent); padding:16px; border-radius:10px; text-align:center; margin-bottom:24px;'>
                            <strong style='color: var(--color-accent); font-size:1.1rem;'>⚠️ MODE DE SIMULACIÓ ACTIU</strong>
                            <p style='margin:8px 0 0 0; color: var(--body-text-color); font-size:1.05rem; line-height:1.4;'>
                                A continuació tens els <b>4 controls</b> que utilitzaràs per construir el teu sistema d'IA en el pas següent.<br>
                                <b>Fes clic a cadascun ara</b> per entendre què fan abans que comenci la competició.
                            </p>
                        </div>
            
                        <details class="styled-details" style="border: 1px solid var(--border-color-primary); padding: 8px; border-radius: 8px; margin-bottom: 8px;">
                            <summary style="cursor: pointer; font-weight: 600; color: var(--body-text-color);">1. Estratègia del model (el "cervell")</summary>
                            <div class="content" style="padding-top: 12px; padding-left: 12px;">
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);"><span class="radio-circle selected" style="display:inline-block; width:12px; height:12px; border-radius:50%; background:var(--color-accent); margin-right:8px;"></span> <b>El Generalista Equilibrat</b></div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color-subdued);"><span class="radio-circle" style="display:inline-block; width:12px; height:12px; border-radius:50%; border:1px solid var(--body-text-color-subdued); margin-right:8px;"></span> El Creador de Regles</div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color-subdued);"><span class="radio-circle" style="display:inline-block; width:12px; height:12px; border-radius:50%; border:1px solid var(--body-text-color-subdued); margin-right:8px;"></span> El Detector de Patrons Profunds</div>
                                
                                <div class="info-popup" style="background: var(--background-fill-secondary); padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color-primary);">
                                    <b style="color: var(--body-text-color);">En el joc:</b> <span style="color: var(--body-text-color);">Triaràs una d'aquestes estratègies de model. Cada estratègia permet que el model aprengui de les dades d’entrada d’una manera diferent.</span><br>
                                    <i style="color: var(--body-text-color-subdued);">Consell: Comença amb el "Generalista Equilibrat" per obtenir una puntuació base segura i fiable.</i>
                                </div>
                            </div>
                        </details>
            
                        <details class="styled-details" style="border: 1px solid var(--border-color-primary); padding: 8px; border-radius: 8px; margin-bottom: 8px;">
                            <summary style="cursor: pointer; font-weight: 600; color: var(--body-text-color);">2. Complexitat del model (nivell de focus)</summary>
                            <div class="content" style="padding-top: 12px; padding-left: 12px;">
                                <div class="slider-track" style="height: 4px; background: var(--neutral-200); margin: 16px 0; position: relative;"><div class="slider-thumb" style="width: 16px; height: 16px; background: var(--color-accent); border-radius: 50%; position: absolute; left: 50%; top: -6px;"></div></div>
                                <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--body-text-color-subdued);">
                                    <span>Nivell 1 (general)</span>
                                    <span>Nivell 10 (específic)</span>
                                </div>
                                
                                <div class="info-popup" style="background: var(--background-fill-secondary); padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color-primary);">
                                    <b style="color: var(--body-text-color);">En el joc:</b> <span style="color: var(--body-text-color);">Pensa-hi com <b>estudiar vs. memoritzar</b>.</span><br>
                                    <span style="color: var(--body-text-color);">• <b>Complexitat baixa:</b> La IA aprèn conceptes generals (bo per a casos nous).</span><br>
                                    <span style="color: var(--body-text-color);">• <b>Complexitat alta:</b> La IA memoritza les respostes (dolent per a casos nous).</span><br>
                                    <strong style="color:#ef4444;">⚠️ El parany:</strong> <span style="color: var(--body-text-color);">un nivell alt pot semblar perfecte a la prova pràctica, però falla al món real perquè la IA només ha memoritzat les respostes.</span>
                                </div>
                            </div>
                        </details>
            
                        <details class="styled-details" style="border: 1px solid var(--border-color-primary); padding: 8px; border-radius: 8px; margin-bottom: 8px;">
                            <summary style="cursor: pointer; font-weight: 600; color: var(--body-text-color);">3. Variables de dades (les entrades)</summary>
                            <div class="content" style="padding-top: 12px; padding-left: 12px;">
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);">
                                    <span style="color:var(--color-accent); font-weight:bold;">☑</span> <b>Delictes anteriors</b>
                                </div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);">
                                    <span style="color:var(--color-accent); font-weight:bold;">☑</span> <b>Grau del càrrec delictiu</b>
                                </div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);">
                                    <span style="color:var(--neutral-400); font-weight:bold;">☐</span> <b>Dades demogràfiques (origen ètnic/sexe)</b> <span class="risk-tag" style="background:#fef2f2; color:#b91c1c; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold;">⚠️ RISC</span>
                                </div>
                                
                                <div class="info-popup" style="background: var(--background-fill-secondary); padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color-primary);">
                                    <b style="color: var(--body-text-color);">En el joc:</b> <span style="color: var(--body-text-color);">marcaràs caselles per decidir quines dades d’entrada pot utilitzar la IA per aprendre nous patrons.</span><br>
                                    <strong style="color:#ef4444;">⚠️ Risc ètic:</strong> <span style="color: var(--body-text-color);">Pots utilitzar les dades demogràfiques per millorar la teva puntuació, però és just?</span>
                                </div>
                            </div>
                        </details>
            
                        <details class="styled-details" style="border: 1px solid var(--border-color-primary); padding: 8px; border-radius: 8px;">
                            <summary style="cursor: pointer; font-weight: 600; color: var(--body-text-color);">4. Mida de les dades (volum)</summary>
                            <div class="content" style="padding-top: 12px; padding-left: 12px;">
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);"><span class="radio-circle selected" style="display:inline-block; width:12px; height:12px; border-radius:50%; background:var(--color-accent); margin-right:8px;"></span> <b>Petita (20%)</b> - La IA aprèn ràpid, però veu menys dades.</div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color-subdued);"><span class="radio-circle" style="display:inline-block; width:12px; height:12px; border-radius:50%; border:1px solid var(--body-text-color-subdued); margin-right:8px;"></span> <b>Completa (100%)</b> - La IA veu més dades, però aprèn més lentament.</div>
                                
                                <div class="info-popup" style="background: var(--background-fill-secondary); padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color-primary);">
                                    <b style="color: var(--body-text-color);">En el joc:</b> <span style="color: var(--body-text-color);">Decideixes quina quantitat d’historial de dades llegeix el model.</span><br>
                                    <i style="color: var(--body-text-color-subdued);">Consell: Fes servir "Petita" per provar idees ràpidament. Fes servir "Completa" quan creguis que tens una estratègia guanyadora.</i>
                                </div>
                            </div>
                        </details>
            
                    </div>
                </div>
                """
            )
            
            with gr.Row():
                briefing_5_back = gr.Button("◀️ Enrere", size="lg")
                briefing_5_next = gr.Button("Següent ▶️", variant="primary", size="lg")
  
        # Slide 6: Final Score
        with gr.Column(visible=False, elem_id="slide-6") as briefing_slide_6:            
            gr.HTML(
                """
                <div class='slide-content'>
                    <div class='panel-box'>
                        <div class='t-minus-header'>
                            <h2 class='t-minus-title'>🚀 Les claus finals: el veredicte de la missió</h2>
                        </div>
                        
                        <p style='font-size: 1.15rem; text-align:center; margin-bottom: 24px;'>
                            Accés concedit. Així és com es jutjarà la teva feina.
                        </p>
            
                        <div style='background:var(--prose-background-fill); padding:20px; border-radius:12px; text-align:left; margin-bottom:24px;'>
                            <div style='display:flex; align-items:center; gap:8px; margin-bottom:12px;'>
                                <span style='font-size:1.5rem;'>🔐</span>
                                <strong style='font-size:1.2rem; color:#eef2ff;'>Com guanyar</strong>
                            </div>
                            
                            <p style='margin-bottom:12px;'>
                                Al món real, no coneixem el futur. Per simular-ho, hem amagat el 20% dels arxius de casos (dades) en una "caixa forta".
                            </p>
                            
                            <ul style='margin:0; padding-left:24px; color:var(--text-muted); line-height:1.6;'>
                                <li style='margin-bottom:8px;'>
                                    El teu sistema d'IA aprendrà de les dades d'entrada que li donis, però serà avaluat amb les dades amagades a la "caixa forta".
                                </li>
                                <li>
                                    <b>La teva puntuació:</b> es calcula segons la precisió de la predicció. Si obtens un 50%, la teva IA bàsicament està endevinant (com fer un cara o creu). El teu objectiu és dissenyar un sistema que faci prediccions molt més precises!
                                </li>
                            </ul>
                        </div>
            
                        <div style='text-align:center; border-top:1px solid var(--card-border-subtle); padding-top:20px; margin-bottom:30px;'>
                            <h3 style='margin:0 0 8px 0; font-size:1.2rem;'>Desbloqueja rangs</h3>
                            <p style='margin-bottom:16px; font-size:0.95rem; color:var(--text-muted);'>
                                A mesura que refinis el teu model i pugis a la classificació, guanyaràs nous rangs:
                            </p>
                            <div style='display:inline-flex; gap:12px; flex-wrap:wrap; justify-content:center;'>
                                <span style='padding:6px 12px; background:#f3f4f6; border-radius:20px; font-size:0.9rem;color:#4338ca;'>⭐ En pràctiques</span>
                                <span style='padding:6px 12px; background:#e0e7ff; border-radius:20px; font-size:0.9rem; color:#4338ca;'>⭐⭐ Júnior</span>
                                <span style='padding:6px 12px; background:#fae8ff; border-radius:20px; font-size:0.9rem; color:#86198f;'>⭐⭐⭐ Sènior</span>
                            </div>
                        </div>
                        
                        <div style='text-align:center; background: color-mix(in srgb, var(--color-accent) 10%, transparent); padding: 20px; border-radius: 12px; border: 2px solid var(--color-accent);'>
                            <p style='margin:0 0 8px 0; font-size: 1.1rem; color: var(--text-muted);'>Per començar la competició:</p>
                            <b style='color:var(--accent-strong); font-size:1.3rem;'>Fes clic a "Començar" i després a "Construir i enviar el model"</b>
                            <p style='margin:8px 0 0 0; font-size: 1rem;'>Així, la teva primera puntuació apareixerà a la classificació.</p>
                        </div>
                    </div>
                </div>
                """
            )
            
            with gr.Row():
                briefing_6_back = gr.Button("◀️ Enrere", size="lg")
                briefing_6_next = gr.Button("Començar la construcció del model ▶️", variant="primary", size="lg")

        # --- End Briefing Slideshow ---


        # Model Building App (Main Interface)
        with gr.Column(visible=False, elem_id="model-step") as model_building_step:
            gr.Markdown("<h1 style='text-align:center;'>🛠️ Àrea de construcció de models</h1>")
            
            # Status panel for initialization progress - HIDDEN
            init_status_display = gr.HTML(value="", visible=False)
            

            # Session-based authentication state objects
            # Concurrency Note: These are initialized to None/empty and populated
            # during handle_load_with_session_auth. Do NOT use os.environ here.
            username_state = gr.State(None)
            token_state = gr.State(None)
            
            team_name_state = gr.State(None)  # Populated via handle_load_with_session_auth
            last_submission_score_state = gr.State(0.0)
            last_rank_state = gr.State(0)
            best_score_state = gr.State(0.0)
            submission_count_state = gr.State(0)
            first_submission_score_state = gr.State(None)
            
            # New states for readiness gating and preview tracking
            readiness_state = gr.State(False)
            was_preview_state = gr.State(False)
            kpi_meta_state = gr.State({})
            last_seen_ts_state = gr.State(None)  # Track last seen user timestamp

            # Buffered states for all dynamic inputs
            model_type_state = gr.State(DEFAULT_MODEL)
            complexity_state = gr.State(2)
            feature_set_state = gr.State(DEFAULT_FEATURE_SET)
            data_size_state = gr.State(DEFAULT_DATA_SIZE)

            rank_message_display = gr.Markdown("### Carregant la classificació...")
            with gr.Row():
                with gr.Column(scale=1):

                    model_type_radio = gr.Radio(
                        label="1. Estratègia del model",
                        choices=MODEL_RADIO_CHOICES, # Uses the list of tuples [(Cat, En), ...]
                        value=DEFAULT_MODEL,         # "The Balanced Generalist"
                        interactive=False
                    )
                    model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL))

                    gr.Markdown("---") # Separator

                    complexity_slider = gr.Slider(
                        label="2. Complexitat del model (1–10)",
                        minimum=1, maximum=3, step=1, value=2,
                        info="Valors més alts aprenen més, però un excés pot empitjorar els resultats."
                    )

                    gr.Markdown("---") # Separator

                    feature_set_checkbox = gr.CheckboxGroup(
                        label="3. Selecciona les variables de dades",
                        choices=FEATURE_SET_ALL_OPTIONS,
                        value=DEFAULT_FEATURE_SET,
                        interactive=False,
                        info="Desbloqueja més variables a mesura que puges de posició!"
                    )

                    gr.Markdown("---") # Separator

                    data_size_radio = gr.Radio(
                        label="4. Mida de les dades",
                        choices=[DEFAULT_DATA_SIZE],
                        value=DEFAULT_DATA_SIZE,
                        interactive=False
                    )

                    gr.Markdown("---") # Separator

                    # Attempt tracker display
                    attempts_tracker_display = gr.HTML(
                        value="",  # keep empty
                        visible=False  # keep hidden
                    )
                    submit_button = gr.Button(
                        value="5. 🔬 Construir i enviar el model",
                        variant="primary",
                        size="lg"
                    )

                with gr.Column(scale=1):
                    gr.HTML(
                        """
                        <div class='leaderboard-box'>
                            <h3 style='margin-top:0;'>🏆 Classificació en directe</h3>
                            <p style='margin:0;'>Envia un model per veure la teva posició.</p>
                        </div>
                        """
                    )

                    # KPI Card
                    submission_feedback_display = gr.HTML(
                        "<p style='text-align:center; color:#6b7280; padding:20px 0;'>Envia el teu primer model per obtenir una valoració!</p>"
                    )
                    
                    # Inline Login Components (initially hidden)
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

                    with gr.Tabs():
                        with gr.TabItem("Classificació per equips"):
                            team_leaderboard_display = gr.HTML(
                                "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Envia un model per veure la classificació dels equips.</p>"
                            )
                        with gr.TabItem("Classificació individual"):
                            individual_leaderboard_display = gr.HTML(
                                "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Envia un model per veure la classificació individual.</p>"
                            )

            # REMOVED: Ethical Reminder HTML Block
            step_2_next = gr.Button("Finalitzar i reflexionar ▶️", variant="secondary")

        # Conclusion Step
        with gr.Column(visible=False, elem_id="conclusion-step") as conclusion_step:
            gr.Markdown("<h1 style='text-align:center;'>✅ Secció completada</h1>")
            final_score_display = gr.HTML(value="<p>Preparant el resum final...</p>")
            step_3_back = gr.Button("◀️ Tornar a l'experiment")

        # --- Navigation Logic ---
        all_steps_nav = [
            intro_slide,
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
        def nav_js(target_id: str, message: str, min_show_ms: int = 1200, notify_parent: bool = False) -> str:
            """
            Generate JavaScript for enhanced slide navigation with loading overlay.
            """
            
            # CHANGE 2: Prepare the notification code
            notification_code = ""
            if notify_parent:
                notification_code = "try { window.parent.postMessage('model-updated', '*'); } catch(e) { console.warn(e); }"

            return f"""
            ()=>{{
              {notification_code} 
              try {{
                // Show overlay immediately
                const overlay = document.getElementById('nav-loading-overlay');
                const messageEl = document.getElementById('nav-loading-text');
                
                // ... (Keep the rest of your existing JS logic exactly the same) ...
                
                if(overlay && messageEl) {{
                  messageEl.textContent = '{message}';
                  overlay.style.display = 'flex';
                  setTimeout(() => {{ overlay.style.opacity = '1'; }}, 10);
                }}
                
                const startTime = Date.now();
                
                // Scroll to top after brief delay
                setTimeout(() => {{
                  const anchor = document.getElementById('app_top_anchor');
                  // ... (rest of scroll logic) ...
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
                
                // Poll for target visibility
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
        
        # Final Step: Slide 6 -> Model Building Interface
        intro_next_btn.click(
            fn=create_nav(intro_slide, model_building_step),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("model-step", "Inicialitzant l'entorn de construcció...")
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
            js=nav_js("conclusion-step", "Generant el resum de rendiment...")
        )

        # Conclusion -> App
        step_3_back.click(
            fn=create_nav(conclusion_step, model_building_step),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("model-step", "Tornant a l'àrea de construcció del model...")
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
                username_state,  # NEW: Session-based auth
                token_state,     # NEW: Session-based auth
                readiness_state, # Renamed to readiness_flag in function signature
                was_preview_state, # Renamed to was_preview_prev in function signature
                # kpi_meta_state removed from inputs - used only as output
            ],
            outputs=all_outputs,
            show_progress="full",
            js=nav_js("model-step", "Executant l'experiment...", 500, notify_parent=False)
            
            ).then(
                # CHANGE 2: Send the notification ONLY after Python is done (20s later)
                fn=None,
                inputs=None,
                outputs=None,
                js="() => { try { window.parent.postMessage('model-updated', '*'); console.log('Submission complete. Notifying parent.'); } catch(e) { console.warn(e); } }"
            )

        # Handle session-based authentication on page load
        def handle_load_with_session_auth(request: "gr.Request"):
            """
            Check for session token, auto-login if present, then load initial UI with stats.
            
            Concurrency Note: This function does NOT set per-user values in os.environ.
            All authentication state is returned via gr.State objects (username_state,
            token_state, team_name_state) to prevent cross-user data leakage.
            """
            success, username, token = _try_session_based_auth(request)
            
            if success and username and token:
                _log(f"Session auth successful on load for {username}")
                
                # Get user stats and team from cache/leaderboard
                stats = _compute_user_stats(username, token)
                team_name = stats.get("team_name", "")
                
                # Concurrency Note: Do NOT set os.environ for per-user values.
                # Return state via gr.State objects exclusively.
                
                # Hide login form since user is authenticated via session
                # Return initial load results plus login form hidden
                # Pass token explicitly for authenticated leaderboard fetch
                initial_results = on_initial_load(username, token=token, team_name=team_name)
                return initial_results + (
                    gr.update(visible=False),  # login_username
                    gr.update(visible=False),  # login_password  
                    gr.update(visible=False),  # login_submit
                    gr.update(visible=False),  # login_error (hide any messages)
                    username,  # username_state
                    token,     # token_state
                    team_name, # team_name_state
                )
            else:
                _log("No valid session on load, showing login form")
                # No valid session, proceed with normal load (show login form)
                # No token available, call without token
                initial_results = on_initial_load(None, token=None, team_name="")
                return initial_results + (
                    gr.update(visible=True),   # login_username
                    gr.update(visible=True),   # login_password
                    gr.update(visible=True),   # login_submit
                    gr.update(visible=False),  # login_error
                    None,  # username_state
                    None,  # token_state
                    "",    # team_name_state
                )
        
        demo.load(
            fn=handle_load_with_session_auth,
            inputs=None,  # Request is auto-injected
            outputs=[
                model_card_display,
                team_leaderboard_display, 
                individual_leaderboard_display, 
                rank_message_display,
                model_type_radio,
                complexity_slider,
                feature_set_checkbox,
                data_size_radio,
                login_username,
                login_password,
                login_submit,
                login_error,
                username_state,  # NEW
                token_state,     # NEW
                team_name_state, # NEW
            ]
        )

    return demo

# -------------------------------------------------------------------------
# 4. Convenience Launcher
# -------------------------------------------------------------------------

def launch_model_building_game_ca_final_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
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

    demo = create_model_building_game_ca_final_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

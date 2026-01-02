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
# CACHE CONFIGURATION (Optimized: Thread-Safe SQLite)
# -------------------------------------------------------------------------
import sqlite3

CACHE_DB_FILE = "prediction_cache.sqlite"

def get_cached_prediction(key):
    """
    Lightning-fast lookup from SQLite database.
    THREAD-SAFE FIX: Opens a new connection for every lookup.
    """
    # 1. Check if DB exists
    if not os.path.exists(CACHE_DB_FILE):
        return None

    try:
        # Use a context manager ('with') to ensure the connection 
        # is ALWAYS closed, releasing file locks immediately.
        # timeout=10 ensures we don't wait forever if the file is busy.
        with sqlite3.connect(CACHE_DB_FILE, timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cache WHERE key=?", (key,))
            result = cursor.fetchone()
            
            if result:
                return result[0] 
            else:
                return None
            
    except sqlite3.OperationalError as e:
        # Handle locking errors gracefully
        print(f"⚠️ CACHE LOCK ERROR: {e}. Falling back to training.", flush=True)
        return None
        
    except Exception as e:
        print(f"⚠️ DB READ ERROR: {e}", flush=True)
        return None

print("✅ App configured for Thread-Safe SQLite Cache.")


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

MODEL_TYPES = {
    "The Balanced Generalist": {
        "model_builder": lambda: LogisticRegression(
            max_iter=500, random_state=42, class_weight="balanced"
        ),
        "card": "A fast, reliable, well-rounded model. Good starting point; less prone to overfitting."
    },
    "The Rule-Maker": {
        "model_builder": lambda: DecisionTreeClassifier(
            random_state=42, class_weight="balanced"
        ),
        "card": "Learns simple 'if/then' rules. Easy to interpret, but can miss subtle patterns."
    },
    "The 'Nearest Neighbor'": {
        "model_builder": lambda: KNeighborsClassifier(),
        "card": "Looks at the closest past examples. 'You look like these others; I'll predict like they behave.'"
    },
    "The Deep Pattern-Finder": {
        "model_builder": lambda: RandomForestClassifier(
            random_state=42, class_weight="balanced"
        ),
        "card": "An ensemble of many decision trees. Powerful, can capture deep patterns; watch complexity."
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
def build_login_prompt_html():
    """
    Generate HTML for the login prompt text *only*.
    The styled preview card will be prepended to this.
    """
    return f"""
    <h2 style='color: #111827; margin-top:20px; border-top: 2px solid #e5e7eb; padding-top: 20px;'>🔐 Sign in to submit & rank</h2>
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
        title = "⏳ Submission Processing"
        acc_color = "#3b82f6"  # Blue
        acc_text = f"{(local_test_accuracy * 100):.2f}%" if local_test_accuracy is not None else "N/A"
        
        # Compute provisional diff between local (new) and last score
        if local_test_accuracy is not None and last_score is not None and last_score > 0:
            score_diff = local_test_accuracy - last_score
            if abs(score_diff) < 0.0001:
                acc_diff_html = "<p style='font-size: 1.5rem; font-weight: 600; color: #6b7280; margin:0;'>No Change (↔) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Pending leaderboard update...</p>"
            elif score_diff > 0:
                acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #16a34a; margin:0;'>+{(score_diff * 100):.2f} (⬆️) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Pending leaderboard update...</p>"
            else:
                acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #ef4444; margin:0;'>{(score_diff * 100):.2f} (⬇️) <span style='font-size: 0.9rem; color: #9ca3af;'>(Provisional)</span></p><p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Pending leaderboard update...</p>"
        else:
            # No last score available - just show pending message
            acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Pending leaderboard update...</p>"
        
        border_color = acc_color
        rank_color = "#6b7280"  # Gray
        rank_text = "Pending"
        rank_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0;'>Calculating rank...</p>"
        
    # Handle preview mode - Styled to match "success" card
    elif is_preview:
        title = "🔬 Successful Preview Run!"
        acc_color = "#16a34a"  # Green (like success)
        acc_text = f"{(new_score * 100):.2f}%" if new_score > 0 else "N/A"
        acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>(Preview only - not submitted)</p>" # Neutral color
        border_color = acc_color # Green border
        rank_color = "#3b82f6" # Blue (like rank)
        rank_text = "N/A" # Placeholder
        rank_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0;'>Not ranked (preview)</p>" # Neutral color
    
    # 1. Handle First Submission
    elif submission_count == 0:
        title = "🎉 First Model Submitted!"
        acc_color = "#16a34a" # green
        acc_text = f"{(new_score * 100):.2f}%"
        acc_diff_html = "<p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>(Your first score!)</p>"

        rank_color = "#3b82f6" # blue
        rank_text = f"#{new_rank}"
        rank_diff_html = "<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>You're on the board!</p>"
        border_color = acc_color

    else:
        # 2. Handle Score Changes
        score_diff = new_score - last_score
        if abs(score_diff) < 0.0001:
            title = "✅ Submission Successful"
            acc_color = "#6b7280" # gray
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>No Change (↔)</p>"
            border_color = acc_color
        elif score_diff > 0:
            title = "✅ Submission Successful!"
            acc_color = "#16a34a" # green
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>+{(score_diff * 100):.2f} (⬆️)</p>"
            border_color = acc_color
        else:
            title = "📉 Score Dropped"
            acc_color = "#ef4444" # red
            acc_text = f"{(new_score * 100):.2f}%"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>{(score_diff * 100):.2f} (⬇️)</p>"
            border_color = acc_color

        # 3. Handle Rank Changes
        rank_diff = last_rank - new_rank
        rank_color = "#3b82f6" # blue
        rank_text = f"#{new_rank}"
        if last_rank == 0: # Handle first rank
             rank_diff_html = "<p style='font-size: 1.5rem; font-weight: 600; color: #3b82f6; margin:0;'>You're on the board!</p>"
        elif rank_diff > 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #16a34a; margin:0;'>🚀 Moved up {rank_diff} spot{'s' if rank_diff > 1 else ''}!</p>"
        elif rank_diff < 0:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: #ef4444; margin:0;'>🔻 Dropped {abs(rank_diff)} spot{'s' if abs(rank_diff) > 1 else ''}</p>"
        else:
            rank_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {rank_color}; margin:0;'>No Change (↔)</p>"

    return f"""
    <div class='kpi-card' style='border-color: {border_color};'>
        <h2 style='color: #eef2ff; margin-top:0;'>{title}</h2>
        <div class='kpi-card-body'>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>New Accuracy</p>
                <p class='kpi-score' style='color: {acc_color};'>{acc_text}</p>
                {acc_diff_html}
            </div>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>Your Rank</p>
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
    """
    if team_summary_df is None or team_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>No team submissions yet.</p>"

    # Normalize the current user's team name for comparison
    normalized_user_team = _normalize_team_name(team_name).lower()

    header = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>Best_Score</th>
                <th>Avg_Score</th>
                <th>Submissions</th>
            </tr>
        </thead>
        <tbody>
    """

    body = ""
    for index, row in team_summary_df.iterrows():
        # Normalize the row's team name and compare case-insensitively
        normalized_row_team = _normalize_team_name(row["Team"]).lower()
        is_user_team = normalized_row_team == normalized_user_team
        row_class = "class='user-row-highlight'" if is_user_team else ""
        body += f"""
        <tr {row_class}>
            <td>{index}</td>
            <td>{row['Team']}</td>
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
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Leaderboard empty.</p>",
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Leaderboard empty.</p>",
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
    return MODEL_TYPES.get(model_name, {}).get("card", "No description available.")

def compute_rank_settings(
    submission_count,
    current_model,
    current_complexity,
    current_feature_set,
    current_data_size
):
    """Returns rank gating settings (updated for 1–10 complexity scale)."""

    def get_choices_for_rank(rank):
        if rank == 0: # Trainee
            return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in FEATURE_SET_GROUP_1_VALS]
        if rank == 1: # Junior
            return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in (FEATURE_SET_GROUP_1_VALS + FEATURE_SET_GROUP_2_VALS)]
        return FEATURE_SET_ALL_OPTIONS # Senior+

    if submission_count == 0:
        return {
            "rank_message": "# 🧑‍🎓 Rank: Trainee Engineer\n<p style='font-size:24px; line-height:1.4;'>For your first submission, just click the big '🔬 Build & Submit Model' button below!</p>",
            "model_choices": ["The Balanced Generalist"],
            "model_value": "The Balanced Generalist",
            "model_interactive": False,
            "complexity_max": 3,
            "complexity_value": min(current_complexity, 3),
            "feature_set_choices": get_choices_for_rank(0),
            "feature_set_value": FEATURE_SET_GROUP_1_VALS,
            "feature_set_interactive": False,
            "data_size_choices": ["Small (20%)"],
            "data_size_value": "Small (20%)",
            "data_size_interactive": False,
        }
    elif submission_count == 1:
        return {
            "rank_message": "# 🎉 Rank Up! Junior Engineer\n<p style='font-size:24px; line-height:1.4;'>New models, data sizes, and data ingredients unlocked!</p>",
            "model_choices": ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"],
            "model_value": current_model if current_model in ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"] else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 6,
            "complexity_value": min(current_complexity, 6),
            "feature_set_choices": get_choices_for_rank(1),
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)"],
            "data_size_value": current_data_size if current_data_size in ["Small (20%)", "Medium (60%)"] else "Small (20%)",
            "data_size_interactive": True,
        }
    elif submission_count == 2:
        return {
            "rank_message": "# 🌟 Rank Up! Senior Engineer\n<p style='font-size:24px; line-height:1.4;'>Strongest Data Ingredients Unlocked! The most powerful predictors (like 'Age' and 'Prior Crimes Count') are now available in your list. These will likely boost your accuracy, but remember they often carry the most societal bias.</p>",
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Deep Pattern-Finder",
            "model_interactive": True,
            "complexity_max": 8,
            "complexity_value": min(current_complexity, 8),
            "feature_set_choices": get_choices_for_rank(2),
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)",
            "data_size_interactive": True,
        }
    else:
        return {
            "rank_message": "# 👑 Rank: Lead Engineer\n<p style='font-size:24px; line-height:1.4;'>All tools unlocked — optimize freely!</p>",
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 10,
            "complexity_value": current_complexity,
            "feature_set_choices": get_choices_for_rank(3),
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
    Core experiment: Uses 'yield' for visual updates and progress bar.
    Updated with "Look-Before-You-Leap" caching strategy.
    """
    # --- COLLISION GUARDS ---
    # Log types of potentially shadowed names to ensure they refer to component objects, not dicts
    _log(f"DEBUG guard: types — submit_button={type(submit_button)} submission_feedback_display={type(submission_feedback_display)} kpi_meta_state={type(kpi_meta_state)} was_preview_state={type(was_preview_state)} readiness_flag_param={type(readiness_flag)}")
    
    # If any of the component names are found as dicts (indicating parameter shadowing), short-circuit
    if isinstance(submit_button, dict) or isinstance(submission_feedback_display, dict) or isinstance(kpi_meta_state, dict) or isinstance(was_preview_state, dict):
        error_html = """
        <div class='kpi-card' style='border-color: #ef4444;'>
            <h2 style='color: #111827; margin-top:0;'>⚠️ Configuration Error</h2>
            <div class='kpi-card-body'>
                <p style='color: #991b1b;'>Parameter shadowing detected. Global component variables were shadowed by local parameters.</p>
                <p style='color: #7f1d1d; margin-top: 8px;'>Please refresh the page and try again. If the issue persists, contact support.</p>
            </div>
        </div>
        """
        yield {
            submission_feedback_display: gr.update(value=error_html, visible=True),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True)
        }
        return
    
    # Sanitize feature_set: convert dicts/tuples to their string values
    sanitized_feature_set = []
    for feat in (feature_set or []):
        if isinstance(feat, dict):
            # Extract 'value' key if present, otherwise use string representation
            sanitized_feature_set.append(feat.get("value", str(feat)))
        elif isinstance(feat, tuple):
            # For tuples like ("Label", "value"), take the second element
            sanitized_feature_set.append(feat[1] if len(feat) > 1 else str(feat))
        else:
            # Already a string
            sanitized_feature_set.append(str(feat))
    feature_set = sanitized_feature_set
    
    # Use readiness_flag parameter if provided, otherwise check readiness
    if readiness_flag is not None:
        ready = readiness_flag
    else:
        ready = _is_ready()
    _log(f"run_experiment: ready={ready}, username={username}, token_present={token is not None}")
    
    # Add debug log (optional)
    _log(f"run_experiment received username={username} token_present={token is not None}")    
    # Concurrency Note: Use provided parameters exclusively, not os.environ.
    # Default to "Unknown_User" only if no username provided via state.
    if not username:
        username = "Unknown_User"
    
    # Helper to generate the animated HTML
    def get_status_html(step_num, title, subtitle):
        return f"""
        <div class='processing-status'>
            <span class='processing-icon'>⚙️</span>
            <div class='processing-text'>Step {step_num}/5: {title}</div>
            <div class='processing-subtext'>{subtitle}</div>
        </div>
        """

    # --- Stage 1: Lock UI and give initial feedback ---
    progress(0.1, desc="Starting Experiment...")
    initial_updates = {
        submit_button: gr.update(value="⏳ Experiment Running...", interactive=False),
        submission_feedback_display: gr.update(value=get_status_html(1, "Initializing", "Preparing your data ingredients..."), visible=True), # Make sure it's visible
        login_error: gr.update(visible=False), # Hide login success/error message
        attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
    }
    yield initial_updates

    if not model_name_key or model_name_key not in MODEL_TYPES:
        model_name_key = DEFAULT_MODEL
    complexity_level = safe_int(complexity_level, 2)

    log_output = f"▶ New Experiment\nModel: {model_name_key}\n..."

    # Check readiness
    # If playground is None or not ready, fallback error
    if playground is None or not ready:
        settings = compute_rank_settings(
             submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )
        
        error_msg = "<p style='text-align:center; color:red; padding:20px 0;'>"
        if playground is None:
            error_msg += "Playground not connected. Please try again later."
        else:
            error_msg += "Data still initializing. Please wait a moment and try again."
        error_msg += "</p>"
        
        error_kpi_meta = {
            "was_preview": False, "preview_score": None, "ready_at_run_start": False,
            "poll_iterations": 0, "local_test_accuracy": None, "this_submission_score": None,
            "new_best_accuracy": None, "rank": None
        }
        
        error_updates = {
            submission_feedback_display: gr.update(value=error_msg, visible=True),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True),
            individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False),
            last_submission_score_state: last_submission_score,
            last_rank_state: last_rank,
            best_score_state: best_score,
            submission_count_state: submission_count,
            first_submission_score_state: first_submission_score,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            login_username: gr.update(visible=False),
            login_password: gr.update(visible=False),
            login_submit: gr.update(visible=False),
            login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)),
            was_preview_state: False,
            kpi_meta_state: error_kpi_meta,
            last_seen_ts_state: None
        }
        yield error_updates
        return

    try:
        # --- Stage 2: Smart Build (Cache vs Train) ---
        progress(0.3, desc="Building Model...")
        
        # 1. Generate Cache Key (Matches format in precompute_cache.py)
        # Key: "ModelName|Complexity|DataSize|SortedFeatures"
        sanitized_features = sorted([str(f) for f in feature_set])
        feature_key = ",".join(sanitized_features)
        cache_key = f"{model_name_key}|{complexity_level}|{data_size_str}|{feature_key}"
        
        # 2. Check Cache
        cached_predictions = get_cached_prediction(cache_key)
        
        # Initialize submission variables
        predictions = None
        tuned_model = None
        preprocessor = None
        
        if cached_predictions:
            # === FAST PATH (Zero CPU) ===
            _log(f"⚡ CACHE HIT: {cache_key}")
            yield { 
                submission_feedback_display: gr.update(value=get_status_html(2, "Training Model", "⚡ The machine is learning from history..."), visible=True),
                login_error: gr.update(visible=False)
            }

            # --- DECOMPRESSION STEP (Vital) ---
            # If string "01010...", convert to [0, 1, 0, 1...]
            if isinstance(cached_predictions, str):
                predictions = [int(c) for c in cached_predictions]
            else:
                predictions = cached_predictions

            # Pass None to submit_model to skip training overhead validation
            tuned_model = None
            preprocessor = None
            
            
        else:
            # === CACHE MISS (Training Disabled) ===
            # This ensures we NEVER run heavy training code in production.
            msg = f"❌ CACHE MISS: {cache_key}"
            _log(msg)
            
            # User-friendly error message
            error_html = f"""
            <div style='background:#fee2e2; padding:16px; border-radius:8px; border:2px solid #ef4444; color:#991b1b; text-align:center;'>
                <h3 style='margin:0;'>⚠️ Configuration Not Found</h3>
                <p style='margin:8px 0;'>This specific combination of settings was not found in our pre-computed database.</p>
                <p style='font-size:0.9em;'>To ensure system stability, real-time training is disabled. Please adjust your settings (e.g., change the Data Size or Model Strategy) and try again.</p>
            </div>
            """
            
            yield { 
                submission_feedback_display: gr.update(value=error_html, visible=True),
                submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
                login_error: gr.update(visible=False)
            }
            return # <--- CRITICAL: Stop execution here.

        # --- Stage 3: Submit (API Call 1) ---
        # AUTHENTICATION GATE: Check for token before submission
        if token is None:
            # User not authenticated - compute preview score and show login prompt
            progress(0.6, desc="Computing Preview Score...")
            
            # We need to calculate accuracy for the preview card
            from sklearn.metrics import accuracy_score
            # Ensure predictions are in correct format (list or array)
            if isinstance(predictions, list):
                # Cached predictions are lists
                preds_array = np.array(predictions)
            else:
                preds_array = predictions
                
            preview_score = accuracy_score(Y_TEST, preds_array)
            
            preview_kpi_meta = {
                "was_preview": True, "preview_score": preview_score, "ready_at_run_start": ready,
                "poll_iterations": 0, "local_test_accuracy": preview_score,
                "this_submission_score": None, "new_best_accuracy": None, "rank": None
            }
            
            # 1. Generate the styled preview card
            preview_card_html = _build_kpi_card_html(
                new_score=preview_score, last_score=0, new_rank=0, last_rank=0,
                submission_count=-1, is_preview=True, is_pending=False, local_test_accuracy=None
            )
            
            # 2. Inject login text
            login_prompt_text_html = build_login_prompt_html() 
            closing_div_index = preview_card_html.rfind("</div>")
            if closing_div_index != -1:
                combined_html = preview_card_html[:closing_div_index] + login_prompt_text_html + "</div>"
            else:
                combined_html = preview_card_html + login_prompt_text_html 
                
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            
            gate_updates = {
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
                was_preview_state: True, kpi_meta_state: preview_kpi_meta, last_seen_ts_state: None
            }
            yield gate_updates
            return  # Stop here
        
        # --- ATTEMPT LIMIT CHECK ---
        if submission_count >= ATTEMPT_LIMIT:
            limit_warning_html = f"""
            <div class='kpi-card' style='border-color: #ef4444;'>
                <h2 style='color: #111827; margin-top:0;'>🛑 Submission Limit Reached</h2>
                <div class='kpi-card-body'>
                    <div class='kpi-metric-box'>
                        <p class='kpi-label'>Attempts Used</p>
                        <p class='kpi-score' style='color: #ef4444;'>{ATTEMPT_LIMIT} / {ATTEMPT_LIMIT}</p>
                    </div>
                </div>
                <div style='margin-top: 16px; background:#fef2f2; padding:16px; border-radius:12px; text-align:left; font-size:0.98rem; line-height:1.4;'>
                    <p style='margin:0; color:#991b1b;'><b>Nice Work!</b> Scroll down to "Finish and Reflect".</p>
                </div>
            </div>"""
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            limit_reached_updates = {
                submission_feedback_display: gr.update(value=limit_warning_html, visible=True),
                submit_button: gr.update(value="🛑 Submission Limit Reached", interactive=False),
                model_type_radio: gr.update(interactive=False), complexity_slider: gr.update(interactive=False),
                feature_set_checkbox: gr.update(interactive=False), data_size_radio: gr.update(interactive=False),
                attempts_tracker_display: gr.update(value=f"<div style='text-align:center; padding:8px; margin:8px 0; background:#fef2f2; border-radius:8px; border:1px solid #ef4444;'><p style='margin:0; color:#991b1b; font-weight:600;'>🛑 Attempts used: {ATTEMPT_LIMIT}/{ATTEMPT_LIMIT}</p></div>"),
                team_leaderboard_display: team_leaderboard_display, individual_leaderboard_display: individual_leaderboard_display,
                last_submission_score_state: last_submission_score, last_rank_state: last_rank,
                best_score_state: best_score, submission_count_state: submission_count,
                first_submission_score_state: first_submission_score, rank_message_display: settings["rank_message"],
                login_username: gr.update(visible=False), login_password: gr.update(visible=False),
                login_submit: gr.update(visible=False), login_error: gr.update(visible=False),
                was_preview_state: False, kpi_meta_state: {}, last_seen_ts_state: None
            }
            yield limit_reached_updates
            return
        
        progress(0.5, desc="Submitting to Cloud...")
        yield { 
            submission_feedback_display: gr.update(value=get_status_html(3, "Submitting", "Sending model to the competition server..."), visible=True),
            login_error: gr.update(visible=False)
        }

        description = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})"
        tags = f"team:{team_name},model:{model_name_key}"

        # 1. FETCH BASELINE SNAPSHOT (non-cached) before submission
        baseline_leaderboard_df = _get_leaderboard_with_optional_token(playground, token)
        
        # Capture baseline user stats for comparison after submission
        baseline_row_count = 0
        baseline_best_score = 0.0
        baseline_latest_ts = None
        baseline_latest_score = None
        
        if baseline_leaderboard_df is not None and not baseline_leaderboard_df.empty:
            user_rows = baseline_leaderboard_df[baseline_leaderboard_df["username"] == username]
            if not user_rows.empty:
                baseline_row_count = len(user_rows)
                if "accuracy" in user_rows.columns:
                    baseline_best_score = float(user_rows["accuracy"].max())
                baseline_latest_ts = _get_user_latest_ts(baseline_leaderboard_df, username)
                baseline_latest_score = _get_user_latest_accuracy(baseline_leaderboard_df, username)
        
        _log(f"Baseline snapshot: row_count={baseline_row_count}, best_score={baseline_best_score:.4f}, latest_ts={baseline_latest_ts}, latest_score={baseline_latest_score}")
        
        from sklearn.metrics import accuracy_score
        # Ensure correct type for local accuracy calc
        if isinstance(predictions, list):
            local_accuracy_preds = np.array(predictions)
        else:
            local_accuracy_preds = predictions
        local_test_accuracy = accuracy_score(Y_TEST, local_accuracy_preds)

        # 2. SUBMIT & CAPTURE ACCURACY with submission_ok flag
        submission_ok = False
        this_submission_score = local_test_accuracy  # Initialize with local score
        submission_error = ""  # Initialize with empty string
        
        def _submit():
            # If using cache (tuned_model is None), we pass None for model/preprocessor
            # and explicitly pass predictions.
            return playground.submit_model(
                model=tuned_model, 
                preprocessor=preprocessor, 
                prediction_submission=predictions,
                input_dict={'description': description, 'tags': tags},
                custom_metadata={'Team': team_name, 'Moral_Compass': 0}, 
                token=token,
                return_metrics=["accuracy"] 
            )
        
        try:
            submit_result = _retry_with_backoff(_submit, description="model submission")
            # Parse submission result to get server-side accuracy
            if isinstance(submit_result, tuple) and len(submit_result) == 3:
                _, _, metrics = submit_result
                if metrics and "accuracy" in metrics and metrics["accuracy"] is not None:
                    this_submission_score = float(metrics["accuracy"])
                # else: keep local_test_accuracy as fallback (already initialized above)
            # else: keep local_test_accuracy as fallback (already initialized above)
            
            # If we reach here without exception, submission succeeded
            submission_ok = True
            _log(f"Submission successful. Server Score: {this_submission_score}")
        except Exception as e:
            submission_ok = False
            submission_error = str(e)
            # this_submission_score keeps its local_test_accuracy value (for error display if needed)
            _log(f"Submission FAILED: {e}")
        
        # 3. HANDLE SUBMISSION FAILURE - show error card and do NOT increment attempts
        if not submission_ok:
            error_html = f"""
            <div class='kpi-card' style='border-color: #ef4444;'>
                <h2 style='color: #111827; margin-top:0;'>❌ Submission Failed</h2>
                <div class='kpi-card-body'>
                    <p style='color: #991b1b; margin: 16px 0;'>
                        Your model could not be submitted to the leaderboard. This attempt was NOT counted.
                    </p>
                    <div style='background:#fef2f2; padding:16px; border-radius:12px; text-align:left; font-size:0.98rem; line-height:1.4;'>
                        <p style='margin:0; color:#7f1d1d;'><b>Possible causes:</b></p>
                        <ul style='margin:8px 0 0 20px; color:#7f1d1d;'>
                            <li>Invalid or expired authentication token</li>
                            <li>Network connectivity issues</li>
                            <li>Backend service unavailable</li>
                        </ul>
                        <details style='margin-top:12px; font-size:0.85rem; color:#7f1d1d;'>
                            <summary style='cursor:pointer;'>Technical details</summary>
                            <pre style='margin-top:8px; padding:8px; background:#fee; border-radius:4px; overflow-x:auto;'>{submission_error}</pre>
                        </details>
                    </div>
                    <p style='color: #991b1b; margin: 16px 0 0 0;'>
                        Please try again. If the problem persists, contact support.
                    </p>
                </div>
            </div>
            """
            settings = compute_rank_settings(submission_count, model_name_key, complexity_level, feature_set, data_size_str)
            
            failure_updates = {
                submission_feedback_display: gr.update(value=error_html, visible=True),
                submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
                team_leaderboard_display: team_leaderboard_display if 'team_leaderboard_display' in locals() else gr.update(),
                individual_leaderboard_display: individual_leaderboard_display if 'individual_leaderboard_display' in locals() else gr.update(),
                last_submission_score_state: last_submission_score,
                last_rank_state: last_rank,
                best_score_state: best_score,
                submission_count_state: submission_count,  # Do NOT increment on failure
                first_submission_score_state: first_submission_score,
                rank_message_display: settings["rank_message"],
                model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
                complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
                feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
                data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
                login_username: gr.update(visible=False),
                login_password: gr.update(visible=False),
                login_submit: gr.update(visible=False),
                login_error: gr.update(visible=False),
                attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)),
                was_preview_state: False,
                kpi_meta_state: {"error": submission_error, "was_preview": False},
                last_seen_ts_state: None
            }
            yield failure_updates
            return

        # --- Stage 4: Poll for leaderboard update (submission succeeded) ---
        progress(0.7, desc="Verifying submission...")
        
        # Show pending KPI card while polling
        pending_kpi_html = _build_kpi_card_html(
            new_score=0, last_score=last_submission_score, new_rank=0, last_rank=last_rank,
            submission_count=submission_count, is_preview=False, is_pending=True,
            local_test_accuracy=local_test_accuracy
        )
        yield {
            submission_feedback_display: gr.update(value=pending_kpi_html, visible=True),
            login_error: gr.update(visible=False)
        }
        
        # Poll leaderboard until user's rows change or timeout
        poll_detected_change = False
        poll_iterations = 0
        updated_leaderboard_df = None  # Will hold the fresh leaderboard if polling succeeds
        
        for attempt in range(LEADERBOARD_POLL_TRIES):
            poll_iterations = attempt + 1
            _log(f"Polling attempt {poll_iterations}/{LEADERBOARD_POLL_TRIES}")
            
            # Fetch fresh leaderboard (bypass cache)
            refreshed_leaderboard = _get_leaderboard_with_optional_token(playground, token)
            
            # Check if user's rows changed
            if _user_rows_changed(
                refreshed_leaderboard, username, baseline_row_count, baseline_best_score,
                baseline_latest_ts, baseline_latest_score
            ):
                _log(f"User rows changed detected after {poll_iterations} polls")
                poll_detected_change = True
                updated_leaderboard_df = refreshed_leaderboard  # Store updated leaderboard
                break
            
            time.sleep(LEADERBOARD_POLL_SLEEP)
        
        if not poll_detected_change:
            _log(f"Polling timed out after {poll_iterations} attempts. Using optimistic fallback.")
        
        # --- Stage 5: Calculate final state (optimistic if polling timed out) ---
        progress(0.9, desc="Calculating Rank...")
        
        # Increment submission count ONLY after verified success (or timeout with optimistic fallback)
        new_submission_count = submission_count + 1
        new_first_submission_score = first_submission_score
        if submission_count == 0 and first_submission_score is None:
            new_first_submission_score = this_submission_score
        
        # Use polled leaderboard if available, else simulate with baseline
        if poll_detected_change and updated_leaderboard_df is not None:
            # Real data from polling - use the updated leaderboard
            final_leaderboard_df = updated_leaderboard_df
        else:
            # Optimistic fallback: simulate the new row using baseline snapshot
            # Note: We use pd.Timestamp.now() as an approximation. This may not match
            # the exact backend timestamp, but it's acceptable for the fallback case
            # since the real leaderboard will eventually be consistent.
            simulated_df = baseline_leaderboard_df.copy() if baseline_leaderboard_df is not None else pd.DataFrame()
            new_row = pd.DataFrame([{
                "username": username,
                "accuracy": this_submission_score,
                "Team": team_name,
                "timestamp": pd.Timestamp.now(), 
                "version": "latest"
            }])
            if not simulated_df.empty:
                simulated_df = pd.concat([simulated_df, new_row], ignore_index=True)
            else:
                simulated_df = new_row
            final_leaderboard_df = simulated_df

        # Generate tables and KPI card from final leaderboard
        team_html, individual_html, _, new_best_accuracy, new_rank, _ = generate_competitive_summary(
            final_leaderboard_df, team_name, username, last_submission_score, last_rank, submission_count
        )

        # Build final KPI card (success, not pending)
        kpi_card_html = _build_kpi_card_html(
            new_score=this_submission_score,
            last_score=last_submission_score,
            new_rank=new_rank,
            last_rank=last_rank,
            submission_count=submission_count, 
            is_preview=False,
            is_pending=False
        )

        # --- Stage 6: Final UI Update ---
        progress(1.0, desc="Complete!")
        
        success_kpi_meta = {
            "was_preview": False, "preview_score": None, "ready_at_run_start": ready,
            "poll_iterations": poll_iterations, "local_test_accuracy": local_test_accuracy,
            "this_submission_score": this_submission_score, "new_best_accuracy": new_best_accuracy,
            "rank": new_rank, "pending": False, "poll_detected_change": poll_detected_change,
            "optimistic_fallback": not poll_detected_change
        }
        
        settings = compute_rank_settings(new_submission_count, model_name_key, complexity_level, feature_set, data_size_str)

        # -------------------------------------------------------------------------
        # NEW LOGIC: Check for Limit Reached immediately AFTER this submission
        # -------------------------------------------------------------------------
        limit_reached = new_submission_count >= ATTEMPT_LIMIT
        
        # Prepare the UI state based on whether limit is reached
        if limit_reached:
            # 1. Append the Limit Warning HTML *below* the Result Card
            limit_html = f"""
            <div style='margin-top: 16px; border: 2px solid #ef4444; background:#fef2f2; padding:16px; border-radius:12px; text-align:left;'>
                <h3 style='margin:0 0 8px 0; color:#991b1b;'>🛑 Submission Limit Reached ({ATTEMPT_LIMIT}/{ATTEMPT_LIMIT})</h3>
                <p style='margin:0; color:#7f1d1d; line-height:1.4;'>
                    <b>You have used all your attempts for this session.</b><br>
                    Review your final results above, then scroll down to "Finish and Reflect" to continue.
                </p>
            </div>
            """
            final_html_display = kpi_card_html + limit_html
            
            # 2. Disable all controls
            button_update = gr.update(value="🛑 Limit Reached", interactive=False)
            interactive_state = False
            tracker_html = f"<div style='text-align:center; padding:8px; margin:8px 0; background:#fef2f2; border-radius:8px; border:1px solid #ef4444;'><p style='margin:0; color:#991b1b; font-weight:600;'>🛑 Attempts used: {ATTEMPT_LIMIT}/{ATTEMPT_LIMIT} (Max)</p></div>"
        
        else:
            # Normal State: Show just the result card and keep controls active
            final_html_display = kpi_card_html
            button_update = gr.update(value="🔬 Build & Submit Model", interactive=True)
            interactive_state = True
            tracker_html = _build_attempts_tracker_html(new_submission_count)

        # -------------------------------------------------------------------------

        final_updates = {
            submission_feedback_display: gr.update(value=final_html_display, visible=True),
            team_leaderboard_display: team_html,
            individual_leaderboard_display: individual_html,
            last_submission_score_state: this_submission_score, 
            last_rank_state: new_rank, 
            best_score_state: new_best_accuracy,
            submission_count_state: new_submission_count,
            first_submission_score_state: new_first_submission_score,
            rank_message_display: settings["rank_message"],
            
            # Apply the interactive state calculated above
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=(settings["model_interactive"] and interactive_state)),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"], interactive=interactive_state),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=(settings["feature_set_interactive"] and interactive_state)),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=(settings["data_size_interactive"] and interactive_state)),
            
            submit_button: button_update,
            
            login_username: gr.update(visible=False), login_password: gr.update(visible=False),
            login_submit: gr.update(visible=False), login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=tracker_html),
            was_preview_state: False,
            kpi_meta_state: success_kpi_meta,
            last_seen_ts_state: time.time()
        }
        yield final_updates
      
    except Exception as e:
        error_msg = f"ERROR: {e}"
        _log(f"Exception in run_experiment: {error_msg}")
        settings = compute_rank_settings(
             submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )
        
        exception_kpi_meta = {
            "was_preview": False, "preview_score": None, "ready_at_run_start": ready if 'ready' in locals() else False,
            "poll_iterations": 0, "local_test_accuracy": None, "this_submission_score": None,
            "new_best_accuracy": None, "rank": None, "error": str(e)
        }
        
        error_updates = {
            submission_feedback_display: gr.update(
                f"<p style='text-align:center; color:red; padding:20px 0;'>An error occurred: {error_msg}</p>", visible=True
            ),
            team_leaderboard_display: f"<p style='text-align:center; color:red; padding-top:20px;'>An error occurred: {error_msg}</p>",
            individual_leaderboard_display: f"<p style='text-align:center; color:red; padding-top:20px;'>An error occurred: {error_msg}</p>",
            last_submission_score_state: last_submission_score,
            last_rank_state: last_rank,
            best_score_state: best_score,
            submission_count_state: submission_count,
            first_submission_score_state: first_submission_score,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            login_username: gr.update(visible=False),
            login_password: gr.update(visible=False),
            login_submit: gr.update(visible=False),
            login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count)),
            was_preview_state: False,
            kpi_meta_state: exception_kpi_meta,
            last_seen_ts_state: None
        }
        yield error_updates

def on_initial_load(username, token=None, team_name=""):
    """
    Updated to show "Welcome & CTA" if the SPECIFIC USER has 0 submissions,
    even if the leaderboard/team already has data from others.
    """
    initial_ui = compute_rank_settings(
        0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE
    )

    # 1. Prepare the Welcome HTML
    display_team = team_name if team_name else "Your Team"
    
    welcome_html = f"""
    <div style='text-align:center; padding: 30px 20px;'>
        <div style='font-size: 3rem; margin-bottom: 10px;'>👋</div>
        <h3 style='margin: 0 0 8px 0; color: #111827; font-size: 1.5rem;'>Welcome to <b>{display_team}</b>!</h3>
        <p style='font-size: 1.1rem; color: #4b5563; margin: 0 0 20px 0;'>
            Your team is waiting for your help to improve the AI.
        </p>
        
        <div style='background:#eff6ff; padding:16px; border-radius:12px; border:2px solid #bfdbfe; display:inline-block;'>
            <p style='margin:0; color:#1e40af; font-weight:bold; font-size:1.1rem;'>
                👈 Click "Build & Submit Model" to Start Playing!
            </p>
        </div>
    </div>
    """

    # Check background init
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
        individual_html = "<p style='text-align:center; color:#6b7280; padding-top:40px;'>Submit your model to see where you rank!</p>"
        
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
            team_html = "<p style='text-align:center; color:red; padding-top:20px;'>Error rendering leaderboard.</p>"
            individual_html = "<p style='text-align:center; color:red; padding-top:20px;'>Error rendering leaderboard.</p>"

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
    Build the final conclusion HTML with performance summary.
    Colors are handled via CSS classes so that light/dark mode work correctly.
    """
    unlocked_tiers = min(3, max(0, submissions - 1))  # 0..3
    tier_names = ["Trainee", "Junior", "Senior", "Lead"]
    reached = tier_names[: unlocked_tiers + 1]
    tier_line = " → ".join([f"{t}{' ✅' if t in reached else ''}" for t in tier_names])

    improvement = (best_score - first_score) if (first_score is not None and submissions > 1) else 0.0
    strong_predictors = {"age", "length_of_stay", "priors_count", "age_cat"}
    strong_used = [f for f in feature_set if f in strong_predictors]

    ethical_note = (
        "You unlocked powerful predictors. Consider: Would removing demographic fields change fairness? "
        "In the next section we will begin to investigate this question further."
    )

    # Tailor message for very few submissions
    tip_html = ""
    if submissions < 2:
        tip_html = """
        <div class="final-conclusion-tip">
          <b>Tip:</b> Try at least 2–3 submissions changing ONE setting at a time to see clear cause/effect.
        </div>
        """

    # Add note if user reached the attempt cap
    attempt_cap_html = ""
    if submissions >= ATTEMPT_LIMIT:
        attempt_cap_html = f"""
        <div class="final-conclusion-attempt-cap">
          <p style="margin:0;">
            <b>📊 Attempt Limit Reached:</b> You used all {ATTEMPT_LIMIT} allowed submission attempts for this session.
            We will open up submissions again after you complete some new activities next.
          </p>
        </div>
        """

    return f"""
    <div class="final-conclusion-root">
      <h1 class="final-conclusion-title">🎉 Engineering Phase Complete</h1>
      <div class="final-conclusion-card">
        <h2 class="final-conclusion-subtitle">Your Performance Snapshot</h2>
        <ul class="final-conclusion-list">
          <li>🏁 <b>Best Accuracy:</b> {(best_score * 100):.2f}%</li>
          <li>📊 <b>Rank Achieved:</b> {('#' + str(rank)) if rank > 0 else '—'}</li>
          <li>🔁 <b>Submissions Made This Session:</b> {submissions}{' / ' + str(ATTEMPT_LIMIT) if submissions >= ATTEMPT_LIMIT else ''}</li>
          <li>🧗 <b>Improvement Over First Score This Session:</b> {(improvement * 100):+.2f}</li>
          <li>🎖️ <b>Tier Progress:</b> {tier_line}</li>
          <li>🧪 <b>Strong Predictors Used:</b> {len(strong_used)} ({', '.join(strong_used) if strong_used else 'None yet'})</li>
        </ul>

        {tip_html}

        <div class="final-conclusion-ethics">
          <p style="margin:0;"><b>Ethical Reflection:</b> {ethical_note}</p>
        </div>

        {attempt_cap_html}

        <hr class="final-conclusion-divider" />

        <div class="final-conclusion-next">
          <h2>➡️ Next: Real-World Consequences</h2>
          <p>Scroll below this app to continue. You'll examine how models like yours shape judicial outcomes.</p>
          <h1 class="final-conclusion-scroll">👇 SCROLL DOWN 👇</h1>
        </div>
      </div>
    </div>
    """



def build_conclusion_from_state(best_score, submissions, rank, first_score, feature_set):
    return build_final_conclusion_html(best_score, submissions, rank, first_score, feature_set)
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
                    <h2 style='font-size:2rem; color:#6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )

        # --- Briefing Slideshow (Updated with New Cards) ---

        # Slide 1: Intro
        with gr.Column(visible=True, elem_id="slide-1") as briefing_slide_1:
            gr.Markdown("<h1 style='text-align:center;'>🔄 From Understanding to Building</h1>")
            gr.HTML("""
                <div class='slide-content'>
                <div class='panel-box'>
                <h3 style='font-size: 1.5rem; text-align:center; margin-top:0;'>Great progress! You've now:</h3>
                <ul style='list-style: none; padding-left: 0; margin-top: 24px; margin-bottom: 24px;'>
                    <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'>✅ Made tough decisions as a judge</li>
                    <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'>✅ Learned about false positives and negatives</li>
                    <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'>✅ Understood how AI works</li>
                </ul>
                <div style='background:white; padding:16px; border-radius:12px; margin:12px 0; text-align:center;'>
                    <span style='background:#dbeafe; padding:8px; border-radius:4px; color:#0369a1; font-weight:bold;'>INPUT</span> → 
                    <span style='background:#fef3c7; padding:8px; border-radius:4px; color:#92400e; font-weight:bold;'>MODEL</span> → 
                    <span style='background:#f0fdf4; padding:8px; border-radius:4px; color:#15803d; font-weight:bold;'>OUTPUT</span>
                </div>
                <h3 style='font-size: 1.5rem; text-align:center;'>Now: Step into the shoes of an AI Engineer.</h3>
                </div>
                </div>
            """)
            briefing_1_next = gr.Button("Next ▶️", variant="primary", size="lg")

        # Slide 2: Mission
# Slide 2: Mission
        with gr.Column(visible=False, elem_id="slide-2") as briefing_slide_2:
            gr.Markdown("<h1 style='text-align:center;'>📋 Your Mission – Build Better AI</h1>")
            gr.HTML("""
                <div class='slide-content'>
                    <div class='panel-box'>
                        <h3>The Mission</h3>
                        <p>Build an AI model that helps judges make better decisions. Your job is to predict re-offending risk more accurately than the previous model.</p>
                        
                        <h3>The Competition</h3>
                        <p>To do this, you’ll compete with other engineers! You’ll join a team, with scores tracked for both individual and team performance on live leaderboards.</p>
                        <div style="background:var(--background-fill-secondary); padding:8px 12px; border-radius:8px; margin-bottom:12px; border:1px solid var(--border-color-primary);">
                             You’ll join a team such as… <b>🛡️ The Ethical Explorers</b>
                        </div>

                        <h3>The Data Challenge</h3>
                        <p>To compete, you’ll have access to thousands of old case files containing <b>Defendant Profiles</b> (Age, History) and <b>Historical Outcomes</b> (Did they re-offend?).</p>
                        <p>Your task is to train an AI system that learns from the profiles and accurately predicts the outcome. Ready to build something that could change how justice works?</p>
                    </div>
                </div>
            """)
            with gr.Row():
                briefing_2_back = gr.Button("◀️ Back", size="lg")
                briefing_2_next = gr.Button("Next ▶️", variant="primary", size="lg")

        # Slide 3: Concept
        with gr.Column(visible=False, elem_id="slide-3") as briefing_slide_3:
            gr.Markdown("<h1 style='text-align:center;'>🧠 What is an AI System?</h1>")
            gr.HTML("""
                <div class='slide-content'>
                    <div class='panel-box'>
                        <p>Think of an AI System as a "Prediction Machine." You assemble it using three main components:</p>
                        <p><strong>1. The Inputs:</strong> The data you feed it (eg: Age, Crimes).</p>
                        <p><strong>2. The Model ("The Brain"):</strong> The math (algorithm) that finds patterns.</p>
                        <p><strong>3. The Output:</strong> The prediction (eg: Risk Level)</p>
                    </div>
                </div>
            """)
            with gr.Row():
                briefing_3_back = gr.Button("◀️ Back", size="lg")
                briefing_3_next = gr.Button("Next ▶️", variant="primary", size="lg")

        # Slide 4: The Loop
        with gr.Column(visible=False, elem_id="slide-4") as briefing_slide_4:
            gr.Markdown("<h1 style='text-align:center;'>🔁 How Engineers Work — The Loop</h1>")
            gr.HTML("""
                <div class='slide-content'>
                    <div class='panel-box'>
                        <p>Real AI teams never get it right on the first try. They follow a loop: <strong>Try, Test, Learn, Repeat.</strong></p>
                        <p>You’ll do exactly the same in this competition:</p>
                        <div class='step-visual'>
                            <div class='step-visual-box'><b>1. Configure</b><br><span style='font-size:0.85rem'>choose model & data</span></div>→
                            <div class='step-visual-box'><b>2. Submit</b><br><span style='font-size:0.85rem'>train your system</span></div>→
                            <div class='step-visual-box'><b>3. Analyze</b><br><span style='font-size:0.85rem'>check ranking</span></div>→
                            <div class='step-visual-box'><b>4. Refine</b><br><span style='font-size:0.85rem'>tweak & try again</span></div>
                        </div>
                    </div>
                </div>
            """)
            
            with gr.Row():
                briefing_4_back = gr.Button("◀️ Back", size="lg")
                briefing_4_next = gr.Button("Next ▶️", variant="primary", size="lg")

        # Slide 5: Systems Check (Controls)
        with gr.Column(visible=False, elem_id="slide-5") as briefing_slide_5:
            gr.HTML(
                """
                <div class='slide-content'>
                    <div class='panel-box'>
                        <div class='t-minus-header'>
                            <h2 class='t-minus-title' style='color: var(--body-text-color);'>🔧 Engineering Systems Check</h2>
                        </div>
            
                        <div style='background: color-mix(in srgb, var(--color-accent) 10%, transparent); border:1px solid var(--color-accent); padding:16px; border-radius:10px; text-align:center; margin-bottom:24px;'>
                            <strong style='color: var(--color-accent); font-size:1.1rem;'>⚠️ SIMULATION MODE ACTIVE</strong>
                            <p style='margin:8px 0 0 0; color: var(--body-text-color); font-size:1.05rem; line-height:1.4;'>
                                Below are the <b>exact 4 controls</b> you will use to build your model in the next step.<br>
                                <b>Click each one now</b> to learn what they do before the competition starts.
                            </p>
                        </div>
            
                        <details class="styled-details" style="border: 1px solid var(--border-color-primary); padding: 8px; border-radius: 8px; margin-bottom: 8px;">
                            <summary style="cursor: pointer; font-weight: 600; color: var(--body-text-color);">1. Model Strategy (The ‘brain’)</summary>
                            <div class="content" style="padding-top: 12px; padding-left: 12px;">
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);"><span class="radio-circle selected" style="display:inline-block; width:12px; height:12px; border-radius:50%; background:var(--color-accent); margin-right:8px;"></span> <b>The Balanced Generalist</b></div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color-subdued);"><span class="radio-circle" style="display:inline-block; width:12px; height:12px; border-radius:50%; border:1px solid var(--body-text-color-subdued); margin-right:8px;"></span> The Rule-Maker</div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color-subdued);"><span class="radio-circle" style="display:inline-block; width:12px; height:12px; border-radius:50%; border:1px solid var(--body-text-color-subdued); margin-right:8px;"></span> The Deep Pattern-Finder</div>
                                
                                <div class="info-popup" style="background: var(--background-fill-secondary); padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color-primary);">
                                    <b style="color: var(--body-text-color);">In the Game:</b> <span style="color: var(--body-text-color);">You will choose one of these model strategies. Each strategy enables your model to learn from input data in a unique way.</span><br>
                                    <i style="color: var(--body-text-color-subdued);">Tip: Start with "Balanced Generalist" for a safe, reliable baseline score.</i>
                                </div>
                            </div>
                        </details>
            
                        <details class="styled-details" style="border: 1px solid var(--border-color-primary); padding: 8px; border-radius: 8px; margin-bottom: 8px;">
                            <summary style="cursor: pointer; font-weight: 600; color: var(--body-text-color);">2. Model Complexity (Focus Level)</summary>
                            <div class="content" style="padding-top: 12px; padding-left: 12px;">
                                <div class="slider-track" style="height: 4px; background: var(--neutral-200); margin: 16px 0; position: relative;"><div class="slider-thumb" style="width: 16px; height: 16px; background: var(--color-accent); border-radius: 50%; position: absolute; left: 50%; top: -6px;"></div></div>
                                <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--body-text-color-subdued);">
                                    <span>Level 1 (General)</span>
                                    <span>Level 10 (Specific)</span>
                                </div>
                                
                                <div class="info-popup" style="background: var(--background-fill-secondary); padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color-primary);">
                                    <b style="color: var(--body-text-color);">In the Game:</b> <span style="color: var(--body-text-color);">Think of this like <b>Studying vs. Memorizing</b>.</span><br>
                                    <span style="color: var(--body-text-color);">• <b>Low Complexity:</b> The AI learns general concepts (Good for new cases).</span><br>
                                    <span style="color: var(--body-text-color);">• <b>High Complexity:</b> The AI memorizes the answer key (Bad for new cases).</span><br>
                                    <strong style="color:#ef4444;">⚠️ The Trap:</strong> <span style="color: var(--body-text-color);">A high setting looks perfect on the practice test, but fails in the real world because the AI just memorized the answers!</span>
                                </div>
                            </div>
                        </details>
            
                        <details class="styled-details" style="border: 1px solid var(--border-color-primary); padding: 8px; border-radius: 8px; margin-bottom: 8px;">
                            <summary style="cursor: pointer; font-weight: 600; color: var(--body-text-color);">3. Data Ingredients (The inputs)</summary>
                            <div class="content" style="padding-top: 12px; padding-left: 12px;">
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);">
                                    <span style="color:var(--color-accent); font-weight:bold;">☑</span> <b>Prior Crimes</b>
                                </div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);">
                                    <span style="color:var(--color-accent); font-weight:bold;">☑</span> <b>Charge Degree</b>
                                </div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);">
                                    <span style="color:var(--neutral-400); font-weight:bold;">☐</span> <b>Demographics (Race/Sex)</b> <span class="risk-tag" style="background:#fef2f2; color:#b91c1c; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold;">⚠️ RISK</span>
                                </div>
                                
                                <div class="info-popup" style="background: var(--background-fill-secondary); padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color-primary);">
                                    <b style="color: var(--body-text-color);">In the Game:</b> <span style="color: var(--body-text-color);">You will check boxes to decide what raw input data the AI is allowed to use to learn new patterns.</span><br>
                                    <strong style="color:#ef4444;">⚠️ Ethical Risk:</strong> <span style="color: var(--body-text-color);">You <i>can</i> use demographics to boost your score, but is it fair?</span>
                                </div>
                            </div>
                        </details>
            
                        <details class="styled-details" style="border: 1px solid var(--border-color-primary); padding: 8px; border-radius: 8px;">
                            <summary style="cursor: pointer; font-weight: 600; color: var(--body-text-color);">4. Data Size (Volume)</summary>
                            <div class="content" style="padding-top: 12px; padding-left: 12px;">
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color);"><span class="radio-circle selected" style="display:inline-block; width:12px; height:12px; border-radius:50%; background:var(--color-accent); margin-right:8px;"></span> <b>Small (20%)</b> - AI Learns fast, but sees less data.</div>
                                <div class="widget-row" style="margin-bottom: 4px; color: var(--body-text-color-subdued);"><span class="radio-circle" style="display:inline-block; width:12px; height:12px; border-radius:50%; border:1px solid var(--body-text-color-subdued); margin-right:8px;"></span> <b>Full (100%)</b> - AI sees more data and learns more slowly.</div>
                                
                                <div class="info-popup" style="background: var(--background-fill-secondary); padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color-primary);">
                                    <b style="color: var(--body-text-color);">In the Game:</b> <span style="color: var(--body-text-color);">You choose how much history the model reads.</span><br>
                                    <i style="color: var(--body-text-color-subdued);">Tip: Use "Small" to test ideas quickly. Use "Full" when you think you have a winning strategy.</i>
                                </div>
                            </div>
                        </details>
                    </div>
                </div>
                """
            )
            
            
            with gr.Row():
                briefing_5_back = gr.Button("◀️ Back", size="lg")
                briefing_5_next = gr.Button("Next ▶️", variant="primary", size="lg")

        # Slide 6: Final Score
        with gr.Column(visible=False, elem_id="slide-6") as briefing_slide_6:            
            gr.HTML(
                """
                <div class='slide-content'>
                    <div class='panel-box'>
                        <div class='t-minus-header'>
                            <h2 class='t-minus-title'>🚀 Mission Briefing: The Final Score</h2>
                        </div>
                        
                        <p style='font-size: 1.15rem; text-align:center; margin-bottom: 24px;'>
                            Your access is granted. Here is how your work will be judged.
                        </p>
            
                        <!-- How to Win Section -->
                        <div style='background:var(--prose-background-fill); padding:20px; border-radius:12px; text-align:left; margin-bottom:24px;'>
                            <div style='display:flex; align-items:center; gap:8px; margin-bottom:12px;'>
                                <span style='font-size:1.5rem;'>🔐</span>
                                <strong style='font-size:1.2rem; color:#eef2ff;'>How to Win</strong>
                            </div>
                            
                            <p style='margin-bottom:12px;'>
                                In the real world, we don't know the future. To simulate this, we have hidden 20% of the case files (data) in a "Vault."
                            </p>
                            
                            <ul style='margin:0; padding-left:24px; color:var(--text-muted); line-height:1.6;'>
                                <li style='margin-bottom:8px;'>
                                    Your AI will learn from the input data you give it, but it will be tested on the hidden data in the Vault.
                                </li>
                                <li>
                                    <b>Your Score:</b> You are scored using prediction accuracy. If you get a 50%, your AI is essentially guessing (like a coin flip). Your goal is to engineer a system that predicts much higher!
                                </li>
                            </ul>
                        </div>
            
                        <!-- Ranks Section -->
                        <div style='text-align:center; border-top:1px solid var(--card-border-subtle); padding-top:20px; margin-bottom:30px;'>
                            <h3 style='margin:0 0 8px 0; font-size:1.2rem;'>Unlockable Ranks</h3>
                            <p style='margin-bottom:16px; font-size:0.95rem; color:var(--text-muted);'>
                                As you refine your model and climb the leaderboard, you will earn new ranks:
                            </p>
                            <div style='display:inline-flex; gap:12px; flex-wrap:wrap; justify-content:center;'>
                                <span style='padding:6px 12px; background:#064e3b; border-radius:20px; font-size:0.9rem;'>⭐ Rookie</span>
                                <span style='padding:6px 12px; background:#e0e7ff; border-radius:20px; font-size:0.9rem; color:#4338ca;'>⭐⭐ Junior</span>
                                <span style='padding:6px 12px; background:#fae8ff; border-radius:20px; font-size:0.9rem; color:#86198f;'>⭐⭐⭐ Lead Engineer</span>
                            </div>
                        </div>
                        
                        <!-- CTA Section -->
                        <div style='text-align:center; background: color-mix(in srgb, var(--color-accent) 10%, transparent); padding: 20px; border-radius: 12px; border: 2px solid var(--color-accent);'>
                            <p style='margin:0 0 8px 0; font-size: 1.1rem; color: var(--text-muted);'>To start the competition:</p>
                            <b style='color:var(--accent-strong); font-size:1.3rem;'>Click "Begin", then "Build & Submit Model"</b>
                            <p style='margin:8px 0 0 0; font-size: 1rem;'>This will make your first submission to the leaderboard.</p>
                        </div>
                    </div>
                </div>
                """
            )
            # --- END FIX ---
            
            with gr.Row():
                briefing_6_back = gr.Button("◀️ Back", size="lg")
                briefing_6_next = gr.Button("Begin Model Building ▶️", variant="primary", size="lg")

        # --- End Briefing Slideshow ---


        # Model Building App (Main Interface)
        with gr.Column(visible=False, elem_id="model-step") as model_building_step:
            gr.Markdown("<h1 style='text-align:center;'>🛠️ Model Building Arena</h1>")
            
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

            rank_message_display = gr.Markdown("### Rank loading...")
            with gr.Row():
                with gr.Column(scale=1):

                    model_type_radio = gr.Radio(
                        label="1. Model Strategy",
                        # Initialize with all possible keys so validation passes even if browser caches a high-rank selection
                        choices=list(MODEL_TYPES.keys()), 
                        value=DEFAULT_MODEL,
                        interactive=False
                    )
                    model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL))

                    gr.Markdown("---") # Separator

                    complexity_slider = gr.Slider(
                        label="2. Model Complexity (1–10)",
                        minimum=1, maximum=3, step=1, value=2,
                        info="Higher values allow deeper pattern learning; very high values may overfit."
                    )

                    gr.Markdown("---") # Separator

                    feature_set_checkbox = gr.CheckboxGroup(
                        label="3. Select Data Ingredients",
                        choices=FEATURE_SET_ALL_OPTIONS,
                        value=DEFAULT_FEATURE_SET,
                        interactive=False,
                        info="More ingredients unlock as you rank up!"
                    )

                    gr.Markdown("---") # Separator

                    data_size_radio = gr.Radio(
                        label="4. Data Size",
                        choices=[DEFAULT_DATA_SIZE],
                        value=DEFAULT_DATA_SIZE,
                        interactive=False
                    )

                    gr.Markdown("---") # Separator

                    # Attempt tracker display
                    attempts_tracker_display = gr.HTML(
                        value="<div style='text-align:center; padding:8px; margin:8px 0; background:#f0f9ff; border-radius:8px; border:1px solid #bae6fd;'>"
                        "<p style='margin:0; color:#0369a1; font-weight:600; font-size:1rem;'>📊 Attempts used: 0/10</p>"
                        "</div>",
                        visible=True
                    )

                    submit_button = gr.Button(
                        value="5. 🔬 Build & Submit Model",
                        variant="primary",
                        size="lg"
                    )

                with gr.Column(scale=1):
                    gr.HTML(
                        """
                        <div class='leaderboard-box'>
                            <h3 style='margin-top:0;'>🏆 Live Standings</h3>
                            <p style='margin:0;'>Submit a model to see your rank.</p>
                        </div>
                        """
                    )

                    # KPI Card
                    submission_feedback_display = gr.HTML(
                        "<p style='text-align:center; color:#6b7280; padding:20px 0;'>Submit your first model to get feedback!</p>"
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
                        with gr.TabItem("Team Standings"):
                            team_leaderboard_display = gr.HTML(
                                "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see team rankings.</p>"
                            )
                        with gr.TabItem("Individual Standings"):
                            individual_leaderboard_display = gr.HTML(
                                "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see individual rankings.</p>"
                            )

            # REMOVED: Ethical Reminder HTML Block
            step_2_next = gr.Button("Finish & Reflect ▶️", variant="secondary")

        # Conclusion Step
        with gr.Column(visible=False, elem_id="conclusion-step") as conclusion_step:
            gr.Markdown("<h1 style='text-align:center;'>✅ Section Complete</h1>")
            final_score_display = gr.HTML(value="<p>Preparing final summary...</p>")
            step_3_back = gr.Button("◀️ Back to Experiment")

        # --- Navigation Logic ---
        all_steps_nav = [
            briefing_slide_1, briefing_slide_2, briefing_slide_3,
            briefing_slide_4, briefing_slide_5,  briefing_slide_6, 
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
            js=nav_js("slide-4", "System check...")
        )
        briefing_5_next.click(
            fn=create_nav(briefing_slide_5,briefing_slide_6),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-6", "Final Clearance...")
        )
        briefing_6_back.click(
            fn=create_nav(briefing_slide_6, briefing_slide_5),
            inputs=None, outputs=all_steps_nav,
            js=nav_js("slide-5", "Configuring brain settings...")
        )
        briefing_6_next.click(
            fn=create_nav(briefing_slide_6, model_building_step),
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

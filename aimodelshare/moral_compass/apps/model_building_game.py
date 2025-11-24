"""
Model Building Game - Gradio application for the Justice & Equity Challenge.

Session-based authentication with leaderboard caching and progressive rank unlocking.
"""

import os
import time
import random
import requests
import contextlib
from io import StringIO
import threading
import functools
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

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

LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

# In-memory caches (per container instance)
_cache_lock = threading.Lock()
_leaderboard_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

def _log(msg: str):
    """Log message if DEBUG_LOG is enabled."""
    if DEBUG_LOG:
        print(f"[ModelBuildingGame] {msg}")

def _normalize_team_name(name: str) -> str:
    """
    Normalize team name for consistent comparison and storage.
    Strips leading/trailing whitespace and collapses multiple spaces.
    """
    if not name:
        return ""
    return " ".join(str(name).strip().split())


def _fetch_leaderboard(token: str) -> Optional[pd.DataFrame]:
    """
    Fetch leaderboard with caching (TTL: LEADERBOARD_CACHE_SECONDS).
    Thread-safe via _cache_lock.
    """
    now = time.time()
    with _cache_lock:
        if (
            _leaderboard_cache["data"] is not None
            and now - _leaderboard_cache["timestamp"] < LEADERBOARD_CACHE_SECONDS
        ):
            _log("Leaderboard cache hit")
            return _leaderboard_cache["data"]

    _log("Fetching fresh leaderboard...")
    try:
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        df = playground.get_leaderboard(token=token)
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
        _log(f"Leaderboard fetched: {len(df) if df is not None else 0} entries")
    except Exception as e:
        _log(f"Leaderboard fetch failed: {e}")
        df = None

    with _cache_lock:
        _leaderboard_cache["data"] = df
        _leaderboard_cache["timestamp"] = time.time()
    return df

def _get_or_assign_team(username: str, leaderboard_df: Optional[pd.DataFrame]) -> Tuple[str, bool]:
    """
    Get existing team from leaderboard or assign random team.
    Uses most recent submission timestamp to recover team.
    Returns: (team_name, is_new_assignment)
    """
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
        # TEAM_NAMES is defined in configuration section
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        _log(f"Assigning new team to {username}: {new_team}")
        return new_team, True
    except Exception as e:
        _log(f"Team assignment error: {e}")
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        return new_team, True

def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Attempt to authenticate user via session token from URL parameters.
    Returns: (success, username, token) - NO os.environ mutation.
    """
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
    Compute user statistics with caching (TTL: USER_STATS_TTL).
    Returns dict with best_score, rank, team_name, submission_count.
    """
    now = time.time()
    cached = _user_stats_cache.get(username)
    if cached and (now - cached.get("_ts", 0) < USER_STATS_TTL):
        _log(f"User stats cache hit for {username}")
        return cached

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
                    # Get most recent score
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
            
            # Compute rank
            if "accuracy" in leaderboard_df.columns:
                user_bests = leaderboard_df.groupby("username")["accuracy"].max()
                ranked = user_bests.sort_values(ascending=False)
                try:
                    stats["rank"] = int(ranked.index.get_loc(username) + 1)
                except KeyError:
                    stats["rank"] = 0
    except Exception as e:
        _log(f"Error computing stats for {username}: {e}")

    _user_stats_cache[username] = stats
    _log(f"Stats for {username}: {stats}")
    return stats

def check_attempt_limit(submission_count: int, limit: int = None) -> Tuple[bool, str]:
    """
    Check if submission count exceeds limit.
    Returns: (can_submit, message)
    """
    # ATTEMPT_LIMIT is defined in configuration section below
    if limit is None:
        limit = ATTEMPT_LIMIT
    
    if submission_count >= limit:
        msg = f"⚠️ Attempt limit reached ({submission_count}/{limit})"
        return False, msg
    return True, f"Attempts: {submission_count}/{limit}"

# -------------------------------------------------------------------------
# 1. Configuration
# -------------------------------------------------------------------------

MY_PLAYGROUND_ID = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"

# --- Submission Limit Configuration ---
# Maximum number of successful leaderboard submissions per user per session.
# Preview runs (pre-login) and failed/invalid attempts do NOT count toward this limit.
# Only actual successful playground.submit_model() calls increment the count.
ATTEMPT_LIMIT = 10

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
        # Step 5: Leaderboard prefetch
        if playground is not None:
            _ = playground.get_leaderboard()
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

@functools.lru_cache(maxsize=32)
def _get_cached_preprocessor_config(numeric_cols_tuple, categorical_cols_tuple):
    """
    Create and return preprocessor configuration (memoized).
    Uses tuples for hashability in lru_cache.
    
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
        cat_tf = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])
        transformers.append(("cat", cat_tf, categorical_cols))
        selected_cols.extend(categorical_cols)
    
    return transformers, selected_cols

def build_preprocessor(numeric_cols, categorical_cols):
    """
    Build a preprocessor using cached configuration.
    The configuration (pipeline structure) is memoized; the actual fit is not.
    """
    # Convert to tuples for caching
    numeric_tuple = tuple(sorted(numeric_cols))
    categorical_tuple = tuple(sorted(categorical_cols))
    
    transformers, selected_cols = _get_cached_preprocessor_config(numeric_tuple, categorical_tuple)
    
    # Create new ColumnTransformer with cached config
    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    
    return preprocessor, selected_cols

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

def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count, is_preview=False):
    """Generates the HTML for the KPI feedback card. Supports preview mode label."""

    # Handle preview mode - Styled to match "success" card
    if is_preview:
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
        <h2 style='color: #111827; margin-top:0;'>{title}</h2>
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
#     Examples:
#         - Demographic parity: P(pred=1|sensitive=A) ≈ P(pred=1|sensitive=B)
#         - Equalized odds: FPR and TPR should be similar across groups
#         - Disparate impact ratio: min/max of positive prediction rates
#     """
#     pass

# -------------------------------------------------------------------------


def generate_competitive_summary(leaderboard_df, team_name, username, last_submission_score, last_rank, submission_count):
    """
    Build summaries, HTML, and KPI card.
    Returns (team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score).
    """
    team_summary_df = pd.DataFrame(columns=["Team", "Best_Score", "Avg_Score", "Submissions"])
    individual_summary_df = pd.DataFrame(columns=["Engineer", "Best_Score", "Submissions"])

    if leaderboard_df is None or leaderboard_df.empty or "accuracy" not in leaderboard_df.columns:
        return (
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Leaderboard empty.</p>",
            "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Leaderboard empty.</p>",
            _build_kpi_card_html(0, 0, 0, 0, 0), 0.0, 0, 0.0
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
        my_submissions = leaderboard_df[leaderboard_df["username"] == username].sort_values(
            by="timestamp", ascending=False
        )
        if not my_submissions.empty:
            this_submission_score = my_submissions.iloc[0]["accuracy"]

        my_rank_row = individual_summary_df[individual_summary_df["Engineer"] == username]
        if not my_rank_row.empty:
            new_rank = my_rank_row.index[0]
            new_best_accuracy = my_rank_row["Best_Score"].iloc[0]

    except Exception:
        pass # Keep defaults

    # Generate HTML outputs
    team_html = _build_team_html(team_summary_df, os.environ.get("TEAM_NAME"))
    individual_html = _build_individual_html(individual_summary_df, username)
    kpi_card_html = _build_kpi_card_html(
        this_submission_score, last_submission_score, new_rank, last_rank, submission_count
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
# Login components (will be assigned in create_model_building_game_app)
login_username = None
login_password = None
login_submit = None
login_error = None
# This one will be assigned globally but is also defined in the function
# first_submission_score_state = None 

def get_or_assign_team(username):
    """
    Get the existing team for a user from the leaderboard, or assign a new random team.
    
    Queries the playground leaderboard to check if the user has prior submissions with
    a team assignment. If found, returns that team (most recent if multiple submissions).
    Otherwise assigns a random team. All team names are normalized for consistency.
    
    Args:
        username: str, the username to check for existing team
    
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
        
        leaderboard_df = playground.get_leaderboard()
        
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
    Perform inline authentication and set credentials in environment.
    
    Validates non-empty credentials, sets environment variables, and attempts
    to fetch AWS token via get_aws_token(). Returns Gradio component updates
    for login UI visibility and feedback messages.
    
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
            team_name_state: gr.update()
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
            team_name_state: gr.update()
        }
    
    # Set credentials in environment
    os.environ["username"] = username_input.strip()
    os.environ["password"] = password_input.strip()
    
    # Attempt to get AWS token
    try:
        token = get_aws_token()
        os.environ["AWS_TOKEN"] = token
        
        # Get or assign team for this user (already normalized by get_or_assign_team)
        team_name, is_new_team = get_or_assign_team(username_input.strip())
        # Normalize team name before storing (defensive - already normalized by get_or_assign_team)
        team_name = _normalize_team_name(team_name)
        os.environ["TEAM_NAME"] = team_name
        
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
            team_name_state: gr.update(value=team_name)
        }
        
    except Exception as e:
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
            team_name_state: gr.update()
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
    progress=gr.Progress()
):
    """
    Core experiment: Uses 'yield' for visual updates and progress bar.
    """
    
    # Fetch the username from os.environ at runtime, not from a stale state.
    username = os.environ.get("username") or "Unknown_User"
    
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
    feature_set = feature_set or []
    complexity_level = safe_int(complexity_level, 2)

    log_output = f"▶ New Experiment\nModel: {model_name_key}\n..."

    # Check readiness
    with INIT_LOCK:
        flags = INIT_FLAGS.copy()
    
    ready_for_submission = flags["competition"] and flags["dataset_core"] and flags["pre_samples_small"]
    
    # If not ready but warm mini available, run preview
    if not ready_for_submission and flags["warm_mini"] and X_TRAIN_WARM is not None:
        progress(0.5, desc="Running Preview...")
        yield { 
            submission_feedback_display: gr.update(value=get_status_html("Preview", "Warm-up Run", "Testing on mini-dataset..."), visible=True),
            login_error: gr.update(visible=False)
        }
        
        try:
            # Run preview on warm mini dataset
            numeric_cols = [f for f in feature_set if f in ALL_NUMERIC_COLS]
            categorical_cols = [f for f in feature_set if f in ALL_CATEGORICAL_COLS]
            
            if not numeric_cols and not categorical_cols:
                raise ValueError("No features selected for modeling.")
            
            # Quick preprocessing and training on warm mini (uses memoized preprocessor)
            preprocessor, selected_cols = build_preprocessor(numeric_cols, categorical_cols)
            
            X_warm_processed = preprocessor.fit_transform(X_TRAIN_WARM[selected_cols])
            X_test_processed = preprocessor.transform(X_TEST_RAW[selected_cols])
            
            base_model = MODEL_TYPES[model_name_key]["model_builder"]()
            tuned_model = tune_model_complexity(base_model, complexity_level)
            tuned_model.fit(X_warm_processed, Y_TRAIN_WARM)
            
            # Get preview score
            from sklearn.metrics import accuracy_score
            predictions = tuned_model.predict(X_test_processed)
            preview_score = accuracy_score(Y_TEST, predictions)
            
            # Show preview card
            preview_html = _build_kpi_card_html(preview_score, 0, 0, 0, -1, is_preview=True)
            
            settings = compute_rank_settings(
                 submission_count, model_name_key, complexity_level, feature_set, data_size_str
            )
            
            final_updates = {
                submission_feedback_display: gr.update(value=preview_html, visible=True),
                team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True),
                individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False),
                last_submission_score_state: last_submission_score,
                last_rank_state: last_rank,
                best_score_state: best_score,
                submission_count_state: submission_count,
                rank_message_display: settings["rank_message"],
                model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
                complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
                feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
                data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
                submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
                login_error: gr.update(visible=False),
                attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
            }
            yield final_updates
            return
            
        except Exception as e:
            print(f"Preview failed: {e}")
            # Fall through to error handling
    
    if playground is None or not ready_for_submission:
        settings = compute_rank_settings(
             submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )
        
        error_msg = "<p style='text-align:center; color:red; padding:20px 0;'>"
        if playground is None:
            error_msg += "Playground not connected. Please try again later."
        else:
            error_msg += "Data still initializing. Please wait a moment and try again."
        error_msg += "</p>"
        
        error_updates = {
            submission_feedback_display: gr.update(value=error_msg, visible=True),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True),
            individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False),
            last_submission_score_state: last_submission_score,
            last_rank_state: last_rank,
            best_score_state: best_score,
            submission_count_state: submission_count,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
        }
        yield error_updates
        return

    try:
        # --- Stage 2: Train Model (Local) ---
        progress(0.3, desc="Training Model...")
        yield { 
            submission_feedback_display: gr.update(value=get_status_html(2, "Training Model", "The machine is learning from history..."), visible=True),
            login_error: gr.update(visible=False)
        }

        # A. Get pre-sampled data
        sample_frac = DATA_SIZE_MAP.get(data_size_str, 0.2)
        X_train_sampled = X_TRAIN_SAMPLES_MAP[data_size_str]
        y_train_sampled = Y_TRAIN_SAMPLES_MAP[data_size_str]
        log_output += f"Using {int(sample_frac * 100)}% data.\n"

        # B. Determine features...
        numeric_cols = []
        categorical_cols = []
        for feat in feature_set:
            if feat in ALL_NUMERIC_COLS: numeric_cols.append(feat)
            elif feat in ALL_CATEGORICAL_COLS: categorical_cols.append(feat)

        if not numeric_cols and not categorical_cols:
            raise ValueError("No features selected for modeling.")

        # C. Preprocessing (uses memoized preprocessor builder)
        preprocessor, selected_cols = build_preprocessor(numeric_cols, categorical_cols)

        X_train_processed = preprocessor.fit_transform(X_train_sampled[selected_cols])
        X_test_processed = preprocessor.transform(X_TEST_RAW[selected_cols])

        # D. Model build & tune
        base_model = MODEL_TYPES[model_name_key]["model_builder"]()
        tuned_model = tune_model_complexity(base_model, complexity_level)

        # E. Train
        tuned_model.fit(X_train_processed, y_train_sampled)
        log_output += "Training done.\n"

        # --- Stage 3: Submit (API Call 1) ---
        # AUTHENTICATION GATE: Check for AWS_TOKEN before submission
        if os.environ.get("AWS_TOKEN") is None:
            # User not authenticated - compute preview score and show login prompt
            progress(0.6, desc="Computing Preview Score...")
            
            predictions = tuned_model.predict(X_test_processed)
            from sklearn.metrics import accuracy_score
            preview_score = accuracy_score(Y_TEST, predictions)
            
            # --- FIX APPLIED HERE ---
            # 1. Generate the styled preview card
            preview_card_html = _build_kpi_card_html(
                new_score=preview_score,
                last_score=0,
                new_rank=0,
                last_rank=0,
                submission_count=-1, # Force preview
                is_preview=True
            )
            
            # 2. Get the login prompt text
            login_prompt_text_html = build_login_prompt_html() # No longer pass score
            
            # 3. Manually combine them by injecting login text inside the kpi-card div
            closing_div_index = preview_card_html.rfind("</div>")
            if closing_div_index != -1:
                combined_html = preview_card_html[:closing_div_index] + login_prompt_text_html + "</div>"
            else:
                combined_html = preview_card_html + login_prompt_text_html # Fallback
            # --- END OF FIX ---
                
            settings = compute_rank_settings(
                submission_count, model_name_key, complexity_level, feature_set, data_size_str
            )
            
            # Show login prompt and enable login form
            gate_updates = {
                submission_feedback_display: gr.update(value=combined_html, visible=True), # Use combined HTML
                submit_button: gr.update(value="Sign In Required", interactive=False),
                login_username: gr.update(visible=True),
                login_password: gr.update(visible=True),
                login_submit: gr.update(visible=True),
                login_error: gr.update(value="", visible=False),
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
                attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
            }
            yield gate_updates
            return  # Stop here - user needs to login and resubmit
        
        # User is authenticated - proceed with submission
        # --- ATTEMPT LIMIT CHECK ---
        # Check if user has reached the submission limit BEFORE submitting to leaderboard.
        # Only successful submissions to playground.submit_model() count toward ATTEMPT_LIMIT.
        # Preview runs, failed attempts, and pre-login runs do NOT count.
        if submission_count >= ATTEMPT_LIMIT:
            # User has reached the attempt limit - show warning and disable controls
            limit_warning_html = f"""
            <div class='kpi-card' style='border-color: #ef4444;'>
                <h2 style='color: #111827; margin-top:0;'>🛑 Submission Limit Reached</h2>
                <div class='kpi-card-body'>
                    <div class='kpi-metric-box'>
                        <p class='kpi-label'>Attempts Used</p>
                        <p class='kpi-score' style='color: #ef4444;'>{ATTEMPT_LIMIT} / {ATTEMPT_LIMIT}</p>
                        <p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Maximum submissions reached</p>
                    </div>
                </div>
                <div style='margin-top: 16px; background:#fef2f2; padding:16px; border-radius:12px; text-align:left; font-size:0.98rem; line-height:1.4;'>
                    <p style='margin:0; color:#991b1b;'><b>Nice Work!  Don't worry, you will have a chance compete further to improve your model more after a few new activities.  </b></p>
                    <p style='margin:8px 0 0 0; color:#7f1d1d;'>
                        Scroll down to click "Finish and Reflect" to see a summary of your results so far.
                    </p>
                </div>
            </div>
            """
            
            settings = compute_rank_settings(
                submission_count, model_name_key, complexity_level, feature_set, data_size_str
            )
            
            # Disable all interactive controls - user can only view results
            limit_reached_updates = {
                submission_feedback_display: gr.update(value=limit_warning_html, visible=True),
                submit_button: gr.update(value="🛑 Submission Limit Reached", interactive=False),
                model_type_radio: gr.update(interactive=False),
                complexity_slider: gr.update(interactive=False),
                feature_set_checkbox: gr.update(interactive=False),
                data_size_radio: gr.update(interactive=False),
                attempts_tracker_display: gr.update(value=f"<div style='text-align:center; padding:8px; margin:8px 0; background:#fef2f2; border-radius:8px; border:1px solid #ef4444;'>"
                    f"<p style='margin:0; color:#991b1b; font-weight:600; font-size:1rem;'>🛑 Attempts used: {ATTEMPT_LIMIT}/{ATTEMPT_LIMIT} (Limit Reached)</p>"
                    "</div>"),
                team_leaderboard_display: team_leaderboard_display,
                individual_leaderboard_display: individual_leaderboard_display,
                last_submission_score_state: last_submission_score,
                last_rank_state: last_rank,
                best_score_state: best_score,
                submission_count_state: submission_count,
                first_submission_score_state: first_submission_score,
                rank_message_display: settings["rank_message"],
                login_error: gr.update(visible=False)
            }
            yield limit_reached_updates
            return  # Stop here - no more submissions allowed
        # --- END ATTEMPT LIMIT CHECK ---
        
        progress(0.5, desc="Submitting to Cloud...")
        yield { 
            submission_feedback_display: gr.update(value=get_status_html(3, "Submitting", "Sending model to the competition server..."), visible=True),
            login_error: gr.update(visible=False)
        }

        predictions = tuned_model.predict(X_test_processed)
        description = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})"
        tags = f"team:{os.environ.get("TEAM_NAME")},model:{model_name_key}"

        playground.submit_model(
            model=tuned_model, preprocessor=preprocessor, prediction_submission=predictions,
            input_dict={'description': description, 'tags': tags},
            custom_metadata={'Team': os.environ.get("TEAM_NAME"), 'Moral_Compass': 0}
        )
        log_output += "\nSUCCESS! Model submitted.\n"

        # --- Stage 4: Refresh Leaderboard (API Call 2) ---
        # Show skeletons while fetching
        progress(0.8, desc="Updating Leaderboard...")
        yield {
            submission_feedback_display: gr.update(value=get_status_html(4, "Calculating Rank", "Comparing your score against others..."), visible=True),
            team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True),
            individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False),
            login_error: gr.update(visible=False)
        }

        full_leaderboard_df = playground.get_leaderboard()

        # Call new summary function
        team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score = generate_competitive_summary(
            full_leaderboard_df,
            team_name,
            username,
            last_submission_score,
            last_rank,
            submission_count
        )

        # --- Stage 5: Final UI Update ---
        progress(1.0, desc="Complete!")
        # No need for Step 5 HTML update, jumping to results

        new_submission_count = submission_count + 1
        
        # Track first submission score
        new_first_submission_score = first_submission_score
        if submission_count == 0 and first_submission_score is None:
            new_first_submission_score = this_submission_score
        
        settings = compute_rank_settings(
            new_submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )

        final_updates = {
            submission_feedback_display: gr.update(value=kpi_card_html, visible=True),
            team_leaderboard_display: team_html,
            individual_leaderboard_display: individual_html,
            last_submission_score_state: this_submission_score, 
            last_rank_state: new_rank, 
            best_score_state: new_best_accuracy,
            submission_count_state: new_submission_count,
            first_submission_score_state: new_first_submission_score,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(new_submission_count))
        }
        yield final_updates

    except Exception as e:
        error_msg = f"ERROR: {e}"
        settings = compute_rank_settings(
             submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )
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
            login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
        }
        yield error_updates


def on_initial_load(username):
    """
    Updated to load HTML leaderboards with skeleton placeholders during init.
    Shows skeleton if leaderboard not yet ready, real data otherwise.
    """

    initial_ui = compute_rank_settings(
        0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE
    )

    # Check if leaderboard is ready
    with INIT_LOCK:
        leaderboard_ready = INIT_FLAGS["leaderboard"]
    
    if not leaderboard_ready:
        # Show skeleton placeholders while loading
        team_html = _build_skeleton_leaderboard(rows=6, is_team=True)
        individual_html = _build_skeleton_leaderboard(rows=6, is_team=False)
    else:
        # Try to load real leaderboard data
        team_html = "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see team rankings.</p>"
        individual_html = "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see individual rankings.</p>"
        try:
            if playground:
                full_leaderboard_df = playground.get_leaderboard()
                team_html, individual_html, _, _, _, _ = generate_competitive_summary(
                    full_leaderboard_df,
                    os.environ.get("TEAM_NAME"),
                    username,
                    0, 0, -1
                )
        except Exception as e:
            print(f"Error on initial load: {e}")
            team_html = "<p style='text-align:center; color:red; padding-top:20px;'>Could not load leaderboard.</p>"
            individual_html = "<p style='text-align:center; color:red; padding-top:20px;'>Could not load leaderboard.</p>"

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


# -------------------------------------------------------------------------
# 3. Factory Function: Build Gradio App
# -------------------------------------------------------------------------

def create_model_building_game_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """
    Create (but do not launch) the model building game app.
    Starts background initialization automatically.
    """
    # Start background initialization thread
    start_background_init()
    
import os
import time
import random
import requests
import contextlib
from io import StringIO
import threading
import functools
from pathlib import Path
from datetime import datetime, timedelta

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
# 1. Configuration
# -------------------------------------------------------------------------

MY_PLAYGROUND_ID = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"

# --- Submission Limit Configuration ---
# Maximum number of successful leaderboard submissions per user per session.
# Preview runs (pre-login) and failed/invalid attempts do NOT count toward this limit.
# Only actual successful playground.submit_model() calls increment the count.
ATTEMPT_LIMIT = 10

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
        # Step 5: Leaderboard prefetch
        if playground is not None:
            _ = playground.get_leaderboard()
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

@functools.lru_cache(maxsize=32)
def _get_cached_preprocessor_config(numeric_cols_tuple, categorical_cols_tuple):
    """
    Create and return preprocessor configuration (memoized).
    Uses tuples for hashability in lru_cache.
    
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
        cat_tf = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])
        transformers.append(("cat", cat_tf, categorical_cols))
        selected_cols.extend(categorical_cols)
    
    return transformers, selected_cols

def build_preprocessor(numeric_cols, categorical_cols):
    """
    Build a preprocessor using cached configuration.
    The configuration (pipeline structure) is memoized; the actual fit is not.
    """
    # Convert to tuples for caching
    numeric_tuple = tuple(sorted(numeric_cols))
    categorical_tuple = tuple(sorted(categorical_cols))
    
    transformers, selected_cols = _get_cached_preprocessor_config(numeric_tuple, categorical_tuple)
    
    # Create new ColumnTransformer with cached config
    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    
    return preprocessor, selected_cols

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

def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count, is_preview=False):
    """
    Generates the HTML for the KPI feedback card.
    Uses theme-driven colors (no hard-coded palette) so dark mode stays consistent.
    """

    # Default semantic CSS classes
    card_classes = ["kpi-card"]
    acc_score_class = "kpi-score"
    rank_score_class = "kpi-score"
    acc_subtext = ""
    rank_subtext = ""

    # Preview mode (no submission)
    if is_preview:
        title = "🔬 Successful Preview Run!"
        card_classes.append("kpi-card--neutral")
        acc_text = f"{(new_score * 100):.2f}%" if new_score > 0 else "N/A"
        rank_text = "N/A"
        acc_subtext = "<p class='kpi-subtext-muted'>(Preview only – not submitted)</p>"
        rank_subtext = "<p class='kpi-subtext-muted'>Not ranked (preview)</p>"

    # First actual submission
    elif submission_count == 0:
        title = "🎉 First Model Submitted!"
        card_classes.append("kpi-card--subtle-accent")
        acc_text = f"{(new_score * 100):.2f}%"
        acc_subtext = "<p class='kpi-subtext-muted'>(Your first score!)</p>"

        rank_text = f"#{new_rank}" if new_rank > 0 else "—"
        rank_subtext = "<p class='kpi-subtext-muted'>You're on the board!</p>"

    else:
        # Subsequent submissions – compare scores and ranks
        score_diff = new_score - last_score

        # Score change text
        if abs(score_diff) < 0.0001:
            title = "✅ Submission Successful"
            card_classes.append("kpi-card--neutral")
            acc_text = f"{(new_score * 100):.2f}%"
            acc_subtext = "<p class='kpi-subtext-muted'>No change (↔)</p>"
        elif score_diff > 0:
            title = "✅ Submission Successful!"
            card_classes.append("kpi-card--subtle-accent")
            acc_text = f"{(new_score * 100):.2f}%"
            acc_subtext = f"<p class='kpi-subtext-muted'>+{(score_diff * 100):.2f} points (⬆️)</p>"
        else:
            title = "📉 Score Dropped"
            card_classes.append("kpi-card--neutral")
            acc_text = f"{(new_score * 100):.2f}%"
            acc_subtext = f"<p class='kpi-subtext-muted'>{(score_diff * 100):.2f} points (⬇️)</p>"

        # Rank change
        rank_text = f"#{new_rank}" if new_rank > 0 else "—"
        rank_diff = last_rank - new_rank

        if last_rank == 0 and new_rank > 0:
            rank_subtext = "<p class='kpi-subtext-muted'>You're on the board!</p>"
        elif rank_diff > 0:
            rank_subtext = f"<p class='kpi-subtext-muted'>🚀 Moved up {rank_diff} spot{'s' if rank_diff > 1 else ''}!</p>"
        elif rank_diff < 0:
            rank_subtext = f"<p class='kpi-subtext-muted'>🔻 Dropped {abs(rank_diff)} spot{'s' if abs(rank_diff) > 1 else ''}</p>"
        else:
            rank_subtext = "<p class='kpi-subtext-muted'>No rank change (↔)</p>"

    classes_str = " ".join(card_classes)

    return f"""
    <div class='{classes_str}'>
        <h2 style='margin-top:0;'>{title}</h2>
        <div class='kpi-card-body'>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>New Accuracy</p>
                <p class='{acc_score_class}'>{acc_text}</p>
                {acc_subtext}
            </div>
            <div class='kpi-metric-box'>
                <p class='kpi-label'>Your Rank</p>
                <p class='{rank_score_class}'>{rank_text}</p>
                {rank_subtext}
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

def _build_attempts_tracker_html(current_count, limit=ATTEMPT_LIMIT):
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

# --- End Helper Functions ---


def generate_competitive_summary(leaderboard_df, team_name, username, last_submission_score, last_rank, submission_count):
    """
    Build summaries, HTML, and KPI card.
    Returns (team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score).
    If the leaderboard is empty or missing required columns, returns the skeleton placeholder instead of "Leaderboard empty.".
    """
    team_summary_df = pd.DataFrame(columns=["Team", "Best_Score", "Avg_Score", "Submissions"])
    individual_summary_df = pd.DataFrame(columns=["Engineer", "Best_Score", "Submissions"])

    # Use skeleton placeholder if leaderboard is missing "accuracy" or is empty
    if leaderboard_df is None or leaderboard_df.empty or "accuracy" not in leaderboard_df.columns:
        team_html = _build_skeleton_leaderboard(rows=6, is_team=True)
        individual_html = _build_skeleton_leaderboard(rows=6, is_team=False)
        return (
            team_html,
            individual_html,
            _build_kpi_card_html(0, 0, 0, 0, 0), 0.0, 0, 0.0
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
        my_submissions = leaderboard_df[leaderboard_df["username"] == username].sort_values(
            by="timestamp", ascending=False
        )
        if not my_submissions.empty:
            this_submission_score = my_submissions.iloc[0]["accuracy"]

        my_rank_row = individual_summary_df[individual_summary_df["Engineer"] == username]
        if not my_rank_row.empty:
            new_rank = my_rank_row.index[0]
            new_best_accuracy = my_rank_row["Best_Score"].iloc[0]

    except Exception:
        pass # Keep defaults

    # Generate HTML outputs
    team_html = _build_team_html(team_summary_df, os.environ.get("TEAM_NAME"))
    individual_html = _build_individual_html(individual_summary_df, username)
    kpi_card_html = _build_kpi_card_html(
        this_submission_score, last_submission_score, new_rank, last_rank, submission_count
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
# Login components (will be assigned in create_model_building_game_app)
login_username = None
login_password = None
login_submit = None
login_error = None
# This one will be assigned globally but is also defined in the function
# first_submission_score_state = None 

def get_or_assign_team(username):
    """
    Get the existing team for a user from the leaderboard, or assign a new random team.
    
    Queries the playground leaderboard to check if the user has prior submissions with
    a team assignment. If found, returns that team (most recent if multiple submissions).
    Otherwise assigns a random team. All team names are normalized for consistency.
    
    Args:
        username: str, the username to check for existing team
    
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
        
        leaderboard_df = playground.get_leaderboard()
        
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
    Perform inline authentication and set credentials in environment.
    
    Validates non-empty credentials, sets environment variables, and attempts
    to fetch AWS token via get_aws_token(). Returns Gradio component updates
    for login UI visibility and feedback messages.
    
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
            team_name_state: gr.update()
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
            team_name_state: gr.update()
        }
    
    # Set credentials in environment
    os.environ["username"] = username_input.strip()
    os.environ["password"] = password_input.strip()
    
    # Attempt to get AWS token
    try:
        token = get_aws_token()
        os.environ["AWS_TOKEN"] = token
        
        # Get or assign team for this user (already normalized by get_or_assign_team)
        team_name, is_new_team = get_or_assign_team(username_input.strip())
        # Normalize team name before storing (defensive - already normalized by get_or_assign_team)
        team_name = _normalize_team_name(team_name)
        os.environ["TEAM_NAME"] = team_name
        
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
            team_name_state: gr.update(value=team_name)
        }
        
    except Exception as e:
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
            team_name_state: gr.update()
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
    progress=gr.Progress()
):
    """
    Core experiment: Uses 'yield' for visual updates and progress bar.
    """
    
    # Fetch the username from os.environ at runtime, not from a stale state.
    username = os.environ.get("username") or "Unknown_User"
    
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
    feature_set = feature_set or []
    complexity_level = safe_int(complexity_level, 2)

    log_output = f"▶ New Experiment\nModel: {model_name_key}\n..."

    # Check readiness
    with INIT_LOCK:
        flags = INIT_FLAGS.copy()
    
    ready_for_submission = flags["competition"] and flags["dataset_core"] and flags["pre_samples_small"]
    
    # If not ready but warm mini available, run preview
    if not ready_for_submission and flags["warm_mini"] and X_TRAIN_WARM is not None:
        progress(0.5, desc="Running Preview...")
        yield { 
            submission_feedback_display: gr.update(value=get_status_html("Preview", "Warm-up Run", "Testing on mini-dataset..."), visible=True),
            login_error: gr.update(visible=False)
        }
        
        try:
            # Run preview on warm mini dataset
            numeric_cols = [f for f in feature_set if f in ALL_NUMERIC_COLS]
            categorical_cols = [f for f in feature_set if f in ALL_CATEGORICAL_COLS]
            
            if not numeric_cols and not categorical_cols:
                raise ValueError("No features selected for modeling.")
            
            # Quick preprocessing and training on warm mini (uses memoized preprocessor)
            preprocessor, selected_cols = build_preprocessor(numeric_cols, categorical_cols)
            
            X_warm_processed = preprocessor.fit_transform(X_TRAIN_WARM[selected_cols])
            X_test_processed = preprocessor.transform(X_TEST_RAW[selected_cols])
            
            base_model = MODEL_TYPES[model_name_key]["model_builder"]()
            tuned_model = tune_model_complexity(base_model, complexity_level)
            tuned_model.fit(X_warm_processed, Y_TRAIN_WARM)
            
            # Get preview score
            from sklearn.metrics import accuracy_score
            predictions = tuned_model.predict(X_test_processed)
            preview_score = accuracy_score(Y_TEST, predictions)
            
            # Show preview card
            preview_html = _build_kpi_card_html(preview_score, 0, 0, 0, -1, is_preview=True)
            
            settings = compute_rank_settings(
                 submission_count, model_name_key, complexity_level, feature_set, data_size_str
            )
            
            final_updates = {
                submission_feedback_display: gr.update(value=preview_html, visible=True),
                team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True),
                individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False),
                last_submission_score_state: last_submission_score,
                last_rank_state: last_rank,
                best_score_state: best_score,
                submission_count_state: submission_count,
                rank_message_display: settings["rank_message"],
                model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
                complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
                feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
                data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
                submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
                login_error: gr.update(visible=False),
                attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
            }
            yield final_updates
            return
            
        except Exception as e:
            print(f"Preview failed: {e}")
            # Fall through to error handling
    
    if playground is None or not ready_for_submission:
        settings = compute_rank_settings(
             submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )
        
        error_msg = "<p style='text-align:center; color:red; padding:20px 0;'>"
        if playground is None:
            error_msg += "Playground not connected. Please try again later."
        else:
            error_msg += "Data still initializing. Please wait a moment and try again."
        error_msg += "</p>"
        
        error_updates = {
            submission_feedback_display: gr.update(value=error_msg, visible=True),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True),
            individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False),
            last_submission_score_state: last_submission_score,
            last_rank_state: last_rank,
            best_score_state: best_score,
            submission_count_state: submission_count,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
        }
        yield error_updates
        return

    try:
        # --- Stage 2: Train Model (Local) ---
        progress(0.3, desc="Training Model...")
        yield { 
            submission_feedback_display: gr.update(value=get_status_html(2, "Training Model", "The machine is learning from history..."), visible=True),
            login_error: gr.update(visible=False)
        }

        # A. Get pre-sampled data
        sample_frac = DATA_SIZE_MAP.get(data_size_str, 0.2)
        X_train_sampled = X_TRAIN_SAMPLES_MAP[data_size_str]
        y_train_sampled = Y_TRAIN_SAMPLES_MAP[data_size_str]
        log_output += f"Using {int(sample_frac * 100)}% data.\n"

        # B. Determine features...
        numeric_cols = []
        categorical_cols = []
        for feat in feature_set:
            if feat in ALL_NUMERIC_COLS: numeric_cols.append(feat)
            elif feat in ALL_CATEGORICAL_COLS: categorical_cols.append(feat)

        if not numeric_cols and not categorical_cols:
            raise ValueError("No features selected for modeling.")

        # C. Preprocessing (uses memoized preprocessor builder)
        preprocessor, selected_cols = build_preprocessor(numeric_cols, categorical_cols)

        X_train_processed = preprocessor.fit_transform(X_train_sampled[selected_cols])
        X_test_processed = preprocessor.transform(X_TEST_RAW[selected_cols])

        # D. Model build & tune
        base_model = MODEL_TYPES[model_name_key]["model_builder"]()
        tuned_model = tune_model_complexity(base_model, complexity_level)

        # E. Train
        tuned_model.fit(X_train_processed, y_train_sampled)
        log_output += "Training done.\n"

        # --- Stage 3: Submit (API Call 1) ---
        # AUTHENTICATION GATE: Check for AWS_TOKEN before submission
        if os.environ.get("AWS_TOKEN") is None:
            # User not authenticated - compute preview score and show login prompt
            progress(0.6, desc="Computing Preview Score...")
            
            predictions = tuned_model.predict(X_test_processed)
            from sklearn.metrics import accuracy_score
            preview_score = accuracy_score(Y_TEST, predictions)
            
            # --- FIX APPLIED HERE ---
            # 1. Generate the styled preview card
            preview_card_html = _build_kpi_card_html(
                new_score=preview_score,
                last_score=0,
                new_rank=0,
                last_rank=0,
                submission_count=-1, # Force preview
                is_preview=True
            )
            
            # 2. Get the login prompt text
            login_prompt_text_html = build_login_prompt_html() # No longer pass score
            
            # 3. Manually combine them by injecting login text inside the kpi-card div
            closing_div_index = preview_card_html.rfind("</div>")
            if closing_div_index != -1:
                combined_html = preview_card_html[:closing_div_index] + login_prompt_text_html + "</div>"
            else:
                combined_html = preview_card_html + login_prompt_text_html # Fallback
            # --- END OF FIX ---
                
            settings = compute_rank_settings(
                submission_count, model_name_key, complexity_level, feature_set, data_size_str
            )
            
            # Show login prompt and enable login form
            gate_updates = {
                submission_feedback_display: gr.update(value=combined_html, visible=True), # Use combined HTML
                submit_button: gr.update(value="Sign In Required", interactive=False),
                login_username: gr.update(visible=True),
                login_password: gr.update(visible=True),
                login_submit: gr.update(visible=True),
                login_error: gr.update(value="", visible=False),
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
                attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
            }
            yield gate_updates
            return  # Stop here - user needs to login and resubmit
        
        # User is authenticated - proceed with submission
        # --- ATTEMPT LIMIT CHECK ---
        # Check if user has reached the submission limit BEFORE submitting to leaderboard.
        # Only successful submissions to playground.submit_model() count toward ATTEMPT_LIMIT.
        # Preview runs, failed attempts, and pre-login runs do NOT count.
        if submission_count >= ATTEMPT_LIMIT:
            # User has reached the attempt limit - show warning and disable controls
            limit_warning_html = f"""
            <div class='kpi-card' style='border-color: #ef4444;'>
                <h2 style='color: #111827; margin-top:0;'>🛑 Submission Limit Reached</h2>
                <div class='kpi-card-body'>
                    <div class='kpi-metric-box'>
                        <p class='kpi-label'>Attempts Used</p>
                        <p class='kpi-score' style='color: #ef4444;'>{ATTEMPT_LIMIT} / {ATTEMPT_LIMIT}</p>
                        <p style='font-size: 1.2rem; font-weight: 500; color: #6b7280; margin:0; padding-top: 8px;'>Maximum submissions reached</p>
                    </div>
                </div>
                <div style='margin-top: 16px; background:#fef2f2; padding:16px; border-radius:12px; text-align:left; font-size:0.98rem; line-height:1.4;'>
                    <p style='margin:0; color:#991b1b;'><b>Nice Work!  Don't worry, you will have a chance compete further to improve your model more after a few new activities.  </b></p>
                    <p style='margin:8px 0 0 0; color:#7f1d1d;'>
                        Scroll down to click "Finish and Reflect" to see a summary of your results so far.
                    </p>
                </div>
            </div>
            """
            
            settings = compute_rank_settings(
                submission_count, model_name_key, complexity_level, feature_set, data_size_str
            )
            
            # Disable all interactive controls - user can only view results
            limit_reached_updates = {
                submission_feedback_display: gr.update(value=limit_warning_html, visible=True),
                submit_button: gr.update(value="🛑 Submission Limit Reached", interactive=False),
                model_type_radio: gr.update(interactive=False),
                complexity_slider: gr.update(interactive=False),
                feature_set_checkbox: gr.update(interactive=False),
                data_size_radio: gr.update(interactive=False),
                attempts_tracker_display: gr.update(value=f"<div style='text-align:center; padding:8px; margin:8px 0; background:#fef2f2; border-radius:8px; border:1px solid #ef4444;'>"
                    f"<p style='margin:0; color:#991b1b; font-weight:600; font-size:1rem;'>🛑 Attempts used: {ATTEMPT_LIMIT}/{ATTEMPT_LIMIT} (Limit Reached)</p>"
                    "</div>"),
                team_leaderboard_display: team_leaderboard_display,
                individual_leaderboard_display: individual_leaderboard_display,
                last_submission_score_state: last_submission_score,
                last_rank_state: last_rank,
                best_score_state: best_score,
                submission_count_state: submission_count,
                first_submission_score_state: first_submission_score,
                rank_message_display: settings["rank_message"],
                login_error: gr.update(visible=False)
            }
            yield limit_reached_updates
            return  # Stop here - no more submissions allowed
        # --- END ATTEMPT LIMIT CHECK ---
        
        progress(0.5, desc="Submitting to Cloud...")
        yield { 
            submission_feedback_display: gr.update(value=get_status_html(3, "Submitting", "Sending model to the competition server..."), visible=True),
            login_error: gr.update(visible=False)
        }

        predictions = tuned_model.predict(X_test_processed)
        description = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})"
        tags = f"team:{os.environ.get("TEAM_NAME")},model:{model_name_key}"

        playground.submit_model(
            model=tuned_model, preprocessor=preprocessor, prediction_submission=predictions,
            input_dict={'description': description, 'tags': tags},
            custom_metadata={'Team': os.environ.get("TEAM_NAME"), 'Moral_Compass': 0}
        )
        log_output += "\nSUCCESS! Model submitted.\n"

        # --- Stage 4: Refresh Leaderboard (API Call 2) ---
        # Show skeletons while fetching
        progress(0.8, desc="Updating Leaderboard...")
        yield {
            submission_feedback_display: gr.update(value=get_status_html(4, "Calculating Rank", "Comparing your score against others..."), visible=True),
            team_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=True),
            individual_leaderboard_display: _build_skeleton_leaderboard(rows=6, is_team=False),
            login_error: gr.update(visible=False)
        }

        full_leaderboard_df = playground.get_leaderboard()

        # Call new summary function
        team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score = generate_competitive_summary(
            full_leaderboard_df,
            team_name,
            username,
            last_submission_score,
            last_rank,
            submission_count
        )

        # --- Stage 5: Final UI Update ---
        progress(1.0, desc="Complete!")
        # No need for Step 5 HTML update, jumping to results

        new_submission_count = submission_count + 1
        
        # Track first submission score
        new_first_submission_score = first_submission_score
        if submission_count == 0 and first_submission_score is None:
            new_first_submission_score = this_submission_score
        
        settings = compute_rank_settings(
            new_submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )

        final_updates = {
            submission_feedback_display: gr.update(value=kpi_card_html, visible=True),
            team_leaderboard_display: team_html,
            individual_leaderboard_display: individual_html,
            last_submission_score_state: this_submission_score, 
            last_rank_state: new_rank, 
            best_score_state: new_best_accuracy,
            submission_count_state: new_submission_count,
            first_submission_score_state: new_first_submission_score,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(new_submission_count))
        }
        yield final_updates

    except Exception as e:
        error_msg = f"ERROR: {e}"
        settings = compute_rank_settings(
             submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )
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
            login_error: gr.update(visible=False),
            attempts_tracker_display: gr.update(value=_build_attempts_tracker_html(submission_count))
        }
        yield error_updates


def on_initial_load(username):
    """
    Updated to load HTML leaderboards with skeleton placeholders during init.
    Shows skeleton if leaderboard not yet ready, real data otherwise.
    """

    initial_ui = compute_rank_settings(
        0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE
    )

    # Check if leaderboard is ready
    with INIT_LOCK:
        leaderboard_ready = INIT_FLAGS["leaderboard"]
    
    if not leaderboard_ready:
        # Show skeleton placeholders while loading
        team_html = _build_skeleton_leaderboard(rows=6, is_team=True)
        individual_html = _build_skeleton_leaderboard(rows=6, is_team=False)
    else:
        # Try to load real leaderboard data
        team_html = "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see team rankings.</p>"
        individual_html = "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see individual rankings.</p>"
        try:
            if playground:
                full_leaderboard_df = playground.get_leaderboard()
                team_html, individual_html, _, _, _, _ = generate_competitive_summary(
                    full_leaderboard_df,
                    os.environ.get("TEAM_NAME"),
                    username,
                    0, 0, -1
                )
        except Exception as e:
            print(f"Error on initial load: {e}")
            team_html = "<p style='text-align:center; color:red; padding-top:20px;'>Could not load leaderboard.</p>"
            individual_html = "<p style='text-align:center; color:red; padding-top:20px;'>Could not load leaderboard.</p>"

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
# Conclusion helpers
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

# -------------------------------------------------------------------------
# 3. Factory Function: Build Gradio App
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
    with contextlib.redirect_stdout(open(os.devnull, "w")), contextlib.redirect_stderr(open(os.devnull, "w")):
        demo.launch(share=share, inline=True, debug=debug, height=height)

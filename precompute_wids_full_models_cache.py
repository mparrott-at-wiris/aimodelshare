import os
import json
import gzip
import time
import gc
import itertools
import ast
import pandas as pd
import numpy as np

from joblib import Parallel, delayed

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier

# --- CONFIGURATION ---
MAX_ROWS_TEST = 4000                              # reproduce original X_TEST sampling
MAX_RUNTIME_SEC = int(os.getenv("MAX_RUNTIME_SEC", "3000"))  # allow override via env
BATCH_SIZE = 400

FULL_CHECKPOINT_FILE = "wids_full_models_cache_checkpoint.jsonl"
FULL_FINAL_FILE = "wids_prediction_cache_full_models.json.gz"

BASE_FINAL_FILE = "wids_prediction_cache.json.gz"
BASE_CHECKPOINT_FILE = "wids_cache_checkpoint.jsonl"

# Specified columns for WiDS dataset
ALL_NUMERIC_COLS = ["floor_area", "year_built", "ELEVATION", "heating_degree_days", 
                    "cooling_degree_days", "january_min_temp", "july_max_temp", 
                    "avg_temp", "april_avg_temp", "october_avg_temp"]
ALL_CATEGORICAL_COLS = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
ALL_FEATURES = ALL_NUMERIC_COLS + ALL_CATEGORICAL_COLS

DATA_SIZE_LABEL = "Full (100%)"  # only one data size, as requested

# Original four model names (exact)
BASE_MODEL_TYPES = {
    "The Balanced Generalist": lambda: LogisticRegression(max_iter=200, random_state=42, class_weight="balanced"),
    "The Rule-Maker": lambda: DecisionTreeClassifier(random_state=42, class_weight="balanced"),
    "The 'Nearest Neighbor'": lambda: KNeighborsClassifier(),
    "The Deep Pattern-Finder": lambda: RandomForestClassifier(random_state=42, class_weight="balanced"),
}
MAJORITY_MODEL_NAME = "The Majority Vote"  # derived

WIDS_DATASET_PATH = "datasets/recreated_wids_v2_ny_10k.csv"

# --- DATA PREP (match original script for X_TEST) ---
def load_and_prepare(df: pd.DataFrame, max_rows: int | None):
    df = df.copy()
    
    if max_rows is not None and df.shape[0] > max_rows:
        df = df.sample(n=max_rows, random_state=42)

    # Ensure all required feature columns exist
    for col in ALL_FEATURES:
        if col not in df.columns:
            df[col] = np.nan

    X = df[ALL_FEATURES].copy()
    y = df["high_energy_usage"].copy()
    return X, y

def load_original_test_split():
    df = pd.read_csv(WIDS_DATASET_PATH)
    X, y = load_and_prepare(df, max_rows=MAX_ROWS_TEST)
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    return X_train_raw, X_test_raw, y_train, y_test

def load_full_train_data():
    df = pd.read_csv(WIDS_DATASET_PATH)
    X_full, y_full = load_and_prepare(df, max_rows=None)
    return X_full, y_full

# --- PREPROCESSOR ---
def get_preprocessor(features):
    num = [f for f in features if f in ALL_NUMERIC_COLS]
    cat = [f for f in features if f in ALL_CATEGORICAL_COLS]
    steps = []
    if num:
        steps.append(("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), num))
    if cat:
        steps.append(("cat", Pipeline([("imputer", SimpleImputer(strategy="constant", fill_value="missing")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))]), cat))
    return ColumnTransformer(steps, remainder="drop")

# --- TUNING ---
def tune_model(model, level: int):
    if isinstance(model, LogisticRegression):
        model.C = {1: 0.01, 2: 0.025, 3: 0.05, 4: 0.1, 5: 0.25, 6: 0.5, 7: 1.0, 8: 2.0, 9: 5.0, 10: 10.0}.get(level, 1.0)
    elif isinstance(model, RandomForestClassifier):
        model.n_estimators = {1: 10, 2: 12, 3: 15, 4: 18, 5: 20, 6: 22, 7: 25, 8: 28, 9: 30, 10: 30}.get(level, 20)
        model.max_depth = level * 2 + 2 if level < 9 else None
    elif isinstance(model, DecisionTreeClassifier):
        model.max_depth = level + 1 if level < 10 else None
    elif isinstance(model, KNeighborsClassifier):
        model.n_neighbors = {1: 100, 2: 75, 3: 60, 4: 50, 5: 40, 6: 30, 7: 25, 8: 15, 9: 7, 10: 3}.get(level, 25)
    return model

# --- LOADING BASE CACHE ---
def load_base_cache():
    """
    Tries loading from the base final artifact first, 
    then fallback to checkpoint (JSONL). Returns dict[key -> pred_string].
    """
    base_cache = {}
    
    # 1. Try final gz
    if os.path.exists(BASE_FINAL_FILE):
        print(f"Loading base cache from {BASE_FINAL_FILE}...")
        with gzip.open(BASE_FINAL_FILE, "rt", encoding="UTF-8") as f:
            base_cache = json.load(f)
        print(f"Loaded {len(base_cache)} entries from base final artifact.")
        return base_cache
    
    # 2. Fallback to checkpoint
    if os.path.exists(BASE_CHECKPOINT_FILE):
        print(f"Loading base cache from {BASE_CHECKPOINT_FILE}...")
        with open(BASE_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    base_cache[entry["k"]] = entry["v"]
        print(f"Loaded {len(base_cache)} entries from base checkpoint.")
        return base_cache
    
    print("⚠️ No base cache found. The Majority Vote model requires the base cache.")
    return {}

# --- WORKER ---
def process_task(task, X_full_train, y_full_train, X_test_raw, base_cache):
    model_name, complexity, feature_tuple = task
    feature_key = ",".join(sorted(feature_tuple))
    
    # For Majority Vote, derive from base_cache
    if model_name == MAJORITY_MODEL_NAME:
        # Collect predictions from base models with the same complexity/features/data_size
        base_pred_strings = []
        for base_model_name in BASE_MODEL_TYPES.keys():
            base_key = f"{base_model_name}|{complexity}|Full (100%)|{feature_key}"
            if base_key in base_cache:
                base_pred_strings.append(base_cache[base_key])
        
        if len(base_pred_strings) == 0:
            return None  # can't form majority vote
        
        # Convert strings to arrays
        arrays = [np.array(list(s), dtype=int) for s in base_pred_strings]
        # Majority vote
        stacked = np.stack(arrays, axis=0)
        majority = (np.sum(stacked, axis=0) > (len(arrays) / 2)).astype(int)
        pred_string = "".join(majority.astype(str))
        
        key = f"{model_name}|{complexity}|{DATA_SIZE_LABEL}|{feature_key}"
        return key, pred_string
    
    # Otherwise train from scratch on full data
    try:
        prep = get_preprocessor(feature_tuple)
        X_tr = prep.fit_transform(X_full_train)
        X_te = prep.transform(X_test_raw)
        
        model = BASE_MODEL_TYPES[model_name]()
        model = tune_model(model, complexity)
        
        if isinstance(model, (RandomForestClassifier, DecisionTreeClassifier)):
            X_tr = X_tr.toarray() if hasattr(X_tr, "toarray") else X_tr
            X_te = X_te.toarray() if hasattr(X_te, "toarray") else X_te
        
        model.fit(X_tr, y_full_train)
        preds = model.predict(X_te)
        pred_string = "".join(preds.astype(str))
        
        key = f"{model_name}|{complexity}|{DATA_SIZE_LABEL}|{feature_key}"
        return key, pred_string
    except Exception:
        return None

# --- MAIN ---
if __name__ == "__main__":
    start_time = time.time()
    
    print("Loading full training data...")
    X_full, y_full = load_full_train_data()
    
    print("Loading test split (for consistency with base cache)...")
    _, X_test, _, _ = load_original_test_split()
    
    print("Loading base cache (for Majority Vote)...")
    base_cache = load_base_cache()
    
    # Load checkpoint
    completed_keys = set()
    if os.path.exists(FULL_CHECKPOINT_FILE):
        print(f"Reading checkpoint {FULL_CHECKPOINT_FILE}...")
        try:
            with open(FULL_CHECKPOINT_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        completed_keys.add(data["k"])
        except Exception as e:
            print(f"Warning: Checkpoint corrupt ({e}). Starting fresh.")
            completed_keys = set()
    
    print(f"Resuming with {len(completed_keys)} already finished.")
    
    # Generate all feature combos
    all_combos = []
    for r in range(1, len(ALL_FEATURES) + 1):
        all_combos.extend(itertools.combinations(ALL_FEATURES, r))
    
    # Build task list: base models + majority vote, all complexities, all feature combos
    all_model_names = list(BASE_MODEL_TYPES.keys()) + [MAJORITY_MODEL_NAME]
    all_tasks = []
    for m in all_model_names:
        for c in range(1, 11):
            for f_combo in all_combos:
                fk = ",".join(sorted(f_combo))
                k = f"{m}|{c}|{DATA_SIZE_LABEL}|{fk}"
                if k not in completed_keys:
                    all_tasks.append((m, c, f_combo))
    
    total_remaining = len(all_tasks)
    print(f"Models remaining to train: {total_remaining}")
    
    # Process in batches
    if total_remaining > 0:
        with open(FULL_CHECKPOINT_FILE, "a") as f_out:
            for i in range(0, total_remaining, BATCH_SIZE):
                elapsed = time.time() - start_time
                if elapsed > MAX_RUNTIME_SEC:
                    print(f"⚠️ Time limit reached ({elapsed:.0f}s). Stopping gracefully.")
                    break
                
                batch_tasks = all_tasks[i : i + BATCH_SIZE]
                print(f"Processing Batch {i//BATCH_SIZE + 1} ({len(batch_tasks)} tasks)...")
                
                with Parallel(n_jobs=1, return_as="generator", verbose=0) as parallel:
                    for result in parallel(delayed(process_task)(t, X_full, y_full, X_test, base_cache) for t in batch_tasks):
                        if result is None:
                            continue
                        key, val = result
                        f_out.write(json.dumps({"k": key, "v": val}) + "\n")
                
                f_out.flush()
                os.fsync(f_out.fileno())
                gc.collect()
                print(f"Batch saved. Time elapsed: {time.time() - start_time:.0f}s")
    
    # Finalization
    final_keys = set()
    if os.path.exists(FULL_CHECKPOINT_FILE):
        with open(FULL_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    final_keys.add(json.loads(line)["k"])
    
    # Calculate total possible tasks
    # With 14 features: 2^14 - 1 = 16,383 feature combinations
    # Total = 16,383 combos * 5 models * 10 complexity = 819,150
    total_possible = len(all_combos) * len(all_model_names) * 10
    
    print(f"Status: {len(final_keys)} / {total_possible} complete.")
    
    if len(final_keys) >= total_possible:
        print("🎉 ALL TASKS COMPLETE. Building final cache file...")
        final_cache = {}
        with open(FULL_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    final_cache[entry["k"]] = entry["v"]
        
        with gzip.open(FULL_FINAL_FILE, "wt", encoding="UTF-8") as f:
            json.dump(final_cache, f)
        
        print(f"✅ Final Artifact Created: {FULL_FINAL_FILE}")
    else:
        print("⏳ Time limit reached. Please re-run this job to continue.")

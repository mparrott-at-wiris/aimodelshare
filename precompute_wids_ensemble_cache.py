import os
import json
import gzip
import itertools
import time
import gc
import pandas as pd
import numpy as np

from joblib import Parallel, delayed

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split

from sklearn.ensemble import (
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    ExtraTreesClassifier,
    VotingClassifier,
)

# --- CONFIGURATION (align with original; resumable and chunked) ---
MAX_ROWS_TEST = 4000              # to reproduce original X_TEST from precompute_wids_cache.py
MAX_RUNTIME_SEC = 3000            # stop after ~50 minutes
BATCH_SIZE = 400                  # tune for runtime/memory

ENSEMBLE_CHECKPOINT_FILE = "wids_ensemble_cache_checkpoint.jsonl"
ENSEMBLE_FINAL_FILE = "wids_prediction_cache_ensemble.json.gz"

# Specified columns for WiDS dataset
ALL_NUMERIC_COLS = ["floor_area", "year_built", "ELEVATION", "heating_degree_days", 
                    "cooling_degree_days", "january_min_temp", "july_max_temp", 
                    "avg_temp", "april_avg_temp", "october_avg_temp"]
ALL_CATEGORICAL_COLS = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
ALL_FEATURES = ALL_NUMERIC_COLS + ALL_CATEGORICAL_COLS

# Match original data sizes
DATA_SIZE_MAP = {"Small (20%)": 0.2, "Medium (60%)": 0.6, "Large (80%)": 0.8, "Full (100%)": 1.0}

# New model set with human-readable names consistent with original key style
NEW_MODEL_TYPES = {
    "The Gradient Booster": lambda: GradientBoostingClassifier(random_state=42),
    "The Histogram Booster": lambda: HistGradientBoostingClassifier(random_state=42),
    "The Extra Trees": lambda: ExtraTreesClassifier(random_state=42, n_jobs=-1),
    "The Voting Committee (GB+HGB+ET)": "VOTING"  # special case constructed per complexity
}

WIDS_DATASET_PATH = "datasets/recreated_wids_v2_ny_10k.csv"

# --- DATA PREP: replicate original X_TEST; training uses full data or sampled fractions per DATA_SIZE_MAP ---
def load_and_prepare(df: pd.DataFrame, max_rows: int | None):
    df = df.copy()

    # Optional sampling (only used to reproduce original X_TEST)
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

def load_full_data():
    df = pd.read_csv(WIDS_DATASET_PATH)
    X_full, y_full = load_and_prepare(df, max_rows=None)  # full dataset (no sampling)
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
    level = int(level)
    if isinstance(model, GradientBoostingClassifier):
        model.n_estimators = {1: 50, 2: 75, 3: 100, 4: 125, 5: 150, 6: 175, 7: 200, 8: 250, 9: 300, 10: 350}.get(level, 100)
        model.max_depth   = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3, 6: 4, 7: 4, 8: 4, 9: 5, 10: 5}.get(level, 3)
        model.learning_rate = {1: 0.2, 2: 0.15, 3: 0.12, 4: 0.1, 5: 0.08, 6: 0.07, 7: 0.06, 8: 0.05, 9: 0.05, 10: 0.04}.get(level, 0.1)
    elif isinstance(model, HistGradientBoostingClassifier):
        model.max_iter   = {1: 60, 2: 80, 3: 100, 4: 120, 5: 140, 6: 160, 7: 180, 8: 200, 9: 240, 10: 300}.get(level, 100)
        model.max_depth  = {1: 2, 2: 3, 3: 3, 4: 4, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 10: None}.get(level, None)
        model.learning_rate = {1: 0.2, 2: 0.15, 3: 0.12, 4: 0.1, 5: 0.08, 6: 0.07, 7: 0.06, 8: 0.05, 9: 0.05, 10: 0.04}.get(level, 0.1)
        model.l2_regularization = 0.0
    elif isinstance(model, ExtraTreesClassifier):
        model.n_estimators = {1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 350, 7: 400, 8: 450, 9: 500, 10: 600}.get(level, 300)
        model.max_depth    = {1: 10, 2: 12, 3: 14, 4: 16, 5: 18, 6: 20, 7: 24, 8: 28, 9: 32, 10: None}.get(level, None)
        model.min_samples_leaf = {1: 10, 2: 8, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 2, 9: 1, 10: 1}.get(level, 2)
    return model

# --- WORKER ---
def process_task(task, X_samples, Y_samples, X_test_raw):
    model_name, complexity, data_size, feature_tuple = task
    feature_key = ",".join(sorted(feature_tuple))
    key = f"{model_name}|{complexity}|{data_size}|{feature_key}"
    
    try:
        prep = get_preprocessor(feature_tuple)
        X_tr = prep.fit_transform(X_samples[data_size])
        X_te = prep.transform(X_test_raw)
        
        # Handle "VOTING" (meta-classifier)
        if NEW_MODEL_TYPES[model_name] == "VOTING":
            gb = GradientBoostingClassifier(random_state=42)
            hgb = HistGradientBoostingClassifier(random_state=42)
            et = ExtraTreesClassifier(random_state=42, n_jobs=-1)
            
            gb = tune_model(gb, complexity)
            hgb = tune_model(hgb, complexity)
            et = tune_model(et, complexity)
            
            model = VotingClassifier(
                estimators=[("gb", gb), ("hgb", hgb), ("et", et)],
                voting="hard"
            )
        else:
            model = NEW_MODEL_TYPES[model_name]()
            model = tune_model(model, complexity)
        
        # Convert sparse to dense for tree-based ensemble models if needed
        if isinstance(model, (GradientBoostingClassifier, ExtraTreesClassifier, VotingClassifier)):
            X_tr = X_tr.toarray() if hasattr(X_tr, "toarray") else X_tr
            X_te = X_te.toarray() if hasattr(X_te, "toarray") else X_te
        
        model.fit(X_tr, Y_samples[data_size])
        preds = model.predict(X_te)
        pred_string = "".join(preds.astype(str))
        
        return key, pred_string
    except Exception:
        return None

# --- MAIN ---
if __name__ == "__main__":
    start_time = time.time()
    
    print("Loading original test split...")
    X_train_raw, X_test_raw, y_train, y_test = load_original_test_split()
    
    print("Loading full data for 100% sample...")
    X_full, y_full = load_full_data()
    
    # Prepare data samples for each size
    X_samples, Y_samples = {}, {}
    for label, frac in DATA_SIZE_MAP.items():
        if frac == 1.0:
            X_samples[label], Y_samples[label] = X_full, y_full
        else:
            # Sample from the full dataset
            X_sample = X_full.sample(frac=frac, random_state=42)
            Y_samples[label] = y_full.loc[X_sample.index]
            X_samples[label] = X_sample
    
    # Load checkpoint
    completed_keys = set()
    if os.path.exists(ENSEMBLE_CHECKPOINT_FILE):
        print(f"Reading checkpoint {ENSEMBLE_CHECKPOINT_FILE}...")
        try:
            with open(ENSEMBLE_CHECKPOINT_FILE, "r") as f:
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
    
    # Build task list
    all_tasks = []
    for m in NEW_MODEL_TYPES:
        for c in range(1, 11):
            for d in DATA_SIZE_MAP:
                for f_combo in all_combos:
                    fk = ",".join(sorted(f_combo))
                    k = f"{m}|{c}|{d}|{fk}"
                    if k not in completed_keys:
                        all_tasks.append((m, c, d, f_combo))
    
    total_remaining = len(all_tasks)
    print(f"Models remaining to train: {total_remaining}")
    
    # Process in batches
    if total_remaining > 0:
        with open(ENSEMBLE_CHECKPOINT_FILE, "a") as f_out:
            for i in range(0, total_remaining, BATCH_SIZE):
                elapsed = time.time() - start_time
                if elapsed > MAX_RUNTIME_SEC:
                    print(f"⚠️ Time limit reached ({elapsed:.0f}s). Stopping gracefully.")
                    break
                
                batch_tasks = all_tasks[i : i + BATCH_SIZE]
                print(f"Processing Batch {i//BATCH_SIZE + 1} ({len(batch_tasks)} tasks)...")
                
                with Parallel(n_jobs=1, return_as="generator", verbose=0) as parallel:
                    for result in parallel(delayed(process_task)(t, X_samples, Y_samples, X_test_raw) for t in batch_tasks):
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
    if os.path.exists(ENSEMBLE_CHECKPOINT_FILE):
        with open(ENSEMBLE_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    final_keys.add(json.loads(line)["k"])
    
    # Calculate total possible tasks
    # With 14 features: all combinations from size 1 to 14 = sum(C(14,r) for r=1..14) = 2^14 - 1 = 16,383
    # Total = 16,383 combos * 4 models * 10 complexity * 4 data sizes = 2,621,120
    total_possible = len(all_combos) * len(NEW_MODEL_TYPES) * 10 * len(DATA_SIZE_MAP)
    
    print(f"Status: {len(final_keys)} / {total_possible} complete.")
    
    if len(final_keys) >= total_possible:
        print("🎉 ALL TASKS COMPLETE. Building final cache file...")
        final_cache = {}
        with open(ENSEMBLE_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    final_cache[entry["k"]] = entry["v"]
        
        with gzip.open(ENSEMBLE_FINAL_FILE, "wt", encoding="UTF-8") as f:
            json.dump(final_cache, f)
        
        print(f"✅ Final Artifact Created: {ENSEMBLE_FINAL_FILE}")
    else:
        print("⏳ Time limit reached. Please re-run this job to continue.")

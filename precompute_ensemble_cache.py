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
MAX_ROWS_TEST = 4000              # to reproduce original X_TEST from precompute_cache.py
MAX_RUNTIME_SEC = 3000            # stop after ~50 minutes
BATCH_SIZE = 400                  # tune for runtime/memory

ENSEMBLE_CHECKPOINT_FILE = "ensemble_cache_checkpoint.jsonl"
ENSEMBLE_FINAL_FILE = "prediction_cache_ensemble.json.gz"

ALL_NUMERIC_COLS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count",
    "days_b_screening_arrest", "age", "length_of_stay", "priors_count"
]
ALL_CATEGORICAL_COLS = ["race", "sex", "c_charge_degree", "c_charge_desc"]
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

COMPAS_URL = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"

# --- DATA PREP: replicate original X_TEST; training uses full data or sampled fractions per DATA_SIZE_MAP ---
def load_and_prepare(df: pd.DataFrame, max_rows: int | None):
    # Compute length_of_stay robustly
    try:
        df = df.copy()
        df['c_jail_in'] = pd.to_datetime(df['c_jail_in'])
        df['c_jail_out'] = pd.to_datetime(df['c_jail_out'])
        df['length_of_stay'] = (df['c_jail_out'] - df['c_jail_in']).dt.total_seconds() / (24 * 60 * 60)
    except Exception:
        df = df.copy()
        df['length_of_stay'] = np.nan

    # Optional sampling (only used to reproduce original X_TEST)
    if max_rows is not None and df.shape[0] > max_rows:
        df = df.sample(n=max_rows, random_state=42)

    # Map c_charge_desc to top-50 or OTHER (same logic as original)
    top_charges = df["c_charge_desc"].value_counts().head(50).index
    df["c_charge_desc"] = df["c_charge_desc"].apply(lambda x: x if pd.notna(x) and x in top_charges else "OTHER")

    # Ensure all required feature columns exist
    for col in ALL_FEATURES:
        if col not in df.columns:
            df[col] = np.nan

    X = df[ALL_FEATURES].copy()
    y = df["two_year_recid"].copy()
    return X, y

def load_original_test_split():
    df = pd.read_csv(COMPAS_URL)
    X, y = load_and_prepare(df, max_rows=MAX_ROWS_TEST)
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    return X_train_raw, X_test_raw, y_train, y_test

def load_full_data():
    df = pd.read_csv(COMPAS_URL)
    X_full, y_full = load_and_prepare(df, max_rows=None)  # full dataset (no sampling)
    return X_full, y_full

# --- PREPROCESSOR ---
def get_preprocessor(features):
    num = [f for f in features if f in ALL_NUMERIC_COLS]
    cat = [f for f in features if f in ALL_CATEGORICAL_COLS]
    steps = []
    if num:
        steps.append(("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ]), num))
    if cat:
        steps.append(("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))
        ]), cat))
    return ColumnTransformer(steps, remainder="drop")

def to_dense(X):
    return X.toarray() if hasattr(X, "toarray") else X

# --- COMPLEXITY TUNING (levels 1..10) ---
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

def build_voting_classifier(level: int):
    gb  = tune_model(GradientBoostingClassifier(random_state=42), level)
    hgb = tune_model(HistGradientBoostingClassifier(random_state=42), level)
    et  = tune_model(ExtraTreesClassifier(random_state=42, n_jobs=-1), level)
    vc  = VotingClassifier(
        estimators=[("GB", gb), ("HGB", hgb), ("ET", et)],
        voting="hard"
    )
    return vc

# --- TASK PROCESSOR ---
def process_task(task, X_full, y_full, X_test_raw):
    model_name, complexity, data_size_label, feature_tuple = task
    feature_key = ",".join(sorted(feature_tuple))
    key = f"{model_name}|{complexity}|{data_size_label}|{feature_key}"

    try:
        # Build training subset by data size
        frac = DATA_SIZE_MAP[data_size_label]
        if frac < 1.0:
            X_train = X_full.sample(frac=frac, random_state=42)
            y_train = y_full.loc[X_train.index]
        else:
            X_train = X_full
            y_train = y_full

        prep = get_preprocessor(feature_tuple)
        X_tr = prep.fit_transform(X_train)
        X_te = prep.transform(X_test_raw)

        # Tree-based & boosting models benefit from dense arrays
        X_tr = to_dense(X_tr)
        X_te = to_dense(X_te)

        if NEW_MODEL_TYPES[model_name] == "VOTING":
            model = build_voting_classifier(complexity)
        else:
            model = NEW_MODEL_TYPES[model_name]()
            model = tune_model(model, complexity)

        model.fit(X_tr, y_train)
        preds = model.predict(X_te)
        pred_string = "".join(preds.astype(str))

        return key, pred_string
    except Exception:
        return None

# --- MAIN EXECUTION (RESUMABLE) ---
if __name__ == "__main__":
    start_time = time.time()

    # 1) Load reproducible original X_TEST (from 4k-sampled dataset split)
    _, X_TEST_RAW, _, _ = load_original_test_split()

    # 2) Load full dataset for training base
    X_FULL, Y_FULL = load_full_data()

    # 3) Recover completed keys from ensemble checkpoint
    completed_keys = set()
    if os.path.exists(ENSEMBLE_CHECKPOINT_FILE):
        print(f"Reading ensemble checkpoint {ENSEMBLE_CHECKPOINT_FILE}...")
        try:
            with open(ENSEMBLE_CHECKPOINT_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        completed_keys.add(data["k"])
        except Exception as e:
            print(f"Warning: Ensemble checkpoint corrupt ({e}). Starting fresh.")
            completed_keys = set()
    print(f"Resuming with {len(completed_keys)} already finished (ensemble).")

    # 4) Generate tasks: every feature combination, complexity 1..10, for all new models, all data sizes
    print("Generating ensemble task list...")
    all_combos = []
    for r in range(1, len(ALL_FEATURES) + 1):
        all_combos.extend(itertools.combinations(ALL_FEATURES, r))

    all_tasks = []
    for m in NEW_MODEL_TYPES.keys():
        for c in range(1, 11):
            for d_label in DATA_SIZE_MAP.keys():
                for f_combo in all_combos:
                    fk = ",".join(sorted(f_combo))
                    k = f"{m}|{c}|{d_label}|{fk}"
                    if k not in completed_keys:
                        all_tasks.append((m, c, d_label, f_combo))

    total_remaining = len(all_tasks)
    print(f"Ensemble models remaining to train: {total_remaining}")

    # 5) Processing loop with checkpoint writes
    if total_remaining > 0:
        with open(ENSEMBLE_CHECKPOINT_FILE, "a") as f_out:
            for i in range(0, total_remaining, BATCH_SIZE):
                elapsed = time.time() - start_time
                if elapsed > MAX_RUNTIME_SEC:
                    print(f"⚠️ Time limit reached ({elapsed:.0f}s). Stopping gracefully to save progress.")
                    break

                batch_tasks = all_tasks[i : i + BATCH_SIZE]
                print(f"Processing Ensemble Batch {i//BATCH_SIZE + 1} ({len(batch_tasks)} tasks)...")

                # Serial mode to control memory footprint
                with Parallel(n_jobs=1, return_as="generator", verbose=0) as parallel:
                    for result in parallel(delayed(process_task)(t, X_FULL, Y_FULL, X_TEST_RAW) for t in batch_tasks):
                        if result is None:
                            continue
                        key, val = result
                        f_out.write(json.dumps({"k": key, "v": val}) + "\n")

                f_out.flush()
                os.fsync(f_out.fileno())
                gc.collect()
                print(f"Batch saved. Time elapsed: {time.time() - start_time:.0f}s")

    # 6) Finalization: build the ensemble final gzip only when everything is complete
    final_keys = set()
    if os.path.exists(ENSEMBLE_CHECKPOINT_FILE):
        with open(ENSEMBLE_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    final_keys.add(json.loads(line)["k"])

    total_features = len(ALL_FEATURES)
    total_combos = (2 ** total_features) - 1
    total_models = len(NEW_MODEL_TYPES)
    total_complexities = 10
    total_data_sizes = len(DATA_SIZE_MAP)
    total_expected = total_combos * total_models * total_complexities * total_data_sizes

    print(f"Ensemble Status: {len(final_keys)} / {total_expected} complete.")

    if len(final_keys) >= total_expected:
        print("🎉 ALL ENSEMBLE TASKS COMPLETE. Building final ensemble cache file...")

        final_cache = {}
        with open(ENSEMBLE_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    final_cache[entry["k"]] = entry["v"]

        with gzip.open(ENSEMBLE_FINAL_FILE, "wt", encoding="UTF-8") as f:
            json.dump(final_cache, f)

        print(f"✅ Final Ensemble Artifact Created: {ENSEMBLE_FINAL_FILE}")
    else:
        print("⏳ Time limit reached. Please re-run this job to continue.")

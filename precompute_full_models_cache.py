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

FULL_CHECKPOINT_FILE = "full_models_cache_checkpoint.jsonl"
FULL_FINAL_FILE = "prediction_cache_full_models.json.gz"

BASE_FINAL_FILE = "prediction_cache.json.gz"
BASE_CHECKPOINT_FILE = "cache_checkpoint.jsonl"

ALL_NUMERIC_COLS = ["juv_fel_count", "juv_misd_count", "juv_other_count", "days_b_screening_arrest", "age", "length_of_stay", "priors_count"]
ALL_CATEGORICAL_COLS = ["race", "sex", "c_charge_degree", "c_charge_desc"]
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

COMPAS_URL = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"

# --- DATA PREP (match original script for X_TEST) ---
def load_and_prepare(df: pd.DataFrame, max_rows: int | None):
    try:
        df = df.copy()
        df['c_jail_in'] = pd.to_datetime(df['c_jail_in'])
        df['c_jail_out'] = pd.to_datetime(df['c_jail_out'])
        df['length_of_stay'] = (df['c_jail_out'] - df['c_jail_in']).dt.total_seconds() / (24 * 60 * 60)
    except Exception:
        df = df.copy()
        df['length_of_stay'] = np.nan

    if max_rows is not None and df.shape[0] > max_rows:
        df = df.sample(n=max_rows, random_state=42)

    top_charges = df["c_charge_desc"].value_counts().head(50).index
    df["c_charge_desc"] = df["c_charge_desc"].apply(lambda x: x if pd.notna(x) and x in top_charges else "OTHER")

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

def load_full_train_data():
    df = pd.read_csv(COMPAS_URL)
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

def to_dense(X):
    return X.toarray() if hasattr(X, "toarray") else X

# --- ORIGINAL COMPLEXITY TUNING (levels 1..10) ---
def tune_model(model, level: int):
    level = int(level)
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

# --- BASE CACHE MERGE ---
def load_base_cache():
    if os.path.exists(BASE_FINAL_FILE):
        print(f"Reading base cache: {BASE_FINAL_FILE}")
        try:
            with gzip.open(BASE_FINAL_FILE, "rt", encoding="UTF-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to read {BASE_FINAL_FILE}: {e}")
            return {}
    elif os.path.exists(BASE_CHECKPOINT_FILE):
        print(f"Reconstructing base cache from checkpoint: {BASE_CHECKPOINT_FILE}")
        mapping = {}
        try:
            with open(BASE_CHECKPOINT_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        mapping[entry["k"]] = entry["v"]
            return mapping
        except Exception as e:
            print(f"Warning: Failed to reconstruct from checkpoint: {e}")
            return {}
    else:
        print("No prior base cache artifacts found. Starting full-models cache from scratch.")
        return {}

# --- ALLOWED FEATURE SETS (parse from app via AST; fallback to power set of ALL_FEATURES) ---
def _parse_available_features_from_source(path="aimodelshare/moral_compass/apps/model_building_app_en.py"):
    """
    Parse FEATURE_SET_ALL_OPTIONS directly from source file via AST.
    Returns a list of available feature names that users can select from.
    For example: ['age', 'race', 'sex', ...]
    
    Args:
        path: Relative path from repository root to the app source file.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "FEATURE_SET_ALL_OPTIONS":
                        # Evaluate the list literal
                        value = ast.literal_eval(node.value)
                        features = []
                        for opt in value:
                            # Each opt is a tuple like ("Display Name", "feature_key")
                            # We want the second element (the feature key)
                            if isinstance(opt, tuple) and len(opt) >= 2:
                                feature_key = str(opt[1])
                                # Validate that the feature exists in ALL_FEATURES
                                if feature_key in ALL_FEATURES:
                                    features.append(feature_key)
                        if features:
                            # Deduplicate
                            features = sorted(set(features))
                            print(f"Parsed {len(features)} available features from source.")
                            return features
        print("FEATURE_SET_ALL_OPTIONS not found in source; falling back to ALL_FEATURES.")
        return None
    except Exception as e:
        print(f"Warning: Failed to parse features from source ({e}); falling back to ALL_FEATURES.")
        return None

def get_allowed_feature_sets() -> list[tuple[str, ...]]:
    """
    Returns a list of sorted tuples representing ALL POSSIBLE COMBINATIONS of features
    that users can select in the app.
    
    First tries AST parsing of app source to get available features, then generates
    the power set (all combinations) of those features.
    Fallback: power set of ALL_FEATURES if parsing fails.
    
    This generates every combination users can select from FEATURE_SET_ALL_OPTIONS:
    - 10 features from FEATURE_SET_ALL_OPTIONS
    - 2^10 - 1 = 1023 combinations (excluding empty set)
    - Total tasks: 1023 combinations × 1 data size × 10 levels × 5 models = 51,150
    
    The +1 model is the majority vote model, which is derived from the 4 base model
    predictions without additional training.
    """
    # Try to parse available features from the app
    available_features = _parse_available_features_from_source()
    
    if available_features is not None and len(available_features) > 0:
        # Generate power set of available features
        all_combos = []
        for r in range(1, len(available_features) + 1):
            all_combos.extend(itertools.combinations(available_features, r))
        feature_sets = [tuple(sorted(c)) for c in all_combos]
        print(f"Generated {len(feature_sets)} feature combinations from {len(available_features)} available features.")
        return feature_sets
    
    # Fallback: full power set of ALL_FEATURES (excluding empty set)
    print("Using fallback: generating power set of ALL_FEATURES.")
    all_combos = []
    for r in range(1, len(ALL_FEATURES) + 1):
        all_combos.extend(itertools.combinations(ALL_FEATURES, r))
    return [tuple(sorted(c)) for c in all_combos]

# --- TASK PROCESSOR (base models only) ---
def process_task(task, X_full, y_full, X_test_raw):
    model_name, complexity, feature_tuple = task
    feature_key = ",".join(sorted(feature_tuple))
    key = f"{model_name}|{complexity}|{DATA_SIZE_LABEL}|{feature_key}"

    try:
        prep = get_preprocessor(feature_tuple)
        X_tr = prep.fit_transform(X_full)
        X_te = prep.transform(X_test_raw)

        # Densify for tree/kNN where beneficial
        X_tr = to_dense(X_tr)
        X_te = to_dense(X_te)

        model = BASE_MODEL_TYPES[model_name]()
        model = tune_model(model, complexity)
        model.fit(X_tr, y_full)
        preds = model.predict(X_te)

        pred_string = "".join(preds.astype(str))
        return key, pred_string
    except Exception:
        return None

# --- MAJORITY VOTE (derived from saved predictions, no training) ---
def compute_majority_string(pred_strings, tie_break="random", rng_seed=42):
    n_models = len(pred_strings)
    if n_models != 4:
        raise ValueError(f"Expected 4 base model predictions, got {n_models}")
    lengths = {len(s) for s in pred_strings}
    if len(lengths) != 1:
        raise ValueError("Prediction strings have mismatched lengths.")
    n_samples = lengths.pop()

    rng = np.random.default_rng(rng_seed)
    out_chars = []
    for i in range(n_samples):
        votes = [int(s[i]) for s in pred_strings]
        zeros = votes.count(0)
        ones = votes.count(1)
        if zeros > ones:
            out_chars.append("0")
        elif ones > zeros:
            out_chars.append("1")
        else:
            out_chars.append(str(rng.choice([0, 1])) if tie_break == "random" else "0")
    return "".join(out_chars)

def add_majority_votes_to_checkpoint():
    if not os.path.exists(FULL_CHECKPOINT_FILE):
        print("No full-models checkpoint present; skipping majority-vote derivation.")
        return

    entries = []
    with open(FULL_CHECKPOINT_FILE, "r") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    existing_keys = {e["k"] for e in entries}
    groups = {}  # (complexity, feature_key) -> {model_name: pred_string}

    for e in entries:
        k = e["k"]
        parts = k.split("|")
        if len(parts) != 4:
            continue
        model_name, complexity, data_size, feature_key = parts
        if data_size != DATA_SIZE_LABEL:
            continue
        if model_name == MAJORITY_MODEL_NAME:
            continue
        if model_name not in BASE_MODEL_TYPES:
            continue
        groups.setdefault((complexity, feature_key), {})[model_name] = e["v"]

    new_entries = []
    for (complexity, feature_key), model_map in groups.items():
        if len(model_map) != 4:
            continue
        maj_key = f"{MAJORITY_MODEL_NAME}|{complexity}|{DATA_SIZE_LABEL}|{feature_key}"
        if maj_key in existing_keys:
            continue

        pred_strings = [
            model_map["The Balanced Generalist"],
            model_map["The Rule-Maker"],
            model_map["The Deep Pattern-Finder"],
            model_map["The 'Nearest Neighbor'"],
        ]
        maj_val = compute_majority_string(pred_strings, tie_break="random", rng_seed=42)
        new_entries.append({"k": maj_key, "v": maj_val})

    if not new_entries:
        print("No new majority-vote entries to add.")
        return

    with open(FULL_CHECKPOINT_FILE, "a") as f_out:
        for e in new_entries:
            f_out.write(json.dumps(e) + "\n")
    print(f"Added {len(new_entries)} majority-vote entries to checkpoint.")

# --- MAIN EXECUTION (RESUMABLE) ---
if __name__ == "__main__":
    start_time = time.time()

    # 1) Load reproducible original X_TEST
    _, X_TEST_RAW, _, _ = load_original_test_split()

    # 2) Load full training data (no sampling)
    X_FULL, Y_FULL = load_full_train_data()

    # 3) Recover completed keys from full-models checkpoint
    completed_keys = set()
    if os.path.exists(FULL_CHECKPOINT_FILE):
        print(f"Reading full-models checkpoint {FULL_CHECKPOINT_FILE}...")
        try:
            with open(FULL_CHECKPOINT_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        completed_keys.add(data["k"])
        except Exception as e:
            print(f"Warning: Full-models checkpoint corrupt ({e}). Starting fresh.")
            completed_keys = set()
    print(f"Resuming with {len(completed_keys)} already finished (full-models).")

    # 4) Generate tasks restricted to app feature sets (fallback to power set)
    allowed_feature_sets = get_allowed_feature_sets()

    all_tasks = []
    for feature_tuple in allowed_feature_sets:
        fk = ",".join(sorted(feature_tuple))
        for model_name in BASE_MODEL_TYPES.keys():
            for c in range(1, 11):
                k = f"{model_name}|{c}|{DATA_SIZE_LABEL}|{fk}"
                if k not in completed_keys:
                    all_tasks.append((model_name, c, feature_tuple))

    total_remaining = len(all_tasks)
    print(f"Full-dataset base-models remaining to train (restricted to app sets): {total_remaining}")

    # 5) Processing loop with checkpoint writes
    if total_remaining > 0:
        with open(FULL_CHECKPOINT_FILE, "a") as f_out:
            for i in range(0, total_remaining, BATCH_SIZE):
                elapsed = time.time() - start_time
                if elapsed > MAX_RUNTIME_SEC:
                    print(f"⚠️ Time limit reached ({elapsed:.0f}s). Stopping gracefully to save progress.")
                    break

                batch_tasks = all_tasks[i : i + BATCH_SIZE]
                print(f"Processing Full-Models Batch {i//BATCH_SIZE + 1} ({len(batch_tasks)} tasks)...")

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

    # 6) Derive majority-vote entries from saved base predictions (fast, no training)
    add_majority_votes_to_checkpoint()

    # 7) Finalization: build the combined final gzip only when everything is complete
    final_keys = set()
    if os.path.exists(FULL_CHECKPOINT_FILE):
        with open(FULL_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    final_keys.add(json.loads(line)["k"])

    # Expected total = (#allowed_sets) × (10 complexities) × (4 base models + 1 majority vote)
    total_allowed_sets = len(allowed_feature_sets)
    total_complexities = 10
    total_models = len(BASE_MODEL_TYPES) + 1  # +1 for majority vote
    total_expected = total_allowed_sets * total_complexities * total_models

    print(f"Full-Models Status (restricted): {len(final_keys)} / {total_expected} complete.")

    if len(final_keys) >= total_expected:
        print("🎉 ALL FULL-MODELS TASKS COMPLETE. Building final cache file...")

        merged = load_base_cache()
        with open(FULL_CHECKPOINT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    merged[entry["k"]] = entry["v"]

        with gzip.open(FULL_FINAL_FILE, "wt", encoding="UTF-8") as f:
            json.dump(merged, f)

        print(f"✅ Final Full-Models Artifact Created: {FULL_FINAL_FILE}")
    else:
        print("⏳ Time limit reached. Please re-run this job to continue.")

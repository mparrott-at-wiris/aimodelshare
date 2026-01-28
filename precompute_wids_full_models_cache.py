import os
import json
import gzip
import argparse
import pandas as pd
import numpy as np

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
MAX_ROWS_TEST = 4000
ALL_NUMERIC_COLS = ["floor_area", "year_built", "ELEVATION", "heating_degree_days", 
                    "cooling_degree_days", "january_min_temp", "july_max_temp", 
                    "avg_temp", "april_avg_temp", "october_avg_temp"]
ALL_CATEGORICAL_COLS = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
ALL_FEATURES = ALL_NUMERIC_COLS + ALL_CATEGORICAL_COLS

DATA_SIZE_LABEL = "Full (100%)"
MAJORITY_MODEL_NAME = "The Majority Vote"

BASE_FINAL_FILE = "wids_prediction_cache.json.gz"
WIDS_DATASET_PATH = "datasets/recreated_wids_v2_ny_10k.csv"

# Model Definitions
BASE_MODEL_TYPES = {
    "The Balanced Generalist": lambda: LogisticRegression(max_iter=200, random_state=42, class_weight="balanced"),
    "The Rule-Maker": lambda: DecisionTreeClassifier(random_state=42, class_weight="balanced"),
    "The 'Nearest Neighbor'": lambda: KNeighborsClassifier(),
    "The Deep Pattern-Finder": lambda: RandomForestClassifier(random_state=42, class_weight="balanced"),
}

# --- DATA LOADING ---
def load_and_prepare(df: pd.DataFrame, max_rows: int | None):
    df = df.copy()
    if max_rows is not None and df.shape[0] > max_rows:
        df = df.sample(n=max_rows, random_state=42)
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

def load_full_train_data_excluding_test():
    df_for_test_indices = pd.read_csv(WIDS_DATASET_PATH)
    X_sampled, y_sampled = load_and_prepare(df_for_test_indices, max_rows=MAX_ROWS_TEST)
    _, X_test_for_indices, _, _ = train_test_split(
        X_sampled, y_sampled, test_size=0.25, random_state=42, stratify=y_sampled
    )
    test_indices = set(X_test_for_indices.index)
    
    df_full = pd.read_csv(WIDS_DATASET_PATH)
    X_full, y_full = load_and_prepare(df_full, max_rows=None)
    
    mask = ~X_full.index.isin(test_indices)
    return X_full[mask], y_full[mask]

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

def load_base_cache():
    if os.path.exists(BASE_FINAL_FILE):
        print(f"Loading base cache from {BASE_FINAL_FILE}...")
        with gzip.open(BASE_FINAL_FILE, "rt", encoding="UTF-8") as f:
            return json.load(f)
    print("⚠️ No base cache found. Majority Vote may fail.")
    return {}

def process_task(task_key, X_full_train, y_full_train, X_test_raw, base_cache):
    # Parse key: "Model|Complexity|DataSize|Features"
    try:
        parts = task_key.split("|")
        model_name = parts[0]
        complexity = int(parts[1])
        # data_size is parts[2] (ignored, we know it's full)
        features = parts[3].split(",")
    except:
        return None

    # Majority Vote Logic
    if model_name == MAJORITY_MODEL_NAME:
        base_pred_strings = []
        for base_model_name in BASE_MODEL_TYPES.keys():
            # Look for pre-computed Full models in the base cache
            # Note: This relies on the Base Cache having "Full" runs. 
            # If the base cache only has Partial runs, this will return None.
            base_key = f"{base_model_name}|{complexity}|{DATA_SIZE_LABEL}|{parts[3]}"
            if base_key in base_cache:
                base_pred_strings.append(base_cache[base_key])
        
        if len(base_pred_strings) == 0:
            return None 
        
        arrays = [np.array(list(s), dtype=int) for s in base_pred_strings]
        stacked = np.stack(arrays, axis=0)
        majority = (np.sum(stacked, axis=0) > (len(arrays) / 2)).astype(int)
        pred_string = "".join(majority.astype(str))
        return task_key, pred_string

    # Standard Training Logic
    try:
        prep = get_preprocessor(features)
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
        
        return task_key, pred_string
    except Exception as e:
        # print(f"Error on {task_key}: {e}") # Optional debug
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True, help="JSON file containing list of tasks")
    args = parser.parse_args()

    # Load Data
    X_full, y_full = load_full_train_data_excluding_test()
    _, X_test, _, _ = load_original_test_split()
    base_cache = load_base_cache()

    # Load Tasks
    with open(args.task_file, "r") as f:
        tasks = json.load(f)
    
    print(f"Processing {len(tasks)} tasks from {args.task_file}...")

    # Output file
    output_file = "wids_cache_checkpoint.jsonl.gz"

    # Process sequentially (the parallelism is at the Job level, not script level)
    # We use a simple loop because we are already running inside a parallel worker
    with gzip.open(output_file, "wt", encoding="UTF-8") as f_out:
        for i, task_key in enumerate(tasks):
            result = process_task(task_key, X_full, y_full, X_test, base_cache)
            if result:
                k, v = result
                f_out.write(json.dumps({"k": k, "v": v}) + "\n")
            
            if i % 100 == 0:
                print(f"Progress: {i}/{len(tasks)}")

    print(f"Chunk processing complete. Saved to {output_file}")

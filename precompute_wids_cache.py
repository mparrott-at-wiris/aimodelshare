import os
import argparse
import json
import gzip
import itertools
import time
import gc
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

# --- 1. CONFIGURATION ---
MAX_ROWS = 4000
# Time limit for execution: 20,000 seconds leaves some buffer before workflow timeout
MAX_RUNTIME_SEC = 20000
BATCH_SIZE = 500
CHECKPOINT_FILE = "wids_cache_checkpoint.jsonl.gz"
FINAL_FILE = "wids_prediction_cache.json.gz"

# Define columns and data configuration
ALL_NUMERIC_COLS = [
    "floor_area", "year_built", "ELEVATION", "heating_degree_days",
    "cooling_degree_days", "january_min_temp", "july_max_temp",
    "avg_temp", "april_avg_temp", "october_avg_temp"
]
ALL_CATEGORICAL_COLS = ["facility_type", "building_class", "State_Factor", "Year_Factor"]
ALL_FEATURES = ALL_NUMERIC_COLS + ALL_CATEGORICAL_COLS

DATA_SIZE_MAP = {
    "Small (20%)": 0.2,
    "Medium (60%)": 0.6,
    "Large (80%)": 0.8,
    "Full (100%)": 1.0
}

MODEL_TYPES = {
    "The Balanced Generalist": lambda: LogisticRegression(max_iter=200, random_state=42, class_weight="balanced"),
    "The Rule-Maker": lambda: DecisionTreeClassifier(random_state=42, class_weight="balanced"),
    "The 'Nearest Neighbor'": lambda: KNeighborsClassifier(),
    "The Deep Pattern-Finder": lambda: RandomForestClassifier(random_state=42, class_weight="balanced"),
}

import psutil

def log_resource_usage(batch_number):
    memory = psutil.virtual_memory()
    print(f"Batch {batch_number} memory usage: {memory.percent}% used, {memory.available // (1024 * 1024)} MB available")
    
# --- 2. DATA PREPARATION ---
def load_data():
    """Load WiDS dataset and prepare training/test splits."""
    print("Loading WiDS dataset...")
    dataset_path = "datasets/recreated_wids_v2_ny_10k.csv"
    df = pd.read_csv(dataset_path)

    if df.shape[0] > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42)

    for col in ALL_FEATURES:
        if col not in df.columns:
            df[col] = np.nan

    X = df[ALL_FEATURES].copy()
    y = df["high_energy_usage"].copy()
    print(f"Data Loaded. Shape: {X.shape}")
    return train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_data()

X_SAMPLES, Y_SAMPLES = {}, {}
for label, frac in DATA_SIZE_MAP.items():
    if frac == 1.0:
        X_SAMPLES[label], Y_SAMPLES[label] = X_TRAIN_RAW, Y_TRAIN
    else:
        X_SAMPLES[label] = X_TRAIN_RAW.sample(frac=frac, random_state=42)
        Y_SAMPLES[label] = Y_TRAIN.loc[X_SAMPLES[label].index]

# --- 3. WORKER FUNCTIONS ---
def get_preprocessor(features):
    """
    Create a ColumnTransformer for selected numeric and categorical features.
    """
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

def tune_model(model, level):
    """Adjust model hyperparameters based on level."""
    level = int(level)
    if isinstance(model, LogisticRegression):
        model.C = {1: 0.01, 2: 0.025, 3: 0.05, 4: 0.1, 5: 0.25, 6: 0.5,
                   7: 1.0, 8: 2.0, 9: 5.0, 10: 10.0}.get(level, 1.0)
    elif isinstance(model, RandomForestClassifier):
        model.n_estimators = {1: 10, 2: 12, 3: 15, 4: 18, 5: 20, 6: 22,
                              7: 25, 8: 28, 9: 30, 10: 30}.get(level, 20)
        model.max_depth = level * 2 + 2 if level < 9 else None
    elif isinstance(model, DecisionTreeClassifier):
        model.max_depth = level + 1 if level < 10 else None
    elif isinstance(model, KNeighborsClassifier):
        model.n_neighbors = {1: 100, 2: 75, 3: 60, 4: 50, 5: 40, 6: 30,
                             7: 25, 8: 15, 9: 7, 10: 3}.get(level, 25)
    return model

def process(task):
    """Process an individual task."""
    model_name, complexity, data_size, feature_tuple = task
    feature_key = ",".join(sorted(feature_tuple))
    key = f"{model_name}|{complexity}|{data_size}|{feature_key}"
    try:
        preprocessor = get_preprocessor(feature_tuple)
        X_train = preprocessor.fit_transform(X_SAMPLES[data_size])
        X_test = preprocessor.transform(X_TEST_RAW)

        model = MODEL_TYPES[model_name]()
        model = tune_model(model, complexity)

        if isinstance(model, (RandomForestClassifier, DecisionTreeClassifier)):
            # Handle sparse to dense conversion
            X_train = X_train.toarray() if hasattr(X_train, "toarray") else X_train
            X_test = X_test.toarray() if hasattr(X_test, "toarray") else X_test

        model.fit(X_train, Y_SAMPLES[data_size])
        predictions = model.predict(X_test)
        pred_string = "".join(predictions.astype(str))
        return key, pred_string

    except Exception as e:
        print(f"⚠️ Error processing task {key}: {e}")
        return None

# --- 4. MAIN EXECUTION ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True, help="Path to the task JSON file")
    args = parser.parse_args()

    # Load tasks for this job chunk
    with open(args.task_file, "r") as f:
        task_chunk = json.load(f)

    # Load checkpoint if available
    completed_keys = set()
    if os.path.exists(CHECKPOINT_FILE):
        print(f"Resuming from checkpoint: {CHECKPOINT_FILE}")
        with gzip.open(CHECKPOINT_FILE, "rt", encoding="UTF-8") as f:
            for line in f:
                data = json.loads(line.strip())
                completed_keys.add(data["k"])

    all_tasks = []
    for task in task_chunk:
        if task not in completed_keys:
            model, complexity, data_size, feature_str = task.split("|")
            feature_tuple = feature_str.split(",")
            all_tasks.append((model, int(complexity), data_size, feature_tuple))

    print(f"Remaining tasks to process: {len(all_tasks)}")
    start_time = time.time()

    # Process tasks in batches
    if all_tasks:
        with gzip.open(CHECKPOINT_FILE, "at", encoding="UTF-8") as f_out:
            for i in range(0, len(all_tasks), BATCH_SIZE):
                batch = all_tasks[i:i+BATCH_SIZE]
                elapsed = time.time() - start_time
                if elapsed > MAX_RUNTIME_SEC:
                    print(f"⏰ Time limit reached. Ending gracefully.")
                    break

                results = Parallel(n_jobs=1)(delayed(process)(task) for task in batch)
                for result in results:
                    if result is None:
                        continue
                    f_out.write(json.dumps({"k": result[0], "v": result[1]}) + "\n")
                f_out.flush()
                gc.collect()
                print(f"Processed batch {i // BATCH_SIZE + 1}. Time elapsed: {elapsed:.2f}s.")
                # Calculate the total number of remaining tasks
                total_remaining = len(all_tasks)
                print(f"Models remaining to train: {total_remaining}")
                for i in range(0, total_remaining, BATCH_SIZE):
                    batch_tasks = all_tasks[i:i + BATCH_SIZE]
                    elapsed = time.time() - start_time
                    log_resource_usage(i // BATCH_SIZE + 1)

    print("✅ Task processing complete.")

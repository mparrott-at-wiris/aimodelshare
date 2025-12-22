import os
import json
import gzip
import itertools
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
# Reduce batch size to ensure regular memory cleanup
BATCH_SIZE = 20000 

ALL_NUMERIC_COLS = ["juv_fel_count", "juv_misd_count", "juv_other_count", "days_b_screening_arrest", "age", "length_of_stay", "priors_count"]
ALL_CATEGORICAL_COLS = ["race", "sex", "c_charge_degree", "c_charge_desc"]
ALL_FEATURES = ALL_NUMERIC_COLS + ALL_CATEGORICAL_COLS

DATA_SIZE_MAP = {"Small (20%)": 0.2, "Medium (60%)": 0.6, "Large (80%)": 0.8, "Full (100%)": 1.0}

# OPTIMIZATION: Reduced iterations/estimators for build speed
# (Users won't notice the difference between 20 and 100 trees in this educational context)
MODEL_TYPES = {
    "The Balanced Generalist": lambda: LogisticRegression(max_iter=200, random_state=42, class_weight="balanced"),
    "The Rule-Maker": lambda: DecisionTreeClassifier(random_state=42, class_weight="balanced"),
    "The 'Nearest Neighbor'": lambda: KNeighborsClassifier(),
    "The Deep Pattern-Finder": lambda: RandomForestClassifier(random_state=42, class_weight="balanced")
}

# --- 2. DATA PREP ---
def load_data():
    print("Loading dataset...")
    url = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"
    try:
        df = pd.read_csv(url)
        df['c_jail_in'] = pd.to_datetime(df['c_jail_in'])
        df['c_jail_out'] = pd.to_datetime(df['c_jail_out'])
        df['length_of_stay'] = (df['c_jail_out'] - df['c_jail_in']).dt.total_seconds() / (24 * 60 * 60)
    except:
        df = pd.read_csv(url)
        df['length_of_stay'] = np.nan

    if df.shape[0] > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42)

    top_charges = df["c_charge_desc"].value_counts().head(50).index
    df["c_charge_desc"] = df["c_charge_desc"].apply(lambda x: x if pd.notna(x) and x in top_charges else "OTHER")

    for col in ALL_FEATURES:
        if col not in df.columns: df[col] = np.nan

    X = df[ALL_FEATURES].copy()
    y = df["two_year_recid"].copy()
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

# --- 3. WORKER HELPERS ---
def get_preprocessor(features):
    num = [f for f in features if f in ALL_NUMERIC_COLS]
    cat = [f for f in features if f in ALL_CATEGORICAL_COLS]
    steps = []
    if num: steps.append(("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), num))
    if cat: steps.append(("cat", Pipeline([("imputer", SimpleImputer(strategy="constant", fill_value="missing")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))]), cat))
    return ColumnTransformer(steps, remainder="drop")

def tune_model(model, level):
    level = int(level)
    if isinstance(model, LogisticRegression):
        model.C = {1: 0.01, 2: 0.025, 3: 0.05, 4: 0.1, 5: 0.25, 6: 0.5, 7: 1.0, 8: 2.0, 9: 5.0, 10: 10.0}.get(level, 1.0)
    elif isinstance(model, RandomForestClassifier):
        # Cap at 30 trees for speed/memory safety during build
        model.n_estimators = {1: 10, 2: 12, 3: 15, 4: 18, 5: 20, 6: 22, 7: 25, 8: 28, 9: 30, 10: 30}.get(level, 20)
        model.max_depth = level * 2 + 2 if level < 9 else None
    elif isinstance(model, DecisionTreeClassifier):
        model.max_depth = level + 1 if level < 10 else None
    elif isinstance(model, KNeighborsClassifier):
        model.n_neighbors = {1: 100, 2: 75, 3: 60, 4: 50, 5: 40, 6: 30, 7: 25, 8: 15, 9: 7, 10: 3}.get(level, 25)
    return model

def process(task):
    model_name, complexity, data_size, feature_tuple = task
    feature_key = ",".join(sorted(feature_tuple))
    key = f"{model_name}|{complexity}|{data_size}|{feature_key}"
    
    try:
        prep = get_preprocessor(feature_tuple)
        X_tr = prep.fit_transform(X_SAMPLES[data_size])
        X_te = prep.transform(X_TEST_RAW)
        
        model = MODEL_TYPES[model_name]()
        model = tune_model(model, complexity)
        
        if isinstance(model, (RandomForestClassifier, DecisionTreeClassifier)):
            X_tr = X_tr.toarray() if hasattr(X_tr, "toarray") else X_tr
            X_te = X_te.toarray() if hasattr(X_te, "toarray") else X_te
            
        model.fit(X_tr, Y_SAMPLES[data_size])
        
        preds = model.predict(X_te)
        # Store as lightweight string "010101"
        pred_string = "".join(preds.astype(str))
        
        return key, pred_string
    except Exception:
        return None

# --- 4. EXECUTION (BATCHED) ---
if __name__ == "__main__":
    print(f"Generating feature combinations for {len(ALL_FEATURES)} features...")
    
    all_combos = []
    for r in range(1, len(ALL_FEATURES) + 1):
        all_combos.extend(itertools.combinations(ALL_FEATURES, r))
    
    print(f"Total Feature Combos: {len(all_combos)}")
    
    tasks = []
    for m in MODEL_TYPES:
        for c in range(1, 11):
            for d in DATA_SIZE_MAP:
                for f_combo in all_combos:
                    tasks.append((m, c, d, f_combo))
                    
    total_tasks = len(tasks)
    print(f"Total Models: {total_tasks}")
    
    outfile = "prediction_cache.json.gz"
    print(f"Streaming results to {outfile} in batches of {BATCH_SIZE}...")

    with gzip.open(outfile, "wt", encoding="UTF-8") as f:
        f.write("{") 
        
        is_first_overall = True
        
        # BATCHED LOOP
        # We iterate through the tasks in chunks. 
        # This allows us to close the Parallel pool repeatedly, freeing memory leaks.
        for i in range(0, total_tasks, BATCH_SIZE):
            batch_tasks = tasks[i : i + BATCH_SIZE]
            print(f"Processing Batch {i//BATCH_SIZE + 1} ({len(batch_tasks)} tasks)...")
            
            # Start a FRESH pool for every batch
            # n_jobs=2 is safe for GitHub runners (7GB RAM limit)
            with Parallel(n_jobs=2, return_as="generator", verbose=0) as parallel:
                for result in parallel(delayed(process)(t) for t in batch_tasks):
                    if result is None: continue
                    
                    key, val = result
                    
                    if not is_first_overall:
                        f.write(",")
                    else:
                        is_first_overall = False
                    
                    f.write(f"{json.dumps(key)}:{json.dumps(val)}")
            
            # Force garbage collection between batches
            gc.collect()
            print(f"Batch {i//BATCH_SIZE + 1} Complete. RAM cleaned.")
        
        f.write("}") 

    size_mb = os.path.getsize(outfile) / (1024 * 1024)
    print(f"✅ DONE! Cache Size: {size_mb:.2f} MB")

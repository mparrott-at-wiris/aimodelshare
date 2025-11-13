"""
Model Building Game (Ètica en Joc) - Justice & Equity Challenge

This app teaches:
1. The experiment loop of iterative AI model development
2. How model parameters (type, complexity, data size, features) affect performance
3. Competition-driven improvement (individual & team leaderboards
4. Ethical awareness via controlled unlocking of sensitive features

Structure:
- Factory function `create_model_building_game_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_model_building_game_app()` launches it inline (for notebooks)

---
V23 Updates:
- (V23) **BUG FIX:** Removed the 'theme_mode="light"' argument from
        gr.Blocks() constructor, which was causing a TypeError in
        Gradio v5.49.1.
- (V22) Kept the explicit 'color' CSS properties from V22, which correctly
        fixes the dark mode readability issue.
- (V21-V9) Kept all V21-V9 optimizations and UI logic.
---
"""

import os
import time
import random
import requests
import contextlib
from io import StringIO

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
        "The 'aimodelshare' library is required. Install with: pip install aimodelshare aim-widgets"
    )

# -------------------------------------------------------------------------
# 1. Configuration
# -------------------------------------------------------------------------

MY_PLAYGROUND_ID = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"

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


# --- (V9) Feature groups for scaffolding (Weak -> Medium -> Strong) ---
FEATURE_SET_ALL_OPTIONS = [
    ("Juvenile Felony Count", "juv_fel_count"),
    ("Juvenile Misdemeanor Count", "juv_misd_count"),
    ("Other Juvenile Count", "juv_other_count"),
    ("Race", "race"),
    ("Sex", "sex"),
    ("Charge Severity (M/F)", "c_charge_degree"),
    ("Days Before Arrest", "days_b_screening_arrest"),
    ("Charge Description", "c_charge_desc"),
    ("Age", "age"),
    ("Length of Stay", "length_of_stay"),
    ("Prior Crimes Count", "priors_count"),
    ("Age Group", "age_cat"),
]
FEATURE_SET_GROUP_1_VALS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex",
    "c_charge_degree", "days_b_screening_arrest"
]
FEATURE_SET_GROUP_2_VALS = ["c_charge_desc"]
FEATURE_SET_GROUP_3_VALS = ["age", "length_of_stay", "priors_count", "age_cat"]
ALL_NUMERIC_COLS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count",
    "days_b_screening_arrest", "age", "length_of_stay", "priors_count"
]
ALL_CATEGORICAL_COLS = [
    "race", "sex", "c_charge_degree", "c_charge_desc", "age_cat"
]
DEFAULT_FEATURE_SET = FEATURE_SET_GROUP_1_VALS
# --- END V9 UPDATE ---


# --- (V6) Data Size config ---
DATA_SIZE_MAP = {
    "Small (20%)": 0.2,
    "Medium (60%)": 0.6,
    "Large (80%)": 0.8,
    "Full (100%)": 1.0
}
DEFAULT_DATA_SIZE = "Small (20%)"


MAX_ROWS = 4000
TOP_N_CHARGE_CATEGORICAL = 50
np.random.seed(42)

# Global state containers (populated during initialization)
playground = None
X_TRAIN_RAW = None # Keep this for 100%
X_TEST_RAW = None
Y_TRAIN = None
Y_TEST = None
# (V10) Add a container for our pre-sampled data
X_TRAIN_SAMPLES_MAP = {}
Y_TRAIN_SAMPLES_MAP = {}

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

def load_and_prep_data():
    """
    (V10) Load, sample, and prepare raw COMPAS dataset.
    NOW PRE-SAMPLES ALL DATA SIZES.
    """
    url = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"
    
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
    
    # (V10) Pre-sample all data sizes
    global X_TRAIN_SAMPLES_MAP, Y_TRAIN_SAMPLES_MAP
    
    X_TRAIN_SAMPLES_MAP["Full (100%)"] = X_train_raw
    Y_TRAIN_SAMPLES_MAP["Full (100%)"] = y_train
    
    for label, frac in DATA_SIZE_MAP.items():
        if frac < 1.0:
            X_train_sampled = X_train_raw.sample(frac=frac, random_state=42)
            y_train_sampled = y_train.loc[X_train_sampled.index]
            X_TRAIN_SAMPLES_MAP[label] = X_train_sampled
            Y_TRAIN_SAMPLES_MAP[label] = y_train_sampled
            
    print(f"Pre-sampling complete. {len(X_TRAIN_SAMPLES_MAP)} data sizes cached.")
    
    return X_train_raw, X_test_raw, y_train, y_test

def tune_model_complexity(model, level):
    """Map a simple 1–5 slider value to model hyperparameters."""
    level = int(level)
    if isinstance(model, LogisticRegression):
        c_map = {1: 0.1, 2: 0.5, 3: 1.0, 4: 5.0, 5: 10.0}
        model.C = c_map.get(level, 1.0)
    elif isinstance(model, RandomForestClassifier):
        depth_map = {1: 3, 2: 5, 3: 10, 4: 20, 5: None}
        est_map = {1: 20, 2: 40, 3: 50, 4: 100, 5: 150}
        model.max_depth = depth_map.get(level, 10)
        model.n_estimators = est_map.get(level, 50)
    elif isinstance(model, DecisionTreeClassifier):
        depth_map = {1: 2, 2: 4, 3: 6, 4: 10, 5: None}
        model.max_depth = depth_map.get(level, 6)
    elif isinstance(model, KNeighborsClassifier):
        k_map = {1: 50, 2: 25, 3: 10, 4: 5, 5: 3}
        model.n_neighbors = k_map.get(level, 10)
    return model

# --- (V17) New Helper Functions for HTML Generation ---

def _build_kpi_card_html(new_score, last_score, new_rank, last_rank, submission_count):
    """Generates the HTML for the KPI feedback card."""
    
    # 1. Handle First Submission
    if submission_count == 0:
        title = "🎉 First Model Submitted!"
        acc_color = "#16a34a" # green
        acc_text = f"{new_score:.4f}"
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
            acc_text = f"{new_score:.4f}"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>No Change (↔)</p>"
            border_color = acc_color
        elif score_diff > 0:
            title = "✅ Submission Successful!"
            acc_color = "#16a34a" # green
            acc_text = f"{new_score:.4f}"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>+{score_diff:.4f} (⬆️)</p>"
            border_color = acc_color
        else:
            title = "📉 Score Dropped"
            acc_color = "#ef4444" # red
            acc_text = f"{new_score:.4f}"
            acc_diff_html = f"<p style='font-size: 1.5rem; font-weight: 600; color: {acc_color}; margin:0;'>{score_diff:.4f} (⬇️)</p>"
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
            <!-- Accuracy KPI -->
            <div class='kpi-metric-box'>
                <p class='kpi-label'>New Accuracy</p>
                <p class='kpi-score' style='color: {acc_color};'>{acc_text}</p>
                {acc_diff_html}
            </div>
            <!-- Rank KPI -->
            <div class='kpi-metric-box'>
                <p class='kpi-label'>Your Rank</p>
                <p class='kpi-score' style='color: {rank_color};'>{rank_text}</p>
                {rank_diff_html}
            </div>
        </div>
    </div>
    """

def _build_team_html(team_summary_df, team_name):
    """Generates the HTML for the team leaderboard."""
    if team_summary_df is None or team_summary_df.empty:
        return "<p style='text-align:center; color:#6b7280; padding-top:20px;'>No team submissions yet.</p>"

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
        is_user_team = row["Team"] == team_name
        row_class = "class='user-row-highlight'" if is_user_team else ""
        body += f"""
        <tr {row_class}>
            <td>{index}</td>
            <td>{row['Team']}</td>
            <td>{row['Best_Score']:.4f}</td>
            <td>{row['Avg_Score']:.4f}</td>
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
            <td>{row['Best_Score']:.4f}</td>
            <td>{row['Submissions']}</td>
        </tr>
        """
        
    footer = "</tbody></table>"
    return header + body + footer

# --- (V17) End Helper Functions ---


def generate_competitive_summary(leaderboard_df, team_name, username, last_submission_score, last_rank, submission_count):
    """
    (V17) Build summaries, HTML, and KPI card.
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
    team_html = _build_team_html(team_summary_df, team_name)
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
    """(V9) Returns rank gating settings."""
    
    def get_choices_for_rank(rank):
        if rank == 0: # Trainee
            return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in FEATURE_SET_GROUP_1_VALS]
        if rank == 1: # Junior
            return [opt for opt in FEATURE_SET_ALL_OPTIONS if opt[1] in (FEATURE_SET_GROUP_1_VALS + FEATURE_SET_GROUP_2_VALS)]
        return FEATURE_SET_ALL_OPTIONS # Senior+
    
    if submission_count == 0:
        return {
            "rank_message": "### 🧑‍🎓 Rank: Trainee Engineer\n<p style='font-size:16px; line-height:1.4;'>Your controls are limited. For your first submission, just use the defaults and click the big '🔬 Build & Submit Model' button below!</p>",
            "model_choices": ["The Balanced Generalist"],
            "model_value": "The Balanced Generalist",
            "model_interactive": False,
            "complexity_max": 2,
            "complexity_value": 2,
            "feature_set_choices": get_choices_for_rank(0),
            "feature_set_value": FEATURE_SET_GROUP_1_VALS,
            "feature_set_interactive": False,
            "data_size_choices": ["Small (20%)"],
            "data_size_value": "Small (20%)",
            "data_size_interactive": False,
        }
    elif submission_count == 1:
        return {
            "rank_message": "### 🎉 Rank Up! Junior Engineer\nNew models, data sizes, and data ingredients unlocked!",
            "model_choices": ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"],
            "model_value": current_model if current_model in ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"] else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 4,
            "complexity_value": min(current_complexity, 4),
            "feature_set_choices": get_choices_for_rank(1),
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)"],
            "data_size_value": current_data_size if current_data_size in ["Small (20%)", "Medium (60%)"] else "Small (20%)",
            "data_size_interactive": True,
        }
    elif submission_count == 2:
        return {
            "rank_message": "### 🌟 Rank Up! Senior Engineer\n<p style='font-size:16px; line-height:1.4;'>**Strongest Data Ingredients Unlocked!** The most powerful predictors (like 'Age' and 'Prior Crimes Count') are now available in your list. These will likely boost your accuracy, but remember they often carry the most societal bias.</p>",
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Deep Pattern-Finder",
            "model_interactive": True,
            "complexity_max": 5,
            "complexity_value": min(current_complexity, 5),
            "feature_set_choices": get_choices_for_rank(2),
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)",
            "data_size_interactive": True,
        }
    else:
        return {
            "rank_message": "### 👑 Rank: Lead Engineer\nAll tools unlocked — optimize freely!",
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 5,
            "complexity_value": current_complexity,
            "feature_set_choices": get_choices_for_rank(3),
            "feature_set_value": current_feature_set,
            "feature_set_interactive": True,
            "data_size_choices": ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"],
            "data_size_value": current_data_size if current_data_size in DATA_SIZE_MAP else "Small (20%)",
            "data_size_interactive": True,
        }

# (V10) Find components by name to yield updates
submit_button = None
submission_feedback_display = None
team_leaderboard_display = None
individual_leaderboard_display = None
last_submission_score_state = None # (V17) Renamed
last_rank_state = None # (V17) New
submission_count_state = None
rank_message_display = None
model_type_radio = None
complexity_slider = None
feature_set_checkbox = None
data_size_radio = None

def run_experiment(
    model_name_key,
    complexity_level,
    feature_set,
    data_size_str,
    team_name,
    last_submission_score, # (V17) Renamed
    last_rank, # (V17) New
    submission_count,
    username
):
    """
    (V17) Core experiment: Now uses 'yield' and HTML helpers.
    """
    
    # --- Stage 1: Lock UI and give initial feedback ---
    initial_updates = {
        submit_button: gr.update(value="🔬 (1/5) Starting Experiment...", interactive=False),
        submission_feedback_display: gr.update(value="<p style='text-align:center; padding: 20px 0;'>Starting experiment...</p>"),
    }
    yield initial_updates
    
    if not model_name_key or model_name_key not in MODEL_TYPES:
        model_name_key = DEFAULT_MODEL
    feature_set = feature_set or []
    complexity_level = safe_int(complexity_level, 2)
    
    log_output = f"▶ New Experiment\nModel: {model_name_key}\n..."

    if playground is None:
        settings = compute_rank_settings(
             submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )
        error_updates = {
            submission_feedback_display: "<p style='text-align:center; color:red; padding:20px 0;'>Playground not connected.</p>",
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True),
            team_leaderboard_display: "<p style='text-align:center; color:red; padding-top:20px;'>Playground not connected.</p>",
            individual_leaderboard_display: "<p style='text-align:center; color:red; padding-top:20px;'>Playground not connected.</p>",
            last_submission_score_state: last_submission_score,
            last_rank_state: last_rank,
            submission_count_state: submission_count,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
        }
        yield error_updates
        return

    try:
        # --- Stage 2: Train Model (Local) ---
        yield { submission_feedback_display: gr.update(value="<p style='text-align:center; padding: 20px 0;'>🔬 (2/5) Training model locally...</p>") }

        # A. (V10) Get pre-sampled data
        sample_frac = DATA_SIZE_MAP.get(data_size_str, 0.2)
        X_train_sampled = X_TRAIN_SAMPLES_MAP[data_size_str]
        y_train_sampled = Y_TRAIN_SAMPLES_MAP[data_size_str]
        log_output += f"Using {int(sample_frac * 100)}% data.\n"

        # B. (V9) Determine features...
        numeric_cols = []
        categorical_cols = []
        for feat in feature_set:
            if feat in ALL_NUMERIC_COLS: numeric_cols.append(feat)
            elif feat in ALL_CATEGORICAL_COLS: categorical_cols.append(feat)
        
        if not numeric_cols and not categorical_cols:
            raise ValueError("No features selected for modeling.")

        # C. Preprocessing
        num_tf = Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
        cat_tf = Pipeline(steps=[("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
                                 ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
        transformers = []
        if numeric_cols: transformers.append(("num", num_tf, numeric_cols))
        if categorical_cols: transformers.append(("cat", cat_tf, categorical_cols))
        preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")

        X_train_processed = preprocessor.fit_transform(X_train_sampled[numeric_cols + categorical_cols])
        X_test_processed = preprocessor.transform(X_TEST_RAW[numeric_cols + categorical_cols])

        # D. Model build & tune
        base_model = MODEL_TYPES[model_name_key]["model_builder"]()
        tuned_model = tune_model_complexity(base_model, complexity_level)

        # E. Train
        tuned_model.fit(X_train_processed, y_train_sampled)
        log_output += "Training done.\n"

        # --- Stage 3: Submit (API Call 1) ---
        yield { submission_feedback_display: gr.update(value="<p style='text-align:center; padding: 20px 0;'>📡 (3/5) Submitting model to leaderboard...</p>") }

        predictions = tuned_model.predict(X_test_processed)
        description = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_str})"
        tags = f"team:{team_name},model:{model_name_key}"
        
        playground.submit_model(
            model=tuned_model, preprocessor=preprocessor, prediction_submission=predictions,
            input_dict={'description': description, 'tags': tags},
            custom_metadata={'Team': team_name, 'Moral_Compass': 0} 
        )
        log_output += "\nSUCCESS! Model submitted.\n"

        # --- Stage 4: Refresh Leaderboard (API Call 2) ---
        yield { submission_feedback_display: gr.update(value="<p style='text-align:center; padding: 20px 0;'>🏆 (4/5) Fetching new leaderboard rankings...</p>") }
        
        full_leaderboard_df = playground.get_leaderboard()

        # (V17) Call new summary function
        team_html, individual_html, kpi_card_html, new_best_accuracy, new_rank, this_submission_score = generate_competitive_summary(
            full_leaderboard_df, 
            team_name, 
            username,
            last_submission_score,
            last_rank,
            submission_count
        )

        # --- Stage 5: Final UI Update ---
        yield { submission_feedback_display: gr.update(value="<p style='text-align:center; padding: 20px 0;'>✅ (5/5) All done! Updating results.</p>") }
        
        new_submission_count = submission_count + 1
        settings = compute_rank_settings(
            new_submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )

        final_updates = {
            submission_feedback_display: kpi_card_html,
            team_leaderboard_display: team_html,
            individual_leaderboard_display: individual_html,
            last_submission_score_state: this_submission_score, # (V17) Store this sub's score
            last_rank_state: new_rank, # (V17) Store new rank
            submission_count_state: new_submission_count,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True)
        }
        yield final_updates

    except Exception as e:
        error_msg = f"ERROR: {e}"
        settings = compute_rank_settings(
             submission_count, model_name_key, complexity_level, feature_set, data_size_str
        )
        error_updates = {
            submission_feedback_display: f"<p style='text-align:center; color:red; padding:20px 0;'>An error occurred: {error_msg}</p>",
            team_leaderboard_display: "<p style='text-align:center; color:red; padding-top:20px;'>Error loading data.</p>",
            individual_leaderboard_display: "<p style='text-align:center; color:red; padding-top:20px;'>Error loading data.</p>",
            last_submission_score_state: last_submission_score,
            last_rank_state: last_rank,
            submission_count_state: submission_count,
            rank_message_display: settings["rank_message"],
            model_type_radio: gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            complexity_slider: gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            feature_set_checkbox: gr.update(choices=settings["feature_set_choices"], value=settings["feature_set_value"], interactive=settings["feature_set_interactive"]),
            data_size_radio: gr.update(choices=settings["data_size_choices"], value=settings["data_size_value"], interactive=settings["data_size_interactive"]),
            submit_button: gr.update(value="🔬 Build & Submit Model", interactive=True)
        }
        yield error_updates


def on_initial_load(username):
    """(V17) Updated to load HTML leaderboards."""
    
    initial_ui = compute_rank_settings(
        0, DEFAULT_MODEL, 2, DEFAULT_FEATURE_SET, DEFAULT_DATA_SIZE
    )
    
    team_html = "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see team rankings.</p>"
    individual_html = "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see individual rankings.</p>"
    try:
        if playground:
            full_leaderboard_df = playground.get_leaderboard()
            team_html, individual_html, _, _, _, _ = generate_competitive_summary(
                full_leaderboard_df, 
                CURRENT_TEAM_NAME, 
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
# 3. Factory Function: Build Gradio App
# -------------------------------------------------------------------------

def create_model_building_game_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """
    Create (but do not launch) the model building game app.
    """
    css = """
    .panel-box {
        background:#fef3c7; padding:20px; border-radius:16px;
        border:2px solid #f59e0b; margin-bottom:18px; color: #92400e;
    }
    .leaderboard-box {
        background:#dbeafe; padding:20px; border-radius:16px;
        border:2px solid #3b82f6; margin-top:12px; color: #1e3a8a;
    }
    .slide-content {
        max-width: 900px; margin-left: auto; margin-right: auto;
    }
    .step-visual {
        display:flex; flex-wrap: wrap; justify-content:space-around; 
        align-items:center; margin: 24px 0; text-align:center; font-size: 1rem;
    }
    .step-visual-box {
        padding:16px; background:white; border-radius:8px; 
        border:2px solid #6366f1; margin: 5px; color: #1f2937;
    }
    .step-visual-arrow { font-size: 2rem; color: #6b7280; margin: 5px; }
    .mock-button {
        width: 100%; font-size: 1.25rem; font-weight: 600; padding: 16px 24px;
        background-color: #4f46e5; color: white; border: none; border-radius: 8px;
        cursor: not-allowed;
    }
    .mock-ui-box {
        background: #f9fafb; border: 2px solid #e5e7eb; padding: 24px; border-radius: 16px;
        color: #1f2937;
    }
    .mock-ui-inner {
        background: #ffffff; border: 1px solid #e5e7eb; padding: 24px; border-radius: 12px;
    }
    .mock-ui-control-box {
        padding: 12px; background:white; border-radius:8px; border: 1px solid #d1d5db;
    }
    .mock-ui-radio-on { font-size: 1.5rem; vertical-align: middle; color: #4f46e5; }
    .mock-ui-radio-off { font-size: 1.5rem; vertical-align: middle; color: #d1d5db; }
    .mock-ui-slider-text { font-size: 1.5rem; margin:0; color: #4f46e5; letter-spacing: 4px; }
    .mock-ui-slider-bar { color: #d1d5db; }
    
    /* (V17) New KPI Card Styles */
    .kpi-card {
        background: #f9fafb; border: 2px solid #16a34a; padding: 24px;
        border-radius: 16px; text-align: center; max-width: 600px; margin: auto;
        color: #111827;
    }
    .kpi-card-body {
        display: flex; flex-wrap: wrap; justify-content: space-around;
        align-items: flex-end; margin-top: 24px;
    }
    .kpi-metric-box { min-width: 150px; margin: 10px; }
    .kpi-label { font-size: 1rem; color: #6b7280; margin:0; }
    .kpi-score { font-size: 3rem; font-weight: 700; margin:0; line-height: 1.1; }
    
    /* (V17) New Leaderboard Table Styles */
    .leaderboard-html-table {
        width: 100%; border-collapse: collapse; text-align: left;
        font-size: 1rem; color: #1f2937;
    }
    .leaderboard-html-table thead { background: #f3f4f6; }
    .leaderboard-html-table th {
        padding: 12px 16px; font-size: 0.9rem; color: #374151;
        font-weight: 600;
    }
    .leaderboard-html-table tbody tr { border-bottom: 1px solid #e5e7eb; }
    .leaderboard-html-table td { padding: 12px 16px; }
    .leaderboard-html-table .user-row-highlight {
        background: #dbeafe; /* light blue */
        font-weight: 600;
        color: #1e3a8a; /* dark blue */
    }
    """
    
    # (V10) Define globals for yield
    global submit_button, submission_feedback_display, team_leaderboard_display
    global individual_leaderboard_display, last_submission_score_state, last_rank_state, submission_count_state
    global rank_message_display, model_type_radio, complexity_slider
    global feature_set_checkbox, data_size_radio

    # (V22) Removed 'theme_mode="light"' to fix crash in Gradio v5.49.1
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="indigo"), css=css) as demo:
        username = os.environ.get("username") or "Unknown_User"

        # Loading screen
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding:100px 0;'>
                    <h2 style='font-size:2rem; color:#6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )
            
        # --- (V21) New 7-Slide Briefing Slideshow ---
            
        # (V19) Slide 1: From Understanding to Building
        with gr.Column(visible=True) as briefing_slide_1:
            gr.Markdown("<h1 style='text-align:center;'>🔄 From Understanding to Building</h1>")
            gr.HTML(
                """
                <div class='slide-content'>
                <div class='leaderboard-box' style='border-color: #16a34a;'>
                <h3 style='font-size: 1.5rem; text-align:center; margin-top:0;'>Great progress! You've now:</h3>
                
                <ul style='list-style: none; padding-left: 0; margin-top: 24px; margin-bottom: 24px;'>
                    <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'>
                        <span style='font-size: 1.5rem; vertical-align: middle;'>✅</span>
                        Made tough decisions as a judge using AI predictions
                    </li>
                    <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'>
                        <span style='font-size: 1.5rem; vertical-align: middle;'>✅</span>
                        Learned about false positives and false negatives
                    </li>
                    <li style='font-size: 1.1rem; font-weight: 500; margin-bottom: 12px;'>
                        <span style='font-size: 1.5rem; vertical-align: middle;'>✅</span>
                        Understood how AI works:
                    </li>
                </ul>
                
                <div style='background:white; padding:16px; border-radius:12px; margin:12px 0; text-align:center;'>
                    <div style='display:inline-block; background:#dbeafe; padding:12px 16px; border-radius:8px; margin:4px;'>
                        <h3 style='margin:0; color:#0369a1;'>INPUT</h3>
                    </div>
                    <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                    <div style='display:inline-block; background:#fef3c7; padding:12px 16px; border-radius:8px; margin:4px;'>
                        <h3 style='margin:0; color:#92400e;'>MODEL</h3>
                    </div>
                    <div style='display:inline-block; font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                    <div style='display:inline-block; background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:4px;'>
                        <h3 style='margin:0; color:#15803d;'>OUTPUT</h3>
                    </div>
                </div>
                
                <hr style='margin: 24px 0; border-top: 2px solid #c7d2fe;'>
                
                <h3 style='font-size: 1.5rem; text-align:center;'>Now it's time to step into the shoes of an AI Engineer.</h3>
                <p style='font-size: 1.1rem; text-align:center; margin-top: 12px;'>
                    <strong>Your New Challenge:</strong> Build AI models that are more accurate than the one you used as a judge.
                </p>
                <p style='font-size: 1.1rem; text-align:center; margin-top: 12px;'>
                    Remember: You experienced firsthand how AI predictions affect real people's lives. Use that knowledge to build something better.
                </p>
                </div>
                </div>
                """
            )
            briefing_1_next = gr.Button("Next ▶️", variant="primary", size="lg")
        
        # (V19) Slide 2: Your Engineering Mission
        with gr.Column(visible=False) as briefing_slide_2:
            gr.Markdown("<h1 style='text-align:center;'>⚗️ Your Engineering Mission</h1>")
            gr.HTML("<div class='slide-content'>")
            gr.HTML("<div class='panel-box'>")
            gr.Markdown(
                f"""
                ### You're about to compete with other engineers... and as a team!
                To help you in your mission, you've been assigned to an engineering team. Your results will be tracked both individually and as a group on the Live Standings.
                """
            )
            gr.HTML(
                f"""
                <div class='leaderboard-box' style='max-width: 600px; margin: 16px auto; text-align: center; padding: 16px;'>
                    <p style='font-size: 1.1rem; margin:0;'>Your team is:</p>
                    <h3 style='font-size: 1.75rem; color: #4338ca; margin: 8px 0;'>
                        {CURRENT_TEAM_NAME}
                    </h3>
                </div>
                """
            )
            gr.Markdown(
                """
                **The Data Challenge:**
                * **Defendant profiles:** Age, prior offenses, charge details
                * **Historical outcomes:** Who *actually* re-offended
                * **Your goal:** Predict future risk more accurately

                Ready to build something that could change how justice works?
                """
            )
            gr.HTML("</div>")
            gr.HTML("</div>")
            with gr.Row():
                briefing_2_back = gr.Button("◀️ Back", size="lg")
                briefing_2_next = gr.Button("Next ▶️", variant="primary", size="lg")
                
        # (V18) Slide 3: How to Play
        with gr.Column(visible=False) as briefing_slide_3:
            gr.Markdown("<h1 style='text-align:center;'>🕹️ How to Play</h1>")
            gr.HTML("<div class='slide-content'>")
            gr.HTML("<div class='panel-box'>")
            gr.Markdown(
                """
                ### It's as easy as 1-2-3.

                1.  Select your options.
                2.  Push one button.
                3.  See your score!

                When you get to the 'Model Building Arena', your main action is to press this button:
                """
            )
            gr.HTML(
                """
                <div style='max-width: 400px; margin: 24px auto;'>
                    <button class='mock-button'>
                        5. 🔬 Build & Submit Model
                    </button>
                </div>
                """
            )
            gr.Markdown(
                """
                But *why* would you press it more than once? Let's look at the process.
                """
            )
            gr.HTML("</div>")
            gr.HTML("</div>")
            with gr.Row():
                briefing_3_back = gr.Button("◀️ Back", size="lg")
                briefing_3_next = gr.Button("Next ▶️", variant="primary", size="lg")
                
        # (V18) Slide 4: The Experiment Loop
        with gr.Column(visible=False) as briefing_slide_4:
            gr.Markdown("<h1 style='text-align:center;'>🔁 The Experiment Loop</h1>")
            gr.HTML("<div class='slide-content'>")
            gr.HTML("<div class='panel-box'>")
            gr.Markdown(
                """
                ### How AI Teams Find the Best Model
                Real AI teams never get it right on the first try. They follow a simple loop to experiment and improve: **Try, Test, Learn, Repeat.**
                """
            )
            gr.HTML(
                """
                <!-- Simple 3-step visual -->
                <div class='step-visual'>
                    <div class='step-visual-box'><b>1. Build a Model</b><br/>(Get a starting score)</div>
                    <div class='step-visual-arrow'>→</div>
                    <div class='step-visual-box'><b>2. Ask a Question</b><br/>(e.g., "What if I use more data?")</div>
                    <div class='step-visual-arrow'>→</div>
                    <div class='step-visual-box'><b>3. Test Again & Compare</b><br/>(Did the score get better or worse?)</div>
                </div>
                """
            )
            gr.Markdown(
                """
                They repeat this loop—changing one thing at a time—until they find the best possible score.

                <hr style='margin: 24px 0;'>

                ### You will do the exact same thing!
                This is how you will experiment:
                1.  Pick your settings using the **Control Knobs**.
                2.  Click the **"Build & Submit Model"** button.
                3.  Check your new score on the **Leaderboard**.
                4.  ...Then, change one thing and submit again!
                """
            )
            gr.HTML("</div>")
            gr.HTML("</div>")
            with gr.Row():
                briefing_4_back = gr.Button("◀️ Back", size="lg")
                briefing_4_next = gr.Button("Next ▶️", variant="primary", size="lg")

        # (V21) Slide 5: Control Knobs (Part 1)
        with gr.Column(visible=False) as briefing_slide_5:
            gr.Markdown("<h1 style='text-align:center;'>🎛️ Your Control Knobs (Part 1)</h1>")
            gr.HTML("<div class='slide-content'>")
            gr.HTML("<div class='mock-ui-box' style='border-color: #f59e0b;'>") # Panel box border
            gr.HTML(
                """
                <div class='mock-ui-inner'>

                    <!-- Visually Mocked-up Control 1 -->
                    <h3 style='margin-top:0;'>1. Model Strategy</h3>
                    <div class='mock-ui-control-box'>
                        <p style='font-size: 1.1rem; margin: 8px 0;'>
                            <span class='mock-ui-radio-on'>◉</span>
                            (•) The Balanced Generalist
                        </p>
                        <p style='font-size: 1.1rem; margin: 8px 0;'>
                            <span class='mock-ui-radio-off'>○</span>
                            ( ) The Rule-Maker
                        </p>
                    </div>
                    
                    <!-- Explanation 1 -->
                    <div style='margin-top: 16px; font-size: 1rem;'>
                        <ul style='list-style-position: inside;'>
                            <li><b>What it is:</b> Your starting plan, or <i>how</i> the model learns. Different "strategies" are just different types of models that learn in different ways.</li>
                            <li><b>Why it matters:</b> Some are simple and fast, others are powerful and complex. Choosing the right one is your first big decision.</li>
                            <li><b>Examples in your app:</b>
                                <ul style='list-style-position: inside; margin-left: 20px;'>
                                <li><b>The Balanced Generalist:</b> A reliable, all-purpose model. It's fast and gives good, stable results.</li>
                                <li><b>The Rule-Maker:</b> This model learns simple "if... then..." rules from the data.</li>
                                <li><b>The Deep Pattern-Finder:</b> A very powerful model that can find hidden, complex connections.</li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                    
                    <hr style='margin: 24px 0;'>

                    <!-- Visually Mocked-up Control 2 -->
                    <h3>2. Model Complexity</h3>
                    <div class='mock-ui-control-box' style='text-align: center;'>
                        <p style='font-size: 1.1rem; margin:0;'>Level: 3</p>
                        <p class='mock-ui-slider-text'>
                            <span class='mock-ui-slider-bar'>1 ── 2 ──</span> ● <span class='mock-ui-slider-bar'>── 4 ── 5</span>
                        </p>
                    </div>
                    
                    <!-- Explanation 2 -->
                    <div style='margin-top: 16px; font-size: 1rem;'>
                        <ul style='list-style-position: inside;'>
                            <li><b>What it is:</b> This tunes <i>how much detail</i> your chosen model should learn.</li>
                            <li><b>Why it matters:</b>
                                <br/>→ <b>Low Complexity (Level 1):</b> Tells the model to "learn only the most basic, obvious rules."
                                <br/>→ <b>High Complexity (Level 5):</b> Tells the model to "learn every tiny, specific detail." This is powerful, but risks "memorizing" the practice data.</li>
                        </ul>
                    </div>

                </div>
                """
            )
            gr.HTML("</div></div>")
            with gr.Row():
                briefing_5_back = gr.Button("◀️ Back", size="lg")
                briefing_5_next = gr.Button("Next ▶️", variant="primary", size="lg")

        # (V21) Slide 6: Control Knobs (Part 2)
        with gr.Column(visible=False) as briefing_slide_6:
            gr.Markdown("<h1 style='text-align:center;'>🎛️ Your Control Knobs (Part 2)</h1>")
            gr.HTML("<div class='slide-content'>")
            gr.HTML("<div class='mock-ui-box' style='border-color: #f59e0b;'>") # Panel box border
            gr.HTML(
                """
                <div class='mock-ui-inner'>

                    <!-- Visually Mocked-up Control 3 -->
                    <h3 style='margin-top:0;'>3. Data Ingredients</h3>
                    <div class='mock-ui-control-box'>
                        <p style='font-size: 1.1rem; margin: 8px 0;'>
                            <span class='mock-ui-radio-on'>☑</span>
                            [✓] Juvenile Felony Count
                        </p>
                        <p style='font-size: 1.1rem; margin: 8px 0;'>
                            <span class='mock-ui-radio-on'>☑</span>
                            [✓] Race
                        </p>
                        <p style='font-size: 1.1rem; margin: 8px 0;'>
                            <span class='mock-ui-radio-off'>☐</span>
                            [ ] Charge Description
                        </p>
                    </div>
                    
                    <!-- Explanation 3 -->
                    <div style='margin-top: 16px; font-size: 1rem;'>
                        <ul style='list-style-position: inside;'>
                            <li><b>What it is:</b> The <i>information</i> you feed the model to help it learn. The model can <i>only</i> learn from the data you give it.</li>
                            <li><b>Why it matters:</b> If you give it good information (like `Prior Crimes Count`), it can make good predictions. If you give it biased information (like `Race`), it will learn to make biased predictions.</li>
                        </ul>
                    </div>
                    
                    <hr style='margin: 24px 0;'>

                    <!-- Visually Mocked-up Control 4 -->
                    <h3>4. Data Size</h3>
                    <div class='mock-ui-control-box'>
                        <p style='font-size: 1.1rem; margin: 8px 0;'>
                            <span class='mock-ui-radio-on'>◉</span>
                            (•) Small (20%)
                        </p>
                        <p style='font-size: 1.1rem; margin: 8px 0;'>
                            <span class='mock-ui-radio-off'>○</span>
                            ( ) Medium (60%)
                        </p>
                    </div>
                    
                    <!-- Explanation 4 -->
                    <div style='margin-top: 16px; font-size: 1rem;'>
                        <ul style='list-style-position: inside;'>
                            <li><b>What it is:</b> How much "practice" data you give the model to learn from.</li>
                            <li><b>Why it matters:</b>
                                <br/>→ <b>Small (20%):</b> Very fast! Great for a quick first test, but the model won't learn much.
                                <br/>→ <b>Full (100%):</b> Gives the model the most "practice" possible. It's slower, but gives the model the best chance to learn.</li>
                        </ul>
                    </div>

                </div>
                """
            )
            gr.HTML("</div></div>")
            with gr.Row():
                briefing_6_back = gr.Button("◀️ Back", size="lg")
                briefing_6_next = gr.Button("Next ▶️", variant="primary", size="lg")

        # (V21) Slide 7: Your Career as an Engineer
        with gr.Column(visible=False) as briefing_slide_7:
            gr.Markdown("<h1 style='text-align:center;'>🏆 Your Career as an Engineer</h1>")
            gr.HTML("<div class='slide-content'>")
            gr.HTML("<div class='panel-box'>")
            gr.Markdown(
                """
                ### How You're Scored: The "Final Test"
                * **How it works:** Your model is tested on hidden data for official Accuracy score
                * **The Leaderboard:** Live Standings leaderboard tracks your progress
                
                ### How You Improve: The Game
                * **Compete to Improve:** Compete to improve your personal best score
                * **Get Promoted & Unlock Tools:** Get promoted & unlock tools as you submit more models
                * **Trainee → Junior → Senior → Lead Engineer**

                ### Begin Your Mission
                You are now ready. Use the experiment loop, get promoted, unlock all the tools, and find the best combination to get the highest score.
                
                Remember: You've seen how these predictions affect real people. Build accordingly.
                """
            )
            gr.HTML("</div>")
            gr.HTML("</div>")
            with gr.Row():
                briefing_7_back = gr.Button("◀️ Back", size="lg")
                briefing_7_next = gr.Button("Begin Model Building ▶️", variant="primary", size="lg")
                
        # --- End V21 Slideshow ---


        # (V13) Renamed to 'model_building_step'
        with gr.Column(visible=False) as model_building_step:
            gr.Markdown("<h1 style='text-align:center;'>🛠️ Model Building Arena</h1>")

            team_name_state = gr.State(CURRENT_TEAM_NAME)
            # (V17) Updated state vars
            last_submission_score_state = gr.State(0.0)
            last_rank_state = gr.State(0)
            submission_count_state = gr.State(0)

            # Buffered states for all dynamic inputs
            model_type_state = gr.State(DEFAULT_MODEL)
            complexity_state = gr.State(2)
            feature_set_state = gr.State(DEFAULT_FEATURE_SET)
            data_size_state = gr.State(DEFAULT_DATA_SIZE)

            # (V10) Assign UI components to global vars
            rank_message_display = gr.Markdown("### Rank loading...")
            with gr.Row():
                with gr.Column(scale=1):
                    
                    model_type_radio = gr.Radio(
                        label="1. Model Strategy", 
                        choices=[], 
                        value=None, 
                        interactive=False
                    )
                    model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL))

                    gr.Markdown("---") # Separator

                    complexity_slider = gr.Slider(
                        label="2. Model Complexity",
                        minimum=1, maximum=2, step=1, value=2,
                        info="Higher may capture deeper patterns; may overfit."
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
                    
                    # (V16) Renamed label to "Data Size"
                    data_size_radio = gr.Radio(
                        label="4. Data Size",
                        choices=[DEFAULT_DATA_SIZE],
                        value=DEFAULT_DATA_SIZE,
                        interactive=False
                    )

                    gr.Markdown("---") # Separator
                    
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
                    
                    # (V17) This is now the KPI Card
                    submission_feedback_display = gr.HTML(
                        "<p style='text-align:center; color:#6b7280; padding:20px 0;'>Submit your first model to get feedback!</p>"
                    )

                    with gr.Tabs():
                        with gr.TabItem("Team Standings"):
                            # (V17) Replaced DataFrame with HTML
                            team_leaderboard_display = gr.HTML(
                                "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see team rankings.</p>"
                            )
                        with gr.TabItem("Individual Standings"):
                            # (V17) Replaced DataFrame with HTML
                            individual_leaderboard_display = gr.HTML(
                                "<p style='text-align:center; color:#6b7280; padding-top:20px;'>Submit a model to see individual rankings.</p>"
                            )

            gr.HTML(
                """
                <div style='background:#fef2f2; padding:20px; border-radius:12px; border-left:6px solid #dc2626; margin-top:24px;'>
                    <b>Ethical Reminder:</b> Accuracy isn't everything. The strongest data 'ingredients' (like age or prior counts) often carry the most societal bias.
                </div>
                """
            )
            step_2_next = gr.Button("Finish & Reflect ▶️", variant="secondary")

        # (V13) Renamed to 'conclusion_step'
        with gr.Column(visible=False) as conclusion_step:
            gr.Markdown("<h1 style='text-align:center;'>✅ Section Complete</h1>")
            
            final_score_display = gr.Markdown("### Your Final Results:")
            
            gr.HTML("<div class='leaderboard-box'>")
            # (V20) Updated conclusion text
            gr.Markdown(
                """
                ### ✅ Section Complete

                **💡 What you learned by doing:**
                * Choice of Model Strategy gives different starting scores
                * More complex ≠ always better
                * More data generally helps model performance
                * Data inputs like previous criminal activity can help the model learn.

                Now you have built model optimized to predict criminal risk on a specific dataset. Next let's explore how it affects the real world.

                ---
                <h2 style='text-align:center; margin-top:16px;'>👇 SCROLL DOWN 👇</h2>
                <p style='text-align:center;'>Scroll down in the notebook to continue to the next learning section.</p>
                """
            )
            gr.HTML("</div>") 
            
            step_3_back = gr.Button("◀️ Back to Experiment")

        # --- (V21) Updated Navigation logic for 7 slides ---
        all_steps_nav = [
            briefing_slide_1, briefing_slide_2, briefing_slide_3, 
            briefing_slide_4, briefing_slide_5, briefing_slide_6, briefing_slide_7,
            model_building_step, conclusion_step, loading_screen
        ]

        def create_nav(current_step, next_step):
            def _nav():
                updates = {loading_screen: gr.update(visible=True)}
                for s in all_steps_nav:
                    if s != loading_screen:
                        updates[s] = gr.update(visible=False)
                yield updates
                
                updates = {next_step: gr.update(visible=True)}
                for s in all_steps_nav:
                    if s != next_step:
                        updates[s] = gr.update(visible=False)
                yield updates
            return _nav

        def navigate_to_step_3(feedback_text):
            updates = {loading_screen: gr.update(visible=True)}
            for s in all_steps_nav:
                if s != loading_screen:
                    updates[s] = gr.update(visible=False)
            yield updates
            
            updates = {
                conclusion_step: gr.update(visible=True),
                final_score_display: gr.HTML(feedback_text) # (V17) Use HTML
            }
            for s in all_steps_nav:
                if s != conclusion_step:
                    updates[s] = gr.update(visible=False)
            yield updates
        
        # --- (V21) Wire up all 7 briefing slide buttons ---
        
        briefing_1_next.click(
            fn=create_nav(briefing_slide_1, briefing_slide_2),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_2_back.click(
            fn=create_nav(briefing_slide_2, briefing_slide_1),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_2_next.click(
            fn=create_nav(briefing_slide_2, briefing_slide_3),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_3_back.click(
            fn=create_nav(briefing_slide_3, briefing_slide_2),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_3_next.click(
            fn=create_nav(briefing_slide_3, briefing_slide_4),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_4_back.click(
            fn=create_nav(briefing_slide_4, briefing_slide_3),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_4_next.click(
            fn=create_nav(briefing_slide_4, briefing_slide_5),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_5_back.click(
            fn=create_nav(briefing_slide_5, briefing_slide_4),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_5_next.click(
            fn=create_nav(briefing_slide_5, briefing_slide_6),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_6_back.click(
            fn=create_nav(briefing_slide_6, briefing_slide_5),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_6_next.click(
            fn=create_nav(briefing_slide_6, briefing_slide_7),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        briefing_7_back.click(
            fn=create_nav(briefing_slide_7, briefing_slide_6),
            inputs=None, outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        
        # Slide 7 -> Model Building App
        briefing_7_next.click(
            fn=create_nav(briefing_slide_7, model_building_step),
            inputs=None,
            outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        
        # Model Building App -> Conclusion
        step_2_next.click(
            fn=navigate_to_step_3,
            inputs=[submission_feedback_display], 
            outputs=all_steps_nav + [final_score_display], 
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        
        # Conclusion -> Model Building App
        step_3_back.click(
            fn=create_nav(conclusion_step, model_building_step),
            inputs=None,
            outputs=all_steps_nav,
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        # --- END NAVIGATION UPDATE ---

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

        # (V17) Updated submit_button click with new states
        all_outputs = [
            submission_feedback_display,
            team_leaderboard_display,
            individual_leaderboard_display,
            last_submission_score_state,
            last_rank_state,
            submission_count_state,
            rank_message_display,
            model_type_radio,
            complexity_slider,
            feature_set_checkbox, 
            data_size_radio,
            submit_button
        ]
        
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
                gr.State(username)
            ],
            outputs=all_outputs,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )

        # (V17) Updated demo.load() outputs
        demo.load(
            fn=lambda u: on_initial_load(u),
            inputs=[gr.State(username)],
            outputs=[
                model_card_display,
                team_leaderboard_display, # HTML
                individual_leaderboard_display, # HTML
                rank_message_display,
                model_type_radio,
                complexity_slider,
                feature_set_checkbox,
                data_size_radio,
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
        # (V10) This now triggers the pre-sampling
        X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_and_prep_data()

    demo = create_model_building_game_app()
    with contextlib.redirect_stdout(open(os.devnull, "w")), contextlib.redirect_stderr(open(os.devnull, "w")):
        demo.launch(share=share, inline=True, debug=debug, height=height)

# -------------------------------------------------------------------------
# 5. Script Entrypoint
# -------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- Initializing Model Building Game ---")
    try:
        playground = Competition(MY_PLAYGROUND_ID)
        print("Playground connection successful.")
    except Exception as e:
        print(f"Playground connection failed: {e}")
        playground = None

    # (V10) This now triggers the pre-sampling
    X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_and_prep_data()
    print("--- Launching App ---")
    app = create_model_building_game_app()
    app.launch(share=False, debug=True, height=1100)

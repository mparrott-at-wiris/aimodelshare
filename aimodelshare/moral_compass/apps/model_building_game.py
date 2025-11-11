"""
Model Building Game (Ètica en Joc) - Justice & Equity Challenge

This app teaches:
1. The experiment loop of iterative AI model development
2. How model parameters (type, complexity, data size, features) affect performance
3. Competition-driven improvement (individual & team leaderboards)
4. Ethical awareness via controlled unlocking of sensitive features

Structure:
- Factory function `create_model_building_game_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_model_building_game_app()` launches it inline (for notebooks)

Stylistic & UX Alignment:
- Uses multi-step slideshow navigation with a loading screen (like other apps)
- Central, color-coded instructional panels
- Smooth scroll-to-top transitions
- Factory + launcher pattern consistent with other challenge apps
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

# Feature groups
BASIC_NUMERIC_COLS = [
    "priors_count", "juv_fel_count", "juv_misd_count",
    "juv_other_count", "days_b_screening_arrest"
]
BASIC_CATEGORICAL_COLS = ["c_charge_desc"]
SENSITIVE_FEATURES = ["race", "sex", "age", "age_cat", "c_charge_degree"]
ALL_NUMERIC_COLS = BASIC_NUMERIC_COLS + [c for c in SENSITIVE_FEATURES if c == "age"]
ALL_CATEGORICAL_COLS = BASIC_CATEGORICAL_COLS + [c for c in SENSITIVE_FEATURES if c != "age"]

MAX_ROWS = 4000
TOP_N_CHARGE_CATEGORICAL = 50
np.random.seed(42)

# Global state containers (populated during initialization)
playground = None
X_TRAIN_RAW = None
X_TEST_RAW = None
Y_TRAIN = None
Y_TEST = None


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
    """Load, sample, and prepare raw COMPAS dataset."""
    url = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"
    response = requests.get(url)
    df = pd.read_csv(StringIO(response.text))

    if df.shape[0] > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42)

    feature_columns = [
        "race", "sex", "age", "age_cat", "c_charge_degree", "c_charge_desc",
        "priors_count", "juv_fel_count", "juv_misd_count", "juv_other_count",
        "days_b_screening_arrest"
    ]
    target_column = "two_year_recid"

    # Reduce charge descriptor cardinality
    if "c_charge_desc" in df.columns:
        top_charges = df["c_charge_desc"].value_counts().head(TOP_N_CHARGE_CATEGORICAL).index
        df["c_charge_desc"] = df["c_charge_desc"].apply(
            lambda x: x if pd.notna(x) and x in top_charges else "OTHER"
        )

    # Ensure required columns exist
    for col in feature_columns:
        if col not in df.columns:
            df[col] = np.nan

    X = df[feature_columns].copy()
    y = df[target_column].copy()

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
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


def generate_competitive_summary(leaderboard_df, team_name, username):
    """
    Build summaries and feedback from leaderboard.
    Returns (team_summary_df, individual_summary_df, feedback_text, latest_accuracy).
    """
    team_summary = pd.DataFrame(columns=["Team", "Best_Score", "Avg_Score", "Submissions"])
    individual_summary = pd.DataFrame(columns=["Engineer", "Best_Score", "Submissions"])

    if leaderboard_df is None or leaderboard_df.empty or "accuracy" not in leaderboard_df.columns:
        return team_summary, individual_summary, "Leaderboard empty — be first to submit!", 0.0

    # Team summary
    if "Team" in leaderboard_df.columns:
        team_summary = (
            leaderboard_df.groupby("Team")["accuracy"]
            .agg(Best_Score="max", Avg_Score="mean", Submissions="count")
            .reset_index()
            .sort_values("Best_Score", ascending=False)
            .reset_index(drop=True)
        )
        team_summary.index = team_summary.index + 1
        team_summary["Best_Score"] = team_summary["Best_Score"].round(4)
        team_summary["Avg_Score"] = team_summary["Avg_Score"].round(4)

    # Individual summary
    user_bests = leaderboard_df.groupby("username")["accuracy"].max()
    user_counts = leaderboard_df.groupby("username")["accuracy"].count()
    individual_summary = pd.DataFrame(
        {"Engineer": user_bests.index, "Best_Score": user_bests.values, "Submissions": user_counts.values}
    ).sort_values("Best_Score", ascending=False).reset_index(drop=True)
    individual_summary.index = individual_summary.index + 1
    individual_summary["Best_Score"] = individual_summary["Best_Score"].round(4)

    # Feedback
    latest_accuracy = 0.0
    individual_feedback = ""
    team_feedback = ""
    try:
        my_submissions = leaderboard_df[leaderboard_df["username"] == username].sort_values(
            by="timestamp", ascending=False
        )
        if not my_submissions.empty:
            latest_accuracy = my_submissions.iloc[0]["accuracy"]
            rank_row = individual_summary[individual_summary["Engineer"] == username]
            if not rank_row.empty:
                rank = rank_row.index[0]
                individual_feedback += f"You are Rank #{rank} of {len(individual_summary)} engineers.\n"

            if len(my_submissions) > 1:
                prev_acc = my_submissions.iloc[1]["accuracy"]
                diff = latest_accuracy - prev_acc
                if diff > 0.0001:
                    individual_feedback += f"Improved! {latest_accuracy:.4f} (+{diff:.4f} vs last).\n"
                elif diff < -0.0001:
                    individual_feedback += f"Drop: {latest_accuracy:.4f} (-{abs(diff):.4f} vs last).\n"
                else:
                    individual_feedback += f"No change from last ({latest_accuracy:.4f}).\n"
            else:
                individual_feedback += f"First submission score: {latest_accuracy:.4f}.\n"
        else:
            individual_feedback += "No submissions yet.\n"

        if "Team" in leaderboard_df.columns:
            tdf = leaderboard_df[leaderboard_df["Team"] == team_name]
            if not tdf.empty:
                team_best = tdf["accuracy"].max()
                team_avg = tdf["accuracy"].mean()
                team_cnt = len(tdf)
                team_feedback = f"Team '{team_name}' — Submissions: {team_cnt}, Best: {team_best:.4f}, Avg: {team_avg:.4f}"
            else:
                team_feedback = f"Team '{team_name}' has no submissions yet."
        else:
            team_feedback = "Team metadata not yet available."

    except Exception:
        individual_feedback = "Could not compute feedback."
        team_feedback = "Team stats unavailable."

    feedback_text = (
        f"### 🏆 Individual Results\n{individual_feedback}\n\n"
        f"### 🤝 Team Stats\n{team_feedback}"
    )
    return team_summary, individual_summary, feedback_text, latest_accuracy


def refresh_leaderboard(team_name, username):
    """Get latest leaderboard summaries."""
    if playground is None:
        return pd.DataFrame(), pd.DataFrame()
    try:
        full_df = playground.get_leaderboard()
        team_df, indiv_df, _, _ = generate_competitive_summary(full_df, team_name, username)
        return team_df, indiv_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


def get_model_card(model_name):
    return MODEL_TYPES.get(model_name, {}).get("card", "No description available.")


def compute_rank_settings(submission_count, current_model, current_complexity, current_size, current_features):
    """
    Returns rank gating settings (no direct component references).
    """
    if submission_count == 0:
        return {
            "rank_message": "### 🧑‍🎓 Rank: Trainee Engineer\nSubmit your first model to rank up!",
            "model_choices": ["The Balanced Generalist"],
            "model_value": "The Balanced Generalist",
            "model_interactive": False,
            "complexity_max": 2,
            "complexity_value": 2,
            "size_max": 2,
            "size_value": 1,
            "features_interactive": False,
            "features_value": []
        }
    elif submission_count == 1:
        return {
            "rank_message": "### 🎉 Rank Up! Junior Engineer\nNew models unlocked — submit 2 more to rank up.",
            "model_choices": ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"],
            "model_value": current_model if current_model in ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'"] else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 4,
            "complexity_value": min(current_complexity, 4),
            "size_max": 4,
            "size_value": min(current_size, 4),
            "features_interactive": False,
            "features_value": []
        }
    elif submission_count == 2:
        return {
            "rank_message": "### 🌟 Rank Up! Senior Engineer\nAll models & complexity unlocked — sensitive data enabled next rank.",
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Deep Pattern-Finder",
            "model_interactive": True,
            "complexity_max": 5,
            "complexity_value": min(current_complexity, 5),
            "size_max": 5,
            "size_value": min(current_size, 5),
            "features_interactive": True,
            "features_value": current_features
        }
    else:
        return {
            "rank_message": "### 👑 Rank: Lead Engineer\nAll tools unlocked — optimize freely!",
            "model_choices": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else "The Balanced Generalist",
            "model_interactive": True,
            "complexity_max": 5,
            "complexity_value": current_complexity,
            "size_max": 5,
            "size_value": current_size,
            "features_interactive": True,
            "features_value": current_features
        }


def run_experiment(
    model_name_key,
    complexity_level,
    data_size_level,
    data_to_include,
    team_name,
    last_accuracy,
    submission_count,
    username
):
    """
    Core experiment: build, train, submit, refresh leaderboard, rank updates.
    Returns the 11 values expected by the UI.
    """
    # Coerce slider values to safe integers to prevent TypeError
    complexity_level = safe_int(complexity_level, 2)
    data_size_level = safe_int(data_size_level, 1)
    
    log_output = f"▶ New Experiment\nModel: {model_name_key}\nComplexity: {complexity_level}\nData Size Level: {data_size_level}\nExtra Data: {', '.join(data_to_include) if data_to_include else 'None'}\n"

    if playground is None:
        log_output += "\nERROR: Playground connection failed."
        settings = compute_rank_settings(submission_count, model_name_key, complexity_level, data_size_level, data_to_include)
        return (
            log_output,
            "Playground not connected.",
            pd.DataFrame(),
            pd.DataFrame(),
            last_accuracy,
            submission_count,
            settings["rank_message"],
            gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            gr.update(minimum=1, maximum=settings["size_max"], value=settings["size_value"]),
            gr.update(interactive=settings["features_interactive"], value=settings["features_value"])
        )

    try:
        # A. Sample training data by size level
        size_map = {1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8, 5: 1.0}
        sample_frac = size_map.get(int(data_size_level), 0.2)
        if sample_frac == 1.0:
            X_train_sampled = X_TRAIN_RAW
            y_train_sampled = Y_TRAIN
        else:
            X_train_sampled = X_TRAIN_RAW.sample(frac=sample_frac, random_state=42)
            y_train_sampled = Y_TRAIN.loc[X_train_sampled.index]
        log_output += f"Using {int(sample_frac * 100)}% training data ({len(X_train_sampled)} rows).\n"

        # B. Features
        numeric_cols = list(BASIC_NUMERIC_COLS)
        categorical_cols = list(BASIC_CATEGORICAL_COLS)
        for feat in data_to_include:
            if feat in ALL_NUMERIC_COLS and feat not in numeric_cols:
                numeric_cols.append(feat)
            elif feat in ALL_CATEGORICAL_COLS and feat not in categorical_cols:
                categorical_cols.append(feat)
        log_output += f"Features: {', '.join(numeric_cols + categorical_cols)}\n"

        if not numeric_cols and not categorical_cols:
            raise ValueError("No features selected for modeling.")

        # C. Preprocessing
        num_tf = Pipeline(
            steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
        )
        cat_tf = Pipeline(
            steps=[("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
                   ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]
        )
        transformers = []
        if numeric_cols:
            transformers.append(("num", num_tf, numeric_cols))
        if categorical_cols:
            transformers.append(("cat", cat_tf, categorical_cols))
        preprocessor = ColumnTransformer(transformers=transformers)

        X_train_processed = preprocessor.fit_transform(X_train_sampled)
        X_test_processed = preprocessor.transform(X_TEST_RAW)
        log_output += "Preprocessing complete.\n"

        # D. Model build & tune
        base_model = MODEL_TYPES[model_name_key]["model_builder"]()
        tuned_model = tune_model_complexity(base_model, complexity_level)
        log_output += f"Model tuned (complexity level {complexity_level}).\n"

        # E. Train
        tuned_model.fit(X_train_processed, y_train_sampled)
        log_output += "Training done.\n"

        # F. Predict & submit
        predictions = tuned_model.predict(X_test_processed)
        description = f"{model_name_key} (Cplx:{complexity_level} Size:{data_size_level})"
        tags = f"team:{team_name},model:{model_name_key}"

        playground.submit_model(
            model=tuned_model,
            preprocessor=preprocessor,
            prediction_submission=predictions,
            input_dict={'description': description, 'tags': tags},
            custom_metadata={'Team': team_name, 'Moral_Compass': 0} 
        )

        log_output += "\nSUCCESS! Model submitted to the 'Ètica en Joc' leaderboard.\n"

        # G. Refresh & analyze leaderboard
        full_leaderboard_df = playground.get_leaderboard()

        team_summary_df, individual_summary_df, feedback_text, new_accuracy = generate_competitive_summary(
            full_leaderboard_df, 
            team_name, 
            os.environ.get('username') 
        )

        # H. Update rank and UI
        new_submission_count = submission_count + 1
        settings = compute_rank_settings(
            new_submission_count,
            model_name_key,
            complexity_level,
            data_size_level,
            data_to_include
        )

        return (
            log_output, feedback_text, team_summary_df, individual_summary_df, new_accuracy,
            new_submission_count,
            settings["rank_message"],
            gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            gr.update(minimum=1, maximum=settings["size_max"], value=settings["size_value"]),
            gr.update(interactive=settings["features_interactive"], value=settings["features_value"])
        )

    except Exception as e:
        error_msg = f"ERROR: {e}"
        settings = compute_rank_settings(
            submission_count,
            model_name_key,
            complexity_level,
            data_size_level,
            data_to_include
        )
        return (
            log_output + f"\n{error_msg}",
            error_msg,
            pd.DataFrame(),
            pd.DataFrame(),
            last_accuracy,
            submission_count,
            settings["rank_message"],
            gr.update(choices=settings["model_choices"], value=settings["model_value"], interactive=settings["model_interactive"]),
            gr.update(minimum=1, maximum=settings["complexity_max"], value=settings["complexity_value"]),
            gr.update(minimum=1, maximum=settings["size_max"], value=settings["size_value"]),
            gr.update(interactive=settings["features_interactive"], value=settings["features_value"])
        )


def refresh_leaderboard_simple():
    """ 
    Called by 'Refresh' button.
    Returns BOTH summary DataFrames.
    """
    if playground is None:
        return pd.DataFrame(), pd.DataFrame()
    try:
        full_leaderboard_df = playground.get_leaderboard()
        
        team_summary_df, individual_summary_df, _, _ = generate_competitive_summary(
            full_leaderboard_df, 
            CURRENT_TEAM_NAME, 
            os.environ.get('username')
        )
        return team_summary_df, individual_summary_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

def get_model_card(model_name_key):
    """ Returns the description card for the selected model. """
    return MODEL_TYPES.get(model_name_key, {}).get("card", "No description found.")

def on_initial_load(username):
    """
    Called by demo.load() to populate the app on startup.
    """
    team_summary_df, individual_summary_df = refresh_leaderboard_simple() 
    initial_ui = compute_rank_settings(0, DEFAULT_MODEL, 2, 1, [])
    return (
        get_model_card(DEFAULT_MODEL), 
        team_summary_df, 
        individual_summary_df,
        initial_ui["rank_message"],
        gr.update(choices=initial_ui["model_choices"], value=initial_ui["model_value"], interactive=initial_ui["model_interactive"]),
        gr.update(minimum=1, maximum=initial_ui["complexity_max"], value=initial_ui["complexity_value"]),
        gr.update(minimum=1, maximum=initial_ui["size_max"], value=initial_ui["size_value"]),
        gr.update(interactive=initial_ui["features_interactive"], value=initial_ui["features_value"])
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
        background:#fef3c7;
        padding:20px;
        border-radius:16px;
        border:2px solid #f59e0b;
        margin-bottom:18px;
    }
    .leaderboard-box {
        background:#dbeafe;
        padding:20px;
        border-radius:16px;
        border:2px solid #3b82f6;
        margin-top:12px;
    }
    .rank-box {
        background:#e0f2fe;
        padding:16px;
        border-radius:12px;
        border:2px solid #0284c7;
        margin-bottom:16px;
    }
    .log-box textarea {
        font-family: monospace !important;
        font-size: 14px !important;
        line-height: 1.4 !important;
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
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

        # Step 1
        with gr.Column(visible=True) as step_1:
            gr.Markdown("<h1 style='text-align:center;'>🚀 Mission Briefing</h1>")
            gr.HTML(
                f"""
                <div style='font-size:20px; background:#e0f2fe; padding:28px; border-radius:16px; border:2px solid #0284c7;'>
                    <p><b>Welcome, Engineer!</b> You have joined <b>Team: {CURRENT_TEAM_NAME}</b>.</p>
                    <p>Your objective: <b>Build the most accurate prediction model.</b></p>
                    <p>You'll iterate models, submit results, and climb the leaderboard.</p>
                    <div style='background:#fef3c7; padding:16px; border-radius:12px; border-left:6px solid #f59e0b; margin-top:16px;'>
                        <b>Remember:</b> More accuracy often means more trust — but using sensitive data can raise ethical trade-offs.
                    </div>
                </div>
                """
            )
            gr.Markdown(
                """
                <div style='font-size:18px; background:#faf5ff; padding:24px; border-radius:16px; border:2px solid #9333ea;'>
                    <h3 style='margin-top:0;'>🔁 The Experiment Loop</h3>
                    <ul style='font-size:18px;'>
                        <li>Choose a model strategy</li>
                        <li>Adjust complexity & data usage</li>
                        <li>Submit → Get score → Rank up → Unlock more tools</li>
                    </ul>
                    <p style='margin-top:12px;'>Each submission teaches you how changes affect performance.</p>
                </div>
                """
            )
            step_1_next = gr.Button("Begin Model Building ▶️", variant="primary", size="lg")

        # Step 2
        with gr.Column(visible=False) as step_2:
            gr.Markdown("<h1 style='text-align:center;'>🛠️ Model Building Arena</h1>")

            team_name_state = gr.State(CURRENT_TEAM_NAME)
            last_accuracy_state = gr.State(0.0)
            submission_count_state = gr.State(0)

            rank_message_display = gr.Markdown("### Rank loading...")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("<div class='panel-box'><h3 style='margin-top:0;'>1. Model Strategy</h3></div>")
                    model_type_radio = gr.Radio(label="Select Model", choices=[], value=None, interactive=False)

                    model_card_display = gr.Markdown(get_model_card(DEFAULT_MODEL))

                    gr.HTML("<div class='panel-box'><h3 style='margin-top:0;'>2. Model Complexity</h3></div>")
                    complexity_slider = gr.Slider(
                        minimum=1, maximum=2, step=1, value=2,
                        label="Complexity Level",
                        info="Higher may capture deeper patterns; may overfit."
                    )

                    gr.HTML("<div class='panel-box'><h3 style='margin-top:0;'>3. Training Data Size</h3></div>")
                    data_size_slider = gr.Slider(
                        minimum=1, maximum=2, step=1, value=1,
                        label="Data Size Level",
                        info="More data can improve learning but costs time."
                    )

                    gr.HTML("<div class='panel-box'><h3 style='margin-top:0;'>4. Additional Sensitive Data</h3></div>")
                    data_include_checkbox = gr.CheckboxGroup(
                        choices=SENSITIVE_FEATURES,
                        label="Sensitive Features (Unlocks with Rank)",
                        value=[],
                        interactive=False
                    )

                    gr.HTML("<div class='panel-box'><h3 style='margin-top:0;'>5. Submit Experiment</h3></div>")
                    submit_button = gr.Button("🔬 Build & Submit Model", variant="primary", size="lg")

                    experiment_log_display = gr.Textbox(
                        label="Experiment Log",
                        lines=12,
                        interactive=False,
                        elem_classes=["log-box"],
                        placeholder="Detailed run logs will appear here..."
                    )

                with gr.Column(scale=1):
                    gr.HTML(
                        """
                        <div class='leaderboard-box'>
                            <h3 style='margin-top:0;'>🏆 Live Standings</h3>
                            <p style='margin:0;'>Refresh & compare your progress.</p>
                        </div>
                        """
                    )
                    submission_feedback_display = gr.Markdown("Submit a model to see feedback.")

                    with gr.Tabs():
                        with gr.TabItem("Team Standings"):
                            team_leaderboard_display = gr.DataFrame(
                                value=pd.DataFrame(),
                                label="Team Rankings",
                                wrap=True,
                                interactive=False,
                                visible=True
                            )
                        with gr.TabItem("Individual Standings"):
                            individual_leaderboard_display = gr.DataFrame(
                                value=pd.DataFrame(),
                                label="Engineer Rankings",
                                wrap=True,
                                interactive=False,
                                visible=True
                            )

                    refresh_button = gr.Button("🔄 Refresh Leaderboard")

            gr.HTML(
                """
                <div style='background:#fef2f2; padding:20px; border-radius:12px; border-left:6px solid #dc2626; margin-top:24px;'>
                    <b>Ethical Reminder:</b> Accuracy isn't everything. Consider fairness & bias when adding sensitive data.
                </div>
                """
            )
            step_2_next = gr.Button("Finish & Reflect ▶️", variant="secondary")

        # Step 3
        with gr.Column(visible=False) as step_3:
            gr.Markdown("<h1 style='text-align:center;'>✅ Section Complete</h1>")
            gr.HTML(
                """
                <div style='font-size:20px; background:#e0f2fe; padding:28px; border-radius:16px; border:2px solid #0284c7;'>
                    <p><b>Great work!</b> You've experienced iterative model experimentation.</p>
                    <ul style='font-size:18px;'>
                        <li>Model strategy affects baseline performance</li>
                        <li>Complexity trades off bias vs. variance</li>
                        <li>Data size influences stability</li>
                        <li>Sensitive features raise ethical considerations</li>
                    </ul>
                    <div style='background:#faf5ff; padding:16px; border-radius:12px; border:2px solid #9333ea; margin-top:16px;'>
                        <p style='margin:0;'>Scroll down to continue to the next learning section.</p>
                    </div>
                    <h2 style='text-align:center; margin-top:32px;'>👇 SCROLL DOWN 👇</h2>
                </div>
                """
            )
            step_3_back = gr.Button("◀️ Back to Experiment")

        # Navigation
        all_steps = [step_1, step_2, step_3, loading_screen]

        def create_nav(current_step, next_step):
            def _nav():
                updates = {loading_screen: gr.update(visible=True)}
                for s in all_steps:
                    if s != loading_screen:
                        updates[s] = gr.update(visible=False)
                yield updates

                updates = {next_step: gr.update(visible=True)}
                for s in all_steps:
                    if s != next_step:
                        updates[s] = gr.update(visible=False)
                yield updates
            return _nav

        step_1_next.click(
            fn=create_nav(step_1, step_2),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_next.click(
            fn=create_nav(step_2, step_3),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_3_back.click(
            fn=create_nav(step_3, step_2),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )

        # Events
        model_type_radio.change(
            fn=get_model_card,
            inputs=model_type_radio,
            outputs=model_card_display
        )

        submit_button.click(
            fn=run_experiment,
            inputs=[
                model_type_radio,
                complexity_slider,
                data_size_slider,
                data_include_checkbox,
                team_name_state,
                last_accuracy_state,
                submission_count_state,
                gr.State(username)
            ],
            outputs=[
                experiment_log_display,
                submission_feedback_display,
                team_leaderboard_display,
                individual_leaderboard_display,
                last_accuracy_state,
                submission_count_state,
                rank_message_display,
                model_type_radio,
                complexity_slider,
                data_size_slider,
                data_include_checkbox
            ],
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )

        refresh_button.click(
            fn=lambda t, u: refresh_leaderboard(t, u),
            inputs=[team_name_state, gr.State(username)],
            outputs=[team_leaderboard_display, individual_leaderboard_display]
        )

        demo.load(
            fn=lambda u: on_initial_load(u),
            inputs=[gr.State(username)],
            outputs=[
                model_card_display,
                team_leaderboard_display,
                individual_leaderboard_display,
                rank_message_display,
                model_type_radio,
                complexity_slider,
                data_size_slider,
                data_include_checkbox
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

    X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_and_prep_data()
    print("--- Launching App ---")
    app = create_model_building_game_app()
    app.launch(debug=True)

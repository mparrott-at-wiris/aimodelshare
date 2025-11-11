"""
Beginner Mode: Model Building Game (Ètica en Joc) - Justice & Equity Challenge

Purpose:
A simplified, scaffolded version of the full model building app for first-time or low-tech learners.

Differences from the advanced version:
- Fewer initial model choices (Balanced Generalist only → unlock Rule-Maker → unlock all).
- Complexity slider limited to 1–3.
- Training data size simplified to Small (40%) vs Full (100%).
- Sensitive features hidden (only optional 'age' unlock at final rank for discussion).
- Simplified experiment log & reflective summary.
- Guided numbered panels explain each action.
- Reduced cognitive overhead while preserving authentic ML loop.

Ranks:
0: Trainee (Model: Balanced Generalist, Complexity ≤ 2, Size options limited)
1: Junior (Adds Rule-Maker, Complexity ≤ 3, Size Full usable)
2+: Explorer (Unlocks all 4 models + optional Age feature toggle)

Structure:
- Factory function: create_model_building_game_beginner_app()
- Launcher: launch_model_building_game_beginner_app()

"""

import os
import random
import contextlib
from io import StringIO

import numpy as np
import pandas as pd
import requests
import gradio as gr

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

try:
    from aimodelshare.playground import Competition
except ImportError:
    raise ImportError("Install dependencies: pip install aimodelshare aim-widgets")

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
MY_PLAYGROUND_ID = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"

MODEL_TYPES = {
    "The Balanced Generalist": {
        "builder": lambda: LogisticRegression(max_iter=500, random_state=42, class_weight="balanced"),
        "card": "A solid default that learns general patterns. Good first choice."
    },
    "The Rule-Maker": {
        "builder": lambda: DecisionTreeClassifier(random_state=42, class_weight="balanced"),
        "card": "Creates if/then rules. Easy to understand; may miss subtle patterns."
    },
    "The 'Nearest Neighbor'": {
        "builder": lambda: KNeighborsClassifier(),
        "card": "Compares each case to similar past ones. Simple pattern matching."
    },
    "The Deep Pattern-Finder": {
        "builder": lambda: RandomForestClassifier(random_state=42, class_weight="balanced"),
        "card": "Many trees working together. Powerful; can overfit if too complex."
    }
}

DEFAULT_MODEL = "The Balanced Generalist"
TEAM_NAMES = [
    "The Moral Champions", "The Justice League", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]
CURRENT_TEAM_NAME = random.choice(TEAM_NAMES)

BASIC_NUMERIC = [
    "priors_count", "juv_fel_count", "juv_misd_count",
    "juv_other_count", "days_b_screening_arrest"
]
BASIC_CATEGORICAL = ["c_charge_desc"]
OPTIONAL_FEATURE = "age"  # Only unlock at final rank (Explorer)

MAX_ROWS = 3000
TOP_N_CHARGES = 40
np.random.seed(42)

# Globals (initialized at launch)
playground = None
X_TRAIN_RAW = None
X_TEST_RAW = None
Y_TRAIN = None
Y_TEST = None


# ---------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------
def load_and_prep_data():
    url = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"
    df = pd.read_csv(StringIO(requests.get(url).text))

    if df.shape[0] > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42)

    if "c_charge_desc" in df.columns:
        top_vals = df["c_charge_desc"].value_counts().head(TOP_N_CHARGES).index
        df["c_charge_desc"] = df["c_charge_desc"].apply(
            lambda v: v if (isinstance(v, str) and v in top_vals) else "OTHER"
        )

    needed = BASIC_NUMERIC + BASIC_CATEGORICAL + [OPTIONAL_FEATURE]
    for c in needed:
        if c not in df.columns:
            df[c] = np.nan

    X = df[needed]
    y = df["two_year_recid"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    return X_train, X_test, y_train, y_test


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------
def get_model_card(name):
    return MODEL_TYPES.get(name, {}).get("card", "No description available.")


def tune_model(model, complexity_level):
    lvl = int(complexity_level)
    if isinstance(model, LogisticRegression):
        model.C = {1: 0.5, 2: 1.0, 3: 3.0}.get(lvl, 1.0)
    elif isinstance(model, DecisionTreeClassifier):
        model.max_depth = {1: 3, 2: 6, 3: None}.get(lvl, 6)
    elif isinstance(model, RandomForestClassifier):
        model.max_depth = {1: 5, 2: 10, 3: None}.get(lvl, 10)
        model.n_estimators = {1: 30, 2: 60, 3: 100}.get(lvl, 60)
    elif isinstance(model, KNeighborsClassifier):
        model.n_neighbors = {1: 25, 2: 10, 3: 5}.get(lvl, 10)
    return model


def compute_rank_state(submissions, current_model, current_complexity, current_size, include_age):
    """
    Determine unlocked tools based on submission count.
    """
    if submissions == 0:
        return {
            "rank_msg": "### 🧑‍🎓 Rank: Trainee\nSubmit 1 model to unlock a second model.",
            "models": [DEFAULT_MODEL],
            "model_value": DEFAULT_MODEL,
            "model_interactive": False,
            "complexity_max": 2,
            "complexity_value": min(current_complexity, 2),
            "size_choices": ["Small (40%)", "Full (100%)"],
            "size_value": "Small (40%)",
            "age_enabled": False,
            "age_checked": False
        }
    elif submissions == 1:
        return {
            "rank_msg": "### 🚀 Rank Up: Junior\nRule-Maker + Complexity Level 3 unlocked.",
            "models": [DEFAULT_MODEL, "The Rule-Maker"],
            "model_value": current_model if current_model in [DEFAULT_MODEL, "The Rule-Maker"] else DEFAULT_MODEL,
            "model_interactive": True,
            "complexity_max": 3,
            "complexity_value": min(current_complexity, 3),
            "size_choices": ["Small (40%)", "Full (100%)"],
            "size_value": current_size,
            "age_enabled": False,
            "age_checked": False
        }
    else:
        return {
            "rank_msg": "### 🌟 Rank: Explorer\nAll models + optional 'Age' feature unlocked.",
            "models": list(MODEL_TYPES.keys()),
            "model_value": current_model if current_model in MODEL_TYPES else DEFAULT_MODEL,
            "model_interactive": True,
            "complexity_max": 3,
            "complexity_value": current_complexity,
            "size_choices": ["Small (40%)", "Full (100%)"],
            "size_value": current_size,
            "age_enabled": True,
            "age_checked": include_age
        }


def summarize_leaderboard(team_name, username):
    if playground is None:
        return pd.DataFrame(), pd.DataFrame(), "Playground not connected.", 0.0

    try:
        df = playground.get_leaderboard()
        if df is None or df.empty or "accuracy" not in df.columns:
            return pd.DataFrame(), pd.DataFrame(), "No submissions yet.", 0.0

        # Team summary (condensed)
        team_df = pd.DataFrame()
        if "Team" in df.columns:
            team_df = (
                df.groupby("Team")["accuracy"]
                .agg(Best="max", Avg="mean", Subs="count")
                .reset_index()
                .sort_values("Best", ascending=False)
            )
            team_df["Best"] = team_df["Best"].round(4)
            team_df["Avg"] = team_df["Avg"].round(4)

        # Individual summary
        user_best = df.groupby("username")["accuracy"].max().reset_index().rename(columns={"accuracy": "Best"})
        user_best["Best"] = user_best["Best"].round(4)
        user_best = user_best.sort_values("Best", ascending=False).reset_index(drop=True)

        # Feedback
        latest_acc = 0.0
        feedback = "Submit a model to appear on the leaderboard."
        my_subs = df[df["username"] == username].sort_values("timestamp", ascending=False)
        if not my_subs.empty:
            latest_acc = my_subs.iloc[0]["accuracy"]
            feedback = f"Your latest accuracy: {latest_acc:.4f}"
            if len(my_subs) > 1:
                prev = my_subs.iloc[1]["accuracy"]
                diff = latest_acc - prev
                if diff > 0.0001:
                    feedback += f" (Improved +{diff:.4f})"
                elif diff < -0.0001:
                    feedback += f" (Down -{abs(diff):.4f})"
                else:
                    feedback += " (No change)"
        return team_df, user_best, feedback, latest_acc
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), f"Error loading leaderboard: {e}", 0.0


def run_beginner_experiment(
    model_name,
    complexity_level,
    size_choice,
    include_age,
    team_name,
    last_accuracy,
    submissions,
    username
):
    log = f"▶ Experiment\nModel: {model_name}\nComplexity: {complexity_level}\nData Size: {size_choice}\nInclude Age: {'Yes' if include_age else 'No'}\n"

    if playground is None:
        state = compute_rank_state(submissions, model_name, complexity_level, size_choice, include_age)
        return (
            log + "\nERROR: Playground not connected.",
            "Playground connection failed.",
            pd.DataFrame(),
            pd.DataFrame(),
            last_accuracy,
            submissions,
            state["rank_msg"],
            gr.update(choices=state["models"], value=state["model_value"], interactive=state["model_interactive"]),
            gr.update(maximum=state["complexity_max"], value=state["complexity_value"]),
            gr.update(choices=state["size_choices"], value=state["size_value"]),
            gr.update(interactive=state["age_enabled"], value=state["age_checked"])
        )

    try:
        # Data sampling
        frac = 0.4 if "Small" in size_choice else 1.0
        if frac == 1.0:
            X_sample = X_TRAIN_RAW
            y_sample = Y_TRAIN
        else:
            X_sample = X_TRAIN_RAW.sample(frac=frac, random_state=42)
            y_sample = Y_TRAIN.loc[X_sample.index]
        log += f"Rows used: {len(X_sample)} ({int(frac*100)}% of training set)\n"

        # Features
        numeric = list(BASIC_NUMERIC)
        categorical = list(BASIC_CATEGORICAL)
        if include_age:
            numeric.append(OPTIONAL_FEATURE)
        log += f"Features: {', '.join(numeric + categorical)}\n"

        num_tf = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler())
        ])
        cat_tf = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])

        ct = ColumnTransformer([
            ("num", num_tf, numeric),
            ("cat", cat_tf, categorical)
        ])

        X_train_processed = ct.fit_transform(X_sample)
        X_test_processed = ct.transform(X_TEST_RAW)
        log += "Preprocessing complete.\n"

        base = MODEL_TYPES[model_name]["builder"]()
        tuned = tune_model(base, complexity_level)
        tuned.fit(X_train_processed, y_sample)
        log += "Model trained.\n"

        preds = tuned.predict(X_test_processed)
        desc = f"{model_name} (C:{complexity_level} Size:{'Full' if frac==1.0 else 'Small'} Age:{include_age})"
        tags = f"team:{team_name},mode:beginner"

        playground.submit_model(
            model=tuned,
            preprocessor=ct,
            prediction_submission=preds,
            input_dict={"description": desc, "tags": tags},
            custom_metadata={"Team": team_name, "Beginner_Mode": 1}
        )
        log += "Submitted to leaderboard.\n"

        team_df, indiv_df, feedback, latest_acc = summarize_leaderboard(team_name, username)
        new_submissions = submissions + 1
        state = compute_rank_state(new_submissions, model_name, complexity_level, size_choice, include_age)

        reflection = (
            f"### 🔍 What Just Happened?\n"
            f"- You trained: {model_name}\n"
            f"- Complexity setting: {complexity_level}\n"
            f"- Data amount: {'All data' if frac==1.0 else 'Partial data'}\n"
            f"- Optional Age included: {'Yes' if include_age else 'No'}\n\n"
            f"Latest Accuracy: {latest_acc:.4f}\n"
            f"Tip: Try changing one setting at a time to learn cause and effect."
        )

        return (
            log,
            reflection + "\n\n" + feedback,
            team_df,
            indiv_df,
            latest_acc,
            new_submissions,
            state["rank_msg"],
            gr.update(choices=state["models"], value=state["model_value"], interactive=state["model_interactive"]),
            gr.update(maximum=state["complexity_max"], value=state["complexity_value"]),
            gr.update(choices=state["size_choices"], value=state["size_value"]),
            gr.update(interactive=state["age_enabled"], value=state["age_checked"])
        )

    except Exception as e:
        err = f"ERROR: {e}"
        state = compute_rank_state(submissions, model_name, complexity_level, size_choice, include_age)
        return (
            log + err,
            err,
            pd.DataFrame(),
            pd.DataFrame(),
            last_accuracy,
            submissions,
            state["rank_msg"],
            gr.update(choices=state["models"], value=state["model_value"], interactive=state["model_interactive"]),
            gr.update(maximum=state["complexity_max"], value=state["complexity_value"]),
            gr.update(choices=state["size_choices"], value=state["size_value"]),
            gr.update(interactive=state["age_enabled"], value=state["age_checked"])
        )


def initial_load(username):
    team_df, indiv_df, feedback, _ = summarize_leaderboard(CURRENT_TEAM_NAME, username)
    state = compute_rank_state(0, DEFAULT_MODEL, 2, "Small (40%)", False)
    return (
        get_model_card(DEFAULT_MODEL),
        team_df,
        indiv_df,
        state["rank_msg"],
        gr.update(choices=state["models"], value=state["model_value"], interactive=state["model_interactive"]),
        gr.update(maximum=state["complexity_max"], value=state["complexity_value"]),
        gr.update(choices=state["size_choices"], value=state["size_value"]),
        gr.update(interactive=state["age_enabled"], value=state["age_checked"])
    )


# ---------------------------------------------------------------------
# Gradio App Factory
# ---------------------------------------------------------------------
def create_model_building_game_beginner_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    css = """
    .panel {
        background:#fff;
        padding:18px;
        border-radius:16px;
        border:2px solid #e5e7eb;
        margin-bottom:16px;
    }
    .highlight-box {
        background:#e0f2fe;
        padding:18px;
        border-radius:12px;
        border:2px solid #0284c7;
    }
    .log-box textarea {
        font-family: monospace !important;
        font-size: 13px !important;
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        username = os.environ.get("username") or "New_User"

        # Loading screen
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding:80px 0;'>
                  <h2 style='color:#6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )

        # Step 1: Intro
        with gr.Column(visible=True) as step_1:
            gr.Markdown("<h1 style='text-align:center;'>🎯 Beginner Mode: Your First AI Experiments</h1>")
            gr.HTML(
                f"""
                <div class='highlight-box'>
                  <p><b>Welcome!</b> You joined <b>Team: {CURRENT_TEAM_NAME}</b>.</p>
                  <p>This simplified mode helps you learn the experiment loop step-by-step.</p>
                  <ul style='font-size:16px;'>
                    <li>Pick a model strategy</li>
                    <li>Set complexity</li>
                    <li>Choose how much data to use</li>
                    <li>Submit & observe the leaderboard</li>
                  </ul>
                  <p style='margin-top:10px;'>You will unlock more tools by submitting models.</p>
                </div>
                """
            )
            step_1_next = gr.Button("Start Building ▶️", variant="primary", size="lg")

        # Step 2: Main Workspace
        with gr.Column(visible=False) as step_2:
            gr.Markdown("<h1 style='text-align:center;'>🛠️ Build a Model</h1>")
            rank_message_display = gr.Markdown("Rank loading...")

            # Hidden states
            team_state = gr.State(CURRENT_TEAM_NAME)
            last_acc_state = gr.State(0.0)
            submissions_state = gr.State(0)

            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Box():
                        gr.Markdown("### 1️⃣ Choose Model")
                        model_radio = gr.Radio(label="Model", choices=[], interactive=False)
                        model_card = gr.Markdown(get_model_card(DEFAULT_MODEL))

                    with gr.Box():
                        gr.Markdown("### 2️⃣ Set Complexity")
                        complexity_slider = gr.Slider(
                            minimum=1, maximum=2, step=1, value=2,
                            label="Complexity",
                            info="Higher = deeper patterns, but risk of overfitting."
                        )

                    with gr.Box():
                        gr.Markdown("### 3️⃣ Data Size")
                        size_radio = gr.Radio(
                            choices=["Small (40%)", "Full (100%)"],
                            value="Small (40%)",
                            label="Training Data Amount"
                        )

                    with gr.Box():
                        gr.Markdown("### 4️⃣ Optional Feature (Ethics)")
                        age_checkbox = gr.Checkbox(label="Include Age Feature", value=False, interactive=False)
                        gr.Markdown(
                            "> Age can improve accuracy but raises fairness concerns. Use thoughtfully."
                        )

                    with gr.Box():
                        gr.Markdown("### 5️⃣ Submit")
                        submit_btn = gr.Button("🔬 Train & Submit", variant="primary")
                        experiment_log = gr.Textbox(
                            label="Run Log",
                            lines=10,
                            interactive=False,
                            elem_classes=["log-box"],
                            placeholder="Your experiment steps will appear here..."
                        )
                        show_details = gr.Checkbox(label="Show Technical Details", value=False)
                        details_box = gr.Markdown(visible=False)

                with gr.Column(scale=1):
                    gr.Markdown("### 📊 Feedback & Leaderboards")
                    feedback_md = gr.Markdown("Submit a model to see feedback.")
                    team_table = gr.DataFrame(value=pd.DataFrame(), label="Team Summary", interactive=False)
                    indiv_table = gr.DataFrame(value=pd.DataFrame(), label="Engineer Summary", interactive=False)
                    refresh_btn = gr.Button("🔄 Refresh Leaderboard")

            step_2_next = gr.Button("Finish & Reflect ▶️", variant="secondary")

        # Step 3: Completion
        with gr.Column(visible=False) as step_3:
            gr.Markdown("<h1 style='text-align:center;'>✅ Beginner Section Complete</h1>")
            gr.HTML(
                """
                <div class='highlight-box'>
                  <p><b>Great job!</b> You now understand the core experiment loop:</p>
                  <ol style='font-size:16px;'>
                    <li>Pick a model strategy</li>
                    <li>Adjust complexity / data amount</li>
                    <li>Submit and observe accuracy</li>
                    <li>Iterate to improve</li>
                  </ol>
                  <p>Next: Try Advanced Mode or explore ethical trade-offs in later sections.</p>
                  <h2 style='text-align:center;'>👇 SCROLL DOWN FOR NEXT SECTION 👇</h2>
                </div>
                """
            )
            step_3_back = gr.Button("◀️ Back to Workspace")

        # Navigation logic
        all_steps = [step_1, step_2, step_3, loading_screen]

        def nav(to_show, from_show):
            def _go():
                updates = {loading_screen: gr.update(visible=True)}
                for s in all_steps:
                    if s != loading_screen:
                        updates[s] = gr.update(visible=False)
                yield updates

                updates = {to_show: gr.update(visible=True)}
                for s in all_steps:
                    if s != to_show:
                        updates[s] = gr.update(visible=False)
                yield updates
            return _go

        step_1_next.click(
            fn=nav(step_2, step_1),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_next.click(
            fn=nav(step_3, step_2),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_3_back.click(
            fn=nav(step_2, step_3),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )

        # Interactions
        model_radio.change(get_model_card, model_radio, model_card)

        def toggle_details(show):
            if not show:
                return gr.update(visible=False, value="")
            tech_md = """
            ### 🧪 Technical Details
            - Preprocessing: Numeric → Median Impute + StandardScaler; Categorical → Constant Impute + OneHot
            - Metric: Accuracy (correct predictions / total)
            - Models available: LogisticRegression, DecisionTree, KNN, RandomForest (phased unlock)
            """
            return gr.update(visible=True, value=tech_md)

        show_details.change(toggle_details, show_details, details_box)

        submit_btn.click(
            fn=run_beginner_experiment,
            inputs=[
                model_radio,
                complexity_slider,
                size_radio,
                age_checkbox,
                team_state,
                last_acc_state,
                submissions_state,
                gr.State(username)
            ],
            outputs=[
                experiment_log,
                feedback_md,
                team_table,
                indiv_table,
                last_acc_state,
                submissions_state,
                rank_message_display,
                model_radio,
                complexity_slider,
                size_radio,
                age_checkbox
            ],
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )

        refresh_btn.click(
            fn=lambda tm, u: summarize_leaderboard(tm, u)[:2],
            inputs=[team_state, gr.State(username)],
            outputs=[team_table, indiv_table]
        )

        # Initial load
        demo.load(
            fn=lambda u: initial_load(u),
            inputs=[gr.State(username)],
            outputs=[
                model_card,
                team_table,
                indiv_table,
                rank_message_display,
                model_radio,
                complexity_slider,
                size_radio,
                age_checkbox
            ]
        )

    return demo


# ---------------------------------------------------------------------
# Launcher
# ---------------------------------------------------------------------
def launch_model_building_game_beginner_app(height: int = 1100, share: bool = False, debug: bool = False):
    global playground, X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST
    if playground is None:
        try:
            playground = Competition(MY_PLAYGROUND_ID)
        except Exception as e:
            print(f"WARNING: Could not connect to playground: {e}")
            playground = None

    if X_TRAIN_RAW is None:
        X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_and_prep_data()

    app = create_model_building_game_beginner_app()
    with contextlib.redirect_stdout(open(os.devnull, "w")), contextlib.redirect_stderr(open(os.devnull, "w")):
        app.launch(share=share, inline=True, debug=debug, height=height)


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("Initializing Beginner Mode...")
    try:
        playground = Competition(MY_PLAYGROUND_ID)
        print("Playground connected.")
    except Exception as e:
        print(f"Playground connection failed: {e}")
        playground = None

    X_TRAIN_RAW, X_TEST_RAW, Y_TRAIN, Y_TEST = load_and_prep_data()
    print("Launching Beginner Mode App...")
    create_model_building_game_beginner_app().launch(debug=True)

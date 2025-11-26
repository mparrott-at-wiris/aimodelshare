import os
import time
import pytest
import pandas as pd
import gradio as gr

from aimodelshare.moral_compass.apps import model_building_game as app
from aimodelshare.aws import get_token_from_session, _get_username_from_token

WAIT_READY_TIMEOUT_SEC = 180
LEADERBOARD_POLL_TRIES = 8
LEADERBOARD_POLL_SLEEP_SEC = 1.0

def wait_for_ready(timeout_sec=WAIT_READY_TIMEOUT_SEC):
    start = time.time()
    while time.time() - start < timeout_sec:
        with app.INIT_LOCK:
            flags = app.INIT_FLAGS.copy()
        if flags.get("competition") and flags.get("dataset_core") and flags.get("pre_samples_small"):
            return True
        time.sleep(1.0)
    return False

def fetch_leaderboard(token):
    # Uses the app’s helper which applies retry and the configured Competition in app.playground
    return app._get_leaderboard_with_optional_token(app.playground, token)

def get_user_metrics(df, username):
    """
    Compute (latest_submission_score, best_accuracy, rank) from a leaderboard DataFrame.
    - latest score: last by timestamp (parsed), falling back to last row for the user
    - best_accuracy: max accuracy across user's submissions
    - rank: position of the user's best in sorted unique-user bests (1-based); 0 if absent
    """
    latest_score = 0.0
    best_acc = 0.0
    rank = 0

    if df is None or df.empty or "accuracy" not in df.columns:
        return latest_score, best_acc, rank

    user_rows = df[df["username"] == username].copy()
    if not user_rows.empty:
        # Best accuracy
        best_acc = float(user_rows["accuracy"].max())
        # Latest score by timestamp if possible
        if "timestamp" in user_rows.columns:
            parsed = pd.to_datetime(user_rows["timestamp"], errors="coerce")
            if parsed.notna().any():
                user_rows["__t"] = parsed
                user_rows = user_rows.sort_values("__t", ascending=False)
                latest_score = float(user_rows.iloc[0]["accuracy"])
            else:
                latest_score = float(user_rows.iloc[-1]["accuracy"])
        else:
            latest_score = float(user_rows.iloc[-1]["accuracy"])

    # Rank among users by best
    if "accuracy" in df.columns:
        user_bests = df.groupby("username")["accuracy"].max()
        ranked = user_bests.sort_values(ascending=False)
        try:
            rank = int(ranked.index.get_loc(username) + 1)
        except KeyError:
            rank = 0

    return latest_score, best_acc, rank

def parse_kpi(html: str):
    out = {}
    if not isinstance(html, str):
        return out
    # Title in <h2>...</h2>
    if "<h2" in html:
        start = html.find("<h2")
        end = html.find("</h2>", start)
        out["title"] = html[start:end].split(">")[-1]
    # Accuracy text
    acc_idx = html.find("New Accuracy")
    if acc_idx != -1:
        score_idx = html.find("kpi-score", acc_idx)
        pct_start = html.find(">", score_idx) + 1
        pct_end = html.find("</", pct_start)
        out["acc_text"] = html[pct_start:pct_end]
    # Rank text
    rank_idx = html.find("Your Rank")
    if rank_idx != -1:
        score_idx = html.find("kpi-score", rank_idx)
        val_start = html.find(">", score_idx) + 1
        val_end = html.find("</", val_start)
        out["rank_text"] = html[val_start:val_end]
    return out

def consume_run_experiment_once(
    username, token, team_name,
    model_name_key, complexity_level, feature_set, data_size_str,
    last_submission_score, last_rank, submission_count, first_submission_score, best_score
):
    """
    Drive one run_experiment call to completion (perform a real submission),
    but do not attempt to read the yielded UI mapping (component keys are None outside Blocks).
    """
    gen = app.run_experiment(
        model_name_key,
        complexity_level,
        feature_set,
        data_size_str,
        team_name,
        last_submission_score,
        last_rank,
        submission_count,
        first_submission_score,
        best_score,
        username=username,
        token=token,
        progress=gr.Progress()
    )
    # Exhaust generator
    for _ in gen:
        pass

@pytest.mark.timeout(600)
def test_sessionid_kpi_integration_flow():
    # 1) Real auth from SESSION_ID
    session_id = os.getenv("SESSION_ID")
    assert session_id, "SESSION_ID GitHub Action secret must be set (Settings → Secrets → Actions)."

    token = get_token_from_session(session_id)
    assert token, "Failed to obtain token from SESSION_ID."
    username = _get_username_from_token(token)
    assert username, "Failed to obtain username from token."

    # 2) Ensure playground exists and background init is running
    if app.playground is None:
        app.playground = app.Competition(app.MY_PLAYGROUND_ID)
    app.start_background_init()
    assert wait_for_ready(), "App did not become ready in time."

    # 3) Resolve team
    team_name, _ = app.get_or_assign_team(username, token=token)
    assert isinstance(team_name, str) and team_name.strip(), "Could not resolve team name."

    # 4) Baseline leaderboard metrics for user
    df0 = fetch_leaderboard(token) or pd.DataFrame()
    base_rows = len(df0[df0.get("username", pd.Series(dtype=str)) == username]) if not df0.empty else 0
    last_score0, best0, rank0 = get_user_metrics(df0, username)

    # 5) Run first authenticated submission (session perspective: submission_count=0)
    model_name_key = app.DEFAULT_MODEL
    complexity_level = 2
    feature_set = app.DEFAULT_FEATURE_SET
    data_size_str = "Small (20%)"

    consume_run_experiment_once(
        username, token, team_name,
        model_name_key, complexity_level, feature_set, data_size_str,
        last_submission_score=last_score0, last_rank=rank0, submission_count=0,
        first_submission_score=None, best_score=best0
    )

    # Poll until a new row appears for the user
    df1 = df0
    for _ in range(LEADERBOARD_POLL_TRIES):
        df1 = fetch_leaderboard(token) or pd.DataFrame()
        rows1 = len(df1[df1.get("username", pd.Series(dtype=str)) == username]) if not df1.empty else 0
        if rows1 > base_rows:
            break
        time.sleep(LEADERBOARD_POLL_SLEEP_SEC)

    rows1 = 0 if df1 is None or df1.empty else len(df1[df1["username"] == username])
    assert rows1 > base_rows, "First submission did not appear on leaderboard."

    # Compute metrics and KPI HTML from fresh leaderboard
    last_score1, best1, rank1 = get_user_metrics(df1, username)
    team_html_1, indev_html_1, kpi_html_1, new_best_1, new_rank_1, this_score_1 = app.generate_competitive_summary(
        df1, team_name, username, last_submission_score=last_score0, last_rank=rank0, submission_count=0
    )
    p1 = parse_kpi(kpi_html_1)
    assert isinstance(kpi_html_1, str) and len(kpi_html_1) > 0, "KPI HTML missing after first submission."
    # Accept either first-submission or general success title (depends on session history vs global history)
    assert ("First Model Submitted" in p1.get("title", "")) or ("Submission Successful" in p1.get("title", ""))

    # 6) Run second authenticated submission (submission_count=1)
    consume_run_experiment_once(
        username, token, team_name,
        model_name_key, complexity_level, feature_set, data_size_str,
        last_submission_score=last_score1, last_rank=rank1, submission_count=1,
        first_submission_score=this_score_1, best_score=new_best_1
    )

    # Poll for second new row
    df2 = df1
    for _ in range(LEADERBOARD_POLL_TRIES):
        df2 = fetch_leaderboard(token) or pd.DataFrame()
        rows2 = len(df2[df2.get("username", pd.Series(dtype=str)) == username]) if not df2.empty else 0
        if rows2 > rows1:
            break
        time.sleep(LEADERBOARD_POLL_SLEEP_SEC)

    rows2 = 0 if df2 is None or df2.empty else len(df2[df2["username"] == username])
    assert rows2 > rows1, "Second submission did not appear on leaderboard."

    last_score2, best2, rank2 = get_user_metrics(df2, username)
    team_html_2, indev_html_2, kpi_html_2, new_best_2, new_rank_2, this_score_2 = app.generate_competitive_summary(
        df2, team_name, username, last_submission_score=last_score1, last_rank=rank1, submission_count=1
    )
    p2 = parse_kpi(kpi_html_2)
    assert isinstance(kpi_html_2, str) and len(kpi_html_2) > 0, "KPI HTML missing after second submission."
    assert ("Submission Successful" in p2.get("title", "")) or ("Score Dropped" in p2.get("title", "")), \
        "Second KPI should indicate a real submission result."

    # Sanity checks across the two submissions
    assert kpi_html_1 != kpi_html_2, "KPI HTML should change between submissions."
    # Rank format sanity
    assert p2.get("rank_text", "").startswith("#") or p2.get("rank_text") == "N/A"

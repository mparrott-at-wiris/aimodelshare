import os
import time
import pytest

import numpy as np
import pandas as pd

import gradio as gr

from aimodelshare.moral_compass.apps import model_building_game as app

# Integration settings
WAIT_READY_TIMEOUT_SEC = 120    # max time to wait for init readiness
LEADERBOARD_SETTLE_SEC = 2.0    # allow server-side leaderboard to update
SLEEP_BETWEEN_SUBMISSIONS_SEC = 2.0

def wait_for_ready():
    """Poll the app INIT_FLAGS until competition/data/pre_samples_small are ready."""
    start = time.time()
    while time.time() - start < WAIT_READY_TIMEOUT_SEC:
        with app.INIT_LOCK:
            flags = app.INIT_FLAGS.copy()
        ready = flags.get("competition") and flags.get("dataset_core") and flags.get("pre_samples_small")
        if ready:
            return True
        time.sleep(1.0)
    return False

def parse_kpi(html: str):
    out = {}
    # Title
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

@pytest.mark.timeout(300)
def test_sessionid_kpi_integration_flow():
    """
    Full integration test:
    - Get token from SESSION_ID.
    - Wait for app readiness.
    - Run two authenticated submissions via run_experiment.
    - Verify KPI card transitions: first submission vs subsequent submission.
    """
    session_id = os.getenv("SESSION_ID")
    assert session_id, "SESSION_ID GitHub Action secret must be set."

    # Get token and username via aimodelshare
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
    token = get_token_from_session(session_id)
    assert token, "Failed to derive token from SESSION_ID."
    username = _get_username_from_token(token)
    assert username, "Failed to derive username from token."

    # Start background init (if not already started)
    app.start_background_init()

    # Wait for readiness
    assert wait_for_ready(), "App did not become ready in time."

    # Determine a team name for the user (using leaderboard or assign)
    team_name, _ = app.get_or_assign_team(username, token=token)
    assert team_name and isinstance(team_name, str), "Could not resolve team name."

    # Prepare initial session KPI states (as in the app)
    last_submission_score = 0.0
    last_rank = 0
    submission_count = 0
    first_submission_score = None
    best_score = 0.0

    # Choose conservative settings for speed and predictability
    model_name_key = app.DEFAULT_MODEL  # "The Balanced Generalist" (LogisticRegression)
    complexity_level = 2                # low complexity
    feature_set = app.DEFAULT_FEATURE_SET  # initial allowed features
    data_size_str = "Small (20%)"       # smallest sample for speed

    # Build the run_experiment generator inputs (matching app wiring)
    def run_once():
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
        last_update = None
        for updates in gen:
            last_update = updates
        return last_update

    # First authenticated submission
    updates1 = run_once()
    assert isinstance(updates1, dict), "Expected a dict of final updates from run_experiment."
    # Extract KPI and states
    kpi_html_1 = updates1.get(app.submission_feedback_display)
    rank_message_1 = updates1.get(app.rank_message_display)
    last_submission_score = updates1.get(app.last_submission_score_state, last_submission_score)
    last_rank = updates1.get(app.last_rank_state, last_rank)
    best_score = updates1.get(app.best_score_state, best_score)
    submission_count = updates1.get(app.submission_count_state, submission_count)
    first_submission_score = updates1.get(app.first_submission_score_state, first_submission_score)

    assert submission_count >= 1, "Submission count should increment after authenticated submission."
    assert isinstance(kpi_html_1, str) and len(kpi_html_1) > 0, "KPI HTML should be present."

    parsed1 = parse_kpi(kpi_html_1)
    # For a genuine first submission within the session, expect first-submission KPI title
    assert ("First Model Submitted" in parsed1.get("title", "")) or ("Submission Successful" in parsed1.get("title", "")), \
        "KPI title should indicate a successful first submission."

    # Small settle pause
    time.sleep(LEADERBOARD_SETTLE_SEC)

    # Second authenticated submission (same settings; state comparisons should reflect change or neutrality)
    updates2 = run_once()
    assert isinstance(updates2, dict), "Expected a dict of final updates from second run_experiment."

    kpi_html_2 = updates2.get(app.submission_feedback_display)
    last_submission_score_2 = updates2.get(app.last_submission_score_state, last_submission_score)
    last_rank_2 = updates2.get(app.last_rank_state, last_rank)
    best_score_2 = updates2.get(app.best_score_state, best_score)
    submission_count_2 = updates2.get(app.submission_count_state, submission_count)

    assert submission_count_2 == submission_count + 1, "Submission count should increment again."

    parsed2 = parse_kpi(kpi_html_2)
    assert isinstance(kpi_html_2, str) and len(kpi_html_2) > 0, "Second KPI HTML should be present."

    # The title should be a general success or reflect score change
    assert ("Submission Successful" in parsed2.get("title", "")) or ("Score Dropped" in parsed2.get("title", "")) or ("Successful Preview Run" not in parsed2.get("title", "")), \
        "Second KPI should indicate a real submission result, not a preview."

    # Basic sanity on rank formatting
    assert parsed2.get("rank_text", "").startswith("#") or parsed2.get("rank_text") == "N/A", "Rank text should be formatted."

    # At least ensure KPI changed across submissions
    assert kpi_html_2 != kpi_html_1, "KPI card content should change between submissions."

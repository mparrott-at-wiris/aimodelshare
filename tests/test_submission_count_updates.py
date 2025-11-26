import time
import inspect
import traceback
import pytest
import pandas as pd
import gradio as gr

from aimodelshare.moral_compass.apps import model_building_game as app

class MockCompetition:
    def __init__(self, pid):
        self.pid = pid
        self.submissions = []
    def submit_model(self, *args, **kwargs):
        # Simulate successful submission that is immediately visible
        self.submissions.append({
            "username": kwargs.get("custom_metadata", {}).get("Team", "tester_team"),
            "timestamp": time.time()
        })
        return True
    def get_leaderboard(self, token=None):
        # Return a leaderboard with fields used by generate_competitive_summary
        # For count/visibility assertions, we craft a simple DF each call.
        # Note: We do not derive username or accuracy here; run_experiment uses real evaluation to compute KPI.
        data = []
        # Simulate a single user with incremental submissions; accuracy is not critical for this test
        for i, rec in enumerate(self.submissions, start=1):
            data.append({"username": "tester", "accuracy": 0.50 + (i * 0.01), "Team": "The Ethical Explorers", "timestamp": rec["timestamp"]})
        return pd.DataFrame(data, columns=["username", "accuracy", "Team", "timestamp"])

@pytest.fixture(autouse=True)
def patch_playground(monkeypatch):
    mock_comp = MockCompetition("test-pid")
    monkeypatch.setattr(app, "Competition", lambda pid: mock_comp)
    # Set the global playground to use our mock
    app.playground = mock_comp

    # Mark app as ready to avoid preview gating unless we want to test preview explicitly
    with app.INIT_LOCK:
        app.INIT_FLAGS.update({
            "competition": True,
            "dataset_core": True,
            "pre_samples_small": True,
            "pre_samples_medium": True,
            "pre_samples_large": True,
            "pre_samples_full": True,
            "leaderboard": True,
            "default_preprocessor": True,
            "warm_mini": True,
            "errors": []
        })

    # Minimal training sample maps to avoid None refs
    if "Small (20%)" not in app.X_TRAIN_SAMPLES_MAP:
        num_cols = app.ALL_NUMERIC_COLS
        cat_cols = app.ALL_CATEGORICAL_COLS
        X_df = pd.DataFrame({c: [0, 1, 2, 3] for c in num_cols})
        for c in cat_cols:
            X_df[c] = ["A", "B", "A", "C"]
        y_series = pd.Series([0, 1, 0, 1], name="two_year_recid")
        app.X_TRAIN_SAMPLES_MAP["Small (20%)"] = X_df
        app.Y_TRAIN_SAMPLES_MAP["Small (20%)"] = y_series
        app.X_TRAIN_SAMPLES_MAP[app.DEFAULT_DATA_SIZE] = X_df
        app.Y_TRAIN_SAMPLES_MAP[app.DEFAULT_DATA_SIZE] = y_series

    if app.X_TEST_RAW is None:
        app.X_TEST_RAW = app.X_TRAIN_SAMPLES_MAP[app.DEFAULT_DATA_SIZE].copy()
    if app.Y_TEST is None:
        app.Y_TEST = app.Y_TRAIN_SAMPLES_MAP[app.DEFAULT_DATA_SIZE].copy()

    # Create mock component objects to avoid None-key collisions in update dicts
    # When components are None, all updates use None as key and only last value survives
    app.submit_button = object()
    app.submission_feedback_display = object()
    app.team_leaderboard_display = object()
    app.individual_leaderboard_display = object()
    app.last_submission_score_state = object()
    app.last_rank_state = object()
    app.best_score_state = object()
    app.submission_count_state = object()
    app.first_submission_score_state = object()
    app.rank_message_display = object()
    app.model_type_radio = object()
    app.complexity_slider = object()
    app.feature_set_checkbox = object()
    app.data_size_radio = object()
    app.login_username = object()
    app.login_password = object()
    app.login_submit = object()
    app.login_error = object()
    app.attempts_tracker_display = object()
    app.was_preview_state = object()
    app.kpi_meta_state = object()

    yield

def _run_to_last_updates(username, token, submission_count=0, readiness_flag=True, preview_mode=True):
    """
    Run app.run_experiment once and return the final updates dict.
    """
    model_name_key = app.DEFAULT_MODEL
    complexity_level = 2
    feature_set = ["age", "race", "sex", "priors_count"]
    data_size_str = app.DEFAULT_DATA_SIZE
    team_name = "The Ethical Explorers"

    # Build args to match current signature dynamically
    sig = inspect.signature(app.run_experiment)
    params = list(sig.parameters.keys())

    args = [
        model_name_key,
        complexity_level,
        feature_set,
        data_size_str,
        team_name,
        0.0,             # last_submission_score
        0,               # last_rank
        submission_count,
        None,            # first_submission_score
        0.0,             # best_score
        username,
        token,
    ]
    if "readiness_flag" in params:
        args.append(readiness_flag)
    if "preview_mode_flag" in params:
        args.append(preview_mode)
    if "was_preview_prev" in params:
        args.append(False)
    if "kpi_meta_prev" in params:
        args.append({})

    gen = app.run_experiment(*args, progress=gr.Progress())
    last = None
    for updates in gen:
        last = updates
    return last or {}

def _extract_submission_count(updates):
    # submission_count_state is a component; in updates dict, it maps to a raw value
    return updates.get(app.submission_count_state, None)

def test_submission_count_increments_on_authenticated_submission():
    """
    When the app is ready and a valid token is provided, submission_count_state should increment by 1 per run.
    """
    username = "tester"
    token = "dummy-token"

    # First run (starting at 0)
    updates1 = _run_to_last_updates(username, token, submission_count=0, readiness_flag=True)
    count1 = _extract_submission_count(updates1)
    assert isinstance(count1, int), f"submission_count_state should be int, got {type(count1)}"
    assert count1 == 1, f"Expected 1 after first authenticated submission, got {count1}"

    # Second run (starting at 1)
    updates2 = _run_to_last_updates(username, token, submission_count=count1, readiness_flag=True)
    count2 = _extract_submission_count(updates2)
    assert count2 == 2, f"Expected 2 after second authenticated submission, got {count2}"

def test_submission_count_does_not_increment_on_preview():
    """
    If token is None (unauthenticated), the run should display a preview and not increment submission_count_state.
    """
    username = "tester"
    token = None  # unauthenticated

    updates = _run_to_last_updates(username, token, submission_count=0, readiness_flag=True)
    count = _extract_submission_count(updates)
    assert count == 0, f"Preview runs should not increment submission_count; got {count}"

def test_submission_count_does_not_increment_when_not_ready_and_preview_disabled():
    """
    If readiness_flag is False and preview_mode_flag is False, run should exit with gating message and not increment count.
    """
    username = "tester"
    token = "dummy-token"

    # Force not ready and disable preview
    updates = _run_to_last_updates(username, token, submission_count=0, readiness_flag=False, preview_mode=False)
    count = _extract_submission_count(updates)
    assert count == 0, f"Not-ready/no-preview runs should not increment submission_count; got {count}"

def test_attempt_limit_blocks_increment():
    """
    If submission_count >= ATTEMPT_LIMIT before run, ensure it does not increment and UI returns limit reached.
    """
    username = "tester"
    token = "dummy-token"

    starting = app.ATTEMPT_LIMIT
    updates = _run_to_last_updates(username, token, submission_count=starting, readiness_flag=True)
    count = _extract_submission_count(updates)
    # Should remain at ATTEMPT_LIMIT
    assert count == starting, f"Count should not increase past attempt limit ({app.ATTEMPT_LIMIT}); got {count}"

def test_first_submission_score_is_set_on_first_authenticated_run():
    """
    first_submission_score_state should be set on the first authenticated submission when previously None.
    """
    username = "tester"
    token = "dummy-token"

    updates = _run_to_last_updates(username, token, submission_count=0, readiness_flag=True)
    first_score = updates.get(app.first_submission_score_state, None)
    assert first_score is not None, "first_submission_score_state must be set on first authenticated submission"

def test_submission_count_state_type_and_consistency_across_runs():
    """
    Ensure submission_count_state remains an int across multiple runs and is not replaced by a dict/other type.
    """
    username = "tester"
    token = "dummy-token"

    count = 0
    for i in range(3):
        updates = _run_to_last_updates(username, token, submission_count=count, readiness_flag=True)
        count_new = _extract_submission_count(updates)
        assert isinstance(count_new, int), f"submission_count_state type drift at run {i}: got {type(count_new)}"
        assert count_new == count + 1, f"Inconsistent increment at run {i}: expected {count+1}, got {count_new}"
        count = count_new

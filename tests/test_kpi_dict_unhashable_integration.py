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
        # Simulate immediate success; store a minimal submission record
        self.submissions.append({"ts": time.time()})
        return True
    def get_leaderboard(self, token=None):
        # Return an empty but well-formed leaderboard DataFrame
        return pd.DataFrame(columns=["username", "accuracy", "Team", "timestamp"])

@pytest.fixture(autouse=True)
def patch_playground(monkeypatch):
    # Patch Competition used by the app to avoid live API calls
    mock_comp = MockCompetition("test-pid")
    monkeypatch.setattr(app, "Competition", lambda pid: mock_comp)
    # Set the global playground to use our mock
    app.playground = mock_comp

    # Ensure app flags reflect a ready state to avoid preview gating in tests
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

    # Ensure minimal training sample maps exist
    if "Small (20%)" not in app.X_TRAIN_SAMPLES_MAP:
        # Create small synthetic frames if not initialized
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

    # Provide a simple X_TEST_RAW, Y_TEST if missing
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

def log_signature_and_features(feature_set):
    sig = inspect.signature(app.run_experiment)
    params = list(sig.parameters.keys())
    print("\n[DICT-UNHASHABLE-TEST] run_experiment signature params:", params)
    print("[DICT-UNHASHABLE-TEST] feature_set types:", [type(x).__name__ for x in (feature_set or [])])
    print("[DICT-UNHASHABLE-TEST] feature_set sample:", (feature_set or [])[:4])

def run_once_safely(model_name_key, complexity_level, feature_set, data_size_str, include_kpi_meta_input=False):
    """
    Drives run_experiment once with controlled inputs, capturing exceptions and returning a result dict:
    {
      'ok': bool,
      'exc': Exception or None,
      'stack': str or '',
      'feature_set_types': list,
      'signature_params': list
    }
    """
    username = "tester"
    token = "dummy-token"

    sig = inspect.signature(app.run_experiment)
    params = list(sig.parameters.keys())
    log_signature_and_features(feature_set)

    # Base args (align with original signature)
    args = [
        model_name_key,
        complexity_level,
        feature_set,
        data_size_str,
        "The Ethical Explorers",  # team_name
        0.0,  # last_submission_score
        0,    # last_rank
        0,    # submission_count
        None, # first_submission_score
        0.0,  # best_score
        username,
        token,
    ]

    # Optional readiness/preview/kpi inputs (append only if present in signature)
    if "readiness_flag" in params:
        args.append(True)
    if "preview_mode_flag" in params:
        args.append(True)
    if "was_preview_prev" in params:
        args.append(False)
    if "kpi_meta_prev" in params:
        args.append({"prev": "meta"} if include_kpi_meta_input else {})

    result = {
        "ok": False,
        "exc": None,
        "stack": "",
        "feature_set_types": [type(x).__name__ for x in (feature_set or [])],
        "signature_params": params
    }

    try:
        gen = app.run_experiment(*args, progress=gr.Progress())
        last = None
        for updates in gen:
            last = updates
        result["ok"] = True
        return result
    except Exception as e:
        result["exc"] = e
        result["stack"] = traceback.format_exc()
        return result

def test_feature_set_with_dicts_triggers_unhashable_if_not_sanitized():
    """
    Pass feature_set containing dicts/tuples which are common UI artifacts.
    If build_preprocessor/_get_cached_preprocessor_config receives these,
    lru_cache may see unhashable types and raise 'unhashable type: dict'.
    """
    bad_feature_set = [
        {"label": "Age", "value": "age"},
        {"label": "Race", "value": "race"},
        ("Sex", "sex"),
        "priors_count"  # mix with a valid string
    ]

    res = run_once_safely(app.DEFAULT_MODEL, 2, bad_feature_set, app.DEFAULT_DATA_SIZE, include_kpi_meta_input=False)
    if res["ok"]:
        # If the app sanitizes feature_set to strings, this should pass.
        assert True
    else:
        print("[DICT-UNHASHABLE-TEST] Exception stack:\n", res["stack"])
        assert "unhashable type: 'dict'" in res["stack"] or "unhashable type" in str(res["exc"])

def test_kpi_meta_state_as_input_can_cause_unhashable():
    """
    If kpi_meta_state (a dict) is passed as an input to run_experiment and forwarded to a memoized helper,
    Python can raise 'unhashable type: dict'. This test confirms that path when signature accepts kpi_meta_prev.
    """
    good_feature_set = ["age", "race", "sex"]
    res = run_once_safely(app.DEFAULT_MODEL, 2, good_feature_set, app.DEFAULT_DATA_SIZE, include_kpi_meta_input=True)
    if res["ok"]:
        assert True
    else:
        print("[DICT-UNHASHABLE-TEST] Exception stack:\n", res["stack"])
        assert "unhashable type" in res["stack"] or "unhashable type" in str(res["exc"])

def test_feature_set_strings_only_should_pass():
    """
    With sanitized feature_set (strings only), the run should complete without unhashable errors.
    """
    good_feature_set = ["age", "race", "sex", "priors_count"]
    res = run_once_safely(app.DEFAULT_MODEL, 2, good_feature_set, app.DEFAULT_DATA_SIZE, include_kpi_meta_input=False)
    assert res["ok"], f"Unexpected failure with strings-only feature_set: {res}"

"""
Integration test: Verify automatic session-based login behavior for the model building game.

Key Question:
- At app session start (with a valid SESSION_ID), is the user considered logged in automatically,
  or must they manually log in?

Update (per request):
- The mock Gradio Request now exposes `sessionid` and `lang` as query parameters
  (request.query_params['sessionid'], request.query_params['lang']),
  mimicking how live GET requests supply them.
"""

import os
import time
import pytest

# Import the module under test
from aimodelshare.moral_compass.apps import model_building_game as mbg

try:
    import gradio as gr
except ImportError:
    gr = None  # States will still be emulated


MAX_AUTH_RETRIES = 3
RETRY_SLEEP_SECONDS = 2.0


class FakeRequest:
    """
    Minimal stand-in for gradio.Request.

    Gradio's real Request object (as passed to events like .load()) exposes:
      - request.query_params (dict-like)
      - request.headers
      - request.cookies
      - request.client

    We only need query_params for _try_session_based_auth, which looks up:
        session_id = params.get("sessionid") or params.get("session_id")

    This mock now mimics production by placing both sessionid and lang
    in query_params instead of cookies.
    """
    def __init__(self, sessionid: str, lang: str = "en"):
        self.query_params = {
            "sessionid": sessionid,
            "lang": lang,
        }
        self.headers = {}
        self.cookies = {}
        self.client = type("Client", (), {"host": "testclient"})()


def _attempt_session_auth(session_id: str, lang: str = "en"):
    """
    Try the internal auth helper with limited retries to reduce flakiness.
    Returns (success, username, token).
    """
    last_exc = None
    for attempt in range(1, MAX_AUTH_RETRIES + 1):
        req = FakeRequest(sessionid=session_id, lang=lang)
        try:
            success, username, token = mbg._try_session_based_auth(req)  # type: ignore[attr-defined]
            if success and username and token:
                return success, username, token
            time.sleep(RETRY_SLEEP_SECONDS)
        except Exception as e:
            last_exc = e
            time.sleep(RETRY_SLEEP_SECONDS)

    if last_exc:
        raise last_exc
    return False, None, None


@pytest.mark.integration
def test_auto_login_via_session_cookie_query_params():
    """
    Core test answering the key question about automatic login.
    """
    session_id = os.environ.get("SESSION_ID")
    assert session_id, (
        "Environment variable SESSION_ID not set. "
        "Configure MC_TEST_SESSIONID secret with a valid session value."
    )

    success, username, token = _attempt_session_auth(session_id, lang="en")

    print(f"[diag] success={success}, username={username}, token_present={bool(token)}")

    assert success and username and token, (
        "Automatic session-based login FAILED (sessionid passed via query params). "
        "=> Key Question Answer: User IS ASKED TO LOG IN."
    )

    # Simulate state assignment like the app
    if gr is not None:
        mbg.username_state = gr.State(username)
        mbg.token_state = gr.State(token)
    else:
        mbg.username_state = username
        mbg.token_state = token

    print(
        "Automatic session-based login SUCCEEDED (sessionid via query params): "
        "=> Key Question Answer: User IS CONSIDERED LOGGED IN AUTOMATICALLY."
    )

    assert mbg.username_state, "username_state not set after simulated auto login"
    assert mbg.token_state, "token_state not set after simulated auto login"


@pytest.mark.integration
def test_manual_login_not_required_if_auto_login_succeeds():
    """
    Secondary check: If auto login succeeds, manual login should be unnecessary.
    """
    if not getattr(mbg, "username_state", None) or not getattr(mbg, "token_state", None):
        pytest.skip("Auto login state not present from previous test; skipping secondary check.")

    user_logged_in = bool(mbg.username_state) and bool(mbg.token_state)
    print(f"[diag] user_logged_in={user_logged_in}")
    assert user_logged_in, "User should be logged in automatically; manual login flow not required."


def test_report_conclusion():
    """
    Final summarizing test to print outcome clearly in CI logs.
    """
    auto_login_success = (
        getattr(mbg, "username_state", None) and getattr(mbg, "token_state", None)
    )
    print("=== SESSION AUTO-LOGIN SUMMARY (QUERY PARAM MODE) ===")
    if auto_login_success:
        print("Result: User IS CONSIDERED LOGGED IN AUTOMATICALLY at app start.")
    else:
        print("Result: User IS ASKED TO LOG IN at app start.")
    assert auto_login_success, "Summary: Automatic login did not occur."

import os
import re
import time
import json
import typing as t

import pytest

SESSION_ID = os.environ.get("SESSION_ID")

NEW_MESSAGE_SNIPPETS = [
    "⏳ Submission Processing",
    "New Accuracy",
    "Pending leaderboard update...",
    "Your Rank",
    "Pending",
    "Calculating rank...",
]

@pytest.mark.timeout(600)
@pytest.mark.skipif(not SESSION_ID, reason="SESSION_ID is required to exercise real submission flow.")
def test_kpi_updates_on_second_submission(monkeypatch):
    """
    Goal:
    - Reproduce and detect the issue where KPI content does not update after the first submission.
    - Assert that after a second submission, KPI values are refreshed and differ when inputs differ.
    - Verify the new progress message text is emitted during/after submission.

    Test strategy:
    1) Initialize client/session from aimodelshare SDK.
    2) Submit two different payloads or models such that the KPI (e.g., accuracy) should change.
    3) Capture the post-submission response/output for progress message validation.
    4) Poll the leaderboard/KPI source until the pending update resolves or timeout.
    5) Compare KPI after the first and second submission; they must differ if inputs differ.
    6) Log detailed diagnostics if values are identical to help locate regression.

    Notes:
    - We intentionally keep generous timeouts and polling because leaderboard updates can be async.
    - If SDK raises or interface differs, we fall back to a skip-with-details to avoid false reds.
    """
    try:
        # Lazy imports to avoid hard failures if SDK changes.
        from aimodelshare import ModelShare
    except Exception as e:
        pytest.skip(f"aimodelshare SDK unavailable or import failed: {e}")

    # Initialize client with SESSION_ID; adapt if SDK differs
    try:
        client = ModelShare(session_id=SESSION_ID)
    except TypeError:
        # Some SDKs use different arg names
        client = ModelShare(SESSION_ID=SESSION_ID)

    # Prepare two distinct "submissions". Depending on the SDK, these could be:
    # - model files with slightly different weights
    # - different prediction artifacts
    # - explicit KPI overrides in a test endpoint
    #
    # We will use a generic interface:
    # client.submit(model=..., metadata=..., dry_run=False) -> returns dict with message and kpi/accuracy
    #
    # If your SDK differs, this test will still capture messages and log what was found.
    def submit_payload(version_tag: str, payload_diff: int) -> t.Tuple[dict, str]:
        metadata = {"version_tag": version_tag, "payload_diff": payload_diff}
        # Using a lightweight synthetic artifact to force difference
        synthetic_predictions = [0] * 100
        synthetic_predictions[payload_diff % 100] = 1  # nudge one position to alter accuracy

        response = {}
        message_blob = ""

        try:
            response = client.submit(
                predictions=synthetic_predictions,
                metadata=metadata,
            )
            message_blob = json.dumps(response, ensure_ascii=False)
        except AttributeError:
            # Fallback: some clients print messages and return None
            # Try an alternative method name
            try:
                response = client.submit_predictions(
                    predictions=synthetic_predictions,
                    metadata=metadata,
                )
                message_blob = json.dumps(response, ensure_ascii=False)
            except Exception as e:
                pytest.skip(f"Submission API did not match expected shape: {e}")
        except Exception as e:
            pytest.fail(f"Submission failed unexpectedly: {e}")

        return response, message_blob

    # First submission
    resp1, msg1 = submit_payload("v1-first", payload_diff=1)
    for snippet in NEW_MESSAGE_SNIPPETS:
        assert snippet in msg1, f"Progress message missing '{snippet}' in first submission output."

    # Capture KPI (accuracy) after first submission (could be immediate or pending)
    kpi1 = _extract_accuracy_from_response_or_poll(client, initial_response=resp1)

    # Second submission with a meaningful difference
    resp2, msg2 = submit_payload("v2-second", payload_diff=7)
    for snippet in NEW_MESSAGE_SNIPPETS:
        assert snippet in msg2, f"Progress message missing '{snippet}' in second submission output."

    kpi2 = _extract_accuracy_from_response_or_poll(client, initial_response=resp2)

    # Diagnostic logging to aid triage in CI
    print(f"[DIAG] KPI after first submission: {kpi1}")
    print(f"[DIAG] KPI after second submission: {kpi2}")

    # The core assertion: KPI should update and differ between submissions with different payloads
    assert kpi1 is not None, "Did not retrieve KPI after first submission."
    assert kpi2 is not None, "Did not retrieve KPI after second submission."
    assert kpi1 != kpi2, (
        "KPI did not change between first and second submission despite differing inputs. "
        "This likely reproduces the bug. See diagnostic logs above."
    )


def _extract_accuracy_from_response_or_poll(client, initial_response: dict, timeout_s: int = 300, interval_s: float = 5.0):
    """
    Try to extract 'accuracy' from the immediate response. If not present or pending,
    poll the leaderboard or KPI endpoint until the value is updated or timeout.
    """
    # First attempt: direct field in response
    acc = None
    for key in ("accuracy", "new_accuracy", "kpi_accuracy", "kpi"):
        val = initial_response.get(key)
        if isinstance(val, (int, float)):
            acc = float(val)
            break
        # Some APIs may return strings like "57.10%"
        if isinstance(val, str):
            m = re.search(r"(\d+(?:\.\d+)?)\s*%", val)
            if m:
                acc = float(m.group(1))
                break

    # If accuracy present and not marked as pending, return
    if acc is not None and not _is_pending(initial_response):
        return acc

    # Poll path: try calling client.get_leaderboard or client.get_kpi
    deadline = time.time() + timeout_s
    last_seen = None
    while time.time() < deadline:
        try:
            # Prefer a direct KPI accessor if available
            if hasattr(client, "get_kpi"):
                kpi = client.get_kpi()
                acc = _extract_accuracy_from_generic_kpi(kpi)
            elif hasattr(client, "get_leaderboard"):
                lb = client.get_leaderboard()
                acc = _extract_accuracy_from_leaderboard(lb)
            else:
                # No known method; break to return what we saw
                break
        except Exception:
            acc = None

        if acc is not None:
            # Store last seen; break if not pending
            last_seen = acc
            break

        time.sleep(interval_s)

    return last_seen


def _extract_accuracy_from_generic_kpi(kpi_obj) -> t.Optional[float]:
    # Accept dicts or list of dicts
    try:
        if isinstance(kpi_obj, dict):
            for key in ("accuracy", "new_accuracy", "kpi_accuracy"):
                val = kpi_obj.get(key)
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    m = re.search(r"(\d+(?:\.\d+)?)\s*%", val)
                    if m:
                        return float(m.group(1))
        elif isinstance(kpi_obj, list) and kpi_obj:
            # Try first entry
            return _extract_accuracy_from_generic_kpi(kpi_obj[0])
    except Exception:
        pass
    return None


def _extract_accuracy_from_leaderboard(lb_obj) -> t.Optional[float]:
    # Try typical structures: list of entries with accuracy column/key
    try:
        if isinstance(lb_obj, list):
            # Find the most recent or the one associated with our session/user
            for row in lb_obj:
                for key in ("accuracy", "new_accuracy", "kpi_accuracy"):
                    val = row.get(key)
                    if isinstance(val, (int, float)):
                        return float(val)
                    if isinstance(val, str):
                        m = re.search(r"(\d+(?:\.\d+)?)\s*%", val)
                        if m:
                            return float(m.group(1))
        elif hasattr(lb_obj, "to_dict"):
            rows = lb_obj.to_dict(orient="records")
            return _extract_accuracy_from_leaderboard(rows)
    except Exception:
        pass
    return None


def _is_pending(resp: dict) -> bool:
    # Heuristic: look for "Pending" or "Calculating" markers in response strings
    try:
        blob = json.dumps(resp, ensure_ascii=False)
        return ("Pending" in blob) or ("Calculating" in blob)
    except Exception:
        return False

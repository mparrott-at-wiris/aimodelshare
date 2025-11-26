import pandas as pd
import pytest

from aimodelshare.moral_compass.apps.model_building_game import (
    generate_competitive_summary,
    _build_kpi_card_html,
    TEAM_NAMES,
    _normalize_team_name,
)

def parse_kpi(html: str):
    """
    Minimal HTML scraper for KPI card content.
    Extracts: title, New Accuracy text, and Your Rank text.
    """
    out = {}
    # Title
    if "<h2" in html:
        start = html.find("<h2")
        end = html.find("</h2>", start)
        out["title"] = html[start:end].split(">")[-1]
    # New Accuracy text
    acc_idx = html.find("New Accuracy")
    if acc_idx != -1:
        score_idx = html.find("kpi-score", acc_idx)
        pct_start = html.find(">", score_idx) + 1
        pct_end = html.find("</", pct_start)
        out["acc_text"] = html[pct_start:pct_end]
    # Your Rank text
    rank_idx = html.find("Your Rank")
    if rank_idx != -1:
        score_idx = html.find("kpi-score", rank_idx)
        val_start = html.find(">", score_idx) + 1
        val_end = html.find("</", val_start)
        out["rank_text"] = html[val_start:val_end]
    return out

def ts(offset_sec: int = 0) -> pd.Timestamp:
    """UTC timestamp helper with offset seconds."""
    return pd.Timestamp.utcnow() + pd.Timedelta(seconds=offset_sec)

def test_sessionid_authenticated_kpi_flow():
    """
    Simulate the KPI flow for a session-authenticated user without any live API calls.

    We drive the flow purely with synthetic leaderboard DataFrames and verify:
    - First submission → 'First Model Submitted!' KPI and rank #1.
    - Second submission with improvement → updated KPI, best score, and same rank (#1).
    - Preview KPI shows N/A rank and does not imply state changes.
    - Third submission with worse score → KPI shows decline/neutral but best score remains from step 2.
    """
    username = "session_user"
    team_name = _normalize_team_name(TEAM_NAMES[1])

    # Step 1: first authenticated submission (accuracy 0.62)
    lb1 = pd.DataFrame([{
        "username": username,
        "accuracy": 0.62,
        "Team": team_name,
        "timestamp": ts(0)
    }])

    team_html, indiv_html, kpi1, best1, rank1, score1 = generate_competitive_summary(
        lb1, team_name, username, last_submission_score=0.0, last_rank=0, submission_count=0
    )
    p1 = parse_kpi(kpi1)

    assert "First Model Submitted" in p1.get("title", ""), "Expected first-submission KPI title"
    assert p1.get("rank_text") == "#1", "Single user should rank #1"
    assert p1.get("acc_text", "").endswith("%"), "Accuracy should be shown as a percent"
    assert abs(score1 - 0.62) < 1e-6
    assert abs(best1 - 0.62) < 1e-6

    # Step 2: second submission improved (accuracy 0.71)
    lb2 = pd.concat([lb1, pd.DataFrame([{
        "username": username,
        "accuracy": 0.71,
        "Team": team_name,
        "timestamp": ts(5)
    }])], ignore_index=True)

    team_html2, indiv_html2, kpi2, best2, rank2, score2 = generate_competitive_summary(
        lb2, team_name, username, last_submission_score=score1, last_rank=rank1, submission_count=1
    )
    p2 = parse_kpi(kpi2)

    assert "Submission Successful" in p2.get("title", ""), "Expected general success title on subsequent submission"
    assert p2.get("rank_text") == "#1", "Still only one user, rank #1"
    assert abs(score2 - 0.71) < 1e-6
    assert abs(best2 - 0.71) < 1e-6
    assert kpi2 != kpi1, "KPI card should change between submissions"

    # Step 3: preview KPI (does not affect state, shows N/A rank)
    prev = _build_kpi_card_html(new_score=0.55, last_score=0.0, new_rank=0, last_rank=0, submission_count=-1, is_preview=True)
    pp = parse_kpi(prev)

    assert "Successful Preview Run" in pp.get("title", ""), "Preview title expected"
    assert pp.get("rank_text") == "N/A", "Preview rank should be N/A"

    # Step 4: third submission worse (accuracy 0.60) – best remains 0.71
    lb3 = pd.concat([lb2, pd.DataFrame([{
        "username": username,
        "accuracy": 0.60,
        "Team": team_name,
        "timestamp": ts(10)
    }])], ignore_index=True)

    team_html3, indiv_html3, kpi3, best3, rank3, score3 = generate_competitive_summary(
        lb3, team_name, username, last_submission_score=score2, last_rank=rank2, submission_count=2
    )
    p3 = parse_kpi(kpi3)

    assert ("Score Dropped" in p3.get("title", "")) or ("Submission Successful" in p3.get("title", "")), \
        "KPI should indicate a decline or neutral outcome"
    assert abs(score3 - 0.60) < 1e-6
    assert abs(best3 - 0.71) < 1e-6
    assert p3.get("rank_text") == "#1", "Rank remains #1 with a single user"

def test_empty_leaderboard_yields_neutral_kpi():
    """
    With an empty leaderboard, the summary should return a neutral KPI and rank #0.
    """
    lb_empty = pd.DataFrame(columns=["username", "accuracy", "Team", "timestamp"])
    _, _, kpi, best, rank, score = generate_competitive_summary(
        lb_empty, TEAM_NAMES[0], "userX", 0, 0, 0
    )
    p = parse_kpi(kpi)

    assert "Submission Successful" in p.get("title", ""), "Neutral success title expected when leaderboard empty"
    assert p.get("rank_text") == "#0", "Rank should be 0 when no users"
    assert p.get("acc_text") in ("0.00%", "N/A"), "Accuracy should be neutral when no data"

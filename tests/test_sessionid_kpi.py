import time
import pandas as pd
import pytest

from aimodelshare.moral_compass.apps.model_building_game import (
    generate_competitive_summary,
    _build_kpi_card_html,
    TEAM_NAMES,
    _normalize_team_name,
)

# -----------------------
# Simple KPI HTML parser
# -----------------------
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

def iso_ts(offset_sec: float = 0.0) -> str:
    return pd.Timestamp.utcnow() + pd.Timedelta(seconds=offset_sec)
    
def test_sessionid_authenticated_kpi_flow():
    """
    Simulate the KPI flow with a session-authenticated user by constructing
    leaderboard DataFrames directly (no live API calls).
    """
    username = "session_user"
    team_name = _normalize_team_name(TEAM_NAMES[1])

    # Step 1: first authenticated submission (best=0.62, rank #1)
    lb = pd.DataFrame([{
        "username": username,
        "accuracy": 0.62,
        "Team": team_name,
        "timestamp": iso_ts(0)
    }])

    team_html, indiv_html, kpi_html, best_acc, new_rank, this_score = generate_competitive_summary(
        lb, team_name, username, last_submission_score=0.0, last_rank=0, submission_count=0
    )

    parsed = parse_kpi(kpi_html)
    assert "First Model Submitted" in parsed.get("title", ""), "first-submission KPI title"
    assert parsed.get("acc_text", "").endswith("%"), "accuracy percent present"
    assert parsed.get("rank_text") == "#1", "rank should be #1 for single user"
    assert abs(this_score - 0.62) < 1e-6
    assert abs(best_acc - 0.62) < 1e-6

    # Step 2: second submission improved to 0.71 (best=0.71)
    lb2 = pd.concat([lb, pd.DataFrame([{
        "username": username,
        "accuracy": 0.71,
        "Team": team_name,
        "timestamp": iso_ts(5)
    }])], ignore_index=True)

    team_html2, indiv_html2, kpi_html2, best_acc2, new_rank2, this_score2 = generate_competitive_summary(
        lb2, team_name, username, last_submission_score=this_score, last_rank=new_rank, submission_count=1
    )

    parsed2 = parse_kpi(kpi_html2)
    assert "Submission Successful" in parsed2.get("title", ""), "general success title"
    assert abs(this_score2 - 0.71) < 1e-6
    assert abs(best_acc2 - 0.71) < 1e-6
    assert parsed2.get("rank_text") == "#1"
    assert kpi_html2 != kpi_html, "card should change between submissions"

    # Step 3: preview card (does not change state)
    preview_html = _build_kpi_card_html(new_score=0.55, last_score=0.0, new_rank=0, last_rank=0, submission_count=-1, is_preview=True)
    parsed_prev = parse_kpi(preview_html)
    assert "Successful Preview Run" in parsed_prev.get("title", ""), "preview title expected"
    assert parsed_prev.get("rank_text") == "N/A", "preview rank is N/A"

    # Step 4: third submission worse (0.60), best stays 0.71
    lb3 = pd.concat([lb2, pd.DataFrame([{
        "username": username,
        "accuracy": 0.60,
        "Team": team_name,
        "timestamp": iso_ts(10)
    }])], ignore_index=True)

    team_html3, indiv_html3, kpi_html3, best_acc3, new_rank3, this_score3 = generate_competitive_summary(
        lb3, team_name, username, last_submission_score=this_score2, last_rank=new_rank2, submission_count=2
    )

    parsed3 = parse_kpi(kpi_html3)
    assert ("Score Dropped" in parsed3.get("title", "")) or ("Submission Successful" in parsed3.get("title", "")), \
        "decline or neutral title expected"
    assert abs(this_score3 - 0.60) < 1e-6
    assert abs(best_acc3 - 0.71) < 1e-6

def test_empty_leaderboard_yields_neutral_kpi():
    lb = pd.DataFrame(columns=["username", "accuracy", "Team", "timestamp"])
    team_html, indiv_html, kpi_html, best_acc, new_rank, this_score = generate_competitive_summary(
        lb, TEAM_NAMES[0], "userX", 0, 0, 0
    )
    parsed = parse_kpi(kpi_html)
    assert "Submission Successful" in parsed.get("title", ""), "neutral title for empty board"
    assert parsed.get("rank_text") == "#0"
    assert parsed.get("acc_text") in ("0.00%", "N/A")

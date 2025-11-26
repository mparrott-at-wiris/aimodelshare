name: SessionID KPI Workflow Tests

on:
  workflow_dispatch:

jobs:
  test-sessionid-kpi:
    runs-on: ubuntu-latest

    permissions:
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install system dependencies (match Dockerfile pattern)
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends \
            libgl1 \
            libglib2.0-0 \
            gcc \
            python3-dev
          sudo rm -rf /var/lib/apt/lists/*

      - name: Install Python dependencies (match Dockerfile pattern)
        run: |
          python -m pip install --upgrade pip
          pip install --no-cache-dir -r requirements-apps.txt
          pip install --no-cache-dir aimodelshare
          # Test-only dependencies (keep if not in requirements-apps.txt)
          pip install --no-cache-dir pytest pytest-timeout

      - name: Create tests
        run: |
          mkdir -p tests
          cat > tests/test_sessionid_kpi.py << 'PYTEST'
          import types
          import time
          import pandas as pd
          import numpy as np
          import pytest

          from aimodelshare.moral_compass.apps.model_building_game import (
              create_model_building_game_app,
              run_experiment,
              generate_competitive_summary,
              _build_kpi_card_html,
              _get_leaderboard_with_optional_token,
              Competition,
              INIT_FLAGS,
              TEAM_NAMES,
              ATTEMPT_LIMIT,
              _normalize_team_name,
          )

          class MockCompetition:
              def __init__(self, pid):
                  self.pid = pid
                  self.submissions = []

              def submit_model(self, model, preprocessor, prediction_submission, input_dict, custom_metadata, token):
                  acc = float(custom_metadata.get("__test_accuracy", 0.5))
                  username = custom_metadata.get("__test_username", "user1")
                  team = custom_metadata.get("Team", TEAM_NAMES[0])
                  timestamp = time.time()
                  self.submissions.append({
                      "username": username,
                      "accuracy": acc,
                      "Team": team,
                      "timestamp": timestamp,
                  })
                  return True

              def get_leaderboard(self, token=None):
                  if not self.submissions:
                      return pd.DataFrame(columns=["username", "accuracy", "Team", "timestamp"])
                  return pd.DataFrame(self.submissions)

          @pytest.fixture(autouse=True)
          def patch_playground(monkeypatch):
              monkeypatch.setattr(
                  "aimodelshare.moral_compass.apps.model_building_game.Competition",
                  lambda pid: MockCompetition(pid)
              )
              INIT_FLAGS.update({
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
              yield

          def parse_kpi(html: str):
              out = {}
              if "<h2" in html:
                  start = html.find("<h2")
                  end = html.find("</h2>", start)
                  out["title"] = html[start:end].split(">")[-1]
              acc_idx = html.find("New Accuracy")
              if acc_idx != -1:
                  score_idx = html.find("kpi-score", acc_idx)
                  pct_start = html.find(">", score_idx) + 1
                  pct_end = html.find("</", pct_start)
                  out["acc_text"] = html[pct_start:pct_end]
              rank_idx = html.find("Your Rank")
              if rank_idx != -1:
                  score_idx = html.find("kpi-score", rank_idx)
                  val_start = html.find(">", score_idx) + 1
                  val_end = html.find("</", val_start)
                  out["rank_text"] = html[val_start:val_end]
              return out

          def test_sessionid_authenticated_kpi_flow(monkeypatch):
              demo = create_model_building_game_app()
              username = "session_user"
              token = "valid_token"
              team_name = _normalize_team_name(TEAM_NAMES[1])

              comp = Competition("pid")

              comp.submit_model(
                  model=None, preprocessor=None, prediction_submission=None,
                  input_dict={"description": "test"},
                  custom_metadata={"Team": team_name, "Moral_Compass": 0, "__test_accuracy": 0.62, "__test_username": username},
                  token=token
              )

              lb = comp.get_leaderboard(token=token)
              team_html, indiv_html, kpi_html, best_acc, new_rank, this_score = generate_competitive_summary(
                  lb, team_name, username, last_submission_score=0.0, last_rank=0, submission_count=0
              )
              parsed = parse_kpi(kpi_html)
              assert "First Model Submitted" in parsed.get("title", "")
              assert parsed.get("acc_text") and parsed["acc_text"].endswith("%")
              assert parsed.get("rank_text") == f"#{new_rank}"
              assert abs(this_score - 0.62) < 1e-6
              assert abs(best_acc - 0.62) < 1e-6
              assert new_rank == 1

              comp.submit_model(
                  model=None, preprocessor=None, prediction_submission=None,
                  input_dict={"description": "test2"},
                  custom_metadata={"Team": team_name, "Moral_Compass": 0, "__test_accuracy": 0.71, "__test_username": username},
                  token=token
              )

              for _ in range(3):
                  lb = comp.get_leaderboard(token=token)
                  if len(lb[lb["username"] == username]) >= 2:
                      break
                  time.sleep(0.2)

              team_html2, indiv_html2, kpi_html2, best_acc2, new_rank2, this_score2 = generate_competitive_summary(
                  lb, team_name, username, last_submission_score=this_score, last_rank=new_rank, submission_count=1
              )
              parsed2 = parse_kpi(kpi_html2)
              assert "Submission Successful" in parsed2.get("title", "")
              assert abs(this_score2 - 0.71) < 1e-6
              assert abs(best_acc2 - 0.71) < 1e-6
              assert parsed2.get("rank_text") == f"#{new_rank2}"
              assert kpi_html2 != kpi_html

              preview_html = _build_kpi_card_html(new_score=0.55, last_score=0.0, new_rank=0, last_rank=0, submission_count=-1, is_preview=True)
              parsed_prev = parse_kpi(preview_html)
              assert "Successful Preview Run" in parsed_prev.get("title", "")
              assert parsed_prev.get("rank_text") == "N/A"

              comp.submit_model(
                  model=None, preprocessor=None, prediction_submission=None,
                  input_dict={"description": "test3"},
                  custom_metadata={"Team": team_name, "Moral_Compass": 0, "__test_accuracy": 0.60, "__test_username": username},
                  token=token
              )

              for _ in range(3):
                  lb = comp.get_leaderboard(token=token)
                  if len(lb[lb["username"] == username]) >= 3:
                      break
                  time.sleep(0.2)

              team_html3, indiv_html3, kpi_html3, best_acc3, new_rank3, this_score3 = generate_competitive_summary(
                  lb, team_name, username, last_submission_score=this_score2, last_rank=new_rank2, submission_count=2
              )
              parsed3 = parse_kpi(kpi_html3)
              assert ("Score Dropped" in parsed3.get("title", "")) or ("Submission Successful" in parsed3.get("title", ""))
              assert abs(this_score3 - 0.60) < 1e-6
              assert abs(best_acc3 - 0.71) < 1e-6

          def test_empty_leaderboard_yields_neutral_kpi(monkeypatch):
              comp = Competition("pid")
              lb = comp.get_leaderboard(token="any")
              team_html, indiv_html, kpi_html, best_acc, new_rank, this_score = generate_competitive_summary(
                  lb, TEAM_NAMES[0], "userX", 0, 0, 0
              )
              parsed = parse_kpi(kpi_html)
              assert "Submission Successful" in parsed.get("title", "")
              assert parsed.get("rank_text") == "#0"
              assert parsed.get("acc_text") in ("0.00%", "N/A")

          PYTEST

      - name: Run tests
        run: |
          pytest -q tests/test_sessionid_kpi.py --disable-warnings --maxfail=1

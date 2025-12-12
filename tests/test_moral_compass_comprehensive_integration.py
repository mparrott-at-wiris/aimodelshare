#!/usr/bin/env python3

import os
import sys
import time
import uuid
import logging
import random
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse

RUN_ID = uuid.uuid4().hex[:8]
LOG_FILE = f"/tmp/mc_comprehensive_test_{RUN_ID}.log"

# Optional flag to preserve the table across runs to accumulate users/rankings
SKIP_CLEANUP = os.environ.get("MC_SKIP_CLEANUP", "true").lower() == "true"

logger = logging.getLogger("mc_comprehensive_single_user_test")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(fmt)
logger.addHandler(sh)

fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
fh.setFormatter(fmt)
logger.addHandler(fh)

def log_kv(title: str, data: dict):
    logger.info(f"--- {title} ---")
    for k, v in data.items():
        logger.info(f"{k}: {v}")
    logger.info("--- end ---")

try:
    from aimodelshare.moral_compass import MoralcompassApiClient, ApiClientError, NotFoundError
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)


class MoralCompassIntegrationTest:
    # Pools to vary run data
    ACCURACY_CHOICES = [0.72, 0.80, 0.85, 0.90, 0.95]
    TEAM_CHOICES = ["team-a", "team-b", "team-c"]
    PARTIAL_RATIO_MIN = 0.30
    PARTIAL_RATIO_MAX = 0.80

    def __init__(self, api_base_url: Optional[str] = None, session_id: Optional[str] = None):
        env_snapshot = {
            "MORAL_COMPASS_API_BASE_URL": os.environ.get("MORAL_COMPASS_API_BASE_URL"),
            "SESSION_ID_present": bool(os.environ.get("SESSION_ID")),
            "JWT_AUTHORIZATION_TOKEN_present": bool(os.environ.get("JWT_AUTHORIZATION_TOKEN")),
            "TEST_TABLE_ID": os.environ.get("TEST_TABLE_ID"),
            "TEST_PLAYGROUND_URL": os.environ.get("TEST_PLAYGROUND_URL"),
            "MC_SKIP_CLEANUP": os.environ.get("MC_SKIP_CLEANUP", "true"),
            "PYTHON_VERSION": sys.version.split()[0],
            "RUN_ID": RUN_ID,
            "LOG_FILE": LOG_FILE,
        }
        log_kv("Environment Snapshot", env_snapshot)

        api_base_url = api_base_url or os.environ.get("MORAL_COMPASS_API_BASE_URL")
        if not api_base_url:
            raise ValueError("MORAL_COMPASS_API_BASE_URL must be set")

        session_id = session_id or os.environ.get("SESSION_ID")
        if not session_id:
            raise ValueError("SESSION_ID must be provided for single-user comprehensive test")

        logger.info("Authenticating via SESSION_ID...")
        self.auth_token = get_token_from_session(session_id)
        os.environ["JWT_AUTHORIZATION_TOKEN"] = self.auth_token
        self.username = _get_username_from_token(self.auth_token)
        log_kv("Auth Details", {"username": self.username, "token_masked": self.auth_token[:6] + "***"})

        self.client = MoralcompassApiClient(api_base_url=api_base_url, auth_token=self.auth_token)

        # Fixed table behavior:
        # Prefer TEST_TABLE_ID if provided. Otherwise, derive from TEST_PLAYGROUND_URL as <playgroundId>-mc.
        explicit_table = os.environ.get("TEST_TABLE_ID")
        pg_url = os.environ.get("TEST_PLAYGROUND_URL")

        if explicit_table and explicit_table.strip():
            self.test_table_id = explicit_table.strip()
            # If playground_url not provided, synthesize one tied to table id for metadata
            self.playground_url = pg_url or f"https://example.com/playground/{self.test_table_id}"
        else:
            # Derive stable table id from playground URL or use a shared default
            self.playground_url = pg_url or "https://example.com/playground/shared-comprehensive"
            parts = [p for p in urlparse(self.playground_url).path.split('/') if p]
            playground_id = parts[-1] if parts else "shared-comprehensive"
            self.test_table_id = f"{playground_id}-mc"

        # Random selections for this run
        random.seed()  # system entropy
        self.accuracy = random.choice(self.ACCURACY_CHOICES)
        self.tasks = 10  # base total tasks for this challenge
        self.team = random.choice(self.TEAM_CHOICES)

        # Random partial completion ratio (30–80%), then clamp to [0,1]
        raw_ratio = random.uniform(self.PARTIAL_RATIO_MIN, self.PARTIAL_RATIO_MAX)
        self.partial_ratio = max(0.0, min(1.0, raw_ratio))
        # Compute integer tasks_completed based on ratio
        self.partial_tasks_completed = max(0, min(self.tasks, int(round(self.tasks * self.partial_ratio))))

        log_kv("Test Config", {
            "test_table_id": self.test_table_id,
            "playground_url": self.playground_url,
            "selected_accuracy": self.accuracy,
            "accuracy_choices": self.ACCURACY_CHOICES,
            "total_tasks": self.tasks,
            "selected_team": self.team,
            "team_choices": self.TEAM_CHOICES,
            "partial_ratio": f"{self.partial_ratio:.2f}",
            "partial_tasks_completed": self.partial_tasks_completed,
            "skip_cleanup": SKIP_CLEANUP,
        })

        # Will store full ranking outputs for final summary
        self.last_individual_rankings: List[Dict[str, Any]] = []
        self.last_team_rankings: List[Dict[str, Any]] = []

        self.errors = []
        self.passed_tests = 0
        self.total_tests = 0

    def log_test_start(self, name):
        self.total_tests += 1
        logger.info("\n" + "=" * 70)
        logger.info(f"TEST: {name}")
        logger.info("=" * 70)

    def log_pass(self, name, msg=""):
        self.passed_tests += 1
        logger.info(f"✅ PASS: {name}")
        if msg:
            logger.info(f"   {msg}")

    def log_fail(self, name, err):
        self.errors.append(f"{name}: {err}")
        logger.error(f"❌ FAIL: {name}")
        logger.error(f"   {err}")

    def cleanup_table(self):
        logger.info("Cleaning up test table (if exists)...")
        try:
            self.client.delete_table(self.test_table_id)
            logger.info(f"Cleaned up test table: {self.test_table_id}")
        except Exception as e:
            logger.info(f"Cleanup continued (delete may be disabled or table missing): {e}")

    def ensure_table_exists(self):
        name = "Ensure Table Exists"
        self.log_test_start(name)
        try:
            # Check table
            try:
                table = self.client.get_table(self.test_table_id)
                log_kv("get_table (pre-check)", {"table_id": table.table_id, "user_count": table.user_count})
                self.log_pass(name, "Table already exists")
                return True
            except NotFoundError:
                logger.info("Table not found. Attempting to create...")
            except ApiClientError as e:
                logger.info(f"get_table error (will attempt create): {e}")

            # Create table
            create_payload = {
                "table_id": self.test_table_id,
                "display_name": f"Moral Compass Integration Test - Shared Table",
                "playground_url": self.playground_url
            }
            log_kv("create_table Request", create_payload)
            res = self.client.create_table(**create_payload)
            log_kv("create_table Response", res)

            time.sleep(0.5)
            table = self.client.get_table(self.test_table_id)
            log_kv("get_table (post-create)", {"table_id": table.table_id, "user_count": table.user_count})
            self.log_pass(name, f"Created and verified table: {self.test_table_id}")
            return True
        except Exception as e:
            self.log_fail(name, str(e))
            return False

    def test_create_user_full_completion(self):
        name = "Create Authenticated User (Full Completion)"
        self.log_test_start(name)
        try:
            request_payload = {
                "table_id": self.test_table_id,
                "username": self.username,
                "metrics": {"accuracy": self.accuracy},
                "tasks_completed": self.tasks,
                "total_tasks": self.tasks,
                "questions_correct": 0,
                "total_questions": 0,
                "primary_metric": "accuracy",
                "team_name": self.team,
            }
            log_kv("UpdateMoralCompass Request", request_payload)
            res = self.client.update_moral_compass(**request_payload)
            log_kv("UpdateMoralCompass Response", res)
            actual = float(res.get("moralCompassScore", 0))
            expected = self.accuracy  # ratio == 1
            log_kv("Score Check", {"actual": actual, "expected": expected})
            if abs(actual - expected) < 0.01:
                self.log_pass(name, f"Score correct for full completion: {actual:.4f}")
            else:
                self.log_fail(name, f"Score mismatch: {actual:.4f} (expected={expected:.4f})")
        except Exception as e:
            self.log_fail(name, str(e))

    def test_create_user_partial_completion(self):
        name = "Create/Update Authenticated User (Partial Completion)"
        self.log_test_start(name)
        try:
            request_payload = {
                "table_id": self.test_table_id,
                "username": self.username,
                "metrics": {"accuracy": self.accuracy},
                "tasks_completed": self.partial_tasks_completed,
                "total_tasks": self.tasks,
                "questions_correct": 0,
                "total_questions": 0,
                "primary_metric": "accuracy",
                "team_name": self.team,
            }
            log_kv("UpdateMoralCompass Request (Partial)", request_payload)
            res = self.client.update_moral_compass(**request_payload)
            log_kv("UpdateMoralCompass Response (Partial)", res)
            actual = float(res.get("moralCompassScore", 0))
            expected = self.accuracy * (self.partial_tasks_completed / self.tasks)
            log_kv("Score Check (Partial)", {"actual": actual, "expected": expected})
            if abs(actual - expected) < 0.01:
                self.log_pass(name, f"Score correct for partial completion: {actual:.4f}")
            else:
                self.log_fail(name, f"Score mismatch (partial): {actual:.4f} (expected={expected:.4f})")
        except Exception as e:
            self.log_fail(name, str(e))

    def list_all_users(self) -> List[Dict[str, Any]]:
        resp = self.client.list_users(table_id=self.test_table_id, limit=500)
        users = resp.get("users", [])
        log_kv("ListUsers Summary", {"count": len(users)})
        for u in users:
            logger.info(f"UserRow: username={u.get('username')} score={u.get('moralCompassScore')} team={u.get('teamName')} tasks={u.get('tasksCompleted')}/{u.get('totalTasks')} q={u.get('questionsCorrect')}/{u.get('totalQuestions')}")
        return users

    def compute_individual_rankings(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def sort_key(x):
            return (float(x.get('moralCompassScore', 0) or 0.0), x.get('submissionCount', 0))
        ranked = sorted(users, key=sort_key, reverse=True)
        rankings: List[Dict[str, Any]] = []
        for idx, u in enumerate(ranked, 1):
            rankings.append({
                "rank": idx,
                "username": u.get("username"),
                "moralCompassScore": float(u.get("moralCompassScore", 0) or 0.0),
                "teamName": u.get("teamName"),
                "tasksCompleted": u.get("tasksCompleted"),
                "totalTasks": u.get("totalTasks"),
                "questionsCorrect": u.get("questionsCorrect"),
                "totalQuestions": u.get("totalQuestions")
            })
        return rankings

    def test_individual_ranking(self):
        name = "Individual Ranking by Moral Compass Score"
        self.log_test_start(name)
        try:
            time.sleep(0.5)
            users = self.list_all_users()
            rankings = self.compute_individual_rankings(users)
            self.last_individual_rankings = rankings

            logger.info("Current Individual Rankings (full list):")
            logger.info(json.dumps(rankings, indent=2))

            my_rank_entry = next((r for r in rankings if r["username"] == self.username), None)
            if my_rank_entry is None:
                self.log_fail(name, "Authenticated user not found in ranking list")
                return
            self.log_pass(name, f"Authenticated user's current rank: #{my_rank_entry['rank']}")
            log_kv("Individual Ranking Result", {"my_rank": my_rank_entry['rank'], "total_users": len(rankings)})
        except Exception as e:
            self.log_fail(name, str(e))

    def compute_team_rankings(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        team_scores: Dict[str, float] = {}
        team_counts: Dict[str, int] = {}
        for u in users:
            team = u.get('teamName')
            if not team:
                continue
            score = float(u.get('moralCompassScore', 0) or 0.0)
            team_scores[team] = team_scores.get(team, 0.0) + score
            team_counts[team] = team_counts.get(team, 0) + 1
        team_avgs: List[Tuple[str, float]] = [(team, team_scores[team] / team_counts[team]) for team in team_scores]
        ranked_teams = sorted(team_avgs, key=lambda kv: kv[1], reverse=True)
        rankings: List[Dict[str, Any]] = []
        for idx, (team, avg) in enumerate(ranked_teams, 1):
            rankings.append({
                "rank": idx,
                "teamName": team,
                "averageScore": avg,
                "members": team_counts.get(team, 0)
            })
        return rankings

    def test_team_ranking(self):
        name = "Team Ranking by Average Score"
        self.log_test_start(name)
        try:
            users = self.list_all_users()
            rankings = self.compute_team_rankings(users)
            self.last_team_rankings = rankings

            logger.info("Current Team Rankings (full list):")
            logger.info(json.dumps(rankings, indent=2))

            my_team = self.team
            my_team_entry = next((r for r in rankings if r["teamName"] == my_team), None)
            if my_team_entry is None:
                self.log_fail(name, f"User's team '{my_team}' not found in team rankings")
                return
            self.log_pass(name, f"User's current team rank: #{my_team_entry['rank']}")
            log_kv("Team Ranking Result", {"my_team": my_team, "my_team_rank": my_team_entry['rank'], "total_teams": len(rankings)})
        except Exception as e:
            self.log_fail(name, str(e))

    def run_all(self):
        logger.info("\n" + "=" * 80)
        logger.info("MORAL COMPASS COMPREHENSIVE INTEGRATION TEST SUITE (Single-User, Shared Table)")
        logger.info("=" * 80)
        log_kv("Run Metadata", {
            "run_id": RUN_ID,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "log_file": LOG_FILE,
        })

        # Ensure table exists
        if not self.ensure_table_exists():
            logger.error("Table setup failed, aborting subsequent tests.")
        else:
            # Full completion with selected accuracy and team
            self.test_create_user_full_completion()
            # Partial completion using random 30–80% ratio
            self.test_create_user_partial_completion()
            # Individual rank from current table content (full list returned)
            self.test_individual_ranking()
            # Team rank by average score (full list returned)
            self.test_team_ranking()

        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        summary = {
            "Total Tests": self.total_tests,
            "Passed": self.passed_tests,
            "Failed": len(self.errors),
        }
        log_kv("Summary", summary)

        # Emit full rankings again in summary for easy artifact parsing
        logger.info("--- Full Individual Rankings (Summary) ---")
        logger.info(json.dumps(self.last_individual_rankings, indent=2))
        logger.info("--- end ---")
        logger.info("--- Full Team Rankings (Summary) ---")
        logger.info(json.dumps(self.last_team_rankings, indent=2))
        logger.info("--- end ---")

        if self.errors:
            logger.error("\nFailed Tests:")
            for e in self.errors:
                logger.error(f"  • {e}")
            return False

        logger.info("\n✅ ALL TESTS PASSED!")
        logger.info("=" * 80)
        return True

    def cleanup(self):
        logger.info("\nCleaning up test resources...")
        if SKIP_CLEANUP:
            logger.info("MC_SKIP_CLEANUP=true → skipping table deletion to preserve cumulative rankings.")
        else:
            try:
                self.cleanup_table()
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
        logger.info(f"Logs written to: {LOG_FILE}")


def main():
    api_base_url = os.environ.get("MORAL_COMPASS_API_BASE_URL")
    if not api_base_url:
        logger.error("MORAL_COMPASS_API_BASE_URL environment variable is required")
        sys.exit(1)

    session_id = os.environ.get("SESSION_ID")
    if not session_id:
        logger.error("SESSION_ID environment variable is required")
        sys.exit(1)

    suite = MoralCompassIntegrationTest(api_base_url=api_base_url, session_id=session_id)
    ok = False
    try:
        ok = suite.run_all()
    finally:
        suite.cleanup()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

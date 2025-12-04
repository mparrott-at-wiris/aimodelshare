#!/usr/bin/env python3

import os
import sys
import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

RUN_ID = uuid.uuid4().hex[:8]
LOG_FILE = f"/tmp/mc_comprehensive_test_{RUN_ID}.log"

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
    def __init__(self, api_base_url: Optional[str] = None, session_id: Optional[str] = None):
        env_snapshot = {
            "MORAL_COMPASS_API_BASE_URL": os.environ.get("MORAL_COMPASS_API_BASE_URL"),
            "SESSION_ID_present": bool(os.environ.get("SESSION_ID")),
            "JWT_AUTHORIZATION_TOKEN_present": bool(os.environ.get("JWT_AUTHORIZATION_TOKEN")),
            "TEST_TABLE_ID": os.environ.get("TEST_TABLE_ID"),
            "TEST_PLAYGROUND_URL": os.environ.get("TEST_PLAYGROUND_URL"),
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

        self.test_id = uuid.uuid4().hex[:8]
        self.test_table_id = os.environ.get("TEST_TABLE_ID") or f"test-mc-comprehensive-{self.test_id}"
        self.playground_url = os.environ.get("TEST_PLAYGROUND_URL") or f"https://example.com/playground/{self.test_table_id}"

        # Single-user config
        self.accuracy = 0.92
        self.tasks = 10
        self.team = "team-a"
        log_kv("Test Config", {
            "test_table_id": self.test_table_id,
            "playground_url": self.playground_url,
            "initial_accuracy": self.accuracy,
            "initial_tasks": self.tasks,
            "team": self.team,
        })

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
                "display_name": f"Moral Compass Integration Test {self.test_id}",
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
            partial_tasks_completed = self.tasks // 2  # e.g., 5 of 10
            request_payload = {
                "table_id": self.test_table_id,
                "username": self.username,
                "metrics": {"accuracy": self.accuracy},
                "tasks_completed": partial_tasks_completed,
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
            expected = self.accuracy * (partial_tasks_completed / self.tasks)
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

    def test_individual_ranking(self):
        name = "Individual Ranking by Moral Compass Score"
        self.log_test_start(name)
        try:
            time.sleep(0.5)
            users = self.list_all_users()
            # Sort by score desc, then submissionCount desc as tie-breaker
            def sort_key(x):
                return (float(x.get('moralCompassScore', 0) or 0.0), x.get('submissionCount', 0))
            ranked = sorted(users, key=sort_key, reverse=True)

            logger.info("Current Individual Rankings:")
            for rank, u in enumerate(ranked, 1):
                logger.info(f"  #{rank} {u.get('username')} score={float(u.get('moralCompassScore', 0) or 0.0):.4f} team={u.get('teamName')}")
            # Find current user rank
            my_rank = next((i + 1 for i, u in enumerate(ranked) if u.get('username') == self.username), None)
            if my_rank is None:
                self.log_fail(name, "Authenticated user not found in ranking list")
                return
            self.log_pass(name, f"Authenticated user's current rank: #{my_rank}")
            log_kv("Individual Ranking Result", {"my_rank": my_rank, "total_users": len(ranked)})
        except Exception as e:
            self.log_fail(name, str(e))

    def test_team_ranking(self):
        name = "Team Ranking by Average Score"
        self.log_test_start(name)
        try:
            users = self.list_all_users()
            # Aggregate scores per team
            team_scores: Dict[str, float] = {}
            team_counts: Dict[str, int] = {}
            for u in users:
                team = u.get('teamName')
                if not team:
                    continue
                score = float(u.get('moralCompassScore', 0) or 0.0)
                team_scores[team] = team_scores.get(team, 0.0) + score
                team_counts[team] = team_counts.get(team, 0) + 1
            team_avgs = {team: (team_scores[team] / team_counts[team]) for team in team_scores}

            ranked_teams = sorted(team_avgs.items(), key=lambda kv: kv[1], reverse=True)
            logger.info("Current Team Rankings (by average score):")
            for rank, (team, avg) in enumerate(ranked_teams, 1):
                logger.info(f"  #{rank} {team} avg={avg:.4f} members={team_counts.get(team, 0)}")

            # User's current team rank
            my_team = self.team
            my_team_rank = next((i + 1 for i, (t, _) in enumerate(ranked_teams) if t == my_team), None)
            if my_team_rank is None:
                self.log_fail(name, f"User's team '{my_team}' not found in team rankings")
                return
            self.log_pass(name, f"User's current team rank: #{my_team_rank}")
            log_kv("Team Ranking Result", {"my_team": my_team, "my_team_rank": my_team_rank, "total_teams": len(ranked_teams)})
        except Exception as e:
            self.log_fail(name, str(e))

    def run_all(self):
        logger.info("\n" + "=" * 80)
        logger.info("MORAL COMPASS COMPREHENSIVE INTEGRATION TEST SUITE (Single-User)")
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
            # Full completion
            self.test_create_user_full_completion()
            # Partial completion
            self.test_create_user_partial_completion()
            # Individual rank
            self.test_individual_ranking()
            # Team rank
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

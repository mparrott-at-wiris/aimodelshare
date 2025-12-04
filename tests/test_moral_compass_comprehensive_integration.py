#!/usr/bin/env python3

import os
import sys
import time
import uuid
import logging
from datetime import datetime
from typing import Optional

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
        """Ensure the test table exists; create it if missing, then verify."""
        name = "Ensure Table Exists"
        self.log_test_start(name)
        try:
            # Try get_table first
            try:
                table = self.client.get_table(self.test_table_id)
                log_kv("get_table (pre-check)", {"table_id": table.table_id, "user_count": table.user_count})
                self.log_pass(name, "Table already exists")
                return True
            except NotFoundError:
                logger.info("Table not found. Attempting to create...")
            except ApiClientError as e:
                logger.info(f"get_table error (will attempt create): {e}")

            # Create table with correct keyword argument names
            create_payload = {
                "table_id": self.test_table_id,
                "display_name": f"Moral Compass Integration Test {self.test_id}",
                "playground_url": self.playground_url
            }
            log_kv("create_table Request", create_payload)
            res = self.client.create_table(**create_payload)
            log_kv("create_table Response", res)

            # Verify creation with get_table
            time.sleep(0.5)
            table = self.client.get_table(self.test_table_id)
            log_kv("get_table (post-create)", {"table_id": table.table_id, "user_count": table.user_count})
            self.log_pass(name, f"Created and verified table: {self.test_table_id}")
            return True
        except Exception as e:
            self.log_fail(name, str(e))
            return False

    def test_4_create_authenticated_user(self):
        name = "Create Authenticated User"
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
            expected = self.accuracy  # ratio == 1 -> score equals accuracy
            log_kv("Score Check", {"actual": actual, "expected": expected})
            if abs(actual - expected) < 0.01:
                self.log_pass(name, f"User created with expected score={actual:.4f}")
            else:
                self.log_fail(name, f"Score mismatch: {actual:.4f} (expected={expected:.4f})")
        except Exception as e:
            self.log_fail(name, str(e))

    def test_5_retrieve_authenticated_user(self):
        name = "Retrieve Authenticated User"
        self.log_test_start(name)
        try:
            time.sleep(0.5)
            resp = self.client.list_users(table_id=self.test_table_id, limit=20)
            users = resp.get("users", [])
            log_kv("ListUsers Response Summary", {"returned_count": len(users)})
            for u in users:
                logger.info(f"UserRow: username={u.get('username')} score={u.get('moralCompassScore')} team={u.get('teamName')} tasks={u.get('tasksCompleted')}/{u.get('totalTasks')} q={u.get('questionsCorrect')}/{u.get('totalQuestions')}")
            me = next((u for u in users if u["username"] == self.username), None)
            if me:
                self.log_pass(name, "Authenticated user retrieved")
            else:
                self.log_fail(name, "Authenticated user not found in table")
        except Exception as e:
            self.log_fail(name, str(e))

    def test_6_verify_score_calc(self):
        name = "Verify Moral Compass Score Calculation"
        self.log_test_start(name)
        try:
            resp = self.client.list_users(table_id=self.test_table_id, limit=20)
            users = resp.get("users", [])
            me = next((u for u in users if u["username"] == self.username), None)
            if not me:
                self.log_fail(name, "Authenticated user not found")
                return
            actual = float(me.get("moralCompassScore", 0))
            expected = self.accuracy
            log_kv("Score Check", {"actual": actual, "expected": expected})
            if abs(actual - expected) < 0.01:
                self.log_pass(name, "Score matches expected calculation")
            else:
                self.log_fail(name, f"Score mismatch: {actual:.4f} (expected={expected:.4f})")
        except Exception as e:
            self.log_fail(name, str(e))

    def test_7_update_user_new_accuracy(self):
        name = "Update User with New Accuracy Score"
        self.log_test_start(name)
        try:
            new_accuracy = 0.80
            new_tasks = self.tasks + 5
            request_payload = {
                "table_id": self.test_table_id,
                "username": self.username,
                "metrics": {"accuracy": new_accuracy},
                "tasks_completed": new_tasks,
                "total_tasks": new_tasks,
                "questions_correct": 0,
                "total_questions": 0,
                "primary_metric": "accuracy",
                "team_name": self.team,
            }
            log_kv("UpdateMoralCompass Request (Update)", request_payload)
            res = self.client.update_moral_compass(**request_payload)
            log_kv("UpdateMoralCompass Response (Update)", res)
            actual = float(res.get("moralCompassScore", 0))
            expected = new_accuracy
            log_kv("Score Check (Update)", {"actual": actual, "expected": expected})
            if abs(actual - expected) < 0.01:
                self.log_pass(name, f"Score updated correctly: {actual:.4f}")
            else:
                self.log_fail(name, f"Score mismatch: {actual:.4f} (expected={expected:.4f})")
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

        # NEW: ensure table exists first
        if not self.ensure_table_exists():
            logger.error("Table setup failed, aborting subsequent tests.")
        else:
            self.test_4_create_authenticated_user()
            self.test_5_retrieve_authenticated_user()
            self.test_6_verify_score_calc()
            self.test_7_update_user_new_accuracy()

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

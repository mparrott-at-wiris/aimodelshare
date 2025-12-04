#!/usr/bin/env python3
"""
Comprehensive Integration Test for Moral Compass REST API and Lambda (Single-User Mode)

Scoring model note:
- The API computes moralCompassScore = primaryMetricValue * ((tasksCompleted + questionsCorrect) / (totalTasks + totalQuestions))
- With tasksCompleted == totalTasks and totalQuestions == 0 (and questionsCorrect == 0),
  the score equals the primary metric value (e.g., accuracy), not accuracy * tasks.
"""

import os
import sys
import time
import uuid
import logging
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from aimodelshare.moral_compass import MoralcompassApiClient, ApiClientError
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)


class MoralCompassIntegrationTest:
    def __init__(self, api_base_url: Optional[str] = None, session_id: Optional[str] = None):
        api_base_url = api_base_url or os.environ.get("MORAL_COMPASS_API_BASE_URL")
        if not api_base_url:
            raise ValueError("MORAL_COMPASS_API_BASE_URL must be set")

        session_id = session_id or os.environ.get("SESSION_ID")
        if not session_id:
            raise ValueError("SESSION_ID must be provided for single-user comprehensive test")

        logger.info("SESSION_ID provided, fetching token from session API...")
        self.auth_token = get_token_from_session(session_id)
        os.environ["JWT_AUTHORIZATION_TOKEN"] = self.auth_token
        self.username = _get_username_from_token(self.auth_token)
        logger.info(f"✓ Authenticated as user: {self.username}")

        self.client = MoralcompassApiClient(api_base_url=api_base_url, auth_token=self.auth_token)

        self.test_id = uuid.uuid4().hex[:8]
        self.test_table_id = os.environ.get("TEST_TABLE_ID") or f"test-mc-comprehensive-{self.test_id}"
        self.playground_url = os.environ.get("TEST_PLAYGROUND_URL") or f"https://example.com/playground/{self.test_table_id}"

        # Single-user config
        self.accuracy = 0.92
        self.tasks = 10
        self.team = "team-a"

        self.errors = []
        self.passed_tests = 0
        self.total_tests = 0

    def log_test_start(self, name): self.total_tests += 1; logger.info(f"\n{'='*70}\nTEST: {name}\n{'='*70}")
    def log_pass(self, name, msg=""): self.passed_tests += 1; logger.info(f"✅ PASS: {name}" + (f"\n   {msg}" if msg else ""))
    def log_fail(self, name, err): self.errors.append(f"{name}: {err}"); logger.error(f"❌ FAIL: {name}\n   {err}")

    def cleanup_table(self):
        try:
            self.client.delete_table(self.test_table_id)
            logger.info(f"Cleaned up test table: {self.test_table_id}")
        except Exception:
            pass

    def test_1_create_table(self):
        name = "Create Table with Playground URL"
        self.log_test_start(name)
        try:
            self.cleanup_table()
            time.sleep(1)
            res = self.client.create_table(self.test_table_id, f"Moral Compass Integration Test {self.test_id}", self.playground_url)
            if res.get("tableId") == self.test_table_id:
                self.log_pass(name, f"Created table: {self.test_table_id}")
            else:
                self.log_fail(name, f"Unexpected response: {res}")
        except Exception as e:
            self.log_fail(name, str(e))

    def test_2_get_table_no_auth(self):
        name = "Find Table by ID (No Auth)"
        self.log_test_start(name)
        try:
            client_no_auth = MoralcompassApiClient(api_base_url=self.client.api_base_url, auth_token=None)
            table = client_no_auth.get_table(self.test_table_id)
            if table.table_id == self.test_table_id:
                self.log_pass(name, f"Found table without auth: {table.table_id}")
            else:
                self.log_fail(name, f"Table ID mismatch: expected {self.test_table_id}, got {table.table_id}")
        except ApiClientError as e:
            if "401" in str(e) or "Authentication" in str(e):
                self.log_pass(name, "Auth is enabled - 401 expected for unauthenticated requests")
            else:
                self.log_fail(name, f"Unexpected error: {e}")
        except Exception as e:
            self.log_fail(name, str(e))

    def test_3_get_table_with_auth(self):
        name = "Find Table by ID (With Auth)"
        self.log_test_start(name)
        try:
            table = self.client.get_table(self.test_table_id)
            if table.table_id == self.test_table_id:
                self.log_pass(name, f"Found table with auth: {table.table_id}")
            else:
                self.log_fail(name, f"Table ID mismatch: expected {self.test_table_id}, got {table.table_id}")
        except Exception as e:
            self.log_fail(name, str(e))

    def test_4_create_authenticated_user(self):
        name = "Create Authenticated User"
        self.log_test_start(name)
        try:
            res = self.client.update_moral_compass(
                table_id=self.test_table_id,
                username=self.username,
                metrics={"accuracy": self.accuracy},
                tasks_completed=self.tasks,
                total_tasks=self.tasks,
                questions_correct=0,
                total_questions=0,
                primary_metric="accuracy",
                team_name=self.team
            )
            actual = float(res.get("moralCompassScore", 0))
            # Expected = accuracy * ((tasksCompleted + questionsCorrect) / (totalTasks + totalQuestions)) = accuracy
            expected = self.accuracy
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
            time.sleep(1)
            resp = self.client.list_users(table_id=self.test_table_id, limit=20)
            users = resp.get("users", [])
            me = next((u for u in users if u["username"] == self.username), None)
            if me:
                logger.info(f"   User: {me['username']} score={me.get('moralCompassScore', 'N/A')} team={me.get('teamName', 'N/A')}")
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
            expected = self.accuracy  # ratio = 1, expected score = accuracy
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
            res = self.client.update_moral_compass(
                table_id=self.test_table_id,
                username=self.username,
                metrics={"accuracy": new_accuracy},
                tasks_completed=new_tasks,
                total_tasks=new_tasks,
                questions_correct=0,
                total_questions=0,
                primary_metric="accuracy",
                team_name=self.team
            )
            actual = float(res.get("moralCompassScore", 0))
            expected = new_accuracy  # ratio = 1 again -> score equals accuracy
            if abs(actual - expected) < 0.01:
                self.log_pass(name, f"Score updated correctly: {actual:.4f}")
            else:
                self.log_fail(name, f"Score mismatch: {actual:.4f} (expected={expected:.4f})")
        except Exception as e:
            self.log_fail(name, str(e))

    def run_all(self):
        logger.info("\n" + "="*80)
        logger.info("MORAL COMPASS COMPREHENSIVE INTEGRATION TEST SUITE (Single-User)")
        logger.info("="*80)

        self.test_1_create_table()
        self.test_2_get_table_no_auth()
        self.test_3_get_table_with_auth()
        self.test_4_create_authenticated_user()
        self.test_5_retrieve_authenticated_user()
        self.test_6_verify_score_calc()
        self.test_7_update_user_new_accuracy()

        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests: {self.total_tests}")
        logger.info(f"Passed: {self.passed_tests}")
        logger.info(f"Failed: {len(self.errors)}")
        if self.errors:
            logger.error("\nFailed Tests:")
            for e in self.errors: logger.error(f"  • {e}")
            return False
        logger.info("\n✅ ALL TESTS PASSED!")
        return True


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
        try:
            suite.cleanup_table()
        except Exception:
            pass
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

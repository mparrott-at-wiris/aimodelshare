#!/usr/bin/env python3
"""
Comprehensive Integration Test for Moral Compass REST API and Lambda (Single-User Mode)

This test suite validates functionality needed for the detective bias app, scoped to the
authenticated user for CI runs:
1. Finding tables based on playground IDs (with and without auth)
2. Updating user information with accuracy scores and tasks (moral compass calculation)
3. Adding and retrieving team information for the authenticated user
4. Retrieving the authenticated user information
5. Computing a basic "individual ranking context" (presence and score)
6. Verifying team average when only one member exists

Environment Variables:
- MORAL_COMPASS_API_BASE_URL: Base URL for the API (required)
- SESSION_ID: Session ID (fetch token from session API; required for single-user mode)
- JWT_AUTHORIZATION_TOKEN: Optional auth token (ignored when SESSION_ID is present)
- TEST_PLAYGROUND_URL: Optional playground URL for table ID derivation
- TEST_TABLE_ID: Optional explicit table ID (overrides derivation)
"""

import os
import sys
import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

try:
    from aimodelshare.moral_compass import (
        MoralcompassApiClient,
        NotFoundError,
        ApiClientError
    )
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure aimodelshare package is installed.")
    sys.exit(1)


class MoralCompassIntegrationTest:
    """Single-user comprehensive integration test suite for Moral Compass API"""

    def __init__(self, api_base_url: Optional[str] = None, auth_token: Optional[str] = None, session_id: Optional[str] = None):
        self.api_base_url = api_base_url or os.environ.get("MORAL_COMPASS_API_BASE_URL")
        if not self.api_base_url:
            raise ValueError("MORAL_COMPASS_API_BASE_URL must be set")

        # Require session for single-user mode
        session_id = session_id or os.environ.get("SESSION_ID")
        if not session_id:
            raise ValueError("SESSION_ID must be provided for single-user comprehensive test")

        logger.info("SESSION_ID provided, fetching token from session API...")
        try:
            self.auth_token = get_token_from_session(session_id)
            os.environ["JWT_AUTHORIZATION_TOKEN"] = self.auth_token
            logger.info(f"✓ Token obtained from session API: {self._mask_token(self.auth_token)}")
            try:
                self.username = _get_username_from_token(self.auth_token)
                logger.info(f"✓ Authenticated as user: {self.username}")
            except Exception as e:
                logger.error(f"Could not extract username from token: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to get token from session ID: {e}")
            raise ValueError(f"Failed to authenticate with session ID: {e}")

        self.client = MoralcompassApiClient(api_base_url=self.api_base_url, auth_token=self.auth_token)

        # Test configuration
        self.test_id = uuid.uuid4().hex[:8]
        self.test_table_id = os.environ.get("TEST_TABLE_ID") or f"test-mc-comprehensive-{self.test_id}"
        self.playground_url = os.environ.get("TEST_PLAYGROUND_URL") or f"https://example.com/playground/{self.test_table_id}"

        # Single-user test data for the authenticated user
        self.user_config = {
            'username': self.username,
            'accuracy': 0.92,
            'tasks': 10,
            'team': 'team-a'
        }
        self.errors = []
        self.passed_tests = 0
        self.total_tests = 0

    def _mask_token(self, token: str) -> str:
        if not token:
            return ""
        return token[:6] + "***" if len(token) > 6 else "***"

    def log_test_start(self, test_name: str):
        logger.info(f"\n{'='*70}")
        logger.info(f"TEST: {test_name}")
        logger.info(f"{'='*70}")
        self.total_tests += 1

    def log_test_pass(self, test_name: str, message: str = ""):
        self.passed_tests += 1
        logger.info(f"✅ PASS: {test_name}")
        if message:
            logger.info(f"   {message}")

    def log_test_fail(self, test_name: str, error: str):
        self.errors.append(f"{test_name}: {error}")
        logger.error(f"❌ FAIL: {test_name}")
        logger.error(f"   {error}")

    def cleanup_test_table(self):
        try:
            self.client.delete_table(self.test_table_id)
            logger.info(f"Cleaned up test table: {self.test_table_id}")
        except NotFoundError:
            logger.info(f"Test table {self.test_table_id} does not exist (already cleaned)")
        except Exception as e:
            logger.warning(f"Failed to cleanup test table: {e}")

    def test_1_create_table_with_playground_url(self):
        test_name = "Create Table with Playground URL"
        self.log_test_start(test_name)
        try:
            self.cleanup_test_table()
            time.sleep(1)
            result = self.client.create_table(
                table_id=self.test_table_id,
                display_name=f"Moral Compass Integration Test {self.test_id}",
                playground_url=self.playground_url
            )
            if result.get('tableId') == self.test_table_id:
                self.log_test_pass(test_name, f"Created table: {self.test_table_id}")
            else:
                self.log_test_fail(test_name, f"Unexpected response: {result}")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_2_find_table_by_id_without_auth(self):
        test_name = "Find Table by ID (No Auth)"
        self.log_test_start(test_name)
        try:
            client_no_auth = MoralcompassApiClient(api_base_url=self.api_base_url, auth_token=None)
            table = client_no_auth.get_table(self.test_table_id)
            if table.table_id == self.test_table_id:
                self.log_test_pass(test_name, f"Found table without auth: {table.table_id}")
            else:
                self.log_test_fail(test_name, f"Table ID mismatch: expected {self.test_table_id}, got {table.table_id}")
        except ApiClientError as e:
            if "401" in str(e) or "Authentication" in str(e):
                self.log_test_pass(test_name, "Auth is enabled - 401 expected for unauthenticated requests")
            else:
                self.log_test_fail(test_name, f"Unexpected error: {e}")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_3_find_table_by_id_with_auth(self):
        test_name = "Find Table by ID (With Auth)"
        self.log_test_start(test_name)
        try:
            table = self.client.get_table(self.test_table_id)
            if table.table_id == self.test_table_id:
                self.log_test_pass(test_name, f"Found table with auth: {table.table_id}")
            else:
                self.log_test_fail(test_name, f"Table ID mismatch: expected {self.test_table_id}, got {table.table_id}")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_4_create_single_user(self):
        """Create/update authenticated user with metrics, tasks, and team"""
        test_name = "Create Authenticated User"
        self.log_test_start(test_name)
        cfg = self.user_config
        try:
            result = self.client.update_moral_compass(
                table_id=self.test_table_id,
                username=cfg['username'],
                metrics={'accuracy': cfg['accuracy']},
                tasks_completed=cfg['tasks'],
                total_tasks=cfg['tasks'],
                questions_correct=0,
                total_questions=0,
                primary_metric='accuracy',
                team_name=cfg['team']
            )
            expected_score = cfg['accuracy'] * cfg['tasks']
            actual_score = float(result.get('moralCompassScore', 0))
            if abs(actual_score - expected_score) < 0.01:
                self.log_test_pass(test_name, f"User created with expected score={actual_score:.4f}")
            else:
                self.log_test_fail(test_name, f"Score mismatch: {actual_score:.4f} (expected={expected_score:.4f})")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_5_retrieve_authenticated_user(self):
        test_name = "Retrieve Authenticated User"
        self.log_test_start(test_name)
        try:
            time.sleep(1)
            resp = self.client.list_users(table_id=self.test_table_id, limit=20)
            users = resp.get('users', [])
            me = next((u for u in users if u['username'] == self.username), None)
            if me:
                logger.info(f"   User: {me['username']} score={me.get('moralCompassScore', 'N/A')} team={me.get('teamName', 'N/A')}")
                self.log_test_pass(test_name, "Authenticated user retrieved")
            else:
                self.log_test_fail(test_name, "Authenticated user not found in table")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_6_verify_moral_compass_calculation(self):
        test_name = "Verify Moral Compass Score Calculation"
        self.log_test_start(test_name)
        try:
            resp = self.client.list_users(table_id=self.test_table_id, limit=20)
            users = resp.get('users', [])
            me = next((u for u in users if u['username'] == self.username), None)
            if not me:
                self.log_test_fail(test_name, "Authenticated user not found")
                return
            expected_score = self.user_config['accuracy'] * self.user_config['tasks']
            actual_score = float(me.get('moralCompassScore', 0))
            if abs(actual_score - expected_score) < 0.01:
                self.log_test_pass(test_name, "Score matches expected calculation")
            else:
                self.log_test_fail(test_name, f"Score mismatch: {actual_score:.4f} (expected={expected_score:.4f})")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_7_update_user_with_new_accuracy(self):
        test_name = "Update User with New Accuracy Score"
        self.log_test_start(test_name)
        try:
            new_accuracy = 0.80
            new_tasks = self.user_config['tasks'] + 5
            result = self.client.update_moral_compass(
                table_id=self.test_table_id,
                username=self.username,
                metrics={'accuracy': new_accuracy},
                tasks_completed=new_tasks,
                total_tasks=new_tasks,
                questions_correct=0,
                total_questions=0,
                primary_metric='accuracy',
                team_name=self.user_config['team']
            )
            new_score = float(result.get('moralCompassScore', 0))
            expected_score = new_accuracy * new_tasks
            if abs(new_score - expected_score) < 0.01:
                self.log_test_pass(test_name, f"Score updated correctly: {new_score:.4f}")
            else:
                self.log_test_fail(test_name, f"Score mismatch: {new_score:.4f} (expected={expected_score:.4f})")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_8_verify_team_information(self):
        test_name = "Verify Team Information"
        self.log_test_start(test_name)
        try:
            resp = self.client.list_users(table_id=self.test_table_id, limit=20)
            users = resp.get('users', [])
            me = next((u for u in users if u['username'] == self.username), None)
            if not me:
                self.log_test_fail(test_name, "Authenticated user not found")
                return
            expected_team = self.user_config['team']
            actual_team = me.get('teamName')
            if actual_team == expected_team:
                self.log_test_pass(test_name, f"Team assignment is correct: {actual_team}")
            else:
                self.log_test_fail(test_name, f"Team mismatch: {actual_team} (expected {expected_team})")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_9_individual_context(self):
        """Sanity check that at least one user (self) is present with a score."""
        test_name = "Individual Ranking Context (Single User)"
        self.log_test_start(test_name)
        try:
            resp = self.client.list_users(table_id=self.test_table_id, limit=20)
            users = resp.get('users', [])
            me = next((u for u in users if u['username'] == self.username), None)
            if me and float(me.get('moralCompassScore', 0)) > 0:
                self.log_test_pass(test_name, "Authenticated user has a positive score")
            else:
                self.log_test_fail(test_name, "Authenticated user missing or score not positive")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def test_10_team_average_single_member(self):
        """With only one member on team, team average equals the user's score."""
        test_name = "Team Average (Single Member)"
        self.log_test_start(test_name)
        try:
            resp = self.client.list_users(table_id=self.test_table_id, limit=20)
            users = resp.get('users', [])
            team = self.user_config['team']
            team_users = [u for u in users if u.get('teamName') == team]
            if not team_users:
                self.log_test_fail(test_name, f"No users found for team {team}")
                return
            avg = sum(float(u.get('moralCompassScore', 0)) for u in team_users) / len(team_users)
            me = next((u for u in team_users if u['username'] == self.username), None)
            if me is None:
                self.log_test_fail(test_name, "Authenticated user not found in team list")
                return
            my_score = float(me.get('moralCompassScore', 0))
            if abs(avg - my_score) < 0.01:
                self.log_test_pass(test_name, "Team average equals user's score (single member)")
            else:
                self.log_test_fail(test_name, f"Average mismatch: {avg:.4f} vs my score {my_score:.4f}")
        except Exception as e:
            self.log_test_fail(test_name, str(e))

    def run_all_tests(self):
        logger.info("\n" + "="*80)
        logger.info("MORAL COMPASS COMPREHENSIVE INTEGRATION TEST SUITE (Single-User)")
        logger.info("="*80)
        logger.info(f"API Base URL: {self.api_base_url}")
        logger.info(f"Test Table ID: {self.test_table_id}")
        logger.info(f"Authenticated User: {self.username}")
        logger.info("="*80 + "\n")

        self.test_1_create_table_with_playground_url()
        self.test_2_find_table_by_id_without_auth()
        self.test_3_find_table_by_id_with_auth()
        self.test_4_create_single_user()
        self.test_5_retrieve_authenticated_user()
        self.test_6_verify_moral_compass_calculation()
        self.test_7_update_user_with_new_accuracy()
        self.test_8_verify_team_information()
        self.test_9_individual_context()
        self.test_10_team_average_single_member()

        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests: {self.total_tests}")
        logger.info(f"Passed: {self.passed_tests}")
        logger.info(f"Failed: {len(self.errors)}")

        if self.errors:
            logger.error("\nFailed Tests:")
            for error in self.errors:
                logger.error(f"  • {error}")
            logger.info("\n" + "="*80)
            return False
        else:
            logger.info("\n✅ ALL TESTS PASSED!")
            logger.info("="*80)
            return True

    def cleanup(self):
        logger.info("\nCleaning up test resources...")
        self.cleanup_test_table()


def main():
    api_base_url = os.environ.get("MORAL_COMPASS_API_BASE_URL")
    if not api_base_url:
        logger.error("MORAL_COMPASS_API_BASE_URL environment variable is required")
        logger.error("Example: export MORAL_COMPASS_API_BASE_URL=https://api.example.com")
        sys.exit(1)

    test_suite = MoralCompassIntegrationTest()

    try:
        success = test_suite.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        try:
            test_suite.cleanup()
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


if __name__ == "__main__":
    main()

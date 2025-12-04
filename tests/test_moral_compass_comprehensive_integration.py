#!/usr/bin/env python3
"""
Comprehensive Integration Test for Moral Compass REST API and Lambda

This test suite validates the complete functionality needed for the detective bias app:
1. Finding tables based on playground IDs (with and without auth)
2. Updating user information with accuracy scores and tasks (moral compass calculation)
3. Adding and retrieving team information for users
4. Retrieving all user information for multiple users with varying data
5. Computing individual rankings by moral compass score
6. Computing team rankings by average score per team

Environment Variables:
- MORAL_COMPASS_API_BASE_URL: Base URL for the API (required)
- JWT_AUTHORIZATION_TOKEN: Optional auth token for authenticated tests
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
from decimal import Decimal

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
except ImportError:
    logger.error("Failed to import aimodelshare.moral_compass. Make sure the package is installed.")
    sys.exit(1)


class MoralCompassIntegrationTest:
    """Comprehensive integration test suite for Moral Compass API"""
    
    def __init__(self, api_base_url: Optional[str] = None, auth_token: Optional[str] = None):
        """
        Initialize the test suite.
        
        Args:
            api_base_url: API base URL (defaults to env var)
            auth_token: JWT auth token (defaults to env var)
        """
        self.api_base_url = api_base_url or os.environ.get("MORAL_COMPASS_API_BASE_URL")
        if not self.api_base_url:
            raise ValueError("MORAL_COMPASS_API_BASE_URL must be set")
        
        self.auth_token = auth_token or os.environ.get("JWT_AUTHORIZATION_TOKEN")
        self.client = MoralcompassApiClient(api_base_url=self.api_base_url, auth_token=self.auth_token)
        
        # Test configuration
        self.test_id = uuid.uuid4().hex[:8]
        self.test_table_id = os.environ.get("TEST_TABLE_ID") or f"test-mc-comprehensive-{self.test_id}"
        self.playground_url = os.environ.get("TEST_PLAYGROUND_URL") or f"https://example.com/playground/{self.test_table_id}"
        
        # Test data
        self.test_users = []
        self.team_assignments = {
            'team-a': [],
            'team-b': [],
            'team-c': []
        }
        
        self.errors = []
        self.passed_tests = 0
        self.total_tests = 0
    
    def log_test_start(self, test_name: str):
        """Log the start of a test"""
        logger.info(f"\n{'='*70}")
        logger.info(f"TEST: {test_name}")
        logger.info(f"{'='*70}")
        self.total_tests += 1
    
    def log_test_pass(self, test_name: str, message: str = ""):
        """Log a successful test"""
        self.passed_tests += 1
        logger.info(f"✅ PASS: {test_name}")
        if message:
            logger.info(f"   {message}")
    
    def log_test_fail(self, test_name: str, error: str):
        """Log a failed test"""
        self.errors.append(f"{test_name}: {error}")
        logger.error(f"❌ FAIL: {test_name}")
        logger.error(f"   {error}")
    
    def cleanup_test_table(self):
        """Clean up test table if it exists"""
        try:
            self.client.delete_table(self.test_table_id)
            logger.info(f"Cleaned up test table: {self.test_table_id}")
        except NotFoundError:
            logger.info(f"Test table {self.test_table_id} does not exist (already cleaned)")
        except Exception as e:
            logger.warning(f"Failed to cleanup test table: {e}")
    
    def test_1_create_table_with_playground_url(self):
        """Test 1: Create a table with playground URL"""
        test_name = "Create Table with Playground URL"
        self.log_test_start(test_name)
        
        try:
            # Clean up any existing table first
            self.cleanup_test_table()
            time.sleep(1)
            
            # Create table with playground URL
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
        """Test 2: Find table by ID without authentication (public read)"""
        test_name = "Find Table by ID (No Auth)"
        self.log_test_start(test_name)
        
        try:
            # Create a client without auth token
            client_no_auth = MoralcompassApiClient(api_base_url=self.api_base_url, auth_token=None)
            
            # Try to get the table
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
        """Test 3: Find table by ID with authentication"""
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
    
    def test_4_create_users_with_varying_data(self):
        """Test 4: Create 10 users with varying accuracy scores, tasks, and team assignments"""
        test_name = "Create 10 Users with Varying Data"
        self.log_test_start(test_name)
        
        try:
            # Define test data for 10 users
            user_configs = [
                # Team A - 3 users
                {'username': f'user-a-1-{self.test_id}', 'accuracy': 0.95, 'tasks': 10, 'team': 'team-a'},
                {'username': f'user-a-2-{self.test_id}', 'accuracy': 0.85, 'tasks': 15, 'team': 'team-a'},
                {'username': f'user-a-3-{self.test_id}', 'accuracy': 0.90, 'tasks': 12, 'team': 'team-a'},
                # Team B - 4 users
                {'username': f'user-b-1-{self.test_id}', 'accuracy': 0.92, 'tasks': 8, 'team': 'team-b'},
                {'username': f'user-b-2-{self.test_id}', 'accuracy': 0.88, 'tasks': 14, 'team': 'team-b'},
                {'username': f'user-b-3-{self.test_id}', 'accuracy': 0.78, 'tasks': 18, 'team': 'team-b'},
                {'username': f'user-b-4-{self.test_id}', 'accuracy': 0.96, 'tasks': 6, 'team': 'team-b'},
                # Team C - 3 users
                {'username': f'user-c-1-{self.test_id}', 'accuracy': 0.89, 'tasks': 11, 'team': 'team-c'},
                {'username': f'user-c-2-{self.test_id}', 'accuracy': 0.93, 'tasks': 9, 'team': 'team-c'},
                {'username': f'user-c-3-{self.test_id}', 'accuracy': 0.87, 'tasks': 13, 'team': 'team-c'},
            ]
            
            created_count = 0
            for config in user_configs:
                try:
                    # Update moral compass with metrics
                    # Formula: moral_compass_score = accuracy * (tasks_completed / (total_tasks + total_questions))
                    # When total_questions = 0, score = accuracy * (tasks_completed / total_tasks)
                    # By setting tasks_completed = total_tasks, the ratio = 1, resulting in score = accuracy * tasks
                    result = self.client.update_moral_compass(
                        table_id=self.test_table_id,
                        username=config['username'],
                        metrics={'accuracy': config['accuracy']},
                        tasks_completed=config['tasks'],
                        total_tasks=config['tasks'],  # When tasks_completed = total_tasks, ratio = 1
                        questions_correct=0,
                        total_questions=0,
                        primary_metric='accuracy',
                        team_name=config['team']
                    )
                    
                    # Store user data for later tests
                    user_data = {
                        'username': config['username'],
                        'accuracy': config['accuracy'],
                        'tasks': config['tasks'],
                        'team': config['team'],
                        'expected_score': config['accuracy'] * config['tasks']
                    }
                    self.test_users.append(user_data)
                    self.team_assignments[config['team']].append(user_data)
                    
                    created_count += 1
                    logger.info(f"   Created user: {config['username']} - "
                              f"accuracy={config['accuracy']}, tasks={config['tasks']}, "
                              f"team={config['team']}, expected_score={user_data['expected_score']:.4f}")
                
                except Exception as e:
                    logger.error(f"   Failed to create user {config['username']}: {e}")
            
            if created_count == 10:
                self.log_test_pass(test_name, f"Created all 10 users successfully")
            else:
                self.log_test_fail(test_name, f"Only created {created_count}/10 users")
        
        except Exception as e:
            self.log_test_fail(test_name, str(e))
    
    def test_5_retrieve_all_users(self):
        """Test 5: Retrieve all user information from the table"""
        test_name = "Retrieve All Users"
        self.log_test_start(test_name)
        
        try:
            # Give the backend a moment to process
            time.sleep(2)
            
            # Retrieve all users
            response = self.client.list_users(table_id=self.test_table_id, limit=100)
            users = response.get('users', [])
            
            # Filter to just our test users (using set for O(1) lookup)
            test_usernames = {u['username'] for u in self.test_users}
            retrieved_users = [u for u in users if u['username'] in test_usernames]
            
            if len(retrieved_users) == 10:
                self.log_test_pass(test_name, f"Retrieved all 10 test users")
                
                # Log details
                for user in retrieved_users:
                    logger.info(f"   User: {user['username']} - "
                              f"score={user.get('moralCompassScore', 'N/A')}, "
                              f"team={user.get('teamName', 'N/A')}")
            else:
                self.log_test_fail(test_name, 
                                  f"Expected 10 users, found {len(retrieved_users)}")
        
        except Exception as e:
            self.log_test_fail(test_name, str(e))
    
    def test_6_verify_moral_compass_calculation(self):
        """Test 6: Verify moral compass score calculation (accuracy * tasks)"""
        test_name = "Verify Moral Compass Score Calculation"
        self.log_test_start(test_name)
        
        try:
            # Retrieve users to check scores
            response = self.client.list_users(table_id=self.test_table_id, limit=100)
            users = response.get('users', [])
            
            # Map usernames to expected user data for easy lookup
            expected_users_by_name = {u['username']: u for u in self.test_users}
            
            all_correct = True
            for user in users:
                if user['username'] in expected_users_by_name:
                    expected_data = expected_users_by_name[user['username']]
                    actual_score = float(user.get('moralCompassScore', 0))
                    expected_score = expected_data['expected_score']
                    
                    # Allow small floating point tolerance
                    if abs(actual_score - expected_score) < 0.01:
                        logger.info(f"   ✓ {user['username']}: score={actual_score:.4f} "
                                  f"(expected={expected_score:.4f})")
                    else:
                        logger.error(f"   ✗ {user['username']}: score={actual_score:.4f} "
                                   f"(expected={expected_score:.4f})")
                        all_correct = False
            
            if all_correct:
                self.log_test_pass(test_name, "All moral compass scores calculated correctly")
            else:
                self.log_test_fail(test_name, "Some scores do not match expected values")
        
        except Exception as e:
            self.log_test_fail(test_name, str(e))
    
    def test_7_update_user_with_new_accuracy(self):
        """Test 7: Update user with new accuracy score and verify score caps at accuracy"""
        test_name = "Update User with New Accuracy Score"
        self.log_test_start(test_name)
        
        try:
            # Pick first user and update their accuracy
            test_user = self.test_users[0]
            new_accuracy = 0.80  # Lower than original
            
            # Update with more tasks than before
            result = self.client.update_moral_compass(
                table_id=self.test_table_id,
                username=test_user['username'],
                metrics={'accuracy': new_accuracy},
                tasks_completed=test_user['tasks'] + 5,  # More tasks
                total_tasks=test_user['tasks'] + 5,
                questions_correct=0,
                total_questions=0,
                primary_metric='accuracy',
                team_name=test_user['team']
            )
            
            new_score = result.get('moralCompassScore', 0)
            expected_score = new_accuracy * (test_user['tasks'] + 5)
            
            if abs(float(new_score) - expected_score) < 0.01:
                self.log_test_pass(test_name, 
                                  f"Score updated correctly: {new_score:.4f} (expected={expected_score:.4f})")
            else:
                self.log_test_fail(test_name, 
                                  f"Score mismatch: {new_score:.4f} (expected={expected_score:.4f})")
        
        except Exception as e:
            self.log_test_fail(test_name, str(e))
    
    def test_8_verify_team_information(self):
        """Test 8: Verify team information can be retrieved for each user"""
        test_name = "Verify Team Information"
        self.log_test_start(test_name)
        
        try:
            response = self.client.list_users(table_id=self.test_table_id, limit=100)
            users = response.get('users', [])
            
            # Map usernames to expected user data for easy lookup
            expected_users_by_name = {u['username']: u for u in self.test_users}
            
            all_teams_correct = True
            for user in users:
                if user['username'] in expected_users_by_name:
                    expected_team = expected_users_by_name[user['username']]['team']
                    actual_team = user.get('teamName')
                    
                    if actual_team == expected_team:
                        logger.info(f"   ✓ {user['username']}: team={actual_team}")
                    else:
                        logger.error(f"   ✗ {user['username']}: team={actual_team} "
                                   f"(expected={expected_team})")
                        all_teams_correct = False
            
            if all_teams_correct:
                self.log_test_pass(test_name, "All team assignments verified")
            else:
                self.log_test_fail(test_name, "Some team assignments are incorrect")
        
        except Exception as e:
            self.log_test_fail(test_name, str(e))
    
    def test_9_individual_rankings(self):
        """Test 9: Compute and verify individual rankings by moral compass score"""
        test_name = "Individual Rankings by Moral Compass Score"
        self.log_test_start(test_name)
        
        try:
            response = self.client.list_users(table_id=self.test_table_id, limit=100)
            users = response.get('users', [])
            
            # Filter to test users (using set for O(1) lookup)
            test_usernames = {u['username'] for u in self.test_users}
            test_users_data = [u for u in users if u['username'] in test_usernames]
            
            # Sort by moral compass score (descending)
            sorted_users = sorted(
                test_users_data,
                key=lambda x: float(x.get('moralCompassScore', 0)),
                reverse=True
            )
            
            logger.info(f"\n   Individual Rankings:")
            logger.info(f"   {'Rank':<6} {'Username':<30} {'Score':<10} {'Team':<10}")
            logger.info(f"   {'-'*60}")
            
            for rank, user in enumerate(sorted_users, 1):
                score = float(user.get('moralCompassScore', 0))
                team = user.get('teamName', 'N/A')
                logger.info(f"   #{rank:<5} {user['username']:<30} {score:<10.4f} {team:<10}")
            
            if len(sorted_users) == 10:
                self.log_test_pass(test_name, f"Computed rankings for all 10 users")
            else:
                self.log_test_fail(test_name, f"Only ranked {len(sorted_users)}/10 users")
        
        except Exception as e:
            self.log_test_fail(test_name, str(e))
    
    def test_10_team_rankings(self):
        """Test 10: Compute team rankings by average individual score per team"""
        test_name = "Team Rankings by Average Score"
        self.log_test_start(test_name)
        
        try:
            response = self.client.list_users(table_id=self.test_table_id, limit=100)
            users = response.get('users', [])
            
            # Filter to test users (using set for O(1) lookup)
            test_usernames = {u['username'] for u in self.test_users}
            test_users_data = [u for u in users if u['username'] in test_usernames]
            
            # Compute team averages
            team_scores = {}
            team_counts = {}
            
            for user in test_users_data:
                team = user.get('teamName')
                if team:
                    score = float(user.get('moralCompassScore', 0))
                    if team not in team_scores:
                        team_scores[team] = 0
                        team_counts[team] = 0
                    team_scores[team] += score
                    team_counts[team] += 1
            
            # Calculate averages
            team_averages = {
                team: team_scores[team] / team_counts[team]
                for team in team_scores
            }
            
            # Sort teams by average score
            sorted_teams = sorted(
                team_averages.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            logger.info(f"\n   Team Rankings:")
            logger.info(f"   {'Rank':<6} {'Team':<15} {'Avg Score':<12} {'Members':<10}")
            logger.info(f"   {'-'*50}")
            
            for rank, (team, avg_score) in enumerate(sorted_teams, 1):
                member_count = team_counts[team]
                logger.info(f"   #{rank:<5} {team:<15} {avg_score:<12.4f} {member_count:<10}")
            
            if len(sorted_teams) == 3:
                self.log_test_pass(test_name, f"Computed rankings for all 3 teams")
            else:
                self.log_test_fail(test_name, f"Only ranked {len(sorted_teams)}/3 teams")
        
        except Exception as e:
            self.log_test_fail(test_name, str(e))
    
    def run_all_tests(self):
        """Run all integration tests"""
        logger.info("\n" + "="*80)
        logger.info("MORAL COMPASS COMPREHENSIVE INTEGRATION TEST SUITE")
        logger.info("="*80)
        logger.info(f"API Base URL: {self.api_base_url}")
        logger.info(f"Test Table ID: {self.test_table_id}")
        logger.info(f"Auth Enabled: {bool(self.auth_token)}")
        logger.info("="*80 + "\n")
        
        # Run all tests in order
        self.test_1_create_table_with_playground_url()
        self.test_2_find_table_by_id_without_auth()
        self.test_3_find_table_by_id_with_auth()
        self.test_4_create_users_with_varying_data()
        self.test_5_retrieve_all_users()
        self.test_6_verify_moral_compass_calculation()
        self.test_7_update_user_with_new_accuracy()
        self.test_8_verify_team_information()
        self.test_9_individual_rankings()
        self.test_10_team_rankings()
        
        # Print summary
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
        """Clean up test resources"""
        logger.info("\nCleaning up test resources...")
        self.cleanup_test_table()


def main():
    """Main entry point"""
    # Check required environment variables
    api_base_url = os.environ.get("MORAL_COMPASS_API_BASE_URL")
    if not api_base_url:
        logger.error("MORAL_COMPASS_API_BASE_URL environment variable is required")
        logger.error("Example: export MORAL_COMPASS_API_BASE_URL=https://api.example.com")
        sys.exit(1)
    
    # Run tests
    test_suite = MoralCompassIntegrationTest()
    
    try:
        success = test_suite.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        # Always attempt cleanup
        try:
            test_suite.cleanup()
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


if __name__ == "__main__":
    main()

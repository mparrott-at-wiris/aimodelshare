#!/usr/bin/env python3
"""
Integration tests for Moral Compass dynamic metric support.

Tests the new multi-metric functionality including:
- put_user_moral_compass endpoint
- Dynamic metric tracking
- Moral compass score calculation
- Leaderboard sorting by moralCompassScore
- ChallengeManager class

Run with: pytest -m integration tests/test_moral_compass_dynamic_metrics.py
"""

import pytest
import uuid
from typing import Generator

from aimodelshare.moral_compass import (
    MoralcompassApiClient,
    ChallengeManager,
    NotFoundError,
)


@pytest.fixture(scope="module")
def client() -> MoralcompassApiClient:
    """Create a client instance for testing"""
    return MoralcompassApiClient()


@pytest.fixture
def test_table_id() -> str:
    """Generate a unique test table ID"""
    return f"test-metrics-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_username() -> str:
    """Generate a unique test username"""
    return f"testuser-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def created_table(client: MoralcompassApiClient, test_table_id: str) -> Generator[str, None, None]:
    """Create a test table and clean it up after the test"""
    client.create_table(test_table_id, f"Test Metrics Table {test_table_id}")
    yield test_table_id
    try:
        client.patch_table(test_table_id, is_archived=True)
    except Exception:
        pass


class TestMoralCompassDynamicMetrics:
    """Integration tests for dynamic metric support"""
    
    @pytest.mark.integration
    def test_update_moral_compass_basic(self, client: MoralcompassApiClient, 
                                       created_table: str, test_username: str):
        """Test basic moral compass update with single metric"""
        result = client.update_moral_compass(
            table_id=created_table,
            username=test_username,
            metrics={"accuracy": 0.85},
            tasks_completed=5,
            total_tasks=10
        )
        
        assert result["username"] == test_username
        assert "moralCompassScore" in result
        assert "metrics" in result
        assert result["metrics"]["accuracy"] == 0.85
        assert result["primaryMetric"] == "accuracy"
        
        # Verify score calculation: 0.85 * (5/10) = 0.425
        expected_score = 0.85 * (5 / 10)
        assert abs(result["moralCompassScore"] - expected_score) < 0.0001
    
    @pytest.mark.integration
    def test_update_moral_compass_multiple_metrics(self, client: MoralcompassApiClient,
                                                   created_table: str, test_username: str):
        """Test moral compass update with multiple metrics"""
        result = client.update_moral_compass(
            table_id=created_table,
            username=test_username,
            metrics={
                "accuracy": 0.87,
                "fairness": 0.92,
                "robustness": 0.84
            },
            primary_metric="fairness",
            tasks_completed=3,
            total_tasks=5,
            questions_correct=8,
            total_questions=10
        )
        
        assert result["primaryMetric"] == "fairness"
        assert len(result["metrics"]) == 3
        
        # Verify score: 0.92 * ((3 + 8) / (5 + 10)) = 0.92 * 0.7333 = 0.6747
        expected_score = 0.92 * ((3 + 8) / (5 + 10))
        assert abs(result["moralCompassScore"] - expected_score) < 0.0001
    
    @pytest.mark.integration
    def test_update_moral_compass_default_primary(self, client: MoralcompassApiClient,
                                                  created_table: str, test_username: str):
        """Test that 'accuracy' becomes primary metric by default"""
        result = client.update_moral_compass(
            table_id=created_table,
            username=test_username,
            metrics={
                "robustness": 0.80,
                "accuracy": 0.88,
                "fairness": 0.90
            },
            tasks_completed=2,
            total_tasks=4
        )
        
        # Should default to 'accuracy' even though it's not first alphabetically
        assert result["primaryMetric"] == "accuracy"
        
        # Score should use accuracy: 0.88 * (2/4) = 0.44
        expected_score = 0.88 * (2 / 4)
        assert abs(result["moralCompassScore"] - expected_score) < 0.0001
    
    @pytest.mark.integration
    def test_update_moral_compass_no_accuracy_default(self, client: MoralcompassApiClient,
                                                      created_table: str, test_username: str):
        """Test primary metric defaults to first sorted key when no accuracy"""
        result = client.update_moral_compass(
            table_id=created_table,
            username=test_username,
            metrics={
                "robustness": 0.80,
                "fairness": 0.90
            },
            tasks_completed=1,
            total_tasks=2
        )
        
        # Should default to 'fairness' (first alphabetically)
        assert result["primaryMetric"] == "fairness"
        
        # Score: 0.90 * (1/2) = 0.45
        expected_score = 0.90 * (1 / 2)
        assert abs(result["moralCompassScore"] - expected_score) < 0.0001
    
    @pytest.mark.integration
    def test_update_moral_compass_zero_denominator(self, client: MoralcompassApiClient,
                                                   created_table: str, test_username: str):
        """Test that zero denominator results in 0.0 score"""
        result = client.update_moral_compass(
            table_id=created_table,
            username=test_username,
            metrics={"accuracy": 0.95},
            tasks_completed=0,
            total_tasks=0,
            questions_correct=0,
            total_questions=0
        )
        
        assert result["moralCompassScore"] == 0.0
    
    @pytest.mark.integration
    def test_list_users_includes_moral_compass_fields(self, client: MoralcompassApiClient,
                                                      created_table: str, test_username: str):
        """Test that list_users includes moral compass fields"""
        # Create user with moral compass data
        client.update_moral_compass(
            table_id=created_table,
            username=test_username,
            metrics={"accuracy": 0.90, "fairness": 0.95},
            primary_metric="accuracy",
            tasks_completed=4,
            total_tasks=5,
            questions_correct=9,
            total_questions=10
        )
        
        # List users
        response = client.list_users(created_table)
        users = response["users"]
        
        # Find our user
        user = next((u for u in users if u["username"] == test_username), None)
        assert user is not None
        
        # Verify all fields present
        assert "moralCompassScore" in user
        assert "metrics" in user
        assert "primaryMetric" in user
        assert "tasksCompleted" in user
        assert "totalTasks" in user
        assert "questionsCorrect" in user
        assert "totalQuestions" in user
        
        assert user["metrics"]["accuracy"] == 0.90
        assert user["primaryMetric"] == "accuracy"
    
    @pytest.mark.integration
    def test_leaderboard_sorting_by_moral_compass_score(self, client: MoralcompassApiClient,
                                                       created_table: str):
        """Test that users are sorted by moralCompassScore"""
        # Create multiple users with different scores
        users_data = [
            ("user_low", {"accuracy": 0.70}, 2, 10, 0.14),   # 0.70 * 0.2 = 0.14
            ("user_high", {"accuracy": 0.95}, 9, 10, 0.855), # 0.95 * 0.9 = 0.855
            ("user_mid", {"accuracy": 0.80}, 5, 10, 0.40),   # 0.80 * 0.5 = 0.40
        ]
        
        for username, metrics, tasks_done, tasks_total, expected_score in users_data:
            result = client.update_moral_compass(
                table_id=created_table,
                username=username,
                metrics=metrics,
                tasks_completed=tasks_done,
                total_tasks=tasks_total
            )
            # Verify score calculation
            assert abs(result["moralCompassScore"] - expected_score) < 0.0001
        
        # List users (should be sorted by score descending)
        response = client.list_users(created_table)
        users = response["users"]
        
        # Extract usernames in order
        usernames = [u["username"] for u in users]
        
        # Should be ordered: user_high, user_mid, user_low
        assert usernames.index("user_high") < usernames.index("user_mid")
        assert usernames.index("user_mid") < usernames.index("user_low")
    
    @pytest.mark.integration
    def test_backward_compatibility_with_legacy_users(self, client: MoralcompassApiClient,
                                                     created_table: str):
        """Test that legacy users (without moral compass) still work"""
        # Create a legacy user
        legacy_user = "legacy_user"
        client.put_user(created_table, legacy_user, submission_count=10, total_count=50)
        
        # Create a new moral compass user
        new_user = "new_user"
        client.update_moral_compass(
            table_id=created_table,
            username=new_user,
            metrics={"accuracy": 0.80},
            tasks_completed=5,
            total_tasks=10
        )
        
        # List all users
        response = client.list_users(created_table)
        users = response["users"]
        
        # Both should be present
        legacy = next((u for u in users if u["username"] == legacy_user), None)
        new = next((u for u in users if u["username"] == new_user), None)
        
        assert legacy is not None
        assert new is not None
        
        # Legacy user should not have moral compass fields
        assert "moralCompassScore" not in legacy
        assert "metrics" not in legacy
        
        # New user should have moral compass fields
        assert "moralCompassScore" in new
        assert "metrics" in new
    
    @pytest.mark.integration
    def test_invalid_primary_metric(self, client: MoralcompassApiClient,
                                   created_table: str, test_username: str):
        """Test that invalid primary metric returns error"""
        # This should fail at the API level - we expect a 400 error
        from requests.exceptions import HTTPError
        
        with pytest.raises((HTTPError, Exception)):
            client.update_moral_compass(
                table_id=created_table,
                username=test_username,
                metrics={"accuracy": 0.85},
                primary_metric="nonexistent_metric",
                tasks_completed=5,
                total_tasks=10
            )
    
    @pytest.mark.integration
    def test_empty_metrics_error(self, client: MoralcompassApiClient,
                                created_table: str, test_username: str):
        """Test that empty metrics dict returns error"""
        from requests.exceptions import HTTPError
        
        with pytest.raises((HTTPError, Exception)):
            client.update_moral_compass(
                table_id=created_table,
                username=test_username,
                metrics={},
                tasks_completed=5,
                total_tasks=10
            )


class TestChallengeManager:
    """Tests for ChallengeManager class"""
    
    @pytest.mark.integration
    def test_challenge_manager_basic(self, client: MoralcompassApiClient,
                                    created_table: str, test_username: str):
        """Test basic ChallengeManager functionality"""
        manager = ChallengeManager(created_table, test_username, api_client=client)
        
        # Set metrics
        manager.set_metric("accuracy", 0.85, primary=True)
        manager.set_metric("fairness", 0.90)
        
        # Set progress
        manager.set_progress(tasks_completed=3, total_tasks=5)
        
        # Verify local score
        expected_local_score = 0.85 * (3 / 5)
        assert abs(manager.get_local_score() - expected_local_score) < 0.0001
        
        # Sync to server
        result = manager.sync()
        
        assert result["username"] == test_username
        assert abs(result["moralCompassScore"] - expected_local_score) < 0.0001
    
    @pytest.mark.integration
    def test_challenge_manager_auto_primary(self, client: MoralcompassApiClient,
                                           created_table: str, test_username: str):
        """Test that first metric becomes primary automatically"""
        manager = ChallengeManager(created_table, test_username, api_client=client)
        
        # Don't specify primary
        manager.set_metric("accuracy", 0.88)
        
        assert manager.primary_metric == "accuracy"
        
        manager.set_metric("fairness", 0.92)
        
        # Should still be accuracy (first set)
        assert manager.primary_metric == "accuracy"
    
    @pytest.mark.integration
    def test_challenge_manager_progressive_updates(self, client: MoralcompassApiClient,
                                                  created_table: str, test_username: str):
        """Test progressive updates with ChallengeManager"""
        manager = ChallengeManager(created_table, test_username, api_client=client)
        
        # Stage 1
        manager.set_metric("accuracy", 0.80, primary=True)
        manager.set_progress(tasks_completed=1, total_tasks=5)
        result1 = manager.sync()
        assert abs(result1["moralCompassScore"] - 0.16) < 0.0001
        
        # Stage 2
        manager.set_metric("accuracy", 0.85)
        manager.set_progress(tasks_completed=3, total_tasks=5)
        result2 = manager.sync()
        assert abs(result2["moralCompassScore"] - 0.51) < 0.0001
        
        # Stage 3
        manager.set_metric("accuracy", 0.90)
        manager.set_metric("fairness", 0.95)
        manager.set_progress(tasks_completed=5, total_tasks=5)
        result3 = manager.sync()
        assert abs(result3["moralCompassScore"] - 0.90) < 0.0001
    
    @pytest.mark.integration
    def test_challenge_manager_with_questions(self, client: MoralcompassApiClient,
                                             created_table: str, test_username: str):
        """Test ChallengeManager with both tasks and questions"""
        manager = ChallengeManager(created_table, test_username, api_client=client)
        
        manager.set_metric("accuracy", 0.82, primary=True)
        manager.set_progress(
            tasks_completed=5,
            total_tasks=5,
            questions_correct=8,
            total_questions=10
        )
        
        # Score: 0.82 * ((5 + 8) / (5 + 10)) = 0.82 * 0.8667
        expected_score = 0.82 * (13 / 15)
        assert abs(manager.get_local_score() - expected_score) < 0.0001
        
        result = manager.sync()
        assert abs(result["moralCompassScore"] - expected_score) < 0.0001
    
    @pytest.mark.integration
    def test_challenge_manager_repr(self, created_table: str, test_username: str):
        """Test ChallengeManager string representation"""
        manager = ChallengeManager(created_table, test_username)
        manager.set_metric("accuracy", 0.90, primary=True)
        manager.set_progress(tasks_completed=5, total_tasks=10)
        
        repr_str = repr(manager)
        assert created_table in repr_str
        assert test_username in repr_str
        assert "accuracy" in repr_str


if __name__ == "__main__":
    import sys
    
    print("Running integration tests for Moral Compass dynamic metrics...")
    print("Note: This requires a deployed API instance.")
    print("")
    
    exit_code = pytest.main([__file__, "-v", "-m", "integration"])
    sys.exit(exit_code)

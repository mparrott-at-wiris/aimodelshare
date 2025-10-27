#!/usr/bin/env python3
"""
Unit tests for Moral Compass dynamic metric support (no API required).

Tests local logic without requiring a deployed API:
- ChallengeManager score calculations
- Metric validation logic
- Primary metric selection

Run with: pytest tests/test_moral_compass_unit.py -v
"""

import pytest
from decimal import Decimal


class MockApiClient:
    """Mock API client for testing"""
    def __init__(self):
        self.last_call = None
    
    def update_moral_compass(self, **kwargs):
        self.last_call = kwargs
        # Simulate server response
        metrics = kwargs.get('metrics', {})
        primary_metric = kwargs.get('primary_metric')
        
        # Determine primary metric (server logic)
        if primary_metric is None:
            if 'accuracy' in metrics:
                primary_metric = 'accuracy'
            else:
                primary_metric = sorted(metrics.keys())[0]
        
        primary_value = metrics[primary_metric]
        
        # Calculate score
        tc = kwargs.get('tasks_completed', 0)
        tt = kwargs.get('total_tasks', 0)
        qc = kwargs.get('questions_correct', 0)
        qt = kwargs.get('total_questions', 0)
        
        denom = tt + qt
        if denom == 0:
            score = 0.0
        else:
            score = primary_value * ((tc + qc) / denom)
        
        return {
            'username': kwargs.get('username'),
            'metrics': metrics,
            'primaryMetric': primary_metric,
            'moralCompassScore': score,
            'tasksCompleted': tc,
            'totalTasks': tt,
            'questionsCorrect': qc,
            'totalQuestions': qt,
            'message': 'Moral compass data updated successfully',
            'createdNew': False
        }


class TestChallengeManagerUnit:
    """Unit tests for ChallengeManager class"""
    
    def test_basic_metric_setting(self):
        """Test setting a single metric"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("accuracy", 0.85, primary=True)
        
        assert manager.metrics["accuracy"] == 0.85
        assert manager.primary_metric == "accuracy"
    
    def test_multiple_metrics(self):
        """Test setting multiple metrics"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("accuracy", 0.85)
        manager.set_metric("fairness", 0.92, primary=True)
        manager.set_metric("robustness", 0.88)
        
        assert len(manager.metrics) == 3
        assert manager.primary_metric == "fairness"
    
    def test_local_score_single_metric(self):
        """Test local score calculation with single metric"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("accuracy", 0.85, primary=True)
        manager.set_progress(tasks_completed=5, total_tasks=10)
        
        score = manager.get_local_score()
        expected = 0.85 * (5/10)
        
        assert abs(score - expected) < 0.0001
    
    def test_local_score_with_questions(self):
        """Test local score calculation with tasks and questions"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("fairness", 0.92, primary=True)
        manager.set_progress(
            tasks_completed=3,
            total_tasks=5,
            questions_correct=8,
            total_questions=10
        )
        
        score = manager.get_local_score()
        expected = 0.92 * ((3 + 8) / (5 + 10))
        
        assert abs(score - expected) < 0.0001
    
    def test_local_score_defaults_to_accuracy(self):
        """Test that score defaults to accuracy metric when no primary specified"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("robustness", 0.80)
        manager.set_metric("accuracy", 0.88)
        manager.set_progress(tasks_completed=2, total_tasks=4)
        
        score = manager.get_local_score()
        expected = 0.88 * (2/4)  # Should use accuracy
        
        assert abs(score - expected) < 0.0001
    
    def test_local_score_defaults_to_first_sorted(self):
        """Test that score defaults to first sorted metric when no accuracy"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("robustness", 0.80)
        manager.set_metric("fairness", 0.90)
        manager.set_progress(tasks_completed=1, total_tasks=2)
        
        score = manager.get_local_score()
        expected = 0.90 * (1/2)  # Should use fairness (first alphabetically)
        
        assert abs(score - expected) < 0.0001
    
    def test_local_score_zero_denominator(self):
        """Test that zero denominator returns 0.0"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("accuracy", 0.95)
        manager.set_progress(tasks_completed=0, total_tasks=0)
        
        score = manager.get_local_score()
        
        assert score == 0.0
    
    def test_sync_with_mock_client(self):
        """Test syncing with mock API client"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        mock_client = MockApiClient()
        manager = ChallengeManager("test-table", "test-user", api_client=mock_client)
        
        manager.set_metric("accuracy", 0.85, primary=True)
        manager.set_progress(tasks_completed=5, total_tasks=10)
        
        result = manager.sync()
        
        assert result['username'] == 'test-user'
        expected_score = 0.85 * (5/10)
        assert result['moralCompassScore'] == expected_score
        assert result['primaryMetric'] == 'accuracy'
        
        # Verify the client was called with correct params
        assert mock_client.last_call['table_id'] == 'test-table'
        assert mock_client.last_call['username'] == 'test-user'
        assert mock_client.last_call['metrics'] == {'accuracy': 0.85}
    
    def test_sync_without_metrics_raises(self):
        """Test that syncing without metrics raises ValueError"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        
        with pytest.raises(ValueError, match="No metrics set"):
            manager.sync()
    
    def test_repr(self):
        """Test string representation"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("accuracy", 0.90, primary=True)
        manager.set_progress(tasks_completed=5, total_tasks=10)
        
        repr_str = repr(manager)
        
        assert "test-table" in repr_str
        assert "test-user" in repr_str
        assert "accuracy" in repr_str


class TestScoreCalculation:
    """Unit tests for score calculation logic"""
    
    def test_score_formula_basic(self):
        """Test basic score formula"""
        primary_value = 0.85
        tasks_completed = 5
        total_tasks = 10
        questions_correct = 0
        total_questions = 0
        
        denom = total_tasks + total_questions
        if denom == 0:
            score = 0.0
        else:
            score = primary_value * ((tasks_completed + questions_correct) / denom)
        
        expected = 0.85 * (5/10)
        assert abs(score - expected) < 0.0001
    
    def test_score_formula_with_questions(self):
        """Test score formula with questions"""
        primary_value = 0.92
        tasks_completed = 3
        total_tasks = 5
        questions_correct = 8
        total_questions = 10
        
        score = primary_value * ((tasks_completed + questions_correct) / (total_tasks + total_questions))
        
        expected = 0.92 * (11/15)
        assert abs(score - expected) < 0.0001
    
    def test_decimal_precision(self):
        """Test that Decimal calculations match expected precision"""
        primary_value = Decimal('0.82')
        tasks_completed = 5
        total_tasks = 5
        questions_correct = 8
        total_questions = 10
        
        progress_ratio = Decimal(tasks_completed + questions_correct) / Decimal(total_tasks + total_questions)
        score = primary_value * progress_ratio
        
        expected = Decimal('0.82') * Decimal('13') / Decimal('15')
        
        assert abs(float(score) - float(expected)) < 0.0001


class TestPrimaryMetricSelection:
    """Unit tests for primary metric selection logic"""
    
    def test_explicit_primary_metric(self):
        """Test explicitly set primary metric"""
        from aimodelshare.moral_compass.challenge import ChallengeManager
        
        manager = ChallengeManager("test-table", "test-user", api_client=MockApiClient())
        manager.set_metric("accuracy", 0.85)
        manager.set_metric("fairness", 0.92, primary=True)
        
        assert manager.primary_metric == "fairness"
    
    def test_default_to_accuracy_when_present(self):
        """Test that accuracy is default when present"""
        metrics = {"robustness": 0.80, "accuracy": 0.88, "fairness": 0.90}
        
        # Simulate server logic
        if 'accuracy' in metrics:
            primary = 'accuracy'
        else:
            primary = sorted(metrics.keys())[0]
        
        assert primary == "accuracy"
    
    def test_default_to_first_sorted_without_accuracy(self):
        """Test that first sorted key is default without accuracy"""
        metrics = {"robustness": 0.80, "fairness": 0.90}
        
        # Simulate server logic
        if 'accuracy' in metrics:
            primary = 'accuracy'
        else:
            primary = sorted(metrics.keys())[0]
        
        assert primary == "fairness"  # First alphabetically


if __name__ == "__main__":
    import sys
    
    print("Running unit tests for Moral Compass dynamic metrics...")
    print("These tests do not require a deployed API.")
    print("")
    
    exit_code = pytest.main([__file__, "-v"])
    sys.exit(exit_code)

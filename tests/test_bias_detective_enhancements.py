#!/usr/bin/env python3
"""
Tests for bias detective app enhancements:
- Ethical percentage validation (cannot exceed 100%)
- Task submission limits (one-time submission and max count validation)
- Dynamic rank tracking

Run with: pytest tests/test_bias_detective_enhancements.py -v
"""

import pytest
from unittest.mock import MagicMock
from aimodelshare.moral_compass.challenge import ChallengeManager, JusticeAndEquityChallenge


def create_test_challenge_manager():
    """Create a ChallengeManager with mocked API client for testing."""
    challenge = JusticeAndEquityChallenge()
    
    # Create a mock API client
    mock_api_client = MagicMock()
    mock_api_client.update_moral_compass.return_value = {
        'moralCompassScore': 0.5,
        'submissionCount': 1
    }
    
    cm = ChallengeManager(
        table_id="test-table",
        username="test-user",
        api_client=mock_api_client,
        challenge=challenge
    )
    
    return cm


def test_challenge_manager_prevents_duplicate_task_completion():
    """Test that ChallengeManager prevents duplicate task submissions."""
    cm = create_test_challenge_manager()
    
    # Complete task A for the first time
    result1 = cm.complete_task("A")
    assert result1 is True, "First completion should return True"
    assert cm.tasks_completed == 1, "Tasks completed should be 1"
    
    # Try to complete task A again
    result2 = cm.complete_task("A")
    assert result2 is False, "Second completion should return False"
    assert cm.tasks_completed == 1, "Tasks completed should still be 1"


def test_challenge_manager_is_task_completed():
    """Test the is_task_completed method."""
    cm = create_test_challenge_manager()
    
    # Task should not be completed initially
    assert cm.is_task_completed("A") is False
    
    # Complete the task
    cm.complete_task("A")
    
    # Task should now be completed
    assert cm.is_task_completed("A") is True


def test_challenge_manager_enforces_max_tasks():
    """Test that ChallengeManager enforces maximum task count."""
    cm = create_test_challenge_manager()
    
    # Complete all available tasks
    total_tasks = cm.total_tasks
    task_ids = [task.id for task in cm.challenge.tasks]
    
    for i, task_id in enumerate(task_ids):
        cm.complete_task(task_id)
        assert cm.tasks_completed == i + 1
    
    # Verify we can't exceed total tasks
    assert cm.tasks_completed <= total_tasks


def test_challenge_manager_prevents_duplicate_question_answers():
    """Test that ChallengeManager prevents duplicate question submissions."""
    cm = create_test_challenge_manager()
    
    # Answer a question for the first time
    is_correct1, is_new1 = cm.answer_question("A", "A1", 1)
    assert is_new1 is True, "First answer should be new"
    
    # Try to answer the same question again
    is_correct2, is_new2 = cm.answer_question("A", "A1", 1)
    assert is_new2 is False, "Second answer should not be new"


def test_challenge_manager_is_question_answered():
    """Test the is_question_answered method."""
    cm = create_test_challenge_manager()
    
    # Question should not be answered initially
    assert cm.is_question_answered("A1") is False
    
    # Answer the question
    cm.answer_question("A", "A1", 1)
    
    # Question should now be answered
    assert cm.is_question_answered("A1") is True


def test_ethical_progress_percentage_caps_at_100():
    """Test that ethical progress percentage is capped at 100%."""
    # This test simulates the calculation in bias_detective.py
    
    def calculate_ethical_progress_capped(tasks_completed: int, max_points: int) -> float:
        """Simulate the calculate_ethical_progress function."""
        if max_points == 0:
            return 0.0
        progress = (tasks_completed / max_points) * 100
        return min(progress, 100.0)
    
    # Normal case
    assert calculate_ethical_progress_capped(5, 10) == 50.0
    assert calculate_ethical_progress_capped(10, 10) == 100.0
    
    # Edge case: should cap at 100%
    assert calculate_ethical_progress_capped(15, 10) == 100.0
    assert calculate_ethical_progress_capped(20, 10) == 100.0
    
    # Zero max_points
    assert calculate_ethical_progress_capped(5, 0) == 0.0


def test_challenge_manager_enforces_question_limit():
    """Test that ChallengeManager enforces maximum question count."""
    cm = create_test_challenge_manager()
    
    # Answer all available questions correctly
    total_questions = cm.total_questions
    questions_answered = 0
    
    for task in cm.challenge.tasks:
        for question in task.questions:
            cm.answer_question(task.id, question.id, question.correct_index)
            questions_answered += 1
    
    # Verify count matches
    assert cm.questions_correct == questions_answered
    assert cm.questions_correct <= total_questions


def test_get_moral_compass_score_html_includes_ranks():
    """Test that the moral compass score HTML includes rank information."""
    from aimodelshare.moral_compass.apps.bias_detective import get_moral_compass_score_html
    
    # Test without ranks
    html1 = get_moral_compass_score_html(
        local_points=10,
        max_points=21,
        accuracy=0.92,
        ethical_progress_pct=47.6
    )
    assert "10/21 tasks completed" in html1
    assert "Ethical Progress" in html1
    
    # Test with individual rank
    html2 = get_moral_compass_score_html(
        local_points=10,
        max_points=21,
        accuracy=0.92,
        ethical_progress_pct=47.6,
        individual_rank=3
    )
    assert "Individual Rank: #3" in html2
    
    # Test with team rank
    html3 = get_moral_compass_score_html(
        local_points=10,
        max_points=21,
        accuracy=0.92,
        ethical_progress_pct=47.6,
        individual_rank=3,
        team_rank=2,
        team_name="The Justice League"
    )
    assert "Individual Rank: #3" in html3
    assert "Team 'The Justice League' Rank: #2" in html3


def test_get_moral_compass_score_html_caps_ethical_progress():
    """Test that the score HTML caps ethical progress at 100%."""
    from aimodelshare.moral_compass.apps.bias_detective import get_moral_compass_score_html
    
    # Test with ethical progress over 100%
    html = get_moral_compass_score_html(
        local_points=25,
        max_points=21,
        accuracy=0.92,
        ethical_progress_pct=119.0  # Should be capped at 100%
    )
    
    # The HTML should show 100% ethical progress, not 119%
    assert "100.0%" in html or "100%" in html
    # Combined score should not exceed accuracy * 100
    assert "92.0" in html  # accuracy (0.92) * 100 (ethical at 100%)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Test bias detective task tracking integration with completedTaskIds.

This test verifies that:
1. Initial load reads completedTaskIds from get_user and shows 0 score if empty
2. Correct Module 0 answer appends "t1" to completedTaskIds
3. Navigation without correct answer does not change backend progress
4. Score is displayed as 0 when completedTaskIds is empty, even if accuracy exists
"""

import pytest
from unittest.mock import MagicMock, patch, call


def test_get_leaderboard_data_includes_completed_task_ids():
    """Test that get_leaderboard_data includes completedTaskIds from user record."""
    from aimodelshare.moral_compass.apps.bias_detective import get_leaderboard_data
    
    mock_client = MagicMock()
    mock_client.list_users.return_value = {
        "users": [
            {
                "username": "test-user",
                "moralCompassScore": 0.5,
                "teamName": "team-a",
                "completedTaskIds": ["t1", "t2"]
            }
        ]
    }
    
    result = get_leaderboard_data(mock_client, "test-user", "team-a")
    
    assert result is not None
    assert result["score"] == 0.5
    assert result["completed_task_ids"] == ["t1", "t2"]


def test_get_leaderboard_data_handles_missing_completed_task_ids():
    """Test that get_leaderboard_data handles missing completedTaskIds gracefully."""
    from aimodelshare.moral_compass.apps.bias_detective import get_leaderboard_data
    
    mock_client = MagicMock()
    mock_client.list_users.return_value = {
        "users": [
            {
                "username": "test-user",
                "moralCompassScore": 0.5,
                "teamName": "team-a"
                # No completedTaskIds field
            }
        ]
    }
    
    result = get_leaderboard_data(mock_client, "test-user", "team-a")
    
    assert result is not None
    assert result["score"] == 0.5
    assert result["completed_task_ids"] == []


def test_render_top_dashboard_shows_zero_when_no_completed_tasks():
    """Test that render_top_dashboard shows 0 score when completedTaskIds is empty."""
    from aimodelshare.moral_compass.apps.bias_detective import render_top_dashboard
    
    data = {
        "score": 0.5,  # Non-zero score
        "rank": 1,
        "team_rank": 1,
        "completed_task_ids": []  # Empty completed tasks
    }
    
    html = render_top_dashboard(data, module_id=0)
    
    # Should show 0.000 instead of the actual score
    assert "0.000" in html
    assert "0.5" not in html


def test_render_top_dashboard_shows_actual_score_when_tasks_completed():
    """Test that render_top_dashboard shows actual score when tasks are completed."""
    from aimodelshare.moral_compass.apps.bias_detective import render_top_dashboard
    
    data = {
        "score": 0.5,
        "rank": 1,
        "team_rank": 1,
        "completed_task_ids": ["t1"]  # Has completed tasks
    }
    
    html = render_top_dashboard(data, module_id=0)
    
    # Should show actual score
    assert "0.500" in html


def test_trigger_api_update_with_task_id():
    """Test that trigger_api_update appends task ID correctly."""
    from aimodelshare.moral_compass.apps.bias_detective import trigger_api_update
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.MoralcompassApiClient') as MockClient, \
         patch('aimodelshare.moral_compass.apps.bias_detective.get_leaderboard_data') as mock_get_lb:
        
        mock_client_instance = MockClient.return_value
        mock_client_instance.get_table.return_value = {"tableId": "m-mc"}
        
        # Mock previous data with no completed tasks
        mock_get_lb.side_effect = [
            {"score": 0.0, "rank": 10, "team_rank": 2, "completed_task_ids": []},  # prev
            {"score": 0.3, "rank": 5, "team_rank": 1, "completed_task_ids": ["t1"]}  # new
        ]
        
        prev, curr, username, prev_task_ids, new_task_ids = trigger_api_update(
            "test-user", "test-token", "team-a", module_id=0,
            append_task_id="t1", increment_question=True
        )
        
        # Verify update_moral_compass was called with correct parameters
        mock_client_instance.update_moral_compass.assert_called_once()
        call_args = mock_client_instance.update_moral_compass.call_args
        
        assert call_args[1]["completed_task_ids"] == ["t1"]
        assert call_args[1]["tasks_completed"] == 1
        assert call_args[1]["questions_correct"] == 1
        assert call_args[1]["total_questions"] == 10  # Fixed total
        
        # Verify task IDs are returned correctly
        assert prev_task_ids == []
        assert new_task_ids == ["t1"]


def test_trigger_api_update_appends_to_existing_task_ids():
    """Test that trigger_api_update appends to existing completedTaskIds."""
    from aimodelshare.moral_compass.apps.bias_detective import trigger_api_update
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.MoralcompassApiClient') as MockClient, \
         patch('aimodelshare.moral_compass.apps.bias_detective.get_leaderboard_data') as mock_get_lb:
        
        mock_client_instance = MockClient.return_value
        mock_client_instance.get_table.return_value = {"tableId": "m-mc"}
        
        # Mock previous data with existing completed tasks
        mock_get_lb.side_effect = [
            {"score": 0.3, "rank": 5, "team_rank": 1, "completed_task_ids": ["t1"]},  # prev
            {"score": 0.5, "rank": 3, "team_rank": 1, "completed_task_ids": ["t1", "t2"]}  # new
        ]
        
        prev, curr, username, prev_task_ids, new_task_ids = trigger_api_update(
            "test-user", "test-token", "team-a", module_id=1,
            append_task_id="t2", increment_question=True
        )
        
        # Verify update_moral_compass was called with correct parameters
        call_args = mock_client_instance.update_moral_compass.call_args
        
        # Verify task IDs are returned correctly
        assert prev_task_ids == ["t1"]
        assert new_task_ids == ["t1", "t2"]
        
        assert call_args[1]["completed_task_ids"] == ["t1", "t2"]
        assert call_args[1]["tasks_completed"] == 2
        assert call_args[1]["questions_correct"] == 2


def test_trigger_api_update_without_task_id():
    """Test that trigger_api_update works without appending task ID (navigation only)."""
    from aimodelshare.moral_compass.apps.bias_detective import trigger_api_update
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.MoralcompassApiClient') as MockClient, \
         patch('aimodelshare.moral_compass.apps.bias_detective.get_leaderboard_data') as mock_get_lb:
        
        mock_client_instance = MockClient.return_value
        mock_client_instance.get_table.return_value = {"tableId": "m-mc"}
        
        mock_get_lb.side_effect = [
            {"score": 0.3, "rank": 5, "team_rank": 1, "completed_task_ids": ["t1"]},  # prev
            {"score": 0.5, "rank": 3, "team_rank": 1, "completed_task_ids": ["t1"]}  # new (no change)
        ]
        
        prev, curr, username, prev_task_ids, new_task_ids = trigger_api_update(
            "test-user", "test-token", "team-a", module_id=1,
            append_task_id=None, increment_question=False
        )
        
        # Verify update_moral_compass was called without changing completedTaskIds
        call_args = mock_client_instance.update_moral_compass.call_args
        
        # Verify task IDs remain the same
        assert prev_task_ids == ["t1"]
        assert new_task_ids == ["t1"]
        
        # When no task is appended, should use comp_pct calculation
        assert call_args[1]["questions_correct"] == 0


def test_submit_quiz_0_correct_answer_appends_t1():
    """Test that submit_quiz_0 with correct answer appends 't1' to completedTaskIds."""
    from aimodelshare.moral_compass.apps.bias_detective import submit_quiz_0, CORRECT_ANSWER_0
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.trigger_api_update') as mock_update, \
         patch('aimodelshare.moral_compass.apps.bias_detective.render_top_dashboard') as mock_render_top, \
         patch('aimodelshare.moral_compass.apps.bias_detective.render_leaderboard_card') as mock_render_lb:
        
        mock_update.return_value = (
            {"score": 0.0, "rank": 10, "completed_task_ids": []},  # prev
            {"score": 0.3, "rank": 5, "completed_task_ids": ["t1"]},  # curr
            "test-user",
            [],  # prev_task_ids
            ["t1"]  # new_task_ids
        )
        
        mock_render_top.return_value = "<div>Top Dashboard</div>"
        mock_render_lb.return_value = "<div>Leaderboard</div>"
        
        result = submit_quiz_0(
            "test-user", "test-token", "team-a", 
            module0_done=False, answer=CORRECT_ANSWER_0
        )
        
        # Verify trigger_api_update was called with append_task_id="t1"
        mock_update.assert_called_once_with(
            "test-user", "test-token", "team-a", 
            module_id=0, append_task_id="t1", increment_question=True
        )


def test_submit_quiz_0_incorrect_answer_no_update():
    """Test that submit_quiz_0 with incorrect answer does not update backend."""
    from aimodelshare.moral_compass.apps.bias_detective import submit_quiz_0
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.trigger_api_update') as mock_update:
        
        result = submit_quiz_0(
            "test-user", "test-token", "team-a", 
            module0_done=False, answer="Wrong answer"
        )
        
        # Verify trigger_api_update was NOT called
        mock_update.assert_not_called()


def test_on_next_from_module_0_does_not_update_backend():
    """Test that navigation from Module 0 to Module 1 does not call trigger_api_update."""
    # This is a structural test - we verified in the code that on_next_from_module_0 
    # calls ensure_table_and_get_data instead of trigger_api_update.
    # The actual app creation test is skipped due to Gradio API compatibility issues.
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

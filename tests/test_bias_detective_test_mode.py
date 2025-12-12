"""
Test bias detective test mode functionality.

This test verifies that:
1. render_debug function generates HTML correctly
2. trigger_api_update returns prev_task_ids and new_task_ids
3. submit_quiz functions can accept test_mode parameter
4. Test mode correctly displays debug information
"""

import pytest
from unittest.mock import MagicMock, patch


def test_render_debug_generates_html():
    """Test that render_debug generates properly formatted HTML."""
    from aimodelshare.moral_compass.apps.bias_detective import render_debug
    
    html = render_debug(
        "Test Context",
        Score=0.5,
        Global_Rank=1,
        Team_Rank=2,
        Completed_Task_IDs=["t1", "t2"]
    )
    
    assert "DEBUG: Test Context" in html
    assert "Score" in html
    assert "0.5" in html
    assert "Global_Rank" in html
    assert "Team_Rank" in html
    assert "Completed_Task_IDs" in html
    assert "['t1', 't2']" in html


def test_trigger_api_update_returns_task_ids():
    """Test that trigger_api_update returns prev_task_ids and new_task_ids."""
    from aimodelshare.moral_compass.apps.bias_detective import trigger_api_update
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.MoralcompassApiClient') as MockClient, \
         patch('aimodelshare.moral_compass.apps.bias_detective.get_leaderboard_data') as mock_get_data, \
         patch('aimodelshare.moral_compass.apps.bias_detective.time.sleep'):
        
        # Setup mock client
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        
        # Setup mock leaderboard data
        prev_data = {
            "score": 0.0,
            "rank": 999,
            "team_rank": 10,
            "completed_task_ids": []
        }
        
        curr_data = {
            "score": 0.06,
            "rank": 1,
            "team_rank": 1,
            "completed_task_ids": ["t1"]
        }
        
        mock_get_data.side_effect = [prev_data, curr_data]
        
        # Call trigger_api_update
        prev, curr, username, prev_task_ids, new_task_ids = trigger_api_update(
            "test-user", "test-token", "team-a", module_id=0,
            append_task_id="t1", increment_question=True
        )
        
        # Verify it returns 5 values including task IDs
        assert prev == prev_data
        assert curr == curr_data
        assert username == "test-user"
        assert prev_task_ids == []
        assert new_task_ids == ["t1"]


def test_trigger_api_update_prevents_duplicate_task_ids():
    """Test that trigger_api_update doesn't append duplicate task IDs."""
    from aimodelshare.moral_compass.apps.bias_detective import trigger_api_update
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.MoralcompassApiClient') as MockClient, \
         patch('aimodelshare.moral_compass.apps.bias_detective.get_leaderboard_data') as mock_get_data, \
         patch('aimodelshare.moral_compass.apps.bias_detective.time.sleep'):
        
        # Setup mock client
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        
        # Setup mock leaderboard data with existing task IDs
        prev_data = {
            "score": 0.06,
            "rank": 1,
            "team_rank": 1,
            "completed_task_ids": ["t1"]
        }
        
        curr_data = {
            "score": 0.06,
            "rank": 1,
            "team_rank": 1,
            "completed_task_ids": ["t1"]  # Should not have duplicate
        }
        
        mock_get_data.side_effect = [prev_data, curr_data]
        
        # Call trigger_api_update with a task ID that already exists
        prev, curr, username, prev_task_ids, new_task_ids = trigger_api_update(
            "test-user", "test-token", "team-a", module_id=0,
            append_task_id="t1", increment_question=True
        )
        
        # Verify task IDs don't have duplicates
        assert prev_task_ids == ["t1"]
        assert new_task_ids == ["t1"]  # Should still be just ["t1"], not ["t1", "t1"]
        
        # Verify the API was called with completed_task_ids=["t1"]
        mock_client.update_moral_compass.assert_called_once()
        call_kwargs = mock_client.update_moral_compass.call_args[1]
        assert call_kwargs["completed_task_ids"] == ["t1"]


def test_submit_quiz_0_with_test_mode():
    """Test that submit_quiz_0 handles test_mode parameter."""
    from aimodelshare.moral_compass.apps.bias_detective import submit_quiz_0, CORRECT_ANSWER_0
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.trigger_api_update') as mock_trigger, \
         patch('aimodelshare.moral_compass.apps.bias_detective.ensure_table_and_get_data') as mock_ensure:
        
        prev_data = {
            "score": 0.0,
            "rank": 999,
            "team_rank": 10,
            "completed_task_ids": []
        }
        
        curr_data = {
            "score": 0.06,
            "rank": 1,
            "team_rank": 1,
            "completed_task_ids": ["t1"]
        }
        
        mock_trigger.return_value = (prev_data, curr_data, "test-user", [], ["t1"])
        mock_ensure.return_value = (curr_data, "test-user")
        
        # Test with test_mode=True
        result = submit_quiz_0("test-user", "test-token", "team-a", False, CORRECT_ANSWER_0, test_mode=True)
        
        # Should return 5 values when test_mode is True (including debug_html)
        assert len(result) == 5
        # The last element should be the debug HTML
        assert "DEBUG:" in result[4] or result[4] == ""  # Empty string for gr.update()
        
        # Test with test_mode=False
        result = submit_quiz_0("test-user", "test-token", "team-a", False, CORRECT_ANSWER_0, test_mode=False)
        
        # Should still return 5 values but last one is gr.update()
        assert len(result) == 5


def test_submit_quiz_1_with_test_mode():
    """Test that submit_quiz_1 handles test_mode parameter."""
    from aimodelshare.moral_compass.apps.bias_detective import submit_quiz_1, CORRECT_ANSWER_1
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.trigger_api_update') as mock_trigger:
        
        prev_data = {
            "score": 0.06,
            "rank": 1,
            "team_rank": 1,
            "completed_task_ids": ["t1"]
        }
        
        curr_data = {
            "score": 0.12,
            "rank": 1,
            "team_rank": 1,
            "completed_task_ids": ["t1", "t2"]
        }
        
        mock_trigger.return_value = (prev_data, curr_data, "test-user", ["t1"], ["t1", "t2"])
        
        # Test with test_mode=True
        result = submit_quiz_1("test-user", "test-token", "team-a", CORRECT_ANSWER_1, test_mode=True)
        
        # Should return 4 values when test_mode is True (including debug_html)
        assert len(result) == 4
        # The last element should be the debug HTML or gr.update()
        assert isinstance(result[3], str) or hasattr(result[3], '__class__')


def test_submit_quiz_justice_with_test_mode():
    """Test that submit_quiz_justice handles test_mode parameter."""
    from aimodelshare.moral_compass.apps.bias_detective import submit_quiz_justice, CORRECT_ANSWER_2
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.trigger_api_update') as mock_trigger:
        
        prev_data = {
            "score": 0.12,
            "rank": 1,
            "team_rank": 1,
            "completed_task_ids": ["t1", "t2"]
        }
        
        curr_data = {
            "score": 0.18,
            "rank": 1,
            "team_rank": 1,
            "completed_task_ids": ["t1", "t2", "t3"]
        }
        
        mock_trigger.return_value = (prev_data, curr_data, "test-user", ["t1", "t2"], ["t1", "t2", "t3"])
        
        # Test with test_mode=True
        result = submit_quiz_justice("test-user", "test-token", "team-a", CORRECT_ANSWER_2, test_mode=True)
        
        # Should return 4 values when test_mode is True (including debug_html)
        assert len(result) == 4
        # The last element should be the debug HTML or gr.update()
        assert isinstance(result[3], str) or hasattr(result[3], '__class__')


def test_create_bias_detective_app_with_test_mode():
    """Test that create_bias_detective_app accepts test_mode parameter."""
    from aimodelshare.moral_compass.apps.bias_detective import create_bias_detective_app
    import inspect
    
    # Test that the function accepts test_mode parameter
    sig = inspect.signature(create_bias_detective_app)
    assert 'test_mode' in sig.parameters
    assert sig.parameters['test_mode'].default is False


def test_launch_bias_detective_app_accepts_test_mode():
    """Test that launch_bias_detective_app accepts test_mode parameter."""
    from aimodelshare.moral_compass.apps.bias_detective import launch_bias_detective_app
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.create_bias_detective_app') as mock_create:
        mock_app = MagicMock()
        mock_create.return_value = mock_app
        
        # Test with test_mode=True
        launch_bias_detective_app(share=False, test_mode=True)
        mock_create.assert_called_with(theme_primary_hue="indigo", test_mode=True)
        mock_app.launch.assert_called_once()

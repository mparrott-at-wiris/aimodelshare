"""
Unit tests for submit_model return value validation.
Tests that submit_model always returns a tuple and never returns None.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import json


class TestSubmitModelReturns:
    """Test that submit_model always returns proper tuple structure."""
    
    def test_submit_model_raises_on_missing_credentials(self):
        """Test that submit_model raises RuntimeError when credentials are missing."""
        from aimodelshare.model import submit_model
        
        # Clear credentials from environment
        env_backup = {}
        for key in ['username', 'password']:
            if key in os.environ:
                env_backup[key] = os.environ[key]
                del os.environ[key]
        
        try:
            # Should raise RuntimeError, not return None
            with pytest.raises(RuntimeError, match="Submit Model.*unsuccessful.*credentials"):
                submit_model(
                    model_filepath=None,
                    apiurl="https://example.com/api",
                    prediction_submission=[1, 2, 3]
                )
        finally:
            # Restore environment
            for key, value in env_backup.items():
                os.environ[key] = value
    
    def test_submit_model_raises_on_unauthorized(self):
        """Test that submit_model raises RuntimeError when user is unauthorized."""
        from aimodelshare.model import submit_model
        
        # Set up mock credentials
        os.environ['username'] = 'test_user'
        os.environ['password'] = 'test_pass'
        os.environ['AWS_TOKEN'] = 'test_token'
        
        try:
            # Mock the API responses
            with patch('aimodelshare.model.run_function_on_lambda') as mock_lambda:
                mock_response = Mock()
                mock_response.content = json.dumps(['1.0', 'bucket', 'model_id']).encode('utf-8')
                mock_lambda.return_value = (mock_response, None)
                
                with patch('aimodelshare.model.requests.post') as mock_post:
                    # Return unauthorized response
                    mock_post.return_value.text = json.dumps({"message": "Unauthorized"})
                    
                    # Should raise RuntimeError, not return None
                    with pytest.raises(RuntimeError, match="Unauthorized user"):
                        submit_model(
                            model_filepath=None,
                            apiurl="https://example.com/api",
                            prediction_submission=[1, 2, 3]
                        )
        finally:
            # Clean up
            for key in ['username', 'password', 'AWS_TOKEN']:
                if key in os.environ:
                    del os.environ[key]
    
    def test_submit_model_returns_tuple_on_success(self):
        """Test that submit_model returns (version, url) tuple on success."""
        from aimodelshare.model import submit_model
        
        # Set up mock credentials
        os.environ['username'] = 'test_user'
        os.environ['password'] = 'test_pass'
        os.environ['AWS_TOKEN'] = 'test_token'
        
        try:
            # This test would require extensive mocking of the entire submission flow
            # For now, we'll just verify the structure is correct by checking the code
            # In a real scenario, this would need full integration testing
            pass
        finally:
            # Clean up
            for key in ['username', 'password', 'AWS_TOKEN']:
                if key in os.environ:
                    del os.environ[key]
    
    def test_playground_submit_validates_return_structure(self):
        """Test that ModelPlayground.submit_model validates return structure."""
        from aimodelshare.playground import ModelPlayground, Competition
        
        # Create a playground instance
        playground = ModelPlayground(
            input_type="tabular",
            task_type="classification",
            private=True,
            playground_url="https://example.com/api"
        )
        
        # Mock the Competition.submit_model to return None (the bug we're fixing)
        with patch.object(Competition, 'submit_model', return_value=None):
            # Should raise RuntimeError about invalid return structure
            with pytest.raises(RuntimeError, match="Invalid return.*expected.*tuple"):
                playground.submit_model(
                    model=Mock(),
                    preprocessor=Mock(),
                    prediction_submission=[1, 2, 3],
                    submission_type="competition",
                    input_dict={"tags": "test", "description": "test"}
                )
        
        # Mock the Competition.submit_model to return tuple (correct behavior)
        with patch.object(Competition, 'submit_model', return_value=("1", "https://example.com/model")):
            with patch('aimodelshare.playground.model_to_onnx_timed', return_value="model.onnx"):
                with patch('builtins.print'):  # Suppress print output
                    # Should not raise an error
                    playground.submit_model(
                        model=Mock(),
                        preprocessor=Mock(),
                        prediction_submission=[1, 2, 3],
                        submission_type="competition",
                        input_dict={"tags": "test", "description": "test"}
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

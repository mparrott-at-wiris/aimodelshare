"""
Unit tests for ModelPlayground initialization.
These tests help isolate playground initialization issues.
"""
import pytest
from unittest.mock import patch, MagicMock
from aimodelshare.playground import ModelPlayground


class TestModelPlaygroundInitialization:
    """Test ModelPlayground class initialization."""
    
    def test_init_with_all_params(self):
        """Test initialization with all required parameters."""
        playground = ModelPlayground(
            input_type="tabular",
            task_type="classification",
            private=True
        )
        
        assert playground.model_type == "tabular"
        assert playground.categorical is True
        assert playground.private is True
        assert playground.playground_url is None
        assert playground.email_list == []
    
    def test_init_classification_task(self):
        """Test that classification task sets categorical correctly."""
        playground = ModelPlayground(
            input_type="image",
            task_type="classification",
            private=False
        )
        
        assert playground.categorical is True
    
    def test_init_regression_task(self):
        """Test that regression task sets categorical correctly."""
        playground = ModelPlayground(
            input_type="tabular",
            task_type="regression",
            private=False
        )
        
        assert playground.categorical is False
    
    def test_init_with_invalid_task_type(self):
        """Test that invalid task_type raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            ModelPlayground(
                input_type="tabular",
                task_type="invalid_task",
                private=False
            )
        
        assert "classification" in str(excinfo.value) or "regression" in str(excinfo.value)
    
    def test_init_missing_required_params(self):
        """Test that missing required parameters raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            ModelPlayground(input_type="tabular")
        
        assert "playground_url" in str(excinfo.value) or "input_type" in str(excinfo.value)
    
    def test_init_with_playground_url(self):
        """Test initialization with playground_url only."""
        test_url = "https://test-api.modelshare.ai/playground/test"
        
        with patch('aimodelshare.playground.requests.post') as mock_post:
            # Mock the response to return task_type
            mock_response = MagicMock()
            mock_response.text = '{"task_type": "classification"}'
            mock_post.return_value = mock_response
            
            playground = ModelPlayground(
                playground_url=test_url,
                private=True
            )
            
            assert playground.playground_url == test_url
            assert playground.categorical is True
    
    def test_init_with_email_list(self):
        """Test initialization with email list for private playground."""
        emails = ["test1@example.com", "test2@example.com"]
        
        playground = ModelPlayground(
            input_type="tabular",
            task_type="classification",
            private=True,
            email_list=emails
        )
        
        assert playground.email_list == emails
    
    def test_init_different_input_types(self):
        """Test initialization with different input types."""
        input_types = ["tabular", "image", "text", "video", "audio", "timeseries"]
        
        for input_type in input_types:
            playground = ModelPlayground(
                input_type=input_type,
                task_type="classification",
                private=False
            )
            
            assert playground.model_type == input_type
    
    def test_class_string_representation(self):
        """Test that the class string is generated correctly."""
        playground = ModelPlayground(
            input_type="tabular",
            task_type="classification",
            private=True
        )
        
        assert hasattr(playground, 'class_string')
        assert 'ModelPlayground' in playground.class_string
        assert 'tabular' in playground.class_string

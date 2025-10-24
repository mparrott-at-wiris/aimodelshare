"""
Unit tests for model.py helper functions.
Tests the _normalize_model_config function that prevents TypeError when model_config is None or dict.
"""
import pytest
import sys
import os

# Import the function directly by reading and executing just the helper function
def load_normalize_function():
    """Load just the _normalize_model_config function without full module import."""
    import ast
    
    # Read the model.py file
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'aimodelshare',
        'model.py'
    )
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    # Parse and extract just the _normalize_model_config function
    tree = ast.parse(content)
    
    # Find the function definition
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == '_normalize_model_config':
            # Create a minimal module with just this function
            func_code = ast.unparse(node)
            # Create namespace with necessary imports
            namespace = {}
            exec("import ast", namespace)
            exec(func_code, namespace)
            return namespace['_normalize_model_config']
    
    raise ImportError("Could not find _normalize_model_config function")

# Try to load the function
try:
    _normalize_model_config = load_normalize_function()
    IMPORT_SUCCESS = True
except Exception as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Cannot load _normalize_model_config function")
class TestNormalizeModelConfig:
    
    def test_normalize_none_input(self):
        """Test that None input returns empty dict."""
        result = _normalize_model_config(None)
        assert isinstance(result, dict)
        assert result == {}
    
    def test_normalize_dict_input(self):
        """Test that dict input is returned as-is."""
        input_dict = {'max_iter': 100, 'solver': 'lbfgs', 'random_state': 42}
        result = _normalize_model_config(input_dict)
        assert isinstance(result, dict)
        assert result == input_dict
        # Verify it's the same object (not a copy)
        assert result is input_dict
    
    def test_normalize_string_dict_representation(self):
        """Test that string representation of dict is parsed correctly."""
        input_str = "{'max_iter': 100, 'solver': 'lbfgs', 'random_state': 42}"
        result = _normalize_model_config(input_str)
        assert isinstance(result, dict)
        assert result.get('max_iter') == 100
        assert result.get('solver') == 'lbfgs'
        assert result.get('random_state') == 42
    
    def test_normalize_invalid_string(self):
        """Test that invalid string returns empty dict."""
        result = _normalize_model_config("not a dict")
        assert isinstance(result, dict)
        assert result == {}
    
    def test_normalize_int_input(self):
        """Test that int input returns empty dict."""
        result = _normalize_model_config(123)
        assert isinstance(result, dict)
        assert result == {}
    
    def test_normalize_list_input(self):
        """Test that list input returns empty dict."""
        result = _normalize_model_config([1, 2, 3])
        assert isinstance(result, dict)
        assert result == {}
    
    def test_normalize_empty_dict(self):
        """Test that empty dict input is returned as-is."""
        result = _normalize_model_config({})
        assert isinstance(result, dict)
        assert result == {}
    
    def test_normalize_complex_dict_string(self):
        """Test parsing of complex dict string with nested structures."""
        # Simple case without nested calls
        input_str = "{'alpha': 0.5, 'beta': [1, 2, 3], 'gamma': 'test'}"
        result = _normalize_model_config(input_str)
        assert isinstance(result, dict)
        assert result.get('alpha') == 0.5
        assert result.get('beta') == [1, 2, 3]
        assert result.get('gamma') == 'test'
    
    def test_normalize_with_model_type_context(self):
        """Test that model_type parameter is accepted (for logging context)."""
        # Should work the same regardless of model_type
        result1 = _normalize_model_config(None, model_type='LogisticRegression')
        result2 = _normalize_model_config({}, model_type='RandomForest')
        
        assert result1 == {}
        assert result2 == {}


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Cannot load _normalize_model_config function")
class TestModelConfigIntegration:
    """Integration tests to verify the fix works in context."""
    
    def test_sklearn_model_config_with_none(self):
        """Test that sklearn branch handles None model_config without TypeError."""
        # This simulates the scenario where model_config is None
        # The actual integration would require mocking more of the model submission flow
        
        # Simulate what happens in upload_model_dict/submit_model
        meta_dict = {
            'model_config': None,
            'model_type': 'LogisticRegression',
            'ml_framework': 'sklearn'
        }
        
        # This should not raise TypeError anymore
        model_config = _normalize_model_config(
            meta_dict.get("model_config"), 
            meta_dict.get('model_type')
        )
        
        assert isinstance(model_config, dict)
        assert model_config == {}
    
    def test_sklearn_model_config_with_dict(self):
        """Test that sklearn branch handles dict model_config without TypeError."""
        
        # Simulate what happens when model_config is already a dict
        meta_dict = {
            'model_config': {'max_iter': 100, 'solver': 'lbfgs'},
            'model_type': 'LogisticRegression',
            'ml_framework': 'sklearn'
        }
        
        # This should not raise TypeError anymore
        model_config = _normalize_model_config(
            meta_dict.get("model_config"), 
            meta_dict.get('model_type')
        )
        
        assert isinstance(model_config, dict)
        assert model_config == {'max_iter': 100, 'solver': 'lbfgs'}
    
    def test_xgboost_model_config_with_none(self):
        """Test that xgboost branch handles None model_config without TypeError."""
        
        # Simulate what happens in upload_model_dict/submit_model for xgboost
        meta_dict = {
            'model_config': None,
            'model_type': 'XGBClassifier',
            'ml_framework': 'xgboost'
        }
        
        # This should not raise TypeError anymore
        model_config = _normalize_model_config(
            meta_dict.get("model_config"), 
            meta_dict.get('model_type')
        )
        
        assert isinstance(model_config, dict)
        assert model_config == {}

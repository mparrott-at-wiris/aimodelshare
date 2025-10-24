"""
Unit tests for model.py helper functions.
Tests the _normalize_model_config, _normalize_eval_payload, and _subset_numeric functions
that prevent TypeError when handling eval metrics and model configs.
"""
import pytest
import sys
import os

# Import the functions directly by reading and executing just the helper functions
def load_helper_functions():
    """Load helper functions without full module import."""
    import ast
    
    # Read the model.py file
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'aimodelshare',
        'model.py'
    )
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    # Parse and extract helper functions
    tree = ast.parse(content)
    
    # Find the function definitions
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in [
            '_normalize_model_config',
            '_normalize_eval_payload', 
            '_subset_numeric'
        ]:
            # Create a minimal module with just this function
            func_code = ast.unparse(node)
            # Create namespace with necessary imports
            namespace = {}
            exec("import ast", namespace)
            exec(func_code, namespace)
            functions[node.name] = namespace[node.name]
    
    return functions

# Try to load the functions
try:
    helper_functions = load_helper_functions()
    _normalize_model_config = helper_functions.get('_normalize_model_config')
    _normalize_eval_payload = helper_functions.get('_normalize_eval_payload')
    _subset_numeric = helper_functions.get('_subset_numeric')
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


@pytest.mark.skipif(not IMPORT_SUCCESS or _normalize_eval_payload is None, 
                    reason="Cannot load _normalize_eval_payload function")
class TestNormalizeEvalPayload:
    """Tests for _normalize_eval_payload helper function."""
    
    def test_normalize_list_with_two_dicts(self):
        """Test the expected format: {"eval": [public_dict, private_dict]}."""
        raw_eval = {
            "eval": [
                {"accuracy": 0.95, "f1_score": 0.93},
                {"accuracy": 0.92, "f1_score": 0.90}
            ],
            "get": {},
            "put": {}
        }
        public, private = _normalize_eval_payload(raw_eval)
        
        assert isinstance(public, dict)
        assert isinstance(private, dict)
        assert public == {"accuracy": 0.95, "f1_score": 0.93}
        assert private == {"accuracy": 0.92, "f1_score": 0.90}
    
    def test_normalize_list_with_one_dict(self):
        """Test when eval list has only one dict."""
        raw_eval = {
            "eval": [{"accuracy": 0.95, "f1_score": 0.93}],
            "get": {},
            "put": {}
        }
        public, private = _normalize_eval_payload(raw_eval)
        
        assert isinstance(public, dict)
        assert isinstance(private, dict)
        assert public == {"accuracy": 0.95, "f1_score": 0.93}
        assert private == {}
    
    def test_normalize_single_dict(self):
        """Test when eval is a single dict (not a list)."""
        raw_eval = {
            "eval": {"accuracy": 0.95, "f1_score": 0.93},
            "get": {},
            "put": {}
        }
        public, private = _normalize_eval_payload(raw_eval)
        
        assert isinstance(public, dict)
        assert isinstance(private, dict)
        assert public == {"accuracy": 0.95, "f1_score": 0.93}
        assert private == {}
    
    def test_normalize_none_eval(self):
        """Test when eval field is None."""
        raw_eval = {
            "eval": None,
            "get": {},
            "put": {}
        }
        public, private = _normalize_eval_payload(raw_eval)
        
        assert isinstance(public, dict)
        assert isinstance(private, dict)
        assert public == {}
        assert private == {}
    
    def test_normalize_missing_eval(self):
        """Test when eval field is missing."""
        raw_eval = {
            "get": {},
            "put": {}
        }
        public, private = _normalize_eval_payload(raw_eval)
        
        assert isinstance(public, dict)
        assert isinstance(private, dict)
        assert public == {}
        assert private == {}
    
    def test_normalize_invalid_dict_type(self):
        """Test when raw_eval is not a dict."""
        raw_eval = ["invalid", "response"]
        public, private = _normalize_eval_payload(raw_eval)
        
        assert isinstance(public, dict)
        assert isinstance(private, dict)
        assert public == {}
        assert private == {}
    
    def test_normalize_unexpected_eval_type(self):
        """Test when eval field has unexpected type."""
        raw_eval = {
            "eval": "unexpected string",
            "get": {},
            "put": {}
        }
        public, private = _normalize_eval_payload(raw_eval)
        
        assert isinstance(public, dict)
        assert isinstance(private, dict)
        assert public == {}
        assert private == {}
    
    def test_normalize_list_with_non_dict_elements(self):
        """Test when eval list contains non-dict elements."""
        raw_eval = {
            "eval": ["string1", "string2"],
            "get": {},
            "put": {}
        }
        public, private = _normalize_eval_payload(raw_eval)
        
        assert isinstance(public, dict)
        assert isinstance(private, dict)
        assert public == {}
        assert private == {}


@pytest.mark.skipif(not IMPORT_SUCCESS or _subset_numeric is None,
                    reason="Cannot load _subset_numeric function")
class TestSubsetNumeric:
    """Tests for _subset_numeric helper function."""
    
    def test_subset_all_numeric_values(self):
        """Test extracting numeric values from complete metrics dict."""
        metrics = {
            "accuracy": 0.95,
            "f1_score": 0.93,
            "precision": 0.94,
            "recall": 0.92,
            "mse": 0.05
        }
        keys = ["accuracy", "f1_score", "precision", "recall"]
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {
            "accuracy": 0.95,
            "f1_score": 0.93,
            "precision": 0.94,
            "recall": 0.92
        }
    
    def test_subset_missing_keys(self):
        """Test when some keys are missing from metrics dict."""
        metrics = {
            "accuracy": 0.95,
            "f1_score": 0.93
        }
        keys = ["accuracy", "f1_score", "precision", "recall", "mse"]
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {
            "accuracy": 0.95,
            "f1_score": 0.93
        }
    
    def test_subset_with_none_values(self):
        """Test that None values are excluded."""
        metrics = {
            "accuracy": 0.95,
            "f1_score": None,
            "precision": 0.94,
            "recall": None
        }
        keys = ["accuracy", "f1_score", "precision", "recall"]
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {
            "accuracy": 0.95,
            "precision": 0.94
        }
    
    def test_subset_with_non_numeric_values(self):
        """Test that non-numeric values are excluded."""
        metrics = {
            "accuracy": 0.95,
            "f1_score": "not a number",
            "precision": [1, 2, 3],
            "recall": 0.92
        }
        keys = ["accuracy", "f1_score", "precision", "recall"]
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {
            "accuracy": 0.95,
            "recall": 0.92
        }
    
    def test_subset_with_int_values(self):
        """Test that integer values are included (not just floats)."""
        metrics = {
            "accuracy": 95,  # int
            "f1_score": 0.93,  # float
            "count": 100  # int
        }
        keys = ["accuracy", "f1_score", "count"]
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {
            "accuracy": 95,
            "f1_score": 0.93,
            "count": 100
        }
    
    def test_subset_empty_metrics(self):
        """Test with empty metrics dict."""
        metrics = {}
        keys = ["accuracy", "f1_score"]
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {}
    
    def test_subset_empty_keys(self):
        """Test with empty keys list."""
        metrics = {
            "accuracy": 0.95,
            "f1_score": 0.93
        }
        keys = []
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {}
    
    def test_subset_invalid_metrics_type(self):
        """Test when metrics is not a dict."""
        metrics = ["list", "not", "dict"]
        keys = ["accuracy", "f1_score"]
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {}
    
    def test_subset_zero_values(self):
        """Test that zero values are included (they are numeric)."""
        metrics = {
            "accuracy": 0.0,
            "f1_score": 0,
            "precision": 0.94
        }
        keys = ["accuracy", "f1_score", "precision"]
        
        result = _subset_numeric(metrics, keys)
        
        assert isinstance(result, dict)
        assert result == {
            "accuracy": 0.0,
            "f1_score": 0,
            "precision": 0.94
        }


@pytest.mark.skipif(not IMPORT_SUCCESS or _normalize_eval_payload is None,
                    reason="Cannot load helper functions")
class TestEvalMetricsIntegration:
    """Integration tests simulating the actual submit_model flow."""
    
    def test_list_response_integration(self):
        """Simulate API returning {"eval": [public_dict, private_dict]}."""
        # This is the problematic case that caused TypeError
        api_response = {
            "eval": [
                {"accuracy": 0.95, "f1_score": 0.93},
                {"accuracy": 0.92, "f1_score": 0.90}
            ],
            "get": {"presigned_url": "..."},
            "put": {"presigned_url": "..."},
            "idempotentmodel_version": "v1"
        }
        
        # Extract presigned URLs
        s3_dict = {k: v for k, v in api_response.items() if k != 'eval'}
        assert "get" in s3_dict
        assert "put" in s3_dict
        
        # Normalize eval metrics
        eval_metrics, eval_metrics_private = _normalize_eval_payload(api_response)
        
        # Verify both are dicts (no TypeError)
        assert isinstance(eval_metrics, dict)
        assert isinstance(eval_metrics_private, dict)
        
        # Extract subset safely
        keys = ["accuracy", "f1_score", "precision", "recall"]
        subset = _subset_numeric(eval_metrics, keys)
        subset_private = _subset_numeric(eval_metrics_private, keys)
        
        # Verify results
        assert subset == {"accuracy": 0.95, "f1_score": 0.93}
        assert subset_private == {"accuracy": 0.92, "f1_score": 0.90}
    
    def test_dict_response_integration(self):
        """Simulate API returning {"eval": dict} (single dict, not list)."""
        api_response = {
            "eval": {"accuracy": 0.95, "f1_score": 0.93},
            "get": {"presigned_url": "..."},
            "put": {"presigned_url": "..."},
            "idempotentmodel_version": "v1"
        }
        
        # Extract presigned URLs
        s3_dict = {k: v for k, v in api_response.items() if k != 'eval'}
        
        # Normalize eval metrics
        eval_metrics, eval_metrics_private = _normalize_eval_payload(api_response)
        
        # Verify both are dicts
        assert isinstance(eval_metrics, dict)
        assert isinstance(eval_metrics_private, dict)
        
        # Extract subset safely
        keys = ["accuracy", "f1_score", "precision", "recall"]
        subset = _subset_numeric(eval_metrics, keys)
        subset_private = _subset_numeric(eval_metrics_private, keys)
        
        # Verify results
        assert subset == {"accuracy": 0.95, "f1_score": 0.93}
        assert subset_private == {}  # No private metrics
    
    def test_empty_response_integration(self):
        """Simulate API returning no eval metrics."""
        api_response = {
            "eval": None,
            "get": {"presigned_url": "..."},
            "put": {"presigned_url": "..."},
            "idempotentmodel_version": "v1"
        }
        
        # Normalize eval metrics
        eval_metrics, eval_metrics_private = _normalize_eval_payload(api_response)
        
        # Verify both are empty dicts (no crash)
        assert eval_metrics == {}
        assert eval_metrics_private == {}
        
        # Extract subset safely (should return empty)
        keys = ["accuracy", "f1_score", "precision", "recall"]
        subset = _subset_numeric(eval_metrics, keys)
        subset_private = _subset_numeric(eval_metrics_private, keys)
        
        # Verify empty results
        assert subset == {}
        assert subset_private == {}

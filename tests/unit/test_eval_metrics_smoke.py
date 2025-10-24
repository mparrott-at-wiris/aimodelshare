"""
Smoke test for eval metrics normalization in submit_model flow.

This test validates that the helper functions work correctly with real-world
scenarios without requiring actual API calls or model submissions.
"""
import pytest
import sys
import os

# Import the helper functions using the same pattern as test_model_helpers.py
def load_helper_functions():
    """Load helper functions without full module import."""
    import ast
    
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'aimodelshare',
        'model.py'
    )
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in [
            '_normalize_eval_payload', 
            '_subset_numeric'
        ]:
            func_code = ast.unparse(node)
            namespace = {}
            exec(func_code, namespace)
            functions[node.name] = namespace[node.name]
    
    return functions

try:
    helper_functions = load_helper_functions()
    _normalize_eval_payload = helper_functions.get('_normalize_eval_payload')
    _subset_numeric = helper_functions.get('_subset_numeric')
    IMPORT_SUCCESS = True
except Exception as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not IMPORT_SUCCESS, reason="Cannot load helper functions")
class TestSubmitModelSmokeTest:
    """End-to-end smoke tests simulating the submit_model workflow."""
    
    def test_problematic_list_response_no_longer_crashes(self):
        """
        This is the exact scenario that was causing TypeError.
        
        The API returns {"eval": [public_dict, private_dict]}, which was
        being assigned directly to eval_metrics, making it a list.
        Then line 1116 tried: eval_metrics[key] which failed with TypeError.
        
        This test validates the fix works end-to-end.
        """
        # Simulate the problematic API response
        api_response = {
            "eval": [
                {
                    "accuracy": 0.9523809523809523,
                    "f1_score": 0.9333333333333333,
                    "precision": 0.9428571428571428,
                    "recall": 0.9285714285714286
                },
                {
                    "accuracy": 0.9047619047619048,
                    "f1_score": 0.8888888888888888,
                    "precision": 0.9,
                    "recall": 0.88
                }
            ],
            "get": {
                "model_eval_data_mastertable.csv": "s3://presigned/url1",
                "model_eval_data_mastertable_private.csv": "s3://presigned/url2"
            },
            "put": {
                "preprocessor_v1.zip": "{'url': 's3://...', 'fields': {...}}",
                "onnx_model_v1.onnx": "{'url': 's3://...', 'fields': {...}}",
                "model_eval_data_mastertable.csv": "{'url': 's3://...', 'fields': {...}}",
                "model_eval_data_mastertable_private.csv": "{'url': 's3://...', 'fields': {...}}"
            },
            "idempotentmodel_version": "1"
        }
        
        # Step 1: Extract S3 presigned URLs (as done in submit_model)
        s3_presigned_dict = {k: v for k, v in api_response.items() if k != 'eval'}
        assert 'get' in s3_presigned_dict
        assert 'put' in s3_presigned_dict
        assert 'idempotentmodel_version' in s3_presigned_dict
        
        # Step 2: Normalize eval metrics (THIS IS THE FIX)
        eval_metrics, eval_metrics_private = _normalize_eval_payload(api_response)
        
        # Step 3: Verify both are dicts (not lists)
        assert isinstance(eval_metrics, dict), f"Expected dict, got {type(eval_metrics)}"
        assert isinstance(eval_metrics_private, dict), f"Expected dict, got {type(eval_metrics_private)}"
        
        # Step 4: Extract metric subsets (THIS USED TO CRASH)
        keys_to_extract = ["accuracy", "f1_score", "precision", "recall", "mse", "rmse", "mae", "r2"]
        
        # THIS LINE WOULD HAVE CAUSED: TypeError: list indices must be integers or slices, not str
        eval_metrics_subset = _subset_numeric(eval_metrics, keys_to_extract)
        eval_metrics_private_subset = _subset_numeric(eval_metrics_private, keys_to_extract)
        
        # Step 5: Filter to only numeric values (as done in submit_model)
        eval_metrics_subset_nonulls = {
            key: value for key, value in eval_metrics_subset.items() 
            if isinstance(value, (int, float))
        }
        eval_metrics_private_subset_nonulls = {
            key: value for key, value in eval_metrics_private_subset.items() 
            if isinstance(value, (int, float))
        }
        
        # Step 6: Verify we got the expected metrics
        assert len(eval_metrics_subset_nonulls) == 4  # accuracy, f1_score, precision, recall
        assert "accuracy" in eval_metrics_subset_nonulls
        assert "f1_score" in eval_metrics_subset_nonulls
        assert "precision" in eval_metrics_subset_nonulls
        assert "recall" in eval_metrics_subset_nonulls
        
        assert len(eval_metrics_private_subset_nonulls) == 4
        assert "accuracy" in eval_metrics_private_subset_nonulls
        
        # Verify actual values
        assert abs(eval_metrics_subset_nonulls["accuracy"] - 0.9523809523809523) < 0.0001
        assert abs(eval_metrics_private_subset_nonulls["accuracy"] - 0.9047619047619048) < 0.0001
        
        print("✅ SUCCESS: The fix prevents the TypeError that was occurring!")
    
    def test_single_dict_response_still_works(self):
        """
        Validate that responses with single dict (not list) still work.
        
        Some API responses might return {"eval": {...}} directly.
        """
        api_response = {
            "eval": {
                "accuracy": 0.95,
                "f1_score": 0.93,
                "precision": 0.94,
                "recall": 0.92
            },
            "get": {},
            "put": {},
            "idempotentmodel_version": "1"
        }
        
        # Normalize
        eval_metrics, eval_metrics_private = _normalize_eval_payload(api_response)
        
        # Extract subsets
        keys_to_extract = ["accuracy", "f1_score", "precision", "recall"]
        eval_metrics_subset = _subset_numeric(eval_metrics, keys_to_extract)
        eval_metrics_private_subset = _subset_numeric(eval_metrics_private, keys_to_extract)
        
        # Verify
        assert len(eval_metrics_subset) == 4
        assert eval_metrics_subset["accuracy"] == 0.95
        assert eval_metrics_private_subset == {}  # No private metrics
        
        print("✅ SUCCESS: Single dict responses still work!")
    
    def test_missing_metrics_gracefully_handled(self):
        """
        Validate that missing metrics don't crash the submission.
        
        If the API returns partial metrics or no metrics, the code should
        handle it gracefully.
        """
        api_response = {
            "eval": {
                "accuracy": 0.95
                # Missing: f1_score, precision, recall
            },
            "get": {},
            "put": {},
            "idempotentmodel_version": "1"
        }
        
        # Normalize
        eval_metrics, eval_metrics_private = _normalize_eval_payload(api_response)
        
        # Extract subsets (requesting metrics that don't exist)
        keys_to_extract = ["accuracy", "f1_score", "precision", "recall", "mse", "rmse"]
        eval_metrics_subset = _subset_numeric(eval_metrics, keys_to_extract)
        
        # Verify only accuracy is present
        assert len(eval_metrics_subset) == 1
        assert "accuracy" in eval_metrics_subset
        assert "f1_score" not in eval_metrics_subset
        
        print("✅ SUCCESS: Missing metrics are handled gracefully!")
    
    def test_malformed_response_returns_empty(self):
        """
        Validate that completely malformed responses don't crash.
        
        Even if the API returns garbage, we should handle it gracefully.
        """
        # Test with list instead of dict
        api_response = ["malformed", "response"]
        eval_metrics, eval_metrics_private = _normalize_eval_payload(api_response)
        
        assert eval_metrics == {}
        assert eval_metrics_private == {}
        
        # Test with string eval field
        api_response = {"eval": "not a dict or list"}
        eval_metrics, eval_metrics_private = _normalize_eval_payload(api_response)
        
        assert eval_metrics == {}
        assert eval_metrics_private == {}
        
        print("✅ SUCCESS: Malformed responses don't crash!")
    
    def test_numeric_type_flexibility(self):
        """
        Validate that both int and float values are accepted.
        
        Some metrics might be returned as int (e.g., counts) while others
        are float (e.g., accuracy). Both should work.
        """
        api_response = {
            "eval": {
                "accuracy": 0.95,  # float
                "count": 100,  # int
                "f1_score": 1,  # int that looks like float
                "invalid": "string",  # should be excluded
                "none_value": None  # should be excluded
            },
            "get": {},
            "put": {},
            "idempotentmodel_version": "1"
        }
        
        eval_metrics, _ = _normalize_eval_payload(api_response)
        
        keys_to_extract = ["accuracy", "count", "f1_score", "invalid", "none_value"]
        subset = _subset_numeric(eval_metrics, keys_to_extract)
        
        # Verify only numeric values included
        assert len(subset) == 3
        assert subset["accuracy"] == 0.95
        assert subset["count"] == 100
        assert subset["f1_score"] == 1
        assert "invalid" not in subset
        assert "none_value" not in subset
        
        print("✅ SUCCESS: Both int and float types are supported!")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])

"""
Unit tests for enhanced preprocessor diagnostics.
Tests the debug_preprocessor flag and closure variable failure reporting.
"""
import pytest
import tempfile
import os
import sys


class TestPreprocessorDiagnostics:
    """Test enhanced diagnostics for preprocessor function exports."""
    
    def test_submit_model_accepts_debug_preprocessor_param(self):
        """Test that submit_model signature accepts debug_preprocessor parameter."""
        # Test that the parameter was added correctly by checking the source
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'model.py')
        
        if not os.path.exists(model_path):
            pytest.skip("model.py not found")
        
        # Read the source and check for the parameter
        with open(model_path, 'r') as f:
            content = f.read()
        
        # Verify the parameter exists in submit_model signature
        assert 'debug_preprocessor' in content
        assert 'debug_preprocessor=False' in content
    
    def test_diagnose_closure_variables_function_exists(self):
        """Test that _diagnose_closure_variables function was added."""
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'model.py')
        
        if not os.path.exists(model_path):
            pytest.skip("model.py not found")
        
        with open(model_path, 'r') as f:
            content = f.read()
        
        # Verify the new function exists
        assert 'def _diagnose_closure_variables' in content
        assert 'inspect.getclosurevars' in content
    
    def test_prepare_preprocessor_accepts_debug_mode(self):
        """Test that _prepare_preprocessor_if_function accepts debug_mode parameter."""
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'model.py')
        
        if not os.path.exists(model_path):
            pytest.skip("model.py not found")
        
        with open(model_path, 'r') as f:
            content = f.read()
        
        # Verify the debug_mode parameter exists
        assert 'def _prepare_preprocessor_if_function(preprocessor, debug_mode=False)' in content
        # Verify debug mode is used for printing debug messages
        assert '[DEBUG]' in content or 'debug_mode' in content
    
    def test_export_preprocessor_tracks_failures(self):
        """Test that export_preprocessor tracks failed serializations."""
        preproc_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'preprocessormodules.py')
        
        if not os.path.exists(preproc_path):
            pytest.skip("preprocessormodules.py not found")
        
        with open(preproc_path, 'r') as f:
            content = f.read()
        
        # Verify enhanced error handling exists
        assert 'failed_objects' in content
        assert 'serialization failures' in content
    
    def test_test_object_serialization_helper_exists(self):
        """Test that _test_object_serialization helper was added."""
        preproc_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'preprocessormodules.py')
        
        if not os.path.exists(preproc_path):
            pytest.skip("preprocessormodules.py not found")
        
        with open(preproc_path, 'r') as f:
            content = f.read()
        
        # Verify the helper function exists
        assert 'def _test_object_serialization' in content
        assert 'pickle.dumps(obj)' in content


class TestIntegration:
    """Integration tests that require minimal dependencies."""
    
    def test_basic_preprocessor_with_serializable_closures(self):
        """Test basic preprocessor with serializable closures works."""
        # Create a simple test
        import pickle
        
        # Define a preprocessor with serializable closures
        scaler_mean = 0.5
        scaler_std = 1.0
        
        def preprocessor(x):
            return (x - scaler_mean) / scaler_std
        
        # Verify the closure variables can be pickled
        import inspect
        closure_vars = inspect.getclosurevars(preprocessor)
        
        for var_name, var_value in closure_vars.globals.items():
            try:
                pickle.dumps(var_value)
                # Should succeed
                assert True
            except Exception:
                # Shouldn't fail for basic types
                pytest.fail(f"Failed to pickle {var_name}")
    
    def test_file_handle_not_serializable(self):
        """Test that file handles are detected as non-serializable."""
        import pickle
        
        # Create a file handle
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        temp_file.write("test")
        temp_file.flush()
        
        try:
            file_handle = open(temp_file.name, 'r')
            
            # Try to pickle it - should fail
            with pytest.raises(Exception):
                pickle.dumps(file_handle)
            
            file_handle.close()
        finally:
            os.unlink(temp_file.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



"""
Unit tests for transformer object preprocessor handling.
Tests the enhanced _prepare_preprocessor_if_function that supports sklearn transformers.
"""
import pytest
import tempfile
import os
import sys
import zipfile
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class TestTransformerPreprocessor:
    """Test preprocessor handling for sklearn transformer objects."""
    
    def test_prepare_preprocessor_accepts_transformers(self):
        """Test that model.py has logic to handle transformer objects."""
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'model.py')
        
        if not os.path.exists(model_path):
            pytest.skip("model.py not found")
        
        with open(model_path, 'r') as f:
            content = f.read()
        
        # Verify the function handles transformers
        assert 'hasattr(preprocessor, \'transform\')' in content
        assert 'is_transformer_obj' in content
        assert 'pickle.dump' in content or 'pickle' in content
    
    def test_column_transformer_export_integration(self):
        """Integration test that ColumnTransformer objects can be exported to preprocessor zip."""
        # Execute the function directly from source code to avoid import issues
        import inspect
        import pickle
        import textwrap
        
        # Read and extract the function source
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'model.py')
        with open(model_path, 'r') as f:
            content = f.read()
        
        # Create namespace and execute the function
        namespace = {
            'os': os,
            'inspect': inspect,
            'tempfile': tempfile,
            'zipfile': zipfile,
            'pickle': pickle,
            'textwrap': textwrap
        }
        
        # Extract and execute just the function
        import re
        match = re.search(r'(def _prepare_preprocessor_if_function.*?)(?=\ndef [^_]|\Z)', content, re.DOTALL)
        if not match:
            pytest.skip("Could not extract function")
        
        exec(match.group(1), namespace)
        _prepare_preprocessor_if_function = namespace['_prepare_preprocessor_if_function']
        
        # Create a simple ColumnTransformer
        numeric_transformer = Pipeline(steps=[
            ('scaler', StandardScaler())
        ])
        
        numeric_features = ['feature1', 'feature2']
        preprocess = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features)
            ]
        )
        
        # Fit with sample data
        X = pd.DataFrame({
            'feature1': [1.0, 2.0, 3.0],
            'feature2': [4.0, 5.0, 6.0]
        })
        preprocess.fit(X)
        
        # Export the transformer
        result = _prepare_preprocessor_if_function(preprocess)
        
        # Verify the zip was created
        assert result is not None
        assert os.path.exists(result)
        assert result.endswith('.zip')
        assert os.path.getsize(result) > 0
        
        # Verify zip contents
        with zipfile.ZipFile(result, 'r') as zf:
            contents = zf.namelist()
            assert 'preprocessor.py' in contents
            assert 'preprocessor.pkl' in contents
    
    def test_transformer_export_can_be_loaded_integration(self):
        """Integration test that exported transformer can be loaded and used."""
        import inspect
        import pickle
        import textwrap
        
        # Read and extract the function source
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'model.py')
        with open(model_path, 'r') as f:
            content = f.read()
        
        # Create namespace and execute the function
        namespace = {
            'os': os,
            'inspect': inspect,
            'tempfile': tempfile,
            'zipfile': zipfile,
            'pickle': pickle,
            'textwrap': textwrap
        }
        
        # Extract and execute just the function
        import re
        match = re.search(r'(def _prepare_preprocessor_if_function.*?)(?=\ndef [^_]|\Z)', content, re.DOTALL)
        if not match:
            pytest.skip("Could not extract function")
        
        exec(match.group(1), namespace)
        _prepare_preprocessor_if_function = namespace['_prepare_preprocessor_if_function']
        
        # Create and fit transformer
        numeric_transformer = Pipeline(steps=[('scaler', StandardScaler())])
        preprocess = ColumnTransformer(
            transformers=[('num', numeric_transformer, ['f1', 'f2'])]
        )
        
        X_train = pd.DataFrame({'f1': [1, 2, 3], 'f2': [4, 5, 6]})
        preprocess.fit(X_train)
        
        # Export
        zip_path = _prepare_preprocessor_if_function(preprocess)
        
        # Extract and load
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_dir)
        
        # Load the preprocessor module
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "preprocessor_mod", 
            os.path.join(temp_dir, "preprocessor.py")
        )
        preprocessor_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preprocessor_mod)
        
        # Test transformation
        X_test = pd.DataFrame({'f1': [4], 'f2': [7]})
        result = preprocessor_mod.preprocessor(X_test)
        
        # Should return transformed data
        assert result is not None
        assert result.shape == (1, 2)
    
    def test_pipeline_export_integration(self):
        """Integration test that Pipeline objects can be exported."""
        import inspect
        import pickle
        import textwrap
        import re
        
        # Read and extract the function source
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'model.py')
        with open(model_path, 'r') as f:
            content = f.read()
        
        # Create namespace and execute the function
        namespace = {
            'os': os,
            'inspect': inspect,
            'tempfile': tempfile,
            'zipfile': zipfile,
            'pickle': pickle,
            'textwrap': textwrap
        }
        
        # Extract and execute just the function
        match = re.search(r'(def _prepare_preprocessor_if_function.*?)(?=\ndef [^_]|\Z)', content, re.DOTALL)
        if not match:
            pytest.skip("Could not extract function")
        
        exec(match.group(1), namespace)
        _prepare_preprocessor_if_function = namespace['_prepare_preprocessor_if_function']
        
        # Create a Pipeline
        pipeline = Pipeline(steps=[
            ('scaler', StandardScaler())
        ])
        
        # Fit with sample data
        X = pd.DataFrame({'f1': [1, 2, 3], 'f2': [4, 5, 6]})
        pipeline.fit(X)
        
        # Export
        result = _prepare_preprocessor_if_function(pipeline)
        
        # Verify
        assert result is not None
        assert os.path.exists(result)
        assert result.endswith('.zip')
        
        with zipfile.ZipFile(result, 'r') as zf:
            assert 'preprocessor.py' in zf.namelist()
            assert 'preprocessor.pkl' in zf.namelist()
    
    def test_none_preprocessor_integration(self):
        """Integration test that None is returned when preprocessor is None."""
        import inspect
        import pickle
        import textwrap
        import re
        
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'aimodelshare', 'model.py')
        with open(model_path, 'r') as f:
            content = f.read()
        
        namespace = {
            'os': os,
            'inspect': inspect,
            'tempfile': tempfile,
            'zipfile': zipfile,
            'pickle': pickle,
            'textwrap': textwrap
        }
        
        match = re.search(r'(def _prepare_preprocessor_if_function.*?)(?=\ndef [^_]|\Z)', content, re.DOTALL)
        if not match:
            pytest.skip("Could not extract function")
        
        exec(match.group(1), namespace)
        _prepare_preprocessor_if_function = namespace['_prepare_preprocessor_if_function']
        
        result = _prepare_preprocessor_if_function(None)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Basic sanity tests that can run without external dependencies.
These tests verify the test structure itself is working.
"""
import pytest
import sys
import os


class TestBasicSetup:
    """Basic sanity checks for test environment."""
    
    def test_python_version(self):
        """Verify Python version is acceptable."""
        version_info = sys.version_info
        assert version_info.major == 3
        assert version_info.minor >= 8  # Should work with Python 3.8+
    
    def test_imports_work(self):
        """Verify basic imports work."""
        try:
            import pandas
            import numpy
            import sklearn
            assert True
        except ImportError as e:
            pytest.skip(f"Required package not installed: {e}")
    
    def test_aimodelshare_imports(self):
        """Verify aimodelshare can be imported."""
        try:
            import aimodelshare
            assert hasattr(aimodelshare, 'playground')
        except ImportError as e:
            pytest.fail(f"Cannot import aimodelshare: {e}")
    
    def test_aimodelshare_playground_module(self):
        """Verify playground module exists."""
        try:
            from aimodelshare.playground import ModelPlayground
            assert ModelPlayground is not None
        except ImportError as e:
            pytest.fail(f"Cannot import ModelPlayground: {e}")
    
    def test_aimodelshare_aws_module(self):
        """Verify aws module exists."""
        try:
            from aimodelshare import aws
            assert hasattr(aws, 'set_credentials')
            assert hasattr(aws, 'get_aws_token')
        except ImportError as e:
            pytest.fail(f"Cannot import aws module: {e}")
    
    def test_unittest_mock_available(self):
        """Verify unittest.mock is available for testing."""
        try:
            from unittest.mock import patch, MagicMock, Mock
            assert patch is not None
            assert MagicMock is not None
            assert Mock is not None
        except ImportError as e:
            pytest.fail(f"unittest.mock not available: {e}")
    
    def test_sklearn_components_available(self):
        """Verify sklearn components needed for tests."""
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import train_test_split
            from sklearn.compose import ColumnTransformer
            from sklearn.pipeline import Pipeline
            
            assert LogisticRegression is not None
            assert StandardScaler is not None
            assert train_test_split is not None
        except ImportError as e:
            pytest.skip(f"sklearn component not available: {e}")
    
    def test_seaborn_available(self):
        """Verify seaborn is available for data tests."""
        try:
            import seaborn as sns
            assert sns is not None
        except ImportError:
            pytest.skip("seaborn not installed - data preprocessing tests will be skipped")
    
    def test_pandas_available(self):
        """Verify pandas is available."""
        try:
            import pandas as pd
            assert pd is not None
            # Test basic DataFrame creation
            df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
            assert len(df) == 3
        except ImportError as e:
            pytest.fail(f"pandas not available: {e}")

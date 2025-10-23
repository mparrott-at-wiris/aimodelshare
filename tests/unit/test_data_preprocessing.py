"""
Unit tests for data preprocessing and preparation.
These tests help isolate data preprocessing issues in the playground tests.
"""
import pytest
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


class TestDataPreprocessing:
    """Test data preprocessing functionality."""
    
    def test_penguin_dataset_loading(self):
        """Test that the penguins dataset can be loaded and processed."""
        try:
            import seaborn as sns
            penguins = sns.load_dataset("penguins")
            
            assert penguins is not None
            assert isinstance(penguins, pd.DataFrame)
            assert 'sex' in penguins.columns
            assert 'bill_length_mm' in penguins.columns
        except ImportError:
            pytest.skip("seaborn not installed")
    
    def test_penguin_dataset_dropna(self):
        """Test dropping NA values from penguins dataset."""
        try:
            import seaborn as sns
            penguins = sns.load_dataset("penguins").dropna()
            
            # Verify no NA values remain
            assert penguins.isnull().sum().sum() == 0
            assert len(penguins) > 0
        except ImportError:
            pytest.skip("seaborn not installed")
    
    def test_train_test_split_penguin_data(self):
        """Test train/test split on penguin data."""
        try:
            import seaborn as sns
            penguins = sns.load_dataset("penguins").dropna()
            X = penguins[['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']]
            y = penguins['sex']
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Verify shapes
            assert len(X_train) + len(X_test) == len(X)
            assert len(y_train) + len(y_test) == len(y)
            assert len(X_train) == len(y_train)
            assert len(X_test) == len(y_test)
            
            # Verify test size is approximately 20%
            expected_test_size = int(len(X) * 0.2)
            assert abs(len(X_test) - expected_test_size) <= 1
        except ImportError:
            pytest.skip("seaborn not installed")
    
    def test_preprocessor_creation(self):
        """Test creating a StandardScaler preprocessor."""
        # Create sample data
        X = pd.DataFrame({
            'feature1': [1.0, 2.0, 3.0, 4.0, 5.0],
            'feature2': [10.0, 20.0, 30.0, 40.0, 50.0],
            'feature3': [100.0, 200.0, 300.0, 400.0, 500.0],
            'feature4': [5.0, 15.0, 25.0, 35.0, 45.0]
        })
        
        numeric_features = ['feature1', 'feature2', 'feature3', 'feature4']
        numeric_transformer = Pipeline(steps=[
            ('scaler', StandardScaler())
        ])
        
        preprocess = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features)
            ]
        )
        
        # Fit the preprocessor
        preprocess.fit(X)
        
        # Transform data
        X_transformed = preprocess.transform(X)
        
        # Verify transformation
        assert X_transformed.shape == X.shape
        # StandardScaler should result in approximately zero mean
        assert np.abs(X_transformed.mean(axis=0)).max() < 1e-10
    
    def test_preprocessor_function_wrapper(self):
        """Test creating a preprocessor function wrapper."""
        # Create sample data
        X = pd.DataFrame({
            'feature1': [1.0, 2.0, 3.0],
            'feature2': [10.0, 20.0, 30.0]
        })
        
        numeric_transformer = Pipeline(steps=[
            ('scaler', StandardScaler())
        ])
        
        preprocess = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, ['feature1', 'feature2'])
            ]
        )
        
        preprocess.fit(X)
        
        # Create wrapper function
        def preprocessor(data):
            preprocessed_data = preprocess.transform(data)
            return preprocessed_data
        
        # Test the wrapper
        result = preprocessor(X)
        assert result is not None
        assert result.shape == (3, 2)
    
    def test_y_labels_conversion_to_list(self):
        """Test converting y_test to list of labels."""
        try:
            import seaborn as sns
            penguins = sns.load_dataset("penguins").dropna()
            y = penguins['sex']
            
            X_train, X_test, y_train, y_test = train_test_split(
                penguins[['bill_length_mm', 'bill_depth_mm']], 
                y, 
                test_size=0.2, 
                random_state=42
            )
            
            # Convert to list
            y_test_labels = list(y_test)
            
            # Verify conversion
            assert isinstance(y_test_labels, list)
            assert len(y_test_labels) > 0
            assert all(isinstance(label, str) for label in y_test_labels)
        except ImportError:
            pytest.skip("seaborn not installed")
    
    def test_example_data_copy(self):
        """Test creating a copy of test data for deployment."""
        try:
            import seaborn as sns
            penguins = sns.load_dataset("penguins").dropna()
            X = penguins[['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']]
            
            X_train, X_test, _, _ = train_test_split(
                X, penguins['sex'], test_size=0.2, random_state=42
            )
            
            # Create example data copy
            example_data = X_test.copy()
            
            # Verify it's a copy and has the right structure
            assert example_data is not X_test  # Different object
            assert example_data.equals(X_test)  # Same values
            assert isinstance(example_data, pd.DataFrame)
        except ImportError:
            pytest.skip("seaborn not installed")

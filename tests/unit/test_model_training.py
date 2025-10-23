"""
Unit tests for model training and prediction.
These tests help isolate model training issues in the playground tests.
"""
import pytest
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


class TestModelTraining:
    """Test model training functionality."""
    
    def test_logistic_regression_creation(self):
        """Test creating a LogisticRegression model."""
        model = LogisticRegression()
        
        assert model is not None
        assert isinstance(model, LogisticRegression)
    
    def test_model_training_with_simple_data(self):
        """Test training a model with simple synthetic data."""
        # Create simple synthetic data
        X = np.array([[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]])
        y = np.array(['A', 'A', 'B', 'B', 'A', 'B'])
        
        model = LogisticRegression()
        model.fit(X, y)
        
        # Verify model is trained
        assert hasattr(model, 'classes_')
        assert len(model.classes_) == 2
    
    def test_model_prediction(self):
        """Test model prediction functionality."""
        # Create simple synthetic data
        X = np.array([[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]])
        y = np.array(['A', 'A', 'B', 'B', 'A', 'B'])
        
        model = LogisticRegression()
        model.fit(X, y)
        
        # Make predictions
        predictions = model.predict(X)
        
        # Verify predictions
        assert predictions is not None
        assert len(predictions) == len(y)
        assert all(pred in ['A', 'B'] for pred in predictions)
    
    def test_penguin_model_training(self):
        """Test training a model on penguin data."""
        try:
            import seaborn as sns
            penguins = sns.load_dataset("penguins").dropna()
            X = penguins[['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']]
            y = penguins['sex']
            
            # Scale the data
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train model
            model = LogisticRegression()
            model.fit(X_scaled, y)
            
            # Verify model is trained
            assert hasattr(model, 'classes_')
            assert 'Male' in model.classes_ or 'Female' in model.classes_
        except ImportError:
            pytest.skip("seaborn not installed")
    
    def test_prediction_labels_generation(self):
        """Test generating prediction labels from model."""
        try:
            import seaborn as sns
            penguins = sns.load_dataset("penguins").dropna()
            X = penguins[['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']]
            y = penguins['sex']
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale and train
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            model = LogisticRegression()
            model.fit(X_train_scaled, y_train)
            
            # Generate predictions
            prediction_labels = model.predict(X_test_scaled)
            
            # Verify predictions
            assert len(prediction_labels) == len(X_test)
            assert all(isinstance(label, str) for label in prediction_labels)
        except ImportError:
            pytest.skip("seaborn not installed")
    
    def test_model_with_preprocessor_function(self):
        """Test model training with preprocessor function."""
        try:
            import seaborn as sns
            from sklearn.compose import ColumnTransformer
            from sklearn.pipeline import Pipeline
            
            penguins = sns.load_dataset("penguins").dropna()
            X = penguins[['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']]
            y = penguins['sex']
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Create preprocessor
            numeric_features = ['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']
            numeric_transformer = Pipeline(steps=[
                ('scaler', StandardScaler())
            ])
            
            preprocess = ColumnTransformer(
                transformers=[
                    ('num', numeric_transformer, numeric_features)
                ]
            )
            
            preprocess.fit(X_train)
            
            # Create preprocessor function
            def preprocessor(data):
                return preprocess.transform(data)
            
            # Train model with preprocessor
            model = LogisticRegression()
            model.fit(preprocessor(X_train), y_train)
            
            # Make predictions
            predictions = model.predict(preprocessor(X_test))
            
            # Verify
            assert len(predictions) == len(X_test)
            assert predictions is not None
        except ImportError:
            pytest.skip("seaborn not installed")
    
    def test_model_score(self):
        """Test model scoring functionality."""
        # Create simple synthetic data
        X = np.array([[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]] * 10)
        y = np.array(['A', 'A', 'B', 'B', 'A', 'B'] * 10)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        model = LogisticRegression()
        model.fit(X_train, y_train)
        
        # Get score
        score = model.score(X_test, y_test)
        
        # Verify score is valid
        assert score is not None
        assert 0 <= score <= 1

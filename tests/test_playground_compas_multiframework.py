"""
Multi-framework integration test using ProPublica COMPAS two-year recidivism dataset.

Tests joint submissions from sklearn, Keras, and PyTorch models in a single public playground competition.
Includes bias-related features (race, sex, age, age_cat, charge info) to validate model submission
pipeline and leaderboard metadata handling.

Uses session-scoped fixtures for playground and preprocessing to reduce overhead.
Sampling cap (MAX_ROWS=4000) for manageable CI runtime.
"""

import os
import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
import requests
from io import StringIO

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# Sklearn classifiers
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

# TensorFlow/Keras
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# PyTorch
import torch
import torch.nn as nn
import torch.nn.functional as F

from aimodelshare.playground import ModelPlayground
from aimodelshare.aws import set_credentials, get_aws_token
from aimodelshare.modeluser import get_jwt_token, create_user_getkeyandpassword


# Set seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)
torch.manual_seed(42)

# Dataset configuration
MAX_ROWS = 4000  # Sampling cap for CI performance
TOP_N_CHARGE_CATEGORIES = 50  # Top N frequent c_charge_desc categories to keep


@pytest.fixture(scope="session")
def credentials():
    """Setup credentials for playground tests (session-scoped)."""
    # Try to load from file first (for local testing)
    try:
        set_credentials(credential_file="../../../credentials.txt", type="deploy_model")
        return
    except Exception:
        pass
    
    try:
        set_credentials(credential_file="../../credentials.txt", type="deploy_model")
        return
    except Exception:
        pass
    
    # Mock user input from environment variables
    inputs = [
        os.environ.get('username'),
        os.environ.get('password'),
        os.environ.get('AWS_ACCESS_KEY_ID'),
        os.environ.get('AWS_SECRET_ACCESS_KEY'),
        os.environ.get('AWS_REGION')
    ]
    
    with patch("getpass.getpass", side_effect=inputs):
        from aimodelshare.aws import configure_credentials
        configure_credentials()
    
    # Set credentials
    set_credentials(credential_file="credentials.txt", type="deploy_model")
    
    # Clean up credentials file
    if os.path.exists("credentials.txt"):
        os.remove("credentials.txt")


@pytest.fixture(scope="session")
def aws_environment(credentials):
    """Setup AWS environment variables (session-scoped)."""
    try:
        os.environ['AWS_TOKEN'] = get_aws_token()
        os.environ['AWS_ACCESS_KEY_ID_AIMS'] = os.environ.get('AWS_ACCESS_KEY_ID')
        os.environ['AWS_SECRET_ACCESS_KEY_AIMS'] = os.environ.get('AWS_SECRET_ACCESS_KEY')
        os.environ['AWS_REGION_AIMS'] = os.environ.get('AWS_REGION')
    except Exception as e:
        print(f"Warning: Could not set AWS environment: {e}")
    
    # Validate JWT tokens
    try:
        get_jwt_token(os.environ.get('username'), os.environ.get('password'))
        create_user_getkeyandpassword()
    except Exception as e:
        print(f"Warning: Could not validate JWT tokens: {e}")


@pytest.fixture(scope="session")
def compas_data():
    """
    Load and prepare COMPAS dataset (session-scoped).
    
    Downloads ProPublica COMPAS two-year recidivism dataset and prepares features.
    Includes bias-related features: race, sex, age, age_cat, c_charge_degree, 
    c_charge_desc (top N categories), priors_count, juvenile counts, days_b_screening_arrest.
    
    Excludes decile_score and is_recid to avoid target leakage.
    """
    # Download COMPAS dataset
    url = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"
    response = requests.get(url)
    df = pd.read_csv(StringIO(response.text))
    
    print(f"Downloaded COMPAS dataset: {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Sample if needed
    if df.shape[0] > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42)
        print(f"Sampled to {MAX_ROWS} rows for CI performance")
    
    # Select features (excluding decile_score and is_recid to avoid leakage)
    feature_columns = [
        'race', 'sex', 'age', 'age_cat', 
        'c_charge_degree', 'c_charge_desc',
        'priors_count', 'juv_fel_count', 'juv_misd_count', 'juv_other_count',
        'days_b_screening_arrest'
    ]
    target_column = 'two_year_recid'
    
    # Handle c_charge_desc: keep top N categories, set others to 'OTHER_DESC'
    if 'c_charge_desc' in df.columns:
        top_charges = df['c_charge_desc'].value_counts().head(TOP_N_CHARGE_CATEGORIES).index
        df['c_charge_desc'] = df['c_charge_desc'].apply(
            lambda x: x if pd.notna(x) and x in top_charges else 'OTHER_DESC'
        )
    
    # Prepare features and target
    X = df[feature_columns].copy()
    y = df[target_column].values
    
    print(f"Features: {X.shape[1]} columns")
    print(f"Target distribution: {pd.Series(y).value_counts().to_dict()}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    # Define numeric and categorical columns
    numeric_features = ['age', 'priors_count', 'juv_fel_count', 'juv_misd_count', 
                       'juv_other_count', 'days_b_screening_arrest']
    categorical_features = ['race', 'sex', 'age_cat', 'c_charge_degree', 'c_charge_desc']
    
    # Build preprocessing pipeline
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])
    
    # Fit preprocessor on training data
    preprocessor.fit(X_train)
    
    # Create preprocessor function
    def preprocessor_func(data):
        return preprocessor.transform(data)
    
    return X_train, X_test, y_train, y_test, preprocessor, preprocessor_func


@pytest.fixture(scope="session")
def shared_playground(credentials, aws_environment, compas_data):
    """Create a shared ModelPlayground instance for all tests (session-scoped)."""
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func = compas_data
    eval_labels = list(y_test)
    
    # Create playground
    playground = ModelPlayground(
        input_type='tabular',
        task_type='classification',
        private=True
    )
    playground.create(eval_data=eval_labels, public=True)
    print(f"✓ Shared playground created successfully")
    
    return playground


def test_sklearn_logistic_regression(shared_playground, compas_data):
    """Test sklearn LogisticRegression submission with preprocessor."""
    print(f"\n{'='*60}")
    print(f"Testing: sklearn LogisticRegression")
    print(f"{'='*60}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func = compas_data
    
    # Preprocess data
    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)
    
    # Train model
    try:
        model = LogisticRegression(class_weight='balanced', max_iter=500, random_state=42)
        model.fit(X_train_processed, y_train)
        
        # Generate predictions (probability threshold 0.5)
        proba = model.predict_proba(X_test_processed)[:, 1]
        preds = (proba >= 0.5).astype(int)
        
        print(f"✓ Model trained successfully, generated {len(preds)} predictions")
        print(f"  Prediction distribution: {pd.Series(preds).value_counts().to_dict()}")
    except Exception as e:
        pytest.fail(f"Failed to train LogisticRegression: {e}")
    
    # Submit model with preprocessor
    try:
        shared_playground.submit_model(
            model=model,
            preprocessor=preprocessor,
            prediction_submission=preds,
            input_dict={
                'description': 'CI test sklearn LogisticRegression COMPAS',
                'tags': 'compas,bias,sklearn,logistic_regression'
            },
            submission_type='experiment'
        )
        print(f"✓ Submission succeeded")
    except Exception as e:
        pytest.fail(f"Submission failed for LogisticRegression: {e}")


def test_sklearn_random_forest(shared_playground, compas_data):
    """Test sklearn RandomForestClassifier submission with preprocessor."""
    print(f"\n{'='*60}")
    print(f"Testing: sklearn RandomForestClassifier")
    print(f"{'='*60}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func = compas_data
    
    # Preprocess data
    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)
    
    # Train model
    try:
        model = RandomForestClassifier(
            n_estimators=60, 
            max_depth=12, 
            class_weight='balanced', 
            random_state=42
        )
        model.fit(X_train_processed, y_train)
        
        # Generate predictions (probability threshold 0.5)
        proba = model.predict_proba(X_test_processed)[:, 1]
        preds = (proba >= 0.5).astype(int)
        
        print(f"✓ Model trained successfully, generated {len(preds)} predictions")
        print(f"  Prediction distribution: {pd.Series(preds).value_counts().to_dict()}")
    except Exception as e:
        pytest.fail(f"Failed to train RandomForestClassifier: {e}")
    
    # Submit model with preprocessor
    try:
        shared_playground.submit_model(
            model=model,
            preprocessor=preprocessor,
            prediction_submission=preds,
            input_dict={
                'description': 'CI test sklearn RandomForest COMPAS',
                'tags': 'compas,bias,sklearn,random_forest'
            },
            submission_type='experiment'
        )
        print(f"✓ Submission succeeded")
    except Exception as e:
        pytest.fail(f"Submission failed for RandomForestClassifier: {e}")


def test_keras_dense_network(shared_playground, compas_data):
    """Test Keras Dense network submission with preprocessor."""
    print(f"\n{'='*60}")
    print(f"Testing: Keras Dense Network")
    print(f"{'='*60}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func = compas_data
    
    # Preprocess data
    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)
    
    input_dim = X_train_processed.shape[1]
    
    # Build Keras model (64->32->1 sigmoid)
    try:
        model = keras.Sequential([
            layers.Dense(64, activation='relu', input_shape=(input_dim,)),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        # Train model (epochs=8, batch_size=64)
        model.fit(
            X_train_processed, y_train,
            epochs=8,
            batch_size=64,
            verbose=0,
            validation_split=0.1
        )
        
        # Generate predictions (probability threshold 0.5)
        proba = model.predict(X_test_processed, verbose=0).flatten()
        preds = (proba >= 0.5).astype(int)
        
        print(f"✓ Model trained successfully, generated {len(preds)} predictions")
        print(f"  Prediction distribution: {pd.Series(preds).value_counts().to_dict()}")
    except Exception as e:
        pytest.fail(f"Failed to train Keras model: {e}")
    
    # Submit model with preprocessor
    try:
        shared_playground.submit_model(
            model=model,
            preprocessor=preprocessor,
            prediction_submission=preds,
            input_dict={
                'description': 'CI test Keras Dense COMPAS',
                'tags': 'compas,bias,keras,dense_network'
            },
            submission_type='experiment'
        )
        print(f"✓ Submission succeeded")
    except Exception as e:
        pytest.fail(f"Submission failed for Keras model: {e}")


class PyTorchMLP(nn.Module):
    """PyTorch MLP for binary classification (64->32->1)."""
    
    def __init__(self, input_dim):
        super(PyTorchMLP, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def test_pytorch_mlp(shared_playground, compas_data):
    """Test PyTorch MLP submission with preprocessor and dummy forward pass for ONNX."""
    print(f"\n{'='*60}")
    print(f"Testing: PyTorch MLP")
    print(f"{'='*60}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func = compas_data
    
    # Preprocess data
    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)
    
    input_dim = X_train_processed.shape[1]
    
    # Build and train PyTorch model
    try:
        model = PyTorchMLP(input_dim)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train_processed)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
        X_test_tensor = torch.FloatTensor(X_test_processed)
        
        # Setup training
        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        # Create dataset and dataloader
        dataset = torch.utils.data.TensorDataset(X_train_tensor, y_train_tensor)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)
        
        # Training loop (epochs=8)
        model.train()
        for epoch in range(8):
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
        
        # Generate predictions (probability threshold 0.5)
        model.eval()
        with torch.no_grad():
            logits = model(X_test_tensor)
            proba = torch.sigmoid(logits).numpy().flatten()
            preds = (proba >= 0.5).astype(int)
        
        print(f"✓ Model trained successfully, generated {len(preds)} predictions")
        print(f"  Prediction distribution: {pd.Series(preds).value_counts().to_dict()}")
        
        # Create dummy input for ONNX tracing
        dummy_input = torch.randn((1, input_dim), dtype=torch.float32)
        
        # Perform a lightweight forward pass to ensure module parameters are initialized
        model.eval()
        with torch.no_grad():
            _ = model(dummy_input)
        
    except Exception as e:
        pytest.fail(f"Failed to train PyTorch model: {e}")
    
    # Submit model with preprocessor and dummy input
    try:
        shared_playground.submit_model(
            model=model,
            preprocessor=preprocessor,
            prediction_submission=preds,
            input_dict={
                'description': 'CI test PyTorch MLP COMPAS',
                'tags': 'compas,bias,pytorch,mlp'
            },
            submission_type='experiment',
            model_input=dummy_input
        )
        print(f"✓ Submission succeeded")
    except Exception as e:
        pytest.fail(f"Submission failed for PyTorch model: {e}")


def test_leaderboard_validation(shared_playground):
    """
    Validate leaderboard contains all submitted models with correct tags.
    
    Ensures presence of submissions from sklearn, Keras, and PyTorch frameworks
    with tags 'compas' and 'bias'.
    """
    print(f"\n{'='*60}")
    print(f"Testing: Leaderboard Validation")
    print(f"{'='*60}")
    
    # Get leaderboard
    try:
        data = shared_playground.get_leaderboard()
        
        # Handle both dict and DataFrame responses
        if isinstance(data, dict):
            df = pd.DataFrame(data)
            assert not df.empty, (
                'Leaderboard dict converted to empty DataFrame. '
                'Expected: Non-empty leaderboard with model submission entries.'
            )
            print(f"✓ Leaderboard retrieved (dict -> DataFrame): {len(df)} entries")
        else:
            assert isinstance(data, pd.DataFrame), (
                f'Leaderboard did not return a DataFrame, got {type(data).__name__}. '
                'Expected: DataFrame or dict convertible to DataFrame.'
            )
            assert not data.empty, (
                'Leaderboard DataFrame is empty. '
                'Expected: Non-empty leaderboard with model submission entries.'
            )
            df = data
            print(f"✓ Leaderboard retrieved (DataFrame): {len(df)} entries")
        
        # Check for presence of tags if tags column exists
        if 'tags' in df.columns:
            # Check for compas and bias tags
            compas_tagged = df['tags'].astype(str).str.contains('compas', case=False, na=False)
            bias_tagged = df['tags'].astype(str).str.contains('bias', case=False, na=False)
            
            print(f"  Entries with 'compas' tag: {compas_tagged.sum()}")
            print(f"  Entries with 'bias' tag: {bias_tagged.sum()}")
            
            # Validate that we have submissions with both tags
            assert compas_tagged.any(), "Expected at least one submission with 'compas' tag"
            assert bias_tagged.any(), "Expected at least one submission with 'bias' tag"
        
        # Check for framework diversity if description column exists
        if 'description' in df.columns:
            sklearn_present = df['description'].astype(str).str.contains('sklearn', case=False, na=False).any()
            keras_present = df['description'].astype(str).str.contains('Keras', case=False, na=False).any()
            pytorch_present = df['description'].astype(str).str.contains('PyTorch', case=False, na=False).any()
            
            print(f"  sklearn submissions present: {sklearn_present}")
            print(f"  Keras submissions present: {keras_present}")
            print(f"  PyTorch submissions present: {pytorch_present}")
            
            # Validate multi-framework presence
            assert sklearn_present, "Expected at least one sklearn submission"
            assert keras_present, "Expected at least one Keras submission"
            assert pytorch_present, "Expected at least one PyTorch submission"
        
        print(df.head())
        print(f"✓ Leaderboard validation test passed")
        
    except Exception as e:
        pytest.fail(f"Leaderboard validation failed: {e}")

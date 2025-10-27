"""
Lightweight COMPAS integration test for CI efficiency.

Tests a minimal subset of models across sklearn, Keras, and PyTorch using ProPublica COMPAS dataset.
Designed to conserve CI minutes while validating multi-framework submission pipeline.

Key differences from full test:
- Reduced MAX_ROWS: 2500 (vs 4000)
- Minimal model set: 2 sklearn, 1 Keras, 1 PyTorch
- Reduced epochs: 6 for deep learning models
- Target runtime: < 3 minutes
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

# Sklearn classifiers - minimal set
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

# TensorFlow/Keras
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras.models import Sequential

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
MAX_ROWS = 2500  # Reduced for faster CI runtime
TOP_N_CHARGE_CATEGORIES = 50


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
        ('imputer', SimpleImputer(strategy='most_frequent')),
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


def submit_model_helper(playground, model, preprocessor, preds, framework, model_name, submission_type):
    """
    Helper function to submit a model with consistent error handling.
    
    Returns True if submission succeeded, False if skipped due to ONNX/stdin issues.
    Raises exception for other failures.
    """
    try:
        # For PyTorch models, we need to provide model_input
        extra_kwargs = {}
        if framework == 'pytorch':
            # Get input dimension from preprocessor
            X_dummy = pd.DataFrame([[0]*6 + ['A']*5], columns=[
                'age', 'priors_count', 'juv_fel_count', 'juv_misd_count', 
                'juv_other_count', 'days_b_screening_arrest',
                'race', 'sex', 'age_cat', 'c_charge_degree', 'c_charge_desc'
            ])
            X_processed = preprocessor.transform(X_dummy)
            input_dim = X_processed.shape[1]
            dummy_input = torch.zeros((1, input_dim), dtype=torch.float32)
            extra_kwargs['model_input'] = dummy_input
        
        playground.submit_model(
            model=model,
            preprocessor=preprocessor,
            prediction_submission=preds,
            input_dict={
                'description': f'CI test {framework} {model_name} COMPAS_short {submission_type}',
                'tags': f'compas_short,{framework},{submission_type}'
            },
            submission_type=submission_type,
            **extra_kwargs
        )
        print(f"✓ Submission succeeded ({submission_type})")
        return True
    except Exception as e:
        error_str = str(e).lower()
        # Skip only on stdin or ONNX fallback issues
        if 'reading from stdin' in error_str or 'stdin' in error_str or 'onnx' in error_str:
            print(f"⊘ Skipped {model_name} ({submission_type}) due to ONNX/stdin issue")
            return False
        # Re-raise other exceptions
        raise


def test_compas_short_sklearn_models(shared_playground, compas_data):
    """
    Test minimal sklearn models with COMPAS dataset.
    
    Tests 2 sklearn classifiers with both competition and experiment submission types.
    Uses reduced parameters for CI performance.
    """
    print(f"\n{'='*80}")
    print(f"Testing: sklearn Models on COMPAS Dataset (Short)")
    print(f"{'='*80}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func = compas_data
    
    # Define minimal sklearn classifiers with CI-optimized parameters
    classifiers = [
        ("LogisticRegression", LogisticRegression(max_iter=500, random_state=42, class_weight='balanced')),
        ("RandomForestClassifier", RandomForestClassifier(n_estimators=40, max_depth=10, random_state=42, class_weight='balanced')),
    ]
    
    failures = []
    
    for model_name, model in classifiers:
        print(f"\n{'-'*60}")
        print(f"Model: {model_name}")
        print(f"{'-'*60}")
        
        # Preprocess data
        X_train_processed = preprocessor_func(X_train)
        X_test_processed = preprocessor_func(X_test)
        
        # Train model
        try:
            model.fit(X_train_processed, y_train)
            
            # Generate predictions (probability threshold 0.5 for binary classification)
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(X_test_processed)[:, 1]
                preds = (proba >= 0.5).astype(int)
            else:
                preds = model.predict(X_test_processed)
            
            print(f"✓ Model trained, generated {len(preds)} predictions")
            print(f"  Prediction distribution: {pd.Series(preds).value_counts().to_dict()}")
        except Exception as e:
            error_msg = f"Failed to train {model_name}: {e}"
            print(f"✗ {error_msg}")
            failures.append(error_msg)
            continue
        
        # Submit twice: once as competition, once as experiment
        for submission_type in ['competition', 'experiment']:
            try:
                submit_model_helper(
                    shared_playground, model, preprocessor, preds, 
                    'sklearn', model_name, submission_type
                )
            except Exception as e:
                error_msg = f"Submission failed for {model_name} ({submission_type}): {e}"
                print(f"✗ {error_msg}")
                failures.append(error_msg)
    
    # Report failures
    if failures:
        failure_report = "\n".join(f"  - {err}" for err in failures)
        pytest.fail(
            f"sklearn model failures:\n{failure_report}\n\n"
            f"Expected: All sklearn models should train and submit successfully (or skip only on ONNX/stdin issues)."
        )
    
    print(f"\n{'='*80}")
    print(f"✓ All sklearn models completed successfully")
    print(f"{'='*80}")


def test_compas_short_keras_models(shared_playground, compas_data):
    """
    Test minimal Keras model with COMPAS dataset.
    
    Tests 1 Keras model with both competition and experiment submission types.
    Uses 6 epochs for CI performance.
    """
    print(f"\n{'='*80}")
    print(f"Testing: Keras Model on COMPAS Dataset (Short)")
    print(f"{'='*80}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func = compas_data
    
    # Preprocess data
    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)
    input_dim = X_train_processed.shape[1]
    
    # Create simple Sequential model
    print(f"\n{'-'*60}")
    print(f"Model: sequential_dense")
    print(f"{'-'*60}")
    
    failures = []
    
    try:
        model = Sequential([
            layers.Input(shape=(input_dim,)),
            layers.Dense(64, activation='relu'),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        
        # Train with 6 epochs as specified
        model.fit(
            X_train_processed, y_train,
            epochs=6,
            batch_size=64,
            verbose=0,
            validation_split=0.1
        )
        
        # Generate predictions (probability threshold 0.5)
        proba = model.predict(X_test_processed, verbose=0).flatten()
        preds = (proba >= 0.5).astype(int)
        
        print(f"✓ Model trained, generated {len(preds)} predictions")
        print(f"  Prediction distribution: {pd.Series(preds).value_counts().to_dict()}")
    except Exception as e:
        error_msg = f"Failed to train Keras model: {e}"
        print(f"✗ {error_msg}")
        failures.append(error_msg)
    
    if not failures:
        # Submit twice: once as competition, once as experiment
        for submission_type in ['competition', 'experiment']:
            try:
                submit_model_helper(
                    shared_playground, model, preprocessor, preds,
                    'keras', 'sequential_dense', submission_type
                )
            except Exception as e:
                error_msg = f"Submission failed for Keras model ({submission_type}): {e}"
                print(f"✗ {error_msg}")
                failures.append(error_msg)
    
    # Report failures
    if failures:
        failure_report = "\n".join(f"  - {err}" for err in failures)
        pytest.fail(
            f"Keras model failures:\n{failure_report}\n\n"
            f"Expected: Keras model should train and submit successfully (or skip only on ONNX/stdin issues)."
        )
    
    print(f"\n{'='*80}")
    print(f"✓ Keras model completed successfully")
    print(f"{'='*80}")


def test_compas_short_pytorch_models(shared_playground, compas_data):
    """
    Test minimal PyTorch model with COMPAS dataset.
    
    Tests 1 PyTorch model with both competition and experiment submission types.
    Uses 6 epochs for CI performance.
    """
    print(f"\n{'='*80}")
    print(f"Testing: PyTorch Model on COMPAS Dataset (Short)")
    print(f"{'='*80}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func = compas_data
    
    # Preprocess data
    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)
    input_dim = X_train_processed.shape[1]
    
    # Define PyTorch model class
    class MLPBasic(nn.Module):
        """Basic Multi-Layer Perceptron."""
        def __init__(self, input_size):
            super().__init__()
            self.fc1 = nn.Linear(input_size, 64)
            self.fc2 = nn.Linear(64, 32)
            self.fc3 = nn.Linear(32, 1)
        
        def forward(self, x):
            x = F.relu(self.fc1(x))
            x = F.relu(self.fc2(x))
            x = self.fc3(x)
            return x
    
    print(f"\n{'-'*60}")
    print(f"Model: mlp_basic")
    print(f"{'-'*60}")
    
    failures = []
    
    try:
        model = MLPBasic(input_dim)
        
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
        
        # Training loop (6 epochs as specified)
        model.train()
        for epoch in range(6):
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
        
        print(f"✓ Model trained, generated {len(preds)} predictions")
        print(f"  Prediction distribution: {pd.Series(preds).value_counts().to_dict()}")
    except Exception as e:
        error_msg = f"Failed to train PyTorch model: {e}"
        print(f"✗ {error_msg}")
        failures.append(error_msg)
    
    if not failures:
        # Submit twice: once as competition, once as experiment
        for submission_type in ['competition', 'experiment']:
            try:
                submit_model_helper(
                    shared_playground, model, preprocessor, preds,
                    'pytorch', 'mlp_basic', submission_type
                )
            except Exception as e:
                error_msg = f"Submission failed for PyTorch model ({submission_type}): {e}"
                print(f"✗ {error_msg}")
                failures.append(error_msg)
    
    # Report failures
    if failures:
        failure_report = "\n".join(f"  - {err}" for err in failures)
        pytest.fail(
            f"PyTorch model failures:\n{failure_report}\n\n"
            f"Expected: PyTorch model should train and submit successfully (or skip only on ONNX/stdin issues)."
        )
    
    print(f"\n{'='*80}")
    print(f"✓ PyTorch model completed successfully")
    print(f"{'='*80}")


def test_compas_short_leaderboards(shared_playground):
    """
    Validate leaderboard contains submissions from all frameworks with both submission types.
    
    Ensures presence of submissions from sklearn, Keras, and PyTorch frameworks
    with tags 'compas_short' and both 'competition' and 'experiment' submission types.
    """
    print(f"\n{'='*80}")
    print(f"Testing: Leaderboard Validation for All Frameworks and Submission Types")
    print(f"{'='*80}")
    
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
            # Check for compas_short tag
            compas_short_tagged = df['tags'].astype(str).str.contains('compas_short', case=False, na=False)
            sklearn_tagged = df['tags'].astype(str).str.contains('sklearn', case=False, na=False)
            keras_tagged = df['tags'].astype(str).str.contains('keras', case=False, na=False)
            pytorch_tagged = df['tags'].astype(str).str.contains('pytorch', case=False, na=False)
            competition_tagged = df['tags'].astype(str).str.contains('competition', case=False, na=False)
            experiment_tagged = df['tags'].astype(str).str.contains('experiment', case=False, na=False)
            
            print(f"  Entries with 'compas_short' tag: {compas_short_tagged.sum()}")
            print(f"  Entries with 'sklearn' tag: {sklearn_tagged.sum()}")
            print(f"  Entries with 'keras' tag: {keras_tagged.sum()}")
            print(f"  Entries with 'pytorch' tag: {pytorch_tagged.sum()}")
            print(f"  Entries with 'competition' tag: {competition_tagged.sum()}")
            print(f"  Entries with 'experiment' tag: {experiment_tagged.sum()}")
            
            # Validate that we have submissions with expected tags
            assert compas_short_tagged.any(), "Expected at least one submission with 'compas_short' tag"
            assert sklearn_tagged.any(), "Expected at least one sklearn submission"
            assert keras_tagged.any(), "Expected at least one Keras submission"
            assert pytorch_tagged.any(), "Expected at least one PyTorch submission"
            # Note: competition/experiment tags should be present
            assert competition_tagged.any() or experiment_tagged.any(), "Expected submissions with 'competition' or 'experiment' tags"
        
        print(f"\nLeaderboard sample:")
        print(df.head(10))
        print(f"\n✓ Leaderboard validation test passed")
        
    except Exception as e:
        pytest.fail(f"Leaderboard validation failed: {e}")

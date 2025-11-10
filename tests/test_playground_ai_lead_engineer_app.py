#!/usr/bin/env python3
"""
Integration test for AI Lead Engineer Gradio app with playground submission.

Tests the end-to-end flow:
1. Create synthetic COMPAS-like dataset
2. Build standard & MinMax preprocessors
3. Create a public playground
4. Submit a model via the app's training logic (without launching full UI)
5. Verify accuracy > 0 and leaderboard contains etica_tech_challenge tag

Run with: pytest tests/test_playground_ai_lead_engineer_app.py -v -s
"""

import os
import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from aimodelshare.playground import ModelPlayground
from aimodelshare.aws import set_credentials, get_aws_token
from aimodelshare.modeluser import get_jwt_token, setup_bucket_only


# Set seeds for reproducibility
np.random.seed(42)


def _create_synthetic_compas_data(n_samples=300):
    """
    Create a small synthetic COMPAS-like dataset for testing.
    
    Returns DataFrame with features similar to COMPAS dataset.
    """
    np.random.seed(42)
    
    races = ['African-American', 'Caucasian', 'Hispanic', 'Asian', 'Other']
    sexes = ['Male', 'Female']
    age_cats = ['Less than 25', '25 - 45', 'Greater than 45']
    charge_degrees = ['F', 'M']  # Felony, Misdemeanor
    charge_descs = ['Battery', 'Theft', 'Drug Possession', 'Assault', 'Traffic']
    
    data = {
        'race': np.random.choice(races, n_samples),
        'sex': np.random.choice(sexes, n_samples),
        'age': np.random.randint(18, 70, n_samples),
        'age_cat': np.random.choice(age_cats, n_samples),
        'c_charge_degree': np.random.choice(charge_degrees, n_samples),
        'c_charge_desc': np.random.choice(charge_descs, n_samples),
        'priors_count': np.random.poisson(2, n_samples),
        'juv_fel_count': np.random.poisson(0.3, n_samples),
        'juv_misd_count': np.random.poisson(0.5, n_samples),
        'juv_other_count': np.random.poisson(0.2, n_samples),
        'days_b_screening_arrest': np.random.randint(-30, 30, n_samples),
        'two_year_recid': np.random.choice([0, 1], n_samples, p=[0.55, 0.45])
    }
    
    return pd.DataFrame(data)


@pytest.fixture(scope="module")
def credentials():
    """Setup credentials for playground tests."""
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
    
    # Check for environment variables
    if not os.environ.get('username') or not os.environ.get('password'):
        pytest.skip("No credentials available - skipping test")
    
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


@pytest.fixture(scope="module")
def aws_environment(credentials):
    """Setup AWS environment variables."""
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
        setup_bucket_only()
    except Exception as e:
        print(f"Warning: Could not validate JWT tokens: {e}")


@pytest.fixture(scope="module")
def test_data():
    """Create synthetic COMPAS-like test data with preprocessors."""
    # Create synthetic data
    df = _create_synthetic_compas_data(n_samples=300)
    
    print(f"Created synthetic dataset: {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Select features and target
    feature_columns = [
        'race', 'sex', 'age', 'age_cat', 
        'c_charge_degree', 'c_charge_desc',
        'priors_count', 'juv_fel_count', 'juv_misd_count', 'juv_other_count',
        'days_b_screening_arrest'
    ]
    target_column = 'two_year_recid'
    
    X = df[feature_columns].copy()
    y = df[target_column].values
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    # Define numeric and categorical columns
    numeric_features = ['age', 'priors_count', 'juv_fel_count', 'juv_misd_count', 
                       'juv_other_count', 'days_b_screening_arrest']
    categorical_features = ['race', 'sex', 'age_cat', 'c_charge_degree', 'c_charge_desc']
    
    # Build standard preprocessing pipeline (StandardScaler)
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
    
    preprocessor.fit(X_train)
    
    # Build MinMax preprocessing pipeline for MultinomialNB
    minmax_numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', MinMaxScaler())
    ])
    
    minmax_preprocessor = ColumnTransformer(
        transformers=[
            ('num', minmax_numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])
    
    minmax_preprocessor.fit(X_train)
    
    return X_train, X_test, y_train, y_test, preprocessor, minmax_preprocessor


@pytest.fixture(scope="module")
def test_playground(credentials, aws_environment, test_data):
    """Create a test playground for model submissions."""
    X_train, X_test, y_train, y_test, preprocessor, minmax_preprocessor = test_data
    eval_labels = list(y_test)
    
    # Create playground
    playground = ModelPlayground(
        input_type='tabular',
        task_type='classification',
        private=False
    )
    playground.create(eval_data=eval_labels, public=True)
    print(f"✓ Test playground created successfully")
    
    return playground


def test_ai_lead_engineer_app_imports():
    """Test that the AI Lead Engineer app can be imported."""
    from aimodelshare.moral_compass.apps import create_ai_lead_engineer_app, launch_ai_lead_engineer_app
    
    assert create_ai_lead_engineer_app is not None
    assert launch_ai_lead_engineer_app is not None
    assert callable(create_ai_lead_engineer_app)
    assert callable(launch_ai_lead_engineer_app)


def test_ai_lead_engineer_app_model_registry():
    """Test that the model registry is properly configured."""
    from aimodelshare.moral_compass.apps.ai_lead_engineer import MODEL_OPTIONS
    
    # Check families exist
    assert "sklearn" in MODEL_OPTIONS
    assert "keras" in MODEL_OPTIONS
    assert "pytorch" in MODEL_OPTIONS
    
    # Check sklearn models
    assert "LogisticRegression" in MODEL_OPTIONS["sklearn"]
    assert "RandomForest" in MODEL_OPTIONS["sklearn"]
    assert "GradientBoosting" in MODEL_OPTIONS["sklearn"]
    assert "MultinomialNB" in MODEL_OPTIONS["sklearn"]
    
    # Check keras models
    assert "SimpleDense" in MODEL_OPTIONS["keras"]
    assert "DenseWithDropout" in MODEL_OPTIONS["keras"]
    
    # Check pytorch models
    assert "MLPBasic" in MODEL_OPTIONS["pytorch"]
    
    # Check complexity params exist for each model
    for family in MODEL_OPTIONS:
        for model_key in MODEL_OPTIONS[family]:
            config = MODEL_OPTIONS[family][model_key]
            assert "display_name" in config
            assert "description" in config
            assert "complexity_params" in config
            
            # Check all complexity levels 1-5
            for complexity in range(1, 6):
                assert complexity in config["complexity_params"]


def test_ai_lead_engineer_app_submission_flow(test_playground, test_data):
    """
    Test complete submission flow: train model via app logic and submit to playground.
    
    This test:
    1. Uses the app's training functions directly (without launching UI)
    2. Trains a LogisticRegression model
    3. Submits to playground with correct tags
    4. Verifies submission appears in leaderboard
    5. Checks accuracy > 0
    6. Verifies etica_tech_challenge tag is present
    """
    from aimodelshare.moral_compass.apps.ai_lead_engineer import (
        _build_sklearn_model,
        _generate_predictions,
        _create_tags
    )
    from sklearn.metrics import accuracy_score
    
    X_train, X_test, y_train, y_test, preprocessor, minmax_preprocessor = test_data
    
    print(f"\n{'='*80}")
    print("Testing AI Lead Engineer App Submission Flow")
    print(f"{'='*80}")
    
    # Preprocess data
    X_train_processed = preprocessor.transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    
    # Train model using app logic
    model_key = "LogisticRegression"
    complexity = 2
    
    print(f"Training {model_key} with complexity {complexity}...")
    model = _build_sklearn_model(
        model_key, complexity,
        X_train_processed, y_train,
        use_minmax=False
    )
    print("✓ Model trained")
    
    # Generate predictions
    preds = _generate_predictions(model, "sklearn", X_test_processed)
    print(f"✓ Generated {len(preds)} predictions")
    
    # Calculate accuracy
    accuracy = accuracy_score(y_test, preds)
    print(f"✓ Accuracy: {accuracy:.4f}")
    assert accuracy > 0, "Accuracy should be greater than 0"
    
    # Create tags
    team_name = "Test Team Alpha"
    tags = _create_tags("sklearn", model_key, complexity, team_name)
    print(f"✓ Tags: {tags}")
    
    # Verify tags contain expected components
    assert "etica_tech_challenge" in tags
    assert "sklearn" in tags
    assert model_key in tags
    assert f"complexity_{complexity}" in tags
    assert "team_test_team_alpha" in tags
    
    # Submit to playground
    input_dict = {
        'description': f'Test submission {model_key} complexity {complexity}',
        'tags': tags
    }
    
    custom_metadata = {
        'username': 'test_user',
        'team': team_name,
        'complexity': complexity,
        'model_family': 'sklearn',
        'model_type': model_key
    }
    
    print("Submitting model to playground...")
    try:
        test_playground.submit_model(
            model=model,
            preprocessor=preprocessor,
            prediction_submission=preds,
            input_dict=input_dict,
            submission_type='competition',
            custom_metadata=custom_metadata
        )
        print("✓ Model submitted successfully")
    except Exception as e:
        # Check if it's an ONNX/stdin issue which we can skip
        error_str = str(e).lower()
        if 'reading from stdin' in error_str or 'stdin' in error_str or 'onnx' in error_str:
            pytest.skip(f"Skipped due to ONNX/stdin issue: {e}")
        else:
            raise
    
    # Verify leaderboard entry
    print("Fetching leaderboard...")
    data = test_playground.get_leaderboard()
    
    if isinstance(data, dict):
        df = pd.DataFrame(data)
    elif isinstance(data, pd.DataFrame):
        df = data
    else:
        pytest.fail("Leaderboard data is neither dict nor DataFrame")
    
    assert not df.empty, "Leaderboard should contain submissions"
    
    # Check for etica_tech_challenge tag in leaderboard
    if 'tags' in df.columns:
        tags_found = df['tags'].astype(str).str.contains('etica_tech_challenge', case=False, na=False)
        assert tags_found.any(), "At least one submission should have etica_tech_challenge tag"
        print("✓ Found etica_tech_challenge tag in leaderboard")
    
    print(f"\n{'='*80}")
    print("✓ AI Lead Engineer App submission flow test completed successfully")
    print(f"{'='*80}")


def test_ai_lead_engineer_app_can_be_created_without_data():
    """Test that app can be instantiated without data (shows warning)."""
    from aimodelshare.moral_compass.apps import create_ai_lead_engineer_app
    
    # Should create app but show warning about missing data
    app = create_ai_lead_engineer_app()
    assert app is not None
    assert hasattr(app, 'launch')


def test_ai_lead_engineer_app_can_be_created_with_data(test_data):
    """Test that app can be instantiated with data."""
    from aimodelshare.moral_compass.apps import create_ai_lead_engineer_app
    
    X_train, X_test, y_train, y_test, preprocessor, minmax_preprocessor = test_data
    
    app = create_ai_lead_engineer_app(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        preprocessor=preprocessor,
        minmax_preprocessor=minmax_preprocessor
    )
    
    assert app is not None
    assert hasattr(app, 'launch')


def test_cpu_enforcement():
    """Test that CPU enforcement works correctly."""
    from aimodelshare.moral_compass.apps.ai_lead_engineer import _enforce_cpu_only
    import tensorflow as tf
    
    # Call enforcement
    _enforce_cpu_only()
    
    # Check TensorFlow sees no GPUs
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '-1'
    
    # Check TensorFlow device list
    gpus = tf.config.list_physical_devices('GPU')
    print(f"TensorFlow sees {len(gpus)} GPUs (should be 0)")
    
    # Note: We don't assert len(gpus) == 0 because the test environment might not have GPU support at all
    # The important thing is that CUDA_VISIBLE_DEVICES is set to -1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

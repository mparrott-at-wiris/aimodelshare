#!/usr/bin/env python3
"""
Integration test for AI Lead Engineer Gradio app with playground submission.

Tests the end-to-end flow:
1. Create synthetic COMPAS-like dataset
2. Build standard & MinMax preprocessors (object + callable function forms)
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
    """
    np.random.seed(42)
    races = ['African-American', 'Caucasian', 'Hispanic', 'Asian', 'Other']
    sexes = ['Male', 'Female']
    age_cats = ['Less than 25', '25 - 45', 'Greater than 45']
    charge_degrees = ['F', 'M']
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


def _fallback_region():
    """
    Provide a safe AWS region fallback if missing or blank.
    Prevents blank ECR endpoints (https://api.ecr..amazonaws.com).
    """
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or ''
    if not region.strip():
        region = 'us-east-1'
    return region


@pytest.fixture(scope="module")
def credentials():
    """Setup credentials for playground tests."""
    for candidate in ["../../../credentials.txt", "../../credentials.txt"]:
        try:
            set_credentials(credential_file=candidate, type="deploy_model")
            return
        except Exception:
            pass

    if not os.environ.get('username') or not os.environ.get('password'):
        pytest.skip("Skipping: username/password not available in environment")

    inputs = [
        os.environ.get('username'),
        os.environ.get('password'),
        os.environ.get('AWS_ACCESS_KEY_ID', ''),
        os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
        _fallback_region()
    ]

    with patch("getpass.getpass", side_effect=inputs):
        from aimodelshare.aws import configure_credentials
        configure_credentials()

    set_credentials(credential_file="credentials.txt", type="deploy_model")
    if os.path.exists("credentials.txt"):
        os.remove("credentials.txt")


@pytest.fixture(scope="module")
def aws_environment(credentials):
    """Setup AWS environment variables."""
    region = _fallback_region()
    os.environ['AWS_REGION'] = region
    os.environ['AWS_DEFAULT_REGION'] = region
    os.environ['AWS_REGION_AIMS'] = region

    if not os.environ.get('AWS_ACCESS_KEY_ID') or not os.environ.get('AWS_SECRET_ACCESS_KEY'):
        pytest.skip("Skipping: AWS credentials not available.")

    try:
        os.environ['AWS_TOKEN'] = get_aws_token()
        os.environ['AWS_ACCESS_KEY_ID_AIMS'] = os.environ.get('AWS_ACCESS_KEY_ID')
        os.environ['AWS_SECRET_ACCESS_KEY_AIMS'] = os.environ.get('AWS_SECRET_ACCESS_KEY')
    except Exception as e:
        print(f"Warning: Could not set AWS environment: {e}")

    try:
        get_jwt_token(os.environ.get('username'), os.environ.get('password'))
        setup_bucket_only()
    except Exception as e:
        print(f"Warning: Could not validate JWT tokens: {e}")


@pytest.fixture(scope="module")
def test_data():
    """
    Create synthetic data and build preprocessors (objects + callable wrappers).
    Returns:
        X_train, X_test, y_train, y_test,
        preprocessor_obj, preprocessor_func,
        minmax_preprocessor_obj, minmax_preprocessor_func
    """
    df = _create_synthetic_compas_data(n_samples=300)
    print(f"Created synthetic dataset: {df.shape[0]} rows, {df.shape[1]} columns")

    feature_columns = [
        'race', 'sex', 'age', 'age_cat',
        'c_charge_degree', 'c_charge_desc',
        'priors_count', 'juv_fel_count', 'juv_misd_count', 'juv_other_count',
        'days_b_screening_arrest'
    ]
    target_column = 'two_year_recid'

    X = df[feature_columns].copy()
    y = df[target_column].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    numeric_features = ['age', 'priors_count', 'juv_fel_count', 'juv_misd_count',
                        'juv_other_count', 'days_b_screening_arrest']
    categorical_features = ['race', 'sex', 'age_cat', 'c_charge_degree', 'c_charge_desc']

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

    def preprocessor_func(data):
        return preprocessor.transform(data)

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

    def minmax_preprocessor_func(data):
        return minmax_preprocessor.transform(data)

    return (X_train, X_test, y_train, y_test,
            preprocessor, preprocessor_func,
            minmax_preprocessor, minmax_preprocessor_func)


@pytest.fixture(scope="module")
def test_playground(credentials, aws_environment, test_data):
    """
    Create a test playground for model submissions (private=True like COMPAS test).
    """
    region = _fallback_region()
    if not region:
        pytest.skip("Skipping playground creation: AWS region unresolved.")

    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func, minmax_preprocessor, minmax_preprocessor_func = test_data
    eval_labels = list(y_test)

    playground = ModelPlayground(
        input_type='tabular',
        task_type='classification',
        private=True
    )

    try:
        playground.create(eval_data=eval_labels, public=True)
        print("✓ Test playground created successfully")
    except ValueError as e:
        if "Invalid endpoint" in str(e):
            pytest.skip(f"Skipping: Invalid AWS endpoint (missing region). Details: {e}")
        raise
    except Exception as e:
        raise

    return playground


def test_ai_lead_engineer_app_imports():
    """Test that the AI Lead Engineer app can be imported."""
    from aimodelshare.moral_compass.apps import create_ai_lead_engineer_app, launch_ai_lead_engineer_app
    assert callable(create_ai_lead_engineer_app)
    assert callable(launch_ai_lead_engineer_app)


def test_ai_lead_engineer_app_model_registry():
    """Test that the model registry is properly configured."""
    from aimodelshare.moral_compass.apps.ai_lead_engineer import MODEL_OPTIONS

    assert "sklearn" in MODEL_OPTIONS
    assert "keras" in MODEL_OPTIONS
    assert "pytorch" in MODEL_OPTIONS

    assert "LogisticRegression" in MODEL_OPTIONS["sklearn"]
    assert "RandomForest" in MODEL_OPTIONS["sklearn"]
    assert "GradientBoosting" in MODEL_OPTIONS["sklearn"]
    assert "MultinomialNB" in MODEL_OPTIONS["sklearn"]

    assert "SimpleDense" in MODEL_OPTIONS["keras"]
    assert "DenseWithDropout" in MODEL_OPTIONS["keras"]

    assert "MLPBasic" in MODEL_OPTIONS["pytorch"]

    for family in MODEL_OPTIONS:
        for model_key in MODEL_OPTIONS[family]:
            cfg = MODEL_OPTIONS[family][model_key]
            assert "display_name" in cfg
            assert "description" in cfg
            assert "complexity_params" in cfg
            for complexity in range(1, 6):
                assert complexity in cfg["complexity_params"]


def test_ai_lead_engineer_app_submission_flow(test_playground, test_data):
    """
    Full submission flow using callable preprocessors for consistency with COMPAS tests.
    """
    from aimodelshare.moral_compass.apps.ai_lead_engineer import (
        _build_sklearn_model,
        _generate_predictions,
        _create_tags
    )
    from sklearn.metrics import accuracy_score

    if test_playground is None:
        pytest.skip("Playground fixture unavailable (likely skipped due to missing AWS credentials).")

    (X_train, X_test, y_train, y_test,
     preprocessor, preprocessor_func,
     minmax_preprocessor, minmax_preprocessor_func) = test_data

    print(f"\n{'='*80}")
    print("Testing AI Lead Engineer App Submission Flow")
    print(f"{'='*80}")

    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)

    model_key = "LogisticRegression"
    complexity = 2
    print(f"Training {model_key} with complexity {complexity}...")
    model = _build_sklearn_model(
        model_key, complexity,
        X_train_processed, y_train,
        use_minmax=False
    )
    print("✓ Model trained")

    preds = _generate_predictions(model, "sklearn", X_test_processed)
    print(f"✓ Generated {len(preds)} predictions")

    accuracy = accuracy_score(y_test, preds)
    print(f"✓ Accuracy: {accuracy:.4f}")
    assert accuracy > 0

    team_name = "Test Team Alpha"
    tags = _create_tags("sklearn", model_key, complexity, team_name)
    print(f"✓ Tags: {tags}")

    assert "etica_tech_challenge" in tags
    assert "sklearn" in tags
    assert model_key in tags
    assert f"complexity_{complexity}" in tags
    assert "team_test_team_alpha" in tags

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
            preprocessor=preprocessor,  # pass transformer object (mirrors COMPAS test)
            prediction_submission=preds,
            input_dict=input_dict,
            submission_type='competition',
            custom_metadata=custom_metadata
        )
        print("✓ Model submitted successfully")
    except Exception as e:
        err = str(e).lower()
        if any(x in err for x in ['reading from stdin', 'stdin', 'onnx']):
            pytest.skip(f"Skipped due to ONNX/stdin issue: {e}")
        elif 'invalid endpoint' in err:
            pytest.skip(f"Skipped due to invalid AWS endpoint: {e}")
        else:
            raise

    print("Fetching leaderboard...")
    data = test_playground.get_leaderboard()

    if isinstance(data, dict):
        df = pd.DataFrame(data)
    elif isinstance(data, pd.DataFrame):
        df = data
    else:
        pytest.fail("Leaderboard data is neither dict nor DataFrame")

    assert not df.empty, "Leaderboard should contain submissions"

    if 'tags' in df.columns:
        tags_found = df['tags'].astype(str).str.contains('etica_tech_challenge', case=False, na=False)
        assert tags_found.any(), "At least one submission should have etica_tech_challenge tag"
        print("✓ Found etica_tech_challenge tag in leaderboard")

    print(f"\n{'='*80}")
    print("✓ AI Lead Engineer App submission flow test completed successfully")
    print(f"{'='*80}")


def test_ai_lead_engineer_app_can_be_created_without_data():
    """Test that app can be instantiated without data."""
    from aimodelshare.moral_compass.apps import create_ai_lead_engineer_app
    app = create_ai_lead_engineer_app()
    assert app is not None
    assert hasattr(app, 'launch')


def test_ai_lead_engineer_app_can_be_created_with_data(test_data):
    """Test that app can be instantiated with provided data & preprocessors."""
    from aimodelshare.moral_compass.apps import create_ai_lead_engineer_app

    (X_train, X_test, y_train, y_test,
     preprocessor, preprocessor_func,
     minmax_preprocessor, minmax_preprocessor_func) = test_data

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

    _enforce_cpu_only()
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '-1'
    gpus = tf.config.list_physical_devices('GPU')
    print(f"TensorFlow sees {len(gpus)} GPUs (should be 0)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

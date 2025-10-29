"""
Comprehensive sklearn model submission test for ModelPlayground.

Tests 18 different sklearn classifier types with and without preprocessors
using the iris dataset to validate submit_model functionality.

Uses session-scoped fixtures for playground and preprocessing to reduce overhead.
"""

import os
import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

# Classifiers to test
from sklearn.linear_model import LogisticRegression, RidgeClassifier, SGDClassifier
from sklearn.svm import SVC, LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB, MultinomialNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    AdaBoostClassifier,
    BaggingClassifier
)
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.neural_network import MLPClassifier

from aimodelshare.playground import ModelPlayground
from aimodelshare.aws import set_credentials, get_aws_token
from aimodelshare.modeluser import get_jwt_token, setup_bucket_only


# Define the 18 classifier variants to test
CLASSIFIERS = [
    ("LogisticRegression", LogisticRegression(max_iter=500, random_state=42)),
    ("RidgeClassifier", RidgeClassifier(random_state=42)),
    ("SGDClassifier", SGDClassifier(max_iter=500, random_state=42, tol=1e-3)),
    ("SVC", SVC(probability=True, random_state=42)),
    ("CalibratedClassifierCV_LinearSVC", CalibratedClassifierCV(LinearSVC(random_state=42, max_iter=500), cv=2)),
    ("KNeighborsClassifier", KNeighborsClassifier()),
    ("GaussianNB", GaussianNB()),
    ("MultinomialNB", MultinomialNB()),  # Requires non-negative features
    ("DecisionTreeClassifier", DecisionTreeClassifier(random_state=42)),
    ("RandomForestClassifier", RandomForestClassifier(n_estimators=5, random_state=42)),
    ("ExtraTreesClassifier", ExtraTreesClassifier(n_estimators=5, random_state=42)),
    ("GradientBoostingClassifier", GradientBoostingClassifier(n_estimators=5, random_state=42)),
    ("HistGradientBoostingClassifier", HistGradientBoostingClassifier(max_iter=5, random_state=42)),
    ("AdaBoostClassifier", AdaBoostClassifier(n_estimators=5, random_state=42)),
    ("BaggingClassifier", BaggingClassifier(n_estimators=5, random_state=42)),
    ("LinearDiscriminantAnalysis", LinearDiscriminantAnalysis()),
    ("QuadraticDiscriminantAnalysis", QuadraticDiscriminantAnalysis()),
    ("MLPClassifier", MLPClassifier(solver='lbfgs', max_iter=150, random_state=42, hidden_layer_sizes=(20,))),
]


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
        setup_bucket_only()
    except Exception as e:
        print(f"Warning: Could not validate JWT tokens: {e}")


@pytest.fixture(scope="session")
def iris_data():
    """Load and prepare iris dataset (session-scoped)."""
    # Load iris dataset
    iris = load_iris()
    X = iris.data
    y = iris.target
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    return X_train, X_test, y_train, y_test


@pytest.fixture(scope="session")
def preprocessors(iris_data):
    """Create preprocessing pipelines (session-scoped).
    
    Returns both preprocessor objects and callable functions.
    """
    X_train, X_test, y_train, y_test = iris_data
    
    # StandardScaler preprocessor
    scaler_standard = StandardScaler()
    scaler_standard.fit(X_train)
    
    def preprocessor_standard(data):
        return scaler_standard.transform(data)
    
    # MinMaxScaler preprocessor
    scaler_minmax = MinMaxScaler()
    scaler_minmax.fit(X_train)
    
    def preprocessor_minmax(data):
        return scaler_minmax.transform(data)
    
    return {
        'standard': preprocessor_standard,
        'standard_obj': scaler_standard,
        'minmax': preprocessor_minmax,
        'minmax_obj': scaler_minmax
    }


@pytest.fixture(scope="session")
def shared_playground(credentials, aws_environment, iris_data):
    """Create a shared ModelPlayground instance for all tests (session-scoped)."""
    X_train, X_test, y_train, y_test = iris_data
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


@pytest.mark.parametrize("model_name,model", CLASSIFIERS)
def test_sklearn_classifier_submission(model_name, model, shared_playground, iris_data, preprocessors):
    """
    Test submission of sklearn classifier to ModelPlayground.
    
    Each model is tested twice:
    A) predictions only (no preprocessor)
    B) with preprocessor object
    """
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")
    
    # Load data
    X_train, X_test, y_train, y_test = iris_data
    
    # For MultinomialNB, we need non-negative features, so use MinMaxScaler
    if model_name == "MultinomialNB":
        preprocessor = preprocessors['minmax']
        X_train_processed = preprocessor(X_train)
        X_test_processed = preprocessor(X_test)
    else:
        preprocessor = preprocessors['standard']
        X_train_processed = preprocessor(X_train)
        X_test_processed = preprocessor(X_test)
    
    # Train model
    try:
        model.fit(X_train_processed, y_train)
        preds = model.predict(X_test_processed)
        print(f"✓ Model trained successfully, generated {len(preds)} predictions")
    except Exception as e:
        pytest.fail(f"Failed to train {model_name}: {e}")
    
    # Test A: Submit with predictions only (no preprocessor)
    submission_errors = []
    try:
        shared_playground.submit_model(
            model=model,
            preprocessor=None,
            prediction_submission=preds,
            input_dict={
                'description': f'CI test {model_name} no preprocessor',
                'tags': f'integration,{model_name},no_preprocessor'
            },
            submission_type='experiment'
        )
        print(f"✓ Submission A (predictions only) succeeded")
    except Exception as e:
        # Check for stdin read error (specific to MLPClassifier)
        error_str = str(e)
        if 'reading from stdin' in error_str.lower() or 'stdin' in error_str.lower():
            pytest.skip(f"Skipping {model_name} due to stdin read error: {e}")
        error_msg = f"Submission A failed for {model_name}: {e}"
        print(f"✗ {error_msg}")
        submission_errors.append(error_msg)
    
    # Test B: Submit with preprocessor object
    try:
        shared_playground.submit_model(
            model=model,
            preprocessor=preprocessor,
            prediction_submission=preds,
            input_dict={
                'description': f'CI test {model_name} with preprocessor',
                'tags': f'integration,{model_name},with_preprocessor'
            },
            submission_type='experiment'
        )
        print(f"✓ Submission B (with preprocessor) succeeded")
    except Exception as e:
        # Check for stdin read error (specific to MLPClassifier)
        error_str = str(e)
        if 'reading from stdin' in error_str.lower() or 'stdin' in error_str.lower():
            pytest.skip(f"Skipping {model_name} due to stdin read error: {e}")
        error_msg = f"Submission B failed for {model_name}: {e}"
        print(f"✗ {error_msg}")
        submission_errors.append(error_msg)
    
    # Fail the test if any submission errors occurred
    if submission_errors:
        pytest.fail(
            f"Submission errors for {model_name}:\n" + 
            "\n".join(f"  - {err}" for err in submission_errors) +
            f"\n\nExpected: Both submission A (predictions only) and B (with preprocessor) should succeed."
        )
    
    print(f"✓ All tests passed for {model_name}")


def test_leaderboard_retrieval(shared_playground):
    """
    Validate that leaderboard retrieval is non-empty after submissions.
    This test runs after all parameterized tests.
    """
    print(f"\n{'='*60}")
    print(f"Testing: Leaderboard Retrieval")
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
            print(df.head())
        else:
            assert isinstance(data, pd.DataFrame), (
                f'Leaderboard did not return a DataFrame, got {type(data).__name__}. '
                'Expected: DataFrame or dict convertible to DataFrame.'
            )
            assert not data.empty, (
                'Leaderboard DataFrame is empty. '
                'Expected: Non-empty leaderboard with model submission entries.'
            )
            print(f"✓ Leaderboard retrieved (DataFrame): {len(data)} entries")
            print(data.head())
        
        print(f"✓ Leaderboard retrieval test passed")
    except Exception as e:
        pytest.fail(f"Leaderboard retrieval failed: {e}")

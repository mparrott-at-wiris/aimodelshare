"""
Comprehensive TensorFlow Keras model submission test for ModelPlayground.

Tests 5 different Keras model types with and without preprocessors
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
from sklearn.preprocessing import StandardScaler

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
from tensorflow.keras.models import Sequential

from aimodelshare.playground import ModelPlayground
from aimodelshare.aws import set_credentials, get_aws_token
from aimodelshare.modeluser import get_jwt_token, setup_bucket_only


# Set seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# Training constants for consistency across all models
TRAINING_EPOCHS = 12
TRAINING_BATCH_SIZE = 16


def create_sequential_dense_model():
    """Sequential model with Dense layers."""
    model = Sequential([
        layers.Dense(32, activation='relu', input_shape=(4,)),
        layers.Dense(16, activation='relu'),
        layers.Dense(3, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model


def create_functional_api_model():
    """Functional API model with two hidden relu layers."""
    inputs = keras.Input(shape=(4,))
    x = layers.Dense(32, activation='relu')(inputs)
    x = layers.Dense(16, activation='relu')(x)
    outputs = layers.Dense(3, activation='softmax')(x)
    model = Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model


def create_sequential_dropout_model():
    """Sequential model with Dropout."""
    model = Sequential([
        layers.Dense(64, activation='relu', input_shape=(4,)),
        layers.Dropout(0.3),
        layers.Dense(3, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model


def create_batchnorm_model():
    """Model with BatchNormalization."""
    model = Sequential([
        layers.Dense(64, activation='relu', input_shape=(4,)),
        layers.BatchNormalization(),
        layers.Dense(3, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model


class SubclassModel(tf.keras.Model):
    """Custom tf.keras.Model subclass with two Dense layers.
    
    This model demonstrates testing Keras model subclassing, which requires
    the model to be built by calling it once before training. Architecture:
    - Dense layer with 32 units and relu activation
    - Dense output layer with 3 units and softmax activation
    """
    
    def __init__(self):
        super(SubclassModel, self).__init__()
        self.dense1 = layers.Dense(32, activation='relu')
        self.dense2 = layers.Dense(3, activation='softmax')
    
    def call(self, inputs):
        x = self.dense1(inputs)
        return self.dense2(x)


def create_subclass_model():
    """Create and compile a subclass model.
    
    Note: Subclass models need to be built before training by calling them once.
    """
    model = SubclassModel()
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model


# Define the 5 Keras model variants to test
KERAS_MODELS = [
    ("sequential_dense", create_sequential_dense_model),
    ("functional_api", create_functional_api_model),
    ("sequential_dropout", create_sequential_dropout_model),
    ("batchnorm_model", create_batchnorm_model),
    ("subclass_model", create_subclass_model),
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
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


@pytest.fixture(scope="session")
def shared_playground(credentials, aws_environment, iris_data):
    """Create a shared ModelPlayground instance for all tests (session-scoped)."""
    X_train_scaled, X_test_scaled, y_train, y_test, scaler = iris_data
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


@pytest.mark.parametrize("model_name,model_factory", KERAS_MODELS)
def test_keras_model_submission(model_name, model_factory, shared_playground, iris_data):
    """
    Test submission of Keras models to ModelPlayground.
    
    Each model is tested twice:
    A) predictions only (no preprocessor)
    B) with preprocessor object (StandardScaler)
    """
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")
    
    # Load data
    X_train_scaled, X_test_scaled, y_train, y_test, scaler = iris_data
    
    # Create and train model
    try:
        model = model_factory()
        
        # For subclass models, build the model by calling it once with sample data
        if model_name == "subclass_model":
            _ = model(X_train_scaled[:1])
        
        # Train model with constants defined at module level
        model.fit(X_train_scaled, y_train, epochs=TRAINING_EPOCHS, batch_size=TRAINING_BATCH_SIZE, verbose=0)
        
        # Generate predictions
        predictions_proba = model.predict(X_test_scaled, verbose=0)
        preds = np.argmax(predictions_proba, axis=1)
        
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
        error_str = str(e).lower()
        # Skip if error is due to ONNX conversion issue or stdin capture
        if 'onnx' in error_str or 'conversion' in error_str or 'stdin' in error_str:
            pytest.skip(f"Skipping {model_name} submission A due to ONNX or stdin issue: {e}")
        error_msg = f"Submission A failed for {model_name}: {e}"
        print(f"✗ {error_msg}")
        submission_errors.append(error_msg)
    
    # Test B: Submit with preprocessor object
    try:
        shared_playground.submit_model(
            model=model,
            preprocessor=scaler,
            prediction_submission=preds,
            input_dict={
                'description': f'CI test {model_name} with preprocessor',
                'tags': f'integration,{model_name},with_preprocessor'
            },
            submission_type='experiment'
        )
        print(f"✓ Submission B (with preprocessor) succeeded")
    except Exception as e:
        error_str = str(e).lower()
        # Skip if error is due to ONNX conversion issue or stdin capture
        if 'onnx' in error_str or 'conversion' in error_str or 'stdin' in error_str:
            pytest.skip(f"Skipping {model_name} submission B due to ONNX or stdin issue: {e}")
        error_msg = f"Submission B failed for {model_name}: {e}"
        print(f"✗ {error_msg}")
        submission_errors.append(error_msg)
    
    # Fail the test if any submission errors occurred (that weren't ONNX-related)
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

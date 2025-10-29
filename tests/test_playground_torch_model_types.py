"""
Comprehensive PyTorch model submission test for ModelPlayground.

Tests 4 different PyTorch model types with and without preprocessors
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

import torch
import torch.nn as nn
import torch.nn.functional as F

from aimodelshare.playground import ModelPlayground
from aimodelshare.aws import set_credentials, get_aws_token
from aimodelshare.modeluser import get_jwt_token, setup_bucket_only


# Set seeds for reproducibility
np.random.seed(42)
torch.manual_seed(42)

# Training constants for consistency across all models
TRAINING_EPOCHS = 10
TRAINING_BATCH_SIZE = 16
LEARNING_RATE = 0.01


class BasicMLP(nn.Module):
    """Basic Multi-Layer Perceptron with two hidden layers."""
    
    def __init__(self, input_size=4, hidden_size=32, num_classes=3):
        super(BasicMLP, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 16)
        self.fc3 = nn.Linear(16, num_classes)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


class MLPWithDropout(nn.Module):
    """MLP with Dropout layers for regularization."""
    
    def __init__(self, input_size=4, hidden_size=64, num_classes=3, dropout_rate=0.3):
        super(MLPWithDropout, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.dropout1 = nn.Dropout(dropout_rate)
        self.fc2 = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.dropout1(x)
        x = self.fc2(x)
        return x


class MLPWithBatchNorm(nn.Module):
    """MLP with Batch Normalization layers."""
    
    def __init__(self, input_size=4, hidden_size=64, num_classes=3):
        super(MLPWithBatchNorm, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.bn1 = nn.BatchNorm1d(hidden_size)
        self.fc2 = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.fc2(x)
        return x


class CustomSubclassModel(nn.Module):
    """Custom PyTorch model demonstrating subclass pattern.
    
    This model uses a simple multi-layer architecture to demonstrate
    handling of custom model architectures.
    """
    
    def __init__(self, input_size=4, hidden_size=32, num_classes=3):
        super(CustomSubclassModel, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def train_torch_model(model, X_train, y_train, epochs=TRAINING_EPOCHS, batch_size=TRAINING_BATCH_SIZE, lr=LEARNING_RATE):
    """Train a PyTorch model on the given data.
    
    Args:
        model: PyTorch model to train
        X_train: Training features (numpy array)
        y_train: Training labels (numpy array)
        epochs: Number of training epochs
        batch_size: Batch size for training
        lr: Learning rate
    
    Returns:
        Trained model
    """
    # Convert to tensors
    X_tensor = torch.FloatTensor(X_train)
    y_tensor = torch.LongTensor(y_train)
    
    # Create dataset and dataloader
    dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # Setup optimizer and loss
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    
    # Training loop
    model.train()
    for epoch in range(epochs):
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
    
    return model


def predict_torch_model(model, X_test):
    """Generate predictions from a PyTorch model.
    
    Args:
        model: Trained PyTorch model
        X_test: Test features (numpy array)
    
    Returns:
        Predictions as numpy array
    """
    model.eval()
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_test)
        outputs = model(X_tensor)
        _, predictions = torch.max(outputs, 1)
    return predictions.numpy()


# Define the 4 PyTorch model variants to test
TORCH_MODELS = [
    ("basic_mlp", BasicMLP),
    ("mlp_dropout", MLPWithDropout),
    ("mlp_batchnorm", MLPWithBatchNorm),
    ("custom_subclass", CustomSubclassModel),
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


@pytest.mark.parametrize("model_name,model_class", TORCH_MODELS)
def test_torch_model_submission(model_name, model_class, shared_playground, iris_data):
    """
    Test submission of PyTorch models to ModelPlayground.
    
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
        model = model_class()
        model = train_torch_model(model, X_train_scaled, y_train)
        
        # Create dummy input for ONNX conversion (1 sample with input_dim features)
        # Using randn (random normal) instead of zeros for better model testing:
        # - Batch normalization layers may not initialize running stats properly with all-zero inputs
        # - Random inputs better exercise activation functions and dropout layers
        # - Provides more realistic test of model behavior during ONNX conversion
        input_dim = X_train_scaled.shape[1]
        dummy_input = torch.randn((1, input_dim), dtype=torch.float32)
        
        # Perform a lightweight forward pass to ensure module parameters are initialized
        model.eval()
        with torch.no_grad():
            _ = model(dummy_input)
        
        # Generate predictions
        preds = predict_torch_model(model, X_test_scaled)
        
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
            submission_type='experiment',
            model_input=dummy_input
        )
        print(f"✓ Submission A (predictions only) succeeded")
    except Exception as e:
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
            submission_type='experiment',
            model_input=dummy_input
        )
        print(f"✓ Submission B (with preprocessor) succeeded")
    except Exception as e:
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

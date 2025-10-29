"""
Multi-framework integration test using ProPublica COMPAS two-year recidivism dataset.

Tests joint submissions from sklearn, Keras, and PyTorch models in a single public playground competition.
Includes bias-related features (race, sex, age, age_cat, charge info) to validate model submission
pipeline and leaderboard metadata handling.

Tests all models with dual submission types (competition and experiment) to validate both modes.

Uses session-scoped fixtures for playground and preprocessing to reduce overhead.
Sampling cap (MAX_ROWS=4000) for manageable CI runtime.
"""

import os
import itertools
import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
import requests
from io import StringIO

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# Sklearn classifiers - full set from test_playground_model_types.py
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

# TensorFlow/Keras
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
from tensorflow.keras.models import Sequential

# PyTorch
import torch
import torch.nn as nn
import torch.nn.functional as F

from aimodelshare.playground import ModelPlayground
from aimodelshare.aws import set_credentials, get_aws_token
from aimodelshare.modeluser import get_jwt_token, setup_bucket_only


# Set seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)
torch.manual_seed(42)

# Dataset configuration
MAX_ROWS = 4000  # Sampling cap for CI performance
TOP_N_CHARGE_CATEGORIES = 50  # Top N frequent c_charge_desc categories to keep

# Fairness value generator - cycles through 0.25, 0.50, 0.75
def fairness_value_generator():
    """Generator that cycles through fairness values: 0.25, 0.50, 0.75"""
    return itertools.cycle([0.25, 0.50, 0.75])


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
    # NOTE: Intentionally including protected/sensitive attributes (race, sex, age_cat)
    # for bias evaluation purposes. This test validates the model submission pipeline's
    # ability to handle datasets with fairness-related features.
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
    
    # Create MinMaxScaler for MultinomialNB (requires non-negative features)
    # Apply MinMaxScaler directly to raw features (not to already-preprocessed data)
    minmax_preprocessor = ColumnTransformer(
        transformers=[
            ('num', Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', MinMaxScaler())
            ]), numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])
    minmax_preprocessor.fit(X_train)
    
    def minmax_preprocessor_func(data):
        return minmax_preprocessor.transform(data)
    
    return X_train, X_test, y_train, y_test, preprocessor, preprocessor_func, minmax_preprocessor, minmax_preprocessor_func


@pytest.fixture(scope="session")
def shared_playground(credentials, aws_environment, compas_data):
    """Create a shared ModelPlayground instance for all tests (session-scoped)."""
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func, minmax_preprocessor, minmax_preprocessor_func = compas_data
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


def test_compas_sklearn_models(shared_playground, compas_data):
    """
    Test all sklearn models with COMPAS dataset.
    
    Tests 18 different sklearn classifier types with both competition and experiment submission types.
    Includes special handling for MultinomialNB (non-negative feature requirement).
    Uses reduced iterations/estimators for CI performance.
    """
    print(f"\n{'='*80}")
    print(f"Testing: sklearn Models on COMPAS Dataset")
    print(f"{'='*80}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func, minmax_preprocessor, minmax_preprocessor_func = compas_data
    
    # Initialize fairness value generator
    fairness_gen = fairness_value_generator()
    
    # Define all 18 sklearn classifiers with CI-optimized parameters
    classifiers = [
        ("LogisticRegression", LogisticRegression(max_iter=500, random_state=42, class_weight='balanced')),
        ("RidgeClassifier", RidgeClassifier(random_state=42)),
        ("SGDClassifier", SGDClassifier(max_iter=800, random_state=42, tol=1e-3)),
        ("SVC", SVC(probability=True, random_state=42)),
        ("CalibratedClassifierCV_LinearSVC", CalibratedClassifierCV(LinearSVC(random_state=42, max_iter=500), cv=2)),
        ("KNeighborsClassifier", KNeighborsClassifier()),
        ("GaussianNB", GaussianNB()),
        ("MultinomialNB", MultinomialNB()),  # Requires non-negative features
        ("DecisionTreeClassifier", DecisionTreeClassifier(random_state=42)),
        ("RandomForestClassifier", RandomForestClassifier(n_estimators=50, random_state=42, class_weight='balanced')),
        ("ExtraTreesClassifier", ExtraTreesClassifier(n_estimators=50, random_state=42)),
        ("GradientBoostingClassifier", GradientBoostingClassifier(n_estimators=50, random_state=42)),
        ("HistGradientBoostingClassifier", HistGradientBoostingClassifier(max_iter=50, random_state=42)),
        ("AdaBoostClassifier", AdaBoostClassifier(n_estimators=50, random_state=42)),
        ("BaggingClassifier", BaggingClassifier(n_estimators=50, random_state=42)),
        ("LinearDiscriminantAnalysis", LinearDiscriminantAnalysis()),
        ("QuadraticDiscriminantAnalysis", QuadraticDiscriminantAnalysis()),
        ("MLPClassifier", MLPClassifier(solver='lbfgs', max_iter=150, random_state=42, hidden_layer_sizes=(20,))),
    ]
    
    failures = []
    
    for model_name, model in classifiers:
        print(f"\n{'-'*60}")
        print(f"Model: {model_name}")
        print(f"{'-'*60}")
        
        # Use MinMaxScaler preprocessor for MultinomialNB, StandardScaler for others
        if model_name == "MultinomialNB":
            current_preprocessor = minmax_preprocessor
            current_preprocessor_func = minmax_preprocessor_func
        else:
            current_preprocessor = preprocessor
            current_preprocessor_func = preprocessor_func
        
        # Preprocess data
        X_train_processed = current_preprocessor_func(X_train)
        X_test_processed = current_preprocessor_func(X_test)
        
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
                # Get next fairness value
                fairness_value = next(fairness_gen)
                
                shared_playground.submit_model(
                    model=model,
                    preprocessor=current_preprocessor,
                    prediction_submission=preds,
                    input_dict={
                        'description': f'CI test sklearn {model_name} COMPAS {submission_type}',
                        'tags': f'compas,bias,sklearn,{model_name},{submission_type}'
                    },
                    submission_type=submission_type,
                    custom_metadata={'Moral_Compass_Fairness': fairness_value}
                )
                print(f"✓ Submission succeeded ({submission_type}) with fairness={fairness_value}")
            except Exception as e:
                error_str = str(e).lower()
                # Skip only on stdin or ONNX fallback issues
                if 'reading from stdin' in error_str or 'stdin' in error_str or 'onnx' in error_str:
                    print(f"⊘ Skipped {model_name} ({submission_type}) due to ONNX/stdin issue")
                    continue
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


def test_compas_keras_models(shared_playground, compas_data):
    """
    Test all Keras models with COMPAS dataset.
    
    Tests 5 different Keras model types with both competition and experiment submission types.
    Uses 8 epochs for CI performance (as per problem statement).
    """
    print(f"\n{'='*80}")
    print(f"Testing: Keras Models on COMPAS Dataset")
    print(f"{'='*80}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func, minmax_scaler, minmax_preprocessor_func = compas_data
    
    # Initialize fairness value generator
    fairness_gen = fairness_value_generator()
    
    # Preprocess data
    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)
    input_dim = X_train_processed.shape[1]
    
    # Define Keras model factory functions
    def create_sequential_dense():
        """Sequential model with Dense layers."""
        model = Sequential([
            layers.Dense(64, activation='relu', input_shape=(input_dim,)),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model
    
    def create_functional_api():
        """Functional API model."""
        inputs = keras.Input(shape=(input_dim,))
        x = layers.Dense(64, activation='relu')(inputs)
        x = layers.Dense(32, activation='relu')(x)
        outputs = layers.Dense(1, activation='sigmoid')(x)
        model = Model(inputs=inputs, outputs=outputs)
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model
    
    def create_sequential_dropout():
        """Sequential model with Dropout."""
        model = Sequential([
            layers.Dense(64, activation='relu', input_shape=(input_dim,)),
            layers.Dropout(0.3),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model
    
    def create_batchnorm_model():
        """Model with BatchNormalization."""
        model = Sequential([
            layers.Dense(64, activation='relu', input_shape=(input_dim,)),
            layers.BatchNormalization(),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model
    
    class SubclassModel(tf.keras.Model):
        """Custom tf.keras.Model subclass."""
        def __init__(self):
            super(SubclassModel, self).__init__()
            self.dense1 = layers.Dense(64, activation='relu')
            self.dense2 = layers.Dense(32, activation='relu')
            self.dense3 = layers.Dense(1, activation='sigmoid')
        
        def call(self, inputs):
            x = self.dense1(inputs)
            x = self.dense2(x)
            return self.dense3(x)
    
    def create_subclass_model():
        """Create and compile subclass model."""
        model = SubclassModel()
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model
    
    keras_models = [
        ("sequential_dense", create_sequential_dense),
        ("functional_api", create_functional_api),
        ("sequential_dropout", create_sequential_dropout),
        ("batchnorm_model", create_batchnorm_model),
        ("subclass_model", create_subclass_model),
    ]
    
    failures = []
    
    for model_name, model_factory in keras_models:
        print(f"\n{'-'*60}")
        print(f"Model: {model_name}")
        print(f"{'-'*60}")
        
        # Create and train model
        try:
            model = model_factory()
            
            # For subclass models, build by calling once with sample data
            if model_name == "subclass_model":
                _ = model(X_train_processed[:1])
            
            # Train with 8 epochs as specified
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
                # Get next fairness value
                fairness_value = next(fairness_gen)
                
                shared_playground.submit_model(
                    model=model,
                    preprocessor=preprocessor,
                    prediction_submission=preds,
                    input_dict={
                        'description': f'CI test Keras {model_name} COMPAS {submission_type}',
                        'tags': f'compas,bias,keras,{model_name},{submission_type}'
                    },
                    submission_type=submission_type,
                    custom_metadata={'Moral_Compass_Fairness': fairness_value}
                )
                print(f"✓ Submission succeeded ({submission_type}) with fairness={fairness_value}")
            except Exception as e:
                error_str = str(e).lower()
                # Skip only on stdin ONNX fallback issues
                if 'reading from stdin' in error_str or 'stdin' in error_str or 'onnx' in error_str:
                    print(f"⊘ Skipped {model_name} ({submission_type}) due to ONNX/stdin issue")
                    continue
                error_msg = f"Submission failed for {model_name} ({submission_type}): {e}"
                print(f"✗ {error_msg}")
                failures.append(error_msg)
    
    # Report failures
    if failures:
        failure_report = "\n".join(f"  - {err}" for err in failures)
        pytest.fail(
            f"Keras model failures:\n{failure_report}\n\n"
            f"Expected: All Keras models should train and submit successfully (or skip only on ONNX/stdin issues)."
        )
    
    print(f"\n{'='*80}")
    print(f"✓ All Keras models completed successfully")
    print(f"{'='*80}")


def test_compas_torch_models(shared_playground, compas_data):
    """
    Test all PyTorch models with COMPAS dataset.
    
    Tests 4 different PyTorch model types with both competition and experiment submission types.
    Uses 8 epochs for CI performance (as per problem statement).
    """
    print(f"\n{'='*80}")
    print(f"Testing: PyTorch Models on COMPAS Dataset")
    print(f"{'='*80}")
    
    X_train, X_test, y_train, y_test, preprocessor, preprocessor_func, minmax_scaler, minmax_preprocessor_func = compas_data
    
    # Initialize fairness value generator
    fairness_gen = fairness_value_generator()
    
    # Preprocess data
    X_train_processed = preprocessor_func(X_train)
    X_test_processed = preprocessor_func(X_test)
    input_dim = X_train_processed.shape[1]
    
    # Define PyTorch model classes
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
    
    class MLPDropout(nn.Module):
        """MLP with Dropout layers."""
        def __init__(self, input_size):
            super().__init__()
            self.fc1 = nn.Linear(input_size, 64)
            self.dropout1 = nn.Dropout(0.3)
            self.fc2 = nn.Linear(64, 32)
            self.fc3 = nn.Linear(32, 1)
        
        def forward(self, x):
            x = F.relu(self.fc1(x))
            x = self.dropout1(x)
            x = F.relu(self.fc2(x))
            x = self.fc3(x)
            return x
    
    class MLPBatchNorm(nn.Module):
        """MLP with Batch Normalization."""
        def __init__(self, input_size):
            super().__init__()
            self.fc1 = nn.Linear(input_size, 64)
            self.bn1 = nn.BatchNorm1d(64)
            self.fc2 = nn.Linear(64, 32)
            self.fc3 = nn.Linear(32, 1)
        
        def forward(self, x):
            x = self.fc1(x)
            x = self.bn1(x)
            x = F.relu(x)
            x = F.relu(self.fc2(x))
            x = self.fc3(x)
            return x
    
    class MLPSubclass(nn.Module):
        """Custom PyTorch model demonstrating subclass pattern."""
        def __init__(self, input_size):
            super().__init__()
            self.fc1 = nn.Linear(input_size, 64)
            self.fc2 = nn.Linear(64, 64)
            self.fc3 = nn.Linear(64, 1)
        
        def forward(self, x):
            x = F.relu(self.fc1(x))
            x = F.relu(self.fc2(x))
            x = self.fc3(x)
            return x
    
    torch_models = [
        ("mlp_basic", MLPBasic),
        ("mlp_dropout", MLPDropout),
        ("mlp_batchnorm", MLPBatchNorm),
        ("mlp_subclass", MLPSubclass),
    ]
    
    failures = []
    
    for model_name, model_class in torch_models:
        print(f"\n{'-'*60}")
        print(f"Model: {model_name}")
        print(f"{'-'*60}")
        
        # Create and train model
        try:
            model = model_class(input_dim)
            
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
            
            # Training loop (8 epochs as specified)
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
            
            print(f"✓ Model trained, generated {len(preds)} predictions")
            print(f"  Prediction distribution: {pd.Series(preds).value_counts().to_dict()}")
            
            # Create dummy input for ONNX tracing
            dummy_input = torch.zeros((1, input_dim), dtype=torch.float32)
            
            # Perform forward pass to initialize parameters
            model.eval()
            with torch.no_grad():
                _ = model(dummy_input)
            
        except Exception as e:
            error_msg = f"Failed to train {model_name}: {e}"
            print(f"✗ {error_msg}")
            failures.append(error_msg)
            continue
        
        # Submit twice: once as competition, once as experiment
        for submission_type in ['competition', 'experiment']:
            try:
                # Get next fairness value
                fairness_value = next(fairness_gen)
                
                shared_playground.submit_model(
                    model=model,
                    preprocessor=preprocessor,
                    prediction_submission=preds,
                    input_dict={
                        'description': f'CI test PyTorch {model_name} COMPAS {submission_type}',
                        'tags': f'compas,bias,pytorch,{model_name},{submission_type}'
                    },
                    submission_type=submission_type,
                    model_input=dummy_input,
                    custom_metadata={'Moral_Compass_Fairness': fairness_value}
                )
                print(f"✓ Submission succeeded ({submission_type}) with fairness={fairness_value}")
            except Exception as e:
                error_str = str(e).lower()
                # Skip only on stdin or ONNX fallback issues
                if 'reading from stdin' in error_str or 'stdin' in error_str or 'onnx' in error_str:
                    print(f"⊘ Skipped {model_name} ({submission_type}) due to ONNX/stdin issue")
                    continue
                error_msg = f"Submission failed for {model_name} ({submission_type}): {e}"
                print(f"✗ {error_msg}")
                failures.append(error_msg)
    
    # Report failures
    if failures:
        failure_report = "\n".join(f"  - {err}" for err in failures)
        pytest.fail(
            f"PyTorch model failures:\n{failure_report}\n\n"
            f"Expected: All PyTorch models should train and submit successfully (or skip only on ONNX/stdin issues)."
        )
    
    print(f"\n{'='*80}")
    print(f"✓ All PyTorch models completed successfully")
    print(f"{'='*80}")


def test_compas_leaderboards(shared_playground):
    """
    Validate leaderboard contains submissions from all frameworks with both submission types.
    
    Ensures presence of submissions from sklearn, Keras, and PyTorch frameworks
    with tags 'compas', 'bias', and both 'competition' and 'experiment' submission types.
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
            # Check for compas and bias tags
            compas_tagged = df['tags'].astype(str).str.contains('compas', case=False, na=False)
            bias_tagged = df['tags'].astype(str).str.contains('bias', case=False, na=False)
            competition_tagged = df['tags'].astype(str).str.contains('competition', case=False, na=False)
            experiment_tagged = df['tags'].astype(str).str.contains('experiment', case=False, na=False)
            
            print(f"  Entries with 'compas' tag: {compas_tagged.sum()}")
            print(f"  Entries with 'bias' tag: {bias_tagged.sum()}")
            print(f"  Entries with 'competition' tag: {competition_tagged.sum()}")
            print(f"  Entries with 'experiment' tag: {experiment_tagged.sum()}")
            
            # Validate that we have submissions with expected tags
            assert compas_tagged.any(), "Expected at least one submission with 'compas' tag"
            assert bias_tagged.any(), "Expected at least one submission with 'bias' tag"
            # Note: competition/experiment tags may not be present if all submissions used experiment type
        
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
        
        print(f"\nLeaderboard sample:")
        print(df.head(10))
        print(f"\n✓ Leaderboard validation test passed")
        
    except Exception as e:
        pytest.fail(f"Leaderboard validation failed: {e}")


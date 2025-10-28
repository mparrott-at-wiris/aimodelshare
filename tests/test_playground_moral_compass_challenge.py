# tests/test_playground_moral_compass_challenge.py
import os
import time
import math
import pytest
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from aimodelshare.moral_compass import MoralcompassApiClient
from aimodelshare.moral_compass.api_client import NotFoundError, ApiClientError
from aimodelshare.moral_compass.challenge import ChallengeManager, JusticeAndEquityChallenge
from aimodelshare.moral_compass.config import get_api_base_url

USERNAME = os.getenv('username') or 'testuser_mc'
PLAYGROUND_ID = 'justice_equity_playground_integration'
TABLE_ID = f'{PLAYGROUND_ID}-mc'  # Follow naming convention
PLAYGROUND_URL = f'https://example.com/playground/{PLAYGROUND_ID}'

def resolve_api_base_url():
    """
    Resolve the Moral Compass API base URL.
    
    Resolution order:
    1. MORAL_COMPASS_API_BASE_URL environment variable (set in CI)
    2. get_api_base_url() fallback for local developer environments
    
    Returns:
        str: The API base URL
        
    Raises:
        RuntimeError: If API base URL cannot be determined
    """
    # Try environment variable first (CI sets this)
    env_url = os.getenv('MORAL_COMPASS_API_BASE_URL')
    if env_url:
        return env_url.rstrip('/')
    
    # Fall back to get_api_base_url() for local development
    try:
        return get_api_base_url()
    except RuntimeError as e:
        raise RuntimeError(
            "Could not resolve API base URL. In CI, ensure MORAL_COMPASS_API_BASE_URL "
            "is exported from terraform outputs. For local development, set the environment "
            "variable or ensure terraform outputs are accessible."
        ) from e

def build_dataset():
    # Synthetic mini COMPAS-like data (balanced + slight bias potential)
    import numpy as np
    rng = np.random.default_rng(42)
    n = 200
    race = rng.choice(['Black','White'], size=n, p=[0.5,0.5])
    sex = rng.choice(['Male','Female'], size=n, p=[0.6,0.4])
    age = rng.integers(18, 60, size=n)
    priors = rng.integers(0, 15, size=n)
    # Label: higher recidivism probability for higher priors + slight race effect (to simulate bias)
    base = 0.3 + 0.03*priors + (race == 'Black')*0.05 + (sex == 'Male')*0.02
    prob = 1/(1+np.exp(- (base - 0.5)))
    label = (rng.random(n) < prob).astype(int)
    df = pd.DataFrame({'race':race,'sex':sex,'age':age,'priors':priors,'label':label})
    return df

def featurize(df):
    # Simple numeric + one-hot encode race/sex manually for determinism
    d = df.copy()
    d['race_Black'] = (d['race']=='Black').astype(int)
    d['race_White'] = (d['race']=='White').astype(int)
    d['sex_Male'] = (d['sex']=='Male').astype(int)
    d['sex_Female'] = (d['sex']=='Female').astype(int)
    X = d[['age','priors','race_Black','sex_Male']]  # choose subset features
    y = d['label']
    return X, y

def train_model(X, y, C):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=13)
    pipe = Pipeline([('scaler', StandardScaler()), ('lr', LogisticRegression(C=C, max_iter=200))])
    pipe.fit(Xtr, ytr)
    acc = pipe.score(Xte, yte)
    return pipe, acc

def test_moral_compass_challenge_flow():
    # Try to resolve API base URL, skip test if unavailable
    try:
        api_base_url = resolve_api_base_url()
    except RuntimeError as e:
        pytest.skip(f"API base URL not available: {e}")
    
    # Explicitly pass api_base_url to bypass auto-discovery in CI
    api = MoralcompassApiClient(api_base_url=api_base_url)
    
    # Ensure table exists (idempotent create) with playgroundUrl
    try:
        api.create_table(TABLE_ID, display_name='Justice & Equity Challenge Integration', 
                        playground_url=PLAYGROUND_URL)
        time.sleep(1)
    except Exception:
        # Table may already exist from prior runs
        pass
    
    # Retry get_table to ensure metadata is available (avoid race condition)
    max_retries = 10
    retry_delay = 0.5
    table_available = False
    for attempt in range(max_retries):
        try:
            api.get_table(TABLE_ID)
            table_available = True
            break
        except (NotFoundError, ApiClientError) as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                pytest.fail(f"Table metadata not available after {max_retries} retries: {e}")
    
    assert table_available, "Table should be available before proceeding"
    
    # Pre-sync smoke test: validate endpoint with minimal metrics
    try:
        smoke_response = api.update_moral_compass(
            table_id=TABLE_ID,
            username=USERNAME,
            metrics={"accuracy": 0.5},
            tasks_completed=0,
            total_tasks=6,
            questions_correct=0,
            total_questions=14
        )
        assert 'moralCompassScore' in smoke_response, 'Smoke test response should include moralCompassScore'
        print(f"✓ Pre-sync smoke test passed: {smoke_response}")
    except (NotFoundError, ApiClientError) as e:
        pytest.fail(f"Pre-sync smoke test failed: {e}")

    # Build dataset & submit models (simulate user model improvement phase)
    df = build_dataset()
    X, y = featurize(df)
    candidate_Cs = [0.1, 1.0, 3.0]  # simple hyperparameter search
    best_acc = -1
    best_C = None
    models = []
    for C in candidate_Cs:
        model, acc = train_model(X, y, C)
        models.append((C, acc))
        if acc > best_acc:
            best_acc = acc
            best_C = C
    assert best_acc > 0, 'Accuracy must be positive'

    # Initialize challenge manager with primary accuracy metric
    manager = ChallengeManager(table_id=TABLE_ID, username=USERNAME, api_client=api)
    manager.set_metric('accuracy', best_acc, primary=True)

    # Progress through tasks A-F answering questions correctly
    challenge = manager.challenge
    prev_score = 0.0
    for task in challenge.tasks:
        manager.complete_task(task.id)
        for q in task.questions:
            manager.answer_question(task.id, q.id, selected_index=q.correct_index)
        # Sync after each task block
        sync_resp = manager.sync()
        mc_score = sync_resp['moralCompassScore']
        assert mc_score >= prev_score - 1e-6, f'Score decreased unexpectedly from {prev_score} to {mc_score}'
        prev_score = mc_score

    # Final validations
    summary = manager.get_progress_summary()
    assert summary['tasksCompleted'] == summary['totalTasks']
    assert summary['questionsCorrect'] == summary['totalQuestions']
    final_local = summary['localScorePreview']
    assert final_local > 0, 'Final local score should be > 0'

    # Leaderboard check
    lb = api.list_users(TABLE_ID, limit=100)
    entries = [u for u in lb.get('users', []) if u['username'] == USERNAME]
    assert entries, 'User not found on leaderboard'
    user_entry = entries[0]
    assert user_entry.get('moralCompassScore', 0) >= final_local - 0.2, 'Leaderboard score not aligned with local score'
    assert 'metrics' in user_entry and 'accuracy' in (user_entry['metrics'] or {}), 'Metrics map missing accuracy'

    print('✓ Moral Compass Justice & Equity challenge integration test passed.')

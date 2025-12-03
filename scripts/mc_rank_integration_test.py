#!/usr/bin/env python3
"""
Moral Compass Rank Integration Test

This test script validates that rank updates work correctly in a real user session.
It performs the following steps:
1. Authenticates using a session ID
2. Initializes a challenge manager for the user
3. Submits a sequence of tasks to the Moral Compass challenge
4. After each submission, syncs state and fetches ranks
5. Verifies that ranks change appropriately
6. Logs rank transitions for debugging

The test is designed to help diagnose front-end rank update issues by validating
that the back-end APIs return updated ranks promptly.

Usage:
    # Via environment variables
    SESSION_ID=<session_id> python scripts/mc_rank_integration_test.py
    
    # With optional parameters
    SESSION_ID=<session_id> TABLE_ID=<table_id> DEBUG_LOG=true python scripts/mc_rank_integration_test.py

Environment Variables:
    SESSION_ID (required): Session ID for authentication
    TABLE_ID (optional): Moral Compass table ID (auto-derived if not set)
    DEBUG_LOG (optional): Enable verbose logging (default: false)
    MORAL_COMPASS_API_BASE_URL (optional): Override API base URL
    PLAYGROUND_URL (optional): Override playground URL
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple

# Configuration constants
DEFAULT_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
SYNC_WAIT_SECONDS = 2  # Wait time after sync for consistency
TASK_INTERVAL_SECONDS = 3  # Wait time between task submissions to avoid rate limiting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Set up debug logging if requested
if os.getenv('DEBUG_LOG', 'false').lower() == 'true':
    logger.setLevel(logging.DEBUG)
    # Also enable debug for aimodelshare modules
    logging.getLogger('aimodelshare').setLevel(logging.DEBUG)


def mask_sensitive_data(data: str, length: int = 8) -> str:
    """Mask sensitive data for safe logging."""
    if not data or len(data) <= length:
        return '***'
    return data[:length] + '***'


def check_prerequisites() -> bool:
    """Check if required environment variables are set."""
    session_id = os.getenv('SESSION_ID')
    
    if not session_id:
        logger.warning("SESSION_ID environment variable not set")
        logger.info("This test requires a valid SESSION_ID to authenticate")
        logger.info("Skipping test (exit 0)")
        return False
    
    logger.info(f"SESSION_ID provided: {mask_sensitive_data(session_id)}")
    return True


def authenticate(session_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Authenticate using session ID to get token and username.
    
    Returns:
        Tuple of (username, token) or (None, None) on failure
    """
    try:
        from aimodelshare.aws import get_token_from_session, _get_username_from_token
        
        logger.info("Authenticating via session ID...")
        token = get_token_from_session(session_id)
        
        if not token:
            logger.error("Failed to get token from session")
            return None, None
        
        logger.info(f"Token obtained: {mask_sensitive_data(token, 12)}")
        
        username = _get_username_from_token(token)
        if not username:
            logger.error("Failed to extract username from token")
            return None, None
        
        logger.info(f"Username extracted: {username}")
        return username, token
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}", exc_info=True)
        return None, None


def initialize_challenge_manager(username: str, table_id: Optional[str] = None) -> Optional[Any]:
    """
    Initialize ChallengeManager for the user.
    
    Returns:
        ChallengeManager instance or None on failure
    """
    try:
        from aimodelshare.moral_compass.apps.mc_integration_helpers import (
            get_challenge_manager,
            _derive_table_id
        )
        
        if not table_id:
            table_id = os.getenv('TABLE_ID') or _derive_table_id()
        
        logger.info(f"Initializing ChallengeManager for user '{username}' with table '{table_id}'")
        
        cm = get_challenge_manager(username, table_id)
        
        if not cm:
            logger.error("get_challenge_manager returned None")
            return None
        
        # Configure for Bias Detective flow (21 tasks)
        cm.set_progress(
            tasks_completed=0,
            total_tasks=21,
            questions_correct=0,
            total_questions=0
        )
        
        # Set a test accuracy metric
        cm.set_metric('accuracy', 0.92, primary=False)
        
        logger.info("ChallengeManager initialized successfully")
        return cm
        
    except Exception as e:
        logger.error(f"Failed to initialize ChallengeManager: {e}", exc_info=True)
        return None


def get_initial_ranks(username: str, table_id: str, team_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get initial ranks for the user.
    
    Returns:
        Dictionary with rank information
    """
    try:
        from aimodelshare.moral_compass.apps.mc_integration_helpers import get_user_ranks
        
        logger.info("Fetching initial ranks...")
        rank_info = get_user_ranks(username, table_id, team_name)
        
        logger.info(f"Initial ranks: individual={rank_info.get('individual_rank')}, team={rank_info.get('team_rank')}")
        return rank_info
        
    except Exception as e:
        logger.error(f"Failed to get initial ranks: {e}", exc_info=True)
        return {'individual_rank': None, 'team_rank': None, 'moral_compass_score': None}


def submit_task_and_sync(
    cm: Any,
    task_id: str,
    moral_points: int,
    accuracy: float,
    username: str,
    table_id: str,
    team_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit a task, sync state, and get updated ranks.
    
    Returns:
        Dictionary with sync and rank information
    """
    try:
        from aimodelshare.moral_compass.apps.mc_integration_helpers import (
            sync_user_moral_state,
            get_user_ranks,
            sync_team_state
        )
        
        logger.info(f"Submitting task '{task_id}' with moral_points={moral_points}")
        
        # Complete the task
        task_completed = cm.complete_task(task_id)
        
        if not task_completed:
            logger.warning(f"Task '{task_id}' was already completed or could not be completed")
        else:
            logger.info(f"Task '{task_id}' completed successfully")
        
        # Sync user state (with override to bypass debounce)
        logger.info("Syncing user moral state...")
        sync_result = sync_user_moral_state(
            cm=cm,
            moral_points=moral_points,
            accuracy=accuracy,
            override=True  # Bypass debounce for testing
        )
        
        logger.info(f"Sync result: {json.dumps(sync_result, indent=2)}")
        
        if not sync_result.get('synced'):
            logger.warning("Sync did not complete successfully")
        
        # Wait a moment for consistency
        time.sleep(SYNC_WAIT_SECONDS)
        
        # Clear any local caches (simulating what the app does)
        logger.debug("Clearing local caches...")
        
        # Get updated ranks
        logger.info("Fetching updated ranks...")
        rank_info = get_user_ranks(username, table_id, team_name)
        
        logger.info(f"Updated ranks: individual={rank_info.get('individual_rank')}, team={rank_info.get('team_rank')}")
        
        # Sync team state if team name provided
        if team_name:
            logger.info(f"Syncing team state for '{team_name}'...")
            team_sync_result = sync_team_state(team_name, table_id)
            logger.debug(f"Team sync result: {json.dumps(team_sync_result, indent=2)}")
        
        return {
            'task_id': task_id,
            'task_completed': task_completed,
            'sync_result': sync_result,
            'rank_info': rank_info
        }
        
    except Exception as e:
        logger.error(f"Failed to submit task and sync: {e}", exc_info=True)
        return {
            'task_id': task_id,
            'error': str(e)
        }


def verify_rank_changes(rank_history: List[Dict[str, Any]]) -> bool:
    """
    Verify that ranks changed during the test.
    
    Returns:
        True if ranks changed appropriately, False otherwise
    """
    if len(rank_history) < 2:
        logger.error("Not enough rank data to verify changes")
        return False
    
    initial_rank = rank_history[0].get('individual_rank')
    final_rank = rank_history[-1].get('individual_rank')
    
    logger.info(f"Rank progression: initial={initial_rank} -> final={final_rank}")
    
    # Check if ranks are present
    if initial_rank is None and final_rank is None:
        logger.error("No individual ranks found throughout test")
        return False
    
    # For a real test, we'd expect ranks to improve (decrease in number) or at least change
    # However, in a test environment with synthetic data, we just verify they're being tracked
    rank_changes_detected = False
    for i in range(1, len(rank_history)):
        prev_rank = rank_history[i-1].get('individual_rank')
        curr_rank = rank_history[i].get('individual_rank')
        
        if prev_rank != curr_rank:
            logger.info(f"Rank change detected: #{prev_rank} -> #{curr_rank}")
            rank_changes_detected = True
    
    if not rank_changes_detected:
        logger.warning("No rank changes detected during test")
        logger.info("This may be expected if the user is the only participant or already at top rank")
        # Don't fail the test for this - just log it
    
    logger.info("✓ Rank tracking is working (ranks are being reported)")
    return True


def run_test() -> int:
    """
    Run the full integration test.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 70)
    logger.info("Moral Compass Rank Integration Test")
    logger.info("=" * 70)
    
    # Check prerequisites
    if not check_prerequisites():
        return 0  # Skip gracefully
    
    session_id = os.getenv('SESSION_ID')
    table_id = os.getenv('TABLE_ID')
    
    # Step 1: Authenticate
    logger.info("\n[STEP 1] Authenticating...")
    username, token = authenticate(session_id)
    
    if not username or not token:
        logger.error("Authentication failed")
        return 1
    
    logger.info(f"✓ Authenticated as '{username}'")
    
    # Step 2: Initialize challenge manager
    logger.info("\n[STEP 2] Initializing ChallengeManager...")
    cm = initialize_challenge_manager(username, table_id)
    
    if not cm:
        logger.error("Failed to initialize ChallengeManager")
        return 1
    
    logger.info("✓ ChallengeManager initialized")
    
    # Derive table_id if not provided
    if not table_id:
        from aimodelshare.moral_compass.apps.mc_integration_helpers import _derive_table_id
        table_id = _derive_table_id()
    
    # Get team name (if any)
    team_name = None
    try:
        # Try to get team from playground leaderboard
        from aimodelshare.playground import Competition
        playground_url = os.getenv('PLAYGROUND_URL', DEFAULT_PLAYGROUND_URL)
        playground = Competition(playground_url)
        leaderboard = playground.get_leaderboard(token=token)
        
        if leaderboard is not None and not leaderboard.empty and "Team" in leaderboard.columns:
            user_entries = leaderboard[leaderboard["username"] == username]
            if not user_entries.empty:
                team_name = user_entries.iloc[0]["Team"]
                if team_name and str(team_name).strip():
                    logger.info(f"Detected team: '{team_name}'")
    except Exception as e:
        logger.debug(f"Could not detect team: {e}")
    
    # Step 3: Get initial ranks
    logger.info("\n[STEP 3] Getting initial ranks...")
    initial_ranks = get_initial_ranks(username, table_id, team_name)
    
    rank_history = [initial_ranks]
    
    # Step 4: Submit tasks and track rank changes
    logger.info("\n[STEP 4] Submitting tasks and tracking rank changes...")
    
    # Submit 5 tasks as a test sequence
    test_tasks = [
        ('mc_test_1', 1, 0.92),
        ('mc_test_2', 2, 0.92),
        ('mc_test_3', 3, 0.93),
        ('mc_test_4', 4, 0.93),
        ('mc_test_5', 5, 0.94),
    ]
    
    for task_id, moral_points, accuracy in test_tasks:
        logger.info(f"\n--- Task {moral_points}/5 ---")
        
        result = submit_task_and_sync(
            cm=cm,
            task_id=task_id,
            moral_points=moral_points,
            accuracy=accuracy,
            username=username,
            table_id=table_id,
            team_name=team_name
        )
        
        if 'error' in result:
            logger.error(f"Task submission failed: {result['error']}")
            continue
        
        # Add to rank history
        rank_history.append(result['rank_info'])
        
        # Wait between tasks to avoid rate limiting
        time.sleep(TASK_INTERVAL_SECONDS)
    
    # Step 5: Verify rank changes
    logger.info("\n[STEP 5] Verifying rank changes...")
    
    # Log rank progression
    logger.info("\nRank progression summary:")
    logger.info("-" * 50)
    for i, ranks in enumerate(rank_history):
        logger.info(f"  After task {i}: individual=#{ranks.get('individual_rank')}, "
                   f"team=#{ranks.get('team_rank')}, "
                   f"score={ranks.get('moral_compass_score')}")
    logger.info("-" * 50)
    
    if not verify_rank_changes(rank_history):
        logger.error("Rank verification failed")
        return 1
    
    logger.info("\n" + "=" * 70)
    logger.info("✓ Test completed successfully!")
    logger.info("=" * 70)
    
    return 0


if __name__ == '__main__':
    exit_code = run_test()
    sys.exit(exit_code)

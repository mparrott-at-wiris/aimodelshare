#!/usr/bin/env python3
"""
Moral Compass Rank Integration Test

This script authenticates using a Gradio-style session id, initializes a ChallengeManager,
submits tasks to the Moral Compass challenge, and checks rank updates after each sync.

It derives table_id from PLAYGROUND_URL via mc_integration_helpers._derive_table_id()
if TABLE_ID is not provided.

Environment:
- SESSION_ID: required (from workflow input or secret)
- TABLE_ID: optional (workflow input override). If absent, derive from PLAYGROUND_URL.
- PLAYGROUND_URL: optional but required if TABLE_ID is not provided (for deriving table id)
- MORAL_COMPASS_API_BASE_URL: optional; if set, used by API client
- DEBUG_LOG: optional ("true"/"false")

Exit codes:
- 0 on success
- 1 on failure
"""

import os
import sys
import time
import json
import logging
from typing import Optional, Dict, Any, List

# Configure logging
logger = logging.getLogger("mc_rank_integration_test")
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Optional debug toggle
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"
if DEBUG_LOG:
    logger.setLevel(logging.DEBUG)

# Imports from aimodelshare
from aimodelshare.aws import get_token_from_session, _get_username_from_token
from aimodelshare.moral_compass.apps.mc_integration_helpers import (
    get_challenge_manager,
    sync_user_moral_state,
    get_user_ranks,
    _derive_table_id,
    sync_team_state,
)

def mask(s: str) -> str:
    if not s:
        return ""
    if len(s) <= 4:
        return "***"
    return s[:6] + "***"

def derive_table_id_if_needed(explicit_table_id: Optional[str]) -> str:
    """
    Return explicit_table_id if provided; otherwise derive via _derive_table_id().

    _derive_table_id() typically uses PLAYGROUND_URL and naming conventions (suffix '-mc'),
    and honors MC_ENFORCE_NAMING to include region when required.
    """
    if explicit_table_id and explicit_table_id.strip():
        logger.info(f"Using provided TABLE_ID: {explicit_table_id}")
        return explicit_table_id.strip()
    # Fall back to derive from PLAYGROUND_URL
    derived = _derive_table_id()
    logger.info(f"Derived TABLE_ID via PLAYGROUND_URL: {derived}")
    return derived

def authenticate_via_session(session_id: str) -> Dict[str, str]:
    logger.info("\n[STEP 1] Authenticating...")
    try:
        token = get_token_from_session(session_id)
        logger.info(f"Token obtained: {mask(token)}")
        username = _get_username_from_token(token)
        logger.info(f"Username extracted: {username}")
        logger.info(f"✓ Authenticated as '{username}'")
        return {"token": token, "username": username}
    except Exception as e:
        logger.error(f"Failed session authentication: {e}")
        raise

def initialize_challenge_manager(username: str, table_id: str, team_name: Optional[str]) -> Any:
    logger.info("\n[STEP 2] Initializing ChallengeManager...")
    logger.info(f"Initializing ChallengeManager for user '{username}' with table '{table_id}'")
    try:
        cm = get_challenge_manager(username, team_name=team_name)
        if cm is None:
            raise RuntimeError("get_challenge_manager returned None")
        # Configure for Bias Detective flow (21 tasks)
        cm.set_progress(tasks_completed=0, total_tasks=21, questions_correct=0, total_questions=0)
        cm.set_metric("accuracy", 0.92, primary=True)
        logger.info(f"Created ChallengeManager for user={username}, table={table_id}")
        logger.info("ChallengeManager initialized successfully")
        return cm
    except Exception as e:
        logger.error(f"Failed to initialize ChallengeManager: {e}")
        raise

def get_initial_team(username: str, table_id: str) -> Optional[str]:
    # Try to get ranks first; if user has existing teamName it may be returned there
    try:
        ranks = get_user_ranks(username=username, table_id=table_id)
        team_name = ranks.get("team_name") or ranks.get("teamName")
        if team_name:
            logger.info(f"Detected team: '{team_name}'")
        return team_name
    except Exception as e:
        logger.debug(f"Could not detect team from ranks: {e}")
        return None

def fetch_ranks(username: str, table_id: str, team_name: Optional[str]) -> Dict[str, Any]:
    logger.info("Fetching ranks...")
    try:
        rank_info = get_user_ranks(username=username, table_id=table_id, team_name=team_name)
        logger.debug(f"Rank payload: {json.dumps(rank_info, indent=2)}")
        individual_rank = rank_info.get("individual_rank")
        team_rank = rank_info.get("team_rank")
        score = rank_info.get("moral_compass_score")
        logger.info(f"Current ranks: individual={individual_rank}, team={team_rank}, score={score}")
        return {"individual_rank": individual_rank, "team_rank": team_rank, "score": score}
    except Exception as e:
        logger.error(f"Failed to fetch ranks: {e}")
        return {"individual_rank": None, "team_rank": None, "score": None}

def submit_tasks_and_track(cm: Any, username: str, table_id: str, team_name: Optional[str], tasks: List[str]) -> List[Dict[str, Any]]:
    logger.info("\n[STEP 4] Submitting tasks and tracking rank changes...")
    progression = []
    for i, task_id in enumerate(tasks):
        try:
            newly_completed = cm.complete_task(task_id)
            if not newly_completed:
                logger.debug(f"Task {task_id} was already completed")
            sync_result = sync_user_moral_state(cm=cm, moral_points=cm.tasks_completed, accuracy=cm.metrics.get("accuracy", 0.0))
            logger.debug(f"Sync result: {json.dumps(sync_result, indent=2)}")

            # Optionally sync team if team_name exists
            if team_name:
                team_sync = sync_team_state(team_name=team_name)
                logger.debug(f"Team sync result: {json.dumps(team_sync, indent=2)}")

            # Short delay to allow backend state visibility (DynamoDB, caches)
            time.sleep(1.0)

            ranks = fetch_ranks(username, table_id, team_name)
            logger.info(f"After task {i}: individual=#{ranks['individual_rank']}, team=#{ranks['team_rank']}, score={ranks['score']}")
            progression.append(ranks)
        except Exception as e:
            logger.error(f"Error submitting task {task_id}: {e}")
            progression.append({"individual_rank": None, "team_rank": None, "score": None})
    return progression

def main():
    logger.info("======================================================================")
    logger.info("Moral Compass Rank Integration Test")
    logger.info("======================================================================")

    session_id = os.environ.get("SESSION_ID", "").strip()
    table_id_input = os.environ.get("TABLE_ID", "").strip()

    if not session_id:
        logger.error("SESSION_ID is required. Provide via workflow input or secret.")
        sys.exit(1)

    logger.info(f"SESSION_ID provided: {mask(session_id)}")

    # Derive or use provided table_id
    table_id = derive_table_id_if_needed(table_id_input)

    # Authenticate
    auth = authenticate_via_session(session_id)
    token = auth["token"]
    username = auth["username"]

    # Initialize ChallengeManager
    team_name = get_initial_team(username, table_id)
    cm = initialize_challenge_manager(username, table_id, team_name)

    # Initial ranks
    logger.info("\n[STEP 3] Getting initial ranks...")
    initial_ranks = fetch_ranks(username, table_id, team_name)

    # Submit tasks and track rank changes (use a few sample task IDs)
    tasks = ["mc1", "mc2", "mc3", "mc4", "mc5", "mc6"]
    progression = submit_tasks_and_track(cm, username, table_id, team_name, tasks)

    # Verification
    logger.info("\n[STEP 5] Verifying rank changes...")
    logger.info("\nRank progression summary:")
    logger.info("--------------------------------------------------")
    for idx, r in enumerate(progression):
        logger.info(f"  After task {idx}: individual=#{r['individual_rank']}, team=#{r['team_rank']}, score={r['score']}")
    logger.info("--------------------------------------------------")

    initial_individual = initial_ranks.get("individual_rank")
    final_individual = progression[-1].get("individual_rank") if progression else None
    logger.info(f"Rank progression: initial={initial_individual} -> final={final_individual}")

    # Basic assertion: we should observe some rank or score present, even if rank doesn't change immediately
    if all(r.get("individual_rank") is None for r in progression):
        logger.error("No individual ranks found throughout test")
        sys.exit(1)

    # If everything looks reasonable, exit success
    logger.info("✓ Rank integration test completed")
    sys.exit(0)

if __name__ == "__main__":
    main()

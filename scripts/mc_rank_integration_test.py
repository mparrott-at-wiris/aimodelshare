#!/usr/bin/env python3
"""
Moral Compass Rank Integration Test

Updates:
- After authenticating via SESSION_ID, set JWT_AUTHORIZATION_TOKEN env var
  to the extracted token so API calls (e.g., create table) are authorized.

Env:
- SESSION_ID (required)
- TABLE_ID (optional; if missing, derive via _derive_table_id)
- PLAYGROUND_URL (optional; used when creating table)
- MORAL_COMPASS_API_BASE_URL (optional)
- DEBUG_LOG (optional)
"""

import os
import sys
import time
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("mc_rank_integration_test")
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"
if DEBUG_LOG:
    logger.setLevel(logging.DEBUG)

from aimodelshare.aws import get_token_from_session, _get_username_from_token
from aimodelshare.moral_compass.apps.mc_integration_helpers import (
    get_challenge_manager,
    sync_user_moral_state,
    get_user_ranks,
    _derive_table_id,
    sync_team_state,
)
from aimodelshare.moral_compass import MoralcompassApiClient, NotFoundError, ApiClientError

def mask(s: str) -> str:
    if not s:
        return ""
    return s[:6] + "***" if len(s) > 6 else "***"

def derive_table_id_if_needed(explicit_table_id: Optional[str]) -> str:
    if explicit_table_id and explicit_table_id.strip():
        logger.info(f"Using provided TABLE_ID: {explicit_table_id}")
        return explicit_table_id.strip()
    derived = _derive_table_id()
    logger.info(f"Derived TABLE_ID via PLAYGROUND_URL: {derived}")
    return derived

def ensure_table_exists(table_id: str, playground_url: Optional[str]) -> None:
    """
    Verify table exists; create it if missing.
    Requires JWT_AUTHORIZATION_TOKEN in env when AUTH_ENABLED=true.
    """
    api_base = os.environ.get("MORAL_COMPASS_API_BASE_URL")
    client = MoralcompassApiClient(api_base_url=api_base) if api_base else MoralcompassApiClient()

    try:
        client.get_table(table_id)
        logger.info(f"Table '{table_id}' exists.")
        return
    except NotFoundError:
        logger.info(f"Table '{table_id}' not found. Attempting creation...")
        try:
            resp = client.create_table(
                table_id=table_id,
                display_name=f"Moral Compass - {table_id}",
                playground_url=playground_url
            )
            logger.info(f"Created table '{table_id}': {resp}")
        except ApiClientError as e:
            logger.error(f"Failed to create table '{table_id}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating table '{table_id}': {e}")
            raise
    except Exception as e:
        logger.error(f"Failed to verify table '{table_id}': {e}")
        raise

def authenticate_and_export_token(session_id: str) -> Dict[str, str]:
    """
    Authenticate via session ID and set JWT_AUTHORIZATION_TOKEN in env
    so subsequent API client calls are authorized.
    """
    logger.info("\n[STEP 1] Authenticating...")
    token = get_token_from_session(session_id)
    logger.info(f"Token obtained: {mask(token)}")
    username = _get_username_from_token(token)
    logger.info(f"Username extracted: {username}")
    logger.info(f"✓ Authenticated as '{username}'")

    # Export the session token as JWT for API client
    os.environ["JWT_AUTHORIZATION_TOKEN"] = token
    logger.info("JWT_AUTHORIZATION_TOKEN exported from session token")

    return {"token": token, "username": username}

def initialize_challenge_manager(username: str) -> Any:
    logger.info("\n[STEP 2] Initializing ChallengeManager...")
    try:
        cm = get_challenge_manager(username)
        if cm is None:
            raise RuntimeError("get_challenge_manager returned None")
        cm.set_progress(tasks_completed=0, total_tasks=21, questions_correct=0, total_questions=0)
        cm.set_metric("accuracy", 0.92, primary=True)
        logger.info(f"ChallengeManager initialized for user={username}")
        return cm
    except Exception as e:
        logger.error(f"Failed to initialize ChallengeManager: {e}")
        raise

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
            cm.complete_task(task_id)
            sync_result = sync_user_moral_state(cm=cm, moral_points=cm.tasks_completed, accuracy=cm.metrics.get("accuracy", 0.0))
            logger.debug(f"Sync result: {json.dumps(sync_result, indent=2)}")

            if team_name:
                try:
                    team_sync = sync_team_state(team_name=team_name)
                    logger.debug(f"Team sync result: {json.dumps(team_sync, indent=2)}")
                except Exception as te:
                    logger.debug(f"Team sync failed: {te}")

            time.sleep(1.0)  # brief delay for backend visibility
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
    playground_url = os.environ.get("PLAYGROUND_URL", "").strip()

    if not session_id:
        logger.error("SESSION_ID is required. Provide via workflow input or secret.")
        sys.exit(1)
    logger.info(f"SESSION_ID provided: {mask(session_id)}")

    table_id = derive_table_id_if_needed(table_id_input)

    # Authenticate and set JWT_AUTHORIZATION_TOKEN from session
    auth = authenticate_and_export_token(session_id)
    username = auth["username"]

    # Ensure table exists or create it (now authorized)
    try:
        ensure_table_exists(table_id, playground_url if playground_url else None)
    except Exception:
        logger.error("Table setup failed; cannot proceed with rank test.")
        sys.exit(2)

    # Initialize CM
    cm = initialize_challenge_manager(username)

    # Initial ranks
    logger.info("\n[STEP 3] Getting initial ranks...")
    initial_rank_info = fetch_ranks(username, table_id, team_name=None)
    team_name = initial_rank_info.get("team_name") or None

    # Submit tasks and verify
    tasks = ["mc1", "mc2", "mc3", "mc4", "mc5", "mc6"]
    progression = submit_tasks_and_track(cm, username, table_id, team_name, tasks)

    logger.info("\n[STEP 5] Verifying rank changes...")
    logger.info("\nRank progression summary:")
    logger.info("--------------------------------------------------")
    for idx, r in enumerate(progression):
        logger.info(f"  After task {idx}: individual=#{r['individual_rank']}, team=#{r['team_rank']}, score={r['score']}")
    logger.info("--------------------------------------------------")

    if all(r.get("individual_rank") is None for r in progression):
        logger.error("No individual ranks found throughout test")
        sys.exit(1)

    logger.info("✓ Rank integration test completed")
    sys.exit(0)

if __name__ == "__main__":
    main()

"""
Integration helpers for Moral Compass apps.

Provides helper functions to:
- Derive table ID
- Manage ChallengeManager lifecycle
- Sync user and team state
- Compute user ranks

This patch updates _derive_table_id to use host-based derivation:
- playground_id = first hostname label (e.g., cf3wdpkg0d from cf3wdpkg0d.execute-api.us-east-1.amazonaws.com)
- region = label immediately after 'execute-api' (e.g., us-east-1)
- table_id = <playground_id>-mc (default) or <playground_id>-<region>-mc when MC_ENFORCE_NAMING requires region-aware naming.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from aimodelshare.moral_compass.api_client import MoralcompassApiClient
from aimodelshare.moral_compass.challenge import ChallengeManager

logger = logging.getLogger("aimodelshare.moral_compass.apps.helpers")

# Local cache for list_users responses to reduce API load
_leaderboard_cache: Dict[str, Dict[str, Any]] = {}
_LEADERBOARD_TTL_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))

def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    entry = _leaderboard_cache.get(key)
    if not entry:
        return None
    if (time.time() - entry.get("_ts", 0)) > _LEADERBOARD_TTL_SECONDS:
        try:
            del _leaderboard_cache[key]
        except Exception:
            pass
        return None
    return entry

def _cache_set(key: str, data: Dict[str, Any]) -> None:
    _leaderboard_cache[key] = {"data": data, "_ts": time.time()}

def _derive_table_id() -> str:
    """
    Derive Moral Compass table ID from PLAYGROUND_URL using host-based rules:

    - playground_id: first label of hostname (before first dot)
      Example: PLAYGROUND_URL=https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m
               host=cf3wdpkg0d.execute-api.us-east-1.amazonaws.com
               playground_id=cf3wdpkg0d

    - region: label immediately after 'execute-api' in hostname, if present
      Example: 'us-east-1'

    Naming:
    - If MC_ENFORCE_NAMING=true and a region is found: <playground_id>-<region>-mc
    - Else: <playground_id>-mc

    Fallback:
    - If PLAYGROUND_URL is missing or host parsing fails, fall back to legacy path-based ID:
      Use last non-empty path segment when it matches a safe ID pattern; otherwise 'm'.
      Then append '-mc'.

    Environment flags:
    - MC_ENFORCE_NAMING controls whether to include region when available.

    Returns:
        table_id string
    """
    url = os.environ.get("PLAYGROUND_URL", "").strip()
    enforce = os.environ.get("MC_ENFORCE_NAMING", "false").lower() == "true"

    if not url:
        # Conservative default
        return "m-mc"

    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").split(":")[0]
        labels = host.split(".") if host else []

        playground_id = labels[0] if labels else None

        region = None
        if labels:
            try:
                idx = labels.index("execute-api")
                if idx + 1 < len(labels):
                    region = labels[idx + 1]
            except ValueError:
                region = None

        # Fallback to legacy path-based extraction if host-based failed
        if not playground_id:
            path_parts = [p for p in (parsed.path or "").split("/") if p]
            playground_id = path_parts[-1] if path_parts else "m"

        if enforce and region:
            return f"{playground_id}-{region}-mc"
        return f"{playground_id}-mc"

    except Exception as e:
        logger.warning(f"Failed to derive table ID from PLAYGROUND_URL: {e}")
        return "m-mc"


def get_challenge_manager(username: str) -> Optional[ChallengeManager]:
    """
    Create or retrieve a ChallengeManager for the given user.

    Uses derived table_id and default MoralcompassApiClient unless overridden by env.
    """
    try:
        table_id = _derive_table_id()
        api_base_url = os.environ.get("MORAL_COMPASS_API_BASE_URL")
        client = MoralcompassApiClient(api_base_url=api_base_url) if api_base_url else MoralcompassApiClient()
        manager = ChallengeManager(table_id=table_id, username=username, api_client=client)
        return manager
    except Exception as e:
        logger.error(f"Failed to initialize ChallengeManager for {username}: {e}")
        return None


def sync_user_moral_state(cm: ChallengeManager, moral_points: int, accuracy: float) -> Dict[str, Any]:
    """
    Sync user's moral compass metrics using ChallengeManager.
    """
    try:
        cm.set_metric('accuracy', accuracy, primary=True if cm.primary_metric is None else False)
        cm.set_progress(tasks_completed=moral_points, total_tasks=cm.total_tasks)
        result = cm.sync()
        return {
            "synced": True,
            "status": "ok",
            "local_preview": cm.get_local_score(),
            **result
        }
    except Exception as e:
        logger.warning(f"User sync failed for {cm.username}: {e}")
        return {
            "synced": False,
            "status": "error",
            "local_preview": cm.get_local_score(),
            "error": str(e),
            "message": "⚠️ Sync error. Local preview: {:.4f}".format(cm.get_local_score())
        }


def sync_team_state(team_name: str) -> Dict[str, Any]:
    """
    Placeholder for team sync. Implement as needed when team endpoints are available.
    """
    # In current backend, teams are inferred from user rows (teamName field).
    # This function is kept for API parity and future expansion.
    return {"synced": False, "status": "error", "message": f"No members found for team {team_name}"}


def fetch_cached_users(table_id: str, ttl: int = _LEADERBOARD_TTL_SECONDS) -> List[Dict[str, Any]]:
    """
    Fetch and cache users for a table, exposing moralCompassScore for ranking computations.

    Returns a list of dicts with keys:
    - username
    - moralCompassScore (fallback to totalCount if missing)
    - submissionCount
    - totalCount
    - teamName (if present)
    """
    now = time.time()
    cached = _leaderboard_cache.get(table_id)
    if cached and (now - cached.get("_ts", 0) < ttl):
        return cached["data"]

    client = MoralcompassApiClient(api_base_url=os.environ.get("MORAL_COMPASS_API_BASE_URL"))
    resp = client.list_users(table_id, limit=100)
    users = resp.get("users", []) if isinstance(resp, dict) else []

    # Normalize fields and fallback
    normalized = []
    for u in users:
        normalized.append({
            "username": u.get("username"),
            "moralCompassScore": u.get("moralCompassScore", u.get("totalCount", 0)),
            "submissionCount": u.get("submissionCount", 0),
            "totalCount": u.get("totalCount", 0),
            "teamName": u.get("teamName")
        })

    _leaderboard_cache[table_id] = {"data": normalized, "_ts": now}
    return normalized


def get_user_ranks(username: str, table_id: Optional[str] = None, team_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Compute ranks for a user based on moralCompassScore from list_users.

    Returns:
        {
            "individual_rank": Optional[int],
            "team_rank": Optional[int],
            "moral_compass_score": Optional[float],
            "team_name": Optional[str]
        }
    """
    table_id = table_id or _derive_table_id()
    users = fetch_cached_users(table_id)

    # Individual ranks sorted by moralCompassScore desc, then submissionCount desc
    sorted_users = sorted(users, key=lambda x: (float(x.get("moralCompassScore", 0)), x.get("submissionCount", 0)), reverse=True)

    individual_rank = None
    moral_score = None
    user_team = None

    for idx, u in enumerate(sorted_users, start=1):
        if u.get("username") == username:
            individual_rank = idx
            moral_score = float(u.get("moralCompassScore", 0))
            user_team = u.get("teamName")
            break

    team_rank = None
    # Compute team rank if provided
    if team_name:
        # Aggregate team entries where username starts with 'team:' or matches teamName
        team_users = [u for u in sorted_users if u.get("username", "").startswith("team:") or u.get("teamName")]
        # Create team scores grouped by teamName or 'team:<name>' entries
        team_scores: Dict[str, float] = {}
        for u in team_users:
            tname = u.get("teamName")
            uname = u.get("username", "")
            if uname.startswith("team:"):
                tname = uname.split("team:", 1)[-1]
            if not tname:
                continue
            score = float(u.get("moralCompassScore", 0))
            team_scores[tname] = max(team_scores.get(tname, 0.0), score)

        sorted_teams = sorted(team_scores.items(), key=lambda kv: kv[1], reverse=True)
        for idx, (tname, _) in enumerate(sorted_teams, start=1):
            if tname == team_name:
                team_rank = idx
                break

    return {
        "individual_rank": individual_rank,
        "team_rank": team_rank,
        "moral_compass_score": moral_score,
        "team_name": user_team
    }

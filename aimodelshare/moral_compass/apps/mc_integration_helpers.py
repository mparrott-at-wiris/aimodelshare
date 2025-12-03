"""
Integration helpers for Moral Compass apps.

Provides helper functions to:
- Derive table ID
- Manage ChallengeManager lifecycle
- Sync user and team state
- Compute user ranks
- Build leaderboard and widget HTML for apps

This version includes:
- Host-based table ID derivation (_derive_table_id)
- ChallengeManager factory using MoralcompassApiClient
- Cached list_users fetch for ranks (fetch_cached_users)
- Rank computation (get_user_ranks)
- Minimal HTML builders: build_moral_leaderboard_html and get_moral_compass_widget_html
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

from aimodelshare.moral_compass import MoralcompassApiClient
from aimodelshare.moral_compass.challenge import ChallengeManager

logger = logging.getLogger("aimodelshare.moral_compass.apps.helpers")

# Local caches
_leaderboard_cache: Dict[str, Dict[str, Any]] = {}
_LEADERBOARD_TTL_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))


def _cache_get(key: str) -> Optional[List[Dict[str, Any]]]:
    entry = _leaderboard_cache.get(key)
    if not entry:
        return None
    if (time.time() - entry.get("_ts", 0)) > _LEADERBOARD_TTL_SECONDS:
        try:
            del _leaderboard_cache[key]
        except Exception:
            pass
        return None
    return entry.get("data")


def _cache_set(key: str, data: List[Dict[str, Any]]) -> None:
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


def get_challenge_manager(username: str, auth_token: Optional[str] = None) -> Optional[ChallengeManager]:
    """
    Create or retrieve a ChallengeManager for the given user.

    Uses derived table_id and MoralcompassApiClient. If auth_token is provided,
    the client will attach it to requests (recommended when AUTH_ENABLED=true).
    """
    try:
        table_id = _derive_table_id()
        api_base_url = os.environ.get("MORAL_COMPASS_API_BASE_URL")
        client = MoralcompassApiClient(api_base_url=api_base_url, auth_token=auth_token) if api_base_url else MoralcompassApiClient(auth_token=auth_token)
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
        merged = {
            "synced": True,
            "status": "ok",
            "local_preview": cm.get_local_score(),
        }
        # Merge server payload keys if present (e.g., moralCompassScore)
        if isinstance(result, dict):
            merged.update(result)
        return merged
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
    cached = _cache_get(table_id)
    if cached is not None:
        return cached

    client = MoralcompassApiClient(api_base_url=os.environ.get("MORAL_COMPASS_API_BASE_URL"))
    resp = client.list_users(table_id, limit=100)
    users = resp.get("users", []) if isinstance(resp, dict) else []

    # Normalize fields and fallback
    normalized: List[Dict[str, Any]] = []
    for u in users:
        normalized.append({
            "username": u.get("username"),
            "moralCompassScore": u.get("moralCompassScore", u.get("totalCount", 0)),
            "submissionCount": u.get("submissionCount", 0),
            "totalCount": u.get("totalCount", 0),
            "teamName": u.get("teamName")
        })

    _cache_set(table_id, normalized)
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
    sorted_users = sorted(users, key=lambda x: (float(x.get("moralCompassScore", 0) or 0.0), x.get("submissionCount", 0)), reverse=True)

    individual_rank = None
    moral_score = None
    user_team = None

    for idx, u in enumerate(sorted_users, start=1):
        if u.get("username") == username:
            individual_rank = idx
            try:
                moral_score = float(u.get("moralCompassScore", 0) or 0.0)
            except Exception:
                moral_score = None
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
            try:
                score = float(u.get("moralCompassScore", 0) or 0.0)
            except Exception:
                score = 0.0
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


def build_moral_leaderboard_html(table_id: Optional[str] = None, max_entries: Optional[int] = 20) -> str:
    """
    Build a simple leaderboard HTML from list_users data sorted by moralCompassScore.
    """
    table_id = table_id or _derive_table_id()
    users = fetch_cached_users(table_id)
    if max_entries is not None:
        users = users[:max_entries]

    rows = []
    for idx, u in enumerate(users, start=1):
        uname = u.get("username") or ""
        score = u.get("moralCompassScore", 0)
        try:
            score_float = float(score or 0.0)
        except Exception:
            score_float = 0.0
        rows.append(f"<tr><td>{idx}</td><td>{uname}</td><td>{score_float:.4f}</td></tr>")

    html = f"""
    <div class="mc-leaderboard">
      <h3>Moral Compass Leaderboard</h3>
      <table>
        <thead><tr><th>#</th><th>User</th><th>Score</th></tr></thead>
        <tbody>
          {''.join(rows) if rows else '<tr><td colspan="3">No users yet</td></tr>'}
        </tbody>
      </table>
    </div>
    """
    return html


def get_moral_compass_widget_html(username: str, table_id: Optional[str] = None) -> str:
    """
    Build a minimal widget HTML showing the user's current moral compass score and rank.
    """
    table_id = table_id or _derive_table_id()
    ranks = get_user_ranks(username=username, table_id=table_id)

    rank_text = f"#{ranks['individual_rank']}" if ranks.get("individual_rank") is not None else "N/A"
    score = ranks.get("moral_compass_score")
    score_text = f"{score:.4f}" if isinstance(score, (int, float)) else "N/A"

    html = f"""
    <div class="mc-widget">
      <p><strong>User:</strong> {username}</p>
      <p><strong>Rank:</strong> {rank_text}</p>
      <p><strong>Moral Compass Score:</strong> {score_text}</p>
    </div>
    """
    return html

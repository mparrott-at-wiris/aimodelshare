import os
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

from aimodelshare.moral_compass import MoralcompassApiClient, NotFoundError, ApiClientError
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
    Derive Moral Compass table ID in the same way as the comprehensive integration test:

    Priority:
    - If TEST_TABLE_ID is provided, use it as-is.
    - Else derive from TEST_PLAYGROUND_URL or PLAYGROUND_URL:
      Use the last non-empty path segment and append '-mc'.

    This matches tests/test_moral_compass_comprehensive_integration.py behavior so the app
    reads/writes the same shared table.
    """
    explicit = os.environ.get("TEST_TABLE_ID")
    if explicit and explicit.strip():
        return explicit.strip()

    # Prefer TEST_PLAYGROUND_URL for parity with the integration test, fallback to PLAYGROUND_URL
    pg_url = os.environ.get("TEST_PLAYGROUND_URL") or os.environ.get(
        "PLAYGROUND_URL",
        "https://example.com/playground/shared-comprehensive"
    )
    try:
        parts = [p for p in urlparse(pg_url).path.split("/") if p]
        playground_id = parts[-1] if parts else "shared-comprehensive"
        return f"{playground_id}-mc"
    except Exception as e:
        logger.warning(f"Failed to derive table ID from playground URL '{pg_url}': {e}")
        return "shared-comprehensive-mc"


def _ensure_table_exists(client: MoralcompassApiClient, table_id: str, playground_url: Optional[str] = None) -> None:
    """
    Ensure the table exists by mirroring the integration test's behavior.
    If not found, create it with a display name and playground_url metadata.
    """
    try:
        client.get_table(table_id)
        return
    except NotFoundError:
        pass
    except ApiClientError as e:
        logger.info(f"get_table error (will attempt create): {e}")
    except Exception as e:
        logger.info(f"Unexpected get_table error (will attempt create): {e}")

    payload = {
        "table_id": table_id,
        "display_name": "Moral Compass Integration Test - Shared Table",
        "playground_url": playground_url or os.environ.get("TEST_PLAYGROUND_URL") or os.environ.get("PLAYGROUND_URL"),
    }
    try:
        client.create_table(**payload)
        # optional brief delay is handled in tests; here we rely on backend immediacy
        logger.info(f"Created Moral Compass table: {table_id}")
    except Exception as e:
        logger.warning(f"Failed to create Moral Compass table '{table_id}': {e}")


def get_challenge_manager(username: str, auth_token: Optional[str] = None) -> Optional[ChallengeManager]:
    """
    Create or retrieve a ChallengeManager for the given user.

    Uses derived table_id and MoralcompassApiClient. Ensures the table exists first
    to avoid missing-rank issues.
    """
    try:
        table_id = _derive_table_id()
        api_base_url = os.environ.get("MORAL_COMPASS_API_BASE_URL")
        client = MoralcompassApiClient(api_base_url=api_base_url, auth_token=auth_token) if api_base_url else MoralcompassApiClient(auth_token=auth_token)

        # Ensure table exists (matches integration-test behavior)
        _ensure_table_exists(client, table_id, playground_url=os.environ.get("TEST_PLAYGROUND_URL") or os.environ.get("PLAYGROUND_URL"))

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

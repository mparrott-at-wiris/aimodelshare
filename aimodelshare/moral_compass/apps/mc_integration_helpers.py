"""
Moral Compass Integration Helpers for Activities 7, 8, and 9.

This module provides helper functions for integrating the Moral Compass scoring system
into Ethics/Game apps, including:
- ChallengeManager initialization and management
- Debounced server synchronization
- Team aggregation logic
- Leaderboard generation with caching

Design Rationale:
- Client-side only scoring combination logic (server stores single moralCompassScore)
- Debounce prevents excessive API calls while providing responsive UI
- Team synthetic users (prefix: team:) enable team leaderboards
- Local preview fallback ensures graceful degradation when debounced or offline

Server Constraints:
- Only existing API endpoints available (no custom metadata fields)
- All combination logic handled client-side
- Primary metric stored as moralCompassScore in server
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger("aimodelshare.moral_compass.apps")


# ============================================================================
# Constants
# ============================================================================

TEAM_USERNAME_PREFIX = "team:"


# ============================================================================
# Environment Configuration
# ============================================================================

def get_env_config() -> Dict[str, Any]:
    """
    Get environment configuration for Moral Compass integration.
    
    Returns:
        Dictionary with configuration values
    """
    return {
        # Debounce settings
        'DEBOUNCE_SECONDS': int(os.getenv('MC_DEBOUNCE_SECONDS', '5')),
        
        # Scoring mode: 'product' or 'sum'
        'SCORING_MODE': os.getenv('MC_SCORING_MODE', 'product'),
        
        # Weights for sum mode
        'WEIGHT_ACCURACY': float(os.getenv('MC_WEIGHT_ACC', '0.6')),
        'WEIGHT_MORAL': float(os.getenv('MC_WEIGHT_MORAL', '0.4')),
        
        # Normalization settings
        'ACCURACY_FLOOR': float(os.getenv('MC_ACCURACY_FLOOR', '0.0')),
        'MAX_MORAL_POINTS': int(os.getenv('MAX_MORAL_POINTS', '1000')),
        
        # Cache TTL for leaderboard
        'CACHE_TTL_SECONDS': int(os.getenv('MC_CACHE_TTL', '30')),
    }


# ============================================================================
# Debounce State Management
# ============================================================================

# Global state for debounce tracking
_last_sync_times: Dict[str, float] = {}


def should_sync(username: str, override: bool = False) -> bool:
    """
    Check if sync should proceed based on debounce logic.
    
    Args:
        username: The username to check
        override: If True, bypass debounce check (for Force Sync)
        
    Returns:
        True if sync should proceed, False if debounced
    """
    if override:
        return True
    
    config = get_env_config()
    debounce_seconds = config['DEBOUNCE_SECONDS']
    
    last_sync = _last_sync_times.get(username, 0)
    current_time = time.time()
    
    return (current_time - last_sync) >= debounce_seconds


def mark_synced(username: str) -> None:
    """
    Mark a username as having been synced.
    
    Args:
        username: The username that was synced
    """
    _last_sync_times[username] = time.time()


# ============================================================================
# ChallengeManager Initialization
# ============================================================================

def get_challenge_manager(username: str, table_id: Optional[str] = None) -> Optional['ChallengeManager']:
    """
    Get or create a ChallengeManager for a user.
    
    Args:
        username: The username
        table_id: Optional table ID (auto-derived if not provided)
        
    Returns:
        ChallengeManager instance, or None if user not signed in
        
    Note:
        Requires aimodelshare.moral_compass.challenge.ChallengeManager
    """
    if not username or username.lower() == 'guest':
        logger.debug("Cannot create ChallengeManager for guest user")
        return None
    
    try:
        from aimodelshare.moral_compass.challenge import ChallengeManager
        from aimodelshare.moral_compass.api_client import MoralcompassApiClient
        
        # Auto-derive table_id if not provided
        if not table_id:
            table_id = _derive_table_id()
        
        # Create API client and ChallengeManager
        api_client = MoralcompassApiClient()
        cm = ChallengeManager(
            table_id=table_id,
            username=username,
            api_client=api_client
        )
        
        logger.info(f"Created ChallengeManager for user={username}, table={table_id}")
        return cm
        
    except Exception as e:
        logger.error(f"Failed to create ChallengeManager: {e}")
        return None


def _derive_table_id() -> str:
    """
    Auto-derive table ID from environment or use default.
    
    Returns:
        Table ID string
    """
    # Check for explicit table ID
    table_id = os.getenv('MORAL_COMPASS_TABLE_ID')
    if table_id:
        return table_id
    
    # Try to derive from playground URL
    playground_url = os.getenv('PLAYGROUND_URL')
    if playground_url:
        # Extract playground ID and append -mc suffix
        from urllib.parse import urlparse
        parsed = urlparse(playground_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        for i, part in enumerate(path_parts):
            if part.lower() in ['playground', 'playgrounds']:
                if i + 1 < len(path_parts):
                    playground_id = path_parts[i + 1]
                    return f"{playground_id}-mc"
        
        # Fallback to last path component
        if path_parts:
            return f"{path_parts[-1]}-mc"
    
    # Default fallback
    return "justice-equity-challenge-mc"


# ============================================================================
# Scoring Logic
# ============================================================================

def compute_combined_score(accuracy: float, moral_points: int, 
                           config: Optional[Dict[str, Any]] = None) -> float:
    """
    Compute combined ethical + accuracy score.
    
    Args:
        accuracy: Accuracy value (0.0 to 1.0)
        moral_points: Raw moral compass points
        config: Optional config dict (uses env defaults if None)
        
    Returns:
        Combined score as float
        
    Note:
        All combination logic is client-side. Server receives only the
        final combined score as the primary metric (moralCompassScore).
    """
    if config is None:
        config = get_env_config()
    
    # Apply accuracy floor
    accuracy_floor = config['ACCURACY_FLOOR']
    accuracy = max(accuracy, accuracy_floor)
    
    # Normalize moral points (0 to 1)
    max_moral = config['MAX_MORAL_POINTS']
    moral_normalized = min(moral_points / max_moral, 1.0) if max_moral > 0 else 0.0
    
    # Compute combined score based on mode
    scoring_mode = config['SCORING_MODE']
    
    if scoring_mode == 'product':
        # Product mode: accuracy * moral_normalized
        combined = accuracy * moral_normalized
    elif scoring_mode == 'sum':
        # Weighted sum mode
        weight_acc = config['WEIGHT_ACCURACY']
        weight_moral = config['WEIGHT_MORAL']
        combined = (weight_acc * accuracy) + (weight_moral * moral_normalized)
    else:
        logger.warning(f"Unknown scoring mode '{scoring_mode}', defaulting to product")
        combined = accuracy * moral_normalized
    
    logger.debug(
        f"Combined score: accuracy={accuracy:.4f}, moral_points={moral_points}, "
        f"moral_norm={moral_normalized:.4f}, mode={scoring_mode}, result={combined:.4f}"
    )
    
    return combined


# ============================================================================
# User Sync
# ============================================================================

def sync_user_moral_state(
    cm: 'ChallengeManager',
    moral_points: int,
    accuracy: Optional[float] = None,
    override: bool = False
) -> Dict[str, Any]:
    """
    Sync user's moral state to server with debounce.
    
    Args:
        cm: ChallengeManager instance
        moral_points: Current moral compass points for this activity
        accuracy: Optional accuracy value (fetched from playground if None)
        override: If True, bypass debounce (for Force Sync button)
        
    Returns:
        Dictionary with sync result:
        - 'synced': bool (True if actually synced, False if debounced)
        - 'status': str ('synced', 'debounced', 'error')
        - 'server_score': float (if synced)
        - 'local_preview': float (always present)
        - 'message': str (user-facing message)
        
    Design Note:
        - Seeds ChallengeManager with playground accuracy if not provided
        - Computes combined score (accuracy * moral_normalized) client-side
        - Stores combined score as primary metric on server
        - Respects debounce unless override=True
    """
    username = cm.username
    
    # Check debounce
    if not should_sync(username, override=override):
        local_preview = compute_combined_score(
            accuracy or 0.7,  # Default accuracy for preview
            moral_points
        )
        return {
            'synced': False,
            'status': 'debounced',
            'local_preview': local_preview,
            'message': f'Sync pending (debounced). Local preview: {local_preview:.4f}'
        }
    
    try:
        # Fetch accuracy from playground if not provided
        if accuracy is None:
            accuracy = _fetch_playground_accuracy(username)
        
        # Compute combined score
        combined_score = compute_combined_score(accuracy, moral_points)
        
        # Update ChallengeManager metrics
        cm.set_metric('accuracy', accuracy, primary=False)
        cm.set_metric('moral_points', moral_points, primary=False)
        cm.set_metric('combined_score', combined_score, primary=True)
        
        # Sync to server
        response = cm.sync()
        
        # Mark as synced
        mark_synced(username)
        
        server_score = response.get('moralCompassScore', combined_score)
        
        logger.info(
            f"User sync successful: username={username}, moral_points={moral_points}, "
            f"accuracy={accuracy:.4f}, combined={combined_score:.4f}, "
            f"server_score={server_score:.4f}"
        )
        
        return {
            'synced': True,
            'status': 'synced',
            'server_score': server_score,
            'local_preview': combined_score,
            'message': f'✓ Synced! Server score: {server_score:.4f}'
        }
        
    except Exception as e:
        logger.error(f"User sync failed for {username}: {e}")
        local_preview = compute_combined_score(accuracy or 0.7, moral_points)
        return {
            'synced': False,
            'status': 'error',
            'local_preview': local_preview,
            'error': str(e),
            'message': f'⚠️ Sync error. Local preview: {local_preview:.4f}'
        }


def _fetch_playground_accuracy(username: str) -> float:
    """
    Fetch user's accuracy from playground leaderboard.
    
    Args:
        username: The username
        
    Returns:
        Accuracy value (0.0 to 1.0), defaults to 0.7 if not found
        
    Note:
        Uses playground.get_leaderboard() to fetch accuracy data
    """
    try:
        from aimodelshare.playground import Competition
        
        playground_url = os.getenv('PLAYGROUND_URL', 
                                   'https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m')
        
        playground = Competition(playground_url)
        leaderboard = playground.get_leaderboard()
        
        # Find user's entry
        for entry in leaderboard:
            if entry.get('username') == username or entry.get('user') == username:
                # Get accuracy (might be stored as 'accuracy', 'score', or 'test_accuracy')
                accuracy = (
                    entry.get('accuracy') or 
                    entry.get('test_accuracy') or 
                    entry.get('score', 0.7)
                )
                logger.debug(f"Fetched accuracy for {username}: {accuracy}")
                return float(accuracy)
        
        logger.warning(f"User {username} not found in leaderboard, using default 0.7")
        return 0.7
        
    except Exception as e:
        logger.error(f"Failed to fetch playground accuracy: {e}")
        return 0.7


# ============================================================================
# Team Sync
# ============================================================================

def sync_team_state(team_name: str, table_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync team aggregated state to server.
    
    Args:
        team_name: The team name
        table_id: Optional table ID (auto-derived if not provided)
        
    Returns:
        Dictionary with sync result (same structure as sync_user_moral_state)
        
    Design Note:
        - Aggregates member accuracy from playground.get_leaderboard()
        - Aggregates member moral scores from moral_compass.list_users()
        - Computes team combined score (avg_accuracy * avg_moral_norm)
        - Persists as synthetic user with username = 'team:<TeamName>'
    """
    if not team_name:
        return {
            'synced': False,
            'status': 'error',
            'message': 'No team name provided'
        }
    
    try:
        # Auto-derive table_id if not provided
        if not table_id:
            table_id = _derive_table_id()
        
        # Get team members and their data
        team_data = _aggregate_team_data(team_name, table_id)
        
        if not team_data['members']:
            logger.warning(f"No team members found for team '{team_name}'")
            return {
                'synced': False,
                'status': 'error',
                'message': f'No members found for team {team_name}'
            }
        
        # Compute team combined score
        avg_accuracy = team_data['avg_accuracy']
        avg_moral_points = team_data['avg_moral_points']
        
        combined_score = compute_combined_score(avg_accuracy, int(avg_moral_points))
        
        # Create synthetic team user
        from aimodelshare.moral_compass.api_client import MoralcompassApiClient
        
        api_client = MoralcompassApiClient()
        team_username = f"{TEAM_USERNAME_PREFIX}{team_name}"
        
        # Update team entry
        response = api_client.update_moral_compass(
            table_id=table_id,
            username=team_username,
            metrics={
                'accuracy': avg_accuracy,
                'moral_points': avg_moral_points,
                'combined_score': combined_score,
                'member_count': len(team_data['members'])
            },
            tasks_completed=0,
            total_tasks=0,
            questions_correct=0,
            total_questions=0,
            primary_metric='combined_score'
        )
        
        server_score = response.get('moralCompassScore', combined_score)
        
        logger.info(
            f"Team sync successful: team={team_name}, members={len(team_data['members'])}, "
            f"avg_accuracy={avg_accuracy:.4f}, avg_moral={avg_moral_points:.1f}, "
            f"combined={combined_score:.4f}, server_score={server_score:.4f}"
        )
        
        return {
            'synced': True,
            'status': 'synced',
            'server_score': server_score,
            'local_preview': combined_score,
            'message': f'✓ Team synced! Score: {server_score:.4f}'
        }
        
    except Exception as e:
        logger.error(f"Team sync failed for '{team_name}': {e}")
        return {
            'synced': False,
            'status': 'error',
            'error': str(e),
            'message': f'⚠️ Team sync error: {str(e)}'
        }


def _aggregate_team_data(team_name: str, table_id: str) -> Dict[str, Any]:
    """
    Aggregate data for all team members.
    
    Args:
        team_name: The team name
        table_id: The table ID
        
    Returns:
        Dictionary with:
        - 'members': List of member usernames
        - 'avg_accuracy': Average accuracy across members
        - 'avg_moral_points': Average moral points across members
    """
    try:
        # Get team members from environment or use heuristic
        team_members = _get_team_members(team_name)
        
        if not team_members:
            logger.warning(f"No team members configured for team '{team_name}'")
            return {'members': [], 'avg_accuracy': 0.0, 'avg_moral_points': 0.0}
        
        # Fetch accuracy data from playground
        accuracy_data = _fetch_team_accuracy_data(team_members)
        
        # Fetch moral compass data
        moral_data = _fetch_team_moral_data(team_members, table_id)
        
        # Compute averages
        valid_members = set(accuracy_data.keys()) & set(moral_data.keys())
        
        if not valid_members:
            return {'members': [], 'avg_accuracy': 0.0, 'avg_moral_points': 0.0}
        
        avg_accuracy = sum(accuracy_data[m] for m in valid_members) / len(valid_members)
        avg_moral = sum(moral_data[m] for m in valid_members) / len(valid_members)
        
        return {
            'members': list(valid_members),
            'avg_accuracy': avg_accuracy,
            'avg_moral_points': avg_moral
        }
        
    except Exception as e:
        logger.error(f"Failed to aggregate team data: {e}")
        return {'members': [], 'avg_accuracy': 0.0, 'avg_moral_points': 0.0}


def _get_team_members(team_name: str) -> List[str]:
    """
    Get list of team members.
    
    Args:
        team_name: The team name
        
    Returns:
        List of member usernames
        
    Note:
        Currently reads from TEAM_MEMBERS environment variable (comma-separated).
        Future enhancement: read from team registry or user profiles.
    """
    # Check environment variable
    members_str = os.getenv('TEAM_MEMBERS', '')
    if members_str:
        return [m.strip() for m in members_str.split(',') if m.strip()]
    
    # Fallback: try to infer from current user
    username = os.getenv('username')
    if username:
        return [username]
    
    return []


def _fetch_team_accuracy_data(members: List[str]) -> Dict[str, float]:
    """
    Fetch accuracy data for team members from playground.
    
    Args:
        members: List of member usernames
        
    Returns:
        Dictionary mapping username -> accuracy
    """
    try:
        from aimodelshare.playground import Competition
        
        playground_url = os.getenv('PLAYGROUND_URL',
                                   'https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m')
        
        playground = Competition(playground_url)
        leaderboard = playground.get_leaderboard()
        
        accuracy_data = {}
        for entry in leaderboard:
            username = entry.get('username') or entry.get('user')
            if username in members:
                accuracy = (
                    entry.get('accuracy') or
                    entry.get('test_accuracy') or
                    entry.get('score', 0.7)
                )
                accuracy_data[username] = float(accuracy)
        
        return accuracy_data
        
    except Exception as e:
        logger.error(f"Failed to fetch team accuracy data: {e}")
        return {}


def _fetch_team_moral_data(members: List[str], table_id: str) -> Dict[str, float]:
    """
    Fetch moral compass data for team members.
    
    Args:
        members: List of member usernames
        table_id: The table ID
        
    Returns:
        Dictionary mapping username -> moral_points
    """
    try:
        from aimodelshare.moral_compass.api_client import MoralcompassApiClient
        
        api_client = MoralcompassApiClient()
        
        moral_data = {}
        for username in members:
            try:
                user_stats = api_client.get_user(table_id, username)
                # Extract moral points from moralCompassScore (reverse normalization estimate)
                # This is an approximation; ideally we'd store raw points separately
                moral_score = user_stats.total_count if hasattr(user_stats, 'total_count') else 0
                moral_data[username] = float(moral_score)
            except Exception as e:
                logger.debug(f"Could not fetch moral data for {username}: {e}")
                continue
        
        return moral_data
        
    except Exception as e:
        logger.error(f"Failed to fetch team moral data: {e}")
        return {}


# ============================================================================
# Leaderboard Cache & Generation
# ============================================================================

# Global cache for leaderboard data
_leaderboard_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}


def fetch_cached_users(table_id: Optional[str] = None, ttl: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch users from moral compass table with caching.
    
    Args:
        table_id: Optional table ID (auto-derived if not provided)
        ttl: Cache TTL in seconds (default: 30)
        
    Returns:
        List of user dictionaries with fields:
        - 'username': str
        - 'moralCompassScore': float
        - 'submissionCount': int (if available)
        - 'totalCount': int (if available)
        - 'teamName': str (if available)
    """
    if not table_id:
        table_id = _derive_table_id()
    
    # Check cache
    cache_key = table_id
    if cache_key in _leaderboard_cache:
        cache_time, cached_data = _leaderboard_cache[cache_key]
        if (time.time() - cache_time) < ttl:
            logger.debug(f"Using cached leaderboard for table {table_id}")
            return cached_data
    
    # Fetch from API using raw list_users to get moralCompassScore
    try:
        from aimodelshare.moral_compass.api_client import MoralcompassApiClient
        
        api_client = MoralcompassApiClient()
        
        # Use list_users with pagination to get raw data including moralCompassScore
        user_list = []
        last_key = None
        
        while True:
            response = api_client.list_users(table_id, limit=100, last_key=last_key)
            users = response.get("users", [])
            
            for user_data in users:
                user_list.append({
                    'username': user_data.get("username"),
                    'moralCompassScore': user_data.get("moralCompassScore", user_data.get("totalCount", 0)),
                    'submissionCount': user_data.get("submissionCount", 0),
                    'totalCount': user_data.get("totalCount", 0),
                    'teamName': user_data.get("teamName")
                })
            
            last_key = response.get("lastKey")
            if not last_key:
                break
        
        # Update cache
        _leaderboard_cache[cache_key] = (time.time(), user_list)
        
        logger.info(f"Fetched {len(user_list)} users for table {table_id}")
        return user_list
        
    except Exception as e:
        logger.error(f"Failed to fetch users for leaderboard: {e}")
        return []


def get_user_ranks(username: str, table_id: Optional[str] = None, team_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get user's individual and team ranks from moral compass leaderboard.
    
    Args:
        username: The username
        table_id: Optional table ID (auto-derived if not provided)
        team_name: Optional team name to get team rank
        
    Returns:
        Dictionary with:
        - 'individual_rank': int or None
        - 'team_rank': int or None
        - 'moral_compass_score': float or None
    """
    try:
        users = fetch_cached_users(table_id, ttl=5)  # Short TTL for rank queries
        
        if not users:
            return {'individual_rank': None, 'team_rank': None, 'moral_compass_score': None}
        
        # Separate individual users from team synthetic users
        individual_users = [u for u in users if not u['username'].startswith(TEAM_USERNAME_PREFIX)]
        team_users = [u for u in users if u['username'].startswith(TEAM_USERNAME_PREFIX)]
        
        # Sort individual users by moralCompassScore descending for individual ranking
        individual_users_sorted = sorted(individual_users, key=lambda u: u['moralCompassScore'], reverse=True)
        
        # Find individual rank (only among individual users, not teams)
        individual_rank = None
        moral_compass_score = None
        for rank, user in enumerate(individual_users_sorted, start=1):
            if user['username'] == username:
                individual_rank = rank
                moral_compass_score = user['moralCompassScore']
                break
        
        # Find team rank if team_name provided
        team_rank = None
        if team_name:
            # Sort team users by moralCompassScore descending for team ranking
            team_users_sorted = sorted(team_users, key=lambda u: u['moralCompassScore'], reverse=True)
            for rank, user in enumerate(team_users_sorted, start=1):
                team_display_name = user['username'][len(TEAM_USERNAME_PREFIX):]  # Remove prefix
                if team_display_name == team_name:
                    team_rank = rank
                    break
        
        return {
            'individual_rank': individual_rank,
            'team_rank': team_rank,
            'moral_compass_score': moral_compass_score
        }
        
    except Exception as e:
        logger.error(f"Failed to get user ranks for {username}: {e}")
        return {'individual_rank': None, 'team_rank': None, 'moral_compass_score': None}


def build_moral_leaderboard_html(
    highlight_username: Optional[str] = None,
    include_teams: bool = True,
    table_id: Optional[str] = None,
    max_entries: int = 20
) -> str:
    """
    Build HTML for moral compass leaderboard.
    
    Args:
        highlight_username: Username to highlight (current user)
        include_teams: If True, include team entries
        table_id: Optional table ID (auto-derived if not provided)
        max_entries: Maximum number of entries to display
        
    Returns:
        HTML string with leaderboard table
        
    Note:
        Uses same styling classes as model_building_game:
        - leaderboard-html-table
        - user-row-highlight
    """
    users = fetch_cached_users(table_id)
    
    if not users:
        return """
        <div style='text-align: center; padding: 40px; color: var(--text-muted);'>
            <p>No leaderboard data available yet.</p>
            <p>Complete activities and sync to appear on the leaderboard!</p>
        </div>
        """
    
    # Filter teams if needed
    if not include_teams:
        users = [u for u in users if not u['username'].startswith(TEAM_USERNAME_PREFIX)]
    
    # Sort by moralCompassScore descending
    users_sorted = sorted(users, key=lambda u: u['moralCompassScore'], reverse=True)
    users_sorted = users_sorted[:max_entries]
    
    # Build HTML
    html = """
    <table class='leaderboard-html-table'>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Name</th>
                <th>Moral Compass Score</th>
                <th>Type</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for rank, user in enumerate(users_sorted, start=1):
        username = user['username']
        score = user['moralCompassScore']
        
        is_team = username.startswith(TEAM_USERNAME_PREFIX)
        display_name = username[len(TEAM_USERNAME_PREFIX):] if is_team else username  # Remove prefix
        entry_type = '👥 Team' if is_team else '👤 User'
        
        # Highlight current user
        highlight = username == highlight_username
        row_class = "class='user-row-highlight'" if highlight else ""
        
        html += f"""
            <tr {row_class}>
                <td>{rank}</td>
                <td>{display_name}</td>
                <td>{score:.4f}</td>
                <td>{entry_type}</td>
            </tr>
        """
    
    html += """
        </tbody>
    </table>
    """
    
    return html


# ============================================================================
# Convenience Functions
# ============================================================================

def get_moral_compass_widget_html(
    local_points: int,
    server_score: Optional[float] = None,
    is_synced: bool = False
) -> str:
    """
    Generate HTML for Moral Compass widget.
    
    Args:
        local_points: Local moral points accumulated
        server_score: Server moral compass score (if synced)
        is_synced: Whether currently synced
        
    Returns:
        HTML string for widget display
    """
    status_icon = "✓" if is_synced else "⏳"
    status_text = "(synced)" if is_synced else "(pending)"
    
    html = f"""
    <div style='background: var(--block-background-fill); padding: 16px; border-radius: 8px; 
                border: 2px solid var(--accent-strong); margin: 16px 0;'>
        <h3 style='margin-top: 0;'>🧭 Moral Compass Score</h3>
        <div style='display: flex; justify-content: space-around; flex-wrap: wrap;'>
            <div style='text-align: center; margin: 10px;'>
                <div style='font-size: 0.9rem; color: var(--text-muted);'>Local Points</div>
                <div style='font-size: 2rem; font-weight: bold; color: var(--accent-strong);'>
                    {local_points}
                </div>
            </div>
    """
    
    if server_score is not None:
        html += f"""
            <div style='text-align: center; margin: 10px;'>
                <div style='font-size: 0.9rem; color: var(--text-muted);'>Server Score {status_icon}</div>
                <div style='font-size: 2rem; font-weight: bold; color: var(--accent-strong);'>
                    {server_score:.4f}
                </div>
                <div style='font-size: 0.8rem; color: var(--text-muted);'>{status_text}</div>
            </div>
        """
    
    html += """
        </div>
    </div>
    """
    
    return html

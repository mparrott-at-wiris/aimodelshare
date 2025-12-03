"""
Bias Detective V2 - Comprehensive AI Bias Investigation Module

This app teaches participants how to identify, measure, and diagnose bias in AI systems
through a 21-slide interactive investigation covering:

PHASE I: THE SETUP (Slides 1-2) - Onboarding and mission briefing
PHASE II: THE TOOLKIT (Slides 3-5) - Ethical framework and methodology  
PHASE III: DATASET FORENSICS (Slides 6-10) - Input analysis for bias
PHASE IV: FAIRNESS AUDIT (Slides 11-18) - Performance analysis and disparities
PHASE V: THE VERDICT (Slides 19-21) - Diagnosis and next steps

Features:
- 21 Multiple Choice tasks integrated with Moral Compass scoring
- Lightweight UX with toast notifications, gauge animations, and delta pills
- Rank refreshes at checkpoints (after slides 10 and 18)
- Team integration via mc_integration_helpers
- Follows shared_activity_styles.css patterns
"""

import os
import logging
import random
import time
import threading
import pandas as pd
from typing import Dict, Any, Optional, Tuple

try:
    import gradio as gr
except ImportError:
    gr = None

# Import moral compass integration helpers
from .mc_integration_helpers import (
    get_challenge_manager,
    sync_user_moral_state,
    sync_team_state,
    build_moral_leaderboard_html,
    get_moral_compass_widget_html,
    get_user_ranks,
    _derive_table_id,
)

# Import playground and AWS utilities
try:
    from aimodelshare.playground import Competition
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    # Mock/Pass if not available locally
    pass

# Removed session_auth in favor of request-based sessionid extraction (Cloud Run multi-session safe).
# from .session_auth import (
#     create_session_state,
#     authenticate_session,
#     get_session_username,
#     get_session_token,
#     is_session_authenticated,
#     get_session_team,
#     set_session_team,
# )

logger = logging.getLogger("aimodelshare.moral_compass.apps.bias_detective_v2")

# ============================================================================
# Data & Constants
# ============================================================================

OEIAC_PRINCIPLES = [
    "Justice & Fairness",
    "Non-maleficence",
    "Autonomy",
    "Beneficence",
    "Explainability",
    "Responsibility",
    "Privacy"
]

DEMOGRAPHICS_DATA = {
    "race": {
        "Group A": 51,
        "Group B": 32,
        "Other": 17
    },
    "gender": {
        "Male": 81,
        "Female": 19
    },
    "age": {
        "Under 35": 68,
        "35-50": 22,
        "Over 50": 10
    }
}

FAIRNESS_METRICS = {
    "race": {
        "Group A": {"fp_rate": 45, "fn_rate": 28},
        "Group B": {"fp_rate": 23, "fn_rate": 48}
    },
    "gender": {
        "Female": {"severity_bias": "High risk for minor offenses"},
        "Male": {"severity_bias": "Lower"}
    },
    "age": {
        "Under 35": {"estimation": "Over-estimated"},
        "Over 50": {"estimation": "Under-estimated (missed flags)"}
    },
    "geography": {
        "High-density urban": {"proxy_correlation": "High FP rate correlation with race"}
    }
}

TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]


# ============================================================================
# Translation Configuration (i18n scaffold)
# ============================================================================
TRANSLATIONS = {
    "en": {
        "title": "🕵️ Bias Detective: The Investigation",
        "loading": "⏳ Loading...",
    }
    # Future: Add 'es' and 'ca' translations
}

def t(lang: str, key: str, **kwargs) -> str:
    """Translation helper function."""
    translation = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    if kwargs:
        return translation.format(**kwargs)
    return translation

# ============================================================================
# Configuration
# ============================================================================
LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES_STR = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES_STR) if MAX_LEADERBOARD_ENTRIES_STR else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

# Bias Detective specific configuration
BIAS_DETECTIVE_TOTAL_TASKS = 21  # Total number of tasks in the Bias Detective 21-slide flow

# ============================================================================
# In-memory caches
# ============================================================================
_cache_lock = threading.Lock()
_leaderboard_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

# ============================================================================
# Helper Functions
# ============================================================================

def _log(msg: str):
    if DEBUG_LOG:
        print(f"[BiasDetectiveApp] {msg}")

def _normalize_team_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(str(name).strip().split())

def _fetch_leaderboard(token: str) -> Optional[pd.DataFrame]:
    """Fetch leaderboard data from playground with caching."""
    now = time.time()
    with _cache_lock:
        if (
            _leaderboard_cache["data"] is not None
            and now - _leaderboard_cache["timestamp"] < LEADERBOARD_CACHE_SECONDS
        ):
            return _leaderboard_cache["data"]

    try:
        playground_id = os.environ.get(
            "PLAYGROUND_URL",
            "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        )
        playground = Competition(playground_id)
        df = playground.get_leaderboard(token=token)
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES is not None:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
    except Exception as e:
        _log(f"Leaderboard fetch failed: {e}")
        df = None

    with _cache_lock:
        _leaderboard_cache["data"] = df
        _leaderboard_cache["timestamp"] = time.time()
    return df

def _get_or_assign_team(username: str, leaderboard_df: Optional[pd.DataFrame]) -> Tuple[str, bool]:
    """Get existing team from leaderboard or assign a new one."""
    try:
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(
                            user_submissions["timestamp"], errors="coerce"
                        )
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                    except Exception as ts_err:
                        _log(f"Timestamp sort error: {ts_err}")
                existing_team = user_submissions.iloc[0]["Team"]
                if pd.notna(existing_team) and str(existing_team).strip():
                    return _normalize_team_name(existing_team), False
        return _normalize_team_name(random.choice(TEAM_NAMES)), True
    except Exception as e:
        _log(f"Team assignment error: {e}")
        return _normalize_team_name(random.choice(TEAM_NAMES)), True

def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    """Authenticate using sessionid from request query params, returning (success, username, token)."""
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id:
            return False, None, None
        token = get_token_from_session(session_id)
        if not token:
            return False, None, None
        username = _get_username_from_token(token)
        if not username:
            return False, None, None
        return True, username, token
    except Exception as e:
        _log(f"Session auth failed: {e}")
        return False, None, None

def _compute_user_stats(username: str, token: str) -> Dict[str, Any]:
    """Compute user stats from leaderboard with caching."""
    now = time.time()
    with _cache_lock:
        cached = _user_stats_cache.get(username)
        if cached and (now - cached.get("_ts", 0) < USER_STATS_TTL):
            return cached

    leaderboard_df = _fetch_leaderboard(token)
    team_name, _ = _get_or_assign_team(username, leaderboard_df)
    best_score = None
    rank = None
    team_rank = None

    try:
        if leaderboard_df is not None and not leaderboard_df.empty:
            if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
                user_submissions = leaderboard_df[leaderboard_df["username"] == username]
                if not user_submissions.empty:
                    best_score = user_submissions["accuracy"].max()

                # Individual rank
                user_bests = leaderboard_df.groupby("username")["accuracy"].max()
                summary_df = user_bests.reset_index()
                summary_df.columns = ["Engineer", "Best_Score"]
                summary_df = summary_df.sort_values("Best_Score", ascending=False).reset_index(drop=True)
                summary_df.index = summary_df.index + 1
                my_row = summary_df[summary_df["Engineer"] == username]
                if not my_row.empty:
                    rank = my_row.index[0]

                # Team rank
                if "Team" in leaderboard_df.columns and team_name:
                    team_summary_df = (
                        leaderboard_df.groupby("Team")["accuracy"]
                        .agg(Best_Score="max")
                        .reset_index()
                        .sort_values("Best_Score", ascending=False)
                        .reset_index(drop=True)
                    )
                    team_summary_df.index = team_summary_df.index + 1
                    my_team_row = team_summary_df[team_summary_df["Team"] == team_name]
                    if not my_team_row.empty:
                        team_rank = my_team_row.index[0]
    except Exception as e:
        _log(f"User stats error for {username}: {e}")

    stats = {
        "username": username,
        "best_score": best_score,
        "rank": rank,
        "team_name": team_name,
        "team_rank": team_rank,
        "is_signed_in": True,
        "_ts": now
    }
    with _cache_lock:
        _user_stats_cache[username] = stats
    return stats

def format_toast_message(message: str) -> str:
    """Format a toast notification message."""
    return f"✓ {message}"

def format_delta_pill(delta: float) -> str:
    """Format a delta pill showing score change."""
    if delta > 0:
        return f"+{delta:.1f}%"
    return f"{delta:.1f}%"

def get_moral_compass_score_html(
    local_points: int,
    max_points: int,
    accuracy: float = 0.0,
    ethical_progress_pct: float = 0.0,
    individual_rank: Optional[int] = None,
    team_rank: Optional[int] = None,
    team_name: Optional[str] = None
) -> str:
    """
    Generate HTML for the Moral Compass Score widget with gauge.
    
    Args:
        local_points: Current points earned
        max_points: Maximum possible points
        accuracy: Current model accuracy (0-1)
        ethical_progress_pct: Ethical progress percentage (0-100)
        individual_rank: Individual rank (if available)
        team_rank: Team rank (if available)
        team_name: Team name (if available)
    
    Returns:
        HTML string with styled widget
    """
    # Ensure ethical progress doesn't exceed 100%
    ethical_progress_pct = min(ethical_progress_pct, 100.0)
    
    combined_score = accuracy * (ethical_progress_pct / 100.0) * 100
    
    html = f"""
    <div class="kpi-card kpi-card--subtle-accent">
        <h3>🧭 YOUR MORAL COMPASS SCORE</h3>
        <div class="kpi-card-body">
            <div class="kpi-metric-box">
                <p class="kpi-label">Combined Score</p>
                <p class="kpi-score">{combined_score:.1f}</p>
            </div>
            <div class="kpi-metric-box">
                <p class="kpi-label">Accuracy</p>
                <p class="kpi-score kpi-score--muted">{accuracy*100:.1f}%</p>
            </div>
            <div class="kpi-metric-box">
                <p class="kpi-label">Ethical Progress</p>
                <p class="kpi-score kpi-score--muted">{ethical_progress_pct:.1f}%</p>
            </div>
        </div>
        <p class="kpi-subtext-muted">{local_points}/{max_points} tasks completed</p>
    """
    
    # Add rank information if available
    if individual_rank is not None:
        html += f"""
        <p class="kpi-subtext-muted">🏆 Individual Rank: #{individual_rank}</p>
        """
    
    if team_name and team_rank is not None:
        html += f"""
        <p class="kpi-subtext-muted">👥 Team '{team_name}' Rank: #{team_rank}</p>
        """
    
    html += """
    </div>
    """
    return html

# ============================================================================
# App Factory
# ============================================================================

def create_bias_detective_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """
    Create the Bias Detective V2 Gradio Blocks app.
    
    This is a comprehensive 21-slide interactive investigation module
    covering bias detection, measurement, and diagnosis in AI systems.
    
    Args:
        theme_primary_hue: Primary color hue for theme (default: "indigo")
    
    Returns:
        Gradio Blocks object ready to launch
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for the bias detective app. Install with `pip install gradio`."
        )
    
    try:
        gr.close_all(verbose=False)
    except Exception:
        pass  # Ignore close_all errors
    
    # ========================================================================
    # State Management
    # ========================================================================
    
    # Track moral compass points and progress
    moral_compass_state = {
        "points": 0,
        "max_points": BIAS_DETECTIVE_TOTAL_TASKS,  # Total tasks in Bias Detective flow
        "accuracy": 0.92,  # Example accuracy from prior model building
        "tasks_completed": 0,
        "checkpoint_reached": [],  # Track which checkpoints hit
        "username": None,  # Username from session
        "token": None,  # Token from session
        "team_name": None,  # Team name from leaderboard
        "team_rank": None,  # Team rank from leaderboard
        "individual_rank": None,  # Individual rank from leaderboard
        "challenge_manager": None  # ChallengeManager instance
    }
    
    # Task answers tracking
    task_answers = {}  # task_id -> answer
    
    # ========================================================================
    # Utility Functions
    # ========================================================================
    
    def calculate_ethical_progress() -> float:
        """Calculate ethical progress percentage, capped at 100%."""
        if moral_compass_state["max_points"] == 0:
            return 0.0
        progress = (moral_compass_state["tasks_completed"] / moral_compass_state["max_points"]) * 100
        # Ensure progress doesn't exceed 100%
        return min(progress, 100.0)
    
    def update_moral_compass_score() -> str:
        """Update and return Moral Compass Score HTML."""
        ethical_pct = calculate_ethical_progress()
        return get_moral_compass_score_html(
            local_points=moral_compass_state["tasks_completed"],
            max_points=moral_compass_state["max_points"],
            accuracy=moral_compass_state["accuracy"],
            ethical_progress_pct=ethical_pct,
            individual_rank=moral_compass_state.get("individual_rank"),
            team_rank=moral_compass_state.get("team_rank"),
            team_name=moral_compass_state.get("team_name")
        )
    
    def log_task_completion(task_id: str, is_correct: bool) -> Tuple[str, str]:
        """
        Log a task completion and return toast + score update.
        
        Syncs progress to moral compass database and includes team updates.
        Prevents duplicate submissions and enforces max task limit.
        
        Returns:
            (toast_message, updated_score_html)
        """
        # Check if we've reached the maximum number of tasks
        if moral_compass_state["tasks_completed"] >= moral_compass_state["max_points"]:
            return "⚠️ Maximum number of tasks already completed.", update_moral_compass_score()
        
        # If using ChallengeManager, check there first for authoritative state
        if moral_compass_state["challenge_manager"] is not None:
            cm = moral_compass_state["challenge_manager"]
            if cm.is_task_completed(task_id):
                # Task already completed in ChallengeManager - sync local state
                if task_id not in task_answers:
                    task_answers[task_id] = True  # Sync local tracking
                return "⚠️ You've already answered this question.", update_moral_compass_score()
        
        # Check local tracking as secondary check
        if task_id in task_answers:
            return "⚠️ You've already answered this question.", update_moral_compass_score()
        
        if is_correct:
            # Try to complete task via ChallengeManager first
            task_newly_completed = False
            if moral_compass_state["challenge_manager"] is not None:
                cm = moral_compass_state["challenge_manager"]
                task_newly_completed = cm.complete_task(task_id)
                
                # Only record locally if ChallengeManager accepted it
                if task_newly_completed:
                    task_answers[task_id] = is_correct
                else:
                    # Task was already completed in ChallengeManager
                    return "⚠️ Task already recorded. No duplicate credit.", update_moral_compass_score()
            else:
                # No ChallengeManager - use local tracking only
                task_answers[task_id] = is_correct
                task_newly_completed = True
            
            if task_newly_completed:
                # Increment tasks completed (with safety check)
                moral_compass_state["tasks_completed"] = min(
                    moral_compass_state["tasks_completed"] + 1,
                    moral_compass_state["max_points"]
                )
            
            delta_per_task = 100.0 / float(moral_compass_state["max_points"]) if moral_compass_state["max_points"] > 0 else 0.0
            
            sync_message = ""
            rank_updated = False
            
            if moral_compass_state["challenge_manager"] is not None:
                try:
                    cm = moral_compass_state["challenge_manager"]
                    
                    # Sync to server
                    sync_result = sync_user_moral_state(
                        cm=cm,
                        moral_points=moral_compass_state["tasks_completed"],
                        accuracy=moral_compass_state["accuracy"]
                    )
                    
                    if sync_result.get("synced"):
                        sync_message = " [Synced to server]"
                        
                        # Update ranks dynamically after syncing using moral compass API
                        if moral_compass_state["username"]:
                            try:
                                # Get ranks from moral compass leaderboard
                                table_id = _derive_table_id()
                                rank_info = get_user_ranks(
                                    username=moral_compass_state["username"],
                                    table_id=table_id,
                                    team_name=moral_compass_state.get("team_name")
                                )
                                
                                if rank_info.get("individual_rank") is not None:
                                    moral_compass_state["individual_rank"] = rank_info["individual_rank"]
                                    rank_updated = True
                                    if DEBUG_LOG:
                                        _log(f"Updated individual rank from Moral Compass: #{rank_info['individual_rank']}")
                                
                                if rank_info.get("team_rank") is not None:
                                    moral_compass_state["team_rank"] = rank_info["team_rank"]
                                    rank_updated = True
                                    if DEBUG_LOG:
                                        _log(f"Updated team rank from Moral Compass: #{rank_info['team_rank']}")
                            except Exception as rank_err:
                                logger.warning(f"Could not update ranks from Moral Compass API: {rank_err}")
                                # Keep last-known ranks instead of falling back to playground
                                if DEBUG_LOG:
                                    _log(f"Keeping last-known Moral Compass ranks: individual=#{moral_compass_state.get('individual_rank')}, team=#{moral_compass_state.get('team_rank')}")
                        
                        # Update team if applicable
                        if moral_compass_state["team_name"]:
                            team_sync_result = sync_team_state(
                                team_name=moral_compass_state["team_name"]
                            )
                            if team_sync_result.get("synced"):
                                sync_message += f" [Team '{moral_compass_state['team_name']}' updated]"
                except Exception as e:
                    logger.warning(f"Failed to sync progress: {e}")
            
            toast = format_toast_message(f"Progress logged. Ethical % +{delta_per_task:.1f}%{sync_message}")
            
            # Show rank if available
            if rank_updated:
                if moral_compass_state.get("individual_rank"):
                    toast += f"\n🏆 Your rank: #{moral_compass_state['individual_rank']}"
                if moral_compass_state["team_name"] and moral_compass_state.get("team_rank"):
                    toast += f"\n👥 Team '{moral_compass_state['team_name']}' rank: #{moral_compass_state['team_rank']}"
            
            score_html = update_moral_compass_score()
            
            return toast, score_html
        else:
            # Incorrect answer - no point gained but still log attempt
            return "Try again - review the material above.", update_moral_compass_score()
    
    def check_checkpoint_refresh(slide_num: int) -> str:
        """
        Check if we should refresh ranks at this slide and return updated stats.
        
        Checkpoints after slides 10 and 18 where ranks are refreshed.
        
        Returns:
            Status message about rank refresh
        """
        if slide_num not in [10, 18]:
            return ""
        
        if moral_compass_state["username"]:
            try:
                # Try moral compass API first
                table_id = _derive_table_id()
                rank_info = get_user_ranks(
                    username=moral_compass_state["username"],
                    table_id=table_id,
                    team_name=moral_compass_state.get("team_name")
                )
                
                if rank_info.get("individual_rank") is not None:
                    moral_compass_state["individual_rank"] = rank_info["individual_rank"]
                
                if rank_info.get("team_rank") is not None:
                    moral_compass_state["team_rank"] = rank_info["team_rank"]
                
                msg = f"🔄 **Checkpoint {slide_num}: Ranks Refreshed!**\n\n"
                
                if moral_compass_state.get("individual_rank"):
                    msg += f"🏆 Your individual rank: **#{moral_compass_state['individual_rank']}**\n\n"
                
                if moral_compass_state.get("team_name") and moral_compass_state.get("team_rank"):
                    msg += f"👥 Your team '{moral_compass_state['team_name']}' rank: **#{moral_compass_state['team_rank']}**\n\n"
                
                moral_compass_state["checkpoint_reached"].append(slide_num)
                
                _log(f"Checkpoint {slide_num} refresh for {moral_compass_state['username']}: rank={moral_compass_state.get('individual_rank')}, team_rank={moral_compass_state.get('team_rank')}")
                
                return msg
            except Exception as e:
                logger.warning(f"Failed to refresh ranks from Moral Compass at checkpoint {slide_num}: {e}")
                
                # Keep last-known ranks and show message
                msg = f"🔄 **Checkpoint {slide_num} reached**\n\n"
                msg += f"⚠️ Rank refresh temporarily unavailable. Showing last-known ranks:\n\n"
                
                if moral_compass_state.get("individual_rank"):
                    msg += f"🏆 Your individual rank: **#{moral_compass_state['individual_rank']}**\n\n"
                
                if moral_compass_state.get("team_name") and moral_compass_state.get("team_rank"):
                    msg += f"👥 Your team '{moral_compass_state['team_name']}' rank: **#{moral_compass_state['team_rank']}**\n\n"
                
                moral_compass_state["checkpoint_reached"].append(slide_num)
                
                if DEBUG_LOG:
                    _log(f"Checkpoint {slide_num} refresh failed, keeping last-known Moral Compass ranks")
                
                return msg
        
        return f"🔄 Checkpoint {slide_num} reached"
    
    def _initialize_user_from_request(request: gr.Request) -> str:
        """
        Initialize user data using sessionid from request (Cloud Run multi-session safe).
        Mirrors the moral_compass_challenge approach.
        """
        try:
            success, username, token = _try_session_based_auth(request)
            if success and username and token and username != "guest":
                user_stats = _compute_user_stats(username, token)
                
                moral_compass_state["username"] = username
                moral_compass_state["token"] = token
                moral_compass_state["team_name"] = user_stats.get("team_name")
                moral_compass_state["team_rank"] = user_stats.get("team_rank")
                moral_compass_state["individual_rank"] = user_stats.get("rank")
                
                if user_stats.get("best_score") is not None:
                    moral_compass_state["accuracy"] = user_stats["best_score"]
                
                try:
                    cm = get_challenge_manager(username)
                    if cm:
                        # Configure for Bias Detective flow
                        cm.set_progress(
                            tasks_completed=moral_compass_state.get("tasks_completed", 0),
                            total_tasks=BIAS_DETECTIVE_TOTAL_TASKS,
                            questions_correct=0,
                            total_questions=0
                        )
                        # Set accuracy as primary metric
                        cm.set_metric('accuracy', moral_compass_state["accuracy"], primary=True)
                        moral_compass_state["challenge_manager"] = cm
                        _log(f"Initialized ChallengeManager for user {username} with 21-task Bias Detective flow, accuracy={moral_compass_state['accuracy']:.4f}")
                    else:
                        logger.warning(f"get_challenge_manager returned None for user {username}")
                except Exception as e:
                    logger.warning(f"Could not initialize ChallengeManager: {e}")
                
                welcome_msg = f"👋 Welcome back, **{username}**!\n\n"
                
                if user_stats.get("best_score") is not None:
                    welcome_msg += f"📊 Your best accuracy: **{user_stats['best_score']*100:.1f}%**\n\n"
                
                if user_stats.get("rank"):
                    welcome_msg += f"🏆 Your individual rank: **#{user_stats['rank']}**\n\n"
                
                if user_stats.get("team_name"):
                    welcome_msg += f"👥 Your team: **{user_stats['team_name']}**\n\n"
                    if user_stats.get("team_rank"):
                        welcome_msg += f"🛡️ Team rank: **#{user_stats['team_rank']}**\n\n"
                
                welcome_msg += "Your progress will be synced to the Moral Compass database as you complete tasks."
                
                _log(f"User initialized: {username}, accuracy={user_stats.get('best_score')}, team={user_stats.get('team_name')}")
                return welcome_msg
            else:
                return "👋 Welcome! You're in guest mode. Sign in to save your progress and join a team."
        except Exception as e:
            logger.error(f"Failed to initialize user data from request: {e}")
            return "⚠️ Could not load user data. Continuing in guest mode."
    
    # ========================================================================
    # Gradio App Layout
    # ========================================================================
    
    css_path = os.path.join(os.path.dirname(__file__), "shared_activity_styles.css")
    try:
        with open(css_path, 'r') as f:
            base_css = f.read()
    except FileNotFoundError:
        logger.warning(f"CSS file not found at {css_path}, using default styles")
        base_css = ""
    
    # Add navigation overlay CSS for slide transitions
    nav_overlay_css = """
    #nav-loading-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: color-mix(in srgb, var(--body-background-fill) 95%, transparent);
        z-index: 9999; display: none; flex-direction: column;
        align-items: center; justify-content: center;
        opacity: 0; transition: opacity 0.3s ease;
    }
    .nav-spinner {
        width: 50px; height: 50px;
        border: 5px solid var(--border-color-primary);
        border-top: 5px solid var(--color-accent);
        border-radius: 50%; animation: nav-spin 1s linear infinite;
        margin-bottom: 20px;
    }
    @keyframes nav-spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    #nav-loading-text {
        font-size: 1.3rem; font-weight: 600; color: var(--color-accent);
    }
    @media (prefers-color-scheme: dark) {
        #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); }
        .nav-spinner {
            border-color: rgba(148, 163, 184, 0.4);
            border-top-color: var(--color-accent);
        }
    }
    """
    css_content = base_css + nav_overlay_css
    
    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue=theme_primary_hue),
        css=css_content,
        title="🕵️ Bias Detective V2: The Investigation"
    ) as app:
        
        # Language state for i18n
        lang_state = gr.State(value="en")
        
        # Top anchor for scroll navigation
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        
        # Navigation loading overlay
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)
        
        # Header
        gr.Markdown("# 🕵️ BIAS DETECTIVE: THE INVESTIGATION")
        gr.Markdown("*An Interactive Module on AI Fairness & Bias Detection*")
        
        # Moral Compass Score Widget (persistent across slides)
        moral_compass_display = gr.HTML(
            value=update_moral_compass_score(),
            label="Moral Compass Score"
        )
        
        # Toast notification area (for feedback)
        toast_notification = gr.Textbox(
            value="",
            visible=False,
            label="Notification"
        )
        
        # Welcome message with user stats
        with gr.Row():
            with gr.Column(scale=3):
                welcome_message = gr.Markdown(
                    value="👋 Welcome! Loading your user data...",
                    label="User Information"
                )
            with gr.Column(scale=1):
                load_user_data_btn = gr.Button("🔄 Load User Data", variant="primary", size="sm")
        
        # Initial load: populate user state from request (sessionid) + parse lang
        def initial_load(request: gr.Request):
            msg = _initialize_user_from_request(request)
            params = request.query_params if request else {}
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS:
                lang = "en"
            return [msg, update_moral_compass_score(), lang]
        
        app.load(
            fn=initial_load,
            inputs=None,
            outputs=[welcome_message, moral_compass_display, lang_state]
        )
        
        # Explicit refresh button: also use request
        def load_user_data_from_request(request: gr.Request):
            msg = _initialize_user_from_request(request)
            return [msg, update_moral_compass_score()]
        
        load_user_data_btn.click(
            fn=load_user_data_from_request,
            inputs=None,
            outputs=[welcome_message, moral_compass_display]
        )
        

        gr.HTML("<hr style='margin:24px 0;'>")
        
        # ========================================================================
        # Navigation Helper Functions
        # ========================================================================
        
        def create_nav_generator(current_step, next_step, all_steps, loading_screen):
            """Generate navigation between slides with loading screen."""
            def navigate():
                # Show loading
                updates = {loading_screen: gr.update(visible=True)}
                for step in all_steps:
                    if step != loading_screen:
                        updates[step] = gr.update(visible=False)
                yield updates
                
                # Show next step
                updates = {next_step: gr.update(visible=True)}
                for step in all_steps:
                    if step != next_step:
                        updates[step] = gr.update(visible=False)
                yield updates
            return navigate
        
        def nav_js(target_id: str, message: str = "Loading...") -> str:
            """JavaScript for overlay animation and scroll."""
            return f"""
            ()=>{{
              try {{
                const overlay = document.getElementById('nav-loading-overlay');
                const messageEl = document.getElementById('nav-loading-text');
                if(overlay && messageEl) {{
                  messageEl.textContent = '{message}';
                  overlay.style.display = 'flex';
                  setTimeout(() => {{ overlay.style.opacity = '1'; }}, 10);
                }}
                setTimeout(() => {{
                  const anchor = document.getElementById('app_top_anchor');
                  if(anchor) anchor.scrollIntoView({{behavior:'smooth', block:'start'}});
                }}, 40);
                const startTime = Date.now();
                const targetId = '{target_id}';
                const pollInterval = setInterval(() => {{
                  const elapsed = Date.now() - startTime;
                  const target = document.getElementById(targetId);
                  const isVisible = target && target.offsetParent !== null;
                  if((isVisible && elapsed >= 1200) || elapsed > 7000) {{
                    clearInterval(pollInterval);
                    if(overlay) {{
                      overlay.style.opacity = '0';
                      setTimeout(() => {{ overlay.style.display = 'none'; }}, 300);
                    }}
                  }}
                }}, 90);
              }} catch(e) {{ console.warn('nav error', e); }}
            }}
            """
        
        # ========================================================================
        # Loading Screen
        # ========================================================================
        
        with gr.Column(visible=False, elem_id="loading") as loading_screen:
            gr.HTML("<div style='text-align:center; padding:100px 0;'><h2 style='font-size:2rem;'>⏳ Loading...</h2></div>")
        
        # ====================================================================
        # PHASE I: THE SETUP (Slides 1-2)
        # ====================================================================
        
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            gr.Markdown("""
            ## 🧭 Meet the Moral Compass
            
            ### Badge: PART 0: SCORE PREVIEW
            
            You will see a **Moral Compass Score** during this experience.
            
            It combines:
            - Your current model accuracy (from prior activities)
            - Your **Ethical Progress %** from short learning tasks
            
            The score may update after small checks; ranks might refresh at checkpoints.
            
            ---
            
            ### Mini Practice
            Tap "Log my first check" below to see a subtle score bump and a tiny toast notification.
            """)
            
            gr.Markdown("#### MC Task #1: Understanding the Moral Compass Score")
            mc1_question = gr.Radio(
                choices=[
                    "It's fixed by accuracy only.",
                    "It may change as Ethical Progress % grows through learning tasks, multiplied by current accuracy.",
                    "It increases just by opening slides."
                ],
                label="Which statement best describes how your Moral Compass Score changes in this module?",
                type="index"
            )
            mc1_submit = gr.Button("Submit Answer")
            mc1_feedback = gr.Markdown("")
            
            def check_mc1(answer_idx):
                if answer_idx == 1:  # Correct answer
                    toast, score_html = log_task_completion("mc1", True)
                    return "✅ Correct! Your score combines accuracy with ethical progress.", toast, score_html
                else:
                    return "❌ Not quite. The score is a combination of accuracy and ethical progress.", "", update_moral_compass_score()
            
            mc1_submit.click(
                fn=check_mc1,
                inputs=[mc1_question],
                outputs=[mc1_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("#### MC Task #2: Test Recording")
            mc2_button = gr.Button("Test Recording")
            mc2_feedback = gr.Markdown("")
            
            def check_mc2():
                toast, score_html = log_task_completion("mc2", True)
                return "✅ Success! Tracker is logging properly. Small bump recorded.", toast, score_html
            
            mc2_button.click(
                fn=check_mc2,
                inputs=[],
                outputs=[mc2_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 2**")
            
            # Navigation
            step_1_next = gr.Button("Next: The Setup ▶️", variant="primary", size="lg")

        
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            gr.Markdown("""
            ## ⚡ TARGET: HIDDEN AI BIAS
            
            ### Role Badge: ACCESS GRANTED: BIAS DETECTIVE
            
            **Mission Brief:**
            > "This AI model may appear neutral, but we suspect it might be unfair. Your mission: 
            > examine whether bias could be present in the training data before the system affects 
            > real people. If we can't detect it, we might not be able to mitigate it."
            
            ---
            
            ### Investigation Roadmap
            
            **Step 1: 🛡️ LEARN THE RULES** (What counts as bias?)  
            **Step 2: 📡 SCAN THE DATA** (Where could bias be?)  
            **Step 3: ⚖️ PROVE THE ERROR** (How unfair is it?)  
            **Step 4: 📝 DIAGNOSE HARM** (File the fairness report)
            
            ---
            """)
            
            gr.Markdown("#### MC Task #3: Investigation Steps")
            mc3_question = gr.Radio(
                choices=[
                    "Scan the Data",
                    "Diagnose Potential Harm",
                    "Assess the Error"
                ],
                label="Which step comes after 'Learn the Rules'?",
                type="index"
            )
            mc3_submit = gr.Button("Submit Answer")
            mc3_feedback = gr.Markdown("")
            
            def check_mc3(answer_idx):
                if answer_idx == 0:  # "Scan the Data"
                    toast, score_html = log_task_completion("mc3", True)
                    return "✅ Correct! After learning the rules, we scan the data.", toast, score_html
                else:
                    return "❌ Review the roadmap above.", "", update_moral_compass_score()
            
            mc3_submit.click(
                fn=check_mc3,
                inputs=[mc3_question],
                outputs=[mc3_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 3**")
            gr.Markdown("▶️ **CTA:** Begin Investigation")
                
                # Navigation
            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Next ▶️", variant="primary", size="lg")

        
        # ====================================================================
        # PHASE II: THE TOOLKIT (Slides 3-5)
        # ====================================================================
        
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            gr.Markdown("""
            ## ⚖️ THE DETECTIVE'S CODE
            
            ### Badge: STEP 1: INTELLIGENCE BRIEFING
            
            We don't guess; we use standards from the **Catalan Observatory for Ethics in AI (OEIAC)**.
            They outline **7 core principles** for safer AI. Our initial signals suggest a concern under **Principle #1**.
            
            ---
            
            ### 7 OEIAC Principles
            
            1. **⚖️ Justice & Fairness** ← *HIGHLIGHTED*
            2. Non-maleficence
            3. Autonomy
            4. Beneficence
            5. Explainability
            6. Responsibility
            7. Privacy
            
            ---
            """)
            
            gr.Markdown("#### MC Task #4: Justice & Fairness")
            mc4_question = gr.Radio(
                choices=[
                    "Prefer speed even if some groups get worse results.",
                    "Treat similar cases similarly unless relevant differences justify distinctions.",
                    "Optimize only for average accuracy."
                ],
                label="Which statement best aligns with Justice & Fairness?",
                type="index"
            )
            mc4_submit = gr.Button("Submit Answer")
            mc4_feedback = gr.Markdown("")
            
            def check_mc4(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc4", True)
                    return "✅ Correct! Justice requires treating similar cases similarly.", toast, score_html
                else:
                    return "❌ Review the principle of Justice & Fairness.", "", update_moral_compass_score()
            
            mc4_submit.click(
                fn=check_mc4,
                inputs=[mc4_question],
                outputs=[mc4_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 4**")
            gr.Markdown("▶️ **CTA:** Initialize Investigation Protocol")
                
                # Navigation
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("Next ▶️", variant="primary", size="lg")

        
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            gr.Markdown("""
            ## ⚠️ THE RISK OF INVISIBLE BIAS
            
            ### Badge: PRINCIPLE #1: JUSTICE & FAIRNESS
            
            **Why is an AI bias investigation important?**
            
            - A judge's bias can be **noticed and challenged**
            - AI bias can be **quiet and hidden**
            - Because the system outputs a clean "Risk Score," some audiences might assume it's **objective**
            - If we don't look closely, discrimination could become **harder to spot or challenge**
            
            ---
            
            ### The Ripple Effect
            
            **1 flawed algorithm** → **10,000 potentially unfair outcomes**
            
            ---
            """)
            
            gr.Markdown("#### MC Task #5: Why AI Bias is Harder to See")
            mc5_question = gr.Radio(
                choices=[
                    "AI systems never make mistakes.",
                    "Outputs appear objective (a clean score), so people might assume neutrality.",
                    "Bias only exists in training, never in outputs."
                ],
                label="Why might AI-related bias be harder to see than a biased judge?",
                type="index"
            )
            mc5_submit = gr.Button("Submit Answer")
            mc5_feedback = gr.Markdown("")
            
            def check_mc5(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc5", True)
                    return "✅ Correct! Clean outputs can mask hidden bias.", toast, score_html
                else:
                    return "❌ Think about how objective AI outputs appear.", "", update_moral_compass_score()
            
            mc5_submit.click(
                fn=check_mc5,
                inputs=[mc5_question],
                outputs=[mc5_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 5**")
            gr.Markdown("▶️ **CTA:** I understand the stakes. Show me how")
                
                # Navigation
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("Next ▶️", variant="primary", size="lg")

        
        with gr.Column(visible=False, elem_id="step-5") as step_5:
            gr.Markdown("""
            ## 🔎 HOW DO WE CATCH A MACHINE?
            
            ### Badge: STEP 2: SCAN EVIDENCE
            
            We can't interrogate an algorithm; we examine the **evidence trail** it leaves.
            
            If you were investigating a suspicious judge, where would you look?
            
            ---
            
            ### Interactive Brainstorm
            
            - **"Who is being arrested?"** → Check the **History**
            - **"Who is being wrongly accused?"** → Check the **Mistakes**
            - **"Who is getting hurt?"** → Check the **Punishment**
            
            ---
            
            ### Expert Validation
            
            ✓ That's the standard audit protocol: **Dataset Forensics & Error Analysis**
            
            ---
            """)
            
            gr.Markdown("#### MC Task #6: Audit Lens")
            mc6_question = gr.Radio(
                choices=[
                    "Check the History",
                    "Check the Mistakes",
                    "Check the Punishment"
                ],
                label="Which lens best surfaces wrongful accusations?",
                type="index"
            )
            mc6_submit = gr.Button("Submit Answer")
            mc6_feedback = gr.Markdown("")
            
            def check_mc6(answer_idx):
                if answer_idx == 1:  # "Check the Mistakes"
                    toast, score_html = log_task_completion("mc6", True)
                    return "✅ Correct! Mistakes reveal wrongful accusations.", toast, score_html
                else:
                    return "❌ Think about where errors show wrongful accusations.", "", update_moral_compass_score()
            
            mc6_submit.click(
                fn=check_mc6,
                inputs=[mc6_question],
                outputs=[mc6_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 6**")
            gr.Markdown("▶️ **CTA:** Protocol confirmed. Start scanning")
                
                # Navigation
            with gr.Row():
                step_5_back = gr.Button("◀️ Back", size="lg")
                step_5_next = gr.Button("Next ▶️", variant="primary", size="lg")

        
        # ====================================================================
        # PHASE III: DATASET FORENSICS (Slides 6-10)
        # ====================================================================
        
        with gr.Column(visible=False, elem_id="step-6") as step_6:
            gr.Markdown("""
            ## 📂 THE DATA FORENSICS BRIEFING
            
            ### Badge: STEP 2: EVIDENCE BRIEFING
            
            You're about to view raw evidence files. The AI might treat this data as **'truth.'**
            
            If policing historically targeted one area, the dataset could **over-represent** that area.
            The model doesn't "know" this is bias—it just sees a pattern.
            
            ---
            
            ### Task: How to Detect Bias in Inputs
            
            **Compare Data vs. Relevant Baselines** and look for distortions:
            - **Over-representation** (frequency bias)
            - **Under-representation** (representation bias)
            
            ---
            """)
            
            gr.Markdown("#### MC Task #7: Baseline Comparison")
            mc7_question = gr.Radio(
                choices=["True", "False"],
                label="We compare the dataset to appropriate baselines to look for over/under-representation.",
                type="index"
            )
            mc7_submit = gr.Button("Submit Answer")
            mc7_feedback = gr.Markdown("")
            
            def check_mc7(answer_idx):
                if answer_idx == 0:  # True
                    toast, score_html = log_task_completion("mc7", True)
                    return "✅ Correct! Baseline comparison reveals distortions.", toast, score_html
                else:
                    return "❌ Review the method above.", "", update_moral_compass_score()
            
            mc7_submit.click(
                fn=check_mc7,
                inputs=[mc7_question],
                outputs=[mc7_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 7**")
            gr.Markdown("▶️ **CTA:** I know what to look for. Open scanner")
                
                # Navigation
            with gr.Row():
                step_6_back = gr.Button("◀️ Back", size="lg")
                step_6_next = gr.Button("Next ▶️", variant="primary", size="lg")

        
        with gr.Column(visible=False, elem_id="step-7") as step_7:
            gr.Markdown(f"""
            ## 🔎 FORENSIC ANALYSIS: RACE
            
            ### Badge: EVIDENCE SCAN: VARIABLE 1 of 3
            
            In this local example, suppose **Group A** is ~12% of the population.  
            If the dataset were balanced, we might expect roughly similar representation.
            
            ---
            
            ### Scan Results
            
            **Group A:** {DEMOGRAPHICS_DATA['race']['Group A']}%  
            **Group B:** {DEMOGRAPHICS_DATA['race']['Group B']}%  
            **Other:** {DEMOGRAPHICS_DATA['race']['Other']}%
            
            ---
            
            ### Detective's Analysis
            
            ⚠️ **~51% is about 4× the local share.**
            
            What's the risk signal?
            
            → This points to **Frequency Bias (over-representation)**.  
            The model could learn patterns that track **exposure** rather than **risk**.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #8: Frequency Bias")
            mc8_question = gr.Radio(
                choices=[
                    "Measurement bias",
                    "Frequency bias (over-representation)",
                    "Label leakage"
                ],
                label="Local share ≈ 12%, dataset ≈ 51%. What's the concern called?",
                type="index"
            )
            mc8_submit = gr.Button("Submit Answer")
            mc8_feedback = gr.Markdown("")
            
            def check_mc8(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc8", True)
                    return "✅ Correct! This is frequency bias from over-representation.", toast, score_html
                else:
                    return "❌ Review the detective's analysis above.", "", update_moral_compass_score()
            
            mc8_submit.click(
                fn=check_mc8,
                inputs=[mc8_question],
                outputs=[mc8_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 8**")
            gr.Markdown("▶️ **CTA:** Log evidence & continue")
                
                # Navigation
            with gr.Row():
                step_7_back = gr.Button("◀️ Back", size="lg")
                step_7_next = gr.Button("Next ▶️", variant="primary", size="lg")

        
        with gr.Column(visible=False, elem_id="step-8") as step_8:
            gr.Markdown(f"""
            ## 🔎 FORENSIC ANALYSIS: GENDER
            
            ### Badge: EVIDENCE SCAN: VARIABLE 2 of 3
            
            We're checking balance. If training data skews heavily toward one gender,
            the model may learn patterns for that group more than others.
            
            ---
            
            ### Scan Results
            
            **Male:** {DEMOGRAPHICS_DATA['gender']['Male']}%  
            **Female:** {DEMOGRAPHICS_DATA['gender']['Female']}%
            
            ---
            
            ### Detective's Analysis
            
            ⚠️ **If training data is ~81% male, how could this affect a female defendant?**
            
            → This suggests **Representation Bias (under-representation)**.  
            The model might miss female-specific patterns.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #9: Representation Bias")
            mc9_question = gr.Radio(
                choices=[
                    "Perfect calibration for women",
                    "Representation bias",
                    "Guaranteed fairness"
                ],
                label="If women are sparse in training data, which risk increases?",
                type="index"
            )
            mc9_submit = gr.Button("Submit Answer")
            mc9_feedback = gr.Markdown("")
            
            def check_mc9(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc9", True)
                    return "✅ Correct! Sparse data leads to representation bias.", toast, score_html
                else:
                    return "❌ Review the detective's analysis.", "", update_moral_compass_score()
            
            mc9_submit.click(
                fn=check_mc9,
                inputs=[mc9_question],
                outputs=[mc9_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 9**")
            gr.Markdown("▶️ **CTA:** Log evidence & continue")
                
                # Navigation
            with gr.Row():
                step_8_back = gr.Button("◀️ Back", size="lg")
                step_8_next = gr.Button("Next ▶️", variant="primary", size="lg")

        
        with gr.Column(visible=False, elem_id="step-9") as step_9:
            gr.Markdown(f"""
            ## 🔎 FORENSIC ANALYSIS: AGE
            
            ### Badge: EVIDENCE SCAN: VARIABLE 3 of 3
            
            Risk can vary with age. If most files are from younger people,
            the model might generalize poorly to older people.
            
            ---
            
            ### Scan Results
            
            **Under 35:** {DEMOGRAPHICS_DATA['age']['Under 35']}%  
            **35-50:** {DEMOGRAPHICS_DATA['age']['35-50']}%  
            **Over 50:** {DEMOGRAPHICS_DATA['age']['Over 50']}%
            
            ---
            
            ### Detective's Analysis
            
            ⚠️ **Heavy skew to <35. How might the model judge a 62-year-old?**
            
            → This signals **Generalization Error**—applying "youth logic" to older cases.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #10: Generalization Error")
            mc10_question = gr.Radio(
                choices=[
                    "Better performance for older groups",
                    "Generalization error to older people",
                    "No change"
                ],
                label="Heavy skew to younger cases can lead to…",
                type="index"
            )
            mc10_submit = gr.Button("Submit Answer")
            mc10_feedback = gr.Markdown("")
            
            def check_mc10(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc10", True)
                    return "✅ Correct! Skewed age data causes generalization errors.", toast, score_html
                else:
                    return "❌ Think about applying youth patterns to older people.", "", update_moral_compass_score()
            
            mc10_submit.click(
                fn=check_mc10,
                inputs=[mc10_question],
                outputs=[mc10_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 10**")
            gr.Markdown("▶️ **CTA:** Log evidence & view summary")
            gr.Markdown("🔄 **CHECKPOINT: Ranks may refresh after this slide**")
                
            # Navigation
            with gr.Row():
                step_9_back = gr.Button("◀️ Back", size="lg")
                step_9_next = gr.Button("Next ▶️", variant="primary", size="lg")
        
        with gr.Column(visible=False, elem_id="step-10") as step_10:
            gr.Markdown("""
            ## 📂 FORENSICS REPORT: SUMMARY
            
            ### Badge: STATUS: STEP 2 COMPLETE
            
            Great work. You examined inputs and found signals of imbalance.
            
            ---
            
            ### Evidence Board
            
            **Finding #1:** Frequency Bias (Over-representation of Group A)  
            **Finding #2:** Representation Bias (Under-representation of females)  
            **Finding #3:** Generalization Error (Age skew toward youth)
            
            ---
            
            ### Deduction
            
            Inputs appear flawed. Next: **test outputs**.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #11: Summary Check")
            mc11_question = gr.CheckboxGroup(
                choices=[
                    "Frequency bias",
                    "Representation bias",
                    "Generalization error",
                    "Label noise (not covered here)"
                ],
                label="Which potential issues did we flag in inputs? (Select all that apply)"
            )
            mc11_submit = gr.Button("Submit Answer")
            mc11_feedback = gr.Markdown("")
            
            def check_mc11(selected):
                correct = {"Frequency bias", "Representation bias", "Generalization error"}
                selected_set = set(selected or [])
                
                if correct.issubset(selected_set) and "Label noise (not covered here)" not in selected_set:
                    toast, score_html = log_task_completion("mc11", True)
                    return "✅ Correct! All three issues were identified.", toast, score_html
                else:
                    return "❌ Review the evidence board above.", "", update_moral_compass_score()
            
            mc11_submit.click(
                fn=check_mc11,
                inputs=[mc11_question],
                outputs=[mc11_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 11**")
            
            checkpoint_refresh_btn = gr.Button("🔄 Refresh Rankings (Checkpoint 10)", variant="secondary")
            checkpoint_refresh_msg = gr.Markdown("")
            
            def do_checkpoint_refresh():
                return check_checkpoint_refresh(10)
            
            checkpoint_refresh_btn.click(
                fn=do_checkpoint_refresh,
                inputs=[],
                outputs=[checkpoint_refresh_msg]
            )
                
                # Navigation
            with gr.Row():
                step_10_back = gr.Button("◀️ Back", size="lg")
                step_10_next = gr.Button("Next: Performance Audit ▶️", variant="primary", size="lg")
            
            gr.Markdown("▶️ **CTA:** Initiate Phase 3: Performance Audit")
        
        # ====================================================================
        # PHASE IV: FAIRNESS AUDIT (Slides 11-19)
        # ====================================================================
        
        with gr.Column(visible=False, elem_id="step-11") as step_11:
            gr.Markdown("""
            ## ⚠️ THE TRAP OF "AVERAGES"
            
            ### Badge: STEP 3: PROVE THE ERROR
            
            A vendor might cite **92% overall accuracy**. Sounds impressive!
            
            But if the dataset is 81% male, the model could perform much better on men than women.
            
            → So a **high average might mask subgroup failures**.
            
            ---
            
            ### Breakdown by Subgroup
            
            The system might be:
            - **Strong** for the majority
            - **Weaker** elsewhere
            
            We need to check performance for **each group**.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #12: Average Accuracy")
            mc12_question = gr.Radio(
                choices=[
                    "Yes",
                    "No",
                    "Only if accuracy > 95%"
                ],
                label="Does high average accuracy guarantee fairness across groups?",
                type="index"
            )
            mc12_submit = gr.Button("Submit Answer")
            mc12_feedback = gr.Markdown("")
            
            def check_mc12(answer_idx):
                if answer_idx == 1:  # "No"
                    toast, score_html = log_task_completion("mc12", True)
                    return "✅ Correct! High average can mask subgroup failures.", toast, score_html
                else:
                    return "❌ Review the trap of averages above.", "", update_moral_compass_score()
            
            mc12_submit.click(
                fn=check_mc12,
                inputs=[mc12_question],
                outputs=[mc12_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 12**")
                
                # Navigation
            with gr.Row():
                step_11_back = gr.Button("◀️ Back", size="lg")
                step_11_next = gr.Button("Next ▶️", variant="primary", size="lg")
            gr.Markdown("▶️ **CTA:** Identify failure type")
        
        with gr.Column(visible=False, elem_id="step-12") as step_12:
            gr.Markdown("""
            ## ⏳ THE POWER OF HINDSIGHT
            
            ### Badge: AUDIT PROTOCOL: GROUND TRUTH VERIFICATION
            
            We compare **Predictions vs. Reality** (historical outcomes).
            
            ---
            
            ### Definitions
            
            **False Positive ("False Alarm"):**  
            - Flagged **High Risk** → Did **not** re-offend  
            - Consequence: Possible wrongful detention
            
            **False Negative ("Missed Target"):**  
            - Flagged **Low Risk** → **Did** re-offend  
            - Consequence: Public safety risk
            
            ---
            
            Next: Analyze **High Risk vs. Reality** (False Positives)
            
            ---
            """)
            
            gr.Markdown("#### MC Task #13: Error Types")
            mc13_question = gr.Radio(
                choices=[
                    "False Positive",
                    "False Negative",
                    "True Positive"
                ],
                label="High risk prediction but no re-offense is a…",
                type="index"
            )
            mc13_submit = gr.Button("Submit Answer")
            mc13_feedback = gr.Markdown("")
            
            def check_mc13(answer_idx):
                if answer_idx == 0:  # "False Positive"
                    toast, score_html = log_task_completion("mc13", True)
                    return "✅ Correct! False alarm = False Positive.", toast, score_html
                else:
                    return "❌ Review the definitions above.", "", update_moral_compass_score()
            
            mc13_submit.click(
                fn=check_mc13,
                inputs=[mc13_question],
                outputs=[mc13_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 13**")
                
                # Navigation
            with gr.Row():
                step_12_back = gr.Button("◀️ Back", size="lg")
                step_12_next = gr.Button("Next ▶️", variant="primary", size="lg")
            gr.Markdown("▶️ **CTA:** Analyze High Risk vs. Reality (False Positives)")
        
        with gr.Column(visible=False, elem_id="step-13") as step_13:
            gr.Markdown(f"""
            ## ⚠️ EVIDENCE FOUND: PUNITIVE BIAS
            
            ### Badge: EVIDENCE LOG: RACIAL DISPARITY
            
            We examined "False Alarms"—people flagged as high risk who did **not** re-offend.
            
            ---
            
            ### Data (Example)
            
            **Group A:** {FAIRNESS_METRICS['race']['Group A']['fp_rate']}% error (false positive rate)  
            **Group B:** {FAIRNESS_METRICS['race']['Group B']['fp_rate']}% error (false positive rate)
            
            ---
            
            ### Insight
            
            ⚠️ This may indicate a **punitive pattern** for Group A.
            
            People in Group A are nearly **2× more likely** to be wrongly labeled "high risk"
            compared to Group B.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #14: Punitive Pattern")
            mc14_question = gr.Radio(
                choices=[
                    "A punitive pattern against Group X",
                    "Only label noise",
                    "Perfect fairness"
                ],
                label="If Group X has a higher False Positive rate than Group Y, this may indicate…",
                type="index"
            )
            mc14_submit = gr.Button("Submit Answer")
            mc14_feedback = gr.Markdown("")
            
            def check_mc14(answer_idx):
                if answer_idx == 0:
                    toast, score_html = log_task_completion("mc14", True)
                    return "✅ Correct! Higher FP rate suggests punitive bias.", toast, score_html
                else:
                    return "❌ Review the insight above.", "", update_moral_compass_score()
            
            mc14_submit.click(
                fn=check_mc14,
                inputs=[mc14_question],
                outputs=[mc14_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 14**")
                
                # Navigation
            with gr.Row():
                step_13_back = gr.Button("◀️ Back", size="lg")
                step_13_next = gr.Button("Next ▶️", variant="primary", size="lg")
            gr.Markdown("▶️ **CTA:** Log punitive error & check False Negatives")
        
        with gr.Column(visible=False, elem_id="step-14") as step_14:
            gr.Markdown(f"""
            ## ⚠️ EVIDENCE FOUND: THE "FREE PASS"
            
            ### Badge: EVIDENCE LOG: RACIAL DISPARITY
            
            Now we look at people labeled "Low Risk" who **did** re-offend.
            
            ---
            
            ### Data (Example)
            
            **Group B:** {FAIRNESS_METRICS['race']['Group B']['fn_rate']}% FN (false negative rate)  
            **Group A:** {FAIRNESS_METRICS['race']['Group A']['fn_rate']}% FN (false negative rate)
            
            ---
            
            ### Insight
            
            ⚠️ This may indicate an **omission pattern** (a "free pass") for Group B.
            
            Group B members who should have been flagged are more likely to be missed.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #15: Omission Pattern")
            mc15_question = gr.Radio(
                choices=[
                    "A punitive pattern",
                    "An omission-type disparity (the 'free pass')",
                    "No disparity"
                ],
                label="If Group Y has more False Negatives than Group X, this may indicate…",
                type="index"
            )
            mc15_submit = gr.Button("Submit Answer")
            mc15_feedback = gr.Markdown("")
            
            def check_mc15(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc15", True)
                    return "✅ Correct! Higher FN rate suggests omission bias.", toast, score_html
                else:
                    return "❌ Review the insight above.", "", update_moral_compass_score()
            
            mc15_submit.click(
                fn=check_mc15,
                inputs=[mc15_question],
                outputs=[mc15_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 15**")
                
                # Navigation
            with gr.Row():
                step_14_back = gr.Button("◀️ Back", size="lg")
                step_14_next = gr.Button("Next ▶️", variant="primary", size="lg")
            gr.Markdown("▶️ **CTA:** Log omission error & analyze Gender")
        
        with gr.Column(visible=False, elem_id="step-15") as step_15:
            gr.Markdown(f"""
            ## ⚠️ EVIDENCE FOUND: SEVERITY BIAS
            
            ### Badge: EVIDENCE LOG: GENDER BIAS
            
            With ~4:1 male-to-female training cases, the model might not capture female patterns well.
            
            ---
            
            ### Data (Example)
            
            Women flagged "High Risk" for **minor crimes** more often than men.
            
            **Observation:** {FAIRNESS_METRICS['gender']['Female']['severity_bias']}
            
            ---
            
            ### Insight
            
            ⚠️ This could reflect a **severity bias pattern**.
            
            The model may over-estimate risk for women committing minor offenses.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #16: Severity Bias")
            mc16_question = gr.Radio(
                choices=[
                    "Perfect thresholding",
                    "A severity bias pattern",
                    "Purely geographic effects"
                ],
                label="Women flagged 'High Risk' more often for minor offenses could reflect…",
                type="index"
            )
            mc16_submit = gr.Button("Submit Answer")
            mc16_feedback = gr.Markdown("")
            
            def check_mc16(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc16", True)
                    return "✅ Correct! This is a severity bias pattern.", toast, score_html
                else:
                    return "❌ Review the insight above.", "", update_moral_compass_score()
            
            mc16_submit.click(
                fn=check_mc16,
                inputs=[mc16_question],
                outputs=[mc16_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 16**")
                
                # Navigation
            with gr.Row():
                step_15_back = gr.Button("◀️ Back", size="lg")
                step_15_next = gr.Button("Next ▶️", variant="primary", size="lg")
            gr.Markdown("▶️ **CTA:** Log severity error & analyze Age")
        
        with gr.Column(visible=False, elem_id="step-16") as step_16:
            gr.Markdown(f"""
            ## ⚠️ EVIDENCE FOUND: ESTIMATION ERROR
            
            ### Badge: EVIDENCE LOG: AGE BIAS
            
            The model may equate "criminal" with "young" and might underestimate older risk.
            
            ---
            
            ### Data (Example)
            
            **Observation:** {FAIRNESS_METRICS['age']['Over 50']['estimation']}
            
            Missed flags among older re-offenders.
            
            ---
            
            ### Insight
            
            ⚠️ This suggests **estimation error** tied to age.
            
            The model learned youth patterns and fails to generalize to older individuals.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #17: Age Estimation Error")
            mc17_question = gr.Radio(
                choices=[
                    "Excellent age calibration",
                    "Estimation error tied to age",
                    "No age effect"
                ],
                label="Missing risk among older groups despite re-offense suggests…",
                type="index"
            )
            mc17_submit = gr.Button("Submit Answer")
            mc17_feedback = gr.Markdown("")
            
            def check_mc17(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc17", True)
                    return "✅ Correct! This is age-related estimation error.", toast, score_html
                else:
                    return "❌ Review the insight above.", "", update_moral_compass_score()
            
            mc17_submit.click(
                fn=check_mc17,
                inputs=[mc17_question],
                outputs=[mc17_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 17**")
                
                # Navigation
            with gr.Row():
                step_16_back = gr.Button("◀️ Back", size="lg")
                step_16_next = gr.Button("Next ▶️", variant="primary", size="lg")
            gr.Markdown("▶️ **CTA:** Log estimation error & check Geography")
        
        with gr.Column(visible=False, elem_id="step-17") as step_17:
            gr.Markdown(f"""
            ## ⚠️ THE "PROXY" PROBLEM
            
            ### Badge: AUDIT TARGET: PROXY VARIABLES
            
            Removing the "Race" column isn't always enough.  
            Features like **Neighborhood** could act as proxies.
            
            ---
            
            ### Data (Example)
            
            **Observation:** {FAIRNESS_METRICS['geography']['High-density urban']['proxy_correlation']}
            
            "High-density urban" ZIP codes show higher FP rates.
            
            ---
            
            ### Insight
            
            ⚠️ A location feature might **stand in for race** (a proxy variable).
            
            Even without direct demographic data, the model can still encode bias.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #18: Proxy Variables")
            mc18_question = gr.Radio(
                choices=[
                    "Harmless feature",
                    "Proxy variable",
                    "Regularizer"
                ],
                label="A location feature that correlates with race may function as a…",
                type="index"
            )
            mc18_submit = gr.Button("Submit Answer")
            mc18_feedback = gr.Markdown("")
            
            def check_mc18(answer_idx):
                if answer_idx == 1:  # "Proxy variable"
                    toast, score_html = log_task_completion("mc18", True)
                    return "✅ Correct! Correlated features can be proxy variables.", toast, score_html
                else:
                    return "❌ Review the proxy problem above.", "", update_moral_compass_score()
            
            mc18_submit.click(
                fn=check_mc18,
                inputs=[mc18_question],
                outputs=[mc18_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 18**")
            gr.Markdown("▶️ **CTA:** Investigation complete. File final report")
            gr.Markdown("🔄 **CHECKPOINT: Ranks may refresh after this slide**")
            
            # Navigation
            with gr.Row():
                step_17_back = gr.Button("◀️ Back", size="lg")
                step_17_next = gr.Button("Next ▶️", variant="primary", size="lg")
        
        with gr.Column(visible=False, elem_id="step-18") as step_18:
            gr.Markdown("""
            ## 📂 AUDIT REPORT: SUMMARY
            
            ### Badge: STATUS: AUDIT COMPLETE
            
            Overall accuracy might look high, but subgroup analysis indicates fairness concerns.
            
            ---
            
            ### Impact Matrix
            
            | Category | Pattern Identified |
            |----------|-------------------|
            | **Race** | Punitive pattern (higher FPs for Group A) |
            | **Gender** | Severity pattern (women over-flagged for minor crimes) |
            | **Age** | Estimation pattern (older risk under-estimated) |
            | **Geography** | Proxy pattern (location correlates with race) |
            
            ---
            
            ### Deduction
            
            You have evidence of potential harm; proceed to **final judgment**.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #19: Fairness vs. Accuracy")
            mc19_question = gr.Radio(
                choices=[
                    "Deploy immediately",
                    "Fairness concerns remain and may require changes",
                    "The audit is final for all contexts"
                ],
                label="Passing 'average accuracy' while failing subgroup checks means…",
                type="index"
            )
            mc19_submit = gr.Button("Submit Answer")
            mc19_feedback = gr.Markdown("")
            
            def check_mc19(answer_idx):
                if answer_idx == 1:
                    toast, score_html = log_task_completion("mc19", True)
                    return "✅ Correct! Fairness concerns require attention despite high average accuracy.", toast, score_html
                else:
                    return "❌ Review the impact matrix above.", "", update_moral_compass_score()
            
            mc19_submit.click(
                fn=check_mc19,
                inputs=[mc19_question],
                outputs=[mc19_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 19**")
            
            checkpoint_refresh_btn_18 = gr.Button("🔄 Refresh Rankings (Checkpoint 18)", variant="secondary")
            checkpoint_refresh_msg_18 = gr.Markdown("")
            
            def do_checkpoint_refresh_18():
                return check_checkpoint_refresh(18)
            
            checkpoint_refresh_btn_18.click(
                fn=do_checkpoint_refresh_18,
                inputs=[],
                outputs=[checkpoint_refresh_msg_18]
            )
                
                # Navigation
            with gr.Row():
                step_18_back = gr.Button("◀️ Back", size="lg")
                step_18_next = gr.Button("Next: Final Verdict ▶️", variant="primary", size="lg")
            
            gr.Markdown("▶️ **CTA:** Open Final Case File & Submit Diagnosis")
        
        # ====================================================================
        # PHASE V: THE VERDICT (Slides 20-21)
        # ====================================================================
        
        with gr.Column(visible=False, elem_id="step-19") as step_19:
            gr.Markdown("""
            ## ⚖️ THE FINAL JUDGMENT
            
            ### Badge: STEP 4: DIAGNOSE HARM
            
            The vendor highlights **92% accuracy** and **efficiency**.  
            You've seen subgroup concerns.
            
            ---
            
            ### Decision Point
            
            What should be done with this AI system?
            
            **A) Authorize Deployment**  
            **B) REJECT & OVERHAUL**  
            **C) Monitor Only**
            
            ---
            
            ### Feedback
            
            **Recommended: REJECT & OVERHAUL**
            
            High accuracy doesn't excuse potential rights violations.  
            The system needs fairness fixes before deployment.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #20: Final Recommendation")
            mc20_question = gr.Radio(
                choices=[
                    "Authorize deployment",
                    "Request overhaul",
                    "Monitor only without changes"
                ],
                label="In this exercise, which outcome is recommended?",
                type="index"
            )
            mc20_submit = gr.Button("Submit Answer")
            mc20_feedback = gr.Markdown("")
            
            def check_mc20(answer_idx):
                if answer_idx == 1:  # "Request overhaul"
                    toast, score_html = log_task_completion("mc20", True)
                    return "✅ Correct! The system needs overhaul for fairness.", toast, score_html
                else:
                    return "❌ Consider the fairness concerns identified.", "", update_moral_compass_score()
            
            mc20_submit.click(
                fn=check_mc20,
                inputs=[mc20_question],
                outputs=[mc20_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 20**")
                
                # Navigation
            with gr.Row():
                step_19_back = gr.Button("◀️ Back", size="lg")
                step_19_next = gr.Button("Next: Mission Debrief ▶️", variant="primary", size="lg")
            gr.Markdown("▶️ **CTA:** Sign & file fairness report")
        
        with gr.Column(visible=False, elem_id="step-20") as step_20:
            gr.Markdown("""
            ## 🏆 EXCELLENT WORK, DETECTIVE
            
            ### Badge: PART 1 COMPLETE: BIAS DETECTED
            
            You surfaced fairness risks and documented potential harm.
            
            A diagnosis is a **starting point**. The court still needs a working, safer system.
            
            ---
            
            ### New Assignment: Promotion to Fairness Engineer
            
            **Roadmap:**
            
            1. Remove demographics (where appropriate)
            2. Reduce proxies
            3. Develop guidelines
            4. Continuous improvement
            
            ---
            
            ### Your Journey Continues
            
            Your current **Moral Compass Score** will carry into the next activity.
            
            ---
            """)
            
            gr.Markdown("#### MC Task #21: Score Continuity")
            mc21_question = gr.Radio(
                choices=["True", "False"],
                label="Your current Moral Compass Score will carry into the next activity.",
                type="index"
            )
            mc21_submit = gr.Button("Submit Answer")
            mc21_feedback = gr.Markdown("")
            
            def check_mc21(answer_idx):
                if answer_idx == 0:  # True
                    toast, score_html = log_task_completion("mc21", True)
                    return "✅ Correct! Your progress continues to the next activity.", toast, score_html
                else:
                    return "❌ Your score does carry forward.", "", update_moral_compass_score()
            
            mc21_submit.click(
                fn=check_mc21,
                inputs=[mc21_question],
                outputs=[mc21_feedback, toast_notification, moral_compass_display]
            )
            
            gr.Markdown("**Running MC total: 21**")
                
            # Navigation
            with gr.Row():
                step_20_back = gr.Button("◀️ Back", size="lg")
                step_20_next = gr.Button("Next: Summary ▶️", variant="primary", size="lg")
            
            gr.Markdown("---")
            gr.Markdown("### 🎓 Mission Complete")
            gr.Markdown("⬇️ Scroll to begin next activity ⬇️")

        
        with gr.Column(visible=False, elem_id="step-21") as step_21:
            gr.Markdown("## Your Investigation Summary")
            
            summary_button = gr.Button("Generate Summary Report")
            summary_output = gr.Markdown("")
            
            def generate_summary():
                ethical_pct = calculate_ethical_progress()
                combined = moral_compass_state["accuracy"] * (ethical_pct / 100.0) * 100
                
                report = f"""
                ## Investigation Complete ✅
                
                **Tasks Completed:** {moral_compass_state['tasks_completed']}/{moral_compass_state['max_points']}
                
                **Ethical Progress:** {ethical_pct:.1f}%
                
                **Model Accuracy:** {moral_compass_state['accuracy']*100:.1f}%
                
                **Combined Moral Compass Score:** {combined:.1f}
                
                ---
                
                ### Key Learnings
                
                ✓ **Phase I:** Understood the mission and scoring system  
                ✓ **Phase II:** Learned the OEIAC framework and audit methodology  
                ✓ **Phase III:** Identified frequency, representation, and generalization biases in data  
                ✓ **Phase IV:** Analyzed disparate impact across race, gender, age, and geography  
                ✓ **Phase V:** Recommended system overhaul for fairness
                
                ---
                
                ### Next Steps
                
                Your Moral Compass Score is saved and will carry into the next activity.
                Continue your journey to become a Fairness Engineer!
                """
                
                return report
            
            summary_button.click(
                fn=generate_summary,
                inputs=[],
                outputs=[summary_output]
            )
            
            # Navigation
            step_21_back = gr.Button("◀️ Back to Mission Debrief", size="lg")
        
        # Button wiring for rank refresh already defined in slides 10 and 18
        

        # ========================================================================
        # Navigation Button Wiring
        # ========================================================================
        
        # Collect all step columns for navigation
        all_steps = [
            loading_screen, step_1, step_2, step_3, step_4, step_5,
            step_6, step_7, step_8, step_9, step_10, step_11,
            step_12, step_13, step_14, step_15, step_16, step_17,
            step_18, step_19, step_20, step_21
        ]
        
        # Wire Step 1
        step_1_next.click(
            fn=create_nav_generator(step_1, step_2, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-2", "Loading...")
        )
        
        # Wire Step 2
        step_2_back.click(
            fn=create_nav_generator(step_2, step_1, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-1", "Loading...")
        )
        step_2_next.click(
            fn=create_nav_generator(step_2, step_3, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-3", "Loading...")
        )
        
        # Wire Step 3
        step_3_back.click(
            fn=create_nav_generator(step_3, step_2, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-2", "Loading...")
        )
        step_3_next.click(
            fn=create_nav_generator(step_3, step_4, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-4", "Loading...")
        )
        
        # Wire Step 4
        step_4_back.click(
            fn=create_nav_generator(step_4, step_3, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-3", "Loading...")
        )
        step_4_next.click(
            fn=create_nav_generator(step_4, step_5, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-5", "Loading...")
        )
        
        # Wire Step 5
        step_5_back.click(
            fn=create_nav_generator(step_5, step_4, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-4", "Loading...")
        )
        step_5_next.click(
            fn=create_nav_generator(step_5, step_6, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-6", "Loading...")
        )
        
        # Wire Step 6
        step_6_back.click(
            fn=create_nav_generator(step_6, step_5, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-5", "Loading...")
        )
        step_6_next.click(
            fn=create_nav_generator(step_6, step_7, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-7", "Loading...")
        )
        
        # Wire Step 7
        step_7_back.click(
            fn=create_nav_generator(step_7, step_6, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-6", "Loading...")
        )
        step_7_next.click(
            fn=create_nav_generator(step_7, step_8, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-8", "Loading...")
        )
        
        # Wire Step 8
        step_8_back.click(
            fn=create_nav_generator(step_8, step_7, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-7", "Loading...")
        )
        step_8_next.click(
            fn=create_nav_generator(step_8, step_9, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-9", "Loading...")
        )
        
        # Wire Step 9
        step_9_back.click(
            fn=create_nav_generator(step_9, step_8, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-8", "Loading...")
        )
        step_9_next.click(
            fn=create_nav_generator(step_9, step_10, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-10", "Loading...")
        )
        

        # Wire Step 10
        step_10_back.click(
            fn=create_nav_generator(step_10, step_9, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-9", "Loading...")
        )
        step_10_next.click(
            fn=create_nav_generator(step_10, step_11, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-11", "Loading...")
        )
        
        # Wire Step 11
        step_11_back.click(
            fn=create_nav_generator(step_11, step_10, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-10", "Loading...")
        )
        step_11_next.click(
            fn=create_nav_generator(step_11, step_12, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-12", "Loading...")
        )
        
        # Wire Step 12
        step_12_back.click(
            fn=create_nav_generator(step_12, step_11, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-11", "Loading...")
        )
        step_12_next.click(
            fn=create_nav_generator(step_12, step_13, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-13", "Loading...")
        )
        
        # Wire Step 13
        step_13_back.click(
            fn=create_nav_generator(step_13, step_12, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-12", "Loading...")
        )
        step_13_next.click(
            fn=create_nav_generator(step_13, step_14, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-14", "Loading...")
        )
        
        # Wire Step 14
        step_14_back.click(
            fn=create_nav_generator(step_14, step_13, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-13", "Loading...")
        )
        step_14_next.click(
            fn=create_nav_generator(step_14, step_15, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-15", "Loading...")
        )
        
        # Wire Step 15
        step_15_back.click(
            fn=create_nav_generator(step_15, step_14, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-14", "Loading...")
        )
        step_15_next.click(
            fn=create_nav_generator(step_15, step_16, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-16", "Loading...")
        )
        
        # Wire Step 16
        step_16_back.click(
            fn=create_nav_generator(step_16, step_15, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-15", "Loading...")
        )
        step_16_next.click(
            fn=create_nav_generator(step_16, step_17, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-17", "Loading...")
        )
        
        # Wire Step 17
        step_17_back.click(
            fn=create_nav_generator(step_17, step_16, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-16", "Loading...")
        )
        step_17_next.click(
            fn=create_nav_generator(step_17, step_18, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-18", "Loading...")
        )
        
        # Wire Step 18
        step_18_back.click(
            fn=create_nav_generator(step_18, step_17, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-17", "Loading...")
        )
        step_18_next.click(
            fn=create_nav_generator(step_18, step_19, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-19", "Loading...")
        )
        
        # Wire Step 19
        step_19_back.click(
            fn=create_nav_generator(step_19, step_18, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-18", "Loading...")
        )
        step_19_next.click(
            fn=create_nav_generator(step_19, step_20, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-20", "Loading...")
        )
        
        # Wire Step 20
        step_20_back.click(
            fn=create_nav_generator(step_20, step_19, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-19", "Loading...")
        )
        step_20_next.click(
            fn=create_nav_generator(step_20, step_21, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-21", "Loading...")
        )
        
        # Wire Step 21 (final slide)
        step_21_back.click(
            fn=create_nav_generator(step_21, step_20, all_steps, loading_screen),
            outputs=all_steps,
            js=nav_js("step-20", "Loading...")
        )


    return app


def launch_bias_detective_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    """
    Launch the Bias Detective V2 app.
    
    Args:
        share: Whether to create a public link
        server_name: Server hostname
        server_port: Server port
        theme_primary_hue: Primary color hue
        **kwargs: Additional Gradio launch arguments
    """
    app = create_bias_detective_app(theme_primary_hue=theme_primary_hue)
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        **kwargs
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    launch_bias_detective_app(share=False)

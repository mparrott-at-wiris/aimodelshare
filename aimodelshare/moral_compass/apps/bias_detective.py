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

# Import moral compass integration helpers
from .mc_integration_helpers import (
    get_challenge_manager,
    sync_user_moral_state,
    sync_team_state,
    build_moral_leaderboard_html,
    get_moral_compass_widget_html,
)

# Import playground and AWS utilities
try:
    from aimodelshare.playground import Competition
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    # Mock/Pass if not available locally
    pass

# Import session-based authentication
from .session_auth import (
    create_session_state,
    authenticate_session,
    get_session_username,
    get_session_token,
    is_session_authenticated,
    get_session_team,
    set_session_team,
)

logger = logging.getLogger("aimodelshare.moral_compass.apps.bias_detective_v2")

# ============================================================================
# Data & Constants
# ============================================================================

# OEIAC Principles for reference
OEIAC_PRINCIPLES = [
    "Justice & Fairness",
    "Non-maleficence",
    "Autonomy",
    "Beneficence",
    "Explainability",
    "Responsibility",
    "Privacy"
]

# Simulated demographic data from COMPAS-like dataset
DEMOGRAPHICS_DATA = {
    "race": {
        "Group A": 51,  # Over-represented (local ~12%)
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

# Simulated fairness metrics showing disparities
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

# Team names for assignment
TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]

# ============================================================================
# Configuration
# ============================================================================
LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES_STR = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES_STR) if MAX_LEADERBOARD_ENTRIES_STR else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

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
    """Try to authenticate using session-based authentication."""
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
    ethical_progress_pct: float = 0.0
) -> str:
    """
    Generate HTML for the Moral Compass Score widget with gauge.
    
    Args:
        local_points: Current points earned
        max_points: Maximum possible points
        accuracy: Current model accuracy (0-1)
        ethical_progress_pct: Ethical progress percentage (0-100)
    
    Returns:
        HTML string with styled widget
    """
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
    </div>
    """
    return html


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
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the bias detective app. Install with `pip install gradio`."
        ) from e
    
    # ========================================================================
    # State Management
    # ========================================================================
    
    # Track moral compass points and progress
    moral_compass_state = {
        "points": 0,
        "max_points": 21,  # 21 MC tasks total
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
        """Calculate ethical progress percentage."""
        return (moral_compass_state["tasks_completed"] / moral_compass_state["max_points"]) * 100
    
    def update_moral_compass_score() -> str:
        """Update and return Moral Compass Score HTML."""
        ethical_pct = calculate_ethical_progress()
        return get_moral_compass_score_html(
            local_points=moral_compass_state["tasks_completed"],
            max_points=moral_compass_state["max_points"],
            accuracy=moral_compass_state["accuracy"],
            ethical_progress_pct=ethical_pct
        )
    
    def log_task_completion(task_id: str, is_correct: bool) -> Tuple[str, str]:
        """
        Log a task completion and return toast + score update.
        
        Syncs progress to moral compass database and includes team updates.
        
        Returns:
            (toast_message, updated_score_html)
        """
        task_answers[task_id] = is_correct
        
        if is_correct:
            moral_compass_state["tasks_completed"] += 1
            # Calculate the percentage increase per task (100% / max_points)
            delta_per_task = 100.0 / float(moral_compass_state["max_points"])
            
            # Sync to moral compass database if user is authenticated
            sync_message = ""
            if moral_compass_state["challenge_manager"] is not None:
                try:
                    # Sync user moral state
                    sync_result = sync_user_moral_state(
                        cm=moral_compass_state["challenge_manager"],
                        moral_points=moral_compass_state["tasks_completed"],
                        accuracy=moral_compass_state["accuracy"]
                    )
                    
                    if sync_result.get("synced"):
                        sync_message = " [Synced to server]"
                        
                        # Also sync team state if team is assigned
                        if moral_compass_state["team_name"]:
                            team_sync_result = sync_team_state(
                                team_name=moral_compass_state["team_name"]
                            )
                            if team_sync_result.get("synced"):
                                sync_message += f" [Team '{moral_compass_state['team_name']}' updated]"
                except Exception as e:
                    logger.warning(f"Failed to sync progress: {e}")
            
            # Build toast message with team info
            toast = format_toast_message(f"Progress logged. Ethical % +{delta_per_task:.1f}%{sync_message}")
            
            # Add team information to the toast if available
            if moral_compass_state["team_name"] and moral_compass_state["team_rank"]:
                toast += f"\n👥 Your team '{moral_compass_state['team_name']}' is ranked #{moral_compass_state['team_rank']}"
            
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
        # Checkpoints after slides 10 and 18
        if slide_num not in [10, 18]:
            return ""
        
        # Refresh user stats if authenticated
        if moral_compass_state["username"] and moral_compass_state["token"]:
            try:
                # Clear cache to force refresh
                with _cache_lock:
                    _user_stats_cache.pop(moral_compass_state["username"], None)
                
                # Fetch updated stats
                updated_stats = _compute_user_stats(
                    moral_compass_state["username"],
                    moral_compass_state["token"]
                )
                
                # Update state
                moral_compass_state["team_rank"] = updated_stats.get("team_rank")
                moral_compass_state["individual_rank"] = updated_stats.get("rank")
                
                # Build refresh message
                msg = f"🔄 **Checkpoint {slide_num}: Ranks Refreshed!**\n\n"
                
                if updated_stats.get("rank"):
                    msg += f"🏆 Your individual rank: **#{updated_stats['rank']}**\n\n"
                
                if updated_stats.get("team_name") and updated_stats.get("team_rank"):
                    msg += f"👥 Your team '{updated_stats['team_name']}' rank: **#{updated_stats['team_rank']}**\n\n"
                
                moral_compass_state["checkpoint_reached"].append(slide_num)
                
                _log(f"Checkpoint {slide_num} refresh for {moral_compass_state['username']}: rank={updated_stats.get('rank')}, team_rank={updated_stats.get('team_rank')}")
                
                return msg
            except Exception as e:
                logger.warning(f"Failed to refresh ranks at checkpoint {slide_num}: {e}")
                return f"🔄 Checkpoint {slide_num} reached (refresh pending)"
        
        return f"🔄 Checkpoint {slide_num} reached"
    
    def initialize_user_data_from_session(session_state_val: Dict[str, Any]) -> str:
        """
        Initialize user data from playground leaderboard using session state.
        
        This function:
        1. Uses session state to get username and token
        2. Fetches their latest accuracy score from playground leaderboard
        3. Gets their team assignment from the leaderboard
        4. Initializes ChallengeManager for moral compass database
        5. Returns welcome message with user stats
        
        Args:
            session_state_val: Session state dictionary with auth info
            
        Returns:
            Welcome message string
        """
        try:
            # Get username and token from session state
            username = session_state_val.get("username")
            token = session_state_val.get("token")
            
            if username and token and username != "guest":
                # Compute user stats from leaderboard
                user_stats = _compute_user_stats(username, token)
                
                # Update state with user information
                moral_compass_state["username"] = username
                moral_compass_state["token"] = token
                moral_compass_state["team_name"] = user_stats.get("team_name")
                moral_compass_state["team_rank"] = user_stats.get("team_rank")
                moral_compass_state["individual_rank"] = user_stats.get("rank")
                
                # Update accuracy from leaderboard if available
                if user_stats.get("best_score") is not None:
                    moral_compass_state["accuracy"] = user_stats["best_score"]
                
                # Initialize ChallengeManager for moral compass database
                try:
                    cm = get_challenge_manager(username)
                    moral_compass_state["challenge_manager"] = cm
                    _log(f"Initialized ChallengeManager for user {username}")
                except Exception as e:
                    logger.warning(f"Could not initialize ChallengeManager: {e}")
                
                # Build welcome message
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
                # Guest mode
                return "👋 Welcome! You're in guest mode. Sign in to save your progress and join a team."
                
        except Exception as e:
            logger.error(f"Failed to initialize user data: {e}")
            return "⚠️ Could not load user data. Continuing in guest mode."
    
    def authenticate_and_load_user_data(request: "gr.Request", session_state_val: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Authenticate user from request and update session state, then load user data.
        
        Args:
            request: Gradio request object
            session_state_val: Current session state
            
        Returns:
            Tuple of (welcome_message, updated_session_state)
        """
        try:
            # Try session-based authentication from request
            success, username, token = _try_session_based_auth(request)
            
            if success and username:
                # Update session state
                session_state_val = authenticate_session(
                    session_state_val,
                    username=username,
                    token=token
                )
                
                # Load user data
                welcome_msg = initialize_user_data_from_session(session_state_val)
                return welcome_msg, session_state_val
            else:
                return "👋 Welcome! You're in guest mode. Sign in to save your progress and join a team.", session_state_val
                
        except Exception as e:
            logger.error(f"Failed to authenticate and load user data: {e}")
            return "⚠️ Could not authenticate. Continuing in guest mode.", session_state_val
    
    # ========================================================================
    # Gradio App Layout
    # ========================================================================
    
    # Load CSS from shared styles
    css_path = os.path.join(os.path.dirname(__file__), "shared_activity_styles.css")
    try:
        with open(css_path, 'r') as f:
            css_content = f.read()
    except FileNotFoundError:
        logger.warning(f"CSS file not found at {css_path}, using default styles")
        css_content = ""
    
    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue=theme_primary_hue),
        css=css_content,
        title="🕵️ Bias Detective V2: The Investigation"
    ) as app:
        
        # Session state
        session_state = gr.State(create_session_state())
        
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
        welcome_message = gr.Markdown(
            value="👋 Welcome! Click 'Load User Data' to authenticate and see your stats.",
            label="User Information"
        )
        
        # Button to trigger user data loading
        load_user_data_btn = gr.Button("🔄 Load User Data", variant="secondary", size="sm")
        
        # ====================================================================
        # PHASE I: THE SETUP (Slides 1-2)
        # ====================================================================
        
        with gr.Tab("📋 Part 0: Score Preview (Slide 1)"):
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
            
            # MC Task #1
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
            
            # MC Task #2
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
        
        with gr.Tab("⚡ The Setup (Slide 2)"):
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
            
            # MC Task #3
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
        
        # ====================================================================
        # PHASE II: THE TOOLKIT (Slides 3-5)
        # ====================================================================
        
        with gr.Tab("⚖️ The Detective's Code (Slide 3)"):
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
            
            # MC Task #4
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
        
        with gr.Tab("⚠️ The Stakes (Slide 4)"):
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
            
            # MC Task #5
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
        
        with gr.Tab("🔎 The Detective's Method (Slide 5)"):
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
            
            # MC Task #6
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
        
        # ====================================================================
        # PHASE III: DATASET FORENSICS (Slides 6-10)
        # ====================================================================
        
        with gr.Tab("📂 Data Forensics Briefing (Slide 6)"):
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
            
            # MC Task #7
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
        
        with gr.Tab("🔎 Evidence Scan: Race (Slide 7)"):
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
            
            # MC Task #8
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
        
        with gr.Tab("🔎 Evidence Scan: Gender (Slide 8)"):
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
            
            # MC Task #9
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
        
        with gr.Tab("🔎 Evidence Scan: Age (Slide 9)"):
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
            
            # MC Task #10
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
        
        with gr.Tab("📂 Forensics Conclusion (Slide 10)"):
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
            
            # MC Task #11
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
                selected_set = set(selected)
                
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
            
            # Checkpoint refresh component
            checkpoint_refresh_btn = gr.Button("🔄 Refresh Rankings (Checkpoint 10)", variant="secondary")
            checkpoint_refresh_msg = gr.Markdown("")
            
            def do_checkpoint_refresh():
                return check_checkpoint_refresh(10)
            
            checkpoint_refresh_btn.click(
                fn=do_checkpoint_refresh,
                inputs=[],
                outputs=[checkpoint_refresh_msg]
            )
            
            gr.Markdown("▶️ **CTA:** Initiate Phase 3: Performance Audit")
        
        # ====================================================================
        # PHASE IV: FAIRNESS AUDIT (Slides 11-19)
        # ====================================================================
        
        with gr.Tab("⚠️ The Audit Briefing (Slide 11)"):
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
            
            # MC Task #12
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
            gr.Markdown("▶️ **CTA:** Identify failure type")
        
        with gr.Tab("⏳ The Truth Serum (Slide 12)"):
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
            
            # MC Task #13
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
            gr.Markdown("▶️ **CTA:** Analyze High Risk vs. Reality (False Positives)")
        
        with gr.Tab("⚠️ Audit: False Positives (Slide 13)"):
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
            
            # MC Task #14
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
            gr.Markdown("▶️ **CTA:** Log punitive error & check False Negatives")
        
        with gr.Tab("⚠️ Audit: False Negatives (Slide 14)"):
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
            
            # MC Task #15
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
            gr.Markdown("▶️ **CTA:** Log omission error & analyze Gender")
        
        with gr.Tab("⚠️ Audit: Gender (Slide 15)"):
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
            
            # MC Task #16
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
            gr.Markdown("▶️ **CTA:** Log severity error & analyze Age")
        
        with gr.Tab("⚠️ Audit: Age (Slide 16)"):
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
            
            # MC Task #17
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
            gr.Markdown("▶️ **CTA:** Log estimation error & check Geography")
        
        with gr.Tab("⚠️ Audit: Geography (Slide 17)"):
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
            
            # MC Task #18
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
        
        with gr.Tab("📂 Audit Conclusion (Slide 18)"):
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
            
            # MC Task #19
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
            
            # Checkpoint refresh component
            checkpoint_refresh_btn_18 = gr.Button("🔄 Refresh Rankings (Checkpoint 18)", variant="secondary")
            checkpoint_refresh_msg_18 = gr.Markdown("")
            
            def do_checkpoint_refresh_18():
                return check_checkpoint_refresh(18)
            
            checkpoint_refresh_btn_18.click(
                fn=do_checkpoint_refresh_18,
                inputs=[],
                outputs=[checkpoint_refresh_msg_18]
            )
            
            gr.Markdown("▶️ **CTA:** Open Final Case File & Submit Diagnosis")
        
        # ====================================================================
        # PHASE V: THE VERDICT (Slides 20-21)
        # ====================================================================
        
        with gr.Tab("⚖️ The Final Verdict (Slide 19)"):
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
            
            # MC Task #20
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
            gr.Markdown("▶️ **CTA:** Sign & file fairness report")
        
        with gr.Tab("🏆 Mission Debrief (Slide 21)"):
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
            
            # MC Task #21
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
            gr.Markdown("---")
            gr.Markdown("### 🎓 Mission Complete")
            gr.Markdown("⬇️ Scroll to begin next activity ⬇️")
        
        # Final summary tab
        with gr.Tab("📊 Progress Summary"):
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
        
        # ====================================================================
        # User Authentication Event Handler
        # ====================================================================
        
        # Button to authenticate and load user data
        load_user_data_btn.click(
            fn=authenticate_and_load_user_data,
            inputs=[session_state],
            outputs=[welcome_message, session_state]
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

"""
The Moral Compass Challenge - Gradio application for the Justice & Equity Challenge.

This version:
- Restores original slide content & styling helpers (standing, step 2, step 6) from the prior version you wanted.
- Keeps session-only authentication (no manual sign-in).
- Adds caching & concurrency optimizations (leaderboard + per-user stats TTL cache).
- Avoids per-user environment variable mutation.
- Retains navigation logic structure.

Replace placeholder HTML and CSS sections (“... existing ...”) with your original full content if needed.
"""

import os
import random
import time
import threading
from typing import Optional, Dict, Any, Tuple

import gradio as gr
import pandas as pd

try:
    from aimodelshare.playground import Competition
except ImportError as e:
    raise ImportError(
        "The 'aimodelshare' library is required. Install with: pip install aimodelshare"
    ) from e

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]

# ---------------------------------------------------------------------------
# In-memory caches
# ---------------------------------------------------------------------------
_cache_lock = threading.Lock()
_leaderboard_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS  # align TTLs

def _log(msg: str):
    if DEBUG_LOG:
        print(f"[MoralCompassApp] {msg}")

def _normalize_team_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(str(name).strip().split())

def _fetch_leaderboard(token: str) -> Optional[pd.DataFrame]:
    now = time.time()
    with _cache_lock:
        if (
            _leaderboard_cache["data"] is not None
            and now - _leaderboard_cache["timestamp"] < LEADERBOARD_CACHE_SECONDS
        ):
            return _leaderboard_cache["data"]

    try:
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        df = playground.get_leaderboard(token=token)
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
    except Exception as e:
        _log(f"Leaderboard fetch failed: {e}")
        df = None

    with _cache_lock:
        _leaderboard_cache["data"] = df
        _leaderboard_cache["timestamp"] = time.time()
    return df

def _get_or_assign_team(username: str, leaderboard_df: Optional[pd.DataFrame]) -> Tuple[str, bool]:
    try:
        if (
            leaderboard_df is not None
            and not leaderboard_df.empty
            and "Team" in leaderboard_df.columns
        ):
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(
                            user_submissions["timestamp"], errors="coerce"
                        )
                        user_submissions = user_submissions.sort_values(
                            "timestamp", ascending=False
                        )
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
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id:
            return False, None, None
        from aimodelshare.aws import get_token_from_session, _get_username_from_token
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
    now = time.time()
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
                    if "Team" in user_submissions.columns:
                        team_val = user_submissions.iloc[0]["Team"]
                        if pd.notna(team_val) and str(team_val).strip():
                            team_name = _normalize_team_name(team_val)

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
    _user_stats_cache[username] = stats
    return stats

# ---------------------------------------------------------------------------
# Original HTML builder helpers (restored)
# ---------------------------------------------------------------------------
def build_standing_html(user_stats):
    if user_stats["is_signed_in"] and user_stats["best_score"] is not None:
        best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
        rank_text = f"#{user_stats['rank']}" if user_stats["rank"] else "N/A"
        team_text = user_stats["team_name"] if user_stats["team_name"] else "N/A"
        team_rank_text = f"#{user_stats['team_rank']}" if user_stats["team_rank"] else "N/A"
        return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                You've Built an Accurate Model
            </h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    Through experimentation and iteration, you've achieved impressive results:
                </p>
                <div class='stat-grid'>
                    <div class='stat-card stat-card--success'>
                        <p class='stat-card__label'>Your Best Accuracy</p>
                        <p class='stat-card__value'>{best_score_pct}</p>
                    </div>
                    <div class='stat-card stat-card--accent'>
                        <p class='stat-card__label'>Your Individual Rank</p>
                        <p class='stat-card__value'>{rank_text}</p>
                    </div>
                </div>
                <div class='team-card'>
                    <p class='team-card__label'>Your Team</p>
                    <p class='team-card__value'>🛡️ {team_text}</p>
                    <p class='team-card__rank'>Team Rank: {team_rank_text}</p>
                </div>
                <ul class='bullet-list'>
                    <li>✅ Mastered the model-building process</li>
                    <li>✅ Climbed the accuracy leaderboard</li>
                    <li>✅ Competed with fellow engineers</li>
                    <li>✅ Earned promotions and unlocked tools</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>
                    🏆 Congratulations on your technical achievement!
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    But now you know the full story...
                </p>
                <p>
                    High accuracy isn't enough. Real-world AI systems must also be
                    <strong>fair, equitable, and <span class='emph-harm'>minimize harm</span></strong>
                    across all groups of people.
                </p>
            </div>
        </div>
        """
    elif user_stats["is_signed_in"]:
        return """
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                Ready to Begin Your Journey
            </h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    You've learned about the model-building process and are ready to take on the challenge:
                </p>
                <ul class='bullet-list'>
                    <li>✅ Understood the AI model-building process</li>
                    <li>✅ Learned about accuracy and performance</li>
                    <li>✅ Discovered real-world bias in AI systems</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>
                    🎯 Ready to learn about ethical AI!
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    Now you know the full story...
                </p>
                <p>
                    High accuracy isn't enough. Real-world AI systems must also be
                    <strong>fair, equitable, and <span class='emph-harm'>minimize harm</span></strong>
                    across all groups of people.
                </p>
            </div>
        </div>
        """
    else:
        return """
        <div class='slide-shell slide-shell--warning' style='text-align:center;'>
            <h2 class='slide-shell__title'>
                🔒 Session Required
            </h2>
            <p class='slide-shell__subtitle'>
                Please access this app via a valid session URL.<br>
                No manual sign-in is offered.<br>
                You can still continue through this lesson to learn!
            </p>
        </div>
        """

def build_step2_html(user_stats):
    if user_stats["is_signed_in"] and user_stats["best_score"] is not None:
        gauge_value = int(user_stats["best_score"] * 100)
    else:
        gauge_value = 75
    gauge_fill_percent = f"{gauge_value}%"
    gauge_display = str(gauge_value)
    return f"""
        <div class='slide-shell slide-shell--warning'>
            <h3 class='slide-shell__title'>
                We Need a Higher Standard
            </h3>
            <p class='slide-shell__subtitle'>
                While your model is accurate, a higher standard is needed to prevent
                <span class='emph-harm'>real-world harm</span>. To incentivize this new focus,
                we're introducing a new score.
            </p>
            <div class='content-box'>
                <h4 class='content-box__heading'>Watch Your Score</h4>
                <div class='score-gauge-container'>
                    <div class='score-gauge' style='--fill-percent: {gauge_fill_percent};'>
                        <div class='score-gauge-inner'>
                            <div class='score-gauge-value'>{gauge_display}</div>
                            <div class='score-gauge-label'>Accuracy Score</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    This score measures only <strong>one dimension</strong> of success.
                </p>
                <p>
                    It's time to add a second, equally important dimension:
                    <strong class='emph-fairness'>Ethics</strong>.
                </p>
            </div>
        </div>
    """

def build_step6_html(user_stats):
    if user_stats["is_signed_in"] and user_stats["rank"]:
        rank_text = f"#{user_stats['rank']}"
        position_message = f"""
                    <p class='slide-teaching-body' style='text-align:left;'>
                        You were previously <strong>ranked {rank_text}</strong> on the accuracy leaderboard.
                        But now, with the introduction of the Moral Compass Score, your position has changed:
                    </p>
        """
    else:
        position_message = """
                    <p class='slide-teaching-body' style='text-align:left;'>
                        With the introduction of the Moral Compass Score, everyone starts fresh.
                        Your previous work on accuracy is valuable, but now we need to add ethics:
                    </p>
        """

    return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                📍 Your Current Position
            </h3>
            <div class='content-box'>
                {position_message}
                <div class='content-box content-box--danger'>
                    <p class='content-box__heading'>
                        Current Moral Compass Rank: <span class='emph-risk'>Starting Fresh</span>
                    </p>
                    <p>
                        (Because your Moral Compass Score = <span class='emph-harm'>0</span>)
                    </p>
                </div>
            </div>
            <div class='content-box content-box--success'>
                <h4 class='content-box__heading'>
                    🛤️ The Path Forward
                </h4>
                <p class='slide-teaching-body'>
                    The next section will provide expert guidance from the <strong>UdG's
                    OEIAC AI Ethics Center</strong>. You'll learn to:
                </p>
                <ul class='bullet-list'>
                    <li>🔍 <strong>Detect and measure bias</strong> in your AI models</li>
                    <li>⚖️ <strong>Apply fairness metrics</strong> to evaluate equity</li>
                    <li>🔧 <strong>Redesign your system</strong> to <span class='emph-harm'>minimize harm</span></li>
                    <li>📊 <strong>Balance accuracy with fairness</strong> for better outcomes</li>
                </ul>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>
                    🏆 Upon Completion
                </p>
                <p>
                    By completing the full learning module and improving your Moral Compass Score,
                    you will earn your <strong class='emph-fairness'>AI Ethical Risk Training Certificate</strong>.
                </p>
                <p class='note-text'>
                    (Certificate details and delivery will be covered in upcoming sections)
                </p>
            </div>
            <h1 style='margin:32px 0 16px 0; font-size: 3rem; text-align:center;'>👇 SCROLL DOWN 👇</h1>
            <p style='font-size:1.2rem; text-align:center;'>
                Continue to the expert guidance section to begin improving your Moral Compass Score.
            </p>
        </div>
    """

# Restore your original (full) CSS here – only placeholder shown previously.
CSS = """
/* Restore your full original CSS here (previous file showed placeholder).
   Ensure all classes (slide-shell--info, slide-shell--warning, stat-card modifiers,
   emph-harm, emph-fairness, emph-risk, etc.) are present exactly as before. */
... [CSS unchanged for brevity in original snippet] ...
"""

def create_moral_compass_challenge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=CSS) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        gr.Markdown("<h1 style='text-align:center;'>⚖️ The Ethical Challenge: The Moral Compass</h1>")

        # Step 1
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            stats_display = gr.HTML(value="")  # Set after session auth
            step_1_next = gr.Button("Introduce the New Standard ▶️", variant="primary", size="lg")

        # Step 2
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            step_2_html_comp = gr.HTML(value="")
            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Reset and Transform ▶️", variant="primary", size="lg")

        # Step 3
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            # Placeholder from original file – replace with full original reset gauge HTML if needed
            step_3_html_comp = gr.HTML(""" ... existing reset gauge HTML ... """)
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("Introduce the Moral Compass ▶️", variant="primary", size="lg")

        # Step 4
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            gr.Markdown("<h2 style='text-align:center;'>🧭 The Moral Compass Score</h2>")
            # Placeholder from original file – replace with full MC Score HTML if needed
            step_4_html_comp = gr.HTML(""" ... existing MC Score HTML ... """)
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("See the Challenge Ahead ▶️", variant="primary", size="lg")

        # Step 6
        with gr.Column(visible=False, elem_id="step-6") as step_6:
            step_6_html_comp = gr.HTML(value="")
            with gr.Row():
                step_6_back = gr.Button("◀️ Back", size="lg")

        all_steps = [step_1, step_2, step_3, step_4, step_6]

        def _nav_generator(target):
            def go():
                yield {**{s: gr.update(visible=False) for s in all_steps}}
                yield {**{s: gr.update(visible=False) for s in all_steps}, target: gr.update(visible=True)}
            return go

        def _nav_js(target_id: str, message: str, min_show_ms: int = 600) -> str:
            return f"""
()=>{{
  try {{
    const overlay=document.getElementById('nav-loading-overlay');
    const msg=document.getElementById('nav-loading-text');
    if(overlay && msg){{ msg.textContent='{message}'; overlay.style.display='flex'; setTimeout(()=>overlay.style.opacity='1',10); }}
    const start=Date.now();
    setTimeout(()=>{{ window.scrollTo({{top:0, behavior:'smooth'}}); }},40);
    const poll=setInterval(()=>{{
      const elapsed=Date.now()-start;
      const target=document.getElementById('{target_id}');
      const visible=target && target.offsetParent!==null;
      if((visible && elapsed>={min_show_ms}) || elapsed>5000){{
        clearInterval(poll);
        if(overlay){{ overlay.style.opacity='0'; setTimeout(()=>overlay.style.display='none',300); }}
      }}
    }},90);
  }} catch(e){{}}
}}
"""

        # Navigation wiring
        step_1_next.click(fn=_nav_generator(step_2), inputs=None, outputs=all_steps, js=_nav_js("step-2", "Introducing new standard..."))
        step_2_back.click(fn=_nav_generator(step_1), inputs=None, outputs=all_steps, js=_nav_js("step-1", "Returning..."))
        step_2_next.click(fn=_nav_generator(step_3), inputs=None, outputs=all_steps, js=_nav_js("step-3", "Resetting perspective..."))
        step_3_back.click(fn=_nav_generator(step_2), inputs=None, outputs=all_steps, js=_nav_js("step-2", "Revisiting..."))
        step_3_next.click(fn=_nav_generator(step_4), inputs=None, outputs=all_steps, js=_nav_js("step-4", "Introducing Moral Compass..."))
        step_4_back.click(fn=_nav_generator(step_3), inputs=None, outputs=all_steps, js=_nav_js("step-3", "Back..."))
        step_4_next.click(fn=_nav_generator(step_6), inputs=None, outputs=all_steps, js=_nav_js("step-6", "Computing starting point..."))
        step_6_back.click(fn=_nav_generator(step_4), inputs=None, outputs=all_steps, js=_nav_js("step-4", "Reviewing..."))

        # Session auth load
        def handle_session_auth(request: "gr.Request"):
            success, username, token = _try_session_based_auth(request)
            if not success or not username:
                return {
                    stats_display: gr.update(value=build_standing_html({"is_signed_in": False})),
                    step_2_html_comp: gr.update(value=build_step2_html({"is_signed_in": False, "best_score": None})),
                    step_6_html_comp: gr.update(value=build_step6_html({"is_signed_in": False}))
                }
            stats = _compute_user_stats(username, token)
            return {
                stats_display: gr.update(value=build_standing_html(stats)),
                step_2_html_comp: gr.update(value=build_step2_html(stats)),
                step_6_html_comp: gr.update(value=build_step6_html(stats))
            }

        demo.load(
            fn=handle_session_auth,
            inputs=None,
            outputs=[stats_display, step_2_html_comp, step_6_html_comp]
        )

    return demo

def launch_moral_compass_challenge_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_moral_compass_challenge_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)





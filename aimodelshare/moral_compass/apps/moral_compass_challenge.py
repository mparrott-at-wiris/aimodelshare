"""
Optimized Moral Compass Challenge App for multi-session deployment (Google Cloud Run ready).

Changes:
- Session-only authentication via ?sessionid=...
- Added leaderboard & per-user stats caching (TTL configurable)
- Removed unused imports and print spam
- Added structured debug logging toggle
- Modular HTML generation
- Stateless per-request user handling (no os.environ mutations)
- Navigation logic implemented (previous snippet omitted it)

Environment Variables:
    LEADERBOARD_CACHE_SECONDS (int) default=45
    MAX_LEADERBOARD_ENTRIES (int) default=None
    DEBUG_LOG ('true'/'false') default='false'
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

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
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

    # Fetch outside lock
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
            if (
                "accuracy" in leaderboard_df.columns
                and "username" in leaderboard_df.columns
            ):
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
# HTML Builders
# ---------------------------------------------------------------------------
def build_standing_html(user_stats: Dict[str, Any]) -> str:
    if user_stats.get("is_signed_in") and user_stats.get("best_score") is not None:
        best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
        rank_text = f"#{user_stats['rank']}" if user_stats["rank"] else "N/A"
        team_text = user_stats["team_name"] or "N/A"
        team_rank_text = f"#{user_stats['team_rank']}" if user_stats["team_rank"] else "N/A"
        return f"""
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>You Built an Accurate Model</h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    Your experimentation paid off. Here are your current stats:
                </p>
                <div class='stat-grid'>
                    <div class='stat-card'>
                        <p class='stat-card__label'>Best Accuracy</p>
                        <p class='stat-card__value'>{best_score_pct}</p>
                    </div>
                    <div class='stat-card'>
                        <p class='stat-card__label'>Your Rank</p>
                        <p class='stat-card__value'>{rank_text}</p>
                    </div>
                </div>
                <div class='team-card'>
                    <p class='team-card__label'>Team</p>
                    <p class='team-card__value'>🛡️ {team_text}</p>
                    <p class='team-card__label'>Team Rank</p>
                    <p class='team-card__value'>{team_rank_text}</p>
                </div>
                <ul class='bullet-list'>
                    <li>✅ Iterated effectively</li>
                    <li>✅ Climbed the accuracy board</li>
                    <li>✅ Contributed to team progress</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>🏆 Strong technical foundation!</p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>But there's more...</p>
                <p>Accuracy alone is insufficient—ethical impact matters.</p>
            </div>
        </div>
        """
    elif user_stats.get("is_signed_in"):
        return """
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>Ready to Begin</h3>
            <div class='content-box'>
                <p class='slide-shell__subtitle'>
                    You're authenticated but have not submitted models yet.
                </p>
                <ul class='bullet-list'>
                    <li>✅ Learned about accuracy</li>
                    <li>✅ Observed bias implications</li>
                    <li>✅ Prepared for ethical metrics</li>
                </ul>
                <p class='slide-shell__subtitle' style='font-weight:600;'>🎯 Let's raise the standard.</p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p class='content-box__heading'>Next Step</p>
                <p>Introduce the concept of balancing performance with fairness.</p>
            </div>
        </div>
        """
    else:
        return """
        <div class='slide-shell slide-shell--warning'>
            <h2 class='slide-shell__title'>🔒 Session Required</h2>
            <p class='slide-shell__subtitle'>
                Supply a valid ?sessionid=... in the URL to view personalized stats.
                No manual sign-in is available.
            </p>
        </div>
        """

def build_step2_html(user_stats: Dict[str, Any]) -> str:
    if user_stats.get("is_signed_in") and user_stats.get("best_score") is not None:
        gauge_value = int(user_stats["best_score"] * 100)
    else:
        # Generic placeholder gauge
        gauge_value = 72
    gauge_percent = f"{gauge_value}%"
    return f"""
    <div class='slide-shell slide-shell--warning'>
        <h3 class='slide-shell__title'>We Need a Higher Standard</h3>
        <p class='slide-shell__subtitle'>
            Your accuracy score is one dimension:
        </p>
        <div class='content-box'>
            <h4 class='content-box__heading'>Accuracy Gauge</h4>
            <div class='score-gauge-container'>
                <div class='score-gauge' style='--fill-percent:{gauge_percent};'>
                    <div class='score-gauge-inner'>
                        <div class='score-gauge-value'>{gauge_value}</div>
                        <div class='score-gauge-label'>Accuracy</div>
                    </div>
                </div>
            </div>
            <p style='margin-top:1rem;'>Now we introduce a second dimension: Ethics.</p>
        </div>
        <div class='content-box content-box--emphasis'>
            <p><strong>Goal:</strong> Transition from single-metric success to multi-dimensional responsibility.</p>
        </div>
    </div>
    """

def build_step3_html() -> str:
    return """
    <div class='slide-shell slide-shell--info'>
        <h3 class='slide-shell__title'>Resetting Perspective</h3>
        <div class='content-box'>
            <p>
                Visualizing a paradigm shift: we temporarily 'reset' the dominance of accuracy
                to make space for the Moral Compass Score.
            </p>
            <div style='margin-top:20px; text-align:center; font-size:3rem;'>🔄</div>
        </div>
        <div class='content-box content-box--emphasis'>
            <p><strong>Outcome:</strong> Everyone starts at 0 on the new ethical dimension.</p>
        </div>
    </div>
    """

def build_step4_html() -> str:
    return """
    <div class='slide-shell slide-shell--info'>
        <h3 class='slide-shell__title'>🧭 The Moral Compass Score</h3>
        <div class='content-box'>
            <p>
                The Moral Compass Score combines technical performance with fairness & harm reduction.
            </p>
            <ul class='bullet-list'>
                <li>⚖️ Penalizes biased error distributions</li>
                <li>🔍 Encourages disparity analysis</li>
                <li>🔧 Rewards mitigation strategies</li>
                <li>📈 Complements accuracy rather than replaces it</li>
            </ul>
        </div>
        <div class='content-box content-box--emphasis'>
            <p><strong>Principle:</strong> Ethical AI is multi-objective optimization.</p>
        </div>
    </div>
    """

def build_step6_html(user_stats: Dict[str, Any]) -> str:
    if user_stats.get("is_signed_in") and user_stats.get("rank"):
        rank_text = f"#{user_stats['rank']}"
        position_msg = f"You were previously ranked {rank_text} on the accuracy leaderboard."
    else:
        position_msg = "You will establish your position as you build ethically aware models."

    return f"""
    <div class='slide-shell slide-shell--info'>
        <h3 class='slide-shell__title'>📍 Your New Starting Point</h3>
        <div class='content-box'>
            <p>{position_msg}</p>
            <div class='content-box content-box--danger'>
                <p class='content-box__heading'>
                    Current Moral Compass Rank: <span style='color:#b91c1c;'>Not Yet Established</span>
                </p>
                <p>(Moral Compass Score = 0 initially)</p>
            </div>
        </div>
        <div class='content-box content-box--success'>
            <h4 class='content-box__heading'>🛤️ Path Forward</h4>
            <ul class='bullet-list'>
                <li>🔍 Detect and measure bias</li>
                <li>⚖️ Apply fairness metrics</li>
                <li>🔧 Redesign models to minimize harm</li>
                <li>📊 Balance performance & ethics</li>
            </ul>
        </div>
        <div class='content-box content-box--emphasis'>
            <p><strong>Achievement:</strong> Improve your Moral Compass Score to earn certification.</p>
        </div>
        <h1 style='margin:32px 0 16px 0; font-size:2.5rem; text-align:center;'>👇 CONTINUE 👇</h1>
        <p style='text-align:center;'>Proceed to ethical tooling & evaluation modules.</p>
    </div>
    """

# ---------------------------------------------------------------------------
# CSS (pared-down for performance; extend as needed)
# ---------------------------------------------------------------------------
CSS = """
.slide-shell { padding:24px; border-radius:16px; background:var(--block-background-fill);
  border:2px solid var(--border-color-primary); max-width:900px; margin:auto; }
.slide-shell--info { border-color: var(--color-accent); }
.slide-shell--warning { border-color: var(--color-accent); }
.slide-shell__title { font-size:2.2rem; margin:0; text-align:center; }
.slide-shell__subtitle { font-size:1.05rem; margin-top:16px; text-align:center; color:var(--secondary-text-color); }
.stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; }
.stat-card, .team-card { text-align:center; padding:16px; border-radius:8px; border:1px solid var(--border-color-primary); }
.stat-card__label { margin:0; font-size:0.75rem; color:var(--secondary-text-color); }
.stat-card__value { margin:4px 0 0 0; font-size:1.4rem; font-weight:600; }
.team-card__label { margin:0; font-size:0.75rem; color:var(--secondary-text-color); }
.team-card__value { margin:4px 0 0 0; font-size:1.1rem; font-weight:600; }
.content-box { background:var(--block-background-fill); border:1px solid var(--border-color-primary);
  border-radius:12px; padding:20px; margin:22px 0; }
.content-box--emphasis { border-left:5px solid var(--color-accent); }
.content-box--danger { border-left:5px solid #dc2626; }
.content-box--success { border-left:5px solid #16a34a; }
.bullet-list { list-style:disc; padding-left:22px; line-height:1.6; }
.score-gauge-container { display:flex; justify-content:center; margin-top:10px; }
.score-gauge { width:160px; height:160px; border-radius:50%; background:
  conic-gradient(var(--color-accent) var(--fill-percent), var(--block-background-fill) var(--fill-percent));
  display:flex; align-items:center; justify-content:center; position:relative; }
.score-gauge-inner { width:120px; height:120px; border-radius:50%; background:var(--block-background-fill);
  display:flex; flex-direction:column; align-items:center; justify-content:center; border:1px solid var(--border-color-primary); }
.score-gauge-value { font-size:2rem; font-weight:700; }
.score-gauge-label { font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; margin-top:4px; }
#nav-loading-overlay { position:fixed; inset:0; background:var(--body-background-fill);
  z-index:9999; display:none; flex-direction:column; align-items:center; justify-content:center; opacity:0;
  transition:opacity .3s; }
.nav-spinner { width:50px; height:50px; border:5px solid var(--block-background-fill);
  border-top:5px solid var(--color-accent); border-radius:50%; animation: nav-spin 1s linear infinite; margin-bottom:20px; }
@keyframes nav-spin { to { transform: rotate(360deg); } }
"""

# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------
def create_moral_compass_challenge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=CSS) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)
        gr.Markdown("<h1 style='text-align:center;'>⚖️ The Moral Compass Challenge</h1>")

        # Step 1
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            stats_display = gr.HTML(build_standing_html({"is_signed_in": False}))
            step_1_next = gr.Button("Introduce the New Standard ▶️", variant="primary", size="lg")

        # Step 2
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            step_2_html_comp = gr.HTML(build_step2_html({"is_signed_in": False, "best_score": None}))
            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Reset and Transform ▶️", variant="primary", size="lg")

        # Step 3
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            step_3_html_comp = gr.HTML(build_step3_html())
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("Introduce Moral Compass ▶️", variant="primary", size="lg")

        # Step 4
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            step_4_html_comp = gr.HTML(build_step4_html())
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("See Challenge Ahead ▶️", variant="primary", size="lg")

        # Step 6 (after Step 4)
        with gr.Column(visible=False, elem_id="step-6") as step_6:
            step_6_html_comp = gr.HTML(build_step6_html({"is_signed_in": False}))
            with gr.Row():
                step_6_back = gr.Button("◀️ Back", size="lg")

        all_steps = [step_1, step_2, step_3, step_4, step_6]

        # Navigation helpers
        def _nav_generator(target):
            def go():
                # Phase 1: show loading
                yield {
                    **{s: gr.update(visible=False) for s in all_steps},
                    step_1: gr.update(visible=False),
                }
                # Loading overlay handled by JS; we just yield hidden steps
                # Phase 2: show target
                yield {
                    **{s: gr.update(visible=False) for s in all_steps},
                    target: gr.update(visible=True),
                }
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
  }} catch(e){{ console.warn('nav js error', e); }}
}}
"""

        # Wire navigation
        step_1_next.click(fn=_nav_generator(step_2), inputs=None, outputs=all_steps, js=_nav_js("step-2", "Introducing new standard..."))
        step_2_back.click(fn=_nav_generator(step_1), inputs=None, outputs=all_steps, js=_nav_js("step-1", "Returning..."))
        step_2_next.click(fn=_nav_generator(step_3), inputs=None, outputs=all_steps, js=_nav_js("step-3", "Resetting perspective..."))
        step_3_back.click(fn=_nav_generator(step_2), inputs=None, outputs=all_steps, js=_nav_js("step-2", "Revisiting..."))
        step_3_next.click(fn=_nav_generator(step_4), inputs=None, outputs=all_steps, js=_nav_js("step-4", "Introducing Moral Compass..."))
        step_4_back.click(fn=_nav_generator(step_3), inputs=None, outputs=all_steps, js=_nav_js("step-3", "Back..."))
        step_4_next.click(fn=_nav_generator(step_6), inputs=None, outputs=all_steps, js=_nav_js("step-6", "Computing starting point..."))
        step_6_back.click(fn=_nav_generator(step_4), inputs=None, outputs=all_steps, js=_nav_js("step-4", "Reviewing..."))

        # Session auth handler
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






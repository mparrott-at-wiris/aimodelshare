"""
The Moral Compass Challenge - Gradio application for the Justice & Equity Challenge.

This version:
- Uses sessionid-only authentication (no username/password UI).
- Retains the restored original slide text/content you wanted (standing, paradigm shift, reset, formula, challenge ahead).
- Keeps lightweight leaderboard + per-user stats caching for scalability.
- Integrates the richer dark/light mode optimized CSS from the older version you supplied (including gauge, alerts, emphasis classes, etc.).
- No per-user environment mutation; everything resolved per request.

Environment Variables (optional):
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
    raise ImportError("The 'aimodelshare' library is required. Install with: pip install aimodelshare") from e

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
# In-memory caches (per container instance)
# ---------------------------------------------------------------------------
_cache_lock = threading.Lock()
_leaderboard_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

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
# HTML Builders (restored original wording)
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
                Supply a valid ?sessionid=... in the URL to view personalized stats.
                No manual sign-in is available.
            </p>
        </div>
        """

def build_step2_html(user_stats):
    if user_stats.get("is_signed_in") and user_stats.get("best_score") is not None:
        gauge_value = int(user_stats["best_score"] * 100)
    else:
        gauge_value = 75
    gauge_percent = f"{gauge_value}%"
    return f"""
    <div class='slide-shell slide-shell--warning'>
        <h3 class='slide-shell__title'>We Need a Higher Standard</h3>
        <p class='slide-shell__subtitle'>
            While your model is accurate, a higher standard is needed to prevent
            <span class='emph-harm'>real-world harm</span>. To incentivize this new focus,
            we're introducing a new score.
        </p>
        <div class='content-box'>
            <h4 class='content-box__heading'>Watch Your Score</h4>
            <div class='score-gauge-container'>
                <div class='score-gauge' style='--fill-percent:{gauge_percent};'>
                    <div class='score-gauge-inner'>
                        <div class='score-gauge-value'>{gauge_value}</div>
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
            <p class='content-box__heading'>
                🏆 Achievement
            </p>
            <p>Improve your Moral Compass Score to earn certification.</p>
        </div>
        <h1 style='margin:32px 0 16px 0; font-size:2.5rem; text-align:center;'>👇 CONTINUE 👇</h1>
        <p style='text-align:center;'>Proceed to ethical tooling & evaluation modules.</p>
    </div>
    """

# ---------------------------------------------------------------------------
# Dark/Light Mode Optimized CSS (from older version)
# ---------------------------------------------------------------------------
CSS = """
.large-text { font-size: 20px !important; }

/* Slide + containers */
.slide-shell {
  padding: 28px;
  border-radius: 16px;
  background-color: var(--block-background-fill);
  color: var(--body-text-color);
  border: 2px solid var(--border-color-primary);
  box-shadow: 0 8px 20px rgba(0,0,0,0.05);
  max-width: 900px;
  margin: 0 auto 24px auto;
  font-size: 20px;
}

.slide-shell--info { border-color: var(--color-accent); }
.slide-shell--warning { border-color: var(--color-accent); }

.slide-shell__title {
  font-size: 2rem;
  margin: 0 0 16px 0;
  text-align: center;
}
.slide-shell__subtitle {
  font-size: 1.1rem;
  margin-top: 8px;
  text-align: center;
  color: var(--secondary-text-color);
  line-height: 1.7;
}

.content-box {
  background-color: var(--block-background-fill);
  border-radius: 12px;
  border: 1px solid var(--border-color-primary);
  padding: 24px;
  margin: 24px 0;
}
.content-box__heading {
  margin-top: 0;
  font-weight: 600;
  font-size: 1.2rem;
}
.content-box--emphasis { border-left: 6px solid var(--color-accent); }
.content-box--danger { border-left: 6px solid #dc2626; }
.content-box--success { border-left: 6px solid #16a34a; }

.bullet-list {
  list-style: none;
  padding-left: 0;
  margin: 16px auto 0 auto;
  max-width: 600px;
  font-size: 1.05rem;
}
.bullet-list li { padding: 6px 0; }

.note-text {
  font-size: 0.95rem;
  margin-top: 12px;
  font-style: italic;
  color: var(--secondary-text-color);
}

/* Stats cards */
.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 24px auto;
  max-width: 600px;
}
.stat-card, .team-card {
  text-align: center;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid var(--border-color-primary);
  background-color: var(--block-background-fill);
}
.stat-card__label, .team-card__label {
  margin: 0;
  font-size: 0.9rem;
  color: var(--secondary-text-color);
}
.stat-card__value {
  margin: 8px 0 0 0;
  font-size: 2.2rem;
  font-weight: 800;
}
.stat-card--success .stat-card__value { color: #16a34a; }
.stat-card--accent .stat-card__value { color: var(--color-accent); }
.team-card__value {
  margin: 8px 0 4px 0;
  font-size: 1.5rem;
  font-weight: 700;
}
.team-card__rank { margin: 0; font-size: 1rem; color: var(--secondary-text-color); }

/* Teaching body */
.slide-teaching-body {
  font-size: 1.1rem;
  line-height: 1.8;
  margin-top: 1rem;
}

/* Emphasis */
.emph-harm { color: #b91c1c; font-weight: 700; }
.emph-risk { color: #b45309; font-weight: 600; }
.emph-fairness { color: var(--color-accent); font-weight: 600; }

@media (prefers-color-scheme: dark) {
  .emph-harm { color: #fca5a5; }
  .emph-risk { color: #fed7aa; }
}

/* Alerts */
.alert {
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid var(--border-color-primary);
  margin-top: 12px;
  background-color: var(--block-background-fill);
  color: var(--body-text-color);
  font-size: 0.95rem;
}
.alert__title { margin: 0; font-weight: 600; font-size: 1.05rem; }
.alert__subtitle { margin: 8px 0 0 0; font-weight: 600; }
.alert__body { margin: 8px 0 0 0; }
.alert__link { text-decoration: underline; }
.alert--error { border-left-color: #dc2626; }
.alert--warning { border-left-color: #f59e0b; }
.alert--success { border-left-color: #16a34a; }

/* Gauge */
.score-gauge-container {
  position: relative;
  width: 260px;
  height: 260px;
  margin: 24px auto;
}
.score-gauge {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: conic-gradient(
    from 180deg,
    #16a34a 0%,
    #16a34a var(--fill-percent, 0%),
    var(--border-color-primary) var(--fill-percent, 0%),
    var(--border-color-primary) 100%
  );
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
}
.score-gauge-inner {
  width: 70%;
  height: 70%;
  border-radius: 50%;
  background-color: var(--block-background-fill);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2;
  border: 1px solid var(--border-color-primary);
}
.score-gauge-value {
  font-size: 3.2rem;
  font-weight: 800;
  color: var(--body-text-color);
  line-height: 1;
}
.score-gauge-label {
  font-size: 0.95rem;
  color: var(--secondary-text-color);
  margin-top: 8px;
}

/* Gauge reset animation */
@keyframes gauge-drop {
  0% { background: conic-gradient(from 180deg,#16a34a 0%,#16a34a 75%,var(--border-color-primary) 75%,var(--border-color-primary) 100%); }
  100% { background: conic-gradient(from 180deg,#dc2626 0%,#dc2626 0%,var(--border-color-primary) 0%,var(--border-color-primary) 100%); }
}
.gauge-dropped { animation: gauge-drop 2s ease-out forwards; }

/* Navigation overlay */
#nav-loading-overlay {
  position: fixed;
  top:0; left:0;
  width:100%; height:100%;
  background-color: var(--body-background-fill);
  z-index:9999;
  display:none;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  opacity:0;
  transition:opacity .25s ease;
}
.nav-spinner {
  width:50px; height:50px;
  border:5px solid var(--block-background-fill);
  border-top:5px solid var(--color-accent);
  border-radius:50%;
  animation: nav-spin 1s linear infinite;
  margin-bottom:20px;
}
@keyframes nav-spin { to { transform: rotate(360deg); } }
#nav-loading-text {
  font-size:1.3rem;
  font-weight:600;
  color: var(--body-text-color);
}

/* Dark mode: reduce shadows */
@media (prefers-color-scheme: dark) {
  .slide-shell,
  .content-box,
  .alert {
    box-shadow:none;
  }
  .score-gauge { box-shadow:none; }
}
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
            step_3_html_comp = gr.HTML("""
            <div class='slide-shell slide-shell--warning'>
                <div style='text-align:center;'>
                    <h3 class='slide-shell__title'>
                        Your Accuracy Score Is Being Reset
                    </h3>
                    <div class='score-gauge-container'>
                        <div class='score-gauge gauge-dropped' style='--fill-percent: 0%;'>
                            <div class='score-gauge-inner'>
                                <div class='score-gauge-value' style='color:#dc2626;'>0</div>
                                <div class='score-gauge-label'>Score Reset</div>
                            </div>
                        </div>
                    </div>
                    <div class='content-box content-box--danger'>
                        <h4 class='content-box__heading'>
                            ⚠️ Why This Reset?
                        </h4>
                        <p class='slide-teaching-body' style='text-align:left;'>
                            We reset your score to emphasize a critical truth: your previous success
                            was measured by only <strong>one dimension</strong> — prediction accuracy. So far, you
                            <strong>have not demonstrated</strong> that you know how to make your AI system
                            <span class='emph-fairness'>safe for society</span>. You don’t yet know whether
                            the model you built is <strong class='emph-harm'>just as biased</strong> as the
                            harmful examples we studied in the previous activity. Moving forward, you’ll need
                            to excel on <strong>two fronts</strong>: technical performance <em>and</em>
                            ethical responsibility.
                        </p>
                    </div>
                    <div class='content-box content-box--success'>
                        <h4 class='content-box__heading'>
                            ✅ Don't Worry!
                        </h4>
                        <p class='slide-teaching-body'>
                            As you make your AI more ethical through the upcoming lessons and challenges,
                            <strong>your score will be restored</strong>—and could climb even higher than before.
                        </p>
                    </div>
                </div>
            </div>
            """)
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("Introduce Moral Compass ▶️", variant="primary", size="lg")

        # Step 4
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            step_4_html_comp = gr.HTML("""
            <div class='slide-shell slide-shell--info'>
                <h3 class='slide-shell__title'>
                    A New Way to Win
                </h3>
                <p class='slide-shell__subtitle'>
                    Your new goal is to climb the leaderboard by increasing your
                    <strong>Moral Compass Score</strong>.
                </p>
                <div class='content-box formula-box'>
                    <h4 class='content-box__heading' style='text-align:center;'>📐 The Scoring Formula</h4>
                    <div class='formula-math'>
                        <strong>Moral Compass Score</strong> =<br><br>
                        [ Current Model Accuracy ] × [ Ethical Progress % ]
                    </div>
                    <div class='content-box' style='margin-top:20px;'>
                        <p class='content-box__heading'>Where:</p>
                        <ul class='bullet-list'>
                            <li><strong>Current Model Accuracy:</strong> Your technical performance</li>
                            <li>
                                <strong>Ethical Progress %:</strong> Percentage of:
                                <ul class='bullet-list' style='margin-top:8px;'>
                                    <li>✅ Ethical learning tasks completed</li>
                                    <li>✅ Check-in questions answered correctly</li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                </div>
                <div class='content-box content-box--success'>
                    <h4 class='content-box__heading'>💡 What This Means:</h4>
                    <p class='slide-teaching-body'>
                        You <strong>cannot</strong> win by accuracy alone—you must also demonstrate
                        <strong class='emph-fairness'>ethical understanding</strong>. And you
                        <strong>cannot</strong> win by just completing lessons—you need a working model too.
                        <strong class='emph-risk'>Both dimensions matter</strong>.
                    </p>
                </div>
            </div>
            """)
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("See Challenge Ahead ▶️", variant="primary", size="lg")

        # Step 6
        with gr.Column(visible=False, elem_id="step-6") as step_6:
            step_6_html_comp = gr.HTML(build_step6_html({"is_signed_in": False}))
            with gr.Row():
                step_6_back = gr.Button("◀️ Back", size="lg")

        all_steps = [step_1, step_2, step_3, step_4, step_6]

        # Navigation helpers
        def _nav_generator(target):
            def go():
                # Phase 1
                yield {**{s: gr.update(visible=False) for s in all_steps}}
                # Phase 2
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

        demo.load(fn=handle_session_auth, inputs=None, outputs=[stats_display, step_2_html_comp, step_6_html_comp])

    return demo

def launch_moral_compass_challenge_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_moral_compass_challenge_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

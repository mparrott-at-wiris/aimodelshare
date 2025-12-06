import os
import sys
import subprocess
import time
from typing import Tuple, Optional

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
TABLE_ID = "m-mc"

# --- 2. SETUP & DEPENDENCIES ---

def install_dependencies():
    packages = ["gradio>=5.0.0", "aimodelshare", "pandas"]
    for package in packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import gradio as gr
    from aimodelshare.moral_compass import MoralcompassApiClient
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    print("📦 Installing dependencies...")
    install_dependencies()
    import gradio as gr
    from aimodelshare.moral_compass import MoralcompassApiClient
    from aimodelshare.aws import get_token_from_session, _get_username_from_token

# --- 3. AUTH HELPER ---

def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Attempt to authenticate via session token from Gradio request.
    Returns (success, username, token).
    """
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
        
    except Exception:
        # Log generic failure without exposing sensitive details
        print("Session auth failed: unable to authenticate")
        return False, None, None

def validate_auth(session_id):
    """
    Attempts to get a token. Returns (token, username) or raises Error.
    """
    if not session_id or str(session_id).strip() == "":
        raise gr.Error("⚠️ Session ID is missing. Please paste your ID.")
    
    try:
        token = get_token_from_session(session_id)
        if not token:
            raise ValueError("Empty token returned")
        username = _get_username_from_token(token)
        return token, username
    except Exception as e:
        raise gr.Error(f"❌ Authentication Failed: Session Invalid or Expired. ({str(e)})")

# --- 4. MODULE DEFINITIONS ---

MODULES = [
    {
        "id": 0,
        "title": "Module 0: Moral Compass Intro",
        "sim_acc": 0.60,
        "sim_comp": 5,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🧭 Introducing the Moral Compass: A New Way to Win</h2>
                <div class="slide-body">
                    <p>
                        While your model is accurate, a higher standard is needed to prevent
                        <span style="color:#ef4444; font-weight:bold;">real-world harm</span>.
                        To incentivize this, we are introducing the <strong>Moral Compass Score</strong>.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">1. The Scoring Formula</h4>
                        <div style="font-size: 1.4rem; margin: 16px 0;">
                            <strong>Moral Compass Score</strong> =<br><br>
                            <span style="color:var(--color-accent); font-weight:bold;">[ Current Model Accuracy ]</span>
                            ×
                            <span style="color:#22c55e; font-weight:bold;">[ Ethical Progress % ]</span>
                        </div>
                        <p style="font-size:1rem; max-width:600px; margin:0 auto;">
                            Your accuracy is powerful, but it is only unlocked as you demonstrate ethical progress
                            through this course. The same model can either be risky or responsible depending on how
                            it is deployed and governed.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:24px; margin-top:24px;">
                        <div class="hint-box" style="text-align:left;">
                            <h4 style="margin-top:0; font-size:1.1rem;">2. Dynamic Calibration</h4>
                            <p>
                                Your score is <strong>alive</strong>. As you complete the upcoming modules, your
                                <strong>Ethical Progress %</strong> rises, unlocking more and more of your base
                                accuracy.
                            </p>
                            <p>
                                Early on, even a strong model may have a modest Moral Compass Score. By the final
                                module, the same accuracy can translate into a much higher, safer score.
                            </p>
                        </div>
                        <div class="hint-box" style="text-align:left;">
                            <h4 style="margin-top:0; font-size:1.1rem;">3. Eyes on the Dashboard</h4>
                            <p>
                                <strong>Top Bar:</strong> Your Moral Compass score updates as you progress.<br>
                                <strong>Standings Below:</strong> Team and individual leaderboards re-rank in
                                real-time as you and your colleagues complete modules.
                            </p>
                            <p style="margin-bottom:0;">
                                The goal is not just to be accurate, but to be <strong>accurate and safe</strong>
                                in the ways that matter for people’s lives.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 1,
        "title": "Phase I: The Setup — Your Mission",
        "sim_acc": 0.70,
        "sim_comp": 25,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🕵️‍♀️ Your Next Mission: Investigate AI Bias</h2>
                <div class="slide-body">
                    
                    <!-- Role Badge -->
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="
                            display:inline-flex;
                            align-items:center;
                            gap:10px;
                            padding:10px 18px;
                            border-radius:999px;
                            background:var(--background-fill-secondary);
                            border:1px solid var(--border-color-primary);
                            font-size:0.95rem;
                            text-transform:uppercase;
                            letter-spacing:0.08em;
                            font-weight:700;
                        ">
                            <span style="font-size:1.1rem;">🎟️</span>
                            <span>ACCESS GRANTED: <span style="color:var(--color-accent);">BIAS DETECTIVE</span></span>
                        </div>
                    </div>

                    <!-- Target Header -->
                    <h3 style="font-size:1.3rem; margin-top:0; text-align:center;">
                        ⚡ Your Target: <span style="color:var(--color-accent);">Find Hidden AI Bias</span>
                    </h3>

                    <!-- Narrative Hook -->
                    <p style="font-size:1.05rem; max-width:780px; margin:14px auto 22px auto; text-align:center;">
                        This AI model claims to be neutral, but we suspect it is unfair.
                        Your mission is simple: <strong>uncover the bias hiding inside the training data</strong>
                        before this system hurts real people.
                        <br><br>
                        If you can't find it, we can't fix it.
                    </p>

                    <!-- Investigation Roadmap -->
                    <div class="ai-risk-container" style="margin-top:10px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            🔍 Investigation Roadmap
                        </h4>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:12px;">
                            
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700; margin-bottom:6px;">
                                    Step 1: 🛡️ LEARN THE RULES
                                </div>
                                <div style="font-size:0.95rem;">
                                    What actually counts as bias? Before we accuse the model, we need a clear
                                    standard for fairness and harm.
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700; margin-bottom:6px;">
                                    Step 2: 📡 SCAN THE DATA
                                </div>
                                <div style="font-size:0.95rem;">
                                    Where is the bias hiding? You’ll look for patterns in who is misclassified,
                                    underrepresented, or treated unfairly.
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700; margin-bottom:6px;">
                                    Step 3: ⚖️ PROVE THE ERROR
                                </div>
                                <div style="font-size:0.95rem;">
                                    How unfair is it? You’ll gather evidence that the model’s errors are not random,
                                    but systematically skewed.
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700; margin-bottom:6px;">
                                    Step 4: 📝 DIAGNOSE HARM
                                </div>
                                <div style="font-size:0.95rem;">
                                    File the fairness report: who is being harmed, how, and what needs to change
                                    before this model is deployable.
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- CTA copy (button is wired in Python) -->
                    <div style="text-align:center; margin-top:24px;">
                        <p style="margin-bottom:10px; font-size:1.0rem;">
                            When you’re ready, lock in your role and continue to your first intelligence briefing.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 2,
        "title": "Step 1: Intelligence Briefing — The Detective’s Code",
        "sim_acc": 0.78,
        "sim_comp": 50,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚖️ The Detective's Code</h2>
                <div class="slide-body">
                    
                    <!-- Badge -->
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="
                            display:inline-flex;
                            align-items:center;
                            gap:10px;
                            padding:10px 18px;
                            border-radius:999px;
                            background:var(--background-fill-secondary);
                            border:1px solid var(--border-color-primary);
                            font-size:0.95rem;
                            text-transform:uppercase;
                            letter-spacing:0.08em;
                            font-weight:700;
                        ">
                            <span style="font-size:1.1rem;">📜</span>
                            <span>STEP 1: INTELLIGENCE BRIEFING</span>
                        </div>
                    </div>

                    <!-- Narrative / Authority -->
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We don't guess. We investigate based on the standards set by the experts at the
                        <strong>Catalan Observatory for Ethics in AI (OEIAC)</strong>.
                        <br><br>
                        While they established <strong>7 core principles</strong> to keep AI safe, our intel suggests
                        this specific case involves a violation of what we will treat as
                        <strong>Principle #1 in this investigation: Justice &amp; Fairness</strong>
                        — formally captured in their principle of <strong>Justice and Equity</strong>.
                    </p>

                    <!-- Principles Grid -->
                    <div class="ai-risk-container" style="margin-top:10px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            🧩 Key Ethical Principles (OEIAC Framework)
                        </h4>
                        <p style="font-size:0.95rem; text-align:center; margin-bottom:14px;">
                            These principles define the ground rules for trustworthy AI.
                            One of them is already flagged as <strong style="color:#ef4444;">case priority</strong>.
                        </p>

                        <div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; margin-top:10px;">
                            <!-- 1: Transparency and Explainability -->
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    1 · Transparency and Explainability
                                </div>
                            </div>

                            <!-- 2: Justice and Equity (CASE PRIORITY) -->
                            <div class="hint-box" style="
                                margin-top:0;
                                font-size:0.9rem;
                                border-width:2px;
                                border-color:#ef4444;
                                box-shadow:0 0 0 1px rgba(239,68,68,0.12);
                                background:linear-gradient(
                                    135deg,
                                    rgba(239,68,68,0.06),
                                    var(--block-background-fill)
                                );
                            ">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                        2 · Justice and Equity
                                    </div>
                                    <div style="
                                        font-size:0.7rem;
                                        text-transform:uppercase;
                                        letter-spacing:0.12em;
                                        font-weight:800;
                                        padding:2px 8px;
                                        border-radius:999px;
                                        border:1px solid #ef4444;
                                        color:#ef4444;
                                        background-color:rgba(239,68,68,0.08);
                                    ">
                                        ⚠️ CASE PRIORITY
                                    </div>
                                </div>
                                <div style="font-size:0.8rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Also referred to here as <strong>Justice &amp; Fairness</strong>.
                                    Who pays the price when the model is wrong?
                                </div>
                            </div>

                            <!-- 3: Safety and Non-Maleficence -->
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    3 · Safety and Non-Maleficence
                                </div>
                            </div>

                            <!-- 4: Responsibility and Accountability -->
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    4 · Responsibility and Accountability
                                </div>
                            </div>

                            <!-- 5: Privacy -->
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    5 · Privacy
                                </div>
                            </div>

                            <!-- 6: Autonomy -->
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    6 · Autonomy
                                </div>
                            </div>

                            <!-- 7: Sustainability -->
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    7 · Sustainability
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- CTA copy (button is wired in Python) -->
                    <div style="text-align:center; margin-top:24px;">
                        <p style="margin-bottom:10px; font-size:1.0rem;">
                            You now have your ethical playbook. Next, we initialize the
                            <strong>Investigation Protocol</strong> to test whether this model is quietly
                            breaking Justice &amp; Fairness.
                        </p>
                    </div>
                </div>
            </div>
        """
    }
]

# --- 5. LEADERBOARD HELPERS ---

def get_or_assign_team(client, username):
    """
    Get user's existing team from leaderboard or assign a default team.
    Returns team_name string.
    """
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])
        
        # Look for existing team assignment
        my_user = next((u for u in users if u.get("username") == username), None)
        if my_user and my_user.get("teamName"):
            return my_user.get("teamName")
        
        # If no team found, return default
        return "team-a"
    except Exception:
        # Fallback to default team
        return "team-a"

def get_leaderboard_data(client, username, team_name):
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])
        
        users_sorted = sorted(
            users,
            key=lambda x: float(x.get("moralCompassScore", 0) or 0),
            reverse=True
        )
        my_user = next((u for u in users_sorted if u.get("username") == username), None)
        score = float(my_user.get("moralCompassScore", 0) or 0) if my_user else 0.0
        rank = users_sorted.index(my_user) + 1 if my_user else 0
        
        team_map = {}
        for u in users:
            t = u.get("teamName")
            s = float(u.get("moralCompassScore", 0) or 0)
            if t:
                if t not in team_map:
                    team_map[t] = {"sum": 0, "count": 0}
                team_map[t]["sum"] += s
                team_map[t]["count"] += 1
        
        teams_sorted = []
        for t, d in team_map.items():
            teams_sorted.append({"team": t, "avg": d["sum"] / d["count"]})
        teams_sorted.sort(key=lambda x: x["avg"], reverse=True)
        
        my_team = next((t for t in teams_sorted if t['team'] == team_name), None)
        team_rank = teams_sorted.index(my_team) + 1 if my_team else 0
        
        return {
            "score": score,
            "rank": rank,
            "team_rank": team_rank,
            "all_users": users_sorted,
            "all_teams": teams_sorted
        }
    except Exception as e:
        print(f"Leaderboard Error: {e}")
        return None

def ensure_table_and_get_data(username, token, team_name):
    """Get leaderboard data using username and token directly."""
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

    try:
        client.get_table(TABLE_ID)
    except Exception:
        try:
            client.create_table(table_id=TABLE_ID, display_name="LMS", playground_url="x")
        except Exception:
            pass

    data = get_leaderboard_data(client, username, team_name)
    return data, username

def trigger_api_update(username, token, team_name, module_id):
    """Update moral compass score using username and token directly."""
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    
    try:
        client.get_table(TABLE_ID)
    except Exception:
        try:
            client.create_table(table_id=TABLE_ID, display_name="LMS", playground_url="x")
        except Exception:
            pass
    
    mod = next(m for m in MODULES if m["id"] == module_id)
    acc = mod["sim_acc"]
    comp_pct = mod["sim_comp"]
    
    prev_data = get_leaderboard_data(client, username, team_name)

    client.update_moral_compass(
        table_id=TABLE_ID,
        username=username,
        team_name=team_name,
        metrics={"accuracy": acc},
        tasks_completed=int(10 * (comp_pct / 100)),
        total_tasks=10,
        questions_correct=0,
        total_questions=0,
        primary_metric="accuracy"
    )
    time.sleep(0.5)
    
    new_data = get_leaderboard_data(client, username, team_name)
    return prev_data, new_data, username

# --- 6. RENDERERS ---

def render_top_dashboard(data, module_id):
    if not data:
        return """
        <div class="summary-box">
            <div class="summary-box-inner">
                <div class="summary-metrics">
                    <div style="text-align:center;">
                        <div class="label-text">Moral Compass Score</div>
                        <div class="score-text-primary">🧭 0.000</div>
                    </div>
                    <div class="divider-vertical"></div>
                    <div style="text-align:center;">
                        <div class="label-text">Team Rank</div>
                        <div class="score-text-team">–</div>
                    </div>
                    <div class="divider-vertical"></div>
                    <div style="text-align:center;">
                        <div class="label-text">Global Rank</div>
                        <div class="score-text-global">–</div>
                    </div>
                </div>
                <div class="summary-progress">
                    <div class="progress-label">
                        Course Progress: 0%
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width:0%;"></div>
                    </div>
                </div>
            </div>
        </div>
        """
    progress_pct = int(((module_id + 1) / len(MODULES)) * 100)
    
    return f"""
    <div class="summary-box">
        <div class="summary-box-inner">
            <div class="summary-metrics">
                <div style="text-align:center;">
                    <div class="label-text">Moral Compass Score</div>
                    <div class="score-text-primary">🧭 {data['score']:.3f}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Team Rank</div>
                    <div class="score-text-team">#{data['team_rank']}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Global Rank</div>
                    <div class="score-text-global">#{data['rank']}</div>
                </div>
            </div>
            <div class="summary-progress">
                <div class="progress-label">
                    Course Progress: {progress_pct}%
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{progress_pct}%;"></div>
                </div>
            </div>
        </div>
    </div>
    """

def render_team_table(data, team_name):
    if not data or not data.get("all_teams"):
        return "<p>No team standings yet. Complete a module to activate your Moral Compass.</p>"
    rows = ""
    for idx, t in enumerate(data["all_teams"]):
        is_mine = (t["team"] == team_name)
        row_class = "row-highlight-team" if is_mine else "row-normal"
        rows += f"""
        <tr class="{row_class}">
            <td style="padding:12px; text-align:center;">{idx+1}</td>
            <td style="padding:12px;">{t['team']}</td>
            <td style="padding:12px; text-align:right;">{t['avg']:.3f}</td>
        </tr>
        """
    return f"""
    <div class="table-container">
        <table class="leaderboard-table">
            <thead>
                <tr>
                    <th style="padding:12px;">Rank</th>
                    <th style="padding:12px; text-align:left;">Team</th>
                    <th style="padding:12px; text-align:right;">Avg Moral Compass Score 🧭</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """

def render_user_table(data, username):
    if not data or not data.get("all_users"):
        return "<p>No individual scores yet. Complete a module to activate your Moral Compass.</p>"
    rows = ""
    for idx, u in enumerate(data["all_users"]):
        is_me = (u.get("username") == username)
        row_class = "row-highlight-me" if is_me else "row-normal"
        rows += f"""
        <tr class="{row_class}">
            <td style="padding:12px; text-align:center;">{idx+1}</td>
            <td style="padding:12px;">{u.get('username','')}</td>
            <td style="padding:12px; text-align:right;">{float(u.get('moralCompassScore',0)):.3f}</td>
        </tr>
        """
    return f"""
    <div class="table-container">
        <table class="leaderboard-table">
            <thead>
                <tr>
                    <th style="padding:12px;">Rank</th>
                    <th style="padding:12px; text-align:left;">Agent</th>
                    <th style="padding:12px; text-align:right;">Moral Compass Score 🧭</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """

def render_leaderboard_card(data, username, team_name):
    team_html = render_team_table(data, team_name)
    user_html = render_user_table(data, username)
    return f"""
    <div class="scenario-box leaderboard-card">
        <h3 class="slide-title" style="text-align:left; margin-bottom:10px;">
            📊 Live Moral Compass Standings
        </h3>
        <div class="lb-tabs">
            <input type="radio" id="lb-tab-team" name="lb-tabs" checked>
            <label for="lb-tab-team" class="lb-tab-label">🏆 Team Standings</label>
            <input type="radio" id="lb-tab-user" name="lb-tabs">
            <label for="lb-tab-user" class="lb-tab-label">👤 Individual Leaderboard</label>

            <div class="lb-tab-panels">
                <div class="lb-panel panel-team">
                    {team_html}
                </div>
                <div class="lb-panel panel-user">
                    {user_html}
                </div>
            </div>
        </div>
    </div>
    """

# --- 7. QUIZ LOGIC FOR MODULE 0 ---

CORRECT_ANSWER_0 = "A) Because simple accuracy ignores potential bias and harm."

def submit_quiz_0(username, token, team_name, module0_done, answer):
    if answer is None:
        return (
            gr.update(),  # out_top
            gr.update(),  # leaderboard_html
            module0_done,
            "<div class='hint-box'>Please select an answer before moving on.</div>",
        )

    if answer != CORRECT_ANSWER_0:
        return (
            gr.update(),
            gr.update(),
            module0_done,
            "<div class='hint-box'>❌ Not quite. Think about what accuracy leaves out. A model can be accurate on average yet still cause harm for certain groups.</div>",
        )

    if module0_done:
        data, username = ensure_table_and_get_data(username, token, team_name)
        html_top = render_top_dashboard(data, module_id=0)
        lb_html = render_leaderboard_card(data, username, team_name)
        msg_html = f"""
        <div class="profile-card risk-low" style="text-align:center;">
            <h2 style="color:#22c55e; margin:0 0 10px 0;">✅ Already Unlocked</h2>
            <p style="font-size:1.05rem; margin-bottom:6px;">
                You've already activated your <strong>Module 0 Moral Compass</strong>.
            </p>
            <p style="font-size:0.95rem;">
                Your current score is <strong>{data['score']:.3f}</strong> with a global rank of
                <strong>#{data['rank']}</strong>. You can move on to the next module at any time.
            </p>
        </div>
        """
        return (
            gr.update(value=html_top),
            gr.update(value=lb_html),
            module0_done,
            gr.update(value=msg_html),
        )

    prev, curr, username = trigger_api_update(username, token, team_name, module_id=0)

    d_score = curr["score"] - (prev["score"] if prev else 0.0)
    prev_rank = prev["rank"] if prev and prev.get("rank") else 999
    curr_rank = curr["rank"]
    rank_diff = prev_rank - curr_rank

    if rank_diff > 0:
        rank_msg = f"Up {rank_diff} spots!"
        rank_color = "#22c55e"
    elif rank_diff < 0:
        rank_msg = f"Down {abs(rank_diff)} spots"
        rank_color = "#ef4444"
    else:
        rank_msg = "No change"
        rank_color = "var(--secondary-text-color)"

    msg_html = f"""
    <div class="profile-card risk-low" style="text-align:center;">
        <h2 style="color:#22c55e; margin:0 0 10px 0;">🚀 Correct! Baseline Established.</h2>
        <div style="display:flex; justify-content:space-around; align-items:center; margin:15px 0;">
            <div>
                <div class="label-text">Score Increase</div>
                <div style="font-size:1.8rem; font-weight:bold; color:var(--color-accent);">
                    +{d_score:.3f}
                </div>
            </div>
            <div>
                <div class="label-text">Rank Change</div>
                <div style="font-size:1.8rem; font-weight:bold; color:{rank_color};">
                    {rank_msg}
                </div>
            </div>
        </div>
        <p style="font-size:1.05rem; margin-bottom:6px;">
            Your <strong>Ethical Progress</strong> multiplier just activated for this module.
        </p>
        <p style="font-size:0.95rem; font-weight:bold; color:var(--body-text-color);">
            👀 Check the <span style="color:var(--color-accent)">dashboard above</span> and 
            <span style="color:var(--color-accent)">standings below</span> to see your new status.
        </p>
    </div>
    """

    html_top = render_top_dashboard(curr, module_id=0)
    lb_html = render_leaderboard_card(curr, username, team_name)

    return (
        gr.update(value=html_top),
        gr.update(value=lb_html),
        True,
        gr.update(value=msg_html),
    )

# --- 8. CSS ---

css = """
/* Top summary bar layout */
.summary-box {
    background-color: var(--block-background-fill);
    color: var(--body-text-color);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid var(--border-color-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    margin-bottom: 20px;
}

.summary-box-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 30px;
}

.summary-metrics {
    display: flex;
    align-items: center;
    gap: 30px;
}

.summary-progress {
    width: 520px;
}

.progress-label {
    text-align: left;
    margin-bottom: 6px;
    color: var(--body-text-color);
    font-weight: 600;
    font-size: 0.85rem;
}

/* Scenario / content cards */
.scenario-box {
    font-size: 1.2rem;
    padding: 24px;
    border-radius: 12px;
    background-color: var(--block-background-fill);
    color: var(--body-text-color);
    border: 1px solid var(--border-color-primary);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    margin-bottom: 20px;
}

.slide-title {
    margin-top: 0;
    font-size: 1.8rem;
    text-align: left;
}

.slide-body {
    font-size: 1.1rem;
    line-height: 1.7;
}

/* Hint / quiz feedback */
.hint-box {
    font-size: 0.95rem;
    padding: 14px;
    border-radius: 8px;
    background-color: var(--block-background-fill);
    color: var(--body-text-color);
    border: 1px solid var(--border-color-primary);
    margin-top: 12px;
}

/* Profile-style card (for dynamic quiz result) */
.profile-card {
    background-color: var(--block-background-fill);
    color: var(--body-text-color);
    padding: 20px;
    border-radius: 12px;
    border-left: 6px solid var(--border-color-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    margin-top: 16px;
}
.risk-low { border-left-color: #22c55e; }

/* Progress bar visuals */
.label-text {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--body-text-color-subdued);
    letter-spacing: 0.5px;
}

.score-text-primary { font-size: 2.0rem; font-weight: 800; color: var(--color-accent); }
.score-text-team    { font-size: 2.0rem; font-weight: 800; color: #60a5fa; }
.score-text-global  { font-size: 2.0rem; font-weight: 800; color: var(--body-text-color); }

.divider-vertical {
    width: 1px;
    height: 40px;
    background: var(--border-color-primary);
}

.progress-bar-bg {
    width: 100%;
    height: 8px;
    background: var(--background-fill-primary);
    border-radius: 4px;
    overflow: hidden;
    margin-top: 5px;
}

.progress-bar-fill {
    height: 100%;
    background: var(--color-accent);
}

/* Leaderboard card */
.leaderboard-card {
    margin-top: 24px;
}

/* CSS-only tabs inside leaderboard card */
.leaderboard-card .lb-tabs {
    margin-top: 8px;
}

/* Hide the radio controls */
.leaderboard-card input[type="radio"] {
    display: none;
}

/* Tab labels */
.leaderboard-card .lb-tab-label {
    display: inline-block;
    padding: 6px 14px;
    margin-right: 8px;
    border-radius: 999px;
    font-size: 0.9rem;
    cursor: pointer;
    border: 1px solid var(--border-color-primary);
    background-color: var(--background-fill-primary);
    color: var(--body-text-color);
}

/* Active tab styling */
.leaderboard-card #lb-tab-team:checked + label {
    background-color: var(--color-accent);
    color: #ffffff;
    border-color: var(--color-accent);
}
.leaderboard-card #lb-tab-user:checked + label {
    background-color: var(--color-accent);
    color: #ffffff;
    border-color: var(--color-accent);
}

/* Tab panels */
.leaderboard-card .lb-tab-panels {
    margin-top: 10px;
}

.leaderboard-card .lb-panel {
    display: none;
}

.leaderboard-card #lb-tab-team:checked ~ .lb-tab-panels .panel-team {
    display: block;
}

.leaderboard-card #lb-tab-team:checked ~ .lb-tab-panels .panel-user {
    display: none;
}

.leaderboard-card #lb-tab-user:checked ~ .lb-tab-panels .panel-team {
    display: none;
}

.leaderboard-card #lb-tab-user:checked ~ .lb-tab-panels .panel-user {
    display: block;
}

/* Tables */
.table-container {
    height: 300px;
    overflow-y: auto;
    padding: 0;
    border: 1px solid var(--border-color-primary);
    border-radius: 8px;
    background-color: var(--block-background-fill);
}

.leaderboard-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}

.leaderboard-table th {
    background-color: var(--background-fill-secondary);
    position: sticky;
    top: 0;
    color: var(--body-text-color);
    padding: 10px;
    font-weight: 600;
    border-bottom: 2px solid var(--border-color-primary);
}

.row-normal {
    border-bottom: 1px solid var(--border-color-primary);
}

/* Highlight rows using the same blue hue as Team Rank (#60a5fa) */
.row-highlight-me,
.row-highlight-team {
    background-color: rgba(96, 165, 250, 0.18);
    border-bottom: 1px solid var(--border-color-primary);
    font-weight: 600;
}

/* AI risk container */
.ai-risk-container {
    margin-top: 16px;
    padding: 12px;
    background-color: var(--body-background-fill);
    border-radius: 8px;
    border: 1px solid var(--border-color-primary);
}

/* Dark mode tweaks */
@media (prefers-color-scheme: dark) {
    .scenario-box,
    .summary-box,
    .hint-box,
    .table-container,
    .leaderboard-card,
    .profile-card {
        background-color: #2D323E;
        color: white;
        border-color: #555555;
        box-shadow: none;
    }

    .ai-risk-container {
        background-color: #181B22;
        border-color: #555555;
    }

    .leaderboard-table th {
        background-color: #1f2937;
        color: white;
        border-bottom-color: #555555;
    }
}
"""

# --- 9. BUILD APP (Bias Detective) ---

def create_bias_detective_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # State - now stores username and token directly
        username_state = gr.State(value=None)
        token_state    = gr.State(value=None)
        team_state     = gr.State(value=None)
        module0_done   = gr.State(value=False)

        # Title
        gr.Markdown("# 🕵️‍♀️ Bias Detective: Moral Compass Lab")

        # Top dashboard
        out_top = gr.HTML()

        # Module 0
        with gr.Column(visible=True) as module_0:
            mod0_html = gr.HTML(MODULES[0]["html"])
            quiz_q = gr.Markdown(
                "### 🧠 Quick Knowledge Check\n\n"
                "**Why do we multiply your Accuracy by Ethical Progress?**"
            )
            quiz_radio = gr.Radio(
                label="Select your answer:",
                choices=[
                    "A) Because simple accuracy ignores potential bias and harm.",
                    "B) To make the leaderboard math more complicated.",
                    "C) Accuracy is the only metric that actually matters.",
                ]
            )
            quiz_feedback = gr.HTML("")
            btn_next_0 = gr.Button("Complete Module & Next ➡️", variant="primary")

        # Module 1 – Mission
        with gr.Column(visible=False) as module_1:
            mod1_html = gr.HTML(MODULES[1]["html"])
            with gr.Row():
                btn_prev_1 = gr.Button("⬅️ Previous")
                btn_next_1 = gr.Button("Begin Intelligence Briefing ▶️", variant="primary")

        # Module 2 – Detective’s Code (OEIAC principles)
        with gr.Column(visible=False) as module_2:
            mod2_html = gr.HTML(MODULES[2]["html"])
            with gr.Row():
                btn_prev_2 = gr.Button("⬅️ Back to Mission")
                btn_next_2 = gr.Button("Initialize Investigation Protocol ▶️", variant="primary")

        # Leaderboard card at the bottom
        leaderboard_html = gr.HTML()

        # Quiz scoring for module 0
        quiz_radio.change(
            fn=submit_quiz_0,
            inputs=[username_state, token_state, team_state, module0_done, quiz_radio],
            outputs=[out_top, leaderboard_html, module0_done, quiz_feedback],
        )

        # Initial load with session-based auth
        def handle_initial_load(request: gr.Request):
            """
            Authenticate via session token on page load.
            """
            success, username, token = _try_session_based_auth(request)
            
            if success and username and token:
                # Get or assign team based on user's leaderboard data
                os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
                client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
                team_name = get_or_assign_team(client, username)
                
                data, username = ensure_table_and_get_data(username, token, team_name)
                html_top = render_top_dashboard(data, module_id=0)
                lb_html = render_leaderboard_card(data, username, team_name)
                
                return (
                    username,        # username_state
                    token,           # token_state
                    team_name,       # team_state
                    False,           # module0_done
                    html_top,        # out_top
                    lb_html,         # leaderboard_html
                )
            else:
                # No valid session - show empty state
                return (
                    None,            # username_state
                    None,            # token_state
                    None,            # team_state
                    False,           # module0_done
                    "<div class='hint-box'>⚠️ Authentication required. Please access this app with a valid session ID.</div>",
                    "",              # leaderboard_html
                )

        demo.load(
            fn=handle_initial_load,
            inputs=None,
            outputs=[
                username_state,
                token_state,
                team_state,
                module0_done,
                out_top,
                leaderboard_html,
            ],
        )

        # Next: Module 0 -> Module 1 (score update for module 1)
        def on_next_from_module_0(username, token, team, answer):
            if answer is None:
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    "<div class='hint-box'>Please select an answer before continuing.</div>",
                )
            _, new_data, username = trigger_api_update(username, token, team, module_id=1)
            html_top  = render_top_dashboard(new_data, module_id=1)
            lb_html   = render_leaderboard_card(new_data, username, team)
            return (
                gr.update(value=html_top),
                gr.update(value=lb_html),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
            )

        btn_next_0.click(
            fn=on_next_from_module_0,
            inputs=[username_state, token_state, team_state, quiz_radio],
            outputs=[out_top, leaderboard_html, module_0, module_1, module_2],
        )

        # Prev: Module 1 -> Module 0
        def on_prev_from_module_1():
            return (
                gr.update(visible=True),
                gr.update(visible=False),
            )

        btn_prev_1.click(
            fn=on_prev_from_module_1,
            inputs=None,
            outputs=[module_0, module_1],
        )

        # Next: Module 1 -> Module 2 (progress bump + refresh)
        def on_next_from_module_1(username, token, team):
            data, username = ensure_table_and_get_data(username, token, team)
            html_top = render_top_dashboard(data, module_id=2)
            lb_html  = render_leaderboard_card(data, username, team)
            return (
                gr.update(value=html_top),
                gr.update(value=lb_html),
                gr.update(visible=False),
                gr.update(visible=True),
            )

        btn_next_1.click(
            fn=on_next_from_module_1,
            inputs=[username_state, token_state, team_state],
            outputs=[out_top, leaderboard_html, module_1, module_2],
        )

        # Prev: Module 2 -> Module 1
        def on_prev_from_module_2():
            return (
                gr.update(visible=True),
                gr.update(visible=False),
            )

        btn_prev_2.click(
            fn=on_prev_from_module_2,
            inputs=None,
            outputs=[module_1, module_2],
        )

        # Finish from Module 2
        def on_finish_from_module_2():
            return "<div class='summary-box'><h3>✅ Briefing Complete</h3><p>You’ve completed Phase I: Moral Compass + Intelligence Briefing. Next, you’ll begin scanning the model for signs of bias.</p></div>"

        btn_next_2.click(
            fn=on_finish_from_module_2,
            inputs=None,
            outputs=[out_top],
        )

    return demo




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

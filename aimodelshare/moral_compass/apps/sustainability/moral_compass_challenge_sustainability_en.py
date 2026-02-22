import os
import sys
import subprocess
import time
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://bhtrtkrbf4.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "sustainabilitymc"
FALLBACK_TABLE_ID = "sustainabilitymcfallback"
TOTAL_COURSE_TASKS = 10  # Score calculated against full course
LOCAL_TEST_SESSION_ID = None


# --- 2. SETUP & DEPENDENCIES ---
def install_dependencies():
    packages = ["gradio>=5.0.0", "aimodelshare", "pandas"]
    for package in packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])


try:
    import gradio as gr
    import pandas as pd
    from aimodelshare.playground import Competition
    from aimodelshare.moral_compass import MoralcompassApiClient
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    print("Installing dependencies...")
    install_dependencies()
    import gradio as gr
    import pandas as pd
    from aimodelshare.playground import Competition
    from aimodelshare.moral_compass import MoralcompassApiClient
    from aimodelshare.aws import get_token_from_session, _get_username_from_token

# --- 3. AUTH & HISTORY HELPERS ---
def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id and LOCAL_TEST_SESSION_ID:
            session_id = LOCAL_TEST_SESSION_ID
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
        return False, None, None


def fetch_user_history(username, token):
    default_acc = 0.0
    default_team = "Team-Unassigned"
    try:
        playground = Competition(ORIGINAL_PLAYGROUND_URL)
        df = playground.get_leaderboard(token=token)
        if df is None or df.empty:
            return default_acc, default_team
        if "username" in df.columns and "accuracy" in df.columns:
            user_rows = df[df["username"] == username]
            if not user_rows.empty:
                best_acc = user_rows["accuracy"].max()
                if "timestamp" in user_rows.columns and "Team" in user_rows.columns:
                    try:
                        user_rows = user_rows.copy()
                        user_rows["timestamp"] = pd.to_datetime(
                            user_rows["timestamp"], errors="coerce"
                        )
                        user_rows = user_rows.sort_values("timestamp", ascending=False)
                        found_team = user_rows.iloc[0]["Team"]
                        if pd.notna(found_team) and str(found_team).strip():
                            default_team = str(found_team).strip()
                    except Exception:
                        pass
                return float(best_acc), default_team
    except Exception:
        pass
    return default_acc, default_team


# --- 4. LEADERBOARD DATA HELPERS ---
def get_leaderboard_data(client, username, team_name, local_task_list=None, override_score=None):
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])

        if override_score is not None:
            found = False
            for u in users:
                if u.get("username") == username:
                    u["moralCompassScore"] = override_score
                    found = True
                    break
            if not found:
                users.append(
                    {"username": username, "moralCompassScore": override_score, "teamName": team_name}
                )

        users_sorted = sorted(
            users, key=lambda x: float(x.get("moralCompassScore", 0) or 0), reverse=True
        )

        my_user = next((u for u in users_sorted if u.get("username") == username), None)
        score = float(my_user.get("moralCompassScore", 0) or 0) if my_user else 0.0
        rank = users_sorted.index(my_user) + 1 if my_user else 0

        completed_task_ids = (
            local_task_list
            if local_task_list is not None
            else (my_user.get("completedTaskIds", []) if my_user else [])
        )

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
        my_team = next((t for t in teams_sorted if t["team"] == team_name), None)
        team_rank = teams_sorted.index(my_team) + 1 if my_team else 0
        return {
            "score": score,
            "rank": rank,
            "team_rank": team_rank,
            "all_users": users_sorted,
            "all_teams": teams_sorted,
            "completed_task_ids": completed_task_ids,
        }
    except Exception:
        return None


def ensure_table_and_get_data(username, token, team_name, task_list_state=None):
    global TABLE_ID
    if not username or not token:
        return None, username
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    try:
        client.get_table(TABLE_ID)
    except Exception:
        try:
            client.get_table(FALLBACK_TABLE_ID)
            TABLE_ID = FALLBACK_TABLE_ID
        except Exception:
            pass
    return get_leaderboard_data(client, username, team_name, task_list_state), username


# ============================================================================
# 5. MODULE DEFINITIONS — 4-PAGE MORAL COMPASS CHALLENGE
# ============================================================================
# Module 0: Certification Day (celebration → checklist failure)
# Module 1: The Hidden Bill (3 tap-to-unlock audit sections)
# Module 2: Score Reset + The New Formula (gauge drain → what-if slider)
# Module 3: Mission Briefing (mission cards + leaderboard + CTA)
# ============================================================================

MODULES = [
    # ─────────────────────────────────────────────
    # MODULE 0 — CERTIFICATION DAY
    # ─────────────────────────────────────────────
    {
        "id": 0,
        "title": "Certification Day",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <!-- Phase 1: Celebration -->
                <div id="mcc-cert-phase1">
                    <div class="mcc-intro-page">
                        <div class="mcc-reveal" style="animation-delay:0s;">
                            <div style="font-size:0.875rem; font-weight:800; letter-spacing:3px; color:var(--mcc-success); text-transform:uppercase; margin-bottom:24px; text-align:center;">
                                Certification Day
                            </div>
                        </div>
                        <div class="mcc-reveal" style="animation-delay:0.3s;">
                            <h1 style="font-size:clamp(1.8rem, 6vw, 2.8rem); font-weight:800; text-align:center; line-height:1.1; letter-spacing:-1px; color:var(--mcc-text); margin:0 0 28px 0;">
                                <span id="mcc-typewriter-text"></span><span class="mcc-blink" style="color:var(--mcc-success);">|</span>
                            </h1>
                        </div>
                        <div id="mcc-stats-reveal" style="opacity:0; transform:translateY(20px); transition:all 0.8s ease;">
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin:30px 0; max-width:500px; width:100%;">
                                <div class="mcc-stat-card">
                                    <div class="mcc-stat-value" style="color:var(--mcc-success);" id="mcc-accuracy-display">75.0%</div>
                                    <div class="mcc-stat-label">Model Accuracy</div>
                                </div>
                                <div class="mcc-stat-card">
                                    <div class="mcc-stat-value" style="color:var(--mcc-success);" id="mcc-rank-display">#N/A</div>
                                    <div class="mcc-stat-label">Global Rank</div>
                                </div>
                            </div>
                            <div id="mcc-achievement-reveal" style="opacity:0; transform:translateY(15px); transition:all 0.6s ease;">
                                <div style="border:2px solid var(--mcc-success); background:var(--mcc-success-bg); border-radius:16px; padding:20px 24px; margin-bottom:24px; max-width:500px; width:100%;">
                                    <p style="margin:0; font-size:1.05rem; line-height:1.6; color:var(--mcc-text); text-align:center;">
                                        <strong style="color:var(--mcc-success);">Achievement Unlocked:</strong><br>
                                        You built an AI that predicts which buildings waste energy. Real satellite data. Real predictions. That's real engineering.
                                    </p>
                                </div>
                                <div style="text-align:center;">
                                    <button id="mcc-certify-btn" class="mcc-btn mcc-btn-success" onclick="mccStartChecklist()" style="font-size:1.2rem; padding:20px 40px; width:100%; max-width:500px;">
                                        CERTIFY MY MODEL &rarr;
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Phase 2: Checklist -->
                <div id="mcc-cert-phase2" style="display:none;">
                    <div style="text-align:center; margin-bottom:24px;">
                        <div style="font-size:0.875rem; font-weight:800; letter-spacing:3px; color:var(--mcc-accent); text-transform:uppercase; margin-bottom:12px;">
                            Certification Audit
                        </div>
                        <h2 style="font-size:clamp(1.4rem, 4vw, 1.8rem); font-weight:800; color:var(--mcc-text); margin:0;">
                            Running Pre-Certification Checks...
                        </h2>
                    </div>

                    <div style="max-width:560px; margin:30px auto;">
                        <div class="mcc-checklist-item" id="mcc-check-0" style="opacity:0.3;">
                            <span class="mcc-check-icon" id="mcc-check-icon-0">&#9744;</span>
                            <span>Model architecture validated</span>
                        </div>
                        <div class="mcc-checklist-item" id="mcc-check-1" style="opacity:0.3;">
                            <span class="mcc-check-icon" id="mcc-check-icon-1">&#9744;</span>
                            <span>Accuracy verified against test data</span>
                        </div>
                        <div class="mcc-checklist-item" id="mcc-check-2" style="opacity:0.3;">
                            <span class="mcc-check-icon" id="mcc-check-icon-2">&#9744;</span>
                            <span>Global ranking confirmed</span>
                        </div>
                        <div class="mcc-checklist-item" id="mcc-check-3" style="opacity:0.3;">
                            <span class="mcc-check-icon" id="mcc-check-icon-3">&#9744;</span>
                            <span>Dataset compliance checked</span>
                        </div>
                        <div class="mcc-checklist-item" id="mcc-check-4" style="opacity:0.3;">
                            <span class="mcc-check-icon" id="mcc-check-icon-4">&#9744;</span>
                            <span><strong>Do you know what your AI costs the planet?</strong></span>
                        </div>
                    </div>

                    <!-- Warning banner (hidden until animation completes) -->
                    <div id="mcc-cert-warning" style="display:none; max-width:560px; margin:20px auto;">
                        <div style="background:var(--mcc-accent-highlight); border:2px solid var(--mcc-accent); border-radius:16px; padding:24px; text-align:center;">
                            <h3 style="color:var(--mcc-accent); margin:0 0 12px 0; font-size:1.4rem; letter-spacing:2px;">WAIT &mdash; THERE'S SOMETHING YOU HAVEN'T SEEN.</h3>
                            <p style="margin:0 0 8px 0; font-size:1.05rem; color:var(--mcc-text);">
                                Your AI works. But every prediction it makes has a hidden cost &mdash; energy, water, and carbon emissions that most engineers never think about.
                            </p>
                            <p style="margin:0; font-size:1rem; color:var(--mcc-text-dim);">
                                Let's find out what that cost looks like.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 1 — HAVE YOU CONSIDERED THIS? (AI Environmental Awareness)
    # ─────────────────────────────────────────────
    {
        "id": 1,
        "title": "Have You Considered This?",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="mcc-reveal" style="animation-delay:0s;">
                    <div style="text-align:center; margin-bottom:8px;">
                        <div style="font-size:0.875rem; font-weight:800; letter-spacing:3px; color:var(--mcc-accent); text-transform:uppercase; margin-bottom:12px;">
                            The Hidden Cost of AI
                        </div>
                        <h2 style="font-size:clamp(1.4rem, 4vw, 1.8rem); font-weight:800; color:var(--mcc-text); margin:0 0 8px 0;">
                            Have You Considered This?
                        </h2>
                        <p style="font-size:1.05rem; color:var(--mcc-text-dim); margin:0 0 8px 0;">Tap each card to reveal what AI really costs.</p>
                        <div id="mcc-audit-progress" style="font-size:0.9rem; font-weight:700; color:var(--mcc-accent); margin-bottom:20px;">
                            0/3 revealed
                        </div>
                    </div>
                </div>

                <!-- Card 0: Energy -->
                <div class="mcc-reveal" style="animation-delay:0.15s;">
                    <div class="mcc-flip-card" id="mcc-card-0" onclick="mccFlipCard(0)">
                        <div class="mcc-flip-card-front">
                            <div style="font-size:2.5rem; margin-bottom:12px;">&#128274;</div>
                            <div style="font-size:1.1rem; font-weight:700; color:var(--mcc-text);">Energy</div>
                            <div style="font-size:0.9rem; color:var(--mcc-text-dim); margin-top:8px;">Tap to reveal</div>
                        </div>
                        <div class="mcc-flip-card-back" id="mcc-card-back-0">
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                                <div class="mcc-knockout-stat">
                                    <div style="font-size:2rem; margin-bottom:8px;">&#9889;</div>
                                    <div style="font-size:1.6rem; font-weight:800; color:var(--mcc-accent);">Bigger than a country</div>
                                    <p style="font-size:0.95rem; color:var(--mcc-text); margin:8px 0 0 0; line-height:1.5;">
                                        The world's data centers already use more electricity than <strong>the entire United Kingdom</strong> &mdash; and AI is the fastest-growing piece of that demand
                                    </p>
                                </div>
                                <div class="mcc-knockout-stat">
                                    <div style="font-size:2rem; margin-bottom:8px;">&#128200;</div>
                                    <div style="font-size:1.6rem; font-weight:800; color:var(--mcc-accent);">48&times; more energy in just 3 years</div>
                                    <p style="font-size:0.95rem; color:var(--mcc-text); margin:8px 0 0 0; line-height:1.5;">
                                        Each new generation of AI models is dramatically more power-hungry. Training the latest chatbots takes an estimated <strong>40&ndash;48&times; more energy</strong> than the version from just three years ago
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Card 1: Water -->
                <div class="mcc-reveal" style="animation-delay:0.3s;">
                    <div class="mcc-flip-card" id="mcc-card-1" onclick="mccFlipCard(1)">
                        <div class="mcc-flip-card-front">
                            <div style="font-size:2.5rem; margin-bottom:12px;">&#128274;</div>
                            <div style="font-size:1.1rem; font-weight:700; color:var(--mcc-text);">Water</div>
                            <div style="font-size:0.9rem; color:var(--mcc-text-dim); margin-top:8px;">Tap to reveal</div>
                        </div>
                        <div class="mcc-flip-card-back" id="mcc-card-back-1">
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                                <div class="mcc-knockout-stat">
                                    <div style="font-size:2rem; margin-bottom:8px;">&#128167;</div>
                                    <div style="font-size:1.6rem; font-weight:800; color:var(--mcc-accent);">As much water as every bottle sold on Earth</div>
                                    <p style="font-size:0.95rem; color:var(--mcc-text); margin:8px 0 0 0; line-height:1.5;">
                                        Researchers estimate AI's total water footprint now matches <strong>the world's entire bottled water supply</strong> &mdash; and most people have no idea
                                    </p>
                                </div>
                                <div class="mcc-knockout-stat">
                                    <div style="font-size:2rem; margin-bottom:8px;">&#127961;</div>
                                    <div style="font-size:1.6rem; font-weight:800; color:var(--mcc-accent);">One data center, one small city</div>
                                    <p style="font-size:0.95rem; color:var(--mcc-text); margin:8px 0 0 0; line-height:1.5;">
                                        A single large data center can drink up to <strong>5 million gallons of water per day</strong> &mdash; as much as a town of up to 50,000 people
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Card 2: Scale -->
                <div class="mcc-reveal" style="animation-delay:0.45s;">
                    <div class="mcc-flip-card" id="mcc-card-2" onclick="mccFlipCard(2)">
                        <div class="mcc-flip-card-front">
                            <div style="font-size:2.5rem; margin-bottom:12px;">&#128274;</div>
                            <div style="font-size:1.1rem; font-weight:700; color:var(--mcc-text);">Scale</div>
                            <div style="font-size:0.9rem; color:var(--mcc-text-dim); margin-top:8px;">Tap to reveal</div>
                        </div>
                        <div class="mcc-flip-card-back" id="mcc-card-back-2">
                            <div style="text-align:center;">
                                <div class="mcc-knockout-stat">
                                    <div style="font-size:2rem; margin-bottom:8px;">&#127981;</div>
                                    <div style="font-size:1.6rem; font-weight:800; color:var(--mcc-accent);">100,000 chips, 100,000 homes</div>
                                    <p style="font-size:0.95rem; color:var(--mcc-text); margin:8px 0 0 0; line-height:1.5;">
                                        Elon Musk's new "Colossus" data center uses around 100,000 specialized chips and consumes enough energy to power <strong>more than 100,000 homes</strong>.
                                    </p>
                                </div>
                                <p style="font-size:1rem; color:var(--mcc-text-dim); margin:16px 0 0 0; line-height:1.6;">
                                    And this is just <em>one</em> company. Google, Microsoft, Meta, and Amazon are all racing to build their own.
                                </p>
                                <p style="font-size:0.8rem; color:var(--mcc-text-dim); margin:12px 0 0 0; font-style:italic;">
                                    Sources: IEA, EESI, VU Amsterdam, TVA/xAI reporting (2024&ndash;2025)
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Summary after all 3 unlocked -->
                <div id="mcc-audit-summary" style="display:none; margin-top:20px;">
                    <div style="background:var(--mcc-accent-highlight); border:2px solid var(--mcc-accent); border-radius:16px; padding:20px 24px; text-align:center;">
                        <p style="margin:0; font-size:1.1rem; font-weight:600; color:var(--mcc-text); line-height:1.6;">
                            Energy. Water. Emissions. Every AI model has a cost beyond its accuracy score &mdash; <strong>and it's growing fast.</strong>
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 2 — SCORE RESET + THE NEW FORMULA
    # ─────────────────────────────────────────────
    {
        "id": 2,
        "title": "Score Reset",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <!-- Phase 1: Score Reset -->
                <div id="mcc-reset-phase1" style="text-align:center;">
                    <div class="mcc-reveal" style="animation-delay:0s;">
                        <h2 id="mcc-recalc-header" class="mcc-blink-red" style="font-size:clamp(1.4rem, 4vw, 1.8rem); font-weight:800; margin:0 0 30px 0; letter-spacing:2px; text-transform:uppercase;">
                            RECALCULATING YOUR SCORE...
                        </h2>
                    </div>

                    <div class="mcc-reveal" style="animation-delay:0.3s;">
                        <div class="mcc-gauge-container">
                            <div class="mcc-gauge" id="mcc-main-gauge">
                                <div class="mcc-gauge-inner">
                                    <div class="mcc-gauge-value" id="mcc-gauge-score">75</div>
                                    <div style="font-size:0.8rem; text-transform:uppercase; letter-spacing:2px; color:var(--mcc-text-dim);">SCORE</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div id="mcc-reset-message" style="opacity:0; transition:opacity 1s; max-width:560px; margin:0 auto;">
                        <p style="font-size:1.1rem; color:var(--mcc-text); line-height:1.6;">
                            Your accuracy remains at <strong id="mcc-accuracy-text">75.0%</strong>.
                        </p>
                        <p style="font-size:1rem; color:var(--mcc-text-dim); line-height:1.6;">
                            But now we're introducing a new way to win: the <strong style="color:var(--mcc-accent);">Moral Compass Score</strong>.
                        </p>
                    </div>
                </div>

                <!-- Phase 2: Formula (revealed after gauge animation) -->
                <div id="mcc-formula-phase" style="display:none; margin-top:30px;">
                    <div style="background:var(--mcc-input-bg); padding:30px; border-radius:16px; text-align:center; border:2px dashed var(--mcc-accent); margin-bottom:24px;">
                        <p style="font-size:1.05rem; color:var(--mcc-text); line-height:1.6; margin:0 0 16px 0;">
                            This new score combines Accuracy and Sustainability:
                        </p>
                        <div style="font-size:1.5rem; font-weight:700; margin:15px 0; color:var(--mcc-text); font-family:'Outfit',sans-serif;">
                            Moral Compass Score =
                            <span style="background:rgba(5,150,105,0.15); color:var(--mcc-success); padding:4px 10px; border-radius:6px;">[ Accuracy ]</span>
                            &times;
                            <span style="background:rgba(217,119,6,0.15); color:var(--mcc-accent); padding:4px 10px; border-radius:6px;">[ Ethical Progress % ]</span>
                        </div>
                        <p style="font-size:0.95rem; margin:16px 0 0 0; color:var(--mcc-text-dim); line-height:1.6;">
                            Since you didn't consider Sustainability when building your model, your Ethical Progress is <strong>0%</strong>.<br>
                            And if Ethical Progress is 0%, the final score is also <strong>0</strong>.
                        </p>
                    </div>

                    <p style="font-size:1.05rem; color:var(--mcc-text); line-height:1.6; text-align:center; margin:0;">
                        In the next activity, you'll learn about Sustainability and earn points to recover your score.
                    </p>
                </div>
            </div>
        """,
    },
    # ─────────────────────────────────────────────
    # MODULE 3 — MISSION BRIEFING
    # ─────────────────────────────────────────────
    {
        "id": 3,
        "title": "Mission Briefing",
        "html": """
            <div class="scenario-box" style="border:none; background:transparent; box-shadow:none; padding:0;">
                <div class="mcc-reveal" style="animation-delay:0s;">
                    <div style="text-align:center; margin-bottom:8px;">
                        <div style="font-size:0.875rem; font-weight:800; letter-spacing:3px; color:var(--mcc-accent); text-transform:uppercase; margin-bottom:12px;">
                            What Comes Next
                        </div>
                        <h2 style="font-size:clamp(1.6rem, 5vw, 2.2rem); font-weight:800; color:var(--mcc-text); margin:0 0 8px 0;">
                            Your Sustainability Missions
                        </h2>
                        <p style="font-size:1.05rem; color:var(--mcc-text-dim); margin:0 0 24px 0;">
                            Complete these two missions to earn Sustainability % and restore your Moral Compass Score.
                        </p>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px;">
                    <!-- Mission 1: Green AI Detective -->
                    <div class="mcc-reveal" style="animation-delay:0.15s;">
                        <div class="mcc-mission-card" style="border-left:4px solid #0284c7;">
                            <div style="font-size:2rem; margin-bottom:12px;">&#128269;</div>
                            <h3 style="font-size:1.2rem; font-weight:800; color:#0284c7; margin:0 0 8px 0;">Green AI Detective</h3>
                            <p style="font-size:0.95rem; color:var(--mcc-text-dim); margin:0 0 12px 0; line-height:1.5;">
                                Investigate AI's true environmental cost &mdash; from a single prompt to the entire planet.
                            </p>
                            <div style="font-size:0.85rem; color:var(--mcc-text-dim);">
                                <strong>4 investigations</strong> &middot; <strong>4 quizzes</strong><br>
                                Earn up to <strong style="color:#0284c7;">40% Sustainability</strong>
                            </div>
                        </div>
                    </div>
                    <!-- Mission 2: Green AI Advisor -->
                    <div class="mcc-reveal" style="animation-delay:0.3s;">
                        <div class="mcc-mission-card" style="border-left:4px solid var(--mcc-success);">
                            <div style="font-size:2rem; margin-bottom:12px;">&#128737;&#65039;</div>
                            <h3 style="font-size:1.2rem; font-weight:800; color:var(--mcc-success); margin:0 0 8px 0;">Green AI Advisor</h3>
                            <p style="font-size:0.95rem; color:var(--mcc-text-dim); margin:0 0 12px 0; line-height:1.5;">
                                The mayor picked you to protect your city from a polluting AI company. Make 5 critical decisions.
                            </p>
                            <div style="font-size:0.85rem; color:var(--mcc-text-dim);">
                                <strong>5 rounds</strong> &middot; <strong>6 quizzes</strong><br>
                                Earn up to <strong style="color:var(--mcc-success);">60% Sustainability</strong>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Score Summary -->
                <div class="mcc-reveal" style="animation-delay:0.45s;">
                    <div style="background:var(--mcc-input-bg); border-radius:12px; padding:16px 20px; text-align:center; margin-bottom:20px; border:1px solid var(--mcc-border-color);">
                        <span style="font-size:1rem; color:var(--mcc-text);">
                            Moral Compass Score: <strong style="color:var(--mcc-error);">0.000</strong>
                            &nbsp;&middot;&nbsp;
                            Sustainability: <strong style="color:var(--mcc-accent);">0%</strong>
                            &nbsp;&middot;&nbsp;
                            Accuracy: <strong id="mcc-summary-accuracy" style="color:var(--mcc-success);">75.0%</strong>
                        </span>
                    </div>
                </div>
            </div>
        """,
    },
]


# ============================================================================
# 6. DASHBOARD & LEADERBOARD RENDERERS
# ============================================================================

def render_top_dashboard(data, module_id):
    display_score = 0.0
    count_completed = 0
    rank_display = "\u2013"
    team_rank_display = "\u2013"
    if data:
        display_score = float(data.get("score", 0.0))
        rank_display = f"#{data.get('rank', '\u2013')}"
        team_rank_display = f"#{data.get('team_rank', '\u2013')}"
        count_completed = len(data.get("completed_task_ids", []) or [])
    progress_pct = min(100, int((count_completed / TOTAL_COURSE_TASKS) * 100))

    return f"""
    <div class="summary-box">
        <div class="summary-box-inner">
            <div class="summary-metrics">
                <div style="text-align:center;">
                    <div class="label-text">Moral Compass Score</div>
                    <div class="score-text-primary">\U0001f9ed {display_score:.3f}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Team Rank</div>
                    <div class="score-text-team">{team_rank_display}</div>
                </div>
                <div class="divider-vertical"></div>
                <div style="text-align:center;">
                    <div class="label-text">Global Rank</div>
                    <div class="score-text-global">{rank_display}</div>
                </div>
            </div>
            <div class="summary-progress">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="progress-label">Course Progress: {progress_pct}%</div>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{progress_pct}%;"></div>
                </div>
            </div>
        </div>
    </div>
    """


def render_leaderboard_card(data, username, team_name):
    team_rows = ""
    user_rows = ""
    if data and data.get("all_teams"):
        for i, t in enumerate(data["all_teams"]):
            cls = "row-highlight-team" if t["team"] == team_name else "row-normal"
            team_rows += (
                f"<tr class='{cls}'><td style='padding:8px;text-align:center;'>{i+1}</td>"
                f"<td style='padding:8px;'>{t['team']}</td>"
                f"<td style='padding:8px;text-align:right;'>{t['avg']:.3f}</td></tr>"
            )
    if data and data.get("all_users"):
        for i, u in enumerate(data["all_users"]):
            cls = "row-highlight-me" if u.get("username") == username else "row-normal"
            sc = float(u.get("moralCompassScore", 0))
            if u.get("username") == username and data.get("score") != sc:
                sc = data.get("score")
            user_rows += (
                f"<tr class='{cls}'><td style='padding:8px;text-align:center;'>{i+1}</td>"
                f"<td style='padding:8px;'>{u.get('username','')}</td>"
                f"<td style='padding:8px;text-align:right;'>{sc:.3f}</td></tr>"
            )
    return f"""
    <div class="scenario-box leaderboard-card">
        <h3 class="slide-title" style="margin-bottom:10px;">\U0001f4ca Live Standings</h3>
        <div class="lb-tabs">
            <input type="radio" id="lb-tab-team" name="lb-tabs" checked>
            <label for="lb-tab-team" class="lb-tab-label">\U0001f3c6 Team</label>
            <input type="radio" id="lb-tab-user" name="lb-tabs">
            <label for="lb-tab-user" class="lb-tab-label">\U0001f464 Individual</label>
            <div class="lb-tab-panels">
                <div class="lb-panel panel-team">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Rank</th><th>Team</th><th style='text-align:right;'>Avg \U0001f9ed</th></tr>
                            </thead>
                            <tbody>{team_rows}</tbody>
                        </table>
                    </div>
                </div>
                <div class="lb-panel panel-user">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Rank</th><th>Engineer</th><th style='text-align:right;'>Score \U0001f9ed</th></tr>
                            </thead>
                            <tbody>{user_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """


# ============================================================================
# 7. CSS — MCC Design System (mcc-* prefix)
# ============================================================================

css = """
/* ========== Moral Compass Challenge Design System ========== */

/* Hide elements via CSS so they stay in the DOM for programmatic .click() */
.mcc-btn-hidden { display: none !important; }
.mcc-module-hidden { display: none !important; }

/* MCC CSS variables — scoped with mcc- prefix */
:root {
    --mcc-bg: #f8fafc;
    --mcc-card-bg: rgba(255, 255, 255, 0.9);
    --mcc-accent: #d97706;
    --mcc-accent-glow: rgba(217, 119, 6, 0.2);
    --mcc-success: #059669;
    --mcc-warning: #d97706;
    --mcc-error: #dc2626;
    --mcc-text: #0f172a;
    --mcc-text-dim: #64748b;
    --mcc-card-shadow: rgba(0, 0, 0, 0.1);
    --mcc-border-color: rgba(0, 0, 0, 0.08);
    --mcc-input-bg: rgba(0, 0, 0, 0.02);
    --mcc-input-border: rgba(0, 0, 0, 0.1);
    --mcc-hover-bg: rgba(0, 0, 0, 0.05);
    --mcc-success-bg: rgba(5, 150, 105, 0.08);
    --mcc-error-bg: rgba(220, 38, 38, 0.08);
    --mcc-accent-highlight: rgba(217, 119, 6, 0.1);
}
@media (prefers-color-scheme: dark) {
    :root {
        --mcc-bg: #0f172a;
        --mcc-card-bg: rgba(30, 41, 59, 0.7);
        --mcc-accent: #f59e0b;
        --mcc-accent-glow: rgba(245, 158, 11, 0.3);
        --mcc-success: #10b981;
        --mcc-warning: #fbbf24;
        --mcc-error: #f43f5e;
        --mcc-text: #f8fafc;
        --mcc-text-dim: #94a3b8;
        --mcc-card-shadow: rgba(0, 0, 0, 0.5);
        --mcc-border-color: rgba(255, 255, 255, 0.05);
        --mcc-input-bg: rgba(255, 255, 255, 0.05);
        --mcc-input-border: rgba(255, 255, 255, 0.1);
        --mcc-hover-bg: rgba(255, 255, 255, 0.08);
        --mcc-success-bg: rgba(16, 185, 129, 0.08);
        --mcc-error-bg: rgba(244, 63, 94, 0.08);
        --mcc-accent-highlight: rgba(245, 158, 11, 0.1);
    }
}
.dark {
    --mcc-bg: #0f172a;
    --mcc-card-bg: rgba(30, 41, 59, 0.7);
    --mcc-accent: #f59e0b;
    --mcc-accent-glow: rgba(245, 158, 11, 0.3);
    --mcc-success: #10b981;
    --mcc-warning: #fbbf24;
    --mcc-error: #f43f5e;
    --mcc-text: #f8fafc;
    --mcc-text-dim: #94a3b8;
    --mcc-card-shadow: rgba(0, 0, 0, 0.5);
    --mcc-border-color: rgba(255, 255, 255, 0.05);
    --mcc-input-bg: rgba(255, 255, 255, 0.05);
    --mcc-input-border: rgba(255, 255, 255, 0.1);
    --mcc-hover-bg: rgba(255, 255, 255, 0.08);
    --mcc-success-bg: rgba(16, 185, 129, 0.08);
    --mcc-error-bg: rgba(244, 63, 94, 0.08);
    --mcc-accent-highlight: rgba(245, 158, 11, 0.1);
}

/* MCC Animations */
@keyframes mccSlideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes mccBlink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}
@keyframes mccBlinkRed {
    0%, 100% { color: var(--mcc-text); }
    50% { color: var(--mcc-error); }
}
@keyframes mccPulse {
    0%, 100% { box-shadow: 0 4px 15px rgba(5, 150, 105, 0.4); }
    50% { box-shadow: 0 8px 30px rgba(5, 150, 105, 0.6); }
}
@keyframes mccGaugeDrop {
    0% { background: conic-gradient(from 180deg, var(--mcc-success) 0%, var(--mcc-success) 100%, var(--mcc-border-color) 100%); }
    100% { background: conic-gradient(from 180deg, var(--mcc-error) 0%, var(--mcc-error) 0%, var(--mcc-border-color) 0%, var(--mcc-border-color) 100%); }
}
@keyframes mccCheckFlash {
    0%, 100% { background: var(--mcc-error-bg); }
    50% { background: rgba(220, 38, 38, 0.25); }
}

/* MCC reveal animation */
.mcc-reveal {
    opacity: 0;
    transform: translateY(30px);
    animation: mccSlideUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.mcc-blink { animation: mccBlink 1s infinite; }
.mcc-blink-red { animation: mccBlinkRed 1s infinite; }

/* MCC Intro page */
.mcc-intro-page {
    min-height: 55vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 40px 20px;
    max-width: 900px;
    margin: 0 auto;
}

/* MCC Stat cards */
.mcc-stat-card {
    background: var(--mcc-input-bg);
    border: 1px solid var(--mcc-border-color);
    padding: 20px;
    border-radius: 16px;
    text-align: center;
}
.mcc-stat-value {
    font-size: 2.5rem;
    font-weight: 800;
}
.mcc-stat-label {
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--mcc-text-dim);
    margin-top: 5px;
}

/* MCC Buttons */
.mcc-btn {
    background: var(--mcc-accent);
    color: white;
    border: 2px solid transparent;
    padding: 16px 28px;
    border-radius: 16px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.3s ease;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 1rem;
    font-family: 'Outfit', sans-serif;
}
.mcc-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px var(--mcc-accent-glow);
}
.mcc-btn-success {
    background: var(--mcc-success);
    animation: mccPulse 2s ease-in-out infinite;
}
.mcc-btn-success:hover {
    box-shadow: 0 8px 25px rgba(5, 150, 105, 0.5);
}

/* MCC Checklist */
.mcc-checklist-item {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 18px;
    border-radius: 12px;
    margin-bottom: 8px;
    background: var(--mcc-input-bg);
    border: 1px solid var(--mcc-border-color);
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--mcc-text);
    transition: all 0.4s ease;
    font-family: 'Outfit', sans-serif;
}
.mcc-checklist-item.checked {
    opacity: 1 !important;
    background: var(--mcc-success-bg);
    border-color: var(--mcc-success);
}
.mcc-checklist-item.failed {
    opacity: 1 !important;
    background: var(--mcc-error-bg);
    border-color: var(--mcc-error);
    animation: mccCheckFlash 0.5s ease 3;
}
.mcc-check-icon {
    font-size: 1.4rem;
    flex-shrink: 0;
}

/* MCC Flip cards */
.mcc-flip-card {
    background: var(--mcc-card-bg);
    backdrop-filter: blur(16px);
    border-radius: 20px;
    border: 1px solid var(--mcc-border-color);
    box-shadow: 0 12px 30px var(--mcc-card-shadow);
    margin-bottom: 16px;
    cursor: pointer;
    overflow: hidden;
    transition: border-color 0.3s;
}
.mcc-flip-card:hover {
    border-color: var(--mcc-accent);
}
.mcc-flip-card.flipped {
    cursor: default;
    border-color: var(--mcc-accent);
}
.mcc-flip-card.flipped .mcc-flip-card-front {
    display: none;
}
.mcc-flip-card.flipped .mcc-flip-card-back {
    display: block;
}
.mcc-flip-card-front {
    padding: 32px 24px;
    text-align: center;
}
.mcc-flip-card-back {
    display: none;
    padding: 28px 24px;
}
.mcc-flip-card.audit-done {
    border-color: var(--mcc-accent);
    background: var(--mcc-accent-highlight);
}

/* MCC Knockout stats */
.mcc-knockout-stat {
    background: var(--mcc-input-bg);
    border: 1px solid var(--mcc-border-color);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
}

/* MCC Gauge */
.mcc-gauge-container {
    position: relative;
    width: 200px;
    height: 200px;
    margin: 0 auto 30px auto;
}
.mcc-gauge {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: conic-gradient(from 180deg, var(--mcc-success) 0%, var(--mcc-success) 100%, var(--mcc-border-color) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 30px rgba(5, 150, 105, 0.2);
    transition: background 2s ease-in-out;
}
.mcc-gauge-inner {
    width: 80%;
    height: 80%;
    border-radius: 50%;
    background-color: var(--block-background-fill, var(--mcc-bg));
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.mcc-gauge-value {
    font-size: 3rem;
    font-weight: 800;
    color: var(--mcc-text);
    font-family: 'Outfit', sans-serif;
}
.mcc-gauge.gauge-dropping {
    animation: mccGaugeDrop 2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* MCC Mission cards */
.mcc-mission-card {
    background: var(--mcc-card-bg);
    backdrop-filter: blur(16px);
    border-radius: 20px;
    padding: 24px;
    border: 1px solid var(--mcc-border-color);
    box-shadow: 0 12px 30px var(--mcc-card-shadow);
    height: 100%;
}

/* MCC Range slider styling */
input[type="range"]#mcc-prompt-slider,
input[type="range"]#mcc-whatif-slider {
    -webkit-appearance: none;
    background: var(--mcc-input-bg);
    border-radius: 6px;
    outline: none;
    height: 8px;
}
input[type="range"]#mcc-prompt-slider::-webkit-slider-thumb,
input[type="range"]#mcc-whatif-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: var(--mcc-accent);
    cursor: pointer;
    box-shadow: 0 0 10px var(--mcc-accent-glow);
}

/* Module container font */
.module-container .scenario-box {
    font-family: 'Outfit', sans-serif;
}

/* ========== Gradio Integration Styles ========== */

/* Layout + containers */
.summary-box {
    background: var(--block-background-fill);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid var(--border-color-primary);
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}
.summary-box-inner { display: flex; align-items: center; justify-content: space-between; gap: 30px; }
.summary-metrics { display: flex; gap: 30px; align-items: center; }
.summary-progress { width: 560px; max-width: 100%; }

/* Scenario cards */
.scenario-box {
    padding: 24px;
    border-radius: 14px;
    background: var(--block-background-fill);
    border: 1px solid var(--border-color-primary);
    margin-bottom: 22px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.08);
}
.slide-title { margin-top: 0; font-size: 1.9rem; font-weight: 800; }

/* Hint boxes */
.hint-box {
    padding: 12px;
    border-radius: 10px;
    background: var(--background-fill-secondary);
    border: 1px solid var(--border-color-primary);
    margin-top: 10px;
    font-size: 0.98rem;
}

/* Numbers + labels */
.score-text-primary { font-size: 2.05rem; font-weight: 900; color: var(--color-accent); }
.score-text-team { font-size: 2.05rem; font-weight: 900; color: var(--color-accent); }
.score-text-global { font-size: 2.05rem; font-weight: 900; }
.label-text { font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--body-text-color-subdued, #6b7280); }
.progress-label { font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--body-text-color-subdued, #6b7280); }

/* Progress bar */
.progress-bar-bg { width: 100%; height: 10px; background: var(--border-color-primary, #e5e7eb); border-radius: 6px; overflow: hidden; margin-top: 8px; }
.progress-bar-fill { height: 100%; background: var(--color-accent); transition: width 280ms ease; }

/* Leaderboard tabs + tables */
.leaderboard-card input[type="radio"] { display: none; }
.lb-tab-label {
    display: inline-block; padding: 8px 16px; margin-right: 8px; border-radius: 20px;
    cursor: pointer; border: 1px solid var(--border-color-primary); font-weight: 700; font-size: 0.94rem;
}
#lb-tab-team:checked + label, #lb-tab-user:checked + label {
    background: var(--color-accent); color: white; border-color: var(--color-accent);
    box-shadow: 0 3px 8px rgba(99,102,241,0.25);
}
.lb-panel { display: none; margin-top: 10px; }
#lb-tab-team:checked ~ .lb-tab-panels .panel-team { display: block; }
#lb-tab-user:checked ~ .lb-tab-panels .panel-user { display: block; }
.table-container { height: 320px; overflow-y: auto; border: 1px solid var(--border-color-primary); border-radius: 10px; }
.leaderboard-table { width: 100%; border-collapse: collapse; }
.leaderboard-table th {
    position: sticky; top: 0; background: var(--background-fill-secondary);
    padding: 10px; text-align: left; border-bottom: 2px solid var(--border-color-primary);
    font-weight: 800;
}
.leaderboard-table td { padding: 10px; border-bottom: 1px solid var(--border-color-primary); }
.row-highlight-me, .row-highlight-team { background: var(--mcc-accent-highlight); font-weight: 700; }

/* Small utility */
.divider-vertical { width: 1px; height: 48px; background: var(--border-color-primary); opacity: 0.6; }

/* Navigation loading overlay */
#nav-loading-overlay {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: color-mix(in srgb, var(--body-background-fill) 95%, transparent);
    z-index: 9999; display: none; flex-direction: column; align-items: center;
    justify-content: center; opacity: 0; transition: opacity 0.3s ease;
}
.nav-spinner {
    width: 50px; height: 50px; border: 5px solid var(--border-color-primary);
    border-top: 5px solid var(--color-accent); border-radius: 50%;
    animation: nav-spin 1s linear infinite; margin-bottom: 20px;
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
    .nav-spinner { border-color: rgba(148, 163, 184, 0.4); border-top-color: var(--color-accent); }
}
.dark #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); }
.dark .nav-spinner { border-color: rgba(148, 163, 184, 0.4); border-top-color: var(--color-accent); }

/* Transition overlay */
#mcc-transition-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(10px);
    z-index: 9998;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}

/* Responsive adjustments */
@media (max-width: 640px) {
    .summary-box-inner { flex-direction: column; gap: 16px; }
    .summary-progress { width: 100%; }
    .mcc-mission-card { padding: 16px; }
}
"""


# ============================================================================
# 8. CLIENT-SIDE JAVASCRIPT
# ============================================================================

CLIENT_JS = """
// === Dynamically load Outfit font ===
(function(){
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap';
    document.head.appendChild(link);
})();

// === Global state ===
var mccFlippedCards = [false, false, false];
var mccGaugePlayed = false;
var mccChecklistPlayed = false;
var mccUserAccuracy = 0.75; // Updated from Python on load

// === Module 0: Typewriter + stats reveal ===
(function mccInitTypewriter(){
    var el = document.getElementById('mcc-typewriter-text');
    // Wait until element exists AND is visible (offsetParent !== null).
    // Parent container starts hidden until the load handler fires.
    if (!el || el.offsetParent === null) { setTimeout(mccInitTypewriter, 200); return; }
    if (el.dataset.init === '1') return;
    el.dataset.init = '1';
    var full = "Your AI Model Is Ready for the Real World";
    var i = 0;
    var iv = setInterval(function(){
        i++;
        el.textContent = full.slice(0, i);
        if (i >= full.length) {
            clearInterval(iv);
            // After typewriter, reveal stats
            setTimeout(function(){
                var statsEl = document.getElementById('mcc-stats-reveal');
                if (statsEl) { statsEl.style.opacity = '1'; statsEl.style.transform = 'translateY(0)'; }
                // Then reveal achievement
                setTimeout(function(){
                    var achEl = document.getElementById('mcc-achievement-reveal');
                    if (achEl) { achEl.style.opacity = '1'; achEl.style.transform = 'translateY(0)'; }
                }, 600);
            }, 400);
        }
    }, 50);
})();

// === Module 0: Certification Checklist ===
function mccStartChecklist() {
    if (mccChecklistPlayed) return;
    mccChecklistPlayed = true;

    var phase1 = document.getElementById('mcc-cert-phase1');
    var phase2 = document.getElementById('mcc-cert-phase2');
    if (phase1) phase1.style.display = 'none';
    if (phase2) phase2.style.display = 'block';

    var delays = [1000, 2000, 3000, 4000, 5000];
    for (var idx = 0; idx < 4; idx++) {
        (function(i){
            setTimeout(function(){
                var item = document.getElementById('mcc-check-' + i);
                var icon = document.getElementById('mcc-check-icon-' + i);
                if (item && icon) {
                    item.classList.add('checked');
                    icon.innerHTML = '&#9989;';
                }
            }, delays[i]);
        })(idx);
    }

    // Last item: FAILED
    setTimeout(function(){
        var item = document.getElementById('mcc-check-4');
        var icon = document.getElementById('mcc-check-icon-4');
        if (item && icon) {
            item.classList.add('failed');
            icon.innerHTML = '&#10060;';
        }
        // Show warning banner, then reveal the Next button for manual advance
        setTimeout(function(){
            var warning = document.getElementById('mcc-cert-warning');
            if (warning) warning.style.display = 'block';
            // Unhide the Gradio Next button so the user can click it
            var nextEl = document.getElementById('mcc-next-0');
            if (nextEl) nextEl.classList.remove('mcc-btn-hidden');
        }, 500);
    }, delays[4]);
}

// === Module 1: Flip cards ===
function mccFlipCard(idx) {
    if (mccFlippedCards[idx]) return;
    var card = document.getElementById('mcc-card-' + idx);
    if (!card) return;
    mccFlippedCards[idx] = true;
    card.classList.add('flipped');

    // Update progress
    var count = mccFlippedCards.filter(function(x){ return x; }).length;
    var progressEl = document.getElementById('mcc-audit-progress');
    if (progressEl) progressEl.textContent = count + '/3 revealed';

    // All unlocked?
    if (count === 3) {
        // Mark cards as audit-done
        for (var i = 0; i < 3; i++) {
            var c = document.getElementById('mcc-card-' + i);
            if (c) c.classList.add('audit-done');
        }
        // Show summary
        var summary = document.getElementById('mcc-audit-summary');
        if (summary) summary.style.display = 'block';
    }
}

// === Module 2: Gauge drain animation ===
function mccRunGaugeDrain() {
    if (mccGaugePlayed) {
        // If already played, show end state immediately
        var msg = document.getElementById('mcc-reset-message');
        var formula = document.getElementById('mcc-formula-phase');
        if (msg) msg.style.opacity = '1';
        if (formula) formula.style.display = 'block';
        return;
    }
    mccGaugePlayed = true;

    var gauge = document.getElementById('mcc-main-gauge');
    var scoreVal = document.getElementById('mcc-gauge-score');
    var msg = document.getElementById('mcc-reset-message');
    var formula = document.getElementById('mcc-formula-phase');
    var header = document.getElementById('mcc-recalc-header');

    if (!gauge || !scoreVal) return;

    gauge.classList.add('gauge-dropping');

    var score = parseInt(scoreVal.textContent) || 75;
    var interval = setInterval(function() {
        score -= 2;
        if (score <= 0) {
            score = 0;
            clearInterval(interval);
            scoreVal.style.color = 'var(--mcc-error)';
            if (header) header.style.animation = 'none';
            if (header) header.style.color = 'var(--mcc-error)';
            if (header) header.textContent = 'SCORE RESET TO ZERO';
            // Show message
            setTimeout(function(){
                if (msg) msg.style.opacity = '1';
                // Show formula after message
                setTimeout(function(){
                    if (formula) formula.style.display = 'block';
                }, 800);
            }, 500);
        }
        scoreVal.textContent = score;
    }, 30);
}

// === Module 2: What-if formula slider ===
function mccUpdateFormula(val) {
    var susEl = document.getElementById('mcc-whatif-sus');
    var resultEl = document.getElementById('mcc-whatif-result');
    var msgEl = document.getElementById('mcc-whatif-message');
    if (!susEl || !resultEl || !msgEl) return;

    var sus = parseInt(val);
    var score = mccUserAccuracy * (sus / 100);
    susEl.textContent = sus + '%';

    resultEl.textContent = score.toFixed(3);

    // Color coding
    if (sus === 0) {
        resultEl.style.color = 'var(--mcc-error)';
        susEl.style.color = 'var(--mcc-error)';
        msgEl.textContent = "That's where you are now.";
    } else if (sus < 40) {
        resultEl.style.color = 'var(--mcc-error)';
        susEl.style.color = 'var(--mcc-accent)';
        msgEl.textContent = 'Getting started — every point counts.';
    } else if (sus < 70) {
        resultEl.style.color = 'var(--mcc-accent)';
        susEl.style.color = 'var(--mcc-accent)';
        msgEl.textContent = 'Halfway there — already making a difference.';
    } else {
        resultEl.style.color = 'var(--mcc-success)';
        susEl.style.color = 'var(--mcc-success)';
        if (sus === 100) {
            msgEl.textContent = 'Full marks. This is what a responsible AI Engineer looks like.';
        } else {
            msgEl.textContent = 'Strong commitment to sustainability!';
        }
    }
}

// === Module 3: Transition overlay ===
function mccShowTransition() {
    var overlay = document.getElementById('mcc-transition-overlay');
    if (overlay) overlay.style.display = 'flex';
    try { window.parent.postMessage('activity_complete', '*'); } catch (e) { }
}

// === Re-init function (called after navigation) ===
function mccReinitAll() {
    // Re-run typewriter if needed
    var tw = document.getElementById('mcc-typewriter-text');
    if (tw && tw.dataset.init !== '1') {
        tw.dataset.init = '0';
        // Re-trigger
    }
    // Re-trigger gauge if on module 2
    var gauge = document.getElementById('mcc-main-gauge');
    if (gauge && gauge.offsetParent !== null) {
        setTimeout(mccRunGaugeDrain, 500);
    }
}

// === Apply dynamic user data from server ===
(function mccApplyUserData(){
    var el = document.getElementById('mcc-user-data');
    if (!el) { setTimeout(mccApplyUserData, 200); return; }
    if (el.dataset.applied === '1') return;
    el.dataset.applied = '1';
    var parts = (el.textContent || '').trim().split('|');
    if (parts.length < 4) return;
    var accDisplay = parts[0];
    var rankDisplay = parts[1];
    var scoreInt = parts[2];
    var userAcc = parseFloat(parts[3] || '0.75');
    mccUserAccuracy = userAcc;
    var ad = document.getElementById('mcc-accuracy-display');
    if(ad) ad.textContent = accDisplay;
    var rd = document.getElementById('mcc-rank-display');
    if(rd) rd.textContent = rankDisplay;
    var gs = document.getElementById('mcc-gauge-score');
    if(gs) gs.textContent = scoreInt;
    var at = document.getElementById('mcc-accuracy-text');
    if(at) at.textContent = accDisplay;
    var wa = document.getElementById('mcc-whatif-acc');
    if(wa) wa.textContent = accDisplay;
    var sa = document.getElementById('mcc-summary-accuracy');
    if(sa) sa.textContent = accDisplay;
})();
"""

HEAD_HTML = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap">\n'
    '<script>\n' + CLIENT_JS + '\n</script>'
)


# ============================================================================
# 9. APP FACTORY
# ============================================================================

def create_moral_compass_challenge_sustainability_en_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue=theme_primary_hue),
        css=css,
        head=HEAD_HTML,
    ) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

        # Top anchor + loading overlay
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # Transition overlay (global, outside modules)
        gr.HTML("""
            <div id="mcc-transition-overlay">
                <div style="font-size:4rem; margin-bottom:20px;">&#127793;</div>
                <h2 style="color:#10b981; font-size:2rem; margin-bottom:10px; font-family:'Outfit',sans-serif;">Activity Complete</h2>
                <p style="color:#f8fafc; font-size:1.2rem; max-width:600px; font-family:'Outfit',sans-serif; line-height:1.6;">
                    Next up: investigate AI's environmental footprint as a <strong>Green AI Detective</strong>.
                </p>
                <button onclick="document.getElementById('mcc-transition-overlay').style.display='none'; try { window.parent.postMessage('navigate-to-activity-6', '*'); } catch(e) {}"
                    style="margin-top:40px; font-size:1.1rem; padding:18px 40px; border-radius:16px; background:rgba(16,185,129,0.2); color:#10b981; border:2px solid #10b981; cursor:pointer; font-family:'Outfit',sans-serif; font-weight:700; text-transform:uppercase;">
                    PROCEED TO ACTIVITY 6 &rarr;
                </button>
            </div>
        """)

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>Authenticating...</h2>"
                "<p>Syncing Moral Compass Data...</p>"
                "</div>"
            )

        # --- MAIN APP VIEW ---
        with gr.Column(visible=False) as main_app_col:
            # Top dashboard
            out_top = gr.HTML()

            # Module containers
            module_ui_elements = {}

            for i, mod in enumerate(MODULES):
                with gr.Column(
                    elem_id=f"module-{i}",
                    elem_classes=["module-container"] if i == 0 else ["module-container", "mcc-module-hidden"],
                    visible=True,
                ) as mod_col:
                    gr.HTML(mod["html"])

                    # Navigation buttons
                    with gr.Row():
                        btn_prev = gr.Button("\u2b05\ufe0f Previous", visible=(i > 0))
                        if i < len(MODULES) - 1:
                            next_label = "Next \u25b6\ufe0f"
                        else:
                            next_label = "PROCEED TO NEXT ACTIVITY \u27a1"
                        # Hide Next on Module 0 via CSS (not visible=False which
                        # removes from DOM in Gradio ≥5.36, breaking getElementById)
                        if i == 0:
                            btn_next = gr.Button(
                                next_label, variant="primary",
                                elem_id="mcc-next-0",
                                elem_classes=["mcc-btn-hidden"],
                            )
                        else:
                            btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            # Formula details (collapsible, below modules)
            gr.HTML("""
                <details style="background:var(--background-fill-secondary); border-radius:16px;
                                border:1px solid var(--border-color-primary); margin:8px 0 12px 0; opacity:0.7;">
                    <summary style="padding:14px 24px; cursor:pointer; text-transform:uppercase; letter-spacing:1.5px;
                                    color:var(--body-text-color-subdued); font-size:0.78rem; font-weight:700;
                                    text-align:center; list-style:none;">
                        &#9656; The Moral Compass Formula
                    </summary>
                    <div style="padding:0 24px 24px 24px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:700; margin:12px 0; font-family:'Outfit',sans-serif;">
                            Moral Compass Score =
                            <span style="background:rgba(5,150,105,0.15); color:var(--mcc-success); padding:4px 10px; border-radius:6px;">
                                [ Accuracy ]</span>
                            &times;
                            <span style="background:rgba(217,119,6,0.15); color:var(--mcc-accent); padding:4px 10px; border-radius:6px;">
                                [ Sustainability % ]</span>
                        </div>
                        <p style="font-size:0.95rem; margin:12px 0 0 0; color:var(--body-text-color-subdued);">
                            <strong>Sustainability %</strong> reflects your Moral Compass progress through the missions.<br/>
                            If your Sustainability % is <strong>0%</strong>, your Moral Compass Score is <strong>0</strong>.
                        </p>
                    </div>
                </details>
            """)

            # Leaderboard at bottom
            leaderboard_html = gr.HTML()

            # Hidden HTML for injecting dynamic values via JS
            inject_js_html = gr.HTML()

        # --- LOAD HANDLER ---
        def handle_load(request: gr.Request):
            ok, uname, tok = _try_session_based_auth(request)
            if ok:
                best_acc, fetched_team = fetch_user_history(uname, tok)
                team = "Team-Unassigned"
                fetched_tasks: List[str] = []

                os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
                client = MoralcompassApiClient(
                    api_base_url=DEFAULT_API_URL, auth_token=tok
                )

                # Resolve team from existing server record
                def get_or_assign_team(client_obj, username_val):
                    try:
                        user_data = client_obj.get_user(
                            table_id=TABLE_ID, username=username_val
                        )
                    except Exception:
                        user_data = None
                    if user_data and isinstance(user_data, dict):
                        if user_data.get("teamName"):
                            return user_data["teamName"]
                    return "team-a"

                exist_team = get_or_assign_team(client, uname)
                if fetched_team != "Team-Unassigned":
                    team = fetched_team
                elif exist_team != "team-a":
                    team = exist_team
                else:
                    team = "team-a"

                # Fetch completedTaskIds from server via get_user()
                try:
                    user_stats = client.get_user(table_id=TABLE_ID, username=uname)
                except Exception:
                    user_stats = None

                if user_stats:
                    if isinstance(user_stats, dict):
                        fetched_tasks = user_stats.get("completedTaskIds") or []
                    else:
                        fetched_tasks = getattr(
                            user_stats, "completed_task_ids", []
                        ) or []

                # Sync baseline moral compass record
                try:
                    client.update_moral_compass(
                        table_id=TABLE_ID,
                        username=uname,
                        team_name=team,
                        metrics={"accuracy": best_acc},
                        tasks_completed=len(fetched_tasks),
                        total_tasks=TOTAL_COURSE_TASKS,
                        primary_metric="accuracy",
                        completed_task_ids=fetched_tasks,
                    )
                    time.sleep(1.0)
                except Exception:
                    pass

                data, _ = ensure_table_and_get_data(
                    uname, tok, team, fetched_tasks
                )

                # Compute display values for injecting into HTML
                acc_pct = best_acc * 100 if best_acc <= 1.0 else best_acc
                acc_display = f"{acc_pct:.1f}%"
                score_int = int(acc_pct)

                # Get rank from leaderboard data
                rank_val = data.get("rank", "N/A") if data else "N/A"
                rank_display = f"#{rank_val}" if rank_val != "N/A" else "#N/A"

                # Build JS injection to update all dynamic values in the page
                inject_script = f'<div id="mcc-user-data" style="display:none">{acc_display}|{rank_display}|{score_int}|{acc_pct / 100:.4f}</div>'

                is_demo = False
                if best_acc == 0.0:
                    is_demo = True
                    acc_pct = 75.0
                    inject_script = """<div id="mcc-user-data" style="display:none"></div>
                    <div style="background:rgba(217,119,6,0.15); border:2px solid var(--mcc-accent); padding:12px; border-radius:8px; margin-bottom:12px; text-align:center;">
                        <strong style="color:var(--mcc-accent);">Demo Mode:</strong>
                        <span style="color:var(--mcc-text-dim);">Your real model score could not be loaded. Showing example values.</span>
                    </div>"""

                return (
                    uname, tok, team,
                    best_acc, fetched_tasks,
                    render_top_dashboard(data, 0),
                    render_leaderboard_card(data, uname, team),
                    inject_script,
                    gr.update(visible=False),
                    gr.update(visible=True),
                )
            return (
                None, None, None,
                0.0, [],
                "<div class='hint-box'>Auth Failed. Please launch from the course link.</div>",
                "",
                """<div id="mcc-user-data" style="display:none"></div>
                <div style="background:rgba(217,119,6,0.15); border:2px solid var(--mcc-accent); padding:12px; border-radius:8px; margin-bottom:12px; text-align:center;">
                    <strong style="color:var(--mcc-accent);">Demo Mode:</strong>
                    <span style="color:var(--mcc-text-dim);">Could not authenticate. Showing example values.</span>
                </div>""",
                gr.update(visible=False),
                gr.update(visible=True),
            )

        demo.load(
            handle_load, None,
            [
                username_state, token_state, team_state,
                accuracy_state, task_list_state,
                out_top, leaderboard_html,
                inject_js_html,
                loader_col, main_app_col,
            ],
        )

        # --- JAVASCRIPT HELPER ---
        def nav_js(target_id: str, message: str) -> str:
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
                const startTime = Date.now();
                setTimeout(() => {{
                  const anchor = document.getElementById('app_top_anchor');
                  if(anchor) anchor.scrollIntoView({{behavior:'smooth', block:'start'}});
                }}, 40);
                const targetId = '{target_id}';
                const pollInterval = setInterval(() => {{
                  const elapsed = Date.now() - startTime;
                  const target = document.getElementById(targetId);
                  const isVisible = target && target.offsetParent !== null &&
                                   window.getComputedStyle(target).display !== 'none';
                  if((isVisible && elapsed >= 1200) || elapsed > 7000) {{
                    clearInterval(pollInterval);
                    if(overlay) {{
                      overlay.style.opacity = '0';
                      setTimeout(() => {{ overlay.style.display = 'none'; }}, 300);
                    }}
                    setTimeout(function(){{ if(typeof mccReinitAll==='function') mccReinitAll(); }}, 300);
                  }}
                }}, 90);
              }} catch(e) {{ console.warn('nav-js error', e); }}
            }}
            """

        # --- NAVIGATION ---
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]

            if i > 0:
                prev_col = module_ui_elements[i - 1][0]
                prev_target_id = f"module-{i-1}"

                def make_prev_handler(p_col, c_col, target_id):
                    def navigate_prev():
                        yield gr.update(elem_classes=["module-container", "mcc-module-hidden"]), gr.update(elem_classes=["module-container", "mcc-module-hidden"])
                        yield gr.update(elem_classes=["module-container"]), gr.update(elem_classes=["module-container", "mcc-module-hidden"])
                    return navigate_prev

                prev_btn.click(
                    fn=make_prev_handler(prev_col, curr_col, prev_target_id),
                    outputs=[prev_col, curr_col],
                    js=nav_js(prev_target_id, "Loading..."),
                )

            if i < len(MODULES) - 1:
                next_col = module_ui_elements[i + 1][0]
                next_target_id = f"module-{i+1}"

                def make_next_handler(c_col, n_col, next_idx):
                    def wrapper_next(user, tok, team, tasks, acc):
                        data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                        dash_html = render_top_dashboard(data, next_idx)
                        # Also update leaderboard when navigating to last module
                        if next_idx == len(MODULES) - 1:
                            lb_html = render_leaderboard_card(data, user, team)
                            return dash_html, lb_html
                        return dash_html, gr.update()
                    return wrapper_next

                def make_nav_generator(c_col, n_col):
                    def navigate_next():
                        yield gr.update(elem_classes=["module-container", "mcc-module-hidden"]), gr.update(elem_classes=["module-container", "mcc-module-hidden"])
                        yield gr.update(elem_classes=["module-container", "mcc-module-hidden"]), gr.update(elem_classes=["module-container"])
                    return navigate_next

                next_btn.click(
                    fn=make_next_handler(curr_col, next_col, i + 1),
                    inputs=[username_state, token_state, team_state, task_list_state, accuracy_state],
                    outputs=[out_top, leaderboard_html],
                    js=nav_js(next_target_id, "Loading..."),
                ).then(
                    fn=make_nav_generator(curr_col, next_col),
                    outputs=[curr_col, next_col],
                )

            # Last module: CTA triggers transition overlay
            if i == len(MODULES) - 1:
                next_btn.click(
                    fn=None,
                    js="() => { try { window.parent.postMessage('navigate-to-activity-6', '*'); } catch(e) {} }",
                )

        return demo


# ============================================================================
# LAUNCH
# ============================================================================

def launch_moral_compass_challenge_sustainability_en_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    app = create_moral_compass_challenge_sustainability_en_app(theme_primary_hue=theme_primary_hue)
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        **kwargs
    )


if __name__ == "__main__":
    launch_moral_compass_challenge_sustainability_en_app(share=False, debug=True, height=1000)

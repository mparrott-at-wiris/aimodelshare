import os
import sys
import subprocess
import time
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"
TOTAL_COURSE_TASKS = 19
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
    print("📦 Installing dependencies...")
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
        if not session_id and LOCAL_TEST_SESSION_ID: session_id = LOCAL_TEST_SESSION_ID
        if not session_id: return False, None, None
        token = get_token_from_session(session_id)
        if not token: return False, None, None
        username = _get_username_from_token(token)
        if not username: return False, None, None
        return True, username, token
    except Exception: return False, None, None

def fetch_user_history(username, token):
    default_acc = 0.0; default_team = "Team-Unassigned"
    try:
        playground = Competition(ORIGINAL_PLAYGROUND_URL)
        df = playground.get_leaderboard(token=token)
        if df is None or df.empty: return default_acc, default_team
        if "username" in df.columns and "accuracy" in df.columns:
            user_rows = df[df["username"] == username]
            if not user_rows.empty:
                best_acc = user_rows["accuracy"].max()
                if "timestamp" in user_rows.columns and "Team" in user_rows.columns:
                    try:
                        user_rows = user_rows.copy()
                        user_rows["timestamp"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
                        user_rows = user_rows.sort_values("timestamp", ascending=False)
                        found_team = user_rows.iloc[0]["Team"]
                        if pd.notna(found_team) and str(found_team).strip(): default_team = str(found_team).strip()
                    except Exception: pass
                return float(best_acc), default_team
    except Exception: pass
    return default_acc, default_team

# --- 4. API & LEADERBOARD LOGIC ---
def get_or_assign_team(client, username):
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        u = next((u for u in resp.get("users", []) if u.get("username") == username), None)
        return u.get("teamName") if u else "team-a"
    except: return "team-a"

def get_leaderboard_data(client, username, team_name, local_list=None, override_score=None):
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])

        # Optimistic Score Patch
        if override_score is not None:
            found = False
            for u in users:
                if u.get("username") == username:
                    u["moralCompassScore"] = override_score; found = True; break
            if not found: users.append({"username": username, "moralCompassScore": override_score, "teamName": team_name})

        users_sorted = sorted(users, key=lambda x: float(x.get("moralCompassScore", 0) or 0), reverse=True)
        my_user = next((u for u in users_sorted if u.get("username") == username), None)
        score = float(my_user.get("moralCompassScore", 0) or 0) if my_user else 0.0
        rank = users_sorted.index(my_user) + 1 if my_user else 0
        completed = local_list if local_list is not None else (my_user.get("completedTaskIds", []) if my_user else [])

        team_map = {}
        for u in users:
            t = u.get("teamName"); s = float(u.get("moralCompassScore", 0) or 0)
            if t:
                if t not in team_map: team_map[t] = {"sum": 0, "count": 0}
                team_map[t]["sum"] += s; team_map[t]["count"] += 1
        teams_sorted = []
        for t, d in team_map.items(): teams_sorted.append({"team": t, "avg": d["sum"] / d["count"]})
        teams_sorted.sort(key=lambda x: x["avg"], reverse=True)
        my_team = next((t for t in teams_sorted if t['team'] == team_name), None)
        team_rank = teams_sorted.index(my_team) + 1 if my_team else 0

        return {"score": score, "rank": rank, "team_rank": team_rank, "all_users": users_sorted, "all_teams": teams_sorted, "completed_task_ids": completed}
    except Exception: return None

def ensure_table_and_get_data(username, token, team_name, task_list_state=None):
    if not username or not token: return None, username
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    try: client.get_table(TABLE_ID)
    except:
        try: client.create_table(table_id=TABLE_ID, display_name="LMS", playground_url="https://example.com")
        except: pass
    return get_leaderboard_data(client, username, team_name, task_list_state), username

def trigger_api_update(username, token, team_name, module_id, user_real_accuracy, task_list_state, append_task_id=None):
    if not username or not token: return None, None, username, task_list_state
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

    acc = float(user_real_accuracy) if user_real_accuracy is not None else 0.0

    old_task_list = list(task_list_state) if task_list_state else []
    new_task_list = list(old_task_list)
    if append_task_id and append_task_id not in new_task_list:
        new_task_list.append(append_task_id)
        try: new_task_list.sort(key=lambda x: int(x[1:]) if x.startswith('t') and x[1:].isdigit() else 0)
        except: pass

    tasks_completed = len(new_task_list)
    client.update_moral_compass(table_id=TABLE_ID, username=username, team_name=team_name, metrics={"accuracy": acc}, tasks_completed=tasks_completed, total_tasks=TOTAL_COURSE_TASKS, primary_metric="accuracy", completed_task_ids=new_task_list)

    old_score_calc = acc * (len(old_task_list) / TOTAL_COURSE_TASKS)
    new_score_calc = acc * (len(new_task_list) / TOTAL_COURSE_TASKS)

    prev_data = get_leaderboard_data(client, username, team_name, old_task_list, override_score=old_score_calc)
    lb_data = get_leaderboard_data(client, username, team_name, new_task_list, override_score=new_score_calc)
    return prev_data, lb_data, username, new_task_list

def reset_user_progress(username, token, team_name, acc):
    if not username or not token: return []
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    print(f"🔄 Resetting progress for {username}...")
    client.update_moral_compass(table_id=TABLE_ID, username=username, team_name=team_name, metrics={"accuracy": acc}, tasks_completed=0, total_tasks=TOTAL_COURSE_TASKS, primary_metric="accuracy", completed_task_ids=[])
    time.sleep(1.0)
    return []

# --- 5. CONTENT MODULES ---
MODULES = [
    {
        "id": 0, "title": "Part 2 Intro",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🕵️‍♀️ PART 2: THE ALGORITHMIC AUDIT</h2>
                <div class="slide-body">

                    <!-- STATUS BADGE -->
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); font-size:0.95rem; text-transform:uppercase; letter-spacing:0.08em; font-weight:700;">
                            <span style="font-size:1.1rem;">⚡</span>
                            <span>STATUS: DATA FORENSICS COMPLETE</span>
                        </div>
                    </div>

                    <!-- ROADMAP RECAP (from App 1) -->
                    <div class="ai-risk-container" style="margin:0 auto 22px auto; max-width:780px; padding:16px; border:1px solid var(--border-color-primary); border-radius:10px;">
                        <h4 style="margin-top:0; font-size:1.05rem; text-align:center;">🗺️ Your Investigation Roadmap</h4>
                        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin-top:12px;">

                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">1. Learn the Rules</div>
                                <div style="font-size:0.85rem; color:var(--body-text-color-subdued);">✔ Completed</div>
                            </div>

                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">2. Collect Evidence</div>
                                <div style="font-size:0.85rem; color:var(--body-text-color-subdued);">✔ Completed</div>
                            </div>

                            <div class="hint-box" style="margin-top:0; border-left:4px solid #3b82f6; background:rgba(59,130,246,0.08);">
                                <div style="font-weight:700; color:#1d4ed8;">3. Prove the Prediction Error</div>
                                <div style="font-size:0.85rem; color:var(--body-text-color-subdued);">⬅ You are here</div>
                            </div>

                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">4. Diagnose Harm</div>
                                <div style="font-size:0.85rem; color:var(--body-text-color-subdued);">Coming Soon</div>
                            </div>

                        </div>
                    </div>

                    <!-- TRANSITION NARRATIVE -->
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 14px auto; text-align:center;">
                        Welcome back, Detective. In Part 1, you uncovered powerful evidence: the <strong>input data</strong>
                        feeding this model was distorted by history and unequal sampling. 
                    </p>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 18px auto; text-align:center;">
                        But corrupted data is only <em>half</em> the case. Now comes the decisive moment in any AI audit:
                        testing whether these distorted inputs have produced <strong>unfair outputs</strong> — unequal predictions
                        that change real lives.
                    </p>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        In Part 2, you will compare the model’s predictions against reality, group by group.  
                        This is where you expose <strong>false positives</strong>, <strong>false negatives</strong>, and the
                        hidden <strong>error gaps</strong> that reveal whether the system is treating people unfairly.
                    </p>

                </div>
            </div>

        """
    },
    {
        "id": 1, "title": "Why outputs matter",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🎯 WHY OUTPUTS MATTER</h2>
                <div class="slide-body">

                    <!-- Badge -->
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px;
                                    border-radius:999px; background:var(--background-fill-secondary);
                                    border:1px solid var(--border-color-primary); font-size:0.95rem;
                                    text-transform:uppercase; letter-spacing:0.08em; font-weight:700;">
                            <span style="font-size:1.1rem;">🎛️</span>
                            <span>FOCUS: MODEL OUTPUTS</span>
                        </div>
                    </div>

                    <!-- Core framing -->
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
                        In Part 1, you uncovered distortions in the <strong>input data</strong>. But biased data doesn’t
                        automatically prove the model’s <em>decisions</em> are unfair.
                    </p>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 24px auto; text-align:center;">
                        To protect people — and society — we must test the <strong>outputs</strong>.  
                        When an AI model makes a prediction, that prediction can directly shape someone’s future.
                    </p>

                    <!-- Visual box: consequences -->
                    <div class="ai-risk-container" style="margin:22px auto; max-width:780px; padding:20px;
                                border-radius:12px; background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.25);">
                        <h4 style="margin-top:0; font-size:1.2rem; text-align:center;">🔎 Why Outputs Shape Justice</h4>
                        <p style="font-size:1rem; text-align:center; margin-bottom:12px;">
                            A model’s prediction doesn’t just describe risk — it can <strong>change real decisions</strong>.
                        </p>

                        <ul style="font-size:0.98rem; max-width:700px; margin:0 auto; padding-left:20px;">
                            <li><strong>High risk score →</strong> denied bail, longer detention, fewer opportunities.</li>
                            <li><strong>Low risk score →</strong> early release, access to programs, second chances.</li>
                        </ul>

                        <p style="font-size:1rem; text-align:center; margin:12px 0;">
                            And mistakes go both ways:
                        </p>

                        <ul style="font-size:0.98rem; max-width:700px; margin:0 auto; padding-left:20px;">
                            <li><strong>False alarms</strong> keep low-risk people locked up — harming families and communities.</li>
                            <li><strong>Missed warnings</strong> can release someone who may commit another crime — harming public safety.</li>
                        </ul>
                    </div>

                    <!-- Interactive cards: click to reveal examples -->
                    <div class="ai-risk-container" style="margin:18px auto; max-width:780px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🗂️ Evidence Cards: How Outputs Change Lives</h4>
                        <p style="font-size:0.95rem; text-align:center; margin:6px 0 14px 0; color:var(--body-text-color-subdued);">
                            Click each card to reveal what can happen when an AI model gets it wrong.
                        </p>

                        <div style="display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px;">

                            <!-- Card 1: Human impact (false alarm) -->
                            <details class="hint-box" style="margin-top:0;">
                                <summary style="display:flex; align-items:center; justify-content:space-between; font-weight:800; cursor:pointer;">
                                    <span>🧑‍⚖️ Card 1: False Alarm</span>
                                    <span style="font-size:0.8rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                                </summary>
                                <div style="font-size:0.95rem; margin-top:10px;">
                                    A young person with a low real risk gets a <strong>high risk score</strong>.
                                    The judge sees the number and decides to keep them in jail.
                                </div>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:6px;">
                                    They lose their job, miss school, and their family struggles without them — even though the model was wrong.
                                    This is the cost of <strong>too many false alarms</strong>.
                                </div>
                            </details>

                            <!-- Card 2: Public safety impact (missed warning) -->
                            <details class="hint-box" style="margin-top:0;">
                                <summary style="display:flex; align-items:center; justify-content:space-between; font-weight:800; cursor:pointer;">
                                    <span>🌍 Card 2: Missed Warning</span>
                                    <span style="font-size:0.8rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                                </summary>
                                <div style="font-size:0.95rem; margin-top:10px;">
                                    Someone with a high real risk gets a <strong>low risk score</strong>.
                                    They are released early because the system says they are “safe”.
                                </div>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:6px;">
                                    If they go on to commit another crime, people in the community are harmed,
                                    and trust in the justice system and AI tools drops.
                                    This is the danger of <strong>missed warnings</strong>.
                                </div>
                            </details>

                            <!-- Card 3: Justice & Equity tradeoff -->
                            <details class="hint-box" style="margin-top:0;">
                                <summary style="display:flex; align-items:center; justify-content:space-between; font-weight:800; cursor:pointer;">
                                    <span>⚖️ Card 3: Unequal Mistakes</span>
                                    <span style="font-size:0.8rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                                </summary>
                                <div style="font-size:0.95rem; margin-top:10px;">
                                    Now imagine these errors are not random: one group gets <strong>more false alarms</strong>,
                                    another gets <strong>more missed warnings</strong>.
                                </div>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:6px;">
                                    The result? Some communities are over-punished, others are under-protected.
                                    The AI system doesn’t just make mistakes — it can make society <strong>less just</strong>.
                                </div>
                            </details>

                        </div>
                    </div>

                    <!-- Societal lens -->
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 18px auto; text-align:center;">
                        This is why fairness experts warn that AI can make society more just — or less just —
                        depending on whether its <strong>mistakes fall equally</strong> across groups.
                    </p>

                    <p style="font-size:1.05rem; max-width:760px; margin:0 auto 22px auto; text-align:center;">
                        A biased model doesn’t just harm individuals.  
                        It can also <strong>distort public safety</strong> by being too strict on some people and too lenient with others.
                    </p>

                    <!-- Justice & Equity callout -->
                    <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444;">
                        <div style="font-weight:800;">Justice & Equity Check</div>
                        <div style="font-size:0.95rem;">
                            A system threatens Justice & Equity when one group receives more <strong>false alarms</strong>,
                            more <strong>missed warnings</strong>, or more <strong>harmful outcomes</strong>.
                            This doesn’t just break fairness — it weakens trust and safety for everyone.
                        </div>
                    </div>

                    <!-- Next move -->
                    <div style="text-align:center; margin-top:24px; padding:14px;
                                background:rgba(59,130,246,0.08); border-radius:10px;">
                        <p style="font-size:1.05rem; margin:0;">
                            <strong>Your next task:</strong> Test whether the model treats all groups fairly.
                            You’ll compare predictions vs reality to see whose futures are being shaped — or distorted.
                        </p>
                    </div>

                </div>
            </div>

        """
    },
    {
        "id": 2, "title": "HOW WE KNOW WHEN AI IS WRONG",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⏳ THE POWER OF HINDSIGHT</h2>
                <div class="slide-body">

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        How do we know when the AI is wrong if we can’t open its code?
                        Simple — we compare what the model <em>predicted</em> with what <em>actually happened</em>.
                    </p>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Investigative journalists at <strong>ProPublica</strong> collected public records on over 7,000 defendants.
                        This gives us a rare advantage: the real-world outcomes — also called the <strong>ground truth</strong> —
                        that let us check the AI’s homework.
                    </p>

                    <div class="ai-risk-container">
                        <div style="display:grid; gap:14px; margin-top:16px;">

                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">1. The Prediction (What the AI expected)</div>
                                <div style="font-size:0.95rem; margin-top:4px;">
                                    The model’s guess about the future (e.g., “High Risk”).
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e;">
                                <div style="font-weight:bold; color:#22c55e;">2. What Actually Happened (the Ground Truth)</div>
                                <div style="font-size:0.95rem; margin-top:4px;">
                                    The real outcome in the world (e.g., “Did Not Re-offend”).  
                                    This is the answer key we use to check whether the AI was right.
                                </div>
                            </div>

                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:760px; margin:22px auto 10px auto; text-align:center;">
                        When the prediction doesn’t match what happened in real life,  
                        <strong>that’s a mistake</strong> — a false alarm or a missed warning.
                    </p>

                    <!-- Hands-on interactive example -->
                    <div class="ai-risk-container" style="margin-top:18px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🧪 Try It Yourself: Did the AI Get It Right?</h4>
                        <p style="font-size:0.95rem; text-align:center; margin:6px 0 14px 0; color:var(--body-text-color-subdued);">
                            Look at each case file. Decide: <strong>Was the AI correct?</strong>  
                            If not, was it a <strong>false alarm</strong> or a <strong>missed warning</strong>?  
                            Click to reveal the answer.
                        </p>

                        <div style="display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px;">

                            <!-- Case 1 -->
                            <details class="hint-box" style="margin-top:0;">
                                <summary style="display:flex; flex-direction:column; gap:6px; cursor:pointer;">
                                    <div style="display:flex; align-items:center; justify-content:space-between; font-weight:800;">
                                        <span>📁 Case #1</span>
                                        <span style="font-size:0.8rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                                    </div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">
                                        Prediction: <strong>High Risk</strong><br>
                                        Real Outcome: <strong>Did Not Re-offend</strong>
                                    </div>
                                </summary>
                                <div style="font-size:0.95rem; margin-top:10px;">
                                    ❌ The AI was <strong>wrong</strong>.  
                                    This is a <strong>false alarm</strong> (false positive).
                                </div>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:6px;">
                                    A low-risk person was treated as “dangerous.”  
                                    They may have been kept in jail longer or denied opportunities unfairly.
                                </div>
                            </details>

                            <!-- Case 2 -->
                            <details class="hint-box" style="margin-top:0;">
                                <summary style="display:flex; flex-direction:column; gap:6px; cursor:pointer;">
                                    <div style="display:flex; align-items:center; justify-content:space-between; font-weight:800;">
                                        <span>📁 Case #2</span>
                                        <span style="font-size:0.8rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                                    </div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">
                                        Prediction: <strong>Low Risk</strong><br>
                                        Real Outcome: <strong>Re-offended</strong>
                                    </div>
                                </summary>
                                <div style="font-size:0.95rem; margin-top:10px;">
                                    ❌ The AI was <strong>wrong</strong>.  
                                    This is a <strong>missed warning</strong> (false negative).
                                </div>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:6px;">
                                    Someone who was actually high risk was treated as “safe,”  
                                    which can harm people in the community and weaken trust.
                                </div>
                            </details>

                            <!-- Case 3 -->
                            <details class="hint-box" style="margin-top:0;">
                                <summary style="display:flex; flex-direction:column; gap:6px; cursor:pointer;">
                                    <div style="display:flex; align-items:center; justify-content:space-between; font-weight:800;">
                                        <span>📁 Case #3</span>
                                        <span style="font-size:0.8rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                                    </div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color-subdued);">
                                        Prediction: <strong>High Risk</strong><br>
                                        Real Outcome: <strong>Re-offended</strong>
                                    </div>
                                </summary>
                                <div style="font-size:0.95rem; margin-top:10px;">
                                    ✅ The AI was <strong>correct</strong>.  
                                    This is a <strong>true positive</strong>.
                                </div>
                                <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:6px;">
                                    The model’s high-risk flag matched reality.  
                                    Correct predictions like this are useful — as long as errors aren’t concentrated on certain groups.
                                </div>
                            </details>

                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:760px; margin:22px auto 0 auto; text-align:center;">
                        Next, you’ll stop looking at single cases and start scanning <strong>patterns</strong>:  
                        which groups get more false alarms or missed warnings from the model.
                    </p>

                </div>
            </div>


        """
    },
    {
        "id": 3, "title": "Analysis: False Positives",
        "html": """
            <div class="scenario-box">
            <h2 class="slide-title">📡 OUTPUT SCAN: SEARCHING FOR UNEQUAL MISTAKES</h2>
            <div class="slide-body">

                <p style="font-size:1.05rem; max-width:800px; margin:0 auto 18px auto; text-align:center;">
                    You’ve seen individual cases where the AI made false alarms and missed warnings.  
                    Now it’s time to look for <strong>patterns</strong> across groups.  
                    A fair system should not make <em>more mistakes</em> for one group than another.
                </p>

                <div class="ai-risk-container" style="margin-top:10px;">
                    <h4 style="margin-top:0; font-size:1.2rem; text-align:center;">🧠 What an Output Error Scan Looks For</h4>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px;">
                        
                        <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                            <div style="font-weight:800;">1. False Alarm Rate</div>
                            <div style="font-size:0.95rem; color:var(--body-text-color-subdued);">
                                How often the model labels someone “High Risk” when they actually did <em>not</em> re-offend.
                            </div>
                            <div style="font-size:0.92rem; margin-top:6px;">
                                High false alarms mean more people may face detention or punishment unfairly.
                            </div>
                        </div>

                        <div class="hint-box" style="margin-top:0; border-left:4px solid #3b82f6;">
                            <div style="font-weight:800;">2. Missed Warning Rate</div>
                            <div style="font-size:0.95rem; color:var(--body-text-color-subdued);">
                                How often the model labels someone “Low Risk” when they actually re-offend.
                            </div>
                            <div style="font-size:0.92rem; margin-top:6px;">
                                High missed warnings can harm communities and reduce trust in the justice system.
                            </div>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:20px auto 14px auto; text-align:center;">
                        If one group receives more false alarms or more missed warnings,  
                        the system may violate <strong>Justice & Equity</strong>.
                    </p>
                </div>

                  <!-- FIRST REAL OUTPUT SCAN: False Alarms by Race -->
                  <div class="ai-risk-container" style="margin-top:30px; padding:22px; border-width:2px;">

                    <h3 style="margin-top:0; font-size:1.35rem; text-align:center;">
                      📡 FIRST SCAN: FALSE ALARMS BY RACE
                    </h3>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 18px auto; text-align:center;">
                      You’ll now scan for <strong>False Alarms</strong> — cases where the AI marked someone as “High Risk”
                      even though they <em>did not</em> re-offend. Click the scan below to reveal what you found.
                    </p>

                    <!-- INTERACTIVE SCAN -->
                    <details style="border:1px solid var(--border-color-primary); border-radius:12px; overflow:hidden; margin-top:10px;">
                      <summary style="list-style:none; cursor:pointer; padding:14px 18px; font-weight:800;
                                      text-align:center; background:var(--background-fill-secondary);">
                        📡 SCAN: False Alarms by Race — Click to reveal analysis
                      </summary>

                      <!-- EVERYTHING BELOW IS REVEALED AFTER CLICK -->
                      <div style="text-align:center; padding:24px;">

                        <!-- Title -->
                        <h4 style="margin-top:0; font-size:1.25rem; margin-bottom:20px;">
                          📊 False Alarm Rate (Incorrect High-Risk Flags)
                        </h4>

                        <!-- CLEAN, ALIGNED BAR CHART -->
                        <div style="display:flex; justify-content:center; gap:40px;">

                          <!-- African-American Bar -->
                          <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                            <div style="font-size:2rem; font-weight:800; color:#ef4444; margin-bottom:6px;">
                              45%
                            </div>
                            <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                        width:80px; height:180px; background:#fee2e2; border-radius:8px;
                                        overflow:hidden; border:1px solid #fca5a5;">
                              <div style="background:#ef4444; height:45%; width:100%;"></div>
                            </div>
                            <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">
                              African-American
                            </div>
                          </div>

                          <!-- White Bar -->
                          <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                            <div style="font-size:2rem; font-weight:800; color:#3b82f6; margin-bottom:6px;">
                              23%
                            </div>
                            <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                        width:80px; height:180px; background:#dbeafe; border-radius:8px;
                                        overflow:hidden; border:1px solid #93c5fd;">
                              <div style="background:#3b82f6; height:23%; width:100%;"></div>
                            </div>
                            <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">
                              White
                            </div>
                          </div>

                        </div>

                        <p style="font-size:0.95rem; max-width:760px; margin:20px auto 0 auto;
                                  color:var(--body-text-color-subdued);">
                          African-American defendants received nearly <strong>twice as many</strong> false alarms as White defendants.
                        </p>

                        <!-- DETECTIVE ANALYSIS -->
                        <div class="hint-box" style="background:rgba(239, 68, 68, 0.08); margin-top:24px; border-left:4px solid #ef4444;">
                          <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>

                          <p style="font-size:0.98rem; margin-bottom:10px;">
                            This scan reveals a major imbalance: the AI is producing <strong>nearly twice as many false alarms</strong>
                            for African-American defendants as for White defendants. These are people labeled “High Risk”
                            even though they <em>did not</em> re-offend.
                          </p>

                          <p style="font-size:0.98rem; margin-bottom:12px;">
                            As a detective, this is where you’d ask:
                            <strong>“If the system is wrong, who pays the price for the mistake?”</strong>
                            In this case, one group consistently receives harsher mistakes — and that pattern has a name.
                          </p>

                          <!-- Punitive Bias Definition -->
                          <div style="background:white; border:1px solid #ef4444; border-radius:8px; padding:14px; margin:14px 0;">
                            <h4 style="margin:0; color:#ef4444; font-size:1.05rem;">⚠️ What You Just Found: Punitive Bias</h4>
                            <p style="font-size:0.95rem; margin:8px 0 0 0;">
                              <strong>Punitive Bias</strong> happens when an AI makes mistakes that unfairly label certain groups as
                              “more dangerous,” causing harsher outcomes — even when those individuals did nothing wrong.
                            </p>
                            <p style="font-size:0.9rem; margin:8px 0 0 0; color:var(--body-text-color-subdued);">
                              These mistakes aren’t random. One group gets <em>more false alarms</em>, <em>more harsh labels</em>,  
                              and <em>more punishment</em>. That’s a serious warning of a Justice & Equity failure.
                            </p>
                          </div>

                          <p style="font-size:0.95rem; margin-top:8px;">
                            The takeaway: this model isn’t just inaccurate — it is <strong>inaccurate in a way that targets one group more than others</strong>.
                            That means the harm is not evenly shared.
                          </p>
                        </div>


                        <!-- TRANSITION TO NEXT SCAN -->
                        <div style="text-align:center; margin-top:26px; padding:14px; background:rgba(59,130,246,0.08); border-radius:10px;">
                          <p style="font-size:1.05rem; margin:0;">
                            <strong>Next:</strong> Punitive Bias is only half the story.  
                            What about mistakes that make the system <em>too lenient</em>?  
                            Let’s scan for <strong>False Negatives</strong> — cases where the model missed real danger.
                          </p>
                        </div>

                      </div> <!-- end of revealed content -->

                    </details>

                  </div>
                          

        """
    },

    {
        "id": 4, "title": "Analysis: Missed Risk",
        "html": """
            <div class="scenario-box">
              <h2 class="slide-title">⚖️ THE OTHER SIDE OF ERROR: MISSED RISK</h2>
              <div class="slide-body">

                <!-- Step badge -->
                <div style="display:flex; justify-content:center; margin-bottom:18px;">
                  <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px;
                              border-radius:999px; background:var(--background-fill-secondary);
                              border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                    <span style="font-size:1.1rem;">📋</span>
                    <span>STEP 3: PROVE THE PREDICTION ERROR — Part 2</span>
                  </div>
                </div>

                <!-- Framing text -->
                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 14px auto; text-align:center;">
                  You’ve already uncovered <strong>Punitive Bias</strong> — the model is more likely to
                  <em>wrongly label</em> African-American defendants as “High Risk.”
                </p>
                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 18px auto; text-align:center;">
                  But that’s only half the story. Now we ask the mirror question:
                  <strong>Who does the model go too easy on?</strong> 
                </p>

                <div class="ai-risk-container" style="margin-top:8px;">
                  <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🧩 What We’re Looking For Now</h4>
                  <p style="font-size:1.0rem; max-width:780px; margin:0 auto 8px auto; text-align:center;">
                    In AI fairness, we don’t just look at who is punished more. We also look at who the system
                    <strong>lets off the hook</strong> — even when they later cause harm.
                  </p>
                  <p style="font-size:1.0rem; max-width:780px; margin:0 auto; text-align:center; color:var(--body-text-color-subdued);">
                    These cases are called <strong>False Negatives</strong>: people labeled “Low Risk” by the AI
                    who actually <em>did re-offend</em> in the real world.
                  </p>
                </div>

                <!-- Simple explanatory analogy -->
                <div class="hint-box" style="margin-top:16px;">
                  <div style="font-weight:800;">🔁 Two Types of Dangerous Mistakes</div>
                  <div style="font-size:0.98rem; margin-top:4px;">
                    You can think of the model like a security checkpoint:
                  </div>
                  <ul style="font-size:0.95rem; margin:8px 0 0 18px; padding:0;">
                    <li><strong>False Positive (False Alarm):</strong> Stopping an innocent person as if they were dangerous.</li>
                    <li><strong>False Negative (Missed Risk):</strong> Letting a dangerous person walk through unchecked.</li>
                  </ul>
                  <p style="font-size:0.96rem; margin-top:10px;">
                    Justice &amp; Equity means checking <em>both</em>: Who is unfairly stopped, and who is unfairly waved through.
                  </p>
                </div>

                <!-- INTERACTIVE SCAN: FALSE NEGATIVES BY RACE -->
                <div class="ai-risk-container" style="margin-top:24px; padding:22px; border-width:2px;">
                  <h3 style="margin-top:0; font-size:1.3rem; text-align:center;">
                    📡 SECOND SCAN: MISSED RISK BY RACE
                  </h3>

                  <p style="font-size:1.02rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
                    Now you’ll scan for <strong>False Negatives</strong> — people the AI marked as “Low Risk” who
                    <em>did</em> go on to re-offend. Click the scan to reveal what you found in the COMPAS data.
                  </p>

                  <details style="border:1px solid var(--border-color-primary); border-radius:12px; overflow:hidden; margin-top:10px;">
                    <summary style="list-style:none; cursor:pointer; padding:14px 18px; font-weight:800;
                                    text-align:center; background:var(--background-fill-secondary);">
                      📡 SCAN: Missed Risk by Race — Click to reveal analysis
                    </summary>

                    <!-- Revealed content -->
                    <div style="text-align:center; padding:24px;">

                      <h4 style="margin-top:0; font-size:1.2rem; margin-bottom:18px;">
                        📊 False Negative Rate (Missed High-Risk Cases)
                      </h4>

                      <p style="font-size:0.95rem; max-width:780px; margin:0 auto 18px auto;">
                        Among people who <strong>did re-offend</strong>, how often did the AI incorrectly label them as
                        “Low Risk”?
                      </p>

                      <!-- Vertical bar chart -->
                      <div style="display:flex; justify-content:center; gap:40px;">

                        <!-- African-American bar -->
                        <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                          <div style="font-size:1.8rem; font-weight:800; color:#ef4444; margin-bottom:6px;">
                            28%
                          </div>
                          <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                      width:80px; height:180px; background:#fee2e2; border-radius:8px;
                                      overflow:hidden; border:1px solid #fca5a5;">
                            <div style="background:#ef4444; height:28%; width:100%;"></div>
                          </div>
                          <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">
                            African-American
                          </div>
                        </div>

                        <!-- White bar -->
                        <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                          <div style="font-size:1.8rem; font-weight:800; color:#3b82f6; margin-bottom:6px;">
                            48%
                          </div>
                          <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                      width:80px; height:180px; background:#dbeafe; border-radius:8px;
                                      overflow:hidden; border:1px solid #93c5fd;">
                            <div style="background:#3b82f6; height:48%; width:100%;"></div>
                          </div>
                          <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">
                            White
                          </div>
                        </div>

                      </div>

                      <p style="font-size:0.95rem; max-width:760px; margin:20px auto 0 auto;
                                color:var(--body-text-color-subdued);">
                        In this dataset, White defendants who went on to re-offend were <strong>much more likely</strong>
                        to be labeled “Low Risk” than African-American defendants who re-offended.
                      </p>

                      <!-- Detective analysis -->
                      <div class="hint-box" style="background:rgba(59,130,246,0.08); margin-top:24px; border-left:4px solid #3b82f6;">
                        <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>

                        <p style="font-size:0.98rem; margin-bottom:10px;">
                          Earlier, you found <strong>Punitive Bias</strong>: more harsh mistakes for African-American defendants
                          (False Alarms). Now you’ve found the flip side:
                          the model is <strong>more likely to underestimate risk</strong> for White defendants.
                        </p>

                        <p style="font-size:0.98rem; margin-bottom:10px;">
                          This pattern is sometimes called a <strong>leniency pattern</strong>: the system gives one group
                          <em>more second chances</em>, even when those people are statistically more likely to re-offend.
                        </p>

                        <p style="font-size:0.98rem; margin-bottom:10px;">
                          Put together, this means:
                        </p>
                        <ul style="font-size:0.95rem; margin:0 0 8px 18px; padding:0;">
                          <li><strong>More false harshness</strong> for one group (Punitive Bias).</li>
                          <li><strong>More false leniency</strong> for another group (leniency pattern / Missed Risk).</li>
                        </ul>

                        <p style="font-size:0.96rem; margin-top:8px;">
                          The system isn’t just “a bit wrong.” It is wrong in a way that <strong>shifts both punishment and
                          protection unequally</strong>. That’s a serious Justice &amp; Equity concern.
                        </p>
                      </div>

                      <!-- Optional: small bonus tip -->
                      <details style="margin:22px 0 0 0; border:1px solid var(--border-color-primary); border-radius:10px; overflow:hidden;">
                        <summary style="
                            list-style:none;
                            cursor:pointer;
                            padding:10px 16px;
                            display:flex;
                            align-items:center;
                            justify-content:space-between;
                            gap:10px;
                            background:rgba(59,130,246,0.08);
                            font-weight:800;
                            font-size:0.9rem;">
                          <span>
                            🕵️ BONUS DETECTIVE TIP: Justice vs. Safety — what balance do you want?
                          </span>
                          <span style="font-size:0.85rem; opacity:0.8;">Click to reveal</span>
                        </summary>
                        <div style="padding:14px 16px 18px 16px; background:rgba(15,23,42,0.02);">
                          <p style="font-size:0.96rem; margin-top:0;">
                            Some people argue: “As long as we catch dangerous people, it’s fine.” But your scan shows something deeper:
                            <strong>who is protected and who is punished depends on how the errors are distributed.</strong>
                          </p>
                          <ul style="font-size:0.94rem; margin:8px 0 0 18px; padding:0;">
                            <li>If False Alarms target one group → <strong>unfair punishment.</strong></li>
                            <li>If Missed Risk favors another group → <strong>unfair protection.</strong></li>
                          </ul>
                          <p style="font-size:0.96rem; margin-top:10px;">
                            As a Bias Detective, your job is not to make the model perfect — it’s to make sure its mistakes
                            <strong>don’t systematically favor or hurt specific groups</strong>.
                          </p>
                        </div>
                      </details>

                    </div> <!-- end revealed content -->

                  </details>
                </div>

                <!-- Short transition to next step -->
                <div style="text-align:center; margin-top:24px; padding:14px; background:rgba(59,130,246,0.1); border-radius:10px;">
                  <p style="font-size:1.04rem; margin:0; font-weight:600;">
                    Next, compare these errors across <strong>Gender → Age → Geography</strong> to before you build and submit your full audit report.
                  </p>
                </div>

              </div>
            </div>

        """
    },
    {
        "id": 5, "title": "Analysis: Gender",
        "html": """
              <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: GENERALIZATION BIAS (GENDER)</h2>
                <div class="slide-body">

                  <!-- Step badge -->
                  <div style="display:flex; justify-content:center; margin-bottom:18px;">
                    <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px;
                                border-radius:999px; background:var(--background-fill-secondary);
                                border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                      <span style="font-size:1.1rem;">📋</span>
                      <span>STEP 3: PROVE THE PREDICTION ERROR — Gender Scan</span>
                    </div>
                  </div>

                  <!-- Framing text -->
                  <p style="font-size:1.05rem; max-width:780px; margin:0 auto 14px auto; text-align:center;">
                    Earlier, you discovered that the COMPAS dataset is <strong>81% male</strong> and only <strong>19% female</strong>.
                    Now we’ll see what that imbalance does to the model’s behavior.
                  </p>
                  <p style="font-size:1.05rem; max-width:780px; margin:0 auto 18px auto; text-align:center;">
                    We’re looking for <strong>Generalization Bias</strong> — when the AI learns patterns mostly from one group
                    and then <em>copies</em> those patterns onto another group where they don’t really fit.
                  </p>

                  <!-- 92% Accuracy Trap -->
                  <div class="hint-box" style="margin-top:10px;">
                    <div style="font-weight:800;">🎭 The “92% Accuracy” Trap</div>

                    <p style="font-size:0.98rem; margin-top:6px;">
                      Imagine the COMPAS engineering team proudly reports:
                      <br><strong>“Our model is 92% accurate.”</strong>
                    </p>

                    <p style="font-size:0.98rem; margin-top:8px;">
                      Sounds impressive, right? But that <strong>92% is an average</strong> over the whole dataset —
                      and we already know that most of that dataset is men.
                    </p>

                    <p style="font-size:0.98rem; margin-top:8px;">
                      That means the “92% accuracy” number mostly reflects how well the model does on
                      <strong>men’s cases</strong>. The accuracy for women could be much worse, but you’d never
                      see that from the headline number alone.
                    </p>

                    <p style="font-size:0.98rem; margin-top:8px;">
                      A system can look “92% accurate overall” while still making
                      <strong>dangerously bad mistakes for a smaller group</strong> it barely saw in training.
                    </p>

                    <p style="font-size:0.96rem; margin-top:10px; color:var(--body-text-color-subdued);">
                      Your job as a Bias Detective is to <strong>break that average apart</strong> and see who the
                      model is really failing.
                    </p>
                  </div>

                  <!-- INTERACTIVE SCAN: ERROR PATTERN BY GENDER -->
                  <div class="ai-risk-container" style="margin-top:22px; padding:22px; border-width:2px;">
                    <h3 style="margin-top:0; font-size:1.25rem; text-align:center;">
                      📡 GENDER SCAN: WHO GETS MISTAKENLY FLAGGED?
                    </h3>

                    <p style="font-size:1.0rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
                      Now you’ll scan for how often the AI <strong>over-predicts risk</strong> for men vs women.
                      Think of it as asking: <strong>“Whose behavior is the model bad at reading?”</strong>
                    </p>

                    <details style="border:1px solid var(--border-color-primary); border-radius:12px; overflow:hidden; margin-top:10px;">
                      <summary style="list-style:none; cursor:pointer; padding:14px 18px; font-weight:800;
                                      text-align:center; background:var(--background-fill-secondary);">
                        📡 SCAN: High-Risk Errors by Gender — Click to reveal analysis
                      </summary>

                      <!-- Revealed content -->
                      <div style="text-align:center; padding:24px;">

                        <h4 style="margin-top:0; font-size:1.15rem; margin-bottom:14px;">
                          📊 Example Scan: Incorrect “High Risk” Flags on Less Serious Charges
                        </h4>

                        <p style="font-size:0.95rem; max-width:780px; margin:0 auto 18px auto;">
                          Imagine your scan finds this pattern for people with <strong>less serious (non-violent) charges</strong>:
                          how often does the AI wrongly label them as “High Risk”?
                        </p>

                        <!-- Simple vertical bar chart -->
                        <div style="display:flex; justify-content:center; gap:40px; margin-top:10px;">

                          <!-- Men bar -->
                          <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                            <div style="font-size:1.6rem; font-weight:800; color:#3b82f6; margin-bottom:6px;">
                              18%
                            </div>
                            <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                        width:80px; height:180px; background:#dbeafe; border-radius:8px;
                                        overflow:hidden; border:1px solid #93c5fd;">
                              <div style="background:#3b82f6; height:18%; width:100%;"></div>
                            </div>
                            <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">
                              Men
                            </div>
                            <div style="margin-top:4px; font-size:0.85rem; color:var(--body-text-color-subdued);">
                              Wrong “High Risk” label
                            </div>
                          </div>

                          <!-- Women bar -->
                          <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                            <div style="font-size:1.6rem; font-weight:800; color:#ef4444; margin-bottom:6px;">
                              32%
                            </div>
                            <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                        width:80px; height:180px; background:#fee2e2; border-radius:8px;
                                        overflow:hidden; border:1px solid #fca5a5;">
                              <div style="background:#ef4444; height:32%; width:100%;"></div>
                            </div>
                            <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">
                              Women
                            </div>
                            <div style="margin-top:4px; font-size:0.85rem; color:var(--body-text-color-subdued);">
                              Wrong “High Risk” label
                            </div>
                          </div>

                        </div>

                        <p style="font-size:0.93rem; max-width:760px; margin:20px auto 0 auto;
                                  color:var(--body-text-color-subdued);">
                          In this kind of pattern, women with similar, less serious charges are
                          <strong>more likely</strong> to be mistakenly treated as “High Risk” than men.
                        </p>

                        <!-- Detective analysis -->
                        <div class="hint-box" style="background:rgba(239,68,68,0.08); margin-top:22px; border-left:4px solid #ef4444;">
                          <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>

                          <p style="font-size:0.98rem; margin-bottom:10px;">
                            The model was trained mostly on men. So when it sees women’s cases, it often
                            <strong>copies male patterns onto them</strong> — even when women’s real re-offense patterns are different.
                          </p>

                          <p style="font-size:0.98rem; margin-bottom:10px;">
                            This is an example of <strong>generalization bias</strong>:
                            the AI takes what it learned from one group and wrongly generalizes it to another group
                            it doesn’t really understand.
                          </p>

                          <p style="font-size:0.98rem; margin-bottom:10px;">
                            The “92% accuracy” claim hides this:
                          </p>
                          <ul style="font-size:0.95rem; margin:0 0 8px 18px; padding:0;">
                            <li>The model might be doing <strong>okay for men</strong> (the majority).</li>
                            <li>But for women, it makes <strong>more bad calls</strong> — flagging them as “High Risk”
                                when their actual risk is lower.</li>
                          </ul>

                          <p style="font-size:0.96rem; margin-top:8px;">
                            To judges or the public, the system looks “92% accurate.” But to the women
                            being misclassified, the system feels <strong>unfair, over-cautious, and mistrustful</strong>.
                          </p>
                        </div>

                      </div> <!-- end revealed content -->

                    </details>
                  </div>

                  <!-- Short transition -->
                  <div style="text-align:center; margin-top:24px; padding:14px; background:rgba(59,130,246,0.1); border-radius:10px;">
                    <p style="font-size:1.04rem; margin:0; font-weight:600;">
                      Next, you’ll repeat this logic for <strong>Age</strong> and <strong>Geography</strong> to see
                      whether the model’s “overall accuracy” is hiding more unfair patterns.
                    </p>
                  </div>

                </div>
              </div>

        """
    },
    {
        "id": 6, "title": "Age Scan",
        "html": """
              <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: AGE BLIND SPOTS</h2>
                <div class="slide-body">

                  <!-- Step badge -->
                  <div style="display:flex; justify-content:center; margin-bottom:18px;">
                    <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px;
                                border-radius:999px; background:var(--background-fill-secondary);
                                border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                      <span style="font-size:1.1rem;">📋</span>
                      <span>STEP 3: PROVE THE PREDICTION ERROR — Age Scan</span>
                    </div>
                  </div>

                  <!-- Framing text -->
                  <p style="font-size:1.05rem; max-width:780px; margin:0 auto 14px auto; text-align:center;">
                    You’ve analyzed Race and Gender. Now we examine <strong>Age</strong> — one of the strongest predictors of real-world recidivism.
                  </p>

                  <p style="font-size:1.05rem; max-width:780px; margin:0 auto 18px auto; text-align:center;">
                    Criminology shows that <strong>risk generally drops as people get older</strong>.  
                    But the COMPAS dataset you scanned earlier is <strong>heavily concentrated in ages 25–45</strong>.
                    That imbalance creates a new kind of error pattern.
                  </p>

                  <!-- Age Accuracy Trap -->
                  <div class="hint-box" style="margin-top:10px;">
                    <div style="font-weight:800;">🎭 Why Age Matters — and How Accuracy Lies Again</div>

                    <p style="font-size:0.98rem; margin-top:6px;">
                      Suppose the COMPAS team proudly reports:
                      <br><strong>“Our model is 92% accurate at predicting reoffending.”</strong>
                    </p>

                    <p style="font-size:0.98rem; margin-top:8px;">
                      But here’s the trick: <strong>most of the dataset is 25–45 years old</strong>.  
                      The model learns their patterns extremely well.
                    </p>

                    <p style="font-size:0.98rem; margin-top:8px;">
                      That means the “92% accuracy” mostly describes <em>middle-aged predictions</em>, not the whole population.
                    </p>

                    <p style="font-size:0.98rem; margin-top:8px;">
                      For younger adults (&lt; 25) and older adults (&gt; 45), the model has <strong>far fewer training examples</strong>,
                      so its predictions can become much less reliable — while still looking perfect in the headline number.
                    </p>

                    <p style="font-size:0.96rem; margin-top:10px; color:var(--body-text-color-subdued);">
                      Your job is to uncover where the AI struggles — especially when the stakes involve sentencing or pretrial release.
                    </p>
                  </div>

                  <!-- INTERACTIVE SCAN: AGE ERROR PATTERN -->
                  <div class="ai-risk-container" style="margin-top:22px; padding:22px; border-width:2px;">
                    <h3 style="margin-top:0; font-size:1.25rem; text-align:center;">
                      📡 AGE SCAN: WHO GETS MISLABELED?
                    </h3>

                    <p style="font-size:1.0rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
                      Click the scan to reveal how the model performs across different age groups — especially for people
                      the AI saw less often during training.
                    </p>

                    <details style="border:1px solid var(--border-color-primary); border-radius:12px; overflow:hidden; margin-top:10px;">
                      <summary style="list-style:none; cursor:pointer; padding:14px 18px; font-weight:800;
                                      text-align:center; background:var(--background-fill-secondary);">
                        📡 SCAN: Prediction Accuracy by Age — Click to reveal
                      </summary>

                      <!-- Revealed content -->
                      <div style="text-align:center; padding:24px;">

                        <h4 style="margin-top:0; font-size:1.2rem; margin-bottom:14px;">
                          📊 Example Scan: Incorrect “High Risk” Predictions Across Age Groups
                        </h4>

                        <p style="font-size:0.95rem; max-width:780px; margin:0 auto 18px auto;">
                          When we look at people who <strong>did not reoffend</strong>, how often did the AI incorrectly label them as “High Risk”?
                        </p>

                        <!-- Simple bar chart -->
                        <div style="display:flex; justify-content:center; gap:40px; margin-top:10px;">

                          <!-- Under 25 -->
                          <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                            <div style="font-size:1.6rem; font-weight:800; color:#ef4444; margin-bottom:6px;">
                              33%
                            </div>
                            <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                        width:80px; height:180px; background:#fee2e2; border-radius:8px;
                                        overflow:hidden; border:1px solid #fca5a5;">
                              <div style="background:#ef4444; height:33%; width:100%;"></div>
                            </div>
                            <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">Under 25</div>
                          </div>

                          <!-- Age 25–45 -->
                          <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                            <div style="font-size:1.6rem; font-weight:800; color:#3b82f6; margin-bottom:6px;">
                              18%
                            </div>
                            <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                        width:80px; height:180px; background:#dbeafe; border-radius:8px;
                                        overflow:hidden; border:1px solid #93c5fd;">
                              <div style="background:#3b82f6; height:18%; width:100%;"></div>
                            </div>
                            <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">25–45</div>
                          </div>

                          <!-- Over 45 -->
                          <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                            <div style="font-size:1.6rem; font-weight:800; color:#f97316; margin-bottom:6px;">
                              27%
                            </div>
                            <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                        width:80px; height:180px; background:#ffedd5; border-radius:8px;
                                        overflow:hidden; border:1px solid #fdba74;">
                              <div style="background:#f97316; height:27%; width:100%;"></div>
                            </div>
                            <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">Over 45</div>
                          </div>

                        </div>

                        <p style="font-size:0.93rem; max-width:760px; margin:20px auto 0 auto;
                                  color:var(--body-text-color-subdued);">
                          The AI is most accurate for ages 25–45 (the group it saw most often),
                          and makes more mistakes for younger and older adults — groups with fewer training examples.
                        </p>

                        <!-- Detective analysis -->
                        <div class="hint-box" style="background:rgba(239,68,68,0.08); margin-top:22px; border-left:4px solid #ef4444;">
                          <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>

                          <p style="font-size:0.98rem; margin-bottom:10px;">
                            This is classic <strong>Representation Bias</strong> + <strong>Generalization Error</strong>.
                            The model understands 25–45 year olds well, because that’s where most of its data came from—
                            but it misreads younger and older adults.
                          </p>

                          <p style="font-size:0.98rem; margin-bottom:10px;">
                            Even if the model boasts a “92% accuracy” score, that average hides the fact that its errors
                            are <strong>unevenly distributed</strong> — with younger and older adults getting the worst predictions.
                          </p>

                          <ul style="font-size:0.95rem; margin:0 0 8px 18px; padding:0;">
                            <li><strong>Younger defendants</strong> → more “High Risk” false alarms.</li>
                            <li><strong>Older defendants</strong> → misclassified because the model didn’t see enough examples.</li>
                          </ul>

                          <p style="font-size:0.96rem; margin-top:8px;">
                            The system doesn’t just make mistakes — it makes <strong>predictable mistakes</strong> for certain age groups.
                            That’s a major Justice & Equity concern.
                          </p>
                        </div>

                      </div> <!-- end revealed content -->

                    </details>
                  </div>

                  <!-- Short transition -->
                  <div style="text-align:center; margin-top:24px; padding:14px; background:rgba(59,130,246,0.1); border-radius:10px;">
                    <p style="font-size:1.04rem; margin:0; font-weight:600;">
                      Next, you'll explore how <strong>Geography</strong> affects predictions before building your full audit report.
                    </p>
                  </div>

                </div>
              </div>

        """
    },
    {
        "id": 7, "title": "Geography Scan",
        "html": """
            <div class="scenario-box">
              <h2 class="slide-title">⚠️ THE “DOUBLE PROXY”: GEOGRAPHY AS RACE & CLASS</h2>
              <div class="slide-body">

                <!-- Step badge -->
                <div style="display:flex; justify-content:center; margin-bottom:18px;">
                  <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px;
                              border-radius:999px; background:var(--background-fill-secondary);
                              border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                    <span style="font-size:1.1rem;">📋</span>
                    <span>STEP 3: PROVE THE PREDICTION ERROR — Geography Scan</span>
                  </div>
                </div>

                <!-- Intro framing -->
                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 12px auto; text-align:center;">
                  You’ve analyzed <strong>Race</strong>, <strong>Gender</strong>, and <strong>Age</strong>.  
                  Now we look at one of the most powerful — and misunderstood — risk factors:
                  <strong>Where someone lives</strong>.
                </p>

                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
                  Many people think: <em>“Just delete the Race or Income columns and the model becomes fair.”</em>  
                  But geography often acts as a <strong>Double Proxy</strong>:
                </p>

                <ul style="max-width:760px; margin:0 auto 18px auto; font-size:0.98rem;">
                  <li><strong>Proxy for Race:</strong> Neighborhood segregation means ZIP codes encode racial patterns.</li>
                  <li><strong>Proxy for Class:</strong> Housing density and economic inequality are baked into location data.</li>
                </ul>

                <p style="font-size:1.03rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                  So even if an AI model never sees Race or Income, it can still learn their patterns through geography.
                </p>

                <!-- Geography Accuracy Trap -->
                <div class="hint-box" style="margin-top:10px;">
                  <div style="font-weight:800;">🎭 The Geography Trap: Why “92% Accuracy” Means Nothing Here</div>

                  <p style="font-size:0.98rem; margin-top:6px;">
                    Imagine the COMPAS team again reports:
                    <br><strong>“Our model is 92% accurate across all locations.”</strong>
                  </p>

                  <p style="font-size:0.98rem; margin-top:8px;">
                    But “92% accuracy” could simply mean the model works well for <strong>low-density suburban areas</strong>,
                    where most of the training data came from.
                  </p>

                  <p style="font-size:0.98rem; margin-top:8px;">
                    For people in <strong>high-density neighborhoods</strong> — often poorer areas with different policing patterns —
                    the model might make <em>far more mistakes</em>.
                  </p>

                  <p style="font-size:0.98rem; margin-top:10px; color:var(--body-text-color-subdued);">
                    Your job is to uncover whether predictions change dramatically just based on a person’s address.
                  </p>
                </div>

                <!-- INTERACTIVE SCAN: FALSE POSITIVES BY LOCATION -->
                <div class="ai-risk-container" style="margin-top:22px; padding:22px; border-width:2px;">
                  <h3 style="margin-top:0; font-size:1.25rem; text-align:center;">
                    📡 GEOGRAPHY SCAN: WHO GETS FALSELY FLAGGED?
                  </h3>

                  <p style="font-size:1.0rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
                    Click below to reveal how a person’s neighborhood affects the AI’s mistakes — especially
                    <strong>False Positives</strong> (“High Risk” labels for people who did <em>not</em> reoffend).
                  </p>

                  <details style="border:1px solid var(--border-color-primary); border-radius:12px; overflow:hidden; margin-top:10px;">
                    <summary style="list-style:none; cursor:pointer; padding:14px 18px; font-weight:800;
                                    text-align:center; background:var(--background-fill-secondary);">
                      📡 SCAN: False Positive Rate by Neighborhood — Click to reveal
                    </summary>

                    <!-- Revealed content -->
                    <div style="text-align:center; padding:24px;">

                      <h4 style="margin-top:0; font-size:1.2rem; margin-bottom:14px;">
                        📊 Incorrect “High Risk” Flags by Location
                      </h4>

                      <p style="font-size:0.95rem; max-width:780px; margin:0 auto 18px auto;">
                        How often does the model falsely label someone as “High Risk” based only on the type of neighborhood they come from?
                      </p>

                      <!-- Bar chart -->
                      <div style="display:flex; justify-content:center; gap:40px; margin-top:10px;">

                        <!-- Rural/Suburban -->
                        <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                          <div style="font-size:1.8rem; font-weight:800; color:#3b82f6; margin-bottom:6px;">
                            22%
                          </div>
                          <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                      width:80px; height:180px; background:#dbeafe; border-radius:8px;
                                      overflow:hidden; border:1px solid #93c5fd;">
                            <div style="background:#3b82f6; height:22%; width:100%;"></div>
                          </div>
                          <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">
                            Rural / Suburban
                          </div>
                        </div>

                        <!-- High Density Urban -->
                        <div style="display:flex; flex-direction:column; align-items:center; width:150px;">
                          <div style="font-size:1.8rem; font-weight:800; color:#ef4444; margin-bottom:6px;">
                            58%
                          </div>
                          <div style="display:flex; flex-direction:column; justify-content:flex-end;
                                      width:80px; height:180px; background:#fee2e2; border-radius:8px;
                                      overflow:hidden; border:1px solid #fca5a5;">
                            <div style="background:#ef4444; height:58%; width:100%;"></div>
                          </div>
                          <div style="margin-top:10px; font-weight:700; font-size:0.95rem;">
                            High-Density Urban
                          </div>
                        </div>
                      </div>

                      <p style="font-size:0.93rem; max-width:760px; margin:20px auto 0 auto;
                                color:var(--body-text-color-subdued);">
                        The model is <strong>more than twice as likely</strong> to falsely flag someone from a 
                        high-density neighborhood as “High Risk.”
                      </p>

                      <!-- Detective analysis -->
                      <div class="hint-box" style="background:rgba(239,68,68,0.08); margin-top:22px; border-left:4px solid #ef4444;">
                        <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>

                        <p style="font-size:0.98rem; margin-bottom:10px;">
                          The model is not “just predicting risk.”  
                          It is picking up on policing patterns baked into different neighborhoods.
                        </p>

                        <p style="font-size:0.98rem; margin-bottom:10px;">
                          High-density areas — which often contain more low-income and minority residents —
                          have more recorded arrests. The model learns that pattern and <strong>treats location
                          as a risk factor</strong>, even when individuals present no greater danger.
                        </p>

                        <p style="font-size:0.98rem; margin-bottom:10px;">
                          This is the essence of the <strong>Double Proxy</strong> problem:
                        </p>

                        <ul style="font-size:0.95rem; margin:0 0 8px 18px; padding:0;">
                          <li>Neighborhood → reflects Race patterns</li>
                          <li>Neighborhood → reflects Class patterns</li>
                        </ul>

                        <p style="font-size:0.96rem; margin-top:8px;">
                          When the model is twice as harsh based on location alone, that’s not public safety —
                          it’s <strong>proxy discrimination</strong> hidden inside an algorithm.
                        </p>
                      </div>

                    </div> <!-- end revealed content -->

                  </details>
                </div>

                <!-- Short transition -->
                <div style="text-align:center; margin-top:24px; padding:14px; background:rgba(59,130,246,0.1); border-radius:10px;">
                  <p style="font-size:1.04rem; margin:0; font-weight:600;">
                    Now you have scans for <strong>Race → Gender → Age → Geography</strong>.
                    You're ready to assemble your final audit report.
                  </p>
                </div>

              </div>
            </div>

        """
    },
    {
        "id": 8, "title": "Final Audit Report",
        "html": """
      <div class="scenario-box">
        <h2 class="slide-title">🧾 FINAL AUDIT REPORT: PULLING IT ALL TOGETHER</h2>
        <div class="slide-body">

          <!-- Status badge -->
          <div style="display:flex; justify-content:center; margin-bottom:14px;">
            <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px;
                        border-radius:999px; background:rgba(34,197,94,0.1);
                        border:1px solid #22c55e; font-size:0.95rem; font-weight:700;">
              <span style="font-size:1.1rem;">🏁</span>
              <span>STATUS: STEP 4 — DIAGNOSE HARM (FINAL STEP)</span>
            </div>
          </div>

          <!-- Mini roadmap strip -->
          <div class="ai-risk-container" style="margin-bottom:16px; padding:14px 16px;">
            <h4 style="margin-top:0; font-size:1.05rem; text-align:center;">🗺️ Your Investigation Journey</h4>
            <div style="display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:8px; margin-top:10px; font-size:0.9rem;">
              <div class="hint-box" style="margin-top:0; opacity:0.7;">
                <div style="font-weight:700;">Step 1</div>
                <div>Learn the Rules</div>
                <div style="font-size:0.8rem; margin-top:4px; color:var(--body-text-color-subdued);">Justice &amp; Equity</div>
              </div>
              <div class="hint-box" style="margin-top:0; opacity:0.7;">
                <div style="font-weight:700;">Step 2</div>
                <div>Collect Evidence</div>
                <div style="font-size:0.8rem; margin-top:4px; color:var(--body-text-color-subdued);">Data forensics</div>
              </div>
              <div class="hint-box" style="margin-top:0; opacity:0.7;">
                <div style="font-weight:700;">Step 3</div>
                <div>Prove the Error</div>
                <div style="font-size:0.8rem; margin-top:4px; color:var(--body-text-color-subdued);">Error gaps by group</div>
              </div>
              <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e; background:rgba(34,197,94,0.12);">
                <div style="font-weight:700; color:#166534;">Step 4</div>
                <div style="font-weight:700; color:#166534;">Diagnose Harm</div>
                <div style="font-size:0.8rem; margin-top:4px; color:#166534;">Turn findings into a report</div>
              </div>
            </div>
            <p style="font-size:0.9rem; margin:10px 0 0 0; text-align:center; color:var(--body-text-color-subdued);">
              You’re now at the final stage: explaining <strong>who is harmed, who is protected</strong>,
              and why this model can’t be treated as neutral.
            </p>
          </div>

          <!-- Framing text -->
          <p style="font-size:1.05rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
            You’ve completed your investigation. You scanned the COMPAS model’s behavior across
            <strong>Race, Gender, Age, and Geography</strong>, and uncovered patterns that affect
            who is punished and who is protected.
          </p>
          <p style="font-size:1.05rem; max-width:780px; margin:0 auto 18px auto; text-align:center;">
            Now it’s time to turn your findings into a <strong>clear audit report</strong> that a judge,
            journalist, or policy-maker could understand.
          </p>

          <!-- Evidence board / summary visualization -->
          <div class="ai-risk-container" style="margin-top:10px;">
            <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">📌 Evidence Board: Bias Patterns You Found</h4>
            <p style="font-size:0.98rem; max-width:780px; margin:0 auto 10px auto; text-align:center; color:var(--body-text-color-subdued);">
              This is your “case file” overview. Each card is a key piece of evidence you can choose to include
              in your final report.
            </p>

            <div style="display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px; margin-top:12px;">

              <!-- Punitive Bias -->
              <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                <div style="font-weight:800;">⚖️ Punitive Bias (False Alarms by Race)</div>
                <div style="font-size:0.95rem; margin-top:4px;">
                  African-American defendants were <strong>far more likely</strong> to be falsely labeled
                  “High Risk” compared to White defendants.
                </div>
                <div style="font-size:0.9rem; margin-top:6px; color:var(--body-text-color-subdued);">
                  Result: More people from this group face unnecessary jail, stricter bail, or longer sentences.
                </div>
              </div>

              <!-- Missed Risk / Leniency -->
              <div class="hint-box" style="margin-top:0; border-left:4px solid #3b82f6;">
                <div style="font-weight:800;">🛑 Missed Risk (Leniency Pattern by Race)</div>
                <div style="font-size:0.95rem; margin-top:4px;">
                  White defendants who went on to re-offend were <strong>more likely</strong> to be labeled
                  “Low Risk” than African-American defendants.
                </div>
                <div style="font-size:0.9rem; margin-top:6px; color:var(--body-text-color-subdued);">
                  Result: One group receives more “second chances” from the model than another.
                </div>
              </div>

              <!-- Generalization Bias (Gender) -->
              <div class="hint-box" style="margin-top:0; border-left:4px solid #ec4899;">
                <div style="font-weight:800;">👥 Generalization Bias (Gender)</div>
                <div style="font-size:0.95rem; margin-top:4px;">
                  The dataset is <strong>81% male / 19% female</strong>, but the model reports a high-looking
                  overall “accuracy” (for example, 92%) without showing group differences.
                </div>
                <div style="font-size:0.9rem; margin-top:6px; color:var(--body-text-color-subdued);">
                  Result: The model appears strong overall but may be much less reliable for women than for men.
                </div>
              </div>

              <!-- Age / Geography -->
              <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e;">
                <div style="font-weight:800;">📍 Age Skew &amp; Geography as Proxy</div>
                <div style="font-size:0.95rem; margin-top:4px;">
                  Most data focuses on <strong>ages 25–45</strong> and on certain high-policing neighborhoods,
                  meaning the model is “trained” more on some ages and places than others.
                </div>
                <div style="font-size:0.9rem; margin-top:6px; color:var(--body-text-color-subdued);">
                  Result: Where someone lives and how old they are can act as <em>stand-ins</em> (proxies) for race
                  and class in the risk score.
                </div>
              </div>

            </div>
          </div>

          <!-- Bridge to interactive report builder (Gradio components go below this HTML) -->
          <div class="ai-risk-container" style="margin-top:18px;">
            <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🧱 Build Your Audit Report</h4>
            <p style="font-size:0.98rem; max-width:780px; margin:0 auto 4px auto; text-align:center;">
              Now you’ll assemble a short, clear report using the evidence you’ve collected.
            </p>
            <p style="font-size:0.98rem; max-width:780px; margin:0 auto; text-align:center; color:var(--body-text-color-subdued);">
              Use the checklist below to select which bias patterns to include. We’ll help you auto-draft
              a paragraph you could share with a judge, journalist, or policy-maker.
            </p>
          </div>

        </div>
      </div>



        """
    },
    {
        "id": 9, "title": "Mission Accomplished",
        "html": """
            <div class="scenario-box">
              <h2 class="slide-title">⚖️ THE FINAL VERDICT</h2>
              <div class="slide-body">
                
                <!-- Status badge -->
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
                    font-weight:700;">
                    <span style="font-size:1.1rem;">🕵️‍♀️</span>
                    <span>STATUS: FULL AUDIT COMPLETED</span>
                  </div>
                </div>

                <!-- Framing text -->
                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
                  You’ve seen behind the curtain. The vendor is still proudly advertising the model as 
                  <strong>“92% Accurate”</strong> and “ready to deploy” to clear the court backlog.
                </p>
                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 24px auto; text-align:center;">
                  But your investigation uncovered something else: the model’s mistakes are not random — 
                  they <strong>hit some groups harder</strong> and <strong>protect others more</strong>.
                </p>

                <!-- Evidence recap -->
                <div class="ai-risk-container" style="margin-top:6px;">
                  <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🧾 Your Case File: What You Found</h4>
                  <div style="display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px; margin-top:10px;">

                    <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                      <div style="font-weight:800;">Punitive Bias (False Alarms)</div>
                      <div style="font-size:0.95rem; margin-top:4px;">
                        African-American defendants were <strong>more often mislabeled “High Risk”</strong> when 
                        they did <em>not</em> re-offend — unfair extra punishment.
                      </div>
                    </div>

                    <div class="hint-box" style="margin-top:0; border-left:4px solid #3b82f6;">
                      <div style="font-weight:800;">Leniency Pattern (Missed Risk)</div>
                      <div style="font-size:0.95rem; margin-top:4px;">
                        White defendants who <strong>did re-offend</strong> were more likely to be labeled “Low Risk” — 
                        extra protection and second chances.
                      </div>
                    </div>

                    <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e;">
                      <div style="font-weight:800;">Generalization Gaps (Age & Gender)</div>
                      <div style="font-size:0.95rem; margin-top:4px;">
                        The model learned patterns mostly from younger men, making it <strong>less reliable</strong> 
                        for women and older adults.
                      </div>
                    </div>

                    <div class="hint-box" style="margin-top:0; border-left:4px solid #f97316;">
                      <div style="font-weight:800;">Location as a Proxy</div>
                      <div style="font-size:0.95rem; margin-top:4px;">
                        Even without an explicit “Race” column, features like <strong>ZIP code</strong> and neighborhood 
                        acted as <strong>proxies</strong> for race and social class.
                      </div>
                    </div>

                  </div>

                  <p style="font-size:0.96rem; max-width:780px; margin:16px auto 0 auto; text-align:center; color:var(--body-text-color-subdued);">
                    In short: the model’s errors are <strong>systematic</strong>, not random — and they 
                    <strong>do not treat people equally</strong>.
                  </p>
                </div>

                <!-- Decision card -->
                <div class="ai-risk-container" style="margin-top:22px; border-width:2px;">
                  <h4 style="margin-top:0; font-size:1.18rem; text-align:center;">🎯 Your Decision as Bias Detective</h4>
                  <p style="font-size:1.02rem; max-width:780px; margin:0 auto 16px auto; text-align:center;">
                    The court is waiting for your recommendation. Should this model be used on real people <em>as it is now</em>?
                  </p>

                  <div style="display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:14px; margin-top:10px;">

                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:800;">Option A: Approve &amp; Deploy</div>
                      <div style="font-size:0.95rem; margin-top:4px;">
                        Treat <strong>92% overall accuracy</strong> as “good enough” and allow the model to 
                        keep making unequal errors across groups.
                      </div>
                    </div>

                    <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e; background:rgba(34,197,94,0.08);">
                      <div style="font-weight:800;">Option B: Pause &amp; Fix First</div>
                      <div style="font-size:0.95rem; margin-top:4px;">
                        Declare that the model is <strong>too unfair to deploy</strong> without changes and 
                        recommend a fairness upgrade before anyone relies on it.
                      </div>
                    </div>

                  </div>

                  <p style="font-size:0.98rem; max-width:780px; margin:18px auto 0 auto; text-align:center;">
                    On the <strong>next screen</strong>, your choice will unlock your new mission as a 
                    <strong>Fairness Engineer</strong> — the person who doesn’t just find bias, but actually fixes it.
                  </p>
                </div>

              </div>
            </div>



        """
    },
    {
        "id": 10, "title": "Mission Accomplished",
        "html": """
            <div class="scenario-box">
              <h2 class="slide-title">🎖️ PROMOTION UNLOCKED: FAIRNESS ENGINEER</h2>
              <div class="slide-body">

                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 20px auto; text-align:center;">
                  You made the call: <strong>the model cannot be deployed safely</strong> in its current form.
                  That decision required evidence, judgment, and courage. 
                </p>

                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 28px auto; text-align:center;">
                  Exposing bias is only the first half of the mission. 
                  Now, the real work begins.
                </p>

                <div style="
                  margin-top:20px; 
                  padding:28px; 
                  background:linear-gradient(135deg, rgba(59,130,246,0.1), rgba(16,185,129,0.1));
                  border-radius:14px; 
                  border:2px solid var(--color-accent);
                  text-align:center;">
                  
                  <h3 style="margin-top:0; color:var(--color-accent); font-size:1.4rem;">
                    🎓 Your New Role: <strong>Fairness Engineer</strong>
                  </h3>

                  <p style="font-size:1.05rem; margin-top:10px;">
                    You’re no longer just investigating harm — you’re responsible for <strong>fixing the system</strong>.
                  </p>

                  <ul style="list-style:none; padding:0; margin-top:20px; font-size:1.0rem; line-height:1.6;">
                    <li>🔧 <strong>Remove biased features</strong> like direct demographic attributes (race, sex, age)</li>
                    <li>🕵️‍♀️ <strong>Hunt down proxy variables</strong> (ZIP code, prior arrests, income) that quietly re-create bias</li>
                    <li>📊 <strong>Design representative data strategies</strong> so the model reflects the people it affects</li>
                    <li>🗺️ <strong>Build an ethical roadmap</strong> with ongoing audits, documentation, and stakeholder input</li>
                  </ul>

                  <p style="font-size:1.05rem; margin-top:24px;">
                    You’ve proven you can diagnose systemic failures.<br>
                    Now you’ll learn how to rebuild a risk model that is <strong>more fair, more transparent, and safer</strong> to use.
                  </p>
                </div>

                <div style="text-align:center; margin-top:30px;">
                  <p style="font-size:1.1rem; font-weight:600;">
                    👉 Your next mission is <strong>Activity 8: Fairness Fixer</strong>.<br>
                    There, you’ll remove biased and proxy features, redesign the data strategy,<br>
                    and draft a continuous improvement plan for Justice &amp; Equity.
                  </p>
                </div>

              </div>
            </div>


        """
    }
]

# --- 6. INTERACTIVE CONFIG ---
QUIZ_CONFIG = {
    1: {
        "t": "t11",
        "q": "Which outcome shows why testing AI outputs is essential?",
        "o": [
            "A) Wrong predictions can harm people or communities when one group gets more mistakes",
            "B) Only the input data determines fairness",
            "C) Outputs don’t affect real decisions"
        ],
        "a": "A) Wrong predictions can harm people or communities when one group gets more mistakes",
        "success": "Impact Identified. You understand that unequal mistakes shape real lives—and real safety."
    },
    2: {
        "t": "t12",
        "q": "How did ProPublica figure out when the AI was right or wrong?",
        "o": [
            "A) Interviewed judges",
            "B) Compared the AI’s predictions to what actually happened over 2 years",
            "C) Ran computer simulations"
        ],
        "a": "B) Compared the AI’s predictions to what actually happened over 2 years",
        "success": "Hindsight Unlocked. You used the real outcomes to check the AI’s accuracy."
    },
    3: {
      "t": "t13",
      "q": "If Black defendants get 45% False Alarms and White defendants get 23%, what does this mean for fairness?",
      "o": [
        "A) The model is fair to both groups",
        "B) The model is lenient toward everyone",
        "C) The AI wrongly flags Black defendants as 'High Risk' almost twice as often"
      ],
      "a": "C) The AI wrongly flags Black defendants as 'High Risk' almost twice as often",
      "success": "Harm Confirmed: Punitive Bias against Black defendants."
    },
    4: {
      "t": "t14",
      "q": "False Negatives: 48% (White) vs 28% (African-American). What does this pattern show?",
      "o": [
        "A) The model is giving White defendants more 'free passes' (leniency pattern / Missed Risk)",
        "B) The model is equally fair to both groups",
        "C) The model is harsher on White defendants"
      ],
      "a": "A) The model is giving White defendants more 'free passes' (leniency pattern / Missed Risk)",
      "success": "Harm Verified: Missed Risk / Leniency Pattern — the model underestimates risk for White defendants, shifting protection unevenly."
    },
    5: {
      "t": "t15",
      "q": "If the model reports '92% accuracy' overall but frequently mislabels women as High Risk, what does this reveal?",
      "o": [
        "A) The high accuracy score is hiding errors for a smaller group (generalization bias)",
        "B) The model is equally accurate for everyone",
        "C) Women must actually be higher risk"
      ],
      "a": "A) The high accuracy score is hiding errors for a smaller group (generalization bias)",
      "success": "Bias Confirmed: The '92% accuracy' average hides uneven mistakes. The model generalizes men’s patterns onto women."
    },
    6: {
      "t": "t16",
      "q": "Why does the model make fewer mistakes for ages 25–45?",
      "o": [
        "A) Because this age group appears most often in the model's data",
        "B) Because people 25–45 commit fewer crimes",
        "C) Because the model is designed to ignore younger and older adults"
      ],
      "a": "A) Because this age group appears most often in the model's data",
      "success": "Pattern Detected: The model performs best on the group it saw the most — and struggles with younger and older adults."
    },
    7: {
      "t": "t17",
      "q": "If the model is twice as likely to falsely flag people from high-density neighborhoods as “High Risk,” what does this reveal?",
      "o": [
        "A) Geography is acting as a proxy for race and class patterns the model has learned",
        "B) High-density neighborhoods are naturally more dangerous",
        "C) The model needs more CPU power to run correctly"
      ],
      "a": "A) Geography is acting as a proxy for race and class patterns the model has learned",
      "success": "Bias Confirmed: Location becomes a stand-in for race and class, causing unfair punishment toward people from certain neighborhoods."
    },
    8: {
      "t": "t18",
      "q": "After uncovering consistent unfair errors across Race, Gender, Age, and Geography, how should you classify the model’s behavior?",
      "o": [
        "A) A minor glitch — small coding bugs happen",
        "B) User error — judges are interpreting the scores wrong",
        "C) A systemic failure — the model’s patterns create unequal harm"
      ],
      "a": "C) A systemic failure — the model’s patterns create unequal harm",
      "success": "Audit Complete: You correctly identified this as a systemic failure, not a small mistake."
    },
    9: {
      "t": "t19",
      "q": "Given everything you uncovered in your investigation, what should happen to this AI model?",
      "o": [
        "A) Deploy it immediately — 92% accuracy is good enough.",
        "B) Pause deployment — the model needs fairness repairs first.",
        "C) Delete the model entirely — AI can never be fair."
      ],
      "a": "B) Pause deployment — the model needs fairness repairs first.",
      "success": "Correct. A responsible auditor doesn't rush a system with documented harm. Now step into your next mission: becoming the Fairness Engineer who fixes it."
    }
    }

# --- 7. RENDERERS ---
def generate_success_message(prev, curr, specific_text):
    old_score = float(prev.get("score", 0) or 0) if prev else 0.0
    new_score = float(curr.get("score", 0) or 0)
    diff_score = new_score - old_score

    old_rank = prev.get("rank", "–") if prev else "–"
    new_rank = curr.get("rank", "–")

    # Are ranks integers? If yes, we can reason about direction.
    ranks_are_int = isinstance(old_rank, int) and isinstance(new_rank, int)
    rank_diff = old_rank - new_rank if ranks_are_int else 0  # positive => rank improved

    # --- STYLE SELECTION -------------------------------------------------
    # First-time score: special "on the board" moment
    if old_score == 0 and new_score > 0:
        style_key = "first"
    else:
        if ranks_are_int:
            if rank_diff >= 3:
                style_key = "major"   # big rank jump
            elif rank_diff > 0:
                style_key = "climb"   # small climb
            elif diff_score > 0 and new_rank == old_rank:
                style_key = "solid"   # better score, same rank
            else:
                style_key = "tight"   # leaderboard shifted / no visible rank gain
        else:
            # When we can't trust rank as an int, lean on score change
            style_key = "solid" if diff_score > 0 else "tight"

    # --- TEXT + CTA BY STYLE --------------------------------------------
    card_class = "profile-card success-card"

    if style_key == "first":
        card_class += " first-score"
        header_emoji = "🎉"
        header_title = "You're Officially on the Board!"
        summary_line = (
            "You just earned your first Moral Compass Score — you're now part of the global rankings."
        )
        cta_line = "Scroll down to take your next step and start climbing."
    elif style_key == "major":
        header_emoji = "🔥"
        header_title = "Major Moral Compass Boost!"
        summary_line = (
            "Your decision made a big impact — you just moved ahead of other participants."
        )
        cta_line = "Scroll down to take on your next challenge and keep the boost going."
    elif style_key == "climb":
        header_emoji = "🚀"
        header_title = "You're Climbing the Leaderboard"
        summary_line = "Nice work — you edged out a few other participants."
        cta_line = "Scroll down to continue your investigation and push even higher."
    elif style_key == "tight":
        header_emoji = "📊"
        header_title = "The Leaderboard Is Shifting"
        summary_line = (
            "Other teams are moving too. You'll need a few more strong decisions to stand out."
        )
        cta_line = "Take on the next question to strengthen your position."
    else:  # "solid"
        header_emoji = "✅"
        header_title = "Progress Logged"
        summary_line = "Your ethical insight increased your Moral Compass Score."
        cta_line = "Try the next scenario to break into the next tier."

    # --- SCORE / RANK LINES ---------------------------------------------

    # First-time: different wording (no previous score)
    if style_key == "first":
        score_line = f"🧭 Score: <strong>{new_score:.3f}</strong>"
        if ranks_are_int:
            rank_line = f"🏅 Initial Rank: <strong>#{new_rank}</strong>"
        else:
            rank_line = f"🏅 Initial Rank: <strong>#{new_rank}</strong>"
    else:
        score_line = (
            f"🧭 Score: {old_score:.3f} → <strong>{new_score:.3f}</strong> "
            f"(+{diff_score:.3f})"
        )

        if ranks_are_int:
            if old_rank == new_rank:
                rank_line = f"📊 Rank: <strong>#{new_rank}</strong> (holding steady)"
            elif rank_diff > 0:
                rank_line = (
                    f"📈 Rank: #{old_rank} → <strong>#{new_rank}</strong> "
                    f"(+{rank_diff} places)"
                )
            else:
                rank_line = (
                    f"🔻 Rank: #{old_rank} → <strong>#{new_rank}</strong> "
                    f"({rank_diff} places)"
                )
        else:
            rank_line = f"📊 Rank: <strong>#{new_rank}</strong>"

    # --- HTML COMPOSITION -----------------------------------------------
    return f"""
    <div class="{card_class}">
        <div class="success-header">
            <div>
                <div class="success-title">{header_emoji} {header_title}</div>
                <div class="success-summary">{summary_line}</div>
            </div>
            <div class="success-delta">
                +{diff_score:.3f}
            </div>
        </div>

        <div class="success-metrics">
            <div class="success-metric-line">{score_line}</div>
            <div class="success-metric-line">{rank_line}</div>
        </div>

        <div class="success-body">
            <p class="success-body-text">{specific_text}</p>
            <p class="success-cta">{cta_line}</p>
        </div>
    </div>
    """

def render_top_dashboard(data, module_id):
    display_score = 0.0; count_completed = 0; rank_display = "–"; team_rank_display = "–"
    if data:
        display_score = float(data.get('score', 0.0))
        rank_display = f"#{data.get('rank', '–')}"
        team_rank_display = f"#{data.get('team_rank', '–')}"
        count_completed = len(data.get('completed_task_ids', []) or [])
    progress_pct = min(100, int((count_completed / TOTAL_COURSE_TASKS) * 100))
    return f"""<div class="summary-box"><div class="summary-box-inner"><div class="summary-metrics"><div style="text-align:center;"><div class="label-text">Moral Compass Score</div><div class="score-text-primary">🧭 {display_score:.3f}</div></div><div class="divider-vertical"></div><div style="text-align:center;"><div class="label-text">Team Rank</div><div class="score-text-team">{team_rank_display}</div></div><div class="divider-vertical"></div><div style="text-align:center;"><div class="label-text">Global Rank</div><div class="score-text-global">{rank_display}</div></div></div><div class="summary-progress"><div class="progress-label">Mission Progress: {progress_pct}%</div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width:{progress_pct}%;"></div></div></div></div></div>"""

def render_leaderboard_card(data, username, team_name):
    team_rows = ""; user_rows = ""
    if data and data.get("all_teams"):
        for i, t in enumerate(data["all_teams"]):
            cls = "row-highlight-team" if t["team"] == team_name else "row-normal"
            team_rows += f"<tr class='{cls}'><td style='padding:8px;text-align:center;'>{i+1}</td><td style='padding:8px;'>{t['team']}</td><td style='padding:8px;text-align:right;'>{t['avg']:.3f}</td></tr>"
    if data and data.get("all_users"):
        for i, u in enumerate(data["all_users"]):
            cls = "row-highlight-me" if u.get("username") == username else "row-normal"
            sc = float(u.get('moralCompassScore',0))
            if u.get("username") == username and data.get('score') != sc: sc = data.get('score')
            user_rows += f"<tr class='{cls}'><td style='padding:8px;text-align:center;'>{i+1}</td><td style='padding:8px;'>{u.get('username','')}</td><td style='padding:8px;text-align:right;'>{sc:.3f}</td></tr>"
    return f"""<div class="scenario-box leaderboard-card"><h3 class="slide-title" style="margin-bottom:10px;">📊 Live Standings</h3><div class="lb-tabs"><input type="radio" id="lb-tab-team" name="lb-tabs" checked><label for="lb-tab-team" class="lb-tab-label">🏆 Team</label><input type="radio" id="lb-tab-user" name="lb-tabs"><label for="lb-tab-user" class="lb-tab-label">👤 Individual</label><div class="lb-tab-panels"><div class="lb-panel panel-team"><div class='table-container'><table class='leaderboard-table'><thead><tr><th>Rank</th><th>Team</th><th style='text-align:right;'>Avg 🧭</th></tr></thead><tbody>{team_rows}</tbody></table></div></div><div class="lb-panel panel-user"><div class='table-container'><table class='leaderboard-table'><thead><tr><th>Rank</th><th>Agent</th><th style='text-align:right;'>Score 🧭</th></tr></thead><tbody>{user_rows}</tbody></table></div></div></div></div></div>"""

# --- 8. CSS ---
css = """
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
.slide-body { font-size: 1.12rem; line-height: 1.65; }

/* Hint boxes */
.hint-box {
  padding: 12px;
  border-radius: 10px;
  background: var(--background-fill-secondary);
  border: 1px solid var(--border-color-primary);
  margin-top: 10px;
  font-size: 0.98rem;
}

/* Success / profile card */
.profile-card.success-card {
  padding: 20px;
  border-radius: 14px;
  border-left: 6px solid #22c55e;
  background: linear-gradient(135deg, rgba(34,197,94,0.08), var(--block-background-fill));
  margin-top: 16px;
  box-shadow: 0 4px 18px rgba(0,0,0,0.08);
  font-size: 1.04rem;
  line-height: 1.55;
}
.profile-card.first-score {
  border-left-color: #facc15;
  background: linear-gradient(135deg, rgba(250,204,21,0.18), var(--block-background-fill));
}
.success-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 8px; }
.success-title { font-size: 1.26rem; font-weight: 900; color: #16a34a; }
.success-summary { font-size: 1.06rem; color: var(--body-text-color-subdued); margin-top: 4px; }
.success-delta { font-size: 1.5rem; font-weight: 800; color: #16a34a; }
.success-metrics { margin-top: 10px; padding: 10px 12px; border-radius: 10px; background: var(--background-fill-secondary); font-size: 1.06rem; }
.success-metric-line { margin-bottom: 4px; }
.success-body { margin-top: 10px; font-size: 1.06rem; }
.success-body-text { margin: 0 0 6px 0; }
.success-cta { margin: 4px 0 0 0; font-weight: 700; font-size: 1.06rem; }

/* Numbers + labels */
.score-text-primary { font-size: 2.05rem; font-weight: 900; color: var(--color-accent); }
.score-text-team { font-size: 2.05rem; font-weight: 900; color: #60a5fa; }
.score-text-global { font-size: 2.05rem; font-weight: 900; }
.label-text { font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #6b7280; }

/* Progress bar */
.progress-bar-bg { width: 100%; height: 10px; background: #e5e7eb; border-radius: 6px; overflow: hidden; margin-top: 8px; }
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
.row-highlight-me, .row-highlight-team { background: rgba(96,165,250,0.18); font-weight: 700; }

/* Containers */
.ai-risk-container { margin-top: 16px; padding: 16px; background: var(--body-background-fill); border-radius: 10px; border: 1px solid var(--border-color-primary); }

/* Interactive blocks (text size tuned for 17–20 age group) */
.interactive-block { font-size: 1.06rem; }
.interactive-block .hint-box { font-size: 1.02rem; }
.interactive-text { font-size: 1.06rem; }

/* Radio sizes */
.scenario-radio-large label { font-size: 1.06rem; }
.quiz-radio-large label { font-size: 1.06rem; }

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
"""

def build_audit_report(selected_biases):
    """
    Build a short markdown audit report based on which bias patterns
    the student selects in the Final Audit slide.
    """
    if not selected_biases:
        return (
            "Select at least one bias pattern above to start drafting your audit report. "
            "Your report will appear here."
        )

    lines = []
    lines.append("### 🧾 Draft Audit Report")
    lines.append("")
    lines.append(
        "Below is a draft summary of the main bias patterns you identified in the COMPAS model. "
        "You can refine this text in your own words."
    )
    lines.append("")

    if "Punitive Bias (False Alarms by Race)" in selected_biases:
        lines.append("**1. Punitive Bias (False Alarms by Race)**")
        lines.append(
            "- African-American defendants were more likely to be falsely labeled 'High Risk' "
            "compared to White defendants, even when they did not re-offend."
        )
        lines.append(
            "- This leads to unfairly harsher treatment for one group (e.g., stricter bail, longer sentences)."
        )
        lines.append("")

    if "Missed Risk (Leniency Pattern by Race)" in selected_biases:
        lines.append("**2. Missed Risk (Leniency Pattern by Race)**")
        lines.append(
            "- Among people who actually re-offended, White defendants were more likely to be labeled "
            "'Low Risk' than African-American defendants."
        )
        lines.append(
            "- This means one group is given more 'second chances' by the model, even when their risk is high."
        )
        lines.append("")

    if "Generalization Bias (Gender)" in selected_biases:
        lines.append("**3. Generalization Bias (Gender)**")
        lines.append(
            "- The dataset is heavily skewed toward male cases (around 81% men, 19% women), "
            "yet the model is described with a single overall accuracy value (for example, 92%)."
        )
        lines.append(
            "- That single number can hide larger prediction errors for women, because the model learned "
            "mostly from male data."
        )
        lines.append("")

    if "Age Skew & Geography as Proxy" in selected_biases:
        lines.append("**4. Age Skew & Geography as Proxy**")
        lines.append(
            "- Most training data comes from ages 25–45 and from certain high-policing neighborhoods."
        )
        lines.append(
            "- Age and location can act as stand-ins (proxies) for race and class, "
            "which can quietly reintroduce inequality even if race and income columns are removed."
        )
        lines.append("")

    lines.append(
        "**Overall Conclusion:** The COMPAS model is not just 'a bit inaccurate.' Its mistakes are "
        "distributed in ways that **increase punishment for some groups and increase protection for others**, "
        "raising serious Justice & Equity concerns."
    )

    return "\n".join(lines)

# --- 9. APP FACTORY ---
def create_bias_detective_part2_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(None)
        token_state = gr.State(None)
        team_state = gr.State(None)
        module0_done = gr.State(False)
        accuracy_state = gr.State(0.0)
        task_list_state = gr.State([])

        # --- TOP ANCHOR & LOADING OVERLAY FOR NAVIGATION ---
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML("<div style='text-align:center; padding:100px;'><h2>🕵️‍♀️ Authenticating...</h2><p>Syncing Moral Compass Data...</p></div>")

        with gr.Column(visible=False) as main_app_col:
            gr.Markdown("# 🕵️‍♀️ Bias Detective: Part 2 - Algorithmic Audit")
            out_top = gr.HTML()

            # --- DYNAMIC MODULE GENERATION ---
            module_ui_elements = {}
            quiz_wiring_queue = []
            final_reset_btn = None

            for i, mod in enumerate(MODULES):
                with gr.Column(elem_id=f"module-{i}", elem_classes=["module-container"], visible=(i==0)) as mod_col:
                    gr.HTML(mod['html'])

                    # --- Final Audit interactive builder on module index 8 ---
                    if i == 8:
                        report_checklist = gr.CheckboxGroup(
                            choices=[
                                "Punitive Bias (False Alarms by Race)",
                                "Missed Risk (Leniency Pattern by Race)",
                                "Generalization Bias (Gender)",
                                "Age Skew & Geography as Proxy",
                            ],
                            label="Step 1: Select the bias patterns you want to include in your report",
                        )

                        report_preview = gr.Markdown(
                            "Select at least one bias pattern above to start drafting your audit report."
                        )

                        report_checklist.change(
                            fn=build_audit_report,
                            inputs=report_checklist,
                            outputs=report_preview,
                        )

                    # Existing quiz wiring
                    if i in QUIZ_CONFIG:
                        q_data = QUIZ_CONFIG[i]
                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(choices=q_data['o'], label="Select Answer:")
                        feedback = gr.HTML("")
                        pass

                    with gr.Row():
                        btn_prev = gr.Button("⬅️ Previous", visible=(i > 0))
                        next_label = "Next ▶️" if i < len(MODULES)-1 else "🎉 Finish Course"
                        btn_next = gr.Button(next_label, variant="primary")

                        # Reset Button (Only created in last module loop)
                        if i == len(MODULES) - 1:
                            btn_reset = gr.Button("🔄 Reset Mission (Start Over)", variant="secondary", visible=True)
                            final_reset_btn = btn_reset

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

                    if i in QUIZ_CONFIG:
                        reset_ref = btn_reset if i == len(MODULES) - 1 else None
                        quiz_wiring_queue.append((i, radio, feedback, btn_next, reset_ref))



            leaderboard_html = gr.HTML()

            # --- WIRING: CONNECT QUIZZES ---
            for mod_id, radio_comp, feedback_comp, next_btn_comp, reset_btn_ref in quiz_wiring_queue:
                def quiz_logic_wrapper(user, tok, team, acc_val, task_list, ans, mid=mod_id):
                    cfg = QUIZ_CONFIG[mid]
                    if ans == cfg['a']:
                        prev, curr, _, new_tasks = trigger_api_update(user, tok, team, mid, acc_val, task_list, cfg['t'])
                        msg = generate_success_message(prev, curr, cfg['success'])
                        return (render_top_dashboard(curr, mid), render_leaderboard_card(curr, user, team), msg, new_tasks)
                    else:
                        return (gr.update(), gr.update(), "<div class='hint-box' style='border-color:red;'>❌ Incorrect. Review the evidence above.</div>", task_list)

                radio_comp.change(
                    fn=quiz_logic_wrapper,
                    inputs=[username_state, token_state, team_state, accuracy_state, task_list_state, radio_comp],
                    outputs=[out_top, leaderboard_html, feedback_comp, task_list_state]
                )

            # --- WIRING: RESET BUTTON ---
            if final_reset_btn:
                def handle_reset(user, tok, team, acc):
                    new_list = reset_user_progress(user, tok, team, acc)
                    data, _ = ensure_table_and_get_data(user, tok, team, new_list)
                    return (
                        render_top_dashboard(data, 0),
                        render_leaderboard_card(data, user, team),
                        new_list,
                        gr.update(visible=True),  # Show Module 0
                        gr.update(visible=False)  # Hide Module 10
                    )

                final_reset_btn.click(
                    fn=handle_reset,
                    inputs=[username_state, token_state, team_state, accuracy_state],
                    outputs=[out_top, leaderboard_html, task_list_state, module_ui_elements[0][0], module_ui_elements[len(MODULES)-1][0]]
                )

        # --- LOGIC WIRING (Global) ---
        def handle_load(req: gr.Request):
            success, user, token = _try_session_based_auth(req)
            team, acc = "Team-Unassigned", 0.0
            fetched_tasks = []

            if success and user and token:
                acc, fetched_team = fetch_user_history(user, token)
                os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
                client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

                exist_team = get_or_assign_team(client, user)
                if fetched_team != "Team-Unassigned": team = fetched_team
                elif exist_team != "team-a": team = exist_team
                else: team = "team-a"

                try: user_stats = client.get_user(table_id=TABLE_ID, username=user)
                except: user_stats = None

                if user_stats:
                    if isinstance(user_stats, dict): fetched_tasks = user_stats.get("completedTaskIds") or []
                    else: fetched_tasks = getattr(user_stats, "completed_task_ids", []) or []

                if not user_stats or (team != "Team-Unassigned"):
                    client.update_moral_compass(table_id=TABLE_ID, username=user, team_name=team, metrics={"accuracy": acc}, tasks_completed=len(fetched_tasks), total_tasks=TOTAL_COURSE_TASKS, primary_metric="accuracy", completed_task_ids=fetched_tasks)
                    time.sleep(1.0)

                data, _ = ensure_table_and_get_data(user, token, team, fetched_tasks)
                return (user, token, team, False, render_top_dashboard(data, 0), render_leaderboard_card(data, user, team), acc, fetched_tasks, gr.update(visible=False), gr.update(visible=True))

            return (None, None, None, False, "<div class='hint-box'>⚠️ Auth Failed</div>", "", 0.0, [], gr.update(visible=False), gr.update(visible=True))

        demo.load(handle_load, None, [username_state, token_state, team_state, module0_done, out_top, leaderboard_html, accuracy_state, task_list_state, loader_col, main_app_col])

        # --- JAVASCRIPT HELPER FOR NAVIGATION ---
        def nav_js(target_id: str, message: str) -> str:
            """Generate JavaScript for smooth navigation with loading overlay."""
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
                  }}
                }}, 90);
              }} catch(e) {{ console.warn('nav-js error', e); }}
            }}
            """

        # 2. NAVIGATION WIRING
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]
            if i > 0:
                prev_col = module_ui_elements[i-1][0]
                prev_target_id = f"module-{i-1}"

                def make_prev_handler(p_col, c_col, target_id):
                    def navigate_prev():
                        # First yield: hide current, show nothing (transition state)
                        yield gr.update(visible=False), gr.update(visible=False)
                        # Second yield: show previous, hide current
                        yield gr.update(visible=True), gr.update(visible=False)
                    return navigate_prev
                
                prev_btn.click(
                    fn=make_prev_handler(prev_col, curr_col, prev_target_id),
                    outputs=[prev_col, curr_col],
                    js=nav_js(prev_target_id, "Loading..."),
                )

            if i < len(MODULES) - 1:
                next_col = module_ui_elements[i+1][0]
                next_target_id = f"module-{i+1}"

                def make_next_handler(c_col, n_col, next_idx):
                    def wrapper_next(user, tok, team, tasks):
                        data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                        dash_html = render_top_dashboard(data, next_idx)
                        return dash_html
                    return wrapper_next
                
                def make_nav_generator(c_col, n_col):
                    def navigate_next():
                        # First yield: hide current, show nothing (transition state)
                        yield gr.update(visible=False), gr.update(visible=False)
                        # Second yield: hide current, show next
                        yield gr.update(visible=False), gr.update(visible=True)
                    return navigate_next

                next_btn.click(
                    fn=make_next_handler(curr_col, next_col, i + 1),
                    inputs=[username_state, token_state, team_state, task_list_state],
                    outputs=[out_top],
                    js=nav_js(next_target_id, "Loading..."),
                ).then(
                    fn=make_nav_generator(curr_col, next_col),
                    outputs=[curr_col, next_col],
                )

    return demo

def launch_bias_detective_part2_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    """
    Launch the Bias Detective Part 2 app.

    Args:
        share: Whether to create a public link
        server_name: Server hostname
        server_port: Server port
        theme_primary_hue: Primary color hue
        **kwargs: Additional Gradio launch arguments
    """
    app = create_bias_detective_part2_app(theme_primary_hue=theme_primary_hue)
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
    launch_bias_detective_part2_app(share=False, debug=True, height=1000)

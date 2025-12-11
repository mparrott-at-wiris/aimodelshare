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
        "id": 1, "title": "The Audit Briefing",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ THE TRAP OF "AVERAGES"</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        The AI vendor claims that the <strong>model's predictions are 92% accurate</strong>. But remember: the data was
                        81% Male. If it works for men but fails for women, the "Average" still looks high.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 24px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">🔨 Break Down by Gender</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:12px;">"Overall Accuracy": 92% (Looks Great!)</div>
                            <div style="height:40px; background:#22c55e; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:1.1rem; font-weight:bold; color:white;">92% Accurate ✓</div>
                        </div>
                        <div style="margin: 30px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:12px;">But when broken down by gender...</div>
                            <div style="display:flex; gap:12px;">
                                <div style="flex:1;"><div style="font-size:0.85rem; margin-bottom:6px; font-weight:600;">Men</div><div style="height:40px; background:#22c55e; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:0.95rem; font-weight:bold; color:white;">99% ✓</div></div>
                                <div style="flex:1;"><div style="font-size:0.85rem; margin-bottom:6px; font-weight:600;">Women</div><div style="height:40px; background:#ef4444; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:0.95rem; font-weight:bold; color:white;">60% ✗</div></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 2, "title": "The Truth Serum",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⏳ THE POWER OF HINDSIGHT</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        How do we know the AI is wrong if we can't see the code? We look at what actually happened.
                        Investigative journalists at <strong>ProPublica</strong> gathered public records on 7,000 defendants
                        to determine the "Ground Truth."
                    </p>
                    <div class="ai-risk-container">
                        <div style="display:grid; gap:14px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;"><div style="font-weight:bold; color:#ef4444;">1. The Prediction (The Risk Score)</div><div style="font-size:0.95rem; margin-top:4px;">What the AI <em>thought</em> would happen (e.g., "High Risk").</div></div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e;"><div style="font-weight:bold; color:#22c55e;">2. The Ground Truth (The Answer Key)</div><div style="font-size:0.95rem; margin-top:4px;">What <em>actually</em> happened in the real world (e.g., "Did Not Re-offend").</div></div>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 3, "title": "Analysis: False Positives",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: PUNITIVE BIAS</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We analyzed the "False Alarms"—innocent people flagged as High Risk. Compare the error rates between groups below.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 24px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem; margin-bottom:20px;">📊 False Positive Rate (The "False Alarm")</h4>
                        <div style="display:flex; justify-content:center; align-items:flex-end; gap:40px; height:220px; border-bottom: 2px solid var(--border-color-primary); padding-bottom:10px;">
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:2rem; font-weight:800; color:#ef4444; margin-bottom:8px;">45%</div>
                                <div style="width:100%; height:180px; background:linear-gradient(to top, #ef4444, #f87171); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">African-American</div>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:2rem; font-weight:800; color:#3b82f6; margin-bottom:8px;">23%</div>
                                <div style="width:100%; height:92px; background:linear-gradient(to top, #3b82f6, #60a5fa); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">Caucasian</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 4, "title": "Analysis: False Negatives",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: THE "FREE PASS"</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Now we look at the dangerous people the AI mistakenly labeled "Low Risk."
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 24px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem; margin-bottom:20px;">📊 False Negative Rate (The "Missed Target")</h4>
                        <div style="display:flex; justify-content:center; align-items:flex-end; gap:40px; height:220px; border-bottom: 2px solid var(--border-color-primary); padding-bottom:10px;">
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:2rem; font-weight:800; color:#ef4444; margin-bottom:8px;">48%</div>
                                <div style="width:100%; height:192px; background:linear-gradient(to top, #ef4444, #f87171); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">Caucasian</div>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:2rem; font-weight:800; color:#3b82f6; margin-bottom:8px;">28%</div>
                                <div style="width:100%; height:112px; background:linear-gradient(to top, #3b82f6, #60a5fa); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">African-American</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 5, "title": "Analysis: Gender",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: SEVERITY BIAS</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Remember the 81% Male data? The AI doesn't understand female crime patterns. It panics.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 24px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem; margin-bottom:20px;">📊 High Risk Flagging for Minor Crimes</h4>
                        <div style="display:flex; justify-content:center; align-items:flex-end; gap:40px; height:220px; border-bottom: 2px solid var(--border-color-primary); padding-bottom:10px;">
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:1.1rem; font-weight:800; color:#3b82f6; margin-bottom:8px;">Baseline</div>
                                <div style="width:100%; height:100px; background:linear-gradient(to top, #3b82f6, #60a5fa); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">Men</div>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:2rem; font-weight:800; color:#ef4444; margin-bottom:8px;">+37%</div>
                                <div style="width:100%; height:137px; background:linear-gradient(to top, #ef4444, #f87171); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">Women</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 6, "title": "Analysis: Age",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: ESTIMATION ERROR</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        The AI thinks "Criminal = Young." It fails to recognize risk in older populations.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 24px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem; margin-bottom:20px;">📊 Missed Detection Rate (Older Defendants 50+)</h4>
                        <div style="display:flex; justify-content:center; align-items:flex-end; gap:40px; height:220px; border-bottom: 2px solid var(--border-color-primary); padding-bottom:10px;">
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:1.5rem; font-weight:800; color:#3b82f6; margin-bottom:8px;">20%</div>
                                <div style="width:100%; height:80px; background:linear-gradient(to top, #3b82f6, #60a5fa); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">Under 30</div>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:2rem; font-weight:800; color:#ef4444; margin-bottom:8px;">55%</div>
                                <div style="width:100%; height:200px; background:linear-gradient(to top, #ef4444, #f87171); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">Over 50</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 7, "title": "Analysis: Geography",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ THE "DOUBLE PROXY": RACE & CLASS</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We often hear: "Just delete the Race and Income columns." But the AI can still see
                        <strong>Where You Live</strong>.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 24px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem; margin-bottom:20px;">📊 False Positive Rate by Location</h4>
                        <div style="display:flex; justify-content:center; align-items:flex-end; gap:40px; height:220px; border-bottom: 2px solid var(--border-color-primary); padding-bottom:10px;">
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:1.5rem; font-weight:800; color:#3b82f6; margin-bottom:8px;">22%</div>
                                <div style="width:100%; height:88px; background:linear-gradient(to top, #3b82f6, #60a5fa); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">Rural/Suburban</div>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:center; width:140px;">
                                <div style="font-size:2rem; font-weight:800; color:#ef4444; margin-bottom:8px;">58%</div>
                                <div style="width:100%; height:232px; background:linear-gradient(to top, #ef4444, #f87171); border-radius:8px 8px 0 0; position:relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>
                                <div style="margin-top:12px; font-weight:700; font-size:0.95rem;">High Density</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 8, "title": "Audit Conclusion",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">📂 AUDIT REPORT: SUMMARY</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Analysis complete. The system passes "Average Accuracy" but fails fairness on every level.
                    </p>
                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">📋 Impact Matrix: Proven Harms</h4>
                        <div style="display:grid; gap:14px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;"><div style="font-weight:bold; color:#ef4444;">Race: Punitive Harm</div><div style="font-size:0.95rem; margin-top:4px;">2x False Alarms for African-Americans</div></div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;"><div style="font-weight:bold; color:#ef4444;">Gender: Severity Bias</div><div style="font-size:0.95rem; margin-top:4px;">37% harsher penalties for women on minor crimes</div></div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;"><div style="font-weight:bold; color:#ef4444;">Age: Estimation Error</div><div style="font-size:0.95rem; margin-top:4px;">Blind to older risk (55% miss rate)</div></div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;"><div style="font-weight:bold; color:#ef4444;">Geography: Proxy Bias</div><div style="font-size:0.95rem; margin-top:4px;">Redlining (58% false positive in urban areas)</div></div>
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 9, "title": "The Final Verdict",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚖️ THE FINAL JUDGMENT</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You have the full picture. The AI Vendor argues that the model is <strong>92% Accurate</strong>
                        and highly efficient. They want to deploy it immediately to clear the court backlog.
                    </p>
                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🎯 Your Decision</h4>
                        <p style="font-size:1.0rem; text-align:center; margin-bottom:20px; color:var(--body-text-color-subdued);">
                            Based on your investigation, what is your recommendation?
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 10, "title": "Mission Debrief",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🏆 MISSION ACCOMPLISHED</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You successfully exposed the "Invisible Enemy." You proved that "92% Accuracy" was a mask
                        for <strong style="color:#ef4444;">Punitive Bias</strong> and
                        <strong style="color:#ef4444;">Proxy Discrimination</strong>. But a Diagnosis is not a Cure.
                    </p>
                    <div style="margin-top:28px; padding:24px; background:linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <h3 style="margin-top:0; text-align:center; color:var(--color-accent);">🎖️ PROMOTION: FAIRNESS ENGINEER</h3>
                        <p style="font-size:1.05rem; text-align:center; margin-bottom:16px;">
                            We don't just need someone to <strong>find</strong> the problems anymore—we need someone to <strong>fix</strong> them.
                        </p>
                    </div>
                </div>
            </div>
        """
    }
]

# --- 6. INTERACTIVE CONFIG ---
QUIZ_CONFIG = {
    1: {"t": "t11", "q": "Why is '92% Accuracy' a dangerous metric?", "o": ["A) It hides failure for vulnerable groups", "B) 92% is too low", "C) It ignores speed"], "a": "A) It hides failure for vulnerable groups", "success": "Deception Exposed. You rejected the aggregate statistic."},
    2: {"t": "t12", "q": "How did ProPublica determine the 'likely harm'?", "o": ["A) Interviewed judges", "B) Compared predictions vs. 2-year re-offense records", "C) Ran simulations"], "a": "B) Compared predictions vs. 2-year re-offense records", "success": "Ground Truth Established."},
    3: {"t": "t13", "q": "False Alarms: 45% (Black) vs 23% (White). What does this reveal?", "o": ["A) Equal accuracy", "B) Leniency", "C) 2x more likely to falsely accuse Black defendants"], "a": "C) 2x more likely to falsely accuse Black defendants", "success": "Harm Verified: Punitive Bias."},
    4: {"t": "t14", "q": "False Negatives: 48% (White) vs 28% (Black). What kind of bias is this?", "o": ["A) Omission Bias (Free Pass)", "B) Selection Bias", "C) Confirmation Bias"], "a": "A) Omission Bias (Free Pass)", "success": "Harm Verified: Omission Bias."},
    5: {"t": "t15", "q": "The model flags women as 'High Risk' for minor misdemeanors. Why?", "o": ["A) Women commit more crimes", "B) Severity Bias (Male standards applied to women)", "C) Programmed caution"], "a": "B) Severity Bias (Male standards applied to women)", "success": "Harm Verified: Severity Bias."},
    6: {"t": "t16", "q": "The AI misses 55% of re-offending older defendants. Consequence?", "o": ["A) Unfair punishment", "B) Slower processing", "C) Public Endangerment"], "a": "C) Public Endangerment", "success": "Harm Verified: Public Endangerment."},
    7: {"t": "t17", "q": "Race/Income deleted, but map shows bias. Why?", "o": ["A) Double Proxy (Zip Code targets Race & Class)", "B) Random guessing", "C) Sentient bias"], "a": "A) Double Proxy (Zip Code targets Race & Class)", "success": "Harm Verified: Compound Bias."},
    8: {"t": "t18", "q": "Is this a minor glitch?", "o": ["A) Yes, coding error", "B) User error", "C) No, Systemic Failure"], "a": "C) No, Systemic Failure", "success": "Audit Complete. Systemic Failure Confirmed."},
    9: {"t": "t19", "q": "Final Verdict?", "o": ["A) Authorize Deployment", "B) Reject & Overhaul", "C) Monitor Only"], "a": "B) Reject & Overhaul", "success": "Verdict Logged: REJECTED."}
}

# --- 7. RENDERERS ---
def generate_success_message(prev, curr, specific_text):
    old_score = float(prev.get('score', 0) or 0) if prev else 0.0
    new_score = float(curr.get('score', 0) or 0)
    diff_score = new_score - old_score # Correct variable name
    old_rank = prev.get('rank', '-') if prev else '-'
    new_rank = curr.get('rank', '-')

    rank_html = f"<div style='color:gray;'>Rank: #{new_rank}</div>"
    if isinstance(old_rank, int) and isinstance(new_rank, int):
        if new_rank < old_rank: rank_html = f"<div style='color:#22c55e; font-weight:bold;'>⬆️ Rank Improved: #{old_rank} → #{new_rank}</div>"
        elif new_rank == old_rank:
            if new_rank == 1: rank_html = f"<div style='color:#60a5fa; font-weight:bold;'>🏆 Rank: #1 (Leader)</div>"
            else: rank_html = f"<div style='color:gray;'>Rank: #{new_rank} (Steady)</div>"

    return f"""
    <div class='profile-card risk-low' style='border-left-color:#22c55e; background:var(--block-background-fill); padding:16px;'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <h2 style='margin:0; color:#22c55e; font-size:1.2rem;'>✅ Analysis Confirmed</h2>
            <div style='font-size:1.5rem;'>🧭 +{diff_score:.3f}</div>
        </div>
        <hr style='margin:12px 0; border:0; border-top:1px solid var(--border-color-primary);'>
        <p style='margin-bottom:12px; font-size:1rem;'>{specific_text}</p>
        <div style='background:var(--background-fill-secondary); padding:10px; border-radius:6px; font-size:0.9rem;'>
            <div style='display:flex; justify-content:space-between; margin-bottom:4px;'>
                <span>Moral Compass Score:</span>
                <strong>{old_score:.3f} → {new_score:.3f}</strong>
            </div>
            {rank_html}
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
.summary-box { background: var(--block-background-fill); padding: 20px; border-radius: 12px; border: 1px solid var(--border-color-primary); margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.summary-box-inner { display: flex; align-items: center; justify-content: space-between; gap: 30px; }
.summary-metrics { display: flex; gap: 30px; }
.summary-progress { width: 500px; }
.scenario-box { padding: 24px; border-radius: 12px; background: var(--block-background-fill); border: 1px solid var(--border-color-primary); margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); }
.slide-title { margin-top: 0; font-size: 1.8rem; }
.slide-body { font-size: 1.15rem; line-height: 1.6; }
.hint-box { padding: 12px; border-radius: 8px; background: var(--block-background-fill); border: 1px solid var(--border-color-primary); margin-top: 10px; font-size: 0.95rem; }
.profile-card { padding: 20px; border-radius: 12px; border-left: 6px solid #22c55e; background: var(--block-background-fill); margin-top: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.score-text-primary { font-size: 2rem; font-weight: 800; color: var(--color-accent); }
.score-text-team { font-size: 2rem; font-weight: 800; color: #60a5fa; }
.score-text-global { font-size: 2rem; font-weight: 800; }
.label-text { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: gray; }
.progress-bar-bg { width: 100%; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; margin-top: 6px; }
.progress-bar-fill { height: 100%; background: var(--color-accent); }
.leaderboard-card input[type="radio"] { display: none; }
.lb-tab-label { display: inline-block; padding: 6px 14px; margin-right: 8px; border-radius: 20px; cursor: pointer; border: 1px solid var(--border-color-primary); font-weight: 600; font-size: 0.9rem; }
#lb-tab-team:checked + label, #lb-tab-user:checked + label { background: var(--color-accent); color: white; border-color: var(--color-accent); }
.lb-panel { display: none; margin-top: 10px; }
#lb-tab-team:checked ~ .lb-tab-panels .panel-team { display: block; }
#lb-tab-user:checked ~ .lb-tab-panels .panel-user { display: block; }
.table-container { height: 300px; overflow-y: auto; border: 1px solid var(--border-color-primary); border-radius: 8px; }
.leaderboard-table { width: 100%; border-collapse: collapse; }
.leaderboard-table th { position: sticky; top: 0; background: var(--background-fill-secondary); padding: 10px; text-align: left; border-bottom: 2px solid var(--border-color-primary); }
.leaderboard-table td { padding: 10px; border-bottom: 1px solid var(--border-color-primary); }
.row-highlight-me, .row-highlight-team { background: rgba(96, 165, 250, 0.15); font-weight: 600; }
.ai-risk-container { margin-top: 16px; padding: 16px; background: var(--body-background-fill); border-radius: 8px; border: 1px solid var(--border-color-primary); }
"""
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

        # 2. NAVIGATION WIRING
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]
            if i > 0:
                prev_col = module_ui_elements[i-1][0]
                prev_btn.click(lambda: (gr.update(visible=True), gr.update(visible=False)), outputs=[prev_col, curr_col])

            if i < len(MODULES) - 1:
                next_col = module_ui_elements[i+1][0]
                def update_dash_next(user, tok, team, tasks, next_idx=i+1):
                    data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                    return render_top_dashboard(data, next_idx)

                next_btn.click(
                    fn=update_dash_next,
                    inputs=[username_state, token_state, team_state, task_list_state],
                    outputs=[out_top]
                ).then(
                    fn=lambda: (gr.update(visible=False), gr.update(visible=True)),
                    outputs=[curr_col, next_col]
                )

    return demo

def launch_bias_detective_part2_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    #server_port: int = 8080,
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
        #server_port=server_port,
        **kwargs
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    launch_bias_detective_part2_app(share=False, debug=True, height=1000)

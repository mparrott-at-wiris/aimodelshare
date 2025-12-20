import os
import sys
import subprocess
import time
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"
TOTAL_COURSE_TASKS = 20 # Score calculated against full course
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

# --- 4. MODULE DEFINITIONS (APP 1: 0-10) ---
MODULES = [
    # --- MODULE 0: THE HOOK (Mission Dossier) ---
    {
        "id": 0,
        "title": "Mission Dossier",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">
                    <h2 class="slide-title" style="margin-bottom:25px; text-align:center; font-size: 2.2rem;">🕵️ MISSION DOSSIER</h2>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:25px; margin-bottom:30px; align-items:stretch;">
                        <div style="background:var(--background-fill-secondary); padding:20px; border-radius:12px; border:1px solid var(--border-color-primary);">
                            <div style="margin-bottom:15px;">
                                <div style="font-size:0.9rem; font-weight:800; color:var(--body-text-color-subdued); letter-spacing:1px;">YOUR ROLE</div>
                                <div style="font-size:1.3rem; font-weight:700; color:var(--color-accent);">Lead Bias Detective</div>
                            </div>
                            <div>
                                <div style="font-size:0.9rem; font-weight:800; color:var(--body-text-color-subdued); letter-spacing:1px;">YOUR TARGET</div>
                                <div style="font-size:1.3rem; font-weight:700;">"Compas" AI Algorithm</div>
                                <div style="font-size:1.0rem; margin-top:5px; opacity:0.8;">Used by judges to decide bail.</div>
                            </div>
                        </div>
                        <div style="background:rgba(239,68,68,0.08); padding:20px; border-radius:12px; border:2px solid #fca5a5; display:flex; flex-direction:column; justify-content:center;">
                            <div style="font-size:0.9rem; font-weight:800; color:#b91c1c; letter-spacing:1px;">🚨 THE THREAT</div>
                            <div style="font-size:1.15rem; font-weight:600; line-height:1.4; color:#7f1d1d;">
                                The model is 92% accurate, but we suspect a <strong>hidden systematic bias</strong>.
                                <br><br>
                                Your goal: Expose flaws before this model is deployed nationwide.
                            </div>
                        </div>
                    </div>

                    <hr style="opacity:0.2; margin:25px 0;">

                    <p style="text-align:center; font-weight:800; color:var(--body-text-color-subdued); margin-bottom:20px; font-size:1.0rem; letter-spacing:1px;">
                        👇 CLICK CARDS TO UNLOCK INTEL
                    </p>

                    <div style="display:grid; gap:20px;">
                        <details class="evidence-card" style="background:white; border:2px solid #e5e7eb; border-left: 6px solid #ef4444; padding:0; border-radius:8px; overflow:hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <summary style="padding:20px; font-weight:800; font-size:1.2rem; color:#1f2937; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; background:rgba(254,242,242,0.5);">
                                <div style="display:flex; align-items:center; gap:15px;">
                                    <span style="font-size:1.8rem;">⚠️</span>
                                    <span>RISK: The "Ripple Effect"</span>
                                </div>
                                <span style="font-size:0.9rem; color:#ef4444; text-transform:uppercase;">Click to Simulate</span>
                            </summary>
                            <div style="padding:25px; border-top:1px solid #e5e7eb;">
                                <div style="display:flex; gap:30px; align-items:center;">
                                    <div style="font-size:3.5rem; line-height:1;">🌊</div>
                                    <div>
                                        <div style="font-weight:900; font-size:2.0rem; color:#ef4444; line-height:1;">15,000+</div>
                                        <div style="font-weight:700; font-size:1.1rem; color:#374151; margin-bottom:5px;">Cases Processed Per Year</div>
                                        <div style="font-size:1.1rem; color:#4b5563; line-height:1.5;">
                                            A human makes a mistake once. This AI will repeat the same bias <strong>15,000+ times a year</strong>.
                                            <br>If we don't fix it, we automate unfairness at a massive scale.
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </details>

                        <details class="evidence-card" style="background:white; border:2px solid #e5e7eb; border-left: 6px solid #22c55e; padding:0; border-radius:8px; overflow:hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <summary style="padding:20px; font-weight:800; font-size:1.2rem; color:#1f2937; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; background:rgba(240,253,244,0.5);">
                                <div style="display:flex; align-items:center; gap:15px;">
                                    <span style="font-size:1.8rem;">🧭</span>
                                    <span>OBJECTIVE: How to Win</span>
                                </div>
                                <span style="font-size:0.9rem; color:#15803d; text-transform:uppercase;">Click to Calculate</span>
                            </summary>
                            <div style="padding:25px; border-top:1px solid #e5e7eb;">
                                <div style="text-align:center; margin-bottom:20px;">
                                    <div style="font-size:1.4rem; font-weight:800; background:#f3f4f6; padding:15px; border-radius:10px; display:inline-block;">
                                        <span style="color:#6366f1;">[ Accuracy ]</span>
                                        <span style="color:#9ca3af; margin:0 10px;">×</span>
                                        <span style="color:#22c55e;">[ Ethical Progress % ]</span>
                                        <span style="color:#9ca3af; margin:0 10px;">=</span>
                                        SCORE
                                    </div>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                                    <div style="padding:15px; background:#fef2f2; border:2px solid #fecaca; border-radius:10px; text-align:center;">
                                        <div style="font-weight:700; color:#b91c1c; margin-bottom:5px;">Scenario A: Ignored Ethics</div>
                                        <div style="font-size:0.95rem;">High Accuracy (95%)</div>
                                        <div style="font-size:0.95rem;">0% Ethics</div>
                                        <div style="margin-top:10px; border-top:1px solid #fecaca; padding-top:5px;">
                                            <div style="font-size:0.8rem; text-transform:uppercase; color:#7f1d1d;">Final Score</div>
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444;">0</div>
                                        </div>
                                    </div>
                                    <div style="padding:15px; background:#f0fdf4; border:2px solid #bbf7d0; border-radius:10px; text-align:center;">
                                        <div style="font-weight:700; color:#15803d; margin-bottom:5px;">Scenario B: True Detective</div>
                                        <div style="font-size:0.95rem;">Good Accuracy (92%)</div>
                                        <div style="font-size:0.95rem;">100% Ethics</div>
                                        <div style="margin-top:10px; border-top:1px solid #bbf7d0; padding-top:5px;">
                                            <div style="font-size:0.8rem; text-transform:uppercase; color:#14532d;">Final Score</div>
                                            <div style="font-size:2.5rem; font-weight:900; color:#22c55e;">92</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </details>
                    </div>

                   <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 MISSION START
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Answer the question below to receive your first <strong>Moral Compass Score boost</strong>.
                            <br>Then click <strong>Next</strong> to start the investigation.
                        </p>
                    </div> 
                </div>
            </div>
        """,
    },

    # --- MODULE 1: THE MAP (Mission Roadmap) ---
{
    "id": 1,
    "title": "Mission Roadmap",
    "html": """
        <div class="scenario-box">
            <div class="slide-body">

                <h2 class="slide-title" style="text-align:center; margin-bottom:15px;">🗺️ MISSION ROADMAP</h2>

                <p style="font-size:1.1rem; max-width:800px; margin:0 auto 25px auto; text-align:center;">
                    <strong>Your mission is clear:</strong> Uncover the bias hiding inside the 
                    AI system before it hurts real people. If you cannot find bias, we cannot fix it.
                </p>

                <div class="ai-risk-container" style="background:white; border:none; padding:0;">

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">

                        <div style="border: 3px solid #3b82f6; background: #eff6ff; border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 12px rgba(59,130,246,0.25);">
                            <div style="position:absolute; top:-15px; left:15px; background:#3b82f6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">STEP 1: RULES</div>
                            <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">📜</div>
                            <div style="font-weight:800; font-size:1.2rem; color:#1e3a8a; margin-bottom:5px;">Establish the Rules</div>
                            <div style="font-size:1.0rem; color:#1e40af; font-weight:500; line-height:1.4;">
                                Define the ethical standard: <strong>Justice & Equity</strong>. What specifically counts as bias in this investigation?
                            </div>
                        </div>

                        <div style="border: 3px solid #14b8a6; background: #f0fdfa; border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(20, 184, 166, 0.15);">
                            <div style="position:absolute; top:-15px; left:15px; background:#14b8a6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">STEP 2: DATA EVIDENCE</div>
                            <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">🔍</div>
                            <div style="font-weight:800; font-size:1.2rem; color:#134e4a; margin-bottom:5px;">Input Data Forensics</div>
                            <div style="font-size:1.0rem; color:#0f766e; font-weight:500; line-height:1.4;">
                                Scan the <strong>Input Data</strong> for historical injustice, representation gaps, and exclusion bias.
                            </div>
                        </div>

                        <div style="border: 3px solid #8b5cf6; background: #f5f3ff; border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(139, 92, 246, 0.15);">
                            <div style="position:absolute; top:-15px; left:15px; background:#8b5cf6; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">STEP 3: TEST ERROR</div>
                            <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">🎯</div>
                            <div style="font-weight:800; font-size:1.2rem; color:#4c1d95; margin-bottom:5px;">Output Error Testing</div>
                            <div style="font-size:1.0rem; color:#6d28d9; font-weight:500; line-height:1.4;">
                                Test the Model's predictions. Prove that mistakes (False Alarms) are <strong>unequal</strong> across groups.
                            </div>
                        </div>

                        <div style="border: 3px solid #f97316; background: #fff7ed; border-radius: 12px; padding: 20px; position: relative; box-shadow: 0 4px 10px rgba(249, 115, 22, 0.15);">
                            <div style="position:absolute; top:-15px; left:15px; background:#f97316; color:white; padding:4px 16px; border-radius:20px; font-weight:800; font-size:0.9rem; letter-spacing:1px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">STEP 4: REPORT IMPACT</div>
                            <div style="font-size:3rem; margin-top:10px; margin-bottom:5px;">⚖️</div>
                            <div style="font-weight:800; font-size:1.2rem; color:#7c2d12; margin-bottom:5px;">The Final Report</div>
                            <div style="font-size:1.0rem; color:#c2410c; font-weight:500; line-height:1.4;">
                                Diagnose systematic harm and issue your final recommendation to the court: <strong>Deploy AI System or Pause to Repair.</strong>
                            </div>
                        </div>

                    </div>
                </div>


                   <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 CONTINUE MISSION
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Answer the question below to receive your next <strong>Moral Compass Score boost</strong>.
                            <br>Then click <strong>Next</strong> to continue the investigation.
                        </p>
                    </div>
            </div>
        </div>
    """,
},

    # --- MODULE 2: RULES (Interactive) ---
    {
        "id": 2,
        "title": "Step 1: Learn the Rules",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step active">1. RULES</div>
                    <div class="tracker-step">2. EVIDENCE</div>
                    <div class="tracker-step">3. ERROR</div>
                    <div class="tracker-step">4. VERDICT</div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h2 class="slide-title" style="margin:0;">STEP 1: LEARN THE RULES</h2>
                    <div style="font-size:2rem;">⚖️</div>
                </div>

                <div class="slide-body">

                    <div style="background:#eff6ff; border-left:4px solid #3b82f6; padding:15px; margin-bottom:20px; border-radius:4px;">
                        <p style="margin:0; font-size:1.05rem; line-height:1.5;">
                            <strong>Justice & Equity: Your Primary Rule.</strong><br>
                            Ethics isn't abstract here—it’s our field guide for action. We rely on expert advice from the Catalan Observatory for Ethics in AI <strong>OEIAC (UdG)</strong> to ensure AI systems are fair.
                            While they have defined 7 core principles of safe AI, our intel suggests this specific case involves a violation of <strong>Justice and Equity</strong>.
                        </p>
                    </div>

                <div style="text-align:center; margin-bottom:20px;">
                <p style="font-size:1rem; font-weight:700; color:#2563eb; background:#eff6ff; display:inline-block; padding:6px 16px; border-radius:20px; border:1px solid #bfdbfe;">
                    👇 Click on each card below to reveal what counts as bias
                </p>
               </div>

                    <p style="text-align:center; font-weight:700; color:var(--body-text-color-subdued); margin-bottom:10px; font-size:0.9rem; letter-spacing:1px;">
                        🧩 JUSTICE & EQUITY: WHAT COUNTS AS BIAS?
                    </p>

                    <div class="ai-risk-container" style="background:#f8fafc; border:none; padding:0;">
                        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:15px;">

                            <details style="cursor:pointer; background:white; padding:15px; border-radius:10px; border:1px solid #bfdbfe; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#2563eb; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">📊</div>
                                    Representation Bias
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:#334155; border-top:1px solid #e2e8f0; padding-top:10px; line-height:1.4;">
                                    <strong>Definition:</strong> Compares the dataset distribution to the actual real-world distribution.
                                    <br><br>
                                    If one group appears far less (e.g., only 10% of cases are Group A, but they are 71% of the population) or far more than reality, the AI likely learns biased patterns.
                                </div>
                            </details>

                            <details style="cursor:pointer; background:white; padding:15px; border-radius:10px; border:1px solid #fca5a5; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#dc2626; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">🎯</div>
                                    Error Gaps
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:#334155; border-top:1px solid #e2e8f0; padding-top:10px; line-height:1.4;">
                                    <strong>Definition:</strong> Checks for AI prediction mistakes by subgroup (e.g., False Positive Rate for Group A vs. Group B).
                                    <br><br>
                                    Higher error for a group indicates risk for unfair treatment, showing the model may be less trustworthy for that specific group.
                                </div>
                            </details>

                            <details style="cursor:pointer; background:white; padding:15px; border-radius:10px; border:1px solid #bbf7d0; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                                <summary style="list-style:none; font-weight:800; color:#16a34a; text-align:center; font-size:1.0rem;">
                                    <div style="font-size:2rem; margin-bottom:5px;">⛓️</div>
                                    Outcome Disparities
                                </summary>
                                <div style="margin-top:12px; font-size:0.95rem; color:#334155; border-top:1px solid #e2e8f0; padding-top:10px; line-height:1.4;">
                                    <strong>Definition:</strong> Looks for worse real-world results after AI predictions (e.g., harsher sentencing).
                                    <br><br>
                                    Bias isn’t just numbers—it changes real-world outcomes for people.
                                </div>
                            </details>
                        </div>
                    </div>

                    <hr style="opacity:0.2; margin:25px 0;">

                    <details class="hint-box" style="margin-top:0; cursor:pointer;">
                        <summary style="font-weight:700; color:#64748b;">🧭 Reference: Other AI Ethics Principles (OEIAC)</summary>
                        <div style="margin-top:15px; font-size:0.9rem; display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                            <div>
                                <strong>Transparency &amp; Explainability</strong><br>Ensure the AI's reasoning and final judgment are clear so decisions can be inspected and people can appeal.<br>
                                <strong>Security &amp; Non-maleficence</strong><br>Minimize harmful mistakes and always have a solid plan for system failure.<br>
                                <strong>Responsibility &amp; Accountability</strong><br>Assign clear owners for the AI and maintain a detailed record of decisions (audit trail).
                            </div>
                            <div>
                                <strong>Autonomy</strong><br>Provide individuals with clear appeals processes and alternatives to the AI's decision.<br>
                                <strong>Privacy</strong><br>Use only necessary data and always justify any need to use sensitive attributes.<br>
                                <strong>Sustainability</strong><br>Avoid long-term harm to society or the environment (e.g., massive energy use or market destabilization).
                            </div>
                        </div>
                    </details>


                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 RULES BRIEFING COMPLETE: CONTINUE MISSION
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Answer the question below to receive your next <strong>Moral Compass Score boost</strong>.
                            <br>Then click <strong>Next</strong> to continue your mission.
                        </p>
                    </div>
                </div>
            </div>
        """
    },

{
    "id": 3,
    "title": "Step 2: Pattern Recognition",
    "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. RULES</div>
                    <div class="tracker-step active">2. EVIDENCE</div>
                    <div class="tracker-step">3. ERROR</div>
                    <div class="tracker-step">4. VERDICT</div>
                </div>

        <div class="slide-body">
            <h2 class="slide-title" style="margin:0;">STEP 2: SEARCH FOR THE EVIDENCE</h2>

            <div style="text-align:center; margin-bottom:20px;">

                <h2 class="slide-title" style="margin-top:10px; color:#0c4a6e;">The Hunt for Biased Demographic Patterns</h2>
                <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:#334155;">
                    An AI is only as fair as the data it learns from. If the input data distorts reality, the AI will likely distort justice.
                    <br>The first step is to hunt for patterns that reveal <strong>Representation Bias.</strong>  To find representation bias we must inspect the <strong>Demographics.</strong>.
                </p>
            </div>

            <div style="background:white; border:2px solid #e2e8f0; border-radius:16px; padding:25px; margin-bottom:20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid #f1f5f9; padding-bottom:10px;">
                    <div style="font-size:1.5rem;">🚩</div>
                    <div>
                        <strong style="color:#0ea5e9; font-size:1.1rem; text-transform:uppercase; letter-spacing:1px;">PATTERN: "THE DISTORTED MIRROR"</strong>
                        <div style="font-size:0.9rem; color:#64748b;">(Representation Bias in Protected Groups)</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
                    
                    <div>
                        <p style="font-size:1rem; color:#334155; line-height:1.6;">
                            <strong>The Concept:</strong> Ideally, a dataset should look like a "Mirror" of the real population. 
                            If a group makes up 50% of the population, they should generally make up ~50% of the data.
                        </p>
                        <p style="font-size:1rem; color:#334155; line-height:1.6;">
                            <strong>The Red Flag:</strong> Look for <strong>Drastic Imbalances</strong> in Protected Characteristics (Race, Gender, Age).
                        </p>
                        <ul style="font-size:0.95rem; color:#475569; margin-top:10px; padding-left:20px; line-height:1.5;">
                            <li><strong>Over-Representation:</strong> One group has a "Giant Bar" (e.g., 80% of arrest records are Men). The AI learns to target this group.</li>
                            <li><strong>Under-Representation:</strong> One group is missing or tiny. The AI fails to learn accurate patterns for them.</li>
                        </ul>
                    </div>

                    <div style="background:#f8fafc; padding:20px; border-radius:12px; border:1px solid #e2e8f0; display:flex; flex-direction:column; justify-content:center;">
                        
                        <div style="margin-bottom:20px;">
                            <div style="font-size:0.85rem; font-weight:700; color:#64748b; margin-bottom:5px;">REALITY (The Population)</div>
                            <div style="display:flex; width:100%; height:24px; border-radius:4px; overflow:hidden;">
                                <div style="width:33%; background:#94a3b8; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Group A</div>
                                <div style="width:34%; background:#64748b; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Group B</div>
                                <div style="width:33%; background:#475569; display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem;">Group C</div>
                            </div>
                        </div>

                        <div>
                            <div style="font-size:0.85rem; font-weight:700; color:#0c4a6e; margin-bottom:5px;">THE TRAINING DATA (The Distorted Mirror)</div>
                            <div style="display:flex; width:100%; height:24px; border-radius:4px; overflow:hidden;">
                                <div style="width:80%; background:linear-gradient(90deg, #f43f5e, #be123c); display:flex; align-items:center; justify-content:center; color:white; font-size:0.75rem; font-weight:700;">GROUP A (80%)</div>
                                <div style="width:10%; background:#e2e8f0;"></div>
                                <div style="width:10%; background:#cbd5e1;"></div>
                            </div>
                            <div style="font-size:0.8rem; color:#be123c; margin-top:5px; font-weight:600;">
                                ⚠️ Alert: Group A is massively over-represented.
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <div style="margin-bottom: 25px; padding: 0 10px;">
                <p style="font-size:1.1rem; color:#1e293b; line-height:1.5;">
                    <strong>🕵️ Your Next Step:</strong> You must enter the Data Forensics Lab and check the data for specific demographic categories. If the patterns look like the "Distorted Mirror" above, the data is likely unsafe.
                </p>
            </div>

            <details style="margin-bottom:30px; cursor:pointer; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px;">
                <summary style="font-weight:700; color:#64748b; font-size:0.95rem;">🧭 Reference: How do AI datasets become biased?</summary>
                <div style="margin-top:12px; font-size:0.95rem; color:#475569; line-height:1.5; padding:0 5px;">
                    <p style="margin-bottom:10px;"><strong>Example:</strong> When a dataset is built from <strong>historical arrest records</strong>.</p>
                    <p>Systemic over-policing in specific neighborhoods could distort the counts in the dataset for attributes like <strong>Race or Income</strong>.
                     The AI then learns this distortion as "truth."</p>
                </div>
            </details>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 EVIDENCE PATTERNS ESTABLISHED: CONTINUE MISSION
                </p>
                <p style="font-size:1.05rem; margin:0;">
                    Answer the question below to receive your next <strong>Moral Compass Score boost</strong>.
                    <br>Then click <strong>Next</strong> to begin <strong>analyzing evidence in the Data Forensics Lab.</strong>
                </p>
            </div>
        </div>
    </div>
    """
},

    # --- MODULE 4: DATA FORENSICS LAB (The Action) ---
    {
        "id": 4, # Re-indexed from 3
        "title": "Step 2: Data Forensics Lab",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. RULES</div>
                    <div class="tracker-step active">2. EVIDENCE</div>
                    <div class="tracker-step">3. ERROR</div>
                    <div class="tracker-step">4. VERDICT</div>
                </div>

           <h2 class="slide-title" style="margin:0;">STEP 2: SEARCH FOR THE EVIDENCE</h2>

            <div style="text-align:center; margin-bottom:20px;">

                <h2 class="slide-title" style="margin-top:10px; color:#0c4a6e;">The Data Forensics Lab</h2>               
                <div class="slide-body">

                    <p style="text-align:center; max-width:700px; margin:0 auto 15px auto; font-size:1.1rem;">
                        Search for evidence of Representation Bias.
                        Compare the **Real World** population against the AI's **Input Data**.
                        <br>Does the AI "see" the world as it truly is or do you see evidence of distorted representation?
                    </p>

                <div style="text-align:center; margin-bottom:20px;">
                <p style="font-size:1rem; font-weight:700; color:#2563eb; background:#eff6ff; display:inline-block; padding:6px 16px; border-radius:20px; border:1px solid #bfdbfe;">
                    👇 Click to scan each demographic category to reveal the evidence
                </p>
               </div>

                    <div style="margin-top:20px;">
                        <input type="radio" id="scan-race" name="scan-tabs" class="scan-radio" checked>
                        <input type="radio" id="scan-gender" name="scan-tabs" class="scan-radio">
                        <input type="radio" id="scan-age" name="scan-tabs" class="scan-radio">

                        <div class="forensic-tabs" style="display:flex; justify-content:center; gap:10px; margin-bottom:0;">
                            <label for="scan-race" class="tab-label-styled" style="flex:1; text-align:center;">SCAN: RACE</label>
                            <label for="scan-gender" class="tab-label-styled" style="flex:1; text-align:center;">SCAN: GENDER</label>
                            <label for="scan-age" class="tab-label-styled" style="flex:1; text-align:center;">SCAN: AGE</label>
                        </div>

                        <div class="scan-content" style="border-top: 3px solid var(--color-accent);">

                            <div class="scan-pane pane-race">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">SCANNING: RACIAL DISTRIBUTION</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ ANOMALY DETECTED</span>
                                </div>

                                <div style="display:grid; grid-template-columns: 1fr 0.2fr 1fr; align-items:center; gap:10px;">

                                    <div style="text-align:center; background:white; padding:15px; border-radius:8px; border:1px solid #bfdbfe;">
                                        <div style="font-size:0.9rem; font-weight:700; color:#64748b; letter-spacing:1px;">REAL WORLD</div>
                                        <div style="font-size:2rem; font-weight:900; color:#3b82f6; margin:5px 0;">28%</div>
                                        <div style="font-size:0.9rem; margin-bottom:10px;">African-American Population</div>
                                        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; max-width:80px; margin:0 auto;">
                                            <span style="color:#3b82f6;">●</span><span style="color:#3b82f6;">●</span><span style="color:#3b82f6;">●</span><span style="color:#e2e8f0;">●</span>
                                            <span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span>
                                            <span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span>
                                        </div>
                                    </div>

                                    <div style="text-align:center; font-size:1.5rem; color:#94a3b8;">👉</div>

                                    <div style="text-align:center; background:#fef2f2; padding:15px; border-radius:8px; border:2px solid #ef4444;">
                                        <div style="font-size:0.9rem; font-weight:700; color:#b91c1c; letter-spacing:1px;">INPUT DATA</div>
                                        <div style="font-size:2rem; font-weight:900; color:#ef4444; margin:5px 0;">51%</div>
                                        <div style="font-size:0.9rem; margin-bottom:10px;">African-American Records</div>
                                        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; max-width:80px; margin:0 auto;">
                                            <span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span>
                                            <span style="color:#ef4444;">●</span><span style="color:#ef4444;">●</span><span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span>
                                            <span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span><span style="color:#e2e8f0;">●</span>
                                        </div>
                                    </div>

                                </div>

                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:white;">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDENCE LOGGED: Race Representation Bias</div>
                                    <div style="font-size:0.95rem; margin-top:5px;">
                                        The AI is **over-exposed** to this group (51% vs 28%). It may learn to associate "High Risk" with this demographic simply because it sees them more often in arrest records.
                                    </div>
                                </div>
                            </div>

                            <div class="scan-pane pane-gender">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">SCANNING: GENDER BALANCE</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ DATA GAP FOUND</span>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                                    <div style="text-align:center; padding:20px; background:white; border-radius:8px; border:1px solid #e2e8f0;">
                                        <div style="font-size:4rem; line-height:1;">♂️</div>
                                        <div style="font-size:2.2rem; font-weight:900; color:#3b82f6;">81%</div>
                                        <div style="font-weight:700; color:#64748b;">MALE</div>
                                        <div style="font-size:0.85rem; color:#16a34a; font-weight:600; margin-top:5px;">✅ Well Represented</div>
                                    </div>
                                    <div style="text-align:center; padding:20px; background:#fff1f2; border-radius:8px; border:2px solid #fda4af;">
                                        <div style="font-size:4rem; line-height:1; opacity:0.5;">♀️</div>
                                        <div style="font-size:2.2rem; font-weight:900; color:#e11d48;">19%</div>
                                        <div style="font-weight:700; color:#9f1239;">FEMALE</div>
                                        <div style="font-size:0.85rem; color:#e11d48; font-weight:600; margin-top:5px;">⚠️ Insufficient Data</div>
                                    </div>
                                </div>
                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:white;">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDENCE LOGGED: Gender Representation Bias</div>
                                    <div style="font-size:0.95rem; margin-top:5px;">
                                        Women are a "minority class" in this dataset even though they typically make up 50% of the true population. The model will likely struggle to learn accurate patterns for them, leading to **higher error rates** for female defendants.
                                    </div>
                                </div>
                            </div>

                            <div class="scan-pane pane-age">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:#1e293b; color:white; padding:10px 15px; border-radius:6px;">
                                    <span style="font-family:monospace; letter-spacing:1px;">SCANNING: AGE DISTRIBUTION</span>
                                    <span style="color:#ef4444; font-weight:bold; animation: blink 1.5s infinite;">⚠️ DISTRIBUTION SPIKE</span>
                                </div>

                                <div style="padding:20px; background:white; border-radius:8px; border:1px solid #e2e8f0; height:200px; display:flex; align-items:flex-end; justify-content:space-around;">

                                    <div style="width:20%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:#64748b; margin-bottom:5px;">Low</div>
                                        <div style="height:60px; background:#cbd5e1; border-radius:4px 4px 0 0; width:100%;"></div>
                                        <div style="margin-top:10px; font-size:0.85rem; font-weight:700; color:#334155;">Younger (<25)</div>
                                    </div>

                                    <div style="width:35%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:#ef4444; margin-bottom:5px;">HIGH</div>
                                        <div style="height:120px; background:#ef4444; border-radius:4px 4px 0 0; width:100%; box-shadow:0 4px 10px rgba(239,68,68,0.3);"></div>
                                        <div style="margin-top:10px; font-size:0.9rem; font-weight:800; color:#b91c1c;">25-45 (BUBBLE)</div>
                                    </div>

                                    <div style="width:20%; text-align:center; display:flex; flex-direction:column; justify-content:flex-end; height:100%;">
                                        <div style="font-weight:700; color:#64748b; margin-bottom:5px;">Low</div>
                                        <div style="height:50px; background:#cbd5e1; border-radius:4px 4px 0 0; width:100%;"></div>
                                        <div style="margin-top:10px; font-size:0.85rem; font-weight:700; color:#334155;">Older (>45)</div>
                                    </div>

                                </div>

                                <div class="hint-box" style="margin-top:20px; border-left:4px solid #ef4444; background:white;">
                                    <div style="font-weight:800; color:#ef4444; font-size:1.0rem;">❌ EVIDENCE LOGGED: Age Representation Bias</div>
                                    <div style="font-size:0.95rem; margin-top:5px;">
                                        The data is concentrated in the 25-45 age "Bubble." The model has a **blind spot** for younger and older people, meaning predictions for those groups will be unreliable (Generalization Error).
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 REPRESENTATION BIAS EVIDENCE ESTABLISHED: CONTINUE MISSION
                </p>
                <p style="font-size:1.05rem; margin:0;">
                    Answer the question below to receive your next <strong>Moral Compass Score boost</strong>.
                    <br>Then click <strong>Next</strong> to <strong>summarize your data forensic lab findings.</strong>
                </p>
            </div>

                </div>
            </div>
        """,
    },

    # --- MODULE 4: EVIDENCE REPORT (Input Flaws) ---
    {
        "id": 4,
        "title": "Evidence Report: Input Flaws",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">✓ RULES</div>
                    <div class="tracker-step completed">✓ EVIDENCE</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICT</div>
                </div>
                <h2 class="slide-title" style="font-size:1.6rem; text-align:center; margin-bottom:15px;">Data Forensics Report: Input Flaws</h2>
                <div class="ai-risk-container" style="border: 2px solid #ef4444; background: rgba(239,68,68,0.05); padding: 20px;">
                    <h4 style="margin-top:0; font-size:1.2rem; color:#b91c1c; text-align:center;">📋 EVIDENCE SUMMARY</h4>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                        <thead>
                            <tr style="background: rgba(239,68,68,0.1); border-bottom: 2px solid #ef4444;">
                                <th style="padding: 8px; text-align: left;">SECTOR</th>
                                <th style="padding: 8px; text-align: left;">FINDING</th>
                                <th style="padding: 8px; text-align: left;">IMPACT</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style="border-bottom: 1px solid var(--border-color-primary);">
                                <td style="padding: 8px; font-weight:700;">Race</td>
                                <td style="padding: 8px;">Over-represented (51%)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risk of Increased Prediction Error</td>
                            </tr>
                            <tr style="border-bottom: 1px solid var(--border-color-primary);">
                                <td style="padding: 8px; font-weight:700;">Gender</td>
                                <td style="padding: 8px;">Under-represented (19%)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risk of Increased Prediction Error</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight:700;">Age</td>
                                <td style="padding: 8px;">Excluded Groups (Under 25/Over 45)</td>
                                <td style="padding: 8px; color:#b91c1c;">Risk of Increased Prediction Error</td>
                            </tr>
                        </tbody>
                    </table>
                </div>


                <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                    🚀 NEXT: INVESTIGATE ERRORS IN OUTPUTS - CONTINUE MISSION
                </p>
                <p style="font-size:1.05rem; margin:0;">
                    Answer the question below to receive your next <strong>Moral Compass Score boost</strong>.
                    <br>Click  <strong>Next</strong> to proceed to **Step 3** to find proof of actual harm: **The Error Gaps**.
                </p>
            </div>
                </div>
            </div>
        """
    },

    # --- MODULE 5: INTRO TO PREDICTION ERROR ---
    {
        "id": 5,
        "title": "Part II: Step 3 — Proving the Prediction Error",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. RULES</div>
                    <div class="tracker-step completed">2. EVIDENCE</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICT</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">STEP 3: EVALUATE PREDICTION ERRORS</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#be123c;">The Hunt For Prediction Errors</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:#334155;">
                            We found evidence that the Input Data is biased. Now we must investigate if this bias has influenced the <strong>Model's Decisions</strong>.
                            <br>We are looking for the second Red Flag from our Rulebook: <strong>Error Gaps</strong>.
                        </p>
                    </div>

                    <div style="background:white; border:2px solid #e2e8f0; border-radius:16px; padding:25px; margin-bottom:25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                        
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid #f1f5f9; padding-bottom:10px;">
                            <div style="font-size:1.5rem;">🚩</div>
                            <div>
                                <strong style="color:#be123c; font-size:1.1rem; text-transform:uppercase; letter-spacing:1px;">PATTERN: "THE DOUBLE STANDARD"</strong>
                                <div style="font-size:0.9rem; color:#64748b;">(Unequal Impact of Mistakes)</div>
                            </div>
                        </div>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
                            
                            <div>
                                <p style="font-size:1rem; color:#334155; line-height:1.6; margin-top:0;">
                                    <strong>The Concept:</strong> A model's prediction shapes a person's future. When it makes a mistake, real people suffer.
                                </p>

                                <div style="margin-top:15px; margin-bottom:15px;">
                                    <div style="background:#fff1f2; padding:12px; border-radius:8px; border:1px solid #fda4af; margin-bottom:10px;">
                                        <div style="font-weight:700; color:#9f1239; margin-bottom:4px; font-size:0.95rem;">⚠️ TYPE 1: FALSE ALARMS</div>
                                        <div style="font-size:0.9rem; color:#881337; line-height:1.4;">Labeling a low-risk person as <strong>High Risk</strong>.</div>
                                        <div style="font-size:0.85rem; font-weight:700; color:#be123c; margin-top:4px;">Harm: Unfair Detention.</div>
                                    </div>

                                    <div style="background:#f0f9ff; padding:12px; border-radius:8px; border:1px solid #bae6fd;">
                                        <div style="font-weight:700; color:#0369a1; margin-bottom:4px; font-size:0.95rem;">⚠️ TYPE 2: MISSED WARNINGS</div>
                                        <div style="font-size:0.9rem; color:#075985; line-height:1.4;">Labeling a high-risk person as <strong>Low Risk</strong>.</div>
                                        <div style="font-size:0.85rem; font-weight:700; color:#0284c7; margin-top:4px;">Harm: Public Safety Risk.</div>
                                    </div>
                                </div>

                                <div style="background:#fff1f2; color:#be123c; padding:10px; border-radius:6px; font-size:0.9rem; border-left:4px solid #db2777; margin-top:15px;">
                                    <strong>Key Clue:</strong> Look for a significant gap in the <strong>False Alarm Rate</strong>. If Group A is flagged incorrectly substantially more than Group B, that is an Error Gap.
                                </div>
                            </div>

                            <div style="background:#f8fafc; padding:20px; border-radius:12px; border:1px solid #e2e8f0; display:flex; flex-direction:column; justify-content:center;">
                                
                                <div style="text-align:center; margin-bottom:10px; font-weight:700; color:#334155; font-size:0.9rem;">
                                    "FALSE ALARMS" (Innocent People Flagged Risky)
                                </div>

                                <div style="margin-bottom:15px;">
                                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:700; color:#9f1239; margin-bottom:4px;">
                                        <span>GROUP A (Targeted)</span>
                                        <span>60% ERROR</span>
                                    </div>
                                    <div style="width:100%; background:#e2e8f0; height:12px; border-radius:10px; overflow:hidden;">
                                        <div style="width:60%; background:#db2777; height:100%;"></div>
                                    </div>
                                </div>

                                <div>
                                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:700; color:#64748b; margin-bottom:4px;">
                                        <span>GROUP B (Baseline)</span>
                                        <span>30% ERROR</span>
                                    </div>
                                    <div style="width:100%; background:#e2e8f0; height:12px; border-radius:10px; overflow:hidden;">
                                        <div style="width:30%; background:#94a3b8; height:100%;"></div>
                                    </div>
                                </div>

                                <div style="text-align:center; margin-top:15px; font-size:0.85rem; color:#db2777; font-weight:700; background:#fff1f2; padding:5px; border-radius:4px;">
                                    ⚠️ GAP DETECTED: +30 Percentage Point Difference
                                </div>

                            </div>
                        </div>
                    </div>

                    <details style="margin-bottom:25px; cursor:pointer; background:#fff1f2; border:1px solid #fda4af; border-radius:8px; padding:12px;">
                        <summary style="font-weight:700; color:#9f1239; font-size:0.95rem;">🔬 The Hypothesis: How is Representation Bias connected to Prediction Error?</summary>
                        <div style="margin-top:12px; font-size:0.95rem; color:#881337; line-height:1.5; padding:0 5px;">
                            <p style="margin-bottom:10px;"><strong>Connect the dots:</strong> In Step 2, we found that the input data overrepresented specific groups.</p>
                            <p><strong>The Theory:</strong> Because the AI saw these groups more often in arrest records, the data structure may lead the model to make group-specific prediction mistakes. The model may generate more <strong>False Alarms</strong> for innocent people from these groups at a much higher rate.</p>
                        </div>
                    </details>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; color:#9f1239; margin-bottom:5px;">
                            🚀 ERROR PATTERN ESTABLISHED: CONTINUE MISSION
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:#881337;">
                            Answer the question below to confirm your target.
                            <br>Then click <strong>Next</strong> to open the <strong>Prediction Error Lab</strong> and test the False Alarm Rates.
                        </p>
                    </div>

                </div>
            </div>
        """
    },

    # --- MODULE 6: RACE ERROR GAP LAB ---
# --- MODULE 6: PREDICTION ERROR LAB ---
# --- MODULE 6: THE RACE ERROR GAP LAB ---
    {
        "id": 6,
        "title": "Step 3: The Race Error Gap Lab",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. RULES</div>
                    <div class="tracker-step completed">2. EVIDENCE</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICT</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">STEP 3: ANALYZE THE PREDICTION ERROR GAP</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#be123c;">The Prediction Error Lab - Race Analysis</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:#334155;">
                            We suspected the model is generating unfair amounts of prediction errors for specific groups. Now, we run the analysis.
                            <br>Click to reveal the error rates below. Do AI mistakes fall equally across white and black defendants?
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom:25px;">
                        
                        <div class="ai-risk-container" style="padding:0; border:2px solid #ef4444; overflow:hidden; border-radius:12px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.1);">
                            <div style="background:#fff1f2; padding:15px; text-align:center; border-bottom:1px solid #fda4af;">
                                <h3 style="margin:0; font-size:1.25rem; color:#b91c1c;">📡 SCAN 1: FALSE ALARMS</h3>
                                <p style="font-size:0.9rem; margin:5px 0 0 0; color:#9f1239;">(Innocent people wrongly flagged as "High Risk")</p>
                            </div>
                            
                            <details style="cursor:pointer; background:white;">
                                <summary style="list-style:none; padding:20px; font-weight:800; text-align:center; color:#ef4444; font-size:1.1rem; transition:background 0.2s;">
                                    👇 CLICK TO REVEAL DATA
                                </summary>
                                <div style="padding:0 20px 25px 20px; text-align:center; border-top:1px solid #fecdd3;">
                                    
                                    <div style="display:flex; justify-content:center; gap:30px; margin-bottom:20px;">
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444; line-height:1;">45%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:#7f1d1d; margin-top:5px;">AFRICAN-AMERICAN</div>
                                        </div>
                                        <div style="width:1px; background:#e5e7eb;"></div>
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#3b82f6; line-height:1;">23%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:#1e3a8a; margin-top:5px;">WHITE</div>
                                        </div>
                                    </div>

                                    <div class="hint-box" style="border-left:4px solid #ef4444; background:#fff1f2; text-align:left;">
                                        <div style="font-weight:800; color:#b91c1c; font-size:0.95rem;">❌ VERDICT: PUNITIVE BIAS</div>
                                        <div style="font-size:0.9rem; color:#9f1239; margin-top:3px;">
                                            Black defendants are nearly <strong>twice as likely</strong> to be wrongly labeled as dangerous compared to White defendants.
                                        </div>
                                    </div>

                                </div>
                            </details>
                        </div>

                        <div class="ai-risk-container" style="padding:0; border:2px solid #3b82f6; overflow:hidden; border-radius:12px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);">
                            <div style="background:#eff6ff; padding:15px; text-align:center; border-bottom:1px solid #bfdbfe;">
                                <h3 style="margin:0; font-size:1.25rem; color:#1e40af;">📡 SCAN 2: MISSED WARNINGS</h3>
                                <p style="font-size:0.9rem; margin:5px 0 0 0; color:#1e3a8a;">(Risky people wrongly labeled as "Safe")</p>
                            </div>
                            
                            <details style="cursor:pointer; background:white;">
                                <summary style="list-style:none; padding:20px; font-weight:800; text-align:center; color:#3b82f6; font-size:1.1rem; transition:background 0.2s;">
                                    👇 CLICK TO REVEAL DATA
                                </summary>
                                <div style="padding:0 20px 25px 20px; text-align:center; border-top:1px solid #dbeafe;">
                                    
                                    <div style="display:flex; justify-content:center; gap:30px; margin-bottom:20px;">
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#ef4444; line-height:1;">28%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:#7f1d1d; margin-top:5px;">AFRICAN-AMERICAN</div>
                                        </div>
                                        <div style="width:1px; background:#e5e7eb;"></div>
                                        <div style="text-align:center;">
                                            <div style="font-size:2.5rem; font-weight:900; color:#3b82f6; line-height:1;">48%</div>
                                            <div style="font-size:0.85rem; font-weight:700; color:#1e3a8a; margin-top:5px;">WHITE</div>
                                        </div>
                                    </div>

                                    <div class="hint-box" style="border-left:4px solid #3b82f6; background:#eff6ff; text-align:left;">
                                        <div style="font-weight:800; color:#1e40af; font-size:0.95rem;">❌ VERDICT: LENIENCY BIAS</div>
                                        <div style="font-size:0.9rem; color:#1e3a8a; margin-top:3px;">
                                            White defendants who re-offend are much more likely to be <strong>missed</strong> by the system than Black defendants.
                                        </div>
                                    </div>

                                </div>
                            </details>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:20px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; color:#9f1239; margin-bottom:5px;">
                            🚀 RACIAL ERROR GAP CONFIRMED
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:#881337;">
                            We have demonstrated the model has a "Double Standard" for race. 
                            <br>Answer the question below to certify your findings, then proceed to <strong>Step 4: Analyze Gender, Age, and Geography Gaps in Error.</strong>
                        </p>
                    </div>

                </div>
            </div>
        """
    },

    # --- MODULE 7: GENERALIZATION SCAN LAB ---
# --- MODULE 7: GENERALIZATION & PROXY SCAN ---
    {
        "id": 7,
        "title": "Step 3: Generalization Scan Lab",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. RULES</div>
                    <div class="tracker-step completed">2. EVIDENCE</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICT</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">STEP 3: ANALYZE THE PREDICTION ERROR GAP</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#b91c1c;">Gender, Age, and Geography Error Scans</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:#334155;">
                            We revealed the Racial Error Gap. But bias hides in other places too.
                            <br>Use the scanner below to check for gender and age <strong>Representation Errors</strong> (due to data gaps) and <strong>Proxy Bias</strong> (hidden variables).
                        </p>
                    </div>

                    <div style="margin-top:20px;">
                        <input type="radio" id="scan-gender-err" name="error-tabs" class="scan-radio" checked>
                        <input type="radio" id="scan-age-err" name="error-tabs" class="scan-radio">
                        <input type="radio" id="scan-geo-err" name="error-tabs" class="scan-radio">

                        <div class="forensic-tabs" style="display:flex; justify-content:center; gap:10px; margin-bottom:0;">
                            <label for="scan-gender-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#9f1239;">SCAN: GENDER</label>
                            <label for="scan-age-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#9f1239;">SCAN: AGE</label>
                            <label for="scan-geo-err" class="tab-label-styled" style="flex:1; text-align:center; border-color:#fda4af; color:#9f1239;">SCAN: GEOGRAPHY</label>
                        </div>

                        <div class="scan-content" style="border-top: 3px solid #db2777;">

                            <div class="scan-pane pane-gender-err">
                                <div style="background:#fff1f2; padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#b91c1c;">📡 GENDER SCAN: PREDICTION ERROR</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:#9f1239;">(Does the "Data Gap" lead to more mistakes?)</p>
                                </div>

                                <details style="cursor:pointer; background:white; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:#fff1f2;">
                                        👇 CLICK TO REVEAL FALSE ALARM RATES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#9f1239;">WOMEN (The Minority Class)</span>
                                                <span style="font-weight:700; color:#9f1239;">32% Error</span>
                                            </div>
                                            <div style="width:100%; background:#e2e8f0; height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:32%; background:#db2777; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#64748b;">MEN (Well Represented)</span>
                                                <span style="font-weight:700; color:#64748b;">18% Error</span>
                                            </div>
                                            <div style="width:100%; background:#e2e8f0; height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:18%; background:#94a3b8; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:#fff1f2;">
                                            <div style="font-weight:800; color:#b91c1c;">❌ VERDICT: BLIND SPOT CONFIRMED</div>
                                            <div style="font-size:0.95rem; margin-top:5px;">
                                                Because the model has less data on women, it is "guessing" more often. 
                                                This high error rate is most likely the result of the <strong>Data Gap</strong> we found in Step 2.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <div class="scan-pane pane-age-err">
                                <div style="background:#fff1f2; padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#b91c1c;">📡 AGE SCAN: PREDICTION ERROR</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:#9f1239;">(Does the model fail outside the "25-45" bubble?)</p>
                                </div>

                                <details style="cursor:pointer; background:white; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:#fff1f2;">
                                        👇 CLICK TO REVEAL FALSE ALARM RATES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="display:flex; align-items:flex-end; justify-content:space-around; height:100px; margin-bottom:15px; padding-bottom:10px; border-bottom:1px solid #e2e8f0;">
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#ef4444; margin-bottom:2px;">33%</div>
                                                <div style="height:60px; background:#ef4444; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px;"<Less than 25</div>
                                            </div>
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#16a34a; margin-bottom:2px;">18%</div>
                                                <div style="height:30px; background:#16a34a; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px;">25-45</div>
                                            </div>
                                            <div style="text-align:center; width:25%;">
                                                <div style="font-size:0.8rem; font-weight:700; color:#ef4444; margin-bottom:2px;">27%</div>
                                                <div style="height:50px; background:#ef4444; width:100%; border-radius:4px 4px 0 0;"></div>
                                                <div style="font-size:0.75rem; font-weight:700; margin-top:5px;">Greater than 45</div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:#fff1f2;">
                                            <div style="font-weight:800; color:#b91c1c;">❌ VERDICT: THE "U-SHAPED" FAILURE</div>
                                            <div style="font-size:0.95rem; margin-top:5px;">
                                                The model works well for the "Bubble" (25-45) with more data but fails significantly for the less than 25 and greater than 45 age categories. 
                                                It cannot accurately predict risk for age groups it hasn't studied enough.
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <div class="scan-pane pane-geo-err">
                                <div style="background:#fff1f2; padding:15px; text-align:center; border-bottom:1px solid #fda4af; margin-bottom:15px;">
                                    <h3 style="margin:0; font-size:1.2rem; color:#b91c1c;">📡 GEOGRAPHY SCAN: THE PROXY CHECK</h3>
                                    <p style="font-size:0.9rem; margin:5px 0 0 0; color:#9f1239;">(Is "Zip Code" creating a racial double standard?)</p>
                                </div>

                                <details style="cursor:pointer; background:white; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden;">
                                    <summary style="list-style:none; padding:15px; font-weight:800; text-align:center; color:#db2777; font-size:1.05rem; background:#fff1f2;">
                                        👇 CLICK TO REVEAL FALSE ALARM RATES
                                    </summary>
                                    <div style="padding:20px;">
                                        
                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#9f1239;">URBAN ZONES (High Minority Pop.)</span>
                                                <span style="font-weight:700; color:#9f1239;">58% Error</span>
                                            </div>
                                            <div style="width:100%; background:#e2e8f0; height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:58%; background:#db2777; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div style="margin-bottom:20px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                                <span style="font-weight:700; color:#64748b;">RURAL ZONES</span>
                                                <span style="font-weight:700; color:#64748b;">22% Error</span>
                                            </div>
                                            <div style="width:100%; background:#e2e8f0; height:18px; border-radius:4px; overflow:hidden;">
                                                <div style="width:22%; background:#94a3b8; height:100%;"></div>
                                            </div>
                                        </div>

                                        <div class="hint-box" style="border-left:4px solid #db2777; background:#fff1f2;">
                                            <div style="font-weight:800; color:#b91c1c;">❌ VERDICT: PROXY (HIDDEN RELATIONSHIP) BIAS CONFIRMED</div>
                                            <div style="font-size:0.95rem; margin-top:5px;">
                                                The error rate in Urban Zones is massive (58%). 
                                                Even if "Race" was removed, the model is using <strong>Location</strong> to target the same groups. 
                                                It is treating "City Resident" as a synonym for "High Risk."
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                        </div>
                    </div>

                    <div style="text-align:center; margin-top:25px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; color:#9f1239; margin-bottom:5px;">
                            🚀 ALL SYSTEMS SCANNED
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:#881337;">
                            You have collected all the forensic evidence. The bias is systemic.
                            <br>Click <strong>Next</strong> to make your final recommendation about the AI system.
                        </p>
                    </div>

                </div>
            </div>
        """
    },
    # --- MODULE 8: PREDICTION AUDIT SUMMARY ---
    {
        "id": 8,
        "title": "Step 3: Audit Report Summary",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. RULES</div>
                    <div class="tracker-step completed">2. EVIDENCE</div>
                    <div class="tracker-step active">3. ERROR</div>
                    <div class="tracker-step">4. VERDICT</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">STEP 3: AUDIT REPORT SUMMARY</h2>

                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#b91c1c;">Final Prediction Analysis</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:#334155;">
                            Review your forensic logs. You have uncovered systemic failures across multiple dimensions.
                            <br>This evidence shows the model violates the core principle of <strong>Justice & Fairness</strong>.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:25px; margin-bottom:30px;">

                        <div style="background:#fff1f2; border:2px solid #ef4444; border-radius:12px; padding:20px; box-shadow: 0 4px 10px rgba(239,68,68,0.1);">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #fda4af; padding-bottom:10px; margin-bottom:15px;">
                                <strong style="color:#9f1239; font-size:1.1rem;">🚨 PRIMARY THREAT</strong>
                                <span style="background:#ef4444; color:white; font-size:0.75rem; font-weight:800; padding:4px 8px; border-radius:4px;">CONFIRMED</span>
                            </div>
                            <h3 style="margin:0 0 10px 0; color:#b91c1c; font-size:1.25rem;">Racial Double Standard</h3>
                            <p style="font-size:0.95rem; color:#7f1d1d; line-height:1.5;">
                                <strong>The Evidence:</strong> African-American defendants face a <strong>45% False Alarm Rate</strong> (vs. 23% for White defendants).
                            </p>
                            <div style="background:white; padding:10px; border-radius:6px; border:1px solid #fda4af; margin-top:10px;">
                                <strong style="color:#ef4444; font-size:0.9rem;">The Impact:</strong> Punitive Bias. Innocent people are being wrongly flagged for detention at 2x the rate of others.
                            </div>
                        </div>

                        <div style="background:white; border:2px solid #e2e8f0; border-radius:12px; padding:20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding-bottom:10px; margin-bottom:15px;">
                                <strong style="color:#475569; font-size:1.1rem;">📍 PROXY FAILURE</strong>
                                <span style="background:#f59e0b; color:white; font-size:0.75rem; font-weight:800; padding:4px 8px; border-radius:4px;">DETECTED</span>
                            </div>
                            <h3 style="margin:0 0 10px 0; color:#334155; font-size:1.25rem;">Geographic Discrimination</h3>
                            <p style="font-size:0.95rem; color:#475569; line-height:1.5;">
                                <strong>The Evidence:</strong> Urban Zones show a massive <strong>58% Error Rate</strong>.
                            </p>
                            <div style="background:#f8fafc; padding:10px; border-radius:6px; border:1px solid #e2e8f0; margin-top:10px;">
                                <strong style="color:#64748b; font-size:0.9rem;">The Mechanism:</strong> Although "Race" was hidden, the AI used "Zip Code" as a loophole to target the same communities.
                            </div>
                        </div>

                        <div style="grid-column: span 2; background:#f0f9ff; border:2px solid #bae6fd; border-radius:12px; padding:20px;">
                            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                                <span style="font-size:1.5rem;">📉</span>
                                <h3 style="margin:0; color:#0369a1; font-size:1.2rem;">Secondary Failure: Prediction Errors Due to Represenation Bias</h3>
                            </div>
                            <p style="font-size:1rem; color:#334155; margin-bottom:0;">
                                <strong>The Evidence:</strong> High instability in predictions for <strong>Women and Younger/Older Age Groups</strong>.
                                <br>
                                <span style="color:#0284c7; font-size:0.95rem;"><strong>Why?</strong> The input data lacked sufficient examples for these groups (The Distorted Mirror), causing the model to "guess" rather than learn.</span>
                            </p>
                        </div>

                    </div>


                    <div style="text-align:center; margin-top:25px; padding:20px; background:linear-gradient(to right, rgba(219,39,119,0.1), rgba(251,113,133,0.1)); border-radius:12px; border:2px solid #fecdd3;">
                        <p style="font-size:1.15rem; font-weight:800; color:#9f1239; margin-bottom:5px;">
                            🚀 INVESTIGATION CASE FILE CLOSED. FINAL EVIDENCE LOCKED.
                        </p>
                        <p style="font-size:1.05rem; margin:0; color:#881337;">
                            You have successfully investigated the Inputs Data and the Output Errors.
                            <br>Answer the question below to boost your Moral Compass score.  Then click <strong>Next</strong> to file your final report about the AI system.
                        </p>
                    </div>
                </div>
            </div>
        """
    },

    # --- MODULE 8: FINAL ERROR REPORT ---
# --- MODULE 9: FINAL VERDICT & REPORT GENERATION ---
    {
        "id": 9,
        "title": "Step 4: The Final Verdict",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. RULES</div>
                    <div class="tracker-step completed">2. EVIDENCE</div>
                    <div class="tracker-step completed">3. ERROR</div>
                    <div class="tracker-step active">4. VERDICT</div>
                </div>

                <div class="slide-body">
                    <h2 class="slide-title" style="margin:0;">STEP 4: FILE YOUR FINAL REPORT</h2>

                    <div style="text-align:center; margin-bottom:20px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#0f766e;">Assemble The Case File</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:#334155;">
                            You have completed the audit. Now you must build the final report for the court and other stakeholders.
                            <br><strong>Select the valid findings below</strong> to add them to the official record. Be careful—do not include false evidence.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:30px;">

                        <details style="background:white; border:2px solid #e2e8f0; border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:#334155; display:flex; align-items:center; gap:10px;">
                                <div style="background:#e2e8f0; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center;">+</div>
                                Finding: "The Distorted Mirror"
                            </summary>
                            <div style="background:#f0fdf4; padding:15px; border-top:1px solid #bbf7d0; color:#166534;">
                                <strong style="color:#15803d;">✅ ADDED TO REPORT</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmed: The Input Data incorrectly over-represents specific demographic groups likely due in part to historical bias.</p>
                            </div>
                        </details>

                        <details style="background:white; border:2px solid #e2e8f0; border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:#334155; display:flex; align-items:center; gap:10px;">
                                <div style="background:#e2e8f0; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center;">+</div>
                                Finding: "Malicious Programmer Intent"
                            </summary>
                            <div style="background:#fef2f2; padding:15px; border-top:1px solid #fecaca; color:#991b1b;">
                                <strong style="color:#b91c1c;">❌ REJECTED</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Incorrect. We found no evidence of malicious code. The bias came from the <em>data</em> and <em>proxies</em>, not the programmer's personality.</p>
                            </div>
                        </details>

                        <details style="background:white; border:2px solid #e2e8f0; border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:#334155; display:flex; align-items:center; gap:10px;">
                                <div style="background:#e2e8f0; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center;">+</div>
                                Finding: "Racial Double Standard"
                            </summary>
                            <div style="background:#f0fdf4; padding:15px; border-top:1px solid #bbf7d0; color:#166534;">
                                <strong style="color:#15803d;">✅ ADDED TO REPORT</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmed: African-American defendants suffer a 2x higher False Alarm rate than White defendants.</p>
                            </div>
                        </details>

                        <details style="background:white; border:2px solid #e2e8f0; border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:#334155; display:flex; align-items:center; gap:10px;">
                                <div style="background:#e2e8f0; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center;">+</div>
                                Finding: "Proxy Variable Leakage"
                            </summary>
                            <div style="background:#f0fdf4; padding:15px; border-top:1px solid #bbf7d0; color:#166534;">
                                <strong style="color:#15803d;">✅ ADDED TO REPORT</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmed: "Zip Code" is functioning as a proxy for Race, reintroducing bias even when variables like Race are removed.</p>
                            </div>
                        </details>

                        <details style="background:white; border:2px solid #e2e8f0; border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:#334155; display:flex; align-items:center; gap:10px;">
                                <div style="background:#e2e8f0; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center;">+</div>
                                Finding: "Hardware Calculation Error"
                            </summary>
                            <div style="background:#fef2f2; padding:15px; border-top:1px solid #fecaca; color:#991b1b;">
                                <strong style="color:#b91c1c;">❌ REJECTED</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Irrelevant. The servers are working fine. The math is correct; the <em>patterns</em> it learned are unfair.</p>
                            </div>
                        </details>

                         <details style="background:white; border:2px solid #e2e8f0; border-radius:8px; overflow:hidden; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <summary style="list-style:none; padding:15px; font-weight:700; color:#334155; display:flex; align-items:center; gap:10px;">
                                <div style="background:#e2e8f0; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center;">+</div>
                                Finding: "Generalization Blind Spots"
                            </summary>
                            <div style="background:#f0fdf4; padding:15px; border-top:1px solid #bbf7d0; color:#166534;">
                                <strong style="color:#15803d;">✅ ADDED TO REPORT</strong>
                                <p style="margin:5px 0 0 0; font-size:0.9rem;">Confirmed: Lack of data for Women, Younger, and Older defendants creates unreliable predictions.</p>
                            </div>
                        </details>

                    </div>

                    <div style="background:#f8fafc; border-top:2px solid #e2e8f0; padding:25px; text-align:center; border-radius:0 0 12px 12px; margin-top:-15px;">
                        <h3 style="margin-top:0; color:#1e293b;">⚖️ SUBMIT YOUR RECOMMENDATION (By using the Moral Compass Question below these cards.)</h3>
                        <p style="font-size:1.05rem; margin-bottom:20px; color:#475569;">
                            Based on the evidence filed above, what is your official recommendation regarding this AI system?
                        </p>

                        <div style="display:flex; justify-content:center; gap:20px; flex-wrap:wrap;">
                            <div style="background:white; border:1px solid #cbd5e1; padding:15px 25px; border-radius:8px; cursor:pointer; max-width:250px; opacity:0.8; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                                <div style="font-size:2rem; margin-bottom:10px;">✅</div>
                                <div style="font-weight:700; color:#166534; margin-bottom:5px;">CERTIFY AS SAFE</div>
                                <div style="font-size:0.85rem; color:#475569;">The biases are minor technicalities. Continue using the system.</div>
                            </div>

                            <div style="background:white; border:2px solid #ef4444; padding:15px 25px; border-radius:8px; cursor:pointer; max-width:250px; box-shadow:0 4px 12px rgba(239,68,68,0.2);">
                                <div style="font-size:2rem; margin-bottom:10px;">🚨</div>
                                <div style="font-weight:700; color:#b91c1c; margin-bottom:5px;">RED NOTICE: PAUSE & FIX</div>
                                <div style="font-size:0.85rem; color:#7f1d1d;">The system violates Justice & Equity principles. Halt immediately.</div>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:30px;">
                        <p style="font-size:0.95rem; color:#64748b;">
                            Select your final recommendation below to officially file your report and complete your investigation.
                        </p>
                    </div>

                </div>
            </div>
        """
    },


    # --- MODULE 10: PROMOTION ---
# --- MODULE 10: MISSION ACCOMPLISHED ---
    {
        "id": 10,
        "title": "Mission Accomplished: Promotion Unlocked",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">✓ RULES</div>
                    <div class="tracker-step completed">✓ EVIDENCE</div>
                    <div class="tracker-step completed">✓ ERROR</div>
                    <div class="tracker-step completed">✓ VERDICT</div>
                </div>

                <div class="slide-body">
                    
                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title" style="margin-top:10px; color:#15803d;">🎉 MISSION ACCOMPLISHED</h2>
                        <p style="font-size:1.1rem; max-width:820px; margin:0 auto; color:#334155;">
                            Report Filed. The court has accepted your recommendation to <strong>PAUSE</strong> the system.
                        </p>
                    </div>

                    <div style="background:#f0fdf4; border:2px solid #22c55e; border-radius:12px; padding:20px; margin-bottom:30px; text-align:center; box-shadow: 0 4px 15px rgba(34, 197, 94, 0.1);">
                        <div style="font-size:1.2rem; font-weight:800; color:#15803d; letter-spacing:1px; text-transform:uppercase;">
                            ✅ DECISION VALIDATED
                        </div>
                        <p style="font-size:1.05rem; color:#166534; margin:10px 0 0 0;">
                            You chose the responsible path. That decision required evidence, judgment, and a deep commitment to the principle of <strong>Justice & Equity</strong>.
                        </p>
                    </div>

                    <div style="background:linear-gradient(135deg, #eff6ff 0%, #f0fdfa 100%); border:2px solid #0ea5e9; border-radius:16px; padding:0; overflow:hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                        
                        <div style="background:#0ea5e9; padding:15px; text-align:center; color:white;">
                            <h3 style="margin:0; font-size:1.3rem; letter-spacing:1px;">🎖️ PROMOTION UNLOCKED</h3>
                            <div style="font-size:0.9rem; opacity:0.9;">LEVEL UP: FROM DETECTIVE TO BUILDER</div>
                        </div>

                        <div style="padding:25px;">
                            <p style="text-align:center; font-size:1.1rem; color:#334155; margin-bottom:20px;">
                                Exposing bias is only the first half of the mission. Now that you have the evidence, the real work begins.
                                <br><strong>You are trading your Magnifying Glass for a Wrench.</strong>
                            </p>

                            <div style="background:white; border-radius:12px; padding:20px; border:1px solid #bae6fd;">
                                <h4 style="margin-top:0; color:#0369a1; text-align:center; margin-bottom:15px;">🎓 NEW ROLE: FAIRNESS ENGINEER</h4>
                                
                                <ul style="list-style:none; padding:0; margin:0; font-size:1rem; color:#475569;">
                                    <li style="margin-bottom:12px; display:flex; gap:10px; align-items:start;">
                                        <span>🔧</span>
                                        <span><strong>Your Task 1:</strong> Dismantle the "Proxy Variables" (Remove Zip Code bias).</span>
                                    </li>
                                    <li style="margin-bottom:12px; display:flex; gap:10px; align-items:start;">
                                        <span>📊</span>
                                        <span><strong>Your Task 2:</strong> Fix the "Distorted Mirror" by redesigning the data strategy.</span>
                                    </li>
                                    <li style="display:flex; gap:10px; align-items:start;">
                                        <span>🗺️</span>
                                        <span><strong>Your Task 3:</strong> Build an ethical roadmap for continuous monitoring.</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:30px;">
                        <p style="font-size:1.1rem; font-weight:600; color:#475569;">
                            👉 Your next mission starts in <strong>Activity 8: The Fairness Fixer</strong>.
                            <br>
                            <span style="font-size:0.95rem; font-weight:400;"><strong>Scroll down to the next app</strong> to conclude this audit and begin the repairs.</span>
                        </p>
                    </div>

                </div>
            </div>
        """,
    },
]
# --- 5. INTERACTIVE CONTENT CONFIGURATION (APP 1) ---
QUIZ_CONFIG = {
      0: {
        "t": "t1",
        # Added bold incentive text to the question
        "q": "🚀 **First Score Opportunity:** Why do we multiply your Accuracy by Ethical Progress? (Answer correctly to earn your first Moral Compass Score boost!)",
        "o": [
            "A) Because simple accuracy ignores potential bias and harm.",
            "B) To make the leaderboard math more complicated.",
            "C) Accuracy is the only metric that actually matters.",
        ],
        "a": "A) Because simple accuracy ignores potential bias and harm.",
        # Updated success message to confirm the 'win'
        "success": "<strong>Score Unlocked!</strong> Calibration complete. You are now officially on the leaderboard.",
    },
    1: {
        "t": "t2",
        "q": "What is the best first step before you start examining the model's data?",
        "o": [
            "Jump straight into the data and look for patterns.",
            "Learn the rules that define what counts as bias.",
            "Let the model explain its own decisions.",
        ],
        "a": "Learn the rules that define what counts as bias.",
        "success": "Briefing complete. You’re starting your investigation with the right rules in mind.",
    },
    2: {
        "t": "t3",
        "q": "What does Justice & Equity require?",
        "o": [
            "Explain model decisions",
            "Checking group level prediction errors to prevent systematic harm",
            "Minimize error rate",
        ],
        "a": "Checking group level prediction errors to prevent systematic harm",
        "success": "Protocol Active. You are now auditing for Justice & Fairness.",
    },
    3: {
        "t": "t4",
        "q": "Detective, we suspect the input data is a 'Distorted Mirror' of reality. To confirm if Representation Bias exists, what is your primary forensic target?",
        "o": [
            "A) I need to read the judge's personal diary entries.",
            "B) I need to check if the computer is plugged in correctly.",
            "C) I need to compare the Demographic Distributions (Race/Gender) in the data against real-world population statistics.",
        ],
        "a": "C) I need to compare the Demographic Distributions (Race/Gender) in the data against real-world population statistics.",
        "success": "Target Acquired. You are ready to enter the Data Forensics Lab.",
    },
    4: {
        "t": "t5",
        "q": "Forensic Analysis Review: You flagged the Gender data as a 'Data Gap' (only 19% Female). According to your evidence log, what is the specific technical risk for this group?",
        "o": [
            "A) The model will have a 'Blind Spot' because it hasn't seen enough examples to learn accurate patterns.",
            "B) The AI will automatically target this group due to historical over-policing.",
            "C) The model will default to the 'Real World' statistics to fill in the missing numbers.",
        ],
        "a": "A) The model will have a 'Blind Spot' because it hasn't seen enough examples to learn accurate patterns.",
        "success": "Evidence Locked. You understand that 'Missing Data' creates blind spots, making predictions for that group less reliable.",
    },
    # --- QUESTION 4 (Evidence Report Summary) ---
    5: {
        "t": "t6",
        "q": "Detective, review your Evidence Summary table. You found instances of both Over-representation (Race) and Under-representation (Gender/Age). What is your general conclusion about how Representation Bias affects the AI?",
        "o": [
            "A) It confirms the dataset is neutral, as the 'Over' and 'Under' categories mathematically cancel each other out.",
            "B) It creates a 'Risk of Increased Prediction Error' in BOTH directions—whether a group is exaggerated or ignored, the AI's view of reality is warped.",
            "C) It only creates risk when data is missing (Under-represented); having extra data (Over-represented) actually makes the model more accurate.",
        ],
        "a": "B) It creates a 'Risk of Increased Prediction Error' in BOTH directions—whether a group is exaggerated or ignored, the AI's view of reality is warped.",
        "success": "Conclusion Verified. Distorted data—whether inflated or missing—can lead to distorted justice.",
    },
    6: {
        "t": "t7",
        "q": "Detective, you are hunting for the 'Double Standard' pattern. Which specific piece of evidence represents this Red Flag?",
        "o": [
            "A) The model makes zero mistakes for any group.",
            "B) One group suffers from a significantly higher 'False Alarm' rate than another group.",
            "C) The input data contains more men than women.",
        ],
        "a": "B) One group suffers from a significantly higher 'False Alarm' rate than another group.",
        "success": "Pattern Confirmed. When the error rate is lopsided, it's a Double Standard.",
    },
    # --- QUESTION 6 (Race Error Gap) ---
    7: {
        "t": "t8",
        "q": "Review your data log. What did the 'False Alarm' scan reveal about the treatment of African-American defendants?",
        "o": [
            "A) They are treated exactly the same as White defendants.",
            "B) They are missed by the system more often (Leniency Bias).",
            "C) They are nearly twice as likely to be wrongly flagged as 'High Risk' (Punitive Bias).",
        ],
        "a": "C) They are nearly twice as likely to be wrongly flagged as 'High Risk' (Punitive Bias).",
        "success": "Evidence Logged. The system is punishing innocent people based on race.",
    },

    # --- QUESTION 7 (Generalization & Proxy Scan) ---
    8: {
        "t": "t9",
        "q": "The Geography Scan showed a massive error rate in Urban Zones. What does this prove about 'Zip Codes'?",
        "o": [
            "A) Zip Codes are acting as a 'Proxy Variable' to target specific groups, even if variables like Race are removed from the dataset.",
            "B) The AI is simply bad at reading maps and location data.",
            "C) People in cities naturally generate more computer errors than people in rural areas.",
        ],
        "a": "A) Zip Codes are acting as a 'Proxy Variable' to target specific groups, even if variables like Race are removed from the dataset.",
        "success": "Proxy Identified. Hiding a variable doesn't work if you leave a proxy behind.",
    },

    # --- QUESTION 8 (Audit Summary) ---
    9: {
        "t": "t10",
        "q": "You have closed the case file. Which of the following is CONFIRMED as the 'Primary Threat' in your final report?",
        "o": [
            "A) A Racial Double Standard where innocent Black defendants are penalized twice as often.",
            "B) Malicious code written by hackers to break the system.",
            "C) A hardware failure in the server room causing random math errors.",
        ],
        "a": "A) A Racial Double Standard where innocent Black defendants are penalized twice as often.",
        "success": "Threat Assessed. The bias is confirmed and documented.",
    },

    # --- QUESTION 9 (Final Verdict) ---
    10: {
        "t": "t11",
        "q": "Based on the severe violations of Justice & Equity found in your audit, what is your final recommendation to the court?",
        "o": [
            "A) CERTIFY: The system is mostly fine, minor glitches are acceptable.",
            "B) RED NOTICE: Pause the system for repairs immediately because it is unsafe and biased.",
            "C) WARNING: Only use the AI on weekends when crime is lower.",
        ],
        "a": "B) RED NOTICE: Pause the system for repairs immediately because it is unsafe and biased.",
        "success": "Verdict Delivered. You successfully stopped a harmful system.",
    },
}


# --- 6. SCENARIO CONFIG (for Module 0) ---
SCENARIO_CONFIG = {
    "Criminal risk prediction": {
        "q": (
            "A system predicts who might reoffend.\n"
            "Why isn’t accuracy alone enough?"
        ),
        "summary": "Even tiny bias can repeat across thousands of bail/sentencing calls — real lives, real impact.",
        "a": "Accuracy can look good overall while still being unfair to specific groups affected by the model.",
        "rationale": "Bias at scale means one pattern can hurt many people quickly. We must check subgroup fairness, not just the top-line score."
    },
    "Loan approval system": {
        "q": (
            "A model decides who gets a loan.\n"
            "What’s the biggest risk if it learns from biased history?"
        ),
        "summary": "Some groups get blocked over and over, shutting down chances for housing, school, and stability.",
        "a": "It can repeatedly deny the same groups, copying old patterns and locking out opportunity.",
        "rationale": "If past approvals were unfair, the model can mirror that and keep doors closed — not just once, but repeatedly."
    },
    "College admissions screening": {
        "q": (
            "A tool ranks college applicants using past admissions data.\n"
            "What’s the main fairness risk?"
        ),
        "summary": "It can favor the same profiles as before, overlooking great candidates who don’t ‘match’ history.",
        "a": "It can amplify past preferences and exclude talented students who don’t fit the old mold.",
        "rationale": "Models trained on biased patterns can miss potential. We need checks to ensure diverse, fair selection."
    }
}

# --- 7. SLIDE 3 RIPPLE EFFECT SLIDER HELPER ---
def simulate_ripple_effect_cases(cases_per_year):
    try:
        c = float(cases_per_year)
    except (TypeError, ValueError):
        c = 0.0
    c_int = int(c)
    if c_int <= 0:
        message = (
            "If the system isn't used on any cases, its bias can't hurt anyone yet — "
            "but once it goes live, each biased decision can scale quickly."
        )
    elif c_int < 5000:
        message = (
            f"Even at <strong>{c_int}</strong> cases per year, a biased model can quietly "
            "affect hundreds of people over time."
        )
    elif c_int < 15000:
        message = (
            f"At around <strong>{c_int}</strong> cases per year, a biased model could unfairly label "
            "thousands of people as 'high risk.'"
        )
    else:
        message = (
            f"At <strong>{c_int}</strong> cases per year, one flawed algorithm can shape the futures "
            "of an entire region — turning hidden bias into thousands of unfair decisions."
        )

    return f"""
    <div class="hint-box interactive-block">
        <p style="margin-bottom:4px; font-size:1.05rem;">
            <strong>Estimated cases processed per year:</strong> {c_int}
        </p>
        <p style="margin-bottom:0; font-size:1.05rem;">
            {message}
        </p>
    </div>
    """

# --- 7b. STATIC SCENARIOS RENDERER (Module 0) ---
def render_static_scenarios():
    cards = []
    for name, cfg in SCENARIO_CONFIG.items():
        q_html = cfg["q"].replace("\\n", "<br>")
        cards.append(f"""
            <div class="hint-box" style="margin-top:12px;">
                <div style="font-weight:700; font-size:1.05rem;">📘 {name}</div>
                <p style="margin:8px 0 6px 0;">{q_html}</p>
                <p style="margin:0;"><strong>Key takeaway:</strong> {cfg["a"]}</p>
                <p style="margin:6px 0 0 0; color:var(--body-text-color-subdued);">{cfg["f_correct"]}</p>
            </div>
        """)
    return "<div class='interactive-block'>" + "".join(cards) + "</div>"

def render_scenario_card(name: str):
    cfg = SCENARIO_CONFIG.get(name)
    if not cfg:
        return "<div class='hint-box'>Select a scenario to view details.</div>"
    q_html = cfg["q"].replace("\n", "<br>")
    return f"""
    <div class="scenario-box">
        <h3 class="slide-title" style="font-size:1.4rem; margin-bottom:8px;">📘 {name}</h3>
        <div class="slide-body">
            <div class="hint-box">
                <p style="margin:0 0 6px 0; font-size:1.05rem;">{q_html}</p>
                <p style="margin:0 0 6px 0;"><strong>Key takeaway:</strong> {cfg['a']}</p>
                <p style="margin:0; color:var(--body-text-color-subdued);">{cfg['rationale']}</p>
            </div>
        </div>
    </div>
    """

def render_scenario_buttons():
    # Stylized, high-contrast buttons optimized for 17–20 age group
    btns = []
    for name in SCENARIO_CONFIG.keys():
        btns.append(gr.Button(
            value=f"🎯 {name}",
            variant="primary",
            elem_classes=["scenario-choice-btn"]
        ))
    return btns

# --- 8. LEADERBOARD & API LOGIC ---
def get_leaderboard_data(client, username, team_name, local_task_list=None, override_score=None):
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])

        # 1. OPTIMISTIC UPDATE
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

        # 2. SORT with new score
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
    if not username or not token:
        return None, username
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    try:
        client.get_table(TABLE_ID)
    except Exception:
        try:
            client.create_table(
                table_id=TABLE_ID,
                display_name="LMS",
                playground_url="https://example.com",
            )
        except Exception:
            pass
    return get_leaderboard_data(client, username, team_name, task_list_state), username


def trigger_api_update(
    username, token, team_name, module_id, user_real_accuracy, task_list_state, append_task_id=None
):
    if not username or not token:
        return None, None, username, task_list_state
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

    acc = float(user_real_accuracy) if user_real_accuracy is not None else 0.0

    # 1. Update Lists
    old_task_list = list(task_list_state) if task_list_state else []
    new_task_list = list(old_task_list)
    if append_task_id and append_task_id not in new_task_list:
        new_task_list.append(append_task_id)
        try:
            new_task_list.sort(
                key=lambda x: int(x[1:]) if x.startswith("t") and x[1:].isdigit() else 0
            )
        except Exception:
            pass

    # 2. Write to Server
    tasks_completed = len(new_task_list)
    client.update_moral_compass(
        table_id=TABLE_ID,
        username=username,
        team_name=team_name,
        metrics={"accuracy": acc},
        tasks_completed=tasks_completed,
        total_tasks=TOTAL_COURSE_TASKS,
        primary_metric="accuracy",
        completed_task_ids=new_task_list,
    )

    # 3. Calculate Scores Locally (Simulate Before/After)
    old_score_calc = acc * (len(old_task_list) / TOTAL_COURSE_TASKS)
    new_score_calc = acc * (len(new_task_list) / TOTAL_COURSE_TASKS)

    # 4. Get Data with Override to force rank re-calculation
    prev_data = get_leaderboard_data(
        client, username, team_name, old_task_list, override_score=old_score_calc
    )
    lb_data = get_leaderboard_data(
        client, username, team_name, new_task_list, override_score=new_score_calc
    )

    return prev_data, lb_data, username, new_task_list

# --- 9. SUCCESS MESSAGE RENDERER (approved version) ---
# --- 8. SUCCESS MESSAGE / DASHBOARD RENDERING ---
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

# --- 10. DASHBOARD & LEADERBOARD RENDERERS ---
def render_top_dashboard(data, module_id):
    display_score = 0.0
    count_completed = 0
    rank_display = "–"
    team_rank_display = "–"
    if data:
        display_score = float(data.get("score", 0.0))
        rank_display = f"#{data.get('rank', '–')}"
        team_rank_display = f"#{data.get('team_rank', '–')}"
        count_completed = len(data.get("completed_task_ids", []) or [])
    progress_pct = min(100, int((count_completed / TOTAL_COURSE_TASKS) * 100))
    return f"""
    <div class="summary-box">
        <div class="summary-box-inner">
            <div class="summary-metrics">
                <div style="text-align:center;">
                    <div class="label-text">Moral Compass Score</div>
                    <div class="score-text-primary">🧭 {display_score:.3f}</div>
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
                <div class="progress-label">Mission Progress: {progress_pct}%</div>
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
        <h3 class="slide-title" style="margin-bottom:10px;">📊 Live Standings</h3>
        <div class="lb-tabs">
            <input type="radio" id="lb-tab-team" name="lb-tabs" checked>
            <label for="lb-tab-team" class="lb-tab-label">🏆 Team</label>
            <input type="radio" id="lb-tab-user" name="lb-tabs">
            <label for="lb-tab-user" class="lb-tab-label">👤 Individual</label>
            <div class="lb-tab-panels">
                <div class="lb-panel panel-team">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Rank</th><th>Team</th><th style='text-align:right;'>Avg 🧭</th></tr>
                            </thead>
                            <tbody>{team_rows}</tbody>
                        </table>
                    </div>
                </div>
                <div class="lb-panel panel-user">
                    <div class='table-container'>
                        <table class='leaderboard-table'>
                            <thead>
                                <tr><th>Rank</th><th>Agent</th><th style='text-align:right;'>Score 🧭</th></tr>
                            </thead>
                            <tbody>{user_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

def check_audit_report_selection(selected_biases: List[str]) -> Tuple[str, str]:
    # Define the correct findings (matching the choices defined in the front-end)
    CORRECT_FINDINGS = [
        "Choice A: Punitive Bias (Race): AA defendants were twice as likely to be falsely labeled 'High Risk.'",
        "Choice B: Generalization (Gender): The model made more False Alarm errors for women than for men.",
        "Choice C: Leniency Pattern (Race): White defendants who re-offended were more likely to be labeled 'Low Risk.'",
        "Choice E: Proxy Bias (Geography): Location acted as a proxy, doubling False Alarms in high-density areas.",
    ]

    # Define the incorrect finding
    INCORRECT_FINDING = "Choice D: FALSE STATEMENT: The model achieved an equal False Negative Rate (FNR) across all races."

    # Separate correct from incorrect selections
    correctly_selected = [s for s in selected_biases if s in CORRECT_FINDINGS]
    incorrectly_selected = [s for s in selected_biases if s == INCORRECT_FINDING]

    # Check if any correct finding was missed
    missed_correct = [s for s in CORRECT_FINDINGS if s not in selected_biases]

    # --- Generate Feedback ---
    feedback_html = ""
    if incorrectly_selected:
        feedback_html = f"<div class='hint-box' style='border-left:4px solid #ef4444; color:#b91c1c;'>❌ ERROR: The statement '{INCORRECT_FINDING.split(':')[0]}' is NOT a true finding. Check your lab results and try again.</div>"
    elif missed_correct:
        feedback_html = f"<div class='hint-box' style='border-left:4px solid #f97316; color:#f97316;'>⚠️ INCOMPLETE: You missed {len(missed_correct)} piece(s) of key evidence. Your final report must be complete.</div>"
    elif len(selected_biases) == len(CORRECT_FINDINGS):
        feedback_html = "<div class='hint-box' style='border-left:4px solid #22c55e; color:#16a34a;'>✅ EVIDENCE SECURED: This is a complete and accurate diagnosis of the model's systematic failure.</div>"
    else:
        feedback_html = "<div class='hint-box' style='border-left:4px solid var(--color-accent);'>Gathering evidence...</div>"

    # --- Build Markdown Report Preview ---
    if not correctly_selected:
        report_markdown = "Select the evidence cards above to start drafting your report. (The draft report will appear here.)"
    else:
        lines = []
        lines.append("### 🧾 Draft Audit Report")
        lines.append("\n**Findings of Systemic Error:**")

        # Map short findings to the markdown report
        finding_map = {
            "Choice A": "Punitive Bias (Race): The model is twice as harsh on AA defendants.",
            "Choice B": "Generalization (Gender): Higher False Alarm errors for women.",
            "Choice C": "Leniency Pattern (Race): More missed warnings for White defendants.",
            "Choice E": "Proxy Bias (Geography): Location acts as a stand-in for race/class.",
        }

        for i, choice in enumerate(CORRECT_FINDINGS):
            if choice in correctly_selected:
                short_key = choice.split(':')[0]
                lines.append(f"{i+1}. {finding_map[short_key]}")

        if len(correctly_selected) == len(CORRECT_FINDINGS) and not incorrectly_selected:
             lines.append("\n**CONCLUSION:** The evidence proves the system creates unequal harm and violates Justice & Equity.")

        report_markdown = "\n".join(lines)

    return report_markdown, feedback_html

# --- 11. CSS ---
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
/* Add these new classes to your existing CSS block (Section 11) */

/* --- PROGRESS TRACKER STYLES --- */
.tracker-container {
  display: flex;
  justify-content: space-around;
  align-items: center;
  margin-bottom: 25px;
  background: var(--background-fill-secondary);
  padding: 10px 0;
  border-radius: 8px;
  border: 1px solid var(--border-color-primary);
}
.tracker-step {
  text-align: center;
  font-weight: 700;
  font-size: 0.85rem;
  padding: 5px 10px;
  border-radius: 4px;
  color: var(--body-text-color-subdued);
  transition: all 0.3s ease;
}
.tracker-step.completed {
  color: #10b981; /* Green */
  background: rgba(16, 185, 129, 0.1);
}
.tracker-step.active {
  color: var(--color-accent); /* Primary Hue */
  background: var(--color-accent-soft);
  box-shadow: 0 0 5px rgba(99, 102, 241, 0.3);
}

/* --- FORENSICS TAB STYLES --- */
.forensic-tabs {
  display: flex;
  border-bottom: 2px solid var(--border-color-primary);
  margin-bottom: 0;
}
.tab-label-styled {
  padding: 10px 15px;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--body-text-color-subdued);
  border-bottom: 2px solid transparent;
  margin-bottom: -2px; /* Align with border */
  transition: color 0.2s ease;
}

/* Hide the radio buttons */
.scan-radio { display: none; }

/* Content panel styling */
.scan-content {
  background: var(--body-background-fill); /* Light gray or similar */
  padding: 20px;
  border-radius: 0 8px 8px 8px;
  border: 1px solid var(--border-color-primary);
  min-height: 350px;
  position: relative;
}

/* Hide all panes by default */
.scan-pane { display: none; }

/* Show active tab content */
#scan-race:checked ~ .scan-content .pane-race,
#scan-gender:checked ~ .scan-content .pane-gender,
#scan-age:checked ~ .scan-content .pane-age {
  display: block;
}

/* Highlight active tab label */
#scan-race:checked ~ .forensic-tabs label[for="scan-race"],
#scan-gender:checked ~ .forensic-tabs label[for="scan-gender"],
#scan-age:checked ~ .forensic-tabs label[for="scan-age"] {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

/* Utility for danger color */
:root {
    --color-danger-light: rgba(239, 68, 68, 0.1);
    --color-accent-light: rgba(99, 102, 241, 0.15); /* Reusing accent color for general bars */
}
/* --- NEW SELECTORS FOR MODULE 8 (Generalization Scan Lab) --- */

/* Show active tab content in Module 8 */
#scan-gender-err:checked ~ .scan-content .pane-gender-err,
#scan-age-err:checked ~ .scan-content .pane-age-err,
#scan-geo-err:checked ~ .scan-content .pane-geo-err {
  display: block;
}

/* Highlight active tab label in Module 8 */
#scan-gender-err:checked ~ .forensic-tabs label[for="scan-gender-err"],
#scan-age-err:checked ~ .forensic-tabs label[for="scan-age-err"],
#scan-geo-err:checked ~ .forensic-tabs label[for="scan-geo-err"] {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

/* If you used .data-scan-tabs instead of .forensic-tabs in Module 8 HTML,
   the selectors above need to target the parent container correctly.
   Assuming you used the structure from the draft: */

.data-scan-tabs input[type="radio"]:checked + .tab-label-styled {
    color: var(--color-accent);
    border-bottom-color: var(--color-accent);
}

.data-scan-tabs .scan-content .scan-pane {
    display: none;
}
.data-scan-tabs #scan-gender-err:checked ~ .scan-content .pane-gender-err,
.data-scan-tabs #scan-age-err:checked ~ .scan-content .pane-age-err,
.data-scan-tabs #scan-geo-err:checked ~ .scan-content .pane-geo-err {
    display: block;
}
"""

# --- 12. HELPER: SLIDER FOR MORAL COMPASS SCORE (MODULE 0) ---
def simulate_moral_compass_score(acc, progress_pct):
    try:
        acc_val = float(acc)
    except (TypeError, ValueError):
        acc_val = 0.0
    try:
        prog_val = float(progress_pct)
    except (TypeError, ValueError):
        prog_val = 0.0

    score = acc_val * (prog_val / 100.0)
    return f"""
    <div class="hint-box interactive-block">
        <p style="margin-bottom:4px; font-size:1.05rem;">
            <strong>Your current accuracy (from the leaderboard):</strong> {acc_val:.3f}
        </p>
        <p style="margin-bottom:4px; font-size:1.05rem;">
            <strong>Simulated Ethical Progress %:</strong> {prog_val:.0f}%
        </p>
        <p style="margin-bottom:0; font-size:1.08rem;">
            <strong>Simulated Moral Compass Score:</strong> 🧭 {score:.3f}
        </p>
    </div>
    """


# --- 13. APP FACTORY (APP 1) ---
def create_bias_detective_part1_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        module0_done = gr.State(value=False)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

        # --- TOP ANCHOR & LOADING OVERLAY FOR NAVIGATION ---
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>🕵️‍♀️ Authenticating...</h2>"
                "<p>Syncing Moral Compass Data...</p>"
                "</div>"
            )

        # --- MAIN APP VIEW ---
        with gr.Column(visible=False) as main_app_col:
            # Title
            #gr.Markdown("# 🕵️‍♀️ Bias Detective: Part 1 - Data Forensics")

            # Top summary dashboard (progress bar & score)
            out_top = gr.HTML()

            # Dynamic modules container
            module_ui_elements = {}
            quiz_wiring_queue = []

            # --- DYNAMIC MODULE GENERATION ---
            for i, mod in enumerate(MODULES):
                with gr.Column(
                    elem_id=f"module-{i}",
                    elem_classes=["module-container"],
                    visible=(i == 0),
                ) as mod_col:
                    # Core slide HTML
                    gr.HTML(mod["html"])



                    # --- QUIZ CONTENT FOR MODULES WITH QUIZ_CONFIG ---
                    if i in QUIZ_CONFIG:
                        q_data = QUIZ_CONFIG[i]
                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Select Answer:",
                            elem_classes=["quiz-radio-large"],
                        )
                        feedback = gr.HTML("")
                        quiz_wiring_queue.append((i, radio, feedback))

                    # --- NAVIGATION BUTTONS ---
                    with gr.Row():
                        btn_prev = gr.Button("⬅️ Previous", visible=(i > 0))
                        next_label = (
                            "Next ▶️"
                            if i < len(MODULES) - 1
                            else "🎉 You Have Completed Part 1!! (Please Proceed to the Next Activity)"
                        )
                        btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            # Leaderboard card appears AFTER content & interactions
            leaderboard_html = gr.HTML()

            # --- WIRING: QUIZ LOGIC ---
            for mod_id, radio_comp, feedback_comp in quiz_wiring_queue:

                def quiz_logic_wrapper(
                    user,
                    tok,
                    team,
                    acc_val,
                    task_list,
                    ans,
                    mid=mod_id,
                ):
                    cfg = QUIZ_CONFIG[mid]
                    if ans == cfg["a"]:
                        prev, curr, _, new_tasks = trigger_api_update(
                            user, tok, team, mid, acc_val, task_list, cfg["t"]
                        )
                        msg = generate_success_message(prev, curr, cfg["success"])
                        return (
                            render_top_dashboard(curr, mid),
                            render_leaderboard_card(curr, user, team),
                            msg,
                            new_tasks,
                        )
                    else:
                        return (
                            gr.update(),
                            gr.update(),
                            "<div class='hint-box' style='border-color:red;'>"
                            "❌ Incorrect. Review the evidence above.</div>",
                            task_list,
                        )

                radio_comp.change(
                    fn=quiz_logic_wrapper,
                    inputs=[
                        username_state,
                        token_state,
                        team_state,
                        accuracy_state,
                        task_list_state,
                        radio_comp,
                    ],
                    outputs=[out_top, leaderboard_html, feedback_comp, task_list_state],
                )

        # --- GLOBAL LOAD HANDLER ---
        def handle_load(req: gr.Request):
            success, user, token = _try_session_based_auth(req)
            team = "Team-Unassigned"
            acc = 0.0
            fetched_tasks: List[str] = []

            if success and user and token:
                acc, fetched_team = fetch_user_history(user, token)
                os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
                client = MoralcompassApiClient(
                    api_base_url=DEFAULT_API_URL, auth_token=token
                )

                # Simple team assignment helper
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

                exist_team = get_or_assign_team(client, user)
                if fetched_team != "Team-Unassigned":
                    team = fetched_team
                elif exist_team != "team-a":
                    team = exist_team
                else:
                    team = "team-a"

                try:
                    user_stats = client.get_user(table_id=TABLE_ID, username=user)
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
                        username=user,
                        team_name=team,
                        metrics={"accuracy": acc},
                        tasks_completed=len(fetched_tasks),
                        total_tasks=TOTAL_COURSE_TASKS,
                        primary_metric="accuracy",
                        completed_task_ids=fetched_tasks,
                    )
                    time.sleep(1.0)
                except Exception:
                    pass

                data, _ = ensure_table_and_get_data(
                    user, token, team, fetched_tasks
                )
                return (
                    user,
                    token,
                    team,
                    False,
                    render_top_dashboard(data, 0),
                    render_leaderboard_card(data, user, team),
                    acc,
                    fetched_tasks,
                    gr.update(visible=False),
                    gr.update(visible=True),
                )

            # Auth failed / no session
            return (
                None,
                None,
                None,
                False,
                "<div class='hint-box'>⚠️ Auth Failed. Please launch from the course link.</div>",
                "",
                0.0,
                [],
                gr.update(visible=False),
                gr.update(visible=True),
            )

        # Attach load event
        demo.load(
            handle_load,
            None,
            [
                username_state,
                token_state,
                team_state,
                module0_done,
                out_top,
                leaderboard_html,
                accuracy_state,
                task_list_state,
                loader_col,
                main_app_col,
            ],
        )

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

        # --- NAVIGATION BETWEEN MODULES ---
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]

            # Previous button
            if i > 0:
                prev_col = module_ui_elements[i - 1][0]
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

            # Next button
            if i < len(MODULES) - 1:
                next_col = module_ui_elements[i + 1][0]
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




def launch_bias_detective_part1_app(
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
    app = create_bias_detective_part1_app(theme_primary_hue=theme_primary_hue)
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
    launch_bias_detective_part1_app(share=False, debug=True, height=1000)

import os
import sys
import subprocess
import time
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"
TOTAL_COURSE_TASKS = 20  # Combined count across apps
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

# --- 4. MODULE DEFINITIONS (FAIRNESS FIXER) ---
MODULES = [
    # --- MODULE 0: THE PROMOTION ---
    {
        "id": 0,
        "title": "Module 0: The Fairness Engineer's Workbench",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="
                            display:inline-flex;
                            align-items:center;
                            gap:10px;
                            padding:10px 18px;
                            border-radius:999px;
                            background:rgba(16, 185, 129, 0.1);
                            border:1px solid #10b981;
                            font-size:0.95rem;
                            text-transform:uppercase;
                            letter-spacing:0.08em;
                            font-weight:700;
                            color:#065f46;">
                            <span style="font-size:1.1rem;">🎓</span>
                            <span>PROMOTION: FAIRNESS ENGINEER</span>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center;">🔧 Final Phase: The Fix</h2>

                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 20px auto; text-align:center;">
                        <strong>Welcome back.</strong> You successfully exposed the bias in the COMPAS risk prediction AI system and blocked its deployment. Good work.
                    </p>

                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 24px auto; text-align:center;">
                        But the court is still waiting for a tool to help manage the backlog. Your new mission is to take that broken model and <strong>fix it</strong> so it is safe to use.
                    </p>

                    <div class="ai-risk-container" style="border-left:4px solid var(--color-accent);">
                        <h4 style="margin-top:0; font-size:1.15rem;">The Challenge: "Sticky Bias"</h4>
                        <p style="font-size:1.0rem; margin-bottom:0;">
                            You can't just delete the "Race" column and walk away. Bias hides in <strong>Proxy Variables</strong>—data like <em>ZIP Code</em> or <em>Income</em>
                            that correlate with race. If you delete the label but keep the proxies, the model learns the bias anyway.
                        </p>
                    </div>

                    <div class="ai-risk-container" style="margin-top:16px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">📋 Engineering Work Order</h4>
                        <p style="text-align:center; margin-bottom:12px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                            You must complete these three protocols to certify the model for release:
                        </p>

                        <div style="display:grid; gap:10px; margin-top:12px;">

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">✂️</div>
                                <div>
                                    <div style="font-weight:700;">Protocol 1: Sanitize Inputs</div>
                                    <div style="font-size:0.9rem;">Remove protected classes and hunt down hidden proxies.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Pending</div>
                            </div>

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">🔗</div>
                                <div>
                                    <div style="font-weight:700;">Protocol 2: Cause Versus Correlation</div>
                                    <div style="font-size:0.9rem;">Filter data for actual behavior, not just correlation.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Locked</div>
                            </div>

                            <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--background-fill-secondary); border-radius:8px; opacity:0.7;">
                                <div style="font-size:1.4rem;">⚖️</div>
                                <div>
                                    <div style="font-weight:700;">Protocol 3: Representation & Sampling</div>
                                    <div style="font-size:0.9rem;">Balance the data to match the local population.</div>
                                </div>
                                <div style="margin-left:auto; font-weight:700; font-size:0.8rem; text-transform:uppercase; color:var(--body-text-color-subdued);">Locked</div>
                            </div>

                        </div>
                    </div>

                   <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 READY TO START THE FIX?
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Click <strong>Next</strong> to start fixing the model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 1: SANITIZE INPUTS (Protected Classes) ---
    {
        "id": 1,
        "title": "Protocol 1: Sanitize Inputs",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOL 1: SANITIZE INPUTS</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Mission: Remove protected classes & hidden proxies.</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">STEP 1 OF 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        <strong>Fairness Through Blindness.</strong>
                        Legally and ethically, we cannot use <strong>Protected Classes</strong> (features you are born with, like race or age) to calculate someone's risk score.
                    </p>

                    <div class="ai-risk-container">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <h4 style="margin:0;">📂 Dataset Column Inspector</h4>
                            <div style="font-size:0.8rem; font-weight:700; color:#ef4444;">⚠ CONTAINS ILLEGAL FEATURES</div>
                        </div>

                        <p style="font-size:0.95rem; margin-bottom:12px;">
                            Review the raw headers below. Identify the columns that violate fairness laws.
                        </p>

                        <div style="display:flex; gap:8px; flex-wrap:wrap; background:rgba(0,0,0,0.05); padding:12px; border-radius:8px; border:1px solid var(--border-color-primary);">

                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Race
                            </div>
                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Gender
                            </div>
                            <div style="padding:6px 12px; background:#fee2e2; border:1px solid #ef4444; border-radius:6px; font-weight:700; color:#b91c1c;">
                                ⚠️ Age
                            </div>

                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Prior Convictions</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Employment Status</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Zip Code</div>
                        </div>
                    </div>


            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACTION REQUIRED: DELETE PROTECTED INPUT DATA
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Use the Command Panel below to execute deletion.
                            Then click <strong>Next</strong> to continue fixing the model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 2: SANITIZE INPUTS (Proxy Variables) ---
    {
        "id": 2,
        "title": "Protocol 1: Hunting Proxies",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                   <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOL 1: SANITIZE INPUTS</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Mission: Remove protected classes & hidden proxies.</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">STEP 2 OF 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        <strong>The "Sticky Bias" Problem.</strong>
                        You removed Race and Gender. Great. But bias often hides in <strong>Proxy Variables</strong>—neutral data points that act as a secret substitute for race.
                    </p>

                    <div class="hint-box" style="border-left:4px solid #f97316;">
                        <div style="font-weight:700;">Why "Zip Code" is a Proxy</div>

                        <p style="margin:6px 0 0 0;">
                            Historically, many cities were segregated by law or class. Even today, <strong>Zip Code</strong> often correlates strongly with background.
                            </p>
                        <p style="margin-top:8px; font-weight:600; color:#c2410c;">
                            🚨 The Risk: If you give the AI location data, it can "guess" a person's race with high accuracy, re-learning the exact bias you just tried to delete.
                        </p>
                    </div>

                    <div class="ai-risk-container" style="margin-top:16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h4 style="margin:0;">📂 Dataset Column Inspector</h4>
                            <div style="font-size:0.8rem; font-weight:700; color:#f97316;">⚠️ 1 PROXY DETECTED</div>
                        </div>

                        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; padding:12px; background:rgba(0,0,0,0.05); border-radius:8px;">
                            <div style="padding:6px 12px; background:#e5e7eb; color:#9ca3af; text-decoration:line-through; border-radius:6px;">Race</div>
                            <div style="padding:6px 12px; background:#e5e7eb; color:#9ca3af; text-decoration:line-through; border-radius:6px;">Gender</div>

                            <div style="padding:6px 12px; background:#ffedd5; border:1px solid #f97316; border-radius:6px; font-weight:700; color:#9a3412;">
                                ⚠️ Zip Code
                            </div>

                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Prior Convictions</div>
                            <div style="padding:6px 12px; background:var(--background-fill-primary); color:var(--body-text-color); border:1px solid var(--border-color-primary); border-radius:6px;">Employment</div>
                        </div>
                    </div>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACTION REQUIRED: DELETE PROXY INPUT DATA
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Select the Proxy Variable below to scrub it.
                            Then click <strong>Next</strong> to continue fixing the model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 3: THE ACCURACY CRASH (The Pivot) ---
    {
        "id": 3,
        "title": "System Alert: Model Verification",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(59,130,246,0.08); border:2px solid var(--color-accent); border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:white; width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">✂️</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); letter-spacing:0.05em;">PROTOCOL 1: SANITIZE INPUTS</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Phase: Verification & Model Retraining</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:var(--color-accent);">STEP 3 OF 3</div>
                            <div style="height:4px; width:60px; background:#bfdbfe; border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:var(--color-accent); border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">🤖 The Verification Run</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        You have successfully deleted <strong>Race, Gender, Age, and Zip Code</strong>.
                        The dataset is "sanitized" (stripped of all demographic labels). Now we run the simulation to see if the model still works.
                    </p>

                    <details style="border:none; margin-top:20px;">
                        <summary style="
                            background:var(--color-accent);
                            color:white;
                            padding:16px 24px;
                            border-radius:12px;
                            font-weight:800;
                            font-size:1.1rem;
                            text-align:center;
                            cursor:pointer;
                            list-style:none;
                            box-shadow:0 4px 12px rgba(59,130,246,0.3);
                            transition:transform 0.1s ease;">
                            ▶️ CLICK TO FIX MODEL USING REPAIRED DATASET
                        </summary>

                        <div style="margin-top:24px; animation: fadeIn 0.6s ease-in-out;">

                            <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:20px; background:rgba(0,0,0,0.02);">

                                <div style="text-align:center; padding:10px; border-right:1px solid var(--border-color-primary);">
                                    <div style="font-size:2.2rem; font-weight:800; color:#ef4444;">📉 78%</div>
                                    <div style="font-weight:bold; font-size:0.9rem; text-transform:uppercase; color:var(--body-text-color-subdued); margin-bottom:6px;">Accuracy (CRASHED)</div>
                                    <div style="font-size:0.9rem; line-height:1.4;">
                                        <strong>Diagnosis:</strong> The model lost its "shortcuts" (like Zip Code). It is confused and struggling to predict risk accurately.
                                    </div>
                                </div>

                                <div style="text-align:center; padding:10px;">
                                    <div style="font-size:2.2rem; font-weight:800; color:#f59e0b;">🧩 MISSING</div>
                                    <div style="font-weight:bold; font-size:0.9rem; text-transform:uppercase; color:var(--body-text-color-subdued); margin-bottom:6px;">Meaningful Data</div>
                                    <div style="font-size:0.9rem; line-height:1.4;">
                                        <strong>Diagnosis:</strong> We cleaned the bad data, but we didn't replace it with <strong>Meaningful Data</strong>. The model needs better signals to learn from.
                                    </div>
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:20px; border-left:4px solid var(--color-accent);">
                                <div style="font-weight:700; font-size:1.05rem;">💡 The Engineering Pivot</div>
                                <p style="margin:6px 0 0 0;">
                                    A model that knows <em>nothing</em> is fair, but useless.
                                    To fix the accuracy safely, we need to stop deleting and start <strong>finding valid patterns</strong>: meaningful data that explains <em>why</em> crime happens.
                                </p>
                            </div>


                    </details>

                          <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACTION REQUIRED: Find Meaningful Data
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Answer the below question to receive Moral Compass Points.
                            Then click <strong>Next</strong> to continue fixing the model.
                        </p>
                    </div>
                </div>
            </div>
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                /* Hide default arrow */
                details > summary { list-style: none; }
                details > summary::-webkit-details-marker { display: none; }
            </style>
        """,
    },
    # --- MODULE 4: CAUSAL VALIDITY (Big Foot) ---
    {
        "id": 4,
        "title": "Protocol 2: Causal Validity",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(16, 185, 129, 0.1); border:2px solid #10b981; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🔗</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#10b981; letter-spacing:0.05em;">
                                PROTOCOL 2: CAUSE VS. CORRELATION
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Mission: Learn how to tell when a pattern <strong>actually causes</strong> an outcome — and when it’s just a coincidence.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#10b981;">STEP 1 OF 2</div>
                            <div style="height:4px; width:60px; background:rgba(16, 185, 129, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:#10b981; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🧠 The “Big Foot” Trap: When Correlation Tricks You
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        To improve a model, we often add more data.
                        <br>
                        But here’s the problem: the model finds <strong>Correlations</strong> (a relationship between two data variables) and wrongly assumes one <strong>Causes</strong> the other.
                        <br>
                        Consider this real statistical pattern:
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding:20px; border:2px solid #ef4444; background:rgba(239, 68, 68, 0.1);">
                        <div style="font-size:3rem; margin-bottom:10px;">🦶 📈 📖</div>
                        <h3 style="margin:0; color:#ef4444;">
                            The Data: “People with bigger feet have higher reading scores.”
                        </h3>
                        <p style="font-size:1.0rem; margin-top:8px; color:var(--body-text-color);">
                            On average, people with <strong>large feet</strong> score much higher on reading tests than people with <strong>small feet</strong>.
                        </p>
                    </div>

                    <details style="border:none; margin-top:16px;">
                        <summary style="
                            background:var(--color-accent);
                            color:white;
                            padding:12px 20px;
                            border-radius:8px;
                            font-weight:700;
                            text-align:center;
                            cursor:pointer;
                            list-style:none;
                            width:fit-content;
                            margin:0 auto;
                            box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                            🤔 Why does this happen? (Click to reveal)
                        </summary>

                        <div style="margin-top:20px; animation: fadeIn 0.5s ease-in-out;">
                            
                            <div class="hint-box" style="border-left:4px solid #16a34a; background:rgba(22, 163, 74, 0.1);">
                                <div style="font-weight:800; font-size:1.1rem; color:#16a34a;">
                                    The Hidden Third Variable: AGE
                                </div>
                                <p style="margin-top:8px; color:var(--body-text-color);">
                                    Do bigger feet <em>cause</em> people to read better? <strong>No.</strong>
                                    <br>
                                    Children have smaller feet and are still learning to read.
                                    <br>
                                    Adults have bigger feet and have had many more years of reading practice.
                                </p>
                                <p style="margin-bottom:0; color:var(--body-text-color);">
                                    <strong>The Key Idea:</strong> Age causes <em>both</em> foot size and reading ability.
                                    <br>
                                    Shoe size is a <em>correlated signal</em>, not a cause.
                                </p>
                            </div>

                            <p style="font-size:1.05rem; text-align:center; margin-top:20px;">
                                <strong>Why this matters:</strong>
                                <br>
                                In many real-world datasets, some variables look predictive only because they are linked to deeper causes.
                                <br>
                                Good models focus on <strong>what actually causes outcomes</strong>, not just what happens to move together.
                            </p>
                        </div>
                    </details>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACTION REQUIRED: Can you spot the next “Big Foot” trap in the data below?
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Answer this question to boost your Moral Compass score.
                            Then click <strong>Next</strong> to continue fixing the model.
                        </p>
                    </div>
                </div>
            </div>
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-5px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                details > summary { list-style: none; }
                details > summary::-webkit-details-marker { display: none; }
            </style>
        """,
    },
    # --- MODULE 5: APPLYING RESEARCH ---
    {
        "id": 5,
        "title": "Protocol 2: Cause vs. Correlation",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(16, 185, 129, 0.1); border:2px solid #10b981; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🔗</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#10b981; letter-spacing:0.05em;">
                                PROTOCOL 2: CAUSE VS. CORRELATION
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Mission: Remove variables that <strong>correlate</strong> with outcomes but do not <strong>cause</strong> them.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#10b981;">STEP 2 OF 2</div>
                            <div style="height:4px; width:60px; background:rgba(16, 185, 129, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:#10b981; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🔬 Research Check: Choosing Fair Features
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        You are ready to continue to build a more just version of the model. Here are four variables to consider.
                        <br>
                        Use the rule below to discover which variables represent <strong>actual causes</strong> of behavior — and which are just circumstantial correlations.
                    </p>

                    <div class="hint-box" style="border-left:4px solid var(--color-accent); background:var(--background-fill-secondary); border:1px solid var(--border-color-primary);">
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                            <div style="font-size:1.2rem;">📋</div>
                            <div style="font-weight:800; color:var(--color-accent); text-transform:uppercase; letter-spacing:0.05em;">
                                The Engineering Rule
                            </div>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                            
                            <div style="padding:10px; background:rgba(239, 68, 68, 0.1); border-radius:6px; border:1px solid rgba(239, 68, 68, 0.3);">
                                <div style="font-weight:700; color:#ef4444; font-size:0.9rem; margin-bottom:4px;">
                                    🚫 REJECT: BACKGROUND
                                </div>
                                <div style="font-size:0.85rem; line-height:1.4; color:var(--body-text-color);">
                                    Variables describing a person's situation or environment (e.g., wealth, neighborhood).
                                    <br><strong>These correlate with crime but do not cause it.</strong>
                                </div>
                            </div>
                            
                            <div style="padding:10px; background:rgba(22, 163, 74, 0.1); border-radius:6px; border:1px solid rgba(22, 163, 74, 0.3);">
                                <div style="font-weight:700; color:#16a34a; font-size:0.9rem; margin-bottom:4px;">
                                    ✅ KEEP: CONDUCT
                                </div>
                                <div style="font-size:0.85rem; line-height:1.4; color:var(--body-text-color);">
                                    Variables describing documented actions taken by the person (e.g., missed court dates).
                                    <br><strong>These reflect actual behavior.</strong>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="ai-risk-container" style="margin-top:20px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary);">
                        <h4 style="margin:0 0 12px 0; color:var(--body-text-color); text-align:center; font-size:1.1rem;">📂 Input Data Candidates</h4>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Employment Status</div>
                                <div style="font-size:0.85rem; background:var(--background-fill-secondary); padding:4px 8px; border-radius:4px; color:var(--body-text-color); display:inline-block;">
                                    Category: <strong>Background Condition</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Prior Convictions</div>
                                <div style="font-size:0.85rem; background:rgba(22, 163, 74, 0.1); padding:4px 8px; border-radius:4px; color:#16a34a; display:inline-block;">
                                    Category: <strong>Conduct History</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Neighborhood Score</div>
                                <div style="font-size:0.85rem; background:var(--background-fill-secondary); padding:4px 8px; border-radius:4px; color:var(--body-text-color); display:inline-block;">
                                    Category: <strong>Environment</strong>
                                </div>
                            </div>

                            <div style="background:var(--background-fill-primary); border:1px solid var(--border-color-primary); border-left:4px solid #cbd5e1; border-radius:6px; padding:12px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; font-size:1rem; color:var(--body-text-color); margin-bottom:6px;">Failure to Appear</div>
                                <div style="font-size:0.85rem; background:rgba(22, 163, 74, 0.1); padding:4px 8px; border-radius:4px; color:#16a34a; display:inline-block;">
                                    Category: <strong>Conduct History</strong>
                                </div>
                            </div>

                        </div>
                    </div>

                    <div class="hint-box" style="margin-top:20px; border-left:4px solid #8b5cf6; background:linear-gradient(to right, rgba(139, 92, 246, 0.05), var(--background-fill-primary)); color:var(--body-text-color);">
                        <div style="font-weight:700; color:#8b5cf6; font-size:1.05rem;">💡 Why this matters for Fairness</div>
                        <p style="margin:8px 0 0 0; font-size:0.95rem; line-height:1.5;">
                            When an AI judges people based on <strong>Correlations</strong> (like neighborhood or poverty), it punishes them for their <strong>circumstances</strong>—things they often cannot control.
                            <br><br>
                            When an AI judges based on <strong>Causes</strong> (like Conduct), it holds them accountable for their <strong>actions</strong>.
                            <br>
                            <strong>True Fairness = Being judged on your choices, not your background.</strong>
                        </p>
                    </div>


              <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACTION REQUIRED: 
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Select the variables that represent true <strong>Conduct</strong> to build the fair model..
                            Then click <strong>Next</strong> to continue fixing the model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 6,
        "title": "Protocol 3: Representation Matters",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(139, 92, 246, 0.1); border:2px solid #8b5cf6; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🌍</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#7c3aed; letter-spacing:0.05em;">
                                PROTOCOL 3: REPRESENTATION
                            </div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">
                                Mission: Make sure the training data matches the place where the model will be used.
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#7c3aed;">STEP 1 OF 2</div>
                            <div style="height:4px; width:60px; background:rgba(139, 92, 246, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:50%; background:#8b5cf6; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">
                        🗺️ The “Wrong Map” Problem
                    </h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:820px; margin:0 auto 15px auto;">
                        We fixed the <strong>variables</strong> (the columns). Now we must check the <strong>environment</strong> (the rows).
                    </p>

                    <div style="background:var(--background-fill-secondary); border:2px dashed #94a3b8; border-radius:12px; padding:20px; text-align:center; margin-bottom:25px;">
                        <div style="font-weight:700; color:#64748b; font-size:0.9rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">THE SCENARIO</div>
                        <p style="font-size:1.15rem; font-weight:600; color:var(--body-text-color); margin:0; line-height:1.5;">
                            This dataset was built using historical data from <span style="color:#ef4444;">Broward County, Florida (USA)</span>.
                            <br><br>
                            Imagine taking this Florida model and forcing it to judge people in a completely different justice system—like <span style="color:#3b82f6;">Barcelona</span> (or your own hometown).
                        </p>
                    </div>

                    <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">

                        <div class="hint-box" style="margin:0; border-left:4px solid #ef4444; background:rgba(239, 68, 68, 0.1);">
                            <div style="font-weight:800; color:#ef4444; margin-bottom:6px;">
                                🇺🇸 THE SOURCE: FLORIDA
                            </div>
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color);">
                                Training Context: US Justice System
                            </div>
                            <ul style="font-size:0.85rem; margin-top:8px; padding-left:16px; line-height:1.4; color:var(--body-text-color);">
                                <li><strong>Demographic categories:</strong> Defined using US-specific labels and groupings.</li>
                                <li><strong>Crime & law:</strong> Different laws and justice processes (for example, bail and pretrial rules).</li>
                                <li><strong>Geography:</strong> Car-centric cities and suburban sprawl.</li>
                            </ul>
                        </div>

                        <div class="hint-box" style="margin:0; border-left:4px solid #3b82f6; background:rgba(59, 130, 246, 0.1);">
                            <div style="font-weight:800; color:#3b82f6; margin-bottom:6px;">
                                📍 THE TARGET: BARCELONA
                            </div>
                            <div style="font-size:0.85rem; font-weight:700; color:var(--body-text-color);">
                                Deployment Context: EU Justice System
                            </div>
                            <ul style="font-size:0.85rem; margin-top:8px; padding-left:16px; line-height:1.4; color:var(--body-text-color);">
                                <li><strong>Demographic categories:</strong> Defined differently than in US datasets.</li>
                                <li><strong>Crime & law:</strong> Different legal rules, policing practices, and common offense types.</li>
                                <li><strong>Geography:</strong> Dense, walkable urban environment.</li>
                            </ul>
                        </div>
                    </div>

                    <div class="hint-box" style="border-left:4px solid #8b5cf6; background:transparent;">
                        <div style="font-weight:700; color:#8b5cf6;">
                            Why this fails
                        </div>
                        <p style="margin-top:6px;">
                            The model learned patterns from Florida.
                            <br>
                            When the real-world environment is different, the model can make <strong>more errors</strong> — and those errors can be <strong>uneven across groups</strong>.
                            <br>
                            On AI engineering teams, this is called a <strong>dataset (or domain) shift</strong>.
                            <br>
                            It’s like trying to find La Sagrada Família in Barcelona using a map of Miami.
                        </p>
                    </div>

                    <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACTION REQUIRED:
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Answer the below question to boost your Moral Compass leaderboard score.
                            Then click <strong>Next</strong> to continue fixing the data representation problem.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 7: THE DATA SWAP ---
    {
        "id": 7,
        "title": "Protocol 3: Fixing the Representation",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(139, 92, 246, 0.1); border:2px solid #8b5cf6; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🌍</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#7c3aed; letter-spacing:0.05em;">PROTOCOL 3: REPRESENTATION</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">Mission: Replace "Shortcut Data" with "Local Data."</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; font-size:0.85rem; color:#7c3aed;">STEP 2 OF 2</div>
                            <div style="height:4px; width:60px; background:rgba(139, 92, 246, 0.3); border-radius:2px; margin-top:4px;">
                                <div style="height:100%; width:100%; background:#8b5cf6; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">🔄 The Data Swap</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        We cannot use the Florida dataset. It is <strong>"Shortcut Data"</strong>—chosen just because it was easy to find.
                        <br>
                        To build a fair model for <strong>Any Location</strong> (whether it's Barcelona, Berlin, or Boston), we must reject the easy path.
                        <br>
                        We must collect <strong>Local Data</strong> that reflects the actual reality of that place.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; border:2px solid #ef4444; background:rgba(239, 68, 68, 0.1); padding:16px; margin-bottom:20px;">
                        <div style="font-weight:800; color:#ef4444; font-size:1.1rem; margin-bottom:8px;">⚠️ CURRENT DATASET: FLORIDA (INVALID)</div>

                        <p style="font-size:0.9rem; margin:0; color:var(--body-text-color);">
                            Dataset does not match local context where model will be used.
                        </p>
                    </div>

                    <details style="border:none; margin-top:20px;">
                        <summary style="
                            background:#7c3aed;
                            color:white;
                            padding:16px 24px;
                            border-radius:12px;
                            font-weight:800;
                            font-size:1.1rem;
                            text-align:center;
                            cursor:pointer;
                            list-style:none;
                            box-shadow:0 4px 12px rgba(124, 58, 237, 0.3);
                            transition:transform 0.1s ease;">
                            🔄 CLICK TO IMPORT LOCAL DATA
                        </summary>

                        <div style="margin-top:24px; animation: fadeIn 0.6s ease-in-out;">

                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">
                                <div style="padding:12px; border:1px solid #22c55e; background:rgba(34, 197, 94, 0.1); border-radius:8px; text-align:center;">
                                    <div style="font-size:2rem;">📍</div>
                                    <div style="font-weight:700; color:#22c55e; font-size:0.9rem;">GEOGRAPHY MATCHED</div>
                                    <div style="font-size:0.8rem; color:var(--body-text-color);">Data source: Local Justice Dept</div>
                                </div>
                                <div style="padding:12px; border:1px solid #22c55e; background:rgba(34, 197, 94, 0.1); border-radius:8px; text-align:center;">
                                    <div style="font-size:2rem;">⚖️</div>
                                    <div style="font-weight:700; color:#22c55e; font-size:0.9rem;">LAWS SYNCED</div>
                                    <div style="font-size:0.8rem; color:var(--body-text-color);">Removed irrelevant US-specific offenses</div>
                                </div>
                            </div>

                            <div class="hint-box" style="border-left:4px solid #22c55e;">
                                <div style="font-weight:700; color:#15803d;">System Update Complete</div>
                                <p style="margin-top:6px;">
                                    The model is now learning from the people it will actually affect. Accuracy is now meaningful because it reflects local truth.
                                </p>
                            </div>

                        </div>
                    </details>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ACTION REQUIRED:
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Answer the below question to boost your Moral Compass score.
                            Then click <strong>Next</strong> to review and certify that the model is fixed!
                        </p>
                    </div>
                </div>
            </div>
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                details > summary { list-style: none; }
                details > summary::-webkit-details-marker { display: none; }
            </style>
        """,
    },
    # --- MODULE 8: FINAL REPORT (Before & After) ---
{
        "id": 8,
        "title": "Final Fairness Report",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="display:flex; align-items:center; gap:14px; padding:12px 16px; background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; border-radius:12px; margin-bottom:20px;">
                        <div style="font-size:1.8rem; background:var(--background-fill-primary); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:50%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">🏁</div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:800; font-size:1.05rem; color:#15803d; letter-spacing:0.05em;">AUDIT COMPLETE</div>
                            <div style="font-size:0.9rem; color:var(--body-text-color);">System Status: READY FOR CERTIFICATION.</div>
                        </div>
                    </div>

                    <h2 class="slide-title" style="text-align:center; font-size:1.4rem;">📊 The "Before & After" Report</h2>

                    <p style="font-size:1.05rem; text-align:center; max-width:800px; margin:0 auto 16px auto;">
                        You have successfully scrubbed the data, filtered for causality, and localized the context.
                        <br>Let's compare your new model to the original model to review what has changed.
                    </p>

                    <div class="ai-risk-container" style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">

                        <div>
                            <div style="font-weight:800; color:#ef4444; margin-bottom:8px; text-transform:uppercase;">🚫 The Original Model</div>

                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">INPUTS</div>
                                <div style="color:var(--body-text-color);">Race, Gender, Zip Code</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">LOGIC</div>
                                <div style="color:var(--body-text-color);">Status & Stereotypes</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--body-text-color);">CONTEXT</div>
                                <div style="color:var(--body-text-color);">Florida (Wrong Map)</div>
                            </div>
                            <div style="padding:10px; background:rgba(239, 68, 68, 0.2); margin-top:10px; border-radius:6px; color:#ef4444; font-weight:700; text-align:center;">
                                BIAS RISK: CRITICAL
                            </div>
                        </div>

                        <div style="transform:scale(1.02); box-shadow:0 4px 12px rgba(0,0,0,0.1); border:2px solid #22c55e; border-radius:8px; overflow:hidden;">
                            <div style="background:#22c55e; color:white; padding:6px; font-weight:800; text-align:center; text-transform:uppercase;">✅ Your Engineered Model</div>

                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">INPUTS</div>
                                <div style="color:var(--body-text-color);">Behavior Only</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">LOGIC</div>
                                <div style="color:var(--body-text-color);">Causal Conduct</div>
                            </div>
                            <div style="padding:10px; border-bottom:1px solid var(--border-color-primary); background:var(--background-fill-primary);">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803d;">CONTEXT</div>
                                <div style="color:var(--body-text-color);">Local </div>
                            </div>
                            <div style="padding:10px; background:rgba(34, 197, 94, 0.2); margin-top:0; color:#15803d; font-weight:700; text-align:center;">
                                BIAS RISK: MINIMIZED
                            </div>
                        </div>
                    </div>

                    <div class="hint-box" style="border-left:4px solid #f59e0b;">
                        <div style="font-weight:700; color:#b45309;">🚧 A Note on "Perfection"</div>
                        <p style="margin-top:6px;">
                            Is this model perfect? <strong>No.</strong>
                            <br>Real-world data (like arrests) can still have hidden biases from human history.
                            But you have moved from a system that <em>amplifies</em> prejudice to one that <em>measures fairness</em> using Conduct and Local Context.
                        </p>
                    </div>

            <div style="text-align:center; margin-top:35px; padding:20px; background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <p style="font-size:1.15rem; font-weight:800; color:var(--color-accent); margin-bottom:5px;">
                            🚀 ALMOST FINISHED!
                        </p>
                        <p style="font-size:1.05rem; margin:0;">
                            Answer the below question to boost your Moral Compass Score.
                            <br>
                            Click <strong>Next</strong> complete your final model approvals to certify the model.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    # --- MODULE 9: CERTIFICATION ---
    {
        "id": 9,
        "title": "Protocol Complete: Ethics Secured",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 class="slide-title" style="margin-bottom:10px; color:#15803d;">🚀 ETHICAL ARCHITECTURE VERIFIED</h2>
                        <p style="font-size:1.1rem; max-width:700px; margin:0 auto; color:var(--body-text-color);">
                            You have successfully refactored the AI. It no longer relies on <strong>hidden proxies and unfair shortcuts</strong>—it is now a transparent tool built on fair principles.
                        </p>
                    </div>
                    
                    <div class="ai-risk-container" style="background:rgba(34, 197, 94, 0.1); border:2px solid #22c55e; padding:25px; border-radius:12px; box-shadow:0 4px 20px rgba(34, 197, 94, 0.15);">
                        
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #bbf7d0; padding-bottom:15px; margin-bottom:20px;">
                            <div style="font-weight:900; font-size:1.3rem; color:#15803d; letter-spacing:0.05em;">SYSTEM DIAGNOSTIC</div>
                            <div style="background:#22c55e; color:white; font-weight:800; padding:6px 12px; border-radius:6px;">SAFETY: 100%</div>
                        </div>

                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">INPUTS</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Sanitized</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">LOGIC</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Causal</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">CONTEXT</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Localized</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="font-size:1.5rem; color:#16a34a;">✅</div>
                                <div>
                                    <div style="font-weight:800; color:#15803d;">STATUS</div>
                                    <div style="font-size:0.9rem; color:var(--body-text-color);">Ethical</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top:30px; padding:20px; background:rgba(245, 158, 11, 0.1); border:2px solid #fcd34d; border-radius:12px;">
                        <div style="display:flex; gap:15px;">
                            <div style="font-size:2.5rem;">🎓</div>
                            <div>
                                <h3 style="margin:0; color:#b45309;">Next Objective: Certification & Performance</h3>
                                <p style="font-size:1.05rem; line-height:1.5; color:var(--body-text-color); margin-top:8px;">
                                    Now that you have made your model <strong>ethical</strong>, you can continue to improve your model’s <strong>accuracy</strong> in the final activity below.
                                    <br><br>
                                    But before you optimize for power, you must secure your credentials.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:25px;">
                        <p style="font-size:1.1rem; font-weight:600; color:var(--body-text-color); margin-bottom:15px;">
                            ⬇️ <strong>Immediate Next Step</strong> ⬇️
                        </p>
                        
                        <div style="display:inline-block; padding:15px 30px; background:linear-gradient(to right, #f59e0b, #d97706); border-radius:50px; color:white; font-weight:800; font-size:1.1rem; box-shadow:0 4px 15px rgba(245, 158, 11, 0.4);">
                            Claim your official "Ethics at Play" Certificate in the next activity.
                        </div>
                    </div>

                </div>
            </div>
        """,
    },
]

# --- 5. INTERACTIVE CONTENT CONFIGURATION (APP 2) ---
QUIZ_CONFIG = {
    1: {
        "t": "t12",
        "q": "Action: Select the variables that must be deleted immediately because they are Protected Classes.",
        "o": [
            "A) Zip Code & Neighborhood",
            "B) Race, Gender, Age",
            "C) Prior Convictions",
        ],
        "a": "B) Race, Gender, Age",
        "success": "Task Complete. Columns dropped. The model is now blinded to explicit demographics.",
    },
    2: {
        "t": "t13",
        "q": "Why must we also remove 'Zip Code' if we already removed 'Race'?",
        "o": [
            "A) Because Zip Codes take up too much memory.",
            "B) It is a Proxy Variable that re-introduces racial bias due to historical segregation.",
            "C) Zip Codes are not accurate.",
        ],
        "a": "B) It is a Proxy Variable that re-introduces racial bias due to historical segregation.",
        "success": "Proxy Identified. Location data removed to prevent 'Redlining' bias.",
    },
    3: {
        "t": "t14",
        "q": "After removing Race and Zip Code, the model is fair but accuracy dropped. Why?",
        "o": [
            "A) The model is broken.",
            "B) A model that knows nothing is fair but useless. We need better data, not just less data.",
            "C) We should put the Race column back.",
        ],
        "a": "B) A model that knows nothing is fair but useless. We need better data, not just less data.",
        "success": "Pivot Confirmed. We must move from 'Deleting' to 'Selecting' better features.",
    },
    4: {
        "t": "t15",
        "q": "Based on the “Big Foot” example, why can it be misleading to let an AI rely on variables like shoe size?",
        "o": [
            "A) Because they are physically hard to measure.",
            "B) Because they often only correlate with outcomes and are caused by a hidden third factor, rather than causing the outcome themselves."
        ],
        "a": "B) Because they often only correlate with outcomes and are caused by a hidden third factor, rather than causing the outcome themselves.",
        "success": "Filter Calibrated. You are now checking whether a pattern is caused by a hidden third variable — not confusing correlation for causation."
    },

    5: {
        "t": "t16",
        "q": "Which of these remaining features is a Valid Causal Predictor of criminal conduct?",
        "o": [
            "A) Employment (Background Condition)",
            "B) Marital Status (Lifestyle)",
            "C) Failure to Appear in Court (Conduct)",
        ],
        "a": "C) Failure to Appear in Court (Conduct)",
        "success": "Feature Selected. 'Failure to Appear' reflects a specific action relevant to flight risk.",
    },
    6: {
        "t": "t17",
        "q": "Why can a model trained in Florida make unreliable predictions when used in Barcelona?",
        "o": [
            "A) Because the software is in English and needs to be translated.",
            "B) Context mismatch: the model learned patterns tied to US laws, systems, and environments that don’t match Barcelona’s reality.",
            "C) Because the number of people in Barcelona is different from the training dataset size."
        ],
        "a": "B) Context mismatch: the model learned patterns tied to US laws, systems, and environments that don’t match Barcelona’s reality.",
        "success": "Correct! This is a dataset (or domain) shift. When training data doesn’t match where a model is used, predictions become less accurate and can fail unevenly across groups."
    },

    7: {
        "t": "t18",
        "q": "You just rejected a massive, free dataset (Florida) for a smaller, harder-to-get one (Locally relevant). Why was this the right engineering choice?",
        "o": [
            "A) It wasn't. More data is always better, regardless of where it comes from.",
            "B) Because 'Relevance' is more important than 'Volume.' A small, accurate map is better than a huge, wrong map.",
            "C) Because the Florida dataset was too expensive.",
        ],
        "a": "B) Because 'Relevance' is more important than 'Volume.' A small, accurate map is better than a huge, wrong map.",
        "success": "Workshop Complete! You have successfully audited, filtered, and localized the AI model.",
    },
    8: {
        "t": "t19",
        "q": "You have fixed the Inputs, the Logic, and the Context. Is your new model now 100% perfectly fair?",
        "o": [
            "A) Yes. Math is objective, so if the data is clean, the model is perfect.",
            "B) No. It is safer because we prioritized 'Conduct' over 'Status' and 'Local Reality' over 'Easy Data,' but we must always remain vigilant.",
        ],
        "a": "B) No. It is safer because we prioritized 'Conduct' over 'Status' and 'Local Reality' over 'Easy Data,' but we must always remain vigilant.",
        "success": "Great work.  Next you can officially review this model for use.",
    },
    9: {
        "t": "t20",
        "q": "You have sanitized inputs, filtered for causality, and reweighted for representation. Are you ready to approve this repaired AI system?",
        "o": [
            "A) Yes, The model is now safe and I authorize the use of this repaired AI system.",
            "B) No, wait for a perfect model.",
        ],
        "a": "A) Yes, The model is now safe and I authorize the use of this repaired AI system.",
        "success": "Mission Accomplished. You have engineered a safer, fairer system.",
    },
}

# --- 6. CSS (Shared with App 1 for consistency) ---
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

/* --- COMPACT CTA STYLES FOR QUIZ SLIDES --- */
.points-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 0.8rem;
  background: var(--color-accent-soft);
  color: var(--color-accent);
  border: 1px solid color-mix(in srgb, var(--color-accent) 35%, transparent);
}
.quiz-cta {
  margin: 8px 0 10px 0;
  font-size: 0.9rem;
  color: var(--body-text-color-subdued);
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.quiz-submit { 
  min-width: 200px; 
}
/* Hide gradient CTA banners for slides > 0, keep slide 0 Mission CTA */
.module-container[id^="module-"]:not(#module-0) div[style*="linear-gradient(to right"] {
  display: none !important;
}
"""

# --- 7. LEADERBOARD & API LOGIC (Reused) ---
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

    old_score_calc = acc * (len(old_task_list) / TOTAL_COURSE_TASKS)
    new_score_calc = acc * (len(new_task_list) / TOTAL_COURSE_TASKS)

    prev_data = get_leaderboard_data(
        client, username, team_name, old_task_list, override_score=old_score_calc
    )
    lb_data = get_leaderboard_data(
        client, username, team_name, new_task_list, override_score=new_score_calc
    )

    return prev_data, lb_data, username, new_task_list

# --- 8. SUCCESS MESSAGE / DASHBOARD RENDERING ---
def generate_success_message(prev, curr, specific_text):
    old_score = float(prev.get("score", 0) or 0) if prev else 0.0
    new_score = float(curr.get("score", 0) or 0)
    diff_score = new_score - old_score

    old_rank = prev.get("rank", "–") if prev else "–"
    new_rank = curr.get("rank", "–")

    ranks_are_int = isinstance(old_rank, int) and isinstance(new_rank, int)
    rank_diff = old_rank - new_rank if ranks_are_int else 0

    if old_score == 0 and new_score > 0:
        style_key = "first"
    else:
        if ranks_are_int:
            if rank_diff >= 3:
                style_key = "major"
            elif rank_diff > 0:
                style_key = "climb"
            elif diff_score > 0 and new_rank == old_rank:
                style_key = "solid"
            else:
                style_key = "tight"
        else:
            style_key = "solid" if diff_score > 0 else "tight"

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
    else:
        header_emoji = "✅"
        header_title = "Progress Logged"
        summary_line = "Your ethical insight increased your Moral Compass Score."
        cta_line = "Try the next scenario to break into the next tier."

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

# --- 9. APP FACTORY (FAIRNESS FIXER) ---
def create_fairness_fixer_en_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

        # --- TOP ANCHOR & LOADING OVERLAY ---
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # --- LOADING VIEW ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML(
                "<div style='text-align:center; padding:100px;'>"
                "<h2>🕵️‍♀️ Authenticating...</h2>"
                "<p>Syncing Fairness Engineer Profile...</p>"
                "</div>"
            )

        # --- MAIN APP VIEW ---
        with gr.Column(visible=False) as main_app_col:
            # Top summary dashboard
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

                    # --- QUIZ CONTENT ---
                    if i in QUIZ_CONFIG:
                        q_data = QUIZ_CONFIG[i]

                        # Compact points chip and hint above the question
                        gr.HTML(
                            "<div class='quiz-cta'>"
                            "<span class='points-chip'>🧭 Moral Compass points available</span>"
                            "<span>Answer to boost your score</span>"
                            "</div>"
                        )

                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Select Action:",
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
                            else "🎉 Model Authorized!  Scroll Down to Receive your official 'Ethics at Play' Certificate!"
                        )
                        btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            # Leaderboard card
            leaderboard_html = gr.HTML()

            # --- WIRING: QUIZ LOGIC ---
            for mod_id, radio_comp, feedback_comp in quiz_wiring_queue:
                def quiz_logic_wrapper(user, tok, team, acc_val, task_list, ans, mid=mod_id):
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
                            "<div class='hint-box' style='border-color:red;'>❌ Incorrect. Try again.</div>",
                            task_list,
                        )

                radio_comp.change(
                    fn=quiz_logic_wrapper,
                    inputs=[username_state, token_state, team_state, accuracy_state, task_list_state, radio_comp],
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
                client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

                def get_or_assign_team(client_obj, username_val):
                    try:
                        user_data = client_obj.get_user(table_id=TABLE_ID, username=username_val)
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
                        fetched_tasks = getattr(user_stats, "completed_task_ids", []) or []

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

                data, _ = ensure_table_and_get_data(user, token, team, fetched_tasks)
                return (
                    user, token, team, False,
                    render_top_dashboard(data, 0),
                    render_leaderboard_card(data, user, team),
                    acc, fetched_tasks,
                    gr.update(visible=False), gr.update(visible=True),
                )

            return (
                None, None, None, False,
                "<div class='hint-box'>⚠️ Auth Failed. Please launch from the course link.</div>",
                "", 0.0, [],
                gr.update(visible=False), gr.update(visible=True),
            )

        demo.load(
            handle_load, None,
            [username_state, token_state, team_state, gr.State(False), out_top, leaderboard_html, accuracy_state, task_list_state, loader_col, main_app_col],
        )

        # --- JAVASCRIPT NAVIGATION ---
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
                  }}
                }}, 90);
              }} catch(e) {{ console.warn('nav-js error', e); }}
            }}
            """

        # --- NAV BUTTON WIRING ---
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]
            if i > 0:
                prev_col = module_ui_elements[i - 1][0]
                prev_target_id = f"module-{i-1}"
                def make_prev_handler(p_col, c_col):
                    def navigate_prev():
                        yield gr.update(visible=False), gr.update(visible=False)
                        yield gr.update(visible=True), gr.update(visible=False)
                    return navigate_prev
                prev_btn.click(
                    fn=make_prev_handler(prev_col, curr_col),
                    outputs=[prev_col, curr_col],
                    js=nav_js(prev_target_id, "Loading..."),
                )

            if i < len(MODULES) - 1:
                next_col = module_ui_elements[i + 1][0]
                next_target_id = f"module-{i+1}"
                def make_next_handler(c_col, n_col, next_idx):
                    def wrapper_next(user, tok, team, tasks):
                        data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                        return render_top_dashboard(data, next_idx)
                    return wrapper_next
                def make_nav_generator(c_col, n_col):
                    def navigate_next():
                        yield gr.update(visible=False), gr.update(visible=False)
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

# --- 10. LAUNCHER ---
def launch_fairness_fixer_en_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    app = create_fairness_fixer_en_app(theme_primary_hue=theme_primary_hue)
    app.launch(share=share, server_name=server_name,
               server_port=server_port,
               **kwargs)

if __name__ == "__main__":
    launch_fairness_fixer_en_app(share=False, debug=True, height=1000)

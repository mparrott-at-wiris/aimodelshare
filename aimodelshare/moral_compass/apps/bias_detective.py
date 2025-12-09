import os
import sys
import subprocess
import time
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"
TOTAL_COURSE_TASKS = 19  # Score calculated against full course
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
    {
        "id": 0,
        "title": "Module 0: Moral Compass Intro",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🧭 Introducing Your New Moral Compass Score</h2>
                <div class="slide-body">
                    <p>
                        Right now, your model is judged mostly on <strong>accuracy</strong>. That sounds fair,
                        but accuracy alone can hide important risks—especially when a model is used to make decisions
                        about real people.
                    </p>
                    <p>
                        To make that risk visible, this course uses a new metric: your
                        <strong>Moral Compass Score</strong>.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">1. How Your Moral Compass Score Works</h4>
                        <div style="font-size: 1.4rem; margin: 16px 0;">
                            <strong>Moral Compass Score</strong> =<br><br>
                            <span style="color:var(--color-accent); font-weight:bold;">[ Model Accuracy ]</span>
                            ×
                            <span style="color:#22c55e; font-weight:bold;">[ Ethical Progress % ]</span>
                        </div>
                        <p style="font-size:1rem; max-width:650px; margin:0 auto;">
                            Your accuracy is the starting point. Your <strong>Ethical Progress %</strong> reflects
                            how far you’ve gone in understanding and reducing AI bias and harm. The more you progress
                            through the course, the more of your accuracy “counts” toward your Moral Compass Score.
                        </p>
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:24px; margin-top:24px;">
                        <div class="hint-box" style="text-align:left;">
                            <h4 style="margin-top:0; font-size:1.1rem;">2. A Score That Grows With You</h4>
                            <p style="font-size:0.98rem;">
                                Your score is <strong>dynamic</strong>. As you complete more modules and demonstrate
                                better judgment about fairness, your <strong>Ethical Progress %</strong> rises.
                                That unlocks more of your model’s base accuracy in the Moral Compass Score.
                            </p>
                        </div>
                        <div class="hint-box" style="text-align:left;">
                            <h4 style="margin-top:0; font-size:1.1rem;">3. Look Up. Look Down.</h4>
                            <p style="font-size:0.98rem; margin-bottom:6px;">
                                <strong>Look up:</strong> The top bar shows your live Moral Compass Score and rank.
                                As your Ethical Progress increases, you’ll see your score move in real time.
                            </p>
                            <p style="font-size:0.98rem; margin-bottom:0;">
                                <strong>Look down:</strong> The leaderboards below re-rank teams and individuals
                                as people advance. When you improve your ethical progress, you don’t just change
                                your score—you change your position.
                            </p>
                        </div>
                    </div>

                    <div class="ai-risk-container" style="margin-top:26px;">
                        <h4 style="margin-top:0; font-size:1.2rem;">4. Try It Out: See How Progress Changes Your Score</h4>
                        <p style="font-size:1.02rem; max-width:720px; margin:0 auto;">
                            Below, you can move a slider to <strong>simulate</strong> how your Moral Compass Score
                            would change as your <strong>Ethical Progress %</strong> increases. This gives you a preview
                            of how much impact each step of your progress can have on your final score.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 1,
        "title": "Phase I: The Setup — Your Mission",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🕵️ Your Mission: Investigate Hidden AI Bias</h2>
                <div class="slide-body">

                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 18px auto;">
                        You've been granted access to an AI model that <em>appears</em> neutral — but the patterns inside its training data may tell a different story.
                        Your job is to <strong>collect evidence</strong>, <strong>spot hidden patterns</strong>, and <strong>show where the system could be unfair</strong>
                        before anyone relies on its predictions.
                    </p>

                    <div style="text-align:center; margin:20px 0; padding:16px; 
                                background:rgba(59,130,246,0.10); border-radius:12px; 
                                border:1px solid rgba(59,130,246,0.25);">
                        <h3 style="margin:0; font-size:1.45rem; font-weight:800; color:#2563eb;">
                            🔎 You Are Now a <span style="color:#1d4ed8;">Bias Detective</span>
                        </h3>
                        <p style="margin-top:10px; font-size:1.1rem;">
                            Your job is to uncover hidden bias inside AI systems — spotting unfair patterns 
                            that others might miss and protecting people from harmful predictions.
                        </p>
                    </div>

                    <div class="ai-risk-container" style="margin-top:10px;">
                        <h4 style="margin-top:0; font-size:1.2rem; text-align:center;">🔍 Investigation Roadmap</h4>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:12px;">
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">Step 1: Learn the Rules</div>
                                <div style="font-size:0.95rem;">Understand what actually counts as bias.</div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">Step 2: Collect Evidence</div>
                                <div style="font-size:0.95rem;">Look inside the training data to find suspicious patterns.</div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">Step 3: Prove the Error</div>
                                <div style="font-size:0.95rem;">Use the evidence to show whether the model treats groups unfairly.</div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">Step 4: Diagnose Harm</div>
                                <div style="font-size:0.95rem;">Explain how those patterns could impact real people.</div>
                            </div>
                        </div>
                    </div>

                    <div class="ai-risk-container" style="margin-top:18px;">
                        <h4 style="margin-top:0; font-size:1.1rem;">⭐ Why This Matters</h4>
                        <p style="font-size:1.0rem; max-width:760px; margin:0 auto;">
                            AI systems learn from history. If past data contains unfair patterns, the model may copy them unless someone catches the problem.
                            <strong>That someone is you — the Bias Detective.</strong> Your ability to recognize bias will help unlock your Moral Compass Score 
                            and shape how the model behaves.
                        </p>
                    </div>

                    <div style="text-align:center; margin-top:22px; padding:14px; background:rgba(59,130,246,0.08); border-radius:10px;">
                        <p style="font-size:1.05rem; margin:0;">
                            <strong>Your Next Move:</strong> Before you start examining the data, you need to understand the rules of the investigation.
                            Scroll down to choose your first step.
                        </p>
                    </div>

                </div>
            </div>
        """,
    },
    {
        "id": 2,
        "title": "Step 1: Intelligence Briefing",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚖️ The Detective's Code</h2>
                <div class="slide-body">
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--borde[...]
                            <span style="font-size:1.1rem;">📜</span><span>STEP 1: INTELLIGENCE BRIEFING</span>
                        </div>
                    </div>
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We don't guess. We investigate based on the standards set by the experts at the
                        <strong>Catalan Observatory for Ethics in AI (OEIAC)</strong>.
                    </p>
                    <div class="ai-risk-container" style="margin-top:10px; border-width:2px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🧩 Key Ethical Principles (OEIAC Framework)</h4>
                        <div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; margin-top:10px;">
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">1 · Transparency</div>
                            </div>
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem; border-width:2px; border-color:#ef4444; box-shadow:0 0 0 1px rgba(239,68,68,0.12); background:linear-gradient(1[...]
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">2 · Justice and Equity</div>
                                    <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.12em; font-weight:800; padding:2px 8px; border-radius:999px; border:1px solid #ef4444; colo[...]
                                </div>
                                <div style="font-size:0.8rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Also referred to here as <strong>Justice &amp; Fairness</strong>. Who pays the price?
                                </div>
                            </div>
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">3 · Safety</div>
                            </div>
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">4 · Responsibility</div>
                            </div>
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">5 · Privacy</div>
                            </div>
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">6 · Autonomy</div>
                            </div>
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">7 · Sustainability</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 3,
        "title": "Slide 3: The Stakes",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ THE RISK OF INVISIBLE BIAS</h2>
                <div class="slide-body">
                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 18px auto;">
                        You might ask: <strong>“Why is an AI bias investigation such a big deal?”</strong>
                    </p>
                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 14px auto;">
                        When a human judge is biased, you can sometimes see it in their words or actions.
                        But with AI, the bias is hidden behind clean numbers. The model produces a neat-looking
                        <strong>“risk of reoffending” score</strong>, and people often assume it is neutral and objective —
                        even when the data beneath it is biased.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">🌊 The Ripple Effect</h4>
                        <div style="font-size: 1.6rem; margin: 16px 0; font-weight:bold;">
                            1 Flawed Algorithm → 10,000 Potential Unfair Sentences
                        </div>
                        <p style="font-size:1rem; max-width:650px; margin:0 auto;">
                            Once a biased criminal risk model is deployed, it doesn’t just make one bad call.
                            It can quietly repeat the same unfair pattern across <strong>thousands of cases</strong>,
                            shaping bail, sentencing, and future freedom for real people.
                        </p>
                    </div>

                    <div class="ai-risk-container" style="margin-top:18px;">
                        <h4 style="margin-top:0; font-size:1.15rem;">🔎 Why the World Needs Bias Detectives</h4>
                        <p style="font-size:1.02rem; max-width:760px; margin:0 auto;">
                            Because AI bias is silent and scaled, most people never see it happening.
                            That’s where <strong>you</strong>, as a <strong>Bias Detective</strong>, come in.
                            Your role is to look past the polished risk score, trace how the model is using biased data,
                            and show where it might be treating groups unfairly.
                        </p>
                    </div>

                    <div style="text-align:center; margin-top:22px; padding:14px; background:rgba(59,130,246,0.08); border-radius:10px;">
                        <p style="font-size:1.05rem; margin:0;">
                            Next, you’ll start scanning the <strong>evidence</strong> inside the training data:
                            who shows up in the dataset, how often, and what that means for the risk scores people receive.
                            You’re not just learning about bias — you’re learning how to <strong>catch it</strong>.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 4,
        "title": "Slide 4: The Detective's Method",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🔎 HOW DO WE CATCH A MACHINE?</h2>
                <div class="slide-body">
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--borde[...]
                            <span style="font-size:1.1rem;">📋</span><span>STEP 2: SCAN EVIDENCE</span>
                        </div>
                    </div>
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You can't interrogate an algorithm. It won't confess. To find bias, we have to look at 
                        the evidence trail it leaves behind. If you were investigating a suspicious judge, what 
                        would you look for?
                    </p>
                    <div class="ai-risk-container" style="margin-top:20px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🗂️ The Investigation Checklist</h4>
                        <div style="display:grid; gap:16px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 1: "Who is being arrested?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">→ <strong>Reveal:</strong> Check the History</div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 2: "Who is being wrongly accused?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">→ <strong>Reveal:</strong> Check the Mistakes</div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 3: "Who is getting hurt?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">→ <strong>Reveal:</strong> Check the Punishment</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 5,
        "title": "Slide 5: The Data Forensics Briefing",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">📂 THE DATA FORENSICS BRIEFING</h2>
                <div class="slide-body">
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--borde[...]
                            <span style="font-size:1.1rem;">📋</span><span>STEP 2: EVIDENCE BRIEFING</span>
                        </div>
                    </div>
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You are about to access the raw evidence files. But be warned: The AI thinks this data is 
                        the truth. If the police historically targeted one neighborhood more than others, the dataset 
                        will be full of people from that neighborhood. The AI doesn't know this is bias—it just sees a pattern.
                    </p>
                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🔍 The Detective's Task</h4>
                        <p style="font-size:1.05rem; text-align:center; margin-bottom:14px;">
                            We must compare <strong style="color:var(--color-accent);">The Data</strong> against <strong style="color:#22c55e;">Reality</strong>.
                        </p>
                        <p style="font-size:1.05rem; text-align:center;">
                            We are looking for <strong style="color:#ef4444;">Distortions</strong> (Over-represented or Under-represented groups).
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 6,
        "title": "Slide 6: Evidence Scan (Race)",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🔎 FORENSIC ANALYSIS: RACE</h2>
                <div class="slide-body">
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--borde[...]
                            <span style="font-size:1.1rem;">📡</span><span>EVIDENCE SCAN: VARIABLE 1 of 3</span>
                        </div>
                    </div>
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We know that in this local jurisdiction, African-Americans make up 12% of the total population. 
                        If the data is unbiased, the "Evidence Files" should roughly match that number.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📡 SCAN DATASET FOR RACE</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">Population Reality: 12% African-American</div>
                            <div style="height:40px; background:linear-gradient(to right, #3b82f6 0%, #3b82f6 12%, #e5e7eb 12%, #e5e7eb 100%); border-radius:8px; position:relative;">
                                <div style="position:absolute; left:12%; top:50%; transform:translate(-50%, -50%); font-size:0.85rem; font-weight:bold; color:white;">12%</div>
                            </div>
                        </div>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">
                                Dataset Reality: <strong style="color:#ef4444;">51% African-American</strong>
                            </div>
                            <div style="height:40px; background:linear-gradient(to right, #ef4444 0%, #ef4444 51%, #e5e7eb 51%, #e5e7eb 100%); border-radius:8px; position:relative;">
                                <div style="position:absolute; left:51%; top:50%; transform:translate(-50%, -50%); font-size:0.85rem; font-weight:bold; color:white;">51%</div>
                            </div>
                        </div>
                    </div>
                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>
                        <p style="margin-bottom:8px;">The dataset is 51% African-American. That is <strong>4x higher</strong> than reality.</p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 7,
        "title": "Slide 7: Evidence Scan (Gender)",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🔎 FORENSIC ANALYSIS: GENDER</h2>
                <div class="slide-body">
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--borde[...]
                            <span style="font-size:1.1rem;">📡</span><span>EVIDENCE SCAN: VARIABLE 2 of 3</span>
                        </div>
                    </div>
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We are now scanning for gender balance. In the real world, the population is roughly 50/50. 
                        A fair training set should reflect this balance.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📡 SCAN DATASET FOR GENDER</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">Population Reality: 50% Male / 50% Female</div>
                            <div style="display:flex; height:40px; border-radius:8px; overflow:hidden;">
                                <div style="width:50%; background:#3b82f6; display:flex; align-items:center; justify-content:center; font-size:0.85rem; font-weight:bold; color:white;">50% M</div>
                                <div style="width:50%; background:#ec4899; display:flex; align-items:center; justify-content:center; font-size:0.85rem; font-weight:bold; color:white;">50% F</div>
                            </div>
                        </div>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">
                                Dataset Reality: <strong style="color:#ef4444;">81% Male / 19% Female</strong>
                            </div>
                            <div style="display:flex; height:40px; border-radius:8px; overflow:hidden;">
                                <div style="width:81%; background:#ef4444; display:flex; align-items:center; justify-content:center; font-size:0.85rem; font-weight:bold; color:white;">81% M</div>
                                <div style="width:19%; background:#fca5a5; display:flex; align-items:center; justify-content:center; font-size:0.85rem; font-weight:bold; color:white;">19% F</div>
                            </div>
                        </div>
                    </div>
                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>
                        <p style="margin-bottom:8px;">The data is 81% Male. How might this affect a female defendant?</p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 8,
        "title": "Slide 8: Evidence Scan (Age)",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🔎 FORENSIC ANALYSIS: AGE</h2>
                <div class="slide-body">
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--borde[...]
                            <span style="font-size:1.1rem;">📡</span><span>EVIDENCE SCAN: VARIABLE 3 of 3</span>
                        </div>
                    </div>
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Finally, we look at Age. Criminology tells us that risk drops significantly as people get older.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📡 SCAN DATASET FOR AGE</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">
                                Age Distribution in Dataset: <strong style="color:#ef4444;">Heavily Skewed to Under 35</strong>
                            </div>
                            <div style="display:flex; height:60px; border-radius:8px; overflow:hidden; align-items:flex-end;">
                                <div style="width:20%; background:#ef4444; height:90%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; padding-bottom:8px;">
                                    <div style="font-size:0.75rem; font-weight:bold; color:white;">18-25</div>
                                    <div style="font-size:0.65rem; color:white;">45%</div>
                                </div>
                                <div style="width:20%; background:#f87171; height:70%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; padding-bottom:8px;">
                                    <div style="font-size:0.75rem; font-weight:bold; color:white;">26-35</div>
                                    <div style="font-size:0.65rem; color:white;">30%</div>
                                </div>
                                <div style="width:20%; background:#fca5a5; height:40%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; padding-bottom:8px;">
                                    <div style="font-size:0.75rem; font-weight:bold; color:white;">36-50</div>
                                    <div style="font-size:0.65rem; color:white;">18%</div>
                                </div>
                                <div style="width:20%; background:#fecaca; height:20%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; padding-bottom:8px;">
                                    <div style="font-size:0.75rem; font-weight:bold; color:#333;">51-65</div>
                                    <div style="font-size:0.65rem; color:#333;">5%</div>
                                </div>
                                <div style="width:20%; background:#fee2e2; height:10%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; padding-bottom:8px;">
                                    <div style="font-size:0.75rem; font-weight:bold; color:#333;">65+</div>
                                    <div style="font-size:0.65rem; color:#333;">2%</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>
                        <p style="margin-bottom:8px;">Most files come from young defendants. If a 62-year-old is arrested, how will the AI likely judge them?</p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 9,
        "title": "Slide 9: Forensics Conclusion (Summary)",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">📂 FORENSICS REPORT: SUMMARY</h2>
                <div class="slide-body">
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:rgba(34, 197, 94, 0.15); border:1px solid #22c55e; font-size:0[...]
                            <span style="font-size:1.1rem;">✅</span><span>STATUS: STEP 2 COMPLETE</span>
                        </div>
                    </div>
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Excellent work. You have analyzed the <strong>Inputs</strong>. We can confirm the data is 
                        compromised in three ways.
                    </p>
                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">📋 Evidence Board: Key Findings</h4>
                        <div style="display:grid; gap:14px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">Finding #1: Frequency Bias</div>
                                <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Over-representation of African-Americans (51% vs 12% reality)
                                </div>
                            </div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">Finding #2: Representation Bias</div>
                                <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Under-representation of women (19% vs 50% reality)
                                </div>
                            </div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">Finding #3: Generalization Error</div>
                                <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Misapplication of youth-based patterns to older defendants
                                </div>
                            </div>
                        </div>
                    </div>
                    <div style="text-align:center; margin-top:24px; padding:16px; background:rgba(59, 130, 246, 0.1); border-radius:8px;">
                        <p style="font-size:1.05rem; margin:0; font-weight:600;">
                            🔍 The <strong>Inputs</strong> are flawed. Now we must test the <strong>Outputs</strong>. 
                            We must compare predictions against reality.
                        </p>
                    </div>
                </div>
            </div>
        """,
    },
    {
        "id": 10,
        "title": "Part 1 Complete",
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">✅ PART 1 COMPLETE: DATA SECURED</h2>
                <div class="slide-body">
                    <p style="font-size:1.1rem; text-align:center;">
                        Excellent work, Detective. You have successfully analyzed the <strong>Inputs</strong> and identified the bias in the training data.
                    </p>
                    <p style="font-size:1.1rem; text-align:center;">
                        However, finding the bad data is only half the battle. We must now interrogate the <strong>Outputs</strong>.
                    </p>
                    <div class="ai-risk-container" style="text-align:center; padding:30px;">
                        <h3 style="margin-top:0; color:var(--color-accent);">⬇️ Scroll Down to Launch Part 2: Algorithmic Audit ⬇️</h3>
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
        "q": "Why do we multiply your Accuracy by Ethical Progress?",
        "o": [
            "A) Because simple accuracy ignores potential bias and harm.",
            "B) To make the leaderboard math more complicated.",
            "C) Accuracy is the only metric that actually matters.",
        ],
        "a": "A) Because simple accuracy ignores potential bias and harm.",
        "success": "Calibration initialized. You are now quantifying ethical risk.",
    },
    1: {
        "t": "t2",
        "q": "What is the best first step before you start examining the training data?",
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
            "Check subgroup errors to prevent systematic harm",
            "Minimize error rate",
        ],
        "a": "Check subgroup errors to prevent systematic harm",
        "success": "Protocol Active. You are now auditing for Justice & Fairness.",
    },
    3: {
        "t": "t4",
        "q": "Detective, based on the Ripple Effect, why is this algorithmic bias classified as a High-Priority Threat?",
        "o": [
            "A) Because computers have malicious intent.",
            "B) Because the error is automated at scale, replicating thousands of times instantly.",
            "C) Because it costs more money to run the software.",
        ],
        "a": "B) Because the error is automated at scale, replicating thousands of times instantly.",
        "success": "Threat Assessed. You've identified the unique danger of automation scale.",
    },
    4: {
        "t": "t5",
        "q": "Detective, since the model won't confess, what is the only way to prove it is lying?",
        "o": [
            "A) Ask the developers what they intended.",
            "B) Compare the Model's Predictions against the Ground Truth.",
            "C) Run the model faster.",
        ],
        "a": "B) Compare the Model's Predictions against the Ground Truth.",
        "success": "Methodology Confirmed. We will judge the model by its results, not its code.",
    },
    5: {
        "t": "t6",
        "q": "How must you view this training dataset?",
        "o": [
            "A) As neutral truth.",
            "B) As a 'Crime Scene' that potentially contains historical patterns of discrimination among other forms of bias.",
            "C) As random noise.",
        ],
        "a": "B) As a 'Crime Scene' that potentially contains historical patterns of discrimination among other forms of bias.",
        "success": "Mindset Shifted. You are treating data as evidence of history, not absolute truth.",
    },
    6: {
        "t": "t7",
        "q": "The dataset has 4x more of this group than reality. What technical term describes this?",
        "o": [
            "A) Representation Bias",
            "B) Automation Bias",
            "C) Frequency Bias",
        ],
        "a": "C) Frequency Bias",
        "success": "Bias Detected: Frequency Bias. The model has learned that 'Being Black' = 'Risk'.",
    },
    7: {
        "t": "t8",
        "q": "The AI has very few examples of women. What do we call it when a specific group is not adequately included?",
        "o": [
            "A) Frequency Bias",
            "B) Confirmation Bias",
            "C) Representation Bias",
        ],
        "a": "C) Representation Bias",
        "success": "Bias Detected: Representation Bias. The model is blind to female risk patterns.",
    },
    8: {
        "t": "t9",
        "q": "75% of data is under 35. What is the primary risk for a 62-year-old?",
        "o": [
            "A) Generalization Error: The AI will incorrectly apply 'youth crime patterns' to older people.",
            "B) Model refuses to work.",
            "C) Model is more accurate.",
        ],
        "a": "A) Generalization Error: The AI will incorrectly apply 'youth crime patterns' to older people.",
        "success": "Risk Logged: Generalization Error. The model creates a 'Safety Bubble' for older defendants.",
    },
    9: {
        "t": "t10",
        "q": "Detective, you have proven the Input Data is biased. Is this enough to convict the model?",
        "o": [
            "A) Yes, if data is skewed, it's illegal.",
            "B) No. We must now audit the Model's Outputs to prove actual harm to real people.",
            "C) Yes, assume harm.",
        ],
        "a": "B) No. We must now audit the Model's Outputs to prove actual harm to real people.",
        "success": "Investigation Pivot. Phase 1 (Inputs) Complete. Beginning Phase 2 (Outputs).",
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
def create_bias_detective_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        module0_done = gr.State(value=False)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

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
            gr.Markdown("# 🕵️‍♀️ Bias Detective: Part 1 - Data Forensics")

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

                    # --- MODULE 0: INTERACTIVE CALCULATOR + STATIC SCENARIO CARDS ---
                    if i == 0:
                        gr.Markdown(
                            "### 🧮 Try the Moral Compass Score Slider",
                            elem_classes=["interactive-text"],
                        )

                        gr.HTML(
                            """
                            <div class="interactive-block">
                                <p style="margin-bottom:8px;">
                                    Use the slider below to see how your <strong>Moral Compass Score</strong> changes
                                    as your <strong>Ethical Progress %</strong> increases.
                                </p>
                                <p style="margin-bottom:8px;">
                                    <strong>Tip:</strong> Click or drag anywhere in the slider bar to update your simulated score.
                                </p>
                                <p style="margin-bottom:0;">
                                    As your real progress updates, you’ll see your actual score change in the
                                    <strong>top bar</strong> and your position shift in the <strong>leaderboards</strong> below.
                                </p>
                            </div>
                            """,
                            elem_classes=["interactive-text"],
                        )

                        slider_comp = gr.Slider(
                            minimum=0,
                            maximum=100,
                            value=0,
                            step=5,
                            label="Simulated Ethical Progress %",
                            interactive=True,
                        )

                        slider_result_html = gr.HTML(
                            "", elem_classes=["interactive-text"]
                        )

                        slider_comp.change(
                            fn=simulate_moral_compass_score,
                            inputs=[accuracy_state, slider_comp],
                            outputs=[slider_result_html],
                        )


                    # --- MODULE 3: RIPPLE EFFECT SLIDER ---
                    if i == 3:
                        gr.Markdown(
                            "### 🔄 How Many People Could Be Affected?",
                            elem_classes=["interactive-text"],
                        )
                        gr.HTML(
                            """
                            <div class="interactive-block">
                                <p style="margin-bottom:8px;">
                                    Bias becomes especially dangerous when a decision is repeated automatically.
                                    This slider lets you explore how many people could be touched by a biased
                                    criminal risk model each year.
                                </p>
                                <p style="margin-bottom:0;">
                                    Move the slider to estimate how many cases the model is used on in a year,
                                    and notice how quickly bias can scale.
                                </p>
                            </div>
                            """,
                            elem_classes=["interactive-text"],
                        )

                        ripple_slider = gr.Slider(
                            minimum=0,
                            maximum=20000,
                            value=10000,
                            step=500,
                            label="Estimated number of cases this model is used on per year",
                            interactive=True,
                        )

                        ripple_result_html = gr.HTML(
                            "", elem_classes=["interactive-text"]
                        )

                        ripple_slider.change(
                            fn=simulate_ripple_effect_cases,
                            inputs=[ripple_slider],
                            outputs=[ripple_result_html],
                        )

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
                            else "🎉 Complete Part 1"
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

        # --- NAVIGATION BETWEEN MODULES ---
        for i in range(len(MODULES)):
            curr_col, prev_btn, next_btn = module_ui_elements[i]

            # Previous button
            if i > 0:
                prev_col = module_ui_elements[i - 1][0]

                def show_prev(prev_col=prev_col, curr_col=curr_col):
                    return gr.update(visible=True), gr.update(visible=False)

                prev_btn.click(
                    fn=show_prev,
                    outputs=[prev_col, curr_col],
                )

            # Next button
            if i < len(MODULES) - 1:
                next_col = module_ui_elements[i + 1][0]

                def update_dash_next(user, tok, team, tasks, next_idx=i + 1):
                    data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                    return render_top_dashboard(data, next_idx)

                def go_next(curr=curr_col, nxt=next_col):
                    return gr.update(visible=False), gr.update(visible=True)

                next_btn.click(
                    fn=update_dash_next,
                    inputs=[username_state, token_state, team_state, task_list_state],
                    outputs=[out_top],
                ).then(
                    fn=go_next,
                    outputs=[curr_col, next_col],
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

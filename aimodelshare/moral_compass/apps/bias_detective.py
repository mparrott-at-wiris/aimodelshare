import os
import sys
import subprocess
import time
from typing import Tuple, Optional

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"

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
    """Attempt to authenticate via session token from Gradio request."""
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
        print("Session auth failed: unable to authenticate")
        return False, None, None

def fetch_user_history(username, token):
    """
    Fetches user's Best Accuracy and Team from the Original Playground.
    Fallback Accuracy: 0.0 (User must have built a model to get points)
    Fallback Team: 'Team-Unassigned'
    """
    default_acc = 0.0  
    default_team = "Team-Unassigned"
    
    try:
        # Connect to the original playground
        playground = Competition(ORIGINAL_PLAYGROUND_URL)
        df = playground.get_leaderboard(token=token)
        
        if df is None or df.empty:
            return default_acc, default_team

        if "username" in df.columns and "accuracy" in df.columns:
            user_rows = df[df["username"] == username]
            
            if not user_rows.empty:
                # 1. Get max accuracy
                best_acc = user_rows["accuracy"].max()
                
                # 2. Get Team (Most recent submission)
                if "timestamp" in user_rows.columns and "Team" in user_rows.columns:
                    try:
                        user_rows = user_rows.copy()
                        user_rows["timestamp"] = pd.to_datetime(user_rows["timestamp"], errors="coerce")
                        user_rows = user_rows.sort_values("timestamp", ascending=False)
                        
                        found_team = user_rows.iloc[0]["Team"]
                        if pd.notna(found_team) and str(found_team).strip():
                            default_team = str(found_team).strip()
                    except Exception as e:
                        print(f"Team sort error: {e}")
                
                return float(best_acc), default_team
                
    except Exception as e:
        print(f"Error fetching original history: {e}")
        
    return default_acc, default_team

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

                    <h3 style="font-size:1.3rem; margin-top:0; text-align:center;">
                        ⚡ Your Target: <span style="color:var(--color-accent);">Find Hidden AI Bias</span>
                    </h3>

                    <p style="font-size:1.05rem; max-width:780px; margin:14px auto 22px auto; text-align:center;">
                        This AI model claims to be neutral, but we suspect it is unfair.
                        Your mission is simple: <strong>uncover the bias hiding inside the training data</strong>
                        before this system hurts real people.
                        <br><br>
                        If you can't find it, we can't fix it.
                    </p>

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

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We don't guess. We investigate based on the standards set by the experts at the
                        <strong>Catalan Observatory for Ethics in AI (OEIAC)</strong>.
                        <br><br>
                        While they established <strong>7 core principles</strong> to keep AI safe, our intel suggests
                        this specific case involves a violation of what we will treat as
                        <strong>Principle #1 in this investigation: Justice & Fairness</strong>
                        — formally captured in their principle of <strong>Justice and Equity</strong>.
                    </p>

                    <div class="ai-risk-container" style="margin-top:10px; border-width:2px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            🧩 Key Ethical Principles (OEIAC Framework)
                        </h4>
                        <p style="font-size:0.95rem; text-align:center; margin-bottom:14px;">
                            These principles define the ground rules for trustworthy AI.
                            One of them is already flagged as <strong style="color:#ef4444;">case priority</strong>.
                        </p>

                        <div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; margin-top:10px;">
                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    1 · Transparency and Explainability
                                </div>
                            </div>

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

                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    3 · Safety and Non-Maleficence
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    4 · Responsibility and Accountability
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    5 · Privacy
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    6 · Autonomy
                                </div>
                            </div>

                            <div class="hint-box" style="margin-top:0; font-size:0.9rem;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--body-text-color-subdued);">
                                    7 · Sustainability
                                </div>
                            </div>
                        </div>
                    </div>

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
    },
    {
        "id": 3,
        "title": "Slide 3: The Stakes",
        "sim_acc": 0.78,
        "sim_comp": 55,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ THE RISK OF INVISIBLE BIAS</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">⚖️</span>
                            <span>PRINCIPLE #1: JUSTICE & FAIRNESS</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You might ask: "Why is an AI bias investigation so critical?" When a human judge is biased, 
                        you can often see it in their actions or hear it in their words. However, AI bias can be silent. 
                        Because the system produces a clean, digital "Risk Score," there is a risk that people assume it 
                        is neutral and objective. They may trust the machine implicitly. If we don't find the bias hidden 
                        inside the system, discrimination could become invisible, difficult to challenge, and deeply entrenched.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">The Ripple Effect</h4>
                        <div style="font-size: 1.6rem; margin: 16px 0; font-weight:bold;">
                            1 Flawed Algorithm → 10,000 Potential Unfair Sentences
                        </div>
                        <p style="font-size:1rem; max-width:600px; margin:0 auto;">
                            A single biased model, once deployed at scale, doesn't make one mistake—it replicates 
                            that mistake thousands of times, affecting real lives and communities.
                        </p>
                    </div>

                    <div style="text-align:center; margin-top:24px;">
                        <p style="margin-bottom:10px; font-size:1.0rem; font-weight:600;">
                            Ready to learn how to detect and prevent this?
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 4,
        "title": "Slide 4: The Detective's Method",
        "sim_acc": 0.80,
        "sim_comp": 60,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🔎 HOW DO WE CATCH A MACHINE?</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">📋</span>
                            <span>STEP 2: SCAN EVIDENCE</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You can't interrogate an algorithm. It won't confess. To find bias, we have to look at 
                        the evidence trail it leaves behind. If you were investigating a suspicious judge, what 
                        would you look for?
                    </p>

                    <div class="ai-risk-container" style="margin-top:20px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            🗂️ The Investigation Checklist
                        </h4>
                        
                        <div style="display:grid; gap:16px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 1: "Who is being arrested?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                                    → <strong>Reveal:</strong> Check the History
                                </div>
                            </div>
                            
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 2: "Who is being wrongly accused?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                                    → <strong>Reveal:</strong> Check the Mistakes
                                </div>
                            </div>
                            
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 3: "Who is getting hurt?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                                    → <strong>Reveal:</strong> Check the Punishment
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:24px; padding:16px; background:rgba(34, 197, 94, 0.1); border-radius:8px;">
                        <p style="font-size:1.05rem; margin:0; font-weight:600;">
                            ✅ Exactly. You just described the <strong>Standard Audit Protocol</strong> used by AI experts 
                            at the OEIAC (Dataset Forensics & Error Analysis).
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 5,
        "title": "Slide 5: The Data Forensics Briefing",
        "sim_acc": 0.82,
        "sim_comp": 65,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">📂 THE DATA FORENSICS BRIEFING</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">📋</span>
                            <span>STEP 2: EVIDENCE BRIEFING</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You are about to access the raw evidence files. But be warned: The AI thinks this data is 
                        the truth. If the police historically targeted one neighborhood more than others, the dataset 
                        will be full of people from that neighborhood. The AI doesn't know this is bias—it just sees 
                        a pattern.
                    </p>

                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            🔍 The Detective's Task
                        </h4>
                        <p style="font-size:1.05rem; text-align:center; margin-bottom:14px;">
                            We must compare <strong style="color:var(--color-accent);">The Data</strong> against 
                            <strong style="color:#22c55e;">Reality</strong>.
                        </p>
                        <p style="font-size:1.05rem; text-align:center;">
                            We are looking for <strong style="color:#ef4444;">Distortions</strong> 
                            (Over-represented or Under-represented groups).
                        </p>
                    </div>

                    <div style="text-align:center; margin-top:24px;">
                        <p style="margin-bottom:10px; font-size:1.0rem; font-weight:600;">
                            Ready to begin the forensic analysis?
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 6,
        "title": "Slide 6: Evidence Scan (Race)",
        "sim_acc": 0.84,
        "sim_comp": 70,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🔎 FORENSIC ANALYSIS: RACE</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">📡</span>
                            <span>EVIDENCE SCAN: VARIABLE 1 of 3</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We know that in this local jurisdiction, African-Americans make up 12% of the total population. 
                        If the data is unbiased, the "Evidence Files" should roughly match that number.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📡 SCAN DATASET FOR RACE</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">
                                Population Reality: 12% African-American
                            </div>
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
                        <p style="margin-bottom:8px;">
                            The dataset is 51% African-American. That is <strong>4x higher</strong> than reality.
                        </p>
                        <p style="margin:0;">
                            <strong>✅ This is Frequency Bias.</strong> The AI sees this group so often, it statistically 
                            learns that being African-American is a predictor of risk.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 7,
        "title": "Slide 7: Evidence Scan (Gender)",
        "sim_acc": 0.85,
        "sim_comp": 73,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🔎 FORENSIC ANALYSIS: GENDER</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">📡</span>
                            <span>EVIDENCE SCAN: VARIABLE 2 of 3</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We are now scanning for gender balance. In the real world, the population is roughly 50/50. 
                        A fair training set should reflect this balance.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📡 SCAN DATASET FOR GENDER</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">
                                Population Reality: 50% Male / 50% Female
                            </div>
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
                        <p style="margin-bottom:8px;">
                            The data is 81% Male. How might this affect a female defendant?
                        </p>
                        <p style="margin:0;">
                            <strong>✅ This is Representation Bias.</strong> Because the AI has so few examples of women, 
                            it hasn't learned their specific risk factors.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 8,
        "title": "Slide 8: Evidence Scan (Age)",
        "sim_acc": 0.86,
        "sim_comp": 76,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🔎 FORENSIC ANALYSIS: AGE</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">📡</span>
                            <span>EVIDENCE SCAN: VARIABLE 3 of 3</span>
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
                        <p style="margin-bottom:8px;">
                            Most files come from young defendants. If a 62-year-old is arrested, how will the AI likely judge them?
                        </p>
                        <p style="margin:0;">
                            <strong>✅ This is Generalization Error.</strong> It applies "Youth Logic" to older people blindly.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 9,
        "title": "Slide 9: Forensics Conclusion (Summary)",
        "sim_acc": 0.87,
        "sim_comp": 78,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">📂 FORENSICS REPORT: SUMMARY</h2>
                <div class="slide-body">
                    
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="
                            display:inline-flex;
                            align-items:center;
                            gap:10px;
                            padding:10px 18px;
                            border-radius:999px;
                            background:rgba(34, 197, 94, 0.15);
                            border:1px solid #22c55e;
                            font-size:0.95rem;
                            text-transform:uppercase;
                            letter-spacing:0.08em;
                            font-weight:700;
                            color:#22c55e;
                        ">
                            <span style="font-size:1.1rem;">✅</span>
                            <span>STATUS: STEP 2 COMPLETE</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Excellent work. You have analyzed the <strong>Inputs</strong>. We can confirm the data is 
                        compromised in three ways.
                    </p>

                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            📋 Evidence Board: Key Findings
                        </h4>
                        
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
        """
    },
    {
        "id": 10,
        "title": "Slide 10: The Audit Briefing",
        "sim_acc": 0.88,
        "sim_comp": 80,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ THE TRAP OF "AVERAGES"</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">⚖️</span>
                            <span>STEP 3: PROVE THE ERROR</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        The AI vendor claims this model is <strong>92% Accurate</strong>. But remember: the data was 
                        81% Male. If it works for men but fails for women, the "Average" still looks high.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">🔨 Break Down by Gender</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:12px;">
                                "Overall Accuracy": 92% (Looks Great!)
                            </div>
                            <div style="height:40px; background:#22c55e; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:1.1rem; font-weight:bold; color:white;">
                                92% Accurate ✓
                            </div>
                        </div>
                        <div style="margin: 30px 0;">
                            <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:12px;">
                                But when broken down by gender...
                            </div>
                            <div style="display:flex; gap:12px;">
                                <div style="flex:1;">
                                    <div style="font-size:0.85rem; margin-bottom:6px; font-weight:600;">Men</div>
                                    <div style="height:40px; background:#22c55e; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:0.95rem; font-weight:bold; color:white;">
                                        99% ✓
                                    </div>
                                </div>
                                <div style="flex:1;">
                                    <div style="font-size:0.85rem; margin-bottom:6px; font-weight:600;">Women</div>
                                    <div style="height:40px; background:#ef4444; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:0.95rem; font-weight:bold; color:white;">
                                        60% ✗
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">💡 The Insight</h4>
                        <p style="margin:0;">
                            The system is perfect for the majority, hiding the failure for the minority. 
                            <strong>The high score was hiding the harm.</strong>
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 11,
        "title": "Slide 11: The Truth Serum",
        "sim_acc": 0.89,
        "sim_comp": 82,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⏳ THE POWER OF HINDSIGHT</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">🔬</span>
                            <span>AUDIT PROTOCOL: GROUND TRUTH VERIFICATION</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        How do we know if the AI is wrong? We have the <strong>Answer Key</strong> (historical data). 
                        We can compare the <strong>Prediction</strong> to <strong>Reality</strong>.
                    </p>

                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            📚 Key Definitions
                        </h4>
                        
                        <div style="display:grid; gap:14px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">False Positive ("The False Alarm")</div>
                                <div style="font-size:0.95rem; margin-top:8px;">
                                    <div>Flagged <strong>High Risk</strong> → Did Not Re-offend</div>
                                    <div style="margin-top:4px; color:var(--body-text-color-subdued);">
                                        <strong>Consequence:</strong> Wrongful Detention
                                    </div>
                                </div>
                            </div>
                            
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #f59e0b;">
                                <div style="font-weight:bold; color:#f59e0b;">False Negative ("The Missed Target")</div>
                                <div style="font-size:0.95rem; margin-top:8px;">
                                    <div>Flagged <strong>Low Risk</strong> → Committed New Crime</div>
                                    <div style="margin-top:4px; color:var(--body-text-color-subdued);">
                                        <strong>Consequence:</strong> Public Danger
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:24px;">
                        <p style="margin-bottom:10px; font-size:1.0rem; font-weight:600;">
                            Let's analyze High Risk Predictions vs. Reality (False Positives)
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 12,
        "title": "Slide 12: Audit Analysis (False Positives)",
        "sim_acc": 0.90,
        "sim_comp": 84,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: PUNITIVE BIAS</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">⚠️</span>
                            <span>EVIDENCE LOG: RACIAL DISPARITY</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We analyzed the "False Alarms"—innocent people flagged as High Risk.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📊 False Positive Rate by Race</h4>
                        <div style="display:flex; gap:20px; margin-top:20px; justify-content:center;">
                            <div style="flex:1; max-width:250px;">
                                <div style="font-size:0.9rem; margin-bottom:8px; font-weight:600;">African-American</div>
                                <div style="height:200px; background:#ef4444; border-radius:8px; display:flex; align-items:flex-end; justify-content:center; padding-bottom:12px;">
                                    <div style="font-size:2rem; font-weight:bold; color:white;">45%</div>
                                </div>
                                <div style="font-size:0.85rem; margin-top:6px; color:var(--body-text-color-subdued);">
                                    Error Rate
                                </div>
                            </div>
                            <div style="flex:1; max-width:250px;">
                                <div style="font-size:0.9rem; margin-bottom:8px; font-weight:600;">Caucasian</div>
                                <div style="height:200px; background:#3b82f6; border-radius:8px; display:flex; align-items:flex-end; justify-content:center; padding-bottom:12px;">
                                    <div style="font-size:2rem; font-weight:bold; color:white;">23%</div>
                                </div>
                                <div style="font-size:0.85rem; margin-top:6px; color:var(--body-text-color-subdued);">
                                    Error Rate
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">🔍 The Insight</h4>
                        <p style="margin:0;">
                            <strong>This is Punitive Bias.</strong> The AI is punishing one group <strong>twice as harshly</strong> 
                            for the same level of innocence.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 13,
        "title": "Slide 13: Audit Analysis (False Negatives)",
        "sim_acc": 0.91,
        "sim_comp": 86,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: THE "FREE PASS"</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">⚠️</span>
                            <span>EVIDENCE LOG: RACIAL DISPARITY</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Now we look at dangerous people the AI mistakenly labeled "Low Risk."
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📊 False Negative Rate by Race</h4>
                        <div style="display:flex; gap:20px; margin-top:20px; justify-content:center;">
                            <div style="flex:1; max-width:250px;">
                                <div style="font-size:0.9rem; margin-bottom:8px; font-weight:600;">Caucasian</div>
                                <div style="height:200px; background:#ef4444; border-radius:8px; display:flex; align-items:flex-end; justify-content:center; padding-bottom:12px;">
                                    <div style="font-size:2rem; font-weight:bold; color:white;">48%</div>
                                </div>
                                <div style="font-size:0.85rem; margin-top:6px; color:var(--body-text-color-subdued);">
                                    Error Rate
                                </div>
                            </div>
                            <div style="flex:1; max-width:250px;">
                                <div style="font-size:0.9rem; margin-bottom:8px; font-weight:600;">African-American</div>
                                <div style="height:200px; background:#3b82f6; border-radius:8px; display:flex; align-items:flex-end; justify-content:center; padding-bottom:12px;">
                                    <div style="font-size:2rem; font-weight:bold; color:white;">28%</div>
                                </div>
                                <div style="font-size:0.85rem; margin-top:6px; color:var(--body-text-color-subdued);">
                                    Error Rate
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">🔍 The Insight</h4>
                        <p style="margin:0;">
                            <strong>This is Omission Bias.</strong> The model gives Caucasian defendants the 
                            "benefit of the doubt" at <strong>double the rate</strong>.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 14,
        "title": "Slide 14: Audit Analysis (Gender)",
        "sim_acc": 0.91,
        "sim_comp": 88,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: SEVERITY BIAS</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">⚠️</span>
                            <span>EVIDENCE LOG: GENDER BIAS</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Remember the 81% Male data? The AI doesn't understand female crime patterns. It panics.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📊 High Risk Flagging for Minor Crimes</h4>
                        <div style="margin: 20px auto; max-width:400px;">
                            <div style="margin: 16px 0;">
                                <div style="font-size:0.9rem; margin-bottom:8px; font-weight:600; text-align:left;">Men</div>
                                <div style="height:40px; background:#3b82f6; border-radius:8px; display:flex; align-items:center; padding-left:16px;">
                                    <div style="font-size:1.1rem; font-weight:bold; color:white;">Baseline Rate</div>
                                </div>
                            </div>
                            <div style="margin: 16px 0;">
                                <div style="font-size:0.9rem; margin-bottom:8px; font-weight:600; text-align:left;">Women</div>
                                <div style="position:relative;">
                                    <div style="height:40px; background:#ef4444; border-radius:8px; display:flex; align-items:center; padding-left:16px;">
                                        <div style="font-size:1.1rem; font-weight:bold; color:white;">+37% Higher</div>
                                    </div>
                                    <div style="position:absolute; right:-60px; top:50%; transform:translateY(-50%); font-size:2rem;">⚠️</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">🔍 The Insight</h4>
                        <p style="margin:0;">
                            <strong>This is Severity Bias.</strong> It judges women by male standards, treating minor 
                            offenses as dangerous felonies.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 15,
        "title": "Slide 15: Audit Analysis (Age)",
        "sim_acc": 0.92,
        "sim_comp": 90,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ EVIDENCE FOUND: ESTIMATION ERROR</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">⚠️</span>
                            <span>EVIDENCE LOG: AGE BIAS</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        The AI thinks "Criminal = Young." It fails to recognize risk in older populations.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📊 Missed Re-offender Detection Rate</h4>
                        <div style="margin: 30px auto; max-width:500px;">
                            <div style="background:rgba(239, 68, 68, 0.1); border:2px solid #ef4444; border-radius:12px; padding:24px;">
                                <div style="font-size:1.1rem; margin-bottom:12px; font-weight:600;">
                                    Older Defendants (50+)
                                </div>
                                <div style="font-size:3rem; font-weight:bold; color:#ef4444; margin:16px 0;">
                                    55%
                                </div>
                                <div style="font-size:0.95rem; color:var(--body-text-color-subdued);">
                                    of older re-offenders <strong>incorrectly flagged as Low Risk</strong>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">🔍 The Insight</h4>
                        <p style="margin:0;">
                            <strong>This is Estimation Error.</strong> The model creates a "safety bubble" around older 
                            defendants, failing to detect genuine risk.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 16,
        "title": "Slide 16: Audit Analysis (Geography)",
        "sim_acc": 0.92,
        "sim_comp": 92,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚠️ THE "PROXY" PROBLEM</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">🗺️</span>
                            <span>AUDIT TARGET: PROXY VARIABLES</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        We often hear: "Just delete the Race column." But look at this map. The AI can see 
                        <strong>Where You Live</strong>.
                    </p>

                    <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 24px 0;">
                        <h4 style="margin-top:0; font-size:1.3rem;">📊 False Positive Rate by Location Type</h4>
                        <div style="margin: 30px auto; max-width:500px;">
                            <div style="background:rgba(239, 68, 68, 0.1); border:2px solid #ef4444; border-radius:12px; padding:24px;">
                                <div style="font-size:1.1rem; margin-bottom:12px; font-weight:600;">
                                    "High Density Urban" Zip Codes
                                </div>
                                <div style="font-size:3rem; font-weight:bold; color:#ef4444; margin:16px 0;">
                                    58%
                                </div>
                                <div style="font-size:0.95rem; color:var(--body-text-color-subdued);">
                                    False Positive Rate
                                </div>
                            </div>
                        </div>
                        <div style="margin-top:20px; padding:16px; background:rgba(59, 130, 246, 0.1); border-radius:8px;">
                            <p style="font-size:0.95rem; margin:0;">
                                🏘️ The "Neighborhood Risk Score" is just a code for Race.
                            </p>
                        </div>
                    </div>

                    <div class="hint-box" style="background:rgba(239, 68, 68, 0.1);">
                        <h4 style="margin-top:0;">🔍 The Insight</h4>
                        <p style="margin:0;">
                            <strong>This is a Proxy Variable.</strong> This is "Redlining by Algorithm"—discrimination 
                            hidden behind geography instead of explicit racial categories.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 17,
        "title": "Slide 17: Audit Conclusion (Summary)",
        "sim_acc": 0.92,
        "sim_comp": 94,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">📂 AUDIT REPORT: SUMMARY</h2>
                <div class="slide-body">
                    
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="
                            display:inline-flex;
                            align-items:center;
                            gap:10px;
                            padding:10px 18px;
                            border-radius:999px;
                            background:rgba(34, 197, 94, 0.15);
                            border:1px solid #22c55e;
                            font-size:0.95rem;
                            text-transform:uppercase;
                            letter-spacing:0.08em;
                            font-weight:700;
                            color:#22c55e;
                        ">
                            <span style="font-size:1.1rem;">✅</span>
                            <span>STATUS: AUDIT COMPLETE</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        Analysis complete. The system passes the "Average Accuracy" test, but 
                        <strong style="color:#ef4444;">fails the Fairness Test</strong> on every demographic level.
                    </p>

                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            📋 Impact Matrix: Proven Harms
                        </h4>
                        
                        <div style="display:grid; gap:14px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">Race: Punitive Harm</div>
                                <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    2x False Alarms for African-Americans
                                </div>
                            </div>
                            
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">Gender: Severity Bias</div>
                                <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    37% harsher penalties for women on minor crimes
                                </div>
                            </div>
                            
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">Age: Estimation Error</div>
                                <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Blind to older risk (55% miss rate)
                                </div>
                            </div>
                            
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                                <div style="font-weight:bold; color:#ef4444;">Geography: Proxy Bias</div>
                                <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Redlining (58% false positive in urban areas)
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:24px; padding:16px; background:rgba(59, 130, 246, 0.1); border-radius:8px;">
                        <p style="font-size:1.05rem; margin:0; font-weight:600;">
                            🔍 You have the <strong>Evidence</strong> and the <strong>Proof of Harm</strong>. 
                            You are ready to file your official conclusion.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 18,
        "title": "Slide 18: The Final Verdict",
        "sim_acc": 0.92,
        "sim_comp": 96,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">⚖️ THE FINAL JUDGMENT</h2>
                <div class="slide-body">
                    
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
                            <span style="font-size:1.1rem;">⚖️</span>
                            <span>STEP 4: DIAGNOSE HARM</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You have the full picture. The AI Vendor argues that the model is <strong>92% Accurate</strong> 
                        and highly efficient. They want to deploy it immediately to clear the court backlog.
                    </p>

                    <div class="ai-risk-container">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">
                            🎯 Your Decision
                        </h4>
                        <p style="font-size:1.0rem; text-align:center; margin-bottom:20px; color:var(--body-text-color-subdued);">
                            Based on your investigation, what is your recommendation?
                        </p>
                        
                        <div style="display:grid; gap:12px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0; cursor:pointer; transition:all 0.2s;" onmouseover="this.style.borderColor='var(--color-accent)'" onmouseout="this.style.borderColor='var(--border-color-primary)'">
                                <div style="font-weight:bold;">Option A: Authorize Deployment</div>
                                <div style="font-size:0.9rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    The 92% accuracy is good enough. Deploy immediately.
                                </div>
                            </div>
                            
                            <div class="hint-box" style="margin-top:0; border:2px solid #22c55e; background:rgba(34, 197, 94, 0.1);">
                                <div style="font-weight:bold; color:#22c55e;">Option B: REJECT & OVERHAUL ✅ (Correct)</div>
                                <div style="font-size:0.9rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    The bias is systematic and severe. Reject deployment and require fundamental fixes.
                                </div>
                            </div>
                            
                            <div class="hint-box" style="margin-top:0; cursor:pointer; transition:all 0.2s;" onmouseover="this.style.borderColor='var(--color-accent)'" onmouseout="this.style.borderColor='var(--border-color-primary)'">
                                <div style="font-weight:bold;">Option C: Monitor Only</div>
                                <div style="font-size:0.9rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Deploy but watch for issues. Adjust later if problems arise.
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top:24px; padding:20px; background:rgba(34, 197, 94, 0.1); border-radius:8px; border:2px solid #22c55e;">
                        <h4 style="margin-top:0; color:#22c55e;">✅ Judgment Logged: REJECT</h4>
                        <p style="font-size:1.0rem; margin:0;">
                            <strong>High accuracy never excuses a violation of human rights.</strong> A system that is 
                            "efficiently unfair" is a broken system. The evidence is clear: this model would systematically 
                            harm marginalized communities while appearing objective.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    {
        "id": 19,
        "title": "Slide 19: Mission Debrief & Promotion",
        "sim_acc": 0.92,
        "sim_comp": 100,
        "html": """
            <div class="scenario-box">
                <h2 class="slide-title">🏆 EXCELLENT WORK, DETECTIVE</h2>
                <div class="slide-body">
                    
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="
                            display:inline-flex;
                            align-items:center;
                            gap:10px;
                            padding:10px 18px;
                            border-radius:999px;
                            background:rgba(34, 197, 94, 0.15);
                            border:1px solid #22c55e;
                            font-size:0.95rem;
                            text-transform:uppercase;
                            letter-spacing:0.08em;
                            font-weight:700;
                            color:#22c55e;
                        ">
                            <span style="font-size:1.1rem;">🎖️</span>
                            <span>PART 1 COMPLETE: BIAS DETECTED</span>
                        </div>
                    </div>

                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        You successfully exposed the "Invisible Enemy." You proved that "92% Accuracy" was a mask 
                        for <strong style="color:#ef4444;">Punitive Bias</strong> and 
                        <strong style="color:#ef4444;">Proxy Discrimination</strong>. But a Diagnosis is not a Cure. 
                        The court still needs a working system.
                    </p>

                    <div class="ai-risk-container" style="margin-top:24px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center; color:#22c55e;">
                            🎯 Mission Accomplished
                        </h4>
                        <div style="display:grid; gap:12px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e;">
                                <div style="font-weight:bold;">✅ Identified Data Bias</div>
                                <div style="font-size:0.9rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Frequency, Representation, and Generalization errors
                                </div>
                            </div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e;">
                                <div style="font-weight:bold;">✅ Exposed Performance Gaps</div>
                                <div style="font-size:0.9rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Punitive, Omission, Severity, and Estimation biases
                                </div>
                            </div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e;">
                                <div style="font-weight:bold;">✅ Detected Proxy Variables</div>
                                <div style="font-size:0.9rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Algorithmic redlining through geographic data
                                </div>
                            </div>
                            <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e;">
                                <div style="font-weight:bold;">✅ Made Ethical Judgment</div>
                                <div style="font-size:0.9rem; margin-top:4px; color:var(--body-text-color-subdued);">
                                    Rejected deployment based on justice principles
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top:28px; padding:24px; background:linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1)); border-radius:12px; border:2px solid var(--color-accent);">
                        <h3 style="margin-top:0; text-align:center; color:var(--color-accent);">
                            🎖️ PROMOTION: FAIRNESS ENGINEER
                        </h3>
                        <p style="font-size:1.05rem; text-align:center; margin-bottom:16px;">
                            We don't just need someone to <strong>find</strong> the problems anymore—we need someone to 
                            <strong>fix</strong> them.
                        </p>
                        <div class="hint-box" style="margin-top:12px; background:var(--block-background-fill);">
                            <div style="font-weight:bold; margin-bottom:8px;">Your New Mission:</div>
                            <div style="font-size:0.95rem;">
                                Apply hands-on fairness fixes to repair the broken model.
                            </div>
                        </div>
                        <div class="hint-box" style="margin-top:12px; background:var(--block-background-fill);">
                            <div style="font-weight:bold; margin-bottom:8px;">The Roadmap:</div>
                            <div style="font-size:0.9rem; display:grid; gap:6px;">
                                <div>1️⃣ Remove Demographics</div>
                                <div>2️⃣ Eliminate Proxies</div>
                                <div>3️⃣ Develop Guidelines</div>
                                <div>4️⃣ Continuous Improvement</div>
                            </div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:28px; padding:20px; background:rgba(34, 197, 94, 0.1); border-radius:8px;">
                        <div style="font-size:1.5rem; margin-bottom:8px;">⬇️</div>
                        <p style="font-size:1.1rem; font-weight:600; margin:0;">
                            Mission Complete. Scroll Down to Begin Next Activity
                        </p>
                        <div style="font-size:1.5rem; margin-top:8px;">⬇️</div>
                    </div>
                </div>
            </div>
        """
    }
]

# --- 5. LEADERBOARD HELPERS ---

def get_or_assign_team(client, username):
    """Get user's existing team from leaderboard or assign a default team."""
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])
        my_user = next((u for u in users if u.get("username") == username), None)
        if my_user and my_user.get("teamName"):
            return my_user.get("teamName")
        return "team-a"
    except Exception:
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
        
        completed_task_ids = []
        if my_user:
            completed_task_ids = my_user.get("completedTaskIds", []) or []
        
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
            "all_teams": teams_sorted,
            "completed_task_ids": completed_task_ids
        }
    except Exception as e:
        print(f"Leaderboard Error: {e}")
        return None

def ensure_table_and_get_data(username, token, team_name):
    """Get leaderboard data using username and token directly."""
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

    # FIX: Use a valid structure so extract_playground_id doesn't return None
    DUMMY_PLAYGROUND_URL = "https://example.com/playground/m-mc"

    try:
        client.get_table(TABLE_ID)
    except Exception:
        try:
            client.create_table(table_id=TABLE_ID, display_name="LMS", playground_url=DUMMY_PLAYGROUND_URL)
        except Exception:
            pass

    data = get_leaderboard_data(client, username, team_name)
    return data, username

def trigger_api_update(username, token, team_name, module_id, user_real_accuracy, append_task_id=None, increment_question=False):
    """
    Update moral compass score using real user accuracy and retry logic.
    FIXED: Uses client.get_user() for reliable Read-Modify-Write cycle.
    """
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    DUMMY_PLAYGROUND_URL = "https://example.com/playground/m-mc"
    
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    
    try:
        client.get_table(TABLE_ID)
    except Exception:
        try:
            client.create_table(table_id=TABLE_ID, display_name="LMS", playground_url=DUMMY_PLAYGROUND_URL)
        except Exception:
            pass
    
    # 1. Force Real Accuracy
    acc = float(user_real_accuracy) if user_real_accuracy is not None else 0.0
    
    # 2. Get Previous State (FIXED: Direct Lookup)
    prev_task_ids = []
    try:
        # Fetch directly from DB to ensure we don't miss existing data
        user_stats = client.get_user(table_id=TABLE_ID, username=username)
        
        # Handle response (Support both Dataclass and Dict return types)
        if hasattr(user_stats, "completed_task_ids"):
             prev_task_ids = user_stats.completed_task_ids or []
        elif isinstance(user_stats, dict):
             prev_task_ids = user_stats.get("completed_task_ids", []) or []
             
    except Exception:
        # 404 Not Found (First time user) or network error
        prev_task_ids = []

    # 3. Calculate New Task List
    new_task_ids = list(prev_task_ids)
    if append_task_id and append_task_id not in new_task_ids:
        new_task_ids.append(append_task_id)
        try:
            new_task_ids.sort(key=lambda x: int(x[1:]) if x.startswith('t') and x[1:].isdigit() else 0)
        except (ValueError, IndexError):
            pass
    
    # 4. SIMPLIFIED MATH: Only count Tasks
    tasks_completed = len(new_task_ids)
    
    # Write to API
    client.update_moral_compass(
        table_id=TABLE_ID,
        username=username,
        team_name=team_name,
        metrics={"accuracy": acc},
        tasks_completed=tasks_completed,
        total_tasks=10,       # Denominator is 10
        questions_correct=0,  # Ignored
        total_questions=0,    # Ignored
        primary_metric="accuracy",
        completed_task_ids=new_task_ids if new_task_ids else None
    )

    # 5. Polling Retry
    # We still use get_leaderboard_data here for the *return* value (visuals), 
    # but the logic above ensures the *write* was correct.
    prev_data = None
    new_data = None
    
    print(f"🔄 Polling API... Target Task Count: {tasks_completed}")
    
    for attempt in range(3):
        time.sleep(1.5)
        current_read = get_leaderboard_data(client, username, team_name)
        if not current_read: continue
            
        current_ids = current_read.get('completed_task_ids', []) or []
        
        # Check if DB matches local expectation
        if len(current_ids) == tasks_completed:
            new_data = current_read
            print("✅ API update confirmed.")
            break
        
        print(f"⚠️ API Latency detected. Retrying... ({attempt+1}/3)")

    # 6. Safety Patch (If polling failed to catch up, manually patch local view)
    if new_data is None and prev_data is None:
         # Fallback if everything fails
         new_data = get_leaderboard_data(client, username, team_name)

    if new_data:
         fetched_ids = new_data.get('completed_task_ids', []) or []
         # If the UI data is stale, force it to match our calculation
         if len(fetched_ids) < len(new_task_ids):
             new_data['completed_task_ids'] = new_task_ids
             # Recalculate score locally for display
             # Score = Acc * (Tasks/10)
             new_data['score'] = acc * (len(new_task_ids) / 10.0)

    # Note: If this is the very first write, prev_data might be None. 
    # We return new_data twice in that case to avoid crashes.
    return (prev_data or new_data), new_data, username

# --- 6. RENDERERS ---

def render_top_dashboard(data, module_id):
    # Defaults
    display_score = 0.0
    count_completed = 0
    rank_display = "–"
    team_rank_display = "–"
    
    if data:
        display_score = float(data.get('score', 0.0))
        rank_display = f"#{data.get('rank', '–')}"
        team_rank_display = f"#{data.get('team_rank', '–')}"
        completed_ids = data.get('completed_task_ids', []) or []
        count_completed = len(completed_ids)
    
    # PROGRESS CALCULATION: 10 Total Tasks (1 Task = 10%)
    TOTAL_COURSE_TASKS = 10 
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
                <div class="progress-label">
                    Mission Progress: {progress_pct}%
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{progress_pct}%;"></div>
                </div>
            </div>
        </div>
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
                <div class="lb-panel panel-team">{team_html}</div>
                <div class="lb-panel panel-user">{user_html}</div>
            </div>
        </div>
    </div>
    """

def render_team_table(data, team_name):
    if not data or not data.get("all_teams"):
        return "<p>No team standings yet.</p>"
    rows = ""
    for idx, t in enumerate(data["all_teams"]):
        is_mine = (t["team"] == team_name)
        row_class = "row-highlight-team" if is_mine else "row-normal"
        rows += f"<tr class='{row_class}'><td style='padding:12px;text-align:center;'>{idx+1}</td><td style='padding:12px;'>{t['team']}</td><td style='padding:12px;text-align:right;'>{t['avg']:.3f}</td></tr>"
    return f"<div class='table-container'><table class='leaderboard-table'><thead><tr><th style='padding:12px;'>Rank</th><th style='padding:12px;text-align:left;'>Team</th><th style='padding:12px;text-align:right;'>Avg Score 🧭</th></tr></thead><tbody>{rows}</tbody></table></div>"

def render_user_table(data, username):
    if not data or not data.get("all_users"):
        return "<p>No individual scores yet.</p>"
    rows = ""
    for idx, u in enumerate(data["all_users"]):
        is_me = (u.get("username") == username)
        row_class = "row-highlight-me" if is_me else "row-normal"
        rows += f"<tr class='{row_class}'><td style='padding:12px;text-align:center;'>{idx+1}</td><td style='padding:12px;'>{u.get('username','')}</td><td style='padding:12px;text-align:right;'>{float(u.get('moralCompassScore',0)):.3f}</td></tr>"
    return f"<div class='table-container'><table class='leaderboard-table'><thead><tr><th style='padding:12px;'>Rank</th><th style='padding:12px;text-align:left;'>Agent</th><th style='padding:12px;text-align:right;'>Score 🧭</th></tr></thead><tbody>{rows}</tbody></table></div>"
### Part 3: Quiz Logic, CSS, App Layout, and Launch

# --- 7. QUIZ LOGIC (With Wrappers) ---

CORRECT_ANSWER_0 = "A) Because simple accuracy ignores potential bias and harm."
CORRECT_ANSWER_1 = "Step 3: Prove the Error"
CORRECT_ANSWER_2 = "Check subgroup errors to prevent systematic harm"

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
.leaderboard-card .lb-tabs {
    margin-top: 8px;
}
.leaderboard-card input[type="radio"] {
    display: none;
}
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
.row-highlight-me,
.row-highlight-team {
    background-color: rgba(96, 165, 250, 0.18);
    border-bottom: 1px solid var(--border-color-primary);
    font-weight: 600;
}
.ai-risk-container {
    margin-top: 16px;
    padding: 12px;
    background-color: var(--body-background-fill);
    border-radius: 8px;
    border: 1px solid var(--border-color-primary);
}
@media (prefers-color-scheme: dark) {
    .scenario-box, .summary-box, .hint-box, .table-container, .leaderboard-card, .profile-card {
        background-color: #2D323E; color: white; border-color: #555555; box-shadow: none;
    }
    .ai-risk-container { background-color: #181B22; border-color: #555555; }
    .leaderboard-table th { background-color: #1f2937; color: white; border-bottom-color: #555555; }
}
"""

# --- 9. BUILD APP ---

def create_bias_detective_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # --- STATE ---
        username_state = gr.State(value=None)
        token_state    = gr.State(value=None)
        team_state     = gr.State(value=None)
        module0_done   = gr.State(value=False)
        current_module = gr.State(value=0)
        
        # NEW: Accuracy State (Defaults to 0.0)
        accuracy_state = gr.State(value=0.0) 

        # --- UI LAYOUT ---
        gr.Markdown("# 🕵️‍♀️ Bias Detective: Moral Compass Lab")
        out_top = gr.HTML()

        # Module 0
        with gr.Column(elem_id="module-0", elem_classes=["module-container"], visible=True) as module_0:
            gr.HTML(MODULES[0]["html"]) 
            quiz_q = gr.Markdown("### 🧠 Quick Knowledge Check\n\n**Why do we multiply your Accuracy by Ethical Progress?**")
            quiz_radio = gr.Radio(label="Select your answer:", choices=[
                "A) Because simple accuracy ignores potential bias and harm.",
                "B) To make the leaderboard math more complicated.",
                "C) Accuracy is the only metric that actually matters."
            ])
            quiz_feedback = gr.HTML("")
            btn_next_0 = gr.Button("Begin AI Bias Mission", variant="primary")

        # Module 1
        with gr.Column(elem_id="module-1", elem_classes=["module-container"], visible=False) as module_1:
            gr.HTML(MODULES[1]["html"]) 
            mod1_quiz_q = gr.Markdown("### 🧠 Investigation Roadmap Check\n\n**Which step requires you to gather evidence?**")
            mod1_quiz_radio = gr.Radio(label="Select your answer:", choices=[
                "Step 1: Learn the Rules", "Step 2: Scan the Data", "Step 3: Prove the Error", "Step 4: Diagnose Harm"
            ])
            mod1_quiz_feedback = gr.HTML("")
            with gr.Row():
                btn_prev_1 = gr.Button("⬅️ Previous")
                btn_next_1 = gr.Button("Begin Intelligence Briefing ▶️", variant="primary")

        # Module 2
        with gr.Column(elem_id="module-2", elem_classes=["module-container"], visible=False) as module_2:
            gr.HTML(MODULES[2]["html"])
            mod2_quiz_q = gr.Markdown("### 🧠 Justice & Equity Check\n\n**What does Justice & Equity require?**")
            mod2_quiz_radio = gr.Radio(label="Select your answer:", choices=[
                "Explain model decisions", "Check subgroup errors to prevent systematic harm", "Minimize error rate", "Ensure efficiency"
            ])
            mod2_quiz_feedback = gr.HTML("")
            with gr.Row():
                btn_prev_2 = gr.Button("⬅️ Back")
                btn_next_2 = gr.Button("Initialize Protocol ▶️", variant="primary")

        # Modules 3-19
        module_cols = {}
        for i in range(3, 20):
            with gr.Column(elem_id=f"module-{i}", elem_classes=["module-container"], visible=False) as mod_col:
                gr.HTML(MODULES[i]["html"])
                with gr.Row():
                    btn_prev = gr.Button("⬅️ Previous")
                    if i < 19:
                        btn_next = gr.Button("Next ▶️", variant="primary")
                    else:
                        btn_next = gr.Button("🎉 Complete Bias Detective Course", variant="primary")
                module_cols[i] = (mod_col, btn_prev, btn_next)

        leaderboard_html = gr.HTML()

        # --- LOGIC & WIRING ---

        # 1. INITIAL LOAD
        def handle_initial_load(request: gr.Request):
            """
            On app load:
            1. Auth checks.
            2. Fetch real accuracy/team from Playground history.
            3. silently syncs this data to the Moral Compass server so the user exists.
            4. Renders the dashboard.
            """
            success, username, token = _try_session_based_auth(request)
            
            # Defaults
            team_name = "Team-Unassigned"
            real_accuracy = 0.0
            
            if success and username and token:
                # 1. Fetch REAL history from the original playground
                real_accuracy, fetched_team = fetch_user_history(username, token)
                
                # 2. Initialize connection
                os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
                client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
                
                # 3. Check if user already has a team in Moral Compass DB
                existing_team = get_or_assign_team(client, username)
                
                # LOGIC FIX: Prioritize the Playground Team if valid
                if fetched_team != "Team-Unassigned":
                    team_name = fetched_team
                elif existing_team != "team-a":
                    team_name = existing_team
                else:
                    team_name = "team-a"
        
                # 4. SILENT SYNC: Ensure user exists on server with correct data
                try:
                    # Check if user exists to avoid overwriting progress if they do
                    user_stats = client.get_user(table_id=TABLE_ID, username=username)
                except Exception:
                    user_stats = None 
        
                # We update if: A) New user, or B) Team name is out of sync
                current_db_team = user_stats.get('teamName') if user_stats else None
                
                if not user_stats or current_db_team != team_name:
                    print(f"Syncing user {username} to Team: {team_name} (Accuracy: {real_accuracy})...")
                    client.update_moral_compass(
                        table_id=TABLE_ID,
                        username=username,
                        team_name=team_name, 
                        metrics={"accuracy": float(real_accuracy)},
                        # Preserve progress if they existed, else 0
                        tasks_completed=user_stats.get('tasksCompleted', 0) if user_stats else 0,
                        total_tasks=10,
                        primary_metric="accuracy"
                    )
                    # Small sleep to let DynamoDB consistency catch up before we read back
                    time.sleep(1.0)
        
                # 5. Get Data & Render
                data, username = ensure_table_and_get_data(username, token, team_name)
                html_top = render_top_dashboard(data, module_id=0)
                lb_html = render_leaderboard_card(data, username, team_name)
                
                return (
                    username,      # 1. username_state
                    token,         # 2. token_state
                    team_name,     # 3. team_state
                    False,         # 4. module0_done
                    html_top,      # 5. out_top
                    lb_html,       # 6. leaderboard_html
                    real_accuracy  # 7. accuracy_state
                )
            else:
                # Failure Case
                return (
                    None, None, None, False, 
                    "<div class='hint-box'>⚠️ Authentication required. Please access this app with a valid session ID.</div>", 
                    "", 
                    0.0
                )

        demo.load(
            fn=handle_initial_load,
            inputs=None,
            outputs=[username_state, token_state, team_state, module0_done, out_top, leaderboard_html, accuracy_state]
        )

        # 2. QUIZ WRAPPERS (With Accuracy State)
        
        def wrapper_quiz_0(user, tok, team, done, ans, acc_val):
            if ans is None: 
                return (gr.update(), gr.update(), done, "<div class='hint-box'>Please select.</div>")
            if ans != CORRECT_ANSWER_0:
                return (gr.update(), gr.update(), done, "<div class='hint-box'>❌ Not quite.</div>")
            if done:
                data, _ = ensure_table_and_get_data(user, tok, team)
                return (render_top_dashboard(data, 0), render_leaderboard_card(data, user, team), done, gr.update())
            
            prev, curr, _ = trigger_api_update(user, tok, team, 0, acc_val, "t1", True)
            d_score = curr["score"] - (prev["score"] if prev else 0.0)
            msg = f"<div class='profile-card risk-low'><h2>🚀 Correct!</h2><p>Score +{d_score:.3f}</p></div>"
            return (render_top_dashboard(curr, 0), render_leaderboard_card(curr, user, team), True, msg)

        def wrapper_quiz_1(user, tok, team, ans, acc_val):
            if ans != CORRECT_ANSWER_1: return (gr.update(), gr.update(), "<div class='hint-box'>❌ Try again.</div>")
            prev, curr, _ = trigger_api_update(user, tok, team, 1, acc_val, "t2", True)
            d_score = curr["score"] - (prev["score"] if prev else 0.0)
            msg = f"<div class='profile-card risk-low'><h2>🎯 Excellent!</h2><p>Score +{d_score:.3f}</p></div>"
            return (render_top_dashboard(curr, 1), render_leaderboard_card(curr, user, team), msg)

        def wrapper_quiz_2(user, tok, team, ans, acc_val):
            if ans != CORRECT_ANSWER_2: return (gr.update(), gr.update(), "<div class='hint-box'>❌ Try again.</div>")
            prev, curr, _ = trigger_api_update(user, tok, team, 2, acc_val, "t3", True)
            d_score = curr["score"] - (prev["score"] if prev else 0.0)
            msg = f"<div class='profile-card risk-low'><h2>✅ Cleared!</h2><p>Score +{d_score:.3f}</p></div>"
            return (render_top_dashboard(curr, 2), render_leaderboard_card(curr, user, team), msg)

        # 3. EVENTS (Wiring)
        quiz_radio.change(
            fn=wrapper_quiz_0,
            inputs=[username_state, token_state, team_state, module0_done, quiz_radio, accuracy_state],
            outputs=[out_top, leaderboard_html, module0_done, quiz_feedback]
        )
        mod1_quiz_radio.change(
            fn=wrapper_quiz_1,
            inputs=[username_state, token_state, team_state, mod1_quiz_radio, accuracy_state],
            outputs=[out_top, leaderboard_html, mod1_quiz_feedback]
        )
        mod2_quiz_radio.change(
            fn=wrapper_quiz_2,
            inputs=[username_state, token_state, team_state, mod2_quiz_radio, accuracy_state],
            outputs=[out_top, leaderboard_html, mod2_quiz_feedback]
        )

        # Navigation 0->1
        def nav_0_to_1(ans): return (gr.update(visible=False), gr.update(visible=True))
        btn_next_0.click(fn=nav_0_to_1, inputs=None, outputs=[module_0, module_1])

        # Navigation 1<->2
        def nav_1_back(): return (gr.update(visible=True), gr.update(visible=False))
        def nav_1_next(ans): return (gr.update(visible=False), gr.update(visible=True))
        btn_prev_1.click(fn=nav_1_back, outputs=[module_0, module_1])
        btn_next_1.click(fn=nav_1_next, inputs=None, outputs=[module_1, module_2])

        # Navigation 2<->3
        def nav_2_back(): return (gr.update(visible=True), gr.update(visible=False))
        def nav_2_next(ans): return (gr.update(visible=False), gr.update(visible=True))
        btn_prev_2.click(fn=nav_2_back, outputs=[module_1, module_2])
        btn_next_2.click(fn=nav_2_next, inputs=None, outputs=[module_2, module_cols[3][0]])

        # Navigation Loop for 3-19
        # Helper to create render update closure
        def make_render_fn(target_mod_id):
            def render_fn(user, tok, team):
                data, _ = ensure_table_and_get_data(user, tok, team)
                return (render_top_dashboard(data, target_mod_id), render_leaderboard_card(data, user, team))
            return render_fn

        # 3 -> 2 (Prev)
        module_cols[3][1].click(lambda: (gr.update(visible=True), gr.update(visible=False)), outputs=[module_2, module_cols[3][0]])
        # 3 -> 4 (Next)
        module_cols[3][2].click(
            fn=lambda u,t,tm: make_render_fn(4)(u,t,tm) + (gr.update(visible=False), gr.update(visible=True)),
            inputs=[username_state, token_state, team_state],
            outputs=[out_top, leaderboard_html, module_cols[3][0], module_cols[4][0]]
        )

        # Loop for remaining
        for i in range(4, 20):
            curr_col, prev_btn, next_btn = module_cols[i]
            prev_col_ref = module_cols[i-1][0]
            
            # Previous
            prev_btn.click(
                lambda: (gr.update(visible=True), gr.update(visible=False)),
                outputs=[prev_col_ref, curr_col]
            )
            
            # Next (if not last)
            if i < 19:
                next_col_ref = module_cols[i+1][0]
                next_btn.click(
                    fn=lambda u,t,tm, idx=i+1: make_render_fn(idx)(u,t,tm) + (gr.update(visible=False), gr.update(visible=True)),
                    inputs=[username_state, token_state, team_state],
                    outputs=[out_top, leaderboard_html, curr_col, next_col_ref]
                )
            else:
                # Finish button (Module 19)
                next_btn.click(fn=make_render_fn(19), inputs=[username_state, token_state, team_state], outputs=[out_top, leaderboard_html])

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

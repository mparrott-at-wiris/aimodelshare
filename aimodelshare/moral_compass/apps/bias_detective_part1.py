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
                        To make that risk visible, this challenge uses a new metric: your
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
                            through this challenge, the more of your accuracy “counts” toward your Moral Compass Score.
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
                <h2 class="slide-title">🕵️ Your New Mission: Investigate Hidden AI Bias</h2>
                <div class="slide-body">

                    <p style="font-size:1.05rem; max-width:800px; margin:0 auto 18px auto;">
                        You've been granted access to an AI model that <em>appears</em> safe — but the historical information it learned from may include unfair patterns.
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
                        <h4 style="margin-top:0; font-size:1.2rem; text-align:center;">🔍 Your Investigation Roadmap</h4>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:12px;">
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">Step 1: Learn the Rules</div>
                                <div style="font-size:0.95rem;">Understand what actually counts as bias.</div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">Step 2: Collect Evidence</div>
                                <div style="font-size:0.95rem;">Look inside the data the model learned from to find suspicious patterns.</div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:700;">Step 3: Prove the Prediction Error</div>
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
            <h2 class="slide-title">⚖️ Justice & Equity: Your Primary Rule</h2>
            <div class="slide-body">

              <!-- Step badge -->
              <div style="display:flex; justify-content:center; margin-bottom:18px;">
                <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); font-weight:800;">
                  <span style="font-size:1.1rem;">📜</span><span>STEP 1: LEARN THE RULES — Understand what actually counts as bias.</span>
                </div>
              </div>

              <!-- Framing & intel -->
              <p style="font-size:1.05rem; max-width:780px; margin:0 auto 12px auto; text-align:center;">
                Before we examine the evidence, we need the <strong>rules of the investigation</strong>. Ethics isn’t abstract here — it’s our field guide.
              </p>
              <p style="font-size:1.05rem; max-width:820px; margin:0 auto 12px auto; text-align:center;">
                We do not guess what is right or wrong - we rely on <strong>expert advice</strong>.
                <br>
                We will use guidance from the experts at the <strongCatalan Observatory for Ethics in AI (OEIAC)</strong>, who help ensure AI systems are fair and responsible.
                <br>
                <em>While they established 7 core principles to keep AI safe, our intel suggests this specific case involves a violation of the <strong>Justice and Equity</strong> principle.</em>
              </p>

              <!-- Where principles fit -->
              <div class="ai-risk-container" style="margin-top:10px; border-width:2px;">
                <h4 style="margin-top:0; font-size:1.12rem; text-align:center;">🗺️ Where Principles Fit</h4>
                <div style="display:flex; align-items:center; justify-content:center; gap:10px; flex-wrap:wrap; font-weight:800;">
                  <span>Principles</span>
                  <span style="opacity:0.6;">→</span>
                  <span>Evidence</span>
                  <span style="opacity:0.6;">→</span>
                  <span>Tests</span>
                  <span style="opacity:0.6;">→</span>
                  <span>Judgment</span>
                  <span style="opacity:0.6;">→</span>
                  <span>Fixes</span>
                </div>
                <p style="font-size:0.98rem; text-align:center; margin:8px 0 0 0;">
                  <strong>Principles help define the evidence you should collect and the tests you should run.</strong> Evidence and tests tell you <em>what counts as bias</em> when you investigate real data and outputs.
                </p>
              </div>

              <!-- Primary principle focus: Justice & Equity -->
              <div class="ai-risk-container" style="margin-top:14px; border-width:2px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <h4 style="margin:0; font-size:1.18rem; color:#ef4444;">🧩 Justice & Equity — What Counts as Bias</h4>
                  <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.12em; font-weight:800; padding:2px 8px; border-radius:999px; border:1px solid #ef4444; color:#ef4444;">Priority in this case</div>
                </div>

                <div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; margin-top:10px;">
                  <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                    <div style="font-weight:800;">Representation Bias</div>
                    <div style="font-size:0.95rem;">Compare dataset distribution to reality (e.g., 10% group representation vs 71%).</div>
                    <div style="font-size:0.95rem; color:var(--body-text-color-subdued);">If one group appears far more than reality, the model may learn these group patterns in a biased manner.</div>
                  </div>
                  <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                    <div style="font-weight:800;">Error Gaps</div>
                    <div style="font-size:0.95rem;">Check for AI prediction mistakes by subgroup.</div>
                    <div style="font-size:0.95rem; color:var(--body-text-color-subdued);">Higher error for a group can mean unfair treatment; that <em>can mean increased bias</em>.</div>
                  </div>
                  <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                    <div style="font-weight:800;">Outcome Disparities</div>
                    <div style="font-size:0.95rem;">Look for worse outcomes related to AI predictions for specific groups (early release, bail, sentencing).</div>
                    <div style="font-size:0.95rem; color:var(--body-text-color-subdued);">Bias isn’t just numbers — it changes real‑world outcomes.</div>
                  </div>
                </div>

                <div class="hint-box" style="margin-top:12px;">
                  <div style="font-weight:800;">Plain Rule</div>
                  <div style="font-size:0.95rem;">If one group is <strong>systematically misclassified more</strong>, that’s a likely signal for a Justice & Equity violation.</div>
                </div>
              </div>

              <!-- Other principles: visible but secondary -->
              <div class="ai-risk-container" style="margin-top:14px; border-width:2px;">
                <h4 style="margin-top:0; font-size:1.12rem; text-align:center;">🧭 Examples of Other AI Ethics Principles (Could also be used to help investigate AI.)</h4>
                <div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:10px; opacity:0.9;">
                  <div class="hint-box" style="margin-top:0;">
                    <div style="font-weight:800;">Transparency & Explainability</div>
                    <div style="font-size:0.95rem;">Explainable scores enable audits and appeals.</div>
                  </div>
                  <div class="hint-box" style="margin-top:0;">
                    <div style="font-weight:800;">Security & Non-maleficence</div>
                    <div style="font-size:0.95rem;">Minimize harmful mistakes; plan for failure.</div>
                  </div>
                  <div class="hint-box" style="margin-top:0;">
                    <div style="font-weight:800;">Responsibility & Accountability</div>
                    <div style="font-size:0.95rem;">Assign owners; keep an audit trail.</div>
                  </div>
                  <div class="hint-box" style="margin-top:0;">
                    <div style="font-weight:800;">Privacy</div>
                    <div style="font-size:0.95rem;">Use only necessary data; justify sensitive attributes.</div>
                  </div>
                  <div class="hint-box" style="margin-top:0;">
                    <div style="font-weight:800;">Autonomy</div>
                    <div style="font-size:0.95rem;">Provide appeals and alternatives.</div>
                  </div>
                  <div class="hint-box" style="margin-top:0;">
                    <div style="font-weight:800;">Sustainability</div>
                    <div style="font-size:0.95rem;">Avoid long‑term social or environmental harm.</div>
                  </div>
                </div>

                <div class="hint-box" style="margin-top:12px;">
                  <div style="font-weight:800;">Why do we need Principles that clearly define the rules of ethical AI?</div>
                  <div style="font-size:0.95rem;">
                    Without a clear plan, what <strong>standards</strong> do we use to make AI more <strong>just</strong>?  AI ethics experts carve out meaningful AI principles and well defined AI safetey action plans that create these shared standards for consistent evaluation and make findings <strong>explainable</strong> to teams, courts, and the public.
                  </div>
                </div>
              </div>

              <!-- Bridge to next step -->
              <div class="hint-box" style="margin-top:16px;">
                <div style="font-weight:800;">✅ You’ve established the rules.</div>
                <div style="font-size:0.98rem;">Next, you will rely on them for your investigation.</div>
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
                            Next, you’ll start scanning the <strong>evidence</strong> inside the data:
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

                    <!-- Transition from rules (Justice & Equity) to action -->
                    <div class="hint-box" style="margin-bottom:16px;">
                        <div style="font-weight:800;">From Rules to Evidence</div>
                        <div style="font-size:0.98rem;">
                            You’ve learned the primary principle — <strong>Justice & Equity</strong> - that helps set the rules for your investigation. Now we apply it.
                            Gather any evidence of (<strong>different categories of bias</strong>, <strong>prediction error gaps</strong>, <strong>outcome disparities</strong>)
                            to examine the model's data. This is the start of <em>evidence collection</em> — finding patterns that signal unfair treatment.
                        </div>
                    </div>

                    <!-- Step badge -->
                    <div style="display:flex; justify-content:center; margin-bottom:18px;">
                        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                            <span style="font-size:1.1rem;">📋</span><span>STEP 2: COLLECT EVIDENCE</span>
                        </div>
                    </div>

                    <!-- Core framing -->
                    <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                        But where should you begin your investigation? You can't interrogate an algorithm. It won't confess. To find bias, we have to look at
                        the evidence trail it leaves behind. If you were investigating a suspicious judge, what would you look for — who they charge most often,
                        who they make the most mistakes with, and whether their decisions harm some people more than others?
                    </p>

                    <!-- Investigation checklist -->
                    <div class="ai-risk-container" style="margin-top:20px;">
                        <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🗂️ The Investigation Checklist</h4>
                        <div style="display:grid; gap:16px; margin-top:16px;">
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 1: "Who is being charged?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                                    → <strong>Reveal:</strong> Check the History (Is one group over‑represented vs reality?)
                                </div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 2: "Who is being wrongly accused?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                                    → <strong>Reveal:</strong> Check the Mistakes (Are prediction errors higher for a group?)
                                </div>
                            </div>
                            <div class="hint-box" style="margin-top:0;">
                                <div style="font-weight:bold; margin-bottom:8px;">📂 Folder 3: "Who is getting hurt?"</div>
                                <div style="padding-left:20px; font-size:0.95rem; color:var(--body-text-color-subdued);">
                                    → <strong>Reveal:</strong> Check the Punishment (Do model outputs lead to worse real outcomes for a group?)
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Expert validation -->
                    <div class="hint-box" style="margin-top:16px; border-left:4px solid #22c55e;">
                        <div style="font-weight:800;">🧠 Expert Validation</div>
                        <div style="font-size:0.98rem;">
                            <em>Exactly.</em> You’ve just described steps that AI ethics experts — including our partners at OEIAC — look for when checking whether an AI system treats people fairly. 
                            They focus on the same ideas you’re using here: who appears in the data, where mistakes happen, and how those mistakes affect people.
                        </div>
                    </div>

                    <!-- Action bridge -->
                    <div class="hint-box" style="margin-top:16px;">
                        <div style="font-weight:800;">✅ Next move</div>
                        <div style="font-size:0.98rem;">
                            Apply the Justice & Equity principle to real evidence: Analyze <strong>Race</strong> → <strong>Gender</strong> → <strong>Age</strong>.
                            You’re building a real case based on data, not guesses.
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
                  <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                    <span style="font-size:1.1rem;">📋</span><span>STEP 2 CONTINUED: YOUR EVIDENCE COLLECTION BRIEFING</span>
                  </div>
                </div>

                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 22px auto; text-align:center;">
                  You are about to access the raw evidence files. But be warned: The AI thinks this data is the truth.
                  If the police historically targeted one neighborhood more than others, the dataset will be full of people from that neighborhood.
                  The AI doesn't know this is potential bias — it just sees a pattern.
                </p>

                <div class="ai-risk-container">
                  <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🔍 The Detective's Task</h4>
                  <p style="font-size:1.05rem; text-align:center; margin-bottom:14px;">
                    We must compare <strong style="color:var(--color-accent);">The Data</strong> against <strong style="color:#22c55e;">Reality</strong>.
                  </p>
                  <p style="font-size:1.05rem; text-align:center;">
                    We are looking for <strong style="color:#ef4444;">Distortions</strong> (Over‑represented, Under‑represented, or Missing groups).
                  </p>
                </div>

                <!-- Click-to-reveal bias concepts (updated categories) -->
                <div class="ai-risk-container" style="margin-top:18px;">
                  <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🧠 Three Common Data Distortions</h4>
                  <p style="font-size:0.95rem; text-align:center; margin:6px 0 14px 0; color:var(--body-text-color-subdued);">
                    Click or tap each card to reveal what it means and the evidence to look for.
                  </p>

                  <div style="display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:14px;">
                    <!-- Historical Bias -->
                    <details class="hint-box" style="margin-top:0;">
                      <summary style="display:flex; align-items:center; justify-content:space-between; font-weight:800; cursor:pointer;">
                        <span>1) Historical Bias</span>
                        <span style="font-size:0.85rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                      </summary>
                      <div style="font-size:0.96rem; margin-top:10px;">
                        Bias baked into past decisions carries into the dataset (e.g., over‑policing of certain neighborhoods or groups).
                      </div>
                      <div style="font-size:0.95rem; color:var(--body-text-color-subdued); margin-top:6px;">
                        Why it matters: The model learns past unfair patterns as if they were “normal,” repeating them at scale.
                      </div>
                      <div style="margin-top:10px; font-size:0.95rem;">
                        Evidence to look for:
                        <ul style="margin:8px 0 0 18px; padding:0;">
                          <li>Long‑term over‑representation of a group in arrests vs real population share.</li>
                          <li>Data concentrated in a few precincts or zip codes with known targeting history.</li>
                          <li>Labels reflecting past policy (e.g., harsher charges) more for specific groups.</li>
                        </ul>
                      </div>
                    </details>

                    <!-- Sampling Bias -->
                    <details class="hint-box" style="margin-top:0;">
                      <summary style="display:flex; align-items:center; justify-content:space-between; font-weight:800; cursor:pointer;">
                        <span>2) Sampling Bias</span>
                        <span style="font-size:0.85rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                      </summary>
                      <div style="font-size:0.96rem; margin-top:10px;">
                        The way data was collected over‑collects information some groups or places and under‑samples others (the “sample” doesn’t match reality).
                      </div>
                      <div style="font-size:0.95rem; color:var(--body-text-color-subdued); margin-top:6px;">
                        Why it matters: The model sees more examples from certain groups, becoming over‑confident or “trigger‑happy” for them.
                      </div>
                      <div style="margin-top:10px; font-size:0.95rem;">
                        Evidence to look for:
                        <ul style="margin:8px 0 0 18px; padding:0;">
                          <li>One precinct/time window dominates incidents (data collection bias).</li>
                          <li>Label imbalance: many “positive” outcomes for one group vs others.</li>
                          <li>Duplicate or repeat entries inflating counts for certain neighborhoods or individuals.</li>
                        </ul>
                      </div>
                    </details>

                    <!-- Exclusion Bias -->
                    <details class="hint-box" style="margin-top:0;">
                      <summary style="display:flex; align-items:center; justify-content:space-between; font-weight:800; cursor:pointer;">
                        <span>3) Exclusion Bias</span>
                        <span style="font-size:0.85rem; font-weight:700; opacity:0.8;">Click to reveal</span>
                      </summary>
                      <div style="font-size:0.96rem; margin-top:10px;">
                        Important people or features are missing or under‑recorded, so the model can’t see the full picture.
                      </div>
                      <div style="font-size:0.95rem; color:var(--body-text-color-subdued); margin-top:6px;">
                        Why it matters: Decisions ignore protective context, making some groups look riskier or less understood.
                      </div>
                      <div style="margin-top:10px; font-size:0.95rem;">
                        Evidence to look for:
                        <ul style="margin:8px 0 0 18px; padding:0;">
                          <li>“Unknown” or missing values clustered for specific groups (e.g., age, employment).</li>
                          <li>No data on protective factors (community ties, stability) → inflated risk scores.</li>
                          <li>Whole regions or language communities absent or barely represented.</li>
                        </ul>
                      </div>
                    </details>
                  </div>
                </div>

                <!-- How distortions show up in model behavior -->
                <div class="ai-risk-container" style="margin-top:16px;">
                  <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🔁 What These Distortions Might Do to the Model</h4>
                  <div style="display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px;">
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:800;">Flagging Bias</div>
                      <div style="font-size:0.95rem;">The model learns to flag one group more often (higher “risk” scores) because the data over‑exposed it.</div>
                    </div>
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:800;">Error Gaps</div>
                      <div style="font-size:0.95rem;">False predictions for high and low risk rates differ by group, especially with skewed sampling or missing context.</div>
                    </div>
                  </div>
                  <p style="font-size:0.95rem; text-align:center; margin-top:10px; color:var(--body-text-color-subdued);">
                    These are core signals for Justice & Equity issues: who gets mislabeled more, and why.
                  </p>
                </div>

                <!-- Quick student-friendly examples -->
                <div class="ai-risk-container" style="margin-top:16px;">
                  <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">📎 Quick Examples</h4>
                  <div style="display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px;">
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:800;">Historical</div>
                      <div style="font-size:0.95rem;">Years of over‑policing one group → dataset shows them far more than reality.</div>
                    </div>
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:800;">Sampling</div>
                      <div style="font-size:0.95rem;">One precinct supplies 70% of arrests → model predicts more risk there by default.</div>
                    </div>
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:800;">Exclusion</div>
                      <div style="font-size:0.95rem;">Missing data for specific demographic groups → risk looks higher for those records.</div>
                    </div>
                  </div>
                </div>

                <!-- Action bridge -->
                <div class="hint-box" style="margin-top:16px;">
                  <div style="font-weight:800;">✅ What You’ll Do Next</div>
                  <div style="font-size:0.98rem;">
                    Capture distribution snapshots (who shows up), check sampling patterns (how data was collected), and mark missing fields (what’s excluded).
                    These are the first proof points for or against <strong>Justice & Equity</strong> conclusions about this model's data and predictive performance.
                  </div>
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
            <h2 class="slide-title">🔎 DATA FORENSIC ANALYSIS: RACE</h2>
            <div class="slide-body">
              <div style="display:flex; justify-content:center; margin-bottom:18px;">
                <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                  <span style="font-size:1.1rem;">📡</span><span>EVIDENCE SCAN: VARIABLE 1 of 3</span>
                </div>
              </div>

              <!-- Overview: What data are we scanning -->
              <div class="ai-risk-container" style="margin-bottom:12px;">
                <h4 style="margin-top:0; font-size:1.2rem; text-align:center;">🗃️ What Are We Scanning?</h4>
                <p style="font-size:1.02rem; max-width:820px; margin:0 auto 10px auto; text-align:center;">
                  We’re examining the <strong>COMPAS dataset</strong>, collected and analyzed by investigative journalists at <strong>ProPublica</strong>. It contains real records used to
                  score a person’s “risk of reoffending,” including demographics (race, age, gender), charges, prior history, and risk scores.
                </p>
                <p style="font-size:1.02rem; max-width:820px; margin:0 auto; text-align:center; color:var(--body-text-color-subdued);">
                  If the <em>data itself</em> is skewed (who shows up, how often, or what gets recorded), the model can learn those
                  patterns as “truth.” Scanning helps us spot distortions that may violate <strong>Justice & Equity</strong>.
                </p>
              </div>

              <!-- Explanation: What the scan button will do -->
              <div class="ai-risk-container" style="margin-bottom:16px;">
                <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🛠️ How the SCAN Works</h4>
                <p style="font-size:1.02rem; max-width:780px; margin:0 auto; text-align:center;">
                  Click <strong>SCAN</strong> to run a quick analysis for the selected demographic group. The scan will:
                </p>
                <ul style="max-width:780px; margin:8px auto 0 auto; font-size:0.98rem;">
                  <li>Compare the group’s share in the <strong>local population</strong> (Broward County, Florida, USA) vs the <strong>dataset</strong>.</li>
                  <li>Reveal <strong>visual bars</strong> showing the gap (population vs dataset).</li>
                  <li>Uncover a <strong>Detective’s Analysis</strong> explaining what the gap means for <strong>Justice & Equity</strong> and what to check next.</li>
                </ul>
              </div>

              <!-- SINGLE TOGGLE: Scan button that reveals ALL hidden learning content (charts + findings) -->
              <details style="border:1px solid var(--border-color-primary); border-radius:12px; overflow:hidden;">
                <summary style="list-style:none; cursor:pointer; padding:14px 18px; font-weight:800; text-align:center; background:var(--background-fill-secondary);">
                  📡 SCAN: Race (African-American) — Click to reveal analysis
                </summary>

                <!-- Explanation for what the scan checks -->
                <div class="hint-box" style="margin:14px; border-left:4px solid var(--color-accent);">
                  <div style="font-weight:800;">What this scan checks</div>
                  <div style="font-size:0.95rem;">
                    We compare the share of African‑Americans in the <strong>local population</strong> vs their share in the
                    <strong>COMPAS training dataset</strong>. Large gaps point to <em>historical or sampling bias</em> and may lead to unfair flagging.
                  </div>
                </div>

                <!-- Context text -->
                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 12px auto; text-align:center;">
                  We know that in this local jurisdiction, African-Americans make up roughly 28% of the total population.
                  If the data is unbiased, the "Evidence Files" should roughly match that number.
                </p>

                <!-- Charts: revealed together with the scan -->
                <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 16px 0;">
                  <h4 style="margin-top:0; font-size:1.2rem;">📊 Comparison Bars</h4>
                  <div style="margin: 16px 0;">
                    <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">Population Reality: ~28% African-American</div>
                    <div style="height:40px; background:linear-gradient(to right, #3b82f6 0%, #3b82f6 28%, #e5e7eb 28%, #e5e7eb 100%); border-radius:8px; position:relative;">
                      <div style="position:absolute; left:28%; top:50%; transform:translate(-50%, -50%); font-size:0.85rem; font-weight:bold; color:white;">28%</div>
                    </div>
                  </div>
                  <div style="margin: 16px 0;">
                    <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">
                      Dataset Reality: <strong style="color:#ef4444;">51% African-American</strong>
                    </div>
                    <div style="height:40px; background:linear-gradient(to right, #ef4444 0%, #ef4444 51%, #e5e7eb 51%, #e5e7eb 100%); border-radius:8px; position:relative;">
                      <div style="position:absolute; left:51%; top:50%; transform:translate(-50%, -50%); font-size:0.85rem; font-weight:bold; color:white;">51%</div>
                    </div>
                  </div>
                </div>

                <!-- Detective findings: revealed together -->
                <div class="hint-box" style="background:rgba(239, 68, 68, 0.08); margin-top:8px;">
                  <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>
                  <p style="margin-bottom:8px;">The dataset is 51% African-American. That is <strong>almost twice</strong> their representation in the local population.</p>
                  <ul style="margin:0 0 10px 18px; padding:0; font-size:0.95rem;">
                    <li><strong>What it likely means:</strong> historical over‑policing or sampling bias concentrated in certain neighborhoods.</li>
                    <li><strong>Why it matters:</strong> the model may learn to flag African‑Americans more often simply because it saw more cases.</li>
                    <li><strong>Next check:</strong> compare false high and low predcition rates by race to see if error gaps confirm Justice & Equity risks.</li>
                  </ul>
                  <p style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:8px;">
                    Source context: ProPublica’s COMPAS dataset is widely used to study fairness in criminal risk scoring. It helps us see how
                    data patterns can shape model behavior — for better or worse.
                  </p>
                </div>
              </details>
            </div>
          </div>
        """,
    },
    {
        "id": 7,
        "title": "Slide 7: Evidence Scan (Gender)",
        "html": """
          <div class="scenario-box">
            <h2 class="slide-title">🔎 DATA FORENSIC ANALYSIS: GENDER</h2>
            <div class="slide-body">
              <div style="display:flex; justify-content:center; margin-bottom:18px;">
                <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                  <span style="font-size:1.1rem;">📡</span><span>EVIDENCE SCAN: VARIABLE 2 of 3</span>
                </div>
              </div>

              <!-- Overview: What data are we scanning -->
              <div class="ai-risk-container" style="margin-bottom:12px;">
                <h4 style="margin-top:0; font-size:1.2rem; text-align:center;">🗃️ What Are We Scanning?</h4>
                <p style="font-size:1.02rem; max-width:820px; margin:0 auto 10px auto; text-align:center;">
                  We’re examining gender representation in the <strong>COMPAS dataset</strong> (ProPublica). It includes real case records
                  with demographics (gender, race, age), charges, prior history, and risk scores used in criminal justice decisions.
                </p>
                <p style="font-size:1.02rem; max-width:820px; margin:0 auto; text-align:center; color:var(--body-text-color-subdued);">
                  If the dataset is skewed toward one gender, the model may learn that skew as “normal,” which can affect scoring fairness.
                </p>
              </div>

              <!-- Explanation: What the scan button will do -->
              <div class="ai-risk-container" style="margin-bottom:16px;">
                <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🛠️ How the SCAN Works</h4>
                <p style="font-size:1.02rem; max-width:780px; margin:0 auto; text-align:center;">
                  Click <strong>SCAN</strong> to run a quick analysis for the selected demographic group. The scan will:
                </p>
                <ul style="max-width:780px; margin:8px auto 0 auto; font-size:0.98rem;">
                  <li>Compare <strong>population reality</strong> (roughly 50% male / 50% female) to the <strong>training dataset</strong>.</li>
                  <li>Reveal <strong>visual bars</strong> showing the gap (population vs dataset).</li>
                  <li>Uncover a <strong>Detective’s Analysis</strong> explaining fairness implications and next checks.</li>
                </ul>
              </div>

              <!-- SINGLE TOGGLE: Scan button that reveals ALL hidden learning content (charts + findings) -->
              <details style="border:1px solid var(--border-color-primary); border-radius:12px; overflow:hidden;">
                <summary style="list-style:none; cursor:pointer; padding:14px 18px; font-weight:800; text-align:center; background:var(--background-fill-secondary);">
                  📡 SCAN: Gender — Click to reveal analysis
                </summary>

                <!-- Explanation for what the scan checks -->
                <div class="hint-box" style="margin:14px; border-left:4px solid var(--color-accent);">
                  <div style="font-weight:800;">What this scan checks</div>
                  <div style="font-size:0.95rem;">
                    We compare the gender split in the <strong>local population (Broward County, Florida, USA</strong> (≈50/50) vs the <strong>COMPAS dataset</strong>.
                    Large gaps signal <em>sampling or historical bias</em> that can influence how the model treats men vs women.
                  </div>
                </div>

                <!-- Context text -->
                <p style="font-size:1.05rem; max-width:780px; margin:0 auto 12px auto; text-align:center;">
                  We are now scanning for gender balance. In the real world, the population is roughly 50/50.
                  A fair training set is more likely to reflect this balance.
                </p>

                <!-- Charts: revealed with the scan -->
                <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 16px 0;">
                  <h4 style="margin-top:0; font-size:1.2rem;">📊 Comparison Bars</h4>
                  <div style="margin: 16px 0;">
                    <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">Population Reality: 50% Male / 50% Female</div>
                    <div style="display:flex; height:40px; border-radius:8px; overflow:hidden;">
                      <div style="width:50%; background:#3b82f6; display:flex; align-items:center; justify-content:center; font-size:0.85rem; font-weight:bold; color:white;">50% M</div>
                      <div style="width:50%; background:#ec4899; display:flex; align-items:center; justify-content:center; font-size:0.85rem; font-weight:bold; color:white;">50% F</div>
                    </div>
                  </div>
                  <div style="margin: 16px 0;">
                    <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">
                      Dataset Reality: <strong style="color:#ef4444;">81% Male / 19% Female</strong>
                    </div>
                    <div style="display:flex; height:40px; border-radius:8px; overflow:hidden;">
                      <div style="width:81%; background:#ef4444; display:flex; align-items:center; justify-content:center; font-size:0.85rem; font-weight:bold; color:white;">81% M</div>
                      <div style="width:19%; background:#fca5a5; display:flex; align-items:center; justify-content:center; font-size:0.85rem; font-weight:bold; color:white;">19% F</div>
                    </div>
                  </div>
                </div>

                <!-- Detective findings: revealed together -->
                <div class="hint-box" style="background:rgba(239, 68, 68, 0.08); margin-top:8px;">
                  <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>
                  <p style="margin-bottom:8px;">The dataset is 81% male and 19% female — a strong imbalance vs the local demographic reality.</p>
                  <ul style="margin:0 0 10px 18px; padding:0; font-size:0.95rem;">
                    <li><strong>What it likely means:</strong> sampling bias (more male cases recorded), or historical factors making male cases more visible.</li>
                    <li><strong>Why it matters:</strong> the model may generalize poorly for women, raising error rates in realistic risk predictions.</li>
                    <li><strong>Next check:</strong> compare false risk prediction rates by gender; inspect missing or biased data fields by gender (exclusion bias).</li>
                  </ul>
                  <p style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:8px;">
                    Source context: ProPublica’s COMPAS dataset is widely used to study fairness in criminal risk scoring. Gender imbalance can
                    affect how a model evaluates individuals across different groups.
                  </p>
                </div>
              </details>
            </div>
          </div>
        """,
    },
    {
        "id": 8,
        "title": "Slide 8: Evidence Scan (Age)",
        "html": """
          <div class="scenario-box">
            <h2 class="slide-title">🔎 DATA FORENSIC ANALYSIS: AGE</h2>
            <div class="slide-body">
              <div style="display:flex; justify-content:center; margin-bottom:18px;">
                <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:var(--background-fill-secondary); border:1px solid var(--border-color-primary); font-size:0.95rem; font-weight:800;">
                  <span style="font-size:1.1rem;">📡</span><span>EVIDENCE SCAN: VARIABLE 3 of 3</span>
                </div>
              </div>

              <!-- Overview: What we're checking for Age -->
              <div class="ai-risk-container" style="margin-bottom:12px;">
                <h4 style="margin-top:0; font-size:1.2rem; text-align:center;">🗃️ What Are We Scanning (Age)?</h4>
                <p style="font-size:1.02rem; max-width:820px; margin:0 auto 10px auto; text-align:center;">
                  We’re examining how <strong>age</strong> is represented in the data. Criminology shows that risk can drop as people get older,
                  so a dataset <em>heavily skewed to younger ages</em> could teach the model to overestimate risk for everyone.
                </p>
                <p style="font-size:1.02rem; max-width:820px; margin:0 auto; text-align:center; color:var(--body-text-color-subdued);">
                  If the sample mostly contains people under 45, the model may become “age‑biased,” underestimating how age reduces risk.
                </p>
              </div>

              <!-- Explanation: What the scan button will do -->
              <div class="ai-risk-container" style="margin-bottom:16px;">
                <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">🛠️ How the SCAN Works</h4>
                <p style="font-size:1.02rem; max-width:780px; margin:0 auto; text-align:center;">
                  Click <strong>SCAN</strong> to analyze the dataset’s <em>age distribution</em>. The scan will:
                </p>
                <ul style="max-width:780px; margin:8px auto 0 auto; font-size:0.98rem;">
                  <li>Show the share of cases across three age groups (&lt;25, 25–45, &gt;45) used in the COMPAS dataset.</li>
                  <li>Reveal <strong>visual bars</strong> indicating where the dataset is concentrated.</li>
                  <li>Uncover a <strong>Detective’s Analysis</strong> explaining how skewed ages can distort risk predictions.</li>
                </ul>
              </div>

              <!-- SINGLE TOGGLE: Scan button that reveals ALL hidden learning content (bars + findings) -->
              <details style="border:1px solid var(--border-color-primary); border-radius:12px; overflow:hidden;">
                <summary style="list-style:none; cursor:pointer; padding:14px 18px; font-weight:800; text-align:center; background:var(--background-fill-secondary);">
                  📡 SCAN: Age Distribution — Click to reveal analysis
                </summary>

                <!-- Charts: age distribution bars -->
                <div class="ai-risk-container" style="text-align:center; padding: 20px; margin: 16px 0;">
                  <h4 style="margin-top:0; font-size:1.2rem;">📊 Age Distribution in Dataset (COMPAS)</h4>
                  <div style="margin: 10px 0;">
                    <div style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-bottom:8px;">
                      Summary: <strong>Majority between 25–45, fewer very young or older adults</strong>
                    </div>

                    <!-- Bar container -->
                    <div style="display:flex; height:60px; border-radius:8px; overflow:hidden; align-items:flex-end;">
                      <!-- Less than 25 -->
                      <div style="width:33.3%; background:#fca5a5; height:40%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; padding-bottom:8px;">
                        <div style="font-size:0.75rem; font-weight:bold; color:#333;">&lt; 25</div>
                        <div style="font-size:0.65rem; color:#333;">22%</div>
                      </div>

                      <!-- 25–45 -->
                      <div style="width:33.3%; background:#ef4444; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; padding-bottom:8px;">
                        <div style="font-size:0.75rem; font-weight:bold; color:white;">25–45</div>
                        <div style="font-size:0.65rem; color:white;">57%</div>
                      </div>

                      <!-- > 45 -->
                      <div style="width:33.3%; background:#fecaca; height:37%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; padding-bottom:8px;">
                        <div style="font-size:0.75rem; font-weight:bold; color:#333;">&gt; 45</div>
                        <div style="font-size:0.65rem; color:#333;">21%</div>
                      </div>
                    </div>
                  </div>

                  <p style="font-size:0.85rem; max-width:580px; margin:10px auto 0 auto; color:var(--body-text-color-subdued);">
                    Based on the cleaned COMPAS two-year recidivism dataset (6,172 people). Age is grouped into the standard bins: 
                    “Less than 25”, “25–45”, and “Greater than 45”.
                  </p>
                </div>

                </div>

                <!-- Detective findings: implications of skewed age -->
                <div class="hint-box" style="background:rgba(239, 68, 68, 0.08); margin-top:8px;">
                  <h4 style="margin-top:0;">🔍 Detective's Analysis</h4>
                  <p style="margin-bottom:8px;">
                    The dataset contains far fewer older adults than people in the 25–45 range. So if a 62-year-old is arrested, how will the AI interpret their risk?
                  </p>
                  <ul style="margin:0 0 10px 18px; padding:0; font-size:0.95rem;">
                    <li><strong>Risk of distortion:</strong> With few examples of older adults, the model may incorrectly <em>estimate</em> risk for them.</li>
                    <li><strong>Justice & Equity check:</strong> Compare <em>error rates</em> across age groups to see whether the system <em>over-predicts or under-predicts</em> risk for older individuals.</li>
                  </ul>
                </div>
              </details>
            </div>
          </div>
        """,
    },
    {
        "id": 9,
        "title": "Slide 9: Data Forensics Conclusion (Summary)",
        "html": """
            <div class="scenario-box">
              <h2 class="slide-title">📂 DATA FORENSICS REPORT: SUMMARY</h2>
              <div class="slide-body">
                <div style="display:flex; justify-content:center; margin-bottom:18px;">
                  <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 18px; border-radius:999px; background:rgba(34, 197, 94, 0.15); border:1px solid #22c55e; font-size:0.95rem; font-weight:800;">
                    <span style="font-size:1.1rem;">✅</span><span>STATUS: STEP 2 INITIAL DATA EVIDENCE COLLECTION COMPLETE</span>
                  </div>
                </div>

                <p style="font-size:1.05rem; max-width:820px; margin:0 auto 22px auto; text-align:center;">
                  Excellent work. You analyzed the data <strong>Inputs</strong> to the Compas crime risk model and ran scans across <strong>Race</strong>, <strong>Gender</strong>, and <strong>Age</strong>.
                  We found three core distortions that compromise the dataset and can affect AI <strong>Justice & Equity</strong>.
                </p>

                <div class="ai-risk-container">
                  <h4 style="margin-top:0; font-size:1.15rem; text-align:center;">📋 Evidence Board: Key Findings</h4>
                  <div style="display:grid; gap:14px; margin-top:16px;">

                    <!-- Race finding -->
                    <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                      <div style="font-weight:bold; color:#ef4444;">Finding #1: Historical & Sampling Bias (Race)</div>
                      <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                        African-Americans are <strong>over‑represented</strong> in the dataset: <strong>51%</strong> vs <strong>28%</strong> in local reality (≈4×).
                      </div>
                      <div style="font-size:0.92rem; margin-top:6px;">
                        Why it matters: The model may learn to flag this group more often because it saw more cases in the training data.
                      </div>
                    </div>

                    <!-- Gender finding -->
                    <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                      <div style="font-weight:bold; color:#ef4444;">Finding #2: Representation Bias (Gender)</div>
                      <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                        Women are <strong>under‑represented</strong>: <strong>19%</strong> in the dataset vs roughly <strong>50%</strong> in reality.
                      </div>
                      <div style="font-size:0.92rem; margin-top:6px;">
                        Why it matters: With fewer examples, the model may mislearn patterns for women or generalize male‑dominant patterns to them.
                      </div>
                    </div>

                <!-- Age finding -->
                <div class="hint-box" style="margin-top:0; border-left:4px solid #ef4444;">
                  <div style="font-weight:bold; color:#ef4444;">Finding #3: Exclusion/Sampling Skew (Age)</div>
                  <div style="font-size:0.95rem; margin-top:4px; color:var(--body-text-color-subdued);">
                    The dataset is <strong>concentrated in ages 25–45</strong> (a clear majority), with <strong>fewer older adults (over 45)</strong> and fewer people under 25.
                  </div>
                  <div style="font-size:0.92rem; margin-top:6px;">
                    Why it matters: The model may <strong>misestimate risk</strong> for older adults or fail to capture how risk often <em>decreases</em> with age.
                  </div>
                </div>

                <!-- Optional quick visual recap -->
                <div class="ai-risk-container" style="margin-top:18px;">
                  <h4 style="margin-top:0; font-size:1.05rem; text-align:center;">🔎 Quick Recap (What the scans showed)</h4>
                  <div style="display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px;">
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:700;">Race</div>
                      <div style="font-size:0.92rem;">Population: ~28% African-American → Dataset: 51% (almost 2× higher)</div>
                    </div>
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:700;">Gender</div>
                      <div style="font-size:0.92rem;">Reality ≈ 50% women → Dataset: 19% women (under‑representation)</div>
                    </div>
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:700;">Age</div>
                      <div style="font-size:0.92rem;">
                        Ages 25–45 dominate (~57%); people under 25 and over 45 each make up only about one-fifth of the dataset.
                      </div>
                    </div>
                  </div>
                </div>

                <div style="text-align:center; margin-top:24px; padding:16px; background:rgba(59, 130, 246, 0.1); border-radius:8px;">
                  <p style="font-size:1.05rem; margin:0; font-weight:600;">
                    🔍 The <strong>Inputs</strong> are flawed. Next, we must test the <strong>Outputs</strong>:
                    compare predictions against reality and check <strong>error gaps</strong> by group (false positives/negatives).
                  </p>
                </div>
              </div>
            </div>
        """,
    },
    {
        "id": 10,
        "title": "Mission Progress: Initial Data Investigation COMPLETE",
        "html": """
            <div class="scenario-box">
              <h2 class="slide-title">✅ Initial Data Investigation COMPLETE</h2>
              <div class="slide-body">

                <!-- Roadmap from Mission: show current position -->
                <div class="ai-risk-container" style="margin-bottom:14px;">
                  <h4 style="margin-top:0; font-size:1.05rem; text-align:center;">🗺️ Investigation Roadmap</h4>
                  <div style="display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:10px;">
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:700;">Step 1: Learn the Rules</div>
                      <div style="font-size:0.92rem; color:var(--body-text-color-subdued);">Understand what counts as bias.</div>
                    </div>
                    <div class="hint-box" style="margin-top:0; border-left:4px solid #22c55e; background:rgba(34,197,94,0.10);">
                      <div style="font-weight:700; color:#166534;">Step 2: Collect Evidence ✅</div>
                      <div style="font-size:0.92rem; color:var(--body-text-color-subdued);">Dataset forensics complete (Race, Gender, Age).</div>
                    </div>
                    <div class="hint-box" style="margin-top:0; border-left:4px solid #3b82f6; background:rgba(59,130,246,0.10);">
                      <div style="font-weight:700; color:#1d4ed8;">Step 3: Prove the Prediction Error ▶️</div>
                      <div style="font-size:0.92rem; color:var(--body-text-color-subdued);">Test predictions for fairness by group.</div>
                    </div>
                    <div class="hint-box" style="margin-top:0;">
                      <div style="font-weight:700;">Step 4: Diagnose Harm</div>
                      <div style="font-size:0.92rem; color:var(--body-text-color-subdued);">Explain real‑world impacts and fixes.</div>
                    </div>
                  </div>
                  <br>
                  <h4 style="margin-top:0; font-size:1.05rem; text-align:center;">
                    Steps 1 and 2 complete! Next = Step 3 — Prove the Error.
                  </h4>
                </div>

                <!-- Why the next step matters (concise) -->
                <div class="ai-risk-container" style="margin-top:6px;">
                  <h4 style="margin-top:0; font-size:1.05rem; text-align:center;">🎯 Why Group‑by‑Group Prediction Analysis Matters</h4>
                  <ul style="max-width:800px; margin:8px auto 0 auto; font-size:0.98rem;">
                    <li>Reveal <strong>false positive/negative gaps</strong> by Race, Gender, and Age.</li>
                    <li>See <strong>who gets flagged</strong> at current thresholds — and whether it’s fair.</li>
                    <li>Convert your evidence into <strong>a final report of unequal errors</strong> (or clear the model).</li>
                  </ul>
                </div>

                <!-- Short CTA -->
                <div style="text-align:center; margin-top:16px; padding:14px; background:rgba(59,130,246,0.1); border-radius:8px;">
                  <p style="font-size:1.04rem; margin:0; font-weight:600;">
                    ⬇️ Scroll down to begin Step 3: Prove the Error — compare predictions vs reality by group ⬇️
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
        "q": "Detective, based on the Ripple Effect, why is this algorithmic bias classified as a High-Priority Threat?",
        "o": [
            "A) Because computers have malicious intent.",
            "B) Because the error is automated at scale, potentially replicating thousands of times across many cases.",
            "C) Because it costs more money to run the software.",
        ],
        "a": "B) Because the error is automated at scale, potentially replicating thousands of times across many cases.",
        "success": "Threat Assessed. You've identified the unique danger of automation scale.",
    },
    4: {
        "t": "t5",
        "q": "Detective, since the model won't confess, what is one key way to investigate bias?",
        "o": [
            "A) Ask the developers what they intended.",
            "B) Compare the model's predictions against the real outcomes.",
            "C) Run the model faster.",
        ],
        "a": "B) Compare the model's predictions against the real outcomes.",
        "success": "Methodology Confirmed. We will judge the model by its results, not its code.",
    },
    5: {
        "t": "t6",
        "q": "How must you view the dataset as you begin your investigation?",
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
        "q": "The dataset has about 2x more of this group than reality. What technical term best describes this mismatch between the dataset and the population?",
        "o": [
            "A) Sampling or Historical Bias",
            "B) Overfitting",
            "C) Data Leakage",
            "D) Concept Drift",
        ],
        "a": "A) Sampling or Historical Bias",
        "success": "Bias detected: Sampling or Historical Bias. The dataset over‑samples this group relative to reality, which can lead the model to over‑flag. Next: compare error rates by race to confirm fairness impacts.",
    },
    7: {
        "t": "t8",
        "q": "The AI has very few examples of women. What do we call it when a specific group is not adequately included?",
        "o": [
            "A) Overfitting",
            "B) Data Leakage",
            "C) Concept Drift",
            "D) Representation Bias",
        ],
        "a": "D) Representation Bias",
        "success": "Bias detected: Representation Bias. Under‑representation can cause the model to generalize poorly for women. Next: compare error rates by gender and inspect missing fields for exclusion bias.",
    },
    8: {
        "t": "t9",
        "q": "Most COMPAS data falls between ages 25–45, with fewer people over 45. What is the primary risk for a 62-year-old?",
        "o": [
            "A) Generalization Error: The AI may misjudge risk because it has few examples of older adults.",
            "B) The model refuses to make a prediction.",
            "C) Older adults automatically receive more accurate predictions.",
        ],
        "a": "A) Generalization Error: The AI may misjudge risk because it has few examples of older adults.",
        "success": "Risk Logged: Generalization Error. The model has limited 'visibility' into older defendants.",
    },
    9: {
        "t": "t10",
        "q": "Detective, you have built evidence that the Input Data could be biased. Is this enough to convict the model?",
        "o": [
            "A) Yes, if data is skewed, it's illegal.",
            "B) No. We must now analyze the Model's prediction mistakes for specific groups to study actual harm to real people.",
            "C) Yes, assume harm.",
        ],
        "a": "B) No. We must now analyze the Model's prediction mistakes for specific groups to study actual harm to real people.",
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
                            else "🎉 Complete Part 1 (Please Scroll Down)"
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
    launch_bias_detective_app(share=False, debug=True, height=1000)

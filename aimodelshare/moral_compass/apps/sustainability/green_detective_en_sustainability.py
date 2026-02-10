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
TOTAL_COURSE_TASKS = 17 # Score calculated against full course (8 in Act6 + 6 in Act7 + 3 reserved)
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


# ============================================================================
# 4. MODULE DEFINITIONS — 8-STEP CURRICULUM-ALIGNED JOURNEY
# ============================================================================
# Phase 1: Personal Impact (Steps 0-5)
# Phase 2: Global Scale + Audit (Steps 6-7)
# ============================================================================

MODULES = [
    # ─────────────────────────────────────────────
    # MODULE 0 — THE HOOK: PERSONAL CONFRONTATION
    # ─────────────────────────────────────────────
    {
        "id": 0,
        "title": "Mission Dossier",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">

                    <!-- HOOK: Personal confrontation -->
                    <div style="text-align:center; margin-bottom:8px;">
                        <div style="font-size:2.6rem; margin-bottom:6px;">👁️</div>
                        <h2 class="slide-title" style="margin-bottom:10px; font-size:2rem; line-height:1.2;">
                            You've already used AI today.
                        </h2>
                        <p style="font-size:1.15rem; max-width:650px; margin:0 auto 18px; line-height:1.5; opacity:0.85;">
                            That autocorrect. That face unlock. That feed algorithm deciding what you see next.
                            <br>Every single one <strong>burned electricity you never saw.</strong>
                        </p>
                    </div>

                    <!-- LIVE COUNTER — homes as primary metric, MWh secondary -->
                    <div style="background:#1e293b; color:white; padding:18px 20px; border-radius:12px; margin-bottom:20px; text-align:center;">
                        <div style="font-size:0.78rem; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">
                            ⚡ Since you opened this page, global AI has powered the equivalent of:
                        </div>
                        <div style="display:flex; justify-content:center; align-items:baseline; gap:6px;">
                            <span id="live-homes-counter" style="font-size:2.8rem; font-weight:900; color:#f87171; font-family:monospace;">0</span>
                            <span style="font-size:1.1rem; color:#94a3b8; font-weight:600;">homes for an hour</span>
                        </div>
                        <div style="font-size:0.82rem; color:#64748b; margin-top:4px;">
                            (<span id="live-kwh-counter" style="color:#94a3b8;">0</span> MWh) — and rising every second
                        </div>
                    </div>
                    <script>
                    (function(){
                        var MWH_PER_SEC = 12000 / 3600;
                        var startTime = Date.now();
                        function tick() {
                            var s = (Date.now() - startTime) / 1000;
                            var mwh = s * MWH_PER_SEC;
                            var homes = Math.round(mwh * 0.85);
                            var el1 = document.getElementById('live-kwh-counter');
                            var el2 = document.getElementById('live-homes-counter');
                            if(el1) el1.textContent = mwh.toFixed(1).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
                            if(el2) el2.textContent = homes.toLocaleString();
                            requestAnimationFrame(tick);
                        }
                        tick();
                    })();
                    </script>

                    <!-- SOCIAL PROOF -->
                    <div style="background:rgba(99,102,241,0.08); border:2px solid rgba(99,102,241,0.2); border-radius:10px; padding:14px 18px; margin-bottom:20px; display:flex; align-items:center; gap:14px;">
                        <span style="font-size:2rem;">🤯</span>
                        <div>
                            <div style="font-size:1.05rem; font-weight:700;">91% of students your age have no idea AI uses water.</div>
                            <div style="font-size:0.9rem; opacity:0.7;">By the end of this investigation, you'll know more about AI's real cost than most adults.</div>
                        </div>
                    </div>

                    <!-- TWO SHOCK STATS — clarify text vs image costs differ -->
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:20px;">
                        <div style="background:#fee2e2; padding:18px; border-radius:12px; border:2px solid #fca5a5; text-align:center;">
                            <div style="font-size:2.4rem;">📱</div>
                            <div style="font-size:1.5rem; font-weight:900; color:#ef4444; margin:6px 0 2px;">Half a phone charge</div>
                            <div style="font-size:0.95rem;">The energy cost of generating <strong>one</strong> AI image.</div>
                            <div style="font-size:0.78rem; color:#7f1d1d; margin-top:4px;">Luccioni et al., 2023</div>
                        </div>
                        <div style="background:#dbeafe; padding:18px; border-radius:12px; border:2px solid #93c5fd; text-align:center;">
                            <div style="font-size:2.4rem;">💧</div>
                            <div style="font-size:1.5rem; font-weight:900; color:#1e40af; margin:6px 0 2px;">One water bottle</div>
                            <div style="font-size:0.95rem;"><strong>Evaporated forever</strong> for every 20–25 text prompts.</div>
                            <div style="font-size:0.78rem; color:#1e3a8a; margin-top:4px;">Li et al., 2023 — UC Riverside</div>
                        </div>
                    </div>
                    <div style="padding:8px 12px; background:rgba(250,204,21,0.1); border-radius:6px; font-size:0.82rem; margin-bottom:20px; text-align:center; opacity:0.8;">
                        ⚠️ Note: Costs vary by task. An AI-generated image uses ~50× more energy than a text reply. We'll explore this in later steps.
                    </div>

                    <!-- THE MISSION -->
                    <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:18px; margin-bottom:18px;">
                        <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                            <span style="font-size:2rem;">🔍</span>
                            <div>
                                <div style="font-size:0.78rem; font-weight:800; color:var(--body-text-color-subdued); letter-spacing:1.5px;">YOUR ASSIGNMENT</div>
                                <div style="font-size:1.25rem; font-weight:800; color:var(--color-accent);">Green AI Detective — 8-Step Investigation</div>
                            </div>
                        </div>
                        <p style="font-size:1rem; line-height:1.55; margin-bottom:12px;">
                            Trace the invisible trail from your screen to the planet. In 8 steps you'll follow your prompt through networks, into GPUs, past cooling towers, across nations — and decide what's worth the cost.
                        </p>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                            <div style="padding:10px; background:rgba(99,102,241,0.08); border-radius:8px; border-left:3px solid #6366f1;">
                                <div style="font-weight:800; font-size:0.82rem; color:#6366f1;">PHASE 1: PERSONAL IMPACT</div>
                                <div style="font-size:0.85rem;">Steps 1-5 — Your click → network → GPU → water → paradox</div>
                            </div>
                            <div style="padding:10px; background:rgba(239,68,68,0.08); border-radius:8px; border-left:3px solid #ef4444;">
                                <div style="font-weight:800; font-size:0.82rem; color:#ef4444;">PHASE 2: GLOBAL SCALE</div>
                                <div style="font-size:0.85rem;">Steps 6-7 — Global scale → your ethical audit</div>
                            </div>
                        </div>
                    </div>

                    <!-- CTA -->
                    <div style="text-align:center; padding:14px; background:linear-gradient(135deg, rgba(34,197,94,0.12), rgba(16,185,129,0.12)); border-radius:12px; border:2px solid #22c55e;">
                        <p style="font-size:1.1rem; font-weight:800; color:var(--color-accent); margin-bottom:4px;">⬇️ Answer below to unlock your first Moral Compass Score</p>
                        <p style="font-size:0.9rem; margin:0; opacity:0.7;">Every correct answer earns points and reveals the next step of the investigation.</p>
                    </div>
                </div>
            </div>
        """,
    },

    # ─────────────────────────────────────────────
    # MODULE 1 — STEP 1: THE DIGITAL GHOST (Your Click)
    # ─────────────────────────────────────────────
    {
        "id": 1,
        "title": "Step 1: The Digital Ghost",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step active">1. YOUR CLICK</div>
                    <div class="tracker-step">2. THE NETWORK</div>
                    <div class="tracker-step">3. THE GPU</div>
                    <div class="tracker-step">4. THE WATER</div>
                    <div class="tracker-step">5. THE PARADOX</div>
                </div>
                <h2 class="slide-title" style="text-align:center;">👻 STEP 1: THE DIGITAL GHOST</h2>
                <div class="slide-body">
                    <div style="max-width:800px; margin:0 auto;">

                        <p style="font-size:1.1rem; text-align:center; margin-bottom:20px;">
                            When you hit "Send" on ChatGPT, ask Snapchat My AI a question, or let an AI rewrite your essay intro —<br>
                            you think it vanishes into the cloud. <strong>It doesn't.</strong>
                        </p>

                        <!-- ANIMATED JOURNEY -->
                        <div style="background:#1e293b; color:white; padding:20px; border-radius:12px; margin-bottom:20px; overflow:hidden; position:relative;">
                            <div style="font-size:0.78rem; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:14px; text-align:center;">
                                ⚡ WHAT HAPPENS WHEN YOU HIT "SEND"
                            </div>
                            <div class="ghost-journey" style="display:flex; justify-content:space-between; align-items:center; gap:0; position:relative; padding:0 8px;">
                                <div class="ghost-step" style="text-align:center; flex:1; opacity:0; animation: ghostFadeIn 0.5s ease forwards 0.3s;">
                                    <div style="font-size:1.8rem;">📱</div>
                                    <div style="font-size:0.78rem; font-weight:700; margin-top:4px;">You type</div>
                                    <div style="font-size:0.7rem; color:#94a3b8;">"Help me with this essay"</div>
                                </div>
                                <div style="color:#475569; opacity:0; animation: ghostFadeIn 0.3s ease forwards 0.8s;">→</div>
                                <div class="ghost-step" style="text-align:center; flex:1; opacity:0; animation: ghostFadeIn 0.5s ease forwards 1.0s;">
                                    <div style="font-size:1.8rem;">🔌</div>
                                    <div style="font-size:0.78rem; font-weight:700; margin-top:4px;">WiFi + cables</div>
                                    <div style="font-size:0.7rem; color:#94a3b8;">1,000s of miles</div>
                                </div>
                                <div style="color:#475569; opacity:0; animation: ghostFadeIn 0.3s ease forwards 1.5s;">→</div>
                                <div class="ghost-step" style="text-align:center; flex:1; opacity:0; animation: ghostFadeIn 0.5s ease forwards 1.7s;">
                                    <div style="font-size:1.8rem;">🏭</div>
                                    <div style="font-size:0.78rem; font-weight:700; margin-top:4px;">Data center</div>
                                    <div style="font-size:0.7rem; color:#94a3b8;">GPU draws power</div>
                                </div>
                                <div style="color:#475569; opacity:0; animation: ghostFadeIn 0.3s ease forwards 2.2s;">→</div>
                                <div class="ghost-step" style="text-align:center; flex:1; opacity:0; animation: ghostFadeIn 0.5s ease forwards 2.4s;">
                                    <div style="font-size:1.8rem;">🔥</div>
                                    <div style="font-size:0.78rem; font-weight:700; margin-top:4px;">Heat generated</div>
                                    <div style="font-size:0.7rem; color:#f87171;">Needs cooling</div>
                                </div>
                                <div style="color:#475569; opacity:0; animation: ghostFadeIn 0.3s ease forwards 2.9s;">→</div>
                                <div class="ghost-step" style="text-align:center; flex:1; opacity:0; animation: ghostFadeIn 0.5s ease forwards 3.1s;">
                                    <div style="font-size:1.8rem;">💧</div>
                                    <div style="font-size:0.78rem; font-weight:700; margin-top:4px;">Water evaporates</div>
                                    <div style="font-size:0.7rem; color:#60a5fa;">Gone from here</div>
                                </div>
                            </div>
                            <div style="text-align:center; margin-top:14px; padding:8px; background:rgba(248,113,113,0.15); border-radius:6px; opacity:0; animation: ghostFadeIn 0.5s ease forwards 3.6s;">
                                <span style="font-weight:800; color:#f87171;">Total time:</span>
                                <span style="color:#e2e8f0;"> ~200 milliseconds. You never noticed. But the planet did.</span>
                            </div>
                        </div>

                        <!-- GUESS FIRST -->
                        <div id="guess-block" style="background:rgba(99,102,241,0.08); border:2px solid rgba(99,102,241,0.2); border-radius:12px; padding:18px; margin-bottom:20px;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); margin-bottom:6px;">🤔 Quick — before you see the answer:</div>
                            <p style="font-size:0.95rem; margin-bottom:4px;">
                                Surveys suggest the average teen interacts with AI about <strong>50 times a week</strong> — counting ChatGPT, image filters, Snapchat AI, voice assistants, and smart autocomplete.
                            </p>
                            <p style="font-size:0.82rem; opacity:0.6; margin-bottom:12px;">
                                (Source: Reuters/Ipsos youth AI usage survey, 2024; Goldman Sachs AI adoption report)
                            </p>
                            <p style="font-size:0.95rem; margin-bottom:12px;">
                                How many <strong>phone charges</strong> of energy do you think that equals per week?
                            </p>
                            <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
                                <button onclick="document.getElementById('guess-reveal').style.display='block'; document.getElementById('guess-buttons').style.display='none'; document.getElementById('user-guess-1').textContent='You guessed: ~5 charges.';" class="guess-btn" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~5 charges</button>
                                <button onclick="document.getElementById('guess-reveal').style.display='block'; document.getElementById('guess-buttons').style.display='none'; document.getElementById('user-guess-1').textContent='You guessed: ~10 charges.';" class="guess-btn" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~10 charges</button>
                                <button onclick="document.getElementById('guess-reveal').style.display='block'; document.getElementById('guess-buttons').style.display='none'; document.getElementById('user-guess-1').textContent='You guessed: ~25 charges. Correct!';" class="guess-btn" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~25 charges</button>
                                <button onclick="document.getElementById('guess-reveal').style.display='block'; document.getElementById('guess-buttons').style.display='none'; document.getElementById('user-guess-1').textContent='You guessed: ~50 charges.';" class="guess-btn" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~50 charges</button>
                            </div>
                            <div id="guess-buttons"></div>
                            <div id="guess-reveal" style="display:none; padding:14px; background:#fee2e2; border-radius:8px; border:2px solid #ef4444;">
                                <div id="user-guess-1" style="font-size:0.9rem; font-weight:600; color:#7f1d1d; margin-bottom:6px; padding:6px 10px; background:rgba(127,29,29,0.08); border-radius:6px;"></div>
                                <div style="font-size:1.4rem; font-weight:900; color:#ef4444; margin-bottom:4px;">≈ 25 phone charges per week.</div>
                                <div style="font-size:0.95rem;">That's <strong>~1,000 charges over a school year</strong> — from ONE student, without realizing it.</div>
                                <div style="font-size:0.82rem; margin-top:4px; opacity:0.7;">Based on ~0.5 Wh avg/query across mixed AI use (Luccioni et al., 2023; IEA, 2024)</div>
                            </div>
                        </div>

                        <!-- CLASS MULTIPLIER — show the math -->
                        <div style="background:rgba(34,197,94,0.08); border:2px solid rgba(34,197,94,0.2); border-radius:12px; padding:16px; margin-bottom:18px;">
                            <div style="font-weight:800; font-size:1.05rem; color:#16a34a; margin-bottom:8px;">👥 Now scale it to this room</div>
                            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; text-align:center;">
                                <div style="background:white; padding:12px; border-radius:8px;">
                                    <div style="font-size:0.78rem; font-weight:600; opacity:0.6;">You alone</div>
                                    <div style="font-size:1.3rem; font-weight:900; color:#ef4444;">25/week</div>
                                </div>
                                <div style="background:white; padding:12px; border-radius:8px;">
                                    <div style="font-size:0.78rem; font-weight:600; opacity:0.6;">Your class (30 students)</div>
                                    <div style="font-size:1.3rem; font-weight:900; color:#ef4444;">750/week</div>
                                </div>
                                <div style="background:white; padding:12px; border-radius:8px;">
                                    <div style="font-size:0.78rem; font-weight:600; opacity:0.6;">Full school year (×40 weeks)</div>
                                    <div style="font-size:1.3rem; font-weight:900; color:#ef4444;">30,000</div>
                                    <div style="font-size:0.7rem; opacity:0.6;">phone charges</div>
                                </div>
                            </div>
                            <div style="text-align:center; font-size:0.78rem; opacity:0.5; margin-top:6px;">
                                Math: 25 charges × 30 students × 40 school weeks = 30,000
                            </div>
                        </div>

                        <!-- PERSONAL USAGE CALCULATOR — integrated label -->
                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:16px; margin-bottom:16px;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); margin-bottom:4px;">📊 YOUR Personal Footprint Calculator</div>
                            <p style="font-size:0.9rem; margin-bottom:4px; opacity:0.8;">👇 Use the slider right below to enter YOUR weekly AI prompts and see your real impact.</p>
                            <p style="font-size:0.78rem; margin-bottom:0; opacity:0.6;">
                                (This slider calculates an average across text and image tasks. Heavy image generation would be higher; text-only would be lower.)
                            </p>
                        </div>
        """,
    },

    # ─────────────────────────────────────────────
    # MODULE 2 — STEP 2: THE PHYSICAL TRIP (Network)
    # ─────────────────────────────────────────────
    {
        "id": 2,
        "title": "Step 2: The Network",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. YOUR CLICK</div>
                    <div class="tracker-step active">2. THE NETWORK</div>
                    <div class="tracker-step">3. THE GPU</div>
                    <div class="tracker-step">4. THE WATER</div>
                    <div class="tracker-step">5. THE PARADOX</div>
                </div>
                <h2 class="slide-title" style="text-align:center;">🌐 STEP 2: THE PHYSICAL TRIP</h2>
                <div class="slide-body">
                    <div style="max-width:800px; margin:0 auto;">

                        <!-- GEOGRAPHY HOOK — specific, visceral -->
                        <p style="font-size:1.15rem; text-align:center; margin-bottom:8px; font-weight:700;">
                            Right now, your last AI prompt is probably in Northern Virginia — or Dublin, or Singapore.
                        </p>
                        <p style="font-size:1rem; text-align:center; margin-bottom:20px; opacity:0.8;">
                            Most major AI models run from a handful of mega-data-centers. If you're in Europe, your prompt likely crossed the Atlantic. In the US, it may have traveled to Virginia or Oregon. Either way: thousands of kilometers, powered every meter.
                        </p>

                        <!-- GUESS INTERACTION — distance -->
                        <div style="background:rgba(99,102,241,0.08); border:2px solid rgba(99,102,241,0.2); border-radius:12px; padding:18px; margin-bottom:20px;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); margin-bottom:6px;">🤔 Before you see the route:</div>
                            <p style="font-size:0.95rem; margin-bottom:12px;">
                                How far do you think your prompt physically travels to reach an AI data center?
                            </p>
                            <div id="dist-guess-btns" style="display:flex; gap:8px; flex-wrap:wrap;">
                                <button onclick="document.getElementById('dist-reveal').style.display='block'; document.getElementById('dist-guess-btns').style.display='none'; document.getElementById('user-guess-2').textContent='You guessed: ~100 km.';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~100 km</button>
                                <button onclick="document.getElementById('dist-reveal').style.display='block'; document.getElementById('dist-guess-btns').style.display='none'; document.getElementById('user-guess-2').textContent='You guessed: ~1,000 km.';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~1,000 km</button>
                                <button onclick="document.getElementById('dist-reveal').style.display='block'; document.getElementById('dist-guess-btns').style.display='none'; document.getElementById('user-guess-2').textContent='You guessed: ~5,000 km. Close!';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~5,000 km</button>
                                <button onclick="document.getElementById('dist-reveal').style.display='block'; document.getElementById('dist-guess-btns').style.display='none'; document.getElementById('user-guess-2').textContent='You guessed: ~10,000+ km. Close!';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~10,000+ km</button>
                            </div>
                            <div id="dist-reveal" style="display:none; padding:14px; background:#fee2e2; border-radius:8px; border:2px solid #ef4444; margin-top:8px;">
                                <div id="user-guess-2" style="font-size:0.9rem; font-weight:600; color:#7f1d1d; margin-bottom:6px; padding:6px 10px; background:rgba(127,29,29,0.08); border-radius:6px;"></div>
                                <div style="font-size:1.3rem; font-weight:900; color:#ef4444;">~6,000 – 14,000 km round trip</div>
                                <div style="font-size:0.9rem; margin-top:3px;">Depending on your location. From Europe that's across the Atlantic and back — powered every meter of the way.</div>
                            </div>
                        </div>

                        <!-- PHONE BATTERY CALLBACK — bridge to their pocket -->
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
                            <div style="padding:14px; background:rgba(239,68,68,0.08); border-radius:8px; text-align:center; border:1px solid rgba(239,68,68,0.2);">
                                <div style="font-size:1.8rem;">🔋</div>
                                <div style="font-weight:700; font-size:0.95rem;">Your phone gets hot using AI apps?</div>
                                <div style="font-size:0.85rem; opacity:0.7;">That's the same physics — electricity → heat. Your phone is a tiny data center in your hand.</div>
                            </div>
                            <div style="padding:14px; background:rgba(34,197,94,0.08); border-radius:8px; text-align:center; border:1px solid rgba(34,197,94,0.2);">
                                <div style="font-size:1.8rem;">📍</div>
                                <div style="font-weight:700; font-size:0.95rem;">70% of US internet traffic</div>
                                <div style="font-size:0.85rem; opacity:0.7;">passes through one county in Virginia — Loudoun County, "Data Center Alley"</div>
                            </div>
                        </div>

                        <div style="padding:12px; background:#fef3c7; border-left:3px solid #f59e0b; border-radius:6px; font-size:0.9rem;">
                            <strong>🔑 Key Insight:</strong> The internet feels free and instant. But "instant" still means electricity burned across 7,000+ km of physical cable. <strong>Instant doesn't mean free.</strong>
                        </div>
                    </div>
                </div>
            </div>
        """,
    },

    # ─────────────────────────────────────────────
    # MODULE 3 — STEP 3: THE BRAIN IN THE BASEMENT (GPU)
    # ─────────────────────────────────────────────
    {
        "id": 3,
        "title": "Step 3: The GPU",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. YOUR CLICK</div>
                    <div class="tracker-step completed">2. THE NETWORK</div>
                    <div class="tracker-step active">3. THE GPU</div>
                    <div class="tracker-step">4. THE WATER</div>
                    <div class="tracker-step">5. THE PARADOX</div>
                </div>
                <h2 class="slide-title" style="text-align:center;">🧠 STEP 3: THE BRAIN IN THE BASEMENT</h2>
                <div class="slide-body">
                    <div style="max-width:800px; margin:0 auto;">

                        <p style="font-size:1.1rem; text-align:center; margin-bottom:20px;">
                            Your prompt arrived at a GPU — the processor that does the "thinking." You know the GPU in a PS5 that renders your games?
                            <br><strong>Now imagine 10,000 of them, stacked in a warehouse, running 24/7 at max power.</strong>
                        </p>

                        <!-- PS5 SCALING LADDER -->
                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:18px; margin-bottom:20px;">
                            <div style="font-weight:800; font-size:1rem; margin-bottom:12px; text-align:center;">🎮 FROM YOUR ROOM TO THE DATA CENTER</div>
                            <div style="display:grid; grid-template-columns:1fr auto 1fr auto 1fr; gap:6px; align-items:center; text-align:center;">
                                <div style="padding:12px; background:rgba(99,102,241,0.08); border-radius:8px;">
                                    <div style="font-size:1.8rem;">🎮</div>
                                    <div style="font-weight:800; font-size:0.85rem;">Your PS5</div>
                                    <div style="font-size:0.78rem; opacity:0.6;">1 GPU</div>
                                    <div style="font-size:0.78rem; opacity:0.6;">350W</div>
                                    <div style="font-size:0.78rem; opacity:0.6;">A few hrs/day</div>
                                </div>
                                <div style="font-size:1.3rem; color:var(--body-text-color-subdued);">→</div>
                                <div style="padding:12px; background:rgba(239,68,68,0.08); border-radius:8px;">
                                    <div style="font-size:1.8rem;">🖥️</div>
                                    <div style="font-weight:800; font-size:0.85rem;">1 AI Server Rack</div>
                                    <div style="font-size:0.78rem; opacity:0.6;">8 GPUs</div>
                                    <div style="font-size:0.78rem; color:#ef4444; font-weight:600;">10,000W</div>
                                    <div style="font-size:0.78rem; opacity:0.6;">24/7/365</div>
                                </div>
                                <div style="font-size:1.3rem; color:var(--body-text-color-subdued);">→</div>
                                <div style="padding:12px; background:rgba(239,68,68,0.15); border-radius:8px; border:2px solid #fca5a5;">
                                    <div style="font-size:1.8rem;">🏭</div>
                                    <div style="font-weight:800; font-size:0.85rem;">1 Data Center</div>
                                    <div style="font-size:0.78rem; opacity:0.6;">100,000+ GPUs</div>
                                    <div style="font-size:0.78rem; color:#ef4444; font-weight:700;">50-100 MW</div>
                                    <div style="font-size:0.78rem; color:#ef4444; font-weight:600;">= a town of ~80,000</div>
                                </div>
                            </div>
                            <div style="text-align:center; margin-top:10px; font-size:0.82rem; opacity:0.6;">
                                The heat from one data center could warm an Olympic swimming pool in hours.
                            </div>
                        </div>

                        <!-- GUESS FIRST — 10x comparison -->
                        <div style="background:rgba(99,102,241,0.08); border:2px solid rgba(99,102,241,0.2); border-radius:12px; padding:18px; margin-bottom:20px;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); margin-bottom:6px;">🤔 Take a guess:</div>
                            <p style="font-size:0.95rem; margin-bottom:12px;">
                                How many times more energy does a single ChatGPT query use compared to a Google search?
                            </p>
                            <div id="gpu-guess-btns" style="display:flex; gap:8px; flex-wrap:wrap;">
                                <button onclick="document.getElementById('gpu-reveal').style.display='block'; document.getElementById('gpu-guess-btns').style.display='none';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">2× more</button>
                                <button onclick="document.getElementById('gpu-reveal').style.display='block'; document.getElementById('gpu-guess-btns').style.display='none';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">5× more</button>
                                <button onclick="document.getElementById('gpu-reveal').style.display='block'; document.getElementById('gpu-guess-btns').style.display='none';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">10× more</button>
                                <button onclick="document.getElementById('gpu-reveal').style.display='block'; document.getElementById('gpu-guess-btns').style.display='none';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">50× more</button>
                            </div>
                            <div id="gpu-reveal" style="display:none;">
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:12px;">
                                    <div style="background:rgba(59,130,246,0.08); padding:16px; border-radius:12px; border:2px solid rgba(59,130,246,0.2); text-align:center;">
                                        <div style="font-size:0.8rem; font-weight:700; color:#3b82f6; text-transform:uppercase; margin-bottom:6px;">Google Search</div>
                                        <div style="font-size:2.5rem;">🔍</div>
                                        <div style="margin-top:8px; height:12px; background:#e5e7eb; border-radius:6px; overflow:hidden;">
                                            <div style="height:100%; width:10%; background:#3b82f6; border-radius:6px;"></div>
                                        </div>
                                        <div style="font-size:0.9rem; margin-top:4px; font-weight:700;">0.3 Wh</div>
                                    </div>
                                    <div style="background:rgba(239,68,68,0.08); padding:16px; border-radius:12px; border:2px solid rgba(239,68,68,0.2); text-align:center;">
                                        <div style="font-size:0.8rem; font-weight:700; color:#ef4444; text-transform:uppercase; margin-bottom:6px;">ChatGPT Query</div>
                                        <div style="font-size:2.5rem;">🤖</div>
                                        <div style="margin-top:8px; height:12px; background:#e5e7eb; border-radius:6px; overflow:hidden;">
                                            <div style="height:100%; width:100%; background:#ef4444; border-radius:6px;"></div>
                                        </div>
                                        <div style="font-size:0.9rem; margin-top:4px; font-weight:700; color:#ef4444;">3.0 Wh — 10× more ⚠️</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- COOKBOOK ANALOGY — intuitive, not technical -->
                        <div style="background:rgba(250,204,21,0.08); border:2px solid rgba(250,204,21,0.25); border-radius:12px; padding:16px; margin-bottom:18px;">
                            <div style="font-weight:800; font-size:1rem; margin-bottom:8px;">📖 TRAINING vs. INFERENCE — The Cookbook Analogy</div>
                            <p style="font-size:0.95rem; margin-bottom:0; line-height:1.6;">
                                <strong>Training</strong> is like writing a cookbook. You do it once — it's months of hard work — but then it's done.
                                <br><strong>Inference</strong> is like cooking every meal from that cookbook for <strong>200 million people, every single day, forever.</strong>
                                <br>The cookbook took effort. But the <em>cooking</em> never stops.
                            </p>
                        </div>

                        <!-- 11-DAY CLIMAX — with its own guess -->
                        <div style="background:#1e293b; color:#e2e8f0; padding:20px; border-radius:12px; margin-bottom:18px;">
                            <div style="color:#fbbf24; font-weight:800; margin-bottom:10px; text-align:center; font-size:1.05rem;">⚡ THE REAL ENERGY MONSTER</div>
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                                <div style="background:rgba(96,165,250,0.1); padding:12px; border-radius:8px;">
                                    <div style="font-weight:700; color:#60a5fa;">📖 TRAINING (one-time)</div>
                                    <div style="font-size:0.9rem; margin-top:4px;">GPT-3 training: <strong>1,287 MWh</strong></div>
                                    <div style="font-size:0.82rem; opacity:0.7;">= 120 homes powered for a year</div>
                                </div>
                                <div style="background:rgba(248,113,113,0.1); padding:12px; border-radius:8px;">
                                    <div style="font-weight:700; color:#f87171;">🔥 INFERENCE (daily)</div>
                                    <div style="font-size:0.9rem; margin-top:4px;">200M queries/day: <strong>~120 MWh/day</strong></div>
                                    <div style="font-size:0.82rem; opacity:0.7;">and growing every month</div>
                                </div>
                            </div>
                            <div style="text-align:center; margin-bottom:8px; font-size:0.95rem;">
                                Training consumed 1,287 MWh of energy over several months. At 120 MWh/day of inference, how many days until users have consumed that same <strong>amount of energy</strong>?
                            </div>
                            <div id="days-guess-btns" style="display:flex; gap:8px; flex-wrap:wrap; justify-content:center;">
                                <button onclick="document.getElementById('days-reveal').style.display='block'; document.getElementById('days-guess-btns').style.display='none'; document.getElementById('user-guess-3').textContent='You guessed: ~1 year.';" style="padding:6px 16px; border-radius:8px; border:2px solid rgba(250,204,21,0.3); background:rgba(255,255,255,0.05); color:white; font-weight:700; font-size:0.9rem; cursor:pointer;">~1 year</button>
                                <button onclick="document.getElementById('days-reveal').style.display='block'; document.getElementById('days-guess-btns').style.display='none'; document.getElementById('user-guess-3').textContent='You guessed: ~6 months.';" style="padding:6px 16px; border-radius:8px; border:2px solid rgba(250,204,21,0.3); background:rgba(255,255,255,0.05); color:white; font-weight:700; font-size:0.9rem; cursor:pointer;">~6 months</button>
                                <button onclick="document.getElementById('days-reveal').style.display='block'; document.getElementById('days-guess-btns').style.display='none'; document.getElementById('user-guess-3').textContent='You guessed: ~1 month.';" style="padding:6px 16px; border-radius:8px; border:2px solid rgba(250,204,21,0.3); background:rgba(255,255,255,0.05); color:white; font-weight:700; font-size:0.9rem; cursor:pointer;">~1 month</button>
                                <button onclick="document.getElementById('days-reveal').style.display='block'; document.getElementById('days-guess-btns').style.display='none'; document.getElementById('user-guess-3').textContent='You guessed: Less. Correct!';" style="padding:6px 16px; border-radius:8px; border:2px solid rgba(250,204,21,0.3); background:rgba(255,255,255,0.05); color:white; font-weight:700; font-size:0.9rem; cursor:pointer;">Less</button>
                            </div>
                            <div id="days-reveal" style="display:none; margin-top:12px; text-align:center; padding:16px; background:rgba(248,113,113,0.15); border-radius:10px; border:2px solid #f87171;">
                                <div id="user-guess-3" style="font-size:0.9rem; font-weight:600; color:#fca5a5; margin-bottom:6px; padding:6px 10px; background:rgba(248,113,113,0.1); border-radius:6px;"></div>
                                <div style="font-size:2.4rem; font-weight:900; color:#f87171;">~11 days.</div>
                                <div style="font-size:1rem; margin-top:4px; color:#fca5a5;">All those months of training? Users burned through the same energy in less than two weeks.</div>
                                <div style="font-size:0.82rem; margin-top:6px; opacity:0.6;">That was 2023. Usage has doubled since then.</div>
                            </div>
                        </div>

                        <!-- OPPORTUNITY COST — what ELSE could this power? -->
                        <div style="background:rgba(34,197,94,0.08); border:2px solid rgba(34,197,94,0.2); border-radius:12px; padding:16px; margin-bottom:16px;">
                            <div style="font-weight:800; font-size:1rem; color:#16a34a; margin-bottom:8px;">🔄 WHAT ELSE COULD THAT ENERGY DO?</div>
                            <p style="font-size:0.9rem; margin-bottom:10px;">ChatGPT's daily inference energy (~120 MWh/day) could instead:</p>
                            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; text-align:center;">
                                <div style="background:white; padding:10px; border-radius:8px;">
                                    <div style="font-size:1.4rem;">🏫</div>
                                    <div style="font-weight:700; font-size:0.85rem;">Power ~300 schools</div>
                                    <div style="font-size:0.75rem; opacity:0.6;">for a full day</div>
                                </div>
                                <div style="background:white; padding:10px; border-radius:8px;">
                                    <div style="font-size:1.4rem;">📱</div>
                                    <div style="font-weight:700; font-size:0.85rem;">Charge 10 million phones</div>
                                    <div style="font-size:0.75rem; opacity:0.6;">to 100%</div>
                                </div>
                                <div style="background:white; padding:10px; border-radius:8px;">
                                    <div style="font-size:1.4rem;">🚇</div>
                                    <div style="font-weight:700; font-size:0.85rem;">Run the London Tube</div>
                                    <div style="font-size:0.75rem; opacity:0.6;">for 8 hours</div>
                                </div>
                            </div>
                        </div>

                        <div style="padding:12px; background:#fef3c7; border-left:3px solid #f59e0b; border-radius:6px; font-size:0.9rem;">
                            <strong>🔑 Key Insight:</strong> Everyone talks about the cost of <em>training</em> AI. But <strong>inference — the daily use — overtakes training in just 11 days.</strong> The cooking costs more than the cookbook, and the restaurant never closes.
                        </div>
                    </div>
                </div>
            </div>
        """,
    },

    # ─────────────────────────────────────────────
    # MODULE 4 — STEP 4: THE THIRST FOR COOLING (Water)
    # ─────────────────────────────────────────────
    {
        "id": 4,
        "title": "Step 4: The Water",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. YOUR CLICK</div>
                    <div class="tracker-step completed">2. THE NETWORK</div>
                    <div class="tracker-step completed">3. THE GPU</div>
                    <div class="tracker-step active">4. THE WATER</div>
                    <div class="tracker-step">5. THE PARADOX</div>
                </div>
                <h2 class="slide-title" style="text-align:center;">💧 STEP 4: THE THIRST FOR COOLING</h2>
                <div class="slide-body">
                    <div style="max-width:800px; margin:0 auto;">

                        <!-- VISCERAL OPENER — WHY water specifically -->
                        <p style="font-size:1.1rem; text-align:center; margin-bottom:8px;">
                            Those 100,000 GPUs from Step 3? At full power, they produce so much heat they would <strong style="color:#ef4444;">physically melt their own circuits</strong> within minutes.
                        </p>
                        <p style="font-size:1.05rem; text-align:center; margin-bottom:20px; opacity:0.85;">
                            The solution? Evaporate massive amounts of water. It enters the atmosphere and falls as rain — but somewhere else entirely. For the local community, that water is <strong>gone for good.</strong>
                        </p>

                        <!-- GUESS FIRST — how much water per day? -->
                        <div style="background:rgba(99,102,241,0.08); border:2px solid rgba(99,102,241,0.2); border-radius:12px; padding:18px; margin-bottom:20px;">
                            <div style="font-weight:800; font-size:1.05rem; color:var(--color-accent); margin-bottom:6px;">🤔 Guess first:</div>
                            <p style="font-size:0.95rem; margin-bottom:12px;">
                                A single large AI data center uses how much water <strong>per day</strong>?
                            </p>
                            <div id="water-guess-btns" style="display:flex; gap:8px; flex-wrap:wrap;">
                                <button onclick="document.getElementById('water-reveal').style.display='block'; document.getElementById('water-guess-btns').style.display='none';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~1,000 liters</button>
                                <button onclick="document.getElementById('water-reveal').style.display='block'; document.getElementById('water-guess-btns').style.display='none';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~100,000 liters</button>
                                <button onclick="document.getElementById('water-reveal').style.display='block'; document.getElementById('water-guess-btns').style.display='none';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~1 million liters</button>
                                <button onclick="document.getElementById('water-reveal').style.display='block'; document.getElementById('water-guess-btns').style.display='none';" style="padding:8px 18px; border-radius:8px; border:2px solid rgba(99,102,241,0.3); background:white; font-weight:700; font-size:0.95rem; cursor:pointer;">~20 million liters</button>
                            </div>
                            <div id="water-reveal" style="display:none; padding:14px; background:#dbeafe; border-radius:8px; border:2px solid #3b82f6; margin-top:8px;">
                                <div style="font-size:1.4rem; font-weight:900; color:#1e40af;">~19 million liters / day</div>
                                <div style="font-size:0.95rem; margin-top:3px;">That's 5 million gallons — enough to supply <strong>50,000 people</strong> with their daily drinking water.</div>
                                <div style="font-size:0.82rem; margin-top:6px; opacity:0.7;">And that's just ONE data center. Google, Microsoft, and Meta each operate dozens.</div>
                            </div>
                        </div>

                        <!-- BATHTUB ANALOGY — make the scale intuitive -->
                        <div style="background:#1e293b; color:white; padding:18px; border-radius:12px; margin-bottom:20px;">
                            <div style="color:#60a5fa; font-weight:800; margin-bottom:12px; text-align:center;">🛁 THE BATHTUB TEST</div>
                            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; text-align:center;">
                                <div style="padding:12px; background:rgba(96,165,250,0.1); border-radius:8px;">
                                    <div style="font-size:2rem;">💬</div>
                                    <div style="font-size:0.78rem; color:#94a3b8;">20-25 AI prompts</div>
                                    <div style="font-size:1.1rem; font-weight:900; color:#60a5fa;">1 bottle</div>
                                    <div style="font-size:0.72rem; color:#94a3b8;">500ml</div>
                                </div>
                                <div style="padding:12px; background:rgba(96,165,250,0.15); border-radius:8px;">
                                    <div style="font-size:2rem;">📱</div>
                                    <div style="font-size:0.78rem; color:#94a3b8;">Your weekly AI use (50/wk)</div>
                                    <div style="font-size:1.1rem; font-weight:900; color:#60a5fa;">~1 liter</div>
                                    <div style="font-size:0.72rem; color:#94a3b8;">evaporated/week</div>
                                </div>
                                <div style="padding:12px; background:rgba(248,113,113,0.15); border-radius:8px;">
                                    <div style="font-size:2rem;">🏫</div>
                                    <div style="font-size:0.78rem; color:#94a3b8;">Your class (30 students/yr)</div>
                                    <div style="font-size:1.1rem; font-weight:900; color:#f87171;">~1,200 liters</div>
                                    <div style="font-size:0.72rem; color:#94a3b8;">= 7 full bathtubs</div>
                                </div>
                            </div>
                            <div style="text-align:center; margin-top:10px; padding:8px; background:rgba(248,113,113,0.1); border-radius:6px; font-size:0.85rem;">
                                7 bathtubs from one class sounds small next to a data center's 19 million liters/day. But that's the point: <strong style="color:#f87171;">the data center exists because millions of classes are all sending prompts at once.</strong> Your 7 bathtubs × every class in the world = the data center.
                            </div>
                            <div style="text-align:center; font-size:0.72rem; color:#64748b; margin-top:6px;">Source: Li et al., 2023, UC Riverside</div>
                        </div>

                        <!-- REAL PEOPLE — not just stats, human stories -->
                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:18px; margin-bottom:18px;">
                            <div style="font-weight:800; font-size:1.05rem; margin-bottom:12px;">🗣️ REAL PEOPLE, REAL CONFLICT</div>
                            <div style="display:grid; gap:10px;">
                                <div style="padding:12px; background:rgba(239,68,68,0.06); border-radius:8px; border-left:4px solid #ef4444;">
                                    <div style="font-weight:700; font-size:0.95rem;">🇺🇸 Mesa, Arizona (2023)</div>
                                    <div style="font-size:0.88rem; line-height:1.5; margin-top:4px;">
                                        During the worst drought in 1,200 years, residents discovered Microsoft's data center was using <strong>56 million gallons/year</strong> of their water. Families were told to shorten showers while a server farm evaporated enough water to supply 670 homes.
                                    </div>
                                </div>
                                <div style="padding:12px; background:rgba(59,130,246,0.06); border-radius:8px; border-left:4px solid #3b82f6;">
                                    <div style="font-weight:700; font-size:0.95rem;">📊 Google Global (2023)</div>
                                    <div style="font-size:0.88rem; line-height:1.5; margin-top:4px;">
                                        Total water use: <strong>5.6 billion gallons</strong> — up 17% from the previous year. That's enough to fill 8,500 Olympic swimming pools, evaporated in a single year.
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- THE INVISIBLE PIPELINE -->
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
                            <div style="padding:14px; background:rgba(239,68,68,0.08); border-radius:8px; text-align:center; border:1px solid rgba(239,68,68,0.2);">
                                <div style="font-size:1.8rem;">🏜️</div>
                                <div style="font-weight:700; font-size:0.95rem;">Why drought zones?</div>
                                <div style="font-size:0.85rem; opacity:0.7;">Land is cheap in dry areas. Tech companies save billions — and local communities pay with their water.</div>
                            </div>
                            <div style="padding:14px; background:rgba(34,197,94,0.08); border-radius:8px; text-align:center; border:1px solid rgba(34,197,94,0.2);">
                                <div style="font-size:1.8rem;">♻️</div>
                                <div style="font-weight:700; font-size:0.95rem;">Can't we just recycle it?</div>
                                <div style="font-size:0.85rem; opacity:0.7;">Evaporative cooling turns water into vapor. It re-enters the water cycle — but as rain in a different watershed. The local community doesn't get it back.</div>
                            </div>
                        </div>

                        <div style="padding:12px; background:#fef3c7; border-left:3px solid #f59e0b; border-radius:6px; font-size:0.9rem;">
                            <strong>🔑 Key Insight:</strong> This isn't just environmental — it's a <strong>justice</strong> problem. The heaviest AI users (wealthy nations) aren't the ones losing water. Data centers go where land and water are cheap — and local communities bear the cost of someone else's convenience.
                        </div>
                    </div>
                </div>
            </div>
        """,
    },

    # ─────────────────────────────────────────────
    # MODULE 5 — STEP 5: THE SUSTAINABILITY PARADOX
    # ─────────────────────────────────────────────
    {
        "id": 5,
        "title": "Step 5: The Paradox",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">1. YOUR CLICK</div>
                    <div class="tracker-step completed">2. THE NETWORK</div>
                    <div class="tracker-step completed">3. THE GPU</div>
                    <div class="tracker-step completed">4. THE WATER</div>
                    <div class="tracker-step active">5. THE PARADOX</div>
                </div>
                <h2 class="slide-title" style="text-align:center;">⚖️ STEP 5: THE SUSTAINABILITY PARADOX</h2>
                <div class="slide-body">
                    <div style="max-width:800px; margin:0 auto;">

                        <!-- OPEN WITH THE CONTRADICTION — not a summary, a genuine puzzle -->
                        <p style="font-size:1.1rem; text-align:center; margin-bottom:6px;">
                            Here's the twist that makes this whole investigation complicated:
                        </p>
                        <div style="text-align:center; margin-bottom:20px;">
                            <span style="font-size:1.2rem; font-weight:800; color:#ef4444;">AI is destroying the environment</span>
                            <span style="font-size:1.2rem; font-weight:800; opacity:0.4; margin:0 10px;">&</span>
                            <span style="font-size:1.2rem; font-weight:800; color:#22c55e;">AI is saving the environment.</span>
                            <br><span style="font-size:1rem; opacity:0.7; font-weight:600;">Both are true. At the same time.</span>
                        </div>

                        <!-- INTERACTIVE SORT — classify real AI uses -->
                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:18px; margin-bottom:20px;">
                            <div style="font-weight:800; font-size:1.05rem; margin-bottom:6px;">🧪 CONTEXT FOR YOUR DECISION</div>
                            <p style="font-size:0.88rem; margin-bottom:12px; opacity:0.7;">Tap each use case to see its environmental cost and benefit. Then form your own opinion: <em>"Does the benefit justify the electricity and water?"</em></p>

                            <div style="display:grid; gap:8px;" id="sort-cases">
                                <details style="border-radius:8px; overflow:hidden; border:2px solid rgba(148,163,184,0.3);">
                                    <summary style="padding:12px; font-weight:700; cursor:pointer; display:flex; justify-content:space-between; align-items:center; background:rgba(148,163,184,0.05);">
                                        <span>🎨 Generating 50 AI memes for a group chat</span>
                                        <span style="font-size:0.75rem; color:#94a3b8;">TAP</span>
                                    </summary>
                                    <div style="padding:12px; border-top:1px solid rgba(148,163,184,0.15); font-size:0.9rem;">
                                        <div style="font-weight:700; color:#ef4444; margin-bottom:4px;">⚖️ COST: ~25 phone charges of energy. Half a liter of water evaporated.</div>
                                        <div>BENEFIT: Entertainment for ~10 minutes. Could you have found a similar meme with a Google Image search at 1/10th the energy? Probably.</div>
                                    </div>
                                </details>

                                <details style="border-radius:8px; overflow:hidden; border:2px solid rgba(148,163,184,0.3);">
                                    <summary style="padding:12px; font-weight:700; cursor:pointer; display:flex; justify-content:space-between; align-items:center; background:rgba(148,163,184,0.05);">
                                        <span>🌾 AI predicting crop disease to save 30% of a harvest</span>
                                        <span style="font-size:0.75rem; color:#94a3b8;">TAP</span>
                                    </summary>
                                    <div style="padding:12px; border-top:1px solid rgba(148,163,184,0.15); font-size:0.9rem;">
                                        <div style="font-weight:700; color:#22c55e; margin-bottom:4px;">⚖️ COST: Significant computation. BENEFIT: Feeding thousands of families.</div>
                                        <div>This one AI system might save more water (through reduced irrigation waste) than it consumes for cooling. <strong>Net positive.</strong></div>
                                    </div>
                                </details>

                                <details style="border-radius:8px; overflow:hidden; border:2px solid rgba(148,163,184,0.3);">
                                    <summary style="padding:12px; font-weight:700; cursor:pointer; display:flex; justify-content:space-between; align-items:center; background:rgba(148,163,184,0.05);">
                                        <span>📚 Student using AI to understand a difficult concept they're stuck on</span>
                                        <span style="font-size:0.75rem; color:#94a3b8;">TAP</span>
                                    </summary>
                                    <div style="padding:12px; border-top:1px solid rgba(148,163,184,0.15); font-size:0.9rem;">
                                        <div style="font-weight:700; color:#f59e0b; margin-bottom:4px;">⚖️ COST: A few prompts. BENEFIT: Genuine learning that couldn't happen otherwise.</div>
                                        <div>This one's genuinely debatable. If the textbook or a tutor could have helped, it's less justified. If AI is the only resource available? <strong>Probably worth it.</strong> Context matters.</div>
                                    </div>
                                </details>
                            </div>
                        </div>

                        <!-- THE FRAMEWORK — the tool they take away -->
                        <div style="background:#1e293b; color:white; padding:20px; border-radius:12px; margin-bottom:18px;">
                            <div style="text-align:center; margin-bottom:14px;">
                                <div style="font-size:0.78rem; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:1.5px;">THE GREEN AI DETECTIVE'S FRAMEWORK</div>
                                <div style="font-size:1.3rem; font-weight:900; color:#fbbf24; margin-top:6px;">Before you send any prompt, ask:</div>
                            </div>
                            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; text-align:center;">
                                <div style="padding:14px; background:rgba(250,204,21,0.1); border-radius:8px;">
                                    <div style="font-size:1.6rem;">1️⃣</div>
                                    <div style="font-weight:700; font-size:0.9rem; margin-top:4px;">Do I need AI for this?</div>
                                    <div style="font-size:0.78rem; color:#94a3b8; margin-top:4px;">Could a search engine, textbook, or my own thinking handle it?</div>
                                </div>
                                <div style="padding:14px; background:rgba(250,204,21,0.1); border-radius:8px;">
                                    <div style="font-size:1.6rem;">2️⃣</div>
                                    <div style="font-weight:700; font-size:0.9rem; margin-top:4px;">Is the benefit real?</div>
                                    <div style="font-size:0.78rem; color:#94a3b8; margin-top:4px;">Learning, safety, health — or just convenience I could skip?</div>
                                </div>
                                <div style="padding:14px; background:rgba(250,204,21,0.1); border-radius:8px;">
                                    <div style="font-size:1.6rem;">3️⃣</div>
                                    <div style="font-weight:700; font-size:0.9rem; margin-top:4px;">Am I being efficient?</div>
                                    <div style="font-size:0.78rem; color:#94a3b8; margin-top:4px;">One clear, detailed prompt beats 12 vague attempts. Follow-ups are fine — mindless repetition isn't.</div>
                                </div>
                            </div>
                        </div>

                        <!-- PHASE 1 CAPSTONE — the real question -->
                        <div style="text-align:center; padding:16px; background:linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.08)); border:2px solid rgba(99,102,241,0.2); border-radius:12px; margin-bottom:16px;">
                            <div style="font-size:0.78rem; font-weight:700; color:#6366f1; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">🏁 PHASE 1 COMPLETE</div>
                            <div style="font-size:1.15rem; font-weight:800; margin-bottom:6px;">You've traced the full journey: Click → Network → GPU → Water → Paradox</div>
                            <div style="font-size:0.95rem; opacity:0.7;">Phase 2 scales this from your screen to the entire planet.</div>
                        </div>

                        <div style="padding:12px; background:#fef3c7; border-left:3px solid #f59e0b; border-radius:6px; font-size:0.9rem;">
                            <strong>🔑 Key Insight:</strong> The answer is never "all AI is bad" or "all AI is good." It's: <strong>"Is THIS specific use worth its environmental cost?"</strong> That one question, applied every time, is more powerful than any ban.
                        </div>
                    </div>
                </div>
            </div>
        """,
    },

    # ─────────────────────────────────────────────
    # MODULE 6 — STEP 6: GLOBAL SCALE (Merged: City + Ranking + E-Waste bonus)
    # ─────────────────────────────────────────────
    {
        "id": 6,
        "title": "Step 6: Global Scale",
        "html": """
            <div class="scenario-box">
                <div class="phase-banner" style="background:linear-gradient(135deg, #ef4444, #dc2626); color:white; padding:12px; border-radius:8px; text-align:center; margin-bottom:16px; font-weight:800; font-size:1.05rem;">
                    🔴 PHASE 2: SCALING THE IMPACT — FROM YOUR SCREEN TO THE PLANET
                </div>
                <div class="tracker-container">
                    <div class="tracker-step active">6. GLOBAL SCALE</div>
                    <div class="tracker-step">7. YOUR AUDIT</div>
                </div>
                <h2 class="slide-title" style="text-align:center;">🌍 STEP 6: GLOBAL SCALE</h2>
                <div class="slide-body">
                    <div style="max-width:800px; margin:0 auto;">

                        <!-- PERSONAL BRIDGE — connect back to Phase 1 -->
                        <p style="font-size:1.1rem; text-align:center; margin-bottom:6px;">
                            In Phase 1, you calculated your class evaporates <strong style="color:#ef4444;">7 bathtubs of water</strong> per year and burns <strong style="color:#ef4444;">30,000 phone charges</strong>.
                        </p>
                        <p style="font-size:1.05rem; text-align:center; margin-bottom:20px; opacity:0.85;">
                            There are roughly <strong>500,000 secondary schools in Europe alone.</strong> Let's multiply.
                        </p>

                        <!-- SCALER — from class to continent -->
                        <div style="background:#1e293b; color:white; padding:20px; border-radius:12px; margin-bottom:20px;">
                            <div style="color:#fbbf24; font-weight:800; text-align:center; margin-bottom:14px;">📐 THE CLASS-TO-CONTINENT SCALER</div>
                            <div style="display:grid; grid-template-columns:1fr auto 1fr auto 1fr; gap:6px; align-items:center; text-align:center;">
                                <div style="padding:12px; background:rgba(96,165,250,0.1); border-radius:8px;">
                                    <div style="font-size:1.6rem;">🧑‍🎓</div>
                                    <div style="font-weight:700; font-size:0.85rem;">Your class</div>
                                    <div style="font-size:0.85rem; color:#60a5fa;">30,000 charges/yr</div>
                                    <div style="font-size:0.78rem; color:#94a3b8;">7 bathtubs water</div>
                                </div>
                                <div style="color:#475569;">×</div>
                                <div style="padding:12px; background:rgba(250,204,21,0.1); border-radius:8px;">
                                    <div style="font-size:1.6rem;">🏫</div>
                                    <div style="font-weight:700; font-size:0.85rem;">Europe's schools</div>
                                    <div style="font-size:0.85rem; color:#fbbf24;">~500,000</div>
                                    <div style="font-size:0.78rem; color:#94a3b8;">secondary schools</div>
                                </div>
                                <div style="color:#475569;">=</div>
                                <div style="padding:12px; background:rgba(248,113,113,0.15); border-radius:8px; border:2px solid #f87171;">
                                    <div style="font-size:1.6rem;">🌍</div>
                                    <div style="font-weight:700; font-size:0.85rem;">Just students</div>
                                    <div style="font-size:0.85rem; color:#f87171; font-weight:800;">15 BILLION charges</div>
                                    <div style="font-size:0.78rem; color:#fca5a5;">3.5M bathtubs of water</div>
                                </div>
                            </div>
                            <div style="text-align:center; margin-top:12px; padding:8px; background:rgba(248,113,113,0.1); border-radius:6px; font-size:0.88rem;">
                                And that's <strong style="color:#fbbf24;">only students</strong>. Add offices, hospitals, governments, and the 200M daily ChatGPT users worldwide...
                            </div>
                        </div>

                        <!-- GLOBAL ELECTRICITY RANKING -->
                        <div style="background:#1e293b; color:white; padding:18px; border-radius:12px; margin-bottom:20px;">
                            <div style="color:#fbbf24; font-weight:800; margin-bottom:12px; text-align:center;">⚡ GLOBAL ELECTRICITY RANKING (2026 projection)</div>
                            <div style="display:grid; gap:8px;">
                                <div style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:rgba(255,255,255,0.05); border-radius:6px;">
                                    <span style="font-weight:800; color:#94a3b8; width:24px;">#1</span>
                                    <span style="font-size:1.2rem;">🇨🇳</span>
                                    <span style="flex:1;">China</span>
                                    <div style="width:180px; height:8px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                                        <div style="height:100%; width:100%; background:#60a5fa;"></div>
                                    </div>
                                </div>
                                <div style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:rgba(255,255,255,0.05); border-radius:6px;">
                                    <span style="font-weight:800; color:#94a3b8; width:24px;">#2</span>
                                    <span style="font-size:1.2rem;">🇺🇸</span>
                                    <span style="flex:1;">United States</span>
                                    <div style="width:180px; height:8px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                                        <div style="height:100%; width:65%; background:#60a5fa;"></div>
                                    </div>
                                </div>
                                <div style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:rgba(255,255,255,0.05); border-radius:6px;">
                                    <span style="font-weight:800; color:#94a3b8; width:24px;">#3</span>
                                    <span style="font-size:1.2rem;">🇮🇳</span>
                                    <span style="flex:1;">India</span>
                                    <div style="width:180px; height:8px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                                        <div style="height:100%; width:45%; background:#60a5fa;"></div>
                                    </div>
                                </div>
                                <div style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:rgba(255,255,255,0.05); border-radius:6px;">
                                    <span style="font-weight:800; color:#94a3b8; width:24px;">#4</span>
                                    <span style="font-size:1.2rem;">🇯🇵</span>
                                    <span style="flex:1;">Japan</span>
                                    <div style="width:180px; height:8px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                                        <div style="height:100%; width:30%; background:#60a5fa;"></div>
                                    </div>
                                </div>
                                <div style="display:flex; align-items:center; gap:10px; padding:10px 12px; background:rgba(239,68,68,0.15); border-radius:6px; border:2px solid #f87171;">
                                    <span style="font-weight:900; color:#f87171; width:24px;">#5</span>
                                    <span style="font-size:1.2rem;">🖥️</span>
                                    <span style="flex:1; font-weight:800; color:#f87171;">DATA CENTERS</span>
                                    <div style="width:180px; height:8px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                                        <div style="height:100%; width:25%; background:#f87171;"></div>
                                    </div>
                                </div>
                                <div style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:rgba(255,255,255,0.05); border-radius:6px;">
                                    <span style="font-weight:800; color:#94a3b8; width:24px;">#6</span>
                                    <span style="font-size:1.2rem;">🇷🇺</span>
                                    <span style="flex:1;">Russia</span>
                                    <div style="width:180px; height:8px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                                        <div style="height:100%; width:22%; background:#60a5fa;"></div>
                                    </div>
                                </div>
                            </div>
                            <div style="text-align:center; margin-top:10px; font-size:0.8rem; color:#94a3b8;">Source: IEA Electricity 2024 Report</div>
                        </div>

                        <!-- REAL STORY — Dublin -->
                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:18px; margin-bottom:18px;">
                            <div style="font-weight:800; font-size:1.05rem; margin-bottom:10px;">🇮🇪 REAL STORY: Dublin Said "No More"</div>
                            <div style="padding:12px; background:rgba(239,68,68,0.06); border-radius:8px; border-left:4px solid #ef4444; margin-bottom:10px;">
                                <div style="font-size:0.92rem; line-height:1.5;">
                                    By 2022, data centers were consuming <strong>18% of Ireland's entire electricity supply</strong> — heading toward 30%. Ireland's grid operator warned of blackout risks. Dublin imposed a <strong>moratorium: no new data centers</strong> until the grid could cope. Amazon, Microsoft, and Google all had expansion plans frozen.
                                </div>
                                <div style="font-size:0.78rem; opacity:0.6; margin-top:6px;">Source: EirGrid, Irish Times, 2022</div>
                            </div>
                            <div style="font-size:0.9rem; font-style:italic; opacity:0.8;">
                                "A country literally told Big Tech: 'You're taking too much. Stop.'"
                            </div>
                        </div>

                        <!-- 2030 PROJECTION -->
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:18px;">
                            <div style="padding:16px; background:var(--background-fill-secondary); border-radius:12px; border:2px solid var(--border-color-primary); text-align:center;">
                                <div style="font-size:0.78rem; font-weight:700; opacity:0.6; text-transform:uppercase;">2026 (now)</div>
                                <div style="font-size:2rem; font-weight:900; color:#f59e0b; margin:6px 0;">#5</div>
                                <div style="font-size:0.88rem;">Between Japan and Russia</div>
                                <div style="font-size:0.82rem; opacity:0.6;">~1,000 TWh/year</div>
                            </div>
                            <div style="padding:16px; background:rgba(239,68,68,0.06); border-radius:12px; border:2px solid #fca5a5; text-align:center;">
                                <div style="font-size:0.78rem; font-weight:700; color:#ef4444; text-transform:uppercase;">2030 (projected)</div>
                                <div style="font-size:2rem; font-weight:900; color:#ef4444; margin:6px 0;">#3–4?</div>
                                <div style="font-size:0.88rem;">Challenging India for #3</div>
                                <div style="font-size:0.82rem; color:#ef4444;">~1,800 TWh/year (IEA high scenario)</div>
                            </div>
                        </div>

                        <!-- "Powered by renewables" insight -->
                        <div style="background:rgba(250,204,21,0.08); border:2px solid rgba(250,204,21,0.25); border-radius:12px; padding:16px; margin-bottom:18px;">
                            <div style="font-weight:800; font-size:1rem; margin-bottom:8px;">⚠️ "Powered by Renewables" — Read the Fine Print</div>
                            <p style="font-size:0.92rem; line-height:1.5; margin:0;">
                                When tech companies claim "100% renewable energy," they usually mean they <strong>bought renewable energy certificates</strong> — not that their data center actually runs on clean power. The local grid still burns fossil fuels to meet AI's actual demand. "Powered by renewables" often means <strong>"we bought certificates"</strong> — not "we use clean power."
                            </p>
                            <div style="font-size:0.78rem; opacity:0.6; margin-top:6px;">Source: IEA, Goldman Sachs "Generational Growth" report, 2024</div>
                        </div>

                        <!-- E-WASTE BONUS — collapsible details -->
                        <details style="border-radius:10px; overflow:hidden; border:2px solid rgba(148,163,184,0.3); margin-bottom:18px;">
                            <summary style="padding:14px; font-weight:800; cursor:pointer; display:flex; justify-content:space-between; align-items:center; background:rgba(148,163,184,0.05); font-size:1rem;">
                                <span>🪦 BONUS: The Hardware Graveyard (E-Waste)</span>
                                <span style="font-size:0.75rem; color:#94a3b8;">TAP TO EXPLORE</span>
                            </summary>
                            <div style="padding:16px; border-top:1px solid rgba(148,163,184,0.15);">
                                <p style="font-size:0.95rem; margin-bottom:12px;">
                                    A GPU server component weighs about <strong>4 lbs</strong>. But producing it requires mining <strong style="color:#ef4444;">1,763 lbs of raw materials</strong> — a 440:1 ratio. And these GPUs get replaced every 3–5 years, not because they break, but because newer chips are faster and companies must stay competitive.
                                </p>
                                <div style="padding:12px; background:rgba(239,68,68,0.06); border-radius:8px; border-left:4px solid #ef4444; margin-bottom:10px;">
                                    <div style="font-weight:700; font-size:0.95rem;">🇬🇭 Agbogbloshie, Ghana</div>
                                    <div style="font-size:0.88rem; line-height:1.5; margin-top:4px;">
                                        One of the world's largest e-waste dumps until its closure in 2021. Workers — some as young as 12 — burned circuit boards over open fires to extract copper and gold. The site was declared one of the <strong>most polluted places on Earth</strong>.
                                    </div>
                                    <div style="font-size:0.78rem; opacity:0.6; margin-top:4px;">Source: UN E-Waste Monitor, 2024; Blacksmith Institute</div>
                                </div>
                                <div style="font-size:0.88rem; font-style:italic; opacity:0.8;">
                                    Only 22.3% of global e-waste is properly recycled. The AI arms race — replacing working GPUs every 18 months — produces industrial-scale waste from functional equipment.
                                </div>
                            </div>
                        </details>

                        <div style="padding:12px; background:#fef3c7; border-left:3px solid #f59e0b; border-radius:6px; font-size:0.9rem;">
                            <strong>🔑 Key Insight:</strong> Your 7 bathtubs × every class in the world = a country's worth of electricity. Data centers rank #5 globally and are heading to #3 by 2030. AI's demand is growing so fast that <strong>entire nations are hitting the brakes.</strong>
                        </div>
                    </div>
                </div>
            </div>
        """,
    },

    # ─────────────────────────────────────────────
    # MODULE 7 — STEP 7: YOUR ETHICAL AUDIT (Capstone)
    # ─────────────────────────────────────────────
    {
        "id": 7,
        "title": "Step 7: Your Audit",
        "html": """
            <div class="scenario-box">
                <div class="tracker-container">
                    <div class="tracker-step completed">6. GLOBAL SCALE</div>
                    <div class="tracker-step active">7. YOUR AUDIT</div>
                </div>
                <h2 class="slide-title" style="text-align:center;">📋 STEP 7: YOUR ETHICAL AUDIT</h2>
                <div class="slide-body">
                    <div style="max-width:800px; margin:0 auto;">

                        <p style="font-size:1.1rem; text-align:center; margin-bottom:6px;">
                            You've traced AI's real cost across <strong>8 steps</strong>:
                        </p>
                        <p style="font-size:1rem; text-align:center; margin-bottom:20px; opacity:0.8;">
                            Click → Network → GPU → Water → Paradox → Global Scale → <strong>Now: Your Verdict.</strong>
                        </p>

                        <!-- THE LAW -->
                        <div style="background:rgba(99,102,241,0.08); border:2px solid rgba(99,102,241,0.2); padding:18px; border-radius:12px; margin-bottom:20px;">
                            <div style="font-weight:800; color:var(--color-accent); margin-bottom:10px;">📜 THE LAW IS CATCHING UP — AND IT AFFECTS YOU</div>
                            <p style="font-size:0.95rem; margin-bottom:10px; line-height:1.5;">The EU AI Act (2024) will require AI providers to publish their <strong>energy and water consumption</strong>. By 2026, every AI product in Europe must carry environmental disclosures — like the <strong>energy labels on your fridge or washing machine.</strong></p>
                            <p style="font-size:0.95rem; margin:0; line-height:1.5;">This means: soon, you'll be able to <em>see</em> how much energy and water your AI tools actually use. The invisibility from Step 0? It's ending.</p>
                            <div style="font-size:0.78rem; opacity:0.6; margin-top:6px;">Source: EU AI Act, Article 53; European Commission, 2024</div>
                        </div>

                        <!-- SUMMARY TABLE -->
                        <div style="margin-bottom:20px;">
                            <div style="font-weight:800; margin-bottom:12px; font-size:1.05rem;">📊 YOUR 8-STEP INVESTIGATION — THE EVIDENCE</div>
                            <table style="width:100%; border-collapse:collapse; border-radius:8px; overflow:hidden; border:1px solid var(--border-color-primary);">
                                <thead>
                                    <tr style="background:var(--background-fill-secondary);">
                                        <th style="padding:10px; text-align:left; font-size:0.85rem;">Step</th>
                                        <th style="padding:10px; text-align:left; font-size:0.85rem;">What You Found</th>
                                        <th style="padding:10px; text-align:left; font-size:0.85rem;">The Number to Remember</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom:1px solid var(--border-color-primary);">
                                        <td style="padding:8px; font-weight:600;">📱 Your Click</td>
                                        <td style="padding:8px; font-size:0.88rem;">~25 phone charges/week</td>
                                        <td style="padding:8px; font-size:0.88rem; color:#ef4444; font-weight:700;">30,000 charges/class/yr</td>
                                    </tr>
                                    <tr style="border-bottom:1px solid var(--border-color-primary);">
                                        <td style="padding:8px; font-weight:600;">🌐 The Network</td>
                                        <td style="padding:8px; font-size:0.88rem;">7,200 km per prompt</td>
                                        <td style="padding:8px; font-size:0.88rem; color:#ef4444; font-weight:700;">10× more than Google</td>
                                    </tr>
                                    <tr style="border-bottom:1px solid var(--border-color-primary);">
                                        <td style="padding:8px; font-weight:600;">🧠 The GPU</td>
                                        <td style="padding:8px; font-size:0.88rem;">Training vs inference</td>
                                        <td style="padding:8px; font-size:0.88rem; color:#ef4444; font-weight:700;">11 days to match training</td>
                                    </tr>
                                    <tr style="border-bottom:1px solid var(--border-color-primary);">
                                        <td style="padding:8px; font-weight:600;">💧 The Water</td>
                                        <td style="padding:8px; font-size:0.88rem;">19M liters/day/center</td>
                                        <td style="padding:8px; font-size:0.88rem; color:#ef4444; font-weight:700;">7 bathtubs/class/yr</td>
                                    </tr>
                                    <tr style="border-bottom:1px solid var(--border-color-primary);">
                                        <td style="padding:8px; font-weight:600;">⚖️ The Paradox</td>
                                        <td style="padding:8px; font-size:0.88rem;">Some AI helps, some wastes</td>
                                        <td style="padding:8px; font-size:0.88rem; color:#6366f1; font-weight:700;">3-question framework</td>
                                    </tr>
                                    <tr style="border-bottom:1px solid var(--border-color-primary);">
                                        <td style="padding:8px; font-weight:600;">🌍 Global Scale</td>
                                        <td style="padding:8px; font-size:0.88rem;">Dublin moratorium, #5 globally</td>
                                        <td style="padding:8px; font-size:0.88rem; color:#ef4444; font-weight:700;">18% of Ireland's grid, heading to #3</td>
                                    </tr>
                                    <tr>
                                        <td style="padding:8px; font-weight:600;">📋 Your Audit</td>
                                        <td style="padding:8px; font-size:0.88rem;">You decide what's worth it</td>
                                        <td style="padding:8px; font-size:0.88rem; color:#22c55e; font-weight:700;">⬇️ Right now</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <!-- PERSONAL AUDIT ACTIVITY -->
                        <div style="background:#1e293b; color:white; padding:20px; border-radius:12px; margin-bottom:20px;">
                            <div style="color:#fbbf24; font-weight:800; text-align:center; margin-bottom:10px; font-size:1.1rem;">🔍 YOUR PERSONAL AI AUDIT</div>
                            <p style="font-size:0.95rem; text-align:center; margin-bottom:14px; opacity:0.85;">Think of 3 AI tools or habits you used <strong>this week</strong>. For each, apply the 3-question framework:</p>
                            <div style="display:grid; gap:10px; margin-bottom:14px;">
                                <div style="padding:14px; background:rgba(250,204,21,0.08); border-radius:8px; border:1px solid rgba(250,204,21,0.2);">
                                    <div style="display:flex; gap:12px; align-items:center;">
                                        <span style="font-size:1.5rem;">1️⃣</span>
                                        <div>
                                            <div style="font-weight:700;">AI tool: _____________</div>
                                            <div style="font-size:0.88rem; color:#94a3b8; margin-top:2px;">Did I need AI? Was the benefit real? Was I efficient?</div>
                                            <div style="font-size:0.85rem; margin-top:4px;">My verdict: 🟢 Worth it / 🟡 Debatable / 🔴 Could skip</div>
                                        </div>
                                    </div>
                                </div>
                                <div style="padding:14px; background:rgba(250,204,21,0.08); border-radius:8px; border:1px solid rgba(250,204,21,0.2);">
                                    <div style="display:flex; gap:12px; align-items:center;">
                                        <span style="font-size:1.5rem;">2️⃣</span>
                                        <div>
                                            <div style="font-weight:700;">AI tool: _____________</div>
                                            <div style="font-size:0.88rem; color:#94a3b8; margin-top:2px;">Did I need AI? Was the benefit real? Was I efficient?</div>
                                            <div style="font-size:0.85rem; margin-top:4px;">My verdict: 🟢 Worth it / 🟡 Debatable / 🔴 Could skip</div>
                                        </div>
                                    </div>
                                </div>
                                <div style="padding:14px; background:rgba(250,204,21,0.08); border-radius:8px; border:1px solid rgba(250,204,21,0.2);">
                                    <div style="display:flex; gap:12px; align-items:center;">
                                        <span style="font-size:1.5rem;">3️⃣</span>
                                        <div>
                                            <div style="font-weight:700;">AI tool: _____________</div>
                                            <div style="font-size:0.88rem; color:#94a3b8; margin-top:2px;">Did I need AI? Was the benefit real? Was I efficient?</div>
                                            <div style="font-size:0.85rem; margin-top:4px;">My verdict: 🟢 Worth it / 🟡 Debatable / 🔴 Could skip</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div style="text-align:center; padding:10px; background:rgba(250,204,21,0.1); border-radius:8px; font-size:0.88rem; color:#fbbf24;">
                                💡 Most people find at least one 🔴. That's the point — awareness changes behavior.
                            </div>
                        </div>

                        <!-- CERTIFICATION BADGE -->
                        <div style="text-align:center; padding:20px; background:linear-gradient(135deg, rgba(34,197,94,0.12), rgba(99,102,241,0.12)); border:3px solid #22c55e; border-radius:16px; margin-bottom:20px;">
                            <div style="font-size:3rem; margin-bottom:6px;">🏆</div>
                            <div style="font-size:0.78rem; font-weight:700; color:#22c55e; text-transform:uppercase; letter-spacing:2px;">CERTIFIED</div>
                            <div style="font-size:1.5rem; font-weight:900; margin:6px 0;">Green AI Detective</div>
                            <div style="font-size:0.95rem; opacity:0.7;">8-Step Investigation Complete</div>
                            <div style="margin-top:14px; padding:12px 16px; background:rgba(34,197,94,0.1); border-radius:10px; font-size:0.92rem; text-align:left; max-width:500px; margin-left:auto; margin-right:auto;">
                                <strong>Investigation complete.</strong> You now have the tools to evaluate AI's environmental impact and make informed decisions about when and how to use it. Every prompt has a cost — and now you know how to weigh it.
                            </div>
                            <div style="margin-top:12px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; max-width:400px; margin-left:auto; margin-right:auto;">
                                <div style="padding:6px; background:white; border-radius:6px; font-size:0.78rem;">
                                    <div style="font-weight:700; color:#6366f1;">Phase 1</div>
                                    <div style="opacity:0.6;">Personal Impact ✓</div>
                                </div>
                                <div style="padding:6px; background:white; border-radius:6px; font-size:0.78rem;">
                                    <div style="font-weight:700; color:#ef4444;">Phase 2</div>
                                    <div style="opacity:0.6;">Global Scale ✓</div>
                                </div>
                                <div style="padding:6px; background:white; border-radius:6px; font-size:0.78rem;">
                                    <div style="font-weight:700; color:#22c55e;">Audit</div>
                                    <div style="opacity:0.6;">Your Verdict ✓</div>
                                </div>
                            </div>
                        </div>

                        <!-- SHAREABLE TAKEAWAYS -->
                        <div style="background:var(--background-fill-secondary); border:2px solid var(--border-color-primary); border-radius:12px; padding:18px; margin-bottom:18px;">
                            <div style="font-weight:800; font-size:1.05rem; margin-bottom:10px;">🗣️ YOUR TOP 5 SHAREABLE FACTS</div>
                            <div style="font-size:0.88rem; opacity:0.7; margin-bottom:10px;">Pick your favorite. Tell someone today.</div>
                            <div style="display:grid; gap:6px;">
                                <div style="padding:10px 14px; background:white; border-radius:6px; font-size:0.9rem; border-left:3px solid #ef4444;">
                                    📱 "Every 25 AI prompts evaporate a bottle of water — forever."
                                </div>
                                <div style="padding:10px 14px; background:white; border-radius:6px; font-size:0.9rem; border-left:3px solid #f59e0b;">
                                    ⚡ "ChatGPT users burn through GPT-3's entire training energy in 11 days."
                                </div>
                                <div style="padding:10px 14px; background:white; border-radius:6px; font-size:0.9rem; border-left:3px solid #3b82f6;">
                                    🌍 "If data centers were a country, they'd be the 5th largest electricity consumer on Earth."
                                </div>
                                <div style="padding:10px 14px; background:white; border-radius:6px; font-size:0.9rem; border-left:3px solid #8b5cf6;">
                                    🇮🇪 "Dublin banned new data centers because they were using 18% of Ireland's electricity."
                                </div>
                                <div style="padding:10px 14px; background:white; border-radius:6px; font-size:0.9rem; border-left:3px solid #22c55e;">
                                    ⛏️ "Making a 4 lb server component requires mining 1,763 lbs of raw earth."
                                </div>
                            </div>
                        </div>

                        <div style="padding:14px; background:linear-gradient(135deg, rgba(34,197,94,0.1), rgba(99,102,241,0.1)); border:2px solid #22c55e; border-radius:10px; text-align:center;">
                            <div style="font-size:1.15rem; font-weight:800; color:var(--color-accent);">🎯 FINAL QUESTION BELOW</div>
                            <div style="font-size:0.95rem; margin-top:4px;">The hardest question in the investigation. No obvious answer this time.</div>
                        </div>
                    </div>
                </div>
            </div>
        """,
    },
]

# ============================================================================
# 5. QUIZ CONFIG — 8 QUESTIONS ALIGNED TO 8-STEP CURRICULUM
# ============================================================================

QUIZ_CONFIG = {
    0: {
        "t": "t1",
        "q": "🚀 **First Score Opportunity:** One AI image costs half a phone charge. 25 text prompts evaporate a water bottle. Most people have no idea. **Why does this invisibility matter?**",
        "o": [
            "A) It doesn't — the energy per prompt is tiny, so even billions of users create negligible total impact compared to transportation or manufacturing.",
            "B) Invisible costs mean billions of users waste energy daily without feedback, and no one pushes companies to change.",
            "C) It's only a problem for the environment, not for people — water evaporation is part of the natural cycle and doesn't reduce anyone's supply.",
        ],
        "a": "B) Invisible costs mean billions of users waste energy daily without feedback, and no one pushes companies to change.",
        "success": "<strong>Score Unlocked!</strong> The core problem: invisibility enables waste at scale. Now let's make it visible.",
    },
    1: {
        "t": "t2",
        "q": "Your friend says: *\"My individual AI use is so tiny it doesn't matter.\"* You just calculated 30,000 phone charges for one class per year. **What's the strongest counter?**",
        "o": [
            "A) Your friend has a point — the real problem is corporate data centers, not individual users. Even if everyone cut their usage in half, companies would still build the same infrastructure.",
            "B) Individual prompts are tiny, but 200M users × 50 prompts/week creates massive collective demand. Companies build infrastructure to match OUR usage.",
            "C) The responsible move is to stop using AI entirely until companies prove they run on 100% renewables — partial measures just slow the transition.",
        ],
        "a": "B) Individual prompts are tiny, but 200M users × 50 prompts/week creates massive collective demand. Companies build infrastructure to match OUR usage.",
        "success": "Ghost detected. 🗣️ <strong>Dinner table challenge:</strong> Tell someone tonight: your weekly AI use = ~25 phone charges.",
    },
    2: {
        "t": "t3",
        "q": "Your school is replacing Google Search with AI-powered search for all students. A teacher argues: *\"The internet already uses electricity — AI search won't make a difference.\"* **What's the flaw?**",
        "o": [
            "A) The teacher is right — both Google and ChatGPT run on the same servers and data centers, so switching from one to the other doesn't meaningfully change total energy consumption.",
            "B) AI queries use ~10× more energy than traditional search. Switching 500 students to AI would multiply the school's search energy tenfold.",
            "C) AI search is actually more efficient because it gives one direct answer instead of ten blue links — users spend less time browsing, which reduces total screen-on energy use.",
        ],
        "a": "B) AI queries use ~10× more energy than traditional search. Switching 500 students to AI would multiply the school's search energy tenfold.",
        "success": "Network traced. AI traffic is an order of magnitude hungrier than traditional browsing. 🗣️ <strong>Share:</strong> 70% of US internet traffic passes through one county in Virginia.",
    },
    3: {
        "t": "t4",
        "q": "Training GPT-3 consumed 1,287 MWh. Inference matched that in ~11 days. A classmate says: *\"Inference is more efficient per query, so it's not a big deal.\"* **Why is this misleading?**",
        "o": [
            "A) Training is actually the bigger long-term cost — each new model version requires retraining from scratch, which compounds over time as models get larger and more frequent.",
            "B) Per-query efficiency is irrelevant at 200M queries/day. Low cost × massive volume = total energy that dwarfs training in days, and never stops growing.",
            "C) Inference is essentially free since the model already exists — the electricity costs are negligible compared to the original training investment.",
        ],
        "a": "B) Per-query efficiency is irrelevant at 200M queries/day. Low cost × massive volume = total energy that dwarfs training in days, and never stops growing.",
        "success": "GPU scanned. 🗣️ <strong>Pop quiz for a friend:</strong> Training GPT-3 took months. How long for users to burn the same energy? 11 days.",
    },
    4: {
        "t": "t5",
        "q": "In Mesa, Arizona, families shortened showers during a 1,200-year drought while Microsoft evaporated 56M gallons/year nearby. A tech exec says: *\"We bring jobs and growth.\"* **What's the strongest response?**",
        "o": [
            "A) The jobs argument is valid — data centers create high-paying technical jobs and attract other businesses, which strengthens the local economy enough to fund water infrastructure improvements.",
            "B) Economic benefits don't justify taking essential resources without consent. The people losing water didn't choose to trade it — and you can't drink a paycheck during a drought.",
            "C) Evaporated water re-enters the water cycle as rain elsewhere, so the total global water supply is unchanged — the real issue is energy, not water.",
        ],
        "a": "B) Economic benefits don't justify taking essential resources without consent. The people losing water didn't choose to trade it — and you can't drink a paycheck during a drought.",
        "success": "Water crisis confirmed. 🗣️ <strong>Share this:</strong> In Mesa, Arizona, families shortened showers during a 1,200-year drought while Microsoft evaporated 56 million gallons/year nearby.",
    },
    5: {
        "t": "t6",
        "q": "A friend says: *\"Companies should just use renewables — it's not my problem.\"* You've been sorting AI uses from wasteful to worthwhile. **Why is your friend only half right?**",
        "o": [
            "A) Your friend is correct — the responsibility lies entirely with corporations. Consumers switching to renewable-powered services like Google (which claims carbon neutrality) eliminates the problem without requiring behavior change.",
            "B) Companies should use renewables, yes. But demand drives supply — unnecessary prompts mean MORE data centers regardless of energy source. Both efficiency and clean energy are needed.",
            "C) Renewable energy can't actually power data centers at the scale needed — solar and wind are too intermittent, so fossil fuels will remain dominant for AI infrastructure through at least 2040.",
        ],
        "a": "B) Companies should use renewables, yes. But demand drives supply — unnecessary prompts mean MORE data centers regardless of energy source. Both efficiency and clean energy are needed.",
        "success": "Paradox resolved. 🧠 <strong>Your new superpower:</strong> Before any prompt, ask: <em>Do I need AI? Is the benefit real? Am I being efficient?</em>",
    },
    6: {
        "t": "t7",
        "q": "Dublin banned new data centers in 2022 because they threatened 18% of Ireland's electricity. A tech lobbyist argues: *\"Data centers create jobs and tax revenue — banning them hurts the economy more than the grid.\"* **What's the strongest counter?**",
        "o": [
            "A) The lobbyist is right — Ireland's tech sector accounts for 30% of corporate tax revenue, and data center jobs pay 2-3× the national average. Economic growth should take priority over grid concerns.",
            "B) Jobs and tax revenue matter, but not if the lights go out. EirGrid warned of blackouts — a grid failure would damage the economy far more than pausing data center growth.",
            "C) Data centers should be banned permanently, not just paused — no amount of economic benefit justifies the environmental damage they cause, and the jobs can be replaced by green energy projects.",
        ],
        "a": "B) Jobs and tax revenue matter, but not if the lights go out. EirGrid warned of blackouts — a grid failure would damage the economy far more than pausing data center growth.",
        "success": "Scale mapped. 🗣️ <strong>Share this:</strong> Dublin literally told Big Tech 'You're taking too much. Stop.'",
    },
    7: {
        "t": "t11",
        "q": "🎯 **Final Verdict:** Your school wants to deploy AI tutoring for struggling students. Early tests show it genuinely helps — but running it for 500 students would use as much energy as powering 50 homes for a year. **What do you recommend?**",
        "o": [
            "A) Deploy it fully — 500 students benefiting from better education outweighs the energy cost of 50 homes. Education is a fundamental right, and effective AI tutoring is exactly the use case that justifies its environmental footprint.",
            "B) Deploy with conditions — start with 50 students who need it most, measure real impact vs. energy cost, and expand only if the learning gains are proven significant enough to justify the resources.",
            "C) Reject it — 50 homes' worth of energy for a tutoring tool is disproportionate when human tutors could deliver the same or better results while creating local jobs and producing zero environmental cost.",
        ],
        "a": "B) Deploy with conditions — start with 50 students who need it most, measure real impact vs. energy cost, and expand only if the learning gains are proven significant enough to justify the resources.",
        "success": "🏆 <strong>Investigation Complete!</strong> You didn't pick the easy answer. That's exactly the thinking the world needs — not 'ban it' or 'allow everything,' but <em>'prove it's worth it, then scale responsibly.'</em>",
    },
}


# ============================================================================
# 7. LEADERBOARD & API LOGIC (Preserved from original)
# ============================================================================

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


# ============================================================================
# 9. SUCCESS MESSAGE RENDERER
# ============================================================================

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
        summary_line = "You just earned your first Moral Compass Score — you're now part of the global rankings."
        cta_line = "Keep investigating to climb the leaderboard."
    elif style_key == "major":
        header_emoji = "🔥"
        header_title = "Major Moral Compass Boost!"
        summary_line = "Your analysis made a big impact — you just moved ahead of other detectives."
        cta_line = "Continue your investigation to keep the momentum."
    elif style_key == "climb":
        header_emoji = "🚀"
        header_title = "You're Climbing the Leaderboard"
        summary_line = "Nice work — you edged out other participants."
        cta_line = "Click NEXT to continue your investigation."
    elif style_key == "tight":
        header_emoji = "📊"
        header_title = "The Leaderboard Is Shifting"
        summary_line = "Other teams are moving too. A few more strong answers will set you apart."
        cta_line = "Take on the next step to strengthen your position."
    else:
        header_emoji = "✅"
        header_title = "Progress Logged"
        summary_line = "Your sustainability knowledge increased your Moral Compass Score."
        cta_line = "Try the next step to keep climbing."

    if style_key == "first":
        score_line = f"🧭 Score: <strong>{new_score:.3f}</strong>"
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
                rank_line = f"📈 Rank: #{old_rank} → <strong>#{new_rank}</strong> (+{rank_diff} places)"
            else:
                rank_line = f"🔻 Rank: #{old_rank} → <strong>#{new_rank}</strong> ({rank_diff} places)"
        else:
            rank_line = f"📊 Rank: <strong>#{new_rank}</strong>"

    return f"""
    <div class="{card_class}">
        <div class="success-header">
            <div>
                <div class="success-title">{header_emoji} {header_title}</div>
                <div class="success-summary">{summary_line}</div>
            </div>
            <div class="success-delta">+{diff_score:.3f}</div>
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


# ============================================================================
# 10. DASHBOARD & LEADERBOARD RENDERERS
# ============================================================================

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

    # Phase indicator
    if module_id <= 5:
        phase_label = "PHASE 1: Personal Impact"
        phase_color = "#6366f1"
    else:
        phase_label = "PHASE 2: Global Scale"
        phase_color = "#ef4444"

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
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="progress-label">Investigation Progress: {progress_pct}%</div>
                    <div style="font-size:0.75rem; font-weight:700; color:{phase_color}; background:rgba(0,0,0,0.05); padding:2px 8px; border-radius:10px;">{phase_label}</div>
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
                                <tr><th>Rank</th><th>Detective</th><th style='text-align:right;'>Score 🧭</th></tr>
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
# 11. CSS
# ============================================================================

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

/* Interactive blocks */
.interactive-block { font-size: 1.06rem; }
.interactive-block .hint-box { font-size: 1.02rem; }
.interactive-text { font-size: 1.06rem; }

/* Radio sizes */
.scenario-radio-large label { font-size: 1.06rem; }
.quiz-radio-large label { font-size: 1.06rem; }

/* Small utility */
.divider-vertical { width: 1px; height: 48px; background: var(--border-color-primary); opacity: 0.6; }

/* Progress tracker */
.tracker-container {
  display: flex;
  justify-content: space-around;
  align-items: center;
  margin-bottom: 25px;
  background: var(--background-fill-secondary);
  padding: 10px 0;
  border-radius: 8px;
  border: 1px solid var(--border-color-primary);
  flex-wrap: wrap;
  gap: 4px;
}
.tracker-step {
  text-align: center;
  font-weight: 700;
  font-size: 0.78rem;
  padding: 5px 8px;
  border-radius: 4px;
  color: var(--body-text-color-subdued);
  transition: all 0.3s ease;
}
.tracker-step.completed {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}
.tracker-step.active {
  color: var(--color-accent);
  background: var(--color-accent-soft);
  box-shadow: 0 0 5px rgba(99, 102, 241, 0.3);
}

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

/* Points chip + quiz CTA */
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
.quiz-submit { min-width: 200px; }

/* Ghost journey animation */
@keyframes ghostFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.ghost-step { transition: all 0.3s ease; }

/* Usage slider styling */
.usage-slider { margin-top: -8px !important; }
.usage-slider .wrap { padding: 0 4px !important; }

/* Guess buttons hover */
.guess-btn:hover { background: rgba(99,102,241,0.12) !important; border-color: var(--color-accent) !important; }
"""


# ============================================================================
# 12. MORAL COMPASS SLIDER HELPER
# ============================================================================

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
        <p style="margin-bottom:4px; font-size:1.05rem;"><strong>Your accuracy:</strong> {acc_val:.3f}</p>
        <p style="margin-bottom:4px; font-size:1.05rem;"><strong>Simulated Ethical Progress %:</strong> {prog_val:.0f}%</p>
        <p style="margin-bottom:0; font-size:1.08rem;"><strong>Simulated Moral Compass Score:</strong> 🧭 {score:.3f}</p>
    </div>
    """


# ============================================================================
# 13. APP FACTORY
# ============================================================================

def create_green_detective_en_sustainability_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)
        module0_done = gr.State(value=False)
        accuracy_state = gr.State(value=0.0)
        task_list_state = gr.State(value=[])

        # Top anchor + loading overlay
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
            # Top dashboard
            out_top = gr.HTML()

            with gr.Accordion("How is the Moral Compass Score calculated?", open=False):
                gr.HTML("""
                    <div style="padding:12px; font-size:0.92rem; line-height:1.6;">
                        <div style="font-weight:700; margin-bottom:8px;">Formula:</div>
                        <div style="background:var(--background-fill-secondary); padding:12px 16px; border-radius:8px; font-family:monospace; font-size:1rem; margin-bottom:10px; border:1px solid var(--border-color-primary);">
                            Moral Compass Score = Accuracy × (Steps Completed ÷ Total Steps)
                        </div>
                        <ul style="margin:0; padding-left:20px;">
                            <li><strong>Accuracy</strong> — Your model's accuracy score from Activity 4 (0 to 1).</li>
                            <li><strong>Steps Completed</strong> — How many investigation steps you've answered correctly so far.</li>
                            <li><strong>Total Steps</strong> — The total number of quiz questions across the investigation (8).</li>
                        </ul>
                        <div style="margin-top:10px; padding:8px 12px; background:rgba(99,102,241,0.08); border-radius:6px; font-size:0.88rem;">
                            Your score increases as you progress through the investigation. A perfect score means high model accuracy <em>and</em> completing all ethical reasoning steps.
                        </div>
                    </div>
                """)

            # Module containers
            module_ui_elements = {}
            quiz_wiring_queue = []

            for i, mod in enumerate(MODULES):
                with gr.Column(
                    elem_id=f"module-{i}",
                    elem_classes=["module-container"],
                    visible=(i == 0),
                ) as mod_col:
                    gr.HTML(mod["html"])

                    # --- MODULE 1: Interactive Personal Usage Slider ---
                    if i == 1:
                        usage_slider = gr.Slider(
                            minimum=0, maximum=200, value=50, step=5,
                            label="🎚️ How many AI prompts do YOU send per week? (ChatGPT, image gen, Snapchat AI, voice assistants, autocomplete…)",
                            elem_classes=["usage-slider"],
                        )
                        usage_output = gr.HTML("")

                        def calc_footprint(n_prompts):
                            charges_week = round(n_prompts * 0.5, 1)
                            charges_year = round(charges_week * 40, 0)
                            water_bottles = round(n_prompts / 22.5, 1)
                            water_year = round(water_bottles * 40, 0)
                            co2_year_kg = round(n_prompts * 0.003 * 52, 1)  # ~3g CO2 per prompt

                            bar_pct_energy = min(100, int(charges_week / 50 * 100))
                            bar_pct_water = min(100, int(water_bottles / 10 * 100))

                            return f"""
                            <div style="background:#1e293b; color:white; padding:16px 18px; border-radius:12px; margin-top:4px;">
                                <div style="font-size:0.78rem; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:10px; text-align:center;">
                                    📊 YOUR WEEKLY AI FOOTPRINT — {int(n_prompts)} prompts/week
                                </div>
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px;">
                                    <div style="text-align:center; padding:12px; background:rgba(248,113,113,0.12); border-radius:8px;">
                                        <div style="font-size:0.75rem; color:#94a3b8;">⚡ Energy / week</div>
                                        <div style="font-size:1.6rem; font-weight:900; color:#f87171;">{charges_week} charges</div>
                                        <div style="height:6px; background:rgba(255,255,255,0.1); border-radius:3px; margin-top:6px; overflow:hidden;">
                                            <div style="height:100%; width:{bar_pct_energy}%; background:#f87171; border-radius:3px;"></div>
                                        </div>
                                    </div>
                                    <div style="text-align:center; padding:12px; background:rgba(96,165,250,0.12); border-radius:8px;">
                                        <div style="font-size:0.75rem; color:#94a3b8;">💧 Water / week</div>
                                        <div style="font-size:1.6rem; font-weight:900; color:#60a5fa;">{water_bottles} bottles</div>
                                        <div style="height:6px; background:rgba(255,255,255,0.1); border-radius:3px; margin-top:6px; overflow:hidden;">
                                            <div style="height:100%; width:{bar_pct_water}%; background:#60a5fa; border-radius:3px;"></div>
                                        </div>
                                    </div>
                                </div>
                                <div style="text-align:center; padding:10px; background:rgba(250,204,21,0.1); border-radius:8px;">
                                    <span style="font-size:0.85rem; color:#fbbf24; font-weight:700;">Over one school year (40 weeks):</span>
                                    <span style="color:white; font-weight:800;"> {int(charges_year)} phone charges</span>
                                    <span style="color:#94a3b8;"> · </span>
                                    <span style="color:white; font-weight:800;">{int(water_year)} water bottles evaporated</span>
                                    <span style="color:#94a3b8;"> · </span>
                                    <span style="color:white; font-weight:800;">{co2_year_kg} kg CO₂</span>
                                </div>
                            </div>
                            <div style="padding:10px; background:#fef3c7; border-left:3px solid #f59e0b; border-radius:6px; font-size:0.9rem; margin-top:10px;">
                                <strong>🔑 Key Insight:</strong> Every time you hit "send," somewhere a power plant burns fuel and a cooling tower evaporates water. There is no such thing as a free prompt.
                            </div>
                            """

                        usage_slider.change(
                            fn=calc_footprint,
                            inputs=[usage_slider],
                            outputs=[usage_output],
                        )
                        # Show default value on load
                        demo.load(
                            fn=lambda: calc_footprint(50),
                            outputs=[usage_output],
                        )

                    # --- MODULE 7: Personal Audit Textboxes ---
                    if i == 7:
                        gr.HTML("<div style='margin-top:10px; font-weight:700; font-size:1rem;'>Type your personal AI audit below:</div>")
                        audit_tool_1 = gr.Textbox(
                            label="1. AI tool or habit",
                            placeholder="e.g. ChatGPT for homework help — Worth it / Debatable / Could skip",
                            lines=2,
                        )
                        audit_tool_2 = gr.Textbox(
                            label="2. AI tool or habit",
                            placeholder="e.g. AI image generation for fun — Worth it / Debatable / Could skip",
                            lines=2,
                        )
                        audit_tool_3 = gr.Textbox(
                            label="3. AI tool or habit",
                            placeholder="e.g. Voice assistant for reminders — Worth it / Debatable / Could skip",
                            lines=2,
                        )

                    # Quiz content
                    if i in QUIZ_CONFIG:
                        q_data = QUIZ_CONFIG[i]

                        gr.HTML(
                            "<div class='quiz-cta'>"
                            "<span class='points-chip'>🧭 Moral Compass points available</span>"
                            "<span>Answer to boost your score</span>"
                            "</div>"
                        )

                        gr.Markdown(f"### 🧠 {q_data['q']}")
                        radio = gr.Radio(
                            choices=q_data["o"],
                            label="Select Answer:",
                            elem_classes=["quiz-radio-large"],
                        )
                        feedback = gr.HTML("")
                        quiz_wiring_queue.append((i, radio, feedback))

                    # Navigation buttons
                    with gr.Row():
                        btn_prev = gr.Button("⬅️ Previous", visible=(i > 0))
                        next_label = (
                            "Next ▶️"
                            if i < len(MODULES) - 1
                            else "🎉 Investigation Complete!"
                        )
                        btn_next = gr.Button(next_label, variant="primary")

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            # Leaderboard at bottom
            leaderboard_html = gr.HTML()

            # --- WIRING: QUIZ LOGIC ---
            for mod_id, radio_comp, feedback_comp in quiz_wiring_queue:

                def quiz_logic_wrapper(
                    user, tok, team, acc_val, task_list, ans, mid=mod_id
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
                            "❌ Not quite. Re-read the evidence above and think about what the data specifically shows.</div>",
                            task_list,
                        )

                radio_comp.change(
                    fn=quiz_logic_wrapper,
                    inputs=[username_state, token_state, team_state, accuracy_state, task_list_state, radio_comp],
                    outputs=[out_top, leaderboard_html, feedback_comp, task_list_state],
                )

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
                return (
                    uname, tok, team, False,
                    render_top_dashboard(data, 0),
                    render_leaderboard_card(data, uname, team),
                    best_acc, fetched_tasks,
                    gr.update(visible=False),
                    gr.update(visible=True),
                )
            return (
                None, None, None, False,
                "<div class='hint-box'>⚠️ Auth Failed. Please launch from the course link.</div>",
                "", 0.0, [],
                gr.update(visible=False),
                gr.update(visible=True),
            )

        demo.load(
            handle_load, None,
            [
                username_state, token_state, team_state, module0_done,
                out_top, leaderboard_html, accuracy_state, task_list_state,
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
                        yield gr.update(visible=False), gr.update(visible=False)
                        yield gr.update(visible=True), gr.update(visible=False)
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
                    def wrapper_next(user, tok, team, tasks):
                        data, _ = ensure_table_and_get_data(user, tok, team, tasks)
                        dash_html = render_top_dashboard(data, next_idx)
                        return dash_html
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


# ============================================================================
# LAUNCH
# ============================================================================

def launch_green_detective_en_sustainability_app(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 8080,
    theme_primary_hue: str = "indigo",
    **kwargs
) -> None:
    app = create_green_detective_en_sustainability_app(theme_primary_hue=theme_primary_hue)
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        **kwargs
    )


if __name__ == "__main__":
    launch_green_detective_en_sustainability_app(share=False, debug=True, height=1000)

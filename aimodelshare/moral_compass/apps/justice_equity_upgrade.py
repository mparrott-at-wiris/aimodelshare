import os
import sys
import subprocess
import time
import datetime
from typing import Tuple, Optional, List

# --- 1. CONFIGURATION ---
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"
TOTAL_COURSE_TASKS = 20 # Sync with App 2
LOCAL_TEST_SESSION_ID = None

# ==============================================================================
# --- BRANDING CONFIGURATION ---
SHOW_BRANDED_LOGOS = False 

# PASTE YOUR BASE64 STRINGS HERE (do not include "data:image/png;base64," prefix)
PARTNER_LOGO_1_BASE64 = ""
PARTNER_LOGO_2_BASE64 = ""
PARTNER_LOGO_3_BASE64 = ""
PARTNER_LOGO_4_BASE64 = ""
PARTNER_LOGO_5_BASE64 = ""
PARTNER_LOGO_6_BASE64 = ""

# Fallback/Default Logos
FAKE_LOGO_1 = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/IBM_logo.svg/200px-IBM_logo.svg.png" 
FAKE_LOGO_2 = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/University_of_California%2C_Berkeley_logo.svg/200px-University_of_California%2C_Berkeley_logo.svg.png" 
FAKE_LOGO_3 = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Apple_logo_black.svg/150px-Apple_logo_black.svg.png" 
# ==============================================================================

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

# --- 4. CSS (COMBINED STYLE FROM APP 2 + PRINT STYLES) ---
css = """
/* --- STYLES IMPORTED FROM APP 2 --- */
/* Layout + containers */
.summary-box { background: var(--block-background-fill); padding: 20px; border-radius: 12px; border: 1px solid var(--border-color-primary); margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.summary-box-inner { display: flex; align-items: center; justify-content: space-between; gap: 30px; }
.summary-metrics { display: flex; gap: 30px; align-items: center; }
.summary-progress { width: 560px; max-width: 100%; }

/* Scenario cards */
.scenario-box { padding: 24px; border-radius: 14px; background: var(--block-background-fill); border: 1px solid var(--border-color-primary); margin-bottom: 22px; box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
.slide-title { margin-top: 0; font-size: 1.9rem; font-weight: 800; }
.slide-body { font-size: 1.12rem; line-height: 1.65; }

/* Hint boxes */
.hint-box { padding: 12px; border-radius: 10px; background: var(--background-fill-secondary); border: 1px solid var(--border-color-primary); margin-top: 10px; font-size: 0.98rem; }

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
.lb-tab-label { display: inline-block; padding: 8px 16px; margin-right: 8px; border-radius: 20px; cursor: pointer; border: 1px solid var(--border-color-primary); font-weight: 700; font-size: 0.94rem; }
#lb-tab-team:checked + label, #lb-tab-user:checked + label { background: var(--color-accent); color: white; border-color: var(--color-accent); box-shadow: 0 3px 8px rgba(99,102,241,0.25); }
.lb-panel { display: none; margin-top: 10px; }
#lb-tab-team:checked ~ .lb-tab-panels .panel-team { display: block; }
#lb-tab-user:checked ~ .lb-tab-panels .panel-user { display: block; }
.table-container { height: 320px; overflow-y: auto; border: 1px solid var(--border-color-primary); border-radius: 10px; }
.leaderboard-table { width: 100%; border-collapse: collapse; }
.leaderboard-table th { position: sticky; top: 0; background: var(--background-fill-secondary); padding: 10px; text-align: left; border-bottom: 2px solid var(--border-color-primary); font-weight: 800; }
.leaderboard-table td { padding: 10px; border-bottom: 1px solid var(--border-color-primary); }
.row-highlight-me, .row-highlight-team { background: rgba(96,165,250,0.18); font-weight: 700; }

/* Containers */
.ai-risk-container { margin-top: 16px; padding: 16px; background: var(--body-background-fill); border-radius: 10px; border: 1px solid var(--border-color-primary); }

/* Small utility */
.divider-vertical { width: 1px; height: 48px; background: var(--border-color-primary); opacity: 0.6; }

/* --- APP 3 SPECIFIC STYLES (Printing/Sharing) --- */
.share-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 20px; border-radius: 50px; font-weight: 700; text-decoration: none; color: white; transition: transform 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.1); cursor: pointer; border: none; }
.share-btn:hover { transform: translateY(-2px); opacity: 0.95; }
.share-wa { background-color: #25D366; }
.share-tw { background-color: #1DA1F2; }
.share-em { background-color: #64748b; }
.share-ig { background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); }
.share-print { background-color: #1e3a8a; }

/* STRICT PRINT STYLES - Hides App UI, Shows Certificate */
@media print {
    body, body * { visibility: hidden !important; height: 0; overflow: hidden; }
    #cert-printable, #cert-printable * { visibility: visible !important; height: auto; overflow: visible; }
    #cert-printable { position: absolute !important; left: 0 !important; top: 0 !important; width: 100% !important; margin: 0 !important; padding: 0 !important; z-index: 999999; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    button, .share-btn { display: none !important; }
}
"""

# --- 5. RENDERERS (PORTED FROM APP 2) ---

def render_top_dashboard(data):
    display_score = 0.0
    count_completed = 0
    rank_display = "–"
    team_rank_display = "–"
    if data:
        display_score = float(data.get("score", 0.0))
        rank_display = f"#{data.get('rank', '–')}"
        team_rank_display = f"#{data.get('team_rank', '–')}"
        count_completed = len(data.get("completed_task_ids", []) or [])
    
    # Force 100% since this is the certificate app
    progress_pct = 100 

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
                <div class="progress-label" style="font-weight:700; color:var(--color-accent);">Certification Progress: {progress_pct}%</div>
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

# --- 6. HTML CERTIFICATE GENERATOR ---
# --- 4. HTML CERTIFICATE GENERATOR (TECH STYLE) ---
def generate_html_certificate(name, score, team_name):
    date_str = datetime.date.today().strftime("%B %d, %Y")
    cert_id = int(time.time())
    
    # BRAND COLORS
    c_primary = "#5a46cc"    # Deep Indigo
    c_sec_light = "#d0d5e9"  # Soft Lavender
    c_slate = "#8485a1"      # Tech Slate
    
    # --- LOGO LOGIC (Preserves layout unless branding is enabled) ---
    if SHOW_BRANDED_LOGOS:
        logo_section = f"""
        <div style="display: flex; justify-content: center; align-items: center; gap: 20px; flex-wrap: wrap; margin-top: 10px;">
             <img src="data:image/png;base64,{PARTNER_LOGO_1_BASE64}" style="height: 35px; max-width: 100px; object-fit: contain;">
             <img src="data:image/png;base64,{PARTNER_LOGO_2_BASE64}" style="height: 35px; max-width: 100px; object-fit: contain;">
             <img src="data:image/png;base64,{PARTNER_LOGO_3_BASE64}" style="height: 35px; max-width: 100px; object-fit: contain;">
             <img src="data:image/png;base64,{PARTNER_LOGO_4_BASE64}" style="height: 35px; max-width: 100px; object-fit: contain;">
             <img src="data:image/png;base64,{PARTNER_LOGO_5_BASE64}" style="height: 35px; max-width: 100px; object-fit: contain;">
             <img src="data:image/png;base64,{PARTNER_LOGO_6_BASE64}" style="height: 35px; max-width: 100px; object-fit: contain;">
        </div>
        """
    else:
        # Exact default layout requested
        logo_section = f"""
        <div style="display: flex; gap: 25px; opacity: 1.0; align-items: center;">
             <img src="{FAKE_LOGO_1}" style="height: 30px; object-fit: contain;">
             <img src="{FAKE_LOGO_2}" style="height: 35px; object-fit: contain;">
             <img src="{FAKE_LOGO_3}" style="height: 25px; object-fit: contain;">
        </div>
        """

    # --- HTML STRUCTURE ---
    # Used ID cert-printable for JS printing targeting
    html = f"""
    <div id="cert-printable" style="
        position: relative; width: 100%; max-width: 900px; margin: 0 auto;
        padding: 0;
        background: #fff;
        /* Double Border: Thick Brand Indigo + Thin Inner Line */
        border: 10px solid {c_primary}; 
        outline: 2px solid {c_primary}; outline-offset: -16px;
        font-family: 'IBM Plex Sans', 'Helvetica', sans-serif; 
        color: #1e293b;
        box-shadow: 0 15px 40px rgba(0,0,0,0.15); 
        text-align: center;
        box-sizing: border-box;
    ">
        <div style="padding: 60px 50px;">
            
            <div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid {c_sec_light}; padding-bottom: 20px; margin-bottom: 40px;">
                <div style="text-align: left;">
                    <div style="
                        font-family: 'Source Serif Pro', 'Georgia', serif; 
                        font-weight: 700; 
                        color: {c_primary}; 
                        font-size: 1.4rem;
                        letter-spacing: -0.5px;
                    ">
                        Ethics at Play - Digital Education Program
                    </div>
                    <div style="font-size: 0.75rem; color: {c_slate}; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 5px;">
                        Ethical AI - Justice and Equity Accreditation
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-family: 'Courier New', monospace; font-size: 0.85rem; color: {c_slate};">
                        REF_ID: <span style="color: #000;">{cert_id}</span>
                    </div>
                </div>
            </div>

            <div style="margin-bottom: 40px;">
                <h3 style="
                    font-size: 1rem; 
                    font-weight: 600; 
                    color: {c_slate}; 
                    text-transform: uppercase; 
                    letter-spacing: 3px;
                    margin: 0;
                ">Ethics at Play Certification</h3>
                
                <h3 style="
                    font-family: 'Source Serif Pro', 'Georgia', serif; 
                    font-size: 3.5rem; 
                    color: #1e293b; 
                    margin: 10px 0 0 0;
                    line-height: 1.1;
                ">
                    Ethical AI Innovation<br><span style="color: {c_primary};">Justice and Equity</span>
                </h3>
            </div>

            <div style="background: #f8fafc; padding: 30px; border-radius: 8px; border-left: 6px solid {c_primary}; margin-bottom: 40px; text-align: left;">
                <p style="font-size: 0.9rem; color: {c_slate}; text-transform: uppercase; margin: 0 0 5px 0;">Awarded To AI Fairness Engineer</p>
                <h2 style="
                    font-family: 'Source Serif Pro', 'Georgia', serif; 
                    font-size: 3rem; 
                    margin: 0; 
                    color: #0f172a; 
                    font-weight: 700;
                ">{name}</h2>
                <p style="font-size: 1.1rem; color: #475569; margin: 5px 0 0 0;">
                    Member of <strong>{team_name}</strong>
                </p>
            </div>

            <p style="font-size: 1.1rem; line-height: 1.6; color: #334155; margin-bottom: 40px; text-align: left;">
                For demonstrating the ability to <strong>make AI more just and fair</strong> responsibly. The recipient has successfully successfully audited AI pipelines for representation bias, implemented causal sanitization, and localized AI systems for deployment contexts.
            </p>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 50px;">
                <div style="border: 1px solid {c_sec_light}; border-radius: 6px; padding: 15px; text-align: left;">
                    <div style="font-size: 0.75rem; color: {c_slate}; text-transform: uppercase; font-weight: 700;">Moral Compass Score</div>
                    <div style="font-size: 2rem; font-weight: 700; color: {c_primary}; font-family: 'Courier New', monospace;">
                        {score:.3f}
                    </div>
                </div>
                <div style="border: 1px solid {c_sec_light}; border-radius: 6px; padding: 15px; text-align: left; background: #f0fdf4;">
                    <div style="font-size: 0.75rem; color: #166534; text-transform: uppercase; font-weight: 700;">Audit Status</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: #15803d; margin-top: 8px;">
                        ✅ VERIFIED FAIR
                    </div>
                </div>
            </div>

            <div style="border-top: 2px solid #1e293b; padding-top: 25px; display: flex; justify-content: space-between; align-items: flex-end;">
                <div style="text-align: left;">
                    <div style="font-family: 'Source Serif Pro', serif; font-size: 1.2rem; font-weight: 700; color: #000;">
                        Ethics at Play
                    </div>
                    <div style="font-size: 0.85rem; color: {c_slate}; margin-top: 5px;">
                        Authorized Curriculum • {date_str}
                    </div>
                </div>

                {logo_section}
                
            </div>

        </div>
    </div>
    """
    return html

# --- 7. MODULE DEFINITIONS ---
MODULES = [
    # --- MODULE 0: VICTORY DASHBOARD (UPDATED TO MATCH APP 2 STYLE) ---
    {
        "id": 0,
        "title": "Achievement Unlocked",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">
                    <div style="text-align:center; margin-bottom:20px;">
                        <div style="font-size:3rem;">🏆</div>
                        <h2 class="slide-title" style="margin-top:5px; color:#b45309;">Achievement Unlocked</h2>
                        <p style="font-size:1.1rem; max-width:800px; margin:0 auto; color:var(--body-text-color);">
                            You have successfully completed the Fairness Protocol.
                            <br>
                            Review your final performance metrics below before claiming your credential.
                        </p>
                    </div>

                    <div id="final-dashboard-inject"></div>
                    <div id="final-leaderboard-inject" style="margin-top:20px;"></div>

                    <p style="text-align:center; margin-top:25px; font-weight:600;">
                        Click <strong>Next ▶️</strong> to review your engineering log and generate your certificate.
                    </p>
                </div>
            </div>
        """
    },
    # --- MODULE 1: THE ENGINEERING LOG ---
    {
        "id": 1,
        "title": "Engineering Log",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">
                    <h2 class="slide-title" style="text-align:center;">📋 Your Engineering Resume</h2>
                    <p style="text-align:center; margin-bottom:20px;">
                        You are now qualified to handle high-risk AI systems. Here is what you proved:
                    </p>

                    <div style="display:grid; gap:15px;">
                        <div style="background:var(--background-fill-secondary); border-left:5px solid #3b82f6; padding:15px; border-radius:4px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <div style="font-weight:800; color:#1e40af; font-size:1.1rem;">👁️ BIAS DETECTION</div>
                            <div style="color:var(--body-text-color);">You identified hidden Representation Bias ("The Distorted Mirror") and diagnosed the Racial Error Gap.</div>
                        </div>

                        <div style="background:var(--background-fill-secondary); border-left:5px solid #8b5cf6; padding:15px; border-radius:4px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <div style="font-weight:800; color:#6d28d9; font-size:1.1rem;">✂️ DATA SANITIZATION</div>
                            <div style="color:var(--body-text-color);">You stripped Protected Classes and successfully hunted down sneaky Proxy Variables (Zip Codes).</div>
                        </div>

                        <div style="background:var(--background-fill-secondary); border-left:5px solid #10b981; padding:15px; border-radius:4px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                            <div style="font-weight:800; color:#065f46; font-size:1.1rem;">🌍 CONTEXTUAL ENGINEERING</div>
                            <div style="color:var(--body-text-color);">You rejected "Shortcut Data" and implemented Local Data to prevent Context Mismatch.</div>
                        </div>
                    </div>

                    <div style="text-align:center; margin-top:25px;">
                        <p style="font-size:1.0rem;">
                            Click <strong>Next ▶️</strong> to generate your official certificate.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    # --- MODULE 2: CERTIFICATE GENERATOR ---
    {
        "id": 2,
        "title": "Official Certification",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">
                    <h2 class="slide-title" style="text-align:center; color:#15803d;">🎓 Claim Your Credentials</h2>
                    <p style="text-align:center; margin-bottom:20px;">
                        Enter your name exactly as you want it to appear on your official <strong>Ethics at Play</strong> certificate.
                    </p>

                    <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:20px; border-radius:12px; text-align:center; margin-bottom:20px;">
                        <div style="font-weight:700; color:#166534; margin-bottom:10px;">AUTHORIZED FOR:</div>
                        <div style="font-size:1.5rem; font-weight:900; color:#15803d; margin-bottom:5px;">AI FAIRNESS ENGINEER</div>
                        <p style="font-size:0.9rem; color:#14532d; margin:0;">
                            This document proves you prioritize Justice over Convenience.
                        </p>
                    </div>
                </div>
            </div>
        """
    },
    # --- MODULE 3: THE FINAL TRANSITION ---
    {
        "id": 3,
        "title": "The Final Challenge",
        "html": """
            <div class="scenario-box">
                <div class="slide-body">
                    <div style="text-align:center;">
                        <div style="font-size:3rem;">🚀</div>
                        <h2 class="slide-title" style="margin-top:10px;">The Final Frontier</h2>
                    </div>

                    <p style="font-size:1.1rem; text-align:center; max-width:800px; margin:0 auto 25px auto;">
                        You have the ethics. You have the certificate.
                        <br>
                        Now, it is time to prove you have the <strong>Skill</strong>.
                    </p>

                    <div class="ai-risk-container" style="background:linear-gradient(to right, #eff6ff, var(--body-background-fill)); border:2px solid #3b82f6;">
                        <h3 style="margin-top:0; color:#1e40af;">🏆 The Accuracy Competition</h3>
                        <p style="font-size:1.05rem; line-height:1.5; color:var(--body-text-color);">
                            Your final mission is to compete against your classmates to build the <strong>most accurate model possible</strong>.
                            <br><br>
                            But remember: <strong>You must maintain your Moral Compass.</strong>
                            <br>
                            High accuracy achieved by cheating (using biased data) will result in disqualification.
                        </p>
                    </div>

                    <div style="text-align:center; margin-top:30px;">
                        <a href="#" target="_self" style="text-decoration:none;">
                            <div style="display:inline-block; padding:16px 32px; background:var(--color-accent); color:white; border-radius:50px; font-weight:800; font-size:1.2rem; box-shadow:0 4px 15px rgba(99, 102, 241, 0.4);">
                                ENTER THE ARENA ▶️
                            </div>
                        </a>
                        <p style="font-size:0.9rem; color:var(--body-text-color-subdued); margin-top:10px;">(Scroll down to the next activity to begin)</p>
                    </div>
                </div>
            </div>
        """
    }
]

# --- 8. LOGIC FUNCTIONS ---

def get_leaderboard_data(client, username, team_name):
    # Ported from App 2 logic
    try:
        resp = client.list_users(table_id=TABLE_ID, limit=500)
        users = resp.get("users", [])
        
        users_sorted = sorted(
            users, key=lambda x: float(x.get("moralCompassScore", 0) or 0), reverse=True
        )
        my_user = next((u for u in users_sorted if u.get("username") == username), None)
        score = float(my_user.get("moralCompassScore", 0) or 0) if my_user else 0.0
        rank = users_sorted.index(my_user) + 1 if my_user else 0
        completed_task_ids = my_user.get("completedTaskIds", []) if my_user else []
        
        team_map = {}
        for u in users:
            t = u.get("teamName")
            s = float(u.get("moralCompassScore", 0) or 0)
            if t:
                if t not in team_map: team_map[t] = {"sum": 0, "count": 0}
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
            "completed_task_ids": completed_task_ids,
            "all_users": users_sorted,
            "all_teams": teams_sorted
        }
    except:
        return None

def create_cert_handler(user_input_name, username_state, token, team_name):
    if not user_input_name:
        user_input_name = username_state

    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
    data = get_leaderboard_data(client, username_state, team_name)
    score = data.get("score", 0.0)

    # Generate HTML content (Using the Tech Style)
    cert_html = generate_html_certificate(user_input_name, score, team_name)

    share_text = f"I just certified as a Responsible AI Innovator! 🧭 #EthicsAtPlay #ResponsibleAI"
    wa_link = f"https://wa.me/?text={share_text}"
    tw_link = f"https://twitter.com/intent/tweet?text={share_text}"
    ig_link = "https://instagram.com"

    # --- JAVASCRIPT POPUP PRINTER ---
    js_print_logic = """
    var cert = document.getElementById('cert-printable');
    var w = window.open('', '_blank');
    w.document.write('<html><head><title>Certificate</title>');
    w.document.write('<style>');
    w.document.write('body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: sans-serif; background: #fff; }');
    w.document.write('@media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }');
    w.document.write('</style>');
    w.document.write('</head><body>');
    w.document.write(cert.outerHTML);
    w.document.write('</body></html>');
    w.document.close();
    setTimeout(function() { w.print(); w.close(); }, 500);
    """

    share_html = f"""
    <div style="margin-top:25px; text-align:center; padding:20px; background:linear-gradient(to bottom, #f8fafc, white); border-radius:12px; border:1px solid #e2e8f0;">
        <p style="font-weight:800; color:#475569; margin-bottom:15px; font-size:1.1rem;">
            📢 Save & Share Your Success
        </p>

        <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
            <button onclick="{js_print_logic}" class="share-btn share-print">🖨️ Print / Save as PDF</button>
            <a href="{wa_link}" target="_blank" class="share-btn share-wa">WhatsApp</a>
            <a href="{ig_link}" target="_blank" class="share-btn share-ig">Instagram</a>
            <a href="{tw_link}" target="_blank" class="share-btn share-tw">X / Twitter</a>
        </div>

        <p style="font-size:0.85rem; color:#94a3b8; margin-top:15px; font-style:italic;">
            📸 <strong>Pro Tip:</strong> Click 'Print' and choose 'Save as PDF' to keep your certificate forever.
            <br>For Instagram, take a screenshot of the certificate above!
        </p>
    </div>
    """
    
    return gr.update(value=cert_html, visible=True), gr.update(value=share_html, visible=True)

# --- 9. APP FACTORY ---
def create_justice_equity_upgrade_app(theme_primary_hue: str = "indigo"):
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # States
        username_state = gr.State(value=None)
        token_state = gr.State(value=None)
        team_state = gr.State(value=None)

        # --- LOADING ---
        with gr.Column(visible=True, elem_id="app-loader") as loader_col:
            gr.HTML("<div style='text-align:center; padding:100px;'><h2>🏆 Verifying Credentials...</h2></div>")

        # --- MAIN APP ---
        with gr.Column(visible=False) as main_app_col:

            # Module containers
            module_ui_elements = {}

            for i, mod in enumerate(MODULES):
                with gr.Column(visible=(i==0), elem_id=f"mod-{i}") as mod_col:
                    gr.HTML(mod["html"])

                    # Special Logic for Module 0 (Victory Dashboard)
                    if i == 0:
                        dash_output = gr.HTML()
                        lb_output = gr.HTML()

                    # Special Logic for Module 2 (Certificate Input)
                    if i == 2:
                        name_input = gr.Textbox(label="Full Name for Certificate", placeholder="e.g. Jane Doe")
                        gen_btn = gr.Button("🎓 Generate & Sign Certificate", variant="primary")

                        cert_display = gr.HTML(label="Official Certificate", visible=False)
                        share_row = gr.HTML(visible=False)

                        gen_btn.click(
                            create_cert_handler,
                            inputs=[name_input, username_state, token_state, team_state],
                            outputs=[cert_display, share_row]
                        )

                    # Nav
                    with gr.Row():
                        btn_prev = gr.Button("⬅️ Previous", visible=(i > 0))
                        next_txt = "Next ▶️" if i < len(MODULES) - 1 else "Finish"
                        btn_next = gr.Button(next_txt, visible=(i < len(MODULES) - 1))

                    module_ui_elements[i] = (mod_col, btn_prev, btn_next)

            # --- NAVIGATION LOGIC ---
            for i in range(len(MODULES)):
                curr_col, prev_btn, next_btn = module_ui_elements[i]

                if i > 0:
                    prev_col = module_ui_elements[i-1][0]
                    def nav_back():
                        return gr.update(visible=False), gr.update(visible=True)
                    prev_btn.click(nav_back, None, [curr_col, prev_col])

                if i < len(MODULES) - 1:
                    next_col = module_ui_elements[i+1][0]
                    def nav_fwd():
                        return gr.update(visible=False), gr.update(visible=True)
                    next_btn.click(nav_fwd, None, [curr_col, next_col])

        # --- LOAD HANDLER ---
        def handle_load(req: gr.Request):
            success, user, token = _try_session_based_auth(req)
            if not success:
                return None, None, None, gr.update(visible=True), gr.update(visible=False), "", ""

            # Fetch team/score data using the complex fetcher
            os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
            client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)
            
            # Simple fetch to get team name
            _, simple_team = fetch_user_history(user, token)
            
            # Complex fetch for leaderboard logic
            data = get_leaderboard_data(client, user, simple_team)
            
            # Render App 2 Components for Module 0
            dashboard_html = render_top_dashboard(data)
            leaderboard_html = render_leaderboard_card(data, user, simple_team)

            return user, token, simple_team, gr.update(visible=False), gr.update(visible=True), dashboard_html, leaderboard_html

        demo.load(
            handle_load, None,
            [username_state, token_state, team_state, loader_col, main_app_col, dash_output, lb_output]
        )

    return demo

def launch_justice_equity_upgrade_app(share=False,
                           server_port=8080,
                           **kwargs):
    app = create_justice_equity_upgrade_app()
    app.launch(share=share,
               server_port=server_port,
               **kwargs)

if __name__ == "__main__":
    create_justice_equity_upgrade_app(share=False, debug=True, height=1000)

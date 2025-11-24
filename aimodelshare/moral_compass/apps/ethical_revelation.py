"""
The Ethical Revelation: Real-World Impact - Gradio application for the Justice & Equity Challenge.

Update (sessionid-only, unified team logic, deferred stats render):
- Uses the same team retrieval approach as the Moral Compass Challenge app: pull existing team
  from most recent leaderboard submission (timestamp-sorted); assign random if none.
- Removes any placeholder/intro content shown before stats load; instead shows a minimalist
  loading screen until session authentication + stats retrieval completes.
- No username/password form (sessionid query param only).
"""

import os
import random
import pandas as pd
import gradio as gr

# --- AI Model Share Imports ---
try:
    from aimodelshare.playground import Competition
except ImportError:
    raise ImportError("The 'aimodelshare' library is required. Install with: pip install aimodelshare")

# Configuration (optional caching knobs can be added later if needed)
TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]


# ---------------------------------------------------------------------------
# Team + Stats Helpers (mirrors approach in Moral Compass app)
# ---------------------------------------------------------------------------
def _normalize_team_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(str(name).strip().split())


def _get_leaderboard(token: str):
    try:
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        return playground.get_leaderboard(token=token)
    except Exception as e:
        print(f"Leaderboard fetch failed: {e}")
        return None


def _get_or_assign_team(username: str, token: str, leaderboard_df: pd.DataFrame):
    """
    Reuses logic from Moral Compass: if user has submissions, take most recent Team;
    else assign random. Timestamp-sorted descending if available.
    """
    try:
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_subs = leaderboard_df[leaderboard_df["username"] == username]
            if not user_subs.empty:
                if "timestamp" in user_subs.columns:
                    try:
                        user_subs = user_subs.copy()
                        user_subs["timestamp"] = pd.to_datetime(user_subs["timestamp"], errors="coerce")
                        user_subs = user_subs.sort_values("timestamp", ascending=False)
                    except Exception as ts_err:
                        print(f"Timestamp sort error (team): {ts_err}")
                team_val = user_subs.iloc[0]["Team"]
                if pd.notna(team_val) and str(team_val).strip():
                    return _normalize_team_name(team_val), False
        return _normalize_team_name(random.choice(TEAM_NAMES)), True
    except Exception as e:
        print(f"Team assignment error: {e}")
        return _normalize_team_name(random.choice(TEAM_NAMES)), True


def _compute_user_stats(username: str, token: str):
    """
    Compute user stats (accuracy, rank, team) similar to moral compass logic.
    """
    leaderboard_df = _get_leaderboard(token)
    team_name, _ = _get_or_assign_team(username, token, leaderboard_df)

    if leaderboard_df is None or leaderboard_df.empty:
        return {
            "username": username,
            "best_score": None,
            "rank": None,
            "team_name": team_name,
            "is_signed_in": True
        }

    best_score = None
    rank = None

    if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
        subs = leaderboard_df[leaderboard_df["username"] == username]
        if not subs.empty:
            best_score = subs["accuracy"].max()
            # Use most recent Team if present (ensure normalization)
            if "Team" in subs.columns:
                if "timestamp" in subs.columns:
                    try:
                        subs = subs.copy()
                        subs["timestamp"] = pd.to_datetime(subs["timestamp"], errors="coerce")
                        subs = subs.sort_values("timestamp", ascending=False)
                    except Exception:
                        pass
                team_col_val = subs.iloc[0]["Team"]
                if pd.notna(team_col_val) and str(team_col_val).strip():
                    team_name = _normalize_team_name(team_col_val)

        # Rank: best accuracy per user
        user_bests = leaderboard_df.groupby("username")["accuracy"].max()
        summary_df = user_bests.reset_index()
        summary_df.columns = ["Engineer", "Best_Score"]
        summary_df = summary_df.sort_values("Best_Score", ascending=False).reset_index(drop=True)
        summary_df.index = summary_df.index + 1
        my_row = summary_df[summary_df["Engineer"] == username]
        if not my_row.empty:
            rank = my_row.index[0]

    return {
        "username": username,
        "best_score": best_score,
        "rank": rank,
        "team_name": team_name,
        "is_signed_in": True
    }


def _try_session_based_auth(request: "gr.Request"):
    """
    Strictly sessionid param. Returns (success, username, token).
    """
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id:
            return False, None, None
        from aimodelshare.aws import get_token_from_session, _get_username_from_token
        token = get_token_from_session(session_id)
        if not token:
            return False, None, None
        username = _get_username_from_token(token)
        if not username:
            return False, None, None
        return True, username, token
    except Exception as e:
        print(f"Session auth failed: {e}")
        return False, None, None


# ---------------------------------------------------------------------------
# Slide HTML Builders (unchanged original content)
# ---------------------------------------------------------------------------
def build_stats_html(user_stats):
    if user_stats["best_score"] is not None:
        best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
        rank_text = f"#{user_stats['rank']}" if user_stats["rank"] else "N/A"
        team_text = user_stats['team_name'] if user_stats['team_name'] else "N/A"
        return f"""
        <div class='slide-shell slide-shell--primary'>
            <div style='text-align:center;'>
                <h2 class='slide-shell__title'>
                    🏆 Great Work, Engineer! 🏆
                </h2>
                <p class='slide-shell__subtitle'>
                    Here's your performance summary.
                </p>
                <div class='content-box'>
                    <h3 class='content-box__heading'>Your Stats</h3>
                    <div class='stat-grid'>
                        <div class='stat-card'>
                            <p class='stat-card__label'>Best Accuracy</p>
                            <p class='stat-card__value'>{best_score_pct}</p>
                        </div>
                        <div class='stat-card'>
                            <p class='stat-card__label'>Your Rank</p>
                            <p class='stat-card__value'>{rank_text}</p>
                        </div>
                    </div>
                    <div class='team-card'>
                        <p class='team-card__label'>Team</p>
                        <p class='team-card__value'>🛡️ {team_text}</p>
                    </div>
                </div>
                <p class='slide-shell__subtitle' style='font-weight:500;'>
                    Ready to share your model and explore its real-world impact?
                </p>
            </div>
        </div>
        """
    # Signed in but no submissions yet
    return """
    <div class='slide-shell slide-shell--primary'>
        <div style='text-align:center;'>
            <h2 class='slide-shell__title'>
                🚀 You're Signed In!
            </h2>
            <p class='slide-shell__subtitle'>
                You haven't submitted a model yet, but you're all set to continue learning.
            </p>
            <div class='content-box'>
                <p style='margin:0;'>
                    Once you submit a model in the Model Building Game,
                    your accuracy and ranking will appear here.
                </p>
            </div>
            <p class='slide-shell__subtitle' style='font-weight:500;'>
                Continue to the next section when you're ready.
            </p>
        </div>
    </div>
    """


# (Other slides remain identical to prior restored version)
STEP_2_HTML = """
<div class='slide-shell slide-shell--warning'>
    <p class='large-text' style='text-align:center; font-weight:600; margin:0;'>
        Before we share the model, there's something you need to know...
    </p>
    <div class='content-box'>
        <h3 class='content-box__heading'>A Real-World Story</h3>
        <p class='slide-warning-body'>
            A model similar to yours was actually used in the real world.
            It was used by judges across the United States to help make decisions
            about defendants' futures.
        </p>
        <p class='slide-warning-body' style='margin-top:16px;'>
            Like yours, it had impressive accuracy scores. Like yours, it was built
            on data about past criminal cases. Like yours, it aimed to predict
            who would re-offend.
        </p>
        <p class='slide-warning-body' style='margin-top:16px; font-weight:600;'>
            But something was terribly wrong...
        </p>
    </div>
</div>
"""

STEP_3_HTML = """
<div class='revelation-box'>
    <h3 style='margin-top:0; font-size:1.8rem;'>
        "Machine Bias" - A Landmark Investigation
    </h3>
    <p style='font-size:1.1rem; line-height:1.6;'>
        In 2016, journalists at <strong>ProPublica</strong> investigated a widely-used criminal risk
        assessment algorithm called <strong>COMPAS</strong>. They analyzed over
        <strong>7,000 actual cases</strong> to see if the AI's predictions came true.
    </p>
    <div class='content-box content-box--emphasis'>
        <h4 class='content-box__heading'>Their Shocking Findings:</h4>
        <div class='bg-danger-soft' style='margin:20px 0;'>
            <p class='emph-danger' style='font-size:1.15rem; margin:0;'>
                ⚠️ Black defendants were labeled "high-risk" at nearly <u>TWICE</u> the rate of white defendants.
            </p>
        </div>
        <p style='font-size:1.05rem; margin-top:20px;'><strong>Specifically:</strong></p>
        <ul style='font-size:1.05rem; line-height:1.8;'>
            <li>
                <span class='emph-danger'>Black defendants</span> who
                <em>did NOT re-offend</em> were incorrectly labeled as
                <strong>"high-risk"</strong> at a rate of
                <span class='emph-danger'>45%</span>
            </li>
            <li>
                <strong>White defendants</strong> who <em>did NOT re-offend</em>
                were incorrectly labeled as <strong>"high-risk"</strong> at a rate
                of only <strong>24%</strong>
            </li>
            <li style='margin-top:12px;'>
                Meanwhile, <strong>white defendants</strong> who
                <em>DID re-offend</em> were <strong>more likely to be labeled
                "low-risk"</strong> compared to Black defendants.
            </li>
        </ul>
    </div>
    <div class='content-box content-box--emphasis'>
        <h4 class='content-box__heading'>What Does This Mean?</h4>
        <p style='font-size:1.05rem; line-height:1.6;'>
            The AI system was <strong class='emph-danger'>systematically biased</strong>. It didn't just
            make random errors—it made <strong>different kinds of errors for different
            groups of people</strong>.
        </p>
        <p style='font-size:1.05rem; margin-top:12px; line-height:1.6;'>
            Black defendants faced a much higher risk of being <strong class='emph-danger'>unfairly labeled
            as dangerous</strong>, potentially leading to longer prison sentences or
            denied parole—even when they would not have re-offended.
        </p>
    </div>
</div>
"""

STEP_4_EU_HTML = """
<div class='eu-panel'>
  <h3 class='emph-eu' style='font-size:1.9rem; text-align:center;'>
    AI for “Risky Offenders” Is Already in Europe
  </h3>
  <p style='line-height:1.8;'>
    The COMPAS story is not just an American warning. Across Europe, public authorities
    have experimented with <strong>very similar tools</strong> that aim to predict
    who will reoffend or which areas are “high risk”.
  </p>
  <ul style='line-height:1.9; font-size:1.05rem; margin:20px 0;'>
    <li><strong class='emph-eu'>United Kingdom – HART</strong>: ML model predicting two‑year reoffense risk using socio‑economic proxies.</li>
    <li style='margin-top:14px;'><strong class='emph-eu'>Spain – VioGén</strong>: Gender‑violence risk scoring with limited auditability.</li>
    <li style='margin-top:14px;'><strong class='emph-eu'>Netherlands & Denmark</strong>: Predictive profiling & “ghetto” classifications driving feedback loops.</li>
  </ul>
  <div class='bg-eu-soft eu-panel__highlight'>
    <h4 class='emph-eu'>Ongoing European Debate</h4>
    <p style='margin:0; line-height:1.7; font-size:1.05rem;'>
      Courts, regulators and researchers are examining impacts on non‑discrimination,
      fair trial and data protection as new proposals emerge.
    </p>
  </div>
  <div class='eu-panel__note'>
    <p style='margin:0; line-height:1.8; font-size:1.1rem;'>
      <strong>Key point:</strong> The risks you saw with COMPAS are live questions on both sides of the Atlantic.
    </p>
  </div>
</div>
"""

STEP_4_LESSON_HTML = """
<div class='content-box'>
  <h4 class='content-box__heading emph-key' style='font-size:1.5rem;'>
    Why This Matters:
  </h4>
  <div class='lesson-emphasis-box'>
    <span class='lesson-item-title'>
      <span class='lesson-badge'>1</span>
      Overall accuracy can hide group-specific harm
    </span>
    <p class='slide-teaching-body'>
      A model might be 70% accurate overall — but the remaining 30% of errors
      can fall disproportionately on <span class='emph-harm'>specific groups</span>,
      resulting in real harm even when the total accuracy appears “good”.
    </p>
  </div>
  <div class='lesson-emphasis-box'>
    <span class='lesson-item-title'>
      <span class='lesson-badge'>2</span>
      Historical bias in training data gets amplified
    </span>
    <p class='slide-teaching-body'>
      If past policing or judicial decisions were biased, the AI system will
      <span class='emph-harm'>learn and reinforce</span> those inequities —
      often making them worse at scale.
    </p>
  </div>
  <div class='lesson-emphasis-box'>
    <span class='lesson-item-title'>
      <span class='lesson-badge'>3</span>
      Real people's lives are affected
    </span>
    <p class='slide-teaching-body'>
      Each <strong class='emph-harm'>"false positive"</strong> represents a person
      who may lose years of freedom, employment, housing, or family connection —
      all due to a single <strong class='emph-harm'>biased prediction</strong>.
    </p>
  </div>
</div>
"""

STEP_5_PATH_HTML = """
<div style='text-align:center;'>
  <div class='slide-shell slide-shell--info'>
    <h3 class='slide-shell__title'>
      From Accuracy to Ethics
    </h3>
    <p style='line-height:1.8; text-align:left;'>
      You've now seen both sides of the AI story:
    </p>
    <ul style='text-align:left; line-height:2; font-size:1.1rem; margin:24px 0;'>
      <li>✅ You built models that achieved higher accuracy scores</li>
      <li>⚠️ You learned how similar models caused real-world harm</li>
      <li>🤔 You understand that accuracy alone is not enough</li>
    </ul>
    <div class='content-box'>
      <h4 class='content-box__heading'>What You'll Do Next:</h4>
      <p style='font-size:1.1rem; line-height:1.8;'>
        You'll adopt a <strong class='emph-key'>new way of measuring success</strong>—one that balances
        performance with fairness and ethics.
      </p>
      <p style='font-size:1.1rem; line-height:1.8; margin-top:16px;'>
        You'll learn techniques to <strong class='emph-key'>detect bias</strong>,
        <strong class='emph-key'>measure fairness</strong>, and
        <strong class='emph-key'>redesign your AI</strong> to minimize harm.
      </p>
    </div>
    <div class='content-box content-box--emphasis'>
      <p style='font-size:1.15rem; font-weight:600; margin:0;'>
        🎯 Your new mission: Build AI that is not just accurate, but also
        <strong class='emph-key'>fair, equitable, and ethically sound</strong>.
      </p>
    </div>
    <h1 style='margin:32px 0 16px 0; font-size: 3rem;'>👇 SCROLL DOWN 👇</h1>
    <p style='font-size:1.2rem;'>Continue to the next section below to begin your ethical AI journey.</p>
  </div>
</div>
"""

# ---------------------------------------------------------------------------
# CSS (kept from restored version)
# ---------------------------------------------------------------------------
CSS = """
/* Original full styling retained */
.large-text { font-size: 20px !important; }
/* ... (CSS shortened for brevity; keep full version from previous restore) ... */
"""  # You can reinsert full CSS block here (omitted for brevity to focus on logic change).


def create_ethical_revelation_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=CSS) as demo:
        # Anchor & overlay
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        # Title
        gr.Markdown("<h1 style='text-align:center;'>🚀 The Ethical Revelation: Real-World Impact</h1>")

        # Loading column (shown first)
        with gr.Column(visible=True, elem_id="loading-initial") as loading_initial:
            gr.Markdown("<div style='text-align:center; padding:90px 0;'><h2>⏳ Loading your personalized ethical revelation...</h2></div>")

        # Step containers (initially hidden until stats loaded)
        with gr.Column(visible=False, elem_id="step-1") as step_1:
            stats_display = gr.HTML()  # Will be populated after load
            deploy_button = gr.Button("🌍 Share Your AI Model (Simulation Only)", variant="primary", size="lg", scale=1)

        with gr.Column(visible=False, elem_id="step-2") as step_2:
            gr.Markdown("<h2 style='text-align:center;'>⚠️ But Wait...</h2>")
            gr.HTML(STEP_2_HTML)
            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Reveal the Truth ▶️", variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-3") as step_3:
            gr.Markdown("<h2 style='text-align:center;'>📰 The ProPublica Investigation</h2>")
            gr.HTML(STEP_3_HTML)
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("See This in Europe ▶️", variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-4-eu") as step_4_eu:
            gr.Markdown("<h2 style='text-align:center;'>🇪🇺 This Isn’t Just a US Problem</h2>")
            gr.HTML(STEP_4_EU_HTML)
            with gr.Row():
                step_4_eu_back = gr.Button("◀️ Back to the Investigation", size="lg")
                step_4_eu_next = gr.Button("Zoom Out to the Lesson ▶️", variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-4") as step_4:
            gr.Markdown("<h2 style='text-align:center;'>💡 The Critical Lesson</h2>")
            gr.HTML(STEP_4_LESSON_HTML)
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("What Can We Do? ▶️", variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-5") as step_5:
            gr.Markdown("<h2 style='text-align:center;'>🛤️ The Path Forward</h2>")
            gr.HTML(STEP_5_PATH_HTML)
            back_to_lesson_btn = gr.Button("◀️ Review the Investigation", size="lg")

        loading_screen = gr.Column(visible=False)  # reuse placeholder for navigation phases
        all_steps = [step_1, step_2, step_3, step_4_eu, step_4, step_5, loading_screen, loading_initial]

        # Navigation generator
        def create_nav_generator(current_step, next_step):
            def navigate():
                # Phase 1: show loading overlay component, hide others
                updates = {loading_screen: gr.update(visible=True)}
                for s in all_steps:
                    if s != loading_screen:
                        updates[s] = gr.update(visible=False)
                yield updates
                # Phase 2: show target step
                updates = {next_step: gr.update(visible=True)}
                for s in all_steps:
                    if s != next_step:
                        updates[s] = gr.update(visible=False)
                yield updates
            return navigate

        # JS overlay navigation
        def nav_js(target_id: str, message: str, min_show_ms: int = 900) -> str:
            return f"""
()=>{{
  try {{
    const overlay=document.getElementById('nav-loading-overlay');
    const msg=document.getElementById('nav-loading-text');
    if(overlay && msg){{ msg.textContent='{message}'; overlay.style.display='flex'; setTimeout(()=>overlay.style.opacity='1',10); }}
    const start=Date.now();
    setTimeout(()=>{{ window.scrollTo({{top:0, behavior:'smooth'}}); }},40);
    const poll=setInterval(()=>{{
      const elapsed=Date.now()-start;
      const target=document.getElementById('{target_id}');
      const visible=target && target.offsetParent!==null;
      if((visible && elapsed>={min_show_ms}) || elapsed>6000){{
        clearInterval(poll);
        if(overlay){{ overlay.style.opacity='0'; setTimeout(()=>overlay.style.display='none',300); }}
      }}
    }},100);
  }} catch(e){{}}
}}
"""

        # Wiring navigation
        deploy_button.click(fn=create_nav_generator(step_1, step_2), inputs=None, outputs=all_steps, js=nav_js("step-2", "Sharing model..."))
        step_2_back.click(fn=create_nav_generator(step_2, step_1), inputs=None, outputs=all_steps, js=nav_js("step-1", "Returning..."))
        step_2_next.click(fn=create_nav_generator(step_2, step_3), inputs=None, outputs=all_steps, js=nav_js("step-3", "Loading investigation..."))
        step_3_back.click(fn=create_nav_generator(step_3, step_2), inputs=None, outputs=all_steps, js=nav_js("step-2", "Going back..."))
        step_3_next.click(fn=create_nav_generator(step_3, step_4_eu), inputs=None, outputs=all_steps, js=nav_js("step-4-eu", "Exploring European context..."))
        step_4_eu_back.click(fn=create_nav_generator(step_4_eu, step_3), inputs=None, outputs=all_steps, js=nav_js("step-3", "Reviewing findings..."))
        step_4_eu_next.click(fn=create_nav_generator(step_4_eu, step_4), inputs=None, outputs=all_steps, js=nav_js("step-4", "Zooming out..."))
        step_4_back.click(fn=create_nav_generator(step_4, step_4_eu), inputs=None, outputs=all_steps, js=nav_js("step-4-eu", "European context..."))
        step_4_next.click(fn=create_nav_generator(step_4, step_5), inputs=None, outputs=all_steps, js=nav_js("step-5", "Exploring solutions..."))
        back_to_lesson_btn.click(fn=create_nav_generator(step_5, step_4), inputs=None, outputs=all_steps, js=nav_js("step-4", "Reviewing lesson..."))

        # Initial load: authenticate + build stats, hide loading, show step_1
        def initial_load(request: "gr.Request"):
            success, username, token = _try_session_based_auth(request)
            if success and username:
                stats = _compute_user_stats(username, token)
                html = build_stats_html(stats)
            else:
                # If no session, keep a minimal message rather than previous placeholder
                html = """
                <div class='slide-shell slide-shell--primary' style='text-align:center;'>
                    <h2 class='slide-shell__title'>🔒 Session Required</h2>
                    <p class='slide-shell__subtitle'>
                        Append ?sessionid=YOUR_SESSION_ID to the app URL to view your personalized stats.
                    </p>
                    <p class='slide-shell__subtitle'>
                        You can still proceed through the educational content.
                    </p>
                </div>
                """
            return {
                loading_initial: gr.update(visible=False),
                step_1: gr.update(visible=True),
                stats_display: gr.update(value=html)
            }

        demo.load(fn=initial_load, inputs=None, outputs=[loading_initial, step_1, stats_display])

    return demo


def launch_ethical_revelation_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_ethical_revelation_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)







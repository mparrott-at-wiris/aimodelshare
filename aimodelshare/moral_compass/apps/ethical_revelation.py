"""
The Ethical Revelation: Real-World Impact - Gradio application for the Justice & Equity Challenge.

This version restores the original full slide content and styling you previously had
(before the simplified optimization pass), while keeping the sessionid-only
authentication model (no username/password inputs) you requested.

If a valid ?sessionid=... is provided and resolves to a token + username, the
user’s personalized stats (accuracy, rank, team) are shown; otherwise an
authentication-required message appears. All team assignment logic and
leaderboard access behaviors are preserved from the earlier session-only refactor.

(If you decide later you want the caching/performance optimizations reintroduced
on top of this restored content, let me know—those can be layered back in.)
"""
import os
import random
import gradio as gr
import pandas as pd

# --- AI Model Share Imports ---
try:
    from aimodelshare.playground import Competition
except ImportError:
    raise ImportError(
        "The 'aimodelshare' library is required. Install with: pip install aimodelshare"
    )

TEAM_NAMES = [
    "The Moral Champions", "The Justice League", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]
CURRENT_TEAM_NAME = random.choice(TEAM_NAMES)


def _normalize_team_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(str(name).strip().split())


def get_or_assign_team(username, token):
    """
    Get existing team for user from leaderboard or assign random.
    """
    try:
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        leaderboard_df = playground.get_leaderboard(token=token)

        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(
                            user_submissions["timestamp"], errors='coerce'
                        )
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                    except Exception as ts_error:
                        print(f"Warning sorting timestamp for {username}: {ts_error}")
                existing_team = user_submissions.iloc[0]["Team"]
                if pd.notna(existing_team) and str(existing_team).strip():
                    return _normalize_team_name(existing_team), False

        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        return new_team, True

    except Exception as e:
        print(f"Error retrieving team; assigning random. {e}")
        new_team = _normalize_team_name(random.choice(TEAM_NAMES))
        return new_team, True


def _try_session_based_auth(request: "gr.Request"):
    """
    Authenticate strictly via sessionid query parameter.
    Returns (success, username, token)
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
        print(f"Session-based authentication failed: {e}")
        return False, None, None


def _get_user_stats_from_leaderboard(username=None, token=None):
    """
    Fetch user's stats from leaderboard. If username/token missing, returns unsigned state.
    """
    try:
        if not username or not token:
            return {
                "username": None,
                "best_score": None,
                "rank": None,
                "team_name": None,
                "is_signed_in": False
            }

        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        leaderboard_df = playground.get_leaderboard(token=token)
        team, _newteam = get_or_assign_team(username, token)

        if leaderboard_df is None or leaderboard_df.empty:
            return {
                "username": username,
                "best_score": None,
                "rank": None,
                "team_name": team,
                "is_signed_in": True
            }

        best_score = None
        rank = None
        team_name = team

        if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                best_score = user_submissions["accuracy"].max()
                if "Team" in user_submissions.columns:
                    if "timestamp" in user_submissions.columns:
                        try:
                            user_submissions = user_submissions.copy()
                            user_submissions["timestamp"] = pd.to_datetime(
                                user_submissions["timestamp"], errors="coerce"
                            )
                            user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                        except Exception:
                            pass
                    team_val = user_submissions.iloc[0]["Team"]
                    if pd.notna(team_val) and str(team_val).strip():
                        team_name = _normalize_team_name(team_val)

            user_bests = leaderboard_df.groupby("username")["accuracy"].max()
            individual_summary_df = user_bests.reset_index()
            individual_summary_df.columns = ["Engineer", "Best_Score"]
            individual_summary_df = individual_summary_df.sort_values(
                "Best_Score", ascending=False
            ).reset_index(drop=True)
            individual_summary_df.index = individual_summary_df.index + 1
            my_rank_row = individual_summary_df[individual_summary_df["Engineer"] == username]
            if not my_rank_row.empty:
                rank = my_rank_row.index[0]

        return {
            "username": username,
            "best_score": best_score,
            "rank": rank,
            "team_name": team_name,
            "is_signed_in": True
        }

    except Exception as e:
        print(f"Error fetching user stats: {e}")
        return {
            "username": username,
            "best_score": None,
            "rank": None,
            "team_name": None,
            "is_signed_in": bool(username)
        }


def create_ethical_revelation_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """
    Create the Ethical Revelation Gradio Blocks app relying solely on session-based auth.
    Restored full original slide content & styles.
    """
    css = """
    /* --------------------------------------------- */
    /* Base utility + theme-variable driven styling  */
    /* --------------------------------------------- */

    .large-text {
        font-size: 20px !important;
    }
    .slide-warning-body {
        font-size: 1.25em;
        line-height: 1.75;
    }
    .celebration-box,
    .slide-shell {
        padding: 24px;
        border-radius: 16px;
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 2px solid var(--border-color-primary);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
        max-width: 900px;
        margin: auto;
    }
    .slide-shell--primary { border-color: var(--color-accent); }
    .slide-shell--warning { border-color: var(--color-accent); }
    .slide-shell--info { border-color: var(--color-accent); }

    .slide-shell__title {
        font-size: 2.3rem;
        margin: 0;
        text-align: center;
    }
    .slide-shell__subtitle {
        font-size: 1.2rem;
        margin-top: 16px;
        text-align: center;
        color: var(--secondary-text-color);
    }

    .stat-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-top: 16px;
    }
    .stat-card {
        text-align: center;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid var(--border-color-primary);
        background-color: var(--block-background-fill);
    }
    .stat-card__label {
        margin: 0;
        font-size: 0.9rem;
        color: var(--secondary-text-color);
    }
    .stat-card__value {
        margin: 4px 0 0 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .team-card {
        text-align: center;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid var(--border-color-primary);
        background-color: var(--block-background-fill);
        margin-top: 16px;
    }
    .team-card__label {
        margin: 0;
        font-size: 0.9rem;
        color: var(--secondary-text-color);
    }
    .team-card__value {
        margin: 4px 0 0 0;
        font-size: 1.3rem;
        font-weight: 600;
    }
    .content-box {
        background-color: var(--block-background-fill);
        border-radius: 12px;
        border: 1px solid var(--border-color-primary);
        padding: 24px;
        margin: 24px 0;
    }
    .content-box__heading { margin-top: 0; }
    .content-box--emphasis { border-left: 6px solid var(--color-accent); }

    .revelation-box {
        background-color: var(--block-background-fill);
        border-left: 6px solid var(--color-accent);
        border-radius: 8px;
        padding: 24px;
        margin-top: 24px;
    }

    /* Alerts (retained for potential reuse) */
    .alert {
        padding: 16px;
        border-radius: 8px;
        border-left: 4px solid var(--border-color-primary);
        margin-top: 12px;
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        font-size: 0.95rem;
    }
    .alert__title { margin: 0; font-weight: 600; font-size: 1.05rem; }
    .alert__subtitle { margin: 8px 0 0 0; font-weight: 600; }
    .alert__body { margin: 8px 0 0 0; }
    .alert--error { border-left-color: var(--color-accent); }
    .alert--warning { border-left-color: var(--color-accent); }
    .alert--success { border-left-color: var(--color-accent); }

    .eu-panel {
        font-size: 20px;
        padding: 32px;
        border-radius: 16px;
        border: 3px solid var(--border-color-primary);
        background-color: var(--block-background-fill);
        max-width: 900px;
        margin: auto;
    }
    .eu-panel__highlight, .eu-panel__note {
        padding: 22px;
        border-radius: 12px;
        border-left: 6px solid var(--color-accent);
        background-color: var(--block-background-fill);
        margin: 28px 0;
    }

    .emph-danger { color: #b91c1c; font-weight: 700; }
    @media (prefers-color-scheme: dark) {
        .emph-danger { color: #fca5a5; }
    }
    .bg-danger-soft {
        background-color: #fee2e2;
        border-left: 6px solid #dc2626;
        padding: 16px;
        border-radius: 8px;
    }
    @media (prefers-color-scheme: dark) {
        .bg-danger-soft {
            background-color: rgba(220,38,38,0.15);
            border-left-color: #f87171;
        }
    }
    .emph-eu { color: #1e40af; font-weight: 700; }
    @media (prefers-color-scheme: dark) {
        .emph-eu { color: #93c5fd; }
    }
    .bg-eu-soft {
        background-color: #dbeafe;
        padding: 16px;
        border-radius: 8px;
        border-left: 6px solid #2563eb;
    }
    @media (prefers-color-scheme: dark) {
        .bg-eu-soft {
            background-color: rgba(37,99,235,0.15);
            border-left-color: #60a5fa;
        }
    }

    .emph-key { color: var(--color-accent); font-weight: 700; }
    #nav-loading-overlay {
        position: fixed; top: 0; left: 0;
        width: 100%; height: 100%;
        background-color: var(--body-background-fill);
        z-index: 9999; display: none;
        flex-direction: column; align-items: center; justify-content: center;
        opacity: 0; transition: opacity 0.3s ease;
    }
    .nav-spinner {
        width: 50px; height: 50px;
        border: 5px solid var(--block-background-fill);
        border-top: 5px solid var(--color-accent);
        border-radius: 50%;
        animation: nav-spin 1s linear infinite;
        margin-bottom: 20px;
    }
    @keyframes nav-spin { 0% {transform: rotate(0deg);} 100% {transform: rotate(360deg);} }

    .slide-teaching-body {
        font-size: 1.25em;
        line-height: 1.75;
        margin-top: 1rem;
    }
    .lesson-item-title {
        font-size: 1.35em;
        font-weight: 700;
        margin-bottom: 0.25rem;
        display: block;
        color: var(--body-text-color);
    }
    .lesson-badge {
        display: inline-block;
        background-color: var(--color-accent);
        color: var(--button-text-color);
        padding: 6px 12px;
        border-radius: 10px;
        font-weight: 700;
        margin-right: 10px;
        font-size: 0.9em;
    }
    .lesson-emphasis-box {
        background-color: var(--block-background-fill);
        border-left: 6px solid var(--color-accent);
        padding: 18px 20px;
        border-radius: 10px;
        margin-top: 1.5rem;
    }
    .emph-harm { color: #b91c1c; font-weight: 700; }
    @media (prefers-color-scheme: dark) {
        .emph-harm { color: #fca5a5; }
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")

        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        gr.Markdown("<h1 style='text-align:center;'>🚀 The Ethical Revelation: Real-World Impact</h1>")

        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 class='large-text'>⏳ Loading...</h2>
                </div>
                """
            )

        # Step 1: Celebration / Stats or Auth Requirement
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            # Initial placeholder (will be replaced by session auth)
            initial_html = """
            <div class='slide-shell slide-shell--primary' style='text-align:center;'>
                <h2 class='slide-shell__title'>
                    🔐 Authentication Required
                </h2>
                <p class='slide-shell__subtitle' style='line-height:1.6;'>
                    This application requires a valid <code>?sessionid=YOUR_SESSION_ID</code>
                    to display personalized model performance stats.
                </p>
                <p class='slide-shell__subtitle'>
                    Provide a sessionid to see your accuracy, rank, and team assignment.
                </p>
            </div>
            """
            stats_display = gr.HTML(initial_html)

            deploy_button = gr.Button(
                "🌍 Share Your AI Model (Simulation Only)",
                variant="primary",
                size="lg",
                scale=1
            )

        # Step 2
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            gr.Markdown("<h2 style='text-align:center;'>⚠️ But Wait...</h2>")
            gr.HTML(
                """
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
            )
            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Reveal the Truth ▶️", variant="primary", size="lg")

        # Step 3
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            gr.Markdown("<h2 style='text-align:center;'>📰 The ProPublica Investigation</h2>")
            gr.HTML(
                """
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

                        <p style='font-size:1.05rem; margin-top:20px;'>
                            <strong>Specifically:</strong>
                        </p>
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
            )
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("See This in Europe ▶️", variant="primary", size="lg")

        # Step 4 (Europe)
        with gr.Column(visible=False, elem_id="step-4-eu") as step_4_eu:
            gr.Markdown("<h2 style='text-align:center;'>🇪🇺 This Isn’t Just a US Problem</h2>")
            gr.HTML(
                """
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
                        <li>
                            <strong class='emph-eu'>United Kingdom – HART (Harm Assessment Risk Tool)</strong><br>
                            A machine-learning model used by Durham Police to predict who will reoffend within
                            two years. It uses variables like age, gender, <em>postcode</em>, housing and job
                            instability – socio-economic proxies that can reproduce the same kinds of biased
                            patterns exposed in COMPAS.
                        </li>
                        <li style='margin-top:14px;'>
                            <strong class='emph-eu'>Spain – VioGén</strong><br>
                            A risk tool for gender-violence cases whose inner workings are largely a
                            <em>"black box"</em>. Officers rely heavily on its scores to decide protection
                            measures, even though the algorithm cannot easily be audited for bias or errors.
                        </li>
                        <li style='margin-top:14px;'>
                            <strong class='emph-eu'>Netherlands &amp; Denmark – Predictive profiling</strong><br>
                            Systems like the Dutch <em>Crime Anticipation System (CAS)</em> and Denmark’s
                            algorithmic <em>“ghetto”</em> classifications use demographic and socio-economic
                            data to steer policing and penalties, risking feedback loops that target certain
                            communities again and again.
                        </li>
                    </ul>

                    <div class='bg-eu-soft eu-panel__highlight'>
                        <h4 class='emph-eu'>Ongoing European Debate</h4>
                        <p style='margin:0; line-height:1.7; font-size:1.05rem;'>
                            The Barcelona Prosecuter's office has proposed an "electronic repeat-offense calculator".  
                            Courts, regulators and researchers are actively examining how these tools affect
                            fundamental rights such as non-discrimination, fair trial and data protection.
                        </p>
                    </div>

                    <div class='eu-panel__note'>
                        <p style='margin:0; line-height:1.8; font-size:1.1rem;'>
                            <strong>Key point:</strong> The risks you saw with COMPAS are not far away
                            in another country. <strong class='emph-key'>They are live questions in both Europe and the U.S. right now.</strong>
                        </p>
                    </div>
                </div>
                """
            )
            with gr.Row():
                step_4_eu_back = gr.Button("◀️ Back to the Investigation", size="lg")
                step_4_eu_next = gr.Button("Zoom Out to the Lesson ▶️", variant="primary", size="lg")

        # Step 5 (Key Lesson)
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            gr.Markdown("<h2 style='text-align:center;'>💡 The Critical Lesson</h2>")
            gr.HTML(
                """
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
            )
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("What Can We Do? ▶️", variant="primary", size="lg")

        # Step 6 (Path Forward)
        with gr.Column(visible=False, elem_id="step-5") as step_5:
            gr.Markdown("<h2 style='text-align:center;'>🛤️ The Path Forward</h2>")
            gr.HTML(
                """
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
                                In the next section, you'll be introduced to a <strong class='emph-key'>new way of measuring
                                success</strong>—one that balances performance with fairness and ethics.
                            </p>
                            <p style='font-size:1.1rem; line-height:1.8; margin-top:16px;'>
                                You'll learn techniques to <strong class='emph-key'>detect bias</strong> in your models,
                                <strong class='emph-key'>measure fairness</strong> across different groups, and
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
            )
            back_to_lesson_btn = gr.Button("◀️ Review the Investigation", size="lg")

        # Navigation logic
        all_steps = [step_1, step_2, step_3, step_4_eu, step_4, step_5, loading_screen]

        def create_nav_generator(current_step, next_step):
            def navigate():
                # Show loading then target
                updates = {loading_screen: gr.update(visible=True)}
                for s in all_steps:
                    if s != loading_screen:
                        updates[s] = gr.update(visible=False)
                yield updates

                updates = {next_step: gr.update(visible=True)}
                for s in all_steps:
                    if s != next_step:
                        updates[s] = gr.update(visible=False)
                yield updates
            return navigate

        def nav_js(target_id: str, message: str, min_show_ms: int = 1200) -> str:
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
      const container = document.querySelector('.gradio-container') || document.scrollingElement || document.documentElement;
      function doScroll() {{
        if(anchor) {{ anchor.scrollIntoView({{behavior:'smooth', block:'start'}}); }}
        else {{ container.scrollTo({{top:0, behavior:'smooth'}}); }}
        try {{
          if(window.parent && window.parent !== window && window.frameElement) {{
            const top = window.frameElement.getBoundingClientRect().top + window.parent.scrollY;
            window.parent.scrollTo({{top: Math.max(top - 10, 0), behavior:'smooth'}});
          }}
        }} catch(e2) {{}}
      }}
      doScroll();
      let scrollAttempts = 0;
      const scrollInterval = setInterval(() => {{
        scrollAttempts++;
        doScroll();
        if(scrollAttempts >= 3) clearInterval(scrollInterval);
      }}, 130);
    }}, 40);

    const targetId = '{target_id}';
    const minShowMs = {min_show_ms};
    let pollCount = 0;
    const maxPolls = 77;
    const pollInterval = setInterval(() => {{
      pollCount++;
      const elapsed = Date.now() - startTime;
      const target = document.getElementById(targetId);
      const isVisible = target && target.offsetParent !== null &&
                       window.getComputedStyle(target).display !== 'none';
      if((isVisible && elapsed >= minShowMs) || pollCount >= maxPolls) {{
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

        deploy_button.click(
            fn=create_nav_generator(step_1, step_2),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-2", "Sharing model...")
        )
        step_2_back.click(
            fn=create_nav_generator(step_2, step_1),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-1", "Returning...")
        )
        step_2_next.click(
            fn=create_nav_generator(step_2, step_3),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-3", "Loading investigation findings...")
        )
        step_3_back.click(
            fn=create_nav_generator(step_3, step_2),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-2", "Going back...")
        )
        step_3_next.click(
            fn=create_nav_generator(step_3, step_4_eu),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4-eu", "Seeing European context...")
        )
        step_4_eu_back.click(
            fn=create_nav_generator(step_4_eu, step_3),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-3", "Reviewing investigation...")
        )
        step_4_eu_next.click(
            fn=create_nav_generator(step_4_eu, step_4),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4", "Key lesson...")
        )
        step_4_back.click(
            fn=create_nav_generator(step_4, step_4_eu),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4-eu", "European context...")
        )
        step_4_next.click(
            fn=create_nav_generator(step_4, step_5),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-5", "Exploring solutions...")
        )
        back_to_lesson_btn.click(
            fn=create_nav_generator(step_5, step_4),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4", "Reviewing key lesson...")
        )

        # Session-based authentication on page load
        def handle_session_auth(request: "gr.Request"):
            success, username, token = _try_session_based_auth(request)
            if success and username:
                user_stats = _get_user_stats_from_leaderboard(username, token)
                if user_stats["best_score"] is not None:
                    best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
                    rank_text = f"#{user_stats['rank']}" if user_stats['rank'] else "N/A"
                    team_text = user_stats['team_name'] if user_stats['team_name'] else "N/A"
                    celebration_html = f"""
                    <div class='slide-shell slide-shell--primary'>
                        <div style='text-align:center;'>
                            <h2 class='slide-shell__title'>🏆 Great Work, Engineer! 🏆</h2>
                            <p class='slide-shell__subtitle'>Here's your performance summary.</p>
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
                else:
                    celebration_html = """
                    <div class='slide-shell slide-shell--primary'>
                        <div style='text-align:center;'>
                            <h2 class='slide-shell__title'>🚀 You're Signed In!</h2>
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
                return {stats_display: gr.update(value=celebration_html)}
            else:
                return {stats_display: gr.update()}  # keep initial auth-required message

        demo.load(
            fn=handle_session_auth,
            inputs=None,
            outputs=[stats_display]
        )

    return demo


def launch_ethical_revelation_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_ethical_revelation_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)








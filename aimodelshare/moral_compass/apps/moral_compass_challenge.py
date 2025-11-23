"""
The Moral Compass Challenge - Gradio application for the Justice & Equity Challenge.

This app teaches:
1. The paradigm shift from pure accuracy to ethics-focused scoring
2. Introduction of the Moral Compass Score
3. Team-based collaborative learning
4. The balance between technical performance and ethical understanding

Structure:
- Factory function `create_moral_compass_challenge_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_moral_compass_challenge_app()` launches it inline (for notebooks)
"""

import random
import gradio as gr

TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]

def _try_session_based_auth(request):
    """
    Attempt to authenticate user via session token from URL parameters.

    Args:
        request: Gradio request object containing query parameters

    Returns:
        dict: {
            "success": bool,
            "username": str or None,
            "token": str or None,
            "team_name": str or None
        }
    """
    import random

    session_id = request.query_params.get("sessionid") if request else None
    if not session_id:
        return {"success": False, "username": None, "token": None, "team_name": None}

    try:
        from aimodelshare.aws import get_token_from_session, _get_username_from_token

        token = get_token_from_session(session_id)
        if not token:
            return {"success": False, "username": None, "token": None, "team_name": None}

        username = _get_username_from_token(token)
        if not username:
            return {"success": False, "username": None, "token": None, "team_name": None}

        # Assign team name based on leaderboard (or random)
        try:
            from aimodelshare.playground import Competition
            import pandas as pd

            playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
            playground = Competition(playground_id)
            leaderboard_df = playground.get_leaderboard()
            team_name = None
            if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
                user_submissions = leaderboard_df[leaderboard_df["username"] == username]
                if not user_submissions.empty:
                    if "timestamp" in user_submissions.columns:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(
                            user_submissions["timestamp"], errors='coerce'
                        )
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                    existing_team = user_submissions.iloc[0]["Team"]
                    if pd.notna(existing_team) and existing_team and str(existing_team).strip():
                        team_name = str(existing_team).strip()
            if not team_name:
                team_name = random.choice(TEAM_NAMES)
        except Exception:
            team_name = random.choice(TEAM_NAMES)
        return {"success": True, "username": username, "token": token, "team_name": team_name}

    except Exception as e:
        print(f"Session-based authentication failed: {e}")
        return {"success": False, "username": None, "token": None, "team_name": None}


def _get_user_stats_from_leaderboard(username, team_name):
    """
    Fetch the user's statistics from the model building game leaderboard.

    Args:
        username (str): authenticated user's username
        team_name (str): user's assigned team name

    Returns:
        dict: Dictionary containing user stats
    """
    try:
        from aimodelshare.playground import Competition
        import pandas as pd

        if not username:
            return {
                "username": None,
                "best_score": None,
                "rank": None,
                "team_name": None,
                "team_rank": None,
                "is_signed_in": False
            }

        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        leaderboard_df = playground.get_leaderboard()

        if leaderboard_df is None or leaderboard_df.empty:
            return {
                "username": username,
                "best_score": None,
                "rank": None,
                "team_name": team_name,
                "team_rank": None,
                "is_signed_in": True
            }

        # Get user's best score and rank
        best_score = None
        rank = None
        team_rank = None

        if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
            # Get best score
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
                            user_submissions = user_submissions.sort_values(
                                "timestamp", ascending=False
                            )
                        except Exception:
                            pass
                    team_name = user_submissions.iloc[0]["Team"]

            # Individual rank
            user_bests = leaderboard_df.groupby("username")["accuracy"].max()
            individual_summary_df = user_bests.reset_index()
            individual_summary_df.columns = ["Engineer", "Best_Score"]
            individual_summary_df = (
                individual_summary_df.sort_values("Best_Score", ascending=False)
                .reset_index(drop=True)
            )
            individual_summary_df.index = individual_summary_df.index + 1

            my_rank_row = individual_summary_df[
                individual_summary_df["Engineer"] == username
            ]
            if not my_rank_row.empty:
                rank = my_rank_row.index[0]

            # Team rank
            if "Team" in leaderboard_df.columns and team_name:
                team_summary_df = (
                    leaderboard_df.groupby("Team")["accuracy"]
                    .agg(Best_Score="max")
                    .reset_index()
                    .sort_values("Best_Score", ascending=False)
                    .reset_index(drop=True)
                )
                team_summary_df.index = team_summary_df.index + 1

                my_team_row = team_summary_df[team_summary_df["Team"] == team_name]
                if not my_team_row.empty:
                    team_rank = my_team_row.index[0]

        return {
            "username": username,
            "best_score": best_score,
            "rank": rank,
            "team_name": team_name,
            "team_rank": team_rank,
            "is_signed_in": True,
        }

    except Exception as e:
        print(f"Error fetching user stats: {e}")
        return {
            "username": username,
            "best_score": None,
            "rank": None,
            "team_name": team_name,
            "team_rank": None,
            "is_signed_in": bool(username),
        }


def create_moral_compass_challenge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the Moral Compass Challenge Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the moral compass challenge app. Install with `pip install gradio`."
        ) from e

    def build_standing_html(user_stats):
        if user_stats["is_signed_in"] and user_stats["best_score"] is not None:
            best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
            rank_text = f"#{user_stats['rank']}" if user_stats["rank"] else "N/A"
            team_text = user_stats["team_name"] if user_stats["team_name"] else "N/A"
            team_rank_text = (
                f"#{user_stats['team_rank']}" if user_stats["team_rank"] else "N/A"
            )
            return f"""
            <div class='slide-shell slide-shell--info'>
                <h3 class='slide-shell__title'>
                    You've Built an Accurate Model
                </h3>
                <div class='content-box'>
                    <p class='slide-shell__subtitle'>
                        Through experimentation and iteration, you've achieved impressive results:
                    </p>
                    <div class='stat-grid'>
                        <div class='stat-card stat-card--success'>
                            <p class='stat-card__label'>Your Best Accuracy</p>
                            <p class='stat-card__value'>{best_score_pct}</p>
                        </div>
                        <div class='stat-card stat-card--accent'>
                            <p class='stat-card__label'>Your Individual Rank</p>
                            <p class='stat-card__value'>{rank_text}</p>
                        </div>
                    </div>
                    <div class='team-card'>
                        <p class='team-card__label'>Your Team</p>
                        <p class='team-card__value'>🛡️ {team_text}</p>
                        <p class='team-card__rank'>Team Rank: {team_rank_text}</p>
                    </div>
                    <ul class='bullet-list'>
                        <li>✅ Mastered the model-building process</li>
                        <li>✅ Climbed the accuracy leaderboard</li>
                        <li>✅ Competed with fellow engineers</li>
                        <li>✅ Earned promotions and unlocked tools</li>
                    </ul>
                    <p class='slide-shell__subtitle' style='font-weight:600;'>
                        🏆 Congratulations on your technical achievement!
                    </p>
                </div>
                <div class='content-box content-box--emphasis'>
                    <p class='content-box__heading'>
                        But now you know the full story...
                    </p>
                    <p>
                        High accuracy isn't enough. Real-world AI systems must also be
                        <strong>fair, equitable, and <span class='emph-harm'>minimize harm</span></strong>
                        across all groups of people.
                    </p>
                </div>
            </div>
            """
        elif user_stats["is_signed_in"]:
            return """
            <div class='slide-shell slide-shell--info'>
                <h3 class='slide-shell__title'>
                    Ready to Begin Your Journey
                </h3>
                <div class='content-box'>
                    <p class='slide-shell__subtitle'>
                        You've learned about the model-building process and are ready to take on the challenge:
                    </p>
                    <ul class='bullet-list'>
                        <li>✅ Understood the AI model-building process</li>
                        <li>✅ Learned about accuracy and performance</li>
                        <li>✅ Discovered real-world bias in AI systems</li>
                    </ul>
                    <p class='slide-shell__subtitle' style='font-weight:600;'>
                        🎯 Ready to learn about ethical AI!
                    </p>
                </div>
                <div class='content-box content-box--emphasis'>
                    <p class='content-box__heading'>
                        Now you know the full story...
                    </p>
                    <p>
                        High accuracy isn't enough. Real-world AI systems must also be
                        <strong>fair, equitable, and <span class='emph-harm'>minimize harm</span></strong>
                        across all groups of people.
                    </p>
                </div>
            </div>
            """
        else:
            return """
            <div class='slide-shell slide-shell--warning' style='text-align:center;'>
                <h2 class='slide-shell__title'>
                    🔒 Session Required
                </h2>
                <p class='slide-shell__subtitle'>
                    Please access this app via a valid session URL.<br>
                    No manual sign-in is offered.<br>
                    You can still continue through this lesson to learn!
                </p>
            </div>
            """

    def build_step2_html(user_stats):
        if user_stats["is_signed_in"] and user_stats["best_score"] is not None:
            gauge_value = int(user_stats["best_score"] * 100)
        else:
            gauge_value = 75
        gauge_fill_percent = f"{gauge_value}%"
        gauge_display = str(gauge_value)
        return f"""
            <div class='slide-shell slide-shell--warning'>
                <h3 class='slide-shell__title'>
                    We Need a Higher Standard
                </h3>
                <p class='slide-shell__subtitle'>
                    While your model is accurate, a higher standard is needed to prevent
                    <span class='emph-harm'>real-world harm</span>. To incentivize this new focus,
                    we're introducing a new score.
                </p>
                <div class='content-box'>
                    <h4 class='content-box__heading'>Watch Your Score</h4>
                    <div class='score-gauge-container'>
                        <div class='score-gauge' style='--fill-percent: {gauge_fill_percent};'>
                            <div class='score-gauge-inner'>
                                <div class='score-gauge-value'>{gauge_display}</div>
                                <div class='score-gauge-label'>Accuracy Score</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class='content-box content-box--emphasis'>
                    <p class='content-box__heading'>
                        This score measures only <strong>one dimension</strong> of success.
                    </p>
                    <p>
                        It's time to add a second, equally important dimension:
                        <strong class='emph-fairness'>Ethics</strong>.
                    </p>
                </div>
            </div>
        """

    def build_step6_html(user_stats):
        if user_stats["is_signed_in"] and user_stats["rank"]:
            rank_text = f"#{user_stats['rank']}"
            position_message = f"""
                        <p class='slide-teaching-body' style='text-align:left;'>
                            You were previously <strong>ranked {rank_text}</strong> on the accuracy leaderboard.
                            But now, with the introduction of the Moral Compass Score, your position has changed:
                        </p>
            """
        else:
            position_message = """
                        <p class='slide-teaching-body' style='text-align:left;'>
                            With the introduction of the Moral Compass Score, everyone starts fresh.
                            Your previous work on accuracy is valuable, but now we need to add ethics:
                        </p>
            """

        return f"""
            <div class='slide-shell slide-shell--info'>
                <h3 class='slide-shell__title'>
                    📍 Your Current Position
                </h3>
                <div class='content-box'>
                    {position_message}
                    <div class='content-box content-box--danger'>
                        <p class='content-box__heading'>
                            Current Moral Compass Rank: <span class='emph-risk'>Starting Fresh</span>
                        </p>
                        <p>
                            (Because your Moral Compass Score = <span class='emph-harm'>0</span>)
                        </p>
                    </div>
                </div>
                <div class='content-box content-box--success'>
                    <h4 class='content-box__heading'>
                        🛤️ The Path Forward
                    </h4>
                    <p class='slide-teaching-body'>
                        The next section will provide expert guidance from the <strong>UdG's
                        OEIAC AI Ethics Center</strong>. You'll learn to:
                    </p>
                    <ul class='bullet-list'>
                        <li>🔍 <strong>Detect and measure bias</strong> in your AI models</li>
                        <li>⚖️ <strong>Apply fairness metrics</strong> to evaluate equity</li>
                        <li>🔧 <strong>Redesign your system</strong> to <span class='emph-harm'>minimize harm</span></li>
                        <li>📊 <strong>Balance accuracy with fairness</strong> for better outcomes</li>
                    </ul>
                </div>
                <div class='content-box content-box--emphasis'>
                    <p class='content-box__heading'>
                        🏆 Upon Completion
                    </p>
                    <p>
                        By completing the full learning module and improving your Moral Compass Score,
                        you will earn your <strong class='emph-fairness'>AI Ethical Risk Training Certificate</strong>.
                    </p>
                    <p class='note-text'>
                        (Certificate details and delivery will be covered in upcoming sections)
                    </p>
                </div>
                <h1 style='margin:32px 0 16px 0; font-size: 3rem; text-align:center;'>👇 SCROLL DOWN 👇</h1>
                <p style='font-size:1.2rem; text-align:center;'>
                    Continue to the expert guidance section to begin improving your Moral Compass Score.
                </p>
            </div>
        """

    css = """ ... [CSS unchanged for brevity] ... """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        gr.Markdown("<h1 style='text-align:center;'>⚖️ The Ethical Challenge: The Moral Compass</h1>")

        with gr.State() as app_state:
            # Step 1: A Higher Standard
            with gr.Column(visible=True, elem_id="step-1") as step_1:
                stats_display = gr.HTML(value="")  # We'll dynamically set this later
                step_1_next = gr.Button(
                    "Introduce the New Standard ▶️", variant="primary", size="lg"
                )

            # Step 2: The Dramatic Reset
            with gr.Column(visible=False, elem_id="step-2") as step_2:
                step_2_html_comp = gr.HTML(value="")
                with gr.Row():
                    step_2_back = gr.Button("◀️ Back", size="lg")
                    step_2_next = gr.Button("Reset and Transform ▶️", variant="primary", size="lg")

            # Step 3: The Reset Animation
            with gr.Column(visible=False, elem_id="step-3") as step_3:
                gr.HTML(""" ... existing reset gauge HTML ... """)
                with gr.Row():
                    step_3_back = gr.Button("◀️ Back", size="lg")
                    step_3_next = gr.Button("Introduce the Moral Compass ▶️", variant="primary", size="lg")

            # Step 4: The Moral Compass Score
            with gr.Column(visible=False, elem_id="step-4") as step_4:
                gr.Markdown("<h2 style='text-align:center;'>🧭 The Moral Compass Score</h2>")
                gr.HTML(""" ... existing MC Score HTML ... """)
                with gr.Row():
                    step_4_back = gr.Button("◀️ Back", size="lg")
                    step_4_next = gr.Button("See the Challenge Ahead ▶️", variant="primary", size="lg")

            # Step 6: The Challenge Ahead (directly after Step 4)
            with gr.Column(visible=False, elem_id="step-6") as step_6:
                step_6_html_comp = gr.HTML(value="")
                with gr.Row():
                    step_6_back = gr.Button("◀️ Back", size="lg")

            all_steps = [step_1, step_2, step_3, step_4, step_6]

            # Navigation logic unchanged

            # Session-based authentication on page load
            def handle_session_auth(request: "gr.Request", s: dict):
                auth_result = _try_session_based_auth(request)
                if auth_result["success"]:
                    s['username'] = auth_result["username"]
                    s['AWS_TOKEN'] = auth_result["token"]
                    s['TEAM_NAME'] = auth_result["team_name"]
                    s['is_signed_in'] = True
                    user_stats = _get_user_stats_from_leaderboard(s['username'], s['TEAM_NAME'])

                    standing_html = build_standing_html(user_stats)
                    step2_html = build_step2_html(user_stats)
                    step6_html = build_step6_html(user_stats)

                    return {
                        stats_display: gr.update(value=standing_html),
                        step_2_html_comp: gr.update(value=step2_html),
                        step_6_html_comp: gr.update(value=step6_html)
                    }
                else:
                    info_html = build_standing_html({"is_signed_in": False})
                    return {
                        stats_display: gr.update(value=info_html),
                        step_2_html_comp: gr.update(value=build_step2_html({"is_signed_in": False, "best_score": None})),
                        step_6_html_comp: gr.update(value=build_step6_html({"is_signed_in": False}))
                    }

            demo.load(
                fn=handle_session_auth,
                inputs=[app_state],
                outputs=[stats_display, step_2_html_comp, step_6_html_comp]
            )

            # Navigation logic unchanged (must be present)

    return demo

def launch_moral_compass_challenge_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    """Convenience wrapper to create and launch the moral compass challenge app inline."""
    import gradio as gr
    demo = create_moral_compass_challenge_app()
    import os
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)


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
import os
import random

# Team names for assignment (still used in stats/login messaging)
TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]


def _get_user_stats_from_leaderboard():
    """
    Fetch the user's statistics from the model building game leaderboard.

    Returns:
        dict: Dictionary containing:
            - username: str or None
            - best_score: float or None
            - rank: int or None
            - team_name: str or None
            - team_rank: int or None
            - is_signed_in: bool
    """
    try:
        # Import here to avoid circular dependencies
        from aimodelshare.playground import Competition
        import pandas as pd

        # Check if user is signed in
        username = os.environ.get("username")
        if not username:
            return {
                "username": None,
                "best_score": None,
                "rank": None,
                "team_name": None,
                "team_rank": None,
                "is_signed_in": False
            }

        # Try to connect to playground
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        leaderboard_df = playground.get_leaderboard()

        if leaderboard_df is None or leaderboard_df.empty:
            return {
                "username": username,
                "best_score": None,
                "rank": None,
                "team_name": os.environ.get("TEAM_NAME"),
                "team_rank": None,
                "is_signed_in": True
            }

        # Get user's best score and rank
        best_score = None
        rank = None
        team_name = os.environ.get("TEAM_NAME")
        team_rank = None

        if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
            # Get best score
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                best_score = user_submissions["accuracy"].max()

                # Get team name from most recent submission
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

            # Calculate individual rank
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

            # Calculate team rank
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
            "username": os.environ.get("username"),
            "best_score": None,
            "rank": None,
            "team_name": os.environ.get("TEAM_NAME"),
            "team_rank": None,
            "is_signed_in": bool(os.environ.get("username")),
        }


def _perform_inline_login(username_input, password_input):
    """
    Perform inline authentication and set credentials in environment.

    Returns tuple of (success_bool, message_html, user_stats_dict)
    """

    def _normalize_team_name(team_name):
        """Normalize team name to match standard format."""
        if not team_name or not str(team_name).strip():
            return random.choice(TEAM_NAMES)
        team_str = str(team_name).strip()
        for standard_name in TEAM_NAMES:
            if team_str.lower() == standard_name.lower():
                return standard_name
        return team_str

    def _get_or_assign_team(username):
        """Get existing team or assign new one."""
        try:
            from aimodelshare.playground import Competition
            import pandas as pd

            playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
            playground = Competition(playground_id)
            leaderboard_df = playground.get_leaderboard()

            if (
                leaderboard_df is not None
                and not leaderboard_df.empty
                and "Team" in leaderboard_df.columns
            ):
                user_submissions = leaderboard_df[
                    leaderboard_df["username"] == username
                ]

                if not user_submissions.empty:
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

                    existing_team = user_submissions.iloc[0]["Team"]
                    if (
                        pd.notna(existing_team)
                        and existing_team
                        and str(existing_team).strip()
                    ):
                        return _normalize_team_name(existing_team), False

            new_team = _normalize_team_name(random.choice(TEAM_NAMES))
            return new_team, True

        except Exception:
            new_team = _normalize_team_name(random.choice(TEAM_NAMES))
            return new_team, True

    # Validate inputs
    if not username_input or not username_input.strip():
        error_html = """
        <div class='alert alert--error'>
            <p class='alert__title'>⚠️ Username is required</p>
        </div>
        """
        return False, error_html, _get_user_stats_from_leaderboard()

    if not password_input or not password_input.strip():
        error_html = """
        <div class='alert alert--error'>
            <p class='alert__title'>⚠️ Password is required</p>
        </div>
        """
        return False, error_html, _get_user_stats_from_leaderboard()

    # Set credentials in environment
    os.environ["username"] = username_input.strip()
    os.environ["password"] = password_input.strip()

    # Attempt to get AWS token
    try:
        from aimodelshare.aws import get_aws_token

        token = get_aws_token()
        os.environ["AWS_TOKEN"] = token

        # Get or assign team for this user
        team_name, is_new_team = _get_or_assign_team(username_input.strip())
        os.environ["TEAM_NAME"] = team_name

        # Get updated stats
        user_stats = _get_user_stats_from_leaderboard()

        # Check if user has submitted any models
        if user_stats["best_score"] is None:
            # User signed in but hasn't submitted models yet
            warning_html = f"""
            <div class='alert alert--warning'>
                <p class='alert__title'>✓ Signed in successfully!</p>
                <p class='alert__body'>
                    Team: <b>{team_name}</b>
                </p>
                <p class='alert__subtitle'>
                    ⚠️ You haven't submitted any models yet!
                </p>
                <p class='alert__body'>
                    Please go back to the <strong>Model Building Game</strong> activity and submit at least one model
                    to see your personalized stats here.
                </p>
            </div>
            """
            return True, warning_html, user_stats

        # Success with submissions
        if is_new_team:
            team_message = f"You have been assigned to: <b>{team_name}</b> 🎉"
        else:
            team_message = f"Welcome back to team: <b>{team_name}</b> ✅"

        success_html = f"""
        <div class='alert alert--success'>
            <p class='alert__title'>✓ Signed in successfully!</p>
            <p class='alert__body'>
                {team_message}
            </p>
            <p class='alert__body'>
                Your personalized stats are now displayed above!
            </p>
        </div>
        """
        return True, success_html, user_stats

    except Exception:
        # Authentication failed
        error_html = """
        <div class='alert alert--error'>
            <p class='alert__title'>⚠️ Authentication failed</p>
            <p class='alert__body'>
                Could not verify your credentials. Please check your username and password.
            </p>
            <p class='alert__body'>
                <strong>New user?</strong> Create a free account at
                <a href='https://www.modelshare.ai/login' target='_blank' class='alert__link'>modelshare.ai/login</a>
            </p>
        </div>
        """
        return False, error_html, _get_user_stats_from_leaderboard()


def create_moral_compass_challenge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the Moral Compass Challenge Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the moral compass challenge app. Install with `pip install gradio`."
        ) from e

    # ---------- HTML builder helpers (always use current stats) ----------

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
                    📊 Sign In to See Your Stats
                </h2>
                <p class='slide-shell__subtitle'>
                    To view your personalized standing with actual scores and rankings,
                    please sign in below.
                </p>
                <p class='slide-shell__subtitle'>
                    You can still continue through this lesson without signing in.
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

    # ------------------------ CSS & Blocks layout ------------------------

    css = """
    .large-text {
        font-size: 20px !important;
    }

    /* --------------------------------------------- */
    /*  Slide + content containers (theme-aware)     */
    /* --------------------------------------------- */

    .slide-shell {
        padding: 28px;
        border-radius: 16px;
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 2px solid var(--border-color-primary);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
        max-width: 900px;
        margin: 0 auto 24px auto;
        font-size: 20px;
    }

    .slide-shell--info {
        border-color: var(--color-accent);
    }

    .slide-shell--warning {
        border-color: var(--color-accent);
    }

    .slide-shell__title {
        font-size: 2rem;
        margin: 0 0 16px 0;
        text-align: center;
    }

    .slide-shell__subtitle {
        font-size: 1.1rem;
        margin-top: 8px;
        text-align: center;
        color: var(--secondary-text-color);
        line-height: 1.7;
    }

    .content-box {
        background-color: var(--block-background-fill);
        border-radius: 12px;
        border: 1px solid var(--border-color-primary);
        padding: 24px;
        margin: 24px 0;
    }

    .content-box__heading {
        margin-top: 0;
        font-weight: 600;
        font-size: 1.2rem;
    }

    .content-box--emphasis {
        border-left: 6px solid var(--color-accent);
    }

    .content-box--danger {
        border-left: 6px solid #dc2626;
    }

    .content-box--success {
        border-left: 6px solid #16a34a;
    }

    .bullet-list {
        list-style: none;
        padding-left: 0;
        margin: 16px auto 0 auto;
        max-width: 600px;
        font-size: 1.05rem;
    }

    .bullet-list li {
        padding: 6px 0;
    }

    .note-text {
        font-size: 0.95rem;
        margin-top: 12px;
        font-style: italic;
        color: var(--secondary-text-color);
    }

    /* Stats cards */
    .stat-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin: 24px auto;
        max-width: 600px;
    }

    .stat-card {
        text-align: center;
        padding: 16px;
        border-radius: 10px;
        border: 1px solid var(--border-color-primary);
        background-color: var(--block-background-fill);
    }

    .stat-card__label {
        margin: 0;
        font-size: 0.9rem;
        color: var(--secondary-text-color);
    }

    .stat-card__value {
        margin: 8px 0 0 0;
        font-size: 2.2rem;
        font-weight: 800;
    }

    .stat-card--success .stat-card__value {
        color: #16a34a;
    }

    .stat-card--accent .stat-card__value {
        color: var(--color-accent);
    }

    .team-card {
        text-align: center;
        padding: 16px;
        border-radius: 10px;
        border: 1px solid var(--border-color-primary);
        background-color: var(--block-background-fill);
        margin-top: 8px;
    }

    .team-card__label {
        margin: 0;
        font-size: 0.9rem;
        color: var(--secondary-text-color);
    }

    .team-card__value {
        margin: 8px 0 4px 0;
        font-size: 1.5rem;
        font-weight: 700;
    }

    .team-card__rank {
        margin: 0;
        font-size: 1rem;
        color: var(--secondary-text-color);
    }

    /* Larger teaching text */
    .slide-teaching-body {
        font-size: 1.1rem;
        line-height: 1.8;
        margin-top: 1rem;
    }

    /* Ethical-risk emphasis utilities */
    .emph-harm {
        color: #b91c1c;
        font-weight: 700;
    }

    .emph-risk {
        color: #b45309;
        font-weight: 600;
    }

    .emph-fairness {
        color: var(--color-accent);
        font-weight: 600;
    }

    @media (prefers-color-scheme: dark) {
        .emph-harm {
            color: #fca5a5;
        }
        .emph-risk {
            color: #fed7aa;
        }
    }

    /* Alerts used by inline login + feedback */
    .alert {
        padding: 16px;
        border-radius: 8px;
        border-left: 4px solid var(--border-color-primary);
        margin-top: 12px;
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        font-size: 0.95rem;
    }
    .alert__title {
        margin: 0;
        font-weight: 600;
        font-size: 1.05rem;
    }
    .alert__subtitle {
        margin: 8px 0 0 0;
        font-weight: 600;
    }
    .alert__body {
        margin: 8px 0 0 0;
    }
    .alert__link {
        text-decoration: underline;
    }

    .alert--error {
        border-left-color: #dc2626;
    }
    .alert--warning {
        border-left-color: #f59e0b;
    }
    .alert--success {
        border-left-color: #16a34a;
    }

    /* Gauge/Meter styles (theme-aware) */
    .score-gauge-container {
        position: relative;
        width: 260px;
        height: 260px;
        margin: 24px auto;
    }

    .score-gauge {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: conic-gradient(
            from 180deg,
            #16a34a 0%,
            #16a34a var(--fill-percent, 0%),
            var(--border-color-primary) var(--fill-percent, 0%),
            var(--border-color-primary) 100%
        );
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
    }

    .score-gauge-inner {
        width: 70%;
        height: 70%;
        border-radius: 50%;
        background-color: var(--block-background-fill);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 2;
        border: 1px solid var(--border-color-primary);
    }

    .score-gauge-value {
        font-size: 3.2rem;
        font-weight: 800;
        color: var(--body-text-color);
        line-height: 1;
    }

    .score-gauge-label {
        font-size: 0.95rem;
        color: var(--secondary-text-color);
        margin-top: 8px;
    }

    /* Animation for gauge drop (Step 3) */
    @keyframes gauge-drop {
        0% {
            background: conic-gradient(
                from 180deg,
                #16a34a 0%,
                #16a34a 75%,
                var(--border-color-primary) 75%,
                var(--border-color-primary) 100%
            );
        }
        100% {
            background: conic-gradient(
                from 180deg,
                #dc2626 0%,
                #dc2626 0%,
                var(--border-color-primary) 0%,
                var(--border-color-primary) 100%
            );
        }
    }

    .gauge-dropped {
        animation: gauge-drop 2s ease-out forwards;
    }

    /* Formula box styles */
    .formula-box {
        background-color: var(--block-background-fill);
        border: 3px solid var(--color-accent);
        border-radius: 16px;
        padding: 24px;
        margin: 24px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .formula-math {
        font-family: "Courier New", monospace;
        font-size: 1.2rem;
        font-weight: 600;
        background-color: var(--body-background-fill);
        padding: 18px;
        border-radius: 8px;
        text-align: center;
        margin: 16px 0;
        line-height: 1.9;
    }

    /* Navigation Loading Overlay Styles (opaque, theme-aware) */
    #nav-loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: var(--body-background-fill);
        z-index: 9999;
        display: none;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.25s ease;
    }

    .nav-spinner {
        width: 50px;
        height: 50px;
        border: 5px solid var(--block-background-fill);
        border-top: 5px solid var(--color-accent);
        border-radius: 50%;
        animation: nav-spin 1s linear infinite;
        margin-bottom: 20px;
    }

    @keyframes nav-spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    #nav-loading-text {
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--body-text-color);
    }

    /* Dark-mode fine-tuning */
    @media (prefers-color-scheme: dark) {
        .slide-shell,
        .content-box,
        .alert,
        .formula-box {
            box-shadow: none;
        }

        .score-gauge {
            box-shadow: none;
        }
    }
    """

    import gradio as gr

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # Persistent top anchor for scroll-to-top navigation
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")

        # Navigation loading overlay with spinner and dynamic message
        gr.HTML(
            """
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """
        )

        gr.Markdown(
            "<h1 style='text-align:center;'>⚖️ The Ethical Challenge: The Moral Compass</h1>"
        )

        # --- Loading screen ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 class='large-text' style='color: var(--secondary-text-color);'>⏳ Loading...</h2>
                </div>
                """
            )

        # Step 1: A Higher Standard
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            # Get user stats at app load (may be unauthenticated)
            user_stats = _get_user_stats_from_leaderboard()

            gr.Markdown("<h2 style='text-align:center;'>📊 Your Current Standing</h2>")

            stats_display = gr.HTML(build_standing_html(user_stats))

            # Login form (only shown if not signed in)
            with gr.Column(visible=not user_stats["is_signed_in"]) as login_form:
                gr.Markdown("### Sign In")
                login_username = gr.Textbox(
                    label="Username",
                    placeholder="Enter your modelshare.ai username",
                )
                login_password = gr.Textbox(
                    label="Password",
                    type="password",
                    placeholder="Enter your password",
                )
                login_submit = gr.Button("Sign In", variant="primary")
                login_feedback = gr.HTML(value="", visible=False)

            step_1_next = gr.Button(
                "Introduce the New Standard ▶️", variant="primary", size="lg"
            )

        # Step 2: The Dramatic Reset
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            gr.Markdown("<h2 style='text-align:center;'>⚠️ The Paradigm Shift</h2>")
            step_2_html_comp = gr.HTML(build_step2_html(user_stats))

            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button(
                    "Reset and Transform ▶️", variant="primary", size="lg"
                )

        # Step 3: The Reset Animation
        with gr.Column(visible=False, elem_id="step-3") as step_3:

            gr.HTML(
                """
                <div class='slide-shell slide-shell--warning'>
                    <div style='text-align:center;'>
                        <h3 class='slide-shell__title'>
                            Your Accuracy Score Is Being Reset
                        </h3>

                        <div class='score-gauge-container'>
                            <div class='score-gauge gauge-dropped' style='--fill-percent: 0%;'>
                                <div class='score-gauge-inner'>
                                    <div class='score-gauge-value' style='color:#dc2626;'>0</div>
                                    <div class='score-gauge-label'>Score Reset</div>
                                </div>
                            </div>
                        </div>

                        <div class='content-box content-box--danger'>
                            <h4 class='content-box__heading'>
                                ⚠️ Why This Reset?
                            </h4>
                            <p class='slide-teaching-body' style='text-align:left;'>
                                We reset your score to emphasize a critical truth: your previous success
                                was measured by only <strong>one dimension</strong> — prediction accuracy. So far, you
                                <strong>have not demonstrated</strong> that you know how to make your AI system
                                <span class='emph-fairness'>safe for society</span>. You don’t yet know whether
                                the model you built is <strong class='emph-harm'>just as biased</strong> as the
                                harmful examples we studied in the previous activity. Moving forward, you’ll need
                                to excel on <strong>two fronts</strong>: technical performance <em>and</em>
                                ethical responsibility.
                            </p>
                        </div>

                        <div class='content-box content-box--success'>
                            <h4 class='content-box__heading'>
                                ✅ Don't Worry!
                            </h4>
                            <p class='slide-teaching-body'>
                                As you make your AI more ethical through the upcoming lessons and challenges,
                                <strong>your score will be restored</strong>—and could climb even higher than before.
                            </p>
                        </div>
                    </div>
                </div>
                """
            )

            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button(
                    "Introduce the Moral Compass ▶️", variant="primary", size="lg"
                )

        # Step 4: The Moral Compass Score
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            gr.Markdown("<h2 style='text-align:center;'>🧭 The Moral Compass Score</h2>")
            gr.HTML(
                """
                <div class='slide-shell slide-shell--info'>
                    <h3 class='slide-shell__title'>
                        A New Way to Win
                    </h3>

                    <p class='slide-shell__subtitle'>
                        Your new goal is to climb the leaderboard by increasing your
                        <strong>Moral Compass Score</strong>.
                    </p>

                    <div class='formula-box'>
                        <h4 class='content-box__heading' style='text-align:center;'>
                            📐 The Scoring Formula
                        </h4>

                        <div class='formula-math'>
                            <strong>Moral Compass Score</strong> =<br><br>
                            [ Current Model Accuracy ] × [ Ethical Progress % ]
                        </div>

                        <div class='content-box' style='margin-top:20px;'>
                            <p class='content-box__heading'>Where:</p>
                            <ul class='bullet-list'>
                                <li>
                                    <strong>Current Model Accuracy:</strong> Your technical performance
                                    (can be improved through model refinement)
                                </li>
                                <li>
                                    <strong>Ethical Progress %:</strong> Percentage of:
                                    <ul class='bullet-list' style='margin-top:8px;'>
                                        <li>✅ Ethical learning tasks completed</li>
                                        <li>✅ Check-in questions answered correctly</li>
                                    </ul>
                                </li>
                            </ul>
                        </div>
                    </div>

                    <div class='content-box content-box--success'>
                        <h4 class='content-box__heading'>
                            💡 What This Means:
                        </h4>
                        <p class='slide-teaching-body'>
                            You <strong>cannot</strong> win by accuracy alone—you must also demonstrate
                            <strong class='emph-fairness'>ethical understanding</strong>. And you
                            <strong>cannot</strong> win by just completing lessons—you need a working model too.
                            <strong class='emph-risk'>Both dimensions matter</strong>.
                        </p>
                    </div>
                </div>
                """
            )

            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button(
                    "See the Challenge Ahead ▶️", variant="primary", size="lg"
                )

        # Step 6: The Challenge Ahead (directly after Step 4)
        with gr.Column(visible=False, elem_id="step-6") as step_6:
            gr.Markdown("<h2 style='text-align:center;'>🎯 The Challenge Ahead</h2>")
            step_6_html_comp = gr.HTML(build_step6_html(user_stats))

            with gr.Row():
                step_6_back = gr.Button("◀️ Back", size="lg")

        # ---------- LOGIN HANDLER (updates slides 1, 2, and 6) ----------

        def handle_login(username, password):
            success, message, new_stats = _perform_inline_login(username, password)

            if success:
                return {
                    stats_display: gr.update(value=build_standing_html(new_stats)),
                    login_form: gr.update(visible=False),
                    login_feedback: gr.update(value=message, visible=True),
                    step_2_html_comp: gr.update(value=build_step2_html(new_stats)),
                    step_6_html_comp: gr.update(value=build_step6_html(new_stats)),
                }
            else:
                # Failed login: keep slides as-is, just show feedback
                return {
                    stats_display: gr.update(),
                    login_form: gr.update(visible=True),
                    login_feedback: gr.update(value=message, visible=True),
                    step_2_html_comp: gr.update(),
                    step_6_html_comp: gr.update(),
                }

        login_submit.click(
            fn=handle_login,
            inputs=[login_username, login_password],
            outputs=[
                stats_display,
                login_form,
                login_feedback,
                step_2_html_comp,
                step_6_html_comp,
            ],
        )

        # ---------- NAVIGATION LOGIC ----------

        all_steps = [step_1, step_2, step_3, step_4, step_6, loading_screen]

        def create_nav_generator(current_step, next_step):
            def navigate():
                # Yield 1: Show loading, hide all
                updates = {loading_screen: gr.update(visible=True)}
                for step in all_steps:
                    if step != loading_screen:
                        updates[step] = gr.update(visible=False)
                yield updates

                # Yield 2: Show new step, hide all others
                updates = {next_step: gr.update(visible=True)}
                for step in all_steps:
                    if step != next_step:
                        updates[step] = gr.update(visible=False)
                yield updates

            return navigate

        def nav_js(target_id: str, message: str, min_show_ms: int = 1200) -> str:
            """Generate JavaScript for enhanced slide navigation with loading overlay."""
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

        # Wire navigation
        step_1_next.click(
            fn=create_nav_generator(step_1, step_2),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-2", "Introducing the new standard..."),
        )
        step_2_back.click(
            fn=create_nav_generator(step_2, step_1),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-1", "Returning..."),
        )
        step_2_next.click(
            fn=create_nav_generator(step_2, step_3),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-3", "Resetting score..."),
        )
        step_3_back.click(
            fn=create_nav_generator(step_3, step_2),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-2", "Going back..."),
        )
        step_3_next.click(
            fn=create_nav_generator(step_3, step_4),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-4", "Introducing the Moral Compass..."),
        )
        step_4_back.click(
            fn=create_nav_generator(step_4, step_3),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-3", "Reviewing the reset..."),
        )
        step_4_next.click(
            fn=create_nav_generator(step_4, step_6),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-6", "Preparing the challenge..."),
        )
        step_6_back.click(
            fn=create_nav_generator(step_6, step_4),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-4", "Reviewing scoring..."),
        )

    return demo


def launch_moral_compass_challenge_app(
    height: int = 1000, share: bool = False, debug: bool = False
) -> None:
    """Convenience wrapper to create and launch the moral compass challenge app inline."""
    import gradio as gr

    demo = create_moral_compass_challenge_app()
    demo.launch(share=share, inline=True, debug=debug, height=height)

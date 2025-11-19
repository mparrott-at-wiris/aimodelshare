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
        <div style='background:#fef2f2; padding:16px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:600;'>⚠️ Username is required</p>
        </div>
        """
        return False, error_html, _get_user_stats_from_leaderboard()

    if not password_input or not password_input.strip():
        error_html = """
        <div style='background:#fef2f2; padding:16px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:600;'>⚠️ Password is required</p>
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
            <div style='background:#fef9c3; padding:16px; border-radius:8px; border-left:4px solid #f59e0b; margin-top:12px;'>
                <p style='margin:0; color:#92400e; font-weight:600; font-size:1.1rem;'>✓ Signed in successfully!</p>
                <p style='margin:8px 0; color:#78350f; font-size:0.95rem;'>
                    Team: <b>{team_name}</b>
                </p>
                <p style='margin:8px 0 0 0; color:#92400e; font-weight:600; font-size:0.95rem;'>
                    ⚠️ You haven't submitted any models yet!
                </p>
                <p style='margin:8px 0 0 0; color:#78350f; font-size:0.95rem;'>
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
        <div style='background:#f0fdf4; padding:16px; border-radius:8px; border-left:4px solid #16a34a; margin-top:12px;'>
            <p style='margin:0; color:#15803d; font-weight:600; font-size:1.1rem;'>✓ Signed in successfully!</p>
            <p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>
                {team_message}
            </p>
            <p style='margin:8px 0 0 0; color:#166534; font-size:0.95rem;'>
                Your personalized stats are now displayed above!
            </p>
        </div>
        """
        return True, success_html, user_stats

    except Exception:
        # Authentication failed
        error_html = """
        <div style='background:#fef2f2; padding:16px; border-radius:8px; border-left:4px solid #ef4444; margin-top:12px;'>
            <p style='margin:0; color:#991b1b; font-weight:600; font-size:1.1rem;'>⚠️ Authentication failed</p>
            <p style='margin:8px 0; color:#7f1d1d; font-size:0.95rem;'>
                Could not verify your credentials. Please check your username and password.
            </p>
            <p style='margin:8px 0 0 0; color:#7f1d1d; font-size:0.95rem;'>
                <strong>New user?</strong> Create a free account at
                <a href='https://www.modelshare.ai/login' target='_blank' style='color:#dc2626; text-decoration:underline;'>modelshare.ai/login</a>
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
            <div style='font-size: 20px; background:#e0f2fe; padding:28px; border-radius:16px; border: 3px solid #0369a1;'>
                <h3 style='color:#0c4a6e; margin-top:0; text-align:center;'>
                    You've Built an Accurate Model
                </h3>

                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0;'>
                    <p style='line-height:1.8; text-align:center;'>
                        Through experimentation and iteration, you've achieved impressive results:
                    </p>

                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 24px auto; max-width: 600px;'>
                        <div style='text-align:center; padding:16px; background:#f0fdf4; border-radius:8px; border:2px solid #16a34a;'>
                            <p style='margin:0; font-size:0.9rem; color:#6b7280;'>Your Best Accuracy</p>
                            <p style='margin:8px 0 0 0; font-size:2.5rem; font-weight:800; color:#16a34a;'>{best_score_pct}</p>
                        </div>
                        <div style='text-align:center; padding:16px; background:#eff6ff; border-radius:8px; border:2px solid #2563eb;'>
                            <p style='margin:0; font-size:0.9rem; color:#6b7280;'>Your Individual Rank</p>
                            <p style='margin:8px 0 0 0; font-size:2.5rem; font-weight:800; color:#2563eb;'>{rank_text}</p>
                        </div>
                    </div>

                    <div style='text-align:center; padding:16px; background:#fef3c7; border-radius:8px; margin-top:16px; border:2px solid #f59e0b;'>
                        <p style='margin:0; font-size:0.9rem; color:#6b7280;'>Your Team</p>
                        <p style='margin:8px 0; font-size:1.5rem; font-weight:700; color:#92400e;'>🛡️ {team_text}</p>
                        <p style='margin:0; font-size:1rem; color:#78350f;'>Team Rank: {team_rank_text}</p>
                    </div>

                    <ul style='list-style:none; padding:0; text-align:left; max-width:600px; margin:24px auto 0 auto; font-size:1.1rem;'>
                        <li style='padding:8px 0;'>✅ Mastered the model-building process</li>
                        <li style='padding:8px 0;'>✅ Climbed the accuracy leaderboard</li>
                        <li style='padding:8px 0;'>✅ Competed with fellow engineers</li>
                        <li style='padding:8px 0;'>✅ Earned promotions and unlocked tools</li>
                    </ul>

                    <p style='text-align:center; font-size:1.2rem; font-weight:600; color:#16a34a; margin-top:24px;'>
                        🏆 Congratulations on your technical achievement!
                    </p>
                </div>

                <div style='background:#fef9c3; padding:20px; border-radius:8px; border-left:6px solid #f59e0b; margin-top:24px;'>
                    <p style='font-size:1.15rem; font-weight:600; margin:0; color:#92400e;'>
                        But now you know the full story...
                    </p>
                    <p style='margin:12px 0 0 0; line-height:1.6;'>
                        High accuracy isn't enough. Real-world AI systems must also be
                        <strong>fair, equitable, and minimize harm</strong> across all groups of people.
                    </p>
                </div>
            </div>
            """
        elif user_stats["is_signed_in"]:
            return """
            <div style='font-size: 20px; background:#e0f2fe; padding:28px; border-radius:16px; border: 3px solid #0369a1;'>
                <h3 style='color:#0c4a6e; margin-top:0; text-align:center;'>
                    Ready to Begin Your Journey
                </h3>

                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0;'>
                    <p style='line-height:1.8; text-align:center;'>
                        You've learned about the model-building process and are ready to take on the challenge:
                    </p>

                    <ul style='list-style:none; padding:0; text-align:left; max-width:600px; margin:20px auto; font-size:1.1rem;'>
                        <li style='padding:8px 0;'>✅ Understood the AI model-building process</li>
                        <li style='padding:8px 0;'>✅ Learned about accuracy and performance</li>
                        <li style='padding:8px 0;'>✅ Discovered real-world bias in AI systems</li>
                    </ul>

                    <p style='text-align:center; font-size:1.2rem; font-weight:600; color:#2563eb; margin-top:24px;'>
                        🎯 Ready to learn about ethical AI!
                    </p>
                </div>

                <div style='background:#fef9c3; padding:20px; border-radius:8px; border-left:6px solid #f59e0b; margin-top:24px;'>
                    <p style='font-size:1.15rem; font-weight:600; margin:0; color:#92400e;'>
                        Now you know the full story...
                    </p>
                    <p style='margin:12px 0 0 0; line-height:1.6;'>
                        High accuracy isn't enough. Real-world AI systems must also be
                        <strong>fair, equitable, and minimize harm</strong> across all groups of people.
                    </p>
                </div>
            </div>
            """
        else:
            return """
            <div style='background:#fef3c7; padding:32px; border-radius:16px; border:3px solid #f59e0b; text-align:center;'>
                <h2 style='font-size: 2rem; margin:0; color:#92400e;'>
                    📊 Sign In to See Your Stats
                </h2>
                <p style='font-size: 1.2rem; margin-top:20px; color:#78350f; line-height:1.6;'>
                    To view your personalized standing with actual scores and rankings,
                    please sign in below.
                </p>
                <p style='font-size: 1.1rem; margin-top:16px; color:#78350f;'>
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
            <div style='font-size: 20px; background:#fef2f2; padding:28px; border-radius:16px; border: 3px solid #dc2626;'>
                <h3 style='color:#991b1b; margin-top:0; text-align:center; font-size:1.8rem;'>
                    We Need a Higher Standard
                </h3>

                <p style='text-align:center; font-size:1.2rem; line-height:1.8;'>
                    While your model is accurate, a higher standard is needed to prevent
                    real-world harm. To incentivize this new focus, we're introducing a new score.
                </p>

                <div style='background:white; padding:32px; border-radius:12px; margin:32px 0; text-align:center;'>
                    <h4 style='margin-top:0; color:#374151; font-size:1.5rem;'>
                        Watch Your Score
                    </h4>

                    <div class='score-gauge-container'>
                        <div class='score-gauge' style='--fill-percent: {gauge_fill_percent};'>
                            <div class='score-gauge-inner'>
                                <div class='score-gauge-value'>{gauge_display}</div>
                                <div class='score-gauge-label'>Accuracy Score</div>
                            </div>
                        </div>
                    </div>


                </div>

                <div style='background:#fef3c7; padding:24px; border-radius:8px; text-align:center; border:2px solid #f59e0b;'>
                    <p style='font-size:1.3rem; font-weight:600; margin:0; color:#92400e;'>
                        This score measures only <strong>one dimension</strong> of success.
                    </p>
                    <p style='font-size:1.1rem; margin:12px 0 0 0; color:#78350f;'>
                        It's time to add a second, equally important dimension: <strong>Ethics</strong>
                    </p>
                </div>
            </div>
        """

    def build_step6_html(user_stats):
        if user_stats["is_signed_in"] and user_stats["rank"]:
            rank_text = f"#{user_stats['rank']}"
            position_message = f"""
                        <p style='font-size:1.2rem; line-height:1.8; text-align:left;'>
                            You were previously <strong>ranked {rank_text}</strong> on the accuracy leaderboard.
                            But now, with the introduction of the Moral Compass Score, your position has changed:
                        </p>
            """
        else:
            position_message = """
                        <p style='font-size:1.2rem; line-height:1.8; text-align:left;'>
                            With the introduction of the Moral Compass Score, everyone starts fresh.
                            Your previous work on accuracy is valuable, but now we need to add ethics:
                        </p>
            """

        return f"""
            <div style='text-align:center;'>
                <div style='font-size: 20px; background:#e0f2fe; padding:36px; border-radius:16px;
                            border: 3px solid #0369a1; max-width:900px; margin:auto;'>
                    <h3 style='color:#0c4a6e; margin-top:0; font-size:2rem;'>
                        📍 Your Current Position
                    </h3>

                    <div style='background:white; padding:28px; border-radius:12px; margin:24px 0;'>
                        {position_message}

                        <div style='background:#fef2f2; padding:24px; border-radius:8px; margin:24px 0; border:2px solid #dc2626;'>
                            <p style='font-size:1.5rem; font-weight:700; margin:0; color:#991b1b;'>
                                Current Moral Compass Rank: Starting Fresh
                            </p>
                            <p style='font-size:1.1rem; margin:12px 0 0 0; color:#7f1d1d;'>
                                (Because your Moral Compass Score = 0)
                            </p>
                        </div>
                    </div>

                    <div style='background:#f0fdf4; padding:28px; border-radius:12px; border-left:6px solid #16a34a; text-align:left;'>
                        <h4 style='margin-top:0; color:#15803d; font-size:1.4rem;'>
                            🛤️ The Path Forward
                        </h4>
                        <p style='font-size:1.1rem; line-height:1.8;'>
                            The next section will provide expert guidance from the <strong>UdG's
                            OEIAC AI Ethics Center</strong>. You'll learn to:
                        </p>
                        <ul style='font-size:1.05rem; line-height:2;'>
                            <li>🔍 <strong>Detect and measure bias</strong> in your AI models</li>
                            <li>⚖️ <strong>Apply fairness metrics</strong> to evaluate equity</li>
                            <li>🔧 <strong>Redesign your system</strong> to minimize harm</li>
                            <li>📊 <strong>Balance accuracy with fairness</strong> for better outcomes</li>
                        </ul>
                    </div>

                    <div style='background:#fef3c7; padding:24px; border-radius:12px; margin-top:24px; border:2px solid #f59e0b;'>
                        <p style='font-size:1.2rem; font-weight:600; margin:0; color:#92400e;'>
                            🏆 Upon Completion
                        </p>
                        <p style='font-size:1.05rem; margin:12px 0 0 0; line-height:1.8;'>
                            By completing the full learning module and improving your Moral Compass Score,
                            you will earn your <strong>AI Ethical Risk Training Certificate</strong>.
                        </p>
                        <p style='font-size:0.95rem; margin:12px 0 0 0; color:#78350f; font-style:italic;'>
                            (Certificate details and delivery will be covered in upcoming sections)
                        </p>
                    </div>

                    <h1 style='margin:32px 0 16px 0; font-size: 3rem;'>👇 SCROLL DOWN 👇</h1>
                    <p style='font-size:1.2rem;'>
                        Continue to the expert guidance section to begin improving your Moral Compass Score.
                    </p>
                </div>
            </div>
        """

    # ------------------------ CSS & Blocks layout ------------------------

    css = """
    /* Global forced light background overrides */
    html, body, .gradio-container {
      background:#ffffff !important;
      color:#1f2937 !important;
    }
    body.dark, html.dark, body[class*="dark"], html[class*="dark"] {
      background:#ffffff !important;
      color:#1f2937 !important;
    }
    body.dark *, html.dark *, body[class*="dark"] *, html[class*="dark"] * {
      color-scheme: light !important;
    }
    :root { color-scheme: light !important; }
    .gradio-container, .gradio-container * {
      --color-background-primary: #ffffff !important;
      --color-background-secondary: #ffffff !important;
      --color-background-tertiary: #ffffff !important;
      color-scheme: light !important;
    }
    
    .large-text {
        font-size: 20px !important;
    }

    /* Gauge/Meter styles for dramatic reset */
    .score-gauge-container {
        position: relative;
        width: 300px;
        height: 300px;
        margin: 32px auto;
    }

    .score-gauge {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: conic-gradient(
            from 180deg,
            #16a34a 0%,
            #16a34a var(--fill-percent, 0%),
            #e5e7eb var(--fill-percent, 0%),
            #e5e7eb 100%
        );
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    }

    .score-gauge-inner {
        width: 70%;
        height: 70%;
        border-radius: 50%;
        background: white;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 2;
    }

    .score-gauge-value {
        font-size: 4rem;
        font-weight: 800;
        color: #1f2937;
        line-height: 1;
    }

    .score-gauge-label {
        font-size: 1rem;
        color: #6b7280;
        margin-top: 8px;
    }

    /* Animation for gauge drop */
    @keyframes gauge-drop {
        0% {
            background: conic-gradient(
                from 180deg,
                #16a34a 0%,
                #16a34a 75%,
                #e5e7eb 75%,
                #e5e7eb 100%
            );
        }
        100% {
            background: conic-gradient(
                from 180deg,
                #dc2626 0%,
                #dc2626 0%,
                #e5e7eb 0%,
                #e5e7eb 100%
            );
        }
    }

    .gauge-dropped {
        animation: gauge-drop 2s ease-out forwards;
    }

    /* Formula box styles */
    .formula-box {
        background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
        border: 3px solid #7c3aed;
        border-radius: 16px;
        padding: 32px;
        margin: 24px 0;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.2);
    }

    .formula-math {
        font-family: 'Courier New', monospace;
        font-size: 1.3rem;
        font-weight: 600;
        background: white;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        color: #5b21b6;
        margin: 16px 0;
        line-height: 2;
    }

    /* Navigation Loading Overlay Styles */
    #nav-loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.95);
        z-index: 9999;
        display: none;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .nav-spinner {
        width: 50px;
        height: 50px;
        border: 5px solid #e5e7eb;
        border-top: 5px solid #6366f1;
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
        color: #4338ca;
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
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Loading...</h2>
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
                <div style='font-size: 20px; background:#f9fafb; padding:40px; border-radius:16px; border: 3px solid #6b7280;'>
                    <div style='text-align:center;'>
                        <h3 style='color:#1f2937; margin-top:0; font-size:2rem;'>
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

                        <div style='background:#fef2f2; padding:28px; border-radius:12px; margin:32px auto; max-width:700px; border:2px solid #dc2626;'>
                            <h4 style='margin-top:0; color:#991b1b; font-size:1.5rem;'>
                                ⚠️ Why This Reset?
                            </h4>
                            <p style='line-height:1.8; text-align:left;'>
                                We reset your score to emphasize a critical truth: your previous success
                                was measured by only <strong>one dimension</strong> — prediction accuracy. So far, you
                                <strong>have not demonstrated</strong> that you know how to make your AI system
                                safe for society. You don’t yet know whether the model you built is
                                <strong>just as biased</strong> as the harmful examples we studied in the
                                previous activity. Moving forward, you’ll need to excel on
                                <strong>two fronts</strong>: technical performance <em>and</em> ethical responsibility.
                            </p>
                        </div>

                        <div style='background:#d1fae5; padding:24px; border-radius:12px; border-left:6px solid #16a34a;'>
                            <h4 style='margin-top:0; color:#15803d; font-size:1.3rem;'>
                                ✅ Don't Worry!
                            </h4>
                            <p style='font-size:1.1rem; margin:0; line-height:1.8;'>
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
                <div style='font-size: 20px; background:linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                            padding:32px; border-radius:16px; border: 3px solid #0284c7;'>
                    <h3 style='color:#0c4a6e; margin-top:0; text-align:center; font-size:2rem;'>
                        A New Way to Win
                    </h3>

                    <p style='text-align:center; font-size:1.2rem; line-height:1.8;'>
                        Your new goal is to climb the leaderboard by increasing your
                        <strong>Moral Compass Score</strong>.
                    </p>

                    <div class='formula-box'>
                        <h4 style='margin-top:0; color:#5b21b6; text-align:center; font-size:1.5rem;'>
                            📐 The Scoring Formula
                        </h4>

                        <div class='formula-math'>
                            <strong>Moral Compass Score</strong> =<br>
                            <br>
                            [ Current Model Accuracy ] × [ Ethical Progress % ]
                        </div>

                        <div style='background:white; padding:20px; border-radius:8px; margin-top:20px;'>
                            <p style='margin:0; line-height:1.8;'><strong>Where:</strong></p>
                            <ul style='line-height:2; text-align:left;'>
                                <li>
                                    <strong>Current Model Accuracy:</strong> Your technical performance
                                    (can be improved through model refinement)
                                </li>
                                <li>
                                    <strong>Ethical Progress %:</strong> Percentage of:
                                    <ul style='margin-top:8px;'>
                                        <li>✅ Ethical learning tasks completed</li>
                                        <li>✅ Check-in questions answered correctly</li>
                                    </ul>
                                </li>
                            </ul>
                        </div>
                    </div>

                    <div style='background:#ecfdf5; padding:24px; border-radius:12px; border-left:6px solid #10b981; margin-top:24px;'>
                        <h4 style='margin-top:0; color:#047857;'>💡 What This Means:</h4>
                        <p style='margin:0; line-height:1.8;'>
                            You <strong>cannot</strong> win by accuracy alone—you must also demonstrate
                            ethical understanding. And you <strong>cannot</strong> win by just completing
                            lessons—you need a working model too. <strong>Both dimensions matter.</strong>
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

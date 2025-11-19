"""
The Ethical Revelation: Real-World Impact - Gradio application for the Justice & Equity Challenge.

This app teaches:
1. The pivot from technical accuracy to real-world ethical consequences
2. Introduction to fairness concepts through real-world case study
3. The ProPublica "Machine Bias" investigation findings
4. How high-performing models can still amplify societal harms

Structure:
- Factory function `create_ethical_revelation_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_ethical_revelation_app()` launches it inline (for notebooks)
"""
import contextlib
import os

# --- AI Model Share Imports ---
try:
    from aimodelshare.playground import Competition
except ImportError:
    raise ImportError(
        "The 'aimodelshare' library is required. Install with: pip install aimodelshare"
    )


def _get_user_stats_from_leaderboard():
    """
    Fetch the user's statistics from the model building game leaderboard.

    Returns:
        dict: Dictionary containing:
            - username: str or None
            - best_score: float or None
            - rank: int or None
            - team_name: str or None
            - is_signed_in: bool
    """
    try:
        # Import here to avoid circular dependencies / unnecessary imports for unsigned users
        from aimodelshare.playground import Competition
        from aimodelshare.aws import get_aws_token
        import pandas as pd
        import os

        # Check if user is signed in (via environment)
        username = os.environ.get("username")
        if not username:
            # User not signed in yet: just tell the UI that
            return {
                "username": None,
                "best_score": None,
                "rank": None,
                "team_name": None,
                "is_signed_in": False
            }

        # User is "signed in" (username present) – make sure we have an AWS token
        if not os.environ.get("AWS_TOKEN"):
            try:
                os.environ["AWS_TOKEN"] = get_aws_token()
            except Exception as e:
                # If we can't get a token, log it and return minimal signed-in info
                print(f"Warning: could not obtain AWS token for user stats: {e}")
                return {
                    "username": username,
                    "best_score": None,
                    "rank": None,
                    "team_name": os.environ.get("TEAM_NAME"),
                    "is_signed_in": True,
                }

        # Connect to playground and fetch leaderboard
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        leaderboard_df = playground.get_leaderboard()

        # If leaderboard is unavailable or empty, still show basic signed-in state
        if leaderboard_df is None or leaderboard_df.empty:
            return {
                "username": username,
                "best_score": None,
                "rank": None,
                "team_name": os.environ.get("TEAM_NAME"),
                "is_signed_in": True
            }

        # Compute user-specific stats
        best_score = None
        rank = None
        team_name = os.environ.get("TEAM_NAME")

        if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
            # Filter to this user's submissions
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                # Best accuracy
                best_score = user_submissions["accuracy"].max()

                # Get team name from most recent submission (if available)
                if "Team" in user_submissions.columns:
                    if "timestamp" in user_submissions.columns:
                        try:
                            user_submissions = user_submissions.copy()
                            user_submissions["timestamp"] = pd.to_datetime(
                                user_submissions["timestamp"],
                                errors="coerce"
                            )
                            user_submissions = user_submissions.sort_values(
                                "timestamp",
                                ascending=False
                            )
                        except Exception:
                            # If parsing timestamps fails, just use current ordering
                            pass
                    team_name = user_submissions.iloc[0]["Team"]

            # Calculate rank: best score per user, sorted descending
            user_bests = leaderboard_df.groupby("username")["accuracy"].max()
            individual_summary_df = user_bests.reset_index()
            individual_summary_df.columns = ["Engineer", "Best_Score"]
            individual_summary_df = individual_summary_df.sort_values(
                "Best_Score",
                ascending=False
            ).reset_index(drop=True)
            individual_summary_df.index = individual_summary_df.index + 1  # ranks start at 1

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
        # Generic fallback: don't break the app, just log and return minimal info
        import os
        print(f"Error fetching user stats: {e}")
        return {
            "username": os.environ.get("username"),
            "best_score": None,
            "rank": None,
            "team_name": os.environ.get("TEAM_NAME"),
            "is_signed_in": bool(os.environ.get("username"))
        }


def _perform_inline_login(username_input, password_input):
    """
    Perform inline authentication and set credentials in environment.

    Returns tuple of (success_bool, message_html, user_stats_dict)
    """
    import random

    # Team names for assignment
    TEAM_NAMES = [
        "The Justice League", "The Moral Champions", "The Data Detectives",
        "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
    ]

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

            if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
                user_submissions = leaderboard_df[leaderboard_df["username"] == username]

                if not user_submissions.empty:
                    if "timestamp" in user_submissions.columns:
                        try:
                            user_submissions = user_submissions.copy()
                            user_submissions["timestamp"] = pd.to_datetime(user_submissions["timestamp"], errors='coerce')
                            user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                        except:
                            pass

                    existing_team = user_submissions.iloc[0]["Team"]
                    if pd.notna(existing_team) and existing_team and str(existing_team).strip():
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

    except Exception as e:
        # Authentication failed
        error_html = f"""
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


def create_ethical_revelation_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the Ethical Revelation Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the ethical revelation app. Install with `pip install gradio`."
        ) from e

    css = """
    .large-text {
        font-size: 20px !important;
    }
    .celebration-box {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%) !important;
        border: 3px solid #f59e0b !important;
        border-radius: 16px !important;
        padding: 32px !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important;
    }
    .revelation-box {
        background: #fef2f2 !important;
        border-left: 6px solid #dc2626 !important;
        border-radius: 8px !important;
        padding: 24px !important;
        margin-top: 24px !important;
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

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # Persistent top anchor for scroll-to-top navigation
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")

        # Navigation loading overlay with spinner and dynamic message
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        gr.Markdown("<h1 style='text-align:center;'>🚀 The Ethical Revelation: Real-World Impact</h1>")

        # --- Loading screen ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )

        # Step 1: Celebration - High Performance Model
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            # Get user stats
            user_stats = _get_user_stats_from_leaderboard()

            gr.Markdown("<h2 style='text-align:center;'>🎉 Congratulations, Engineer!</h2>")

            # Build personalized content based on user stats
            if user_stats["is_signed_in"] and user_stats["best_score"] is not None:
                # Show actual user stats
                best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
                rank_text = f"#{user_stats['rank']}" if user_stats['rank'] else "N/A"
                team_text = user_stats['team_name'] if user_stats['team_name'] else "N/A"

                celebration_html = f"""
                <div style='
                    background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
                    border: 2px solid #6366f1;
                    border-radius: 16px;
                    padding: 32px;
                    box-shadow: 0 8px 20px rgba(0,0,0,0.05);
                    max-width: 800px;
                    margin: auto;
                '>
                    <div style='text-align:center;'>
                        <h2 style='font-size: 2.3rem; margin:0; color:#4338ca;'>
                            🏆 Great Work, Engineer! 🏆
                        </h2>
                        <p style='font-size: 1.3rem; margin-top:16px; color:#475569;'>
                            Here's your performance summary.
                        </p>

                        <div style='
                            background:white;
                            padding:24px;
                            border-radius:12px;
                            margin:24px auto;
                            border:1px solid #e2e8f0;
                            max-width:600px;
                        '>
                            <h3 style='margin-top:0; color:#1e293b;'>Your Stats</h3>

                            <div style='display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px;'>
                                <div style='
                                    text-align:center;
                                    padding:16px;
                                    background:#eef2ff;
                                    border-radius:8px;
                                    border:1px solid #c7d2fe;
                                '>
                                    <p style='margin:0; font-size:0.9rem; color:#64748b;'>Best Accuracy</p>
                                    <p style='margin:4px 0 0 0; font-size:1.8rem; font-weight:700; color:#4338ca;'>
                                        {best_score_pct}
                                    </p>
                                </div>

                                <div style='
                                    text-align:center;
                                    padding:16px;
                                    background:#f0fdf4;
                                    border-radius:8px;
                                    border:1px solid #bbf7d0;
                                '>
                                    <p style='margin:0; font-size:0.9rem; color:#64748b;'>Your Rank</p>
                                    <p style='margin:4px 0 0 0; font-size:1.8rem; font-weight:700; color:#15803d;'>
                                        {rank_text}
                                    </p>
                                </div>
                            </div>

                            <div style='
                                text-align:center;
                                padding:16px;
                                background:#f8fafc;
                                border-radius:8px;
                                border:1px solid #e2e8f0;
                                margin-top:16px;
                            '>
                                <p style='margin:0; font-size:0.9rem; color:#64748b;'>Team</p>
                                <p style='margin:4px 0 0 0; font-size:1.3rem; font-weight:600; color:#4338ca;'>
                                    🛡️ {team_text}
                                </p>
                            </div>
                        </div>

                        <p style='font-size: 1.2rem; margin-top:16px; color:#475569; font-weight:500;'>
                            Ready to share your model and explore its real-world impact?
                        </p>
                    </div>
                </div>
                """
            elif user_stats["is_signed_in"]:
                # Signed in but no submissions yet
                celebration_html = """
                <div style='
                    background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
                    border: 2px solid #6366f1;
                    border-radius: 16px;
                    padding: 32px;
                    box-shadow: 0 8px 20px rgba(0,0,0,0.05);
                    max-width: 800px;
                    margin: auto;
                '>
                    <div style='text-align:center;'>
                        <h2 style='font-size: 2.3rem; margin:0; color:#4338ca;'>
                            🚀 You're Signed In!
                        </h2>
                        <p style='font-size: 1.2rem; margin-top:20px; color:#475569;'>
                            You haven't submitted a model yet, but you're all set to continue learning.
                        </p>

                        <div style='
                            background:white;
                            padding:24px;
                            border-radius:12px;
                            margin:24px auto;
                            border:1px solid #e2e8f0;
                            max-width:600px;
                        '>
                            <p style='font-size:1.1rem; margin:0; color:#334155;'>
                                Once you submit a model in the Model Building Game,
                                your accuracy and ranking will appear here.
                            </p>
                        </div>

                        <p style='font-size: 1.2rem; margin-top:16px; color:#475569; font-weight:500;'>
                            Continue to the next section when you're ready.
                        </p>
                    </div>
                </div>
                """
            else:
                # Not signed in - show prompt with login form
                celebration_html = """
                <div style='
                    background: #f8fafc;
                    border: 2px solid #6366f1;
                    border-radius: 16px;
                    padding: 32px;
                    box-shadow: 0 8px 20px rgba(0,0,0,0.05);
                    max-width: 800px;
                    margin: auto;
                    text-align:center;
                '>
                    <h2 style='font-size: 2rem; margin:0; color:#4338ca;'>
                        🔐 Sign In to View Your Stats
                    </h2>
                    <p style='font-size:1.1rem; margin-top:16px; color:#475569; line-height:1.6;'>
                        Sign in to see your personalized performance summary, including your
                        score, rank, and team assignment.
                    </p>
                    <p style='font-size:1rem; margin-top:16px; color:#64748b;'>
                        You can still continue the lesson even if you skip signing in.
                    </p>
                </div>
                """

            stats_display = gr.HTML(celebration_html)

            # Login form (only shown if not signed in)
            with gr.Column(visible=not user_stats["is_signed_in"]) as login_form:
                gr.Markdown("### Sign In")
                login_username = gr.Textbox(
                    label="Username",
                    placeholder="Enter your modelshare.ai username"
                )
                login_password = gr.Textbox(
                    label="Password",
                    type="password",
                    placeholder="Enter your password"
                )
                login_submit = gr.Button("Sign In", variant="primary")
                login_feedback = gr.HTML(value="", visible=False)

                # Handle login
                def handle_login(username, password):
                    success, message, new_stats = _perform_inline_login(username, password)

                    # Rebuild celebration HTML with new stats
                    if success and new_stats["best_score"] is not None:
                        best_score_pct = f"{(new_stats['best_score'] * 100):.1f}%"
                        rank_text = f"#{new_stats['rank']}" if new_stats['rank'] else "N/A"
                        team_text = new_stats['team_name'] if new_stats['team_name'] else "N/A"

                        new_celebration_html = f"""
                        <div style='
                            background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
                            border: 2px solid #6366f1;
                            border-radius: 16px;
                            padding: 32px;
                            box-shadow: 0 8px 20px rgba(0,0,0,0.05);
                            max-width: 800px;
                            margin: auto;
                        '>
                            <div style='text-align:center;'>
                                <h2 style='font-size: 2.3rem; margin:0; color:#4338ca;'>
                                    🏆 Great Work, Engineer! 🏆
                                </h2>
                                <p style='font-size: 1.3rem; margin-top:16px; color:#475569;'>
                                    Here's your performance summary.
                                </p>

                                <div style='
                                    background:white;
                                    padding:24px;
                                    border-radius:12px;
                                    margin:24px auto;
                                    border:1px solid #e2e8f0;
                                    max-width:600px;
                                '>
                                    <h3 style='margin-top:0; color:#1e293b;'>Your Stats</h3>

                                    <div style='display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px;'>
                                        <div style='
                                            text-align:center;
                                            padding:16px;
                                            background:#eef2ff;
                                            border-radius:8px;
                                            border:1px solid #c7d2fe;
                                        '>
                                            <p style='margin:0; font-size:0.9rem; color:#64748b;'>Best Accuracy</p>
                                            <p style='margin:4px 0 0 0; font-size:1.8rem; font-weight:700; color:#4338ca;'>
                                                {best_score_pct}
                                            </p>
                                        </div>

                                        <div style='
                                            text-align:center;
                                            padding:16px;
                                            background:#f0fdf4;
                                            border-radius:8px;
                                            border:1px solid #bbf7d0;
                                        '>
                                            <p style='margin:0; font-size:0.9rem; color:#64748b;'>Your Rank</p>
                                            <p style='margin:4px 0 0 0; font-size:1.8rem; font-weight:700; color:#15803d;'>
                                                {rank_text}
                                            </p>
                                        </div>
                                    </div>

                                    <div style='
                                        text-align:center;
                                        padding:16px;
                                        background:#f8fafc;
                                        border-radius:8px;
                                        border:1px solid #e2e8f0;
                                        margin-top:16px;
                                    '>
                                        <p style='margin:0; font-size:0.9rem; color:#64748b;'>Team</p>
                                        <p style='margin:4px 0 0 0; font-size:1.3rem; font-weight:600; color:#4338ca;'>
                                            🛡️ {team_text}
                                        </p>
                                    </div>
                                </div>

                                <p style='font-size: 1.2rem; margin-top:16px; color:#475569; font-weight:500;'>
                                    Ready to share your model and explore its real-world impact?
                                </p>
                            </div>
                        </div>
                        """
                        return {
                            stats_display: gr.update(value=new_celebration_html),
                            login_form: gr.update(visible=False),
                            login_feedback: gr.update(value=message, visible=True)
                        }
                    elif success:
                        # Signed in but no submissions
                        new_celebration_html = """
                        <div style='
                            background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
                            border: 2px solid #6366f1;
                            border-radius: 16px;
                            padding: 32px;
                            box-shadow: 0 8px 20px rgba(0,0,0,0.05);
                            max-width: 800px;
                            margin: auto;
                        '>
                            <div style='text-align:center;'>
                                <h2 style='font-size: 2.3rem; margin:0; color:#4338ca;'>
                                    🚀 You're Signed In!
                                </h2>
                                <p style='font-size: 1.2rem; margin-top:20px; color:#475569;'>
                                    You haven't submitted a model yet, but you're all set to continue learning.
                                </p>

                                <div style='
                                    background:white;
                                    padding:24px;
                                    border-radius:12px;
                                    margin:24px auto;
                                    border:1px solid #e2e8f0;
                                    max-width:600px;
                                '>
                                    <p style='font-size:1.1rem; margin:0; color:#334155;'>
                                        Once you submit a model in the Model Building Game,
                                        your accuracy and ranking will appear here.
                                    </p>
                                </div>

                                <p style='font-size: 1.2rem; margin-top:16px; color:#475569; font-weight:500;'>
                                    Continue to the next section when you're ready.
                                </p>
                            </div>
                        </div>
                        """
                        return {
                            stats_display: gr.update(value=new_celebration_html),
                            login_form: gr.update(visible=False),
                            login_feedback: gr.update(value=message, visible=True)
                        }
                    else:
                        # Login failed
                        return {
                            stats_display: gr.update(),
                            login_form: gr.update(visible=True),
                            login_feedback: gr.update(value=message, visible=True)
                        }

                login_submit.click(
                    fn=handle_login,
                    inputs=[login_username, login_password],
                    outputs=[stats_display, login_form, login_feedback]
                )

            gr.HTML("<div style='margin:32px 0;'></div>")

            deploy_button = gr.Button(
                "🌍 Share Your AI Model (Simulation Only)",
                variant="primary",
                size="lg",
                scale=1
            )

        # Step 2: The Twist - Reality Check
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            gr.Markdown("<h2 style='text-align:center;'>⚠️ But Wait...</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#fef9c3; padding:28px; border-radius:16px; border: 3px solid #f59e0b;'>
                    <p style='text-align:center; font-size:1.5rem; font-weight:600; margin:0;'>
                        Before we share the model, there's something you need to know...
                    </p>

                    <div style='margin-top:32px; background:white; padding:24px; border-radius:12px;'>
                        <h3 style='margin-top:0; color:#92400e;'>A Real-World Story</h3>
                        <p>
                            A model similar to yours was actually used in the real world.
                            It was used by judges across the United States to help make decisions
                            about defendants' futures.
                        </p>
                        <p style='margin-top:16px;'>
                            Like yours, it had impressive accuracy scores. Like yours, it was built
                            on data about past criminal cases. Like yours, it aimed to predict
                            who would re-offend.
                        </p>
                        <p style='margin-top:16px; font-weight:600;'>
                            But something was terribly wrong...
                        </p>
                    </div>
                </div>
                """
            )

            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Reveal the Truth ▶️", variant="primary", size="lg")

        # Step 3: The Revelation - ProPublica Investigation
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            gr.Markdown("<h2 style='text-align:center;'>📰 The ProPublica Investigation</h2>")
            gr.HTML(
                """
                <div class='revelation-box dramatic-reveal'>
                    <h3 style='color:#991b1b; margin-top:0; font-size:1.8rem;'>
                        "Machine Bias" - A Landmark Investigation
                    </h3>

                    <p style='font-size:1.1rem; line-height:1.6;'>
                        In 2016, journalists at <strong>ProPublica</strong> investigated a widely-used criminal risk
                        assessment algorithm called <strong>COMPAS</strong>. They analyzed over
                        <strong>7,000 actual cases</strong> to see if the AI's predictions came true.
                    </p>

                    <div style='background:#fff; padding:24px; border-radius:12px; margin:24px 0; border:2px solid #dc2626;'>
                        <h4 style='margin-top:0; color:#dc2626;'>Their Shocking Findings:</h4>

                        <div style='margin:20px 0; padding:20px; background:#fef2f2; border-radius:8px;'>
                            <p style='font-size:1.15rem; font-weight:600; margin:0; color:#991b1b;'>
                                ⚠️ Black defendants were labeled "high-risk" at nearly TWICE the rate of white defendants
                            </p>
                        </div>

                        <p style='font-size:1.05rem; margin-top:20px;'>
                            <strong>Specifically:</strong>
                        </p>
                        <ul style='font-size:1.05rem; line-height:1.8;'>
                            <li>
                                <strong style='color:#dc2626;'>Black defendants</strong> who
                                <em>did NOT re-offend</em> were incorrectly labeled as
                                <strong>"high-risk"</strong> at a rate of <strong>45%</strong>
                            </li>
                            <li>
                                <strong>White defendants</strong> who <em>did NOT re-offend</em>
                                were incorrectly labeled as <strong>"high-risk"</strong> at a rate
                                of only <strong>24%</strong>
                            </li>
                            <li style='margin-top:12px;'>
                                Meanwhile, <strong style='color:#dc2626;'>white defendants</strong> who
                                <em>DID re-offend</em> were <strong>more likely to be labeled
                                "low-risk"</strong> compared to Black defendants
                            </li>
                        </ul>
                    </div>

                    <div style='background:#dbeafe; padding:20px; border-radius:8px; border-left:6px solid #2563eb;'>
                        <h4 style='margin-top:0; color:#1e40af;'>What Does This Mean?</h4>
                        <p style='font-size:1.05rem; margin:0; line-height:1.6;'>
                            The AI system was <strong>systematically biased</strong>. It didn't just
                            make random errors—it made <strong>different kinds of errors for different
                            groups of people</strong>.
                        </p>
                        <p style='font-size:1.05rem; margin-top:12px; line-height:1.6;'>
                            Black defendants faced a much higher risk of being <strong>unfairly labeled
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

        # NEW Step 4: Europe Too – This Isn’t Just a US Problem
        with gr.Column(visible=False, elem_id="step-4-eu") as step_4_eu:
            gr.Markdown("<h2 style='text-align:center;'>🇪🇺 This Isn’t Just a US Problem</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#e0f2fe; padding:32px; border-radius:16px;
                            border: 3px solid #0369a1; max-width:900px; margin:auto;'>
                    <h3 style='color:#0c4a6e; margin-top:0; font-size:1.9rem; text-align:center;'>
                        AI for “Risky Offenders” Is Already in Europe
                    </h3>

                    <p style='line-height:1.8;'>
                        The COMPAS story is not just an American warning. Across Europe, public authorities
                        have experimented with <strong>very similar tools</strong> that aim to predict
                        who will reoffend or which areas are “high risk”.
                    </p>

                    <ul style='line-height:1.9; font-size:1.05rem; margin:20px 0;'>
                        <li>
                            <strong>United Kingdom – HART (Harm Assessment Risk Tool)</strong><br>
                            A machine-learning model used by Durham Police to predict who will reoffend within
                            two years. It uses variables like age, gender, <em>postcode</em>, housing and job
                            instability – socio-economic proxies that can reproduce the same kinds of biased
                            patterns exposed in COMPAS.
                        </li>
                        <li style='margin-top:14px;'>
                            <strong>Spain – VioGén</strong><br>
                            A risk tool for gender-violence cases whose inner workings are largely a
                            <em>"black box"</em>. Officers rely heavily on its scores to decide protection
                            measures, even though the algorithm cannot easily be audited for bias or errors.
                        </li>
                        <li style='margin-top:14px;'>
                            <strong>Netherlands &amp; Denmark – Predictive profiling</strong><br>
                            Systems like the Dutch <em>Crime Anticipation System (CAS)</em> and Denmark’s
                            algorithmic <em>“ghetto”</em> classifications use demographic and socio-economic
                            data to steer policing and penalties, risking feedback loops that target certain
                            communities again and again.
                        </li>
                    </ul>

                    <div style='background:#eff6ff; padding:22px; border-radius:12px; border-left:6px solid #1d4ed8; margin:28px 0;'>
                        <h4 style='margin-top:0; color:#1d4ed8;'>Ongoing European Debate</h4>
                        <p style='margin:0; line-height:1.7; font-size:1.05rem;'>
                            The Barcelona Prosecuter's office has proposed an "electronic repeat-offense calculator".  
                            Courts, regulators and researchers are actively examining how these tools affect
                            fundamental rights such as non-discrimination, fair trial and data protection.
                        </p>
                    </div>

                    <div style='background:#fef3c7; padding:22px; border-radius:12px; border-left:6px solid #f59e0b;'>
                        <p style='margin:0; line-height:1.8; font-size:1.1rem;'>
                            <strong>Key point:</strong> The risks you saw with COMPAS are not far away
                            in another country. <strong>They are live questions in both Europe and the U.S. right now.</strong>
                        </p>
                    </div>
                </div>
                """
            )

            with gr.Row():
                step_4_eu_back = gr.Button("◀️ Back to the Investigation", size="lg")
                step_4_eu_next = gr.Button("Zoom Out to the Lesson ▶️", variant="primary", size="lg")

        # Step 5: The Key Takeaway (was Step 4)
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            gr.Markdown("<h2 style='text-align:center;'>💡 The Critical Lesson</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#fef3c7; padding:32px; border-radius:16px; border: 3px solid #f59e0b;'>
                    <h3 style='color:#92400e; margin-top:0; text-align:center; font-size:2rem;'>
                        High Accuracy ≠ Fair Outcomes
                    </h3>

                    <div style='background:white; padding:28px; border-radius:12px; margin:24px 0;'>
                        <h4 style='margin-top:0; color:#1f2937;'>Why This Matters:</h4>

                        <p style='line-height:1.8;'>
                            <strong>1. Overall accuracy can hide group-specific harm</strong><br>
                            A model might be 70% accurate overall, but that 30% error rate might
                            fall disproportionately on certain groups.
                        </p>

                        <p style='line-height:1.8; margin-top:20px;'>
                            <strong>2. Historical bias in training data gets amplified</strong><br>
                            If past policing or judicial decisions were biased, the AI will learn
                            and replicate those patterns—often making them worse.
                        </p>

                        <p style='line-height:1.8; margin-top:20px;'>
                            <strong>3. Real people's lives are affected</strong><br>
                            These aren't just statistics. Each "false positive" represents a person
                            who lost years of their life, separated from family, denied opportunities—
                            all based on a biased prediction.
                        </p>
                    </div>

                    <div class='revelation-box' style='margin-top:24px;'>
                        <h4 style='margin-top:0; font-size:1.5rem; color:#991b1b;'>
                            ⚖️ The New Standard
                        </h4>
                        <p style='font-size:1.15rem; line-height:1.8; margin:0;'>
                            Building accurate AI is not enough. We must also ask:
                            <strong>Is this system fair? Does it treat all groups equitably?
                            Could it amplify existing societal harms?</strong>
                        </p>
                    </div>
                </div>
                """
            )

            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("What Can We Do? ▶️", variant="primary", size="lg")

        # Step 6: The Path Forward (was Step 5)
        with gr.Column(visible=False, elem_id="step-5") as step_5:
            gr.Markdown("<h2 style='text-align:center;'>🛤️ The Path Forward</h2>")
            gr.HTML(
                """
                <div style='text-align:center;'>
                    <div style='font-size: 20px; background:#e0f2fe; padding:32px; border-radius:16px;
                                border: 3px solid #0369a1; max-width:900px; margin:auto;'>
                        <h3 style='color:#0c4a6e; margin-top:0; font-size:2rem;'>
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

                        <div style='background:white; padding:28px; border-radius:12px; margin:32px 0; text-align:left;'>
                            <h4 style='margin-top:0; color:#0c4a6e;'>What You'll Do Next:</h4>
                            <p style='font-size:1.1rem; line-height:1.8;'>
                                In the next section, you'll be introduced to a <strong>new way of measuring
                                success</strong>—one that balances performance with fairness and ethics.
                            </p>
                            <p style='font-size:1.1rem; line-height:1.8; margin-top:16px;'>
                                You'll learn techniques to <strong>detect bias</strong> in your models,
                                <strong>measure fairness</strong> across different groups, and
                                <strong>redesign your AI</strong> to minimize harm.
                            </p>
                        </div>

                        <div style='background:#fef3c7; padding:24px; border-radius:12px; border-left:6px solid #f59e0b; text-align:left;'>
                            <p style='font-size:1.15rem; font-weight:600; margin:0;'>
                                🎯 Your new mission: Build AI that is not just accurate, but also
                                <strong>fair, equitable, and ethically sound</strong>.
                            </p>
                        </div>

                        <h1 style='margin:32px 0 16px 0; font-size: 3rem;'>👇 SCROLL DOWN 👇</h1>
                        <p style='font-size:1.2rem;'>Continue to the next section below to begin your ethical AI journey.</p>
                    </div>
                </div>
                """
            )

            back_to_lesson_btn = gr.Button("◀️ Review the Investigation", size="lg")

        # --- NAVIGATION LOGIC ---

        all_steps = [step_1, step_2, step_3, step_4_eu, step_4, step_5, loading_screen]

        def create_nav_generator(current_step, next_step):
            """A helper to create the generator functions to avoid repetitive code."""
            def navigate():
                # Yield 1: Show loading, hide all
                updates = {loading_screen: gr.update(visible=True)}
                for step in all_steps:
                    if step != loading_screen:
                        updates[step] = gr.update(visible=False)
                yield updates

                # Yield 2: Show new step, hide all
                updates = {next_step: gr.update(visible=True)}
                for step in all_steps:
                    if step != next_step:
                        updates[step] = gr.update(visible=False)
                yield updates
            return navigate

        # Helper function to generate navigation JS with loading overlay
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

        # --- Wire up navigation ---
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
            js=nav_js("step-4-eu", "Seeing how this plays out in Europe...")
        )
        step_4_eu_back.click(
            fn=create_nav_generator(step_4_eu, step_3),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-3", "Reviewing the ProPublica findings...")
        )
        step_4_eu_next.click(
            fn=create_nav_generator(step_4_eu, step_4),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4", "Zooming out to the key lesson...")
        )
        step_4_back.click(
            fn=create_nav_generator(step_4, step_4_eu),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4-eu", "Revisiting the European context...")
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

    return demo


def launch_ethical_revelation_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    """Convenience wrapper to create and launch the ethical revelation app inline."""
    demo = create_ethical_revelation_app()
    demo.launch(share=share, inline=True, debug=debug, height=height)


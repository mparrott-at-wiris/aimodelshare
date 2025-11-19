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
                "is_signed_in": True
            }
        
        # Get user's best score and rank
        best_score = None
        rank = None
        team_name = os.environ.get("TEAM_NAME")
        
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
                            user_submissions["timestamp"] = pd.to_datetime(user_submissions["timestamp"], errors='coerce')
                            user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                        except:
                            pass
                    team_name = user_submissions.iloc[0]["Team"]
            
            # Calculate rank
            user_bests = leaderboard_df.groupby("username")["accuracy"].max()
            individual_summary_df = user_bests.reset_index()
            individual_summary_df.columns = ["Engineer", "Best_Score"]
            individual_summary_df = individual_summary_df.sort_values("Best_Score", ascending=False).reset_index(drop=True)
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
            "username": os.environ.get("username"),
            "best_score": None,
            "rank": None,
            "team_name": os.environ.get("TEAM_NAME"),
            "is_signed_in": bool(os.environ.get("username"))
        }


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
    
    /* Pulse animation for dramatic reveal */
    @keyframes pulse-dramatic {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.9; }
    }
    
    .dramatic-reveal {
        animation: pulse-dramatic 2s ease-in-out infinite;
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
                <div class='celebration-box'>
                    <div style='text-align:center; padding:20px;'>
                        <h2 style='font-size: 2.5rem; margin:0; color:#92400e;'>
                            🏆 Mission Accomplished! 🏆
                        </h2>
                        <p style='font-size: 1.5rem; margin-top:20px; color:#78350f;'>
                            You've built a high-performing AI model!
                        </p>
                        <div style='background:white; padding:24px; border-radius:12px; margin:24px auto; max-width:600px;'>
                            <h3 style='margin-top:0; color:#374151;'>Your Achievement Summary</h3>
                            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;'>
                                <div style='text-align:center; padding:12px; background:#f0fdf4; border-radius:8px;'>
                                    <p style='margin:0; font-size:0.9rem; color:#6b7280;'>Best Accuracy</p>
                                    <p style='margin:4px 0 0 0; font-size:2rem; font-weight:700; color:#16a34a;'>{best_score_pct}</p>
                                </div>
                                <div style='text-align:center; padding:12px; background:#eff6ff; border-radius:8px;'>
                                    <p style='margin:0; font-size:0.9rem; color:#6b7280;'>Your Rank</p>
                                    <p style='margin:4px 0 0 0; font-size:2rem; font-weight:700; color:#2563eb;'>{rank_text}</p>
                                </div>
                            </div>
                            <div style='text-align:center; padding:12px; background:#fef3c7; border-radius:8px; margin-top:16px;'>
                                <p style='margin:0; font-size:0.9rem; color:#6b7280;'>Your Team</p>
                                <p style='margin:4px 0 0 0; font-size:1.3rem; font-weight:600; color:#92400e;'>🛡️ {team_text}</p>
                            </div>
                            <p style='font-size:1.1rem; margin-top:20px; color:#374151;'>
                                You competed, improved, and climbed the leaderboard!
                            </p>
                        </div>
                        <p style='font-size: 1.3rem; margin-top:24px; color:#78350f; font-weight:600;'>
                            It's time to share your creation with the world!
                        </p>
                    </div>
                </div>
                """
            elif user_stats["is_signed_in"]:
                # Signed in but no submissions yet
                celebration_html = """
                <div class='celebration-box'>
                    <div style='text-align:center; padding:20px;'>
                        <h2 style='font-size: 2.5rem; margin:0; color:#92400e;'>
                            🏆 Ready to Deploy! 🏆
                        </h2>
                        <p style='font-size: 1.5rem; margin-top:20px; color:#78350f;'>
                            You've learned about building AI models!
                        </p>
                        <div style='background:white; padding:24px; border-radius:12px; margin:24px auto; max-width:500px;'>
                            <p style='font-size:1.2rem; margin:0; color:#374151;'>
                                You've gone through the model-building process.<br>
                                Now let's explore what happens when we deploy AI to the real world.
                            </p>
                        </div>
                        <p style='font-size: 1.3rem; margin-top:24px; color:#78350f; font-weight:600;'>
                            It's time to share your creation with the world!
                        </p>
                    </div>
                </div>
                """
            else:
                # Not signed in - show prompt
                celebration_html = """
                <div style='background:#fef3c7; padding:32px; border-radius:16px; border:3px solid #f59e0b; text-align:center;'>
                    <h2 style='font-size: 2rem; margin:0; color:#92400e;'>
                        📊 Sign In to See Your Stats
                    </h2>
                    <p style='font-size: 1.2rem; margin-top:20px; color:#78350f; line-height:1.6;'>
                        To view your personalized achievement summary, please sign in through the 
                        <strong>Model Building Game</strong> activity above.
                    </p>
                    <div style='background:white; padding:24px; border-radius:12px; margin:24px auto; max-width:500px;'>
                        <p style='font-size:1rem; margin:0; color:#374151; line-height:1.6;'>
                            If you've completed the Model Building Game and haven't signed in yet, 
                            scroll up to that section and click the sign-in button to authenticate. 
                            Then return here to see your actual scores and rankings!
                        </p>
                    </div>
                    <p style='font-size: 1.1rem; margin-top:24px; color:#78350f;'>
                        You can still continue through this lesson without signing in.
                    </p>
                </div>
                """
            
            gr.HTML(celebration_html)
            
            gr.HTML("<div style='margin:32px 0;'></div>")
            
            deploy_button = gr.Button(
                "🌍 Deploy: Share Your AI Model with the World!",
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
                        Before we deploy, there's something you need to know...
                    </p>
                    
                    <div style='margin-top:32px; background:white; padding:24px; border-radius:12px;'>
                        <h3 style='margin-top:0; color:#92400e;'>A Real-World Story</h3>
                        <p>
                            A model similar to yours was actually deployed in the real world.
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
                        In 2016, <strong>ProPublica</strong> investigated a widely-used criminal risk
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
                                of only <strong>23%</strong>
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
                step_3_next = gr.Button("Understand the Impact ▶️", variant="primary", size="lg")
        
        # Step 4: The Key Takeaway
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
        
        # Step 5: The Path Forward
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
                            <li>✅ You built models that achieved high accuracy scores</li>
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
        
        all_steps = [step_1, step_2, step_3, step_4, step_5, loading_screen]

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
            js=nav_js("step-2", "Deploying model...")
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
            fn=create_nav_generator(step_3, step_4), 
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4", "Understanding the impact...")
        )
        step_4_back.click(
            fn=create_nav_generator(step_4, step_3), 
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-3", "Reviewing findings...")
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
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the ethical revelation app.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

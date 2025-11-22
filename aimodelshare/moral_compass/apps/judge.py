"""
You Be the Judge - Gradio application for the Justice & Equity Challenge.

This app teaches:
1. How to make decisions based on AI predictions
2. The stakes involved in using AI for criminal justice decisions
3. The importance of understanding what AI gets wrong

Structure:
- Factory function `create_judge_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_judge_app()` launches it inline (for notebooks)
"""
import contextlib
import os


def _generate_defendant_profiles():
    """Generate synthetic defendant profiles for the exercise."""
    import random
    random.seed(42)  # For reproducibility

    profiles = [
        {
            "id": 1,
            "name": "Carlos M.",
            "age": 23,
            "gender": "Male",
            "race": "Hispanic",
            "prior_offenses": 2,
            "current_charge": "Drug possession",
            "ai_risk": "High",
            "ai_confidence": "85%",
        },
        {
            "id": 2,
            "name": "Sarah J.",
            "age": 34,
            "gender": "Female",
            "race": "White",
            "prior_offenses": 0,
            "current_charge": "Theft",
            "ai_risk": "Low",
            "ai_confidence": "72%",
        },
        {
            "id": 3,
            "name": "DeShawn W.",
            "age": 19,
            "gender": "Male",
            "race": "Black",
            "prior_offenses": 1,
            "current_charge": "Assault",
            "ai_risk": "Medium",
            "ai_confidence": "68%",
        },
        {
            "id": 4,
            "name": "Maria R.",
            "age": 41,
            "gender": "Female",
            "race": "Hispanic",
            "prior_offenses": 3,
            "current_charge": "Fraud",
            "ai_risk": "Medium",
            "ai_confidence": "70%",
        },
        {
            "id": 5,
            "name": "James K.",
            "age": 28,
            "gender": "Male",
            "race": "White",
            "prior_offenses": 5,
            "current_charge": "Burglary",
            "ai_risk": "High",
            "ai_confidence": "91%",
        },
    ]

    return profiles


def create_judge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the You Be the Judge Gradio Blocks app (not launched yet)."""
    os.environ["APP_NAME"] = "judge"

    try:
        import gradio as gr
        gr.close_all(verbose=False)

    except ImportError as e:
        raise ImportError(
            "Gradio is required for the judge app. Install with `pip install gradio`."
        ) from e

    profiles = _generate_defendant_profiles()

    # State to track decisions
    decisions = {}

    def format_profile(profile):
        """Format a defendant profile for display using theme-aware CSS classes."""
        risk_class = f"risk-{profile['ai_risk'].lower()}"
        return f"""
        <div class="profile-card {risk_class}">
            <h3 class="profile-title">
                Defendant #{profile['id']}: {profile['name']}
            </h3>
            <div class="profile-grid">
                <div><b>Age:</b> {profile['age']}</div>
                <div><b>Gender:</b> {profile['gender']}</div>
                <div><b>Race:</b> {profile['race']}</div>
                <div><b>Prior Offenses:</b> {profile['prior_offenses']}</div>
                <div class="profile-charge">
                    <b>Current Charge:</b> {profile['current_charge']}
                </div>
            </div>
            <div class="ai-risk-container">
                <b>🤖 AI Risk Assessment:</b>
                <span class="ai-risk-label {risk_class}">
                    {profile['ai_risk']} Risk
                </span>
                <span class="ai-risk-confidence">
                    (Confidence: {profile['ai_confidence']})
                </span>
            </div>
        </div>
        """

    def make_decision(defendant_id, decision):
        """Record a decision for a defendant."""
        decisions[defendant_id] = decision
        return f"✓ Decision recorded: {decision}"

    def get_summary():
        """Get summary of all decisions made."""
        if not decisions:
            return "No decisions made yet."

        released = sum(1 for d in decisions.values() if d == "Release")
        kept = sum(1 for d in decisions.values() if d == "Keep in Prison")

        summary = f"""
        <div class="summary-box">
            <h3 class="summary-title">📊 Your Decisions Summary</h3>
            <div class="summary-body">
                <p><b>Prisoners Released:</b> {released} of {len(decisions)}</p>
                <p><b>Prisoners Kept in Prison:</b> {kept} of {len(decisions)}</p>
            </div>
        </div>
        """
        return summary

    css = """
    /* -------------------------------------------- */
    /* BUTTONS                                      */
    /* -------------------------------------------- */
    .decision-button {
        font-size: 18px !important;
        padding: 12px 24px !important;
    }

    /* -------------------------------------------- */
    /* TOP INTRO & CONTEXT BOXES                    */
    /* -------------------------------------------- */

    .judge-intro-box {
        text-align: center;
        font-size: 18px;
        max-width: 900px;
        margin: auto;
        padding: 20px;
        border-radius: 12px;
        border: 2px solid var(--border-color-primary);

        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    }

    .scenario-box {
        font-size: 18px;
        padding: 24px;
        border-radius: 12px;

        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 1px solid var(--border-color-primary);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    }

    .hint-box {
        text-align: center;
        font-size: 16px;
        padding: 12px;
        border-radius: 8px;

        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 1px solid var(--border-color-primary);
    }

    .complete-box {
        font-size: 1.3rem;
        padding: 28px;
        border-radius: 16px;

        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 2px solid var(--color-accent);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    }

    .loading-title {
        font-size: 2rem;
        color: var(--secondary-text-color);
    }

    /* -------------------------------------------- */
    /* DEFENDANT PROFILE CARD                       */
    /* -------------------------------------------- */

    .profile-card {
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid var(--border-color-primary);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    }

    .profile-title {
        margin-top: 0;
        color: var(--body-text-color);
    }

    .profile-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        font-size: 16px;
    }

    .profile-charge {
        grid-column: span 2;
    }

    .ai-risk-container {
        margin-top: 16px;
        padding: 12px;
        background-color: var(--body-background-fill);
        border-radius: 8px;
        border: 1px solid var(--border-color-primary);
    }

    .ai-risk-label {
        font-size: 20px;
        font-weight: bold;
        margin-left: 4px;
    }

    .ai-risk-confidence {
        color: var(--secondary-text-color);
        margin-left: 8px;
    }

    /* Semantic risk colors (ok to keep these brights across modes) */
    .risk-high {
        border-left-color: #ef4444;
        color: #ef4444;
    }

    .profile-card.risk-high {
        border-left-color: #ef4444;
    }

    .risk-medium {
        border-left-color: #f59e0b;
        color: #f59e0b;
    }

    .profile-card.risk-medium {
        border-left-color: #f59e0b;
    }

    .risk-low {
        border-left-color: #22c55e;
        color: #22c55e;
    }

    .profile-card.risk-low {
        border-left-color: #22c55e;
    }

    /* -------------------------------------------- */
    /* SUMMARY BOX                                  */
    /* -------------------------------------------- */

    .summary-box {
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid var(--border-color-primary);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    }

    .summary-title {
        margin-top: 0;
    }

    .summary-body {
        font-size: 18px;
    }

    /* -------------------------------------------- */
    /* NAVIGATION LOADING OVERLAY                   */
    /* -------------------------------------------- */

    #nav-loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;

        /* Blend with theme background, high confidence in both modes */
        background: color-mix(in srgb, var(--body-background-fill) 95%, transparent);

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
        border: 5px solid var(--border-color-primary);
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
        color: var(--color-accent);
    }

    /* -------------------------------------------- */
    /* DARK-MODE HIGH-CONFIDENCE OVERRIDES          */
    /* -------------------------------------------- */

    @media (prefers-color-scheme: dark) {
        .judge-intro-box,
        .scenario-box,
        .hint-box,
        .complete-box,
        .profile-card,
        .summary-box {
            background-color: #2D323E;
            color: white;
            border-color: #555555;
            box-shadow: none;
        }

        .ai-risk-container {
            background-color: #181B22;
            border-color: #555555;
        }

        #nav-loading-overlay {
            background: rgba(15, 23, 42, 0.9);
        }

        .nav-spinner {
            border-color: rgba(148, 163, 184, 0.4);
            border-top-color: var(--color-accent);
        }
    }
    """

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

        gr.Markdown("<h1 style='text-align:center;'>⚖️ You Be the Judge</h1>")
        gr.Markdown(
            """
            <div class="judge-intro-box">
              <b>Your Role:</b> You are a judge who must decide whether to release defendants from prison.<br>
              An AI system has analyzed each case and provided a risk assessment.<br><br>
              <b>Your Task:</b> Review each defendant's profile and the AI's prediction, then make your decision.
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")

        # --- Loading screen ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 class='loading-title'>⏳ Loading...</h2>
                </div>
                """
            )

        # Introduction
        with gr.Column(visible=True, elem_id="intro") as intro_section:
            gr.Markdown("<h2 style='text-align:center;'>📋 The Scenario</h2>")
            gr.Markdown(
                """
                <div class="scenario-box">
                You are a judge in a busy criminal court. Due to prison overcrowding, you must decide 
                which defendants can be safely released.<br><br>
                
                To help you, the court has implemented an AI system that predicts the risk of each 
                defendant committing new crimes if released. The AI categorizes defendants as:<br><br>
                
                <ul style='font-size:18px;'>
                    <li><span class='ai-risk-label risk-high'>High Risk</span> - Likely to re-offend</li>
                    <li><span class='ai-risk-label risk-medium'>Medium Risk</span> - Moderate chance of re-offending</li>
                    <li><span class='ai-risk-label risk-low'>Low Risk</span> - Unlikely to re-offend</li>
                </ul>
                
                <b>Remember:</b> Your decisions affect real people's lives and public safety.
                </div>
                """
            )
            start_btn = gr.Button("Begin Making Decisions ▶️", variant="primary", size="lg")

        # Defendant profiles section
        with gr.Column(visible=False, elem_id="profiles") as profiles_section:
            gr.Markdown("<h2 style='text-align:center;'>👥 Defendant Profiles</h2>")
            gr.Markdown(
                """
                <div class="hint-box">
                  Review each defendant's information and the AI's risk assessment, then make your decision.
                </div>
                """
            )
            gr.HTML("<br>")

            # Create UI for each defendant
            for profile in profiles:
                with gr.Column():
                    gr.HTML(format_profile(profile))

                    with gr.Row():
                        release_btn = gr.Button(
                            "✓ Release Prisoner",
                            variant="primary",
                            elem_classes=["decision-button"],
                        )
                        keep_btn = gr.Button(
                            "✗ Keep in Prison",
                            variant="secondary",
                            elem_classes=["decision-button"],
                        )

                    decision_status = gr.Markdown("")

                    # Wire up buttons
                    release_btn.click(
                        lambda p_id=profile["id"]: make_decision(p_id, "Release"),
                        inputs=None,
                        outputs=decision_status,
                    )
                    keep_btn.click(
                        lambda p_id=profile["id"]: make_decision(p_id, "Keep in Prison"),
                        inputs=None,
                        outputs=decision_status,
                    )

                    gr.HTML("<hr style='margin:24px 0;'>")

            # Summary section
            summary_display = gr.HTML("")
            show_summary_btn = gr.Button(
                "📊 Show My Decisions Summary", variant="primary", size="lg"
            )
            show_summary_btn.click(get_summary, inputs=None, outputs=summary_display)

            gr.HTML("<br>")
            complete_btn = gr.Button(
                "Complete This Section ▶️", variant="primary", size="lg"
            )

        # Completion section
        with gr.Column(visible=False, elem_id="complete") as complete_section:
            gr.Markdown(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>✅ Decisions Complete!</h2>
                    <div class="complete-box">
                        You've made your decisions based on the AI's recommendations.<br><br>
                        But here's the critical question:<br><br>
                        <h2 style='margin:16px 0; color: var(--color-accent);'>
                          What if the AI was wrong?
                        </h2>
                        <p style='font-size:1.1rem;'>
                        Continue to the next section below to explore the consequences of 
                        trusting AI predictions in high-stakes situations.
                        </p>
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 SCROLL DOWN 👇</h1>
                        <p style='font-size:1.1rem;'>
                          Find the next section below to continue your journey.
                        </p>
                    </div>
                </div>
                """
            )
            back_to_profiles_btn = gr.Button("◀️ Back to Review Decisions")

        # --- NAVIGATION LOGIC (GENERATOR-BASED) ---

        all_steps = [intro_section, profiles_section, complete_section, loading_screen]

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

        # --- Wire up each button to its own unique generator ---
        start_btn.click(
            fn=create_nav_generator(intro_section, profiles_section),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("profiles", "Loading defendant profiles..."),
        )
        complete_btn.click(
            fn=create_nav_generator(profiles_section, complete_section),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("complete", "Reviewing your decisions..."),
        )
        back_to_profiles_btn.click(
            fn=create_nav_generator(complete_section, profiles_section),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("profiles", "Returning to profiles..."),
        )

    return demo


def launch_judge_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    """Convenience wrapper to create and launch the judge app inline."""
    demo = create_judge_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the tutorial app.") from e
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

launch_judge_app()

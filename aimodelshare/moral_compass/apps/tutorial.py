"""
Tutorial Gradio application for onboarding users to the Justice & Equity Challenge.

This app teaches:
1. How to advance slideshow-style steps
2. How to interact with sliders/buttons
3. How model prediction output appears

Structure:
- Factory function `create_tutorial_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_tutorial_app()` launches it inline (for notebooks)
"""
import contextlib
import os


def _build_synthetic_model():
    """Build a tiny linear regression model on synthetic study habit data."""
    import numpy as np
    from sklearn.linear_model import LinearRegression

    rng = np.random.default_rng(7)
    n = 200
    hours_study = rng.uniform(0, 12, n)
    hours_sleep = rng.uniform(4, 10, n)
    attendance = rng.uniform(50, 100, n)
    exam_score = (
        5 * hours_study
        + 3 * hours_sleep
        + 0.5 * attendance
        + rng.normal(0, 10, n)
    )

    X = np.column_stack([hours_study, hours_sleep, attendance])
    y = exam_score
    lin_reg = LinearRegression().fit(X, y)

    def predict_exam(sl, slp, att):
        pred = float(lin_reg.predict([[sl, slp, att]])[0])
        import numpy as np

        pred = float(np.clip(pred, 0, 100))
        return f"{round(pred, 1)}%"

    return predict_exam


def create_tutorial_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the tutorial Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr

        gr.close_all(verbose=False)

    except ImportError as e:
        raise ImportError(
            "Gradio is required for the tutorial app. Install with `pip install gradio`."
        ) from e

    predict_exam = _build_synthetic_model()

    # All custom colors use Gradio theme variables + dark-mode overrides.
    css = """
    /* ---------------------------------------------------- */
    /* CORE TYPOGRAPHY / COMPONENT OVERRIDES                */
    /* ---------------------------------------------------- */

    /* Prediction output styled with theme accent color */
    #prediction_output_textbox textarea {
        font-size: 2.5rem !important;
        font-weight: bold !important;
        text-align: center !important;
        color: var(--color-accent) !important;
    }

    /* Tutorial intro container at top */
    .tutorial-intro-box {
        text-align: left;
        font-size: 20px;
        max-width: 800px;
        margin: auto;
        padding: 15px;
        border-radius: 8px;

        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 1px solid var(--border-color-primary);

        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    }

    /* Slide-style emphasis box (Step 1) */
    .slide-box {
        font-size: 28px;
        text-align: center;
        padding: 28px;
        border-radius: 16px;
        min-height: 150px;

        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 1px solid var(--border-color-primary);

        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    }

    /* Step 2 explanation box */
    .interactive-info-box {
        font-size: 20px;
        text-align: left;
        padding: 20px;
        border-radius: 16px;

        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 1px solid var(--border-color-primary);

        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    }

    /* Completion message (Step 3) */
    .complete-box {
        font-size: 1.5rem;
        padding: 28px;
        border-radius: 16px;

        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        border: 2px solid var(--color-accent);

        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    }

    /* Loading title text */
    .loading-title {
        font-size: 2rem;
        color: var(--secondary-text-color);
    }

    /* ---------------------------------------------------- */
    /* NAVIGATION LOADING OVERLAY                           */
    /* ---------------------------------------------------- */

    #nav-loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;

        /* Use theme background, slightly blended with transparency */
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

    /* ---------------------------------------------------- */
    /* DARK MODE OVERRIDES (HIGH-CONFIDENCE ZONE)           */
    /* ---------------------------------------------------- */

    @media (prefers-color-scheme: dark) {
        .tutorial-intro-box,
        .slide-box,
        .interactive-info-box,
        .complete-box {
            /* Explicit dark background for strong contrast */
            background-color: #2D323E;
            color: white;
            border-color: #555555;
            box-shadow: none;
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

        gr.Markdown("<h1 style='text-align:center;'>👋 How to Use an App (A Quick Tutorial)</h1>")
        gr.Markdown(
            """
            <div class='tutorial-intro-box'>
              This is a simple, 3-step tutorial.<br><br>
              <b>Your Task:</b> Just read the instructions for each step and click the "Next" button to continue.
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

        # Step 1
        with gr.Column(visible=True, elem_id="step-1") as step_1_container:
            gr.Markdown("<h2 style='text-align:center;'>Step 1: How to Use \"Slideshows\"</h2>")
            gr.Markdown(
                """
                <div class='slide-box'>
                  <b>This is a "Slideshow" step.</b><br><br>
                  Some apps are just for reading. Your only task is to click the "Next" button to move to the next step.
                </div>
                """
            )
            step_1_next = gr.Button("Next Step ▶️", variant="primary")

        # Step 2
        with gr.Column(visible=False, elem_id="step-2") as step_2_container:
            gr.Markdown("<h2 style='text-align:center;'>Step 2: How to Use \"Interactive Demos\"</h2>")
            gr.Markdown(
                """
                <div class='interactive-info-box'>
                  <b>This is an "Interactive Demo."</b><br><br>
                  Just follow the numbered steps below (from top to bottom) to see how it works!
                </div>
                """
            )
            gr.HTML("<br>")
            gr.Markdown(
                """
                <div style="font-size: 24px; text-align:left; padding-left: 10px;">
                  <b>[ 1 ] Use these sliders to change the inputs.</b>
                </div>
                """
            )
            s_hours = gr.Slider(0, 12, step=0.5, value=6, label="Hours Studied per Week")
            s_sleep = gr.Slider(4, 10, step=0.5, value=7, label="Hours of Sleep per Night")
            s_att = gr.Slider(50, 100, step=1, value=90, label="Class Attendance %")

            gr.HTML("<hr style='margin: 20px 0;'>")

            gr.Markdown(
                """
                <div style="font-size: 24px; text-align:left; padding-left: 10px;">
                  <b>[ 2 ] Click this button to run.</b>
                </div>
                """
            )
            with gr.Row():
                gr.HTML(visible=False)
                go = gr.Button("🔮 Predict", variant="primary", scale=2)
                gr.HTML(visible=False)

            gr.HTML("<hr style='margin: 20px 0;'>")

            gr.Markdown(
                """
                <div style="font-size: 24px; text-align:left; padding-left: 10px;">
                  <b>[ 3 ] See the result here!</b>
                </div>
                """
            )
            out = gr.Textbox(
                label="🔮 Predicted Exam Score",
                elem_id="prediction_output_textbox",
                interactive=False,
            )

            # Added scroll_to_output so the page scrolls to the prediction result automatically.
            go.click(
                predict_exam,
                [s_hours, s_sleep, s_att],
                out,
                scroll_to_output=True,
            )

            gr.HTML("<hr style='margin: 15px 0;'>")
            with gr.Row():
                step_2_back = gr.Button("◀️ Back")
                step_2_next = gr.Button("Finish Tutorial ▶️", variant="primary")

        # Step 3
        with gr.Column(visible=False, elem_id="step-3") as step_3_container:
            gr.Markdown(
                """
                <div style='text-align:center;'>
                  <h2 style='text-align:center; font-size: 2.5rem;'>✅ Tutorial Complete!</h2>
                  <div class='complete-box'>
                    You've mastered the basics!<br><br>
                    Your next step is <b>outside</b> this app window.<br><br>
                    <h1 style='margin:0; font-size: 3rem;'>👇 SCROLL DOWN 👇</h1><br>
                    Look below this app to find <b>Section 3</b> and begin the challenge!
                  </div>
                </div>
                """
            )
            with gr.Row():
                step_3_back = gr.Button("◀️ Back")

        # --- NAVIGATION LOGIC (GENERATOR-BASED) ---
        all_steps = [step_1_container, step_2_container, step_3_container, loading_screen]

        def create_nav_generator(current_step, next_step):
            """A helper to create the generator functions to avoid repetitive code."""

            def navigate():
                updates = {loading_screen: gr.update(visible=True)}
                for step in all_steps:
                    if step != loading_screen:
                        updates[step] = gr.update(visible=False)
                yield updates

                updates = {next_step: gr.update(visible=True)}
                for step in all_steps:
                    if step != next_step:
                        updates[step] = gr.update(visible=False)
                yield updates

            return navigate

        # Helper function to generate navigation JS with loading overlay
        def nav_js(target_id: str, message: str, min_show_ms: int = 1200) -> str:
            """
            Generate JavaScript for enhanced slide navigation with loading overlay.

            Args:
                target_id: Element ID of the target slide (e.g., 'step-2')
                message: Loading message to display during transition
                min_show_ms: Minimum time to show overlay (prevents flicker)

            Returns:
                JavaScript arrow function string for Gradio's js parameter
            """
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

        step_1_next.click(
            fn=create_nav_generator(step_1_container, step_2_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-2", "Learning to interact..."),
        )
        step_2_back.click(
            fn=create_nav_generator(step_2_container, step_1_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-1", "Returning to start..."),
        )
        step_2_next.click(
            fn=create_nav_generator(step_2_container, step_3_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-3", "Completing tutorial..."),
        )
        step_3_back.click(
            fn=create_nav_generator(step_3_container, step_2_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-2", "Going back..."),
        )

    return demo


def launch_tutorial_app(height: int = 950, share: bool = False, debug: bool = False) -> None:
    """Convenience wrapper to create and launch the tutorial app inline."""
    demo = create_tutorial_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the tutorial app.") from e
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)



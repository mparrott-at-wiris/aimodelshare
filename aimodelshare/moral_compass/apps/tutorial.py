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
    exam_score = 5 * hours_study + 3 * hours_sleep + 0.5 * attendance + rng.normal(0, 10, n)

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

    css = """
    #prediction_output_textbox textarea {
        font-size: 2.5rem !important;
        font-weight: bold !important;
        color: #1E40AF !important;
        text-align: center !important;
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("<h1 style='text-align:center;'>👋 How to Use an App (A Quick Tutorial)</h1>")
        gr.Markdown(
            """
            <div style='text-align:left; font-size:20px; max-width: 800px; margin: auto;
                        padding: 15px; background-color: #f7f7f7; border-radius: 8px;'>
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
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )

        # Step 1
        with gr.Column(visible=True) as step_1_container:
            gr.Markdown("<h2 style='text-align:center;'>Step 1: How to Use \"Slideshows\"</h2>")
            gr.Markdown(
                """
                <div style='font-size: 28px; text-align: center; background:#E3F2FD;
                             padding:28px; border-radius:16px; min-height: 150px;'>
                  <b>This is a "Slideshow" step.</b><br><br>
                  Some apps are just for reading. Your only task is to click the "Next" button to move to the next step.
                </div>
                """
            )
            step_1_next = gr.Button("Next Step ▶️", variant="primary")

        # Step 2
        with gr.Column(visible=False) as step_2_container:
            gr.Markdown("<h2 style='text-align:center;'>Step 2: How to Use \"Interactive Demos\"</h2>")
            gr.Markdown(
                """
                <div style='font-size: 20px; text-align: left; background:#FFF3E0;
                            padding:20px; border-radius:16px;'>
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
                label="🔮 Predicted Exam Score", elem_id="prediction_output_textbox", interactive=False
            )

            # Added scroll_to_output so the page scrolls to the prediction result automatically.
            # (Optional) If you prefer a smoother centered scroll, uncomment js=... line below instead or in addition.
            go.click(
                predict_exam,
                [s_hours, s_sleep, s_att],
                out,
                scroll_to_output=True,
                # js="()=>{document.getElementById('prediction_output_textbox').scrollIntoView({behavior:'smooth', block:'center'});}"
            )

            gr.HTML("<hr style='margin: 15px 0;'>")
            with gr.Row():
                step_2_back = gr.Button("◀️ Back")
                step_2_next = gr.Button("Finish Tutorial ▶️", variant="primary")

        # Step 3
        with gr.Column(visible=False) as step_3_container:
            gr.Markdown(
                """
                <div style='text-align:center;'>
                  <h2 style='text-align:center; font-size: 2.5rem;'>✅ Tutorial Complete!</h2>
                  <div style='font-size: 1.5rem; background:#E8F5E9; padding:28px; border-radius:16px;
                              border: 2px solid #4CAF50;'>
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

        step_1_next.click(
            fn=create_nav_generator(step_1_container, step_2_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_back.click(
            fn=create_nav_generator(step_2_container, step_1_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_next.click(
            fn=create_nav_generator(step_2_container, step_3_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_3_back.click(
            fn=create_nav_generator(step_3_container, step_2_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )

    return demo


def launch_tutorial_app(height: int = 950, share: bool = False, debug: bool = False) -> None:
    """Convenience wrapper to create and launch the tutorial app inline."""
    demo = create_tutorial_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the tutorial app.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

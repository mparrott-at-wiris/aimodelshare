"""
AI Consequences - Gradio application for the Justice & Equity Challenge.

This app teaches:
1. The consequences of wrong AI predictions in criminal justice
2. Understanding false positives and false negatives
3. The ethical stakes of relying on AI for high-stakes decisions

Structure:
- Factory function `create_ai_consequences_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_ai_consequences_app()` launches it inline (for notebooks)
"""
import contextlib
import os


def create_ai_consequences_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the AI Consequences Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the AI consequences app. Install with `pip install gradio`."
        ) from e
    
    css = """
    .large-text {
        font-size: 20px !important;
    }
    .warning-box {
        background: #fef2f2 !important;
        border-left: 6px solid #dc2626 !important;
    }
    """
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("# ⚠️ What If the AI Was Wrong?")
        gr.Markdown(
            """
            You just made decisions based on an AI's predictions.  
            But AI systems are not perfect. Let's explore what happens when they make mistakes.
            """
        )
        gr.Markdown("---")
        
        # Step 1: Introduction
        with gr.Column(visible=True) as step_1:
            gr.Markdown("## The Stakes of AI Predictions")
            gr.Markdown(
                """
                In the previous exercise, you relied on an AI system to predict which defendants were **High**, **Medium**, or **Low** risk of re-offending.

                **But what if those predictions were incorrect?**

                AI systems make two types of errors that have very different consequences:

                - **False Positives** – Incorrectly predicting HIGH risk  
                - **False Negatives** – Incorrectly predicting LOW risk  

                Let's examine each type of error and its real-world impact.
                """
            )
            step_1_next = gr.Button("Next: False Positives ▶️", variant="primary", size="lg")
        
        # Step 2: False Positives
        with gr.Column(visible=False) as step_2:
            gr.Markdown("## 🔴 False Positives: Predicting Danger Where None Exists")
            gr.Markdown(
                """
                **What is a False Positive?**  
                A *false positive* occurs when the AI predicts someone is **HIGH RISK**, but they would **not** have actually re-offended if released.

                **Example Scenario:**  
                - Sarah was flagged as **HIGH RISK**  
                - Based on this, the judge kept her in prison  
                - In reality, Sarah would have rebuilt her life and never committed another crime

                **The Human Cost:**
                - Innocent people spend unnecessary time in prison
                - Families are separated longer than needed
                - Job opportunities and rehabilitation are delayed
                - Trust in the justice system erodes
                - Disproportionate impact on marginalized communities

                **Key Point:** False positives mean the AI is being **too cautious**, keeping people locked up who should be free.
                """
            )
            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Next: False Negatives ▶️", variant="primary", size="lg")
        
        # Step 3: False Negatives
        with gr.Column(visible=False) as step_3:
            gr.Markdown("## 🔵 False Negatives: Missing Real Danger")
            gr.Markdown(
                """
                **What is a False Negative?**  
                A *false negative* occurs when the AI predicts someone is **LOW RISK**, but they **do** actually re-offend after being released.

                **Example Scenario:**  
                - James was flagged as **LOW RISK**  
                - Based on this, the judge released him  
                - Unfortunately, James committed another serious crime

                **The Human Cost:**
                - New victims of preventable crimes
                - Loss of public trust in the justice system
                - Media scrutiny and backlash against judges
                - Political pressure to be “tough on crime”
                - Potential harm to communities and families

                **Key Point:** False negatives mean the AI is being **too lenient**, releasing people who pose a real danger.
                """
            )
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("Next: The Dilemma ▶️", variant="primary", size="lg")
        
        # Step 4: The Dilemma (refactored to pure Markdown)
        with gr.Column(visible=False) as step_4:
            gr.Markdown(
                """
                ## ⚖️ The Impossible Balance

                **Every AI System Makes Trade-offs**

                No AI system can eliminate both types of errors.

                **If you make the AI more cautious:**
                - ✅ Fewer false negatives (fewer dangerous people released)
                - ❌ More false positives (more innocent people kept in prison)

                **If you make the AI more lenient:**
                - ✅ Fewer false positives (more innocent people freed)
                - ❌ More false negatives (more dangerous people released)

                **Ethical Question:**  
                Which mistake is worse?  
                - Keeping innocent people in prison?  
                - Releasing dangerous individuals?

                There is no universally “correct” answer. Different societies weigh these trade-offs differently.

                **Why Understanding AI Matters:**  
                We need to know how these systems work to make informed decisions about when and how to use them.
                """
            )
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("Continue to Learn About AI ▶️", variant="primary", size="lg")
        
        # Step 5: Completion (pure Markdown)
        with gr.Column(visible=False) as step_5:
            gr.Markdown(
                """
                ## ✅ Section Complete!

                You now understand the consequences of AI errors in high-stakes decisions.

                **Next up:** Learn what AI actually is and how these prediction systems work.

                This knowledge will help you understand how to build better, more ethical AI systems.

                ### ⬇️ Continue Below
                Find the next section below to continue your journey.
                """
            )
            back_to_dilemma_btn = gr.Button("◀️ Back to Review")
        
        # Navigation logic
        step_1_next.click(
            lambda: (gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), 
                    gr.update(visible=False), gr.update(visible=False)),
            inputs=None,
            outputs=[step_1, step_2, step_3, step_4, step_5]
        )
        
        step_2_back.click(
            lambda: (gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), 
                    gr.update(visible=False), gr.update(visible=False)),
            inputs=None,
            outputs=[step_1, step_2, step_3, step_4, step_5]
        )
        
        step_2_next.click(
            lambda: (gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), 
                    gr.update(visible=False), gr.update(visible=False)),
            inputs=None,
            outputs=[step_1, step_2, step_3, step_4, step_5]
        )
        
        step_3_back.click(
            lambda: (gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), 
                    gr.update(visible=False), gr.update(visible=False)),
            inputs=None,
            outputs=[step_1, step_2, step_3, step_4, step_5]
        )
        
        step_3_next.click(
            lambda: (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), 
                    gr.update(visible=True), gr.update(visible=False)),
            inputs=None,
            outputs=[step_1, step_2, step_3, step_4, step_5]
        )
        
        step_4_back.click(
            lambda: (gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), 
                    gr.update(visible=False), gr.update(visible=False)),
            inputs=None,
            outputs=[step_1, step_2, step_3, step_4, step_5]
        )
        
        step_4_next.click(
            lambda: (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), 
                    gr.update(visible=False), gr.update(visible=True)),
            inputs=None,
            outputs=[step_1, step_2, step_3, step_4, step_5]
        )
        
        back_to_dilemma_btn.click(
            lambda: (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), 
                    gr.update(visible=True), gr.update(visible=False)),
            inputs=None,
            outputs=[step_1, step_2, step_3, step_4, step_5]
        )
    
    return demo


def launch_ai_consequences_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    """Convenience wrapper to create and launch the AI consequences app inline."""
    demo = create_ai_consequences_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the AI consequences app.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

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
            "ai_confidence": "85%"
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
            "ai_confidence": "72%"
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
            "ai_confidence": "68%"
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
            "ai_confidence": "70%"
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
            "ai_confidence": "91%"
        }
    ]
    
    return profiles


def create_judge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the You Be the Judge Gradio Blocks app (not launched yet)."""
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
        """Format a defendant profile for display."""
        risk_color = {
            "High": "#ef4444",
            "Medium": "#f59e0b", 
            "Low": "#22c55e"
        }
        
        color = risk_color.get(profile["ai_risk"], "#6b7280")
        
        return f"""
        <div style='background:#f9fafb; padding:20px; border-radius:12px; border-left: 6px solid {color};'>
            <h3 style='margin-top:0; color:#1f2937;'>Defendant #{profile['id']}: {profile['name']}</h3>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 16px;'>
                <div><b>Age:</b> {profile['age']}</div>
                <div><b>Gender:</b> {profile['gender']}</div>
                <div><b>Race:</b> {profile['race']}</div>
                <div><b>Prior Offenses:</b> {profile['prior_offenses']}</div>
                <div style='grid-column: span 2;'><b>Current Charge:</b> {profile['current_charge']}</div>
            </div>
            <div style='margin-top:16px; padding:12px; background:white; border-radius:8px;'>
                <b>🤖 AI Risk Assessment:</b> 
                <span style='color:{color}; font-size:20px; font-weight:bold;'>{profile['ai_risk']} Risk</span>
                <span style='color:#6b7280; margin-left:8px;'>(Confidence: {profile['ai_confidence']})</span>
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
        <div style='background:#dbeafe; padding:20px; border-radius:12px;'>
            <h3 style='margin-top:0;'>📊 Your Decisions Summary</h3>
            <div style='font-size:18px;'>
                <p><b>Prisoners Released:</b> {released} of {len(decisions)}</p>
                <p><b>Prisoners Kept in Prison:</b> {kept} of {len(decisions)}</p>
            </div>
        </div>
        """
        return summary
    
    css = """
    .decision-button {
        font-size: 18px !important;
        padding: 12px 24px !important;
    }
    """
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("<h1 style='text-align:center;'>⚖️ You Be the Judge</h1>")
        gr.Markdown(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #fef3c7; border-radius: 12px; border: 2px solid #f59e0b;'>
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
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )
        
        # Introduction
        with gr.Column(visible=True) as intro_section:
            gr.Markdown("<h2 style='text-align:center;'>📋 The Scenario</h2>")
            gr.Markdown(
                """
                <div style='font-size: 18px; background:#e0f2fe; padding:24px; border-radius:12px;'>
                You are a judge in a busy criminal court. Due to prison overcrowding, you must decide 
                which defendants can be safely released.<br><br>
                
                To help you, the court has implemented an AI system that predicts the risk of each 
                defendant committing new crimes if released. The AI categorizes defendants as:<br><br>
                
                <ul style='font-size:18px;'>
                    <li><span style='color:#ef4444; font-weight:bold;'>High Risk</span> - Likely to re-offend</li>
                    <li><span style='color:#f59e0b; font-weight:bold;'>Medium Risk</span> - Moderate chance of re-offending</li>
                    <li><span style='color:#22c55e; font-weight:bold;'>Low Risk</span> - Unlikely to re-offend</li>
                </ul>
                
                <b>Remember:</b> Your decisions affect real people's lives and public safety.
                </div>
                """
            )
            start_btn = gr.Button("Begin Making Decisions ▶️", variant="primary", size="lg")
        
        # Defendant profiles section
        with gr.Column(visible=False) as profiles_section:
            gr.Markdown("<h2 style='text-align:center;'>👥 Defendant Profiles</h2>")
            gr.Markdown(
                """
                <div style='text-align:center; font-size:16px; background:#f3f4f6; padding:12px; border-radius:8px;'>
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
                            elem_classes=["decision-button"]
                        )
                        keep_btn = gr.Button(
                            "✗ Keep in Prison",
                            variant="secondary",
                            elem_classes=["decision-button"]
                        )
                    
                    decision_status = gr.Markdown("")
                    
                    # Wire up buttons
                    release_btn.click(
                        lambda p_id=profile["id"]: make_decision(p_id, "Release"),
                        inputs=None,
                        outputs=decision_status
                    )
                    keep_btn.click(
                        lambda p_id=profile["id"]: make_decision(p_id, "Keep in Prison"),
                        inputs=None,
                        outputs=decision_status
                    )
                    
                    gr.HTML("<hr style='margin:24px 0;'>")
            
            # Summary section
            summary_display = gr.HTML("")
            show_summary_btn = gr.Button("📊 Show My Decisions Summary", variant="primary", size="lg")
            show_summary_btn.click(get_summary, inputs=None, outputs=summary_display)
            
            gr.HTML("<br>")
            complete_btn = gr.Button("Complete This Section ▶️", variant="primary", size="lg")
        
        # Completion section
        with gr.Column(visible=False) as complete_section:
            gr.Markdown(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>✅ Decisions Complete!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        You've made your decisions based on the AI's recommendations.<br><br>
                        But here's the critical question:<br><br>
                        <h2 style='color:#dc2626; margin:16px 0;'>What if the AI was wrong?</h2>
                        <p style='font-size:1.1rem;'>
                        Continue to the next section below to explore the consequences of 
                        trusting AI predictions in high-stakes situations.
                        </p>
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 SCROLL DOWN 👇</h1>
                        <p style='font-size:1.1rem;'>Find the next section below to continue your journey.</p>
                        </div>
                </div>
                """
            )
            back_to_profiles_btn = gr.Button("◀️ Back to Review Decisions")
        
        # --- NAVIGATION LOGIC (GENERATOR-BASED) ---
        
        # This list must be defined *after* all the components
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

        # --- Wire up each button to its own unique generator ---
        start_btn.click(
            fn=create_nav_generator(intro_section, profiles_section), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        complete_btn.click(
            fn=create_nav_generator(profiles_section, complete_section), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        back_to_profiles_btn.click(
            fn=create_nav_generator(complete_section, profiles_section), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
    
    return demo


def launch_judge_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    """Convenience wrapper to create and launch the judge app inline."""
    demo = create_judge_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the judge app.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

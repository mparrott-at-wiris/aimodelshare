"""
What is AI - Gradio application for the Justice & Equity Challenge.

This app teaches:
1. A simple, non-technical explanation of what AI is
2. How predictive models work (Input → Model → Output)
3. Real-world examples and connections to the justice challenge

Structure:
- Factory function `create_what_is_ai_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_what_is_ai_app()` launches it inline (for notebooks)
"""
import contextlib
import os

def _create_simple_predictor():
    """Create a simple demonstration predictor for teaching purposes."""
    def predict_outcome(age, priors, severity):
        """Simple rule-based predictor for demonstration."""
        
        
        # Simple scoring logic for demonstration
        score = 0
        
        # Age factor (younger = higher risk in this simple model)
        if age < 25:
            score += 3
        elif age < 35:
            score += 2
        else:
            score += 1
        
        # Prior offenses factor
        if priors >= 3:
            score += 3
        elif priors >= 1:
            score += 2
        else:
            score += 0
        
        # Severity factor
        severity_map = {"Minor": 1, "Moderate": 2, "Serious": 3}
        score += severity_map.get(severity, 2)
        
        # Determine risk level
        if score >= 7:
            risk = "High Risk"
            color = "#dc2626"
            emoji = "🔴"
        elif score >= 4:
            risk = "Medium Risk"
            color = "#f59e0b"
            emoji = "🟡"
        else:
            risk = "Low Risk"
            color = "#16a34a"
            emoji = "🟢"
        
        return f"""
        <div style='background:white; padding:24px; border-radius:12px; border:3px solid {color}; text-align:center;'>
            <h2 style='color:{color}; margin:0; font-size:2.5rem;'>{emoji} {risk}</h2>
            <p style='font-size:18px; color:#6b7280; margin-top:12px;'>Risk Score: {score}/9</p>
        </div>
        """
    
    return predict_outcome


def create_what_is_ai_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the What is AI Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)

    except ImportError as e:
        raise ImportError(
            "Gradio is required for the what is AI app. Install with `pip install gradio`."
        ) from e
    
    predict_outcome = _create_simple_predictor()
    
    css = """
    .large-text {
        font-size: 20px !important;
    }
    """
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("<h1 style='text-align:center;'>🤖 What is AI, Anyway?</h1>")
        gr.HTML(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #e0e7ff; border-radius: 12px; border: 2px solid #6366f1;'>
            Before you can build better AI systems, you need to understand what AI actually is.<br>
            Don't worry - we'll explain it in simple, everyday terms!
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")
        
        # --- This is the new loading screen ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Loading...</h2>
                </div>
                """
            )
        
        # Step 1: Introduction
        with gr.Column(visible=True) as step_1:
            gr.Markdown("<h2 style='text-align:center;'>🎯 A Simple Definition</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#dbeafe; padding:28px; border-radius:16px;'>
                <p><b style='font-size:24px;'>Artificial Intelligence (AI) is just a fancy name for:</b></p>
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0; border:3px solid #0284c7;'>
                    <h2 style='text-align:center; color:#0284c7; margin:0; font-size:2rem;'>
                    A system that makes predictions based on patterns
                    </h2>
                </div>
                <p>That's it! Let's break down what that means...</p>
                <h3 style='color:#0369a1; margin-top:24px;'>Think About How YOU Make Predictions:</h3>
                <ul style='font-size:19px; margin-top:12px;'>
                    <li><b>Weather:</b> Dark clouds → You predict rain → You bring an umbrella</li>
                    <li><b>Traffic:</b> Rush hour time → You predict congestion → You leave early</li>
                    <li><b>Movies:</b> Actor you like → You predict you'll enjoy it → You watch it</li>
                </ul>
                <div style='background:#fef3c7; padding:20px; border-radius:8px; margin-top:24px; border-left:6px solid #f59e0b;'>
                    <p style='font-size:18px; margin:0;'><b>AI does the same thing, but using data and math 
                    instead of human experience and intuition.</b></p>
                </div>
                </div>
                """
            )
            step_1_next = gr.Button("Next: The AI Formula ▶️", variant="primary", size="lg")
        
        # Step 2: The Three-Part Formula
        with gr.Column(visible=False) as step_2:
            gr.Markdown("<h2 style='text-align:center;'>📐 The Three-Part Formula</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#f0fdf4; padding:28px; border-radius:16px;'>
                <p>Every AI system works the same way, following this simple formula:</p>
                <div style='background:white; padding:32px; border-radius:12px; margin:24px 0; text-align:center;'>
                    <div style='display:inline-block; background:#dbeafe; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#0369a1;'>1️⃣ INPUT</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>Data goes in</p>
                    </div>
                    <div style='display:inline-block; font-size:2rem; margin:0 16px; color:#6b7280;'>→</div>
                    <div style='display:inline-block; background:#fef3c7; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#92400e;'>2️⃣ MODEL</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>AI processes it</p>
                    </div>
                    <div style='display:inline-block; font-size:2rem; margin:0 16px; color:#6b7280;'>→</div>
                    <div style='display:inline-block; background:#f0fdf4; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#15803d;'>3️⃣ OUTPUT</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>Prediction comes out</p>
                    </div>
                </div>
                <h3 style='color:#15803d; margin-top:32px;'>Real-World Examples:</h3>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Input:</b> Photo of a dog<br>
                    <b style='color:#92400e;'>Model:</b> Image recognition AI<br>
                    <b style='color:#15803d;'>Output:</b> "This is a Golden Retriever"
                    </p>
                </div>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Input:</b> "How's the weather?"<br>
                    <b style='color:#92400e;'>Model:</b> Language AI (like ChatGPT)<br>
                    <b style='color:#15803d;'>Output:</b> A helpful response
                    </p>
                </div>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Input:</b> Person's criminal history<br>
                    <b style='color:#92400e;'>Model:</b> Risk assessment AI<br>
                    <b style='color:#15803d;'>Output:</b> "High Risk" or "Low Risk"
                    </p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Next: How Models Learn ▶️", variant="primary", size="lg")
        
        # Step 3: How Models Learn (Shorter Version - Direct Intro)
        with gr.Column(visible=False) as step_3:
            gr.Markdown("<h2 style='text-align:center;'>🧠 How Does an AI Model Learn?</h2>")
            
            gr.HTML(
                """
                <div style='font-size: 19px; background:#fef3c7; padding:28px; border-radius:16px;'>
                
                <h3 style='color:#92400e; margin-top:0;'>1. It Learns from Examples</h3>
                
                <p>An AI model isn't programmed with answers. Instead, it's trained on a huge number of examples, and it learns how to find the answers on its own.</p>
                <p>In our justice scenario, this means feeding the model thousands of past cases (<b>examples</b>) to teach it how to find the <b>patterns</b> that connect a person's details to their [...]
                
                <hr style='margin:24px 0;'>
                
                <h3 style='color:#92400e;'>2. The Training Process</h3>
                <p>The AI "trains" by looping through historical data (past cases) millions of times:</p>
                
                <div style='margin:24px 0; padding:20px; background:#fff; border-radius:8px;'>
                    <div style='display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap;'>
                        <div style='background:#dbeafe; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#0369a1;'>1. INPUT<br>EXAMPLES</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>2. MODEL<br>GUESSES</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>3. CHECK<br>ANSWER</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>4. ADJUST<br>WEIGHTS</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#15803d;'>LEARNED<br>MODEL</b>
                        </div>
                    </div>
                </div>
                
                <p style='margin-top:20px;'>During the <b>"Adjust"</b> step, the model changes its internal rules (called <b>"weights"</b>) to get closer to the right answer. 
                   For example, it learns <b>how much</b> "prior offenses" should matter more than "age".</p>
                
                <hr style='margin:24px 0;'>

                <h3 style='color:#dc2626;'>⚠️ The Ethical Challenge</h3>
                <div style='font-size: 18px; background:#fef2f2; padding:24px; border-radius:12px; border-left:6px solid #dc2626;'>
                    <p style='margin:0;'><b>Here's the critical problem:</b> The model *only* learns from the data.
                    If the historical data is biased (e.g., certain groups were arrested more often), 
                    the model will learn those biased patterns.
                    <br><br>
                    <b>The model doesn't know "fairness" or "justice," it only knows patterns.</b>
                    </p>
                </div>

                </div>
            """
            )
            
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("Next: Try It Yourself ▶️", variant="primary", size="lg")
        
        # Step 4: Interactive Demo
        with gr.Column(visible=False) as step_4:
            gr.Markdown("<h2 style='text-align:center;'>🎮 Try It Yourself!</h2>")
            gr.Markdown(
                """
                <div style='font-size: 18px; background:#fef3c7; padding:24px; border-radius:12px; text-align:center;'>
                <p style='margin:0;'><b>Let's use a simple AI model to predict criminal risk.</b><br>
                Adjust the inputs below and see how the model's prediction changes!</p>
                </div>
                """
            )
            gr.HTML("<br>")
            
            gr.Markdown("<h3 style='text-align:center; color:#0369a1;'>1️⃣ INPUT: Adjust the Data</h3>")
            
            with gr.Row():
                age_slider = gr.Slider(
                    minimum=18, 
                    maximum=65, 
                    value=25, 
                    step=1, 
                    label="Age",
                    info="Defendant's age"
                )
                priors_slider = gr.Slider(
                    minimum=0, 
                    maximum=10, 
                    value=2, 
                    step=1, 
                    label="Prior Offenses",
                    info="Number of previous crimes"
                )
            
            severity_dropdown = gr.Dropdown(
                choices=["Minor", "Moderate", "Serious"],
                value="Moderate",
                label="Current Charge Severity",
                info="How serious is the current charge?"
            )
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown("<h3 style='text-align:center; color:#92400e;'>2️⃣ MODEL: Process the Data</h3>")
            
            predict_btn = gr.Button("🔮 Run AI Prediction", variant="primary", size="lg")
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown("<h3 style='text-align:center; color:#15803d;'>3️⃣ OUTPUT: See the Prediction</h3>")
            
            prediction_output = gr.HTML(
                """
                <div style='background:#f3f4f6; padding:40px; border-radius:12px; text-align:center;'>
                    <p style='color:#6b7280; font-size:18px; margin:0;'>
                    Click "Run AI Prediction" above to see the result
                    </p>
                </div>
                """
            )
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown(
                """
                <div style='background:#e0f2fe; padding:20px; border-radius:12px; font-size:18px;'>
                <b>What You Just Did:</b><br><br>
                You used a very simple AI model! You provided <b style='color:#0369a1;'>input data</b> 
                (age, priors, severity), the <b style='color:#92400e;'>model processed it</b> using rules 
                and patterns, and it produced an <b style='color:#15803d;'>output prediction</b>.<br><br>
                Real AI models are more complex, but they work on the same principle!
                </div>
                """
            )
            
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("Next: Connection to Justice ▶️", variant="primary", size="lg")
        
        # Step 5: Connection to the Challenge
        with gr.Column(visible=False) as step_5:
            gr.Markdown("<h2 style='text-align:center;'>🔗 Connecting to Criminal Justice</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#faf5ff; padding:28px; border-radius:16px;'>
                <p><b>Remember the risk prediction you used earlier as a judge?</b></p>
                
                <p style='margin-top:20px;'>That was a real-world example of AI in action:</p>
                
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0; border:3px solid #9333ea;'>
                    <p style='font-size:18px; margin-bottom:16px;'>
                    <b style='color:#0369a1;'>INPUT:</b> Defendant's information<br>
                    <span style='margin-left:24px; color:#6b7280;'>• Age, race, gender, prior offenses, charge details</span>
                    </p>
                    
                    <p style='font-size:18px; margin:16px 0;'>
                    <b style='color:#92400e;'>MODEL:</b> Risk assessment algorithm<br>
                    <span style='margin-left:24px; color:#6b7280;'>• Trained on historical criminal justice data</span><br>
                    <span style='margin-left:24px; color:#6b7280;'>• Looks for patterns in who re-offended in the past</span>
                    </p>
                    
                    <p style='font-size:18px; margin-top:16px; margin-bottom:0;'>
                    <b style='color:#15803d;'>OUTPUT:</b> Risk prediction<br>
                    <span style='margin-left:24px; color:#6b7280;'>• "High Risk", "Medium Risk", or "Low Risk"</span>
                    </p>
                </div>
                
                <h3 style='color:#7e22ce; margin-top:32px;'>Why This Matters for Ethics:</h3>
                
                <div style='background:#fef2f2; padding:20px; border-radius:8px; margin-top:16px; border-left:6px solid #dc2626;'>
                    <ul style='font-size:18px; margin:8px 0;'>
                        <li>The <b>input data</b> might contain historical biases</li>
                        <li>The <b>model</b> learns patterns from potentially unfair past decisions</li>
                        <li>The <b>output predictions</b> can perpetuate discrimination</li>
                    </ul>
                </div>
                
                <div style='background:#dbeafe; padding:20px; border-radius:8px; margin-top:24px;'>
                    <p style='font-size:18px; margin:0;'>
                    <b>Understanding how AI works is the first step to building fairer systems.</b><br><br>
                    Now that you know what AI is, you're ready to help design better models that 
                    are more ethical and less biased!
                    </p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_5_back = gr.Button("◀️ Back", size="lg")
                step_5_next = gr.Button("Complete This Section ▶️", variant="primary", size="lg")
        
        # Step 6: Completion
        with gr.Column(visible=False) as step_6:
            gr.HTML(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>🎓 You Now Understand AI!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        <p><b>Congratulations!</b> You now know:</p>
                        
                        <ul style='font-size:1.1rem; text-align:left; max-width:600px; margin:20px auto;'>
                            <li>What AI is (a prediction system)</li>
                            <li>How it works (Input → Model → Output)</li>
                            <li>How AI models learn from data</li>
                            <li>Why it matters for criminal justice</li>
                            <li>The ethical implications of AI decisions</li>
                        </ul>
                        
                        <p style='margin-top:32px;'><b>Next Steps:</b></p>
                        <p>In the following sections, you'll learn how to build and improve AI models 
                        to make them more fair and ethical.</p>
                        
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 SCROLL DOWN 👇</h1>
                        <p style='font-size:1.1rem;'>Continue to the next section below.</p>
                    </div>
                </div>
                """
            )
            back_to_connection_btn = gr.Button("◀️ Back to Review")
        
        
        # --- PREDICTION BUTTON LOGIC ---
        predict_btn.click(
            predict_outcome,
            inputs=[age_slider, priors_slider, severity_dropdown],
            outputs=prediction_output,
            show_progress="full",
            scroll_to_output=True,
            # js="()=>{document.querySelector('[data-testid=\"component-html\"]').scrollIntoView({behavior:'smooth', block:'center'});}"
        )
        
        # --- CORRECTED NAVIGATION LOGIC (GENERATOR-BASED) ---
        
        # This list must be defined *after* all the components
        all_steps = [step_1, step_2, step_3, step_4, step_5, step_6, loading_screen]

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
        step_1_next.click(
            fn=create_nav_generator(step_1, step_2), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_back.click(
            fn=create_nav_generator(step_2, step_1), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_next.click(
            fn=create_nav_generator(step_2, step_3), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_3_back.click(
            fn=create_nav_generator(step_3, step_2), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_3_next.click(
            fn=create_nav_generator(step_3, step_4), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_4_back.click(
            fn=create_nav_generator(step_4, step_3), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_4_next.click(
            fn=create_nav_generator(step_4, step_5), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_5_back.click(
            fn=create_nav_generator(step_5, step_4), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_5_next.click(
            fn=create_nav_generator(step_5, step_6), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        back_to_connection_btn.click(
            fn=create_nav_generator(step_6, step_5), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        # --- END NAVIGATION LOGIC ---
    
    return demo


def launch_what_is_ai_app(height: int = 1100, share: bool = False, debug: bool = False) -> None:
    """Convenience wrapper to create and launch the what is AI app inline."""
    demo = create_what_is_ai_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the what is AI app.") from e
    
    # This is the original wrapper, designed for use in a notebook (like Colab)
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

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

        # Theme-aware prediction card: background from theme, border color from score
        return f"""
        <div class="prediction-card" style="border-color:{color};">
            <h2 class="prediction-title" style="color:{color};">{emoji} {risk}</h2>
            <p class="prediction-score">Risk Score: {score}/9</p>
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
        /* -------------------------------------------- */
        /* TYPOGRAPHY / UTILITY CLASSES                 */
        /* -------------------------------------------- */
        .large-text {
            font-size: 20px !important;
        }

        .loading-title {
            font-size: 2rem;
            color: var(--secondary-text-color);
        }

        /* Labels for Input / Model / Output headings & inline labels
          Use the same palette as the training-process visual */
        .io-step-label-input,
        .io-label-input {
            color: #0369a1;
            font-weight: 700;
        }

        .io-step-label-model,
        .io-label-model {
            color: #92400e;
            font-weight: 700;
        }

        .io-step-label-output,
        .io-label-output {
            color: #15803d;
            font-weight: 700;
        }

        /* INPUT / MODEL / OUTPUT chips row */
        .io-chip-row {
            text-align: center;
        }

        .io-chip {
            display: inline-block;
            padding: 16px 24px;
            border-radius: 8px;
            margin: 8px;
            /* Base: blend with theme background so it looks okay in both modes */
            background-color: color-mix(in srgb, var(--block-background-fill) 60%, #ffffff 40%);
        }

        /* Light-mode tints for each chip */
        .io-chip-input {
            background-color: color-mix(in srgb, #dbeafe 75%, var(--block-background-fill) 25%);
        }

        .io-chip-model {
            background-color: color-mix(in srgb, #fef3c7 75%, var(--block-background-fill) 25%);
        }

        .io-chip-output {
            background-color: color-mix(in srgb, #dcfce7 75%, var(--block-background-fill) 25%);
        }

        .io-arrow {
            display: inline-block;
            font-size: 2rem;
            margin: 0 16px;
            color: var(--secondary-text-color);
            vertical-align: middle;
        }

        /* -------------------------------------------- */
        /* CONTENT CONTAINERS                           */
        /* -------------------------------------------- */

        .ai-intro-box {
            text-align: center;
            font-size: 18px;
            max-width: 900px;
            margin: auto;
            padding: 20px;
            border-radius: 12px;

            background-color: var(--block-background-fill);
            color: var(--body-text-color);
            border: 2px solid #6366f1;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }

        .step-card {
            font-size: 20px;
            padding: 28px;
            border-radius: 16px;

            background-color: var(--block-background-fill);
            color: var(--body-text-color);
            border: 1px solid var(--border-color-primary);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        }

        .step-card-soft-blue {
            border-width: 2px;
            border-color: #6366f1;
        }

        .step-card-green {
            border-width: 2px;
            border-color: #16a34a;
        }

        .step-card-amber {
            border-width: 2px;
            border-color: #f59e0b;
        }

        .step-card-purple {
            border-width: 2px;
            border-color: #9333ea;
        }

        .inner-card {
            background-color: var(--body-background-fill);
            color: var(--body-text-color);
            padding: 24px;
            border-radius: 12px;
            margin: 24px 0;
            border: 1px solid var(--border-color-primary);
        }

        .inner-card-emphasis-blue {
            border-width: 3px;
            border-color: #0284c7;
        }

        .inner-card-wide {
            background-color: var(--body-background-fill);
            color: var(--body-text-color);
            padding: 20px;
            border-radius: 8px;
            margin: 16px 0;
            border: 1px solid var(--border-color-primary);
        }

        .keypoint-box {
            background-color: var(--block-background-fill);
            color: var(--body-text-color);
            padding: 24px;
            border-radius: 12px;
            margin-top: 20px;
            border-left: 6px solid #dc2626;
        }

        .highlight-soft {
            background-color: var(--block-background-fill);
            color: var(--body-text-color);
            padding: 20px;
            border-radius: 12px;
            font-size: 18px;
            border: 1px solid var(--border-color-primary);
        }

        .completion-box {
            font-size: 1.3rem;
            padding: 28px;
            border-radius: 16px;

            background-color: var(--block-background-fill);
            color: var(--body-text-color);
            border: 2px solid #0284c7;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }

        .prediction-card {
            background-color: var(--block-background-fill);
            color: var(--body-text-color);
            padding: 24px;
            border-radius: 12px;
            border: 3px solid var(--border-color-primary);
            text-align: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        .prediction-title {
            margin: 0;
            font-size: 2.5rem;
        }

        .prediction-score {
            font-size: 18px;
            margin-top: 12px;
            color: var(--secondary-text-color);
        }

        .prediction-placeholder {
            background-color: var(--block-background-fill);
            color: var(--secondary-text-color);
            padding: 40px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid var(--border-color-primary);
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

            /* Blend with page background so it fits both modes */
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
            .ai-intro-box,
            .step-card,
            .inner-card,
            .inner-card-wide,
            .keypoint-box,
            .highlight-soft,
            .completion-box,
            .prediction-card,
            .prediction-placeholder {
                background-color: #2D323E;
                color: white;
                border-color: #555555;
                box-shadow: none;
            }

            .inner-card,
            .inner-card-wide {
                background-color: #181B22;
            }

            #nav-loading-overlay {
                background: rgba(15, 23, 42, 0.9);
            }

            .nav-spinner {
                border-color: rgba(148, 163, 184, 0.4);
                border-top-color: var(--color-accent);
            }

            /* Dark-mode backgrounds for IO chips – more contrast with light labels */
            .io-chip-input {
                background-color: color-mix(in srgb, #1d4ed8 35%, #020617 65%);
            }

            .io-chip-model {
                background-color: color-mix(in srgb, #b45309 40%, #020617 60%);
            }

            .io-chip-output {
                background-color: color-mix(in srgb, #15803d 40%, #020617 60%);
            }

            .io-arrow {
                color: #e5e7eb;
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

        gr.Markdown("<h1 style='text-align:center;'>🤖 What is AI, Anyway?</h1>")
        gr.HTML(
            """
            <div class='ai-intro-box'>
              Before you can build better AI systems, you need to understand what AI actually is.<br>
              Don't worry - we'll explain it in simple, everyday terms!
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

        # Step 1: Introduction
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            gr.Markdown("<h2 style='text-align:center;'>🎯 A Simple Definition</h2>")
            gr.HTML(
                """
                <div class='step-card step-card-soft-blue'>
                  <p><b style='font-size:24px;'>Artificial Intelligence (AI) is just a fancy name for:</b></p>
                  <div class='inner-card inner-card-emphasis-blue'>
                      <h2 style='text-align:center; margin:0; font-size:2rem;'>
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
                  <div class='highlight-soft' style='border-left:6px solid #f59e0b;'>
                      <p style='font-size:18px; margin:0;'>
                        <b>AI does the same thing, but using data and math 
                        instead of human experience and intuition.</b>
                      </p>
                  </div>
                </div>
                """
            )
            step_1_next = gr.Button("Next: The AI Formula ▶️", variant="primary", size="lg")

        # Step 2: The Three-Part Formula
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            gr.Markdown("<h2 style='text-align:center;'>📐 The Three-Part Formula</h2>")
            gr.HTML(
                """
                <div class='step-card step-card-green'>
                  <p>Every AI system works the same way, following this simple formula:</p>

                  <div class='inner-card'>
                      <div class='io-chip-row'>
                          <div class='io-chip io-chip-input'>
                              <!-- INPUT uses same palette as training visual -->
                              <h3 class='io-step-label-input' style='margin:0;'>1️⃣ INPUT</h3>
                              <p style='margin:8px 0 0 0; font-size:16px;'>Data goes in</p>
                          </div>

                          <span class='io-arrow'>→</span>

                          <div class='io-chip io-chip-model'>
                              <!-- MODEL -->
                              <h3 class='io-step-label-model' style='margin:0;'>2️⃣ MODEL</h3>
                              <p style='margin:8px 0 0 0; font-size:16px;'>AI processes it</p>
                          </div>

                          <span class='io-arrow'>→</span>

                          <div class='io-chip io-chip-output'>
                              <!-- OUTPUT -->
                              <h3 class='io-step-label-output' style='margin:0;'>3️⃣ OUTPUT</h3>
                              <p style='margin:8px 0 0 0; font-size:16px;'>Prediction comes out</p>
                          </div>
                      </div>
                  </div>

                  <h3 style='color:#15803d; margin-top:32px;'>Real-World Examples:</h3>

                  <div class='inner-card-wide'>
                      <p style='margin:0; font-size:18px;'>
                      <b class='io-label-input'>Input:</b> Photo of a dog<br>
                      <b class='io-label-model'>Model:</b> Image recognition AI<br>
                      <b class='io-label-output'>Output:</b> "This is a Golden Retriever"
                      </p>
                  </div>

                  <div class='inner-card-wide'>
                      <p style='margin:0; font-size:18px;'>
                      <b class='io-label-input'>Input:</b> "How's the weather?"<br>
                      <b class='io-label-model'>Model:</b> Language AI (like ChatGPT)<br>
                      <b class='io-label-output'>Output:</b> A helpful response
                      </p>
                  </div>

                  <div class='inner-card-wide'>
                      <p style='margin:0; font-size:18px;'>
                      <b class='io-label-input'>Input:</b> Person's criminal history<br>
                      <b class='io-label-model'>Model:</b> Risk assessment AI<br>
                      <b class='io-label-output'>Output:</b> "High Risk" or "Low Risk"
                      </p>
                  </div>
                </div>
                """
            )

            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Next: How Models Learn ▶️", variant="primary", size="lg")

        # Step 3: How Models Learn
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            gr.Markdown("<h2 style='text-align:center;'>🧠 How Does an AI Model Learn?</h2>")

            gr.HTML(
                """
                <div class='step-card step-card-amber'>
                  <h3 style='color:#92400e; margin-top:0;'>1. It Learns from Examples</h3>
                  
                  <p>An AI model isn't programmed with answers. Instead, it's trained on a huge number of examples, and it learns how to find the answers on its own.</p>
                  <p>In our justice scenario, this means feeding the model thousands of past cases (<b>examples</b>) to teach it how to find the <b>patterns</b> that connect a person's details to their criminal risk.</p>
                  
                  <hr style='margin:24px 0;'>
                  
                  <h3 style='color:#92400e;'>2. The Training Process</h3>
                  <p>The AI "trains" by looping through historical data (past cases) millions of times:</p>
                  
                  <div class='inner-card'>
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
                  <div class='keypoint-box'>
                      <p style='margin:0;'>
                        <b>Here's the critical problem:</b> The model *only* learns from the data.
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
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            gr.Markdown("<h2 style='text-align:center;'>🎮 Try It Yourself!</h2>")
            gr.Markdown(
                """
                <div class='step-card step-card-amber' style='text-align:center; font-size:18px;'>
                  <p style='margin:0;'>
                    <b>Let's use a simple AI model to predict criminal risk.</b><br>
                    Adjust the inputs below and see how the model's prediction changes!
                  </p>
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
                    info="Defendant's age",
                )
                priors_slider = gr.Slider(
                    minimum=0,
                    maximum=10,
                    value=2,
                    step=1,
                    label="Prior Offenses",
                    info="Number of previous crimes",
                )

            severity_dropdown = gr.Dropdown(
                choices=["Minor", "Moderate", "Serious"],
                value="Moderate",
                label="Current Charge Severity",
                info="How serious is the current charge?",
            )

            gr.HTML("<hr style='margin:24px 0;'>")

            gr.Markdown("<h3 style='text-align:center; color:#92400e;'>2️⃣ MODEL: Process the Data</h3>")

            predict_btn = gr.Button("🔮 Run AI Prediction", variant="primary", size="lg")

            gr.HTML("<hr style='margin:24px 0;'>")

            gr.Markdown("<h3 style='text-align:center; color:#15803d;'>3️⃣ OUTPUT: See the Prediction</h3>")

            prediction_output = gr.HTML(
                """
                <div class='prediction-placeholder'>
                    <p style='font-size:18px; margin:0;'>
                    Click "Run AI Prediction" above to see the result
                    </p>
                </div>
                """
            )

            gr.HTML("<hr style='margin:24px 0;'>")

            gr.Markdown(
                """
                <div class='highlight-soft'>
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
        with gr.Column(visible=False, elem_id="step-5") as step_5:
            gr.Markdown("<h2 style='text-align:center;'>🔗 Connecting to Criminal Justice</h2>")
            gr.HTML(
                """
                <div class='step-card step-card-purple'>
                  <p><b>Remember the risk prediction you used earlier as a judge?</b></p>
                  
                  <p style='margin-top:20px;'>That was a real-world example of AI in action:</p>
                  
                  <div class='inner-card inner-card-emphasis-blue' style='border-color:#9333ea;'>
                      <p style='font-size:18px; margin-bottom:16px;'>
                      <b class='io-label-input'>INPUT:</b> Defendant's information<br>
                      <span style='margin-left:24px; color:#6b7280;'>• Age, race, gender, prior offenses, charge details</span>
                      </p>
                      
                      <p style='font-size:18px; margin:16px 0;'>
                      <b class='io-label-model'>MODEL:</b> Risk assessment algorithm<br>
                      <span style='margin-left:24px; color:#6b7280;'>• Trained on historical criminal justice data</span><br>
                      <span style='margin-left:24px; color:#6b7280;'>• Looks for patterns in who re-offended in the past</span>
                      </p>
                      
                      <p style='font-size:18px; margin-top:16px; margin-bottom:0;'>
                      <b class='io-label-output'>OUTPUT:</b> Risk prediction<br>
                      <span style='margin-left:24px; color:#6b7280;'>• "High Risk", "Medium Risk", or "Low Risk"</span>
                      </p>
                  </div>
                  
                  <h3 style='color:#7e22ce; margin-top:32px;'>Why This Matters for Ethics:</h3>
                  
                  <div class='keypoint-box'>
                      <ul style='font-size:18px; margin:8px 0;'>
                          <li>The <b>input data</b> might contain historical biases</li>
                          <li>The <b>model</b> learns patterns from potentially unfair past decisions</li>
                          <li>The <b>output predictions</b> can perpetuate discrimination</li>
                      </ul>
                  </div>
                  
                  <div class='highlight-soft' style='margin-top:24px;'>
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
        with gr.Column(visible=False, elem_id="step-6") as step_6:
            gr.HTML(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>🎓 You Now Understand AI!</h2>
                    <div class='completion-box'>
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
        )

        # --- NAVIGATION LOGIC (GENERATOR-BASED) ---

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
        step_1_next.click(
            fn=create_nav_generator(step_1, step_2),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-2", "Learning the formula..."),
        )
        step_2_back.click(
            fn=create_nav_generator(step_2, step_1),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-1", "Returning to introduction..."),
        )
        step_2_next.click(
            fn=create_nav_generator(step_2, step_3),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-3", "Understanding model training..."),
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
            js=nav_js("step-4", "Loading interactive demo..."),
        )
        step_4_back.click(
            fn=create_nav_generator(step_4, step_3),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-3", "Reviewing training concepts..."),
        )
        step_4_next.click(
            fn=create_nav_generator(step_4, step_5),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-5", "Connecting to criminal justice..."),
        )
        step_5_back.click(
            fn=create_nav_generator(step_5, step_4),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-4", "Returning to demo..."),
        )
        step_5_next.click(
            fn=create_nav_generator(step_5, step_6),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-6", "Completing section..."),
        )
        back_to_connection_btn.click(
            fn=create_nav_generator(step_6, step_5),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js=nav_js("step-5", "Reviewing connections..."),
        )

    return demo


def launch_what_is_ai_app(
    height: int = 1100, share: bool = False, debug: bool = False
) -> None:
    """Convenience wrapper to create and launch the what is AI app inline."""
    demo = create_what_is_ai_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "Gradio must be installed to launch the what is AI app."
        ) from e

    # This is the original wrapper, designed for use in a notebook (like Colab)
    port = int(os.environ.get("PORT", 8080))
    with contextlib.redirect_stdout(open(os.devnull, "w")), contextlib.redirect_stderr(
        open(os.devnull, "w")
    ):
        demo.launch(share=share, inline=True, debug=debug, height=height, server_name="0.0.0.0", server_port=port)

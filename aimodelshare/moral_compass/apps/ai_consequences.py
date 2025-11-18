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
        gr.close_all(verbose=False)
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
        
        gr.Markdown("<h1 style='text-align:center;'>⚠️ What If the AI Was Wrong?</h1>")
        gr.Markdown(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #fef2f2; border-radius: 12px; border: 2px solid #dc2626;'>
            You just made decisions based on an AI's predictions.<br>
            But AI systems are not perfect. Let's explore what happens when they make mistakes.
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
        
        # Step 1: Introduction
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            gr.Markdown("<h2 style='text-align:center;'>The Stakes of AI Predictions</h2>")
            gr.Markdown(
                """
                <div style='font-size: 20px; background:#dbeafe; padding:28px; border-radius:16px;'>
                <p>In the previous exercise, you relied on an AI system to predict which defendants 
                were at <b>High</b>, <b>Medium</b>, or <b>Low</b> risk of re-offending.</p>
                
                <p style='margin-top:20px;'><b>But what if those predictions were incorrect?</b></p>
                
                <p style='margin-top:20px;'>AI systems make two types of errors that have very different consequences:</p>
                
                <ul style='font-size:18px; margin-top:12px;'>
                    <li><b>False Positives</b> - Incorrectly predicting HIGH risk</li>
                    <li><b>False Negatives</b> - Incorrectly predicting LOW risk</li>
                </ul>
                
                <p style='margin-top:20px;'>Let's examine each type of error and its real-world impact.</p>
                </div>
                """
            )
            step_1_next = gr.Button("Next: False Positives ▶️", variant="primary", size="lg")
        
        # Step 2: False Positives
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            gr.Markdown("<h2 style='text-align:center;'>🔴 False Positives: Predicting Danger Where None Exists</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#fef3c7; padding:28px; border-radius:16px; border: 3px solid #f59e0b;'>
                <h3 style='color:#b45309; margin-top:0;'>What is a False Positive?</h3>
                
                <p>A <b>false positive</b> occurs when the AI predicts someone is <b style='color:#dc2626;'>HIGH RISK</b>, 
                but they would NOT have actually re-offended if released.</p>
                
                <div style='background:white; padding:20px; border-radius:8px; margin:20px 0;'>
                    <h4 style='margin-top:0;'>Example Scenario:</h4>
                    <p style='font-size:18px;'>
                    • Sarah was flagged as <b style='color:#dc2626;'>HIGH RISK</b><br>
                    • Based on this, the judge kept her in prison<br>
                    • In reality, Sarah would have rebuilt her life and never committed another crime
                    </p>
                </div>
                
                <h3 style='color:#b45309;'>The Human Cost:</h3>
                <ul style='font-size:18px;'>
                    <li>Innocent people spend unnecessary time in prison</li>
                    <li>Families are separated for longer than needed</li>
                    <li>Job opportunities and rehabilitation are delayed</li>
                    <li>Trust in the justice system erodes</li>
                    <li>Disproportionate impact on marginalized communities</li>
                </ul>
                
                <div style='background:#fef2f2; padding:16px; border-radius:8px; margin-top:20px; border-left:6px solid #dc2626;'>
                    <p style='font-size:18px; margin:0;'><b>Key Point:</b> False positives mean the AI is being 
                    <b>too cautious</b>, keeping people locked up who should be free.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_2_back = gr.Button("◀️ Back", size="lg")
                step_2_next = gr.Button("Next: False Negatives ▶️", variant="primary", size="lg")
        
        # Step 3: False Negatives
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            gr.Markdown("<h2 style='text-align:center;'>🔵 False Negatives: Missing Real Danger</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#f0fdf4; padding:28px; border-radius:16px; border: 3px solid #16a34a;'>
                <h3 style='color:#15803d; margin-top:0;'>What is a False Negative?</h3>
                
                <p>A <b>false negative</b> occurs when the AI predicts someone is <b style='color:#16a34a;'>LOW RISK</b>, 
                but they DO actually re-offend after being released.</p>
                
                <div style='background:white; padding:20px; border-radius:8px; margin:20px 0;'>
                    <h4 style='margin-top:0;'>Example Scenario:</h4>
                    <p style='font-size:18px;'>
                    • James was flagged as <b style='color:#16a34a;'>LOW RISK</b><br>
                    • Based on this, the judge released him<br>
                    • Unfortunately, James did commit another serious crime
                    </p>
                </div>
                
                <h3 style='color:#15803d;'>The Human Cost:</h3>
                <ul style='font-size:18px;'>
                    <li>New victims of preventable crimes</li>
                    <li>Loss of public trust in the justice system</li>
                    <li>Media scrutiny and backlash against judges</li>
                    <li>Political pressure to be "tough on crime"</li>
                    <li>Potential harm to communities and families</li>
                </ul>
                
                <div style='background:#fef2f2; padding:16px; border-radius:8px; margin-top:20px; border-left:6px solid #dc2626;'>
                    <p style='font-size:18px; margin:0;'><b>Key Point:</b> False negatives mean the AI is being 
                    <b>too lenient</b>, releasing people who pose a real danger to society.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_3_back = gr.Button("◀️ Back", size="lg")
                step_3_next = gr.Button("Next: The Dilemma ▶️", variant="primary", size="lg")
        
        # Step 4: The Dilemma
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            gr.Markdown("<h2 style='text-align:center;'>⚖️ The Impossible Balance</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#faf5ff; padding:28px; border-radius:16px; border: 3px solid #9333ea;'>
                <h3 style='color:#7e22ce; margin-top:0;'>Every AI System Makes Trade-offs</h3>
                
                <p>Here's the harsh reality: <b>No AI system can eliminate both types of errors.</b></p>
                
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0;'>
                    <p style='font-size:18px; margin-bottom:16px;'><b>If you make the AI more cautious:</b></p>
                    <ul style='font-size:18px;'>
                        <li>✓ Fewer false negatives (fewer dangerous people released)</li>
                        <li>✗ More false positives (more innocent people kept in prison)</li>
                    </ul>
                    
                    <hr style='margin:20px 0;'>
                    
                    <p style='font-size:18px; margin-bottom:16px;'><b>If you make the AI more lenient:</b></p>
                    <ul style='font-size:18px;'>
                        <li>✓ Fewer false positives (more innocent people freed)</li>
                        <li>✗ More false negatives (more dangerous people released)</li>
                    </ul>
                </div>
                
                <h3 style='color:#7e22ce;'>The Ethical Question:</h3>
                <div style='background:#fef2f2; padding:20px; border-radius:8px; border-left:6px solid #dc2626;'>
                    <p style='font-size:20px; font-weight:bold; margin:0;'>
                    Which mistake is worse?
                    </p>
                    <p style='font-size:18px; margin-top:12px; margin-bottom:0;'>
                    • Keeping innocent people in prison?<br>
                    • Or releasing dangerous individuals?
                    </p>
                </div>
                
                <p style='margin-top:24px; font-size:18px;'><b>There is no universally "correct" answer.</b> 
                Different societies, legal systems, and ethical frameworks weigh these trade-offs differently.</p>
                
                <div style='background:#dbeafe; padding:16px; border-radius:8px; margin-top:20px;'>
                    <p style='font-size:18px; margin:0;'><b>This is why understanding AI is crucial.</b> 
                    We need to know how these systems work so we can make informed decisions about when 
                    and how to use them.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_4_back = gr.Button("◀️ Back", size="lg")
                step_4_next = gr.Button("Continue to Learn About AI ▶️", variant="primary", size="lg")
        
        # Step 5: Completion
        with gr.Column(visible=False, elem_id="step-5") as step_5:
            gr.HTML(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>✅ Section Complete!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        <p>You now understand the consequences of AI errors in high-stakes decisions.</p>
                        
                        <p style='margin-top:24px;'><b>Next up:</b> Learn what AI actually is and how these 
                        prediction systems work.</p>
                        
                        <p style='margin-top:24px;'>This knowledge will help you understand how to build 
                        better, more ethical AI systems.</p>
                        
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 SCROLL DOWN 👇</h1>
                        <p style='font-size:1.1rem;'>Find the next section below to continue your journey.</p>
                    </div>
                </div>
                """
            )
            back_to_dilemma_btn = gr.Button("◀️ Back to Review")
        
        # --- NAVIGATION LOGIC (GENERATOR-BASED) ---
        
        # This list must be defined *after* all the components
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
        def nav_js(target_id: str, message: str, min_show_ms: int = 400) -> str:
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
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-2", "Learning about false positives...")
        )
        step_2_back.click(
            fn=create_nav_generator(step_2, step_1), 
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-1", "Returning to introduction...")
        )
        step_2_next.click(
            fn=create_nav_generator(step_2, step_3), 
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-3", "Exploring false negatives...")
        )
        step_3_back.click(
            fn=create_nav_generator(step_3, step_2), 
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-2", "Going back...")
        )
        step_3_next.click(
            fn=create_nav_generator(step_3, step_4), 
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4", "Understanding the dilemma...")
        )
        step_4_back.click(
            fn=create_nav_generator(step_4, step_3), 
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-3", "Reviewing false negatives...")
        )
        step_4_next.click(
            fn=create_nav_generator(step_4, step_5), 
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-5", "Completing section...")
        )
        back_to_dilemma_btn.click(
            fn=create_nav_generator(step_5, step_4),
            inputs=None, outputs=all_steps, show_progress="full",
            js=nav_js("step-4", "Returning to dilemma...")
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

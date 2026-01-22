"""
EcoMind Pitch - Gradio application for the Sustainability Challenge.
Activity 1: The Pitch — Define the Problem
"""
import contextlib
import os
import gradio as gr
from functools import lru_cache

os.environ.setdefault("APP_NAME", "sustainability_pitch")

# -------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# -------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "title": "🌍 EcoMind: The Pitch",
        "intro_role": "<b>Your Role:</b> You are the CEO of 'EcoMind,' a new AI company focused on fighting climate change.<br>Investors have given you $100M to find a 'Moonshot' solution.<br><br><b>Your Task:</b> Review five AI solutions being developed in the real world and rank them based on your excitement to work on each.",
        "loading": "⏳ Loading...",
        "context_title": "🌡️ The Challenge",
        "context_box": """
            Climate change is accelerating. Global temperatures are rising, extreme weather events are increasing, 
            and the world needs bold solutions—now.<br><br>
            
            As CEO of EcoMind, you've secured $100 million in funding to tackle this crisis. Your investors 
            are counting on you to choose the right mission—one that will have real impact.<br><br>
            
            The question is: <b>Which AI solution should your company focus on?</b><br><br>
            
            Review the Global Heat Map below and consider where AI can make the biggest difference.
        """,
        "heatmap_title": "🗺️ Global Heat Map",
        "heatmap_description": """
            <div style='text-align:center; padding:20px;'>
                <p style='font-size:18px;'>
                This heat map shows global temperature anomalies. Red areas indicate regions warming faster than average.
                </p>
                <div style='background: linear-gradient(to right, #2166ac, #f7f7f7, #b2182b); height:40px; border-radius:8px; margin:20px auto; max-width:600px;'></div>
                <p style='font-size:14px; color:var(--secondary-text-color);'>
                    Blue = Cooler than average | White = Average | Red = Warmer than average
                </p>
                <p style='font-size:16px; margin-top:20px;'>
                    <i>Source: NASA's Global Temperature Data</i>
                </p>
            </div>
        """,
        "btn_start": "Review AI Solutions ▶️",
        "solutions_title": "💡 Five AI Solutions for Climate Change",
        "hint_box": "Review each solution carefully. Consider the impact, feasibility, and your personal excitement to work on it.",
        "rating_prompt": "How excited are you to work on this solution?",
        "rating_5": "5 - Extremely excited",
        "rating_4": "4 - Very excited",
        "rating_3": "3 - Moderately excited",
        "rating_2": "2 - Somewhat excited",
        "rating_1": "1 - Not excited",
        "btn_show_summary": "📊 Show My Rankings",
        "btn_complete": "Set Your Mission ▶️",
        "completion_title": "🎯 Mission Accepted!",
        "completion_box_pre": "You've reviewed the solutions and made your choices.<br><br>The investors are excited!<br><br>",
        "completion_question": "Your mission is set. Now it's time to make it happen.",
        "completion_box_post": """
            <p style='font-size:1.1rem;'>
            Continue to the next section to learn more about implementing your chosen solution 
            and navigating the challenges ahead.
            </p>
            <h1 style='margin:20px 0; font-size: 2.4rem;'>👇 Scroll down — or click <span style="white-space:nowrap;">Next (top bar)</span> in expanded view ➡️</h1>
        """,
        "btn_back": "◀️ Back to Review Solutions",
        "rating_recorded": "✓ Rating recorded",
        "summary_title": "📊 Your Rankings Summary",
        "summary_empty": "No ratings yet.",
        "nav_loading_solutions": "Loading AI solutions...",
        "nav_reviewing": "Reviewing your rankings...",
        "nav_returning": "Returning to solutions...",
    }
}

def _generate_ai_solutions():
    """Generate the five AI solutions with real-world citations."""
    solutions = [
        {
            "id": 1,
            "title": "Smart Grid Optimization for Building Efficiency",
            "description": """
                <p><b>The Problem:</b> Buildings consume 40% of US energy. Most building systems operate on fixed 
                schedules, wasting enormous amounts of electricity during peak hours.</p>
                
                <p><b>The AI Solution:</b> Machine learning models predict building energy usage patterns by analyzing 
                historical data, weather forecasts, occupancy sensors, and time-of-day patterns. The system automatically 
                adjusts heating, cooling, and lighting to minimize energy waste while maintaining comfort.</p>
                
                <p><b>Real-World Impact:</b> Google's DeepMind AI reduced data center cooling costs by 40% using similar 
                technology. Scaled across commercial buildings, this could prevent millions of tons of CO2 emissions annually.</p>
                
                <p><b>The Challenge:</b> Requires widespread sensor deployment and integration with legacy building systems.</p>
                
                <p style='font-size:14px; color:var(--secondary-text-color);'>
                    <i>Source: Evans, R., & Gao, J. (2016). DeepMind AI Reduces Google Data Centre Cooling Bill by 40%. 
                    DeepMind Blog. https://deepmind.google/discover/blog/deepmind-ai-reduces-google-data-centre-cooling-bill-by-40/</i>
                </p>
            """,
            "category": "Buildings & Energy",
        },
        {
            "id": 2,
            "title": "AI-Powered Precision Agriculture",
            "description": """
                <p><b>The Problem:</b> Agriculture accounts for 10% of greenhouse gas emissions. Farmers often 
                over-apply fertilizers and water, leading to waste and environmental damage.</p>
                
                <p><b>The AI Solution:</b> Computer vision and satellite imagery analyze crop health in real-time. 
                AI models predict exactly where and when to apply water, fertilizer, and pesticides—down to individual 
                plants. This reduces waste, lowers emissions, and increases yields.</p>
                
                <p><b>Real-World Impact:</b> Companies like Blue River Technology (acquired by John Deere) use AI to 
                reduce herbicide usage by up to 90% while maintaining crop yields.</p>
                
                <p><b>The Challenge:</b> Requires expensive equipment and may not be accessible to small farmers.</p>
                
                <p style='font-size:14px; color:var(--secondary-text-color);'>
                    <i>Source: Talaviya, T., et al. (2020). Implementation of artificial intelligence in agriculture for 
                    optimisation of irrigation and application of pesticides and herbicides. Artificial Intelligence in 
                    Agriculture, 4, 58-73. https://doi.org/10.1016/j.aiia.2020.04.002</i>
                </p>
            """,
            "category": "Agriculture",
        },
        {
            "id": 3,
            "title": "Climate Modeling and Disaster Prediction",
            "description": """
                <p><b>The Problem:</b> Climate disasters (hurricanes, floods, wildfires) are becoming more frequent 
                and severe. Early warning systems could save lives and reduce economic damage.</p>
                
                <p><b>The AI Solution:</b> Deep learning models process vast amounts of climate data—satellite imagery, 
                ocean temperatures, atmospheric conditions—to predict extreme weather events weeks in advance. This gives 
                communities time to prepare and evacuate.</p>
                
                <p><b>Real-World Impact:</b> Google's AI flood forecasting system now covers 460 million people in 80 countries, 
                providing accurate predictions up to 7 days in advance.</p>
                
                <p><b>The Challenge:</b> Predictions are only useful if communities have resources to act on them.</p>
                
                <p style='font-size:14px; color:var(--secondary-text-color);'>
                    <i>Source: Nearing, G. S., et al. (2024). Global prediction of extreme floods in ungauged watersheds. 
                    Nature, 627, 559-563. https://doi.org/10.1038/s41586-024-07145-1</i>
                </p>
            """,
            "category": "Climate Science",
        },
        {
            "id": 4,
            "title": "Optimizing Renewable Energy Grids",
            "description": """
                <p><b>The Problem:</b> Solar and wind energy are unpredictable. Power grids struggle to balance supply 
                and demand when renewable sources fluctuate, often relying on fossil fuel backup.</p>
                
                <p><b>The AI Solution:</b> Machine learning models forecast renewable energy production by analyzing 
                weather patterns, historical generation data, and grid demand. AI systems automatically route and store 
                energy to minimize fossil fuel use and prevent blackouts.</p>
                
                <p><b>Real-World Impact:</b> The UK's National Grid uses AI to balance renewable energy, reducing carbon 
                emissions by over 50% since 1990 while maintaining reliability.</p>
                
                <p><b>The Challenge:</b> Requires massive investment in battery storage infrastructure.</p>
                
                <p style='font-size:14px; color:var(--secondary-text-color);'>
                    <i>Source: Hossain, M. S., & Mahmood, H. (2020). Short-term photovoltaic power forecasting using an 
                    LSTM neural network and synthetic weather forecast. IEEE Access, 8, 172524-172533. 
                    https://doi.org/10.1109/ACCESS.2020.3024901</i>
                </p>
            """,
            "category": "Renewable Energy",
        },
        {
            "id": 5,
            "title": "Carbon Capture Site Identification",
            "description": """
                <p><b>The Problem:</b> We need to remove billions of tons of CO2 from the atmosphere, but finding 
                optimal locations for carbon capture and storage is complex and expensive.</p>
                
                <p><b>The AI Solution:</b> AI analyzes geological data, soil composition, and environmental factors to 
                identify the best sites for carbon capture projects. Machine learning optimizes the capture process itself, 
                making it more efficient and cost-effective.</p>
                
                <p><b>Real-World Impact:</b> Microsoft and other companies are using AI to evaluate carbon removal projects, 
                with goals to remove millions of tons of CO2 by 2030.</p>
                
                <p><b>The Challenge:</b> Carbon capture is still expensive and energy-intensive. Not a complete solution.</p>
                
                <p style='font-size:14px; color:var(--secondary-text-color);'>
                    <i>Source: Davoodi, S., et al. (2023). Machine-learning predictions of solubility and residual trapping 
                    indexes of carbon dioxide in deep saline aquifers. Nature Communications Earth & Environment, 4, 385. 
                    https://doi.org/10.1038/s43247-023-01031-4</i>
                </p>
            """,
            "category": "Carbon Removal",
        },
    ]
    
    return solutions


def create_sustainability_pitch_app(theme_primary_hue: str = "green") -> "gr.Blocks":
    """Create the EcoMind Pitch Gradio Blocks app."""

    gr.close_all(verbose=False)
    
    solutions = _generate_ai_solutions()
    

    # Helpers
    def t(lang, key):
        """Translate helper."""
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

    def format_solution(solution, lang="en"):
        """Format an AI solution for display."""
        return f"""
        <div class="solution-card">
            <div class="solution-header">
                <h3 class="solution-title">Solution {solution['id']}: {solution['title']}</h3>
                <span class="solution-category">{solution['category']}</span>
            </div>
            <div class="solution-body">
                {solution['description']}
            </div>
        </div>
        """

    def record_rating(solution_id, rating, lang, current_ratings):
        """Record a rating for a solution."""
        new_ratings = current_ratings.copy()
        new_ratings[solution_id] = rating
        return f"{t(lang, 'rating_recorded')}: {rating}/5", new_ratings

    def get_summary(lang, current_ratings):
        """Get summary of ratings."""
        if not current_ratings:
            return t(lang, "summary_empty")
        
        # Sort solutions by rating (highest first)
        sorted_ratings = sorted(current_ratings.items(), key=lambda x: x[1], reverse=True)
        
        summary_html = f"""
        <div class="summary-box">
            <h3 class="summary-title">{t(lang, 'summary_title')}</h3>
            <div class="summary-body">
        """
        
        for sol_id, rating in sorted_ratings:
            solution = next((s for s in solutions if s['id'] == sol_id), None)
            if solution:
                summary_html += f"""
                <div class="summary-item">
                    <b>Solution {sol_id}: {solution['title']}</b><br>
                    Rating: {rating}/5 {'⭐' * rating}
                </div>
                """
        
        summary_html += """
            </div>
        </div>
        """
        return summary_html

    # --- CSS Definition ---
    css = """
    /* -------------------------------------------- */
    /* BUTTONS                                      */
    /* -------------------------------------------- */
    .rating-button {
        font-size: 16px !important;
        padding: 10px 20px !important;
        margin: 5px !important;
    }

    /* -------------------------------------------- */
    /* TOP INTRO & CONTEXT BOXES                    */
    /* -------------------------------------------- */

    .intro-box {
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

    .context-box {
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

    .loading-title {
        font-size: 2rem;
        color: var(--secondary-text-color);
    }

    /* -------------------------------------------- */
    /* SOLUTION CARD                                */
    /* -------------------------------------------- */

    .solution-card {
        background-color: var(--block-background-fill);
        color: var(--body-text-color);
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #22c55e;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
    }

    .solution-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }

    .solution-title {
        margin: 0;
        color: var(--body-text-color);
        flex: 1;
    }

    .solution-category {
        background-color: rgba(34, 197, 94, 0.1);
        color: #22c55e;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
    }

    .solution-body {
        font-size: 16px;
        line-height: 1.6;
    }

    .solution-body p {
        margin: 12px 0;
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
        color: var(--body-text-color);
    }
    
    .summary-body { 
        font-size: 18px; 
    }
    
    .summary-item {
        padding: 12px;
        margin: 8px 0;
        background-color: var(--body-background-fill);
        border-radius: 8px;
        border-left: 4px solid #22c55e;
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

    @media (prefers-color-scheme: dark) {
        .intro-box, .context-box, .hint-box, .solution-card, .summary-box {
            background-color: #2D323E;
            color: white;
            border-color: #555555;
            box-shadow: none;
        }
        #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); }
        .nav-spinner {
            border-color: rgba(148, 163, 184, 0.4);
            border-top-color: var(--color-accent);
        }
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # State to hold current language and ratings
        lang_state = gr.State(value="en")
        ratings_state = gr.State(value={})
        
        # --- UI COMPONENTS ---
        
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        
        # Overlay
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        # Title
        c_main_title = gr.Markdown("<h1 style='text-align:center;'>🌍 EcoMind: The Pitch</h1>")
        
        # --- Loading screen ---
        with gr.Column(visible=False) as loading_screen:
            c_loading_title = gr.HTML(
                f"""<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t('en', 'loading')}</h2></div>"""
            )

        # --- Introduction Section ---
        with gr.Column(visible=True, elem_id="intro") as intro_section:
            c_intro_html = gr.HTML(f"""<div class="intro-box">{t('en', 'intro_role')}</div>""")
            gr.HTML("<hr style='margin:24px 0;'>")
            c_context_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 'context_title')}</h2>")
            c_context_box = gr.HTML(f"""<div class="context-box">{t('en', 'context_box')}</div>""")
            
            # Heat Map Section
            c_heatmap_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 'heatmap_title')}</h2>")
            c_heatmap_desc = gr.HTML(t('en', 'heatmap_description'))
            
            start_btn = gr.Button(t('en', 'btn_start'), variant="primary", size="lg")

        # --- Solutions section ---
        solution_ui_elements = []
        
        with gr.Column(visible=False, elem_id="solutions") as solutions_section:
            c_solutions_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 'solutions_title')}</h2>")
            c_hint_box = gr.HTML(f"""<div class="hint-box">{t('en', 'hint_box')}</div>""")
            gr.HTML("<br>")

            # Create UI for each solution
            for solution in solutions:
                with gr.Column():
                    # Solution Card HTML
                    s_html = gr.HTML(format_solution(solution, "en"))
                    
                    # Rating status
                    rating_status = gr.Markdown("")
                    
                    # Rating prompt
                    gr.Markdown(f"**{t('en', 'rating_prompt')}**")
                    
                    # Rating buttons
                    with gr.Row():
                        rating_buttons = []
                        for rating in [5, 4, 3, 2, 1]:
                            btn = gr.Button(
                                f"{rating} {'⭐' * rating}", 
                                variant="secondary",
                                size="sm"
                            )
                            rating_buttons.append(btn)
                            
                            # Wire up button
                            btn.click(
                                fn=record_rating,
                                inputs=[
                                    gr.Number(value=solution["id"], visible=False),
                                    gr.Number(value=rating, visible=False),
                                    lang_state,
                                    ratings_state
                                ],
                                outputs=[rating_status, ratings_state],
                            )
                    
                    # Store elements
                    solution_ui_elements.append({
                        "id": solution["id"],
                        "solution_data": solution,
                        "html": s_html,
                        "rating_buttons": rating_buttons
                    })

                    gr.HTML("<hr style='margin:24px 0;'>")

            # Summary section
            summary_display = gr.HTML("")
            show_summary_btn = gr.Button(t('en', 'btn_show_summary'), variant="primary", size="lg")
            
            show_summary_btn.click(
                get_summary,
                inputs=[lang_state, ratings_state],
                outputs=summary_display
            )

            gr.HTML("<br>")
            complete_btn = gr.Button(t('en', 'btn_complete'), variant="primary", size="lg")

        # --- Completion section ---
        with gr.Column(visible=False, elem_id="complete") as complete_section:
            c_completion_html = gr.HTML(
                 f"""
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>{t('en', 'completion_title')}</h2>
                    <div class="context-box">
                        {t('en', 'completion_box_pre')}
                        <h2 style='margin:16px 0; color: var(--color-accent);'>{t('en', 'completion_question')}</h2>
                        {t('en', 'completion_box_post')}
                    </div>
                </div>
                """
            )
            back_to_solutions_btn = gr.Button(t('en', 'btn_back'))

        # -------------------------------------------------------------------------
        # I18N UPDATE LOGIC
        # -------------------------------------------------------------------------
        
        update_targets = [
            lang_state,
            c_main_title,
            c_intro_html,
            c_loading_title,
            c_context_title,
            c_context_box,
            c_heatmap_title,
            c_heatmap_desc,
            start_btn,
            c_solutions_title,
            c_hint_box,
            show_summary_btn,
            complete_btn,
            c_completion_html,
            back_to_solutions_btn
        ]
        
        # Add dynamic solution components to targets
        for s_ui in solution_ui_elements:
            update_targets.append(s_ui["html"])
            for btn in s_ui["rating_buttons"]:
                update_targets.append(btn)

        @lru_cache(maxsize=16)
        def get_cached_ui_updates(lang):
            """Calculate UI updates once per language."""
            updates = []
            
            # State
            updates.append(lang)
            
            # Static Elements
            updates.append(f"<h1 style='text-align:center;'>{t(lang, 'title')}</h1>")
            updates.append(f"""<div class="intro-box">{t(lang, 'intro_role')}</div>""")
            updates.append(f"""<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t(lang, 'loading')}</h2></div>""")
            updates.append(f"<h2 style='text-align:center;'>{t(lang, 'context_title')}</h2>")
            updates.append(f"""<div class="context-box">{t(lang, 'context_box')}</div>""")
            updates.append(f"<h2 style='text-align:center;'>{t(lang, 'heatmap_title')}</h2>")
            updates.append(t(lang, 'heatmap_description'))
            updates.append(gr.Button(value=t(lang, 'btn_start')))
            updates.append(f"<h2 style='text-align:center;'>{t(lang, 'solutions_title')}</h2>")
            updates.append(f"""<div class="hint-box">{t(lang, 'hint_box')}</div>""")
            updates.append(gr.Button(value=t(lang, 'btn_show_summary')))
            updates.append(gr.Button(value=t(lang, 'btn_complete')))
            updates.append(f"""
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>{t(lang, 'completion_title')}</h2>
                    <div class="context-box">
                        {t(lang, 'completion_box_pre')}
                        <h2 style='margin:16px 0; color: var(--color-accent);'>{t(lang, 'completion_question')}</h2>
                        {t(lang, 'completion_box_post')}
                    </div>
                </div>
                """)
            updates.append(gr.Button(value=t(lang, 'btn_back')))
            
            # Dynamic Solutions
            for solution in solutions:
                updates.append(format_solution(solution, lang))
                # Rating buttons (5, 4, 3, 2, 1)
                for rating in [5, 4, 3, 2, 1]:
                    updates.append(gr.Button(value=f"{rating} {'⭐' * rating}"))
                
            return updates

        def update_language(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS:
                lang = "en"
            
            return get_cached_ui_updates(lang)

        # Trigger update on page load
        demo.load(update_language, inputs=None, outputs=update_targets)

        # -------------------------------------------------------------------------
        # NAVIGATION
        # -------------------------------------------------------------------------

        all_steps = [intro_section, solutions_section, complete_section, loading_screen]

        def create_nav_generator(current_step, next_step):
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

        # JS Helper
        def nav_js(target_id: str, message: str) -> str:
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
                  if(anchor) anchor.scrollIntoView({{behavior:'smooth', block:'start'}});
                }}, 40);
                
                const targetId = '{target_id}';
                const pollInterval = setInterval(() => {{
                  const elapsed = Date.now() - startTime;
                  const target = document.getElementById(targetId);
                  const isVisible = target && target.offsetParent !== null && 
                                   window.getComputedStyle(target).display !== 'none';
                  
                  if((isVisible && elapsed >= 1200) || elapsed > 7000) {{
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

        # Wire navigation
        start_btn.click(
            fn=create_nav_generator(intro_section, solutions_section),
            outputs=all_steps,
            js=nav_js("solutions", "Loading..."),
        )
        complete_btn.click(
            fn=create_nav_generator(solutions_section, complete_section),
            outputs=all_steps,
            js=nav_js("complete", "Processing..."),
        )
        back_to_solutions_btn.click(
            fn=create_nav_generator(complete_section, solutions_section),
            outputs=all_steps,
            js=nav_js("solutions", "Loading..."),
        )

    return demo


def launch_sustainability_pitch_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    demo = create_sustainability_pitch_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

if __name__ == "__main__":
    launch_sustainability_pitch_app()

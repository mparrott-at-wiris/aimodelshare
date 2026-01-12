"""
You Be the Judge - Gradio application for the Justice & Equity Challenge.
Updated with i18n support and visual fixes (gr.HTML implementation).
"""
import contextlib
import os
import gradio as gr
from functools import lru_cache

os.environ.setdefault("APP_NAME", "judge")

# -------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# -------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "title": "⚖️ You Be the Judge",
        "intro_role": "<b>Your Role:</b> You are a judge who must decide whether to release defendants from prison.<br>An AI system has analyzed each case and provided a risk assessment.<br><br><b>Your Task:</b> Review each defendant's profile and the AI's prediction, then make your decision.",
        "loading": "⏳ Loading...",
        "scenario_title": "📋 The Scenario",
        "scenario_box": """
            You are a judge in a busy criminal court. Due to prison overcrowding, you must decide 
            which defendants can be safely released.<br><br>
            
            To help you, the court has implemented an AI system that predicts the risk of each 
            defendant committing new crimes if released on parole. The AI categorizes defendants as:<br><br>
            
            <ul style='font-size:18px;'>
                <li><span class='ai-risk-label risk-high'>High Risk</span> - Likely to re-offend</li>
                <li><span class='ai-risk-label risk-medium'>Medium Risk</span> - Moderate chance of re-offending</li>
                <li><span class='ai-risk-label risk-low'>Low Risk</span> - Unlikely to re-offend</li>
            </ul>
            
            <b>Remember:</b> Your decisions affect real people's lives and public safety.
        """,
        "btn_start": "Begin Making Decisions ▶️",
        "profiles_title": "👥 Defendant Profiles",
        "hint_box": "Review each defendant's information and the AI's risk assessment, then make your decision.",
        "btn_release": "✓ Release",
        "btn_keep": "✗ Keep in Prison",
        "btn_show_summary": "📊 Show My Decisions Summary",
        "btn_complete": "Complete This Section ▶️",
        "completion_title": "✅ Decisions Complete!",
        "completion_box_pre": "You've made your decisions based on the AI's recommendations.<br><br>But here's the critical question:<br><br>",
        "completion_question": "What if the AI was wrong?",
        "completion_box_post": """
            <p style='font-size:1.1rem;'>
            Continue to the next section below to explore the consequences of 
            trusting AI predictions in high-stakes situations.
            </p>
            <h1 style='margin:20px 0; font-size: 2.4rem;'>👇 Scroll down — or click <span style="white-space:nowrap;">Next (top bar)</span> in expanded view ➡️</h1>
        """,
        "btn_back": "◀️ Back to Review Decisions",
        "decision_release": "Release",
        "decision_keep": "Keep in Prison",
        "decision_recorded": "✓ Decision recorded:",
        "summary_title": "📊 Your Decisions Summary",
        "summary_released": "Incarcerated Individuals Released:",
        "summary_kept": "Incarcerated Individuals Kept in Prison:",
        "summary_empty": "No decisions made yet.",
        "nav_loading_profiles": "Loading defendant profiles...",
        "nav_reviewing": "Reviewing your decisions...",
        "nav_returning": "Returning to profiles...",
        # Profile Data Keys
        "label_defendant": "Defendant",
        "label_age": "Age",
        "label_gender": "Gender",
        "label_race": "Race/Etnicity",
        "label_prior": "Prior Offenses",
        "label_charge": "Current Charge",
        "label_ai_risk": "🤖 AI Risk Assessment:",
        "label_risk": "Risk",
        "label_confidence": "Confidence:",
        # Demographics Translations
        "Male": "Male",
        "Female": "Female",
        "Hispanic": "Hispanic",
        "White": "White",
        "Black": "Black",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
        "Drug possession": "Drug possession",
        "Theft": "Theft",
        "Assault": "Assault",
        "Fraud": "Fraud",
        "Burglary": "Burglary"
    },
    "es": {
        "title": "⚖️ ¡Ponte en el rol de juez!",
        "intro_role": "<b>Tu rol:</b> Eres un juez o una jueza que debe decidir si se concede la libertad condicional a una persona presa o si debe continuar en prisión.<br>Un sistema de IA ha analizado cada caso y ha proporcionado una evaluación de riesgos.<br><br><b>Tu tarea:</b> Revisa el perfil de cada acusado y la predicción de la IA, luego toma tu decisión.",
        "loading": "⏳ Cargando...",
        "scenario_title": "📋 El escenario",
        "scenario_box": """
            Eres miembro de un tribunal penal con mucho trabajo. Debido al hacinamiento en las prisiones, debes decidir 
            qué personas presas pueden obtener la libertad condicional de manera segura.<br><br>
            
            Para ayudarte, el tribunal ha implementado un sistema de IA que predice el riesgo de que cada 
            persona presa cometa nuevos delitos si obtiene la libertad condicional. La IA clasifica a las personas presas como:<br><br>
            
            <ul style='font-size:18px;'>
                <li><span class='ai-risk-label risk-high'>Alto Riesgo</span> - Probable reincidencia (de cometer nuevos delitos)</li>
                <li><span class='ai-risk-label risk-medium'>Riesgo Medio</span> - Probabilidad moderada de reincidencia</li>
                <li><span class='ai-risk-label risk-low'>Bajo Riesgo</span> - Improbable reincidencia</li>
            </ul>
            
            <b>Recuerda:</b> Tus decisiones afectan la vida de personas reales y la seguridad pública.
        """,
        "btn_start": "Comenzar a tomar decisiones ▶️",
        "profiles_title": "👥 Perfiles de las personas presas",
        "hint_box": "Revisa la información de cada persona presa y la evaluación de riesgos de la IA, luego toma tu decisión.",
        "btn_release": "✓ Liberar la persona presa",
        "btn_keep": "✗ Mantener en prisión",
        "btn_show_summary": "📊 Mostrar resumen de decisiones",
        "btn_complete": "Completar esta sección ▶️",
        "completion_title": "✅ ¡Decisiones completadas!",
        "completion_box_pre": "Ya has tomado tus decisiones basándote en las recomendaciones de la IA.<br><br>Ahora bien, surge una pregunta clave:<br><br>",
        "completion_question": "¿Y si la IA se equivocó?",
        "completion_box_post": """
            <p style='font-size:1.1rem;'>
            Continúa en la siguiente sección para explorar las consecuencias de 
            confiar en las predicciones de la IA en situaciones de alto riesgo.
            </p>
            <h1 style='margin:20px 0; font-size: 2.4rem;'>👇 Desplázate hacia abajo — o haz clic en <span style="white-space:nowrap;">Siguiente (barra superior)</span> en vista ampliada ➡️</h1>
        """,
        "btn_back": "◀️ Volver a revisar decisiones",
        "decision_release": "Liberar",
        "decision_keep": "Mantener en prisión",
        "decision_recorded": "✓ Decisión registrada:",
        "summary_title": "📊 Resumen de tus decisiones",
        "summary_released": "Personas presas puestas en libertad:",
        "summary_kept": "Personas presas que continúan en prisión:",
        "summary_empty": "Aún no se han tomado decisiones.",
        "nav_loading_profiles": "Cargando perfiles...",
        "nav_reviewing": "Revisando tus decisiones...",
        "nav_returning": "Volver a perfiles...",
        "label_defendant": "Persona presa",
        "label_age": "Edad",
        "label_gender": "Género",
        "label_race": "Raza/Etnicidad",
        "label_prior": "Delitos previos",
        "label_charge": "Cargo actual",
        "label_ai_risk": "🤖 Evaluación de riesgo IA:",
        "label_risk": "Riesgo",
        "label_confidence": "Confianza:",
        "Male": "Masculino",
        "Female": "Femenino",
        "Hispanic": "Hispano",
        "White": "Blanco",
        "Black": "Negro",
        "High": "Alto",
        "Medium": "Medio",
        "Low": "Bajo",
        "Drug possession": "Posesión de drogas",
        "Theft": "Robo",
        "Assault": "Asalto",
        "Fraud": "Fraude",
        "Burglary": "Robo con allanamiento de morada"
    },
    "ca": {
        "title": "⚖️ Posa't en el rol de jutge!",
        "intro_role": "<b>El teu rol:</b> Ets un jutge o una jutgessa que ha de decidir si es concedeix la llibertat condicional a una persona presa o ha de continuar a la presó.<br>Un sistema d'IA ha analitzat cada cas i ha proporcionat una avaluació de riscos.<br><br><b>La teva tasca:</b> Revisa el perfil de cada persona presa i la predicció de la IA, després pren la teva decisió.",
        "loading": "⏳ Carregant...",
        "scenario_title": "📋 L'escenari",
        "scenario_box": """
            Ets membre d'un tribunal penal amb molta feina. A causa de la massificació a les presons, has de decidir 
            quines persones preses poden ser posades en llibertat de manera segura.<br><br>
            
            Per ajudar-te, el tribunal ha implementat un sistema d'IA que prediu el risc que cada 
            persona presa cometi nous delictes si obté la llibertat condicional. La IA classifica les persones preses com:<br><br>
            
            <ul style='font-size:18px;'>
                <li><span class='ai-risk-label risk-high'>Alt Risc</span> - Probable reincidència (de cometre nous delictes)</li>
                <li><span class='ai-risk-label risk-medium'>Risc Mitjà</span> - Probabilitat moderada de reincidència</li>
                <li><span class='ai-risk-label risk-low'>Baix Risc</span> - Improbable reincidència</li>
            </ul>
            
            <b>Recorda:</b> Les teves decisions afecten la vida de persones reals i la seguretat pública.
        """,
        "btn_start": "Començar a prendre decisions ▶️",
        "profiles_title": "👥 Perfils de les persones preses",
        "hint_box": "Revisa la informació de cada persona presa i l'avaluació de riscos de la IA, després pren la teva decisió.",
        "btn_release": "✓ Alliberar",
        "btn_keep": "✗ Mantenir a la presó",
        "btn_show_summary": "📊 Mostrar resum de decisions",
        "btn_complete": "Completar aquesta secció ▶️",
        "completion_title": "✅ Decisions completades!",
        "completion_box_pre": "Ja has pres les teves decisions basant-te en les recomanacions de la IA.<br><br>Ara bé, sorgeix una pregunta clau:<br><br>",
        "completion_question": "I si la IA s'hagués equivocat?",
        "completion_box_post": """
            <p style='font-size:1.1rem;'>
            Continua a la següent secció per explorar les conseqüències de 
            confiar en les prediccions de la IA en situacions d'alt risc.
            </p>
            <h1 style='margin:20px 0; font-size: 2.4rem;'>👇 Desplaça't cap avall — o fes clic a <span style="white-space:nowrap;">Següent (barra superior)</span> en vista ampliada ➡️</h1>
        """,
        "btn_back": "◀️ Tornar a revisar decisions",
        "decision_release": "Alliberar",
        "decision_keep": "Mantenir a la presó",
        "decision_recorded": "✓ Decisió registrada:",
        "summary_title": "📊 Resum de les teves decisions",
        "summary_released": "Persones preses posades en llibertat:",
        "summary_kept": "Persones preses que continuen a la presó:",
        "summary_empty": "Encara no s'han pres decisions.",
        "nav_loading_profiles": "Carregant perfils...",
        "nav_reviewing": "Revisant les teves decisions...",
        "nav_returning": "Tornar a perfils...",
        "label_defendant": "Persona presa",
        "label_age": "Edat",
        "label_gender": "Gènere",
        "label_race": "Raça/Etnicitat",
        "label_prior": "Delictes previs",
        "label_charge": "Càrrec actual",
        "label_ai_risk": "🤖 Avaluació de risc de la IA:",
        "label_risk": "Risc",
        "label_confidence": "Confiança:",
        "Male": "Masculí",
        "Female": "Femení",
        "Hispanic": "Hispà",
        "White": "Blanc",
        "Black": "Negre",
        "High": "Alt",
        "Medium": "Mitjà",
        "Low": "Baix",
        "Drug possession": "Possessió de drogues",
        "Theft": "Robatori",
        "Assault": "Assalt",
        "Fraud": "Frau",
        "Burglary": "Robatori amb violació de domicili"
    }
}

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
            "ai_risk": "Low",
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
            "ai_risk": "High",
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
            "ai_risk": "High",
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
            "ai_risk": "Low",
            "ai_confidence": "91%",
        },
    ]

    return profiles


def create_judge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the You Be the Judge Gradio Blocks app."""

    gr.close_all(verbose=False)
    
    profiles = _generate_defendant_profiles()
    

    # Helpers
    def t(lang, key):
        """Translate helper."""
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

    def format_profile(profile, lang="en"):
        """Format a defendant profile for display using theme-aware CSS classes and i18n."""
        # Translate values
        gender_t = t(lang, profile['gender'])
        race_t = t(lang, profile['race'])
        charge_t = t(lang, profile['current_charge'])
        risk_val_t = t(lang, profile['ai_risk'])
        
        risk_class = f"risk-{profile['ai_risk'].lower()}"
        
        return f"""
        <div class="profile-card {risk_class}">
            <h3 class="profile-title">
                {t(lang, 'label_defendant')} #{profile['id']}: {profile['name']}
            </h3>
            <div class="profile-grid">
                <div><b>{t(lang, 'label_age')}:</b> {profile['age']}</div>
                <div><b>{t(lang, 'label_gender')}:</b> {gender_t}</div>
                <div><b>{t(lang, 'label_race')}:</b> {race_t}</div>
                <div><b>{t(lang, 'label_prior')}:</b> {profile['prior_offenses']}</div>
                <div class="profile-charge">
                    <b>{t(lang, 'label_charge')}:</b> {charge_t}
                </div>
            </div>
            <div class="ai-risk-container">
                <b>{t(lang, 'label_ai_risk')}</b>
                <span class="ai-risk-label {risk_class}">
                    {risk_val_t} {t(lang, 'label_risk')}
                </span>
                <span class="ai-risk-confidence">
                    ({t(lang, 'label_confidence')} {profile['ai_confidence']})
                </span>
            </div>
        </div>
        """

    def make_decision(defendant_id, decision_type, lang, current_decisions):
            """Record a decision for a defendant safely per user."""
            # Create a copy so we don't affect other users
            new_decisions = current_decisions.copy()
            new_decisions[defendant_id] = decision_type 
            
            dec_text = t(lang, "decision_release" if decision_type == "Release" else "decision_keep")
            # Return the notification text AND the updated dictionary
            return f"{t(lang, 'decision_recorded')} {dec_text}", new_decisions

    def get_summary(lang, current_decisions):
        """Get summary based on the specific user's decisions."""
        if not current_decisions:
            return t(lang, "summary_empty")

        released = sum(1 for d in current_decisions.values() if d == "Release")
        kept = sum(1 for d in current_decisions.values() if d == "Keep in Prison")

        summary = f"""
        <div class="summary-box">
            <h3 class="summary-title">{t(lang, 'summary_title')}</h3>
            <div class="summary-body">
                <p><b>{t(lang, 'summary_released')}</b> {released} of {len(current_decisions)}</p>
                <p><b>{t(lang, 'summary_kept')}</b> {kept} of {len(current_decisions)}</p>
            </div>
        </div>
        """
        return summary

    # --- CSS Definition (Kept Original) ---
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

    /* Compact, responsive CTA sizing in completion sections */
    .completion-box h1,
    .final-instruction {
      font-size: clamp(1.5rem, 2vw + 0.6rem, 2rem) !important;
      line-height: 1.25;
      margin: 16px 0;
    }
    .complete-box h1 { font-size: clamp(1.5rem, 2vw + 0.6rem, 2rem) !important; line-height: 1.25; margin: 16px 0; }
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

    /* Semantic risk colors */
    .risk-high { border-left-color: #ef4444; color: #ef4444; }
    .profile-card.risk-high { border-left-color: #ef4444; }

    .risk-medium { border-left-color: #f59e0b; color: #f59e0b; }
    .profile-card.risk-medium { border-left-color: #f59e0b; }

    .risk-low { border-left-color: #22c55e; color: #22c55e; }
    .profile-card.risk-low { border-left-color: #22c55e; }

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

    .summary-title { margin-top: 0; }
    .summary-body { font-size: 18px; }

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
        .judge-intro-box, .scenario-box, .hint-box, .complete-box, 
        .profile-card, .summary-box {
            background-color: #2D323E;
            color: white;
            border-color: #555555;
            box-shadow: none;
        }
        .ai-risk-container {
            background-color: #181B22;
            border-color: #555555;
        }
        #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); }
        .nav-spinner {
            border-color: rgba(148, 163, 184, 0.4);
            border-top-color: var(--color-accent);
        }
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        # State to hold current language (defaults to 'en')
        lang_state = gr.State(value="en")
        decisions_state = gr.State(value={})
        
        # --- UI COMPONENTS (Stored in variables for update) ---
        
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        
        # Overlay
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)

        # Title
        c_main_title = gr.Markdown("<h1 style='text-align:center;'>⚖️ You Be the Judge</h1>")
        

        # --- Loading screen ---
        with gr.Column(visible=False) as loading_screen:
            c_loading_title = gr.HTML(
                f"""<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t('en', 'loading')}</h2></div>"""
            )

        # --- Introduction Section ---
        with gr.Column(visible=True, elem_id="intro") as intro_section:
            c_intro_html = gr.HTML(f"""<div class="judge-intro-box">{t('en', 'intro_role')}</div>""")
            gr.HTML("<hr style='margin:24px 0;'>")
            c_scenario_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 'scenario_title')}</h2>")
            # CHANGED TO HTML
            c_scenario_box = gr.HTML(f"""<div class="scenario-box">{t('en', 'scenario_box')}</div>""")
            start_btn = gr.Button(t('en', 'btn_start'), variant="primary", size="lg")

        # --- Defendant profiles section ---
        profile_ui_elements = [] # To store (html, btn_rel, btn_keep) tuples
        
        with gr.Column(visible=False, elem_id="profiles") as profiles_section:
            c_profiles_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 'profiles_title')}</h2>")
            # CHANGED TO HTML
            c_hint_box = gr.HTML(f"""<div class="hint-box">{t('en', 'hint_box')}</div>""")
            gr.HTML("<br>")

            # Create UI for each defendant
            for profile in profiles:
                with gr.Column():
                    # 1. Profile Card HTML
                    p_html = gr.HTML(format_profile(profile, "en"))
                    
                    # 2. Define the status text component FIRST (so buttons can reference it)
                    decision_status = gr.Markdown("")

                    # 3. Create Row with Buttons
                    with gr.Row():
                        # Define the buttons
                        p_rel_btn = gr.Button(t("en", "btn_release"), variant="secondary")
                        p_keep_btn = gr.Button(t("en", "btn_keep"), variant="stop")
                        
                        # Wire up buttons
                        p_rel_btn.click(
                            fn=make_decision,
                            inputs=[gr.Number(value=profile["id"], visible=False), gr.State(value="Release"), lang_state, decisions_state],
                            outputs=[decision_status, decisions_state], 
                        )
                        p_keep_btn.click(
                            fn=make_decision,
                            inputs=[gr.Number(value=profile["id"], visible=False), gr.State(value="Keep in Prison"), lang_state, decisions_state],
                            outputs=[decision_status, decisions_state], 
                        )

                    # 4. Store elements for language updates
                    profile_ui_elements.append({
                        "id": profile["id"],
                        "profile_data": profile,
                        "html": p_html,
                        "btn_rel": p_rel_btn,
                        "btn_keep": p_keep_btn
                    })

                    gr.HTML("<hr style='margin:24px 0;'>")

            # Summary section
            summary_display = gr.HTML("")
            show_summary_btn = gr.Button(t('en', 'btn_show_summary'), variant="primary", size="lg")
            
            show_summary_btn.click(
                get_summary, 
                inputs=[lang_state, decisions_state], # Pass the state
                outputs=summary_display
            )

            gr.HTML("<br>")
            complete_btn = gr.Button(t('en', 'btn_complete'), variant="primary", size="lg")

        # --- Completion section ---
        with gr.Column(visible=False, elem_id="complete") as complete_section:
            # CHANGED TO HTML
            c_completion_html = gr.HTML(
                 f"""
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>{t('en', 'completion_title')}</h2>
                    <div class="complete-box">
                        {t('en', 'completion_box_pre')}
                        <h2 style='margin:16px 0; color: var(--color-accent);'>{t('en', 'completion_question')}</h2>
                        {t('en', 'completion_box_post')}
                    </div>
                </div>
                """
            )
            back_to_profiles_btn = gr.Button(t('en', 'btn_back'))

        # -------------------------------------------------------------------------
        # I18N UPDATE LOGIC (CACHED)
        # -------------------------------------------------------------------------
        
        # 1. Define targets (This remains the same)
        update_targets = [
            lang_state,          # 0
            c_main_title,        # 1
            c_intro_html,        # 2
            c_loading_title,     # 3
            c_scenario_title,    # 4
            c_scenario_box,      # 5
            start_btn,           # 6
            c_profiles_title,    # 7
            c_hint_box,          # 8
            show_summary_btn,    # 9
            complete_btn,        # 10
            c_completion_html,   # 11
            back_to_profiles_btn # 12
        ]
        
        # Add dynamic profile components to targets
        for p_ui in profile_ui_elements:
            update_targets.append(p_ui["html"])
            update_targets.append(p_ui["btn_rel"])
            update_targets.append(p_ui["btn_keep"])

        # 2. Define the Cached Generator
        @lru_cache(maxsize=16)
        def get_cached_ui_updates(lang):
            """
            Calculates the massive list of HTML strings and Labels ONCE per language.
            """
            updates = []
            
            # 0. State
            updates.append(lang)
            
            # Static Elements
            updates.append(f"<h1 style='text-align:center;'>{t(lang, 'title')}</h1>")
            updates.append(f"""<div class="judge-intro-box">{t(lang, 'intro_role')}</div>""")
            updates.append(f"""<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t(lang, 'loading')}</h2></div>""")
            updates.append(f"<h2 style='text-align:center;'>{t(lang, 'scenario_title')}</h2>")
            updates.append(f"""<div class="scenario-box">{t(lang, 'scenario_box')}</div>""")
            updates.append(gr.Button(value=t(lang, 'btn_start')))
            updates.append(f"<h2 style='text-align:center;'>{t(lang, 'profiles_title')}</h2>")
            updates.append(f"""<div class="hint-box">{t(lang, 'hint_box')}</div>""")
            updates.append(gr.Button(value=t(lang, 'btn_show_summary')))
            updates.append(gr.Button(value=t(lang, 'btn_complete')))
            updates.append(f"""
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>{t(lang, 'completion_title')}</h2>
                    <div class="complete-box">
                        {t(lang, 'completion_box_pre')}
                        <h2 style='margin:16px 0; color: var(--color-accent);'>{t(lang, 'completion_question')}</h2>
                        {t(lang, 'completion_box_post')}
                    </div>
                </div>
                """)
            updates.append(gr.Button(value=t(lang, 'btn_back')))
            
            # Dynamic Profiles (Loop through the data, not the UI elements, to be safe)
            # Note: We rely on 'profiles' being available in this scope.
            for profile in profiles:
                updates.append(format_profile(profile, lang))
                updates.append(gr.Button(value=t(lang, 'btn_release')))
                updates.append(gr.Button(value=t(lang, 'btn_keep')))
                
            return updates

        # 3. Define the Request Handler
        def update_language(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS:
                lang = "en"
            
            # Instant return from cache
            return get_cached_ui_updates(lang)

        # Trigger update on page load
        demo.load(update_language, inputs=None, outputs=update_targets)

        # -------------------------------------------------------------------------
        # NAVIGATION GENERATORS
        # -------------------------------------------------------------------------

        all_steps = [intro_section, profiles_section, complete_section, loading_screen]

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
            fn=create_nav_generator(intro_section, profiles_section),
            outputs=all_steps,
            js=nav_js("profiles", "Loading..."),
        )
        complete_btn.click(
            fn=create_nav_generator(profiles_section, complete_section),
            outputs=all_steps,
            js=nav_js("complete", "Processing..."),
        )
        back_to_profiles_btn.click(
            fn=create_nav_generator(complete_section, profiles_section),
            outputs=all_steps,
            js=nav_js("profiles", "Loading..."),
        )

    return demo


def launch_judge_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    demo = create_judge_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

if __name__ == "__main__":
    launch_judge_app()



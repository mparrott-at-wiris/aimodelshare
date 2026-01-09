"""
AI Consequences - Gradio application for the Justice & Equity Challenge.
Refined Design: Matches 'Bias Detective' UI (Scenario Boxes, Click Reveals).
"""
import gradio as gr
from functools import lru_cache

# -------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# -------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "app_title": "⚠️ AI Consequences",
        "loading": "⏳ Loading...",
        
        # SLIDE 1: ORIGINAL TEXT (Preserved)
        "s1_title": "The Stakes of AI Predictions",
        "s1_p1": "In the previous exercise, you relied on an AI system to predict which defendants were at <b>High</b>, <b>Medium</b>, or <b>Low</b> risk of re-offending.",
        "s1_p2": "<b>But what if those predictions were incorrect?</b>",
        "s1_p3": "AI systems make two types of errors that have very different consequences:",
        "s1_li1": "<b>False Positives</b> - Incorrectly predicting HIGH risk",
        "s1_li2": "<b>False Negatives</b> - Incorrectly predicting LOW risk",
        "s1_p4": "Let's examine each type of error and its real-world impact.",
        "s1_btn": "Start Investigation ▶️",

        # SLIDE 2: SARAH (False Positive)
        "s2_title": "🔴 Case File: Sarah",
        "s2_card_label": "CASE #892",
        "s2_ai_pred": "AI PREDICTION: <span style='color:#dc2626'>HIGH RISK 🔴</span>",
        "s2_desc": "Sarah was flagged by the AI as dangerous. Based on this, the judge denied bail and kept her in prison awaiting trial.",
        "s2_reveal_btn": "🔍 Reveal Reality (Click Here)",
        "s2_reveal_title": "THE REALITY:",
        "s2_reveal_text": "Sarah was eventually released. <b>She never committed another crime.</b>",
        "s2_analysis_title": "DIAGNOSIS: FALSE POSITIVE",
        "s2_analysis_text": "This is a 'False Alarm.' The AI saw danger where there was none.<br><b>The Cost:</b> An innocent person lost their freedom, job, and time with family.",
        "s2_btn": "Next Case ▶️",

        # SLIDE 3: JAMES (False Negative)
        "s3_title": "🔵 Case File: James",
        "s3_card_label": "CASE #893",
        "s3_ai_pred": "AI PREDICTION: <span style='color:#16a34a'>LOW RISK 🟢</span>",
        "s3_desc": "James was flagged as safe. The judge released him on parole based on this low-risk score.",
        "s3_reveal_btn": "🔍 Reveal Reality (Click Here)",
        "s3_reveal_title": "THE REALITY:",
        "s3_reveal_text": "One month later, <b>James committed a serious robbery.</b>",
        "s3_analysis_title": "DIAGNOSIS: FALSE NEGATIVE",
        "s3_analysis_text": "The AI 'Missed' the warning.<br><b>The Cost:</b> Public safety was compromised, creating new victims and eroding trust in the justice system.",
        "s3_btn": "Next: The Dilemma ▶️",

        # SLIDE 4: THE TRADE-OFF (Slider)
        "s4_title": "⚖️ The Impossible Balance",
        "s4_intro": "Can you fix the AI? Try to adjust the strictness to get <b>Zero Errors</b>.",
        "s4_label": "AI Strictness Setting",
        "s4_fp_label": "Innocents Jailed (False Warnings)",
        "s4_fn_label": "Criminals Released (Missed Warnings)",
        "s4_feed_lenient": "⚠️ <b>Too Lenient!</b> You reduced False Warnings (False Positives), but now <b>crime has spiked</b> (High Missed Warnings/False Negatives).",
        "s4_feed_strict": "⚠️ <b>Too Strict!</b> You stopped crime, but now you are <b>locking up innocent people</b> (High False Warnings/False Positives).",
        "s4_feed_tradeoff": "⚖️ <b>The Hard Truth:</b> You cannot make both errors zero. As one goes down, the other goes up.",
        "s4_btn": "I Understand - Finish ▶️",

        # SLIDE 5: ORIGINAL COMPLETION (Preserved)
        "s5_title": "✅ Section Complete!",
        "s5_p1": "You now understand the consequences of AI errors in high-stakes decisions.",
        "s5_p2": "<b>Next up:</b> Learn what AI actually is and how these prediction systems work.",
        "s5_p3": "This knowledge will help you understand how to build better, more ethical AI systems.",
        "s5_scroll": "👇 Continue to the next activity below — or click <span style='white-space:nowrap;'>Next (top bar)</span> in expanded view ➡️",
        "s5_find": "If you’re not in expanded view, scroll to find the next activity.",
        "s5_btn": "◀️ Review Cases"
    },
    "es": {
        "app_title": "⚠️ Consecuencias de la IA",
        "loading": "⏳ Cargando...",
        "s1_title": "Los riesgos de las predicciones de IA",
        "s1_p1": "En el ejercicio anterior, confiaste en un sistema de IA para predecir qué personas tenían un riesgo <b>Alto</b>, <b>Medio</b> o <b>Bajo</b> de reincidir.",
        "s1_p2": "<b>¿Pero qué pasa si esas predicciones eran incorrectas?</b>",
        "s1_p3": "Los sistemas de IA cometen dos tipos de errores con consecuencias muy diferentes:",
        "s1_li1": "<b>Falsos Positivos</b> - Predecir incorrectamente ALTO riesgo",
        "s1_li2": "<b>Falsos Negativos</b> - Predecir incorrectamente BAJO riesgo",
        "s1_p4": "Examinemos cada tipo de error y su impacto real.",
        "s1_btn": "Iniciar Investigación ▶️",

        "s2_title": "🔴 Expediente: Sarah",
        "s2_card_label": "CASO #892",
        "s2_ai_pred": "PREDICCIÓN IA: <span style='color:#dc2626'>ALTO RIESGO 🔴</span>",
        "s2_desc": "Sarah fue marcada como peligrosa. El juez le denegó la fianza y la mantuvo en prisión.",
        "s2_reveal_btn": "🔍 Revelar Realidad",
        "s2_reveal_title": "LA REALIDAD:",
        "s2_reveal_text": "Sarah fue liberada finalmente. <b>Nunca cometió otro delito.</b>",
        "s2_analysis_title": "DIAGNÓSTICO: FALSO POSITIVO",
        "s2_analysis_text": "Es una 'Falsa Alarma'. La IA vio peligro donde no lo había.<br><b>El Coste:</b> Una persona inocente perdió su libertad y tiempo con su familia.",
        "s2_btn": "Siguiente Caso ▶️",

        "s3_title": "🔵 Expediente: James",
        "s3_card_label": "CASO #893",
        "s3_ai_pred": "PREDICCIÓN IA: <span style='color:#16a34a'>BAJO RIESGO 🟢</span>",
        "s3_desc": "James fue marcado como seguro. El juez lo liberó bajo palabra basándose en esto.",
        "s3_reveal_btn": "🔍 Revelar Realidad",
        "s3_reveal_title": "LA REALIDAD:",
        "s3_reveal_text": "Un mes después, <b>James cometió un robo grave.</b>",
        "s3_analysis_title": "DIAGNÓSTICO: FALSO NEGATIVO",
        "s3_analysis_text": "La IA 'perdió' la amenaza.<br><b>El Coste:</b> La seguridad pública se vio comprometida, creando nuevas víctimas.",
        "s3_btn": "Siguiente: El Dilema ▶️",

        "s4_title": "⚖️ El Equilibrio Imposible",
        "s4_intro": "¿Puedes arreglar la IA? Intenta ajustar la estrictez para obtener <b>Cero Errores</b>.",
        "s4_label": "Nivel de Estrictez",
        "s4_fp_label": "Inocentes en Prisión (Falsos Positivos)",
        "s4_fn_label": "Criminales Liberados (Falsos Negativos)",
        "s4_feed_lenient": "⚠️ <b>¡Demasiado Indulgente!</b> Redujiste los Falsos Positivos, pero <b>el crimen aumentó</b> (Falsos Negativos).",
        "s4_feed_strict": "⚠️ <b>¡Demasiado Estricto!</b> Detuviste el crimen, pero estás <b>encarcelando a inocentes</b> (Falsos Positivos).",
        "s4_feed_tradeoff": "⚖️ <b>La Dura Verdad:</b> No puedes eliminar ambos errores. Si uno baja, el otro sube.",
        "s4_btn": "Entiendo - Finalizar ▶️",

        "s5_title": "✅ Sección Completada",
        "s5_p1": "Ahora entiendes las consecuencias de los errores de la IA en decisiones de alto riesgo.",
        "s5_p2": "<b>A continuación:</b> Aprende qué es realmente la IA y cómo funcionan estos sistemas.",
        "s5_p3": "Este conocimiento te ayudará a entender cómo construir sistemas de IA mejores y más éticos.",
        "s5_scroll": "👇 Continúa con la siguiente actividad abajo — o haz clic en <span style='white-space:nowrap;'>Siguiente</span> en la barra superior ➡️",
        "s5_find": "Si no estás en vista ampliada, desplázate para encontrar la siguiente actividad.",
        "s5_btn": "◀️ Revisar Casos"
    },
    "ca": {
        "app_title": "⚠️ Conseqüències de la IA",
        "loading": "⏳ Carregant...",
        "s1_title": "Els riscos de les prediccions d'IA",
        "s1_p1": "En l'exercici anterior, has confiat en un sistema d'IA per predir quines persones tenien un risc <b>Alt</b>, <b>Mitjà</b> o <b>Baix</b> de reincidir.",
        "s1_p2": "<b>Però què passa si aquestes prediccions eren incorrectes?</b>",
        "s1_p3": "Els sistemes d'IA cometen dos tipus d'errors amb conseqüències molt diferents:",
        "s1_li1": "<b>Falsos Positius</b> - Predir incorrectament ALT risc",
        "s1_li2": "<b>Falsos Negatius</b> - Predir incorrectament BAIX risc",
        "s1_p4": "Examinem cada tipus d'error i el seu impacte real.",
        "s1_btn": "Iniciar Investigació ▶️",

        "s2_title": "🔴 Expedient: Sarah",
        "s2_card_label": "CAS #892",
        "s2_ai_pred": "PREDICCIÓ IA: <span style='color:#dc2626'>ALT RISC 🔴</span>",
        "s2_desc": "La Sarah va ser marcada com a perillosa. El jutge li va denegar la fiança i la va mantenir a la presó.",
        "s2_reveal_btn": "🔍 Revelar Realitat",
        "s2_reveal_title": "LA REALITAT:",
        "s2_reveal_text": "La Sarah va ser alliberada finalment. <b>Mai va cometre un altre delicte.</b>",
        "s2_analysis_title": "DIAGNÒSTIC: FALS POSITIU",
        "s2_analysis_text": "És una 'Falsa Alarma'. La IA va veure perill on no n'hi havia.<br><b>El Cost:</b> Una persona innocent va perdre la llibertat i temps amb la seva família.",
        "s2_btn": "Següent Cas ▶️",

        "s3_title": "🔵 Expedient: James",
        "s3_card_label": "CAS #893",
        "s3_ai_pred": "PREDICCIÓ IA: <span style='color:#16a34a'>BAIX RISC 🟢</span>",
        "s3_desc": "En James va ser marcat com a segur. El jutge el va alliberar sota paraula basant-se en això.",
        "s3_reveal_btn": "🔍 Revelar Realitat",
        "s3_reveal_title": "LA REALITAT:",
        "s3_reveal_text": "Un mes després, <b>en James va cometre un robatori greu.</b>",
        "s3_analysis_title": "DIAGNÒSTIC: FALS NEGATIU",
        "s3_analysis_text": "La IA va 'perdre' l'amenaça.<br><b>El Cost:</b> La seguretat pública es va veure compromesa, creant noves víctimes.",
        "s3_btn": "Següent: El Dilema ▶️",

        "s4_title": "⚖️ L'Equilibri Impossible",
        "s4_intro": "Pots arreglar la IA? Intenta ajustar l'estricte per obtenir <b>Zero Errors</b>.",
        "s4_label": "Nivell d'Estricte",
        "s4_fp_label": "Innocents a la Presó (Falsos Positius)",
        "s4_fn_label": "Criminals Alliberats (Falsos Negatius)",
        "s4_feed_lenient": "⚠️ <b>Massa Indulgent!</b> Has reduït els Falsos Positius, però <b>el crim ha augmentat</b> (Falsos Negatius).",
        "s4_feed_strict": "⚠️ <b>Massa Estricte!</b> Has aturat el crim, però estàs <b>empresonant innocents</b> (Falsos Positius).",
        "s4_feed_tradeoff": "⚖️ <b>La Dura Veritat:</b> No pots eliminar els dos errors. Si un baixa, l'altre puja.",
        "s4_btn": "Entès - Finalitzar ▶️",

        "s5_title": "✅ Secció Completada",
        "s5_p1": "Ara entens les conseqüències dels errors de la IA en decisions d'alt risc.",
        "s5_p2": "<b>A continuació:</b> Aprèn què és realment la IA i com funcionen aquests sistemes.",
        "s5_p3": "Aquest coneixement t'ajudarà a entendre com construir sistemes d'IA millors i més ètics.",
        "s5_scroll": "👇 Continua amb la següent activitat a sota — o fes clic a <span style='white-space:nowrap;'>Següent</span> a la barra superior ➡️",
        "s5_find": "Si no estàs en vista ampliada, desplaça’t per trobar la següent activitat.",
        "s5_btn": "◀️ Revisar Casos"
    }
}

def create_ai_consequences_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    
    # --- Helpers ---
    def t(lang, key):
        if not isinstance(lang, str): lang = "en"
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

    # --- CSS Adapted from Bias Detective ---
    css = """
    /* --- LAYOUT CONTAINERS --- */
    .scenario-box {
        padding: 24px;
        border-radius: 14px;
        background: var(--block-background-fill);
        border: 1px solid var(--border-color-primary);
        margin-bottom: 22px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
    }
    .slide-title { margin-top: 0; font-size: 1.8rem; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .slide-body { font-size: 1.1rem; line-height: 1.6; }
    
    /* --- CONTENT BOXES --- */
    .hint-box {
        padding: 16px;
        border-radius: 10px;
        background: var(--background-fill-secondary);
        border: 1px solid var(--border-color-primary);
        margin-top: 15px;
        font-size: 1rem;
    }
    .ai-risk-container { 
        margin-top: 16px; 
        padding: 20px; 
        background: var(--body-background-fill); 
        border-radius: 10px; 
        border: 1px solid var(--border-color-primary); 
    }
    
    /* --- SPECIFIC CARDS (Sarah/James) --- */
    .case-card {
        background: var(--background-fill-secondary);
        border-radius: 12px;
        border: 1px solid var(--border-color-primary);
        padding: 0;
        overflow: hidden;
        margin-bottom: 20px;
    }
    .case-header {
        padding: 15px;
        background: var(--background-fill-primary);
        border-bottom: 1px solid var(--border-color-primary);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 700;
    }
    .case-body { padding: 20px; }
    
    /* --- BAR CHART --- */
    .bar-container { display: flex; align-items: center; margin-bottom: 12px; }
    .bar-label { width: 140px; font-weight: bold; font-size: 0.9rem; }
    .bar-track { flex-grow: 1; background: #e5e7eb; height: 24px; border-radius: 4px; overflow: hidden; position: relative; }
    .bar-fill { height: 100%; transition: width 0.3s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 0.8rem; font-weight: bold; }

    /* --- LOADING OVERLAY --- */
    #nav-loading-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: color-mix(in srgb, var(--body-background-fill) 95%, transparent);
        z-index: 9999; display: none; flex-direction: column; align-items: center;
        justify-content: center; opacity: 0; transition: opacity 0.3s ease;
    }
    .nav-spinner {
        width: 50px; height: 50px; border: 5px solid var(--border-color-primary);
        border-top: 5px solid var(--color-accent); border-radius: 50%;
        animation: nav-spin 1s linear infinite; margin-bottom: 20px;
    }
    @keyframes nav-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    #nav-loading-text { font-size: 1.3rem; font-weight: 600; color: var(--color-accent); }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        
        # --- State ---
        lang_state = gr.State("en")
        
        # --- Loading Overlay ---
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # --- SLIDE 1: INTRO (Original Text, New Style) ---
        with gr.Group(elem_id="step-1") as step_1:
            with gr.Column(elem_classes=["scenario-box"]):
                s1_title = gr.Markdown(f"## {t('en', 's1_title')}", elem_classes=["slide-title"])
                s1_content = gr.HTML(f"""
                <div class='slide-body'>
                    <p>{t('en', 's1_p1')}</p>
                    <p style='margin-top:15px; font-size:1.2rem; text-align:center;'>{t('en', 's1_p2')}</p>
                    <div class='ai-risk-container'>
                        <p>{t('en', 's1_p3')}</p>
                        <ul>
                            <li style='margin-bottom:8px;'>{t('en', 's1_li1')}</li>
                            <li>{t('en', 's1_li2')}</li>
                        </ul>
                    </div>
                    <p style='margin-top:20px; font-weight:bold; text-align:center;'>{t('en', 's1_p4')}</p>
                </div>
                """)
                s1_next = gr.Button(t('en', 's1_btn'), variant="primary", size="lg")

        # --- SLIDE 2: SARAH (Reveal Interaction) ---
        with gr.Group(visible=False, elem_id="step-2") as step_2:
            with gr.Column(elem_classes=["scenario-box"]):
                s2_title = gr.Markdown(f"## {t('en', 's2_title')}", elem_classes=["slide-title"])
                
                # Case File Visual
                s2_case_html = gr.HTML(f"""
                <div class='case-card' style='border-left: 6px solid #dc2626;'>
                    <div class='case-header'>
                        <span>{t('en', 's2_card_label')}</span>
                        <span>👤 Sarah</span>
                    </div>
                    <div class='case-body'>
                        <div style='font-size:1.2rem; font-weight:800; margin-bottom:10px;'>{t('en', 's2_ai_pred')}</div>
                        <p>{t('en', 's2_desc')}</p>
                    </div>
                </div>
                """)
                
                s2_reveal_btn = gr.Button(t('en', 's2_reveal_btn'), variant="secondary")
                
                # Reveal Box (Hidden initially)
                s2_outcome_box = gr.HTML(visible=False) 
                
                s2_next = gr.Button(t('en', 's2_btn'), visible=False, variant="primary")

        # --- SLIDE 3: JAMES (Reveal Interaction) ---
        with gr.Group(visible=False, elem_id="step-3") as step_3:
            with gr.Column(elem_classes=["scenario-box"]):
                s3_title = gr.Markdown(f"## {t('en', 's3_title')}", elem_classes=["slide-title"])
                
                s3_case_html = gr.HTML(f"""
                <div class='case-card' style='border-left: 6px solid #16a34a;'>
                    <div class='case-header'>
                        <span>{t('en', 's3_card_label')}</span>
                        <span>👤 James</span>
                    </div>
                    <div class='case-body'>
                        <div style='font-size:1.2rem; font-weight:800; margin-bottom:10px;'>{t('en', 's3_ai_pred')}</div>
                        <p>{t('en', 's3_desc')}</p>
                    </div>
                </div>
                """)
                
                s3_reveal_btn = gr.Button(t('en', 's3_reveal_btn'), variant="secondary")
                s3_outcome_box = gr.HTML(visible=False)
                s3_next = gr.Button(t('en', 's3_btn'), visible=False, variant="primary")

        # --- SLIDE 4: THE DILEMMA (Slider) ---
        with gr.Group(visible=False, elem_id="step-4") as step_4:
            with gr.Column(elem_classes=["scenario-box"]):
                s4_title = gr.Markdown(f"## {t('en', 's4_title')}", elem_classes=["slide-title"])
                s4_intro = gr.Markdown(f"### {t('en', 's4_intro')}")
                
                s4_slider = gr.Slider(minimum=0, maximum=100, value=50, step=5, label=t('en', 's4_label'))
                s4_bars_html = gr.HTML() # Dynamic output
                s4_feed_text = gr.HTML() # Dynamic output
                
                s4_next = gr.Button(t('en', 's4_btn'), variant="primary")

        # --- SLIDE 5: CONCLUSION (Original Text, New Style) ---
        with gr.Group(visible=False, elem_id="step-5") as step_5:
            with gr.Column(elem_classes=["scenario-box"]):
                s5_title = gr.Markdown(f"## {t('en', 's5_title')}", elem_classes=["slide-title"])
                s5_content = gr.HTML(f"""
                <div class='slide-body' style='text-align:center;'>
                    <p style='font-size:1.2rem;'>{t('en', 's5_p1')}</p>
                    <div class='hint-box' style='margin: 30px 0; text-align:left;'>
                        <p>{t('en', 's5_p2')}</p>
                        <p>{t('en', 's5_p3')}</p>
                    </div>
                    <div style='background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); padding:20px; border-radius:12px; border:2px solid var(--color-accent);'>
                        <h2 style='margin:0; font-size:1.5rem;'>{t('en', 's5_scroll')}</h2>
                        <p>{t('en', 's5_find')}</p>
                    </div>
                </div>
                """)
                s5_restart = gr.Button(t('en', 's5_btn'), variant="secondary")

        # --- JS Navigation Helper ---
        def nav_js(target_id):
            return f"""
            ()=>{{
                document.getElementById('nav-loading-overlay').style.display = 'flex';
                setTimeout(() => {{ document.getElementById('nav-loading-overlay').style.opacity = '1'; }}, 10);
                setTimeout(() => {{
                    const anchor = document.getElementById('app_top_anchor');
                    if(anchor) anchor.scrollIntoView({{behavior:'smooth', block:'start'}});
                    document.getElementById('nav-loading-overlay').style.opacity = '0';
                    setTimeout(() => {{ document.getElementById('nav-loading-overlay').style.display = 'none'; }}, 300);
                }}, 600);
            }}
            """

        # --- Event Handlers ---

        # Reveal Logic (Slide 2)
        def reveal_s2(lang):
            html = f"""
            <div class='hint-box' style='border-left: 4px solid #dc2626; background: rgba(220, 38, 38, 0.05);'>
                <div style='font-weight:800; color:#dc2626; font-size:1.1rem; margin-bottom:5px;'>{t(lang, 's2_reveal_title')}</div>
                <div style='margin-bottom:15px; font-size:1.1rem;'>{t(lang, 's2_reveal_text')}</div>
                <div style='border-top:1px solid #fecaca; padding-top:10px;'>
                    <div style='font-weight:700; color:#b91c1c;'>{t(lang, 's2_analysis_title')}</div>
                    <div style='font-size:0.95rem; color:var(--body-text-color);'>{t(lang, 's2_analysis_text')}</div>
                </div>
            </div>
            """
            return gr.HTML(value=html, visible=True), gr.Button(visible=True), gr.Button(visible=False)

        s2_reveal_btn.click(reveal_s2, inputs=[lang_state], outputs=[s2_outcome_box, s2_next, s2_reveal_btn])

        # Reveal Logic (Slide 3)
        def reveal_s3(lang):
            html = f"""
            <div class='hint-box' style='border-left: 4px solid #16a34a; background: rgba(22, 163, 74, 0.05);'>
                <div style='font-weight:800; color:#16a34a; font-size:1.1rem; margin-bottom:5px;'>{t(lang, 's3_reveal_title')}</div>
                <div style='margin-bottom:15px; font-size:1.1rem;'>{t(lang, 's3_reveal_text')}</div>
                <div style='border-top:1px solid #bbf7d0; padding-top:10px;'>
                    <div style='font-weight:700; color:#15803d;'>{t(lang, 's3_analysis_title')}</div>
                    <div style='font-size:0.95rem; color:var(--body-text-color);'>{t(lang, 's3_analysis_text')}</div>
                </div>
            </div>
            """
            return gr.HTML(value=html, visible=True), gr.Button(visible=True), gr.Button(visible=False)

        s3_reveal_btn.click(reveal_s3, inputs=[lang_state], outputs=[s3_outcome_box, s3_next, s3_reveal_btn])

        # Slider Logic (Slide 4)
        def update_bars(lang, val):
            # Guard against invalid inputs that could cause a crash
            if val is None: val = 50
            try:
                val = int(val)
            except (ValueError, TypeError):
                val = 50

            fp_count = val
            fn_count = 100 - val
            
            fp_label = t(lang, 's4_fp_label')
            fn_label = t(lang, 's4_fn_label')
            
            html = f"""
            <div style='margin-top:20px; padding:15px; border:1px solid var(--border-color-primary); border-radius:8px; background:var(--body-background-fill);'>
                <div class='bar-container'>
                    <div class='bar-label' style='color:#dc2626;'>{fp_label}</div>
                    <div class='bar-track'>
                        <div class='bar-fill' style='width:{fp_count}%; background:#dc2626;'>{fp_count}</div>
                    </div>
                </div>
                <div class='bar-container'>
                    <div class='bar-label' style='color:#16a34a;'>{fn_label}</div>
                    <div class='bar-track'>
                        <div class='bar-fill' style='width:{fn_count}%; background:#16a34a;'>{fn_count}</div>
                    </div>
                </div>
            </div>
            """
            
            msg = ""
            bg_color = "var(--background-fill-secondary)"
            border_color = "var(--border-color-primary)"
            
            if val < 20:
                msg = t(lang, 's4_feed_lenient')
                bg_color = "rgba(22, 163, 74, 0.1)"
                border_color = "#16a34a"
            elif val > 80:
                msg = t(lang, 's4_feed_strict')
                bg_color = "rgba(220, 38, 38, 0.1)"
                border_color = "#dc2626"
            else:
                msg = t(lang, 's4_feed_tradeoff')
                
            feed_html = f"<div class='hint-box' style='text-align:center; background:{bg_color}; border:1px solid {border_color}; margin-top:20px;'>{msg}</div>"
            return html, feed_html

        # Init slider
        demo.load(update_bars, inputs=[lang_state, s4_slider], outputs=[s4_bars_html, s4_feed_text])
        s4_slider.change(update_bars, inputs=[lang_state, s4_slider], outputs=[s4_bars_html, s4_feed_text])

        # Navigation
        def nav(target):
            return {
                step_1: gr.update(visible=target==1),
                step_2: gr.update(visible=target==2),
                step_3: gr.update(visible=target==3),
                step_4: gr.update(visible=target==4),
                step_5: gr.update(visible=target==5)
            }

        s1_next.click(lambda: nav(2), outputs=[step_1, step_2, step_3, step_4, step_5], js=nav_js("step-2"))
        s2_next.click(lambda: nav(3), outputs=[step_1, step_2, step_3, step_4, step_5], js=nav_js("step-3"))
        s3_next.click(lambda: nav(4), outputs=[step_1, step_2, step_3, step_4, step_5], js=nav_js("step-4"))
        s4_next.click(lambda: nav(5), outputs=[step_1, step_2, step_3, step_4, step_5], js=nav_js("step-5"))
        s5_restart.click(lambda: nav(1), outputs=[step_1, step_2, step_3, step_4, step_5], js=nav_js("step-1"))

        # Language Update
        def update_language(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS: lang = "en"
            
            # Helper for S1 content reconstruction
            s1_html = f"""
            <div class='slide-body'>
                <p>{t(lang, 's1_p1')}</p>
                <p style='margin-top:15px; font-size:1.2rem; text-align:center;'>{t(lang, 's1_p2')}</p>
                <div class='ai-risk-container'>
                    <p>{t(lang, 's1_p3')}</p>
                    <ul>
                        <li style='margin-bottom:8px;'>{t(lang, 's1_li1')}</li>
                        <li>{t(lang, 's1_li2')}</li>
                    </ul>
                </div>
                <p style='margin-top:20px; font-weight:bold; text-align:center;'>{t(lang, 's1_p4')}</p>
            </div>
            """
            
            # Helper for S2 Case
            s2_html = f"""
            <div class='case-card' style='border-left: 6px solid #dc2626;'>
                <div class='case-header'>
                    <span>{t(lang, 's2_card_label')}</span>
                    <span>👤 Sarah</span>
                </div>
                <div class='case-body'>
                    <div style='font-size:1.2rem; font-weight:800; margin-bottom:10px;'>{t(lang, 's2_ai_pred')}</div>
                    <p>{t(lang, 's2_desc')}</p>
                </div>
            </div>
            """

            # Helper for S3 Case
            s3_html = f"""
            <div class='case-card' style='border-left: 6px solid #16a34a;'>
                <div class='case-header'>
                    <span>{t(lang, 's3_card_label')}</span>
                    <span>👤 James</span>
                </div>
                <div class='case-body'>
                    <div style='font-size:1.2rem; font-weight:800; margin-bottom:10px;'>{t(lang, 's3_ai_pred')}</div>
                    <p>{t(lang, 's3_desc')}</p>
                </div>
            </div>
            """

            # Helper for S5 Content
            s5_html = f"""
            <div class='slide-body' style='text-align:center;'>
                <p style='font-size:1.2rem;'>{t(lang, 's5_p1')}</p>
                <div class='hint-box' style='margin: 30px 0; text-align:left;'>
                    <p>{t(lang, 's5_p2')}</p>
                    <p>{t(lang, 's5_p3')}</p>
                </div>
                <div style='background:linear-gradient(to right, rgba(99,102,241,0.1), rgba(16,185,129,0.1)); padding:20px; border-radius:12px; border:2px solid var(--color-accent);'>
                    <h2 style='margin:0; font-size:1.5rem;'>{t(lang, 's5_scroll')}</h2>
                    <p>{t(lang, 's5_find')}</p>
                </div>
            </div>
            """

            return [
                lang,
                f"## {t(lang, 's1_title')}", s1_html, t(lang, 's1_btn'),
                f"## {t(lang, 's2_title')}", s2_html, t(lang, 's2_reveal_btn'), t(lang, 's2_btn'),
                f"## {t(lang, 's3_title')}", s3_html, t(lang, 's3_reveal_btn'), t(lang, 's3_btn'),
                f"## {t(lang, 's4_title')}", f"### {t(lang, 's4_intro')}", 
                gr.update(label=t(lang, 's4_label')), # FIX: Safely update label without changing value
                t(lang, 's4_btn'),
                f"## {t(lang, 's5_title')}", s5_html, t(lang, 's5_btn')
            ]

        demo.load(update_language, inputs=None, outputs=[
            lang_state,
            s1_title, s1_content, s1_next,
            s2_title, s2_case_html, s2_reveal_btn, s2_next,
            s3_title, s3_case_html, s3_reveal_btn, s3_next,
            s4_title, s4_intro, s4_slider, s4_next,
            s5_title, s5_content, s5_restart
        ])

    return demo

def launch_ai_consequences_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_ai_consequences_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)



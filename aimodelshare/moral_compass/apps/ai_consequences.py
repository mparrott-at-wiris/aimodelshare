"""
AI Consequences - Gradio application for the Justice & Equity Challenge.
Updated with i18n support for English (en), Spanish (es), and Catalan (ca).
"""
import contextlib
import os
import gradio as gr

# -------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# -------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "title": "⚠️ What If the AI Was Wrong?",
        "intro_box": "You just made decisions based on an AI's predictions.<br>But AI systems are not perfect. Let's explore what happens when they make mistakes.",
        "loading": "⏳ Loading...",
        # Step 1
        "s1_title": "The Stakes of AI Predictions",
        "s1_p1": "In the previous exercise, you relied on an AI system to predict which defendants were at <b>High</b>, <b>Medium</b>, or <b>Low</b> risk of re-offending.",
        "s1_p2": "<b>But what if those predictions were incorrect?</b>",
        "s1_p3": "AI systems make two types of errors that have very different consequences:",
        "s1_li1": "<b>False Positives</b> - Incorrectly predicting HIGH risk",
        "s1_li2": "<b>False Negatives</b> - Incorrectly predicting LOW risk",
        "s1_p4": "Let's examine each type of error and its real-world impact.",
        "btn_next_fp": "Next: False Positives ▶️",
        # Step 2 (False Positives)
        "s2_title": "🔴 False Positives: Predicting Danger Where None Exists",
        "s2_card_title": "What is a False Positive?",
        "s2_def": "A <b>false positive</b> occurs when the AI predicts someone is <b style='color:#dc2626;'>HIGH RISK</b>, but they would NOT have actually re-offended if released.",
        "s2_ex_title": "Example Scenario:",
        "s2_ex_li1": "• Sarah was flagged as <b style='color:#dc2626;'>HIGH RISK</b>",
        "s2_ex_li2": "• Based on this, the judge kept her in prison",
        "s2_ex_li3": "• In reality, Sarah would have rebuilt her life and never committed another crime",
        "s2_cost_title": "The Human Cost:",
        "s2_cost_li1": "People who would not re-offend spend unnecessary time in prison",
        "s2_cost_li2": "Families are separated for longer than needed",
        "s2_cost_li3": "Job opportunities and rehabilitation are delayed",
        "s2_cost_li4": "Trust in the justice system erodes",
        "s2_cost_li5": "Disproportionate impact on marginalized communities",
        "s2_key": "<b>Key Point:</b> False positives mean the AI is being <b>too cautious</b>, keeping people locked up who should be free.",
        "btn_back": "◀️ Back",
        "btn_next_fn": "Next: False Negatives ▶️",
        # Step 3 (False Negatives)
        "s3_title": "🔵 False Negatives: Missing Real Danger",
        "s3_card_title": "What is a False Negative?",
        "s3_def": "A <b>false negative</b> occurs when the AI predicts someone is <b style='color:#16a34a;'>LOW RISK</b>, but they DO actually re-offend after being released.",
        "s3_ex_title": "Example Scenario:",
        "s3_ex_li1": "• James was flagged as <b style='color:#16a34a;'>LOW RISK</b>",
        "s3_ex_li2": "• Based on this, the judge released him on parole",
        "s3_ex_li3": "• Unfortunately, James did commit another serious crime",
        "s3_cost_title": "The Human Cost:",
        "s3_cost_li1": "New victims of preventable crimes",
        "s3_cost_li2": "Loss of public trust in the justice system",
        "s3_cost_li3": "Media scrutiny and backlash against judges",
        "s3_cost_li4": "Political pressure to be 'tough on crime'",
        "s3_cost_li5": "Potential harm to communities and families",
        "s3_key": "<b>Key Point:</b> False negatives mean the AI is being <b>too lenient</b>, releasing people who pose a real danger to society.",
        "btn_next_dil": "Next: The Dilemma ▶️",
        # Step 4 (Dilemma)
        "s4_title": "⚖️ The Impossible Balance",
        "s4_card_title": "Every AI System Makes Trade-offs",
        "s4_p1": "Here's the harsh reality: <b>No AI system can eliminate both types of errors.</b>",
        "s4_sub1": "<b>If you make the AI more cautious:</b>",
        "s4_sub1_li1": "✓ Fewer false negatives (fewer people who pose a real risk are released)",
        "s4_sub1_li2": "✗ More false positives (more people who would not re-offend kept in prison)",
        "s4_sub2": "<b>If you make the AI more lenient:</b>",
        "s4_sub2_li1": "✓ Fewer false positives (more people who would not re-offend are released)",
        "s4_sub2_li2": "✗ More false negatives (more people who pose a real risk released)",
        "s4_eth_title": "The Ethical Question:",
        "s4_q1": "Which mistake is worse?",
        "s4_q2": "• Keeping people who would not re-offend in prison?<br>• Or releasing individuals who pose a real risk?",
        "s4_conc": "<b>There is no universally 'correct' answer.</b> Different societies, legal systems, and ethical frameworks weigh these trade-offs differently.",
        "s4_final": "<b>This is why understanding AI is crucial.</b> We need to know how these systems work so we can make informed decisions about when and how to use them.",
        "btn_cont": "Continue to Learn About AI ▶️",
        # Step 5 (Completion)
        "s5_title": "✅ Section Complete!",
        "s5_p1": "You now understand the consequences of AI errors in high-stakes decisions.",
        "s5_p2": "<b>Next up:</b> Learn what AI actually is and how these prediction systems work.",
        "s5_p3": "This knowledge will help you understand how to build better, more ethical AI systems.",
        "s5_scroll": "👇 SCROLL DOWN 👇",
        "s5_find": "Find the next section below to continue your journey.",
        "btn_review": "◀️ Back to Review"
    },
    "es": {
        "title": "⚠️ ¿Y si la IA estuviera equivocada?",
        "intro_box": "Acabas de tomar decisiones basadas en las predicciones de una IA.<br>Pero los sistemas de IA no son perfectos. Exploremos qué sucede cuando cometen errores.",
        "loading": "⏳ Cargando...",
        # Step 1
        "s1_title": "Los riesgos de las predicciones de IA",
        "s1_p1": "En el ejercicio anterior, confiaste en un sistema de IA para predecir qué personas presas tenían un riesgo <b>alto</b>, <b>medio</b> o <b>bajo</b> de reincidir.",
        "s1_p2": "<b>¿Pero qué pasa si esas predicciones eran incorrectas?</b>",
        "s1_p3": "Los sistemas de IA cometen dos tipos de errores que tienen consecuencias muy diferentes:",
        "s1_li1": "<b>Falsos positivos</b> - Predecir incorrectamente ALTO riesgo",
        "s1_li2": "<b>Falsos negativos</b> - Predecir incorrectamente BAJO riesgo",
        "s1_p4": "Examinemos cada tipo de error y su impacto en el mundo real.",
        "btn_next_fp": "Siguiente: Falsos positivos ▶️",
        # Step 2
        "s2_title": "🔴 Falsos positivos: El riesgo inexistente",
        "s2_card_title": "¿Qué es un falso positivo?",
        "s2_def": "Un <b>falso positivo</b> ocurre cuando la IA predice que alguien es de <b style='color:#dc2626;'>ALTO RIESGO</b>, pero en realidad NO habría reincidido si hubiera sido puesto en libertad.",
        "s2_ex_title": "Escenario de ejemplo:",
        "s2_ex_li1": "• Sarah fue marcada como <b style='color:#dc2626;'>ALTO RIESGO</b>",
        "s2_ex_li2": "• Basado en esto, el tribunal la mantuvo en prisión",
        "s2_ex_li3": "• En realidad, Sarah habría rehecho su vida y nunca habría cometido otro delito",
        "s2_cost_title": "El coste humano:",
        "s2_cost_li1": "Personas que no reincidirían pasan tiempo innecesario en prisión",
        "s2_cost_li2": "Las familias son separadas por más tiempo del necesario",
        "s2_cost_li3": "Las oportunidades laborales y la rehabilitación se retrasan",
        "s2_cost_li4": "La confianza en el sistema judicial se erosiona",
        "s2_cost_li5": "Impacto desproporcionado en comunidades marginadas",
        "s2_key": "<b>Punto clave:</b> Los falsos positivos significan que la IA está siendo <b>demasiado cautelosa</b>, manteniendo en prisión a personas que deberían ser puestas en libertad.",
        "btn_back": "◀️ Atrás",
        "btn_next_fn": "Siguiente: Falsos negativos ▶️",
        # Step 3
        "s3_title": "🔵 Falsos negativos: El riesgo no detectado",
        "s3_card_title": "¿Qué es un falso negativo?",
        "s3_def": "Un <b>falso negativo</b> ocurre cuando la IA predice que alguien es de <b style='color:#16a34a;'>BAJO RIESGO</b>, pero SÍ vuelve a cometer un delito después de ser liberado.",
        "s3_ex_title": "Escenario de ejemplo:",
        "s3_ex_li1": "• James fue marcado como <b style='color:#16a34a;'>BAJO RIESGO</b>",
        "s3_ex_li2": "• Basado en esto, el tribunal le concedió la libertad condicional",
        "s3_ex_li3": "• Desafortunadamente, James cometió otro delito grave",
        "s3_cost_title": "El coste humano:",
        "s3_cost_li1": "Nuevas víctimas de delitos prevenibles",
        "s3_cost_li2": "Pérdida de confianza pública en el sistema judicial",
        "s3_cost_li3": "Escrutinio mediático y reacciones contra los tribunales",
        "s3_cost_li4": "Presión política para adoptar medidas severas contra la delincuencia.",
        "s3_cost_li5": "Daño potencial a comunidades y familias",
        "s3_key": "<b>Punto clave:</b> Los falsos negativos significan que la IA está siendo <b>demasiado indulgente</b>, poniendo en libertad a personas que representan un peligro real para la sociedad.",
        "btn_next_dil": "Siguiente: El dilema ▶️",
        # Step 4
        "s4_title": "⚖️ El equilibrio imposible",
        "s4_card_title": "Todo sistema de IA presenta un dilema",
        "s4_p1": "Esta es la dura realidad: <b>Ningún sistema de IA puede eliminar ambos tipos de errores.</b>",
        "s4_sub1": "<b>Si haces que la IA sea más cautelosa:</b>",
        "s4_sub1_li1": "✓ Menos falsos negativos (menos personas que representan un peligro real liberadas)",
        "s4_sub1_li2": "✗ Más falsos positivos (más personas que no reincidirían permanecen en prisión)",
        "s4_sub2": "<b>Si haces que la IA sea más indulgente:</b>",
        "s4_sub2_li1": "✓ Menos falsos positivos (más personas que no reincidirían son puestas en libertad)",
        "s4_sub2_li2": "✗ Más falsos negativos (más personas que representan un peligro real liberadas son puestas en libertad)",
        "s4_eth_title": "La pregunta ética:",
        "s4_q1": "¿Qué error es peor?",
        "s4_q2": "• ¿Mantener a personas que no reincidirían en prisión?<br>• ¿O poner en libertad a personas que representan un peligro real?",
        "s4_conc": "<b>No hay una respuesta universalmente 'correcta'.</b> Diferentes sociedades, sistemas legales y marcos éticos sopesan estos dilemas de manera diferente.",
        "s4_final": "<b>Por eso es crucial entender la IA.</b> Necesitamos saber cómo funcionan estos sistemas para tomar decisiones informadas sobre cuándo y cómo usarlos.",
        "btn_cont": "Continuar Aprendiendo sobre la IA ▶️",
        # Step 5
        "s5_title": "✅ Sección completada",
        "s5_p1": "Ahora entiendes las consecuencias de los errores de la IA en decisiones de alto riesgo.",
        "s5_p2": "<b>A continuación:</b> Aprende qué es realmente la IA y cómo funcionan estos sistemas de predicción.",
        "s5_p3": "Este conocimiento te ayudará a entender cómo construir sistemas de IA mejores y más éticos.",
        "s5_scroll": "👇 DESPLÁZATE HACIA ABAJO 👇",
        "s5_find": "Encuentra la siguiente sección abajo para continuar tu viaje.",
        "btn_review": "◀️ Volver a revisar"
    },
    "ca": {
        "title": "⚠️ I si la IA s'hagués equivocat?",
        "intro_box": "Acabes de prendre decisions basades en les prediccions d'una IA.<br>Però els sistemes d'IA no són perfectes. Explorem què passa quan cometen errors.",
        "loading": "⏳ Carregant...",
        # Step 1
        "s1_title": "Els riscos de les prediccions d'IA",
        "s1_p1": "En l'exercici anterior, has confiat en un sistema d'IA per predir quines persones preses tenien un risc <b>Alt</b>, <b>Mitjà</b> o <b>Baix</b> de reincidir.",
        "s1_p2": "<b>Però què passa si aquestes prediccions eren incorrectes?</b>",
        "s1_p3": "Els sistemes d'IA cometen dos tipus d'errors que tenen conseqüències molt diferents:",
        "s1_li1": "<b>Falsos positius</b> - Predir incorrectament ALT risc",
        "s1_li2": "<b>Falsos Negatius</b> - Predir incorrectament BAIX risc",
        "s1_p4": "Examinem cada tipus d'error i el seu impacte en el món real.",
        "btn_next_fp": "Següent: Falsos positius ▶️",
        # Step 2
        "s2_title": "🔴 Falsos positius: El risc inexistent",
        "s2_card_title": "Què és un fals positiu?",
        "s2_def": "Un <b>fals positiu</b> es produeix quan la IA prediu que algú és d'<b style='color:#dc2626;'>ALT RISC</b>, però en realitat NO hauria reincidit si hagués estat posat en llibertat.",
        "s2_ex_title": "Escenari d'exemple:",
        "s2_ex_li1": "• La Sarah va ser marcada com d'<b style='color:#dc2626;'>ALT RISC</b>",
        "s2_ex_li2": "• Basat en això, el tribunal la va mantenir a la presó",
        "s2_ex_li3": "• En realitat, la Sarah hauria refet la seva vida i mai hauria comès un altre delicte",
        "s2_cost_title": "El cost humà:",
        "s2_cost_li1": "Persones innocents passen temps innecessari a la presó",
        "s2_cost_li2": "Les famílies són separades per més temps del necessari",
        "s2_cost_li3": "Les oportunitats laborals i la rehabilitació es retarden",
        "s2_cost_li4": "La confiança en el sistema judicial s'erosiona",
        "s2_cost_li5": "Impacte desproporcionat en comunitats marginades",
        "s2_key": "<b>Punt clau:</b> Els falsos positius signifiquen que la IA està sent <b>massa cautelosa</b>, mantenint a la presó a persones que haurien de ser posades en llibertat.",
        "btn_back": "◀️ Enrere",
        "btn_next_fn": "Següent: Falsos negatius ▶️",
        # Step 3
        "s3_title": "🔵 Falsos negatius: El risc no detectat",
        "s3_card_title": "Què és un fals negatiu?",
        "s3_def": "Un <b>fals negatiu</b> es produeix quan la IA prediu que algú és de <b style='color:#16a34a;'>BAIX RISC</b>, però SÍ torna a cometre un delicte després de ser posat en llibertat.",
        "s3_ex_title": "Escenari d'exemple:",
        "s3_ex_li1": "• En James va ser marcat com de <b style='color:#16a34a;'>BAIX RISC</b>",
        "s3_ex_li2": "• Basat en això, el tribunal li va concedir la llibertat condicional",
        "s3_ex_li3": "• Malauradament, en James va cometre un altre delicte greu",
        "s3_cost_title": "El cost humà:",
        "s3_cost_li1": "Noves víctimes de delictes prevenibles",
        "s3_cost_li2": "Pèrdua de confiança pública en el sistema judicial",
        "s3_cost_li3": "Escrutini mediàtic i reaccions contra els tribunals",
        "s3_cost_li4": "Pressió política per adoptar mesures severes contra la delinqüència",
        "s3_cost_li5": "Dany potencial a comunitats i famílies",
        "s3_key": "<b>Punt clau:</b> Els falsos negatius signifiquen que la IA està sent <b>massa indulgent</b>, posant en llibertat persones que representen un perill real per a la societat.",
        "btn_next_dil": "Següent: El dilema ▶️",
        # Step 4
        "s4_title": "⚖️ L'equilibri impossible",
        "s4_card_title": "Tot sistema d'IA presenta un dilema",
        "s4_p1": "Aquesta és la dura realitat: <b>Cap sistema d'IA pot eliminar els dos tipus d'errors.</b>",
        "s4_sub1": "<b>Si fas que la IA sigui més cautelosa:</b>",
        "s4_sub1_li1": "✓ Menys falsos negatius (menys persones que representen un perill real són posades en llibertat)",
        "s4_sub1_li2": "✗ Més falsos positius (més persones que no reincidirien es mantenen a la presó)",
        "s4_sub2": "<b>Si fas que la IA sigui més indulgent:</b>",
        "s4_sub2_li1": "✓ Menys falsos positius (més persones que no reincidirien són posades en llibertat)",
        "s4_sub2_li2": "✗ Més falsos negatius (més persones que representen un perill real són posades en llibertat)",
        "s4_eth_title": "La pregunta ètica:",
        "s4_q1": "Quin error és pitjor?",
        "s4_q2": "• Mantenir a la presó persones que no reincidirien?<br>• O posar en llibertat persones que representen un perill real?",
        "s4_conc": "<b>No hi ha una resposta universalment 'correcta'.</b> Diferents societats, sistemes legals i marcs ètics sospesen aquests dilemes de manera diferent.",
        "s4_final": "<b>Per això és crucial entendre la IA.</b> Necessitem saber com funcionen aquests sistemes per prendre decisions informades sobre quan i com utilitzar-los.",
        "btn_cont": "Continuar aprenent sobre la IA ▶️",
        # Step 5
        "s5_title": "✅ Secció completada",
        "s5_p1": "Ara entens les conseqüències dels errors de la IA en decisions d'alt risc.",
        "s5_p2": "<b>A continuació:</b> Aprèn què és realment la IA i com funcionen aquests sistemes de predicció.",
        "s5_p3": "Aquest coneixement t'ajudarà a entendre com construir sistemes d'IA millors i més ètics.",
        "s5_scroll": "👇 DESPLAÇA'T CAP AVALL 👇",
        "s5_find": "Troba la següent secció a sota per continuar el teu viatge.",
        "btn_review": "◀️ Tornar a revisar"
    }
}

def create_ai_consequences_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the AI Consequences Gradio Blocks app."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError("Gradio is required.") from e

    # --- HTML Generator Helpers for i18n ---
    def t(lang, key):
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

    def _get_step1_html(lang):
        return f"""
        <div class='step-card'>
          <p>{t(lang, 's1_p1')}</p>
          <p style='margin-top:20px;'>{t(lang, 's1_p2')}</p>
          <p style='margin-top:20px;'>{t(lang, 's1_p3')}</p>
          <ul style='font-size:18px; margin-top:12px;'>
              <li>{t(lang, 's1_li1')}</li>
              <li>{t(lang, 's1_li2')}</li>
          </ul>
          <p style='margin-top:20px;'>{t(lang, 's1_p4')}</p>
        </div>
        """

    def _get_step2_html(lang):
        return f"""
        <div class='step-card step-card-warning'>
          <h3 style='color:#b45309; margin-top:0;'>{t(lang, 's2_card_title')}</h3>
          <p>{t(lang, 's2_def')}</p>
          <div class='inner-card'>
              <h4 style='margin-top:0;'>{t(lang, 's2_ex_title')}</h4>
              <p style='font-size:18px;'>
              {t(lang, 's2_ex_li1')}<br>
              {t(lang, 's2_ex_li2')}<br>
              {t(lang, 's2_ex_li3')}
              </p>
          </div>
          <h3 style='color:#b45309;'>{t(lang, 's2_cost_title')}</h3>
          <ul style='font-size:18px;'>
              <li>{t(lang, 's2_cost_li1')}</li>
              <li>{t(lang, 's2_cost_li2')}</li>
              <li>{t(lang, 's2_cost_li3')}</li>
              <li>{t(lang, 's2_cost_li4')}</li>
              <li>{t(lang, 's2_cost_li5')}</li>
          </ul>
          <div class='keypoint-box'>
              <p style='font-size:18px; margin:0;'>{t(lang, 's2_key')}</p>
          </div>
        </div>
        """

    def _get_step3_html(lang):
        return f"""
        <div class='step-card step-card-success'>
          <h3 style='color:#15803d; margin-top:0;'>{t(lang, 's3_card_title')}</h3>
          <p>{t(lang, 's3_def')}</p>
          <div class='inner-card'>
              <h4 style='margin-top:0;'>{t(lang, 's3_ex_title')}</h4>
              <p style='font-size:18px;'>
              {t(lang, 's3_ex_li1')}<br>
              {t(lang, 's3_ex_li2')}<br>
              {t(lang, 's3_ex_li3')}
              </p>
          </div>
          <h3 style='color:#15803d;'>{t(lang, 's3_cost_title')}</h3>
          <ul style='font-size:18px;'>
              <li>{t(lang, 's3_cost_li1')}</li>
              <li>{t(lang, 's3_cost_li2')}</li>
              <li>{t(lang, 's3_cost_li3')}</li>
              <li>{t(lang, 's3_cost_li4')}</li>
              <li>{t(lang, 's3_cost_li5')}</li>
          </ul>
          <div class='keypoint-box'>
              <p style='font-size:18px; margin:0;'>{t(lang, 's3_key')}</p>
          </div>
        </div>
        """

    def _get_step4_html(lang):
        return f"""
        <div class='step-card step-card-balance'>
          <h3 style='color:#7e22ce; margin-top:0;'>{t(lang, 's4_card_title')}</h3>
          <p>{t(lang, 's4_p1')}</p>
          <div class='inner-card-wide'>
              <p style='font-size:18px; margin-bottom:16px;'>{t(lang, 's4_sub1')}</p>
              <ul style='font-size:18px;'>
                  <li>{t(lang, 's4_sub1_li1')}</li>
                  <li>{t(lang, 's4_sub1_li2')}</li>
              </ul>
              <hr style='margin:20px 0;'>
              <p style='font-size:18px; margin-bottom:16px;'>{t(lang, 's4_sub2')}</p>
              <ul style='font-size:18px;'>
                  <li>{t(lang, 's4_sub2_li1')}</li>
                  <li>{t(lang, 's4_sub2_li2')}</li>
              </ul>
          </div>
          <h3 style='color:#7e22ce;'>{t(lang, 's4_eth_title')}</h3>
          <div class='keypoint-box'>
              <p style='font-size:20px; font-weight:bold; margin:0;'>{t(lang, 's4_q1')}</p>
              <p style='font-size:18px; margin-top:12px; margin-bottom:0;'>{t(lang, 's4_q2')}</p>
          </div>
          <p style='margin-top:24px; font-size:18px;'>{t(lang, 's4_conc')}</p>
          <div class='highlight-soft'>
              <p style='font-size:18px; margin:0;'>{t(lang, 's4_final')}</p>
          </div>
        </div>
        """

    def _get_step5_html(lang):
        return f"""
        <div style='text-align:center;'>
            <h2 style='font-size: 2.5rem;'>{t(lang, 's5_title')}</h2>
            <div class='completion-box'>
                <p>{t(lang, 's5_p1')}</p>
                <p style='margin-top:24px;'>{t(lang, 's5_p2')}</p>
                <p style='margin-top:24px;'>{t(lang, 's5_p3')}</p>
                <h1 style='margin:20px 0; font-size: 3rem;'>{t(lang, 's5_scroll')}</h1>
                <p style='font-size:1.1rem;'>{t(lang, 's5_find')}</p>
            </div>
        </div>
        """

    css = """
    /* (CSS remains exactly as provided in the previous snippet) */
    .large-text { font-size: 20px !important; }
    .loading-title { font-size: 2rem; color: var(--secondary-text-color); }
    .warning-box { background-color: var(--block-background-fill) !important; border-left: 6px solid #dc2626 !important; color: var(--body-text-color); }
    .consequences-intro-box { text-align: center; font-size: 18px; max-width: 900px; margin: auto; padding: 20px; border-radius: 12px; background-color: var(--block-background-fill); color: var(--body-text-color); border: 2px solid #dc2626; box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08); }
    .step-card { font-size: 20px; padding: 28px; border-radius: 16px; background-color: var(--block-background-fill); color: var(--body-text-color); border: 1px solid var(--border-color-primary); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06); }
    .step-card-warning { border-width: 3px; border-color: #f59e0b; }
    .step-card-success { border-width: 3px; border-color: #16a34a; }
    .step-card-balance { border-width: 3px; border-color: #9333ea; }
    .inner-card { background-color: var(--body-background-fill); color: var(--body-text-color); padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid var(--border-color-primary); }
    .inner-card-wide { background-color: var(--body-background-fill); color: var(--body-text-color); padding: 24px; border-radius: 12px; margin: 24px 0; border: 1px solid var(--border-color-primary); }
    .keypoint-box { background-color: var(--block-background-fill); color: var(--body-text-color); padding: 16px; border-radius: 8px; margin-top: 20px; border-left: 6px solid #dc2626; }
    .highlight-soft { background-color: var(--block-background-fill); color: var(--body-text-color); padding: 16px; border-radius: 8px; margin-top: 20px; border: 1px solid var(--border-color-primary); }
    .completion-box { font-size: 1.3rem; padding: 28px; border-radius: 16px; background-color: var(--block-background-fill); color: var(--body-text-color); border: 2px solid var(--color-accent); box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08); }
    #nav-loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: color-mix(in srgb, var(--body-background-fill) 95%, transparent); z-index: 9999; display: none; flex-direction: column; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.3s ease; }
    .nav-spinner { width: 50px; height: 50px; border: 5px solid var(--border-color-primary); border-top: 5px solid var(--color-accent); border-radius: 50%; animation: nav-spin 1s linear infinite; margin-bottom: 20px; }
    @keyframes nav-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    #nav-loading-text { font-size: 1.3rem; font-weight: 600; color: var(--color-accent); }
    @media (prefers-color-scheme: dark) { .consequences-intro-box, .step-card, .inner-card, .inner-card-wide, .keypoint-box, .highlight-soft, .completion-box { background-color: #2D323E; color: white; border-color: #555555; box-shadow: none; } .inner-card, .inner-card-wide { background-color: #181B22; } #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); } .nav-spinner { border-color: rgba(148, 163, 184, 0.4); border-top-color: var(--color-accent); } }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # --- Dynamic Text Components ---
        # We assign them to variables so we can return them in the update function
        
        c_main_title = gr.Markdown("<h1 style='text-align:center;'>⚠️ What If the AI Was Wrong?</h1>")
        c_intro_box = gr.Markdown(f"<div class='consequences-intro-box'>{t('en', 'intro_box')}</div>")
        gr.HTML("<hr style='margin:24px 0;'>")

        with gr.Column(visible=False) as loading_screen:
            c_loading_title = gr.Markdown(f"<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t('en', 'loading')}</h2></div>")

        # Step 1
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            c_s1_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's1_title')}</h2>")
            c_s1_html = gr.HTML(_get_step1_html("en"))
            step_1_next = gr.Button(t('en', 'btn_next_fp'), variant="primary", size="lg")

        # Step 2
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            c_s2_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's2_title')}</h2>")
            c_s2_html = gr.HTML(_get_step2_html("en"))
            with gr.Row():
                step_2_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_2_next = gr.Button(t('en', 'btn_next_fn'), variant="primary", size="lg")

        # Step 3
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            c_s3_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's3_title')}</h2>")
            c_s3_html = gr.HTML(_get_step3_html("en"))
            with gr.Row():
                step_3_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_3_next = gr.Button(t('en', 'btn_next_dil'), variant="primary", size="lg")

        # Step 4
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            c_s4_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's4_title')}</h2>")
            c_s4_html = gr.HTML(_get_step4_html("en"))
            with gr.Row():
                step_4_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_4_next = gr.Button(t('en', 'btn_cont'), variant="primary", size="lg")

        # Step 5
        with gr.Column(visible=False, elem_id="step-5") as step_5:
            c_s5_html = gr.HTML(_get_step5_html("en"))
            back_to_dilemma_btn = gr.Button(t('en', 'btn_review'))

        # --- I18N UPDATE LOGIC ---
        
        update_targets = [
            c_main_title, c_intro_box, c_loading_title,
            c_s1_title, c_s1_html, step_1_next,
            c_s2_title, c_s2_html, step_2_back, step_2_next,
            c_s3_title, c_s3_html, step_3_back, step_3_next,
            c_s4_title, c_s4_html, step_4_back, step_4_next,
            c_s5_html, back_to_dilemma_btn
        ]

        def update_language(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS:
                lang = "en"
            
            return [
                f"<h1 style='text-align:center;'>{t(lang, 'title')}</h1>",
                f"<div class='consequences-intro-box'>{t(lang, 'intro_box')}</div>",
                f"<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t(lang, 'loading')}</h2></div>",
                # Step 1
                f"<h2 style='text-align:center;'>{t(lang, 's1_title')}</h2>",
                _get_step1_html(lang),
                gr.Button(value=t(lang, 'btn_next_fp')),
                # Step 2
                f"<h2 style='text-align:center;'>{t(lang, 's2_title')}</h2>",
                _get_step2_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_next_fn')),
                # Step 3
                f"<h2 style='text-align:center;'>{t(lang, 's3_title')}</h2>",
                _get_step3_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_next_dil')),
                # Step 4
                f"<h2 style='text-align:center;'>{t(lang, 's4_title')}</h2>",
                _get_step4_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_cont')),
                # Step 5
                _get_step5_html(lang),
                gr.Button(value=t(lang, 'btn_review')),
            ]

        demo.load(update_language, inputs=None, outputs=update_targets)

        # --- NAVIGATION LOGIC ---
        
        all_steps = [step_1, step_2, step_3, step_4, step_5, loading_screen]

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

        step_1_next.click(fn=create_nav_generator(step_1, step_2), outputs=all_steps, js=nav_js("step-2", "Loading..."))
        step_2_back.click(fn=create_nav_generator(step_2, step_1), outputs=all_steps, js=nav_js("step-1", "Loading..."))
        step_2_next.click(fn=create_nav_generator(step_2, step_3), outputs=all_steps, js=nav_js("step-3", "Loading..."))
        step_3_back.click(fn=create_nav_generator(step_3, step_2), outputs=all_steps, js=nav_js("step-2", "Loading..."))
        step_3_next.click(fn=create_nav_generator(step_3, step_4), outputs=all_steps, js=nav_js("step-4", "Loading..."))
        step_4_back.click(fn=create_nav_generator(step_4, step_3), outputs=all_steps, js=nav_js("step-3", "Loading..."))
        step_4_next.click(fn=create_nav_generator(step_4, step_5), outputs=all_steps, js=nav_js("step-5", "Loading..."))
        back_to_dilemma_btn.click(fn=create_nav_generator(step_5, step_4), outputs=all_steps, js=nav_js("step-4", "Loading..."))

    return demo

def launch_ai_consequences_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_ai_consequences_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)



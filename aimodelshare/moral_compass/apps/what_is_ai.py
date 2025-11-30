"""
What is AI - Gradio application for the Justice & Equity Challenge.
Updated with "Open the Black Box" logic and clearer definitions.
"""
import contextlib
import os
import gradio as gr

# -------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# -------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "title": "🤖 What is AI, Anyway?",
        "intro_box": "Before you can build better AI systems, you need to understand what AI actually is.<br>Don't worry - we'll explain it in simple, everyday terms!",
        "loading": "⏳ Loading...",
        # Step 1
        "s1_title": "🎯 A Simple Definition",
        "s1_head": "Artificial Intelligence (AI) is just a fancy name for:",
        "s1_big": "A Prediction Machine",
        "s1_sub": "It treats the world like a math problem: <b>Inputs + Rules = Prediction</b>.",
        "s1_list_title": "Compare: Intuition vs. Math",
        "s1_human_head": "🧠 <b>Human Intuition:</b>",
        "s1_human_text": "Dark clouds? -> I feel like it will rain. -> I'll bring an umbrella.",
        "s1_ai_head": "💻 <b>AI Calculation:</b>",
        "s1_ai_text": "Cloud Density (90%) + Humidity (85%) = <b>95% Rain Probability</b>.",
        "s1_highlight": "AI predicts the future just like you do, but it uses <b>data and math</b> instead of gut feelings.",
        "btn_next_formula": "Next: The AI Formula ▶️",
        # Step 2
        "s2_title": "📐 The Three-Part Formula",
        "s2_intro": "Every AI system works the same way, following this simple formula:",
        "lbl_input": "INPUT",
        "lbl_model": "MODEL",
        "lbl_output": "OUTPUT",
        "desc_input": "Data goes in",
        "desc_model": "The Mathematical Brain", # Updated definition
        "desc_output": "Prediction comes out",
        "s2_ex_title": "Real-World Examples:",
        "s2_ex1_in": "Photo of a dog",
        "s2_ex1_mod": "Image Rules",
        "s2_ex1_out": "\"This is a Golden Retriever\"",
        "s2_ex2_in": "\"How's the weather?\"",
        "s2_ex2_mod": "Language Rules",
        "s2_ex2_out": "A helpful response",
        "s2_ex3_in": "Person's criminal history",
        "s2_ex3_mod": "Risk Assessment Rules",
        "s2_ex3_out": "\"High Risk\" or \"Low Risk\"",
        "btn_back": "◀️ Back",
        "btn_next_learn": "Next: How Models Learn ▶️",
        # Step 3
        "s3_title": "🧠 How Does an AI Model Learn?",
        "s3_h1": "1. It Learns from Examples",
        "s3_p1": "An AI model isn't programmed with answers. Instead, it's trained on a huge number of examples.",
        "s3_p2": "We show it thousands of past cases (<b>examples</b>) and say \"Find the pattern that predicts re-offense.\"",
        "s3_h2": "2. The Training Loop",
        "s3_p3": "The AI \"trains\" by looping through data millions of times:",
        "flow_1": "1. INPUT<br>EXAMPLES",
        "flow_2": "2. MODEL<br>GUESSES",
        "flow_3": "3. CHECK<br>ANSWER",
        "flow_4": "4. ADJUST<br>IMPORTANCE", # Renamed from Weights
        "flow_5": "LEARNED<br>MODEL",
        "s3_vol_title": "🎚️ The \"Volume Knob\" Concept",
        "s3_vol_desc": "Think of the model like a mixing board. When it makes a mistake, it adjusts the <b>Importance (Weight)</b> of the inputs.<br>It might learn to turn the volume <b>UP</b> on \"Prior Crimes\" and turn the volume <b>DOWN</b> on \"Age\".",
        "s3_eth_title": "⚠️ The Ethical Challenge",
        "s3_eth_p": "<b>The model is blind to justice.</b> If the historical data is biased (e.g., certain groups were arrested more often), the AI will simply learn that bias as a mathematical pattern.",
        "btn_next_try": "Next: Try It Yourself ▶️",
        # Step 4 (Interactive)
        "s4_title": "🎮 Try It Yourself!",
        "s4_intro": "<b>Let's look inside the brain of a simple AI.</b><br>Adjust the inputs, and we will show you exactly how the model calculates the score.",
        "s4_sect1": "1️⃣ INPUT: Adjust the Data",
        "lbl_age": "Age",
        "info_age": "Defendant's age",
        "lbl_priors": "Prior Offenses",
        "info_priors": "Number of previous crimes",
        "lbl_severity": "Current Charge Severity",
        "info_severity": "How serious is the current charge?",
        "opt_minor": "Minor",
        "opt_moderate": "Moderate",
        "opt_serious": "Serious",
        "s4_sect2": "2️⃣ MODEL: Process the Data",
        "btn_run": "🔮 Run AI Prediction",
        "s4_sect3": "3️⃣ OUTPUT: See the Math",
        "res_placeholder": "Click \"Run AI Prediction\" above to see the calculation.",
        "s4_highlight": "<b>Did you see the math?</b><br><br>The model didn't \"think\" about the person. It just applied a <b>rule</b> (+Points) to every input. Real AI does this same math, just with millions of rules instead of three.",
        "btn_next_conn": "Next: Connection to Justice ▶️",
        # Step 4 Math Breakdown
        "math_title": "🧮 How the Model Decided:",
        "math_pts": "pts",
        "math_total": "Total Score",
        # Step 5
        "s5_title": "🔗 Connecting to Criminal Justice",
        "s5_p1": "<b>Why do we care about 'Math' and 'Inputs'?</b>",
        "s5_p2": "Because the same logic you just used is applied to real people. But there is a key difference between Human and AI bias:",
        "s5_col1_title": "🧑‍⚖️ Human Judge",
        "s5_col1_desc": "Relies on experience and intuition. Bias comes from subconscious beliefs or personal mood.",
        "s5_col2_title": "🤖 AI Model",
        "s5_col2_desc": "Relies on historical data. Bias comes from <b>past statistics</b>. It repeats history exactly.",
        "s5_h2": "The Engineering Goal:",
        "s5_final": "Your job as an engineer is to check the <b>Inputs</b> and test the <b>Model</b> to ensure it doesn't just repeat the mistakes of the past.<br><br><b>Understanding this is the first step to building fairness.</b>",
        "btn_complete": "Complete This Section ▶️",
        # Step 6
        "s6_title": "🎓 You Now Understand AI!",
        "s6_congrats": "<b>Congratulations!</b> You can now answer the question:",
        "s6_li1": "<b>What is AI?</b> A machine that turns data into predictions using math rules.",
        "s6_li2": "<b>How does it work?</b> Input + Model (Rules) = Output.",
        "s6_li3": "<b>How does it learn?</b> By adjusting the \"importance\" of inputs based on past examples.",
        "s6_li4": "<b>Why is it risky?</b> It trusts historical data completely, even if that data contains bias.",
        "s6_li5": "", # Removed 5th point to keep it simpler as per review
        "s6_next": "<b>Next Steps:</b>",
        "s6_next_desc": "In the following sections, you will become the Engineer. You will choose the inputs and build the model yourself.",
        "s6_scroll": "👇 SCROLL DOWN 👇",
        "s6_find": "Continue to the next section below.",
        "btn_review": "◀️ Back to Review",
        # Logic / Dynamic
        "risk_high": "High Risk",
        "risk_med": "Medium Risk",
        "risk_low": "Low Risk",
        "risk_score": "Risk Score:"
    },
    "es": {
        "title": "🤖 ¿Qué es la IA, en realidad?",
        "intro_box": "Antes de poder construir mejores sistemas de IA, necesitas entender qué es realmente la IA.<br>No te preocupes, ¡lo explicaremos en términos simples!",
        "loading": "⏳ Cargando...",
        "s1_title": "🎯 Una Definición Simple",
        "s1_head": "Inteligencia Artificial (IA) es solo un nombre elegante para:",
        "s1_big": "Una Máquina de Predicción",
        "s1_sub": "Trata al mundo como un problema matemático: <b>Entradas + Reglas = Predicción</b>.",
        "s1_list_title": "Compara: Intuición vs. Matemáticas",
        "s1_human_head": "🧠 <b>Intuición Humana:</b>",
        "s1_human_text": "¿Nubes oscuras? -> Siento que lloverá. -> Llevo paraguas.",
        "s1_ai_head": "💻 <b>Cálculo de IA:</b>",
        "s1_ai_text": "Densidad de Nubes (90%) + Humedad (85%) = <b>95% Probabilidad de Lluvia</b>.",
        "s1_highlight": "La IA predice el futuro igual que tú, pero usa <b>datos y matemáticas</b> en lugar de instinto.",
        "btn_next_formula": "Siguiente: La Fórmula de la IA ▶️",
        "s2_title": "📐 La Fórmula de Tres Partes",
        "s2_intro": "Todo sistema de IA funciona igual, siguiendo esta fórmula:",
        "lbl_input": "ENTRADA",
        "lbl_model": "MODELO",
        "lbl_output": "SALIDA",
        "desc_input": "Entran datos",
        "desc_model": "El Cerebro Matemático",
        "desc_output": "Sale predicción",
        "s2_ex_title": "Ejemplos del Mundo Real:",
        "s2_ex1_in": "Foto de un perro",
        "s2_ex1_mod": "Reglas de Imagen",
        "s2_ex1_out": "\"Es un Golden Retriever\"",
        "s2_ex2_in": "\"¿Qué tal el clima?\"",
        "s2_ex2_mod": "Reglas de Lenguaje",
        "s2_ex2_out": "Una respuesta útil",
        "s2_ex3_in": "Historial criminal",
        "s2_ex3_mod": "Reglas de Riesgo",
        "s2_ex3_out": "\"Alto Riesgo\" o \"Bajo Riesgo\"",
        "btn_back": "◀️ Atrás",
        "btn_next_learn": "Siguiente: Cómo Aprenden los Modelos ▶️",
        "s3_title": "🧠 ¿Cómo Aprende un Modelo?",
        "s3_h1": "1. Aprende de Ejemplos",
        "s3_p1": "Un modelo de IA no está programado con respuestas. Se entrena con muchos ejemplos.",
        "s3_p2": "Le mostramos miles de casos pasados (<b>ejemplos</b>) y le decimos \"Encuentra el patrón que predice la reincidencia.\"",
        "s3_h2": "2. El Bucle de Entrenamiento",
        "s3_p3": "La IA \"entrena\" recorriendo datos millones de veces:",
        "flow_1": "1. EJEMPLOS<br>ENTRADA",
        "flow_2": "2. MODELO<br>ADIVINA",
        "flow_3": "3. REVISAR<br>RESPUESTA",
        "flow_4": "4. AJUSTAR<br>IMPORTANCIA",
        "flow_5": "MODELO<br>APRENDIDO",
        "s3_vol_title": "🎚️ El Concepto de \"Volumen\"",
        "s3_vol_desc": "Piensa en el modelo como una mesa de mezclas. Cuando se equivoca, ajusta la <b>Importancia (Peso)</b> de las entradas.<br>Podría aprender a subir el volumen a \"Delitos Previos\" y bajarlo a \"Edad\".",
        "s3_eth_title": "⚠️ El Desafío Ético",
        "s3_eth_p": "<b>El modelo es ciego a la justicia.</b> Si los datos históricos están sesgados, la IA aprenderá ese sesgo como un patrón matemático.",
        "btn_next_try": "Siguiente: Pruébalo Tú Mismo ▶️",
        "s4_title": "🎮 ¡Pruébalo Tú Mismo!",
        "s4_intro": "<b>Miremos dentro del cerebro de una IA simple.</b><br>Ajusta las entradas y te mostraremos exactamente cómo el modelo calcula el puntaje.",
        "s4_sect1": "1️⃣ ENTRADA: Ajusta los Datos",
        "lbl_age": "Edad",
        "info_age": "Edad del acusado",
        "lbl_priors": "Delitos Previos",
        "info_priors": "Número de crímenes anteriores",
        "lbl_severity": "Gravedad del Cargo",
        "info_severity": "¿Qué tan grave es el cargo?",
        "opt_minor": "Menor",
        "opt_moderate": "Moderado",
        "opt_serious": "Grave",
        "s4_sect2": "2️⃣ MODELO: Procesa los Datos",
        "btn_run": "🔮 Ejecutar Predicción IA",
        "s4_sect3": "3️⃣ SALIDA: Ver las Matemáticas",
        "res_placeholder": "Haz clic en \"Ejecutar Predicción IA\" para ver el cálculo.",
        "s4_highlight": "<b>¿Viste las matemáticas?</b><br><br>El modelo no \"pensó\" en la persona. Solo aplicó una <b>regla</b> (+Puntos) a cada entrada. La IA real hace esta misma matemática, pero con millones de reglas en lugar de tres.",
        "btn_next_conn": "Siguiente: Conexión con la Justicia ▶️",
        "math_title": "🧮 Cómo Decidió el Modelo:",
        "math_pts": "pts",
        "math_total": "Puntaje Total",
        "s5_title": "🔗 Conectando con la Justicia Penal",
        "s5_p1": "<b>¿Por qué nos importan las 'Matemáticas' y las 'Entradas'?</b>",
        "s5_p2": "Porque la misma lógica se aplica a personas reales. Pero hay una diferencia clave entre el sesgo Humano y el de la IA:",
        "s5_col1_title": "🧑‍⚖️ Juez Humano",
        "s5_col1_desc": "Se basa en experiencia e intuición. El sesgo proviene de creencias subconscientes o estado de ánimo.",
        "s5_col2_title": "🤖 Modelo de IA",
        "s5_col2_desc": "Se basa en datos históricos. El sesgo proviene de <b>estadísticas pasadas</b>. Repite la historia exactamente.",
        "s5_h2": "El Objetivo del Ingeniero:",
        "s5_final": "Tu trabajo es revisar las <b>Entradas</b> y probar el <b>Modelo</b> para asegurar que no repita los errores del pasado.<br><br><b>Entender esto es el primer paso para construir equidad.</b>",
        "btn_complete": "Completar esta Sección ▶️",
        "s6_title": "🎓 ¡Ahora Entiendes la IA!",
        "s6_congrats": "<b>¡Felicidades!</b> Ahora puedes responder:",
        "s6_li1": "<b>¿Qué es la IA?</b> Una máquina que convierte datos en predicciones usando reglas matemáticas.",
        "s6_li2": "<b>¿Cómo funciona?</b> Entrada + Modelo (Reglas) = Salida.",
        "s6_li3": "<b>¿Cómo aprende?</b> Ajustando la \"importancia\" de las entradas basándose en ejemplos pasados.",
        "s6_li4": "<b>¿Por qué es riesgosa?</b> Confía completamente en datos históricos, incluso si contienen sesgos.",
        "s6_li5": "",
        "s6_next": "<b>Próximos Pasos:</b>",
        "s6_next_desc": "En las siguientes secciones, te convertirás en el Ingeniero. Elegirás las entradas y construirás el modelo tú mismo.",
        "s6_scroll": "👇 DESPLÁZATE HACIA ABAJO 👇",
        "s6_find": "Continúa en la siguiente sección abajo.",
        "btn_review": "◀️ Volver a Revisar",
        "risk_high": "Alto Riesgo",
        "risk_med": "Riesgo Medio",
        "risk_low": "Bajo Riesgo",
        "risk_score": "Puntaje de Riesgo:"
    },
    "ca": {
        "title": "🤖 Què és la IA, realment?",
        "intro_box": "Abans de poder construir millors sistemes d'IA, necessites entendre què és realment la IA.<br>No et preocupis, ho explicarem en termes simples!",
        "loading": "⏳ Carregant...",
        "s1_title": "🎯 Una Definició Simple",
        "s1_head": "Intel·ligència Artificial (IA) és només un nom elegant per a:",
        "s1_big": "Una Màquina de Predicció",
        "s1_sub": "Tracta el món com un problema matemàtic: <b>Entrades + Regles = Predicció</b>.",
        "s1_list_title": "Compara: Intuïció vs. Matemàtiques",
        "s1_human_head": "🧠 <b>Intuïció Humana:</b>",
        "s1_human_text": "Núvols foscos? -> Sento que plourà. -> Porto paraigua.",
        "s1_ai_head": "💻 <b>Càlcul d'IA:</b>",
        "s1_ai_text": "Densitat de Núvols (90%) + Humitat (85%) = <b>95% Probabilitat de Pluja</b>.",
        "s1_highlight": "La IA prediu el futur igual que tu, però utilitza <b>dades i matemàtiques</b> en lloc d'instint.",
        "btn_next_formula": "Següent: La Fórmula de la IA ▶️",
        "s2_title": "📐 La Fórmula de Tres Parts",
        "s2_intro": "Tot sistema d'IA funciona igual, seguint aquesta fórmula:",
        "lbl_input": "ENTRADA",
        "lbl_model": "MODEL",
        "lbl_output": "SORTIDA",
        "desc_input": "Entren dades",
        "desc_model": "El Cervell Matemàtic",
        "desc_output": "Surt predicció",
        "s2_ex_title": "Exemples del Món Real:",
        "s2_ex1_in": "Foto d'un gos",
        "s2_ex1_mod": "Regles d'Imatge",
        "s2_ex1_out": "\"Això és un Golden Retriever\"",
        "s2_ex2_in": "\"Quin temps fa?\"",
        "s2_ex2_mod": "Regles de Llenguatge",
        "s2_ex2_out": "Una resposta útil",
        "s2_ex3_in": "Historial criminal",
        "s2_ex3_mod": "Regles de Risc",
        "s2_ex3_out": "\"Alt Risc\" o \"Baix Risc\"",
        "btn_back": "◀️ Enrere",
        "btn_next_learn": "Següent: Com Aprenen els Models ▶️",
        "s3_title": "🧠 Com Aprèn un Model?",
        "s3_h1": "1. Aprèn d'Exemples",
        "s3_p1": "Un model d'IA no està programat amb respostes. S'entrena amb molts exemples.",
        "s3_p2": "Li mostrem milers de casos passats (<b>exemples</b>) i li diem \"Troba el patró que prediu la reincidència.\"",
        "s3_h2": "2. El Bucle d'Entrenament",
        "s3_p3": "La IA \"entrena\" recorrent dades milions de vegades:",
        "flow_1": "1. EXEMPLES<br>ENTRADA",
        "flow_2": "2. MODEL<br>ENDEVINA",
        "flow_3": "3. REVISAR<br>RESPOSTA",
        "flow_4": "4. AJUSTAR<br>IMPORTÀNCIA",
        "flow_5": "MODEL<br>APRÈS",
        "s3_vol_title": "🎚️ El Concepte de \"Volum\"",
        "s3_vol_desc": "Pensa en el model com una taula de mescles. Quan s'equivoca, ajusta la <b>Importància (Pes)</b> de les entrades.<br>Podria aprendre a pujar el volum a \"Delictes Previs\" i baixar-lo a \"Edat\".",
        "s3_eth_title": "⚠️ El Desafiament Ètic",
        "s3_eth_p": "<b>El model és cec a la justícia.</b> Si les dades històriques estan esbiaixades, la IA aprendrà aquest biaix com un patró matemàtic.",
        "btn_next_try": "Següent: Prova-ho Tu Mateix ▶️",
        "s4_title": "🎮 Prova-ho Tu Mateix!",
        "s4_intro": "<b>Mirem dins del cervell d'una IA simple.</b><br>Ajusta les entrades i et mostrarem exactament com el model calcula la puntuació.",
        "s4_sect1": "1️⃣ ENTRADA: Ajusta les Dades",
        "lbl_age": "Edat",
        "info_age": "Edat de l'acusat",
        "lbl_priors": "Delictes Previs",
        "info_priors": "Nombre de crims anteriors",
        "lbl_severity": "Gravetat del Càrrec",
        "info_severity": "Què tan greu és el càrrec?",
        "opt_minor": "Menor",
        "opt_moderate": "Moderat",
        "opt_serious": "Greu",
        "s4_sect2": "2️⃣ MODEL: Processa les Dades",
        "btn_run": "🔮 Executar Predicció IA",
        "s4_sect3": "3️⃣ SORTIDA: Veure les Matemàtiques",
        "res_placeholder": "Fes clic a \"Executar Predicció IA\" per veure el càlcul.",
        "s4_highlight": "<b>Has vist les matemàtiques?</b><br><br>El model no va \"pensar\" en la persona. Només va aplicar una <b>regla</b> (+Punts) a cada entrada. La IA real fa aquesta mateixa matemàtica, però amb milions de regles en lloc de tres.",
        "btn_next_conn": "Següent: Connexió amb la Justícia ▶️",
        "math_title": "🧮 Com ha Decidit el Model:",
        "math_pts": "punts",
        "math_total": "Puntuació Total",
        "s5_title": "🔗 Connectant amb la Justícia Penal",
        "s5_p1": "<b>Per què ens importen les 'Matemàtiques' i les 'Entrades'?</b>",
        "s5_p2": "Perquè la mateixa lògica s'aplica a persones reals. Però hi ha una diferència clau entre el biaix Humà i el de la IA:",
        "s5_col1_title": "🧑‍⚖️ Jutge Humà",
        "s5_col1_desc": "Es basa en experiència i intuïció. El biaix prové de creences subconscients o estat d'ànim.",
        "s5_col2_title": "🤖 Model d'IA",
        "s5_col2_desc": "Es basa en dades històriques. El biaix prové de <b>estadístiques passades</b>. Repeteix la història exactament.",
        "s5_h2": "L'Objectiu de l'Enginyer:",
        "s5_final": "La teva feina és revisar les <b>Entrades</b> i provar el <b>Model</b> per assegurar que no repeteixi els errors del passat.<br><br><b>Entendre això és el primer pas per construir equitat.</b>",
        "btn_complete": "Completar aquesta Secció ▶️",
        "s6_title": "🎓 Ara Entens la IA!",
        "s6_congrats": "<b>Felicitats!</b> Ara pots respondre:",
        "s6_li1": "<b>Què és la IA?</b> Una màquina que converteix dades en prediccions usant regles matemàtiques.",
        "s6_li2": "<b>Com funciona?</b> Entrada + Model (Regles) = Sortida.",
        "s6_li3": "<b>Com aprèn?</b> Ajustant la \"importància\" de les entrades basant-se en exemples passats.",
        "s6_li4": "<b>Per què és perillosa?</b> Confia completament en dades històriques, fins i tot si contenen biaixos.",
        "s6_li5": "",
        "s6_next": "<b>Propers Passos:</b>",
        "s6_next_desc": "En les següents seccions, et convertiràs en l'Enginyer. Triaràs les entrades i construiràs el model tu mateix.",
        "s6_scroll": "👇 DESPLAÇA'T CAP AVALL 👇",
        "s6_find": "Continua a la següent secció a sota.",
        "btn_review": "◀️ Tornar a Revisar",
        "risk_high": "Alt Risc",
        "risk_med": "Risc Mitjà",
        "risk_low": "Baix Risc",
        "risk_score": "Puntuació de Risc:"
    }
}


def _create_simple_predictor():
    """Create a simple demonstration predictor that shows the math score."""
    
    # Helper for translation
    def t(lang, key):
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

    def predict_outcome(age, priors, severity, lang="en"):
        """Simple rule-based predictor that outputs the Score Card explanation."""
        
        # 1. Normalize Inputs
        severity_map = {
            "Minor": 1, "Menor": 1,
            "Moderate": 2, "Moderado": 2, "Moderat": 2,
            "Serious": 3, "Grave": 3, "Greu": 3
        }
        
        # 2. Logic (The "Model")
        # Breakdown list to store the math explanation lines
        breakdown = []
        score = 0
        pts_label = t(lang, "math_pts")

        # Age Rule
        if age < 25: 
            score += 3
            breakdown.append(f"<li><b>{t(lang, 'lbl_age')} &lt; 25:</b> <span style='color:#dc2626; font-weight:bold;'>+3 {pts_label}</span></li>")
        elif age < 35: 
            score += 2
            breakdown.append(f"<li><b>{t(lang, 'lbl_age')} 25-35:</b> <span style='color:#f59e0b; font-weight:bold;'>+2 {pts_label}</span></li>")
        else: 
            score += 1
            breakdown.append(f"<li><b>{t(lang, 'lbl_age')} 35+:</b> <span style='color:#16a34a; font-weight:bold;'>+1 {pts_label}</span></li>")

        # Priors Rule
        if priors >= 3: 
            score += 3
            breakdown.append(f"<li><b>{t(lang, 'lbl_priors')} ({priors}):</b> <span style='color:#dc2626; font-weight:bold;'>+3 {pts_label}</span></li>")
        elif priors >= 1: 
            score += 2
            breakdown.append(f"<li><b>{t(lang, 'lbl_priors')} ({priors}):</b> <span style='color:#f59e0b; font-weight:bold;'>+2 {pts_label}</span></li>")
        else: 
            score += 0
            breakdown.append(f"<li><b>{t(lang, 'lbl_priors')} (0):</b> <span style='color:#16a34a; font-weight:bold;'>+0 {pts_label}</span></li>")

        # Severity Rule
        sev_val = severity_map.get(severity, 2)
        score += sev_val
        breakdown.append(f"<li><b>{t(lang, 'lbl_severity')} ({severity}):</b> <span style='font-weight:bold;'>+{sev_val} {pts_label}</span></li>")

        # 3. Determine Outcome
        if score >= 7:
            risk = t(lang, "risk_high")
            color = "#dc2626"
            emoji = "🔴"
        elif score >= 4:
            risk = t(lang, "risk_med")
            color = "#f59e0b"
            emoji = "🟡"
        else:
            risk = t(lang, "risk_low")
            color = "#16a34a"
            emoji = "🟢"

        # 4. Construct HTML Output (Math + Result)
        breakdown_html = "".join(breakdown)
        
        return f"""
        <div class="math-card">
            <h4 style="margin:0 0 10px 0; color:#4b5563;">{t(lang, 'math_title')}</h4>
            <ul style="margin:0; padding-left:20px; list-style-type:disc;">
                {breakdown_html}
            </ul>
            <div style="margin-top:10px; border-top:1px solid #e5e7eb; padding-top:8px; display:flex; justify-content:space-between; align-items:center;">
                <b>{t(lang, 'math_total')}:</b>
                <b style="font-size:1.2rem;">{score} / 9</b>
            </div>
        </div>
        
        <div class="prediction-card" style="border-color:{color}; margin-top:16px;">
            <h2 class="prediction-title" style="color:{color};">{emoji} {risk}</h2>
        </div>
        """

    return predict_outcome


def create_what_is_ai_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the What is AI Gradio Blocks app."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError("Gradio is required.") from e

    predict_outcome = _create_simple_predictor()

    # --- Translation Helper ---
    def t(lang, key):
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

    # --- HTML Generator Helpers ---
    def _get_step1_html(lang):
        return f"""
        <div class='step-card step-card-soft-blue'>
          <p><b style='font-size:24px;'>{t(lang, 's1_head')}</b></p>
          <div class='inner-card inner-card-emphasis-blue'>
              <h2 style='text-align:center; margin:0; font-size:2rem;'>
                {t(lang, 's1_big')}
              </h2>
          </div>
          <p style='text-align:center; font-size:1.1rem; margin-top:12px;'>{t(lang, 's1_sub')}</p>
          
          <h3 style='color:#0369a1; margin-top:32px;'>{t(lang, 's1_list_title')}</h3>
          
          <div class='comparison-row'>
              <div class='comparison-col' style='background-color:#eff6ff; border-color:#93c5fd;'>
                  <p style='margin:0 0 8px 0;'>{t(lang, 's1_human_head')}</p>
                  <p style='font-size:0.95rem; margin:0;'>{t(lang, 's1_human_text')}</p>
              </div>
              <div class='comparison-col' style='background-color:#f0fdf4; border-color:#86efac;'>
                  <p style='margin:0 0 8px 0;'>{t(lang, 's1_ai_head')}</p>
                  <p style='font-size:0.95rem; margin:0;'>{t(lang, 's1_ai_text')}</p>
              </div>
          </div>

          <div class='highlight-soft' style='border-left:6px solid #f59e0b; margin-top:24px;'>
              <p style='font-size:18px; margin:0;'>{t(lang, 's1_highlight')}</p>
          </div>
        </div>
        """

    def _get_step2_html(lang):
        return f"""
        <div class='step-card step-card-green'>
          <p>{t(lang, 's2_intro')}</p>
          <div class='inner-card'>
              <div class='io-chip-row'>
                  <div class='io-chip io-chip-input'>
                      <h3 class='io-step-label-input' style='margin:0;'>1️⃣ {t(lang, 'lbl_input')}</h3>
                      <p style='margin:8px 0 0 0; font-size:16px;'>{t(lang, 'desc_input')}</p>
                  </div>
                  <span class='io-arrow'>→</span>
                  <div class='io-chip io-chip-model'>
                      <h3 class='io-step-label-model' style='margin:0;'>2️⃣ {t(lang, 'lbl_model')}</h3>
                      <p style='margin:8px 0 0 0; font-size:16px;'>{t(lang, 'desc_model')}</p>
                  </div>
                  <span class='io-arrow'>→</span>
                  <div class='io-chip io-chip-output'>
                      <h3 class='io-step-label-output' style='margin:0;'>3️⃣ {t(lang, 'lbl_output')}</h3>
                      <p style='margin:8px 0 0 0; font-size:16px;'>{t(lang, 'desc_output')}</p>
                  </div>
              </div>
          </div>
          <h3 style='color:#15803d; margin-top:32px;'>{t(lang, 's2_ex_title')}</h3>
          <div class='inner-card-wide'>
              <p style='margin:0; font-size:18px;'>
              <b class='io-label-input'>{t(lang, 'lbl_input')}:</b> {t(lang, 's2_ex1_in')}<br>
              <b class='io-label-model'>{t(lang, 'lbl_model')}:</b> {t(lang, 's2_ex1_mod')}<br>
              <b class='io-label-output'>{t(lang, 'lbl_output')}:</b> {t(lang, 's2_ex1_out')}
              </p>
          </div>
          <div class='inner-card-wide'>
              <p style='margin:0; font-size:18px;'>
              <b class='io-label-input'>{t(lang, 'lbl_input')}:</b> {t(lang, 's2_ex2_in')}<br>
              <b class='io-label-model'>{t(lang, 'lbl_model')}:</b> {t(lang, 's2_ex2_mod')}<br>
              <b class='io-label-output'>{t(lang, 'lbl_output')}:</b> {t(lang, 's2_ex2_out')}
              </p>
          </div>
          <div class='inner-card-wide'>
              <p style='margin:0; font-size:18px;'>
              <b class='io-label-input'>{t(lang, 'lbl_input')}:</b> {t(lang, 's2_ex3_in')}<br>
              <b class='io-label-model'>{t(lang, 'lbl_model')}:</b> {t(lang, 's2_ex3_mod')}<br>
              <b class='io-label-output'>{t(lang, 'lbl_output')}:</b> {t(lang, 's2_ex3_out')}
              </p>
          </div>
        </div>
        """

    def _get_step3_html(lang):
        return f"""
        <div class='step-card step-card-amber'>
          <h3 style='color:#92400e; margin-top:0;'>{t(lang, 's3_h1')}</h3>
          <p>{t(lang, 's3_p1')}</p>
          <p>{t(lang, 's3_p2')}</p>
          <hr style='margin:24px 0;'>
          <h3 style='color:#92400e;'>{t(lang, 's3_h2')}</h3>
          <p>{t(lang, 's3_p3')}</p>
          <div class='inner-card'>
              <div style='display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap;'>
                  <div style='background:#dbeafe; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                      <b style='color:#0369a1;'>{t(lang, 'flow_1')}</b>
                  </div>
                  <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                  <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                      <b style='color:#92400e;'>{t(lang, 'flow_2')}</b>
                  </div>
                  <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                  <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                      <b style='color:#92400e;'>{t(lang, 'flow_3')}</b>
                  </div>
                  <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                  <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center; border:2px solid #f59e0b;'>
                      <b style='color:#92400e;'>{t(lang, 'flow_4')}</b>
                  </div>
                  <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                  <div style='background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                      <b style='color:#15803d;'>{t(lang, 'flow_5')}</b>
                  </div>
              </div>
          </div>
          
          <div class='keypoint-box' style='border-left-color:#f59e0b; margin-top:24px;'>
              <h4 style='margin:0 0 8px 0; color:#b45309;'>{t(lang, 's3_vol_title')}</h4>
              <p style='margin:0;'>{t(lang, 's3_vol_desc')}</p>
          </div>

          <hr style='margin:24px 0;'>
          <h3 style='color:#dc2626;'>{t(lang, 's3_eth_title')}</h3>
          <p style='margin:0;'>{t(lang, 's3_eth_p')}</p>
        </div>
        """

    def _get_step4_intro_html(lang):
        return f"""
        <div class='step-card step-card-amber' style='text-align:center; font-size:18px;'>
          <p style='margin:0;'>{t(lang, 's4_intro')}</p>
        </div>
        """
    
    def _get_step4_highlight_html(lang):
        return f"""
        <div class='highlight-soft'>
            {t(lang, 's4_highlight')}
        </div>
        """

    def _get_step5_html(lang):
        return f"""
        <div class='step-card step-card-purple'>
          <p><b>{t(lang, 's5_p1')}</b></p>
          <p style='margin-top:10px;'>{t(lang, 's5_p2')}</p>
          
          <div class='comparison-row' style='margin-top:20px;'>
              <div class='comparison-col' style='background-color:#fff1f2; border-color:#fda4af;'>
                  <h4 style='margin:0 0 8px 0; font-size:1.1rem;'>{t(lang, 's5_col1_title')}</h4>
                  <p style='font-size:0.95rem; margin:0;'>{t(lang, 's5_col1_desc')}</p>
              </div>
              <div class='comparison-col' style='background-color:#f3e8ff; border-color:#d8b4fe;'>
                  <h4 style='margin:0 0 8px 0; font-size:1.1rem;'>{t(lang, 's5_col2_title')}</h4>
                  <p style='font-size:0.95rem; margin:0;'>{t(lang, 's5_col2_desc')}</p>
              </div>
          </div>

          <h3 style='color:#7e22ce; margin-top:32px;'>{t(lang, 's5_h2')}</h3>
          <div class='highlight-soft' style='border-color:#9333ea; margin-top:16px;'>
              <p style='font-size:18px; margin:0;'>{t(lang, 's5_final')}</p>
          </div>
        </div>
        """

    def _get_step6_html(lang):
        return f"""
        <div style='text-align:center;'>
            <h2 style='font-size: 2.5rem;'>{t(lang, 's6_title')}</h2>
            <div class='completion-box'>
                <p>{t(lang, 's6_congrats')}</p>
                <ul style='font-size:1.1rem; text-align:left; max-width:600px; margin:20px auto;'>
                    <li>{t(lang, 's6_li1')}</li>
                    <li>{t(lang, 's6_li2')}</li>
                    <li>{t(lang, 's6_li3')}</li>
                    <li>{t(lang, 's6_li4')}</li>
                </ul>
                <p style='margin-top:32px;'><b>{t(lang, 's6_next')}</b></p>
                <p>{t(lang, 's6_next_desc')}</p>
                <h1 style='margin:20px 0; font-size: 3rem;'>{t(lang, 's6_scroll')}</h1>
                <p style='font-size:1.1rem;'>{t(lang, 's6_find')}</p>
            </div>
        </div>
        """

    # --- CSS (Updated for new layouts) ---
    css = """
    .large-text { font-size: 20px !important; }
    .loading-title { font-size: 2rem; color: var(--secondary-text-color); }
    .io-step-label-input, .io-label-input { color: #0369a1; font-weight: 700; }
    .io-step-label-model, .io-label-model { color: #92400e; font-weight: 700; }
    .io-step-label-output, .io-label-output { color: #15803d; font-weight: 700; }
    .io-chip-row { text-align: center; }
    .io-chip { display: inline-block; padding: 16px 24px; border-radius: 8px; margin: 8px; background-color: color-mix(in srgb, var(--block-background-fill) 60%, #ffffff 40%); }
    .io-chip-input { background-color: color-mix(in srgb, #dbeafe 75%, var(--block-background-fill) 25%); }
    .io-chip-model { background-color: color-mix(in srgb, #fef3c7 75%, var(--block-background-fill) 25%); }
    .io-chip-output { background-color: color-mix(in srgb, #dcfce7 75%, var(--block-background-fill) 25%); }
    .io-arrow { display: inline-block; font-size: 2rem; margin: 0 16px; color: var(--secondary-text-color); vertical-align: middle; }
    .ai-intro-box { text-align: center; font-size: 18px; max-width: 900px; margin: auto; padding: 20px; border-radius: 12px; background-color: var(--block-background-fill); color: var(--body-text-color); border: 2px solid #6366f1; box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08); }
    .step-card { font-size: 20px; padding: 28px; border-radius: 16px; background-color: var(--block-background-fill); color: var(--body-text-color); border: 1px solid var(--border-color-primary); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06); }
    .step-card-soft-blue { border-width: 2px; border-color: #6366f1; }
    .step-card-green { border-width: 2px; border-color: #16a34a; }
    .step-card-amber { border-width: 2px; border-color: #f59e0b; }
    .step-card-purple { border-width: 2px; border-color: #9333ea; }
    .inner-card { background-color: var(--body-background-fill); color: var(--body-text-color); padding: 24px; border-radius: 12px; margin: 24px 0; border: 1px solid var(--border-color-primary); }
    .inner-card-emphasis-blue { border-width: 3px; border-color: #0284c7; }
    .inner-card-wide { background-color: var(--body-background-fill); color: var(--body-text-color); padding: 20px; border-radius: 8px; margin: 16px 0; border: 1px solid var(--border-color-primary); }
    .keypoint-box { background-color: var(--block-background-fill); color: var(--body-text-color); padding: 24px; border-radius: 12px; margin-top: 20px; border-left: 6px solid #dc2626; }
    .highlight-soft { background-color: var(--block-background-fill); color: var(--body-text-color); padding: 20px; border-radius: 12px; font-size: 18px; border: 1px solid var(--border-color-primary); }
    .completion-box { font-size: 1.3rem; padding: 28px; border-radius: 16px; background-color: var(--block-background-fill); color: var(--body-text-color); border: 2px solid #0284c7; box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08); }
    .prediction-card { background-color: var(--block-background-fill); color: var(--body-text-color); padding: 24px; border-radius: 12px; border: 3px solid var(--border-color-primary); text-align: center; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
    .prediction-title { margin: 0; font-size: 2.5rem; }
    .prediction-score { font-size: 18px; margin-top: 12px; color: var(--secondary-text-color); }
    .prediction-placeholder { background-color: var(--block-background-fill); color: var(--secondary-text-color); padding: 40px; border-radius: 12px; text-align: center; border: 1px solid var(--border-color-primary); }
    
    /* NEW CSS FOR COLUMNS */
    .comparison-row { display: flex; gap: 16px; margin-top: 20px; }
    .comparison-col { flex: 1; padding: 20px; border-radius: 12px; border: 2px solid #ccc; font-size: 1rem; color: #111827; }
    .math-card { background-color: var(--body-background-fill); border: 1px solid var(--border-color-primary); border-radius: 12px; padding: 16px; font-size: 1rem; }

    #nav-loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: color-mix(in srgb, var(--body-background-fill) 95%, transparent); z-index: 9999; display: none; flex-direction: column; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.3s ease; }
    .nav-spinner { width: 50px; height: 50px; border: 5px solid var(--border-color-primary); border-top: 5px solid var(--color-accent); border-radius: 50%; animation: nav-spin 1s linear infinite; margin-bottom: 20px; }
    @keyframes nav-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    #nav-loading-text { font-size: 1.3rem; font-weight: 600; color: var(--color-accent); }
    
    @media (max-width: 600px) { .comparison-row { flex-direction: column; } }
    @media (prefers-color-scheme: dark) { 
        .ai-intro-box, .step-card, .inner-card, .inner-card-wide, .keypoint-box, .highlight-soft, .completion-box, .prediction-card, .prediction-placeholder, .math-card { background-color: #2D323E; color: white; border-color: #555555; box-shadow: none; } 
        .inner-card, .inner-card-wide, .math-card { background-color: #181B22; } 
        .comparison-col { color: white; border-color: #555; }
        .comparison-col[style*="eff6ff"] { background-color: #1e3a8a !important; border-color: #3b82f6 !important; }
        .comparison-col[style*="f0fdf4"] { background-color: #14532d !important; border-color: #22c55e !important; }
        .comparison-col[style*="fff1f2"] { background-color: #881337 !important; border-color: #f43f5e !important; }
        .comparison-col[style*="f3e8ff"] { background-color: #581c87 !important; border-color: #a855f7 !important; }
        #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); } 
        .nav-spinner { border-color: rgba(148, 163, 184, 0.4); border-top-color: var(--color-accent); } 
        .io-chip-input { background-color: color-mix(in srgb, #1d4ed8 35%, #020617 65%); } 
        .io-chip-model { background-color: color-mix(in srgb, #b45309 40%, #020617 60%); } 
        .io-chip-output { background-color: color-mix(in srgb, #15803d 40%, #020617 60%); } 
        .io-arrow { color: #e5e7eb; } 
        .math-card h4 { color: #9ca3af !important; }
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        lang_state = gr.State("en")
        
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # --- Variables for dynamic updating ---
        c_title = gr.Markdown("<h1 style='text-align:center;'>🤖 What is AI, Anyway?</h1>")
        c_intro = gr.HTML(f"<div class='ai-intro-box'>{t('en', 'intro_box')}</div>")
        gr.HTML("<hr style='margin:24px 0;'>")

        with gr.Column(visible=False) as loading_screen:
            c_load = gr.Markdown(f"<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t('en', 'loading')}</h2></div>")

        # Step 1
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            c_s1_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's1_title')}</h2>")
            c_s1_html = gr.HTML(_get_step1_html("en"))
            step_1_next = gr.Button(t('en', 'btn_next_formula'), variant="primary", size="lg")

        # Step 2
        with gr.Column(visible=False, elem_id="step-2") as step_2:
            c_s2_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's2_title')}</h2>")
            c_s2_html = gr.HTML(_get_step2_html("en"))
            with gr.Row():
                step_2_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_2_next = gr.Button(t('en', 'btn_next_learn'), variant="primary", size="lg")

        # Step 3
        with gr.Column(visible=False, elem_id="step-3") as step_3:
            c_s3_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's3_title')}</h2>")
            c_s3_html = gr.HTML(_get_step3_html("en"))
            with gr.Row():
                step_3_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_3_next = gr.Button(t('en', 'btn_next_try'), variant="primary", size="lg")

        # Step 4 (Interactive)
        with gr.Column(visible=False, elem_id="step-4") as step_4:
            c_s4_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's4_title')}</h2>")
            c_s4_intro = gr.HTML(_get_step4_intro_html("en"))
            gr.HTML("<br>")

            c_s4_sect1 = gr.Markdown(f"<h3 style='text-align:center; color:#0369a1;'>{t('en', 's4_sect1')}</h3>")
            with gr.Row():
                age_slider = gr.Slider(minimum=18, maximum=65, value=25, step=1, label=t('en', 'lbl_age'), info=t('en', 'info_age'))
                priors_slider = gr.Slider(minimum=0, maximum=10, value=2, step=1, label=t('en', 'lbl_priors'), info=t('en', 'info_priors'))
            severity_dropdown = gr.Dropdown(choices=["Minor", "Moderate", "Serious"], value="Moderate", label=t('en', 'lbl_severity'), info=t('en', 'info_severity'))

            gr.HTML("<hr style='margin:24px 0;'>")
            c_s4_sect2 = gr.Markdown(f"<h3 style='text-align:center; color:#92400e;'>{t('en', 's4_sect2')}</h3>")
            predict_btn = gr.Button(t('en', 'btn_run'), variant="primary", size="lg")

            gr.HTML("<hr style='margin:24px 0;'>")
            c_s4_sect3 = gr.Markdown(f"<h3 style='text-align:center; color:#15803d;'>{t('en', 's4_sect3')}</h3>")
            
            prediction_output = gr.HTML(f"<div class='prediction-placeholder'><p style='font-size:18px; margin:0;'>{t('en', 'res_placeholder')}</p></div>")
            
            gr.HTML("<hr style='margin:24px 0;'>")
            c_s4_highlight = gr.HTML(_get_step4_highlight_html("en"))

            with gr.Row():
                step_4_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_4_next = gr.Button(t('en', 'btn_next_conn'), variant="primary", size="lg")

        # Step 5
        with gr.Column(visible=False, elem_id="step-5") as step_5:
            c_s5_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's5_title')}</h2>")
            c_s5_html = gr.HTML(_get_step5_html("en"))
            with gr.Row():
                step_5_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_5_next = gr.Button(t('en', 'btn_complete'), variant="primary", size="lg")

        # Step 6
        with gr.Column(visible=False, elem_id="step-6") as step_6:
            c_s6_html = gr.HTML(_get_step6_html("en"))
            back_to_connection_btn = gr.Button(t('en', 'btn_review'))

        # --- Update Logic ---
        
        def update_language(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS: lang = "en"
            
            # Helper to access options for Dropdown updates
            def get_opt(k): return t(lang, k)
            
            return [
                lang, # state
                f"<h1 style='text-align:center;'>{t(lang, 'title')}</h1>",
                f"<div class='ai-intro-box'>{t(lang, 'intro_box')}</div>",
                f"<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t(lang, 'loading')}</h2></div>",
                
                # Step 1
                f"<h2 style='text-align:center;'>{t(lang, 's1_title')}</h2>",
                _get_step1_html(lang),
                gr.Button(value=t(lang, 'btn_next_formula')),
                
                # Step 2
                f"<h2 style='text-align:center;'>{t(lang, 's2_title')}</h2>",
                _get_step2_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_next_learn')),
                
                # Step 3
                f"<h2 style='text-align:center;'>{t(lang, 's3_title')}</h2>",
                _get_step3_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_next_try')),
                
                # Step 4
                f"<h2 style='text-align:center;'>{t(lang, 's4_title')}</h2>",
                _get_step4_intro_html(lang),
                f"<h3 style='text-align:center; color:#0369a1;'>{t(lang, 's4_sect1')}</h3>",
                gr.Slider(label=t(lang, 'lbl_age'), info=t(lang, 'info_age')),
                gr.Slider(label=t(lang, 'lbl_priors'), info=t(lang, 'info_priors')),
                gr.Dropdown(
                    label=t(lang, 'lbl_severity'), 
                    info=t(lang, 'info_severity'), 
                    choices=[get_opt('opt_minor'), get_opt('opt_moderate'), get_opt('opt_serious')],
                    value=get_opt('opt_moderate')
                ),
                f"<h3 style='text-align:center; color:#92400e;'>{t(lang, 's4_sect2')}</h3>",
                gr.Button(value=t(lang, 'btn_run')),
                f"<h3 style='text-align:center; color:#15803d;'>{t(lang, 's4_sect3')}</h3>",
                f"<div class='prediction-placeholder'><p style='font-size:18px; margin:0;'>{t(lang, 'res_placeholder')}</p></div>", # Reset output on lang change
                _get_step4_highlight_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_next_conn')),
                
                # Step 5
                f"<h2 style='text-align:center;'>{t(lang, 's5_title')}</h2>",
                _get_step5_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_complete')),
                
                # Step 6
                _get_step6_html(lang),
                gr.Button(value=t(lang, 'btn_review'))
            ]

        # List of outputs must match the return order exactly
        update_targets = [
            lang_state,
            c_title, c_intro, c_load,
            # S1
            c_s1_title, c_s1_html, step_1_next,
            # S2
            c_s2_title, c_s2_html, step_2_back, step_2_next,
            # S3
            c_s3_title, c_s3_html, step_3_back, step_3_next,
            # S4
            c_s4_title, c_s4_intro, c_s4_sect1, age_slider, priors_slider, severity_dropdown,
            c_s4_sect2, predict_btn, c_s4_sect3, prediction_output, c_s4_highlight, step_4_back, step_4_next,
            # S5
            c_s5_title, c_s5_html, step_5_back, step_5_next,
            # S6
            c_s6_html, back_to_connection_btn
        ]
        
        demo.load(update_language, inputs=None, outputs=update_targets)

        # --- PREDICTION BUTTON LOGIC ---
        # Note: We pass lang_state to the predictor to ensure result is translated
        predict_btn.click(
            predict_outcome,
            inputs=[age_slider, priors_slider, severity_dropdown, lang_state],
            outputs=prediction_output,
            show_progress="full",
            scroll_to_output=True,
        )

        # --- NAVIGATION LOGIC ---
        all_steps = [step_1, step_2, step_3, step_4, step_5, step_6, loading_screen]

        def create_nav_generator(current_step, next_step):
            def navigate():
                updates = {loading_screen: gr.update(visible=True)}
                for step in all_steps:
                    if step != loading_screen: updates[step] = gr.update(visible=False)
                yield updates
                updates = {next_step: gr.update(visible=True)}
                for step in all_steps:
                    if step != next_step: updates[step] = gr.update(visible=False)
                yield updates
            return navigate

        # JS Helper for loading overlay
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
        step_5_back.click(fn=create_nav_generator(step_5, step_4), outputs=all_steps, js=nav_js("step-4", "Loading..."))
        step_5_next.click(fn=create_nav_generator(step_5, step_6), outputs=all_steps, js=nav_js("step-6", "Loading..."))
        back_to_connection_btn.click(fn=create_nav_generator(step_6, step_5), outputs=all_steps, js=nav_js("step-5", "Loading..."))

    return demo

def launch_what_is_ai_app(height: int = 1100, share: bool = False, debug: bool = False) -> None:
    demo = create_what_is_ai_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)

if __name__ == "__main__":
    launch_what_is_ai_app()

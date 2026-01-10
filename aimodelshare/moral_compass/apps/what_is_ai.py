"""
What is AI - Gradio application for the Justice & Equity Challenge.
Updated with i18n support for English (en), Spanish (es), and Catalan (ca).
"""
import contextlib
import os
import gradio as gr
from functools import lru_cache

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
        "s1_big": "A system that makes predictions based on patterns",
        "s1_sub": "That's it! Let's break down what that means...",
        "s1_list_title": "Think About How YOU Make Predictions:",
        "s1_li1": "<b>Weather:</b> Dark clouds → You predict rain → You bring an umbrella",
        "s1_li2": "<b>Traffic:</b> Rush hour time → You predict congestion → You leave early",
        "s1_li3": "<b>Movies:</b> Actor you like → You predict you'll enjoy it → You watch it",
        "s1_highlight": "AI does the same thing, but using data and math instead of human experience and intuition.",
        "btn_next_formula": "Next: The AI Formula ▶️",
        # Step 2
        "s2_title": "📐 The Three-Part Formula",
        "s2_intro": "Every AI system works the same way, following this simple formula:",
        "lbl_input": "INPUT",
        "lbl_model": "MODEL",
        "lbl_output": "OUTPUT",
        "desc_input": "Data goes in",
        "desc_model": "AI processes it",
        "desc_output": "Prediction comes out",
        "s2_ex_title": "Real-World Examples:",
        "s2_ex1_in": "Photo of a dog",
        "s2_ex1_mod": "Image recognition AI",
        "s2_ex1_out": "\"This is a Golden Retriever\"",
        "s2_ex2_in": "\"How's the weather?\"",
        "s2_ex2_mod": "Language AI (like ChatGPT)",
        "s2_ex2_out": "A helpful response",
        "s2_ex3_in": "Person's criminal history",
        "s2_ex3_mod": "Risk assessment AI",
        "s2_ex3_out": "\"High Risk\" or \"Low Risk\"",
        "btn_back": "◀️ Back",
        "btn_next_learn": "Next: How Models Learn ▶️",
        # Step 3
        "s3_title": "🧠 How Does an AI Model Learn?",
        "s3_h1": "1. It Learns from Examples",
        "s3_p1": "An AI model isn't programmed with answers. Instead, it's trained on a huge number of examples, and it learns how to find the answers on its own.",
        "s3_p2": "In our justice scenario, this means feeding the model thousands of past cases (<b>examples</b>) to teach it how to find the <b>patterns</b> that connect a person's details to their risk of re-offending.",
        "s3_h2": "2. The Training Process",
        "s3_p3": "The AI \"trains\" by looping through historical data (past cases) millions of times:",
        "flow_1": "1. INPUT<br>EXAMPLES",
        "flow_2": "2. MODEL<br>GUESSES",
        "flow_3": "3. CHECK<br>ANSWER",
        "flow_4": "4. ADJUST<br>WEIGHTS",
        "flow_5": "LEARNED<br>MODEL",
        "s3_p4": "During the <b>\"Adjust\"</b> step, the model changes its internal rules (called <b>\"weights\"</b>) to get closer to the right answer. For example, it learns <b>how much</b> \"prior offenses\" should matter more than \"age\".",
        "s3_eth_title": "⚠️ The Ethical Challenge",
        "s3_eth_p": "<b>Here's the critical problem:</b> The model *only* learns from the data. If the historical data is biased (e.g., certain groups were arrested more often), the model will learn those biased patterns.<br><br><b>The model doesn't know \"fairness\" or \"justice,\" it only knows patterns.</b>",
        "btn_next_try": "Next: Try It Yourself ▶️",
        # Step 4 (Interactive)
        "s4_title": "🎮 Try It Yourself!",
        "s4_intro": "<b>Let's use a simple AI model to predict risk of re-offending.</b><br>Adjust the inputs below and see how the model's prediction changes!",
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
        "s4_sect3": "3️⃣ OUTPUT: See the Prediction",
        "res_placeholder": "Click \"Run AI Prediction\" above to see the result",
        "s4_highlight": "<b>What You Just Did:</b><br><br>You used a very simple AI model! You provided <b style='color:#0369a1;'>input data</b> (age, priors, severity), the <b style='color:#92400e;'>model processed it</b> using rules and patterns, and it produced an <b style='color:#15803d;'>output prediction</b>.<br><br>Real AI models are more complex, but they work on the same principle!",
        "btn_next_conn": "Next: Connection to Justice ▶️",
        # Step 5
        "s5_title": "🔗 Connecting to Criminal Justice",
        "s5_p1": "<b>Remember the risk prediction you used earlier as a judge?</b>",
        "s5_p2": "That was a real-world example of AI in action:",
        "s5_in_desc": "• Age, race, gender, prior offenses, charge details",
        "s5_mod_desc1": "• Trained on historical criminal justice data",
        "s5_mod_desc2": "• Looks for patterns in who re-offended in the past",
        "s5_out_desc": "• \"High Risk\", \"Medium Risk\", or \"Low Risk\"",
        "s5_h2": "Why This Matters for Ethics:",
        "s5_li1": "The <b>input data</b> might contain historical biases",
        "s5_li2": "The <b>model</b> learns patterns from potentially unfair past decisions",
        "s5_li3": "The <b>output predictions</b> can perpetuate discrimination",
        "s5_final": "<b>Understanding how AI works is the first step to building fairer systems.</b><br><br>Now that you know the basics of AI, you're ready to help design better models that are more ethical and less biased!",
        "btn_complete": "Complete This Section ▶️",
        # Step 6
        "s6_title": "🎓 You Now Understand the Basics of AI!",
        "s6_congrats": "<b>Congratulations!</b> You now know:",
        "s6_li1": "What AI is (a prediction system)",
        "s6_li2": "How it works (Input → Model → Output)",
        "s6_li3": "How AI models learn from data",
        "s6_li4": "Why it matters for criminal justice",
        "s6_li5": "The ethical implications of AI decisions",
        "s6_next": "<b>Next Steps:</b>",
        "s6_next_desc": "In the following sections, you'll learn how to build and improve AI models to make them more fair and ethical.",
        "s6_scroll": "👇 Continue to the next activity below — or click <span style='white-space:nowrap;'>Next (top bar)</span> in expanded view ➡️",
        "s6_find": "",
        "btn_review": "◀️ Back to Review",
        # Logic / Dynamic
        "risk_high": "High Risk",
        "risk_med": "Medium Risk",
        "risk_low": "Low Risk",
        "risk_score": "Risk Score:"
    },
    "es": {
        "title": "🤖 Pero, ¿qué es la IA, en realidad?",
        "intro_box": "Antes de poder construir mejores sistemas de IA, necesitas entender qué es realmente la IA.<br>No te preocupes, ¡lo explicaremos en términos simples y cotidianos!",
        "loading": "⏳ Cargando...",
        # Step 1
        "s1_title": "🎯 Una definición simple",
        "s1_head": "Inteligencia Artificial (IA) es solo un nombre elegante para:",
        "s1_big": "Un sistema que hace predicciones basadas en patrones",
        "s1_sub": "¡Eso es todo! Desglosemos qué significa eso...",
        "s1_list_title": "Piensa en cómo TÚ haces predicciones:",
        "s1_li1": "<b>Tiempo:</b> Nubes oscuras → Predices lluvia → Llevas paraguas",
        "s1_li2": "<b>Tráfico:</b> Hora punta → Predices congestión → Sales temprano",
        "s1_li3": "<b>Película:</b> Actor que te gusta → Predices que te gustará → La ves",
        "s1_highlight": "La IA hace lo mismo, pero usando datos y matemáticas en lugar de experiencia humana e intuición.",
        "btn_next_formula": "Siguiente: La fórmula de la IA ▶️",
        # Step 2
        "s2_title": "📐 Las tres partes de la fórmula",
        "s2_intro": "Todo sistema de IA funciona de la misma manera, siguiendo esta fórmula simple:",
        "lbl_input": "ENTRADA",
        "lbl_model": "MODELO",
        "lbl_output": "SALIDA",
        "desc_input": "Entran datos",
        "desc_model": "La IA los procesa",
        "desc_output": "Sale la predicción",
        "s2_ex_title": "Ejemplos del mundo real:",
        "s2_ex1_in": "Foto de un perro",
        "s2_ex1_mod": "IA de reconocimiento de imágenes",
        "s2_ex1_out": "\"Esto es un Golden Retriever\"",
        "s2_ex2_in": "\"¿Qué tiempo hace?\"",
        "s2_ex2_mod": "IA de lenguaje (como ChatGPT)",
        "s2_ex2_out": "Una respuesta útil",
        "s2_ex3_in": "Historial criminal de una persona",
        "s2_ex3_mod": "IA de evaluación de riesgos",
        "s2_ex3_out": "\"Alto Riesgo\" o \"Bajo Riesgo\"",
        "btn_back": "◀️ Atrás",
        "btn_next_learn": "Siguiente: Cómo aprenden los modelos ▶️",
        # Step 3
        "s3_title": "🧠 ¿Cómo aprende un modelo de IA?",
        "s3_h1": "1. Aprende de ejemplos",
        "s3_p1": "Un modelo de IA no está programado con respuestas. En cambio, se entrena con una gran cantidad de ejemplos y aprende a encontrar las respuestas por sí mismo.",
        "s3_p2": "En nuestro escenario de justicia, esto significa alimentar al modelo con miles de casos pasados (<b>ejemplos</b>) para enseñarle a encontrar los <b>patrones</b> que conectan los detalles de una persona con su riesgo criminal.",
        "s3_h2": "2. El Proceso de entrenamiento",
        "s3_p3": "La IA se \"entrena\" repitiendo el ciclo millones de veces a través de datos históricos (casos pasados):",
        "flow_1": "1. EJEMPLOS<br>ENTRADA",
        "flow_2": "2. MODELO<br>ESTIMACIONES",
        "flow_3": "3. REVISAR<br>RESPUESTA",
        "flow_4": "4. AJUSTAR<br>PESOS",
        "flow_5": "MODELO<br>APRENDIDO",
        "s3_p4": "Durante el paso de <b>\"Ajustar\"</b>, el modelo cambia sus reglas internas (llamadas <b>\"pesos\"</b>) para acercarse a la respuesta correcta. Por ejemplo, aprende <b>cuánto</b> deben importar más los \"delitos previos\" que la \"edad\".",
        "s3_eth_title": "⚠️ El desafío ético",
        "s3_eth_p": "<b>Aquí nos encontramos con un problema crítico:</b> El modelo *solo* aprende de los datos. Si los datos históricos están sesgados (por ejemplo, ciertos grupos de personas fueron arrestados con más frecuencia), el modelo aprenderá esos patrones sesgados.<br><br><b>El modelo no conoce de \"equidad\" o de \"justicia\", solo conoce patrones.</b>",
        "btn_next_try": "Siguiente: Pruébalo tú mismo ▶️",
        # Step 4
        "s4_title": "🎮 ¡Pruébalo tú mismo!",
        "s4_intro": "<b>Usemos un modelo de IA simple para predecir el riesgo de reincidencia.</b><br>¡A continuación, ajusta las entradas y observa cómo cambia la predicción del modelo!",
        "s4_sect1": "1️⃣ ENTRADA: Ajusta los datos",
        "lbl_age": "Edad",
        "info_age": "Edad del acusado",
        "lbl_priors": "Delitos previos",
        "info_priors": "Número de crímenes anteriores",
        "lbl_severity": "Gravedad del cargo actual",
        "info_severity": "¿Qué tan grave es el cargo actual?",
        "opt_minor": "Menor",
        "opt_moderate": "Moderado",
        "opt_serious": "Grave",
        "s4_sect2": "2️⃣ MODELO: Procesa los datos",
        "btn_run": "🔮 Ejecutar predicción de la IA",
        "s4_sect3": "3️⃣ SALIDA: Ver la predicción",
        "res_placeholder": "Haz clic en \"Ejecutar predicción de la IA\" para ver el resultado",
        "s4_highlight": "<b>Lo que acabas de hacer:</b><br><br>¡Usaste un modelo de IA muy simple! Proporcionaste <b style='color:#0369a1;'>datos de entrada</b> (edad, delitos, gravedad), el <b style='color:#92400e;'>modelo los procesó</b> usando reglas y patrones, y produjo una <b style='color:#15803d;'>predicción de salida</b>.<br><br>¡Los modelos de IA reales son más complejos, pero funcionan bajo el mismo principio!",
        "btn_next_conn": "Siguiente: Conexión con la justicia ▶️",
        # Step 5
        "s5_title": "🔗 Connexión con el sistema de justicia penal",
        "s5_p1": "<b>¿Recuerdas la predicción de riesgo que usaste antes en tu rol de juez?</b>",
        "s5_p2": "Ese fue un ejemplo del mundo real de IA en acción:",
        "s5_in_desc": "• Edad, raza, género, delitos previos, detalles del cargo penal",
        "s5_mod_desc1": "• Se entrena con datos históricos de la justicia penal",
        "s5_mod_desc2": "• Busca patrones entre las personas que reincindieron en el pasado",
        "s5_out_desc": "• \"Alto Riesgo\", \"Riesgo Medio\" o \"Bajo Riesgo\"",
        "s5_h2": "¿Por qué es esto importante para la ética?:",
        "s5_li1": "Los <b>datos de entrada</b> pueden contener sesgos históricos",
        "s5_li2": "El <b>modelo</b> aprende patrones de decisiones pasadas potencialmente injustas",
        "s5_li3": "Las <b>predicciones de salida</b> pueden perpetuar la discriminación",
        "s5_final": "<b>Entender cómo funciona la IA es el primer paso para construir sistemas más justos.</b><br><br>¡Ahora que sabes los conceptos básicos de la IA, estás listo para ayudar a diseñar mejores modelos que sean más éticos y menos sesgados!",
        "btn_complete": "Completar esta sección ▶️",
        # Step 6
        "s6_title": "🎓 ¡Ahora entiendes los conceptos básicos de la IA!",
        "s6_congrats": "<b>¡Felicidades!</b> Ahora sabes:",
        "s6_li1": "Qué es la IA (un sistema de predicción)",
        "s6_li2": "Cómo funciona (Entrada → Modelo → Salida)",
        "s6_li3": "Cómo los modelos de IA aprenden de los datos",
        "s6_li4": "Por qué importa para el sistema de justicia penal",
        "s6_li5": "Las implicaciones éticas de las decisiones de la IA",
        "s6_next": "<b>Próximos pasos:</b>",
        "s6_next_desc": "En las siguientes secciones, aprenderás cómo construir y mejorar modelos de IA para hacerlos más justos y éticos.",
        "s6_scroll": "👇 Continúa con la siguiente actividad abajo — o haz clic en <span style='white-space:nowrap;'>Siguiente (barra superior)</span> en vista ampliada ➡️",
        "s6_find": "",
        "btn_review": "◀️ Volver a revisar",
        "risk_high": "Alto Riesgo",
        "risk_med": "Riesgo Medio",
        "risk_low": "Bajo Riesgo",
        "risk_score": "Puntaje de Riesgo:"
    },
    "ca": {
        "title": "🤖 Però, què és la IA, realment?",
        "intro_box": "Abans de poder construir millors sistemes d'IA, necessites entendre què és realment la IA.<br>No et preocupis, ho explicarem en termes simples i quotidians!",
        "loading": "⏳ Carregant...",
        # Step 1
        "s1_title": "🎯 Una definició simple",
        "s1_head": "Intel·ligència Artificial (IA) és només un nom elegant per a:",
        "s1_big": "Un sistema que fa prediccions basades en patrons",
        "s1_sub": "Això és tot! Desglossem què significa això...",
        "s1_list_title": "Pensa en com TU fas prediccions:",
        "s1_li1": "<b>Temps:</b> Núvols negres → Predius pluja → Portes paraigua",
        "s1_li2": "<b>Trànsit:</b> Hora punta → Predius congestió → Surts d'hora",
        "s1_li3": "<b>Pel·lícula:</b> Actor que t'agrada → Predius que t'agradarà → La veus",
        "s1_highlight": "La IA fa el mateix, però utilitzant dades i matemàtiques en lloc d'experiència humana i intuïció.",
        "btn_next_formula": "Següent: La fórmula de la IA ▶️",
        # Step 2
        "s2_title": "📐 Les tres parts de la fórmula",
        "s2_intro": "Tot sistema d'IA funciona de la mateixa manera, seguint aquesta fórmula simple:",
        "lbl_input": "ENTRADA",
        "lbl_model": "MODEL",
        "lbl_output": "SORTIDA",
        "desc_input": "Entren dades",
        "desc_model": "La IA les processa",
        "desc_output": "Surt la predicció",
        "s2_ex_title": "Exemples del món real:",
        "s2_ex1_in": "Foto d'un gos",
        "s2_ex1_mod": "IA de reconeixement d'imatges",
        "s2_ex1_out": "\"Això és un Golden Retriever\"",
        "s2_ex2_in": "\"Quin temps fa?\"",
        "s2_ex2_mod": "IA de llenguatge (com ChatGPT)",
        "s2_ex2_out": "Una resposta útil",
        "s2_ex3_in": "Historial criminal d'una persona",
        "s2_ex3_mod": "IA d'avaluació de riscos",
        "s2_ex3_out": "\"Alt Risc\" o \"Baix Risc\"",
        "btn_back": "◀️ Enrere",
        "btn_next_learn": "Següent: Com aprenen els models ▶️",
        # Step 3
        "s3_title": "🧠 Com aprèn un model d'IA?",
        "s3_h1": "1. Aprèn d'exemples",
        "s3_p1": "Un model d'IA no està programat amb respostes. En canvi, s'entrena amb una gran quantitat d'exemples i aprèn a trobar les respostes per si mateix.",
        "s3_p2": "En el nostre escenari de justícia, això significa alimentar el model amb milers de casos passats (<b>exemples</b>) per ensenyar-li a trobar els <b>patrons</b> que connecten els detalls d'una persona amb el seu risc criminal.",
        "s3_h2": "2. El procés d'entrenament",
        "s3_p3": "La IA \"s'entrena\" repetint el cicle milions de vegades a través de dades històriques (casos passats):",
        "flow_1": "1. EXEMPLES<br>ENTRADA",
        "flow_2": "2. MODEL<br>ESTIMACIONS",
        "flow_3": "3. REVISAR<br>RESPOSTA",
        "flow_4": "4. AJUSTAR<br>PESOS",
        "flow_5": "MODEL<br>APRÈS",
        "s3_p4": "Durant el pas d'<b>\"ajustar\"</b>, el model canvia les seves regles internes (anomenades <b>\"pesos\"</b>) per apropar-se a la resposta correcta. Per exemple, aprèn <b>quant</b> han d'importar més els \"delictes previs\" que l'\"edat\".",
        "s3_eth_title": "⚠️ El desafiament ètic",
        "s3_eth_p": "<b>Aquí ens trobem amb un problema crític:</b> El model *només* aprèn de les dades. Si les dades històriques estan esbiaixades (per exemple, certs grups de persones van ser detinguts amb més freqüència), el model aprendrà aquests patrons esbiaixats.<br><br><b>El model no coneix d'\"equitat\" o de \"justícia\", només coneix patrons.</b>",
        "btn_next_try": "Següent: Prova-ho tu mateix ▶️",
        # Step 4
        "s4_title": "🎮 Prova-ho tu mateix!",
        "s4_intro": "<b>Utilitzem un model d'IA simple per predir el risc de reincidència.</b><br>A continuació, ajusta les entrades i observa com canvia la predicció del model!",
        "s4_sect1": "1️⃣ ENTRADA: Ajusta les dades",
        "lbl_age": "Edat",
        "info_age": "Edat de la persona presa",
        "lbl_priors": "Delictes previs",
        "info_priors": "Nombre de crims anteriors",
        "lbl_severity": "Gravetat del càrrec actual",
        "info_severity": "Què tan greu és el càrrec actual?",
        "opt_minor": "Menor",
        "opt_moderate": "Moderat",
        "opt_serious": "Greu",
        "s4_sect2": "2️⃣ MODEL: Processa les dades",
        "btn_run": "🔮 Executar predicció de la IA",
        "s4_sect3": "3️⃣ SORTIDA: Veure la predicció",
        "res_placeholder": "Fes clic a \"Executar la predicció de la IA\" per veure el resultat",
        "s4_highlight": "<b>El que acabes de fer:</b><br><br>Has utilitzat un model d'IA molt simple! Has proporcionat <b style='color:#0369a1;'>dades d'entrada</b> (edat, delictes, gravetat), el <b style='color:#92400e;'>model les ha processat</b> utilitzant regles i patrons, i ha produït una <b style='color:#15803d;'>predicció de sortida</b>.<br><br>Els models d'IA reals són més complexos, però funcionen sota el mateix principi!",
        "btn_next_conn": "Següent: Connexió amb la justícia ▶️",
        # Step 5
        "s5_title": "🔗 Connexió amb el sistema de justícia penal",
        "s5_p1": "<b>Recordes la predicció de risc que has utilitzat abans en el teu rol de jutge?</b>",
        "s5_p2": "Aquest és un exemple real de l'aplicació de la IA:",
        "s5_in_desc": "• Edat, raça, gènere, delictes previs, detalls del càrrec",
        "s5_mod_desc1": "• Entrenat amb dades històriques de justícia penal",
        "s5_mod_desc2": "• Busca patrons entre les persones que van reincidir en el passat",
        "s5_out_desc": "• \"Alt Risc\", \"Risc Mitjà\" o \"Baix Risc\"",
        "s5_h2": "Per què això és important per a l'ètica?",
        "s5_li1": "Les <b>dades d'entrada</b> poden contenir biaixos històrics",
        "s5_li2": "El <b>model</b> aprèn patrons de decisions passades potencialment injustes",
        "s5_li3": "Les <b>prediccions de sortida</b> poden perpetuar la discriminació",
        "s5_final": "<b>Entendre com funciona la IA és el primer pas per construir sistemes més justos.</b><br><br>Ara que saps què és la IA, estàs a punt per ajudar a dissenyar models que siguin més ètics i menys esbiaixats!",
        "btn_complete": "Completar aquesta secció ▶️",
        # Step 6
        "s6_title": "🎓 Ara ja entens els conceptes bàsics de la IA!",
        "s6_congrats": "<b>Felicitats!</b> Ara saps:",
        "s6_li1": "Què és la IA (un sistema de predicció)",
        "s6_li2": "Com funciona (Entrada → Model → Sortida)",
        "s6_li3": "Com els models d'IA aprenen de les dades",
        "s6_li4": "Per què importa per a la justícia penal",
        "s6_li5": "Les implicacions ètiques de les decisions de la IA",
        "s6_next": "<b>Propers Passos:</b>",
        "s6_next_desc": "En les següents seccions, aprendràs com construir i millorar models d'IA per fer-los més justos i ètics.",
        "s6_scroll": "👇 Continua amb la següent activitat a sota — o fes clic a <span style='white-space:nowrap;'>Següent (barra superior)</span> en vista ampliada ➡️",
        "s6_find": "",
        "btn_review": "◀️ Tornar a revisar",
        "risk_high": "Alt Risc",
        "risk_med": "Risc Mitjà",
        "risk_low": "Baix Risc",
        "risk_score": "Puntuació de risc:"
    }
}


def _create_simple_predictor():
    """Create a simple demonstration predictor for teaching purposes."""
    
    # Helper for translation
    def t(lang, key):
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

    def predict_outcome(age, priors, severity, lang="en"):
        """Simple rule-based predictor for demonstration."""
        
        # Translate generic input to English for logic if needed (or map values)
        # Assuming severity inputs come in as the localized string, we map them
        severity_map = {
            "Minor": 1, "Menor": 1,
            "Moderate": 2, "Moderado": 2, "Moderat": 2,
            "Serious": 3, "Grave": 3, "Greu": 3
        }
        
        score = 0
        if age < 25: score += 3
        elif age < 35: score += 2
        else: score += 1

        if priors >= 3: score += 3
        elif priors >= 1: score += 2
        else: score += 0

        score += severity_map.get(severity, 2)

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

        score_label = t(lang, "risk_score")

        return f"""
        <div class="prediction-card" style="border-color:{color};">
            <h2 class="prediction-title" style="color:{color};">{emoji} {risk}</h2>
            <p class="prediction-score">{score_label} {score}/9</p>
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
          <p>{t(lang, 's1_sub')}</p>
          <h3 style='color:#0369a1; margin-top:24px;'>{t(lang, 's1_list_title')}</h3>
          <ul style='font-size:19px; margin-top:12px;'>
              <li>{t(lang, 's1_li1')}</li>
              <li>{t(lang, 's1_li2')}</li>
              <li>{t(lang, 's1_li3')}</li>
          </ul>
          <div class='highlight-soft' style='border-left:6px solid #f59e0b;'>
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
                  <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                      <b style='color:#92400e;'>{t(lang, 'flow_4')}</b>
                  </div>
                  <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                  <div style='background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                      <b style='color:#15803d;'>{t(lang, 'flow_5')}</b>
                  </div>
              </div>
          </div>
          <p style='margin-top:20px;'>{t(lang, 's3_p4')}</p>
          <hr style='margin:24px 0;'>
          <h3 style='color:#dc2626;'>{t(lang, 's3_eth_title')}</h3>
          <div class='keypoint-box'>
              <p style='margin:0;'>{t(lang, 's3_eth_p')}</p>
          </div>
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
          <p style='margin-top:20px;'>{t(lang, 's5_p2')}</p>
          <div class='inner-card inner-card-emphasis-blue' style='border-color:#9333ea;'>
              <p style='font-size:18px; margin-bottom:16px;'>
              <b class='io-label-input'>{t(lang, 'lbl_input')}:</b> {t(lang, 'info_age')}, ...<br>
              <span style='margin-left:24px; color:#6b7280;'>{t(lang, 's5_in_desc')}</span>
              </p>
              <p style='font-size:18px; margin:16px 0;'>
              <b class='io-label-model'>{t(lang, 'lbl_model')}:</b> {t(lang, 's2_ex3_mod')}<br>
              <span style='margin-left:24px; color:#6b7280;'>{t(lang, 's5_mod_desc1')}</span><br>
              <span style='margin-left:24px; color:#6b7280;'>{t(lang, 's5_mod_desc2')}</span>
              </p>
              <p style='font-size:18px; margin-top:16px; margin-bottom:0;'>
              <b class='io-label-output'>{t(lang, 'lbl_output')}:</b> {t(lang, 's2_ex3_out')}<br>
              <span style='margin-left:24px; color:#6b7280;'>{t(lang, 's5_out_desc')}</span>
              </p>
          </div>
          <h3 style='color:#7e22ce; margin-top:32px;'>{t(lang, 's5_h2')}</h3>
          <div class='keypoint-box'>
              <ul style='font-size:18px; margin:8px 0;'>
                  <li>{t(lang, 's5_li1')}</li>
                  <li>{t(lang, 's5_li2')}</li>
                  <li>{t(lang, 's5_li3')}</li>
              </ul>
          </div>
          <div class='highlight-soft' style='margin-top:24px;'>
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
                    <li>{t(lang, 's6_li5')}</li>
                </ul>
                <p style='margin-top:32px;'><b>{t(lang, 's6_next')}</b></p>
                <p>{t(lang, 's6_next_desc')}</p>
                <h1 class='final-instruction' style='margin:20px 0;'>{t(lang, 's6_scroll')}</h1>
                <p style='font-size:1.1rem;'>{t(lang, 's6_find')}</p>
            </div>
        </div>
        """

    # --- CSS (Standard) ---
    css = """
    /* (All original CSS classes kept intact) */
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
    .final-instruction {
      font-size: clamp(1.5rem, 2vw + 0.6rem, 2rem);
      line-height: 1.25;
      margin: 16px 0;
    }
    .completion-box { font-size: 1.3rem; padding: 28px; border-radius: 16px; background-color: var(--block-background-fill); color: var(--body-text-color); border: 2px solid #0284c7; box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08); }
    .prediction-card { background-color: var(--block-background-fill); color: var(--body-text-color); padding: 24px; border-radius: 12px; border: 3px solid var(--border-color-primary); text-align: center; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
    .prediction-title { margin: 0; font-size: 2.5rem; }
    .prediction-score { font-size: 18px; margin-top: 12px; color: var(--secondary-text-color); }
    .prediction-placeholder { background-color: var(--block-background-fill); color: var(--secondary-text-color); padding: 40px; border-radius: 12px; text-align: center; border: 1px solid var(--border-color-primary); }
    #nav-loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: color-mix(in srgb, var(--body-background-fill) 95%, transparent); z-index: 9999; display: none; flex-direction: column; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.3s ease; }
    .nav-spinner { width: 50px; height: 50px; border: 5px solid var(--border-color-primary); border-top: 5px solid var(--color-accent); border-radius: 50%; animation: nav-spin 1s linear infinite; margin-bottom: 20px; }
    @keyframes nav-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    #nav-loading-text { font-size: 1.3rem; font-weight: 600; color: var(--color-accent); }
    @media (prefers-color-scheme: dark) { .ai-intro-box, .step-card, .inner-card, .inner-card-wide, .keypoint-box, .highlight-soft, .completion-box, .prediction-card, .prediction-placeholder { background-color: #2D323E; color: white; border-color: #555555; box-shadow: none; } .inner-card, .inner-card-wide { background-color: #181B22; } #nav-loading-overlay { background: rgba(15, 23, 42, 0.9); } .nav-spinner { border-color: rgba(148, 163, 184, 0.4); border-top-color: var(--color-accent); } .io-chip-input { background-color: color-mix(in srgb, #1d4ed8 35%, #020617 65%); } .io-chip-model { background-color: color-mix(in srgb, #b45309 40%, #020617 60%); } .io-chip-output { background-color: color-mix(in srgb, #15803d 40%, #020617 60%); } .io-arrow { color: #e5e7eb; } }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        lang_state = gr.State("en")
        
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("<div id='nav-loading-overlay'><div class='nav-spinner'></div><span id='nav-loading-text'>Loading...</span></div>")

        # --- Variables for dynamic updating ---
        c_title = gr.Markdown("<h1 style='text-align:center;'>🤖 What is AI, Anyway?</h1>")

        with gr.Column(visible=False) as loading_screen:
            c_load = gr.Markdown(f"<div style='text-align:center; padding: 100px 0;'><h2 class='loading-title'>{t('en', 'loading')}</h2></div>")

        # Step 1
        with gr.Column(visible=True, elem_id="step-1") as step_1:
            c_intro = gr.HTML(f"<div class='ai-intro-box'>{t('en', 'intro_box')}</div>")
            gr.HTML("<hr style='margin:24px 0;'>")
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
        
        # --- CACHED UPDATE LOGIC ---

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

        @lru_cache(maxsize=16)
        def get_cached_ui_updates(lang):
            """Cache the heavy UI generation."""
            
            # Helper must be defined here or available in scope
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
                f"<div class='prediction-placeholder'><p style='font-size:18px; margin:0;'>{t(lang, 'res_placeholder')}</p></div>", 
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

        def update_language(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS: lang = "en"
            
            return get_cached_ui_updates(lang)
        
        demo.load(update_language, inputs=None, outputs=update_targets)

        # --- PREDICTION BUTTON LOGIC ---
        # Note: We pass lang_state to the predictor to ensure result is translated
        predict_btn.click(
            predict_outcome,
            inputs=[age_slider, priors_slider, severity_dropdown, lang_state],
            outputs=prediction_output,
            show_progress="full",
            scroll_to_output=True,
            api_name="predict")

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

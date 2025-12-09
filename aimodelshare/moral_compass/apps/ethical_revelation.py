"""
The Ethical Revelation: Real-World Impact - Gradio application for the Justice & Equity Challenge.
Updated with i18n support for English (en), Spanish (es), and Catalan (ca).
"""

import os
import random
import time
import threading
from typing import Optional, Dict, Any, Tuple

import pandas as pd
import gradio as gr

# --- AI Model Share Imports ---
try:
    from aimodelshare.playground import Competition
    from aimodelshare.aws import get_token_from_session, _get_username_from_token
except ImportError:
    # For local dev without aimodelshare installed, mock these if needed or raise error
    # raise ImportError("The 'aimodelshare' library is required. Install with: pip install aimodelshare")
    pass

# ---------------------------------------------------------------------------
# Configuration & Caching
# ---------------------------------------------------------------------------
LEADERBOARD_CACHE_SECONDS = int(os.environ.get("LEADERBOARD_CACHE_SECONDS", "45"))
MAX_LEADERBOARD_ENTRIES = os.environ.get("MAX_LEADERBOARD_ENTRIES")
MAX_LEADERBOARD_ENTRIES = int(MAX_LEADERBOARD_ENTRIES) if MAX_LEADERBOARD_ENTRIES else None
DEBUG_LOG = os.environ.get("DEBUG_LOG", "false").lower() == "true"

TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]

# NEW: Team name translations for UI display only
# Internal logic (ranking, caching, grouping) always uses canonical English names
TEAM_NAME_TRANSLATIONS = {
    "en": {
        "The Justice League": "The Justice League",
        "The Moral Champions": "The Moral Champions",
        "The Data Detectives": "The Data Detectives",
        "The Ethical Explorers": "The Ethical Explorers",
        "The Fairness Finders": "The Fairness Finders",
        "The Accuracy Avengers": "The Accuracy Avengers"
    },
    "es": {
        "The Justice League": "La Liga de la Justicia",
        "The Moral Champions": "Los Campeones Morales",
        "The Data Detectives": "Los Detectives de Datos",
        "The Ethical Explorers": "Los Exploradores Éticos",
        "The Fairness Finders": "Los Buscadores de Equidad",
        "The Accuracy Avengers": "Los Vengadores de Precisión"
    },
    "ca": {
        "The Justice League": "La Lliga de la Justícia",
        "The Moral Champions": "Els Campions Morals",
        "The Data Detectives": "Els Detectives de Dades",
        "The Ethical Explorers": "Els Exploradors Ètics",
        "The Fairness Finders": "Els Cercadors d'Equitat",
        "The Accuracy Avengers": "Els Venjadors de Precisió"
    }
}

_cache_lock = threading.Lock()
_leaderboard_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
_user_stats_cache: Dict[str, Dict[str, Any]] = {}
USER_STATS_TTL = LEADERBOARD_CACHE_SECONDS

# ---------------------------------------------------------------------------
# TRANSLATION CONFIGURATION
# ---------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "title": "🚀 The Ethical Revelation: Real-World Impact",
        "loading_personal": "⏳ Loading your personalized experience...",
        # Stats Screen
        "stats_title": "🏆 Great Work, Engineer! 🏆",
        "stats_subtitle": "Here's your performance summary.",
        "stats_heading": "Your Stats",
        "lbl_accuracy": "Best Accuracy",
        "lbl_rank": "Your Rank",
        "lbl_team": "Team",
        "stats_footer": "Ready to share your model and explore its real-world impact?",
        "btn_deploy": "🌍 Share Your AI Model (Simulation Only)",
        "guest_title": "🚀 You're Signed In!",
        "guest_subtitle": "You haven't submitted a model yet, but you're all set to continue learning.",
        "guest_body": "Once you submit a model in the Model Building Game, your accuracy and ranking will appear here.",
        "guest_footer": "Continue to the next section when you're ready.",
        "loading_session": "🔒 Loading your session...",
        # Step 2 (Warning)
        "s2_title": "⚠️ But Wait...",
        "s2_intro": "Before we share the model, there's something you need to know...",
        "s2_box_title": "A Real-World Story",
        "s2_p1": "A model similar to yours was actually used in the real world. It was used by judges across the United States to determine whether to grant parole to people in prison.",
        "s2_p2": "Like yours, it had impressive accuracy scores. Like yours, it was built on data about past criminal cases. Like yours, it aimed to predict who might re-offend.",
        "s2_p3": "But something was terribly wrong...",
        "btn_back": "◀️ Back",
        "btn_reveal": "Reveal the Truth ▶️",
        # Step 3 (ProPublica)
        "s3_title": "📰 The ProPublica Investigation",
        "s3_head": "\"Machine Bias\" - A Landmark Investigation",
        "s3_p1": "In 2016, journalists at <strong>ProPublica</strong> investigated a widely-used criminal risk assessment algorithm called <strong>COMPAS</strong>. They analyzed over <strong>7,000 actual cases</strong> to see if the AI's predictions came true.",
        "s3_box_title": "Their Shocking Findings:",
        "s3_alert": "⚠️ Black defendants were labeled \"high-risk\" at nearly <u>TWICE</u> the rate of white defendants.",
        "s3_spec": "<strong>Specifically:</strong>",
        "s3_li1_pre": "<strong>Black defendants</strong> who <em>did NOT re-offend</em>, were incorrectly labeled as <strong>\"high-risk\"</strong> at a rate of about <strong>45%</strong>",
        "s3_li2_pre": "<strong>White defendants</strong> who <em>did NOT re-offend</em> were incorrectly labeled as <strong>\"high-risk\"</strong> at a rate of only <strong>24%</strong>",
        "s3_li3": "Meanwhile, <strong>white defendants</strong> who <em>DID re-offend</em> were <strong>more likely to be labeled \"low-risk\"</strong> compared to Black defendants",
        "s3_box2_title": "What Does This Mean?",
        "s3_mean_p1": "The AI system was <strong class='emph-danger'>systematically biased</strong>. It didn't just make random errors—it made <strong>different kinds of errors for different groups of people</strong>.",
        "s3_mean_p2": "Black defendants faced a much higher risk of being <strong class='emph-danger'>unfairly labeled as dangerous</strong>, potentially leading to longer prison sentences or denied parole—even when they would not have re-offended.",
        "btn_eu": "See This in Europe ▶️",
        "lbl_black": "Black", # Used in dynamic construction if needed
        # Step 4 EU
        "s4eu_title": "🇪🇺 This Isn’t Just a US Problem",
        "s4eu_head": "Europe Is Already Using AI to Predict Reoffending Risk",
        "s4eu_intro": "The COMPAS story is not just an American warning. Across Europe, public authorities have experimented with <strong>very similar tools</strong> designed to predict who might reoffend or which areas are considered “high risk”.",
        "s4eu_li1_title": "United Kingdom – HART (Harm Assessment Risk Tool)",
        "s4eu_li1_body": "A machine-learning model used by Durham Police to predict who will reoffend within two years. It uses variables like age, gender, <em>postcode</em>, housing and job instability – socio-economic proxies that can reproduce the same kinds of biased patterns exposed in COMPAS.",
        "s4eu_li2_title": "Spain – VioGén",
        "s4eu_li2_body": "A risk tool for gender-violence cases whose inner workings are largely a <em>\"black box\"</em>. Officers rely heavily on its scores to decide protection measures, even though the algorithm cannot easily be audited for bias or errors.",
        "s4eu_li3_title": "Netherlands & Denmark – Predictive profiling",
        "s4eu_li3_body": "Systems like the Dutch <em>Crime Anticipation System (CAS)</em> and Denmark’s algorithmic <em>“ghetto”</em> classifications use demographic and socio-economic data to steer policing and penalties, risking feedback loops that target certain communities again and again.",
        "s4eu_box_title": "Ongoing European Debate",
        "s4eu_box_body": "The Barcelona Prosecuter's office has proposed an \"electronic repeat-offense calculator\". Courts, regulators and researchers are actively examining how these tools affect fundamental rights such as non-discrimination, fair trial and data protection.",
        "s4eu_note": "<strong>Key point:</strong> The risks you saw with COMPAS are not far away in another country. <strong class='emph-key'>They are live questions in both Europe and the U.S. right now.</strong>",
        "btn_back_invest": "◀️ Back to the Investigation",
        "btn_zoom": "Zoom Out to the Lesson ▶️",
        # Step 4 Lesson
        "s4_title": "💡 The Critical Lesson",
        "s4_box_title": "Why This Matters:",
        "s4_li1_title": "A model’s overall accuracy can hide group-specific harm",
        "s4_li1_body": "A model might be 70% accurate overall — but the remaining 30% of errors can fall disproportionately on <span class='emph-harm'>specific groups</span>, resulting in real harm even when the total accuracy appears “good”.",
        "s4_li2_title": "Historical bias in training data gets amplified",
        "s4_li2_body": "If past policing or judicial decisions were biased, the AI system will <span class='emph-harm'>learn and reinforce</span> those inequities — often making them worse at scale.",
        "s4_li3_title": "Real people's lives are affected",
        "s4_li3_body": "Each <strong class='emph-harm'>\"false positive\"</strong> represents a person who may lose years of freedom, employment, housing, or family connection — all due to a single <strong class='emph-harm'>biased prediction</strong>.",
        "btn_back_eu": "◀️ Back",
        "btn_what_do": "What Can We Do? ▶️",
        # Step 5 Path
        "s5_title": "🛤️ The Path Forward",
        "s5_head": "From Accuracy to Ethics",
        "s5_intro": "You've now seen both sides of the AI story:",
        "s5_li1": "✅ You built models that achieved higher accuracy scores",
        "s5_li2": "⚠️ You learned how similar models caused real-world harm",
        "s5_li3": "🤔 You understand that accuracy alone is not enough",
        "s5_box_title": "What You'll Do Next:",
        "s5_p1": "In the next section, you'll be introduced to a <strong class='emph-key'>new way of measuring success</strong>—one that balances performance with fairness and ethics.",
        "s5_p2": "You'll learn techniques to <strong class='emph-key'>detect bias</strong> in your models, <strong class='emph-key'>measure fairness</strong> across different groups, and <strong class='emph-key'>redesign your AI</strong> to minimize harm.",
        "s5_mission": "🎯 Your new mission: Build AI that is not just accurate, but also <strong class='emph-key'>fair, equitable, and ethically sound</strong>.",
        "s5_scroll": "👇 SCROLL DOWN 👇",
        "s5_continue": "Continue to the next section below to begin your ethical AI journey.",
        "btn_review": "◀️ Review the Investigation"
    },
    "es": {
        "title": "🚀 La revelación ética: impacto real",
        "loading_personal": "⏳ Cargando tu experiencia personalizada...",
        "stats_title": "🏆 ¡Gran trabajo, ingeniero/a! 🏆",
        "stats_subtitle": "Aquí tienes el resumen de tu rendimiento.",
        "stats_heading": "Tus estadísticas",
        "lbl_accuracy": "Mejor precisión",
        "lbl_rank": "Tu rango",
        "lbl_team": "Equipo",
        "stats_footer": "¿Listo para compartir tu modelo y explorar su impacto en el mundo real?",
        "btn_deploy": "🌍 Compartir tu modelo de IA (simulación)",
        "guest_title": "🚀 ¡Has iniciado sesión!",
        "guest_subtitle": "Aún no has enviado un modelo, pero estás listo para seguir aprendiendo.",
        "guest_body": "Una vez que envíes un modelo en el Juego de Construcción de Modelos, tu precisión y clasificación aparecerán aquí.",
        "guest_footer": "Continúa a la siguiente sección cuando estés listo.",
        "loading_session": "🔒 Cargando tu sesión...",
        "s2_title": "⚠️ Pero espera...",
        "s2_intro": "Antes de compartir el modelo, hay algo que necesitas saber...",
        "s2_box_title": "Una historia del mundo real",
        "s2_p1": "Un modelo similar al tuyo se empleó en situaciones reales. Jueces de todo Estados Unidos lo usaron para determinar si conceder la libertad condicional a personas presas.",
        "s2_p2": "Como el tuyo, tenía puntuaciones de precisión impresionantes. Como el tuyo, se construyó con datos de casos criminales pasados. Como el tuyo, su objetivo era predecir quíen podría volver a cometer un delito..",
        "s2_p3": "Pero algo iba muy mal...",
        "btn_back": "◀️ Atrás",
        "btn_reveal": "Revelar la verdad ▶️",
        "s3_title": "📰 La investigación de ProPublica",
        "s3_head": "\"Machine Bias\" - Una investigación de referencia sobre los sesgos algorítmicos",
        "s3_p1": "En 2016, periodistas de <strong>ProPublica</strong> investigaron un algoritmo de evaluación de riesgo criminal ampliamente utilizado llamado <strong>COMPAS</strong>. Analizaron más de <strong>7,000 casos reales</strong> para ver si las predicciones de la IA se cumplían.",
        "s3_box_title": "Sus hallazgos impactantes:",
        "s3_alert": "⚠️ Las personas negras presas fueron clasificadas como \"alto riesgo\" casi el <u>DOBLE</u> que las personas blancas presas.",
        "s3_spec": "<strong>Específicamente:</strong>",
        "s3_li1_pre": "Las <span class='emph-danger'>personas negras presas</span> que <em>NO volvieron a cometer un delito</em> fueron clasificadas incorrectamente como <strong>\"alto riesgo\"</strong> en aproximadamente un <strong>45%</strong> de los casos",
        "s3_li2_pre": "Las <strong>personas blancas presas</strong> que <em>NO reincidieron</em> fueron clasificadas incorrectamente como <strong>\"alto riesgo\"</strong> solo en un <strong>24%</strong> de los casos",
        "s3_li3": "En cambio, las <strong>personas blancas presas</strong> que <em>SÍ reincidieron</em> tenían <strong>más probabilidades de ser clasificadas como de \"bajo riesgo\"</strong> en comparación con las personas negras presas",
        "s3_box2_title": "¿Qué significa esto?",
        "s3_mean_p1": "El sistema de IA mostraba <strong class='emph-danger'>un sesgo sistemático</strong>. No solo cometía errores al azar; también hacía <strong>errores distintos según el grupo de personas</strong>.",
        "s3_mean_p2": "Las personas negras presas enfrentaban un riesgo mucho mayor de ser <strong class='emph-danger'>injustamente classificadas como peligrosas</strong>, lo que potencialmente conducía a sentencias de prisión más largas o libertad condicional denegada, incluso cuando no habrían vuelto a cometer un delito.",
        "btn_eu": "Ver esto en Europa ▶️",
        "lbl_black": "Negros",
        "s4eu_title": "🇪🇺 Esto no es solo un problema de EE. UU.",
        "s4eu_head": "Europa ya utiliza IA para evaluar el riesgo de reincidencia",
        "s4eu_intro": "La historia de COMPAS no es solo una advertencia estadounidense. En toda Europa, las autoridades públicas han experimentado con <strong>herramientas muy similares</strong> que pretenden predecir quién reincidirá o qué áreas son de \"alto riesgo\".",
        "s4eu_li1_title": "Reino Unido – HART (Harm Assessment Risk Tool)",
        "s4eu_li1_body": "Un modelo de aprendizaje automático utilizado por la Policía de Durham para predecir quién reincidirá en dos años. Utiliza variables como edad, género, <em>código postal</em>, vivienda e inestabilidad laboral: indicadores socioeconómicos que pueden reproducir los mismos tipos de patrones sesgados expuestos en COMPAS.",
        "s4eu_li2_title": "España – VioGén",
        "s4eu_li2_body": "Una herramienta de riesgo para casos de violencia de género cuyo funcionamiento interno es en gran medida una <em>\"caja negra\"</em>. Los oficiales dependen en gran medida de sus puntuaciones para decidir medidas de protección, aunque no se puede auditar fácilmente el algoritmo en busca de sesgos o errores.",
        "s4eu_li3_title": "Países Bajos y Dinamarca – Perfiles predictivos",
        "s4eu_li3_body": "Sistemas como el <em>Crime Anticipation System (CAS)</em> holandés y las clasificaciones algorítmicas de <em>\"guetos\"</em> de Dinamarca utilizan datos demográficos y socioeconómicos para orientar la vigilancia i las sanciones, con el riesgo de generar bucles de retroalimentación que señalen una y otra vez a las mismas comunidades.",
        "s4eu_box_title": "Debate europeo en curso",
        "s4eu_box_body": "La Fiscalía de Barcelona ha propuesto una \"calculadora electrónica de reincidencia\". Tribunales, reguladores e investigadores están examinando activamente cómo estas herramientas afectan los derechos fundamentales como la no discriminación, el juicio justo y la protección de datos.",
        "s4eu_note": "<strong>Idea clave:</strong> Los riesgos que viste con COMPAS no están lejos ni son ajenos. <strong class='emph-key'>Son cuestiones pleanmente actuales tanto en Europa como en los EE. UU.</strong>",
        "btn_back_invest": "◀️ Volver a la investigación",
        "btn_zoom": "Vista general de la lección ▶️",
        "s4_title": "💡 La lección fundamental",
        "s4_box_title": "Por qué importa esto:",
        "s4_li1_title": "La precisión global de un modelo puede ocultar daños específicos por grupo",
        "s4_li1_body": "Un modelo puede tener un 70% de precisión global, pero el 30% restante de errores puede concentrarse de manera desproporcionada en <span class='emph-harm'>grupos concretos</span>, causando daños reales incluso cuando la precisión global parece \"buena\".",
        "s4_li2_title": "El sesgo histórico en los datos de entrenamiento se amplifica",
        "s4_li2_body": "Si las decisiones policiales o judiciales pasadas fueron sesgadas, el sistema de IA <span class='emph-harm'>aprenderá y reforzará</span> esas desigualdades, y a menudo las amplificará a gran escala.",
        "s4_li3_title": "Las vidas de personas reales se ven afectadas",
        "s4_li3_body": "Cada <strong class='emph-harm'>\"falso positivo\"</strong> representa a una persona que puede perder años de libertad, empleo, vivienda o conexión familiar, todo a causa de una sola <strong class='emph-harm'>predicción sesgada</strong>.",
        "btn_back_eu": "◀️ Atrás",
        "btn_what_do": "¿Qué podemos hacer? ▶️",
        "s5_title": "🛤️ El camino a seguir",
        "s5_head": "De la precisión a la ética",
        "s5_intro": "Ya has visto los dos lados de la IA:",
        "s5_li1": "✅ Has construido modelos con altos niveles de precisión",
        "s5_li2": "⚠️ Has aprendido cómo modelos similares han causado daños reales",
        "s5_li3": "🤔 Entiendes que la precisión por sí sola no es suficiente",
        "s5_box_title": "Lo que harás a continuación:",
        "s5_p1": "En la siguiente sección, se te presentará una <strong class='emph-key'>nueva forma de medir el éxito</strong>, una que equilibra el rendimiento con la equidad y la ética.",
        "s5_p2": "Aprenderás técnicas para <strong class='emph-key'>detectar sesgos</strong> en tus modelos, <strong class='emph-key'>medir la equidad</strong> en diferentes grupos y <strong class='emph-key'>rediseñar tu IA</strong> para minimizar el daño.",
        "s5_mission": "🎯 Tu nueva misión: Construir una IA que no solo sea precisa, sino también <strong class='emph-key'>justa, equitativa y éticamente sólida</strong>.",
        "s5_scroll": "👇 DESPLÁZATE HACIA ABAJO 👇",
        "s5_continue": "Continúa en la siguiente sección para comenzar tu viaje de IA ética.",
        "btn_review": "◀️ Revisar la Investigación"
    },
    "ca": {
        "title": "🚀 La revelació ètica: impacte real",
        "loading_personal": "⏳ Carregant la teva experiència personalitzada...",
        "stats_title": "🏆 Bona feina, enginyer/a! 🏆",
        "stats_subtitle": "Aquí tens el teu resum de rendiment.",
        "stats_heading": "Les teves estadístiques",
        "lbl_accuracy": "Millor precisió",
        "lbl_rank": "El teu rang",
        "lbl_team": "Equip",
        "stats_footer": "A punt per compartir el teu model i explorar el seu impacte al món real?",
        "btn_deploy": "🌍 Compartir el teu model d'IA (simulació)",
        "guest_title": "🚀 Has iniciat sessió!",
        "guest_subtitle": "Encara no has enviat un model, però estàs a punt per continuar aprenent.",
        "guest_body": "Un cop enviïs un model al Joc de Construcció de Models, la teva precisió i classificació apareixeran aquí.",
        "guest_footer": "Continua a la següent secció quan estiguis a punt.",
        "loading_session": "🔒 Carregant la teva sessió...",
        "s2_title": "⚠️ Però espera...",
        "s2_intro": "Abans de compartir el model, hi ha una cosa que hauries de saber...",
        "s2_box_title": "Una història del món real",
        "s2_p1": "Un model similar al teu es va utilitzar en situacions reals. Jutges d’arreu dels Estats Units el van fer servir per determinar si concedir la llibertat condicional a persones preses.",
        "s2_p2": "Com el teu, tenia puntuacions de precisió impressionants. Com el teu, es va construir amb dades de casos criminals passats. Com el teu, el seu objectiu era predir qui podria tornar a cometre un delicte.",
        "s2_p3": "Però alguna cosa anava molt malament...",
        "btn_back": "◀️ Enrere",
        "btn_reveal": "Revelar la veritat ▶️",
        "s3_title": "📰 La investigació de ProPublica",
        "s3_head": "\"Machine Bias\" - Una investigació històrica sobre els biaixos algorítmics",
        "s3_p1": "El 2016, periodistes de <strong>ProPublica</strong> van analitzar un algoritme d’avaluació del risc penal molt estès anomenat <strong>COMPAS</strong>. Van estudiar més de <strong>7.000 casos reals</strong> per veure si les prediccions de la IA es complien.",
        "s3_box_title": "Les seves troballes més impactants:",
        "s3_alert": "⚠️ Les persones negres preses eren classificades com a \"alt risc\" gairebé el <u>DOBLE</u> que les persones blanques preses.",
        "s3_spec": "<strong>En concret:</strong>",
        "s3_li1_pre": "Les <span class='emph-danger'>persones negres preses</span> que <em>NO van tornar a cometre un delicte</em> van ser classificades incorrectament com a <strong>\"alt risc\"</strong> en aproximadament el <strong>45%</strong> dels casos",
        "s3_li2_pre": "Les <strong>persones blanques preses</strong> que <em>NO van reincidir</em> van ser classificades incorrectament com a <strong>\"alt risc\"</strong> en només el <strong>24%</strong> dels casos",
        "s3_li3": "En canvi, les <strong>persones blanques preses</strong> que <em>SÍ van reincidir</em> tenien <strong>més probabilitats de ser classificades com a \"baix risc\"</strong> en comparació amb les persones negres preses",
        "s3_box2_title": "Què significa això?",
        "s3_mean_p1": "El sistema d'IA estava <strong class='emph-danger'>sistemàticament esbiaixat</strong>. No només cometia errors aleatoris, cometia <strong>diferents tipus d'errors segons el grup de persones</strong>.",
        "s3_mean_p2": "Les persones negres preses s'enfrontaven a un risc molt més gran de ser <strong class='emph-danger'>injustament classificats com a perillosos</strong>, la qual cosa que podia comportar penes de presó més llargues o que se’ls denegués la llibertat condicional, fins i tot quan no haurien tornat a cometre un delicte.",
        "btn_eu": "Veure això a Europa ▶️",
        "lbl_black": "Negres",
        "s4eu_title": "🇪🇺 Això no és només un problema dels EUA",
        "s4eu_head": "Europa ja utilitza IA per avaluar el risc de reincidència",
        "s4eu_intro": "La història de COMPAS no és només una advertència nord-americana. A tota Europa, les autoritats públiques han experimentat amb <strong>eines molt similars</strong> que pretenen predir qui reincidirà o quines àrees són d'\"alt risc\".",
        "s4eu_li1_title": "Regne Unit – HART (Harm Assessment Risk Tool)",
        "s4eu_li1_body": "Un model d'aprenentatge automàtic utilitzat per la Policia de Durham per predir qui reincidirà en dos anys. Utilitza variables com edat, gènere, <em>codi postal</em>, habitatge i inestabilitat laboral: indicadors socioeconòmics que poden reproduir els mateixos tipus de patrons esbiaixats exposats a COMPAS.",
        "s4eu_li2_title": "Espanya – VioGén",
        "s4eu_li2_body": "Una eina de risc per a casos de violència de gènere, amb processos interns que són, en gran part, una <em>\"caixa negra\"</em>. Les autoritats depenen àmpliament de les seves puntuacions per decidir mesures de protecció, tot i que l’algoritme no es pot auditar fàcilment per detectar biaixos o errors.",
        "s4eu_li3_title": "Països Baixos i Dinamarca – Perfils predictius",
        "s4eu_li3_body": "Sistemes com el <em>Crime Anticipation System (CAS)</em> holandès i les classificacions algorítmiques de <em>\"guetos\"</em> de Dinamarca utilitzen dades demogràfiques i socioeconòmiques per orientar la vigilància i les sancions, amb el risc de generar bucles de retroalimentació que assenyalen una i altra vegada les mateixes comunitats.",
        "s4eu_box_title": "Debat europeu en curs",
        "s4eu_box_body": "La Fiscalia de Barcelona ha proposat una \"calculadora electrònica de reincidència\". Tribunals, reguladors i investigadors estan examinant activament com aquestes eines afecten els drets fonamentals com la no discriminació, el judici just i la protecció de dades.",
        "s4eu_note": "<strong>Punt clau:</strong> Els riscos que vas veure amb COMPAS no són lluny ni aliens. <strong class='emph-key'>Són qüestions plenament actuals tant a Europa com als EUA.</strong>",
        "btn_back_invest": "◀️ Tornar a la investigació",
        "btn_zoom": "Vista general de la Lliçó ▶️",
        "s4_title": "💡 La lliçó crítica",
        "s4_box_title": "Per què és important això:",
        "s4_li1_title": "La precisió global d'un model pot amagar danys específics a grups concrets",
        "s4_li1_body": "Un model pot tenir un 70% de precisió global, però el 30% restant d'errors pot recaure desproporcionadament en <span class='emph-harm'>determinats grups</span>, provocant danys reals fins i tot quan la precisió global sembla \"bona\".",
        "s4_li2_title": "El biaix històric en les dades d'entrenament s'amplifica",
        "s4_li2_body": "Si les decisions policials o judicials passades van ser esbiaixades, el sistema d'IA <span class='emph-harm'>aprendrà i reforçarà</span> aquestes desigualtats, i sovint les amplificarà.",
        "s4_li3_title": "Les vides de persones reals es veuen afectades",
        "s4_li3_body": "Cada <strong class='emph-harm'>\"fals positiu\"</strong> representa una persona que pot perdre anys de llibertat, feina, habitatge o connexió familiar, tot per una única <strong class='emph-harm'>predicció esbiaixada</strong>.",
        "btn_back_eu": "◀️ Enrere",
        "btn_what_do": "Què podem fer? ▶️",
        "s5_title": "🛤️ El camí a seguir",
        "s5_head": "De la precisió a l'ètica",
        "s5_intro": "Ara ja has vist els dos costats de la IA:",
        "s5_li1": "✅ Has construït models amb alts nivells de precisió",
        "s5_li2": "⚠️ Has après com models similars han causat danys reals",
        "s5_li3": "🤔 Entens que la precisió per si sola no és suficient",
        "s5_box_title": "Què faràs a continuació:",
        "s5_p1": "En la següent secció, se't presentarà una <strong class='emph-key'>nova manera de mesurar l'èxit</strong>, una que equilibra el rendiment amb l'equitat i l'ètica.",
        "s5_p2": "Aprendràs tècniques per <strong class='emph-key'>detectar biaixos</strong> en els teus models, <strong class='emph-key'>mesurar l'equitat</strong> en diferents grups i <strong class='emph-key'>redissenyar la teva IA</strong> per minimitzar el dany.",
        "s5_mission": "🎯 La teva nova missió: Construir una IA que no només sigui precisa, sinó també <strong class='emph-key'>justa, equitativa i èticament sòlida</strong>.",
        "s5_scroll": "👇 DESPLAÇA'T CAP AVALL 👇",
        "s5_continue": "Continua amb la següent secció per iniciar el teu recorregut cap a una IA ètica.",
        "btn_review": "◀️ Revisar la Investigació"
    }
}

# ---------------------------------------------------------------------------
# Logic / Helpers
# ---------------------------------------------------------------------------

def _log(msg: str):
    if DEBUG_LOG:
        print(f"[MoralCompassApp] {msg}")

def _normalize_team_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(str(name).strip().split())

# NEW: Team name translation helpers for UI display
def translate_team_name_for_display(team_en: str, lang: str = "en") -> str:
    """
    Translate a canonical English team name to the specified language for UI display.
    Fallback to English if translation not found.
    """
    if lang not in TEAM_NAME_TRANSLATIONS:
        lang = "en"
    return TEAM_NAME_TRANSLATIONS[lang].get(team_en, team_en)

# NEW: Reverse lookup for future use (e.g., if user input needs to be normalized back to English)
def translate_team_name_to_english(display_name: str, lang: str = "en") -> str:
    """
    Reverse lookup: given a localized team name, return the canonical English name.
    Returns the original display_name if not found.
    """
    if lang not in TEAM_NAME_TRANSLATIONS:
        return display_name  # Already English or unknown
    
    translations = TEAM_NAME_TRANSLATIONS[lang]
    for english_name, localized_name in translations.items():
        if localized_name == display_name:
            return english_name
    return display_name  # UPDATED: Return display_name instead of None for consistency

# NEW: Format leaderboard DataFrame with localized team names (non-destructive copy)
def _format_leaderboard_for_display(df: Optional[pd.DataFrame], lang: str = "en") -> Optional[pd.DataFrame]:
    """
    Create a copy of the leaderboard DataFrame with team names translated for display.
    Does not mutate the original DataFrame.
    For potential future use when displaying full leaderboard.
    """
    if df is None:
        return None  # UPDATED: Handle None explicitly
    
    if df.empty or "Team" not in df.columns:
        return df.copy()  # UPDATED: Return copy for empty or missing Team column
    
    df_display = df.copy()
    df_display["Team"] = df_display["Team"].apply(lambda t: translate_team_name_for_display(t, lang))
    return df_display

def _fetch_leaderboard(token: str) -> Optional[pd.DataFrame]:
    now = time.time()
    with _cache_lock:
        if (
            _leaderboard_cache["data"] is not None
            and now - _leaderboard_cache["timestamp"] < LEADERBOARD_CACHE_SECONDS
        ):
            return _leaderboard_cache["data"]

    try:
        playground_id = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
        playground = Competition(playground_id)
        df = playground.get_leaderboard(token=token)
        if df is not None and not df.empty and MAX_LEADERBOARD_ENTRIES:
            df = df.head(MAX_LEADERBOARD_ENTRIES)
    except Exception as e:
        _log(f"Leaderboard fetch failed: {e}")
        df = None

    with _cache_lock:
        _leaderboard_cache["data"] = df
        _leaderboard_cache["timestamp"] = time.time()
    return df

def _get_or_assign_team(username: str, leaderboard_df: Optional[pd.DataFrame]) -> Tuple[str, bool]:
    try:
        if leaderboard_df is not None and not leaderboard_df.empty and "Team" in leaderboard_df.columns:
            user_submissions = leaderboard_df[leaderboard_df["username"] == username]
            if not user_submissions.empty:
                if "timestamp" in user_submissions.columns:
                    try:
                        user_submissions = user_submissions.copy()
                        user_submissions["timestamp"] = pd.to_datetime(
                            user_submissions["timestamp"], errors="coerce"
                        )
                        user_submissions = user_submissions.sort_values("timestamp", ascending=False)
                    except Exception as ts_err:
                        _log(f"Timestamp sort error: {ts_err}")
                existing_team = user_submissions.iloc[0]["Team"]
                if pd.notna(existing_team) and str(existing_team).strip():
                    return _normalize_team_name(existing_team), False
        return _normalize_team_name(random.choice(TEAM_NAMES)), True
    except Exception as e:
        _log(f"Team assignment error: {e}")
        return _normalize_team_name(random.choice(TEAM_NAMES)), True

def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    try:
        session_id = request.query_params.get("sessionid") if request else None
        if not session_id:
            return False, None, None
        token = get_token_from_session(session_id)
        if not token:
            return False, None, None
        username = _get_username_from_token(token)
        if not username:
            return False, None, None
        return True, username, token
    except Exception as e:
        _log(f"Session auth failed: {e}")
        return False, None, None

def _compute_user_stats(username: str, token: str) -> Dict[str, Any]:
    now = time.time()
    cached = _user_stats_cache.get(username)
    if cached and (now - cached.get("_ts", 0) < USER_STATS_TTL):
        return cached

    leaderboard_df = _fetch_leaderboard(token)
    team_name, _ = _get_or_assign_team(username, leaderboard_df)
    best_score = None
    rank = None
    team_rank = None

    try:
        if leaderboard_df is not None and not leaderboard_df.empty:
            if "accuracy" in leaderboard_df.columns and "username" in leaderboard_df.columns:
                user_submissions = leaderboard_df[leaderboard_df["username"] == username]
                if not user_submissions.empty:
                    best_score = user_submissions["accuracy"].max()

                # Individual rank
                user_bests = leaderboard_df.groupby("username")["accuracy"].max()
                summary_df = user_bests.reset_index()
                summary_df.columns = ["Engineer", "Best_Score"]
                summary_df = summary_df.sort_values("Best_Score", ascending=False).reset_index(drop=True)
                summary_df.index = summary_df.index + 1
                my_row = summary_df[summary_df["Engineer"] == username]
                if not my_row.empty:
                    rank = my_row.index[0]

                # Team rank
                if "Team" in leaderboard_df.columns and team_name:
                    team_summary_df = (
                        leaderboard_df.groupby("Team")["accuracy"]
                        .agg(Best_Score="max")
                        .reset_index()
                        .sort_values("Best_Score", ascending=False)
                        .reset_index(drop=True)
                    )
                    team_summary_df.index = team_summary_df.index + 1
                    my_team_row = team_summary_df[team_summary_df["Team"] == team_name]
                    if not my_team_row.empty:
                        team_rank = my_team_row.index[0]
    except Exception as e:
        _log(f"User stats error for {username}: {e}")

    stats = {
        "username": username,
        "best_score": best_score,
        "rank": rank,
        "team_name": team_name,
        "team_rank": team_rank,
        "is_signed_in": True,
        "_ts": now
    }
    _user_stats_cache[username] = stats
    return stats

# ---------------------------------------------------------------------------
# HTML Helpers (I18N)
# ---------------------------------------------------------------------------

def t(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

def build_stats_html(user_stats: Dict[str, Any], lang="en") -> str:
    if user_stats.get("best_score") is not None:
        best_score_pct = f"{(user_stats['best_score'] * 100):.1f}%"
        rank_text = f"#{user_stats['rank']}" if user_stats['rank'] else "N/A"
        # UPDATED: Translate team name for display based on selected language
        team_text = translate_team_name_for_display(user_stats['team_name'], lang) if user_stats['team_name'] else "N/A"
        return f"""
        <div class='slide-shell slide-shell--primary'>
            <div style='text-align:center;'>
                <h2 class='slide-shell__title'>
                    {t(lang, 'stats_title')}
                </h2>
                <p class='slide-shell__subtitle'>
                    {t(lang, 'stats_subtitle')}
                </p>

                <div class='content-box'>
                    <h3 class='content-box__heading'>{t(lang, 'stats_heading')}</h3>

                    <div class='stat-grid'>
                        <div class='stat-card'>
                            <p class='stat-card__label'>{t(lang, 'lbl_accuracy')}</p>
                            <p class='stat-card__value'>
                                {best_score_pct}
                            </p>
                        </div>

                        <div class='stat-card'>
                            <p class='stat-card__label'>{t(lang, 'lbl_rank')}</p>
                            <p class='stat-card__value'>
                                {rank_text}
                            </p>
                        </div>
                    </div>

                    <div class='team-card'>
                        <p class='team-card__label'>{t(lang, 'lbl_team')}</p>
                        <p class='team-card__value'>
                            🛡️ {team_text}
                        </p>
                    </div>
                </div>

                <p class='slide-shell__subtitle' style='font-weight:500;'>
                    {t(lang, 'stats_footer')}
                </p>
            </div>
        </div>
        """
    else:
        # Authenticated but no submission
        return f"""
        <div class='slide-shell slide-shell--primary'>
            <div style='text-align:center;'>
                <h2 class='slide-shell__title'>
                    {t(lang, 'guest_title')}
                </h2>
                <p class='slide-shell__subtitle'>
                    {t(lang, 'guest_subtitle')}
                </p>

                <div class='content-box'>
                    <p style='margin:0;'>
                        {t(lang, 'guest_body')}
                    </p>
                </div>

                <p class='slide-shell__subtitle' style='font-weight:500;'>
                    {t(lang, 'guest_footer')}
                </p>
            </div>
        </div>
        """

def _get_step2_html(lang):
    return f"""
    <div class='slide-shell slide-shell--warning'>
        <p class='large-text' style='text-align:center; font-weight:600; margin:0;'>
            {t(lang, 's2_intro')}
        </p>

        <div class='content-box'>
            <h3 class='content-box__heading'>{t(lang, 's2_box_title')}</h3>
            <p class='slide-warning-body'>
                {t(lang, 's2_p1')}
            </p>
            <p class='slide-warning-body' style='margin-top:16px;'>
                {t(lang, 's2_p2')}
            </p>
            <p class='slide-warning-body' style='margin-top:16px; font-weight:600;'>
                {t(lang, 's2_p3')}
            </p>
        </div>
    </div>
    """

def _get_step3_html(lang):
    return f"""
    <div class='revelation-box'>
        <h3 style='margin-top:0; font-size:1.8rem;'>
            {t(lang, 's3_head')}
        </h3>
        <p style='font-size:1.1rem; line-height:1.6;'>
            {t(lang, 's3_p1')}
        </p>
        <div class='content-box content-box--emphasis'>
            <h4 class='content-box__heading'>{t(lang, 's3_box_title')}</h4>
            <div class='bg-danger-soft' style='margin:20px 0;'>
                <p class='emph-danger' style='font-size:1.15rem; margin:0;'>
                    {t(lang, 's3_alert')}
                </p>
            </div>
            <p style='font-size:1.05rem; margin-top:20px;'>
                {t(lang, 's3_spec')}
            </p>
            <ul style='font-size:1.05rem; line-height:1.8;'>
                <li>
                    {t(lang, 's3_li1_pre')}
                    <span class='emph-danger'> 45%</span>
                </li>
                <li>
                    {t(lang, 's3_li2_pre')}
                </li>
                <li style='margin-top:12px;'>
                    {t(lang, 's3_li3')}
                </li>
            </ul>
        </div>

        <div class='content-box content-box--emphasis'>
            <h4 class='content-box__heading'>{t(lang, 's3_box2_title')}</h4>
            <p style='font-size:1.05rem; margin:0; line-height:1.6;'>
                {t(lang, 's3_mean_p1')}
            </p>
            <p style='font-size:1.05rem; margin-top:12px; line-height:1.6;'>
                {t(lang, 's3_mean_p2')}
            </p>
        </div>
    </div>
    """

def _get_step4_eu_html(lang):
    return f"""
    <div class='eu-panel'>
        <h3 class='emph-eu' style='font-size:1.9rem; text-align:center;'>
            {t(lang, 's4eu_head')}
        </h3>
        <p style='line-height:1.8;'>
            {t(lang, 's4eu_intro')}
        </p>
        <ul style='line-height:1.9; font-size:1.05rem; margin:20px 0;'>
            <li>
                <strong class='emph-eu'>{t(lang, 's4eu_li1_title')}</strong><br>
                {t(lang, 's4eu_li1_body')}
            </li>
            <li style='margin-top:14px;'>
                <strong class='emph-eu'>{t(lang, 's4eu_li2_title')}</strong><br>
                {t(lang, 's4eu_li2_body')}
            </li>
            <li style='margin-top:14px;'>
                <strong class='emph-eu'>{t(lang, 's4eu_li3_title')}</strong><br>
                {t(lang, 's4eu_li3_body')}
            </li>
        </ul>
        <div class='bg-eu-soft eu-panel__highlight'>
            <h4 class='emph-eu'>{t(lang, 's4eu_box_title')}</h4>
            <p style='margin:0; line-height:1.7; font-size:1.05rem;'>
                {t(lang, 's4eu_box_body')}
            </p>
        </div>
        <div class='eu-panel__note'>
            <p style='margin:0; line-height:1.8; font-size:1.1rem;'>
                {t(lang, 's4eu_note')}
            </p>
        </div>
    </div>
    """

def _get_step4_lesson_html(lang):
    return f"""
    <div class='content-box'>
        <h4 class='content-box__heading emph-key' style='font-size:1.5rem;'>
            {t(lang, 's4_box_title')}
        </h4>
        <div class='lesson-emphasis-box'>
            <span class='lesson-item-title'>
                <span class='lesson-badge'>1</span>
                {t(lang, 's4_li1_title')}
            </span>
            <p class='slide-teaching-body'>
                {t(lang, 's4_li1_body')}
            </p>
        </div>
        <div class='lesson-emphasis-box'>
            <span class='lesson-item-title'>
                <span class='lesson-badge'>2</span>
                {t(lang, 's4_li2_title')}
            </span>
            <p class='slide-teaching-body'>
                {t(lang, 's4_li2_body')}
            </p>
        </div>
        <div class='lesson-emphasis-box'>
            <span class='lesson-item-title'>
                <span class='lesson-badge'>3</span>
                {t(lang, 's4_li3_title')}
            </span>
            <p class='slide-teaching-body'>
                {t(lang, 's4_li3_body')}
            </p>
        </div>
    </div>
    """

def _get_step5_html(lang):
    return f"""
    <div style='text-align:center;'>
        <div class='slide-shell slide-shell--info'>
            <h3 class='slide-shell__title'>
                {t(lang, 's5_head')}
            </h3>
            <p style='line-height:1.8; text-align:left;'>
                {t(lang, 's5_intro')}
            </p>
            <ul style='text-align:left; line-height:2; font-size:1.1rem; margin:24px 0;'>
                <li>{t(lang, 's5_li1')}</li>
                <li>{t(lang, 's5_li2')}</li>
                <li>{t(lang, 's5_li3')}</li>
            </ul>
            <div class='content-box'>
                <h4 class='content-box__heading'>{t(lang, 's5_box_title')}</h4>
                <p style='font-size:1.1rem; line-height:1.8;'>
                    {t(lang, 's5_p1')}
                </p>
                <p style='font-size:1.1rem; line-height:1.8; margin-top:16px;'>
                    {t(lang, 's5_p2')}
                </p>
            </div>
            <div class='content-box content-box--emphasis'>
                <p style='font-size:1.15rem; font-weight:600; margin:0;'>
                    {t(lang, 's5_mission')}
                </p>
            </div>
            <h1 style='margin:32px 0 16px 0; font-size: 3rem;'>{t(lang, 's5_scroll')}</h1>
            <p style='font-size:1.2rem;'>{t(lang, 's5_continue')}</p>
        </div>
    </div>
    """

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = """
.large-text { font-size: 20px !important; }
.slide-shell, .celebration-box {
  padding:24px; border-radius:16px;
  background-color: var(--block-background-fill);
  color: var(--body-text-color);
  border:2px solid var(--border-color-primary);
  max-width:900px; margin:auto;
}
.slide-shell--primary, .slide-shell--warning, .slide-shell--info { border-color: var(--color-accent); }
.slide-shell__title { font-size:2.3rem; margin:0; text-align:center; }
.slide-shell__subtitle { font-size:1.2rem; margin-top:16px; text-align:center; color: var(--secondary-text-color); }
.stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; }
.stat-card, .team-card { text-align:center; padding:16px; border-radius:8px; border:1px solid var(--border-color-primary); background-color: var(--block-background-fill); }
.stat-card__label, .team-card__label { margin:0; font-size:0.9rem; color: var(--secondary-text-color); }
.stat-card__value { margin:4px 0 0 0; font-size:1.8rem; font-weight:700; }
.team-card__value { margin:4px 0 0 0; font-size:1.3rem; font-weight:600; }
.content-box { background-color: var(--block-background-fill); border-radius:12px; border:1px solid var(--border-color-primary); padding:24px; margin:24px 0; }
.content-box--emphasis { border-left:6px solid var(--color-accent); }
.revelation-box { background-color: var(--block-background-fill); border-left:6px solid var(--color-accent); border-radius:8px; padding:24px; margin-top:24px; }
.eu-panel { font-size:20px; padding:32px; border-radius:16px; border:3px solid var(--border-color-primary); background-color: var(--block-background-fill); max-width:900px; margin:auto; }
.bg-danger-soft { background-color:#fee2e2; border-left:6px solid #dc2626; padding:16px; border-radius:8px; }
.emph-danger { color:#b91c1c; font-weight:700; }
.emph-key { color: var(--color-accent); font-weight:700; }
.lesson-emphasis-box { background-color: var(--block-background-fill); border-left:6px solid var(--color-accent); padding:18px 20px; border-radius:10px; margin-top:1.5rem; }
.lesson-item-title { font-size:1.35em; font-weight:700; margin-bottom:0.25rem; display:block; }
.lesson-badge { display:inline-block; background-color: var(--color-accent); color: var(--button-text-color); padding:6px 12px; border-radius:10px; font-weight:700; margin-right:10px; font-size:0.9em; }
.slide-warning-body, .slide-teaching-body { font-size:1.25em; line-height:1.75; }
#nav-loading-overlay { position:fixed; top:0; left:0; width:100%; height:100%; background-color: var(--body-background-fill); z-index:9999; display:none; flex-direction:column; align-items:center; justify-content:center; opacity:0; transition:opacity .3s ease; }
.nav-spinner { width:50px; height:50px; border:5px solid var(--block-background-fill); border-top:5px solid var(--color-accent); border-radius:50%; animation: nav-spin 1s linear infinite; margin-bottom:20px; }
@keyframes nav-spin { 0%{transform:rotate(0deg);} 100%{transform:rotate(360deg);} }
/* EU Panel Highlighting */
.bg-eu-soft { background-color: color-mix(in srgb, var(--color-accent) 15%, transparent); border-radius: 8px; padding: 16px; margin: 20px 0; }
.emph-eu { color: var(--color-accent); font-weight: 700; }
.emph-harm { color: #b91c1c; font-weight: 700; }
@media (prefers-color-scheme: dark) {
    .bg-danger-soft { background-color: #450a0a; border-color: #dc2626; }
    .emph-danger { color: #f87171; }
    .emph-harm { color: #f87171; }
}
"""

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def create_ethical_revelation_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=CSS) as demo:
        gr.HTML("<div id='app_top_anchor' style='height:0;'></div>")
        gr.HTML("""
            <div id='nav-loading-overlay'>
                <div class='nav-spinner'></div>
                <span id='nav-loading-text'>Loading...</span>
            </div>
        """)
        
        # Components needing dynamic updates
        c_title = gr.Markdown("<h1 style='text-align:center;'>🚀 The Ethical Revelation: Real-World Impact</h1>")

        # Loading placeholder
        with gr.Column(visible=True, elem_id="initial-loading") as initial_loading:
            c_loading_text = gr.Markdown("<div style='text-align:center; padding:80px 0;'><h2>⏳ Loading...</h2></div>")

        # Steps
        with gr.Column(visible=False, elem_id="step-1") as step_1:
            stats_display = gr.HTML() # Content built dynamically
            deploy_button = gr.Button(t('en', 'btn_deploy'), variant="primary", size="lg", scale=1)

        with gr.Column(visible=False, elem_id="step-2") as step_2:
            c_s2_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's2_title')}</h2>")
            c_s2_html = gr.HTML(_get_step2_html("en"))
            with gr.Row():
                step_2_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_2_next = gr.Button(t('en', 'btn_reveal'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-3") as step_3:
            c_s3_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's3_title')}</h2>")
            c_s3_html = gr.HTML(_get_step3_html("en"))
            with gr.Row():
                step_3_back = gr.Button(t('en', 'btn_back'), size="lg")
                step_3_next = gr.Button(t('en', 'btn_eu'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-4-eu") as step_4_eu:
            c_s4eu_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's4eu_title')}</h2>")
            c_s4eu_html = gr.HTML(_get_step4_eu_html("en"))
            with gr.Row():
                step_4_eu_back = gr.Button(t('en', 'btn_back_invest'), size="lg")
                step_4_eu_next = gr.Button(t('en', 'btn_zoom'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-4") as step_4:
            c_s4_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's4_title')}</h2>")
            c_s4_html = gr.HTML(_get_step4_lesson_html("en"))
            with gr.Row():
                step_4_back = gr.Button(t('en', 'btn_back_eu'), size="lg")
                step_4_next = gr.Button(t('en', 'btn_what_do'), variant="primary", size="lg")

        with gr.Column(visible=False, elem_id="step-5") as step_5:
            c_s5_title = gr.Markdown(f"<h2 style='text-align:center;'>{t('en', 's5_title')}</h2>")
            c_s5_html = gr.HTML(_get_step5_html("en"))
            back_to_lesson_btn = gr.Button(t('en', 'btn_review'), size="lg")

        loading_screen = gr.Column(visible=False)
        all_steps = [step_1, step_2, step_3, step_4_eu, step_4, step_5, loading_screen, initial_loading]

        # --- Initial Load with Language & Auth ---
        def initial_load(request: gr.Request):
            params = request.query_params
            lang = params.get("lang", "en")
            if lang not in TRANSLATIONS: lang = "en"
            
            # Try auth
            success, username, token = _try_session_based_auth(request)
            
            # Build Stats HTML (Translating inside)
            stats_html = ""
            if success and username:
                stats = _compute_user_stats(username, token)
                stats_html = build_stats_html(stats, lang)
            else:
                stats_html = f"""
                <div class='slide-shell slide-shell--primary' style='text-align:center;'>
                    <h2 class='slide-shell__title'>{t(lang, 'loading_session')}</h2>
                </div>
                """
            
            # Return all UI updates
            return [
                gr.update(visible=False), # initial_loading
                gr.update(visible=True),  # step_1
                gr.update(value=stats_html), # stats_display
                # Title
                f"<h1 style='text-align:center;'>{t(lang, 'title')}</h1>",
                # Loading Text
                f"<div style='text-align:center; padding:80px 0;'><h2>{t(lang, 'loading_personal')}</h2></div>",
                # Step 1 Button
                gr.Button(value=t(lang, 'btn_deploy')),
                # Step 2
                f"<h2 style='text-align:center;'>{t(lang, 's2_title')}</h2>",
                _get_step2_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_reveal')),
                # Step 3
                f"<h2 style='text-align:center;'>{t(lang, 's3_title')}</h2>",
                _get_step3_html(lang),
                gr.Button(value=t(lang, 'btn_back')),
                gr.Button(value=t(lang, 'btn_eu')),
                # Step 4 EU
                f"<h2 style='text-align:center;'>{t(lang, 's4eu_title')}</h2>",
                _get_step4_eu_html(lang),
                gr.Button(value=t(lang, 'btn_back_invest')),
                gr.Button(value=t(lang, 'btn_zoom')),
                # Step 4 Lesson
                f"<h2 style='text-align:center;'>{t(lang, 's4_title')}</h2>",
                _get_step4_lesson_html(lang),
                gr.Button(value=t(lang, 'btn_back_eu')),
                gr.Button(value=t(lang, 'btn_what_do')),
                # Step 5
                f"<h2 style='text-align:center;'>{t(lang, 's5_title')}</h2>",
                _get_step5_html(lang),
                gr.Button(value=t(lang, 'btn_review'))
            ]

        # Load trigger
        update_targets = [
            initial_loading, step_1, stats_display, c_title, c_loading_text,
            deploy_button,
            c_s2_title, c_s2_html, step_2_back, step_2_next,
            c_s3_title, c_s3_html, step_3_back, step_3_next,
            c_s4eu_title, c_s4eu_html, step_4_eu_back, step_4_eu_next,
            c_s4_title, c_s4_html, step_4_back, step_4_next,
            c_s5_title, c_s5_html, back_to_lesson_btn
        ]
        demo.load(fn=initial_load, inputs=None, outputs=update_targets)

        # --- Navigation Logic ---
        def create_nav_generator(current_step, next_step):
            def navigate():
                updates = {loading_screen: gr.update(visible=True)}
                for s in all_steps:
                    if s != loading_screen: updates[s] = gr.update(visible=False)
                yield updates
                updates = {next_step: gr.update(visible=True)}
                for s in all_steps:
                    if s != next_step: updates[s] = gr.update(visible=False)
                yield updates
            return navigate

        def nav_js(target_id: str, message: str, min_show_ms: int = 900) -> str:
            return f"""
            ()=>{{
              try {{
                const overlay=document.getElementById('nav-loading-overlay');
                const msg=document.getElementById('nav-loading-text');
                if(overlay && msg){{ msg.textContent='{message}'; overlay.style.display='flex'; setTimeout(()=>overlay.style.opacity='1',10); }}
                const start=Date.now();
                setTimeout(()=>{{ window.scrollTo({{top:0, behavior:'smooth'}}); }},40);
                const poll=setInterval(()=>{{
                  const elapsed=Date.now()-start;
                  const target=document.getElementById('{target_id}');
                  const visible=target && target.offsetParent!==null;
                  if((visible && elapsed>={min_show_ms}) || elapsed>6000){{
                    clearInterval(poll);
                    if(overlay){{ overlay.style.opacity='0'; setTimeout(()=>overlay.style.display='none',320); }}
                  }}
                }},100);
              }} catch(e){{}}
            }}
            """

        deploy_button.click(fn=create_nav_generator(step_1, step_2), inputs=None, outputs=all_steps, js=nav_js("step-2", "Sharing model..."))
        step_2_back.click(fn=create_nav_generator(step_2, step_1), inputs=None, outputs=all_steps, js=nav_js("step-1", "Returning..."))
        step_2_next.click(fn=create_nav_generator(step_2, step_3), inputs=None, outputs=all_steps, js=nav_js("step-3", "Loading investigation..."))
        step_3_back.click(fn=create_nav_generator(step_3, step_2), inputs=None, outputs=all_steps, js=nav_js("step-2", "Going back..."))
        step_3_next.click(fn=create_nav_generator(step_3, step_4_eu), inputs=None, outputs=all_steps, js=nav_js("step-4-eu", "Exploring European context..."))
        step_4_eu_back.click(fn=create_nav_generator(step_4_eu, step_3), inputs=None, outputs=all_steps, js=nav_js("step-3", "Reviewing findings..."))
        step_4_eu_next.click(fn=create_nav_generator(step_4_eu, step_4), inputs=None, outputs=all_steps, js=nav_js("step-4", "Zooming out..."))
        step_4_back.click(fn=create_nav_generator(step_4, step_4_eu), inputs=None, outputs=all_steps, js=nav_js("step-4-eu", "European context..."))
        step_4_next.click(fn=create_nav_generator(step_4, step_5), inputs=None, outputs=all_steps, js=nav_js("step-5", "Exploring solutions..."))
        back_to_lesson_btn.click(fn=create_nav_generator(step_5, step_4), inputs=None, outputs=all_steps, js=nav_js("step-4", "Reviewing lesson..."))

    return demo

def launch_ethical_revelation_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    demo = create_ethical_revelation_app()
    port = int(os.environ.get("PORT", 8080))
    demo.launch(share=share, inline=True, debug=debug, height=height, server_port=port)


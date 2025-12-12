"""
Translation dictionaries for Bias Detective Part 2
Supports English (en), Spanish (es), and Catalan (ca)
"""

TRANSLATIONS = {
    "en": {
        # App metadata
        "app_title": "🕵️‍♀️ Bias Detective: Part 2 - The Algorithmic Audit",
        "loading_auth": "🕵️‍♀️ Authenticating...",
        "loading_sync": "Syncing Moral Compass Data...",
        "loading": "Loading...",
        "auth_failed": "⚠️ Auth Failed. Please launch from the course link.",
        
        # Module titles
        "mod0_title": "Part 2 Intro",
        "mod1_title": "Why outputs matter",
        "mod2_title": "HOW WE KNOW WHEN AI IS WRONG",
        
        # Module 0: Part 2 Intro
        "mod0_heading": "🕵️‍♀️ PART 2: THE ALGORITHMIC AUDIT",
        "mod0_status_badge": "⚡ STATUS: DATA FORENSICS COMPLETE",
        "mod0_roadmap_title": "🗺️ Your Investigation Roadmap",
        "mod0_step1": "1. Learn the Rules",
        "mod0_step1_status": "✔ Completed",
        "mod0_step2": "2. Collect Evidence",
        "mod0_step2_status": "✔ Completed",
        "mod0_step3": "3. Prove the Prediction Error",
        "mod0_step3_status": "⬅ You are here",
        "mod0_step4": "4. Diagnose Harm",
        "mod0_step4_status": "Coming Soon",
        "mod0_p1": "Welcome back, Detective. In Part 1, you uncovered powerful evidence: the <strong>input data</strong> feeding this model was distorted by history and unequal sampling.",
        "mod0_p2": "But corrupted data is only <em>half</em> the case. Now comes the decisive moment in any AI audit: testing whether these distorted inputs have produced <strong>unfair outputs</strong> — unequal predictions that change real lives.",
        "mod0_p3": "In Part 2, you will compare the model's predictions against reality, group by group. This is where you expose <strong>false positives</strong>, <strong>false negatives</strong>, and the hidden <strong>error gaps</strong> that reveal whether the system is treating people unfairly.",
        
        # Module 1: Why outputs matter
        "mod1_heading": "🎯 WHY OUTPUTS MATTER",
        "mod1_badge": "🎛️ FOCUS: MODEL OUTPUTS",
        "mod1_p1": "In Part 1, you uncovered distortions in the <strong>input data</strong>. But biased data doesn't automatically prove the model's <em>decisions</em> are unfair.",
        "mod1_p2": "To protect people — and society — we must test the <strong>outputs</strong>. When an AI model makes a prediction, that prediction can directly shape someone's future.",
        "mod1_consequences_title": "🔎 Why Outputs Shape Justice",
        "mod1_consequences_desc": "A model's prediction doesn't just describe risk — it can <strong>change real decisions</strong>.",
        "mod1_high_risk": "<strong>High risk score →</strong> denied bail, longer detention, fewer opportunities.",
        "mod1_low_risk": "<strong>Low risk score →</strong> early release, access to programs, second chances.",
        "mod1_mistakes": "And mistakes go both ways:",
        "mod1_false_alarms": "<strong>False alarms</strong> keep low-risk people locked up — harming families and communities.",
        "mod1_missed_warnings": "<strong>Missed warnings</strong> can release someone who may commit another crime — harming public safety.",
        
        # Navigation buttons
        "btn_next": "Next",
        "btn_prev": "Previous",
        "btn_previous": "⬅️ Previous",
        "btn_next_arrow": "Next ▶️",
        "btn_complete_part2": "🎉 Complete Part 2 (Please Scroll Down)",
        "btn_back_top": "Back to Top",
        
        # Leaderboard
        "leaderboard_title": "Leaderboard",
        "leaderboard_rank": "Rank",
        "leaderboard_score": "Score",
        "leaderboard_team": "Team",
        "leaderboard_username": "Username",
    },
    "es": {
        # App metadata
        "app_title": "🕵️‍♀️ Detective de Sesgos: Parte 2 - La Auditoría Algorítmica",
        "loading_auth": "🕵️‍♀️ Autenticando...",
        "loading_sync": "Sincronizando Datos de la Brújula Moral...",
        "loading": "Cargando...",
        "auth_failed": "⚠️ Autenticación Fallida. Por favor, inicia desde el enlace del curso.",
        
        # Module titles
        "mod0_title": "Introducción Parte 2",
        "mod1_title": "Por qué importan las salidas",
        "mod2_title": "CÓMO SABEMOS CUANDO LA IA SE EQUIVOCA",
        
        # Module 0: Part 2 Intro
        "mod0_heading": "🕵️‍♀️ PARTE 2: LA AUDITORÍA ALGORÍTMICA",
        "mod0_status_badge": "⚡ ESTADO: ANÁLISIS FORENSE DE DATOS COMPLETADO",
        "mod0_roadmap_title": "🗺️ Tu Hoja de Ruta de Investigación",
        "mod0_step1": "1. Aprende las Reglas",
        "mod0_step1_status": "✔ Completado",
        "mod0_step2": "2. Recopila Evidencia",
        "mod0_step2_status": "✔ Completado",
        "mod0_step3": "3. Prueba el Error de Predicción",
        "mod0_step3_status": "⬅ Estás aquí",
        "mod0_step4": "4. Diagnostica el Daño",
        "mod0_step4_status": "Próximamente",
        "mod0_p1": "Bienvenido de nuevo, Detective. En la Parte 1, descubriste evidencia poderosa: los <strong>datos de entrada</strong> que alimentan este modelo estaban distorsionados por la historia y el muestreo desigual.",
        "mod0_p2": "Pero los datos corruptos son solo <em>la mitad</em> del caso. Ahora llega el momento decisivo en cualquier auditoría de IA: probar si estas entradas distorsionadas han producido <strong>salidas injustas</strong> — predicciones desiguales que cambian vidas reales.",
        "mod0_p3": "En la Parte 2, compararás las predicciones del modelo con la realidad, grupo por grupo. Aquí es donde expones <strong>falsos positivos</strong>, <strong>falsos negativos</strong> y las <strong>brechas de error</strong> ocultas que revelan si el sistema está tratando a las personas injustamente.",
        
        # Module 1: Why outputs matter
        "mod1_heading": "🎯 POR QUÉ IMPORTAN LAS SALIDAS",
        "mod1_badge": "🎛️ ENFOQUE: SALIDAS DEL MODELO",
        "mod1_p1": "En la Parte 1, descubriste distorsiones en los <strong>datos de entrada</strong>. Pero los datos sesgados no prueban automáticamente que las <em>decisiones</em> del modelo sean injustas.",
        "mod1_p2": "Para proteger a las personas, y a la sociedad, debemos probar las <strong>salidas</strong>. Cuando un modelo de IA hace una predicción, esa predicción puede dar forma directamente al futuro de alguien.",
        "mod1_consequences_title": "🔎 Por Qué las Salidas Dan Forma a la Justicia",
        "mod1_consequences_desc": "La predicción de un modelo no solo describe el riesgo: puede <strong>cambiar decisiones reales</strong>.",
        "mod1_high_risk": "<strong>Puntuación de alto riesgo →</strong> fianza denegada, detención más larga, menos oportunidades.",
        "mod1_low_risk": "<strong>Puntuación de bajo riesgo →</strong> liberación anticipada, acceso a programas, segundas oportunidades.",
        "mod1_mistakes": "Y los errores van en ambos sentidos:",
        "mod1_false_alarms": "<strong>Falsas alarmas</strong> mantienen encerradas a personas de bajo riesgo, perjudicando a familias y comunidades.",
        "mod1_missed_warnings": "<strong>Advertencias perdidas</strong> pueden liberar a alguien que puede cometer otro crimen, perjudicando la seguridad pública.",
        
        # Navigation buttons
        "btn_next": "Siguiente",
        "btn_prev": "Anterior",
        "btn_previous": "⬅️ Anterior",
        "btn_next_arrow": "Siguiente ▶️",
        "btn_complete_part2": "🎉 Completar Parte 2 (Por favor desplázate hacia abajo)",
        "btn_back_top": "Volver Arriba",
        
        # Leaderboard
        "leaderboard_title": "Tabla de Clasificación",
        "leaderboard_rank": "Rango",
        "leaderboard_score": "Puntuación",
        "leaderboard_team": "Equipo",
        "leaderboard_username": "Nombre de Usuario",
    },
    "ca": {
        # App metadata
        "app_title": "🕵️‍♀️ Detectiu de Biaixos: Part 2 - L'Auditoria Algorítmica",
        "loading_auth": "🕵️‍♀️ Autenticant...",
        "loading_sync": "Sincronitzant Dades de la Brúixola Moral...",
        "loading": "Carregant...",
        "auth_failed": "⚠️ Autenticació Fallida. Si us plau, inicia des de l'enllaç del curs.",
        
        # Module titles
        "mod0_title": "Introducció Part 2",
        "mod1_title": "Per què importen les sortides",
        "mod2_title": "COM SABEM QUAN LA IA S'EQUIVOCA",
        
        # Module 0: Part 2 Intro
        "mod0_heading": "🕵️‍♀️ PART 2: L'AUDITORIA ALGORÍTMICA",
        "mod0_status_badge": "⚡ ESTAT: ANÀLISI FORENSE DE DADES COMPLETAT",
        "mod0_roadmap_title": "🗺️ El Teu Full de Ruta d'Investigació",
        "mod0_step1": "1. Aprèn les Regles",
        "mod0_step1_status": "✔ Completat",
        "mod0_step2": "2. Recopila Evidència",
        "mod0_step2_status": "✔ Completat",
        "mod0_step3": "3. Prova l'Error de Predicció",
        "mod0_step3_status": "⬅ Estàs aquí",
        "mod0_step4": "4. Diagnostica el Dany",
        "mod0_step4_status": "Properament",
        "mod0_p1": "Benvingut de nou, Detectiu. A la Part 1, vas descobrir evidència poderosa: les <strong>dades d'entrada</strong> que alimenten aquest model estaven distorsionades per la història i el mostreig desigual.",
        "mod0_p2": "Però les dades corruptes són només <em>la meitat</em> del cas. Ara arriba el moment decisiu en qualsevol auditoria d'IA: provar si aquestes entrades distorsionades han produït <strong>sortides injustes</strong> — prediccions desiguals que canvien vides reals.",
        "mod0_p3": "A la Part 2, compararàs les prediccions del model amb la realitat, grup per grup. Aquí és on exposes <strong>falsos positius</strong>, <strong>falsos negatius</strong> i les <strong>bretxes d'error</strong> ocultes que revelen si el sistema està tractant les persones injustament.",
        
        # Module 1: Why outputs matter
        "mod1_heading": "🎯 PER QUÈ IMPORTEN LES SORTIDES",
        "mod1_badge": "🎛️ ENFOCAMENT: SORTIDES DEL MODEL",
        "mod1_p1": "A la Part 1, vas descobrir distorsions a les <strong>dades d'entrada</strong>. Però les dades esbiaixades no proven automàticament que les <em>decisions</em> del model siguin injustes.",
        "mod1_p2": "Per protegir les persones, i la societat, hem de provar les <strong>sortides</strong>. Quan un model d'IA fa una predicció, aquesta predicció pot donar forma directament al futur d'algú.",
        "mod1_consequences_title": "🔎 Per Què les Sortides Donen Forma a la Justícia",
        "mod1_consequences_desc": "La predicció d'un model no només descriu el risc: pot <strong>canviar decisions reals</strong>.",
        "mod1_high_risk": "<strong>Puntuació d'alt risc →</strong> fiança denegada, detenció més llarga, menys oportunitats.",
        "mod1_low_risk": "<strong>Puntuació de baix risc →</strong> alliberament anticipat, accés a programes, segones oportunitats.",
        "mod1_mistakes": "I els errors van en ambdós sentits:",
        "mod1_false_alarms": "<strong>Falses alarmes</strong> mantenen tancades persones de baix risc, perjudicant famílies i comunitats.",
        "mod1_missed_warnings": "<strong>Advertències perdudes</strong> poden alliberar algú que pot cometre un altre crim, perjudicant la seguretat pública.",
        
        # Navigation buttons
        "btn_next": "Següent",
        "btn_prev": "Anterior",
        "btn_previous": "⬅️ Anterior",
        "btn_next_arrow": "Següent ▶️",
        "btn_complete_part2": "🎉 Completar Part 2 (Si us plau desplaça't cap avall)",
        "btn_back_top": "Tornar a Dalt",
        
        # Leaderboard
        "leaderboard_title": "Taula de Classificació",
        "leaderboard_rank": "Rang",
        "leaderboard_score": "Puntuació",
        "leaderboard_team": "Equip",
        "leaderboard_username": "Nom d'Usuari",
    }
}

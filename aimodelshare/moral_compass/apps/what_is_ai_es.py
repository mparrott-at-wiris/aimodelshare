"""
Qué es la IA - Aplicación Gradio para el Reto de Justicia y Equidad (versión española).

Esta aplicación enseña:
1. Una explicació simple i no tècnica del que és l'IA
2. Com funcionen els models predictius (Entrada → Model → Sortida)
3. Ejemplos del mundo real i connexions amb el repte de justicia

Estructura:
- Función factory `create_what_is_ai_app()` devuelve un objeto Gradio Blocks
- Envolvente de conveniencia `launch_what_is_ai_app()` lo lanza inline (para notebooks)
"""
import contextlib
import os

def _create_simple_predictor():
    """Crear un predictor de demostración simple con finalidades didácticas."""
    def predict_outcome(age, priors, severity):
        """Predictor simple basado en reglas para demostración."""
        
        
        # Lógica simple de puntuación para demostración
        score = 0
        
        # Factor de edad (más joven = mayor riesgo en este modelo simple)
        if age < 25:
            score += 3
        elif age < 35:
            score += 2
        else:
            score += 1
        
        # Factor de delitos anteriores
        if priors >= 3:
            score += 3
        elif priors >= 1:
            score += 2
        else:
            score += 0
        
        # Factor de gravedad
        severity_map = {"Menor": 1, "Moderado": 2, "Grave": 3}
        score += severity_map.get(severity, 2)
        
        # Determinar nivel de riesgo
        if score >= 7:
            risk = "Riesgo Alto"
            color = "#dc2626"
            emoji = "🔴"
        elif score >= 4:
            risk = "Riesgo Medio"
            color = "#f59e0b"
            emoji = "🟡"
        else:
            risk = "Riesgo Bajo"
            color = "#16a34a"
            emoji = "🟢"
        
        return f"""
        <div style='background:white; padding:24px; border-radius:12px; border:3px solid {color}; text-align:center;'>
            <h2 style='color:{color}; margin:0; font-size:2.5rem;'>{emoji} {risk}</h2>
            <p style='font-size:18px; color:#6b7280; margin-top:12px;'>Puntuación de riesgo: {score}/9</p>
        </div>
        """
    
    return predict_outcome


def create_what_is_ai_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Crear l'aplicació Gradio Blocks Qué es la IA (encara no llançada)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)

    except ImportError as e:
        raise ImportError(
            "Gradio es necesario para la aplicación qué es la IA. Instálalo con `pip install gradio`."
        ) from e
    
    predict_outcome = _create_simple_predictor()
    
    css = """
    .large-text {
        font-size: 20px !important;
    }
    """
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("<h1 style='text-align:center;'>🤖 Qué es la IA, entonces?</h1>")
        gr.HTML(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #e0e7ff; border-radius: 12px; border: 2px solid #6366f1;'>
            Antes de poder construir mejores sistemas de IA, necesitas entender qué es realmente la IA.<br>
            No te preocupes - lo explicaremos en términos simples y cotidianos!
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")
        
        # --- Esta es la nueva pantalla de carga ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Cargando...</h2>
                </div>
                """
            )
        
        # Pas 1: Introducció
        with gr.Column(visible=True) as step_1:
            gr.Markdown("<h2 style='text-align:center;'>🎯 Una definición simple</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#dbeafe; padding:28px; border-radius:16px;'>
                <p><b style='font-size:24px;'>Inteligencia Artificial (IA) es solo un nombre sofisticado para:</b></p>
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0; border:3px solid #0284c7;'>
                    <h2 style='text-align:center; color:#0284c7; margin:0; font-size:2rem;'>
                    Un sistema que hace predicciones basadas en patrones
                    </h2>
                </div>
                <p>¡Eso es todo! Desglosemos qué significa esto...</p>
                <h3 style='color:#0369a1; margin-top:24px;'>Piensa en cómo TÚ haces predicciones:</h3>
                <ul style='font-size:19px; margin-top:12px;'>
                    <li><b>Tiempo:</b> Nubes oscuras → Predices lluvia → Llevas paraguas</li>
                    <li><b>Tráfico:</b> Hora punta → Predices congestión → Sales temprano</li>
                    <li><b>Películas:</b> Actor que te gusta → Predices que disfrutarás → La ves</li>
                </ul>
                <div style='background:#fef3c7; padding:20px; border-radius:8px; margin-top:24px; border-left:6px solid #f59e0b;'>
                    <p style='font-size:18px; margin:0;'><b>L'IA fa el mateix, però utilitzant dades i matemàtiques 
                    en lloc d'experiència i intuïció humana.</b></p>
                </div>
                </div>
                """
            )
            step_1_next = gr.Button("Siguiente: La fórmula de l'IA ▶️", variant="primary", size="lg")
        
        # Pas 2: La fórmula de tres partes
        with gr.Column(visible=False) as step_2:
            gr.Markdown("<h2 style='text-align:center;'>📐 La fórmula de tres partes</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#f0fdf4; padding:28px; border-radius:16px;'>
                <p>Todos los sistemas de IA funcionan de la misma manera, siguiendo esta fórmula simple:</p>
                <div style='background:white; padding:32px; border-radius:12px; margin:24px 0; text-align:center;'>
                    <div style='display:inline-block; background:#dbeafe; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#0369a1;'>1️⃣ ENTRADA</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>Los datos entran</p>
                    </div>
                    <div style='display:inline-block; font-size:2rem; margin:0 16px; color:#6b7280;'>→</div>
                    <div style='display:inline-block; background:#fef3c7; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#92400e;'>2️⃣ MODELO</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>La IA los procesa</p>
                    </div>
                    <div style='display:inline-block; font-size:2rem; margin:0 16px; color:#6b7280;'>→</div>
                    <div style='display:inline-block; background:#f0fdf4; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#15803d;'>3️⃣ SALIDA</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>La predicción sale</p>
                    </div>
                </div>
                <h3 style='color:#15803d; margin-top:32px;'>Ejemplos del mundo real:</h3>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Entrada:</b> Foto de un perro<br>
                    <b style='color:#92400e;'>Model:</b> IA de reconocimiento de imágenes<br>
                    <b style='color:#15803d;'>Sortida:</b> "Això és un Golden Retriever"
                    </p>
                </div>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Entrada:</b> "Qué tiempo hace?"<br>
                    <b style='color:#92400e;'>Model:</b> IA de lenguaje (com ChatGPT)<br>
                    <b style='color:#15803d;'>Sortida:</b> Una respuesta útil
                    </p>
                </div>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Entrada:</b> Historial criminal de una persona<br>
                    <b style='color:#92400e;'>Model:</b> Algoritmo de evaluación de riesgo<br>
                    <b style='color:#15803d;'>Sortida:</b> "Riesgo Alto" o "Riesgo Bajo"
                    </p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_2_back = gr.Button("◀️ Atrás", size="lg")
                step_2_next = gr.Button("Siguiente: Cómo aprenden los modelos ▶️", variant="primary", size="lg")
        
        # Pas 3: Cómo aprenden los modelos (Versió més curta - Introducció directa)
        with gr.Column(visible=False) as step_3:
            gr.Markdown("<h2 style='text-align:center;'>🧠 Cómo aprende un modelo de IA?</h2>")
            
            gr.HTML(
                """
                <div style='font-size: 19px; background:#fef3c7; padding:28px; border-radius:16px;'>
                
                <h3 style='color:#92400e; margin-top:0;'>1. Aprende de ejemplos</h3>
                
                <p>Un modelo de IA no está programado con respuestas. En cambio, se entrena con un gran número de ejemplos, i aprende a encontrar las respuestas por sí mismo.</p>
                <p>En nuestro escenario de justicia, esto significa alimentar el modelo con miles de casos pasados (<b>exemples</b>) para enseñarle a encontrar los <b>patrons</b> que conectan los detalles de una persona con la probabilidad de reincidencia.</p>
                
                <hr style='margin:24px 0;'>
                
                <h3 style='color:#92400e;'>2. El proceso de entrenamiento</h3>
                <p>L'IA "s'entrena" buclejant a través de dades històriques (casos pasados) millones de veces:</p>
                
                <div style='margin:24px 0; padding:20px; background:#fff; border-radius:8px;'>
                    <div style='display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap;'>
                        <div style='background:#dbeafe; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#0369a1;'>1. ENTRADA<br>EJEMPLOS</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>2. MODELO<br>ADIVINA</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>3. COMPROBAR<br>RESPUESTA</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>4. AJUSTAR<br>PESOS</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#15803d;'>MODELO<br>APRENDIDO</b>
                        </div>
                    </div>
                </div>
                
                <p style='margin-top:20px;'>Durante el paso de"<b>Ajustar</b>", el modelo cambia sus reglas internas (llamadas <b>"pesos"</b>) para acercarse a la respuesta correcta. 
                   Por ejemplo, aprende <b>cuánto</b> deberían importar más los "delitos anteriores" que la"edad".</p>
                
                <hr style='margin:24px 0;'>

                <h3 style='color:#dc2626;'>⚠️ El reto ético</h3>
                <div style='font-size: 18px; background:#fef2f2; padding:24px; border-radius:12px; border-left:6px solid #dc2626;'>
                    <p style='margin:0;'><b>Aquí está el problema crítico:</b> El model *només* aprèn de les dades.
                    Si los datos históricos tienen sesgo (por ejemplo, ciertos grupos fueron arrestados más a menudo), 
                    el modelo aprenderá estos patrones sesgados.
                    <br><br>
                    <b>El modelo no conoce "equidad" o "justicia", solo conoce patrones.</b>
                    </p>
                </div>

                </div>
            """
            )
            
            with gr.Row():
                step_3_back = gr.Button("◀️ Atrás", size="lg")
                step_3_next = gr.Button("Siguiente: Pruébalo tú mismo ▶️", variant="primary", size="lg")
        
        # Pas 4: Demostració interactiva
        with gr.Column(visible=False) as step_4:
            gr.Markdown("<h2 style='text-align:center;'>🎮 Pruébalo tú mismo!</h2>")
            gr.Markdown(
                """
                <div style='font-size: 18px; background:#fef3c7; padding:24px; border-radius:12px; text-align:center;'>
                <p style='margin:0;'><b>Utilicemos un modelo de IA simple para predecir el riesgo criminal.</b><br>
                Ajusta las entradas a continuación y ve cómo cambia la predicción del modelo!</p>
                </div>
                """
            )
            gr.HTML("<br>")
            
            gr.Markdown("<h3 style='text-align:center; color:#0369a1;'>1️⃣ ENTRADA: Ajusta los datos</h3>")
            
            with gr.Row():
                age_slider = gr.Slider(
                    minimum=18, 
                    maximum=65, 
                    value=25, 
                    step=1, 
                    label="Edat",
                    info="Edad del acusado"
                )
                priors_slider = gr.Slider(
                    minimum=0, 
                    maximum=10, 
                    value=2, 
                    step=1, 
                    label="Delitos anteriores",
                    info="Nombre de delitos anteriores"
                )
            
            severity_dropdown = gr.Dropdown(
                choices=["Menor", "Moderado", "Grave"],
                value="Moderado",
                label="Gravedad del cargo actual",
                info="Qué gravedad tiene el cargo actual?"
            )
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown("<h3 style='text-align:center; color:#92400e;'>2️⃣ MODELO: Procesar los datos</h3>")
            
            predict_btn = gr.Button("🔮 Ejecutar predicción de IA", variant="primary", size="lg")
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown("<h3 style='text-align:center; color:#15803d;'>3️⃣ SALIDA: Ve la predicción</h3>")
            
            prediction_output = gr.HTML(
                """
                <div style='background:#f3f4f6; padding:40px; border-radius:12px; text-align:center;'>
                    <p style='color:#6b7280; font-size:18px; margin:0;'>
                    Haz clic en "Ejecutar predicción de IA" arriba para ver el resultado
                    </p>
                </div>
                """
            )
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown(
                """
                <div style='background:#e0f2fe; padding:20px; border-radius:12px; font-size:18px;'>
                <b>Lo que acabas de hacer:</b><br><br>
                Has utilizado un modelo de IA muy simple! Has proporcionado <b style='color:#0369a1;'>datos de entrada</b> 
                (edad, delitos anteriores, gravetat), el <b style='color:#92400e;'>model les ha processat</b> utilitzant regles 
                i patrons, i ha producido una <b style='color:#15803d;'>predicción de salida</b>.<br><br>
                Los modelos de IA reales son más complejos, pero funcionan con el mismo principio!
                </div>
                """
            )
            
            with gr.Row():
                step_4_back = gr.Button("◀️ Atrás", size="lg")
                step_4_next = gr.Button("Siguiente: Connexió amb la justicia ▶️", variant="primary", size="lg")
        
        # Pas 5: Connexió amb el repte
        with gr.Column(visible=False) as step_5:
            gr.Markdown("<h2 style='text-align:center;'>🔗 Connexió amb la justicia penal</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#faf5ff; padding:28px; border-radius:16px;'>
                <p><b>Recuerdas la predicción de riesgo que utilizaste antes como juez?</b></p>
                
                <p style='margin-top:20px;'>Este era un ejemplo real de IA en acción:</p>
                
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0; border:3px solid #9333ea;'>
                    <p style='font-size:18px; margin-bottom:16px;'>
                    <b style='color:#0369a1;'>ENTRADA:</b> Información del acusado<br>
                    <span style='margin-left:24px; color:#6b7280;'>• Edat, raza, género, delitos anteriores, detalles del cargo</span>
                    </p>
                    
                    <p style='font-size:18px; margin:16px 0;'>
                    <b style='color:#92400e;'>MODELO:</b> Algoritmo de evaluación de riesgo<br>
                    <span style='margin-left:24px; color:#6b7280;'>• Entrenat amb dades de justicia penal històriques</span><br>
                    <span style='margin-left:24px; color:#6b7280;'>• Busca patrones en quién reincidió en el pasado</span>
                    </p>
                    
                    <p style='font-size:18px; margin-top:16px; margin-bottom:0;'>
                    <b style='color:#15803d;'>SALIDA:</b> Predicción de riesgo<br>
                    <span style='margin-left:24px; color:#6b7280;'>• "Riesgo Alto", "Riesgo Medio" o "Riesgo Bajo"</span>
                    </p>
                </div>
                
                <h3 style='color:#7e22ce; margin-top:32px;'>Por qué esto importa para la ética:</h3>
                
                <div style='background:#fef2f2; padding:20px; border-radius:8px; margin-top:16px; border-left:6px solid #dc2626;'>
                    <ul style='font-size:18px; margin:8px 0;'>
                        <li>Les <b>datos de entrada</b> pueden contener sesgos históricos</li>
                        <li>El <b>model</b> aprende patrones de decisiones potencialmente injustas del pasado</li>
                        <li>Les <b>prediccions de sortida</b> pueden perpetuar la discriminación</li>
                    </ul>
                </div>
                
                <div style='background:#dbeafe; padding:20px; border-radius:8px; margin-top:24px;'>
                    <p style='font-size:18px; margin:0;'>
                    <b>Entender cómo funciona la IA es el primer paso para construir sistemas más justos.</b><br><br>
                    Ahora que sabes qué es la IA, estás preparado para ayudar a diseñar mejores modelos que 
                    siguin més ètics i menys esbiaixats!
                    </p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_5_back = gr.Button("◀️ Atrás", size="lg")
                step_5_next = gr.Button("Completar esta sección ▶️", variant="primary", size="lg")
        
        # Pas 6: Finalització
        with gr.Column(visible=False) as step_6:
            gr.HTML(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>🎓 Ahora entiendes la IA!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        <p><b>Felicidades!</b> Ahora sabes:</p>
                        
                        <ul style='font-size:1.1rem; text-align:left; max-width:600px; margin:20px auto;'>
                            <li>Qué es la IA (un sistema de predicción)</li>
                            <li>Cómo funciona (Entrada → Model → Sortida)</li>
                            <li>Cómo aprenden los modelos d'IA de les dades</li>
                            <li>Per què importa per a la justicia penal</li>
                            <li>Las implicaciones éticas de las decisiones de IA</li>
                        </ul>
                        
                        <p style='margin-top:32px;'><b>Próximos pasos:</b></p>
                        <p>En las secciones siguientes, aprenderás cómo construir y mejorar modelos de IA 
                        para hacerlos más justos y éticos.</p>
                        
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 DESPLÁZATE HACIA ABAJO 👇</h1>
                        <p style='font-size:1.1rem;'>Continúa a la siguiente sección a continuación.</p>
                    </div>
                </div>
                """
            )
            back_to_connection_btn = gr.Button("◀️ Volver a revisar")
        
        
        # --- LÒGICA DEL BOTÓ DE PREDICCIÓ ---
        predict_btn.click(
            predict_outcome,
            inputs=[age_slider, priors_slider, severity_dropdown],
            outputs=prediction_output,
            show_progress="full",
            scroll_to_output=True,
        )
        
        # --- LÒGICA DE NAVEGACIÓ CORREGIDA (BASADA EN GENERADOR) ---
        
        # Aquesta llista s'ha de definir *després* de tots els components
        all_steps = [step_1, step_2, step_3, step_4, step_5, step_6, loading_screen]

        def create_nav_generator(current_step, next_step):
            """Un ajudant per crear les funcions generadores per evitar codi repetitiu."""
            def navigate():
                # Yield 1: Mostrar càrrega, amagar tot
                updates = {loading_screen: gr.update(visible=True)}
                for step in all_steps:
                    if step != loading_screen:
                        updates[step] = gr.update(visible=False)
                yield updates
                
                
                # Yield 2: Mostrar nou pas, amagar tot
                updates = {next_step: gr.update(visible=True)}
                for step in all_steps:
                    if step != next_step:
                        updates[step] = gr.update(visible=False)
                yield updates
            return navigate

        # --- Connectar cada botó al seu propi generador únic ---
        step_1_next.click(
            fn=create_nav_generator(step_1, step_2), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_back.click(
            fn=create_nav_generator(step_2, step_1), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_next.click(
            fn=create_nav_generator(step_2, step_3), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_3_back.click(
            fn=create_nav_generator(step_3, step_2), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_3_next.click(
            fn=create_nav_generator(step_3, step_4), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_4_back.click(
            fn=create_nav_generator(step_4, step_3), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_4_next.click(
            fn=create_nav_generator(step_4, step_5), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_5_back.click(
            fn=create_nav_generator(step_5, step_4), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_5_next.click(
            fn=create_nav_generator(step_5, step_6), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        back_to_connection_btn.click(
            fn=create_nav_generator(step_6, step_5), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        # --- FI LÒGICA DE NAVEGACIÓ ---
    
    return demo


def launch_what_is_ai_app(height: int = 1100, share: bool = False, debug: bool = False) -> None:
    """Envolvente de conveniencia per crear i llançar l'aplicació què és l'IA inline."""
    demo = create_what_is_ai_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio debe estar instalado para lanzar la aplicación qué es la IA.") from e
    
    # Este es el envolvente original, diseñado para uso en un notebook (como Colab)
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

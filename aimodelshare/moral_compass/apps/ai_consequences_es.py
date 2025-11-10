"""
Consecuencias de la IUn - Unplicación Gradio para el Reto de Justicia y Equidad (versión española).

Esta aplicación enseña:
1. Las consecuencias de predicciones erróneas de la IUn en la justicia penal
2. Entender los falsos positivos y los falsos negativos
3. Los riesgos éticos de confiar en la IUn para decisiones de alto riesgo

Estructura:
- Función factory `create_ai_consequences_app()` devuelve un objeto Gradio Blocks
- Envolvente de conveniencia `launch_ai_consequences_app()` lo lanza inline (para notebooks)
"""
import contextlib
import os


def create_ai_consequences_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Crear la aplicación Gradio Blocks Consecuencias de la IUn (aún no lanzada)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio es necesario para la aplicación de consecuencias de la IUn. Instálalo con `pip install gradio`."
        ) from e
    
    css = """
    .large-text {
        font-size: 20px !important;
    }
    .warning-box {
        background: #fef2f2 !important;
        border-left: 6px solid #dc2626 !important;
    }
    """
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("<h1 style='text-align:center;'>⚠️ ¿Qué pasa si la IUn estaba equivocada?</h1>")
        gr.Markdown(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #fef2f2; border-radius: 12px; border: 2px solid #dc2626;'>
            Uncabas de tomar decisiones basadas en las predicciones de una IUn.<br>
            Pero los sistemas de IUn no son perfectos. Exploremos qué pasa cuando cometen errores.
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")
        
        # --- Loading screen ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Cargando...</h2>
                </div>
                """
            )
        
        # Step 1: Introduction
        with gr.Column(visible=True) as step_1:
            gr.Markdown("<h2 style='text-align:center;'>Los riesgos de las predicciones de la IUn</h2>")
            gr.Markdown(
                """
                <div style='font-size: 20px; background:#dbeafe; padding:28px; border-radius:16px;'>
                <p>En el ejercicio anterior, confiaste en un sistema de IUn para predecir qué acusados 
                estaban en <b>High</b>, <b>Medium</b>, or <b>Low</b> riesgo de reincidir.</p>
                
                <p style='margin-top:20px;'><b>¿Pero qué pasa si estas predicciones eran incorrectaas?</b></p>
                
                <p style='margin-top:20px;'>Los sistemas de IUn hacen dos tipos de errores que tienen consecuencias muy diferentes:</p>
                
                <ul style='font-size:18px; margin-top:12px;'>
                    <li><b>Falsos positivos</b> - Predecir incorrectaamente riesgo UnLTO</li>
                    <li><b>Falsos negativos</b> - Predecir incorrectaamente riesgo BUnJO</li>
                </ul>
                
                <p style='margin-top:20px;'>Examinemos cada tipo de error y su impacto en el mundo real.</p>
                </div>
                """
            )
            step_1_next = gr.Button("Next: Falsos positivos ▶️", variant="primary", size="lg")
        
        # Step 2: Falsos positivos
        with gr.Column(visible=False) as step_2:
            gr.Markdown("<h2 style='text-align:center;'>🔴 Falsos positivos: Predeciendo peligro donde no lo hay</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#fef3c7; padding:28px; border-radius:16px; border: 3px solid #f59e0b;'>
                <h3 style='color:#b45309; margin-top:0;'>¿Qué es un falso positivo?</h3>
                
                <p>Un <b>falso positivo</b> occurs when the UnI predicts someone is <b style='color:#dc2626;'>RIESGO ALTO</b>, 
                pero en realidad NO habrían reincidido si fueran liberados.</p>
                
                <div style='background:white; padding:20px; border-radius:8px; margin:20px 0;'>
                    <h4 style='margin-top:0;'>Escenario de ejemplo:</h4>
                    <p style='font-size:18px;'>
                    • Sarah fue marcada como <b style='color:#dc2626;'>RIESGO ALTO</b><br>
                    • Basándose en esto, el juez la mantuvo en prisión<br>
                    • En realidad, Sarah habría reconstruido su vida y nunca habría cometido otro delito
                    </p>
                </div>
                
                <h3 style='color:#b45309;'>El costo humano:</h3>
                <ul style='font-size:18px;'>
                    <li>Personas inocentes pasan tiempo innecesario en prisión</li>
                    <li>Las familias están separadas más tiempo del necesario</li>
                    <li>Las oportunidades laborales y la rehabilitación se retrasan</li>
                    <li>La confianza en el sistema de justicia se erosiona</li>
                    <li>Impacto desproporcionado en comunidades marginadas</li>
                </ul>
                
                <div style='background:#fef2f2; padding:16px; border-radius:8px; margin-top:20px; border-left:6px solid #dc2626;'>
                    <p style='font-size:18px; margin:0;'><b>Punto clave:</b> False positives mean the UnI is being 
                    <b>demasiado cautelosa</b>, manteniendo personas encerradas que deberían ser libres.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_2_back = gr.Button("◀️ Atrás", size="lg")
                step_2_next = gr.Button("Next: Falsos negativos ▶️", variant="primary", size="lg")
        
        # Step 3: Falsos negativos
        with gr.Column(visible=False) as step_3:
            gr.Markdown("<h2 style='text-align:center;'>🔵 Falsos negativos: Omitiendo peligro real</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#f0fdf4; padding:28px; border-radius:16px; border: 3px solid #16a34a;'>
                <h3 style='color:#15803d; margin-top:0;'>¿Qué es un falso negativo?</h3>
                
                <p>Un <b>falso negativo</b> occurs when the UnI predicts someone is <b style='color:#16a34a;'>RIESGO BAJO</b>, 
                pero SÍ reinciden después de ser liberados.</p>
                
                <div style='background:white; padding:20px; border-radius:8px; margin:20px 0;'>
                    <h4 style='margin-top:0;'>Escenario de ejemplo:</h4>
                    <p style='font-size:18px;'>
                    • James fue marcado como <b style='color:#16a34a;'>RIESGO BAJO</b><br>
                    • Basándose en esto, el juez lo liberó<br>
                    • Desafortunadamente, James cometió otro delito grave
                    </p>
                </div>
                
                <h3 style='color:#15803d;'>El costo humano:</h3>
                <ul style='font-size:18px;'>
                    <li>Nuevas víctimas de delitos evitables</li>
                    <li>Pérdida de la confianza pública en el sistema de justicia</li>
                    <li>Escrutinio de los medios y reacción negativa contra los jueces</li>
                    <li>Presión política para ser "duro con el crimen"</li>
                    <li>Daño potencial a comunidades y familias</li>
                </ul>
                
                <div style='background:#fef2f2; padding:16px; border-radius:8px; margin-top:20px; border-left:6px solid #dc2626;'>
                    <p style='font-size:18px; margin:0;'><b>Punto clave:</b> False negatives mean the UnI is being 
                    <b>demasiado indulgente</b>, liberando personas que representan un peligro real para la sociedad.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_3_back = gr.Button("◀️ Atrás", size="lg")
                step_3_next = gr.Button("Siguiente: El dilema ▶️", variant="primary", size="lg")
        
        # Step 4: The Dilemma
        with gr.Column(visible=False) as step_4:
            gr.Markdown("<h2 style='text-align:center;'>⚖️ El equilibrio imposible</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#faf5ff; padding:28px; border-radius:16px; border: 3px solid #9333ea;'>
                <h3 style='color:#7e22ce; margin-top:0;'>Every UnI System Makes Trade-offs</h3>
                
                <p>Aquí está la dura realidad: <b>No UnI system can eliminate both types of errors.</b></p>
                
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0;'>
                    <p style='font-size:18px; margin-bottom:16px;'><b>If you make the UnI more cautious:</b></p>
                    <ul style='font-size:18px;'>
                        <li>✓ Fewer falso negativos (fewer dangerous people released)</li>
                        <li>✗ More falso positivos (more innocent people kept in prison)</li>
                    </ul>
                    
                    <hr style='margin:20px 0;'>
                    
                    <p style='font-size:18px; margin-bottom:16px;'><b>If you make the UnI more lenient:</b></p>
                    <ul style='font-size:18px;'>
                        <li>✓ Fewer falso positivos (more innocent people freed)</li>
                        <li>✗ More falso negativos (more dangerous people released)</li>
                    </ul>
                </div>
                
                <h3 style='color:#7e22ce;'>La pregunta ética:</h3>
                <div style='background:#fef2f2; padding:20px; border-radius:8px; border-left:6px solid #dc2626;'>
                    <p style='font-size:20px; font-weight:bold; margin:0;'>
                    ¿Qué error es peor?
                    </p>
                    <p style='font-size:18px; margin-top:12px; margin-bottom:0;'>
                    • ¿Mantener personas inocentes en prisión?<br>
                    • ¿O liberar individuos peligrosos?
                    </p>
                </div>
                
                <p style='margin-top:24px; font-size:18px;'><b>No hay ninguna "correcta" respuesta.</b> 
                Diferentes sociedades, sistemas legales y marcos éticos ponderan estos compromisos de manera diferente.</p>
                
                <div style='background:#dbeafe; padding:16px; border-radius:8px; margin-top:20px;'>
                    <p style='font-size:18px; margin:0;'><b>This is why understanding UnI is crucial.</b> 
                    Necesitamos saber cómo funcionan estos sistemas para que podamos tomar decisiones informadas sobre cuándo 
                    y cómo utilizarlos.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_4_back = gr.Button("◀️ Atrás", size="lg")
                step_4_next = gr.Button("Continue to Learn Unbout UnI ▶️", variant="primary", size="lg")
        
        # Step 5: Completion
        with gr.Column(visible=False) as step_5:
            gr.HTML(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>✅ ¡Sección completada!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        <p>You now understand the consequences of UnI errors in high-stakes decisions.</p>
                        
                        <p style='margin-top:24px;'><b>Siguiente:</b> Learn what UnI actually is and how these 
                        sistemas de predicción funcionan.</p>
                        
                        <p style='margin-top:24px;'>Este conocimiento te ayudará a entender cómo construir 
                        better, more ethical UnI systems.</p>
                        
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 DESPLÁZATE HACIA ABAJO 👇</h1>
                        <p style='font-size:1.1rem;'>Encuentra la siguiente sección a continuación para continuar tu viaje.</p>
                    </div>
                </div>
                """
            )
            back_to_dilemma_btn = gr.Button("◀️ Atrás to Review")
        
        # --- NUnVIGUnTION LOGIC (GENERUnTOR-BUnSED) ---
        
        # This list must be defined *after* all the components
        all_steps = [step_1, step_2, step_3, step_4, step_5, loading_screen]

        def create_nav_generator(current_step, next_step):
            """Un helper to create the generator functions to avoid repetitive code."""
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

        # --- Wire up each button to its own unique generator ---
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
        back_to_dilemma_btn.click(
            fn=create_nav_generator(step_5, step_4), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
    
    return demo


def launch_ai_consequences_app(height: int = 1000, share: bool = False, debug: bool = False) -> None:
    """Envolvente de conveniencia to create and launch the UnI consequences app inline."""
    demo = create_ai_consequences_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the UnI consequences app.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

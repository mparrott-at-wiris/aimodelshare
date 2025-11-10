"""
Tú eres el Juez - Aplicación Gradio para el Reto de Justicia y Equidad (versión española).

Esta aplicación enseña:
1. Cómo tomar decisiones basadas en predicciones de IA
2. Los riesgos implicados en el uso de IA para decisiones de justicia penal
3. La importancia de entender qué se equivoca la IA

Estructura:
- Función factory `create_judge_app()` devuelve un objeto Gradio Blocks
- Envolvente de conveniencia `launch_judge_app()` lo lanza inline (para notebooks)
"""
import contextlib
import os


def _generate_defendant_profiles():
    """Generar perfiles sintéticos de acusados para el ejercicio."""
    import random
    random.seed(42)  # Para reproducibilidad
    
    profiles = [
        {
            "id": 1,
            "name": "Carlos M.",
            "age": 23,
            "gender": "Hombre",
            "race": "Hispano",
            "prior_offenses": 2,
            "current_charge": "Posesión de drogas",
            "ai_risk": "Alto",
            "ai_confidence": "85%"
        },
        {
            "id": 2,
            "name": "Sara J.",
            "age": 34,
            "gender": "Mujer",
            "race": "Blanco",
            "prior_offenses": 0,
            "current_charge": "Robo",
            "ai_risk": "Bajo",
            "ai_confidence": "72%"
        },
        {
            "id": 3,
            "name": "DeShawn W.",
            "age": 19,
            "gender": "Hombre",
            "race": "Negro",
            "prior_offenses": 1,
            "current_charge": "Agresión",
            "ai_risk": "Medio",
            "ai_confidence": "68%"
        },
        {
            "id": 4,
            "name": "María R.",
            "age": 41,
            "gender": "Mujer",
            "race": "Hispana",
            "prior_offenses": 3,
            "current_charge": "Fraude",
            "ai_risk": "Medio",
            "ai_confidence": "70%"
        },
        {
            "id": 5,
            "name": "Jaime K.",
            "age": 28,
            "gender": "Hombre",
            "race": "Blanco",
            "prior_offenses": 5,
            "current_charge": "Robo con violencia",
            "ai_risk": "Alto",
            "ai_confidence": "91%"
        }
    ]
    
    return profiles


def create_judge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Crear la aplicación Gradio Blocks Tú eres el Juez (aún no lanzada)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)

    except ImportError as e:
        raise ImportError(
            "Gradio es necesario para la aplicación de juez. Instálalo con `pip install gradio`."
        ) from e
    
    profiles = _generate_defendant_profiles()
    
    # Estado para hacer seguimiento de las decisiones
    decisions = {}
    
    def format_profile(profile):
        """Formatear un perfil de acusado para la visualización."""
        risk_color = {
            "Alto": "#ef4444",
            "Medio": "#f59e0b", 
            "Bajo": "#22c55e"
        }
        
        color = risk_color.get(profile["ai_risk"], "#6b7280")
        
        return f"""
        <div style='background:#f9fafb; padding:20px; border-radius:12px; border-left: 6px solid {color};'>
            <h3 style='margin-top:0; color:#1f2937;'>Acusado #{profile['id']}: {profile['name']}</h3>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 16px;'>
                <div><b>Edad:</b> {profile['age']}</div>
                <div><b>Género:</b> {profile['gender']}</div>
                <div><b>Raza:</b> {profile['race']}</div>
                <div><b>Delitos anteriores:</b> {profile['prior_offenses']}</div>
                <div style='grid-column: span 2;'><b>Cargo actual:</b> {profile['current_charge']}</div>
            </div>
            <div style='margin-top:16px; padding:12px; background:white; border-radius:8px;'>
                <b>🤖 Evaluación de riesgo de la IA:</b> 
                <span style='color:{color}; font-size:20px; font-weight:bold;'>Riesgo {profile['ai_risk']}</span>
                <span style='color:#6b7280; margin-left:8px;'>(Confianza: {profile['ai_confidence']})</span>
            </div>
        </div>
        """
    
    def make_decision(defendant_id, decision):
        """Registrar una decisión para un acusado."""
        decisions[defendant_id] = decision
        return f"✓ Decisión registrada: {decision}"
    
    def get_summary():
        """Obtener resumen de todas las decisiones tomadas."""
        if not decisions:
            return "Aún no se han tomado decisiones."
        
        released = sum(1 for d in decisions.values() if d == "Liberar")
        kept = sum(1 for d in decisions.values() if d == "Mantener en prisión")
        
        summary = f"""
        <div style='background:#dbeafe; padding:20px; border-radius:12px;'>
            <h3 style='margin-top:0;'>📊 Resumen de tus decisiones</h3>
            <div style='font-size:18px;'>
                <p><b>Prisioneros liberados:</b> {released} de {len(decisions)}</p>
                <p><b>Prisioneros mantenidos en prisión:</b> {kept} de {len(decisions)}</p>
            </div>
        </div>
        """
        return summary
    
    css = """
    .decision-button {
        font-size: 18px !important;
        padding: 12px 24px !important;
    }
    """
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("<h1 style='text-align:center;'>⚖️ Tú eres el Juez</h1>")
        gr.Markdown(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #fef3c7; border-radius: 12px; border: 2px solid #f59e0b;'>
            <b>Tu rol:</b> Eres un juez que debe decidir si liberar acusados de la prisión.<br>
            Un sistema de IA ha analizado cada caso y ha proporcionado una evaluación de riesgo.<br><br>
            <b>Tu tarea:</b> Revisa el perfil de cada acusado y la predicción de la IA, luego toma tu decisión.
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")
        
        # --- Pantalla de carga ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Cargando...</h2>
                </div>
                """
            )
        
        # Introducción
        with gr.Column(visible=True) as intro_section:
            gr.Markdown("<h2 style='text-align:center;'>📋 El escenario</h2>")
            gr.Markdown(
                """
                <div style='font-size: 18px; background:#e0f2fe; padding:24px; border-radius:12px;'>
                Eres un juez en un tribunal penal ocupado. Debido al hacinamiento en las prisiones, debes decidir 
                qué acusados pueden ser liberados de manera segura.<br><br>
                
                Para ayudarte, el tribunal ha implementado un sistema de IA que predice el riesgo de cada 
                acusado de cometer nuevos delitos si es liberado. La IA categoriza a los acusados como:<br><br>
                
                <ul style='font-size:18px;'>
                    <li><span style='color:#ef4444; font-weight:bold;'>Riesgo Alto</span> - Probable que reincida</li>
                    <li><span style='color:#f59e0b; font-weight:bold;'>Riesgo Medio</span> - Posibilidad moderada de reincidencia</li>
                    <li><span style='color:#22c55e; font-weight:bold;'>Riesgo Bajo</span> - Poco probable que reincida</li>
                </ul>
                
                <b>Recuerda:</b> Tus decisiones afectan las vidas de personas reales y la seguridad pública.
                </div>
                """
            )
            start_btn = gr.Button("Comenzar a tomar decisiones ▶️", variant="primary", size="lg")
        
        # Sección de perfiles de acusados
        with gr.Column(visible=False) as profiles_section:
            gr.Markdown("<h2 style='text-align:center;'>👥 Perfiles de acusados</h2>")
            gr.Markdown(
                """
                <div style='text-align:center; font-size:16px; background:#f3f4f6; padding:12px; border-radius:8px;'>
                Revisa la información de cada acusado y la evaluación de riesgo de la IA, luego toma tu decisión.
                </div>
                """
            )
            gr.HTML("<br>")
            
            # Crear interfaz de usuario para cada acusado
            for profile in profiles:
                with gr.Column():
                    gr.HTML(format_profile(profile))
                    
                    with gr.Row():
                        release_btn = gr.Button(
                            "✓ Liberar prisionero", 
                            variant="primary",
                            elem_classes=["decision-button"]
                        )
                        keep_btn = gr.Button(
                            "✗ Mantener en prisión",
                            variant="secondary",
                            elem_classes=["decision-button"]
                        )
                    
                    decision_status = gr.Markdown("")
                    
                    # Conectar botones
                    release_btn.click(
                        lambda p_id=profile["id"]: make_decision(p_id, "Liberar"),
                        inputs=None,
                        outputs=decision_status
                    )
                    keep_btn.click(
                        lambda p_id=profile["id"]: make_decision(p_id, "Mantener en prisión"),
                        inputs=None,
                        outputs=decision_status
                    )
                    
                    gr.HTML("<hr style='margin:24px 0;'>")
            
            # Sección de resumen
            summary_display = gr.HTML("")
            show_summary_btn = gr.Button("📊 Mostrar resumen de mis decisiones", variant="primary", size="lg")
            show_summary_btn.click(get_summary, inputs=None, outputs=summary_display)
            
            gr.HTML("<br>")
            complete_btn = gr.Button("Completar esta sección ▶️", variant="primary", size="lg")
        
        # Sección de finalización
        with gr.Column(visible=False) as complete_section:
            gr.Markdown(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>✅ ¡Decisiones completadas!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        Has tomado tus decisiones basándote en las recomendaciones de la IA.<br><br>
                        Pero aquí está la pregunta crítica:<br><br>
                        <h2 style='color:#dc2626; margin:16px 0;'>¿Qué pasa si la IA estaba equivocada?</h2>
                        <p style='font-size:1.1rem;'>
                        Continúa a la siguiente sección a continuación para explorar las consecuencias de 
                        confiar en las predicciones de IA en situaciones de alto riesgo.
                        </p>
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 DESPLÁZATE HACIA ABAJO 👇</h1>
                        <p style='font-size:1.1rem;'>Encuentra la siguiente sección a continuación para continuar tu viaje.</p>
                        </div>
                </div>
                """
            )
            back_to_profiles_btn = gr.Button("◀️ Volver a revisar decisiones")
        
        # --- LÓGICA DE NAVEGACIÓN (BASADA EN GENERADOR) ---
        
        # Esta lista debe definirse *después* de todos los componentes
        all_steps = [intro_section, profiles_section, complete_section, loading_screen]

        def create_nav_generator(current_step, next_step):
            """Un ayudante para crear las funciones generadoras para evitar código repetitivo."""
            def navigate():
                # Yield 1: Mostrar carga, ocultar todo
                updates = {loading_screen: gr.update(visible=True)}
                for step in all_steps:
                    if step != loading_screen:
                        updates[step] = gr.update(visible=False)
                yield updates
                
                
                # Yield 2: Mostrar nuevo paso, ocultar todo
                updates = {next_step: gr.update(visible=True)}
                for step in all_steps:
                    if step != next_step:
                        updates[step] = gr.update(visible=False)
                yield updates
            return navigate

        # --- Conectar cada botón a su propio generador único ---
        start_btn.click(
            fn=create_nav_generator(intro_section, profiles_section), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        complete_btn.click(
            fn=create_nav_generator(profiles_section, complete_section), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        back_to_profiles_btn.click(
            fn=create_nav_generator(complete_section, profiles_section), 
            inputs=None, outputs=all_steps, show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
    
    return demo


def launch_judge_app(height: int = 1200, share: bool = False, debug: bool = False) -> None:
    """Envolvente de conveniencia para crear y lanzar la aplicación de juez inline."""
    demo = create_judge_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio debe estar instalado para lanzar la aplicación de juez.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

"""
Tutorial Aplicación Gradio para incorporar usuarios al Reto de Justicia y Equidad (versión española).

Esta aplicación enseña:
1. Cómo avanzar pasos estilo presentación de diapositivas
2. Cómo interactuar con controles deslizantes/botones
3. Cómo aparece la salida de predicción del modelo

Estructura:
- Función factory `create_tutorial_app()` devuelve un objeto Gradio Blocks
- Envolvente de conveniencia `launch_tutorial_app()` lo lanza inline (para notebooks)
"""
import contextlib
import os


def _build_synthetic_model():
    """Construir un pequeño modelo de regresión lineal con datos sintéticos de hábitos de estudio."""
    import numpy as np
    from sklearn.linear_model import LinearRegression

    rng = np.random.default_rng(7)
    n = 200
    hours_study = rng.uniform(0, 12, n)
    hours_sleep = rng.uniform(4, 10, n)
    attendance = rng.uniform(50, 100, n)
    exam_score = 5 * hours_study + 3 * hours_sleep + 0.5 * attendance + rng.normal(0, 10, n)

    X = np.column_stack([hours_study, hours_sleep, attendance])
    y = exam_score
    lin_reg = LinearRegression().fit(X, y)

    def predict_exam(sl, slp, att):
        pred = float(lin_reg.predict([[sl, slp, att]])[0])
        import numpy as np
        pred = float(np.clip(pred, 0, 100))
        return f"{round(pred, 1)}%"

    return predict_exam


def create_tutorial_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Crear la aplicación Gradio Blocks tutorial (aún no lanzada)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)

    except ImportError as e:
        raise ImportError(
            "Gradio es necesario para la aplicación de tutorial. Instálalo con `pip install gradio`."
        ) from e

    predict_exam = _build_synthetic_model()

    css = """
    #prediction_output_textbox textarea {
        font-size: 2.5rem !important;
        font-weight: bold !important;
        color: #1E40AF !important;
        text-align: center !important;
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("<h1 style='text-align:center;'>👋 Cómo utilizar una aplicación (Un tutorial rápido)</h1>")
        gr.Markdown(
            """
            <div style='text-align:left; font-size:20px; max-width: 800px; margin: auto;
                        padding: 15px; background-color: #f7f7f7; border-radius: 8px;'>
            Este es un tutorial simple de 3 pasos.<br><br>
            <b>Tu tarea:</b> Solo lee las instrucciones para cada paso y haz clic en el botón "Siguiente" para continuar.
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")

        # --- Pantalla de càrrega ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Cargando...</h2>
                </div>
                """
            )

        # Paso 1
        with gr.Column(visible=True) as step_1_container:
            gr.Markdown("<h2 style='text-align:center;'>Paso 1: Cómo utilizar \"Presentaciones de diapositivas\"</h2>")
            gr.Markdown(
                """
                <div style='font-size: 28px; text-align: center; background:#E3F2FD;
                             padding:28px; border-radius:16px; min-height: 150px;'>
                  <b>Este es un paso de \"Presentación de diapositivas\".</b><br><br>
                  Algunas aplicaciones son solo para leer. Tu única tarea es hacer clic en el botón "Siguiente pas" para pasar al paso siguiente.
                </div>
                """
            )
            step_1_next = gr.Button("Siguiente pas ▶️", variant="primary")

        # Pas 2
        with gr.Column(visible=False) as step_2_container:
            gr.Markdown("<h2 style='text-align:center;'>Paso 2: Cómo utilizar \"Demos interactivas\"</h2>")
            gr.Markdown(
                """
                <div style='font-size: 20px; text-align: left; background:#FFF3E0;
                            padding:20px; border-radius:16px;'>
                  <b>Esta es una \"Demo interactiva\".</b><br><br>
                  Solo sigue los pasos numerados a continuación (de arriba a abajo) para ver cómo funciona!
                </div>
                """
            )
            gr.HTML("<br>")
            gr.Markdown(
                """
                <div style="font-size: 24px; text-align:left; padding-left: 10px;">
                  <b>[ 1 ] Utiliza estos controles deslizantes para cambiar las entradas.</b>
                </div>
                """
            )
            s_hours = gr.Slider(0, 12, step=0.5, value=6, label="Horas de estudio por semana")
            s_sleep = gr.Slider(4, 10, step=0.5, value=7, label="Horas de sueño por noche")
            s_att = gr.Slider(50, 100, step=1, value=90, label="Asistencia a clase %")

            gr.HTML("<hr style='margin: 20px 0;'>")

            gr.Markdown(
                """
                <div style="font-size: 24px; text-align:left; padding-left: 10px;">
                  <b>[ 2 ] Haz clic en este botón para ejecutar.</b>
                </div>
                """
            )
            with gr.Row():
                gr.HTML(visible=False)
                go = gr.Button("🔮 Predecir", variant="primary", scale=2)
                gr.HTML(visible=False)

            gr.HTML("<hr style='margin: 20px 0;'>")

            gr.Markdown(
                """
                <div style="font-size: 24px; text-align:left; padding-left: 10px;">
                  <b>[ 3 ] Ve el resultado aquí!</b>
                </div>
                """
            )
            out = gr.Textbox(
                label="🔮 Puntuación de examen prevista", elem_id="prediction_output_textbox", interactive=False
            )

            go.click(
                predict_exam,
                [s_hours, s_sleep, s_att],
                out,
                scroll_to_output=True,
            )

            gr.HTML("<hr style='margin: 15px 0;'>")
            with gr.Row():
                step_2_back = gr.Button("◀️ Atrás")
                step_2_next = gr.Button("Finalizar tutorial ▶️", variant="primary")

        # Pas 3
        with gr.Column(visible=False) as step_3_container:
            gr.Markdown(
                """
                <div style='text-align:center;'>
                  <h2 style='text-align:center; font-size: 2.5rem;'>✅ Tutorial completado!</h2>
                  <div style='font-size: 1.5rem; background:#E8F5E9; padding:28px; border-radius:16px;
                              border: 2px solid #4CAF50;'>
                    Has dominado los conceptos básicos!<br><br>
                    Tu próximo paso es <b>fuera</b> de esta ventana de aplicación.<br><br>
                    <h1 style='margin:0; font-size: 3rem;'>👇 DESPLÁZATE HACIA ABAJO 👇</h1><br>
                    Busca abajo de esta aplicación para encontrar la <b>Secció 3</b> y comenzar el reto!
                  </div>
                </div>
                """
            )
            with gr.Row():
                step_3_back = gr.Button("◀️ Atrás")

        # --- LÒGICA DE NAVEGACIÓ (BASADA EN GENERADOR) ---
        all_steps = [step_1_container, step_2_container, step_3_container, loading_screen]

        def create_nav_generator(current_step, next_step):
            """Un ayudante para crear las funciones generadoras para evitar código repetitivo."""
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

        step_1_next.click(
            fn=create_nav_generator(step_1_container, step_2_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_back.click(
            fn=create_nav_generator(step_2_container, step_1_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_2_next.click(
            fn=create_nav_generator(step_2_container, step_3_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )
        step_3_back.click(
            fn=create_nav_generator(step_3_container, step_2_container),
            inputs=None,
            outputs=all_steps,
            show_progress="full",
            js="()=>{window.scrollTo({top:0,behavior:'smooth'})}"
        )

    return demo


def launch_tutorial_app(height: int = 950, share: bool = False, debug: bool = False) -> None:
    """Envolvente de conveniencia per crear i llançar l'aplicació de tutorial inline."""
    demo = create_tutorial_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio debe estar instalado para lanzar la aplicación de tutorial.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

"""
Conseqüències de l'IUn - Unplicació Gradio per al Repte de Justícia i Equitat (versió catalana).

Unquesta aplicació ensenya:
1. Les conseqüències de prediccions errònies de l'IUn en la justícia penal
2. Entendre els falsos positius i els falsos negatius
3. Els riscos ètics de confiar en l'IUn per a decisions d'alt risc

Estructura:
- Funció factory `create_ai_consequences_app()` retorna un objecte Gradio Blocks
- Envolcall de conveniència `launch_ai_consequences_app()` el llança inline (per a notebooks)
"""
import contextlib
import os


def create_ai_consequences_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Crear l'aplicació Gradio Blocks Conseqüències de l'IUn (encara no llançada)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio és necessari per a l'aplicació de conseqüències de l'IUn. Instal·la-ho amb `pip install gradio`."
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
        gr.Markdown("<h1 style='text-align:center;'>⚠️ Què passa si l'IUn estava equivocada?</h1>")
        gr.Markdown(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #fef2f2; border-radius: 12px; border: 2px solid #dc2626;'>
            Uncabes de prendre decisions basades en les prediccions d'una IUn.<br>
            Però els sistemes d'IUn no són perfectes. Explorem què passa quan cometen errors.
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")
        
        # --- Loading screen ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Carregant...</h2>
                </div>
                """
            )
        
        # Step 1: Introduction
        with gr.Column(visible=True) as step_1:
            gr.Markdown("<h2 style='text-align:center;'>Els riscos de les prediccions de l'IUn</h2>")
            gr.Markdown(
                """
                <div style='font-size: 20px; background:#dbeafe; padding:28px; border-radius:16px;'>
                <p>En l'exercici anterior, vas confiar en un sistema d'IUn per predir quins acusats 
                estaven en <b>High</b>, <b>Medium</b>, or <b>Low</b> risc de reincidir.</p>
                
                <p style='margin-top:20px;'><b>Però què passa si aquestes prediccions eren incorrectaes?</b></p>
                
                <p style='margin-top:20px;'>Els sistemes d'IUn fan dos tipus d'errors que tenen conseqüències molt diferents:</p>
                
                <ul style='font-size:18px; margin-top:12px;'>
                    <li><b>Falsos positius</b> - Predir incorrectaament risc UnLT</li>
                    <li><b>Falsos negatius</b> - Predir incorrectaament risc BUnIX</li>
                </ul>
                
                <p style='margin-top:20px;'>Examinem cada tipus d'error i el seu impacte al món real.</p>
                </div>
                """
            )
            step_1_next = gr.Button("Next: Falsos positius ▶️", variant="primary", size="lg")
        
        # Step 2: Falsos positius
        with gr.Column(visible=False) as step_2:
            gr.Markdown("<h2 style='text-align:center;'>🔴 Falsos positius: Predient perill on no n'hi ha</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#fef3c7; padding:28px; border-radius:16px; border: 3px solid #f59e0b;'>
                <h3 style='color:#b45309; margin-top:0;'>Què és un fals positiu?</h3>
                
                <p>Un <b>fals positiu</b> occurs when the UnI predicts someone is <b style='color:#dc2626;'>RISC ALT</b>, 
                però en realitat NO haurien reincidit si fossin alliberats.</p>
                
                <div style='background:white; padding:20px; border-radius:8px; margin:20px 0;'>
                    <h4 style='margin-top:0;'>Escenari d'exemple:</h4>
                    <p style='font-size:18px;'>
                    • Sarah va ser marcada com a <b style='color:#dc2626;'>RISC ALT</b><br>
                    • Basant-se en això, el jutge la va mantenir a la presó<br>
                    • En realitat, Sarah hauria reconstruït la seva vida i mai hauria comès un altre delicte
                    </p>
                </div>
                
                <h3 style='color:#b45309;'>El cost humà:</h3>
                <ul style='font-size:18px;'>
                    <li>Persones innocents passen temps innecessari a la presó</li>
                    <li>Les famílies estan separades més temps del necessari</li>
                    <li>Les oportunitats laborals i la rehabilitació es retarden</li>
                    <li>La confiança en el sistema de justícia s'erosiona</li>
                    <li>Impacte desproporcionat en comunitats marginades</li>
                </ul>
                
                <div style='background:#fef2f2; padding:16px; border-radius:8px; margin-top:20px; border-left:6px solid #dc2626;'>
                    <p style='font-size:18px; margin:0;'><b>Punt clau:</b> False positives mean the UnI is being 
                    <b>massa cautelosa</b>, mantenint persones tancades que haurien de ser lliures.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_2_back = gr.Button("◀️ Enrere", size="lg")
                step_2_next = gr.Button("Next: Falsos negatius ▶️", variant="primary", size="lg")
        
        # Step 3: Falsos negatius
        with gr.Column(visible=False) as step_3:
            gr.Markdown("<h2 style='text-align:center;'>🔵 Falsos negatius: Ometent perill real</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#f0fdf4; padding:28px; border-radius:16px; border: 3px solid #16a34a;'>
                <h3 style='color:#15803d; margin-top:0;'>Què és un fals negatiu?</h3>
                
                <p>Un <b>fals negatiu</b> occurs when the UnI predicts someone is <b style='color:#16a34a;'>RISC BAIX</b>, 
                però SÍ que reincideixen després de ser alliberats.</p>
                
                <div style='background:white; padding:20px; border-radius:8px; margin:20px 0;'>
                    <h4 style='margin-top:0;'>Escenari d'exemple:</h4>
                    <p style='font-size:18px;'>
                    • James va ser marcat com a <b style='color:#16a34a;'>RISC BAIX</b><br>
                    • Basant-se en això, el jutge el va alliberar<br>
                    • Desgraciadament, James va cometre un altre delicte greu
                    </p>
                </div>
                
                <h3 style='color:#15803d;'>El cost humà:</h3>
                <ul style='font-size:18px;'>
                    <li>Noves víctimes de delictes evitables</li>
                    <li>Pèrdua de la confiança pública en el sistema de justícia</li>
                    <li>Escrutini dels mitjans i reacció negativa contra els jutges</li>
                    <li>Pressió política per ser "dur amb el crim"</li>
                    <li>Dany potencial a comunitats i famílies</li>
                </ul>
                
                <div style='background:#fef2f2; padding:16px; border-radius:8px; margin-top:20px; border-left:6px solid #dc2626;'>
                    <p style='font-size:18px; margin:0;'><b>Punt clau:</b> False negatives mean the UnI is being 
                    <b>massa indulgent</b>, alliberant persones que representen un perill real per a la societat.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_3_back = gr.Button("◀️ Enrere", size="lg")
                step_3_next = gr.Button("Següent: El dilema ▶️", variant="primary", size="lg")
        
        # Step 4: The Dilemma
        with gr.Column(visible=False) as step_4:
            gr.Markdown("<h2 style='text-align:center;'>⚖️ L'equilibri impossible</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#faf5ff; padding:28px; border-radius:16px; border: 3px solid #9333ea;'>
                <h3 style='color:#7e22ce; margin-top:0;'>Every UnI System Makes Trade-offs</h3>
                
                <p>Aquí està la dura realitat: <b>No UnI system can eliminate both types of errors.</b></p>
                
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0;'>
                    <p style='font-size:18px; margin-bottom:16px;'><b>If you make the UnI more cautious:</b></p>
                    <ul style='font-size:18px;'>
                        <li>✓ Fewer fals negatius (fewer dangerous people released)</li>
                        <li>✗ More fals positius (more innocent people kept in prison)</li>
                    </ul>
                    
                    <hr style='margin:20px 0;'>
                    
                    <p style='font-size:18px; margin-bottom:16px;'><b>If you make the UnI more lenient:</b></p>
                    <ul style='font-size:18px;'>
                        <li>✓ Fewer fals positius (more innocent people freed)</li>
                        <li>✗ More fals negatius (more dangerous people released)</li>
                    </ul>
                </div>
                
                <h3 style='color:#7e22ce;'>La pregunta ètica:</h3>
                <div style='background:#fef2f2; padding:20px; border-radius:8px; border-left:6px solid #dc2626;'>
                    <p style='font-size:20px; font-weight:bold; margin:0;'>
                    Quin error és pitjor?
                    </p>
                    <p style='font-size:18px; margin-top:12px; margin-bottom:0;'>
                    • Mantenir persones innocents a la presó?<br>
                    • O alliberar individus perillosos?
                    </p>
                </div>
                
                <p style='margin-top:24px; font-size:18px;'><b>No hi ha cap "correcta" resposta.</b> 
                Diferents societats, sistemes legals i marcs ètics ponderen aquests compromisos de manera diferent.</p>
                
                <div style='background:#dbeafe; padding:16px; border-radius:8px; margin-top:20px;'>
                    <p style='font-size:18px; margin:0;'><b>This is why understanding UnI is crucial.</b> 
                    Necessitem saber com funcionen aquests sistemes perquè puguem prendre decisions informades sobre quan 
                    i com utilitzar-los.</p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_4_back = gr.Button("◀️ Enrere", size="lg")
                step_4_next = gr.Button("Continue to Learn Unbout UnI ▶️", variant="primary", size="lg")
        
        # Step 5: Completion
        with gr.Column(visible=False) as step_5:
            gr.HTML(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>✅ Secció completada!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        <p>You now understand the consequences of UnI errors in high-stakes decisions.</p>
                        
                        <p style='margin-top:24px;'><b>Següent:</b> Learn what UnI actually is and how these 
                        sistemes de predicció funcionen.</p>
                        
                        <p style='margin-top:24px;'>Aquest coneixement t'ajudarà a entendre com construir 
                        better, more ethical UnI systems.</p>
                        
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 DESPLAÇA'T CAP AVALL 👇</h1>
                        <p style='font-size:1.1rem;'>Troba la següent secció a continuació per continuar el teu viatge.</p>
                    </div>
                </div>
                """
            )
            back_to_dilemma_btn = gr.Button("◀️ Enrere to Review")
        
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
    """Envolcall de conveniència to create and launch the UnI consequences app inline."""
    demo = create_ai_consequences_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio must be installed to launch the UnI consequences app.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

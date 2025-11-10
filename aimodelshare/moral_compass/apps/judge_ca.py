"""
Tu ets el Jutge - Aplicació Gradio per al Repte de Justícia i Equitat (versió catalana).

Aquesta aplicació ensenya:
1. Com prendre decisions basades en prediccions d'IA
2. Els riscos implicats en l'ús d'IA per a decisions de justícia penal
3. La importància d'entendre què es deixa de banda l'IA

Estructura:
- Funció factory `create_judge_app()` retorna un objecte Gradio Blocks
- Envolcall de conveniència `launch_judge_app()` el llança inline (per a notebooks)
"""
import contextlib
import os


def _generate_defendant_profiles():
    """Generar perfils sintètics d'acusats per a l'exercici."""
    import random
    random.seed(42)  # Per a reproductibilitat
    
    profiles = [
        {
            "id": 1,
            "name": "Carles M.",
            "age": 23,
            "gender": "Home",
            "race": "Hispà",
            "prior_offenses": 2,
            "current_charge": "Possessió de drogues",
            "ai_risk": "Alt",
            "ai_confidence": "85%"
        },
        {
            "id": 2,
            "name": "Sara J.",
            "age": 34,
            "gender": "Dona",
            "race": "Blanc",
            "prior_offenses": 0,
            "current_charge": "Robatori",
            "ai_risk": "Baix",
            "ai_confidence": "72%"
        },
        {
            "id": 3,
            "name": "DeShawn W.",
            "age": 19,
            "gender": "Home",
            "race": "Negre",
            "prior_offenses": 1,
            "current_charge": "Agressió",
            "ai_risk": "Mitjà",
            "ai_confidence": "68%"
        },
        {
            "id": 4,
            "name": "Maria R.",
            "age": 41,
            "gender": "Dona",
            "race": "Hispana",
            "prior_offenses": 3,
            "current_charge": "Frau",
            "ai_risk": "Mitjà",
            "ai_confidence": "70%"
        },
        {
            "id": 5,
            "name": "Jaume K.",
            "age": 28,
            "gender": "Home",
            "race": "Blanc",
            "prior_offenses": 5,
            "current_charge": "Robatori amb violència",
            "ai_risk": "Alt",
            "ai_confidence": "91%"
        }
    ]
    
    return profiles


def create_judge_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Crear l'aplicació Gradio Blocks Tu ets el Jutge (encara no llançada)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)

    except ImportError as e:
        raise ImportError(
            "Gradio és necessari per a l'aplicació de jutge. Instal·la-ho amb `pip install gradio`."
        ) from e
    
    profiles = _generate_defendant_profiles()
    
    # Estat per fer seguiment de les decisions
    decisions = {}
    
    def format_profile(profile):
        """Formatar un perfil d'acusat per a la visualització."""
        risk_color = {
            "Alt": "#ef4444",
            "Mitjà": "#f59e0b", 
            "Baix": "#22c55e"
        }
        
        color = risk_color.get(profile["ai_risk"], "#6b7280")
        
        return f"""
        <div style='background:#f9fafb; padding:20px; border-radius:12px; border-left: 6px solid {color};'>
            <h3 style='margin-top:0; color:#1f2937;'>Acusat #{profile['id']}: {profile['name']}</h3>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 16px;'>
                <div><b>Edat:</b> {profile['age']}</div>
                <div><b>Gènere:</b> {profile['gender']}</div>
                <div><b>Raça:</b> {profile['race']}</div>
                <div><b>Delictes anteriors:</b> {profile['prior_offenses']}</div>
                <div style='grid-column: span 2;'><b>Càrrec actual:</b> {profile['current_charge']}</div>
            </div>
            <div style='margin-top:16px; padding:12px; background:white; border-radius:8px;'>
                <b>🤖 Avaluació de risc de l'IA:</b> 
                <span style='color:{color}; font-size:20px; font-weight:bold;'>Risc {profile['ai_risk']}</span>
                <span style='color:#6b7280; margin-left:8px;'>(Confiança: {profile['ai_confidence']})</span>
            </div>
        </div>
        """
    
    def make_decision(defendant_id, decision):
        """Registrar una decisió per a un acusat."""
        decisions[defendant_id] = decision
        return f"✓ Decisió registrada: {decision}"
    
    def get_summary():
        """Obtenir resum de totes les decisions preses."""
        if not decisions:
            return "Encara no s'han pres decisions."
        
        released = sum(1 for d in decisions.values() if d == "Alliberar")
        kept = sum(1 for d in decisions.values() if d == "Mantenir a la presó")
        
        summary = f"""
        <div style='background:#dbeafe; padding:20px; border-radius:12px;'>
            <h3 style='margin-top:0;'>📊 Resum de les teves decisions</h3>
            <div style='font-size:18px;'>
                <p><b>Presoners alliberats:</b> {released} de {len(decisions)}</p>
                <p><b>Presoners mantinguts a la presó:</b> {kept} de {len(decisions)}</p>
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
        gr.Markdown("<h1 style='text-align:center;'>⚖️ Tu ets el Jutge</h1>")
        gr.Markdown(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #fef3c7; border-radius: 12px; border: 2px solid #f59e0b;'>
            <b>El teu rol:</b> Ets un jutge que ha de decidir si alliberar acusats de la presó.<br>
            Un sistema d'IA ha analitzat cada cas i ha proporcionat una avaluació de risc.<br><br>
            <b>La teva tasca:</b> Revisa el perfil de cada acusat i la predicció de l'IA, després pren la teva decisió.
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")
        
        # --- Pantalla de càrrega ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Carregant...</h2>
                </div>
                """
            )
        
        # Introducció
        with gr.Column(visible=True) as intro_section:
            gr.Markdown("<h2 style='text-align:center;'>📋 L'escenari</h2>")
            gr.Markdown(
                """
                <div style='font-size: 18px; background:#e0f2fe; padding:24px; border-radius:12px;'>
                Ets un jutge en un tribunal penal ocupat. A causa del superpoblament a les presons, has de decidir 
                quins acusats poden ser alliberats de manera segura.<br><br>
                
                Per ajudar-te, el tribunal ha implementat un sistema d'IA que prediu el risc de cada 
                acusat de cometre nous delictes si és alliberat. L'IA categoritza els acusats com:<br><br>
                
                <ul style='font-size:18px;'>
                    <li><span style='color:#ef4444; font-weight:bold;'>Risc Alt</span> - Probable que reincideixi</li>
                    <li><span style='color:#f59e0b; font-weight:bold;'>Risc Mitjà</span> - Possibilitat moderada de reincidència</li>
                    <li><span style='color:#22c55e; font-weight:bold;'>Risc Baix</span> - Poc probable que reincideixi</li>
                </ul>
                
                <b>Recorda:</b> Les teves decisions afecten les vides de persones reals i la seguretat pública.
                </div>
                """
            )
            start_btn = gr.Button("Començar a prendre decisions ▶️", variant="primary", size="lg")
        
        # Secció de perfils d'acusats
        with gr.Column(visible=False) as profiles_section:
            gr.Markdown("<h2 style='text-align:center;'>👥 Perfils d'acusats</h2>")
            gr.Markdown(
                """
                <div style='text-align:center; font-size:16px; background:#f3f4f6; padding:12px; border-radius:8px;'>
                Revisa la informació de cada acusat i l'avaluació de risc de l'IA, després pren la teva decisió.
                </div>
                """
            )
            gr.HTML("<br>")
            
            # Crear interfície d'usuari per a cada acusat
            for profile in profiles:
                with gr.Column():
                    gr.HTML(format_profile(profile))
                    
                    with gr.Row():
                        release_btn = gr.Button(
                            "✓ Alliberar presoner", 
                            variant="primary",
                            elem_classes=["decision-button"]
                        )
                        keep_btn = gr.Button(
                            "✗ Mantenir a la presó",
                            variant="secondary",
                            elem_classes=["decision-button"]
                        )
                    
                    decision_status = gr.Markdown("")
                    
                    # Connectar botons
                    release_btn.click(
                        lambda p_id=profile["id"]: make_decision(p_id, "Alliberar"),
                        inputs=None,
                        outputs=decision_status
                    )
                    keep_btn.click(
                        lambda p_id=profile["id"]: make_decision(p_id, "Mantenir a la presó"),
                        inputs=None,
                        outputs=decision_status
                    )
                    
                    gr.HTML("<hr style='margin:24px 0;'>")
            
            # Secció de resum
            summary_display = gr.HTML("")
            show_summary_btn = gr.Button("📊 Mostrar resum de les meves decisions", variant="primary", size="lg")
            show_summary_btn.click(get_summary, inputs=None, outputs=summary_display)
            
            gr.HTML("<br>")
            complete_btn = gr.Button("Completar aquesta secció ▶️", variant="primary", size="lg")
        
        # Secció de finalització
        with gr.Column(visible=False) as complete_section:
            gr.Markdown(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>✅ Decisions completades!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        Has pres les teves decisions basant-te en les recomanacions de l'IA.<br><br>
                        Però aquí està la pregunta crítica:<br><br>
                        <h2 style='color:#dc2626; margin:16px 0;'>Què passa si l'IA estava equivocada?</h2>
                        <p style='font-size:1.1rem;'>
                        Continua a la següent secció a continuació per explorar les conseqüències de 
                        confiar en les prediccions d'IA en situacions d'alt risc.
                        </p>
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 DESPLAÇA'T CAP AVALL 👇</h1>
                        <p style='font-size:1.1rem;'>Troba la següent secció a continuació per continuar el teu viatge.</p>
                        </div>
                </div>
                """
            )
            back_to_profiles_btn = gr.Button("◀️ Tornar a revisar decisions")
        
        # --- LÒGICA DE NAVEGACIÓ (BASADA EN GENERADOR) ---
        
        # Aquesta llista s'ha de definir *després* de tots els components
        all_steps = [intro_section, profiles_section, complete_section, loading_screen]

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
    """Envolcall de conveniència per crear i llançar l'aplicació de jutge inline."""
    demo = create_judge_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio ha d'estar instal·lat per llançar l'aplicació de jutge.") from e
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

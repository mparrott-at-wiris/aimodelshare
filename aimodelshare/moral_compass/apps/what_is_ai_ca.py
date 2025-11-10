"""
Què és l'IA - Aplicació Gradio per al Repte de Justícia i Equitat (versió catalana).

Aquesta aplicació ensenya:
1. Una explicació simple i no tècnica del que és l'IA
2. Com funcionen els models predictius (Entrada → Model → Sortida)
3. Exemples del món real i connexions amb el repte de justícia

Estructura:
- Funció factory `create_what_is_ai_app()` retorna un objecte Gradio Blocks
- Envolcall de conveniència `launch_what_is_ai_app()` el llança inline (per a notebooks)
"""
import contextlib
import os

def _create_simple_predictor():
    """Crear un predictor de demostració simple amb finalitats didàctiques."""
    def predict_outcome(age, priors, severity):
        """Predictor simple basat en regles per a demostració."""
        
        
        # Lògica simple de puntuació per a demostració
        score = 0
        
        # Factor d'edat (més jove = major risc en aquest model simple)
        if age < 25:
            score += 3
        elif age < 35:
            score += 2
        else:
            score += 1
        
        # Factor de delictes anteriors
        if priors >= 3:
            score += 3
        elif priors >= 1:
            score += 2
        else:
            score += 0
        
        # Factor de gravetat
        severity_map = {"Menor": 1, "Moderat": 2, "Greu": 3}
        score += severity_map.get(severity, 2)
        
        # Determinar nivell de risc
        if score >= 7:
            risk = "Risc Alt"
            color = "#dc2626"
            emoji = "🔴"
        elif score >= 4:
            risk = "Risc Mitjà"
            color = "#f59e0b"
            emoji = "🟡"
        else:
            risk = "Risc Baix"
            color = "#16a34a"
            emoji = "🟢"
        
        return f"""
        <div style='background:white; padding:24px; border-radius:12px; border:3px solid {color}; text-align:center;'>
            <h2 style='color:{color}; margin:0; font-size:2.5rem;'>{emoji} {risk}</h2>
            <p style='font-size:18px; color:#6b7280; margin-top:12px;'>Puntuació de risc: {score}/9</p>
        </div>
        """
    
    return predict_outcome


def create_what_is_ai_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Crear l'aplicació Gradio Blocks Què és l'IA (encara no llançada)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)

    except ImportError as e:
        raise ImportError(
            "Gradio és necessari per a l'aplicació què és l'IA. Instal·la-ho amb `pip install gradio`."
        ) from e
    
    predict_outcome = _create_simple_predictor()
    
    css = """
    .large-text {
        font-size: 20px !important;
    }
    """
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue), css=css) as demo:
        gr.Markdown("<h1 style='text-align:center;'>🤖 Què és l'IA, doncs?</h1>")
        gr.HTML(
            """
            <div style='text-align:center; font-size:18px; max-width: 900px; margin: auto;
                        padding: 20px; background-color: #e0e7ff; border-radius: 12px; border: 2px solid #6366f1;'>
            Abans de poder construir millors sistemes d'IA, necessites entendre què és realment l'IA.<br>
            No et preocupis - ho explicarem en termes simples i quotidians!
            </div>
            """
        )
        gr.HTML("<hr style='margin:24px 0;'>")
        
        # --- Aquesta és la nova pantalla de càrrega ---
        with gr.Column(visible=False) as loading_screen:
            gr.Markdown(
                """
                <div style='text-align:center; padding: 100px 0;'>
                    <h2 style='font-size: 2rem; color: #6b7280;'>⏳ Carregant...</h2>
                </div>
                """
            )
        
        # Pas 1: Introducció
        with gr.Column(visible=True) as step_1:
            gr.Markdown("<h2 style='text-align:center;'>🎯 Una definició simple</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#dbeafe; padding:28px; border-radius:16px;'>
                <p><b style='font-size:24px;'>Intel·ligència Artificial (IA) és només un nom sofisticat per a:</b></p>
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0; border:3px solid #0284c7;'>
                    <h2 style='text-align:center; color:#0284c7; margin:0; font-size:2rem;'>
                    Un sistema que fa prediccions basades en patrons
                    </h2>
                </div>
                <p>Això és tot! Desglossem què significa això...</p>
                <h3 style='color:#0369a1; margin-top:24px;'>Pensa en com TU fas prediccions:</h3>
                <ul style='font-size:19px; margin-top:12px;'>
                    <li><b>Temps:</b> Núvols foscos → Prediueixes pluja → Portes paraigua</li>
                    <li><b>Trànsit:</b> Hora punta → Prediueixes congestió → Surts aviat</li>
                    <li><b>Pel·lícules:</b> Actor que t'agrada → Prediueixes que gaudiràs → La veus</li>
                </ul>
                <div style='background:#fef3c7; padding:20px; border-radius:8px; margin-top:24px; border-left:6px solid #f59e0b;'>
                    <p style='font-size:18px; margin:0;'><b>L'IA fa el mateix, però utilitzant dades i matemàtiques 
                    en lloc d'experiència i intuïció humana.</b></p>
                </div>
                </div>
                """
            )
            step_1_next = gr.Button("Següent: La fórmula de l'IA ▶️", variant="primary", size="lg")
        
        # Pas 2: La fórmula de tres parts
        with gr.Column(visible=False) as step_2:
            gr.Markdown("<h2 style='text-align:center;'>📐 La fórmula de tres parts</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#f0fdf4; padding:28px; border-radius:16px;'>
                <p>Tots els sistemes d'IA funcionen de la mateixa manera, seguint aquesta fórmula simple:</p>
                <div style='background:white; padding:32px; border-radius:12px; margin:24px 0; text-align:center;'>
                    <div style='display:inline-block; background:#dbeafe; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#0369a1;'>1️⃣ ENTRADA</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>Les dades entren</p>
                    </div>
                    <div style='display:inline-block; font-size:2rem; margin:0 16px; color:#6b7280;'>→</div>
                    <div style='display:inline-block; background:#fef3c7; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#92400e;'>2️⃣ MODEL</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>L'IA les processa</p>
                    </div>
                    <div style='display:inline-block; font-size:2rem; margin:0 16px; color:#6b7280;'>→</div>
                    <div style='display:inline-block; background:#f0fdf4; padding:16px 24px; border-radius:8px; margin:8px;'>
                        <h3 style='margin:0; color:#15803d;'>3️⃣ SORTIDA</h3>
                        <p style='margin:8px 0 0 0; font-size:16px;'>La predicció surt</p>
                    </div>
                </div>
                <h3 style='color:#15803d; margin-top:32px;'>Exemples del món real:</h3>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Entrada:</b> Foto d'un gos<br>
                    <b style='color:#92400e;'>Model:</b> IA de reconeixement d'imatges<br>
                    <b style='color:#15803d;'>Sortida:</b> "Això és un Golden Retriever"
                    </p>
                </div>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Entrada:</b> "Quin temps fa?"<br>
                    <b style='color:#92400e;'>Model:</b> IA de llenguatge (com ChatGPT)<br>
                    <b style='color:#15803d;'>Sortida:</b> Una resposta útil
                    </p>
                </div>
                <div style='background:white; padding:20px; border-radius:8px; margin:16px 0;'>
                    <p style='margin:0; font-size:18px;'>
                    <b style='color:#0369a1;'>Entrada:</b> Historial criminal d'una persona<br>
                    <b style='color:#92400e;'>Model:</b> Algoritme d'avaluació de risc<br>
                    <b style='color:#15803d;'>Sortida:</b> "Risc Alt" o "Risc Baix"
                    </p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_2_back = gr.Button("◀️ Enrere", size="lg")
                step_2_next = gr.Button("Següent: Com aprenen els models ▶️", variant="primary", size="lg")
        
        # Pas 3: Com aprenen els models (Versió més curta - Introducció directa)
        with gr.Column(visible=False) as step_3:
            gr.Markdown("<h2 style='text-align:center;'>🧠 Com aprèn un model d'IA?</h2>")
            
            gr.HTML(
                """
                <div style='font-size: 19px; background:#fef3c7; padding:28px; border-radius:16px;'>
                
                <h3 style='color:#92400e; margin-top:0;'>1. Aprèn d'exemples</h3>
                
                <p>Un model d'IA no està programat amb respostes. En canvi, s'entrena amb un gran nombre d'exemples, i aprèn a trobar les respostes per si mateix.</p>
                <p>En el nostre escenari de justícia, això significa alimentar el model amb milers de casos passats (<b>exemples</b>) per ensenyar-li a trobar els <b>patrons</b> que connecten els detalls d'una persona amb la probabilitat de reincidència.</p>
                
                <hr style='margin:24px 0;'>
                
                <h3 style='color:#92400e;'>2. El procés d'entrenament</h3>
                <p>L'IA "s'entrena" buclejant a través de dades històriques (casos passats) milions de vegades:</p>
                
                <div style='margin:24px 0; padding:20px; background:#fff; border-radius:8px;'>
                    <div style='display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap;'>
                        <div style='background:#dbeafe; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#0369a1;'>1. ENTRADA<br>EXEMPLES</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>2. MODEL<br>ENDEVINA</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>3. COMPROVAR<br>RESPOSTA</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#fef3c7; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#92400e;'>4. AJUSTAR<br>PESOS</b>
                        </div>
                        <div style='font-size:1.5rem; margin:0 8px; color:#6b7280;'>→</div>
                        <div style='background:#f0fdf4; padding:12px 16px; border-radius:8px; margin:8px; flex:1; min-width:140px; text-align:center;'>
                            <b style='color:#15803d;'>MODEL<br>APRÈS</b>
                        </div>
                    </div>
                </div>
                
                <p style='margin-top:20px;'>Durant el pas d'"<b>Ajustar</b>", el model canvia les seves regles internes (anomenades <b>"pesos"</b>) per apropar-se a la resposta correcta. 
                   Per exemple, aprèn <b>quant</b> haurien d'importar més els "delictes anteriors" que l'"edat".</p>
                
                <hr style='margin:24px 0;'>

                <h3 style='color:#dc2626;'>⚠️ El repte ètic</h3>
                <div style='font-size: 18px; background:#fef2f2; padding:24px; border-radius:12px; border-left:6px solid #dc2626;'>
                    <p style='margin:0;'><b>Aquí està el problema crític:</b> El model *només* aprèn de les dades.
                    Si les dades històriques tenen biaix (per exemple, certs grups van ser arrestats més sovint), 
                    el model aprendrà aquests patrons esbiaixats.
                    <br><br>
                    <b>El model no coneix "equitat" o "justícia", només coneix patrons.</b>
                    </p>
                </div>

                </div>
            """
            )
            
            with gr.Row():
                step_3_back = gr.Button("◀️ Enrere", size="lg")
                step_3_next = gr.Button("Següent: Prova-ho tu mateix ▶️", variant="primary", size="lg")
        
        # Pas 4: Demostració interactiva
        with gr.Column(visible=False) as step_4:
            gr.Markdown("<h2 style='text-align:center;'>🎮 Prova-ho tu mateix!</h2>")
            gr.Markdown(
                """
                <div style='font-size: 18px; background:#fef3c7; padding:24px; border-radius:12px; text-align:center;'>
                <p style='margin:0;'><b>Utilitzem un model d'IA simple per predir el risc criminal.</b><br>
                Ajusta les entrades a continuació i veu com canvia la predicció del model!</p>
                </div>
                """
            )
            gr.HTML("<br>")
            
            gr.Markdown("<h3 style='text-align:center; color:#0369a1;'>1️⃣ ENTRADA: Ajusta les dades</h3>")
            
            with gr.Row():
                age_slider = gr.Slider(
                    minimum=18, 
                    maximum=65, 
                    value=25, 
                    step=1, 
                    label="Edat",
                    info="Edat de l'acusat"
                )
                priors_slider = gr.Slider(
                    minimum=0, 
                    maximum=10, 
                    value=2, 
                    step=1, 
                    label="Delictes anteriors",
                    info="Nombre de delictes anteriors"
                )
            
            severity_dropdown = gr.Dropdown(
                choices=["Menor", "Moderat", "Greu"],
                value="Moderat",
                label="Gravetat del càrrec actual",
                info="Quina gravetat té el càrrec actual?"
            )
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown("<h3 style='text-align:center; color:#92400e;'>2️⃣ MODEL: Processar les dades</h3>")
            
            predict_btn = gr.Button("🔮 Executar predicció d'IA", variant="primary", size="lg")
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown("<h3 style='text-align:center; color:#15803d;'>3️⃣ SORTIDA: Veu la predicció</h3>")
            
            prediction_output = gr.HTML(
                """
                <div style='background:#f3f4f6; padding:40px; border-radius:12px; text-align:center;'>
                    <p style='color:#6b7280; font-size:18px; margin:0;'>
                    Fes clic a "Executar predicció d'IA" a dalt per veure el resultat
                    </p>
                </div>
                """
            )
            
            gr.HTML("<hr style='margin:24px 0;'>")
            
            gr.Markdown(
                """
                <div style='background:#e0f2fe; padding:20px; border-radius:12px; font-size:18px;'>
                <b>El que acabes de fer:</b><br><br>
                Has utilitzat un model d'IA molt simple! Has proporcionat <b style='color:#0369a1;'>dades d'entrada</b> 
                (edat, delictes anteriors, gravetat), el <b style='color:#92400e;'>model les ha processat</b> utilitzant regles 
                i patrons, i ha produït una <b style='color:#15803d;'>predicció de sortida</b>.<br><br>
                Els models d'IA reals són més complexos, però funcionen amb el mateix principi!
                </div>
                """
            )
            
            with gr.Row():
                step_4_back = gr.Button("◀️ Enrere", size="lg")
                step_4_next = gr.Button("Següent: Connexió amb la justícia ▶️", variant="primary", size="lg")
        
        # Pas 5: Connexió amb el repte
        with gr.Column(visible=False) as step_5:
            gr.Markdown("<h2 style='text-align:center;'>🔗 Connexió amb la justícia penal</h2>")
            gr.HTML(
                """
                <div style='font-size: 20px; background:#faf5ff; padding:28px; border-radius:16px;'>
                <p><b>Recordes la predicció de risc que vas utilitzar abans com a jutge?</b></p>
                
                <p style='margin-top:20px;'>Aquest era un exemple real d'IA en acció:</p>
                
                <div style='background:white; padding:24px; border-radius:12px; margin:24px 0; border:3px solid #9333ea;'>
                    <p style='font-size:18px; margin-bottom:16px;'>
                    <b style='color:#0369a1;'>ENTRADA:</b> Informació de l'acusat<br>
                    <span style='margin-left:24px; color:#6b7280;'>• Edat, raça, gènere, delictes anteriors, detalls del càrrec</span>
                    </p>
                    
                    <p style='font-size:18px; margin:16px 0;'>
                    <b style='color:#92400e;'>MODEL:</b> Algoritme d'avaluació de risc<br>
                    <span style='margin-left:24px; color:#6b7280;'>• Entrenat amb dades de justícia penal històriques</span><br>
                    <span style='margin-left:24px; color:#6b7280;'>• Cerca patrons en qui va reincidir en el passat</span>
                    </p>
                    
                    <p style='font-size:18px; margin-top:16px; margin-bottom:0;'>
                    <b style='color:#15803d;'>SORTIDA:</b> Predicció de risc<br>
                    <span style='margin-left:24px; color:#6b7280;'>• "Risc Alt", "Risc Mitjà" o "Risc Baix"</span>
                    </p>
                </div>
                
                <h3 style='color:#7e22ce; margin-top:32px;'>Per què això importa per a l'ètica:</h3>
                
                <div style='background:#fef2f2; padding:20px; border-radius:8px; margin-top:16px; border-left:6px solid #dc2626;'>
                    <ul style='font-size:18px; margin:8px 0;'>
                        <li>Les <b>dades d'entrada</b> poden contenir biaixos històrics</li>
                        <li>El <b>model</b> aprèn patrons de decisions potencialment injustes del passat</li>
                        <li>Les <b>prediccions de sortida</b> poden perpetuar la discriminació</li>
                    </ul>
                </div>
                
                <div style='background:#dbeafe; padding:20px; border-radius:8px; margin-top:24px;'>
                    <p style='font-size:18px; margin:0;'>
                    <b>Entendre com funciona l'IA és el primer pas per construir sistemes més justos.</b><br><br>
                    Ara que saps què és l'IA, estàs preparat per ajudar a dissenyar millors models que 
                    siguin més ètics i menys esbiaixats!
                    </p>
                </div>
                </div>
                """
            )
            with gr.Row():
                step_5_back = gr.Button("◀️ Enrere", size="lg")
                step_5_next = gr.Button("Completar aquesta secció ▶️", variant="primary", size="lg")
        
        # Pas 6: Finalització
        with gr.Column(visible=False) as step_6:
            gr.HTML(
                """
                <div style='text-align:center;'>
                    <h2 style='font-size: 2.5rem;'>🎓 Ara entens l'IA!</h2>
                    <div style='font-size: 1.3rem; background:#e0f2fe; padding:28px; border-radius:16px;
                                border: 2px solid #0284c7;'>
                        <p><b>Felicitats!</b> Ara saps:</p>
                        
                        <ul style='font-size:1.1rem; text-align:left; max-width:600px; margin:20px auto;'>
                            <li>Què és l'IA (un sistema de predicció)</li>
                            <li>Com funciona (Entrada → Model → Sortida)</li>
                            <li>Com aprenen els models d'IA de les dades</li>
                            <li>Per què importa per a la justícia penal</li>
                            <li>Les implicacions ètiques de les decisions d'IA</li>
                        </ul>
                        
                        <p style='margin-top:32px;'><b>Pròxims passos:</b></p>
                        <p>En les seccions següents, aprendràs com construir i millorar models d'IA 
                        per fer-los més justos i ètics.</p>
                        
                        <h1 style='margin:20px 0; font-size: 3rem;'>👇 DESPLAÇA'T CAP AVALL 👇</h1>
                        <p style='font-size:1.1rem;'>Continua a la següent secció a continuació.</p>
                    </div>
                </div>
                """
            )
            back_to_connection_btn = gr.Button("◀️ Tornar a revisar")
        
        
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
    """Envolcall de conveniència per crear i llançar l'aplicació què és l'IA inline."""
    demo = create_what_is_ai_app()
    try:
        import gradio as gr  # noqa: F401
    except ImportError as e:
        raise ImportError("Gradio ha d'estar instal·lat per llançar l'aplicació què és l'IA.") from e
    
    # Aquest és l'envolcall original, dissenyat per a ús en un notebook (com Colab)
    with contextlib.redirect_stdout(open(os.devnull, 'w')), contextlib.redirect_stderr(open(os.devnull, 'w')):
        demo.launch(share=share, inline=True, debug=debug, height=height)

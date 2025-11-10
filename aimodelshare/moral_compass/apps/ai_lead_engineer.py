"""
AI Lead Engineer - Gradio application for building ML models on COMPAS dataset.

This app enables low-tech classroom users to:
1. Select model type from sklearn, Keras, or PyTorch families
2. Configure feature groups and complexity levels
3. Assign team names for leaderboard tracking
4. Train and submit models to playground competitions
5. View leaderboard results

All models run CPU-only to ensure accessibility.

Structure:
- Factory function `create_ai_lead_engineer_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_ai_lead_engineer_app()` launches it inline (for notebooks)
"""

import os
import numpy as np
import pandas as pd


# Model options registry - curated subset for performance
MODEL_OPTIONS = {
    "sklearn": {
        "LogisticRegression": {
            "display_name": "Logistic Regression",
            "description": "Linear model for binary classification",
            "complexity_params": {
                1: {"max_iter": 100, "C": 1.0},
                2: {"max_iter": 200, "C": 1.0},
                3: {"max_iter": 500, "C": 0.5},
                4: {"max_iter": 800, "C": 0.1},
                5: {"max_iter": 1000, "C": 0.01}
            }
        },
        "RandomForest": {
            "display_name": "Random Forest",
            "description": "Ensemble of decision trees",
            "complexity_params": {
                1: {"n_estimators": 10, "max_depth": 3},
                2: {"n_estimators": 25, "max_depth": 5},
                3: {"n_estimators": 50, "max_depth": 10},
                4: {"n_estimators": 75, "max_depth": 15},
                5: {"n_estimators": 100, "max_depth": None}
            }
        },
        "GradientBoosting": {
            "display_name": "Gradient Boosting",
            "description": "Sequential ensemble learning",
            "complexity_params": {
                1: {"n_estimators": 10, "max_depth": 2, "learning_rate": 0.1},
                2: {"n_estimators": 25, "max_depth": 3, "learning_rate": 0.1},
                3: {"n_estimators": 50, "max_depth": 4, "learning_rate": 0.1},
                4: {"n_estimators": 75, "max_depth": 5, "learning_rate": 0.05},
                5: {"n_estimators": 100, "max_depth": 6, "learning_rate": 0.05}
            }
        },
        "MultinomialNB": {
            "display_name": "Naive Bayes (Multinomial)",
            "description": "Probabilistic classifier",
            "complexity_params": {
                1: {"alpha": 1.0},
                2: {"alpha": 0.5},
                3: {"alpha": 0.1},
                4: {"alpha": 0.01},
                5: {"alpha": 0.001}
            },
            "requires_minmax": True
        }
    },
    "keras": {
        "SimpleDense": {
            "display_name": "Simple Neural Network",
            "description": "Basic feedforward network",
            "complexity_params": {
                1: {"layers": [32], "epochs": 5},
                2: {"layers": [64], "epochs": 8},
                3: {"layers": [64, 32], "epochs": 10},
                4: {"layers": [128, 64], "epochs": 12},
                5: {"layers": [128, 64, 32], "epochs": 15}
            }
        },
        "DenseWithDropout": {
            "display_name": "Neural Network with Dropout",
            "description": "Network with regularization",
            "complexity_params": {
                1: {"layers": [32], "dropout": 0.2, "epochs": 5},
                2: {"layers": [64], "dropout": 0.3, "epochs": 8},
                3: {"layers": [64, 32], "dropout": 0.3, "epochs": 10},
                4: {"layers": [128, 64], "dropout": 0.4, "epochs": 12},
                5: {"layers": [128, 64, 32], "dropout": 0.5, "epochs": 15}
            }
        }
    },
    "pytorch": {
        "MLPBasic": {
            "display_name": "Basic PyTorch MLP",
            "description": "Multi-layer perceptron",
            "complexity_params": {
                1: {"hidden_sizes": [32], "epochs": 5},
                2: {"hidden_sizes": [64], "epochs": 8},
                3: {"hidden_sizes": [64, 32], "epochs": 10},
                4: {"hidden_sizes": [128, 64], "epochs": 12},
                5: {"hidden_sizes": [128, 64, 32], "epochs": 15}
            }
        }
    }
}


def _enforce_cpu_only():
    """Enforce CPU-only execution for TensorFlow and PyTorch."""
    # TensorFlow: disable GPU visibility
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    
    # For PyTorch, no special action needed - torch.device('cpu') is default


def _build_sklearn_model(model_key, complexity, preprocessed_data, y_train, use_minmax=False):
    """Build and train an sklearn model."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.naive_bayes import MultinomialNB
    
    model_config = MODEL_OPTIONS["sklearn"][model_key]
    params = model_config["complexity_params"][complexity]
    
    if model_key == "LogisticRegression":
        model = LogisticRegression(
            max_iter=params["max_iter"],
            C=params["C"],
            random_state=42,
            class_weight='balanced'
        )
    elif model_key == "RandomForest":
        model = RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            random_state=42,
            class_weight='balanced'
        )
    elif model_key == "GradientBoosting":
        model = GradientBoostingClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            random_state=42
        )
    elif model_key == "MultinomialNB":
        model = MultinomialNB(alpha=params["alpha"])
    else:
        raise ValueError(f"Unknown model key: {model_key}")
    
    model.fit(preprocessed_data, y_train)
    return model


def _build_keras_model(model_key, complexity, input_dim, preprocessed_data, y_train):
    """Build and train a Keras model with CPU enforcement."""
    import tensorflow as tf
    from tensorflow.keras import layers, Sequential
    
    # Enforce CPU
    _enforce_cpu_only()
    tf.config.set_visible_devices([], 'GPU')
    
    model_config = MODEL_OPTIONS["keras"][model_key]
    params = model_config["complexity_params"][complexity]
    
    model = Sequential()
    model.add(layers.Input(shape=(input_dim,)))
    
    for layer_size in params["layers"]:
        model.add(layers.Dense(layer_size, activation='relu'))
        if "dropout" in params:
            model.add(layers.Dropout(params["dropout"]))
    
    model.add(layers.Dense(1, activation='sigmoid'))
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    
    # Train
    model.fit(
        preprocessed_data, y_train,
        epochs=params["epochs"],
        batch_size=64,
        verbose=0,
        validation_split=0.1
    )
    
    return model


def _build_pytorch_model(model_key, complexity, input_dim, preprocessed_data, y_train):
    """Build and train a PyTorch model (CPU only)."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    
    model_config = MODEL_OPTIONS["pytorch"][model_key]
    params = model_config["complexity_params"][complexity]
    
    class DynamicMLP(nn.Module):
        def __init__(self, input_size, hidden_sizes):
            super().__init__()
            self.layers = nn.ModuleList()
            
            prev_size = input_size
            for hidden_size in hidden_sizes:
                self.layers.append(nn.Linear(prev_size, hidden_size))
                prev_size = hidden_size
            
            self.output = nn.Linear(prev_size, 1)
        
        def forward(self, x):
            for layer in self.layers:
                x = F.relu(layer(x))
            x = self.output(x)
            return x
    
    model = DynamicMLP(input_dim, params["hidden_sizes"])
    
    # Convert to tensors (CPU)
    X_train_tensor = torch.FloatTensor(preprocessed_data)
    y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
    
    # Setup training
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Create dataset and dataloader
    dataset = torch.utils.data.TensorDataset(X_train_tensor, y_train_tensor)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)
    
    # Training loop
    model.train()
    for epoch in range(params["epochs"]):
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
    
    return model


def _generate_predictions(model, model_family, preprocessed_test_data):
    """Generate predictions from a trained model."""
    if model_family == "sklearn":
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(preprocessed_test_data)[:, 1]
            preds = (proba >= 0.5).astype(int)
        else:
            preds = model.predict(preprocessed_test_data)
    
    elif model_family == "keras":
        proba = model.predict(preprocessed_test_data, verbose=0).flatten()
        preds = (proba >= 0.5).astype(int)
    
    elif model_family == "pytorch":
        import torch
        model.eval()
        with torch.no_grad():
            X_test_tensor = torch.FloatTensor(preprocessed_test_data)
            logits = model(X_test_tensor)
            proba = torch.sigmoid(logits).numpy().flatten()
            preds = (proba >= 0.5).astype(int)
    
    return preds


def _create_tags(model_family, model_key, complexity, team_name):
    """Create tags for model submission."""
    team_slug = team_name.lower().replace(" ", "_") if team_name else "no_team"
    tags = f"etica_tech_challenge,{model_family},{model_key},complexity_{complexity},team_{team_slug}"
    return tags


def _fetch_leaderboard(playground):
    """Fetch and format leaderboard data."""
    try:
        data = playground.get_leaderboard()
        
        if isinstance(data, dict):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            return "Could not retrieve leaderboard data."
        
        if df.empty:
            return "No submissions yet. Be the first to submit a model!"
        
        # Format for display
        display_cols = []
        if 'model_name' in df.columns:
            display_cols.append('model_name')
        if 'tags' in df.columns:
            display_cols.append('tags')
        if 'accuracy' in df.columns:
            display_cols.append('accuracy')
        if 'custom_metadata' in df.columns:
            display_cols.append('custom_metadata')
        
        if display_cols:
            display_df = df[display_cols].head(20)
            return display_df.to_markdown(index=False)
        else:
            return df.head(20).to_markdown(index=False)
    
    except Exception as e:
        return f"Error fetching leaderboard: {str(e)}"


def create_ai_lead_engineer_app(
    playground=None,
    X_train=None,
    X_test=None,
    y_train=None,
    y_test=None,
    preprocessor=None,
    minmax_preprocessor=None,
    theme_primary_hue: str = "blue"
) -> "gr.Blocks":
    """
    Create the AI Lead Engineer Gradio Blocks app.
    
    Parameters
    ----------
    playground : ModelPlayground, optional
        Pre-configured playground instance. If None, app will run in local-only mode.
    X_train : array-like, optional
        Training features
    X_test : array-like, optional
        Test features
    y_train : array-like, optional
        Training labels
    y_test : array-like, optional
        Test labels (for local evaluation)
    preprocessor : sklearn preprocessor, optional
        Standard preprocessor (StandardScaler-based)
    minmax_preprocessor : sklearn preprocessor, optional
        MinMax preprocessor for MultinomialNB
    theme_primary_hue : str, default="blue"
        Primary color hue for the Gradio theme
    
    Returns
    -------
    gr.Blocks
        Gradio Blocks app instance (not launched)
    """
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the AI Lead Engineer app. "
            "Install with `pip install gradio`."
        ) from e
    
    # Check if we have required data
    has_data = all([
        X_train is not None,
        X_test is not None,
        y_train is not None,
        preprocessor is not None
    ])
    
    has_playground = playground is not None
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue=theme_primary_hue)) as demo:
        gr.Markdown("# 🤖 AI Lead Engineer")
        gr.Markdown(
            """
            Build and submit machine learning models for the Ètica en Joc Justice Challenge!
            
            **Your Mission:** Select a model type, configure its complexity, and train it on the COMPAS dataset.
            """
        )
        
        if not has_data:
            gr.Markdown(
                """
                ⚠️ **No data provided.** This app requires training data to function.
                Please provide `X_train`, `X_test`, `y_train`, and `preprocessor` when creating the app.
                """
            )
            return demo
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Model Configuration")
                
                model_family = gr.Dropdown(
                    choices=["sklearn", "keras", "pytorch"],
                    value="sklearn",
                    label="Model Family",
                    info="Choose your ML framework"
                )
                
                model_type = gr.Dropdown(
                    choices=list(MODEL_OPTIONS["sklearn"].keys()),
                    value="LogisticRegression",
                    label="Model Type",
                    info="Specific algorithm"
                )
                
                complexity = gr.Slider(
                    minimum=1,
                    maximum=5,
                    step=1,
                    value=2,
                    label="Complexity Level",
                    info="1 = Simple, 5 = Complex"
                )
                
                username = gr.Textbox(
                    label="Your Name",
                    placeholder="Enter your name",
                    value="Student"
                )
                
                team_name = gr.Textbox(
                    label="Team Name",
                    placeholder="Enter your team name",
                    value="Team Alpha"
                )
                
                train_button = gr.Button("🚀 Train & Submit Model", variant="primary")
            
            with gr.Column(scale=2):
                gr.Markdown("### Results")
                
                output_status = gr.Textbox(
                    label="Status",
                    lines=3,
                    interactive=False
                )
                
                model_info = gr.Textbox(
                    label="Model Information",
                    lines=5,
                    interactive=False
                )
                
                if has_playground:
                    gr.Markdown("### Leaderboard")
                    leaderboard_display = gr.Markdown(value="Click 'Refresh Leaderboard' to view submissions")
                    refresh_button = gr.Button("🔄 Refresh Leaderboard")
        
        def update_model_choices(family):
            """Update model type choices based on selected family."""
            choices = list(MODEL_OPTIONS[family].keys())
            return gr.Dropdown(choices=choices, value=choices[0])
        
        def train_and_submit(family, model_key, complexity_level, user, team):
            """Train model and submit to playground."""
            try:
                # Get model config
                model_config = MODEL_OPTIONS[family][model_key]
                use_minmax = model_config.get("requires_minmax", False)
                
                # Select preprocessor
                if use_minmax and minmax_preprocessor is not None:
                    prep = minmax_preprocessor
                    prep_func = lambda x: minmax_preprocessor.transform(x)
                else:
                    prep = preprocessor
                    prep_func = lambda x: preprocessor.transform(x)
                
                # Preprocess data
                X_train_processed = prep_func(X_train)
                X_test_processed = prep_func(X_test)
                input_dim = X_train_processed.shape[1]
                
                status_msg = f"Training {model_config['display_name']} (complexity {complexity_level})...\n"
                
                # Train model
                if family == "sklearn":
                    model = _build_sklearn_model(
                        model_key, complexity_level, 
                        X_train_processed, y_train, use_minmax
                    )
                elif family == "keras":
                    model = _build_keras_model(
                        model_key, complexity_level, input_dim,
                        X_train_processed, y_train
                    )
                elif family == "pytorch":
                    model = _build_pytorch_model(
                        model_key, complexity_level, input_dim,
                        X_train_processed, y_train
                    )
                else:
                    return "Error: Unknown model family", ""
                
                status_msg += "✓ Model trained successfully!\n"
                
                # Generate predictions
                preds = _generate_predictions(model, family, X_test_processed)
                
                # Calculate local accuracy (if y_test provided)
                if y_test is not None:
                    from sklearn.metrics import accuracy_score
                    accuracy = accuracy_score(y_test, preds)
                    status_msg += f"✓ Local accuracy: {accuracy:.4f}\n"
                
                # Prepare submission
                tags = _create_tags(family, model_key, complexity_level, team)
                description = f"{user}'s {model_config['display_name']} (complexity {complexity_level})"
                
                # Submit to playground if available
                if has_playground:
                    try:
                        input_dict = {
                            'description': description,
                            'tags': tags
                        }
                        
                        custom_metadata = {
                            'username': user,
                            'team': team,
                            'complexity': complexity_level,
                            'model_family': family,
                            'model_type': model_key
                        }
                        
                        # For PyTorch, need dummy input for ONNX
                        if family == "pytorch":
                            import torch
                            dummy_input = torch.zeros((1, input_dim), dtype=torch.float32)
                            playground.submit_model(
                                model=model,
                                preprocessor=prep,
                                prediction_submission=preds,
                                input_dict=input_dict,
                                submission_type='competition',
                                model_input=dummy_input,
                                custom_metadata=custom_metadata
                            )
                        else:
                            playground.submit_model(
                                model=model,
                                preprocessor=prep,
                                prediction_submission=preds,
                                input_dict=input_dict,
                                submission_type='competition',
                                custom_metadata=custom_metadata
                            )
                        
                        status_msg += "✓ Model submitted to playground!\n"
                    except Exception as e:
                        status_msg += f"⚠ Submission failed: {str(e)}\n"
                        status_msg += "Model trained locally but not submitted.\n"
                else:
                    status_msg += "ℹ No playground configured - local evaluation only.\n"
                
                # Build model info
                info = f"**Model Family:** {family}\n"
                info += f"**Model Type:** {model_config['display_name']}\n"
                info += f"**Complexity:** {complexity_level}\n"
                info += f"**Description:** {model_config['description']}\n"
                info += f"**Tags:** {tags}\n"
                info += f"**Team:** {team}\n"
                
                return status_msg, info
            
            except Exception as e:
                import traceback
                error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
                return error_msg, ""
        
        def refresh_leaderboard_data():
            """Refresh leaderboard display."""
            if not has_playground:
                return "No playground configured."
            return _fetch_leaderboard(playground)
        
        # Wire up event handlers
        model_family.change(
            fn=update_model_choices,
            inputs=[model_family],
            outputs=[model_type]
        )
        
        train_button.click(
            fn=train_and_submit,
            inputs=[model_family, model_type, complexity, username, team_name],
            outputs=[output_status, model_info]
        )
        
        if has_playground:
            refresh_button.click(
                fn=refresh_leaderboard_data,
                outputs=[leaderboard_display]
            )
    
    return demo


def launch_ai_lead_engineer_app(
    playground=None,
    X_train=None,
    X_test=None,
    y_train=None,
    y_test=None,
    preprocessor=None,
    minmax_preprocessor=None,
    **kwargs
):
    """
    Convenience wrapper to create and launch the AI Lead Engineer app.
    
    Parameters
    ----------
    playground : ModelPlayground, optional
        Pre-configured playground instance
    X_train, X_test, y_train, y_test : array-like
        Training and test data
    preprocessor : sklearn preprocessor
        Standard preprocessor
    minmax_preprocessor : sklearn preprocessor, optional
        MinMax preprocessor for MultinomialNB
    **kwargs : dict
        Additional arguments passed to Gradio's launch() method
    """
    app = create_ai_lead_engineer_app(
        playground=playground,
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        preprocessor=preprocessor,
        minmax_preprocessor=minmax_preprocessor
    )
    app.launch(**kwargs)

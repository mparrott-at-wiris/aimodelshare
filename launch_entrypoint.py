import os
import logging
import sys
import traceback
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("launcher")

# Map app-name (from APP_NAME env var) to factory function name
# Uses create_* factories which are lazily imported from apps module
APP_NAME_TO_FACTORY = {
    "tutorial": "create_tutorial_app",
    "judge": "create_judge_app",
    "ai-consequences": "create_ai_consequences_app",
    "what-is-ai": "create_what_is_ai_app",
    "model-building-game": "launch_model_building_game_app",
    "ethical-revelation": "create_ethical_revelation_app",
    "moral-compass-challenge": "create_moral_compass_challenge_app",
    "bias-detective": "create_bias_detective_app",
    "fairness-fixer": "create_fairness_fixer_app",
    "justice-equity-upgrade": "create_justice_equity_upgrade_app",
}

def load_factory(app_name: str):
    """Load the factory function for the given app name using lazy imports."""
    if app_name not in APP_NAME_TO_FACTORY:
        raise ValueError(f"Unknown APP_NAME '{app_name}'. Valid: {sorted(APP_NAME_TO_FACTORY.keys())}")
    
    factory_name = APP_NAME_TO_FACTORY[app_name]
    logger.info(f"Importing factory '{factory_name}' from apps module (lazy)...")
    
    # Import from apps module - this uses the lazy __getattr__ mechanism
    try:
        from aimodelshare.moral_compass import apps
        return getattr(apps, factory_name)
    except AttributeError as e:
        raise RuntimeError(
            f"Failed to load factory '{factory_name}' for app '{app_name}'. "
            f"The factory function may not exist in the apps module. Error: {e}"
        ) from e
    except ImportError as e:
        raise RuntimeError(
            f"Failed to import dependencies for app '{app_name}' factory '{factory_name}'. "
            f"Check that all required packages are installed. Error: {e}"
        ) from e

if __name__ == "__main__":
    start_ts = time.time()
    app_name = os.environ.get("APP_NAME", "judge")
    port = int(os.environ.get("PORT", "8080"))

    logger.info(f"=== BOOTSTRAP === APP_NAME={app_name} PORT={port}")

    try:
        factory = load_factory(app_name)
        logger.info("Factory loaded; building Blocks object...")
        demo = factory()
        logger.info("Launching Gradio server (non-inline)...")

        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            show_api=False,
            show_error=True
        )

        logger.info(f"Gradio server started successfully in {time.time() - start_ts:.2f}s (listening on :{port}).")

    except Exception as e:
        logger.error(f"CRITICAL FAILURE LAUNCHING APP_NAME={app_name}: {e}")
        traceback.print_exc()
        sys.exit(1)

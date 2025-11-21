import os
import logging
import sys
import traceback
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("launcher")

FACTORY_LOOKUP = {
    "tutorial": ("aimodelshare.moral_compass.apps", "create_tutorial_app"),
    "judge": ("aimodelshare.moral_compass.apps", "create_judge_app"),
    "ai-consequences": ("aimodelshare.moral_compass.apps", "create_ai_consequences_app"),
    "what-is-ai": ("aimodelshare.moral_compass.apps", "create_what_is_ai_app"),
    "model-building-game": ("aimodelshare.moral_compass.apps", "create_model_building_game_app"),
    "ethical-revelation": ("aimodelshare.moral_compass.apps", "create_ethical_revelation_app"),
    "moral-compass-challenge": ("aimodelshare.moral_compass.apps", "create_moral_compass_challenge_app"),
    "bias-detective": ("aimodelshare.moral_compass.apps", "create_bias_detective_app"),
    "fairness-fixer": ("aimodelshare.moral_compass.apps", "create_fairness_fixer_app"),
    "justice-equity-upgrade": ("aimodelshare.moral_compass.apps", "create_justice_equity_upgrade_app"),
}

def load_factory(app_name: str):
    if app_name not in FACTORY_LOOKUP:
        raise ValueError(f"Unknown APP_NAME '{app_name}'. Valid: {sorted(FACTORY_LOOKUP.keys())}")
    mod, attr = FACTORY_LOOKUP[app_name]
    logger.info(f"Importing factory '{attr}' from '{mod}' (lazy)...")
    module = __import__(mod, fromlist=[attr])
    return getattr(module, attr)

if __name__ == "__main__":
    start_ts = time.time()
    app_name = os.environ.get("APP_NAME", "tutorial")
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
            analytics_enabled=False,
            show_error=True
        )

        logger.info(f"Gradio server started successfully in {time.time() - start_ts:.2f}s (listening on :{port}).")

    except Exception as e:
        logger.error(f"CRITICAL FAILURE LAUNCHING APP_NAME={app_name}: {e}")
        traceback.print_exc()
        sys.exit(1)

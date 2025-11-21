import os
import logging
import sys
import traceback

# Configure logging to ensure output appears in Cloud Run logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("launcher")

if __name__ == "__main__":
    try:
        # 1. Configuration
        app_name = os.environ.get("APP_NAME", "tutorial")
        port = int(os.environ.get("PORT", 8080))

        logger.info(f"--- STARTING APP: {app_name} on PORT {port} ---")

        # 2. Lazy Import Strategy
        if app_name == "tutorial":
            from aimodelshare.moral_compass.apps.tutorial import create_tutorial_app as factory
        elif app_name == "judge":
            from aimodelshare.moral_compass.apps.judge import create_judge_app as factory
        elif app_name == "ai-consequences":
            from aimodelshare.moral_compass.apps.ai_consequences import create_ai_consequences_app as factory
        elif app_name == "what-is-ai":
            from aimodelshare.moral_compass.apps.what_is_ai import create_what_is_ai_app as factory
        elif app_name == "model-building-game":
            from aimodelshare.moral_compass.apps.model_building_game import create_model_building_game_app as factory
        elif app_name == "ethical-revelation":
            from aimodelshare.moral_compass.apps.ethical_revelation import create_ethical_revelation_app as factory
        elif app_name == "moral-compass-challenge":
            from aimodelshare.moral_compass.apps.moral_compass_challenge import create_moral_compass_challenge_app as factory
        elif app_name == "bias-detective":
            from aimodelshare.moral_compass.apps.bias_detective import create_bias_detective_app as factory
        elif app_name == "fairness-fixer":
            from aimodelshare.moral_compass.apps.fairness_fixer import create_fairness_fixer_app as factory
        elif app_name == "justice-equity-upgrade":
            from aimodelshare.moral_compass.apps.justice_equity_upgrade import create_justice_equity_upgrade_app as factory
        else:
            raise ValueError(f"Unknown APP_NAME: {app_name}")

        logger.info(f"Factory loaded. Creating app...")
        demo = factory()
        
        logger.info(f"Launching Gradio Server...")
        # 3. Launch
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            show_api=False,
            analytics_enabled=False,
            show_error=True
        )
    except Exception as e:
        # This print statement is critical for debugging Cloud Run "Container failed to start" errors
        logger.error(f"CRITICAL FAILURE LAUNCHING {os.environ.get('APP_NAME')}: {e}")
        traceback.print_exc()
        sys.exit(1)

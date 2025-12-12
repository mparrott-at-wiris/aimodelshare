import os
import logging
import sys
import traceback
import time

# Gradio depends on FastAPI internally; importing explicitly for routing.
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse
import uvicorn
import gradio as gr  # Ensure gradio is installed in your image
from urllib.parse import urlencode  # NEW: build query strings robustly

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("launcher")

# Base mapping of APP_NAME -> factory function (lazy-imported from apps module)
APP_NAME_TO_FACTORY = {
    "tutorial": "create_tutorial_app",
    "judge": "create_judge_app",
    "ai-consequences": "create_ai_consequences_app",
    "what-is-ai": "create_what_is_ai_app",
    # Legacy generic model building game
    "model-building-game": "create_model_building_game_app",
    # Language-specific variants (each module should define its own factory)
    "model-building-game-en": "create_model_building_game_en_app",
    "model-building-game-ca": "create_model_building_game_ca_app",
    "model-building-game-es": "create_model_building_game_es_app",
    "ethical-revelation": "create_ethical_revelation_app",
    "moral-compass-challenge": "create_moral_compass_challenge_app",
    "moral-compass-challenge": "create_moral_compass_challenge_app",
    # Bias Detective apps (split into two separate services)
    # Keep legacy "bias-detective" as an alias for part1 for backward compatibility
    "bias-detective-part1": "create_bias_detective_part1_app",
    "bias-detective-part2": "create_bias_detective_part2_app",
    "moral-compass-challenge": "create_moral_compass_challenge_app",
}

# Supported language codes for model-building-game dynamic routing
MODEL_GAME_LANGS = ("en", "es", "ca")


def lazy_get_factory(factory_name: str):
    """Return a callable factory object from apps module via lazy import."""
    try:
        from aimodelshare.moral_compass import apps
        return getattr(apps, factory_name)
    except AttributeError as e:
        raise RuntimeError(
            f"Factory '{factory_name}' not found in apps module. Error: {e}"
        ) from e
    except ImportError as e:
        raise RuntimeError(
            f"Import error while loading factory '{factory_name}'. Error: {e}"
        ) from e


def build_standard_app(app_name: str):
    """Build and return a single Gradio Blocks app for non-dynamic cases."""
    if app_name not in APP_NAME_TO_FACTORY:
        raise ValueError(f"Unknown APP_NAME '{app_name}'. Valid: {sorted(APP_NAME_TO_FACTORY.keys())}")
    factory_name = APP_NAME_TO_FACTORY[app_name]
    logger.info(f"Loading factory '{factory_name}' for APP_NAME='{app_name}'...")
    factory = lazy_get_factory(factory_name)
    return factory()


def build_model_building_game_router():
    """
    Build a FastAPI router that serves the model building game in different languages
    based on a 'lang' query parameter.

    Access patterns:
      /?lang=es&sessionid=... -> redirect to /es?sessionid=...
      /?lang=ca&sessionid=... -> redirect to /ca?sessionid=...
      /?lang=en or missing/invalid -> redirect to /en (preserving any other query params)

    Direct paths:
      /en?sessionid=...  -> English game (params forwarded to Gradio)
      /es?sessionid=...  -> Spanish game
      /ca?sessionid=...  -> Catalan game

    Blocks apps are created lazily on first access to reduce startup time.
    """
    logger.info("Initializing dynamic language router for model-building-game...")

    fastapi_app = FastAPI(title="Model Building Game (Language Router)")

    # Cache for instantiated language-specific Blocks (to avoid rebuilding)
    blocks_cache = {}

    def get_blocks(lang: str):
        """Return (and cache) the Blocks instance for the requested language."""
        if lang not in MODEL_GAME_LANGS:
            lang = "en"
        if lang in blocks_cache:
            return blocks_cache[lang]

        factory_name = {
            "en": "create_model_building_game_en_app",
            "es": "create_model_building_game_es_app",
            "ca": "create_model_building_game_ca_app",
        }[lang]

        logger.info(f"Lazy-building Blocks for lang='{lang}' using factory '{factory_name}'...")
        factory = lazy_get_factory(factory_name)
        blocks = factory()
        blocks_cache[lang] = blocks
        return blocks

    # Mount Gradio apps at language-specific paths (pre-warm optional)
    for lang in MODEL_GAME_LANGS:
        # Optional pre-warm; comment out if you want fully lazy mounts
        # blocks = get_blocks(lang)
        # gr.mount_gradio_app(fastapi_app, blocks, path=f"/{lang}")
        # logger.info(f"Mounted Gradio Blocks at '/{lang}' for lang='{lang}'.")
        pass

    # Lazy mount handler: mounts app on first visit to /{lang}
    @fastapi_app.get("/{lang_code}")
    async def lang_root(lang_code: str, request: Request):
        lang_code = lang_code.lower()
        if lang_code not in MODEL_GAME_LANGS:
            # Preserve full query string when redirecting to default
            qs = urlencode(request.query_params.multi_items())
            target = "/en" + (f"?{qs}" if qs else "")
            return RedirectResponse(url=target, status_code=307)

        # Mount on demand if not already mounted
        path = f"/{lang_code}"
        # Check if a route exists that serves this path; mount if needed
        try:
            blocks = get_blocks(lang_code)
            # Always re-mount to ensure the path exists (idempotent for Gradio/FastAPI)
            gr.mount_gradio_app(fastapi_app, blocks, path=path)
        except Exception as e:
            logger.error(f"Mount failed for lang='{lang_code}': {e}")
            return PlainTextResponse(f"Error loading language '{lang_code}'", status_code=500)

        # Preserve query params in redirect to the mounted path
        qs = urlencode(request.query_params.multi_items())
        target = path + (f"?{qs}" if qs else "")
        return RedirectResponse(url=target, status_code=307)

    @fastapi_app.get("/")
    async def root(request: Request):
        # Determine lang, defaulting to 'en'
        lang = request.query_params.get("lang", "en").lower()
        if lang not in MODEL_GAME_LANGS:
            lang = "en"
        # Preserve all query parameters (including sessionid and others) on redirect
        params = dict(request.query_params)
        params["lang"] = lang  # normalize lang
        qs = urlencode(list(request.query_params.multi_items()))  # keep order and duplicates
        # Build target: /{lang}?<full query string>
        target = f"/{lang}" + (f"?{qs}" if qs else "")
        return RedirectResponse(url=target, status_code=307)

    @fastapi_app.get("/healthz")
    async def health():
        return PlainTextResponse("ok")

    @fastapi_app.get("/_languages")
    async def list_languages():
        return {"available_languages": MODEL_GAME_LANGS}

    return fastapi_app


def launch_asgi_app(app, port: int):
    """Launch the provided ASGI app with uvicorn."""
    logger.info(f"Starting uvicorn ASGI server on 0.0.0.0:{port} ...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def main():
    start_ts = time.time()
    app_name = os.environ.get("APP_NAME", "judge").strip()
    port = int(os.environ.get("PORT", "8080"))

    logger.info(f"=== BOOTSTRAP === APP_NAME={app_name} PORT={port}")

    try:
        # For the base router service, enable query-param based language routing.
        if app_name == "model-building-game":
            logger.info(
                "Detected base model-building-game. Enabling query parameter routing (?lang=en|es|ca), preserving all query params."
            )
            asgi_app = build_model_building_game_router()
            launch_asgi_app(asgi_app, port)
        elif app_name.startswith("model-building-game-"):
            # Language-specific services: launch only that language variant (no redirects needed)
            logger.info(f"Launching single language variant app: {app_name}")
            demo = build_standard_app(app_name)
            demo.launch(
                server_name="0.0.0.0",
                server_port=port,
                show_api=False,
                show_error=True,
            )
            logger.info(
                f"Gradio server started successfully in {time.time() - start_ts:.2f}s (listening on :{port})."
            )
        else:
            # Standard single-language / single-app launch
            demo = build_standard_app(app_name)
            logger.info("Launching Gradio server (non-inline)...")
            demo.launch(
                server_name="0.0.0.0",
                server_port=port,
                show_api=False,
                show_error=True,
            )
            logger.info(
                f"Gradio server started successfully in {time.time() - start_ts:.2f}s (listening on :{port})."
            )

    except Exception as e:
        logger.error(f"CRITICAL FAILURE LAUNCHING APP_NAME={app_name}: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

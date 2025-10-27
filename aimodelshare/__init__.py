"""
Top-level aimodelshare package initializer.

Refactored to:
- Avoid eager importing of heavy optional dependencies (networkx, torch, tensorflow, etc.)
- Allow lightweight submodules (e.g. aimodelshare.moral_compass) to work in minimal environments.
- Preserve backward compatibility where possible without forcing heavy installs.
"""

from importlib import import_module
import warnings

__all__ = [
    # Heavy/high-level objects (added only if imported successfully)
    "ModelPlayground",
    "Competition",
    "Data",
    "Experiment",
    # Preprocessor helpers (optional)
    "upload_preprocessor",
    "import_preprocessor",
    "export_preprocessor",
    "download_data",
    # Moral Compass client (lightweight)
    "MoralcompassApiClient",
    "MoralcompassTableMeta",
    "MoralcompassUserStats",
    "ApiClientError",
    "NotFoundError",
    "ServerError",
    "get_api_base_url",
]

def _safe_import(module_name, symbols, remove_if_missing=True):
    """
    Attempt to import given symbols from module_name.
    On failure, emit a warning and optionally remove them from __all__.
    """
    try:
        mod = import_module(module_name)
        for sym in symbols:
            try:
                globals()[sym] = getattr(mod, sym)
            except AttributeError:
                warnings.warn(
                    f"aimodelshare: symbol '{sym}' not found in module '{module_name}'."
                )
                if remove_if_missing and sym in __all__:
                    __all__.remove(sym)
    except Exception as exc:
        warnings.warn(
            f"aimodelshare: optional module '{module_name}' not loaded ({exc}). "
            "Lightweight submodules remain usable."
        )
        if remove_if_missing:
            for sym in symbols:
                if sym in __all__ and sym not in globals():
                    __all__.remove(sym)

# Attempt optional imports (silently skip if deps missing)
_safe_import(
    "aimodelshare.playground",
    ["ModelPlayground", "Competition", "Experiment", "Data"],
)

_safe_import(
    "aimodelshare.preprocessormodules",
    ["export_preprocessor", "upload_preprocessor", "import_preprocessor"],
)

_safe_import(
    "aimodelshare.data_sharing.download_data",
    ["download_data", "import_quickstart_data"],  # import_quickstart_data not in __all__
    remove_if_missing=True,
)
# If import_quickstart_data is missing, we don't expose it; if present we leave it accessible.
if "import_quickstart_data" not in globals():
    # Ensure it's not accidentally in __all__
    if "import_quickstart_data" in __all__:
        __all__.remove("import_quickstart_data")

# Moral Compass submodule (expected always present in new branch)
_safe_import(
    "aimodelshare.moral_compass",
    [
        "MoralcompassApiClient",
        "MoralcompassTableMeta",
        "MoralcompassUserStats",
        "ApiClientError",
        "NotFoundError",
        "ServerError",
        "get_api_base_url",
    ],
    remove_if_missing=False,  # If this fails, keep names so import errors surface clearly later
)

# Ensure __all__ only contains names actually available (except intentional exposure for debug)
__all__ = [name for name in __all__ if name in globals()]

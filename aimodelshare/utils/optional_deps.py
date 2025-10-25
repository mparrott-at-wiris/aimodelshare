"""Optional dependency checking utilities."""
import os
import importlib.util
import warnings

_DEF_SUPPRESS_ENV = "AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS"


def check_optional(name: str, feature_label: str, suppress_env: str = _DEF_SUPPRESS_ENV) -> bool:
    """Check if an optional dependency is available.
    
    Print a single warning (via warnings) if missing and suppression env var is not set.
    Returns True if available, False otherwise.
    
    Parameters
    ----------
    name : str
        The name of the module to check (e.g., 'xgboost', 'pyspark')
    feature_label : str
        A human-readable label for the feature that requires this dependency
    suppress_env : str, optional
        Environment variable name to check for suppression (default: AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS)
    
    Returns
    -------
    bool
        True if the module is available, False otherwise
    """
    spec = importlib.util.find_spec(name)
    if spec is None:
        if not os.environ.get(suppress_env):
            warnings.warn(
                f"{feature_label} support unavailable. Install `{name}` to enable.",
                category=UserWarning,
                stacklevel=2,
            )
        return False
    return True

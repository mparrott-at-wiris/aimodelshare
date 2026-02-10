"""
Dataset path resolver for sustainability model-building apps.

Provides robust path resolution for the WiDS CSV dataset that works across
different deployment environments (local development, Docker, Cloud Run).
"""

import os
from pathlib import Path
from typing import Optional


def get_wids_dataset_path() -> str:
    """
    Resolve the path to the WiDS dataset CSV file.
    
    This function attempts to find the dataset file in multiple locations,
    in order of priority:
    1. Environment variable override (WIDS_DATASET_CSV or DATASET_CSV_PATH)
    2. Absolute path in Cloud Run container: /app/datasets/recreated_wids_v2_ny_10k.csv
    3. Relative to repository root: datasets/recreated_wids_v2_ny_10k.csv
    4. Fallback to default relative path (for backwards compatibility)
    
    Returns:
        str: Absolute path to the WiDS dataset CSV file
        
    Raises:
        FileNotFoundError: If the dataset file cannot be found in any location
    """
    dataset_filename = "recreated_wids_v2_ny_10k.csv"
    debug_log = os.environ.get("DEBUG_LOG", "false").lower() == "true"
    
    # Priority 1: Environment variable override
    env_path = os.environ.get("WIDS_DATASET_CSV") or os.environ.get("DATASET_CSV_PATH")
    if env_path:
        if os.path.isfile(env_path):
            if debug_log:
                print(f"[DATASET_RESOLVER] Using env var path: {env_path}", flush=True)
            return env_path
        else:
            if debug_log:
                print(f"[DATASET_RESOLVER] Warning: Env var path not found: {env_path}", flush=True)
    
    # Priority 2: Cloud Run container absolute path
    cloud_run_path = f"/app/datasets/{dataset_filename}"
    if os.path.isfile(cloud_run_path):
        if debug_log:
            print(f"[DATASET_RESOLVER] Using Cloud Run path: {cloud_run_path}", flush=True)
        return cloud_run_path
    
    # Priority 3: Relative to repository root
    # Try to find the repository root by looking for characteristic files
    search_roots = [
        os.getcwd(),                                    # Current working directory
        os.path.dirname(os.path.abspath(__file__)),    # Module directory
        Path(__file__).parent.parent.parent.parent.parent,  # Go up to repo root from this file
    ]
    
    for root in search_roots:
        root_path = Path(root)
        
        # Check if this looks like the repository root
        # (has datasets directory and other characteristic files)
        datasets_dir = root_path / "datasets"
        if datasets_dir.exists() and datasets_dir.is_dir():
            candidate_path = datasets_dir / dataset_filename
            if candidate_path.exists():
                resolved_path = str(candidate_path.resolve())
                if debug_log:
                    print(f"[DATASET_RESOLVER] Using repo-root relative path: {resolved_path}", flush=True)
                return resolved_path
    
    # Priority 4: Fallback to default relative path (for backwards compatibility)
    fallback_path = f"datasets/{dataset_filename}"
    if os.path.isfile(fallback_path):
        if debug_log:
            print(f"[DATASET_RESOLVER] Using fallback relative path: {fallback_path}", flush=True)
        return fallback_path
    
    # If we get here, we couldn't find the file anywhere
    error_msg = (
        f"Dataset file '{dataset_filename}' not found. Searched locations:\n"
        f"  1. Environment variable: {env_path or 'not set'}\n"
        f"  2. Cloud Run path: {cloud_run_path}\n"
        f"  3. Repository root: {search_roots}\n"
        f"  4. Fallback path: {fallback_path}\n"
        f"\nSet WIDS_DATASET_CSV or DATASET_CSV_PATH environment variable to specify a custom location."
    )
    raise FileNotFoundError(error_msg)

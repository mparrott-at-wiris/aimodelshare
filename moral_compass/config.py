"""Configuration module for API base URL discovery.

This module provides logic to discover the API base URL from multiple sources:
1. Environment variables (MORAL_COMPASS_API_BASE_URL or AIMODELSHARE_API_BASE_URL)
2. Cached Terraform outputs file (infra/terraform_outputs.json)
3. Direct terraform output command (if Terraform state is accessible)
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Optional


class ApiBaseUrlNotFound(Exception):
    """Raised when API base URL cannot be discovered."""
    pass


def get_api_base_url(raise_on_missing: bool = True) -> Optional[str]:
    """
    Discover API base URL from environment, cached file, or Terraform output.
    
    Discovery order:
    1. Env var MORAL_COMPASS_API_BASE_URL (primary)
    2. Env var AIMODELSHARE_API_BASE_URL (fallback for backward compatibility)
    3. Cached file infra/terraform_outputs.json
    4. Direct terraform output -raw api_base_url command
    
    Args:
        raise_on_missing: If True, raise ApiBaseUrlNotFound if URL not found.
                         If False, return None.
    
    Returns:
        API base URL string or None if not found and raise_on_missing=False.
        
    Raises:
        ApiBaseUrlNotFound: If URL not found and raise_on_missing=True.
    """
    # 1. Check environment variables
    url = os.getenv("MORAL_COMPASS_API_BASE_URL")
    if url:
        return url.strip()
    
    # Fallback to legacy env var for backward compatibility
    url = os.getenv("AIMODELSHARE_API_BASE_URL")
    if url:
        return url.strip()
    
    # 2. Check cached Terraform outputs file
    # Try to find infra directory relative to this file or in current working directory
    candidates = [
        Path(__file__).parent.parent / "infra" / "terraform_outputs.json",
        Path.cwd() / "infra" / "terraform_outputs.json",
    ]
    
    for cache_file in candidates:
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Handle both direct key and nested output format
                    if "api_base_url" in data:
                        if isinstance(data["api_base_url"], dict):
                            url = data["api_base_url"].get("value")
                        else:
                            url = data["api_base_url"]
                        if url:
                            return url.strip()
            except (json.JSONDecodeError, IOError, KeyError):
                # Continue to next method if file is invalid
                pass
    
    # 3. Try direct Terraform output command
    infra_dirs = [
        Path(__file__).parent.parent / "infra",
        Path.cwd() / "infra",
    ]
    
    for infra_dir in infra_dirs:
        if infra_dir.exists() and (infra_dir / "main.tf").exists():
            try:
                result = subprocess.run(
                    ["terraform", "output", "-raw", "api_base_url"],
                    cwd=str(infra_dir),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    url = result.stdout.strip()
                    if url and url != "null":
                        return url
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
                # Terraform not available or command failed
                pass
    
    # Not found
    if raise_on_missing:
        raise ApiBaseUrlNotFound(
            "API base URL not found. Please set MORAL_COMPASS_API_BASE_URL environment variable, "
            "ensure infra/terraform_outputs.json exists, or run terraform apply in the infra directory."
        )
    
    return None

"""
Configuration module for moral_compass API client.

Provides API base URL discovery via:
1. Environment variable MORAL_COMPASS_API_BASE_URL or AIMODELSHARE_API_BASE_URL
2. Cached terraform outputs file (infra/terraform_outputs.json)
3. Terraform command execution (fallback)

Also provides AWS region discovery for region-aware table naming.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aimodelshare.moral_compass")


def get_aws_region() -> Optional[str]:
    """
    Discover AWS region from multiple sources.
    
    Resolution order:
    1. AWS_REGION environment variable
    2. AWS_DEFAULT_REGION environment variable
    3. Cached terraform outputs file
    4. None (caller should handle default)
    
    Returns:
        Optional[str]: AWS region name or None
    """
    # Strategy 1: Check environment variables
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if region:
        logger.debug(f"Using AWS region from environment: {region}")
        return region
    
    # Strategy 2: Try cached terraform outputs
    cached_region = _get_region_from_cached_outputs()
    if cached_region:
        logger.debug(f"Using AWS region from cached terraform outputs: {cached_region}")
        return cached_region
    
    # No region found - return None and let caller decide default
    logger.debug("AWS region not found, caller should use default")
    return None


def get_api_base_url() -> str:
    """
    Discover API base URL using multiple strategies in order:
    1. Environment variables (MORAL_COMPASS_API_BASE_URL or AIMODELSHARE_API_BASE_URL)
    2. Cached terraform outputs file
    3. Terraform command execution
    
    Returns:
        str: The API base URL
        
    Raises:
        RuntimeError: If API base URL cannot be determined
    """
    # Strategy 1: Check environment variables
    env_url = os.getenv("MORAL_COMPASS_API_BASE_URL") or os.getenv("AIMODELSHARE_API_BASE_URL")
    if env_url:
        logger.debug(f"Using API base URL from environment: {env_url}")
        return env_url.rstrip("/")
    
    # Strategy 2: Try cached terraform outputs
    cached_url = _get_url_from_cached_outputs()
    if cached_url:
        logger.debug(f"Using API base URL from cached terraform outputs: {cached_url}")
        return cached_url
    
    # Strategy 3: Try terraform command (last resort)
    terraform_url = _get_url_from_terraform_command()
    if terraform_url:
        logger.debug(f"Using API base URL from terraform command: {terraform_url}")
        return terraform_url
    
    raise RuntimeError(
        "Could not determine API base URL. Please set MORAL_COMPASS_API_BASE_URL "
        "environment variable or ensure terraform outputs are accessible."
    )


def _get_url_from_cached_outputs() -> Optional[str]:
    """
    Read API base URL from cached terraform outputs file.
    
    Returns:
        Optional[str]: API base URL if found in cache, None otherwise
    """
    # Look for terraform_outputs.json in infra directory
    repo_root = Path(__file__).parent.parent.parent.parent
    outputs_file = repo_root / "infra" / "terraform_outputs.json"
    
    if not outputs_file.exists():
        logger.debug(f"Cached terraform outputs not found at {outputs_file}")
        return None
    
    try:
        with open(outputs_file, "r") as f:
            outputs = json.load(f)
        
        # Handle both formats: {"api_base_url": {"value": "..."}} or {"api_base_url": "..."}
        api_base_url = outputs.get("api_base_url")
        if isinstance(api_base_url, dict):
            url = api_base_url.get("value")
        else:
            url = api_base_url
        
        if url and url != "null":
            return url.rstrip("/")
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error reading cached terraform outputs: {e}")
    
    return None


def _get_region_from_cached_outputs() -> Optional[str]:
    """
    Read AWS region from cached terraform outputs file.
    
    Returns:
        Optional[str]: AWS region if found in cache, None otherwise
    """
    # Look for terraform_outputs.json in infra directory
    repo_root = Path(__file__).parent.parent.parent.parent
    outputs_file = repo_root / "infra" / "terraform_outputs.json"
    
    if not outputs_file.exists():
        logger.debug(f"Cached terraform outputs not found at {outputs_file}")
        return None
    
    try:
        with open(outputs_file, "r") as f:
            outputs = json.load(f)
        
        # Handle both formats: {"region": {"value": "..."}} or {"region": "..."}
        region = outputs.get("region") or outputs.get("aws_region")
        if isinstance(region, dict):
            region_value = region.get("value")
        else:
            region_value = region
        
        if region_value and region_value != "null":
            return region_value
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error reading cached terraform outputs: {e}")
    
    return None


def _get_url_from_terraform_command() -> Optional[str]:
    """
    Execute terraform command to get API base URL.
    
    Returns:
        Optional[str]: API base URL if terraform command succeeds, None otherwise
    """
    repo_root = Path(__file__).parent.parent.parent.parent
    infra_dir = repo_root / "infra"
    
    if not infra_dir.exists():
        logger.debug(f"Infra directory not found at {infra_dir}")
        return None
    
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", "api_base_url"],
            cwd=infra_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            url = result.stdout.strip()
            if url and url != "null":
                return url.rstrip("/")
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
        logger.debug(f"Terraform command failed: {e}")
    
    return None

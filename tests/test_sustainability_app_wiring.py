#!/usr/bin/env python3
"""
Automated validation tests for sustainability Gradio app deployment wiring.

This test verifies that every deployed APP_NAME in `.github/workflows/deploy_gradio_apps_sustainability.yml`
is properly wired through the entire chain:
1. Present in `launch_entrypoint.py`'s `APP_NAME_TO_FACTORY` mapping
2. Mapped to a factory function in the lazy export layer (`aimodelshare/moral_compass/apps/__init__.py`)
3. The factory function is implemented in the referenced module

Run with: pytest -v tests/test_sustainability_app_wiring.py
Or from project root: pytest -v
"""

import os
import re
import ast
import pytest
import yaml
from pathlib import Path


# Get repository root
REPO_ROOT = Path(__file__).parent.parent
WORKFLOW_FILE = REPO_ROOT / ".github/workflows/deploy_gradio_apps_sustainability.yml"
LAUNCH_ENTRYPOINT = REPO_ROOT / "launch_entrypoint.py"
APPS_INIT = REPO_ROOT / "aimodelshare/moral_compass/apps/__init__.py"
APPS_DIR = REPO_ROOT / "aimodelshare/moral_compass/apps"


def extract_app_names_from_workflow():
    """Extract all APP_NAME values from the sustainability workflow YAML."""
    with open(WORKFLOW_FILE, 'r') as f:
        workflow = yaml.safe_load(f)
    
    app_names = set()
    for job_name, job_config in workflow.get('jobs', {}).items():
        if 'steps' in job_config:
            for step in job_config['steps']:
                if 'uses' in step and 'deploy-cloudrun' in step['uses']:
                    flags = step.get('flags', '')
                    match = re.search(r'APP_NAME=([a-z0-9-]+)', flags)
                    if match:
                        app_names.add(match.group(1))
    
    return sorted(app_names)


def extract_app_to_factory_mapping():
    """Extract APP_NAME_TO_FACTORY mapping from launch_entrypoint.py."""
    with open(LAUNCH_ENTRYPOINT, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'APP_NAME_TO_FACTORY':
                    if isinstance(node.value, ast.Dict):
                        mapping = {}
                        for k, v in zip(node.value.keys, node.value.values):
                            if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                                mapping[k.value] = v.value
                        return mapping
    return {}


def extract_export_map():
    """Extract _EXPORT_MAP from apps/__init__.py."""
    with open(APPS_INIT, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '_EXPORT_MAP':
                    if isinstance(node.value, ast.Dict):
                        export_map = {}
                        for k, v in zip(node.value.keys, node.value.values):
                            if isinstance(k, ast.Constant) and isinstance(v, ast.Tuple):
                                module_path = v.elts[0].value if isinstance(v.elts[0], ast.Constant) else None
                                symbol = v.elts[1].value if isinstance(v.elts[1], ast.Constant) else None
                                export_map[k.value] = (module_path, symbol)
                        return export_map
    return {}


def test_workflow_file_exists():
    """Verify the sustainability workflow file exists."""
    assert WORKFLOW_FILE.exists(), f"Workflow file not found: {WORKFLOW_FILE}"


def test_launch_entrypoint_exists():
    """Verify launch_entrypoint.py exists."""
    assert LAUNCH_ENTRYPOINT.exists(), f"Launch entrypoint not found: {LAUNCH_ENTRYPOINT}"


def test_apps_init_exists():
    """Verify apps/__init__.py exists."""
    assert APPS_INIT.exists(), f"Apps __init__.py not found: {APPS_INIT}"


def test_all_deployed_apps_in_launcher():
    """Verify all deployed sustainability apps are in launch_entrypoint.py APP_NAME_TO_FACTORY."""
    workflow_apps = extract_app_names_from_workflow()
    launcher_mapping = extract_app_to_factory_mapping()
    
    missing_apps = []
    for app_name in workflow_apps:
        if app_name not in launcher_mapping:
            missing_apps.append(app_name)
    
    assert not missing_apps, (
        f"Apps deployed in workflow but missing from launch_entrypoint.py APP_NAME_TO_FACTORY: "
        f"{', '.join(missing_apps)}"
    )


def test_all_factories_in_export_map():
    """Verify all factory functions referenced in launcher are in the export map."""
    workflow_apps = extract_app_names_from_workflow()
    launcher_mapping = extract_app_to_factory_mapping()
    export_map = extract_export_map()
    
    missing_factories = []
    for app_name in workflow_apps:
        factory_name = launcher_mapping.get(app_name)
        if factory_name and factory_name not in export_map:
            missing_factories.append(f"{app_name} -> {factory_name}")
    
    assert not missing_factories, (
        f"Factory functions referenced in launcher but missing from export map: "
        f"{', '.join(missing_factories)}"
    )


def test_all_module_files_exist():
    """Verify all module files referenced in export map exist."""
    workflow_apps = extract_app_names_from_workflow()
    launcher_mapping = extract_app_to_factory_mapping()
    export_map = extract_export_map()
    
    missing_files = []
    for app_name in workflow_apps:
        factory_name = launcher_mapping.get(app_name)
        if factory_name and factory_name in export_map:
            module_path, symbol = export_map[factory_name]
            file_path = APPS_DIR / f"{module_path.replace('.', '/')}.py"
            if not file_path.exists():
                missing_files.append(f"{app_name}: {file_path}")
    
    assert not missing_files, (
        f"Module files referenced in export map but not found: "
        f"{'; '.join(missing_files)}"
    )


def test_all_factory_symbols_implemented():
    """Verify all factory symbols exist in their respective modules."""
    workflow_apps = extract_app_names_from_workflow()
    launcher_mapping = extract_app_to_factory_mapping()
    export_map = extract_export_map()
    
    missing_symbols = []
    for app_name in workflow_apps:
        factory_name = launcher_mapping.get(app_name)
        if factory_name and factory_name in export_map:
            module_path, symbol = export_map[factory_name]
            file_path = APPS_DIR / f"{module_path.replace('.', '/')}.py"
            
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check if the function is defined
                pattern = rf"^def {re.escape(symbol)}\("
                if not re.search(pattern, content, re.MULTILINE):
                    missing_symbols.append(
                        f"{app_name}: Symbol '{symbol}' not found in {file_path.relative_to(REPO_ROOT)}"
                    )
    
    assert not missing_symbols, (
        f"Factory symbols not implemented in modules: "
        f"{'; '.join(missing_symbols)}"
    )


def test_complete_chain_validation():
    """Comprehensive test that validates the entire workflow -> launcher -> export -> module chain."""
    workflow_apps = extract_app_names_from_workflow()
    launcher_mapping = extract_app_to_factory_mapping()
    export_map = extract_export_map()
    
    results = []
    errors = []
    
    for app_name in workflow_apps:
        # Step 1: Check launcher mapping
        factory_name = launcher_mapping.get(app_name)
        if not factory_name:
            errors.append(f"❌ {app_name}: Not in launch_entrypoint.py APP_NAME_TO_FACTORY")
            continue
        
        # Step 2: Check export map
        export_info = export_map.get(factory_name)
        if not export_info:
            errors.append(f"❌ {app_name}: Factory '{factory_name}' not in export map")
            continue
        
        module_path, symbol = export_info
        
        # Step 3: Check module file exists
        file_path = APPS_DIR / f"{module_path.replace('.', '/')}.py"
        if not file_path.exists():
            errors.append(f"❌ {app_name}: Module file missing: {file_path.relative_to(REPO_ROOT)}")
            continue
        
        # Step 4: Check symbol exists in module
        with open(file_path, 'r') as f:
            content = f.read()
        
        pattern = rf"^def {re.escape(symbol)}\("
        if not re.search(pattern, content, re.MULTILINE):
            errors.append(
                f"❌ {app_name}: Symbol '{symbol}' not found in {file_path.relative_to(REPO_ROOT)}"
            )
            continue
        
        # All checks passed
        results.append(
            f"✅ {app_name}: workflow → {factory_name} → {module_path}.{symbol}"
        )
    
    # Print results for debugging
    print("\n" + "="*80)
    print("SUSTAINABILITY APP WIRING VALIDATION")
    print("="*80)
    for result in results:
        print(result)
    
    if errors:
        print("\nERRORS:")
        for error in errors:
            print(error)
    
    print("="*80 + "\n")
    
    assert not errors, f"Chain validation failed with {len(errors)} error(s)"


def test_no_extra_sustainability_factories_in_export_map():
    """Verify there are no orphaned sustainability factories in export map not used by workflow.
    
    Note: This test only checks 'create_*' factories (not 'launch_*' factories) since those
    are what's referenced in the launcher mapping. Launch functions are wrapper functions
    that are not directly used by the deployment workflow.
    """
    workflow_apps = extract_app_names_from_workflow()
    launcher_mapping = extract_app_to_factory_mapping()
    export_map = extract_export_map()
    
    # Get all sustainability factory names from export map
    # We only check 'create_' factories as those are what the launcher uses
    sustainability_factories = {
        k for k in export_map.keys() 
        if 'sustainability' in k and k.startswith('create_')
    }
    
    # Get all factories used by workflow
    used_factories = {
        launcher_mapping.get(app_name) 
        for app_name in workflow_apps 
        if launcher_mapping.get(app_name)
    }
    
    # Find unused sustainability factories
    unused = sustainability_factories - used_factories
    
    # This is a warning test - we allow some unused factories
    # but report them so developers know
    if unused:
        print(f"\nℹ️  Note: {len(unused)} sustainability factories in export map not used by workflow:")
        for factory in sorted(unused):
            print(f"   - {factory}")


def test_naming_consistency():
    """Verify factory function names follow the naming convention."""
    launcher_mapping = extract_app_to_factory_mapping()
    
    inconsistencies = []
    for app_name, factory_name in launcher_mapping.items():
        if 'sustainability' not in app_name:
            continue
        
        # Expected factory name: create_{app_name_with_underscores}_app
        expected_factory = f"create_{app_name.replace('-', '_')}_app"
        
        if factory_name != expected_factory:
            inconsistencies.append(
                f"{app_name}: Expected '{expected_factory}', got '{factory_name}'"
            )
    
    assert not inconsistencies, (
        f"Naming inconsistencies found: {'; '.join(inconsistencies)}"
    )


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "-s"])

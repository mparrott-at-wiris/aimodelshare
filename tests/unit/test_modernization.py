"""Tests for modernization and deprecation mitigation features."""
import pytest
import os
import sys
import warnings


class TestOptionalDepsChecker:
    """Tests for the centralized optional dependency checker."""
    
    def test_check_optional_exists(self):
        """Test that check_optional function exists and is importable."""
        from aimodelshare.utils.optional_deps import check_optional
        assert check_optional is not None
    
    def test_check_optional_with_installed_package(self):
        """Test check_optional returns True for installed packages."""
        from aimodelshare.utils.optional_deps import check_optional
        
        # pandas should be installed in test environment
        result = check_optional("pandas", "Pandas")
        assert result is True
    
    def test_check_optional_with_missing_package(self):
        """Test check_optional returns False and warns for missing packages."""
        from aimodelshare.utils.optional_deps import check_optional
        
        # nonexistent_package_xyz should not be installed
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = check_optional("nonexistent_package_xyz", "Nonexistent Feature")
            
            assert result is False
            assert len(w) == 1
            assert "Nonexistent Feature" in str(w[0].message)
            assert "nonexistent_package_xyz" in str(w[0].message)
    
    def test_check_optional_with_suppression(self):
        """Test check_optional respects suppression environment variable."""
        from aimodelshare.utils.optional_deps import check_optional
        
        # Set suppression environment variable
        os.environ["AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS"] = "1"
        
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = check_optional("nonexistent_package_abc", "Another Nonexistent")
                
                assert result is False
                # Should not have produced a warning
                assert len(w) == 0
        finally:
            # Clean up
            os.environ.pop("AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS", None)
    
    def test_check_optional_custom_suppress_env(self):
        """Test check_optional with custom suppression environment variable."""
        from aimodelshare.utils.optional_deps import check_optional
        
        # Set custom suppression environment variable
        os.environ["CUSTOM_SUPPRESS"] = "1"
        
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = check_optional(
                    "nonexistent_package_def", 
                    "Yet Another Nonexistent",
                    suppress_env="CUSTOM_SUPPRESS"
                )
                
                assert result is False
                # Should not have produced a warning
                assert len(w) == 0
        finally:
            # Clean up
            os.environ.pop("CUSTOM_SUPPRESS", None)


class TestImportlibMetadata:
    """Tests for importlib.metadata usage in reproducibility module."""
    
    def test_importlib_metadata_import(self):
        """Test that importlib.metadata can be imported."""
        try:
            import importlib.metadata as md
            assert md is not None
        except ImportError:
            import importlib_metadata as md
            assert md is not None
    
    def test_reproducibility_module_imports(self):
        """Test that reproducibility module imports without pkg_resources."""
        # This will fail if pkg_resources is still being imported
        from aimodelshare import reproducibility
        
        # Check that pkg_resources is NOT in the module
        assert not hasattr(reproducibility, 'pkg_resources')
    
    def test_export_reproducibility_env_basic(self):
        """Test that export_reproducibility_env function works."""
        from aimodelshare.reproducibility import export_reproducibility_env
        import tempfile
        import json
        
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Export reproducibility environment
            export_reproducibility_env(seed=42, directory=tmpdir, mode="cpu")
            
            # Check that the file was created
            repro_file = os.path.join(tmpdir, "reproducibility.json")
            assert os.path.exists(repro_file)
            
            # Load and verify the contents
            with open(repro_file, 'r') as f:
                data = json.load(f)
            
            assert "global_seed_code" in data
            assert "local_seed_code" in data
            assert "gpu_cpu_parallelism_ops" in data
            assert "session_runtime_info" in data
            assert "installed_packages" in data["session_runtime_info"]
            
            # Verify packages list is a list
            assert isinstance(data["session_runtime_info"]["installed_packages"], list)


class TestPyJWTCompatibility:
    """Tests for PyJWT compatibility wrapper."""
    
    def test_decode_token_unverified_exists(self):
        """Test that decode_token_unverified function exists."""
        from aimodelshare.modeluser import decode_token_unverified
        assert decode_token_unverified is not None
    
    def test_decode_token_unverified_basic(self):
        """Test decode_token_unverified with a simple token."""
        import jwt
        from aimodelshare.modeluser import decode_token_unverified
        
        # Create a simple test token
        payload = {"user": "testuser", "exp": 9999999999}
        test_secret = "fake-secret-for-testing-only"
        token = jwt.encode(payload, test_secret, algorithm="HS256")
        
        # Decode using our wrapper
        decoded = decode_token_unverified(token)
        
        assert decoded is not None
        assert decoded["user"] == "testuser"
    
    def test_decode_token_unverified_in_exports(self):
        """Test that decode_token_unverified is in __all__."""
        from aimodelshare import modeluser
        assert "decode_token_unverified" in modeluser.__all__


class TestWorkflowEnvironmentVariables:
    """Tests to verify environment variables for CI workflows."""
    
    def test_tf_cpp_log_level_suppression(self):
        """Test that TF_CPP_MIN_LOG_LEVEL can be set."""
        # This is more of a documentation test - we can set the env var
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
        assert os.environ.get("TF_CPP_MIN_LOG_LEVEL") == "2"
        os.environ.pop("TF_CPP_MIN_LOG_LEVEL", None)
    
    def test_optional_warnings_suppression(self):
        """Test that optional warnings can be suppressed via env var."""
        from aimodelshare.utils.optional_deps import check_optional
        
        os.environ["AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS"] = "1"
        
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = check_optional("fake_package_test", "Fake Feature")
                
                assert result is False
                assert len(w) == 0  # No warnings should be emitted
        finally:
            os.environ.pop("AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS", None)


class TestDeprecationPlanDocumentation:
    """Tests for deprecation plan documentation."""
    
    def test_deprecation_plan_exists(self):
        """Test that DEPRECATION_PLAN.md exists."""
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        deprecation_plan = os.path.join(repo_root, "docs", "DEPRECATION_PLAN.md")
        assert os.path.exists(deprecation_plan)
    
    def test_deprecation_plan_content(self):
        """Test that DEPRECATION_PLAN.md has expected sections."""
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        deprecation_plan = os.path.join(repo_root, "docs", "DEPRECATION_PLAN.md")
        
        with open(deprecation_plan, 'r') as f:
            content = f.read()
        
        # Check for key sections
        assert "pkg_resources" in content
        assert "PyJWT" in content
        assert "importlib.metadata" in content
        assert "AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS" in content


class TestUtilsModuleStructure:
    """Tests for utils module structure."""
    
    def test_utils_module_exists(self):
        """Test that utils module exists."""
        from aimodelshare import utils
        assert utils is not None
    
    def test_utils_optional_deps_submodule_exists(self):
        """Test that utils.optional_deps submodule exists."""
        from aimodelshare.utils import optional_deps
        assert optional_deps is not None
    
    def test_check_optional_in_utils_init(self):
        """Test that check_optional is exported from utils.__init__."""
        from aimodelshare.utils import check_optional
        assert check_optional is not None

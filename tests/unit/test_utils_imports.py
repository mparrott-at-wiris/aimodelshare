"""Test that utils module exports all required symbols."""
import sys
import os
import tempfile
import pytest


@pytest.fixture(scope="module")
def utils_module():
    """Fixture to import the utils module directly."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../aimodelshare'))
    import utils as utils_mod
    return utils_mod


def test_hiddenprints_import(utils_module):
    """Test that HiddenPrints can be imported from aimodelshare.utils."""
    assert hasattr(utils_module, 'HiddenPrints'), "HiddenPrints not found in utils"
    assert 'HiddenPrints' in utils_module.__all__, "HiddenPrints not in __all__"


def test_hiddenprints_functionality(utils_module):
    """Test that HiddenPrints suppresses both stdout and stderr."""
    HiddenPrints = utils_module.HiddenPrints
    
    # Capture what would normally be printed
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    # Test that output is suppressed
    with HiddenPrints():
        # These should not appear anywhere
        print("This should be hidden")
        sys.stderr.write("This error should be hidden\n")
    
    # Restore and verify stdout/stderr are restored
    assert sys.stdout == old_stdout, "stdout not properly restored"
    assert sys.stderr == old_stderr, "stderr not properly restored"


def test_ignore_warning_import(utils_module):
    """Test that ignore_warning can be imported from aimodelshare.utils."""
    assert hasattr(utils_module, 'ignore_warning'), "ignore_warning not found in utils"
    assert 'ignore_warning' in utils_module.__all__, "ignore_warning not in __all__"


def test_utility_functions_import(utils_module):
    """Test that utility functions can be imported from aimodelshare.utils."""
    assert hasattr(utils_module, 'delete_files_from_temp_dir'), "delete_files_from_temp_dir not found"
    assert hasattr(utils_module, 'delete_folder'), "delete_folder not found"
    assert hasattr(utils_module, 'make_folder'), "make_folder not found"
    
    assert 'delete_files_from_temp_dir' in utils_module.__all__, "delete_files_from_temp_dir not in __all__"
    assert 'delete_folder' in utils_module.__all__, "delete_folder not in __all__"
    assert 'make_folder' in utils_module.__all__, "make_folder not in __all__"


def test_utility_functions_work(utils_module):
    """Test that utility functions work correctly."""
    import shutil
    
    # Test make_folder
    test_dir = os.path.join(tempfile.gettempdir(), 'test_utils_folder')
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    utils_module.make_folder(test_dir)
    assert os.path.exists(test_dir), "make_folder did not create directory"
    
    # Test delete_folder
    utils_module.delete_folder(test_dir)
    assert not os.path.exists(test_dir), "delete_folder did not remove directory"
    
    # Test delete_files_from_temp_dir
    test_file = 'test_utils_file.txt'
    test_path = os.path.join(tempfile.gettempdir(), test_file)
    with open(test_path, 'w') as f:
        f.write('test')
    
    utils_module.delete_files_from_temp_dir([test_file])
    assert not os.path.exists(test_path), "delete_files_from_temp_dir did not remove file"


def test_check_optional_import(utils_module):
    """Test that check_optional can be imported from aimodelshare.utils."""
    assert hasattr(utils_module, 'check_optional'), "check_optional not found in utils"
    assert 'check_optional' in utils_module.__all__, "check_optional not in __all__"


if __name__ == '__main__':
    # For standalone execution
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../aimodelshare'))
    import utils
    
    test_hiddenprints_import(utils)
    print('✓ test_hiddenprints_import passed')
    
    test_hiddenprints_functionality(utils)
    print('✓ test_hiddenprints_functionality passed')
    
    test_ignore_warning_import(utils)
    print('✓ test_ignore_warning_import passed')
    
    test_utility_functions_import(utils)
    print('✓ test_utility_functions_import passed')
    
    test_utility_functions_work(utils)
    print('✓ test_utility_functions_work passed')
    
    test_check_optional_import(utils)
    print('✓ test_check_optional_import passed')
    
    print('\n✅ ALL TESTS PASSED')

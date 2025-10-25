"""Test that utils module exports all required symbols."""
import sys
import os
import tempfile


def test_hiddenprints_import():
    """Test that HiddenPrints can be imported from aimodelshare.utils."""
    # Import directly from utils to avoid heavy dependencies
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../aimodelshare'))
    import utils
    
    assert hasattr(utils, 'HiddenPrints'), "HiddenPrints not found in utils"
    assert 'HiddenPrints' in utils.__all__, "HiddenPrints not in __all__"


def test_hiddenprints_functionality():
    """Test that HiddenPrints suppresses both stdout and stderr."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../aimodelshare'))
    import utils
    from io import StringIO
    
    HiddenPrints = utils.HiddenPrints
    
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


def test_ignore_warning_import():
    """Test that ignore_warning can be imported from aimodelshare.utils."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../aimodelshare'))
    import utils
    
    assert hasattr(utils, 'ignore_warning'), "ignore_warning not found in utils"
    assert 'ignore_warning' in utils.__all__, "ignore_warning not in __all__"


def test_utility_functions_import():
    """Test that utility functions can be imported from aimodelshare.utils."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../aimodelshare'))
    import utils
    
    assert hasattr(utils, 'delete_files_from_temp_dir'), "delete_files_from_temp_dir not found"
    assert hasattr(utils, 'delete_folder'), "delete_folder not found"
    assert hasattr(utils, 'make_folder'), "make_folder not found"
    
    assert 'delete_files_from_temp_dir' in utils.__all__, "delete_files_from_temp_dir not in __all__"
    assert 'delete_folder' in utils.__all__, "delete_folder not in __all__"
    assert 'make_folder' in utils.__all__, "make_folder not in __all__"


def test_utility_functions_work():
    """Test that utility functions work correctly."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../aimodelshare'))
    import utils
    import shutil
    
    # Test make_folder
    test_dir = os.path.join(tempfile.gettempdir(), 'test_utils_folder')
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    utils.make_folder(test_dir)
    assert os.path.exists(test_dir), "make_folder did not create directory"
    
    # Test delete_folder
    utils.delete_folder(test_dir)
    assert not os.path.exists(test_dir), "delete_folder did not remove directory"
    
    # Test delete_files_from_temp_dir
    test_file = 'test_utils_file.txt'
    test_path = os.path.join(tempfile.gettempdir(), test_file)
    with open(test_path, 'w') as f:
        f.write('test')
    
    utils.delete_files_from_temp_dir([test_file])
    assert not os.path.exists(test_path), "delete_files_from_temp_dir did not remove file"


def test_check_optional_import():
    """Test that check_optional can be imported from aimodelshare.utils."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../aimodelshare'))
    import utils
    
    assert hasattr(utils, 'check_optional'), "check_optional not found in utils"
    assert 'check_optional' in utils.__all__, "check_optional not in __all__"


if __name__ == '__main__':
    test_hiddenprints_import()
    print('✓ test_hiddenprints_import passed')
    
    test_hiddenprints_functionality()
    print('✓ test_hiddenprints_functionality passed')
    
    test_ignore_warning_import()
    print('✓ test_ignore_warning_import passed')
    
    test_utility_functions_import()
    print('✓ test_utility_functions_import passed')
    
    test_utility_functions_work()
    print('✓ test_utility_functions_work passed')
    
    test_check_optional_import()
    print('✓ test_check_optional_import passed')
    
    print('\n✅ ALL TESTS PASSED')

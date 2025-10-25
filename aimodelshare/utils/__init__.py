"""Utility modules for aimodelshare."""
import os
import sys
import shutil
import tempfile
import functools
import warnings
from typing import Type

from .optional_deps import check_optional


def delete_files_from_temp_dir(temp_dir_file_deletion_list):
    temp_dir = tempfile.gettempdir()
    for file_name in temp_dir_file_deletion_list:
        file_path = os.path.join(temp_dir, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)


def delete_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)


def make_folder(folder_path):
    os.makedirs(folder_path, exist_ok=True)


class HiddenPrints:
    """Context manager that suppresses stdout and stderr (used for silencing noisy outputs)."""
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._devnull_stdout = open(os.devnull, 'w')
        self._devnull_stderr = open(os.devnull, 'w')
        sys.stdout = self._devnull_stdout
        sys.stderr = self._devnull_stderr
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        self._devnull_stdout.close()
        self._devnull_stderr.close()


def ignore_warning(warning: Type[Warning]):
    """
    Ignore a given warning occurring during method execution.

    Args:
        warning (Warning): warning type to ignore.

    Returns:
        the inner function
    """

    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=warning)
                return func(*args, **kwargs)

        return wrapper

    return inner


__all__ = [
    "check_optional",
    "HiddenPrints",
    "ignore_warning",
    "delete_files_from_temp_dir",
    "delete_folder",
    "make_folder",
]

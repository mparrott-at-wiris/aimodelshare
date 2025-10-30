#!/usr/bin/env python3
"""
Extended tests for cleanup_test_resources.py focusing on parsing logic and configuration.
These tests avoid AWS operations (use dry_run and do not trigger network calls for deletion).
"""

import sys
import os

# Add parent directory to path to import the cleanup script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.cleanup_test_resources import ResourceCleanup, parse_comma_list


def test_selection_parsing():
    cleanup = ResourceCleanup(dry_run=True)
    assert cleanup._parse_selection('all', 5) == [0,1,2,3,4]
    assert cleanup._parse_selection('none', 5) == []
    assert cleanup._parse_selection('', 5) == []
    assert cleanup._parse_selection('3', 5) == [2]
    assert cleanup._parse_selection('1,3,5', 5) == [0,2,4]
    assert cleanup._parse_selection('2-4', 5) == [1,2,3]
    assert cleanup._parse_selection('1,3-5', 5) == [0,2,3,4]
    assert cleanup._parse_selection('1,1,2,2', 5) == [0,1]
    assert cleanup._parse_selection('1,10,20', 5) == [0]
    print("✓ Selection parsing tests passed")

def test_parse_comma_list():
    assert parse_comma_list(None) == []
    assert parse_comma_list('') == []
    assert parse_comma_list('a') == ['a']
    assert parse_comma_list('a,b,c') == ['a','b','c']
    assert parse_comma_list('  a , b  ,  c ') == ['a','b','c']
    assert parse_comma_list('a,,c') == ['a','c']
    print("✓ Comma list parsing tests passed")

def test_dry_run_flag():
    cleanup_dry = ResourceCleanup(dry_run=True)
    cleanup_prod = ResourceCleanup(dry_run=False)
    assert cleanup_dry.dry_run is True
    assert cleanup_prod.dry_run is False
    print("✓ Dry-run flag tests passed")

def test_region_setting():
    cleanup_us_east = ResourceCleanup(region='us-east-1')
    cleanup_us_west = ResourceCleanup(region='us-west-2')
    assert cleanup_us_east.region == 'us-east-1'
    assert cleanup_us_west.region == 'us-west-2'
    print("✓ Region setting tests passed")


if __name__ == '__main__':
    print("Running cleanup script tests...\n")
    try:
        test_selection_parsing()
        test_parse_comma_list()
        test_dry_run_flag()
        test_region_setting()
        print("\n============================================================")
        print("All tests passed!")
        print("============================================================")
        sys.exit(0)
    except AssertionError as e:
        print("\n============================================================")
        print(f"Test failed: {e}")
        print("============================================================")
        sys.exit(1)
    except Exception as e:
        print("\n============================================================")
        print(f"Unexpected error: {e}")
        print("============================================================")
        import traceback
        traceback.print_exc()
        sys.exit(1)

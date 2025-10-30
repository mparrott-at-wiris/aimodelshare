#!/usr/bin/env python3
"""
Simple test to verify cleanup_test_resources.py basic functionality.
This tests the parsing and selection logic without requiring AWS credentials.
"""

import sys
import os

# Add parent directory to path to import the cleanup script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.cleanup_test_resources import ResourceCleanup


def test_selection_parsing():
    """Test the selection parsing logic."""
    cleanup = ResourceCleanup(dry_run=True)
    
    # Test 'all' selection
    result = cleanup._parse_selection('all', 5)
    assert result == [0, 1, 2, 3, 4], f"Expected [0,1,2,3,4], got {result}"
    
    # Test 'none' selection
    result = cleanup._parse_selection('none', 5)
    assert result == [], f"Expected [], got {result}"
    
    # Test empty selection
    result = cleanup._parse_selection('', 5)
    assert result == [], f"Expected [], got {result}"
    
    # Test single number
    result = cleanup._parse_selection('3', 5)
    assert result == [2], f"Expected [2], got {result}"
    
    # Test comma-separated numbers
    result = cleanup._parse_selection('1,3,5', 5)
    assert result == [0, 2, 4], f"Expected [0,2,4], got {result}"
    
    # Test range
    result = cleanup._parse_selection('2-4', 5)
    assert result == [1, 2, 3], f"Expected [1,2,3], got {result}"
    
    # Test mixed
    result = cleanup._parse_selection('1,3-5', 5)
    assert result == [0, 2, 3, 4], f"Expected [0,2,3,4], got {result}"
    
    # Test duplicates removed
    result = cleanup._parse_selection('1,1,2,2', 5)
    assert result == [0, 1], f"Expected [0,1], got {result}"
    
    # Test out of bounds filtered
    result = cleanup._parse_selection('1,10,20', 5)
    assert result == [0], f"Expected [0], got {result}"
    
    print("✓ All selection parsing tests passed")


def test_dry_run_mode():
    """Test that dry-run mode is properly set."""
    cleanup_dry = ResourceCleanup(dry_run=True)
    assert cleanup_dry.dry_run == True, "Dry-run mode should be True"
    
    cleanup_prod = ResourceCleanup(dry_run=False)
    assert cleanup_prod.dry_run == False, "Dry-run mode should be False"
    
    print("✓ Dry-run mode test passed")


def test_region_configuration():
    """Test that region is properly configured."""
    cleanup_us_east = ResourceCleanup(region='us-east-1')
    assert cleanup_us_east.region == 'us-east-1', "Region should be us-east-1"
    
    cleanup_us_west = ResourceCleanup(region='us-west-2')
    assert cleanup_us_west.region == 'us-west-2', "Region should be us-west-2"
    
    print("✓ Region configuration test passed")


if __name__ == '__main__':
    print("Running cleanup script tests...")
    print()
    
    try:
        test_selection_parsing()
        test_dry_run_mode()
        test_region_configuration()
        
        print()
        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)
        sys.exit(0)
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"Test failed: {e}")
        print("=" * 60)
        sys.exit(1)
    
    except Exception as e:
        print()
        print("=" * 60)
        print(f"Unexpected error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)

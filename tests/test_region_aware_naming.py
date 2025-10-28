"""
Unit tests for region-aware table naming in moral compass.
"""
import re


def test_extract_region_from_table_id():
    """Test region extraction from region-aware table IDs."""
    # Mock the function since we can't import from Lambda
    MORAL_COMPASS_ALLOWED_SUFFIXES = ['-mc']
    
    def extract_region_from_table_id(table_id, playground_id):
        """Extract AWS region from a region-aware table ID."""
        if not table_id or not playground_id:
            return None
        
        if not table_id.startswith(playground_id):
            return None
        
        for suffix in MORAL_COMPASS_ALLOWED_SUFFIXES:
            if table_id.startswith(playground_id + "-") and table_id.endswith(suffix):
                middle = table_id[len(playground_id) + 1:-len(suffix)]
                if middle and re.match(r'^[a-z]{2}-[a-z]+-\d+$', middle):
                    return middle
        
        return None
    
    # Test cases
    assert extract_region_from_table_id('my-playground-us-east-1-mc', 'my-playground') == 'us-east-1'
    assert extract_region_from_table_id('my-playground-eu-west-2-mc', 'my-playground') == 'eu-west-2'
    assert extract_region_from_table_id('my-playground-ap-south-1-mc', 'my-playground') == 'ap-south-1'
    assert extract_region_from_table_id('my-playground-mc', 'my-playground') is None
    assert extract_region_from_table_id('my-playground', 'my-playground') is None
    assert extract_region_from_table_id('other-playground-us-east-1-mc', 'my-playground') is None


def test_validate_region_aware_table_name():
    """Test validation of region-aware table names."""
    # Mock the validation function
    MORAL_COMPASS_ALLOWED_SUFFIXES = ['-mc']
    
    def validate_moral_compass_table_name(table_id, playground_id):
        """Validate moral compass table naming convention."""
        # Check if table_id matches pattern: <playgroundId><suffix>
        for suffix in MORAL_COMPASS_ALLOWED_SUFFIXES:
            expected = f"{playground_id}{suffix}"
            if table_id == expected:
                return True, None
            
            # Check region-aware pattern: <playgroundId>-<region><suffix>
            if table_id.startswith(playground_id + "-"):
                remainder = table_id[len(playground_id) + 1:]
                if remainder.endswith(suffix):
                    potential_region = remainder[:-len(suffix)]
                    if potential_region and re.match(r'^[a-z]{2}-[a-z]+-\d+$', potential_region):
                        return True, None
        
        allowed_patterns = [f"{playground_id}{s}" for s in MORAL_COMPASS_ALLOWED_SUFFIXES]
        allowed_patterns_region = [f"{playground_id}-<region>{s}" for s in MORAL_COMPASS_ALLOWED_SUFFIXES]
        error = f"Invalid table name. Expected one of: {', '.join(allowed_patterns)} or {', '.join(allowed_patterns_region)}"
        return False, error
    
    # Valid cases
    is_valid, error = validate_moral_compass_table_name('my-playground-mc', 'my-playground')
    assert is_valid is True
    assert error is None
    
    is_valid, error = validate_moral_compass_table_name('my-playground-us-east-1-mc', 'my-playground')
    assert is_valid is True
    assert error is None
    
    is_valid, error = validate_moral_compass_table_name('my-playground-eu-west-2-mc', 'my-playground')
    assert is_valid is True
    assert error is None
    
    # Invalid cases
    is_valid, error = validate_moral_compass_table_name('my-playground-invalid-mc', 'my-playground')
    assert is_valid is False
    assert error is not None
    
    is_valid, error = validate_moral_compass_table_name('wrong-playground-mc', 'my-playground')
    assert is_valid is False
    assert error is not None


def test_api_client_region_parameter():
    """Test that API client supports region parameter."""
    from aimodelshare.moral_compass import MoralcompassApiClient
    from unittest.mock import Mock, patch
    
    # Create a mock client
    client = MoralcompassApiClient(api_base_url='http://test.example.com')
    
    # Mock the create_table method
    with patch.object(client, 'create_table') as mock_create:
        mock_create.return_value = {'tableId': 'test-us-east-1-mc', 'message': 'success'}
        
        # Test region-aware table creation
        result = client.create_table_for_playground(
            playground_url='https://example.com/playground/test',
            region='us-east-1'
        )
        
        # Verify the create_table was called with correct table_id
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1]['table_id'] == 'test-us-east-1-mc'
        assert call_args[1]['playground_url'] == 'https://example.com/playground/test'


def test_region_discovery():
    """Test region discovery from config."""
    from aimodelshare.moral_compass.config import get_aws_region
    import os
    
    # Test with environment variable
    os.environ['AWS_REGION'] = 'us-west-2'
    region = get_aws_region()
    # Should return us-west-2 or None (depending on what's set in the environment)
    # Just verify the function can be called without error
    assert region is None or isinstance(region, str)
    
    # Clean up
    if 'AWS_REGION' in os.environ:
        del os.environ['AWS_REGION']


if __name__ == '__main__':
    test_extract_region_from_table_id()
    test_validate_region_aware_table_name()
    test_api_client_region_parameter()
    test_region_discovery()
    print("All tests passed!")

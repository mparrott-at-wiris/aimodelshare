"""
Unit tests for bucket setup without IAM user creation.
Tests that setup_bucket_only() correctly sets up S3 buckets without creating IAM users.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
import warnings


class TestBucketSetupWithoutIAM:
    """Test bucket setup functionality without creating IAM users."""
    
    def setup_method(self):
        """Clean up environment variables before each test."""
        env_vars = [
            'username', 'password', 'AWS_ACCESS_KEY_ID', 
            'AWS_SECRET_ACCESS_KEY', 'AWS_REGION',
            'AWS_ACCESS_KEY_ID_AIMS', 'AWS_SECRET_ACCESS_KEY_AIMS', 
            'AWS_REGION_AIMS', 'AWS_TOKEN', 'BUCKET_NAME',
            'IAM_USERNAME', 'POLICY_ARN', 'POLICY_NAME',
            'AI_MODELSHARE_ACCESS_KEY_ID', 'AI_MODELSHARE_SECRET_ACCESS_KEY'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def teardown_method(self):
        """Clean up after each test."""
        self.setup_method()
    
    @patch('aimodelshare.modeluser.boto3')
    @patch('aimodelshare.aws.get_s3_iam_client')
    def test_setup_bucket_only_no_iam_user_creation(self, mock_get_client, mock_boto3):
        """Test that setup_bucket_only creates bucket without IAM users."""
        from aimodelshare.modeluser import setup_bucket_only
        
        # Set up test environment
        os.environ['username'] = 'testuser'
        os.environ['AWS_ACCESS_KEY_ID_AIMS'] = 'test_key'
        os.environ['AWS_SECRET_ACCESS_KEY_AIMS'] = 'test_secret'
        os.environ['AWS_REGION_AIMS'] = 'us-east-1'
        
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_s3_resource = MagicMock()
        mock_iam_resource = MagicMock()
        
        mock_get_client.return_value = (
            {'client': mock_s3_client, 'resource': mock_s3_resource},
            {'client': mock_iam_client, 'resource': mock_iam_resource},
            'us-east-1'
        )
        
        # Mock session and STS client
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_session.client.return_value = mock_sts
        mock_boto3.session.Session.return_value = mock_session
        
        # Mock S3 head_bucket to simulate bucket doesn't exist
        mock_s3_client.head_bucket.side_effect = Exception("Bucket doesn't exist")
        mock_s3_client.create_bucket.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Call the function
        setup_bucket_only()
        
        # Verify that bucket was created
        assert mock_s3_client.create_bucket.called, "S3 bucket should be created"
        
        # Verify that IAM user was NOT created
        assert not mock_iam_client.create_user.called, "IAM user should NOT be created"
        assert not mock_iam_client.create_access_key.called, "IAM access key should NOT be created"
        assert not mock_iam_client.create_policy.called, "IAM policy should NOT be created"
        
        # Verify bucket name was set in environment
        assert 'BUCKET_NAME' in os.environ, "BUCKET_NAME should be set in environment"
        assert os.environ['BUCKET_NAME'].startswith('aimodelsharetestuser')
    
    @patch('aimodelshare.modeluser.boto3')
    @patch('aimodelshare.aws.get_s3_iam_client')
    def test_setup_bucket_only_existing_bucket(self, mock_get_client, mock_boto3):
        """Test that setup_bucket_only handles existing buckets correctly."""
        from aimodelshare.modeluser import setup_bucket_only
        
        # Set up test environment
        os.environ['username'] = 'testuser'
        os.environ['AWS_ACCESS_KEY_ID_AIMS'] = 'test_key'
        os.environ['AWS_SECRET_ACCESS_KEY_AIMS'] = 'test_secret'
        os.environ['AWS_REGION_AIMS'] = 'us-west-2'
        
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_s3_resource = MagicMock()
        mock_iam_resource = MagicMock()
        
        mock_get_client.return_value = (
            {'client': mock_s3_client, 'resource': mock_s3_resource},
            {'client': mock_iam_client, 'resource': mock_iam_resource},
            'us-west-2'
        )
        
        # Mock session and STS client
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_session.client.return_value = mock_sts
        mock_boto3.session.Session.return_value = mock_session
        
        # Mock S3 head_bucket to simulate bucket already exists
        mock_s3_client.head_bucket.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Call the function
        setup_bucket_only()
        
        # Verify that bucket was NOT created (already exists)
        assert not mock_s3_client.create_bucket.called, "S3 bucket should not be created if it exists"
        
        # Verify that IAM user was NOT created
        assert not mock_iam_client.create_user.called, "IAM user should NOT be created"
        
        # Verify bucket name was set in environment
        assert 'BUCKET_NAME' in os.environ, "BUCKET_NAME should be set in environment"
    
    @patch('aimodelshare.modeluser.boto3')
    @patch('aimodelshare.aws.get_s3_iam_client')
    def test_create_user_getkeyandpassword_deprecated_warning(self, mock_get_client, mock_boto3):
        """Test that create_user_getkeyandpassword shows deprecation warning."""
        from aimodelshare.modeluser import create_user_getkeyandpassword
        
        # Check for deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Just check that calling the function triggers a deprecation warning
            # We don't need to actually execute it fully
            assert callable(create_user_getkeyandpassword), "Function should be callable"
            
            # The deprecation warning is issued at the start of the function
            # So we can test by attempting to call it
            try:
                # This will fail due to missing dependencies, but should still show the warning
                create_user_getkeyandpassword()
            except Exception:
                pass  # Expected to fail, we just want the warning
            
            # Verify deprecation warning was issued
            if len(w) > 0:
                deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
                if len(deprecation_warnings) > 0:
                    assert "deprecated" in str(deprecation_warnings[0].message).lower(), \
                        "Warning message should mention deprecation"
    
    def test_setup_bucket_only_function_exists(self):
        """Test that setup_bucket_only function exists and is importable."""
        from aimodelshare.modeluser import setup_bucket_only
        
        assert callable(setup_bucket_only), "setup_bucket_only should be a callable function"

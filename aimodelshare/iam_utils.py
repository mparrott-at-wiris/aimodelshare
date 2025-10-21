"""
IAM and S3 resource provisioning utilities with idempotent operations.

This module provides helper functions to ensure AWS resources (buckets, roles, policies)
exist and are configured correctly without creating duplicates.
"""
import json
import hashlib
import time
import boto3
from botocore.exceptions import ClientError


def canonical_policy_doc(policy_dict):
    """
    Convert a policy document dictionary to a canonical JSON string.
    
    This ensures consistent comparison of policies by sorting keys and
    removing whitespace variations.
    
    Args:
        policy_dict: Dictionary representing an IAM policy document
        
    Returns:
        Canonical JSON string representation
    """
    return json.dumps(policy_dict, sort_keys=True, separators=(',', ':'))


def policy_hash(policy_dict):
    """
    Generate a hash of a policy document for comparison.
    
    Args:
        policy_dict: Dictionary representing an IAM policy document
        
    Returns:
        SHA256 hash of the canonical policy document
    """
    canonical = canonical_policy_doc(policy_dict)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def ensure_bucket(s3_client, bucket_name, region):
    """
    Ensure an S3 bucket exists, creating it if necessary.
    
    Args:
        s3_client: boto3 S3 client
        bucket_name: Name of the bucket to ensure
        region: AWS region for bucket creation
        
    Returns:
        True if bucket was created, False if it already existed
    """
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return False  # Bucket already exists
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            # Bucket doesn't exist, create it
            if region == "us-east-1":
                s3_client.create_bucket(
                    ACL="private",
                    Bucket=bucket_name
                )
            else:
                location = {'LocationConstraint': region}
                s3_client.create_bucket(
                    ACL="private",
                    Bucket=bucket_name,
                    CreateBucketConfiguration=location
                )
            return True  # Bucket was created
        else:
            # Some other error occurred
            raise


def ensure_role(iam_client, role_name, trust_relationship, description=""):
    """
    Ensure an IAM role exists with the specified trust relationship.
    
    If the role exists but has a different trust relationship, it will be updated.
    
    Args:
        iam_client: boto3 IAM client
        role_name: Name of the role to ensure
        trust_relationship: Dictionary representing the AssumeRolePolicyDocument
        description: Optional description for the role
        
    Returns:
        Tuple (created, updated) indicating if role was created or updated
    """
    trust_policy_json = canonical_policy_doc(trust_relationship)
    
    try:
        # Check if role exists
        response = iam_client.get_role(RoleName=role_name)
        existing_role = response['Role']
        
        # Compare trust relationships
        existing_trust = canonical_policy_doc(existing_role['AssumeRolePolicyDocument'])
        
        if existing_trust != trust_policy_json:
            # Update trust relationship
            iam_client.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(trust_relationship)
            )
            time.sleep(2)  # Allow time for IAM to propagate
            return (False, True)  # Not created, but updated
        
        return (False, False)  # Already exists with correct trust relationship
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            # Role doesn't exist, create it
            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_relationship),
                Description=description
            )
            time.sleep(2)  # Allow time for IAM to propagate
            return (True, False)  # Created, not updated
        else:
            raise


def ensure_managed_policy(iam_client, policy_name, policy_document, description=""):
    """
    Ensure a managed IAM policy exists with the specified policy document.
    
    If the policy exists but the document differs, creates a new version (up to 5).
    If 5 versions exist, deletes the oldest non-default version before creating new one.
    
    Args:
        iam_client: boto3 IAM client
        policy_name: Name of the policy to ensure
        policy_document: Dictionary representing the policy document
        description: Optional description for the policy
        
    Returns:
        Tuple (policy_arn, created, updated) with the policy ARN and status flags
    """
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    
    policy_json = canonical_policy_doc(policy_document)
    
    try:
        # Check if policy exists
        response = iam_client.get_policy(PolicyArn=policy_arn)
        policy = response['Policy']
        
        # Get the default version
        default_version_id = policy['DefaultVersionId']
        version_response = iam_client.get_policy_version(
            PolicyArn=policy_arn,
            VersionId=default_version_id
        )
        
        existing_policy = canonical_policy_doc(
            version_response['PolicyVersion']['Document']
        )
        
        if existing_policy == policy_json:
            return (policy_arn, False, False)  # Already exists with correct document
        
        # Policy exists but document differs - need to create new version
        # First, check how many versions exist
        versions_response = iam_client.list_policy_versions(PolicyArn=policy_arn)
        versions = versions_response['Versions']
        
        # If we have 5 versions (the max), delete the oldest non-default one
        if len(versions) >= 5:
            # Find oldest non-default version
            non_default_versions = [v for v in versions if not v['IsDefaultVersion']]
            if non_default_versions:
                oldest = min(non_default_versions, key=lambda v: v['CreateDate'])
                iam_client.delete_policy_version(
                    PolicyArn=policy_arn,
                    VersionId=oldest['VersionId']
                )
        
        # Create new version
        iam_client.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=json.dumps(policy_document),
            SetAsDefault=True
        )
        time.sleep(2)  # Allow time for IAM to propagate
        return (policy_arn, False, True)  # Not created, but updated
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            # Policy doesn't exist, create it
            response = iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
                Description=description
            )
            time.sleep(2)  # Allow time for IAM to propagate
            return (response['Policy']['Arn'], True, False)  # Created, not updated
        else:
            raise


def ensure_inline_policy(iam_client, role_name, policy_name, policy_document):
    """
    Ensure an inline IAM policy is attached to a role.
    
    If the policy exists but the document differs, it will be updated.
    
    Args:
        iam_client: boto3 IAM client
        role_name: Name of the role to attach the policy to
        policy_name: Name of the inline policy
        policy_document: Dictionary representing the policy document
        
    Returns:
        Tuple (created, updated) indicating if policy was created or updated
    """
    policy_json = canonical_policy_doc(policy_document)
    
    try:
        # Check if inline policy exists
        response = iam_client.get_role_policy(
            RoleName=role_name,
            PolicyName=policy_name
        )
        
        existing_policy = canonical_policy_doc(response['PolicyDocument'])
        
        if existing_policy == policy_json:
            return (False, False)  # Already exists with correct document
        
        # Policy exists but document differs - update it
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        time.sleep(2)  # Allow time for IAM to propagate
        return (False, True)  # Not created, but updated
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            # Policy doesn't exist, create it
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            time.sleep(2)  # Allow time for IAM to propagate
            return (True, False)  # Created, not updated
        else:
            raise


def attach_managed_policy_to_role(iam_client, role_name, policy_arn):
    """
    Attach a managed policy to a role if not already attached.
    
    Args:
        iam_client: boto3 IAM client
        role_name: Name of the role
        policy_arn: ARN of the managed policy
        
    Returns:
        True if policy was attached, False if already attached
    """
    try:
        # Check if policy is already attached
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        attached_policies = response['AttachedPolicies']
        
        if any(p['PolicyArn'] == policy_arn for p in attached_policies):
            return False  # Already attached
        
        # Attach the policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
        time.sleep(2)  # Allow time for IAM to propagate
        return True  # Newly attached
        
    except ClientError as e:
        raise


__all__ = [
    'canonical_policy_doc',
    'policy_hash',
    'ensure_bucket',
    'ensure_role',
    'ensure_managed_policy',
    'ensure_inline_policy',
    'attach_managed_policy_to_role',
]

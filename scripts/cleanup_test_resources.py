#!/usr/bin/env python3
"""
Cleanup script for identifying and deleting test playgrounds and IAM resources.

This script helps manage AWS resources created during testing by:
1. Listing API Gateway REST APIs (playgrounds)
2. Listing IAM users created during set_credentials process
3. Providing interactive selection for deletion
4. Safely deleting selected resources
"""

import os
import sys
import argparse
import boto3
from datetime import datetime
from typing import List, Dict, Tuple


class ResourceCleanup:
    """Manages cleanup of test playgrounds and IAM resources."""
    
    def __init__(self, region: str = 'us-east-1', dry_run: bool = False):
        """
        Initialize cleanup manager.
        
        Args:
            region: AWS region to operate in
            dry_run: If True, only list resources without deleting
        """
        self.region = region
        self.dry_run = dry_run
        self.api_gateway = boto3.client('apigateway', region_name=region)
        self.iam = boto3.client('iam')
        
    def list_playgrounds(self) -> List[Dict]:
        """
        List all API Gateway REST APIs (playgrounds).
        
        Returns:
            List of playground dictionaries with id, name, and creation date
        """
        playgrounds = []
        try:
            paginator = self.api_gateway.get_paginator('get_rest_apis')
            for page in paginator.paginate():
                for api in page.get('items', []):
                    playgrounds.append({
                        'id': api.get('id'),
                        'name': api.get('name'),
                        'created': api.get('createdDate'),
                        'description': api.get('description', 'N/A')
                    })
        except Exception as e:
            print(f"Error listing playgrounds: {e}")
            
        return playgrounds
    
    def list_iam_users(self, prefix: str = 'temporaryaccessAImodelshare') -> List[Dict]:
        """
        List IAM users, optionally filtered by prefix.
        
        Args:
            prefix: Filter users by name prefix (default: temp users created by set_credentials)
            
        Returns:
            List of IAM user dictionaries
        """
        users = []
        try:
            paginator = self.iam.get_paginator('list_users')
            for page in paginator.paginate():
                for user in page.get('Users', []):
                    username = user.get('UserName')
                    # Filter by prefix if provided
                    if not prefix or username.startswith(prefix):
                        users.append({
                            'username': username,
                            'created': user.get('CreateDate'),
                            'user_id': user.get('UserId'),
                            'arn': user.get('Arn')
                        })
        except Exception as e:
            print(f"Error listing IAM users: {e}")
            
        return users
    
    def get_iam_user_resources(self, username: str) -> Dict:
        """
        Get attached policies and access keys for an IAM user.
        
        Args:
            username: IAM username
            
        Returns:
            Dictionary with policies and access keys
        """
        resources = {
            'policies': [],
            'access_keys': []
        }
        
        try:
            # Get attached policies
            policies_response = self.iam.list_attached_user_policies(UserName=username)
            resources['policies'] = policies_response.get('AttachedPolicies', [])
            
            # Get access keys
            keys_response = self.iam.list_access_keys(UserName=username)
            resources['access_keys'] = keys_response.get('AccessKeyMetadata', [])
        except Exception as e:
            print(f"Error getting resources for user {username}: {e}")
            
        return resources
    
    def delete_playground(self, api_id: str) -> bool:
        """
        Delete an API Gateway REST API (playground).
        
        Args:
            api_id: API Gateway REST API ID
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            print(f"[DRY RUN] Would delete playground: {api_id}")
            return True
            
        try:
            self.api_gateway.delete_rest_api(restApiId=api_id)
            print(f"✓ Deleted playground: {api_id}")
            return True
        except Exception as e:
            print(f"✗ Error deleting playground {api_id}: {e}")
            return False
    
    def delete_iam_user(self, username: str) -> bool:
        """
        Delete an IAM user and all associated resources.
        
        This includes:
        - Detaching all policies
        - Deleting inline policies
        - Deleting access keys
        - Deleting the user
        
        Args:
            username: IAM username to delete
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            print(f"[DRY RUN] Would delete IAM user: {username}")
            return True
            
        try:
            # Get all resources for this user
            resources = self.get_iam_user_resources(username)
            
            # Delete access keys
            for key in resources['access_keys']:
                key_id = key['AccessKeyId']
                self.iam.delete_access_key(UserName=username, AccessKeyId=key_id)
                print(f"  ✓ Deleted access key: {key_id}")
            
            # Detach managed policies
            for policy in resources['policies']:
                policy_arn = policy['PolicyArn']
                self.iam.detach_user_policy(UserName=username, PolicyArn=policy_arn)
                print(f"  ✓ Detached policy: {policy['PolicyName']}")
                
                # Delete the policy if it's a custom policy (contains 'temporaryaccess')
                if 'temporaryaccess' in policy_arn.lower():
                    try:
                        self.iam.delete_policy(PolicyArn=policy_arn)
                        print(f"  ✓ Deleted custom policy: {policy['PolicyName']}")
                    except Exception as e:
                        print(f"  ⚠ Could not delete policy {policy['PolicyName']}: {e}")
            
            # Delete inline policies
            inline_policies_response = self.iam.list_user_policies(UserName=username)
            for policy_name in inline_policies_response.get('PolicyNames', []):
                self.iam.delete_user_policy(UserName=username, PolicyName=policy_name)
                print(f"  ✓ Deleted inline policy: {policy_name}")
            
            # Finally, delete the user
            self.iam.delete_user(UserName=username)
            print(f"✓ Deleted IAM user: {username}")
            return True
            
        except Exception as e:
            print(f"✗ Error deleting IAM user {username}: {e}")
            return False
    
    def interactive_cleanup(self):
        """Run interactive cleanup process."""
        print("=" * 60)
        print("AWS Resource Cleanup - Test Playgrounds & IAM Users")
        print("=" * 60)
        print()
        
        # List playgrounds
        print("Fetching playgrounds...")
        playgrounds = self.list_playgrounds()
        
        if playgrounds:
            print(f"\nFound {len(playgrounds)} playground(s):")
            print()
            for i, pg in enumerate(playgrounds, 1):
                created = pg['created'].strftime('%Y-%m-%d %H:%M:%S') if pg['created'] else 'Unknown'
                print(f"{i}. ID: {pg['id']}")
                print(f"   Name: {pg['name']}")
                print(f"   Created: {created}")
                print(f"   Description: {pg['description']}")
                print()
        else:
            print("\nNo playgrounds found.")
            print()
        
        # List IAM users
        print("Fetching IAM users (filtered by 'temporaryaccessAImodelshare' prefix)...")
        iam_users = self.list_iam_users()
        
        if iam_users:
            print(f"\nFound {len(iam_users)} IAM user(s):")
            print()
            for i, user in enumerate(iam_users, 1):
                created = user['created'].strftime('%Y-%m-%d %H:%M:%S') if user['created'] else 'Unknown'
                print(f"{i}. Username: {user['username']}")
                print(f"   Created: {created}")
                print(f"   User ID: {user['user_id']}")
                
                # Show attached resources
                resources = self.get_iam_user_resources(user['username'])
                if resources['policies']:
                    print(f"   Policies: {len(resources['policies'])}")
                if resources['access_keys']:
                    print(f"   Access Keys: {len(resources['access_keys'])}")
                print()
        else:
            print("\nNo IAM users found with the specified prefix.")
            print()
        
        # If nothing found, exit
        if not playgrounds and not iam_users:
            print("No resources to clean up. Exiting.")
            return
        
        # Get user confirmation
        print("=" * 60)
        print("Select resources to delete:")
        print()
        
        if playgrounds:
            print("Playgrounds to delete (enter comma-separated numbers, or 'all' for all, or 'none'):")
            playground_selection = input(f"  [1-{len(playgrounds)}]: ").strip()
            selected_playgrounds = self._parse_selection(playground_selection, len(playgrounds))
        else:
            selected_playgrounds = []
        
        if iam_users:
            print("\nIAM users to delete (enter comma-separated numbers, or 'all' for all, or 'none'):")
            user_selection = input(f"  [1-{len(iam_users)}]: ").strip()
            selected_users = self._parse_selection(user_selection, len(iam_users))
        else:
            selected_users = []
        
        # Show summary and confirm
        print("\n" + "=" * 60)
        print("SUMMARY:")
        if selected_playgrounds:
            print(f"\nPlaygrounds to delete: {len(selected_playgrounds)}")
            for idx in selected_playgrounds:
                pg = playgrounds[idx]
                print(f"  - {pg['name']} ({pg['id']})")
        
        if selected_users:
            print(f"\nIAM users to delete: {len(selected_users)}")
            for idx in selected_users:
                user = iam_users[idx]
                print(f"  - {user['username']}")
        
        if not selected_playgrounds and not selected_users:
            print("\nNo resources selected for deletion.")
            return
        
        print("\n" + "=" * 60)
        if self.dry_run:
            print("DRY RUN MODE - No resources will actually be deleted")
        else:
            print("WARNING: This action cannot be undone!")
            confirmation = input("\nType 'DELETE' to confirm: ").strip()
            if confirmation != 'DELETE':
                print("Deletion cancelled.")
                return
        
        # Perform deletions
        print("\n" + "=" * 60)
        print("Deleting resources...")
        print()
        
        success_count = 0
        failure_count = 0
        
        # Delete playgrounds
        for idx in selected_playgrounds:
            pg = playgrounds[idx]
            if self.delete_playground(pg['id']):
                success_count += 1
            else:
                failure_count += 1
        
        # Delete IAM users
        for idx in selected_users:
            user = iam_users[idx]
            if self.delete_iam_user(user['username']):
                success_count += 1
            else:
                failure_count += 1
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"Cleanup complete: {success_count} successful, {failure_count} failed")
        print("=" * 60)
    
    def _parse_selection(self, selection: str, max_count: int) -> List[int]:
        """
        Parse user selection input.
        
        Args:
            selection: User input string
            max_count: Maximum number of items
            
        Returns:
            List of zero-based indices
        """
        if selection.lower() == 'none' or not selection:
            return []
        
        if selection.lower() == 'all':
            return list(range(max_count))
        
        indices = []
        try:
            parts = selection.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Range like "1-5"
                    start, end = part.split('-')
                    start_idx = int(start.strip()) - 1
                    end_idx = int(end.strip()) - 1
                    indices.extend(range(start_idx, end_idx + 1))
                else:
                    # Single number
                    idx = int(part) - 1
                    indices.append(idx)
            
            # Filter valid indices
            indices = [i for i in indices if 0 <= i < max_count]
            # Remove duplicates and sort
            indices = sorted(list(set(indices)))
        except ValueError:
            print(f"Invalid selection: {selection}")
            return []
        
        return indices


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Cleanup test playgrounds and IAM resources',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive cleanup with dry-run
  python cleanup_test_resources.py --dry-run
  
  # Interactive cleanup in us-east-1
  python cleanup_test_resources.py --region us-east-1
  
  # Interactive cleanup in production mode
  python cleanup_test_resources.py
        """
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List resources without deleting them'
    )
    
    args = parser.parse_args()
    
    # Check for AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
    except Exception as e:
        print("Error: AWS credentials not configured properly.")
        print(f"Details: {e}")
        print("\nPlease configure AWS credentials using one of these methods:")
        print("  1. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        print("  2. Configure AWS CLI (aws configure)")
        print("  3. Use IAM role (if running on EC2 or in GitHub Actions)")
        sys.exit(1)
    
    # Run cleanup
    cleanup = ResourceCleanup(region=args.region, dry_run=args.dry_run)
    cleanup.interactive_cleanup()


if __name__ == '__main__':
    main()

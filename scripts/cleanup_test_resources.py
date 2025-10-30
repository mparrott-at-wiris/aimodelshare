#!/usr/bin/env python3
"""
Cleanup script for identifying and deleting test playgrounds (API Gateway REST APIs) and IAM resources.

Features:
1. List API Gateway REST APIs (playgrounds)
2. List IAM users (with optional substring filter)
3. Interactive selection (legacy mode) OR non-interactive deletion via comma-separated lists
4. Dry-run support
5. Emits copyable comma-separated resource lists for use in GitHub Actions or manual approval workflows

New arguments:
  --playgrounds          Comma-separated list of API Gateway REST API IDs to delete (non-interactive)
  --users                Comma-separated list of IAM usernames to delete (non-interactive)
  --user-filter          Substring to filter IAM usernames when listing (case-insensitive)
  --list-only            List resources and exit (always non-destructive)
  --non-interactive      Force non-interactive mode (no prompts)
  --confirm-delete       Must be exactly 'DELETE' for destructive operations (safety guard)
"""

import os
import sys
import argparse
import boto3
from datetime import datetime
from typing import List, Dict, Tuple, Optional


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
    
    def list_iam_users(self, substring: Optional[str] = None) -> List[Dict]:
        """
        List IAM users, optionally filtered by substring.
        
        Args:
            substring: Case-insensitive substring to match anywhere in username.
            
        Returns:
            List of IAM user dictionaries.
        """
        users = []
        try:
            paginator = self.iam.get_paginator('list_users')
            for page in paginator.paginate():
                for user in page.get('Users', []):
                    username = user.get('UserName')
                    if substring:
                        if substring.lower() not in username.lower():
                            continue
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
                
                # Optional: Delete custom policy if pattern indicates temporary/test
                if any(token in policy_arn.lower() for token in ['temporaryaccess', 'test', 'playground']):
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
    
    def interactive_cleanup(self, user_filter: Optional[str] = None):
        """Legacy interactive cleanup process (kept for local use)."""
        print("=" * 60)
        print("AWS Resource Cleanup - Test Playgrounds & IAM Users (Interactive)")
        print("=" * 60)
        print()
        
        playgrounds = self.list_playgrounds()
        iam_users = self.list_iam_users(substring=user_filter)
        
        # Display lists
        self._display_playgrounds(playgrounds)
        self._display_users(iam_users)
        
        if not playgrounds and not iam_users:
            print("No resources to clean up. Exiting.")
            return
        
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
        
        # Summary
        self._summary_and_delete(playgrounds, iam_users, selected_playgrounds, selected_users)
    
    def non_interactive_cleanup(
        self,
        playground_ids: List[str],
        iam_usernames: List[str],
        confirm_delete: Optional[str]
    ):
        """
        Non-interactive deletion path using explicit lists.
        
        Args:
            playground_ids: List of API Gateway IDs to delete.
            iam_usernames: List of IAM usernames to delete.
            confirm_delete: Must be 'DELETE' if not dry-run to proceed.
        """
        if not playground_ids and not iam_usernames:
            print("No resources provided for deletion. Nothing to do.")
            return
        
        if self.dry_run:
            print("DRY RUN MODE - Will only report actions.")
        else:
            if confirm_delete != 'DELETE':
                print("Missing or incorrect --confirm-delete value. Use --confirm-delete DELETE to proceed.")
                return
        
        success = 0
        failure = 0
        
        print("=" * 60)
        print("Starting non-interactive deletion")
        print(f"Playgrounds: {playground_ids if playground_ids else '[]'}")
        print(f"IAM Users: {iam_usernames if iam_usernames else '[]'}")
        print("=" * 60)
        
        for pid in playground_ids:
            if self.delete_playground(pid):
                success += 1
            else:
                failure += 1
        
        for uname in iam_usernames:
            if self.delete_iam_user(uname):
                success += 1
            else:
                failure += 1
        
        print("\n" + "=" * 60)
        print(f"Deletion complete: {success} successful, {failure} failed")
        print("=" * 60)
    
    def list_and_emit_copyable(self, user_filter: Optional[str] = None):
        """
        List resources and emit copyable comma-separated lists.
        
        Args:
            user_filter: Substring filter for IAM users.
        """
        print("=" * 60)
        print("Listing AWS Test Resources")
        print("=" * 60)
        
        playgrounds = self.list_playgrounds()
        iam_users = self.list_iam_users(substring=user_filter)
        
        self._display_playgrounds(playgrounds)
        self._display_users(iam_users)
        
        pg_ids = ",".join([p['id'] for p in playgrounds])
        user_names = ",".join([u['username'] for u in iam_users])
        
        print("=" * 60)
        print("COPYABLE RESOURCE LISTS")
        print("Paste these (edit as needed) into a delete run:")
        print(f"PLAYGROUND_IDS={pg_ids}")
        print(f"IAM_USERNAMES={user_names}")
        print()
        print("Example delete invocation:")
        print("  python cleanup_test_resources.py --playgrounds PLAYGROUND_IDS --users IAM_USERNAMES --confirm-delete DELETE")
        print("=" * 60)
    
    def _display_playgrounds(self, playgrounds: List[Dict]):
        if playgrounds:
            print(f"\nFound {len(playgrounds)} playground(s):\n")
            for i, pg in enumerate(playgrounds, 1):
                created = pg['created'].strftime('%Y-%m-%d %H:%M:%S') if pg['created'] else 'Unknown'
                print(f"{i}. ID: {pg['id']}")
                print(f"   Name: {pg['name']}")
                print(f"   Created: {created}")
                print(f"   Description: {pg['description']}")
                print()
        else:
            print("\nNo playgrounds found.\n")
    
    def _display_users(self, iam_users: List[Dict]):
        if iam_users:
            print(f"Found {len(iam_users)} IAM user(s):\n")
            for i, user in enumerate(iam_users, 1):
                created = user['created'].strftime('%Y-%m-%d %H:%M:%S') if user['created'] else 'Unknown'
                print(f"{i}. Username: {user['username']}")
                print(f"   Created: {created}")
                print(f"   User ID: {user['user_id']}")
                resources = self.get_iam_user_resources(user['username'])
                if resources['policies']:
                    print(f"   Policies: {len(resources['policies'])}")
                if resources['access_keys']:
                    print(f"   Access Keys: {len(resources['access_keys'])}")
                print()
        else:
            print("No IAM users found with the specified filter.\n")
    
    def _summary_and_delete(self, playgrounds, iam_users, selected_playgrounds, selected_users):
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
            confirmation = input("\nType 'DELETE' to confirm: ").strip()
            if confirmation != 'DELETE':
                print("Deletion cancelled.")
                return
        
        print("\n" + "=" * 60)
        print("Deleting resources...\n")
        
        success_count = 0
        failure_count = 0
        
        for idx in selected_playgrounds:
            pg = playgrounds[idx]
            if self.delete_playground(pg['id']):
                success_count += 1
            else:
                failure_count += 1
        
        for idx in selected_users:
            user = iam_users[idx]
            if self.delete_iam_user(user['username']):
                success_count += 1
            else:
                failure_count += 1
        
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
                    start, end = part.split('-')
                    start_idx = int(start.strip()) - 1
                    end_idx = int(end.strip()) - 1
                    indices.extend(range(start_idx, end_idx + 1))
                else:
                    idx = int(part) - 1
                    indices.append(idx)
            indices = [i for i in indices if 0 <= i < max_count]
            indices = sorted(list(set(indices)))
        except ValueError:
            print(f"Invalid selection: {selection}")
            return []
        
        return indices


def parse_comma_list(value: Optional[str]) -> List[str]:
    """
    Parse a comma-separated string into a list of trimmed non-empty values.
    
    Args:
        value: Comma-separated string or None.
    
    Returns:
        List of strings.
    """
    if not value:
        return []
    return [v.strip() for v in value.split(',') if v.strip()]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Cleanup test playgrounds and IAM resources',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List resources (dry-run listing equivalent)
  python cleanup_test_resources.py --list-only
  
  # List with IAM user filter
  python cleanup_test_resources.py --list-only --user-filter tempaccess
  
  # Non-interactive dry-run deletion preview
  python cleanup_test_resources.py --playgrounds abc123,def456 --users user1,user2 --dry-run
  
  # Perform deletion (requires confirm)
  python cleanup_test_resources.py --playgrounds abc123 --users user1 --confirm-delete DELETE
  
  # Interactive (legacy)
  python cleanup_test_resources.py
        """
    )
    
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--dry-run', action='store_true', help='List or simulate deletion without making changes')
    parser.add_argument('--list-only', action='store_true', help='Only list resources and emit copyable lists, then exit')
    parser.add_argument('--playgrounds', help='Comma-separated API Gateway REST API IDs to delete (non-interactive)')
    parser.add_argument('--users', help='Comma-separated IAM usernames to delete (non-interactive)')
    parser.add_argument('--user-filter', help='Substring filter for IAM usernames (case-insensitive)')
    parser.add_argument('--non-interactive', action='store_true', help='Force non-interactive mode even without explicit lists')
    parser.add_argument('--confirm-delete', help="Must be 'DELETE' to allow actual deletions when not in dry-run")
    
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
    
    cleanup = ResourceCleanup(region=args.region, dry_run=args.dry_run)
    
    playground_list = parse_comma_list(args.playgrounds)
    user_list = parse_comma_list(args.users)
    
    # Decide execution mode
    if args.list_only:
        cleanup.list_and_emit_copyable(user_filter=args.user_filter)
        return
    
    if playground_list or user_list:
        # Non-interactive explicit deletion list
        cleanup.non_interactive_cleanup(playground_list, user_list, args.confirm_delete)
        return
    
    if args.non_interactive:
        # Non-interactive but no IDs supplied: just list and emit copyable lists
        cleanup.list_and_emit_copyable(user_filter=args.user_filter)
        return
    
    # Fallback to interactive mode
    cleanup.interactive_cleanup(user_filter=args.user_filter)


if __name__ == '__main__':
    main()

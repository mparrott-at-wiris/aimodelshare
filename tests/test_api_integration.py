#!/usr/bin/env python3
"""
API Integration Tests for aimodelshare REST API

This script tests all the main API endpoints defined in the Lambda function
to ensure the deployed API is working correctly.
(Updated: test_list_tables_with_data now polls to handle eventual consistency)
"""

import requests
import json
import sys
import time
import uuid
from typing import Dict, Any

class APIIntegrationTests:
    """Test suite for API integration testing"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.test_table_id = f"test-table-{uuid.uuid4().hex[:8]}"
        self.test_username = f"testuser-{uuid.uuid4().hex[:8]}"
        self.headers = {
            'Content-Type': 'application/json'
        }
        self.errors = []
        
    def wait_for_api_ready(self, max_attempts: int = 10, delay: int = 2):
        """Wait for API to be ready by making health check requests"""
        print(f"🔍 Checking API availability...")
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.api_base_url}/tables", timeout=10)
                if response.status_code in [200, 404]:  # Both are valid responses
                    print(f"✅ API is ready (attempt {attempt + 1})")
                    return True
                else:
                    print(f"⏳ API not ready (attempt {attempt + 1}), status: {response.status_code}")
            except Exception as e:
                print(f"⏳ API not ready (attempt {attempt + 1}), error: {str(e)}")
            
            if attempt < max_attempts - 1:
                time.sleep(delay)
                
        print(f"❌ API not ready after {max_attempts} attempts")
        return False
        
    def log_error(self, test_name: str, error_msg: str):
        """Log test errors"""
        self.errors.append(f"{test_name}: {error_msg}")
        print(f"❌ {test_name}: {error_msg}")
        
    def log_success(self, test_name: str):
        """Log test success"""
        print(f"✅ {test_name}: PASSED")
        
    def make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None) -> requests.Response:
        """Make HTTP request with error handling"""
        url = f"{self.api_base_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                return requests.get(url, headers=self.headers, timeout=30)
            elif method.upper() == 'POST':
                return requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method.upper() == 'PUT':
                return requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method.upper() == 'PATCH':
                return requests.patch(url, headers=self.headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out after 30 seconds")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Failed to connect to {url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP error occurred: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
            
    def test_list_tables_empty(self):
        """Test GET /tables when no tables exist yet"""
        test_name = "test_list_tables_empty"
        try:
            response = self.make_request('GET', '/tables')
            if response.status_code == 200:
                data = response.json()
                if 'tables' in data and isinstance(data['tables'], list):
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Invalid response format: {data}")
            else:
                self.log_error(test_name, f"Expected 200, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_create_table(self):
        """Test POST /tables - Create a new table"""
        test_name = "test_create_table"
        try:
            payload = {
                'tableId': self.test_table_id,
                'displayName': f'Test Table {self.test_table_id}'
            }
            response = self.make_request('POST', '/tables', payload)
            if response.status_code == 201:
                data = response.json()
                if data.get('tableId') == self.test_table_id and 'message' in data:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Invalid response data: {data}")
            else:
                self.log_error(test_name, f"Expected 201, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_create_duplicate_table(self):
        """Test POST /tables with duplicate table ID (should fail)"""
        test_name = "test_create_duplicate_table"
        try:
            payload = {
                'tableId': self.test_table_id,
                'displayName': f'Duplicate Test Table'
            }
            response = self.make_request('POST', '/tables', payload)
            if response.status_code == 409:
                data = response.json()
                if 'error' in data:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Missing error in response: {data}")
            else:
                self.log_error(test_name, f"Expected 409, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_get_table(self):
        """Test GET /tables/{tableId} - Get specific table"""
        test_name = "test_get_table"
        try:
            response = self.make_request('GET', f'/tables/{self.test_table_id}')
            if response.status_code == 200:
                data = response.json()
                required_fields = ['tableId', 'displayName', 'createdAt', 'isArchived', 'userCount']
                if all(field in data for field in required_fields) and data['tableId'] == self.test_table_id:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Missing required fields or wrong tableId: {data}")
            else:
                self.log_error(test_name, f"Expected 200, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_get_nonexistent_table(self):
        """Test GET /tables/{tableId} for non-existent table"""
        test_name = "test_get_nonexistent_table"
        try:
            response = self.make_request('GET', '/tables/nonexistent-table-id')
            if response.status_code == 404:
                data = response.json()
                if 'error' in data:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Missing error in response: {data}")
            else:
                self.log_error(test_name, f"Expected 404, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_list_tables_with_data(self):
        """Test GET /tables after creating a table, with polling for eventual consistency."""
        test_name = "test_list_tables_with_data"
        max_attempts = 5
        delay = 2  # seconds
        for attempt in range(max_attempts):
            try:
                response = self.make_request('GET', '/tables')
                if response.status_code == 200:
                    data = response.json()
                    if 'tables' in data and isinstance(data['tables'], list):
                        table_found = any(table.get('tableId') == self.test_table_id for table in data['tables'])
                        if table_found:
                            self.log_success(test_name)
                            return  # Test passed, exit the function
                        else:
                            print(f"  [Attempt {attempt + 1}/{max_attempts}] Test table not yet found, retrying in {delay}s...")
                    else:
                        # Log error but continue to retry
                        print(f"  [Attempt {attempt + 1}/{max_attempts}] Invalid response format, retrying...")
                else:
                    print(f"  [Attempt {attempt + 1}/{max_attempts}] Received status {response.status_code}, retrying...")

            except Exception as e:
                print(f"  [Attempt {attempt + 1}/{max_attempts}] Request failed with error: {e}, retrying...")

            if attempt < max_attempts - 1:
                time.sleep(delay)

        # If the loop finishes without returning, the test has failed
        self.log_error(test_name, f"Test table {self.test_table_id} not found in tables list after {max_attempts} attempts.")

            
    def test_list_users_empty(self):
        """Test GET /tables/{tableId}/users when no users exist"""
        test_name = "test_list_users_empty"
        try:
            response = self.make_request('GET', f'/tables/{self.test_table_id}/users')
            if response.status_code == 200:
                data = response.json()
                if 'users' in data and isinstance(data['users'], list):
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Invalid response format: {data}")
            else:
                self.log_error(test_name, f"Expected 200, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_create_user(self):
        """Test PUT /tables/{tableId}/users/{username} - Create user data"""
        test_name = "test_create_user"
        try:
            payload = {
                'submissionCount': 5,
                'totalCount': 10
            }
            response = self.make_request('PUT', f'/tables/{self.test_table_id}/users/{self.test_username}', payload)
            if response.status_code == 200:
                data = response.json()
                required_fields = ['username', 'submissionCount', 'totalCount', 'message']
                if all(field in data for field in required_fields) and data['username'] == self.test_username:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Invalid response data: {data}")
            else:
                self.log_error(test_name, f"Expected 200, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_get_user(self):
        """Test GET /tables/{tableId}/users/{username} - Get specific user"""
        test_name = "test_get_user"
        try:
            response = self.make_request('GET', f'/tables/{self.test_table_id}/users/{self.test_username}')
            if response.status_code == 200:
                data = response.json()
                required_fields = ['username', 'submissionCount', 'totalCount', 'lastUpdated']
                if all(field in data for field in required_fields) and data['username'] == self.test_username:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Missing required fields: {data}")
            else:
                self.log_error(test_name, f"Expected 200, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_list_users_with_data(self):
        """Test GET /tables/{tableId}/users after creating a user"""
        test_name = "test_list_users_with_data"
        try:
            response = self.make_request('GET', f'/tables/{self.test_table_id}/users')
            if response.status_code == 200:
                data = response.json()
                if 'users' in data and isinstance(data['users'], list) and len(data['users']) > 0:
                    # Check if our test user is in the list
                    user_found = any(user['username'] == self.test_username for user in data['users'])
                    if user_found:
                        self.log_success(test_name)
                    else:
                        self.log_error(test_name, f"Test user {self.test_username} not found in users list")
                else:
                    self.log_error(test_name, f"Invalid users response: {data}")
            else:
                self.log_error(test_name, f"Expected 200, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_update_user(self):
        """Test PUT /tables/{tableId}/users/{username} - Update existing user"""
        test_name = "test_update_user"
        try:
            payload = {
                'submissionCount': 15,
                'totalCount': 25
            }
            response = self.make_request('PUT', f'/tables/{self.test_table_id}/users/{self.test_username}', payload)
            if response.status_code == 200:
                data = response.json()
                if data.get('submissionCount') == 15 and data.get('totalCount') == 25:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Values not updated correctly: {data}")
            else:
                self.log_error(test_name, f"Expected 200, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_patch_table_archive(self):
        """Test PATCH /tables/{tableId} - Archive table"""
        test_name = "test_patch_table_archive"
        try:
            payload = {
                'isArchived': True
            }
            response = self.make_request('PATCH', f'/tables/{self.test_table_id}', payload)
            if response.status_code == 200:
                data = response.json()
                if 'message' in data:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Missing message in response: {data}")
            else:
                self.log_error(test_name, f"Expected 200, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_invalid_table_id_format(self):
        """Test API with invalid table ID format"""
        test_name = "test_invalid_table_id_format"
        try:
            response = self.make_request('GET', '/tables/invalid@table#id!')
            if response.status_code == 400:
                data = response.json()
                if 'error' in data:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Missing error in response: {data}")
            else:
                self.log_error(test_name, f"Expected 400, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def test_invalid_user_data(self):
        """Test PUT user with invalid data"""
        test_name = "test_invalid_user_data"
        try:
            payload = {
                'submissionCount': -5,  # Invalid negative value
                'totalCount': 10
            }
            response = self.make_request('PUT', f'/tables/{self.test_table_id}/users/testuser', payload)
            if response.status_code == 400:
                data = response.json()
                if 'error' in data:
                    self.log_success(test_name)
                else:
                    self.log_error(test_name, f"Missing error in response: {data}")
            else:
                self.log_error(test_name, f"Expected 400, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_error(test_name, str(e))
            
    def run_all_tests(self):
        """Run all API integration tests in order"""
        print(f"🚀 Starting API Integration Tests")
        print(f"🔗 API Base URL: {self.api_base_url}")
        print(f"🧪 Test Table ID: {self.test_table_id}")
        print(f"👤 Test Username: {self.test_username}")
        print("-" * 60)
        
        # Wait for API to be ready before starting tests
        if not self.wait_for_api_ready():
            print("❌ API is not ready, aborting tests")
            return False
        
        # Test order is important - some tests depend on data created by previous tests
        test_methods = [
            self.test_list_tables_empty,
            self.test_create_table,
            self.test_create_duplicate_table,
            self.test_get_table,
            self.test_get_nonexistent_table,
            self.test_list_tables_with_data,
            self.test_list_users_empty,
            self.test_create_user,
            self.test_get_user,
            self.test_list_users_with_data,
            self.test_update_user,
            self.test_patch_table_archive,
            self.test_invalid_table_id_format,
            self.test_invalid_user_data
        ]
        
        for test_method in test_methods:
            test_method()
            time.sleep(0.5)  # Small delay between tests
            
        print("-" * 60)
        if self.errors:
            print(f"❌ {len(self.errors)} test(s) failed:")
            for error in self.errors:
                print(f"   • {error}")
            return False
        else:
            print(f"✅ All {len(test_methods)} tests passed successfully!")
            return True


def main():
    """Main function to run API integration tests"""
    if len(sys.argv) != 2:
        print("Usage: python test_api_integration.py <api_base_url>")
        print("Example: python test_api_integration.py https://abc123.execute-api.us-east-1.amazonaws.com/dev")
        sys.exit(1)
        
    api_base_url = sys.argv[1]
    
    # Validate URL format
    if not api_base_url.startswith(('http://', 'https://')):
        print(f"❌ Invalid API URL format: {api_base_url}")
        sys.exit(1)
        
    # Run tests
    tester = APIIntegrationTests(api_base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

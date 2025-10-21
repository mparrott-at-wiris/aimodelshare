#!/usr/bin/env python3
"""
Pagination Tests for aimodelshare API

Validates pagination logic for:
- GET /tables/{tableId}/users
- GET /tables

Assumptions:
- Pagination defaults: DEFAULT_PAGE_LIMIT=50, MAX_PAGE_LIMIT=500 (Lambda env).
- lastKey is a JSON object returned when additional pages exist.
- In-page sorting only (not global).

Exit code 0 on success, 1 on any failure.
"""
import os
import sys
import json
import time
import uuid
import math
import requests
from typing import Dict, Any, List, Tuple

API_TIMEOUT = 30
PAGE_DEFAULT = 50   # Expected default limit
SMALL_LIMIT = 30    # Used to test explicit limit override
USERS_TOTAL = 105   # 3 pages under default: 50 + 50 + 5
TABLES_TOTAL = 55   # 2 pages: 50 + 5

class PaginationTestFailure(Exception):
    pass

class PaginationTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.errors: List[str] = []
        self.test_table_id = f"pagination-users-{uuid.uuid4().hex[:8]}"
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}

    def log(self, msg: str):
        print(msg)

    def err(self, msg: str):
        print(f"❌ {msg}")
        self.errors.append(msg)

    # ------------------ HTTP helpers ------------------
    def _get(self, path: str, params: Dict[str, Any] = None) -> requests.Response:
        resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=API_TIMEOUT)
        return resp

    def _post(self, path: str, json_body: Dict[str, Any]) -> requests.Response:
        resp = self.session.post(f"{self.base_url}{path}", json=json_body, headers=self.headers, timeout=API_TIMEOUT)
        return resp

    def _put(self, path: str, json_body: Dict[str, Any]) -> requests.Response:
        resp = self.session.put(f"{self.base_url}{path}", json=json_body, headers=self.headers, timeout=API_TIMEOUT)
        return resp

    # ------------------ Setup data ------------------
    def create_table(self, table_id: str):
        r = self._post("/tables", {"tableId": table_id, "displayName": f"Pagination Test Table {table_id}"})
        if r.status_code not in (201, 409):
            self.err(f"Failed to create table {table_id}: {r.status_code} {r.text}")

    def create_user(self, table_id: str, username: str, submission: int, total: int):
        r = self._put(f"/tables/{table_id}/users/{username}", {"submissionCount": submission, "totalCount": total})
        if r.status_code != 200:
            self.err(f"Failed to create user {username}: {r.status_code} {r.text}")

    def bulk_create_users(self):
        self.log(f"Creating {USERS_TOTAL} users for table {self.test_table_id}...")
        for i in range(USERS_TOTAL):
            submission = i + 1
            total = (i + 1) * 2
            username = f"puser-{i:04d}"
            self.create_user(self.test_table_id, username, submission, total)
        self.log("User creation complete.")

    def bulk_create_tables(self):
        self.log(f"Creating {TABLES_TOTAL} tables (metadata items) to exercise list_tables pagination...")
        for i in range(TABLES_TOTAL):
            table_id = f"ptables-{uuid.uuid4().hex[:6]}-{i:03d}"
            self.create_table(table_id)
        self.log("Table creation complete.")

    # ------------------ Pagination Logic Tests ------------------
    def fetch_all_pages(self, path_template: str, item_key: str, limit: int = None) -> Tuple[List[Dict[str, Any]], List[int]]:
        """Generic paginator for users or tables. Returns (all_items, page_sizes)."""
        last_key = None
        all_items: List[Dict[str, Any]] = []
        page_sizes: List[int] = []
        page = 0
        while True:
            params = {}
            if limit:
                params['limit'] = str(limit)
            if last_key:
                params['lastKey'] = json.dumps(last_key)
            r = self._get(path_template, params=params)
            if r.status_code != 200:
                self.err(f"Pagination request failed on page {page}: {r.status_code} {r.text}")
                break
            data = r.json()
            items = data.get(item_key, [])
            all_items.extend(items)
            page_sizes.append(len(items))
            last_key = data.get('lastKey')
            page += 1
            if not last_key:
                break
            if page > 50:  # safety guard
                self.err("Exceeded 50 pages without termination.")
                break
        return all_items, page_sizes

    def test_user_pagination_default(self):
        self.log("Testing user pagination with default limit...")
        items, page_sizes = self.fetch_all_pages(f"/tables/{self.test_table_id}/users", 'users')
        expected_pages = 3  # 50 + 50 + 5
        if len(page_sizes) != expected_pages:
            self.err(f"Expected {expected_pages} pages, got {len(page_sizes)} sizes={page_sizes}")
        if sum(page_sizes) != USERS_TOTAL:
            self.err(f"Expected total {USERS_TOTAL} users, got {sum(page_sizes)}")
        if page_sizes[0] != PAGE_DEFAULT or page_sizes[1] != PAGE_DEFAULT or page_sizes[2] != USERS_TOTAL - 2*PAGE_DEFAULT:
            self.err(f"Unexpected page size distribution: {page_sizes}")
        usernames = {u['username'] for u in items}
        if len(usernames) != USERS_TOTAL:
            self.err("Duplicate or missing users detected in aggregated pages.")
        # In-page descending submissionCount validation
        last_key = None
        for page_index, size in enumerate(page_sizes):
            params = {}
            if last_key:
                params['lastKey'] = json.dumps(last_key)
            r = self._get(f"/tables/{self.test_table_id}/users", params=params)
            data = r.json()
            page_users = data['users']
            last_key = data.get('lastKey')
            subs = [u.get('submissionCount', 0) for u in page_users]
            if subs != sorted(subs, reverse=True):
                self.err(f"Page {page_index} not sorted descending by submissionCount: {subs[:10]}...")

    def test_user_pagination_small_limit(self):
        self.log("Testing user pagination with explicit smaller limit=30...")
        items, page_sizes = self.fetch_all_pages(f"/tables/{self.test_table_id}/users", 'users', limit=SMALL_LIMIT)
        expected_pages = math.ceil(USERS_TOTAL / SMALL_LIMIT)
        if len(page_sizes) != expected_pages:
            self.err(f"Expected {expected_pages} pages, got {len(page_sizes)} sizes={page_sizes}")
        if page_sizes[0] != SMALL_LIMIT:
            self.err("First page did not honor explicit limit=30")

    def test_malformed_last_key(self):
        self.log("Testing malformed lastKey behavior (should ignore and return first page)...")
        params = {"lastKey": "{bad json"}
        r = self._get(f"/tables/{self.test_table_id}/users", params=params)
        if r.status_code != 200:
            self.err(f"Malformed lastKey request failed: {r.status_code}")
        data = r.json()
        users = data.get('users', [])
        if len(users) == 0:
            self.err("Malformed lastKey unexpectedly returned empty user list")
        if len(users) != PAGE_DEFAULT and len(users) != SMALL_LIMIT:
            self.err(f"Malformed lastKey did not return a normal first page size; got {len(users)}")

    def test_table_pagination(self):
        self.log("Testing table pagination with default limit...")
        items, page_sizes = self.fetch_all_pages("/tables", 'tables')
        if page_sizes and page_sizes[0] != PAGE_DEFAULT:
            # Only assert first page size; total tables may include pre-existing ones
            self.err("First tables page did not match default limit 50")
        if page_sizes:
            first_page = items[:page_sizes[0]]
            created_times = [t.get('createdAt') or '' for t in first_page]
            if created_times != sorted(created_times, reverse=True):
                self.err("First page tables not sorted by createdAt descending.")

    def run(self):
        self.log("--- Pagination Test Suite Starting ---")
        self.create_table(self.test_table_id)
        self.bulk_create_users()
        self.bulk_create_tables()
        self.test_user_pagination_default()
        self.test_user_pagination_small_limit()
        self.test_malformed_last_key()
        self.test_table_pagination()
        self.log("--- Pagination Test Suite Complete ---")
        if self.errors:
            self.log("\nFailures:")
            for e in self.errors:
                self.log(f" - {e}")
            raise PaginationTestFailure(f"{len(self.errors)} pagination assertions failed")

def main():
    if len(sys.argv) != 2:
        print("Usage: python tests/test_api_pagination.py <api_base_url>")
        sys.exit(1)
    api_base_url = sys.argv[1]
    if not api_base_url.startswith(('http://', 'https://')):
        print(f"Invalid API URL: {api_base_url}")
        sys.exit(1)
    tester = PaginationTester(api_base_url)
    try:
        tester.run()
    except PaginationTestFailure as e:
        print(str(e))
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()

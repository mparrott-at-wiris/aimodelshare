#!/usr/bin/env python3
"""
Integration tests for generic data endpoints, aggregation, tasks,
moral compass, and session management.

Complements test_api_integration.py (basic CRUD) and test_api_pagination.py.

Usage: python tests/test_api_generic_endpoints.py <api_base_url>
Exit code 0 on success, 1 on any failure.
"""

import json
import os
import sys
import time
import uuid
import requests
from typing import Any, Dict, List

TIMEOUT = 30


class GenericEndpointTests:
    def __init__(self, api_base_url: str, auth_token: str = None, auth_principal: str = None):
        self.base = api_base_url.rstrip("/")
        self.errors: List[str] = []
        self.table_id = f"generic-test-{uuid.uuid4().hex[:8]}"
        # When authenticated, use real principal so is_self checks pass
        self.user_a = auth_principal if auth_principal else f"user-a-{uuid.uuid4().hex[:6]}"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}"})

    # ── helpers ──────────────────────────────────────────────────

    def _ok(self, name: str):
        print(f"  ✅ {name}")

    def _fail(self, name: str, msg: str):
        print(f"  ❌ {name}: {msg}")
        self.errors.append(f"{name}: {msg}")

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> requests.Response:
        return self.session.get(f"{self.base}{path}", params=params, timeout=TIMEOUT)

    def _post(self, path: str, body: Dict[str, Any]) -> requests.Response:
        return self.session.post(f"{self.base}{path}", json=body, timeout=TIMEOUT)

    def _put(self, path: str, body: Dict[str, Any]) -> requests.Response:
        return self.session.put(f"{self.base}{path}", json=body, timeout=TIMEOUT)

    def _patch(self, path: str, body: Dict[str, Any]) -> requests.Response:
        return self.session.patch(f"{self.base}{path}", json=body, timeout=TIMEOUT)

    def _delete(self, path: str) -> requests.Response:
        return self.session.delete(f"{self.base}{path}", timeout=TIMEOUT)

    # ── setup ────────────────────────────────────────────────────

    def setup(self):
        """Create a table and one user for subsequent tests."""
        print(f"\n🔧 Setup: table={self.table_id}, user={self.user_a}")
        r = self._post("/tables", {"tableId": self.table_id, "displayName": "Generic Test Table"})
        if r.status_code != 201:
            self._fail("setup_create_table", f"Expected 201, got {r.status_code}: {r.text}")
            return False

        r = self._put(
            f"/tables/{self.table_id}/users/{self.user_a}",
            {"submissionCount": 5, "totalCount": 10},
        )
        if r.status_code != 200:
            self._fail("setup_create_user", f"Failed to create {self.user_a}: {r.status_code}: {r.text}")
            return False
        return True

    # ── 1. Health ────────────────────────────────────────────────

    def test_health(self):
        name = "health"
        print("\n── Health ──")
        r = self._get("/health")
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}")
        data = r.json()
        for field in ("tableName", "gsiByUserActive", "timestamp"):
            if field not in data:
                return self._fail(name, f"Missing field: {field}")
        self._ok(name)

    # ── 2. Generic data merge ────────────────────────────────────

    def test_put_user_data(self):
        print("\n── Generic Data Merge (PUT /data) ──")

        name = "put_user_data"
        r = self._put(
            f"/tables/{self.table_id}/users/{self.user_a}/data",
            {"favoriteColor": "blue", "score": 42},
        )
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        data = r.json()
        updated = data.get("fieldsUpdated", [])
        if "favoriteColor" not in updated or "score" not in updated:
            return self._fail(name, f"fieldsUpdated missing expected keys: {updated}")
        self._ok(name)

    def test_put_user_data_merge(self):
        """Second PUT merges new fields without losing old ones."""
        name = "put_user_data_merge"
        r = self._put(
            f"/tables/{self.table_id}/users/{self.user_a}/data",
            {"nickname": "ace"},
        )
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        # Verify old + new fields present via GET user
        r2 = self._get(f"/tables/{self.table_id}/users/{self.user_a}")
        if r2.status_code != 200:
            return self._fail(name, f"GET user failed: {r2.status_code}")
        user = r2.json()
        if user.get("favoriteColor") != "blue":
            return self._fail(name, f"Previous field 'favoriteColor' lost after merge: {user}")
        if user.get("nickname") != "ace":
            return self._fail(name, f"New field 'nickname' missing after merge: {user}")
        self._ok(name)

    def test_put_user_data_reserved_field(self):
        name = "put_user_data_reserved_field"
        r = self._put(
            f"/tables/{self.table_id}/users/{self.user_a}/data",
            {"tableId": "hacked"},
        )
        if r.status_code != 400:
            return self._fail(name, f"Expected 400 for reserved field, got {r.status_code}")
        self._ok(name)

    def test_put_user_data_empty_body(self):
        name = "put_user_data_empty_body"
        r = self._put(f"/tables/{self.table_id}/users/{self.user_a}/data", {})
        if r.status_code != 400:
            return self._fail(name, f"Expected 400 for empty body, got {r.status_code}")
        self._ok(name)

    # ── 3. Numeric aggregation ───────────────────────────────────

    def test_numeric_aggregate(self):
        print("\n── Numeric Aggregation ──")

        self._put(f"/tables/{self.table_id}/users/{self.user_a}/data", {"quizScore": 80})
        time.sleep(0.5)

        name = "numeric_aggregate"
        r = self._get(f"/tables/{self.table_id}/aggregate/numeric/quizScore")
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        data = r.json()
        for field in ("fieldName", "average", "totalStudents", "distribution"):
            if field not in data:
                return self._fail(name, f"Missing field: {field}")
        if data["fieldName"] != "quizScore":
            return self._fail(name, f"Wrong fieldName: {data['fieldName']}")
        if data["totalStudents"] < 1:
            return self._fail(name, f"Expected at least 1 student, got {data['totalStudents']}")
        if abs(data["average"] - 80.0) > 0.5:
            return self._fail(name, f"Expected average ~80.0, got {data['average']}")
        self._ok(name)

    def test_numeric_aggregate_missing_field(self):
        name = "numeric_aggregate_missing_field"
        r = self._get(f"/tables/{self.table_id}/aggregate/numeric/nonexistentField")
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}")
        data = r.json()
        if data.get("totalStudents", -1) != 0:
            return self._fail(name, f"Expected 0 students for missing field, got {data}")
        self._ok(name)

    # ── 4. Word aggregation ──────────────────────────────────────

    def test_words_aggregate(self):
        print("\n── Word Aggregation ──")

        name = "words_aggregate"
        field = "favWord"
        r = self._post(
            f"/tables/{self.table_id}/aggregate/words/{field}",
            {"word": "Python", "username": self.user_a},
        )
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        data = r.json()
        if "words" not in data:
            return self._fail(name, f"Missing 'words' in response: {data}")
        words_map = {w["text"]: w["count"] for w in data["words"]}
        if "python" not in words_map:
            return self._fail(name, f"Expected 'python' in words, got: {words_map}")
        self._ok(name)

    # ── 5. Poll aggregation ──────────────────────────────────────

    def test_poll_aggregate(self):
        print("\n── Poll Aggregation ──")

        name = "poll_aggregate"
        poll_id = "favLang"
        self._put(f"/tables/{self.table_id}/users/{self.user_a}/data", {f"poll_{poll_id}": "python"})
        time.sleep(0.5)

        r = self._get(f"/tables/{self.table_id}/aggregate/poll/{poll_id}")
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        data = r.json()
        for field in ("pollId", "responseCount", "distribution"):
            if field not in data:
                return self._fail(name, f"Missing field: {field}")
        if data["responseCount"] < 1:
            return self._fail(name, f"Expected at least 1 response, got {data['responseCount']}")
        if "python" not in data["distribution"]:
            return self._fail(name, f"'python' not in distribution: {data['distribution']}")
        self._ok(name)

    # ── 6. Task management ───────────────────────────────────────

    def test_tasks(self):
        print("\n── Task Management ──")

        prefix = f"/tables/{self.table_id}/users/{self.user_a}/tasks"

        # add tasks
        name = "tasks_add"
        r = self._patch(prefix, {"op": "add", "taskIds": ["t1", "t2", "t3"]})
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        tasks = r.json().get("completedTaskIds", [])
        if set(tasks) != {"t1", "t2", "t3"}:
            return self._fail(name, f"Expected t1,t2,t3 got {tasks}")
        self._ok(name)

        # add more (deduplicated)
        name = "tasks_add_dedup"
        r = self._patch(prefix, {"op": "add", "taskIds": ["t2", "t4"]})
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        tasks = r.json().get("completedTaskIds", [])
        if set(tasks) != {"t1", "t2", "t3", "t4"}:
            return self._fail(name, f"Expected t1-t4 got {tasks}")
        self._ok(name)

        # remove
        name = "tasks_remove"
        r = self._patch(prefix, {"op": "remove", "taskIds": ["t2"]})
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        tasks = r.json().get("completedTaskIds", [])
        if "t2" in tasks:
            return self._fail(name, f"t2 should have been removed: {tasks}")
        self._ok(name)

        # reset
        name = "tasks_reset"
        r = self._patch(prefix, {"op": "reset", "taskIds": ["t10", "t20"]})
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        tasks = r.json().get("completedTaskIds", [])
        if set(tasks) != {"t10", "t20"}:
            return self._fail(name, f"Expected t10,t20 after reset, got {tasks}")
        self._ok(name)

        # delete (clear all)
        name = "tasks_delete"
        r = self._delete(prefix)
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        tasks = r.json().get("completedTaskIds", [])
        if tasks:
            return self._fail(name, f"Expected empty list after delete, got {tasks}")
        self._ok(name)

    def test_tasks_invalid_op(self):
        name = "tasks_invalid_op"
        r = self._patch(
            f"/tables/{self.table_id}/users/{self.user_a}/tasks",
            {"op": "invalid", "taskIds": ["t1"]},
        )
        if r.status_code != 400:
            return self._fail(name, f"Expected 400, got {r.status_code}")
        self._ok(name)

    def test_tasks_invalid_id_format(self):
        name = "tasks_invalid_id_format"
        r = self._patch(
            f"/tables/{self.table_id}/users/{self.user_a}/tasks",
            {"op": "add", "taskIds": ["bad-id"]},
        )
        if r.status_code != 400:
            return self._fail(name, f"Expected 400, got {r.status_code}")
        self._ok(name)

    # ── 7. Moral compass ─────────────────────────────────────────

    def test_moral_compass(self):
        print("\n── Moral Compass ──")

        name = "moral_compass_put"
        r = self._put(
            f"/tables/{self.table_id}/users/{self.user_a}/moral-compass",
            {
                "metrics": {"accuracy": 0.8, "fairness": 0.6},
                "primaryMetric": "accuracy",
                "tasksCompleted": 4,
                "totalTasks": 5,
                "questionsCorrect": 7,
                "totalQuestions": 10,
                "completedTaskIds": ["t1", "t2", "t3", "t4"],
            },
        )
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        data = r.json()
        for field in ("username", "metrics", "moralCompassScore", "tasksCompleted"):
            if field not in data:
                return self._fail(name, f"Missing field: {field}")
        if data["username"] != self.user_a:
            return self._fail(name, f"Wrong username: {data['username']}")
        # score = accuracy * (tasksCompleted + questionsCorrect) / (totalTasks + totalQuestions)
        # = 0.8 * (4 + 7) / (5 + 10) = 0.8 * 11/15 ≈ 0.587
        score = data["moralCompassScore"]
        if not (0.5 < score < 0.7):
            return self._fail(name, f"Score {score} outside expected range 0.5-0.7")
        self._ok(name)

    def test_moral_compass_empty_metrics(self):
        name = "moral_compass_empty_metrics"
        r = self._put(
            f"/tables/{self.table_id}/users/{self.user_a}/moral-compass",
            {"metrics": {}},
        )
        if r.status_code != 400:
            return self._fail(name, f"Expected 400 for empty metrics, got {r.status_code}")
        self._ok(name)

    def test_moral_compass_bad_primary(self):
        name = "moral_compass_bad_primary"
        r = self._put(
            f"/tables/{self.table_id}/users/{self.user_a}/moral-compass",
            {"metrics": {"accuracy": 0.9}, "primaryMetric": "nonexistent"},
        )
        if r.status_code != 400:
            return self._fail(name, f"Expected 400 for bad primaryMetric, got {r.status_code}")
        self._ok(name)

    # ── 8. Session management ────────────────────────────────────

    def test_sessions(self):
        print("\n── Session Management ──")
        session_id = f"sess-{uuid.uuid4().hex[:8]}"
        fake_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.fake"

        # create
        name = "session_create"
        r = self._post("/sessions", {"sessionId": session_id, "token": fake_token})
        if r.status_code != 201:
            return self._fail(name, f"Expected 201, got {r.status_code}: {r.text}")
        data = r.json()
        if data.get("sessionId") != session_id:
            return self._fail(name, f"Wrong sessionId in response: {data}")
        if "expiresAt" not in data:
            return self._fail(name, f"Missing expiresAt: {data}")
        self._ok(name)

        # retrieve
        name = "session_get"
        r = self._get(f"/sessions/{session_id}")
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        data = r.json()
        if data.get("token") != fake_token:
            return self._fail(name, f"Token mismatch: {data}")
        self._ok(name)

        # refresh
        name = "session_refresh"
        new_token = fake_token + ".refreshed"
        r = self._patch(f"/sessions/{session_id}", {"token": new_token})
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}: {r.text}")
        self._ok(name)

        # verify refresh took effect
        name = "session_get_after_refresh"
        r = self._get(f"/sessions/{session_id}")
        if r.status_code != 200:
            return self._fail(name, f"Expected 200, got {r.status_code}")
        if r.json().get("token") != new_token:
            return self._fail(name, f"Token not refreshed: {r.json()}")
        self._ok(name)

    def test_session_not_found(self):
        name = "session_not_found"
        r = self._get("/sessions/nonexistent-session-id")
        if r.status_code != 404:
            return self._fail(name, f"Expected 404, got {r.status_code}")
        self._ok(name)

    # ── runner ───────────────────────────────────────────────────

    def run(self) -> bool:
        print(f"🚀 Generic Endpoint Tests")
        print(f"🔗 {self.base}")
        print("=" * 60)

        if not self.setup():
            print("\n❌ Setup failed — aborting.")
            return False

        self.test_health()

        self.test_put_user_data()
        self.test_put_user_data_merge()
        self.test_put_user_data_reserved_field()
        self.test_put_user_data_empty_body()

        self.test_numeric_aggregate()
        self.test_numeric_aggregate_missing_field()

        self.test_words_aggregate()

        self.test_poll_aggregate()

        self.test_tasks()
        self.test_tasks_invalid_op()
        self.test_tasks_invalid_id_format()

        self.test_moral_compass()
        self.test_moral_compass_empty_metrics()
        self.test_moral_compass_bad_primary()

        self.test_sessions()
        self.test_session_not_found()

        print("\n" + "=" * 60)
        if self.errors:
            print(f"❌ {len(self.errors)} test(s) failed:")
            for e in self.errors:
                print(f"   • {e}")
            return False
        total = 18  # count of test methods above
        print(f"✅ All {total} tests passed!")
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_api_generic_endpoints.py <api_base_url> [auth_token]")
        print("  auth_token can also be set via AUTH_TOKEN env var")
        sys.exit(1)
    url = sys.argv[1]
    auth_token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('AUTH_TOKEN')
    auth_principal = os.environ.get('AUTH_PRINCIPAL')
    if not url.startswith(("http://", "https://")):
        print(f"Invalid URL: {url}")
        sys.exit(1)
    tester = GenericEndpointTests(url, auth_token=auth_token, auth_principal=auth_principal)
    sys.exit(0 if tester.run() else 1)


if __name__ == "__main__":
    main()

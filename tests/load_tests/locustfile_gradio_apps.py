"""
Load tests for Gradio Cloud Run applications.

This suite includes:
- General Gradio app user flows (UI/config/health/prediction) with stable session hashing.
- What Is AI app-focused flows.
- Model Building Game app flows with realistic, paced submissions that exercise the
  prediction cache (run_experiment) while avoiding rapid-fire external submissions.

Key behaviors:
- Unique session per simulated user by default (configurable).
- Stable session_hash equal to sessionid on all POSTs (avoids Gradio queue races).
- Lightweight retries for transient 503s.
- For Model Building Game:
  - Each user submits exactly N models (default 10), one every T seconds (default 30).
  - Submissions use cache-friendly configurations to hit get_cached_prediction().
  - Small interactions NEVER call run_experiment (they target only small-input deps).

Environment variables:
- LOAD_TEST_UNIQUE_SESSIONS=[1|0] (default 1)
- LOAD_TEST_SESSION_ID=<optional base id when unique sessions enabled>
- LOAD_TEST_SUBMISSIONS_PER_USER=<int, default 10>
- LOAD_TEST_SUBMISSION_INTERVAL_SECONDS=<int, default 30>
- LOAD_TEST_USE_AUTH=[true|false] (default false to avoid external submission load)
- LOAD_TEST_AUTH_TOKEN=<string token if using authenticated branch>
"""

import os
import json
import random
import uuid
import time
from locust import HttpUser, task, between, events


# ---------- Helpers to discover fn_index safely from /config ----------

def _fetch_config(client, session_id=None, lang=None):
    try:
        params = {"sessionid": session_id, "lang": lang} if session_id and lang else None
        resp = client.get("/config", params=params, name="Load Config (helper)")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _components_map(cfg):
    return {c.get("id"): c for c in (cfg.get("components", []) if cfg else [])}


def _dependencies(cfg):
    return cfg.get("dependencies", []) or cfg.get("deps", []) if cfg else []


def _find_pred_fn_index(cfg):
    """
    Heuristics to find a typical prediction dependency:
    - Prefer a button labeled "Run AI Prediction" (localized variants).
    - Fallback: dependency with HTML outputs and >= 4 inputs.
    """
    if not cfg:
        return None
    deps = _dependencies(cfg)
    comps = _components_map(cfg)

    button_labels = [
        "Run AI Prediction",
        "Ejecutar predicción de la IA",
        "Executar predicció de la IA",
    ]

    # Pass 1: match by button label
    for d in deps:
        trig_ids = d.get("trigger", []) or d.get("triggers", [])
        labels = [comps.get(t, {}).get("label") for t in trig_ids if t in comps]
        if any(lbl and any(bl in str(lbl) for bl in button_labels) for lbl in labels):
            return d.get("fn_index")

    # Pass 2: outputs include HTML and inputs length >= 4
    for d in deps:
        outs = d.get("outputs", [])
        ins = d.get("inputs", [])
        if any(comps.get(o, {}).get("type") == "html" for o in outs) and len(ins) >= 4:
            return d.get("fn_index")

    # Pass 3: any dep with HTML output
    for d in deps:
        outs = d.get("outputs", [])
        if any(comps.get(o, {}).get("type") == "html" for o in outs):
            return d.get("fn_index")

    return None


def _find_nav_fn_index(cfg):
    """
    Find a navigation-like dependency:
    - Triggered by a button
    - With <= 1 input (common for simple next/complete buttons)
    """
    if not cfg:
        return None, 0
    deps = _dependencies(cfg)
    comps = _components_map(cfg)

    # Prefer a button-triggered dep with exactly 1 input
    for d in deps:
        trig_ids = d.get("trigger", []) or d.get("triggers", [])
        if any(comps.get(t, {}).get("type") == "button" for t in trig_ids if t in comps):
            ins = d.get("inputs", [])
            if len(ins) == 1:
                return d.get("fn_index"), 1

    # Fallback: any button-triggered dep with 0 inputs
    for d in deps:
        trig_ids = d.get("trigger", []) or d.get("triggers", [])
        if any(comps.get(t, {}).get("type") == "button" for t in trig_ids if t in comps):
            ins = d.get("inputs", [])
            if len(ins) == 0:
                return d.get("fn_index"), 0

    # Fallback: any dep with 1 input
    for d in deps:
        ins = d.get("inputs", [])
        if len(ins) == 1:
            return d.get("fn_index"), 1

    return None, 0


def _find_submit_fn_index(cfg):
    """
    Find the fn_index for the Model Building Game 'Build & Submit Model' button.
    Returns (fn_index, inputs_len). Matches button labels containing 'Submit Model'.
    """
    if not cfg:
        return None, 0
    deps = _dependencies(cfg)
    comps = _components_map(cfg)

    target_substrings = [
        "Build & Submit Model",
        "Submit Model",
        "Build and Submit",
        "🔬"  # fallback icon
    ]

    for d in deps:
        trig_ids = d.get("trigger", []) or d.get("triggers", [])
        labels = [comps.get(t, {}).get("label") for t in trig_ids if t in comps]
        if any(lbl and any(s in str(lbl) for s in target_substrings) for lbl in labels):
            ins = d.get("inputs", [])
            return d.get("fn_index"), len(ins)

    # Fallback: largest-input dependency (run_experiment typically has many inputs)
    best = None
    best_len = -1
    for d in deps:
        ins = d.get("inputs", [])
        if len(ins) > best_len:
            best = d
            best_len = len(ins)
    return (best.get("fn_index"), best_len) if best else (None, 0)


def _find_small_input_dep(cfg, max_inputs=2, exclude_fn_index=None):
    """
    Find a safe small-input dependency (<= max_inputs) that is NOT the submit/run_experiment dep.
    Returns (fn_index, inputs_len). If none found, returns (None, 0).
    """
    if not cfg:
        return None, 0
    for d in _dependencies(cfg):
        ins = d.get("inputs", [])
        fn = d.get("fn_index")
        if fn == exclude_fn_index:
            continue
        if len(ins) <= max_inputs:
            return fn, len(ins)
    return None, 0


def _severity_en_options():
    return ["Minor", "Moderate", "Serious"]


def _fail_with_body(response, label):
    try:
        body = response.text
    except Exception:
        body = "<no-body>"
    response.failure(f"{label} failed: status={response.status_code}, body={body[:300]}")


def _post_with_retry(client, url, payload, name, retries=2, backoff=0.2):
    attempt = 0
    while True:
        with client.post(url, json=payload, catch_response=True, name=name) as response:
            if response.status_code in [200, 201]:
                response.success()
                return
            if response.status_code == 404:
                response.success()
                return
            if response.status_code == 503 and attempt < retries:
                response.success()
                time.sleep(backoff * (attempt + 1))
                attempt += 1
                continue
            _fail_with_body(response, name)
            return


def _resolve_session_id():
    unique_flag = os.environ.get("LOAD_TEST_UNIQUE_SESSIONS", "1")
    base = os.environ.get("LOAD_TEST_SESSION_ID", "")
    if unique_flag == "0":
        return base or str(uuid.uuid4())
    return f"{base}-{uuid.uuid4()}" if base else str(uuid.uuid4())


# ---------- General Gradio App User ----------

class GradioAppUser(HttpUser):
    """
    Simulates a user interacting with a generic Gradio app (UI/config/prediction/health).
    """

    wait_time = between(1, 3)

    def on_start(self):
        self.session_id = _resolve_session_id()
        self.lang = random.choice(['en', 'es', 'ca'])
        params = {'sessionid': self.session_id, 'lang': self.lang}
        self.client.get("/", params=params, name="Initial Load with Session")
        time.sleep(random.uniform(0.15, 0.35))
        cfg = _fetch_config(self.client, self.session_id, self.lang)
        self.pred_fn_index = _find_pred_fn_index(cfg) or 1
        self.nav_fn_index, self.nav_inputs_count = _find_nav_fn_index(cfg)

    @task(4)
    def load_app_ui(self):
        params = {'sessionid': self.session_id, 'lang': self.lang}
        with self.client.get("/", params=params, catch_response=True, name="Load UI") as response:
            if response.status_code == 200:
                response.success()
            else:
                _fail_with_body(response, "Load UI")

    @task(2)
    def load_gradio_config(self):
        params = {'sessionid': self.session_id, 'lang': self.lang}
        with self.client.get("/config", params=params, catch_response=True, name="Load Config") as response:
            if response.status_code == 200:
                try:
                    _ = response.json()
                    response.success()
                except Exception:
                    _fail_with_body(response, "Load Config (JSON decode)")
            else:
                _fail_with_body(response, "Load Config")

    @task(12)
    def run_ai_prediction(self):
        sessionid = self.session_id
        lang = self.lang
        fn_index = self.pred_fn_index
        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        severity = random.choice(_severity_en_options())
        url = f"/gradio_api/call/predict?sessionid={sessionid}&lang={lang}"
        payload = {"fn_index": fn_index, "data": [age, priors, severity, lang], "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Run AI Prediction (General App)")

    @task(3)
    def simulate_button_clicks(self):
        if not self.nav_fn_index:
            return
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        data = [random.choice(["Release", "Keep in Prison", "Next", "Complete"])] if self.nav_inputs_count == 1 else []
        payload = {"data": data, "fn_index": self.nav_fn_index, "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Button Click (CPU-intensive)", retries=1)

    @task(1)
    def check_health(self):
        endpoints = ["/", "/healthz", "/health"]
        for endpoint in endpoints:
            params = {"sessionid": self.session_id, "lang": self.lang} if endpoint == "/" else None
            with self.client.get(endpoint, params=params, catch_response=True, name=f"Health Check ({endpoint})") as response:
                if response.status_code == 200:
                    response.success()
                    break
                elif response.status_code == 404:
                    response.success()
                    break
                else:
                    _fail_with_body(response, f"Health Check ({endpoint})")


# ---------- Model Building Game User (Cache-backed, paced submissions) ----------

class ModelBuildingGameUser(HttpUser):
    """
    Model Building Game user that:
    - Submits exactly N models per user (default 10)
    - Spaces submissions by a fixed interval (default 30 seconds)
    - Exercises the prediction cache path in run_experiment
      • Default: preview mode (LOAD_TEST_USE_AUTH=false) → no external submission
      • Optional: authenticated path (LOAD_TEST_USE_AUTH=true + LOAD_TEST_AUTH_TOKEN)
        still uses cached predictions but may post to the external submission API
    - Browses UI/config lightly between submissions
    - Ensures small interactions NEVER call run_experiment
    """

    wait_time = between(1, 3)

    def on_start(self):
        # Per-user session identity
        self.session_id = _resolve_session_id()
        self.lang = random.choice(['en', 'es', 'ca'])

        # Submission schedule/config
        self.submissions_target = int(os.environ.get("LOAD_TEST_SUBMISSIONS_PER_USER", "10"))
        self.submit_interval_sec = int(os.environ.get("LOAD_TEST_SUBMISSION_INTERVAL_SECONDS", "30"))
        self.submissions_done = 0

        # Auth control: default false to avoid external submission load
        self.use_auth = os.environ.get("LOAD_TEST_USE_AUTH", "false").lower() in ("1", "true", "yes")
        self.auth_token = os.environ.get("LOAD_TEST_AUTH_TOKEN")

        # Stagger the very first submission to avoid instant herd behavior
        self.next_submit_at = time.time() + random.uniform(10, 25)

        # Warm the session
        params = {'sessionid': self.session_id, 'lang': self.lang}
        self.client.get("/", params=params, name="Initial Load with Session")
        time.sleep(random.uniform(0.15, 0.35))

        # Discover dependency indices
        cfg = _fetch_config(self.client, self.session_id, self.lang)

        # run_experiment ("Build & Submit Model") dependency
        self.submit_fn_index, self.submit_inputs_len = _find_submit_fn_index(cfg)

        # Find a safe small-input dependency (<=2 inputs), explicitly excluding run_experiment
        self.small_fn_index, self.small_inputs_count = _find_small_input_dep(cfg, max_inputs=2, exclude_fn_index=self.submit_fn_index)

    @task(8)
    def maybe_submit_model_cache_backed(self):
        """
        Submit a model only when due, up to submissions_target per user.
        Sends the full input list expected by run_experiment (typically 14).
        Configurations selected to hit the prediction cache.
        """
        if not self.submit_fn_index:
            return

        now = time.time()
        if self.submissions_done >= self.submissions_target or now < self.next_submit_at:
            return  # Not time yet or we've hit the cap

        # Cache-friendly defaults
        model_choices = [
            "The Balanced Generalist",
            "The Rule-Maker",
            "The 'Nearest Neighbor'",
            "The Deep Pattern-Finder",
        ]
        feature_codes = [
            "juv_fel_count", "juv_misd_count", "juv_other_count",
            "race", "sex", "c_charge_degree", "days_b_screening_arrest",
            "age", "length_of_stay", "priors_count"
        ]
        model_name = random.choice(model_choices)
        complexity = random.choice([2, 4, 6])  # common cached levels
        default_group_1 = ["juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex", "c_charge_degree", "days_b_screening_arrest"]
        extra = random.sample([c for c in feature_codes if c not in default_group_1], k=random.randint(0, 2))
        feature_set = default_group_1 + extra
        data_size = "Small (20%)"  # fastest, typically cached

        team_name = "Load Testers"
        last_submission_score = 0.0
        last_rank = 0
        submission_count = self.submissions_done
        first_submission_score = None if self.submissions_done == 0 else 0.0
        best_score = 0.0
        username = "LoadTester"

        token = self.auth_token if self.use_auth else None
        readiness_flag = True
        was_preview_prev = False

        data = [
            model_name,
            complexity,
            feature_set,
            data_size,
            team_name,
            last_submission_score,
            last_rank,
            submission_count,
            first_submission_score,
            best_score,
            username,
            token,            # token None → preview path; token set → authenticated path
            readiness_flag,
            was_preview_prev,
        ]

        # Ensure we send the full expected count
        if self.submit_inputs_len and len(data) != self.submit_inputs_len:
            if len(data) > self.submit_inputs_len:
                data = data[: self.submit_inputs_len]
            else:
                data = data + [None] * (self.submit_inputs_len - len(data))

        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        payload = {
            "data": data,
            "fn_index": self.submit_fn_index,
            "session_hash": self.session_id,
        }
        _post_with_retry(self.client, url, payload, "Build & Submit Model (Cache-backed)")

        # Schedule the next submission
        self.submissions_done += 1
        self.next_submit_at = now + self.submit_interval_sec

    @task(3)
    def browse_app_ui(self):
        """
        Light browsing between submissions:
        - Load UI shell
        - Load config
        """
        params = {'sessionid': self.session_id, 'lang': self.lang}
        with self.client.get("/", params=params, catch_response=True, name="Load Game UI") as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                _fail_with_body(resp, "Load Game UI")

        with self.client.get("/config", params=params, catch_response=True, name="Load Game Config") as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                _fail_with_body(resp, "Load Game Config")

    @task(1)
    def occasional_small_interaction(self):
        """
        Rare, low-impact interaction to keep the app busy between submissions.
        Uses a safe small-input dependency only. Skips if none found.
        """
        if not self.small_fn_index or self.small_inputs_count == 0:
            return  # No safe small dep discovered; skip

        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        fn_index = self.small_fn_index
        inputs_count = self.small_inputs_count

        # Minimal payload according to inputs_count
        if inputs_count == 2:
            data = [
                random.sample(["feature1", "feature2", "feature3", "feature4"], k=3),
                random.uniform(0.1, 0.9)
            ]
        elif inputs_count == 1:
            data = [random.choice(["Next", "Complete", "Continue"])]
        else:
            data = []

        payload = {"data": data[:inputs_count], "fn_index": fn_index, "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Occasional Small Interaction", retries=1)

    @task(1)
    def check_health(self):
        """
        Health checks; treat 404 for /health(/z) as non-critical if not implemented.
        """
        for endpoint in ["/", "/health", "/healthz"]:
            params = {"sessionid": self.session_id, "lang": self.lang} if endpoint == "/" else None
            with self.client.get(endpoint, params=params, catch_response=True, name=f"Health Check ({endpoint})") as resp:
                if resp.status_code == 200:
                    resp.success()
                    break
                elif resp.status_code == 404:
                    resp.success()
                    break
                else:
                    _fail_with_body(resp, f"Health Check ({endpoint})")


# ---------- What Is AI App User ----------

class WhatIsAIAppUser(HttpUser):
    """
    Dedicated user class for the What Is AI app.
    Focuses traffic on prediction path while keeping UI/config/health coverage.
    """

    wait_time = between(1, 3)

    def on_start(self):
        self.session_id = _resolve_session_id()
        self.lang = random.choice(['en', 'es', 'ca'])
        params = {'sessionid': self.session_id, 'lang': self.lang}
        self.client.get("/", params=params, name="Initial Load with Session")
        time.sleep(random.uniform(0.15, 0.35))
        cfg = _fetch_config(self.client, self.session_id, self.lang)
        self.pred_fn_index = _find_pred_fn_index(cfg) or 1
        self.nav_fn_index, self.nav_inputs_count = _find_nav_fn_index(cfg)

    @task(4)
    def load_app_ui(self):
        params = {'sessionid': self.session_id, 'lang': self.lang}
        with self.client.get("/", params=params, catch_response=True, name="Load UI") as response:
            if response.status_code == 200:
                response.success()
            else:
                _fail_with_body(response, "Load UI (What is AI)")

    @task(2)
    def load_gradio_config(self):
        params = {'sessionid': self.session_id, 'lang': self.lang}
        with self.client.get("/config", params=params, catch_response=True, name="Load Config") as response:
            if response.status_code == 200:
                try:
                    _ = response.json()
                    response.success()
                except Exception:
                    _fail_with_body(response, "Load Config (JSON decode)")
            else:
                _fail_with_body(response, "Load Config")

    @task(20)
    def run_ai_prediction(self):
        fn_index = self.pred_fn_index or 1
        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        lang = self.lang
        severity = random.choice(_severity_en_options())
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={lang}"
        payload = {"data": [age, priors, severity, lang], "fn_index": fn_index, "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Run AI Prediction (What is AI)")

    @task(3)
    def simulate_button_clicks(self):
        fn_index = self.nav_fn_index
        if not fn_index:
            return
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        data = [random.choice(["Next", "Complete", "Continue"])] if self.nav_inputs_count == 1 else []
        payload = {"data": data, "fn_index": fn_index, "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Button Click (Navigation/UI)", retries=1)

    @task(1)
    def check_health(self):
        endpoints = ["/", "/healthz", "/health"]
        for endpoint in endpoints:
            params = {"sessionid": self.session_id, "lang": self.lang} if endpoint == "/" else None
            with self.client.get(endpoint, params=params, catch_response=True, name=f"Health Check ({endpoint})") as response:
                if response.status_code == 200:
                    response.success()
                    break
                elif response.status_code == 404:
                    response.success()
                    break
                else:
                    _fail_with_body(response, f"Health Check ({endpoint})")


# ---------- Event handlers for reporting ----------

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "="*80)
    print("🚀 Starting Gradio App Load Test")
    print("="*80)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "="*80)
    print("✅ Load Test Complete")
    print("="*80)

    stats = environment.stats
    print(f"\n📊 Summary Statistics:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Failed Requests: {stats.total.num_failures}")
    print(f"  Success Rate: {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0:.2f}%")
    print(f"  Median Response Time: {stats.total.median_response_time:.0f}ms")
    print(f"  95th Percentile: {stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"  99th Percentile: {stats.total.get_response_time_percentile(0.99):.0f}ms")
    print(f"  Average Response Time: {stats.total.avg_response_time:.0f}ms")
    print(f"  Min Response Time: {stats.total.min_response_time:.0f}ms")
    print(f"  Max Response Time: {stats.total.max_response_time:.0f}ms")
    print(f"  Requests/sec: {stats.total.total_rps:.2f}")
    print("="*80 + "\n")

    success_rate = ((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0
    p95_latency = stats.total.get_response_time_percentile(0.95)

    print("📋 Success Criteria Check:")
    print(f"  ✓ Success Rate > 99%: {'PASS' if success_rate > 99 else 'FAIL'} ({success_rate:.2f}%)")
    print(f"  ✓ P95 Latency < 1000ms: {'PASS' if p95_latency < 1000 else 'FAIL'} ({p95_latency:.0f}ms)")
    print(f"  ✓ Failed Requests < 1%: {'PASS' if stats.total.num_failures / stats.total.num_requests * 100 < 1 else 'FAIL' if stats.total.num_requests > 0 else 'N/A'}")

    if success_rate > 99 and p95_latency < 1000:
        print("\n🎉 All criteria met! App is ready for production.\n")
    else:
        print("\n⚠️  Some criteria not met. Review configuration and resource allocation.\n")

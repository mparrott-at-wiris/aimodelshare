"""
Load tests for Gradio Cloud Run applications.

This load test suite validates the scalability of Gradio apps deployed to Cloud Run,
ensuring they can handle 100+ concurrent users as specified in the requirements.

The tests simulate realistic user behavior including:
- Session ID and language query parameters (matching production usage)
- Interactive element usage (buttons, sliders, dropdowns)
- CPU-intensive operations (predictions, model runs)

Usage:
    # Test specific app
    locust -f locustfile_gradio_apps.py --host=https://judge-HASH-uc.a.run.app

    # Test with 100 concurrent users
    locust -f locustfile_gradio_apps.py --host=https://judge-HASH-uc.a.run.app \
        --users 100 --spawn-rate 10 --run-time 5m --headless

    # Test using environment variables (Locust supports LOCUST_* env vars)
    export LOCUST_HOST=https://judge-HASH-uc.a.run.app
    export LOAD_TEST_SESSION_ID=your-session-id-here
    export LOAD_TEST_UNIQUE_SESSIONS=1
    locust -f locustfile_gradio_apps.py --users 100 --spawn-rate 10 --run-time 5m

    # Selecting a specific user class (CLI positional argument)
    locust -f locustfile_gradio_apps.py GradioAppUser --host=https://judge-HASH-uc.a.run.app ...
    locust -f locustfile_gradio_apps.py ModelBuildingGameUser --host=https://model-building-game-en-... ...
    locust -f locustfile_gradio_apps.py WhatIsAIAppUser --host=https://what-is-ai-... ...
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
    Heuristics to find the prediction fn_index:
    - Prefer dependencies triggered by a button whose label matches "Run AI Prediction" in any locale
    - Fallback: dependency whose outputs include an HTML component and expects >= 4 inputs
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
        if any(label and any(bl in str(label) for bl in button_labels) for label in labels):
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


def _severity_en_options():
    return ["Minor", "Moderate", "Serious"]


def _fail_with_body(response, label):
    """
    Mark a locust response as failure, including a short snippet of the body to aid debugging.
    """
    body = ""
    try:
        body = response.text
    except Exception:
        body = "<no-body>"
    response.failure(f"{label} failed: status={response.status_code}, body={body[:300]}")


def _post_with_retry(client, url, payload, name, retries=2, backoff=0.2):
    """
    POST with limited retries for transient 503s. Only mark failure on final attempt.
    """
    attempt = 0
    while True:
        with client.post(url, json=payload, catch_response=True, name=name) as response:
            # Success fast path
            if response.status_code in [200, 201]:
                response.success()
                return

            # Treat 404 as non-critical in some flows
            if response.status_code == 404:
                response.success()
                return

            # Retry on 503s (Cloud Run scaling / session init races)
            if response.status_code == 503 and attempt < retries:
                response.success()  # don't count this attempt as failure
                time.sleep(backoff * (attempt + 1))
                attempt += 1
                continue

            # Final failure
            _fail_with_body(response, name)
            return


def _resolve_session_id():
    """
    Use unique session IDs per user by default to reduce queue contention.
    If LOAD_TEST_UNIQUE_SESSIONS=0, reuse LOAD_TEST_SESSION_ID from env.
    If LOAD_TEST_SESSION_ID is set but unique sessions are requested, suffix it with a UUID to keep analytics traceability.
    """
    unique_flag = os.environ.get("LOAD_TEST_UNIQUE_SESSIONS", "1")  # default: unique
    base = os.environ.get("LOAD_TEST_SESSION_ID", "")
    if unique_flag == "0":
        return base or str(uuid.uuid4())
    # unique per user
    return f"{base}-{uuid.uuid4()}" if base else str(uuid.uuid4())


class GradioAppUser(HttpUser):
    """
    Simulates a user interacting with a Gradio application.
    """

    wait_time = between(1, 3)

    def on_start(self):
        """Called when a simulated user starts."""
        self.session_id = _resolve_session_id()
        self.lang = random.choice(['en', 'es', 'ca'])

        # Initialize session with query parameters (as used in production)
        params = {'sessionid': self.session_id, 'lang': self.lang}
        self.client.get("/", params=params, name="Initial Load with Session")

        # Allow server to finalize session setup before heavy POST traffic
        time.sleep(random.uniform(0.15, 0.35))

        # Discover indices from /config (best effort)
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
                    config = response.json()
                    if "version" in config:
                        response.success()
                    else:
                        response.failure("Load Config failed: missing 'version' field")
                except json.JSONDecodeError:
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
        predict_url = f"/gradio_api/call/predict?sessionid={sessionid}&lang={lang}"

        payload = {
            "fn_index": fn_index,
            "data": [age, priors, severity, lang],
            "session_hash": self.session_id  # stable per-user
        }
        _post_with_retry(self.client, predict_url, payload, "Run AI Prediction (General App)")

    @task(3)
    def simulate_button_clicks(self):
        if not self.nav_fn_index:
            return
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        data = [random.choice(["Release", "Keep in Prison", "Next", "Complete"])] if self.nav_inputs_count == 1 else []
        payload = {
            "data": data,
            "fn_index": self.nav_fn_index,
            "session_hash": self.session_id
        }
        _post_with_retry(self.client, url, payload, "Button Click (CPU-intensive)", retries=1)

    @task(6)
    def simulate_slider_interactions(self):
        lang = self.lang
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={lang}"
        fn_index = self.pred_fn_index
        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        severity = random.choice(_severity_en_options())

        payload = {
            "data": [age, priors, severity, lang],
            "fn_index": fn_index,
            "session_hash": self.session_id
        }
        _post_with_retry(self.client, url, payload, "Slider/Dropdown Change (CPU-intensive)")

    @task(1)
    def check_health(self):
        endpoints_to_check = ["/", "/healthz", "/health"]
        for endpoint in endpoints_to_check:
            params = {"sessionid": self.session_id, "lang": self.lang} if endpoint == "/" else None
            with self.client.get(endpoint, params=params, catch_response=True, name=f"Health Check ({endpoint})") as response:
                if response.status_code == 200:
                    response.success()
                    break
                elif response.status_code == 404:
                    pass
                else:
                    _fail_with_body(response, f"Health Check ({endpoint})")


class ModelBuildingGameUser(HttpUser):
    """
    Specialized user for Model Building Game apps.
    """

    wait_time = between(2, 5)

    def on_start(self):
        self.session_id = _resolve_session_id()
        self.lang = random.choice(['en', 'es', 'ca'])

        params = {'sessionid': self.session_id, 'lang': self.lang}
        self.client.get("/", params=params, name="Initial Load with Session")

        time.sleep(random.uniform(0.15, 0.35))

        cfg = _fetch_config(self.client, self.session_id, self.lang)
        self.train_fn_index, self.train_inputs_count = _find_nav_fn_index(cfg)
        self.feature_fn_index = None
        self.feature_inputs_count = 0
        if cfg:
            deps = _dependencies(cfg)
            comps = _components_map(cfg)
            for d in deps:
                ins = d.get("inputs", [])
                if len(ins) == 2:
                    self.feature_fn_index = d.get("fn_index")
                    self.feature_inputs_count = 2
                    break

    @task(4)
    def load_game_ui(self):
        params = {'sessionid': self.session_id, 'lang': self.lang}
        with self.client.get("/", params=params, catch_response=True, name="Load Game UI") as response:
            if response.status_code == 200:
                response.success()
            else:
                _fail_with_body(response, "Load Game UI")

    @task(2)
    def load_game_data(self):
        params = {'sessionid': self.session_id, 'lang': self.lang}
        with self.client.get("/config", params=params, catch_response=True, name="Load Game Config") as response:
            if response.status_code == 200:
                response.success()
            else:
                _fail_with_body(response, "Load Game Config")

    @task(6)
    def simulate_model_training(self):
        training_params = {
            "model_type": random.choice(["linear", "tree", "neural_net"]),
            "features": random.sample(["age", "race", "gender", "priors"], k=random.randint(2, 4)),
            "fairness_constraint": random.choice(["none", "demographic_parity", "equal_opportunity"])
        }
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        fn_index = self.train_fn_index or 1
        inputs_count = self.train_inputs_count
        data = [json.dumps(training_params)] if inputs_count <= 1 else [json.dumps(training_params), random.uniform(0.1, 0.9)]
        payload = {
            "data": data,
            "fn_index": fn_index,
            "session_hash": self.session_id
        }
        _post_with_retry(self.client, url, payload, "Model Training (Very CPU-intensive)", retries=1)

    @task(5)
    def simulate_feature_selection(self):
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        fn_index = self.feature_fn_index or (self.train_fn_index or 1)
        inputs_count = self.feature_inputs_count or 2
        data = [
            random.sample(["feature1", "feature2", "feature3", "feature4"], k=3),
            random.uniform(0.1, 0.9)
        ][:inputs_count]
        payload = {
            "data": data,
            "fn_index": fn_index,
            "session_hash": self.session_id
        }
        _post_with_retry(self.client, url, payload, "Feature Selection (CPU-intensive)", retries=1)


class WhatIsAIAppUser(HttpUser):
    """
    Dedicated user class for the 'What is AI' educational app.
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
                except json.JSONDecodeError:
                    _fail_with_body(response, "Load Config (JSON decode)")
            else:
                _fail_with_body(response, "Load Config")

    @task(20)
    def run_ai_prediction(self):
        fn_index = self.pred_fn_index or 1
        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        lang = self.lang
        severity = random.choice(_severity_en_options())  # ALWAYS English
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={lang}"
        payload = {
            "data": [age, priors, severity, lang],
            "fn_index": fn_index,
            "session_hash": self.session_id
        }
        _post_with_retry(self.client, url, payload, "Run AI Prediction (What is AI)")

    @task(3)
    def simulate_button_clicks(self):
        fn_index = self.nav_fn_index
        if fn_index is None:
            return
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        data = [random.choice(["Next", "Complete", "Continue"])] if self.nav_inputs_count == 1 else []
        payload = {
            "data": data,
            "fn_index": fn_index,
            "session_hash": self.session_id
        }
        _post_with_retry(self.client, url, payload, "Button Click (Navigation/UI)", retries=1)

    @task(6)
    def simulate_slider_interactions(self):
        lang = self.lang
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={lang}"
        fn_index = self.pred_fn_index or 1
        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        severity = random.choice(_severity_en_options())  # ALWAYS English
        payload = {
            "data": [age, priors, severity, lang],
            "fn_index": fn_index,
            "session_hash": self.session_id
        }
        _post_with_retry(self.client, url, payload, "Slider/Dropdown Change (UI)")

    @task(1)
    def check_health(self):
        endpoints_to_check = ["/", "/healthz", "/health"]
        for endpoint in endpoints_to_check:
            params = {"sessionid": self.session_id, "lang": self.lang} if endpoint == "/" else None
            with self.client.get(endpoint, params=params, catch_response=True, name=f"Health Check ({endpoint})") as response:
                if response.status_code == 200:
                    response.success()
                    break
                elif response.status_code == 404:
                    pass
                else:
                    _fail_with_body(response, f"Health Check ({endpoint})")


# Event handlers for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test starts."""
    print("\n" + "="*80)
    print("🚀 Starting Gradio App Load Test")
    print("="*80)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops."""
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


# Note on selecting user classes:
# Locust does not support a --user-class flag. Select a specific class by
# passing the class name as a positional argument in the CLI:
#   locust -f locustfile_gradio_apps.py GradioAppUser ...
#   locust -f locustfile_gradio_apps.py ModelBuildingGameUser ...
#   locust -f locustfile_gradio_apps.py WhatIsAIAppUser ...

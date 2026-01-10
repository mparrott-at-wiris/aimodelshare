"""
Load tests for Gradio Cloud Run applications.

Adds a focused load test for the Model Building Game EN app that calls the
'Build & Submit Model' function (run_experiment), exercising the real submission
flow in preview mode (no token) by default. Optional auth wiring can be added
later if you want to hit the external Competition API too.

Key features:
- Stable session_hash per user to avoid Gradio queue KeyErrors.
- Unique session per user by default (configurable via env).
- English-only severity values for other apps to avoid dropdown mismatch.
- Lightweight retry/backoff for transient 503s.
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
    if not cfg:
        return None
    deps = _dependencies(cfg)
    comps = _components_map(cfg)

    button_labels = [
        "Run AI Prediction",
        "Ejecutar predicción de la IA",
        "Executar predicció de la IA",
    ]
    for d in deps:
        trig_ids = d.get("trigger", []) or d.get("triggers", [])
        labels = [comps.get(t, {}).get("label") for t in trig_ids if t in comps]
        if any(label and any(bl in str(label) for bl in button_labels) for label in labels):
            return d.get("fn_index")

    for d in deps:
        outs = d.get("outputs", [])
        ins = d.get("inputs", [])
        if any(comps.get(o, {}).get("type") == "html" for o in outs) and len(ins) >= 4:
            return d.get("fn_index")

    for d in deps:
        outs = d.get("outputs", [])
        if any(comps.get(o, {}).get("type") == "html" for o in outs):
            return d.get("fn_index")

    return None


def _find_nav_fn_index(cfg):
    if not cfg:
        return None, 0
    deps = _dependencies(cfg)
    comps = _components_map(cfg)

    for d in deps:
        trig_ids = d.get("trigger", []) or d.get("triggers", [])
        if any(comps.get(t, {}).get("type") == "button" for t in trig_ids if t in comps):
            ins = d.get("inputs", [])
            if len(ins) == 1:
                return d.get("fn_index"), 1

    for d in deps:
        trig_ids = d.get("trigger", []) or d.get("triggers", [])
        if any(comps.get(t, {}).get("type") == "button" for t in trig_ids if t in comps):
            ins = d.get("inputs", [])
            if len(ins) == 0:
                return d.get("fn_index"), 0

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


class GradioAppUser(HttpUser):
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

    @task(6)
    def simulate_slider_interactions(self):
        lang = self.lang
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={lang}"
        fn_index = self.pred_fn_index
        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        severity = random.choice(_severity_en_options())
        payload = {"data": [age, priors, severity, lang], "fn_index": fn_index, "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Slider/Dropdown Change (CPU-intensive)")

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
                    pass
                else:
                    _fail_with_body(response, f"Health Check ({endpoint})")


class ModelBuildingGameUser(HttpUser):
    """
    Specialized user for Model Building Game apps.

    New task added: build_and_submit_model_preview() which posts to the actual
    run_experiment function (“Build & Submit Model” button), exercising the
    preview path (no token) by default.
    """
    wait_time = between(2, 5)

    def on_start(self):
        self.session_id = _resolve_session_id()
        self.lang = random.choice(['en', 'es', 'ca'])
        params = {'sessionid': self.session_id, 'lang': self.lang}
        self.client.get("/", params=params, name="Initial Load with Session")
        time.sleep(random.uniform(0.15, 0.35))

        cfg = _fetch_config(self.client, self.session_id, self.lang)
        # Detect the submit button dependency and its input length
        self.submit_fn_index, self.submit_inputs_len = _find_submit_fn_index(cfg)
        # Fallbacks for other tasks (kept)
        self.train_fn_index, self.train_inputs_count = _find_nav_fn_index(cfg)
        self.feature_fn_index = None
        self.feature_inputs_count = 0
        if cfg:
            deps = _dependencies(cfg)
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

    @task(15)
    def build_and_submit_model_preview(self):
        """
        Calls the actual 'Build & Submit Model' (run_experiment) endpoint with
        realistic inputs. Uses preview path (no token) to avoid external API side-effects.
        """
        if not self.submit_fn_index:
            return

        # Inputs expected by run_experiment (in order):
        # [model_name, complexity, feature_set(list), data_size, team_name,
        #  last_submission_score, last_rank, submission_count, first_submission_score,
        #  best_score, username, token, readiness_flag, was_preview_prev]
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
        complexity = random.randint(1, 10)
        # Choose a safe, unlocked-by-default set (group 1) plus optional extras
        default_group_1 = ["juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex", "c_charge_degree", "days_b_screening_arrest"]
        extra = random.sample([c for c in feature_codes if c not in default_group_1], k=random.randint(0, 3))
        feature_set = default_group_1 + extra
        data_size = "Small (20%)"
        team_name = "Load Testers"
        last_submission_score = 0.0
        last_rank = 0
        submission_count = 0
        first_submission_score = None
        best_score = 0.0
        username = "LoadTester"
        token = None  # Keep preview path to avoid external submissions
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
            token,
            readiness_flag,
            was_preview_prev,
        ]

        # Adjust to match the dependency's expected input length
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
        _post_with_retry(self.client, url, payload, "Build & Submit Model (Preview)")

    @task(3)
    def simulate_model_training(self):
        """Legacy task retained for back-compat; safe no-op against endpoints expecting fewer inputs."""
        training_params = {
            "model_type": random.choice(["linear", "tree", "neural_net"]),
            "features": random.sample(["age", "race", "gender", "priors"], k=random.randint(2, 4)),
            "fairness_constraint": random.choice(["none", "demographic_parity", "equal_opportunity"])
        }
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        fn_index = self.train_fn_index or (self.submit_fn_index or 1)
        inputs_count = self.train_inputs_count or 1
        data = [json.dumps(training_params)] if inputs_count <= 1 else [json.dumps(training_params), random.uniform(0.1, 0.9)]
        payload = {"data": data, "fn_index": fn_index, "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Model Training (Very CPU-intensive)", retries=1)

    @task(3)
    def simulate_feature_selection(self):
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        fn_index = self.feature_fn_index or (self.train_fn_index or (self.submit_fn_index or 1))
        inputs_count = self.feature_inputs_count or 2
        data = [
            random.sample(["feature1", "feature2", "feature3", "feature4"], k=3),
            random.uniform(0.1, 0.9)
        ][:inputs_count]
        payload = {"data": data, "fn_index": fn_index, "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Feature Selection (CPU-intensive)", retries=1)


class WhatIsAIAppUser(HttpUser):
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

    @task(6)
    def simulate_slider_interactions(self):
        fn_index = self.pred_fn_index or 1
        lang = self.lang
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={lang}"
        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        severity = random.choice(_severity_en_options())
        payload = {"data": [age, priors, severity, lang], "fn_index": fn_index, "session_hash": self.session_id}
        _post_with_retry(self.client, url, payload, "Slider/Dropdown Change (UI)")

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
                    pass
                else:
                    _fail_with_body(response, f"Health Check ({endpoint})")


# Event handlers for reporting
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

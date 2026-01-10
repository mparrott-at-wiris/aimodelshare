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


class ModelBuildingGameUser(HttpUser):
    """
    Model Building Game user that:
    - Submits exactly N models per user (default 10)
    - Spaces submissions by a fixed interval (default 30 seconds)
    - Exercises the cache-backed submission path in run_experiment by default (token provided if configured)
    - Browses UI/config lightly between submissions
    - Ensures small interactions NEVER call run_experiment
    """

    wait_time = between(1, 3)

    def on_start(self):
        self.session_id = _resolve_session_id()
        self.lang = random.choice(['en', 'es', 'ca'])

        # Submission schedule/config
        self.submissions_target = int(os.environ.get("LOAD_TEST_SUBMISSIONS_PER_USER", "10"))
        self.submit_interval_sec = int(os.environ.get("LOAD_TEST_SUBMISSION_INTERVAL_SECONDS", "30"))
        self.submissions_done = 0

        # Auth control: exercise cache-backed submission branch (token != None) if desired
        self.use_auth = os.environ.get("LOAD_TEST_USE_AUTH", "true").lower() in ("1", "true", "yes")
        self.auth_token = os.environ.get("LOAD_TEST_AUTH_TOKEN")

        # Stagger the first submission
        self.next_submit_at = time.time() + random.uniform(10, 25)

        # Warm the session
        params = {'sessionid': self.session_id, 'lang': self.lang}
        self.client.get("/", params=params, name="Initial Load with Session")
        time.sleep(random.uniform(0.15, 0.35))

        # Discover dependency indices
        cfg = _fetch_config(self.client, self.session_id, self.lang)

        # run_experiment ("Build & Submit Model")
        self.submit_fn_index, self.submit_inputs_len = _find_submit_fn_index(cfg)

        # Find a safe small-input dependency (<=2 inputs), explicitly excluding run_experiment
        self.small_fn_index, self.small_inputs_count = _find_small_input_dep(cfg, max_inputs=2, exclude_fn_index=self.submit_fn_index)

    @task(8)
    def maybe_submit_model_cache_backed(self):
        """
        Submit a model only when due, up to submissions_target per user.
        Sends the full input list expected by run_experiment (typically 14).
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
        complexity = random.choice([2, 4, 6])
        default_group_1 = ["juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex", "c_charge_degree", "days_b_screening_arrest"]
        extra = random.sample([c for c in feature_codes if c not in default_group_1], k=random.randint(0, 2))
        feature_set = default_group_1 + extra
        data_size = "Small (20%)"

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
            token,
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
    def occasional_feature_tweak(self):
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
        _post_with_retry(self.client, url, payload, "Occasional Feature Tweak", retries=1)

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

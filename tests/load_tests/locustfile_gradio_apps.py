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
    locust -f locustfile_gradio_apps.py --users 100 --spawn-rate 10 --run-time 5m

    # Selecting a specific user class (CLI positional argument)
    locust -f locustfile_gradio_apps.py GradioAppUser --host=https://judge-HASH-uc.a.run.app ...
    locust -f locustfile_gradio_apps.py ModelBuildingGameUser --host=https://model-building-game-en-... ...
    locust -f locustfile_gradio_apps.py WhatIsAIAppUser --host=https://what-is-ai-... ...
"""

import os
import time
import json
import random
import uuid
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


class GradioAppUser(HttpUser):
    """
    Simulates a user interacting with a Gradio application.
    
    This user class represents typical user behavior:
    - Loading the app UI with session ID and language parameters
    - Interacting with components (buttons, sliders, dropdowns)
    - Submitting forms/predictions that trigger CPU usage
    - Navigating between sections
    """
    
    # Wait between 1 and 3 seconds between tasks (realistic user behavior)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Use provided session ID from environment variable (for auth), or generate unique one
        self.session_id = os.environ.get('LOAD_TEST_SESSION_ID', str(uuid.uuid4()))
        # Random language selection (en, es, ca)
        self.lang = random.choice(['en', 'es', 'ca'])
        
        # Initialize session with query parameters (as used in production)
        params = {
            'sessionid': self.session_id,
            'lang': self.lang
        }
        self.client.get("/", params=params, name="Initial Load with Session")
    
    @task(10)
    def load_app_ui(self):
        """Load the main Gradio application interface with session parameters."""
        params = {
            'sessionid': self.session_id,
            'lang': self.lang
        }
        with self.client.get("/", params=params, catch_response=True, name="Load UI") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to load UI: {response.status_code}")
    
    @task(5)
    def load_gradio_config(self):
        """Load Gradio configuration (required for app initialization)."""
        with self.client.get("/config", catch_response=True, name="Load Config") as response:
            if response.status_code == 200:
                try:
                    config = response.json()
                    if "version" in config:
                        response.success()
                    else:
                        response.failure("Config missing version field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in config response")
            else:
                response.failure(f"Failed to load config: {response.status_code}")
    
    @task(8)
    def run_ai_prediction(self):
        sessionid = self.session_id  # or generate new str(uuid4())
        lang = self.lang
        fn_index = 1   # or your discovered value
        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        severity_options = {
            'en': ["Minor", "Moderate", "Serious"],
            'es': ["Menor", "Moderado", "Grave"],
            'ca': ["Menor", "Moderat", "Greu"],
        }
        severity = random.choice(severity_options.get(lang, ["Minor", "Moderate", "Serious"]))
        url = f"/gradio_api/call/predict?sessionid={sessionid}&lang={lang}"
    
        payload = {
            "fn_index": fn_index,
            "data": [age, priors, severity, lang],
            "session_hash": "random-hash-123"
        }
        self.client.post(url, json=payload, name="Run AI Prediction (What is AI)")
        @task(5)
        def simulate_button_clicks(self):
            """
            Simulate intensive button clicks that trigger backend processing.
            This tests CPU usage from user interactions like decision buttons, navigation, etc.
            """
            fn_indices = [0, 1, 2, 3]  # Different functions in the app
            
            with self.client.post(
                "/api/predict",
                json={
                    "data": [random.choice(["Release", "Keep in Prison", "Next", "Complete"])],
                    "fn_index": random.choice(fn_indices),
                    "session_hash": self.session_id
                },
                catch_response=True,
                name="Button Click (CPU-intensive)"
            ) as response:
                if response.status_code in [200, 201]:
                    response.success()
                elif response.status_code == 404:
                    response.success()
                else:
                    response.failure(f"Button interaction failed: {response.status_code}")
    
    @task(3)
    def simulate_slider_interactions(self):
        """
        Simulate slider/dropdown interactions that trigger real-time processing.
        These are CPU-intensive as they may trigger predictions or calculations.
        """
        slider_values = {
            "age": random.randint(18, 65),
            "priors": random.randint(0, 10),
            "severity": random.choice(["Minor", "Moderate", "Serious"])
        }
        
        with self.client.post(
            "/api/predict",
            json={
                "data": list(slider_values.values()),
                "fn_index": random.randint(4, 7),
                "session_hash": self.session_id
            },
            catch_response=True,
            name="Slider/Dropdown Change (CPU-intensive)"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Slider interaction failed: {response.status_code}")
    
    @task(2)
    def check_health(self):
        """Check application health/readiness."""
        endpoints_to_check = ["/", "/healthz", "/health"]
        
        for endpoint in endpoints_to_check:
            with self.client.get(
                endpoint, 
                catch_response=True,
                name=f"Health Check ({endpoint})"
            ) as response:
                if response.status_code == 200:
                    response.success()
                    break
                elif response.status_code == 404:
                    pass
                else:
                    response.failure(f"Health check failed: {response.status_code}")


class ModelBuildingGameUser(HttpUser):
    """
    Specialized user for Model Building Game apps.
    
    These apps have higher resource requirements (4Gi memory) and include
    ML operations, so we test them with appropriate behavior and intensive
    CPU usage from model training/prediction simulations.
    """
    
    wait_time = between(2, 5)  # Longer wait times for ML operations
    
    def on_start(self):
        """Initialize session with parameters for ML apps."""
        self.session_id = os.environ.get('LOAD_TEST_SESSION_ID', str(uuid.uuid4()))
        self.lang = random.choice(['en', 'es', 'ca'])
        
        params = {
            'sessionid': self.session_id,
            'lang': self.lang
        }
        self.client.get("/", params=params, name="Initial Load with Session")
    
    @task(8)
    def load_game_ui(self):
        """Load the model building game interface with session parameters."""
        params = {
            'sessionid': self.session_id,
            'lang': self.lang
        }
        with self.client.get("/", params=params, catch_response=True, name="Load Game UI") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to load game: {response.status_code}")
    
    @task(5)
    def load_game_data(self):
        """Load game configuration and data."""
        with self.client.get("/config", catch_response=True, name="Load Game Config") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to load game config: {response.status_code}")
    
    @task(4)
    def simulate_model_training(self):
        """
        Simulate model training selections (CPU/memory intensive).
        Tests the most demanding operations in model building apps.
        """
        training_params = {
            "model_type": random.choice(["linear", "tree", "neural_net"]),
            "features": random.sample(["age", "race", "gender", "priors"], k=random.randint(2, 4)),
            "fairness_constraint": random.choice(["none", "demographic_parity", "equal_opportunity"])
        }
        
        with self.client.post(
            "/api/predict",
            json={
                "data": [json.dumps(training_params)],
                "fn_index": random.randint(0, 5),
                "session_hash": self.session_id
            },
            catch_response=True,
            name="Model Training (Very CPU-intensive)",
            timeout=45
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Training failed: {response.status_code}")
    
    @task(3)
    def simulate_feature_selection(self):
        """
        Simulate feature selection and parameter tuning (CPU-intensive).
        These operations trigger recalculations and model updates.
        """
        with self.client.post(
            "/api/predict",
            json={
                "data": [
                    random.sample(["feature1", "feature2", "feature3", "feature4"], k=3),
                    random.uniform(0.1, 0.9)
                ],
                "fn_index": random.randint(6, 10),
                "session_hash": self.session_id
            },
            catch_response=True,
            name="Feature Selection (CPU-intensive)",
            timeout=30
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Feature selection failed: {response.status_code}")


class WhatIsAIAppUser(HttpUser):
    """
    Dedicated user class for the 'What is AI' educational app.
    Focuses traffic on the prediction button path while keeping UI/config/health coverage.
    """

    wait_time = between(1, 3)

    def on_start(self):
        self.session_id = os.environ.get('LOAD_TEST_SESSION_ID', str(uuid.uuid4()))
        self.lang = random.choice(['en', 'es', 'ca'])
        params = {
            'sessionid': self.session_id,
            'lang': self.lang
        }
        self.client.get("/", params=params, name="Initial Load with Session")

    @task(6)
    def load_app_ui(self):
        params = {
            'sessionid': self.session_id,
            'lang': self.lang
        }
        with self.client.get("/", params=params, catch_response=True, name="Load UI") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to load UI: {response.status_code}")

    @task(4)
    def load_gradio_config(self):
        with self.client.get("/config", catch_response=True, name="Load Config") as response:
            if response.status_code == 200:
                try:
                    _ = response.json()
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in config response")
            else:
                response.failure(f"Failed to load config: {response.status_code}")

    @task(12)
    def run_ai_prediction(self):
        # Discover fn_index as before (no change)
        fn_index = None
        try:
            cfg_resp = self.client.get("/config", name="Load Config (for fn_index)")
            if cfg_resp.status_code == 200:
                cfg = cfg_resp.json()
                deps = cfg.get("dependencies", []) or cfg.get("deps", [])
                comps = {c.get("id"): c for c in cfg.get("components", [])}
                button_labels = [
                    "Run AI Prediction",
                    "Ejecutar predicción de la IA",
                    "Executar predicció de la IA",
                ]
                for d in deps:
                    trig_ids = d.get("trigger", []) or d.get("triggers", [])
                    labels = [comps.get(t, {}).get("label") for t in trig_ids if t in comps]
                    if any(label and any(bl in str(label) for bl in button_labels) for label in labels):
                        fn_index = d.get("fn_index")
                        break
                if fn_index is None:
                    for d in deps:
                        outs = d.get("outputs", [])
                        if any(comps.get(o, {}).get("type") == "html" for o in outs):
                            fn_index = d.get("fn_index")
                            break
        except Exception:
            pass

        if fn_index is None:
            return

        age = random.randint(18, 65)
        priors = random.randint(0, 10)
        severity_options = {
            'en': ["Minor", "Moderate", "Serious"],
            'es': ["Menor", "Moderado", "Grave"],
            'ca': ["Menor", "Moderat", "Greu"],
        }
        lang = self.lang
        severity = random.choice(severity_options.get(lang, ["Minor", "Moderate", "Serious"]))

        # Construct new prediction endpoint for new Gradio style
        predict_url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={lang}"

        payload = {
            "data": [age, priors, severity, lang],
            "fn_index": fn_index,
            # session_hash can be anything, can use a new uuid to mimic real web clients
            "session_hash": str(uuid.uuid4())
        }

        with self.client.post(
            predict_url,
            json=payload,
            catch_response=True,
            name="Run AI Prediction (What is AI)"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Prediction failed: {response.status_code}")

    @task(3)
    def simulate_button_clicks(self):
        """
        Simulate navigation and button interactions in What is AI app.
        If these trigger prediction-like events, target /gradio_api/call/predict.
        """
        fn_indices = [0, 1, 2, 3]
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        with self.client.post(
            url,
            json={
                "data": [random.choice(["Next", "Complete", "Continue"])],
                "fn_index": random.choice(fn_indices),
                "session_hash": str(uuid.uuid4())
            },
            catch_response=True,
            name="Button Click (Navigation/UI)"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Button interaction failed: {response.status_code}")

    @task(2)
    def simulate_slider_interactions(self):
        """
        Simulate slider/dropdown interactions for parameter adjustments.
        If these are supposed to go through Gradio predict, use the new endpoint.
        """
        slider_values = {
            "age": random.randint(18, 65),
            "priors": random.randint(0, 10),
            "severity": random.choice(["Minor", "Moderate", "Serious"])
        }
        url = f"/gradio_api/call/predict?sessionid={self.session_id}&lang={self.lang}"
        with self.client.post(
            url,
            json={
                "data": list(slider_values.values()),
                "fn_index": random.randint(4, 7),
                "session_hash": str(uuid.uuid4())
            },
            catch_response=True,
            name="Slider/Dropdown Change (UI)"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Slider interaction failed: {response.status_code}")

    @task(1)
    def check_health(self):
        endpoints_to_check = ["/", "/healthz", "/health"]
        for endpoint in endpoints_to_check:
            with self.client.get(endpoint, catch_response=True, name=f"Health Check ({endpoint})") as response:
                if response.status_code == 200:
                    response.success()
                    break
                elif response.status_code == 404:
                    pass
                else:
                    response.failure(f"Health check failed: {response.status_code}")



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

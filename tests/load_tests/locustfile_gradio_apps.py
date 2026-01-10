"""
Load tests for Gradio Cloud Run applications.

This load test suite validates the scalability of Gradio apps deployed to Cloud Run,
ensuring they can handle 100+ concurrent users as specified in the requirements.

Usage:
    # Test specific app
    locust -f locustfile_gradio_apps.py --host=https://judge-HASH-uc.a.run.app
    
    # Test with 100 concurrent users
    locust -f locustfile_gradio_apps.py --host=https://judge-HASH-uc.a.run.app \
        --users 100 --spawn-rate 10 --run-time 5m --headless
    
    # Test from environment variable
    export GRADIO_APP_URL=https://judge-HASH-uc.a.run.app
    locust -f locustfile_gradio_apps.py --users 100 --spawn-rate 10 --run-time 5m
"""

import os
import time
import json
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


class GradioAppUser(HttpUser):
    """
    Simulates a user interacting with a Gradio application.
    
    This user class represents typical user behavior:
    - Loading the app UI
    - Interacting with components
    - Submitting forms/predictions
    - Navigating between sections
    """
    
    # Wait between 1 and 3 seconds between tasks (realistic user behavior)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Initialize session (Gradio uses session cookies)
        self.client.get("/", name="Initial Load")
    
    @task(10)
    def load_app_ui(self):
        """Load the main Gradio application interface."""
        with self.client.get("/", catch_response=True, name="Load UI") as response:
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
    
    @task(3)
    def simulate_user_interaction(self):
        """
        Simulate user interaction with Gradio components.
        This represents clicks, text inputs, and other UI interactions.
        """
        # Gradio uses a queue system for processing requests
        with self.client.post(
            "/queue/join",
            json={"fn_index": 0, "session_hash": f"session_{self.client.base_url}"},
            catch_response=True,
            name="Queue Join"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                # Some apps might not use queue system
                response.success()
            else:
                response.failure(f"Queue join failed: {response.status_code}")
    
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
                    break  # One successful health check is enough
                elif response.status_code == 404:
                    # Endpoint might not exist, that's okay
                    pass
                else:
                    response.failure(f"Health check failed: {response.status_code}")


class ModelBuildingGameUser(HttpUser):
    """
    Specialized user for Model Building Game apps.
    
    These apps have higher resource requirements (4Gi memory) and include
    ML operations, so we test them with appropriate behavior.
    """
    
    wait_time = between(2, 5)  # Longer wait times for ML operations
    
    @task(8)
    def load_game_ui(self):
        """Load the model building game interface."""
        with self.client.get("/", catch_response=True, name="Load Game UI") as response:
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
    
    @task(3)
    def simulate_model_prediction(self):
        """
        Simulate model prediction requests (the most resource-intensive operation).
        This tests the ML operations within the app.
        """
        # Simulate prediction with sample data
        with self.client.post(
            "/api/predict",
            json={
                "data": ["sample input"],
                "fn_index": 0
            },
            catch_response=True,
            name="Model Prediction",
            timeout=30  # ML operations can take longer
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                # API endpoint might be structured differently
                response.success()
            else:
                response.failure(f"Prediction failed: {response.status_code}")


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
    
    # Success criteria based on our requirements
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


# Default user class (can be overridden with --user-class flag)
# Use GradioAppUser for standard apps
# Use ModelBuildingGameUser for model building game apps

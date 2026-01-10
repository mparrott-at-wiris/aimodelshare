# Gradio Apps Load Testing

This directory contains load tests for validating the scalability of Gradio applications deployed to Cloud Run.

## Overview

The load tests ensure that the Cloud Run apps can handle 100+ concurrent users as specified in the scalability requirements. Tests use [Locust](https://locust.io/), a popular Python-based load testing framework.

## Prerequisites

```bash
# Install load testing dependencies
pip install -r requirements.txt
```

## Running Load Tests

### Quick Test (Local)

Test with a small number of users:

```bash
cd tests/load_tests
locust -f locustfile_gradio_apps.py \
  --host=https://your-app-hash-uc.a.run.app \
  --users 10 \
  --spawn-rate 2 \
  --run-time 1m \
  --headless
```

### Production Load Test (100 concurrent users)

```bash
cd tests/load_tests
locust -f locustfile_gradio_apps.py \
  --host=https://your-app-hash-uc.a.run.app \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --html=load_test_report.html
```

### Testing Specific App Types

**Standard Apps (judge, tutorial, ai-consequences, what-is-ai, etc.):**
```bash
locust -f locustfile_gradio_apps.py \
  --host=https://judge-HASH-uc.a.run.app \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless
```

**Model Building Game Apps (higher resource usage):**
```bash
locust -f locustfile_gradio_apps.py \
  --host=https://model-building-game-en-HASH-uc.a.run.app \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --user-class ModelBuildingGameUser
```

### Interactive UI Mode

To run with Locust's web interface:

```bash
locust -f locustfile_gradio_apps.py \
  --host=https://your-app-hash-uc.a.run.app
```

Then open http://localhost:8089 in your browser to control the test.

## Test Parameters

- `--users`: Number of concurrent users to simulate (default: 100)
- `--spawn-rate`: Users spawned per second (default: 10)
- `--run-time`: Duration of the test (e.g., 5m, 30s)
- `--headless`: Run without the web UI
- `--html`: Generate HTML report
- `--user-class`: User behavior class (GradioAppUser or ModelBuildingGameUser)

## Success Criteria

The load tests validate the following criteria:

| Metric | Target | Description |
|--------|--------|-------------|
| Success Rate | > 99% | Percentage of successful requests |
| P95 Latency | < 1000ms | 95th percentile response time |
| Failed Requests | < 1% | Percentage of failed requests |
| Mean Response Time | < 500ms | Average response time |

## Test Scenarios

### GradioAppUser (Standard Apps)
Simulates typical user interactions:
- Loading the app UI (40% of requests)
- Loading configuration (20% of requests)
- User interactions/queue joins (12% of requests)
- Health checks (8% of requests)

### ModelBuildingGameUser (ML Apps)
Simulates ML-heavy interactions:
- Loading game UI (35% of requests)
- Loading game data (22% of requests)
- Model predictions (13% of requests)

## Interpreting Results

### Good Results
```
Total Requests: 5000+
Failed Requests: < 50
Success Rate: > 99%
P95 Latency: < 1000ms
Requests/sec: > 10
```

### Warning Signs
- Success rate < 99%: Indicates timeout or error issues
- P95 latency > 1000ms: App is slow under load
- High failure rate: Configuration or resource issues

### Common Issues

**High Latency:**
- Check CPU/Memory utilization in Cloud Run metrics
- Verify concurrency settings
- Consider increasing resources

**Failed Requests:**
- Check Cloud Run logs for errors
- Verify timeout settings (should be 300s)
- Check if hitting max instances

**Cold Starts:**
- First few requests may be slower
- Consider setting min-instances=1 for critical apps

## Automated Testing (CI/CD)

Load tests can be run automatically in GitHub Actions. See `.github/workflows/load_test_gradio_apps.yml` for the workflow configuration.

## Example Output

```
🚀 Starting Gradio App Load Test
================================================================================
Target: https://judge-abc123-uc.a.run.app
Users: 100
================================================================================

[2026-01-10 12:00:00] Starting load test...
[2026-01-10 12:05:00] Stopping load test...

✅ Load Test Complete
================================================================================

📊 Summary Statistics:
  Total Requests: 5234
  Failed Requests: 12
  Success Rate: 99.77%
  Median Response Time: 245ms
  95th Percentile: 489ms
  99th Percentile: 756ms
  Average Response Time: 267ms
  Min Response Time: 89ms
  Max Response Time: 1234ms
  Requests/sec: 17.45

📋 Success Criteria Check:
  ✓ Success Rate > 99%: PASS (99.77%)
  ✓ P95 Latency < 1000ms: PASS (489ms)
  ✓ Failed Requests < 1%: PASS

🎉 All criteria met! App is ready for production.
```

## Advanced Usage

### Testing Multiple Apps Sequentially

```bash
#!/bin/bash
APPS=(
  "judge"
  "ai-consequences"
  "what-is-ai"
  "model-building-game-en"
)

for app in "${APPS[@]}"; do
  echo "Testing $app..."
  locust -f locustfile_gradio_apps.py \
    --host=https://$app-HASH-uc.a.run.app \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html="reports/${app}_load_test.html"
done
```

### Custom Load Patterns

```bash
# Gradual ramp-up (stress test)
locust -f locustfile_gradio_apps.py \
  --host=https://your-app.run.app \
  --users 200 \
  --spawn-rate 2 \
  --run-time 10m \
  --headless

# Spike test (sudden load)
locust -f locustfile_gradio_apps.py \
  --host=https://your-app.run.app \
  --users 100 \
  --spawn-rate 50 \
  --run-time 2m \
  --headless
```

## Troubleshooting

**"Connection refused" errors:**
- Verify the URL is correct
- Check if app is deployed and running
- Ensure `--allow-unauthenticated` is set

**"Too many requests" errors:**
- Cloud Run is throttling requests
- Check max-instances setting
- Consider increasing concurrency

**Slow response times:**
- Check Cloud Run metrics for CPU/memory usage
- Verify startup-cpu-boost is enabled
- Review application logs for bottlenecks

## References

- [Locust Documentation](https://docs.locust.io/)
- [Cloud Run Monitoring](https://cloud.google.com/run/docs/monitoring)
- [CLOUD_RUN_SCALABILITY_OPTIMIZATIONS.md](../../CLOUD_RUN_SCALABILITY_OPTIMIZATIONS.md)

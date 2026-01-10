# Gradio Apps Load Testing

This directory contains load tests for validating the scalability of Gradio applications deployed to Cloud Run.

## Overview

The load tests ensure that the Cloud Run apps can handle 100+ concurrent users as specified in the scalability requirements. Tests use [Locust](https://locust.io/), a popular Python-based load testing framework.

**Key Features:**
- ✅ **Session ID support**: Tests include `sessionid` query parameter as used in production
- ✅ **Language parameters**: Tests multiple languages (`lang=en/es/ca`)
- ✅ **Interactive elements**: Simulates button clicks, slider changes, dropdown selections
- ✅ **CPU-intensive operations**: Tests model training, predictions, and real-time calculations
- ✅ **Realistic user behavior**: Includes wait times, random selections, and navigation patterns

## Prerequisites

```bash
# Install load testing dependencies
pip install -r requirements.txt
```

## Live App URLs

Here are the deployed Cloud Run app URLs you can test:

```json
{
  "tutorial": "https://tutorial-pvrljp4aja-uc.a.run.app",
  "judge": "https://judge-pvrljp4aja-uc.a.run.app",
  "ai-consequences": "https://ai-consequences-pvrljp4aja-uc.a.run.app",
  "what-is-ai": "https://what-is-ai-pvrljp4aja-uc.a.run.app",
  "model-building-game-en": "https://model-building-game-en-pvrljp4aja-uc.a.run.app",
  "model-building-game-ca": "https://model-building-game-ca-pvrljp4aja-uc.a.run.app",
  "model-building-game-es": "https://model-building-game-es-pvrljp4aja-uc.a.run.app",
  "model-building-game-en-final": "https://model-building-game-en-final-pvrljp4aja-uc.a.run.app",
  "model-building-game-es-final": "https://model-building-game-es-final-pvrljp4aja-uc.a.run.app",
  "model-building-game-ca-final": "https://model-building-game-ca-final-pvrljp4aja-uc.a.run.app",
  "ethical-revelation": "https://ethical-revelation-pvrljp4aja-uc.a.run.app",
  "moral-compass-challenge": "https://moral-compass-challenge-pvrljp4aja-uc.a.run.app",
  "bias-detective-part1": "https://bias-detective-part1-pvrljp4aja-uc.a.run.app",
  "bias-detective-part2": "https://bias-detective-part2-pvrljp4aja-uc.a.run.app",
  "bias-detective-en": "https://bias-detective-en-pvrljp4aja-uc.a.run.app",
  "bias-detective-es": "https://bias-detective-es-pvrljp4aja-uc.a.run.app",
  "bias-detective-ca": "https://bias-detective-ca-pvrljp4aja-uc.a.run.app",
  "fairness-fixer": "https://fairness-fixer-pvrljp4aja-uc.a.run.app",
  "justice-equity-upgrade": "https://justice-equity-upgrade-pvrljp4aja-uc.a.run.app",
  "fairness-fixer-en": "https://fairness-fixer-en-pvrljp4aja-uc.a.run.app",
  "fairness-fixer-es": "https://fairness-fixer-es-pvrljp4aja-uc.a.run.app",
  "fairness-fixer-ca": "https://fairness-fixer-ca-pvrljp4aja-uc.a.run.app",
  "justice-equity-upgrade-en": "https://justice-equity-upgrade-en-pvrljp4aja-uc.a.run.app",
  "justice-equity-upgrade-es": "https://justice-equity-upgrade-es-pvrljp4aja-uc.a.run.app",
  "justice-equity-upgrade-ca": "https://justice-equity-upgrade-ca-pvrljp4aja-uc.a.run.app"
}
```

## Running Load Tests

### Quick Test (Local)

Test with a small number of users:

```bash
cd tests/load_tests

# Set your session ID (required for auth)
export LOAD_TEST_SESSION_ID="your-session-id-here"

# Run the test
locust -f locustfile_gradio_apps.py \
  --host=https://judge-pvrljp4aja-uc.a.run.app \
  --users 10 \
  --spawn-rate 2 \
  --run-time 1m \
  --headless
```

### Production Load Test (100 concurrent users)

```bash
cd tests/load_tests

# Set your session ID (required for auth)
export LOAD_TEST_SESSION_ID="your-session-id-here"

# Run the test
locust -f locustfile_gradio_apps.py \
  --host=https://judge-pvrljp4aja-uc.a.run.app \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --html=load_test_report.html
```

### Testing Specific App Types

**Standard Apps (judge, tutorial, ai-consequences, what-is-ai, etc.):**
```bash
export LOAD_TEST_SESSION_ID="your-session-id-here"

locust -f locustfile_gradio_apps.py \
  --host=https://judge-pvrljp4aja-uc.a.run.app \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless
```

**Model Building Game Apps (higher resource usage):**
```bash
export LOAD_TEST_SESSION_ID="your-session-id-here"

locust -f locustfile_gradio_apps.py \
  --host=https://model-building-game-en-pvrljp4aja-uc.a.run.app \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --user-class ModelBuildingGameUser
```

### Interactive UI Mode

To run with Locust's web interface:

```bash
export LOAD_TEST_SESSION_ID="your-session-id-here"

locust -f locustfile_gradio_apps.py \
  --host=https://judge-pvrljp4aja-uc.a.run.app
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
Simulates typical user interactions with production-like parameters:
- **Initial load with session parameters** (sessionid, lang)
- **Loading the app UI** (40% of requests) with query parameters
- **Loading configuration** (20% of requests)
- **Button clicks** (20% of requests) - CPU-intensive operations like decision making
- **Slider/dropdown interactions** (12% of requests) - Real-time processing
- **Health checks** (8% of requests)

Each user has:
- Unique session ID (UUID)
- Random language selection (en/es/ca)
- Realistic wait times between actions (1-3 seconds)

### ModelBuildingGameUser (ML Apps)
Simulates ML-heavy interactions with intensive CPU usage:
- **Loading game UI with session** (32% of requests)
- **Loading game data** (20% of requests)
- **Model training simulations** (16% of requests) - Very CPU-intensive (45s timeout)
- **Feature selection** (12% of requests) - CPU-intensive (30s timeout)
- **Model predictions** (12% of requests)

Each user has:
- Unique session ID
- Random language and model configurations
- Longer wait times for processing (2-5 seconds)

## What Gets Tested

### Production-Realistic Scenarios

The load tests are designed to match actual production usage:

#### Session Management
- ✅ **Session ID tokens**: Each user gets a unique `sessionid` parameter passed in URLs
- ✅ **Language variants**: Tests cycle through `en`, `es`, and `ca` languages
- ✅ **Session persistence**: Same session ID used throughout user's session

#### Interactive Elements (CPU-Intensive)
- ✅ **Button clicks**: Decision buttons, navigation, form submissions
- ✅ **Slider changes**: Age sliders, risk score adjustments (trigger real-time calculations)
- ✅ **Dropdown selections**: Severity levels, feature selections (trigger backend processing)
- ✅ **Model training**: Full training cycles with various configurations (most CPU-intensive)
- ✅ **Feature selection**: Dynamic feature set changes with recalculations

#### Performance Under Load
The tests validate that these intensive operations can handle concurrent users:
- Multiple users clicking buttons simultaneously
- Slider changes triggering calculations in parallel
- Model training operations running concurrently
- Real-time updates without timeout errors

### What Makes This Test Realistic

1. **Query Parameters**: Just like production, tests include `?sessionid=xxx&lang=en` in requests
2. **Timing**: Realistic wait times between actions (users don't click instantly)
3. **Variety**: Random selections of languages, parameters, and features
4. **Intensity**: Tests the most CPU-heavy operations (training, predictions, real-time calculations)
5. **Concurrency**: Simulates many users performing intensive operations at the same time

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

**To run via GitHub Actions:**

1. Go to **Actions** → **Load Test Gradio Apps**
2. Click **Run workflow**
3. Fill in the inputs:
   - **App URL**: Select from live URLs above (e.g., `https://judge-pvrljp4aja-uc.a.run.app`)
   - **Session ID**: Your auth token/session ID for the app
   - **Number of users**: Default 100
   - **Spawn rate**: Default 10/sec
   - **Duration**: Default 5m
4. Click **Run workflow**
5. Download HTML reports from artifacts when complete

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

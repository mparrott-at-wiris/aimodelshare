# Google Cloud Run Deployment Guide

This document explains how to deploy the Moral Compass Gradio applications to Google Cloud Run for production use.

## Overview

The Moral Compass apps are deployed using a **"Build Once, Deploy Many"** architecture:
- A single Docker image contains all 10 app codebases
- Each Cloud Run service runs the same image but with a different `APP_NAME` environment variable
- This approach minimizes maintenance while allowing independent scaling

## Architecture Benefits

### 🚀 Massive Scalability
- **Auto-scaling**: Cloud Run automatically scales from 0 to 50 instances based on traffic
- **Session Affinity**: Keeps user interactions on the same server instance for state consistency
- **High Concurrency**: Each instance handles 80 concurrent students

### ⚡ Fast Performance
- **Container Size**: ~500MB (vs 3GB+ with TensorFlow/PyTorch)
- **Cold Start**: <5 seconds (vs 15-30s with heavy ML frameworks)
- **Lazy Loading**: Only imports the specific app code requested

### 💰 Cost Efficiency
- **Pay-per-use**: Scales to zero when not in use
- **Shared Image**: Single build deployed to multiple services
- **High Concurrency**: Fewer instances needed per student

## Prerequisites

### 1. Google Cloud Project Setup

1. Create or select a Google Cloud Project
2. Enable required APIs:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   ```

3. Create an Artifact Registry repository:
   ```bash
   gcloud artifacts repositories create moral-compass-apps \
     --repository-format=docker \
     --location=us-central1 \
     --description="Moral Compass Gradio applications"
   ```

### 2. Service Account Setup

1. Create a service account:
   ```bash
   gcloud iam service-accounts create github-actions-deployer \
     --description="Service account for GitHub Actions deployments" \
     --display-name="GitHub Actions Deployer"
   ```

2. Grant necessary roles:
   ```bash
   PROJECT_ID=$(gcloud config get-value project)
   
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"
   
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer"
   
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   ```

3. Create and download a JSON key:
   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com
   ```
   
   **Important**: Store this key securely and delete it from your local machine after adding to GitHub Secrets.

### 3. GitHub Secrets Configuration

Add these secrets to your GitHub repository:

1. **GCP_PROJECT_ID**: Your Google Cloud Project ID
   ```
   Settings → Secrets and variables → Actions → New repository secret
   Name: GCP_PROJECT_ID
   Value: your-project-id
   ```

2. **GCP_SA_KEY**: The contents of the JSON key file
   ```
   Settings → Secrets and variables → Actions → New repository secret
   Name: GCP_SA_KEY
   Value: <paste entire contents of key.json>
   ```

## Deployment

### Automatic Deployment (Recommended)

The GitHub Actions workflow automatically deploys when:
- You push changes to the `main` branch that affect:
  - `aimodelshare/moral_compass/apps/**`
  - `requirements-apps.txt`
  - `launch_entrypoint.py`
  - `Dockerfile`
  - `.github/workflows/deploy_gradio_apps.yml`
- You manually trigger the workflow via GitHub Actions UI

### Manual Deployment

You can also deploy manually:

1. Build the Docker image:
   ```bash
   docker build -t us-central1-docker.pkg.dev/YOUR-PROJECT-ID/moral-compass-apps/gradio-universal:latest .
   ```

2. Push to Artifact Registry:
   ```bash
   docker push us-central1-docker.pkg.dev/YOUR-PROJECT-ID/moral-compass-apps/gradio-universal:latest
   ```

3. Deploy to Cloud Run (example for tutorial app):
   ```bash
   gcloud run deploy tutorial \
     --image us-central1-docker.pkg.dev/YOUR-PROJECT-ID/moral-compass-apps/gradio-universal:latest \
     --region us-central1 \
     --platform managed \
     --allow-unauthenticated \
     --memory 1Gi \
     --cpu 1 \
     --session-affinity \
     --concurrency 80 \
     --min-instances 0 \
     --max-instances 50 \
     --set-env-vars APP_NAME=tutorial,GRADIO_SERVER_NAME=0.0.0.0,GRADIO_ANALYTICS_ENABLED=False
   ```

## Deployed Applications

The following 10 apps are deployed as separate Cloud Run services:

1. **tutorial** - Onboarding tutorial
2. **judge** - Decision-making exercise
3. **ai-consequences** - Understanding AI errors
4. **what-is-ai** - AI fundamentals
5. **model-building-game** - Interactive model building
6. **ethical-revelation** - Ethics exploration
7. **moral-compass-challenge** - Main challenge activity
8. **bias-detective** - Bias identification
9. **fairness-fixer** - Fairness improvement
10. **justice-equity-upgrade** - Justice and equity concepts

## Configuration

### Environment Variables

Each service uses these environment variables:

- `APP_NAME`: Identifies which app to launch (e.g., "tutorial", "judge")
- `PORT`: Server port (Cloud Run provides this automatically, defaults to 8080)
- `GRADIO_SERVER_NAME`: Set to "0.0.0.0" for container networking
- `GRADIO_ANALYTICS_ENABLED`: Set to "False" for privacy and performance
- `GRADIO_NUM_PORTS`: Set to "1" for single-port operation

### Scalability Optimizations

The deployment includes several optimizations for handling 100+ concurrent users:

1. **Reduced Timeout**: 300 seconds (5 minutes) instead of 3000 seconds for better resource management
2. **CPU Throttling**: Enabled to reduce costs during idle periods
3. **Startup CPU Boost**: Enabled for faster cold starts (~20-30% improvement)
4. **Optimized Surge Upgrades**: 3-5 instances at a time for smoother scaling

For detailed information about scalability optimizations, see [CLOUD_RUN_SCALABILITY_OPTIMIZATIONS.md](CLOUD_RUN_SCALABILITY_OPTIMIZATIONS.md).

### Resource Limits

**Standard Apps (judge, tutorial, ai-consequences, what-is-ai, etc.):**
- **Memory**: 2 GiB
- **CPU**: 2 vCPU
- **Concurrency**: 40 requests per instance
- **Min Instances**: 0 (scales to zero)
- **Max Instances**: 50 (handles 2,000 concurrent users)
- **Timeout**: 300 seconds (5 minutes)
- **CPU Throttling**: Enabled (cost optimization)
- **Startup CPU Boost**: Enabled (faster cold starts)
- **Max Surge Upgrade**: 3 instances at a time

**Model Building Game Apps (all language variants):**
- **Memory**: 4 GiB (higher for ML operations)
- **CPU**: 2 vCPU
- **Concurrency**: 40 requests per instance
- **Min Instances**: 0 (scales to zero)
- **Max Instances**: 100 (handles 4,000 concurrent users)
- **Timeout**: 300 seconds (5 minutes)
- **CPU Throttling**: Enabled (cost optimization)
- **Startup CPU Boost**: Enabled (faster cold starts)
- **Max Surge Upgrade**: 5 instances at a time

## Monitoring

### Cloud Run Metrics

Monitor your deployments in Google Cloud Console:
1. Navigate to Cloud Run
2. Select a service
3. View the "METRICS" tab for:
   - Request count
   - Request latency
   - Container instance count
   - Memory utilization
   - CPU utilization

### Logs

View application logs:
```bash
gcloud run services logs read SERVICE_NAME --region=us-central1
```

Or in Cloud Console:
1. Cloud Run → Select service → LOGS tab

## Troubleshooting

### Cold Start Issues
If cold starts are slow:
- Set `--min-instances 1` for frequently-used apps
- Check container size: `docker images | grep gradio-universal`

### Memory Issues
If containers are running out of memory:
- Increase `--memory` to 2Gi
- Check memory usage in Cloud Run metrics
- Review app code for memory leaks

### Import Errors
If apps fail to import:
- Verify `requirements-apps.txt` includes all dependencies
- Check build logs for pip install errors
- Test locally: `docker run -p 8080:8080 -e APP_NAME=tutorial IMAGE`

### Authentication Errors
If deployment fails with permission errors:
- Verify service account has required roles
- Check that GCP_SA_KEY secret is correctly formatted
- Ensure Artifact Registry repository exists

## Local Testing

Test the container locally before deploying:

```bash
# Build the image
docker build -t moral-compass-test .

# Run a specific app
docker run -p 8080:8080 -e APP_NAME=tutorial moral-compass-test

# Access at http://localhost:8080
```

Test different apps by changing APP_NAME:
```bash
docker run -p 8080:8080 -e APP_NAME=judge moral-compass-test
docker run -p 8080:8080 -e APP_NAME=model-building-game moral-compass-test
```

## Cost Estimation

Rough cost estimates for Cloud Run (as of 2024):
- **Free tier**: 2 million requests/month
- **Beyond free tier**: ~$0.40 per million requests
- **Memory**: ~$0.0000025 per GiB-second
- **CPU**: ~$0.00001 per vCPU-second

Example for a class of 200 students using apps for 1 hour:
- Requests: ~200 students × 50 interactions = 10,000 requests
- CPU time: ~200 seconds total = $0.002
- Memory: ~200 GiB-seconds total = $0.0005
- **Total**: < $0.01

## Security Considerations

1. **Secrets**: Never commit `key.json` or secrets to the repository
2. **Authentication**: Apps are deployed with `--allow-unauthenticated` for educational use
3. **Rate Limiting**: Cloud Run has built-in DDoS protection
4. **HTTPS**: All Cloud Run services use HTTPS by default

## Support

For issues or questions:
1. Check the [Cloud Run documentation](https://cloud.google.com/run/docs)
2. Review [GitHub Actions logs](https://github.com/your-repo/actions)
3. Examine Cloud Run service logs in Google Cloud Console

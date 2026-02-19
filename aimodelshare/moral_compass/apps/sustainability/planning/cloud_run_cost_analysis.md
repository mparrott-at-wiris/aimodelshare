# Cloud Run Cost Analysis — Moral Compass Apps

> Generated 2026-02-19. Rates sourced from [Google Cloud Run Pricing](https://cloud.google.com/run/pricing) (Tier 1, `us-central1`).

## Pricing Rates Used

All services use **request-based billing** (the Cloud Run default). In this mode, idle min-instances are billed at a reduced CPU rate while memory stays the same.

| Resource | Active Rate | Idle Rate (min instances) |
|----------|-------------|--------------------------|
| CPU | $0.00002400 /vCPU-sec | $0.00000250 /vCPU-sec |
| Memory | $0.00000250 /GiB-sec | $0.00000250 /GiB-sec |
| Requests | $0.40 /million (first 2M free) | — |

**Free tier** (per billing account/month): 180,000 vCPU-seconds, 360,000 GiB-seconds, 2M requests. Offsets ~$5.22/month — negligible at this scale and excluded from estimates below.

**Seconds per month** (30 days): 2,592,000

---

## Workflow 1: Main Track (`deploy_gradio_apps.yml`)

**20 Cloud Run services** — all currently at `min-instances=1`.

### 2 vCPU / 2 GiB services (14 services)

| # | Service Name | CPU | Memory | min | max |
|---|-------------|-----|--------|-----|-----|
| 1 | judge | 2 | 2Gi | 1 | 150 |
| 2 | ai-consequences | 2 | 2Gi | 1 | 150 |
| 3 | what-is-ai | 2 | 2Gi | 1 | 150 |
| 4 | ethical-revelation | 2 | 2Gi | 1 | 150 |
| 5 | moral-compass-challenge | 2 | 2Gi | 1 | 150 |
| 6 | bias-detective-en | 2 | 2Gi | 1 | 150 |
| 7 | bias-detective-es | 2 | 2Gi | 1 | 150 |
| 8 | bias-detective-ca | 2 | 2Gi | 1 | 150 |
| 9 | fairness-fixer-en | 2 | 2Gi | 1 | 150 |
| 10 | fairness-fixer-es | 2 | 2Gi | 1 | 150 |
| 11 | fairness-fixer-ca | 2 | 2Gi | 1 | 150 |
| 12 | justice-equity-upgrade-en | 2 | 2Gi | 1 | 150 |
| 13 | justice-equity-upgrade-es | 2 | 2Gi | 1 | 150 |
| 14 | justice-equity-upgrade-ca | 2 | 2Gi | 1 | 150 |

### 2 vCPU / 4 GiB services (6 services)

| # | Service Name | CPU | Memory | min | max |
|---|-------------|-----|--------|-----|-----|
| 15 | model-building-game-en | 2 | 4Gi | 1 | 150 |
| 16 | model-building-game-ca | 2 | 4Gi | 1 | 150 |
| 17 | model-building-game-es | 2 | 4Gi | 1 | 150 |
| 18 | model-building-game-en-final | 2 | 4Gi | 1 | 150 |
| 19 | model-building-game-es-final | 2 | 4Gi | 1 | 150 |
| 20 | model-building-game-ca-final | 2 | 4Gi | 1 | 150 |

---

## Workflow 2: Sustainability Track (`deploy_gradio_apps_sustainability.yml`)

**18 Cloud Run services** — all currently at `min-instances=0`.

### 2 vCPU / 4 GiB services (6 services)

| # | Service Name | CPU | Memory | min | max |
|---|-------------|-----|--------|-----|-----|
| 21 | model-building-game-en-sustainability | 2 | 4Gi | 0 | 150 |
| 22 | model-building-game-ca-sustainability | 2 | 4Gi | 0 | 150 |
| 23 | model-building-game-es-sustainability | 2 | 4Gi | 0 | 150 |
| 24 | model-building-game-en-final-sustainability | 2 | 4Gi | 0 | 150 |
| 25 | model-building-game-es-final-sustainability | 2 | 4Gi | 0 | 150 |
| 26 | model-building-game-ca-final-sustainability | 2 | 4Gi | 0 | 150 |

### 2 vCPU / 2 GiB services (12 services)

| # | Service Name | CPU | Memory | min | max |
|---|-------------|-----|--------|-----|-----|
| 27 | bias-detective-en-sustainability | 2 | 2Gi | 0 | 150 |
| 28 | bias-detective-ca-sustainability | 2 | 2Gi | 0 | 150 |
| 29 | bias-detective-es-sustainability | 2 | 2Gi | 0 | 150 |
| 30 | fairness-fixer-en-sustainability | 2 | 2Gi | 0 | 150 |
| 31 | fairness-fixer-ca-sustainability | 2 | 2Gi | 0 | 150 |
| 32 | fairness-fixer-es-sustainability | 2 | 2Gi | 0 | 150 |
| 33 | sustainability-upgrade-en | 2 | 2Gi | 0 | 150 |
| 34 | sustainability-upgrade-ca | 2 | 2Gi | 0 | 150 |
| 35 | sustainability-upgrade-es | 2 | 2Gi | 0 | 150 |
| 36 | moral-compass-en-sustainability | 2 | 2Gi | 0 | 150 |
| 37 | moral-compass-es-sustainability | 2 | 2Gi | 0 | 150 |
| 38 | moral-compass-ca-sustainability | 2 | 2Gi | 0 | 150 |

---

## Total Container Count

| | Main Track | Sustainability Track | Combined |
|--|-----------|---------------------|----------|
| 2 vCPU / 2 GiB | 14 | 12 | **26** |
| 2 vCPU / 4 GiB | 6 | 6 | **12** |
| **Total services** | **20** | **18** | **38** |

---

## Cost Estimates

### Per-service idle cost (min-instances=1, 24/7)

These are the **baseline floor costs** — what you pay even with zero traffic, just to keep one warm instance per service for cold-start elimination.

**2 vCPU / 2 GiB service:**

| Component | Calculation | Monthly |
|-----------|-------------|---------|
| CPU (idle) | 2 vCPU × $0.00000250/sec × 2,592,000 sec | $12.96 |
| Memory (idle) | 2 GiB × $0.00000250/sec × 2,592,000 sec | $12.96 |
| **Total** | | **$25.92** |

**2 vCPU / 4 GiB service:**

| Component | Calculation | Monthly |
|-----------|-------------|---------|
| CPU (idle) | 2 vCPU × $0.00000250/sec × 2,592,000 sec | $12.96 |
| Memory (idle) | 4 GiB × $0.00000250/sec × 2,592,000 sec | $25.92 |
| **Total** | | **$38.88** |

### Per-service active cost (per request-serving instance)

When an instance is actively processing requests, you pay the full active rate *instead of* the idle rate for that instance.

**2 vCPU / 2 GiB service — per active-instance-hour:**

| Component | Calculation | Per Hour |
|-----------|-------------|----------|
| CPU | 2 vCPU × $0.00002400/sec × 3,600 sec | $0.1728 |
| Memory | 2 GiB × $0.00000250/sec × 3,600 sec | $0.0180 |
| **Total** | | **$0.1908** |

**2 vCPU / 4 GiB service — per active-instance-hour:**

| Component | Calculation | Per Hour |
|-----------|-------------|----------|
| CPU | 2 vCPU × $0.00002400/sec × 3,600 sec | $0.1728 |
| Memory | 4 GiB × $0.00000250/sec × 3,600 sec | $0.0360 |
| **Total** | | **$0.2088** |

---

### Scenario A: Current state (main min=1, sustainability min=0)

Sustainability services scale to zero when idle — no baseline cost.

| Track | Services | Idle cost/service | Monthly |
|-------|----------|-------------------|---------|
| Main (2Gi × 14) | 14 | $25.92 | $362.88 |
| Main (4Gi × 6) | 6 | $38.88 | $233.28 |
| Sustainability | 18 | $0.00 (min=0) | $0.00 |
| **Total baseline** | **38** | | **$596.16/mo** |

### Scenario B: All production-ready (all 38 services at min=1)

| Track | Services | Idle cost/service | Monthly |
|-------|----------|-------------------|---------|
| Main (2Gi × 14) | 14 | $25.92 | $362.88 |
| Main (4Gi × 6) | 6 | $38.88 | $233.28 |
| Sustainability (2Gi × 12) | 12 | $25.92 | $311.04 |
| Sustainability (4Gi × 6) | 6 | $38.88 | $233.28 |
| **Total baseline** | **38** | | **$1,140.48/mo** |

### Delta: making sustainability production-ready

| Change | Monthly increase |
|--------|-----------------|
| 12 sustainability 2Gi services → min=1 | +$311.04 |
| 6 sustainability 4Gi services → min=1 | +$233.28 |
| **Total increase** | **+$544.32/mo** |

---

---

## Burst Traffic Scenarios — Classroom Usage in Spain

### Assumptions

- **Context**: High school and college classes in Spain using the platform during guided classroom sessions.
- **Language**: Students primarily use ES (Spanish) variants. Each language is a separate Cloud Run service, so Spanish students only hit `*-es-*` services.
- **Concurrency**: Each instance handles up to 20 simultaneous users (`--concurrency=20`).
- **Max instances**: Currently capped at 150 per service (`--max-instances=150`).
- **Session affinity**: Enabled — each user's WebSocket/SSE connection is sticky to one instance.
- **Session pattern**: Teacher-guided, students progress through activities sequentially. At peak, ~80% of students are on the same activity (service), ~20% transitioning.

### Services used per track per language

**One language of the Sustainability track** uses 6 services per session:

| Activity | Service | Memory |
|----------|---------|--------|
| Activity 2 (Model Building) | model-building-game-es-sustainability | 4Gi |
| Activity 3 (Final Model) | model-building-game-es-final-sustainability | 4Gi |
| Activity 6 (Bias Detective) | bias-detective-es-sustainability | 2Gi |
| Activity 7 (Fairness Fixer) | fairness-fixer-es-sustainability | 2Gi |
| Activity 8 (Upgrade) | sustainability-upgrade-es | 2Gi |
| Activity 5/9 (Moral Compass) | moral-compass-es-sustainability | 2Gi |

The **Main track** follows the same pattern with its 6–7 ES services.

### Instances required at peak

At peak, ~80% of users are on the "hot" service. Instances needed = ceil(users / concurrency).

| Total Simultaneous Users | On hot service (80%) | Instances needed (hot) | On other services (20%) | Instances needed (other, ~2 services) | Within max=150? |
|--------------------------|---------------------|----------------------|------------------------|--------------------------------------|-----------------|
| **1,000** | 800 | **40** | 200 | ~5 each | Yes |
| **2,000** | 1,600 | **80** | 400 | ~10 each | Yes |
| **5,000** | 4,000 | **200** | 1,000 | ~25 each | **No** — hot service capped at 150, ~850 users queued/dropped |
| **10,000** | 8,000 | **400** | 2,000 | ~50 each | **No** — hot service capped at 150, ~5,000 users unable to connect |

> **5,000+ users**: The current `max-instances=150` cap limits each service to ~3,000 concurrent users (150 × 20 concurrency). Serving 5,000+ bursty users on a single activity requires either raising `max-instances` or distributing users across multiple service clones.

### Cost per burst-hour (active instances)

When instances are actively serving requests, they bill at the full active rate. This is the **marginal cost during a burst** above the idle baseline.

**Per active-instance-hour:**

| Service type | CPU cost | Memory cost | Total/instance/hr |
|-------------|----------|-------------|-------------------|
| 2 vCPU / 2 GiB | $0.1728 | $0.0180 | **$0.1908** |
| 2 vCPU / 4 GiB | $0.1728 | $0.0360 | **$0.2088** |

**Peak single-service cost per burst-hour** (the "hot" service at 80% of users):

| Users | Hot instances | If 4Gi (model-building) | If 2Gi (other activities) |
|-------|-------------|------------------------|--------------------------|
| **1,000** | 40 | **$8.35/hr** | **$7.63/hr** |
| **2,000** | 80 | **$16.70/hr** | **$15.26/hr** |
| **5,000** | 150 (capped) | **$31.32/hr** | **$28.62/hr** |
| **10,000** | 150 (capped) | **$31.32/hr** | **$28.62/hr** |

**Total cross-service cost per burst-hour** (hot service + ~2 secondary services):

| Users | Hot instances | Secondary instances (×2 svcs) | Total active instances | Blended cost/hr |
|-------|-------------|-------------------------------|----------------------|-----------------|
| **1,000** | 40 | 5 + 5 = 10 | 50 | **$10.26** |
| **2,000** | 80 | 10 + 10 = 20 | 100 | **$20.52** |
| **5,000** | 150 | 25 + 25 = 50 | 200 | **$40.44** |
| **10,000** | 150 | 50 + 50 = 100 | 250 | **$50.70** |

> Blended rate uses a weighted mix: ~40% of instances serve 4Gi services (model-building activities take the most time), ~60% serve 2Gi services.

### Estimated session cost (one 3-hour class session, one track, one language)

During a full 3-hour guided session, students move through all 6 activities. The burst is not sustained on one service for 3 hours — each activity takes ~30 min, so the peak on any one service lasts roughly 30–45 min. We model **1.5 equivalent full-burst hours** across the session to account for staggered transitions.

| Users | Active instances (peak) | Cost per burst-hr | × 1.5 equiv hrs | **Session cost** |
|-------|------------------------|-------------------|-----------------|------------------|
| **1,000** | ~50 | $10.26 | 1.5 | **$15.39** |
| **2,000** | ~100 | $20.52 | 1.5 | **$30.78** |
| **5,000** | ~200 | $40.44 | 1.5 | **$60.66** |
| **10,000** | ~250 | $50.70 | 1.5 | **$76.05** |

### Monthly projections (classroom usage patterns)

Assumptions for a typical school month in Spain:
- **20 school days/month**
- **1 class session per day** using the platform (per track)
- Session duration: 3 hours
- Both tracks (Main + Sustainability) are active but used by different class groups

| Users per session | Session cost | × 20 days | + Idle baseline (all min=1) | **Monthly total** |
|-------------------|-------------|-----------|----------------------------|-------------------|
| **1,000** | $15.39 | $307.80 | $1,140.48 | **$1,448** |
| **2,000** | $30.78 | $615.60 | $1,140.48 | **$1,756** |
| **5,000** | $60.66 | $1,213.20 | $1,140.48 | **$2,354** |
| **10,000** | $76.05 | $1,521.00 | $1,140.48 | **$2,661** |

> These are per-track estimates. If both tracks run simultaneously with the same user count, double the session/burst costs (but not the idle baseline, which already covers both tracks).

### Capacity limits and scaling considerations

| Scenario | Max concurrent users per service (at concurrency=20) | Action needed |
|----------|-------------------------------------------------------|---------------|
| **1,000 users** | 40 instances — well within max=150 | None |
| **2,000 users** | 80 instances — within max=150 | None |
| **5,000 users** | 200 needed, **capped at 150** | Raise `--max-instances` to 250+ or add service replicas |
| **10,000 users** | 400 needed, **capped at 150** | Raise `--max-instances` to 500+ **and** request GCP quota increase |

> **GCP default quota**: Cloud Run has a default limit of 100 instances per service (can be raised). The YMLs already set `max-instances=150`, which is above default and may require a quota increase. For 5,000+ users, you would need to request further quota increases from GCP.

---

## Summary

| Metric | Value |
|--------|-------|
| Total Cloud Run services | **38** |
| Main track services | 20 (all at min=1) |
| Sustainability track services | 18 (all at min=0) |
| Current monthly baseline (idle) | **~$596/mo** |
| Projected baseline (all min=1) | **~$1,140/mo** |
| Cost to promote sustainability to min=1 | **+~$544/mo** |
| Monthly with 1,000 bursty users (20 sessions) | **~$1,448/mo** |
| Monthly with 2,000 bursty users (20 sessions) | **~$1,756/mo** |
| Monthly with 5,000 bursty users (20 sessions) | **~$2,354/mo** |
| Monthly with 10,000 bursty users (20 sessions) | **~$2,661/mo** |

### Cost reduction levers

- **Committed Use Discounts (CUDs)**: 1-year or 3-year commitments can reduce costs by 17–40%.
- **Reduce min-instances selectively**: Only promote high-traffic sustainability services to min=1; keep lower-traffic ones at min=0 and accept cold starts.
- **Reduce memory on non-model-building services**: Services that don't load ML models could potentially run on 1Gi instead of 2Gi, saving ~$6.48/mo each.
- **Consolidate language variants**: If a single service could serve all 3 languages via a query param, that would cut 3 services down to 1 (saving ~$52/mo per consolidation).
- **Raise max-instances only where needed**: For 5,000+ user scenarios, raise `max-instances` only on the highest-traffic services (model-building, bias-detective) rather than all 38.

---

*Rates: [Google Cloud Run Pricing](https://cloud.google.com/run/pricing), Tier 1, `us-central1`. Verify current rates before making purchasing decisions.*

# Cloud Run Stability Plan: 100 Concurrent Users Over 3 Days

**Date:** 2025-03-25
**Context:** Class using sustainability-variant Gradio apps needs healthy infrastructure for ~100 simultaneous users over the next 3 days.

---

## Current Error Summary

| Priority | Error | Count | Affected Service(s) | Category |
|----------|-------|-------|---------------------|----------|
| P0 | `RuntimeError: Caught handled exception, but response already started` | 1,606 | what-is-ai | Gradio concurrency bottleneck |
| P0 | `HTTPException: 404: Not Found` | 1,606 | what-is-ai | SSE stream collapse (same root cause) |
| P1 | `AttributeError: 'NoneType' object has no attribute 'get'` | 152+131+31+... | fairness-fixer-es, bias-detective-es/ca/en, etc. | Null API response |
| P1 | `The request was aborted because there was no available instance` | 41 | fairness-fixer-es-sustainability | Cold start / scaling |
| P2 | `Value 9 is greater than maximum value 3` | 96 | model-building-game-es-final-sustainability | Gradio component mismatch |
| P2 | `Value: Menor is not in the list of choices` | 82 | what-is-ai | i18n choice mismatch |
| P2 | `Value: 'Completo (100%)' is not in the list of choices` | 32 | model-building-game-es-final | i18n choice mismatch |
| P3 | `ValueError: localhost is not accessible, shareable link must be created` | 22 | fairness-fixer-en-sustainability | Container networking |
| P3 | `TypeError: str is not valid UTF-8: surrogates not allowed` | 22 | fairness-fixer-ca-sustainability | Encoding |
| P3 | `TypeError: '<' not supported between instances of 'NoneType' and 'int'` | 8 | model-building-game-es | Null comparison |

---

## Recommended Changes

### 1. INFRASTRUCTURE: Eliminate Cold Starts (Critical for Class)

**Problem:** Many sustainability services have `--min-instances=0`. When 100 students hit the apps simultaneously, Cloud Run must spin up containers from scratch (10-30s cold start), causing the "no available instance" errors (41 occurrences on fairness-fixer-es-sustainability alone).

**Fix:** In `deploy_gradio_apps_sustainability.yml`, set `--min-instances=1` for ALL services that will be used during class.

**File:** `.github/workflows/deploy_gradio_apps_sustainability.yml`

Services currently at `min-instances=0` that need `min-instances=1`:
- `model-building-game-en-sustainability` (line 115)
- `model-building-game-en-final-sustainability` (line 200)
- `model-building-game-es-final-sustainability` (line 228)
- `model-building-game-ca-final-sustainability` (line 256)
- `bias-detective-en-sustainability` (line 285)
- `fairness-fixer-en-sustainability` (line 370)
- `sustainability-upgrade-en` (line 455)
- `sustainability-upgrade-ca` (line 483)
- `sustainability-upgrade-es` (line 511)
- `moral-compass-en-sustainability` (line 540)

**Cost note:** At ~$0.05/hr per idle instance with 2 vCPU + 2-4 GiB, keeping 10 services warm for 3 days costs roughly $36. Worth it for a class.

**Alternative (faster, no redeploy):** Use `gcloud run services update` directly:
```bash
# Example for each service:
gcloud run services update fairness-fixer-es-sustainability \
  --min-instances=1 \
  --region=us-central1 \
  --project=<PROJECT_ID>
```
This takes effect immediately without rebuilding the image.

---

### 2. Raise Gradio Concurrency Limit on Standard Apps

**Problem:** The `what-is-ai` app is launched via CASE 3 in `launch_entrypoint.py` (line 252-261) without an explicit `.queue()` call. The comment says "NO QUEUE" but this is **misleading** — in Gradio 5.x (we use 5.49.1), queue is **enabled by default** in `Blocks.__init__()`. The real problem is the **default concurrency limit**.

When `.queue()` is called without arguments (or implicitly by Gradio), `default_concurrency_limit` resolves to **1** (unless the env var `GRADIO_DEFAULT_CONCURRENCY_LIMIT` is set). This means each event handler can only process **one request at a time**. With Cloud Run sending up to 20 concurrent users to one instance, 19 users are serialized behind a single-slot queue.

**What users see:** A student clicks "Next" or "Run AI Prediction". The app uses `yield`-based generators for step navigation, which require SSE streams. With `default_concurrency_limit=1`, only one SSE stream is active at a time. The other 19 users' connections pile up, time out, or get dropped:
1. A user's SSE stream starts (HTTP headers sent), then gets interrupted → `RuntimeError: response already started`
2. The broken stream causes the Gradio JS client to retry on a stale endpoint → `HTTPException: 404`
3. Both errors fire per failed request, explaining the identical count of 1,606.

**By contrast, model-building-game variants explicitly call `.queue(default_concurrency_limit=40)` and do NOT have this problem.**

#### Fix Options (two approaches, pick one):

**Option A — Environment variable (no code change, no redeploy):**

Set `GRADIO_DEFAULT_CONCURRENCY_LIMIT` in the Cloud Run service config for all standard apps:
```bash
# Immediate effect, no image rebuild needed:
gcloud run services update what-is-ai \
  --update-env-vars=GRADIO_DEFAULT_CONCURRENCY_LIMIT=20 \
  --region=us-central1 \
  --project=<PROJECT_ID>
```
This is the **fastest fix for the class**. Apply to all standard (non-model-building-game) services.

Also add it to the deploy workflow `env_vars` so it persists across redeployments:
```yaml
env_vars: >-
  APP_NAME=what-is-ai,
  GRADIO_SERVER_NAME=0.0.0.0,
  GRADIO_DEFAULT_CONCURRENCY_LIMIT=20,
  ...
```

**Option B — Code change (requires redeploy):**

In `launch_entrypoint.py`, lines 252-261, add an explicit `.queue()` call to match what model-building-game already does:

```python
# CASE 3: All other standard apps (judge, tutorial, etc.)
else:
    demo = build_standard_app(app_name)
    logger.info(f"Launching standard app: {app_name}")

    demo.queue(default_concurrency_limit=20)

    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        show_api=False,
        show_error=True,
    )
```

**Risk assessment of `.queue(default_concurrency_limit=20)`:**

| Risk | Level | Notes |
|------|-------|-------|
| API compatibility | **None** | `default_concurrency_limit` is the correct param for Gradio 5.x |
| Breaking change | **None** | Only `concurrency_count` was removed in 5.x; we don't use it |
| Functional regression | **Very low** | Queue is already on implicitly; this just raises the limit from 1→20 |
| Memory pressure | **Low** | what-is-ai does simple math scoring (no ML inference); 20 concurrent handlers on 2 GiB is fine |

**Recommendation:** Use Option A (env var) for the class since it's immediate. Then apply Option B in the next code deploy for permanence. Set the limit to 20 to match the Cloud Run `--concurrency=20` setting — there's no benefit to allowing more concurrent Gradio handlers than Cloud Run will send to a single instance.

---

### 3. CODE FIX: Null-Safe Leaderboard Display After Quiz Submission (Future)

**Problem:** `AttributeError: 'NoneType' object has no attribute 'get'` across bias-detective and fairness-fixer apps (300+ total occurrences). When a student answers a quiz correctly, `trigger_api_update` saves their progress to DynamoDB, then calls `get_leaderboard_data()` twice to build a before/after display. If the second call fails (API timeout, connection error), it returns `None` as `curr`. The bug is in `generate_success_message(prev, curr, ...)` which guards `prev` with `if prev` but does NOT guard `curr`.

**User experience:** Student answers correctly, their work IS saved, but instead of a celebration card they see a red error toast: `AttributeError: 'NoneType' object has no attribute 'get'`. They think the app is broken and don't know their answer was recorded. Refreshing the page restores their progress.

**Will scale with load:** 100 concurrent students = 100 concurrent `list_users` API calls. Backend throttling/timeouts become more likely, increasing the error rate beyond the current ~365 occurrences.

**Recommended fix:** Guard at the `quiz_logic_wrapper` level (not just `generate_success_message`) to avoid showing a misleading zeroed-out score card:

```python
# In quiz_logic_wrapper, after trigger_api_update returns:
if curr is None:
    return (
        gr.update(),           # don't touch dashboard
        gr.update(),           # don't touch leaderboard
        "<div class='hint-box'>✅ Correct! Your answer was saved. "
        "The leaderboard is temporarily unavailable — "
        "refresh the page to see your updated score.</div>",
        new_tasks,
    )
msg = generate_success_message(prev, curr, cfg["success"])
```

**Affected files (all have the identical bug pattern):**
- `bias_detective_en.py` — lines 1805, 1809, call site ~2548
- `bias_detective_es.py` — lines 1808, 1812
- `fairness_fixer_en.py` — lines 1429, 1433
- `fairness_fixer_es.py` — lines 1432, 1436
- `bias_detective_en_sustainability.py` — lines 566, 570
- `bias_detective_es_sustainability.py` — lines 583, 587
- `fairness_fixer_en_sustainability.py` — lines 570, 574
- `fairness_fixer_es_sustainability.py` — lines 587, 591

---

### 3a. CODE FIX: Remove `time.sleep(1.0)` and Deduplicate API Calls in `handle_load` (Future — High Impact)

**Problem:** Every sustainability app's `demo.load()` handler (`handle_load`) makes 5 sequential API calls plus a hardcoded `time.sleep(1.0)`, taking ~3 seconds per request. When 50-100 students open the page simultaneously and the Vue portal loads 6 Gradio iframes at once, this creates 300-600 concurrent `handle_load` executions. Even with `default_concurrency_limit=20`, requests queue up and SSE connections time out before `handle_load` completes — producing the red error banner that forces students to refresh.

**Root cause details:**

1. **`time.sleep(1.0)` after `update_moral_compass`** — exists in all 9 sustainability apps (bias-detective, fairness-fixer, moral-compass-challenge × 3 languages). The sleep was added to let a DynamoDB GSI propagate after a write, but the write is just syncing *existing* data on page load, not creating new scores. The subsequent `list_users` query will return the user's previously-propagated data regardless.

2. **Duplicate `client.get_user()` calls** — `handle_load` calls `get_user()` twice for the same user: once to resolve team name (~line 1702), once to fetch `completedTaskIds` (~line 1722). One call can serve both purposes.

3. **5 sequential API calls total** in `handle_load`: `_try_session_based_auth` → `fetch_user_history` → `get_user` (×2) → `update_moral_compass` + sleep → `ensure_table_and_get_data`

**Affected files (all have identical pattern):**
- `bias_detective_{en,es,ca}_sustainability.py` — sleep at lines 1729/1746/1746
- `fairness_fixer_{en,es,ca}_sustainability.py` — sleep at lines 1962/1976/1978
- `moral_compass_challenge_sustainability_{en,es,ca}.py` — sleep at lines 1500/1517/1517

**Recommended fix:**
1. Remove `time.sleep(1.0)` from all 9 files
2. Merge the two `client.get_user()` calls into one, using the result for both team resolution and task list fetching
3. Estimated impact: cuts `handle_load` from ~3s to ~1s, tripling effective throughput under load

**Why the sleep is safe to remove:**
- The `update_moral_compass` write syncs data that already exists in DynamoDB — it's not creating new scores
- The subsequent `list_users` (on GSI) returns previously-propagated data regardless
- For brand-new users, the UI falls back gracefully with default values

**Connection to the iframe loading issue:**
The Vue portal (`SustainableAI.vue`) loads 6 Cloud Run Gradio iframes simultaneously on page mount. Each fires `demo.load()` → `handle_load`. With 50 students × 6 apps = 300 concurrent handler calls, the 1s sleep alone wastes 300 CPU-seconds of concurrency slots per page-load wave. This is the primary cause of the "red error banner on first load" that students experience.

---

### 3a-ext. Full `handle_load` Performance Analysis and Optimization Roadmap

**`handle_load` wall-clock time by app type:**

| App Type | Activities | API Calls | Wall-Clock Time | Has Sleep? |
|----------|-----------|-----------|-----------------|------------|
| Model Building Game | 4 | 2 | 3.5-5.5s | No |
| Sustainability Upgrade | 8 | 3-5 | 3.5-6s | No |
| Bias Detective | 6 | 7 | 6-9s | Yes (1s) |
| Fairness Fixer | 7 | 7 | 6-9s | Yes (1s) |
| Moral Compass Challenge | 5 | 7 | 6-9s | Yes (1s) |

**Sequential call chain in bias-detective/fairness-fixer/moral-compass (the slow apps):**
```
_try_session_based_auth()     → Cognito session lookup         ~0.5-1s
fetch_user_history()          → playground.get_leaderboard()   ~1.5-2s
client.get_user() #1          → DynamoDB (team resolution)     ~0.5-1s
client.get_user() #2          → DynamoDB (task IDs)            ~0.5-1s  [DUPLICATE]
client.update_moral_compass() → DynamoDB write                 ~1-1.5s
time.sleep(1.0)               → blocking wait                  ~1s      [REMOVE]
ensure_table_and_get_data()   → client.list_users(limit=500)   ~1-2s
                                                        TOTAL: ~6-9s
```

**Optimization tiers (cumulative impact):**

**Tier 1 — Remove sleep + deduplicate get_user (est. savings: ~2s per request)**
- Remove `time.sleep(1.0)` from all 9 files
- Merge two `client.get_user()` calls into one — use single response for both team name and task IDs
- New estimated time: ~4-7s

**Tier 2 — Reduce leaderboard payload (est. savings: ~0.5-1s per request)**
- `client.list_users(limit=500)` fetches ALL users on every load just to find one user's rank
- Reduce to `limit=50` for initial load (sufficient for rank display)
- Or add a `get_user_rank` endpoint to avoid fetching the full leaderboard
- New estimated time: ~3.5-6s

**Tier 3 — Parallelize independent API calls (est. savings: ~1-2s per request)**
- `fetch_user_history()` and `client.get_user()` are independent — run concurrently with `asyncio.gather` or `concurrent.futures.ThreadPoolExecutor`
- `update_moral_compass` can run fire-and-forget (no need to wait for the result before reading leaderboard, since the data was already there)
- New estimated time: ~2-4s

**Tier 4 — Cache leaderboard data server-side (est. savings: ~1-2s for repeat loads)**
- Model-building-game already has `_leaderboard_cache` with 45s TTL
- Bias-detective/fairness-fixer/moral-compass don't cache at all
- Add a shared in-memory cache so when 50 students load simultaneously, only the first request fetches `list_users(500)` — the rest read cache
- New estimated time: ~1-2s (with warm cache)

**Combined impact:** From ~6-9s → ~1-2s per `handle_load`, making the app responsive enough to survive 50-100 concurrent iframe loads without SSE timeouts.

---

### 3b. CODE FIX: Thread-Safety in moral_compass_challenge and ethical_revelation (Future)

**Problem:** Both `moral_compass_challenge.py` and `ethical_revelation.py` have unprotected shared mutable state (`_user_stats_cache` dict read/written without the existing `_cache_lock`). These apps are currently safe only because Gradio's implicit `default_concurrency_limit=1` serializes all requests. If concurrency is raised for these apps in the future, race conditions will occur on cache read/write.

**Fix:** Use the existing `_cache_lock` around `_user_stats_cache` access in `_compute_user_stats()`, or raise the concurrency limit only after adding the lock.

---

### 4. CODE FIX: i18n Choice Mismatches

**Problem:** Spanish translations produce choice values that don't match the expected English values:
- `Menor` vs expected `['Minor', 'Moderate', 'Serious']` (82 occurrences in what-is-ai)
- `Completo (100%)` vs expected `['Pequeno (20%)']` (32 occurrences in model-building-game-es-final)
- `Value 9 is greater than maximum value 3` (96 occurrences) — likely a Slider/Number component with wrong `maximum`

**Root cause:** Gradio validates submitted values against the `choices` list defined at component creation time. When apps are localized, the component choices and submitted values must match exactly.

**Investigation needed:**
- In `what_is_ai.py`: Find the severity Dropdown — verify that the `choices` list matches the translated labels users see
- In model-building-game Spanish variants: Check that data-size Radio/Dropdown choices match the translated labels
- For the "Value 9 > maximum 3" error: Find the Slider or Number component and verify its `maximum` parameter matches the valid range for the sustainability variant

**Quick fix approach:** Ensure Gradio components use value-label pairs:
```python
# Instead of:
gr.Dropdown(choices=["Minor", "Moderate", "Serious"])

# Use value-label pairs so the value stays consistent regardless of language:
gr.Dropdown(choices=[("minor", "Menor"), ("moderate", "Moderado"), ("serious", "Grave")])
```

---

### 5. CODE FIX: Localhost / Share Error

**Problem:** `ValueError: When localhost is not accessible, a shareable link must be created` (22 occurrences on fairness-fixer-en-sustainability)

**Root cause:** This happens when `GRADIO_SERVER_NAME` is not set to `0.0.0.0` or when the app fails to bind to the port. Could occur if:
1. The env var is not being set for this specific service
2. The app is crashing during initialization and Gradio falls back to localhost

**Fix:** Verify in `deploy_gradio_apps_sustainability.yml` that `fairness-fixer-en-sustainability` has:
```yaml
env_vars: >-
  APP_NAME=fairness-fixer-en-sustainability,
  GRADIO_SERVER_NAME=0.0.0.0,
  GRADIO_ANALYTICS_ENABLED=False,
  GRADIO_NUM_PORTS=1
```

If it does, this error is likely a symptom of the app crashing during startup (possibly from the NoneType errors above) and Gradio retrying on localhost. Fixing #3 should reduce this.

---

### 6. CODE FIX: UTF-8 Surrogate Error

**Problem:** `TypeError: str is not valid UTF-8: surrogates not allowed` (22 occurrences on fairness-fixer-ca-sustainability)

**Root cause:** Catalan text likely contains characters that, when passed through JSON serialization or pandas string operations, produce surrogate code points (U+D800 to U+DFFF).

**Fix:** Add encoding sanitization to the response path:
```python
# Sanitize any surrogate characters before returning to Gradio
text = text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
```

---

## Pre-Class Checklist (Priority Order)

### Day Before Class — Infrastructure (No Code Changes, No Redeploy)

- [ ] **Set min-instances=1** on all sustainability services via `gcloud run services update` (immediate effect)
- [ ] **Set `GRADIO_DEFAULT_CONCURRENCY_LIMIT=20`** on all standard (non-model-building-game) services via `gcloud run services update --update-env-vars` (immediate fix for what-is-ai 404s)
- [ ] **Verify all services are running** — hit `/healthz` or load the root URL for each
- [ ] **Check Cloud Run quotas** — ensure the GCP project can scale to enough instances (100 users / 20 concurrency = 5 instances minimum per active app)

### Day Before Class — Code Fixes (Require Redeploy)

- [ ] **Add explicit `.queue(default_concurrency_limit=20)`** in `launch_entrypoint.py` CASE 3 for permanence (env var handles this for now)
- [ ] **Add null guards** on API response `.get()` calls (fixes 300+ NoneType errors)
- [ ] **Verify i18n choices** match in Spanish/Catalan variants
- [ ] **Redeploy** sustainability apps via workflow dispatch

### During Class — Monitoring

- [ ] Watch Cloud Run metrics dashboard for:
  - Instance count (should stay >0 for all services)
  - Request latency (p99 should be <10s)
  - Error rate (target <1%)
  - Memory utilization (should stay <80% of limit)
- [ ] Have `gcloud run services update --max-instances=200` ready if scaling limits are hit

### After Class — Revert Cost Optimization

- [ ] Set `--min-instances=0` back on non-critical sustainability services
- [ ] Update the workflow YAML with permanent min-instances decisions

---

## Quick Reference: Service Architecture

```
Cloud Run (us-central1)
├── Project: sustainability-apps
│   ├── model-building-game-{en,es,ca}-sustainability        (4Gi, min=0→1)
│   ├── model-building-game-{en,es,ca}-final-sustainability  (4Gi, min=0→1)
│   ├── bias-detective-{en,es,ca}-sustainability              (2Gi, min=0/1)
│   ├── fairness-fixer-{en,es,ca}-sustainability              (2Gi, min=0/1)
│   ├── sustainability-upgrade-{en,es,ca}                     (2Gi, min=0→1)
│   └── moral-compass-{en,es,ca}-sustainability               (2Gi, min=0/1)
│
├── Scaling: concurrency=20 per instance, max-instances=150
├── Session affinity: enabled
├── Timeout: 3000s (50 min) [sustainability] / 300s [standard]
└── Queue: enabled by default (Gradio 5.x), but default_concurrency_limit=1 on standard apps (needs →20)
```

---

## Estimated Impact

| Fix | Errors Resolved | Effort | Requires Redeploy? |
|-----|----------------|--------|-------------------|
| Raise concurrency limit on standard apps | ~1,606 (what-is-ai) | 5 min gcloud env var | No (env var) or Yes (code) |
| Set min-instances=1 | ~41 (no available instance) | 5 min gcloud commands | No |
| Null-safe API responses | ~300+ (NoneType errors) | 30 min code review + fix | Yes |
| Fix i18n choices | ~210 (choice mismatches) | 1-2 hrs investigation | Yes |
| UTF-8 sanitization | ~22 (surrogate errors) | 15 min | Yes |
| Fix localhost binding | ~22 (likely resolved by #3) | 0 (symptom fix) | No |

**Total: ~1,900+ errors eliminated with these fixes.**

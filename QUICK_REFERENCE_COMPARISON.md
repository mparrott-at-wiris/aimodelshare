# Quick Reference: Original vs Sustainability Variants

## Side-by-Side Comparison

| Component | Original Moral Compass | Sustainability Variant | Match? |
|-----------|----------------------|----------------------|--------|
| **ARCHITECTURE** |
| Framework | Gradio + FastAPI | Gradio + FastAPI | ✅ |
| Caching | SQLite dual-tier | SQLite dual-tier | ✅ |
| Threading | Limited (OMP=1) | Limited (OMP=1) | ✅ |
| Queue | 40 concurrent | 40 concurrent | ✅ |
| **INFRASTRUCTURE** |
| Cloud Platform | GCP Cloud Run | GCP Cloud Run | ✅ |
| Memory | 4Gi | 4Gi | ✅ |
| CPU | 2 cores | 2 cores | ✅ |
| Min Instances | 1 | 1 | ✅ |
| Max Instances | 150 | 150 | ✅ |
| Timeout | 3000s | 3000s | ✅ |
| **APPLICATION DATA** |
| Dataset | COMPAS | WiDS | 🎨 By Design |
| Domain | Criminal Justice | Climate/Energy | 🎨 By Design |
| Target Variable | two_year_recid | high_energy_usage | 🎨 By Design |
| Feature Count | 11 | 14 | 🎨 By Design |
| Sample Size | 7,000 rows | 10,000 rows | 🎨 By Design |
| **DEPLOYMENT** |
| GCP Registry | moral-compass-apps | sustainability-apps | 🎨 By Design |
| Dockerfile | Dockerfile | Dockerfile_sustainability | 🎨 By Design |
| Cache Files | prediction_cache*.gz | wids_prediction_cache*.gz | 🎨 By Design |
| Converter | convert_db.py | convert_db_wids.py | 🎨 By Design |
| Workflow | deploy_gradio_apps.yml | deploy_gradio_apps_sustainability.yml | 🎨 By Design |
| **API INTEGRATION** |
| Leaderboard API | cf3wdpkg0d...aws | bhtrtkrbf4...aws | 🎨 By Design |
| **APP VARIANTS** |
| Languages | en, es, ca | en, es, ca | ✅ |
| Game Types | standard, final | standard, final | ✅ |
| Total Apps | 6 variants | 6 variants | ✅ |

## Legend
- ✅ **Match**: Identical configuration (expected for scalability)
- 🎨 **By Design**: Intentional domain-specific difference

## Deployment Status

### ✅ Ready Components
- [x] Application code (6 variants)
- [x] Dataset file (`datasets/recreated_wids_v2_ny_10k.csv`)
- [x] Cache converter (`convert_db_wids.py`)
- [x] Dockerfile (`Dockerfile_sustainability`)
- [x] Deployment workflow (`deploy_gradio_apps_sustainability.yml`)
- [x] Cache generation workflows (2 workflows)
- [x] App registration in `__init__.py`
- [x] App routing in `launch_entrypoint.py`

### ⏳ Pre-Deployment Steps Needed
- [ ] Run `build_wids_cache.yml` (4-6 hours)
- [ ] Run `build_wids_full_models_cache.yml` (4-6 hours)
- [ ] Verify GCP Artifact Registry `sustainability-apps` exists
- [ ] Test API endpoint: `https://bhtrtkrbf4.execute-api.us-east-1.amazonaws.com/prod/m`

## Scaling Validation

Both variants use the same scaling parameters:

```yaml
Memory: 4Gi
CPU: 2 cores
Concurrency: 20 requests/instance
Min Instances: 1
Max Instances: 150
Max Concurrent Users: 3,000 (20 × 150)
```

**Expected Performance** (identical for both):
- Cache hit rate: >99%
- P95 latency (cached): <500ms
- P95 latency (uncached): <5s
- Cold start: <10s

## Risk Level: LOW ✅

No blocking issues identified. The sustainability variant follows proven patterns from the original implementation.

---
**Conclusion**: Deploy with confidence once pre-deployment checklist is complete.

# Performance Optimization Rollout Guide

## Quick Reference

This guide helps you safely roll out the GSI-based optimizations for `list_tables` and `list_users` endpoints.

## Prerequisites

- ✅ PR merged to main branch
- ✅ `byUser` GSI exists and is ACTIVE (enabled by `enable_gsi_by_user=true`)
- ✅ Integration tests passing on current deployment

## Phase 1: Safe Deployment with Defaults

**Goal:** Deploy code with all optimizations disabled to validate deployment process.

```bash
cd infra
terraform workspace select dev

# Verify current settings (should be defaults)
grep -E "use_metadata_gsi|read_consistent" terraform.tfvars || echo "Using defaults"

# Deploy
terraform plan
terraform apply
```

**Validation:**
```bash
# Get API URL
API_BASE_URL=$(terraform output -raw api_base_url)

# Run integration tests
cd ..
python tests/test_api_integration.py "$API_BASE_URL"
python tests/test_api_pagination.py "$API_BASE_URL"

# Check CloudWatch Logs for metrics
# Look for JSON lines with "metric": "list_tables" and "strategy": "scan"
```

**Expected Metrics:**
```json
{"metric": "list_tables", "strategy": "scan", "consistentRead": true, ...}
{"metric": "list_users", "strategy": "partition_query", "consistentRead": true, ...}
```

## Phase 2: Enable GSI Query

**Goal:** Switch `list_tables` to use GSI query instead of full table scan.

### Option A: Via terraform.tfvars
```hcl
# infra/terraform.tfvars
use_metadata_gsi = true
```

### Option B: Via CLI
```bash
terraform apply -var="use_metadata_gsi=true"
```

**Validation:**
```bash
# Wait 30s for Lambda cold start
sleep 30

# Run tests again
python tests/test_api_integration.py "$API_BASE_URL"
python tests/test_api_pagination.py "$API_BASE_URL"

# Check metrics - strategy should change
```

**Expected Metrics:**
```json
{"metric": "list_tables", "strategy": "gsi_query", "consistentRead": false, ...}
```

**Success Criteria:**
- ✅ All tests pass
- ✅ `durationMs` same or lower than Phase 1
- ✅ No increase in error rates
- ✅ User-facing behavior unchanged

**Comparison Query (CloudWatch Insights):**
```
fields @timestamp, metric, strategy, durationMs, countFetched
| filter metric = "list_tables"
| stats avg(durationMs) as avgDuration, avg(countFetched) as avgFetched by strategy
```

## Phase 3: Reduce Read Consistency (Optional)

**Goal:** Reduce DynamoDB read costs by ~50% using eventually consistent reads.

**Prerequisites:**
- ✅ Phase 2 deployed and validated for at least 24 hours
- ✅ No user complaints about data visibility
- ✅ Understand eventual consistency trade-off

```bash
terraform apply -var="use_metadata_gsi=true" -var="read_consistent=false"
```

**Validation:**
```bash
# Create a table and immediately list
TABLE_ID="test-consistency-$(date +%s)"
curl -X POST "$API_BASE_URL/tables" \
  -H "Content-Type: application/json" \
  -d "{\"tableId\": \"$TABLE_ID\", \"displayName\": \"Consistency Test\"}"

# List tables immediately (may not appear for ~100-500ms)
curl "$API_BASE_URL/tables?limit=100"

# Verify it eventually appears
sleep 1
curl "$API_BASE_URL/tables?limit=100" | grep "$TABLE_ID"
```

**Expected Metrics:**
```json
{"metric": "list_tables", "strategy": "gsi_query", "consistentRead": false, ...}
{"metric": "list_users", "strategy": "partition_query", "consistentRead": false, ...}
```

**Success Criteria:**
- ✅ Tests pass
- ✅ New items appear within acceptable delay (<1 second)
- ✅ No user experience degradation
- ✅ DynamoDB read costs reduced

## Phase 4: Production Rollout

After validating in dev for 1 week and staging for 1 week:

```bash
# Switch to production workspace
terraform workspace select prod

# Apply same settings
terraform apply -var="use_metadata_gsi=true" -var="read_consistent=false"

# Monitor closely
```

**Production Monitoring:**
```
# P95 latency
fields @timestamp, metric, durationMs
| filter metric in ["list_tables", "list_users"]
| stats pct(durationMs, 95) as p95, pct(durationMs, 99) as p99 by metric

# Error rate
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() as errors by bin(5m)

# Cost efficiency
fields metric, countFetched, countReturned
| filter metric = "list_tables"
| stats avg(countFetched) as avgFetch, avg(countReturned) as avgReturn
```

## Rollback Procedures

### Quick Rollback (Immediate)
```bash
# Revert to scan strategy
terraform apply -var="use_metadata_gsi=false" -var="read_consistent=true"

# System returns to original behavior within seconds
```

### Gradual Rollback (Phase by Phase)
```bash
# Step 1: Re-enable strong consistency
terraform apply -var="use_metadata_gsi=true" -var="read_consistent=true"

# If issues persist, Step 2: Disable GSI
terraform apply -var="use_metadata_gsi=false" -var="read_consistent=true"
```

## Troubleshooting

### Issue: Tests fail after enabling GSI

**Check:**
```bash
# Verify GSI is ACTIVE
aws dynamodb describe-table --table-name PlaygroundScores-dev \
  --query 'Table.GlobalSecondaryIndexes[?IndexName==`byUser`].IndexStatus'
```

**Solution:**
- If GSI not ACTIVE, wait for it to finish creating
- If GSI missing, set `enable_gsi_by_user=true` and apply

### Issue: Higher latency with GSI

**Investigate:**
```
fields metric, strategy, durationMs, countFetched
| filter metric = "list_tables"
| stats avg(durationMs) as avg, max(durationMs) as max, min(durationMs) as min by strategy
```

**Possible Causes:**
- Cold start (first request)
- GSI provisioning still in progress
- Network latency

**Solution:**
- Compare after warm-up period (5+ minutes)
- Check CloudWatch Lambda metrics for initialization time

### Issue: Items not appearing immediately (Phase 3)

**Expected:** Eventual consistency delay (typically 100-500ms)

**Verify Normal:**
```bash
# Create item
curl -X POST "$API_BASE_URL/tables" -H "Content-Type: application/json" \
  -d '{"tableId": "test-'$(date +%s)'", "displayName": "Test"}'

# Wait 500ms
sleep 0.5

# Should appear
curl "$API_BASE_URL/tables?limit=100"
```

**Action:**
- If delay >1 second consistently: Consider reverting to `read_consistent=true`
- If user complaints: Rollback Phase 3

## Feature Flags Summary

| Flag | Default | Phase | Impact |
|------|---------|-------|--------|
| `use_metadata_gsi` | false | 2 | Switches to GSI query, reduces latency/cost |
| `read_consistent` | true | 3 | Eventual consistency, reduces cost 50% |
| `default_table_page_limit` | 50 | Any | Changes default page size |
| `enable_gsi_leaderboard` | false | N/A | Reserved for future (not recommended) |
| `use_leaderboard_gsi` | false | N/A | Reserved for future (not recommended) |

## Support

If issues occur during rollout:
1. Check CloudWatch Logs for errors
2. Review metrics for anomalies
3. Run integration tests for regression
4. Execute rollback if needed
5. Investigate with metrics queries

## Success Metrics

After full rollout, expect:
- ✅ `list_tables` latency: 30-50% reduction (with GSI)
- ✅ DynamoDB read costs: ~50% reduction (with eventual consistency)
- ✅ Zero test failures
- ✅ Zero user-reported data visibility issues
- ✅ Scalability: Performance stable as data grows

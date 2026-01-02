# Testing Submission Verification Implementation

## Overview
This document describes how to test the robust submission handling and post-submit verification features implemented in `model_building_app_en.py`.

## Test Session ID
Use the provided live session ID for testing:
```
ad77321e-072b-42c5-9b89-db07c88f2d5c
```

## Test Scenarios

### 1. Successful Submission with Quick Leaderboard Update
**Expected Behavior:**
- User submits a model
- UI shows "⏳ Submission Processing" card with provisional accuracy diff
- Polling detects leaderboard update within a few attempts
- UI flips to success KPI card with actual leaderboard data
- Attempt counter increments
- Leaderboards show updated rankings

**How to Test:**
1. Navigate to app with session ID: `?sessionid=ad77321e-072b-42c5-9b89-db07c88f2d5c`
2. Click "Build & Submit Model"
3. Observe pending card during polling (should be brief)
4. Verify success card shows after detection
5. Check attempt counter incremented
6. Verify leaderboards updated with new submission

### 2. Successful Submission with Slow Backend (Polling Timeout)
**Expected Behavior:**
- User submits a model
- UI shows "⏳ Submission Processing" card
- Polling continues for up to 60 seconds (60 attempts × 1s)
- After timeout, UI shows success card with optimistic/simulated data
- Attempt counter increments
- Console logs show: "Polling timed out after 60 attempts. Using optimistic fallback."

**How to Test:**
This scenario is harder to test as it requires the backend to be slow. If backend responds quickly, you'll see scenario 1 instead. To observe this:
1. Check browser console logs during submission
2. Look for polling attempt logs: "Polling attempt N/60"
3. If all 60 attempts occur, you'll see the optimistic fallback message

### 3. Failed Submission (Invalid/Expired Token)
**Expected Behavior:**
- User submits a model
- Submission fails (e.g., network error, invalid token, backend unavailable)
- UI shows red error card: "❌ Submission Failed"
- Error card includes technical details in expandable section
- Attempt counter does NOT increment
- User can retry without penalty
- Leaderboards remain unchanged

**How to Test:**
This is difficult to test with a valid session token. Possible approaches:
1. **Wait for token expiration**: Wait until the session token expires naturally, then try submitting
2. **Network simulation**: Use browser DevTools to simulate network failure during submission
3. **Backend downtime**: If backend is temporarily unavailable, attempt submission

**Manual token invalidation (advanced):**
1. Open browser DevTools console
2. Before submission, you could try to tamper with the token state (though this may not work due to how Gradio manages state)

### 4. Preview Mode (No Token)
**Expected Behavior:**
- User not authenticated
- Clicking submit shows preview KPI card (green "🔬 Successful Preview Run!")
- Login form appears below preview card
- No polling occurs
- No attempt increment
- Leaderboards show skeleton/placeholder

**How to Test:**
1. Navigate to app WITHOUT session ID parameter
2. Click "Build & Submit Model"
3. Verify preview card appears
4. Verify login form is shown
5. Confirm no polling in console logs

### 5. Attempt Limit Reached
**Expected Behavior:**
- After 10 successful submissions
- Submit button shows "🛑 Limit Reached" and is disabled
- Error card shows: "🛑 Submission Limit Reached (10/10)"
- All input controls disabled
- User directed to "Finish and Reflect" section

**How to Test:**
1. Make 10 successful submissions
2. Verify UI transitions to limit-reached state
3. Confirm submit button and controls are disabled
4. Check attempt counter shows 10/10

## Key Features to Verify

### Polling Behavior
**Monitor console logs for:**
- `Baseline snapshot: row_count=X, best_score=Y, latest_ts=Z, latest_score=A`
- `Polling attempt N/60`
- `User rows changed detected after N polls` (on success)
- `Polling timed out after 60 attempts. Using optimistic fallback.` (on timeout)

### Cache Bypass
**Verify post-submit reads are fresh:**
All polling calls should use `_get_leaderboard_with_optional_token(playground, token)` which bypasses the 45-second cache. This ensures fresh data during verification.

### Change Detection
**The system detects leaderboard changes via:**
1. Row count increase (new submission added)
2. Best score improvement
3. Latest timestamp newer than baseline
4. Latest accuracy different from baseline

Any of these triggers detection and ends polling early.

## Configuration
Key constants in `model_building_app_en.py`:
- `LEADERBOARD_POLL_TRIES = 60` (line 473)
- `LEADERBOARD_POLL_SLEEP = 1.0` (line 474)
- `LEADERBOARD_CACHE_SECONDS = 45` (line 107)
- `ATTEMPT_LIMIT = 10` (line 466)

## Debugging
If issues occur:
1. Check browser console for error messages
2. Check DEBUG_LOG environment variable (set to "true" for verbose logging)
3. Monitor network tab for API calls to leaderboard
4. Look for exception tracebacks in console

## Expected Log Output

### Successful submission with quick detection:
```
Baseline snapshot: row_count=2, best_score=0.7234, latest_ts=1234567890.0, latest_score=0.7234
Submission successful. Server Score: 0.7456
Polling attempt 1/60
Polling attempt 2/60
Polling attempt 3/60
User rows changed detected after 3 polls
  Row count: 2 -> 3
  Best score: 0.7234 -> 0.7456
  Latest score: 0.7234 -> 0.7456
  Timestamp: 1234567890.0 -> 1234567950.0
```

### Failed submission:
```
Baseline snapshot: row_count=2, best_score=0.7234, latest_ts=1234567890.0, latest_score=0.7234
Submission FAILED: <error message>
```

### Polling timeout:
```
Baseline snapshot: row_count=2, best_score=0.7234, latest_ts=1234567890.0, latest_score=0.7234
Submission successful. Server Score: 0.7456
Polling attempt 1/60
Polling attempt 2/60
...
Polling attempt 60/60
Polling timed out after 60 attempts. Using optimistic fallback.
```

# Bias Detective Rank System Fix - Summary

## Overview
This change fixes the Bias Detective app to use Moral Compass API for ranks instead of falling back to the playground leaderboard. This ensures ranks reflect actual progress through the 21-task Bias Detective flow.

## Problem Statement
The Bias Detective app was falling back to playground leaderboard ranks when Moral Compass rank retrieval failed. This caused:
1. Ranks that didn't reflect Moral Compass progress (accuracy × ethical progress)
2. Static ranks that didn't update as users completed tasks
3. Confusion between two different ranking systems

## Solution Implemented

### 1. ChallengeManager Initialization (bias_detective.py)
**Location:** Lines 674-688

**Changes:**
```python
# Before: Generic initialization
cm = get_challenge_manager(username)
moral_compass_state["challenge_manager"] = cm

# After: Configured for 21-task Bias Detective flow
cm = get_challenge_manager(username)
if cm:
    cm.set_progress(
        tasks_completed=moral_compass_state.get("tasks_completed", 0),
        total_tasks=21,  # 21-task Bias Detective flow
        questions_correct=0,
        total_questions=0
    )
    # Set accuracy as primary metric
    cm.set_metric('accuracy', moral_compass_state["accuracy"], primary=True)
    moral_compass_state["challenge_manager"] = cm
```

**Impact:** Ensures moralCompassScore formula (accuracy × progress_ratio) uses correct totals for Bias Detective.

### 2. Remove Playground Fallback (bias_detective.py)
**Location:** Lines 517-534 (log_task_completion), Lines 611-625 (check_checkpoint_refresh)

**Changes:**
```python
# Before: Falls back to playground leaderboard
except Exception as rank_err:
    logger.debug(f"Could not update ranks from moral compass: {rank_err}")
    # Fallback to playground leaderboard method
    updated_stats = _compute_user_stats(username, token)
    moral_compass_state["team_rank"] = updated_stats.get("team_rank")
    moral_compass_state["individual_rank"] = updated_stats.get("rank")

# After: Keep last-known Moral Compass ranks
except Exception as rank_err:
    logger.warning(f"Could not update ranks from Moral Compass API: {rank_err}")
    # Keep last-known ranks instead of falling back to playground
    if DEBUG_LOG:
        _log(f"Keeping last-known Moral Compass ranks: individual=#{moral_compass_state.get('individual_rank')}, team=#{moral_compass_state.get('team_rank')}")
```

**Impact:** Eliminates confusion by using only one rank source (Moral Compass).

### 3. Improved Rank Computation (mc_integration_helpers.py)
**Location:** Lines 691-748

**Changes:**
- Separate individual users from team synthetic users (prefix: team:)
- Compute individual ranks only from individual users
- Compute team ranks only from team synthetic users
- Use moralCompassScore from API response directly

**Impact:** 
- Individual ranks no longer include team entries
- Team ranks properly reflect team aggregation
- Ranks based on moralCompassScore, not arbitrary totalCount

### 4. Better API Data Retrieval (mc_integration_helpers.py)
**Location:** Lines 637-688

**Changes:**
```python
# Before: Used iter_users which returned MoralcompassUserStats objects without moralCompassScore
users = list(api_client.iter_users(table_id))

# After: Use raw list_users API to get moralCompassScore directly
response = api_client.list_users(table_id, limit=100, last_key=last_key)
users = response.get("users", [])
for user_data in users:
    user_list.append({
        'username': user_data.get("username"),
        'moralCompassScore': user_data.get("moralCompassScore", user_data.get("totalCount", 0)),
        ...
    })
```

**Impact:** Direct access to moralCompassScore ensures correct rank computation.

### 5. Flexible Progress Configuration (challenge.py)
**Location:** Lines 221-237

**Changes:**
```python
# Before: Required all parameters, defaulted to 0
def set_progress(self, tasks_completed: int = 0, total_tasks: int = 0, ...)

# After: Optional parameters that preserve existing values
def set_progress(self, tasks_completed: Optional[int] = None, total_tasks: Optional[int] = None, ...)
    if tasks_completed is not None:
        self.tasks_completed = tasks_completed
    if total_tasks is not None:
        self.total_tasks = total_tasks
```

**Impact:** Allows overriding specific progress fields without resetting others.

## Testing

### Test Coverage
**Existing Tests (test_bias_detective_enhancements.py):**
- 9 tests covering duplicate task prevention, progress caps, HTML rendering
- All pass ✓

**New Integration Tests (test_bias_detective_rank_integration.py):**
1. `test_get_user_ranks_computes_from_moral_compass_score` - Verifies ranks use moralCompassScore
2. `test_get_user_ranks_updates_when_score_increases` - Verifies ranks change with score updates
3. `test_get_user_ranks_computes_team_rank` - Verifies team rank computation
4. `test_get_user_ranks_handles_missing_user` - Verifies graceful handling of missing users
5. `test_fetch_cached_users_uses_moral_compass_score` - Verifies API data extraction
6. `test_fetch_cached_users_handles_missing_moral_compass_score` - Verifies fallback behavior
7. `test_fetch_cached_users_caching` - Verifies cache functionality

**Results:** 16/16 tests pass ✓

### Running Tests
```bash
cd /home/runner/work/aimodelshare/aimodelshare
python -m pytest tests/test_bias_detective_enhancements.py tests/test_bias_detective_rank_integration.py -v
```

## Validation Checklist

### Code Review
- [x] Removed all playground fallback logic
- [x] ChallengeManager initialized with correct parameters
- [x] Individual and team ranks computed separately
- [x] moralCompassScore used for ranking
- [x] DEBUG_LOG support added
- [x] Error handling keeps last-known ranks
- [x] All tests pass

### Manual Validation (if possible)
When running the Bias Detective app:
1. Sign in with valid credentials
2. Complete some tasks
3. Check that ranks update after each correct answer
4. Verify ranks shown match Moral Compass score progression
5. Check checkpoint slides (10, 18) for rank refresh
6. Verify team ranks are shown if user is on a team

### Expected Behavior
- Individual rank should update as user completes tasks
- Team rank should update based on team's aggregated score
- No fallback to playground leaderboard should occur
- Temporary API failures should show last-known ranks with warning

## Key Behaviors

### Rank Computation Formula
```
moralCompassScore = accuracy × progress_ratio

where:
- accuracy = primary metric (set during initialization)
- progress_ratio = (tasks_completed + questions_correct) / (total_tasks + total_questions)
- For Bias Detective: progress_ratio = tasks_completed / 21
```

### Individual Rank
- Computed from all non-team users (username does NOT start with "team:")
- Sorted by moralCompassScore descending
- Position in sorted list = rank

### Team Rank
- Computed from team synthetic users only (username starts with "team:")
- Each team has one entry: `team:TeamName`
- Sorted by moralCompassScore descending
- Position in sorted list = team rank

## Files Modified
1. `aimodelshare/moral_compass/apps/bias_detective.py` - Main app logic
2. `aimodelshare/moral_compass/challenge.py` - ChallengeManager improvements
3. `aimodelshare/moral_compass/apps/mc_integration_helpers.py` - Rank computation
4. `tests/test_bias_detective_rank_integration.py` - New integration tests

## Compatibility
- Backward compatible with existing Moral Compass API
- Falls back to totalCount if moralCompassScore field is missing
- No breaking changes to ChallengeManager API
- Existing tests continue to pass

## Environment Variables
- `DEBUG_LOG=true` - Enable detailed logging of rank sources and updates
- `MORAL_COMPASS_TABLE_ID` - Explicit table ID (otherwise auto-derived)
- `PLAYGROUND_URL` - Used to derive table ID if explicit ID not provided

## Risks Mitigated
1. **API Unavailability:** Last-known ranks are kept instead of switching to playground
2. **Missing moralCompassScore:** Falls back to totalCount for backward compatibility
3. **Team Synthetic Users:** Properly excluded from individual rankings
4. **Cache Staleness:** TTL=5s for rank queries ensures fresh data

## Next Steps
1. Merge PR to master
2. Deploy to staging for manual validation
3. Monitor rank updates in production
4. Verify no playground fallback occurs in logs

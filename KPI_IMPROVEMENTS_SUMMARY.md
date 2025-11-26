# KPI Card and Change Detection Improvements - Implementation Summary

## Overview
This implementation addresses the issue where users were not seeing updated rank or accuracy diff (+/-) after submission, especially when the backend overwrites the latest row instead of appending.

## Changes Made

### 1. New Helper Function: `_get_user_latest_accuracy()`
**Location:** `aimodelshare/moral_compass/apps/model_building_game.py` (lines 850-889)

**Purpose:** Robustly extract a user's latest submission accuracy from the leaderboard.

**Implementation:**
- Uses timestamp sorting when available
- Falls back to last row (append order) if timestamps are missing/invalid
- Returns `None` for non-existent users or empty dataframes

**Key Code:**
```python
def _get_user_latest_accuracy(df: Optional[pd.DataFrame], username: str) -> Optional[float]:
    """Extract the user's latest submission accuracy from the leaderboard."""
    # Try timestamp-based sorting if available
    if "timestamp" in user_rows.columns:
        # Sort by timestamp and get latest
        latest_row = valid_ts.sort_values("__parsed_ts", ascending=False).iloc[0]
        return float(latest_row["accuracy"])
    # Fallback: assume last row is latest
    return float(user_rows.iloc[-1]["accuracy"])
```

### 2. Enhanced Change Detection: `_user_rows_changed()`
**Location:** `aimodelshare/moral_compass/apps/model_building_game.py` (lines 924-984)

**New Parameter:** `old_latest_score: Optional[float] = None`

**Enhanced Detection Logic:**
The function now detects changes via ANY of these conditions:
1. Row count increased (new submission appended)
2. Best score improved (>0.0001 epsilon)
3. Latest timestamp increased (when available)
4. **Latest accuracy changed (>=0.00001 epsilon)** - NEW! Handles overwrite case

**Key Code:**
```python
# Check latest accuracy change (handles overwrite-without-append case)
if old_latest_score is not None and new_latest_score is not None:
    accuracy_changed = abs(new_latest_score - old_latest_score) >= 0.00001
    if accuracy_changed:
        _log(f"Latest accuracy changed: {old_latest_score:.4f} -> {new_latest_score:.4f}")
    changed = changed or accuracy_changed
```

### 3. Provisional Diff Display: `_build_kpi_card_html()`
**Location:** `aimodelshare/moral_compass/apps/model_building_game.py` (lines 1131-1228)

**Pending State Enhancement:**
When `is_pending=True`, the KPI card now:
- Shows local test accuracy as the "new" score
- Computes diff vs `last_score` (from last submission)
- Displays `+X.XX (⬆️) (Provisional)` or `-X.XX (⬇️) (Provisional)` or `No Change (↔) (Provisional)`
- Keeps rank as "Pending" with "Calculating rank..." subtext

**Key Code:**
```python
if is_pending:
    # Compute provisional diff between local (new) and last score
    if local_test_accuracy is not None and last_score is not None and last_score > 0:
        score_diff = local_test_accuracy - last_score
        if abs(score_diff) < 0.0001:
            acc_diff_html = "<p ...>No Change (↔) <span>(Provisional)</span></p>..."
        elif score_diff > 0:
            acc_diff_html = f"<p ...>+{(score_diff * 100):.2f} (⬆️) <span>(Provisional)</span></p>..."
        else:
            acc_diff_html = f"<p ...>{(score_diff * 100):.2f} (⬇️) <span>(Provisional)</span></p>..."
```

### 4. Integration in `run_experiment()`
**Location:** `aimodelshare/moral_compass/apps/model_building_game.py` (lines 2277-2320)

**Baseline Extraction:**
Before polling, extract `old_latest_score`:
```python
if full_leaderboard_df is not None and not full_leaderboard_df.empty:
    # ... existing code ...
    old_latest_score = _get_user_latest_accuracy(full_leaderboard_df, username)
else:
    # ... existing code ...
    old_latest_score = None
```

**Pass to Change Detection:**
```python
if _user_rows_changed(refreshed, username, old_row_count, old_best_score, old_latest_ts, old_latest_score):
    # ...
```

**Pending KPI Card:**
```python
pending_kpi_html = _build_kpi_card_html(
    new_score=local_test_accuracy,  # Use local score as "new"
    last_score=last_submission_score,  # Compare against last submission
    new_rank=0,
    last_rank=0,
    submission_count=0,
    is_preview=False,
    is_pending=True,
    local_test_accuracy=local_test_accuracy
)
```

## Testing

### New Unit Tests
**File:** `tests/test_kpi_improvements.py`

**Coverage:** 13 tests, all passing
1. `test_get_user_latest_accuracy_with_timestamps` - Timestamp sorting
2. `test_get_user_latest_accuracy_without_timestamps` - Fallback to last row
3. `test_get_user_latest_accuracy_no_user` - Non-existent user
4. `test_get_user_latest_accuracy_empty_df` - Empty dataframe
5. `test_user_rows_changed_by_latest_accuracy` - Overwrite detection
6. `test_user_rows_changed_no_change` - No change case
7. `test_user_rows_changed_by_count` - Row count increase
8. `test_user_rows_changed_by_best_score` - Best score improvement
9. `test_build_kpi_card_pending_with_provisional_diff_increase` - Pending increase
10. `test_build_kpi_card_pending_with_provisional_diff_decrease` - Pending decrease
11. `test_build_kpi_card_pending_with_provisional_diff_no_change` - Pending no change
12. `test_build_kpi_card_pending_no_last_score` - Pending without last score
13. `test_build_kpi_card_success_shows_diff` - Success card (non-provisional)

### Existing Tests
All existing moral compass unit tests continue to pass (16/16 passed).

## Acceptance Criteria Met

✅ **After submission, users see:**
- Accuracy updated immediately (already working)
- A visible +/- diff (or "No Change ↔") computed from local_test_accuracy vs last_submission_score, even while Pending
- Rank remains "Pending" until leaderboard reflects the submission; once detected, full rank and accurate diffs show

✅ **Change detection flips to "updated" when:**
- Backend overwrites the latest row (same count, same best), but the latest accuracy changed

✅ **Existing tests continue to pass**

✅ **CI pytest remains verbose** (existing behavior preserved)

## Visual Examples

### Pending State - Score Increase
```html
⏳ Submission Processing
New Accuracy: 80.00%
+5.00 (⬆️) (Provisional)
Pending leaderboard update...

Your Rank: Pending
Calculating rank...
```

### Pending State - Score Decrease
```html
⏳ Submission Processing
New Accuracy: 72.00%
-3.00 (⬇️) (Provisional)
Pending leaderboard update...

Your Rank: Pending
Calculating rank...
```

### Success State (After Detection)
```html
✅ Submission Successful!
New Accuracy: 80.00%
+5.00 (⬆️)

Your Rank: #5
🚀 Moved up 2 spots!
```

## Benefits

1. **Better UX:** Users immediately see if their score improved/decreased, even before leaderboard updates
2. **Reduced Confusion:** Clear "(Provisional)" annotation sets expectations
3. **Robust Detection:** Handles backend overwrite scenarios that previously got stuck in "Pending"
4. **Backward Compatible:** Existing success/preview flows unchanged, only pending state enhanced

## Files Changed
- `aimodelshare/moral_compass/apps/model_building_game.py` (378 lines changed, 38 additions)
- `tests/test_kpi_improvements.py` (316 lines added, new file)

## Dependencies
No new dependencies added. All changes use existing libraries (pandas, numpy).

# Bias Detective Task Tracking Integration

## Overview

This document describes the implementation of Moral Compass task tracking and score initialization based on `completedTaskIds` in the Bias Detective app.

## Changes Made

### 1. Score Initialization Based on completedTaskIds

**File:** `aimodelshare/moral_compass/apps/bias_detective.py`

#### Modified Functions:

##### `get_leaderboard_data(client, username, team_name)`
- **Change:** Now extracts and returns `completedTaskIds` from user records in the leaderboard
- **Behavior:** 
  - Retrieves `completedTaskIds` from user data if present
  - Defaults to empty list `[]` if not present or user not found
  - Returns the list as part of the data dictionary with key `completed_task_ids`

##### `render_top_dashboard(data, module_id)`
- **Change:** Shows score as 0 when `completedTaskIds` is empty
- **Behavior:**
  - Checks if `completed_task_ids` field exists and has values
  - If empty or missing, displays `0.000` instead of the actual score
  - Once at least one task is completed, displays the actual score
  - This ensures users see 0 until they complete their first task (Module 0 quiz)

### 2. Task Completion Tracking

##### `trigger_api_update(username, token, team_name, module_id, append_task_id=None, increment_question=False)`
- **New Parameters:**
  - `append_task_id`: Optional task ID to append to completedTaskIds (e.g., "t1")
  - `increment_question`: Boolean flag to increment questions_correct counter
  
- **Behavior:**
  - Retrieves current `completedTaskIds` from previous leaderboard data
  - Appends new task ID if provided and not already present
  - Sorts task IDs numerically (t1, t2, t3, ... not alphabetically)
  - Calculates `tasks_completed` based on length of task IDs when appending
  - Calculates `questions_correct` based on length of task IDs when `increment_question=True`
  - Passes `completed_task_ids` to `update_moral_compass` API call

### 3. Quiz Answer Validation

##### `submit_quiz_0(username, token, team_name, module0_done, answer)`
- **Change:** Only updates backend when answer is correct
- **Behavior:**
  - When answer matches `CORRECT_ANSWER_0`:
    - Calls `trigger_api_update` with `append_task_id="t1"` and `increment_question=True`
    - This appends "t1" to completedTaskIds
    - Increments tasks_completed by 1
    - Increments questions_correct by 1
  - When answer is incorrect:
    - Returns feedback message
    - Does NOT call `trigger_api_update`
    - No backend state changes

### 4. Navigation Without Score Updates

##### `on_next_from_module_0(username, token, team, answer)`
- **Change:** Navigation no longer updates scores
- **Behavior:**
  - Removed call to `trigger_api_update(module_id=1)`
  - Now only calls `ensure_table_and_get_data` to refresh display
  - Updates UI visibility and module state
  - Refreshes leaderboard without modifying backend data

## API Integration

### MoralcompassApiClient.update_moral_compass

The function now uses the following parameters when a correct answer is submitted:

```python
client.update_moral_compass(
    table_id="m-mc",
    username=username,
    team_name=team_name,
    metrics={"accuracy": 0.60},  # From MODULES[0]["sim_acc"]
    tasks_completed=1,  # Length of completedTaskIds
    total_tasks=10,
    questions_correct=1,  # Length of completedTaskIds when incrementing
    total_questions=1,  # At least 1 when we have questions
    primary_metric="accuracy",
    completed_task_ids=["t1"]  # Newly appended task ID
)
```

## User Flow

### Initial Load
1. User accesses app with valid session ID
2. App authenticates via `handle_initial_load`
3. `get_leaderboard_data` retrieves user data including `completedTaskIds`
4. If `completedTaskIds` is empty, `render_top_dashboard` shows score as 0.000
5. User sees initial state with 0 Moral Compass score

### First Correct Answer (Module 0 Quiz)
1. User selects correct answer: "A) Because simple accuracy ignores potential bias and harm."
2. `submit_quiz_0` validates the answer
3. `trigger_api_update` is called with:
   - `append_task_id="t1"`
   - `increment_question=True`
4. Backend updates with:
   - `completedTaskIds: ["t1"]`
   - `tasks_completed: 1`
   - `questions_correct: 1`
   - New moral compass score calculated
5. Dashboard refreshes showing updated score and rank

### Navigation After Correct Answer
1. User clicks "Next" button
2. `on_next_from_module_0` is called
3. Function only refreshes leaderboard data (no backend update)
4. UI transitions to Module 1
5. Dashboard continues showing current score (not incremented)

### Incorrect Answer
1. User selects incorrect answer
2. `submit_quiz_0` returns feedback message
3. No backend API call is made
4. Score remains unchanged
5. User can try again

## Error Handling

All functions gracefully handle missing or malformed data:

- Missing `completedTaskIds` field defaults to empty list `[]`
- Missing user data defaults to score 0, empty task list
- Failed API calls are logged but don't crash the app
- Team assignment falls back to "team-a" if retrieval fails

## Testing

### New Test File: `tests/test_bias_detective_task_tracking.py`

Comprehensive test suite covering:
- ✅ `completedTaskIds` extraction from leaderboard
- ✅ Handling missing `completedTaskIds` gracefully  
- ✅ Score display showing 0 when no tasks completed
- ✅ Score display showing actual value when tasks completed
- ✅ Task ID appending in `trigger_api_update`
- ✅ Appending to existing task IDs
- ✅ Navigation without task ID updates
- ✅ Correct quiz answer appends "t1"
- ✅ Incorrect quiz answer does not update backend

All tests pass ✓

## Backward Compatibility

- All changes are backward compatible
- `completedTaskIds` is optional in API responses
- Functions handle missing fields gracefully
- Existing functionality preserved for users without task IDs
- Team assignment logic remains intact

## Security Considerations

- No sensitive data exposed in completedTaskIds
- Authentication requirements unchanged
- Session-based auth still required
- API token handling unchanged
- No new security vulnerabilities introduced

## Future Enhancements

Potential improvements for future iterations:

1. Track individual task IDs for each module (t1-t10)
2. Add task ID validation (ensure format matches t\d+)
3. Support task ID reset for testing/debugging
4. Add admin interface to view/modify user task progress
5. Implement task ID-based progress visualization

## Summary

This implementation successfully integrates Moral Compass task tracking with the Bias Detective app, ensuring:

- ✅ Score shows 0 until first task is completed
- ✅ Correct answers update `completedTaskIds` with "t1"
- ✅ Navigation does not modify backend state
- ✅ Leaderboard reflects changes only after correct submission
- ✅ Robust error handling for missing data
- ✅ Comprehensive test coverage
- ✅ Backward compatible with existing code

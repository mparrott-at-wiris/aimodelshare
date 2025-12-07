# Unified Task ID Tracking for Moral Compass - Implementation Summary

## Overview
This implementation adds unified tracking of completed tasks and questions for the Moral Compass system using a single `completedTaskIds` list of strings labeled t1, t2, …, tn where n = totalTasks + totalQuestions.

## Key Features

### 1. Server-Side Changes (infra/lambda/app.py)

#### New Validation
- Added `_TASK_ID_RE` regex pattern to validate task IDs (^t\d+$)
- Added `validate_task_ids()` function to validate lists of task IDs

#### Enhanced PUT Endpoint
- `PUT /tables/{tableId}/users/{username}/moral-compass` now accepts optional `completedTaskIds` field
- Validates each ID matches the t\d+ pattern
- Stores completedTaskIds in DynamoDB alongside existing fields
- Returns completedTaskIds in the response when present
- Fully backward compatible - field is optional

#### Enhanced GET Endpoint
- `GET /tables/{tableId}/users/{username}` includes completedTaskIds in response if present
- Maintains backward compatibility for clients not expecting this field

#### New Task Management Endpoints
1. **PATCH /tables/{tableId}/users/{username}/tasks**
   - Supports three operations via `op` field:
     - `add`: Union existing IDs with provided IDs (deduplicates)
     - `remove`: Subtract provided IDs from existing IDs
     - `reset`: Replace with provided IDs
   - Validates all IDs match t\d+ pattern
   - Returns updated completedTaskIds sorted numerically
   - Same authorization as moral compass updates (self or admin)

2. **DELETE /tables/{tableId}/users/{username}/tasks**
   - Clears the completedTaskIds list (sets to empty array)
   - Same authorization as moral compass updates (self or admin)

#### Routing
- Both HTTP API and REST API paths supported for all new endpoints
- Maintains existing routing patterns and conventions

#### Data Consistency
- All operations produce deterministically sorted results
- IDs sorted numerically (t1, t2, t3, t10, t20, not alphabetically)
- Uses retry_dynamo for all DynamoDB operations
- Maintains consistent read flags

### 2. Client-Side Changes (aimodelshare/moral_compass/api_client.py)

#### Enhanced Data Model
- Updated `MoralcompassUserStats` dataclass with optional `completed_task_ids` field
- Backward compatible - defaults to None if not provided

#### Enhanced update_moral_compass()
- Added optional `completed_task_ids` parameter
- Includes completedTaskIds in payload when provided
- Returns completedTaskIds in response

#### New Helper Methods
```python
def add_tasks(table_id, username, task_ids) -> Dict[str, Any]
def remove_tasks(table_id, username, task_ids) -> Dict[str, Any]
def reset_tasks(table_id, username, task_ids=None) -> Dict[str, Any]
def clear_tasks(table_id, username) -> Dict[str, Any]
```
All methods:
- Use existing authentication and retry mechanisms
- Make requests to PATCH or DELETE endpoints
- Return updated completedTaskIds from server

#### Enhanced get_user()
- Populates `completed_task_ids` field in MoralcompassUserStats when present
- Backward compatible - handles absence of field gracefully

### 3. ChallengeManager Changes (aimodelshare/moral_compass/challenge.py)

#### New Mapping Function
- `_build_completed_task_ids()` creates unified list from local state
- Mapping scheme:
  - Tasks map to t1..tTotalTasks by their index in challenge.tasks
  - Questions map to tTotalTasks+1..tN by their index across all tasks
- Deterministic ordering based on challenge structure
- Results sorted numerically for consistency

#### Enhanced sync()
- Automatically builds and passes `completed_task_ids` to update_moral_compass
- Includes all local progress in unified format
- Maintains existing behavior for all other fields

## Data Flow Example

```
ChallengeManager (Local State)
  ├─ Tasks completed: [A, B, C]
  └─ Questions answered: [A1, B1]
         ↓
  _build_completed_task_ids()
         ↓
  ['t1', 't2', 't3', 't7', 't8']
         ↓
  sync() → api_client.update_moral_compass(completed_task_ids=[...])
         ↓
  Lambda API → DynamoDB storage
         ↓
  Response includes completedTaskIds
```

## Backward Compatibility

All changes are fully backward compatible:
- `completedTaskIds` is optional everywhere
- Existing clients work without any changes
- Moral compass score calculation unchanged
- All existing endpoints continue to function identically
- No breaking changes to data structures

## Security & Authorization

- All new endpoints honor `AUTH_ENABLED` configuration
- Self-or-admin authorization pattern maintained
- Same identity extraction and validation as existing endpoints
- No changes to JWT decoding or admin handling

## Testing

Comprehensive testing performed:
1. Unit tests for validation logic
2. Tests for all PATCH operations (add/remove/reset)
3. Tests for DELETE operation
4. Tests for ChallengeManager mapping
5. Integration tests for complete workflow
6. Backward compatibility tests
7. CodeQL security scan (0 alerts)

## ID Mapping Details

For a challenge with 6 tasks and 6 questions:
- t1-t6: Tasks A-F (by index order)
- t7-t12: Questions A1, B1, C1, D1, E1, F1 (by sequential order)

Example:
```
Tasks:     [A, B, C, D, E, F]
Indexes:   [0, 1, 2, 3, 4, 5]
Map to:    [t1,t2,t3,t4,t5,t6]

Questions: [A1, B1, C1, D1, E1, F1]
Offset:    6 (total_tasks)
Map to:    [t7, t8, t9, t10,t11,t12]
```

## Performance Considerations

- No additional API calls required
- Minimal overhead in payload size
- Sorting is O(n log n) where n is number of completed items
- DynamoDB operations use existing retry and consistency patterns
- No impact on moral compass score calculation

## Future Enhancements

Potential future improvements could include:
- Bulk operations endpoint
- Query endpoint to filter users by specific task completion
- Analytics on task completion patterns
- Task completion history with timestamps

# Bias Detective Test Mode Documentation

## Overview

This document describes the test mode functionality added to the Bias Detective app. Test mode enables detailed debugging and tracking of the completedTaskIds lifecycle, user scores, ranks, and team ranks throughout user interactions.

## Purpose

The test mode was implemented to:
1. Surface server-side debugging information in the front-end
2. Print detailed server logs for key interactions
3. Track completedTaskIds reads/writes throughout the user journey
4. Display score deltas, rank changes, and before/after states
5. Aid in development, testing, and troubleshooting

## Usage

### Launching with Test Mode

```python
from aimodelshare.moral_compass.apps.bias_detective import launch_bias_detective_app

# Launch with test mode enabled
launch_bias_detective_app(
    share=False,
    server_name="0.0.0.0",
    server_port=8080,
    test_mode=True  # Enable test mode
)
```

### Creating App with Test Mode

```python
from aimodelshare.moral_compass.apps.bias_detective import create_bias_detective_app

# Create app instance with test mode
app = create_bias_detective_app(
    theme_primary_hue="indigo",
    test_mode=True  # Enable test mode
)
```

## Features

### 1. Debug Panel (Front-End)

When test mode is enabled, a debug panel appears at the bottom of the app showing:

#### Initial Load
- **Score**: Current moral compass score
- **Global_Rank**: User's global rank
- **Team_Rank**: User's team rank
- **Completed_Task_IDs**: List of completed task IDs (e.g., ["t1", "t2", "t3"])

#### Quiz Submissions (Modules 0, 1, 2)
- **Context**: "Module N Quiz Submission"
- **Prev_Task_IDs**: Task IDs before quiz submission
- **New_Task_IDs**: Task IDs after quiz submission
- **Delta_Score**: Score increase (e.g., "+0.060")
- **Prev_Rank**: Rank before submission
- **Curr_Rank**: Rank after submission
- **Rank_Diff**: Rank change (e.g., "Up 5 spots!", "No change")
- **Score**: Current score after update
- **Global_Rank**: Current global rank
- **Team_Rank**: Current team rank

#### Navigation Between Modules
- **Context**: "Navigation to Module N"
- **Score**: Current score
- **Global_Rank**: Current global rank
- **Team_Rank**: Current team rank
- **Completed_Task_IDs**: Current list of completed tasks

### 2. Server-Side Logging

When test mode is enabled, the server prints detailed logs for:

#### Initial Load
```
================================================================================
DEBUG: Initial Load
Username: test-user
Team: team-alpha
Data: {'score': 0.0, 'rank': 10, 'team_rank': 3, 'completed_task_ids': []}
================================================================================
```

#### Quiz Submissions
```
================================================================================
DEBUG: Module 0 Quiz Submission
Previous data: {'score': 0.0, 'rank': 10, 'team_rank': 3, 'completed_task_ids': []}
Current data: {'score': 0.06, 'rank': 5, 'team_rank': 2, 'completed_task_ids': ['t1']}
Previous task IDs: []
New task IDs: ['t1']
================================================================================
```

#### Navigation
```
================================================================================
DEBUG: Navigation to Module 1
Data: {'score': 0.06, 'rank': 5, 'team_rank': 2, 'completed_task_ids': ['t1']}
================================================================================
```

## Implementation Details

### Core Functions Modified

1. **`render_debug(context_label, **kwargs)`**
   - New function that generates debug HTML panel
   - Takes a context label and key-value pairs
   - Returns formatted HTML with debug information

2. **`trigger_api_update(...)`**
   - Now returns 5 values instead of 3:
     - `prev_data`: Previous leaderboard data
     - `curr_data`: Current leaderboard data
     - `username`: Username
     - `prev_task_ids`: Task IDs before update (NEW)
     - `new_task_ids`: Task IDs after update (NEW)
   - Prevents duplicate task IDs from being appended

3. **`submit_quiz_0/1/justice(..., test_mode=False)`**
   - All quiz submission functions now accept `test_mode` parameter
   - When True, they:
     - Print server-side debug logs
     - Generate debug HTML panel
     - Include debug_html in return values

4. **`handle_initial_load(request)`**
   - Prints initial load data when test_mode is True
   - Generates debug panel with initial user state

5. **`on_next_from_module_*(...)`**
   - Navigation handlers updated to include debug output
   - Print navigation logs when test_mode is True
   - Return debug HTML in outputs when test_mode is True

### UI Components

- **`debug_html`**: gr.HTML component
  - Visible when test_mode is True
  - Hidden when test_mode is False
  - Displays debug panel at bottom of app
  - Updates on every interaction

### Duplicate Prevention

The implementation ensures no duplicate task IDs are appended:

```python
# In trigger_api_update
new_task_ids = list(current_task_ids)  # Make a copy
if append_task_id and append_task_id not in new_task_ids:
    new_task_ids.append(append_task_id)
    # Sort numerically
    new_task_ids.sort(key=lambda x: int(x[1:]) if x.startswith('t') and x[1:].isdigit() else 0)
```

## Testing

### Unit Tests

Comprehensive unit tests are provided in `tests/test_bias_detective_test_mode.py`:

1. `test_render_debug_generates_html` - Verifies debug HTML generation
2. `test_trigger_api_update_returns_task_ids` - Verifies 5 return values
3. `test_trigger_api_update_prevents_duplicate_task_ids` - Verifies no duplicates
4. `test_submit_quiz_0_with_test_mode` - Verifies quiz 0 test mode
5. `test_submit_quiz_1_with_test_mode` - Verifies quiz 1 test mode
6. `test_submit_quiz_justice_with_test_mode` - Verifies quiz 2 test mode
7. `test_create_bias_detective_app_with_test_mode` - Verifies parameter acceptance
8. `test_launch_bias_detective_app_accepts_test_mode` - Verifies launch parameter

All tests pass successfully.

### Manual Testing

A manual test script is provided: `test_bias_detective_with_session.py`

To run:
```bash
python test_bias_detective_with_session.py
```

Then access the app at:
```
http://127.0.0.1:8080/?sessionid=<your-session-id>
```

## Example Debug Panel Output

### Initial Load
```html
🐛 DEBUG: Initial Load
┌─────────────────────────┬─────────┐
│ Score                   │ 0       │
│ Global_Rank             │ 0       │
│ Team_Rank               │ 0       │
│ Completed_Task_IDs      │ []      │
└─────────────────────────┴─────────┘
```

### After Module 0 Quiz (Correct Answer)
```html
🐛 DEBUG: Module 0 Quiz Submission
┌─────────────────────────┬──────────────┐
│ Prev_Task_IDs           │ []           │
│ New_Task_IDs            │ ['t1']       │
│ Delta_Score             │ +0.060       │
│ Prev_Rank               │ 10           │
│ Curr_Rank               │ 5            │
│ Rank_Diff               │ Up 5 spots!  │
│ Score                   │ 0.06         │
│ Global_Rank             │ 5            │
│ Team_Rank               │ 2            │
└─────────────────────────┴──────────────┘
```

## Backward Compatibility

- Test mode is **disabled by default** (`test_mode=False`)
- When disabled, the app behaves exactly as before
- No changes to existing functionality
- All existing tests updated to handle new return signature
- Debug panel is completely hidden when test_mode=False

## Performance Considerations

- Debug logging only occurs when test_mode=True
- No performance impact when test_mode=False
- Debug HTML generation is minimal overhead
- Server logs use Python's built-in print (can be redirected to logging framework)

## Security Considerations

- Test mode should **NOT** be enabled in production
- Debug information may contain sensitive user data
- Server logs may expose internal state
- Use only in development/testing environments

## Future Enhancements

Potential improvements:
1. Add logging levels (DEBUG, INFO, WARNING, ERROR)
2. Export debug logs to file
3. Add filtering options for debug panel
4. Include API response times in debug output
5. Add visual diff view for before/after states
6. Track full user journey timeline

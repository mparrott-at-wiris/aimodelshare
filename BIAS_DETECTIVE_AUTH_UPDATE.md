# Bias Detective App Authentication Update

## Overview

The bias detective app has been updated to use automatic session-based authentication from Gradio request query parameters, matching the authentication pattern used by the judge app and other moral compass applications.

## Changes Summary

### Before (Manual Authentication)

1. **Login Form Visible**: Users saw input boxes for:
   - Session ID (password field)
   - Team selection (dropdown with team-a, team-b, team-c)
   - "Start Course" button

2. **Authentication Flow**:
   ```
   User visits app
   → Sees login form
   → Manually enters session ID
   → Selects team from dropdown
   → Clicks "Start Course"
   → validate_auth() called with session_id
   → App loads with credentials
   ```

3. **State Management**:
   - `session_state`: Stored the session ID
   - `team_state`: Stored the selected team
   - Both passed through all event handlers

### After (Automatic Authentication)

1. **No Login Form**: Users immediately see Module 0 content

2. **Authentication Flow**:
   ```
   User visits app with ?sessionid=XXX in URL
   → demo.load() triggers automatically
   → _try_session_based_auth() extracts sessionid from request.query_params
   → get_token_from_session() validates and returns token
   → _get_username_from_token() extracts username
   → get_or_assign_team() fetches team from leaderboard
   → App loads with credentials populated in state
   ```

3. **State Management**:
   - `username_state`: Stores the authenticated username
   - `token_state`: Stores the authentication token
   - `team_state`: Stores the user's team (from leaderboard or default)
   - All passed through event handlers

## Technical Details

### New Functions Added

#### `_try_session_based_auth(request: gr.Request)`
```python
def _try_session_based_auth(request: "gr.Request") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Attempt to authenticate via session token from Gradio request.
    Returns (success, username, token).
    """
    # Extracts sessionid from request.query_params
    # Returns (True, username, token) on success
    # Returns (False, None, None) on failure
```

#### `get_or_assign_team(client, username)`
```python
def get_or_assign_team(client, username):
    """
    Get user's existing team from leaderboard or assign a default team.
    Returns team_name string.
    """
    # Looks up user in leaderboard
    # Returns existing team if found
    # Returns "team-a" as default if not found
```

#### `handle_initial_load(request: gr.Request)`
```python
def handle_initial_load(request: gr.Request):
    """
    Authenticate via session token on page load.
    """
    # Called automatically by demo.load()
    # Authenticates user and initializes state
    # Returns updated state values for all components
```

### Modified Functions

#### Function Signature Changes

**Before:**
```python
def ensure_table_and_get_data(session_id, team_name)
def trigger_api_update(session_id, team_name, module_id)
def submit_quiz_0(session_id, team_name, module0_done, answer)
```

**After:**
```python
def ensure_table_and_get_data(username, token, team_name)
def trigger_api_update(username, token, team_name, module_id)
def submit_quiz_0(username, token, team_name, module0_done, answer)
```

**Rationale**: Functions now receive username and token directly instead of session_id, avoiding repeated session validation.

### Removed Components

1. **Login Row UI**:
   - Removed `gr.Row(visible=True) as login_row`
   - Removed session ID text input
   - Removed team dropdown
   - Removed "Start Course" button
   - Removed `on_start()` handler

2. **Module 0 Visibility**: Changed from `visible=False` to `visible=True` since auth is automatic

## Security Improvements

1. **Reduced Logging of Sensitive Data**:
   - Exception details no longer logged in `_try_session_based_auth()`
   - Generic error message logged instead

2. **Token Validation**:
   - Session tokens validated using existing AWS authentication functions
   - No tokens or session IDs exposed in UI or logs

## Compatibility

### URL Format
The app expects a session ID to be passed via URL query parameter:
```
https://app-url/?sessionid=USER_SESSION_ID
```

This matches the pattern used by:
- Judge app (`judge.py`)
- Ethical Revelation app (`ethical_revelation.py`)
- Model Building Game app (`model_building_game.py`)

### Team Assignment
- Teams are now fetched from the leaderboard via `get_or_assign_team()`
- If user has no existing team, defaults to "team-a"
- Team assignments persist across sessions via leaderboard

## Testing

### New Tests Added (`test_bias_detective_auth.py`)

1. `test_try_session_based_auth_with_valid_session`: Validates authentication with valid session
2. `test_try_session_based_auth_without_session`: Validates failure without session
3. `test_try_session_based_auth_with_invalid_token`: Validates failure with invalid token
4. `test_create_bias_detective_app_structure`: Validates app structure
5. `test_app_has_demo_load_handler`: Validates load handler exists
6. `test_handle_initial_load_with_mock_auth`: Validates initial load logic

### Test Results
- ✅ All 6 new authentication tests pass
- ✅ 7 out of 9 existing bias detective tests pass
- ⚠️ 2 pre-existing test failures (unrelated to authentication changes)

### CodeQL Security Scan
- ✅ No security vulnerabilities detected

## Migration Guide

### For Developers

If you have code that calls bias detective functions, update function calls:

**Before:**
```python
data, username = ensure_table_and_get_data(session_id, team_name)
trigger_api_update(session_id, team_name, module_id=0)
```

**After:**
```python
data, username = ensure_table_and_get_data(username, token, team_name)
trigger_api_update(username, token, team_name, module_id=0)
```

### For Users

No action required. Users will experience:
- Faster app loading (no manual login step)
- Seamless authentication when accessing via proper URL with session ID
- Same functionality once authenticated

## Rollback Plan

If issues arise, the previous version can be restored by reverting commits:
```bash
git revert f002b04  # Address code review feedback
git revert d7a8934  # Add comprehensive tests
git revert c7063c4  # Fix theme parameter
git revert ee81c49  # Update authentication
```

## Future Enhancements

Potential improvements for future consideration:

1. **Enhanced Team Management**:
   - Allow users to switch teams
   - Implement team balancing logic
   - Add team creation/joining UI

2. **Session Management**:
   - Add session expiration handling
   - Implement token refresh logic
   - Add logout functionality

3. **Error Handling**:
   - Better error messages for authentication failures
   - Graceful degradation when API is unavailable
   - Retry logic for transient failures

## References

- Judge app implementation: `aimodelshare/moral_compass/apps/judge.py`
- Model Building Game implementation: `aimodelshare/moral_compass/apps/model_building_game.py`
- Ethical Revelation implementation: `aimodelshare/moral_compass/apps/ethical_revelation.py`
- Test implementation: `tests/test_session_auto_login.py`

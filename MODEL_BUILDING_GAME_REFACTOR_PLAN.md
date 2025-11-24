# Model Building Game Refactoring Plan

## Status: Phase 2 Complete (Session Auth Infrastructure)

### What Was Accomplished

#### Phase 1 ✅ Complete  
- **File Deduplication:** 6200 → 3661 lines (41% reduction)
- Removed duplicate `create_model_building_game_app()` function
- Removed duplicate helper functions
- Single source of truth for all functions

#### Phase 2 ✅ Complete
- **Session-Based Authentication Infrastructure**
  - `_try_session_based_auth(request)` → (success, username, token)
  - NO os.environ mutation for credentials
  - Reads `?sessionid=` from URL query parameters
  
- **Leaderboard & Stats Caching**
  - `_fetch_leaderboard(token)` with TTL caching (45s default)
  - `_user_stats_cache` with per-user caching
  - Thread-safe via `_cache_lock`
  - Configurable via env vars
  
- **Team Assignment Logic**
  - `_get_or_assign_team(username, leaderboard_df)`
  - Timestamp-based team recovery
  - Normalized team names
  
- **User Stats Computation**
  - `_compute_user_stats(username, token)` with caching
  - Returns best_score, rank, team_name, submission_count
  
- **Attempt Limit Checking**
  - `check_attempt_limit(count, limit)` helper
  
- **Fairness Metrics Stub**
  - Commented `compute_fairness_metrics()` ready for implementation

---

## Phase 3: UI Integration & State Management

**Current Commit:** 0d9e245

### Remaining Tasks

Find where state objects are created (around line ~2780) and add:

```python
# Add these BEFORE team_name_state
username_state = gr.State(None)
token_state = gr.State(None)

team_name_state = gr.State(os.environ.get("TEAM_NAME"))
# ... existing states ...
```

### Step 4: Update submit_button.click

Find the submit_button.click handler and add username/token to inputs:

```python
submit_button.click(
    fn=run_experiment,
    inputs=[
        model_type_state,
        complexity_state,
        feature_set_state,
        data_size_state,
        team_name_state,
        last_submission_score_state,
        last_rank_state,
        submission_count_state,
        first_submission_score_state,
        best_score_state,
        username_state,  # NEW
        token_state,     # NEW
    ],
    outputs=all_outputs,
    show_progress="full"
)
```

### Step 5: Implement Session Auth on Load

Find `demo.load` (search for it in create function) and replace with:

```python
def handle_session_auth_on_load(request: "gr.Request"):
    """Check for session, load stats if authenticated."""
    success, username, token = _try_session_based_auth(request)
    
    if success and username and token:
        # Get stats and team
        stats = _compute_user_stats(username, token)
        team_name = stats.get("team_name", "")
        
        # Load UI with stats
        initial_ui = on_initial_load(username)
        
        # Hide login form (user is authenticated)
        return initial_ui + (
            username,  # username_state
            token,     # token_state
            team_name, # team_name_state  
            gr.update(visible=False),  # login_username
            gr.update(visible=False),  # login_password
            gr.update(visible=False),  # login_submit
            gr.update(visible=False),  # login_error
        )
    else:
        # No session - show login form
        initial_ui = on_initial_load(None)
        return initial_ui + (
            None,  # username_state
            None,  # token_state
            "",    # team_name_state
            gr.update(visible=True),   # login_username
            gr.update(visible=True),   # login_password
            gr.update(visible=True),   # login_submit
            gr.update(visible=False),  # login_error
        )

demo.load(
    fn=handle_session_auth_on_load,
    inputs=None,
    outputs=[
        model_card_display,
        team_leaderboard_display,
        individual_leaderboard_display,
        rank_message_display,
        model_type_radio,
        complexity_slider,
        feature_set_checkbox,
        data_size_radio,
        username_state,  # NEW
        token_state,     # NEW
        team_name_state, # NEW
        login_username,
        login_password,
        login_submit,
        login_error,
    ]
)
```

### Step 6: Update Preview Mode

In `run_experiment`, find the preview mode section (around line ~1360) and update the KPI card:

```python
if not ready_for_submission and flags["warm_mini"] and X_TRAIN_WARM is not None:
    # ... existing preview code ...
    
    # Check if user has session
    has_session = username and username != "Unknown_User" and token
    
    if has_session:
        # Normal preview with KPI
        preview_html = _build_kpi_card_html(preview_score, 0, 0, 0, -1, is_preview=True)
    else:
        # Session required variant
        preview_html = f"""
        <div class='kpi-card kpi-card--session-required'>
            <h2>🔬 Preview Run Complete!</h2>
            <div class='kpi-card-body'>
                <div class='kpi-metric-box'>
                    <p class='kpi-label'>Preview Accuracy</p>
                    <p class='kpi-score'>{(preview_score * 100):.2f}%</p>
                </div>
                <div class='kpi-metric-box'>
                    <p class='kpi-label'>Session Required</p>
                    <p>Sign in to submit and rank</p>
                    <p><a href='https://www.modelshare.ai/login' target='_blank'>Create Account</a></p>
                </div>
            </div>
        </div>
        """
```

### Step 7: Remove perform_inline_login (Optional)

If keeping inline login as fallback is acceptable, update `perform_inline_login` to:
- Call `_get_or_assign_team` with leaderboard from `_fetch_leaderboard`
- Return token in team_name_state → change to token_state

If removing completely:
1. Delete `perform_inline_login` function
2. Remove login_submit.click handler
3. Login UI only shows when no session (handled in Step 5)

### Step 8: Remove Old Functions

Delete duplicate/obsolete functions:
- Old `get_or_assign_team` (replaced by `_get_or_assign_team`)
- Old `_try_session_based_auth` that mutates os.environ

### Step 9: Add Fairness Metrics Stub

Add at end of helpers section (before create function):

```python
# -------------------------------------------------------------------------
# Future: Fairness Metrics
# -------------------------------------------------------------------------

# def compute_fairness_metrics(y_true, y_pred, sensitive_attrs):
#     """
#     Compute fairness metrics for model predictions.
#     
#     Args:
#         y_true: Ground truth labels
#         y_pred: Model predictions
#         sensitive_attrs: DataFrame with sensitive attributes (race, sex, age)
#     
#     Returns:
#         dict: Fairness metrics including demographic parity, equalized odds
#     
#     TODO: Implement using fairlearn or aif360
#     """
#     pass
```

---

## Phase 3: Testing & Validation

### Unit Tests
1. Test `_fetch_leaderboard` caching (mock time.time)
2. Test `_get_or_assign_team` timestamp sorting
3. Test `_try_session_based_auth` with/without sessionid
4. Test `check_attempt_limit` boundary conditions

### Integration Tests  
1. Load app with ?sessionid=valid → auto-login
2. Load app without sessionid → show login form
3. Submit with session → leaderboard updates
4. Submit without session → preview only
5. Reach attempt limit → submission blocked

### Manual Verification
1. Launch app locally
2. Test session URL parameter
3. Test preview mode without login
4. Test submission with login
5. Verify dark mode CSS
6. Check mobile responsiveness

---

## Phase 4: CSS & UI Polish

### Consolidate CSS
- Single CSS block in create function
- Remove hard-coded colors
- Use CSS variables for theme
- Test dark mode readability

### Session Required Styling
Add CSS class:
```css
.kpi-card--session-required {
    border: 2px solid var(--color-accent);
    background: linear-gradient(135deg, var(--bg-light) 0%, var(--bg-lighter) 100%);
}
```

---

## Acceptance Criteria Checklist

- [ ] Session auth loads stats when ?sessionid= present
- [ ] Preview works without session
- [ ] Preview shows "Session Required" message in KPI
- [ ] Team names match latest leaderboard entry
- [ ] Attempt limit enforced
- [ ] No os.environ mutation (except temp compat)
- [ ] Inline login removed OR hidden when session present
- [ ] Leaderboard caching reduces API calls (verify via DEBUG_LOG)
- [ ] Dark mode styling consistent
- [ ] File size ~3400 lines (maintained)

---

## Timeline Estimate

- Phase 2 (Session Auth): 4-6 hours
- Phase 3 (Testing): 2-3 hours
- Phase 4 (CSS/Polish): 1-2 hours
- **Total:** ~8-11 hours of focused development

---

## Notes

- Keep ATTEMPT_LIMIT logic intact (default 10)
- Preserve instructional slide content
- No breaking changes to Competition API usage
- Follow patterns from moral_compass_challenge.py exactly

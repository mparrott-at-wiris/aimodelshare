# Bias Detective Transitions Implementation

## Summary

Successfully added smooth transitions and auto-scroll functionality to both `bias_detective_part1.py` and `bias_detective_part2.py` apps, matching the behavior of the `what_is_ai.py` app.

## Changes Made

### 1. Loading Overlay HTML (Added to both apps)

```html
<div id='app_top_anchor' style='height:0;'></div>
<div id='nav-loading-overlay'>
    <div class='nav-spinner'></div>
    <span id='nav-loading-text'>Loading...</span>
</div>
```

- **app_top_anchor**: Invisible anchor point at the top of the page for smooth scrolling
- **nav-loading-overlay**: Full-screen overlay that appears during transitions
- **nav-spinner**: Animated spinner with CSS keyframe animation
- **nav-loading-text**: Customizable loading message text

### 2. CSS Styling (Added to both apps)

```css
/* Navigation loading overlay */
#nav-loading-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: color-mix(in srgb, var(--body-background-fill) 95%, transparent);
  z-index: 9999; display: none; flex-direction: column; align-items: center;
  justify-content: center; opacity: 0; transition: opacity 0.3s ease;
}
.nav-spinner {
  width: 50px; height: 50px; border: 5px solid var(--border-color-primary);
  border-top: 5px solid var(--color-accent); border-radius: 50%;
  animation: nav-spin 1s linear infinite; margin-bottom: 20px;
}
@keyframes nav-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
#nav-loading-text {
  font-size: 1.3rem; font-weight: 600; color: var(--color-accent);
}
```

Features:
- Semi-transparent overlay covering the entire viewport
- Centered spinner with rotation animation
- Smooth fade in/out with opacity transition
- Dark mode support via `@media (prefers-color-scheme: dark)`

### 3. JavaScript Navigation Helper (Added to both apps)

```python
def nav_js(target_id: str, message: str) -> str:
    """Generate JavaScript for smooth navigation with loading overlay."""
    return f"""
    ()=>{{
      try {{
        const overlay = document.getElementById('nav-loading-overlay');
        const messageEl = document.getElementById('nav-loading-text');
        if(overlay && messageEl) {{
          messageEl.textContent = '{message}';
          overlay.style.display = 'flex';
          setTimeout(() => {{ overlay.style.opacity = '1'; }}, 10);
        }}
        const startTime = Date.now();
        setTimeout(() => {{
          const anchor = document.getElementById('app_top_anchor');
          if(anchor) anchor.scrollIntoView({{behavior:'smooth', block:'start'}});
        }}, 40);
        const targetId = '{target_id}';
        const pollInterval = setInterval(() => {{
          const elapsed = Date.now() - startTime;
          const target = document.getElementById(targetId);
          const isVisible = target && target.offsetParent !== null && 
                           window.getComputedStyle(target).display !== 'none';
          if((isVisible && elapsed >= 1200) || elapsed > 7000) {{
            clearInterval(pollInterval);
            if(overlay) {{
              overlay.style.opacity = '0';
              setTimeout(() => {{ overlay.style.display = 'none'; }}, 300);
            }}
          }}
        }}, 90);
      }} catch(e) {{ console.warn('nav-js error', e); }}
    }}
    """
```

This function:
1. Shows the loading overlay with custom message
2. Scrolls to the top of the page (smooth behavior)
3. Polls for target visibility
4. Hides overlay when target is visible or after timeout

### 4. Navigation Handler Updates (Both apps)

**Previous Button (Example):**
```python
def create_prev_nav(prev_col=prev_col, curr_col=curr_col):
    def navigate_prev():
        # First yield: hide current, show nothing (transition state)
        yield gr.update(visible=False), gr.update(visible=False)
        # Second yield: show previous, hide current
        yield gr.update(visible=True), gr.update(visible=False)
    return navigate_prev

prev_btn.click(
    fn=create_prev_nav(),
    outputs=[prev_col, curr_col],
    js=nav_js(prev_target_id, "Loading..."),
)
```

**Next Button (Example):**
```python
def wrapper_next(user, tok, team, tasks, next_idx=i+1):
    data, _ = ensure_table_and_get_data(user, tok, team, tasks)
    dash_html = render_top_dashboard(data, next_idx)
    return dash_html

def navigate_generator(curr=curr_col, nxt=next_col):
    # First yield: hide current, show nothing (transition state)
    yield gr.update(visible=False), gr.update(visible=False)
    # Second yield: hide current, show next
    yield gr.update(visible=False), gr.update(visible=True)

next_btn.click(
    fn=wrapper_next,
    inputs=[username_state, token_state, team_state, task_list_state],
    outputs=[out_top]
).then(
    fn=navigate_generator,
    outputs=[curr_col, next_col],
    js=nav_js(next_target_id, "Loading..."),
)
```

Changes:
- Used generator pattern to yield transition states
- Added `js` parameter to button clicks for loading overlay and scroll behavior
- Maintained dashboard updates for next button navigation

## User Experience Improvements

1. **Smooth Transitions**: Users see a loading overlay instead of instant slide changes
2. **Visual Feedback**: Spinner animation provides clear feedback that navigation is in progress
3. **Auto-Scroll**: Page automatically scrolls to top on every navigation, ensuring users start at the beginning of each slide
4. **Consistent Behavior**: All three apps (what_is_ai, bias_detective_part1, bias_detective_part2) now have identical navigation UX

## Testing

Created `tests/test_bias_detective_parts.py` with tests to verify:
- Both apps can be created without errors
- Navigation CSS is present in both apps
- Spinner animation CSS is present in both apps

All tests pass successfully.

## Files Modified

1. `/home/runner/work/aimodelshare/aimodelshare/aimodelshare/moral_compass/apps/bias_detective_part1.py`
   - Added CSS for loading overlay (lines ~1757-1783)
   - Added loading overlay HTML elements (lines ~1800-1801)
   - Added `nav_js()` JavaScript helper function (lines ~2131-2164)
   - Modified navigation handlers to use generator pattern (lines ~2166-2226)

2. `/home/runner/work/aimodelshare/aimodelshare/aimodelshare/moral_compass/apps/bias_detective_part2.py`
   - Added CSS for loading overlay (lines ~2095-2121)
   - Added loading overlay HTML elements (lines ~2210-2211)
   - Added `nav_js()` JavaScript helper function (lines ~2347-2380)
   - Modified navigation handlers to use generator pattern (lines ~2382-2437)

3. `/home/runner/work/aimodelshare/aimodelshare/tests/test_bias_detective_parts.py` (new file)
   - Tests for app creation and CSS presence

## Verification

The implementation was verified by:
1. Python syntax check (both files compile without errors)
2. Automated tests (all pass)
3. Comparing implementation to the working `what_is_ai.py` reference

# Moral Compass Integration for Activities 7, 8, and 9

## Overview
This document describes the Moral Compass scoring system integration into the Ethics/Game applications (Activities 7, 8, and 9).

## Architecture

### Client-Side Design
All scoring combination logic is performed client-side. The server stores only a single primary metric (`moralCompassScore`) without custom metadata fields.

**Scoring Formula:**
```
Combined Score = Accuracy × Normalized_Moral_Points
Where:
  Normalized_Moral_Points = min(raw_moral_points / MAX_MORAL_POINTS, 1.0)
```

**Alternative (Weighted Sum):**
```
Combined Score = (WEIGHT_ACC × Accuracy) + (WEIGHT_MORAL × Normalized_Moral_Points)
```

Configured via environment variables (see Configuration section).

### Components

#### 1. Helper Module (`mc_integration_helpers.py`)
Core integration logic including:

- **`get_challenge_manager(username)`**: Initialize ChallengeManager for user
- **`sync_user_moral_state(cm, moral_points, override=False)`**: Debounced sync to server
- **`sync_team_state(team_name)`**: Team aggregation logic
- **`fetch_cached_users(table_id, ttl=30)`**: Cached leaderboard data
- **`build_moral_leaderboard_html()`**: Leaderboard rendering
- **`compute_combined_score(accuracy, moral_points)`**: Scoring logic

#### 2. Shared Styles (`shared_activity_styles.css`)
Consistent styling across activities:
- KPI cards (Moral Compass widgets)
- Leaderboard tables with user highlighting
- Button variants (primary, secondary, neutral, success, info)
- Alert panels
- Dark mode support

#### 3. Activity Integration

**Activity 7: Bias Detective (tasks A-C)**
- Task A: OEIAC Framework understanding
- Task B: Demographics identification
- Task C: Bias analysis

**Activity 8: Fairness Fixer (tasks D-E)**
- Task D: Feature and proxy removal
- Task E: Representative data strategies

**Activity 9: Justice & Equity Upgrade (tasks E-F)**
- Task E: Accessibility features
- Task F: Diversity and stakeholder engagement

## Configuration

### Environment Variables

```bash
# Debounce Settings
MC_DEBOUNCE_SECONDS=5          # Default: 5 seconds

# Scoring Mode
MC_SCORING_MODE=product        # Options: 'product' or 'sum'

# Weighted Sum Mode Parameters
MC_WEIGHT_ACC=0.6             # Weight for accuracy (sum mode only)
MC_WEIGHT_MORAL=0.4           # Weight for moral points (sum mode only)

# Normalization
MC_ACCURACY_FLOOR=0.0         # Minimum accuracy value
MAX_MORAL_POINTS=1000         # Maximum moral points for normalization

# Caching
MC_CACHE_TTL=30               # Leaderboard cache TTL in seconds

# Table Identification
MORAL_COMPASS_TABLE_ID=<id>  # Optional explicit table ID
PLAYGROUND_URL=<url>          # For auto-deriving table ID
```

### User Identification

```bash
username=<username>           # Required for sync
TEAM_NAME=<team_name>         # Optional team name
TEAM_MEMBERS=user1,user2     # Comma-separated team members
```

## Features

### 1. Debounced Sync
Prevents excessive API calls by enforcing a minimum interval between syncs (default: 5 seconds).

**Behavior:**
- Rapid user actions trigger local preview
- Actual sync occurs only after debounce interval
- Force Sync button bypasses debounce
- Status message indicates "(synced)" or "(pending)"

### 2. Team Aggregation
Teams are represented as synthetic users with `team:` prefix.

**Algorithm:**
1. Fetch team member list (from env or registry)
2. Retrieve each member's accuracy from playground leaderboard
3. Retrieve each member's moral compass score
4. Compute averages: `avg_accuracy`, `avg_moral_points`
5. Calculate team combined score: `avg_accuracy × avg_moral_norm`
6. Persist as synthetic user: `team:<TeamName>`

### 3. Guest Mode
When user is not signed in:
- Show local moral points only
- No sync attempts (avoid authentication errors)
- Widget displays "Guest mode - sign in to sync"

### 4. Ethics Leaderboard
Separate leaderboard showing combined scores (ethics + accuracy).

**Differences from Model Game Leaderboard:**
- **Model Game:** Pure accuracy/performance ranking
- **Ethics Leaderboard:** Holistic score (ethical engagement + technical skill)
- Includes both individual users and team entries

### 5. Force Sync
Manual sync button that bypasses debounce.

**Use Cases:**
- Immediate score update before viewing leaderboard
- Verification after completing multiple tasks
- Recovery from sync errors

## Educational Content Enhancements

### Activity 7: Bias Detective
- **Confusion Matrix Example:** Real COMPAS-like data showing false positive disparity
- **Real-World Impact:** Explanation of FP consequences (bail denial, longer sentences)

### Activity 8: Fairness Fixer
- **Fairness Metrics Comparison:** Statistical Parity vs Equal Opportunity vs Equalized Odds
- **Numeric Example:** TPR/FPR calculations for two demographic groups
- **Limitation Analysis:** Trade-offs between different fairness definitions

### Activity 9: Justice & Equity Upgrade
- **Barcelona Court Case:** Multilanguage interface accessibility example
- **Design Review Comparison:** Homogeneous vs diverse team outcomes
- **Stakeholder Matrix:** Power vs Impact vs Voice analysis framework

## Implementation Notes

### ChallengeManager Task Mapping
Tasks A-F are distributed across activities as follows:

| Task | Activity | Component | Moral Points |
|------|----------|-----------|--------------|
| A    | 7        | Framework understanding | 100 |
| B    | 7        | Demographics identification | 50 |
| C    | 7        | Bias analysis | 100 |
| D    | 8        | Feature/proxy removal | 200 |
| E    | 8        | Representative data | 75 |
| F    | 9        | Diversity & stakeholders | 100 |

**Total Possible:** 625 points (normalized to 0-1 scale)

### Server API Endpoints Used
Only existing endpoints are utilized:
- `PUT /tables/{table}/users/{username}/moral-compass`
- `GET /tables/{table}/users` (with pagination)
- `GET /tables/{table}/users/{username}`

No server-side changes required.

### Error Handling
All sync operations are wrapped in try/except blocks with user-visible fallback:
- Network errors → Show local preview with error message
- Authentication errors → Provide clear guidance (set JWT_AUTHORIZATION_TOKEN)
- Server errors → Log and display retry option

### Logging
Info-level logging for:
- Sync attempts with summary metrics
- ChallengeManager initialization
- Team aggregation operations
- Cache hits/misses

## Testing Guidelines

### Manual Testing Checklist

#### Sign-In Flow
- [ ] Sign in with valid credentials
- [ ] ChallengeManager initializes
- [ ] Moral Compass widget shows "0 points (pending)"

#### Point Accumulation
- [ ] Complete Task A → 100 points awarded
- [ ] Complete Task B → 50 points awarded
- [ ] Complete Task C → 100 points awarded
- [ ] Local widget updates immediately
- [ ] Server sync occurs (check sync status message)

#### Force Sync
- [ ] Click Force Sync button
- [ ] Server score appears immediately
- [ ] Status changes to "(synced)"
- [ ] Team entry appears in leaderboard (if team configured)

#### Guest Mode
- [ ] Access activity without signing in
- [ ] Widget shows local points only
- [ ] No sync error messages
- [ ] No server API calls attempted

#### Debounce Verification
- [ ] Perform two actions < 3 seconds apart
- [ ] First action triggers sync
- [ ] Second action shows "(pending)"
- [ ] Wait > 5 seconds and perform third action
- [ ] Third action triggers sync

#### Team Aggregation
- [ ] Configure TEAM_MEMBERS with 2+ users
- [ ] Both users accumulate points and sync
- [ ] Team entry appears with username `team:<TeamName>`
- [ ] Team score is average of member scores

### Unit Test Coverage
Key functions to test:
- `compute_combined_score()` with various inputs
- `should_sync()` debounce logic
- `_aggregate_team_data()` averaging logic
- `fetch_cached_users()` cache behavior

## Future Enhancements

### Planned (TODOs in code)
- Historical time-series storage for score progression
- Progress-aware normalization (adjust based on activity completion)
- Team member registry integration (replace env var approach)
- Webhook notifications for team achievements
- Detailed analytics dashboard

### Possible Improvements
- Multi-metric primary selection (user chooses what to optimize)
- Weighted task importance (some tasks worth more than others)
- Adaptive difficulty (harder questions earn more points)
- Peer review component (team members review each other's reasoning)

## Troubleshooting

### Common Issues

**"Guest mode - sign in to sync"**
- Cause: No `username` environment variable
- Solution: Set `username` and optionally `JWT_AUTHORIZATION_TOKEN`

**"Authentication failed (401)"**
- Cause: Invalid or expired JWT token
- Solution: Re-generate token with `get_jwt_token(username, password)`

**"Sync pending (debounced)"**
- Cause: Too many syncs in short time
- Solution: Wait 5+ seconds or use Force Sync button

**Team entry not appearing**
- Cause: TEAM_MEMBERS not set or members haven't synced
- Solution: Set TEAM_MEMBERS env var, ensure members complete activities and sync

**Leaderboard empty**
- Cause: No users in table yet, or table_id incorrect
- Solution: Verify MORAL_COMPASS_TABLE_ID or PLAYGROUND_URL is set correctly

### Debug Logging
Enable debug logging:
```python
import logging
logging.getLogger("aimodelshare.moral_compass.apps").setLevel(logging.DEBUG)
```

## Security Considerations

### CodeQL Scan Results
✓ No security alerts detected (as of implementation)

### Best Practices Applied
- No secrets stored in code
- User input sanitized before API calls
- Authentication tokens handled via environment variables
- SQL injection not applicable (REST API only)
- XSS prevention via Gradio's HTML escaping

### Data Privacy
- Usernames and scores are public within the leaderboard context
- No PII collected beyond username
- Team membership is opt-in via environment configuration
- Server stores only aggregated metrics, not raw activity data

## Maintenance

### Updating Scoring Formula
To change the scoring mode:
1. Set `MC_SCORING_MODE=sum` (or `product`)
2. Adjust weights: `MC_WEIGHT_ACC` and `MC_WEIGHT_MORAL`
3. Restart activities (changes take effect immediately)

### Adding New Tasks
To add Task G to an activity:
1. Update `JusticeAndEquityChallenge` in `challenge.py` with new task
2. Call `challenge_manager.complete_task('G')` at appropriate point
3. Update task mapping documentation above

### Modifying Leaderboard Display
Edit `build_moral_leaderboard_html()` in `mc_integration_helpers.py`:
- Add columns (e.g., last updated timestamp)
- Change sorting criteria
- Apply custom filters (e.g., show only top 10)

## Credits
- Integration design: Based on existing MoralcompassApiClient and ChallengeManager patterns
- Styling: Aligned with model_building_game.py conventions
- Educational content: Inspired by COMPAS case study and OEIAC framework

## References
- Moral Compass API: `aimodelshare/moral_compass/api_client.py`
- Challenge Manager: `aimodelshare/moral_compass/challenge.py`
- Model Building Game: `aimodelshare/moral_compass/apps/model_building_game.py`

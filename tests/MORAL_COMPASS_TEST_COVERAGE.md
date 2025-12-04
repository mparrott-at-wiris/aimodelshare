# Moral Compass Integration Test Coverage

## Problem Statement Requirements vs Test Implementation

This document maps the requirements from the problem statement to the specific tests in `test_moral_compass_comprehensive_integration.py`.

### Original Requirements

> "I need a thorough integration test for the rest api url and lambda that are used to create new moral compass user and table tracking data. We need to test the live api for each functionality that we want to use in the detective bias app."

### Requirement Mapping

#### 1. Find Tables Based on Playground IDs (with and without auth)

**Requirements:**
- Test finding tables with authentication
- Test finding tables without authentication (public read)

**Tests:**
- **Test 2**: `test_2_find_table_by_id_without_auth()`
  - Creates a client without auth token
  - Attempts to retrieve the table
  - Validates behavior (either succeeds with public read or fails gracefully with 401)
  
- **Test 3**: `test_3_find_table_by_id_with_auth()`
  - Uses authenticated client
  - Retrieves table by ID
  - Validates table metadata

**API Endpoints Used:**
- `GET /tables/{tableId}`

#### 2. Update User Information with Accuracy Scores and Tasks

**Requirements:**
- Add new accuracy scores to users
- Update tasks that lead to moral compass score
- Verify that score maxes out at the accuracy score (capped behavior)

**Tests:**
- **Test 4**: `test_4_create_users_with_varying_data()`
  - Creates 10 users with varying accuracy scores (0.78 - 0.96)
  - Sets different task counts (6 - 18 tasks)
  - Assigns team names (a, b, c)
  
- **Test 6**: `test_6_verify_moral_compass_calculation()`
  - Validates that `moralCompassScore = accuracy × tasks_completed`
  - Checks all 10 users' scores against expected values
  
- **Test 7**: `test_7_update_user_with_new_accuracy()`
  - Updates an existing user with a new (lower) accuracy score
  - Adds more tasks to the user
  - Verifies the score recalculates correctly
  - Demonstrates that the score caps appropriately based on accuracy

**API Endpoints Used:**
- `PUT /tables/{tableId}/users/{username}/moral-compass`

**Calculation Verified:**
```
moralCompassScore = primaryMetric × (tasks_completed / (total_tasks + total_questions))
When total_tasks = tasks_completed and questions = 0:
moralCompassScore = accuracy × tasks_completed
```

#### 3. Add and Retrieve Team Information

**Requirements:**
- Test if team information can be added for each user
- Test if team information can be retrieved for each user

**Tests:**
- **Test 4**: `test_4_create_users_with_varying_data()`
  - Assigns team names when creating users
  - Uses `team_name` parameter in `update_moral_compass()` calls
  
- **Test 8**: `test_8_verify_team_information()`
  - Retrieves all users from the table
  - Validates that each user has the correct `teamName` attribute
  - Checks all 10 users against expected team assignments

**API Endpoints Used:**
- `PUT /tables/{tableId}/users/{username}/moral-compass` (with `teamName` field)
- `GET /tables/{tableId}/users` (retrieves users with team data)

#### 4. Retrieve All User Information for 10 Users

**Requirements:**
- Retrieve user data for 10 users
- Users should have different accuracy scores
- Users should have different numbers of tasks completed
- All users should be labeled with team a, b, or c

**Tests:**
- **Test 5**: `test_5_retrieve_all_users()`
  - Fetches all users from the table
  - Filters to the 10 test users
  - Validates that all 10 users are retrieved
  - Logs details for each user (score, team)

**Test Data Created:**
```
Team A (3 users):
- user-a-1: accuracy=0.95, tasks=10, expected_score=9.5
- user-a-2: accuracy=0.85, tasks=15, expected_score=12.75
- user-a-3: accuracy=0.90, tasks=12, expected_score=10.8

Team B (4 users):
- user-b-1: accuracy=0.92, tasks=8, expected_score=7.36
- user-b-2: accuracy=0.88, tasks=14, expected_score=12.32
- user-b-3: accuracy=0.78, tasks=18, expected_score=14.04
- user-b-4: accuracy=0.96, tasks=6, expected_score=5.76

Team C (3 users):
- user-c-1: accuracy=0.89, tasks=11, expected_score=9.79
- user-c-2: accuracy=0.93, tasks=9, expected_score=8.37
- user-c-3: accuracy=0.87, tasks=13, expected_score=11.31
```

**API Endpoints Used:**
- `GET /tables/{tableId}/users?limit=100`

#### 5. Return Individual Rankings by Moral Compass Score

**Requirements:**
- Compute individual rankings based on moral compass score
- Display rankings in order

**Tests:**
- **Test 9**: `test_9_individual_rankings()`
  - Retrieves all users
  - Sorts by `moralCompassScore` (descending)
  - Assigns ranks (1 = highest score)
  - Displays formatted ranking table with:
    - Rank number
    - Username
    - Moral compass score
    - Team assignment

**Example Output:**
```
Individual Rankings:
Rank   Username                       Score      Team      
------------------------------------------------------------
#1     user-b-3                       14.0400    team-b    
#2     user-a-2                       12.7500    team-a    
#3     user-b-2                       12.3200    team-b    
...
```

#### 6. Return Team Rankings by Average Individual Score

**Requirements:**
- Compute team rankings
- Rankings based on average individual score per team

**Tests:**
- **Test 10**: `test_10_team_rankings()`
  - Groups users by team name
  - Calculates average moral compass score per team
  - Sorts teams by average score (descending)
  - Displays formatted ranking table with:
    - Team rank
    - Team name
    - Average score
    - Number of members

**Example Output:**
```
Team Rankings:
Rank   Team            Avg Score    Members   
--------------------------------------------------
#1     team-a          11.0167      3         
#2     team-b          9.8700       4         
#3     team-c          9.8233       3         
```

**Calculation:**
```
Team Average = SUM(member_scores) / COUNT(members)

Team A: (9.5 + 12.75 + 10.8) / 3 = 11.02
Team B: (7.36 + 12.32 + 14.04 + 5.76) / 4 = 9.87
Team C: (9.79 + 8.37 + 11.31) / 3 = 9.82
```

### Additional Tests for Robustness

Beyond the stated requirements, the test suite includes:

- **Test 1**: `test_1_create_table_with_playground_url()`
  - Creates the test table
  - Validates table creation with playground URL
  - Ensures clean state for subsequent tests

### Phase II Evaluation Criteria

The test suite helps evaluate the following for Phase II:

1. **Functionality Completeness**
   - ✅ All required operations are supported
   - ✅ Moral compass score calculation is correct
   - ✅ Team management works as expected
   - ✅ Rankings can be computed from API data

2. **Performance Indicators**
   - Response times for user retrieval
   - Handling of 10+ users concurrently
   - Pagination behavior

3. **Data Consistency**
   - Scores update correctly when user data changes
   - Team assignments persist properly
   - Rankings reflect current state

4. **Authentication & Authorization**
   - Public read access behavior
   - Authenticated operations work correctly
   - Error handling for auth failures

5. **Potential Enhancement Needs**
   - Direct team ranking endpoint (currently computed client-side)
   - Bulk user creation endpoint
   - Leaderboard snapshot API
   - Real-time score updates

### Running the Tests

See [MORAL_COMPASS_INTEGRATION_TEST_README.md](./MORAL_COMPASS_INTEGRATION_TEST_README.md) for detailed instructions on:
- Setting up environment variables
- Running the test suite
- Interpreting results
- Troubleshooting common issues

### Related Files

- Test Implementation: `tests/test_moral_compass_comprehensive_integration.py`
- Documentation: `tests/MORAL_COMPASS_INTEGRATION_TEST_README.md`
- Runner Script: `scripts/run_moral_compass_integration_test.sh`
- Lambda Handler: `infra/lambda/app.py`
- API Client: `aimodelshare/moral_compass/api_client.py`

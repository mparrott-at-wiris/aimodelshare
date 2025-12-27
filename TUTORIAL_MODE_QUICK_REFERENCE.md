# Tutorial Mode - Quick Reference

## Tutorial Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Model Building Arena                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Model Strategy         [Interactive in Step 1+]   │  │
│  │    ○ The Balanced Generalist                          │  │
│  │    ○ The Rule-Maker                                   │  │
│  │    ○ The Deep Pattern-Finder                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 2. Model Complexity       [Interactive in Step 2+]   │  │
│  │    ├─●─────────────┤  (1-10)                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 3. Data Ingredients       [Interactive in Step 3+]   │  │
│  │    ☑ Juvenile Felony Count                            │  │
│  │    ☑ Juvenile Misdemeanor Count                       │  │
│  │    ☐ Race                                             │  │
│  │    ☐ Age                                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 4. Data Size              [Interactive in Step 4+]   │  │
│  │    ○ Small (20%)                                      │  │
│  │    ○ Medium (60%)                                     │  │
│  │    ○ Full (100%)                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [5. 🔬 Build & Submit Model] [Interactive in Step 5] │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [🧭 Start Guided Tutorial]  ← Click to start         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Tutorial Panel (hidden by default)                    │  │
│  │ ┌──────────────────────────────────────────────────┐ │  │
│  │ │ ### Step 1: Model Strategy                        │ │  │
│  │ │ Choose a model strategy that sets the 'brain'...  │ │  │
│  │ │                                                    │ │  │
│  │ │ [◀️ Back]  [Next ▶️]  [Exit Tutorial]           │ │  │
│  │ └──────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Progression

### Step 1: Model Strategy
```
Interactive: [✓] Model Strategy
             [ ] Model Complexity
             [ ] Data Ingredients
             [ ] Data Size
             [ ] Submit Button

Message: "Choose a model strategy that sets the 'brain' of your system. 
         Try starting with 'The Balanced Generalist'."
```

### Step 2: Model Complexity
```
Interactive: [✓] Model Strategy
             [✓] Model Complexity
             [ ] Data Ingredients
             [ ] Data Size
             [ ] Submit Button

Message: "Adjust how deeply the model learns patterns. 
         Start low and increase gradually."
```

### Step 3: Data Ingredients
```
Interactive: [✓] Model Strategy
             [✓] Model Complexity
             [✓] Data Ingredients
             [ ] Data Size
             [ ] Submit Button

Message: "Select the inputs your model can use. Begin with behavioral 
         inputs; consider ethics when adding demographics."
```

### Step 4: Data Size
```
Interactive: [✓] Model Strategy
             [✓] Model Complexity
             [✓] Data Ingredients
             [✓] Data Size
             [ ] Submit Button

Message: "Pick how much historical data to train on. 'Small (20%)' is 
         fast for tests; 'Full (100%)' is strongest."
```

### Step 5: Build & Submit
```
Interactive: [✓] Model Strategy
             [✓] Model Complexity
             [✓] Data Ingredients
             [✓] Data Size
             [✓] Submit Button

Message: "You're ready! Click 'Build & Submit Model' to run your 
         first build."
```

## User Interactions

### Starting Tutorial
1. User clicks "🧭 Start Guided Tutorial"
2. Tutorial panel appears with Step 1 content
3. Login prompts hidden
4. Only Model Strategy control is interactive
5. All other controls disabled

### Navigating Tutorial
- **Next ▶️**: Advance to next step (max: Step 5)
- **◀️ Back**: Return to previous step (min: Step 1)
- **Exit Tutorial**: Close tutorial and restore normal mode

### Exiting Tutorial
1. User clicks "Exit Tutorial"
2. Tutorial panel disappears
3. `compute_rank_settings()` called to restore rank-based interactivity
4. Login prompts restored if user not authenticated
5. User's choices (model, complexity, features, size) preserved

## Code Locations

### UI Components
File: `aimodelshare/moral_compass/apps/model_building_app_en.py`
Lines: 3811-3829

### Helper Functions
File: `aimodelshare/moral_compass/apps/model_building_app_en.py`
Lines: 4093-4206

### Event Wiring
File: `aimodelshare/moral_compass/apps/model_building_app_en.py`
Lines: 4319-4341

### Unit Tests
File: `tests/test_tutorial_mode.py`
Lines: 1-123

## Testing Checklist

### Automated Tests ✅
- [x] Syntax validation
- [x] Code review
- [x] Security scan (CodeQL)
- [x] Unit tests

### Manual Testing (Deploy to test)
- [ ] Click "Start Guided Tutorial"
- [ ] Verify tutorial panel appears
- [ ] Verify Step 1: only Model Strategy interactive
- [ ] Click "Next" → Verify Step 2: Model Strategy + Complexity interactive
- [ ] Click "Next" → Verify Step 3: + Data Ingredients interactive
- [ ] Click "Next" → Verify Step 4: + Data Size interactive
- [ ] Click "Next" → Verify Step 5: All controls + Submit interactive
- [ ] Click "Back" repeatedly → Verify backward navigation
- [ ] Click "Exit Tutorial" → Verify return to normal mode
- [ ] Verify login visibility based on auth state
- [ ] Complete full tutorial → Submit first model → Verify submission works

## Common Issues & Solutions

### Issue: Tutorial doesn't start
**Solution**: Check browser console for errors. Ensure all dependencies loaded.

### Issue: Controls don't become interactive
**Solution**: Verify `_tutorial_interact_for_step()` logic and state updates.

### Issue: Exit doesn't restore normal mode
**Solution**: Check `compute_rank_settings()` is being called correctly with current state.

### Issue: Login prompts not appearing after exit
**Solution**: Verify `username_state` and `token_state` values and authentication logic.

## Implementation Stats

- Total lines added: ~405
- Total files modified: 1
- Total files created: 2
- Functions added: 6
- Constants added: 1
- States added: 2
- UI components added: 5
- Event handlers added: 4
- Test functions: 5
- Documentation pages: 2

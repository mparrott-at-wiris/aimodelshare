# Step-by-Step Engagement & Impact Audit: Activities 1-3

**Date:** 2026-02-10
**Evaluators:** 17-year-old student perspective + Teacher perspective
**Scale:** 1 (disengaged/ineffective) to 5 (highly engaging/highly effective)

---

## Activity 1: Climate Mission Investigation (8 steps)

### Step 0: Mission Briefing
**What happens:** Student gets "Climate Action Investigator" role. Animated fact scroller shows 2 real climate stats (temperature milestone, tech exists). Mission objective: find the biggest polluter in their city. Climate TRACE data source explained.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The role assignment ("Climate Action Investigator") is genuinely cool — teenagers respond to identity framing. The glowing mission objective box grabs attention. The fact scroller with animated counters (+1.45°C, 50%) creates a sense of urgency. Slightly too much text in the data source explanation. |
| **Teacher** | 5/5 | Excellent framing — sets clear learning objective, establishes real-world stakes with cited sources (NASA GISS, IPCC AR6). The mission objective is unambiguous. The "explain" tooltips for jargon like "carbon emissions" and "satellites" show good scaffolding. |

**Improvements:**
- Consider cutting the Climate TRACE explanation to a single sentence — students don't need to know it's a "global group" at this point
- The fact scroller only has 2 facts but shows "1 more" — could feel thin; consider adding a 3rd fact about local impact

### Step 1: Select Your City
**What happens:** Text input for city name, or click a suggestion chip (Barcelona, Lleida, New York, etc.). Submits to Climate TRACE API.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 5/5 | This is the highest-engagement moment in all three activities. Typing YOUR OWN city and getting real satellite data back is genuinely exciting. The suggestion chips lower the barrier for students who aren't sure what to type. The error message with helpful tips prevents frustration. |
| **Teacher** | 4/5 | Great personalization hook. The suggestion chips are well-chosen for the target audience (Spanish cities for the intended deployment context). Minor concern: API latency could cause confusion or disengagement if the connection is slow. No offline fallback. |

**Improvements:**
- Add a short loading-state message like "Scanning satellite data for [city]..." to maintain excitement during API wait
- Consider a retry mechanism or cached fallback for common cities

### Step 2: The Big Picture (Emissions Trend)
**What happens:** Shows 2022 vs 2023 total emissions for the city. Cars-equivalent context line. Families-affected counter. Checkpoint question: did emissions go up or down?

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The big numbers are impressive. The "families affected" counter and "cars driving for a year" translation make abstract tonnes tangible. The checkpoint question is easy (50/50) but creates a sense of participation. Auto-advance after correct answer keeps momentum. |
| **Teacher** | 4/5 | Good data literacy moment — students read real numbers and identify a trend. The human-impact framing (families, cars) is excellent pedagogy. The "explain" tooltip for "carbon footprint" is well-placed. Concern: the checkpoint is too easy to be a real assessment — it's a 50/50 guess with visible data. |

**Improvements:**
- The checkpoint question could be made slightly harder: "By approximately what percentage?" (multiple choice) instead of binary up/down
- The families-affected estimate disclaimer ("based on 8.1 tonnes/year") is good but could briefly explain why that number matters

### Step 3: Sector Breakdown
**What happens:** Chart.js bar chart of emission sectors. Quiz: identify the highest-emitting sector from 4 shuffled options.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The chart is visually clear and uses real data. The quiz forces students to actually read the chart, not just glance at it. The sector name formatting is readable. Selecting the correct answer feels earned. |
| **Teacher** | 5/5 | Excellent data-reading exercise. The chart + quiz pattern is textbook good pedagogy for graph literacy. The randomized option order prevents memorization. The "explain" tooltip on "Sector (Industry Group)" in the heading helps ELL students. |

**Improvements:**
- The chart labels can be tiny on mobile (font-size: 9px) — consider making them slightly larger or rotating them
- After correct answer, a brief sentence about what the top sector actually does would add context

### Step 4: Tracking the Sources
**What happens:** Top 3 sources as clickable cards with rank badges. Click to see details (industry type, emissions, % of city total, lat/lon proximity). Quiz: identify the highest emitter.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | Clicking source cards and seeing real facility names + locations is compelling — these are real places students might recognize. The proximity estimate ("X people live within range") creates emotional stakes. The rank badges make it feel like a leaderboard. |
| **Teacher** | 4/5 | Good investigative skill development. Students learn to compare sources and read detailed data cards. The proximity feature connects abstract data to human impact. Concern: the population estimate is a rough heuristic (emissions/50) with no methodology explanation for teachers. |

**Improvements:**
- The proximity estimate methodology should be documented (even if just a tooltip) — teachers may get questions about it
- Consider adding a "View on map" link using the lat/lon coordinates for spatial learners
- The quiz options show "name (subsector)" which can be confusing if names look similar

### Step 5: Strategic Approaches
**What happens:** Shows the top sector label and impact of halving its emissions. Animated before/after impact bars. Quiz: focused rules vs. asking all industries equally.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 3/5 | The impact bars are visually satisfying. The "cars off the road" translation is concrete. But the quiz is too obvious — "focused rules" vs. "asking with no rules" is a leading question. Students aren't making a real choice; they're guessing what the app wants. The strategy doesn't feel personal enough. |
| **Teacher** | 3/5 | The impact visualization is pedagogically strong. The "half impact" calculation is simple enough for the age group. But the quiz has a clear "right" answer — it's not actually testing strategic thinking. A real decision with trade-offs would be more educational. |

**Improvements:**
- **High priority:** Make the strategy choice genuinely debatable. Instead of "rules" vs. "no rules," offer options like "strict regulation" vs. "financial incentives" vs. "public reporting" — all valid approaches with different trade-offs
- The strategy quiz answer ("focused rules") auto-advances to Step 6 after 2 seconds — this should be longer, or let the student control the pace
- Add a sentence explaining WHY targeted approaches work better than blanket ones

### Step 6: Final Report
**What happens:** Auto-generated summary of findings. Mad-lib style recommendation: dropdown to pick strategy + text input for reasoning.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The fill-in-the-blank format is low friction and feels empowering — "I recommend the city..." makes the student feel like a real advisor. The dropdown prevents blank-page paralysis. The free-text reasoning input lets students express their own thinking. |
| **Teacher** | 5/5 | Excellent formative assessment. The structured recommendation + free-text combo captures both understanding (dropdown choice) and reasoning (text input). The auto-generated context ensures the recommendation is grounded in data. This is genuine scientific writing practice. |

**Improvements:**
- The reasoning input has no minimum length check — students could type "idk" and proceed. Consider requiring at least 10 characters
- The auto-summary could include the specific numbers (emissions quantity, % of total) to model data-driven writing

### Step 7: Mission Complete
**What happens:** Trophy icon, final advice displayed, journey-save banner ("Your data carries forward"), link to Activity 2.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The trophy and "Mission Complete" feel earned. The journey-save banner creates genuine curiosity about Activity 2 by promising the $500K grant narrative. Seeing their recommendation displayed back is satisfying. The decision badge showing "6/6 Decisions" is a nice payoff. |
| **Teacher** | 4/5 | Good closure. The cliffhanger to Activity 2 creates continuity motivation. The saved journey state is invisible but pedagogically powerful — it means Activity 2 will feel connected. Concern: no option to download or share the report (missed portfolio opportunity). |

**Improvements:**
- Add a "Copy my report" or "Screenshot this" prompt — students could save it for portfolios
- The "PROCEED TO ACTIVITY 2" button competes visually with the "MISSION COMPLETE" button — the CTA hierarchy is slightly unclear

### Activity 1 Summary

| Metric | Score |
|--------|:-----:|
| **Average Student** | **4.0/5** |
| **Average Teacher** | **4.3/5** |
| **Combined** | **4.1/5** |

**Strongest steps:** Step 1 (city selection — real data hook), Step 6 (final report — authentic assessment)
**Weakest step:** Step 5 (strategy quiz — leading question, no real choice)

---

## Activity 2: Climate AI Innovation Lab (6 steps)

### Step 0: Grant Announcement
**What happens:** Congratulations screen. If Activity 1 data exists, shows personalized intro referencing the student's city, sector, and top source. $500K grant for building efficiency AI. Briefing item with estimated building count.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 5/5 | **This is the highest-leverage moment across all three activities.** If the student did Activity 1, seeing their city name and findings appear in a completely new app creates a genuine "whoa" moment. The $500K grant framing maintains the role-play. The personalized building count makes it feel specific to their investigation. |
| **Teacher** | 5/5 | Brilliant narrative continuity. The transition from "investigation" to "AI grant" is well-motivated. The fallback for students who didn't do Activity 1 is clean. The built-environment pivot is handled honestly — it doesn't pretend the top sector was buildings. |

**Improvements:**
- The generic fallback text ("Your climate investigation caught the City Council's attention") is vague for students who skipped Activity 1 — consider briefly explaining what they missed
- The building count estimate (total emissions / 50) could be wildly off for some cities — add "estimated" qualifier

### Step 1: Confirm Sector Target
**What happens:** Three sector cards (Transportation, Power, Buildings). Student selects one. Wrong answers get feedback. Hint after 2 wrong attempts. "Learn more" collapsible.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 3/5 | The card descriptions essentially give away the answer — Buildings is described with all positives ("lots of data, local government control, measurable results") while Transport and Power have obvious negatives. There's no real thinking required. The "Click to select" prompt on each card is helpful but the interaction feels perfunctory. |
| **Teacher** | 4/5 | The rationale behind each option teaches data-availability thinking — a genuine AI concept. The hint system prevents students from getting stuck. The collapsible "Learn more" box respects different engagement levels. But the answer is too telegraphed. |

**Improvements:**
- **High priority:** Make the sector descriptions more balanced so students have to actually reason. Currently Buildings reads like an ad and the others read like warnings
- Remove the "Click to select" pseudo-label on each card — it's unnecessary and adds visual noise
- The feedback for wrong answers could explain what makes buildings better *in comparison* rather than just saying "not quite"

### Step 2: Choose Features (Clues)
**What happens:** 6 feature cards in a grid (Floor Area, Weather, Elevation, Owner's Name, Paint Color, Year Built). Student selects 3 correct ones. Wrong choices fade out with explanation. City-specific feedback appears for correct choices.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The card interactions are satisfying — correct ones get a green checkmark, wrong ones fade with a "why" explanation. The city-specific feedback (e.g., "Chicago has harsh winters with significant heating needs") makes weather data feel relevant to THEIR city. Paint Color and Owner's Name are obviously wrong, which means only Elevation is the real "trap." |
| **Teacher** | 5/5 | Excellent feature-engineering exercise. The "why" feedback on every card teaches the reasoning, not just the answer. The correct/wrong classification with instant feedback is good formative assessment. Three correct features + three wrong features is a clean design. City-specific feedback is a strong personalization touch. |

**Improvements:**
- Two of the three wrong answers (Paint Color, Owner's Name) are too obviously wrong — replace one with something more plausible like "Number of Floors" (related but not the best) or "Zip Code" (proxy for location, but redundant with weather)
- The "building stock context" box above the feature grid could feel redundant with the grant announcement — consider cutting it

### Step 3: Define Energy Score (EUI)
**What happens:** Binary choice: Total Energy vs. Energy Per Square Foot. Wrong answer gets feedback. Correct answer reveals EUI explainer with an interactive calculator (warehouse vs. school example).

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The EUI calculator is the highlight — typing numbers, clicking Calculate, and seeing the color-coded result (green/yellow/red) is genuinely interactive. The warehouse vs. school comparison is a good "aha" moment. The binary choice is a bit obvious (the "per square foot" card is described more favorably) but the calculator saves it. |
| **Teacher** | 5/5 | Teaching EUI through comparison (total vs. normalized) is exactly right for this age group. The "miles-per-gallon for buildings" analogy is perfect. The calculator provides hands-on mathematical practice. Students who try different numbers develop intuition about what EUI values mean. |

**Improvements:**
- The binary choice is somewhat telegraphed. Consider making both options sound reasonable at first, with the feedback explaining why normalization matters
- The calculator could suggest a second pair of numbers to try ("Now try the school: 500,000 energy / 10,000 sqft") to ensure students compare both

### Step 4: Submit Data Request
**What happens:** Summary of data requirements (sector, features, prediction target, minimum records). "SEARCH NREL DATABASE" button triggers animated loading steps. 100,000 records found.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 3/5 | The animated loading sequence (checking Floor Area... ✓, checking Weather... ✓) is mildly satisfying but feels like fake loading — because it is. Students will notice it takes exactly the same time every time. The result is predetermined. The impact projection ("retrofitting could cut X tonnes") is the best part but easily missed. |
| **Teacher** | 3/5 | The data requirements summary is a useful recap. The NREL database reference is real and credible. But the "search" is performative — there's no branching based on student choices. If students selected different features, the result would be the same. This undermines the sense of agency. |

**Improvements:**
- **High priority:** Make the search results actually reference the student's chosen features, e.g., "✓ Floor Area data found in 98,000 records" vs. "⚠️ Weather data found in 72,000 records (some gaps)." This creates the illusion that their choices matter
- The loading animation could vary in timing slightly to feel less scripted
- The impact projection should be more prominent — it's the most motivating element but tucked into a small city-context box

### Step 5: Summary & Handoff
**What happens:** Celebration icon, AI system design summary, 2 quiz questions (why buildings? what's EUI?), journey timeline showing 3 activities, link to Activity 3.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 3/5 | The celebration feels slightly premature — the student hasn't built anything yet. The quiz questions are useful checkpoints but feel like a test at the end of a party. The journey timeline (Investigation ✓ → Data Design ✓ → AI Training: Up Next) is satisfying and creates forward momentum. |
| **Teacher** | 4/5 | The quiz questions are well-calibrated for retention checking. The system design summary is a useful artifact. The journey timeline helps students see the bigger picture. The "Proceed to Activity 3" link maintains flow. Concern: there's no option for teachers to see individual student summaries. |

**Improvements:**
- Move the quiz questions BEFORE the celebration, not after — "answer these to complete" is more motivating than "you're done, now answer these"
- The journey timeline's "AI Training: Up Next" could be more specific: "Learn how AI learns from data → Build your own model"
- Add a "Your Design" downloadable summary for portfolio use

### Activity 2 Summary

| Metric | Score |
|--------|:-----:|
| **Average Student** | **3.7/5** |
| **Average Teacher** | **4.3/5** |
| **Combined** | **4.0/5** |

**Strongest steps:** Step 0 (personalized grant — "whoa" moment), Step 2 (feature selection — good interactivity)
**Weakest steps:** Step 1 (telegraphed sector choice), Step 4 (fake database search)

---

## Activity 3: Understanding AI for Climate Action (7 steps)

### Step 0: Intro
**What happens:** Minimal — heading "How AI Actually Works," single sentence ("In 5 minutes, you'll understand..."), city context if available, "LET'S GO" button.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | Clean and fast. The "5 minutes" promise is motivating — it sets expectations and feels achievable. The city context connecting to previous activities is a nice reminder without being wordy. No wasted time. |
| **Teacher** | 4/5 | Good time-framing for classroom management. The city context maintains narrative continuity. But there's no learning objective stated — students don't know what they'll be able to do after completing this. |

**Improvements:**
- Add a single-line learning objective: "You'll learn to spot patterns like an AI does" — frame it as a skill they're gaining
- The heading "How AI Actually Works" is better than the old "What is AI, Anyway?" but could be even more active: "Think Like an AI"

### Step 1: "You Are The AI" Prediction Game
**What happens:** Three building cards with stats (year, size, climate, efficiency rating). Mystery building below with "?" rating. Student predicts High/Medium/Low. Wrong answers get pattern hints. Correct answer reveals "You just did what AI does!"

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 5/5 | **This is the strongest teaching moment in Activity 3.** The student looks at data, finds a pattern, and makes a prediction — exactly what AI does. The "aha" moment when they get it right ("You just did what AI does!") is genuinely educational AND engaging. The wrong-answer hint is helpful without being condescending. The visual building cards are clean and scannable. |
| **Teacher** | 5/5 | Brilliant pedagogical design. Students learn by doing rather than reading. The pattern (older + bigger + extreme climate = less efficient) is discoverable and memorable. The wrong-answer feedback guides thinking without giving away the answer. This single step teaches the core concept of AI better than any definition could. |

**Improvements:**
- Consider a second round with a different mystery building (e.g., Year: 2020, Size: 20K, Climate: Moderate → High Efficiency) to reinforce the pattern in both directions
- The three training buildings could have slightly more visual differentiation (different card colors for different ratings) to aid visual pattern recognition

### Step 2: Animated Pipeline
**What happens:** Three big INPUT → MODEL → OUTPUT boxes. Student clicks "Feed a Building" 3 times. Each click animates data flowing through: numbers appear in INPUT, gear spins in MODEL, color-coded result appears in OUTPUT. Counter shows progress (1/3, 2/3, 3/3).

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 5/5 | Each click is satisfying — watching data flow left-to-right with the glowing box-shadow transitions and spinning gear feels dynamic. Three different buildings with three different results (Low/High/Medium) reinforce that the same formula produces different outputs. The "Pipeline Complete" summary drives home the core formula. |
| **Teacher** | 5/5 | The INPUT → MODEL → OUTPUT framework is the #1 concept students need from this activity, and this step nails it through repetition-by-doing. Three buildings is the perfect number — enough to see the pattern without getting bored. The animated pipeline makes an abstract concept concrete and memorable. |

**Improvements:**
- The pipeline could briefly flash what the MODEL "noticed" for each building: "Old building → likely low efficiency" — this would make the model's reasoning visible
- Consider adding city-specific building data if the journey state exists ("Feeding a building from [Chicago]...")

### Step 3: How AI Learns (Training Animation)
**What happens:** Single sentence of context. Training flow boxes: INPUT EXAMPLES → MODEL GUESSES → CHECK ANSWER → ADJUST WEIGHTS → LEARNED MODEL. Click "Train the AI" to animate. Accuracy counter climbs (47% → 62% → 78% → 91%). Post-animation highlight box about weights.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The training animation is visual and the climbing accuracy percentage is motivating — students instinctively want to see it hit 91%. The flow boxes lighting up sequentially creates a sense of process. The one-sentence intro is perfect — no wall of text. The post-animation explanation about "weights" is appropriately brief. |
| **Teacher** | 4/5 | Good visualization of the training loop. The accuracy climb from 47% to 91% teaches that AI improves through iteration. The "weights" concept is appropriately simplified. Concern: students only watch — they don't interact with the training process. It's a passive animation after the first click. |

**Improvements:**
- **Medium priority:** Let students click "Train Again" to run a second training cycle (91% → 95%), then a third (95% → 97%) — this teaches diminishing returns and makes the training feel iterative rather than one-shot
- The accuracy labels could include a brief description: "47% — Worse than random!" → "91% — Ready for real buildings"
- Consider showing what the model gets wrong at 47% vs. what it gets right at 91%

### Step 4: Testing the AI (Visual Data Split)
**What happens:** 4x4 grid of 16 building icons. Click "Split the Data" to animate: 12 turn blue (training), 4 turn green (test). Split result panel shows 75%/25% breakdown. Question: "Why test on new buildings?" with two choices.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The animated split is visually clear — watching buildings turn blue then green in sequence is satisfying. The 75/25 breakdown is intuitive. The question after the split is well-timed. The wrong-answer feedback ("like memorizing the answer key") uses a relatable analogy. |
| **Teacher** | 5/5 | Train/test split is a critical ML concept and this step teaches it visually and interactively. The building icons make it concrete. The question tests genuine understanding (not just recall). The "memorizing the answer key" analogy for overfitting is excellent — every student understands that. |

**Improvements:**
- The question could be slightly more nuanced: both answers currently read as obviously right/wrong. "Proves it learned real patterns" is clearly correct language. Consider making the wrong answer more tempting: "Training data gives more accurate results"
- After the correct answer, a one-sentence connection to their work: "That's why the NREL dataset was split in Activity 2"

### Step 5: Interactive Demo (Try It Yourself)
**What happens:** Sliders for Year Built and Floor Area, dropdown for Climate Zone. "Run AI Prediction" button produces color-coded efficiency result with impact translation. Cumulative counter tracks buildings analyzed. Challenge: find High Efficiency. Quiz: what did the model do? Bonus: find the least efficient building.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 5/5 | The sliders are immediately satisfying to play with. The color-coded results (red/yellow/green) create a game-like feel. The challenge to find High Efficiency is motivating — students will try different combinations. The cumulative impact counter ("Buildings analyzed: 7 | CO₂ savings: 1,240 tonnes") gamifies exploration. The city-specific impact translation makes each prediction feel consequential. |
| **Teacher** | 4/5 | Excellent hands-on exploration. Students develop intuition about which features affect predictions. The quiz checks conceptual understanding. The challenge encourages systematic experimentation. Concern: the note says "this uses simplified rules, not real AI" — this is honest but could undermine the learning moment. In Activity 4 they'll use real ML, so the scaffolding is fine. |

**Improvements:**
- The "Bonus: find the LEAST efficient" prompt appears after the quiz, which many students will skip. Move it closer to the demo
- Consider adding a "leaderboard" of predictions: show the top 3 most/least efficient buildings the student found
- The climate zone dropdown could auto-set from the journey state AND explain why: "Pre-set to Cold because [Chicago] has harsh winters"

### Step 6: Final Knowledge Check & Journey Recap
**What happens:** Two quiz questions (3 parts of AI? How do we know it learned?). After both correct: journey recap showing all 3 activities with the student's actual choices. "Climate AI Architect: [City]" badge. Link to Activity 4.

| Perspective | Score | Rationale |
|-------------|:-----:|-----------|
| **Student** | 4/5 | The quiz questions are fair and test the two core concepts. The journey recap is satisfying — seeing all three activities summarized with your actual city name, sector, features, and prediction count creates a sense of accomplishment. The "Climate AI Architect: [Chicago]" badge is screenshot-worthy for teenagers who care about identity artifacts. |
| **Teacher** | 5/5 | The two quiz questions assess the two most important concepts (INPUT→MODEL→OUTPUT and train/test split). The journey recap is an excellent portfolio artifact. The badge motivates completion. The wrong-answer feedback is educational, not punitive. The transition to Activity 4 ("AI Arena") creates excitement for the next challenge. |

**Improvements:**
- The badge should be more visually prominent and literally say "Screenshot this!" — teenagers won't think to do it unless prompted
- The journey recap could show the impact numbers more prominently: "Together, you identified X tonnes of potential CO₂ savings"
- Consider a "Share" button that copies a text summary to clipboard

### Activity 3 Summary

| Metric | Score |
|--------|:-----:|
| **Average Student** | **4.4/5** |
| **Average Teacher** | **4.6/5** |
| **Combined** | **4.5/5** |

**Strongest steps:** Step 1 (prediction game — best teaching moment), Step 2 (pipeline — best visual demo), Step 5 (interactive demo — most engaging)
**Weakest step:** Step 3 (training animation — passive after one click)

---

## Cross-Activity Summary

| Activity | Student Avg | Teacher Avg | Combined |
|----------|:-----------:|:-----------:|:--------:|
| **Activity 1** | 4.0 | 4.3 | 4.1 |
| **Activity 2** | 3.7 | 4.3 | 4.0 |
| **Activity 3** | 4.4 | 4.6 | 4.5 |

### Top 5 Highest-Scoring Steps (Combined)

1. **Activity 3, Step 1** — "You Are The AI" prediction game (5.0/5.0)
2. **Activity 3, Step 2** — Animated pipeline demo (5.0/5.0)
3. **Activity 2, Step 0** — Personalized grant opening (5.0/5.0)
4. **Activity 1, Step 1** — City selection with real API data (4.5/5.0)
5. **Activity 3, Step 5** — Interactive slider demo (4.5/5.0)

### Top 5 Steps Needing Improvement (Combined)

1. **Activity 2, Step 4** — Fake database search (3.0/3.0) — predetermined, no branching
2. **Activity 1, Step 5** — Strategy quiz (3.0/3.0) — leading question, no real choice
3. **Activity 2, Step 1** — Sector selection (3.0/4.0) — answer telegraphed by descriptions
4. **Activity 2, Step 5** — Summary & handoff (3.0/4.0) — celebration before quiz is backwards
5. **Activity 3, Step 3** — Training animation (4.0/4.0) — passive after one click

### Priority Improvements (Highest Impact, Lowest Effort)

| Priority | Change | Effort | Impact |
|:---:|--------|:------:|:------:|
| 1 | **Activity 1 Step 5:** Replace binary strategy quiz with 3-4 genuinely debatable approaches (regulation vs. incentives vs. reporting) | Low | High |
| 2 | **Activity 2 Step 1:** Balance sector card descriptions so Buildings doesn't obviously "win" | Low | Medium |
| 3 | **Activity 2 Step 4:** Make search results reference the student's specific features with varied match percentages | Medium | High |
| 4 | **Activity 3 Step 3:** Add "Train Again" button for iterative cycles (91% → 95% → 97%) | Low | Medium |
| 5 | **Activity 3 Step 1:** Add a second mystery building round to reinforce the pattern | Low | Medium |
| 6 | **Activity 2 Step 5:** Move quiz before celebration, not after | Low | Low |
| 7 | **Activity 1 Step 7:** Add "Copy my report" button for portfolio use | Low | Medium |
| 8 | **Activity 3 Step 6:** Add "Screenshot this!" prompt near badge | Trivial | Medium |

### Cross-Cutting Observations

1. **Activities teach best when students DO the thing, not READ about the thing.** Activity 3's redesign (prediction game, pipeline animation) dramatically outscores Activity 2's text-heavy steps.

2. **Personalization from Activity 1 → 2 → 3 is the strongest engagement driver.** Every step that references the student's city scores higher than generic equivalents.

3. **Quiz questions that have obvious answers don't create learning.** Steps 1-5 in Activity 1 and Step 1 in Activity 2 have "right answer bias" where the correct option is linguistically obvious.

4. **The teacher scores consistently higher than student scores.** This suggests the pedagogical design is strong but the surface-level engagement (UI dynamism, interactivity) has room to grow in Activities 1-2.

5. **Activity 3's redesigned Steps 0-4 prove the "less text, more interaction" principle works.** The average went from an estimated 2.0/5 (pre-redesign) to 4.4/5.

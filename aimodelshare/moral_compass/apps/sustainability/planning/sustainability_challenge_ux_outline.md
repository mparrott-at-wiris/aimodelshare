# Sustainability Challenge: Complete UX/UI Outline

> **Purpose:** A single reference document describing the user experience of every app in the Sustainability Challenge sequence. Written for three audiences: a 12-year-old student, a 17-year-old student, and the 17-year-old's teacher.

---

## Journey Map (9 Activities in Sequence)

| # | Activity | Source File | Format |
|---|----------|-------------|--------|
| 1 | Climate Mission: Investigation | `Activity_1.html` | HTML (client-side) |
| 2 | Climate AI Innovation Lab | `Activity_2.html` | HTML (client-side) |
| 3 | Understanding AI Systems | `Activity_3.html` | HTML (client-side) |
| 4 | Model Building Game (Base) | `model_building_app_en_sustainability.py` | Gradio (server) |
| 5 | Moral Compass Challenge | `moral_compass_challenge_sustainability_en.py` | Gradio (server) |
| 6 | Bias Detective (AI Cost Explorer) | `bias_detective_en_sustainability.py` | Gradio (server) |
| 7 | Fairness Fixer (Green AI Advisor Simulation) | `fairness_fixer_en_sustainability.py` | Gradio (server) |
| 8 | Sustainability Upgrade (Certification) | `sustainability_upgrade_en.py` | Gradio (server) |
| 9 | Model Building Game (Final Variant) | `model_building_app_en_final_sustainability.py` | Gradio (server) |

Data flows forward through `localStorage` (Activities 1-3) and authenticated server state (Activities 4-9).

---

## 1. Activity 1 — Climate Mission: Investigation

**Source:** `Activity_1.html` | **Steps:** 8 (0-7) | **Data:** Climate TRACE satellite API v7

### What happens, step by step

| Step | Title | What the user does |
|------|-------|--------------------|
| 0 | Mission Briefing | Reads two animated climate facts (global temperature milestone, technology exists today), scrolls to reveal each. Accepts the mission. |
| 1 | Select Your City | Types a city name (or taps a suggestion chip: Barcelona, Lleida, Tarragona, Madrid, Cordoba, Andorra, New York, Beijing). The app fetches real emissions data from Climate TRACE satellites. If multiple matches, a disambiguation picker appears. |
| 2 | The Big Picture | Sees total CO2 emissions for 2022 vs 2023, a car-equivalent counter, and a "families affected" counter. Answers a checkpoint quiz: "Did emissions go up or down?" |
| 3 | Sector Breakdown | Animated horizontal bar chart races sectors from smallest to largest. The top sector gets a star badge. Quiz: "Which industry has the highest total emissions?" (4 shuffled options) |
| 4 | Tracking the Sources | Three ranked source cards with animated percentage bars. Tapping a card reveals facility details (coordinates, estimated affected population). Quiz: "Which specific source is the highest emitter?" |
| 5 | Strategic Approaches | Chooses one of 4 strategies (Strict Regulation, Financial Incentives, Public Reporting, Technology Investment). Each choice surfaces trade-off feedback. Animated before/after impact bars show projected emission reductions. |
| 6 | Your Report | Sentence-completion form: picks a strategy from a dropdown, writes a free-text reason why it's urgent. |
| 7 | Mission Complete | Sees their full recommendation quoted. Can copy a formatted report to clipboard. A teaser banner explains their data will carry into Activity 2. Link to proceed. |

**Key interactions:** City search with autocomplete/suggestion chips, progressive-scroll fact reveal, 3 checkpoint quizzes (wrong answers flash red and reset), strategy dropdown, free-text writing, copy-to-clipboard report.

**Personalization:** All data (emissions, sectors, sources, projections) is driven by the student's chosen city. A floating "Decision Log" badge tracks every choice and persists to localStorage for Activity 2.

**Gating:** Each step's "Continue" button is disabled until its quiz/interaction is completed. Wrong answers can be retried indefinitely.

### What a 12-year-old experiences

You become a "Climate Action Investigator." You pick your own city — maybe where you live — and a satellite scans it for pollution. You see which factories and industries pollute the most, shown as colorful bars racing across the screen. At each step you answer a question to prove you understood what you saw. At the end you write advice to your city's leaders about how to fix the problem, and you can copy your report like a real scientist.

### What a 17-year-old experiences

Beyond the game framing, you engage with real satellite emissions data (Climate TRACE) for a city of your choice. You learn to read emissions trends, decompose aggregate data into sector-level and source-level breakdowns, reason about policy trade-offs (regulation vs. incentives vs. transparency vs. technology), and compose a data-backed recommendation. The decision log tracks your analytical reasoning chain.

### What a teacher sees

**Pedagogical purpose:** Data literacy, evidence-based argumentation, environmental science.
**Skills practiced:** Reading data visualizations, interpreting trends, identifying top contributors in a dataset, evaluating policy trade-offs, persuasive writing grounded in data.
**Assessment points:** 3 factual quizzes (trend, top sector, top source), strategy selection with written justification, the final report (copy-able for submission). The Decision Log provides a full audit trail of each student's analytical path.
**Cross-activity continuity:** City, emissions data, strategy, and recommendation are saved to localStorage and used in Activity 2.

**Student Engagement Score: 5/5** — Highly interactive: real city data, animated visualizations, personal choice at every step, culminating in a creative writing task.

**Value to Teacher Score: 4/5** — Strong assessment via the written report and decision log. The quizzes test comprehension. Missing a structured rubric, but the copy-to-clipboard report is easily submittable.

---

## 2. Activity 2 — Climate AI Innovation Lab

**Source:** `Activity_2.html` | **Steps:** 6 (0-5) | **Data:** Carried from Activity 1 via localStorage

### What happens, step by step

| Step | Title | What the user does |
|------|-------|--------------------|
| 0 | Grant Awarded | Reads that the City Council has awarded a $500K "Buildings & Energy" AI Innovation Grant based on their Activity 1 findings. The mission: use AI to find the most energy-wasteful buildings. |
| 1 | The Inspector's Dilemma | A 4-phase progressive reveal: (A) Animated city grid scan classifying buildings as efficient/wasteful/unknown. (B) Inspector math — building count / 10 inspectors = years needed. (C) Animated counters showing families overpaying, CO2 wasted, cars-worth of pollution while waiting. (D) The AI promise: "Your AI could analyze ALL buildings in minutes, not years." |
| 2 | Teach Your AI | Selects the 3 best "clues" (features) for predicting building energy use from 6 cards: Floor Area, Weather Data, Year Built (correct); Elevation, Owner's Name, Number of Floors (wrong). Wrong picks fade to grey with an explanation. After 2 wrong picks, a hint appears. |
| 3 | Define the Energy Score | Chooses between "Total energy used" and "Energy per square metre (EUI)." Wrong choice gets a gentle correction. Correct reveals an EUI Matchup Game — 2 rounds of "which building wastes more per m2?" comparing small-but-wasteful vs. large-but-efficient buildings. |
| 4 | Find the Data | A "Search for Data" button triggers an animated database search sequence (progress bar, checkmarks for each feature, NREL database connection). Result: "MATCH FOUND — 100,000 building records from NREL." |
| 5 | Summary & Handoff | Reviews the full AI system design (focus, features, prediction target, dataset). Answers 2 quiz questions: "Why can't cities just send inspectors?" and "What does EUI measure?" Celebration area shows a journey timeline (Investigation → Data Design → AI Training). Link to Activity 3. |

**Key interactions:** 4-phase progressive reveal buttons, clickable feature selection cards (max 3 correct from 6), building comparison matchup cards, animated database search, 2 comprehension quizzes.

**Personalization:** City name, building count estimate (derived from emissions/50), emission-derived impact projections — all carried from Activity 1 via localStorage. If no Activity 1 data, generic fallbacks are used.

**Gating:** Step 1 requires clicking through all 4 phases. Step 2 requires all 3 correct features selected. Step 3 requires EUI selected + both matchup rounds completed. Step 4 requires running the animated search. Step 5 requires answering both quizzes (correctness not required — any answer unlocks).

### What a 12-year-old experiences

The city gives you $500,000 to build an AI that finds buildings wasting energy. First, you see why inspectors can't do it (it would take years!). Then you pick the 3 best clues your AI should look for — like how old a building is, how big it is, and what the weather is like. You learn about EUI (energy per square metre) by playing a matchup game where you guess which building is actually worse. Then your AI finds a real database with 100,000 buildings to learn from.

### What a 17-year-old experiences

You design a feature selection strategy for a machine learning system. The Inspector's Dilemma frames the computational motivation for ML (scaling a classification problem beyond human capacity). The feature selection exercise teaches the difference between predictive and non-predictive variables. EUI introduces the concept of normalization for fair comparison. The NREL database search introduces the idea of finding real training data that matches your model design.

### What a teacher sees

**Pedagogical purpose:** Introduction to AI system design, feature engineering, data normalization, real-world datasets.
**Skills practiced:** Distinguishing useful vs. irrelevant features, understanding normalization (EUI vs. raw totals), evaluating data sources, connecting problem definition to data requirements.
**Assessment points:** Feature selection (self-correcting — wrong picks are permanently disabled), EUI matchup rounds, 2 comprehension quizzes.
**Cross-activity continuity:** Builds on Activity 1's city data. Selected features, prediction target, and completion status are saved for Activity 3's personalization.

**Student Engagement Score: 4/5** — The inspector dilemma is compelling, and the matchup game adds interactivity. The database search animation is satisfying but passive.

**Value to Teacher Score: 4/5** — Excellent for teaching feature selection and normalization concepts. The wrong-feature explanations are pedagogically strong. The 2 final quizzes provide quick comprehension checks.

---

## 3. Activity 3 — Understanding AI Systems

**Source:** `Activity_3.html` | **Steps:** 7 (0-6) | **Data:** Carried from Activities 1-2 via localStorage

### What happens, step by step

| Step | Title | What the user does |
|------|-------|--------------------|
| 0 | Intro | Reads a promise: "In 5 minutes, you'll understand what an AI system is, how it learns, and how to test it." Personalized context banner if city data exists. |
| 1 | "You Are The AI" | A prediction game with a mystery building. Three training buildings show year, size, climate, and efficiency rating. The student predicts the mystery building's rating. Round 1: old, big, cold = Low Efficiency. Round 2: new, small, moderate = High Efficiency. Wrong answers show pattern-matching hints. |
| 2 | The Three-Part Formula | An animated pipeline demo: INPUT → MODEL → OUTPUT. The student clicks "Submit Building Data" 3 times. Each time, a building's data flows through the 3 stages with glowing animations (data in → processing/gear → prediction out). |
| 3 | How AI Learns | 3 training cycles with animated accuracy progression: Cycle 1 reaches 91%, Cycle 2 reaches 95%, Cycle 3 reaches 97%. Each cycle lights up 5 boxes in sequence (Input Examples → Model Guesses → Check Answer → Adjust Settings → Learned Model). Diminishing returns become visible. |
| 4 | Testing the AI | A 4x4 building grid is animated: first 12 icons turn blue (75% training), last 4 turn green (25% test). A comprehension question asks why testing on hidden data matters. Correct answer: "Proves it learned real patterns" (not just memorization). |
| 5 | Try It Yourself | Interactive prediction demo with 3 controls: Year Built slider (1920-2024), Floor Area slider, Climate Zone dropdown. "Run AI Prediction" produces a color-coded efficiency rating. A challenge card asks: "Can you find High Efficiency settings?" A quiz asks what the model did. |
| 6 | Final Knowledge Check | 2 quizzes: "What are the 3 parts of every AI system?" (Input → Model → Output) and "How do we know the AI really learned?" (Test on unseen data). Both must be answered correctly to see the celebration area, journey recap, and link to Activity 4. |

**Key interactions:** Prediction buttons (2 rounds), pipeline animation (3 submissions), training animation (3 cycles), data-split animation, sliders + dropdown for interactive prediction, quiz cards.

**Gating:** Each step requires completing its interaction before Next unlocks. Wrong quiz answers flash red and can be retried.

### What a 12-year-old experiences

You become the AI! You look at 3 buildings and guess if a mystery building wastes energy — just by spotting a pattern (old + big + cold = wasteful). Then you watch data flow through a pipe: information goes in, the AI brain processes it, a prediction comes out. You train the AI 3 times and watch its accuracy climb from 47% to 97%. You split buildings into a practice group and a secret test group. Finally, you get sliders to control the AI yourself — adjusting year, size, and climate to see predictions change live.

### What a 17-year-old experiences

You learn the foundational ML framework: Input → Model → Output. The prediction game demonstrates pattern recognition (the core of what ML does). The pipeline demo makes the abstraction concrete. The training loop introduces iterative optimization and diminishing returns. The data split visualizes train/test methodology and why it matters (overfitting vs. generalization). The interactive demo connects features to predictions and introduces the idea of a decision boundary.

### What a teacher sees

**Pedagogical purpose:** Core ML concepts — the prediction pipeline, iterative training, train/test split, overfitting.
**Skills practiced:** Pattern recognition, understanding the Input → Model → Output framework, recognizing diminishing returns in training, understanding why test data must be "unseen," manipulating variables to observe output changes.
**Assessment points:** 2-round prediction game (gated), data-split comprehension question (gated), Step 5 quiz on model behavior, 2 final knowledge-check quizzes (both must be correct).
**Cross-activity continuity:** Journey recap summarizes Activities 1-3. Data is saved for Activity 4 personalization. The link teases the Model Building Arena.

**Student Engagement Score: 5/5** — The "You Are The AI" game, animated pipeline, training loop, and slider-based prediction tool make every concept tactile and visual.

**Value to Teacher Score: 5/5** — Rich assessment: 6 gated interactions across 7 steps, each testing a specific ML concept. The Step 5 prediction tool doubles as a sandbox for exploration. The journey recap provides a self-assessment artifact.

---

## 4. Model Building Game (Base)

**Source:** `model_building_app_en_sustainability.py` (~2,037 lines) | **Format:** Gradio Blocks app | **Task:** Binary classification — predict high vs. low EUI buildings (WiDS/NREL dataset)

### What happens

**5 onboarding modules (0-4), then the Arena.**

| Module | Title | What the user sees/does |
|--------|-------|-----------------------|
| 0 | Welcome | Typewriter-animated mission briefing: "Build an AI that predicts which buildings waste the most energy." Two animated stat cards: "40% of global emissions from buildings" and "10 attempts to build the best model." |
| 1 | Your Mission | Explains EUI (Energy Use Intensity) with a visual formula card. Green vs. red comparison (Low EUI = Efficient, High EUI = Wasteful). Team assignment. |
| 2 | Your 4 Controls (gated) | A 2x2 grid of clickable control cards. Must tap all 4 to proceed. Each reveals a detail panel: (1) Model Strategy — 4 model types shown as cards. (2) Complexity — slider 1-10 with dynamic description. (3) Data Ingredients — feature toggle chips. (4) Data Size — 4 radio cards with donut charts. Progress tracker: "X/4 explored." |
| 3 | Rank System (gated) | 4-column rank bar: Trainee → Junior → Senior → Lead, showing what each unlocks. Scoring explanation ("25% of data is hidden in a test vault"). Gating quiz: "What happens when you rank up?" Must answer correctly. |
| 4 | Systems Online | Rocket emoji, workflow recap (Pick model → Set complexity → Choose data → Submit). "You have 10 tries." Competition info (2 leaderboards). Explanation that 50% accuracy = coin flip baseline. "Enter the Arena" button. |

**The Arena (2-column layout):**
- **Left column — Controls:** Model Strategy (radio), Complexity (slider with tooltip), Data Ingredients (checkboxes), Data Size (radio), Attempts Tracker ("X/10"), Submit button.
- **Right column — Feedback & Leaderboards:** Submission feedback (5-step progress animation, then KPI card with accuracy, change, rank), tabbed leaderboard (Team + Individual standings).

**Rank progression (submission-count driven):**

| Submissions | Rank | Unlocks |
|-------------|------|---------|
| 0 | Trainee | 1 model, complexity ≤3, 4 base features, Small data only. All controls locked — just click Submit. |
| 1 | Junior | 3 models, complexity ≤6, +3 location features, Small + Medium data. Controls become interactive. |
| 2 | Senior | All 4 models, complexity ≤8, +7 weather features (all 14 available), all data sizes. |
| 3+ | Lead | All tools, complexity ≤10. Full freedom. |

**10 attempts per session.** After limit: controls lock, submit button changes to "Limit Reached," red banner directs to "Finish & Reflect."

**Scoring:** Pre-computed predictions from SQLite cache. Accuracy = % of hidden test-vault buildings classified correctly. Cloud leaderboard via AWS playground API.

**Conclusion screen:** Performance snapshot (best accuracy, rank, submissions, improvement delta, tier progress, which strong predictors were used). Teaser: "Every AI model has a cost beyond its accuracy score."

### What a 12-year-old experiences

You're an AI Engineer now! You get assigned to a team and enter a lab where you build an AI to find wasteful buildings. At first, you just press one button and see what happens. After each try, you unlock new tools — different AI brains, more data, more control. A leaderboard shows how you compare to other students and teams. You get 10 tries to make your AI as smart as possible. It feels like leveling up in a video game.

### What a 17-year-old experiences

You systematically explore how model type (logistic regression, decision tree, KNN, random forest), complexity (regularization strength / tree depth / k), feature selection, and training data size affect classification accuracy. The rank-gating scaffolds the exploration: you start simple and progressively add variables. The "change ONE setting at a time" advice teaches controlled experimentation. The leaderboard creates competitive motivation while team standings encourage peer collaboration.

### What a teacher sees

**Pedagogical purpose:** Hands-on ML model building, controlled experimentation, understanding bias-variance tradeoff, collaborative competition.
**Skills practiced:** Hypothesis-driven experimentation, evaluating model accuracy, understanding how model complexity affects performance, feature importance reasoning, interpreting leaderboard standings.
**Assessment points:** Module 2 exploration (all 4 controls gated), Module 3 quiz, 10 arena submissions with full accuracy history on the leaderboard, conclusion screen with performance metrics.
**Cross-activity continuity:** Best accuracy score feeds into the Moral Compass Score formula in Activities 5-8.

**Student Engagement Score: 5/5** — Gamified with rank-ups, team competition, live leaderboard, attempt limits creating urgency, and progressive unlocking.

**Value to Teacher Score: 5/5** — The leaderboard provides a complete audit trail of every student's experimentation path. The rank system ensures scaffolded learning. The 10-attempt limit prevents mindless clicking and encourages strategic thinking.

---

## 5. Moral Compass Challenge

**Source:** `moral_compass_challenge_sustainability_en.py` (~1,783 lines) | **Format:** Gradio Blocks app (module-based Previous/Next navigation, same architecture as Bias Detective and Fairness Fixer) | **Graded quizzes:** 0 (narrative-only — no score changes)

### What happens

**4 modules (0-3) with full Gradio navigation, top dashboard, leaderboard, and rich client-side animations. The app uses session-based auth (same pattern as detective/fixer), fetches real accuracy and rank from the competition API, and syncs a baseline Moral Compass record on load. CSS design system uses `mcc-*` prefix with light/dark mode support.**

| Module | Title | What the user sees/does |
|--------|-------|-----------------------|
| 0 — Certification Day | Celebration → Checklist Failure | **Phase 1 (on load):** Typewriter heading animates "Your AI Model Is Ready for the Real World" letter by letter. After typewriter completes, two stat cards fade in: real Model Accuracy (%) and real Global Rank (#), both fetched from the competition API. An achievement box celebrates: "You built an AI that predicts which buildings waste energy. Real satellite data. Real predictions. That's real engineering." A pulsing green CTA: "CERTIFY MY MODEL →". **Phase 2 (after CTA click):** CTA disappears, replaced by an animated certification checklist with staggered 1-second delays. Items resolve one by one: ✅ Model architecture validated → ✅ Accuracy verified → ✅ Global ranking confirmed → ✅ Dataset compliance checked → ❌ **Environmental Impact Audit — FAILED** (flashes red 3 times). A warning banner slides in: "CERTIFICATION BLOCKED. Before we can certify you as an AI Engineer, you must pass the Environmental Impact Audit. Your model is accurate. But accuracy is only half the story." |
| 1 — The Hidden Bill | 3 Tap-to-Unlock Audit Sections | Header: "Environmental Impact Audit — The Hidden Bill." Progress indicator: "0/3 audited" → "3/3 audited." Three locked cards (padlock icon + "Tap to reveal"). Tapping each card flips it open to reveal audit findings. Next button activates after all 3 are unlocked. **Section 1 — Training Cost:** "What does it cost to train an AI?" An animated horizontal bar chart appears with staggered delays: Your Model (hairline bar, "≈ 3 phone charges"), GPT-3 (small bar, "1,287 MWh — 120 homes/yr"), GPT-4 (fills most of the width, "62,000 MWh — 5,400 homes/yr"), Next-gen 2025+ (overflows container, striped/pulsing, "???"). The visual contrast between "your model" and GPT-4 is the punchline. **Section 2 — Inference Cost:** "Training happens once. Using it never stops." 3 stat cards appear: ~0.5L water/prompt (= 1 water bottle), ~10 Wh energy/prompt (= 9 seconds of TV), ~0.4g CO₂/prompt. A client-side prompt slider (1–50 prompts/day) dynamically updates water bottles/day, phone charges/day, and grams CO₂/day. Kicker: "Now multiply by 200 million users. GPT-4's entire training cost? Matched in just 11 days." **Section 3 — The Global Picture:** "The industry you just joined." 2 knockout stat cards: ⚡ "AI data centers now use more electricity than the entire United Kingdom" (~200 TWh/yr) and 💧 "AI's water footprint rivals all the bottled water on Earth" (~540B liters/yr). Closer: "These numbers grow every year. As an AI Engineer, your choices shape whether they keep growing — or start falling." Sources: UC Riverside, IEA, MIT, VU Amsterdam (2024–2025). **After all 3 unlocked:** Cards turn warning-colored. Summary: "This is the hidden cost of AI. Your model is accurate — but accuracy is not the whole picture." |
| 2 — Score Reset | Gauge Drain → What-If Formula Slider | **Phase 1 — Score Reset (on load):** Blinking red header: "RECALCULATING YOUR SCORE..." A large circular gauge (CSS conic-gradient) displays the student's real accuracy. The gauge drains from score to 0 over ~2 seconds: ring animates green → empty, counter decrements in center (e.g. 87 → 85 → ... → 0), score text turns red at 0, header stops blinking and reads "SCORE RESET TO ZERO." Message fades in: "Your accuracy stands at [X]%. But your Moral Compass Score is now 0.000. Why? Because your score now includes Sustainability — and yours is zero." **Phase 2 — Formula (revealed after gauge animation):** Dashed-border formula box: **Moral Compass Score = [ Accuracy ] × [ Sustainability % ]**. "If your Sustainability % is 0%, your Moral Compass Score is 0." A client-side what-if slider (0%–100% Sustainability) calculates `[real accuracy] × [slider %] = [result]` live. Color coding transitions: red at 0% → amber at ~40% → green at 70%+. Messages at key points: 0% = "That's where you are now." / 50% = "Halfway there — already making a difference." / 100% = "Full marks. This is what a responsible AI Engineer looks like." |
| 3 — Mission Briefing | Mission Cards + Leaderboard + CTA | Header: "Your Sustainability Missions." Subtext: "Complete these two missions to earn Sustainability % and restore your Moral Compass Score." **2 mission preview cards** in a grid: (1) 🔍 **Green AI Detective** (blue accent) — "Investigate AI's true environmental cost — from a single prompt to the entire planet. 4 investigations · 4 quizzes · Earn up to 40% Sustainability." (2) 🛡️ **Green AI Advisor** (green accent) — "The mayor picked you to protect your city from a polluting AI company. Make 5 critical decisions. 5 rounds · 6 quizzes · Earn up to 60% Sustainability." **Score summary bar:** "Moral Compass Score: 0.000 · Sustainability: 0% · Accuracy: [X]%." **Leaderboard** (Team + Individual tabs — same component as detective/fixer, updated on navigation to this module). **CTA:** "BEGIN SUSTAINABILITY AUDIT →" triggers a full-screen transition overlay: seedling icon, "Next up: investigate AI's environmental footprint as a Green AI Detective." Close button. The overlay also sends a `postMessage('activity_complete')` to the parent frame. |

**Top dashboard (persistent across modules):** Moral Compass Score (3 decimals) · Team Rank · Global Rank · Course Progress bar (%). Same renderer as detective/fixer. Updates on every module navigation.

**Collapsible formula box** below modules: `<details>/<summary>` element showing the Moral Compass Formula (Accuracy × Sustainability %). Always accessible.

**Key animations:** Typewriter heading (letter-by-letter, ~50ms per character), staggered stat card fade-ins, certification checklist with 1-second staggered delays and red flash on failure, flip-card reveal (front → back), animated horizontal bar chart with staggered widths, circular gauge drain (conic-gradient + JS counter decrement at 30ms intervals), blinking header, pulsing CTA button, `mccSlideUp` entrance animation on all content blocks.

**Key client-side interactions (HTML/JS, not Gradio):** Prompt slider (1–50 range input → dynamic stat update), what-if sustainability slider (0–100 range input → live formula calculation with color transitions), card flip (3 locked sections), certification checklist (auto-play sequence), gauge drain (auto-play on module enter).

**Personalization:** Student's real model accuracy and leaderboard rank are fetched from the competition API via session-based auth. All dynamic values (accuracy display, rank, gauge starting score, formula calculation base) are injected post-auth via a hidden `gr.HTML` component using the `<img onload="...">` pattern. Falls back to demo values (75%, rank #N/A) with a visible "Demo Mode" banner if auth fails or accuracy is 0.

**CSS design system (`mcc-*` prefix):** Same variable structure as detective (`ace-*`) and fixer (`cto-*`). Amber/warning accent tone for the "audit" theme. Light/dark mode support via `@media (prefers-color-scheme: dark)` + `.dark` class. Glassmorphism cards, Outfit font. Unique styles: gauge animation (`mccGaugeDrop` keyframes), checklist animation (`mccCheckFlash`), card flip (`.flipped` class toggle), bar chart (staggered width transitions), pulsing CTA (`mccPulse`).

### What a 12-year-old experiences

You think you've won — your AI is amazing and you're about to get certified! A typewriter types out "Your AI Model Is Ready for the Real World" and your real accuracy and rank appear. You click "CERTIFY MY MODEL" and a checklist starts ticking off items one by one — architecture ✅, accuracy ✅, ranking ✅, compliance ✅ — but then the last item flashes red: ❌ Environmental Impact Audit — FAILED. "CERTIFICATION BLOCKED." Whoa.

Now you're an auditor. You tap three locked cards to reveal what AI really costs: your tiny model used barely any energy, but GPT-4 used enough electricity for 5,400 homes. A slider shows that at 50 prompts a day, you'd use 25 liters of water. And globally? AI uses more electricity than the entire UK. Every card you unlock makes it clearer.

Then a gauge shows your score draining from your accuracy all the way down to zero while a red counter blinks. Your Moral Compass Score is now 0.000. But there's a formula — if you earn Sustainability points, your score comes back. You drag a slider and watch your potential score climb from red to green. The final screen shows two missions ahead: Detective (investigate AI's cost) and Advisor (protect your city from a polluting company). Game on.

### What a 17-year-old experiences

The "certification day" bait-and-switch dramatizes a genuine ethical tension in AI: optimizing for accuracy alone ignores externalities. The animated checklist builds false confidence before the "Environmental Impact Audit — FAILED" punchline. Module 1's three audit sections move from personal scale (your model vs. GPT-4) through per-query costs (the prompt slider makes abstract watts/liters tangible) to global infrastructure impact (AI > UK electricity, water rivaling global bottled supply). The data comes from peer-reviewed sources (UC Riverside, IEA, MIT, VU Amsterdam, 2024-2025).

The gauge drain in Module 2 makes the score reset visceral — watching a number you earned decrement to zero. The Moral Compass Formula formalizes multi-objective optimization: accuracy alone is necessary but not sufficient. The what-if slider creates an immediate "I can fix this" motivation by showing exactly how sustainability points restore the score. Module 3's mission preview cards provide a clear roadmap with concrete deliverables (4 investigations + 4 quizzes for 40%, 5 rounds + 6 quizzes for 60%), and the live leaderboard shows where you stand relative to peers.

### What a teacher sees

**Pedagogical purpose:** Ethical awareness, hidden costs of technology, multi-objective evaluation, emotional engagement through narrative surprise, motivation for the subsequent graded activities.
**Skills practiced:** Connecting technical achievement to real-world impact, understanding that optimization metrics have blind spots, recognizing the environmental costs of computing at personal and global scale, interpreting the Moral Compass Formula as a constrained optimization problem.
**Assessment points:** No quizzes or graded interactions — this is purely narrative/emotional. The top dashboard and leaderboard provide real-time progress visibility. The assessment comes in Activities 6-7 where students earn Sustainability % points through graded quizzes.
**Cross-activity continuity:** Introduces the Moral Compass Formula (Accuracy × Sustainability %) that will be scored in Activities 6-7. Previews both missions with specific task counts and percentage breakdowns. The transition overlay signals the detective app. The leaderboard (same component as detective/fixer) provides continuity across all three Gradio apps.

**Student Engagement Score: 5/5** — The bait-and-switch certification narrative is emotionally powerful. The staggered checklist builds genuine suspense. The three tap-to-unlock audit cards create discovery moments. The gauge drain is dramatic. The what-if slider turns despair into agency. The mission preview cards create anticipation for what's next. Students remember this activity.

**Value to Teacher Score: 4/5** — No graded quiz outputs, but significantly richer than a simple 4-step story. The interactive prompt slider and what-if formula slider create genuine engagement with the data. The top dashboard and leaderboard provide real-time class visibility. The audit content (training costs, inference costs, global picture) previews the detective's curriculum. The module-based navigation with Previous/Next ensures students engage with every section rather than clicking through quickly.

---

## 6. Bias Detective (AI Cost Explorer)

**Source:** `bias_detective_en_sustainability.py` (~1,844 lines) | **Format:** Gradio Blocks app | **Graded quizzes:** 4 (task IDs t1-t4)

### What happens

**6 modules (0-5) investigating AI's environmental impact from personal to global scale. Dashboard tracks progress in two phases: "PHASE 1: Individual Impact" (modules 0-3) and "PHASE 2: Global Scale" (modules 4-5).**

| Module | Title | What the user sees/does |
|--------|-------|-----------------------|
| 0 | What Does AI Really Cost the Planet? | Full-screen intro page with typewriter effect: "Every time you use AI, something invisible happens..." Staggered reveal animations. |
| 1 | Every Single Prompt | **Expert-first layout:** Opens with an OEIAC (UdG) ethics reference banner — "We follow expert guidance from the Catalan Observatory for Ethics in AI (OEIAC), which defines 7 core principles of safe AI. This investigation focuses on **Sustainability**." A collapsible `<details>` panel lists the other 6 principles (Justice & Equity, Transparency & Explainability, Security & Non-maleficence, Responsibility & Accountability, Autonomy, Privacy). **Typewriter heading** reveals: "One question to ChatGPT = one bottle of water" then fades in the content below. **Interactive prompt calculator:** A slider (1-200 prompts/day) dynamically updates 3 stat cards: water used (L + bottles), energy used (kWh + TV seconds), CO2 emitted (g + km driven/yr). A toggle button reveals a Google Search vs. AI Prompt energy comparison bar chart (AI = ~30x more energy). **Quiz (t1):** "A classmate says 'that's basically nothing.' What's the strongest counter?" Correct: scale — 200M users x 50+ prompts/day = billions of liters and terawatt-hours per year. |
| 2 | Training the Beast | Intro: "Training GPT-3 alone used enough electricity to power 120 U.S. homes for a year." **3 model buttons:** GPT-3 (2020), GPT-4 (2023), Llama 3 (2024). Tapping each reveals a glassmorphism training footprint card with 3 metrics (energy in MWh, water in millions of liters, CO2 in tons) plus a relatable fun fact. GPT-3: 1,287 MWh / 0.7M L / 502 tons ("driving a car around the Earth 60 times"). GPT-4: 62,000 MWh / 34M L / 24,000 tons ("~5,400 U.S. homes' annual electricity"). Llama 3: 39,000 MWh / 21M L / 15,000 tons ("8 Olympic swimming pools"). **Animated energy bars** show exponential growth: GPT-3 at 2% width (1,287 MWh), GPT-4 at 48% (~62,000 MWh), "Next-gen 2025+" at 100% with "???". **Quiz (t2):** "GPT-4 used ~62,000 MWh for training — that's 48x more than GPT-3. But after training, users send 200M+ queries/day. Which costs more over time?" Correct: inference overtakes training within days because low-cost-per-query x massive volume = total energy that dwarfs training. |
| 3 | Water: The Hidden Cost | Intro: "A 2025 study found AI's global water footprint could reach 312 to 764 billion liters per year — comparable to the entire world's annual bottled water consumption. Only 0.5% of Earth's water is accessible freshwater." **Animated water bar visualization:** 50 vertical bars fill in a staggered wave pattern (each bar ~15 billion liters). 2 stat cards: "5M gallons/day — one large data center = a town of 50,000 people" and "56% deficit by 2030 — global freshwater gap — AI is making it worse." **Client-side quick quiz** (ungraded, 4 options): "Where does data center cooling water come from?" Correct: freshwater from rivers, groundwater & municipal supplies. Wrong answers get immediate colored feedback. **Quiz (t3):** "A single large data center uses 5 million gallons of freshwater per day, and only 0.5% of Earth's water is accessible freshwater. Why does AI's water use raise environmental justice concerns?" Correct: data centers consume freshwater from the same rivers and aquifers that communities depend on — often in drought-prone areas. |
| 4 | Zoom Out | Intro: "Data centers already use about 1.5% of global electricity — projected to nearly triple by 2030. The U.S. alone holds 45.6% of the world's data centers." **4 tabbed stat displays** (switch by clicking emoji icons): (1) AI's total energy in 2025: ~200 TWh/yr = entire UK's electricity. (2) AI's CO2 emissions: ~56M tons/yr = New York City's annual emissions. (3) AI's water footprint: ~540B liters/yr = global bottled water consumption. (4) Data centers by 2030: ~945 TWh = between Japan and Russia's total. **Energy breakdown bars:** Servers (GPUs, CPUs) 60%, Cooling systems 25%, Networking 5%, Storage 5%, Other (lighting, etc.) 5%. **Quiz (t4):** "AI data centers already use ~1.5% of global electricity, projected to nearly triple by 2030. Dublin banned new data centers in 2022 because they threatened 18% of Ireland's grid. What does this tell us?" Correct: AI's energy appetite competes with entire countries for electricity, forcing governments to choose between tech growth and grid stability. |
| 5 | Your Move (Action Plan) | **5 toggle-able action pledge buttons** with checkbox styling: Google it first (-30%), Be specific (-15%), Use smaller models (-25%), Stay aware (-20%), Tell a friend (-10%). Each button shows the action, a short description, and the reduction percentage. A dynamic "Footprint Reduction Score" card tallies selected percentages (max 100%) with tiered encouraging messages (0%: "Select some actions", ≤30%: "A solid start!", ≤60%: "Nice!", ≤90%: "You're basically an AI sustainability advocate!", 100%: "Maximum impact!"). **"The Takeaway" card** with green border: "AI is powerful. AI is useful. But AI is not free. Every prompt costs real water and real energy. Being aware is the first step — you just took it." Sources: UC Riverside, IEA, MIT, VU Amsterdam (2024-2025). No quiz — purely reflective. |

**Click-to-reveal formula box** at the bottom: collapsible `<details>/<summary>` element showing the Moral Compass Formula (Accuracy x Sustainability %). Always accessible.

**Moral Compass Score updates:** Each correct quiz answer calls the API to update the student's score. Score = Accuracy x (completed tasks / 10). With 4 quizzes here (t1-t4), completing all 4 adds 40% of their accuracy to their Moral Compass Score. Wrong answers show a retry hint ("Re-read the evidence above and think about what the data specifically shows") but don't update the score.

**Quiz format — evidence-based counter-argument:** Each quiz presents a real claim or statistic, then asks the student to evaluate arguments. Three options per quiz: one correct evidence-based answer and two plausible-sounding distractors (one overstating, one understating the problem). This trains nuanced reasoning — neither panic nor dismissal.

### What a 12-year-old experiences

You become a detective investigating what AI really costs the planet. First, a typewriter types out "One question to ChatGPT = one bottle of water" — whoa! Then you play with a slider to see how many water bottles your daily AI chats use up — at 200 prompts a day, that's over 100 bottles and enough CO2 to drive a car 30 km. Next you tap on GPT-3, GPT-4, and Llama 3 to see their training footprint — GPT-4 used enough electricity for 5,400 homes and could fill 8 Olympic swimming pools with water. You watch a wave of 50 bars fill up showing how much water AI drinks globally. You zoom out to see that AI uses as much energy as the entire UK. At the end, you pledge actions to reduce your footprint — like using Google search instead of AI for simple questions — and watch your reduction score climb.

### What a 17-year-old experiences

You engage with real research data (UC Riverside, IEA, MIT, VU Amsterdam, 2024-2025) on AI's per-prompt costs, training costs, water consumption, and global energy footprint. The OEIAC ethics framework (from the University of Girona) grounds the investigation in an established European AI ethics standard — Sustainability is one of 7 formal principles. The prompt calculator makes abstract numbers personal by converting watts and liters into TV seconds, water bottles, and kilometers driven. The training comparison contextualizes exponential growth: GPT-4 used 48x more energy than GPT-3, and inference overtakes training in just days. The environmental justice angle (Mesa, Arizona drought vs. Microsoft's water use) introduces equity dimensions. The global-scale tabs reframe AI infrastructure as a geopolitical issue (Dublin's 2022 data center ban, Ireland's 18% grid threat). The action plan connects personal behavior to systemic impact with quantified percentages.

### What a teacher sees

**Pedagogical purpose:** Environmental literacy, quantitative reasoning, scale comprehension, ethical analysis, civic engagement, alignment with OEIAC AI ethics framework.
**Skills practiced:** Interpreting per-unit statistics and scaling them, comparing orders of magnitude (prompt → training → global), analyzing environmental justice trade-offs, evaluating competing claims with evidence, making evidence-based commitments.
**Assessment points:** 4 graded quizzes (each updates the Moral Compass Score and leaderboard), the prompt calculator interaction, model comparison exploration, the ungraded water-source MCQ, action pledge selections. Each graded quiz tests a different conceptual level: personal scale (t1), training vs. inference (t2), environmental justice (t3), geopolitical impact (t4).
**Cross-activity continuity:** Quiz completions accumulate toward the Moral Compass Score. The formula box reinforces the scoring system. The leaderboard updates in real-time. The OEIAC expert reference establishes the ethical framework that carries into Activity 7 (Fairness Fixer).

**Student Engagement Score: 4/5** — The typewriter heading reveal and prompt calculator slider are immediately engaging. The model buttons with fun-fact footprint cards add discovery. The animated water bars are visually striking. Module 5's action pledges with a climbing score feel empowering. The tabbed global stats could feel like reading for younger students.

**Value to Teacher Score: 5/5** — 4 graded quizzes provide clear assessment data across four conceptual levels (personal → training → justice → geopolitical). The OEIAC ethics reference provides academic grounding. The Moral Compass Score provides a single trackable metric. The leaderboard shows class-wide progress. The evidence-based counter-argument quiz format directly trains critical reasoning skills.

---

## 7. Fairness Fixer (Green AI Advisor Simulation)

**Source:** `fairness_fixer_en_sustainability.py` (~1,973 lines) | **Format:** Gradio Blocks app | **Graded quizzes:** 5 (task IDs t5-t9, one per round) + 1 on results (t10)

### What happens

**7 modules (0-6): Title screen, 5 decision rounds, results.**

| Module | What the user sees/does |
|--------|------------------------|
| 0 — Title: GREEN AI ADVISOR | "The mayor just picked YOU as the city's Green AI Advisor! A company called NovaMind wants to build a giant AI data center here." Baseline pollution stats in relatable units: 14,400 homes/year energy, 89 pools/year water, 4,800 cars/year CO2, Green Score 8/100. "Reduce each number to green levels and protect your city!" |
| 1 — Round 1: The Cooling Crisis | NovaMind's plan uses 89 swimming pools of water every year just to keep computers cool — and the city is running out of water. 3 choices: (Best) Dunk Servers in Special Liquid — eliminates water use, -35% energy. (Good) Reuse Water + Use Cold Air — saves about half the water. (Poor) Just Add Sensors to What Exists — cheapest, barely changes anything. |
| 2 — Round 2: Where Does the Power Come From? | NovaMind would plug into dirty power — 65% fossil fuels. Every AI question burns more gas and coal. 3 choices: (Best) Build a Solar Farm + Batteries — solar panels + nighttime batteries, NovaMind owns it forever. (Good) Buy Clean Energy from a Wind/Solar Farm — sign a deal for clean electricity. (Poor) Pay for Carbon Offsets — looks good on paper, pollution stays the same. |
| 3 — Round 3: Right-Sized AI | NovaMind uses its biggest AI model for every question, even "What's the weather?" 8 out of 10 questions don't need the biggest one. 3 choices: (Best) Match Model Size to Question Difficulty — small model for easy, medium for tricky, biggest for hardest (50x less energy for easy questions). (Good) Train a Smaller, Smarter AI — one medium model good enough for 90% of questions. (Poor) Just Save Repeat Answers — biggest model still runs for everything new. |
| 4 — Round 4: Location, Location, Location | NovaMind wants to build in a hot desert because land is cheap. But desert heat = way more cooling, and the local grid runs on gas. 3 choices: (Best) Build in Cold Scandinavia (Sweden/Finland) — freezing air cools for free, 95% clean electricity. (Good) Build in Rainy Oregon — mild weather, hydropower from rivers. (Poor) Stay in the Hot Desert — cheap land but 3x cooling costs, gas grid erases gains. |
| 5 — Round 5: Honesty Check | Most AI companies keep pollution numbers secret. New laws are coming. 3 choices: (Best) Live Public Scoreboard — real-time energy/water data, total honesty. (Good) Yearly Report Card — annual aggregated data, bare minimum. (Poor) Only Share What the Law Forces — hide as much as possible, call it a "business secret." |
| 6 — Your Advisor Report | Letter grade (A+ to F) with descriptive tier (Legendary/Excellent/Great/Decent/Needs Work/Critical). 2 SVG progress rings (Green Score out of 100, Best Choices out of 5). "What Your Choices Changed" impact summary in relatable units (homes of energy saved, swimming pools of water saved, cars' worth of CO2 removed). Audit trail of all 5 choices with Best/Good/Poor tier badges. Certification: ≥60 Green Score = "APPROVED TO BUILD" with medal. <60 = "NEEDS MORE WORK — Sent Back for Changes." "What You Just Learned" card connecting to real companies (Google, Meta, Microsoft). "The Bigger Picture" climate connection card linking individual choices to planetary impact. |

**Each round has:** A persistent pollution stats grid (energy in homes/year, water in pools/year, CO2 in cars/year, Green Score out of 100) that updates after each choice. A scenario card ("What's Happening") with simplified language. 3 choice cards with icons and plain-English descriptions (client-side). After confirming a choice: a tier-colored feedback card (Amazing/Good/Uh Oh), then a sequential 4-card impact reveal with staggered animations showing the effect on energy, water, CO2, and Green Score in relatable units. Below the game interaction, a Gradio-graded quiz tests deeper reasoning.

**Click-to-reveal formula box** at the bottom (same as Bias Detective): collapsible `<details>` element showing the Moral Compass Formula.

**Moral Compass Score updates:** 5 round quizzes + 1 results quiz (6 total, task IDs t5-t10). Each correct answer calls the API to update the student's completed task count, increasing their Sustainability %. Wrong answers show a retry hint but don't update the score.

**Quiz format — argumentation-based:** Every quiz is framed as "Someone says X — what's the best counter-argument?" This trains critical reasoning and debate skills:
- t5: "Someone says: 'Sensors are cheaper — why spend more on cooling?'"
- t6: "A company buys carbon offsets and says: 'We're green now!' What's wrong with this claim?"
- t7: "Someone says: 'Users want the best AI every time!' Why is using the biggest AI for every question a bad idea?"
- t8: "Someone says: 'Desert land is cheap — we'll save millions!' What are they forgetting?"
- t9: "A rival company says: 'Sharing our pollution numbers hurts our business.' Why is hiding a bad idea?"
- t10: "After all 5 rounds, why do these individual choices matter for the whole planet?"

### What a 12-year-old experiences

The mayor picks YOU as the city's Green AI Advisor! A company called NovaMind wants to build a giant data center in your city, and it would use the electricity of 14,400 families, guzzle 89 swimming pools of water, and add as much CO2 as 4,800 cars — every year. You have 5 rounds to fix their plan before they're allowed to build. Each round, you face a real problem — their cooling wastes water, their power comes from fossil fuels, their AI is too big — and you pick from 3 solutions. After each choice, animated cards pop up one by one showing what changed: "You saved enough power for 3,000 families!" or "That's like taking 800 cars off the road!" At the end you get a letter grade and see whether NovaMind is APPROVED TO BUILD or sent back for changes.

### What a 17-year-old experiences

You navigate real infrastructure decisions that AI companies face — reframed as civic oversight rather than corporate management. The "city advisor" framing adds an environmental justice dimension: these are decisions that affect your community's water, air, and energy. The five topics — cooling technology (immersion vs. evaporative), energy sourcing (on-site renewable vs. PPA vs. offsets), model architecture (cascade routing vs. distillation vs. caching), data center siting (climate and grid mix), and corporate transparency — are grounded in real examples (Microsoft's immersion cooling, Meta/Google's Nordic data centers). The argumentation-based quizzes go beyond the game choices: each asks you to counter a specific claim (e.g., "Sensors are cheaper — why spend more?"), training critical reasoning and evidence-based debate. The relatable-unit impact system (homes, swimming pools, cars) makes abstract MWh/L/ton figures tangible.

### What a teacher sees

**Pedagogical purpose:** Decision-making under constraints, infrastructure sustainability, civic responsibility, trade-off analysis, argumentation and counter-argument skills.
**Skills practiced:** Evaluating solutions with multiple criteria (cost, effectiveness, community impact), understanding infrastructure decisions at enterprise scale, reasoning about greenwashing vs. genuine sustainability, connecting technical choices to environmental outcomes, constructing evidence-based counter-arguments.
**Assessment points:** 5 round-level choices (Best/Good/Poor tier badges visible in the Advisor Report audit trail), 6 graded quizzes (t5-t10) that update the Moral Compass Score, the final Green Score (0-100), the letter grade (A+ to F), and the certification status (Approved / Sent Back).
**Cross-activity continuity:** Quiz completions add to the Moral Compass Score alongside Bias Detective tasks. The Green Score and certification tie into the narrative arc. The "Bigger Picture" card explicitly connects the simulation to real-world climate impact.

**Student Engagement Score: 5/5** — The city-advisor role-play is compelling and age-appropriate. The sequential impact reveal after each choice (energy → water → CO2 → Green Score, with staggered animations) creates genuine suspense. Relatable units (swimming pools, cars, families) make every number meaningful. The Advisor Report with letter grade and certification creates a satisfying conclusion.

**Value to Teacher Score: 5/5** — 6 graded quizzes, each testing argumentation about a specific sustainability topic (counter-argument format). The Advisor Report provides a detailed decision audit with tier badges. The relatable-unit impact summary is easily discussable in class. The letter grade + Green Score provide quick at-a-glance assessment.

---

## 8. Sustainability Upgrade (Certification)

**Source:** `sustainability_upgrade_en.py` (~884 lines) | **Format:** Gradio Blocks app

### What happens

**4 modules (0-3).**

| Module | Title | What the user sees/does |
|--------|-------|-----------------------|
| 0 | Achievement Dashboard | Final Moral Compass Score displayed large (3 decimal places, scale 0-1). Team rank and global rank. A tabbed leaderboard (Team and Individual standings) with the student's row highlighted. A "Certificate Ready" badge. |
| 1 | Engineering Log | 3 color-coded summary cards: (Blue) **Energy Awareness** — "You traced AI's hidden energy costs from prompt to GPU, uncovering that one AI image costs half a phone charge and 25 prompts evaporate a water bottle." (Purple) **Efficiency Optimization** — "You mastered prompt engineering and model selection to cut AI energy waste by 60%+ without sacrificing quality." (Green) **Infrastructure Intelligence** — "You evaluated data center cooling, renewable energy claims vs. reality, and grid impacts across nations." |
| 2 | Certificate Generator | A textbox for the student's full name. A "Generate Your Certificate" button. Produces a formal HTML certificate with: indigo border, branded logos, program name ("Green AI Initiative — Digital Education Program"), title ("Sustainable AI Innovation / Environmental Stewardship"), recipient name in large serif font, team name, Moral Compass Score (3 decimals), "VERIFIED GREEN" audit status badge, date, and reference ID. A "Print / Save as PDF" button opens a new window with the certificate formatted for landscape printing. |
| 3 | Bridge to Final Competition | Motivational "The Final Frontier" message. "Your final mission is to compete against your peers to build the most accurate model possible. But remember: You must maintain your Moral Compass." Directs to the next activity. |

### What a 12-year-old experiences

You finally get to see your score — how well you did across the whole challenge! Your name is on a leaderboard with your classmates. You read 3 cards that summarize what you learned about energy, efficiency, and infrastructure. Then you type your name and generate a real-looking certificate with your score and a "Verified Green" badge. You can print it or save it as a PDF. At the end, you're told there's one more competition ahead.

### What a 17-year-old experiences

The dashboard provides a quantitative summary of your Moral Compass Score — a concrete number reflecting both your model accuracy and your sustainability knowledge. The Engineering Log cards connect the discrete activities back to three transferable competencies (energy awareness, efficiency optimization, infrastructure intelligence). The certificate serves as a tangible portfolio artifact. The bridge to the final competition reframes the challenge: now accuracy and sustainability must coexist.

### What a teacher sees

**Pedagogical purpose:** Reflection, self-assessment, recognition, portfolio artifact creation.
**Skills practiced:** Reviewing and synthesizing learning, self-assessment against a rubric (the score), creating a sharable artifact.
**Assessment points:** The Moral Compass Score itself (a single metric integrating accuracy from Activity 4 and sustainability task completions from Activities 6-7). The leaderboard provides class-wide comparative data. The certificate is a portfolio artifact.
**Cross-activity continuity:** Aggregates all prior scores into a final dashboard. The bridge to Activity 9 sets up the final competition.

**Student Engagement Score: 3/5** — The certificate generation is a highlight, but this is mostly reflective reading. The leaderboard provides some competitive engagement.

**Value to Teacher Score: 4/5** — The final score and leaderboard are strong assessment tools. The certificate provides a shareable artifact for portfolios or parent communication. The Engineering Log cards explicitly map learning outcomes.

---

## 9. Model Building Game (Final Variant)

**Source:** `model_building_app_en_final_sustainability.py` (~3,881 lines) | **Format:** Gradio Blocks app

### What happens

**Same 5 onboarding modules + Arena as the base variant (Activity 4), plus conclusion slides after the arena.**

The onboarding, arena mechanics, rank progression, 10-attempt limit, and leaderboard are identical to the base Model Building Game. The key difference is what happens when the student clicks "Finish & Reflect":

**Conclusion slides (added after the arena):**

| Element | Content |
|---------|---------|
| Certification heading | "Certification Earned" with subtitle "Ethics at Play: Sustainable AI Engineering" — positions the entire challenge as a certification-worthy achievement. |
| Performance Snapshot | Final accuracy (as %), global rank, improvement delta over first score, total iterations (model versions tested this session). |
| Learning summary | 4 bullet points: (1) Identify energy consumption patterns in large datasets. (2) Optimize models for real-world environmental impact. (3) Balance predictive power with computational complexity (Green AI). (4) Understand the role of data-driven decisions in urban sustainability. |
| Closing message | "AI is a powerful tool for the planet, but only if built with responsibility. You've shown how to create systems that don't just solve problems, but contribute to a more sustainable future." |

### What a 12-year-old experiences

You're back in the AI lab for one last competition! Everything works the same as before — pick your model, set complexity, choose features, submit. But this time, you already know about the environmental costs, so it feels different. When you finish, you see your final score, how much you improved, and a summary of everything you learned. The closing message says: "AI is a powerful tool for the planet, but only if built with responsibility." It feels like graduation.

### What a 17-year-old experiences

The return to the model-building arena after the sustainability activities creates a full-circle moment. You now approach the same optimization problem with a dual lens: accuracy AND environmental awareness. The conclusion slides make the implicit learning explicit — the 4-point summary maps directly to transferable AI literacy competencies. The "Ethics at Play" framing positions the entire sequence as more than a game: it's a certification in sustainable AI engineering.

### What a teacher sees

**Pedagogical purpose:** Applied practice, synthesis, and certification. Students re-enter the model-building arena with newly acquired ethical/sustainability context.
**Skills practiced:** All the model-building skills from Activity 4, now informed by the sustainability awareness from Activities 5-8. The conclusion's learning summary provides a self-assessment rubric.
**Assessment points:** Same as Activity 4 (leaderboard, submissions, accuracy metrics) plus the conclusion's performance snapshot and feature analysis. The improvement delta over first score measures growth.
**Cross-activity continuity:** This is the capstone. The conclusion explicitly references the full journey and positions the student as a certified "Sustainable AI Engineer."

**Student Engagement Score: 4/5** — The arena is still engaging, though returning to it may feel repetitive for students who spent a lot of time in Activity 4. The conclusion slides provide satisfying closure.

**Value to Teacher Score: 5/5** — The improvement delta (first score vs. best score) measures learning directly. The feature analysis reveals whether students applied their understanding of strong predictors. The conclusion's 4-point learning summary maps cleanly to learning objectives. The leaderboard provides final comparative assessment.

---

## Score Summary Table

| # | Activity | Engagement (1-5) | Teacher Value (1-5) |
|---|----------|:-----------------:|:-------------------:|
| 1 | Climate Mission: Investigation | 5 | 4 |
| 2 | Climate AI Innovation Lab | 4 | 4 |
| 3 | Understanding AI Systems | 5 | 5 |
| 4 | Model Building Game (Base) | 5 | 5 |
| 5 | Moral Compass Challenge | 5 | 3 |
| 6 | Bias Detective | 4 | 5 |
| 7 | Fairness Fixer (Green AI Advisor) | 5 | 5 |
| 8 | Sustainability Upgrade | 3 | 4 |
| 9 | Model Building Game (Final) | 4 | 5 |
| | **Average** | **4.4** | **4.4** |

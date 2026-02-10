# UX Audit: Activity 1 — Climate Mission: Investigation (v1.9)

**Audience lens:** 12-year-old student, first encounter, no prior climate science or data vocabulary.
**Source file:** `Activity_1.html`

---

## Section 1: The User Journey (Step-by-Step Walkthrough)

### Step 0 — Mission Briefing (lines 500-624)

**What happens:** The student receives the title "CLIMATE ACTION INVESTIGATOR" with a green "Designation Acquired" badge. The mission objective is stated: *"Identify the single largest polluter in your home city and generate a data-driven briefing for local leaders."* Four expandable climate fact cards follow (temperature, renewables, extreme weather, tech solutions), each with a stat, description, and source citation. A blue info box explains that Climate TRACE uses satellites and AI. A single button: "ACCEPT MISSION & START SCAN."

**Verdict:** Visually impressive — the dark theme, glowing accent colors, and expandable cards feel like a spy briefing. The 4 fact cards are well-sourced and engaging. However:
- "Designation Acquired" sounds corporate/military — a 12-year-old won't know what "designation" means
- "data-driven briefing for local leaders" is very adult language
- "DATA PEDIGREE" is a term most adults don't use, let alone kids
- "radical transparency and credibility" is buzzword-heavy
- "constellation of satellites" is poetic but not concrete

### Step 1 — Designate Target (lines 627-645)

**What happens:** A text input asks the student to enter their city name. Helpful tips appear if the search fails (try larger city, try province/county, use English names). Button: "INITIALIZE SCAN."

**Verdict:** Clean and simple. The error tips are genuinely helpful. Issues:
- "Designate Target" sounds like a military strike
- "retrieve its satellite climate profile" — kids won't know what a "satellite climate profile" is
- "INITIALIZE SCAN" is sci-fi jargon
- "Province" and "County" are geographic terms that vary by country — could confuse international students

### Step 2 — The Big Picture (lines 654-688)

**What happens:** Shows total emissions for 2022 and 2023 side by side, with a car-equivalent context line ("Roughly equivalent to X cars driving for a year"). A checkpoint quiz asks whether emissions went up or down. Answering correctly unlocks the next step.

**Verdict:** The car equivalent is a great touch — makes abstract numbers tangible. The quiz is simple and effective. Issues:
- "tonnes" — kids may not know metric tonnes vs US tons, or what either means at this scale
- No explanation of what "emissions" actually are (CO2? Greenhouse gases? Pollution in general?)
- The numbers can be enormous (millions) with no sense of whether that's a lot for a city

### Step 3 — Sector Breakdown (lines 691-707)

**What happens:** A bar chart shows emissions by sector. The quiz asks students to select the top 3 sectors. Sectors are displayed with formatted names (e.g., "power" becomes "Power", "transportation" becomes "Transportation").

**Verdict:** The chart is clear and the multi-select quiz is a good interaction pattern. Issues:
- "Sector" is never defined — a kid may not know what an industry sector is
- "emissions volume" in the question text is science jargon
- Some sector names from Climate TRACE are opaque (e.g., "mineral-extraction", "waste", "fluorinated-gases")
- The chart labels at font-size 9px may be hard to read
- No explanation of what the sectors actually do or why they produce emissions

### Step 4 — Tracking the Sources (lines 710-747)

**What happens:** The top 3 individual emission sources are shown as clickable cards with rank badges. Clicking reveals details: industry sector, total emissions, and % of city total. A quiz asks which specific source is the highest emitter.

**Verdict:** Good interactive pattern — clicking to reveal details encourages exploration. The rank badges are clear. Issues:
- Source names are raw from Climate TRACE and can be cryptic facility names (power plants, factories)
- "subsector" label appears in the UI — kids won't know this term
- The distinction between "sector" and "source" is never explained
- "% of City Total" is clear but the percentages can be tiny (e.g., 0.12%), which may confuse kids into thinking it doesn't matter

### Step 5 — Strategic Approaches (lines 750-778)

**What happens:** A "Strategic Insight" box shows: *"If we cut emissions in this sector by half, our whole city's footprint drops by X%."* A binary quiz offers two approaches: "Targeted policy intervention focused on this sector's largest emitters" vs. "Wait for all sectors to voluntarily reduce emissions equally."

**Verdict:** The "cut in half" framing is a smart way to show leverage. But:
- "Targeted policy intervention" is adult policy language — a 12-year-old has no mental model for this
- The wrong answer ("Wait for all sectors to voluntarily reduce emissions equally") is obviously wrong — there's no real decision-making
- "tactical path," "tactical objective," "strategic priority" — heavy military/corporate jargon throughout
- "political will" in the fact cards is an abstract concept for kids
- The question asks about "highest measurable impact" — "measurable" is unnecessary complexity

### Step 6 — Plan of Action (lines 782-803)

**What happens:** An auto-generated "Satellite Intelligence Briefing" summarizes the investigation with bullet points: target area, trend detection, top three culprits, high-impact source, strategic priority. A textarea asks students to write their suggestion to local leaders.

**Verdict:** The auto-generated summary is a great payoff — students see their investigation packaged as a real briefing. Issues:
- "Satellite Intelligence Briefing" sounds like a spy movie
- "Trend Detection" is jargon
- "High-Impact Source" is jargon
- "Strategic Priority: Modernizing the [sector] sector is the primary tactical objective" — kids won't know what "modernizing a sector" means
- The textarea placeholder "Dear Local Leaders, the data shows that... I suggest we..." is good scaffolding

### Step 7 — Mission Complete (lines 806-829)

**What happens:** Trophy icon, "Investigation Complete" header, display of the satellite findings and the student's written suggestion. A green box bridges to Activity 2: *"Next up: You'll design an AI system to predict building energy efficiency using real data."*

**Verdict:** Satisfying conclusion with a clear bridge to the next activity. Issues:
- "decoded the satellite profile" — kids didn't decode anything, they read charts
- The transition to "building energy efficiency" is abrupt — no explanation of why buildings matter after investigating city-wide emissions

---

## Section 2: Confusing Terms & Suggested Rewrites

| # | Current Term | Location | Why Confusing | Suggested Rewrite |
|---|---|---|---|---|
| 1 | "Designation Acquired" | Step 0 header (line 504) | Military/corporate jargon | "You're In!" or "Role Assigned" |
| 2 | "data-driven briefing for local leaders" | Mission objective (line 514) | Corporate speak | "a report backed by real data to share with your city's decision-makers" |
| 3 | "DATA PEDIGREE" | Info box (line 615) | Obscure term (pedigree = dog breeding to most kids) | "WHERE THE DATA COMES FROM" or "OUR DATA SOURCE" |
| 4 | "radical transparency and credibility" | Info box (line 618) | Buzzwords | "so anyone can check the numbers" |
| 5 | "constellation of satellites" | Info box (line 617) | Poetic but vague — how many? | "a network of satellites" |
| 6 | "pre-industrial levels" | Fact card 1 (line 535) | What era is that? | "levels before factories and cars existed (around 1850)" |
| 7 | "climate tipping points" | Fact card 1 (line 536) | Never defined | "points of no return — changes that can't be undone" |
| 8 | "Designate Target" | Step 1 heading (line 628) | Sounds like a military strike | "Pick Your City" or "Choose Your Location" |
| 9 | "retrieve its satellite climate profile" | Step 1 description (line 629) | Technical | "look up its pollution data from satellites" |
| 10 | "INITIALIZE SCAN" | Button (line 635) | Sci-fi jargon | "SEARCH" or "SCAN MY CITY" |
| 11 | "Province" / "County" | Step 1 tip (line 630) | Varies by country; kids mix them up | "region or county" (and add: "the larger area your town is part of") |
| 12 | "tonnes" | Step 2 display (lines 871-872) | Metric vs imperial; meaningless at large scale | Keep "tonnes" but add a one-liner: "1 tonne = about the weight of a small car" |
| 13 | "emissions" | Throughout | Used 20+ times, never defined | Define on first use (Step 0): "emissions — the greenhouse gases (like CO2) released into the air that warm the planet" |
| 14 | "footprint" | Step 2 success, Step 5 (lines 684, 761) | Used interchangeably with "emissions" — which is it? | Pick one term and stick with it, or define: "carbon footprint — the total amount of greenhouse gases a city produces" |
| 15 | "Sector" | Steps 3-5 (throughout) | Never defined | Define on first use (Step 3): "sector — a group of similar industries (like all power plants, or all transportation)" |
| 16 | "emissions volume" | Step 3 quiz (line 700) | Science jargon | "total pollution" or "emissions totals" |
| 17 | "subsector" | Source cards (line 979) | Jargon within jargon | "Industry type" or just "Type" |
| 18 | "Targeted policy intervention focused on this sector's largest emitters" | Step 5 quiz option (line 768-769) | Adult policy language | "Create rules that focus on the biggest polluters in this industry" |
| 19 | "Wait for all sectors to voluntarily reduce emissions equally" | Step 5 quiz option (line 770-771) | Also adult language, and obviously wrong | "Hope that every industry cuts pollution on their own, by the same amount" |
| 20 | "highest measurable impact" | Step 5 quiz question (line 766) | Unnecessary complexity | "biggest difference" |
| 21 | "Satellite Intelligence Briefing" | Step 6 heading (line 788) | Spy movie language | "Your Investigation Report" or "Your Climate Report" |
| 22 | "Trend Detection" | Auto-summary (line 1011) | Jargon | "What Changed" |
| 23 | "High-Impact Source" | Auto-summary (line 1013) | Jargon | "Biggest Single Polluter" |
| 24 | "Strategic Priority: Modernizing the [sector] sector is the primary tactical objective" | Auto-summary (line 1014) | Military + corporate jargon stacked | "Top Priority: Cleaning up the [sector] industry should be this city's #1 goal" |
| 25 | "decoded the satellite profile" | Step 7 (line 810) | Kids didn't "decode" anything | "analyzed the satellite data" or "investigated the pollution data" |
| 26 | "political will" | Fact card 4 (line 603) | Abstract concept | "governments deciding to act" |
| 27 | "implementation speed" | Fact card 4 (line 602) | Corporate speak | "how fast we put solutions to work" |

---

## Section 3: Missing Context / Explanations

1. **What are "emissions" exactly?** — The word is used 20+ times but never defined. A 12-year-old may vaguely know "pollution is bad" but not understand greenhouse gases, CO2, or why they're measured in tonnes. Add a 1-sentence definition in Step 0 or the first fact card.

2. **What is a "sector"?** — Steps 3-5 revolve around sectors but the term is never explained. A simple definition ("a group of similar industries") would help enormously.

3. **Why do some sectors produce more emissions?** — The bar chart shows the data but never explains WHY power plants or transportation produce more than, say, forestry. Even one sentence per sector would add understanding.

4. **What's the difference between a "sector" and a "source"?** — Step 3 analyzes sectors, Step 4 analyzes sources. The relationship (sources are individual facilities within a sector) is never stated.

5. **Are these numbers a lot?** — Showing "1,234,567 tonnes" means nothing without context. The car-equivalent in Step 2 is great but appears only once. Add similar comparisons for sector and source levels.

6. **What can a 12-year-old actually do?** — The mission asks students to write advice to "local leaders," but kids may feel powerless. A brief note about how young people have influenced climate policy (Greta Thunberg, youth climate strikes) could be motivating.

7. **Why does the investigation jump from city emissions to building energy efficiency?** — The Step 7 bridge to Activity 2 says "you'll design an AI system to predict building energy efficiency" but doesn't explain why buildings are relevant after investigating city-wide pollution. Add: "Buildings account for ~40% of energy use in most cities — that's why predicting which buildings waste energy is such a powerful tool."

8. **What happens if my city's emissions went DOWN?** — The quiz in Step 2 handles both directions, but the narrative always implies things are getting worse. A positive framing for improving cities would be encouraging.

---

## Section 4: What Works Well

1. **Dark "mission briefing" aesthetic** — The dark theme with glowing accents feels like a spy/hacker interface. 12-year-olds will love it. Professional without being boring.

2. **Expandable fact cards** — Click-to-reveal is a perfect interaction pattern for this age: low commitment, high curiosity reward. The stats ("+1.45C", "5x More Frequent") are punchy.

3. **Real data from a real API** — Using Climate TRACE with the student's own city makes this personal and authentic. Kids aren't analyzing fake numbers — they're looking at real satellite data.

4. **Car-equivalent context** — "Roughly equivalent to X cars driving for a year" instantly makes abstract tonnage meaningful. Best explanatory moment in the app.

5. **Progressive quiz gating** — Can't proceed without answering correctly. Prevents rushing through without understanding. Wrong answers flash red briefly rather than punishing.

6. **Source investigation cards** — Clicking individual pollution sources to see their details is genuinely engaging detective work.

7. **Auto-generated report** — The summary in Step 6 packages the student's entire journey into a professional-looking briefing. Makes the work feel consequential.

8. **Scaffolded writing prompt** — The textarea placeholder ("Dear Local Leaders, the data shows that... I suggest we...") gives structure without dictating the answer.

9. **Clear navigation** — Progress bar with numbered nodes, back buttons on every step, visual state (completed/active/upcoming) is always clear.

10. **Bridge to next activity** — The green box at the end naturally transitions to Activity 2 without feeling forced.

---

## Section 5: Suggested Structural Improvements

1. **Add a "What does this mean?" glossary tooltip** — On first use of "emissions," "sector," "source," and "tonnes," add a small (i) icon that shows a 1-sentence definition on hover/tap. Reuse the same tooltip pattern throughout.

2. **Add per-sector context lines** — In the bar chart (Step 3), add a one-liner under each sector name: "Power = electricity plants", "Transportation = cars, trucks, planes", etc. Even brief labels would demystify the chart.

3. **Make the Step 5 quiz a real choice** — The current binary (targeted policy vs. do nothing) is too obvious. Replace with 3-4 plausible strategies and explain why the data-driven one is strongest. This would make the step genuinely educational rather than a formality.

4. **Add comparisons at every scale** — Step 2 has the car equivalent; extend this pattern. For sectors: "That's like running X homes for a year." For sources: "This one facility produces as much pollution as X thousand cars."

5. **Define terms inline on first use** — Rather than (or in addition to) a glossary, bold key terms and add a parenthetical on first use: "**emissions** (greenhouse gases released into the air)." This is how science textbooks handle vocabulary.

6. **Add a "How does this compare to other cities?" moment** — After revealing the city's data, show a brief comparison: "Your city produces more/less than the average city of similar size." This adds perspective and motivation.

7. **Soften the military language throughout** — "Designate Target," "Initialize Scan," "Tactical Selection," "Strategic Priority" — the spy theme is fun but the vocabulary is adult. Keep the spy aesthetic but use simpler words: "Pick Your City," "Start Search," "Choose Your Strategy," "Top Priority."

8. **Add a "What can I do?" section before the final report** — Between Steps 5 and 6, add a brief list of age-appropriate actions: talk to family, write to school board, join a climate club, reduce your own footprint. This transforms the mission from observation to agency.

---

## Section 6: Accessibility & Technical Notes

1. **No keyboard navigation for fact cards** — The expandable cards use `onclick` on `<div>` elements. These are not keyboard-accessible (no `tabindex`, no `role="button"`, no `keydown` handler). Screen readers will skip them entirely.

2. **Quiz buttons are `<button>` elements** — Good. These are keyboard-accessible by default.

3. **No ARIA labels on progress nodes** — The step-node circles show numbers but have no `aria-label` explaining "Step 1: Mission Briefing" etc.

4. **Color contrast in light mode** — The `--text-dim` (#64748b on #f8fafc) has a contrast ratio of ~4.6:1, which passes AA for large text but fails for body text (needs 4.5:1 minimum for normal text, but the 1.125rem size may qualify as large).

5. **Chart.js bar chart has no alt text** — The canvas element has no fallback text for screen readers.

6. **Mobile responsiveness** — The `.options-grid` uses `grid-template-columns: 1fr 1fr` which may make quiz options too narrow on phones. Consider a single-column layout below 480px.

7. **No offline fallback** — The app depends entirely on the Climate TRACE API. If the API is down or slow, the student hits an error with no way to continue. Consider caching a few example cities for demo/fallback purposes.

---

# Part 2: 17-Year-Old's Experience If the 12-Year-Old Rewrites Were Applied

**Audience lens:** 17-year-old student, likely has basic science literacy, some exposure to climate discussions in school and media, may be preparing for university. Cares about being taken seriously.

## The Core Tension

A 17-year-old will notice dumbing-down. The 12-year-old rewrites solve real clarity problems, but some go too far for an older audience — replacing precise language with vague simplifications that a 17-year-old would find patronizing. The challenge is: **keep the clarity gains without losing intellectual respect.**

At 17, students *want* to learn real terminology — they just need it introduced properly rather than thrown at them cold. Removing terms like "emissions," "sector," or "intervention" doesn't help a 17-year-old; it insults them. But leaving "DATA PEDIGREE" and "Designate Target" is still bad UX at any age.

---

## Section 7: 12-Year-Old Rewrites Reviewed Through a 17-Year-Old's Lens

### Rewrites That Still Work at 17 (Keep As-Is)

| # | 12-Y/O Rewrite | Why It Works at 17 Too |
|---|---|---|
| 1 | "Designation Acquired" → "You're In!" or "Role Assigned" | "Designation Acquired" is cringe military cosplay at any age. "Role Assigned" works for 17. |
| 3 | "DATA PEDIGREE" → "WHERE THE DATA COMES FROM" | "Pedigree" is just a weird word choice. No one at any age uses it for data. |
| 4 | "radical transparency and credibility" → "so anyone can check the numbers" | Buzzwords are buzzwords. 17-year-olds are especially allergic to corporate-speak. |
| 7 | "climate tipping points" → "points of no return — changes that can't be undone" | The parenthetical definition is useful. 17-year-olds may have heard the term but appreciate the clarification. |
| 10 | "INITIALIZE SCAN" → "SCAN MY CITY" | Better UX at any age. "Initialize" adds nothing. |
| 16 | "emissions volume" → "total pollution" or "emissions totals" | "Volume" is the wrong word (volume = space, not quantity). "Emissions totals" is more precise and clearer. |
| 17 | "subsector" → "Industry type" | "Subsector" is never defined and adds unnecessary hierarchy. "Industry type" is clear. |
| 20 | "highest measurable impact" → "biggest difference" | Leaner writing. A 17-year-old doesn't need filler words either. |
| 21 | "Satellite Intelligence Briefing" → "Your Investigation Report" | The spy roleplay wears thin by 17. "Your Investigation Report" is more respectful. |
| 22 | "Trend Detection" → "What Changed" | Simpler and more direct. No information is lost. |
| 23 | "High-Impact Source" → "Biggest Single Polluter" | More vivid, more concrete. Better writing at any level. |
| 25 | "decoded the satellite profile" → "analyzed the satellite data" | More accurate — they didn't decode anything. |

### Rewrites That Feel Patronizing at 17 (Need Adjustment)

| # | 12-Y/O Rewrite | Problem at 17 | Final Suggestion for 17 |
|---|---|---|---|
| 2 | "a report backed by real data to share with your city's decision-makers" | Too wordy and hand-holdy. A 17-year-old knows what a report is. | "a data-backed briefing for city leaders" — keep "briefing" (it fits the mission theme) but drop "data-driven" for "data-backed" which is more natural |
| 5 | "constellation of satellites" → "a network of satellites" | "Constellation" is actually the correct technical term for a satellite group. A 17-year-old can handle it, especially since it sounds cool. | Keep "constellation of satellites" but add: "a constellation (network) of satellites" on first use only |
| 6 | "pre-industrial levels" → "levels before factories and cars existed (around 1850)" | A 17-year-old taking science classes should know or learn "pre-industrial." The parenthetical is helpful though. | "pre-industrial levels (before ~1850)" — keep the term, just anchor the date |
| 8 | "Designate Target" → "Pick Your City" | "Pick Your City" is fine functionally but loses all mission flavor. At 17, the mission aesthetic is still fun — it just needs less jargon. | "Select Your City" — professional without being militaristic |
| 9 | "retrieve its satellite climate profile" → "look up its pollution data from satellites" | "Pollution data" is imprecise (emissions ≠ all pollution). A 17-year-old can handle "emissions profile." | "pull up its emissions profile from satellite data" |
| 11 | "Province" / "County" → "region or county" | At 17, students should know these geographic terms. The issue was international confusion, not vocabulary. | Keep "Province or County" but add: "(the larger administrative area your city belongs to)" |
| 12 | "tonnes" → add "1 tonne = about the weight of a small car" | The car-weight comparison is slightly childish at 17. A more useful comparison is to everyday emissions. | Add instead: "1 tonne of CO2 = roughly what 1 passenger car emits in 3 months" — connects to something they understand AND teaches a real reference point |
| 13 | "emissions" → define as "greenhouse gases (like CO2) released into the air that warm the planet" | A 17-year-old likely knows what emissions are in general. The definition is fine on first use but shouldn't persist. | Define once in Step 0: "greenhouse gas emissions (CO2, methane, and other gases that trap heat in the atmosphere)" — be specific, include methane, use "trap heat" instead of "warm the planet" |
| 14 | "footprint" → pick one term or define it | The 12-y/o suggestion to pick one term is too restrictive. A 17-year-old can handle both if linked. | On first use: "carbon footprint (total greenhouse gas emissions)" — then use both terms freely |
| 15 | "sector" → define as "a group of similar industries" | The definition is correct but the delivery matters. Don't parenthetically define it every time. | Define once in Step 3 heading: "Sector Breakdown — emissions grouped by industry" — the heading itself teaches the word |
| 18 | "Targeted policy intervention..." → "Create rules that focus on the biggest polluters in this industry" | "Create rules" is vague and oversimplified. A 17-year-old is ready for policy concepts. | "Targeted regulations on this sector's top emitters" — uses "regulations" (a word they should learn) instead of the vaguer "policy intervention," but doesn't water it down to "rules" |
| 19 | "Wait for all sectors to voluntarily reduce..." → "Hope that every industry cuts pollution on their own, by the same amount" | The sarcastic "Hope that..." tone is fine at 17 but the option is still too obviously wrong. The real problem is the quiz design, not just the wording. | "Voluntary equal reductions across all industries, with no enforcement" — sounds plausible enough to require thought, and "no enforcement" is the key detail that makes it the wrong answer |
| 24 | "Strategic Priority: Modernizing the [sector]..." → "Top Priority: Cleaning up the [sector] industry should be this city's #1 goal" | "Cleaning up" is vague. A 17-year-old can engage with what modernizing actually means. | "Top Priority: Reducing emissions in the [sector] sector through regulation and technology upgrades" — specific, actionable, uses real-world language |
| 26 | "political will" → "governments deciding to act" | Slightly reductive. "Political will" is a real concept a 17-year-old should encounter. | "political will (the willingness of governments to act)" — define it, don't replace it |
| 27 | "implementation speed" → "how fast we put solutions to work" | Acceptable but slightly informal for 17. | "the speed of implementation" — just restructure, don't replace the word |

---

## Section 8: Additional Issues a 17-Year-Old Would Notice

A 17-year-old is more analytically critical than a 12-year-old. Beyond vocabulary, they'll notice structural and intellectual weaknesses:

### 1. The Step 5 Quiz Is Insultingly Easy
At 17, "should we target the biggest polluters or just hope everyone fixes it on their own?" is not a real question. It's a fake choice that wastes their time.

**Fix:** Replace with a genuinely debatable multi-option question:
- "Impose strict emissions caps on the top 3 sources" (effective but politically difficult)
- "Offer tax incentives for the whole sector to transition to cleaner technology" (slower but broader)
- "Invest in carbon capture technology at the largest facilities" (innovative but expensive and unproven at scale)
- "Require all new facilities in this sector to meet zero-emission standards" (forward-looking but doesn't address existing sources)

Let the student choose and then show a brief analysis of each option's trade-offs. No single "correct" answer — this teaches critical thinking, not compliance.

### 2. No Data Literacy Taught
The app shows data but never teaches students how to read it critically. A 17-year-old should be asked:
- "What might be missing from this data?"
- "Could there be sources that satellites can't detect?"
- "Why might 2023 numbers differ from 2022 for reasons unrelated to policy?"

**Fix:** Add a "Data Limitations" callout in Step 2 or Step 3: "Remember: satellite data captures what's visible from above. Underground sources, indirect emissions (like imported goods), and natural variations (cold winters = more heating) aren't always reflected."

### 3. No Connection Between Local and Global
The fact cards in Step 0 cite global statistics, but the investigation is local. A 17-year-old will notice the disconnect.

**Fix:** After the city data loads in Step 2, add a one-liner: "Your city contributes approximately X% of your country's total emissions" (if the API supports it) or "Cities like yours account for over 70% of global CO2 emissions — local action has global impact."

### 4. The Writing Prompt Needs More Rigor
"What is the single most important action?" with a blank textarea is fine at 12 but too open-ended at 17. There's no rubric, no structure beyond the placeholder text.

**Fix:** Add 3-4 guiding sub-questions:
- "What specific policy or action do you recommend?"
- "What data from your investigation supports this recommendation?"
- "What's one risk or trade-off of your proposed action?"
- "Who specifically should be responsible for implementing it?"

### 5. No Mention of Scope 1/2/3 Emissions
A 17-year-old studying sustainability should encounter the concept that emissions have scopes — direct (Scope 1), energy-related indirect (Scope 2), and supply-chain indirect (Scope 3). Climate TRACE primarily captures Scope 1.

**Fix:** Add a brief note in Step 3 or Step 4: "Note: This data shows direct emissions (Scope 1) — pollution released at the source. It doesn't include indirect emissions from electricity use (Scope 2) or supply chains (Scope 3), which can be even larger."

### 6. Citations Should Be Linked
The fact cards cite sources (NASA GISS, IEA, WMO, IPCC) but don't link to them. A 17-year-old doing research should be able to click through.

**Fix:** Make citations clickable links to the actual reports.

---

## Section 9: Final Recommended Text — Merged for Both Audiences

The following table provides the final recommended text that balances both audiences. The strategy: **use real terminology but define it inline on first use; keep the mission aesthetic but drop the military cosplay; respect the 17-year-old's intelligence while ensuring the 12-year-old isn't lost.**

| # | Original Text | Final Recommended Text | Notes |
|---|---|---|---|
| 1 | "Designation Acquired" | "Role Assigned" | Works for both ages |
| 2 | "data-driven briefing for local leaders" | "a data-backed briefing for city leaders" | Natural phrasing, not dumbed down |
| 3 | "DATA PEDIGREE" | "OUR DATA SOURCE" | Clear at any age |
| 4 | "radical transparency and credibility" | "so anyone can check the numbers" | Anti-buzzword works universally |
| 5 | "constellation of satellites" | "a constellation (network) of satellites" | Teach the real term, define it once |
| 6 | "pre-industrial levels" | "pre-industrial levels (before ~1850)" | Keep term, anchor the date |
| 7 | "climate tipping points" | "climate tipping points — changes that can't be undone" | Em-dash definition, natural |
| 8 | "Designate Target" | "Select Your City" | Professional, not militaristic |
| 9 | "retrieve its satellite climate profile" | "pull up its emissions profile from satellite data" | Precise, accessible |
| 10 | "INITIALIZE SCAN" | "SCAN MY CITY" | Better UX button text |
| 11 | "Province or County" | "Province or County (the larger area your city belongs to)" | Keep terms, add context |
| 12 | "tonnes" (no context) | Add: "1 tonne of CO2 ≈ what 1 car emits in 3 months" | Useful reference point for both |
| 13 | "emissions" (undefined) | First use: "greenhouse gas emissions (CO2, methane, and other gases that trap heat)" | Define once, then use freely |
| 14 | "footprint" (undefined) | First use: "carbon footprint (total greenhouse gas emissions)" | Link the two terms once |
| 15 | "Sector" (undefined) | Step 3 heading: "Sector Breakdown — emissions grouped by industry" | Heading teaches the word |
| 16 | "emissions volume" | "emissions totals" | Cleaner, more precise |
| 17 | "subsector" | "Industry type" | Universal improvement |
| 18 | "Targeted policy intervention focused on this sector's largest emitters" | "Targeted regulations on this sector's top emitters" | Real vocabulary, not watered down |
| 19 | "Wait for all sectors to voluntarily reduce emissions equally" | "Voluntary equal reductions across all industries, with no enforcement" | Sounds plausible, teaches "enforcement" concept |
| 20 | "highest measurable impact" | "biggest difference" | Lean writing |
| 21 | "Satellite Intelligence Briefing" | "Your Investigation Report" | Respectful at both ages |
| 22 | "Trend Detection" | "What Changed" | Direct |
| 23 | "High-Impact Source" | "Biggest Single Polluter" | Vivid |
| 24 | "Strategic Priority: Modernizing the [sector] sector is the primary tactical objective" | "Top Priority: Reducing emissions in the [sector] sector through regulation and technology upgrades" | Specific, actionable, no military jargon |
| 25 | "decoded the satellite profile" | "analyzed the satellite data" | Accurate |
| 26 | "political will" | "political will (the willingness of governments to act)" | Teach the term |
| 27 | "implementation speed" | "the speed of implementation" | Restructure, don't replace |

---

## Section 10: Structural Changes for a 17-Year-Old Audience

These go beyond text rewrites — they address intellectual depth:

1. **Replace the Step 5 binary quiz with a multi-option policy debate** — 3-4 plausible strategies with trade-off explanations after selection. No single "correct" answer.

2. **Add a "Data Limitations" callout** in Step 2 or 3 — teach critical data literacy by noting what satellite data can and can't capture.

3. **Add Scope 1/2/3 context** in Step 3 or 4 — a one-liner explaining that this data covers direct emissions only.

4. **Make fact card citations clickable links** to the actual reports (NASA GISS, IEA, WMO, IPCC).

5. **Structure the writing prompt** in Step 6 with 3-4 guiding sub-questions (recommended policy, supporting data, trade-offs, responsible parties).

6. **Add local-to-global connection** — after city data loads, show how the city fits into national/global context.

7. **Add a "What might explain this trend?" reflective question** in Step 2 — before the checkpoint quiz, ask students to hypothesize why emissions changed (economic growth, new regulations, weather patterns, COVID recovery, etc.).

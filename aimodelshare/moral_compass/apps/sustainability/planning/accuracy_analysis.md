# Accuracy Analysis: Sustainability Activities 1–3

**Date:** 2026-02-11
**Scope:** Every factual statement, data point, calculation, and conversion across all three activity files
**Audience context:** Students aged 12–17 and their teachers
**Standard:** Claims should be defensible to a teacher who fact-checks them. Simplifications are fine; errors and exaggerations are not.

---

## Severity Key

| Severity | Meaning |
|----------|---------|
| **BUG** | Incorrect calculation or code error — produces wrong numbers for users |
| **INCORRECT** | Factual error that needs correcting |
| **EXAGGERATED** | Defensible core claim but overstated — needs toning down |
| **IMPRECISE** | Correct in one context but misleading in others — needs qualification |
| **OK** | Accurate or acceptably simplified for the audience |

---

## Activity 1: Climate Investigation

### Fact 1: Global Temperature (+1.45°C)

**Claim (line 760–761):**
> "+1.45°C" ... "2024 was the hottest year ever recorded."

**Citation:** "Source: NASA GISS, 2025"

**Analysis:**
- "2024 was the hottest year ever recorded" — **OK**. Confirmed by NASA, NOAA, Copernicus, JMA, and the UK Met Office.
- "+1.45°C" — **IMPRECISE**. NASA GISS reported 2024 at approximately 1.47°C above the 1951–1980 baseline. However, the internationally standard reference period (used by IPCC and WMO) is 1850–1900, under which 2024 was approximately **1.55°C** above pre-industrial. The +1.45°C figure appears to use the 1880–1920 baseline that GISS sometimes references.
- "NASA GISS, 2025" — **OK** as a citation.

**Recommendation:** Change to `+1.5°C` and add "(above pre-industrial levels)" to match the standard WMO/IPCC baseline. This also aligns with the well-known 1.5°C threshold, making it more meaningful for students.

```
CURRENT: <div class="fact-stat" data-target="1.45" data-prefix="+" data-suffix="°C">+0°C</div>
UPDATED: <div class="fact-stat" data-target="1.5" data-prefix="+" data-suffix="°C">+0°C</div>
```
Also update the description to note "above pre-industrial levels (1850–1900 average)."

---

### Fact 1 Description: Heat waves, flooding, wildfires

**Claim (line 761):**
> "Every fraction of a degree means more deadly heat waves, flooding, and wildfires — and the cities producing the most pollution often don't even know where it's coming from."

**Analysis:** **OK**. The first clause is well-supported by IPCC AR6 WGI Chapter 11. The second clause about cities lacking emissions data is the core problem Climate TRACE was created to solve.

---

### Fact 2: Technology to cut emissions by 50%

**Claim (line 771):**
> "We already have the technology to cut emissions in half by 2030."

**Citation:** "Source: IPCC AR6, 2023"

**Analysis:** **EXAGGERATED**. IPCC AR6 WGIII (2022) and the Synthesis Report (2023) found that existing and near-commercial technologies could reduce emissions approximately **43% by 2030** (from 2019 levels) to stay on a 1.5°C pathway. "Half" overshoots this by a meaningful margin. Additionally, the IPCC is clear that this requires massive policy changes and deployment at unprecedented speed — framing it as purely a technology problem is misleading.

**Recommendation:**
```
CURRENT: "We already have the technology to cut emissions in half by 2030."
UPDATED: "We already have the technology to cut emissions by over 40% by 2030."
```
And update `data-target="50"` to `data-target="43"` with the stat display showing "43%". Also change the fact title from "The Technology Exists Today" to something like "We Have the Tools" to soften the implication that it's easy.

Update citation to: "Source: IPCC AR6 Synthesis Report, 2023"

---

### Fact 2 Description: Cities can't fix what they can't measure

**Claim (line 771):**
> "But cities can't fix what they can't measure — they need investigators to find the biggest sources first."

**Analysis:** **OK**. This is a well-established principle in emissions management and provides a direct bridge to the app's mission.

---

### Climate TRACE Description

**Claim (line 780–783):**
> "Climate TRACE, a global group that uses a network of satellites and AI to monitor every major source of carbon emissions on Earth — so anyone can check the numbers."

**Analysis:** **OK**. Accurate description of Climate TRACE (Tracking Real-time Atmospheric Carbon Emissions), founded in 2020. It does use satellite imagery, remote sensing, and AI/ML to estimate emissions from individual facilities worldwide. The "so anyone can check the numbers" accurately reflects its open-data mission.

---

### Car Equivalence Callout

**Claim (line 835):**
> "1 tonne of carbon emissions ≈ what 1 car produces in 3 months"

**Analysis:** **IMPRECISE but acceptable**. US EPA: average passenger vehicle emits ~4.6 tonnes CO₂/year → ~1.15 tonnes per 3 months. So 1 tonne is actually closer to **2.6 months** of car emissions. The "3 months" is a ~15% overstatement but is acceptable as a round-number approximation for the target audience.

**Recommendation:** Keep as-is. The simplification is pedagogically defensible and the error margin is small.

---

### Families Counter: 8.1 tonnes/year

**Claim (line 855):**
> "Estimated based on average household emissions of 8.1 tonnes/year"

**Code (line 1177):** `Math.round(t22 / 8.1)`

**Analysis:** **IMPRECISE**. The 8.1 tonnes figure is approximately the US average for direct household energy emissions (electricity + natural gas). However:
- This is a US-specific figure. Global average household energy emissions are much lower (~3–4 tonnes in Europe, ~1–2 tonnes in developing countries).
- The app is used internationally (Barcelona, Beijing, etc.), so applying a US figure to non-US cities will systematically undercount families affected.
- For many non-US cities, the number displayed could be off by 2–4x.

**Recommendation:** Add "US average" qualifier:
```
CURRENT: "Estimated based on average household emissions of 8.1 tonnes/year"
UPDATED: "Estimated based on US average household emissions of 8.1 tonnes/year"
```
This is honest about the approximation and avoids presenting a US figure as universal.

---

### Cars Equivalent Calculation — **BUG**

**Code (line 1131):**
```javascript
carsEquivalent: Math.round(investigationData.t22 / 4600)
```

**Also used at line 1168:**
```javascript
const cars = Math.round(t22 / 4600).toLocaleString();
```

**Analysis:** **BUG**. The US EPA figure is **4.6 tonnes CO₂/year** per average passenger vehicle. The code divides by **4,600**, which is 1,000× too large. This means the cars-equivalent number shown to students is **1,000× too small**.

Example: A city with 5,000,000 tonnes CO₂ would display "~1,087 cars" instead of the correct "~1,087,000 cars."

Note: Activity 2's `getProblemData()` correctly uses `/4.6` (line 1426), confirming this is a bug in Activity 1, not an intentional unit difference.

**Recommendation:** Fix both occurrences:
```javascript
// Line 1131
carsEquivalent: Math.round(investigationData.t22 / 4.6)

// Line 1168
const cars = Math.round(t22 / 4.6).toLocaleString();
```

Similarly fix the impact bars calculation at line 1506:
```javascript
const carsRemoved = Math.round(reduction / 4600);
// Should be:
const carsRemoved = Math.round(reduction / 4.6);
```

---

### Families Calculation (Activity 1)

**Code (line 1154, 1177):**
```javascript
familiesAffected: Math.round(investigationData.t22 / 8.1)
```

**Analysis:** The math is correct given the 8.1 tonnes/household assumption. The issue is the assumption itself being US-specific (see above). The calculation divides total city emissions (all sectors) by per-household emissions, giving the number of households whose annual energy equals the city's total — this is a meaningful comparison for scale.

**Verdict:** **OK** mechanically, but inherits the US-specificity issue noted above.

---

### Source Proximity Population Estimate

**Code (line 1479):**
```javascript
const estimatedPop = Math.max(1, Math.round(source.emissionsQuantity / 50));
```

**Analysis:** **IMPRECISE**. This estimates "people living within range of emissions" by dividing a source's emissions by 50. There's no scientific basis for this formula — it's a rough proxy at best. A coal plant emitting 5,000,000 tonnes would show "100,000 people" regardless of whether it's in a desert or downtown.

**Recommendation:** Since this is labeled "(estimated)" and serves to make the data more tangible, consider either:
1. Removing the population estimate entirely (the emissions tonnage and percentage are already meaningful), or
2. Adding a clearer caveat: "Very rough estimate — actual affected population depends on wind patterns, geography, and distance."

---

## Activity 2: AI Innovation Lab

### "40% of energy use" for buildings

**Claim (line 851):**
> "homes, offices, and public buildings that account for roughly 40% of energy use in most cities"

**Analysis:** **OK**. In the US, buildings account for approximately 40% of total energy consumption (US EIA). Globally, the figure is 30–40% depending on the country and whether direct + indirect energy is included. "Roughly 40%" with the qualifier "in most cities" is accurate.

---

### Building Count Estimation

**Code (line 1330–1331, repeated in getProblemData line 1418):**
```javascript
const buildingEstimate = totalEmissions ? Math.round(totalEmissions / 50) : 12000;
```

**Analysis:** **IMPRECISE**. The comment says "~50 tonnes avg per building is a rough proxy." In reality:
- US commercial buildings: ~900M tonnes CO₂ across ~5.9M buildings = ~152 tonnes/building average
- US residential: ~600M tonnes CO₂ across ~130M units = ~4.6 tonnes/unit
- Blended average depends heavily on the commercial/residential mix

50 tonnes/building is a reasonable middle ground for a mixed stock but will overestimate the number of buildings for cities with mostly residential stock and underestimate for industrial cities.

**Recommendation:** Add a comment in the code noting this is a rough estimate. The code already handles fallback (`12000`) gracefully. For the user-facing text, the `~` prefix ("~12,000 buildings") already signals approximation. **OK for educational purposes** — no change needed.

---

### Inspector Math: 365 days/year — **INCORRECT**

**Code (line 1419):**
```javascript
const inspectorYears = Math.max(1, Math.round(buildingCount / 365));
```

**Analysis:** **INCORRECT**. This assumes an inspector works **365 days per year** with no weekends, holidays, or sick days. A realistic figure is **~260 working days/year** (52 weeks × 5 days). This makes the displayed inspector-years estimate ~29% too optimistic.

Example: 12,000 buildings → code says 33 years → reality is closer to **46 years**.

Since the pedagogical point is "it takes impossibly long," understating the time actually weakens the argument.

**Recommendation:**
```javascript
const inspectorYears = Math.max(1, Math.round(buildingCount / 260));
```

---

### Inspector Counter Milestones

**Code (lines 1496–1501):**
```javascript
const milestones = [
    { label: 'Day 1', inspected: 1 },
    { label: 'Week 1', inspected: 5 },
    { label: 'Month 1', inspected: 22 },
    { label: 'Year 1', inspected: 260 }
];
```

**Analysis:** **OK**. 5 inspections per week (1/day, 5-day work week), 22 per month (~5 × 4.3 weeks), 260 per year (52 × 5). These are internally consistent and realistic for a single inspector. Note that these correctly use 260 working days/year — but the `inspectorYears` calculation above uses 365. This is an internal inconsistency.

---

### "71% of buildings are a mystery"

**Claim (line 883):**
> "71% of buildings are a mystery."

**Analysis:** **OK**. In the 24-building grid: 3 green + 4 red = 7 known, 17 unknown. 17/24 = 70.83% ≈ 71%. Math checks out. The actual percentage of buildings with no energy audit varies by city, but 70%+ is realistic in many jurisdictions where energy benchmarking is not mandatory.

---

### Building Sector Emissions (40% proxy)

**Code (line 1422):**
```javascript
const buildingEmissions = totalEmissions ? Math.round(totalEmissions * 0.4) : 50000;
```

**Analysis:** **OK**. Consistent with the 40% figure established in Step 0. The fallback of 50,000 tonnes is reasonable for a medium-sized city.

---

### Cars Equivalent (Activity 2)

**Code (line 1426):**
```javascript
const carsEquivalent = totalEmissions ? Math.round(buildingEmissions / 4.6) : 10000;
```

**Analysis:** **OK**. Correctly uses 4.6 tonnes/car/year (EPA figure). Note the inconsistency with Activity 1, which uses `/4600`.

---

### NREL Dataset: "100,000 building records"

**Claim (lines 1835, 1884):**
> "100,000 building records available from NREL"

**Analysis:** **IMPRECISE but acceptable**. NREL maintains several building energy datasets:
- **ResStock & ComStock**: Simulated building stocks (millions of modeled buildings)
- **Building Performance Database (BPD)**: ~1 million measured building records
- **CBECS**: ~6,000 commercial buildings
- **RECS**: ~18,000 residential

100,000 records is plausible as a curated subset from BPD or similar. The description as "NREL (the National Renewable Energy Laboratory — a real US government energy research lab)" is accurate.

**Recommendation:** No change needed. The number is plausible and the source is correctly identified.

---

### NREL Coverage: "New York, Illinois, Washington"

**Claim (line 1839):**
> "Coverage: New York, Illinois, Washington"

**Analysis:** **IMPRECISE**. NREL's building energy datasets are national in scope, not limited to three states. This appears to be presented as the geographic coverage of the matched dataset, which could be interpreted as a curated subset. However, listing only 3 states for 100,000 records might seem limiting.

**Recommendation:** Consider changing to "Coverage: Nationwide (strongest data in New York, Illinois, Washington)" or simply "Coverage: United States" to avoid implying the data is limited to 3 states.

---

### EUI Calculator Thresholds

**Code (lines 1716–1728):**
```javascript
if (eui <= 75) { interpretation = '⚡ That\'s an efficient building!'; }
else if (eui <= 150) { interpretation = '⚠️ Average efficiency — room for improvement.'; }
else { interpretation = '🔴 That building wastes a lot of energy — needs fixing!'; }
```

**Analysis:** **OK**. US commercial building average EUI is approximately 93 kBTU/sqft (CBECS 2018). Under this scheme:
- ≤75 = efficient (below average) — correct
- 76–150 = average — this range is quite wide; 150 is well above average
- \>150 = wasteful — correct (includes hospitals, data centers, etc.)

The thresholds are reasonable simplifications for education.

---

### Feature Selection: Elevation as "wrong"

**Claim (lines 981–986):**
> Elevation: "Interesting idea, but elevation matters much less than the other clues."

**Analysis:** **OK**. While elevation can influence climate (and thus energy use), it's a weak predictor compared to floor area, weather data, and year built. For a simplified 3-feature selection exercise, marking it as less useful is appropriate.

---

### Feature Selection: Number of Floors as "wrong"

**Claim (lines 999–1003):**
> "Taller doesn't mean less efficient — a 2-story building and a 20-story building can have the same energy use per square foot. Floor area already captures size better."

**Analysis:** **OK**. This is pedagogically correct. When predicting EUI (energy per square foot), floor area is a much stronger predictor than number of floors. The explanation is accurate.

---

### Feature Selection: Owner's Name as "wrong"

**Claim (lines 990–995):**
> "A name doesn't tell us anything about energy use!"

**Analysis:** **OK**. This is a good teaching moment about irrelevant features. Owner identity has no causal relationship with building energy efficiency.

---

### EUI Analogy: "like miles-per-gallon, but for buildings"

**Claim (line 1054):**
> "EUI — like miles-per-gallon, but for buildings"

**Analysis:** **OK**. This is a standard and effective analogy used in energy education. EUI normalizes energy use by building size, just as MPG normalizes fuel use by distance.

---

### Impact Projection: "worst 10% retrofitting" estimate

**Code (lines 1344–1349):**
```javascript
const buildingSectorEstimate = Math.round(totalEmissions * 0.4);
const tenPctReduction = Math.round(buildingSectorEstimate * 0.1);
```

**Analysis:** **EXAGGERATED**. The code implies that retrofitting the worst 10% of buildings would reduce building sector emissions by 10%. In reality, the worst 10% of buildings might account for 20–40% of total building energy waste (energy waste follows a Pareto distribution). However, "retrofitting" doesn't eliminate 100% of a building's emissions — typically 20–50% reduction per retrofit.

So: worst 10% of buildings × their share of waste × retrofit efficiency = actual savings, which could be higher or lower than 10% of the total depending on the distribution.

**Recommendation:** The current phrasing ("If your AI identifies the worst 10% of buildings, retrofitting them could cut building emissions by ~X tonnes/year") is actually conservatively phrased since the worst 10% typically wastes disproportionately more. **OK** — the "could cut" qualifier provides sufficient hedging.

---

## Activity 3: Understanding AI

### Step 1: Building Prediction Game

**Training data (lines 714–735):**
| Building | Year | Size | Climate | Rating |
|----------|------|------|---------|--------|
| 🏢 | 1965 | 120K sqft | Cold | Low |
| 🏠 | 2018 | 30K sqft | Moderate | High |
| 🏬 | 1990 | 80K sqft | Hot | Medium |

**Mystery building:** 1958, 150K sqft, Cold → Low

**Analysis:** **OK**. The pattern (older + bigger + extreme climate = less efficient) is well-supported by building energy research. The examples are pedagogically effective with clear, consistent patterns. The second mystery building (2020, 20K sqft, Moderate → High) reinforces the pattern in reverse.

---

### Step 2: "Every AI follows three steps: Input → Model → Output"

**Analysis:** **OK** for the educational level. This is a standard simplification used in ML education. While real AI systems have many more components (preprocessing, feature engineering, post-processing, etc.), the Input → Model → Output framework is an effective mental model for beginners.

---

### Step 3: Training Accuracy Progression

**Code (lines 1517–1527):**
```
Cycle 1: Starting... → 47% → 62% → 78% → 91%
Cycle 2: 91% → 92% → 93% → 94% → 95%
Cycle 3: 95% → 95.5% → 96% → 96.5% → 97%
```

**Analysis:** **OK**. These are illustrative values, not from a real model. The key pedagogical points are correct:
1. Models improve with training (accurate)
2. Improvement slows over time — diminishing returns (accurate)
3. Final accuracy of 97% is achievable but not perfect (realistic for many tasks)

The "diminishing returns" narrative is an excellent teaching point about overfitting risk and the practical limits of more training data.

---

### Step 3: "100,000 building records" training data

**Claim (line 1216):**
> "The model trains on 100,000 building records"

**Analysis:** **OK**. Consistent with Activity 2's NREL dataset claim. 100,000 records is a realistic training set size for building energy prediction.

---

### Step 4: 75/25 Train-Test Split

**Claim (lines 896–905):**
> "75% Training" / "25% Test"

**Analysis:** **OK**. 75/25 is a standard and well-accepted train-test split ratio. Many ML textbooks recommend 70/30 or 80/20, and 75/25 falls squarely in this range.

---

### Step 4: Building Grid (16 buildings: 12 train, 4 test)

**Code (lines 1584–1623):**
```
16 buildings total: first 12 → training (75%), last 4 → test (25%)
```

**Analysis:** **OK**. 12/16 = 75% and 4/16 = 25%, consistent with the stated split.

---

### Step 5: Prediction Model (Simplified Rules)

**Code (lines 1666–1693):**
```javascript
// Age scoring
if (age < 1970) score += 3;
else if (age < 2000) score += 2;
else score += 1;

// Area scoring
if (area > 100) score += 3;
else if (area > 50) score += 2;
else score += 1;

// Climate scoring
if (climate === 'cold') score += 2;
else if (climate === 'hot') score += 2;
else score += 1;
```

**Analysis:** **OK**. The scoring rules correctly reflect real-world building energy patterns:
- Older buildings tend to have higher EUI (poor insulation, outdated HVAC) ✓
- Larger buildings tend to have higher total energy use ✓
- Extreme climates (cold or hot) increase energy demand ✓

The threshold at score ≥7 for "Low Efficiency", ≥4 for "Medium", <4 for "High" produces reasonable results. The disclaimer "This demo uses simplified rules, not real AI" (line 1732) is an important and honest caveat.

---

### Step 5: Impact Calculation (kBTU to tonnes CO₂)

**Code (lines 1700–1702):**
```javascript
const wastePerBuilding = efficiency === 'Low Efficiency' ? 45 : efficiency === 'Medium Efficiency' ? 20 : 5;
const co2PerBuilding = Math.round(wastePerBuilding * area * 0.05);
```

**Analysis:** **OK**.
- `wastePerBuilding` is in kBTU/sqft above baseline (reasonable values: 45 for low, 20 for medium, 5 for high efficiency)
- `area` is in thousands of sqft (from slider)
- Conversion: `kBTU/sqft × 1000 sqft × 0.05` = effective factor of 0.00005 tonnes CO₂ per kBTU
- Actual conversion: ~0.053 kg CO₂/kBTU (natural gas) to ~0.092 kg CO₂/kBTU (US grid electricity)
- 0.05 kg CO₂/kBTU (= 0.00005 tonnes) is a reasonable approximation for a gas/electric mix

---

### Step 5: Car Equivalence in Impact Box

**Code (line 1708):**
```javascript
const carsEquiv = Math.max(1, Math.round(co2PerBuilding / 4.6));
```

**Analysis:** **OK**. Correctly uses 4.6 tonnes/car/year.

---

### Climate Zone Lookup Table

**Code (Activity 3 lines 1164–1176, Activity 2 lines 1248–1284):**

Spot-checking key assignments:
| City | Assigned Zone | Accurate? |
|------|--------------|-----------|
| New York | Cold | **OK** — ASHRAE 4A, cold winters |
| Chicago | Cold | **OK** — ASHRAE 5A |
| Barcelona | Moderate | **OK** — Mediterranean |
| Madrid | Moderate | **IMPRECISE** — Madrid has very hot summers (40°C+) and cold winters. "Moderate" undersells the extremes. For building energy, its cooling needs are significant. |
| Los Angeles | Hot | **IMPRECISE** — LA is more "moderate" in climate science terms (Mediterranean). Cooling loads are moderate compared to Phoenix or Miami. |
| Córdoba (Spain) | Hot | **OK** — Among the hottest cities in Europe |
| Mexico City | Moderate | **OK** — High elevation keeps temperatures mild |
| Denver | Cold | **OK** — Cold, dry winters |
| Singapore | Hot | **OK** — Tropical |

**Recommendation:** These are broad 3-category simplifications. For educational purposes, they're acceptable. Madrid and LA are the most debatable but defensible.

---

### Completion Quiz 1: "What are the 3 parts of every AI system?"

**Correct answer:** "Input → Model → Output"
**Wrong answer:** "Data → Algorithm → Prediction"

**Analysis:** **IMPRECISE**. "Data → Algorithm → Prediction" is arguably equally correct from a technical standpoint — it's essentially the same concept with different terminology. The quiz is testing whether students remember the specific vocabulary used in the activity, not whether they understand the concept. This is pedagogically fine (reinforcing the framework taught) but the feedback should acknowledge that the "wrong" answer isn't technically wrong.

**Current feedback (line 1821):**
> "Data → Algorithm → Prediction is similar, but the Activity 3 framework uses Input → Model → Output. Try again!"

**Analysis:** **OK** — the feedback does acknowledge the similarity while reinforcing the activity's specific terminology.

---

### Completion Quiz 2: "How do we know the AI really learned?"

**Correct answer:** "Test it on data it hasn't seen before"

**Analysis:** **OK**. This correctly teaches the fundamental concept of generalization and out-of-sample testing.

---

## Cross-Activity Issues

### Inconsistent Cars Calculation

| Activity | Code | Divisor | Correct? |
|----------|------|---------|----------|
| Activity 1 (line 1131) | `t22 / 4600` | 4,600 | **BUG** — should be 4.6 |
| Activity 1 (line 1168) | `t22 / 4600` | 4,600 | **BUG** — should be 4.6 |
| Activity 1 (line 1506) | `reduction / 4600` | 4,600 | **BUG** — should be 4.6 |
| Activity 2 (line 1426) | `buildingEmissions / 4.6` | 4.6 | **OK** |
| Activity 3 (line 1708) | `co2PerBuilding / 4.6` | 4.6 | **OK** |

This is the highest-priority fix. Activity 1 is showing cars equivalents that are 1,000× too small.

---

### US-Centric Assumptions in a Global App

Both the 8.1 tonnes/household figure (Activity 1) and the 4.6 tonnes/car figure are US EPA figures. The app is used internationally. While perfect localization isn't practical:
- The 4.6 tonnes/car figure is reasonable globally (global average is ~4.0–5.0 tonnes depending on vehicle mix)
- The 8.1 tonnes/household figure is US-specific and significantly higher than most countries

**Recommendation:** Qualify the 8.1 tonnes figure as "US average" (already recommended above). The car figure is close enough globally.

---

### Inspector Days: 365 vs 260

Activity 2's `inspectorYears` uses 365 days, but its `milestones` array uses 260 working days (5/day week, 22/month, 260/year). These are internally inconsistent. The milestones are correct; the years calculation is wrong.

---

## Summary of Required Changes

### Priority 1: Bugs (Incorrect numbers shown to users)

1. **Activity 1, lines 1131, 1168, 1506:** Change `/4600` to `/4.6` for cars equivalent calculation
2. **Activity 2, line 1419:** Change `buildingCount / 365` to `buildingCount / 260` for inspector years

### Priority 2: Factual Corrections

3. **Activity 1, line 760:** Change `data-target="1.45"` to `data-target="1.5"` and add "above pre-industrial levels" to description
4. **Activity 1, line 770:** Change `data-target="50"` to `data-target="43"` and update text to "over 40% by 2030"

### Priority 3: Precision Improvements

5. **Activity 1, line 855:** Add "US average" qualifier to 8.1 tonnes/household
6. **Activity 2, line 1839:** Broaden NREL coverage description

### No Change Needed

- Climate TRACE description ✓
- "1 tonne ≈ 1 car in 3 months" ✓ (acceptable approximation)
- "40% of energy use" for buildings ✓
- Building count estimation (÷50) ✓ (noted as rough)
- "71% of buildings are a mystery" ✓
- EUI formula and thresholds ✓
- Feature selection correctness ✓
- Training accuracy progression ✓
- 75/25 train-test split ✓
- kBTU to tonnes conversion (×0.05) ✓
- Climate zone assignments ✓ (with minor quibbles on Madrid/LA)
- All quiz questions and feedback ✓
- "100,000 building records from NREL" ✓ (plausible)
- Simplified AI model rules ✓
- "This demo uses simplified rules, not real AI" disclaimer ✓

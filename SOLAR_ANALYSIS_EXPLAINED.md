# Solar Panel Cleaning Analysis: Technical Documentation & Explanation Guide

This document provides a comprehensive, deep-dive explanation of the Solar Cleaning Analyzer tool. It is designed to help you understand the internal logic, the mathematics, and the data processing steps so you can confidently explain the results to stakeholders, clients, or technical teams.

---

## 1. The Core Concept: "The Gap Analysis"

At its heart, this tool performs a **Gap Analysis**. It compares what the solar system _should_ be doing (Theoretical) versus what it _is_ actually doing (Actual).

### 💡 Explanation Tip for Stakeholders:

> "Imagine a car that is supposed to get 100 km per gallon. If we drive it and only get 80 km/gallon, we know something is wrong. In solar, the 'fuel' is sunlight. We measure how much fuel (sunlight) hits the panels and calculate how much energy we _should_ get. If we get less, the difference is usually due to dirt (soiling) or heat."

---

## 2. Data Processing Pipeline

Before any math happens, the data must be cleaned and aligned. This is often the most complex part of the code.

### Step A: The Inputs

We take two distinct data sources that don't naturally talk to each other:

1.  **The "Eye" (Lux Sensor)**: Reads light intensity every minute (or second).
2.  **The "Engine" (Inverter)**: Reports energy production every 30 minutes.

### Step B: Synchronization (The Merge)

Since the sensor reads every minute but the inverter only reports every 30 minutes, we cannot compare them directly row-by-row.

- **Logic**: We group the sensor data into 30-minute "buckets" to match the inverter's schedule.
- **Action**: If the inverter reports generation for `10:00 - 10:30`, we take all sensor readings from `10:00:00` to `10:29:59` and calculate their **average**.

### Step C: The "Golden Window" Filter (Crucial)

The tool discards most of the data. It **only** analyzes data between **10:00 AM and 1:00 PM**.

- **Why?**
  1.  **Angle of Incidence**: In the early morning/late afternoon, sunlight hits panels at a sharp angle, reflecting off the glass rather than being absorbed. This makes the math unreliable.
  2.  **Shadows**: Buildings or trees are most likely to cast shadows when the sun is low.
  3.  **Inverter Wake-up**: Inverters are inefficient at very low power (sunrise/sunset).
- **Result**: By focusing on 10 AM - 1 PM, we isolate the "Peak Performance" window where dirt is the primary variable affecting efficiency.

---

## 3. The Mathematics (Deep Dive)

Here are the exact formulas used, broken down variable by variable.

### Equation 1: Converting Light to Energy Potential

Sensors usually measure **Lux** (brightness to the human eye), but solar panels need **Irradiance** (energy in Watts).

**The Formula:**

```text
Irradiance (W/m²) = Lux Value / Conversion Factor
```

- **Lux Value**: The raw number from the sensor (e.g., 160,000).
- **Conversion Factor**: A calibrated number specific to the light spectrum in the region.
  - _Default for Qatar_: **165** (Derived from empirical data: ~165,000 Lux ≈ 1000 W/m²).
  - _Why it matters_: If this number is wrong, the whole analysis is wrong. If the PR is > 100%, this number is likely too low.

### Equation 2: Theoretical Generation

How much energy _should_ a clean system produce right now?

**The Formula:**

```text
Theoretical kWh = (Irradiance / 1000) × System Capacity × Duration
```

**Understanding the "Irradiance / 1000" Division:**

This is the most critical part to understand. Solar panels are rated under **Standard Test Conditions (STC)**, which is a laboratory environment defined by international standards:

- **1000 W/m²** irradiance (peak sunlight)
- 25°C cell temperature
- Air Mass 1.5 spectrum

When a manufacturer says "This is a 10 kWp system", they mean: _"Under perfect lab conditions (1000 W/m² sunlight), this system will produce 10 kW of power."_

**The Logic:**

- At **1000 W/m²** (full sun) → A 10 kWp system produces **10 kW**
- At **500 W/m²** (half sun) → The same system produces **5 kW**
- At **250 W/m²** (quarter sun) → It produces **2.5 kW**

The division by 1000 converts the actual irradiance into a "fraction of peak sunlight":

```text
Sun Fraction = Irradiance / 1000
```

**Real Example:**
If our sensor reads 800 W/m²:

- Sun Fraction = 800 / 1000 = **0.8** (80% of peak sunlight)
- Power = 0.8 × 10 kW = **8 kW** (80% of rated capacity)

This is why we divide by 1000 - it's the "reference point" that all solar panels are rated against.

**Breaking Down the Full Formula:**

- **Irradiance / 1000**: Converts real-world sunlight to a fraction of STC conditions
- **System Capacity**: The rated peak power (10 kWp means 10 kW at 1000 W/m²)
- **Duration**: Time period (0.5 hours for 30 minutes)

**Example Calculation:**

- Sensor reads: **82,500 Lux**
- Convert to Irradiance: $82,500 / 165 = \mathbf{500 \text{ W/m}^2}$
- Calculate Power: $(500 / 1000) \times 10 \text{ kW} = \mathbf{5 \text{ kW}}$ (Instantaneous Power)
- Calculate Energy (30 mins): $5 \text{ kW} \times 0.5 \text{ hours} = \mathbf{2.5 \text{ kWh}}$

### Equation 3: Performance Ratio (PR)

This is the "Scorecard" for the system.

**The Formula:**

```text
PR (%) = (Actual kWh / Theoretical kWh) × 100
```

- **Actual kWh**: What the inverter said it made.
- **Theoretical kWh**: What we calculated above.

**Example:**

- Theoretical: **2.5 kWh**
- Actual: **2.1 kWh**
- $PR = (2.1 / 2.5) \times 100 = \mathbf{84\%}$

### 💡 Explanation Tip for Stakeholders:

> "Think of PR as the 'Health Score'. A brand new, perfectly clean system might be 85-90% (losses due to wiring/heat are normal). If it drops to 70%, we know the panels are dirty."

---

## 4. Degradation Analysis (Predicting the Future)

This is how the tool decides _when_ to clean.

### Step 1: Establish the Baseline

We need to know what "Clean" looks like.

- **Logic**: The tool looks at the **first 3 days** of data (or the first 3 days after a recorded cleaning date).
- **Calculation**: It averages the PR of these days. Let's say Baseline PR = **85%**.

### Step 2: Determine Current State

- **Logic**: It looks at the **last 3 days** of data.
- **Calculation**: Let's say Current PR = **80%**.

### Step 3: Calculate the "Soiling Loss"

How much have we lost?

```text
Soiling Loss = Baseline PR - Current PR
Loss = 85% - 80% = 5%
```

### Step 4: Calculate the Rate of Decay

How fast are we losing power?

```text
Rate (%/day) = Soiling Loss / Days Elapsed
```

- _Example_: If it took 10 days to lose that 5%:
  - Rate = $5\% / 10 \text{ days} = \mathbf{0.5\% \text{ per day}}$

### Step 5: The Prediction (The "Magic" Number)

When should we clean? We set a threshold (e.g., we don't want to drop below 90% efficiency relative to baseline).

**The Formula:**

```text
Days to Clean = (Allowed Loss %) / (Daily Decay Rate)
```

- _Example_:
  - We are okay with losing 10% performance.
  - We lose 0.5% per day.
  - $10\% / 0.5\% = \mathbf{20 \text{ Days}}$
  - **Result**: "Recommended Cleaning Interval: Every 20 Days"

---

## 5. Temperature Analysis

Heat is the enemy of solar panels. They lose efficiency as they get hotter.

- **Ambient Temp**: The air temperature measured by the sensor.
- **Cell Temp**: The actual temperature of the glass/silicon, which is hotter than the air.
- **The Physics**: For every 1°C increase in temperature, a standard panel loses about **0.36%** of its power.

**How the tool uses this:**
The tool calculates a "Temperature Corrected PR". It tries to subtract the effect of heat to see _only_ the effect of dirt.

- If the PR drops even when it's cool outside, we know for sure it is dirt.
- If the PR drops only when it's hot, it might just be thermal loss, not dirt.

---

## 6. Troubleshooting Guide

When the numbers look weird, here is what to check.

### Scenario A: PR is consistently over 100% (e.g., 110%)

- **Meaning**: The system is producing _more_ energy than our math says is theoretically possible.
- **Cause**: We are underestimating the sunlight.
- **Fix**: The **Lux Conversion Factor** (165) is likely too high. Try lowering it to 150 or 145. This increases the calculated Irradiance, which increases Theoretical Output, which lowers the PR.

### Scenario B: PR is extremely low (e.g., 40%) on a sunny day

- **Meaning**: The system is producing way less than expected.
- **Cause**:
  1.  Panels are extremely dirty.
  2.  **Lux Conversion Factor** is too low (overestimating sunlight).
  3.  System Capacity is set wrong (e.g., set to 20kW for a 10kW system).

### Scenario C: "Max Ambient Temp" is huge (e.g., 75°C)

- **Cause**: The tool was previously displaying "Cell Temperature" (which gets very hot) instead of "Ambient Temperature".
- **Fix**: We updated the code to explicitly separate `Ambient` (Air) vs `Cell` (Panel) temperature.

---

## 7. Summary Checklist for Explaining

1.  **Inputs**: We combine minute-by-minute light data with 30-minute power data.
2.  **Filter**: We only look at 10 AM - 1 PM to ensure accuracy.
3.  **Baseline**: We find the "Clean" score (e.g., 85%).
4.  **Trend**: We measure how fast that score drops day by day.
5.  **Prediction**: We calculate how many days it takes to hit our "dirty" limit (e.g., 10% loss).

# Solar Panel Cleaning Recommendation System

## Overview

The system tracks solar panel cleaning history and automatically recommends when panels need cleaning based on performance degradation.

## How It Works

### Performance Ratio Tracking

The system calculates a **performance ratio** that compares actual solar output to expected output based on irradiance:

```
Performance Ratio = Actual Output / Theoretical Output

Where:
- Actual Output = When available, uses real sensor data from solar inverter
- Theoretical Output = Irradiance × Panel Area × Efficiency × (1 - System Losses)
```

### Cleaning Recommendations

The system uses a **10% degradation threshold** as the primary indicator:

1. **When Panels Are Clean** (Baseline)

   - After cleaning, record the performance ratio as a baseline
   - Typical clean panel ratio: 80-90%

2. **During Operation**

   - System continuously monitors current performance ratio
   - Calculates degradation: `(Baseline - Current) / Baseline × 100%`

3. **Cleaning Alert Triggers**
   - **≥15% degradation** → ⚠️ **URGENT**: Clean immediately
   - **≥10% degradation** → ⚡ **RECOMMENDED**: Schedule cleaning soon
   - **≥5% degradation** → 📊 **MONITORING**: Watch for trends
   - **<5% degradation** → ✅ **GOOD**: Panels performing well

### Additional Factors

- **Time-Based**: If 90+ days since last cleaning, recommend preventive maintenance
- **Historical Patterns**: Tracks average cleaning interval across all cleanings

## Database Schema

```sql
CREATE TABLE cleaning_records (
    id SERIAL PRIMARY KEY,
    cleaning_date TIMESTAMP NOT NULL,
    baseline_ratio REAL NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### 1. Get Cleaning Statistics

```bash
GET /api/cleaning/stats
```

**Response:**

```json
{
  "total_cleanings": 5,
  "last_cleaning": {
    "id": 10,
    "cleaning_date": "2025-10-20T10:30:00",
    "baseline_ratio": 0.87,
    "days_since": 8
  },
  "average_interval_days": 45,
  "degradation": {
    "has_baseline": true,
    "days_since_cleaning": 8,
    "baseline_ratio": 0.87,
    "current_ratio": 0.79,
    "degradation_percent": 9.2,
    "needs_cleaning": false,
    "recommendation": "📊 Monitoring: 9.2% performance loss..."
  },
  "cleaning_history": [...]
}
```

### 2. Record Cleaning Event

```bash
POST /api/cleaning/record
Content-Type: application/json

{
  "cleaning_date": "2025-10-28",
  "notes": "Annual maintenance cleaning"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Cleaning recorded successfully"
}
```

### 3. Get Cleaning History

```bash
GET /api/cleaning/history?limit=10
```

**Response:**

```json
{
  "history": [
    {
      "id": 10,
      "cleaning_date": "2025-10-20T10:30:00",
      "baseline_ratio": 0.87,
      "notes": "Routine cleaning",
      "created_at": "2025-10-20T10:35:00"
    },
    ...
  ]
}
```

## User Interface

### Solar KPI Page (`/kpi/solar`)

The Solar Array KPIs page now includes:

1. **Cleaning Status Card**

   - Visual status indicator (✅ 📊 ⚡ ⚠️)
   - Current performance metrics
   - Days since last cleaning
   - Degradation percentage
   - Actionable recommendation

2. **Record Cleaning Button**

   - Opens modal to log cleaning events
   - Auto-fills with today's date
   - Optional notes field

3. **Cleaning History Table**
   - Shows last 5 cleaning events
   - Date, days ago, baseline ratio, notes
   - Average cleaning interval (if >1 cleaning)

## Usage Workflow

### Initial Setup

1. **Clean Your Panels**
   - Physically clean all solar panels
2. **Record the Cleaning**

   - Go to Solar KPI page
   - Click "Record Cleaning" button
   - Select cleaning date (today)
   - Add optional notes
   - Submit

3. **Baseline Established**
   - System captures current performance ratio
   - This becomes your clean panel baseline
   - Monitoring begins automatically

### Ongoing Monitoring

The system automatically:

- Calculates degradation every 5 seconds
- Updates cleaning recommendation
- Tracks days since last cleaning
- Shows visual status indicators

### When to Clean

Follow the system recommendations:

- **URGENT (≥15%)**: Clean today if possible
- **RECOMMENDED (≥10%)**: Schedule within 1-2 weeks
- **MONITORING (5-10%)**: Keep watching, plan ahead
- **GOOD (<5%)**: No action needed

## Integration with Actual Solar Output

**CURRENTLY**: System uses irradiance-based calculations as a placeholder.

**WHEN SOLAR OUTPUT SENSOR IS AVAILABLE**:

1. Update `cleaning_tracker.py`:

```python
def calculate_current_performance_ratio(self, hours: int = 6) -> float:
    # Fetch actual solar output from inverter/sensor
    actual_output = fetch_solar_output(hours)  # Your sensor integration

    # Fetch irradiance
    avg_irradiance = fetch_avg_irradiance(hours)

    # Calculate theoretical output
    theoretical = (avg_irradiance * PANEL_AREA * EFFICIENCY * (1 - LOSSES)) / 1000

    # Return ratio
    return actual_output / theoretical if theoretical > 0 else 0.0
```

2. No other changes needed - the system will automatically use real data!

## Best Practices

### Recording Cleanings

- Record cleaning immediately after completion
- Add notes about weather, soiling type, special conditions
- Record even if you only did partial cleaning (note it)

### Interpreting Results

- **Morning/Evening**: Expect lower ratios (sun angle)
- **Cloudy Days**: May show false degradation
- **After Rain**: Natural cleaning may improve ratio
- **Dusty Periods**: Faster degradation expected

### Calibration

- First baseline should be after thorough cleaning
- Re-baseline after panel repairs or upgrades
- If ratio seems off, verify sensor calibration

## Example Scenarios

### Scenario 1: Desert Installation

- Baseline: 85% (after cleaning)
- After 30 days: 78% → 8.2% degradation (monitoring)
- After 45 days: 73% → 14.1% degradation (RECOMMENDED)
- **Action**: Schedule cleaning

### Scenario 2: Coastal Area

- Baseline: 87% (after cleaning)
- After 60 days: 84% → 3.4% degradation (good)
- After 90 days: 82% → 5.7% degradation (monitoring)
- **Action**: Plan cleaning, not urgent

### Scenario 3: After Rain

- Before rain: 75% (10% degradation)
- After rain: 82% (improved naturally!)
- **Action**: Monitor, rain provided partial cleaning

## Technical Notes

### Performance Ratio Calculation

The system averages data over the last 6 hours to smooth out transient effects.

### Threshold Justification

- **10% threshold**: Industry standard for triggering cleaning
- Studies show 10-15% loss is economically optimal cleaning point
- Beyond 15%, energy loss exceeds cleaning cost

### Future Enhancements

1. **Machine Learning**: Predict optimal cleaning schedule based on:
   - Historical patterns
   - Weather data
   - Seasonal variations
2. **Cost Analysis**: Calculate ROI of cleaning vs. energy loss

3. **Automated Alerts**: Email/SMS when cleaning recommended

4. **Weather Integration**: Factor in rain forecasts, dust storms

5. **Regional Presets**: Default thresholds for different climates

## Troubleshooting

### "No Baseline Set" Message

- **Cause**: No cleaning has been recorded yet
- **Solution**: Record your first cleaning to establish baseline

### Ratio Seems Too Low

- Check sensor calibration
- Verify panel specifications in `config.py`
- Consider shading, panel age, actual conditions

### Degradation Shows Negative

- System shows 0% instead
- May occur after natural cleaning (rain)
- This is normal - panels can get cleaner naturally

### History Not Showing

- Check database connection
- Verify `cleaning_records` table exists
- Check browser console for errors

## Configuration

Edit in `config.py`:

```python
MANUAL_CONFIG = {
    "solar.panel_area": 100.0,  # m² - Your actual panel area
    "solar.panel_efficiency": 20.0,  # % - Your panel specs
    "solar.system_losses": 15.0,  # % - Inverter, wiring, etc.
}
```

## Support

For issues or questions:

1. Check browser console for errors
2. Verify database connectivity
3. Review `/api/health` endpoint
4. Check sensor data quality in dashboard

---

**Version**: 1.0  
**Last Updated**: October 28, 2025  
**Status**: Production Ready (awaiting actual solar output sensor integration)

# Timezone Configuration - Qatar Time (UTC+3)

## Overview

All timestamps in the ZDEnergy Analytics system are now stored and displayed in **Qatar time (UTC+3)** using the `Asia/Qatar` timezone.

## Implementation Details

### 1. Database Layer (`db_manager.py`)

**Timezone Import:**

```python
from zoneinfo import ZoneInfo
QATAR_TZ = ZoneInfo("Asia/Qatar")
```

**Methods Updated:**

#### `insert_sensor_reading()`

- Converts all incoming timestamps to Qatar time before storage
- If timestamp is naive (no timezone), assumes Qatar time
- If timestamp has different timezone, converts to Qatar time
- Stores in PostgreSQL as `TIMESTAMPTZ` (timestamp with timezone)

```python
if timestamp is None:
    timestamp = datetime.now(QATAR_TZ)
elif timestamp.tzinfo is None:
    timestamp = timestamp.replace(tzinfo=QATAR_TZ)
else:
    timestamp = timestamp.astimezone(QATAR_TZ)
```

#### `get_readings_by_date(date_str)`

- Interprets date string as Qatar time date
- Creates start (00:00:00) and end (23:59:59) in Qatar timezone
- Returns all readings within that Qatar time day
- Converts database timestamps to Qatar time for display

#### `get_readings_by_window(minutes)`

- Uses Qatar time as reference for "now"
- Calculates time window relative to current Qatar time

#### `get_readings_by_time_range(start, end)`

- Converts start/end times to Qatar timezone
- Ensures timezone-aware queries

#### `get_date_range()`

- Uses PostgreSQL's `AT TIME ZONE 'Asia/Qatar'` for date extraction
- Returns min/max dates in Qatar time

### 2. Backend API (`readings.py`)

**Timezone Import:**

```python
from zoneinfo import ZoneInfo
QATAR_TZ = ZoneInfo("Asia/Qatar")
```

**Data Ingestion (`_ingest_line()`):**

- Parses incoming timestamps
- Converts to Qatar time if naive or from different timezone
- Stores in database with Qatar timezone
- Debug logging shows timezone: `YYYY-MM-DD HH:MM:SS +03`

```python
timestamp = datetime.fromisoformat(reading['time_iso'])
if timestamp.tzinfo is None:
    timestamp = timestamp.replace(tzinfo=QATAR_TZ)
else:
    timestamp = timestamp.astimezone(QATAR_TZ)
```

### 3. Database Schema

**Table: sensor_readings**

```sql
timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

PostgreSQL's `TIMESTAMPTZ` type:

- Stores timestamps in UTC internally
- Converts to specified timezone on retrieval
- Supports timezone-aware operations
- Handles daylight saving time automatically

## Timezone Behavior

### Storage

- All timestamps stored in PostgreSQL as UTC (internal)
- Converted to Qatar time when queried
- Database timezone-aware (TIMESTAMPTZ)

### Queries

- Date ranges interpreted in Qatar time
- "Today" means today in Qatar
- Time windows relative to current Qatar time

### Display

- Frontend receives ISO format timestamps with timezone: `2025-10-16T14:30:00+03:00`
- Browser converts to local time automatically for display
- Charts show data in user's local timezone

## Python zoneinfo Module

### Requirements

- Python 3.9+ (built-in zoneinfo)
- Or install `tzdata` package for timezone data

### Installation (if needed)

```bash
pip install tzdata
```

### Available in System

✅ Python 3.9.4 has zoneinfo built-in
✅ No additional dependencies needed

## Testing Timezone Handling

### Test 1: Insert with no timezone

```python
db = get_db_manager()
timestamp = datetime(2025, 10, 16, 14, 30, 0)  # Naive
db.insert_sensor_reading(temperature=25.0, timestamp=timestamp)
# Stored as: 2025-10-16 14:30:00+03 (Qatar time)
```

### Test 2: Insert with different timezone

```python
from zoneinfo import ZoneInfo
timestamp = datetime(2025, 10, 16, 14, 30, 0, tzinfo=ZoneInfo("UTC"))
db.insert_sensor_reading(temperature=25.0, timestamp=timestamp)
# Stored as: 2025-10-16 17:30:00+03 (converted from UTC to Qatar)
```

### Test 3: Query by date

```python
readings = db.get_readings_by_date("2025-10-16")
# Returns all readings from 2025-10-16 00:00:00+03 to 2025-10-16 23:59:59+03
```

### Test 4: Query by window

```python
readings = db.get_readings_by_window(60)  # Last hour
# Uses current Qatar time as reference
```

## Frontend Display

### JavaScript Date Handling

```javascript
const timestamp = "2025-10-16T14:30:00+03:00";
const date = new Date(timestamp);
// Browser automatically converts to local timezone for display
```

### Chart.js Time Axis

```javascript
scales: {
    x: {
        type: 'time',
        time: { tooltipFormat: 'yyyy-MM-dd HH:mm:ss' }
    }
}
```

- Displays times in user's browser timezone
- Tooltips show local time
- X-axis labels in local time

## API Response Format

### `/api/data?window=60`

```json
{
  "readings": [
    {
      "time": "2025-10-16T14:30:00+03:00",
      "temp": 25.5,
      "rh": 60.2,
      "lux": 1234.5,
      "irradiance": 9.72
    }
  ],
  "count": 100,
  "source": "database",
  "window_minutes": 60
}
```

### `/api/data?date=2025-10-16`

```json
{
    "readings": [...],
    "count": 1440,
    "source": "database",
    "date": "2025-10-16"
}
```

Note: "date" refers to Qatar time date

### `/api/dates`

```json
{
  "date_range": {
    "min_date": "2025-10-01",
    "max_date": "2025-10-16"
  },
  "total_readings": 50000
}
```

Note: Dates are in Qatar timezone

## Common Scenarios

### Scenario 1: Sensor sends data with no timezone

```
Input: {"time": "2025-10-16 14:30:00", ...}
Assumption: Qatar time
Storage: 2025-10-16 14:30:00+03
```

### Scenario 2: Sensor sends data with UTC timezone

```
Input: {"time": "2025-10-16 11:30:00Z", ...}
Conversion: UTC → Qatar (+3 hours)
Storage: 2025-10-16 14:30:00+03
```

### Scenario 3: User selects date in date picker

```
User selects: 2025-10-16
Interpretation: Qatar time date
Query range: 2025-10-16 00:00:00+03 to 2025-10-16 23:59:59+03
```

### Scenario 4: Live data display

```
Current time: Uses datetime.now(QATAR_TZ)
Last hour query: Current Qatar time - 60 minutes
Display: Converted to user's browser timezone
```

## Daylight Saving Time (DST)

**Qatar does NOT observe DST:**

- Fixed UTC+3 offset year-round
- No seasonal time changes
- No DST transition handling needed
- Consistent 3-hour offset from UTC

## Migration from Previous Version

### If you have existing data without timezone:

**Option 1: Update existing records (if data was in Qatar time)**

```sql
UPDATE sensor_readings
SET timestamp = timestamp AT TIME ZONE 'Asia/Qatar'
WHERE timestamp IS NOT NULL;
```

**Option 2: If data was in UTC**

```sql
UPDATE sensor_readings
SET timestamp = (timestamp AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Qatar'
WHERE timestamp IS NOT NULL;
```

**Option 3: Leave as-is (mixed data)**

- New data will be stored with Qatar timezone
- Old data queries may need special handling

## Troubleshooting

### Issue: "zoneinfo module not found"

**Solution:**

```bash
pip install tzdata
```

### Issue: "timestamp out of range"

**Check:** Date format in sensor data
**Fix:** Ensure dates are valid (2025-10-16, not 2025-13-99)

### Issue: "times seem off by 3 hours"

**Cause:** Mixing timezone-aware and naive datetimes
**Fix:** Always use timezone-aware datetimes throughout

### Issue: Date picker shows wrong dates

**Cause:** Browser timezone different from Qatar
**Note:** This is expected - dates represent Qatar time
**Solution:** Add timezone indicator in UI: "📅 View Date (Qatar Time):"

## Best Practices

1. **Always use timezone-aware datetimes**

   - Use `datetime.now(QATAR_TZ)` not `datetime.now()`
   - Use `.replace(tzinfo=QATAR_TZ)` for naive timestamps

2. **Let PostgreSQL handle timezone conversions**

   - Store as TIMESTAMPTZ
   - Use `AT TIME ZONE` in queries when needed

3. **Document timezone assumptions**

   - Comment where Qatar time is assumed
   - Clarify in API documentation

4. **Test with different timezones**

   - Test from UTC
   - Test from other timezones
   - Verify conversions are correct

5. **Consider user display preferences**
   - Current: Shows in user's browser timezone
   - Future: Add timezone selector in UI

## Future Enhancements

1. **UI Timezone Indicator**

   - Show "All times in Qatar Time (UTC+3)" notice
   - Add clock showing current Qatar time

2. **Timezone Selector**

   - Let users choose display timezone
   - Keep storage in Qatar time
   - Convert for display only

3. **Multi-timezone Support**

   - Store sensor location timezone
   - Display in user's preferred timezone
   - Keep original timezone for accuracy

4. **Timezone Awareness in Charts**
   - Add timezone label to chart titles
   - Show UTC offset in tooltips
   - Highlight timezone changes if any

## Summary

✅ All timestamps now stored in Qatar time (UTC+3)  
✅ Database uses TIMESTAMPTZ for proper timezone handling  
✅ Automatic conversion from naive/different timezones  
✅ Date picker interprets dates as Qatar dates  
✅ Time windows relative to current Qatar time  
✅ No DST complications (Qatar doesn't observe DST)  
✅ Python 3.9+ zoneinfo support (no external dependencies)

**The entire system is now timezone-aware and consistent with Qatar time! 🇶🇦 ⏰**

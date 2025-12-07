# CSV Data Export Feature - User Guide

## Overview

The dashboard now includes a powerful CSV export feature that allows you to download sensor data in Excel-compatible CSV format for analysis, reporting, or archival purposes.

## Location

The CSV export section is located on the main dashboard (homepage) below the current readings cards.

## Export Options

### 1. Last 24 Hours (Default) ⏰

**Use when:** You need recent data for quick analysis

**What it exports:**

- All sensor readings from the last 24 hours
- Sorted chronologically (oldest to newest)

**Filename:** `sensor_data_last_24h.csv`

**How to use:**

1. Select "Last 24 Hours" radio button
2. Click "📥 Download CSV"
3. File downloads immediately

---

### 2. Single Date 📅

**Use when:** You need data from a specific day

**What it exports:**

- All readings from 00:00:00 to 23:59:59 on the selected date (Qatar time)
- Complete daily data

**Filename:** `sensor_data_YYYY-MM-DD.csv`

**How to use:**

1. Select "Single Date" radio button
2. Date input field becomes enabled
3. Pick a date from the calendar
4. Click "📥 Download CSV"

**Example:**

- Select: October 19, 2025
- Downloads: `sensor_data_2025-10-19.csv`
- Contains: All data from Oct 19, 2025 (Qatar time)

---

### 3. Date Range 📊

**Use when:** You need data spanning multiple days

**What it exports:**

- All readings between start date (00:00:00) and end date (23:59:59)
- Can span days, weeks, or months

**Filename:** `sensor_data_YYYY-MM-DD_to_YYYY-MM-DD.csv`

**How to use:**

1. Select "Date Range" radio button
2. Both date input fields become enabled
3. Pick start date
4. Pick end date (must be after start date)
5. Click "📥 Download CSV"

**Example:**

- Start: October 15, 2025
- End: October 19, 2025
- Downloads: `sensor_data_2025-10-15_to_2025-10-19.csv`
- Contains: 5 days of data

**Validation:**

- End date must be after start date
- System will alert you if dates are invalid

---

### 4. All Available Data 💾

**Use when:** You need complete historical records

**What it exports:**

- Every reading in the database
- From the first recorded reading to the most recent
- Can be very large!

**Filename:** `sensor_data_all.csv`

**How to use:**

1. Select "All Available Data" radio button
2. Click "📥 Download CSV"
3. Wait for download (may take longer for large datasets)

**Warning:** ⚠️

- This can be a large file if you have months of data
- May take several seconds to generate
- Recommended for periodic backups only

---

## CSV File Format

### Columns

```csv
Timestamp,Temperature (°C),Humidity (%),Lux,Irradiance (W/m²)
```

### Sample Data

```csv
Timestamp,Temperature (°C),Humidity (%),Lux,Irradiance (W/m²)
2025-10-19 14:30:00,25.34,48.23,85420.50,672.604
2025-10-19 14:30:02,26.12,46.89,87650.00,690.157
2025-10-19 14:30:04,25.89,47.45,89123.00,701.756
```

### Data Format Details

**Timestamp:**

- Format: `YYYY-MM-DD HH:MM:SS`
- Timezone: Qatar time (UTC+3)
- 24-hour format

**Temperature:**

- Unit: Degrees Celsius (°C)
- Precision: 2 decimal places
- Example: `25.34`

**Humidity:**

- Unit: Percentage (%)
- Precision: 2 decimal places
- Example: `48.23`

**Lux:**

- Unit: Lux (light intensity)
- Precision: 2 decimal places
- Example: `85420.50`

**Irradiance:**

- Unit: Watts per square meter (W/m²)
- Precision: 3 decimal places
- Calculated: `lux / 127.0`
- Example: `672.604`

---

## Opening CSV Files

### Microsoft Excel

1. Double-click the downloaded CSV file
2. Excel opens with data in columns
3. Data is automatically formatted
4. Ready for analysis, charts, pivot tables

**Tips:**

- Use "Format as Table" for better readability
- Create charts directly from data
- Use filters to analyze specific time periods

### Google Sheets

1. Go to Google Sheets
2. File → Import
3. Upload the CSV file
4. Select "Comma" as separator
5. Click "Import data"

### LibreOffice Calc

1. Open LibreOffice Calc
2. File → Open
3. Select the CSV file
4. Choose UTF-8 encoding
5. Separator: Comma

### Python/Pandas

```python
import pandas as pd

# Read CSV
df = pd.read_csv('sensor_data_2025-10-19.csv')

# Convert timestamp to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Basic statistics
print(df.describe())

# Plot temperature
df.plot(x='Timestamp', y='Temperature (°C)')
```

### R Programming

```r
# Read CSV
data <- read.csv('sensor_data_2025-10-19.csv')

# Convert timestamp
data$Timestamp <- as.POSIXct(data$Timestamp)

# Summary statistics
summary(data)

# Plot
plot(data$Timestamp, data$Temperature..°C., type='l')
```

---

## Use Cases

### 1. Daily Reports

**Scenario:** Generate daily summary reports for management

**Steps:**

1. Select "Single Date"
2. Choose yesterday's date
3. Download CSV
4. Open in Excel
5. Create summary charts
6. Email to team

**Frequency:** Daily

---

### 2. Weekly Analysis

**Scenario:** Analyze trends over the past week

**Steps:**

1. Select "Date Range"
2. Start: 7 days ago
3. End: Today
4. Download CSV
5. Analyze in Excel/Python
6. Identify patterns

**Frequency:** Weekly

---

### 3. Monthly Backup

**Scenario:** Archive data for compliance

**Steps:**

1. At end of month, select "Date Range"
2. Start: First day of last month
3. End: Last day of last month
4. Download CSV
5. Store in backup folder
6. Keep for records

**Frequency:** Monthly

---

### 4. Comparative Analysis

**Scenario:** Compare same date across different months

**Steps:**

1. Download Oct 15, 2025 data
2. Download Sep 15, 2025 data
3. Download Aug 15, 2025 data
4. Combine in Excel
5. Create comparison charts
6. Identify seasonal patterns

**Frequency:** As needed

---

### 5. Research & Development

**Scenario:** Detailed analysis for system optimization

**Steps:**

1. Select "All Available Data"
2. Download complete dataset
3. Import into data analysis tool
4. Perform statistical analysis
5. Identify optimization opportunities

**Frequency:** Quarterly

---

## Tips & Best Practices

### ✅ Best Practices

1. **Regular Backups**

   - Export "All Available Data" monthly
   - Store in secure location
   - Keep multiple versions

2. **Organized Filing**

   - Create folder structure: `Data_Exports/YYYY/MM/`
   - Use descriptive filenames
   - Include date in filename

3. **Validation**

   - Open CSV immediately after download
   - Check data completeness
   - Verify date ranges

4. **Analysis Workflow**

   - Export → Open → Validate → Analyze → Report
   - Keep original CSV unchanged
   - Work on copies for analysis

5. **Performance**
   - Use date ranges for large exports
   - Avoid exporting "All Data" frequently
   - Export during off-peak hours for very large datasets

### ⚠️ Common Pitfalls

1. **Wrong Date Selection**

   - ❌ Selecting future dates (no data)
   - ✅ Use date picker constraints

2. **Inverted Date Range**

   - ❌ End date before start date
   - ✅ System validates and alerts

3. **Expecting Live Data**

   - ❌ Exporting before data is stored
   - ✅ Wait a few minutes for data collection

4. **Large File Handling**

   - ❌ Opening 6 months of data in Excel directly
   - ✅ Use Python/R for large datasets

5. **Timezone Confusion**
   - ❌ Forgetting data is in Qatar time
   - ✅ Remember UTC+3 when analyzing

---

## File Size Estimates

Based on 2-second reading interval:

| Duration | Readings    | File Size (approx) |
| -------- | ----------- | ------------------ |
| 1 hour   | 1,800       | ~200 KB            |
| 1 day    | 43,200      | ~4 MB              |
| 1 week   | 302,400     | ~30 MB             |
| 1 month  | ~1,300,000  | ~130 MB            |
| 1 year   | ~15,800,000 | ~1.5 GB            |

**Note:** File size depends on reading frequency and precision

---

## Troubleshooting

### Issue: Download doesn't start

**Cause:** Browser blocking popup/download
**Solution:**

- Allow downloads from localhost
- Check browser download settings
- Try different browser

### Issue: CSV file is empty

**Cause:** No data for selected period
**Solution:**

- Check if data exists for that date
- Verify system was running
- Try "Last 24 Hours" to confirm recent data

### Issue: Wrong date format in Excel

**Cause:** Excel regional settings
**Solution:**

- Excel → Data → Text to Columns
- Choose "Delimited" → Comma
- Format timestamp column as Date/Time

### Issue: Special characters in Excel

**Cause:** UTF-8 encoding issue
**Solution:**

- Open Excel
- Data → From Text/CSV
- Choose UTF-8 encoding
- Import

### Issue: Export takes too long

**Cause:** Very large dataset
**Solution:**

- Use smaller date ranges
- Export during off-peak hours
- Use Python/database tools for bulk exports

---

## API Endpoint (Advanced)

For programmatic access:

### Base URL

```
http://localhost:5000/api/export/csv
```

### Parameters

**Last 24 hours:**

```
GET /api/export/csv
```

**Single date:**

```
GET /api/export/csv?start_date=2025-10-19
```

**Date range:**

```
GET /api/export/csv?start_date=2025-10-15&end_date=2025-10-19
```

**All data:**

```
GET /api/export/csv?all=true
```

### cURL Examples

**Download last 24 hours:**

```bash
curl -O http://localhost:5000/api/export/csv
```

**Download specific date:**

```bash
curl -o data.csv "http://localhost:5000/api/export/csv?start_date=2025-10-19"
```

**Download date range:**

```bash
curl -o data.csv "http://localhost:5000/api/export/csv?start_date=2025-10-15&end_date=2025-10-19"
```

**Download all data:**

```bash
curl -o all_data.csv "http://localhost:5000/api/export/csv?all=true"
```

### Python Script Example

```python
import requests
from datetime import datetime, timedelta

# Download last week's data
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

url = f"http://localhost:5000/api/export/csv"
params = {
    'start_date': start_date.strftime('%Y-%m-%d'),
    'end_date': end_date.strftime('%Y-%m-%d')
}

response = requests.get(url, params=params)

# Save to file
filename = f"sensor_data_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.csv"
with open(filename, 'w') as f:
    f.write(response.text)

print(f"Downloaded: {filename}")
```

---

## Summary

✅ **Four export options** - Last 24h, Single Date, Date Range, All Data  
✅ **Excel-compatible CSV format** - Opens directly in spreadsheet software  
✅ **Clean, structured data** - Ready for immediate analysis  
✅ **Flexible date selection** - Choose exactly what you need  
✅ **Professional filenames** - Automatically named with dates  
✅ **Qatar timezone** - All timestamps in local time  
✅ **Easy to use** - Simple radio buttons and date pickers  
✅ **API access** - Programmatic export for automation

**Start exporting your data now from the dashboard homepage!** 📊📥

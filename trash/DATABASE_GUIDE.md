# 🗄️ Database Integration Guide

## Overview

Your ZDEnergy application now stores all sensor data in a **PostgreSQL database** hosted on Digital Ocean. This ensures data persistence and allows historical analysis.

## Architecture

### Dual Storage System

1. **Database (PostgreSQL)** - Persistent storage for all historical data

   - All sensor readings saved permanently
   - KPI snapshots for trend analysis
   - Survives server restarts

2. **In-Memory Buffer** - Fast access for real-time display
   - Last 1000 readings cached in RAM
   - Provides instant response for dashboard
   - Falls back to database if needed

### Database Schema

#### `sensor_readings` table

```sql
- id (serial primary key)
- timestamp (timestamptz) - indexed for fast queries
- temperature (real)
- humidity (real)
- lux (real)
- irradiance (real)
- created_at (timestamptz)
```

#### `kpi_snapshots` table

```sql
- id (serial primary key)
- timestamp (timestamptz) - indexed
- kpi_name (varchar)
- value (real)
- unit (varchar)
- metadata (jsonb)
- created_at (timestamptz)
```

#### `system_config` table

```sql
- id (serial primary key)
- config_key (varchar unique)
- config_value (text)
- description (text)
- updated_at (timestamptz)
```

## Setup Instructions

### 1. Install Required Packages

```powershell
pip install psycopg2-binary python-dotenv
```

Or install all dependencies:

```powershell
pip install -r requirements.txt
```

### 2. Environment Configuration

Your database credentials are stored in `.env` file:

```env
DB_USERNAME=doadmin
DB_PASSWORD=your_database_password_here
DB_HOST=your-database-host.db.ondigitalocean.com
DB_PORT=25060
DB_NAME=defaultdb
DB_SSLMODE=require
```

**⚠️ IMPORTANT**: The `.env` file is in `.gitignore` and will NOT be committed to Git.

### 3. Test Database Connection

Before starting the main application, test your database:

```powershell
python test_database.py
```

This will:

- ✅ Verify connection to Digital Ocean database
- ✅ Create tables if they don't exist
- ✅ Test insert/query operations
- ✅ Display database statistics

### 4. Start the Application

```powershell
python readings.py
```

The application will:

1. Initialize database connection pool
2. Create schema if needed
3. Start TCP server (port 6000)
4. Start Flask web server (port 5000)

## How It Works

### Data Flow

```
Sensor Gateway (TCP)
    ↓
readings.py (Port 6000)
    ↓
┌─────────────────┬──────────────────┐
│  In-Memory      │   PostgreSQL     │
│  Buffer         │   Database       │
│  (1000 latest)  │   (all data)     │
└─────────────────┴──────────────────┘
    ↓                    ↓
Dashboard              Historical
(real-time)            Analysis
```

### When Data is Received

1. **Parse** - JSON data validated
2. **Memory** - Stored in deque (last 1000)
3. **Database** - Inserted into PostgreSQL
4. **Log** - Confirmation printed

Example log output:

```
Stored reading: t=2025-10-15T10:30:45 temp=25.50°C rh=60.00% lux=500.00
```

### Querying Data

#### Real-time Data (from memory)

```
GET /api/data?limit=100
```

#### Historical Data (from database)

```
GET /api/data?source=database&limit=1000
GET /api/data?minutes=60  (automatically uses database)
```

## API Endpoints

### `/api/data` - Get Sensor Readings

**Query Parameters:**

- `limit` - Number of records (default: 300, max: 10000)
- `source` - `memory` or `database` (default: memory)
- `minutes` - Time window (auto-switches to database)

**Examples:**

```javascript
// Last 100 readings from memory (fast)
fetch("/api/data?limit=100");

// Last 5000 readings from database
fetch("/api/data?source=database&limit=5000");

// Last 2 hours of data
fetch("/api/data?minutes=120");
```

### `/api/status` - System Status

Returns:

```json
{
  "samples_in_memory": 1000,
  "latest": {...},
  "database_stats": {
    "total_readings": 150000,
    "total_kpi_snapshots": 5000,
    "oldest_reading": "2025-10-01T00:00:00",
    "newest_reading": "2025-10-15T10:30:45"
  },
  "tcp_port": 6000,
  "http_port": 5000,
  ...
}
```

## Database Manager API

The `db_manager.py` module provides:

### Get Database Instance

```python
from db_manager import get_db_manager

db = get_db_manager()
```

### Insert Sensor Reading

```python
record_id = db.insert_sensor_reading(
    temperature=25.5,
    humidity=60.0,
    lux=500.0,
    irradiance=3.94,
    timestamp=datetime.now()
)
```

### Query Latest Readings

```python
# Get last 100 readings
readings = db.get_latest_readings(limit=100)

# Get readings from last hour
readings = db.get_readings_by_window(window_minutes=60)

# Get readings between timestamps
readings = db.get_readings_by_time_range(start_time, end_time)
```

### Insert KPI Snapshot

```python
kpi_id = db.insert_kpi_snapshot(
    kpi_name="solar_generation",
    value=2.5,
    unit="kW",
    metadata={"panel_area": 20}
)
```

### Get Statistics

```python
stats = db.get_statistics()
print(f"Total readings: {stats['total_readings']}")
```

### Data Cleanup

```python
# Delete data older than 90 days
deleted_count = db.cleanup_old_data(days_to_keep=90)
```

## Connection Pooling

The database manager uses **connection pooling** for efficiency:

- **Min connections**: 1
- **Max connections**: 10
- **Thread-safe**: Yes
- **Auto-reconnect**: Yes

This ensures:

- Fast queries (reuses connections)
- Handles concurrent requests
- No connection leaks

## Troubleshooting

### Connection Failed

**Error**: `Failed to create connection pool`

**Solutions**:

1. Check `.env` file has correct credentials
2. Verify database is running on Digital Ocean dashboard
3. Check firewall allows your IP address
4. Verify SSL mode is `require`

### Slow Queries

**Error**: Queries take too long

**Solutions**:

1. Add more indices (done automatically)
2. Limit query results with `limit` parameter
3. Use time windows instead of full table scans

### Database Full

**Error**: Storage limit reached

**Solutions**:

1. Run cleanup: `db.cleanup_old_data(days_to_keep=30)`
2. Upgrade database plan on Digital Ocean
3. Archive old data to backup

### SSL Certificate Error

**Error**: SSL connection failed

**Solutions**:

1. Ensure `DB_SSLMODE=require` in `.env`
2. Check system CA certificates are up to date
3. Try `sslmode=verify-full` if issues persist

## Backup Strategy

### Automated Backups (Digital Ocean)

Your managed database includes:

- Daily automated backups (retained 7 days)
- Point-in-time recovery
- Accessible via Digital Ocean dashboard

### Manual Backup

Create a manual backup:

```powershell
# Export to SQL file
pg_dump -h zd-energy-db-do-user-22778792-0.f.db.ondigitalocean.com `
        -p 25060 `
        -U doadmin `
        -d defaultdb `
        -F p `
        -f backup_$(Get-Date -Format 'yyyy-MM-dd').sql
```

### Restore from Backup

```powershell
psql -h zd-energy-db-do-user-22778792-0.f.db.ondigitalocean.com `
     -p 25060 `
     -U doadmin `
     -d defaultdb `
     -f backup_2025-10-15.sql
```

## Performance Tips

### 1. Use Time-Based Queries

```python
# Good - uses indexed timestamp
readings = db.get_readings_by_window(60)

# Avoid - scans entire table
readings = db.get_latest_readings(limit=100000)
```

### 2. Batch Inserts

For bulk data import, consider batching:

```python
# Instead of many single inserts
for reading in readings:
    db.insert_sensor_reading(...)

# Use executemany (custom implementation)
```

### 3. Monitor Connection Pool

Check active connections:

```python
print(f"Active: {db.connection_pool._used}")
print(f"Available: {db.connection_pool._pool}")
```

## Migration Guide

### From In-Memory to Database

If you have existing data in the deque and want to save it:

```python
from db_manager import get_db_manager
from datetime import datetime

db = get_db_manager()

# Save all current in-memory data
for reading in weather_data:
    db.insert_sensor_reading(
        temperature=reading['temp'],
        humidity=reading['rh'],
        lux=reading['lux'],
        irradiance=reading.get('irradiance', reading['lux'] / 127.0),
        timestamp=datetime.fromisoformat(reading['time_iso'])
    )
```

## Security Best Practices

1. ✅ **Never commit `.env`** - Already in `.gitignore`
2. ✅ **Use SSL/TLS** - Enforced with `sslmode=require`
3. ✅ **Connection pooling** - Prevents connection exhaustion
4. ✅ **Prepared statements** - Protection against SQL injection
5. ⚠️ **Rotate passwords** - Change DB password every 90 days
6. ⚠️ **Restrict IP access** - Use Digital Ocean firewall rules

## Next Steps

1. ✅ Run `python test_database.py` to verify setup
2. ✅ Start application with `python readings.py`
3. ✅ Check `/api/status` to see database statistics
4. 📊 Monitor database usage in Digital Ocean dashboard
5. 🔄 Set up automated cleanup job (cron/scheduled task)
6. 📈 Consider adding TimescaleDB extension for time-series optimization

## Support

For issues:

1. Check logs in Flask output
2. Verify database connection with test script
3. Review Digital Ocean database metrics
4. Check `.env` credentials match Digital Ocean dashboard

---

**Your data is now safe and persistent! 🎉**

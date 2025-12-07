# Sensor Simulator Guide

## Overview

The `simulate_sensor.py` script generates realistic random sensor data and sends it to the TCP server (port 6000) as if it were coming from a real IoT sensor.

## Features

### 🌡️ Realistic Temperature Simulation

- **Range**: 20°C to 45°C (realistic for Qatar)
- **Variation**: ±2°C per reading (gradual changes)
- **Random walk**: Temperature drifts naturally over time

### 💧 Realistic Humidity Simulation

- **Range**: 20% to 80%
- **Variation**: ±5% per reading
- **Correlation**: Inverse relationship with temperature
  - When temp increases → humidity tends to decrease
  - Simulates natural weather patterns

### ☀️ Realistic Light (Lux) Simulation

- **Time-based**: Changes based on time of day (Qatar time)
- **Day/Night Cycle**:
  - **Night (20:00-06:00)**: 0-100 lux (dark)
  - **Dawn (06:00-07:00)**: 100-5,000 lux (sunrise)
  - **Early Morning (07:00-08:00)**: 5,000-20,000 lux
  - **Daytime (08:00-17:00)**: 30,000-100,000 lux (bright sun)
  - **Late Afternoon (17:00-18:00)**: 20,000-50,000 lux
  - **Dusk (18:00-19:00)**: 5,000-20,000 lux (sunset)
  - **Early Evening (19:00-20:00)**: 100-5,000 lux
- **Variation**: ±10% random variation for realism

### 🔄 Automatic Irradiance Calculation

- Server automatically calculates: `irradiance = lux / 127.0`
- Converts lux to W/m² (solar irradiance)

## Usage

### Step 1: Start the Flask Server

```powershell
# Terminal 1
python readings.py
```

Server starts on: http://localhost:5000

### Step 2: Run the Sensor Simulator

```powershell
# Terminal 2
python simulate_sensor.py
```

### Output Example

```
============================================================
🌡️  ZDEnergy Sensor Simulator Started
============================================================
📡 TCP Server: localhost:6000
🆔 Sensor ID: sim_sensor_001
⏱️  Send Interval: 2 seconds
🇶🇦 Timezone: Qatar (UTC+3)
============================================================

Press Ctrl+C to stop

✅ [1] Sent: 2025-10-16 14:30:00 | Temp: 25.34°C | RH: 48.23% | Lux: 85420
✅ [2] Sent: 2025-10-16 14:30:02 | Temp: 26.12°C | RH: 46.89% | Lux: 87650
✅ [3] Sent: 2025-10-16 14:30:04 | Temp: 25.89°C | RH: 47.45% | Lux: 89123
...
```

### Stop the Simulator

Press **Ctrl+C** to stop gracefully:

```
============================================================
🛑 Simulation stopped by user
📊 Statistics:
   Total readings: 150
   Successful: 150
   Failed: 0
   Success rate: 100.0%
============================================================
```

## Configuration

Edit `simulate_sensor.py` to customize:

```python
# Connection settings
TCP_HOST = "localhost"  # Change to server IP if remote
TCP_PORT = 6000

# Sensor identification
SENSOR_ID = "sim_sensor_001"  # Change to unique ID

# Timing
SEND_INTERVAL = 2  # seconds between readings (default: 2)

# Temperature settings
TEMP_MIN = 20.0  # Minimum temperature (°C)
TEMP_MAX = 45.0  # Maximum temperature (°C)
TEMP_VARIATION = 2.0  # Max change per reading

# Humidity settings
HUMIDITY_MIN = 20.0  # Minimum humidity (%)
HUMIDITY_MAX = 80.0  # Maximum humidity (%)
HUMIDITY_VARIATION = 5.0  # Max change per reading

# Light settings
LUX_MIN = 0  # Night minimum
LUX_MAX = 100000  # Bright sun maximum
```

## Data Format

### Sent to TCP Server

```json
{
  "id": "sim_sensor_001",
  "time": "2025-10-16 14:30:00",
  "temp": 25.34,
  "rh": 48.23,
  "lux": 85420.5
}
```

### Stored in Database

```sql
sensor_id: sim_sensor_001
timestamp: 2025-10-16 14:30:00+03 (Qatar time)
temperature: 25.34
humidity: 48.23
lux: 85420.50
irradiance: 672.60 (calculated: lux/127.0)
```

## Multiple Sensors

To simulate multiple sensors:

### Option 1: Multiple Terminals

```powershell
# Terminal 2 - Sensor 1
python simulate_sensor.py

# Terminal 3 - Sensor 2 (modify SENSOR_ID first)
python simulate_sensor.py

# Terminal 4 - Sensor 3 (modify SENSOR_ID first)
python simulate_sensor.py
```

### Option 2: Modify Script

Edit `simulate_sensor.py` and change:

```python
SENSOR_ID = "sim_sensor_002"  # Unique ID for each instance
```

### Option 3: Command Line Argument (Future Enhancement)

```powershell
python simulate_sensor.py --id sensor_002 --interval 5
```

## Troubleshooting

### Error: "Connection refused"

**Cause**: TCP server not running
**Solution**: Start Flask server first:

```powershell
python readings.py
```

### Error: "Address already in use"

**Cause**: Another process using port 6000
**Solution**: Stop the other process or change TCP_PORT in both files

### Error: "zoneinfo module not found"

**Cause**: Python version < 3.9
**Solution**: Install tzdata:

```powershell
pip install tzdata
```

### No data in dashboard

**Check**:

1. Server running? `python readings.py`
2. Simulator running? `python simulate_sensor.py`
3. Check server console for "Stored reading:" messages
4. Refresh dashboard: http://localhost:5000

## Testing Scenarios

### Test 1: Basic Connection

```powershell
# Start server
python readings.py

# Start simulator
python simulate_sensor.py

# Verify: Server console shows "Stored reading:" messages
# Verify: Dashboard shows live data
```

### Test 2: Historical Data

```powershell
# Run simulator for 5-10 minutes
python simulate_sensor.py

# Stop simulator (Ctrl+C)
# Open dashboard: http://localhost:5000
# Select date in date picker
# Click "Load Day" - should show all readings
```

### Test 3: Time Windows

```powershell
# Run simulator continuously
# Open dashboard
# Click different time window buttons (5min, 15min, 1hr, etc.)
# Charts should update with appropriate time ranges
```

### Test 4: Database Persistence

```powershell
# Run simulator for a few minutes
# Stop Flask server (Ctrl+C in server terminal)
# Restart Flask server: python readings.py
# Data should still be available in dashboard
# Historical data preserved in database
```

## Data Patterns

### Temperature Pattern

- Starts at 25°C
- Random walk within 20-45°C range
- Gradual changes (±2°C per reading)
- Simulates realistic thermal inertia

### Humidity Pattern

- Starts at 50%
- Random walk within 20-80% range
- Inverse correlation with temperature
- More humid when cooler, drier when hotter

### Lux Pattern

- Time-dependent (Qatar time)
- Follows realistic day/night cycle
- Very bright during midday (80,000-100,000 lux)
- Dark at night (0-100 lux)
- Gradual transitions at dawn/dusk

### Irradiance Pattern

- Automatically calculated from lux
- Formula: `irradiance = lux / 127.0`
- Typical range: 0-800 W/m²
- Peak around noon (bright sun)

## Performance

- **Memory Usage**: ~50 MB
- **CPU Usage**: <1%
- **Network**: Minimal (1 TCP packet per reading)
- **Readings per minute**: 30 (at 2-second interval)
- **Daily readings**: ~43,200 (at 2-second interval)

## Advanced Usage

### High-Frequency Data

For faster data generation:

```python
SEND_INTERVAL = 0.5  # 2 readings per second
```

### Slow Data Collection

For longer intervals:

```python
SEND_INTERVAL = 60  # 1 reading per minute
```

### Extreme Weather Simulation

```python
TEMP_MIN = 15.0  # Cold winter
TEMP_MAX = 50.0  # Extreme heat
TEMP_VARIATION = 5.0  # Rapid changes
```

### Night-Time Testing

Modify `generate_realistic_lux()` to force night:

```python
def generate_realistic_lux():
    return random.uniform(0, 100)  # Always dark
```

## Integration with Real Sensors

When you have real sensors:

1. **Keep the format**: Real sensors should send the same JSON format
2. **Use unique IDs**: Each sensor should have unique `id` field
3. **Include timestamp**: Use Qatar time or UTC (server converts)
4. **TCP connection**: Connect to port 6000
5. **Newline delimiter**: End each JSON message with `\n`

### Real Sensor Example

```python
import socket
import json
from datetime import datetime
from zoneinfo import ZoneInfo

# Read from actual sensor hardware
temp = read_temperature_sensor()
humidity = read_humidity_sensor()
lux = read_light_sensor()

# Create reading
reading = {
    "id": "real_sensor_001",
    "time": datetime.now(ZoneInfo("Asia/Qatar")).strftime("%Y-%m-%d %H:%M:%S"),
    "temp": temp,
    "rh": humidity,
    "lux": lux
}

# Send to server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 6000))
sock.sendall((json.dumps(reading) + "\n").encode('utf-8'))
sock.close()
```

## Summary

✅ **Generates realistic sensor data**  
✅ **Time-of-day aware light simulation**  
✅ **Correlated temperature/humidity**  
✅ **Qatar timezone aware**  
✅ **Automatic irradiance calculation**  
✅ **Easy to configure**  
✅ **Graceful error handling**  
✅ **Statistics on exit**

**Start simulating sensor data now:**

```powershell
python simulate_sensor.py
```

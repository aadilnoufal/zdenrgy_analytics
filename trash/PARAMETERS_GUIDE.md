# KPI System - Parameter Configuration Guide

## Overview

The KPI system is designed with **pluggable data sources**. All parameters are defined in `config.py`, data sources are handled in `data_sources.py`, and KPI calculations are in `kpi_calculator.py`.

## Architecture

```
┌─────────────────┐
│   readings.py   │  Flask API
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ kpi_calculator  │  Business Logic
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ data_sources    │  Data Adapters
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    config.py    │  Parameter Definitions
└─────────────────┘
```

## Parameter Types & Sources

### 1. **Sensor Data** (Already Available)

Source: In-memory sensor readings from TCP server

**Available Parameters:**

- `solar_irradiance` - Calculated from lux sensor (lux / 127.0)
- `temperature` - From temp sensor
- `humidity` - From humidity sensor
- `ambient_lux` - From light sensor

**No changes needed** - these work out of the box!

---

### 2. **Manual Input** (Configured in `config.py`)

Source: Static configuration values

**Configurable Parameters:**

- `panel_area` - Solar panel area (m²)
- `panel_efficiency` - Panel efficiency (%)
- `system_losses` - Total system losses (%)
- `battery_capacity` - Battery storage capacity (kWh)
- `electricity_tariff` - Cost per kWh ($)
- `feed_in_tariff` - Revenue per kWh sold ($)

**How to Update:**
Edit values in `config.py` → `MANUAL_CONFIG` dictionary:

```python
MANUAL_CONFIG: Dict[str, Any] = {
    "solar.panel_area": 150.0,  # ← Change this
    "solar.panel_efficiency": 22.0,  # ← Or this
    # ...
}
```

Or update at runtime via API:

```bash
# TODO: Add API endpoint for updating manual config
```

---

### 3. **External API** (Placeholder - Plug In When Available)

Source: REST APIs for energy meters, battery systems, weather services

**Parameters Waiting for API Integration:**

- `building_load` - Current building consumption (kW)
- `grid_power` - Power from/to grid (kW)
- `battery_soc` - Battery charge level (%)
- `grid_carbon_intensity` - CO₂ per kWh (kg)
- `forecast_irradiance` - Weather forecast (W/m²)
- `forecast_temperature` - Weather forecast (°C)

**How to Plug In an External API:**

1. **Configure the API endpoint** in `config.py`:

   ```python
   MANUAL_CONFIG = {
       "api.base_url": "https://your-api.com",
   }
   ```

2. **Update parameter source config** in `config.py`:

   ```python
   BUILDING_LOAD = Parameter(
       name="building_load",
       display_name="Building Energy Load",
       unit="kW",
       source=DataSourceType.EXTERNAL_API,
       source_config={
           "endpoint": "/api/v1/energy/consumption",  # ← Your endpoint
           "field": "current_load_kw"  # ← JSON field path
       },
       default_value=0.0
   )
   ```

3. **Done!** The system will automatically fetch from your API.

**API Response Format Expected:**

```json
{
  "current_load_kw": 45.2,
  "timestamp": "2025-10-15T10:00:00Z"
}
```

For nested fields, use dot notation:

```python
source_config={"field": "data.metrics.load"}
```

---

### 4. **Database** (Placeholder - Implement When Needed)

Source: SQL/NoSQL database

**How to Plug In a Database:**

1. **Install database driver**:

   ```bash
   pip install psycopg2  # PostgreSQL
   # or
   pip install pymongo   # MongoDB
   ```

2. **Implement database adapter** in `data_sources.py`:

   ```python
   class DatabaseDataSource(DataSourceAdapter):
       def __init__(self, connection_string: str):
           self.conn = psycopg2.connect(connection_string)

       def fetch(self, parameter: Parameter) -> Optional[float]:
           query = parameter.source_config.get("query")
           cursor = self.conn.cursor()
           cursor.execute(query)
           result = cursor.fetchone()
           return float(result[0]) if result else parameter.default_value
   ```

3. **Update parameter definition**:
   ```python
   BUILDING_LOAD = Parameter(
       name="building_load",
       source=DataSourceType.DATABASE,
       source_config={
           "query": "SELECT current_load FROM energy WHERE id = 1"
       }
   )
   ```

---

## Using the System

### In Python Code

```python
from data_sources import create_data_provider
from kpi_calculator import create_kpi_calculator

# Create data provider (pass sensor data reference)
provider = create_data_provider(weather_data)

# Get individual parameters
irradiance = provider.get("solar_irradiance")
temp = provider.get("temperature")
panel_area = provider.get("panel_area")

# Get multiple parameters at once
params = provider.get_multiple([
    "solar_irradiance",
    "temperature",
    "panel_area"
])

# Calculate KPIs
calculator = create_kpi_calculator(provider)
solar_gen = calculator.calculate_solar_generation()
print(f"Solar Generation: {solar_gen.value} {solar_gen.unit}")

# Get all KPIs
all_kpis = calculator.calculate_all()
for kpi in all_kpis:
    print(f"{kpi.display_name}: {kpi.value} {kpi.unit}")
```

### Via API

```bash
# Get all KPIs
curl http://localhost:5000/api/kpi

# Get specific KPI
curl http://localhost:5000/api/kpi/solar_generation

# Get all parameter values
curl http://localhost:5000/api/parameters
```

**Response Format:**

```json
{
  "timestamp": "2025-10-15T10:00:00",
  "kpis": {
    "solar_generation": {
      "value": 15.432,
      "unit": "kW",
      "display_name": "Solar Generation",
      "metadata": {
        "irradiance": 850.5,
        "panel_area": 100.0,
        "efficiency": 20.0,
        "losses": 15.0
      }
    }
  }
}
```

---

## Adding New Parameters

### Step 1: Define in `config.py`

```python
NEW_PARAMETER = Parameter(
    name="inverter_efficiency",
    display_name="Inverter Efficiency",
    unit="%",
    source=DataSourceType.EXTERNAL_API,  # or SENSOR, MANUAL_INPUT, etc.
    source_config={
        "endpoint": "/api/inverter/status",
        "field": "efficiency"
    },
    description="Current inverter conversion efficiency",
    default_value=95.0
)

# Add to registry
ALL_PARAMETERS["inverter_efficiency"] = NEW_PARAMETER
```

### Step 2: Use in Calculations

```python
# In kpi_calculator.py
def calculate_inverter_loss(self) -> KPIResult:
    efficiency = self.provider.get("inverter_efficiency")
    loss = 100 - efficiency

    return KPIResult(
        name="inverter_loss",
        display_name="Inverter Losses",
        value=round(loss, 2),
        unit="%",
        timestamp=datetime.utcnow().isoformat()
    )
```

### Step 3: Done!

The parameter is now available via:

- `provider.get("inverter_efficiency")`
- `/api/parameters` endpoint
- Automatic integration in KPI calculations

---

## Example Integration Scenarios

### Scenario 1: Connect to Smart Meter API

```python
# In config.py, update:
MANUAL_CONFIG["api.base_url"] = "https://smart-meter.company.com"

BUILDING_LOAD = Parameter(
    name="building_load",
    source=DataSourceType.EXTERNAL_API,
    source_config={
        "endpoint": "/v1/meters/123/current",
        "field": "power_kw"
    }
)
```

### Scenario 2: Add Battery Management System

```python
# In config.py
BATTERY_SOC = Parameter(
    name="battery_soc",
    source=DataSourceType.EXTERNAL_API,
    source_config={
        "endpoint": "/api/battery/status",
        "field": "state_of_charge"
    }
)

BATTERY_POWER = Parameter(
    name="battery_power",
    source=DataSourceType.EXTERNAL_API,
    source_config={
        "endpoint": "/api/battery/status",
        "field": "power_kw"
    }
)
```

### Scenario 3: Use PostgreSQL for Historical Data

```python
# In data_sources.py
class DatabaseDataSource(DataSourceAdapter):
    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)

    def fetch(self, parameter: Parameter) -> Optional[float]:
        query = parameter.source_config["query"]
        with self.conn.cursor() as cur:
            cur.execute(query)
            result = cur.fetchone()
            return float(result[0]) if result else None

# In config.py
GRID_CARBON_INTENSITY = Parameter(
    source=DataSourceType.DATABASE,
    source_config={
        "query": "SELECT intensity FROM carbon_data ORDER BY time DESC LIMIT 1"
    }
)
```

---

## Testing Without Real Data Sources

All parameters have **default values**, so the system works even without external APIs:

```python
# These will return default values if API is unavailable
provider.get("building_load")  # Returns 0.0 (default)
provider.get("battery_soc")     # Returns 50.0 (default)
```

To test with mock data, temporarily change defaults in `config.py`:

```python
BUILDING_LOAD = Parameter(
    # ...
    default_value=45.0  # ← Simulate 45 kW load
)
```

---

## API Endpoints Reference

| Endpoint          | Method | Description                          |
| ----------------- | ------ | ------------------------------------ |
| `/api/kpi`        | GET    | Get all calculated KPIs              |
| `/api/kpi/<name>` | GET    | Get specific KPI by name             |
| `/api/parameters` | GET    | Get all parameter values and configs |
| `/api/data`       | GET    | Get raw sensor data (existing)       |
| `/api/status`     | GET    | Get system status (existing)         |

---

## Summary

✅ **Sensor data** - Works now (temp, humidity, lux, irradiance)
✅ **Manual config** - Edit `config.py` → `MANUAL_CONFIG`
⏳ **External APIs** - Update `source_config` endpoint when available
⏳ **Database** - Implement adapter in `data_sources.py` when needed

**The system is designed so you can plug in new data sources without changing KPI calculation logic!**

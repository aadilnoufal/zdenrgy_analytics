# ✅ Refactoring Complete - Pluggable KPI System

## What We Built

Your application now has a **fully modular, pluggable parameter system** for KPI calculations. All data sources (sensors, APIs, databases, manual config) are abstracted and easy to swap in/out.

## New File Structure

```
zdenergy/
├── readings.py              # Flask app + TCP server (backend only)
├── config.py                # ⭐ Parameter definitions
├── data_sources.py          # ⭐ Data source adapters
├── kpi_calculator.py        # ⭐ KPI calculation logic
├── PARAMETERS_GUIDE.md      # ⭐ How to plug in data sources
│
├── templates/               # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   └── kpi.html
│
├── static/                  # Static assets
│   ├── css/styles.css
│   └── js/
│       ├── dashboard.js
│       └── kpi.js
│
└── requirements.txt
```

## Key Features

### 1. **All Parameters Are Variables** ✅

Every parameter is defined once in `config.py`:

```python
SOLAR_IRRADIANCE = Parameter(
    name="solar_irradiance",
    display_name="Solar Irradiance",
    unit="W/m²",
    source=DataSourceType.SENSOR,
    source_config={"field": "irradiance"},
    default_value=0.0
)
```

### 2. **Easy to Use in Code** ✅

```python
from data_sources import create_data_provider

provider = create_data_provider(weather_data)

# Get any parameter - just use its name!
irradiance = provider.get("solar_irradiance")
temp = provider.get("temperature")
panel_area = provider.get("panel_area")

# Get multiple at once
params = provider.get_multiple([
    "solar_irradiance",
    "temperature",
    "panel_area"
])
```

### 3. **Pluggable Data Sources** ✅

Four types of data sources:

| Type             | Status     | Usage                                   |
| ---------------- | ---------- | --------------------------------------- |
| **SENSOR**       | ✅ Working | Already reads from TCP sensor data      |
| **MANUAL_INPUT** | ✅ Working | Edit values in `config.py`              |
| **EXTERNAL_API** | ⏳ Ready   | Just update endpoint URL when available |
| **DATABASE**     | ⏳ Ready   | Implement adapter when needed           |

### 4. **KPI Calculations** ✅

All KPIs automatically use the data provider:

```python
from kpi_calculator import create_kpi_calculator

calculator = create_kpi_calculator(provider)

# Calculate any KPI
solar_gen = calculator.calculate_solar_generation()
savings = calculator.calculate_energy_cost_savings()

# Get all KPIs at once
all_kpis = calculator.calculate_all()
```

## Available Parameters

### Already Working (from sensors):

- ✅ `solar_irradiance` - Solar radiation (W/m²)
- ✅ `temperature` - Ambient temperature (°C)
- ✅ `humidity` - Relative humidity (%)
- ✅ `ambient_lux` - Light level (lux)

### Configurable (manual input):

- ✅ `panel_area` - Solar panel area (m²)
- ✅ `panel_efficiency` - Panel efficiency (%)
- ✅ `system_losses` - System losses (%)
- ✅ `battery_capacity` - Battery capacity (kWh)
- ✅ `electricity_tariff` - Electricity cost ($/kWh)
- ✅ `feed_in_tariff` - Feed-in revenue ($/kWh)

### Ready to plug in (external APIs):

- ⏳ `building_load` - Building consumption (kW)
- ⏳ `grid_power` - Grid power draw (kW)
- ⏳ `battery_soc` - Battery charge (%)
- ⏳ `grid_carbon_intensity` - CO₂ per kWh (kg)
- ⏳ `forecast_irradiance` - Weather forecast (W/m²)

## API Endpoints

### New Endpoints:

```bash
# Get all calculated KPIs
GET /api/kpi
→ Returns all KPIs with values, units, metadata

# Get specific KPI
GET /api/kpi/solar_generation
GET /api/kpi/daily_solar_energy
GET /api/kpi/battery_soc
→ Returns single KPI details

# Get all parameters and current values
GET /api/parameters
→ Shows all configured parameters, their sources, and current values
```

### Existing Endpoints:

```bash
GET /              # Dashboard page
GET /kpi           # KPI page
GET /api/data      # Raw sensor data
GET /api/status    # System status
```

## How to Plug In New Data Sources

### Example 1: Connect Smart Meter API

```python
# In config.py, update the API URL
MANUAL_CONFIG["api.base_url"] = "https://smart-meter.company.com"

# Update the parameter config
BUILDING_LOAD = Parameter(
    name="building_load",
    source=DataSourceType.EXTERNAL_API,
    source_config={
        "endpoint": "/v1/meters/current",  # ← Your endpoint
        "field": "power_kw"  # ← JSON field
    }
)
```

**That's it!** Now `provider.get("building_load")` will fetch from your API.

### Example 2: Add New Parameter

```python
# 1. Define in config.py
INVERTER_TEMP = Parameter(
    name="inverter_temp",
    display_name="Inverter Temperature",
    unit="°C",
    source=DataSourceType.EXTERNAL_API,
    source_config={
        "endpoint": "/api/inverter/status",
        "field": "temperature"
    },
    default_value=25.0
)

# 2. Add to registry
ALL_PARAMETERS["inverter_temp"] = INVERTER_TEMP

# 3. Use anywhere!
temp = provider.get("inverter_temp")
```

## Available KPIs

1. **Solar Generation** - Current solar power output (kW)
2. **Daily Solar Energy** - Estimated daily generation (kWh)
3. **Building Load** - Current consumption (kW)
4. **Self-Consumption Ratio** - % of solar energy self-consumed
5. **Battery Status** - Battery charge level (%)
6. **Energy Cost Savings** - Estimated daily savings ($)
7. **Grid Export Revenue** - Revenue from excess solar ($/h)
8. **Carbon Offset** - CO₂ emissions avoided (kg)
9. **Temperature** - Current temperature (°C)
10. **Humidity** - Current humidity (%)

## Testing the System

### Start the server:

```bash
python readings.py
```

### Test APIs:

```bash
# View all KPIs
curl http://localhost:5000/api/kpi

# View specific KPI
curl http://localhost:5000/api/kpi/solar_generation

# View all parameters
curl http://localhost:5000/api/parameters
```

### In a browser:

- Dashboard: http://localhost:5000
- KPI Page: http://localhost:5000/kpi

## Configuration

### To update manual parameters:

Edit `config.py` → `MANUAL_CONFIG`:

```python
MANUAL_CONFIG = {
    "solar.panel_area": 150.0,        # ← Change panel area
    "solar.panel_efficiency": 22.0,   # ← Change efficiency
    "financial.electricity_tariff": 0.15,  # ← Update tariff
    # ...
}
```

Restart the server for changes to take effect.

## Next Steps

### To integrate external APIs:

1. **Get your API credentials/URL**
2. **Update `config.py`:**
   ```python
   MANUAL_CONFIG["api.base_url"] = "https://your-api.com"
   ```
3. **Update parameter endpoint:**
   ```python
   BUILDING_LOAD = Parameter(
       source_config={
           "endpoint": "/your/endpoint",
           "field": "your_field"
       }
   )
   ```
4. **Done!** The system auto-fetches data.

### To add database storage:

1. **Install database driver:**
   ```bash
   pip install psycopg2  # or pymongo, etc.
   ```
2. **Implement adapter in `data_sources.py`**
3. **Update parameter to use DATABASE source**

## Summary

✅ **All parameters are centralized variables**
✅ **Easy to use anywhere in code** - just `provider.get("parameter_name")`
✅ **Pluggable data sources** - swap sensors/APIs/databases without changing logic
✅ **Working KPI calculations** - use real data when available, defaults otherwise
✅ **Clean separation** - config → data sources → calculations → API

**Read `PARAMETERS_GUIDE.md` for detailed examples and integration scenarios!**

# Quick Reference - Pluggable Parameter System

## 🚀 Getting Started (3 Steps)

### 1. Create Provider

```python
from data_sources import create_data_provider

provider = create_data_provider(weather_data)
```

### 2. Get Parameters

```python
value = provider.get("parameter_name")
```

### 3. Calculate KPIs

```python
from kpi_calculator import create_kpi_calculator

calculator = create_kpi_calculator(provider)
result = calculator.calculate_solar_generation()
```

---

## 📋 Available Parameters

| Parameter               | Source | Unit   | Description       |
| ----------------------- | ------ | ------ | ----------------- |
| `solar_irradiance`      | SENSOR | W/m²   | Solar radiation   |
| `temperature`           | SENSOR | °C     | Ambient temp      |
| `humidity`              | SENSOR | %      | Relative humidity |
| `ambient_lux`           | SENSOR | lux    | Light level       |
| `panel_area`            | MANUAL | m²     | Panel area        |
| `panel_efficiency`      | MANUAL | %      | Panel efficiency  |
| `system_losses`         | MANUAL | %      | System losses     |
| `battery_capacity`      | MANUAL | kWh    | Battery size      |
| `electricity_tariff`    | MANUAL | $/kWh  | Grid cost         |
| `feed_in_tariff`        | MANUAL | $/kWh  | Feed-in revenue   |
| `building_load`         | API    | kW     | Consumption       |
| `grid_power`            | API    | kW     | Grid power        |
| `battery_soc`           | API    | %      | Battery charge    |
| `grid_carbon_intensity` | API    | kg/kWh | CO₂ intensity     |

---

## 🔧 Common Operations

### Get Single Parameter

```python
temp = provider.get("temperature")
```

### Get Multiple Parameters

```python
params = provider.get_multiple([
    "solar_irradiance",
    "temperature",
    "panel_area"
])
```

### Get All Available

```python
all_params = provider.get_all_available()
```

### Get Historical Data

```python
history = provider.get_historical("temperature", minutes=60)
# Returns: [{"time": "...", "value": 25.5}, ...]
```

---

## 📊 KPI Methods

```python
calculator = create_kpi_calculator(provider)

# Individual KPIs
solar_gen = calculator.calculate_solar_generation()
energy = calculator.calculate_daily_solar_energy()
load = calculator.calculate_building_load()
ratio = calculator.calculate_self_consumption_ratio()
battery = calculator.calculate_battery_status()
savings = calculator.calculate_energy_cost_savings()
revenue = calculator.calculate_grid_export_revenue()
carbon = calculator.calculate_carbon_offset()
temp = calculator.calculate_temperature_status()
humidity = calculator.calculate_humidity_status()

# All at once
all_kpis = calculator.calculate_all()

# Summary
summary = calculator.calculate_summary()
```

---

## 🌐 API Endpoints

```bash
# All KPIs
curl http://localhost:5000/api/kpi

# Specific KPI
curl http://localhost:5000/api/kpi/solar_generation

# All parameters
curl http://localhost:5000/api/parameters

# Raw sensor data
curl http://localhost:5000/api/data?limit=100&minutes=60
```

---

## ⚙️ Configuration

### Update Manual Config (Runtime)

```python
from config import update_manual_config

update_manual_config("solar.panel_area", 150.0)
update_manual_config("financial.electricity_tariff", 0.15)
```

### Update Manual Config (File)

Edit `config.py` → `MANUAL_CONFIG` dictionary:

```python
MANUAL_CONFIG = {
    "solar.panel_area": 150.0,
    "solar.panel_efficiency": 22.0,
    # ...
}
```

---

## 🔌 Plug In New Data Source

### For External API:

```python
# In config.py
MANUAL_CONFIG["api.base_url"] = "https://your-api.com"

NEW_PARAM = Parameter(
    name="your_parameter",
    source=DataSourceType.EXTERNAL_API,
    source_config={
        "endpoint": "/api/endpoint",
        "field": "json_field"
    }
)

ALL_PARAMETERS["your_parameter"] = NEW_PARAM
```

### For Database:

```python
# 1. Implement in data_sources.py
class DatabaseDataSource(DataSourceAdapter):
    def fetch(self, parameter):
        # Your DB query logic
        return value

# 2. Update parameter in config.py
PARAM = Parameter(
    source=DataSourceType.DATABASE,
    source_config={"query": "SELECT ..."}
)
```

---

## ➕ Add New Parameter

```python
# In config.py

# 1. Define parameter
NEW_PARAM = Parameter(
    name="inverter_temp",
    display_name="Inverter Temperature",
    unit="°C",
    source=DataSourceType.EXTERNAL_API,
    source_config={
        "endpoint": "/api/inverter",
        "field": "temp"
    },
    default_value=25.0
)

# 2. Register
ALL_PARAMETERS["inverter_temp"] = NEW_PARAM

# 3. Use anywhere!
temp = provider.get("inverter_temp")
```

---

## 📈 Add New KPI

```python
# In kpi_calculator.py

def calculate_new_kpi(self) -> KPIResult:
    # Get parameters
    param1 = self.provider.get("param1")
    param2 = self.provider.get("param2")

    # Calculate
    result_value = param1 * param2

    # Return
    return KPIResult(
        name="new_kpi",
        display_name="My New KPI",
        value=result_value,
        unit="unit",
        timestamp=datetime.utcnow().isoformat()
    )
```

---

## 🛠️ Testing

### Run Examples

```bash
python examples.py
```

### Test API

```bash
# Start server
python readings.py

# Test endpoints
curl http://localhost:5000/api/kpi
curl http://localhost:5000/api/parameters
```

---

## 📁 Key Files

| File                | Purpose               |
| ------------------- | --------------------- |
| `config.py`         | Parameter definitions |
| `data_sources.py`   | Data source adapters  |
| `kpi_calculator.py` | KPI calculation logic |
| `readings.py`       | Flask app & API       |
| `examples.py`       | Usage examples        |

---

## 🎯 Common Patterns

### Pattern 1: Custom Calculation

```python
provider = create_data_provider(weather_data)
irradiance = provider.get("solar_irradiance")
area = provider.get("panel_area")
power = (irradiance * area) / 1000  # kW
```

### Pattern 2: Conditional Logic

```python
temp = provider.get("temperature")
if temp > 30:
    efficiency_factor = 0.95
else:
    efficiency_factor = 1.0
```

### Pattern 3: Time-Series Analysis

```python
history = provider.get_historical("temperature", minutes=60)
avg_temp = sum(h["value"] for h in history) / len(history)
```

---

## ⚠️ Error Handling

### Parameters return defaults if unavailable:

```python
# Will return 0.0 if API is down
load = provider.get("building_load")
```

### Check metadata for data source status:

```python
params = provider.get_multiple(["temp", "building_load"])
# building_load may be default if API unavailable
```

---

## 📚 Documentation Files

- `SYSTEM_OVERVIEW.md` - High-level overview
- `PARAMETERS_GUIDE.md` - Detailed parameter guide
- `ARCHITECTURE.md` - System architecture diagrams
- `REFACTORING.md` - Refactoring history
- `QUICK_REFERENCE.md` - This file

---

## 💡 Pro Tips

1. **Always use `provider.get()`** - Don't access data sources directly
2. **Define once, use everywhere** - Add to `config.py`, done
3. **Defaults are your friend** - System works without external APIs
4. **Test with examples.py** - See how everything works
5. **Read metadata** - KPI results include calculation details

---

## 🎓 Learning Path

1. ✅ Read `SYSTEM_OVERVIEW.md`
2. ✅ Run `python examples.py`
3. ✅ Try API endpoints with curl
4. ✅ Read `PARAMETERS_GUIDE.md`
5. ✅ Add your own parameter
6. ✅ Create custom KPI
7. ✅ Integrate external API

---

**Need help? Check the detailed guides or run examples.py!**

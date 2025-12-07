# System Architecture - Pluggable Parameters

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL WORLD                              │
│                                                                       │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐    │
│  │  TCP      │  │ External  │  │ Database  │  │ Manual       │    │
│  │  Sensors  │  │ REST APIs │  │           │  │ Config File  │    │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘    │
│        │              │              │                │             │
└────────┼──────────────┼──────────────┼────────────────┼─────────────┘
         │              │              │                │
         ▼              ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCE LAYER                             │
│                        (data_sources.py)                             │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐│
│  │SensorData    │  │ExternalAPI   │  │Database      │  │ManualIn │││
│  │Source        │  │DataSource    │  │DataSource    │  │putSourc │││
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘│
│         └──────────────────┴──────────────────┴──────────────┘      │
│                                │                                     │
│                        ┌───────▼────────┐                            │
│                        │ DataProvider   │                            │
│                        │                │                            │
│                        │  .get("name")  │  ← UNIFIED INTERFACE      │
│                        └───────┬────────┘                            │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
                         ┌───────▼───────┐
                         │  PARAMETER    │
                         │  REGISTRY     │
                         │ (config.py)   │
                         └───────┬───────┘
                                 │
┌────────────────────────────────┼─────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                              │
│                    (kpi_calculator.py)                               │
│                                │                                     │
│                        ┌───────▼────────┐                            │
│                        │ KPICalculator  │                            │
│                        │                │                            │
│    ┌───────────────────┤ - solar_gen() │────────────────┐           │
│    │                   │ - savings()   │                │           │
│    │                   │ - carbon()    │                │           │
│    │                   │ - battery()   │                │           │
│    │                   └────────────────┘                │           │
│    ▼                                                     ▼           │
│  ┌────────────────┐                             ┌────────────────┐  │
│  │ KPIResult      │                             │ KPIResult      │  │
│  │ {name, value,  │                             │ {name, value,  │  │
│  │  unit, meta}   │                             │  unit, meta}   │  │
│  └────────┬───────┘                             └────────┬───────┘  │
└───────────┼──────────────────────────────────────────────┼──────────┘
            │                                              │
            └──────────────────┬───────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────────┐
│                        WEB API LAYER                                  │
│                        (readings.py)                                  │
│                               │                                       │
│   ┌────────────┬──────────────┴─────────────┬──────────────────┐    │
│   │            │                             │                  │    │
│   ▼            ▼                             ▼                  ▼    │
│ GET /     GET /api/kpi                 GET /api/kpi/        GET /api/│
│           {"kpis": {...}}              solar_generation     parameters│
│ (HTML)    (JSON)                       (JSON)               (JSON)   │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

## Parameter Flow Example

### Scenario: Calculate Solar Generation

```
1. User requests: GET /api/kpi/solar_generation

2. Flask calls: calculator.calculate_solar_generation()

3. Calculator requests:
   - provider.get("solar_irradiance")
   - provider.get("panel_area")
   - provider.get("panel_efficiency")
   - provider.get("system_losses")

4. DataProvider routes each parameter to appropriate source:

   solar_irradiance → SensorDataSource → weather_data deque → 98.4 W/m²
   panel_area → ManualInputDataSource → config.py → 100.0 m²
   panel_efficiency → ManualInputDataSource → config.py → 20.0 %
   system_losses → ManualInputDataSource → config.py → 15.0 %

5. Calculator computes:
   P = (98.4 × 100 × 0.20 × 0.85) / 1000 = 1.673 kW

6. Returns KPIResult:
   {
     "name": "solar_generation",
     "display_name": "Solar Generation",
     "value": 1.673,
     "unit": "kW",
     "metadata": {
       "irradiance": 98.4,
       "panel_area": 100.0,
       "efficiency": 20.0,
       "losses": 15.0
     }
   }

7. Flask serializes to JSON and returns to user
```

## Adding a New Data Source

### Example: Connect to Smart Meter API

```
Step 1: Configure endpoint in config.py
┌─────────────────────────────────────────┐
│ MANUAL_CONFIG = {                       │
│   "api.base_url": "https://meter.com"  │
│ }                                       │
└─────────────────────────────────────────┘
                    │
                    ▼
Step 2: Update parameter definition
┌─────────────────────────────────────────┐
│ BUILDING_LOAD = Parameter(              │
│   source=DataSourceType.EXTERNAL_API,   │
│   source_config={                       │
│     "endpoint": "/api/load",            │
│     "field": "current_kw"               │
│   }                                     │
│ )                                       │
└─────────────────────────────────────────┘
                    │
                    ▼
Step 3: Use anywhere!
┌─────────────────────────────────────────┐
│ load = provider.get("building_load")    │
│ # Automatically fetches from API        │
└─────────────────────────────────────────┘
```

## Key Design Principles

### 1. **Single Source of Truth**

- All parameters defined once in `config.py`
- No duplication across codebase

### 2. **Loose Coupling**

- KPI calculations don't know about data sources
- Data sources don't know about KPIs
- Connected via `DataProvider` interface

### 3. **Easy Extension**

- Add new parameter: update `config.py`
- Add new data source: implement `DataSourceAdapter`
- Add new KPI: add method to `KPICalculator`

### 4. **Fail-Safe**

- Every parameter has a default value
- System works even with missing data sources
- Graceful degradation

### 5. **Type Safety**

- Parameters typed with units and descriptions
- Data validated at source level
- Type hints throughout

## Code Reusability

The same parameter can be used in:

```python
# API endpoints
@app.route("/api/kpi/solar")
def solar_kpi():
    irradiance = provider.get("solar_irradiance")
    # ...

# KPI calculations
def calculate_solar_generation(self):
    irradiance = self.provider.get("solar_irradiance")
    # ...

# Custom scripts
irradiance = provider.get("solar_irradiance")
# ...

# Frontend via API
fetch('/api/parameters')
  .then(r => r.json())
  .then(data => {
    const irradiance = data.parameters.solar_irradiance.value
  })
```

## Summary

✅ **One parameter definition** → Used everywhere
✅ **Multiple data sources** → Unified interface
✅ **Easy to plug in** → Update config, done
✅ **Type-safe** → Catch errors early
✅ **Production-ready** → Handles failures gracefully

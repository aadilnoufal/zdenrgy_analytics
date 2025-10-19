# KPI Dashboard Navigation Guide

## 📊 Page Structure

```
Main Dashboard (/)
    │
    ├─→ KPI Main Page (/kpi)
    │       │
    │       ├─→ 🔋 Battery KPIs (/kpi/battery)
    │       │   └─ SOC, capacity, power flow, status
    │       │
    │       ├─→ ⚡ Inverter KPIs (/kpi/inverter)
    │       │   └─ DC/AC power, efficiency, conversion
    │       │
    │       ├─→ 🔌 DC Charger KPIs (/kpi/charger)
    │       │   └─ Charging power, sessions, efficiency
    │       │
    │       └─→ ☀️ Solar Array KPIs (/kpi/solar)
    │           └─ Generation, irradiance, savings, carbon
    │
    └─→ Live Sensor Dashboard (/)
        └─ Temperature, humidity, lux, irradiance charts
```

## 🌐 Available URLs

| Page                 | URL             | Description                         |
| -------------------- | --------------- | ----------------------------------- |
| **Main Dashboard**   | `/`             | Real-time sensor data with 4 charts |
| **KPI Hub**          | `/kpi`          | Central hub with 4 category cards   |
| **Battery KPIs**     | `/kpi/battery`  | Battery monitoring and metrics      |
| **Inverter KPIs**    | `/kpi/inverter` | Power conversion performance        |
| **DC Charger KPIs**  | `/kpi/charger`  | EV charging operations              |
| **Solar Array KPIs** | `/kpi/solar`    | Solar production and analytics      |

## 📱 What Each Page Shows

### 1. Main Dashboard (`/`)

**Features:**

- 4 live charts (temp, humidity, lux, irradiance)
- Real-time data updates (5s refresh)
- Time window selector (15m to 24h)
- Data table (last 50 readings)
- Latest values display

**Use For:**

- Monitoring environmental conditions
- Viewing sensor trends
- Checking current measurements

---

### 2. KPI Hub (`/kpi`)

**Features:**

- 4 large category cards
- Hover animations
- Quick navigation
- Visual icons

**Categories:**

- 🔋 Battery (cyan accent)
- ⚡ Inverter (yellow accent)
- 🔌 DC Charger (purple accent)
- ☀️ Solar Array (red accent)

---

### 3. Battery KPIs (`/kpi/battery`)

**Metrics Displayed:**

- State of Charge (%)
- Available Energy (kWh)
- Total Capacity (kWh)
- Battery Status (Online/Offline)
- Historical SOC chart
- Detailed metrics table

**Data Source:**

- `battery_soc` parameter
- External battery API (when configured)
- Falls back to defaults

**Use Cases:**

- Monitor charge level
- Track energy reserves
- Analyze charge patterns
- System health checks

---

### 4. Inverter KPIs (`/kpi/inverter`)

**Metrics Displayed:**

- DC Input Power (kW)
- AC Output Power (kW)
- Conversion Efficiency (%)
- Inverter Status (Active/Standby)
- Historical efficiency chart
- Voltage, temperature metrics

**Data Source:**

- Calculated from solar generation
- Assumes 95% efficiency (default)
- External inverter API (when configured)

**Use Cases:**

- Monitor power conversion
- Track efficiency trends
- Detect inverter issues
- Optimize performance

---

### 5. DC Charger KPIs (`/kpi/charger`)

**Metrics Displayed:**

- Current Charging Power (kW)
- Active Charging Sessions
- Charger Efficiency (%)
- Charger Status (Ready/Charging)
- Daily Energy Delivered (kWh)
- Historical power chart
- Connector status

**Data Source:**

- External charger API (ready to configure)
- Placeholder data until connected

**Use Cases:**

- Monitor EV charging
- Track energy consumption
- Analyze usage patterns
- Customer billing (future)

---

### 6. Solar Array KPIs (`/kpi/solar`)

**Metrics Displayed:**

- Current Generation (kW)
- Daily Energy (kWh)
- Performance Ratio (%)
- Cost Savings ($)
- Irradiance Chart (historical)
- Generation Chart (historical)
- System Configuration
- Carbon Offset (kg CO₂)
- Trees Equivalent

**Data Source:**

- Sensor data (lux → irradiance)
- Manual config (panel area, efficiency)
- Real-time calculations

**Use Cases:**

- Monitor solar production
- Calculate ROI & savings
- Track environmental impact
- Compare actual vs theoretical

---

## 🔄 Auto-Refresh

All KPI pages automatically refresh every **5 seconds**:

✅ Updates metrics in real-time  
✅ Refreshes charts with new data  
✅ No page reload needed  
✅ Minimal bandwidth usage

---

## 🎯 Navigation Tips

### Quick Access URLs

Open directly in browser:

```
http://localhost:5000/              ← Main Dashboard
http://localhost:5000/kpi           ← KPI Hub
http://localhost:5000/kpi/battery   ← Battery KPIs
http://localhost:5000/kpi/inverter  ← Inverter KPIs
http://localhost:5000/kpi/charger   ← Charger KPIs
http://localhost:5000/kpi/solar     ← Solar KPIs
```

### Navigation Flow

**Typical User Flow:**

1. Visit main dashboard to check sensor data
2. Click "View KPIs" button
3. Select specific KPI category (Battery, Inverter, etc.)
4. View detailed metrics and charts
5. Click "← Back to KPIs" to return to hub
6. Click "← Back to Dashboard" to return to main

**Power User Flow:**

1. Bookmark specific KPI pages
2. Open multiple tabs for different categories
3. Monitor all metrics simultaneously

---

## 📊 API Endpoints

### Get All KPIs

```bash
GET /api/kpi
```

Returns: All calculated KPIs with values, units, and metadata

### Get Specific KPI

```bash
GET /api/kpi/solar_generation
GET /api/kpi/battery_soc
GET /api/kpi/daily_cost_savings
```

Returns: Single KPI details

### Get All Parameters

```bash
GET /api/parameters
```

Returns: All configured parameters and current values

### Get Sensor Data

```bash
GET /api/data?limit=100&minutes=60
```

Returns: Historical sensor readings

---

## 🎨 Visual Design

### Color Coding

| Category | Primary Color    | Accent     |
| -------- | ---------------- | ---------- |
| Battery  | Cyan (#4ecdc4)   | Blue-green |
| Inverter | Yellow (#ffd166) | Gold       |
| Charger  | Purple (#a78bfa) | Lavender   |
| Solar    | Red (#ff7369)    | Coral      |

### Status Badges

| Status  | Color | Meaning               |
| ------- | ----- | --------------------- |
| Online  | Green | Active & transmitting |
| Active  | Green | Currently operating   |
| Ready   | Gray  | Available, not in use |
| Standby | Gray  | Idle, waiting         |
| Offline | Red   | No data received      |
| Unknown | Gray  | Source unavailable    |

---

## 🔧 Configuration

### To Add Data for Placeholders:

**Battery:** Configure `battery_soc` in `config.py`

```python
BATTERY_SOC = Parameter(
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/battery", "field": "soc"}
)
```

**Inverter:** Configure inverter API endpoint

```python
INVERTER_POWER = Parameter(
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/inverter", "field": "power"}
)
```

**Charger:** Configure charger API endpoint

```python
CHARGER_POWER = Parameter(
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/charger", "field": "power"}
)
```

See `PARAMETERS_GUIDE.md` for detailed integration instructions.

---

## 📱 Responsive Design

All pages work on:

✅ Desktop (1920x1080+)  
✅ Laptop (1366x768+)  
✅ Tablet (768x1024)  
✅ Mobile (320x568+)

Layout adapts automatically:

- Desktop: Multi-column grid
- Tablet: 2-column layout
- Mobile: Single column, stacked

---

## 🚀 Quick Start

1. **Start server:**

   ```bash
   python readings.py
   ```

2. **Open browser:**

   ```
   http://localhost:5000
   ```

3. **Navigate:**

   - Click "View KPIs" button
   - Select a category
   - Explore metrics

4. **Test APIs:**
   ```bash
   curl http://localhost:5000/api/kpi
   ```

---

## 📚 Related Documentation

- `SYSTEM_OVERVIEW.md` - System architecture
- `PARAMETERS_GUIDE.md` - Parameter configuration
- `QUICK_REFERENCE.md` - Command cheat sheet
- `ARCHITECTURE.md` - Technical diagrams
- `README.md` - Project overview

---

**All pages are live and ready to use!** 🎉

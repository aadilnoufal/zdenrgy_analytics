# ZDEnergy Analytics - Project Documentation

## 1. Project Overview

ZDEnergy Analytics is an IoT dashboard application designed for monitoring solar energy systems. It receives real-time sensor data via TCP, stores it in a PostgreSQL database, and visualizes it through a web interface. The system calculates Key Performance Indicators (KPIs) such as solar generation, energy savings, and carbon reduction.

## 2. System Architecture

### 2.1 Core Components

- **Backend**: Python Flask application (`readings.py`) serving the web UI and API.
- **TCP Server**: Runs on a separate thread (port 6000) to ingest JSON sensor data.
- **Database**: PostgreSQL (Digital Ocean Managed) for persistent storage of sensor readings and KPI snapshots.
- **In-Memory Buffer**: A `deque` stores the last 5000 readings for fast real-time dashboard updates.
- **Frontend**: HTML/CSS/JS using Chart.js for visualization.

### 2.2 KPI System (`kpi_calculator.py`, `data_sources.py`, `config.py`)

The KPI system is modular and pluggable:

- **`config.py`**: Defines all parameters (e.g., `SOLAR_IRRADIANCE`, `PANEL_AREA`) and their sources.
- **`data_sources.py`**: Adapters to fetch data from sensors, manual config, or external APIs.
- **`kpi_calculator.py`**: Business logic to compute KPIs based on fetched data.

### 2.3 File Structure

```
zdenergy/
├── readings.py              # Main Flask app & TCP server
├── db_manager.py            # Database connection & query management
├── kpi_calculator.py        # KPI calculation logic
├── data_sources.py          # Data fetching adapters
├── config.py                # Configuration & Parameter definitions
├── cleaning_tracker.py      # Solar panel cleaning logic
├── simulate_sensor.py       # Script to generate fake sensor data
├── migrate_add_sensor_id.py # Database migration utility
├── requirements.txt         # Python dependencies
├── static/                  # CSS & JS files
└── templates/               # HTML templates
```

## 3. Features

### 3.1 Real-time Dashboard

- Displays live charts for Temperature, Humidity, Lux, and Solar Irradiance.
- Updates every 5 seconds via polling.
- Shows latest values and a data table.

### 3.2 KPI Monitoring

- **Solar Generation**: Calculated based on irradiance, panel area, and efficiency.
- **Energy Savings**: Estimated cost savings based on generation.
- **Carbon Reduction**: CO2 offset calculation.
- **Battery/Inverter/Charger**: Placeholders for future hardware integration.

### 3.3 Historical Data & Export

- **Date Picker**: View sensor data for any specific past date.
- **CSV Export**: Download sensor data for the last 24 hours or a specific date.

### 3.4 Solar Cleaning Tracker

- Monitors performance degradation (Actual vs. Theoretical Output).
- Recommends cleaning when performance drops by >10%.

## 4. Setup & Installation

### 4.1 Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure Environment**:
   Create a `.env` file (optional for local, defaults to local DB or memory).
3. **Run Application**:
   ```bash
   python readings.py
   ```
   - Web UI: `http://localhost:5000`
   - TCP Server: `localhost:6000`

### 4.2 Sensor Simulator

To test without real hardware, run the simulator in a separate terminal:

```bash
python simulate_sensor.py
```

## 5. Deployment (Digital Ocean)

### 5.1 Server Setup

- The application runs on an Ubuntu Droplet.
- **Service**: Managed via `systemd` (`zdenergy.service`).
- **Database**: Connects to a Managed PostgreSQL instance.

### 5.2 Deployment Workflow

1. **Push changes** to GitHub.
2. **SSH into Droplet**:
   ```bash
   ssh root@<DROPLET_IP>
   ```
3. **Run Deploy Script**:
   ```bash
   cd ~/zdenrgy_analytics
   ./deploy.sh
   ```
   Or manually:
   ```bash
   git pull
   sudo systemctl restart zdenergy
   ```

### 5.3 Environment Variables (`.env`)

The server requires a `.env` file with:

- `FLASK_ENV=production`
- `SECRET_KEY=...`
- Database credentials (host, user, password, port, dbname).

## 6. Configuration

### 6.1 Timezone

- The system is configured for **Qatar Time (UTC+3)**.
- `db_manager.py` and `readings.py` handle timezone conversion.
- Database stores `TIMESTAMPTZ`.

### 6.2 Parameters

- Edit `config.py` to change static values like `PANEL_AREA`, `PANEL_EFFICIENCY`, or `ENERGY_COST`.

## 7. Troubleshooting

- **Database Connection**: Check `.env` credentials and ensure the Managed DB is reachable.
- **Timezone Issues**: Ensure `Asia/Qatar` is used. Timestamps in DB might look different (UTC) but are converted on retrieval.
- **Missing Dependencies**: Run `pip install -r requirements.txt`.

# ZD Energy - Sensor Dashboard

Live sensor dashboard that receives data over TCP and displays real-time charts via web interface.

## Features

- TCP server receives JSON sensor readings (temp, humidity, lux)
- Stores last 5,000 readings in memory
- Flask web UI with live charts using Chart.js
- Polling-based updates (every 5 seconds)

## 🚀 Quick Start for Digital Ocean

**See [DEPLOYMENT.md](DEPLOYMENT.md) for complete Digital Ocean deployment guide!**

## Setup

### Development (Local Testing)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python3 readings.py
```

Access at: http://localhost:5000

### Production Deployment

For production, use a WSGI server like **Gunicorn**:

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn (4 worker processes)
gunicorn -w 4 -b 0.0.0.0:5000 readings:app
```

Or use **Waitress** (cross-platform, works on Windows):

```bash
pip install waitress
waitress-serve --port=5000 readings:app
```

## Requirements

- Python 3.7+
- Flask 3.0+
- See `requirements.txt` for full list

## Ports

- HTTP Server: 5000
- TCP Server: 6000 (for sensor data)

## License

MIT

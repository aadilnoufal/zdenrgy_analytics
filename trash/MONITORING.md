# TCP Server Monitoring Guide

## Overview

The TCP server now includes robust error handling, auto-restart capabilities, and health monitoring endpoints to prevent silent failures.

## Key Enhancements

### 1. Heartbeat Tracking

- Global `_tcp_last_activity` timestamp tracks TCP server activity
- Updated on:
  - Server start
  - Connection accept
  - Data receive operations
- Enables detection of stale/dead connections

### 2. Health Check Endpoint

**URL:** `http://146.190.10.188:5000/api/health`

**Response Format:**

```json
{
  "status": "ok", // ok, warning, or error
  "tcp_server": {
    "started": true,
    "thread_alive": true,
    "last_activity": "2025-01-21T12:34:56",
    "seconds_since_activity": 5
  },
  "database": {
    "connected": true
  },
  "memory_readings_count": 1000,
  "timestamp": "2025-01-21T12:35:01"
}
```

**Status Codes:**

- `200`: System healthy
- `503`: Warning or error detected

**Alert Conditions:**

- **Warning**: No TCP activity for 10+ minutes
- **Error**: TCP server thread is dead

### 3. Log Emoji Indicators

Enhanced logging with visual indicators for easy monitoring:

- 🚀 Starting TCP Server
- ✅ TCP Server listening
- 🔌 Gateway connected
- 📴 Gateway disconnected
- ⚠️ Socket timeout
- ❌ Error (recoverable)
- 💥 Fatal error
- 🔄 Restarting server

## Deployment Steps

### On Your Local Machine:

```bash
# Changes already pushed to GitHub
git pull origin main  # (if needed on server)
```

### On Server (146.190.10.188):

```bash
# 1. Pull latest code
cd ~/zdenrgy_analytics
./deploy.sh

# 2. Restart service
sudo systemctl restart zdenergy

# 3. Monitor logs (watch for emoji indicators)
sudo journalctl -u zdenergy -f

# Expected output:
# 🚀 Starting TCP Server on port 6000...
# ✅ TCP Server listening on port 6000
# 🔌 Gateway connected from ('x.x.x.x', port)
```

### Verify TCP Server is Running:

```bash
# Check if port 6000 is listening
sudo netstat -tlnp | grep 6000

# Should show:
# tcp  0  0.0.0.0:6000  0.0.0.0:*  LISTEN  <pid>/gunicorn
```

## Monitoring Strategies

### 1. Real-time Log Monitoring

```bash
# Watch logs for issues
sudo journalctl -u zdenergy -f | grep -E "🚀|✅|💥|❌|⚠️"
```

### 2. Health Check Polling

```bash
# Manual check
curl http://146.190.10.188:5000/api/health | jq

# Continuous monitoring (every 60 seconds)
watch -n 60 'curl -s http://146.190.10.188:5000/api/health | jq'
```

### 3. Automated Alerts (Optional - Future Enhancement)

Consider setting up:

- UptimeRobot: Monitor `/api/health` endpoint
- Healthchecks.io: Ping service on successful data receive
- DigitalOcean monitoring alerts

## Troubleshooting

### If Port 6000 Not Listening:

```bash
# 1. Check service status
sudo systemctl status zdenergy

# 2. Check recent logs
sudo journalctl -u zdenergy -n 100

# 3. Look for fatal errors
sudo journalctl -u zdenergy | grep "💥"

# 4. Restart if needed
sudo systemctl restart zdenergy
```

### If Health Check Shows Warning:

- Check if sensor is powered on
- Verify network connectivity between sensor and server
- Look at `seconds_since_activity` value
- If > 600s, sensor may be offline or disconnected

### If Health Check Shows Error:

- TCP thread crashed (should auto-restart with new code)
- Check logs for root cause: `sudo journalctl -u zdenergy -n 200`
- Look for exception traces before "💥 Fatal TCP Server error"
- Service restart will recreate thread

## Testing the Fix

### Scenario 1: Normal Operation

1. Deploy code and restart service
2. Wait for sensor to send data (every 5 seconds)
3. Monitor logs: should see 🔌 connection messages
4. Check health: `curl http://146.190.10.188:5000/api/health`
5. Verify `seconds_since_activity` stays low (< 10)

### Scenario 2: Sensor Disconnect

1. Turn off sensor
2. Monitor logs: should see "📴 Gateway disconnected"
3. Check health after 11 minutes: should show "warning"
4. No crash expected - server keeps listening
5. Turn sensor back on: should reconnect automatically

### Scenario 3: Network Issues

1. Simulate network timeout
2. Monitor logs: should see "⚠️ Socket timeout"
3. Server should continue accepting new connections
4. Check health: thread should remain alive

## Success Criteria

✅ Port 6000 listening continuously  
✅ Sensor data appearing in dashboard every 5s  
✅ `/api/health` returns status "ok"  
✅ `seconds_since_activity` < 60 during normal operation  
✅ No "💥 Fatal" errors in logs  
✅ Automatic recovery from sensor disconnections

## Next Steps After Deployment

1. ✅ Deploy changes via `./deploy.sh`
2. ✅ Restart service via `sudo systemctl restart zdenergy`
3. ⏳ Monitor logs for 30 minutes to confirm stability
4. ⏳ Check health endpoint every hour for 24 hours
5. ⏳ Verify CSV exports include today's data
6. 🔄 Report any issues with exact error messages

## Future Enhancements

- [ ] Prometheus metrics export
- [ ] Grafana dashboard for monitoring
- [ ] Slack/email alerts on health check failures
- [ ] TCP connection statistics (connections/hour, bytes received)
- [ ] Auto-restart on consecutive failures

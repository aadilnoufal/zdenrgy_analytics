"""Live sensor dashboard application.

Features:
 - TCP server receives JSON lines like:
	 {"id":"e4643048d7292c2e","time":"2025-10-02 17:58:37","temp":24.10,"rh":50.50,"lux":546.60}
 - Stores last 5,000 readings (in-memory ring buffer)
 - Flask web UI with three live line charts (Temperature, Humidity, Lux) using Chart.js
 - Polling every 5 seconds to update charts (simple + robust). Can later be upgraded to WebSockets/SSE.
"""

from __future__ import annotations

import json
import socket
import threading
from collections import deque
from datetime import datetime
from typing import Deque, Dict, Any, List

from flask import Flask, jsonify, make_response, request

APP_HOST = "0.0.0.0"
HTTP_PORT = 5000
TCP_PORT = 6000
MAX_SAMPLES = 5000
DEBUG = True  # Set False for quieter logs

app = Flask(__name__)

# Thread-safe ring buffer for structured readings
weather_data: Deque[Dict[str, Any]] = deque(maxlen=MAX_SAMPLES)
_data_lock = threading.Lock()
_tcp_thread_started = False

# Debug / metrics state
bytes_received = 0
messages_parsed = 0
invalid_messages = 0
last_valid_raw = ""
last_invalid_raw = ""


def parse_reading(raw: str) -> Dict[str, Any] | None:
		"""Attempt to parse a JSON reading, return dict or None if invalid.

		Ensures required keys exist; normalizes time to ISO 8601 string.
		"""
		raw = raw.strip()
		if not raw:
				return None
		try:
				obj = json.loads(raw)
				# Basic validation
				for k in ("time", "temp", "rh", "lux"):
						if k not in obj:
								return None
				# Normalize/parse time
				t = obj.get("time")
				try:
						# Accept either already ISO or 'YYYY-mm-dd HH:MM:SS'
						if "T" in t:
								dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
						else:
								dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
				except Exception:
						dt = datetime.utcnow()
				obj["time_iso"] = dt.isoformat()
				# Cast numeric fields
				for num_key in ("temp", "rh", "lux"):
						try:
								obj[num_key] = float(obj[num_key])
						except Exception:
								return None
				return obj
		except json.JSONDecodeError:
				return None


def tcp_server():
		"""Receives data from gateway over plain TCP.

		Expects newline-delimited JSON objects or single JSON objects per packet.
		"""
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.bind((APP_HOST, TCP_PORT))
		s.listen(5)
		print(f"TCP Server listening on port {TCP_PORT}...")
		while True:
				client, addr = s.accept()
				print(f"Gateway connected from {addr}")
				buffer = ""
				try:
						while True:
								data = client.recv(4096)
								if not data:
										objs, buffer = _extract_json_objects(buffer)
										for obj in objs:
												_ingest_line(obj)
										break
								decoded_chunk = data.decode("utf-8", errors="ignore")
								buffer += decoded_chunk
								# Update debug counters
								global bytes_received
								bytes_received += len(data)
								if DEBUG:
										print(f"[TCP] recv {len(data)} bytes, buffer_len={len(buffer)} preview={decoded_chunk[:80]!r}")
								# Support newline delim (common for gateways)
								if "\n" in buffer:
										parts = buffer.split("\n")
										buffer = parts.pop()
										for p in parts:
												_ingest_line(p)
								# Extract any complete JSON blobs and keep remainder (partial)
								objs, buffer = _extract_json_objects(buffer)
								for obj in objs:
										_ingest_line(obj)
				finally:
						client.close()


def _extract_json_objects(buffer: str):
		"""Extract complete JSON objects from buffer (supports concatenated objects).

		Returns (objects_list, remaining_partial_buffer).
		Keeps an in-progress (partial) JSON object in the remaining buffer so
		that subsequent TCP reads can complete it.
		"""
		objs: List[str] = []
		start = -1
		depth = 0
		in_string = False
		escape = False
		for i, ch in enumerate(buffer):
				if start == -1:
						if ch == '{':
								start = i
								depth = 1
						else:
								continue
						continue
				# Inside a candidate object
				if in_string:
						if escape:
								escape = False
						elif ch == '\\':
								escape = True
						elif ch == '"':
								in_string = False
				elif ch == '"':
						in_string = True
				elif ch == '{':
						depth += 1
				elif ch == '}':
						depth -= 1
						if depth == 0 and start != -1:
								objs.append(buffer[start : i + 1])
								start = -1
		# Determine remaining (partial) buffer
		if start != -1 and depth > 0:
				remaining = buffer[start:]
		else:
				remaining = ''
		return objs, remaining


def _ingest_line(line: str) -> None:
		reading = parse_reading(line)
		if reading:
				global messages_parsed, last_valid_raw
				with _data_lock:
						weather_data.append(reading)
				messages_parsed += 1
				last_valid_raw = line[:500]
				print(
						f"Stored reading: t={reading['time_iso']} temp={reading['temp']:.2f}°C rh={reading['rh']:.2f}% lux={reading['lux']:.2f}"
				)
		else:
				if line.strip():  # avoid noise for empty splits
						global invalid_messages, last_invalid_raw
						invalid_messages += 1
						last_invalid_raw = line[:500]
						if DEBUG:
								print(f"Discarded invalid payload ({len(line)} chars): {line[:160]}")


@app.after_request
def no_cache(resp):  # type: ignore
		resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
		resp.headers["Pragma"] = "no-cache"
		resp.headers["Expires"] = "0"
		return resp


@app.route("/api/data")
def api_data():
	"""Return recent readings as JSON list.

	Query params:
		limit: max number of most recent samples (default 300)
		minutes: optionally restrict to readings within last N minutes
	"""
	try:
		limit = int(request.args.get("limit", 300))
	except ValueError:
		limit = 300
	limit = max(1, min(limit, MAX_SAMPLES))
	minutes_param = request.args.get("minutes")
	cutoff_ts = None
	if minutes_param:
		try:
			minutes_val = float(minutes_param)
			if minutes_val > 0:
				cutoff_ts = datetime.utcnow().timestamp() - minutes_val * 60.0
		except ValueError:
			pass
	with _data_lock:
		data_list: List[Dict[str, Any]] = list(weather_data)
	if cutoff_ts is not None:
		filtered = []
		for r in reversed(data_list):  # iterate from newest backwards until cutoff
			try:
				ts = datetime.fromisoformat(r["time_iso"].split("+")[0]).timestamp()
			except Exception:
				continue
			if ts >= cutoff_ts:
				filtered.append(r)
			else:
				break
		subset = list(reversed(filtered))[-limit:]
	else:
		subset = data_list[-limit:]
	payload = [
		{
			"time": r["time_iso"],
			"temp": r["temp"],
			"rh": r["rh"],
			"lux": r["lux"],
			"irradiance": r["lux"] / 127.0,  # Convert lux to W/m² (127 lux = 1 W/m²)
		}
		for r in subset
	]
	return make_response(jsonify(payload), 200)


@app.route("/")
def dashboard():  # type: ignore
		"""Main dashboard page with three charts."""
		return (
				"""
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8" />
	<title>Sensor Dashboard</title>
	<meta name="viewport" content="width=device-width,initial-scale=1" />
	<style>
		:root { font-family: system-ui, Arial, sans-serif; background:#0f1115; color:#eee; }
		body { margin: 0; padding: 1.2rem; max-width:1400px; margin:auto; }
		h1 { font-weight:600; letter-spacing:.5px; margin-top:0; }
		.grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(320px,1fr)); gap:1.2rem; }
		.grid-2x2 { display:grid; grid-template-columns: repeat(auto-fit,minmax(320px,1fr)); gap:1.2rem; }
		.card { background:#1c1f26; border:1px solid #2a2f3a; border-radius:12px; padding:1rem 1.1rem 1.6rem; box-shadow:0 4px 16px -6px #000a; }
		.card h2 { margin:0 0 .6rem; font-size:1.05rem; font-weight:500; }
		.chart-container { position:relative; height:280px; width:100%; }
		footer { margin-top:2rem; font-size:.75rem; opacity:.55; }
		.meta { display:flex; gap:1.5rem; flex-wrap:wrap; margin:.2rem 0 1rem; font-size:.85rem; }
		.pill { background:#2d3341; padding:.25rem .55rem; border-radius:20px; }
		a { color:#5eb3ff; text-decoration:none; }
		table { width:100%; border-collapse:collapse; margin-top:1.5rem; font-size:.85rem; }
		th, td { text-align:left; padding:.5rem .75rem; border-bottom:1px solid #2a2f3a; }
		th { background:#1c1f26; font-weight:600; position:sticky; top:0; }
		.table-card { background:#1c1f26; border:1px solid #2a2f3a; border-radius:12px; padding:1rem; margin-top:1.5rem; max-height:400px; overflow-y:auto; }
		.table-card h2 { margin:0 0 .8rem; }
	</style>
	<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
	<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3"></script>
	<script>
		let charts = {};
		let currentWindow = 60; // minutes
		const GAP_MS = 2 * 60 * 1000; // break line if gap > 2 minutes

		async function fetchData() {
			const resp = await fetch(`/api/data?limit=1000&minutes=${currentWindow}`);
			const data = await resp.json();
			// Calculate irradiance if not present (for backward compatibility)
			data.forEach(r => {
				if (!r.irradiance) {
					r.irradiance = r.lux / 127.0;
				}
			});
			return data;
		}

		function buildSeries(raw, field) {
			const series = [];
			let prevTime = null;
			for (const r of raw) {
				const t = new Date(r.time).getTime();
				if (prevTime !== null && (t - prevTime) > GAP_MS) {
					// Insert a null point to create a visible break
					series.push({x: new Date(prevTime + 1), y: null});
				}
				series.push({x: new Date(t), y: r[field]});
				prevTime = t;
			}
			return series;
		}

		function makeChart(ctx, label, color, yTitle) {
			return new Chart(ctx, {
				type: 'line',
				data: { datasets: [{
					label,
					data: [],
					fill:false,
					tension:.25,
					borderColor: color,
					pointRadius:0,
					borderWidth:2,
					spanGaps:false,
					normalized:true
				}]},
				options: {
					responsive:true,
					maintainAspectRatio:false,
					animation:false,
					interaction:{ mode:'nearest', intersect:false },
					scales:{
						x:{ type:'time', time:{ tooltipFormat:'yyyy-MM-dd HH:mm:ss' }, ticks:{ color:'#9aa4b1', maxRotation:0 }, grid:{ color:'#2a3039' } },
						y:{ 
							ticks:{ color:'#9aa4b1' }, 
							grid:{ color:'#2a3039' }, 
							title:{ display:true, text:yTitle, color:'#9aa4b1' },
							suggestedMin: undefined,
							suggestedMax: undefined
						}
					},
					plugins:{ legend:{ labels:{ color:'#d0d7e1' } }, tooltip:{ mode:'index', intersect:false } }
				}
			});
		}

		async function refresh() {
			try {
				const raw = await fetchData();
				if (!charts.temp) {
					charts.temp = makeChart(document.getElementById('chart-temp'), 'Temp', '#ff7369', '°C');
					charts.rh = makeChart(document.getElementById('chart-rh'), 'RH', '#4ecdc4', '%');
					charts.lux = makeChart(document.getElementById('chart-lux'), 'Lux', '#ffd166', 'lux');
					charts.irradiance = makeChart(document.getElementById('chart-irradiance'), 'Irradiance', '#a78bfa', 'W/m²');
				}
				const tempData = buildSeries(raw, 'temp');
				const rhData = buildSeries(raw, 'rh');
				const luxData = buildSeries(raw, 'lux');
				const irradianceData = buildSeries(raw, 'irradiance');
				
				// Update chart data
				charts.temp.data.datasets[0].data = tempData;
				charts.rh.data.datasets[0].data = rhData;
				charts.lux.data.datasets[0].data = luxData;
				charts.irradiance.data.datasets[0].data = irradianceData;
				
				// Auto-scale Y axis with padding
				updateYScale(charts.temp, tempData);
				updateYScale(charts.rh, rhData);
				updateYScale(charts.lux, luxData);
				updateYScale(charts.irradiance, irradianceData);
				
				charts.temp.update();
				charts.rh.update();
				charts.lux.update();
				charts.irradiance.update();
				updateMeta(raw);
				updateTable(raw);
			} catch (e) { console.error(e); }
		}

		function updateYScale(chart, data) {
			const values = data.filter(p => p.y !== null).map(p => p.y);
			if (values.length === 0) return;
			const min = Math.min(...values);
			const max = Math.max(...values);
			const range = max - min;
			const padding = range * 0.1 || 1; // 10% padding or 1 if range is 0
			chart.options.scales.y.suggestedMin = min - padding;
			chart.options.scales.y.suggestedMax = max + padding;
		}

		function updateMeta(raw) {
			if (!raw.length) return;
			const latest = raw[raw.length - 1];
			document.getElementById('latest-temp').textContent = latest.temp.toFixed(2) + ' °C';
			document.getElementById('latest-rh').textContent = latest.rh.toFixed(2) + ' %';
			document.getElementById('latest-lux').textContent = latest.lux.toFixed(2) + ' lx';
			document.getElementById('latest-irradiance').textContent = latest.irradiance.toFixed(3) + ' W/m²';
			document.getElementById('latest-time').textContent = new Date(latest.time).toLocaleString();
		}

		function updateTable(raw) {
			const tbody = document.getElementById('data-tbody');
			tbody.innerHTML = '';
			// Show last 50 readings (most recent first)
			const subset = raw.slice(-50).reverse();
			for (const r of subset) {
				const tr = document.createElement('tr');
				tr.innerHTML = `
					<td>${new Date(r.time).toLocaleString()}</td>
					<td>${r.temp.toFixed(2)}</td>
					<td>${r.rh.toFixed(2)}</td>
					<td>${r.lux.toFixed(2)}</td>
					<td>${r.irradiance.toFixed(3)}</td>
				`;
				tbody.appendChild(tr);
			}
		}

		function handleWindowChange(e){
			currentWindow = parseInt(e.target.value, 10);
			refresh();
		}

		setInterval(refresh, 5000);
		window.addEventListener('DOMContentLoaded', () => {
			document.getElementById('window-select').addEventListener('change', handleWindowChange);
			refresh();
		});
	</script>
</head>
<body>
	<h1>Live Sensor Dashboard</h1>
	<div class="meta">
		<div class="pill">Latest Time: <span id="latest-time">—</span></div>
		<div class="pill">Temp: <span id="latest-temp">—</span></div>
		<div class="pill">Humidity: <span id="latest-rh">—</span></div>
		<div class="pill">Lux: <span id="latest-lux">—</span></div>
		<div class="pill">Irradiance: <span id="latest-irradiance">—</span></div>
		<div class="pill">Refresh: 5s</div>
		<div class="pill">Window: 
			<select id="window-select" style="background:#1c1f26;color:#eee;border:1px solid #2a2f3a;border-radius:6px;padding:2px 6px;">
				<option value="15">15m</option>
				<option value="30">30m</option>
				<option value="60" selected>1h</option>
				<option value="180">3h</option>
				<option value="720">12h</option>
				<option value="1440">24h</option>
			</select>
		</div>
	</div>
	<div class="grid-2x2">
		<div class="card">
			<h2>Temperature</h2>
			<div class="chart-container">
				<canvas id="chart-temp"></canvas>
			</div>
		</div>
		<div class="card">
			<h2>Relative Humidity</h2>
			<div class="chart-container">
				<canvas id="chart-rh"></canvas>
			</div>
		</div>
		<div class="card">
			<h2>Light (Lux)</h2>
			<div class="chart-container">
				<canvas id="chart-lux"></canvas>
			</div>
		</div>
		<div class="card">
			<h2>Solar Irradiance (W/m²)</h2>
			<div class="chart-container">
				<canvas id="chart-irradiance"></canvas>
			</div>
		</div>
	</div>
	<div class="table-card">
		<h2>Live Data (Last 50 Readings)</h2>
		<table>
			<thead>
				<tr>
					<th>Time</th>
					<th>Temperature (°C)</th>
					<th>Humidity (%)</th>
					<th>Lux</th>
					<th>Irradiance (W/m²)</th>
				</tr>
			</thead>
			<tbody id="data-tbody">
			</tbody>
		</table>
	</div>
	<footer>Data updates automatically. Built with Flask + Chart.js. Upgrade to WebSockets later for sub-second latency.</footer>
</body>
</html>
				"""
		)


@app.route("/api/status")
def status():  # type: ignore
		with _data_lock:
				count = len(weather_data)
				latest = weather_data[-1] if count else None
		return jsonify(
				{
						"samples": count,
						"latest": latest,
						"tcp_port": TCP_PORT,
						"http_port": HTTP_PORT,
						"bytes_received": bytes_received,
						"messages_parsed": messages_parsed,
						"invalid_messages": invalid_messages,
						"debug": DEBUG,
						"last_valid_raw": last_valid_raw,
						"last_invalid_raw": last_invalid_raw,
				}
		)


@app.route("/api/debug/toggle", methods=["POST"])
def debug_toggle():  # type: ignore
		global DEBUG
		DEBUG = not DEBUG
		return jsonify({"debug": DEBUG})

def start_tcp_thread_once() -> None:
	"""Start the TCP ingest server in a background thread once per process.

	This ensures ingestion runs when served by Gunicorn (WSGI) as well.
	Note: run with a single Gunicorn worker so only one process binds TCP_PORT.
	"""
	global _tcp_thread_started
	if not _tcp_thread_started:
		t = threading.Thread(target=tcp_server, daemon=True)
		t.start()
		_tcp_thread_started = True


# When running under Gunicorn, the module is imported and __main__ isn't executed.
# Use Flask hook to start the TCP server on first request in that process.
@app.before_first_request
def _start_background_ingest():  # type: ignore
	start_tcp_thread_once()


def main():
		start_tcp_thread_once()
		print(f"Starting Flask web server on port {HTTP_PORT}...")
		# Enable threaded to handle simultaneous API + dashboard requests
		app.run(host=APP_HOST, port=HTTP_PORT, threaded=True)


if __name__ == "__main__":
		main()
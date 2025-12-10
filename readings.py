"""Live sensor dashboard application.

Features:
 - TCP server receives JSON lines like:
	 {"id":"e4643048d7292c2e","time":"2025-10-02 17:58:37","temp":24.10,"rh":50.50,"lux":546.60}
 - Stores data in PostgreSQL database for persistence
 - Maintains in-memory buffer for real-time display
 - Flask web UI with three live line charts (Temperature, Humidity, Lux) using Chart.js
 - Polling every 5 seconds to update charts (simple + robust). Can later be upgraded to WebSockets/SSE.
"""

from __future__ import annotations

import json
import socket
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Any, List
import csv
from io import StringIO

from flask import Flask, jsonify, make_response, request, render_template, Response

# Import KPI calculation modules
from data_sources import create_data_provider
from kpi_calculator import create_kpi_calculator

# Import database manager
from db_manager import get_db_manager

# Import cleaning tracker
from cleaning_tracker import get_cleaning_tracker

APP_HOST = "0.0.0.0"
HTTP_PORT = 5000
TCP_PORT = 6000
MAX_SAMPLES = 1000  # Reduced for in-memory buffer (real-time display only)
DEBUG = True  # Set False for quieter logs

app = Flask(__name__)

# Thread-safe ring buffer for structured readings
weather_data: Deque[Dict[str, Any]] = deque(maxlen=MAX_SAMPLES)
_data_lock = threading.Lock()

# Track last database insertion time
_last_db_insertion_time = None

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
		"""Receives data from gateway over plain TCP with robust error handling.

		Expects newline-delimited JSON objects or single JSON objects per packet.
		Automatically recovers from errors and keeps running.
		"""
		global _tcp_last_activity
		print(f"🚀 Starting TCP Server on port {TCP_PORT}...")
		
		while True:  # Outer loop: restart server on fatal errors
				s = None
				try:
						_tcp_last_activity = datetime.utcnow()
						s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
						# Set socket timeout to detect stale connections
						s.settimeout(300)  # 5 minute timeout
						s.bind((APP_HOST, TCP_PORT))
						s.listen(5)
						print(f"✅ TCP Server listening on port {TCP_PORT}")
						
						while True:  # Inner loop: accept connections
								try:
										_tcp_last_activity = datetime.utcnow()
										client, addr = s.accept()
										print(f"🔌 Gateway connected from {addr}")
										
										# Set client socket timeout
										client.settimeout(60)  # 60 second timeout for recv
										
										buffer = ""
										try:
												while True:
														try:
																_tcp_last_activity = datetime.utcnow()
																data = client.recv(4096)
																if not data:
																		# Connection closed gracefully
																		print(f"📴 Gateway {addr} disconnected")
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
																		
														except socket.timeout:
																print(f"⚠️  Socket timeout for {addr} - closing connection")
																break
														except Exception as e:
																print(f"❌ Error receiving data from {addr}: {e}")
																break
												
										finally:
												client.close()
												print(f"🔒 Connection closed for {addr}")
												
								except socket.timeout:
										# Accept timeout - this is normal, just continue
										continue
								except Exception as e:
										print(f"❌ Error accepting connection: {e}")
										# Continue accepting new connections
										continue
						
				except Exception as e:
						print(f"💥 Fatal TCP server error: {e}")
						print("🔄 Restarting TCP server in 5 seconds...")
						if s:
								try:
										s.close()
								except:
										pass
						import time
						time.sleep(5)
						# Loop continues, server will restart


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
				global messages_parsed, last_valid_raw, _last_db_insertion_time
				
				messages_parsed += 1
				last_valid_raw = line[:500]
				
				# Store in memory for real-time display
				with _data_lock:
						weather_data.append(reading)
				
				# Store in database for persistence (throttled to once per 5 minutes)
				try:
						now = datetime.utcnow()
						if _last_db_insertion_time is None or (now - _last_db_insertion_time).total_seconds() >= 60:
								db = get_db_manager()
								# Parse timestamp - keep as-is from sensor (GMT+8 China time)
								# Database stores GMT+8, conversion to Qatar time happens on retrieval
								timestamp = datetime.fromisoformat(reading['time_iso'])
								if timestamp.tzinfo is None:
										# Store as naive datetime (sensor's GMT+8 time)
										timestamp = timestamp.replace(tzinfo=None)
								
								# Calculate irradiance if not present
								irradiance = reading.get('irradiance')
								if irradiance is None and reading.get('lux'):
										irradiance = reading['lux'] / 127.0  # Convert lux to W/m²
								
								db.insert_sensor_reading(
										temperature=reading.get('temp'),
										humidity=reading.get('rh'),
										lux=reading.get('lux'),
										irradiance=irradiance,
										timestamp=timestamp,
										sensor_id=reading.get('id', 'unknown')
								)
								_last_db_insertion_time = now
								if DEBUG:
										print(f"✅ Saved to DB: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
				except Exception as e:
						print(f"⚠️  Failed to store reading in database: {e}")
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


# --- Background TCP server bootstrap (works under Gunicorn) -----------------
# When running under Gunicorn, the __main__ block is not executed. To ensure the
# TCP server is started in production, we start it at module import time in a
# thread-safe, idempotent way. IMPORTANT: Run Gunicorn with a single worker
# (e.g. -w 1 --threads 8). Multiple workers would create separate processes with
# separate memory and cause either port conflicts or split state.

_tcp_started = False
_tcp_start_lock = threading.Lock()
_tcp_last_activity = datetime.utcnow()  # Track last TCP activity
_tcp_thread = None


def ensure_tcp_started() -> None:
	"""Start the TCP server thread exactly once in this process."""
	global _tcp_started, _tcp_thread, _tcp_last_activity
	if _tcp_started:
		return
	with _tcp_start_lock:
		if _tcp_started:
			return
		_tcp_last_activity = datetime.utcnow()
		_tcp_thread = threading.Thread(target=tcp_server, daemon=True, name="tcp-server")
		_tcp_thread.start()
		_tcp_started = True
		print(f"🚀 TCP server thread started on port {TCP_PORT}")


@app.route("/api/data")
def api_data():
	"""Return sensor readings as JSON.

	Query params:
		window: Time window in minutes (e.g., 60, 120, 1440)
		date: Specific date in YYYY-MM-DD format (returns full day)
		start_date: Start date in YYYY-MM-DD format (requires end_date)
		end_date: End date in YYYY-MM-DD format (requires start_date)
		limit: Max number of readings (default 1000)
	"""
	ensure_tcp_started()
	
	# Check for date range parameters
	start_date_param = request.args.get('start_date')
	end_date_param = request.args.get('end_date')
	
	if start_date_param and end_date_param:
		# Return date range from database
		try:
			db = get_db_manager()
			start_dt = datetime.strptime(start_date_param, '%Y-%m-%d')
			end_dt = datetime.strptime(end_date_param, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
			
			readings = db.get_readings_by_time_range(start_dt, end_dt)
			
			# Format readings
			formatted = []
			for r in readings:
				# Return database timestamp as-is (GMT+8)
				ts = r.get('timestamp')
				if isinstance(ts, datetime):
					time_str = ts.isoformat()
				else:
					time_str = str(ts)

				formatted.append({
					'time': time_str,
					'temp': float(r.get('temperature')) if r.get('temperature') is not None else None,
					'rh': float(r.get('humidity')) if r.get('humidity') is not None else None,
					'lux': float(r.get('lux')) if r.get('lux') is not None else None,
					'irradiance': float(r.get('irradiance')) if r.get('irradiance') is not None else None,
				})
			
			return jsonify({
				'readings': formatted,
				'count': len(formatted),
				'source': 'database',
				'start_date': start_date_param,
				'end_date': end_date_param
			})
		except Exception as e:
			return jsonify({'error': str(e)}), 500
	
	# Check for single date parameter
	date_param = request.args.get('date')
	if date_param:
		# Return full day from database
		try:
			db = get_db_manager()
			readings = db.get_readings_by_date(date_param)
			# Normalize/format to match other endpoints
			formatted = []
			for r in readings:
				# Support either DB-shaped or API-shaped rows
				# Database stores GMT+8 (China time), convert to Qatar GMT+3
				ts = r.get('timestamp', r.get('time'))
				if isinstance(ts, datetime):
					ts_qatar = ts - timedelta(hours=5)
					time_str = ts_qatar.isoformat()
				else:
					time_str = str(ts)

				# Choose value keys depending on shape
				temp_val = r.get('temperature', r.get('temp'))
				rh_val = r.get('humidity', r.get('rh'))
				lux_val = r.get('lux')
				irr_val = r.get('irradiance')

				formatted.append({
					'time': time_str,
					'temp': float(temp_val) if temp_val is not None else None,
					'rh': float(rh_val) if rh_val is not None else None,
					'lux': float(lux_val) if lux_val is not None else None,
					'irradiance': float(irr_val) if irr_val is not None else None,
				})

			return jsonify({
				'readings': formatted,
				'count': len(formatted),
				'source': 'database',
				'date': date_param
			})
		except Exception as e:
			return jsonify({'error': str(e)}), 500
	
	# Check for time window parameter
	window_minutes = request.args.get('window', type=int)
	limit = request.args.get('limit', default=1000, type=int)
	limit = max(1, min(limit, 10000))
	
	if window_minutes:
		# Query from database for specific time window
		try:
			db = get_db_manager()
			readings = db.get_readings_by_window(window_minutes)
			
			# Format readings
			formatted = []
			for r in readings:
				# Return database timestamp as-is (GMT+8)
				ts = r.get('timestamp')
				if isinstance(ts, datetime):
					time_str = ts.isoformat()
				else:
					time_str = str(ts)

				formatted.append({
					'time': time_str,
					'temp': float(r.get('temperature')) if r.get('temperature') is not None else None,
					'rh': float(r.get('humidity')) if r.get('humidity') is not None else None,
					'lux': float(r.get('lux')) if r.get('lux') is not None else None,
					'irradiance': float(r.get('irradiance')) if r.get('irradiance') is not None else None,
				})
			
			# Apply limit
			if len(formatted) > limit:
				formatted = formatted[-limit:]
			
			return jsonify({
				'readings': formatted,
				'count': len(formatted),
				'source': 'database',
				'window_minutes': window_minutes
			})
		except Exception as e:
			print(f"⚠️ Database query failed: {e}")
			# Fall back to memory
			with _data_lock:
				data = list(weather_data)[-limit:]
			formatted = [{
				'time': r.get('time_iso', r.get('time')),
				'temp': r.get('temp'),
				'rh': r.get('rh'),
				'lux': r.get('lux'),
				'irradiance': r.get('irradiance', r.get('lux', 0) / 127.0 if r.get('lux') else 0)
			} for r in data]
			return jsonify({
				'readings': formatted,
				'count': len(formatted),
				'source': 'memory'
			})
	
	# Default: return in-memory buffer
	with _data_lock:
		data = list(weather_data)[-limit:]
	
	formatted = []
	for r in data:
		# Emit UTC ISO string if possible
		ts_str = r.get('time_iso', r.get('time'))
		# If the sensor time is naive ISO without tz, append Z to indicate UTC
		if isinstance(ts_str, str) and 'Z' not in ts_str and '+' not in ts_str:
			try:
				# Validate parse; if parseable, mark as UTC
				datetime.fromisoformat(ts_str)
				ts_str = ts_str + 'Z'
			except Exception:
				pass
		formatted.append({
			'time': ts_str,
			'temp': r.get('temp'),
			'rh': r.get('rh'),
			'lux': r.get('lux'),
			'irradiance': r.get('irradiance', (r.get('lux') / 127.0) if (r.get('lux') is not None) else 0)
		})
	
	return jsonify({
		'readings': formatted,
		'count': len(formatted),
		'source': 'memory'
	})


@app.route("/api/dates")
def api_dates():
	"""Return available date range with data.
	
	Returns:
		{
			'date_range': {'min_date': 'YYYY-MM-DD', 'max_date': 'YYYY-MM-DD'},
			'total_readings': N
		}
	"""
	try:
		db = get_db_manager()
		date_range = db.get_date_range()
		stats = db.get_statistics()
		
		return jsonify({
			'date_range': date_range,
			'total_readings': stats.get('total_readings', 0)
		})
	except Exception as e:
		return jsonify({'error': str(e)}), 500


@app.route("/api/export/csv")
def export_csv():
	"""Export sensor data to CSV format.
	
	Query params:
		start_date: Start date (YYYY-MM-DD) - optional
		end_date: End date (YYYY-MM-DD) - optional
		all: Set to 'true' to export all data - optional
		
	If no params provided, exports last 24 hours
	"""
	try:
		db = get_db_manager()
		export_all = request.args.get('all', '').lower() == 'true'
		start_date = request.args.get('start_date')
		end_date = request.args.get('end_date')
		
		# Determine what data to export
		if export_all:
			# Export all data
			conn = db.get_connection()
			cursor = conn.cursor()
			cursor.execute("""
				SELECT timestamp, temperature, humidity, lux, irradiance
				FROM sensor_readings
				ORDER BY timestamp ASC;
			""")
			rows = cursor.fetchall()
			cursor.close()
			db.return_connection(conn)
			filename = "sensor_data_all.csv"
			
		elif start_date and end_date:
			# Export date range
			start_dt = datetime.strptime(start_date, '%Y-%m-%d')
			end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
			
			readings = db.get_readings_by_time_range(start_dt, end_dt)
			rows = [(r['timestamp'], r.get('temperature'), r.get('humidity'), 
					 r.get('lux'), r.get('irradiance')) for r in readings]
			filename = f"sensor_data_{start_date}_to_{end_date}.csv"
			
		elif start_date:
			# Export single date
			readings = db.get_readings_by_date(start_date)
			rows = [(datetime.fromisoformat(r['time']), r.get('temp'), r.get('rh'),
					 r.get('lux'), r.get('irradiance')) for r in readings]
			filename = f"sensor_data_{start_date}.csv"
			
		else:
			# Default: last 24 hours
			readings = db.get_readings_by_window(1440)  # 24 hours
			rows = [(r['timestamp'], r.get('temperature'), r.get('humidity'),
					 r.get('lux'), r.get('irradiance')) for r in readings]
			filename = "sensor_data_last_24h.csv"
		
		# Create CSV in memory
		output = StringIO()
		writer = csv.writer(output)
		
		# Write header
		writer.writerow(['Timestamp', 'Temperature (°C)', 'Humidity (%)', 'Lux', 'Irradiance (W/m²)'])
		
		# Write data rows
		for row in rows:
			timestamp, temp, humidity, lux, irradiance = row
			# Format timestamp and convert to Qatar time
			if isinstance(timestamp, datetime):
				# Convert China (GMT+8) to Qatar (GMT+3)
				ts_qatar = timestamp - timedelta(hours=5)
				ts_str = ts_qatar.strftime('%Y-%m-%d %H:%M:%S')
			else:
				ts_str = str(timestamp)
			
			writer.writerow([
				ts_str,
				f"{temp:.2f}" if temp is not None else '',
				f"{humidity:.2f}" if humidity is not None else '',
				f"{lux:.2f}" if lux is not None else '',
				f"{irradiance:.3f}" if irradiance is not None else ''
			])
		
		# Create response
		output.seek(0)
		response = Response(output.getvalue(), mimetype='text/csv')
		response.headers['Content-Disposition'] = f'attachment; filename={filename}'
		
		return response
		
	except Exception as e:
		return jsonify({'error': str(e)}), 500


@app.route("/")
def dashboard():  # type: ignore
		"""Main dashboard page with three charts."""
		return render_template("dashboard.html")


@app.route("/kpi")
def kpi_page():  # type: ignore
		"""KPI page."""
		return render_template("kpi.html")


@app.route("/kpi/battery")
def kpi_battery():  # type: ignore
		"""Battery KPI page."""
		return render_template("kpi-battery.html")


@app.route("/kpi/inverter")
def kpi_inverter():  # type: ignore
		"""Inverter KPI page."""
		return render_template("kpi-inverter.html")


@app.route("/kpi/charger")
def kpi_charger():  # type: ignore
		"""DC Charger KPI page."""
		return render_template("kpi-charger.html")


@app.route("/kpi/solar")
def kpi_solar():  # type: ignore
		"""Solar Array KPI page."""
		return render_template("kpi-solar.html")


@app.route("/api/kpi")
def api_kpi():  # type: ignore
		"""Return calculated KPIs as JSON.
		
		This endpoint uses the DataProvider and KPICalculator to compute
		all available KPIs from configured data sources.
		"""
		try:
				# Create data provider with access to sensor data
				data_provider = create_data_provider(weather_data)
				
				# Create KPI calculator
				calculator = create_kpi_calculator(data_provider)
				
				# Calculate all KPIs
				summary = calculator.calculate_summary()
				
				return make_response(jsonify(summary), 200)
		except Exception as e:
				return make_response(
						jsonify({"error": str(e), "kpis": {}}),
						500
				)


@app.route("/api/kpi/<kpi_name>")
def api_kpi_single(kpi_name: str):  # type: ignore
		"""Return a single calculated KPI by name.
		
		Available KPIs:
		- solar_generation
		- daily_solar_energy
		- building_load
		- self_consumption_ratio
		- battery_soc
		- daily_cost_savings
		- grid_export_revenue
		- daily_carbon_offset
		- temperature
		- humidity
		"""
		try:
				data_provider = create_data_provider(weather_data)
				calculator = create_kpi_calculator(data_provider)
				
				# Map KPI names to calculator methods
				kpi_methods = {
						"solar_generation": calculator.calculate_solar_generation,
						"daily_solar_energy": calculator.calculate_daily_solar_energy,
						"building_load": calculator.calculate_building_load,
						"self_consumption_ratio": calculator.calculate_self_consumption_ratio,
						"battery_soc": calculator.calculate_battery_status,
						"daily_cost_savings": calculator.calculate_energy_cost_savings,
						"grid_export_revenue": calculator.calculate_grid_export_revenue,
						"daily_carbon_offset": calculator.calculate_carbon_offset,
						"temperature": calculator.calculate_temperature_status,
						"humidity": calculator.calculate_humidity_status,
				}
				
				if kpi_name not in kpi_methods:
						return make_response(
								jsonify({"error": f"Unknown KPI: {kpi_name}"}),
								404
						)
				
				result = kpi_methods[kpi_name]()
				
				return make_response(jsonify({
						"name": result.name,
						"display_name": result.display_name,
						"value": result.value,
						"unit": result.unit,
						"timestamp": result.timestamp,
						"metadata": result.metadata,
				}), 200)
		except Exception as e:
				return make_response(
						jsonify({"error": str(e)}),
						500
				)


@app.route("/api/health")
def api_health():  # type: ignore
		"""Health check endpoint to monitor TCP server status."""
		global _tcp_started, _tcp_thread, _tcp_last_activity, messages_parsed, invalid_messages, bytes_received
		
		# Get start time from server initialization
		import time
		server_start_time = datetime.utcnow() - timedelta(seconds=time.time() - app.config.get('_start_time', time.time()))
		if '_start_time' not in app.config:
				app.config['_start_time'] = time.time()
				server_start_time = datetime.utcnow()
		
		now = datetime.utcnow()
		uptime_seconds = (now - server_start_time).total_seconds()
		seconds_since_last_data = (now - _tcp_last_activity).total_seconds() if _tcp_last_activity else None
		
		# Get database statistics
		db_stats = {"total_readings": 0, "date_range": None}
		db_connected = False
		try:
				db = get_db_manager()
				db_connected = db is not None
				if db_connected:
						db_stats = db.get_statistics()
						date_range = db.get_date_range()
						db_stats['date_range'] = date_range
		except Exception as e:
				print(f"⚠️ Error getting DB stats: {e}")
		
		# Get memory count
		with _data_lock:
				memory_count = len(weather_data)
		
		health = {
				"status": "ok",
				"start_time": server_start_time.isoformat(),
				"uptime_seconds": uptime_seconds,
				"tcp_server": {
						"listening": _tcp_started and (_tcp_thread is not None and _tcp_thread.is_alive()),
						"port": TCP_PORT,
						"heartbeat_age": seconds_since_last_data if seconds_since_last_data else 0,
						"last_connection_time": _tcp_last_activity.isoformat() if _tcp_last_activity else None,
						"seconds_since_last_data": seconds_since_last_data,
						"connections_received": 1 if messages_parsed > 0 else 0,  # Simplified tracking
						"messages_parsed": messages_parsed,
						"invalid_messages": invalid_messages,
				},
				"memory": {
						"count": memory_count,
						"max_size": MAX_SAMPLES,
				},
				"database": {
						"connected": db_connected,
						"total_readings": db_stats.get('total_readings', 0),
						"date_range": db_stats.get('date_range'),
				},
				"timestamp": now.isoformat(),
		}
		
		# Set status to warning if no activity for 10 minutes
		if seconds_since_last_data and seconds_since_last_data > 600:
				health["status"] = "warning"
				health["warnings"] = [f"No TCP activity for {int(seconds_since_last_data)}s"]
		
		# Set status to error if thread is dead
		if _tcp_started and (_tcp_thread is None or not _tcp_thread.is_alive()):
				health["status"] = "error"
				health["errors"] = ["TCP server thread is not running"]
		
		status_code = 200 if health["status"] == "ok" else 503
		return make_response(jsonify(health), status_code)


@app.route("/api/parameters")
def api_parameters():  # type: ignore
		"""Return all configured parameters and their current values."""
		try:
				from config import ALL_PARAMETERS
				
				data_provider = create_data_provider(weather_data)
				
				parameters = {}
				for name, param in ALL_PARAMETERS.items():
						try:
								value = data_provider.get(name)
								parameters[name] = {
										"display_name": param.display_name,
										"value": value,
										"unit": param.unit,
										"source": param.source.value,
										"description": param.description,
								}
						except Exception:
								parameters[name] = {
										"display_name": param.display_name,
										"value": param.default_value,
										"unit": param.unit,
										"source": param.source.value,
										"description": param.description,
										"error": "Unable to fetch"
								}
				
				return make_response(jsonify({"parameters": parameters}), 200)
		except Exception as e:
				return make_response(
						jsonify({"error": str(e)}),
						500
				)


@app.route("/api/status")
def status():  # type: ignore
		"""Return system status including database statistics."""
		with _data_lock:
				count = len(weather_data)
				latest = weather_data[-1] if count else None
		
		# Get database statistics
		try:
				db = get_db_manager()
				db_stats = db.get_statistics()
		except Exception as e:
				db_stats = {"error": str(e)}
		
		return jsonify(
				{
						"samples_in_memory": count,
						"latest": latest,
						"database_stats": db_stats,
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


@app.route("/api/cleaning/stats")
def api_cleaning_stats():  # type: ignore
		"""Get solar panel cleaning statistics and recommendations"""
		try:
				tracker = get_cleaning_tracker()
				stats = tracker.get_cleaning_stats()
				return jsonify(stats)
		except Exception as e:
				return jsonify({"error": str(e)}), 500


@app.route("/api/cleaning/record", methods=["POST"])
def api_record_cleaning():  # type: ignore
		"""Record a panel cleaning event"""
		try:
				tracker = get_cleaning_tracker()
				data = request.get_json() or {}
				
				cleaning_date = data.get('cleaning_date')
				if cleaning_date:
						cleaning_date = datetime.fromisoformat(cleaning_date)
				
				baseline_ratio = data.get('baseline_ratio')
				notes = data.get('notes', '')
				
				success = tracker.record_cleaning(
						cleaning_date=cleaning_date,
						baseline_ratio=baseline_ratio,
						notes=notes
				)
				
				if success:
						return jsonify({
								"success": True,
								"message": "Cleaning recorded successfully"
						})
				else:
						return jsonify({
								"success": False,
								"error": "Failed to record cleaning"
						}), 500
		except Exception as e:
				return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cleaning/history")
def api_cleaning_history():  # type: ignore
		"""Get cleaning history"""
		try:
				tracker = get_cleaning_tracker()
				limit = request.args.get('limit', default=10, type=int)
				history = tracker.get_cleaning_history(limit=limit)
				return jsonify({"history": history})
		except Exception as e:
				return jsonify({"error": str(e)}), 500


# =============================================================================
# SOLAR CLEANING ANALYZER API ROUTES
# =============================================================================

# Store analyzer instance and uploaded data in memory
_analyzer_data = {
		'lux_df': None,
		'inverter_df': None,
		'cleaning_dates': [],
		'last_analysis': None
}

@app.route("/api/analyzer/upload", methods=["POST"])
def api_analyzer_upload():
		"""Upload CSV files for analysis"""
		from solar_cleaning_analyzer import parse_lux_csv, parse_inverter_csv
		import tempfile
		import os
		
		try:
				# Accept both 'type' and 'file_type' for flexibility
				file_type = request.form.get('type') or request.form.get('file_type')  # 'lux' or 'inverter'
				
				print(f"[DEBUG] Upload request - form data: {dict(request.form)}")
				print(f"[DEBUG] Upload request - files: {list(request.files.keys())}")
				print(f"[DEBUG] file_type: {file_type}")
				
				if 'file' not in request.files:
						return jsonify({"success": False, "error": "No file provided"}), 400
				
				file = request.files['file']
				if file.filename == '':
						return jsonify({"success": False, "error": "No file selected"}), 400
				
				if not file_type:
						return jsonify({"success": False, "error": "File type not specified. Use 'lux' or 'inverter'"}), 400
				
				# Save to temp file and parse
				with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
						file.save(tmp.name)
						tmp_path = tmp.name
				
				try:
						if file_type == 'lux':
								df = parse_lux_csv(tmp_path)
								_analyzer_data['lux_df'] = df
								return jsonify({
										"success": True,
										"type": "lux",
										"rows": len(df),
										"date_range": {
												"start": df['timestamp'].min().isoformat(),
												"end": df['timestamp'].max().isoformat()
										},
										"preview": df.head(5).to_dict(orient='records')
								})
						elif file_type == 'inverter':
								df = parse_inverter_csv(tmp_path)
								_analyzer_data['inverter_df'] = df
								return jsonify({
										"success": True,
										"type": "inverter",
										"rows": len(df),
										"date_range": {
												"start": df['timestamp'].min().isoformat(),
												"end": df['timestamp'].max().isoformat()
										},
										"total_kwh": round(df['actual_kwh'].sum(), 2),
										"preview": df.head(5).to_dict(orient='records')
								})
						else:
								return jsonify({"success": False, "error": "Invalid file type. Use 'lux' or 'inverter'"}), 400
				finally:
						os.unlink(tmp_path)
						
		except Exception as e:
				import traceback
				traceback.print_exc()
				return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyzer/cleaning-dates", methods=["POST"])
def api_analyzer_cleaning_dates():
		"""Add or update cleaning dates for analysis"""
		try:
				data = request.get_json() or {}
				dates = data.get('dates', [])
				
				cleaning_dates = []
				for date_str in dates:
						try:
								dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
								cleaning_dates.append(dt)
						except:
								try:
										dt = datetime.strptime(date_str, '%Y-%m-%d')
										cleaning_dates.append(dt)
								except:
										pass
				
				_analyzer_data['cleaning_dates'] = sorted(cleaning_dates)
				
				return jsonify({
						"success": True,
						"cleaning_dates": [d.isoformat() for d in _analyzer_data['cleaning_dates']]
				})
		except Exception as e:
				return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyzer/run", methods=["POST"])
def api_analyzer_run():
		"""Run the cleaning interval analysis"""
		from solar_cleaning_analyzer import SolarCleaningAnalyzer, SYSTEM_CONFIG
		
		try:
				data = request.get_json() or {}
				
				# Update system configuration if provided
				capacity = data.get('capacity_kwp', 10.0)
				SYSTEM_CONFIG.capacity_kwp = float(capacity)
				
				# Allow configuring lux-to-irradiance conversion factor
				lux_factor = data.get('lux_conversion_factor', 165.0)
				SYSTEM_CONFIG.lux_to_irradiance = float(lux_factor)
				
				print(f"📊 CONFIG: Capacity={SYSTEM_CONFIG.capacity_kwp} kWp, Lux factor={SYSTEM_CONFIG.lux_to_irradiance}")
				
				# Check if data is loaded
				if _analyzer_data['lux_df'] is None:
						return jsonify({"success": False, "error": "No lux data uploaded. Please upload lux CSV first."}), 400
				if _analyzer_data['inverter_df'] is None:
						return jsonify({"success": False, "error": "No inverter data uploaded. Please upload inverter CSV first."}), 400
				
				# Debug: Show date ranges
				lux_df = _analyzer_data['lux_df']
				inverter_df = _analyzer_data['inverter_df']
				print(f"📊 DEBUG: Lux data - {len(lux_df)} rows, range: {lux_df['timestamp'].min()} to {lux_df['timestamp'].max()}")
				print(f"📊 DEBUG: Inverter data - {len(inverter_df)} rows, range: {inverter_df['timestamp'].min()} to {inverter_df['timestamp'].max()}")
				
				# Re-calculate irradiance with updated conversion factor
				lux_df['irradiance'] = (lux_df['lux'] / SYSTEM_CONFIG.lux_to_irradiance).clip(upper=SYSTEM_CONFIG.max_irradiance)
				
				# Create analyzer and load data
				analyzer = SolarCleaningAnalyzer()
				success, debug_info = analyzer.load_from_dataframes(
						lux_df,
						_analyzer_data['inverter_df'],
						_analyzer_data['cleaning_dates']
				)
				
				print(f"📊 DEBUG: Merge result - success={success}, debug_info={debug_info}")
				
				if not success:
						error_msg = debug_info.get('error', 'Failed to merge data')
						
						# Build helpful error message
						if not debug_info.get('overlap_found', True):
								lux_range = debug_info.get('lux_date_range', {})
								inv_range = debug_info.get('inverter_date_range', {})
								error_msg = f"No date overlap found! Lux data: {lux_range.get('min', 'N/A')} to {lux_range.get('max', 'N/A')}, Inverter data: {inv_range.get('min', 'N/A')} to {inv_range.get('max', 'N/A')}"
						elif debug_info.get('merged_rows', 0) == 0:
								error_msg = f"Data exists but timestamps don't match after rounding to 30-min intervals. Lux samples: {debug_info.get('lux_sample_timestamps', [])}, Inverter samples: {debug_info.get('inverter_sample_timestamps', [])}"
						
						return jsonify({
								"success": False, 
								"error": error_msg,
								"debug_info": debug_info
						}), 400
				
				# Generate report
				report = analyzer.generate_report()
				
				if not report.get('success'):
						return jsonify({"success": False, "error": report.get('error', 'Analysis failed')}), 400
				
				# Store for later retrieval
				_analyzer_data['last_analysis'] = report
				
				return jsonify(report)
				
		except Exception as e:
				import traceback
				traceback.print_exc()
				return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyzer/status")
def api_analyzer_status():
		"""Get current analyzer data status"""
		status = {
				"lux_loaded": _analyzer_data['lux_df'] is not None,
				"inverter_loaded": _analyzer_data['inverter_df'] is not None,
				"cleaning_dates": [d.isoformat() for d in _analyzer_data['cleaning_dates']],
				"has_analysis": _analyzer_data['last_analysis'] is not None
		}
		
		if _analyzer_data['lux_df'] is not None:
				df = _analyzer_data['lux_df']
				status['lux_info'] = {
						"rows": len(df),
						"date_range": {
								"start": df['timestamp'].min().isoformat(),
								"end": df['timestamp'].max().isoformat()
						}
				}
		
		if _analyzer_data['inverter_df'] is not None:
				df = _analyzer_data['inverter_df']
				status['inverter_info'] = {
						"rows": len(df),
						"date_range": {
								"start": df['timestamp'].min().isoformat(),
								"end": df['timestamp'].max().isoformat()
						},
						"total_kwh": round(df['actual_kwh'].sum(), 2)
				}
		
		return jsonify(status)


@app.route("/api/analyzer/results")
def api_analyzer_results():
		"""Get the last analysis results"""
		if _analyzer_data['last_analysis'] is None:
				return jsonify({"success": False, "error": "No analysis has been run yet"}), 404
		
		return jsonify(_analyzer_data['last_analysis'])


@app.route("/api/analyzer/clear", methods=["POST"])
def api_analyzer_clear():
		"""Clear all uploaded data"""
		_analyzer_data['lux_df'] = None
		_analyzer_data['inverter_df'] = None
		_analyzer_data['cleaning_dates'] = []
		_analyzer_data['last_analysis'] = None
		
		return jsonify({"success": True, "message": "All analyzer data cleared"})


def main():
		# Safe to call multiple times; starts only once per process
		ensure_tcp_started()
		print(f"Starting Flask web server on port {HTTP_PORT}...")
		# Enable threaded to handle simultaneous API + dashboard requests
		app.run(host=APP_HOST, port=HTTP_PORT, threaded=True)


if __name__ == "__main__":
		main()

# Ensure TCP server is started when imported by WSGI servers like Gunicorn
# This must remain at the end of the module so all functions are defined.
ensure_tcp_started()
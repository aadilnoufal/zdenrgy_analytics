let charts = {};
let currentWindow = 60; // minutes
let currentMode = 'live'; // 'live', 'historical', or 'range'
let selectedDate = null;
let selectedStartDate = null;
let selectedEndDate = null;
let refreshInterval = null;
const GAP_MS = 2 * 60 * 1000; // break line if gap > 2 minutes

async function fetchData() {
	let url;
	if (currentMode === 'range' && selectedStartDate && selectedEndDate) {
		url = `/api/data?start_date=${selectedStartDate}&end_date=${selectedEndDate}`;
	} else if (currentMode === 'historical' && selectedDate) {
		url = `/api/data?date=${selectedDate}`;
	} else {
		url = `/api/data?window=${currentWindow}`;
	}
	
	const resp = await fetch(url);
	const json = await resp.json();
	
	// Handle new response format
	const raw = json.readings || json;
	
	// Calculate irradiance if not present (for backward compatibility)
	raw.forEach(r => {
		if (!r.irradiance) {
			r.irradiance = r.lux / 127.0;
		}
	});
	
	return raw;
}

function buildSeries(raw, field) {
	const series = [];
	let prevTimeStr = null;
	for (const r of raw) {
		// Display timestamp as-is from database (no timezone conversion)
		const timeStr = r.time.replace('T', ' ').replace(/\.\d+/, '').split('+')[0].split('Z')[0];
		
		series.push({x: timeStr, y: r[field]});
		prevTimeStr = timeStr;
	}
	return series;
}

function makeChart(ctx, label, color, yTitle, isFullscreen = false) {
	return new Chart(ctx, {
		type: 'line',
		data: { datasets: [{
			label,
			data: [],
			fill: false,
			tension: .25,
			borderColor: color,
			pointRadius: isFullscreen ? 2 : 0,
			borderWidth: isFullscreen ? 3 : 2,
			spanGaps: false,
			normalized: true
		}]},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			animation: false,
			interaction: { 
				mode: 'nearest', 
				intersect: false,
				axis: 'x'
			},
			scales: {
				x: {
					type: 'category',
					ticks: { 
						color: '#9aa4b1', 
						maxRotation: 0,
						font: { size: isFullscreen ? 14 : 11 }
					},
					grid: { color: '#2a3039' }
				},
				y: {
					ticks: { 
						color: '#9aa4b1',
						font: { size: isFullscreen ? 14 : 11 }
					},
					grid: { color: '#2a3039' },
					title: { 
						display: true, 
						text: yTitle, 
						color: '#9aa4b1',
						font: { size: isFullscreen ? 16 : 12 }
					},
					suggestedMin: undefined,
					suggestedMax: undefined
				}
			},
			plugins: {
				legend: { 
					labels: { 
						color: '#d0d7e1',
						font: { size: isFullscreen ? 16 : 12 }
					} 
				},
				tooltip: { 
					mode: 'index', 
					intersect: false,
					titleFont: { size: isFullscreen ? 14 : 12 },
					bodyFont: { size: isFullscreen ? 13 : 11 }
				},
				zoom: {
					pan: {
						enabled: true,
						mode: 'x',
						modifierKey: null,
					},
					zoom: {
						wheel: {
							enabled: true,
							speed: 0.1,
						},
						pinch: {
							enabled: true
						},
						mode: 'x',
					},
					limits: {
						x: { min: 'original', max: 'original' },
					}
				}
			}
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
		
		// Update fullscreen chart if open
		updateFullscreenChart();
	} catch (e) {
		console.error(e);
	}
}

function updateYScale(chart, data) {
	const values = data.filter(p => p.y !== null).map(p => p.y);
	if (values.length === 0) return;
	const min = Math.min(...values);
	const max = Math.max(...values);
	const range = max - min;
	const padding = Math.max(range * 0.1, 1); // 10% padding or at least 1 unit
	// Round to whole numbers for cleaner scaling
	chart.options.scales.y.suggestedMin = Math.floor(min - padding);
	chart.options.scales.y.suggestedMax = Math.ceil(max + padding);
	// Set step size to 1 for cleaner grid lines
	chart.options.scales.y.ticks.stepSize = 1;
}

function updateMeta(raw) {
	document.getElementById('reading-count').textContent = raw.length;
	
	if (!raw.length) {
		document.getElementById('latest-time').textContent = '—';
		document.getElementById('current-temp').textContent = '—';
		document.getElementById('current-rh').textContent = '—';
		document.getElementById('current-lux').textContent = '—';
		document.getElementById('current-irradiance').textContent = '—';
		return;
	}
	
	const latest = raw[raw.length - 1];
	document.getElementById('current-temp').textContent = (latest.temp !== null && latest.temp !== undefined) ? latest.temp.toFixed(2) : '0.00';
	document.getElementById('current-rh').textContent = (latest.rh !== null && latest.rh !== undefined) ? latest.rh.toFixed(2) : '0.00';
	document.getElementById('current-lux').textContent = (latest.lux !== null && latest.lux !== undefined) ? latest.lux.toFixed(2) : '0.00';
	document.getElementById('current-irradiance').textContent = (latest.irradiance !== null && latest.irradiance !== undefined) ? latest.irradiance.toFixed(3) : '0.000';
	// Display database time as-is (no timezone conversion)
	const timeStr = latest.time.replace('T', ' ').replace(/\.\d+/, '').split('+')[0].split('Z')[0];
	document.getElementById('latest-time').textContent = timeStr;
	
	// Update mode display
	const modeDisplay = document.getElementById('mode-display');
	const refreshStatus = document.getElementById('refresh-status');
	if (currentMode === 'range') {
		modeDisplay.textContent = `Range (${selectedStartDate} to ${selectedEndDate})`;
		refreshStatus.textContent = 'Paused';
	} else if (currentMode === 'historical') {
		modeDisplay.textContent = `Historical (${selectedDate})`;
		refreshStatus.textContent = 'Paused';
	} else {
		modeDisplay.textContent = 'Live';
		refreshStatus.textContent = '5s';
	}
}

function updateTable(raw) {
	const tbody = document.getElementById('data-tbody');
	tbody.innerHTML = '';
	// Show last 50 readings (most recent first)
	const subset = raw.slice(-50).reverse();
	for (const r of subset) {
		const tr = document.createElement('tr');
		const temp = (r.temp !== null && r.temp !== undefined) ? r.temp.toFixed(2) : '0.00';
		const rh = (r.rh !== null && r.rh !== undefined) ? r.rh.toFixed(2) : '0.00';
		const lux = (r.lux !== null && r.lux !== undefined) ? r.lux.toFixed(2) : '0.00';
		const irradiance = (r.irradiance !== null && r.irradiance !== undefined) ? r.irradiance.toFixed(3) : '0.000';
		// Display database time as-is (no timezone conversion)
		const timeStr = r.time.replace('T', ' ').replace(/\.\d+/, '').split('+')[0].split('Z')[0];
		tr.innerHTML = `
			<td>${timeStr}</td>
			<td>${temp}</td>
			<td>${rh}</td>
			<td>${lux}</td>
			<td>${irradiance}</td>
		`;
		tbody.appendChild(tr);
	}
}

async function loadAvailableDates() {
	try {
		const resp = await fetch('/api/dates');
		const data = await resp.json();
		
		if (data.date_range && data.date_range.max_date) {
			// Set max date for date picker
			const picker = document.getElementById('date-picker');
			picker.max = data.date_range.max_date;
			if (data.date_range.min_date) {
				picker.min = data.date_range.min_date;
			}
		}
	} catch (e) {
		console.error('Failed to load date range:', e);
	}
}

function setupEventListeners() {
	// Time window buttons
	document.querySelectorAll('.time-btn').forEach(btn => {
		btn.addEventListener('click', (e) => {
			// Remove active from all buttons
			document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
			// Add active to clicked button
			e.target.classList.add('active');
			
			// Switch to live mode
			currentMode = 'live';
			currentWindow = parseInt(e.target.dataset.minutes, 10);
			selectedDate = null;
			
			// Restart auto-refresh
			startAutoRefresh();
			refresh();
		});
	});
	
	// Load day button
	document.getElementById('load-day-btn').addEventListener('click', () => {
		const datePicker = document.getElementById('date-picker');
		if (!datePicker.value) {
			alert('Please select a date first');
			return;
		}
		
		// Switch to historical mode
		currentMode = 'historical';
		selectedDate = datePicker.value;
		selectedStartDate = null;
		selectedEndDate = null;
		
		// Stop auto-refresh for historical data
		stopAutoRefresh();
		refresh();
	});
	
	// Load range button
	document.getElementById('load-range-btn').addEventListener('click', () => {
		const startPicker = document.getElementById('start-date-picker');
		const endPicker = document.getElementById('end-date-picker');
		
		if (!startPicker.value || !endPicker.value) {
			alert('Please select both start and end dates');
			return;
		}
		
		if (startPicker.value > endPicker.value) {
			alert('Start date must be before or equal to end date');
			return;
		}
		
		// Switch to range mode
		currentMode = 'range';
		selectedStartDate = startPicker.value;
		selectedEndDate = endPicker.value;
		selectedDate = null;
		
		// Stop auto-refresh for historical data
		stopAutoRefresh();
		refresh();
	});
	
	// Today button
	document.getElementById('today-btn').addEventListener('click', () => {
		// Switch to live mode
		currentMode = 'live';
		selectedDate = null;
		selectedStartDate = null;
		selectedEndDate = null;
		
		// Clear date pickers
		document.getElementById('date-picker').value = '';
		document.getElementById('start-date-picker').value = '';
		document.getElementById('end-date-picker').value = '';
		
		// Restart auto-refresh
		startAutoRefresh();
		refresh();
	});
	
	// CSV Export radio buttons - enable/disable date inputs
	document.querySelectorAll('input[name="export-type"]').forEach(radio => {
		radio.addEventListener('change', (e) => {
			const singleDate = document.getElementById('export-single-date');
			const startDate = document.getElementById('export-start-date');
			const endDate = document.getElementById('export-end-date');
			
			// Disable all date inputs first
			singleDate.disabled = true;
			startDate.disabled = true;
			endDate.disabled = true;
			
			// Enable based on selection
			if (e.target.value === 'single-date') {
				singleDate.disabled = false;
			} else if (e.target.value === 'date-range') {
				startDate.disabled = false;
				endDate.disabled = false;
			}
		});
	});
	
	// CSV Export button
	document.getElementById('export-csv-btn').addEventListener('click', () => {
		const exportType = document.querySelector('input[name="export-type"]:checked').value;
		let url = '/api/export/csv?';
		
		if (exportType === 'last24h') {
			// Default - no params needed
			url = '/api/export/csv';
		} else if (exportType === 'single-date') {
			const date = document.getElementById('export-single-date').value;
			if (!date) {
				alert('Please select a date');
				return;
			}
			url += `start_date=${date}`;
		} else if (exportType === 'date-range') {
			const startDate = document.getElementById('export-start-date').value;
			const endDate = document.getElementById('export-end-date').value;
			if (!startDate || !endDate) {
				alert('Please select both start and end dates');
				return;
			}
			if (startDate > endDate) {
				alert('Start date must be before end date');
				return;
			}
			url += `start_date=${startDate}&end_date=${endDate}`;
		} else if (exportType === 'all') {
			url += 'all=true';
		}
		
		// Trigger download
		window.location.href = url;
	});
}

function startAutoRefresh() {
	stopAutoRefresh();
	refreshInterval = setInterval(refresh, 5000);
	// Also check system health every 10 seconds
	setInterval(updateSystemStatus, 10000);
}

function stopAutoRefresh() {
	if (refreshInterval) {
		clearInterval(refreshInterval);
		refreshInterval = null;
	}
}

// System Status Functions
async function updateSystemStatus() {
	try {
		const resp = await fetch('/api/health');
		const health = await resp.json();
		
		const statusDot = document.getElementById('status-dot');
		const statusText = document.getElementById('status-text');
		
		// Determine status based on health metrics
		let status = 'active';
		let statusLabel = 'Active';
		
		if (!health.tcp_server.listening) {
			status = 'inactive';
			statusLabel = 'TCP Server Down';
		} else if (health.tcp_server.seconds_since_last_data > 300) {
			// No data for 5+ minutes
			status = 'warning';
			statusLabel = 'No Recent Data';
		} else if (health.memory.count === 0) {
			status = 'warning';
			statusLabel = 'No Data';
		}
		
		// Update indicator
		statusDot.className = `status-dot ${status}`;
		statusText.textContent = statusLabel;
		
	} catch (err) {
		console.error('Failed to fetch health status:', err);
		const statusDot = document.getElementById('status-dot');
		const statusText = document.getElementById('status-text');
		statusDot.className = 'status-dot inactive';
		statusText.textContent = 'Connection Error';
	}
}

async function showHealthDetails() {
	const modal = document.getElementById('health-modal');
	const detailsDiv = document.getElementById('health-details');
	
	modal.classList.add('show');
	detailsDiv.innerHTML = '<div class="loading">Loading health data...</div>';
	
	try {
		const resp = await fetch('/api/health');
		const health = await resp.json();
		
		const uptime = formatUptime(health.uptime_seconds);
		const lastData = health.tcp_server.seconds_since_last_data !== null
			? formatTimeSince(health.tcp_server.seconds_since_last_data)
			: 'Never';
		
		detailsDiv.innerHTML = `
			<div class="health-metric ${health.tcp_server.listening ? '' : 'error'}">
				<div class="health-metric-label">TCP Server Status</div>
				<div class="health-metric-value">${health.tcp_server.listening ? '🟢 Listening' : '🔴 Not Listening'}</div>
				<div class="health-metric-detail">Port: ${health.tcp_server.port} | Heartbeat: ${health.tcp_server.heartbeat_age}s ago</div>
			</div>
			
			<div class="health-metric">
				<div class="health-metric-label">Last Data Received</div>
				<div class="health-metric-value">${lastData}</div>
				${health.tcp_server.last_connection_time ? 
					`<div class="health-metric-detail">Last connection: ${new Date(health.tcp_server.last_connection_time).toLocaleString()}</div>` : ''}
			</div>
			
			<div class="health-metric">
				<div class="health-metric-label">Server Uptime</div>
				<div class="health-metric-value">${uptime}</div>
				<div class="health-metric-detail">Started: ${new Date(health.start_time).toLocaleString()}</div>
			</div>
			
			<div class="health-metric">
				<div class="health-metric-label">In-Memory Buffer</div>
				<div class="health-metric-value">${health.memory.count} readings</div>
				<div class="health-metric-detail">Max capacity: ${health.memory.max_size}</div>
			</div>
			
			<div class="health-metric">
				<div class="health-metric-label">Database</div>
				<div class="health-metric-value">${health.database.total_readings.toLocaleString()} total readings</div>
				${health.database.date_range ? 
					`<div class="health-metric-detail">Range: ${health.database.date_range.min_date} to ${health.database.date_range.max_date}</div>` : ''}
			</div>
			
			<div class="health-metric ${health.tcp_server.connections_received === 0 ? 'warning' : ''}">
				<div class="health-metric-label">Connection Stats</div>
				<div class="health-metric-value">${health.tcp_server.connections_received} connections received</div>
				<div class="health-metric-detail">Messages: ${health.tcp_server.messages_parsed} valid, ${health.tcp_server.invalid_messages} invalid</div>
			</div>
		`;
	} catch (err) {
		detailsDiv.innerHTML = `
			<div class="health-metric error">
				<div class="health-metric-label">Error</div>
				<div class="health-metric-value">Failed to load health data</div>
				<div class="health-metric-detail">${err.message}</div>
			</div>
		`;
	}
}

function closeHealthModal(event) {
	const modal = document.getElementById('health-modal');
	modal.classList.remove('show');
}

function formatUptime(seconds) {
	const days = Math.floor(seconds / 86400);
	const hours = Math.floor((seconds % 86400) / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	
	if (days > 0) return `${days}d ${hours}h ${minutes}m`;
	if (hours > 0) return `${hours}h ${minutes}m`;
	return `${minutes}m`;
}

function formatTimeSince(seconds) {
	if (seconds < 60) return `${Math.floor(seconds)}s ago`;
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
	if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
	return `${Math.floor(seconds / 86400)}d ago`;
}

// Fullscreen Chart Functionality
let fullscreenChart = null;
let currentFullscreenType = null;

const chartConfigs = {
	temp: { label: 'Temperature', color: '#ff7369', yTitle: '°C', field: 'temp' },
	rh: { label: 'Relative Humidity', color: '#4ecdc4', yTitle: '%', field: 'rh' },
	lux: { label: 'Light (Lux)', color: '#ffd166', yTitle: 'lux', field: 'lux' },
	irradiance: { label: 'Solar Irradiance', color: '#a78bfa', yTitle: 'W/m²', field: 'irradiance' }
};

async function toggleFullscreen(chartType) {
	const modal = document.getElementById('chart-fullscreen-modal');
	const title = document.getElementById('fullscreen-chart-title');
	const canvas = document.getElementById('chart-fullscreen');
	
	modal.classList.add('show');
	currentFullscreenType = chartType;
	
	const config = chartConfigs[chartType];
	title.textContent = config.label;
	
	// Destroy existing chart if any
	if (fullscreenChart) {
		fullscreenChart.destroy();
	}
	
	// Create new fullscreen chart
	const ctx = canvas.getContext('2d');
	fullscreenChart = makeChart(ctx, config.label, config.color, config.yTitle, true);
	
	// Load data
	try {
		const raw = await fetchData();
		const data = buildSeries(raw, config.field);
		fullscreenChart.data.datasets[0].data = data;
		updateYScale(fullscreenChart, data);
		fullscreenChart.update();
	} catch (e) {
		console.error('Error loading fullscreen chart data:', e);
	}
}

function closeFullscreenChart(event) {
	if (event && event.target.className !== 'chart-fullscreen-modal') {
		return;
	}
	
	const modal = document.getElementById('chart-fullscreen-modal');
	modal.classList.remove('show');
	
	if (fullscreenChart) {
		fullscreenChart.destroy();
		fullscreenChart = null;
	}
	
	currentFullscreenType = null;
}

function resetZoom() {
	if (fullscreenChart) {
		fullscreenChart.resetZoom();
	}
}

// Update fullscreen chart data (called from main refresh)
async function updateFullscreenChart() {
	if (currentFullscreenType && fullscreenChart) {
		try {
			const raw = await fetchData();
			const config = chartConfigs[currentFullscreenType];
			const data = buildSeries(raw, config.field);
			fullscreenChart.data.datasets[0].data = data;
			updateYScale(fullscreenChart, data);
			fullscreenChart.update();
		} catch (e) {
			console.error('Error updating fullscreen chart:', e);
		}
	}
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
	if (e.key === 'Escape' && currentFullscreenType) {
		closeFullscreenChart();
	}
	if (e.key === 'r' && currentFullscreenType) {
		resetZoom();
	}
});

window.addEventListener('DOMContentLoaded', () => {
	setupEventListeners();
	loadAvailableDates();
	updateSystemStatus(); // Initial status check
	startAutoRefresh();
	refresh();
});


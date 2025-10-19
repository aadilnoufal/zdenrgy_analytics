let charts = {};
let currentWindow = 60; // minutes
let currentMode = 'live'; // 'live' or 'historical'
let selectedDate = null;
let refreshInterval = null;
const GAP_MS = 2 * 60 * 1000; // break line if gap > 2 minutes

async function fetchData() {
	let url;
	if (currentMode === 'historical' && selectedDate) {
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
			fill: false,
			tension: .25,
			borderColor: color,
			pointRadius: 0,
			borderWidth: 2,
			spanGaps: false,
			normalized: true
		}]},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			animation: false,
			interaction: { mode: 'nearest', intersect: false },
			scales: {
				x: {
					type: 'time',
					time: { tooltipFormat: 'yyyy-MM-dd HH:mm:ss' },
					ticks: { color: '#9aa4b1', maxRotation: 0 },
					grid: { color: '#2a3039' }
				},
				y: {
					ticks: { color: '#9aa4b1' },
					grid: { color: '#2a3039' },
					title: { display: true, text: yTitle, color: '#9aa4b1' },
					suggestedMin: undefined,
					suggestedMax: undefined
				}
			},
			plugins: {
				legend: { labels: { color: '#d0d7e1' } },
				tooltip: { mode: 'index', intersect: false }
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
	document.getElementById('current-temp').textContent = latest.temp.toFixed(2);
	document.getElementById('current-rh').textContent = latest.rh.toFixed(2);
	document.getElementById('current-lux').textContent = latest.lux.toFixed(2);
	document.getElementById('current-irradiance').textContent = latest.irradiance.toFixed(3);
	document.getElementById('latest-time').textContent = new Date(latest.time).toLocaleString();
	
	// Update mode display
	const modeDisplay = document.getElementById('mode-display');
	const refreshStatus = document.getElementById('refresh-status');
	if (currentMode === 'historical') {
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
		
		// Stop auto-refresh for historical data
		stopAutoRefresh();
		refresh();
	});
	
	// Today button
	document.getElementById('today-btn').addEventListener('click', () => {
		// Switch to live mode
		currentMode = 'live';
		selectedDate = null;
		
		// Clear date picker
		document.getElementById('date-picker').value = '';
		
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
}

function stopAutoRefresh() {
	if (refreshInterval) {
		clearInterval(refreshInterval);
		refreshInterval = null;
	}
}

window.addEventListener('DOMContentLoaded', () => {
	setupEventListeners();
	loadAvailableDates();
	startAutoRefresh();
	refresh();
});


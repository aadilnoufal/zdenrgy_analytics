// Battery KPI page JavaScript

let batteryChart = null;

async function fetchBatteryKPIs() {
    try {
        const response = await fetch('/api/kpi');
        const data = await response.json();
        
        if (data.kpis) {
            // Update battery SOC
            if (data.kpis.battery_soc) {
                const soc = data.kpis.battery_soc;
                document.getElementById('battery-soc').textContent = soc.value.toFixed(1);
                
                // Calculate available energy from metadata
                if (soc.metadata && soc.metadata.available_energy) {
                    document.getElementById('battery-energy').textContent = soc.metadata.available_energy.toFixed(2);
                }
                
                if (soc.metadata && soc.metadata.capacity) {
                    document.getElementById('battery-capacity').textContent = soc.metadata.capacity.toFixed(1);
                }
            }
            
            // Update status badge
            const status = document.getElementById('battery-status');
            if (data.kpis.battery_soc && data.kpis.battery_soc.value > 0) {
                status.textContent = 'Online';
                status.className = 'status-badge online';
            } else {
                status.textContent = 'No Data';
                status.className = 'status-badge unknown';
            }
            
            // Update metrics table
            updateBatteryMetrics(data.kpis);
        }
    } catch (error) {
        console.error('Error fetching battery KPIs:', error);
    }
}

function updateBatteryMetrics(kpis) {
    const tbody = document.getElementById('battery-metrics');
    const metrics = [];
    
    if (kpis.battery_soc) {
        const soc = kpis.battery_soc.value;
        let status = 'Normal';
        if (soc < 20) status = 'Low';
        if (soc > 80) status = 'High';
        
        metrics.push({
            name: 'State of Charge',
            value: soc.toFixed(1),
            unit: '%',
            status: status
        });
        
        if (kpis.battery_soc.metadata) {
            metrics.push({
                name: 'Available Energy',
                value: kpis.battery_soc.metadata.available_energy?.toFixed(2) || '—',
                unit: 'kWh',
                status: 'Normal'
            });
            
            metrics.push({
                name: 'Total Capacity',
                value: kpis.battery_soc.metadata.capacity?.toFixed(1) || '—',
                unit: 'kWh',
                status: 'Normal'
            });
        }
    }
    
    tbody.innerHTML = metrics.map(m => `
        <tr>
            <td>${m.name}</td>
            <td>${m.value}</td>
            <td>${m.unit}</td>
            <td><span class="pill">${m.status}</span></td>
        </tr>
    `).join('');
}

async function updateBatteryChart() {
    // For now, show simulated data
    // In production, fetch historical battery data
    if (!batteryChart) {
        const ctx = document.getElementById('chart-battery-soc');
        batteryChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Battery SOC',
                    data: [],
                    borderColor: '#4ecdc4',
                    backgroundColor: 'rgba(78, 205, 196, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: { tooltipFormat: 'HH:mm:ss' },
                        ticks: { color: '#9aa4b1' },
                        grid: { color: '#2a3039' }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        ticks: { color: '#9aa4b1' },
                        grid: { color: '#2a3039' },
                        title: { display: true, text: 'SOC (%)', color: '#9aa4b1' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#d0d7e1' } }
                }
            }
        });
    }
    
    // Update chart with current data
    const response = await fetch('/api/kpi/battery_soc');
    const data = await response.json();
    
    if (data.value !== undefined) {
        batteryChart.data.datasets[0].data.push({
            x: new Date(),
            y: data.value
        });
        
        // Keep last 50 points
        if (batteryChart.data.datasets[0].data.length > 50) {
            batteryChart.data.datasets[0].data.shift();
        }
        
        batteryChart.update('none');
    }
}

// Refresh every 5 seconds
setInterval(() => {
    fetchBatteryKPIs();
    updateBatteryChart();
}, 5000);

// Initial load
window.addEventListener('DOMContentLoaded', () => {
    fetchBatteryKPIs();
    updateBatteryChart();
});

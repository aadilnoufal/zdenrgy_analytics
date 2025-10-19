// Inverter KPI page JavaScript

let inverterChart = null;

async function fetchInverterKPIs() {
    try {
        const response = await fetch('/api/kpi');
        const data = await response.json();
        
        if (data.kpis) {
            // Calculate inverter metrics from available data
            const solarGen = data.kpis.solar_generation?.value || 0;
            
            // DC Power (from solar generation)
            document.getElementById('inverter-dc-power').textContent = solarGen.toFixed(3);
            
            // AC Power (assume 95% efficiency for now)
            const acPower = solarGen * 0.95;
            document.getElementById('inverter-ac-power').textContent = acPower.toFixed(3);
            
            // Efficiency
            const efficiency = solarGen > 0 ? 95.0 : 0;
            document.getElementById('inverter-efficiency').textContent = efficiency.toFixed(1);
            
            // Status
            const status = document.getElementById('inverter-status');
            if (solarGen > 0) {
                status.textContent = 'Active';
                status.className = 'status-badge online';
            } else {
                status.textContent = 'Standby';
                status.className = 'status-badge unknown';
            }
            
            updateInverterMetrics(data.kpis);
        }
    } catch (error) {
        console.error('Error fetching inverter KPIs:', error);
    }
}

function updateInverterMetrics(kpis) {
    const tbody = document.getElementById('inverter-metrics');
    const solarGen = kpis.solar_generation?.value || 0;
    
    const metrics = [
        {
            name: 'DC Input Voltage',
            value: '—',
            unit: 'V',
            status: 'Not Available'
        },
        {
            name: 'AC Output Voltage',
            value: '—',
            unit: 'V',
            status: 'Not Available'
        },
        {
            name: 'Conversion Efficiency',
            value: solarGen > 0 ? '95.0' : '0.0',
            unit: '%',
            status: solarGen > 0 ? 'Normal' : 'Standby'
        },
        {
            name: 'Operating Temperature',
            value: kpis.temperature?.value.toFixed(1) || '—',
            unit: '°C',
            status: 'Normal'
        }
    ];
    
    tbody.innerHTML = metrics.map(m => `
        <tr>
            <td>${m.name}</td>
            <td>${m.value}</td>
            <td>${m.unit}</td>
            <td><span class="pill">${m.status}</span></td>
        </tr>
    `).join('');
}

async function updateInverterChart() {
    if (!inverterChart) {
        const ctx = document.getElementById('chart-inverter-efficiency');
        inverterChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Efficiency',
                    data: [],
                    borderColor: '#ffd166',
                    backgroundColor: 'rgba(255, 209, 102, 0.1)',
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
                        title: { display: true, text: 'Efficiency (%)', color: '#9aa4b1' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#d0d7e1' } }
                }
            }
        });
    }
    
    const response = await fetch('/api/kpi/solar_generation');
    const data = await response.json();
    
    const efficiency = data.value > 0 ? 95.0 : 0;
    
    inverterChart.data.datasets[0].data.push({
        x: new Date(),
        y: efficiency
    });
    
    if (inverterChart.data.datasets[0].data.length > 50) {
        inverterChart.data.datasets[0].data.shift();
    }
    
    inverterChart.update('none');
}

setInterval(() => {
    fetchInverterKPIs();
    updateInverterChart();
}, 5000);

window.addEventListener('DOMContentLoaded', () => {
    fetchInverterKPIs();
    updateInverterChart();
});

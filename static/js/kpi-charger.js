// DC Charger KPI page JavaScript

let chargerChart = null;

async function fetchChargerKPIs() {
    try {
        const response = await fetch('/api/kpi');
        const data = await response.json();
        
        if (data.kpis) {
            // Charger metrics (placeholder data until real source available)
            document.getElementById('charger-power').textContent = '0.0';
            document.getElementById('charger-sessions').textContent = '0';
            document.getElementById('charger-efficiency').textContent = '95.0';
            document.getElementById('charger-daily-energy').textContent = '0.0';
            
            // Status
            const status = document.getElementById('charger-status');
            status.textContent = 'Ready';
            status.className = 'status-badge unknown';
            
            updateChargerMetrics(data.kpis);
        }
    } catch (error) {
        console.error('Error fetching charger KPIs:', error);
    }
}

function updateChargerMetrics(kpis) {
    const tbody = document.getElementById('charger-metrics');
    
    const metrics = [
        {
            name: 'Charging Power',
            value: '0.0',
            unit: 'kW',
            status: 'Not Available'
        },
        {
            name: 'Active Sessions',
            value: '0',
            unit: '',
            status: 'Not Available'
        },
        {
            name: 'Charger Efficiency',
            value: '95.0',
            unit: '%',
            status: 'Not Available'
        },
        {
            name: 'Daily Energy Delivered',
            value: '0.0',
            unit: 'kWh',
            status: 'Not Available'
        },
        {
            name: 'Connector Status',
            value: 'Available',
            unit: '',
            status: 'Ready'
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

async function updateChargerChart() {
    if (!chargerChart) {
        const ctx = document.getElementById('chart-charger-power');
        chargerChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Charging Power',
                    data: [],
                    borderColor: '#a78bfa',
                    backgroundColor: 'rgba(167, 139, 250, 0.1)',
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
                        ticks: { color: '#9aa4b1' },
                        grid: { color: '#2a3039' },
                        title: { display: true, text: 'Power (kW)', color: '#9aa4b1' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#d0d7e1' } }
                }
            }
        });
    }
    
    // Placeholder data
    chargerChart.data.datasets[0].data.push({
        x: new Date(),
        y: 0
    });
    
    if (chargerChart.data.datasets[0].data.length > 50) {
        chargerChart.data.datasets[0].data.shift();
    }
    
    chargerChart.update('none');
}

setInterval(() => {
    fetchChargerKPIs();
    updateChargerChart();
}, 5000);

window.addEventListener('DOMContentLoaded', () => {
    fetchChargerKPIs();
    updateChargerChart();
});

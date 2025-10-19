// Solar Array KPI page JavaScript

let irradianceChart = null;
let generationChart = null;

async function fetchSolarKPIs() {
    try {
        const response = await fetch('/api/kpi');
        const data = await response.json();
        
        if (data.kpis) {
            // Solar generation
            if (data.kpis.solar_generation) {
                document.getElementById('solar-generation').textContent = 
                    data.kpis.solar_generation.value.toFixed(3);
            }
            
            // Daily energy
            if (data.kpis.daily_solar_energy) {
                document.getElementById('solar-daily-energy').textContent = 
                    data.kpis.daily_solar_energy.value.toFixed(2);
            }
            
            // Cost savings
            if (data.kpis.daily_cost_savings) {
                document.getElementById('solar-savings').textContent = 
                    data.kpis.daily_cost_savings.value.toFixed(2);
            }
            
            // Carbon offset
            if (data.kpis.daily_carbon_offset) {
                document.getElementById('solar-carbon').textContent = 
                    data.kpis.daily_carbon_offset.value.toFixed(2);
                
                // Calculate trees equivalent (1 tree absorbs ~21 kg CO2 per year, so ~0.058 kg/day)
                const trees = (data.kpis.daily_carbon_offset.value / 0.058).toFixed(1);
                document.getElementById('solar-trees').textContent = trees;
            }
            
            // Performance ratio (actual / theoretical)
            if (data.kpis.solar_generation && data.kpis.solar_generation.metadata) {
                const metadata = data.kpis.solar_generation.metadata;
                const theoretical = (metadata.irradiance * metadata.panel_area * metadata.efficiency / 100) / 1000;
                const actual = data.kpis.solar_generation.value;
                const ratio = theoretical > 0 ? (actual / theoretical * 100) : 0;
                document.getElementById('solar-performance').textContent = ratio.toFixed(1);
                
                // Update irradiance pill
                document.getElementById('solar-irradiance-pill').textContent = 
                    metadata.irradiance.toFixed(1);
            }
            
            // Update configuration table
            updateSolarConfig(data.kpis);
        }
    } catch (error) {
        console.error('Error fetching solar KPIs:', error);
    }
}

function updateSolarConfig(kpis) {
    const tbody = document.getElementById('solar-config');
    
    const config = [];
    
    if (kpis.solar_generation && kpis.solar_generation.metadata) {
        const m = kpis.solar_generation.metadata;
        config.push(
            { param: 'Panel Area', value: m.panel_area.toFixed(1), unit: 'm²' },
            { param: 'Panel Efficiency', value: m.efficiency.toFixed(1), unit: '%' },
            { param: 'System Losses', value: m.losses.toFixed(1), unit: '%' },
            { param: 'Current Irradiance', value: m.irradiance.toFixed(2), unit: 'W/m²' }
        );
    }
    
    if (kpis.temperature) {
        config.push({
            param: 'Ambient Temperature',
            value: kpis.temperature.value.toFixed(1),
            unit: '°C'
        });
    }
    
    tbody.innerHTML = config.map(c => `
        <tr>
            <td>${c.param}</td>
            <td>${c.value}</td>
            <td>${c.unit}</td>
        </tr>
    `).join('');
}

async function updateSolarCharts() {
    try {
        const response = await fetch('/api/data?limit=50&minutes=60');
        const data = await response.json();
        
        // Initialize charts if needed
        if (!irradianceChart) {
            const ctx1 = document.getElementById('chart-irradiance');
            irradianceChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Irradiance',
                        data: [],
                        borderColor: '#ffd166',
                        backgroundColor: 'rgba(255, 209, 102, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: { tooltipFormat: 'HH:mm' },
                            ticks: { color: '#9aa4b1' },
                            grid: { color: '#2a3039' }
                        },
                        y: {
                            ticks: { color: '#9aa4b1' },
                            grid: { color: '#2a3039' },
                            title: { display: true, text: 'W/m²', color: '#9aa4b1' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#d0d7e1' } }
                    }
                }
            });
        }
        
        if (!generationChart) {
            const ctx2 = document.getElementById('chart-generation');
            generationChart = new Chart(ctx2, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Generation',
                        data: [],
                        borderColor: '#ff7369',
                        backgroundColor: 'rgba(255, 115, 105, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: { tooltipFormat: 'HH:mm' },
                            ticks: { color: '#9aa4b1' },
                            grid: { color: '#2a3039' }
                        },
                        y: {
                            ticks: { color: '#9aa4b1' },
                            grid: { color: '#2a3039' },
                            title: { display: true, text: 'kW', color: '#9aa4b1' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#d0d7e1' } }
                    }
                }
            });
        }
        
        // Update chart data
        const irradianceData = data.map(d => ({
            x: new Date(d.time),
            y: d.irradiance || (d.lux / 127.0)
        }));
        
        const generationData = data.map(d => {
            const irradiance = d.irradiance || (d.lux / 127.0);
            // Simple generation calculation: irradiance * area * efficiency * (1 - losses) / 1000
            // Using defaults: 100 m², 20%, 15% losses
            return {
                x: new Date(d.time),
                y: (irradiance * 100 * 0.20 * 0.85) / 1000
            };
        });
        
        irradianceChart.data.datasets[0].data = irradianceData;
        generationChart.data.datasets[0].data = generationData;
        
        irradianceChart.update('none');
        generationChart.update('none');
    } catch (error) {
        console.error('Error updating solar charts:', error);
    }
}

setInterval(() => {
    fetchSolarKPIs();
    updateSolarCharts();
}, 5000);

window.addEventListener('DOMContentLoaded', () => {
    fetchSolarKPIs();
    updateSolarCharts();
});

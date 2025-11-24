// Solar Array KPI page JavaScript

let irradianceChart = null;
let generationChart = null;
let currentIrradiance = 0; // Store current irradiance for calculations

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
                currentIrradiance = metadata.irradiance; // Store for use elsewhere
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

async function fetchCleaningStats() {
    try {
        const response = await fetch('/api/cleaning/stats');
        const data = await response.json();
        
        const statusDiv = document.getElementById('cleaning-status');
        const degradation = data.degradation;
        
        if (!degradation) {
            statusDiv.innerHTML = '<div style="text-align: center; opacity: 0.6;">Unable to load cleaning data</div>';
            return;
        }
        
        // Determine status color
        let statusClass = 'status-good';
        let statusIcon = '✅';
        if (!degradation.has_baseline) {
            statusClass = 'status-info';
            statusIcon = '📊';
        } else if (degradation.degradation_percent >= 15) {
            statusClass = 'status-critical';
            statusIcon = '⚠️';
        } else if (degradation.degradation_percent >= 10) {
            statusClass = 'status-warning';
            statusIcon = '⚡';
        } else if (degradation.degradation_percent >= 5) {
            statusClass = 'status-monitoring';
            statusIcon = '📊';
        }
        
        let statusHTML = `
            <div class="cleaning-metric ${statusClass}">
                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                    <div style="font-size: 3rem;">${statusIcon}</div>
                    <div style="flex: 1;">
                        <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.3rem;">
                            ${degradation.has_baseline ? 'Performance Tracking' : 'No Baseline Set'}
                        </div>
                        <div style="font-size: 0.9rem; opacity: 0.8;">
                            ${degradation.recommendation || degradation.message}
                        </div>
                    </div>
                </div>
        `;
        
        if (degradation.has_baseline) {
            statusHTML += `
                <div class="cleaning-stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Days Since Cleaning</div>
                        <div class="stat-value">${degradation.days_since_cleaning}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Performance Loss</div>
                        <div class="stat-value">${degradation.degradation_percent.toFixed(1)}%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Current Ratio</div>
                        <div class="stat-value">${(degradation.current_ratio * 100).toFixed(1)}%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Baseline Ratio</div>
                        <div class="stat-value">${(degradation.baseline_ratio * 100).toFixed(1)}%</div>
                    </div>
                </div>
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a2f3a; font-size: 0.85rem; opacity: 0.7;">
                    Last cleaned: ${new Date(degradation.last_cleaning_date).toLocaleDateString('en-US', { 
                        year: 'numeric', month: 'short', day: 'numeric' 
                    })}
                </div>
            `;
        }
        
        statusHTML += '</div>';
        statusDiv.innerHTML = statusHTML;
        
        // Update history
        if (data.cleaning_history && data.cleaning_history.length > 0) {
            const historyTbody = document.getElementById('cleaning-history');
            historyTbody.innerHTML = data.cleaning_history.map(record => {
                const date = new Date(record.cleaning_date);
                const daysAgo = Math.floor((Date.now() - date) / (1000 * 60 * 60 * 24));
                return `
                    <tr>
                        <td>${date.toLocaleDateString()}</td>
                        <td>${daysAgo}</td>
                        <td>${(record.baseline_ratio * 100).toFixed(1)}%</td>
                        <td>${record.notes || '—'}</td>
                    </tr>
                `;
            }).join('');
        }
        
        // Show average interval if available
        if (data.average_interval_days) {
            const avgHTML = `
                <div style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.7;">
                    Average cleaning interval: ${data.average_interval_days} days
                    (Based on ${data.total_cleanings} cleanings)
                </div>
            `;
            document.getElementById('cleaning-history-section').insertAdjacentHTML('beforeend', avgHTML);
        }
        
    } catch (error) {
        console.error('Error fetching cleaning stats:', error);
        document.getElementById('cleaning-status').innerHTML = 
            '<div style="text-align: center; color: #ff7369;">Error loading cleaning data</div>';
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
        // Fetch real sensor data
        const response = await fetch('/api/data?window=60');
        const data = await response.json();
        const readings = data.readings || data;
        
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
        
        // Update chart data with REAL irradiance from dashboard
        const irradianceData = readings.map(d => ({
            x: new Date(d.time),
            y: d.irradiance || (d.lux / 127.0)
        }));
        
        // Calculate generation based on real irradiance
        const generationData = readings.map(d => {
            const irradiance = d.irradiance || (d.lux / 127.0);
            // Generation calculation: irradiance * area * efficiency * (1 - losses) / 1000
            // Using defaults from config: 100 m², 20%, 15% losses
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

// Record cleaning modal functions
function openCleaningModal() {
    const modal = document.getElementById('cleaning-modal');
    document.getElementById('cleaning-date').valueAsDate = new Date();
    modal.classList.add('show');
}

function closeCleaningModal(event) {
    if (event && event.target.id !== 'cleaning-modal') {
        return;
    }
    const modal = document.getElementById('cleaning-modal');
    modal.classList.remove('show');
}

async function submitCleaning(event) {
    event.preventDefault();
    
    const date = document.getElementById('cleaning-date').value;
    const notes = document.getElementById('cleaning-notes').value;
    
    try {
        const response = await fetch('/api/cleaning/record', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cleaning_date: date,
                notes: notes
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✅ Cleaning recorded successfully!');
            closeCleaningModal();
            fetchCleaningStats(); // Refresh stats
        } else {
            alert('⚠️ Error: ' + (result.error || 'Failed to record cleaning'));
        }
    } catch (error) {
        alert('⚠️ Error recording cleaning: ' + error.message);
    }
}

// Set up event listeners
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('record-cleaning-btn').addEventListener('click', openCleaningModal);
    document.getElementById('cleaning-form').addEventListener('submit', submitCleaning);
    
    // Keyboard shortcut
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeCleaningModal();
        }
    });
});

setInterval(() => {
    fetchSolarKPIs();
    updateSolarCharts();
    fetchCleaningStats();
}, 5000);

window.addEventListener('DOMContentLoaded', () => {
    fetchSolarKPIs();
    updateSolarCharts();
    fetchCleaningStats();
});

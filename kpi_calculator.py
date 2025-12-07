"""KPI calculation engine using configured parameters.

All KPI calculations use the DataProvider to fetch parameters,
making it easy to plug in different data sources without changing calculation logic.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from data_sources import DataProvider


@dataclass
class KPIResult:
    """Result of a KPI calculation"""
    name: str
    display_name: str
    value: float
    unit: str
    timestamp: str
    metadata: Dict[str, Any] = None


class KPICalculator:
    """
    Calculates various KPIs using the DataProvider.
    
    Usage:
        calculator = KPICalculator(data_provider)
        solar_generation = calculator.calculate_solar_generation()
        all_kpis = calculator.calculate_all()
    """
    
    def __init__(self, data_provider: DataProvider):
        """
        Initialize KPI calculator.
        
        Args:
            data_provider: DataProvider instance for fetching parameters
        """
        self.provider = data_provider
    
    # ==========================================================================
    # SOLAR ENERGY KPIs
    # ==========================================================================
    
    def calculate_solar_generation(self) -> KPIResult:
        """
        Calculate instantaneous solar power generation.
        
        Formula: P = Irradiance × Area × Efficiency × (1 - Losses/100)
        """
        # Fetch all required parameters using the data provider
        irradiance = self.provider.get("solar_irradiance")  # W/m²
        panel_area = self.provider.get("panel_area")  # m²
        efficiency = self.provider.get("panel_efficiency")  # %
        losses = self.provider.get("system_losses")  # %
        
        # Calculate generation in kW
        generation_kw = (
            irradiance 
            * panel_area 
            * (efficiency / 100) 
            * (1 - losses / 100)
        ) / 1000  # Convert W to kW
        
        return KPIResult(
            name="solar_generation",
            display_name="Solar Generation",
            value=round(generation_kw, 3),
            unit="kW",
            # Use Qatar time (UTC+3) for the timestamp
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat(),
            metadata={
                "irradiance": irradiance,
                "panel_area": panel_area,
                "efficiency": efficiency,
                "losses": losses,
            }
        )
    
    def calculate_daily_solar_energy(self, hours: int = 24) -> KPIResult:
        """
        Calculate expected daily solar energy generation.
        
        Note: Requires historical irradiance data or forecast
        """
        # For now, use simple estimation based on current generation
        current_gen = self.calculate_solar_generation()
        
        # Estimate daily energy (kWh) - simplified
        # In production, integrate historical data
        avg_sunlight_hours = 5.0  # Typical average
        daily_energy = current_gen.value * avg_sunlight_hours
        
        return KPIResult(
            name="daily_solar_energy",
            display_name="Est. Daily Solar Energy",
            value=round(daily_energy, 2),
            unit="kWh",
            # Use Qatar time (UTC+3)
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat(),
            metadata={"avg_sunlight_hours": avg_sunlight_hours}
        )
    
    # ==========================================================================
    # ENERGY CONSUMPTION KPIs
    # ==========================================================================
    
    def calculate_building_load(self) -> KPIResult:
        """Get current building energy consumption"""
        load = self.provider.get("building_load")  # kW
        
        return KPIResult(
            name="building_load",
            display_name="Building Load",
            value=round(load, 3),
            unit="kW",
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat()
        )
    
    def calculate_self_consumption_ratio(self) -> KPIResult:
        """
        Calculate ratio of solar energy consumed vs. generated.
        
        Formula: Self-consumption % = (Solar - Grid Export) / Solar × 100
        """
        solar_gen = self.calculate_solar_generation().value
        building_load = self.provider.get("building_load")
        
        if solar_gen <= 0:
            ratio = 0.0
        else:
            # Simplified: assume all consumption up to generation is self-consumed
            consumed = min(solar_gen, building_load)
            ratio = (consumed / solar_gen) * 100
        
        return KPIResult(
            name="self_consumption_ratio",
            display_name="Self-Consumption Ratio",
            value=round(ratio, 2),
            unit="%",
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat(),
            metadata={
                "solar_generation": solar_gen,
                "building_load": building_load,
            }
        )
    
    # ==========================================================================
    # BATTERY KPIs
    # ==========================================================================
    
    def calculate_battery_status(self) -> KPIResult:
        """Get battery state of charge"""
        soc = self.provider.get("battery_soc")  # %
        capacity = self.provider.get("battery_capacity")  # kWh
        available_energy = (soc / 100) * capacity
        
        return KPIResult(
            name="battery_soc",
            display_name="Battery State of Charge",
            value=round(soc, 1),
            unit="%",
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat(),
            metadata={
                "capacity": capacity,
                "available_energy": round(available_energy, 2),
            }
        )
    
    # ==========================================================================
    # FINANCIAL KPIs
    # ==========================================================================
    
    def calculate_energy_cost_savings(self, hours: int = 24) -> KPIResult:
        """
        Calculate daily cost savings from solar generation.
        
        Formula: Savings = Solar Energy × Electricity Tariff
        """
        daily_energy = self.calculate_daily_solar_energy().value  # kWh
        tariff = self.provider.get("electricity_tariff")  # $/kWh
        
        savings = daily_energy * tariff
        
        return KPIResult(
            name="daily_cost_savings",
            display_name="Est. Daily Cost Savings",
            value=round(savings, 2),
            unit="$",
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat(),
            metadata={
                "daily_energy": daily_energy,
                "tariff": tariff,
            }
        )
    
    def calculate_grid_export_revenue(self) -> KPIResult:
        """Calculate potential revenue from excess solar export"""
        solar_gen = self.calculate_solar_generation().value
        building_load = self.provider.get("building_load")
        feed_in_tariff = self.provider.get("feed_in_tariff")
        
        # Excess power exported to grid
        excess = max(0, solar_gen - building_load)
        
        # Hourly revenue (instantaneous)
        hourly_revenue = excess * feed_in_tariff
        
        return KPIResult(
            name="grid_export_revenue",
            display_name="Grid Export Revenue (hourly)",
            value=round(hourly_revenue, 3),
            unit="$/h",
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat(),
            metadata={
                "excess_power": round(excess, 3),
                "feed_in_tariff": feed_in_tariff,
            }
        )
    
    # ==========================================================================
    # ENVIRONMENTAL KPIs
    # ==========================================================================
    
    def calculate_carbon_offset(self) -> KPIResult:
        """
        Calculate CO₂ emissions avoided by using solar.
        
        Formula: Offset = Solar Energy × Grid Carbon Intensity
        """
        daily_energy = self.calculate_daily_solar_energy().value  # kWh
        carbon_intensity = self.provider.get("grid_carbon_intensity")  # kg CO₂/kWh
        
        offset = daily_energy * carbon_intensity
        
        return KPIResult(
            name="daily_carbon_offset",
            display_name="Est. Daily Carbon Offset",
            value=round(offset, 2),
            unit="kg CO₂",
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat(),
            metadata={
                "daily_energy": daily_energy,
                "carbon_intensity": carbon_intensity,
            }
        )
    
    # ==========================================================================
    # ENVIRONMENTAL MONITORING KPIs
    # ==========================================================================
    
    def calculate_temperature_status(self) -> KPIResult:
        """Get current temperature"""
        temp = self.provider.get("temperature")
        
        return KPIResult(
            name="temperature",
            display_name="Temperature",
            value=round(temp, 2),
            unit="°C",
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat()
        )
    
    def calculate_humidity_status(self) -> KPIResult:
        """Get current humidity"""
        humidity = self.provider.get("humidity")
        
        return KPIResult(
            name="humidity",
            display_name="Humidity",
            value=round(humidity, 2),
            unit="%",
            timestamp=(datetime.utcnow() + timedelta(hours=3)).isoformat()
        )
    
    # ==========================================================================
    # AGGREGATE CALCULATIONS
    # ==========================================================================
    
    def calculate_all(self) -> List[KPIResult]:
        """Calculate all available KPIs"""
        kpis = [
            self.calculate_solar_generation(),
            self.calculate_daily_solar_energy(),
            self.calculate_building_load(),
            self.calculate_self_consumption_ratio(),
            self.calculate_battery_status(),
            self.calculate_energy_cost_savings(),
            self.calculate_grid_export_revenue(),
            self.calculate_carbon_offset(),
            self.calculate_temperature_status(),
            self.calculate_humidity_status(),
        ]
        
        return kpis
    
    def calculate_summary(self) -> Dict[str, Any]:
        """Get a summary of key KPIs as a dictionary"""
        all_kpis = self.calculate_all()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "kpis": {
                kpi.name: {
                    "value": kpi.value,
                    "unit": kpi.unit,
                    "display_name": kpi.display_name,
                    "metadata": kpi.metadata,
                }
                for kpi in all_kpis
            }
        }


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


def create_kpi_calculator(data_provider: DataProvider) -> KPICalculator:
    """
    Create a KPI calculator instance.
    
    Args:
        data_provider: DataProvider instance
        
    Returns:
        KPICalculator instance
    """
    return KPICalculator(data_provider)

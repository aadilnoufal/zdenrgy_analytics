"""
Example usage of the pluggable parameter system.

This demonstrates how easy it is to use parameters and calculate KPIs.
"""

from data_sources import create_data_provider
from kpi_calculator import create_kpi_calculator
from config import update_manual_config


def example_basic_usage(weather_data):
    """Basic parameter fetching"""
    print("=== Basic Parameter Usage ===\n")
    
    # Create data provider
    provider = create_data_provider(weather_data)
    
    # Get individual parameters
    irradiance = provider.get("solar_irradiance")
    temperature = provider.get("temperature")
    humidity = provider.get("humidity")
    panel_area = provider.get("panel_area")
    
    print(f"Solar Irradiance: {irradiance} W/m²")
    print(f"Temperature: {temperature} °C")
    print(f"Humidity: {humidity} %")
    print(f"Panel Area: {panel_area} m²")
    print()


def example_multiple_parameters(weather_data):
    """Fetch multiple parameters at once"""
    print("=== Fetching Multiple Parameters ===\n")
    
    provider = create_data_provider(weather_data)
    
    # Get multiple parameters in one call
    params = provider.get_multiple([
        "solar_irradiance",
        "temperature",
        "humidity",
        "panel_area",
        "panel_efficiency",
        "electricity_tariff"
    ])
    
    for name, value in params.items():
        print(f"{name}: {value}")
    print()


def example_kpi_calculations(weather_data):
    """Calculate KPIs"""
    print("=== KPI Calculations ===\n")
    
    # Setup
    provider = create_data_provider(weather_data)
    calculator = create_kpi_calculator(provider)
    
    # Calculate individual KPIs
    solar_gen = calculator.calculate_solar_generation()
    print(f"{solar_gen.display_name}: {solar_gen.value} {solar_gen.unit}")
    print(f"  Metadata: {solar_gen.metadata}\n")
    
    savings = calculator.calculate_energy_cost_savings()
    print(f"{savings.display_name}: ${savings.value}")
    print(f"  Metadata: {savings.metadata}\n")
    
    carbon = calculator.calculate_carbon_offset()
    print(f"{carbon.display_name}: {carbon.value} {carbon.unit}\n")


def example_all_kpis(weather_data):
    """Get all KPIs at once"""
    print("=== All KPIs ===\n")
    
    provider = create_data_provider(weather_data)
    calculator = create_kpi_calculator(provider)
    
    # Get all KPIs
    all_kpis = calculator.calculate_all()
    
    for kpi in all_kpis:
        print(f"{kpi.display_name}: {kpi.value} {kpi.unit}")
    print()


def example_update_config():
    """Update manual configuration at runtime"""
    print("=== Updating Configuration ===\n")
    
    # Update panel area
    update_manual_config("solar.panel_area", 200.0)
    print("Updated panel area to 200.0 m²")
    
    # Update tariff
    update_manual_config("financial.electricity_tariff", 0.15)
    print("Updated electricity tariff to $0.15/kWh")
    print()


def example_custom_calculation(weather_data):
    """Use parameters in custom calculations"""
    print("=== Custom Calculation ===\n")
    
    provider = create_data_provider(weather_data)
    
    # Get parameters for custom calculation
    irradiance = provider.get("solar_irradiance")
    panel_area = provider.get("panel_area")
    efficiency = provider.get("panel_efficiency")
    
    # Custom: Calculate max theoretical power (no losses)
    max_power_kw = (irradiance * panel_area * efficiency / 100) / 1000
    
    print(f"Maximum Theoretical Power: {max_power_kw:.3f} kW")
    print(f"  (based on {irradiance} W/m², {panel_area} m², {efficiency}% efficiency)")
    print()


def example_handle_missing_data(weather_data):
    """Demonstrate graceful handling of missing data"""
    print("=== Handling Missing Data ===\n")
    
    provider = create_data_provider(weather_data)
    
    # These will return default values if external API is not available
    building_load = provider.get("building_load")
    battery_soc = provider.get("battery_soc")
    
    print(f"Building Load: {building_load} kW (from external API or default)")
    print(f"Battery SOC: {battery_soc} % (from external API or default)")
    print("\nNote: System uses defaults when data sources are unavailable")
    print()


# ==============================================================================
# Run all examples
# ==============================================================================

if __name__ == "__main__":
    from collections import deque
    
    # Create sample weather data
    sample_data = deque([
        {
            "time_iso": "2025-10-15T10:00:00",
            "temp": 25.5,
            "rh": 65.2,
            "lux": 12500.0,
        }
    ], maxlen=10000)
    
    print("=" * 60)
    print("PLUGGABLE PARAMETER SYSTEM - USAGE EXAMPLES")
    print("=" * 60)
    print()
    
    example_basic_usage(sample_data)
    example_multiple_parameters(sample_data)
    example_kpi_calculations(sample_data)
    example_all_kpis(sample_data)
    example_update_config()
    example_custom_calculation(sample_data)
    example_handle_missing_data(sample_data)
    
    print("=" * 60)
    print("For more details, see PARAMETERS_GUIDE.md")
    print("=" * 60)

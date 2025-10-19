"""Configuration and data source settings for KPI calculations.

This module centralizes all parameter definitions and data source mappings.
To plug in a new data source, simply update the fetch functions in data_sources.py
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class DataSourceType(Enum):
    """Available data source types"""
    SENSOR = "sensor"  # From our sensor readings
    EXTERNAL_API = "external_api"  # From external APIs
    DATABASE = "database"  # From database
    MANUAL_INPUT = "manual_input"  # Manually configured values
    CALCULATED = "calculated"  # Calculated from other parameters


@dataclass
class Parameter:
    """Defines a parameter used in KPI calculations"""
    name: str  # Internal variable name
    display_name: str  # Human-readable name
    unit: str  # Unit of measurement
    source: DataSourceType  # Where this data comes from
    source_config: Dict[str, Any]  # Configuration for fetching this parameter
    description: str = ""  # Optional description
    default_value: Any = None  # Fallback value if unavailable


# ==============================================================================
# PARAMETER DEFINITIONS - Add/modify parameters here
# ==============================================================================

# Solar/Energy Parameters
SOLAR_IRRADIANCE = Parameter(
    name="solar_irradiance",
    display_name="Solar Irradiance",
    unit="W/m²",
    source=DataSourceType.SENSOR,
    source_config={"field": "irradiance", "calculation": "lux / 127.0"},
    description="Solar radiation power per unit area",
    default_value=0.0
)

PANEL_AREA = Parameter(
    name="panel_area",
    display_name="Solar Panel Area",
    unit="m²",
    source=DataSourceType.MANUAL_INPUT,
    source_config={"config_key": "solar.panel_area"},
    description="Total area of installed solar panels",
    default_value=100.0  # Example: 100 m²
)

PANEL_EFFICIENCY = Parameter(
    name="panel_efficiency",
    display_name="Panel Efficiency",
    unit="%",
    source=DataSourceType.MANUAL_INPUT,
    source_config={"config_key": "solar.panel_efficiency"},
    description="Solar panel conversion efficiency",
    default_value=20.0  # Example: 20% efficiency
)

SYSTEM_LOSSES = Parameter(
    name="system_losses",
    display_name="System Losses",
    unit="%",
    source=DataSourceType.MANUAL_INPUT,
    source_config={"config_key": "solar.system_losses"},
    description="Total system losses (inverter, wiring, soiling, etc.)",
    default_value=15.0  # Example: 15% losses
)

# Environmental Parameters
TEMPERATURE = Parameter(
    name="temperature",
    display_name="Temperature",
    unit="°C",
    source=DataSourceType.SENSOR,
    source_config={"field": "temp"},
    description="Ambient temperature",
    default_value=25.0
)

HUMIDITY = Parameter(
    name="humidity",
    display_name="Relative Humidity",
    unit="%",
    source=DataSourceType.SENSOR,
    source_config={"field": "rh"},
    description="Relative humidity",
    default_value=50.0
)

AMBIENT_LUX = Parameter(
    name="ambient_lux",
    display_name="Light Level",
    unit="lux",
    source=DataSourceType.SENSOR,
    source_config={"field": "lux"},
    description="Ambient light level",
    default_value=0.0
)

# Energy Consumption Parameters
BUILDING_LOAD = Parameter(
    name="building_load",
    display_name="Building Energy Load",
    unit="kW",
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/energy/load", "field": "load_kw"},
    description="Current building energy consumption",
    default_value=0.0
)

GRID_POWER = Parameter(
    name="grid_power",
    display_name="Grid Power Draw",
    unit="kW",
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/energy/grid", "field": "grid_kw"},
    description="Power drawn from utility grid",
    default_value=0.0
)

BATTERY_SOC = Parameter(
    name="battery_soc",
    display_name="Battery State of Charge",
    unit="%",
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/battery/status", "field": "soc"},
    description="Battery charge level",
    default_value=50.0
)

BATTERY_CAPACITY = Parameter(
    name="battery_capacity",
    display_name="Battery Capacity",
    unit="kWh",
    source=DataSourceType.MANUAL_INPUT,
    source_config={"config_key": "battery.capacity"},
    description="Total battery storage capacity",
    default_value=10.0  # Example: 10 kWh
)

# Financial Parameters
ELECTRICITY_TARIFF = Parameter(
    name="electricity_tariff",
    display_name="Electricity Tariff",
    unit="$/kWh",
    source=DataSourceType.MANUAL_INPUT,
    source_config={"config_key": "financial.electricity_tariff"},
    description="Cost per kWh from utility",
    default_value=0.12  # Example: $0.12/kWh
)

FEED_IN_TARIFF = Parameter(
    name="feed_in_tariff",
    display_name="Feed-in Tariff",
    unit="$/kWh",
    source=DataSourceType.MANUAL_INPUT,
    source_config={"config_key": "financial.feed_in_tariff"},
    description="Revenue per kWh sold to grid",
    default_value=0.08  # Example: $0.08/kWh
)

# Carbon Emissions
GRID_CARBON_INTENSITY = Parameter(
    name="grid_carbon_intensity",
    display_name="Grid Carbon Intensity",
    unit="kg CO₂/kWh",
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/carbon/intensity", "field": "intensity"},
    description="Carbon emissions per kWh from grid",
    default_value=0.5  # Example: 0.5 kg CO₂/kWh
)

# Weather Forecast (for predictions)
FORECAST_IRRADIANCE = Parameter(
    name="forecast_irradiance",
    display_name="Forecasted Irradiance",
    unit="W/m²",
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/weather/forecast", "field": "irradiance"},
    description="Predicted solar irradiance",
    default_value=0.0
)

FORECAST_TEMPERATURE = Parameter(
    name="forecast_temperature",
    display_name="Forecasted Temperature",
    unit="°C",
    source=DataSourceType.EXTERNAL_API,
    source_config={"endpoint": "/api/weather/forecast", "field": "temperature"},
    description="Predicted temperature",
    default_value=25.0
)


# ==============================================================================
# PARAMETER REGISTRY - Automatically collects all defined parameters
# ==============================================================================

ALL_PARAMETERS: Dict[str, Parameter] = {
    "solar_irradiance": SOLAR_IRRADIANCE,
    "panel_area": PANEL_AREA,
    "panel_efficiency": PANEL_EFFICIENCY,
    "system_losses": SYSTEM_LOSSES,
    "temperature": TEMPERATURE,
    "humidity": HUMIDITY,
    "ambient_lux": AMBIENT_LUX,
    "building_load": BUILDING_LOAD,
    "grid_power": GRID_POWER,
    "battery_soc": BATTERY_SOC,
    "battery_capacity": BATTERY_CAPACITY,
    "electricity_tariff": ELECTRICITY_TARIFF,
    "feed_in_tariff": FEED_IN_TARIFF,
    "grid_carbon_intensity": GRID_CARBON_INTENSITY,
    "forecast_irradiance": FORECAST_IRRADIANCE,
    "forecast_temperature": FORECAST_TEMPERATURE,
}


def get_parameter(name: str) -> Parameter:
    """Get parameter definition by name"""
    if name not in ALL_PARAMETERS:
        raise ValueError(f"Unknown parameter: {name}")
    return ALL_PARAMETERS[name]


def get_parameters_by_source(source: DataSourceType) -> List[Parameter]:
    """Get all parameters from a specific data source"""
    return [p for p in ALL_PARAMETERS.values() if p.source == source]


# ==============================================================================
# MANUAL CONFIGURATION - Edit these values as needed
# ==============================================================================

MANUAL_CONFIG: Dict[str, Any] = {
    # Solar System Configuration
    "solar.panel_area": 100.0,  # m²
    "solar.panel_efficiency": 20.0,  # %
    "solar.system_losses": 15.0,  # %
    
    # Battery Configuration
    "battery.capacity": 10.0,  # kWh
    
    # Financial Configuration
    "financial.electricity_tariff": 0.12,  # $/kWh
    "financial.feed_in_tariff": 0.08,  # $/kWh
    
    # External API Endpoints (update when available)
    "api.base_url": "http://localhost:5000",  # Change to actual API URL
    "api.timeout": 5.0,  # seconds
}


def get_manual_config(key: str, default: Any = None) -> Any:
    """Get a manual configuration value"""
    return MANUAL_CONFIG.get(key, default)


def update_manual_config(key: str, value: Any) -> None:
    """Update a manual configuration value (runtime)"""
    MANUAL_CONFIG[key] = value

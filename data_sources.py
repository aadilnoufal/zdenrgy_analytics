"""Data source adapters for fetching parameter values.

This module handles fetching data from various sources (sensors, APIs, databases, etc.).
To plug in a new data source, implement or update the appropriate fetch function.
"""

from __future__ import annotations

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque

from config import (
    Parameter,
    DataSourceType,
    MANUAL_CONFIG,
    get_manual_config,
)


# ==============================================================================
# DATA SOURCE INTERFACES - Implement these to connect to your data sources
# ==============================================================================


class DataSourceAdapter:
    """Base class for data source adapters"""
    
    def fetch(self, parameter: Parameter) -> Optional[float]:
        """Fetch current value for a parameter. Return None if unavailable."""
        raise NotImplementedError


class SensorDataSource(DataSourceAdapter):
    """Fetches data from in-memory sensor readings (our current system)"""
    
    def __init__(self, weather_data: deque):
        """
        Args:
            weather_data: Reference to the weather_data deque from readings.py
        """
        self.weather_data = weather_data
    
    def fetch(self, parameter: Parameter) -> Optional[float]:
        """Get latest sensor reading for the specified field"""
        if not self.weather_data:
            return parameter.default_value
        
        latest = self.weather_data[-1]
        field = parameter.source_config.get("field")
        
        if field not in latest:
            # Check if we need to calculate it
            calculation = parameter.source_config.get("calculation")
            if calculation and "lux" in calculation:
                # Calculate irradiance from lux
                lux = latest.get("lux", 0)
                return lux / 127.0
            return parameter.default_value
        
        return float(latest.get(field, parameter.default_value))
    
    def fetch_historical(
        self, 
        parameter: Parameter, 
        minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get historical sensor readings for a parameter
        
        Args:
            parameter: Parameter to fetch
            minutes: Number of minutes of history to return
            
        Returns:
            List of dicts with 'time' and 'value' keys
        """
        field = parameter.source_config.get("field")
        cutoff = datetime.utcnow().timestamp() - (minutes * 60)
        
        result = []
        for reading in self.weather_data:
            try:
                ts = datetime.fromisoformat(
                    reading["time_iso"].split("+")[0]
                ).timestamp()
                if ts < cutoff:
                    continue
                
                # Get value
                if field in reading:
                    value = reading[field]
                else:
                    # Calculate if needed
                    calculation = parameter.source_config.get("calculation")
                    if calculation and "lux" in calculation:
                        value = reading.get("lux", 0) / 127.0
                    else:
                        continue
                
                result.append({
                    "time": reading["time_iso"],
                    "value": float(value)
                })
            except Exception:
                continue
        
        return result


class ExternalAPIDataSource(DataSourceAdapter):
    """Fetches data from external REST APIs"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        self.base_url = base_url or get_manual_config("api.base_url")
        self.timeout = timeout
    
    def fetch(self, parameter: Parameter) -> Optional[float]:
        """Fetch data from external API endpoint"""
        endpoint = parameter.source_config.get("endpoint")
        field = parameter.source_config.get("field")
        
        if not endpoint:
            return parameter.default_value
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Navigate nested fields (e.g., "data.value")
            value = data
            for key in field.split("."):
                value = value.get(key)
                if value is None:
                    return parameter.default_value
            
            return float(value)
        
        except (requests.RequestException, ValueError, KeyError):
            # Return default value if API call fails
            return parameter.default_value


class DatabaseDataSource(DataSourceAdapter):
    """Fetches data from a database (implement as needed)"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string
        # TODO: Initialize database connection
    
    def fetch(self, parameter: Parameter) -> Optional[float]:
        """Fetch data from database"""
        # TODO: Implement database query logic
        # Example:
        # query = parameter.source_config.get("query")
        # result = self.execute_query(query)
        # return float(result)
        
        return parameter.default_value


class ManualInputDataSource(DataSourceAdapter):
    """Fetches manually configured values"""
    
    def fetch(self, parameter: Parameter) -> Optional[float]:
        """Get value from manual configuration"""
        config_key = parameter.source_config.get("config_key")
        value = get_manual_config(config_key, parameter.default_value)
        return float(value)


# ==============================================================================
# DATA PROVIDER - Main interface for fetching parameters
# ==============================================================================


class DataProvider:
    """
    Unified interface for fetching parameter values from any source.
    
    Usage:
        provider = DataProvider(weather_data=weather_data)
        irradiance = provider.get("solar_irradiance")
        temp = provider.get("temperature")
    """
    
    def __init__(
        self,
        weather_data: Optional[deque] = None,
        api_base_url: Optional[str] = None,
        db_connection: Optional[str] = None,
    ):
        """
        Initialize data provider with available data sources.
        
        Args:
            weather_data: Reference to sensor data deque
            api_base_url: Base URL for external APIs
            db_connection: Database connection string
        """
        self.sources: Dict[DataSourceType, DataSourceAdapter] = {}
        
        # Initialize available data sources
        if weather_data is not None:
            self.sources[DataSourceType.SENSOR] = SensorDataSource(weather_data)
        
        self.sources[DataSourceType.EXTERNAL_API] = ExternalAPIDataSource(api_base_url)
        self.sources[DataSourceType.DATABASE] = DatabaseDataSource(db_connection)
        self.sources[DataSourceType.MANUAL_INPUT] = ManualInputDataSource()
    
    def get(self, parameter_name: str) -> float:
        """
        Fetch current value for a parameter.
        
        Args:
            parameter_name: Name of the parameter (e.g., "solar_irradiance")
            
        Returns:
            Current value or default value if unavailable
        """
        from config import get_parameter
        
        param = get_parameter(parameter_name)
        source = self.sources.get(param.source)
        
        if source is None:
            # Data source not available, return default
            return param.default_value
        
        value = source.fetch(param)
        return value if value is not None else param.default_value
    
    def get_multiple(self, parameter_names: List[str]) -> Dict[str, float]:
        """
        Fetch multiple parameters at once.
        
        Args:
            parameter_names: List of parameter names
            
        Returns:
            Dictionary mapping parameter names to values
        """
        return {name: self.get(name) for name in parameter_names}
    
    def get_all_available(self) -> Dict[str, float]:
        """Get all parameters that have available data sources"""
        from config import ALL_PARAMETERS
        
        result = {}
        for name, param in ALL_PARAMETERS.items():
            if param.source in self.sources:
                result[name] = self.get(name)
        
        return result
    
    def get_historical(
        self,
        parameter_name: str,
        minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get historical data for a parameter (if supported by source).
        
        Args:
            parameter_name: Name of the parameter
            minutes: Number of minutes of history
            
        Returns:
            List of dicts with 'time' and 'value' keys
        """
        from config import get_parameter
        
        param = get_parameter(parameter_name)
        source = self.sources.get(param.source)
        
        if source is None:
            return []
        
        # Only sensor source supports historical data currently
        if isinstance(source, SensorDataSource):
            return source.fetch_historical(param, minutes)
        
        return []


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


def create_data_provider(weather_data: deque) -> DataProvider:
    """
    Create a data provider with default configuration.
    
    Args:
        weather_data: Reference to sensor data from readings.py
        
    Returns:
        Configured DataProvider instance
    """
    return DataProvider(
        weather_data=weather_data,
        api_base_url=get_manual_config("api.base_url"),
        db_connection=None,  # Add DB config when needed
    )

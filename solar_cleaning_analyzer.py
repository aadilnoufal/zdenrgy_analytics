"""Solar Panel Cleaning Interval Analyzer

Analyzes historical lux/temperature data combined with actual inverter generation
to calculate Performance Ratio (PR), track soiling degradation, and recommend
optimal cleaning intervals.

Key Features:
- Import CSV data from lux sensor (per minute) and inverter (per 30 min)
- Calculate Performance Ratio: Actual Output / Theoretical Output
- Track degradation since installation or last cleaning
- Predict optimal cleaning intervals based on degradation patterns
- Support for manual cleaning event recording

System: 10 kWp Solar Panel Installation
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Tuple
from dataclasses import dataclass
from pathlib import Path
import json


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class SolarSystemConfig:
    """Solar system specifications"""
    capacity_kwp: float = 10.0  # System capacity in kWp
    panel_efficiency: float = 0.20  # 20% nominal efficiency
    lux_to_irradiance: float = 165.0  # Conversion factor: lux / 165 = W/m² (calibrated for Qatar)
    temp_coefficient: float = -0.0036  # -0.36%/°C temperature loss coefficient
    reference_temp: float = 25.0  # Standard Test Conditions temperature (°C)
    noct: float = 45.0  # Nominal Operating Cell Temperature
    max_irradiance: float = 1000.0  # Maximum expected irradiance (W/m²) for clamping


# Global config instance
SYSTEM_CONFIG = SolarSystemConfig()


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PerformanceData:
    """Performance data for a single interval"""
    timestamp: datetime
    avg_lux: float
    avg_irradiance: float  # W/m²
    avg_temp: float
    actual_kwh: float
    theoretical_kwh: float
    performance_ratio: float
    temp_adjusted_pr: float  # PR adjusted for temperature effects


@dataclass 
class DegradationAnalysis:
    """Analysis of performance degradation"""
    baseline_pr: float
    current_pr: float
    degradation_percent: float
    degradation_rate_per_day: float
    days_since_baseline: int
    days_to_95_percent: Optional[int]
    days_to_90_percent: Optional[int]
    days_to_85_percent: Optional[int]
    days_to_80_percent: Optional[int]
    recommended_interval_days: int
    soiling_loss_index: float


@dataclass
class CleaningAnalysisResult:
    """Complete analysis result"""
    summary: Dict[str, Any]
    daily_performance: pd.DataFrame
    degradation: DegradationAnalysis
    cleaning_events: List[datetime]
    recommendations: List[str]


# =============================================================================
# CSV PARSING
# =============================================================================

def parse_lux_csv(filepath: str) -> pd.DataFrame:
    """
    Parse lux/temperature CSV file (per-minute data)
    
    Expected format:
    Timestamp, Temperature (°C), Humidity (%), Lux, Irradiance (W/m²)
    12/3/2025 13:20, 36.3, 26.1, 42938.6, 338.099
    
    Returns DataFrame with columns: timestamp, temperature, humidity, lux
    """
    df = pd.read_csv(filepath)
    
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    
    # Find and rename columns
    col_mapping = {}
    for col in df.columns:
        if 'timestamp' in col or 'time' in col or 'date' in col:
            col_mapping[col] = 'timestamp'
        elif 'temp' in col:
            col_mapping[col] = 'temperature'
        elif 'humid' in col or 'rh' in col:
            col_mapping[col] = 'humidity'
        elif 'lux' in col:
            col_mapping[col] = 'lux'
        elif 'irrad' in col:
            col_mapping[col] = 'irradiance_csv'  # Ignore, we'll recalculate
            
    print(f"📊 CSV Column Mapping: {col_mapping}")
    
    df = df.rename(columns=col_mapping)
    
    # Parse timestamp - handle multiple formats
    def parse_timestamp(ts):
        formats = [
            '%m/%d/%Y %H:%M',
            '%d/%m/%Y %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%m/%d/%Y %H:%M:%S',
        ]
        for fmt in formats:
            try:
                return pd.to_datetime(ts, format=fmt)
            except:
                continue
        return pd.to_datetime(ts)  # Let pandas try to parse
    
    df['timestamp'] = df['timestamp'].apply(parse_timestamp)
    
    # Calculate irradiance from lux using proper conversion
    # Clamp to max realistic irradiance (prevents unrealistic theoretical values)
    df['irradiance'] = (df['lux'] / SYSTEM_CONFIG.lux_to_irradiance).clip(upper=SYSTEM_CONFIG.max_irradiance)
    
    # Select and order columns
    result = df[['timestamp', 'temperature', 'humidity', 'lux', 'irradiance']].copy()
    result = result.sort_values('timestamp').reset_index(drop=True)
    
    return result


def parse_inverter_csv(filepath: str) -> pd.DataFrame:
    """
    Parse inverter generation CSV file (per 30-min data)
    
    Expected format:
    Site name, Generation date, Time period, Electricity unit price (QAR/kWh), 
    Electricity generation (kWh), Electricity charge (QAR)
    
    Returns DataFrame with columns: timestamp, actual_kwh, electricity_price
    """
    df = pd.read_csv(filepath)
    
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    
    # Find relevant columns
    date_col = None
    time_col = None
    kwh_col = None
    price_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'generation date' in col_lower or 'date' in col_lower:
            date_col = col
        elif 'time period' in col_lower or 'time' in col_lower:
            time_col = col
        elif 'electricity generation' in col_lower or 'kwh' in col_lower:
            kwh_col = col
        elif 'unit price' in col_lower or 'price' in col_lower:
            price_col = col
    
    # Combine date and time into timestamp
    def create_timestamp(row):
        date_str = str(row[date_col]).strip()
        time_str = str(row[time_col]).strip()
        
        # Parse date
        date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
        date_obj = None
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                break
            except:
                continue
        if date_obj is None:
            date_obj = pd.to_datetime(date_str).to_pydatetime()
        
        # Parse time (format: "13:30")
        try:
            time_parts = time_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            return date_obj.replace(hour=hour, minute=minute)
        except:
            return date_obj
    
    df['timestamp'] = df.apply(create_timestamp, axis=1)
    df['actual_kwh'] = pd.to_numeric(df[kwh_col], errors='coerce')
    
    if price_col:
        df['electricity_price'] = pd.to_numeric(df[price_col], errors='coerce')
    else:
        df['electricity_price'] = 0.22  # Default QAR/kWh
    
    result = df[['timestamp', 'actual_kwh', 'electricity_price']].copy()
    result = result.sort_values('timestamp').reset_index(drop=True)
    
    return result


def parse_cleaning_dates(filepath: str) -> List[datetime]:
    """
    Parse cleaning dates from a text file (one date per line)
    
    Format: YYYY-MM-DD or MM/DD/YYYY
    """
    if not os.path.exists(filepath):
        return []
    
    cleaning_dates = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
            for fmt in formats:
                try:
                    dt = datetime.strptime(line, fmt)
                    cleaning_dates.append(dt)
                    break
                except:
                    continue
    
    return sorted(cleaning_dates)


# =============================================================================
# DATA MERGING
# =============================================================================

def merge_sensor_and_inverter_data(
    lux_df: pd.DataFrame,
    inverter_df: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Merge sensor data (per-second, per-minute, or any frequency) with 30-min inverter data.
    
    Aggregates sensor data to 30-min intervals to match inverter timestamps.
    Handles high-frequency data (per-second) efficiently.
    
    Returns:
        Tuple of (merged DataFrame, debug info dict)
    """
    debug_info = {
        'lux_rows_original': len(lux_df),
        'inverter_rows': len(inverter_df),
        'lux_date_range': None,
        'inverter_date_range': None,
        'merged_rows': 0,
        'overlap_found': False
    }
    
    # Get date ranges for debugging
    if len(lux_df) > 0:
        debug_info['lux_date_range'] = {
            'min': lux_df['timestamp'].min().isoformat(),
            'max': lux_df['timestamp'].max().isoformat()
        }
    
    if len(inverter_df) > 0:
        debug_info['inverter_date_range'] = {
            'min': inverter_df['timestamp'].min().isoformat(),
            'max': inverter_df['timestamp'].max().isoformat()
        }
    
    # Check for date overlap
    if len(lux_df) > 0 and len(inverter_df) > 0:
        lux_min, lux_max = lux_df['timestamp'].min(), lux_df['timestamp'].max()
        inv_min, inv_max = inverter_df['timestamp'].min(), inverter_df['timestamp'].max()
        
        # Check if there's any overlap
        overlap_start = max(lux_min, inv_min)
        overlap_end = min(lux_max, inv_max)
        debug_info['overlap_found'] = overlap_start <= overlap_end
        
        if debug_info['overlap_found']:
            debug_info['overlap_range'] = {
                'start': overlap_start.isoformat(),
                'end': overlap_end.isoformat()
            }
    
    # Round lux timestamps to 30-min intervals
    lux_df = lux_df.copy()
    lux_df['interval'] = lux_df['timestamp'].dt.floor('30min')
    
    # Aggregate lux data by 30-min interval (handles per-second, per-minute, etc.)
    lux_agg = lux_df.groupby('interval').agg({
        'temperature': 'mean',
        'humidity': 'mean',
        'lux': 'mean',
        'irradiance': 'mean'
    }).reset_index()
    lux_agg = lux_agg.rename(columns={'interval': 'timestamp'})
    
    debug_info['lux_rows_aggregated'] = len(lux_agg)
    
    # Round inverter timestamps to match
    inverter_df = inverter_df.copy()
    inverter_df['timestamp'] = inverter_df['timestamp'].dt.floor('30min')
    
    # Remove duplicate inverter entries for same timestamp (take sum of kwh)
    inverter_agg = inverter_df.groupby('timestamp').agg({
        'actual_kwh': 'sum',
        'electricity_price': 'first'
    }).reset_index()
    
    debug_info['inverter_rows_aggregated'] = len(inverter_agg)
    
    # Merge on timestamp
    merged = pd.merge(
        lux_agg, 
        inverter_agg, 
        on='timestamp', 
        how='inner'
    )
    
    debug_info['merged_rows_before_filter'] = len(merged)
    
    # Filter for time between 10:00 AM and 1:00 PM (inclusive of 13:00)
    # This ensures we analyze peak sun hours and avoid sunrise/sunset anomalies
    # Keeps: 10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00
    mask = (merged['timestamp'].dt.hour >= 10) & (
        (merged['timestamp'].dt.hour < 13) | 
        ((merged['timestamp'].dt.hour == 13) & (merged['timestamp'].dt.minute == 0))
    )
    merged = merged[mask]
    
    debug_info['merged_rows'] = len(merged)
    
    # If no inner join matches, try to diagnose
    if len(merged) == 0 and debug_info['overlap_found']:
        # Check the actual timestamp values
        debug_info['lux_sample_timestamps'] = [t.isoformat() for t in lux_agg['timestamp'].head(5).tolist()]
        debug_info['inverter_sample_timestamps'] = [t.isoformat() for t in inverter_agg['timestamp'].head(5).tolist()]
    
    return merged, debug_info


# =============================================================================
# PERFORMANCE CALCULATIONS
# =============================================================================

def calculate_theoretical_kwh(
    irradiance: float,  # W/m²
    duration_hours: float = 0.5,  # 30 min = 0.5 hours
    config: SolarSystemConfig = SYSTEM_CONFIG
) -> float:
    """
    Calculate theoretical energy output based on irradiance.
    
    Formula: Theoretical = (Irradiance / 1000) × Capacity_kWp × Duration
    
    At 1000 W/m² (STC), a 10 kWp system should produce 10 kW
    """
    # Irradiance ratio (1000 W/m² = STC)
    irradiance_ratio = irradiance / 1000.0
    
    # Theoretical output
    theoretical_kw = irradiance_ratio * config.capacity_kwp
    theoretical_kwh = theoretical_kw * duration_hours
    
    return max(0, theoretical_kwh)


def calculate_performance_ratio(
    actual_kwh: float,
    theoretical_kwh: float
) -> float:
    """
    Calculate Performance Ratio (PR).
    
    PR = Actual Output / Theoretical Output
    
    Typical values: 0.75-0.90 for well-maintained systems
    """
    if theoretical_kwh <= 0:
        return 0.0
    
    return actual_kwh / theoretical_kwh


def calculate_temp_adjusted_pr(
    pr: float,
    temperature: float,
    config: SolarSystemConfig = SYSTEM_CONFIG
) -> float:
    """
    Adjust PR for temperature effects.
    
    Panels lose efficiency at higher temperatures.
    Standard coefficient: -0.36%/°C above 25°C
    """
    temp_diff = temperature - config.reference_temp
    temp_loss_factor = 1 + (config.temp_coefficient * temp_diff)
    
    # Adjusted PR removes temperature effect to isolate soiling
    if temp_loss_factor > 0:
        return pr / temp_loss_factor
    return pr


def calculate_cell_temperature(
    ambient_temp: float,
    irradiance: float,
    config: SolarSystemConfig = SYSTEM_CONFIG
) -> float:
    """
    Estimate cell temperature using NOCT model.
    
    T_cell = T_ambient + (NOCT - 20) × (Irradiance / 800)
    """
    return ambient_temp + (config.noct - 20) * (irradiance / 800)


def calculate_soiling_loss_index(
    current_pr: float,
    baseline_pr: float
) -> float:
    """
    Calculate Soiling Loss Index (%).
    
    SLI = (Baseline_PR - Current_PR) / Baseline_PR × 100
    
    Represents power loss attributable to soiling.
    """
    if baseline_pr <= 0:
        return 0.0
    
    return max(0, (baseline_pr - current_pr) / baseline_pr * 100)


def calculate_temperature_loss(
    pr_at_temp: float,
    temperature: float,
    config: SolarSystemConfig = SYSTEM_CONFIG
) -> float:
    """
    Calculate actual temperature loss coefficient.
    
    Compare with standard -0.36%/°C to validate assumptions.
    """
    temp_diff = temperature - config.reference_temp
    if temp_diff == 0:
        return 0.0
    
    # Assuming baseline PR at reference temp is ~0.85
    expected_pr = 0.85
    actual_loss_percent = (expected_pr - pr_at_temp) / expected_pr * 100
    
    return actual_loss_percent / temp_diff if temp_diff != 0 else 0


# =============================================================================
# ANALYSIS ENGINE
# =============================================================================

class SolarCleaningAnalyzer:
    """Main analysis engine for solar panel cleaning optimization"""
    
    def __init__(self, config: SolarSystemConfig = SYSTEM_CONFIG):
        self.config = config
        self.merged_data: Optional[pd.DataFrame] = None
        self.daily_performance: Optional[pd.DataFrame] = None
        self.cleaning_events: List[datetime] = []
        self.installation_date: Optional[datetime] = None
        self.merge_debug_info: Dict[str, Any] = {}
    
    def load_data(
        self,
        lux_csv: str,
        inverter_csv: str,
        cleaning_dates_file: Optional[str] = None
    ) -> bool:
        """Load and merge all data sources"""
        try:
            # Parse CSVs
            lux_df = parse_lux_csv(lux_csv)
            inverter_df = parse_inverter_csv(inverter_csv)
            
            # Merge data
            self.merged_data, self.merge_debug_info = merge_sensor_and_inverter_data(lux_df, inverter_df)
            
            if len(self.merged_data) == 0:
                print("⚠️ Warning: No matching data found between lux and inverter CSVs")
                print(f"   Lux data range: {lux_df['timestamp'].min()} to {lux_df['timestamp'].max()}")
                print(f"   Inverter data range: {inverter_df['timestamp'].min()} to {inverter_df['timestamp'].max()}")
                return False
            
            # Calculate performance metrics for each interval
            self._calculate_interval_performance()
            
            # Aggregate to daily
            self._calculate_daily_performance()
            
            # Load cleaning dates
            if cleaning_dates_file:
                self.cleaning_events = parse_cleaning_dates(cleaning_dates_file)
            
            # Set installation date as first data point
            self.installation_date = self.merged_data['timestamp'].min()
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_from_dataframes(
        self,
        lux_df: pd.DataFrame,
        inverter_df: pd.DataFrame,
        cleaning_dates: Optional[List[datetime]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Load data from pandas DataFrames directly
        
        Returns:
            Tuple of (success: bool, debug_info: dict)
        """
        debug_info = {}
        try:
            self.merged_data, merge_debug = merge_sensor_and_inverter_data(lux_df, inverter_df)
            debug_info = merge_debug
            
            if len(self.merged_data) == 0:
                debug_info['error'] = 'No matching timestamps found between lux and inverter data'
                return False, debug_info
            
            self._calculate_interval_performance()
            self._calculate_daily_performance()
            
            if cleaning_dates:
                self.cleaning_events = sorted(cleaning_dates)
            
            self.installation_date = self.merged_data['timestamp'].min()
            debug_info['success'] = True
            return True, debug_info
            
        except Exception as e:
            import traceback
            debug_info['error'] = str(e)
            debug_info['traceback'] = traceback.format_exc()
            print(f"❌ Error loading data: {e}")
            return False, debug_info
    
    def _calculate_interval_performance(self):
        """Calculate performance metrics for each 30-min interval"""
        df = self.merged_data.copy()
        
        # Calculate theoretical output
        df['theoretical_kwh'] = df['irradiance'].apply(
            lambda x: calculate_theoretical_kwh(x, 0.5, self.config)
        )
        
        # Calculate PR
        df['performance_ratio'] = df.apply(
            lambda row: calculate_performance_ratio(row['actual_kwh'], row['theoretical_kwh']),
            axis=1
        )
        
        # Calculate cell temperature
        df['cell_temp'] = df.apply(
            lambda row: calculate_cell_temperature(row['temperature'], row['irradiance'], self.config),
            axis=1
        )
        
        # Calculate temperature-adjusted PR
        df['temp_adjusted_pr'] = df.apply(
            lambda row: calculate_temp_adjusted_pr(row['performance_ratio'], row['cell_temp'], self.config),
            axis=1
        )
        
        # Filter out night/low irradiance periods (< 50 W/m²)
        df['valid_for_analysis'] = df['irradiance'] >= 50
        
        self.merged_data = df
    
    def _calculate_daily_performance(self):
        """Aggregate to daily performance metrics"""
        df = self.merged_data[self.merged_data['valid_for_analysis']].copy()
        
        if len(df) == 0:
            self.daily_performance = pd.DataFrame()
            return
        
        df['date'] = df['timestamp'].dt.date
        
        daily = df.groupby('date').agg({
            'temperature': 'mean',
            'humidity': 'mean',
            'lux': 'mean',
            'irradiance': 'mean',
            'actual_kwh': 'sum',
            'theoretical_kwh': 'sum',
            'performance_ratio': 'mean',
            'temp_adjusted_pr': 'mean',
            'cell_temp': 'mean'
        }).reset_index()
        
        # Recalculate daily PR from sums
        daily['daily_pr'] = daily.apply(
            lambda row: row['actual_kwh'] / row['theoretical_kwh'] if row['theoretical_kwh'] > 0 else 0,
            axis=1
        )
        
        # Add days since installation/cleaning
        daily['date'] = pd.to_datetime(daily['date'])
        
        self.daily_performance = daily
    
    def analyze_degradation(self) -> DegradationAnalysis:
        """Analyze performance degradation pattern"""
        if self.daily_performance is None or len(self.daily_performance) == 0:
            return DegradationAnalysis(
                baseline_pr=0, current_pr=0, degradation_percent=0,
                degradation_rate_per_day=0, days_since_baseline=0,
                days_to_95_percent=None, days_to_90_percent=None,
                days_to_85_percent=None, days_to_80_percent=None,
                recommended_interval_days=14, soiling_loss_index=0
            )
        
        df = self.daily_performance.copy()
        
        # Determine baseline period (first 3 days or after last cleaning)
        if self.cleaning_events:
            last_cleaning = max(self.cleaning_events)
            baseline_start = last_cleaning
        else:
            baseline_start = df['date'].min()
        
        # Get baseline PR (average of first 3 days after baseline)
        baseline_end = baseline_start + timedelta(days=3)
        baseline_data = df[(df['date'] >= baseline_start) & (df['date'] <= baseline_end)]
        
        if len(baseline_data) > 0:
            baseline_pr = baseline_data['daily_pr'].mean()
        else:
            # Use first available data
            baseline_pr = df['daily_pr'].iloc[:3].mean() if len(df) >= 3 else df['daily_pr'].mean()
        
        # Current PR (last 3 days average)
        current_pr = df['daily_pr'].iloc[-3:].mean() if len(df) >= 3 else df['daily_pr'].iloc[-1]
        
        # Days since baseline
        days_since = (df['date'].max() - baseline_start).days
        
        # Degradation
        degradation_percent = calculate_soiling_loss_index(current_pr, baseline_pr)
        
        # Degradation rate per day
        if days_since > 0:
            degradation_rate = degradation_percent / days_since
        else:
            degradation_rate = 0
        
        # Predict days to thresholds
        def days_to_threshold(target_percent_loss):
            if degradation_rate <= 0:
                return None
            return int(target_percent_loss / degradation_rate)
        
        days_to_95 = days_to_threshold(5)   # 5% loss = 95% capacity
        days_to_90 = days_to_threshold(10)  # 10% loss = 90% capacity
        days_to_85 = days_to_threshold(15)  # 15% loss = 85% capacity
        days_to_80 = days_to_threshold(20)  # 20% loss = 80% capacity
        
        # Recommended interval (when 10% degradation occurs)
        recommended = days_to_90 if days_to_90 else 14
        
        return DegradationAnalysis(
            baseline_pr=baseline_pr,
            current_pr=current_pr,
            degradation_percent=degradation_percent,
            degradation_rate_per_day=degradation_rate,
            days_since_baseline=days_since,
            days_to_95_percent=days_to_95,
            days_to_90_percent=days_to_90,
            days_to_85_percent=days_to_85,
            days_to_80_percent=days_to_80,
            recommended_interval_days=recommended,
            soiling_loss_index=degradation_percent
        )
    
    def calculate_post_cleaning_recovery(self) -> List[Dict[str, Any]]:
        """Calculate performance recovery after each cleaning event"""
        if not self.cleaning_events or self.daily_performance is None:
            return []
        
        recoveries = []
        df = self.daily_performance
        
        for cleaning_date in self.cleaning_events:
            cleaning_dt = pd.Timestamp(cleaning_date)
            
            # Get 3 days before cleaning
            before_start = cleaning_dt - timedelta(days=3)
            before_data = df[(df['date'] >= before_start) & (df['date'] < cleaning_dt)]
            
            # Get 3 days after cleaning
            after_end = cleaning_dt + timedelta(days=3)
            after_data = df[(df['date'] > cleaning_dt) & (df['date'] <= after_end)]
            
            if len(before_data) > 0 and len(after_data) > 0:
                pr_before = before_data['daily_pr'].mean()
                pr_after = after_data['daily_pr'].mean()
                
                recovery_percent = ((pr_after - pr_before) / pr_before) * 100 if pr_before > 0 else 0
                
                recoveries.append({
                    'cleaning_date': cleaning_date,
                    'pr_before': pr_before,
                    'pr_after': pr_after,
                    'recovery_percent': recovery_percent,
                    'kwh_before_avg': before_data['actual_kwh'].sum() / len(before_data),
                    'kwh_after_avg': after_data['actual_kwh'].sum() / len(after_data)
                })
        
        return recoveries
    
    def calculate_temperature_analysis(self) -> Dict[str, float]:
        """Analyze temperature effects on performance"""
        if self.merged_data is None:
            return {}
        
        df = self.merged_data[self.merged_data['valid_for_analysis']].copy()
        
        if len(df) == 0:
            return {}
        
        # Group by temperature bins
        df['temp_bin'] = pd.cut(df['cell_temp'], bins=range(20, 65, 5))
        temp_analysis = df.groupby('temp_bin').agg({
            'performance_ratio': 'mean',
            'cell_temp': 'mean'
        }).dropna()
        
        # Calculate actual temperature coefficient
        if len(temp_analysis) >= 2:
            temps = temp_analysis['cell_temp'].values
            prs = temp_analysis['performance_ratio'].values
            
            # Linear regression
            if len(temps) > 1:
                slope = np.polyfit(temps, prs, 1)[0]
                avg_pr = np.mean(prs)
                temp_coefficient = (slope / avg_pr) * 100  # %/°C
            else:
                temp_coefficient = -0.36
        else:
            temp_coefficient = -0.36
        
        return {
            'measured_temp_coefficient': temp_coefficient,
            'expected_temp_coefficient': -0.36,
            'avg_cell_temp': df['cell_temp'].mean(),
            'max_cell_temp': df['cell_temp'].max(),
            'min_cell_temp': df['cell_temp'].min(),
            'max_ambient_temp': df['temperature'].max(),
            'avg_ambient_temp': df['temperature'].mean()
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        if self.daily_performance is None or len(self.daily_performance) == 0:
            return {
                'error': 'No data loaded or no valid data for analysis',
                'success': False
            }
        
        degradation = self.analyze_degradation()
        temp_analysis = self.calculate_temperature_analysis()
        cleaning_recovery = self.calculate_post_cleaning_recovery()
        
        # Summary statistics
        df = self.daily_performance
        total_actual_kwh = df['actual_kwh'].sum()
        total_theoretical_kwh = df['theoretical_kwh'].sum()
        avg_daily_kwh = df['actual_kwh'].mean()
        
        # Generate recommendations
        recommendations = []
        
        if degradation.degradation_percent >= 15:
            recommendations.append("⚠️ URGENT: Clean panels immediately - 15%+ performance loss detected")
        elif degradation.degradation_percent >= 10:
            recommendations.append("⚡ RECOMMENDED: Schedule cleaning soon - 10%+ performance loss")
        elif degradation.degradation_percent >= 5:
            recommendations.append("📊 MONITORING: Performance declining - watch for trends")
        else:
            recommendations.append("✅ GOOD: Panels performing well")
        
        if degradation.days_to_90_percent:
            recommendations.append(f"📅 Optimal cleaning interval: every {degradation.days_to_90_percent} days")
        
        if degradation.degradation_rate_per_day > 0:
            recommendations.append(f"📉 Degradation rate: {degradation.degradation_rate_per_day:.2f}%/day")
        
        return {
            'success': True,
            'summary': {
                'data_range': {
                    'start': df['date'].min().isoformat(),
                    'end': df['date'].max().isoformat(),
                    'days': len(df)
                },
                'total_generation_kwh': round(total_actual_kwh, 2),
                'total_theoretical_kwh': round(total_theoretical_kwh, 2),
                'avg_daily_kwh': round(avg_daily_kwh, 2),
                'overall_pr': round(total_actual_kwh / total_theoretical_kwh * 100, 1) if total_theoretical_kwh > 0 else 0,
                'system_capacity_kwp': self.config.capacity_kwp
            },
            'degradation': {
                'baseline_pr_percent': round(degradation.baseline_pr * 100, 1),
                'current_pr_percent': round(degradation.current_pr * 100, 1),
                'degradation_percent': round(degradation.degradation_percent, 2),
                'degradation_rate_per_day': round(degradation.degradation_rate_per_day, 3),
                'days_since_baseline': degradation.days_since_baseline,
                'days_to_95_percent': degradation.days_to_95_percent,
                'days_to_90_percent': degradation.days_to_90_percent,
                'days_to_85_percent': degradation.days_to_85_percent,
                'days_to_80_percent': degradation.days_to_80_percent,
                'recommended_interval_days': degradation.recommended_interval_days,
                'soiling_loss_index': round(degradation.soiling_loss_index, 2)
            },
            'temperature_analysis': {
                'measured_coefficient': round(temp_analysis.get('measured_temp_coefficient', -0.36), 3),
                'expected_coefficient': -0.36,
                'avg_cell_temp': round(temp_analysis.get('avg_cell_temp', 0), 1),
                'max_cell_temp': round(temp_analysis.get('max_cell_temp', 0), 1),
                'max_ambient_temp': round(temp_analysis.get('max_ambient_temp', 0), 1),
                'avg_ambient_temp': round(temp_analysis.get('avg_ambient_temp', 0), 1)
            },
            'cleaning_recovery': cleaning_recovery,
            'cleaning_events_count': len(self.cleaning_events),
            'recommendations': recommendations,
            'daily_data': df.to_dict(orient='records') if len(df) <= 100 else df.tail(30).to_dict(orient='records')
        }
    
    def get_daily_pr_trend(self) -> List[Dict[str, Any]]:
        """Get daily PR trend for charting"""
        if self.daily_performance is None:
            return []
        
        df = self.daily_performance
        return [
            {
                'date': row['date'].isoformat(),
                'daily_pr': round(row['daily_pr'] * 100, 1),
                'actual_kwh': round(row['actual_kwh'], 2),
                'theoretical_kwh': round(row['theoretical_kwh'], 2),
                'avg_temp': round(row['temperature'], 1),
                'avg_irradiance': round(row['irradiance'], 1)
            }
            for _, row in df.iterrows()
        ]


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """Command line interface for analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Solar Panel Cleaning Interval Analyzer')
    parser.add_argument('--lux', required=True, help='Path to lux/temp CSV file')
    parser.add_argument('--inverter', required=True, help='Path to inverter generation CSV file')
    parser.add_argument('--cleaning', help='Path to cleaning dates file (optional)')
    parser.add_argument('--capacity', type=float, default=10.0, help='System capacity in kWp (default: 10)')
    parser.add_argument('--output', help='Output JSON file path (optional)')
    
    args = parser.parse_args()
    
    # Update config
    SYSTEM_CONFIG.capacity_kwp = args.capacity
    
    # Run analysis
    analyzer = SolarCleaningAnalyzer()
    
    print("🔄 Loading data...")
    if not analyzer.load_data(args.lux, args.inverter, args.cleaning):
        print("❌ Failed to load data")
        return 1
    
    print("📊 Analyzing performance...")
    report = analyzer.generate_report()
    
    if not report.get('success'):
        print(f"❌ Analysis failed: {report.get('error')}")
        return 1
    
    # Print summary
    print("\n" + "="*60)
    print("☀️  SOLAR PANEL CLEANING ANALYSIS REPORT")
    print("="*60)
    
    summary = report['summary']
    print(f"\n📅 Data Range: {summary['data_range']['start']} to {summary['data_range']['end']}")
    print(f"   ({summary['data_range']['days']} days of data)")
    print(f"\n⚡ System Capacity: {summary['system_capacity_kwp']} kWp")
    print(f"   Total Generation: {summary['total_generation_kwh']} kWh")
    print(f"   Average Daily: {summary['avg_daily_kwh']} kWh")
    print(f"   Overall PR: {summary['overall_pr']}%")
    
    deg = report['degradation']
    print(f"\n📉 DEGRADATION ANALYSIS:")
    print(f"   Baseline PR: {deg['baseline_pr_percent']}%")
    print(f"   Current PR: {deg['current_pr_percent']}%")
    print(f"   Performance Loss: {deg['degradation_percent']}%")
    print(f"   Degradation Rate: {deg['degradation_rate_per_day']}%/day")
    print(f"   Soiling Loss Index: {deg['soiling_loss_index']}%")
    
    print(f"\n⏱️  CAPACITY PREDICTIONS:")
    if deg['days_to_95_percent']:
        print(f"   → 95% capacity in: ~{deg['days_to_95_percent']} days")
    if deg['days_to_90_percent']:
        print(f"   → 90% capacity in: ~{deg['days_to_90_percent']} days")
    if deg['days_to_85_percent']:
        print(f"   → 85% capacity in: ~{deg['days_to_85_percent']} days")
    if deg['days_to_80_percent']:
        print(f"   → 80% capacity in: ~{deg['days_to_80_percent']} days")
    
    print(f"\n🧹 RECOMMENDED CLEANING INTERVAL: Every {deg['recommended_interval_days']} days")
    
    temp = report['temperature_analysis']
    print(f"\n🌡️  TEMPERATURE ANALYSIS:")
    print(f"   Measured Temp Coefficient: {temp['measured_coefficient']}%/°C")
    print(f"   Expected Coefficient: {temp['expected_coefficient']}%/°C")
    print(f"   Avg Cell Temperature: {temp['avg_cell_temp']}°C")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"   {rec}")
    
    print("\n" + "="*60)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 Report saved to: {args.output}")
    
    return 0


if __name__ == '__main__':
    exit(main())

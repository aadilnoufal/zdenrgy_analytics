"""Solar Panel Cleaning Tracker

Tracks cleaning history and calculates optimal cleaning intervals based on
performance degradation (ratio of actual output to expected output based on irradiance).
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psycopg2
from db_manager import get_db_manager


class CleaningTracker:
    """Manages solar panel cleaning records and recommendations"""
    
    def __init__(self):
        self.db = get_db_manager()
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create cleaning_records table if it doesn't exist"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cleaning_records (
                    id SERIAL PRIMARY KEY,
                    cleaning_date TIMESTAMP NOT NULL,
                    baseline_ratio REAL NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_cleaning_date 
                ON cleaning_records(cleaning_date DESC);
            """)
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"⚠️ Error creating cleaning_records table: {e}")
            conn.rollback()
        finally:
            self.db.return_connection(conn)
    
    def record_cleaning(self, cleaning_date: datetime = None, baseline_ratio: float = None, 
                       notes: str = "") -> bool:
        """
        Record a panel cleaning event
        
        Args:
            cleaning_date: When panels were cleaned (default: now)
            baseline_ratio: Performance ratio after cleaning (default: calculate from current data)
            notes: Optional notes about the cleaning
        
        Returns:
            True if successful, False otherwise
        """
        if cleaning_date is None:
            cleaning_date = datetime.utcnow()
        
        if baseline_ratio is None:
            # Calculate current performance ratio
            baseline_ratio = self.calculate_current_performance_ratio()
        
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cleaning_records (cleaning_date, baseline_ratio, notes)
                VALUES (%s, %s, %s)
            """, (cleaning_date, baseline_ratio, notes))
            conn.commit()
            cursor.close()
            print(f"✅ Recorded cleaning on {cleaning_date} with baseline ratio {baseline_ratio:.3f}")
            return True
        except Exception as e:
            print(f"⚠️ Error recording cleaning: {e}")
            conn.rollback()
            return False
        finally:
            self.db.return_connection(conn)
    
    def get_last_cleaning(self) -> Optional[Dict[str, Any]]:
        """Get the most recent cleaning record"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, cleaning_date, baseline_ratio, notes, created_at
                FROM cleaning_records
                ORDER BY cleaning_date DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'id': row[0],
                    'cleaning_date': row[1],
                    'baseline_ratio': row[2],
                    'notes': row[3],
                    'created_at': row[4],
                    'days_since': (datetime.utcnow() - row[1]).days
                }
            return None
        except Exception as e:
            print(f"⚠️ Error getting last cleaning: {e}")
            return None
        finally:
            self.db.return_connection(conn)
    
    def get_cleaning_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get cleaning history"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, cleaning_date, baseline_ratio, notes, created_at
                FROM cleaning_records
                ORDER BY cleaning_date DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            
            history = []
            for row in rows:
                history.append({
                    'id': row[0],
                    'cleaning_date': row[1],
                    'baseline_ratio': row[2],
                    'notes': row[3],
                    'created_at': row[4]
                })
            return history
        except Exception as e:
            print(f"⚠️ Error getting cleaning history: {e}")
            return []
        finally:
            self.db.return_connection(conn)
    
    def calculate_current_performance_ratio(self, hours: int = 6) -> float:
        """
        Calculate current performance ratio (actual output / theoretical output)
        
        This will use actual solar output once available. For now, uses a baseline method.
        
        Args:
            hours: Number of hours to average over
        
        Returns:
            Performance ratio (0.0 to 1.0+)
        """
        # Get recent sensor data
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT AVG(irradiance) as avg_irradiance
                FROM sensor_readings
                WHERE timestamp >= %s
                  AND irradiance > 100
            """, (cutoff,))
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0]:
                # Placeholder: Return a baseline ratio
                # When actual solar output is available, replace with:
                # actual_output / (avg_irradiance * panel_area * efficiency * (1 - losses))
                return 0.85  # Baseline clean panel performance
            
            return 0.80  # Default if no data
        except Exception as e:
            print(f"⚠️ Error calculating performance ratio: {e}")
            return 0.80
        finally:
            self.db.return_connection(conn)
    
    def get_performance_degradation(self) -> Optional[Dict[str, Any]]:
        """
        Calculate performance degradation since last cleaning
        
        Returns:
            Dictionary with degradation metrics or None if insufficient data
        """
        last_cleaning = self.get_last_cleaning()
        if not last_cleaning:
            return {
                'has_baseline': False,
                'message': 'No cleaning records found. Record a cleaning to establish baseline.',
                'current_ratio': self.calculate_current_performance_ratio(),
                'degradation_percent': 0.0,
                'needs_cleaning': False
            }
        
        baseline_ratio = last_cleaning['baseline_ratio']
        current_ratio = self.calculate_current_performance_ratio()
        
        # Calculate degradation
        degradation = ((baseline_ratio - current_ratio) / baseline_ratio) * 100
        
        # Recommendation threshold (default 10% degradation)
        needs_cleaning = degradation >= 10.0
        
        return {
            'has_baseline': True,
            'last_cleaning_date': last_cleaning['cleaning_date'],
            'days_since_cleaning': last_cleaning['days_since'],
            'baseline_ratio': baseline_ratio,
            'current_ratio': current_ratio,
            'degradation_percent': max(0.0, degradation),  # Don't show negative
            'needs_cleaning': needs_cleaning,
            'recommendation': self._get_recommendation(degradation, last_cleaning['days_since'])
        }
    
    def _get_recommendation(self, degradation: float, days_since: int) -> str:
        """Generate cleaning recommendation message"""
        if degradation >= 15:
            return f"⚠️ URGENT: {degradation:.1f}% performance loss detected. Clean panels immediately!"
        elif degradation >= 10:
            return f"⚡ Recommended: {degradation:.1f}% performance loss. Schedule cleaning soon."
        elif degradation >= 5:
            return f"📊 Monitoring: {degradation:.1f}% performance loss. Consider cleaning if trend continues."
        elif days_since >= 90:
            return f"📅 Preventive: {days_since} days since last cleaning. Consider routine maintenance."
        else:
            return f"✅ Good: {degradation:.1f}% degradation. Panels performing well."
    
    def get_average_cleaning_interval(self) -> Optional[int]:
        """Calculate average days between cleanings"""
        history = self.get_cleaning_history(limit=10)
        if len(history) < 2:
            return None
        
        intervals = []
        for i in range(len(history) - 1):
            delta = history[i]['cleaning_date'] - history[i + 1]['cleaning_date']
            intervals.append(delta.days)
        
        return int(sum(intervals) / len(intervals)) if intervals else None
    
    def get_cleaning_stats(self) -> Dict[str, Any]:
        """Get comprehensive cleaning statistics"""
        history = self.get_cleaning_history(limit=100)
        last_cleaning = self.get_last_cleaning()
        avg_interval = self.get_average_cleaning_interval()
        degradation = self.get_performance_degradation()
        
        return {
            'total_cleanings': len(history),
            'last_cleaning': last_cleaning,
            'average_interval_days': avg_interval,
            'degradation': degradation,
            'cleaning_history': history[:5]  # Last 5 cleanings
        }


# Global instance
_cleaning_tracker = None

def get_cleaning_tracker() -> CleaningTracker:
    """Get global cleaning tracker instance"""
    global _cleaning_tracker
    if _cleaning_tracker is None:
        _cleaning_tracker = CleaningTracker()
    return _cleaning_tracker

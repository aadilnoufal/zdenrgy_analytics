"""
Database Manager for ZDEnergy Analytics
Handles PostgreSQL connections, schema management, and data operations
"""

import os
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        """Initialize database connection pool"""
        self.connection_pool = None
        self._create_connection_pool()
    
    def _create_connection_pool(self):
        """Create a connection pool for efficient database access"""
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USERNAME'),
                password=os.getenv('DB_PASSWORD'),
                sslmode=os.getenv('DB_SSLMODE', 'require')
            )
            logger.info("✅ Database connection pool created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create connection pool: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            return self.connection_pool.getconn()
        except Exception as e:
            logger.error(f"❌ Failed to get connection: {e}")
            raise
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        try:
            self.connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"❌ Failed to return connection: {e}")
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("✅ All database connections closed")
    
    def initialize_schema(self):
        """Create database tables if they don't exist"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create sensor_readings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    sensor_id VARCHAR(100),
                    temperature REAL,
                    humidity REAL,
                    lux REAL,
                    irradiance REAL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # Create index for fast time-based queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp 
                ON sensor_readings (timestamp DESC);
            """)
            
            # Create KPI snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kpi_snapshots (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    kpi_name VARCHAR(100) NOT NULL,
                    value REAL NOT NULL,
                    unit VARCHAR(50),
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # Create index for KPI queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_timestamp 
                ON kpi_snapshots (timestamp DESC, kpi_name);
            """)
            
            # Create system configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id SERIAL PRIMARY KEY,
                    config_key VARCHAR(100) UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            conn.commit()
            logger.info("✅ Database schema initialized successfully")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Failed to initialize schema: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def insert_sensor_reading(
        self, 
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        lux: Optional[float] = None,
        irradiance: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        sensor_id: Optional[str] = None
    ) -> int:
        """
        Insert a sensor reading into the database
        Returns the inserted record ID
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Use current time if timestamp not provided
            if timestamp is None:
                timestamp = datetime.utcnow()
            # Just use timestamp as-is (no timezone conversion)
            
            # Try inserting with sensor_id, fall back to without if column doesn't exist
            try:
                cursor.execute("""
                    INSERT INTO sensor_readings (timestamp, sensor_id, temperature, humidity, lux, irradiance)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (timestamp, sensor_id, temperature, humidity, lux, irradiance))
            except Exception as e:
                if "sensor_id" in str(e) and "does not exist" in str(e):
                    # Column doesn't exist, rollback and insert without it
                    conn.rollback()
                    logger.warning("⚠️  sensor_id column not found, inserting without it")
                    cursor.execute("""
                        INSERT INTO sensor_readings (timestamp, temperature, humidity, lux, irradiance)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (timestamp, temperature, humidity, lux, irradiance))
                else:
                    raise
            
            record_id = cursor.fetchone()[0]
            conn.commit()
            
            return record_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Failed to insert sensor reading: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def get_latest_readings(self, limit: int = 100) -> List[Dict]:
        """Get the most recent sensor readings"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT timestamp, temperature, humidity, lux, irradiance
                FROM sensor_readings
                ORDER BY timestamp DESC
                LIMIT %s;
            """, (limit,))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest readings: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def get_readings_by_time_range(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """Get sensor readings within a time range (converts to Qatar time)"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Use times as-is (no timezone conversion)
            cursor.execute("""
                SELECT timestamp, temperature, humidity, lux, irradiance
                FROM sensor_readings
                WHERE timestamp BETWEEN %s AND %s
                ORDER BY timestamp ASC;
            """, (start_time, end_time))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Failed to get readings by time range: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def get_readings_by_window(self, window_minutes: int = 60) -> List[Dict]:
        """Get sensor readings for the last N minutes"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=window_minutes)
        return self.get_readings_by_time_range(start_time, end_time)
    
    def get_readings_by_date(self, date_str: str) -> List[Dict]:
        """Get all readings for a specific date (YYYY-MM-DD).
        
        Args:
            date_str: Date in format 'YYYY-MM-DD'
            
        Returns:
            List of readings for that day
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Parse date and create start/end timestamps for the day
            date = datetime.strptime(date_str, '%Y-%m-%d')
            start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            cursor.execute("""
                SELECT 
                    sensor_id as id,
                    timestamp,
                    temperature as temp,
                    humidity as rh,
                    lux,
                    irradiance
                FROM sensor_readings
                WHERE timestamp >= %s AND timestamp <= %s
                ORDER BY timestamp ASC;
            """, (start_time, end_time))
            
            results = cursor.fetchall()
            
            # Convert to list of dicts with proper formatting
            readings = []
            for row in results:
                # Use timestamp as-is
                ts = row['timestamp']
                    
                readings.append({
                    'id': row['id'],
                    'time': ts.isoformat() if ts else None,
                    'temp': float(row['temp']) if row['temp'] else None,
                    'rh': float(row['rh']) if row['rh'] else None,
                    'lux': float(row['lux']) if row['lux'] else None,
                    'irradiance': float(row['irradiance']) if row['irradiance'] else None,
                })
            
            logger.info(f"📊 Retrieved {len(readings)} readings for {date_str}")
            return readings
            
        except Exception as e:
            logger.error(f"❌ Failed to get readings by date: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def get_date_range(self) -> Dict[str, str]:
        """Get the earliest and latest dates with sensor data in Qatar time.
        
        Returns:
            Dict with 'min_date' and 'max_date' in YYYY-MM-DD format (Qatar time)
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Convert timestamps to Qatar time before extracting date
            cursor.execute("""
                SELECT 
                    MIN(timestamp AT TIME ZONE 'Asia/Qatar') as min_date,
                    MAX(timestamp AT TIME ZONE 'Asia/Qatar') as max_date
                FROM sensor_readings;
            """)
            
            row = cursor.fetchone()
            return {
                'min_date': row[0].strftime('%Y-%m-%d') if row[0] else None,
                'max_date': row[1].strftime('%Y-%m-%d') if row[1] else None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get date range: {e}")
            return {'min_date': None, 'max_date': None}
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def insert_kpi_snapshot(
        self,
        kpi_name: str,
        value: float,
        unit: str,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> int:
        """Insert a KPI snapshot for historical tracking"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if timestamp is None:
                timestamp = datetime.now()
            
            cursor.execute("""
                INSERT INTO kpi_snapshots (timestamp, kpi_name, value, unit, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (timestamp, kpi_name, value, unit, psycopg2.extras.Json(metadata or {})))
            
            record_id = cursor.fetchone()[0]
            conn.commit()
            
            return record_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Failed to insert KPI snapshot: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def get_kpi_history(
        self,
        kpi_name: str,
        hours: int = 24
    ) -> List[Dict]:
        """Get historical KPI values"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            start_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT timestamp, kpi_name, value, unit, metadata
                FROM kpi_snapshots
                WHERE kpi_name = %s AND timestamp >= %s
                ORDER BY timestamp ASC;
            """, (kpi_name, start_time))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Failed to get KPI history: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get total record count
            cursor.execute("SELECT COUNT(*) as total_readings FROM sensor_readings;")
            total_readings = cursor.fetchone()['total_readings']
            
            # Get oldest and newest timestamps
            cursor.execute("""
                SELECT 
                    MIN(timestamp) as oldest_reading,
                    MAX(timestamp) as newest_reading
                FROM sensor_readings;
            """)
            time_range = cursor.fetchone()
            
            # Get total KPI snapshots
            cursor.execute("SELECT COUNT(*) as total_kpis FROM kpi_snapshots;")
            total_kpis = cursor.fetchone()['total_kpis']
            
            return {
                'total_readings': total_readings,
                'oldest_reading': time_range['oldest_reading'],
                'newest_reading': time_range['newest_reading'],
                'total_kpi_snapshots': total_kpis
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {e}")
            return {}
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Delete data older than specified days (for data retention policy)"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Delete old sensor readings
            cursor.execute("""
                DELETE FROM sensor_readings
                WHERE timestamp < %s;
            """, (cutoff_date,))
            
            deleted_readings = cursor.rowcount
            
            # Delete old KPI snapshots
            cursor.execute("""
                DELETE FROM kpi_snapshots
                WHERE timestamp < %s;
            """, (cutoff_date,))
            
            deleted_kpis = cursor.rowcount
            
            conn.commit()
            logger.info(f"✅ Cleaned up {deleted_readings} old readings and {deleted_kpis} old KPI snapshots")
            
            return deleted_readings, deleted_kpis
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Failed to cleanup old data: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)


# Global database manager instance
db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        db_manager.initialize_schema()
    return db_manager


# Test connection function
def test_connection():
    """Test database connection and print statistics"""
    try:
        manager = get_db_manager()
        stats = manager.get_statistics()
        print("✅ Database connection successful!")
        print(f"📊 Statistics:")
        print(f"   Total readings: {stats.get('total_readings', 0)}")
        print(f"   Oldest reading: {stats.get('oldest_reading', 'N/A')}")
        print(f"   Newest reading: {stats.get('newest_reading', 'N/A')}")
        print(f"   Total KPI snapshots: {stats.get('total_kpi_snapshots', 0)}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test the connection
    test_connection()

import json
import pymysql
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any
from .models import Driver, Order, Market, AllocationResult

class MySQLDatabaseManager:
    """Manages connection and CRUD operations for Laragon MySQL database 'simulator'."""
    
    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "", database: str = "simulator"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    def get_connection(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )

    def init_db(self):
        """Create MySQL database tables if they do not exist."""
        # 1. Connect without DB first to ensure database 'simulator' exists
        conn_server = pymysql.connect(
            host=self.host, port=self.port, user=self.user, password=self.password, autocommit=True
        )
        try:
            with conn_server.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}` CHARACTER SET utf8mb4;")
        finally:
            conn_server.close()

        # 2. Create tables
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # drivers table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS drivers (
                    id VARCHAR(64) PRIMARY KEY,
                    lat DOUBLE NOT NULL,
                    lon DOUBLE NOT NULL,
                    service_types TEXT NOT NULL,
                    online TINYINT(1) NOT NULL DEFAULT 1,
                    acceptance_rate DOUBLE NOT NULL,
                    completion_rate DOUBLE NOT NULL,
                    online_hours DOUBLE NOT NULL,
                    online_days INT NOT NULL,
                    history_json TEXT,
                    account_status VARCHAR(32) NOT NULL DEFAULT 'active',
                    device_status VARCHAR(32) NOT NULL DEFAULT 'healthy',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)

                # orders table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id VARCHAR(64) PRIMARY KEY,
                    service_type VARCHAR(64) NOT NULL,
                    pickup_lat DOUBLE NOT NULL,
                    pickup_lon DOUBLE NOT NULL,
                    dest_lat DOUBLE NOT NULL,
                    dest_lon DOUBLE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    estimated_distance DOUBLE NOT NULL,
                    estimated_duration DOUBLE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)

                # allocations table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS allocations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    order_id VARCHAR(64) NOT NULL,
                    driver_id VARCHAR(64) NOT NULL,
                    score DOUBLE NOT NULL,
                    probability DOUBLE NOT NULL,
                    result VARCHAR(32) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_order (order_id),
                    INDEX idx_driver (driver_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
        finally:
            conn.close()

    def save_drivers(self, drivers: List[Driver]):
        """Save or update drivers into MySQL database."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                sql = """
                INSERT INTO drivers (
                    id, lat, lon, service_types, online, acceptance_rate, completion_rate,
                    online_hours, online_days, history_json, account_status, device_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    lat=VALUES(lat), lon=VALUES(lon), service_types=VALUES(service_types),
                    online=VALUES(online), acceptance_rate=VALUES(acceptance_rate),
                    completion_rate=VALUES(completion_rate), online_hours=VALUES(online_hours),
                    online_days=VALUES(online_days), history_json=VALUES(history_json),
                    account_status=VALUES(account_status), device_status=VALUES(device_status);
                """
                for d in drivers:
                    cur.execute(sql, (
                        d.id, d.location[0], d.location[1],
                        json.dumps(d.service_types), 1 if d.online else 0,
                        d.acceptance_rate, d.completion_rate,
                        d.online_hours, d.online_days,
                        json.dumps(d.history), d.account_status, d.device_status
                    ))
        finally:
            conn.close()

    def load_drivers(self) -> List[Driver]:
        """Load active drivers from MySQL database."""
        conn = self.get_connection()
        drivers = []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM drivers WHERE online = 1;")
                rows = cur.fetchall()
                for row in rows:
                    drivers.append(Driver(
                        id=row["id"],
                        location=(row["lat"], row["lon"]),
                        service_types=json.loads(row["service_types"]),
                        online=bool(row["online"]),
                        acceptance_rate=row["acceptance_rate"],
                        completion_rate=row["completion_rate"],
                        online_hours=row["online_hours"],
                        online_days=row["online_days"],
                        history=json.loads(row["history_json"]) if row["history_json"] else {},
                        account_status=row["account_status"],
                        device_status=row["device_status"]
                    ))
        finally:
            conn.close()
        return drivers

    def save_allocations(self, results: List[AllocationResult]):
        """Save simulation allocation results into MySQL database."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                sql = """
                INSERT INTO allocations (timestamp, order_id, driver_id, score, probability, result)
                VALUES (%s, %s, %s, %s, %s, %s);
                """
                for r in results:
                    cur.execute(sql, (
                        r.timestamp, r.order_id, r.driver_id,
                        r.score, r.probability, r.result
                    ))
        finally:
            conn.close()

    def query_allocations(self, limit: int = 100) -> pd.DataFrame:
        """Fetch latest allocation records into pandas DataFrame."""
        conn = self.get_connection()
        try:
            df = pd.read_sql(f"SELECT * FROM allocations ORDER BY id DESC LIMIT {limit};", conn)
        finally:
            conn.close()
        return df

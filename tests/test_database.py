import pytest
from src.database import MySQLDatabaseManager
from src.models import Driver, Order, AllocationResult

def test_mysql_database_manager_connection():
    db = MySQLDatabaseManager(host="localhost", port=3306, user="root", password="", database="simulator")
    
    # Try connecting to Laragon MySQL
    try:
        conn = db.get_connection()
        conn.close()
        can_connect = True
    except Exception as e:
        can_connect = False
        
    if not can_connect:
        pytest.skip("Laragon MySQL database server is not running locally.")

    # Initialize tables
    db.init_db()
    
    # Test saving & loading drivers
    test_driver = Driver(
        id="D_TEST_001",
        location=(-6.9147, 107.6098),
        service_types=["GoRide", "GoFood"],
        online=True,
        acceptance_rate=0.98,
        completion_rate=0.99,
        online_hours=60.0,
        online_days=10,
        history={"services": {"GoRide": 15}},
        account_status="active",
        device_status="healthy"
    )
    
    db.save_drivers([test_driver])
    loaded_drivers = db.load_drivers()
    assert any(d.id == "D_TEST_001" for d in loaded_drivers)
    
    # Test saving allocations
    alloc = AllocationResult("2026-08-11 12:00:00", "O_TEST_001", "D_TEST_001", 88.5, 0.45, "allocated")
    db.save_allocations([alloc])
    
    df_alloc = db.query_allocations(limit=10)
    assert len(df_alloc) > 0

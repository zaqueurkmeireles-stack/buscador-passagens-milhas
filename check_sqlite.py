import sqlite3
import os

db_path = "travel_agent.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in SQLite:")
    for table in tables:
        print(table[0])
    conn.close()
else:
    print("SQLite DB not found.")

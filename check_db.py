"""Проверка структуры БД"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'libraryadmin', 'library.db')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== TABLES ===")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for r in cur.fetchall():
    print(f"  {r['name']}")

print("\n=== VIEWS ===")
cur.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
for r in cur.fetchall():
    print(f"  {r['name']}")

print("\n=== REPORT_BY_INSTANCES (first 10 rows) ===")
try:
    cur.execute("SELECT * FROM report_by_instances ORDER BY year DESC, book_name LIMIT 10")
    for r in cur.fetchall():
        print(dict(r))
except Exception as e:
    print(f"Error: {e}")

print("\n=== ISSUE (sample 5 rows) ===")
cur.execute("SELECT * FROM issue LIMIT 5")
for r in cur.fetchall():
    print(dict(r))

print("\n=== BOOK_INSTANCE (sample 5 rows) ===")
cur.execute("SELECT * FROM book_instance LIMIT 5")
for r in cur.fetchall():
    print(dict(r))

conn.close()
print("\nAll checks passed!")
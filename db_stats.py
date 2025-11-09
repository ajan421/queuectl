#!/usr/bin/env python3
"""Quick database statistics for QueueCTL."""

import sqlite3
from pathlib import Path

db_path = Path.home() / '.queuectl' / 'jobs.db'

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    print("Run queuectl commands first to create the database.")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("QueueCTL Database Statistics")
print("=" * 40)

# Job counts by state
cursor.execute('SELECT state, COUNT(*) FROM jobs GROUP BY state ORDER BY COUNT(*) DESC')
results = cursor.fetchall()
print("Job counts by state:")
for state, count in results:
    print(f"  {state}: {count}")

# Recent jobs
cursor.execute('SELECT id, state, attempts, created_at FROM jobs ORDER BY created_at DESC LIMIT 5')
jobs = cursor.fetchall()
print(f"\nRecent jobs (last {len(jobs)}):")
for job in jobs:
    created = job[3][:19]  # Truncate timestamp
    print(f"  {job[0]} - {job[1]} - attempts: {job[2]} - {created}")

# Total jobs
cursor.execute('SELECT COUNT(*) FROM jobs')
total = cursor.fetchone()[0]
print(f"\nTotal jobs in database: {total}")

conn.close()
print("\nTip: Use 'python view_db.py' for full database inspection")

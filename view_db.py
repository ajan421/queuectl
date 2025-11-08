#!/usr/bin/env python3
"""Quick script to view the QueueCTL database."""

import sqlite3
from pathlib import Path
import json

db_path = Path.home() / '.queuectl' / 'jobs.db'

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    print("Run queuectl commands first to create the database.")
    exit(1)

print(f"Database location: {db_path}\n")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Show tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:")
for table in tables:
    print(f"  - {table[0]}")

# Show schema
print("\n" + "="*60)
print("Jobs Table Schema:")
print("="*60)
cursor.execute("PRAGMA table_info(jobs)")
columns = cursor.fetchall()
for col in columns:
    nullable = "NULL" if col[3] == 0 else "NOT NULL"
    default = f" DEFAULT {col[4]}" if col[4] else ""
    print(f"  {col[1]:20} {col[2]:10} {nullable}{default}")

# Show indexes
print("\n" + "="*60)
print("Indexes:")
print("="*60)
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='jobs'")
indexes = cursor.fetchall()
for idx in indexes:
    print(f"  {idx[0]}")

# Show all jobs
print("\n" + "="*60)
print("All Jobs:")
print("="*60)
cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
rows = cursor.fetchall()
column_names = [description[0] for description in cursor.description]

if rows:
    print(f"\nFound {len(rows)} job(s):\n")
    for row in rows:
        job = dict(zip(column_names, row))
        print(f"ID: {job['id']}")
        print(f"  Command: {job['command']}")
        print(f"  State: {job['state']}")
        print(f"  Attempts: {job['attempts']}/{job['max_retries']}")
        print(f"  Created: {job['created_at']}")
        if job.get('next_retry_at'):
            print(f"  Next Retry: {job['next_retry_at']}")
        if job.get('worker_id'):
            print(f"  Worker ID: {job['worker_id']}")
        print()
else:
    print("No jobs in database.")

conn.close()


"""Storage layer for QueueCTL using SQLite."""

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .utils import get_current_timestamp


class Storage:
    """Manages job storage in SQLite database."""
    
    def __init__(self, db_path: str = None):
        """Initialize storage.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.queuectl/jobs.db
        """
        if db_path is None:
            db_dir = Path.home() / ".queuectl"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "jobs.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                next_retry_at TEXT,
                worker_id TEXT,
                priority INTEGER NOT NULL DEFAULT 0,
                run_at TEXT,
                timeout INTEGER,
                last_output TEXT,
                duration_ms INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                state TEXT NOT NULL,
                success INTEGER NOT NULL,
                attempts INTEGER NOT NULL,
                duration_ms INTEGER,
                output TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Ensure additional columns exist (for upgrades)
        cursor.execute('PRAGMA table_info(jobs)')
        existing_columns = {row[1] for row in cursor.fetchall()}
        columns_to_add = {
            "priority": "INTEGER NOT NULL DEFAULT 0",
            "run_at": "TEXT",
            "timeout": "INTEGER",
            "last_output": "TEXT",
            "duration_ms": "INTEGER"
        }
        for column, definition in columns_to_add.items():
            if column not in existing_columns:
                cursor.execute(f'ALTER TABLE jobs ADD COLUMN {column} {definition}')
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_state ON jobs(state)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_next_retry ON jobs(next_retry_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_priority ON jobs(priority)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_run_at ON jobs(run_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_logs_created_at ON job_logs(created_at)')
        
        conn.commit()
        conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_job(self, job_data: Dict[str, Any]) -> bool:
        """Create a new job."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = get_current_timestamp()
        
        try:
            cursor.execute('''
                INSERT INTO jobs (id, command, state, attempts, max_retries, created_at,
                                  updated_at, next_retry_at, worker_id, priority, run_at,
                                  timeout, last_output, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data['id'],
                job_data['command'],
                job_data.get('state', 'pending'),
                job_data.get('attempts', 0),
                job_data.get('max_retries', 3),
                job_data.get('created_at', now),
                job_data.get('updated_at', now),
                job_data.get('next_retry_at'),
                job_data.get('worker_id'),
                job_data.get('priority', 0),
                job_data.get('run_at'),
                job_data.get('timeout'),
                job_data.get('last_output'),
                job_data.get('duration_ms')
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    
    def update_job(self, job_id: str, updates: Dict[str, Any]):
        """Update job fields."""
        conn = self._get_connection()
        cursor = conn.cursor()
        updates = updates.copy()
        updates['updated_at'] = get_current_timestamp()
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [job_id]
        cursor.execute(f'UPDATE jobs SET {set_clause} WHERE id = ?', values)
        conn.commit()
        conn.close()
    
    def list_jobs(self, state: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List jobs, optionally filtered by state."""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = 'SELECT * FROM jobs'
        params: List[Any] = []
        if state:
            query += ' WHERE state = ?'
            params.append(state)
        query += ' ORDER BY priority DESC, run_at IS NOT NULL, run_at ASC, created_at DESC'
        if limit:
            query += f' LIMIT {int(limit)}'
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def _lock_job(self, cursor: sqlite3.Cursor, job_id: str, current_state: str, worker_id: str, now: str) -> Optional[Dict[str, Any]]:
        """Attempt to lock a job for processing."""
        cursor.execute('''
            UPDATE jobs
            SET state = 'processing', worker_id = ?, updated_at = ?
            WHERE id = ? AND state = ?
        ''', (worker_id, now, job_id, current_state))
        if cursor.rowcount > 0:
            cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        return None
    
    def get_pending_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get and lock a pending job that is ready for execution."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = get_current_timestamp()
        
        cursor.execute('''
            SELECT * FROM jobs
            WHERE state = 'pending'
              AND (run_at IS NULL OR run_at <= ?)
              AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY priority DESC, run_at IS NOT NULL, run_at ASC, created_at ASC
            LIMIT 1
        ''', (now, now))
        row = cursor.fetchone()
        if row:
            job_id = row['id']
            locked_job = self._lock_job(cursor, job_id, 'pending', worker_id, now)
            if locked_job:
                conn.commit()
                conn.close()
                return locked_job
        conn.commit()
        conn.close()
        return None
    
    def get_failed_job_ready_for_retry(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get and lock a failed job that's ready for retry."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = get_current_timestamp()
        
        cursor.execute('''
            SELECT * FROM jobs
            WHERE state = 'failed'
              AND next_retry_at IS NOT NULL
              AND next_retry_at <= ?
            ORDER BY priority DESC, next_retry_at ASC
            LIMIT 1
        ''', (now,))
        row = cursor.fetchone()
        if row:
            job_id = row['id']
            locked_job = self._lock_job(cursor, job_id, 'failed', worker_id, now)
            if locked_job:
                conn.commit()
                conn.close()
                return locked_job
        conn.commit()
        conn.close()
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about job states."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT state, COUNT(*) as count FROM jobs GROUP BY state')
        rows = cursor.fetchall()
        conn.close()
        stats = {row['state']: row['count'] for row in rows}
        return stats
    
    def get_metrics(self) -> Dict[str, Any]:
        """Compute metrics for dashboard/CLI."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        metrics: Dict[str, Any] = {}
        cursor.execute('SELECT COUNT(*) FROM jobs')
        metrics['total_jobs'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE state = 'completed'")
        metrics['completed_jobs'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE state = 'failed'")
        metrics['failed_jobs'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE state = 'dead'")
        metrics['dead_jobs'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE state = 'pending'")
        metrics['pending_jobs'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(duration_ms) FROM job_logs WHERE duration_ms IS NOT NULL")
        avg_duration = cursor.fetchone()[0]
        metrics['average_duration_ms'] = round(avg_duration, 2) if avg_duration is not None else None
        
        cursor.execute("SELECT MAX(created_at) FROM job_logs WHERE success = 1")
        metrics['last_success_at'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(created_at) FROM job_logs WHERE success = 0")
        metrics['last_failure_at'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT job_id, state, success, attempts, duration_ms, created_at
            FROM job_logs
            ORDER BY created_at DESC
            LIMIT 10
        """)
        metrics['recent_logs'] = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT job_id, command, priority, run_at, state, attempts, last_output, updated_at
            FROM jobs
            WHERE state IN ('pending', 'failed')
            ORDER BY priority DESC, run_at IS NOT NULL, run_at ASC, created_at ASC
            LIMIT 10
        """)
        metrics['queue_snapshot'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return metrics
    
    def log_job_execution(self, job_id: str, state: str, success: bool, attempts: int,
                          duration_ms: Optional[int], output: Optional[str]):
        """Record job execution details in job_logs table."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO job_logs (job_id, state, success, attempts, duration_ms, output, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, state, 1 if success else 0, attempts, duration_ms, output, get_current_timestamp()))
        conn.commit()
        conn.close()
    
    def get_recent_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent execution logs."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM job_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


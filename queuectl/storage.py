"""Storage layer for QueueCTL using SQLite."""

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


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
                worker_id TEXT
            )
        ''')
        
        # Create index on state for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_state ON jobs(state)
        ''')
        
        # Create index on next_retry_at for retry scheduling
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_next_retry ON jobs(next_retry_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_job(self, job_data: Dict[str, Any]) -> bool:
        """Create a new job.
        
        Args:
            job_data: Dictionary containing job fields
            
        Returns:
            True if successful, False if job ID already exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO jobs (id, command, state, attempts, max_retries, 
                                created_at, updated_at, next_retry_at, worker_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data['id'],
                job_data['command'],
                job_data.get('state', 'pending'),
                job_data.get('attempts', 0),
                job_data.get('max_retries', 3),
                job_data.get('created_at', datetime.utcnow().isoformat() + 'Z'),
                job_data.get('updated_at', datetime.utcnow().isoformat() + 'Z'),
                job_data.get('next_retry_at'),
                job_data.get('worker_id')
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
        
        # Always update updated_at
        updates['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [job_id]
        
        cursor.execute(f'UPDATE jobs SET {set_clause} WHERE id = ?', values)
        conn.commit()
        conn.close()
    
    def list_jobs(self, state: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List jobs, optionally filtered by state."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if state:
            cursor.execute('SELECT * FROM jobs WHERE state = ? ORDER BY created_at DESC', (state,))
        else:
            cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        jobs = [dict(row) for row in rows]
        
        if limit:
            jobs = jobs[:limit]
        
        return jobs
    
    def get_pending_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get and lock a pending job for processing.
        
        Uses database-level locking to prevent race conditions.
        Returns the first pending job that's ready to be processed
        (either has no next_retry_at or next_retry_at is in the past).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Try to get a pending job that's ready to be processed
        # Use a transaction to ensure atomicity
        now = datetime.utcnow().isoformat() + 'Z'
        
        cursor.execute('''
            SELECT * FROM jobs 
            WHERE state = 'pending' 
            AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY created_at ASC
            LIMIT 1
        ''', (now,))
        
        row = cursor.fetchone()
        
        if row:
            job_id = row['id']
            # Lock the job by updating state and worker_id atomically
            cursor.execute('''
                UPDATE jobs 
                SET state = 'processing', worker_id = ?, updated_at = ?
                WHERE id = ? AND state = 'pending'
            ''', (worker_id, now, job_id))
            
            if cursor.rowcount > 0:
                conn.commit()
                # Fetch the updated job
                cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
                updated_row = cursor.fetchone()
                conn.close()
                return dict(updated_row)
            else:
                # Job was already taken by another worker
                conn.close()
                return None
        
        conn.close()
        return None
    
    def get_failed_job_ready_for_retry(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get and lock a failed job that's ready for retry."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat() + 'Z'
        
        cursor.execute('''
            SELECT * FROM jobs 
            WHERE state = 'failed' 
            AND next_retry_at IS NOT NULL
            AND next_retry_at <= ?
            ORDER BY next_retry_at ASC
            LIMIT 1
        ''', (now,))
        
        row = cursor.fetchone()
        
        if row:
            job_id = row['id']
            cursor.execute('''
                UPDATE jobs 
                SET state = 'processing', worker_id = ?, updated_at = ?
                WHERE id = ? AND state = 'failed'
            ''', (worker_id, now, job_id))
            
            if cursor.rowcount > 0:
                conn.commit()
                cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
                updated_row = cursor.fetchone()
                conn.close()
                return dict(updated_row)
            else:
                conn.close()
                return None
        
        conn.close()
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about job states."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT state, COUNT(*) as count 
            FROM jobs 
            GROUP BY state
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        stats = {row['state']: row['count'] for row in rows}
        return stats
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted


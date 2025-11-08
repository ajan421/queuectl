"""Job manager for QueueCTL."""

from typing import Dict, Any, List, Optional
from .storage import Storage
from .config import Config
from .utils import get_current_timestamp, calculate_next_retry_time


class JobManager:
    """Manages job lifecycle and operations."""
    
    VALID_STATES = ['pending', 'processing', 'completed', 'failed', 'dead']
    
    def __init__(self, storage: Storage = None, config: Config = None):
        """Initialize job manager.
        
        Args:
            storage: Storage instance (creates default if None)
            config: Config instance (creates default if None)
        """
        self.storage = storage or Storage()
        self.config = config or Config()
    
    def enqueue(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enqueue a new job.
        
        Args:
            job_data: Dictionary with job fields (id, command, etc.)
            
        Returns:
            Created job dictionary
            
        Raises:
            ValueError: If job data is invalid
        """
        # Validate required fields
        if 'id' not in job_data:
            raise ValueError("Job must have an 'id' field")
        if 'command' not in job_data:
            raise ValueError("Job must have a 'command' field")
        
        # Set defaults
        job_data.setdefault('state', 'pending')
        job_data.setdefault('attempts', 0)
        job_data.setdefault('max_retries', self.config.get('max_retries', 3))
        job_data.setdefault('created_at', get_current_timestamp())
        job_data.setdefault('updated_at', get_current_timestamp())
        
        # Validate state
        if job_data['state'] not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {job_data['state']}")
        
        # Create job in storage
        success = self.storage.create_job(job_data)
        if not success:
            raise ValueError(f"Job with id '{job_data['id']}' already exists")
        
        return self.storage.get_job(job_data['id'])
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        return self.storage.get_job(job_id)
    
    def list_jobs(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """List jobs, optionally filtered by state."""
        if state and state not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {state}")
        
        return self.storage.list_jobs(state=state)
    
    def mark_completed(self, job_id: str):
        """Mark job as completed."""
        self.storage.update_job(job_id, {
            'state': 'completed',
            'worker_id': None
        })
    
    def mark_failed(self, job_id: str, worker_id: str = None) -> bool:
        """Mark job as failed and handle retry logic.
        
        Args:
            job_id: Job ID
            worker_id: Worker ID (optional)
            
        Returns:
            True if job should be retried, False if moved to DLQ
        """
        job = self.storage.get_job(job_id)
        if not job:
            return False
        
        attempts = job['attempts'] + 1
        max_retries = job.get('max_retries', self.config.get('max_retries', 3))
        
        if attempts >= max_retries:
            # Move to DLQ
            self.storage.update_job(job_id, {
                'state': 'dead',
                'attempts': attempts,
                'worker_id': None
            })
            return False
        else:
            # Schedule retry with exponential backoff
            backoff_base = self.config.get('backoff_base', 2)
            next_retry_at = calculate_next_retry_time(attempts, backoff_base)
            
            self.storage.update_job(job_id, {
                'state': 'failed',
                'attempts': attempts,
                'next_retry_at': next_retry_at,
                'worker_id': None
            })
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status including job counts and configuration."""
        stats = self.storage.get_stats()
        
        # Ensure all states are represented
        status = {
            'pending': stats.get('pending', 0),
            'processing': stats.get('processing', 0),
            'completed': stats.get('completed', 0),
            'failed': stats.get('failed', 0),
            'dead': stats.get('dead', 0),
        }
        
        return {
            'jobs': status,
            'total': sum(status.values()),
            'config': self.config.get_all()
        }
    
    def retry_dead_job(self, job_id: str) -> bool:
        """Retry a dead job by resetting it to pending.
        
        Args:
            job_id: Job ID to retry
            
        Returns:
            True if successful, False if job not found or not in dead state
        """
        job = self.storage.get_job(job_id)
        if not job or job['state'] != 'dead':
            return False
        
        self.storage.update_job(job_id, {
            'state': 'pending',
            'attempts': 0,
            'next_retry_at': None,
            'worker_id': None
        })
        return True


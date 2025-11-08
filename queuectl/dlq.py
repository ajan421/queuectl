"""Dead Letter Queue (DLQ) manager for QueueCTL."""

from typing import List, Dict, Any
from .storage import Storage
from .job_manager import JobManager


class DLQManager:
    """Manages Dead Letter Queue operations."""
    
    def __init__(self, storage: Storage = None):
        """Initialize DLQ manager.
        
        Args:
            storage: Storage instance (creates default if None)
        """
        self.storage = storage or Storage()
        self.job_manager = JobManager(self.storage)
    
    def list_dead_jobs(self) -> List[Dict[str, Any]]:
        """List all jobs in the Dead Letter Queue."""
        return self.storage.list_jobs(state='dead')
    
    def retry_job(self, job_id: str) -> bool:
        """Retry a dead job by moving it back to pending.
        
        Args:
            job_id: Job ID to retry
            
        Returns:
            True if successful, False if job not found or not in dead state
        """
        return self.job_manager.retry_dead_job(job_id)
    
    def get_dead_job(self, job_id: str) -> Dict[str, Any]:
        """Get a dead job by ID."""
        job = self.storage.get_job(job_id)
        if job and job['state'] == 'dead':
            return job
        return None


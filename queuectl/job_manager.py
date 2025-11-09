"""Job manager for QueueCTL."""

from typing import Dict, Any, List, Optional
from .storage import Storage
from .config import Config
from .utils import get_current_timestamp, calculate_next_retry_time, normalize_timestamp


class JobManager:
    """Manages job lifecycle and operations."""
    
    VALID_STATES = ['pending', 'processing', 'completed', 'failed', 'dead']
    
    def __init__(self, storage: Storage = None, config: Config = None):
        self.storage = storage or Storage()
        self.config = config or Config()
    
    def enqueue(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enqueue a new job."""
        if 'id' not in job_data:
            raise ValueError("Job must have an 'id' field")
        if 'command' not in job_data:
            raise ValueError("Job must have a 'command' field")
        
        job_data = job_data.copy()
        current_ts = get_current_timestamp()
        job_data.setdefault('state', 'pending')
        job_data.setdefault('attempts', 0)
        job_data.setdefault('max_retries', self.config.get('max_retries', 3))
        job_data.setdefault('created_at', current_ts)
        job_data.setdefault('updated_at', current_ts)
        job_data.setdefault('next_retry_at', None)
        job_data.setdefault('worker_id', None)
        job_data.setdefault('last_output', None)
        job_data.setdefault('duration_ms', None)
        
        # Normalize optional fields
        try:
            job_data['priority'] = int(job_data.get('priority', self.config.get('default_priority', 0)))
        except (TypeError, ValueError) as exc:
            raise ValueError("priority must be an integer") from exc
        
        if 'run_at' in job_data and job_data['run_at'] is not None:
            job_data['run_at'] = normalize_timestamp(job_data['run_at'])
        
        timeout_default = self.config.get('default_timeout', 3600)
        try:
            job_data['timeout'] = int(job_data.get('timeout', timeout_default))
        except (TypeError, ValueError) as exc:
            raise ValueError("timeout must be an integer") from exc
        
        if job_data['timeout'] <= 0:
            raise ValueError("timeout must be greater than zero")
        
        job_data['max_retries'] = int(job_data['max_retries'])
        job_data['attempts'] = int(job_data['attempts'])
        
        if job_data['state'] not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {job_data['state']}")
        
        success = self.storage.create_job(job_data)
        if not success:
            raise ValueError(f"Job with id '{job_data['id']}' already exists")
        
        return self.storage.get_job(job_data['id'])
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.storage.get_job(job_id)
    
    def list_jobs(self, state: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if state and state not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {state}")
        return self.storage.list_jobs(state=state, limit=limit)
    
    def mark_completed(self, job: Dict[str, Any], output: Optional[str] = None,
                       duration_ms: Optional[int] = None):
        """Mark job as completed and record execution details."""
        job_id = job['id']
        self.storage.update_job(job_id, {
            'state': 'completed',
            'worker_id': None,
            'next_retry_at': None,
            'last_output': output,
            'duration_ms': duration_ms,
            'run_at': None
        })
        self.storage.log_job_execution(
            job_id=job_id,
            state='completed',
            success=True,
            attempts=job.get('attempts', 0),
            duration_ms=duration_ms,
            output=output
        )
    
    def mark_failed(self, job: Dict[str, Any], worker_id: Optional[str],
                    output: Optional[str], duration_ms: Optional[int],
                    error_message: Optional[str] = None) -> bool:
        """Mark job as failed and handle retry logic."""
        job_id = job['id']
        attempts = int(job.get('attempts', 0)) + 1
        max_retries = int(job.get('max_retries', self.config.get('max_retries', 3)))
        combined_output = output or ''
        if error_message:
            combined_output = f"{combined_output}\n{error_message}".strip()
        
        if attempts >= max_retries:
            self.storage.update_job(job_id, {
                'state': 'dead',
                'attempts': attempts,
                'worker_id': None,
                'next_retry_at': None,
                'last_output': combined_output,
                'duration_ms': duration_ms,
                'run_at': None
            })
            self.storage.log_job_execution(
                job_id=job_id,
                state='dead',
                success=False,
                attempts=attempts,
                duration_ms=duration_ms,
                output=combined_output
            )
            return False
        else:
            backoff_base = self.config.get('backoff_base', 2)
            next_retry_at = calculate_next_retry_time(attempts, backoff_base)
            self.storage.update_job(job_id, {
                'state': 'failed',
                'attempts': attempts,
                'next_retry_at': next_retry_at,
                'worker_id': None,
                'last_output': combined_output,
                'duration_ms': duration_ms
            })
            self.storage.log_job_execution(
                job_id=job_id,
                state='failed',
                success=False,
                attempts=attempts,
                duration_ms=duration_ms,
                output=combined_output
            )
            return True
    
    def get_status(self) -> Dict[str, Any]:
        stats = self.storage.get_stats()
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
    
    def get_metrics(self) -> Dict[str, Any]:
        return self.storage.get_metrics()
    
    def retry_dead_job(self, job_id: str) -> bool:
        job = self.storage.get_job(job_id)
        if not job or job['state'] != 'dead':
            return False
        self.storage.update_job(job_id, {
            'state': 'pending',
            'attempts': 0,
            'next_retry_at': None,
            'worker_id': None,
            'run_at': None
        })
        return True


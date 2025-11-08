"""Worker process for QueueCTL."""

import subprocess
import signal
import sys
import os
import time
from typing import Optional
from .storage import Storage
from .config import Config
from .job_manager import JobManager


class Worker:
    """Worker process that executes jobs."""
    
    def __init__(self, worker_id: str, storage: Storage = None, config: Config = None):
        """Initialize worker.
        
        Args:
            worker_id: Unique identifier for this worker
            storage: Storage instance
            config: Config instance
        """
        self.worker_id = worker_id
        self.storage = storage or Storage()
        self.config = config or Config()
        self.job_manager = JobManager(self.storage, self.config)
        self.running = False
        self.current_job: Optional[dict] = None
        self.shutdown_requested = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.shutdown_requested = True
        if self.current_job:
            print(f"\n[Worker {self.worker_id}] Shutdown requested, finishing current job...")
    
    def _execute_command(self, command: str):
        """Execute a shell command.
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                check=False
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            return success, output.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 1 hour"
        except Exception as e:
            return False, f"Execution error: {str(e)}"
    
    def _process_job(self, job: dict):
        """Process a single job."""
        job_id = job['id']
        command = job['command']
        
        print(f"[Worker {self.worker_id}] Processing job {job_id}: {command}")
        
        success, output = self._execute_command(command)
        
        if success:
            self.job_manager.mark_completed(job_id)
            print(f"[Worker {self.worker_id}] Job {job_id} completed successfully")
        else:
            should_retry = self.job_manager.mark_failed(job_id, self.worker_id)
            if should_retry:
                attempts = job['attempts'] + 1
                print(f"[Worker {self.worker_id}] Job {job_id} failed (attempt {attempts}), will retry")
            else:
                print(f"[Worker {self.worker_id}] Job {job_id} failed permanently, moved to DLQ")
    
    def _get_next_job(self) -> Optional[dict]:
        """Get next available job to process."""
        # First try to get a pending job
        job = self.storage.get_pending_job(self.worker_id)
        if job:
            return job
        
        # Then try to get a failed job ready for retry
        job = self.storage.get_failed_job_ready_for_retry(self.worker_id)
        if job:
            return job
        
        return None
    
    def run(self):
        """Main worker loop."""
        self.running = True
        poll_interval = self.config.get('poll_interval', 1)
        
        print(f"[Worker {self.worker_id}] Started")
        
        while self.running and not self.shutdown_requested:
            try:
                job = self._get_next_job()
                
                if job:
                    self.current_job = job
                    self._process_job(job)
                    self.current_job = None
                else:
                    # No jobs available, wait before polling again
                    time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                self.shutdown_requested = True
                break
            except Exception as e:
                print(f"[Worker {self.worker_id}] Error: {e}", file=sys.stderr)
                if self.current_job:
                    # Mark current job as failed if we have an error
                    try:
                        self.job_manager.mark_failed(self.current_job['id'], self.worker_id)
                    except:
                        pass
                    self.current_job = None
                time.sleep(poll_interval)
        
        # Finish current job if shutdown was requested
        if self.current_job and not self.shutdown_requested:
            self._process_job(self.current_job)
        
        print(f"[Worker {self.worker_id}] Stopped")
        self.running = False


def start_worker_process(worker_id: str, storage_path: str = None, config_path: str = None):
    """Start a worker process (entry point for multiprocessing)."""
    storage = Storage(storage_path) if storage_path else Storage()
    config = Config(config_path) if config_path else Config()
    
    worker = Worker(worker_id, storage, config)
    worker.run()


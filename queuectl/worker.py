"""Worker process for QueueCTL."""

import subprocess
import signal
import sys
import os
import time
from typing import Optional, Tuple
from .storage import Storage
from .config import Config
from .job_manager import JobManager


class Worker:
    """Worker process that executes jobs."""
    
    def __init__(self, worker_id: str, storage: Storage = None, config: Config = None):
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
        self.shutdown_requested = True
        if self.current_job:
            print(f"\n[Worker {self.worker_id}] Shutdown requested, finishing current job...")
    
    def _execute_command(self, command: str, timeout: int) -> Tuple[bool, str, Optional[int]]:
        """Execute a shell command with timeout and capture output."""
        start_time = time.perf_counter()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output = (result.stdout or "") + (result.stderr or "")
            success = result.returncode == 0
            return success, output.strip(), duration_ms
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output = (exc.stdout or "") + (exc.stderr or "")
            message = f"Command timed out after {timeout} seconds"
            if output.strip():
                message = f"{message}\n{output.strip()}"
            return False, message, duration_ms
        except Exception as exc:  # pragma: no cover - rare execution error
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return False, f"Execution error: {exc}", duration_ms
    
    def _process_job(self, job: dict):
        job_id = job['id']
        command = job['command']
        priority = job.get('priority', 0)
        run_at = job.get('run_at')
        job_timeout = job.get('timeout') or self.config.get('default_timeout', 3600)
        
        print(f"[Worker {self.worker_id}] Processing job {job_id} (priority={priority}, timeout={job_timeout}s): {command}")
        
        success, output, duration_ms = self._execute_command(command, job_timeout)
        
        if success:
            self.job_manager.mark_completed(job, output, duration_ms)
            duration_text = f" in {duration_ms} ms" if duration_ms is not None else ""
            print(f"[Worker {self.worker_id}] Job {job_id} completed successfully{duration_text}")
        else:
            should_retry = self.job_manager.mark_failed(job, self.worker_id, output, duration_ms)
            job['attempts'] = int(job.get('attempts', 0)) + 1
            if should_retry:
                print(f"[Worker {self.worker_id}] Job {job_id} failed (attempt {job['attempts']}), will retry")
            else:
                print(f"[Worker {self.worker_id}] Job {job_id} failed permanently, moved to DLQ")
    
    def _get_next_job(self) -> Optional[dict]:
        job = self.storage.get_pending_job(self.worker_id)
        if job:
            return job
        return self.storage.get_failed_job_ready_for_retry(self.worker_id)
    
    def run(self):
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
                    time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                self.shutdown_requested = True
                break
            except Exception as exc:
                print(f"[Worker {self.worker_id}] Error: {exc}", file=sys.stderr)
                if self.current_job:
                    try:
                        self.job_manager.mark_failed(self.current_job, self.worker_id, str(exc), None)
                    except Exception:  # pragma: no cover - best effort
                        pass
                    self.current_job = None
                time.sleep(poll_interval)
        
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


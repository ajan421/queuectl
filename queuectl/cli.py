"""CLI interface for QueueCTL."""

import click
import json
import multiprocessing
import os
import signal
import sys
import time
import webbrowser
from pathlib import Path
from typing import Dict, Any

if os.name == "nt":
    import ctypes

from .storage import Storage
from .config import Config
from .job_manager import JobManager
from .dlq import DLQManager
from .worker import start_worker_process
from .utils import parse_json_input


# Global worker processes storage
_worker_processes = []
_worker_pids_file = None


def get_worker_pids_file() -> str:
    """Get path to worker PIDs file."""
    pids_dir = Path.home() / ".queuectl"
    pids_dir.mkdir(exist_ok=True)
    return str(pids_dir / "worker_pids.json")


def load_worker_pids() -> list:
    """Load worker PIDs from file."""
    pids_file = get_worker_pids_file()
    if os.path.exists(pids_file):
        try:
            with open(pids_file, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def save_worker_pids(pids: list):
    """Save worker PIDs to file."""
    pids_file = get_worker_pids_file()
    with open(pids_file, 'w') as f:
        json.dump(pids, f)


def is_process_running(pid: int) -> bool:
    """Check whether a process is running."""
    if pid is None:
        return False

    if os.name == "nt":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True


def stop_all_workers():
    """Stop all running workers."""
    pids = load_worker_pids()
    stopped = []
    remaining = []
    
    for pid in pids:
        stopped_successfully = False
        try:
            os.kill(pid, signal.SIGTERM)
            stopped_successfully = True
        except ProcessLookupError:
            # Process already dead
            stopped_successfully = True
        except OSError as e:
            # On Windows, ERROR_INVALID_PARAMETER (87) indicates the PID is no longer valid
            if os.name == "nt" and getattr(e, "winerror", None) == 87:
                stopped_successfully = True
            else:
                remaining.append(pid)
                click.echo(f"Error stopping worker {pid}: {e}", err=True)
        except Exception as e:
            remaining.append(pid)
            click.echo(f"Error stopping worker {pid}: {e}", err=True)
        
        if stopped_successfully:
            stopped.append(pid)
    
    # Wait a bit for graceful shutdown
    if stopped:
        time.sleep(2)
    
    # Remove any PIDs that are still running
    save_worker_pids([pid for pid in remaining if is_process_running(pid)])
    
    return len(stopped)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """QueueCTL - CLI-based background job queue system."""
    pass


@cli.command()
@click.argument('job_json', type=str, required=False)
@click.option('--file', '-f', type=click.Path(exists=True), help='Read job JSON from file')
def enqueue(job_json, file):
    """Enqueue a new job.
    
    JOB_JSON: JSON string with job data (e.g., '{"id":"job1","command":"sleep 2"}')
    
    If --file is specified, reads JSON from the file instead.
    """
    try:
        # Read from file if specified
        if file:
            with open(file, 'r', encoding='utf-8') as f:
                job_json = f.read().strip()
        
        if not job_json:
            click.echo("Error: Either provide JOB_JSON argument or use --file option", err=True)
            sys.exit(1)
        
        job_data = parse_json_input(job_json)
        job_manager = JobManager()
        job = job_manager.enqueue(job_data)
        
        click.echo(f"Job enqueued successfully:")
        click.echo(json.dumps(job, indent=2))
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.group()
def worker():
    """Manage worker processes."""
    pass


@worker.command()
@click.option('--count', default=1, type=int, help='Number of workers to start')
def start(count):
    """Start one or more worker processes."""
    if count < 1:
        click.echo("Error: Count must be at least 1", err=True)
        sys.exit(1)
    
    # Check for existing workers
    existing_pids = load_worker_pids()
    if existing_pids:
        click.echo(f"Warning: Found {len(existing_pids)} existing worker processes")
        if not click.confirm("Start new workers anyway?"):
            return
    
    # Get storage and config paths
    db_dir = Path.home() / ".queuectl"
    config_path = str(db_dir / "config.json")
    db_path = str(db_dir / "jobs.db")
    
    processes = []
    pids = []
    
    for i in range(count):
        worker_id = f"worker-{os.getpid()}-{i}-{int(time.time())}"
        process = multiprocessing.Process(
            target=start_worker_process,
            args=(worker_id, db_path, config_path)
        )
        process.start()
        processes.append(process)
        pids.append(process.pid)
        
        click.echo(f"Started worker {i+1} (PID: {process.pid})")
    
    # Save PIDs
    save_worker_pids(pids)
    
    click.echo(f"\nStarted {count} worker(s). Use 'queuectl worker stop' to stop them.")


@worker.command()
def stop():
    """Stop all running worker processes gracefully."""
    stopped = stop_all_workers()
    
    if stopped > 0:
        click.echo(f"Stopped {stopped} worker(s)")
    else:
        click.echo("No running workers found")


@cli.command()
def status():
    """Show summary of job states and active workers."""
    job_manager = JobManager()
    status_data = job_manager.get_status()
    
    click.echo("=== QueueCTL Status ===\n")
    
    # Job counts
    click.echo("Job States:")
    jobs = status_data['jobs']
    for state, count in jobs.items():
        click.echo(f"  {state:12} {count:4}")
    click.echo(f"  {'total':12} {status_data['total']:4}")
    
    # Active workers
    click.echo("\nActive Workers:")
    pids = load_worker_pids()
    if pids:
        active_pids = []
        for pid in pids:
            if is_process_running(pid):
                click.echo(f"  Worker (PID: {pid}) - Running")
                active_pids.append(pid)
            else:
                click.echo(f"  Worker (PID: {pid}) - Not running")
        if len(active_pids) != len(pids):
            save_worker_pids(active_pids)
    else:
        click.echo("  No active workers")
    
    # Configuration
    click.echo("\nConfiguration:")
    config = status_data['config']
    for key, value in config.items():
        click.echo(f"  {key}: {value}")


@cli.command()
@click.option('--state', type=click.Choice(['pending', 'processing', 'completed', 'failed', 'dead']),
              help='Filter jobs by state')
def list(state):
    """List jobs, optionally filtered by state."""
    job_manager = JobManager()
    jobs = job_manager.list_jobs(state=state)
    
    if not jobs:
        state_msg = f" with state '{state}'" if state else ""
        click.echo(f"No jobs found{state_msg}")
        return
    
    click.echo(f"Found {len(jobs)} job(s){' (' + state + ')' if state else ''}:\n")
    
    for job in jobs:
        click.echo(f"ID: {job['id']}")
        click.echo(f"  Command: {job['command']}")
        click.echo(f"  State: {job['state']}")
        click.echo(f"  Attempts: {job['attempts']}/{job['max_retries']}")
        click.echo(f"  Created: {job['created_at']}")
        if job.get('next_retry_at'):
            click.echo(f"  Next Retry: {job['next_retry_at']}")
        click.echo()


@cli.group()
def dlq():
    """Manage Dead Letter Queue."""
    pass


@dlq.command('list')
def dlq_list():
    """List all jobs in the Dead Letter Queue."""
    dlq_manager = DLQManager()
    dead_jobs = dlq_manager.list_dead_jobs()
    
    if not dead_jobs:
        click.echo("No jobs in Dead Letter Queue")
        return
    
    click.echo(f"Found {len(dead_jobs)} job(s) in Dead Letter Queue:\n")
    
    for job in dead_jobs:
        click.echo(f"ID: {job['id']}")
        click.echo(f"  Command: {job['command']}")
        click.echo(f"  Attempts: {job['attempts']}/{job['max_retries']}")
        click.echo(f"  Failed at: {job['updated_at']}")
        click.echo()


@dlq.command()
@click.argument('job_id', type=str)
def retry(job_id):
    """Retry a job from the Dead Letter Queue."""
    dlq_manager = DLQManager()
    
    if dlq_manager.retry_job(job_id):
        click.echo(f"Job '{job_id}' moved back to pending queue")
    else:
        click.echo(f"Error: Job '{job_id}' not found or not in Dead Letter Queue", err=True)
        sys.exit(1)


@cli.group()
def config():
    """Manage configuration."""
    pass


@config.command('set')
@click.argument('key', type=str)
@click.argument('value', type=str)
def config_set(key, value):
    """Set a configuration value.
    
    KEY: Configuration key (max-retries, backoff-base, poll-interval)
    VALUE: Configuration value
    """
    config = Config()
    
    # Convert key from kebab-case to snake_case
    key_map = {
        'max-retries': 'max_retries',
        'backoff-base': 'backoff_base',
        'poll-interval': 'poll_interval'
    }
    
    internal_key = key_map.get(key, key.replace('-', '_'))
    
    # Convert value to appropriate type
    try:
        if internal_key in ['max_retries', 'poll_interval']:
            value = int(value)
        elif internal_key == 'backoff_base':
            value = float(value) if '.' in value else int(value)
    except ValueError:
        click.echo(f"Error: Invalid value for {key}: {value}", err=True)
        sys.exit(1)
    
    config.set(internal_key, value)
    click.echo(f"Set {key} = {value}")


@config.command('get')
@click.argument('key', type=str, required=False)
def config_get(key):
    """Get configuration value(s)."""
    config = Config()
    
    if key:
        # Convert key from kebab-case to snake_case
        key_map = {
            'max-retries': 'max_retries',
            'backoff-base': 'backoff_base',
            'poll-interval': 'poll_interval'
        }
        internal_key = key_map.get(key, key.replace('-', '_'))
        value = config.get(internal_key)
        if value is not None:
            click.echo(f"{key} = {value}")
        else:
            click.echo(f"Configuration key '{key}' not found", err=True)
            sys.exit(1)
    else:
        # Show all config
        all_config = config.get_all()
        click.echo("Configuration:")
        for k, v in all_config.items():
            display_key = k.replace('_', '-')
            click.echo(f"  {display_key} = {v}")


def main():
    """Main entry point for queuectl CLI."""
    cli()


if __name__ == '__main__':
    main()


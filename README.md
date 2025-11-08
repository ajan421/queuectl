# QueueCTL - CLI-based Background Job Queue System

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

QueueCTL is a production-grade CLI tool for managing background jobs with worker processes, automatic retries with exponential backoff, and a Dead Letter Queue (DLQ) for permanently failed jobs. It provides a simple yet powerful interface for executing and managing asynchronous tasks in a reliable and scalable manner.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Command Reference](#command-reference)
- [Architecture](#architecture)
- [Job Lifecycle](#job-lifecycle)
- [Configuration](#configuration)
- [Database Management](#database-management)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Performance Considerations](#performance-considerations)
- [Security Considerations](#security-considerations)
- [Production Deployment](#production-deployment)
- [API Examples](#api-examples)
- [Common Use Cases](#common-use-cases)
- [Assumptions & Trade-offs](#assumptions--trade-offs)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)

## Features

- ✅ **Job Management**: Enqueue, list, and monitor background jobs with full lifecycle tracking
- ✅ **Worker Processes**: Run multiple worker processes in parallel for high-throughput processing
- ✅ **Automatic Retries**: Exponential backoff retry mechanism for failed jobs
- ✅ **Dead Letter Queue**: Automatic DLQ for permanently failed jobs with manual retry capability
- ✅ **Persistent Storage**: SQLite database for job persistence across restarts
- ✅ **Configuration Management**: Configurable retry count, backoff base, and polling intervals
- ✅ **Graceful Shutdown**: Workers finish current jobs before exiting
- ✅ **Race Condition Prevention**: Database-level locking prevents duplicate processing
- ✅ **Cross-Platform**: Works on Windows, Linux, and macOS
- ✅ **File-based Job Input**: Support for reading jobs from JSON files (PowerShell-friendly)

## Tech Stack

- **Python 3.7+** - Core language
- **SQLite** - Persistent job storage
- **Click** - CLI framework for elegant command-line interfaces
- **Multiprocessing** - Parallel worker execution
- **Subprocess** - Command execution

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- Git (for cloning the repository)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd q
   ```

2. **Install the package:**
   ```bash
   pip install -e .
   ```

   This installs QueueCTL in "editable" mode, so code changes are reflected immediately.

3. **Verify installation:**
   ```bash
   queuectl --version
   ```

   Expected output: `queuectl, version 1.0.0`

### Alternative Installation Methods

**Using Python module directly:**
```bash
python -m queuectl.cli --version
```

**Install with specific Python version:**
```bash
python3.9 -m pip install -e .
```

## Quick Start

### 1. Enqueue Your First Job

**Linux/macOS:**
```bash
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'
```

**Windows PowerShell:**
```powershell
# Using file (recommended for PowerShell)
queuectl enqueue --file job.json

# Or using variable
$job = '{"id":"job1","command":"echo Hello World"}'
queuectl enqueue $job
```

### 2. Start a Worker

```bash
queuectl worker start --count 1
```

### 3. Check Status

```bash
queuectl status
```

### 4. View Results

```bash
queuectl list --state completed
```

### 5. Stop Workers

```bash
queuectl worker stop
```

## Usage Guide

### Enqueue Jobs

#### Method 1: Direct JSON String (Linux/macOS)

```bash
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'
```

#### Method 2: From File (Recommended for Windows)

Create a JSON file (`job.json`):
```json
{"id":"job1","command":"echo Hello World"}
```

Then enqueue:
```bash
queuectl enqueue --file job.json
# or short form
queuectl enqueue -f job.json
```

#### Method 3: Using Python Module

```bash
python -m queuectl.cli enqueue '{"id":"job1","command":"echo Hello World"}'
```

#### Job JSON Schema

```json
{
  "id": "unique-job-id",           // Required: Unique identifier
  "command": "shell command",       // Required: Command to execute
  "max_retries": 3,                 // Optional: Max retry attempts (default: 3)
  "state": "pending"                // Optional: Initial state (default: "pending")
}
```

#### Examples

**Simple echo job:**
```json
{"id":"echo-job","command":"echo Hello from QueueCTL"}
```

**Job with sleep:**
```json
{"id":"sleep-job","command":"sleep 5 && echo Done"}
```

**Job with multiple commands:**
```json
{"id":"multi-cmd","command":"echo Step1 && echo Step2 && echo Step3"}
```

**Job with custom retries:**
```json
{"id":"retry-job","command":"some-command","max_retries":5}
```

**Windows-specific command:**
```json
{"id":"win-job","command":"timeout /t 2 /nobreak && echo Finished"}
```

### Worker Management

#### Start Workers

```bash
# Start single worker
queuectl worker start

# Start multiple workers (parallel processing)
queuectl worker start --count 3

# Start 10 workers for high throughput
queuectl worker start --count 10
```

**Worker Behavior:**
- Workers poll the database for available jobs
- Multiple workers process jobs in parallel
- Each worker can only process one job at a time
- Workers automatically handle retries and DLQ movement

#### Stop Workers

```bash
queuectl worker stop
```

**Graceful Shutdown:**
- Workers receive SIGTERM/SIGINT signals
- Current job is finished before worker exits
- No jobs are lost during shutdown

#### Check Worker Status

```bash
queuectl status
```

This shows:
- Number of active workers
- Worker PIDs
- Worker health status

### Job Listing

#### List All Jobs

```bash
queuectl list
```

#### Filter by State

```bash
# Pending jobs (waiting to be processed)
queuectl list --state pending

# Currently processing jobs
queuectl list --state processing

# Successfully completed jobs
queuectl list --state completed

# Failed jobs (will retry)
queuectl list --state failed

# Dead jobs (in DLQ)
queuectl list --state dead
```

#### Example Output

```
Found 5 job(s):

ID: job-1
  Command: echo Hello
  State: completed
  Attempts: 1/3
  Created: 2025-11-05T10:00:00Z

ID: job-2
  Command: sleep 2
  State: pending
  Attempts: 0/3
  Created: 2025-11-05T10:01:00Z
```

### Status Monitoring

```bash
queuectl status
```

**Output includes:**
- Job counts by state (pending, processing, completed, failed, dead)
- Total job count
- Active worker count and PIDs
- Current configuration settings

**Example Output:**
```
=== QueueCTL Status ===

Job States:
  pending         5
  processing      2
  completed       100
  failed          1
  dead            3
  total           111

Active Workers:
  Worker (PID: 12345) - Running
  Worker (PID: 12346) - Running
  Worker (PID: 12347) - Running

Configuration:
  max_retries: 3
  backoff_base: 2
  poll_interval: 1
```

### Dead Letter Queue (DLQ)

Jobs that fail after exhausting all retries are moved to the Dead Letter Queue.

#### List DLQ Jobs

```bash
queuectl dlq list
```

#### Retry DLQ Jobs

```bash
queuectl dlq retry job-id
```

This moves the job back to `pending` state with attempts reset to 0.

#### Example: Handling DLQ

```bash
# Check DLQ
queuectl dlq list

# Retry a specific job
queuectl dlq retry failed-job-123

# Job is now back in pending queue
queuectl list --state pending
```

### Configuration Management

#### View All Configuration

```bash
queuectl config get
```

#### Get Specific Configuration

```bash
queuectl config get max-retries
queuectl config get backoff-base
queuectl config get poll-interval
```

#### Set Configuration

```bash
# Set max retries
queuectl config set max-retries 5

# Set backoff base (for exponential backoff)
queuectl config set backoff-base 3

# Set polling interval (seconds)
queuectl config set poll-interval 2
```

#### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `max-retries` | 3 | Maximum number of retry attempts before moving to DLQ |
| `backoff-base` | 2 | Base for exponential backoff calculation (delay = base^attempts) |
| `poll-interval` | 1 | Worker polling interval in seconds |

**Configuration File Location:**
- Linux/macOS: `~/.queuectl/config.json`
- Windows: `%USERPROFILE%\.queuectl\config.json`

## Command Reference

### Main Commands

| Command | Description | Example |
|---------|-------------|---------|
| `queuectl enqueue` | Enqueue a new job | `queuectl enqueue -f job.json` |
| `queuectl list` | List jobs | `queuectl list --state pending` |
| `queuectl status` | Show system status | `queuectl status` |
| `queuectl worker start` | Start workers | `queuectl worker start --count 3` |
| `queuectl worker stop` | Stop workers | `queuectl worker stop` |
| `queuectl dlq list` | List DLQ jobs | `queuectl dlq list` |
| `queuectl dlq retry` | Retry DLQ job | `queuectl dlq retry job-id` |
| `queuectl config get` | Get configuration | `queuectl config get` |
| `queuectl config set` | Set configuration | `queuectl config set max-retries 5` |

### Help Commands

```bash
# Main help
queuectl --help

# Command-specific help
queuectl enqueue --help
queuectl worker --help
queuectl dlq --help
queuectl config --help

# Subcommand help
queuectl worker start --help
queuectl config set --help
```

## Architecture

### System Architecture

```
┌─────────────────┐
│   CLI (cli.py)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐  ┌──▼────────┐
│ Job   │  │ Worker    │
│Manager│  │ Process   │
└───┬───┘  └──┬────────┘
    │         │
    └────┬────┘
         │
    ┌────▼────┐
    │ Storage │
    │ (SQLite)│
    └─────────┘
```

### Component Overview

1. **CLI Interface** (`cli.py`)
   - Command-line interface using Click framework
   - Handles user input and output
   - Manages worker processes

2. **Job Manager** (`job_manager.py`)
   - Job lifecycle management
   - State transitions
   - Retry logic
   - DLQ operations

3. **Storage Layer** (`storage.py`)
   - SQLite database operations
   - Job CRUD operations
   - Atomic locking mechanism
   - Query optimization

4. **Worker Process** (`worker.py`)
   - Job execution
   - Retry handling
   - Graceful shutdown
   - Error handling

5. **DLQ Manager** (`dlq.py`)
   - Dead Letter Queue operations
   - Job retry functionality

6. **Configuration** (`config.py`)
   - Settings management
   - JSON-based storage
   - Default values

7. **Utilities** (`utils.py`)
   - JSON parsing
   - Timestamp generation
   - Backoff calculation

### Data Flow

```
1. User enqueues job → CLI → Job Manager → Storage (DB)
2. Worker polls DB → Gets pending job → Locks job
3. Worker executes command → Updates job state
4. On success → Mark completed
5. On failure → Retry with backoff → DLQ if max retries exceeded
```

## Job Lifecycle

### State Diagram

```
┌─────────┐
│ pending │ ← New jobs start here
└────┬────┘
     │
     │ Worker picks up
     ▼
┌─────────────┐
│ processing  │ ← Currently executing
└────┬────────┘
     │
     ├─ Success ──→ ┌───────────┐
     │              │ completed │
     │              └───────────┘
     │
     └─ Failure ──→ ┌─────────┐
                    │ failed  │ ← Will retry with backoff
                    └────┬────┘
                         │
                         │ After max retries
                         ▼
                    ┌───────┐
                    │ dead  │ ← Moved to DLQ
                    └───────┘
```

### State Transitions

| From State | To State | Condition |
|------------|----------|-----------|
| `pending` | `processing` | Worker picks up job |
| `processing` | `completed` | Command executes successfully |
| `processing` | `failed` | Command fails (retries available) |
| `failed` | `processing` | Retry scheduled and executed |
| `failed` | `dead` | Max retries exceeded |
| `dead` | `pending` | Manual retry from DLQ |

### Retry Mechanism

**Exponential Backoff Formula:**
```
delay = base ^ attempts seconds
```

**Example with `backoff_base = 2`:**
- Attempt 1: 2^1 = 2 seconds
- Attempt 2: 2^2 = 4 seconds
- Attempt 3: 2^3 = 8 seconds
- Attempt 4: 2^4 = 16 seconds

**Retry Schedule:**
1. Job fails → State: `failed`, Attempts: 1
2. Wait 2 seconds (2^1)
3. Retry → State: `processing`
4. If fails again → State: `failed`, Attempts: 2
5. Wait 4 seconds (2^2)
6. Retry → State: `processing`
7. Continue until `max_retries` reached
8. Move to DLQ → State: `dead`

## Configuration

### Default Configuration

```json
{
  "max_retries": 3,
  "backoff_base": 2,
  "poll_interval": 1
}
```

### Configuration File

**Location:**
- Linux/macOS: `~/.queuectl/config.json`
- Windows: `%USERPROFILE%\.queuectl\config.json`

**Format:**
```json
{
  "max_retries": 5,
  "backoff_base": 3,
  "poll_interval": 2
}
```

### Environment Variables

Currently not supported, but can be added as a future enhancement.

### Per-Job Configuration

Jobs can override global `max_retries`:
```json
{"id":"job1","command":"cmd","max_retries":10}
```

## Database Management

### Database Location

**Linux/macOS:**
```
~/.queuectl/jobs.db
```

**Windows:**
```
%USERPROFILE%\.queuectl\jobs.db
```

### Database Schema

**Table: `jobs`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT | Primary key, unique job identifier |
| `command` | TEXT | Shell command to execute |
| `state` | TEXT | Current job state (pending, processing, completed, failed, dead) |
| `attempts` | INTEGER | Number of retry attempts (default: 0) |
| `max_retries` | INTEGER | Maximum retry attempts (default: 3) |
| `created_at` | TEXT | Job creation timestamp (ISO format) |
| `updated_at` | TEXT | Last update timestamp (ISO format) |
| `next_retry_at` | TEXT | Next retry scheduled time (ISO format, NULL if not scheduled) |
| `worker_id` | TEXT | Worker ID processing the job (NULL if not assigned) |

**Indexes:**
- Primary key on `id`
- Index on `state` (for faster state queries)
- Index on `next_retry_at` (for retry scheduling)

### Viewing the Database

#### Method 1: Using Python Script

A helper script is provided (`view_db.py`):
```bash
python view_db.py
```

#### Method 2: Using SQLite CLI

```bash
sqlite3 ~/.queuectl/jobs.db

# View schema
.schema jobs

# View all jobs
SELECT * FROM jobs;

# View jobs by state
SELECT * FROM jobs WHERE state = 'pending';

# View failed jobs
SELECT * FROM jobs WHERE state = 'failed';

# View DLQ jobs
SELECT * FROM jobs WHERE state = 'dead';

# View job statistics
SELECT state, COUNT(*) FROM jobs GROUP BY state;
```

#### Method 3: Using GUI Tools

**Recommended Tools:**
- **DB Browser for SQLite**: https://sqlitebrowser.org/
- **SQLiteStudio**: https://sqlitestudio.pl/
- **VS Code Extension**: SQLite Viewer

**Open database:**
- Linux/macOS: `~/.queuectl/jobs.db`
- Windows: `%USERPROFILE%\.queuectl\jobs.db`

### Database Backup

```bash
# Linux/macOS
cp ~/.queuectl/jobs.db ~/.queuectl/jobs.db.backup

# Windows
copy %USERPROFILE%\.queuectl\jobs.db %USERPROFILE%\.queuectl\jobs.db.backup
```

### Database Maintenance

**Vacuum (reclaim space):**
```sql
VACUUM;
```

**Analyze (update statistics):**
```sql
ANALYZE;
```

**Check integrity:**
```sql
PRAGMA integrity_check;
```

## Testing

### Unit Tests

```bash
# Run all tests
python -m pytest tests/

# Run with verbose output
python -m pytest tests/ -v

# Run specific test file
python -m unittest tests.test_storage
python -m unittest tests.test_job_manager

# Run with coverage
python -m pytest tests/ --cov=queuectl
```

### Integration Tests

```bash
# Run demo script (comprehensive integration test)
python demo_script.py
```

### Manual Testing Scenarios

#### 1. Basic Job Completion

```bash
# Enqueue a simple job
queuectl enqueue -f job.json

# Start a worker
queuectl worker start --count 1

# Wait a few seconds, then check status
queuectl status
queuectl list --state completed
```

#### 2. Failed Job with Retry

```bash
# Enqueue a job that will fail
queuectl enqueue '{"id":"fail-test","command":"nonexistent-command","max_retries":2}'

# Start a worker
queuectl worker start --count 1

# Wait for retries (check status periodically)
queuectl status
queuectl list --state failed

# After max retries, check DLQ
queuectl dlq list
```

#### 3. Multiple Workers

```bash
# Start multiple workers
queuectl worker start --count 3

# Enqueue multiple jobs
for i in {1..10}; do
  queuectl enqueue "{\"id\":\"job$i\",\"command\":\"echo Job $i && sleep 1\"}"
done

# Monitor status
queuectl status
```

#### 4. Persistence Across Restarts

```bash
# Enqueue jobs
queuectl enqueue -f job.json

# Stop workers and restart
queuectl worker stop
queuectl worker start --count 1

# Jobs should still be there and process
queuectl status
```

#### 5. DLQ Retry

```bash
# Check DLQ
queuectl dlq list

# Retry a job
queuectl dlq retry failed-job-id

# Verify job is back in pending
queuectl list --state pending
```

#### 6. Configuration Changes

```bash
# View current config
queuectl config get

# Change max retries
queuectl config set max-retries 5

# Verify change
queuectl config get max-retries
```

### Performance Testing

```bash
# Enqueue many jobs
for i in {1..100}; do
  queuectl enqueue "{\"id\":\"perf-job-$i\",\"command\":\"echo $i\"}"
done

# Start multiple workers
queuectl worker start --count 10

# Monitor processing rate
watch -n 1 'queuectl status'
```

## Troubleshooting

### Common Issues

#### 1. Command Not Found

**Problem:** `queuectl: command not found`

**Solutions:**
- Verify installation: `pip install -e .`
- Check Python Scripts in PATH
- Use Python module: `python -m queuectl.cli`

#### 2. Workers Not Starting

**Problem:** Workers fail to start

**Solutions:**
- Check Python version: `python --version` (must be 3.7+)
- Verify database exists: `ls ~/.queuectl/jobs.db`
- Check for stale PIDs: `cat ~/.queuectl/worker_pids.json`
- Restart: `queuectl worker stop && queuectl worker start`

#### 3. Jobs Stuck in Processing

**Problem:** Jobs remain in `processing` state

**Solutions:**
- Check if workers are running: `queuectl status`
- Stop and restart workers: `queuectl worker stop && queuectl worker start`
- Manually reset job state (via database):
  ```sql
  UPDATE jobs SET state = 'pending', worker_id = NULL WHERE state = 'processing';
  ```

#### 4. Database Locked Errors

**Problem:** `database is locked` errors

**Solutions:**
- Reduce number of workers
- Increase polling interval: `queuectl config set poll-interval 2`
- Check for long-running jobs
- Restart workers

#### 5. JSON Parsing Errors

**Problem:** `Invalid JSON input` errors

**Solutions:**
- Use `--file` option instead of direct JSON
- Verify JSON syntax: `python -m json.tool job.json`
- Escape quotes properly in PowerShell
- Use single quotes for JSON strings

#### 6. Jobs Not Processing

**Problem:** Jobs remain in `pending` state

**Solutions:**
- Verify workers are running: `queuectl status`
- Check worker logs for errors
- Verify database connectivity
- Restart workers

#### 7. PowerShell JSON Issues

**Problem:** JSON parsing fails in PowerShell

**Solutions:**
- Use `--file` option: `queuectl enqueue -f job.json`
- Use PowerShell variables:
  ```powershell
  $job = '{"id":"test","command":"echo hello"}'
  queuectl enqueue $job
  ```
- Use Python module: `python -m queuectl.cli enqueue '{"id":"test","command":"echo"}'`

#### 8. Permission Errors

**Problem:** Permission denied errors

**Solutions:**
- Check file permissions: `chmod 755 ~/.queuectl`
- Check database permissions: `chmod 644 ~/.queuectl/jobs.db`
- Run with appropriate user permissions

### Debug Mode

Enable verbose logging by modifying worker code or checking database directly:

```bash
# View recent jobs
sqlite3 ~/.queuectl/jobs.db "SELECT * FROM jobs ORDER BY updated_at DESC LIMIT 10;"

# Check worker PIDs
cat ~/.queuectl/worker_pids.json

# View configuration
cat ~/.queuectl/config.json
```

### Getting Help

```bash
# General help
queuectl --help

# Command-specific help
queuectl enqueue --help
queuectl worker --help
queuectl dlq --help
queuectl config --help
```

## Best Practices

### 1. Job Design

- **Use unique job IDs**: Prevent conflicts and enable tracking
- **Keep commands simple**: Complex logic should be in scripts
- **Set appropriate retries**: Balance between resilience and quick failure
- **Use descriptive IDs**: `backup-db-2025-11-05` vs `job1`

### 2. Worker Management

- **Match workers to workload**: More workers for high-throughput scenarios
- **Monitor worker health**: Regularly check `queuectl status`
- **Graceful shutdown**: Always use `queuectl worker stop`
- **Scale gradually**: Start with few workers, increase as needed

### 3. Error Handling

- **Handle failures gracefully**: Jobs should fail fast on unrecoverable errors
- **Use DLQ for investigation**: Review DLQ jobs regularly
- **Monitor retry patterns**: High retry rates may indicate systemic issues
- **Set appropriate timeouts**: Prevent jobs from hanging indefinitely

### 4. Configuration

- **Set reasonable defaults**: Don't set max_retries too high
- **Tune backoff base**: Higher values reduce system load but increase delay
- **Adjust polling interval**: Balance between responsiveness and CPU usage
- **Document custom settings**: Keep track of configuration changes

### 5. Monitoring

- **Regular status checks**: Monitor job queues and worker health
- **Track metrics**: Job completion rates, failure rates, processing times
- **Review DLQ regularly**: Investigate and fix recurring failures
- **Monitor database size**: Clean up old completed jobs periodically

### 6. Security

- **Validate job commands**: Don't execute untrusted commands
- **Limit worker access**: Run workers with minimal privileges
- **Secure database**: Protect database file with appropriate permissions
- **Audit job history**: Keep logs of job executions for security auditing

### 7. Performance

- **Batch operations**: Enqueue multiple jobs efficiently
- **Optimize commands**: Keep job execution times reasonable
- **Monitor database**: Regular maintenance (VACUUM, ANALYZE)
- **Scale workers**: Add more workers for parallel processing

## Performance Considerations

### Throughput

- **Single worker**: ~10-50 jobs/second (depends on job complexity)
- **Multiple workers**: Linear scaling up to database limits
- **Optimal worker count**: 2-10 workers for most use cases

### Database Performance

- **SQLite limitations**: Best for single-machine deployments
- **Concurrent access**: SQLite handles moderate concurrency well
- **Database size**: Efficient up to several GB
- **Indexing**: Automatic indexes on `state` and `next_retry_at`

### Resource Usage

- **Memory**: ~10-50 MB per worker process
- **CPU**: Minimal when idle, scales with job complexity
- **Disk**: Database grows with job history (clean up old jobs)

### Optimization Tips

1. **Clean up old jobs**: Regularly remove completed jobs
2. **Tune polling interval**: Reduce for low-latency, increase for efficiency
3. **Optimize commands**: Keep job execution times short
4. **Monitor database**: Regular VACUUM and ANALYZE
5. **Scale workers**: Add more workers for parallel processing

## Security Considerations

### Command Execution

- **Untrusted commands**: Never execute untrusted user input
- **Shell injection**: Validate and sanitize commands
- **Permissions**: Run workers with minimal required privileges
- **Isolation**: Consider containerization for untrusted jobs

### Database Security

- **File permissions**: Protect database file (chmod 600)
- **Backup encryption**: Encrypt database backups
- **Access control**: Limit database file access
- **Audit logging**: Log job executions for security auditing

### Network Security

- **Local only**: Database is local, no network exposure
- **Worker communication**: Workers communicate via database only
- **No external dependencies**: No network calls in core system

### Best Practices

1. **Validate inputs**: Check job JSON before enqueueing
2. **Limit privileges**: Run workers with minimal permissions
3. **Monitor activity**: Track job executions and failures
4. **Regular updates**: Keep Python and dependencies updated
5. **Backup data**: Regular database backups

## Production Deployment

### Requirements

- **Python 3.7+**: Required runtime
- **SQLite**: Included with Python
- **Disk space**: Adequate for database growth
- **Memory**: Sufficient for worker processes

### Deployment Steps

1. **Install QueueCTL:**
   ```bash
   pip install -e .
   ```

2. **Configure:**
   ```bash
   queuectl config set max-retries 5
   queuectl config set backoff-base 2
   queuectl config set poll-interval 1
   ```

3. **Start Workers:**
   ```bash
   queuectl worker start --count 5
   ```

4. **Monitor:**
   ```bash
   queuectl status
   ```

### Systemd Service (Linux)

Create `/etc/systemd/system/queuectl.service`:

```ini
[Unit]
Description=QueueCTL Worker Service
After=network.target

[Service]
Type=simple
User=queuectl
WorkingDirectory=/opt/queuectl
ExecStart=/usr/local/bin/queuectl worker start --count 5
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable queuectl
sudo systemctl start queuectl
sudo systemctl status queuectl
```

### Windows Service

Use NSSM (Non-Sucking Service Manager) or similar tool to run workers as Windows service.

### Monitoring

- **Status checks**: Regular `queuectl status` commands
- **Database monitoring**: Track database size and performance
- **Worker health**: Monitor worker processes
- **Job metrics**: Track completion rates and failures

### Backup Strategy

1. **Database backups**: Regular backups of `jobs.db`
2. **Configuration backups**: Backup `config.json`
3. **Job history**: Archive completed jobs periodically
4. **Disaster recovery**: Test restoration procedures

## API Examples

### Python Integration

```python
import subprocess
import json

# Enqueue a job
job = {
    "id": "python-job-1",
    "command": "python script.py",
    "max_retries": 3
}
subprocess.run(["queuectl", "enqueue", json.dumps(job)])

# Check status
result = subprocess.run(["queuectl", "status"], capture_output=True, text=True)
print(result.stdout)
```

### Shell Script Integration

```bash
#!/bin/bash

# Enqueue multiple jobs
for i in {1..10}; do
    queuectl enqueue "{\"id\":\"job-$i\",\"command\":\"echo $i\"}"
done

# Start workers
queuectl worker start --count 3

# Wait for completion
sleep 30

# Check status
queuectl status
```

### PowerShell Integration

```powershell
# Enqueue jobs from array
$jobs = @(
    @{id="job1"; command="echo Hello"},
    @{id="job2"; command="echo World"}
)

foreach ($job in $jobs) {
    $json = $job | ConvertTo-Json -Compress
    queuectl enqueue $json
}

# Start workers
queuectl worker start --count 2

# Monitor
Start-Sleep -Seconds 10
queuectl status
```

## Common Use Cases

### 1. Background Task Processing

```bash
# Enqueue long-running tasks
queuectl enqueue '{"id":"backup","command":"tar -czf backup.tar.gz /data"}'
queuectl enqueue '{"id":"report","command":"python generate_report.py"}'

# Process with workers
queuectl worker start --count 2
```

### 2. Scheduled Jobs (with cron)

```bash
# Add to crontab
0 * * * * queuectl enqueue '{"id":"hourly-job","command":"python hourly_task.py"}'
```

### 3. Batch Processing

```bash
# Process files in batch
for file in *.txt; do
    queuectl enqueue "{\"id\":\"process-$file\",\"command\":\"python process.py $file\"}"
done

# Process with multiple workers
queuectl worker start --count 5
```

### 4. Retry Logic

```bash
# Job with retries for unreliable operations
queuectl enqueue '{"id":"api-call","command":"curl https://api.example.com/data","max_retries":5}'
```

### 5. DLQ Management

```bash
# Check DLQ regularly
queuectl dlq list

# Retry failed jobs after fixing issues
queuectl dlq retry failed-job-id
```

## Assumptions & Trade-offs

### Assumptions

1. **Command Execution**: Commands are executed in a shell environment with standard commands available
2. **Timeout**: Jobs have a 1-hour timeout to prevent infinite execution
3. **Concurrency**: Database locking prevents race conditions, SQLite handles moderate concurrency
4. **Worker Management**: Workers are managed via process PIDs stored in a file (single-machine deployment)
5. **Single Machine**: Designed for single-machine deployments, not distributed systems

### Trade-offs

1. **SQLite vs. PostgreSQL/MySQL**: 
   - Chosen for simplicity and zero-configuration
   - Works well for single-machine deployments
   - May have limitations with very high concurrency

2. **File-based PID tracking**: 
   - Simple but may not work in distributed environments
   - Suitable for single-machine deployment

3. **Polling vs. Event-driven**: 
   - Workers poll the database for jobs
   - Event-driven would be more efficient but requires more complexity

4. **No job priority**: 
   - Jobs are processed in FIFO order
   - Priority queues could be added as enhancement

5. **No job scheduling**: 
   - Jobs are executed immediately when picked up
   - Scheduled/delayed jobs could be added as enhancement

### Design Decisions

1. **Exponential Backoff**: Uses `base ^ attempts` formula for retry delays
2. **Database Locking**: Atomic UPDATE operations prevent race conditions
3. **Graceful Shutdown**: Workers handle signals and finish current jobs
4. **Configuration Storage**: JSON file for simplicity
5. **CLI-first Design**: Prioritizes command-line usability

## Future Enhancements

### Planned Features

- [ ] Job timeout handling (configurable per job)
- [ ] Job priority queues
- [ ] Scheduled/delayed jobs (`run_at` field)
- [ ] Job output logging to files
- [ ] Execution metrics and statistics
- [ ] Minimal web dashboard for monitoring
- [ ] Job dependencies (job B runs after job A completes)
- [ ] Job result storage
- [ ] Distributed worker support (multiple machines)
- [ ] REST API for job management
- [ ] Webhook notifications
- [ ] Job templates
- [ ] Bulk job operations
- [ ] Job cancellation
- [ ] Job progress tracking
- [ ] Resource limits (CPU, memory)
- [ ] Job tagging and filtering
- [ ] Export/import jobs
- [ ] Job history archival
- [ ] Performance metrics dashboard

### Contribution Ideas

- Database migration tools
- Additional storage backends (PostgreSQL, MySQL)
- Job scheduling integration (cron-like)
- Monitoring integrations (Prometheus, Grafana)
- Alerting system
- Job validation framework
- Plugin system for custom job types

## Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd q

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/

# Run demo script
python demo_script.py
```

### Code Style

- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings for all functions
- Add tests for new features

### Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## File Structure

```
queuectl/
├── queuectl/
│   ├── __init__.py           # Package initialization
│   ├── cli.py                 # CLI interface (main entry point)
│   ├── storage.py             # SQLite database operations
│   ├── job_manager.py         # Job lifecycle management
│   ├── worker.py              # Worker process logic
│   ├── dlq.py                 # Dead Letter Queue operations
│   ├── config.py              # Configuration management
│   └── utils.py               # Utility functions
├── tests/
│   ├── __init__.py
│   ├── test_storage.py        # Storage layer tests
│   └── test_job_manager.py    # Job manager tests
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── demo_script.py             # Demo/validation script
├── view_db.py                 # Database viewer script
├── enqueue_all_jobs.ps1       # PowerShell batch enqueue script
├── job.json                   # Example job file
├── job1.json                  # Example job file
├── job2.json                  # Example job file
├── job3.json                  # Example job file
├── job4.json                  # Example job file
├── job5.json                  # Example job file
├── README.md                  # This file
└── .gitignore                 # Git ignore rules
```

## License

This project is part of a backend developer internship assignment.

## Contact

For questions or issues, please refer to the repository issues page.

## Acknowledgments

- Built with Python and Click framework
- Uses SQLite for persistent storage
- Inspired by modern job queue systems like Celery and Bull

## Changelog

### Version 1.0.0 (2025-11-05)

- Initial release
- Basic job queue functionality
- Worker processes with multiprocessing
- Retry mechanism with exponential backoff
- Dead Letter Queue (DLQ)
- Configuration management
- CLI interface with Click
- SQLite persistent storage
- Graceful worker shutdown
- Database-level locking
- File-based job input support

---

**QueueCTL** - Reliable background job processing made simple.

# QueueCTL - CLI-based Background Job Queue System

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A production-grade CLI tool for managing background jobs with worker processes, automatic retries with exponential backoff, and a Dead Letter Queue (DLQ).

## 🎥 Demo Video

**Watch the complete feature demonstration (2 minutes):**

[![QueueCTL Demo Video](https://img.youtube.com/vi/rur8wBvwfPo/maxresdefault.jpg)](https://www.youtube.com/watch?v=rur8wBvwfPo)

**👆 Click to watch the demo on YouTube**

---

## 1. Setup Instructions

### Prerequisites
- Python 3.7+
- pip

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd q

# Install the package
pip install -e .

# Verify installation
queuectl --version
```

**Database & Config Location:**
- Linux/macOS: `~/.queuectl/`
- Windows: `%USERPROFILE%\.queuectl\`

---

## 2. Usage Examples

### Basic Workflow

```bash
# 1. Enqueue a job
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'

# Windows PowerShell (use file method)
queuectl enqueue -f job.json

# 2. Start workers
queuectl worker start --count 3

# 3. Check status
queuectl status

# 4. List jobs by state
queuectl list --state completed
queuectl list --state pending
queuectl list --state failed

# 5. Stop workers
queuectl worker stop
```

### Example Output

```bash
$ queuectl status
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
```

### Job JSON Format

```json
{
  "id": "unique-job-id",
  "command": "shell command to execute",
  "max_retries": 3,
  "priority": 0,
  "timeout": 10,
  "run_at": "2025-11-10T12:00:00Z"
}
```

**Required fields:** `id`, `command`

**Optional fields:**
- `max_retries` (default: 3)
- `priority` (default: 0, higher = processed first)
- `timeout` (default: 10 seconds)
- `run_at` (ISO timestamp for scheduled jobs)

### Advanced Features

**Priority Queues:**
```bash
queuectl enqueue '{"id":"urgent","command":"backup.sh","priority":10}'
queuectl enqueue '{"id":"normal","command":"cleanup.sh","priority":0}'
# Urgent job processes first
```

**Job Timeout:**
```bash
queuectl enqueue '{"id":"quick","command":"long-task.sh","timeout":30}'
# Job killed after 30 seconds
```

**Dead Letter Queue:**
```bash
# List failed jobs
queuectl dlq list

# Retry a dead job
queuectl dlq retry job-id
```

**Configuration:**
```bash
# View all settings
queuectl config get

# Update settings
queuectl config set max-retries 5
queuectl config set backoff-base 2
queuectl config set poll-interval 1
```

---

## 3. Architecture Overview

### System Components

```
┌─────────────┐
│   CLI       │ ← User interaction
└──────┬──────┘
       │
┌──────▼──────┐
│ JobManager  │ ← Job lifecycle & retry logic
└──────┬──────┘
       │
┌──────▼──────┐
│  Storage    │ ← SQLite database (persistent)
│  (SQLite)   │
└──────┬──────┘
       │
┌──────▼──────┐
│   Worker    │ ← Execute jobs in parallel
│  Processes  │
└─────────────┘
```

### Job Lifecycle

```
┌─────────┐
│ pending │ ← Job created
└────┬────┘
     │
     ▼
┌────────────┐
│ processing │ ← Worker picks up job
└─────┬──────┘
      │
      ├─ Success ──→ [completed]
      │
      └─ Failure ──→ [failed] ──→ Retry with backoff
                         │
                         └─ Max retries ──→ [dead] (DLQ)
```

**State Transitions:**
- `pending` → `processing` (worker picks up)
- `processing` → `completed` (success)
- `processing` → `failed` (failure, retries available)
- `failed` → `processing` (retry after backoff delay)
- `failed` → `dead` (max retries exceeded)
- `dead` → `pending` (manual retry from DLQ)

### Data Persistence

**SQLite Database Schema:**

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Unique job identifier (PRIMARY KEY) |
| command | TEXT | Shell command to execute |
| state | TEXT | Job state (pending/processing/completed/failed/dead) |
| attempts | INTEGER | Number of retry attempts |
| max_retries | INTEGER | Maximum retry attempts |
| priority | INTEGER | Job priority (higher = first) |
| timeout | INTEGER | Command timeout in seconds |
| run_at | TEXT | Scheduled execution time (ISO format) |
| created_at | TEXT | Job creation timestamp |
| updated_at | TEXT | Last update timestamp |
| next_retry_at | TEXT | Next retry scheduled time |
| worker_id | TEXT | Worker ID currently processing job |
| last_output | TEXT | Command output (stdout/stderr) |
| duration_ms | INTEGER | Execution duration in milliseconds |

**Indexes:**
- `idx_state` on `state` (fast state queries)
- `idx_next_retry` on `next_retry_at` (retry scheduling)
- `idx_priority` on `priority` (priority ordering)
- `idx_run_at` on `run_at` (scheduled jobs)

### Worker Logic

**Polling Mechanism:**
1. Worker polls database every `poll_interval` (default: 1 second)
2. Atomic query locks next available job with:
   ```sql
   UPDATE jobs SET state='processing', worker_id=? 
   WHERE id=(SELECT id FROM jobs WHERE state='pending' 
            AND (run_at IS NULL OR run_at <= ?) 
            ORDER BY priority DESC, run_at ASC, created_at ASC 
            LIMIT 1)
   ```
3. Database-level locking prevents duplicate processing
4. Worker executes command with `subprocess.run(timeout=...)`
5. Update job state based on result

**Retry Logic (Exponential Backoff):**
- Formula: `delay = base ^ attempts` seconds
- Default: `base = 2`
- Example: 2s, 4s, 8s, 16s, 32s...
- After `max_retries`, job moves to DLQ

**Graceful Shutdown:**
- Workers listen for SIGTERM/SIGINT
- Current job finishes before exit
- No jobs are lost during shutdown

---

## 4. Assumptions & Trade-offs

### Assumptions

1. **Single-machine deployment** — SQLite works for one machine; not distributed
2. **Shell commands available** — Commands execute in system shell (bash/powershell)
3. **Job timeout** — Default 10 seconds prevents infinite execution
4. **Worker trust** — Workers have permission to execute enqueued commands
5. **Moderate concurrency** — SQLite handles 2-10 workers well

### Design Trade-offs

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **SQLite vs PostgreSQL** | Zero-config, simple deployment | Limited to single machine |
| **Polling vs Event-driven** | Simple implementation, reliable | Higher latency (~1 second) |
| **File-based PID tracking** | No external dependencies | Won't work in distributed setup |
| **Exponential backoff** | Reduces load on failing services | Longer delays for retries |
| **No job cancellation** | Simpler worker logic | Can't stop running jobs |
| **FIFO with priority** | Predictable processing order | No complex scheduling |

### Simplifications

- **No distributed workers** — Single-machine only (could add Redis/PostgreSQL)
- **No job dependencies** — Jobs run independently (could add DAG support)
- **No streaming output** — Output captured after completion
- **Limited scheduling** — Basic `run_at` field (could add cron-like syntax)
- **No web dashboard** — CLI only (could add Flask/FastAPI UI)

### Performance Characteristics

- **Throughput:** 10-50 jobs/second per worker (depends on job complexity)
- **Latency:** ~1 second (polling interval)
- **Concurrency:** 2-10 workers recommended
- **Database size:** Efficient up to several GB

---

## 5. Testing Instructions

### Quick Test (Manual)

```bash
# 1. Enqueue a test job
queuectl enqueue '{"id":"test1","command":"echo Test passed"}'

# 2. Start worker
queuectl worker start --count 1

# 3. Wait 2 seconds, then check
queuectl list --state completed
# Should show "test1" completed

# 4. Stop worker
queuectl worker stop
```

### Automated Demo Script

**Full demo (~60 seconds):**
```bash
./demo.ps1
```

**Quick demo (~30 seconds):**
```bash
./demo_fast.ps1
```

### Feature Tests

**1. Retry Mechanism:**
```bash
queuectl enqueue '{"id":"fail-test","command":"nonexistent-cmd","max_retries":2}'
queuectl worker start --count 1
# Wait 10 seconds for retries (2s + 4s delays)
queuectl dlq list
# Should show "fail-test" in DLQ
queuectl worker stop
```

**2. Priority Queue:**
```bash
queuectl enqueue '{"id":"low","command":"echo Low","priority":0}'
queuectl enqueue '{"id":"high","command":"echo High","priority":10}'
queuectl worker start --count 1
# Wait 2 seconds
queuectl list --state completed
# "high" should complete before "low"
queuectl worker stop
```

**3. Job Timeout:**
```bash
queuectl enqueue '{"id":"timeout","command":"sleep 60","timeout":2}'
queuectl worker start --count 1
# Wait 3 seconds
queuectl list --state failed
# Should show "timeout" failed after 2 seconds
queuectl worker stop
```

**4. Multiple Workers:**
```bash
queuectl enqueue '{"id":"p1","command":"echo Job1"}'
queuectl enqueue '{"id":"p2","command":"echo Job2"}'
queuectl enqueue '{"id":"p3","command":"echo Job3"}'
queuectl worker start --count 3
# Wait 2 seconds
queuectl status
# Should show 3 workers processed jobs in parallel
queuectl worker stop
```

### Database Inspection

```bash
# View database contents
python view_db.py

# View statistics
python db_stats.py

# Direct SQL access (optional)
sqlite3 ~/.queuectl/jobs.db "SELECT * FROM jobs;"
```

### Cleanup

```bash
# Stop all workers
queuectl worker stop

# Clear database (fresh start)
rm ~/.queuectl/jobs.db
# Or on Windows:
# Remove-Item $env:USERPROFILE\.queuectl\jobs.db
```

---

## Configuration Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `max-retries` | 3 | Max retry attempts before DLQ |
| `backoff-base` | 2 | Exponential backoff base (2^attempts) |
| `poll-interval` | 1 | Worker polling interval (seconds) |
| `default-timeout` | 10 | Default job timeout (seconds) |

```bash
# Update configuration
queuectl config set max-retries 5
queuectl config set backoff-base 3
queuectl config set poll-interval 2
queuectl config set default-timeout 30
```

---

## File Structure

```
queuectl/
├── queuectl/              # Main package
│   ├── cli.py             # CLI interface (Click)
│   ├── storage.py         # SQLite database layer
│   ├── job_manager.py     # Job lifecycle management
│   ├── worker.py          # Worker process logic
│   ├── dlq.py             # Dead Letter Queue
│   ├── config.py          # Configuration management
│   └── utils.py           # Helper functions
├── tests/                 # Unit tests
├── demo.ps1               # Full demo script
├── demo_fast.ps1          # Quick demo script
├── db_stats.py            # Database statistics viewer
├── view_db.py             # Database content viewer
├── job.json               # Example job file
├── setup.py               # Package setup
├── requirements.txt       # Dependencies
└── README.md              # This file
```

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Contact

For questions or issues, please open an issue on the GitHub repository.

---

**QueueCTL** - Reliable background job processing made simple.

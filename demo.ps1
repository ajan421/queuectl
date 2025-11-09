# QueueCTL Complete Demo Script for Video Recording
# Run this script to demonstrate all features in ~2 minutes

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "  QueueCTL - Complete Feature Demo" -ForegroundColor Cyan
Write-Host "===================================================`n" -ForegroundColor Cyan

# ============================================
# STEP 0: Clean Database (Fresh Start)
# ============================================
Write-Host "[0] Cleaning database for fresh start..." -ForegroundColor Yellow
queuectl worker stop 2>$null | Out-Null
Start-Sleep -Milliseconds 200
Remove-Item $env:USERPROFILE\.queuectl\* -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

# ============================================
# STEP 1: Initial Status (Empty System)
# ============================================
Write-Host "`n[1] Initial Status - Empty System" -ForegroundColor Green
queuectl status
Start-Sleep -Milliseconds 500

# ============================================
# STEP 2: Enqueue Basic Jobs
# ============================================
Write-Host "`n[2] Enqueueing Jobs..." -ForegroundColor Green

# Create temporary job files
'{"id":"job1","command":"echo Job 1 completed"}' | Out-File -FilePath temp_job1.json -Encoding ASCII -NoNewline
'{"id":"job2","command":"echo Job 2 completed"}' | Out-File -FilePath temp_job2.json -Encoding ASCII -NoNewline
'{"id":"job3","command":"echo Job 3 completed"}' | Out-File -FilePath temp_job3.json -Encoding ASCII -NoNewline

queuectl enqueue -f temp_job1.json
queuectl enqueue -f temp_job2.json
queuectl enqueue -f temp_job3.json

Write-Host "`nListing Pending Jobs:" -ForegroundColor Cyan
queuectl list --state pending
Start-Sleep -Milliseconds 500

# ============================================
# STEP 3: Single Worker Demo
# ============================================
Write-Host "`n[3] Starting Single Worker..." -ForegroundColor Green
queuectl worker start --count 1
Start-Sleep -Milliseconds 1200

Write-Host "`nChecking Status After Processing:" -ForegroundColor Cyan
queuectl status
Start-Sleep -Milliseconds 500

Write-Host "`nCompleted Jobs:" -ForegroundColor Cyan
queuectl list --state completed
Start-Sleep -Milliseconds 500

queuectl worker stop
Start-Sleep -Milliseconds 300

# ============================================
# STEP 4: Priority Queue Demo
# ============================================
Write-Host "`n[4] Testing Priority Queues..." -ForegroundColor Green

'{"id":"low-priority","command":"echo Low Priority","priority":0}' | Out-File -FilePath temp_low.json -Encoding ASCII -NoNewline
'{"id":"high-priority","command":"echo High Priority","priority":10}' | Out-File -FilePath temp_high.json -Encoding ASCII -NoNewline
'{"id":"medium-priority","command":"echo Medium Priority","priority":5}' | Out-File -FilePath temp_medium.json -Encoding ASCII -NoNewline

queuectl enqueue -f temp_low.json
queuectl enqueue -f temp_high.json
queuectl enqueue -f temp_medium.json

Write-Host "`nPending Jobs (ordered by priority):" -ForegroundColor Cyan
queuectl list --state pending

queuectl worker start --count 1
Start-Sleep -Milliseconds 1200
queuectl worker stop
Start-Sleep -Milliseconds 300

# ============================================
# STEP 5: Multiple Workers (Parallel)
# ============================================
Write-Host "`n[5] Multiple Workers - Parallel Processing..." -ForegroundColor Green

'{"id":"parallel1","command":"echo Parallel Job 1"}' | Out-File -FilePath temp_p1.json -Encoding ASCII -NoNewline
'{"id":"parallel2","command":"echo Parallel Job 2"}' | Out-File -FilePath temp_p2.json -Encoding ASCII -NoNewline
'{"id":"parallel3","command":"echo Parallel Job 3"}' | Out-File -FilePath temp_p3.json -Encoding ASCII -NoNewline

queuectl enqueue -f temp_p1.json
queuectl enqueue -f temp_p2.json
queuectl enqueue -f temp_p3.json

Write-Host "`nStarting 3 Workers for Parallel Processing:" -ForegroundColor Cyan
queuectl worker start --count 3
Start-Sleep -Milliseconds 1200

queuectl status
queuectl worker stop
Start-Sleep -Milliseconds 300

# ============================================
# STEP 6: Retry & Exponential Backoff
# ============================================
Write-Host "`n[6] Testing Retry with Exponential Backoff..." -ForegroundColor Green

'{"id":"fail-job","command":"nonexistent-command","max_retries":2}' | Out-File -FilePath temp_fail.json -Encoding ASCII -NoNewline

queuectl enqueue -f temp_fail.json

queuectl worker start --count 1
Write-Host "`nWaiting for retries (2^1=2s, 2^2=4s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 7

Write-Host "`nChecking Failed Jobs:" -ForegroundColor Cyan
queuectl list --state failed
queuectl worker stop
Start-Sleep -Milliseconds 300

# ============================================
# STEP 7: Dead Letter Queue
# ============================================
Write-Host "`n[7] Dead Letter Queue (DLQ)..." -ForegroundColor Green

Write-Host "`nWaiting for job to move to DLQ..." -ForegroundColor Yellow
queuectl worker start --count 1
Start-Sleep -Seconds 5
queuectl worker stop

Write-Host "`nDLQ Contents:" -ForegroundColor Cyan
queuectl dlq list
Start-Sleep -Milliseconds 500

Write-Host "`nRetrying Job from DLQ:" -ForegroundColor Cyan
queuectl dlq retry fail-job
Start-Sleep -Milliseconds 300

# ============================================
# STEP 8: Configuration Management
# ============================================
Write-Host "`n[8] Configuration Management..." -ForegroundColor Green

Write-Host "`nCurrent Configuration:" -ForegroundColor Cyan
queuectl config get
Start-Sleep -Milliseconds 500

Write-Host "`nChanging Max Retries to 5:" -ForegroundColor Cyan
queuectl config set max-retries 5

Write-Host "`nVerifying Change:" -ForegroundColor Cyan
queuectl config get max-retries
Start-Sleep -Milliseconds 500

# ============================================
# STEP 9: Job Timeout Demo
# ============================================
Write-Host "`n[9] Testing Job Timeout..." -ForegroundColor Green

'{"id":"timeout-job","command":"timeout /t 60 /nobreak","timeout":3}' | Out-File -FilePath temp_timeout.json -Encoding ASCII -NoNewline

queuectl enqueue -f temp_timeout.json

queuectl worker start --count 1
Write-Host "`nWaiting for timeout (3 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 4

Write-Host "`nJob should have timed out:" -ForegroundColor Cyan
queuectl list --state failed
queuectl worker stop
Start-Sleep -Milliseconds 300

# ============================================
# STEP 10: Database Inspection
# ============================================
Write-Host "`n[10] Database Inspection..." -ForegroundColor Green

Write-Host "`nDatabase Statistics:" -ForegroundColor Cyan
python db_stats.py
Start-Sleep -Milliseconds 500

# ============================================
# STEP 11: Final Status & Cleanup
# ============================================
Write-Host "`n[11] Final Status & Summary..." -ForegroundColor Green

Write-Host "`nProcessing Remaining Jobs:" -ForegroundColor Cyan
queuectl worker start --count 2
Start-Sleep -Milliseconds 1500
queuectl worker stop

Write-Host "`nFinal System Status:" -ForegroundColor Cyan
queuectl status
Start-Sleep -Milliseconds 500

Write-Host "`nAll Completed Jobs:" -ForegroundColor Cyan
queuectl list --state completed

# Cleanup temp files
Remove-Item temp_*.json -Force -ErrorAction SilentlyContinue

# ============================================
# END
# ============================================
Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "  Demo Complete! All Features Demonstrated" -ForegroundColor Cyan
Write-Host "===================================================`n" -ForegroundColor Cyan

Write-Host "Database Location: $env:USERPROFILE\.queuectl\jobs.db" -ForegroundColor Gray
Write-Host "Total Runtime: ~60 seconds" -ForegroundColor Gray
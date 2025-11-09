# QueueCTL Fast Demo - Silent Workers, Quick Execution
# Total Runtime: ~30 seconds

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "  QueueCTL - Fast Demo (Silent Mode)" -ForegroundColor Cyan
Write-Host "===================================================`n" -ForegroundColor Cyan

# Clean Start
Write-Host "[0] Cleaning database..." -ForegroundColor Yellow
queuectl worker stop 2>$null | Out-Null
Start-Sleep -Milliseconds 200
Remove-Item $env:USERPROFILE\.queuectl\* -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 200

# Initial Status
Write-Host "`n[1] Initial Status" -ForegroundColor Green
queuectl status

# Enqueue Jobs
Write-Host "`n[2] Enqueueing 3 Jobs..." -ForegroundColor Green
'{"id":"job1","command":"echo Job 1"}' | Out-File temp1.json -Encoding ASCII -NoNewline
'{"id":"job2","command":"echo Job 2"}' | Out-File temp2.json -Encoding ASCII -NoNewline
'{"id":"job3","command":"echo Job 3"}' | Out-File temp3.json -Encoding ASCII -NoNewline
queuectl enqueue -f temp1.json | Out-Null
queuectl enqueue -f temp2.json | Out-Null
queuectl enqueue -f temp3.json | Out-Null
queuectl list --state pending

# Single Worker
Write-Host "`n[3] Single Worker Processing..." -ForegroundColor Green
Start-Job -ScriptBlock { queuectl worker start --count 1 } | Out-Null
Start-Sleep -Seconds 2
queuectl status
queuectl list --state completed
queuectl worker stop | Out-Null

# Priority Queue
Write-Host "`n[4] Priority Queue Demo..." -ForegroundColor Green
'{"id":"low","command":"echo Low","priority":0}' | Out-File temp_low.json -Encoding ASCII -NoNewline
'{"id":"high","command":"echo High","priority":10}' | Out-File temp_high.json -Encoding ASCII -NoNewline
'{"id":"med","command":"echo Med","priority":5}' | Out-File temp_med.json -Encoding ASCII -NoNewline
queuectl enqueue -f temp_low.json | Out-Null
queuectl enqueue -f temp_high.json | Out-Null
queuectl enqueue -f temp_med.json | Out-Null
queuectl list --state pending
Start-Job -ScriptBlock { queuectl worker start --count 1 } | Out-Null
Start-Sleep -Seconds 2
queuectl worker stop | Out-Null

# Multiple Workers
Write-Host "`n[5] Multiple Workers (Parallel)..." -ForegroundColor Green
'{"id":"p1","command":"echo P1"}' | Out-File temp_p1.json -Encoding ASCII -NoNewline
'{"id":"p2","command":"echo P2"}' | Out-File temp_p2.json -Encoding ASCII -NoNewline
'{"id":"p3","command":"echo P3"}' | Out-File temp_p3.json -Encoding ASCII -NoNewline
queuectl enqueue -f temp_p1.json | Out-Null
queuectl enqueue -f temp_p2.json | Out-Null
queuectl enqueue -f temp_p3.json | Out-Null
Start-Job -ScriptBlock { queuectl worker start --count 3 } | Out-Null
Start-Sleep -Seconds 2
queuectl status
queuectl worker stop | Out-Null

# Retry Demo
Write-Host "`n[6] Retry & Exponential Backoff..." -ForegroundColor Green
'{"id":"fail","command":"bad-cmd","max_retries":2}' | Out-File temp_fail.json -Encoding ASCII -NoNewline
queuectl enqueue -f temp_fail.json | Out-Null
Start-Job -ScriptBlock { queuectl worker start --count 1 } | Out-Null
Write-Host "Waiting for retries (2s, 4s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 7
queuectl list --state failed
queuectl worker stop | Out-Null

# DLQ
Write-Host "`n[7] Dead Letter Queue..." -ForegroundColor Green
Start-Job -ScriptBlock { queuectl worker start --count 1 } | Out-Null
Start-Sleep -Seconds 5
queuectl worker stop | Out-Null
queuectl dlq list
queuectl dlq retry fail | Out-Null
Write-Host "Job retried from DLQ" -ForegroundColor Cyan

# Config
Write-Host "`n[8] Configuration..." -ForegroundColor Green
queuectl config get
queuectl config set max-retries 5 | Out-Null
queuectl config get max-retries

# Timeout
Write-Host "`n[9] Job Timeout Test..." -ForegroundColor Green
'{"id":"timeout","command":"timeout /t 60 /nobreak","timeout":2}' | Out-File temp_timeout.json -Encoding ASCII -NoNewline
queuectl enqueue -f temp_timeout.json | Out-Null
Start-Job -ScriptBlock { queuectl worker start --count 1 } | Out-Null
Write-Host "Waiting for timeout (2s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
queuectl list --state failed
queuectl worker stop | Out-Null

# Database Stats
Write-Host "`n[10] Database Statistics..." -ForegroundColor Green
python db_stats.py

# Final Summary
Write-Host "`n[11] Final Summary..." -ForegroundColor Green
Start-Job -ScriptBlock { queuectl worker start --count 2 } | Out-Null
Start-Sleep -Seconds 2
queuectl worker stop | Out-Null
queuectl status
queuectl list --state completed

# Cleanup
Remove-Item temp*.json -Force -ErrorAction SilentlyContinue
Get-Job | Remove-Job -Force 2>$null

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "  Demo Complete! (~30 seconds)" -ForegroundColor Cyan
Write-Host "===================================================`n" -ForegroundColor Cyan


# Enqueue all job files
Write-Host "Enqueuing all jobs..." -ForegroundColor Green

$jobFiles = @("job.json", "job1.json", "job2.json", "job3.json", "job4.json", "job5.json")

foreach ($file in $jobFiles) {
    if (Test-Path $file) {
        Write-Host "Enqueuing $file..." -ForegroundColor Yellow
        queuectl enqueue -f $file
        Start-Sleep -Milliseconds 500
    } else {
        Write-Host "File $file not found, skipping..." -ForegroundColor Red
    }
}

Write-Host "`nAll jobs enqueued! Check status with: queuectl status" -ForegroundColor Green


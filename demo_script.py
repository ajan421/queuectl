#!/usr/bin/env python3
"""Demo script to validate QueueCTL core flows."""

import subprocess
import time
import json
import os
import sys


def run_command(cmd):
    """Run a command and return output."""
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def main():
    """Run demo script to validate QueueCTL."""
    print("=" * 60)
    print("QueueCTL Demo Script - Core Flow Validation")
    print("=" * 60)
    
    # Check if queuectl is installed
    result = subprocess.run("queuectl --version", shell=True, capture_output=True)
    if result.returncode != 0:
        print("\nError: queuectl not found. Please install it first:")
        print("  pip install -e .")
        sys.exit(1)
    
    # Clean up any existing workers
    print("\n1. Cleaning up any existing workers...")
    run_command("queuectl worker stop")
    
    # Show initial status
    print("\n2. Initial status:")
    run_command("queuectl status")
    
    # Test 1: Enqueue a simple job
    print("\n3. Test 1: Enqueue a simple successful job")
    job1 = {
        "id": "demo-job-1",
        "command": "echo 'Hello from QueueCTL'"
    }
    run_command(f"queuectl enqueue '{json.dumps(job1)}'")
    
    # Start a worker
    print("\n4. Starting a worker...")
    run_command("queuectl worker start --count 1")
    
    # Wait for job to complete
    print("\n5. Waiting for job to complete...")
    time.sleep(3)
    
    # Check status
    print("\n6. Status after job completion:")
    run_command("queuectl status")
    
    # List completed jobs
    print("\n7. List completed jobs:")
    run_command("queuectl list --state completed")
    
    # Test 2: Enqueue a job that will fail
    print("\n8. Test 2: Enqueue a job that will fail")
    job2 = {
        "id": "demo-job-2",
        "command": "nonexistent-command-12345",
        "max_retries": 2
    }
    run_command(f"queuectl enqueue '{json.dumps(job2)}'")
    
    # Wait for retries and DLQ movement
    print("\n9. Waiting for retries and DLQ movement...")
    time.sleep(10)
    
    # Check status
    print("\n10. Status after retries:")
    run_command("queuectl status")
    
    # Check DLQ
    print("\n11. Dead Letter Queue:")
    run_command("queuectl dlq list")
    
    # Test 3: Retry a DLQ job
    print("\n12. Test 3: Retry a job from DLQ")
    run_command("queuectl dlq retry demo-job-2")
    
    # Wait for processing
    print("\n13. Waiting for retry...")
    time.sleep(5)
    
    # Check status
    print("\n14. Status after DLQ retry:")
    run_command("queuectl status")
    
    # Test 4: Multiple workers
    print("\n15. Test 4: Start multiple workers")
    run_command("queuectl worker stop")
    time.sleep(1)
    run_command("queuectl worker start --count 3")
    
    # Enqueue multiple jobs
    print("\n16. Enqueue multiple jobs...")
    for i in range(5):
        job = {
            "id": f"demo-job-parallel-{i}",
            "command": f"echo 'Job {i}' && sleep 1"
        }
        run_command(f"queuectl enqueue '{json.dumps(job)}'")
    
    # Wait for processing
    print("\n17. Waiting for parallel processing...")
    time.sleep(8)
    
    # Check status
    print("\n18. Final status:")
    run_command("queuectl status")
    
    # Test 5: Configuration
    print("\n19. Test 5: Configuration management")
    run_command("queuectl config get")
    run_command("queuectl config set max-retries 5")
    run_command("queuectl config get max-retries")
    
    # Cleanup
    print("\n20. Cleaning up...")
    run_command("queuectl worker stop")
    
    print("\n" + "=" * 60)
    print("Demo script completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""Tests for job manager."""

import unittest
import os
import tempfile
from queuectl.job_manager import JobManager
from queuectl.storage import Storage
from queuectl.config import Config


class TestJobManager(unittest.TestCase):
    """Test job manager operations."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.temp_config = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_config.close()
        
        self.storage = Storage(self.temp_db.name)
        self.config = Config(self.temp_config.name)
        self.job_manager = JobManager(self.storage, self.config)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        if os.path.exists(self.temp_config.name):
            os.unlink(self.temp_config.name)
    
    def test_enqueue(self):
        """Test enqueuing a job."""
        job_data = {
            'id': 'test-enqueue-1',
            'command': 'echo hello'
        }
        
        job = self.job_manager.enqueue(job_data)
        self.assertIsNotNone(job)
        self.assertEqual(job['id'], 'test-enqueue-1')
        self.assertEqual(job['state'], 'pending')
        self.assertEqual(job['attempts'], 0)
    
    def test_mark_completed(self):
        """Test marking a job as completed."""
        job_data = {
            'id': 'test-complete-1',
            'command': 'echo hello'
        }
        
        self.job_manager.enqueue(job_data)
        self.job_manager.mark_completed('test-complete-1')
        
        job = self.job_manager.get_job('test-complete-1')
        self.assertEqual(job['state'], 'completed')
    
    def test_mark_failed_with_retry(self):
        """Test marking a job as failed with retry."""
        job_data = {
            'id': 'test-fail-1',
            'command': 'nonexistent',
            'max_retries': 3
        }
        
        self.job_manager.enqueue(job_data)
        
        # First failure
        should_retry = self.job_manager.mark_failed('test-fail-1')
        self.assertTrue(should_retry)
        
        job = self.job_manager.get_job('test-fail-1')
        self.assertEqual(job['state'], 'failed')
        self.assertEqual(job['attempts'], 1)
        self.assertIsNotNone(job['next_retry_at'])
    
    def test_mark_failed_move_to_dlq(self):
        """Test moving job to DLQ after max retries."""
        job_data = {
            'id': 'test-dlq-1',
            'command': 'nonexistent',
            'max_retries': 2
        }
        
        self.job_manager.enqueue(job_data)
        
        # First failure
        self.job_manager.mark_failed('test-dlq-1')
        
        # Second failure
        self.job_manager.mark_failed('test-dlq-1')
        
        # Third failure - should move to DLQ
        should_retry = self.job_manager.mark_failed('test-dlq-1')
        self.assertFalse(should_retry)
        
        job = self.job_manager.get_job('test-dlq-1')
        self.assertEqual(job['state'], 'dead')
        self.assertEqual(job['attempts'], 3)


if __name__ == '__main__':
    unittest.main()


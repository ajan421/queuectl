"""Tests for storage layer."""

import unittest
import os
import tempfile
from queuectl.storage import Storage


class TestStorage(unittest.TestCase):
    """Test storage operations."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.storage = Storage(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_create_job(self):
        """Test job creation."""
        job_data = {
            'id': 'test-job-1',
            'command': 'echo hello',
            'state': 'pending',
            'attempts': 0,
            'max_retries': 3,
            'created_at': '2025-01-01T00:00:00Z',
            'updated_at': '2025-01-01T00:00:00Z'
        }
        
        result = self.storage.create_job(job_data)
        self.assertTrue(result)
        
        # Try to create duplicate
        result = self.storage.create_job(job_data)
        self.assertFalse(result)
    
    def test_get_job(self):
        """Test getting a job."""
        job_data = {
            'id': 'test-job-2',
            'command': 'echo hello',
            'state': 'pending',
            'attempts': 0,
            'max_retries': 3,
            'created_at': '2025-01-01T00:00:00Z',
            'updated_at': '2025-01-01T00:00:00Z'
        }
        
        self.storage.create_job(job_data)
        
        job = self.storage.get_job('test-job-2')
        self.assertIsNotNone(job)
        self.assertEqual(job['id'], 'test-job-2')
        self.assertEqual(job['command'], 'echo hello')
    
    def test_list_jobs(self):
        """Test listing jobs."""
        # Create multiple jobs
        for i in range(5):
            job_data = {
                'id': f'test-job-{i}',
                'command': f'echo {i}',
                'state': 'pending' if i % 2 == 0 else 'completed',
                'attempts': 0,
                'max_retries': 3,
                'created_at': '2025-01-01T00:00:00Z',
                'updated_at': '2025-01-01T00:00:00Z'
            }
            self.storage.create_job(job_data)
        
        # List all jobs
        all_jobs = self.storage.list_jobs()
        self.assertEqual(len(all_jobs), 5)
        
        # List pending jobs
        pending_jobs = self.storage.list_jobs(state='pending')
        self.assertEqual(len(pending_jobs), 3)
        
        # List completed jobs
        completed_jobs = self.storage.list_jobs(state='completed')
        self.assertEqual(len(completed_jobs), 2)


if __name__ == '__main__':
    unittest.main()


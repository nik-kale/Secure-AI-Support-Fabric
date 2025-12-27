import time
import unittest
from unittest.mock import patch, MagicMock
from lab.common.rate_limit import RateLimiter

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        self.limiter = RateLimiter()

    def test_allow_single_request(self):
        allowed, meta = self.limiter.is_allowed('1.2.3.4', 'default', 10, 60)
        self.assertTrue(allowed)
        self.assertEqual(meta['remaining'], 9)
        self.assertEqual(meta['limit'], 10)

    def test_block_excess_requests(self):
        # Allow 2 requests
        self.limiter.is_allowed('1.2.3.4', 'default', 2, 60)
        self.limiter.is_allowed('1.2.3.4', 'default', 2, 60)
        
        # 3rd request should fail
        allowed, meta = self.limiter.is_allowed('1.2.3.4', 'default', 2, 60)
        self.assertFalse(allowed)
        self.assertEqual(meta['remaining'], 0)

    def test_separate_limits_by_ip(self):
        # IP 1 uses all quota
        self.limiter.is_allowed('1.1.1.1', 'default', 1, 60)
        allowed1, _ = self.limiter.is_allowed('1.1.1.1', 'default', 1, 60)
        self.assertFalse(allowed1)

        # IP 2 should still be allowed
        allowed2, _ = self.limiter.is_allowed('2.2.2.2', 'default', 1, 60)
        self.assertTrue(allowed2)

    def test_separate_limits_by_tier(self):
        # Tier A uses all quota
        self.limiter.is_allowed('1.1.1.1', 'tierA', 1, 60)
        allowed1, _ = self.limiter.is_allowed('1.1.1.1', 'tierA', 1, 60)
        self.assertFalse(allowed1)

        # Tier B should still be allowed for same IP
        allowed2, _ = self.limiter.is_allowed('1.1.1.1', 'tierB', 1, 60)
        self.assertTrue(allowed2)

    @patch('time.time')
    def test_window_reset(self, mock_time):
        # Start at time 1000
        mock_time.return_value = 1000.0
        
        # Use up quota
        self.limiter.is_allowed('1.2.3.4', 'default', 1, 10)
        allowed, _ = self.limiter.is_allowed('1.2.3.4', 'default', 1, 10)
        self.assertFalse(allowed)

        # Advance time past window (1000 + 11 = 1011)
        mock_time.return_value = 1011.0
        
        # Should be allowed again
        allowed, _ = self.limiter.is_allowed('1.2.3.4', 'default', 1, 10)
        self.assertTrue(allowed)

    @patch('time.time')
    def test_cleanup(self, mock_time):
        mock_time.return_value = 1000.0
        self.limiter._last_cleanup = 1000.0
        
        # Add entry
        self.limiter.is_allowed('1.2.3.4', 'default', 10, 60)
        
        # Access internal storage to verify
        self.assertTrue(self.limiter._requests['1.2.3.4']['default'])
        
        # Advance time by 2 hours (cleanup threshold is 1 hour)
        mock_time.return_value = 1000.0 + 7200.0
        
        # Trigger cleanup by making a request
        self.limiter.is_allowed('5.6.7.8', 'other', 10, 60)
        
        # Old entry should be gone
        timestamps = self.limiter._requests['1.2.3.4']['default']
        self.assertEqual(len(timestamps), 0)

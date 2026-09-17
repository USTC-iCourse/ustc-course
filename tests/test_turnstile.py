import io
import unittest
from urllib.error import URLError
from unittest.mock import patch
from app import app
from app.utils import verify_turnstile

class TurnstileTests(unittest.TestCase):
    def setUp(self):
        self.config = patch.dict(app.config, TURNSTILE_SITE_KEY='test-site', TURNSTILE_SECRET_KEY='test-secret')
        self.config.start()
        self.addCleanup(self.config.stop)

    def test_missing_response_is_rejected_without_network(self):
        with patch('app.utils.urllib.request.urlopen') as fetch:
            self.assertFalse(verify_turnstile(''))
            fetch.assert_not_called()

    def test_successful_cloudflare_verification_is_accepted(self):
        with patch('app.utils.urllib.request.urlopen', return_value=io.BytesIO(b'{"success": true}')):
            self.assertTrue(verify_turnstile('test-response'))

    def test_cloudflare_rejection_is_rejected(self):
        with patch('app.utils.urllib.request.urlopen', return_value=io.BytesIO(b'{"success": false}')):
            self.assertFalse(verify_turnstile('test-response'))

    def test_network_failure_is_rejected(self):
        with patch('app.utils.urllib.request.urlopen', side_effect=URLError('unavailable')):
            self.assertFalse(verify_turnstile('test-response'))

    def test_unreadable_response_is_rejected(self):
        with patch('app.utils.urllib.request.urlopen', return_value=io.BytesIO(b'not JSON')):
            self.assertFalse(verify_turnstile('test-response'))

if __name__ == '__main__':
    unittest.main()

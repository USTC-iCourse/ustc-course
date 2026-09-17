import unittest
from unittest.mock import patch
from app import app
from app.utils import trusted_signin_callback

class CallbackTests(unittest.TestCase):
    def test_registered_https_destination(self):
        with patch.dict(app.config, THIRD_PARTY_SIGNIN_REDIRECTS=['https://partner.example/callback'], THIRD_PARTY_SIGNIN_REDIRECT_ALIASES={}):
            self.assertEqual(trusted_signin_callback('https://partner.example/callback'), 'https://partner.example/callback')

    def test_legacy_alias_uses_registered_https_destination(self):
        with patch.dict(app.config, THIRD_PARTY_SIGNIN_REDIRECTS=['https://partner.example/callback'], THIRD_PARTY_SIGNIN_REDIRECT_ALIASES={'http://partner.example/callback': 'https://partner.example/callback'}):
            self.assertEqual(trusted_signin_callback('http://partner.example/callback'), 'https://partner.example/callback')

    def test_alias_does_not_implicitly_register_destination(self):
        with patch.dict(app.config, THIRD_PARTY_SIGNIN_REDIRECTS=[], THIRD_PARTY_SIGNIN_REDIRECT_ALIASES={'legacy': 'https://partner.example/callback'}):
            self.assertIsNone(trusted_signin_callback('legacy'))
            self.assertIsNone(trusted_signin_callback('https://partner.example/callback'))

if __name__ == '__main__':
    unittest.main()

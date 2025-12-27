import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, jsonify
from lab.common.auth import APIKeyAuth, require_auth, get_auth

class TestAuth(unittest.TestCase):
    def test_verify_valid_key(self):
        auth = APIKeyAuth(api_keys={'valid-key'})
        self.assertTrue(auth.verify_api_key('valid-key'))

    def test_verify_invalid_key(self):
        auth = APIKeyAuth(api_keys={'valid-key'})
        self.assertFalse(auth.verify_api_key('invalid-key'))
        self.assertFalse(auth.verify_api_key(''))
        self.assertFalse(auth.verify_api_key(None))

    def test_load_from_env(self):
        with patch.dict('os.environ', {'API_KEYS': 'key1,key2, key3 '}):
            auth = APIKeyAuth()
            self.assertTrue(auth.verify_api_key('key1'))
            self.assertTrue(auth.verify_api_key('key2'))
            self.assertTrue(auth.verify_api_key('key3'))
            self.assertFalse(auth.verify_api_key('key4'))

    def test_dev_mode_warning(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertLogs('lab.common.auth', level='WARNING') as cm:
                auth = APIKeyAuth()
                self.assertTrue(any('DO NOT USE IN PRODUCTION' in m for m in cm.output))
                self.assertTrue(auth.verify_api_key('dev-key-DO-NOT-USE-IN-PRODUCTION'))

    def test_decorator_success(self):
        app = Flask(__name__)
        
        # Reset singleton for testing
        import lab.common.auth
        lab.common.auth._auth_instance = APIKeyAuth(api_keys={'secret'})
        
        @app.route('/test')
        @require_auth
        def test_route():
            return 'success'

        with app.test_client() as client:
            resp = client.get('/test', headers={'X-API-Key': 'secret'})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data.decode(), 'success')

    def test_decorator_missing_key(self):
        app = Flask(__name__)
        import lab.common.auth
        lab.common.auth._auth_instance = APIKeyAuth(api_keys={'secret'})
        
        @app.route('/test')
        @require_auth
        def test_route():
            return 'success'

        with app.test_client() as client:
            resp = client.get('/test')
            self.assertEqual(resp.status_code, 401)
            self.assertIn('Missing API key', resp.json['error'])

    def test_decorator_invalid_key(self):
        app = Flask(__name__)
        import lab.common.auth
        lab.common.auth._auth_instance = APIKeyAuth(api_keys={'secret'})
        
        @app.route('/test')
        @require_auth
        def test_route():
            return 'success'

        with app.test_client() as client:
            resp = client.get('/test', headers={'X-API-Key': 'wrong'})
            self.assertEqual(resp.status_code, 401)
            self.assertIn('Invalid API key', resp.json['error'])

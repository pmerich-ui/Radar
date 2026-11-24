import os
import unittest
from unittest.mock import patch

from src.awin_api_fallback import discover, _clean, _read_json


class TestAwinApiFallback(unittest.TestCase):
    @patch.dict(os.environ, {'AWIN_API_TOKEN': ''})
    def test_missing_token_blocks_without_network(self):
        def forbidden(_):
            self.fail('network used')
        result = discover(read_json=forbidden)
        self.assertEqual(result['reason'], 'AWIN_API_TOKEN_MISSING')
        self.assertEqual(result['publishable_deals'], 0)

    @patch.dict(os.environ, {'AWIN_API_TOKEN': 'sensitive-token'})
    def test_joined_merchants_no_publication_or_links(self):
        paths = []
        def read(path):
            paths.append(path)
            if path.startswith('/accounts'):
                return {'accounts': [{'accountType': 'publisher', 'accountId': 12345}]}
            return [{'id': 456, 'name': 'Merchant', 'primaryRegion': 'CH',
                     'clickThroughUrl': 'https://example.org/?secret=never-expose'}]
        result = discover(read_json=read)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['joined_merchants'], 1)
        self.assertEqual(result['publishable_deals'], 0)
        self.assertFalse(result['publishing_enabled'])
        self.assertTrue(result['merchants'][0]['clickthrough_metadata_present'])
        self.assertNotIn('example.org', str(result))
        self.assertNotIn('sensitive-token', str(result))
        self.assertEqual(paths[1], '/publishers/12345/programmes?relationship=joined')

    @patch.dict(os.environ, {'AWIN_API_TOKEN': 'token'})
    def test_no_publishers_blocked(self):
        result = discover(read_json=lambda _: [])
        self.assertEqual(result['reason'], 'EXPECTED_ONE_PUBLISHER')

    @patch.dict(os.environ, {'AWIN_API_TOKEN': 'token'})
    def test_api_exceptions_redacted(self):
        def broken(_):
            raise RuntimeError('Bearer secret-should-never-appear')
        result = discover(read_json=broken)
        self.assertEqual(result['reason'], 'AWIN_API_READ_FAILED')
        self.assertNotIn('secret-should-never-appear', str(result))

    @patch.dict(os.environ, {'AWIN_API_TOKEN': 'token'})
    def test_reject_invalid_programme_response(self):
        def read(path):
            return [{'accountType': 'publisher', 'accountId': 42}] if path.startswith('/accounts') else {'programmes': 'bad'}
        self.assertEqual(discover(read_json=read)['reason'], 'UNEXPECTED_PROGRAMMES_RESPONSE')

    def test_clean_control_characters(self):
        self.assertEqual(_clean('Hello\r\nWorld'), 'Hello World')

    @patch.dict(os.environ, {'AWIN_API_TOKEN': 'token'})
    def test_invalid_route_without_network(self):
        with self.assertRaises(ValueError):
            _read_json('/evil')


if __name__ == '__main__':
    unittest.main()

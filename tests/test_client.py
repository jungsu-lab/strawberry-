import unittest
from unittest.mock import patch

from libsbapi.client import SBAPIClient


class _ApiResponse:
    def json(self):
        return {"result": False}


class SBAPIClientTest(unittest.TestCase):
    def test_repr_redacts_authorization_key(self):
        client = SBAPIClient("secret-token")

        representation = repr(client)

        self.assertIn("key='***'", representation)
        self.assertNotIn("secret-token", representation)

    def test_send_uses_configured_timeout(self):
        client = SBAPIClient("secret-token", timeout=12.5)

        with patch("libsbapi.client.requests.post", return_value=_ApiResponse()) as post:
            with self.assertRaises(SBAPIClient._NetworkError):
                client._send(b"\x00")

        self.assertEqual(post.call_args.kwargs["timeout"], 12.5)

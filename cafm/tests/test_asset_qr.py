from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from cafm.asset_qr import get_asset_qr_url


class TestAssetQRCode(FrappeTestCase):
    def test_qr_url_opens_the_encoded_asset_route(self):
        with patch("cafm.asset_qr.get_url", return_value="https://cafm.example.com"):
            self.assertEqual(
                get_asset_qr_url("AHU 01/West"),
                "https://cafm.example.com/app/asset/AHU%2001%2FWest",
            )

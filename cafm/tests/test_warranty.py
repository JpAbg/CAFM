from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from cafm.warranty import (
    get_warranty_status,
    update_asset_warranty_status,
    validate_warranty_claim,
)


class TestWarrantyStatus(FrappeTestCase):
    def test_warranty_statuses_are_calculated_from_dates(self):
        self.assertEqual(
            get_warranty_status("2026-01-01", "2026-12-31", "2026-08-31"),
            "Active",
        )
        self.assertEqual(
            get_warranty_status("2026-01-01", "2026-09-15", "2026-08-31"),
            "Expiring Soon",
        )
        self.assertEqual(
            get_warranty_status("2026-01-01", "2026-08-30", "2026-08-31"),
            "Expired",
        )
        self.assertEqual(
            get_warranty_status("2026-10-01", "2027-10-01", "2026-08-31"),
            "Pending",
        )

    def test_warranty_without_an_expiry_date_is_not_covered(self):
        self.assertEqual(
            get_warranty_status("2026-01-01", None, "2026-08-31"),
            "Not Covered",
        )

    def test_reversed_warranty_dates_are_rejected(self):
        asset = frappe._dict(
            custom_warranty_start_date="2026-12-31",
            custom_warranty_expiry_date="2026-01-01",
        )
        with self.assertRaises(frappe.ValidationError):
            update_asset_warranty_status(asset)

    def test_active_warranty_claim_is_allowed_and_expired_claim_is_rejected(self):
        work_order = frappe._dict(
            warranty_claim=1,
            asset="TEST-ASSET",
            planned_start="2026-08-31 09:00:00",
            actual_start=None,
            creation="2026-08-31 08:00:00",
        )
        with patch(
            "cafm.warranty.frappe.db.get_value",
            return_value=frappe._dict(
                custom_warranty_start_date="2026-01-01",
                custom_warranty_expiry_date="2026-12-31",
            ),
        ):
            validate_warranty_claim(work_order)

        with patch(
            "cafm.warranty.frappe.db.get_value",
            return_value=frappe._dict(
                custom_warranty_start_date="2025-01-01",
                custom_warranty_expiry_date="2026-08-30",
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                validate_warranty_claim(work_order)

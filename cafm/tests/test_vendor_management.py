import frappe
from frappe.tests.utils import FrappeTestCase

from cafm.cafm.doctype.facility_service_contract.facility_service_contract import (
    contract_covers_work_order,
)
from cafm.cafm.doctype.facility_vendor_quotation.facility_vendor_quotation import (
    FacilityVendorQuotation,
)


class TestVendorManagement(FrappeTestCase):
    def test_contract_scope_matches_the_correct_work_order(self):
        contract = frappe._dict(
            company="Test Company",
            contract_status="Active",
            start_date="2026-01-01",
            end_date="2026-12-31",
            service_provider="Test Provider",
            scope_type="Service Category",
            service_category="HVAC",
        )
        work_order = frappe._dict(
            company="Test Company",
            vendor="Test Provider",
            facility_location="Test Location",
            asset="Test Asset",
            category="HVAC",
        )
        self.assertTrue(contract_covers_work_order(contract, work_order))
        work_order.category = "Electrical"
        self.assertFalse(contract_covers_work_order(contract, work_order))

    def test_quotation_total_includes_tax(self):
        quotation = frappe._dict(quoted_amount=1000, tax_amount=110)
        FacilityVendorQuotation.calculate_total(quotation)
        self.assertEqual(quotation.total_amount, 1110)

from frappe.tests.utils import FrappeTestCase

from cafm.sla import calculate_sla_status


class TestSla(FrappeTestCase):
    def test_response_breach_precedes_resolution_due_date(self):
        status = calculate_sla_status(
            "2026-09-01 09:00:00",
            "2026-09-01 12:00:00",
            reference_datetime="2026-09-01 10:00:00",
        )
        self.assertEqual(status, "Response Breached")

    def test_resolved_work_order_meets_sla_when_both_targets_are_met(self):
        status = calculate_sla_status(
            "2026-09-01 09:00:00",
            "2026-09-01 12:00:00",
            response_achieved_on="2026-09-01 08:30:00",
            resolution_achieved_on="2026-09-01 11:30:00",
            reference_datetime="2026-09-01 13:00:00",
        )
        self.assertEqual(status, "Met")

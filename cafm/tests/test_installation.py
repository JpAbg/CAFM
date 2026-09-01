import frappe
from frappe.tests.utils import FrappeTestCase

from cafm import hooks
from cafm.setup.install import ROLES, setup_cafm


WORKFLOWS = (
    "CAFM Maintenance Request Workflow",
    "CAFM Facility Work Order Workflow",
    "CAFM Facility Inspection Workflow",
)

REPORTS = (
    "Asset Maintenance History",
    "Maintenance Cost Report",
    "Maintenance Request Report",
    "Preventive Maintenance Report",
    "Technician Performance Report",
    "Work Order Report",
)

DASHBOARD_CHARTS = (
    "Asset Downtime",
    "Maintenance Cost by Site and Building",
    "Preventive Maintenance Compliance",
    "Top Recurring Asset Failures",
    "Work Order by Category",
    "Work Orders by Priority",
)

NUMBER_CARDS = (
    "Average Resolution Time",
    "Average Response Time",
    "Open Maintenance Requests",
    "Overdue Work Orders",
)


class TestCAFMInstallation(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_required_apps_and_install_hooks_are_declared(self):
        self.assertEqual(hooks.required_apps, ["erpnext", "hrms"])
        self.assertEqual(
            hooks.after_install,
            "cafm.setup.install.after_install",
        )
        self.assertEqual(
            hooks.after_migrate,
            "cafm.setup.install.after_migrate",
        )

    def test_setup_is_complete_and_idempotent(self):
        setup_cafm()
        first_counts = self.configuration_counts()
        setup_cafm()
        second_counts = self.configuration_counts()
        self.assertEqual(first_counts, second_counts)

        for role in ROLES:
            self.assertTrue(frappe.db.exists("Role", role))

        for priority in ("Critical", "High", "Medium", "Low"):
            self.assertTrue(frappe.db.exists("Issue Priority", priority))

        for workflow_name in WORKFLOWS:
            workflow = frappe.get_doc("Workflow", workflow_name)
            self.assertTrue(workflow.is_active)

        self.assertEqual(
            frappe.db.get_value(
                "Custom Field",
                {
                    "dt": "Asset",
                    "fieldname": "custom_asset_location",
                },
                ["label", "options", "reqd"],
            ),
            ("Facility Location", "Facility Location", 1),
        )
        self.assertEqual(
            frappe.db.get_value(
                "Custom Field",
                {"dt": "Asset", "fieldname": "custom_asset_qr_code"},
                ["label", "fieldtype", "read_only"],
            ),
            ("Asset QR Code", "Attach Image", 1),
        )
        self.assertEqual(
            frappe.db.get_value(
                "Property Setter",
                {
                    "doc_type": "Asset",
                    "field_name": "location",
                    "property": "hidden",
                },
                "value",
            ),
            "1",
        )
        self.assertEqual(
            frappe.db.get_value(
                "Property Setter",
                {
                    "doc_type": "Asset",
                    "field_name": "location",
                    "property": "reqd",
                },
                "value",
            ),
            "0",
        )

    def test_packaged_reports_dashboard_and_scheduler_exist(self):
        self.assertTrue(frappe.db.exists("DocType", "Facility Service Contract"))
        self.assertTrue(frappe.db.exists("DocType", "Facility Vendor Quotation"))
        self.assertTrue(
            frappe.db.exists(
                "Dashboard",
                "Facility Management Dashboard",
            )
        )
        for report in REPORTS:
            self.assertTrue(
                frappe.db.exists("Report", report),
                f"Missing packaged report: {report}",
            )
        for chart in DASHBOARD_CHARTS:
            self.assertTrue(
                frappe.db.exists("Dashboard Chart", chart),
                f"Missing packaged dashboard chart: {chart}",
            )
        for card in NUMBER_CARDS:
            self.assertTrue(
                frappe.db.exists("Number Card", card),
                f"Missing packaged number card: {card}",
            )

        scheduler_events = hooks.scheduler_events
        self.assertIn("cafm.tasks.daily", scheduler_events["daily"])
        self.assertIn("cafm.tasks.hourly", scheduler_events["hourly"])
        self.assertTrue(
            frappe.db.exists(
                "Scheduled Job Type",
                {"method": "cafm.tasks.daily"},
            )
        )
        self.assertTrue(
            frappe.db.exists(
                "Scheduled Job Type",
                {"method": "cafm.tasks.hourly"},
            )
        )

    def configuration_counts(self):
        return {
            "roles": frappe.db.count(
                "Role", {"name": ["in", list(ROLES)]}
            ),
            "workflows": frappe.db.count(
                "Workflow", {"name": ["in", list(WORKFLOWS)]}
            ),
            "asset_location_fields": frappe.db.count(
                "Custom Field",
                {
                    "dt": "Asset",
                    "fieldname": "custom_asset_location",
                },
            ),
            "asset_location_setters": frappe.db.count(
                "Property Setter",
                {
                    "doc_type": "Asset",
                    "field_name": "location",
                    "property": ["in", ["hidden", "reqd"]],
                },
            ),
            "cafm_location_roots": frappe.db.count(
                "Location", {"name": "CAFM Locations"}
            ),
        }


class TestMaintenanceCostChart(FrappeTestCase):
    def test_sites_are_x_axis_and_full_building_names_are_datasets(self):
        from cafm.cafm.report.maintenance_cost_report.maintenance_cost_report import (
            get_chart,
        )

        chart = get_chart(
            [
                frappe._dict(
                    site="Headquarters Site",
                    building="HQ-01",
                    building_name="Main Administration Building",
                    material_cost=100,
                ),
                frappe._dict(
                    site="Headquarters Site",
                    building="HQ-01",
                    building_name="Main Administration Building",
                    material_cost=25,
                ),
                frappe._dict(
                    site="Headquarters Site",
                    building="HQ-02",
                    building_name="Technical Services Annex",
                    material_cost=50,
                ),
                frappe._dict(
                    site="Regional Branch",
                    building="BR-01",
                    building_name="Customer Service Center",
                    material_cost=80,
                ),
            ]
        )

        self.assertEqual(
            chart["data"]["labels"],
            ["Headquarters Site", "Regional Branch"],
        )
        self.assertEqual(
            chart["data"]["datasets"],
            [
                {
                    "name": "Customer Service Center",
                    "values": [None, 80.0],
                },
                {
                    "name": "Main Administration Building",
                    "values": [125.0, None],
                },
                {
                    "name": "Technical Services Annex",
                    "values": [50.0, None],
                },
            ],
        )

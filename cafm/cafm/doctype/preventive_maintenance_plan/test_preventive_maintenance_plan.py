# Copyright (c) 2026, Jean Paul Abou Gharib and Contributors
# See license.txt

import frappe
from cafm.tests.factories import ensure_test_company
from frappe.tests.utils import FrappeTestCase

from cafm.notifications import send_upcoming_preventive_reminders
from cafm.preventive_maintenance import (
    generate_occurrence,
    generate_preventive_work_orders,
    get_next_due_date,
)

test_ignore = [
    "Asset",
    "Company",
    "Employee",
    "Facility Inspection Template",
    "Facility Location",
    "Facility Service Provider",
    "Facility Work Order",
    "Issue Priority",
    "Issue Type",
]


class TestPreventiveMaintenancePlan(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        ensure_test_company(self)
        self.suffix = frappe.generate_hash(length=6)
        self.location = self.make_location()
        self.issue_type = self.make_issue_type()
        self.asset = self.make_asset()

    def tearDown(self):
        frappe.set_user("Administrator")

    def make_location(self):
        site = frappe.get_doc(
            {
                "doctype": "Site",
                "company": self.company,
                "site_name": f"PM Test Site {self.suffix}",
                "site_id": f"PM-S-{self.suffix}",
                "site_type": "HQ",
                "address": "Preventive maintenance test address",
            }
        ).insert(ignore_permissions=True)
        building = frappe.get_doc(
            {
                "doctype": "Building",
                "site": site.name,
                "building_name": f"PM Building {self.suffix}",
                "building_id": f"PM-B-{self.suffix}",
                "building_type": "Office",
            }
        ).insert(ignore_permissions=True)
        floor = frappe.get_doc(
            {
                "doctype": "Floor",
                "building": building.name,
                "floor_name": "Plant Floor",
                "floor_level": 1,
                "floor_type": "Workspace",
            }
        ).insert(ignore_permissions=True)
        room = frappe.get_doc(
            {
                "doctype": "Room",
                "floor": floor.name,
                "room_name": f"Mechanical Room {self.suffix}",
                "room_id": f"PM-R-{self.suffix}",
                "room_type": "Server Room",
            }
        ).insert(ignore_permissions=True)
        return frappe.get_doc(
            {
                "doctype": "Facility Location",
                "site": site.name,
                "building": building.name,
                "floor": floor.name,
                "room": room.name,
            }
        ).insert(ignore_permissions=True).name

    def make_issue_type(self):
        name = f"Preventive Test {self.suffix}"
        frappe.get_doc(
            {
                "doctype": "Issue Type",
                "__newname": name,
            }
        ).insert(ignore_permissions=True)
        return name

    def make_asset(self):
        category = f"CAFM Test Asset Category {self.suffix}"
        fixed_asset_account = frappe.db.get_value(
            "Account",
            {
                "company": self.company,
                "account_type": "Fixed Asset",
                "is_group": 0,
            },
            "name",
        )
        self.assertTrue(fixed_asset_account)
        frappe.get_doc(
            {
                "doctype": "Asset Category",
                "asset_category_name": category,
                "accounts": [
                    {
                        "company_name": self.company,
                        "fixed_asset_account": fixed_asset_account,
                    }
                ],
            }
        ).insert(ignore_permissions=True)

        item_code = f"CAFM-PM-ASSET-{self.suffix}"
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "description": "Preventive maintenance test asset",
                "asset_category": category,
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "is_fixed_asset": 1,
                "auto_create_assets": 0,
            }
        ).insert(ignore_permissions=True)

        erpnext_location = frappe.get_doc(
            {
                "doctype": "Location",
                "location_name": f"CAFM PM Location {self.suffix}",
            }
        ).insert(ignore_permissions=True)

        asset = frappe.get_doc(
            {
                "doctype": "Asset",
                "asset_name": f"CAFM PM Asset {self.suffix}",
                "item_code": item_code,
                "asset_category": category,
                "company": self.company,
                "purchase_date": "2025-01-01",
                "available_for_use_date": "2025-01-01",
                "gross_purchase_amount": 1000,
                "purchase_amount": 1000,
                "calculate_depreciation": 0,
                "is_existing_asset": 1,
                "asset_owner": "Company",
                "location": erpnext_location.name,
                "custom_asset_location": self.location,
            }
        ).insert(ignore_permissions=True)
        asset.submit()
        return asset.name

    def test_all_supported_frequency_calculations(self):
        cases = {
            "Daily": "2026-02-01",
            "Weekly": "2026-02-07",
            "Monthly": "2026-02-28",
            "Quarterly": "2026-04-30",
            "Yearly": "2027-01-31",
        }
        for frequency, expected in cases.items():
            with self.subTest(frequency=frequency):
                self.assertEqual(
                    str(get_next_due_date("2026-01-31", frequency)),
                    expected,
                )

    def test_scheduler_generates_one_work_order_and_advances_plan(self):
        plan = frappe.get_doc(
            {
                "doctype": "Preventive Maintenance Plan",
                "plan_name": f"Monthly HVAC Service {self.suffix}",
                "company": self.company,
                "asset": self.asset,
                "facility_location": self.location,
                "category": self.issue_type,
                "priority": "High",
                "frequency": "Monthly",
                "start_date": "2026-01-31",
                "next_due_date": "2026-01-31",
                "generate_before_days": 0,
                "planned_duration_hours": 3,
                "instructions": "Inspect and service the HVAC unit.",
                "checklist": [
                    {
                        "description": "Inspect filters",
                        "is_required": 1,
                        "instructions": "Replace damaged filters.",
                    },
                    {
                        "description": "Measure operating temperature",
                        "is_required": 1,
                    },
                ],
            }
        ).insert(ignore_permissions=True)

        generated = generate_preventive_work_orders("2026-01-31", [plan.name])
        self.assertEqual(len(generated), 1)

        work_order = frappe.get_doc("Facility Work Order", generated[0])
        self.assertEqual(work_order.work_order_type, "Preventive")
        self.assertEqual(work_order.preventive_maintenance_plan, plan.name)
        self.assertEqual(str(work_order.scheduled_occurrence_date), "2026-01-31")
        self.assertEqual(work_order.asset, self.asset)
        self.assertEqual(work_order.facility_location, self.location)
        self.assertEqual(len(work_order.checklist), 2)
        self.assertEqual(work_order.checklist[0].result, "Pending")
        self.assertEqual(
            work_order.preventive_occurrence_key,
            f"{plan.name}::2026-01-31",
        )

        plan.reload()
        self.assertEqual(str(plan.next_due_date), "2026-02-28")
        self.assertEqual(plan.last_work_order, work_order.name)

        second_run = generate_preventive_work_orders("2026-01-31", [plan.name])
        self.assertEqual(second_run, [])
        self.assertEqual(
            generate_occurrence(plan, "2026-01-31"),
            work_order.name,
        )
        self.assertEqual(
            frappe.db.count(
                "Facility Work Order",
                {
                    "preventive_occurrence_key":
                        f"{plan.name}::2026-01-31",
                },
            ),
            1,
        )

    def test_upcoming_reminder_is_sent_once_per_occurrence(self):
        manager_user = f"cafm.pm.manager.{self.suffix}@example.com"
        frappe.get_doc(
            {
                "doctype": "User",
                "email": manager_user,
                "first_name": "Preventive Manager",
                "enabled": 1,
                "send_welcome_email": 0,
                "user_type": "System User",
                "roles": [{"role": "Facility Manager"}],
            }
        ).insert(ignore_permissions=True)

        plan = frappe.get_doc(
            {
                "doctype": "Preventive Maintenance Plan",
                "plan_name": f"Upcoming PM Reminder {self.suffix}",
                "company": self.company,
                "asset": self.asset,
                "facility_location": self.location,
                "category": self.issue_type,
                "priority": "Medium",
                "frequency": "Monthly",
                "start_date": "2098-01-05",
                "next_due_date": "2098-01-05",
                "generate_before_days": 0,
                "planned_duration_hours": 2,
                "instructions": "Perform the scheduled inspection.",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)

        for _ in range(2):
            self.assertEqual(
                send_upcoming_preventive_reminders(
                    reference_date="2098-01-01",
                    reminder_days=7,
                ),
                [plan.name],
            )

        reminder_title = (
            f"Upcoming Preventive Maintenance: "
            f"{plan.plan_name} on 2098-01-05"
        )
        self.assertEqual(
            frappe.db.count(
                "Notification Log",
                {
                    "type": "Alert",
                    "title": reminder_title,
                    "document_type": "Preventive Maintenance Plan",
                    "document_name": plan.name,
                    "for_user": manager_user,
                },
            ),
            1,
        )

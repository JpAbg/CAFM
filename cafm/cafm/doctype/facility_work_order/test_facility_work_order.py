# Copyright (c) 2026, Jean Paul Abou Gharib and Contributors
# See license.txt

import base64
from unittest.mock import patch

import frappe
from cafm.tests.factories import (
    ensure_test_company,
    make_test_asset,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import (
    make_stock_entry,
)
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase

from cafm.api import (
    create_maintenance_request,
    get_work_order,
    list_assigned_work_orders,
    list_maintenance_requests,
    submit_technician_resolution,
    update_work_order_status,
    upload_work_order_attachment,
)
from cafm.cafm.doctype.facility_inspection.facility_inspection import (
    create_from_work_order,
)
from cafm.asset_maintenance import (
    get_asset_maintenance_history,
    get_open_maintenance_work,
)
from cafm.cafm.doctype.facility_work_order.facility_work_order import (
    create_from_issue,
)
from cafm.cafm.report.maintenance_cost_report.maintenance_cost_report import (
    execute as execute_maintenance_cost_report,
)
from cafm.inspections import (
    generate_inspection_occurrence,
    generate_scheduled_inspections,
)
from cafm.materials import issue_materials
from cafm.notifications import (
    notify_overdue_work_orders,
    send_daily_overdue_summary,
)

test_ignore = [
    "Asset",
    "Batch",
    "Company",
    "Employee",
    "Facility Inspection Template",
    "Facility Location",
    "Facility Service Provider",
    "Issue",
    "Issue Priority",
    "Issue Type",
    "Item",
    "Preventive Maintenance Plan",
    "Stock Entry",
    "UOM",
    "User",
    "Warehouse",
]


class TestFacilityWorkOrder(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        ensure_test_company(self)
        self.suffix = frappe.generate_hash(length=6)
        self.requester_user = self.make_user(
            f"cafm.requester.{self.suffix}@example.com",
            "Requester / Employee",
        )
        self.other_requester_user = self.make_user(
            f"cafm.other.{self.suffix}@example.com",
            "Requester / Employee",
        )
        self.technician_user = self.make_user(
            f"cafm.technician.{self.suffix}@example.com",
            "Technician",
        )
        self.coordinator_user = self.make_user(
            f"cafm.coordinator.{self.suffix}@example.com",
            "Facility Coordinator",
        )
        self.manager_user = self.make_user(
            f"cafm.manager.{self.suffix}@example.com",
            "Facility Manager",
        )
        self.requester = self.make_employee(
            self.requester_user, f"Requester {self.suffix}"
        )
        self.other_requester = self.make_employee(
            self.other_requester_user, f"Other {self.suffix}"
        )
        self.technician = self.make_employee(
            self.technician_user, f"Technician {self.suffix}"
        )
        self.issue_type = self.make_issue_type()
        technician = frappe.get_doc("Employee", self.technician)
        technician.custom_is_facility_technician = 1
        technician.custom_primary_specialization = "General Maintenance"
        technician.custom_max_active_work_orders = 5
        technician.append(
            "custom_service_categories",
            {"service_category": self.issue_type, "is_primary": 1},
        )
        technician.save(ignore_permissions=True)
        self.location = self.make_location()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.flags.in_import = False

    def make_user(self, email, role):
        frappe.flags.in_import = True
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": role,
                "enabled": 1,
                "send_welcome_email": 0,
                "user_type": "System User",
                "roles": [{"role": role}],
            }
        ).insert(ignore_permissions=True)
        frappe.flags.in_import = False
        frappe.clear_cache(user=email)
        return user.name

    def make_employee(self, user, first_name):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "first_name": first_name,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01",
                "status": "Active",
                "company": self.company,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)
        return employee.name

    def make_issue_type(self):
        name = f"CAFM Test {self.suffix}"
        frappe.get_doc(
            {
                "doctype": "Issue Type",
                "__newname": name,
            }
        ).insert(ignore_permissions=True)
        return name

    def make_location(self):
        site = frappe.get_doc(
            {
                "doctype": "Site",
                "company": self.company,
                "site_name": f"CAFM Test Site {self.suffix}",
                "site_id": f"TEST-{self.suffix}",
                "site_type": "HQ",
                "address": "Test address",
            }
        ).insert(ignore_permissions=True)
        building = frappe.get_doc(
            {
                "doctype": "Building",
                "site": site.name,
                "building_name": f"Building {self.suffix}",
                "building_id": f"BLD-{self.suffix}",
                "building_type": "Office",
            }
        ).insert(ignore_permissions=True)
        floor = frappe.get_doc(
            {
                "doctype": "Floor",
                "building": building.name,
                "floor_name": "Ground Floor",
                "floor_level": 0,
                "floor_type": "Office",
            }
        ).insert(ignore_permissions=True)
        room = frappe.get_doc(
            {
                "doctype": "Room",
                "floor": floor.name,
                "room_name": f"Room {self.suffix}",
                "room_id": f"R-{self.suffix}",
                "room_type": "Workspace",
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

    def make_inspection_template(self):
        return frappe.get_doc(
            {
                "doctype": "Facility Inspection Template",
                "template_name": f"CAFM Test Inspection {self.suffix}",
                "category": self.issue_type,
                "is_active": 1,
                "items": [
                    {
                        "inspection_point": "Verify repair quality",
                        "is_required": 1,
                    },
                    {
                        "inspection_point": "Check housekeeping",
                        "is_required": 0,
                    },
                ],
            }
        ).insert(ignore_permissions=True).name

    def make_service_provider(self, vendor_user=None, tag=None):
        supplier_group = (
            frappe.db.exists("Supplier Group", "Services")
            or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
        )
        provider_tag = tag or self.suffix
        supplier_name = f"CAFM Test Provider {provider_tag}"
        frappe.get_doc(
            {
                "doctype": "Supplier",
                "supplier_name": supplier_name,
                "supplier_group": supplier_group,
                "supplier_type": "Company",
            }
        ).insert(ignore_permissions=True)
        return frappe.get_doc(
            {
                "doctype": "Facility Service Provider",
                "provider_name": supplier_name,
                "supplier": supplier_name,
                "company": self.company,
                "status": "Active",
                "primary_specialization": "General Maintenance",
                "service_phone": "+961 1 555 999",
                "vendor_user": vendor_user,
                "service_categories": [
                    {
                        "service_category": self.issue_type,
                        "is_primary": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True).name

    def test_required_failed_inspection_blocks_closure_until_override(self):
        template = self.make_inspection_template()

        frappe.set_user(self.requester_user)
        issue = frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": f"Inspection-gated request {self.suffix}",
                "description": "Repair requires supervisor inspection.",
                "company": self.company,
                "custom_facility_location": self.location,
                "issue_type": self.issue_type,
                "priority": "High",
            }
        ).insert()

        frappe.set_user(self.coordinator_user)
        work_order_name = create_from_issue(issue.name)
        work_order = frappe.get_doc("Facility Work Order", work_order_name)
        work_order.assignment_type = "Internal Technician"
        work_order.technician = self.technician
        work_order.inspection_required = 1
        work_order.inspection_template = template
        work_order.planned_start = frappe.utils.now_datetime()
        work_order.save()
        apply_workflow(work_order, "Assign")

        with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
            inspection_name = create_from_work_order(work_order.name)
        self.assertTrue(
            any(
                "tabFacility Work Order" in str(call.args[0])
                and "FOR UPDATE" in str(call.args[0])
                for call in sql.call_args_list
            )
        )
        inspection = frappe.get_doc("Facility Inspection", inspection_name)
        self.assertEqual(len(inspection.results), 2)
        apply_workflow(inspection, "Assign Inspection")

        frappe.set_user(self.technician_user)
        work_order.reload()
        apply_workflow(work_order, "Start Work")
        work_order.reload()
        work_order.resolution_summary = "Repair completed for inspection."
        work_order.save()
        apply_workflow(work_order, "Resolve")

        inspection.reload()
        apply_workflow(inspection, "Start Inspection")
        inspection.reload()
        inspection.results[0].result = "Fail"
        inspection.results[0].comments = "Repair finish requires review."
        inspection.results[1].result = "Pass"
        inspection.save()
        apply_workflow(inspection, "Complete Inspection")
        inspection.reload()
        self.assertEqual(inspection.overall_result, "Fail")

        frappe.set_user(self.manager_user)
        work_order.reload()
        with self.assertRaises(frappe.ValidationError):
            apply_workflow(work_order, "Close")

        inspection.reload()
        with self.assertRaises(frappe.ValidationError):
            apply_workflow(inspection, "Approve Inspection")

        inspection.reload()
        inspection.override_failure = 1
        inspection.override_reason = "Safe temporary repair approved by supervisor."
        inspection.save()
        apply_workflow(inspection, "Approve Inspection")
        inspection.reload()
        self.assertEqual(inspection.status, "Approved")
        self.assertEqual(inspection.override_by, self.manager_user)

        work_order.reload()
        apply_workflow(work_order, "Close")
        work_order.reload()
        self.assertEqual(work_order.work_order_status, "Closed")

        frappe.set_user(self.other_requester_user)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list(
                "Facility Inspection",
                filters={"name": inspection.name},
                pluck="name",
            )

    def test_inspection_schedule_is_duplicate_safe(self):
        template = self.make_inspection_template()
        schedule = frappe.get_doc(
            {
                "doctype": "Facility Inspection Schedule",
                "schedule_name": f"Monthly Inspection {self.suffix}",
                "inspection_template": template,
                "company": self.company,
                "facility_location": self.location,
                "category": self.issue_type,
                "inspector": self.technician,
                "frequency": "Monthly",
                "start_date": "2026-01-31",
                "next_due_date": "2026-01-31",
                "generate_before_days": 0,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)

        generated = generate_scheduled_inspections(
            "2026-01-31",
            [schedule.name],
        )
        self.assertEqual(len(generated), 1)

        inspection = frappe.get_doc("Facility Inspection", generated[0])
        self.assertEqual(inspection.inspection_schedule, schedule.name)
        self.assertEqual(str(inspection.occurrence_date), "2026-01-31")
        self.assertEqual(len(inspection.results), 2)

        schedule.reload()
        self.assertEqual(str(schedule.next_due_date), "2026-02-28")
        self.assertEqual(schedule.last_inspection, inspection.name)
        self.assertEqual(
            generate_scheduled_inspections(
                "2026-01-31",
                [schedule.name],
            ),
            [],
        )
        self.assertEqual(
            generate_inspection_occurrence(schedule, "2026-01-31"),
            inspection.name,
        )
        self.assertEqual(
            frappe.db.count(
                "Facility Inspection",
                {
                    "occurrence_key":
                        f"{schedule.name}::2026-01-31",
                },
            ),
            1,
        )

    def test_material_issue_updates_stock_cost_and_prevents_duplicates(self):
        item_code = f"CAFM-MATERIAL-{self.suffix}"
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "description": "CAFM test spare part",
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 1,
            }
        ).insert(ignore_permissions=True)
        frappe.set_user(self.requester_user)
        issue = frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": f"Material issue request {self.suffix}",
                "description": "Repair requires a spare part.",
                "company": self.company,
                "custom_facility_location": self.location,
                "issue_type": self.issue_type,
                "priority": "High",
            }
        ).insert()

        frappe.set_user(self.coordinator_user)
        work_order_name = create_from_issue(issue.name)
        work_order = frappe.get_doc("Facility Work Order", work_order_name)
        company_abbr = frappe.db.get_value(
            "Company", work_order.company, "abbr"
        )
        warehouse = f"Stores - {company_abbr}"
        self.assertEqual(
            frappe.db.get_value("Warehouse", warehouse, "company"),
            work_order.company,
        )
        frappe.set_user("Administrator")
        make_stock_entry(
            item_code=item_code,
            target=warehouse,
            company=work_order.company,
            qty=10,
            basic_rate=25,
        )
        initial_qty = frappe.db.get_value(
            "Bin",
            {"item_code": item_code, "warehouse": warehouse},
            "actual_qty",
        )
        frappe.set_user(self.coordinator_user)
        work_order.assignment_type = "Internal Technician"
        work_order.technician = self.technician
        work_order.planned_start = frappe.utils.now_datetime()
        work_order.append(
            "materials",
            {
                "item_code": item_code,
                "warehouse": warehouse,
                "quantity": 2,
            },
        )
        work_order.save()
        apply_workflow(work_order, "Assign")

        frappe.set_user(self.technician_user)
        work_order.reload()
        apply_workflow(work_order, "Start Work")
        work_order.reload()
        stock_entry_name = issue_materials(work_order.name)

        stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
        work_order.reload()
        material = work_order.materials[0]
        self.assertEqual(stock_entry.docstatus, 1)
        self.assertEqual(stock_entry.purpose, "Material Issue")
        self.assertEqual(
            stock_entry.custom_facility_work_order,
            work_order.name,
        )
        self.assertEqual(material.stock_entry, stock_entry.name)
        self.assertEqual(
            stock_entry.items[0].custom_facility_work_order_material,
            material.name,
        )
        self.assertGreater(work_order.material_cost, 0)
        self.assertEqual(
            frappe.db.get_value(
                "Bin",
                {"item_code": item_code, "warehouse": warehouse},
                "actual_qty",
            ),
            initial_qty - 2,
        )
        self.assertEqual(
            issue_materials(work_order.name),
            stock_entry.name,
        )

        work_order.reload()
        work_order.materials[0].quantity = 3
        with self.assertRaises(frappe.ValidationError):
            work_order.save()

        frappe.set_user("Administrator")
        stock_entry.reload()
        stock_entry.cancel()
        work_order.reload()
        self.assertFalse(work_order.materials[0].stock_entry)
        self.assertEqual(work_order.material_cost, 0)

        frappe.set_user(self.technician_user)
        work_order.materials[0].quantity = initial_qty + 1
        work_order.save()
        with self.assertRaises(frappe.ValidationError):
            issue_materials(work_order.name)

        work_order.reload()
        work_order.materials[0].quantity = 2
        work_order.save()
        replacement_stock_entry = issue_materials(work_order.name)
        self.assertNotEqual(replacement_stock_entry, stock_entry.name)

        work_order.reload()
        work_order.resolution_summary = "Repair completed with issued part."
        work_order.save()
        apply_workflow(work_order, "Resolve")

        frappe.set_user(self.manager_user)
        work_order.reload()
        apply_workflow(work_order, "Close")
        work_order.reload()
        self.assertEqual(work_order.work_order_status, "Closed")

        frappe.set_user("Administrator")
        replacement = frappe.get_doc(
            "Stock Entry",
            replacement_stock_entry,
        )
        with self.assertRaises(frappe.ValidationError):
            replacement.cancel()

    def test_out_of_service_asset_lists_only_open_maintenance_work(self):
        frappe.set_user("Administrator")
        asset = make_test_asset(
            self.company,
            self.location,
            self.suffix,
            f"CAFM visibility asset {self.suffix}",
        )

        self.assertEqual(
            asset.location,
            frappe.db.get_value(
                "Facility Location",
                self.location,
                "erpnext_location",
            ),
        )

        frappe.set_user(self.requester_user)
        issue = frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": f"Out of service asset {self.suffix}",
                "description": "The asset requires active maintenance.",
                "company": self.company,
                "custom_facility_location": self.location,
                "custom_asset": asset.name,
                "issue_type": self.issue_type,
                "priority": "High",
            }
        ).insert()

        frappe.set_user(self.coordinator_user)
        work_order_name = create_from_issue(issue.name)
        work_order = frappe.get_doc(
            "Facility Work Order",
            work_order_name,
        )
        work_order.assignment_type = "Internal Technician"
        work_order.technician = self.technician
        work_order.planned_start = frappe.utils.now_datetime()
        work_order.save()
        apply_workflow(work_order, "Assign")

        frappe.set_user(self.manager_user)
        open_work = get_open_maintenance_work(asset.name)
        self.assertEqual(
            [row.name for row in open_work],
            [work_order_name],
        )

        frappe.set_user(self.technician_user)
        work_order.reload()
        apply_workflow(work_order, "Start Work")
        work_order.reload()
        work_order.resolution_summary = (
            "Asset restored after corrective maintenance."
        )
        work_order.save()
        apply_workflow(work_order, "Resolve")

        frappe.set_user(self.manager_user)
        work_order.reload()
        apply_workflow(work_order, "Close")
        work_order.reload()
        self.assertEqual(get_open_maintenance_work(asset.name), [])

        history = get_asset_maintenance_history(asset.name)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].work_order, work_order.name)
        self.assertEqual(
            history[0].resolution_summary,
            work_order.resolution_summary,
        )
        self.assertEqual(
            frappe.db.count(
                "Facility Asset Maintenance History",
                {"work_order": work_order.name},
            ),
            1,
        )

        work_order.save()
        self.assertEqual(
            frappe.db.count(
                "Facility Asset Maintenance History",
                {"work_order": work_order.name},
            ),
            1,
        )

    def test_category_rule_automatically_raises_request_priority(self):
        frappe.set_user("Administrator")
        frappe.db.set_value(
            "Issue Type",
            self.issue_type,
            "custom_cafm_minimum_priority",
            "Critical",
        )

        frappe.set_user(self.requester_user)
        issue = frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": f"Critical category request {self.suffix}",
                "description": (
                    "Request priority must be raised automatically."
                ),
                "company": self.company,
                "custom_facility_location": self.location,
                "issue_type": self.issue_type,
                "priority": "Low",
            }
        ).insert()
        self.assertEqual(issue.priority, "Critical")

        issue.priority = "Low"
        issue.save()
        self.assertEqual(issue.priority, "Critical")

    def test_external_service_provider_assignment(self):
        provider_name = self.make_service_provider()

        frappe.set_user(self.requester_user)
        issue = frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": f"External provider request {self.suffix}",
                "description": "Contractor service is required.",
                "company": self.company,
                "custom_facility_location": self.location,
                "issue_type": self.issue_type,
                "priority": "Medium",
            }
        ).insert()

        frappe.set_user(self.coordinator_user)
        work_order_name = create_from_issue(issue.name)
        work_order = frappe.get_doc("Facility Work Order", work_order_name)
        work_order.assignment_type = "External Vendor"
        work_order.vendor = provider_name
        work_order.planned_start = frappe.utils.now_datetime()
        work_order.save()
        apply_workflow(work_order, "Assign")

        work_order.reload()
        provider = frappe.get_doc("Facility Service Provider", provider_name)
        self.assertEqual(work_order.work_order_status, "Assigned")
        self.assertEqual(work_order.vendor, provider_name)
        self.assertEqual(provider.availability, "Assigned")
        self.assertFalse(
            frappe.db.exists(
                "ToDo",
                {
                    "reference_type": "Facility Work Order",
                    "reference_name": work_order.name,
                    "status": "Open",
                },
            )
        )

    def test_vendor_access_is_limited_to_own_external_work(self):
        frappe.set_user("Administrator")
        vendor_user = self.make_user(
            f"cafm.vendor.{self.suffix}@example.com",
            "Vendor",
        )
        other_vendor_user = self.make_user(
            f"cafm.other.vendor.{self.suffix}@example.com",
            "Vendor",
        )
        provider = self.make_service_provider(
            vendor_user,
            f"A-{self.suffix}",
        )
        other_provider = self.make_service_provider(
            other_vendor_user,
            f"B-{self.suffix}",
        )

        frappe.set_user(self.requester_user)
        issue = frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": f"Vendor access request {self.suffix}",
                "description": "External contractor work is required.",
                "company": self.company,
                "custom_facility_location": self.location,
                "issue_type": self.issue_type,
                "priority": "High",
            }
        ).insert()

        frappe.set_user(self.coordinator_user)
        work_order_name = create_from_issue(issue.name)
        work_order = frappe.get_doc(
            "Facility Work Order",
            work_order_name,
        )
        work_order.assignment_type = "External Vendor"
        work_order.vendor = provider
        work_order.planned_start = frappe.utils.now_datetime()
        work_order.save()
        apply_workflow(work_order, "Assign")

        self.assertTrue(
            frappe.db.exists(
                "ToDo",
                {
                    "reference_type": "Facility Work Order",
                    "reference_name": work_order.name,
                    "allocated_to": vendor_user,
                    "status": "Open",
                },
            )
        )

        frappe.set_user(other_vendor_user)
        self.assertEqual(
            frappe.get_list(
                "Facility Work Order",
                filters={"name": work_order.name},
                pluck="name",
            ),
            [],
        )
        self.assertEqual(
            frappe.get_list(
                "Facility Service Provider",
                pluck="name",
            ),
            [other_provider],
        )
        unrelated = frappe.get_doc(
            "Facility Work Order",
            work_order.name,
        )
        with self.assertRaises(frappe.PermissionError):
            unrelated.check_permission("read")

        frappe.set_user(vendor_user)
        self.assertEqual(
            frappe.get_list(
                "Facility Work Order",
                filters={"name": work_order.name},
                pluck="name",
            ),
            [work_order.name],
        )
        self.assertEqual(
            frappe.get_list(
                "Facility Service Provider",
                pluck="name",
            ),
            [provider],
        )

        work_order.reload()
        apply_workflow(work_order, "Start Work")
        work_order.reload()

        work_order.priority = "Low"
        with self.assertRaises(frappe.PermissionError):
            work_order.save()

        work_order.reload()
        with self.assertRaises(frappe.PermissionError):
            issue_materials(work_order.name)

        work_order.technician_notes = "Vendor completed the repair."
        work_order.resolution_summary = (
            "External contractor restored the equipment."
        )
        work_order.save()
        apply_workflow(work_order, "Resolve")
        work_order.reload()
        self.assertEqual(work_order.work_order_status, "Resolved")

    def test_request_to_closed_work_order_flow_and_permissions(self):
        frappe.set_user(self.requester_user)
        issue = frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": f"CAFM test request {self.suffix}",
                "description": "Air conditioning is not cooling.",
                "company": self.company,
                "custom_facility_location": self.location,
                "issue_type": self.issue_type,
                "priority": "High",
            }
        ).insert()
        self.assertEqual(issue.custom_requester, self.requester)
        self.assertEqual(issue.custom_issue_status, "New")

        frappe.set_user(self.coordinator_user)
        with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
            work_order_name = create_from_issue(issue.name)
        self.assertTrue(
            any(
                "tabIssue" in str(call.args[0])
                and "FOR UPDATE" in str(call.args[0])
                for call in sql.call_args_list
            )
        )
        work_order = frappe.get_doc("Facility Work Order", work_order_name)
        work_order.assignment_type = "Internal Technician"
        work_order.technician = self.technician
        work_order.planned_start = frappe.utils.now_datetime()
        work_order.append(
            "checklist",
            {
                "description": "Confirm cooling restored",
                "is_required": 1,
                "result": "Pending",
            },
        )
        work_order.save()
        apply_workflow(work_order, "Assign")

        work_order.reload()
        self.assertEqual(work_order.work_order_status, "Assigned")
        self.assertTrue(
            frappe.db.exists(
                "ToDo",
                {
                    "reference_type": "Facility Work Order",
                    "reference_name": work_order.name,
                    "allocated_to": self.technician_user,
                    "status": "Open",
                },
            )
        )
        self.assertTrue(
            frappe.db.exists(
                "Notification Log",
                {
                    "type": "Assignment",
                    "document_type": "Facility Work Order",
                    "document_name": work_order.name,
                    "for_user": self.technician_user,
                },
            )
        )
        if frappe.db.exists("DocType", "PWA Notification"):
            self.assertEqual(
                frappe.db.count(
                    "PWA Notification",
                    {
                        "to_user": self.technician_user,
                        "reference_document_type": "Facility Work Order",
                        "reference_document_name": work_order.name,
                        "read": 0,
                    },
                ),
                1,
            )

        frappe.set_user(self.technician_user)
        work_order.reload()
        self.assertIn("Technician", frappe.get_roles())
        self.assertEqual(work_order.technician, self.technician)
        self.assertTrue(
            frappe.has_permission(
                "Facility Work Order",
                ptype="write",
                doc=work_order,
                user=self.technician_user,
            )
        )
        apply_workflow(work_order, "Start Work")
        work_order.reload()
        work_order.checklist[0].result = "Pass"
        work_order.resolution_summary = "Cooling restored after servicing the unit."
        work_order.save()
        apply_workflow(work_order, "Resolve")

        work_order.reload()
        self.assertEqual(work_order.work_order_status, "Resolved")
        issue.reload()
        self.assertEqual(issue.custom_issue_status, "Resolved")
        self.assertEqual(issue.status, "Resolved")

        frappe.set_user(self.manager_user)
        work_order.reload()
        apply_workflow(work_order, "Close")
        work_order.reload()
        issue.reload()
        self.assertEqual(work_order.work_order_status, "Closed")
        self.assertEqual(issue.custom_issue_status, "Closed")
        self.assertEqual(issue.status, "Closed")
        self.assertFalse(
            frappe.db.exists(
                "ToDo",
                {
                    "reference_type": "Facility Work Order",
                    "reference_name": work_order.name,
                    "status": "Open",
                },
            )
        )

        frappe.set_user(self.requester_user)
        self.assertEqual(
            frappe.get_list(
                "Issue",
                filters={"name": issue.name},
                pluck="name",
            ),
            [issue.name],
        )
        self.assertEqual(
            frappe.get_list(
                "Facility Work Order",
                filters={"name": work_order.name},
                pluck="name",
            ),
            [work_order.name],
        )
        report_filters = {
            "company": work_order.company,
            "from_date": "2000-01-01",
            "to_date": "2100-12-31",
        }
        requester_rows = execute_maintenance_cost_report(report_filters)[1]
        self.assertIn(
            work_order.name,
            {row.work_order for row in requester_rows},
        )

        frappe.set_user(self.other_requester_user)
        self.assertEqual(
            frappe.get_list(
                "Issue",
                filters={"name": issue.name},
                pluck="name",
            ),
            [],
        )
        self.assertEqual(
            frappe.get_list(
                "Facility Work Order",
                filters={"name": work_order.name},
                pluck="name",
            ),
            [],
        )
        other_requester_rows = execute_maintenance_cost_report(report_filters)[1]
        self.assertNotIn(
            work_order.name,
            {row.work_order for row in other_requester_rows},
        )

    def test_overdue_alerts_and_daily_summary_are_duplicate_safe(self):
        frappe.set_user(self.requester_user)
        issue = frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": f"Overdue automation request {self.suffix}",
                "description": "Test overdue supervisor automation.",
                "company": self.company,
                "custom_facility_location": self.location,
                "issue_type": self.issue_type,
                "priority": "Critical",
            }
        ).insert()

        frappe.set_user(self.coordinator_user)
        work_order_name = create_from_issue(issue.name)
        work_order = frappe.get_doc("Facility Work Order", work_order_name)
        work_order.assignment_type = "Internal Technician"
        work_order.technician = self.technician
        work_order.planned_start = "2098-01-01 09:00:00"
        work_order.planned_end = "2098-01-02 17:00:00"
        work_order.save()
        apply_workflow(work_order, "Assign")

        reference_datetime = "2098-01-03 09:00:00"
        reference_date = "2098-01-03"
        for _ in range(2):
            self.assertIn(
                work_order.name,
                notify_overdue_work_orders(reference_datetime),
            )
            self.assertGreaterEqual(
                send_daily_overdue_summary(
                    reference_date,
                    reference_datetime,
                ),
                1,
            )

        overdue_title = (
            f"Overdue Work Order {work_order.name}: {work_order.subject}"
        )
        self.assertEqual(
            frappe.db.count(
                "Notification Log",
                {
                    "type": "Alert",
                    "title": overdue_title,
                    "document_type": "Facility Work Order",
                    "document_name": work_order.name,
                    "for_user": self.manager_user,
                },
            ),
            1,
        )

        summary_title = (
            f"Daily Overdue Maintenance Summary - {reference_date}"
        )
        self.assertEqual(
            frappe.db.count(
                "Notification Log",
                {
                    "type": "Alert",
                    "title": summary_title,
                    "for_user": self.manager_user,
                },
            ),
            1,
        )

    def test_authenticated_mobile_api_covers_request_to_resolution(self):
        frappe.set_user(self.requester_user)
        request = create_maintenance_request(
            subject=f"API maintenance request {self.suffix}",
            description="Repair the leaking fixture.",
            facility_location=self.location,
            category=self.issue_type,
            priority="High",
        )
        self.assertEqual(request["facility_location"], self.location)
        self.assertEqual(request["status"], "New")

        request_list = list_maintenance_requests(
            filters={"priority": "High", "search": self.suffix},
            page=1,
            page_length=1,
        )
        self.assertEqual(
            [row["name"] for row in request_list["data"]],
            [request["name"]],
        )
        self.assertFalse(request_list["pagination"]["has_next"])

        frappe.set_user(self.other_requester_user)
        self.assertEqual(
            list_maintenance_requests(
                filters={"name": request["name"]}
            )["data"],
            [],
        )

        frappe.set_user(self.coordinator_user)
        work_order_name = create_from_issue(request["name"])
        work_order = frappe.get_doc("Facility Work Order", work_order_name)
        work_order.assignment_type = "Internal Technician"
        work_order.technician = self.technician
        work_order.planned_start = frappe.utils.now_datetime()
        work_order.save()
        apply_workflow(work_order, "Assign")

        frappe.set_user(self.other_requester_user)
        self.assertRaises(
            frappe.PermissionError,
            get_work_order,
            work_order_name,
        )

        frappe.set_user(self.technician_user)
        assigned = list_assigned_work_orders(
            status="Assigned",
            page=1,
            page_length=10,
        )
        self.assertIn(
            work_order_name,
            [row["name"] for row in assigned["data"]],
        )
        details = get_work_order(work_order_name)
        self.assertEqual(details["technician"], self.technician)

        started = update_work_order_status(
            work_order_name,
            "In Progress",
        )
        self.assertEqual(started["status"], "In Progress")
        self.assertTrue(started["actual_start"])

        pending = update_work_order_status(
            work_order_name,
            "Pending",
            pending_reason="Waiting for an isolation permit.",
        )
        self.assertEqual(pending["status"], "Pending")
        self.assertEqual(
            frappe.db.get_value(
                "Issue",
                request["name"],
                "custom_pending_reason",
            ),
            "Waiting for an isolation permit.",
        )
        resumed = update_work_order_status(work_order_name, "In Progress")
        self.assertEqual(resumed["status"], "In Progress")

        attachment = upload_work_order_attachment(
            work_order_name,
            file_name="repair-note.txt",
            file_content=base64.b64encode(b"Repair evidence").decode(),
        )
        self.assertTrue(attachment["is_private"])
        self.assertEqual(
            frappe.db.get_value("File", attachment["name"], "attached_to_name"),
            work_order_name,
        )

        resolved = submit_technician_resolution(
            work_order_name,
            resolution_summary="Fixture repaired and tested.",
            technician_notes="No further leak was observed.",
        )
        self.assertEqual(resolved["status"], "Resolved")
        self.assertEqual(
            frappe.db.get_value(
                "Issue",
                request["name"],
                "custom_issue_status",
            ),
            "Resolved",
        )
        self.assertIn(
            attachment["name"],
            [row["name"] for row in resolved["attachments"]],
        )

    def test_mobile_api_rejects_guest_access(self):
        frappe.set_user("Guest")
        self.assertRaises(
            frappe.AuthenticationError,
            list_maintenance_requests,
        )

    def test_required_role_permission_matrix_is_installed(self):
        expected = {
            "Asset": {
                "Facility Manager": {"read", "write", "create", "report"},
                "Facility Coordinator": {"read", "write", "create", "report"},
                "Technician": {"read"},
                "Requester / Employee": {"read"},
                "Vendor": {"read"},
            },
            "Issue": {
                "Facility Manager": {"read", "write", "create", "report"},
                "Facility Coordinator": {"read", "write", "create", "report"},
                "Requester / Employee": {"read", "write", "create"},
                "Technician": {"read"},
            },
            "Facility Work Order": {
                "Facility Manager": {"read", "write", "create", "report"},
                "Facility Coordinator": {"read", "write", "create", "report"},
                "Technician": {"read", "write"},
                "Requester / Employee": {"read"},
                "Vendor": {"read", "write"},
            },
            "Facility Service Provider": {
                "Facility Manager": {"read", "write", "create", "report"},
                "Facility Coordinator": {"read", "write", "create", "report"},
                "Vendor": {"read"},
            },
            "Facility Inspection": {
                "Facility Manager": {"read", "write", "create", "report"},
                "Facility Coordinator": {"read", "write", "create", "report"},
                "Technician": {"read", "write", "report"},
            },
            "Preventive Maintenance Plan": {
                "Facility Manager": {"read", "write", "create", "report"},
                "Facility Coordinator": {"read", "write", "create", "report"},
                "Technician": {"read"},
            },
        }

        for doctype, role_permissions in expected.items():
            permissions = frappe.get_meta(doctype).permissions
            for role, rights in role_permissions.items():
                matching = [
                    permission
                    for permission in permissions
                    if permission.role == role
                    and permission.permlevel == 0
                    and not permission.if_owner
                ]
                self.assertTrue(matching, f"Missing {role} permission on {doctype}")
                for right in rights:
                    self.assertTrue(
                        matching[0].get(right),
                        f"Missing {right} for {role} on {doctype}",
                    )

# Copyright (c) 2026, Jean Paul Abou Gharib and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form.assign_to import _add, close_all_assignments
from frappe.model.document import Document
from frappe.utils import (
    add_to_date,
    getdate,
    get_datetime,
    now_datetime,
    time_diff_in_hours,
)


ISSUE_STATUS_BY_WORK_ORDER_STATUS = {
    "Assigned": ("Assigned", "Open"),
    "In Progress": ("In Progress", "Open"),
    "Pending": ("Pending", "Hold"),
    "Resolved": ("Resolved", "Resolved"),
    "Closed": ("Closed", "Closed"),
}


class FacilityWorkOrder(Document):
    def before_validate(self):
        self.infer_work_order_type()
        self.populate_from_maintenance_request()
        self.populate_from_preventive_plan()
        self.populate_warranty_details()
        self.set_preventive_occurrence_key()

    def validate(self):
        self.validate_vendor_access()
        self.validate_source()
        self.validate_duplicate_active_work_order()
        self.validate_duplicate_preventive_occurrence()
        self.validate_assignment()
        self.validate_dates()
        self.validate_asset_location()
        self.validate_warranty_claim()
        self.validate_inspection_template()
        self.validate_labor_entries()
        self.validate_materials()
        self.validate_checklist()
        self.validate_inspection_closure()
        self.validate_resolution()

    def after_insert(self):
        if self.maintenance_request:
            frappe.db.set_value(
                "Issue",
                self.maintenance_request,
                "custom_work_order",
                self.name,
                update_modified=True,
            )
        self.sync_technician_assignment()

    def on_update(self):
        self.sync_technician_assignment()
        self.sync_issue_status()
        self.sync_asset_maintenance_history()
        self.refresh_assignment_availability()

    def after_delete(self):
        self.refresh_assignment_availability()

    def on_trash(self):
        self.close_assignments()
        self.clear_issue_link()

    def validate_vendor_access(self):
        from cafm.permissions import validate_vendor_work_order_changes

        validate_vendor_work_order_changes(self)

    def infer_work_order_type(self):
        if self.maintenance_request and not self.preventive_maintenance_plan:
            self.work_order_type = "Corrective"
        elif self.preventive_maintenance_plan and not self.maintenance_request:
            self.work_order_type = "Preventive"

    def populate_from_maintenance_request(self):
        if self.work_order_type != "Corrective" or not self.maintenance_request:
            return

        issue = frappe.get_doc("Issue", self.maintenance_request)
        self.subject = self.subject or issue.subject
        self.company = (
            self.company
            or issue.company
            or frappe.defaults.get_user_default("Company")
        )
        self.facility_location = (
            self.facility_location or issue.custom_facility_location
        )
        self.asset = self.asset or issue.custom_asset
        self.category = self.category or issue.issue_type
        self.priority = self.priority or issue.priority
        self.work_description = self.work_description or issue.description

    def populate_from_preventive_plan(self):
        if (
            self.work_order_type != "Preventive"
            or not self.preventive_maintenance_plan
        ):
            return

        plan = frappe.get_doc(
            "Preventive Maintenance Plan",
            self.preventive_maintenance_plan,
        )
        self.subject = self.subject or _(
            "Preventive Maintenance: {0}"
        ).format(plan.plan_name)
        self.company = self.company or plan.company
        self.facility_location = (
            self.facility_location or plan.facility_location
        )
        self.asset = self.asset or plan.asset
        self.category = self.category or plan.category
        self.priority = self.priority or plan.priority
        self.work_description = self.work_description or plan.instructions
        self.assignment_type = self.assignment_type or plan.assignment_type
        self.technician = self.technician or plan.technician
        self.vendor = self.vendor or plan.vendor
        if self.is_new():
            self.inspection_required = plan.inspection_required
        self.inspection_template = (
            self.inspection_template or plan.inspection_template
        )

        if self.scheduled_occurrence_date and not self.planned_start:
            self.planned_start = get_datetime(
                f"{getdate(self.scheduled_occurrence_date)} 09:00:00"
            )
        if (
            self.planned_start
            and not self.planned_end
            and plan.planned_duration_hours
        ):
            self.planned_end = add_to_date(
                self.planned_start,
                hours=plan.planned_duration_hours,
            )

        if self.is_new() and not self.checklist:
            for item in plan.checklist:
                self.append(
                    "checklist",
                    {
                        "description": item.description,
                        "is_required": item.is_required,
                        "result": "Pending",
                        "comments": item.instructions,
                    },
                )

    def populate_warranty_details(self):
        if not self.asset:
            self.asset_warranty_status = None
            self.warranty_provider = None
            self.warranty_expiry_date = None
            return

        from cafm.warranty import get_warranty_status

        warranty = frappe.db.get_value(
            "Asset",
            self.asset,
            [
                "custom_warranty_service_provider",
                "custom_warranty_start_date",
                "custom_warranty_expiry_date",
            ],
            as_dict=True,
        )
        self.asset_warranty_status = get_warranty_status(
            warranty.custom_warranty_start_date,
            warranty.custom_warranty_expiry_date,
        )
        self.warranty_provider = warranty.custom_warranty_provider
        self.warranty_expiry_date = warranty.custom_warranty_expiry_date

    def set_preventive_occurrence_key(self):
        if (
            self.work_order_type == "Preventive"
            and self.preventive_maintenance_plan
            and self.scheduled_occurrence_date
        ):
            self.preventive_occurrence_key = (
                f"{self.preventive_maintenance_plan}::"
                f"{getdate(self.scheduled_occurrence_date)}"
            )
        elif self.work_order_type != "Preventive":
            self.preventive_occurrence_key = None

    def validate_source(self):
        if self.work_order_type == "Corrective":
            if not self.maintenance_request:
                frappe.throw(
                    _("Maintenance Request is required for corrective work.")
                )
            if self.preventive_maintenance_plan:
                frappe.throw(
                    _("Corrective work cannot be linked to a preventive plan.")
                )
            return

        if self.work_order_type == "Preventive":
            if not self.preventive_maintenance_plan:
                frappe.throw(
                    _("Preventive Maintenance Plan is required.")
                )
            if not self.scheduled_occurrence_date:
                frappe.throw(
                    _("Scheduled Occurrence Date is required.")
                )
            if self.maintenance_request:
                frappe.throw(
                    _("Preventive work cannot be linked to a Maintenance Request.")
                )

            plan = frappe.get_doc(
                "Preventive Maintenance Plan",
                self.preventive_maintenance_plan,
            )
            if self.is_new() and not plan.is_active:
                frappe.throw(
                    _("The Preventive Maintenance Plan is inactive.")
                )
            if plan.asset != self.asset:
                frappe.throw(
                    _("The Work Order asset must match the preventive plan.")
                )
            if plan.facility_location != self.facility_location:
                frappe.throw(
                    _("The Work Order location must match the preventive plan.")
                )
            return

        frappe.throw(_("Work Order Type must be Corrective or Preventive."))

    def validate_duplicate_active_work_order(self):
        if self.work_order_type != "Corrective" or not self.maintenance_request:
            return

        filters = {
            "maintenance_request": self.maintenance_request,
            "work_order_status": ["not in", ["Closed", "Cancelled"]],
        }
        if self.name:
            filters["name"] = ["!=", self.name]

        if frappe.db.exists("Facility Work Order", filters):
            frappe.throw(
                _("An active Facility Work Order already exists for this request.")
            )

    def validate_duplicate_preventive_occurrence(self):
        if (
            self.work_order_type != "Preventive"
            or not self.preventive_occurrence_key
        ):
            return

        filters = {
            "preventive_occurrence_key": self.preventive_occurrence_key,
        }
        if self.name:
            filters["name"] = ["!=", self.name]

        if frappe.db.exists("Facility Work Order", filters):
            frappe.throw(
                _(
                    "A Work Order already exists for this preventive occurrence."
                )
            )

    def validate_assignment(self):
        if (
            self.work_order_status not in ("Draft", "Cancelled")
            and not self.assignment_type
        ):
            frappe.throw(_("Assignment Type is required once work is assigned."))

        if self.assignment_type == "Internal Technician":
            if not self.technician:
                frappe.throw(
                    _("Technician is required for an internal assignment.")
                )
            from cafm.assignment import validate_internal_technician

            validate_internal_technician(
                self.technician,
                self.category,
                self.name if not self.is_new() else None,
            )

        if self.assignment_type == "External Vendor":
            if not self.vendor:
                frappe.throw(
                    _("Service Provider is required for external assignment.")
                )
            from cafm.assignment import validate_external_provider

            validate_external_provider(
                self.vendor,
                self.category,
                self.name if not self.is_new() else None,
            )

    def refresh_assignment_availability(self):
        from cafm.assignment import refresh_work_order_availability

        refresh_work_order_availability(self)

    def validate_dates(self):
        if (
            self.planned_start
            and self.planned_end
            and self.planned_end < self.planned_start
        ):
            frappe.throw(
                _("Planned End cannot be earlier than Planned Start.")
            )

        if (
            self.actual_start
            and self.actual_end
            and self.actual_end < self.actual_start
        ):
            frappe.throw(
                _("Actual End cannot be earlier than Actual Start.")
            )

    def validate_asset_location(self):
        if not self.asset:
            return

        asset_location = frappe.db.get_value(
            "Asset", self.asset, "custom_asset_location"
        )
        if asset_location != self.facility_location:
            frappe.throw(
                _("The Asset does not belong to the selected Facility Location.")
            )

    def validate_warranty_claim(self):
        from cafm.warranty import validate_warranty_claim

        validate_warranty_claim(self)

    def validate_inspection_template(self):
        from cafm.inspection_templates import validate_inspection_template

        validate_inspection_template(self.inspection_template, self.category)

    def validate_labor_entries(self):
        for row in self.labor_entries:
            if row.start_time and row.end_time:
                if row.end_time < row.start_time:
                    frappe.throw(
                        _("Labor end time cannot be earlier than start time.")
                    )
                row.hours = time_diff_in_hours(row.end_time, row.start_time)

    def validate_materials(self):
        from cafm.materials import validate_work_order_materials

        validate_work_order_materials(self)

    def validate_checklist(self):
        if self.work_order_status not in ("Resolved", "Closed"):
            return

        incomplete = [
            row.description
            for row in self.checklist
            if row.is_required and row.result == "Pending"
        ]
        if incomplete:
            frappe.throw(
                _("Complete all required checklist items before resolving: {0}").format(
                    ", ".join(incomplete)
                )
            )

    def validate_inspection_closure(self):
        if self.work_order_status != "Closed" or not self.inspection_required:
            return

        inspections = frappe.get_all(
            "Facility Inspection",
            filters={
                "work_order": self.name,
                "required_for_closure": 1,
                "status": "Approved",
            },
            fields=["name", "overall_result", "override_failure"],
        )
        acceptable = [
            row
            for row in inspections
            if row.overall_result == "Pass" or row.override_failure
        ]
        if not acceptable:
            frappe.throw(
                _(
                    "This Work Order requires an approved passing Inspection "
                    "before closure. A failed Inspection requires a Facility "
                    "Manager override."
                )
            )

    def validate_resolution(self):
        if (
            self.work_order_status in ("Resolved", "Closed")
            and not self.resolution_summary
        ):
            frappe.throw(
                _("Resolution Summary is required before resolving the work order.")
            )

        if self.work_order_status == "Closed":
            self.closed_by = frappe.session.user
            self.closed_on = self.closed_on or now_datetime()

    def sync_asset_maintenance_history(self):
        from cafm.asset_maintenance import (
            sync_asset_maintenance_history,
        )

        sync_asset_maintenance_history(self)

    def sync_technician_assignment(self):
        desired_user = None
        if self.work_order_status not in ("Draft", "Closed", "Cancelled"):
            if (
                self.assignment_type == "Internal Technician"
                and self.technician
            ):
                desired_user = frappe.db.get_value(
                    "Employee",
                    self.technician,
                    "user_id",
                )
            elif self.assignment_type == "External Vendor" and self.vendor:
                desired_user = frappe.db.get_value(
                    "Facility Service Provider",
                    self.vendor,
                    "vendor_user",
                )

        assignments = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": self.doctype,
                "reference_name": self.name,
                "status": ["not in", ["Closed", "Cancelled"]],
            },
            pluck="allocated_to",
        )

        if desired_user and assignments == [desired_user]:
            self.create_hrms_assignment_notification(desired_user)
            return

        if assignments:
            close_all_assignments(
                self.doctype, self.name, ignore_permissions=True
            )

        if desired_user:
            assignment = {
                "assign_to": [desired_user],
                "doctype": self.doctype,
                "name": self.name,
                "description": self.subject,
                "priority": (
                    "High"
                    if self.priority in ("High", "Critical")
                    else "Medium"
                ),
            }
            if self.planned_end:
                assignment["date"] = getdate(self.planned_end)
            _add(assignment, ignore_permissions=True)
            self.create_hrms_assignment_notification(desired_user)

    def create_hrms_assignment_notification(self, desired_user):
        """Mirror assignments into the notification feed used by HRMS."""
        if not frappe.db.exists("DocType", "PWA Notification"):
            return

        filters = {
            "to_user": desired_user,
            "reference_document_type": self.doctype,
            "reference_document_name": self.name,
            "read": 0,
        }
        if frappe.db.exists("PWA Notification", filters):
            return

        notification = frappe.new_doc("PWA Notification")
        notification.from_user = frappe.session.user
        notification.to_user = desired_user
        notification.message = _(
            "You were assigned to Work Order {0}: {1}"
        ).format(self.name, self.subject)
        notification.reference_document_type = self.doctype
        notification.reference_document_name = self.name
        notification.insert(ignore_permissions=True)

    def sync_issue_status(self):
        if not self.maintenance_request:
            return

        if self.work_order_status == "Cancelled":
            self.clear_issue_link()
            frappe.db.set_value(
                "Issue",
                self.maintenance_request,
                {
                    "custom_issue_status": "New",
                    "status": "Open",
                },
                update_modified=True,
            )
            return

        mapped_status = ISSUE_STATUS_BY_WORK_ORDER_STATUS.get(
            self.work_order_status
        )
        if not mapped_status:
            return

        cafm_status, native_status = mapped_status
        updates = {
            "custom_issue_status": cafm_status,
            "status": native_status,
        }
        if cafm_status == "Pending":
            updates["custom_pending_reason"] = (
                self.technician_notes or _("Work Order placed on hold.")
            )
        if cafm_status == "Resolved":
            updates["resolution_details"] = self.resolution_summary

        frappe.db.set_value(
            "Issue",
            self.maintenance_request,
            updates,
            update_modified=True,
        )

    def close_assignments(self):
        close_all_assignments(
            self.doctype, self.name, ignore_permissions=True
        )

    def clear_issue_link(self):
        if not self.maintenance_request:
            return

        linked_work_order = frappe.db.get_value(
            "Issue", self.maintenance_request, "custom_work_order"
        )
        if linked_work_order == self.name:
            frappe.db.set_value(
                "Issue",
                self.maintenance_request,
                "custom_work_order",
                None,
                update_modified=True,
            )


@frappe.whitelist()
def create_from_issue(issue_name):
    issue = frappe.get_doc("Issue", issue_name)
    issue.check_permission("read")

    frappe.db.sql(
        "SELECT name FROM `tabIssue` WHERE name = %s FOR UPDATE",
        issue.name,
    )
    issue.reload()

    if issue.custom_work_order:
        frappe.throw(
            _("This Issue is already linked to a Facility Work Order.")
        )

    work_order = frappe.new_doc("Facility Work Order")
    work_order.work_order_type = "Corrective"
    work_order.maintenance_request = issue.name
    work_order.insert()
    return work_order.name

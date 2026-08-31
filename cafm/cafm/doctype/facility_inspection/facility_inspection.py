import frappe
from frappe import _
from frappe.desk.form.assign_to import _add, close_all_assignments
from frappe.model.document import Document
from frappe.utils import now_datetime


FINAL_INSPECTION_STATUSES = ("Completed", "Approved", "Rejected")
INSPECTION_MANAGER_ROLES = {"System Manager", "Facility Manager"}


class FacilityInspection(Document):
    def before_validate(self):
        self.populate_source_details()
        self.populate_template_items()
        self.set_overall_result()
        self.set_lifecycle_timestamps()

    def validate(self):
        self.validate_source()
        self.validate_template()
        self.validate_asset_location()
        self.validate_inspector()
        self.validate_results()
        self.validate_override()

    def after_insert(self):
        self.sync_inspector_assignment()

    def on_update(self):
        self.sync_inspector_assignment()

    def on_trash(self):
        close_all_assignments(
            self.doctype,
            self.name,
            ignore_permissions=True,
        )

    def populate_source_details(self):
        if self.work_order:
            work_order = frappe.get_doc("Facility Work Order", self.work_order)
            self.source_type = "Work Order"
            self.company = self.company or work_order.company
            self.facility_location = (
                self.facility_location or work_order.facility_location
            )
            self.asset = self.asset or work_order.asset
            self.category = self.category or work_order.category
            self.inspection_template = (
                self.inspection_template or work_order.inspection_template
            )
            self.inspector = self.inspector or work_order.technician
            if self.is_new():
                self.required_for_closure = work_order.inspection_required

        if self.inspection_schedule:
            schedule = frappe.get_doc(
                "Facility Inspection Schedule",
                self.inspection_schedule,
            )
            self.source_type = "Scheduled Inspection"
            self.company = self.company or schedule.company
            self.facility_location = (
                self.facility_location or schedule.facility_location
            )
            self.asset = self.asset or schedule.asset
            self.category = self.category or schedule.category
            self.inspection_template = (
                self.inspection_template or schedule.inspection_template
            )
            self.inspector = self.inspector or schedule.inspector
            if self.is_new():
                self.required_for_closure = 0

    def populate_template_items(self):
        if not self.is_new() or self.results or not self.inspection_template:
            return

        template = frappe.get_doc(
            "Facility Inspection Template",
            self.inspection_template,
        )
        for item in template.items:
            self.append(
                "results",
                {
                    "inspection_point": item.inspection_point,
                    "instructions": item.instructions,
                    "is_required": item.is_required,
                    "requires_evidence": item.requires_evidence,
                    "result": "Pending",
                },
            )

    def set_overall_result(self):
        if not self.results or any(
            row.result == "Pending" for row in self.results
        ):
            self.overall_result = "Pending"
        elif any(row.result == "Fail" for row in self.results):
            self.overall_result = "Fail"
        else:
            self.overall_result = "Pass"

    def set_lifecycle_timestamps(self):
        if self.status == "In Progress" and not self.started_on:
            self.started_on = now_datetime()
        if self.status in FINAL_INSPECTION_STATUSES and not self.completed_on:
            self.completed_on = now_datetime()

    def validate_source(self):
        if self.work_order and self.inspection_schedule:
            frappe.throw(
                _("An Inspection cannot have both a Work Order and a Schedule.")
            )
        if self.source_type == "Work Order" and not self.work_order:
            frappe.throw(_("Work Order is required for this Inspection."))
        if (
            self.source_type == "Scheduled Inspection"
            and not self.inspection_schedule
        ):
            frappe.throw(
                _("Inspection Schedule is required for a scheduled Inspection.")
            )
        if self.source_type == "Manual" and (
            self.work_order or self.inspection_schedule
        ):
            frappe.throw(
                _("A Manual Inspection cannot have an automatic source.")
            )

    def validate_template(self):
        if not self.inspection_template:
            frappe.throw(_("Inspection Template is required."))

        from cafm.inspection_templates import validate_inspection_template

        validate_inspection_template(self.inspection_template, self.category)
        if not self.results:
            frappe.throw(_("The Inspection Template has no checklist items."))

    def validate_asset_location(self):
        if not self.asset:
            return
        asset_location = frappe.db.get_value(
            "Asset",
            self.asset,
            "custom_asset_location",
        )
        if asset_location != self.facility_location:
            frappe.throw(
                _("The Asset does not belong to the selected Facility Location.")
            )

    def validate_inspector(self):
        if self.status == "Draft" and not self.inspector:
            return
        if not self.inspector:
            frappe.throw(_("Inspector is required before starting Inspection."))

        employee = frappe.db.get_value(
            "Employee",
            self.inspector,
            ["status", "user_id"],
            as_dict=True,
        )
        if not employee or employee.status != "Active":
            frappe.throw(_("Inspector must be an active Employee."))
        if not employee.user_id:
            frappe.throw(_("Inspector must be linked to a User account."))

    def validate_results(self):
        if self.status not in FINAL_INSPECTION_STATUSES:
            return

        pending = [
            row.inspection_point
            for row in self.results
            if row.is_required and row.result == "Pending"
        ]
        if pending:
            frappe.throw(
                _("Complete all required Inspection Items: {0}").format(
                    ", ".join(pending)
                )
            )

        unexplained_na = [
            row.inspection_point
            for row in self.results
            if row.is_required and row.result == "N/A" and not row.comments
        ]
        if unexplained_na:
            frappe.throw(
                _("Comments are required for N/A items: {0}").format(
                    ", ".join(unexplained_na)
                )
            )

        missing_evidence = [
            row.inspection_point
            for row in self.results
            if row.requires_evidence
            and row.result != "Pending"
            and not row.evidence
        ]
        if missing_evidence:
            frappe.throw(
                _("Evidence is required for Inspection Items: {0}").format(
                    ", ".join(missing_evidence)
                )
            )

    def validate_override(self):
        previous = self.get_doc_before_save()
        previous_override = bool(
            previous and previous.override_failure
        )
        override_changed = (
            bool(self.override_failure) != previous_override
            or (
                previous
                and self.override_failure
                and self.override_reason != previous.override_reason
            )
        )

        if override_changed and not (
            set(frappe.get_roles()) & INSPECTION_MANAGER_ROLES
        ):
            frappe.throw(
                _("Only a Facility Manager can change a failure override.")
            )

        if self.override_failure:
            if self.overall_result != "Fail":
                frappe.throw(
                    _("Only a failed Inspection can receive an override.")
                )
            if not self.override_reason:
                frappe.throw(_("Override Reason is required."))
            if override_changed or not self.override_by:
                self.override_by = frappe.session.user
                self.override_on = now_datetime()
        else:
            self.override_by = None
            self.override_on = None

        if (
            self.status == "Approved"
            and self.overall_result == "Fail"
            and not self.override_failure
        ):
            frappe.throw(
                _(
                    "A failed Inspection requires a Facility Manager override "
                    "before approval."
                )
            )

    def sync_inspector_assignment(self):
        desired_user = None
        if self.inspector and self.status in ("Assigned", "In Progress"):
            desired_user = frappe.db.get_value(
                "Employee",
                self.inspector,
                "user_id",
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
            return
        if assignments:
            close_all_assignments(
                self.doctype,
                self.name,
                ignore_permissions=True,
            )
        if desired_user:
            _add(
                {
                    "assign_to": [desired_user],
                    "doctype": self.doctype,
                    "name": self.name,
                    "description": _(
                        "Facility Inspection: {0}"
                    ).format(self.inspection_template),
                    "priority": "Medium",
                    "date": self.planned_date,
                },
                ignore_permissions=True,
            )


@frappe.whitelist()
def create_from_work_order(work_order_name):
    work_order = frappe.get_doc("Facility Work Order", work_order_name)
    work_order.check_permission("read")

    if not work_order.inspection_template:
        frappe.throw(
            _("Select an Inspection Template on the Work Order first.")
        )

    roles = set(frappe.get_roles())
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user, "status": "Active"},
        "name",
    )
    if not (
        roles & {"System Manager", "Facility Manager", "Facility Coordinator"}
        or (
            "Technician" in roles
            and employee
            and work_order.technician == employee
        )
    ):
        frappe.throw(_("You cannot create an Inspection for this Work Order."))

    frappe.db.sql(
        "SELECT name FROM `tabFacility Work Order` WHERE name = %s FOR UPDATE",
        work_order.name,
    )
    work_order.reload()

    existing = frappe.db.get_value(
        "Facility Inspection",
        {
            "work_order": work_order.name,
            "inspection_template": work_order.inspection_template,
            "status": ["not in", ["Rejected", "Cancelled"]],
        },
        "name",
    )
    if existing:
        return existing

    inspection = frappe.new_doc("Facility Inspection")
    inspection.source_type = "Work Order"
    inspection.work_order = work_order.name
    inspection.inspection_template = work_order.inspection_template
    inspection.inspector = work_order.technician
    inspection.planned_date = work_order.planned_end or work_order.planned_start
    inspection.insert(ignore_permissions=True)
    return inspection.name

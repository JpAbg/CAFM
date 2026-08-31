import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PreventiveMaintenancePlan(Document):
    def before_validate(self):
        self.populate_asset_details()
        self.next_due_date = self.next_due_date or self.start_date

    def validate(self):
        self.validate_dates()
        self.validate_asset_location()
        self.validate_inspection_template()
        self.validate_assignment()

    def populate_asset_details(self):
        if not self.asset:
            return

        asset = frappe.db.get_value(
            "Asset",
            self.asset,
            ["company", "custom_asset_location"],
            as_dict=True,
        )
        if not asset:
            return

        self.company = self.company or asset.company
        self.facility_location = (
            self.facility_location or asset.custom_asset_location
        )

    def validate_dates(self):
        if self.next_due_date and self.start_date:
            if getdate(self.next_due_date) < getdate(self.start_date):
                frappe.throw(_("Next Due Date cannot be earlier than Start Date."))

        if self.planned_duration_hours is not None:
            if self.planned_duration_hours <= 0:
                frappe.throw(_("Planned Duration must be greater than zero."))

    def validate_asset_location(self):
        asset = frappe.db.get_value(
            "Asset",
            self.asset,
            ["docstatus", "custom_asset_location"],
            as_dict=True,
        )
        if not asset or asset.docstatus != 1:
            frappe.throw(
                _("Preventive maintenance requires a submitted Asset.")
            )

        asset_location = asset.custom_asset_location
        if asset_location != self.facility_location:
            frappe.throw(
                _("The Asset does not belong to the selected Facility Location.")
            )

    def validate_inspection_template(self):
        from cafm.inspection_templates import validate_inspection_template

        validate_inspection_template(self.inspection_template, self.category)

    def validate_assignment(self):
        if self.assignment_type == "Internal Technician":
            if not self.technician:
                frappe.throw(_("Technician is required for internal assignment."))
            from cafm.assignment import validate_internal_technician

            validate_internal_technician(
                self.technician,
                self.category,
                check_capacity=False,
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
            )


@frappe.whitelist()
def generate_next_work_order(plan_name):
    plan = frappe.get_doc("Preventive Maintenance Plan", plan_name)
    plan.check_permission("write")

    from cafm.preventive_maintenance import generate_occurrence

    return generate_occurrence(plan, getdate(plan.next_due_date))

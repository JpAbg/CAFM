import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class FacilityInspectionSchedule(Document):
    def before_validate(self):
        self.populate_asset_details()
        self.next_due_date = self.next_due_date or self.start_date

    def validate(self):
        self.validate_dates()
        self.validate_template()
        self.validate_asset_location()
        self.validate_inspector()

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
        if (
            self.next_due_date
            and self.start_date
            and getdate(self.next_due_date) < getdate(self.start_date)
        ):
            frappe.throw(
                _("Next Due Date cannot be earlier than Start Date.")
            )

    def validate_template(self):
        if not frappe.db.get_value(
            "Facility Inspection Template",
            self.inspection_template,
            "is_active",
        ):
            frappe.throw(_("Inspection Template must be active."))

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


@frappe.whitelist()
def generate_next_inspection(schedule_name):
    schedule = frappe.get_doc(
        "Facility Inspection Schedule",
        schedule_name,
    )
    schedule.check_permission("write")

    from cafm.inspections import generate_inspection_occurrence

    return generate_inspection_occurrence(
        schedule,
        getdate(schedule.next_due_date),
    )

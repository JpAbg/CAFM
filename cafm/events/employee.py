import frappe
from frappe import _

from cafm.assignment import (
    calculate_employee_availability,
    update_employee_availability,
)


def validate_cafm_employee(doc, method=None):
    if not doc.get("custom_is_facility_technician"):
        return

    if not doc.user_id:
        frappe.throw(
            _("A Facility Technician must be linked to a User account.")
        )
    user_roles = frappe.get_doc("User", doc.user_id).roles
    if not any(row.role == "Technician" for row in user_roles):
        frappe.throw(
            _("The linked User must have the Technician role.")
        )

    categories = [
        row.service_category for row in doc.custom_service_categories
    ]
    if len(categories) != len(set(categories)):
        frappe.throw(_("Service Categories cannot contain duplicates."))
    if sum(1 for row in doc.custom_service_categories if row.is_primary) > 1:
        frappe.throw(_("Only one Service Category can be primary."))

    doc.custom_facility_availability = calculate_employee_availability(doc)


def update_cafm_employee_availability(doc, method=None):
    if doc.get("custom_is_facility_technician"):
        update_employee_availability(doc.name)


def update_leave_employee_availability(doc, method=None):
    if doc.employee:
        update_employee_availability(doc.employee)

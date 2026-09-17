import frappe
from frappe import _

from cafm.permissions import PRIVILEGED_ROLES, get_employee_for_user


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to open the Technician Portal."), frappe.PermissionError)

    roles = set(frappe.get_roles())
    if "Technician" not in roles or roles & PRIVILEGED_ROLES:
        frappe.throw(
            _("The Technician Portal is available only to technicians."),
            frappe.PermissionError,
        )
    if not get_employee_for_user(frappe.session.user):
        frappe.throw(
            _("Your account is not linked to an active Employee record."),
            frappe.PermissionError,
        )
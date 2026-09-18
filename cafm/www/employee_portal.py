import frappe
from frappe import _

from cafm.permissions import get_employee_for_user

EMPLOYEE_PORTAL_ROLES = {
    "Employee",
    "Requester / Employee",
    "Technician",
    "Facility Manager",
    "Facility Coordinator",
}
ADMIN_PORTAL_ROLES = {"Administrator", "System Manager"}


def get_context(context):
    context.no_cache = 1

    user = frappe.session.user
    roles = set(frappe.get_roles())
    if user == "Guest" or not roles & (EMPLOYEE_PORTAL_ROLES | ADMIN_PORTAL_ROLES):
        frappe.throw(
            _("The Employee Portal is available only to employees and administrators."),
            frappe.PermissionError,
        )
    if not roles & ADMIN_PORTAL_ROLES and not get_employee_for_user(user):
        frappe.throw(
            _("Your account is not linked to an active Employee record."),
            frappe.PermissionError,
        )
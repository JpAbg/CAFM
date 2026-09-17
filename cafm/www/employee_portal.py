import frappe
from frappe import _

from cafm.events.user import SUPERVISOR_WORKSPACE_ROLES
from cafm.permissions import get_employee_for_user


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to open the Employee Portal."), frappe.PermissionError)

    roles = set(frappe.get_roles())
    is_supervisor = bool(roles & SUPERVISOR_WORKSPACE_ROLES)
    if ("Requester / Employee" not in roles and not is_supervisor) or (
        "Technician" in roles and not is_supervisor
    ):
        frappe.throw(
            _("The Employee Portal is available only to employees."),
            frappe.PermissionError,
        )
    if not get_employee_for_user(frappe.session.user):
        frappe.throw(
            _("Your account is not linked to an active Employee record."),
            frappe.PermissionError,
        )

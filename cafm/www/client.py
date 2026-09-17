import frappe
from frappe import _

from cafm.events.user import CLIENT_ROLES, TECHNICIAN_REDIRECT_EXCLUDED_ROLES


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to open the Client Portal."), frappe.PermissionError)

    roles = set(frappe.get_roles())
    if not roles & CLIENT_ROLES or roles & TECHNICIAN_REDIRECT_EXCLUDED_ROLES:
        frappe.throw(
            _("The Client Portal is available only to clients."),
            frappe.PermissionError,
        )

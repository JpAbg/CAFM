import frappe
from frappe import _

from cafm.events.user import CLIENT_ROLES, TECHNICIAN_REDIRECT_EXCLUDED_ROLES

ADMIN_PORTAL_ROLES = {"Administrator", "System Manager"}


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to open the Client Portal."), frappe.PermissionError)

    roles = set(frappe.get_roles())
    allowed_roles = CLIENT_ROLES | ADMIN_PORTAL_ROLES
    if not roles & allowed_roles or (
        roles & TECHNICIAN_REDIRECT_EXCLUDED_ROLES
        and not roles & ADMIN_PORTAL_ROLES
    ):
        frappe.throw(
            _("The Client Portal is available only to clients and administrators."),
            frappe.PermissionError,
        )

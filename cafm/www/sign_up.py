import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.rate_limiter import rate_limit
from frappe.utils import today, validate_email_address


def get_context(context):
    context.no_cache = 1

    user = frappe.session.user
    if user != "Guest" and user != "Administrator" and "Client" not in frappe.get_roles(user):
        frappe.throw(_("You are not permitted to access this page."), frappe.PermissionError)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def sign_up_account(first_name, last_name, usr, pwd, confirm_password):
    """Create, authenticate, and route an unprivileged CAFM Client account."""
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    if not first_name or not last_name:
        frappe.throw(_("First name and last name are required."))

    email = (usr or "").strip().lower()
    validate_email_address(email, throw=True)
    if not pwd or pwd != confirm_password:
        frappe.throw(_("The passwords do not match."))
    if frappe.db.exists("User", email):
        frappe.throw(_("An account already exists for this email address."))
    if not frappe.db.exists("Role", "Client"):
        frappe.throw(_("Client registration is not configured. Please contact an administrator."))

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": 1,
            "new_password": pwd,
            "user_type": "Website User",
            "send_welcome_email": 0,
        }
    )
    user.flags.ignore_permissions = True
    user.insert()
    user.add_roles("Client")

    client = frappe.get_doc(
        {
            "doctype": "Client",
            "client_type": "Individual",
            "first_name": first_name,
            "last_name": last_name,
            "email_address": email,
            "status": "Active",
            "date_of_partnership": today(),
            "user": email,
        }
    )
    client.flags.ignore_permissions = True
    client.insert()

    login_manager = LoginManager()
    login_manager.authenticate(user=email, pwd=pwd)
    login_manager.post_login()
    return {
        "created": True,
        "user": email,
        "redirect_to": "/client-portal",
    }
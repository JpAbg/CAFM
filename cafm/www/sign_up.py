import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address
from frappe.website.utils import is_signup_disabled


def get_context(context):
    context.no_cache = 1


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def sign_up_account(first_name, last_name, usr, pwd, confirm_password):
    """Create an unprivileged website account using Frappe's password policy."""
    if is_signup_disabled():
        frappe.throw(_("Sign up is currently disabled."), frappe.PermissionError)

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

    default_role = frappe.get_single_value("Portal Settings", "default_role")
    if default_role:
        user.add_roles(default_role)

    return {"created": True}

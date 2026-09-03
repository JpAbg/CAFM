import frappe
from frappe import _

from cafm.assignment import (
    calculate_employee_availability,
    update_employee_availability,
)


def _unique_employee_username(doc, email):
    base = frappe.scrub(
        " ".join(
            part for part in (
                doc.get("first_name"),
                doc.get("middle_name"),
                doc.get("last_name"),
            )
            if part
        )
    ) or frappe.scrub(email.split("@", 1)[0])

    username = base
    suffix = 2
    while frappe.db.exists("User", {"username": username}):
        username = "{0}_{1}".format(base, suffix)
        suffix += 1
    return username


def _cafm_employee_roles(doc, include_employee_role=False):
    roles = {"Requester / Employee"}
    if include_employee_role:
        roles.add("Employee")
    if doc.get("custom_is_facility_technician"):
        roles.add("Technician")
    return roles


def create_employee_user_account(doc, method=None):
    """Create and link a secure login for an active employee with an email."""

    if doc.get("user_id") or doc.get("status") != "Active":
        return

    email = (doc.get("company_email") or doc.get("personal_email") or "").strip().lower()
    if not email:
        return

    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "username": _unique_employee_username(doc, email),
                "first_name": doc.get("first_name"),
                "middle_name": doc.get("middle_name"),
                "last_name": doc.get("last_name"),
                "enabled": 1,
                "send_welcome_email": 1,
                # ERPNext only allows the Employee role after the Employee
                # record has been saved and linked to this User.
                "roles": [
                    {"role": role}
                    for role in sorted(_cafm_employee_roles(doc))
                ],
            }
        )
        user.flags.ignore_permissions = True
        # Test runs must not attempt to send mail to generated fixture emails.
        user.flags.no_welcome_mail = bool(frappe.flags.in_test)
        user.insert()

    doc.user_id = user.name


def ensure_employee_user_roles(doc, method=None):
    """Add employee roles after the linked Employee record exists."""

    if not doc.get("user_id") or doc.get("status") != "Active":
        return

    user = frappe.get_doc("User", doc.user_id)
    username_added = False
    if not user.username:
        user.username = _unique_employee_username(doc, user.name)
        username_added = True

    missing_roles = _cafm_employee_roles(doc, include_employee_role=True) - {
        row.role for row in user.roles
    }
    if missing_roles:
        user.add_roles(*sorted(missing_roles))
    elif username_added:
        user.save(ignore_permissions=True)


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

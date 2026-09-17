import frappe

from cafm.events.user import (
    SUPERVISOR_WORKSPACE_ROLES,
    get_technician_login_redirect,
)


def execute():
    technician_users = frappe.get_all(
        "Has Role",
        filters={
            "parenttype": "User",
            "parentfield": "roles",
            "role": "Technician",
        },
        pluck="parent",
    )
    for user in set(technician_users):
        roles = set(frappe.get_roles(user))
        if roles & SUPERVISOR_WORKSPACE_ROLES:
            continue
        if get_technician_login_redirect(user):
            frappe.db.set_value(
                "User",
                user,
                "default_workspace",
                None,
                update_modified=False,
            )

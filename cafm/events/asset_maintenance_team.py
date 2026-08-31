import frappe
from frappe import _


def validate_member_roles(doc, method=None):
    """Validate the CAFM multi-team membership list.

    Legacy ERPNext rows are only checked while a team has not yet migrated.
    """
    cafm_members = doc.get("custom_cafm_team_members") or []
    if cafm_members:
        validate_members(cafm_members, "user")
        return

    validate_members(doc.get("maintenance_team_members") or [], "team_member")


def validate_members(members, user_field):
    seen_users = set()

    for member in members:
        user = member.get(user_field)
        if not user and member.get("employee"):
            user = frappe.db.get_value("Employee", member.employee, "user_id")
        if not user:
            if member.get("employee"):
                frappe.throw(
                    _("Employee {0} must have a linked user account.").format(
                        frappe.bold(member.employee)
                    )
                )
            continue

        if user in seen_users:
            frappe.throw(
                _("A team member can appear only once in the same maintenance team.")
            )
        seen_users.add(user)

        if not member.maintenance_role:
            continue

        if frappe.db.exists(
            "Has Role",
            {
                "parent": user,
                "parenttype": "User",
                "role": member.maintenance_role,
            },
        ):
            continue

        frappe.throw(
            _("Role {0} is not assigned to user {1}.").format(
                frappe.bold(member.maintenance_role),
                frappe.bold(user),
            )
        )

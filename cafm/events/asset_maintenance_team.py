import frappe
from frappe import _


def validate_member_roles(doc, method=None):
    """Ensure each maintenance role is actually assigned to its team member."""
    for member in doc.get("maintenance_team_members") or []:
        if not member.team_member or not member.maintenance_role:
            continue
        if frappe.db.exists(
            "Has Role",
            {
                "parent": member.team_member,
                "parenttype": "User",
                "role": member.maintenance_role,
            },
        ):
            continue
        frappe.throw(
            _("Role {0} is not assigned to user {1}.").format(
                frappe.bold(member.maintenance_role),
                frappe.bold(member.team_member),
            )
        )

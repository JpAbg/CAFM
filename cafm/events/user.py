import frappe

from cafm.demo_data import CAFM_DEMO_USER_ROLES


def enforce_cafm_demo_user_roles(doc, method=None):
    """Prevent unrelated role profiles from taking over CAFM demo users."""
    expected_roles = CAFM_DEMO_USER_ROLES.get(doc.name)
    if not expected_roles:
        return

    doc.role_profile_name = None
    current_roles = {row.role for row in doc.roles}
    if current_roles == set(expected_roles):
        return

    doc.set("roles", [])
    for role in expected_roles:
        doc.append("roles", {"role": role})

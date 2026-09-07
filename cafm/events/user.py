import frappe

from cafm.demo_data import CAFM_DEMO_USER_ROLES


def clear_new_user_profiles(doc, method=None):
    """Ensure every new account starts without inherited profiles."""
    doc.role_profile_name = None
    doc.module_profile = None
    doc.set("block_modules", [])


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


NORMAL_CAFM_WORKSPACE_ROLES = {"Requester / Employee", "Technician"}
SUPERVISOR_WORKSPACE_ROLES = {"Facility Manager", "Facility Coordinator"}

CAFM_ROLE_PROFILES = {
    "Facility Manager": (
        "CAFM Facility Manager",
        ("Employee", "Requester / Employee", "Facility Manager"),
    ),
    "Facility Coordinator": (
        "CAFM Facility Coordinator",
        ("Employee", "Requester / Employee", "Facility Coordinator"),
    ),
    "Technician": (
        "CAFM Technician",
        ("Employee", "Requester / Employee", "Technician"),
    ),
    "Requester / Employee": (
        "CAFM Employee",
        ("Employee", "Requester / Employee"),
    ),
    "Vendor": (
        "CAFM Vendor",
        ("Vendor",),
    ),
}


def apply_cafm_role_profile(doc, method=None):
    """Replace unrelated profiles with the matching CAFM user profile."""
    if doc.name in {"Administrator", "Guest"}:
        return

    current_roles = {row.role for row in doc.roles}
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": doc.name},
        ["name", "custom_is_facility_technician"],
        as_dict=True,
    )
    is_linked_employee = bool(employee)

    profile_by_name = {
        profile_name: (role, profile_roles)
        for role, (profile_name, profile_roles) in CAFM_ROLE_PROFILES.items()
    }

    selected_profile = None
    # An explicitly assigned operational CAFM role always wins.
    for role in (
        "Facility Manager",
        "Facility Coordinator",
        "Technician",
        "Vendor",
    ):
        if role in current_roles:
            selected_profile = CAFM_ROLE_PROFILES[role]
            break

    # This persistent CAFM marker survives external profile synchronisation.
    # It lets CAFM restore the correct specialised profile after Axiom saves
    # its own profile onto every System User.
    stored_profile = doc.get("custom_cafm_role_profile")
    if not selected_profile and stored_profile in profile_by_name:
        selected_profile = (
            stored_profile,
            profile_by_name[stored_profile][1],
        )

    # Keep an existing specialised CAFM profile intact if a delayed profile
    # refresh temporarily drops its specialised role row.
    if not selected_profile and doc.role_profile_name in profile_by_name:
        profile_role, profile_roles = profile_by_name[doc.role_profile_name]
        if profile_role != "Requester / Employee":
            selected_profile = (doc.role_profile_name, profile_roles)

    if not selected_profile and "Requester / Employee" in current_roles:
        selected_profile = CAFM_ROLE_PROFILES["Requester / Employee"]

    # Replace the known unrelated Axiom profile on CAFM employee accounts,
    # without converting unrelated HR employees into CAFM users.
    if (
        not selected_profile
        and is_linked_employee
        and "Axiom Accountant" in current_roles
    ):
        selected_profile = CAFM_ROLE_PROFILES[
            "Technician"
            if employee.custom_is_facility_technician
            else "Requester / Employee"
        ]

    if not selected_profile:
        return

    profile_name, profile_roles = selected_profile

    # An Employee record must exist before ERPNext accepts its Employee role.
    # The Employee event applies the profile immediately after linking the User.
    if "Employee" in profile_roles and not is_linked_employee:
        return

    doc.role_profile_name = profile_name
    doc.custom_cafm_role_profile = profile_name
    doc.module_profile = None
    doc.set("block_modules", [])
    doc.set("roles", [])
    for role in profile_roles:
        doc.append("roles", {"role": role})


def set_normal_cafm_user_default_workspace(doc, method=None):
    """Keep normal CAFM employees and technicians on Welcome Workspace."""
    if doc.user_type != "System User":
        return

    roles = {row.role for row in doc.roles}
    is_linked_employee = bool(
        frappe.db.exists("Employee", {"user_id": doc.name})
    )
    cafm_workspace_roles = (
        NORMAL_CAFM_WORKSPACE_ROLES | SUPERVISOR_WORKSPACE_ROLES
    )
    if roles & cafm_workspace_roles or is_linked_employee:
        doc.default_workspace = "Welcome Workspace"

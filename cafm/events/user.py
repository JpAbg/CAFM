from urllib.parse import unquote

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
TECHNICIAN_PORTAL_ROUTE = "/technician%20portal"
EMPLOYEE_PORTAL_ROUTE = "/employee%20portal"
CLIENT_PORTAL_ROUTE = "/client-portal"
FACILITIES_WORKSPACE_ROUTE = "/app/facilities"
CLIENT_ROLES = {"Client", "Customer"}
TECHNICIAN_DEFAULT_LANDING_PATHS = {
    "",
    "/",
    "/login",
    "/app",
    "/app/home",
    "/app/welcome-workspace",
    "/app/workspaces/welcome workspace",
    "/welcome workspace",
}
TECHNICIAN_REDIRECT_EXCLUDED_ROLES = {
    "Administrator",
    "System Manager",
    "Facility Manager",
    "Facility Coordinator",
}

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
    stored_profile = doc.get("custom_cafm_role_profile")

    # A profile selected in the User form must take precedence over the roles
    # inherited from the previously saved profile. Without this check, changing
    # a Coordinator/Manager to CAFM Employee immediately selected the stale
    # privileged role again and reverted the profile during validation.
    if (
        doc.role_profile_name in profile_by_name
        and doc.role_profile_name != stored_profile
    ):
        selected_profile = (
            doc.role_profile_name,
            profile_by_name[doc.role_profile_name][1],
        )

    # An explicitly assigned operational CAFM role always wins.
    if not selected_profile:
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
    """Set role-appropriate Desk fallbacks without overriding portal routing."""
    if doc.user_type != "System User":
        return

    roles = {row.role for row in doc.roles}
    if roles & SUPERVISOR_WORKSPACE_ROLES:
        doc.default_workspace = "Facilities"
        return
    if (
        roles & NORMAL_CAFM_WORKSPACE_ROLES
    ):
        doc.default_workspace = None
        return

    is_linked_employee = bool(
        frappe.db.exists("Employee", {"user_id": doc.name})
    )
    if is_linked_employee:
        doc.default_workspace = None


def get_cafm_login_redirect(user):
    """Return the role-specific CAFM landing route after authentication."""
    if not user or user in {"Administrator", "Guest"}:
        return None

    roles = set(frappe.get_roles(user))
    if roles & {"Administrator", "System Manager"}:
        return None
    if roles & SUPERVISOR_WORKSPACE_ROLES:
        return FACILITIES_WORKSPACE_ROUTE
    is_active_employee = bool(frappe.db.exists(
        "Employee", {"user_id": user, "status": "Active"}
    ))
    if "Technician" in roles and is_active_employee:
        return TECHNICIAN_PORTAL_ROUTE
    if "Requester / Employee" in roles and is_active_employee:
        return EMPLOYEE_PORTAL_ROUTE
    if roles & CLIENT_ROLES:
        return CLIENT_PORTAL_ROUTE
    return None


def get_technician_login_redirect(user):
    """Backward-compatible helper for the technician-only route check."""
    redirect_to = get_cafm_login_redirect(user)
    return redirect_to if redirect_to == TECHNICIAN_PORTAL_ROUTE else None


def redirect_cafm_after_login(login_manager=None):
    """Send CAFM users to the landing page assigned to their role."""
    user = getattr(login_manager, "user", None) or frappe.session.user
    redirect_to = get_cafm_login_redirect(user)
    if redirect_to:
        # LoginManager.set_user_info consumes this after all login hooks run.
        frappe.cache.hset("redirect_after_login", user, redirect_to)


def get_technician_default_page_redirect(user, request_path):
    """Redirect technicians away from generic landing pages only."""
    if get_technician_login_redirect(user) != TECHNICIAN_PORTAL_ROUTE:
        return None

    normalized_path = unquote(request_path or "").rstrip("/").lower()
    if normalized_path in TECHNICIAN_DEFAULT_LANDING_PATHS:
        return TECHNICIAN_PORTAL_ROUTE
    return None


def get_cafm_default_page_redirect(user, request_path):
    """Redirect portal users away from generic authenticated landing pages."""
    redirect_to = get_cafm_login_redirect(user)
    if not redirect_to:
        return None

    normalized_path = unquote(request_path or "").rstrip("/").lower()
    if normalized_path in TECHNICIAN_DEFAULT_LANDING_PATHS:
        return redirect_to
    return None


def redirect_technician_default_pages(response=None, request=None):
    """Replace default-page responses with the user's CAFM portal redirect."""
    request = request or getattr(frappe.local, "request", None)
    if not request or request.method != "GET" or response is None:
        return

    redirect_to = get_cafm_default_page_redirect(
        frappe.session.user, request.path
    )
    if redirect_to:
        response.status_code = 302
        response.headers["Location"] = redirect_to
        response.set_data(b"")


def redirect_technician_after_login(login_manager=None):
    """Backward-compatible alias retained for installed sites and imports."""
    redirect_cafm_after_login(login_manager)

import frappe


PRIVILEGED_ROLES = {"System Manager", "Facility Manager", "Facility Coordinator"}


def get_employee_for_user(user):
    return frappe.db.get_value(
        "Employee", {"user_id": user, "status": "Active"}, "name"
    )


def get_provider_for_user(user):
    return frappe.db.get_value(
        "Facility Service Provider",
        {"vendor_user": user, "status": "Active"},
        "name",
    )


def issue_query(user=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return ""

    employee = get_employee_for_user(user)
    if not employee:
        return "1=0"

    employee = frappe.db.escape(employee)
    conditions = []
    if "Requester / Employee" in roles:
        conditions.append(f"`tabIssue`.`custom_requester` = {employee}")
    if "Technician" in roles:
        conditions.append(
            "EXISTS (SELECT 1 FROM `tabFacility Work Order` fwo "
            "WHERE fwo.name = `tabIssue`.`custom_work_order` "
            f"AND fwo.technician = {employee})"
        )
    return f"({' OR '.join(conditions)})" if conditions else "1=0"


def has_issue_permission(doc, user=None, ptype=None, debug=False):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return True

    employee = get_employee_for_user(user)
    if not employee:
        return False

    if (
        ptype == "create"
        and "Requester / Employee" in roles
        and doc.is_new()
    ):
        return True

    if "Requester / Employee" in roles and doc.custom_requester == employee:
        return ptype not in ("delete", "cancel", "submit")

    if "Technician" in roles and doc.custom_work_order:
        technician = frappe.db.get_value(
            "Facility Work Order", doc.custom_work_order, "technician"
        )
        return technician == employee and ptype == "read"

    return False


def work_order_query(user=None, table_alias=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return ""

    tick = chr(96)
    table = (
        f"{tick}{table_alias}{tick}"
        if table_alias
        else f"{tick}tabFacility Work Order{tick}"
    )
    conditions = []
    if "Vendor" in roles:
        provider = get_provider_for_user(user)
        if provider:
            conditions.append(
                f"{table}.{tick}assignment_type{tick} = "
                "'External Vendor' AND "
                f"{table}.{tick}vendor{tick} = "
                f"{frappe.db.escape(provider)}"
            )

    employee = get_employee_for_user(user)
    if employee:
        employee = frappe.db.escape(employee)
        if "Technician" in roles:
            conditions.append(
                f"{table}.{tick}technician{tick} = {employee}"
            )
        if "Requester / Employee" in roles:
            conditions.append(
                "EXISTS (SELECT 1 FROM "
                f"{tick}tabIssue{tick} issue "
                f"WHERE issue.name = {table}.{tick}maintenance_request{tick} "
                f"AND issue.custom_requester = {employee})"
            )

    return f"({' OR '.join(conditions)})" if conditions else "1=0"


def has_work_order_permission(doc, user=None, ptype=None, debug=False):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return True

    if "Vendor" in roles:
        provider = get_provider_for_user(user)
        if (
            provider
            and doc.assignment_type == "External Vendor"
            and doc.vendor == provider
        ):
            return ptype not in ("create", "delete", "cancel", "submit")

    employee = get_employee_for_user(user)
    if not employee:
        return False

    if "Technician" in roles and doc.technician == employee:
        return ptype not in ("delete", "cancel", "submit")

    if "Requester / Employee" in roles:
        requester = frappe.db.get_value(
            "Issue", doc.maintenance_request, "custom_requester"
        )
        return requester == employee and ptype == "read"

    return False


def service_provider_query(user=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return ""
    if "Vendor" not in roles:
        return "1=0"

    provider = get_provider_for_user(user)
    if not provider:
        return "1=0"
    tick = chr(96)
    return (
        f"{tick}tabFacility Service Provider{tick}."
        f"{tick}name{tick} = {frappe.db.escape(provider)}"
    )


def has_service_provider_permission(
    doc,
    user=None,
    ptype=None,
    debug=False,
):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return True
    return (
        "Vendor" in roles
        and doc.vendor_user == user
        and doc.status == "Active"
        and ptype == "read"
    )


VENDOR_LOCKED_WORK_ORDER_FIELDS = (
    "work_order_type",
    "maintenance_request",
    "preventive_maintenance_plan",
    "subject",
    "company",
    "facility_location",
    "asset",
    "category",
    "priority",
    "work_description",
    "assignment_type",
    "technician",
    "vendor",
    "planned_start",
    "planned_end",
    "labor_entries",
    "materials",
    "material_cost",
    "inspection_required",
    "inspection_template",
    "closed_by",
    "closed_on",
)


def validate_vendor_work_order_changes(work_order):
    roles = set(frappe.get_roles())
    if "Vendor" not in roles or roles & PRIVILEGED_ROLES:
        return

    provider = get_provider_for_user(frappe.session.user)
    if (
        not provider
        or work_order.assignment_type != "External Vendor"
        or work_order.vendor != provider
    ):
        frappe.throw(
            "You can only update Work Orders assigned to your Service Provider.",
            frappe.PermissionError,
        )

    if work_order.is_new():
        frappe.throw(
            "Vendors cannot create Work Orders.",
            frappe.PermissionError,
        )

    for fieldname in VENDOR_LOCKED_WORK_ORDER_FIELDS:
        if work_order.has_value_changed(fieldname):
            frappe.throw(
                "Vendors cannot change the Work Order field {0}.".format(
                    work_order.meta.get_label(fieldname)
                ),
                frappe.PermissionError,
            )


def inspection_query(user=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return ""

    employee = get_employee_for_user(user)
    if not employee or "Technician" not in roles:
        return "1=0"

    tick = chr(96)
    return (
        f"{tick}tabFacility Inspection{tick}.{tick}inspector{tick} = "
        f"{frappe.db.escape(employee)}"
    )


def has_inspection_permission(
    doc,
    user=None,
    ptype=None,
    debug=False,
):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return True

    employee = get_employee_for_user(user)
    if (
        employee
        and "Technician" in roles
        and doc.inspector == employee
    ):
        return ptype not in ("create", "delete", "cancel", "submit")

    return False

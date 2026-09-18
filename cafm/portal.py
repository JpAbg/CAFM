import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, now_datetime


PORTAL_ADMIN_ROLES = {"Administrator", "System Manager"}


def _is_portal_admin():
    return bool(set(frappe.get_roles()) & PORTAL_ADMIN_ROLES)


def _requester_for_current_user():
    roles = set(frappe.get_roles())
    if roles & {"Client", "Customer"}:
        requester = frappe.db.get_value(
            "Client",
            {"user": frappe.session.user, "status": "Active"},
            "name",
        )
    else:
        requester = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.session.user, "status": "Active"},
            "name",
        )
    if not requester:
        frappe.throw(_("Your account is not linked to an active requester record."))
    return requester


@frappe.whitelist()
def get_portal_requests():
    is_admin = _is_portal_admin()
    requester = None if is_admin else _requester_for_current_user()
    user = frappe.db.get_value(
        "User", frappe.session.user, ["first_name", "last_name"], as_dict=True
    )
    user_full_name = " ".join(filter(None, [user.first_name, user.last_name])) if user else frappe.session.user
    filters = {"raised_by": frappe.session.user}
    requests = frappe.get_all(
        "Issue",
        filters=filters,
        fields=[
            "name", "naming_series", "subject", "issue_type", "priority", "raised_by",
            "custom_requester", "custom_asset", "custom_facility_location", "custom_issue_status",
            "custom_work_order", "description", "status", "agreement_status",
            "service_level_agreement", "opening_date", "opening_time",
            "first_responded_on", "resolution_details", "custom_pending_reason",
            "custom_rejection_reason", "contact", "company", "via_customer_portal", "modified",
        ],
        order_by="modified desc",
        limit_page_length=100,
        ignore_permissions=True,
    )
    resolved_statuses = {"Resolved", "Closed"}
    hidden_statuses = {"Rejected"}
    resolved_cutoff = add_days(now_datetime(), -30)
    requests = [
        request
        for request in requests
        if request.custom_issue_status not in hidden_statuses
        and (request.custom_issue_status not in resolved_statuses
        or get_datetime(request.modified) >= resolved_cutoff)
    ]
    work_order_names = [request.custom_work_order for request in requests if request.custom_work_order]
    technician_by_work_order = {}
    if work_order_names:
        work_orders = frappe.get_all(
            "Facility Work Order",
            filters={"name": ["in", work_order_names]},
            fields=["name", "technician"],
        )
        technician_names = [row.technician for row in work_orders if row.technician]
        email_by_technician = {}
        if technician_names:
            technicians = frappe.get_all(
                "Employee",
                filters={"name": ["in", technician_names]},
                fields=["name", "user_id", "company_email", "personal_email"],
            )
            email_by_technician = {
                row.name: row.user_id or row.company_email or row.personal_email
                for row in technicians
            }
        technician_by_work_order = {
            row.name: email_by_technician.get(row.technician)
            for row in work_orders
        }
    for request in requests:
        request["assigned_to_email"] = technician_by_work_order.get(request.custom_work_order)
    return {
        "requests": requests,
        "user_full_name": user_full_name,
        "locations": frappe.get_all("Facility Location", pluck="name", order_by="name"),
        "categories": frappe.get_all("Issue Type", pluck="name", order_by="name"),
        "priorities": frappe.get_all("Issue Priority", pluck="name", order_by="name"),
        "requester": requester or frappe.session.user,
        "employees": frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", order_by="name") if is_admin else [requester],
        "assets": frappe.get_all("Asset", pluck="name", order_by="name"),
        "is_admin": is_admin,
        "can_create": True,
        "can_manage_requests": True,
        "can_open_full_record": is_admin,
    }


@frappe.whitelist()
def submit_portal_request(subject, facility_location, issue_type, priority, description, requester=None, asset=None):
    if _is_portal_admin():
        requester = (requester or "").strip()
        if not requester or not frappe.db.exists("Employee", {"name": requester, "status": "Active"}):
            frappe.throw(_("Select an active requester."))
    else:
        requester = _requester_for_current_user()
    fields = {
        "subject": (subject or "").strip(),
        "raised_by": frappe.session.user,
        "custom_requester": requester,
        "custom_facility_location": facility_location,
        "custom_asset": asset or None,
        "issue_type": issue_type,
        "priority": priority,
        "description": description,
        "custom_issue_status": "New",
    }
    if not all([fields["subject"], facility_location, issue_type, priority, description]):
        frappe.throw(_("Please complete every required field."))
    request = frappe.get_doc({"doctype": "Issue", **fields})
    request.flags.preserve_portal_priority = True
    request.insert(ignore_permissions=True)
    return {"name": request.name, "status": request.custom_issue_status}


def _portal_request(name):
    request = frappe.get_doc("Issue", name)
    if _is_portal_admin():
        return request
    requester = _requester_for_current_user()
    if request.custom_requester != requester:
        frappe.throw(_("You can only manage requests submitted by your account."))
    return request


@frappe.whitelist()
def update_portal_request(name, subject, facility_location, issue_type, priority, description, requester=None, asset=None):
    request = _portal_request(name)
    if request.custom_issue_status != "New" or request.custom_work_order:
        frappe.throw(_("Only a new request can be edited."))
    values = {
        "subject": (subject or "").strip(),
        "custom_facility_location": facility_location,
        "issue_type": issue_type,
        "priority": priority,
        "description": description,
        "custom_asset": asset or None,
    }
    if _is_portal_admin():
        if not requester or not frappe.db.exists("Employee", {"name": requester, "status": "Active"}):
            frappe.throw(_("Select an active requester."))
        values["custom_requester"] = requester
    required_values = [values["subject"], values["custom_facility_location"], values["issue_type"], values["priority"], values["description"]]
    if not all(required_values):
        frappe.throw(_("Please complete every required field."))
    for fieldname, value in values.items():
        setattr(request, fieldname, value)
    request.flags.preserve_portal_priority = True
    request.save(ignore_permissions=True)
    return {"name": request.name, "status": request.custom_issue_status}


@frappe.whitelist()
def withdraw_portal_request(name):
    request = _portal_request(name)
    if request.custom_issue_status != "New" or request.custom_work_order:
        frappe.throw(_("Only a new request can be withdrawn."))
    request.custom_issue_status = "Rejected"
    request.custom_rejection_reason = "Withdrawn by the requester through the Facility Portal."
    request.flags.preserve_portal_priority = True
    request.save(ignore_permissions=True)
    return {"name": request.name, "status": "Withdrawn"}

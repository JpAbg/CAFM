import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, now_datetime


def _employee_for_current_user():
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user, "status": "Active"},
        "name",
    )
    if not employee:
        frappe.throw(_("Your account is not linked to an active employee record."))
    return employee


@frappe.whitelist()
def get_portal_requests():
    employee = _employee_for_current_user()
    requests = frappe.get_all(
        "Issue",
        filters={"custom_requester": employee},
        fields=[
            "name", "subject", "issue_type", "priority",
            "custom_facility_location", "custom_issue_status", "custom_work_order", "description", "modified",
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
    return {
        "requests": requests,
        "locations": frappe.get_all("Facility Location", pluck="name", order_by="name"),
        "categories": frappe.get_all("Issue Type", pluck="name", order_by="name"),
        "priorities": frappe.get_all("Issue Priority", pluck="name", order_by="name"),
    }


@frappe.whitelist()
def submit_portal_request(subject, facility_location, issue_type, priority, description):
    employee = _employee_for_current_user()
    fields = {
        "subject": (subject or "").strip(),
        "raised_by": frappe.session.user,
        "custom_requester": employee,
        "custom_facility_location": facility_location,
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
    employee = _employee_for_current_user()
    request = frappe.get_doc("Issue", name)
    if request.custom_requester != employee:
        frappe.throw(_("You can only manage requests submitted by your account."))
    return request


@frappe.whitelist()
def update_portal_request(name, subject, facility_location, issue_type, priority, description):
    request = _portal_request(name)
    if request.custom_issue_status != "New" or request.custom_work_order:
        frappe.throw(_("Only a new request can be edited."))
    values = {
        "subject": (subject or "").strip(),
        "custom_facility_location": facility_location,
        "issue_type": issue_type,
        "priority": priority,
        "description": description,
    }
    if not all(values.values()):
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

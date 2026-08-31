import frappe
from frappe import _


PRIVILEGED_ROLES = {"System Manager", "Facility Manager", "Facility Coordinator"}
NATIVE_STATUS_BY_CAFM_STATUS = {
    "New": "Open",
    "Assigned": "Open",
    "In Progress": "Open",
    "Pending": "Hold",
    "Resolved": "Resolved",
    "Closed": "Closed",
    "Rejected": "Closed",
}
PRIORITY_RANK = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 4,
}


def validate_cafm_issue(doc, method=None):
    validate_requester(doc)
    apply_priority_rules(doc)
    validate_required_fields(doc)
    validate_asset_location(doc)
    validate_status_response(doc)
    synchronize_native_status(doc)
    validate_work_order(doc)


def apply_priority_rules(doc):
    doc.priority = get_automatic_priority(
        issue_type=doc.issue_type,
        asset=doc.custom_asset,
        current_priority=doc.priority,
    )


@frappe.whitelist()
def get_automatic_priority(
    issue_type=None,
    asset=None,
    current_priority=None,
):
    candidates = [current_priority]
    if issue_type:
        candidates.append(
            frappe.db.get_value(
                "Issue Type",
                issue_type,
                "custom_cafm_minimum_priority",
            )
        )
    if asset:
        candidates.append(
            frappe.db.get_value("Asset", asset, "custom_criticality")
        )

    configured = [
        priority for priority in candidates if priority in PRIORITY_RANK
    ]
    if not configured:
        return current_priority
    return max(configured, key=PRIORITY_RANK.get)


def validate_requester(doc):
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles & PRIVILEGED_ROLES:
        return

    employee = frappe.db.get_value(
        "Employee", {"user_id": user, "status": "Active"}, "name"
    )
    if not employee:
        frappe.throw(_("Your user account must be linked to an active Employee."))

    if doc.is_new():
        doc.custom_requester = employee
        doc.raised_by = user
        return

    previous_requester = frappe.db.get_value("Issue", doc.name, "custom_requester")
    if doc.custom_requester != previous_requester:
        frappe.throw(_("You cannot change the requester."))


def validate_required_fields(doc):
    if not doc.custom_requester:
        frappe.throw(_("Requester is required."))
    if not doc.custom_facility_location:
        frappe.throw(_("Facility Location is required."))
    if not doc.issue_type:
        frappe.throw(_("Maintenance Category is required."))
    if not doc.priority:
        frappe.throw(_("Priority is required."))


def validate_asset_location(doc):
    if not doc.custom_asset:
        return
    asset_location = frappe.db.get_value("Asset", doc.custom_asset, "custom_asset_location")
    if asset_location != doc.custom_facility_location:
        frappe.throw(_("The selected asset does not belong to this location."))


def validate_status_response(doc):
    if doc.custom_issue_status == "Pending" and not doc.custom_pending_reason:
        frappe.throw(_("A Pending Reason is required."))
    if doc.custom_issue_status == "Rejected" and not doc.custom_rejection_reason:
        frappe.throw(_("A Rejection Reason is required."))
    if doc.custom_issue_status == "Resolved" and not doc.resolution_details:
        frappe.throw(_("Resolution Details are required."))


def synchronize_native_status(doc):
    native_status = NATIVE_STATUS_BY_CAFM_STATUS.get(doc.custom_issue_status)
    if native_status:
        doc.status = native_status


def validate_work_order(doc):
    if not doc.custom_work_order:
        return
    source_issue = frappe.db.get_value(
        "Facility Work Order", doc.custom_work_order, "maintenance_request"
    )
    if source_issue != doc.name:
        frappe.throw(_("The selected Work Order does not belong to this Issue."))

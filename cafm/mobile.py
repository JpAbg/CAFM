import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, now_datetime

ACTIVE_STATUSES = ("Assigned", "In Progress", "Pending")
COMPLETED_STATUSES = ("Resolved", "Closed")
ALLOWED_VIEWS = ("active", "assigned", "in_progress", "pending", "overdue", "completed")


@frappe.whitelist()
def get_my_work_orders(view="active", priority=None, facility_location=None):
    user_full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
    """Return the logged-in technician's work orders for the mobile workspace."""
    employee = frappe.db.get_value(
        "Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
    )
    empty_summary = {"assigned": 0, "in_progress": 0, "pending": 0, "overdue": 0}
    if not employee:
        return {
            "employee": None,
            "user_full_name": user_full_name,
            "work_orders": [],
            "locations": [],
            "message": _(
                "Your account is not linked to an active Employee record. "
                "Ask a Facility Manager to complete that link."
            ),
            "summary": empty_summary,
        }

    view = view if view in ALLOWED_VIEWS else "active"
    priority = priority if priority and priority != "All" else None
    facility_location = facility_location if facility_location and facility_location != "All" else None
    all_work_orders = frappe.get_all(
        "Facility Work Order",
        filters={"docstatus": ["<", 2], "technician": employee, "work_order_status": ["in", ACTIVE_STATUSES + COMPLETED_STATUSES]},
        fields=["name", "subject", "priority", "category", "facility_location", "asset", "work_order_status", "planned_end", "actual_end", "closed_on", "modified", "sla_status", "sla_resolution_due"],
        order_by="modified desc, name asc",
        ignore_permissions=True,
    )
    reference_datetime = now_datetime()
    completed_cutoff = add_days(reference_datetime, -30)
    summary = empty_summary.copy()
    locations = sorted({row.facility_location for row in all_work_orders if row.facility_location})
    work_orders = []
    for work_order in all_work_orders:
        is_active = work_order.work_order_status in ACTIVE_STATUSES
        is_completed = work_order.work_order_status in COMPLETED_STATUSES
        work_order.is_overdue = bool(is_active and work_order.planned_end and get_datetime(work_order.planned_end) < reference_datetime)
        if is_active:
            if work_order.work_order_status == "Assigned":
                summary["assigned"] += 1
            elif work_order.work_order_status == "In Progress":
                summary["in_progress"] += 1
            elif work_order.work_order_status == "Pending":
                summary["pending"] += 1
            if work_order.is_overdue:
                summary["overdue"] += 1
        completed_on = work_order.actual_end or work_order.closed_on or work_order.modified
        matches_view = {
            "active": is_active, "assigned": work_order.work_order_status == "Assigned",
            "in_progress": work_order.work_order_status == "In Progress",
            "pending": work_order.work_order_status == "Pending",
            "overdue": work_order.is_overdue,
            "completed": is_completed and get_datetime(completed_on) >= completed_cutoff,
        }[view]
        if matches_view and (not priority or work_order.priority == priority) and (not facility_location or work_order.facility_location == facility_location):
            work_orders.append(work_order)
    if view == "completed":
        work_orders.sort(key=lambda row: row.actual_end or row.closed_on or row.modified, reverse=True)
    else:
        work_orders.sort(key=lambda row: (not bool(row.is_overdue), row.planned_end or row.modified))
    return {"employee": employee, "user_full_name": user_full_name, "work_orders": work_orders, "locations": locations, "summary": summary}

@frappe.whitelist()
def get_my_mobile_notifications(limit=10):
    """Return recent notifications addressed to the signed-in technician."""
    notifications = frappe.get_all(
        "Notification Log",
        filters={"for_user": frappe.session.user},
        fields=["name", "subject", "email_content", "document_type", "document_name", "read", "creation"],
        order_by="creation desc",
        limit_page_length=min(max(int(limit or 10), 1), 20),
        ignore_permissions=True,
    )
    unread_count = sum(1 for notification in notifications if not notification.read)
    return {"notifications": notifications, "unread_count": unread_count}


@frappe.whitelist()
def mark_mobile_notifications_read(names):
    names = frappe.parse_json(names) if isinstance(names, str) else names
    names = [name for name in (names or []) if name]
    if not names:
        return
    frappe.db.set_value(
        "Notification Log",
        {"name": ["in", names], "for_user": frappe.session.user},
        "read",
        1,
        update_modified=False,
    )

@frappe.whitelist()
def mark_mobile_notifications_read(names):
    """Mark only the signed-in user's selected notifications as read."""
    names = frappe.parse_json(names) if isinstance(names, str) else names
    for notification_name in names or []:
        if frappe.db.exists(
            "Notification Log",
            {"name": notification_name, "for_user": frappe.session.user},
        ):
            frappe.db.set_value(
                "Notification Log",
                notification_name,
                "read",
                1,
                update_modified=False,
            )

@frappe.whitelist()
def mark_all_mobile_notifications_read():
    """Mark all notifications addressed to the signed-in user as read."""
    frappe.db.sql(
        """
        UPDATE `tabNotification Log`
        SET `read` = 1
        WHERE for_user = %s AND `read` = 0
        """,
        frappe.session.user,
    )

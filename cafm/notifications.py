from html import escape

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import (
    enqueue_create_notification,
)
from frappe.utils import add_days, format_datetime, getdate, now_datetime, nowdate


SUPERVISOR_ROLES = ("Facility Manager", "Facility Coordinator")
COMPLETED_WORK_ORDER_STATUSES = ("Resolved", "Closed", "Cancelled")
UPCOMING_MAINTENANCE_DAYS = 7


def backfill_hrms_assignment_notifications():
    """Create missing HRMS-bell entries for currently assigned work orders."""
    if not frappe.db.exists("DocType", "PWA Notification"):
        return 0

    created = 0
    work_orders = frappe.get_all(
        "Facility Work Order",
        filters={
            "work_order_status": ["not in", COMPLETED_WORK_ORDER_STATUSES]
        },
        fields=["name", "assignment_type", "technician", "vendor"],
    )
    for row in work_orders:
        desired_user = get_assignment_user(row)
        if not desired_user:
            continue
        work_order = frappe.get_doc("Facility Work Order", row.name)
        before = frappe.db.count("PWA Notification")
        work_order.create_hrms_assignment_notification(desired_user)
        created += frappe.db.count("PWA Notification") - before
    return created


def get_supervisor_users():
    users = frappe.get_all(
        "Has Role",
        filters={
            "parenttype": "User",
            "role": ["in", SUPERVISOR_ROLES],
        },
        pluck="parent",
    )
    return get_enabled_users(users)


def get_enabled_users(users):
    users = sorted(set(filter(None, users)))
    if not users:
        return []

    return frappe.get_all(
        "User",
        filters={
            "name": ["in", users],
            "enabled": 1,
            "user_type": "System User",
        },
        pluck="name",
        order_by="name asc",
    )


def get_assignment_user(row):
    if row.assignment_type == "Internal Technician" and row.technician:
        user = frappe.db.get_value("Employee", row.technician, "user_id")
        enabled = frappe.db.get_value("User", user, "enabled") if user else 0
        return user if enabled else None

    if row.assignment_type == "External Vendor" and row.vendor:
        user = frappe.db.get_value(
            "Facility Service Provider",
            row.vendor,
            "vendor_user",
        )
        enabled = frappe.db.get_value("User", user, "enabled") if user else 0
        return user if enabled else None

    return None


def format_due_datetime(value):
    return format_datetime(value) or str(value or _("Not Set"))


def get_overdue_work_orders(reference_datetime=None):
    reference_datetime = reference_datetime or now_datetime()
    return frappe.get_all(
        "Facility Work Order",
        filters={
            "work_order_status": [
                "not in",
                COMPLETED_WORK_ORDER_STATUSES,
            ],
            "planned_end": ["<", reference_datetime],
        },
        fields=[
            "name",
            "subject",
            "priority",
            "planned_end",
            "facility_location",
            "assignment_type",
            "technician",
            "vendor",
        ],
        order_by="planned_end asc, priority desc",
    )


def notify_overdue_work_orders(reference_datetime=None):
    reference_datetime = reference_datetime or now_datetime()
    supervisors = get_supervisor_users()
    if not supervisors:
        return []

    notified = []
    for work_order in get_overdue_work_orders(reference_datetime):
        due_date = format_due_datetime(work_order.planned_end)
        subject = _("Overdue Work Order {0}: {1}").format(
            work_order.name,
            work_order.subject,
        )
        description = _(
            "<p>This work order became overdue on {0}.</p>"
            "<p><strong>Priority:</strong> {1}<br>"
            "<strong>Location:</strong> {2}</p>"
        ).format(
            escape(due_date),
            escape(work_order.priority or _("Not Set")),
            escape(work_order.facility_location or _("Not Set")),
        )
        enqueue_create_notification(
            supervisors,
            {
                "type": "Alert",
                "title": subject,
                "description": description,
                "document_type": "Facility Work Order",
                "document_name": work_order.name,
                "from_user": "Administrator",
                "app": "cafm",
            },
            dedupe_on=[
                "type",
                "document_type",
                "document_name",
                "title",
            ],
        )
        notified.append(work_order.name)

    return notified


def send_upcoming_preventive_reminders(
    reference_date=None,
    reminder_days=UPCOMING_MAINTENANCE_DAYS,
):
    reference_date = getdate(reference_date or nowdate())
    reminder_horizon = getdate(add_days(reference_date, reminder_days))
    supervisors = get_supervisor_users()
    reminded = []

    plans = frappe.get_all(
        "Preventive Maintenance Plan",
        filters={
            "is_active": 1,
            "next_due_date": ["between", [reference_date, reminder_horizon]],
        },
        fields=[
            "name",
            "plan_name",
            "next_due_date",
            "asset",
            "facility_location",
            "assignment_type",
            "technician",
            "vendor",
        ],
        order_by="next_due_date asc",
    )

    for plan in plans:
        assigned_user = get_assignment_user(plan)
        recipients = [assigned_user] if assigned_user else supervisors
        recipients = get_enabled_users(recipients)
        if not recipients:
            continue

        due_date = getdate(plan.next_due_date)
        subject = _("Upcoming Preventive Maintenance: {0} on {1}").format(
            plan.plan_name,
            due_date,
        )
        description = _(
            "<p>Preventive maintenance is due on {0}.</p>"
            "<p><strong>Asset:</strong> {1}<br>"
            "<strong>Location:</strong> {2}</p>"
        ).format(
            escape(str(due_date)),
            escape(plan.asset or _("Not Set")),
            escape(plan.facility_location or _("Not Set")),
        )
        enqueue_create_notification(
            recipients,
            {
                "type": "Alert",
                "title": subject,
                "description": description,
                "document_type": "Preventive Maintenance Plan",
                "document_name": plan.name,
                "from_user": "Administrator",
                "app": "cafm",
            },
            dedupe_on=[
                "type",
                "document_type",
                "document_name",
                "title",
            ],
        )
        reminded.append(plan.name)

    return reminded


def send_daily_overdue_summary(
    reference_date=None,
    reference_datetime=None,
):
    reference_date = getdate(reference_date or nowdate())
    reference_datetime = reference_datetime or now_datetime()
    supervisors = get_supervisor_users()
    overdue = get_overdue_work_orders(reference_datetime)

    if not supervisors or not overdue:
        return 0

    subject = _("Daily Overdue Maintenance Summary - {0}").format(
        reference_date
    )
    items = []
    for work_order in overdue:
        items.append(
            _(
                "<li><strong>{0}</strong> - {1} "
                "(Priority: {2}, Due: {3})</li>"
            ).format(
                escape(work_order.name),
                escape(work_order.subject or ""),
                escape(work_order.priority or _("Not Set")),
                escape(format_due_datetime(work_order.planned_end)),
            )
        )

    description = _(
        "<p>{0} maintenance work order(s) are overdue.</p><ul>{1}</ul>"
    ).format(len(overdue), "".join(items))
    enqueue_create_notification(
        supervisors,
        {
            "type": "Alert",
            "title": subject,
            "description": description,
            "from_user": "Administrator",
            "link": "/app/facility-work-order",
            "app": "cafm",
        },
        dedupe_on=["type", "title"],
    )
    return len(overdue)

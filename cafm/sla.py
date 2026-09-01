from html import escape

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import (
    enqueue_create_notification,
)
from frappe.utils import add_to_date, get_datetime, now_datetime

from cafm.notifications import (
    COMPLETED_WORK_ORDER_STATUSES,
    format_due_datetime,
    get_supervisor_users,
)


SLA_TRACKING_FIELDS = (
    "sla_policy",
    "sla_response_due",
    "sla_resolution_due",
    "sla_response_achieved_on",
    "sla_resolution_achieved_on",
    "sla_status",
)


def get_matching_sla_policy(work_order):
    policies = frappe.get_all(
        "Facility SLA Policy",
        filters={"is_active": 1},
        fields=[
            "name",
            "company",
            "category",
            "priority",
            "response_target_hours",
            "resolution_target_hours",
        ],
    )
    matches = []
    for policy in policies:
        if policy.company and policy.company != work_order.company:
            continue
        if policy.category and policy.category != work_order.category:
            continue
        if policy.priority and policy.priority != work_order.priority:
            continue
        specificity = sum(
            bool(getattr(policy, field))
            for field in ("company", "category", "priority")
        )
        matches.append((specificity, policy.name, policy))

    if not matches:
        return None
    return sorted(matches, key=lambda row: (-row[0], row[1]))[0][2]


def calculate_sla_status(
    response_due,
    resolution_due,
    response_achieved_on=None,
    resolution_achieved_on=None,
    reference_datetime=None,
):
    reference_datetime = get_datetime(reference_datetime or now_datetime())
    response_due = get_datetime(response_due)
    resolution_due = get_datetime(resolution_due)
    response_breached = (
        (response_achieved_on and get_datetime(response_achieved_on) > response_due)
        or (not response_achieved_on and reference_datetime > response_due)
    )
    resolution_breached = (
        (resolution_achieved_on and get_datetime(resolution_achieved_on) > resolution_due)
        or (not resolution_achieved_on and reference_datetime > resolution_due)
    )

    if resolution_breached:
        return "Resolution Breached"
    if response_breached:
        return "Response Breached"
    if resolution_achieved_on:
        return "Met"
    return "On Track"


def update_work_order_sla(work_order, reference_datetime=None):
    if work_order.work_order_status == "Cancelled":
        work_order.sla_status = "Not Applicable"
        return

    policy = None
    if work_order.sla_policy and work_order.work_order_status != "Draft":
        policy = frappe.db.get_value(
            "Facility SLA Policy",
            work_order.sla_policy,
            [
                "name",
                "response_target_hours",
                "resolution_target_hours",
            ],
            as_dict=True,
        )
    policy = policy or get_matching_sla_policy(work_order)
    if not policy:
        work_order.sla_status = "Not Applicable"
        return

    reference_datetime = get_datetime(reference_datetime or now_datetime())
    baseline = get_datetime(work_order.creation or reference_datetime)
    work_order.sla_policy = policy.name
    work_order.sla_response_due = work_order.sla_response_due or add_to_date(
        baseline, hours=policy.response_target_hours
    )
    work_order.sla_resolution_due = work_order.sla_resolution_due or add_to_date(
        baseline, hours=policy.resolution_target_hours
    )

    if (
        work_order.work_order_status
        in ("Assigned", "In Progress", "Pending", "Resolved", "Closed")
        and not work_order.sla_response_achieved_on
    ):
        work_order.sla_response_achieved_on = reference_datetime

    if (
        work_order.work_order_status in ("Resolved", "Closed")
        and not work_order.sla_resolution_achieved_on
    ):
        work_order.sla_resolution_achieved_on = (
            work_order.actual_end or reference_datetime
        )

    work_order.sla_status = calculate_sla_status(
        work_order.sla_response_due,
        work_order.sla_resolution_due,
        work_order.sla_response_achieved_on,
        work_order.sla_resolution_achieved_on,
        reference_datetime,
    )


def backfill_work_order_slas():
    for name in frappe.get_all("Facility Work Order", pluck="name"):
        work_order = frappe.get_doc("Facility Work Order", name)
        update_work_order_sla(work_order)
        frappe.db.set_value(
            "Facility Work Order",
            name,
            {field: work_order.get(field) for field in SLA_TRACKING_FIELDS},
            update_modified=False,
        )


def notify_sla_breaches(reference_datetime=None):
    reference_datetime = get_datetime(reference_datetime or now_datetime())
    recipients = get_supervisor_users()
    if not recipients:
        return []

    breached = []
    work_orders = frappe.get_all(
        "Facility Work Order",
        filters={
            "work_order_status": ["not in", COMPLETED_WORK_ORDER_STATUSES],
            "sla_policy": ["is", "set"],
        },
        fields=[
            "name", "subject", "priority", "facility_location",
            "sla_policy", "sla_response_due", "sla_resolution_due",
            "sla_response_achieved_on", "sla_resolution_achieved_on",
            "sla_response_breached_on", "sla_resolution_breached_on",
        ],
    )
    for row in work_orders:
        response_due = row.sla_response_due
        resolution_due = row.sla_resolution_due
        status = calculate_sla_status(
            response_due,
            resolution_due,
            row.sla_response_achieved_on,
            row.sla_resolution_achieved_on,
            reference_datetime,
        )
        updates = {"sla_status": status}

        for breach_type, due_field, notified_field, label in (
            (
                "Response",
                response_due,
                "sla_response_breached_on",
                _("Response SLA Breach"),
            ),
            (
                "Resolution",
                resolution_due,
                "sla_resolution_breached_on",
                _("Resolution SLA Breach"),
            ),
        ):
            if (
                reference_datetime <= get_datetime(due_field)
                or row.get(notified_field)
                or (
                    breach_type == "Response"
                    and row.sla_response_achieved_on
                    and get_datetime(row.sla_response_achieved_on) <= get_datetime(due_field)
                )
                or (
                    breach_type == "Resolution"
                    and row.sla_resolution_achieved_on
                    and get_datetime(row.sla_resolution_achieved_on) <= get_datetime(due_field)
                )
            ):
                continue

            title = _("{0} - {1}: {2}").format(label, row.name, row.subject)
            description = _(
                "<p><strong>{0}</strong> missed its {1} target.</p>"
                "<p><strong>Policy:</strong> {2}<br>"
                "<strong>Due:</strong> {3}<br>"
                "<strong>Priority:</strong> {4}<br>"
                "<strong>Location:</strong> {5}</p>"
            ).format(
                escape(row.subject or row.name),
                escape(breach_type.lower()),
                escape(row.sla_policy),
                escape(format_due_datetime(due_field)),
                escape(row.priority or _("Not Set")),
                escape(row.facility_location or _("Not Set")),
            )
            enqueue_create_notification(
                recipients,
                {
                    "type": "Alert",
                    "title": title,
                    "description": description,
                    "document_type": "Facility Work Order",
                    "document_name": row.name,
                    "from_user": "Administrator",
                    "app": "cafm",
                },
                dedupe_on=[
                    "type", "document_type", "document_name", "title",
                ],
            )
            updates[notified_field] = reference_datetime
            breached.append({"work_order": row.name, "type": breach_type})

        frappe.db.set_value(
            "Facility Work Order", row.name, updates, update_modified=False
        )
    return breached

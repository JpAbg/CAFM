import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime, time_diff_in_hours


def _count_work_orders(filters):
    result = frappe.get_list(
        "Facility Work Order",
        filters=filters,
        fields=["count(name) as value"],
        order_by=None,
    )
    return cint(result[0].value) if result else 0


@frappe.whitelist()
def get_overdue_work_orders(filters=None):
    """Count open work orders that became overdue less than four hours ago."""
    return _get_overdue_bucket_card(
        minimum_hours=0,
        maximum_hours=4,
        label=_("Work Orders"),
    )


def _get_overdue_bucket_card(minimum_hours, maximum_hours, label):
    current_time = now_datetime()
    latest_due_time = add_to_date(current_time, hours=-minimum_hours)
    work_order_filters = [
        [
            "Facility Work Order",
            "work_order_status",
            "not in",
            ["Resolved", "Closed", "Cancelled"],
        ],
        ["Facility Work Order", "planned_end", "is", "set"],
        ["Facility Work Order", "planned_end", "<=", latest_due_time],
    ]

    if maximum_hours is not None:
        earliest_due_time = add_to_date(current_time, hours=-maximum_hours)
        work_order_filters.append(
            ["Facility Work Order", "planned_end", ">", earliest_due_time]
        )

    value = _count_work_orders(work_order_filters)
    route_start = (
        str(earliest_due_time)
        if maximum_hours is not None
        else "1900-01-01 00:00:00"
    )

    return {
        "value": value,
        "fieldtype": "Int",
        "route": ["List", "Facility Work Order"],
        "route_options": {
            "work_order_status": [
                "not in",
                ["Resolved", "Closed", "Cancelled"],
            ],
            "planned_end": [
                "between",
                [route_start, str(latest_due_time)],
            ],
        },
        "message": _("{0} in this overdue time band.").format(label),
    }


@frappe.whitelist()
def get_delayed_work_orders(filters=None):
    """Count open work orders that are overdue from four to under 24 hours."""
    return _get_overdue_bucket_card(
        minimum_hours=4,
        maximum_hours=24,
        label=_("Work Orders"),
    )


@frappe.whitelist()
def get_escalated_work_orders(filters=None):
    """Count open work orders that are overdue by one day or more."""
    return _get_overdue_bucket_card(
        minimum_hours=24,
        maximum_hours=None,
        label=_("Work Orders"),
    )


@frappe.whitelist()
def get_average_response_time(filters=None):
    """Return average hours from work-order creation to actual start."""
    work_orders = frappe.get_list(
        "Facility Work Order",
        filters=[["Facility Work Order", "actual_start", "is", "set"]],
        fields=["creation", "actual_start"],
        order_by=None,
        limit_page_length=0,
    )
    response_hours = [
        time_diff_in_hours(row.actual_start, row.creation)
        for row in work_orders
        if row.actual_start and row.creation and row.actual_start >= row.creation
    ]
    value = (
        round(sum(response_hours) / len(response_hours), 2)
        if response_hours
        else 0
    )

    return {
        "value": f"{value:.2f} hrs",
        "fieldtype": "Data",
        "route": ["List", "Facility Work Order"],
        "route_options": {"actual_start": ["is", "set"]},
    }


@frappe.whitelist()
def get_average_resolution_time(filters=None):
    """Return average hours from actual start to actual end."""
    work_orders = frappe.get_list(
        "Facility Work Order",
        filters=[
            ["Facility Work Order", "actual_start", "is", "set"],
            ["Facility Work Order", "actual_end", "is", "set"],
        ],
        fields=["actual_start", "actual_end"],
        order_by=None,
        limit_page_length=0,
    )
    resolution_hours = [
        time_diff_in_hours(row.actual_end, row.actual_start)
        for row in work_orders
        if row.actual_start and row.actual_end and row.actual_end >= row.actual_start
    ]
    value = (
        round(sum(resolution_hours) / len(resolution_hours), 2)
        if resolution_hours
        else 0
    )

    return {
        "value": f"{value:.2f} hrs",
        "fieldtype": "Data",
        "route": ["List", "Facility Work Order"],
        "route_options": {"actual_end": ["is", "set"]},
    }

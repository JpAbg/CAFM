import frappe
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
    """Return the permission-aware count used by the overdue work card."""
    current_time = now_datetime()
    work_order_filters = [
        [
            "Facility Work Order",
            "work_order_status",
            "not in",
            ["Resolved", "Closed", "Cancelled"],
        ],
        ["Facility Work Order", "planned_end", "is", "set"],
        ["Facility Work Order", "planned_end", "<", current_time],
    ]

    value = _count_work_orders(work_order_filters)
    previous_time = add_to_date(current_time, days=-1)
    previous_value = _count_work_orders(
        work_order_filters
        + [
            ["Facility Work Order", "creation", "<", previous_time],
            ["Facility Work Order", "planned_end", "<", previous_time],
        ]
    )
    trend_percentage = (
        round(((value / previous_value) - 1) * 100, 2)
        if previous_value
        else None
    )

    return {
        "value": value,
        "fieldtype": "Int",
        "trend_percentage": trend_percentage,
        "trend_label": "since yesterday",
        "route": ["List", "Facility Work Order"],
        "route_options": {
            "work_order_status": [
                "not in",
                ["Resolved", "Closed", "Cancelled"],
            ],
            "planned_end": [
                "between",
                ["1900-01-01 00:00:00", str(current_time)],
            ],
        },
    }


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

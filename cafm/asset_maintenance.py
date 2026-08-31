import frappe
from frappe.utils import time_diff_in_hours


OPEN_WORK_ORDER_STATUSES = (
    "Draft",
    "Assigned",
    "In Progress",
    "Pending",
    "Resolved",
)


def sync_asset_maintenance_history(work_order):
    if (
        work_order.work_order_status != "Closed"
        or not work_order.asset
    ):
        return

    downtime_hours = 0
    if work_order.actual_start and work_order.actual_end:
        downtime_hours = time_diff_in_hours(
            work_order.actual_end,
            work_order.actual_start,
        )

    values = {
        "asset": work_order.asset,
        "work_order": work_order.name,
        "subject": work_order.subject,
        "company": work_order.company,
        "facility_location": work_order.facility_location,
        "maintenance_request": work_order.maintenance_request,
        "work_order_type": work_order.work_order_type,
        "category": work_order.category,
        "priority": work_order.priority,
        "actual_start": work_order.actual_start,
        "actual_end": work_order.actual_end,
        "downtime_hours": downtime_hours,
        "labor_hours": sum(
            row.hours or 0 for row in work_order.labor_entries
        ),
        "material_cost": work_order.material_cost or 0,
        "resolution_summary": work_order.resolution_summary,
        "closed_by": work_order.closed_by,
        "closed_on": work_order.closed_on,
    }

    history_name = frappe.db.get_value(
        "Facility Asset Maintenance History",
        {"work_order": work_order.name},
        "name",
    )
    if history_name:
        history = frappe.get_doc(
            "Facility Asset Maintenance History",
            history_name,
        )
        history.update(values)
        history.save(ignore_permissions=True)
        return history.name

    return frappe.get_doc(
        {
            "doctype": "Facility Asset Maintenance History",
            **values,
        }
    ).insert(ignore_permissions=True).name


def backfill_asset_maintenance_history():
    work_orders = frappe.get_all(
        "Facility Work Order",
        filters={
            "work_order_status": "Closed",
            "asset": ["is", "set"],
        },
        pluck="name",
    )
    for work_order_name in work_orders:
        if not frappe.db.exists(
            "Facility Asset Maintenance History",
            {"work_order": work_order_name},
        ):
            sync_asset_maintenance_history(
                frappe.get_doc(
                    "Facility Work Order",
                    work_order_name,
                )
            )


@frappe.whitelist()
def get_asset_maintenance_history(asset_name):
    asset = frappe.get_doc("Asset", asset_name)
    asset.check_permission("read")
    accessible_work_orders = frappe.get_list(
        "Facility Work Order",
        filters={
            "asset": asset.name,
            "work_order_status": "Closed",
        },
        pluck="name",
        limit_page_length=500,
    )
    if not accessible_work_orders:
        return []

    return frappe.get_all(
        "Facility Asset Maintenance History",
        filters={"work_order": ["in", accessible_work_orders]},
        fields=[
            "name",
            "work_order",
            "subject",
            "work_order_type",
            "category",
            "priority",
            "actual_start",
            "actual_end",
            "downtime_hours",
            "labor_hours",
            "material_cost",
            "resolution_summary",
            "closed_by",
            "closed_on",
        ],
        order_by="closed_on desc",
        limit_page_length=100,
    )


@frappe.whitelist()
def get_open_maintenance_work(asset_name):
    asset = frappe.get_doc("Asset", asset_name)
    asset.check_permission("read")
    return frappe.get_list(
        "Facility Work Order",
        filters={
            "asset": asset.name,
            "work_order_status": ["in", OPEN_WORK_ORDER_STATUSES],
        },
        fields=[
            "name",
            "subject",
            "work_order_status",
            "priority",
            "planned_end",
            "technician",
            "vendor",
        ],
        order_by="modified desc",
        limit_page_length=50,
    )

# Copyright (c) 2026, Jean Paul Abou Gharib and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)
    data = get_data(filters)
    return get_columns(), data


def validate_filters(filters):
    if not filters.get("from_date"):
        filters.from_date = nowdate()
    if not filters.get("to_date"):
        filters.to_date = filters.from_date
    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date."))


def get_columns():
    return [
        {"label": _("Scheduled Date"), "fieldname": "scheduled_date", "fieldtype": "Date", "width": 125},
        {"label": _("Planned Start"), "fieldname": "planned_start", "fieldtype": "Datetime", "width": 155},
        {"label": _("Planned End"), "fieldname": "planned_end", "fieldtype": "Datetime", "width": 155},
        {"label": _("Work Order"), "fieldname": "work_order", "fieldtype": "Link", "options": "Facility Work Order", "width": 170},
        {"label": _("Subject"), "fieldname": "subject", "fieldtype": "Data", "width": 230},
        {"label": _("Status"), "fieldname": "work_order_status", "fieldtype": "Data", "width": 120},
        {"label": _("Asset"), "fieldname": "asset", "fieldtype": "Link", "options": "Asset", "width": 150},
        {"label": _("Facility Location"), "fieldname": "facility_location", "fieldtype": "Link", "options": "Facility Location", "width": 180},
        {"label": _("Technician"), "fieldname": "technician", "fieldtype": "Link", "options": "Employee", "width": 165},
        {"label": _("PM Plan"), "fieldname": "preventive_maintenance_plan", "fieldtype": "Link", "options": "Preventive Maintenance Plan", "width": 170},
    ]


def get_data(filters):
    conditions = [
        "work_order.docstatus < 2",
        "work_order.work_order_type = 'Preventive'",
        "DATE(COALESCE(work_order.planned_start, work_order.scheduled_occurrence_date)) BETWEEN %(from_date)s AND %(to_date)s",
    ]
    values = {"from_date": filters.from_date, "to_date": filters.to_date}

    for fieldname in ("company", "facility_location", "asset", "technician"):
        if filters.get(fieldname):
            conditions.append(f"work_order.{fieldname} = %({fieldname})s")
            values[fieldname] = filters[fieldname]

    status_filter = filters.get("work_order_status") or "All"
    status_conditions = {
        "All": "work_order.work_order_status NOT IN ('Resolved', 'Closed', 'Cancelled')",
        "Draft": "work_order.work_order_status = 'Draft'",
        "Assigned": "work_order.work_order_status = 'Assigned'",
        "In Progress": "work_order.work_order_status = 'In Progress'",
        "Pending": "work_order.work_order_status = 'Pending'",
    }
    conditions.append(status_conditions.get(status_filter, status_conditions["All"]))

    rows = frappe.db.sql(
        f"""
        SELECT
            work_order.name AS work_order,
            work_order.subject,
            work_order.work_order_status,
            work_order.asset,
            work_order.facility_location,
            work_order.technician,
            work_order.preventive_maintenance_plan,
            work_order.planned_start,
            work_order.planned_end,
            DATE(COALESCE(work_order.planned_start, work_order.scheduled_occurrence_date)) AS scheduled_date
        FROM `tabFacility Work Order` work_order
        WHERE {" AND ".join(conditions)}
        ORDER BY COALESCE(work_order.planned_start, work_order.scheduled_occurrence_date), work_order.name
        """,
        values,
        as_dict=True,
    )

    today = getdate(nowdate())
    for row in rows:
        row.indicator = get_indicator(row, today)
    return rows


def get_indicator(row, today):
    if row.work_order_status == "Cancelled":
        return "grey"
    if row.work_order_status in ("Resolved", "Closed"):
        return "green"
    if row.scheduled_date and getdate(row.scheduled_date) < today:
        return "red"
    if row.work_order_status == "In Progress":
        return "blue"
    if row.work_order_status in ("Assigned", "Pending"):
        return "orange"
    return "grey"

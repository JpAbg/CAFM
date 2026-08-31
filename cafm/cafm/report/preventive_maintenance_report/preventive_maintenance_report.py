import calendar

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(filters)

    return columns, data, None, chart


def validate_filters(filters):
    if not filters.from_date or not filters.to_date:
        frappe.throw(_("From Date and To Date are required."))

    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date."))


def get_columns():
    return [
        {
            "label": _("Plan"),
            "fieldname": "plan",
            "fieldtype": "Link",
            "options": "Preventive Maintenance Plan",
            "width": 150,
        },
        {
            "label": _("Plan Name"),
            "fieldname": "plan_name",
            "fieldtype": "Data",
            "width": 190,
        },
        {
            "label": _("Active"),
            "fieldname": "is_active",
            "fieldtype": "Check",
            "width": 90,
        },
        {
            "label": _("Asset"),
            "fieldname": "asset",
            "fieldtype": "Link",
            "options": "Asset",
            "width": 150,
        },
        {
            "label": _("Facility Location"),
            "fieldname": "facility_location",
            "fieldtype": "Link",
            "options": "Facility Location",
            "width": 180,
        },
        {
            "label": _("Site"),
            "fieldname": "site",
            "fieldtype": "Link",
            "options": "Site",
            "width": 120,
        },
        {
            "label": _("Building"),
            "fieldname": "building",
            "fieldtype": "Link",
            "options": "Building",
            "width": 120,
        },
        {
            "label": _("Category"),
            "fieldname": "category",
            "fieldtype": "Link",
            "options": "Issue Type",
            "width": 130,
        },
        {
            "label": _("Frequency"),
            "fieldname": "frequency",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Next Due Date"),
            "fieldname": "next_due_date",
            "fieldtype": "Date",
            "width": 130,
        },
        {
            "label": _("Scheduled"),
            "fieldname": "scheduled_count",
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "label": _("Completed"),
            "fieldname": "completed_count",
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "label": _("Completed On Time"),
            "fieldname": "completed_on_time",
            "fieldtype": "Int",
            "width": 165,
        },
        {
            "label": _("Overdue"),
            "fieldname": "overdue_count",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("Compliance"),
            "fieldname": "compliance",
            "fieldtype": "Percent",
            "width": 120,
        },
        {
            "label": _("Last Work Order"),
            "fieldname": "last_work_order",
            "fieldtype": "Link",
            "options": "Facility Work Order",
            "width": 170,
        },
    ]


def get_data(filters):
    conditions = []
    values = {
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    if filters.get("company"):
        conditions.append("plan.company = %(company)s")
        values["company"] = filters.company

    if filters.get("is_active") == "Active":
        conditions.append("plan.is_active = 1")
    elif filters.get("is_active") == "Inactive":
        conditions.append("plan.is_active = 0")

    if filters.get("frequency") and filters.frequency != "All":
        conditions.append("plan.frequency = %(frequency)s")
        values["frequency"] = filters.frequency

    if filters.get("asset"):
        conditions.append("plan.asset = %(asset)s")
        values["asset"] = filters.asset

    condition_sql = ""
    if conditions:
        condition_sql = "WHERE " + " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            plan.name AS plan,
            plan.plan_name,
            plan.is_active,
            plan.asset,
            plan.facility_location,
            location.site,
            location.building,
            plan.category,
            plan.frequency,
            plan.next_due_date,
            plan.last_work_order,

            COALESCE(stats.scheduled_count, 0)
                AS scheduled_count,

            COALESCE(stats.completed_count, 0)
                AS completed_count,

            COALESCE(stats.completed_on_time, 0)
                AS completed_on_time,

            COALESCE(stats.overdue_count, 0)
                AS overdue_count,

            CASE
                WHEN COALESCE(stats.scheduled_count, 0) = 0
                THEN 0
                ELSE ROUND(
                    stats.completed_on_time
                    / stats.scheduled_count
                    * 100,
                    2
                )
            END AS compliance

        FROM `tabPreventive Maintenance Plan` plan

        LEFT JOIN `tabFacility Location` location
            ON location.name = plan.facility_location

        LEFT JOIN (
            SELECT
                work_order.preventive_maintenance_plan,

                COUNT(*) AS scheduled_count,

                SUM(
                    CASE
                        WHEN work_order.work_order_status = 'Closed'
                        THEN 1
                        ELSE 0
                    END
                ) AS completed_count,

                SUM(
                    CASE
                        WHEN work_order.work_order_status = 'Closed'
                             AND COALESCE(
                                 work_order.actual_end,
                                 work_order.closed_on
                             ) <= COALESCE(
                                 work_order.planned_end,
                                 DATE_ADD(
                                     work_order.scheduled_occurrence_date,
                                     INTERVAL 1 DAY
                                 )
                             )
                        THEN 1
                        ELSE 0
                    END
                ) AS completed_on_time,

                SUM(
                    CASE
                        WHEN work_order.scheduled_occurrence_date < CURDATE()
                             AND work_order.work_order_status NOT IN (
                                 'Closed',
                                 'Cancelled'
                             )
                        THEN 1
                        ELSE 0
                    END
                ) AS overdue_count

            FROM `tabFacility Work Order` work_order

            WHERE
                work_order.work_order_type = 'Preventive'
                AND work_order.scheduled_occurrence_date
                    BETWEEN %(from_date)s AND %(to_date)s
                AND work_order.scheduled_occurrence_date <= CURDATE()

            GROUP BY
                work_order.preventive_maintenance_plan
        ) stats
            ON stats.preventive_maintenance_plan = plan.name

        {condition_sql}

        ORDER BY
            plan.is_active DESC,
            plan.next_due_date ASC
        """,
        values,
        as_dict=True,
    )


def get_chart(filters):
    """Monthly compliance % trend, one line per category.

    Unlike get_data(), this is not a per-plan snapshot over the whole
    date range - it buckets by month so the chart shows a trend rather
    than a single bar per plan.
    """
    conditions = []
    values = {
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    if filters.get("company"):
        conditions.append("plan.company = %(company)s")
        values["company"] = filters.company

    if filters.get("is_active") == "Active":
        conditions.append("plan.is_active = 1")
    elif filters.get("is_active") == "Inactive":
        conditions.append("plan.is_active = 0")

    if filters.get("frequency") and filters.frequency != "All":
        conditions.append("plan.frequency = %(frequency)s")
        values["frequency"] = filters.frequency

    if filters.get("asset"):
        conditions.append("plan.asset = %(asset)s")
        values["asset"] = filters.asset

    condition_sql = ""
    if conditions:
        condition_sql = "AND " + " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            DATE_FORMAT(work_order.scheduled_occurrence_date, '%%Y-%%m')
                AS month,
            plan.category AS category,

            COUNT(*) AS scheduled_count,

            SUM(
                CASE
                    WHEN work_order.work_order_status = 'Closed'
                         AND COALESCE(
                             work_order.actual_end,
                             work_order.closed_on
                         ) <= COALESCE(
                             work_order.planned_end,
                             DATE_ADD(
                                 work_order.scheduled_occurrence_date,
                                 INTERVAL 1 DAY
                             )
                         )
                    THEN 1
                    ELSE 0
                END
            ) AS completed_on_time

        FROM `tabFacility Work Order` work_order

        INNER JOIN `tabPreventive Maintenance Plan` plan
            ON plan.name = work_order.preventive_maintenance_plan

        WHERE
            work_order.work_order_type = 'Preventive'
            AND plan.category IS NOT NULL
            AND work_order.scheduled_occurrence_date
                BETWEEN %(from_date)s AND %(to_date)s
            AND work_order.scheduled_occurrence_date <= CURDATE()
            {condition_sql}

        GROUP BY
            month,
            plan.category

        ORDER BY
            month
        """,
        values,
        as_dict=True,
    )

    if not rows:
        return {
            "data": {"labels": [], "datasets": []},
            "type": "line",
        }

    months = sorted({row.month for row in rows})
    categories = sorted({row.category for row in rows})
    by_month_category = {(row.month, row.category): row for row in rows}

    datasets = []
    for category in categories:
        series = []
        for month in months:
            row = by_month_category.get((month, category))
            if row and row.scheduled_count:
                series.append(
                    flt(row.completed_on_time / row.scheduled_count * 100, 2)
                )
            else:
                series.append(None)
        datasets.append({"name": category, "values": series})

    return {
        "data": {
            "labels": [get_month_label(month) for month in months],
            "datasets": datasets,
        },
        "type": "line",
        "lineOptions": {"regionFill": 0, "hideDots": 0, "dotSize": 4},
        "axisOptions": {"xIsSeries": 0},
    }


def get_month_label(year_month):
    year, month = year_month.split("-")
    return f"{calendar.month_abbr[int(month)]} {year}"
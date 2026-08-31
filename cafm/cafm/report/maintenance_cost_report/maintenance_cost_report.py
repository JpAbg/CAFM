# Copyright (c) 2026, Jean Paul Abou Gharib and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from cafm.permissions import work_order_query


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)

    return columns, data, None, chart, summary


def validate_filters(filters):
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required."))

    if not filters.get("company"):
        frappe.throw(_("Company is required."))

    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date."))


def get_columns():
    return [
        {
            "label": _("Work Order"),
            "fieldname": "work_order",
            "fieldtype": "Link",
            "options": "Facility Work Order",
            "width": 150,
        },
        {
            "label": _("Completed Date"),
            "fieldname": "completed_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Subject"),
            "fieldname": "subject",
            "fieldtype": "Data",
            "width": 210,
        },
        {
            "label": _("Type"),
            "fieldname": "work_order_type",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": _("Status"),
            "fieldname": "work_order_status",
            "fieldtype": "Data",
            "width": 90,
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
            "width": 130,
        },
        {
            "label": _("Facility Location"),
            "fieldname": "facility_location",
            "fieldtype": "Link",
            "options": "Facility Location",
            "width": 180,
        },
        {
            "label": _("Asset"),
            "fieldname": "asset",
            "fieldtype": "Link",
            "options": "Asset",
            "width": 150,
        },
        {
            "label": _("Category"),
            "fieldname": "category",
            "fieldtype": "Link",
            "options": "Issue Type",
            "width": 130,
        },
        {
            "label": _("Technician"),
            "fieldname": "technician",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 145,
        },
        {
            "label": _("Service Provider"),
            "fieldname": "vendor",
            "fieldtype": "Link",
            "options": "Facility Service Provider",
            "width": 155,
        },
        {
            "label": _("Labor Hours"),
            "fieldname": "labor_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 100,
        },
        {
            "label": _("Material Cost"),
            "fieldname": "material_cost",
            "fieldtype": "Currency",
            "width": 115,
        },
        {
            "label": _("Downtime Hours"),
            "fieldname": "downtime_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 115,
        },
    ]


def get_data(filters):
    conditions = [
        "work_order.company = %(company)s",
        """
        DATE(
            COALESCE(
                work_order.closed_on,
                work_order.actual_end,
                work_order.creation
            )
        ) BETWEEN %(from_date)s AND %(to_date)s
        """,
        """
        work_order.work_order_status IN (
            'Resolved',
            'Closed'
        )
        """,
    ]

    values = {
        "company": filters.company,
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    if (
        filters.get("work_order_type")
        and filters.work_order_type != "All"
    ):
        conditions.append(
            "work_order.work_order_type = %(work_order_type)s"
        )
        values["work_order_type"] = filters.work_order_type

    if filters.get("site"):
        conditions.append("location.site = %(site)s")
        values["site"] = filters.site

    if filters.get("building"):
        conditions.append("location.building = %(building)s")
        values["building"] = filters.building

    if filters.get("asset"):
        conditions.append("work_order.asset = %(asset)s")
        values["asset"] = filters.asset

    if filters.get("category"):
        conditions.append("work_order.category = %(category)s")
        values["category"] = filters.category

    permission_condition = work_order_query(table_alias="work_order")
    if permission_condition:
        conditions.append(permission_condition)

    condition_sql = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            work_order.name AS work_order,

            DATE(
                COALESCE(
                    work_order.closed_on,
                    work_order.actual_end,
                    work_order.creation
                )
            ) AS completed_date,

            work_order.subject,
            work_order.work_order_type,
            work_order.work_order_status,
            location.site,
            location.building,
            building.building_name,
            work_order.facility_location,
            work_order.asset,
            work_order.category,
            work_order.technician,
            work_order.vendor,

            COALESCE(labor.total_hours, 0)
                AS labor_hours,

            COALESCE(work_order.material_cost, 0)
                AS material_cost,

            CASE
                WHEN work_order.actual_start IS NOT NULL
                     AND work_order.actual_end IS NOT NULL
                THEN ROUND(
                    TIMESTAMPDIFF(
                        MINUTE,
                        work_order.actual_start,
                        work_order.actual_end
                    ) / 60,
                    2
                )
                ELSE 0
            END AS downtime_hours

        FROM `tabFacility Work Order` work_order

        LEFT JOIN `tabFacility Location` location
            ON location.name = work_order.facility_location

        LEFT JOIN `tabBuilding` building
            ON building.name = location.building

        LEFT JOIN (
            SELECT
                labor.parent,
                SUM(labor.hours) AS total_hours

            FROM `tabFacility Work Order Labor` labor

            WHERE
                labor.parenttype = 'Facility Work Order'

            GROUP BY
                labor.parent
        ) labor
            ON labor.parent = work_order.name

        WHERE {condition_sql}

        ORDER BY
            completed_date DESC,
            work_order.name DESC
        """,
        values,
        as_dict=True,
    )


def get_chart(data):
    """Maintenance cost split by Site, broken down by Building.

    Sites are the x-axis; full building names are legend datasets.
    Missing site/building combinations remain gaps, not zero-cost bars.
    """
    totals = {}

    for row in data:
        site = row.get("site") or _("Not Specified")
        building = (
            row.get("building_name") or row.get("building") or _("Not Specified")
        )
        key = (site, building)
        totals[key] = totals.get(key, 0) + flt(row.material_cost)

    if not totals:
        return {"data": {"labels": [], "datasets": []}, "type": "bar"}

    sites = sorted({site for site, _building in totals})
    buildings = sorted({building for _site, building in totals})

    datasets = []
    for building in buildings:
        values = [
            flt(totals[(site, building)], 2)
            if (site, building) in totals
            else None
            for site in sites
        ]
        datasets.append({"name": building, "values": values})

    return {
        "data": {
            "labels": sites,
            "datasets": datasets,
        },
        "type": "bar",
    }


def get_summary(data):
    total_material_cost = sum(
        flt(row.material_cost)
        for row in data
    )

    total_labor_hours = sum(
        flt(row.labor_hours)
        for row in data
    )

    total_downtime = sum(
        flt(row.downtime_hours)
        for row in data
    )

    average_cost = (
        total_material_cost / len(data)
        if data
        else 0
    )

    return [
        {
            "value": len(data),
            "label": _("Completed Work Orders"),
            "datatype": "Int",
            "indicator": "Blue",
        },
        {
            "value": flt(total_material_cost, 2),
            "label": _("Material Cost"),
            "datatype": "Currency",
            "indicator": "Green",
        },
        {
            "value": flt(average_cost, 2),
            "label": _("Average Cost per Work Order"),
            "datatype": "Currency",
            "indicator": "Blue",
        },
        {
            "value": flt(total_labor_hours, 2),
            "label": _("Labor Hours"),
            "datatype": "Float",
            "indicator": "Blue",
        },
        {
            "value": flt(total_downtime, 2),
            "label": _("Downtime Hours"),
            "datatype": "Float",
            "indicator": "Orange",
        },
    ]

# Copyright (c) 2026, Jean Paul Abou Gharib and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


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
            "label": _("Technician"),
            "fieldname": "technician",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150,
        },
        {
            "label": _("Technician Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 170,
        },
        {
            "label": _("Specialization"),
            "fieldname": "specialization",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Availability"),
            "fieldname": "availability",
            "fieldtype": "Data",
            "width": 105,
        },
        {
            "label": _("Assigned"),
            "fieldname": "assigned_count",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": _("Completed"),
            "fieldname": "completed_count",
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "label": _("Completion Rate"),
            "fieldname": "completion_rate",
            "fieldtype": "Percent",
            "width": 110,
        },
        {
            "label": _("Completed On Time"),
            "fieldname": "on_time_count",
            "fieldtype": "Int",
            "width": 125,
        },
        {
            "label": _("Overdue"),
            "fieldname": "overdue_count",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": _("Average Response Hours"),
            "fieldname": "average_response_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 145,
        },
        {
            "label": _("Average Resolution Hours"),
            "fieldname": "average_resolution_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "label": _("Labor Hours"),
            "fieldname": "labor_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 100,
        },
        {
            "label": _("Inspections Completed"),
            "fieldname": "inspections_completed",
            "fieldtype": "Int",
            "width": 135,
        },
        {
            "label": _("Inspections Passed"),
            "fieldname": "inspections_passed",
            "fieldtype": "Int",
            "width": 120,
        },
    ]


def get_data(filters):
    employee_conditions = [
        "employee.company = %(company)s",
        "employee.custom_is_facility_technician = 1",
    ]

    values = {
        "company": filters.company,
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    if filters.get("technician"):
        employee_conditions.append(
            "employee.name = %(technician)s"
        )
        values["technician"] = filters.technician

    if (
        filters.get("specialization")
        and filters.specialization != "All"
    ):
        employee_conditions.append(
            "employee.custom_primary_specialization = %(specialization)s"
        )
        values["specialization"] = filters.specialization

    if (
        filters.get("employee_status")
        and filters.employee_status != "All"
    ):
        employee_conditions.append(
            "employee.status = %(employee_status)s"
        )
        values["employee_status"] = filters.employee_status

    condition_sql = " AND ".join(employee_conditions)

    return frappe.db.sql(
        f"""
        SELECT
            employee.name AS technician,
            employee.employee_name,
            employee.custom_primary_specialization AS specialization,
            employee.custom_facility_availability AS availability,

            COALESCE(work.assigned_count, 0)
                AS assigned_count,

            COALESCE(work.completed_count, 0)
                AS completed_count,

            CASE
                WHEN COALESCE(work.assigned_count, 0) = 0
                THEN 0
                ELSE ROUND(
                    work.completed_count
                    / work.assigned_count
                    * 100,
                    2
                )
            END AS completion_rate,

            COALESCE(work.on_time_count, 0)
                AS on_time_count,

            COALESCE(work.overdue_count, 0)
                AS overdue_count,

            COALESCE(work.average_response_hours, 0)
                AS average_response_hours,

            COALESCE(work.average_resolution_hours, 0)
                AS average_resolution_hours,

            COALESCE(labor.total_labor_hours, 0)
                AS labor_hours,

            COALESCE(inspections.completed_count, 0)
                AS inspections_completed,

            COALESCE(inspections.passed_count, 0)
                AS inspections_passed

        FROM `tabEmployee` employee

        LEFT JOIN (
            SELECT
                work_order.technician,

                COUNT(*) AS assigned_count,

                SUM(
                    CASE
                        WHEN work_order.work_order_status IN (
                            'Resolved',
                            'Closed'
                        )
                        THEN 1
                        ELSE 0
                    END
                ) AS completed_count,

                SUM(
                    CASE
                        WHEN work_order.work_order_status IN (
                            'Resolved',
                            'Closed'
                        )
                        AND (
                            work_order.planned_end IS NULL
                            OR work_order.actual_end
                                <= work_order.planned_end
                        )
                        THEN 1
                        ELSE 0
                    END
                ) AS on_time_count,

                SUM(
                    CASE
                        WHEN work_order.planned_end IS NOT NULL
                        AND (
                            (
                                work_order.work_order_status IN (
                                    'Draft',
                                    'Assigned',
                                    'In Progress',
                                    'Pending'
                                )
                                AND work_order.planned_end < NOW()
                            )
                            OR
                            (
                                work_order.work_order_status IN (
                                    'Resolved',
                                    'Closed'
                                )
                                AND work_order.actual_end
                                    > work_order.planned_end
                            )
                        )
                        THEN 1
                        ELSE 0
                    END
                ) AS overdue_count,

                ROUND(
                    AVG(
                        CASE
                            WHEN work_order.actual_start IS NOT NULL
                            THEN TIMESTAMPDIFF(
                                MINUTE,
                                work_order.creation,
                                work_order.actual_start
                            ) / 60
                            ELSE NULL
                        END
                    ),
                    2
                ) AS average_response_hours,

                ROUND(
                    AVG(
                        CASE
                            WHEN work_order.actual_start IS NOT NULL
                            AND work_order.actual_end IS NOT NULL
                            THEN TIMESTAMPDIFF(
                                MINUTE,
                                work_order.actual_start,
                                work_order.actual_end
                            ) / 60
                            ELSE NULL
                        END
                    ),
                    2
                ) AS average_resolution_hours

            FROM `tabFacility Work Order` work_order

            WHERE
                work_order.assignment_type = 'Internal Technician'
                AND work_order.technician IS NOT NULL
                AND work_order.company = %(company)s
                AND DATE(work_order.creation)
                    BETWEEN %(from_date)s AND %(to_date)s

            GROUP BY
                work_order.technician
        ) work
            ON work.technician = employee.name

        LEFT JOIN (
            SELECT
                labor.employee,
                SUM(labor.hours) AS total_labor_hours

            FROM `tabFacility Work Order Labor` labor

            INNER JOIN `tabFacility Work Order` work_order
                ON work_order.name = labor.parent

            WHERE
                labor.parenttype = 'Facility Work Order'
                AND work_order.company = %(company)s
                AND DATE(work_order.creation)
                    BETWEEN %(from_date)s AND %(to_date)s

            GROUP BY
                labor.employee
        ) labor
            ON labor.employee = employee.name

        LEFT JOIN (
            SELECT
                inspection.inspector,

                SUM(
                    CASE
                        WHEN inspection.completed_on IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS completed_count,

                SUM(
                    CASE
                        WHEN inspection.completed_on IS NOT NULL
                        AND inspection.overall_result = 'Pass'
                        THEN 1
                        ELSE 0
                    END
                ) AS passed_count

            FROM `tabFacility Inspection` inspection

            WHERE
                inspection.company = %(company)s
                AND inspection.completed_on IS NOT NULL
                AND DATE(inspection.completed_on)
                    BETWEEN %(from_date)s AND %(to_date)s

            GROUP BY
                inspection.inspector
        ) inspections
            ON inspections.inspector = employee.name

        WHERE {condition_sql}

        ORDER BY
            completion_rate DESC,
            completed_count DESC,
            employee.employee_name ASC
        """,
        values,
        as_dict=True,
    )


def get_chart(data):
    return {
        "data": {
            "labels": [row.employee_name for row in data],
            "datasets": [
                {
                    "name": _("Completion Rate"),
                    "values": [
                        flt(row.completion_rate, 2)
                        for row in data
                    ],
                }
            ],
        },
        "type": "bar",
        "colors": ["#2490ef"],
    }


def get_summary(data):
    assigned = sum(row.assigned_count or 0 for row in data)
    completed = sum(row.completed_count or 0 for row in data)
    overdue = sum(row.overdue_count or 0 for row in data)
    labor_hours = sum(row.labor_hours or 0 for row in data)

    completion_rate = (
        flt(completed / assigned * 100, 2)
        if assigned
        else 0
    )

    return [
        {
            "value": len(data),
            "label": _("Technicians"),
            "datatype": "Int",
            "indicator": "Blue",
        },
        {
            "value": assigned,
            "label": _("Assigned Work Orders"),
            "datatype": "Int",
            "indicator": "Blue",
        },
        {
            "value": completion_rate,
            "label": _("Completion Rate"),
            "datatype": "Percent",
            "indicator": (
                "Green"
                if completion_rate >= 90
                else "Orange"
                if completion_rate >= 70
                else "Red"
            ),
        },
        {
            "value": overdue,
            "label": _("Overdue Work Orders"),
            "datatype": "Int",
            "indicator": "Red" if overdue else "Green",
        },
        {
            "value": flt(labor_hours, 2),
            "label": _("Labor Hours"),
            "datatype": "Float",
            "indicator": "Blue",
        },
    ]

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Work Order"), "fieldname": "work_order", "fieldtype": "Link", "options": "Facility Work Order", "width": 155},
        {"label": _("Subject"), "fieldname": "subject", "fieldtype": "Data", "width": 240},
        {"label": _("Priority"), "fieldname": "priority", "fieldtype": "Link", "options": "Issue Priority", "width": 110},
        {"label": _("Work Order Status"), "fieldname": "work_order_status", "fieldtype": "Data", "width": 125},
        {"label": _("SLA Status"), "fieldname": "sla_status", "fieldtype": "Data", "width": 145},
        {"label": _("SLA Policy"), "fieldname": "sla_policy", "fieldtype": "Link", "options": "Facility SLA Policy", "width": 180},
        {"label": _("Response Due"), "fieldname": "sla_response_due", "fieldtype": "Datetime", "width": 155},
        {"label": _("Response Achieved"), "fieldname": "sla_response_achieved_on", "fieldtype": "Datetime", "width": 165},
        {"label": _("Resolution Due"), "fieldname": "sla_resolution_due", "fieldtype": "Datetime", "width": 155},
        {"label": _("Resolution Achieved"), "fieldname": "sla_resolution_achieved_on", "fieldtype": "Datetime", "width": 170},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": _("Facility Location"), "fieldname": "facility_location", "fieldtype": "Link", "options": "Facility Location", "width": 180},
        {"label": _("Technician"), "fieldname": "technician", "fieldtype": "Link", "options": "Employee", "width": 165},
    ]


def get_data(filters):
    conditions = [
        "work_order.docstatus < 2",
        "COALESCE(work_order.sla_policy, '') != ''",
    ]
    values = {}

    for fieldname in ("company", "facility_location", "priority", "sla_policy"):
        if filters.get(fieldname):
            conditions.append(f"work_order.{fieldname} = %({fieldname})s")
            values[fieldname] = filters[fieldname]

    for fieldname in ("sla_status", "work_order_status"):
        if filters.get(fieldname) and filters[fieldname] != "All":
            conditions.append(f"work_order.{fieldname} = %({fieldname})s")
            values[fieldname] = filters[fieldname]

    if filters.get("from_date"):
        conditions.append("DATE(work_order.creation) >= %(from_date)s")
        values["from_date"] = filters.from_date
    if filters.get("to_date"):
        conditions.append("DATE(work_order.creation) <= %(to_date)s")
        values["to_date"] = filters.to_date

    return frappe.db.sql(
        f"""
        SELECT
            work_order.name AS work_order,
            work_order.subject,
            work_order.priority,
            work_order.work_order_status,
            work_order.sla_status,
            work_order.sla_policy,
            work_order.sla_response_due,
            work_order.sla_response_achieved_on,
            work_order.sla_resolution_due,
            work_order.sla_resolution_achieved_on,
            work_order.company,
            work_order.facility_location,
            work_order.technician
        FROM `tabFacility Work Order` work_order
        WHERE {" AND ".join(conditions)}
        ORDER BY
            FIELD(work_order.sla_status, 'Resolution Breached', 'Response Breached', 'On Track', 'Met', 'Not Applicable'),
            work_order.sla_resolution_due ASC,
            work_order.name ASC
        """,
        values,
        as_dict=True,
    )

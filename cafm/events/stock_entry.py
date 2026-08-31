import frappe
from frappe import _
from frappe.utils import flt

from cafm.materials import update_work_order_material_cost


def validate_facility_material_issue(doc, method=None):
    if not doc.get("custom_cafm_material_issue"):
        return

    if not doc.custom_facility_work_order:
        frappe.throw(_("Facility Work Order is required."))
    if doc.purpose != "Material Issue":
        frappe.throw(
            _("A CAFM material Stock Entry must use Material Issue purpose.")
        )

    work_order = frappe.get_doc(
        "Facility Work Order",
        doc.custom_facility_work_order,
    )
    if work_order.company != doc.company:
        frappe.throw(
            _("Stock Entry company must match the Facility Work Order.")
        )
    if work_order.work_order_status not in (
        "Assigned",
        "In Progress",
        "Pending",
        "Resolved",
    ):
        frappe.throw(
            _("This Work Order does not currently allow material issues.")
        )

    material_rows = {row.name: row for row in work_order.materials}
    linked_rows = []
    for item in doc.items:
        material_name = item.custom_facility_work_order_material
        if not material_name or material_name not in material_rows:
            frappe.throw(
                _("Every Stock Entry item must link to a Work Order Material row.")
            )
        if material_name in linked_rows:
            frappe.throw(
                _("A Work Order Material row cannot be issued twice in one entry.")
            )
        linked_rows.append(material_name)

        material = material_rows[material_name]
        if (
            item.item_code != material.item_code
            or item.s_warehouse != material.warehouse
            or flt(item.qty) != flt(material.quantity)
            or (item.batch_no or None) != (material.batch_no or None)
            or normalize_serials(item.serial_no)
            != normalize_serials(material.serial_no)
        ):
            frappe.throw(
                _(
                    "Stock Entry item {0} does not match its "
                    "Work Order Material row."
                ).format(item.idx)
            )
        if item.t_warehouse:
            frappe.throw(
                _("CAFM Material Issues cannot have a target Warehouse.")
            )

        duplicate = frappe.db.exists(
            "Stock Entry Detail",
            {
                "custom_facility_work_order_material": material_name,
                "docstatus": 1,
                "parent": ["!=", doc.name or ""],
            },
        )
        if duplicate:
            frappe.throw(
                _("This Work Order Material row has already been issued.")
            )


def normalize_serials(value):
    return tuple(
        serial.strip()
        for serial in (value or "").splitlines()
        if serial.strip()
    )


def prevent_closed_work_order_material_cancellation(doc, method=None):
    if not doc.get("custom_cafm_material_issue"):
        return
    status = frappe.db.get_value(
        "Facility Work Order",
        doc.custom_facility_work_order,
        "work_order_status",
    )
    if status == "Closed":
        frappe.throw(
            _(
                "Reopen the Facility Work Order before cancelling "
                "its Material Issue."
            )
        )


def sync_facility_material_issue(doc, method=None):
    if not doc.get("custom_cafm_material_issue"):
        return

    for item in doc.items:
        material_name = item.custom_facility_work_order_material
        if not material_name:
            continue
        frappe.db.set_value(
            "Facility Work Order Material",
            material_name,
            {
                "stock_entry": doc.name,
                "stock_entry_detail": item.name,
                "valuation_rate": flt(
                    item.basic_rate or item.valuation_rate
                ),
                "amount": flt(item.basic_amount or item.amount),
            },
            update_modified=False,
        )
    update_work_order_material_cost(doc.custom_facility_work_order)


def clear_facility_material_issue(doc, method=None):
    if not doc.get("custom_cafm_material_issue"):
        return

    rows = frappe.get_all(
        "Facility Work Order Material",
        filters={"stock_entry": doc.name},
        pluck="name",
    )
    for material_name in rows:
        frappe.db.set_value(
            "Facility Work Order Material",
            material_name,
            {
                "stock_entry": None,
                "stock_entry_detail": None,
                "valuation_rate": 0,
                "amount": 0,
            },
            update_modified=False,
        )
    update_work_order_material_cost(doc.custom_facility_work_order)

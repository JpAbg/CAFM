from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt


ISSUABLE_WORK_ORDER_STATUSES = (
    "Assigned",
    "In Progress",
    "Pending",
    "Resolved",
)
LOCKED_MATERIAL_FIELDS = (
    "item_code",
    "warehouse",
    "quantity",
    "batch_no",
    "serial_no",
)


def normalize_serial_numbers(value):
    return tuple(
        serial.strip()
        for serial in (value or "").splitlines()
        if serial.strip()
    )


def get_stock_entry_status(stock_entry):
    if not stock_entry:
        return None
    return frappe.db.get_value("Stock Entry", stock_entry, "docstatus")


def validate_work_order_materials(work_order):
    previous = work_order.get_doc_before_save()
    previous_rows = {
        row.name: row for row in (previous.materials if previous else [])
    }
    current_names = {row.name for row in work_order.materials}

    for old_row in previous_rows.values():
        if (
            old_row.name not in current_names
            and get_stock_entry_status(old_row.stock_entry) == 1
        ):
            frappe.throw(
                _(
                    "Issued Material row {0} cannot be removed. "
                    "Cancel its Stock Entry first."
                ).format(old_row.idx)
            )

    for row in work_order.materials:
        validate_material_row(work_order, row)

        if get_stock_entry_status(row.stock_entry) == 2:
            row.stock_entry = None
            row.stock_entry_detail = None
            row.valuation_rate = 0
            row.amount = 0

        if get_stock_entry_status(row.stock_entry) != 1:
            continue

        linked_work_order = frappe.db.get_value(
            "Stock Entry",
            row.stock_entry,
            "custom_facility_work_order",
        )
        if linked_work_order != work_order.name:
            frappe.throw(
                _("Material row {0} has an unrelated Stock Entry.").format(
                    row.idx
                )
            )

        previous_row = previous_rows.get(row.name)
        if previous_row and any(
            row.get(fieldname) != previous_row.get(fieldname)
            for fieldname in LOCKED_MATERIAL_FIELDS
        ):
            frappe.throw(
                _(
                    "Issued Material row {0} cannot be changed. "
                    "Cancel its Stock Entry first."
                ).format(row.idx)
            )

    work_order.material_cost = sum(
        flt(row.amount)
        for row in work_order.materials
        if get_stock_entry_status(row.stock_entry) == 1
    )

    if work_order.work_order_status == "Closed":
        pending = [
            str(row.idx)
            for row in work_order.materials
            if get_stock_entry_status(row.stock_entry) != 1
        ]
        if pending:
            frappe.throw(
                _(
                    "Issue or remove pending Material rows before closure: {0}"
                ).format(", ".join(pending))
            )


def validate_material_row(work_order, row):
    if not row.item_code:
        frappe.throw(_("Item is required on Material row {0}.").format(row.idx))
    if flt(row.quantity) <= 0:
        frappe.throw(
            _("Quantity must be greater than zero on Material row {0}.").format(
                row.idx
            )
        )
    if not row.warehouse:
        frappe.throw(
            _("Warehouse is required on Material row {0}.").format(row.idx)
        )

    item = frappe.db.get_value(
        "Item",
        row.item_code,
        [
            "disabled",
            "is_stock_item",
            "stock_uom",
            "has_batch_no",
            "has_serial_no",
        ],
        as_dict=True,
    )
    if not item or item.disabled or not item.is_stock_item:
        frappe.throw(
            _("Material Item {0} must be an active Stock Item.").format(
                row.item_code
            )
        )

    warehouse = frappe.db.get_value(
        "Warehouse",
        row.warehouse,
        ["company", "disabled", "is_group"],
        as_dict=True,
    )
    if (
        not warehouse
        or warehouse.disabled
        or warehouse.is_group
        or warehouse.company != work_order.company
    ):
        frappe.throw(
            _(
                "Warehouse {0} must be an active leaf Warehouse "
                "for company {1}."
            ).format(row.warehouse, work_order.company)
        )

    row.uom = item.stock_uom
    if item.has_batch_no and not row.batch_no:
        frappe.throw(
            _("Batch is required for Item {0}.").format(row.item_code)
        )
    if not item.has_batch_no and row.batch_no:
        frappe.throw(
            _("Item {0} is not batch-controlled.").format(row.item_code)
        )

    serial_numbers = normalize_serial_numbers(row.serial_no)
    if item.has_serial_no:
        if len(serial_numbers) != cint(row.quantity):
            frappe.throw(
                _(
                    "Enter one Serial Number per unit for Item {0}; "
                    "{1} required."
                ).format(row.item_code, cint(row.quantity))
            )
        if len(serial_numbers) != len(set(serial_numbers)):
            frappe.throw(
                _("Serial Numbers cannot contain duplicates.")
            )
    elif serial_numbers:
        frappe.throw(
            _("Item {0} is not serial-controlled.").format(row.item_code)
        )


def validate_available_stock(rows):
    required = defaultdict(float)
    for row in rows:
        required[(row.item_code, row.warehouse)] += flt(row.quantity)

    for (item_code, warehouse), quantity in required.items():
        actual_qty = flt(
            frappe.db.get_value(
                "Bin",
                {
                    "item_code": item_code,
                    "warehouse": warehouse,
                },
                "actual_qty",
            )
        )
        if actual_qty < quantity:
            frappe.throw(
                _(
                    "Insufficient stock for {0} in {1}. "
                    "Available: {2}, required: {3}."
                ).format(
                    item_code,
                    warehouse,
                    actual_qty,
                    quantity,
                )
            )


def update_work_order_material_cost(work_order_name):
    if not work_order_name or not frappe.db.exists(
        "Facility Work Order",
        work_order_name,
    ):
        return

    material_cost = frappe.db.sql(
        """
        SELECT COALESCE(SUM(material.amount), 0)
        FROM `tabFacility Work Order Material` material
        INNER JOIN `tabStock Entry` stock_entry
            ON stock_entry.name = material.stock_entry
           AND stock_entry.docstatus = 1
        WHERE material.parent = %(work_order)s
          AND material.parenttype = 'Facility Work Order'
          AND material.parentfield = 'materials'
        """,
        {"work_order": work_order_name},
    )[0][0]
    frappe.db.set_value(
        "Facility Work Order",
        work_order_name,
        "material_cost",
        flt(material_cost),
        update_modified=False,
    )


@frappe.whitelist()
def issue_materials(work_order_name):
    work_order = frappe.get_doc(
        "Facility Work Order",
        work_order_name,
    )
    work_order.check_permission("write")
    roles = set(frappe.get_roles())
    if "Vendor" in roles and not roles & {
        "System Manager",
        "Facility Manager",
        "Facility Coordinator",
    }:
        frappe.throw(
            _("External Vendors cannot issue internal warehouse stock."),
            frappe.PermissionError,
        )

    if work_order.work_order_status not in ISSUABLE_WORK_ORDER_STATUSES:
        frappe.throw(
            _(
                "Materials can only be issued for Assigned, In Progress, "
                "Pending or Resolved Work Orders."
            )
        )

    frappe.db.sql(
        """
        SELECT name
        FROM `tabFacility Work Order`
        WHERE name = %s
        FOR UPDATE
        """,
        work_order.name,
    )
    work_order.reload()
    validate_work_order_materials(work_order)

    pending_rows = [
        row
        for row in work_order.materials
        if get_stock_entry_status(row.stock_entry) != 1
    ]
    if not pending_rows:
        existing = [
            row.stock_entry
            for row in work_order.materials
            if get_stock_entry_status(row.stock_entry) == 1
        ]
        if existing:
            return existing[-1]
        frappe.throw(_("Add at least one Material row before issuing stock."))

    validate_available_stock(pending_rows)

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Issue"
    stock_entry.purpose = "Material Issue"
    stock_entry.company = work_order.company
    stock_entry.custom_facility_work_order = work_order.name
    stock_entry.custom_cafm_material_issue = 1
    stock_entry.remarks = _(
        "Materials consumed for Facility Work Order {0}: {1}"
    ).format(work_order.name, work_order.subject)

    for row in pending_rows:
        item = {
            "item_code": row.item_code,
            "s_warehouse": row.warehouse,
            "qty": row.quantity,
            "uom": row.uom,
            "stock_uom": row.uom,
            "conversion_factor": 1,
            "custom_facility_work_order_material": row.name,
        }
        if row.batch_no or row.serial_no:
            item.update(
                {
                    "use_serial_batch_fields": 1,
                    "batch_no": row.batch_no,
                    "serial_no": row.serial_no,
                }
            )
        stock_entry.append("items", item)

    stock_entry.flags.ignore_permissions = True
    stock_entry.insert(ignore_permissions=True)
    stock_entry.submit()
    return stock_entry.name

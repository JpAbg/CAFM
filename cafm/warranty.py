import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate


WARRANTY_EXPIRING_SOON_DAYS = 30
ACTIVE_WARRANTY_STATUSES = ("Active", "Expiring Soon")


def get_warranty_status(start_date, expiry_date, reference_date=None):
    reference_date = getdate(reference_date or nowdate())
    start_date = getdate(start_date) if start_date else None
    expiry_date = getdate(expiry_date) if expiry_date else None

    if not expiry_date:
        return "Not Covered"
    if start_date and reference_date < start_date:
        return "Pending"
    if reference_date > expiry_date:
        return "Expired"
    if expiry_date <= getdate(
        add_days(reference_date, WARRANTY_EXPIRING_SOON_DAYS)
    ):
        return "Expiring Soon"
    return "Active"


def update_asset_warranty_status(asset, reference_date=None):
    start_date = (
        getdate(asset.custom_warranty_start_date)
        if asset.custom_warranty_start_date
        else None
    )
    expiry_date = (
        getdate(asset.custom_warranty_expiry_date)
        if asset.custom_warranty_expiry_date
        else None
    )
    if start_date and expiry_date and expiry_date < start_date:
        frappe.throw(
            _("Warranty Expiry Date cannot be earlier than Warranty Start Date.")
        )

    asset.custom_warranty_status = get_warranty_status(
        start_date,
        expiry_date,
        reference_date,
    )
    return asset.custom_warranty_status


def validate_warranty_claim(work_order):
    if not work_order.warranty_claim:
        return

    if not work_order.asset:
        frappe.throw(_("An Asset is required for a warranty claim."))

    warranty = frappe.db.get_value(
        "Asset",
        work_order.asset,
        [
            "custom_warranty_start_date",
            "custom_warranty_expiry_date",
        ],
        as_dict=True,
    )
    if not warranty:
        frappe.throw(_("The selected Asset has no warranty information."))

    reference_date = (
        getdate(work_order.actual_start)
        if work_order.actual_start
        else getdate(work_order.planned_start or work_order.creation or nowdate())
    )
    status = get_warranty_status(
        warranty.custom_warranty_start_date,
        warranty.custom_warranty_expiry_date,
        reference_date,
    )
    if status not in ACTIVE_WARRANTY_STATUSES:
        frappe.throw(
            _(
                "A warranty claim cannot be recorded because the Asset warranty "
                "was {0} on {1}."
            ).format(status, reference_date)
        )

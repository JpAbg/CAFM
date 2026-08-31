import hashlib

import frappe
from frappe import _


CAFM_LOCATION_ROOT = "CAFM Locations"
LOCATION_NAME_LENGTH = 140


def ensure_location_root():
    if frappe.db.exists("Location", CAFM_LOCATION_ROOT):
        if not frappe.db.get_value(
            "Location", CAFM_LOCATION_ROOT, "is_group"
        ):
            frappe.throw(
                _(
                    "The ERPNext Location named {0} must be a group."
                ).format(CAFM_LOCATION_ROOT)
            )
        return CAFM_LOCATION_ROOT

    root = frappe.get_doc(
        {
            "doctype": "Location",
            "location_name": CAFM_LOCATION_ROOT,
            "is_group": 1,
        }
    )
    root.insert(ignore_permissions=True)
    return root.name


def _location_name(facility_location, title):
    prefix = "CAFM - "
    label = title or facility_location
    candidate = f"{prefix}{label}"
    if len(candidate) <= LOCATION_NAME_LENGTH:
        return candidate

    digest = hashlib.sha1(
        facility_location.encode("utf-8")
    ).hexdigest()[:12]
    available = LOCATION_NAME_LENGTH - len(prefix) - len(digest) - 3
    return f"{prefix}{label[:available]} - {digest}"


def ensure_erpnext_location(facility_location):
    details = frappe.db.get_value(
        "Facility Location",
        facility_location,
        ["title", "erpnext_location"],
        as_dict=True,
    )
    if not details:
        frappe.throw(
            _("Facility Location {0} does not exist.").format(
                facility_location
            )
        )

    if details.erpnext_location and frappe.db.exists(
        "Location", details.erpnext_location
    ):
        return details.erpnext_location

    parent = ensure_location_root()
    location_name = _location_name(facility_location, details.title)
    existing = frappe.db.get_value(
        "Location",
        location_name,
        ["name", "parent_location", "is_group"],
        as_dict=True,
    )
    if existing and (
        existing.parent_location != parent or existing.is_group
    ):
        digest = hashlib.sha1(
            facility_location.encode("utf-8")
        ).hexdigest()[:12]
        location_name = _location_name(
            facility_location,
            f"{details.title} - {digest}",
        )
        existing = frappe.db.get_value(
            "Location",
            location_name,
            ["name", "parent_location", "is_group"],
            as_dict=True,
        )

    if existing:
        erpnext_location = existing.name
    else:
        erpnext_location = frappe.get_doc(
            {
                "doctype": "Location",
                "location_name": location_name,
                "parent_location": parent,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True).name

    frappe.db.set_value(
        "Facility Location",
        facility_location,
        "erpnext_location",
        erpnext_location,
        update_modified=False,
    )
    return erpnext_location


def sync_asset_location(asset):
    if not asset.custom_asset_location:
        frappe.throw(_("Facility Location is required."))
    asset.location = ensure_erpnext_location(
        asset.custom_asset_location
    )


def backfill_asset_locations():
    for facility_location in frappe.get_all(
        "Facility Location", pluck="name"
    ):
        ensure_erpnext_location(facility_location)

    updated = 0
    assets = frappe.get_all(
        "Asset",
        filters={"custom_asset_location": ["is", "set"]},
        fields=["name", "custom_asset_location", "location"],
    )
    for asset in assets:
        location = ensure_erpnext_location(asset.custom_asset_location)
        if asset.location == location:
            continue
        frappe.db.set_value(
            "Asset",
            asset.name,
            "location",
            location,
            update_modified=False,
        )
        updated += 1
    return updated

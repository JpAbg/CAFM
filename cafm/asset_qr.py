"""QR codes that open CAFM Asset records for signed-in staff."""

from io import BytesIO
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import get_url


def get_asset_qr_url(asset_name):
    """Return the Desk URL encoded in an asset QR code.

    Asset permissions still apply after the user signs in, so the QR code
    never grants access by itself.
    """
    route = f"/app/asset/{quote(asset_name, safe='')}"
    return f"{get_url().rstrip('/')}{route}"


def generate_asset_qr_code(asset, force=False):
    """Attach a durable QR SVG to an Asset and return its file URL."""
    if not asset or not asset.name:
        return None

    current_file = getattr(asset, "custom_asset_qr_code", None)
    if current_file and not force:
        return current_file

    from pyqrcode import create as create_qr_code

    output = BytesIO()
    try:
        create_qr_code(get_asset_qr_url(asset.name), error="M").svg(
            output,
            scale=5,
            quiet_zone=4,
            background="#ffffff",
            module_color="#172b4d",
        )
        content = output.getvalue()
    finally:
        output.close()

    existing_file = frappe.db.get_value(
        "File",
        {
            "attached_to_doctype": "Asset",
            "attached_to_name": asset.name,
            "attached_to_field": "custom_asset_qr_code",
        },
        "name",
    )
    if existing_file:
        frappe.delete_doc("File", existing_file, ignore_permissions=True)

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": f"{asset.name}-cafm-qr.svg",
            "content": content,
            "is_private": 1,
            "attached_to_doctype": "Asset",
            "attached_to_name": asset.name,
            "attached_to_field": "custom_asset_qr_code",
        }
    ).insert(ignore_permissions=True)
    frappe.db.set_value(
        "Asset",
        asset.name,
        "custom_asset_qr_code",
        file_doc.file_url,
        update_modified=False,
    )
    asset.custom_asset_qr_code = file_doc.file_url
    return file_doc.file_url


def backfill_asset_qr_codes():
    """Give existing assets a QR code during installation or migration."""
    for asset_name in frappe.get_all("Asset", pluck="name"):
        asset = frappe.get_doc("Asset", asset_name)
        if not getattr(asset, "custom_asset_qr_code", None):
            generate_asset_qr_code(asset)


@frappe.whitelist()
def regenerate_asset_qr_code(asset_name):
    """Create a fresh QR image for users allowed to update that asset."""
    if not frappe.has_permission("Asset", "write", asset_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return generate_asset_qr_code(frappe.get_doc("Asset", asset_name), force=True)

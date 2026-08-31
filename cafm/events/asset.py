from cafm.asset_qr import generate_asset_qr_code
from cafm.location_sync import sync_asset_location
from cafm.warranty import update_asset_warranty_status


def validate_cafm_asset(doc, method=None):
    sync_asset_location(doc)
    update_asset_warranty_status(doc)


def create_asset_qr_code(doc, method=None):
    generate_asset_qr_code(doc)

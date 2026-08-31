from cafm.location_sync import sync_asset_location


def validate_cafm_asset(doc, method=None):
    sync_asset_location(doc)

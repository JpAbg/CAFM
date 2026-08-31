# Copyright (c) 2026, Jean Paul Abou Gharib and Contributors
# See license.txt

import frappe
from cafm.tests.factories import ensure_test_company
from frappe.tests.utils import FrappeTestCase

test_ignore = [
    "Building",
    "Floor",
    "Location",
    "Room",
    "Site",
]


class TestFacilityLocation(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        ensure_test_company(self)

    def test_rejects_mismatched_site_building_hierarchy(self):
        suffix = frappe.generate_hash(length=6)

        site_one = self.make_site(self.company, f"One {suffix}", f"S1-{suffix}")
        site_two = self.make_site(self.company, f"Two {suffix}", f"S2-{suffix}")
        building = frappe.get_doc(
            {
                "doctype": "Building",
                "site": site_two.name,
                "building_name": f"Building {suffix}",
                "building_id": f"B-{suffix}",
                "building_type": "Office",
            }
        ).insert(ignore_permissions=True)
        floor = frappe.get_doc(
            {
                "doctype": "Floor",
                "building": building.name,
                "floor_name": "Ground",
                "floor_level": 0,
                "floor_type": "Office",
            }
        ).insert(ignore_permissions=True)
        room = frappe.get_doc(
            {
                "doctype": "Room",
                "floor": floor.name,
                "room_name": f"Room {suffix}",
                "room_id": f"R-{suffix}",
                "room_type": "Workspace",
            }
        ).insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Facility Location",
                    "site": site_one.name,
                    "building": building.name,
                    "floor": floor.name,
                    "room": room.name,
                }
            ).insert(ignore_permissions=True)

    def test_maps_to_hidden_erpnext_location(self):
        suffix = frappe.generate_hash(length=6)
        site = self.make_site(
            self.company,
            f"Mapped {suffix}",
            f"MAP-{suffix}",
        )
        building = frappe.get_doc(
            {
                "doctype": "Building",
                "site": site.name,
                "building_name": f"Mapped Building {suffix}",
                "building_id": f"MB-{suffix}",
                "building_type": "Office",
            }
        ).insert(ignore_permissions=True)
        floor = frappe.get_doc(
            {
                "doctype": "Floor",
                "building": building.name,
                "floor_name": "Mapped Floor",
                "floor_level": 1,
                "floor_type": "Office",
            }
        ).insert(ignore_permissions=True)
        room = frappe.get_doc(
            {
                "doctype": "Room",
                "floor": floor.name,
                "room_name": f"Mapped Room {suffix}",
                "room_id": f"MR-{suffix}",
                "room_type": "Workspace",
            }
        ).insert(ignore_permissions=True)
        facility_location = frappe.get_doc(
            {
                "doctype": "Facility Location",
                "site": site.name,
                "building": building.name,
                "floor": floor.name,
                "room": room.name,
            }
        ).insert(ignore_permissions=True)
        facility_location.reload()

        self.assertTrue(facility_location.erpnext_location)
        self.assertEqual(
            frappe.db.get_value(
                "Location",
                facility_location.erpnext_location,
                "parent_location",
            ),
            "CAFM Locations",
        )
        asset_meta = frappe.get_meta("Asset")
        self.assertTrue(asset_meta.get_field("location").hidden)
        self.assertEqual(
            asset_meta.get_field("custom_asset_location").label,
            "Facility Location",
        )

    def make_site(self, company, label, site_id):
        return frappe.get_doc(
            {
                "doctype": "Site",
                "company": company,
                "site_name": f"CAFM Test Site {label}",
                "site_id": site_id,
                "site_type": "HQ",
                "address": "Test address",
            }
        ).insert(ignore_permissions=True)

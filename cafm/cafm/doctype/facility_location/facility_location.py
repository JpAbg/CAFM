import frappe
from frappe import _
from frappe.model.document import Document


class FacilityLocation(Document):
    def autoname(self):
        self.set_title()
        self.name = self.title

    def validate(self):
        self.validate_hierarchy()
        self.set_title()

    def after_insert(self):
        from cafm.location_sync import ensure_erpnext_location

        ensure_erpnext_location(self.name)

    def validate_hierarchy(self):
        if frappe.db.get_value("Building", self.building, "site") != self.site:
            frappe.throw(_("The selected Building does not belong to this Site."))
        if frappe.db.get_value("Floor", self.floor, "building") != self.building:
            frappe.throw(_("The selected Floor does not belong to this Building."))
        if frappe.db.get_value("Room", self.room, "floor") != self.floor:
            frappe.throw(_("The selected Room does not belong to this Floor."))

    def set_title(self):
        site_name = frappe.db.get_value("Site", self.site, "site_name") or self.site
        building_name = frappe.db.get_value("Building", self.building, "building_name") or self.building
        floor_name = frappe.db.get_value("Floor", self.floor, "floor_name") or self.floor
        room_name = frappe.db.get_value("Room", self.room, "room_name") or self.room
        self.title = f"{site_name} - {building_name} - {floor_name} - {room_name}"

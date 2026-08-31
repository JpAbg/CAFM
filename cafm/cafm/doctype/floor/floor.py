import frappe
from frappe import _
from frappe.model.document import Document


class Floor(Document):
    def validate(self):
        if frappe.db.exists("Floor", {"building": self.building, "floor_level": self.floor_level, "name": ["!=", self.name or ""]}):
            frappe.throw(_("Floor level {0} already exists in Building {1}.").format(self.floor_level, self.building))

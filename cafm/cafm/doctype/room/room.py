import frappe
from frappe import _
from frappe.model.document import Document


class Room(Document):
    def validate(self):
        if frappe.db.exists("Room", {"floor": self.floor, "room_id": self.room_id, "name": ["!=", self.name or ""]}):
            frappe.throw(_("Room ID {0} already exists on Floor {1}.").format(self.room_id, self.floor))

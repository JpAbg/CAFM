import frappe
from frappe import _
from frappe.model.document import Document


class Building(Document):
    def validate(self):
        if self.total_floors is not None and self.total_floors < 0:
            frappe.throw(_("Total Floors cannot be negative."))

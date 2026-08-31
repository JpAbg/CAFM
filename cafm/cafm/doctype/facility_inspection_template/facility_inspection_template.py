import frappe
from frappe import _
from frappe.model.document import Document


class FacilityInspectionTemplate(Document):
    def validate(self):
        self.validate_items()

    def validate_items(self):
        if not self.items:
            frappe.throw(_("Add at least one Inspection Item."))

        points = [row.inspection_point.strip() for row in self.items]
        if len(points) != len(set(points)):
            frappe.throw(_("Inspection Points cannot contain duplicates."))

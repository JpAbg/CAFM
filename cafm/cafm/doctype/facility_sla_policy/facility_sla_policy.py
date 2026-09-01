import frappe
from frappe import _
from frappe.model.document import Document


class FacilitySLAPolicy(Document):
    def validate(self):
        if self.resolution_target_hours < self.response_target_hours:
            frappe.throw(
                _("Resolution target must be equal to or greater than the response target.")
            )

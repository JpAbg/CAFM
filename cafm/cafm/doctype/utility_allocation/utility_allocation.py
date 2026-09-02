import frappe
from frappe.model.document import Document
from frappe.utils import flt


class UtilityAllocation(Document):
    def validate(self):
        meter = frappe.get_doc("Utility Meter", self.utility_meter)
        self.company = meter.company
        self.site = meter.site
        self.allocated_cost = flt(self.total_cost) * flt(self.allocation_percent) / 100

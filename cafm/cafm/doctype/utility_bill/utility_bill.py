import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate


class UtilityBill(Document):
    def validate(self):
        self.set_meter_details()
        self.set_reading_comparison()

    def set_meter_details(self):
        meter = frappe.get_doc("Utility Meter", self.utility_meter)
        self.company = meter.company
        self.site = meter.site
        self.utility_type = meter.utility_type
        self.unit_of_measure = meter.unit_of_measure
        self.currency = meter.currency
        self.supplier = meter.supplier

    def set_reading_comparison(self):
        reading = frappe.qb.DocType("Utility Reading")
        result = (frappe.qb.from_(reading).select(Sum(reading.consumption).as_("usage"), Sum(reading.cost).as_("cost")).where(reading.utility_meter == self.utility_meter).where(reading.reading_date >= getdate(self.period_start)).where(reading.reading_date <= getdate(self.period_end))).run(as_dict=True)
        self.recorded_usage = flt(result[0].usage) if result else 0
        self.recorded_cost = flt(result[0].cost) if result else 0
        self.usage_variance = flt(self.billed_usage) - flt(self.recorded_usage)
        self.cost_variance = flt(self.billed_amount) - flt(self.recorded_cost)
        self.match_status = "Matched" if abs(flt(self.usage_variance)) < 0.01 and abs(flt(self.cost_variance)) < 0.01 else "Variance Found"

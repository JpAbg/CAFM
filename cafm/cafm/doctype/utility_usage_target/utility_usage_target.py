import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate


class UtilityUsageTarget(Document):
    def validate(self):
        start = getdate(self.target_month).replace(day=1)
        end = start.replace(year=start.year + 1, month=1, day=1) if start.month == 12 else start.replace(month=start.month + 1, day=1)
        reading = frappe.qb.DocType("Utility Reading")
        meter = frappe.qb.DocType("Utility Meter")
        result = (frappe.qb.from_(reading).join(meter).on(meter.name == reading.utility_meter).select(Sum(reading.consumption).as_("actual")).where(reading.company == self.company).where(meter.site == self.site).where(reading.utility_type == self.utility_type).where(reading.reading_date >= start).where(reading.reading_date < end)).run(as_dict=True)
        self.actual_usage = flt(result[0].actual) if result else 0
        self.usage_variance = flt(self.actual_usage) - flt(self.target_usage)
        self.target_status = "Over Target" if self.usage_variance > 0 else "Within Target"

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate


class UtilityBudget(Document):
    def validate(self):
        self.set_actuals()

    def set_actuals(self):
        month_start = getdate(self.budget_month).replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)
        reading = frappe.qb.DocType("Utility Reading")
        meter = frappe.qb.DocType("Utility Meter")
        result = (
            frappe.qb.from_(reading)
            .join(meter).on(meter.name == reading.utility_meter)
            .select(Sum(reading.cost).as_("actual_cost"))
            .where(reading.company == self.company)
            .where(meter.site == self.site)
            .where(reading.utility_type == self.utility_type)
            .where(reading.reading_date >= month_start)
            .where(reading.reading_date < month_end)
        ).run(as_dict=True)
        self.actual_cost = flt(result[0].actual_cost) if result else 0
        self.variance = flt(self.actual_cost) - flt(self.budget_amount)
        self.budget_status = "Over Budget" if self.variance > 0 else "On Budget"

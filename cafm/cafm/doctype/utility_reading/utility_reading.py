import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class UtilityReading(Document):
    def validate(self):
        self.set_meter_details()
        self.set_consumption_and_cost()

    def set_meter_details(self):
        meter = frappe.get_doc("Utility Meter", self.utility_meter)
        if not meter.is_active:
            frappe.throw(_("Cannot record a reading for an inactive utility meter."))
        self.company = meter.company
        self.utility_type = meter.utility_type
        self.unit_of_measure = meter.unit_of_measure
        self.currency = meter.currency
        if self.unit_rate is None:
            self.unit_rate = meter.default_rate

    def set_consumption_and_cost(self):
        previous = get_previous_reading(self.utility_meter, self.reading_date, self.name)
        self.is_opening_reading = 0 if previous else 1
        self.previous_reading = previous.reading_value if previous else None
        self.consumption = flt(self.reading_value) - flt(self.previous_reading) if previous else 0
        if self.consumption < 0:
            frappe.throw(_("Reading value cannot be lower than the previous reading ({0}).").format(self.previous_reading))
        self.cost = flt(self.consumption) * flt(self.unit_rate)


def get_previous_reading(utility_meter, reading_date, name=None):
    filters = {"utility_meter": utility_meter, "reading_date": ["<=", getdate(reading_date)]}
    if name:
        filters["name"] = ["!=", name]
    readings = frappe.get_all("Utility Reading", filters=filters, fields=["name","reading_date","reading_value","creation"], order_by="reading_date desc, creation desc", limit_page_length=20)
    for reading in readings:
        if getdate(reading.reading_date) < getdate(reading_date):
            return reading
        if name and reading.name != name:
            return reading
    return None

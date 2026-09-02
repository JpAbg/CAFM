import frappe
from frappe.utils import add_to_date, now_datetime

UTILITY_TYPES = ("Electricity", "Water", "Natural Gas", "Fuel", "Other")


@frappe.whitelist()
def get(**kwargs):
    current_month = now_datetime().date().replace(day=1)
    starts = [add_to_date(current_month, months=offset) for offset in range(-5, 1)]
    labels = [month.strftime("%b %Y") for month in starts]
    rows = frappe.get_all("Utility Reading", filters={"reading_date": ["between", [str(starts[0]), str(add_to_date(current_month, months=1, days=-1))]]}, fields=["reading_date", "utility_type", "cost"])
    grouped = {utility_type: [0] * len(starts) for utility_type in UTILITY_TYPES}
    month_index = {(month.year, month.month): index for index, month in enumerate(starts)}
    for row in rows:
        utility_type = row.utility_type if row.utility_type in grouped else "Other"
        index = month_index.get((row.reading_date.year, row.reading_date.month))
        if index is not None:
            grouped[utility_type][index] += row.cost or 0
    datasets = [{"name": utility_type, "values": [round(value, 2) for value in values]} for utility_type, values in grouped.items() if any(values)]
    return {"labels": labels, "datasets": datasets}

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": _("Date"), "fieldname": "reading_date", "fieldtype": "Date", "width": 100},
        {"label": _("Meter"), "fieldname": "utility_meter", "fieldtype": "Link", "options": "Utility Meter", "width": 190},
        {"label": _("Utility"), "fieldname": "utility_type", "width": 110},
        {"label": _("Site"), "fieldname": "site", "fieldtype": "Link", "options": "Site", "width": 150},
        {"label": _("Building"), "fieldname": "building", "fieldtype": "Link", "options": "Building", "width": 150},
        {"label": _("Usage"), "fieldname": "consumption", "fieldtype": "Float", "width": 105},
        {"label": _("Unit"), "fieldname": "unit_of_measure", "width": 80},
        {"label": _("Estimated Cost"), "fieldname": "cost", "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": _("Currency"), "fieldname": "currency", "width": 80},
    ]
    data = get_readings(filters, filters.get("from_date"), filters.get("to_date"))
    current_usage = sum(flt(row.consumption) for row in data)
    current_cost = sum(flt(row.cost) for row in data)
    meter_count = len({row.utility_meter for row in data})

    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    period_days = date_diff(to_date, from_date) + 1
    prior_to_date = add_days(from_date, -1)
    prior_from_date = add_days(prior_to_date, -(period_days - 1))
    prior_data = get_readings(filters, prior_from_date, prior_to_date)
    prior_usage = sum(flt(row.consumption) for row in prior_data)

    if prior_usage:
        usage_change = ((current_usage - prior_usage) / prior_usage) * 100
        usage_change_value = "{0}{1:.1f}%".format("+" if usage_change > 0 else "", usage_change)
        usage_change_indicator = "Red" if usage_change > 0 else "Green" if usage_change < 0 else "Blue"
    else:
        usage_change_value = "No prior data"
        usage_change_indicator = "Blue"

    summary = [
        {"label": _("Meters Reported"), "value": meter_count, "indicator": "Blue"},
        {"label": _("Usage Change"), "value": usage_change_value, "indicator": usage_change_indicator},
        {"label": _("Estimated Cost"), "value": current_cost, "indicator": "Orange", "currency": data[0].currency if data else None},
    ]
    return columns, data, None, None, summary


def get_readings(filters, from_date, to_date):
    conditions = ["r.reading_date between %(from_date)s and %(to_date)s"]
    values = {"from_date": from_date, "to_date": to_date}
    for key, field in (("company", "r.company"), ("utility_meter", "r.utility_meter"), ("site", "m.site"), ("building", "m.building")):
        if filters.get(key):
            conditions.append(field + " = %(" + key + ")s")
            values[key] = filters[key]
    if filters.get("utility_type") and filters.get("utility_type") != "All":
        conditions.append("r.utility_type = %(utility_type)s")
        values["utility_type"] = filters["utility_type"]
    return frappe.db.sql(
        "select r.reading_date, r.utility_meter, r.utility_type, m.site, m.building, r.consumption, r.unit_of_measure, r.cost, r.currency "
        "from `tabUtility Reading` r inner join `tabUtility Meter` m on m.name = r.utility_meter "
        "where " + " and ".join(conditions) + " order by r.reading_date desc, r.creation desc",
        values,
        as_dict=True,
    )

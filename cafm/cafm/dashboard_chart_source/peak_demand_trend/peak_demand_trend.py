import frappe

UTILITY_TYPES = ("Electricity", "Water", "Natural Gas", "Fuel", "Other")
UNITS = {"Electricity": "kW", "Water": "m3/h", "Natural Gas": "GJ/h", "Fuel": "Litres/h", "Other": "units/h"}


def get_selected_utility(filters):
    filters = frappe.parse_json(filters) or {}
    selected = filters.get("utility_type") or "All"
    return selected if selected in UTILITY_TYPES else "All"


@frappe.whitelist()
def get(filters=None, **kwargs):
    selected = get_selected_utility(filters)
    latest_date = frappe.db.sql(
        "SELECT MAX(DATE(reading_datetime)) AS reading_date FROM `tabUtility Demand Reading`",
        as_dict=True,
    )[0].reading_date
    if not latest_date:
        return {"labels": [], "datasets": []}

    rows = frappe.db.sql(
        """
        SELECT demand.reading_datetime, demand.demand_value, demand.demand_unit,
               meter.utility_type
        FROM `tabUtility Demand Reading` AS demand
        INNER JOIN `tabUtility Meter` AS meter ON meter.name = demand.utility_meter
        WHERE DATE(demand.reading_datetime) = %s
        ORDER BY demand.reading_datetime ASC
        """,
        latest_date,
        as_dict=True,
    )
    grouped = {utility_type: [0] * 24 for utility_type in UTILITY_TYPES}
    units = dict(UNITS)
    for row in rows:
        utility_type = row.utility_type if row.utility_type in grouped else "Other"
        if selected != "All" and utility_type != selected:
            continue
        hour = row.reading_datetime.hour
        grouped[utility_type][hour] = max(grouped[utility_type][hour], row.demand_value or 0)
        units[utility_type] = row.demand_unit or units[utility_type]

    datasets = [
        {"name": "{} peak rate ({})".format(utility_type, units[utility_type]), "values": values}
        for utility_type, values in grouped.items()
        if any(values)
    ]
    labels = ["{0:02d}:00".format(hour) if hour % 3 == 0 else "" for hour in range(24)]
    return {"labels": labels, "datasets": datasets}

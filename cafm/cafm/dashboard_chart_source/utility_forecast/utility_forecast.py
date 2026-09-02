from cafm.utilities import get_utility_forecast
import frappe

UTILITY_TYPES = ("Electricity", "Water", "Natural Gas", "Fuel", "Other")
PROFILE = [0.45, 0.4, 0.38, 0.36, 0.35, 0.4, 0.6, 0.85, 1.05, 1.0, 0.95, 0.9, 0.95, 1.0, 1.15, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.55, 0.5]


def get_selected_utility(filters):
    filters = frappe.parse_json(filters) or {}
    selected = filters.get("utility_type") or "All"
    return selected if selected in UTILITY_TYPES else "All"


@frappe.whitelist()
def get(filters=None, **kwargs):
    selected = get_selected_utility(filters)
    meters = frappe.get_all("Utility Meter", filters={"is_active": 1}, fields=["name", "utility_type", "unit_of_measure"])
    totals = {utility_type: {"usage": 0, "unit": None} for utility_type in UTILITY_TYPES}
    for meter in meters:
        utility_type = meter.utility_type if meter.utility_type in totals else "Other"
        if selected != "All" and utility_type != selected:
            continue
        forecast = get_utility_forecast(meter.name)
        if forecast["basis_readings"]:
            totals[utility_type]["usage"] += forecast["forecast_usage"]
            totals[utility_type]["unit"] = meter.unit_of_measure

    profile_total = sum(PROFILE)
    datasets = []
    for utility_type in UTILITY_TYPES:
        total = totals[utility_type]
        if total["usage"]:
            daily_usage = total["usage"] / 30
            datasets.append({"name": "{} forecast ({})".format(utility_type, total["unit"] or "units"), "values": [round(daily_usage * point / profile_total, 2) for point in PROFILE]})
    labels = ["{0:02d}:00".format(hour) if hour % 3 == 0 else "" for hour in range(24)]
    return {"labels": labels, "datasets": datasets}

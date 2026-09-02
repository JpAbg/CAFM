import frappe
from frappe.utils import flt


EMISSION_FACTORS = {"Electricity": 0.45, "Water": 0.0003, "Natural Gas": 2.0, "Fuel": 2.68}


def apply_carbon_emissions(doc, method=None):
    doc.carbon_emissions = flt(doc.consumption) * EMISSION_FACTORS.get(doc.utility_type, 0)


@frappe.whitelist()
def get_usage_anomalies():
    rows = frappe.get_all("Utility Reading", fields=["name","utility_meter","reading_date","consumption"], order_by="reading_date asc")
    by_meter = {}
    anomalies = []
    for row in rows:
        history = by_meter.setdefault(row.utility_meter, [])
        baseline = sum(history[-3:]) / len(history[-3:]) if history else 0
        if baseline and flt(row.consumption) > baseline * 1.5:
            anomalies.append({"reading":row.name,"meter":row.utility_meter,"date":str(row.reading_date),"consumption":row.consumption,"baseline":baseline})
        history.append(flt(row.consumption))
    return anomalies


@frappe.whitelist()
def get_utility_forecast(utility_meter=None):
    filters = {"utility_meter": utility_meter} if utility_meter else {}
    rows = frappe.get_all("Utility Reading", filters=filters, fields=["consumption","cost"], order_by="reading_date desc", limit_page_length=3)
    if not rows:
        return {"forecast_usage": 0, "forecast_cost": 0, "basis_readings": 0}
    return {"forecast_usage": round(sum(flt(r.consumption) for r in rows) / len(rows), 2), "forecast_cost": round(sum(flt(r.cost) for r in rows) / len(rows), 2), "basis_readings": len(rows)}


@frappe.whitelist()
def get_weather_normalized_usage(site, from_date, to_date):
    observations = frappe.get_all("Utility Weather Observation", filters={"site": site, "observation_date": ["between", [from_date, to_date]]}, fields=["cooling_degree_days","heating_degree_days"])
    weather_load = sum(flt(x.cooling_degree_days) + flt(x.heating_degree_days) for x in observations)
    meters = frappe.get_all("Utility Meter", filters={"site": site}, pluck="name")
    usage = sum(flt(x.consumption) for x in frappe.get_all("Utility Reading", filters={"utility_meter": ["in", meters], "reading_date": ["between", [from_date, to_date]]}, fields=["consumption"])) if meters else 0
    return {"usage": usage, "degree_days": weather_load, "usage_per_degree_day": round(usage / weather_load, 2) if weather_load else None}

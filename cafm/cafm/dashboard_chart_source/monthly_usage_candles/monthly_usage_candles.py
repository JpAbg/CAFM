import frappe
from frappe import _
from frappe.utils import cint,flt,formatdate
@frappe.whitelist()
def get(filters=None,**kwargs):
    filters=frappe.parse_json(filters) or {}
    meter_name=filters.get("utility_meter") or frappe.db.get_value("Utility Meter",{"is_active":1},"name",order_by="creation asc")
    if not meter_name:return {"labels":[],"datasets":[],"candles":[],"message":_("Create an active utility meter and readings to view usage candles.")}
    meter=frappe.db.get_value("Utility Meter",meter_name,["name","meter_name","utility_type","unit_of_measure"],as_dict=True)
    if not meter:return {"labels":[],"datasets":[],"candles":[]}
    rows=frappe.get_all("Utility Reading",filters={"utility_meter":meter_name,"is_opening_reading":0},fields=["reading_date","consumption"],order_by="reading_date asc, creation asc")
    months={}
    for row in rows:
        key=str(row.reading_date)[:7]
        bucket=months.setdefault(key,{"date":row.reading_date,"usage":0})
        bucket["usage"]+=flt(row.consumption)
    prior=None;candles=[]
    for bucket in months.values():
        usage=bucket["usage"];opening=usage if prior is None else prior
        candles.append({"label":formatdate(bucket["date"],"MMM yyyy"),"open":round(opening,2),"close":round(usage,2),"high":round(max(opening,usage),2),"low":round(min(opening,usage),2),"change":round(usage-opening,2),"is_first":cint(prior is None)})
        prior=usage
    unit=meter.unit_of_measure or _("units")
    return {"labels":[c["label"] for c in candles],"datasets":[{"name":_("Monthly consumption ({0})").format(unit),"values":[c["close"] for c in candles]}],"candles":candles,"unit":unit,"meter_name":meter.name,"meter_label":meter.meter_name or meter.name,"utility_type":meter.utility_type,"message":_("Each candle compares this month's consumption with the previous recorded month.")}

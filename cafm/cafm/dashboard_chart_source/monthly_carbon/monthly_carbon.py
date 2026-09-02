import frappe
@frappe.whitelist()
def get(**kwargs):
 rows=frappe.get_all("Utility Reading",fields=["reading_date","carbon_emissions"],order_by="reading_date asc")
 data={}
 for r in rows:
  key=str(r.reading_date)[:7];data[key]=data.get(key,0)+(r.carbon_emissions or 0)
 return {"labels":list(data.keys()),"datasets":[{"name":"Carbon (kg CO2e)","values":list(data.values())}]}

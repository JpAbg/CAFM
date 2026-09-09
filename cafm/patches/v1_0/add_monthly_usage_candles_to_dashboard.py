import frappe

def execute():
    if frappe.db.exists("Dashboard", "Utility Consumption Dashboard"):
        dashboard = frappe.get_doc("Dashboard", "Utility Consumption Dashboard")
        if not any(row.chart == "Monthly Usage Candles" for row in dashboard.charts):
            dashboard.append("charts", {"chart": "Monthly Usage Candles", "width": "Full"})
            dashboard.save(ignore_permissions=True)
    if frappe.db.exists("Dashboard Chart", "Monthly Usage Candles"):
        frappe.db.set_value(
            "Dashboard Chart",
            "Monthly Usage Candles",
            "type",
            "Candlestick",
            update_modified=False,
        )

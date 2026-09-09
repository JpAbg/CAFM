frappe.provide("frappe.dashboards.chart_sources");
frappe.dashboards.chart_sources["Monthly Usage Candles"]={method:"cafm.cafm.dashboard_chart_source.monthly_usage_candles.monthly_usage_candles.get",filters:[{fieldname:"utility_meter",label:__("Utility Meter"),fieldtype:"Link",options:"Utility Meter"}]};

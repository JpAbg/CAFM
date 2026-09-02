frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Monthly Utility Cost"] = {
    method: "cafm.cafm.dashboard_chart_source.monthly_utility_cost.monthly_utility_cost.get",
};

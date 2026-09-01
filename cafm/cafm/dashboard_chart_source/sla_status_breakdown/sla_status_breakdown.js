frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["SLA Status Breakdown"] = {
    method: "cafm.cafm.dashboard_chart_source.sla_status_breakdown.sla_status_breakdown.get",
};

frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Peak Demand Trend"] = {
    method: "cafm.cafm.dashboard_chart_source.peak_demand_trend.peak_demand_trend.get",
    filters: [
        {
            fieldname: "utility_type",
            label: __("Utility Type"),
            fieldtype: "Select",
            options: "All\nElectricity\nWater\nNatural Gas\nFuel",
            default: "All",
        },
    ],
};

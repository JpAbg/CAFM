frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Utility Forecast"] = {
    method: "cafm.cafm.dashboard_chart_source.utility_forecast.utility_forecast.get",
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

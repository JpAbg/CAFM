// Copyright (c) 2026, Jean Paul Abou Gharib and contributors
// For license information, please see license.txt

frappe.query_reports["Preventive Maintenance Calendar"] = {
    filters: [
        {fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1},
        {fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.month_end(), reqd: 1},
        {fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1},
        {fieldname: "facility_location", label: __("Facility Location"), fieldtype: "Link", options: "Facility Location"},
        {
            fieldname: "asset",
            label: __("Asset"),
            fieldtype: "Link",
            options: "Asset",
            get_query() {
                const location = frappe.query_report.get_filter_value("facility_location");
                return location ? {filters: {custom_asset_location: location}} : {};
            },
        },
        {fieldname: "technician", label: __("Technician"), fieldtype: "Link", options: "Employee"},
        {
            fieldname: "work_order_status",
            label: __("Work Order Status"),
            fieldtype: "Select",
            default: "All",
            options: ["All", "Draft", "Assigned", "In Progress", "Pending"],
        },
    ],
};

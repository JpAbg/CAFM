frappe.query_reports["SLA Performance"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "facility_location",
            label: __("Facility Location"),
            fieldtype: "Link",
            options: "Facility Location",
        },
        {
            fieldname: "priority",
            label: __("Priority"),
            fieldtype: "Link",
            options: "Issue Priority",
        },
        {
            fieldname: "sla_policy",
            label: __("SLA Policy"),
            fieldtype: "Link",
            options: "Facility SLA Policy",
        },
        {
            fieldname: "sla_status",
            label: __("SLA Status"),
            fieldtype: "Select",
            default: "All",
            options: ["All", "On Track", "Response Breached", "Resolution Breached", "Met", "Not Applicable"],
        },
        {
            fieldname: "work_order_status",
            label: __("Work Order Status"),
            fieldtype: "Select",
            default: "All",
            options: ["All", "Draft", "Assigned", "In Progress", "Pending", "Resolved", "Closed", "Cancelled"],
        },
        {fieldname: "from_date", label: __("Created From"), fieldtype: "Date"},
        {fieldname: "to_date", label: __("Created To"), fieldtype: "Date"},
    ],
};

frappe.ui.form.on("Preventive Maintenance Plan", {
    setup(frm) {
        cafm.set_asset_query_for_location(frm, "asset", "facility_location");
        frm.set_query("technician", () => ({
            filters: {
                status: "Active",
                custom_is_facility_technician: 1,
                custom_facility_availability: ["not in", ["Inactive", "On Leave"]],
            },
        }));
        frm.set_query("vendor", () => ({
            filters: {
                status: "Active",
            },
        }));
        cafm.set_inspection_template_query(frm);
    },

    facility_location(frm) {
        cafm.clear_asset_when_location_changes(frm, "asset");
    },

    category(frm) {
        cafm.clear_inspection_template_when_category_changes(frm);
    },

    refresh(frm) {
        if (!frm.is_new() && frm.doc.is_active && frm.doc.next_due_date) {
            frm.add_custom_button(__("Generate Next Work Order"), () => {
                frappe.call({
                    method: "cafm.cafm.doctype.preventive_maintenance_plan.preventive_maintenance_plan.generate_next_work_order",
                    args: { plan_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Generating preventive work order..."),
                    callback(r) {
                        if (!r.exc && r.message) {
                            frappe.set_route(
                                "Form",
                                "Facility Work Order",
                                r.message
                            );
                        }
                    },
                });
            });
        }
    },
});

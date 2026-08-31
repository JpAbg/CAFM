frappe.ui.form.on("Facility Inspection Schedule", {
    setup(frm) {
        cafm.set_inspection_template_query(frm);
        cafm.set_asset_query_for_location(frm, "asset", "facility_location");
        frm.set_query("inspector", () => ({
            filters: { status: "Active" },
        }));
    },

    facility_location(frm) {
        cafm.clear_asset_when_location_changes(frm, "asset");
    },

    category(frm) {
        cafm.clear_inspection_template_when_category_changes(frm);
    },

    refresh(frm) {
        if (!frm.is_new() && frm.doc.is_active && frm.doc.next_due_date) {
            frm.add_custom_button(__("Generate Next Inspection"), () => {
                frappe.call({
                    method: "cafm.cafm.doctype.facility_inspection_schedule.facility_inspection_schedule.generate_next_inspection",
                    args: { schedule_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Generating inspection..."),
                    callback(r) {
                        if (!r.exc && r.message) {
                            frappe.set_route(
                                "Form",
                                "Facility Inspection",
                                r.message
                            );
                        }
                    },
                });
            });
        }
    },
});

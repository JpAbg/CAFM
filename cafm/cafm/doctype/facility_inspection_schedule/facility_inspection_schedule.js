frappe.ui.form.on("Facility Inspection Schedule", {
    setup(frm) {
        frm.set_query("inspection_template", () => ({
            filters: { is_active: 1 },
        }));
        frm.set_query("asset", () => ({
            filters: {
                company: frm.doc.company || undefined,
                docstatus: 1,
            },
        }));
        frm.set_query("inspector", () => ({
            filters: { status: "Active" },
        }));
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

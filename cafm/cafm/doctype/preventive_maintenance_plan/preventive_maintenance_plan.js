frappe.ui.form.on("Preventive Maintenance Plan", {
    setup(frm) {
        frm.set_query("asset", () => ({
            filters: {
                company: frm.doc.company || undefined,
                docstatus: 1,
            },
        }));
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
        frm.set_query("inspection_template", () => ({
            filters: {
                is_active: 1,
                category: frm.doc.category || undefined,
            },
        }));
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

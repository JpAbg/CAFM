frappe.ui.form.on("Issue", {
    issue_type(frm) {
        apply_cafm_priority_rule(frm);
    },

    custom_asset(frm) {
        apply_cafm_priority_rule(frm);
    },

    refresh(frm) {
        if (
            frm.is_new()
            || frm.doc.custom_work_order
            || !frappe.model.can_create("Facility Work Order")
        ) return;

        frm.add_custom_button(__("Create Work Order"), () => {
            frappe.call({
                method: "cafm.cafm.doctype.facility_work_order.facility_work_order.create_from_issue",
                args: { issue_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Creating Facility Work Order..."),
                callback(r) {
                    if (r.message) {
                        frappe.set_route("Form", "Facility Work Order", r.message);
                    }
                },
            });
        }, __("Create"));
    },
});

function apply_cafm_priority_rule(frm) {
    frappe.call({
        method: "cafm.events.issue.get_automatic_priority",
        args: {
            issue_type: frm.doc.issue_type,
            asset: frm.doc.custom_asset,
            current_priority: frm.doc.priority,
        },
        callback(r) {
            if (r.message && r.message !== frm.doc.priority) {
                frm.set_value("priority", r.message);
            }
        },
    });
}

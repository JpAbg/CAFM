frappe.ui.form.on("Facility Vendor Quotation", {
    setup(frm) {
        frm.set_query("service_provider", () => ({
            filters: {
                status: "Active",
                company: frm.doc.company || undefined,
            },
        }));
        frm.set_query("service_contract", () => ({
            filters: {
                contract_status: "Active",
                company: frm.doc.company || undefined,
                service_provider: frm.doc.service_provider || undefined,
            },
        }));
    },

    refresh(frm) {
        if (
            !frm.is_new()
            && frm.doc.quotation_status === "Received"
            && frappe.model.can_write("Facility Vendor Quotation")
        ) {
            frm.add_custom_button(__("Select Quotation"), () => {
                frappe.confirm(
                    __("Select this quotation and reject the other open quotations for this work order?"),
                    () => {
                        frappe.call({
                            method: "cafm.cafm.doctype.facility_vendor_quotation.facility_vendor_quotation.select_vendor_quotation",
                            args: {quotation_name: frm.doc.name},
                            freeze: true,
                            freeze_message: __("Selecting vendor quotation..."),
                            callback(r) {
                                if (!r.exc && r.message) {
                                    frappe.set_route("Form", "Facility Work Order", r.message);
                                }
                            },
                        });
                    }
                );
            }, __("Actions"));
        }
    },

    quoted_amount(frm) {
        set_quotation_total(frm);
    },

    tax_amount(frm) {
        set_quotation_total(frm);
    },
});

function set_quotation_total(frm) {
    frm.set_value(
        "total_amount",
        flt(frm.doc.quoted_amount) + flt(frm.doc.tax_amount)
    );
}

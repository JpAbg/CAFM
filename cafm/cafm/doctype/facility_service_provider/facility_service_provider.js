frappe.ui.form.on("Facility Service Provider", {
    setup(frm) {
        frm.set_query("supplier", () => ({
            query: "cafm.cafm.doctype.facility_service_provider.facility_service_provider.active_supplier_query",
        }));
    },

    refresh(frm) {
        frm.get_field("service_phone").$wrapper.addClass("cafm-service-phone");
    },
});

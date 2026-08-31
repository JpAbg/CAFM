frappe.ui.form.on("Facility Location", {
    setup(frm) {
        frm.set_query("building", () => ({ filters: { site: frm.doc.site } }));
        frm.set_query("floor", () => ({ filters: { building: frm.doc.building } }));
        frm.set_query("room", () => ({ filters: { floor: frm.doc.floor } }));
    },
    site(frm) {
        frm.set_value("building", null);
        frm.set_value("floor", null);
        frm.set_value("room", null);
    },
    building(frm) {
        frm.set_value("floor", null);
        frm.set_value("room", null);
    },
    floor(frm) {
        frm.set_value("room", null);
    },
});

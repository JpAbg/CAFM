frappe.ui.form.on("Facility Inspection", {
    setup(frm) {
        cafm.set_asset_query_for_location(frm, "asset", "facility_location");
        cafm.set_inspection_template_query(frm);
        frm.set_query("inspector", () => ({
            filters: { status: "Active" },
        }));
    },

    onload(frm) {
        if (frm.is_new() && !frm.doc.category) {
            frm.set_value("category", "General");
        }
    },

    facility_location(frm) {
        cafm.clear_asset_when_location_changes(frm, "asset");
    },

    category(frm) {
        cafm.clear_inspection_template_when_category_changes(frm);
    },

    refresh(frm) {
        const grid = frm.get_field("results").grid;
        grid.cannot_add_rows = true;
        grid.cannot_delete_rows = true;
        grid.cannot_move_rows = true;
        grid.refresh();

        if (frm.doc.work_order) {
            frm.add_custom_button(__("Open Work Order"), () => {
                frappe.set_route(
                    "Form",
                    "Facility Work Order",
                    frm.doc.work_order
                );
            });
        }
    },

    async inspection_template(frm) {
        if (!frm.doc.inspection_template || !frm.is_new()) return;
        const template = await frappe.db.get_doc(
            "Facility Inspection Template",
            frm.doc.inspection_template
        );
        frm.clear_table("results");
        (template.items || []).forEach((point) => {
            const row = frm.add_child("results");
            row.inspection_point = point.inspection_point;
            row.instructions = point.instructions;
            row.is_required = point.is_required;
            row.requires_evidence = point.requires_evidence;
            row.result = "Pending";
        });
        frm.refresh_field("results");
    },
});

window.cafm = window.cafm || {};

cafm.set_asset_query_for_location = function (
    frm,
    asset_fieldname,
    location_fieldname
) {
    frm.set_query(asset_fieldname, () => {
        const filters = {
            docstatus: 1,
        };

        if (frm.doc[location_fieldname]) {
            filters.custom_asset_location = frm.doc[location_fieldname];
        }

        if (frm.doc.company) {
            filters.company = frm.doc.company;
        }

        return { filters };
    });
};

cafm.clear_asset_when_location_changes = function (frm, asset_fieldname) {
    if (frm.doc[asset_fieldname]) {
        frm.set_value(asset_fieldname, null);
    }
};

cafm.set_inspection_template_query = function (frm) {
    frm.set_query("inspection_template", () => {
        const filters = { is_active: 1 };

        if (frm.doc.category && frm.doc.category !== "General") {
            filters.category = ["in", [frm.doc.category, "General"]];
        }

        return { filters };
    });
};

cafm.clear_inspection_template_when_category_changes = function (frm) {
    if (frm.doc.inspection_template) {
        frm.set_value("inspection_template", null);
    }
};

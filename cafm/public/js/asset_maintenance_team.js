frappe.ui.form.on("Asset Maintenance Team", {
    setup(frm) {
        frm.set_query(
            "maintenance_role",
            "maintenance_team_members",
            (doc, cdt, cdn) => {
                const row = locals[cdt][cdn];
                return {
                    query: "cafm.api.user_maintenance_role_query",
                    filters: { user: row.team_member },
                };
            }
        );
    },
});

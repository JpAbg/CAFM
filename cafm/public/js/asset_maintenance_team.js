frappe.ui.form.on("Asset Maintenance Team", {
    setup(frm) {
        for (const fieldname of [
            "maintenance_team_members",
            "custom_cafm_team_members",
        ]) {
            frm.set_query(
                "maintenance_role",
                fieldname,
                (doc, cdt, cdn) => {
                    const row = locals[cdt][cdn];
                    return {
                        query: "cafm.api.user_maintenance_role_query",
                        filters: {
                            employee: row.employee,
                            user: row.user || row.team_member,
                        },
                    };
                }
            );
        }
    },
});

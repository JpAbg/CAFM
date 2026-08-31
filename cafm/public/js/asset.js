frappe.ui.form.on("Asset", {
    refresh(frm) {
        show_open_maintenance_work(frm);
        show_asset_maintenance_history(frm);
    },

    custom_operational_status(frm) {
        show_open_maintenance_work(frm);
    },
});

function show_open_maintenance_work(frm) {
    const field = frm.fields_dict.custom_open_maintenance_work;
    if (!field) return;

    field.$wrapper.empty();
    if (
        frm.is_new()
        || frm.doc.custom_operational_status !== "Out of Service"
    ) return;

    frappe.call({
        method: "cafm.asset_maintenance.get_open_maintenance_work",
        args: { asset_name: frm.doc.name },
        callback(r) {
            const work_orders = r.message || [];
            field.$wrapper.html(render_open_work_orders(work_orders));
        },
    });

    frm.add_custom_button(__("View Open Work Orders"), () => {
        frappe.set_route("List", "Facility Work Order", {
            asset: frm.doc.name,
            work_order_status: ["not in", ["Closed", "Cancelled"]],
        });
    }, __("Maintenance"));
}

function render_open_work_orders(work_orders) {
    if (!work_orders.length) {
        return '<div class="text-muted">'
            + __("No open maintenance work exists for this asset.")
            + "</div>";
    }

    const rows = work_orders.map((row) => {
        const planned_end = row.planned_end
            ? frappe.datetime.str_to_user(row.planned_end)
            : "";
        const url = "/app/facility-work-order/"
            + encodeURIComponent(row.name);
        return "<tr>"
            + '<td><a href="' + url + '">'
            + frappe.utils.escape_html(row.name) + "</a></td>"
            + "<td>" + frappe.utils.escape_html(row.subject || "") + "</td>"
            + "<td>" + frappe.utils.escape_html(row.work_order_status || "") + "</td>"
            + "<td>" + frappe.utils.escape_html(row.priority || "") + "</td>"
            + "<td>" + frappe.utils.escape_html(planned_end) + "</td>"
            + "</tr>";
    }).join("");

    return '<div class="table-responsive">'
        + '<table class="table table-bordered table-hover">'
        + "<thead><tr>"
        + "<th>" + __("Work Order") + "</th>"
        + "<th>" + __("Subject") + "</th>"
        + "<th>" + __("Status") + "</th>"
        + "<th>" + __("Priority") + "</th>"
        + "<th>" + __("Planned End") + "</th>"
        + "</tr></thead><tbody>" + rows + "</tbody></table></div>";
}


function show_asset_maintenance_history(frm) {
    const field = frm.fields_dict.custom_maintenance_history;
    if (!field) return;

    field.$wrapper.empty();
    if (frm.is_new()) return;

    frappe.call({
        method: "cafm.asset_maintenance.get_asset_maintenance_history",
        args: { asset_name: frm.doc.name },
        callback(r) {
            const history = r.message || [];
            field.$wrapper.html(render_maintenance_history(history));
        },
    });

    if (frappe.model.can_read("Facility Asset Maintenance History")) {
        frm.add_custom_button(__("View Maintenance History"), () => {
            frappe.set_route(
                "List",
                "Facility Asset Maintenance History",
                { asset: frm.doc.name },
            );
        }, __("Maintenance"));
    }
}

function render_maintenance_history(history) {
    if (!history.length) {
        return '<div class="text-muted">'
            + __("No completed maintenance history exists for this asset.")
            + "</div>";
    }

    const rows = history.map((row) => {
        const closed_on = row.closed_on
            ? frappe.datetime.str_to_user(row.closed_on)
            : "";
        const url = "/app/facility-work-order/"
            + encodeURIComponent(row.work_order);
        return "<tr>"
            + "<td>" + frappe.utils.escape_html(closed_on) + "</td>"
            + '<td><a href="' + url + '">'
            + frappe.utils.escape_html(row.work_order) + "</a></td>"
            + "<td>" + frappe.utils.escape_html(row.subject || "") + "</td>"
            + "<td>" + frappe.utils.escape_html(row.resolution_summary || "") + "</td>"
            + "<td>" + frappe.utils.escape_html(String(row.labor_hours || 0)) + "</td>"
            + "<td>" + frappe.utils.escape_html(String(row.downtime_hours || 0)) + "</td>"
            + "<td>" + frappe.format(
                row.material_cost || 0,
                { fieldtype: "Currency" },
            ) + "</td>"
            + "</tr>";
    }).join("");

    return '<div class="table-responsive">'
        + '<table class="table table-bordered table-hover">'
        + "<thead><tr>"
        + "<th>" + __("Closed On") + "</th>"
        + "<th>" + __("Work Order") + "</th>"
        + "<th>" + __("Subject") + "</th>"
        + "<th>" + __("Resolution") + "</th>"
        + "<th>" + __("Labor Hours") + "</th>"
        + "<th>" + __("Downtime Hours") + "</th>"
        + "<th>" + __("Material Cost") + "</th>"
        + "</tr></thead><tbody>" + rows + "</tbody></table></div>";
}

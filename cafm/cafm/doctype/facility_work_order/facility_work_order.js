// Copyright (c) 2026, Jean Paul Abou Gharib and contributors
// For license information, please see license.txt

frappe.ui.form.on("Facility Work Order", {
    setup(frm) {
        cafm.set_asset_query_for_location(frm, "asset", "facility_location");
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
        frm.set_query("service_contract", () => ({
            filters: {
                contract_status: "Active",
                company: frm.doc.company || undefined,
                service_provider: frm.doc.vendor || undefined,
            },
        }));
        frm.set_query("preventive_maintenance_plan", () => ({
            filters: {
                is_active: 1,
                company: frm.doc.company || undefined,
            },
        }));
        cafm.set_inspection_template_query(frm);
        frm.set_query("item_code", "materials", () => ({
            filters: {
                is_stock_item: 1,
                disabled: 0,
            },
        }));
        frm.set_query("warehouse", "materials", () => ({
            filters: {
                company: frm.doc.company || undefined,
                is_group: 0,
                disabled: 0,
            },
        }));
        frm.set_query("batch_no", "materials", (doc, cdt, cdn) => {
            const row = locals[cdt][cdn];
            return {
                filters: {
                    item: row.item_code || undefined,
                    disabled: 0,
                },
            };
        });
    },

    facility_location(frm) {
        cafm.clear_asset_when_location_changes(frm, "asset");
    },

    category(frm) {
        cafm.clear_inspection_template_when_category_changes(frm);
    },

    refresh(frm) {
        add_vendor_commercial_actions(frm);
        if (!frm.is_new() && frm.doc.inspection_template) {
            frm.add_custom_button(__("Create Inspection"), () => {
                frappe.call({
                    method: "cafm.cafm.doctype.facility_inspection.facility_inspection.create_from_work_order",
                    args: { work_order_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Creating inspection..."),
                    callback(r) {
                        if (!r.exc && r.message) {
                            frappe.set_route(
                                "Form",
                                "Facility Inspection",
                                r.message
                            );
                        }
                    },
                });
            }, __("Inspection"));
        }
        if (
            !frm.is_new() &&
            frm.doc.materials?.length &&
            ["Assigned", "In Progress", "Pending", "Resolved"].includes(
                frm.doc.work_order_status
            )
        ) {
            frm.add_custom_button(__("Issue Materials"), () => {
                frappe.call({
                    method: "cafm.materials.issue_materials",
                    args: { work_order_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Issuing materials from stock..."),
                    callback(r) {
                        if (!r.exc && r.message) {
                            frappe.set_route("Form", "Stock Entry", r.message);
                        }
                    },
                });
            }, __("Materials"));
        }
    },

    work_order_type(frm) {
        if (frm.doc.work_order_type === "Corrective") {
            frm.set_value("preventive_maintenance_plan", null);
            frm.set_value("scheduled_occurrence_date", null);
        } else if (frm.doc.work_order_type === "Preventive") {
            frm.set_value("maintenance_request", null);
        }
    },

    maintenance_request(frm) {
        if (!frm.doc.maintenance_request) return;

        frm.set_value("work_order_type", "Corrective");
        frappe.db.get_doc("Issue", frm.doc.maintenance_request).then((issue) => {
            frm.set_value("subject", issue.subject);
            frm.set_value("company", issue.company);
            frm.set_value("facility_location", issue.custom_facility_location);
            frm.set_value("asset", issue.custom_asset);
            frm.set_value("category", issue.issue_type);
            frm.set_value("priority", issue.priority);
            frm.set_value("work_description", issue.description);
        });
    },

    preventive_maintenance_plan(frm) {
        if (!frm.doc.preventive_maintenance_plan) return;

        frm.set_value("work_order_type", "Preventive");
        frappe.db
            .get_doc(
                "Preventive Maintenance Plan",
                frm.doc.preventive_maintenance_plan
            )
            .then((plan) => {
                frm.set_value(
                    "subject",
                    __("Preventive Maintenance: {0}", [plan.plan_name])
                );
                frm.set_value("company", plan.company);
                frm.set_value("facility_location", plan.facility_location);
                frm.set_value("asset", plan.asset);
                frm.set_value("category", plan.category);
                frm.set_value("priority", plan.priority);
                frm.set_value("work_description", plan.instructions);
                frm.set_value("assignment_type", plan.assignment_type);
                frm.set_value("technician", plan.technician);
                frm.set_value("vendor", plan.vendor);
                frm.set_value(
                    "inspection_required",
                    plan.inspection_required
                );
                frm.set_value(
                    "inspection_template",
                    plan.inspection_template
                );
            });
    },
});

function add_vendor_commercial_actions(frm) {
    if (frm.is_new()) return;

    if (frappe.model.can_create("Facility Vendor Quotation")) {
        frm.add_custom_button(__("Request Vendor Quotation"), () => {
            frappe.new_doc("Facility Vendor Quotation", {
                quotation_name: __("Quotation for {0}", [frm.doc.name]),
                work_order: frm.doc.name,
                company: frm.doc.company,
                service_provider: frm.doc.vendor,
                service_contract: frm.doc.service_contract,
                scope_of_work: frm.doc.work_description,
            });
        }, __("Vendor"));
    }

    if (frappe.model.can_read("Facility Vendor Quotation")) {
        frm.add_custom_button(__("View Vendor Quotations"), () => {
            frappe.set_route("List", "Facility Vendor Quotation", {
                work_order: frm.doc.name,
            });
        }, __("Vendor"));
    }

    if (frappe.model.can_read("Facility Service Contract")) {
        frm.add_custom_button(__("View Matching Contracts"), () => {
            frappe.call({
                method: "cafm.cafm.doctype.facility_service_contract.facility_service_contract.get_matching_service_contracts",
                args: {work_order_name: frm.doc.name},
                callback(r) {
                    const contracts = r.message || [];
                    if (!contracts.length) {
                        frappe.msgprint(__("No active Service Contract matches this work order."));
                        return;
                    }
                    frappe.set_route("List", "Facility Service Contract", {
                        name: ["in", contracts.map((contract) => contract.name)],
                    });
                },
            });
        }, __("Vendor"));
    }
}

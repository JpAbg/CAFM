import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import (
    make_property_setter,
)
from frappe.permissions import add_permission, update_permission_property


ROLES = (
    "Facility Manager",
    "Facility Coordinator",
    "Technician",
    "Requester / Employee",
    "Vendor",
)

WORKFLOW_STATES = {
    "New": "Primary",
    "Draft": "Primary",
    "Assigned": "Info",
    "In Progress": "Warning",
    "Pending": "Warning",
    "Completed": "Info",
    "Approved": "Success",
    "Resolved": "Success",
    "Closed": "Success",
    "Rejected": "Danger",
    "Cancelled": "Danger",
}

WORKFLOW_ACTIONS = (
    "Assign",
    "Start Work",
    "Put on Hold",
    "Resume",
    "Resolve",
    "Close",
    "Reopen",
    "Reject",
    "Cancel",
    "Assign Inspection",
    "Start Inspection",
    "Complete Inspection",
    "Approve Inspection",
    "Reject Inspection",
    "Reopen Inspection",
    "Cancel Inspection",
)


def after_install():
    setup_cafm()


def after_migrate():
    setup_cafm()


def setup_cafm():
    ensure_roles()
    ensure_issue_priorities()
    ensure_overdue_escalation_rules()
    ensure_general_inspection_category()
    ensure_custom_fields()
    ensure_asset_location_customization()
    ensure_asset_maintenance_team_customization()
    migrate_legacy_asset_maintenance_team_members()
    ensure_workflow_masters()
    ensure_permissions()
    ensure_workflows()
    backfill_asset_locations()
    backfill_asset_maintenance_history()
    cleanup_legacy_reason_fields()
    frappe.clear_cache()


def backfill_asset_maintenance_history():
    from cafm.asset_maintenance import (
        backfill_asset_maintenance_history as backfill,
    )

    backfill()


def backfill_asset_locations():
    from cafm.location_sync import backfill_asset_locations as backfill

    backfill()


def ensure_roles():
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 1,
                }
            ).insert(ignore_permissions=True)


def ensure_issue_priorities():
    priorities = {
        "Critical": (
            "Immediate attention required for critical facility work."
        ),
        "High": "High-priority facility work.",
        "Medium": "Normal-priority facility work.",
        "Low": "Low-priority facility work.",
    }
    for priority, description in priorities.items():
        if not frappe.db.exists("Issue Priority", priority):
            frappe.get_doc(
                {
                    "doctype": "Issue Priority",
                    "__newname": priority,
                    "description": description,
                }
            ).insert(ignore_permissions=True)




def ensure_overdue_escalation_rules():
    rules = (
        {
            "rule_name": "Critical work order escalation",
            "hours_overdue": 1,
            "priority": "Critical",
            "target_role": "Facility Manager",
            "description": "Escalate critical work orders one hour after due time.",
        },
        {
            "rule_name": "Coordinator overdue escalation",
            "hours_overdue": 4,
            "target_role": "Facility Coordinator",
            "description": "Escalate all work orders four hours after due time.",
        },
        {
            "rule_name": "Manager overdue escalation",
            "hours_overdue": 24,
            "target_role": "Facility Manager",
            "description": "Escalate all work orders one day after due time.",
        },
    )
    for rule in rules:
        if frappe.db.exists("Facility Overdue Escalation Rule", rule["rule_name"]):
            continue
        frappe.get_doc(
            {
                "doctype": "Facility Overdue Escalation Rule",
                "is_active": 1,
                **rule,
            }
        ).insert(ignore_permissions=True)


def ensure_general_inspection_category():
    if not frappe.db.exists("Issue Type", "General"):
        frappe.get_doc(
            {
                "doctype": "Issue Type",
                "__newname": "General",
            }
        ).insert(ignore_permissions=True)

    ensure_general_inspection_template()


def ensure_general_inspection_template():
    template_name = "General Facility Inspection"
    if frappe.db.exists("Facility Inspection Template", template_name):
        return

    frappe.get_doc(
        {
            "doctype": "Facility Inspection Template",
            "template_name": template_name,
            "category": "General",
            "is_active": 1,
            "items": [
                {
                    "inspection_point": "Verify the area is safe and accessible.",
                    "is_required": 1,
                },
                {
                    "inspection_point": "Check for visible damage, leaks, or hazards.",
                    "is_required": 1,
                },
                {
                    "inspection_point": "Record any defects that require follow-up.",
                    "is_required": 1,
                },
            ],
        }
    ).insert(ignore_permissions=True)


def ensure_custom_fields():
    create_custom_fields(
        {
            "Dashboard Chart": [
                {
                    "fieldname": "custom_horizontal_bars",
                    "fieldtype": "Check",
                    "label": "Horizontal Bars",
                    "insert_after": "type",
                    "depends_on": "eval:doc.type == 'Bar'",
                    "description": (
                        "Render this dashboard chart with horizontal bars."
                    ),
                },
            ],
            "Issue Type": [
                {
                    "fieldname": "custom_cafm_minimum_priority",
                    "fieldtype": "Link",
                    "label": "Minimum CAFM Priority",
                    "options": "Issue Priority",
                    "insert_after": "description",
                    "description": (
                        "Requests in this category are automatically raised "
                        "to at least this priority."
                    ),
                },
            ],
            "Asset": [
                {
                    "fieldname": "custom_asset_location",
                    "fieldtype": "Link",
                    "label": "Facility Location",
                    "options": "Facility Location",
                    "insert_after": "asset_owner_company",
                    "reqd": 1,
                    "description": (
                        "CAFM site, building, floor, and room location."
                    ),
                },
                {
                    "fieldname": "custom_criticality",
                    "fieldtype": "Select",
                    "label": "Criticality",
                    "options": "\nLow\nMedium\nHigh\nCritical",
                    "insert_after": "custom_asset_location",
                    "description": (
                        "Requests for this asset are automatically raised "
                        "to at least this priority."
                    ),
                },
                {
                    "fieldname": "custom_operational_status",
                    "fieldtype": "Select",
                    "label": "Operational Status",
                    "options": (
                        "In Service\nOut of Service\n"
                        "Under Maintenance\nRetired"
                    ),
                    "default": "In Service",
                    "insert_after": "custom_criticality",
                },
                {
                    "fieldname": "custom_open_maintenance_section",
                    "fieldtype": "Section Break",
                    "label": "Open Maintenance Work",
                    "insert_after": "custom_operational_status",
                    "depends_on": (
                        "eval:doc.custom_operational_status=="
                        "'Out of Service'"
                    ),
                },
                {
                    "fieldname": "custom_open_maintenance_work",
                    "fieldtype": "HTML",
                    "label": "Open Maintenance Work",
                    "insert_after": "custom_open_maintenance_section",
                    "depends_on": (
                        "eval:doc.custom_operational_status=="
                        "'Out of Service'"
                    ),
                },
                {
                    "fieldname": "custom_maintenance_history_section",
                    "fieldtype": "Section Break",
                    "label": "Maintenance History",
                    "insert_after": "custom_open_maintenance_work",
                    "collapsible": 1,
                },
                {
                    "fieldname": "custom_maintenance_history",
                    "fieldtype": "HTML",
                    "label": "Maintenance History",
                    "insert_after": "custom_maintenance_history_section",
                },
            ],
            "Employee": [
                {
                    "fieldname": "custom_cafm_technician_section",
                    "fieldtype": "Section Break",
                    "label": "CAFM Technician",
                    "insert_after": "status",
                },
                {
                    "fieldname": "custom_is_facility_technician",
                    "fieldtype": "Check",
                    "label": "Is Facility Technician",
                    "insert_after": "custom_cafm_technician_section",
                    "default": "0",
                },
                {
                    "fieldname": "custom_primary_specialization",
                    "fieldtype": "Select",
                    "label": "Primary Specialization",
                    "options": "\nHVAC\nElectrical\nPlumbing\nFire Safety\nCleaning\nGeneral Maintenance",
                    "insert_after": "custom_is_facility_technician",
                    "depends_on": "eval:doc.custom_is_facility_technician",
                    "mandatory_depends_on": "eval:doc.custom_is_facility_technician",
                },
                {
                    "fieldname": "custom_facility_availability",
                    "fieldtype": "Select",
                    "label": "Facility Availability",
                    "options": "Available\nAssigned\nBusy\nOn Leave\nInactive",
                    "insert_after": "custom_primary_specialization",
                    "depends_on": "eval:doc.custom_is_facility_technician",
                    "read_only": 1,
                    "default": "Available",
                },
                {
                    "fieldname": "custom_max_active_work_orders",
                    "fieldtype": "Int",
                    "label": "Maximum Active Work Orders",
                    "insert_after": "custom_facility_availability",
                    "depends_on": "eval:doc.custom_is_facility_technician",
                    "default": "5",
                    "non_negative": 1,
                },
                {
                    "fieldname": "custom_service_categories",
                    "fieldtype": "Table",
                    "label": "Service Categories",
                    "options": "Facility Service Category",
                    "insert_after": "custom_max_active_work_orders",
                    "depends_on": "eval:doc.custom_is_facility_technician",
                },
            ],
            "Stock Entry": [
                {
                    "fieldname": "custom_cafm_reference_section",
                    "fieldtype": "Section Break",
                    "label": "CAFM Reference",
                    "insert_after": "remarks",
                    "depends_on": "eval:doc.custom_cafm_material_issue",
                },
                {
                    "fieldname": "custom_facility_work_order",
                    "fieldtype": "Link",
                    "label": "Facility Work Order",
                    "options": "Facility Work Order",
                    "insert_after": "custom_cafm_reference_section",
                    "read_only": 1,
                    "ignore_user_permissions": 1,
                },
                {
                    "fieldname": "custom_cafm_material_issue",
                    "fieldtype": "Check",
                    "label": "CAFM Material Issue",
                    "insert_after": "custom_facility_work_order",
                    "read_only": 1,
                    "hidden": 1,
                    "default": "0",
                },
            ],
            "Stock Entry Detail": [
                {
                    "fieldname": "custom_facility_work_order_material",
                    "fieldtype": "Data",
                    "label": "Facility Work Order Material",
                    "insert_after": "item_code",
                    "read_only": 1,
                    "hidden": 1,
                },
            ],
        },
        update=True,
    )


def ensure_asset_location_customization():
    # ERPNext makes Asset.location mandatory. CAFM supplies that value through
    # custom_asset_location and the location sync hook, so relax the form-level
    # requirement before hiding the standard field. The database value remains
    # populated internally and no ERPNext core DocType is changed.
    required_filters = {
        "doc_type": "Asset",
        "field_name": "location",
        "property": "reqd",
    }
    required_setter = frappe.db.get_value(
        "Property Setter",
        required_filters,
        ["name", "value"],
        as_dict=True,
    )
    if required_setter:
        if required_setter.value != "0":
            frappe.db.set_value(
                "Property Setter",
                required_setter.name,
                "value",
                "0",
                update_modified=False,
            )
    else:
        make_property_setter(
            "Asset",
            "location",
            "reqd",
            "0",
            "Check",
            is_system_generated=False,
        )

    filters = {
        "doc_type": "Asset",
        "field_name": "location",
        "property": "hidden",
    }
    setter = frappe.db.get_value(
        "Property Setter",
        filters,
        ["name", "value"],
        as_dict=True,
    )
    if setter:
        if setter.value != "1":
            frappe.db.set_value(
                "Property Setter",
                setter.name,
                "value",
                "1",
                update_modified=False,
            )
        return

    make_property_setter(
        "Asset",
        "location",
        "hidden",
        "1",
        "Check",
        is_system_generated=False,
    )



def ensure_asset_maintenance_team_customization():
    create_custom_fields(
        {
            "Asset Maintenance Team": [
                {
                    "fieldname": "custom_cafm_team_section",
                    "fieldtype": "Section Break",
                    "label": "CAFM Team Membership",
                    "insert_after": "maintenance_team_members",
                },
                {
                    "fieldname": "custom_cafm_team_members",
                    "fieldtype": "Table",
                    "label": "CAFM Team Members",
                    "options": "Facility Maintenance Team Membership",
                    "insert_after": "custom_cafm_team_section",
                },
            ],
        },
        update=True,
    )

    for property_name, value, property_type in (
        ("reqd", "0", "Check"),
        ("hidden", "1", "Check"),
    ):
        filters = {
            "doc_type": "Asset Maintenance Team",
            "field_name": "maintenance_team_members",
            "property": property_name,
        }
        setter = frappe.db.get_value(
            "Property Setter", filters, ["name", "value"], as_dict=True
        )
        if setter:
            if setter.value != value:
                frappe.db.set_value(
                    "Property Setter",
                    setter.name,
                    "value",
                    value,
                    update_modified=False,
                )
            continue

        make_property_setter(
            "Asset Maintenance Team",
            "maintenance_team_members",
            property_name,
            value,
            property_type,
            is_system_generated=False,
        )


def migrate_legacy_asset_maintenance_team_members():
    for team_name in frappe.get_all("Asset Maintenance Team", pluck="name"):
        team = frappe.get_doc("Asset Maintenance Team", team_name)
        if team.get("custom_cafm_team_members"):
            continue

        for member in team.get("maintenance_team_members") or []:
            employee = frappe.db.get_value(
                "Employee",
                {"user_id": member.team_member, "status": "Active"},
                "name",
            )
            if not employee or not frappe.db.exists(
                "Has Role",
                {
                    "parent": member.team_member,
                    "parenttype": "User",
                    "role": member.maintenance_role,
                },
            ):
                continue
            team.append(
                "custom_cafm_team_members",
                {
                    "employee": employee,
                    "user": member.team_member,
                    "maintenance_role": member.maintenance_role,
                },
            )

        if team.get("custom_cafm_team_members"):
            team.save(ignore_permissions=True)


def ensure_workflow_masters():
    for state_name, style in WORKFLOW_STATES.items():
        if not frappe.db.exists("Workflow State", state_name):
            frappe.get_doc(
                {
                    "doctype": "Workflow State",
                    "workflow_state_name": state_name,
                    "style": style,
                }
            ).insert(ignore_permissions=True)

    for action_name in WORKFLOW_ACTIONS:
        if not frappe.db.exists("Workflow Action Master", action_name):
            frappe.get_doc(
                {
                    "doctype": "Workflow Action Master",
                    "workflow_action_name": action_name,
                }
            ).insert(ignore_permissions=True)


def ensure_permissions():
    permission_map = {
        # Another installed app may add Custom DocPerm rows for Number Card.
        # Frappe treats custom rows as a complete replacement for the standard
        # permissions, so preserve the core dashboard-authoring roles here.
        "Number Card": {
            "System Manager": {
                "read", "write", "create", "delete", "report",
                "export", "share", "print", "email",
            },
            "Dashboard Manager": {
                "read", "write", "create", "delete", "report",
                "export", "share", "print", "email",
            },
        },
        # Shared master records required by CAFM forms. These are read-only for
        # operational roles; their normal ERPNext permissions remain intact.
        "Company": {
            "Facility Manager": {"read"},
            "Facility Coordinator": {"read"},
            "Technician": {"read"},
            "Requester / Employee": {"read"},
            "Vendor": {"read"},
        },
        "Site": {
            "Facility Manager": {"read", "write", "create", "delete", "report"},
            "Facility Coordinator": {"read", "write", "create", "report"},
        },
        "Building": {
            "Facility Manager": {"read", "write", "create", "delete", "report"},
            "Facility Coordinator": {"read", "write", "create", "report"},
        },
        "Floor": {
            "Facility Manager": {"read", "write", "create", "delete", "report"},
            "Facility Coordinator": {"read", "write", "create", "report"},
        },
        "Room": {
            "Facility Manager": {"read", "write", "create", "delete", "report"},
            "Facility Coordinator": {"read", "write", "create", "report"},
        },
        "Facility Location": {
            "Facility Manager": {"read", "write", "create", "delete", "report"},
            "Facility Coordinator": {"read", "write", "create", "report"},
            "Requester / Employee": {"read"},
            "Technician": {"read"},
            "Vendor": {"read"},
        },
        "Asset": {
            "Facility Manager": {"read", "write", "create", "report"},
            "Facility Coordinator": {"read", "write", "create", "report"},
            "Requester / Employee": {"read"},
            "Technician": {"read"},
            "Vendor": {"read"},
        },
        "Asset Category": {
            "Facility Manager": {"read", "write", "create", "delete", "report"},
            "Facility Coordinator": {"read", "write", "create", "report"},
            "Requester / Employee": {"read"},
            "Technician": {"read"},
            "Vendor": {"read"},
        },
        "Facility Asset Maintenance History": {
            "Facility Manager": {"read", "report", "export", "print"},
            "Facility Coordinator": {"read", "report", "export", "print"},
        },
        "Facility Service Provider": {
            "Facility Manager": {
                "read",
                "write",
                "create",
                "delete",
                "report",
                "share",
            },
            "Facility Coordinator": {
                "read",
                "write",
                "create",
                "report",
                "share",
            },
            "Vendor": {"read"},
        },
        "Facility Inspection Template": {
            "Facility Manager": {
                "read", "write", "create", "delete", "report", "share"
            },
            "Facility Coordinator": {
                "read", "write", "create", "report", "share"
            },
            "Technician": {"read"},
        },
        "Facility Inspection Schedule": {
            "Facility Manager": {
                "read", "write", "create", "delete", "report", "share"
            },
            "Facility Coordinator": {
                "read", "write", "create", "report", "share"
            },
        },
        "Facility Inspection": {
            "Facility Manager": {
                "read", "write", "create", "delete", "report", "share"
            },
            "Facility Coordinator": {
                "read", "write", "create", "report", "share"
            },
            "Technician": {"read", "write", "report"},
        },
        "Preventive Maintenance Plan": {
            "Facility Manager": {
                "read",
                "write",
                "create",
                "delete",
                "report",
                "share",
            },
            "Facility Coordinator": {
                "read",
                "write",
                "create",
                "report",
                "share",
            },
            "Technician": {"read"},
        },
        "Issue Priority": {
            "Facility Manager": {"read", "write", "create", "report"},
            "Facility Coordinator": {"read"},
            "Requester / Employee": {"read"},
            "Technician": {"read"},
            "Vendor": {"read"},
        },
        "Issue Type": {
            "Facility Manager": {"read", "write", "create", "report"},
            "Facility Coordinator": {"read"},
            "Requester / Employee": {"read"},
            "Technician": {"read"},
            "Vendor": {"read"},
        },
        "Issue": {
            "Facility Manager": {"read", "write", "create", "delete", "report", "share"},
            "Facility Coordinator": {"read", "write", "create", "report", "share"},
            "Requester / Employee": {"read", "write", "create"},
            "Technician": {"read"},
        },
        "Facility Work Order": {
            "Facility Manager": {"read", "write", "create", "delete", "report", "share"},
            "Facility Coordinator": {"read", "write", "create", "report", "share"},
            "Technician": {"read", "write"},
            "Requester / Employee": {"read"},
            "Vendor": {"read", "write"},
        },
        # Technicians select issued materials through the protected CAFM API.
        # They can read these masters but still cannot create Stock Entries.
        "Item": {
            "Facility Manager": {"read"},
            "Facility Coordinator": {"read"},
            "Technician": {"read"},
        },
        "Warehouse": {
            "Facility Manager": {"read"},
            "Facility Coordinator": {"read"},
            "Technician": {"read"},
        },
        "Supplier": {
            "Facility Manager": {"read"},
            "Facility Coordinator": {"read"},
        },
    }

    all_rights = (
        "read",
        "write",
        "create",
        "delete",
        "submit",
        "cancel",
        "amend",
        "report",
        "export",
        "import",
        "share",
        "print",
        "email",
    )

    for doctype, role_permissions in permission_map.items():
        for role, rights in role_permissions.items():
            existing = frappe.db.get_value(
                "Custom DocPerm",
                {
                    "parent": doctype,
                    "role": role,
                    "permlevel": 0,
                    "if_owner": 0,
                },
            )
            if not existing:
                add_permission(doctype, role, ptype="read")

            for right in all_rights:
                update_permission_property(
                    doctype,
                    role,
                    0,
                    right,
                    1 if right in rights else 0,
                    validate=False,
                )


def ensure_workflows():
    upsert_workflow(
        "CAFM Maintenance Request Workflow",
        "Issue",
        "custom_issue_status",
        [
            ("New", "Facility Coordinator"),
            ("Assigned", "Facility Coordinator"),
            ("In Progress", "Technician"),
            ("Pending", "Technician"),
            ("Resolved", "Facility Manager"),
            ("Closed", "Facility Manager"),
            ("Rejected", "Facility Manager"),
        ],
        [
            ("New", "Assign", "Assigned", "Facility Coordinator"),
            ("New", "Reject", "Rejected", "Facility Coordinator"),
            ("Assigned", "Start Work", "In Progress", "Technician"),
            ("Assigned", "Reject", "Rejected", "Facility Coordinator"),
            ("In Progress", "Put on Hold", "Pending", "Technician"),
            ("Pending", "Resume", "In Progress", "Technician"),
            ("In Progress", "Resolve", "Resolved", "Technician"),
            ("Resolved", "Close", "Closed", "Facility Manager"),
            ("Resolved", "Reopen", "In Progress", "Facility Manager"),
        ],
    )

    upsert_workflow(
        "CAFM Facility Work Order Workflow",
        "Facility Work Order",
        "work_order_status",
        [
            ("Draft", "Facility Coordinator"),
            ("Assigned", "Technician"),
            ("Assigned", "Vendor"),
            ("In Progress", "Technician"),
            ("In Progress", "Vendor"),
            ("Pending", "Technician"),
            ("Pending", "Vendor"),
            ("Resolved", "Facility Manager"),
            ("Closed", "Facility Manager"),
            ("Cancelled", "Facility Manager"),
        ],
        [
            ("Draft", "Assign", "Assigned", "Facility Coordinator"),
            ("Draft", "Cancel", "Cancelled", "Facility Coordinator"),
            ("Assigned", "Start Work", "In Progress", "Technician"),
            ("Assigned", "Start Work", "In Progress", "Vendor"),
            ("Assigned", "Cancel", "Cancelled", "Facility Coordinator"),
            ("In Progress", "Put on Hold", "Pending", "Technician"),
            ("In Progress", "Put on Hold", "Pending", "Vendor"),
            ("Pending", "Resume", "In Progress", "Technician"),
            ("Pending", "Resume", "In Progress", "Vendor"),
            ("In Progress", "Resolve", "Resolved", "Technician"),
            ("In Progress", "Resolve", "Resolved", "Vendor"),
            ("Resolved", "Close", "Closed", "Facility Manager"),
            ("Resolved", "Reopen", "In Progress", "Facility Manager"),
        ],
    )


    upsert_workflow(
        "CAFM Facility Inspection Workflow",
        "Facility Inspection",
        "status",
        [
            ("Draft", "Facility Coordinator"),
            ("Assigned", "Technician"),
            ("In Progress", "Technician"),
            ("Completed", "Facility Manager"),
            ("Approved", "Facility Manager"),
            ("Rejected", "Facility Manager"),
            ("Cancelled", "Facility Manager"),
        ],
        [
            (
                "Draft",
                "Assign Inspection",
                "Assigned",
                "Facility Coordinator",
            ),
            (
                "Draft",
                "Cancel Inspection",
                "Cancelled",
                "Facility Coordinator",
            ),
            (
                "Assigned",
                "Start Inspection",
                "In Progress",
                "Technician",
            ),
            (
                "In Progress",
                "Complete Inspection",
                "Completed",
                "Technician",
            ),
            (
                "Completed",
                "Approve Inspection",
                "Approved",
                "Facility Manager",
            ),
            (
                "Completed",
                "Reject Inspection",
                "Rejected",
                "Facility Manager",
            ),
            (
                "Rejected",
                "Reopen Inspection",
                "In Progress",
                "Facility Manager",
            ),
        ],
    )


def upsert_workflow(name, document_type, state_field, states, transitions):
    if frappe.db.exists("Workflow", name):
        workflow = frappe.get_doc("Workflow", name)
    else:
        workflow = frappe.new_doc("Workflow")
        workflow.workflow_name = name

    workflow.document_type = document_type
    workflow.workflow_state_field = state_field
    workflow.is_active = 1
    workflow.override_status = 0
    workflow.send_email_alert = 0
    workflow.set("states", [])
    workflow.set("transitions", [])

    for state, allow_edit in states:
        workflow.append(
            "states",
            {
                "state": state,
                "doc_status": "0",
                "allow_edit": allow_edit,
                "send_email": 0,
            },
        )

    for state, action, next_state, allowed in transitions:
        workflow.append(
            "transitions",
            {
                "state": state,
                "action": action,
                "next_state": next_state,
                "allowed": allowed,
                "allow_self_approval": 1,
            },
        )

    workflow.save(ignore_permissions=True)


def cleanup_legacy_reason_fields():
    for field_name in (
        "Issue-custom_pending_reson",
        "Issue-custom_rejection_reson",
        "Company-custom_sites",
    ):
        if frappe.db.exists("Custom Field", field_name):
            frappe.delete_doc(
                "Custom Field",
                field_name,
                ignore_permissions=True,
                force=True,
            )

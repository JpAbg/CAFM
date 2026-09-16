import frappe


TECHNICIANS = {
    "cafm.hvac.technician@example.com": (
        "HVAC",
        ("HVAC", "Plumbing", "Fire Safety"),
    ),
    "cafm.electrical.technician@example.com": (
        "Electrical",
        ("Electrical",),
    ),
}

CAFM_DEMO_USER_ROLES = {
    "cafm.demo.technician@example.com": ("Employee", "Technician"),
    "cafm.hvac.technician@example.com": ("Employee", "Technician"),
    "cafm.electrical.technician@example.com": ("Employee", "Technician"),
    "cafm.requester@example.com": ("Employee", "Requester / Employee"),
}


def normalize_cafm_demo_user_roles():
    """Keep CAFM-owned demo users isolated from unrelated role profiles."""
    for user_id, expected_roles in CAFM_DEMO_USER_ROLES.items():
        if not frappe.db.exists("User", user_id):
            continue

        user = frappe.get_doc("User", user_id)
        user.role_profile_name = None
        user.set("roles", [])
        for role in expected_roles:
            user.append("roles", {"role": role})
        user.save(ignore_permissions=True)

        if "Technician" in expected_roles:
            employee_name = frappe.db.get_value(
                "Employee", {"user_id": user_id}, "name"
            )
            if employee_name:
                frappe.db.set_value(
                    "Employee",
                    employee_name,
                    "custom_is_facility_technician",
                    1,
                    update_modified=False,
                )

    frappe.clear_cache()

PROVIDERS = (
    {
        "provider_name": "CoolAir Services Demo",
        "specialization": "HVAC",
        "categories": ("HVAC", "Plumbing"),
        "contact": "Maya Haddad",
        "phone": "+961 1 555 210",
        "email": "dispatch@coolair-demo.example.com",
        "response": 4,
        "emergency": 1,
    },
    {
        "provider_name": "SafeSpark Electrical Demo",
        "specialization": "Electrical",
        "categories": ("Electrical", "Fire Safety"),
        "contact": "Karim Nassar",
        "phone": "+961 1 555 310",
        "email": "service@safespark-demo.example.com",
        "response": 8,
        "emergency": 1,
    },
)


def audit_cafm_demo_user_roles():
    """Return a concise role audit for CAFM-owned demo accounts."""
    audit = {}
    for user_id in CAFM_DEMO_USER_ROLES:
        if not frappe.db.exists("User", user_id):
            continue
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user_id},
            ["name", "custom_is_facility_technician"],
            as_dict=True,
        )
        audit[user_id] = {
            "role_profile": frappe.db.get_value(
                "User", user_id, "role_profile_name"
            ),
            "roles": frappe.get_roles(user_id),
            "is_facility_technician": employee.custom_is_facility_technician
            if employee
            else None,
        }
    return audit

def seed_part_f_demo():
    frappe.set_user("Administrator")
    normalize_cafm_demo_user_roles()
    company = (
        frappe.db.exists("Company", "Ag's Industries")
        or frappe.db.get_value("Company", {}, "name")
    )
    configured_employees = []
    frappe.db.commit()
    frappe.clear_cache()

    for user, (specialization, categories) in TECHNICIANS.items():
        employee_name = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_name:
            continue
        employee = frappe.get_doc("Employee", employee_name)
        employee.custom_is_facility_technician = 1
        employee.custom_primary_specialization = specialization
        employee.custom_max_active_work_orders = 20
        employee.set("custom_service_categories", [])
        for category in categories:
            if frappe.db.exists("Issue Type", category):
                employee.append(
                    "custom_service_categories",
                    {
                        "service_category": category,
                        "is_primary": category == categories[0],
                    },
                )
        employee.save(ignore_permissions=True)
        configured_employees.append(employee.name)

    provider_names = []
    supplier_group = (
        frappe.db.exists("Supplier Group", "Services")
        or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
    )
    for values in PROVIDERS:
        if not frappe.db.exists("Supplier", values["provider_name"]):
            frappe.get_doc(
                {
                    "doctype": "Supplier",
                    "supplier_name": values["provider_name"],
                    "supplier_group": supplier_group,
                    "supplier_type": "Company",
                }
            ).insert(ignore_permissions=True)

        if frappe.db.exists("Facility Service Provider", values["provider_name"]):
            provider = frappe.get_doc(
                "Facility Service Provider", values["provider_name"]
            )
        else:
            provider = frappe.new_doc("Facility Service Provider")
            provider.provider_name = values["provider_name"]

        provider.supplier = values["provider_name"]
        provider.company = company
        provider.status = "Active"
        provider.primary_specialization = values["specialization"]
        provider.primary_contact_name = values["contact"]
        provider.service_phone = values["phone"]
        provider.service_email = values["email"]
        provider.response_time_hours = values["response"]
        provider.emergency_service = values["emergency"]
        provider.set("service_categories", [])
        for category in values["categories"]:
            if frappe.db.exists("Issue Type", category):
                provider.append(
                    "service_categories",
                    {
                        "service_category": category,
                        "is_primary": category == values["categories"][0],
                    },
                )
        provider.save(ignore_permissions=True)
        provider_names.append(provider.name)

    frappe.db.commit()
    return {
        "employees": configured_employees,
        "service_providers": provider_names,
    }


def inspect_part_f_users():
    return {
        user: {
            "exists": bool(frappe.db.exists("User", user)),
            "roles": [row.role for row in frappe.get_doc("User", user).roles]
            if frappe.db.exists("User", user) else [],
            "employee": frappe.db.get_value("Employee", {"user_id": user}, "name"),
        }
        for user in TECHNICIANS
    }



def seed_part_g_demo():
    seed_part_f_demo()

    from frappe.utils import nowdate

    from cafm.cafm.doctype.facility_inspection.facility_inspection import (
        create_from_work_order,
    )
    from cafm.inspections import generate_inspection_occurrence

    frappe.set_user("Administrator")
    company = (
        frappe.db.exists("Company", "Ag's Industries")
        or frappe.db.get_value("Company", {}, "name")
    )
    technician = frappe.db.get_value(
        "Employee",
        {"user_id": "cafm.hvac.technician@example.com"},
        "name",
    )
    if not technician:
        frappe.throw("The Part F HVAC demo technician is required.")

    templates = {
        "HVAC Work Completion Inspection": {
            "category": "HVAC",
            "description": (
                "Supervisor verification after HVAC maintenance work."
            ),
            "items": [
                {
                    "inspection_point": "Verify operating temperature",
                    "instructions": "Confirm temperature is within target range.",
                    "is_required": 1,
                },
                {
                    "inspection_point": "Inspect filters and covers",
                    "instructions": "Confirm filters and covers are secure.",
                    "is_required": 1,
                },
                {
                    "inspection_point": "Check for unusual noise",
                    "instructions": "Record any remaining vibration or noise.",
                    "is_required": 0,
                },
            ],
        },
        "Fire Safety Routine Inspection": {
            "category": "Fire Safety",
            "description": "Routine inspection of fire-safety equipment.",
            "items": [
                {
                    "inspection_point": "Confirm equipment is accessible",
                    "is_required": 1,
                },
                {
                    "inspection_point": "Check visible damage or leakage",
                    "is_required": 1,
                },
                {
                    "inspection_point": "Verify identification label",
                    "is_required": 1,
                },
            ],
        },
    }
    template_names = []
    for name, values in templates.items():
        if frappe.db.exists("Facility Inspection Template", name):
            template = frappe.get_doc(
                "Facility Inspection Template",
                name,
            )
        else:
            template = frappe.new_doc("Facility Inspection Template")
            template.template_name = name
        template.category = (
            values["category"]
            if frappe.db.exists("Issue Type", values["category"])
            else None
        )
        template.description = values["description"]
        template.is_active = 1
        template.set("items", [])
        for item in values["items"]:
            template.append("items", item)
        template.save(ignore_permissions=True)
        template_names.append(template.name)

    asset = frappe.db.get_value(
        "Asset",
        {
            "company": company,
            "docstatus": 1,
            "custom_asset_location": ["is", "set"],
        },
        ["name", "custom_asset_location"],
        as_dict=True,
    )
    schedule_name = "[Demo] Monthly Facility Inspection"
    if frappe.db.exists("Facility Inspection Schedule", schedule_name):
        schedule = frappe.get_doc(
            "Facility Inspection Schedule",
            schedule_name,
        )
    else:
        schedule = frappe.new_doc("Facility Inspection Schedule")
        schedule.schedule_name = schedule_name

    schedule.inspection_template = "HVAC Work Completion Inspection"
    schedule.company = company
    schedule.facility_location = (
        asset.custom_asset_location
        if asset
        else frappe.db.get_value("Facility Location", {}, "name")
    )
    schedule.asset = asset.name if asset else None
    schedule.category = (
        "HVAC" if frappe.db.exists("Issue Type", "HVAC") else None
    )
    schedule.inspector = technician
    schedule.frequency = "Monthly"
    schedule.start_date = schedule.start_date or nowdate()
    schedule.next_due_date = schedule.next_due_date or nowdate()
    schedule.generate_before_days = 0
    schedule.is_active = 1
    schedule.save(ignore_permissions=True)

    scheduled_inspection = generate_inspection_occurrence(
        schedule,
        nowdate(),
    )

    work_order_name = frappe.db.get_value(
        "Facility Work Order",
        {
            "company": company,
            "category": "HVAC",
            "technician": technician,
            "work_order_status": [
                "in",
                ["Draft", "Assigned", "In Progress", "Pending", "Resolved"],
            ],
        },
        "name",
    )
    work_order_inspection = None
    if work_order_name:
        work_order = frappe.get_doc(
            "Facility Work Order",
            work_order_name,
        )
        work_order.inspection_required = 1
        work_order.inspection_template = (
            "HVAC Work Completion Inspection"
        )
        work_order.save(ignore_permissions=True)
        work_order_inspection = create_from_work_order(work_order.name)

    frappe.db.commit()
    return {
        "templates": template_names,
        "schedule": schedule.name,
        "scheduled_inspection": scheduled_inspection,
        "work_order": work_order_name,
        "work_order_inspection": work_order_inspection,
    }



def seed_report_demo_data():
    """Create idempotent demo records covering all six required reports."""
    from cafm.asset_maintenance import sync_asset_maintenance_history

    seed_part_f_demo()
    frappe.set_user("Administrator")

    company = "Ag's Industries"

    def ensure_branch_asset():
        site_name = "CAFM Demo Regional Branch"
        if not frappe.db.exists("Site", site_name):
            frappe.get_doc(
                {
                    "doctype": "Site",
                    "company": company,
                    "site_name": site_name,
                    "site_id": "CAFM-BRANCH-01",
                    "status": "Active",
                    "site_type": "Regional Branch",
                    "address": "CAFM demonstration regional branch",
                    "city": "Beirut",
                }
            ).insert(ignore_permissions=True)

        building_name = "CAFM-BR-01"
        if not frappe.db.exists("Building", building_name):
            frappe.get_doc(
                {
                    "doctype": "Building",
                    "site": site_name,
                    "building_name": "Operations Building",
                    "building_id": building_name,
                    "total_floors": 1,
                    "status": "Active",
                    "building_type": "Warehouse",
                    "gross_area": 1800,
                }
            ).insert(ignore_permissions=True)

        floor_name = f"{building_name}-0"
        if not frappe.db.exists("Floor", floor_name):
            floor_name = frappe.get_doc(
                {
                    "doctype": "Floor",
                    "building": building_name,
                    "floor_name": "Ground Floor",
                    "floor_level": 0,
                    "floor_type": "Workspace",
                    "status": "Active",
                    "floor_area": 1800,
                }
            ).insert(ignore_permissions=True).name

        room_name = f"{floor_name}-UTIL"
        if not frappe.db.exists("Room", room_name):
            room_name = frappe.get_doc(
                {
                    "doctype": "Room",
                    "floor": floor_name,
                    "room_name": "Utility Room",
                    "room_id": "UTIL",
                    "room_type": "Storage",
                    "description": "Mechanical equipment room for dashboard demos.",
                }
            ).insert(ignore_permissions=True).name

        location_name = (
            f"{site_name} - Operations Building - Ground Floor - Utility Room"
        )
        if not frappe.db.exists("Facility Location", location_name):
            location_name = frappe.get_doc(
                {
                    "doctype": "Facility Location",
                    "site": site_name,
                    "building": building_name,
                    "floor": floor_name,
                    "room": room_name,
                }
            ).insert(ignore_permissions=True).name

        item_code = "CAFM-BRANCH-PUMP-AGI"
        asset_category = "CAFM Demo Building Equipment - AGI"
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": "Branch Fire Water Pump",
                    "description": "Fixed asset used by the CAFM dashboard demo.",
                    "asset_category": asset_category,
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                    "is_stock_item": 0,
                    "is_fixed_asset": 1,
                    "auto_create_assets": 0,
                }
            ).insert(ignore_permissions=True)

        erp_location_name = "CAFM Demo Branch Utility Room"
        if not frappe.db.exists("Location", erp_location_name):
            erp_location_name = frappe.get_doc(
                {
                    "doctype": "Location",
                    "location_name": erp_location_name,
                }
            ).insert(ignore_permissions=True).name

        asset_name = frappe.db.get_value(
            "Asset",
            {
                "asset_name": "Branch Fire Water Pump",
                "company": company,
                "docstatus": ["!=", 2],
            },
            "name",
        )
        if not asset_name:
            asset = frappe.get_doc(
                {
                    "doctype": "Asset",
                    "asset_name": "Branch Fire Water Pump",
                    "item_code": item_code,
                    "asset_category": asset_category,
                    "company": company,
                    "purchase_date": "2026-01-01",
                    "available_for_use_date": "2026-01-01",
                    "gross_purchase_amount": 8500,
                    "purchase_amount": 8500,
                    "calculate_depreciation": 0,
                    "is_existing_asset": 1,
                    "asset_owner": "Company",
                    "location": erp_location_name,
                    "custom_asset_location": location_name,
                }
            ).insert(ignore_permissions=True)
            asset.submit()
            asset_name = asset.name

        return frappe.db.get_value(
            "Asset",
            asset_name,
            ["name", "custom_asset_location"],
            as_dict=True,
        )
    requester = frappe.db.get_value(
        "Employee",
        {"user_id": "cafm.requester@example.com", "status": "Active"},
        "name",
    )
    hvac_technician = frappe.db.get_value(
        "Employee",
        {"user_id": "cafm.hvac.technician@example.com", "status": "Active"},
        "name",
    )
    electrical_technician = frappe.db.get_value(
        "Employee",
        {"user_id": "cafm.electrical.technician@example.com", "status": "Active"},
        "name",
    )
    hvac_asset = frappe.db.get_value(
        "Asset",
        {"asset_name": "HQ Rooftop HVAC Unit", "docstatus": 1},
        ["name", "custom_asset_location"],
        as_dict=True,
    )
    electrical_asset = frappe.db.get_value(
        "Asset",
        {"asset_name": "HQ Main Electrical Panel", "docstatus": 1},
        ["name", "custom_asset_location"],
        as_dict=True,
    )

    branch_asset = ensure_branch_asset()

    branch_plan_name = "PM-2026-00003"
    if frappe.db.exists("Preventive Maintenance Plan", branch_plan_name):
        branch_plan = frappe.get_doc(
            "Preventive Maintenance Plan", branch_plan_name
        )
    else:
        branch_plan = frappe.new_doc("Preventive Maintenance Plan")
    branch_plan.plan_name = "Branch Quarterly Pump Service"
    branch_plan.company = company
    branch_plan.asset = branch_asset.name
    branch_plan.facility_location = branch_asset.custom_asset_location
    branch_plan.category = "Plumbing"
    branch_plan.priority = "Medium"
    branch_plan.is_active = 1
    branch_plan.frequency = "Quarterly"
    branch_plan.start_date = "2026-01-01"
    branch_plan.next_due_date = "2026-11-26"
    branch_plan.generate_before_days = 7
    branch_plan.planned_duration_hours = 3
    branch_plan.assignment_type = "Internal Technician"
    branch_plan.technician = hvac_technician
    branch_plan.instructions = (
        "Inspect pump seals, operating pressure, and control condition."
    )
    branch_plan.save(ignore_permissions=True)
    branch_plan_name = branch_plan.name

    required = {
        "company": frappe.db.exists("Company", company),
        "requester": requester,
        "hvac_technician": hvac_technician,
        "electrical_technician": electrical_technician,
        "hvac_asset": hvac_asset,
        "electrical_asset": electrical_asset,
        "branch_asset": branch_asset,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        frappe.throw(
            "Missing report-demo prerequisites: {0}".format(", ".join(missing))
        )

    def ensure_issue(subject, asset, category, priority):
        name = frappe.db.get_value(
            "Issue",
            {"company": company, "subject": subject},
            "name",
        )
        if name:
            frappe.db.set_value(
                "Issue",
                name,
                {
                    "custom_facility_location": asset.custom_asset_location,
                    "custom_asset": asset.name,
                    "issue_type": category,
                    "priority": priority,
                },
                update_modified=False,
            )
            return name

        return frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": subject,
                "description": (
                    "Report demonstration maintenance request for "
                    f"{asset.name}."
                ),
                "company": company,
                "custom_requester": requester,
                "raised_by": "cafm.requester@example.com",
                "custom_facility_location": asset.custom_asset_location,
                "custom_asset": asset.name,
                "issue_type": category,
                "priority": priority,
            }
        ).insert(ignore_permissions=True).name

    def ensure_work_order(
        marker,
        *,
        issue_name=None,
        plan_name=None,
        occurrence_date=None,
        technician,
        planned_start,
        planned_end,
        actual_start=None,
        actual_end=None,
        status="Closed",
        labor_hours=0,
        material_cost=0,
    ):
        if issue_name:
            name = frappe.db.get_value(
                "Issue", issue_name, "custom_work_order"
            )
        else:
            occurrence_key = f"{plan_name}::{occurrence_date}"
            name = frappe.db.get_value(
                "Facility Work Order",
                {"preventive_occurrence_key": occurrence_key},
                "name",
            )

        if not name:
            work_order = frappe.new_doc("Facility Work Order")
            if issue_name:
                work_order.work_order_type = "Corrective"
                work_order.maintenance_request = issue_name
            else:
                work_order.work_order_type = "Preventive"
                work_order.preventive_maintenance_plan = plan_name
                work_order.scheduled_occurrence_date = occurrence_date

            work_order.assignment_type = "Internal Technician"
            work_order.technician = technician
            work_order.planned_start = planned_start
            work_order.planned_end = planned_end
            work_order.insert(ignore_permissions=True)
            name = work_order.name

        work_order = frappe.get_doc("Facility Work Order", name)
        if issue_name:
            request = frappe.db.get_value(
                "Issue",
                issue_name,
                [
                    "subject",
                    "company",
                    "custom_facility_location",
                    "custom_asset",
                    "issue_type",
                    "priority",
                    "description",
                ],
                as_dict=True,
            )
            work_order.subject = request.subject
            work_order.company = request.company
            work_order.facility_location = request.custom_facility_location
            work_order.asset = request.custom_asset
            work_order.category = request.issue_type
            work_order.priority = request.priority
            work_order.work_description = request.description
        work_order.planned_start = planned_start
        work_order.planned_end = planned_end
        work_order.actual_start = actual_start
        work_order.actual_end = actual_end
        work_order.resolution_summary = (
            f"[Report Demo] Maintenance outcome recorded for {marker}."
            if status in ("Resolved", "Closed")
            else None
        )

        if labor_hours and not work_order.labor_entries:
            work_order.append(
                "labor_entries",
                {
                    "employee": technician,
                    "start_time": actual_start,
                    "end_time": actual_end,
                    "notes": f"[Report Demo] Labor for {marker}.",
                },
            )

        if status in ("Resolved", "Closed"):
            for checklist_item in work_order.checklist:
                if checklist_item.result == "Pending":
                    checklist_item.result = "Pass"
                    checklist_item.comments = (
                        "[Report Demo] Required check completed."
                    )

        work_order.save(ignore_permissions=True)

        closed_on = actual_end if status == "Closed" else None
        frappe.db.set_value(
            "Facility Work Order",
            name,
            {
                "work_order_status": status,
                "planned_start": planned_start,
                "planned_end": planned_end,
                "actual_start": actual_start,
                "actual_end": actual_end,
                "resolution_summary": (
                    f"[Report Demo] Maintenance outcome recorded for {marker}."
                    if status in ("Resolved", "Closed")
                    else None
                ),
                "material_cost": material_cost,
                "closed_by": "Administrator" if status == "Closed" else None,
                "closed_on": closed_on,
            },
            update_modified=False,
        )

        if issue_name:
            status_map = {
                "Assigned": ("Assigned", "Open"),
                "In Progress": ("In Progress", "Open"),
                "Pending": ("Pending", "Hold"),
                "Resolved": ("Resolved", "Resolved"),
                "Closed": ("Closed", "Closed"),
            }
            if status in status_map:
                cafm_status, native_status = status_map[status]
                issue_updates = {
                    "custom_issue_status": cafm_status,
                    "status": native_status,
                }
                if status == "Pending":
                    issue_updates["custom_pending_reason"] = (
                        "[Report Demo] Awaiting a replacement component."
                    )
                if status in ("Resolved", "Closed"):
                    issue_updates["resolution_details"] = (
                        f"[Report Demo] Resolved through {name}."
                    )
                frappe.db.set_value(
                    "Issue",
                    issue_name,
                    issue_updates,
                    update_modified=False,
                )

        work_order.reload()
        if status == "Closed":
            sync_asset_maintenance_history(work_order)
        return name

    hvac_closed_issue = ensure_issue(
        "[Report Demo] HVAC cooling loss",
        hvac_asset,
        "HVAC",
        "High",
    )
    electrical_closed_issue = ensure_issue(
        "[Report Demo] Electrical breaker trip",
        electrical_asset,
        "Electrical",
        "Critical",
    )
    hvac_open_issue = ensure_issue(
        "[Report Demo] Recurring HVAC vibration",
        hvac_asset,
        "HVAC",
        "High",
    )
    dashboard_hvac_issue = ensure_issue(
        "[Dashboard Demo] Overdue HVAC filter replacement",
        hvac_asset,
        "HVAC",
        "High",
    )
    dashboard_electrical_issue = ensure_issue(
        "[Dashboard Demo] Overdue electrical safety check",
        electrical_asset,
        "Electrical",
        "High",
    )
    dashboard_now = frappe.utils.now_datetime()
    dashboard_hvac_actual_start = frappe.utils.add_to_date(
        dashboard_now, hours=-2, as_datetime=True
    )
    dashboard_electrical_actual_start = frappe.utils.add_to_date(
        dashboard_now, hours=-1, as_datetime=True
    )

    work_orders = [
        ensure_work_order(
            "on-time HVAC repair",
            issue_name=hvac_closed_issue,
            technician=hvac_technician,
            planned_start="2026-08-05 08:00:00",
            planned_end="2026-08-05 12:00:00",
            actual_start="2026-08-05 08:30:00",
            actual_end="2026-08-05 11:30:00",
            status="Closed",
            labor_hours=3,
            material_cost=185,
        ),
        ensure_work_order(
            "late electrical repair",
            issue_name=electrical_closed_issue,
            technician=electrical_technician,
            planned_start="2026-08-07 09:00:00",
            planned_end="2026-08-07 12:00:00",
            actual_start="2026-08-07 10:00:00",
            actual_end="2026-08-07 14:00:00",
            status="Closed",
            labor_hours=4,
            material_cost=420,
        ),
        ensure_work_order(
            "overdue recurring HVAC repair",
            issue_name=hvac_open_issue,
            technician=hvac_technician,
            planned_start="2026-08-20 08:00:00",
            planned_end="2026-08-20 11:00:00",
            actual_start="2026-08-20 09:00:00",
            status="Pending",
            material_cost=75,
        ),
        ensure_work_order(
            "on-time preventive HVAC occurrence",
            plan_name="PM-2026-00002",
            occurrence_date="2026-08-10",
            technician=hvac_technician,
            planned_start="2026-08-10 09:00:00",
            planned_end="2026-08-10 11:00:00",
            actual_start="2026-08-10 09:00:00",
            actual_end="2026-08-10 10:45:00",
            status="Closed",
            labor_hours=1.75,
            material_cost=95,
        ),
        ensure_work_order(
            "late preventive electrical occurrence",
            plan_name="PM-2026-00004",
            occurrence_date="2026-08-15",
            technician=electrical_technician,
            planned_start="2026-08-15 09:00:00",
            planned_end="2026-08-15 11:00:00",
            actual_start="2026-08-15 09:30:00",
            actual_end="2026-08-15 12:30:00",
            status="Closed",
            labor_hours=3,
            material_cost=130,
        ),
        ensure_work_order(
            "overdue preventive HVAC occurrence",
            plan_name="PM-2026-00002",
            occurrence_date="2026-08-22",
            technician=hvac_technician,
            planned_start="2026-08-22 09:00:00",
            planned_end="2026-08-22 11:00:00",
            actual_start="2026-08-22 09:30:00",
            status="In Progress",
            material_cost=40,
        ),
        ensure_work_order(
            "dashboard overdue HVAC filter replacement",
            issue_name=dashboard_hvac_issue,
            technician=hvac_technician,
            planned_start="2026-08-23 08:00:00",
            planned_end="2026-08-23 11:00:00",
            actual_start=dashboard_hvac_actual_start,
            status="In Progress",
            material_cost=55,
        ),
        ensure_work_order(
            "dashboard overdue electrical safety check",
            issue_name=dashboard_electrical_issue,
            technician=electrical_technician,
            planned_start="2026-08-24 09:00:00",
            planned_end="2026-08-24 12:00:00",
            actual_start=dashboard_electrical_actual_start,
            status="In Progress",
            material_cost=65,
        ),
    ]


    corrective_demo_specs = [
        (
            "[Dashboard Demo] HVAC refrigerant leak",
            "repeat HVAC refrigerant leak",
            hvac_asset, "HVAC", "Critical", hvac_technician,
            "2026-08-03 08:00:00", "2026-08-03 12:00:00",
            "2026-08-03 08:30:00", "2026-08-03 11:00:00",
            "Closed", 2.5, 210, 1.5,
        ),
        (
            "[Dashboard Demo] HVAC fan belt failure",
            "repeat HVAC fan belt failure",
            hvac_asset, "HVAC", "High", hvac_technician,
            "2026-08-12 08:00:00", "2026-08-12 13:00:00",
            "2026-08-12 08:45:00", "2026-08-12 13:15:00",
            "Closed", 4.5, 160, 2,
        ),
        (
            "[Dashboard Demo] HVAC sensor fault",
            "repeat HVAC sensor fault",
            hvac_asset, "HVAC", "Medium", hvac_technician,
            "2026-08-18 10:00:00", "2026-08-18 12:00:00",
            "2026-08-18 10:30:00", "2026-08-18 11:45:00",
            "Closed", 1.25, 85, 0.75,
        ),
        (
            "[Dashboard Demo] Electrical relay failure",
            "repeat electrical relay failure",
            electrical_asset, "Electrical", "Critical", electrical_technician,
            "2026-08-04 09:00:00", "2026-08-04 12:00:00",
            "2026-08-04 09:15:00", "2026-08-04 11:15:00",
            "Closed", 2, 320, 1,
        ),
        (
            "[Dashboard Demo] Electrical ATS control fault",
            "repeat electrical ATS control fault",
            electrical_asset, "Electrical", "High", electrical_technician,
            "2026-08-16 07:00:00", "2026-08-16 11:00:00",
            "2026-08-16 07:30:00", "2026-08-16 11:00:00",
            "Closed", 3.5, 275, 3,
        ),
        (
            "[Dashboard Demo] Branch pump seal leak",
            "repeat branch pump seal leak",
            branch_asset, "Plumbing", "High", hvac_technician,
            "2026-08-06 08:00:00", "2026-08-06 14:00:00",
            "2026-08-06 08:30:00", "2026-08-06 13:30:00",
            "Closed", 5, 510, 2.5,
        ),
        (
            "[Dashboard Demo] Branch pump pressure loss",
            "repeat branch pump pressure loss",
            branch_asset, "Plumbing", "Medium", hvac_technician,
            "2026-08-21 09:00:00", "2026-08-21 12:00:00",
            "2026-08-21 09:15:00", "2026-08-21 12:00:00",
            "Closed", 2.75, 245, 1.25,
        ),
        (
            "[Dashboard Demo] Critical chiller shutdown",
            "open critical chiller shutdown",
            hvac_asset, "HVAC", "Critical", hvac_technician,
            "2026-08-25 07:00:00", "2026-08-25 10:00:00",
            "2026-08-25 08:15:00", None,
            "In Progress", 0, 90, 0.5,
        ),
        (
            "[Dashboard Demo] Branch plumbing leak",
            "open branch plumbing leak",
            branch_asset, "Plumbing", "Medium", hvac_technician,
            "2026-08-26 13:00:00", "2026-08-26 15:00:00",
            None, None, "Assigned", 0, 20, 0,
        ),
        (
            "[Dashboard Demo] Low ventilation noise",
            "open low ventilation noise",
            branch_asset, "Plumbing", "Low", hvac_technician,
            "2026-08-30 09:00:00", "2026-08-30 12:00:00",
            None, None, "Draft", 0, 0, 0,
        ),
        (
            "[Dashboard Demo] Electrical panel monitoring",
            "open electrical panel monitoring",
            electrical_asset, "Electrical", "Medium", electrical_technician,
            "2026-08-24 09:00:00", "2026-08-24 12:00:00",
            "2026-08-24 10:00:00", None,
            "Pending", 0, 35, 2,
        ),
    ]

    extra_issue_names = []
    extra_response_hours = []
    for (
        subject, marker, asset, category, priority, technician,
        planned_start, planned_end, actual_start, actual_end,
        status, labor_hours, material_cost, response_time,
    ) in corrective_demo_specs:
        issue_name = ensure_issue(subject, asset, category, priority)
        extra_issue_names.append(issue_name)
        work_orders.append(
            ensure_work_order(
                marker,
                issue_name=issue_name,
                technician=technician,
                planned_start=planned_start,
                planned_end=planned_end,
                actual_start=actual_start,
                actual_end=actual_end,
                status=status,
                labor_hours=labor_hours,
                material_cost=material_cost,
            )
        )
        extra_response_hours.append(response_time)

    preventive_demo_specs = [
        (
            "second on-time preventive HVAC occurrence",
            "PM-2026-00002", "2026-08-12", hvac_technician,
            "2026-08-12 14:00:00", "2026-08-12 16:00:00",
            "2026-08-12 14:15:00", "2026-08-12 15:45:00",
            "Closed", 1.5, 60, 1,
        ),
        (
            "on-time preventive electrical occurrence",
            "PM-2026-00004", "2026-08-25", electrical_technician,
            "2026-08-25 08:00:00", "2026-08-25 10:00:00",
            "2026-08-25 08:30:00", "2026-08-25 10:00:00",
            "Closed", 1.5, 80, 1.5,
        ),
        (
            "on-time preventive branch pump occurrence",
            branch_plan_name, "2026-08-09", hvac_technician,
            "2026-08-09 08:00:00", "2026-08-09 11:00:00",
            "2026-08-09 08:15:00", "2026-08-09 10:15:00",
            "Closed", 2, 110, 1,
        ),
        (
            "late preventive branch pump occurrence",
            branch_plan_name, "2026-08-18", hvac_technician,
            "2026-08-18 08:00:00", "2026-08-18 10:00:00",
            "2026-08-18 08:30:00", "2026-08-18 12:00:00",
            "Closed", 3.5, 145, 2,
        ),
        (
            "overdue preventive branch pump occurrence",
            branch_plan_name, "2026-08-26", hvac_technician,
            "2026-08-26 08:00:00", "2026-08-26 11:00:00",
            "2026-08-26 09:00:00", None,
            "In Progress", 0, 50, 1,
        ),
    ]

    for (
        marker, plan_name, occurrence_date, technician,
        planned_start, planned_end, actual_start, actual_end,
        status, labor_hours, material_cost, response_time,
    ) in preventive_demo_specs:
        work_orders.append(
            ensure_work_order(
                marker,
                plan_name=plan_name,
                occurrence_date=occurrence_date,
                technician=technician,
                planned_start=planned_start,
                planned_end=planned_end,
                actual_start=actual_start,
                actual_end=actual_end,
                status=status,
                labor_hours=labor_hours,
                material_cost=material_cost,
            )
        )
        extra_response_hours.append(response_time)

    response_hours = (
        2, 4, 3, 1, 2.5, 2, 3, 5, *extra_response_hours
    )
    for work_order_name, hours in zip(work_orders, response_hours):
        actual_start = frappe.db.get_value(
            "Facility Work Order", work_order_name, "actual_start"
        )
        if actual_start:
            creation = frappe.utils.add_to_date(
                actual_start,
                hours=-hours,
                as_datetime=True,
            )
            frappe.db.set_value(
                "Facility Work Order",
                work_order_name,
                "creation",
                creation,
                update_modified=False,
            )

    def ensure_completed_inspection(
        marker,
        technician,
        asset,
        category,
        completed_on,
    ):
        name = frappe.db.get_value(
            "Facility Inspection",
            {"notes": marker},
            "name",
        )
        if not name:
            inspection = frappe.get_doc(
                {
                    "doctype": "Facility Inspection",
                    "source_type": "Manual",
                    "inspection_template": (
                        "HVAC Work Completion Inspection"
                    ),
                    "company": company,
                    "facility_location": asset.custom_asset_location,
                    "asset": asset.name,
                    "category": category,
                    "inspector": technician,
                    "planned_date": completed_on[:10],
                    "notes": marker,
                }
            ).insert(ignore_permissions=True)
            name = inspection.name

        inspection = frappe.get_doc("Facility Inspection", name)
        for result in inspection.results:
            result.result = "Pass"
            result.comments = "[Report Demo] Check completed successfully."
        inspection.save(ignore_permissions=True)
        frappe.db.set_value(
            "Facility Inspection",
            name,
            {
                "status": "Completed",
                "overall_result": "Pass",
                "started_on": completed_on,
                "completed_on": completed_on,
            },
            update_modified=False,
        )
        return name

    inspections = [
        ensure_completed_inspection(
            "[Report Demo] HVAC completion inspection",
            hvac_technician,
            hvac_asset,
            "HVAC",
            "2026-08-10 11:00:00",
        ),
        ensure_completed_inspection(
            "[Report Demo] Electrical completion inspection",
            electrical_technician,
            electrical_asset,
            "Electrical",
            "2026-08-15 13:00:00",
        ),
    ]

    frappe.db.commit()
    frappe.clear_cache()
    return {
        "company": company,
        "issues": [
            hvac_closed_issue,
            electrical_closed_issue,
            hvac_open_issue,
            dashboard_hvac_issue,
            dashboard_electrical_issue,
            *extra_issue_names,
        ],
        "branch_asset": branch_asset.name,
        "branch_plan": branch_plan_name,
        "work_orders": work_orders,
        "inspections": inspections,
    }



def verify_report_demo_data():
    """Run all required reports against the report demo period."""
    from frappe.desk.query_report import run

    company = "Ag's Industries"
    common = {
        "from_date": "2026-08-01",
        "to_date": "2026-08-31",
        "company": company,
    }
    filters_by_report = {
        "Maintenance Request Report": {
            **common,
            "status": "All",
            "priority": "All",
        },
        "Work Order Report": {
            **common,
            "work_order_type": "All",
            "status": "All",
            "priority": "All",
            "assignment_type": "All",
        },
        "Preventive Maintenance Report": {
            **common,
            "is_active": "All",
            "frequency": "All",
        },
        "Asset Maintenance History": {
            **common,
            "work_order_type": "All",
            "priority": "All",
        },
        "Technician Performance Report": {
            **common,
            "specialization": "All",
            "employee_status": "Active",
        },
        "Maintenance Cost Report": {
            **common,
            "work_order_type": "All",
            "group_by": "Site",
        },
    }

    frappe.set_user("Administrator")
    counts = {}
    for report_name, filters in filters_by_report.items():
        output = run(
            report_name=report_name,
            filters=filters,
            ignore_prepared_report=True,
        )
        counts[report_name] = len(output.get("result") or [])
    return counts

def verify_dashboard_demo_data():
    """Return the live values used by all Facility Management widgets."""
    from frappe.desk.doctype.dashboard_chart.dashboard_chart import (
        get as get_dashboard_chart,
    )
    from frappe.desk.query_report import run

    from cafm.dashboard import (
        get_average_resolution_time,
        get_average_response_time,
        get_overdue_work_orders,
    )

    common_filters = {
        "from_date": "2026-08-01",
        "to_date": "2026-08-31",
        "company": "Ag's Industries",
    }
    report_filters = {
        "Preventive Maintenance Compliance": {
            **common_filters,
            "is_active": "All",
            "frequency": "All",
        },
        "Maintenance Cost by Site and Building": {
            **common_filters,
            "work_order_type": "All",
            "group_by": "Site",
        },
    }
    report_names = {
        "Preventive Maintenance Compliance": "Preventive Maintenance Report",
        "Maintenance Cost by Site and Building": "Maintenance Cost Report",
    }

    report_charts = {}
    for chart_name, filters in report_filters.items():
        output = run(
            report_name=report_names[chart_name],
            filters=filters,
            ignore_prepared_report=True,
        )
        report_charts[chart_name] = (output.get("chart") or {}).get("data")

    group_charts = {}
    for chart_name in (
        "Asset Downtime",
        "Top Recurring Asset Failures",
        "Work Order By Category",
        "Work Orders By Priority",
    ):
        group_charts[chart_name] = get_dashboard_chart(
            chart_name=chart_name,
            refresh=1,
        )

    return {
        "cards": {
            "Open Maintenance Requests": frappe.db.count(
                "Issue",
                {
                    "custom_issue_status": [
                        "not in",
                        ["Resolved", "Closed", "Rejected"],
                    ]
                },
            ),
            "Overdue Work Orders": get_overdue_work_orders(),
            "Average Response Time": get_average_response_time(),
            "Average Resolution Time": get_average_resolution_time(),
        },
        "group_charts": group_charts,
        "report_charts": report_charts,
    }



def seed_maintenance_cost_chart_demo():
    """Add idempotent grouped-bar demo data for the maintenance-cost chart."""
    seed_report_demo_data()
    frappe.set_user("Administrator")

    company = "Ag's Industries"
    requester = frappe.db.get_value(
        "Employee",
        {"user_id": "cafm.requester@example.com", "status": "Active"},
        "name",
    )
    technician = frappe.db.get_value(
        "Employee",
        {"user_id": "cafm.hvac.technician@example.com", "status": "Active"},
        "name",
    )
    if not requester or not technician:
        frappe.throw("CAFM requester and technician demo users are required.")

    def ensure_location(site, building_id, building_name):
        if not frappe.db.exists("Building", building_id):
            frappe.get_doc(
                {
                    "doctype": "Building",
                    "site": site,
                    "building_name": building_name,
                    "building_id": building_id,
                    "total_floors": 1,
                    "status": "Active",
                    "building_type": "Office",
                    "gross_area": 900,
                }
            ).insert(ignore_permissions=True)

        floor_name = frappe.db.get_value(
            "Floor",
            {"building": building_id, "floor_level": 0},
            "name",
        )
        if not floor_name:
            floor_name = frappe.get_doc(
                {
                    "doctype": "Floor",
                    "building": building_id,
                    "floor_name": "Ground Floor",
                    "floor_level": 0,
                    "floor_type": "Workspace",
                    "status": "Active",
                    "floor_area": 900,
                }
            ).insert(ignore_permissions=True).name

        room_name = frappe.db.get_value(
            "Room",
            {"floor": floor_name, "room_name": "Maintenance Room"},
            "name",
        )
        if not room_name:
            room_name = frappe.get_doc(
                {
                    "doctype": "Room",
                    "floor": floor_name,
                    "room_name": "Maintenance Room",
                    "room_id": "MAINT",
                    "room_type": "Storage",
                    "description": "Maintenance-cost chart demonstration room.",
                }
            ).insert(ignore_permissions=True).name

        location_name = frappe.db.get_value(
            "Facility Location",
            {
                "site": site,
                "building": building_id,
                "floor": floor_name,
                "room": room_name,
            },
            "name",
        )
        if not location_name:
            location_name = frappe.get_doc(
                {
                    "doctype": "Facility Location",
                    "site": site,
                    "building": building_id,
                    "floor": floor_name,
                    "room": room_name,
                }
            ).insert(ignore_permissions=True).name
        return location_name

    def ensure_closed_work_order(subject, location, cost, start, end):
        issue_name = frappe.db.get_value(
            "Issue",
            {"company": company, "subject": subject},
            "name",
        )
        if not issue_name:
            issue_name = frappe.get_doc(
                {
                    "doctype": "Issue",
                    "subject": subject,
                    "description": "Maintenance-cost grouped-bar demonstration.",
                    "company": company,
                    "custom_requester": requester,
                    "raised_by": "cafm.requester@example.com",
                    "custom_facility_location": location,
                    "issue_type": "HVAC",
                    "priority": "Medium",
                }
            ).insert(ignore_permissions=True).name

        work_order_name = frappe.db.get_value(
            "Facility Work Order",
            {"maintenance_request": issue_name},
            "name",
        )
        if not work_order_name:
            work_order = frappe.get_doc(
                {
                    "doctype": "Facility Work Order",
                    "work_order_type": "Corrective",
                    "maintenance_request": issue_name,
                    "assignment_type": "Internal Technician",
                    "technician": technician,
                    "planned_start": start,
                    "planned_end": end,
                }
            ).insert(ignore_permissions=True)
            work_order_name = work_order.name

        frappe.db.set_value(
            "Facility Work Order",
            work_order_name,
            {
                "facility_location": location,
                "actual_start": start,
                "actual_end": end,
                "material_cost": cost,
                "resolution_summary": (
                    "[Chart Demo] Maintenance completed and cost recorded."
                ),
                "work_order_status": "Closed",
                "closed_by": "Administrator",
                "closed_on": end,
            },
            update_modified=False,
        )
        frappe.db.set_value(
            "Issue",
            issue_name,
            {
                "custom_issue_status": "Closed",
                "status": "Closed",
                "resolution_details": (
                    "[Chart Demo] Completed through the linked work order."
                ),
            },
            update_modified=False,
        )
        return work_order_name

    specs = (
        (
            "Ag's Head Quarters",
            "CAFM-HQ-ANNEX",
            "Administration Annex",
            "[Chart Demo] Administration annex air-handler service",
            680,
            "2026-08-11 09:00:00",
            "2026-08-11 12:00:00",
        ),
        (
            "CAFM Demo Regional Branch",
            "CAFM-BR-SVC",
            "Customer Service Center",
            "[Chart Demo] Customer service center ventilation repair",
            390,
            "2026-08-19 10:00:00",
            "2026-08-19 13:00:00",
        ),
    )

    created = []
    for site, building_id, building_name, subject, cost, start, end in specs:
        if not frappe.db.exists("Site", site):
            frappe.throw(f"Required demo Site does not exist: {site}")
        location = ensure_location(site, building_id, building_name)
        created.append(
            ensure_closed_work_order(subject, location, cost, start, end)
        )

    frappe.db.commit()
    return {
        "work_orders": created,
        "chart": verify_dashboard_demo_data()["report_charts"][
            "Maintenance Cost by Site and Building"
        ],
    }

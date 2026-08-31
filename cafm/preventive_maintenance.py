import frappe
from frappe import _
from frappe.utils import add_days, add_months, getdate, nowdate


MAX_OCCURRENCES_PER_PLAN_PER_RUN = 100


def get_next_due_date(occurrence_date, frequency):
    occurrence_date = getdate(occurrence_date)
    increments = {
        "Daily": lambda value: add_days(value, 1),
        "Weekly": lambda value: add_days(value, 7),
        "Monthly": lambda value: add_months(value, 1),
        "Quarterly": lambda value: add_months(value, 3),
        "Yearly": lambda value: add_months(value, 12),
    }
    if frequency not in increments:
        frappe.throw(_("Unsupported preventive frequency: {0}").format(frequency))
    return getdate(increments[frequency](occurrence_date))


def get_occurrence_key(plan_name, occurrence_date):
    return f"{plan_name}::{getdate(occurrence_date)}"


def generate_occurrence(plan, occurrence_date):
    if isinstance(plan, str):
        plan = frappe.get_doc("Preventive Maintenance Plan", plan)

    occurrence_date = getdate(occurrence_date)
    occurrence_key = get_occurrence_key(plan.name, occurrence_date)
    existing = frappe.db.get_value(
        "Facility Work Order",
        {"preventive_occurrence_key": occurrence_key},
        "name",
    )

    if existing:
        advance_plan(plan, occurrence_date, existing)
        return existing

    work_order = frappe.new_doc("Facility Work Order")
    work_order.work_order_type = "Preventive"
    work_order.preventive_maintenance_plan = plan.name
    work_order.scheduled_occurrence_date = occurrence_date

    try:
        work_order.insert(ignore_permissions=True)
        work_order_name = work_order.name
    except (frappe.DuplicateEntryError, frappe.ValidationError):
        existing = frappe.db.get_value(
            "Facility Work Order",
            {"preventive_occurrence_key": occurrence_key},
            "name",
        )
        if not existing:
            raise
        work_order_name = existing

    advance_plan(plan, occurrence_date, work_order_name)
    return work_order_name


def advance_plan(plan, occurrence_date, work_order_name):
    current_due_date = getdate(
        frappe.db.get_value(
            "Preventive Maintenance Plan",
            plan.name,
            "next_due_date",
        )
        or plan.next_due_date
    )

    updates = {
        "last_generated_date": getdate(occurrence_date),
        "last_work_order": work_order_name,
    }
    if current_due_date <= getdate(occurrence_date):
        updates["next_due_date"] = get_next_due_date(
            occurrence_date,
            plan.frequency,
        )

    frappe.db.set_value(
        "Preventive Maintenance Plan",
        plan.name,
        updates,
        update_modified=True,
    )
    for fieldname, value in updates.items():
        plan.set(fieldname, value)


def generate_preventive_work_orders(reference_date=None, plan_names=None):
    reference_date = getdate(reference_date or nowdate())
    generated = []

    filters = {"is_active": 1}
    if plan_names:
        filters["name"] = ["in", plan_names]

    plans = frappe.get_all(
        "Preventive Maintenance Plan",
        filters=filters,
        fields=["name"],
        order_by="next_due_date asc",
    )

    for row in plans:
        try:
            plan = frappe.get_doc("Preventive Maintenance Plan", row.name)
            count = 0
            horizon = getdate(
                add_days(reference_date, plan.generate_before_days or 0)
            )

            while (
                plan.is_active
                and plan.next_due_date
                and getdate(plan.next_due_date) <= horizon
            ):
                if count >= MAX_OCCURRENCES_PER_PLAN_PER_RUN:
                    frappe.log_error(
                        title="Preventive Maintenance Generation Limit",
                        message=(
                            f"Plan {plan.name} reached "
                            f"{MAX_OCCURRENCES_PER_PLAN_PER_RUN} occurrences "
                            "in one scheduler run."
                        ),
                    )
                    break

                occurrence_date = getdate(plan.next_due_date)
                work_order_name = generate_occurrence(
                    plan,
                    occurrence_date,
                )
                generated.append(work_order_name)
                count += 1
                plan.next_due_date = frappe.db.get_value(
                    "Preventive Maintenance Plan",
                    plan.name,
                    "next_due_date",
                )
        except Exception:
            if frappe.flags.in_test:
                raise
            frappe.log_error(
                title=f"Preventive Maintenance Plan {row.name}",
                message=frappe.get_traceback(),
            )

    return generated

import frappe
from frappe.utils import add_days, getdate, nowdate

from cafm.preventive_maintenance import get_next_due_date


MAX_OCCURRENCES_PER_SCHEDULE_PER_RUN = 100


def get_inspection_occurrence_key(schedule_name, occurrence_date):
    return f"{schedule_name}::{getdate(occurrence_date)}"


def generate_inspection_occurrence(schedule, occurrence_date):
    if isinstance(schedule, str):
        schedule = frappe.get_doc(
            "Facility Inspection Schedule",
            schedule,
        )

    occurrence_date = getdate(occurrence_date)
    occurrence_key = get_inspection_occurrence_key(
        schedule.name,
        occurrence_date,
    )
    existing = frappe.db.get_value(
        "Facility Inspection",
        {"occurrence_key": occurrence_key},
        "name",
    )
    if existing:
        advance_inspection_schedule(schedule, occurrence_date, existing)
        return existing

    inspection = frappe.new_doc("Facility Inspection")
    inspection.source_type = "Scheduled Inspection"
    inspection.inspection_schedule = schedule.name
    inspection.occurrence_date = occurrence_date
    inspection.occurrence_key = occurrence_key
    inspection.planned_date = occurrence_date

    try:
        inspection.insert(ignore_permissions=True)
        inspection_name = inspection.name
    except (frappe.DuplicateEntryError, frappe.ValidationError):
        existing = frappe.db.get_value(
            "Facility Inspection",
            {"occurrence_key": occurrence_key},
            "name",
        )
        if not existing:
            raise
        inspection_name = existing

    advance_inspection_schedule(
        schedule,
        occurrence_date,
        inspection_name,
    )
    return inspection_name


def advance_inspection_schedule(
    schedule,
    occurrence_date,
    inspection_name,
):
    current_due_date = getdate(
        frappe.db.get_value(
            "Facility Inspection Schedule",
            schedule.name,
            "next_due_date",
        )
        or schedule.next_due_date
    )
    updates = {
        "last_generated_date": getdate(occurrence_date),
        "last_inspection": inspection_name,
    }
    if current_due_date <= getdate(occurrence_date):
        updates["next_due_date"] = get_next_due_date(
            occurrence_date,
            schedule.frequency,
        )

    frappe.db.set_value(
        "Facility Inspection Schedule",
        schedule.name,
        updates,
        update_modified=True,
    )
    for fieldname, value in updates.items():
        schedule.set(fieldname, value)


def generate_scheduled_inspections(
    reference_date=None,
    schedule_names=None,
):
    reference_date = getdate(reference_date or nowdate())
    generated = []
    filters = {"is_active": 1}
    if schedule_names:
        filters["name"] = ["in", schedule_names]

    schedules = frappe.get_all(
        "Facility Inspection Schedule",
        filters=filters,
        fields=["name"],
        order_by="next_due_date asc",
    )
    for row in schedules:
        try:
            schedule = frappe.get_doc(
                "Facility Inspection Schedule",
                row.name,
            )
            count = 0
            horizon = getdate(
                add_days(
                    reference_date,
                    schedule.generate_before_days or 0,
                )
            )
            while (
                schedule.is_active
                and schedule.next_due_date
                and getdate(schedule.next_due_date) <= horizon
            ):
                if count >= MAX_OCCURRENCES_PER_SCHEDULE_PER_RUN:
                    frappe.log_error(
                        title="Inspection Schedule Generation Limit",
                        message=(
                            f"Schedule {schedule.name} reached "
                            f"{MAX_OCCURRENCES_PER_SCHEDULE_PER_RUN} "
                            "occurrences in one scheduler run."
                        ),
                    )
                    break

                occurrence_date = getdate(schedule.next_due_date)
                generated.append(
                    generate_inspection_occurrence(
                        schedule,
                        occurrence_date,
                    )
                )
                count += 1
                schedule.next_due_date = frappe.db.get_value(
                    "Facility Inspection Schedule",
                    schedule.name,
                    "next_due_date",
                )
        except Exception:
            if frappe.flags.in_test:
                raise
            frappe.log_error(
                title=f"Facility Inspection Schedule {row.name}",
                message=frappe.get_traceback(),
            )

    return generated

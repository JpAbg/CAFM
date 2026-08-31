from cafm.assignment import refresh_all_assignment_availability
from cafm.inspections import generate_scheduled_inspections
from cafm.notifications import (
    notify_overdue_work_orders,
    send_daily_overdue_summary,
    send_upcoming_preventive_reminders,
)
from cafm.preventive_maintenance import generate_preventive_work_orders


def daily():
    reminders = send_upcoming_preventive_reminders()
    work_orders = generate_preventive_work_orders()
    inspections = generate_scheduled_inspections()
    overdue_summary_count = send_daily_overdue_summary()
    refresh_all_assignment_availability()
    return {
        "preventive_reminders": reminders,
        "work_orders": work_orders,
        "inspections": inspections,
        "overdue_summary_count": overdue_summary_count,
    }


def hourly():
    return {
        "overdue_work_orders": notify_overdue_work_orders(),
    }

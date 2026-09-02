import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime, time_diff_in_hours


def _count_work_orders(filters):
    result = frappe.get_list(
        "Facility Work Order",
        filters=filters,
        fields=["count(name) as value"],
        order_by=None,
    )
    return cint(result[0].value) if result else 0


@frappe.whitelist()
def get_overdue_work_orders(filters=None):
    """Count open work orders that became overdue less than four hours ago."""
    return _get_overdue_bucket_card(
        minimum_hours=0,
        maximum_hours=4,
        label=_("Work Orders"),
    )


def _get_overdue_bucket_card(minimum_hours, maximum_hours, label):
    current_time = now_datetime()
    latest_due_time = add_to_date(current_time, hours=-minimum_hours)
    work_order_filters = [
        [
            "Facility Work Order",
            "work_order_status",
            "not in",
            ["Resolved", "Closed", "Cancelled"],
        ],
        ["Facility Work Order", "planned_end", "is", "set"],
        ["Facility Work Order", "planned_end", "<=", latest_due_time],
    ]

    if maximum_hours is not None:
        earliest_due_time = add_to_date(current_time, hours=-maximum_hours)
        work_order_filters.append(
            ["Facility Work Order", "planned_end", ">", earliest_due_time]
        )

    value = _count_work_orders(work_order_filters)
    route_start = (
        str(earliest_due_time)
        if maximum_hours is not None
        else "1900-01-01 00:00:00"
    )

    return {
        "value": value,
        "fieldtype": "Int",
        "route": ["List", "Facility Work Order"],
        "route_options": {
            "work_order_status": [
                "not in",
                ["Resolved", "Closed", "Cancelled"],
            ],
            "planned_end": [
                "between",
                [route_start, str(latest_due_time)],
            ],
        },
        "message": _("{0} in this overdue time band.").format(label),
    }


@frappe.whitelist()
def get_delayed_work_orders(filters=None):
    """Count open work orders that are overdue from four to under 24 hours."""
    return _get_overdue_bucket_card(
        minimum_hours=4,
        maximum_hours=24,
        label=_("Work Orders"),
    )


@frappe.whitelist()
def get_escalated_work_orders(filters=None):
    """Count open work orders that are overdue by one day or more."""
    return _get_overdue_bucket_card(
        minimum_hours=24,
        maximum_hours=None,
        label=_("Work Orders"),
    )


@frappe.whitelist()
def get_average_response_time(filters=None):
    """Return average hours from work-order creation to actual start."""
    work_orders = frappe.get_list(
        "Facility Work Order",
        filters=[["Facility Work Order", "actual_start", "is", "set"]],
        fields=["creation", "actual_start"],
        order_by=None,
        limit_page_length=0,
    )
    response_hours = [
        time_diff_in_hours(row.actual_start, row.creation)
        for row in work_orders
        if row.actual_start and row.creation and row.actual_start >= row.creation
    ]
    value = (
        round(sum(response_hours) / len(response_hours), 2)
        if response_hours
        else 0
    )

    return {
        "value": f"{value:.2f} hrs",
        "fieldtype": "Data",
        "route": ["List", "Facility Work Order"],
        "route_options": {"actual_start": ["is", "set"]},
    }


@frappe.whitelist()
def get_average_resolution_time(filters=None):
    """Return average hours from actual start to actual end."""
    work_orders = frappe.get_list(
        "Facility Work Order",
        filters=[
            ["Facility Work Order", "actual_start", "is", "set"],
            ["Facility Work Order", "actual_end", "is", "set"],
        ],
        fields=["actual_start", "actual_end"],
        order_by=None,
        limit_page_length=0,
    )
    resolution_hours = [
        time_diff_in_hours(row.actual_end, row.actual_start)
        for row in work_orders
        if row.actual_start and row.actual_end and row.actual_end >= row.actual_start
    ]
    value = (
        round(sum(resolution_hours) / len(resolution_hours), 2)
        if resolution_hours
        else 0
    )

    return {
        "value": f"{value:.2f} hrs",
        "fieldtype": "Data",
        "route": ["List", "Facility Work Order"],
        "route_options": {"actual_end": ["is", "set"]},
    }


SLA_DASHBOARD_ROLES = ("Facility Manager", "Facility Coordinator")


def _require_sla_dashboard_access():
    allowed_roles = set(SLA_DASHBOARD_ROLES) | {"System Manager"}
    if not allowed_roles.intersection(frappe.get_roles(frappe.session.user)):
        frappe.throw(_("Not permitted."), frappe.PermissionError)


def _get_sla_status_card(status):
    _require_sla_dashboard_access()
    value = _count_work_orders(
        [
            ["Facility Work Order", "sla_policy", "is", "set"],
            ["Facility Work Order", "sla_status", "=", status],
        ]
    )
    return {
        "value": value,
        "fieldtype": "Int",
        "route": ["List", "Facility Work Order"],
        "route_options": {"sla_policy": ["is", "set"], "sla_status": status},
        "message": _("Work orders with SLA status: {0}.").format(status),
    }


@frappe.whitelist()
def get_on_track_work_orders(filters=None):
    return _get_sla_status_card("On Track")


@frappe.whitelist()
def get_response_breached_work_orders(filters=None):
    return _get_sla_status_card("Response Breached")


@frappe.whitelist()
def get_resolution_breached_work_orders(filters=None):
    return _get_sla_status_card("Resolution Breached")


@frappe.whitelist()
def get_sla_met_work_orders(filters=None):
    return _get_sla_status_card("Met")



UTILITY_DASHBOARD_ROLES = ("Facility Manager", "Facility Coordinator")


def _require_utility_dashboard_access():
    allowed_roles = set(UTILITY_DASHBOARD_ROLES) | {"System Manager"}
    if not allowed_roles.intersection(frappe.get_roles(frappe.session.user)):
        frappe.throw(_("Not permitted."), frappe.PermissionError)


def _utility_month_bounds(month_start):
    month_end = add_to_date(month_start, months=1, days=-1)
    return str(month_start), str(month_end)


def _utility_month_start(offset=0):
    current = now_datetime().date().replace(day=1)
    return add_to_date(current, months=offset)


def _utility_reading_filters(from_date, to_date):
    return [
        ["Utility Reading", "reading_date", "between", [str(from_date), str(to_date)]],
    ]


@frappe.whitelist()
def get_utility_meters_reported(filters=None):
    _require_utility_dashboard_access()
    from_date, to_date = _utility_month_bounds(_utility_month_start())
    meters = frappe.get_all(
        "Utility Reading",
        filters=_utility_reading_filters(from_date, to_date),
        pluck="utility_meter",
    )
    return {
        "value": len(set(meters)),
        "fieldtype": "Int",
        "route": ["List", "Utility Reading"],
        "route_options": {"reading_date": ["between", [from_date, to_date]]},
        "message": _("Meters with a reading this month."),
    }


@frappe.whitelist()
def get_monthly_utility_cost(filters=None):
    _require_utility_dashboard_access()
    from_date, to_date = _utility_month_bounds(_utility_month_start())
    value = frappe.db.get_value(
        "Utility Reading",
        _utility_reading_filters(from_date, to_date),
        "sum(cost)",
    ) or 0
    return {
        "value": value,
        "fieldtype": "Currency",
        "route": ["List", "Utility Reading"],
        "route_options": {"reading_date": ["between", [from_date, to_date]]},
        "message": _("Estimated utility cost this month."),
    }


@frappe.whitelist()
def get_utility_usage_change(filters=None):
    _require_utility_dashboard_access()
    current_start = _utility_month_start()
    current_from, current_to = _utility_month_bounds(current_start)
    previous_from, previous_to = _utility_month_bounds(_utility_month_start(-1))
    current = frappe.db.get_value(
        "Utility Reading",
        _utility_reading_filters(current_from, current_to),
        "sum(consumption)",
    ) or 0
    previous = frappe.db.get_value(
        "Utility Reading",
        _utility_reading_filters(previous_from, previous_to),
        "sum(consumption)",
    ) or 0
    if not previous:
        return {
            "value": 0,
            "fieldtype": "Percent",
            "route": ["query-report", "Utility Consumption Report"],
            "message": _("No prior-month usage data is available."),
        }
    return {
        "value": round(((current - previous) / previous) * 100, 1),
        "fieldtype": "Percent",
        "route": ["query-report", "Utility Consumption Report"],
        "message": _("Usage compared with the previous month."),
    }

@frappe.whitelist()
def get_peak_demand(filters=None):
    value = frappe.db.get_value("Utility Demand Reading", {}, "max(demand_value)") or 0
    return {"value": value, "fieldtype": "Float", "route": ["List","Utility Demand Reading"], "message": _("Highest recorded demand in kW.")}


@frappe.whitelist()
def get_peak_demand(filters=None):
    value = frappe.db.get_value("Utility Demand Reading", {}, "max(demand_value)") or 0
    return {"value": "{0:g} kW".format(value), "fieldtype": "Data", "route": ["List", "Utility Demand Reading"], "message": _("Highest recorded demand.")}


@frappe.whitelist()
def get_monthly_carbon(filters=None):
    value = frappe.db.get_value("Utility Reading", {}, "sum(carbon_emissions)") or 0
    return {"value": str(round(value, 1)) + " kg CO2e", "fieldtype": "Data", "route": ["List", "Utility Reading"]}

@frappe.whitelist()
def get_forecast_cost(filters=None):
    forecast = get_utility_forecast()
    return {"value": "$" + str(round(forecast["forecast_cost"], 2)), "fieldtype": "Data", "route": ["List", "Utility Reading"]}


@frappe.whitelist()
def get_forecast_cost(filters=None):
    from cafm.utilities import get_utility_forecast
    forecast = get_utility_forecast()
    return {"value": "$" + str(round(forecast["forecast_cost"], 2)), "fieldtype": "Data", "route": ["List", "Utility Reading"]}


@frappe.whitelist()
def get_forecast_cost(filters=None):
    from cafm.utilities import get_utility_forecast
    return {"value": get_utility_forecast()["forecast_cost"], "fieldtype": "Currency", "currency": "USD", "route": ["List", "Utility Reading"]}


def _get_peak_usage(utility_type, unit):
    _require_utility_dashboard_access()
    value = frappe.db.get_value(
        "Utility Reading",
        {"utility_type": utility_type, "is_opening_reading": 0},
        "max(consumption)",
    ) or 0
    return {
        "value": "{0:g} {1}".format(value, unit),
        "fieldtype": "Data",
        "route": ["List", "Utility Reading"],
        "route_options": {"utility_type": utility_type, "is_opening_reading": 0},
        "message": _("Highest recorded usage for {0}.").format(utility_type),
    }


@frappe.whitelist()
def get_peak_electricity_usage(filters=None):
    return _get_peak_usage("Electricity", "kWh")


@frappe.whitelist()
def get_peak_water_usage(filters=None):
    return _get_peak_usage("Water", "m3")


@frappe.whitelist()
def get_peak_natural_gas_usage(filters=None):
    return _get_peak_usage("Natural Gas", "GJ")


@frappe.whitelist()
def get_peak_fuel_usage(filters=None):
    return _get_peak_usage("Fuel", "Litres")

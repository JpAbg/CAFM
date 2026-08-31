import frappe
from frappe import _
from frappe.utils import getdate, nowdate


ACTIVE_WORK_ORDER_STATUSES = (
    "Assigned",
    "In Progress",
    "Pending",
    "Resolved",
)


def get_service_categories(parenttype, parent, parentfield):
    return set(
        frappe.get_all(
            "Facility Service Category",
            filters={
                "parenttype": parenttype,
                "parent": parent,
                "parentfield": parentfield,
            },
            pluck="service_category",
        )
    )


def get_active_work_order_count(fieldname, value, exclude=None):
    filters = {
        fieldname: value,
        "work_order_status": ["in", ACTIVE_WORK_ORDER_STATUSES],
    }
    if exclude:
        filters["name"] = ["!=", exclude]
    return frappe.db.count("Facility Work Order", filters)


def employee_is_on_leave(employee):
    return bool(
        frappe.db.exists(
            "Leave Application",
            {
                "employee": employee,
                "status": "Approved",
                "docstatus": 1,
                "from_date": ["<=", nowdate()],
                "to_date": [">=", nowdate()],
            },
        )
    )


def calculate_employee_availability(employee):
    if isinstance(employee, str):
        employee = frappe.get_doc("Employee", employee)

    if employee.status != "Active":
        return "Inactive"
    if employee_is_on_leave(employee.name):
        return "On Leave"

    statuses = frappe.get_all(
        "Facility Work Order",
        filters={
            "technician": employee.name,
            "work_order_status": ["in", ACTIVE_WORK_ORDER_STATUSES],
        },
        pluck="work_order_status",
    )
    if any(status in ("In Progress", "Pending") for status in statuses):
        return "Busy"
    if statuses:
        return "Assigned"
    return "Available"


def calculate_provider_availability(provider):
    if isinstance(provider, str):
        provider = frappe.get_doc("Facility Service Provider", provider)

    if provider.status != "Active":
        return "Inactive"

    if provider.is_new():
        return "Available"

    statuses = frappe.get_all(
        "Facility Work Order",
        filters={
            "vendor": provider.name,
            "work_order_status": ["in", ACTIVE_WORK_ORDER_STATUSES],
        },
        pluck="work_order_status",
    )
    if any(status in ("In Progress", "Pending") for status in statuses):
        return "Busy"
    if statuses:
        return "Assigned"
    return "Available"


def validate_internal_technician(
    employee_name,
    category=None,
    work_order=None,
    check_capacity=True,
):
    employee = frappe.get_doc("Employee", employee_name)
    if not employee.custom_is_facility_technician:
        frappe.throw(
            _("The selected Employee is not enabled as a Facility Technician.")
        )
    if employee.status != "Active":
        frappe.throw(_("Only an active Employee can be assigned."))
    if not employee.user_id:
        frappe.throw(_("The technician must be linked to a User account."))
    user_roles = frappe.get_doc("User", employee.user_id).roles
    if not any(row.role == "Technician" for row in user_roles):
        frappe.throw(
            _("The technician's User account must have the Technician role.")
        )

    availability = calculate_employee_availability(employee)
    if availability in ("Inactive", "On Leave"):
        frappe.throw(
            _("Technician {0} is currently {1}.").format(
                employee.employee_name,
                availability,
            )
        )

    categories = get_service_categories(
        "Employee",
        employee.name,
        "custom_service_categories",
    )
    if categories and category and category not in categories:
        frappe.throw(
            _("The technician is not configured for service category {0}.").format(
                category
            )
        )

    maximum = employee.custom_max_active_work_orders or 0
    if check_capacity and maximum:
        active_count = get_active_work_order_count(
            "technician",
            employee.name,
            exclude=work_order,
        )
        if active_count >= maximum:
            frappe.throw(
                _("The technician has reached the active Work Order limit.")
            )
    return employee


def validate_external_provider(provider_name, category=None, work_order=None):
    provider = frappe.get_doc("Facility Service Provider", provider_name)
    if provider.status != "Active":
        frappe.throw(_("Only an active Service Provider can be assigned."))

    supplier_disabled = frappe.db.get_value(
        "Supplier", provider.supplier, "disabled"
    )
    if supplier_disabled:
        frappe.throw(_("The Service Provider's Supplier is disabled."))

    categories = get_service_categories(
        "Facility Service Provider",
        provider.name,
        "service_categories",
    )
    if categories and category and category not in categories:
        frappe.throw(
            _("The Service Provider does not support category {0}.").format(
                category
            )
        )
    return provider


def update_employee_availability(employee_name):
    if not employee_name or not frappe.db.exists("Employee", employee_name):
        return
    if not frappe.get_meta("Employee").has_field(
        "custom_facility_availability"
    ):
        return
    employee = frappe.get_doc("Employee", employee_name)
    availability = calculate_employee_availability(employee)
    if employee.custom_facility_availability != availability:
        frappe.db.set_value(
            "Employee",
            employee.name,
            "custom_facility_availability",
            availability,
            update_modified=False,
        )


def update_provider_availability(provider_name):
    if not provider_name or not frappe.db.exists(
        "Facility Service Provider", provider_name
    ):
        return
    provider = frappe.get_doc("Facility Service Provider", provider_name)
    availability = calculate_provider_availability(provider)
    if provider.availability != availability:
        frappe.db.set_value(
            "Facility Service Provider",
            provider.name,
            "availability",
            availability,
            update_modified=False,
        )


def refresh_work_order_availability(work_order):
    previous = work_order.get_doc_before_save()
    employees = {work_order.technician}
    providers = {work_order.vendor}
    if previous:
        employees.add(previous.technician)
        providers.add(previous.vendor)

    for employee in employees:
        update_employee_availability(employee)
    for provider in providers:
        update_provider_availability(provider)


def refresh_all_assignment_availability():
    technicians = frappe.get_all(
        "Employee",
        filters={"custom_is_facility_technician": 1},
        pluck="name",
    )
    providers = frappe.get_all(
        "Facility Service Provider",
        pluck="name",
    )
    for employee in technicians:
        update_employee_availability(employee)
    for provider in providers:
        update_provider_availability(provider)

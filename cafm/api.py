import base64
import binascii
import os

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import cint, getdate, now_datetime
from frappe.utils.file_manager import save_file

from cafm.permissions import PRIVILEGED_ROLES, get_employee_for_user


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def user_maintenance_role_query(
    doctype, txt, searchfield, start, page_len, filters
):
    """Offer only roles that belong to the selected maintenance-team user."""
    user = (filters or {}).get("user")
    if not user:
        return []

    return frappe.db.sql(
        """
        select distinct `role`
        from `tabHas Role`
        where parent = %(user)s
          and parenttype = 'User'
          and `role` like %(txt)s
        order by `role`
        limit %(start)s, %(page_len)s
        """,
        {
            "user": user,
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )


REQUEST_FIELDS = (
    "name",
    "subject",
    "description",
    "company",
    "custom_facility_location",
    "custom_asset",
    "issue_type",
    "priority",
    "custom_issue_status",
    "custom_work_order",
    "creation",
    "modified",
)

WORK_ORDER_LIST_FIELDS = (
    "name",
    "subject",
    "work_order_type",
    "maintenance_request",
    "facility_location",
    "asset",
    "category",
    "priority",
    "work_order_status",
    "planned_start",
    "planned_end",
    "actual_start",
    "actual_end",
    "modified",
)

WORK_ORDER_FIELDS = WORK_ORDER_LIST_FIELDS + (
    "company",
    "work_description",
    "assignment_type",
    "technician",
    "vendor",
    "technician_notes",
    "resolution_summary",
    "inspection_required",
    "inspection_template",
    "material_cost",
    "closed_by",
    "closed_on",
)

STATUS_ACTIONS = {
    ("Draft", "Assigned"): "Assign",
    ("Draft", "Cancelled"): "Cancel",
    ("Assigned", "In Progress"): "Start Work",
    ("Assigned", "Cancelled"): "Cancel",
    ("In Progress", "Pending"): "Put on Hold",
    ("Pending", "In Progress"): "Resume",
    ("In Progress", "Resolved"): "Resolve",
    ("Resolved", "Closed"): "Close",
    ("Resolved", "In Progress"): "Reopen",
}

ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
}


def _require_authenticated():
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentication is required."), frappe.AuthenticationError)


def _positive_int(value, default, maximum=None):
    try:
        value = int(value or default)
    except (TypeError, ValueError):
        frappe.throw(_("Pagination values must be whole numbers."))

    if value < 1:
        frappe.throw(_("Pagination values must be greater than zero."))
    return min(value, maximum) if maximum else value


def _parse_json(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, str):
        try:
            value = frappe.parse_json(value)
        except Exception:
            frappe.throw(_("The supplied JSON value is invalid."))
    return value


def _request_dict(row):
    as_dict = getattr(row, "as_dict", None)
    row = as_dict() if callable(as_dict) else dict(row)
    return {
        "name": row.get("name"),
        "subject": row.get("subject"),
        "description": row.get("description"),
        "company": row.get("company"),
        "facility_location": row.get("custom_facility_location"),
        "asset": row.get("custom_asset"),
        "category": row.get("issue_type"),
        "priority": row.get("priority"),
        "status": row.get("custom_issue_status"),
        "work_order": row.get("custom_work_order"),
        "creation": row.get("creation"),
        "modified": row.get("modified"),
    }


def _work_order_dict(doc, include_details=False):
    data = {field: doc.get(field) for field in WORK_ORDER_FIELDS}
    data["status"] = data.pop("work_order_status")

    if not include_details:
        return data

    data["checklist"] = [
        {
            "name": row.name,
            "idx": row.idx,
            "description": row.description,
            "is_required": row.is_required,
            "result": row.result,
            "comments": row.comments,
        }
        for row in doc.checklist
    ]
    data["labor_entries"] = [
        {
            "name": row.name,
            "employee": row.employee,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "hours": row.hours,
            "notes": row.notes,
        }
        for row in doc.labor_entries
    ]
    data["materials"] = [
        {
            "name": row.name,
            "item_code": row.item_code,
            "uom": row.uom,
            "warehouse": row.warehouse,
            "quantity": row.quantity,
            "batch_no": row.batch_no,
            "serial_no": row.serial_no,
            "amount": row.amount,
            "notes": row.notes,
        }
        for row in doc.materials
    ]
    data["attachments"] = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Facility Work Order",
            "attached_to_name": doc.name,
        },
        fields=["name", "file_name", "file_url", "file_size", "is_private"],
        order_by="creation asc",
    )
    return data


def _pagination(page, page_length, rows):
    has_next = len(rows) > page_length
    return {
        "page": page,
        "page_length": page_length,
        "has_next": has_next,
    }, rows[:page_length]


@frappe.whitelist(methods=["GET"])
def list_maintenance_requests(filters=None, page=1, page_length=20):
    """List maintenance requests visible to the authenticated user."""
    _require_authenticated()
    page = _positive_int(page, 1)
    page_length = _positive_int(page_length, 20, maximum=100)
    filters = _parse_json(filters, {})
    if not isinstance(filters, dict):
        frappe.throw(_("Filters must be a JSON object."))

    field_map = {
        "name": "name",
        "status": "custom_issue_status",
        "priority": "priority",
        "category": "issue_type",
        "facility_location": "custom_facility_location",
        "asset": "custom_asset",
        "company": "company",
    }
    db_filters = {
        field_map[key]: value
        for key, value in filters.items()
        if key in field_map and value not in (None, "")
    }
    if filters.get("from_date"):
        db_filters["creation"] = [">=", getdate(filters["from_date"])]
    if filters.get("to_date"):
        condition = ["<=", getdate(filters["to_date"])]
        if "creation" in db_filters:
            db_filters["creation"] = [
                "between",
                [
                    getdate(filters["from_date"]),
                    getdate(filters["to_date"]),
                ],
            ]
        else:
            db_filters["creation"] = condition

    or_filters = None
    if filters.get("search"):
        search = f"%{filters['search']}%"
        or_filters = {"name": ["like", search], "subject": ["like", search]}

    rows = frappe.get_list(
        "Issue",
        filters=db_filters,
        or_filters=or_filters,
        fields=list(REQUEST_FIELDS),
        order_by="modified desc",
        limit_start=(page - 1) * page_length,
        limit_page_length=page_length + 1,
    )
    pagination, rows = _pagination(page, page_length, rows)
    return {
        "data": [_request_dict(row) for row in rows],
        "pagination": pagination,
    }


@frappe.whitelist(methods=["POST"])
def create_maintenance_request(
    subject,
    description,
    facility_location,
    category,
    priority="Medium",
    asset=None,
    company=None,
):
    """Create a maintenance request for the current employee."""
    _require_authenticated()
    employee = get_employee_for_user(frappe.session.user)
    if not employee:
        frappe.throw(
            _("Your user is not linked to an active Employee."),
            frappe.PermissionError,
        )
    company = company or (
        frappe.db.get_value("Employee", employee, "company")
    ) or frappe.defaults.get_user_default("Company")

    issue = frappe.get_doc(
        {
            "doctype": "Issue",
            "subject": subject,
            "description": description,
            "company": company,
            "custom_facility_location": facility_location,
            "custom_asset": asset,
            "issue_type": category,
            "priority": priority,
            "custom_requester": employee,
            "raised_by": frappe.session.user,
        }
    )
    issue.insert()
    return _request_dict(issue)


@frappe.whitelist(methods=["GET"])
def get_work_order(work_order_name):
    """Return a work order and its mobile execution details."""
    _require_authenticated()
    work_order = frappe.get_doc("Facility Work Order", work_order_name)
    work_order.check_permission("read")
    return _work_order_dict(work_order, include_details=True)


@frappe.whitelist(methods=["POST"])
def update_work_order_status(work_order_name, status, pending_reason=None):
    """Move a work order through its configured Frappe workflow."""
    _require_authenticated()
    work_order = frappe.get_doc("Facility Work Order", work_order_name)
    work_order.check_permission("write")

    current_status = work_order.work_order_status
    if status == current_status:
        return _work_order_dict(work_order)

    action = STATUS_ACTIONS.get((current_status, status))
    if not action:
        frappe.throw(
            _("A Work Order cannot move from {0} to {1}.").format(
                current_status, status
            )
        )

    save_before_transition = False
    if status == "Pending":
        if not pending_reason:
            frappe.throw(_("A pending reason is required."))
        work_order.technician_notes = pending_reason
        save_before_transition = True
    if status == "In Progress" and not work_order.actual_start:
        work_order.actual_start = now_datetime()
        save_before_transition = True
    if status == "Resolved" and not work_order.actual_end:
        work_order.actual_end = now_datetime()
        save_before_transition = True

    if save_before_transition:
        work_order.save()
    work_order = apply_workflow(work_order, action)
    return _work_order_dict(work_order)


@frappe.whitelist(methods=["GET"])
def list_assigned_work_orders(status=None, page=1, page_length=20):
    """List work orders assigned to the current internal technician."""
    _require_authenticated()
    roles = set(frappe.get_roles())
    if "Technician" not in roles and not roles & PRIVILEGED_ROLES:
        frappe.throw(_("A Technician role is required."), frappe.PermissionError)

    technician = get_employee_for_user(frappe.session.user)
    if not technician:
        frappe.throw(
            _("Your user is not linked to an active Employee."),
            frappe.PermissionError,
        )

    page = _positive_int(page, 1)
    page_length = _positive_int(page_length, 20, maximum=100)
    db_filters = {"technician": technician}
    if status:
        statuses = status
        if isinstance(status, str) and status.lstrip().startswith("["):
            statuses = _parse_json(status, status)
        db_filters["work_order_status"] = (
            ["in", statuses] if isinstance(statuses, list) else statuses
        )

    rows = frappe.get_list(
        "Facility Work Order",
        filters=db_filters,
        fields=list(WORK_ORDER_LIST_FIELDS),
        order_by="planned_start asc, modified desc",
        limit_start=(page - 1) * page_length,
        limit_page_length=page_length + 1,
    )
    pagination, rows = _pagination(page, page_length, rows)
    return {
        "data": [_work_order_dict(row) for row in rows],
        "pagination": pagination,
    }


def _update_checklist(work_order, checklist):
    checklist = _parse_json(checklist, [])
    if not isinstance(checklist, list):
        frappe.throw(_("Checklist updates must be a JSON array."))

    rows_by_name = {row.name: row for row in work_order.checklist}
    rows_by_idx = {row.idx: row for row in work_order.checklist}
    for update in checklist:
        if not isinstance(update, dict):
            frappe.throw(_("Every checklist update must be a JSON object."))
        row = rows_by_name.get(update.get("name"))
        if not row and update.get("idx"):
            row = rows_by_idx.get(cint(update["idx"]))
        if not row:
            frappe.throw(_("A checklist item could not be found."))
        if update.get("result") not in ("Pending", "Pass", "Fail", "N/A"):
            frappe.throw(
                _("Checklist result must be Pending, Pass, Fail, or N/A.")
            )
        row.result = update["result"]
        if "comments" in update:
            row.comments = update["comments"]


@frappe.whitelist(methods=["POST"])
def submit_technician_resolution(
    work_order_name,
    resolution_summary,
    technician_notes=None,
    checklist=None,
):
    """Save execution results and resolve an in-progress work order."""
    _require_authenticated()
    work_order = frappe.get_doc("Facility Work Order", work_order_name)
    work_order.check_permission("write")
    if work_order.work_order_status != "In Progress":
        frappe.throw(_("Only an In Progress Work Order can be resolved."))
    if not resolution_summary:
        frappe.throw(_("Resolution Summary is required."))

    _update_checklist(work_order, checklist)
    work_order.resolution_summary = resolution_summary
    if technician_notes is not None:
        work_order.technician_notes = technician_notes
    work_order.actual_end = work_order.actual_end or now_datetime()
    work_order.save()
    work_order = apply_workflow(work_order, "Resolve")
    return _work_order_dict(work_order, include_details=True)


def _uploaded_file(file_name, file_content):
    request = getattr(frappe.local, "request", None)
    uploaded = request.files.get("file") if request and request.files else None
    if uploaded:
        return uploaded.filename, uploaded.stream.read()

    if not file_name or not file_content:
        frappe.throw(
            _("Provide a file upload or file_name and base64 file_content.")
        )
    if isinstance(file_content, str) and "," in file_content:
        file_content = file_content.rsplit(",", 1)[1]
    try:
        return file_name, base64.b64decode(file_content, validate=True)
    except (binascii.Error, TypeError, ValueError):
        frappe.throw(_("file_content must be valid base64 data."))


@frappe.whitelist(methods=["POST"])
def upload_work_order_attachment(
    work_order_name,
    file_name=None,
    file_content=None,
):
    """Attach a private image or document to a permitted work order."""
    _require_authenticated()
    work_order = frappe.get_doc("Facility Work Order", work_order_name)
    work_order.check_permission("write")

    file_name, content = _uploaded_file(file_name, file_content)
    file_name = os.path.basename(file_name or "")
    extension = os.path.splitext(file_name)[1].lower()
    if not file_name or extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        frappe.throw(_("Only standard image and document files are allowed."))

    file_doc = save_file(
        file_name,
        content,
        "Facility Work Order",
        work_order.name,
        is_private=1,
    )
    return {
        "name": file_doc.name,
        "file_name": file_doc.file_name,
        "file_url": file_doc.file_url,
        "file_size": file_doc.file_size,
        "is_private": file_doc.is_private,
    }

import base64
import binascii
import os

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, cint, getdate, now_datetime, strip_html_tags
from frappe.utils.file_manager import save_file

from cafm.permissions import PRIVILEGED_ROLES, get_employee_for_user


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def user_maintenance_role_query(
    doctype, txt, searchfield, start, page_len, filters
):
    """Offer only roles that belong to the selected maintenance-team user."""
    filters = filters or {}
    user = filters.get("user")
    if not user and filters.get("employee"):
        user = frappe.db.get_value("Employee", filters["employee"], "user_id")
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
    ("In Progress", "Closed"): "Complete Work",
    ("Resolved", "Closed"): "Close",
    ("Resolved", "In Progress"): "Reopen",
    ("Closed", "In Progress"): "Reopen",
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


@frappe.whitelist(methods=["POST"])
def reopen_cafm_record(doctype, name):
    """Reopen a closed maintenance request or work order through its workflow."""
    _require_authenticated()
    if doctype not in ("Issue", "Facility Work Order"):
        frappe.throw(_("This record type cannot be reopened."))

    document = frappe.get_doc(doctype, name)
    document.check_permission("write")
    state_field = (
        "custom_issue_status" if doctype == "Issue" else "work_order_status"
    )
    if document.get(state_field) != "Closed":
        frappe.throw(_("Only a closed record can be reopened."))

    document = apply_workflow(document, "Reopen")
    return {
        "doctype": document.doctype,
        "name": document.name,
        "status": document.get(state_field),
    }


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
    """Save execution results and close an in-progress technician work order."""
    _require_authenticated()
    work_order = frappe.get_doc("Facility Work Order", work_order_name)
    work_order.check_permission("write")
    if work_order.work_order_status != "In Progress":
        frappe.throw(_("Only an In Progress Work Order can be completed."))
    if not resolution_summary:
        frappe.throw(_("Resolution Summary is required."))

    _update_checklist(work_order, checklist)
    work_order.resolution_summary = resolution_summary
    if technician_notes is not None:
        work_order.technician_notes = technician_notes
    work_order.actual_end = work_order.actual_end or now_datetime()
    work_order.save()
    work_order = apply_workflow(work_order, "Complete Work")
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

CAFM_APP_VIEW_ROLES = ("Facility Manager", "Facility Coordinator", "System Manager")


CAFM_EMBEDDED_DOCTYPES = {
    "Issue": "custom_issue_status",
    "Facility Work Order": "work_order_status",
    "Preventive Maintenance Plan": "frequency",
    "Facility Inspection": "inspection_status",
    "Asset": "status",
    "Facility Location": "location_type",
    "Asset Category": None,
    "Facility Service Provider": "provider_status",
    "Facility Service Contract": "contract_status",
    "Facility Vendor Quotation": "quotation_status",
    "Facility SLA Policy": "is_active",
    "Utility Meter": "utility_type",
    "Utility Reading": "utility_type",
    "Utility Bill": "match_status",
    "Utility Budget": "budget_status",
}


def _require_cafm_app_view_access():
    _require_authenticated()
    if not set(CAFM_APP_VIEW_ROLES).intersection(frappe.get_roles()):
        frappe.throw(
            _("The CAFM Operations view is available to Facility Managers and Coordinators."),
            frappe.PermissionError,
        )


def _require_cafm_creatable_doctype(doctype):
    _require_cafm_app_view_access()
    if doctype != "Issue" and doctype not in CAFM_EMBEDDED_DOCTYPES:
        frappe.throw(_("This record type is not available in the CAFM view."), frappe.PermissionError)
    if not frappe.has_permission(doctype, "create"):
        frappe.throw(_("You do not have permission to create {0}.").format(doctype), frappe.PermissionError)


@frappe.whitelist()
def get_cafm_create_schema(doctype):
    """Return editable fields grouped by the DocType's native sections."""
    _require_cafm_creatable_doctype(doctype)
    meta = frappe.get_meta(doctype)
    # All scalar controls that can be completed in a native Frappe form. Layout,
    # display-only and child-table controls are deliberately excluded below.
    supported = {
        "Autocomplete", "Barcode", "Code", "Color", "Currency", "Data", "Date",
        "Datetime", "Duration", "Float", "Geolocation", "HTML Editor", "Int", "JSON",
        "Link", "Long Text", "Markdown Editor", "Password", "Percent", "Phone", "Rating",
        "Select", "Signature", "Small Text", "Text", "Text Editor", "Time", "Check", "Table",
    }
    fields = []
    sections = []
    current = {"value": "general", "label": _("General"), "fields": []}
    column_index = 0

    def finish_section():
        nonlocal current
        if current["fields"]:
            sections.append(current)

    section_index = 0
    for field in meta.fields:
        if field.fieldtype in ("Section Break", "Tab Break"):
            finish_section()
            section_index += 1
            column_index = 0
            label = field.label or (_("General") if not sections else _("Details {0}").format(section_index))
            current = {
                "value": field.fieldname or f"section_{section_index}",
                "label": label,
                "fields": [],
            }
            continue
        if field.fieldtype == "Column Break":
            column_index += 1
            continue
        if (
            not field.fieldname
            or field.fieldtype not in supported
            or field.hidden
            or field.read_only
            or field.permlevel
            or field.fieldname in ("naming_series", "name")
        ):
            continue
        item = {
            "fieldname": field.fieldname,
            "label": field.label or field.fieldname,
            "fieldtype": field.fieldtype,
            "required": bool(field.reqd),
            "options": [],
            "default": None,
            "column": column_index,
            "description": field.description or "",
            "placeholder": field.placeholder or "",
            "depends_on": field.depends_on or "",
            "mandatory_depends_on": field.mandatory_depends_on or "",
            "read_only_depends_on": field.read_only_depends_on or "",
        }
        if field.fieldtype == "Table" and field.options:
            item["child_doctype"] = field.options
            item["child_fields"] = []
            child_meta = frappe.get_meta(field.options)
            for child_field in child_meta.fields:
                if (
                    not child_field.fieldname
                    or child_field.fieldtype not in supported - {"Table"}
                    or child_field.hidden
                    or child_field.read_only
                    or child_field.permlevel
                    or child_field.fieldname in ("name", "naming_series")
                ):
                    continue
                child_item = {
                    "fieldname": child_field.fieldname,
                    "label": child_field.label or child_field.fieldname,
                    "fieldtype": child_field.fieldtype,
                    "required": bool(child_field.reqd),
                    "options": [],
                    "default": child_field.default if child_field.default not in (None, "") else None,
                }
                if child_field.fieldtype == "Select":
                    child_item["options"] = [value for value in (child_field.options or "").splitlines() if value]
                elif child_field.fieldtype == "Link" and child_field.options and frappe.has_permission(child_field.options, "read"):
                    child_item["link_doctype"] = child_field.options
                    child_item["options"] = frappe.get_list(child_field.options, pluck="name", order_by="modified desc", limit_page_length=100)
                item["child_fields"].append(child_item)
        elif field.fieldtype == "Select":
            item["options"] = [value for value in (field.options or "").splitlines() if value]
        elif field.fieldtype == "Link" and field.options and frappe.has_permission(field.options, "read"):
            item["link_doctype"] = field.options
            item["options"] = frappe.get_list(
                field.options,
                pluck="name",
                order_by="modified desc",
                limit_page_length=100,
            )
        default = field.default
        if default not in (None, "") and not str(default).startswith(("eval:", "user:", "Today")):
            item["default"] = default
        fields.append(item)
        current["fields"].append(item)
    finish_section()

    # ERPNext's Asset metadata places the custom Warranty Provider after an
    # otherwise display-only QR section. Keep the editable field with the rest
    # of the warranty inputs, and give the unlabeled depreciation block a useful
    # native-style title.
    if doctype == "Asset":
        warranty = next((section for section in sections if section["value"] == "custom_warranty_section"), None)
        qr_section = next((section for section in sections if section["value"] == "custom_asset_qr_section"), None)
        if warranty and qr_section:
            warranty["fields"].extend(qr_section["fields"])
            sections.remove(qr_section)
        for section in sections:
            if section["value"] == "section_break_33" or section["label"] == _("Details 9"):
                section["label"] = _("Depreciation Schedule")

    return {
        "doctype": doctype,
        "label": doctype,
        "fields": fields,
        "sections": sections,
    }


@frappe.whitelist()
def search_cafm_link(doctype, fieldname, txt=""):
    """Search a Link field using its real target DocType and current user permissions."""
    _require_cafm_creatable_doctype(doctype)
    field = frappe.get_meta(doctype).get_field(fieldname)
    if not field or field.fieldtype != "Link" or not field.options:
        frappe.throw(_("This is not a valid Link field."), frappe.PermissionError)
    if field.hidden or field.read_only or field.permlevel or not frappe.has_permission(field.options, "read"):
        frappe.throw(_("You cannot search this linked record type."), frappe.PermissionError)
    filters = {"name": ["like", f"%{txt}%"]} if txt else None
    return frappe.get_list(
        field.options,
        filters=filters,
        fields=["name"],
        order_by="modified desc",
        limit_page_length=20,
    )


@frappe.whitelist(methods=["POST"])
def create_cafm_record(doctype, values):
    """Create a CAFM record from the reusable drawer using normal DocType validation."""
    _require_cafm_creatable_doctype(doctype)
    values = _parse_json(values, {})
    if not isinstance(values, dict):
        frappe.throw(_("Values must be a JSON object."))

    schema = get_cafm_create_schema(doctype)
    allowed = {field["fieldname"]: field for field in schema["fields"]}
    clean = {}
    for fieldname, value in values.items():
        if fieldname not in allowed:
            continue
        field = allowed[fieldname]
        if field["fieldtype"] == "Check":
            clean[fieldname] = cint(value)
        elif value not in (None, ""):
            clean[fieldname] = value

    document = frappe.get_doc({"doctype": doctype, **clean})
    document.insert()
    meta = frappe.get_meta(doctype)
    return {
        "doctype": doctype,
        "name": document.name,
        "title": document.get(meta.title_field) if meta.title_field else document.name,
        "route": f"/app/{frappe.scrub(doctype).replace('_', '-')}/{document.name}",
    }


@frappe.whitelist()
def get_cafm_doctype_detail(doctype, name):
    """Return populated fields grouped by the DocType's native sections."""
    _require_cafm_app_view_access()
    if doctype != "Issue" and doctype not in CAFM_EMBEDDED_DOCTYPES:
        frappe.throw(_("This record type is not available in the CAFM view."), frappe.PermissionError)
    document = frappe.get_doc(doctype, name)
    document.check_permission("read")
    meta = frappe.get_meta(doctype)
    excluded = {
        "Column Break", "HTML", "Button", "Fold", "Heading",
        "Attach", "Attach Image", "Table MultiSelect",
    }
    sections = []
    current = {"value": "general", "label": _("General"), "fields": []}

    def finish_section():
        nonlocal current
        if current["fields"]:
            sections.append(current)

    section_index = 0
    for field in meta.fields:
        if field.fieldtype in ("Section Break", "Tab Break"):
            finish_section()
            section_index += 1
            current = {
                "value": field.fieldname or f"section_{section_index}",
                "label": field.label or (_("General") if not sections else _("Details {0}").format(section_index)),
                "fields": [],
            }
            continue
        if (
            not field.fieldname
            or field.fieldtype in excluded
            or field.hidden
            or field.permlevel
        ):
            continue
        value = document.get(field.fieldname)
        if value in (None, ""):
            continue
        if field.fieldtype == "Table":
            value = _("{0} item(s)").format(len(value or []))
        elif field.fieldtype in ("Text", "Small Text", "Long Text", "Text Editor"):
            value = strip_html_tags(str(value))
        elif field.fieldtype == "Check":
            value = _("Yes") if cint(value) else _("No")
        current["fields"].append({
            "fieldname": field.fieldname,
            "label": field.label or field.fieldname,
            "fieldtype": field.fieldtype,
            "value": value,
        })
    finish_section()

    fields = [field for section in sections for field in section["fields"]]
    actions = []
    roles = set(frappe.get_roles())
    if doctype == "Asset":
        qr_url = document.get("custom_asset_qr_code")
        if qr_url:
            actions.extend([
                {"id": "show_qr", "label": _("Show QR Code"), "icon": "qr", "url": qr_url},
                {"id": "download_qr", "label": _("Download QR Code"), "icon": "download", "url": qr_url},
            ])
        if frappe.has_permission("Issue", "create"):
            actions.append({
                "id": "create_maintenance_request", "label": _("Create Maintenance Request"), "icon": "maintenance",
                "defaults": {
                    "company": document.get("company"), "custom_facility_location": document.get("custom_asset_location"),
                    "custom_asset": document.name,
                    "subject": _("Maintenance request for {0}").format(document.get("asset_name") or document.name),
                },
            })
        if frappe.has_permission("Facility Work Order", "read"):
            actions.append({"id": "view_open_work_orders", "label": _("View Open Work Orders"), "icon": "maintenance"})
        actions.append({"id": "view_maintenance_history", "label": _("View Maintenance History"), "icon": "section"})
    elif doctype == "Issue":
        if document.get("custom_issue_status") == "Closed":
            if frappe.has_permission("Issue", "write", document.name):
                actions.append({"id": "reopen_record", "label": _("Reopen"), "icon": "maintenance"})
        if document.get("custom_work_order") and frappe.has_permission("Facility Work Order", "read", document.get("custom_work_order")):
            actions.append({"id": "open_work_order", "label": _("Open Work Order"), "icon": "maintenance", "work_order": document.get("custom_work_order")})
        elif not document.get("custom_work_order") and frappe.has_permission("Facility Work Order", "create"):
            actions.append({"id": "create_work_order", "label": _("Create Work Order"), "icon": "maintenance"})
    elif doctype == "Facility Work Order":
        if document.get("work_order_status") == "Closed" and frappe.has_permission(doctype, "write", document.name):
            actions.append({"id": "reopen_record", "label": _("Reopen"), "icon": "maintenance"})
        if document.get("inspection_template") and frappe.has_permission("Facility Inspection", "create"):
            actions.append({"id": "create_inspection", "label": _("Create Inspection"), "icon": "section"})
        if document.get("materials") and document.get("work_order_status") in ("Assigned", "In Progress", "Pending", "Resolved") and frappe.has_permission(doctype, "write", document.name) and not ("Vendor" in roles and not roles.intersection({"System Manager", "Facility Manager", "Facility Coordinator"})):
            actions.append({"id": "issue_materials", "label": _("Issue Materials"), "icon": "assets"})
        if frappe.has_permission("Facility Vendor Quotation", "create"):
            actions.append({
                "id": "request_vendor_quotation", "label": _("Request Vendor Quotation"), "icon": "vendors",
                "defaults": {"quotation_name": _("Quotation for {0}").format(document.name), "work_order": document.name, "company": document.get("company"), "service_provider": document.get("vendor"), "service_contract": document.get("service_contract"), "scope_of_work": document.get("work_description")},
            })
        if frappe.has_permission("Facility Vendor Quotation", "read"):
            actions.append({"id": "view_vendor_quotations", "label": _("View Vendor Quotations"), "icon": "vendors"})
        if frappe.has_permission("Facility Service Contract", "read"):
            actions.append({"id": "view_matching_contracts", "label": _("View Matching Contracts"), "icon": "section"})
    elif doctype == "Preventive Maintenance Plan" and document.get("is_active") and document.get("next_due_date") and frappe.has_permission(doctype, "write", document.name):
        actions.append({"id": "generate_next_work_order", "label": _("Generate Next Work Order"), "icon": "maintenance"})
    elif doctype == "Facility Inspection" and document.get("work_order") and frappe.has_permission("Facility Work Order", "read", document.get("work_order")):
        actions.append({"id": "open_work_order", "label": _("Open Work Order"), "icon": "maintenance", "work_order": document.get("work_order")})
    elif doctype == "Facility Vendor Quotation" and document.get("quotation_status") == "Received" and frappe.has_permission(doctype, "write", document.name) and roles.intersection({"Facility Manager", "System Manager"}):
        actions.append({"id": "select_quotation", "label": _("Select Quotation"), "icon": "section"})

    if frappe.has_permission(doctype, "print", document.name):
        actions.extend([
            {"id": "print", "label": _("Print"), "icon": "print"},
            {"id": "download_pdf", "label": _("Download PDF"), "icon": "download"},
        ])


    return {
        "doctype": doctype,
        "name": document.name,
        "title": (document.get(meta.title_field) if meta.title_field else None) or document.name,
        "fields": fields,
        "sections": sections,
        "actions": actions,
        "route": f"/app/{frappe.scrub(doctype).replace('_', '-')}/{document.name}",
    }


@frappe.whitelist()
def get_cafm_doctype_view(doctype):
    """Return permission-filtered list metadata and rows for an embedded CAFM view."""
    _require_cafm_app_view_access()
    if doctype not in CAFM_EMBEDDED_DOCTYPES:
        frappe.throw(_("This record type is not available in the CAFM view."), frappe.PermissionError)
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("You do not have permission to view {0}.").format(doctype), frappe.PermissionError)

    meta = frappe.get_meta(doctype)
    excluded_types = {
        "Section Break",
        "Column Break",
        "Tab Break",
        "Table",
        "Table MultiSelect",
        "HTML",
        "Button",
        "Fold",
        "Heading",
    }
    list_fields = [
        field
        for field in meta.fields
        if field.in_list_view
        and field.fieldname
        and field.fieldtype not in excluded_types
    ]

    title_field = meta.title_field
    group_field = CAFM_EMBEDDED_DOCTYPES[doctype]
    selected_names = ["name"]
    for fieldname in (title_field, group_field):
        if fieldname and fieldname not in selected_names and meta.has_field(fieldname):
            selected_names.append(fieldname)
    for field in list_fields:
        if field.fieldname not in selected_names:
            selected_names.append(field.fieldname)
        if len(selected_names) >= 8:
            break

    rows = frappe.get_list(
        doctype,
        fields=selected_names,
        order_by=f"{meta.sort_field or 'modified'} {meta.sort_order or 'desc'}",
        limit_page_length=500,
    )
    field_map = {field.fieldname: field for field in meta.fields}
    columns = []
    for fieldname in selected_names:
        field = field_map.get(fieldname)
        columns.append(
            {
                "fieldname": fieldname,
                "label": _("ID") if fieldname == "name" else (field.label or fieldname),
                "fieldtype": "Data" if fieldname == "name" else field.fieldtype,
            }
        )

    return {
        "doctype": doctype,
        "title_field": title_field or "name",
        "group_field": group_field if group_field in selected_names else None,
        "columns": columns,
        "rows": rows,
        "can_create": frappe.has_permission(doctype, "create"),
    }


@frappe.whitelist()
def get_cafm_operations_dashboard():
    """Return the small, permission-gated data set used by the /cafm app view."""
    _require_cafm_app_view_access()

    active_statuses = ("Draft", "Assigned", "In Progress", "Pending")
    closed_statuses = ("Resolved", "Closed", "Cancelled")
    open_request_statuses = ("Resolved", "Closed", "Rejected")
    today = getdate()

    active_orders = frappe.db.count(
        "Facility Work Order", {"work_order_status": ["in", active_statuses]}
    )
    open_requests = frappe.db.count(
        "Issue", {"custom_issue_status": ["not in", open_request_statuses]}
    )
    overdue_orders = frappe.db.count(
        "Facility Work Order",
        {
            "work_order_status": ["not in", closed_statuses],
            "planned_end": ["<", today],
        },
    )
    sla_breaches = frappe.db.count(
        "Facility Work Order",
        {
            "work_order_status": ["not in", closed_statuses],
            "sla_status": ["in", ("Response Breached", "Resolution Breached")],
        },
    )

    upcoming_preventive = (
        len(
            frappe.get_list(
                "Preventive Maintenance Plan",
                filters={"is_active": 1, "next_due_date": ["between", [today, add_days(today, 7)]]},
                fields=["name"],
                limit_page_length=10000,
            )
        )
        if frappe.has_permission("Preventive Maintenance Plan", "read")
        else 0
    )
    unresolved_inspections = (
        len(
            frappe.get_list(
                "Facility Inspection",
                filters={"status": ["not in", ("Completed", "Approved", "Rejected", "Cancelled")]},
                fields=["name"],
                limit_page_length=10000,
            )
        )
        if frappe.has_permission("Facility Inspection", "read")
        else 0
    )

    work_orders = frappe.get_all(
        "Facility Work Order",
        filters={"work_order_status": ["in", active_statuses]},
        fields=[
            "name",
            "subject",
            "priority",
            "work_order_status",
            "facility_location",
            "planned_end",
        ],
        order_by="planned_end asc, modified desc",
        limit_page_length=6,
    )

    user_roles = set(frappe.get_roles(frappe.session.user))

    attention = []
    if frappe.has_permission("Issue", "read"):
        for row in frappe.get_list(
            "Issue",
            filters={
                "priority": ["in", ("Critical", "High")],
                "custom_issue_status": ["not in", open_request_statuses],
            },
            fields=["name", "subject", "priority", "custom_issue_status"],
            order_by="modified desc",
            limit_page_length=5,
        ):
            attention.append({
                "title": row.subject or row.name,
                "kind": _("Request"),
                "status": row.custom_issue_status or _("New"),
                "priority": row.priority or _("Not set"),
                "detail": _("High-priority maintenance request"),
                "route": f"/app/issue/{row.name}",
                "doctype": "Issue",
                "name": row.name,
            })
    if frappe.has_permission("Facility Work Order", "read"):
        for row in frappe.get_list(
            "Facility Work Order",
            filters=[
                ["work_order_status", "not in", closed_statuses],
                ["planned_end", "is", "set"],
                ["planned_end", "<", today],
            ],
            fields=["name", "subject", "priority", "work_order_status", "planned_end"],
            order_by="planned_end asc",
            limit_page_length=5,
        ):
            attention.append({
                "title": row.subject or row.name,
                "kind": _("Overdue work order"),
                "status": row.work_order_status,
                "priority": row.priority or _("Not set"),
                "detail": _("Due {0}").format(row.planned_end),
                "route": f"/app/facility-work-order/{row.name}",
                "doctype": "Facility Work Order",
                "name": row.name,
            })

    today_items = []
    if frappe.has_permission("Facility Work Order", "read"):
        for row in frappe.get_list(
            "Facility Work Order",
            filters={"planned_start": ["between", [today, add_days(today, 1)]]},
            fields=["name", "subject", "work_order_status", "planned_start"],
            order_by="planned_start asc",
            limit_page_length=6,
        ):
            today_items.append({
                "title": row.subject or row.name,
                "kind": _("Work order"),
                "status": row.work_order_status,
                "detail": str(row.planned_start or ""),
                "route": f"/app/facility-work-order/{row.name}",
                "doctype": "Facility Work Order",
                "name": row.name,
            })
    if frappe.has_permission("Facility Inspection", "read"):
        for row in frappe.get_list(
            "Facility Inspection",
            filters={"planned_date": today},
            fields=["name", "inspection_template", "status", "planned_date"],
            limit_page_length=6,
        ):
            today_items.append({
                "title": row.inspection_template or row.name,
                "kind": _("Inspection"),
                "status": row.status,
                "detail": str(row.planned_date or ""),
                "route": f"/app/facility-inspection/{row.name}",
                "doctype": "Facility Inspection",
                "name": row.name,
            })
    if frappe.has_permission("Preventive Maintenance Plan", "read"):
        for row in frappe.get_list(
            "Preventive Maintenance Plan",
            filters={"is_active": 1, "next_due_date": today},
            fields=["name", "plan_name", "next_due_date"],
            limit_page_length=6,
        ):
            today_items.append({
                "title": row.plan_name or row.name,
                "kind": _("Preventive maintenance"),
                "status": _("Due today"),
                "detail": str(row.next_due_date or ""),
                "route": f"/app/preventive-maintenance-plan/{row.name}",
                "doctype": "Preventive Maintenance Plan",
                "name": row.name,
            })

    quick_actions = []
    for doctype, label, route in (
        ("Issue", _("Create request"), "/app/issue/new-issue"),
        ("Facility Work Order", _("Create work order"), "/app/facility-work-order/new-facility-work-order"),
        ("Facility Inspection", _("Create inspection"), "/app/facility-inspection/new-facility-inspection"),
        ("Preventive Maintenance Plan", _("Create preventive plan"), "/app/preventive-maintenance-plan/new-preventive-maintenance-plan"),
        ("Utility Reading", _("Add meter reading"), "/app/utility-reading/new-utility-reading"),
    ):
        if frappe.has_permission(doctype, "create"):
            quick_actions.append({"label": label, "route": route, "doctype": doctype})

    return {
        "user_full_name": frappe.db.get_value(
            "User", frappe.session.user, "full_name"
        )
        or frappe.session.user,
        "can_manage_settings": bool(
            {"Facility Manager", "System Manager"}.intersection(user_roles)
        ),
        "stats": [
            {
                "label": _("Active work orders"),
                "value": active_orders,
                "detail": _("Assigned, in progress, or pending"),
                "route": "/app/facility-work-order",
                "tone": "blue",
            },
            {
                "label": _("Open requests"),
                "value": open_requests,
                "detail": _("Awaiting facility action"),
                "route": "/app/issue",
                "tone": "violet",
            },
            {
                "label": _("Overdue workload"),
                "value": overdue_orders,
                "detail": _("Past planned completion"),
                "route": "/app/facility-work-order",
                "tone": "red",
            },
            {
                "label": _("SLA breaches"),
                "value": sla_breaches,
                "detail": _("Response or resolution target missed"),
                "route": "/app/dashboard-view/SLA%20Performance%20Dashboard",
                "tone": "amber",
            },
            {
                "label": _("Preventive due soon"),
                "value": upcoming_preventive,
                "detail": _("Due within seven days"),
                "route": "/app/preventive-maintenance-plan",
                "tone": "blue",
            },
            {
                "label": _("Open inspections"),
                "value": unresolved_inspections,
                "detail": _("Awaiting completion or approval"),
                "route": "/app/facility-inspection",
                "tone": "violet",
            },
        ],
        "work_orders": work_orders,
        "attention": attention[:8],
        "today": today_items[:8],
        "quick_actions": quick_actions,
    }


@frappe.whitelist()
def get_cafm_work_orders_by_priority():
    _require_cafm_app_view_access()
    if not frappe.has_permission("Facility Work Order", "read"):
        frappe.throw(_("You do not have permission to view work orders."), frappe.PermissionError)
    rows = frappe.get_list("Facility Work Order", fields=["priority"], limit_page_length=10000)
    counts = {}
    for row in rows:
        priority = row.get("priority") or _("Not set")
        counts[priority] = counts.get(priority, 0) + 1
    return [{"label": label, "value": value} for label, value in counts.items()]


@frappe.whitelist()
def get_facility_management_analytics():
    """Return live, permission-filtered data for the Frappe UI facility dashboard."""
    _require_cafm_app_view_access()

    overview = get_cafm_operations_dashboard()
    work_orders = frappe.get_list(
        "Facility Work Order",
        fields=[
            "priority",
            "category",
            "work_order_status",
            "facility_location",
            "material_cost",
            "external_service_cost",
        ],
        limit_page_length=10000,
    )
    history = (
        frappe.get_list(
            "Facility Asset Maintenance History",
            fields=["asset", "downtime_hours", "closed_on", "actual_end", "creation"],
            limit_page_length=10000,
        )
        if frappe.has_permission("Facility Asset Maintenance History", "read")
        else []
    )

    def grouped(rows, field, value_field=None, limit=None):
        values = {}
        for row in rows:
            label = row.get(field) or _("Not set")
            value = (row.get(value_field) or 0) if value_field else 1
            values[label] = values.get(label, 0) + value
        result = [
            {"label": label, "value": round(value, 2)}
            for label, value in values.items()
        ]
        result.sort(key=lambda item: item["value"], reverse=True)
        return result[:limit] if limit else result

    location_names = {
        row["name"]: row.get("site") or row["name"]
        for row in frappe.get_list(
            "Facility Location",
            fields=["name", "site"],
            limit_page_length=10000,
        )
    }

    maintenance_costs = {}
    for row in work_orders:
        site = location_names.get(
            row.get("facility_location"),
            row.get("facility_location") or _("Not set"),
        )
        for cost_type, fieldname in (
            (_("Material cost"), "material_cost"),
            (_("External service cost"), "external_service_cost"),
        ):
            key = (site, cost_type)
            maintenance_costs[key] = maintenance_costs.get(key, 0) + (
                row.get(fieldname) or 0
            )

    sites_with_cost = {
        site
        for (site, _cost_type), amount in maintenance_costs.items()
        if amount
    }
    maintenance_cost_by_site = [
        {"site": site, "cost_type": cost_type, "amount": round(amount, 2)}
        for (site, cost_type), amount in sorted(maintenance_costs.items())
        if site in sites_with_cost
    ]

    preventive_plans = (
        frappe.get_list(
            "Preventive Maintenance Plan",
            filters={"is_active": 1},
            fields=["next_due_date"],
            limit_page_length=10000,
        )
        if frappe.has_permission("Preventive Maintenance Plan", "read")
        else []
    )
    weekdays = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    preventive_counts = {}
    for row in preventive_plans:
        if not row.get("next_due_date"):
            continue
        due_date = getdate(row["next_due_date"])
        key = (f"Week {((due_date.day - 1) // 7) + 1}", weekdays[due_date.weekday()])
        preventive_counts[key] = preventive_counts.get(key, 0) + 1

    preventive_maintenance_calendar = [
        {
            "week": f"Week {week}",
            "day": day,
            "plans": preventive_counts.get((f"Week {week}", day), 0),
        }
        for day in weekdays
        for week in range(1, 6)
    ]

    return {
        "user_full_name": overview["user_full_name"],
        "stats": overview["stats"],
        "work_orders_by_priority": grouped(work_orders, "priority"),
        "work_orders_by_category": [
            row
            for row in grouped(work_orders, "category")
            if not str(row["label"]).casefold().startswith("cafm test")
        ][:8],
        "work_orders_by_status": grouped(work_orders, "work_order_status"),
        "asset_downtime": grouped(history, "asset", "downtime_hours", limit=8),
        "recurring_asset_failures": grouped(history, "asset", limit=8),
        "maintenance_cost_by_site": maintenance_cost_by_site,
        "preventive_maintenance_calendar": preventive_maintenance_calendar,
    }


@frappe.whitelist()
def get_utility_consumption_analytics():
    """Return live data for the Frappe UI utility dashboard."""
    from cafm import dashboard as dashboard_api
    from cafm.cafm.dashboard_chart_source.monthly_utility_cost.monthly_utility_cost import (
        get as monthly_cost,
    )
    from cafm.utilities import get_utility_forecast
    from frappe.utils import add_to_date

    dashboard_api._require_utility_dashboard_access()
    cards = [
        ("Utility meters reported", dashboard_api.get_utility_meters_reported()),
        ("Monthly estimated cost", dashboard_api.get_monthly_utility_cost()),
        ("Usage change", dashboard_api.get_utility_usage_change()),
        ("Forecast cost", dashboard_api.get_forecast_cost()),
        ("Monthly carbon estimate", dashboard_api.get_monthly_carbon()),
        ("Peak electricity usage", dashboard_api.get_peak_electricity_usage()),
        ("Peak water usage", dashboard_api.get_peak_water_usage()),
        ("Peak natural gas usage", dashboard_api.get_peak_natural_gas_usage()),
        ("Peak fuel usage", dashboard_api.get_peak_fuel_usage()),
    ]

    current_month = now_datetime().date().replace(day=1)
    months = [add_to_date(current_month, months=offset) for offset in range(-5, 1)]
    next_month = add_to_date(current_month, months=1)
    readings = frappe.get_all(
        "Utility Reading",
        filters={
            "reading_date": [
                "between",
                [str(months[0]), str(add_to_date(current_month, months=1, days=-1))],
            ],
            "is_opening_reading": 0,
        },
        fields=["reading_date", "utility_type", "consumption", "utility_meter"],
    )
    meter_rows = frappe.get_all(
        "Utility Meter",
        filters={"is_active": 1},
        fields=["name", "utility_type", "unit_of_measure"],
    )
    utility_types = ("Electricity", "Water", "Natural Gas", "Fuel", "Other")
    month_index = {(month.year, month.month): index for index, month in enumerate(months)}
    actual = {utility_type: [0.0] * len(months) for utility_type in utility_types}
    for row in readings:
        utility_type = row.utility_type if row.utility_type in actual else "Other"
        index = month_index.get((row.reading_date.year, row.reading_date.month))
        if index is not None:
            actual[utility_type][index] += float(row.consumption or 0)

    forecast_totals = {utility_type: 0.0 for utility_type in utility_types}
    units = {}
    for meter in meter_rows:
        utility_type = meter.utility_type if meter.utility_type in forecast_totals else "Other"
        forecast = get_utility_forecast(meter.name)
        forecast_totals[utility_type] += float(forecast.get("forecast_usage") or 0)
        units[utility_type] = meter.unit_of_measure or units.get(utility_type) or "units"

    labels = [str(month)[:10] for month in months] + [str(next_month)[:10]]
    usage_forecast = []
    for utility_type in utility_types:
        values = [round(value, 2) for value in actual[utility_type]]
        predicted = round(forecast_totals[utility_type], 2)
        if not any(values) and not predicted:
            continue
        historical_forecast = []
        for index in range(len(values)):
            prior_values = values[max(0, index - 3) : index]
            historical_forecast.append(
                round(sum(prior_values) / len(prior_values), 2)
                if prior_values
                else None
            )
        usage_forecast.append(
            {
                "utility_type": utility_type,
                "unit": units.get(utility_type, "units"),
                "labels": labels,
                "actual": values + [None],
                "forecast": historical_forecast + [predicted],
            }
        )

    monthly_cost_data = monthly_cost()
    cost_datasets = monthly_cost_data.get("datasets") or []
    cost_length = len(monthly_cost_data.get("labels") or [])
    monthly_cost_trend = [
        round(
            sum(
                float((dataset.get("values") or [0] * cost_length)[index] or 0)
                for dataset in cost_datasets
            ),
            2,
        )
        for index in range(cost_length)
    ]

    reported_meters = [set() for _month in months]
    for row in readings:
        index = month_index.get((row.reading_date.year, row.reading_date.month))
        if index is not None and row.utility_meter:
            reported_meters[index].add(row.utility_meter)
    meter_trend = [len(meters) for meters in reported_meters]

    card_payload = [
        {"label": label, "value": card.get("value")}
        for label, card in cards
    ]
    card_payload[0].update(
        {
            "target": len(meter_rows),
            "trend": meter_trend,
            "trend_type": "bar",
        }
    )
    card_payload[1].update(
        {
            "compact": True,
            "trend": monthly_cost_trend,
            "selectable_comparison": True,
        }
    )
    utility_trends = {
        series["utility_type"]: series["actual"][:-1]
        for series in usage_forecast
    }
    for card_index, utility_type in (
        (5, "Electricity"),
        (6, "Water"),
        (7, "Natural Gas"),
        (8, "Fuel"),
    ):
        card_payload[card_index]["trend"] = utility_trends.get(utility_type, [])

    return {
        "cards": card_payload,
        "monthly_cost": monthly_cost_data,
        "usage_forecast": usage_forecast,
    }


@frappe.whitelist()
def get_sla_performance_analytics():
    """Return live data for the Frappe UI SLA dashboard."""
    from cafm import dashboard as dashboard_api
    from cafm.cafm.dashboard_chart_source.sla_status_breakdown.sla_status_breakdown import get as sla_breakdown

    dashboard_api._require_sla_dashboard_access()
    cards = [
        ("On-track work orders", dashboard_api.get_on_track_work_orders()),
        ("Response breached", dashboard_api.get_response_breached_work_orders()),
        ("Resolution breached", dashboard_api.get_resolution_breached_work_orders()),
        ("SLA met", dashboard_api.get_sla_met_work_orders()),
    ]
    return {
        "cards": [{"label": label, "value": card.get("value")} for label, card in cards],
        "status_breakdown": sla_breakdown(),
    }

import json
import frappe
from frappe.desk.desktop import get_desktop_page as original_get_desktop_page
from frappe.desk.desktop import get_workspace_sidebar_items as original_get_workspace_sidebar_items


FACILITY_SUPERVISOR_ROLES = {"Facility Manager", "Facility Coordinator"}


def _inject_facilities_workspace(result):
    """Expose Facilities to permitted supervisors despite external hiding rules."""
    if not isinstance(result, dict):
        return result
    if not FACILITY_SUPERVISOR_ROLES.intersection(frappe.get_roles()):
        return result

    pages = result.setdefault("pages", [])
    if any(page.get("name") == "Facilities" for page in pages):
        return result
    if not frappe.db.exists("Workspace", "Facilities"):
        return result

    workspace = frappe.get_doc("Workspace", "Facilities")
    pages.append(
        {
            "name": workspace.name,
            "title": workspace.title,
            "for_user": workspace.for_user,
            "content": workspace.content,
            "public": 1,
            "module": workspace.module,
            "icon": workspace.icon,
            "indicator_color": workspace.indicator_color,
            "is_hidden": 0,
            "label": workspace.label or workspace.name,
        }
    )
    return result


def _filter_welcome_message(result):
    pages = result.get("pages") if isinstance(result, dict) else None
    if pages:
        for p in pages:
            if p.get("name") == "Welcome Workspace" and p.get("content"):
                try:
                    blocks = json.loads(p["content"])
                    filtered_blocks = [
                        b for b in blocks
                        if not (
                            b.get("type") == "header"
                            and "hi," in (b.get("data", {}).get("text") or "").lower()
                        )
                        and not (
                            b.get("type") == "paragraph"
                            and "i guess you don't have access" in (b.get("data", {}).get("text") or "").lower()
                        )
                    ]
                    p["content"] = json.dumps(filtered_blocks)
                except Exception:
                    frappe.log_error(frappe.get_traceback(), "Welcome Workspace content filter failed")
    return result


@frappe.whitelist()
def get_desktop_page(page=None):
    result = original_get_desktop_page(page=page)
    return _filter_welcome_message(result)


@frappe.whitelist()
def get_workspace_sidebar_items():
    result = original_get_workspace_sidebar_items()
    result = _inject_facilities_workspace(result)
    return _filter_welcome_message(result)
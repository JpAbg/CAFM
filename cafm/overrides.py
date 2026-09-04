import json
import frappe
from frappe.desk.desktop import get_desktop_page as original_get_desktop_page
from frappe.desk.desktop import get_workspace_sidebar_items as original_get_workspace_sidebar_items


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
    return _filter_welcome_message(result)
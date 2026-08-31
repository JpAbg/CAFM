import frappe
from frappe import _


def validate_inspection_template(template_name, category):
    if not template_name:
        return

    template = frappe.db.get_value(
        "Facility Inspection Template",
        template_name,
        ["is_active", "category"],
        as_dict=True,
    )
    if not template or not template.is_active:
        frappe.throw(_("Inspection Template must be active."))

    if (
        category != "General"
        and template.category
        and template.category not in (category, "General")
    ):
        frappe.throw(
            _(
                "The Inspection Template category must match the "
                "maintenance category or be General."
            )
        )

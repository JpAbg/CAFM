import frappe
from frappe.tests.utils import FrappeTestCase

from cafm.inspection_templates import validate_inspection_template


class TestInspectionTemplateApplicability(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8)
        self.category = self.make_issue_type("Mechanical")
        self.other_category = self.make_issue_type("Electrical")
        self.general_category = self.get_or_create_general_category()
        self.template = frappe.get_doc(
            {
                "doctype": "Facility Inspection Template",
                "template_name": f"CAFM Template {self.suffix}",
                "category": self.category,
                "is_active": 1,
                "items": [
                    {
                        "inspection_point": "Verify safe operation",
                        "is_required": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self.general_template = frappe.get_doc(
            {
                "doctype": "Facility Inspection Template",
                "template_name": f"CAFM General Template {self.suffix}",
                "category": self.general_category,
                "is_active": 1,
                "items": [
                    {
                        "inspection_point": "Verify general safety",
                        "is_required": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True)

    def get_or_create_general_category(self):
        if not frappe.db.exists("Issue Type", "General"):
            frappe.get_doc(
                {
                    "doctype": "Issue Type",
                    "__newname": "General",
                }
            ).insert(ignore_permissions=True)
        return "General"

    def make_issue_type(self, label):
        name = f"CAFM {label} {self.suffix}"
        frappe.get_doc(
            {
                "doctype": "Issue Type",
                "__newname": name,
            }
        ).insert(ignore_permissions=True)
        return name

    def test_template_category_must_match_maintenance_category(self):
        validate_inspection_template(self.template.name, self.category)

        with self.assertRaises(frappe.ValidationError):
            validate_inspection_template(self.template.name, self.other_category)

    def test_general_template_is_allowed_for_any_category(self):
        validate_inspection_template(self.general_template.name, self.category)
        validate_inspection_template(self.general_template.name, self.other_category)

    def test_general_category_allows_any_active_template(self):
        validate_inspection_template(self.template.name, "General")

import frappe
from frappe.tests.utils import FrappeTestCase

from cafm.api import user_maintenance_role_query
from cafm.events.asset_maintenance_team import validate_member_roles
from cafm.events.user import enforce_cafm_demo_user_roles


class TestRoleIntegrity(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.role_row = frappe.get_all(
            "Has Role",
            filters={"parenttype": "User"},
            fields=["parent", "role"],
            order_by="parent asc, role asc",
            limit=1,
        )[0]

    def test_maintenance_role_query_returns_only_selected_user_roles(self):
        results = user_maintenance_role_query(
            "Role",
            "",
            "name",
            0,
            100,
            {"user": self.role_row.parent},
        )
        returned_roles = {row[0] for row in results}
        assigned_roles = set(
            frappe.get_all(
                "Has Role",
                filters={
                    "parent": self.role_row.parent,
                    "parenttype": "User",
                },
                pluck="role",
            )
        )
        self.assertEqual(returned_roles, assigned_roles)

    def test_unassigned_maintenance_role_is_rejected(self):
        assigned_roles = frappe.get_all(
            "Has Role",
            filters={
                "parent": self.role_row.parent,
                "parenttype": "User",
            },
            pluck="role",
        )
        unassigned_role = frappe.get_all(
            "Role",
            filters={"name": ["not in", assigned_roles]},
            pluck="name",
            limit=1,
        )[0]
        doc = frappe._dict(
            maintenance_team_members=[
                frappe._dict(
                    team_member=self.role_row.parent,
                    maintenance_role=unassigned_role,
                )
            ]
        )
        with self.assertRaises(frappe.ValidationError):
            validate_member_roles(doc)

    def test_cafm_demo_user_rejects_unrelated_role_profile(self):
        user_id = "cafm.requester@example.com"
        if not frappe.db.exists("User", user_id):
            self.skipTest("CAFM demo requester is not installed on this site.")

        user = frappe.get_doc("User", user_id)
        user.role_profile_name = "Axiom - Accounting"
        user.set("roles", [{"role": "Axiom Accountant"}])

        enforce_cafm_demo_user_roles(user)

        self.assertIsNone(user.role_profile_name)
        self.assertEqual(
            {row.role for row in user.roles},
            {"Employee", "Requester / Employee"},
        )

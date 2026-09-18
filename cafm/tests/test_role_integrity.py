from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from cafm.api import user_maintenance_role_query
from cafm.events.asset_maintenance_team import validate_member_roles
from cafm.events.user import (
    apply_cafm_role_profile,
    enforce_cafm_demo_user_roles,
    get_cafm_login_redirect,
)
from cafm.www.client_portal import get_context as get_client_portal_context
from cafm.www.employee_portal import get_context as get_employee_portal_context


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

    def test_duplicate_cafm_team_member_is_rejected_within_one_team(self):
        assigned_role = frappe.get_all(
            "Has Role",
            filters={
                "parent": self.role_row.parent,
                "parenttype": "User",
            },
            pluck="role",
            limit=1,
        )[0]
        doc = frappe._dict(
            custom_cafm_team_members=[
                frappe._dict(
                    user=self.role_row.parent,
                    maintenance_role=assigned_role,
                ),
                frappe._dict(
                    user=self.role_row.parent,
                    maintenance_role=assigned_role,
                ),
            ]
        )

        with self.assertRaises(frappe.ValidationError):
            validate_member_roles(doc)

    def test_cafm_demo_user_rejects_unrelated_role_profile(self):
        user_id = "cafm.requester@example.com"
        if not frappe.db.exists("User", user_id):
            self.skipTest("CAFM demo requester is not installed on this site.")

        user = frappe.get_doc("User", user_id)
        user.role_profile_name = "Unrelated Accounting"
        user.set("roles", [{"role": "Unrelated Accountant"}])

        enforce_cafm_demo_user_roles(user)

        self.assertIsNone(user.role_profile_name)
        self.assertEqual(
            {row.role for row in user.roles},
            {"Employee", "Requester / Employee"},
        )

    def test_explicit_employee_profile_replaces_stale_coordinator_roles(self):
        user = frappe.new_doc("User")
        user.name = "profile-change@example.com"
        user.role_profile_name = "CAFM Employee"
        user.custom_cafm_role_profile = "CAFM Facility Coordinator"
        user.set(
            "roles",
            [
                {"role": "Employee"},
                {"role": "Requester / Employee"},
                {"role": "Facility Coordinator"},
            ],
        )

        linked_employee = frappe._dict(
            name="HR-EMP-TEST",
            custom_is_facility_technician=0,
        )
        with patch("cafm.events.user.frappe.db.get_value", return_value=linked_employee):
            apply_cafm_role_profile(user)

        self.assertEqual(user.role_profile_name, "CAFM Employee")
        self.assertEqual(user.custom_cafm_role_profile, "CAFM Employee")
        self.assertEqual(
            {row.role for row in user.roles},
            {"Employee", "Requester / Employee"},
        )

    def test_facility_supervisor_routes_to_facilities_workspace(self):
        with patch(
            "cafm.events.user.frappe.get_roles",
            return_value=["Employee", "Facility Coordinator"],
        ):
            self.assertEqual(
                get_cafm_login_redirect("coordinator@example.com"),
                "/app/facilities",
            )

    def test_client_routes_to_client_portal(self):
        with patch(
            "cafm.events.user.frappe.get_roles",
            return_value=["Client"],
        ), patch("cafm.events.user.frappe.db.exists", return_value=False):
            self.assertEqual(
                get_cafm_login_redirect("client.com"),
                "/client-portal",
            )

    def test_administrator_can_open_client_portal_without_redirect(self):
        self.assertIsNone(get_cafm_login_redirect("Administrator"))
        context = frappe._dict()
        with patch(
            "cafm.www.client_portal.frappe.get_roles",
            return_value=["Administrator", "System Manager"],
        ):
            get_client_portal_context(context)
        self.assertEqual(context.no_cache, 1)

    def test_linked_facility_supervisor_can_open_employee_portal(self):
        context = frappe._dict()
        with patch(
            "cafm.www.employee_portal.frappe.get_roles",
            return_value=["Employee", "Facility Manager"],
        ), patch(
            "cafm.www.employee_portal.get_employee_for_user",
            return_value="HR-EMP-SUPERVISOR",
        ):
            get_employee_portal_context(context)

        self.assertEqual(context.no_cache, 1)

    def test_client_cannot_open_employee_portal(self):
        context = frappe._dict()
        with patch(
            "cafm.www.employee_portal.frappe.get_roles",
            return_value=["Client"],
        ):
            with self.assertRaises(frappe.PermissionError):
                get_employee_portal_context(context)

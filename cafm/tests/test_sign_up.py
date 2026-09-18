from inspect import unwrap
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from cafm.portal import submit_portal_request
from cafm.www.sign_up import sign_up_account


class TestClientSignUp(FrappeTestCase):
    def test_signup_creates_client_requester_and_authenticated_session(self):
        email = f"client.signup.{random_string(8).lower()}@example.com"
        password = "Axiom!Client2026"
        original_user = frappe.session.user
        try:
            with patch("cafm.www.sign_up.LoginManager") as login_manager_class:
                login_manager = login_manager_class.return_value
                login_manager.post_login.side_effect = lambda: frappe.set_user(email)
                result = unwrap(sign_up_account)(
                    "Portal",
                    "Client",
                    email,
                    password,
                    password,
                )
                login_manager.authenticate.assert_called_once_with(user=email, pwd=password)
                login_manager.post_login.assert_called_once_with()
            self.assertTrue(result["created"])
            self.assertEqual(result["redirect_to"], "/client-portal")
            self.assertEqual(frappe.session.user, email)
            self.assertIn("Client", frappe.get_roles(email))
            self.assertEqual(frappe.db.get_value("User", email, "user_type"), "Website User")
            client = frappe.db.get_value(
                "Client", {"user": email, "status": "Active"}, "name"
            )
            self.assertTrue(client)
            location = frappe.get_all("Facility Location", pluck="name", limit=1)[0]
            category = frappe.get_all("Issue Type", pluck="name", limit=1)[0]
            priority = frappe.get_all("Issue Priority", pluck="name", limit=1)[0]
            request = submit_portal_request(
                "Signup portal request",
                location,
                category,
                priority,
                "Created by the signup integration test.",
            )
            self.assertEqual(
                frappe.db.get_value("Issue", request["name"], "raised_by"),
                email,
            )
        finally:
            frappe.set_user(original_user)

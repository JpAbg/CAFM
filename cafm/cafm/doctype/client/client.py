# Copyright (c) 2026, Jean Paul Abou Gharib and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Client(Document):
	def before_save(self):
		if self.client_type == "Company":
			self.client_name = self.company_name
		else:
			self.client_name = " ".join(filter(None, [self.first_name, self.middle_name, self.last_name]))
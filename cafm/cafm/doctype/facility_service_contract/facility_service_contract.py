import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class FacilityServiceContract(Document):
    def validate(self):
        self.validate_dates()
        self.set_contract_status()

    def validate_dates(self):
        if getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("Contract end date cannot be before the start date."))

    def set_contract_status(self):
        if self.contract_status in ("Suspended", "Terminated"):
            return
        if getdate(self.end_date) < getdate(nowdate()):
            self.contract_status = "Expired"
        elif self.contract_status != "Draft" and getdate(self.start_date) <= getdate(nowdate()):
            self.contract_status = "Active"


def contract_covers_work_order(contract, work_order):
    if contract.company != work_order.company:
        return False
    if contract.contract_status != "Active":
        return False
    today = getdate(nowdate())
    if not (getdate(contract.start_date) <= today <= getdate(contract.end_date)):
        return False
    if work_order.vendor and contract.service_provider != work_order.vendor:
        return False

    scope = contract.scope_type
    if scope == "All Assets":
        return True
    if scope == "Facility Location":
        return contract.facility_location == work_order.facility_location
    if scope == "Specific Asset":
        return contract.asset == work_order.asset
    if scope == "Service Category":
        return contract.service_category == work_order.category
    return False


def validate_contract_for_work_order(work_order):
    if not work_order.service_contract:
        return
    contract = frappe.get_doc("Facility Service Contract", work_order.service_contract)
    if not contract_covers_work_order(contract, work_order):
        frappe.throw(
            _("The selected Service Contract is not active or does not cover this work order.")
        )


@frappe.whitelist()
def get_matching_service_contracts(work_order_name):
    if not frappe.has_permission("Facility Work Order", "read", work_order_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    work_order = frappe.get_doc("Facility Work Order", work_order_name)
    contracts = frappe.get_all(
        "Facility Service Contract",
        filters={"company": work_order.company, "contract_status": "Active"},
        fields=["name", "contract_name", "service_provider", "end_date", "contract_value"],
    )
    return [
        contract for contract in contracts
        if contract_covers_work_order(
            frappe.get_doc("Facility Service Contract", contract.name), work_order
        )
    ]

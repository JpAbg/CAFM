import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, now_datetime, nowdate

from cafm.cafm.doctype.facility_service_contract.facility_service_contract import (
    validate_contract_for_work_order,
)


class FacilityVendorQuotation(Document):
    def autoname(self):
        self.name = make_autoname("VQ-.YYYY.-.#####")

    def before_validate(self):
        self.populate_from_work_order()
        self.calculate_total()
        self.update_expiry_status()

    def validate(self):
        self.validate_provider()
        self.validate_contract()

        from cafm.permissions import validate_vendor_quotation_changes

        validate_vendor_quotation_changes(self)

    def populate_from_work_order(self):
        if not self.work_order:
            return
        work_order = frappe.get_doc("Facility Work Order", self.work_order)
        self.company = self.company or work_order.company
        self.quotation_name = self.quotation_name or _(
            "Quotation for {0}"
        ).format(self.work_order)
        self.scope_of_work = self.scope_of_work or work_order.work_description

    def calculate_total(self):
        self.total_amount = flt(self.quoted_amount) + flt(self.tax_amount)

    def update_expiry_status(self):
        if self.quotation_status in ("Selected", "Rejected"):
            return
        if self.valid_until and getdate(self.valid_until) < getdate(nowdate()):
            self.quotation_status = "Expired"

    def validate_provider(self):
        provider_company = frappe.db.get_value(
            "Facility Service Provider", self.service_provider, "company"
        )
        if provider_company and provider_company != self.company:
            frappe.throw(_("The service provider must belong to the quotation company."))

    def validate_contract(self):
        if not self.service_contract:
            return
        contract = frappe.get_doc("Facility Service Contract", self.service_contract)
        if contract.service_provider != self.service_provider:
            frappe.throw(_("The selected Service Contract belongs to another service provider."))


@frappe.whitelist()
def select_vendor_quotation(quotation_name, selection_notes=None):
    allowed_roles = {"Facility Manager", "System Manager"}
    if not allowed_roles.intersection(frappe.get_roles()):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    quotation = frappe.get_doc("Facility Vendor Quotation", quotation_name)
    if not frappe.has_permission("Facility Vendor Quotation", "write", quotation_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    if quotation.quotation_status != "Received":
        frappe.throw(_("Only a received vendor quotation can be selected."))
    if getdate(quotation.valid_until) < getdate(nowdate()):
        quotation.quotation_status = "Expired"
        quotation.save(ignore_permissions=True)
        frappe.throw(_("This quotation has expired and cannot be selected."))

    work_order = frappe.get_doc("Facility Work Order", quotation.work_order)
    if not frappe.has_permission("Facility Work Order", "write", work_order.name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    work_order.assignment_type = "External Vendor"
    work_order.vendor = quotation.service_provider
    work_order.service_contract = quotation.service_contract
    work_order.selected_vendor_quotation = quotation.name
    work_order.external_service_cost = quotation.total_amount
    validate_contract_for_work_order(work_order)
    work_order.save(ignore_permissions=True)

    quotation.quotation_status = "Selected"
    quotation.selected_by = frappe.session.user
    quotation.selected_on = now_datetime()
    quotation.selection_notes = selection_notes or quotation.selection_notes
    quotation.save(ignore_permissions=True)

    for other in frappe.get_all(
        "Facility Vendor Quotation",
        filters={
            "work_order": quotation.work_order,
            "name": ["!=", quotation.name],
            "quotation_status": ["in", ["Draft", "Received"]],
        },
        pluck="name",
    ):
        frappe.db.set_value(
            "Facility Vendor Quotation",
            other,
            "quotation_status",
            "Rejected",
            update_modified=True,
        )
    return work_order.name

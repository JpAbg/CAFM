import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class FacilityServiceProvider(Document):
    def validate(self):
        self.validate_supplier()
        self.validate_contact()
        self.validate_vendor_user()
        self.validate_dates()
        self.validate_categories()
        self.set_availability()

    def validate_supplier(self):
        supplier = frappe.db.get_value(
            "Supplier",
            self.supplier,
            ["disabled"],
            as_dict=True,
        )
        if not supplier:
            frappe.throw(_("The linked ERPNext Supplier does not exist."))
        if supplier.disabled:
            frappe.throw(_("A disabled Supplier cannot be a service provider."))

    def validate_contact(self):
        if not self.service_phone and not self.service_email:
            frappe.throw(
                _("Enter at least a Service Phone or Service Email.")
            )

    def validate_vendor_user(self):
        if not self.vendor_user:
            return

        user = frappe.get_doc("User", self.vendor_user)
        if not user.enabled or user.user_type != "System User":
            frappe.throw(
                _("Vendor User must be an enabled System User.")
            )
        if "Vendor" not in {row.role for row in user.roles}:
            frappe.throw(
                _("Vendor User must have the Vendor role.")
            )

        duplicate = frappe.db.get_value(
            "Facility Service Provider",
            {
                "vendor_user": self.vendor_user,
                "name": ["!=", self.name],
            },
            "name",
        )
        if duplicate:
            frappe.throw(
                _("Vendor User is already linked to Service Provider {0}.").format(
                    duplicate
                )
            )

    def validate_dates(self):
        if (
            self.contract_start_date
            and self.contract_end_date
            and getdate(self.contract_end_date)
            < getdate(self.contract_start_date)
        ):
            frappe.throw(
                _("Contract End Date cannot be earlier than Contract Start Date.")
            )

    def validate_categories(self):
        categories = [row.service_category for row in self.service_categories]
        if len(categories) != len(set(categories)):
            frappe.throw(_("Service Categories cannot contain duplicates."))
        if sum(1 for row in self.service_categories if row.is_primary) > 1:
            frappe.throw(_("Only one Service Category can be primary."))

    def set_availability(self):
        from cafm.assignment import calculate_provider_availability

        self.availability = calculate_provider_availability(self)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def active_supplier_query(
    doctype,
    txt,
    searchfield,
    start,
    page_len,
    filters,
):
    return frappe.db.sql(
        """
        SELECT name, supplier_name
        FROM tabSupplier
        WHERE disabled = 0
          AND (name LIKE %(txt)s OR supplier_name LIKE %(txt)s)
        ORDER BY supplier_name
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )

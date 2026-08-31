import frappe


TEST_COMPANY = "_CAFM Clean Test Company"
TEST_COMPANY_ABBR = "CTC"


def ensure_test_company(test_case):
    """Create the ERPNext masters and company required by CAFM tests."""
    for doctype, name, values in (
        ("Gender", "Male", {"gender": "Male"}),
        ("UOM", "Nos", {"uom_name": "Nos", "enabled": 1}),
        ("Item Group", "All Item Groups", {"item_group_name": "All Item Groups", "is_group": 1}),
    ):
        if not frappe.db.exists(doctype, name):
            frappe.get_doc({"doctype": doctype, **values}).insert(
                ignore_permissions=True
            )

    if not frappe.db.exists("Warehouse Type", "Transit"):
        frappe.get_doc(
            {"doctype": "Warehouse Type", "__newname": "Transit"}
        ).insert(ignore_permissions=True)

    for purpose in ("Material Receipt", "Material Issue"):
        if not frappe.db.exists("Stock Entry Type", purpose):
            frappe.get_doc(
                {
                    "doctype": "Stock Entry Type",
                    "__newname": purpose,
                    "purpose": purpose,
                    "is_standard": 1,
                }
            ).insert(ignore_permissions=True)

    frappe.local.flags.ignore_chart_of_accounts = False
    if frappe.db.exists("Company", TEST_COMPANY):
        company = frappe.get_doc("Company", TEST_COMPANY)
    else:
        company = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": TEST_COMPANY,
                "abbr": TEST_COMPANY_ABBR,
                "country": "India",
                "default_currency": "INR",
                "create_chart_of_accounts_based_on": "Standard Template",
                "chart_of_accounts": "Standard",
            }
        ).insert(ignore_permissions=True)

    test_case.company = company.name

    today = frappe.utils.getdate()
    fiscal_year = f"_CAFM Test FY {today.year}"
    if not frappe.db.exists("Fiscal Year", fiscal_year):
        frappe.get_doc(
            {
                "doctype": "Fiscal Year",
                "year": fiscal_year,
                "year_start_date": f"{today.year}-01-01",
                "year_end_date": f"{today.year}-12-31",
                "companies": [{"company": company.name}],
            }
        ).insert(ignore_permissions=True)

    return test_case.company


def make_test_asset(company, facility_location, suffix, asset_name):
    fixed_asset_account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "account_type": "Fixed Asset",
            "is_group": 0,
        },
        "name",
    )
    if not fixed_asset_account:
        frappe.throw("Test company has no fixed asset account")

    category = f"CAFM Test Asset Category {suffix}"
    frappe.get_doc(
        {
            "doctype": "Asset Category",
            "asset_category_name": category,
            "accounts": [
                {
                    "company_name": company,
                    "fixed_asset_account": fixed_asset_account,
                }
            ],
        }
    ).insert(ignore_permissions=True)

    item_code = f"CAFM-TEST-ASSET-{suffix}"
    frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_code,
            "description": "CAFM maintenance test asset",
            "asset_category": category,
            "item_group": "All Item Groups",
            "stock_uom": "Nos",
            "is_stock_item": 0,
            "is_fixed_asset": 1,
            "auto_create_assets": 0,
        }
    ).insert(ignore_permissions=True)

    erpnext_location = frappe.db.get_value(
        "Facility Location", facility_location, "erpnext_location"
    )
    return frappe.get_doc(
        {
            "doctype": "Asset",
            "asset_name": asset_name,
            "item_code": item_code,
            "asset_category": category,
            "company": company,
            "purchase_date": "2025-01-01",
            "available_for_use_date": "2025-01-01",
            "gross_purchase_amount": 1000,
            "purchase_amount": 1000,
            "calculate_depreciation": 0,
            "is_existing_asset": 1,
            "asset_owner": "Company",
            "location": erpnext_location,
            "custom_asset_location": facility_location,
            "custom_operational_status": "Out of Service",
        }
    ).insert(ignore_permissions=True)

app_name = "cafm"
app_title = "CAFM"
app_publisher = "Jean Paul Abou Gharib"
app_description = "A complete Computer-Aided Facility Management (CAFM) web-app"
app_email = "abougharib.jp@gmail.com"
app_license = "mit"

required_apps = ["erpnext", "hrms"]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "cafm",
# 		"logo": "/assets/cafm/logo.png",
# 		"title": "CAFM",
# 		"route": "/cafm",
# 		"has_permission": "cafm.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/cafm/css/cafm.css"
app_include_js = [
    "/assets/cafm/js/custom-dashboard-chart.js?v=20",
    "/assets/cafm/js/facility_asset_filters.js?v=6",
    "/assets/cafm/js/welcome-workspace-launcher.js?v=8",
]

# include js, css files in header of web template
# web_include_css = "/assets/cafm/css/cafm.css"
# web_include_js = "/assets/cafm/js/cafm.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "cafm/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
    "Asset": "public/js/asset.js",
    "Asset Maintenance Team": "public/js/asset_maintenance_team.js",
    "Issue": "public/js/issue.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "cafm/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
#home_page = "welcome-workspace"

#role_home_page = {
#    "Administrator": "home",
#    "System Manager": "home",
#    "Facility Manager": "home",
#    "Facility Coordinator": "home"
#}

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "cafm.utils.jinja_methods",
# 	"filters": "cafm.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "cafm.install.before_install"
# after_install = "cafm.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "cafm.uninstall.before_uninstall"
# after_uninstall = "cafm.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "cafm.utils.before_app_install"
# after_app_install = "cafm.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "cafm.utils.before_app_uninstall"
# after_app_uninstall = "cafm.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "cafm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"cafm.tasks.all"
# 	],
# 	"daily": [
# 		"cafm.tasks.daily"
# 	],
# 	"hourly": [
# 		"cafm.tasks.hourly"
# 	],
# 	"weekly": [
# 		"cafm.tasks.weekly"
# 	],
# 	"monthly": [
# 		"cafm.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "cafm.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
    "frappe.desk.desktop.get_desktop_page": "cafm.overrides.get_desktop_page",
    "frappe.desk.desktop.get_workspace_sidebar_items": "cafm.overrides.get_workspace_sidebar_items"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "cafm.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["cafm.utils.before_request"]
# after_request = ["cafm.utils.after_request"]

# Job Events
# ----------
# before_job = ["cafm.utils.before_job"]
# after_job = ["cafm.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"cafm.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


website_route_rules = [{'from_route': '/dashboard/<path:app_path>', 'to_route': 'dashboard'},]

doc_events = {
    "Issue": {
        "validate": "cafm.events.issue.validate_cafm_issue",
    },
    "Asset": {
        "validate": "cafm.events.asset.validate_cafm_asset",
        "after_insert": "cafm.events.asset.create_asset_qr_code",
    },
    "Asset Maintenance Team": {
        "validate": "cafm.events.asset_maintenance_team.validate_member_roles",
    },
    "Employee": {
        "before_validate": "cafm.events.employee.create_employee_user_account",
        "validate": "cafm.events.employee.validate_cafm_employee",
        "on_update": [
            "cafm.events.employee.ensure_employee_user_roles",
            "cafm.events.employee.update_cafm_employee_availability",
            "cafm.events.employee.sync_employee_user_name",
        ],
    },
    "User": {
        "validate": "cafm.events.user.enforce_cafm_demo_user_roles",
    },
    "Stock Entry": {
        "validate": "cafm.events.stock_entry.validate_facility_material_issue",
        "before_cancel": "cafm.events.stock_entry.prevent_closed_work_order_material_cancellation",
        "on_submit": "cafm.events.stock_entry.sync_facility_material_issue",
        "on_cancel": "cafm.events.stock_entry.clear_facility_material_issue",
    },
    "Leave Application": {
        "on_submit": "cafm.events.employee.update_leave_employee_availability",
        "on_cancel": "cafm.events.employee.update_leave_employee_availability",
        "on_update_after_submit": "cafm.events.employee.update_leave_employee_availability",
    },
}

after_install = "cafm.setup.install.after_install"
after_migrate = "cafm.setup.install.after_migrate"

permission_query_conditions = {
    "Issue": "cafm.permissions.issue_query",
    "Facility Work Order": "cafm.permissions.work_order_query",
    "Facility Inspection": "cafm.permissions.inspection_query",
    "Facility Service Provider": "cafm.permissions.service_provider_query",
    "Facility Vendor Quotation": "cafm.permissions.vendor_quotation_query",
    "Facility Service Contract": "cafm.permissions.service_contract_query",
}

has_permission = {
    "Issue": "cafm.permissions.has_issue_permission",
    "Facility Work Order": "cafm.permissions.has_work_order_permission",
    "Facility Inspection": "cafm.permissions.has_inspection_permission",
    "Facility Service Provider": (
        "cafm.permissions.has_service_provider_permission"
    ),
    "Facility Vendor Quotation": (
        "cafm.permissions.has_vendor_quotation_permission"
    ),
    "Facility Service Contract": (
        "cafm.permissions.has_service_contract_permission"
    ),
}

scheduler_events = {
    "daily": [
        "cafm.tasks.daily",
    ],
    "hourly": [
        "cafm.tasks.hourly",
    ],
}


doc_events["Utility Reading"] = {"validate": "cafm.utilities.apply_carbon_emissions"}

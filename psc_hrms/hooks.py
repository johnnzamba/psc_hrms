app_name = "psc_hrms"
app_title = "Psc Hrms"
app_publisher = "Techsavanna Technology"
app_description = "Parklands Sports Club Customizations for HR Module"
app_email = "john@techsavanna.technology"
app_license = "mit"

# Apps
# ------------------
after_install = "psc_hrms.apis.helpers.after_install" #Disabled for Automated Allocation
after_migrate = [ 
    "psc_hrms.apis.minefields.create_or_update_half_day_status",
    # "psc_hrms.apis.cron_jobs.set_user_permissions"
]

# Scheduled Tasks
# ---------------

scheduler_events = {
    "*/5 * * * *":{
        "psc_hrms.apis.cron_jobs.set_user_permissions"
    }
	# "daily": [
	#	"psc_hrms.apis.cron_jobs.set_leave_days"
	# ],
    # "daily": [
    #     "psc_hrms.apis.cron_jobs.expire_leave_allocation"
    # ]
}
fixtures = [
    {
        "doctype": "Workflow State"
    },
    {
        "doctype": "Workflow Action Master"
    },
    {
        "doctype": "Client Script",
        "filters": [["name", "in", ["Set Effective Dates", "Leave Allocation Inner Button", "Leave Allocation for Staff", "Filter By dept", "Leave Application by 3rd Party"]]]
    },
    {
        "doctype": "Workflow",
        "filters": [["name", "in", ["Leave Application", "Claim Form Workflow"]]]
    },
    {
        "doctype": "Role",
        "filters": [["name", "in", ["HR Manager", "HR User"]]]
    },
    {
        "doctype": "Email Template",
        "filters": [["name", "in", ["Informative Notice for Leave", "Leave Status Notification", "Leave Approval Template", "Claim Form Informative Notices"]]]
    }
]
# required_apps = []

# Hooks

doc_events = {
	"Leave Application": {
        "on_update": [
            "psc_hrms.apis.helpers.dispatch_mails",
            "psc_hrms.apis.helpers.dispatch_notices"
        ]
	},
    "Public Holiday and Off Days Claim Form": {
        "on_submit": "psc_hrms.psc_hrms.doctype.public_holiday_and_off_days_claim_form.public_holiday_and_off_days_claim_form.notify_supervisor",
        "on_update_after_submit": "psc_hrms.psc_hrms.doctype.public_holiday_and_off_days_claim_form.public_holiday_and_off_days_claim_form.notify_users"
    }
}

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "psc_hrms",
# 		"logo": "/assets/psc_hrms/logo.png",
# 		"title": "Psc Hrms",
# 		"route": "/psc_hrms",
# 		"has_permission": "psc_hrms.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/psc_hrms/css/psc_hrms.css"
# app_include_js = "/assets/psc_hrms/js/psc_hrms.js"

# include js, css files in header of web template
# web_include_css = "/assets/psc_hrms/css/psc_hrms.css"
# web_include_js = "/assets/psc_hrms/js/psc_hrms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "psc_hrms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "psc_hrms/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "psc_hrms.utils.jinja_methods",
# 	"filters": "psc_hrms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "psc_hrms.install.before_install"

# Uninstallation
# ------------

# before_uninstall = "psc_hrms.uninstall.before_uninstall"
# after_uninstall = "psc_hrms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "psc_hrms.utils.before_app_install"
# after_app_install = "psc_hrms.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "psc_hrms.utils.before_app_uninstall"
# after_app_uninstall = "psc_hrms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "psc_hrms.notifications.get_notification_config"

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

# Testing
# -------

# before_tests = "psc_hrms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "psc_hrms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "psc_hrms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["psc_hrms.utils.before_request"]
# after_request = ["psc_hrms.utils.after_request"]

# Job Events
# ----------
# before_job = ["psc_hrms.utils.before_job"]
# after_job = ["psc_hrms.utils.after_job"]

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
# 	"psc_hrms.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


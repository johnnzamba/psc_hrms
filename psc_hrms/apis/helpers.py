# psc_hrms/apis/helpers.py
import frappe
import hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment as lpa_module

def after_install():
    """
    Called after psc_hrms installation. Monkey-patch core on_submit as a safety.
    """
    lpa_module.LeavePolicyAssignment.on_submit = lambda self: None
    frappe.logger().info("Disabled core LeavePolicyAssignment.on_submit via after_install")

import frappe
from frappe.utils import get_fullname

def send_employee_notification(doc):
    """
    Send a status notification email to the employee using the 'Leave Status Notification' template.
    """
    employee = frappe.get_doc("Employee", doc.employee)
    employee_emails = []
    
    # Collect employee's personal and company emails if available
    if employee.prefered_email:
        employee_emails.append(employee.prefered_email)
    
    # Proceed only if there are email addresses
    if employee_emails:
        # Load the notification template
        notification_tmpl = frappe.get_doc("Email Template", "Leave Status Notification")
        context = doc.as_dict()
        notification_subject = frappe.render_template(notification_tmpl.subject, context)
        notification_body = frappe.render_template(notification_tmpl.response, context)
        
        # Send the notification email to all employee email addresses
        frappe.sendmail(
            recipients=employee_emails,
            subject=notification_subject,
            message=notification_body,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            now=True
        )
    else:
        frappe.log_error(f"Employee {employee.name} has no email addresses set")

def dispatch_mails(doc=None, method=None, doc_name=None):
    """
    Send contextual emails on Leave Application workflow transitions and handle status updates.
    Supports manual testing by passing `doc_name`.
    """
    frappe.logger().info(f"dispatch_mails called for doc: {doc.name}, workflow_state: {doc.workflow_state}")
    # If called with a doc_name (for testing), load that doc
    if doc_name:
        doc = frappe.get_doc("Leave Application", doc_name)

    # Define the template mapping for pending approval states
    template_map = {
        # "Pending Approval by Supervisor": "Leave Approval Template",
        "Pending Approval by HOD": "Leave Approval Template",
        "Pending Approval by HRM": "Leave Approval Template",
    }

    # Check if the current workflow_state requires sending approval emails
    template_name = template_map.get(doc.workflow_state)
    if template_name:
        tmpl = frappe.get_doc("Email Template", template_name)
        context = doc.as_dict()
        subject = frappe.render_template(tmpl.subject, context)
        body = frappe.render_template(tmpl.response, context)

        # Determine recipients based on workflow_state
        recipients = []
        if doc.workflow_state == "Pending Approval by Supervisor":
            emp = frappe.get_doc("Employee", doc.employee)
            if not emp.reports_to:
                frappe.log_error(f"Employee {emp.name} has no reports_to set")
                return
            sup = frappe.get_doc("Employee", emp.reports_to)
            recipient = sup.personal_email or sup.company_email
            if not recipient:
                frappe.log_error(f"Supervisor {sup.name} has no email address")
                return
            recipients = [recipient]
        elif doc.workflow_state == "Pending Approval by HOD":
            # Fetch department filtering by name and company
            department = frappe.get_doc("Department", {"name": doc.department, "company": doc.company})
            if not department:
                frappe.log_error(f"Department {doc.department} not found for company {doc.company}")
                return
            # Fetch all leave approvers from the department
            for row in department.leave_approvers:
                user = frappe.get_doc("User", row.approver)
                if user.email:
                    recipients.append(user.email)
            if not recipients:
                frappe.log_error(f"No leave approvers with email found for department {doc.department}")
                return
        elif doc.workflow_state == "Pending Approval by HRM":
            # Fetch all users with role "HR Manager"
            hr_managers = frappe.get_all(
                "User",
                filters={
                    "role": "HR Manager",
                    "enabled": 1
                },
                fields=["email"]
            )
            recipients = [user.email for user in hr_managers if user.email]
            if not recipients:
                frappe.log_error("No HR Managers with email addresses found")
                return

        # If no recipients are determined, exit the email sending process
        if not recipients:
            return

        # Send individual emails to each recipient
        for recipient in recipients:
            frappe.sendmail(
                recipients=[recipient],
                subject=subject,
                message=body,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                now=True
            )

    if doc.workflow_state == "Pending Approval by HRM":
        doc.status = "Approved"
        doc.save()

    # Send employee notification for Approved state
    if doc.workflow_state == "Approved":
        send_employee_notification(doc)


import frappe
from frappe.utils import flt

@frappe.whitelist()
def allocate_leave_days(employee, leave_type, leave_days, from_date, to_date, additional_description=''):
    """
    Allocates leave days for an employee by creating and submitting a Leave Allocation document.
    """
    # Fetch employee details
    emp = frappe.get_doc('Employee', employee)

    # Build and submit Leave Allocation
    alloc = frappe.new_doc('Leave Allocation')
    alloc.employee             = emp.name
    alloc.employee_name        = emp.employee_name
    alloc.department           = emp.department
    alloc.company              = emp.company
    alloc.leave_type           = leave_type
    alloc.from_date            = from_date
    alloc.to_date              = to_date
    alloc.new_leaves_allocated = flt(leave_days)
    alloc.carry_forward        = 1
    alloc.description          = additional_description

    alloc.insert(ignore_permissions=True)
    alloc.submit()

    return alloc.name


import frappe

@frappe.whitelist()
def user_can_allocate_leave():
    """
    Return True if the current user:
    - has the 'HR Manager' role, OR
    - is present in any Department.leave_approvers table.
    """
    user = frappe.session.user

    # 1) Check if user has the HR Manager role
    roles = frappe.get_roles(user)
    if "HR Manager" in roles:
        return True

    # 2) Otherwise look for them in any Department’s leave_approvers
    approver_depts = frappe.db.sql_list(
        """
        SELECT parent
        FROM `tabDepartment Approver`
        WHERE approver = %s
        """,
        user
    )
    return bool(approver_depts)

import frappe

@frappe.whitelist()
def dispatch_notices(doc=None, method=None, doc_name=None):
    """
    On submit of Leave Application, notify the stand-in employee via
    the 'Informative Notice for Leave' Email Template.

    Allows manual testing by passing `doc_name`.
    """
    # If called with doc_name for testing, load that document
    if doc_name:
        doc = frappe.get_doc("Leave Application", doc_name)

    # 1) Grab the stand-in Employee link
    stand_in = doc.custom_who_is_to_stand_in_place_while_absent
    if not stand_in:
        frappe.logger().debug(f"No stand-in defined for {doc.name}")
        return

    # 2) Fetch Employee record for email
    emp = frappe.get_doc("Employee", stand_in)
    recipient = emp.personal_email or emp.company_email
    if not recipient:
        frappe.log_error(
            message=f"Employee {emp.name} has no email address",
            title="Dispatch Notices"
        )
        return

    # 3) Load the Email Template
    try:
        tmpl = frappe.get_doc("Email Template", "Informative Notice for Leave")
    except frappe.DoesNotExistError:
        frappe.log_error(
            message="Email Template 'Informative Notice for Leave' not found",
            title="Dispatch Notices"
        )
        return

    # 4) Render with context
    context = doc.as_dict()
    subject = frappe.render_template(tmpl.subject, context)
    body = frappe.render_template(tmpl.response, context)

    # 5) Send the email
    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=body,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            # now=True
        )
        frappe.logger().info(f"Dispatched notice to {recipient} for {doc.name}")
    except Exception as e:
        frappe.log_error(
            message=f"Failed to send dispatch notice to {recipient} for {doc.name}: {e}",
            title="Dispatch Notices"
        )
import json
import frappe
import datetime
from datetime import date

@frappe.whitelist()
def get_leave_approver(employee):
    """
    Returns the appropriate leave approver for the given employee.
    """
    # Try direct leave_approver on Employee
    leave_approver, department = frappe.db.get_value(
        "Employee", employee,
        ["leave_approver", "department"]
    )

    # If not set, fallback to first Department Approver
    if not leave_approver and department:
        leave_approver = frappe.db.get_value(
            "Department Approver",
            {"parent": department, "parentfield": "leave_approvers", "idx": 1},
            "approver"
        )

    return leave_approver


@frappe.whitelist()
def create_leave_applications(employee, applications):
    """
    Creates Leave Application docs for the given employee and list of applications.
    Automatically sets leave_approver via get_leave_approver().
    """
    created = []

    # Determine the approver and their name once
    approver = get_leave_approver(employee)
    approver_name = None
    if approver:
        approver_name = frappe.db.get_value("Employee", approver, "employee_name")

    for app in json.loads(applications):
        employee_doc = frappe.get_doc("Employee", employee)

        la = frappe.new_doc("Leave Application")
        la.update({
            "employee": employee,
            "employee_name": employee_doc.employee_name,
            "leave_type": app["leave_type"],
            "from_date": app["from_date"],
            "to_date": app["to_date"],
            "company": employee_doc.company,
            "department": employee_doc.department,
            "leave_approver": approver,
            "leave_approver_name": approver_name,
            "posting_date": date.today()
        })
        la.insert()
        created.append(la.name)

    return created

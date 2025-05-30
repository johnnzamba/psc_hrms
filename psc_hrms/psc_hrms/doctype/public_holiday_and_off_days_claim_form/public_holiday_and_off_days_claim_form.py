# Copyright (c) 2025, Techsavanna Technology and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe.model.naming import make_autoname
from frappe.utils import today
from frappe import _

class PublicHolidayandOffDaysClaimForm(Document):
    def autoname(self):
        emp_name = None
        if self.for_staff:
            try:
                emp_name = frappe.get_value("Employee", self.for_staff, "employee_name")
            except Exception:
                frappe.logger().warning(f"Could not fetch employee_name for {self.for_staff}")

        if not emp_name:
            if self.meta.get("autoname"):
                emp_name = make_autoname(self.meta.autoname)
            else:
                emp_name = frappe.generate_hash()[:8]
        self.name = f"{emp_name} | {today()}"


import frappe
from frappe import _

def notify_supervisor(doc, method=None):
    """
    Handle supervisor notification specifically for on_submit hook
    Only sends email when workflow_state is "Pending Approval by Supervisor"
    """
    if doc.workflow_state != "Pending Approval by Supervisor":
        return
    
    template_name = "Claim Form Informative Notices"
    
    try:
        email_template = frappe.get_doc("Email Template", template_name)
    except frappe.DoesNotExistError:
        frappe.log_error(_("Email Template '{0}' not found").format(template_name))
        return

    context = doc.as_dict()
    subject = frappe.render_template(email_template.subject, context)
    message = frappe.render_template(email_template.response, context)
    
    if not doc.for_staff:
        frappe.log_error(_("Employee not specified in document"))
        return
        
    try:
        employee = frappe.get_doc("Employee", doc.for_staff)
        if not employee.reports_to:
            frappe.log_error(_("No supervisor set for employee: {0}").format(employee.name))
            return
            
        supervisor = frappe.get_doc("Employee", employee.reports_to)
        if not supervisor.prefered_email:
            frappe.log_error(_("No email found for supervisor: {0}").format(supervisor.name))
            return
            
        frappe.sendmail(
            recipients=[supervisor.prefered_email],
            subject=subject,
            message=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            now=True
        )
        
    except Exception as e:
        frappe.log_error(_("Error processing supervisor notification: {0}").format(str(e)))

import frappe
import re
from frappe import _
from frappe.utils import flt, today, getdate, now_datetime
from datetime import date

def notify_users(doc=None, method=None, doc_name=None):
    """
    Handle all notifications for on_update_after_submit hook:
    - HOD and HRM approvals
    - Supervisor resubmissions
    - Sets approval timestamp and creates Leave Allocation for final state
    """
    # Support manual testing
    if doc_name:
        doc = frappe.get_doc("Public Holiday and Off Days Claim Form", doc_name)
        if doc.docstatus != 1:
            frappe.throw("Document must be submitted for testing")

    # Ensure we only process submitted documents
    if not doc_name and doc.docstatus != 1:
        return

    # Define states and template
    pending_states = [
        "Pending Approval by HOD",
        "Pending Approval by HRM",
        "Pending Approval by Supervisor"  # For resubmission cases
    ]
    template_name = "Claim Form Informative Notices"
    
    # Process workflow state changes
    if doc.workflow_state in pending_states:
        try:
            email_template = frappe.get_doc("Email Template", template_name)
        except frappe.DoesNotExistError:
            frappe.log_error(_("Email Template '{0}' not found").format(template_name))
            return

        context = doc.as_dict()
        subject = frappe.render_template(email_template.subject, context)
        message = frappe.render_template(email_template.response, context)
        recipients = []
        error_logged = False

        # HOD Approval Path
        if doc.workflow_state == "Pending Approval by HOD":
            if not doc.department:
                frappe.log_error(_("Department not set in document"))
                error_logged = True
            else:
                try:
                    department = frappe.get_doc("Department", doc.department)
                    if hasattr(department, 'leave_approvers'):
                        approvers = [row.approver for row in department.leave_approvers if row.approver]
                        if approvers:
                            recipients = approvers
                        else:
                            frappe.log_error(_("No approvers found in department: {0}").format(doc.department))
                            error_logged = True
                    else:
                        frappe.log_error(_("Department {0} has no leave_approvers table").format(doc.department))
                        error_logged = True
                except Exception as e:
                    frappe.log_error(_("Error fetching department approvers: {0}").format(str(e)))
                    error_logged = True

        # HRM Approval Path
        elif doc.workflow_state == "Pending Approval by HRM":
            hr_managers = frappe.get_all(
                "Has Role",
                filters={
                    "role": "HR Manager",
                    "parenttype": "User"
                },
                distinct=True,
                pluck="parent"
            )
            if hr_managers:
                recipients = frappe.get_all(
                    "User",
                    filters={"name": ["in", hr_managers], "enabled": 1},
                    pluck="email"
                )
            if not recipients:
                frappe.log_error(_("No active HR Managers found with valid email addresses"))
                error_logged = True

        # Supervisor Resubmission Path
        elif doc.workflow_state == "Pending Approval by Supervisor":
            if not doc.for_staff:
                frappe.log_error(_("Employee not specified in document"))
                error_logged = True
            else:
                try:
                    employee = frappe.get_doc("Employee", doc.for_staff)
                    if not employee.reports_to:
                        frappe.log_error(_("No supervisor set for employee: {0}").format(employee.name))
                        error_logged = True
                    else:
                        supervisor = frappe.get_doc("Employee", employee.reports_to)
                        if supervisor.prefered_email:
                            recipients = [supervisor.prefered_email]
                        else:
                            frappe.log_error(_("No email found for supervisor: {0}").format(supervisor.name))
                            error_logged = True
                except Exception as e:
                    frappe.log_error(_("Error fetching supervisor: {0}").format(str(e)))
                    error_logged = True

        # Send emails if valid recipients
        if recipients and not error_logged:
            frappe.sendmail(
                recipients=recipients,
                subject=subject,
                message=message,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                now=True
            )

    # Handle final approval state
    if doc.workflow_state == "Approved by HRM":
        # # Set approval timestamp
        # frappe.db.set_value(
        #     doc.doctype,
        #     doc.name,
        #     "approved_on",
        #     now_datetime(),
        #     update_modified=False
        # )
        
        try:
            # Extract numeric value from eligible_days (e.g., "1 Day(s)" -> 1.0)
            days_match = re.search(r"(\d+(\.\d+)?)", doc.eligible_days)
            if not days_match:
                frappe.throw(_("Could not parse eligible days: {0}").format(doc.eligible_days))
            new_leaves = flt(days_match.group(1))
            
            # Get department details
            department = frappe.get_doc("Department", doc.department)
            
            # Calculate existing allocations
            existing_allocs = frappe.get_all(
                "Leave Allocation",
                filters={
                    "employee": doc.for_staff,
                    "leave_type": "Public Holiday compensation",
                    "expired": 0,
                    "docstatus": 1
                },
                fields=["SUM(total_leaves_allocated) as total_allocated"]
            )
            
            total_existing = flt(existing_allocs[0].total_allocated) if existing_allocs else 0
            new_total = total_existing + new_leaves
            
            # Calculate end of year date
            current_year = date.today().year
            to_date = getdate(f"{current_year}-12-31")
            
            # Create new Leave Allocation
            alloc_doc = frappe.get_doc({
                "doctype": "Leave Allocation",
                "employee": doc.for_staff,
                "posting_date": today(),
                "department": doc.department,
                "company": department.company,
                "leave_type": "Public Holiday compensation",
                "from_date": today(),
                "to_date": to_date,
                "new_leaves_allocated": new_leaves,
                "carry_forward": 1,
                "total_leaves_allocated": new_total,
                "description": "AUTOGENERATED by Claim Form APPROVED."
            })
            
            alloc_doc.insert(ignore_permissions=True)
            alloc_doc.submit()
            frappe.db.set_value(
				doc.doctype,
				doc.name,
				{
					"leave_allocation": alloc_doc.name,
					"approved_on": now_datetime()
				},
				update_modified=False
			)
            
            frappe.msgprint(_("Leave Allocation {0} created and linked successfully").format(
				frappe.utils.get_link_to_form("Leave Allocation", alloc_doc.name)
			))
						
        except Exception as e:
            frappe.log_error(_("Error creating Leave Allocation: {0}").format(str(e)))
            frappe.msgprint(_("Failed to create Leave Allocation: {0}").format(str(e)), alert=True, indicator="red")
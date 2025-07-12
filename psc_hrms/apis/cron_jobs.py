# file: psc_hrms/apis/cron_jobs.py

import frappe
from frappe.utils import getdate, nowdate, flt
from datetime import timedelta, date
import calendar

def set_leave_days():
    """Called monthly via scheduler_events. On the last day of each month,
    allocate one-twelfth of each leave policy's annual allocation to all
    active assignments for the next month."""
    today = getdate(nowdate())
    # today = getdate("31-05-2025")
    # only run on last day of month
    last_day = calendar.monthrange(today.year, today.month)[1]
    if today.day != last_day:
        return

    current_year = today.year

    # 1. fetch all Leave Policies for this calendar year
    policies = frappe.get_all(
        "Leave Policy",
        filters={"custom_policy_for_year": current_year},
        fields=["name"]
    )

    # compute next month start/end
    # trick: move to day 28 + 4 days -> always next month, then force day=1
    nxt = today.replace(day=28) + timedelta(days=4)
    next_start = nxt.replace(day=1)
    next_end = next_start.replace(day=calendar.monthrange(next_start.year, next_start.month)[1])

    for p in policies:
        # 2. child table entries: leave_type & annual_allocation
        details = frappe.get_all(
            "Leave Policy Detail",
            filters=[
                ["parent", "=", p.name],
                ["leave_type", "!=", "Sick Leave"]
            ],
            fields=["leave_type", "annual_allocation"]
        )

        # 3. all assignments under this policy
        assignments = frappe.get_all(
            "Leave Policy Assignment",
            filters={"leave_policy": p.name},
            fields=["name", "employee", "company", "effective_from", "effective_to"]
        )

        for a in assignments:
            eff_from = getdate(a.effective_from)
            eff_to   = getdate(a.effective_to)
            # only active assignments
            if not (eff_from <= today <= eff_to):
                continue

            for d in details:
                # per-month allocation
                monthly_alloc = flt(d.annual_allocation) / 12.0

                # sum up existing non-expired allocations for this assignment & type
                existing = frappe.get_all(
                    "Leave Allocation",
                    filters={
                        "leave_policy_assignment": a.name,
                        "leave_type": d.leave_type,
                        "expired": 0
                    },
                    fields=["total_leaves_allocated"]
                )
                total_prev = sum(flt(e.total_leaves_allocated) for e in existing)

                # build & insert new Leave Allocation
                new_total = total_prev + monthly_alloc
                alloc_doc = frappe.get_doc({
                    "doctype": "Leave Allocation",
                    "employee": a.employee,
                    "company": a.company,
                    "leave_type": d.leave_type,
                    "from_date": next_start,
                    "to_date": eff_to,
                    "new_leaves_allocated": monthly_alloc,
                    "carry_forward": 1,
                    "total_leaves_allocated": new_total,
                    "leave_policy": p.name,
                    "leave_policy_assignment": a.name
                })
                alloc_doc.insert(ignore_permissions=True)
                alloc_doc.submit()

import frappe

def set_user_permissions():
    """
    Cron job to sync User Permissions for Employees:
      0. For each Employee, create default permission for their own Employee record
      1. For each distinct leave_approver on Employee, grant permission on Employee to that approver.
      2. For each Employee by department, fetch Department Approver entries and grant permission on Employee to each.
    Avoids duplicates by checking existing User Permission docs.
    """
    # Part 0: Create default Employee permissions for all Employees
    employees = frappe.get_all(
        "Employee",
        fields=["name", "user_id", "company"],
        filters={"user_id": ["!=", ""]}
    )
    
    for emp in employees:
        # Create Employee permission
        _create_permission(
            user=emp.user_id,
            allow="Employee",
            for_value=emp.name,
            apply_to_all_doctypes=1,
            is_default=1
        )
        
        # Create Company permission if company exists
        if emp.company:
            _create_permission(
                user=emp.user_id,
                allow="Company",
                for_value=emp.company,
                apply_to_all_doctypes=1
            )

    # Part 1: Permissions for direct leave_approver (non-empty)
    employees = frappe.get_all(
        "Employee",
        fields=["name", "leave_approver"],
        filters={"leave_approver": ["!=", ""]}
    )

    # Group by leave_approver
    approver_map = {}
    for emp in employees:
        approver = emp.leave_approver
        approver_map.setdefault(approver, []).append(emp.name)

    for approver, emp_list in approver_map.items():
        for emp_name in emp_list:
            _create_permission(
                user=approver,
                allow="Leave Application",
                for_value=emp_name,
                apply_to_all_doctypes=1
            )

    # Part 2: Permissions for department-level approvers
    # Fetch distinct non-empty departments
    departments = frappe.get_all(
        "Employee",
        filters={"department": ["!=", ""]},
        fields=["department"],
        distinct=True
    )

    for d in departments:
        dept = d.department
        # Get approvers from Department Approver child table
        approver_rows = frappe.get_all(
            "Department Approver",
            fields=["approver"],
            filters={
                "parent": dept,
                "parentfield": "leave_approvers"
            }
        )
        approvers = {row.approver for row in approver_rows if row.approver}

        # For each employee in this department
        emp_in_dept = frappe.get_all(
            "Employee",
            filters={"department": dept},
            fields=["name"]
        )
        for approver in approvers:
            for emp in emp_in_dept:
                _create_permission(
                    user=approver,
                    allow="Employee",
                    for_value=emp.name,
                    apply_to_all_doctypes=1
                )

def _create_permission(user, allow, for_value, apply_to_all_doctypes=0, is_default=0):
    """
    Helper to create a User Permission if it does not already exist.
    """
    if not user or not for_value:
        return

    try:
        # Build existence check filters
        filters = {
            "user": user,
            "allow": allow,
            "for_value": for_value,
            "apply_to_all_doctypes": apply_to_all_doctypes
        }
        
        # Only include is_default in check if it's set to 1
        if is_default:
            filters["is_default"] = 1

        exists = frappe.db.exists("User Permission", filters)
        
        if not exists:
            perm = frappe.get_doc({
                "doctype": "User Permission",
                "user": user,
                "allow": allow,
                "for_value": for_value,
                "apply_to_all_doctypes": apply_to_all_doctypes,
                "is_default": is_default
            })
            perm.insert(ignore_permissions=True)
            frappe.db.commit()
    except frappe.DuplicateEntryError:
        # Permission already exists, ignore and continue
        frappe.db.rollback()
    except Exception as e:
        frappe.log_error(f"Error creating User Permission: {e}")
        frappe.db.rollback()
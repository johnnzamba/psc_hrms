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


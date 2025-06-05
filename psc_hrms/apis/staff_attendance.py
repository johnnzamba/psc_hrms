import frappe
from frappe import _
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def get_staff():
    try:
        employees = frappe.get_all("Employee", fields=[
            "name", "employee_name", "employee_number", "department"
        ])
        return {"employees": employees}
    except Exception as e:
        frappe.log_error(_("Staff Fetch Error"), e)
        return {"error": str(e)}

@frappe.whitelist(allow_guest=True)
def createAttendanceAndCheckins(data):
    try:
        data = frappe.parse_json(data)
        event_dt = datetime.strptime(data.get("event_date_time"), "%d/%m/%Y %H:%M:%S")
        formatted_time = event_dt.strftime("%d-%m-%Y %H:%M:%S")
        attendance_date = event_dt.date()
        entry_type = "IN" if data.get("entry_exit_type") == "0" else "OUT"
        employee_number = data.get("user_id")

        # Fetch employee details
        employee = frappe.get_value("Employee", 
            {"employee_number": employee_number}, 
            ["name", "employee_name", "company", "department"], as_dict=True
        )
        if not employee:
            return {"error": f"Employee {employee_number} not found"}

        # Attendance handling
        attendance = frappe.db.exists("Attendance", {
            "employee": employee.name, 
            "attendance_date": attendance_date
        })

        created_attendance = None
        if not attendance and entry_type == "IN":
            attendance_doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee.name,
                "employee_name": employee.employee_name,
                "attendance_date": attendance_date,
                "in_time": formatted_time,
                "company": employee.company,
                "department": employee.department,
                "status": "Present"
            })
            attendance_doc.insert()
            attendance_doc.submit()
            created_attendance = attendance_doc.name
            attendance = created_attendance

        # Employee Checkin creation
        checkin_data = {
            "doctype": "Employee Checkin",
            "employee": employee.name,
            "employee_name": employee.employee_name,
            "log_type": entry_type,
            "time": formatted_time,
            "device_id": data.get("master_controller_id"),
            "custom_checkin_synced": 1
        }
        if created_attendance and entry_type == "IN":
            checkin_data["attendance"] = created_attendance

        checkin_doc = frappe.get_doc(checkin_data)
        checkin_doc.insert()

        # Update out_time if exit event
        if entry_type == "OUT" and attendance:
            frappe.db.set_value("Attendance", attendance, "out_time", formatted_time)

        return {"success": True, "attendance": attendance}
    except Exception as e:
        frappe.log_error(_("Attendance Sync Error"), e)
        return {"error": str(e)}
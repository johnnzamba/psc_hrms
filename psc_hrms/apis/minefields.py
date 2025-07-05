import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def create_or_update_half_day_status():
    print("Executing.......")

    # Delete if exists
    custom_field_name = frappe.db.get_value("Custom Field", {"dt": "Attendance", "fieldname": "half_day_status"})
    if custom_field_name:
        frappe.delete_doc("Custom Field", custom_field_name)
        print("Deleted existing 'half_day_status' custom field.")

    # Create the new field
    create_custom_field("Attendance", {
        "fieldname": "half_day_status",
        "fieldtype": "Check",
        "label": "Half Day Status",
        "hidden": 1,
        "default": 0
    })
    print("Custom field 'half_day_status' created successfully.")
    frappe.db.commit()

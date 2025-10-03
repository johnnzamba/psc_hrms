# Script to run on local server
import requests
import json
from datetime import datetime
import base64

# Configuration
FRAPPE_SITE =  "parklands.techsavanna.technology"
FRAPPE_API_KEY = "b1d5854640437ae"
FRAPPE_API_SECRET = "e921c425ab4af71"
COSEC_IP = "192.168.10.200"
COSEC_USERNAME = "sa"
COSEC_PASSWORD = "P@rkland$"

def main():
    # today = datetime.now().strftime("%d%m%Y")
    today = "15082025"
    date_range = f"{today}-{today}"
    frappe_auth = (FRAPPE_API_KEY, FRAPPE_API_SECRET)
    
    # Create Basic Auth header for COSEC
    cosec_credentials = f"{COSEC_USERNAME}:{COSEC_PASSWORD}"
    cosec_auth_header = {
        "Authorization": f"Basic {base64.b64encode(cosec_credentials.encode()).decode()}"
    }

    # Get all employees
    try:
        staff_url = f"https://{FRAPPE_SITE}/api/method/psc_hrms.apis.staff_attendance.get_staff"
        staff_res = requests.get(staff_url, auth=frappe_auth)
        
        if staff_res.status_code != 200:
            print(f"Staff fetch failed with status: {staff_res.status_code}")
            return
            
        staff_data = staff_res.json().get("message", {})
        if "employees" not in staff_data:
            print("No employees found in response")
            return
            
        employees = staff_data["employees"]
    except Exception as e:
        print(f"Staff fetch failed: {str(e)}")
        return

    # Process each employee
    for emp in employees:
        emp_number = emp.get("employee_number")
        if not emp_number:
            print("Skipping employee with missing employee_number")
            continue
        
        clean_emp_number = emp_number.replace("-", "")
        print(f"Original: {emp_number}, Cleaned: {clean_emp_number}")
            
        cosec_url = (
            f"http://{COSEC_IP}/cosec/api.svc/v2/event-ta?"
            f"action=get;date-range={date_range};range=user;Id={clean_emp_number}"
        )
        
        try:
            # Make request to COSEC API with Basic Auth
            cosec_res = requests.get(
                cosec_url, 
                headers=cosec_auth_header,
                timeout=10
            )
            
            if cosec_res.status_code != 200:
                print(f"COSEC API failed for {emp_number}: Status {cosec_res.status_code}")
                continue
                
            # Process response text
            text_data = cosec_res.text.strip()
            if not text_data:
                print(f"No data for employee {emp_number}")
                continue
                
            lines = text_data.split("\n")
            if len(lines) < 2:
                print(f"Invalid data format for {emp_number}")
                continue
                
            # Process each attendance record
            for line in lines[1:]:
                parts = line.split("|")
                if len(parts) < 10:
                    print(f"Skipping malformed line: {line}")
                    continue
                    
                payload = {
                    "index_no": parts[0],
                    "user_id": parts[1],
                    "user_name": parts[2],
                    "event_date_time": parts[3],
                    "entry_exit_type": parts[4],
                    "master_controller_id": parts[5],
                    "door_controller_id": parts[6],
                    "special_function_id": parts[7],
                    "leave_dt": parts[8],
                    "i_date_time": parts[9]
                }
                
                # Sync with Frappe
                try:
                    sync_url = f"https://{FRAPPE_SITE}/api/method/psc_hrms.apis.staff_attendance.createAttendanceAndCheckins"
                    response = requests.post(
                        sync_url, 
                        data={"data": json.dumps(payload)}, 
                        auth=frappe_auth,
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    print(f"API Response: {response.text}")  
                    if response.status_code == 200:
                        result = response.json().get("message", {})
                        if result.get("success"):
                            print(f"Successfully processed record {parts[0]} for {clean_emp_number}")
                        else:
                            print(f"API reported failure: {result.get('error', 'Unknown error')}")
                    else:
                        print(f"Frappe API failed for record {parts[0]}: Status {response.status_code}")
                        print(f"Response: {response.text}")
                        
                except Exception as e:
                    print(f"Frappe sync failed for {clean_emp_number}: {str(e)}")
                
        except Exception as e:
            print(f"Error processing {clean_emp_number}: {str(e)}")

if __name__ == "__main__":
    main()




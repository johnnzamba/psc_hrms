# Script to run on local server
import requests
import json
from datetime import datetime

# Configuration
FRAppe_SITE = "https://parklands.techsavanna.technology/"
API_KEY = "b1d5854640437ae"
API_SECRET = "9ad0e32b7482b4d"
COSEC_IP = "192.168.104.11"

def main():
    today = datetime.now().strftime("%d%m%Y")
    date_range = f"{today}-{today}"
    auth = (f"{API_KEY}:{API_SECRET}")

    # Get all employees
    try:
        staff_url = f"https://{FRAppe_SITE}/api/method/psc_hrms.apis.staff_attendance.get_staff"
        staff_res = requests.get(staff_url, auth=auth)
        staff_data = staff_res.json().get("message", {}).get("employees", [])
    except Exception as e:
        print(f"Staff fetch failed: {str(e)}")
        return

    # Process each employee
    for emp in staff_data:
        emp_number = emp.get("employee_number")
        if not emp_number:
            continue
            
        cosec_url = (
            f"http://{COSEC_IP}/cosec/api.svc/v2/attendance-daily?"
            f"action=get;date-range={date_range};range=user;Id={emp_number}"
        )
        
        try:
            cosec_res = requests.get(cosec_url, timeout=10)
            if cosec_res.status_code != 200:
                continue
                
            lines = cosec_res.text.strip().split("\n")
            if len(lines) < 2:
                continue
                
            # Process each attendance record
            for line in lines[1:]:
                parts = line.split("|")
                if len(parts) < 10:
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
                sync_url = f"https://{FRAppe_SITE}/api/method/psc_hrms.apis.staff_attendance.createAttendanceAndCheckins"
                requests.post(sync_url, data={"data": json.dumps(payload)}, auth=auth)
                
        except Exception as e:
            print(f"Error processing {emp_number}: {str(e)}")

if __name__ == "__main__":
    main()
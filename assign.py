import os
import sys
import time
import threading
import keyboard
import winsound
import subprocess
from datetime import datetime, timedelta, timezone
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from termcolor import colored
from random import randint
import pandas as pd

# Configuration
PERSONAL_ACCESS_TOKEN = ''

# ASSIGNEE = 'INSERT NAME'

PIPELINE_PAT = ""
ADO_US_PAT   = ""
ADO_UK_PAT   = ""
ADO_WEU_PAT  = ""
ADO_AUE_PAT  = ""
ADO_CAN_PAT  = ""
ADO_IN_PAT   = ""
ADO_AP_PAT   = ""

REGION_CONFIG = {
    1:  {'name': 'azwu3-prd04',   'abbr': 'us', 'pat': ADO_US_PAT, 'assignee': ''},
    2:  {'name': 'azwu3-prd05',   'abbr': 'us', 'pat': ADO_US_PAT},
    3:  {'name': 'azcu-prd06',    'abbr': 'us', 'pat': ADO_US_PAT},
    4:  {'name': 'azcu-prd08',    'abbr': 'us', 'pat': ADO_US_PAT},
    5:  {'name': 'azcu-prd09',    'abbr': 'us', 'pat': ADO_US_PAT},
    6:  {'name': 'centralus',     'abbr': 'us', 'pat': ADO_US_PAT},
    7:  {'name': 'eastus',        'abbr': 'us', 'pat': ADO_US_PAT},
    8:  {'name': 'eastus2',       'abbr': 'us', 'pat': ADO_US_PAT},
    9:  {'name': 'uksouth',       'abbr': 'uk', 'pat': ADO_UK_PAT, 'assignee': ''},
    10: {'name': 'francecentral', 'abbr': 'eu', 'pat': ADO_WEU_PAT, 'assignee': ''},
    11: {'name': 'westeurope',    'abbr': 'eu', 'pat': ADO_WEU_PAT, 'assignee': ''},
    12: {'name': 'azfrc-prd03',   'abbr': 'eu', 'pat': ADO_WEU_PAT, 'assignee': ''},
    13: {'name': 'canadacentral', 'abbr': 'ca', 'pat': ADO_CAN_PAT, 'assignee': ''},
    14: {'name': 'australiaeast', 'abbr': 'au', 'pat': ADO_AUE_PAT, 'assignee': ''},
    15: {'name': 'centralindia',  'abbr': 'in', 'pat': ADO_IN_PAT, 'assignee': ''},
    16: {'name': 'southeastasia', 'abbr': 'ap', 'pat': ADO_AP_PAT, 'assignee': ''},
    17: {'name': 'azszn-prd01', 'abbr': 'eu', 'pat': ADO_WEU_PAT, 'assignee': ''},
    18: {'name': 'azcu-prd10', 'abbr': 'us', 'pat': ADO_US_PAT},
    19: {'name': 'azcu-prd11', 'abbr': 'us', 'pat': ADO_US_PAT}
}


for i in range(2, 9):
    REGION_CONFIG[i]['assignee'] = REGION_CONFIG[1]['assignee']
REGION_CONFIG[18]['assignee'] = REGION_CONFIG[1]['assignee']
REGION_CONFIG[19]['assignee'] = REGION_CONFIG[1]['assignee']

# Assign placeholder to non-US regions together
# for i in range(9, 18):
#     REGION_CONFIG[i]['assignee'] = ''

TIME = 5 # minutes

# Shared list and lock
custom_guids = []
lock = threading.Lock()

jumpbox_lock = threading.Lock()
jumpbox_triggered = False

def get_azure_connection(token, org_url):
    credentials = BasicAuthentication('', token)
    return Connection(base_url=org_url, creds=credentials)

def get_work_client(connection):
    return connection.clients.get_work_item_tracking_client()

def build_customer_query(customers):
    return ' AND '.join([f"customer_name = '{c.strip()}'" for c in customers])

def build_wiql(region=None, customers=None):
    if region in [REGION_CONFIG.get(i)['name'] for i in range(1,9)] or region == REGION_CONFIG.get(18)['name'] or region == REGION_CONFIG.get(19)['name']:
        min_alert_age_timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
    else:    
        min_alert_age_timestamp = datetime.now(timezone.utc) - timedelta(minutes=20)
    # min_alert_age_timestamp = datetime.now(timezone.utc) - timedelta(minutes=15)
    formatted_time = min_alert_age_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    base = f"SELECT [System.Id], [System.Title], [System.State] FROM workitems WHERE [System.State] = 'New' AND [System.CreatedDate] > @StartOfDay AND time <= '{formatted_time}'"
    if region:
        base += f" AND tenant_region = '{region}'"
    if customers:
        base += f" AND ({build_customer_query(customers)})"
    return {"query": base}

def process_work_items(work_client, query, assignee, custom_guids, lock, region):
    result = work_client.query_by_wiql(query).work_items
    if not result:
        print(f"({REGION_CONFIG.get(region)['name']}) No work items found matching the query.")
        return

    ids = [item.id for item in result]
    for wid in ids:
        update_document = [
            {"op": "add", "path": "/fields/System.AssignedTo", "value": assignee},
            {"op": "replace", "path": "/fields/System.State", "value": "Under Investigation"}
        ]
        
        # Comment out the following to skip put request
        updated = work_client.update_work_item(document=update_document, id=wid)
        tenant_id = updated.fields.get('Custom.tenant_id')
        if tenant_id:
            print("(" + REGION_CONFIG.get(region)['name'] + ") " + colored(tenant_id, 'red'))
            with lock:
                if tenant_id not in custom_guids:
                    custom_guids.append(tenant_id)
            winsound.MessageBeep(winsound.MB_ICONASTERISK)

def print_ids(guids):
    out = ''
    if len(guids) > 15:
        print_ids(guids[15:])
        guids = guids[:15]
    for x in range(len(guids)):
        out = out + guids[x] + ','
    out = out[:-1]
    print(out)

def listen_for_exit(custom_guids, lock):
    last_pressed = False
    while True:
        if keyboard.is_pressed('`'):
            print("Exiting...")
            os._exit(0)
        elif keyboard.is_pressed('\\'):
            if not last_pressed:
                with lock:
                    print_ids(custom_guids if custom_guids else ["No alerts newly assigned"])
                last_pressed = True
        else:
            last_pressed = False

# def main_loop(region, customers):
#     pat = REGION_CONFIG.get(region)['pat']
    
#     endpoint = REGION_CONFIG.get(region)['abbr']

#     connection = get_azure_connection(pat, f'https://dev.azure.com/mddr-{endpoint}')
#     work_client = get_work_client(connection)

#     threading.Thread(target=listen_for_exit, args=(custom_guids, lock), daemon=True).start()

#     count = 0
#     region = REGION_CONFIG.get(region)['name']
#     while True:
#         if count == 15:
#             print(custom_guids)
#             # TODO: Run Openjumpbox.py
#             count = 0
#             time.sleep(TIME * 60)
#         elif count > 0:
#             time.sleep(TIME * 60)
#         query = build_wiql(region=region, customers=customers)
#         process_work_items(work_client, query, ASSIGNEE, custom_guids, lock)
#         count += 1

# User input
# if __name__ == "__main__":
    
#     region = 0
#     while region not in range(1, 13):
#         try:
#             region = int(input("""Select region:
#     1. azwu3-prd04
#     2. azwu3-prd05
#     3. azcu-prd06
#     4. centralus
#     5. eastus
#     6. eastus2
#     7. uksouth
#     8. francecentral
#     9. westeurope
#     10. canadacentral
#     11. australiaeast
#     12. centralindia
# > """).strip())
#         except ValueError:
#             region = 0
#         if region not in range(1, 13):
#             print('Please select valid region (1-12)')
        
#     filter_customers = input("Assign POD customers? (y/n): ").strip().lower()
#     customers = None
#     if filter_customers == 'y':
#         customers = ['Davenport & Company LLC', 'United States Liability Insurance Group', 'High Street Insurance Partners', 'Imperial Bag and Paper Co LLC', 'Valmont Industries, Inc', 'Cintas', 'JF Ahern Co', 'Master Halco', 'MDU Resources Group Inc', 'SMC Corporation of America', 'University of Miami', 'Greater Harris County 911', 'US Dermatology Partners', 'V2X, Inc.', 'VS Services Company, LLC', 'Microlise', 'Interpath Advisory', 'The Craneware Group', 'JATO Dynamics Limited', 'IRG Advisors LLP', 'Orpea', 'Shaare Zedek Medical Center', 'The Salvation Army Australia']
#     main_loop(region, customers)

def region_worker(region, customers):
    global jumpbox_triggered
    pat = REGION_CONFIG.get(region)['pat']
    endpoint = REGION_CONFIG.get(region)['abbr']
    region_name = REGION_CONFIG.get(region)['name']

    connection = get_azure_connection(pat, f'https://dev.azure.com/mddr-{endpoint}')
    work_client = get_work_client(connection)

    threading.Thread(target=listen_for_exit, args=(custom_guids, lock), daemon=True).start()

    count = 0
    while True:
        # if count >= 30 and region == REGION_CONFIG.get(region)['name'] == 'azwu3-prd04':
        #     count = 0
        #     with jumpbox_lock:
        #         if not jumpbox_triggered:
        #             jumpbox_triggered = not jumpbox_triggered
        #             subprocess.run(["python", "Openjumpbox.py"])
        #         else:
        #             jumpbox_triggered = False
        query = build_wiql(region=region_name, customers=customers)
        try:
            process_work_items(work_client, query, REGION_CONFIG.get(region)['assignee'], custom_guids, lock, region)
        except Exception as e:
            print(f"Error in process_work_items for region {region_name}: {e}")
            continue  # Immediately restart the loop

        if region in range(9,18):
            time.sleep(TIME * randint(60, 60 + 15) * 2)
        else:    
            time.sleep(TIME * randint(60, 60 + 15))
        # count += 1

def get_region_user_mapping(file_path=r'https://varonis.sharepoint.com/sites/SecurityArchitecture/Shared%20Documents/MDDR%20SLA%20Enablement/Sub-Region%20assignments.xlsx?web=1'):
    # Determine the current day of the week (e.g., 'Monday', 'Tuesday', etc.)
    current_day = datetime.now().strftime('%A')

    # Load the Excel file and check for the sheet corresponding to the current day
    xls = pd.ExcelFile(file_path, engine='openpyxl')
    if current_day not in xls.sheet_names:
        raise ValueError(f"No sheet found for {current_day} in the Excel file.")

    # Read the sheet for the current day
    df = pd.read_excel(xls, sheet_name=current_day, engine='openpyxl')

    # Drop rows with all NaN values
    df.dropna(how='all', inplace=True)

    # Attempt to identify columns for region and user
    # This assumes the first two columns are region and user
    region_user_dict = {}
    if df.shape[1] >= 2:
        for _, row in df.iterrows():
            region = str(row.iloc[0]).strip()
            user = str(row.iloc[1]).strip()
            if region and user and region.lower() != 'nan' and user.lower() != 'nan':
                region_user_dict[region] = user

    return region_user_dict

def main_loop(selected_regions, customers):
    for region in selected_regions:
        threading.Thread(target=region_worker, args=(region, customers), daemon=True).start()

if __name__ == "__main__":
    # region_user_mapping = get_region_user_mapping()
    # print(region_user_mapping)
    # Check for command-line argument
    auto_filter = '-p' in sys.argv[1:]
    print("Select regions (comma-separated or ranges, e.g., 1,3,5-7):")
    print("\n".join([f"{k}. {v['name']}" for k, v in REGION_CONFIG.items()]))

    if not auto_filter:
        region_input = input("> ").strip()
    else: 
        region_input = '1-8,18-19'
    selected_regions = set()

    try:
        for part in region_input.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                selected_regions.update(range(start, end + 1))
            else:
                selected_regions.add(int(part))
        # Filter out invalid region numbers
        selected_regions = [r for r in selected_regions if r in REGION_CONFIG]
    except ValueError:
        print("Invalid input. Please enter valid region numbers or ranges.")
        exit(1)

    
    # # Check for command-line argument
    # auto_filter = '-p' in sys.argv[1:]

    # if auto_filter:
    #     filter_customers = 'y'
    # else:
    #     filter_customers = input("Assign POD customers? (y/n): ").strip().lower()

    customers = None
    # if filter_customers == 'y':
    #     customers = ['Davenport & Company LLC', 'United States Liability Insurance Group', 'High Street Insurance Partners', 'Imperial Bag and Paper Co LLC', 'Valmont Industries, Inc', 'Cintas', 'JF Ahern Co', 'Master Halco', 'MDU Resources Group Inc', 'SMC Corporation of America', 'University of Miami', 'Greater Harris County 911', 'US Dermatology Partners', 'V2X, Inc.', 'VS Services Company, LLC', 'Microlise', 'Interpath Advisory', 'The Craneware Group', 'JATO Dynamics Limited', 'IRG Advisors LLP', 'Orpea', 'Shaare Zedek Medical Center', 'The Salvation Army Australia']
    main_loop(selected_regions, customers)
    
    # Keep the main thread alive until manually exited
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting main thread.")

# # Example usage
# region_user_mapping = get_region_user_mapping()
# print(region_user_mapping)


import requests
import base64
import time
import ipaddress
import requests
import urllib3
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

r'''
Script created by Matt S., Willie H. and Drew M. 

(c) 2025 Matt Schiff and Drew McDermitt v1.1.0

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

This script can be used to automate the creation of Jumpboxes and the adding of permissions to tenants based on alerts open in your name. To configure the script, create Personal Access Tokens (PATs) on all ADO dashboards (US, UK, WEU, AUE, and CAN) with READ Work Items permissions, and paste them into the appropriate lines below. Additionally, a PAT for spinning up the Jumpboxes and adding permissions to tenants is necessary. This PAT requires a minimum of Read, Write, and Execute permissions for Release, and Read & Execute permissions for Build. [1] Please note that when creating the PATs, you must copy the value provided once the PAT is created, as you will NOT be able to access the value after closing the pop-up and will have to regenerate the token.

Once configured, the script will pull all MDDR Investigations in your name from each dashboard, collect the URLs, Tenant IDs, and Tenant Regions, and process them to create the appropriate resources. Please note that all jumpbox creation must be performed through the script, or you will experience duplicate boxes being created. This script is still in progress, and updates will occasionally be released as major improvements are made.

To properly maintain records of jumpservers, a "tenant_regions.json" file will be created in the same directory as the script. This file name is configurable by changing the "file_path" variable. This file stores a JSON record of jumpservers that are currently active, and is updated each time the script runs.

PRIOR TO FIRST RUNNING THE SCRIPT:
1. Install Python 3.10 or newer from the Windows Store.
2. Run the following to download the required software packages:

pip install requests
pip install base64
pip install azure.devops
pip install msrest

3. Add the PATs to the script
4. Navigate a PowerShell or CMD window to the directory containing the script. (dir, pwd, and cd are your friends)
5. Run the script: python3 .\Openjumpbox.py
    a. For PODS members: to trigger jumpboxes/permissions for all PODS customers, use the '-p' flag (python3 .\Openjumpbox.py -p)

TODO Planned upgrades to the script:
  - Configuration to pull current jumpboxes and permissions from both pipelines.
  - Integration with the Jumpbox 8-6 Excel Spreadsheet.
  - Command line argument to update JSON without triggering pipeline runs.
  - Command line argument to force trigger a Jumpbox without having an alert assigned.
  - Command line argument to print out all Tenants with permissions alphabetically by dashboard
  - Analyze PAT hashing system to detect which permissions are missing and report
  - More to come...
  
[1]: Not entirely sure on these permissions, will update once I have confirmation of required permissions.

'''
#Paste your PATs between the quotation marks:
PIPELINE_PAT = ""
ADO_US_PAT   = ""
ADO_UK_PAT   = ""
ADO_WEU_PAT  = ""
ADO_AUE_PAT  = ""
ADO_CAN_PAT  = ""
ADO_IN_PAT   = ""
ADO_AP_PAT   = ""
file_path = "tenant_regions.json"

PODS_tenants = {
    'EE8A586E-F006-4E3C-B05B-3F61DB576A59':
        {
            'region': 'azwu3-prd04',
            'customer_url': 'cintas.varonis.io',
            'customer_name': 'Cintas'
        }
    ,
    'D3B937E9-C2C2-4A3C-8D07-6D328CCDA50B':
        {
            'region': 'uksouth',
            'customer_url': 'microlise.varonis.io',
            'customer_name': 'Microlise'
        }
    ,
    'EBDA9C53-93F7-462D-8F80-EBD390F1DC41':
        {
            'region': 'eastus',
            'customer_url': 'miami-edu.varonis.io',
            'customer_name': 'University of Miami'
        }
    ,
    'AFEFB67D-836F-4014-9944-A92C301EB9FA':
        {
            'region': 'centralus',
            'customer_url': 'imperialdade.varonis.io',
            'customer_name': 'IMPERIAL BAG'
        }
    ,
    '12E85B6A-CA45-447B-9D13-1A852347A907':
        {
            'region': 'eastus2',
            'customer_url': 'smcusa-com.varonis.io',
            'customer_name': 'SMC'
        }
    ,
    'F3516ADA-C543-4700-A732-0B9573CE5DAA':
        {
            'region': 'uksouth',
            'customer_url': 'interpath.varonis.io',
            'customer_name': 'Interpath Advisory'
        }
    ,
    'A4A81328-7009-4B5B-A4DA-0777AFD5F48F':
        {
            'region': 'uksouth',
            'customer_url': 'odgersberndtson.varonis.io',
            'customer_name': 'IRG Advisors LLP'
        }
    ,
    'ECC6707B-053A-40AD-970B-CA8146748775':
        {
            'region': 'centralus',
            'customer_url': 'valmont.varonis.io',
            'customer_name': 'Valmont Industries, Inc'
        }
    ,
    'BEA4E105-D682-4250-AE5B-B3FD6F70D88A':
        {
            'region': 'azwu3-prd04',
            'customer_url': 'mduresources-com.varonis.io',
            'customer_name': 'Mdu Resources Group Inc'
        }
    ,
    '23E94EC1-DBBC-4299-B3F7-85B20A15AAE5':
        {
            'region': 'azwu3-prd05',
            'customer_url': 'miami-edu2.varonis.io',
            'customer_name': 'University of Miami'
        }
}

'''
Dictionary of Regions that assigns the region to a specific dashboard
'''
regions = {
    'azwu3-prd04':   'US',
    'azwu3-prd05':   'US',
    'azcu-prd06':    'US',
    'centralus':     'US',
    'eastus':        'US',
    'eastus2':       'US',
    'uksouth':       'UK',
    'francecentral':'WEU',
    'westeurope':   'WEU',
    'canadacentral':'CAN',
    'australiaeast':'AUE',
    'centralindia':  'IN',
    'southeastasia':  'AP'
}
    

'''
Creates tenants and adds their information to the jump server JSON file.

Accepts:
  - file_path: String of path to JSON file.
  - tenants: Dictionary with following structure:
        {
            tenant_id:
                {
                    region: str
                    customer_url: str
                    customer_name: str
                }
            ,
            tenant_id:
                {
                    region: str
                    customer_url: str
                    customer_name: str
                }
            ,
            ...
            ,
            tenant_id:
                {
                    region: str
                    customer_url: str
                    customer_name: str
                }
        }
        
'''
def create_tenants(filepath, tenants_dict): # TODO
    
    # Create a timestamp for future validation of Jumpbox/Permissions
    today_date = datetime.now(timezone.utc)
    
    # Gather up to date information about existing Jumpbox/Permissions
    json_data = read_tenants(file_path)
    parents = []
    add_permissions_list = []
    
    # Check for Tenants with Jumpboxes
    for region, tenants in json_data.items():
        for tenant, values in tenants.items():
            if 'parent' in values:
                parents.append(region)
                break

    # Process new tenants
    for tenant_id, tenant_info in tenants_dict.items():
        region = tenant_info['region']
        url = tenant_info['customer_url']
        name = tenant_info['customer_name']
        # Check if region exists in JSON Data.
        if region in json_data:
            # If Region exists and tenant does not: grant permissions if region has a parent.
            if tenant_id not in json_data[region]:
                json_data[region][tenant_id] = {'creationDate': today_date.isoformat(), 'URL':url, 'Customer Name':name}
                if region in parents:
                    add_permissions_list.append(tenant_id)
            # If Region and Tenant exist: do not grant permissions.
            else:
                pass
            # If Region does not have an open Jumpbox: create one with the tenant.
            if region not in parents:
                json_data[region][tenant_id]['parent'] = True
                parents.append(region)
                create_new_jumpbox(url, tenant_id, name)
        # If Region does not exist: create region in JSON and create a Jumpbox with the tenant.
        else:
            json_data[region] = {tenant_id: {'creationDate': today_date.isoformat(), 'URL':url, 'Customer Name':name, 'parent':True}}
            parents.append(region)
            create_new_jumpbox(url, tenant_id, name)
            
    # Validate all Regions have a Jumpbox
    while set(parents) != set(list(json_data)):
        #Identify which Region requires a Jumpbox and add one from an existing entry
        for region in list(json_data):
            if region not in parents:
                json_data[region][list(json_data[region])[0]]['parent'] = True
                json_data[region][list(json_data[region])[0]]['creationDate'] = today_date
                parents.append(region)
                create_new_jumpbox(json_data[region][list(json_data[region])[0]]['URL'], list(json_data[region])[0], json_data[region][list(json_data[region])[0]]['Customer Name'])
    with open(file_path, 'w') as file:
                json.dump(json_data, file, indent=4)
    if len(add_permissions_list) > 0:
        names_list = []
        names_str = ''
        for tenant in add_permissions_list:
            names_list.append(tenants_dict[tenant]['customer_name'])
        names_list = sorted(names_list, key=str.casefold)
        for tenant in names_list:
            names_str += tenant + '; '
        names_str = names_str[:-2]
        print(f"Adding permissions for the following tenants: {names_str}")
        add_permissions(add_permissions_list)

'''
Reads the JSON into the program. Automatically removes old jump servers from the JSON.

Returns a Dictionary with information on current Jumpbox and Permissions, format:
{
REGION:
    {
    TENANT_ID:
        {
        CREATION_DATE: ISO Timestamp
        URL: Str
        NAME: Str
        (OPT) Parent: Bool -- Used to identify which tenant is associated with the region's jumpbox
        }
    }
}
        
'''   
def read_tenants(file_path):
    today_date = datetime.now(timezone.utc)
    offset = timedelta(hours=12) # OFfset used to check if item is too old
    if os.path.exists(file_path):
        with open(file_path) as file:
            try:
                output = json.load(file)
                filtered_output = {}
                for region, tenants in output.items():
                    filtered_tenants = {}
                    for tenant, value in tenants.items():
                        if datetime.fromisoformat(value['creationDate']) + offset > today_date: # Adds to filtered tenants if new enough
                            filtered_tenants[tenant] = value
                    if len(filtered_tenants) > 0:
                        filtered_output[region] = filtered_tenants
                return filtered_output
            except:
                return {}
    return {}

'''Runs the pipeline to create a new jumpbox'''
def create_new_jumpbox(customer_url, customer_id, customer_name):
    organization = "Varonis"
    project = "DevOps"
    pipeline_id = "789"
    url = f"https://dev.azure.com/{organization}/{project}/_apis/pipelines/{pipeline_id}/runs?api-version=6.0-preview.1"
    base64_token = str(base64.b64encode(bytes(':'+PIPELINE_PAT, 'ascii')), 'ascii')

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {base64_token}"
    }
    uri_data = {
        "resources": {},
        "templateParameters": {
            "customer_id": customer_id,
            "customer_name": customer_url,
            "access_type": "Basic",
            "reason_for_access": "MDDR"
        },
        "variables": {
            "system.debug": "true"
        }
    }

    try:
        response = requests.post(url, json=uri_data, headers=headers)
        response.raise_for_status()
        if response.json().get('name'):
            print(f"New Jumpbox Pipeline {response.json()['name']} created for {customer_name}.")
        else:
            print(f"Pipeline trigger failed: {response.json()}")
    except Exception as e:
        print(str(e))

'''
Adds permissions to any number of customers, recursively reduces list of customers until <15 customers per call

Accepts: A list of tenant_ids to add permissions to.
'''
def add_permissions(customer_ids): # FIXME customer ids length
    if len(customer_ids) > 15:
        add_permissions(customer_ids[:15])
        customer_ids = customer_ids[15:]
    customer_id = ''
    if len(customer_ids) == 0:
        return
    for customer in customer_ids:
        customer_id += customer + ','
    customer_id = customer_id[:-1]
    print(customer_id)
    organization = "Varonis"
    project = "DevOps"
    pipeline_id = "1489"
    url = f"https://dev.azure.com/{organization}/{project}/_apis/pipelines/{pipeline_id}/runs?api-version=6.0-preview.1"
    base64_token = str(base64.b64encode(bytes(':'+PIPELINE_PAT, 'ascii')), 'ascii')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {base64_token}"
    }
    uri_data = {
        "resources": {},
        "templateParameters": {
            "customer_id": customer_id,
            "access_type": "Basic",
            "reason_for_access": "MDDR"
        },
        "variables": {
            "system.debug": "true"
        }
    }
    try:
        response = requests.post(url, json=uri_data, headers=headers)
        response.raise_for_status()
        if response.json().get('name'):
            print(f"Add Permissions Pipeline {response.json()['name']} created for {len(customer_ids)} customers.")
        else:
            print(f"Pipeline trigger failed: {response.json()}")
    except Exception as e:
        print(str(e))
    
if len(sys.argv) > 1 and '-p' in sys.argv:
    create_tenants(file_path, PODS_tenants)

if len(sys.argv) > 1 and '-l' in sys.argv:
    tenants_dict = read_tenants(file_path)
    us_tenants = []
    uk_tenants = []
    weu_tenants = []
    aue_tenants = []
    can_tenants = []
    in_tenants = []
    for region, tenants in tenants_dict.items():
        if regions[region] == 'US':
            for tenant_id, tenant_info in tenants.items():
                us_tenants.append(tenant_info['Customer Name'])
        elif regions[region] == 'UK':
            for tenant_id, tenant_info in tenants.items():
                uk_tenants.append(tenant_info['Customer Name'])
        elif regions[region] == 'WEU':
            for tenant_id, tenant_info in tenants.items():
                weu_tenants.append(tenant_info['Customer Name'])
        elif regions[region] == 'AUE':
            for tenant_id, tenant_info in tenants.items():
                aue_tenants.append(tenant_info['Customer Name'])
        elif regions[region] == 'CAN':
            for tenant_id, tenant_info in tenants.items():
                can_tenants.append(tenant_info['Customer Name'])
        elif regions[region] == 'IN':
            for tenant_id, tenant_info in tenants.items():
                in_tenants.append(tenant_info['Customer Name'])
        elif regions[region] == 'AP':
            for tenant_id, tenant_info in tenants.items():
                in_tenants.append(tenant_info['Customer Name'])
    if len(us_tenants) > 0:
        us_tenants_str = ''
        us_tenants = sorted(us_tenants, key=str.casefold)
        for tenant in us_tenants:
            us_tenants_str += tenant + '; '
        us_tenants_str = us_tenants_str[:-2]
        print(f'US Tenants: {us_tenants_str}')
    if len(uk_tenants) > 0:
        uk_tenants_str = ''
        uk_tenants = sorted(uk_tenants, key=str.casefold)
        for tenant in uk_tenants:
            uk_tenants_str += tenant + '; '
        uk_tenants_str = uk_tenants_str[:-2]
        print(f'UK Tenants: {tenants_dict}')
    if len(weu_tenants) > 0:
        weu_tenants_str = ''
        weu_tenants = sorted(weu_tenants, key=str.casefold)
        for tenant in weu_tenants:
            weu_tenants_str += tenant + '; '
        weu_tenants_str = weu_tenants_str[:-2]
        print(f'EU Tenants: {weu_tenants_str}')
    if len(aue_tenants) > 0:
        aue_tenants_str = ''
        aue_tenants = sorted(aue_tenants, key=str.casefold)
        for tenant in aue_tenants:
            aue_tenants_str += tenant + '; '
        aue_tenants_str = aue_tenants_str[:-2]
        print(f'AU Tenants: {aue_tenants_str}')
    if len(can_tenants) > 0:
        can_tenants_str = ''
        can_tenants = sorted(can_tenants, key=str.casefold)
        for tenant in can_tenants:
            can_tenants_str += tenant + '; '
        can_tenants_str = can_tenants_str[:-2]
        print(f'CA Tenants: {can_tenants_str}')
    if len(in_tenants) > 0:
        in_tenants_str = ''
        in_tenants = sorted(in_tenants, key=str.casefold)
        for tenant in in_tenants:
            in_tenants_str += tenant + '; '
        in_tenants_str = in_tenants_str[:-2]
        print(f'IN Tenants: {in_tenants_str}')
    exit()
    
def get_work_items(PAT, URL):
    credentials = BasicAuthentication('', PAT)
    connection = Connection(base_url=URL, creds=credentials)
    work_client = connection.clients.get_work_item_tracking_client()

    try:
        query_result = work_client.query_by_wiql(wiql).work_items
        
        work_items = []
        if query_result:
            work_item_ids = [item.id for item in query_result]
            work_items = work_client.get_work_items(ids=work_item_ids)
            return work_items
        return []
    except Exception as e:
        print(f"Error fetching work items: {str(e)}")
        return []

#ADOWIQLACCESS
organizations = {
    'US': ('https://dev.azure.com/mddr-us', ADO_US_PAT),
    'UK': ('https://dev.azure.com/mddr-uk', ADO_UK_PAT),
    'WEU': ('https://dev.azure.com/mddr-eu', ADO_WEU_PAT),
    'AUE': ('https://dev.azure.com/mddr-au', ADO_AUE_PAT),
    'CAN': ('https://dev.azure.com/mddr-ca', ADO_CAN_PAT),
    'IN': ('https://dev.azure.com/mddr-in', ADO_IN_PAT),
    'AP': ('https://dev.azure.com/mddr-ap', ADO_AP_PAT)
}

all_work_items = []

#QUERY ADO for all MDDR Investigations assigned to me
wiql = {
    "query": "SELECT [System.Id], [System.Title], [System.State] FROM workitems WHERE [System.AssignedTo] = @Me AND [System.State] = 'Under Investigation' AND [System.WorkItemType] = 'MDDR Investigation' ORDER BY [Custom.tenant_region] ASC, [Custom.customer_name] ASC"
}

# Fetch work items for each organization
for region, (url, pat) in organizations.items():
    work_items = get_work_items(pat, url)
    print(f'{region} Work Items: {len(work_items)}')
    all_work_items.extend(work_items)

# Process Work Items to gather Tenant Information
tenants = {}
for work_item in all_work_items:
    fields = work_item.fields
    filtered_fields = {
        'Custom.tenant_id': fields.get('Custom.tenant_id'),
        'Custom.customer_saas_url': fields.get('Custom.customer_saas_url').replace('https://', ''),
        'Custom.tenant_region': fields.get('Custom.tenant_region'),
        'Custom.customer_name': fields.get('Custom.customer_name')
    }
    tenant_id = filtered_fields['Custom.tenant_id']
    customer_saas_url = filtered_fields['Custom.customer_saas_url']
    tenant_region = filtered_fields['Custom.tenant_region']
    customer_name = filtered_fields['Custom.customer_name']
    if tenant_id not in tenants:
        tenants[tenant_id] = {'region': tenant_region, 'customer_name': customer_name, 'customer_url': customer_saas_url}

'''Handle processed information to spin up Jump Servers'''
create_tenants(file_path, tenants)

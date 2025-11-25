# Prior to initial use:
# 1. Install Python 3.11 from the Microsoft Store
# 2. Run the following command in a PowerShell or Command Prompt window AFTER Python is finished installing: pip install requests
# 3. Create and verify an AbuseIPDB account and generate an API key
#       a. The URL to create an API key once you are logged in: https://www.abuseipdb.com/account/api
#       b. Click Create Key
#       c. Give the key a name and save it
# 4. Create and verify a VirusTotal account and copy the API key that is generated
# 5. Copy the API keys you created into the script lines 43 & 44 (paste the API Key between the single quotes)
# 6. Save the script in an easy to access location (I recommend C:\Users\<your username>\<script name>.py since PowerShell/CMD defaults to that path and makes running the script easier)
# 7. Open a command prompt or PowerShell window and use cd to navigate to the location you saved the script
# 8. Run the script with the command "python3 ./<script name>.py"; tab can be used to autocomplete the script name
#       a. For a cleaner looking terminal, the command "cls; python3 ./<script>" can be used



# USAGE: python3 IPDB_multiple_IPs_shareable.py
# IP Addresses (both IPv4 and IPv6) can be entered as a comma separated list, space separated list, or individually
# This script will provide a warning if the limit of API calls available in a day drops below 100 for AbuseIPDB
# By default, VT limits you to 500 API calls/day and 15.5k calls/month and 4 calls/min
  
import sys
import requests
import json
import re
import urllib3
import os
import ipaddress
from datetime import datetime, timedelta

def validate_ip_address(address):
    try:
        ip = ipaddress.ip_address(address)
        return True
    except ValueError:
        return False

def process_date(date):
    dateobj = datetime.strptime(date,"%Y-%m-%dT%H:%M:%S+00:00")
    return [datetime.strftime(dateobj, "%Y-%m-%d %H:%M:%S UTC"), dateobj < datetime.now() - timedelta(days=14), dateobj < datetime.now() - timedelta(days=30)]

os.system("")

if len(sys.argv) > 1:
    if sys.argv[1] == '-u' or sys.argv[1] == '--usage':
        print(f"""\033[95mUSAGE: python3 {sys.argv[0]}\033[0m
IP Addresses (both IPv4 and IPv6) can be entered as a comma separated list, space separated list, or individually
This script will provide a warning if the limit of API calls available in a day drops below 100

\033[95mUSAGE: python3 {sys.argv[0]} -u/--usage\033[0m
Prints this usage message.
""")
    quit()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
noColor = '\033[0m'

APIKEY_ABUSEIPDB = '' #Insert AbuseIPDB key here
APIKEY_VIRUSTOTAL = '' #Insert Virus Total key here
if not APIKEY_ABUSEIPDB and not APIKEY_VIRUSTOTAL:
    print("\033[95mPlease update your API KEYs. Instructions for updating the API keys can be found in the python script.\033[0m")
    quit()

while(True):
    print("Paste IP Addresses (q to quit): ", end="")
    inputIPs = input()
    if inputIPs.lower() == "q":
        break
    inputIPs = inputIPs.replace(' ', ',')
    inputIPList = inputIPs.split(',')
    for IP in inputIPList:
        if len(IP) > 0 and validate_ip_address(IP):
            vt = False
            ipdb = False
            if APIKEY_VIRUSTOTAL:
                url2 = f'https://www.virustotal.com/api/v3/ip_addresses/{IP}'
                r2 = requests.get(url2, verify = False, headers = {"x-apikey":APIKEY_VIRUSTOTAL})
                if r2.status_code == 200:
                    output2 = json.loads(r2.text)
                    vt = True
            if APIKEY_ABUSEIPDB:
                url = f'https://api.abuseipdb.com/api/v2/check?ipAddress={IP}&maxAgeInDays=365'
                r = requests.get(url, verify = False, headers={"Key":APIKEY_ABUSEIPDB})
                output = json.loads(r.text)['data']
                #print(output)
                ipdb = True
                ipdb_reported = output['lastReportedAt'] and 1
            print(f"\033[95mIP Address: {IP}\033[0m")
            if ipdb:
                if int(output['abuseConfidenceScore']) < 1:
                    color = '\033[92m'
                elif int(output['abuseConfidenceScore']) < 33:
                    color = '\033[93m'
                else:
                    color = '\033[91m'
                print(f"Abuse Confidence: {color}{output['abuseConfidenceScore']}%{noColor}")
       
            try:
                if ipdb_reported:
                    if int(output['totalReports']) < 1:
                        color = '\033[92m'
                    elif int(output['totalReports']) < 5:
                        color = '\033[93m'
                    else:
                        color = '\033[91m'
                    date = process_date(output['lastReportedAt'])
                    print(f"Number of reports: {color}{output['totalReports']}{noColor}")
                    if date[1]:
                        color = '\033[92m'
                    elif date[2]:
                        color = '\033[93m'
                    else:
                        color = '\033[91m'
                    print(f"Last Reported: {color}{date[0]}{noColor}")
                if vt:
                    if int(output2['data']['attributes']['reputation']) < 0:
                        color = '\033[91m'
                    elif int(output2['data']['attributes']['reputation']) < 1:
                        color = '\033[93m'
                    else:
                        color = '\033[92m'
                    print(f"VT Community Score: {color}{output2['data']['attributes']['reputation']}{noColor}")
                    if int(output2['data']['attributes']['last_analysis_stats']['malicious']) < 1:
                        color = '\033[92m'
                    elif int(output2['data']['attributes']['last_analysis_stats']['malicious']) < 3:
                        color = '\033[93m'
                    else:
                        color = '\033[91m'
                    print(f"VT Malicious Reports: {color}{output2['data']['attributes']['last_analysis_stats']['malicious']}{noColor}")
                    if int(output2['data']['attributes']['last_analysis_stats']['suspicious']) < 1:
                        color = '\033[92m'
                    elif int(output2['data']['attributes']['last_analysis_stats']['suspicious']) < 3:
                        color = '\033[93m'
                    else:
                        color = '\033[91m'
                    print(f"VT Suspicious Reports: {color}{output2['data']['attributes']['last_analysis_stats']['suspicious']}{noColor}")
                    if int(output2['data']['attributes']['last_analysis_stats']['harmless']) < 1:
                        color = '\033[93m'
                    elif int(output2['data']['attributes']['last_analysis_stats']['harmless']) < 3:
                        color = '\033[93m'
                    else:
                        color = '\033[92m'
                    print(f"VT Harmless Reports: {color}{output2['data']['attributes']['last_analysis_stats']['harmless']}{noColor}")
                if ipdb:
                    print(f"Country: {output['countryCode']}")
                    print(f"Domain: {output['domain']}")
                    print(f"ISP: {output['isp']}")
                    print(f"Usage Type: {output['usageType']}\n\n")
                
            except KeyError:
                print()
            try:
                if int(r.headers["X-RateLimit-Remaining"]) < 100:
                    print(f"Warning! {int(r.headers['X-RateLimit-Remaining'])} requests remaining today\n")
            except KeyError:
                pass
        else: 
            pass

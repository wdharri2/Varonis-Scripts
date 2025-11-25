# Security Utilities

A small collection of Python utilities to make day-to-day security / IR work a little easier.  

This repo currently includes:

- A multi-region Azure DevOps alert assigner
- A jumpbox / tenant permission automation tool for Azure DevOps
- A multi-IP reputation checker using AbuseIPDB and VirusTotal
- A simple CSV domain extractor

> **Note:** Several scripts are tailored to a specific Azure DevOps / SaaS environment. You will need to customize PATs, API keys, and file paths before using them.

---

## Table of Contents

1. [Prerequisites](#prerequisites)  
2. [Scripts Overview](#scripts-overview)  
   - [assign.py](#assignpy)  
   - [Openjumpbox.py](#openjumpboxpy)  
   - [IPDB_multiple_IPs_shareable.py](#ipdb_multiple_ips_shareablepy)  
   - [domain.py](#domainpy)  
3. [Configuration](#configuration)  
4. [Usage Examples](#usage-examples)  
5. [Security Notes](#security-notes)

---

## Prerequisites

All scripts require **Python 3.10+** and are written with Windows usage in mind.

### Common Python Packages

Depending on which scripts you use, you will need some or all of:

```bash
pip install azure-devops msrest termcolor keyboard pandas openpyxl requests urllib3
```

* `azure-devops`, `msrest` for ADO access
* `termcolor`, `keyboard`, `winsound` for the alert assigner UX
* `pandas`, `openpyxl` for Excel-driven region/user mappings
* `requests`, `urllib3` for API calls (AbuseIPDB, VirusTotal, ADO pipelines)

You will also need various **Personal Access Tokens (PATs)** and **API keys**:

* Azure DevOps PATs for each region/dashboard
* Azure DevOps PAT for pipeline execution
* AbuseIPDB API key
* VirusTotal API key 

---

## Scripts Overview

### `assign.py`

**Purpose:**
Automate assigning new Azure DevOps MDDR Investigation work items to the correct analyst across multiple regions, then track and surface the tenant IDs for quick jumpbox/permission workflows. 

**Key Features:**

* Connects to multiple regional Azure DevOps orgs (US, UK, EU, AU, CA, IN, AP), each with its own PAT and default assignee.
* Periodically runs a WIQL query for **new** work items in specific regions, older than a configurable minimum alert age.
* Automatically:

  * Assigns matching work items to the configured user
  * Sets their state to `Under Investigation`
  * Collects unique `tenant_id` values and prints them with colorized output and an audible beep per new tenant
* Runs one worker thread **per selected region** for parallel monitoring.
* Keyboard shortcuts:

  * <code>`</code> (backtick) to exit the script
  * `\` to print a comma-separated list of all tenant IDs assigned during this run

**Notable Details:**

* Region metadata (name, abbreviation, PAT, assignee) is centralized in the `REGION_CONFIG` dict.
* US regions have a more aggressive minimum alert age, non-US regions use a longer minimum age by default.
* A `-p` flag can be used to automatically select a default subset of regions instead of prompting.

---

### `Openjumpbox.py`

**Purpose:**
Automate the lifecycle of **jumpboxes** and **permissions** in a Varonis / MDDR environment, driven off Azure DevOps MDDR Investigation work items that are assigned to you. 

**High-Level Flow:**

1. Queries each relevant Azure DevOps organization (US, UK, WEU, AUE, CAN, IN, AP) for:

   * `MDDR Investigation` work items
   * `AssignedTo = @Me`
   * `State = 'Under Investigation'`
2. For each matching work item, extracts:

   * `Custom.tenant_id`
   * `Custom.customer_saas_url`
   * `Custom.tenant_region`
   * `Custom.customer_name`
3. Aggregates tenants into an in-memory structure keyed by tenant ID and region.
4. Passes this structure into `create_tenants(...)`, which:

   * Maintains a JSON file (`tenant_regions.json`) of active jumpboxes and permissions
   * Ensures there is at least one **parent** tenant per region (the one associated with the jumpbox)
   * Triggers ADO pipelines to:

     * Create a **new jumpbox** when a region has no parent yet
     * Add permissions for additional tenants in regions that already have an active jumpbox

**Important Pieces:**

* `create_new_jumpbox(...)` calls an Azure DevOps pipeline (ID 789) via REST to spin up a jumpbox for a specific tenant.
* `add_permissions(...)` calls another pipeline (ID 1489) to add access for up to 15 tenant IDs at a time (recursively batches if needed).
* `tenant_regions.json`:

  * Stores tenants by region, with fields like `creationDate`, `URL`, `Customer Name`, and optional `parent`.
  * Old entries are automatically pruned (older than ~12 hours) when read back in. 

**Command-Line Flags:**

* `-p`
  Immediately seeds `tenant_regions.json` from a predefined `PODS_tenants` mapping and triggers jumpboxes/permissions.
* `-l`
  Reads the JSON file and prints all tenants grouped by dashboard (US, UK, WEU, AUE, CAN, IN, AP) in alphabetical order.

---

### `IPDB_multiple_IPs_shareable.py`

**Purpose:**
Quickly triage multiple IP addresses against **AbuseIPDB** and **VirusTotal** from the terminal, with colorized risk scores and basic quota awareness. 

**What It Does:**

* Accepts IPv4 and IPv6 addresses as:

  * Comma-separated list
  * Space-separated list
  * One per line
* Validates IP addresses using Python’s `ipaddress` module.
* For each valid IP:

  * Queries VirusTotal’s IP report API (optional, if API key is configured)
  * Queries AbuseIPDB’s `check` endpoint (optional, if API key is configured)
* Prints:

  * AbuseIPDB **abuse confidence score** with green/yellow/red coloring
  * Number of reports and when it was last reported (with freshness coloring)
  * VirusTotal community reputation
  * VT malicious/suspicious/harmless counts, color-coded
  * Country, domain, ISP, and usage type where available
* Warns when your daily AbuseIPDB quota drops below 100 remaining requests, if the header is provided.

**Usage Notes:**

* Provides a `-u` / `--usage` flag to print usage help and exit.
* Designed to run interactively in a loop until you type `q` to quit.
* API keys are configured at the top of the script:

  * `APIKEY_ABUSEIPDB = '...'`
  * `APIKEY_VIRUSTOTAL = '...'`
* If neither API key is set, the script will prompt you to update them and exit. 

---

### `domain.py`

**Purpose:**
Extracts a de-duplicated list of base domains from the first column of a CSV file, ignoring entries that contain `.com` exactly as written. 

**Behavior:**

* Opens the given CSV file.
* For each row:

  * Takes the first column as a full domain string
  * Skips rows where the domain string contains `.com`
  * For others, splits on `.` and extracts the **second-to-last** part as the “main” domain (e.g., `foo.bar.co.uk` → `co`)
* Stores unique main domains in a `set`, converts to a list, and prints them. 

> Note: The logic is intentionally simple and may not match all real-world public suffix rules. Treat it as a quick-and-dirty helper rather than a full domain parser.

---

## Configuration

### 1. Azure DevOps PATs

Both `assign.py` and `Openjumpbox.py` expect you to paste PATs into the appropriate variables:

* `PIPELINE_PAT` for jumpbox/permission pipelines
* Regional PATs like `ADO_US_PAT`, `ADO_UK_PAT`, `ADO_WEU_PAT`, etc.

Each PAT typically needs at least:

* **Work Items**: read access (for queries)
* **Pipelines**: read, write, execute (for triggering jumpbox/permissions pipelines)

Check your org’s security requirements and scope PATs as narrowly as possible.

### 2. Assignees and Regions (`assign.py`)

* Set `REGION_CONFIG[<id>]['assignee']` to the appropriate display name / UPN for each region, or leave blank if you want to supply it another way.
* Verify the region names and abbreviations match your Azure DevOps org URLs:

  * Example: `azwu3-prd04` with `abbr: 'us'` maps to `https://dev.azure.com/mddr-us`. 
* Optionally configure `TIME` (polling interval in minutes) and the alert age logic in `build_wiql(...)` if you want more or less aggressive polling.

### 3. AbuseIPDB / VirusTotal API Keys

In `IPDB_multiple_IPs_shareable.py`, set:

```python
APIKEY_ABUSEIPDB = 'your-abuseipdb-key'
APIKEY_VIRUSTOTAL = 'your-virustotal-key'
```

Do **not** commit real keys to a public repo.

### 4. Excel Mapping (optional)

If you want to use Excel-driven region/user mapping in `assign.py`, update:

* The SharePoint URL / path in `get_region_user_mapping(...)`
* The expected sheet names (one per weekday) and column layout. 

---

## Usage Examples

### assign.py

```bash
# Basic interactive run
python assign.py

# Automatically select primary regions (example set)
python assign.py -p
```

Once running:

* Press `\` to print the GUIDs of all tenants that have had alerts assigned in this session.
* Press <code>`</code> to exit the script cleanly.

---

### Openjumpbox.py

```bash
# Normal run: pull ADO work items assigned to you and create/update jumpboxes and permissions
python Openjumpbox.py

# For PODS members: trigger jumpboxes/permissions for all PODS customers
python Openjumpbox.py -p

# List all tenants with active jumpboxes/permissions by region
python Openjumpbox.py -l
```

---

### IPDB_multiple_IPs_shareable.py

```bash
# Show usage
python IPDB_multiple_IPs_shareable.py -u

# Interactive run
python IPDB_multiple_IPs_shareable.py
Paste IP Addresses (q to quit): 8.8.8.8, 1.1.1.1, 192.0.2.1
```

The script will print colorized reputation data for each IP until you enter `q`.

---

### domain.py

```bash
python domain.py
```

By default it uses the hard-coded CSV path in the script. Adjust:

```python
file_path = r'C:\Users\<you>\Downloads\list.csv'
```

Run it and you will see a printed Python list of unique base domains extracted from the file. 

---

## Security Notes

* All of these scripts assume a trusted environment and are provided “as-is”, with no warranty, similar to the license header in `Openjumpbox.py`. 
* Review each script’s logic and adapt it to your org’s policies before running in production.
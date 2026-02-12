# Security Utilities

A small collection of Python utilities to make day-to-day security / IR work a little easier.

This repo currently includes:

- A multi-region Azure DevOps alert assigner
- A jumpbox / tenant permission automation tool for Azure DevOps
- A multi-IP reputation checker using AbuseIPDB and VirusTotal
- A simple CSV domain extractor
- A CSV tenant ID extraction, de-duplication, and batching utility

> **Note:** Several scripts are tailored to a specific Azure DevOps / SaaS environment. You will need to customize PATs, API keys, and file paths before using them.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Scripts Overview](#scripts-overview)
   - [assign.py](#assignpy)
   - [Openjumpbox.py](#openjumpboxpy)
   - [IPDB_multiple_IPs_shareable.py](#ipdb_multiple_ips_shareablepy)
   - [domain.py](#domainpy)
   - [extract_tenant_ids.py](#extract_tenant_idspy)
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

- `azure-devops`, `msrest` for ADO access
- `termcolor`, `keyboard`, `winsound` for the alert assigner UX
- `pandas`, `openpyxl` for Excel-driven region/user mappings
- `requests`, `urllib3` for API calls (AbuseIPDB, VirusTotal, ADO pipelines)

You will also need various **Personal Access Tokens (PATs)** and **API keys**:

- Azure DevOps PATs for each region/dashboard
- Azure DevOps PAT for pipeline execution
- AbuseIPDB API key
- VirusTotal API key

---

## Scripts Overview

### `assign.py`

**Purpose:**
Automate assigning new Azure DevOps MDDR Investigation work items to the correct analyst across multiple regions, then track and surface the tenant IDs for quick jumpbox/permission workflows.

**Key Features:**

- Connects to multiple regional Azure DevOps orgs (US, UK, EU, AU, CA, IN, AP), each with its own PAT and default assignee.
- Periodically runs a WIQL query for **new** work items in specific regions, older than a configurable minimum alert age.
- Automatically:
  - Assigns matching work items to the configured user
  - Sets their state to `Under Investigation`
  - Collects unique `tenant_id` values and prints them with colorized output and an audible beep per new tenant
- Runs one worker thread **per selected region** for parallel monitoring.
- Keyboard shortcuts:
  - <code>`</code> (backtick) to exit the script
  - `\` to print a comma-separated list of all tenant IDs assigned during this run

**Notable Details:**

- Region metadata (name, abbreviation, PAT, assignee) is centralized in the `REGION_CONFIG` dict.
- US regions have a more aggressive minimum alert age; non-US regions use a longer minimum age by default.
- A `-p` flag can be used to automatically select a default subset of regions instead of prompting.

---

### `Openjumpbox.py`

**Purpose:**
Automate the lifecycle of **jumpboxes** and **permissions** in a Varonis / MDDR environment, driven off Azure DevOps MDDR Investigation work items that are assigned to you.

**High-Level Flow:**

1. Queries each relevant Azure DevOps organization (US, UK, WEU, AUE, CAN, IN, AP) for:
   - `MDDR Investigation` work items
   - `AssignedTo = @Me`
   - `State = 'Under Investigation'`
2. For each matching work item, extracts:
   - `Custom.tenant_id`
   - `Custom.customer_saas_url`
   - `Custom.tenant_region`
   - `Custom.customer_name`
3. Aggregates tenants into an in-memory structure keyed by tenant ID and region.
4. Passes this structure into `create_tenants(...)`, which:
   - Maintains a JSON file (`tenant_regions.json`) of active jumpboxes and permissions
   - Ensures there is at least one **parent** tenant per region
   - Triggers ADO pipelines to create jumpboxes or add permissions

---

### `IPDB_multiple_IPs_shareable.py`

**Purpose:**
Quickly triage multiple IP addresses against **AbuseIPDB** and **VirusTotal** from the terminal.

---

### `domain.py`

**Purpose:**
Extracts a de-duplicated list of base domains from the first column of a CSV file, ignoring entries that contain `.com` exactly as written.

---

### `extract_tenant_ids.py`

**Purpose:**
Extract unique `tenant_id` values from a CSV file for quick reuse in downstream workflows, then automatically clean up the source file.

---

## Security Notes

- All scripts assume a trusted environment and are provided **as-is**.
- Review and adapt logic to your organization’s policies before running in production.

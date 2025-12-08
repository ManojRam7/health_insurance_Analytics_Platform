# 👥 Members Silver Layer – Architecture & Business Report

## Table of Contents

1. [Context & Objective](#1-context--objective)  
2. [Bronze vs Silver Members](#2-bronze-vs-silver-members)  
3. [Transformations: Bronze → Silver](#3-transformations-bronze--silver)  
4. [New Silver Features](#4-new-silver-features)  
5. [Data Quality & Validation](#5-data-quality--validation)  
6. [Architecture Diagram](#6-architecture-diagram)  
7. [Interview Explanation](#7-interview-explanation)  

---

## 1. Context & Objective

The Members Silver layer transforms **raw member records** into a **clean, validated, business-ready dataset** that:

- 👤 Creates a single, trusted member dimension  
- ✅ Enforces identity consistency  
- 📊 Adds member-level metrics & KPIs  
- 🔒 Includes data quality transparency  

**Enterprise standards applied:**
- Schema enforcement  
- Primary key validation  
- Age & demographic sanity checks  
- Reference dimension validation  
- Feature engineering (KPIs)  
- Deduplication  
- Quarantine of bad data  
- Metrics logging  

---

## 2. Bronze vs Silver Members

| Area | Bronze Issues | Silver Solution |
|------|---------------|-----------------|
| **Schema** | Raw CSV types | Enforced enterprise schema |
| **PK (Member_Key)** | Present but unvalidated | Strictly validated, duplicates removed |
| **Demographics** | Unchecked age/gender | Validated + flagged |
| **Contact Data** | No validation | Email/Phone format checks |
| **Address** | Raw text | Standardized structure |
| **KPIs** | None | Member_Age, Tenure_Days, RFM metrics |
| **DQ Signals** | None | dq_age_valid, dq_contact_valid, dq_address_valid |
| **Quarantine** | N/A | Bad records isolated with codes |

**Result:** Single, consistent member dimension ready for 360° customer analytics.

---

## 3. Transformations: Bronze → Silver

### Read & Enforce Schema

Cast columns to enterprise schema:
```
Member_Key, Member_ID, First_Name, Last_Name, Date_of_Birth,
Gender, Email, Phone, Address, City, Postcode, Member_Status
```

### PK Validation

`Member_Key` must not be NULL → otherwise quarantined.

### Deduplication

Keep latest record per `Member_Key`:
```
drop_dupes_keep_latest(["Member_Key"], ["Member_Status"])
```

### Demographic Validation

**Age validation:**
- Age must be between 0 and 150  
- If DOB provided, calculate age and validate  
- Flag suspicious ages via `dq_age_valid` (0/1)

**Gender validation:**
- Must be in {M, F, Other} or NULL  
- Invalid values quarantined  

### Contact Data Validation

**Email validation:**
- Basic format check (contains @, domain)  
- Flag invalid emails via `dq_contact_valid`

**Phone validation:**
- UK phone format expected  
- Flag invalid numbers  

### Address Standardization

- Trim and uppercase  
- Validate postcode format (UK)  
- Flag invalid postcodes via `dq_address_valid`

### Feature Engineering

#### Member_Age
```python
Member_Age = year(current_date()) - year(Date_of_Birth)
# NULL if DOB missing
```
**Business value:** Age-based segmentation, risk scoring, compliance.

#### Tenure_Days
```python
Tenure_Days = datediff(current_date(), Member_Registration_Date)
# Days as member
```
**Business value:** Loyalty metrics, churn risk, retention campaigns.

#### Member_Status_Clean
```python
Member_Status_Clean = CASE WHEN Member_Status IN ('Active', 'Inactive', 'Lapsed')
                            THEN Member_Status
                            ELSE 'Unknown' END
```
**Business value:** Prevents reporting fragmentation.

### Data Quality Flags

| Flag | Meaning | Business Value |
|------|---------|----------------|
| `dq_age_valid` | Age in valid range | Prevents age-based metric corruption |
| `dq_contact_valid` | Email/Phone valid format | Enables reliable customer outreach |
| `dq_address_valid` | Address & postcode valid | Prevents mailing failures |
| `dq_status_valid` | Status is known value | Prevents segmentation fragmentation |

### Write to Silver

- **Delta path:** `silverdata/members`  
- **Table:** `health_silver.members`  
- **Schema-aware overwrite** ensures stability

### Metrics Logging

Tracked in `silverdata/_metrics`:
- `rowcount_members_silver`  
- `distinct_member_keys`  
- Quarantine counts by violation type  
- DQ flag coverage %  

---

## 4. New Silver Features

| Feature | Type | Purpose | Example |
|---------|------|---------|---------|
| **Member_Age** | int | Current age derived from DOB | 35, 67, NULL |
| **Tenure_Days** | int | Days as member | 365, 1825 |
| **Member_Status_Clean** | string | Standardized status | Active, Inactive, Unknown |
| **dq_age_valid** | int | Age in valid range | 1 or 0 |
| **dq_contact_valid** | int | Email/Phone valid | 1 or 0 |
| **dq_address_valid** | int | Address & postcode valid | 1 or 0 |
| **dq_status_valid** | int | Status known | 1 or 0 |

**Key insight:** These fields are **added by Silver**, not in Bronze. They enable:
- 📊 Reliable member analytics  
- 🎯 Accurate segmentation  
- 🔍 Transparent data quality  

---

## 5. Data Quality & Validation

### Quarantine Strategy

No bad data is silently dropped. Invalid rows are captured with:
- Violation code (PK_NULL, AGE_INVALID, EMAIL_FORMAT, etc.)  
- Timestamp  
- Full record  

**Location:** `silverdata/_quarantine/members/<violation_type>`

### DQ Expectations

Hard rules (quarantine on failure):
- `Member_Key` not NULL  

Soft rules (flag but don't exclude):
- `dq_age_valid`, `dq_contact_valid`, `dq_address_valid`, `dq_status_valid`  

This allows:
- Filtering in dashboards: "only DQ-clean rows"  
- Monitoring quality trends  
- Transparent governance  

---

## 6. Architecture Diagram

```
┌──────────────────────────────────┐
│   Bronze Layer (rawdata)          │
│   bronze.members                  │
│   • Raw types                     │
│   • Duplicates                    │
│   • Bad demographics              │
│   • No KPIs                       │
└────────────┬──────────────────────┘
             │
             │  Schema enforcement
             │  Deduplicate
             │  Validate demographics
             │  Standardize addresses
             │  Add KPIs & DQ flags
             ▼
┌──────────────────────────────────┐
│   Silver Layer (silverdata)       │
│   health_silver.members             │
│   • Enterprise schema             │
│   • Deduplicated                  │
│   • Validated demographics        │
│   • Standardized addresses        │
│   • Member_Age, Tenure_Days KPIs  │
│   • 4 DQ flags (age, contact,     │
│     address, status)              │
└────────┬──────────────────────┬───┘
         │                      │
         ▼                      ▼
    _quarantine            _metrics
   (bad records)         (run metrics)
         │                      │
         ▼                      ▼
   Investigation          Observability
         │                      │
         └──────────┬───────────┘
                    ▼
        Member 360° Analytics
        Segmentation & Targeting
        Compliance Reporting
```

---

## 7. Interview Explanation

> "The Members Silver layer transforms raw member records into a trusted customer dimension. I enforce strict schema, validate and standardize demographic data (age, gender, contact info, addresses), deduplicate by Member_Key, and add business-friendly KPIs like member age and tenure. I also implement comprehensive data quality flags so that downstream users can confidently filter data and understand data health. The result is a single, reliable member dimension that powers 360° customer analytics, targeting campaigns, and compliance reporting."

### Key Talking Points
- ✅ Single source of truth for members  
- ✅ Deduplication (latest per Member_Key)  
- ✅ Demographic validation (age, gender)  
- ✅ Contact & address standardization  
- ✅ New KPIs (Member_Age, Tenure_Days)  
- ✅ 4 DQ flags for transparency  
- ✅ Quarantine & metrics for governance  
- ✅ Enterprise-grade data governance  

---

**Last Updated:** December 2025 | **Status:** Production | **Owner:** Data Engineering

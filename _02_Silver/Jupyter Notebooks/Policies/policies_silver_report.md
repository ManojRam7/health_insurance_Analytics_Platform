# 📄 Policies Silver Layer – Architecture & Business Report

## Table of Contents

1. [Context & Objective](#1-context--objective)  
2. [Bronze vs Silver Policies](#2-bronze-vs-silver-policies)  
3. [Transformations: Bronze → Silver](#3-transformations-bronze--silver)  
4. [New Silver Features](#4-new-silver-features)  
5. [Data Quality & Validation](#5-data-quality--validation)  
6. [Architecture Diagram](#6-architecture-diagram)  
7. [Interview Explanation](#7-interview-explanation)  

---

## 1. Context & Objective

The Policies Silver layer transforms **messy raw policy data** into a **trusted, analysis-ready dataset** that:

- 🔒 Has consistent schema  
- ✅ Enforces business rules  
- 📊 Includes data quality indicators  
- 🎯 Is safe for reporting and ML  

**Enterprise standards applied:**
- Consistent schema enforcement  
- Primary & foreign key validation  
- Date & monetary sanity checks  
- Reference dimension validation  
- Feature engineering (KPIs)  
- Deduplication  
- Quarantine of bad data  
- Metrics logging  

---

## 2. Bronze vs Silver Policies

| Area | Bronze | Silver |
|------|--------|--------|
| **Schema** | Raw CSV types | Enforced enterprise schema |
| **Data Types** | Inconsistent | Strongly typed (string, double, date, int) |
| **Deduplication** | Raw duplicates | Deduplicated (latest per Policy_ID) |
| **Date Validation** | No checks | Logical order enforced; reversed dates fixed |
| **Money Validation** | No checks | Non-negative enforced; flagged if violated |
| **KPIs** | None | Policy_Duration_Days, Renewal_Conversion |
| **DQ Signals** | None | dq_money_valid, dq_discount_valid, dq_renewal_valid |
| **Reference Dims** | Unchecked | Validated against Channel & Product_Line dims |
| **Quarantine** | N/A | Bad records isolated with violation codes |

**Result:** Clean, auditable, ML-ready policies ready for analytics.

---

## 3. Transformations: Bronze → Silver

### Read & Enforce Schema

Cast columns to enterprise schema:
```
Policy_ID, Customer_ID, Product_Line, Sum_Insured_GBP, Annual_Premium_GBP,
Policy_Start_Date, Policy_End_Date, Renewal_Offered_Flag, Renewal_Accepted_Flag,
Discount_Offered_%, Channel
```

### PK & FK Validation

**Hard checks (quarantine if fail):**
- `Policy_ID` not NULL  
- `Customer_ID` not NULL  

### Date Validation & Fixing

- `Policy_End_Date` ≥ `Policy_Start_Date`  
- Reversed dates are auto-swapped via `fix_dates()`  

### Monetary Validation

- All amounts ≥ 0  
- Negative values flagged via `dq_money_valid` (0/1)

### Reference Dimension Validation

Validate:
- `Channel` in `dim_channel` (Agent, Broker, Online, Partner)  
- `Product_Line` in `dim_product_line` (Accident, Dental, Health, Motor, Travel)  

Mismatches are quarantined.

### Deduplication

Keep latest record per `Policy_ID`:
```
drop_dupes_keep_latest(["Policy_ID"], ["Policy_Start_Date"])
```

### Feature Engineering

#### Policy_Duration_Days
```python
Policy_Duration_Days = datediff(Policy_End_Date, Policy_Start_Date)
```
**Business value:** Tenure analysis, churn windows, duration-based pricing.

#### Renewal_Conversion
```python
Renewal_Conversion = CASE WHEN Renewal_Offered_Flag = 1 
                          THEN Renewal_Accepted_Flag 
                          ELSE NULL END
```
**Business value:** Clean renewal KPI (only when renewal was offered).

### Data Quality Flags

| Flag | Meaning | Business Value |
|------|---------|----------------|
| `dq_money_valid` | All monetary fields ≥ 0 | Prevents corrupted financial reporting |
| `dq_discount_valid` | Discount between 0–100% (or NULL) | Flags impossible discount values |
| `dq_renewal_valid` | Accepted implies offered | Catches logical inconsistencies |

### Write to Silver

- **Delta path:** `silverdata/policies`  
- **Table:** `health_silver.policies`  
- **Schema-aware overwrite** ensures type stability

### Metrics Logging

Tracked in `silverdata/_metrics`:
- `rowcount_policies_silver`  
- `distinct_policy_ids`  
- Quarantine counts by violation type  
- DQ flag coverage %  

---

## 4. New Silver Features

| Feature | Type | Purpose | Example |
|---------|------|---------|---------|
| **Policy_Duration_Days** | int | Policy lifespan in days | 365, 730 |
| **Renewal_Conversion** | int | Clean renewal rate (0/1/NULL) | 1, 0, NULL |
| **dq_money_valid** | int | Monetary fields OK | 1 or 0 |
| **dq_discount_valid** | int | Discount in valid range | 1 or 0 |
| **dq_renewal_valid** | int | Renewal logic consistent | 1 or 0 |

**Key insight:** These fields are **added by Silver**, not in Bronze. They enable:
- 📊 Better analytics  
- 🔍 Transparent data quality  
- 🎯 ML model confidence  

---

## 5. Data Quality & Validation

### Quarantine Strategy

No bad data is silently dropped. Invalid rows are captured with:
- Violation code (PK_NULL, FK_INVALID, DATE_REVERSED, etc.)  
- Timestamp  
- Full record  

**Location:** `silverdata/_quarantine/policies/<violation_type>`

### DQ Expectations

Hard rules (quarantine on failure):
- `Policy_ID` not NULL  
- `Customer_ID` not NULL  

Soft rules (flag but don't exclude):
- `dq_money_valid`, `dq_discount_valid`, `dq_renewal_valid`  

This allows:
- Filtering in dashboards: "only DQ-clean rows"  
- Monitoring quality trends  
- Transparent governance  

---

## 6. Architecture Diagram

```
┌──────────────────────────────────┐
│   Bronze Layer (rawdata)          │
│   bronze.policies                 │
│   • Raw types                     │
│   • Duplicates                    │
│   • Bad dates/money               │
└────────────┬──────────────────────┘
             │
             │  Schema enforcement
             │  Deduplicate
             │  Validate dates & money
             │  Add KPIs & DQ flags
             │  Reference validation
             ▼
┌──────────────────────────────────┐
│   Silver Layer (silverdata)       │
│   health_silver.policies            │
│   • Enterprise schema             │
│   • Deduplicated                  │
│   • Clean dates & money           │
│   • Policy_Duration_Days KPI      │
│   • Renewal_Conversion KPI        │
│   • DQ flags (3 types)            │
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
           BI / Dashboards
           ML Models
           Analytics Reports
```

---

## 7. Interview Explanation

> "I built an enterprise-style data pipeline for insurance policies using a layered architecture. Raw Kaggle data is ingested into a Bronze layer as-is. From there, I created a Silver Policies layer where I enforce schema, validate critical business rules (like valid dates, financial sanity, and renewal logic), deduplicate policies, and add new business-friendly features like policy duration and clean renewal conversion. I also implemented quarantine and metrics logging so data quality issues are never hidden—they're traceable and measurable. The result is a trusted Policies dataset that business teams can safely use for reporting, dashboards, and pricing or retention analysis."

### Key Talking Points
- ✅ Layered architecture (Bronze → Silver → Gold)  
- ✅ Core fields preserved, new features added  
- ✅ Date & monetary sanity checks  
- ✅ Deduplication (latest per Policy_ID)  
- ✅ Reference dimension validation  
- ✅ DQ flags for transparency (not hard failures)  
- ✅ Quarantine & metrics for observability  
- ✅ Enterprise-grade governance  

---

**Last Updated:** December 2025 | **Status:** Production | **Owner:** Data Engineering

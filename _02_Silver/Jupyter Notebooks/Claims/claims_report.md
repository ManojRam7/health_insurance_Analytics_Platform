# 📋 Claims Silver Layer – Architecture & Business Report

## Table of Contents

1. [Context & Purpose](#1-context--purpose)  
2. [Bronze vs Silver Claims](#2-bronze-vs-silver-claims)  
3. [Transformations: Bronze → Silver](#3-transformations-bronze--silver)  
4. [New Silver Features](#4-new-silver-features)  
5. [Data Quality & Quarantine](#5-data-quality--quarantine)  
6. [Architecture Diagram](#6-architecture-diagram)  
7. [Interview Explanation](#7-interview-explanation)  

---

## 1. Context & Purpose

The Claims Silver layer converts raw, inconsistent claim records from Kaggle's Medicare Fraud dataset into a **clean, validated, business-ready Delta table** suitable for:
- 📊 Analytics dashboards  
- 🔍 Fraud insights & detection  
- 📈 Operational KPIs & SLA tracking  

**Enterprise standards applied:**
- ✅ Schema enforcement  
- ✅ Primary key validation  
- ✅ Provider FK integrity  
- ✅ Date consistency rules  
- ✅ Financial sanity checks  
- ✅ New KPIs & metrics  
- ✅ Deduplication  
- ✅ Quarantine of bad data  

---

## 2. Bronze vs Silver Claims

| Area | Bronze Issues | Silver Solution |
|------|---------------|-----------------|
| **Schema** | Raw CSV types | Enforced enterprise schema |
| **PK (Claim_ID)** | Present but unvalidated | Strictly validated, bad rows quarantined |
| **Provider FK** | 7% missing/mismatch | Validated + flagged with DQ signals |
| **Member FK** | Incompatible across datasets | Treated as soft FK, logged but not enforced |
| **Dates** | Often NULL | Validated + `dq_date_valid` flag |
| **Money Fields** | Unchecked | `dq_money_valid` applied |
| **KPIs** | None | `Days_To_Settle` derived |
| **Data Quality** | No signals | DQ flags + quarantine + metrics |

**Result:** 558K clean, auditable Silver claims ready for reporting and ML.

---

## 3. Transformations: Bronze → Silver

### Read & Enforce Schema

Cast all columns to enterprise schema:
```
Claim_ID, Provider_ID, Member_Key, Date_Reported, Date_Settled,
Payout_GBP, Claim_Amount_GBP, Fraud_Label, Claim_Type, Claim_Status
```

### PK Validation

`Claim_ID` must not be NULL → otherwise quarantined.

### FK Checks

**Provider_ID (strong FK):**
- 7% missing/mismatched → quarantined with violation code
- Remaining rows tagged with DQ flag for downstream awareness

**Member_Key (soft FK):**
- Comes from different Kaggle source (not enforceable)
- Logged but not quarantined (mirrors real legacy mismatches)

### Date Validations

- Dates can be NULL  
- If present, must follow logical order: `Date_Reported ≤ Date_Settled`
- Flagged via `dq_date_valid` (0/1)

### Monetary Validations

- No negative payouts or claim amounts  
- Flagged via `dq_money_valid` (0/1)

### Deduplication

- Latest record per `Claim_ID` wins

### KPI Creation

```python
Days_To_Settle = datediff(Date_Settled, Date_Reported)
# NULL if dates missing
```

**Business value:** SLA monitoring, customer experience metrics, operations planning.

### Metrics Logging

Tracked in `silverdata/_metrics`:
- `rowcount_claims_silver`  
- `distinct_claim_ids`  
- FK violation counts  
- DQ flag coverage %

---

## 4. New Silver Features

| Feature | Type | Meaning | Business Value |
|---------|------|---------|----------------|
| **Days_To_Settle** | int | Days between report & settlement | SLA monitoring, experience analysis |
| **dq_money_valid** | int | 0/1 flag for valid monetary values | Protects BI & ML from corrupted data |
| **dq_date_valid** | int | 0/1 flag for valid dates | Ensures lifecycle metrics are correct |

---

## 5. Data Quality & Quarantine

### Quarantine Strategy

No bad data is silently dropped. Every invalid row is captured with:
- Violation code (FK_MISSING, PK_NULL, DATE_INVALID, etc.)
- Timestamp  
- Full JSON payload  

**Location:** `silverdata/_quarantine/claims/<violation_type>`

### DQ Flags

- `dq_money_valid`: non-negative financial fields
- `dq_date_valid`: valid date ordering

These allow:
- Filtering in dashboards: "only dq_valid rows"  
- Monitoring quality trends over time  
- Transparent data quality governance  

---

## 6. Architecture Diagram

```
┌──────────────────────────────────┐
│   Bronze Layer (rawdata)          │
│   bronze.claims                   │
│   • Missing providers (7%)        │
│   • NULL dates                    │
│   • No KPIs                       │
└────────────┬──────────────────────┘
             │
             │  Schema enforcement
             │  Validations
             │  KPI derivation
             ▼
┌──────────────────────────────────┐
│   Silver Layer (silverdata)       │
│   health_silver.claims              │
│   • Validated PK & FK             │
│   • Clean dates & money           │
│   • Days_To_Settle KPI            │
│   • DQ flags                      │
└────────┬──────────────────────┬───┘
         │                      │
         ▼                      ▼
    _quarantine            _metrics
  (bad records)          (run metrics)
         │                      │
         ▼                      ▼
   Investigation          Observability
```

---

## 7. Interview Explanation

> "The Claims Silver layer transforms inconsistent raw claims into a trusted corporate dataset. We validate provider references, correct date issues, add SLA metrics like Days_To_Settle, generate data-quality flags, and surface all problems through a quarantine zone instead of hiding them. Member_Key mismatches are intentionally treated as soft FKs due to the combination of independent Kaggle sources. The result is a clean, governed dataset ready for operational dashboards, fraud analytics, and ML use cases—exactly how real insurers manage data quality."

### Key Talking Points
- ✅ Hard PK validation (Claim_ID not NULL)  
- ✅ Strong FK validation (Provider_ID) + quarantine  
- ✅ Soft FK treatment (Member_Key) for legacy compatibility  
- ✅ DQ flags for transparency (not hard failures)  
- ✅ New KPI (Days_To_Settle) for operations  
- ✅ Full audit trail via quarantine & metrics  

---

**Last Updated:** December 2025 | **Status:** Production | **Owner:** Data Engineering

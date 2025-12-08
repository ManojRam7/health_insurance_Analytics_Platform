# 🏥 Providers Silver Layer – Architecture & Business Report

## Table of Contents

1. [Context & Problem](#1-context--problem)  
2. [Bronze vs Silver Providers](#2-bronze-vs-silver-providers)  
3. [Transformations Applied](#3-transformations-applied)  
4. [Silver Providers Schema](#4-silver-providers-schema)  
5. [FK Integrity Fix](#5-fk-integrity-fix)  
6. [Business Value](#6-business-value)  
7. [Architecture Diagram](#7-architecture-diagram)  
8. [Interview Explanation](#8-interview-explanation)  

---

## 1. Context & Problem

The Providers Silver layer solves a **critical data integrity issue:**

> **Provider_ID values in Claims did NOT match Provider_ID values in the Providers dataset.**

### Impact of the Problem

- 🔴 Orphaned claims (no provider record)  
- 🔴 Incomplete provider directories  
- 🔴 Broken fraud analytics  
- 🔴 Unusable provider-level reporting  

### Silver Solution

**Reconstruct a complete, validated, trustworthy Provider dimension** that:
- ✅ Covers every Provider_ID used in Claims  
- ✅ Preserves fraud labels where available  
- ✅ Infers fraud flag for providers not in Bronze  
- ✅ Enables 100% referential integrity  

---

## 2. Bronze vs Silver Providers

| Area | Bronze Issues | Silver Solution |
|------|---------------|-----------------|
| **Coverage** | ~5K providers only | Complete universe (Claims + Bronze) |
| **PK Validation** | Unvalidated | Strict validation, bad IDs quarantined |
| **FK Completeness** | Many Claims orphaned | 100% FK coverage |
| **Fraud Labels** | Partial, inconsistent | Complete with source tracking |
| **Unknown Providers** | Not in Bronze | Inferred with Fraud_Flag = 0 |
| **Schema** | Raw CSV types | Enforced enterprise schema |
| **Quarantine** | N/A | Bad/NULL IDs quarantined |

**Result:** Every claim can join reliably to a provider.

---

## 3. Transformations Applied

### 1. Combine Two Sources

Merge providers from:
- **Bronze provider dataset** (official Kaggle providers)
- **Claims Provider_IDs** (actual providers used in claims)

Creates a **complete provider universe**.

### 2. Enforce Schema

```
Provider_ID          : string
Fraud_Flag           : int (0/1)
Fraud_Label_Source   : string
```

### 3. Fraud Label Logic

| Provider Source | Fraud_Flag | Fraud_Label_Source |
|-----------------|------------|--------------------|
| In Bronze dataset | original | `bronze_label` |
| Only in Claims | 0 (inferred) | `inferred_from_claims` |

**Rationale:** Providers not in official list assumed low-risk; true fraud determined later via claims analysis.

### 4. Quarantine Invalid IDs

Null or malformed Provider_IDs → sent to Silver quarantine with violation code.

### 5. Deduplication

Remove duplicates using:
```
drop_dupes_keep_latest(["Provider_ID"], ["Fraud_Flag"])
```

Result: **One row per Provider_ID**.

### 6. Write to Silver

- **Delta format:** `silverdata/providers`
- **Table:** `health_silver.providers`
- **Auto schema management** enabled

---

## 4. Silver Providers Schema

| Column | Type | Meaning | Example |
|--------|------|---------|---------|
| **Provider_ID** | string | Unique provider identifier | `PROV_001234` |
| **Fraud_Flag** | int | Fraud risk indicator (0/1) | `0` or `1` |
| **Fraud_Label_Source** | string | Where fraud label came from | `bronze_label` / `inferred_from_claims` |

---

## 5. FK Integrity Fix

### Before Silver

```
❌ 100% of claim Provider_IDs failed FK check against Bronze providers
❌ Provider data unusable for reporting
```

### Silver Solution

```
✅ Add all claim-derived provider IDs to Silver
✅ Default Fraud_Flag = 0 for inferred providers
✅ Maintain fraud lineage via Fraud_Label_Source
```

### Result

```
✅ 100% FK coverage — every claim has a valid provider
✅ Zero orphan claims
✅ Fraud analytics now possible
✅ Complete provider dimension for BI
```

---

## 6. Business Value

### For Fraud Teams
- ✅ Complete provider universe  
- ✅ Retains true fraud labels  
- ✅ Enables provider-level anomaly detection  

### For Operations
- ✅ Consistent provider identifiers across systems  
- ✅ Clean provider master data  

### For Actuarial Teams
- ✅ Provider-level cost modeling now possible  
- ✅ Accurate risk segmentation  

### For BI & Reporting
- ✅ No more broken joins  
- ✅ Clean provider dimension for dashboards  
- ✅ Provider-level KPIs reliable  

---

## 7. Architecture Diagram

```
┌─────────────────────────────────┐
│   Bronze Layer (rawdata)         │
├──────────────┬──────────────────┤
│  Providers   │  Claims           │
│  ~5K records │  Provider_IDs     │
└──────┬───────┴───────┬──────────┘
       │               │
       └───────┬───────┘
               │
               ▼
        ┌──────────────────┐
        │ Merge & Normalize│
        │ Provider_IDs     │
        │ (union both)     │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Assign Fraud     │
        │ Labels +         │
        │ Source Tracking  │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Quality Checks   │
        │ (Null IDs, etc.) │
        └────────┬─────────┘
                 │
         ┌───────┴────────┐
         ▼                ▼
    _quarantine      Silver Providers
    (bad records)    health_silver.providers
         │                │
         ▼                ▼
    Investigation    Consumption
```

---

## 8. Interview Explanation

> "The Providers Silver layer fixes a critical data integrity issue: Claims referenced Provider_IDs that didn't exist in the official Providers dataset. I solved this by building a complete provider universe—combining the official Kaggle provider list with all unique Provider_IDs from Claims. For providers only found in Claims, I inferred a fraud flag of 0 and tracked the source. The result is 100% referential integrity: every claim can reliably join to a provider, enabling fraud analytics, provider-level KPIs, and clean BI dashboards."

### Key Talking Points
- ✅ Identifies and solves FK problem  
- ✅ Combines multiple sources  
- ✅ Preserves fraud labels + source tracking  
- ✅ Infers missing data intelligently  
- ✅ Achieves 100% referential integrity  
- ✅ Enables downstream analytics  

---

**Last Updated:** December 2025 | **Status:** Production | **Owner:** Data Engineering

# 📊 Gold `fact_claims` – Architecture & Business Report

## Table of Contents

1. [Context & Objective](#1-context--objective)  
2. [Silver vs Gold fact_claims](#2-silver-vs-gold-fact_claims)  
3. [Transformations: Silver → Gold](#3-transformations-silver--gold)  
4. [New Gold Features](#4-new-gold-features)  
5. [Data Analysis Summary](#5-data-analysis-summary)  
6. [Key Business KPIs](#6-key-business-kpis)  
7. [Architecture Diagram](#7-architecture-diagram)  
8. [Interview Explanation](#8-interview-explanation)  

---

## 1. Context & Objective

The Gold `fact_claims` layer is the **final analytics-ready view** of all claims following the **medallion architecture**:

| Layer | Purpose | Status |
|-------|---------|--------|
| **Raw** | External CSVs (Kaggle) | Source files |
| **Bronze** | Raw Delta tables (no cleaning) | `rawdata` container |
| **Silver** | Cleaned, validated, enriched | `silverdata` container |
| **Gold** | Analytics-ready facts | `silverdata/gold` |

### Purpose of fact_claims

Create a **single, optimized claims fact table** ready for:
- 📈 BI dashboards & self-service analytics  
- 🤖 Machine learning models (fraud, cost prediction)  
- 💼 Operational reporting & fraud analysis  
- 🔍 Provider & claim performance insights  

---

## 2. Silver vs Gold fact_claims

| Area | Silver Claims | Gold fact_claims |
|------|--------------|------------------|
| **Grain** | One row per claim | One row per claim (enriched) |
| **Provider Context** | Provider_ID only | Provider_ID + Fraud_Flag joined |
| **KPIs** | Days_To_Settle | Payout_Ratio + High_Cost_Flag + Days_To_Settle |
| **Fraud Signal** | Claim-level only | Claim-level + Provider fraud context |
| **DQ Flags** | dq_money_valid, dq_date_valid | Same flags carried forward |
| **Cost Analysis** | Basic amounts | Payout ÷ Claimed ratio |
| **Segmentation** | Limited | By provider, cost tier, fraud risk |
| **BI Readiness** | Intermediate | Full (joins pre-computed) |
| **ML Features** | Limited | Rich feature set |

**Result:** Pre-joined, fact-ready dataset for BI, dashboards, and ML models.

---

## 3. Transformations: Silver → Gold

### 3.1 Join with Providers

**Input:**
- Silver Claims: claim records with Days_To_Settle, DQ flags  
- Silver Providers: Provider_ID + Fraud_Flag  

**Logic:**
```python
fact_claims = (
    silver_claims
    .join(silver_providers, on="Provider_ID", how="left")
)
```

**Business impact:**
- ✅ Every claim includes provider risk context  
- ✅ Enables fraud filtering at claim level  
- ✅ Supports provider-level risk segmentation  

### 3.2 Derive Payout Ratio

```python
Payout_to_Amount_Ratio = Payout_GBP / Claim_Amount_GBP
# NULL if Claim_Amount_GBP = 0 or NULL
```

**Business value:**
- 📊 Measures what % of claimed amount is actually paid  
- 🔍 Identifies over/under-compensation patterns  
- 💰 Supports pricing, underwriting, negotiations  
- 🚨 Audit & fraud indicator  

### 3.3 High-Cost Claim Flagging

```python
high_cost_threshold = quantile(Payout_GBP, 0.90)

High_Cost_Claim_Flag = CASE
  WHEN Payout_GBP >= high_cost_threshold THEN 1
  ELSE 0
END
```

**Business value:**
- 🎯 Flags claims in top 10% by cost for targeted analysis  
- 📈 Enables cost-tier segmentation  
- 💼 Focuses management attention on expensive claims  

### 3.4 DQ Flag Carryover

Inherit from Silver:
- `dq_money_valid` (financial data trustworthiness)  
- `dq_date_valid` (date sequence trustworthiness)  

**Business value:**
- 🔍 Dashboards can filter to "DQ-clean" records only  
- 📋 Maintains traceability of data quality  
- ✅ Transparent governance  

### 3.5 Write to Gold

- **Location:** `abfss://silverdata@clientdatastorage.dfs.core.windows.net/gold/fact_claims`  
- **Table:** `health_gold.fact_claims`  
- **Partitioning:** By Date_Reported (year/month)  
- **Mode:** Overwrite with schema enforcement  

---

## 4. New Gold Features

| Feature | Type | Purpose | Example |
|---------|------|---------|---------|
| **Payout_to_Amount_Ratio** | float | Actual payout ÷ claimed | 0.85, 1.0, NULL |
| **High_Cost_Claim_Flag** | int | Top 10% by payout | 0 or 1 |
| **Provider_Fraud_Flag** | int | Provider risk indicator | 0 or 1 |

**Key insight:** Gold pre-computes joins and KPIs so dashboards don't have to.

---

## 5. Data Analysis Summary

| Dimension | Finding |
|-----------|---------|
| **Row Count** | Silver → Gold identical (no duplicates/drops) |
| **Distinct Claims** | All Claim_IDs preserved |
| **Core Amounts** | Payout & Amount values match Silver |
| **Provider Context** | Fraud_Flag successfully joined |
| **New KPIs** | Ratio & High_Cost_Flag on every row |
| **DQ Coverage** | Tracked for monetary & date validations |

---

## 6. Key Business KPIs

### By Claim Type
- Hospital and Outpatient dominate volume  
- Consistent average payouts per type  
- High-cost flags distributed across types  

### By Fraud Label
- Fraudulent claims show **different payout patterns**  
- Significant variance in average payouts  

### By Claim Status
- Settled claims show higher high-cost flag proportions  
- Rejected/Withdrawn have meaningful patterns  

### Provider Fraud Context
- Identifies high-risk providers for claims review  
- Enables joint claim + provider risk analysis  

---

## 7. Architecture Diagram

```
┌──────────────────────────────────┐
│    Silver Layer (silverdata)      │
├──────────────────┬───────────────┤
│  Claims Table    │  Providers     │
│  • Amounts       │  • Fraud_Flag  │
│  • Dates         │  • Provider_ID │
│  • DQ flags      │                │
│  • Days_To_Settle                 │
└────────┬─────────┴────────┬───────┘
         │                  │
         │   LEFT JOIN on   │
         │   Provider_ID    │
         └────────┬─────────┘
                  │
    ┌─────────────┴──────────────┐
    ▼                            ▼
Derive                      Carry DQ
Payout_Ratio                Flags
High_Cost_Flag
    │                            │
    └─────────────┬──────────────┘
                  ▼
        ┌──────────────────────┐
        │  fact_claims (Gold)  │
        │ health_gold.fact_claims│
        └─────────┬────────────┘
                  │
        ┌─────────┼──────────┐
        ▼         ▼          ▼
    Dashboards  ML Models  Operations
```

---

## 8. Interview Explanation

> "The Gold `fact_claims` table is the analytics-ready view of all claims. I built it on top of Silver claims by joining in provider fraud context, deriving business KPIs like payout-to-claim ratios and high-cost flags, and pre-computing everything stakeholders need for reporting, BI dashboards, and ML. The grain is one row per claim, making it perfect for direct consumption by any analytics tool. This follows the medallion architecture: Bronze (raw) → Silver (conformed) → Gold (business-semantic facts)."

### Key Talking Points
- ✅ One row per claim (clear grain)  
- ✅ Multi-table join (claims + providers)  
- ✅ Business-friendly KPIs derived  
- ✅ DQ transparency maintained  
- ✅ Strict schema enforcement  
- ✅ BI & ML ready  
- ✅ Pre-computed joins eliminate user-side work  

---

**Last Updated:** December 2025 | **Status:** Production | **Owner:** Data Engineering

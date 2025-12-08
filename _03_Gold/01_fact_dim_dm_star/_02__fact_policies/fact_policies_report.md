# 📘 Gold `fact_policies` – Architecture & Business Report

## Table of Contents

1. [Context & Objective](#1-context--objective)  
2. [Silver vs Gold fact_policies](#2-silver-vs-gold-fact_policies)  
3. [Transformations: Silver → Gold](#3-transformations-silver--gold)  
4. [New Gold Features](#4-new-gold-features)  
5. [Data Analysis Summary](#5-data-analysis-summary)  
6. [Key Business KPIs](#6-key-business-kpis)  
7. [Architecture Diagram](#7-architecture-diagram)  
8. [Interview Explanation](#8-interview-explanation)  

---

## 1. Context & Objective

The Gold `fact_policies` layer is the **final analytics-ready view** of all policies following the **medallion architecture**:

| Layer | Purpose | Status |
|-------|---------|--------|
| **Raw** | External CSVs (Kaggle) | Source files |
| **Bronze** | Raw Delta tables (no cleaning) | `rawdata` container |
| **Silver** | Cleaned, validated, enriched | `silverdata` container |
| **Gold** | Analytics-ready facts | `silverdata/gold` |

### Purpose of fact_policies

Create a **single, optimized policies fact table** ready for:
- 📈 BI dashboards & self-service analytics  
- 🤖 Machine learning models (churn, renewal prediction)  
- 💼 Business segmentation & reporting  
- 🎯 Product, pricing & sales analytics  

---

## 2. Silver vs Gold fact_policies

| Area | Silver Policies | Gold fact_policies |
|------|-----------------|-------------------|
| **Grain** | One row per policy | One row per policy (enriched) |
| **Core Fields** | PK, dates, amounts | Same + business bands |
| **Tenure** | Policy_Duration_Days | Tenure_Band (0–6m, 6–12m, 1–2y, 2+y) |
| **Premium** | Annual_Premium_GBP | Premium_Band (Low/Medium/High/VH) |
| **Discount** | Discount_Offered_% | Discount_Band (buckets) + renamed field |
| **Renewal** | Flags + Conversion | Renewal_Outcome (Renewed/Not/No Offer) |
| **DQ Flags** | 3 flags (money, discount, renewal) | Same flags carried forward |
| **BI Readiness** | Intermediate | Full (bands pre-computed) |
| **Segmentation** | Limited | Rich (tenure, premium, discount, product) |

**Result:** Business-friendly fact table with pre-computed segmentations.

---

## 3. Transformations: Silver → Gold

### 3.1 Select & Rename Core Columns

**Input:** Silver Policies table

**Logic:**
```python
fact_base = silver_policies.select(
    "Policy_ID", "Customer_ID", "Product_Line", "Channel",
    "Sum_Insured_GBP", "Annual_Premium_GBP",
    "Policy_Start_Date", "Policy_End_Date", "Policy_Duration_Days",
    "Renewal_Offered_Flag", "Renewal_Accepted_Flag", "Renewal_Conversion",
    F.col("`Discount_Offered_%`").alias("Discount_Offered_Pct"),  # cleaner name
    "dq_money_valid", "dq_discount_valid", "dq_renewal_valid"
)
```

**Business impact:**
- ✅ Clean, intuitive column names  
- ✅ All core business attributes included  

### 3.2 Derive Business Bands

#### Tenure_Band
```python
CASE WHEN Policy_Duration_Days < 180 THEN "0–6 months"
     WHEN Policy_Duration_Days < 365 THEN "6–12 months"
     WHEN Policy_Duration_Days < 730 THEN "1–2 years"
     ELSE "2+ years"
END
```

#### Premium_Band
```python
CASE WHEN Annual_Premium_GBP < 250 THEN "Low (<250)"
     WHEN Annual_Premium_GBP < 750 THEN "Medium (250–750)"
     WHEN Annual_Premium_GBP < 1500 THEN "High (750–1500)"
     ELSE "Very High (1500+)"
END
```

#### Discount_Band
```python
CASE WHEN Discount_Offered_Pct = 0 THEN "No discount"
     WHEN Discount_Offered_Pct <= 10 THEN "0–10%"
     WHEN Discount_Offered_Pct <= 20 THEN "10–20%"
     ELSE "20%+"
END
```

#### Renewal_Outcome
```python
CASE WHEN Renewal_Offered_Flag=1 AND Renewal_Accepted_Flag=1 THEN "Renewed"
     WHEN Renewal_Offered_Flag=1 AND Renewal_Accepted_Flag=0 THEN "Not renewed"
     ELSE "No offer"
END
```

**Business value:**
- 🎯 Simplifies dashboards (no repeated CASE logic)  
- 📊 Enables instant segmentation  
- 💼 Consistent KPI definitions across teams  

### 3.3 DQ Flag Carryover

Inherit from Silver:
- `dq_money_valid` (financial sanity)  
- `dq_discount_valid` (discount bounds)  
- `dq_renewal_valid` (renewal logic)  

**Business value:**
- 🔍 Dashboards can filter to "DQ-clean" records  
- 📋 Maintains traceability  
- ✅ Transparent governance  

### 3.4 Write to Gold

- **Location:** `abfss://silverdata@clientdatastorage.dfs.core.windows.net/gold/fact_policies`  
- **Table:** `health_gold.fact_policies`  
- **Mode:** Overwrite with schema enforcement  

---

## 4. New Gold Features

| Feature | Type | Purpose | Example |
|---------|------|---------|---------|
| **Tenure_Band** | string | Bucketed policy duration | 0–6 months, 2+ years |
| **Premium_Band** | string | Bucketed annual premium | Low, Medium, High |
| **Discount_Band** | string | Bucketed discount % | 0–10%, 20%+ |
| **Renewal_Outcome** | string | Simple renewal label | Renewed, Not renewed |
| **Discount_Offered_Pct** | double | Renamed for clarity | Discount_Offered_% → Pct |

**Key insight:** Gold pre-computes bands so BI doesn't have to.

---

## 5. Data Analysis Summary

| Dimension | Finding |
|-----------|---------|
| **Row Count** | Silver → Gold identical (no duplicates/drops) |
| **Distinct Policies** | All Policy_IDs preserved |
| **Core Amounts** | Premium & Sum Insured match Silver |
| **Duration Metrics** | Tenure_Band distributed across all buckets |
| **Renewal Patterns** | Renewal_Outcome shows renewal performance |
| **DQ Coverage** | Tracked across 3 DQ flags |

---

## 6. Key Business KPIs

### By Tenure Band
- New policies (0–6 months) show growth metrics  
- Long-tenure (2+y) show retention & profitability  
- Duration correlates with renewal propensity  

### By Premium Band
- Low-premium policies dominate volume  
- High-premium policies show higher renewal rates  
- Premium band drives profitability analysis  

### By Discount Band
- No-discount policies vs discounted comparison  
- Higher discounts correlate with acquisition metrics  
- Discount elasticity for pricing optimization  

### By Renewal Outcome
- Renewal rate by tenure, premium, discount  
- Product-level renewal performance  
- Channel-level renewal insights  

---

## 7. Architecture Diagram

```
┌──────────────────────────────────┐
│    Silver Layer (silverdata)      │
│    Policies Table                │
│  • Schema enforced               │
│  • Dates fixed                   │
│  • Money validated               │
│  • Renewal logic checked         │
│  • Policy_Duration_Days          │
│  • Renewal_Conversion            │
│  • 3 DQ flags                    │
└────────┬──────────────────────────┘
         │
         │  Bucket Policy_Duration_Days → Tenure_Band
         │  Bucket Annual_Premium_GBP → Premium_Band
         │  Bucket Discount_Offered_% → Discount_Band
         │  Derive Renewal_Outcome
         │  Carry DQ flags
         ▼
┌──────────────────────────────────┐
│  fact_policies (Gold)            │
│ health_gold.fact_policies          │
│  • Business-friendly bands       │
│  • Renewal outcome labels        │
│  • Simplified naming             │
│  • DQ flags inherited            │
└────────┬──────────────────────────┘
         │
    ┌────┴──────────┬──────────┐
    ▼               ▼          ▼
Dashboards      BI Tools    ML Models
```

---

## 8. Interview Explanation

> "The Gold `fact_policies` table is the analytics-ready view of all policies. Silver ensures data is clean and validated. Gold transforms it into business-friendly segmentations: tenure bands, premium bands, discount bands, and renewal outcome labels. This eliminates repeated logic across dashboards and ensures all teams use the same KPI definitions. The result is a trusted, BI-ready fact table that powers dashboards, churn models, and business intelligence without requiring additional transformations."

### Key Talking Points
- ✅ One row per policy (clear grain)  
- ✅ Pre-computed business bands (Tenure, Premium, Discount)  
- ✅ Renewal outcome labels (Renewed/Not/No Offer)  
- ✅ DQ flags carried forward for transparency  
- ✅ Clean column naming conventions  
- ✅ Consistent KPI definitions  
- ✅ BI & ML ready  

---

**Last Updated:** December 2025 | **Status:** Production | **Owner:** Data Engineering

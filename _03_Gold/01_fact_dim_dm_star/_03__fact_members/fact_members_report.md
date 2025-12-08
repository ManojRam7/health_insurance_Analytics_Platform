# 👥 Gold `fact_members` – Architecture & Business Report

## Table of Contents

1. [Context & Objective](#1-context--objective)  
2. [Silver vs Gold fact_members](#2-silver-vs-gold-fact_members)  
3. [Transformations: Silver → Gold](#3-transformations-silver--gold)  
4. [New Gold Features](#4-new-gold-features)  
5. [Data Analysis Summary](#5-data-analysis-summary)  
6. [Key Business KPIs](#6-key-business-kpis)  
7. [Architecture Diagram](#7-architecture-diagram)  
8. [Interview Explanation](#8-interview-explanation)  

---

## 1. Context & Objective

The Gold `fact_members` layer is the **final analytics-ready view** of all members following the **medallion architecture**:

| Layer | Purpose | Status |
|-------|---------|--------|
| **Raw** | External CSVs (Kaggle) | Source files |
| **Bronze** | Raw Delta tables (no cleaning) | `rawdata` container |
| **Silver** | Cleaned, validated, enriched | `silverdata` container |
| **Gold** | Analytics-ready facts | `silverdata/gold` |

### Purpose of fact_members

Create a **single, optimized member dimension** ready for:
- 📈 BI dashboards & member analytics  
- 🤖 ML models (churn, risk, claims prediction)  
- 💼 Customer segmentation & targeting  
- 🏥 Actuarial & health risk analysis  

---

## 2. Silver vs Gold fact_members

| Area | Silver Members | Gold fact_members |
|------|----------------|-------------------|
| **Grain** | One row per member | One row per member (enriched) |
| **Demographics** | Raw age, BMI, gender | Plus Age_Band, BMI_Band |
| **Health** | Raw chronic disease | Plus Chronic_Flag, Chronic_Group |
| **Employment** | Raw status | Plus Employment_Group |
| **Geography** | Raw region | Plus Region_Group |
| **Risk** | Raw smoker flag | Plus Smoker_Status label |
| **DQ Flags** | dq_age_valid, dq_bmi_valid | Same flags carried forward |
| **BI Readiness** | Intermediate | Full (segments pre-computed) |
| **Segmentation** | Limited | Rich (age, BMI, health, region, employment) |

**Result:** Business-friendly member dimension with risk segmentation.

---

## 3. Transformations: Silver → Gold

### 3.1 Select Core Attributes

**Input:** Silver Members table

**Logic:**
```python
fact_base = silver_members.select(
    "Member_ID", "Policy_ID", "First_Name", "Last_Name",
    "Age", "Gender", "BMI", "Smoker_Flag",
    "Chronic_Disease", "Employment_Status", "Region",
    "dq_age_valid", "dq_bmi_valid"
)
```

**Business impact:**
- ✅ All core member attributes included  
- ✅ DQ flags preserved for transparency  

### 3.2 Derive Risk Segmentation

#### Age_Band
```python
CASE WHEN Age < 30 THEN "18–29"
     WHEN Age < 45 THEN "30–44"
     WHEN Age < 60 THEN "45–59"
     ELSE "60+"
END
```

#### BMI_Band
```python
CASE WHEN BMI < 18.5 THEN "Underweight"
     WHEN BMI < 25 THEN "Normal"
     WHEN BMI < 30 THEN "Overweight"
     ELSE "Obese"
END
```

#### Smoker_Status
```python
CASE WHEN Smoker_Flag = 1 THEN "Smoker"
     ELSE "Non-Smoker"
END
```

#### Chronic_Flag & Chronic_Group
```python
Chronic_Flag = CASE WHEN Chronic_Disease IS NOT NULL THEN 1 ELSE 0 END

Chronic_Group = CASE WHEN Chronic_Disease LIKE '%Diabetes%' THEN "Diabetes"
                     WHEN Chronic_Disease LIKE '%Hypertension%' THEN "Hypertension"
                     ELSE "Other"
                END
```

#### Employment_Group
```python
CASE WHEN Employment_Status = 'Employed' THEN "Employed"
     WHEN Employment_Status = 'Student' THEN "Student"
     WHEN Employment_Status = 'Retired' THEN "Retired"
     ELSE "Other"
END
```

#### Region_Group
```python
CASE WHEN Region BETWEEN 1 AND 100 THEN "Region 1–100"
     WHEN Region BETWEEN 101 AND 200 THEN "Region 101–200"
     ELSE "Other"
END
```

**Business value:**
- 🎯 Enables actuarial risk segmentation  
- 📊 Supports health & claims modeling  
- 💰 Powers pricing & underwriting decisions  

### 3.3 DQ Flag Carryover

Inherit from Silver:
- `dq_age_valid` (age plausibility)  
- `dq_bmi_valid` (BMI plausibility)  

**Business value:**
- 🔍 Dashboards can filter to "DQ-clean" records  
- 📋 Maintains traceability  
- ✅ Transparent governance  

### 3.4 Write to Gold

- **Location:** `abfss://silverdata@clientdatastorage.dfs.core.windows.net/gold/fact_members`  
- **Table:** `health_gold.fact_members`  
- **Mode:** Overwrite with schema enforcement  

---

## 4. New Gold Features

| Feature | Type | Purpose | Example |
|---------|------|---------|---------|
| **Age_Band** | string | Age segmentation | 18–29, 30–44, 60+ |
| **BMI_Band** | string | BMI risk classification | Normal, Overweight, Obese |
| **Smoker_Status** | string | Smoking status label | Smoker, Non-Smoker |
| **Chronic_Flag** | int | Chronic disease presence | 0 or 1 |
| **Chronic_Group** | string | Disease type grouping | Diabetes, Hypertension, Other |
| **Employment_Group** | string | Employment status | Employed, Student, Retired |
| **Region_Group** | string | Geographic grouping | Region 1–100, Region 101–200 |

**Key insight:** Gold pre-computes risk segments for instant member analytics.

---

## 5. Data Analysis Summary

| Dimension | Finding |
|-----------|---------|
| **Row Count** | Silver → Gold identical (no duplicates/drops) |
| **Distinct Members** | All Member_IDs preserved |
| **Demographics** | Age/BMI distributions captured in bands |
| **Health Risk** | Chronic_Flag & Chronic_Group distributions |
| **Smoking Profile** | Smoker vs Non-Smoker distribution |
| **DQ Coverage** | Age & BMI validity tracked across bands |

---

## 6. Key Business KPIs

### By Age Band
- Age distribution shows customer demographics  
- Age correlates with claims frequency & severity  
- Pricing & renewal rates vary by age band  

### By BMI Band
- BMI distribution indicates health risk  
- Obese members show higher claims costs  
- Weight-related conditions more common in higher BMI  

### By Smoker Status
- Smokers show higher claims frequency  
- Smoking affects pricing & risk scoring  
- Critical for underwriting decisions  

### By Chronic Disease
- Chronic members show predictable claim patterns  
- Disease grouping enables targeted offers  
- Chronic_Flag improves ML model accuracy  

### By Employment & Region
- Employment status correlates with retention  
- Regional variation in claims costs  
- Geographic & socioeconomic segmentation  

---

## 7. Architecture Diagram

```
┌──────────────────────────────────┐
│    Silver Layer (silverdata)      │
│    Members Table                 │
│  • Schema enforced               │
│  • Demographics validated        │
│  • Contact standardized          │
│  • Address cleaned               │
│  • 2 DQ flags (age, BMI)         │
└────────┬──────────────────────────┘
         │
         │  Bucket Age → Age_Band
         │  Bucket BMI → BMI_Band
         │  Label Smoker_Flag → Smoker_Status
         │  Group Chronic_Disease → Chronic_Group
         │  Standardize Employment → Employment_Group
         │  Bucket Region → Region_Group
         │  Carry DQ flags
         ▼
┌──────────────────────────────────┐
│  fact_members (Gold)             │
│ health_gold.fact_members           │
│  • Risk segments (age, BMI)      │
│  • Health indicators             │
│  • Employment & region groups    │
│  • DQ flags inherited            │
└────────┬──────────────────────────┘
         │
    ┌────┴──────────┬──────────┐
    ▼               ▼          ▼
Dashboards      BI Tools    ML Models
```

---

## 8. Interview Explanation

> "The Gold `fact_members` table is the analytics-ready view of all members. Silver ensures data is clean and validated. Gold transforms it into business-friendly risk segments: age bands, BMI bands, smoker status, chronic disease grouping, employment classification, and geographic grouping. These segments directly support actuarial pricing, churn prediction, claims modeling, and customer targeting. The result is a trusted, BI-ready member dimension with transparent data quality that enables 360° customer analytics without requiring additional transformations."

### Key Talking Points
- ✅ One row per member (clear grain)  
- ✅ Pre-computed risk segments (Age, BMI, Smoker, Chronic)  
- ✅ Health & employment groupings  
- ✅ DQ flags carried forward for transparency  
- ✅ Supports actuarial & underwriting  
- ✅ Powers churn & claims models  
- ✅ 360° customer analytics ready  

---

**Last Updated:** December 2025 | **Status:** Production | **Owner:** Data Engineering

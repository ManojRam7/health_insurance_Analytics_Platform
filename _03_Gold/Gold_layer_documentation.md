# Gold Layer: Architecture and Data Products

Covers fact tables, dimensions, star schemas, data marts, ML feature tables and persisted models.

---

# 1. Purpose of the Gold Layer
The **Gold Layer** represents the *business-ready*, analytics-ready, ML-ready datasets used across reporting, dashboards, actuarial modeling, pricing teams, and fraud/churn analytics.

Silver provides trusted, cleaned, validated data.  
**Gold transforms that into domain-specific, business-optimized structures:**

- **Fact tables** (policy, member, claims measures)
- **Dimension tables** (hierarchies & attributes)
- **Star schemas** (join-optimized query models)
- **Data marts** (KPI-focused tables for business units)
- **ML feature tables** (supervised learning datasets)
- **Model artifacts** (persisted ML pipelines for scoring)


---

# 2. Gold Layer Storage Structure (ADLS Gen2)

All Delta tables are stored under:

```
abfss://golddata@clientdatastorage.dfs.core.windows.net/
```

### **2.1 Fact Tables**
| Table | Description | ADLS Path |
|-------|-------------|-----------|
| `fact_policies` | Policy-level measures | `.../fact_policies` |
| `fact_members` | Member-level measures | `.../fact_members` |
| `fact_claims` | Claims-level measures | `.../fact_claims` |

---

### **2.2 Dimension Tables**
| Dimension | Column Examples | ADLS Path |
|----------|-----------------|-----------|
| `dim_channel` | Channel_Code, Channel_Name | `.../dim_channel` |
| `dim_product_line` | Product_Line_Code, Product_Line | `.../dim_product_line` |
| `dim_providers` | Provider_ID, Fraud_Flag, Risk_Tier | `.../dim_providers` |

---

### **2.3 Star Schema Tables**
| Star Table | Joins Fact With | ADLS Path |
|------------|----------------|-----------|
| `star_policies` | dim_channel, dim_product_line | `.../star_policies` |
| `star_members` | fact_members + dim tables | `.../star_members` |
| `star_claims` | fact_claims + dim_providers | `.../star_claims` |

---

### **2.4 Data Marts**
| Data Mart | Business Focus | ADLS Path |
|-----------|----------------|-----------|
| `dm_policy_retention` | Renewal KPIs | `.../dm_policy_retention` |
| `dm_member_value` | Customer LTV metrics | `.../dm_member_value` |
| `dm_claims_experience` | Cost ratios & provider performance | `.../dm_claims_experience` |

---

### **2.5 ML Feature Tables**
| Feature Table | Used For | ADLS Path |
|---------------|----------|------------|
| `ft_policy_churn` | Churn prediction model | `.../ft_policy_churn` |
| `ft_claims_risk` | Fraud / High-cost claim model | `.../ft_claims_risk` |

---

### **2.6 Persisted ML Models**
| Model | Purpose | ADLS Path |
|-------|----------|-----------|
| `policy_churn_model` | Predicting non-renewals | `.../models/policy_churn_model` |
| `claims_risk_model` | Fraud/high-cost classification | `.../models/claims_risk_model` |

---

# 3. Gold Layer Architecture Diagram

## **3.1 High-Level Lakehouse Flow**
```mermaid
flowchart TD
    RAW[RAW (CSV from Kaggle)] --> BRZ[BRONZE (raw Delta)]
    BRZ --> SIL[SILVER (cleaned, validated, curated)]
    SIL --> GOLD_FACTS[Gold Fact Tables]
    SIL --> GOLD_DIMS[Gold Dimension Tables]

    GOLD_FACTS --> STAR[Star Schemas]
    GOLD_DIMS --> STAR

    STAR --> DM[Data Marts]

    DM --> FEAT[ML Feature Tables]
    FEAT --> MODELS[Model Storage]

    MODELS --> DASH[Dashboards & Batch Scoring]
```

---

# 4. Business Role of Each Gold Layer Component

## **4.1 Fact Tables (Quantitative Measures)**
Fact tables store **events** or **measures**:

### **fact_policies**
- Sum insured  
- Premiums  
- Tenure  
- Renewal outcomes  

Used for underwriting, pricing, profitability.

### **fact_members**
- Member demographics  
- Risk factors  
- Policy linkages  

Used for customer analytics / LTV.

### **fact_claims**
- Claim amount  
- Payout  
- Fraud label  
- Settled/Pending  

Used for claims operations and fraud prevention.

---

## **4.2 Dimensions (Business Hierarchies & Categories)**

Dimensions convert cryptic categories into business-friendly labels.

Examples:
- Channel → *Broker / Agent / Online*
- Product Line → *Health / Motor / Travel*
- Providers → includes fraud tier mapping

Dimensions **drive BI dashboards**, aggregation, and filtering.

---

## **4.3 Star Schemas (Optimized for BI Analytics)**

### Why they exist:
- Faster PowerBI/Tableau queries  
- Denormalized for performance  
- Natural join patterns for analysts  

Example: `star_claims`
```
fact_claims
   JOIN dim_providers
```
Creates columns like:
- Provider_Fraud_Flag  
- Provider_Risk_Tier  
- Claim_Type_Code  

This structure is exactly what BI teams expect.

---

## **4.4 Data Marts (Department-Focused KPI Models)**

### `dm_policy_retention`
Tracks:
- Offer/acceptance rates  
- Renewal conversion  
- Premium by year  

### `dm_member_value`
Tracks:
- Customer lifetime value  
- Member aging curves  
- Policy migration  

### `dm_claims_experience`
Tracks:
- Claim cost ratios  
- Fraud incidence by provider  
- High-cost claim distributions  

These marts power leadership dashboards.

---

## **4.5 ML Feature Tables (Supervised Model Inputs)**

### `ft_policy_churn`
Features include:
- Premium band  
- Tenure band  
- Discount percentile  
- Renewal history pattern  
- Customer demographic joins  

Target: `Churn_Label`

### `ft_claims_risk`
Features include:
- Claim amount  
- Provider fraud tier  
- Claim type  
- Claim status  
- High-cost flag  

Target: `is_fraudulent` or `High_Cost_Flag`.

These tables make model training **reproducible & explainable**.

---

## **4.6 Model Storage (Persisted ML Pipelines)**

Persisted ML pipelines include:
- String indexers  
- One-hot encoders  
- Vector assemblers  
- Logistic regression classifier  

Stored as:
```
/models/policy_churn_model
/models/claims_risk_model
```

Used for:
- Batch scoring  
- POC deployments  
- BI integration (probability fields)

---

# 5. Example: Star Schema for Claims

```
star_claims
├── facts:
│     Claim_ID
│     Claim_Amount_GBP
│     Payout_GBP
│     Fraud_Label
│     High_Cost_Flag
│     Claim_Status
│     Claim_Type
│
└── dimensions:
      Provider_ID → dim_providers
          Provider_Fraud_Flag
          Provider_Risk_Tier
```

---

# 6. Example: ML Churn Scoring Output

| Policy_ID | churn_prob | prediction | Premium_Band | Tenure_Band |
|-----------|------------|------------|--------------|-------------|
| P_001234  | 0.83       | 1          | High         | 0–6 months  |
| P_006789  | 0.12       | 0          | Medium       | 1–2 years   |

---


# 7. Gold Table Inventory

```
/fact_policies
/fact_members
/fact_claims
/dim_channel
/dim_product_line
/dim_providers
/star_policies
/star_members
/star_claims
/dm_policy_retention
/dm_member_value
/dm_claims_experience
/ft_policy_churn
/ft_claims_risk
/models/policy_churn_model
/models/claims_risk_model
```

Perfect, the scoring output looks exactly how we want it ✅
Let’s capture the whole ML layer cleanly now.

Below are **two ready-to-paste docs**:

* `ML_report.txt` – plain text, interview-script friendly
* `ML_report.md` – nice markdown version for GitHub / project repo

---

## 1) `ML_report.txt`

```text
==========================================================
ML LAYER – POLICY CHURN & CLAIMS RISK (TEXT REPORT)
==========================================================

1. PURPOSE & BUSINESS NARRATIVE
-------------------------------

In this project I wanted to go beyond pure data engineering and show how a data scientist at a company like a consultancy would build end-to-end ML solutions for an insurance client (Health Insurance-style).

The goal of the ML layer is to answer two concrete business questions:

1) Policy Churn:
   “Given a policy’s characteristics (product, channel, premium, discounts, tenure, etc.), what is the probability this policy will NOT renew next term?”

2) Claims Risk:
   “Given a claim and its context (claim type, amount, payout, provider behaviour, etc.), how risky is this claim in terms of fraud or high cost?”

Both problems are framed as **supervised classification** tasks sitting on top of the curated **Gold** layer:

- Bronze → Silver → Gold fact tables → Star schemas → ML feature tables → Models


2. DATA SOURCES & FEATURE TABLES
--------------------------------

Everything for ML is built from already-governed GOLD data, not raw data.

Main inputs:

- fact_policies (Gold)
- fact_claims (Gold)
- dim_channel, dim_product_line, dim_claim_type, dim_providers (Gold)
- Data quality flags and engineered features from Silver/Gold (e.g. tenure, discount bands, payout ratios, risk tiers)

From these, I build two dedicated ML feature tables:

1) ft_policy_churn
2) ft_claims_risk

Both are written as Delta tables into the golddata container and include a `dataset_split` column
(train/test) so that evaluation is **reproducible and consistent across experiments**.


3. LABEL DEFINITIONS
--------------------

A) Policy churn label (Churn_Label)

Business definition:
- Churn_Label = 1  → policy did NOT renew (customer churned)
- Churn_Label = 0  → policy renewed

Implementation:
- Use the renewal flags from Silver/Gold:
    - Renewal_Offered_Flag
    - Renewal_Accepted_Flag
- Logic:
    - If Renewal_Offered_Flag = 1 AND Renewal_Accepted_Flag = 1 → renewed (label 0)
    - If Renewal_Offered_Flag = 1 AND Renewal_Accepted_Flag = 0 → churned (label 1)
    - All other cases (no offer / missing data) are labelled as NULL and dropped from training.
- We explicitly filter out rows with NULL labels before modeling to avoid training errors.

B) Claims risk labels (Is_Fraudulent_Claim, Is_High_Cost)

Business definition:
- Two separate risk dimensions:
    1. Fraud risk
       - Is_Fraudulent_Claim = 1 if the claim label indicates fraud, else 0.
    2. High-cost risk
       - Is_High_Cost = 1 if the claim amount is above a chosen percentile threshold (e.g., top X%).

Implementation:
- We derive these flags from:
    - Fraud_Label in the claims table
    - High_Cost_Claim_Flag or thresholds based on Claim_Amount_GBP
- The ML feature table ft_claims_risk contains:
    - Claim_Fraud_Label (original flag)
    - Provider_Fraud_Label / Provider_Risk_Tier from dim_providers
    - Is_Fraudulent_Claim and Is_High_Cost as targets for separate experiments.


4. KEY FEATURES USED
--------------------

A) Policy churn features (ft_policy_churn)

Each policy row in ft_policy_churn is enriched with:

IDENTIFIERS (for explainability, not model input):
- Policy_ID
- Customer_ID

CORE NUMERIC FEATURES:
- Sum_Insured_GBP
- Annual_Premium_GBP
- Policy_Duration_Days
- Premium_per_1k_SumInsured = Annual_Premium_GBP / (Sum_Insured_GBP / 1000)

CATEGORICAL FEATURES:
- Product_Line        (Health, Dental, Motor, Travel, etc.)
- Channel             (Agent, Broker, Online, Partner)
- Renewal_Outcome     (Renewed, Not renewed, No offer, No renewal info)
- Tenure_Band         (0–6 months, 6–12 months, 1–2 years, 2+ years)
- Premium_Band        (Low, Medium, High, Very High)
- Discount_Band       (No discount, 0–10%, 10–20%, 20%+)
- Is_Discounted       (binary indicator)

DATA QUALITY FLAGS (used either as features or for filtering):
- dq_money_valid
- dq_discount_valid
- dq_renewal_valid

TARGET:
- Churn_Label (0 = renew, 1 = churn)


B) Claims risk features (ft_claims_risk)

IDENTIFIERS:
- Claim_ID
- Member_Key
- Provider_ID

CORE NUMERIC FEATURES:
- Claim_Amount_GBP
- Payout_GBP
- Payout_to_Amount_Ratio = Payout_GBP / Claim_Amount_GBP
- Days_To_Settle (difference between Date_Reported and Date_Settled)

CATEGORICAL FEATURES:
- Claim_Type_Name     (Hospital, Dental, Outpatient, Travel, etc.)
- Claim_Outcome_Status (Settled, Pending, Rejected, Withdrawn)
- Provider_Risk_Tier  (Low risk, High risk, etc.)
- Provider_Fraud_Label (0/1)

DATA QUALITY FLAGS:
- dq_money_valid
- dq_date_valid

TARGETS:
- Is_Fraudulent_Claim (for fraud modelling)
- Is_High_Cost        (for high-cost risk modelling)


5. PREPROCESSING & PIPELINES
----------------------------

All models are built using Spark ML Pipelines to keep the training and scoring logic consistent.

Preprocessing steps (for both churn and claims models):

1) Null handling:
   - Numeric features: fill missing values with 0 or simple imputations.
   - Categorical features: fill missing with "Unknown".
   - Ensures no nulls reach the ML algorithms.

2) Encoding:
   - Use StringIndexer on categorical columns (e.g. Product_Line, Channel, Tenure_Band, etc.).
   - Then OneHotEncoder to turn indexed columns into sparse indicator vectors.

3) Feature assembly:
   - VectorAssembler collects all numeric features + OHE categorical features into a single `features` vector.

4) Train/test split:
   - Instead of random splitting inside the model, we pre-assign `dataset_split` in the feature tables.
   - That means different experiments are always comparable because train/test composition is stable.

This entire pipeline (preprocessing + model) is saved and reused for both training and scoring.


6. MODELS TRAINED
-----------------

For Policy Churn (classification):

- Baseline: Logistic Regression (LR)
  - Pros: fast, interpretable coefficients.
- Tree models:
  - RandomForestClassifier (RF)
  - GBTClassifier (Gradient Boosted Trees)

For Claims Risk (classification):

- RandomForestClassifier on ft_claims_risk
- (You can also replicate LR and GBT as variants.)

Why these choices?
- These are standard, battle-tested algorithms for tabular insurance data.
- Logistic Regression provides a strong baseline and interpretability.
- RF and GBT capture non-linear relationships between premium, discounts, tenure, and churn/claims behaviour.


7. EVALUATION LOGIC
-------------------

We evaluate on the **held-out test split** (dataset_split = 'test').

For churn:

- Metrics per model:
  - ROC AUC
  - PR AUC (precision-recall)
  - Accuracy
  - F1-score
  - Confusion matrix (TP, FP, FN, TN)

- Approach:
  1) Fit model on train_pre.
  2) Score test_pre.
  3) Use BinaryClassificationEvaluator for AUC.
  4) Build confusion matrix + precision/recall/F1 by hand.

For claims risk:

- Very similar strategy, focusing on:
  - ROC AUC (for ranking high-risk claims)
  - Recall at top risk deciles (how many fraud/high-cost claims captured in top X%).

We then compare the models and select an overall “best” model for deployment (for example, Random Forest with the best balance of AUC and business interpretability).

Importantly, we avoid any label leakage and only use features that would be known at scoring time.


8. MODEL PERSISTENCE & SCORING FLOW
-----------------------------------

Once the best churn model is chosen, we save the **entire PipelineModel** (preprocessing + classifier) to ADLS:

- MODEL_BASE_PATH = "abfss://golddata@clientdatastorage.dfs.core.windows.net/models"
- MODEL_NAME      = "policy_churn_best"
- MODEL_PATH      = MODEL_BASE_PATH + "/" + MODEL_NAME

Code pattern:
- pipeline.write().overwrite().save(MODEL_PATH)
- Later: loaded_model = PipelineModel.load(MODEL_PATH)

Scoring flow (as implemented in Cell 9):

1) Load the best model (PipelineModel.load).
2) Take a sample of policies from test_df.
3) Apply the same preprocessing via `prep_nulls` and the saved pipeline.
4) Extract churn probability:
   - Convert probability vector to array: vector_to_array("probability")
   - Take index [1] → P(churn=1)
5) Return:
   - Policy_ID, Customer_ID
   - Churn_Label (if known)
   - churn_prob (probability of churn)
   - prediction (0/1)
   - Product_Line, Channel, Premium_Band, Tenure_Band, Discount_Band

This simulates what an API or batch scoring job would do in production to drive:

- Retention campaigns
- Pricing adjustments
- Portfolio risk monitoring


9. HOW THIS MATCHES A REAL DATA SCIENCE PROJECT
-----------------------------------------------

This ML layer mirrors how a data scientist would work in a real client project:

- Start from curated, governed data (Gold facts & dims).
- Build explicit ML feature tables (ft_policy_churn, ft_claims_risk).
- Define clear target labels aligned to business questions.
- Use reproducible train/test splits with a `dataset_split` column.
- Package preprocessing + model into a single Spark ML pipeline.
- Compare multiple algorithms, not just one.
- Persist the best model and demonstrate how to score new data.
- Keep everything traceable, auditable, and easy to explain to business users.

In interviews I can walk through:
- The business question,
- The feature engineering,
- The choice of models,
- How evaluation was done,
- How the model is saved and served.

This shows not just coding skills but also an understanding of how to take a model from raw data all the way to something that a client like Health Insurance can actually use.
```

---

## 2) `ML_report.md`

````markdown
# ML Layer – Policy Churn & Claims Risk

## 1. Purpose & Business Narrative

The ML layer sits on top of the **Bronze → Silver → Gold** data platform and answers two concrete business questions for an insurance client:

1. **Policy Churn**  
   > Given a policy’s attributes (product, channel, premium, discounts, tenure, etc.), what is the probability this policy will **not renew**?

2. **Claims Risk**  
   > Given a claim and its context (claim type, amount, payout, provider behaviour, etc.), how risky is this claim in terms of **fraud** or **high cost**?

The idea is to replicate what a data scientist at a large consultancy (a consultancy-style) would build for a client like Health Insurance:

- Use curated Gold data, not raw CSVs.
- Engineer meaningful business features.
- Train and compare multiple models.
- Persist the best model and show how it can be scored in production.

---

## 2. Data Sources & Feature Tables

All ML work is based on the **Gold layer**, never directly on raw data.

**Gold inputs:**

- `health_gold.fact_policies`
- `health_gold.fact_claims`
- `health_gold.dim_channel`
- `health_gold.dim_product_line`
- `health_gold.dim_claim_type`
- `health_gold.dim_providers`

From these, we construct two ML feature tables in the `golddata` container:

1. `ft_policy_churn` – one row per policy, with churn label.
2. `ft_claims_risk` – one row per claim, with fraud / high-cost flags.

Both tables include a `dataset_split` column (`train` / `test`) so that every experiment is run on the same deterministic split.

---

## 3. Label Definitions

### 3.1 Policy Churn (`Churn_Label`)

**Business definition:**

- `Churn_Label = 1` → the policy **did not renew**.
- `Churn_Label = 0` → the policy **renewed**.

**Implementation:**

Uses the renewal flags from the Silver/Gold policies:

- `Renewal_Offered_Flag`
- `Renewal_Accepted_Flag`

Logic:

- Offered = 1 and Accepted = 1 → renewed (`Churn_Label = 0`)
- Offered = 1 and Accepted = 0 → churned (`Churn_Label = 1`)
- All other cases → label = `NULL` (and excluded from training)

We explicitly **drop rows with null labels** before training to avoid Spark ML errors and to keep the target well-defined.

---

### 3.2 Claims Risk (`Is_Fraudulent_Claim`, `Is_High_Cost`)

Two separate targets:

1. **Fraud risk**
   - `Is_Fraudulent_Claim = 1` if the claim’s `Fraud_Label` indicates fraud.
   - Otherwise `0`.

2. **High-cost risk**
   - `Is_High_Cost = 1` if `Claim_Amount_GBP` is above a chosen percentile threshold (e.g. the top X% of claims).
   - Otherwise `0`.

These targets are derived in `ft_claims_risk` alongside the original labels (e.g. `Claim_Fraud_Label`, `Provider_Fraud_Label`, `High_Cost_Claim_Flag` where available).

---

## 4. Key Features

### 4.1 Policy Churn Features (`ft_policy_churn`)

**Identifiers (for explainability):**

- `Policy_ID`
- `Customer_ID`

**Numeric features:**

- `Sum_Insured_GBP`
- `Annual_Premium_GBP`
- `Policy_Duration_Days` (from Silver)
- `Premium_per_1k_SumInsured = Annual_Premium_GBP / (Sum_Insured_GBP / 1000)`

**Categorical features:**

- `Product_Line` (Health, Dental, Motor, Travel, …)
- `Channel` (Agent, Broker, Online, Partner)
- `Tenure_Band` (0–6 months, 6–12 months, 1–2 years, 2+ years)
- `Premium_Band` (Low, Medium, High, Very High)
- `Discount_Band` (No discount, 0–10%, 10–20%, 20%+)
- `Renewal_Outcome` (Renewed, Not renewed, No offer, No renewal info)
- `Is_Discounted` (binary)

**Data quality flags:**

- `dq_money_valid`
- `dq_discount_valid`
- `dq_renewal_valid`

**Target:**

- `Churn_Label` (0 / 1)

---

### 4.2 Claims Risk Features (`ft_claims_risk`)

**Identifiers:**

- `Claim_ID`
- `Member_Key`
- `Provider_ID`

**Numeric:**

- `Claim_Amount_GBP`
- `Payout_GBP`
- `Payout_to_Amount_Ratio`
- `Days_To_Settle`

**Categorical:**

- `Claim_Type_Name` (Hospital, Dental, Outpatient, Travel, …)
- `Claim_Outcome_Status` (Settled, Pending, Rejected, Withdrawn, …)
- `Provider_Risk_Tier` (Low risk, High risk, …)
- `Provider_Fraud_Label` (0 / 1)

**Data quality:**

- `dq_money_valid`
- `dq_date_valid`

**Targets:**

- `Is_Fraudulent_Claim`
- `Is_High_Cost`

---

## 5. Preprocessing & Spark ML Pipelines

For both churn and claims risk, all transformations are wrapped into a **Spark ML `Pipeline`**, ensuring that training and scoring use exactly the same logic.

Steps:

1. **Null handling**
   - Numeric columns: fill `NULL` with 0 (or simple imputations).
   - Categorical columns: fill `NULL` with `"Unknown"`.

2. **Indexing & Encoding**
   - `StringIndexer` on each categorical feature (e.g. `Product_Line`, `Channel`, `Tenure_Band`, …).
   - `OneHotEncoder` converts indexed categories into sparse vectors.

3. **Feature assembly**
   - `VectorAssembler` combines numeric features and encoded categoricals into one `features` vector.

4. **Train/test split**
   - Use the pre-computed `dataset_split` column (`train` vs `test`) instead of calling `.randomSplit()` in each experiment.
   - This keeps experiments reproducible and comparable.

---

## 6. Models Trained

### 6.1 Policy Churn Models

- **Logistic Regression**
  - Baseline interpretable model.
  - Good for understanding the direction/strength of features like discount or tenure.

- **Random Forest Classifier**
  - Handles non-linear interactions.
  - Robust, often strong on tabular datasets.

- **Gradient Boosted Trees (GBTClassifier)**
  - More expressive ensemble model.
  - Good for ranking policies by churn risk.

Each model is wrapped inside the same preprocessing pipeline, so only the classifier changes.

### 6.2 Claims Risk Models

- **Random Forest on `ft_claims_risk`**
  - Inputs: claim features + provider risk signals.
  - Targets: `Is_Fraudulent_Claim` and/or `Is_High_Cost`.

The overall pattern is the same as for churn:
- Preprocess → assemble → train RF → evaluate on `dataset_split = 'test'`.

---

## 7. Evaluation Strategy

### 7.1 Policy Churn

Evaluate on the test subset:

- **Metrics per model**
  - ROC AUC
  - PR AUC
  - Accuracy
  - Precision, Recall, F1
  - Confusion matrix (TP, FP, FN, TN)

- **Process**
  1. Fit model on `train_pre`.
  2. Score `test_pre`.
  3. Use `BinaryClassificationEvaluator` for AUC.
  4. Build confusion matrix and derived metrics with DataFrame operations.

This allows a clear comparison of LR vs RF vs GBT on the same data.

### 7.2 Claims Risk

For fraud / high-cost models we focus more on:

- ROC AUC
- Recall at top risk deciles (e.g. “What % of fraud claims appear in the top 10% highest risk scores?”)

This is closer to how fraud teams think: they care about **capturing as many bad claims as possible** in their investigation queue.

---

## 8. Model Persistence & Scoring

### 8.1 Saving the best model

Once the best policy churn model is selected, the full `PipelineModel` (preprocessing + classifier) is saved to ADLS:

```python
MODEL_BASE_PATH = "abfss://golddata@clientdatastorage.dfs.core.windows.net/models"
MODEL_NAME = "policy_churn_best"
MODEL_PATH = f"{MODEL_BASE_PATH}/{MODEL_NAME}"

best_model.write().overwrite().save(MODEL_PATH)
````

Later it can be loaded with:

```python
from pyspark.ml import PipelineModel

loaded_model = PipelineModel.load(MODEL_PATH)
```

### 8.2 Scoring flow (Cell 9)

1. Load `loaded_model`.

2. Sample policies from `test_df` (or from fresh data).

3. Apply the same null-handling + feature pipeline.

4. Convert the probability vector to an array:

   ```python
   from pyspark.ml.functions import vector_to_array

   scored_raw = loaded_model.transform(prep_nulls(sample))
   scored = scored_raw.withColumn("prob_arr", vector_to_array("probability"))
   ```

5. Extract the probability of churn (`P(y=1)`):

   ```python
   churn_prob = F.col("prob_arr")[1].alias("churn_prob")
   ```

6. Select key columns:

   * `Policy_ID`, `Customer_ID`
   * `Churn_Label`
   * `churn_prob`, `prediction`
   * `Product_Line`, `Channel`, `Annual_Premium_GBP`
   * `Tenure_Band`, `Discount_Band`

This is effectively a **serving view** that a downstream API, campaign engine or dashboard could consume.

---

## 9. How This Reflects a Real DS Project

This ML layer demonstrates an end-to-end, production-style workflow:

* Start from **governed data** (Gold facts/dims).
* Design **feature tables** specifically for ML.
* Define **clear, business-owned labels**.
* Use **Spark ML Pipelines** for consistent training and scoring.
* Compare multiple algorithms, not just a single model.
* Persist the best model into **cloud storage (ADLS)**.
* Show a realistic **scoring flow**, including probability extraction.

In interviews, this lets you confidently explain:

1. The business question (churn / risk).
2. How you engineered features and labels.
3. Why you chose LR, RF, GBT.
4. How you evaluated and selected models.
5. How the model is saved and used to score new policies/claims.

This positions the whole project as a genuine **data science solution**, not just a toy notebook.

```

---

If you’d like, next we can:

- Add a **short “ML section”** into your main project README tying this to a consultancy/Health Insurance experience, or  
- Draft an **interview script** specifically for the ML part (like we did for Policies Silver / Gold).
::contentReference[oaicite:0]{index=0}
```

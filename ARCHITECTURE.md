# Health Insurance ML Pipeline - Technical Architecture

## 1. System Overview

The Health Insurance ML pipeline implements a **Medallion Architecture** with integrated ML capabilities for predictive analytics across policy management and claims processing.

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
│   (Kaggle, Internal Systems, External Data Feeds)       │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │   BRONZE LAYER          │
        │   (Raw Data Ingestion)   │
        │   - Delta Tables         │
        │   - No transformation    │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   SILVER LAYER          │
        │   (Data Cleaning)        │
        │   - Deduplication       │
        │   - Data validation     │
        │   - Null handling       │
        │   - Quality checks      │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────────────────────┐
        │         GOLD LAYER                      │
        │  (Analytics & ML-Ready)                  │
        │  ┌────────────────────────────────────┐ │
        │  │ Features & ML Models (03a)         │ │
        │  │ - ft_policy_churn                  │ │
        │  │ - ft_claims_risk_split             │ │
        │  │ - models/* (with versioning)       │ │
        │  │ - scored_* (incremental)           │ │
        │  └────────────────────────────────────┘ │
        │  ┌────────────────────────────────────┐ │
        │  │ Star Schemas & Data Marts (03b)    │ │
        │  │ - star_claims, star_policies       │ │
        │  │ - dm_policy_retention              │ │
        │  │ - dm_member_value                  │ │
        │  │ - dm_claims_experience             │ │
        │  └────────────────────────────────────┘ │
        │  ┌────────────────────────────────────┐ │
        │  │ Monitoring & Quality (03c)         │ │
        │  │ - ml_monitoring (run tracking)     │ │
        │  │ - dq_monitoring (quality metrics)  │ │
        │  └────────────────────────────────────┘ │
        └─────────────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │   BI DASHBOARDS         │
        │   & REPORTS             │
        └─────────────────────────┘
```

## 2. Component Architecture

### 2.1 Bronze Layer (Raw Data)

**Purpose**: Immutable copy of source data

**Tables**:
```
bronze_policies
├── columns: [policy_id, customer_id, product_line, premium, sum_insured, ...]
├── rowcount: ~100K
└── format: Delta (ACID compliant)

bronze_members
├── columns: [member_key, customer_id, age, gender, bmi, ...]
├── rowcount: ~50K
└── format: Delta

bronze_claims
├── columns: [claim_id, member_key, claim_amount, claim_type, ...]
├── rowcount: ~2.5M
└── format: Delta

bronze_providers
├── columns: [provider_id, provider_name, risk_tier, ...]
├── rowcount: ~5K
└── format: Delta
```

**Data Flow**: 
- Raw data → `_00_Pre_Pilot` (connector setup)
- Data load → `_01_Bronze/01_data_load.ipynb`
- Format: Parquet/CSV → Delta Lake

### 2.2 Silver Layer (Cleaned Data)

**Purpose**: Data quality, deduplication, standardization

**Transformations**:
```
Policies Silver:
├── Deduplicate on [policy_id, effective_date]
├── Drop rows with invalid premium/duration
├── Standardize dates, channels, product lines
├── Compute derived fields (premium_per_1k_suminsureds, tenure_bands)
└── Flag data quality issues (dq_columns)

Members Silver:
├── Deduplicate on [member_key]
├── Validate age (0-120), BMI (15-50)
├── Standardize gender, occupation categories
├── Compute age_band, bmi_band
└── Handle missing values strategically

Claims Silver:
├── Deduplicate on [claim_id, settlement_date]
├── Validate claim_amount, payout (> 0)
├── Compute derived fields (payout_ratio, days_to_settle)
├── Categorize claim_status, claim_type_code
└── Create initial risk labels (is_fraudulent, is_high_cost)

Providers Silver:
├── Deduplicate on [provider_id]
├── Assign risk_tier based on claim patterns
├── Validate provider_type
└── Compute provider_metrics (fraud_rate, avg_cost)
```

**Data Quality Rules** (configured in `config.DATA_QUALITY_THRESHOLDS`):
- Max null %: policies (20%), members (15%), claims (20%)
- Numeric ranges: premium (100-10000), age (18-95), BMI (15-50)
- Categorical domains: channels {direct, agent, corporate}, claim_status {open, settled, denied}

**Notebooks**:
- `_02_Silver/01_policies_silver.ipynb`
- `_02_Silver/02_members_silver.ipynb`
- `_02_Silver/03_claims_silver.ipynb`
- `_02_Silver/04_providers_silver.ipynb`

### 2.3 Gold Layer - Features & ML (03a)

**Purpose**: Feature engineering and model training/scoring

#### 2.3.1 Feature Engineering
```
Feature Table: ft_policy_churn_split
├── Source: silver_policies + members + claims (aggregated)
├── Target: Churn_Label (0/1) - 12-month non-renewal
├── Features: 11 features
│   ├── Numeric (4): Sum_Insured_GBP, Annual_Premium_GBP, Policy_Duration_Days, Premium_per_1k_SumInsured
│   ├── Categorical (7): Product_Line, Channel, Tenure_Band, Premium_Band, Discount_Band, Renewal_Outcome, Is_Discounted
├── Train/Test Split: 80/20 (stratified on Churn_Label)
├── Null Handling: numeric→0.0, categorical→'Unknown'
└── Rowcount: ~100K (80K train, 20K test)

Feature Table: ft_claims_risk_split
├── Source: silver_claims + providers + members
├── Targets: [Is_Fraudulent_Claim, Is_High_Cost_Claim] (0/1)
├── Features: 9 features
│   ├── Numeric (4): Claim_Amount_GBP, Payout_GBP, Payout_to_Amount_Ratio, Days_To_Settle
│   ├── Categorical (5): Claim_Type_Name, Claim_Status, Claim_Type_Code, Provider_Risk_Tier, Provider_ID
├── Train/Test Split: 80/20 (stratified)
├── Null Handling: numeric→0.0, categorical→'Unknown'
└── Rowcount: ~2.5M (2.0M train, 0.5M test)
```

**Notebooks**:
- `_03_Gold/02_ML_Features/01_claim_features.ipynb` - Feature engineering
- `_03_Gold/02_ML_Features/02_ML_Feature_Analysis.ipynb` - EDA

#### 2.3.2 Model Training (Priority 1, 2, 8)

**Training Workflow**:
```
ft_policy_churn_split (80K train, 20K test)
└── Null Handling (config strategy)
    └── Feature Pipeline
        ├── StringIndexer (categorical)
        ├── OneHotEncoder (categorical)
        ├── VectorAssembler (all features)
        └── Train 3 Models in Parallel:
            ├── LogisticRegression (maxIter=100, regParam=0.01)
            ├── RandomForest (numTrees=100, maxDepth=8) + class weights
            ├── GBTClassifier (maxIter=80, maxDepth=5)
            └── Evaluate on test set
                ├── AUC ROC (primary metric)
                ├── AUC PR (secondary)
                ├── F1 Score, Accuracy
                └── Feature Importance (top-10)
```

**Key Implementation**:
- **Priority 2**: Class weights computed as `weight_i = total_samples / (num_classes × count_i)`
- **Priority 8**: Feature importance extracted from tree models → logged to MLflow
- **Priority 1**: Model saved with version format `v1.0_{YYYYMMDD_HHMMSS}` using `config.get_model_path()`
- **Config-driven**: All hyperparameters from `config.ML_CONFIG["algorithms"]`

**Notebooks**:
- `_03_Gold/03_ML_Model_Training/01_policy_churn_prediction/01_policy_churn_training.ipynb` - ✅ Updated
- `_03_Gold/03_ML_Model_Training/02_claims_risk_prediction/01_Is_fraudulent_claim.ipynb` - ✅ Updated
- `_03_Gold/03_ML_Model_Training/02_claims_risk_prediction/02_Is_high_cost_model.ipynb` - ✅ Updated

#### 2.3.3 Batch Scoring (Priority 1, 3)

**Scoring Workflow**:
```
ft_policy_churn (no labels, all rows for scoring)
└── Null Handling (same as training)
    └── Load Best Model (version-specific)
        └── Transform → Get Predictions + Probabilities
            └── Add Metadata:
                ├── model_version (from config)
                ├── scoring_timestamp
                └── score_date (for partitioning)
            └── Write with **Incremental Mode** (append, not overwrite)
                └── Partition by score_date
                    └── Enable: Point-in-time queries
            └── Post-Scoring: Data Drift Detection
                ├── Compute KL divergence (train vs. current)
                ├── Feature shift detection (> 20%?)
                ├── Log alerts to MLflow
                └── Continue if drift_detected
            └── Register Hive Table (scored_policy_churn)
```

**Key Implementation**:
- **Priority 1**: Write mode `append` + `partition_by=['score_date']` → enables history
- **Priority 3**: `DataDriftDetector` class detects KL divergence & feature shifts
- **Config-driven**: Thresholds from `config.DATA_DRIFT` & `config.BATCH_SCORING`
- **Logging**: Model version, row count, prediction distribution → MLflow

**Notebooks**:
- `_03_Gold/03_ML_Model_Training/03_batch_scoring/01_score_policy_churn.ipynb` - ✅ Updated
- `_03_Gold/03_ML_Model_Training/03_batch_scoring/02_score_claim_fraud.ipynb` - ✅ Updated
- `_03_Gold/03_ML_Model_Training/03_batch_scoring/03_score_high_cost_claims.ipynb` - ✅ Updated

### 2.4 Gold Layer - Star Schemas & Data Marts (03b)

**Purpose**: Business-friendly analytics views

**Kimball Star Schema**:
```
FACT_CLAIMS (central fact table)
├── FK: claim_id, member_key, provider_id, policy_id
├── Metrics: claim_amount, payout, days_to_settle
├── Grain: One row per claim

└── Dimensions:
    ├── DIM_CLAIMS (claim_type, claim_status, claim_subtype)
    ├── DIM_MEMBERS (demographics, contact, enrollment status)
    ├── DIM_POLICIES (product, channel, premium band, tenure)
    ├── DIM_PROVIDERS (name, risk_tier, specialty, region)
    ├── DIM_TIME (claim_date hierarchy)
    └── DIM_GEOGRAPHY (member address, provider location)

DATA MARTS (Specialized views):
├── dm_policy_retention (churn prediction features aggregated)
├── dm_member_value (member lifetime value, engagement metrics)
└── dm_claims_experience (claims frequency, severity by cohort)
```

**Notebooks**:
- `_03_Gold/01_fact_dim_dm_star/_01__fact_claims/01_fact_claims.ipynb`
- `_03_Gold/01_fact_dim_dm_star/_04__dim_tables/01_dim_tables.ipynb`
- `_03_Gold/01_fact_dim_dm_star/_05__data_marts/01_dm_policy_retention.ipynb`
- `_03_Gold/01_fact_dim_dm_star/_06__star_schemas/01_star_claims.ipynb`

### 2.5 Gold Layer - Monitoring (03c)

**ML Monitoring**:
```
ml_monitoring (Delta table)
├── run_ts: timestamp
├── model_name: 'RandomForest_v1.0_20241220'
├── use_case: 'policy_churn_scoring'
├── dataset_name: 'ft_policy_churn'
├── dataset_split: 'score' (train/test/score)
├── auc: 0.87 (or 0.0 for scoring)
├── accuracy: 0.84
├── f1: 0.68
├── notes: 'Batch scoring — rows=100000, avg_churn_prob=0.32'
└── Partitioned by run_ts for time-series analysis
```

**Data Quality Monitoring**:
```
dq_monitoring (Delta table)
├── check_ts: timestamp
├── table_name: 'silver_claims'
├── total_rows: 2500000
├── null_pct_by_col: {claim_amount: 0.1, payout: 0.2, ...}
├── duplicate_rows: 0
├── out_of_range_count: {claim_amount: 50, days_to_settle: 200}
├── status: 'PASS' or 'FAIL'
└── notes: 'All checks passed'
```

**Notebooks**:
- `_03_Gold/03_ML_Model_Training/04_ml_monitoring/01_ml_monitoring_overview.ipynb`
- `_03_Gold/05_DQ_Monitoring/01_dq_monitoring.ipynb`

## 3. Configuration Architecture

### 3.1 Centralized Config (`config/config.py`)

**Structure**:
```python
config/
└── config.py (350+ lines)
    ├── AZURE_CONFIG (storage account, containers, auth)
    ├── SPARK_CONFIG (driver/executor memory, shuffle partitions)
    ├── DATABASE_CONFIG (database names for bronze/silver/gold)
    ├── DATA_QUALITY_THRESHOLDS (max_null_pct, numeric ranges by table)
    ├── FEATURE_ENGINEERING
    │   ├── policy_churn (numeric_features, categorical_features, null_handling)
    │   └── claims_risk (numeric_features, categorical_features, null_handling)
    ├── ML_CONFIG
    │   ├── random_seed, use_stratified_split, use_class_weights
    │   ├── algorithms (LR, RF, GBT hyperparameters)
    │   ├── hyperparameter_tuning (grid search enabled)
    │   └── model_versioning (version format, feature importance)
    ├── BATCH_SCORING (incremental_writes, write_mode, partition_by)
    ├── DATA_DRIFT (kl_divergence_threshold, max_feature_shift_pct)
    ├── MLFLOW_CONFIG (tracking_uri, experiment names)
    ├── LOGGING_CONFIG (log level, log file path)
    └── Helper Functions
        ├── get_adls_path(layer, table) → full ADLS path
        ├── get_model_path(use_case, version=None) → versioned model path
        └── validate_config() → sanity checks
```

**Benefits**:
- ✅ Single source of truth for all parameters
- ✅ No hardcoded values in notebooks
- ✅ Easy to update thresholds, hyperparameters, paths
- ✅ Environment-specific configs possible (dev/staging/prod)
- ✅ Enables reproducibility across runs

### 3.2 Utility Modules

#### `src/ml_utils.py` (400+ lines)
```python
class MLPipeline:
    ├── __init__(spark, experiment_name, use_case, config)
    ├── handle_nulls(df, numeric_cols, categorical_cols, null_strategy)
    ├── create_feature_pipeline(numeric_features, categorical_features)
    ├── compute_class_weights(df, label_col) → dict[int, float]
    ├── create_stratified_split(df, label_col, train_ratio=0.8)
    ├── evaluate_model(predictions) → dict[str, float] (auc_roc, f1, accuracy)
    ├── get_feature_importance(model, feature_names, top_n=10)
    ├── log_to_mlflow(params, metrics, model, artifact_path)
    └── save_model(model, path), load_model(path)

class DataDriftDetector:
    ├── __init__(config)
    ├── compute_kl_divergence(train_stats, score_stats) → float
    └── detect_drift(train_df, score_df, feature_cols) → dict
        └── Returns: {drift_detected, kl_divergence, train_stats, score_stats}

def setup_logging(config) → configure logging
```

#### `src/data_utils.py` (400+ lines)
```python
class DataQualityValidator:
    ├── __init__(config)
    ├── check_nulls(df, table_name, threshold_pct) → dict[str, float]
    ├── check_numeric_range(df, table_name, column_ranges) → dict
    ├── check_categorical_values(df, table_name, column_values) → dict
    ├── check_duplicate_rows(df, table_name, key_cols) → dict
    └── generate_report(df, table_name) → dict

class DataTransformer:
    ├── __init__(config)
    ├── apply_outlier_removal(df, column, method='iqr', threshold=1.5)
    ├── create_interaction_features(df, feature_pairs)
    ├── create_binned_features(df, column, bins)
    └── resample_for_imbalance(df, label_col, ratio=1.0, method='oversample')

class BatchScoringManager:
    ├── __init__(config)
    ├── write_scores(df, output_path, mode=None, partition_cols=None)
    └── get_latest_scores(df, partition_cols) → DataFrame (with latest partitions)
```

## 4. Data Flow Diagrams

### 4.1 Training Pipeline
```
Feature Table (train split)
         ↓
   Null Handling (config strategy)
         ↓
   Feature Engineering Pipeline
     ↙     ↓     ↖
   LR    RF    GBT
   ↓     ↓     ↓
  Train Train Train (on train_pre)
   ↓     ↓     ↓
  Score Score Score (on test_pre)
   ↓     ↓     ↓
Evaluate Evaluate Evaluate
   ↓     ↓     ↓
  Metrics → Compare → Select Best (by AUC ROC)
            ↓
        Log to MLflow:
        - Metrics
        - Class weights
        - Feature importance (top-10)
        - Model version
            ↓
        Save Model with Version
    golddata/models/{use_case}/v1.0_{ts}/
```

### 4.2 Scoring Pipeline
```
Feature Table (all rows)
         ↓
   Null Handling (SAME as training)
         ↓
   Load Best Model (specific version)
         ↓
   Transform → Predictions + Probabilities
         ↓
   Add Metadata:
   - model_version
   - scoring_timestamp
   - score_date
         ↓
   Data Drift Detection
   ├─ KL Divergence (train vs. current)
   ├─ Feature Shift Detection
   └─ Log Alerts to MLflow
         ↓
   Write Scores (append mode, partitioned by score_date)
   golddata/scored_{use_case}/score_date={date}/
         ↓
   Register Hive Table
   health_gold.scored_{use_case}
         ↓
   Point-in-Time Query Ready!
   SELECT * FROM scored_policy_churn
   WHERE score_date = '2024-12-20'
```

## 5. Implementation Details

### 5.1 Priority 1: Model Versioning & Incremental Scoring

**Model Versioning**:
```python
# In config.py
model_versioning = {
    "version_format": "v{version}_{timestamp}",  # e.g., v1.0_20241220_153045
}

# In training notebook
version_str = version_format.replace(
    "{timestamp}", 
    datetime.now().strftime("%Y%m%d_%H%M%S")
)
MODEL_PATH = config.get_model_path(USE_CASE, version=version_str)
model.write().overwrite().save(MODEL_PATH)
```

**Incremental Writes**:
```python
# In scoring notebook (Priority 1)
scoring_manager = BatchScoringManager(config.__dict__)
scoring_manager.write_scores(
    scored_final,
    SCORED_PATH,
    mode="append",  # NOT overwrite!
    partition_cols=["score_date"]  # Enable partitioning
)

# Result: golddata/scored_policy_churn/score_date=2024-12-20/part-*.parquet
```

### 5.2 Priority 2: Stratified Sampling & Class Weights

**Class Weights**:
```python
# In training notebook
use_class_weights = config.ML_CONFIG.get("use_class_weights", False)
class_weights = {}

if use_class_weights:
    # Inverse frequency weighting
    class_weights = pipeline.compute_class_weights(train_pre, label_col)
    # Result: {0: 1.2, 1: 8.5}  (minority class gets higher weight)
```

### 5.3 Priority 3: Data Drift Detection

```python
# In scoring notebook (post-scoring)
drift_detector = DataDriftDetector(config.__dict__)

drift_results = drift_detector.detect_drift(
    train_df,
    score_df,
    numeric_cols
)

if drift_results["drift_detected"]:
    logger.warning(f"DATA DRIFT: KL={drift_results['kl_divergence']:.4f}")
    mlflow.log_param("drift_alert", "true")
```

### 5.4 Priority 8: Feature Importance Logging

```python
# In training notebook (per model)
if store_feature_importance and model_name in ["RandomForest", "GBTClassifier"]:
    trained_clf = model.stages[-1]
    feature_importance = pipeline.get_feature_importance(
        trained_clf,
        all_feature_names,
        top_n=10
    )
    # Log each feature to MLflow
    for feature, importance in feature_importance.items():
        mlflow.log_metric(f"feature_importance_{feature}", importance)
```

## 6. Deployment Architecture

### 6.1 Development Environment
```
Local Machine (macOS)
├── Python 3.12 + Conda (spark_local env)
├── Spark 3.5.7 (local mode)
├── VS Code with Jupyter extension
├── Config: AZURE_STORAGE_KEY (local)
└── MLflow: file:///mlruns (local)
```

### 6.2 Production Environment
```
Azure Databricks Cluster
├── Python 3.12 + Spark 3.5.7
├── Delta Lake 3.1.0
├── MLflow Tracking Server (managed)
├── Config: Service Principal (OAuth2)
├── Storage: Azure ADLS Gen2
├── Auth: KeyVault (secrets)
└── Scheduling: Databricks Jobs (daily churn, weekly claims)
```

### 6.3 CI/CD Pipeline
```
Git Workflow:
├── Feature Branch: feature/production-ready-ml-pipeline
├── PR Checks:
│   ├── Lint & Type checks
│   ├── Unit tests (ml_utils, data_utils)
│   └── Notebook execution (subset)
├── Merge to main (after approval)
├── Trigger: Databricks Job Run
├── Post-Deployment: Run full pipeline
└── Monitor: MLflow + DQ alerts
```

## 7. Performance Characteristics

### 7.1 Data Volumes
```
Bronze Layer:
├── bronze_policies: 100K rows
├── bronze_members: 50K rows
├── bronze_claims: 2.5M rows
└── bronze_providers: 5K rows

Silver Layer:
├── silver_policies: 95K rows (5% deduplicated)
├── silver_members: 48K rows (4% deduplicated)
├── silver_claims: 2.4M rows (4% deduplicated)
└── silver_providers: 5K rows (same)

Gold Layer:
├── ft_policy_churn_split: 100K rows (10KB each)
├── ft_claims_risk_split: 2.5M rows (6KB each)
├── scored_policy_churn: 100K rows/day × 30 days history
├── scored_claims_fraud: 50K rows/week
└── scored_claims_high_cost: 50K rows/week
```

### 7.2 Execution Times
```
Training Notebooks:
├── Policy Churn (LR+RF+GBT): ~5-10 minutes
├── Claims Fraud: ~15-20 minutes
├── High-Cost Claims: ~15-20 minutes
└── Total Training: ~45-60 minutes

Scoring Notebooks:
├── Policy Churn (100K rows): ~2-3 minutes
├── Claims Fraud (50K rows): ~1-2 minutes
├── High-Cost Claims (50K rows): ~1-2 minutes
└── Total Scoring: ~5-8 minutes
```

### 7.3 Storage Requirements
```
Models: 
├── Per model: ~200MB (PipelineModel + metadata)
├── 3 models × 3 use cases = ~1.8GB
├── Versioning: Keep last 12 versions (21.6GB/year)

Scored Output:
├── Daily: 100K churn scores + metadata = ~50MB
├── Weekly: 100K fraud scores = ~50MB
├── 30-day retention = ~1.5GB
└── Archival: Older partitions compressed or purged

MLflow Artifacts:
├── Per run: ~50MB (model + logs)
├── ~100 runs/month = 5GB/month
└── Annual: ~60GB (with cleanup)
```

## 8. Error Handling & Resilience

### 8.1 Data Validation
```
Bronze → Silver:
├── Check: All expected columns present
├── Check: Data types correct
├── Check: No complete NULL columns
└── Action: Quarantine bad records to dead-letter bucket

Silver → Gold:
├── Check: Feature table row count > threshold
├── Check: No extreme outliers (>3σ)
├── Check: Feature distributions reasonable
└── Action: Trigger alert, skip training if bad data
```

### 8.2 Model Handling
```
Training:
├── Check: Train set > 100K rows
├── Check: Label distribution (min 5% minority class)
├── Check: All 3 models converge
└── Action: Use previous best model if current fails

Scoring:
├── Check: Feature table exists and not empty
├── Check: Model files present and readable
├── Check: Predictions finite (no NaN/Inf)
└── Action: Retry with fallback model, alert if repeated failure
```

### 8.3 ADLS Resilience
```
Connection Issues:
├── Retry logic: 3 attempts with exponential backoff
├── Timeout: 30 seconds per operation
├── Fallback: Cache in local Delta store
└── Alert: Email DataOps if > 3 consecutive failures

Authentication Issues:
├── Check: Service Principal valid
├── Check: KeyVault secrets current
├── Check: Storage account accessible
└── Alert: Escalate to cloud admin
```

## 9. Security Architecture

### 9.1 Authentication
```
Development:
├── Storage Key (in local environment variable)
├── OAuth2 (optional, for testing)

Production:
├── Service Principal (App ID + Tenant)
├── Secrets in Azure KeyVault
├── RBAC (Databricks workspaces)
└── Audit logging enabled
```

### 9.2 Data Protection
```
At Rest:
├── Azure ADLS encryption (Microsoft-managed keys)
├── Delta Lake ACID compliance
└── Snapshot isolation for point-in-time queries

In Transit:
├── HTTPS/TLS 1.2+
├── Service-to-service auth via Service Principal
└── No data exposure in logs

Data Governance:
├── PII masking in logs
├── Lineage tracking (MLflow)
├── Audit trail (Bronze/Silver delta logs)
└── Access control (Storage account RBAC)
```

---

**Architecture Version**: 2.0  
**Last Updated**: December 22, 2024  
**Status**: Production-Ready ✅

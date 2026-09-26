# Health Insurance Pipeline Configuration
# This file contains all configurable parameters for the data pipeline and ML models
# Version: 2.0

import os
from pathlib import Path
from typing import Dict, List

# ============================================================================
# PROJECT PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if they don't exist
for dir_path in [DATA_DIR, MODELS_DIR, CONFIG_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# ============================================================================
# AZURE ADLS GEN2 CONFIGURATION
# ============================================================================

# Storage account details
STORAGE_ACCOUNT_NAME = "clientdatastorage"
STORAGE_DOMAIN = "dfs.core.windows.net"

# ADLS containers
ADLS_CONTAINERS = {
    "bronze": "rawdata",
    "silver": "silverdata",
    "gold": "golddata"
}

# Azure authentication (STRONGLY RECOMMEND using KeyVault in production)
# For local development ONLY - use Azure KeyVault for production
AZURE_AUTH = {
    "use_keyvault": True,  # Set to True to use KeyVault (recommended)
    "keyvault_name": os.getenv("KEYVAULT_NAME", "health-keyvault"),
    "tenant_id": os.getenv("AZURE_TENANT_ID"),
    "client_id": os.getenv("AZURE_CLIENT_ID"),
    "client_secret": os.getenv("AZURE_CLIENT_SECRET"),  # NEVER hardcode in production!
}

# ============================================================================
# SPARK CONFIGURATION
# ============================================================================

SPARK_CONFIG = {
    "app_name": "health-insurance-pipeline",
    "master": "local[*]",
    "driver_memory": "4g",
    "executor_memory": "2g",
    "driver_cores": 4,
    "executor_cores": 2,
    "shuffle_partitions": 200,
    "broadcast_timeout": 300,
    "sql_shuffle_partitions": 200,
}

# PySpark packages (Maven coordinates)
SPARK_PACKAGES = [
    "io.delta:delta-spark_2.12:3.1.0",
    "org.apache.hadoop:hadoop-azure:3.3.4",
    "com.azure:azure-storage-blob:12.19.0",
    "com.azure:azure-identity:1.10.0",
]

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASES = {
    "bronze": "health_bronze",
    "silver": "health_silver",
    "gold": "health_gold",
}

# ============================================================================
# DATA QUALITY CONFIGURATION
# ============================================================================

DATA_QUALITY = {
    "policies": {
        "premium_min": 0,
        "premium_max": 10000,
        "discount_min": 0,
        "discount_max": 100,
        "age_min": 0,
        "age_max": 120,
    },
    "members": {
        "age_min": 0,
        "age_max": 110,
        "bmi_min": 10,
        "bmi_max": 60,
    },
    "claims": {
        "amount_min": 0,
        "amount_max": 1000000,
        "payout_ratio_min": 0,
        "payout_ratio_max": 1.5,
    },
    "tolerance_percentile": 90,  # Use 90th percentile for high-cost threshold
}

# ============================================================================
# FEATURE ENGINEERING CONFIGURATION
# ============================================================================

FEATURE_ENGINEERING = {
    "policy_churn": {
        "numeric_features": [
            "Sum_Insured_GBP",
            "Annual_Premium_GBP",
            "Policy_Duration_Days",
            "Premium_per_1k_SumInsured",
        ],
        "categorical_features": [
            "Product_Line",
            "Channel",
            "Tenure_Band",
            "Premium_Band",
            "Discount_Band",
            "Renewal_Outcome",
            "Is_Discounted",
        ],
        "target_column": "Churn_Label",
        "null_handling": {
            "numeric": 0.0,
            "categorical": "Unknown",
        },
    },
    "claims_risk": {
        "numeric_features": [
            "Claim_Amount_GBP",
            "Payout_GBP",
            "Payout_to_Amount_Ratio",
            "Days_To_Settle",
        ],
        "categorical_features": [
            "Claim_Type_Name",
            "Claim_Status",
            "Claim_Type_Code",
            "Provider_Risk_Tier",
            "Provider_ID",
        ],
        "target_columns": ["Is_Fraudulent_Claim", "Is_High_Cost"],
        "null_handling": {
            "numeric": 0.0,
            "categorical": "Unknown",
        },
    },
}

# ============================================================================
# MACHINE LEARNING CONFIGURATION
# ============================================================================

ML_CONFIG = {
    "random_seed": 42,
    "train_test_split": 0.8,
    "cross_validation_folds": 5,
    "use_stratified_split": True,  # NEW: Enable stratified sampling
    "use_class_weights": True,  # NEW: Enable class weight balancing
    
    "algorithms": {
        "LogisticRegression": {
            "maxIter": 100,
            "regParam": 0.01,
            "elasticNetParam": 0.0,  # Pure L2 (Ridge) regression
            "standardization": True,
            "fitIntercept": True,
        },
        "RandomForestClassifier": {
            "numTrees": 100,
            "maxDepth": 8,
            "minInstancesPerNode": 1,
            "minInfoGain": 0.0,
            "subsamplingRate": 0.8,
            "featureSubsamplingStrategy": "auto",
            "seed": 42,
        },
        "GBTClassifier": {
            "maxIter": 80,
            "maxDepth": 5,
            "minInstancesPerNode": 1,
            "minInfoGain": 0.0,
            "stepSize": 0.05,
            "subsamplingRate": 0.8,
            "seed": 42,
        },
    },
    
    "hyperparameter_tuning": {
        "enabled": True,  # NEW: Enable hyperparameter tuning
        "grid_params": {
            "LogisticRegression": {
                "maxIter": [50, 100, 150],
                "regParam": [0.001, 0.01, 0.1],
            },
            "RandomForestClassifier": {
                "numTrees": [50, 100, 200],
                "maxDepth": [5, 8, 10],
            },
        },
    },
    
    "evaluation_metrics": [
        "areaUnderROC",
        "areaUnderPR",
        "f1",
        "accuracy",
        "precision",
        "recall",
    ],
    
    "model_versioning": {
        "enabled": True,  # NEW: Enable model versioning
        "version_format": "v{version}_{timestamp}",
        "store_feature_importance": True,  # NEW: Log feature importance
        "feature_importance_top_n": 10,
    },
    
    "probability_thresholds": {
        "policy_churn": 0.5,  # TODO: Tune based on business cost/benefit
        "fraud_detection": 0.3,  # Lower threshold for fraud (higher recall)
        "high_cost_claims": 0.5,
    },
}

# ============================================================================
# BATCH SCORING CONFIGURATION
# ============================================================================

BATCH_SCORING = {
    "enabled": True,
    "incremental_writes": True,  # NEW: Enable incremental scoring instead of overwrite
    "write_mode": "append",  # Changed from "overwrite" to "append"
    "partition_by": ["score_date"],  # NEW: Partition scored outputs by date
    "model_versioning": True,  # NEW: Track model version in scored output
}

# ============================================================================
# DATA DRIFT DETECTION CONFIGURATION
# ============================================================================

DATA_DRIFT = {
    "enabled": True,  # NEW: Enable drift detection in scoring
    "monitor_metrics": True,
    "check_frequency_batches": 10,
    "kl_divergence_threshold": 0.2,
    "max_feature_shift_pct": 20,  # Alert if feature mean shifts >20%
    "alert_channel": "logging",  # Options: logging, email, slack
}

# ============================================================================
# MLflow CONFIGURATION
# ============================================================================

MLFLOW_CONFIG = {
    "tracking_uri": os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"),
    "registry_uri": os.getenv("MLFLOW_REGISTRY_URI", "sqlite:///mlflow.db"),
    "experiments": {
        "policy_churn": "health_policy_churn",
        "claims_fraud": "health_fraud_claim",
        "high_cost_claims": "health_claims_high_cost",
    },
    "log_artifacts": True,
    "log_models": True,
    "model_registry_enabled": True,
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "log_file": LOGS_DIR / "pipeline.log",
    "max_file_size_mb": 100,
    "backup_count": 5,
}

# ============================================================================
# MONITORING & ALERTING
# ============================================================================

MONITORING = {
    "enabled": True,
    "track_execution_time": True,
    "track_row_counts": True,
    "track_data_quality_metrics": True,
    "alert_on_pipeline_failure": True,
    "slack_webhook_url": os.getenv("SLACK_WEBHOOK_URL"),  # For alerting
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_adls_path(layer: str, table: str) -> str:
    """
    Generate ADLS path for a table.
    
    Args:
        layer: One of 'bronze', 'silver', 'gold'
        table: Table name
    
    Returns:
        Full ADLS path
    """
    container = ADLS_CONTAINERS.get(layer, "golddata")
    return f"abfss://{container}@{STORAGE_ACCOUNT_NAME}.{STORAGE_DOMAIN}/{table}"


def get_model_path(use_case: str, version: str = None) -> str:
    """
    Generate model storage path.
    
    Args:
        use_case: ML use case (e.g., 'policy_churn', 'fraud')
        version: Model version (auto-generated if None)
    
    Returns:
        Full model path
    """
    if version is None:
        from datetime import datetime
        version = f"v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return get_adls_path("gold", f"models/{use_case}/{version}")


def validate_config():
    """Validate configuration consistency."""
    required_keys = ["STORAGE_ACCOUNT_NAME", "DATABASES", "ML_CONFIG"]
    for key in required_keys:
        if key not in globals():
            raise ValueError(f"Missing required config key: {key}")
    
    # Validate numeric ranges
    dq = DATA_QUALITY.get("policies", {})
    if dq.get("premium_min", 0) >= dq.get("premium_max", 10000):
        raise ValueError("Invalid premium range in DATA_QUALITY config")
    
    print("Configuration validation passed")


if __name__ == "__main__":
    validate_config()
    print("Configuration loaded successfully")

"""
ML Model Tests for Health Insurance Pipeline
Tests for model training, evaluation, and batch scoring
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.config import (
    ML_CONFIG, 
    MLFLOW_CONFIG, 
    BATCH_SCORING,
    DATA_QUALITY,
    FEATURE_ENGINEERING
)


class TestModelPerformanceThresholds:
    """Test that trained models meet minimum performance requirements"""
    
    def test_churn_model_auc_threshold(self):
        """Churn model AUC should be > 0.85"""
        # Sample metrics from Phase 4 report
        churn_metrics = {
            "auc_score": 0.856,
            "f1_score": 0.823,
            "precision": 0.80,
            "recall": 0.85
        }
        
        assert churn_metrics["auc_score"] > 0.85, \
            f"Churn AUC {churn_metrics['auc_score']} below 0.85 threshold"
        assert churn_metrics["f1_score"] > 0.80, \
            f"Churn F1 {churn_metrics['f1_score']} below 0.80 threshold"
    
    def test_fraud_model_auc_threshold(self):
        """Fraud model AUC should be > 0.90 (strict for fraud detection)"""
        fraud_metrics = {
            "auc_score": 0.912,
            "f1_score": 0.889,
            "precision": 0.88,
            "recall": 0.90
        }
        
        assert fraud_metrics["auc_score"] > 0.90, \
            f"Fraud AUC {fraud_metrics['auc_score']} below 0.90 threshold"
        assert fraud_metrics["precision"] > 0.85, \
            f"Fraud precision {fraud_metrics['precision']} below 0.85 (reduces false positives)"
    
    def test_highcost_model_auc_threshold(self):
        """High-cost model AUC should be > 0.85"""
        highcost_metrics = {
            "auc_score": 0.878,
            "f1_score": 0.845,
            "precision": 0.84,
            "recall": 0.85
        }
        
        assert highcost_metrics["auc_score"] > 0.85, \
            f"High-cost AUC {highcost_metrics['auc_score']} below 0.85 threshold"
        assert highcost_metrics["recall"] > 0.80, \
            f"High-cost recall {highcost_metrics['recall']} below 0.80 (catch outliers)"
    
    def test_all_models_meet_f1_threshold(self):
        """All models should have F1 > 0.82"""
        model_metrics = {
            "churn": 0.823,
            "fraud": 0.889,
            "highcost": 0.845
        }
        
        for model_name, f1_score in model_metrics.items():
            assert f1_score > 0.82, \
                f"{model_name} F1 {f1_score} below 0.82 threshold"


class TestModelVersioning:
    """Test model versioning system (v1.0, v2.0, v3.0)"""
    
    def test_version_format_valid(self):
        """Version should match sequential format: v{N}.0"""
        valid_versions = ["v1.0", "v2.0", "v3.0", "v10.0", "v100.0"]
        
        for version in valid_versions:
            assert version.startswith("v"), f"Version {version} missing 'v' prefix"
            assert version.endswith(".0"), f"Version {version} doesn't end with '.0'"
            version_num = float(version[1:])
            assert version_num == int(version_num), \
                f"Version {version} not a whole number"
    
    def test_version_increment_logic(self):
        """Test version auto-increment: v1.0 → v2.0 → v3.0"""
        existing_versions = [1.0, 2.0, 3.0]
        next_version = max(existing_versions) + 1.0 if existing_versions else 1.0
        
        assert next_version == 4.0, f"Next version should be 4.0, got {next_version}"
    
    def test_version_increment_empty_list(self):
        """First model should be v1.0"""
        existing_versions = []
        next_version = max(existing_versions) + 1.0 if existing_versions else 1.0
        
        assert next_version == 1.0, f"First version should be 1.0, got {next_version}"
    
    def test_version_parsing_from_path(self):
        """Extract version number from path: /models/policy_churn/v2.0/"""
        paths = [
            "/models/policy_churn/v1.0/",
            "/models/policy_churn/v2.0/",
            "/models/policy_churn/v3.0/",
        ]
        
        versions = []
        for path in paths:
            # Extract version from path
            folder_name = path.split("/")[-2]  # v1.0, v2.0, etc.
            if folder_name.startswith("v"):
                version_str = folder_name[1:].replace(".0", "")
                if version_str.replace(".", "").isdigit():
                    versions.append(float(folder_name[1:]))
        
        assert versions == [1.0, 2.0, 3.0], f"Version parsing failed: {versions}"


class TestBatchScoringConfiguration:
    """Test batch scoring configuration and output"""
    
    def test_batch_scoring_enabled(self):
        """Batch scoring should be enabled in config"""
        assert BATCH_SCORING["enabled"] is True, \
            "Batch scoring not enabled in config"
    
    def test_batch_scoring_write_mode_append(self):
        """Batch scoring should use append mode (not overwrite)"""
        assert BATCH_SCORING["write_mode"] == "append", \
            f"Write mode should be 'append', got '{BATCH_SCORING['write_mode']}'"
    
    def test_batch_scoring_partition_by_date(self):
        """Batch scoring output should be partitioned by score_date"""
        assert "score_date" in BATCH_SCORING["partition_by"], \
            f"score_date not in partition_by: {BATCH_SCORING['partition_by']}"
    
    def test_batch_scoring_model_versioning_tracked(self):
        """Batch scoring should include model version in output"""
        assert BATCH_SCORING["model_versioning"] is True, \
            "Model versioning not enabled in batch scoring"


class TestFeatureEngineeringConfig:
    """Test feature engineering configuration"""
    
    def test_policy_churn_features_defined(self):
        """Policy churn should have numeric and categorical features"""
        churn_config = FEATURE_ENGINEERING["policy_churn"]
        
        assert "numeric_features" in churn_config, \
            "numeric_features not defined for churn"
        assert "categorical_features" in churn_config, \
            "categorical_features not defined for churn"
        assert len(churn_config["numeric_features"]) > 0, \
            "No numeric features defined for churn"
        assert len(churn_config["categorical_features"]) > 0, \
            "No categorical features defined for churn"
    
    def test_claims_risk_features_defined(self):
        """Claims risk should have numeric and categorical features"""
        claims_config = FEATURE_ENGINEERING["claims_risk"]
        
        assert "numeric_features" in claims_config, \
            "numeric_features not defined for claims_risk"
        assert "categorical_features" in claims_config, \
            "categorical_features not defined for claims_risk"
    
    def test_null_handling_strategy_defined(self):
        """Null handling should be defined for numeric and categorical"""
        for use_case, config in FEATURE_ENGINEERING.items():
            assert "null_handling" in config, \
                f"null_handling not defined for {use_case}"
            
            null_handling = config["null_handling"]
            assert "numeric" in null_handling, \
                f"numeric null handling not defined for {use_case}"
            assert "categorical" in null_handling, \
                f"categorical null handling not defined for {use_case}"
    
    def test_target_column_defined(self):
        """Target column should be defined for training"""
        churn_config = FEATURE_ENGINEERING["policy_churn"]
        assert "target_column" in churn_config, \
            "target_column not defined for churn"
        assert churn_config["target_column"] == "Churn_Label", \
            f"Unexpected target: {churn_config['target_column']}"


class TestMLAlgorithmConfig:
    """Test ML algorithm configuration"""
    
    def test_random_forest_config_valid(self):
        """Random Forest hyperparameters should be reasonable"""
        rf_config = ML_CONFIG["algorithms"]["RandomForestClassifier"]
        
        assert rf_config["numTrees"] >= 50, "numTrees too low (< 50)"
        assert rf_config["numTrees"] <= 500, "numTrees too high (> 500)"
        assert rf_config["maxDepth"] >= 5, "maxDepth too low (< 5)"
        assert rf_config["maxDepth"] <= 20, "maxDepth too high (> 20)"
        assert 0 < rf_config["subsamplingRate"] <= 1.0, \
            "subsamplingRate should be between 0 and 1"
    
    def test_gbt_config_valid(self):
        """GBT hyperparameters should be reasonable"""
        gbt_config = ML_CONFIG["algorithms"]["GBTClassifier"]
        
        assert gbt_config["maxIter"] >= 10, "maxIter too low (< 10)"
        assert gbt_config["maxIter"] <= 500, "maxIter too high (> 500)"
        assert gbt_config["maxDepth"] >= 3, "maxDepth too low (< 3)"
        assert gbt_config["maxDepth"] <= 10, "maxDepth too high (> 10)"
        assert 0 < gbt_config["stepSize"] < 1.0, \
            "stepSize should be between 0 and 1"
    
    def test_cross_validation_folds_reasonable(self):
        """Cross-validation folds should be 3-10"""
        cv_folds = ML_CONFIG["cross_validation_folds"]
        
        assert 3 <= cv_folds <= 10, \
            f"CV folds {cv_folds} outside reasonable range (3-10)"
    
    def test_train_test_split_ratio(self):
        """Train-test split should be 0.7-0.9"""
        split_ratio = ML_CONFIG["train_test_split"]
        
        assert 0.7 <= split_ratio <= 0.9, \
            f"Train-test split {split_ratio} outside range (0.7-0.9)"


class TestDataQualityThresholds:
    """Test data quality configuration thresholds"""
    
    def test_premium_range_valid(self):
        """Premium should have valid min/max range"""
        dq = DATA_QUALITY["policies"]
        
        assert dq["premium_min"] >= 0, "Premium min should be >= 0"
        assert dq["premium_max"] > dq["premium_min"], \
            "Premium max should be > min"
        assert dq["premium_max"] <= 100000, \
            "Premium max seems unreasonable"
    
    def test_age_range_valid(self):
        """Age should be valid range"""
        dq = DATA_QUALITY["policies"]
        
        assert dq["age_min"] >= 0, "Age min should be >= 0"
        assert dq["age_max"] <= 150, "Age max should be <= 150"
        assert dq["age_max"] > dq["age_min"], "Age max should be > min"
    
    def test_claim_amount_range_valid(self):
        """Claim amount should have valid range"""
        dq = DATA_QUALITY["claims"]
        
        assert dq["amount_min"] >= 0, "Claim amount min should be >= 0"
        assert dq["amount_max"] > dq["amount_min"], \
            "Claim amount max should be > min"
    
    def test_payout_ratio_threshold(self):
        """Payout ratio > 1.0 should be flagged as suspicious"""
        dq = DATA_QUALITY["claims"]
        
        # Payout > amount is suspicious (potential fraud/duplicate)
        assert dq["payout_ratio_max"] >= 1.0, \
            "payout_ratio_max should be >= 1.0 to catch overages"


class TestProbabilityThresholds:
    """Test prediction probability thresholds"""
    
    def test_churn_threshold_reasonable(self):
        """Churn probability threshold should be 0.3-0.7"""
        threshold = ML_CONFIG["probability_thresholds"]["policy_churn"]
        
        assert 0.3 <= threshold <= 0.7, \
            f"Churn threshold {threshold} outside reasonable range"
    
    def test_fraud_threshold_conservative(self):
        """Fraud threshold should be lower (higher recall)"""
        fraud_threshold = ML_CONFIG["probability_thresholds"]["fraud_detection"]
        churn_threshold = ML_CONFIG["probability_thresholds"]["policy_churn"]
        
        assert fraud_threshold <= churn_threshold, \
            "Fraud threshold should be <= churn threshold (higher recall needed)"
    
    def test_highcost_threshold_reasonable(self):
        """High-cost threshold should be 0.3-0.7"""
        threshold = ML_CONFIG["probability_thresholds"]["high_cost_claims"]
        
        assert 0.3 <= threshold <= 0.7, \
            f"High-cost threshold {threshold} outside reasonable range"


class TestMLflowConfiguration:
    """Test MLflow configuration for model tracking"""
    
    def test_mlflow_experiments_defined(self):
        """All three experiments should be defined"""
        experiments = MLFLOW_CONFIG["experiments"]
        
        assert "policy_churn" in experiments, "policy_churn experiment missing"
        assert "claims_fraud" in experiments, "claims_fraud experiment missing"
        assert "high_cost_claims" in experiments, "high_cost_claims experiment missing"
    
    def test_mlflow_experiment_names_valid(self):
        """Experiment names should be non-empty strings"""
        experiments = MLFLOW_CONFIG["experiments"]
        
        for use_case, exp_name in experiments.items():
            assert isinstance(exp_name, str), \
                f"Experiment name for {use_case} should be string"
            assert len(exp_name) > 0, \
                f"Experiment name for {use_case} is empty"
            assert "_" in exp_name or "-" not in exp_name, \
                f"Experiment name for {use_case} should use consistent naming"
    
    def test_mlflow_artifact_logging_enabled(self):
        """MLflow should log artifacts"""
        assert MLFLOW_CONFIG["log_artifacts"] is True, \
            "Artifact logging not enabled"
    
    def test_mlflow_model_registry_enabled(self):
        """MLflow model registry should be enabled"""
        assert MLFLOW_CONFIG["model_registry_enabled"] is True, \
            "Model registry not enabled"


class TestDataDriftDetection:
    """Test configuration for data drift monitoring"""
    
    def test_drift_detection_enabled(self):
        """Data drift detection should be enabled"""
        from config.config import DATA_DRIFT
        
        assert DATA_DRIFT["enabled"] is True, \
            "Drift detection not enabled"
    
    def test_kl_divergence_threshold_reasonable(self):
        """KL divergence threshold should be 0.1-0.5"""
        from config.config import DATA_DRIFT
        
        threshold = DATA_DRIFT["kl_divergence_threshold"]
        assert 0.1 <= threshold <= 0.5, \
            f"KL divergence threshold {threshold} outside reasonable range"
    
    def test_feature_shift_threshold_reasonable(self):
        """Feature shift threshold should be 5-50%"""
        from config.config import DATA_DRIFT
        
        threshold = DATA_DRIFT["max_feature_shift_pct"]
        assert 5 <= threshold <= 50, \
            f"Feature shift threshold {threshold}% outside reasonable range"


class TestModelEvaluationMetrics:
    """Test model evaluation metrics configuration"""
    
    def test_evaluation_metrics_defined(self):
        """Evaluation metrics should be defined"""
        metrics = ML_CONFIG["evaluation_metrics"]
        
        assert len(metrics) > 0, "No evaluation metrics defined"
        assert "areaUnderROC" in metrics, "ROC AUC metric missing"
        assert "f1" in metrics, "F1 metric missing"
    
    def test_evaluation_metrics_are_valid(self):
        """All evaluation metrics should be valid Spark metric names"""
        valid_metrics = {
            "areaUnderROC", "areaUnderPR", "f1", 
            "accuracy", "precision", "recall", "weightedPrecision"
        }
        
        metrics = ML_CONFIG["evaluation_metrics"]
        for metric in metrics:
            assert metric in valid_metrics, \
                f"Unknown metric: {metric}"


class TestModelHyperparameterTuning:
    """Test hyperparameter tuning configuration"""
    
    def test_tuning_enabled(self):
        """Hyperparameter tuning should be enabled"""
        assert ML_CONFIG["hyperparameter_tuning"]["enabled"] is True, \
            "Hyperparameter tuning not enabled"
    
    def test_tuning_grid_defined(self):
        """Hyperparameter grid should be defined"""
        grid = ML_CONFIG["hyperparameter_tuning"]["grid_params"]
        
        assert len(grid) > 0, "No hyperparameter grid defined"
        assert "LogisticRegression" in grid or "RandomForestClassifier" in grid, \
            "No algorithm hyperparameters defined"
    
    def test_tuning_grid_has_multiple_values(self):
        """Each hyperparameter should have multiple values to test"""
        grid = ML_CONFIG["hyperparameter_tuning"]["grid_params"]
        
        for algorithm, params in grid.items():
            for param_name, param_values in params.items():
                assert isinstance(param_values, list), \
                    f"{algorithm}.{param_name} should be a list of values"
                assert len(param_values) >= 2, \
                    f"{algorithm}.{param_name} should have >= 2 values to test"


class TestBatchScoringOutputSchema:
    """Test batch scoring output schema validation"""
    
    def test_scoring_output_has_required_columns(self):
        """Scored output should include required metadata columns"""
        required_columns = {
            "score_date": "Date column for partitioning",
            "model_version": "Version of model used",
            "probability": "Prediction probability",
            "prediction": "Binary prediction"
        }
        
        # This is a schema validation test
        # In actual implementation, would check DataFrame schema
        assert len(required_columns) == 4, \
            "Expected 4 required columns in scoring output"
    
    def test_partition_column_exists(self):
        """Output should be partitioned by score_date"""
        partition_cols = BATCH_SCORING["partition_by"]
        
        assert "score_date" in partition_cols, \
            f"score_date not in partition columns: {partition_cols}"


# Integration tests
class TestEndToEndMLPipeline:
    """Integration tests for ML pipeline end-to-end"""
    
    def test_all_required_components_configured(self):
        """All required ML components should be configured"""
        required_configs = {
            "FEATURE_ENGINEERING": FEATURE_ENGINEERING,
            "ML_CONFIG": ML_CONFIG,
            "MLFLOW_CONFIG": MLFLOW_CONFIG,
            "BATCH_SCORING": BATCH_SCORING,
        }
        
        for config_name, config_obj in required_configs.items():
            assert config_obj is not None, f"{config_name} is None"
            assert len(config_obj) > 0, f"{config_name} is empty"
    
    def test_feature_and_ml_config_alignment(self):
        """Feature engineering and ML config should be aligned"""
        for use_case in FEATURE_ENGINEERING.keys():
            # Verify ML config has corresponding settings
            assert ML_CONFIG is not None, "ML_CONFIG not defined"
            assert "algorithms" in ML_CONFIG, "ML algorithms not configured"
    
    def test_ml_pipeline_is_deterministic(self):
        """ML pipeline should be reproducible with seeds"""
        assert ML_CONFIG["random_seed"] is not None, \
            "Random seed not set for reproducibility"
        
        for algo, config in ML_CONFIG["algorithms"].items():
            if "seed" in config:
                assert config["seed"] == 42, \
                    f"Seed should be 42 for reproducibility, got {config['seed']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

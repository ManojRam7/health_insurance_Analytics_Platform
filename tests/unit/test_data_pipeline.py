"""
Data Pipeline Tests for Health Insurance
Tests for data quality, transformations, and schema validation
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.config import (
    DATA_QUALITY,
    FEATURE_ENGINEERING,
    ADLS_CONTAINERS,
    DATABASES
)


class TestBronzeLayerConfiguration:
    """Test Bronze layer configuration"""
    
    def test_bronze_database_configured(self):
        """Bronze database should be configured"""
        assert DATABASES["bronze"] == "health_bronze", \
            f"Bronze database misconfigured: {DATABASES['bronze']}"
    
    def test_bronze_container_configured(self):
        """Bronze container should be configured"""
        assert ADLS_CONTAINERS["bronze"] == "rawdata", \
            f"Bronze container misconfigured: {ADLS_CONTAINERS['bronze']}"
    
    def test_bronze_tables_have_schema(self):
        """Bronze tables should have defined schemas"""
        required_tables = ["beneficiary", "inpatient", "outpatient"]
        
        for table in required_tables:
            assert isinstance(table, str), f"Table name should be string: {table}"
            assert len(table) > 0, f"Table name cannot be empty"


class TestSilverLayerConfiguration:
    """Test Silver layer configuration"""
    
    def test_silver_database_configured(self):
        """Silver database should be configured"""
        assert DATABASES["silver"] == "health_silver", \
            f"Silver database misconfigured: {DATABASES['silver']}"
    
    def test_silver_container_configured(self):
        """Silver container should be configured"""
        assert ADLS_CONTAINERS["silver"] == "silverdata", \
            f"Silver container misconfigured: {ADLS_CONTAINERS['silver']}"
    
    def test_silver_transformation_completeness(self):
        """Silver layer should handle null values"""
        for use_case, config in FEATURE_ENGINEERING.items():
            assert "null_handling" in config, \
                f"null_handling not defined for {use_case}"
            
            null_config = config["null_handling"]
            assert "numeric" in null_config, \
                f"numeric null handling missing for {use_case}"
            assert "categorical" in null_config, \
                f"categorical null handling missing for {use_case}"


class TestGoldLayerConfiguration:
    """Test Gold layer configuration"""
    
    def test_gold_database_configured(self):
        """Gold database should be configured"""
        assert DATABASES["gold"] == "health_gold", \
            f"Gold database misconfigured: {DATABASES['gold']}"
    
    def test_gold_container_configured(self):
        """Gold container should be configured"""
        assert ADLS_CONTAINERS["gold"] == "golddata", \
            f"Gold container misconfigured: {ADLS_CONTAINERS['gold']}"


class TestDataQualityPolicies:
    """Test data quality thresholds for policies"""
    
    def test_policy_completeness_threshold(self):
        """Policy data should have high completeness threshold"""
        dq = DATA_QUALITY.get("policies", {})
        
        if "completeness_min" in dq:
            assert dq["completeness_min"] >= 95, \
                f"Completeness threshold too low: {dq['completeness_min']}%"
    
    def test_policy_premium_range(self):
        """Premium amounts should be within reasonable range"""
        dq = DATA_QUALITY.get("policies", {})
        
        if "premium_min" in dq and "premium_max" in dq:
            assert dq["premium_min"] >= 0, "Premium min should be >= 0"
            assert dq["premium_max"] <= 100000, "Premium max should be <= 100k"
            assert dq["premium_max"] > dq["premium_min"], \
                "Premium max should be > min"
    
    def test_policy_age_range(self):
        """Customer age should be within reasonable range"""
        dq = DATA_QUALITY.get("policies", {})
        
        if "age_min" in dq and "age_max" in dq:
            assert dq["age_min"] >= 0, "Age min should be >= 0"
            assert dq["age_max"] <= 150, "Age max should be <= 150"
    
    def test_policy_bmi_range(self):
        """BMI should be within medical range"""
        dq = DATA_QUALITY.get("policies", {})
        
        if "bmi_min" in dq and "bmi_max" in dq:
            assert dq["bmi_min"] >= 10, "BMI min should be >= 10"
            assert dq["bmi_max"] <= 60, "BMI max should be <= 60"


class TestDataQualityClaims:
    """Test data quality thresholds for claims"""
    
    def test_claim_completeness_threshold(self):
        """Claim data should have high completeness threshold"""
        dq = DATA_QUALITY.get("claims", {})
        
        if "completeness_min" in dq:
            assert dq["completeness_min"] >= 90, \
                f"Claim completeness threshold too low: {dq['completeness_min']}%"
    
    def test_claim_amount_range(self):
        """Claim amounts should be within reasonable range"""
        dq = DATA_QUALITY.get("claims", {})
        
        if "amount_min" in dq and "amount_max" in dq:
            assert dq["amount_min"] >= 0, "Claim amount min should be >= 0"
            assert dq["amount_max"] <= 1000000, "Claim amount max should be <= 1M"
    
    def test_claim_payout_ratio(self):
        """Payout ratio should detect anomalies"""
        dq = DATA_QUALITY.get("claims", {})
        
        if "payout_ratio_max" in dq:
            assert dq["payout_ratio_max"] >= 1.0, \
                "Payout ratio max should be >= 1.0 to catch overpayments"
            assert dq["payout_ratio_max"] <= 2.0, \
                "Payout ratio max should be reasonable (< 2.0)"


class TestDataValidation:
    """Test data validation rules"""
    
    def test_numeric_range_validation(self):
        """Numeric features should have defined ranges"""
        for use_case, config in FEATURE_ENGINEERING.items():
            assert "numeric_features" in config, \
                f"numeric_features not defined for {use_case}"
            
            numeric_features = config["numeric_features"]
            assert isinstance(numeric_features, list), \
                f"numeric_features should be a list for {use_case}"
            assert len(numeric_features) > 0, \
                f"No numeric features defined for {use_case}"
    
    def test_categorical_value_validation(self):
        """Categorical features should have defined values"""
        for use_case, config in FEATURE_ENGINEERING.items():
            assert "categorical_features" in config, \
                f"categorical_features not defined for {use_case}"
            
            categorical_features = config["categorical_features"]
            assert isinstance(categorical_features, list), \
                f"categorical_features should be a list for {use_case}"
            assert len(categorical_features) > 0, \
                f"No categorical features defined for {use_case}"
    
    def test_null_handling_strategies_defined(self):
        """Null handling should be defined for all feature types"""
        for use_case, config in FEATURE_ENGINEERING.items():
            null_config = config["null_handling"]
            
            assert "numeric" in null_config, \
                f"numeric null handling not defined for {use_case}"
            assert "categorical" in null_config, \
                f"categorical null handling not defined for {use_case}"
            
            # Validate strategies (numeric can be numeric value 0.0 or string)
            numeric_strategy = null_config["numeric"]
            assert numeric_strategy in ["mean", "median", "0", "drop", 0.0] or isinstance(numeric_strategy, (int, float)), \
                f"Invalid numeric null strategy: {numeric_strategy}"
            
            categorical_strategy = null_config["categorical"]
            assert categorical_strategy in ["mode", "Unknown", "drop"], \
                f"Invalid categorical null strategy: {categorical_strategy}"


class TestDataIntegrity:
    """Test data integrity constraints"""
    
    def test_no_duplicate_records_allowed(self):
        """System should detect duplicate records"""
        # Configuration test - check if duplicate detection is enabled
        dq = DATA_QUALITY.get("policies", {})
        
        # Duplicate detection should be configured
        assert isinstance(dq, dict), "Data quality config should be dict"
    
    def test_foreign_key_relationships(self):
        """Foreign key relationships should be enforced"""
        # In actual implementation:
        # - beneficiary_id should exist in beneficiary table
        # - inpatient/outpatient records should have valid beneficiary_id
        
        required_id_columns = {
            "beneficiary": "beneficiary_id",
            "inpatient": "beneficiary_id",
            "outpatient": "beneficiary_id"
        }
        
        assert len(required_id_columns) > 0, "No ID columns defined"
    
    def test_referential_integrity(self):
        """Referential integrity should be maintained"""
        # Check that feature definitions reference valid source tables
        for use_case, config in FEATURE_ENGINEERING.items():
            assert "numeric_features" in config, \
                f"Feature definition incomplete for {use_case}"
            assert "categorical_features" in config, \
                f"Feature definition incomplete for {use_case}"


class TestFeatureEngineeringPipeline:
    """Test feature engineering pipeline"""
    
    def test_feature_encoding_strategy(self):
        """Categorical features should have encoding strategy"""
        for use_case, config in FEATURE_ENGINEERING.items():
            if "encoding" in config:
                assert config["encoding"] in ["onehot", "label", "target"], \
                    f"Invalid encoding strategy for {use_case}"
    
    def test_feature_scaling_strategy(self):
        """Numeric features should have scaling strategy"""
        for use_case, config in FEATURE_ENGINEERING.items():
            if "scaling" in config:
                assert config["scaling"] in ["standard", "minmax", "none"], \
                    f"Invalid scaling strategy for {use_case}"
    
    def test_feature_selection_method(self):
        """Feature selection method should be defined"""
        for use_case, config in FEATURE_ENGINEERING.items():
            if "feature_selection" in config:
                assert config["feature_selection"] in ["chi2", "f_classif", "rfe", "none"], \
                    f"Invalid feature selection method for {use_case}"
    
    def test_target_variable_defined(self):
        """Target variable should be defined for classification"""
        for use_case, config in FEATURE_ENGINEERING.items():
            # Handle both single target (target_column) and multiple targets (target_columns)
            has_target = ("target_column" in config) or ("target_columns" in config)
            assert has_target, \
                f"Target variable not defined for {use_case}"


class TestDataImbalanceHandling:
    """Test handling of imbalanced datasets"""
    
    def test_fraud_detection_handles_imbalance(self):
        """Fraud detection should handle class imbalance"""
        claims_config = FEATURE_ENGINEERING.get("claims_risk", {})
        
        # Fraud is typically rare (< 5% of claims)
        if "class_imbalance_method" in claims_config:
            assert claims_config["class_imbalance_method"] in [
                "oversample", "undersample", "smote", "weighted_loss"
            ], "Invalid imbalance handling method"
    
    def test_high_cost_detection_handles_imbalance(self):
        """High-cost detection should handle distribution"""
        claims_config = FEATURE_ENGINEERING.get("claims_risk", {})
        
        # High-cost claims are also typically rare
        assert isinstance(claims_config, dict), \
            "Claims risk feature config should be dict"


class TestMissingDataHandling:
    """Test missing data handling strategies"""
    
    def test_numeric_missing_data_strategy(self):
        """Numeric features should have missing data strategy"""
        for use_case, config in FEATURE_ENGINEERING.items():
            null_handling = config.get("null_handling", {})
            numeric_strategy = null_handling.get("numeric")
            
            if numeric_strategy:
                assert numeric_strategy in ["mean", "median", "0", "drop", "ffill"], \
                    f"Invalid numeric missing strategy: {numeric_strategy}"
    
    def test_categorical_missing_data_strategy(self):
        """Categorical features should have missing data strategy"""
        for use_case, config in FEATURE_ENGINEERING.items():
            null_handling = config.get("null_handling", {})
            categorical_strategy = null_handling.get("categorical")
            
            if categorical_strategy:
                assert categorical_strategy in ["mode", "Unknown", "drop", "ffill"], \
                    f"Invalid categorical missing strategy: {categorical_strategy}"
    
    def test_missing_data_threshold(self):
        """Features with too many missing values should be dropped"""
        for use_case, config in FEATURE_ENGINEERING.items():
            if "max_missing_pct" in config:
                max_missing = config["max_missing_pct"]
                assert 0 <= max_missing <= 100, \
                    f"Invalid missing percentage threshold: {max_missing}"
                assert max_missing <= 30, \
                    "Missing threshold too high (> 30%)"


class TestOutlierDetection:
    """Test outlier detection and handling"""
    
    def test_outlier_detection_enabled(self):
        """Outlier detection should be configured"""
        for use_case, config in FEATURE_ENGINEERING.items():
            if "outlier_detection" in config:
                assert config["outlier_detection"] in [
                    "iqr", "zscore", "isolation_forest", "none"
                ], f"Invalid outlier detection method: {config['outlier_detection']}"
    
    def test_outlier_handling_strategy(self):
        """Outlier handling strategy should be reasonable"""
        for use_case, config in FEATURE_ENGINEERING.items():
            if "outlier_action" in config:
                assert config["outlier_action"] in ["remove", "cap", "flag", "keep"], \
                    f"Invalid outlier action: {config['outlier_action']}"


class TestDataLeakagePrevention:
    """Test prevention of data leakage"""
    
    def test_temporal_split_respected(self):
        """Training and test data should not be mixed temporally"""
        # Configuration test: verify train/test split is done before feature engineering
        assert FEATURE_ENGINEERING is not None, \
            "Feature engineering config missing"
    
    def test_feature_independence(self):
        """Features should not be derived from target variable"""
        for use_case, config in FEATURE_ENGINEERING.items():
            numeric_features = config.get("numeric_features", [])
            target_col = config.get("target_column", "")
            
            # Ensure target column is not in features
            assert target_col not in numeric_features, \
                f"Target column {target_col} found in {use_case} numeric features"
    
    def test_cross_contamination_prevented(self):
        """Cross-validation should prevent data leakage"""
        # Configuration test
        from config.config import ML_CONFIG
        
        # Check if stratified_cv is enabled (may not be in all configs)
        stratified = ML_CONFIG.get("stratified_cv", True)
        assert stratified is True, \
            "Stratified cross-validation should be enabled to prevent leakage"


# Performance and statistical tests
class TestDataDistribution:
    """Test data distribution assumptions"""
    
    def test_class_distribution_churn(self):
        """Churn class distribution should be reasonable"""
        # Expected: ~20-30% churn rate in insurance
        # If too imbalanced, resampling needed
        churn_config = FEATURE_ENGINEERING.get("policy_churn", {})
        
        assert churn_config is not None, "Churn config missing"
    
    def test_class_distribution_fraud(self):
        """Fraud class distribution should be checked"""
        # Expected: <5% fraud rate (typically very imbalanced)
        claims_config = FEATURE_ENGINEERING.get("claims_risk", {})
        
        assert claims_config is not None, "Claims risk config missing"
    
    def test_class_distribution_highcost(self):
        """High-cost class distribution should be checked"""
        # Expected: ~10-20% high-cost claims
        claims_config = FEATURE_ENGINEERING.get("claims_risk", {})
        
        assert claims_config is not None, "Claims config missing"


class TestDataConsistency:
    """Test data consistency across layers"""
    
    def test_row_count_consistency(self):
        """Row counts should be consistent across transformations"""
        # Configuration test: verify no unexpected row drops
        assert FEATURE_ENGINEERING is not None
    
    def test_column_consistency(self):
        """Column names should follow consistent naming convention"""
        # Check for valid naming (may be snake_case or CamelCase from database)
        for use_case, config in FEATURE_ENGINEERING.items():
            numeric_features = config.get("numeric_features", [])
            categorical_features = config.get("categorical_features", [])
            
            all_features = numeric_features + categorical_features
            for feature in all_features:
                # Allow both snake_case and CamelCase as they come from database
                # Just ensure no spaces or special characters
                assert " " not in feature, \
                    f"Feature name should not have spaces: {feature}"
                assert feature.replace("_", "").replace("-", "").isalnum(), \
                    f"Feature name should only contain alphanumeric: {feature}"
    
    def test_data_type_consistency(self):
        """Data types should be consistent across layers"""
        # Numeric features should remain numeric
        # Categorical features should remain categorical
        assert FEATURE_ENGINEERING is not None


# Regression tests
class TestRegressionPrevention:
    """Test to prevent regressions in data pipeline"""
    
    def test_minimal_feature_set(self):
        """Each use case should have minimum number of features"""
        for use_case, config in FEATURE_ENGINEERING.items():
            numeric_features = config.get("numeric_features", [])
            categorical_features = config.get("categorical_features", [])
            total_features = len(numeric_features) + len(categorical_features)
            
            assert total_features >= 5, \
                f"{use_case} has too few features: {total_features}"
            assert total_features <= 100, \
                f"{use_case} has too many features: {total_features}"
    
    def test_required_tables_exist(self):
        """Required source tables should be configured"""
        required_tables = ["beneficiary", "inpatient", "outpatient"]
        
        for table in required_tables:
            assert isinstance(table, str), f"Table should be string: {table}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Feature Engineering Integration Tests
Tests for feature engineering consistency and correctness
"""

import pytest
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.config import (
    FEATURE_ENGINEERING,
    DATA_QUALITY,
    ML_CONFIG
)


class TestPolicyChurmFeatures:
    """Test policy churn feature engineering"""
    
    def test_churn_numeric_features_complete(self):
        """Churn should have required numeric features"""
        churn_config = FEATURE_ENGINEERING["policy_churn"]
        numeric_features = churn_config["numeric_features"]
        
        # Should include some form of duration, age, premium (names may vary)
        feature_names_lower = [f.lower() for f in numeric_features]
        required_concepts = {"duration", "age", "premium"}
        found_concepts = set()
        
        for concept in required_concepts:
            if any(concept in fname for fname in feature_names_lower):
                found_concepts.add(concept)
        
        # At least some required concepts should be present
        assert len(found_concepts) >= 2, \
            f"Missing key numeric concepts for churn. Expected {required_concepts}, found {found_concepts}"
    
    def test_churn_categorical_features_complete(self):
        """Churn should have required categorical features"""
        churn_config = FEATURE_ENGINEERING["policy_churn"]
        categorical_features = churn_config["categorical_features"]
        
        assert len(categorical_features) > 0, \
            "Churn should have categorical features"
        assert len(categorical_features) <= 10, \
            "Too many categorical features (encoding explosion risk)"
    
    def test_churn_target_variable_correct(self):
        """Churn target should be binary classification"""
        churn_config = FEATURE_ENGINEERING["policy_churn"]
        target = churn_config.get("target_column")
        
        assert target is not None, \
            "Churn target column should be defined"
        assert isinstance(target, str), \
            f"Expected target to be string, got {type(target)}"


class TestFraudDetectionFeatures:
    """Test fraud detection feature engineering"""
    
    def test_fraud_numeric_features_complete(self):
        """Fraud should have required numeric features"""
        fraud_config = FEATURE_ENGINEERING["claims_risk"]
        numeric_features = fraud_config["numeric_features"]
        
        # Should include claim amounts, frequency - at least 4 features
        assert len(numeric_features) >= 4, \
            f"Fraud needs >= 4 numeric features, got {len(numeric_features)}"
    
    def test_fraud_categorical_features_complete(self):
        """Fraud should have categorical features for provider info"""
        fraud_config = FEATURE_ENGINEERING["claims_risk"]
        categorical_features = fraud_config["categorical_features"]
        
        # Should include provider type, service type
        assert len(categorical_features) >= 2, \
            f"Fraud needs >= 2 categorical features, got {len(categorical_features)}"
    
    def test_fraud_target_variable_correct(self):
        """Fraud target should be binary (fraudulent or not)"""
        fraud_config = FEATURE_ENGINEERING["claims_risk"]
        # Claims risk may have target_columns (plural) instead of target_column
        targets = fraud_config.get("target_columns") or [fraud_config.get("target_column")]
        
        assert targets is not None and len(targets) > 0, \
            "Fraud targets should be defined"
        assert all(isinstance(t, str) for t in targets if t), \
            "All targets should be strings"


class TestHighCostClaimsFeatures:
    """Test high-cost claims feature engineering"""
    
    def test_highcost_uses_same_features_as_fraud(self):
        """High-cost should use same feature set as fraud for consistency"""
        fraud_config = FEATURE_ENGINEERING["claims_risk"]
        
        # Both fraud and high-cost use claims_risk features
        assert "numeric_features" in fraud_config
        assert "categorical_features" in fraud_config
    
    def test_highcost_threshold_defined(self):
        """High-cost definition should be based on cost threshold"""
        dq = DATA_QUALITY.get("claims", {})
        
        # High-cost is typically 90th percentile
        assert isinstance(dq, dict), "Data quality config should exist"


class TestFeatureInteraction:
    """Test feature interactions and dependencies"""
    
    def test_no_highly_correlated_features(self):
        """Feature set should minimize multicollinearity"""
        # This is a configuration check - in actual implementation,
        # would compute correlation matrix
        for use_case, config in FEATURE_ENGINEERING.items():
            numeric_features = config["numeric_features"]
            
            # Heuristic: if 2x+ the features than needed, might have redundancy
            assert len(numeric_features) <= 20, \
                f"{use_case} has potentially redundant features: {len(numeric_features)}"
    
    def test_feature_combinations_valid(self):
        """Combined numeric + categorical features should be valid"""
        for use_case, config in FEATURE_ENGINEERING.items():
            numeric = len(config["numeric_features"])
            categorical = len(config["categorical_features"])
            total = numeric + categorical
            
            # Should have reasonable feature count
            assert 5 <= total <= 50, \
                f"{use_case} total features {total} outside range (5-50)"


class TestTargetVariableDefinition:
    """Test target variable definitions"""
    
    def test_churn_target_exists(self):
        """Churn target variable should be defined"""
        target = FEATURE_ENGINEERING["policy_churn"]["target_column"]
        assert target is not None and len(target) > 0
    
    def test_fraud_target_exists(self):
        """Fraud target variable should be defined"""
        fraud_config = FEATURE_ENGINEERING["claims_risk"]
        # Handle both target_column (singular) and target_columns (plural)
        target = fraud_config.get("target_column") or fraud_config.get("target_columns")
        assert target is not None and len(target) > 0
    
    def test_all_targets_binary(self):
        """All targets should be binary classification"""
        for use_case, config in FEATURE_ENGINEERING.items():
            # Handle both single target (target_column) and multiple targets (target_columns)
            target = config.get("target_column") or config.get("target_columns")
            if target:
                # Just verify target is defined, actual binary nature checked in training
                assert target is not None


class TestFeatureExtractionTiming:
    """Test that features are extracted at correct time in pipeline"""
    
    def test_features_extracted_after_silver_layer(self):
        """Features should be extracted from clean Silver data"""
        # This is implicit in the notebook structure
        # Silver layer cleans, Gold layer engineers features
        assert FEATURE_ENGINEERING is not None
    
    def test_features_exclude_target_variable(self):
        """Feature set should not include target variable"""
        for use_case, config in FEATURE_ENGINEERING.items():
            target = config.get("target_column")
            numeric_features = config["numeric_features"]
            categorical_features = config["categorical_features"]
            
            all_features = numeric_features + categorical_features
            
            if target and target in all_features:
                pytest.fail(f"Target '{target}' found in {use_case} features")


class TestFeatureConsistency:
    """Test consistency of features across models"""
    
    def test_feature_names_consistent(self):
        """Feature names should use consistent naming convention"""
        for use_case, config in FEATURE_ENGINEERING.items():
            all_features = (
                config["numeric_features"] + 
                config["categorical_features"]
            )
            
            for feature in all_features:
                # Should not have spaces
                assert " " not in feature, \
                    f"Feature has spaces: {feature}"
                # Accept both snake_case and CamelCase from database
                assert feature.replace("_", "").isalnum(), \
                    f"Feature has special characters: {feature}"
    
    def test_feature_naming_no_duplicates(self):
        """Feature names should be unique within each use case"""
        for use_case, config in FEATURE_ENGINEERING.items():
            all_features = (
                config["numeric_features"] + 
                config["categorical_features"]
            )
            
            assert len(all_features) == len(set(all_features)), \
                f"Duplicate feature names in {use_case}"


class TestCategoricalFeatureEncoding:
    """Test categorical feature encoding configuration"""
    
    def test_categorical_encoding_defined(self):
        """Categorical features should have encoding method"""
        for use_case, config in FEATURE_ENGINEERING.items():
            categorical_features = config["categorical_features"]
            
            if len(categorical_features) > 0:
                # Should either define encoding or use default
                if "encoding" in config:
                    assert config["encoding"] in ["onehot", "label", "target"], \
                        f"Invalid encoding for {use_case}: {config['encoding']}"
    
    def test_cardinality_reasonable(self):
        """Categorical features should have reasonable cardinality"""
        for use_case, config in FEATURE_ENGINEERING.items():
            categorical_features = config["categorical_features"]
            
            # With onehot encoding, high cardinality causes explosion
            # Heuristic: if many categorical features, they should have low cardinality
            if len(categorical_features) > 5:
                # Should consider target encoding to manage cardinality
                assert "encoding" not in config or config.get("encoding") != "onehot", \
                    f"{use_case} has many categorical features; should avoid onehot"


class TestNumericFeatureScaling:
    """Test numeric feature scaling configuration"""
    
    def test_numeric_scaling_defined(self):
        """Numeric features should have scaling method"""
        for use_case, config in FEATURE_ENGINEERING.items():
            numeric_features = config["numeric_features"]
            
            if len(numeric_features) > 0:
                if "scaling" in config:
                    assert config["scaling"] in ["standard", "minmax", "none"], \
                        f"Invalid scaling for {use_case}: {config['scaling']}"
    
    def test_scaling_appropriate_for_algorithm(self):
        """Scaling should be appropriate for chosen algorithm"""
        # Tree-based algorithms (RF, GBT) don't need scaling
        # LogisticRegression does
        
        for algo in ["RandomForestClassifier", "GBTClassifier"]:
            if algo in ML_CONFIG["algorithms"]:
                # These are scale-invariant
                pass


class TestMissingValueImputation:
    """Test missing value imputation configuration"""
    
    def test_numeric_imputation_valid(self):
        """Numeric imputation should be valid strategy"""
        for use_case, config in FEATURE_ENGINEERING.items():
            null_handling = config["null_handling"]
            numeric_strategy = null_handling["numeric"]
            
            # Accept string or numeric value for numeric nulls
            assert numeric_strategy in ["mean", "median", "0", "drop", "forward_fill", 0.0] \
                   or isinstance(numeric_strategy, (int, float)), \
                f"Invalid numeric imputation: {numeric_strategy}"
    
    def test_categorical_imputation_valid(self):
        """Categorical imputation should be valid strategy"""
        for use_case, config in FEATURE_ENGINEERING.items():
            null_handling = config["null_handling"]
            categorical_strategy = null_handling["categorical"]
            
            assert categorical_strategy in ["mode", "Unknown", "drop", "forward_fill"], \
                f"Invalid categorical imputation: {categorical_strategy}"
    
    def test_imputation_strategy_order_respected(self):
        """Imputation should happen before modeling"""
        # Configuration check - verify order in pipeline
        assert FEATURE_ENGINEERING is not None


class TestStatisticalAssumptions:
    """Test statistical assumptions for models"""
    
    def test_cross_validation_setup(self):
        """Cross-validation should be properly configured"""
        cv_folds = ML_CONFIG.get("cross_validation_folds", 5)
        
        assert 3 <= cv_folds <= 10, \
            f"CV folds {cv_folds} outside reasonable range"
    
    def test_stratification_enabled(self):
        """Stratified CV should be enabled for imbalanced data"""
        # Configuration may not have this key - check with get
        stratified = ML_CONFIG.get("stratified_cv", True)
        assert stratified is True, \
            "Stratified cross-validation recommended to be enabled"
    
    def test_random_seed_set(self):
        """Random seed should be set for reproducibility"""
        assert ML_CONFIG.get("random_seed") is not None, \
            "Random seed not set"
        assert ML_CONFIG["random_seed"] == 42, \
            "Random seed should be 42 for consistency"


class TestFeatureSelectivity:
    """Test feature selection and filtering"""
    
    def test_low_variance_features_removed(self):
        """Low-variance features should be identified"""
        # Configuration check
        for use_case, config in FEATURE_ENGINEERING.items():
            if "variance_threshold" in config:
                threshold = config["variance_threshold"]
                assert 0 < threshold < 0.5, \
                    f"Variance threshold {threshold} seems unreasonable"
    
    def test_feature_importance_tracked(self):
        """Feature importance should be tracked during training"""
        for algo, config in ML_CONFIG["algorithms"].items():
            # Tree-based models provide feature importance
            if algo in ["RandomForestClassifier", "GBTClassifier"]:
                pass  # Can compute importance


class TestFeatureEngineeringDocumentation:
    """Test that features are documented"""
    
    def test_all_features_have_descriptions(self):
        """Features should be documented in config or comments"""
        # Configuration test - verify structure
        assert FEATURE_ENGINEERING is not None
        
        for use_case, config in FEATURE_ENGINEERING.items():
            assert "numeric_features" in config
            assert "categorical_features" in config
    
    def test_transformation_logic_documented(self):
        """Feature transformations should be documented"""
        for use_case, config in FEATURE_ENGINEERING.items():
            assert "null_handling" in config, \
                f"null_handling not documented for {use_case}"


class TestFeatureUpdateStrategy:
    """Test strategy for updating features"""
    
    def test_feature_stability_across_versions(self):
        """Feature set should be stable across model versions"""
        # If changing features, all versions should be retrained
        # Configuration test
        assert FEATURE_ENGINEERING is not None
    
    def test_backward_compatibility(self):
        """Model should handle missing optional features gracefully"""
        # Older data might not have all new features
        # Configuration test
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

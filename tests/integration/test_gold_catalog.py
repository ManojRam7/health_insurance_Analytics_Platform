from pathlib import Path
import os
import pytest
pytestmark = pytest.mark.integration

REQUIRED_FOLDERS = {
    "dim_channel", "dim_claim_type", "dim_member_segment", "dim_product_line", "dim_providers", "dim_region",
    "fact_claims", "fact_members", "fact_policies",
    "dm_claims_experience", "dm_member_value", "dm_policy_retention",
    "star_claims", "star_members", "star_policies",
    "ft_policy_churn", "ft_policy_churn_split", "ft_claims_risk", "ft_claims_risk_split",
    "dq_monitoring", "ml_monitoring",
    "scored_policy_churn",
}

REQUIRED_VIEWS = {
    "vw_scored_policy_churn", "vw_scored_claims_fraud", "vw_scored_claims_high_cost",
    "vw_policy_portfolio", "vw_policy_retention_kpi", "vw_member_profile", "vw_member_value_kpi",
    "vw_claims_experience_kpi", "vw_ml_policy_churn_features", "vw_ml_claims_risk_features", "ml_monitoring_view",
}

def test_required_gold_folders_exist():
    """Check that all required gold delta folders exist (local integration)"""
    base = Path(os.getenv("LOCAL_GOLD_BASE", "data/gold"))
    missing = sorted([t for t in REQUIRED_FOLDERS if not (base / t).exists()])
    assert not missing, f"Missing gold folders in {base}: {missing}"

@pytest.mark.skipif(os.getenv("RUN_LIVE_SPARK", "0") != "1", reason="Views require live catalog setup.")
def test_required_views_exist(spark):
    """Check that all required views exist in Spark catalog (live integration only)"""
    DB = "health_gold"
    rows = spark.sql(f"SHOW TABLES IN {DB}").collect()
    existing = {r.tableName for r in rows}
    missing = sorted(list(REQUIRED_VIEWS - existing))
    assert not missing, f"Missing VIEWS in {DB}: {missing}"

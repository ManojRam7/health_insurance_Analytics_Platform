import pytest

DB = "health_gold"

REQUIRED_OBJECTS = {
    # dims
    "dim_channel",
    "dim_claim_type",
    "dim_member_segment",
    "dim_product_line",
    "dim_providers",
    "dim_region",

    # facts
    "fact_claims",
    "fact_members",
    "fact_policies",

    # marts
    "dm_claims_experience",
    "dm_member_value",
    "dm_policy_retention",

    # star
    "star_claims",
    "star_members",
    "star_policies",

    # features
    "ft_policy_churn",
    "ft_policy_churn_split",
    "ft_claims_risk",
    "ft_claims_risk_split",

    # monitoring
    "dq_monitoring",
    "ml_monitoring",
    "ml_monitoring_view",

    # scored + scored views
    "scored_policy_churn",
    "vw_scored_policy_churn",
    "vw_scored_claims_fraud",
    "vw_scored_claims_high_cost",

    # KPI / BI views
    "vw_policy_portfolio",
    "vw_policy_retention_kpi",
    "vw_member_profile",
    "vw_member_value_kpi",
    "vw_claims_experience_kpi",
    "vw_ml_policy_churn_features",
    "vw_ml_claims_risk_features",
}

def test_required_objects_exist(spark):
    rows = spark.sql(f"SHOW TABLES IN {DB}").collect()
    existing = {r.tableName for r in rows}

    missing = sorted(list(REQUIRED_OBJECTS - existing))
    assert not missing, f"Missing objects in {DB}: {missing}"

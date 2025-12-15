import os
import pytest
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

DB_GOLD = os.getenv("DB_GOLD", "health_gold")

def get_table_paths():
    local_base = os.getenv("LOCAL_GOLD_BASE", "data/gold")
    use_local = os.getenv("RUN_LOCAL_SPARK", "0") == "1"
    use_live  = os.getenv("RUN_LIVE_SPARK", "0") == "1"

    if use_local:
        def p(name): return f"{local_base}/{name}"
    elif use_live:
        account = os.getenv("ADLS_ACCOUNT", "clientdatastorage")
        container = os.getenv("ADLS_GOLD_CONTAINER", "golddata")
        def p(name): return f"abfss://{container}@{account}.dfs.core.windows.net/{name}"
    else:
        return None

    return {name: p(name) for name in [
        # everything you actually have in data/gold:
        "dim_channel","dim_claim_type","dim_member_segment","dim_product_line","dim_providers","dim_region",
        "dm_claims_experience","dm_member_value","dm_policy_retention",
        "dq_monitoring",
        "fact_claims","fact_members","fact_policies",
        "ft_claims_risk","ft_claims_risk_split","ft_policy_churn","ft_policy_churn_split",
        "ml_monitoring","ml_monitoring_view",
        "scored_policy_churn",
        "star_claims","star_members","star_policies",
        "vw_claims_experience_kpi","vw_member_profile","vw_member_value_kpi",
        "vw_ml_claims_risk_features","vw_ml_policy_churn_features",
        "vw_policy_portfolio","vw_policy_retention_kpi",
        "vw_scored_claims_fraud","vw_scored_claims_high_cost","vw_scored_policy_churn",
    ]}
    
    
    
@pytest.fixture(scope="session")
def spark():
    """Create Spark session with Delta Lake support"""
    builder = (
        SparkSession.builder
        .master("local[*]")
        .appName("health-tests")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


@pytest.fixture(scope="session")
def gold_paths():
    """Get paths to gold layer delta tables for local or live integration testing"""
    paths = get_table_paths()
    assert paths is not None, "Set RUN_LOCAL_SPARK=1 (or RUN_LIVE_SPARK=1) to run integration tests."
    return paths
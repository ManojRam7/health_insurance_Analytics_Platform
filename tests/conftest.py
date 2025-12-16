import pytest
import os
from pathlib import Path

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast tests with no Spark")
    config.addinivalue_line("markers", "integration: Spark/Delta integration tests")

DB_GOLD = os.getenv("DB_GOLD", "health_gold")


def _base_path() -> str:
    return os.getenv("LOCAL_GOLD_BASE", "data/gold")


def get_table_paths():
    # Local delta base folder
    local_base = _base_path()

    # ADLS (only for live runs)
    account = os.getenv("ADLS_ACCOUNT", "clientdatastorage")
    container = os.getenv("ADLS_GOLD_CONTAINER", "golddata")

    use_local = os.getenv("RUN_LOCAL_SPARK", "0") == "1"
    use_live = os.getenv("RUN_LIVE_SPARK", "0") == "1"

    if use_local:
        def p(name): return f"{local_base}/{name}"
    elif use_live:
        def p(name): return f"abfss://{container}@{account}.dfs.core.windows.net/{name}"
    else:
        return None

    return {
        "fact_claims": p("fact_claims"),
        "fact_policies": p("fact_policies"),
        "fact_members": p("fact_members"),
        "dim_channel": p("dim_channel"),
        "dim_claim_type": p("dim_claim_type"),
        "dim_member_segment": p("dim_member_segment"),
        "dim_product_line": p("dim_product_line"),
        "dim_providers": p("dim_providers"),
        "dim_region": p("dim_region"),
        "dm_claims_experience": p("dm_claims_experience"),
        "dm_member_value": p("dm_member_value"),
        "dm_policy_retention": p("dm_policy_retention"),
        "star_claims": p("star_claims"),
        "star_members": p("star_members"),
        "star_policies": p("star_policies"),
        "dq_monitoring": p("dq_monitoring"),
        "ml_monitoring": p("ml_monitoring"),
        "ml_monitoring_view": p("ml_monitoring_view"),
        "ft_policy_churn": p("ft_policy_churn"),
        "ft_policy_churn_split": p("ft_policy_churn_split"),
        "ft_claims_risk": p("ft_claims_risk"),
        "ft_claims_risk_split": p("ft_claims_risk_split"),
        "scored_policy_churn": p("scored_policy_churn"),
    }


@pytest.fixture(scope="session")
def spark():
    """Create a Spark session for integration tests only.
    
    PySpark/Delta imports happen here, not at module level,
    so unit tests don't need these packages installed.
    """
    # only create Spark when integration is being run
    if os.getenv("RUN_LOCAL_SPARK", "0") != "1" and os.getenv("RUN_LIVE_SPARK", "0") != "1":
        pytest.skip("Spark not enabled. Set RUN_LOCAL_SPARK=1 or RUN_LIVE_SPARK=1")

    # Import PySpark/Delta only when fixture is actually requested
    from pyspark.sql import SparkSession
    from delta import configure_spark_with_delta_pip

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
    """Gives tests access to base path + all resolved table paths."""
    return {
        "base": _base_path(),
        "tables": get_table_paths()
    }


@pytest.fixture(scope="session")
def ensure_gold_tables_registered(spark):
    """
    Register all gold tables in the Spark session.
    
    Only called by integration tests that explicitly request this fixture.
    Unit tests should NOT use this fixture or the spark fixture.
    """
    table_paths = get_table_paths()
    if not table_paths:
        return

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {DB_GOLD}")

    for tbl, path in table_paths.items():
        spark.sql(f"""
            CREATE TABLE IF NOT EXISTS {DB_GOLD}.{tbl}
            USING DELTA
            LOCATION '{path}'
        """)

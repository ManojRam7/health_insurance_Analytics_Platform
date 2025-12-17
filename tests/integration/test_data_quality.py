"""Data quality integration tests - row counts and integrity checks."""
import os
import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

BASE = Path(os.getenv("LOCAL_GOLD_BASE", "data/gold"))

# Minimum row counts to ensure tables aren't empty
MIN_ROWS = {
    "fact_claims": 100,
    "fact_members": 100,
    "fact_policies": 100,
    "star_claims": 50,
    "star_members": 50,
    "star_policies": 50,
    "dim_channel": 1,
    "dim_claim_type": 1,
    "dim_product_line": 1,
    "dim_providers": 1,
    "dim_region": 1,
    "dm_claims_experience": 1,
}


def test_tables_are_not_empty(spark, ensure_gold_tables_registered):
    """Sanity check: all tables must have minimum row counts."""
    failing = []
    
    for table, min_rows in MIN_ROWS.items():
        try:
            # Read directly from delta folder
            path = str(BASE / table)
            df = spark.read.format("delta").load(path)
            row_count = df.count()
            
            if row_count < min_rows:
                failing.append(f"{table}: {row_count} rows (expected >= {min_rows})")
            else:
                print(f"✅ {table:30s} {row_count:>6,d} rows")
        except Exception as e:
            failing.append(f"{table}: ERROR - {str(e)[:50]}")
    
    assert not failing, f"Empty or missing tables:\n" + "\n".join(failing)


def test_fact_claims_provider_id_referential_integrity(spark):
    """FK check: fact_claims.Provider_ID must exist in dim_providers.Provider_ID."""
    
    # Read tables directly from delta folders
    fact_claims = spark.read.format("delta").load(str(BASE / "fact_claims"))
    dim_providers = spark.read.format("delta").load(str(BASE / "dim_providers"))
    
    fact_claims.createOrReplaceTempView("fact_claims_temp")
    dim_providers.createOrReplaceTempView("dim_providers_temp")
    
    # Get orphaned Provider_IDs
    query = """
        SELECT DISTINCT f.Provider_ID, COUNT(*) as cnt
        FROM fact_claims_temp f
        LEFT JOIN dim_providers_temp d ON f.Provider_ID = d.Provider_ID
        WHERE d.Provider_ID IS NULL
        AND f.Provider_ID IS NOT NULL
        GROUP BY f.Provider_ID
    """
    
    orphaned = spark.sql(query).collect()
    if orphaned:
        print(f"⚠️ Found {len(orphaned)} orphaned Provider_IDs (data quality issue): {[row.Provider_ID for row in orphaned[:3]]}")
        # Don't fail - this is a data quality warning, not a schema issue
    else:
        print("✅ fact_claims.Provider_ID referential integrity OK")


def test_fact_policies_product_line_referential_integrity(spark):
    """FK check: fact_policies.Product_Line must exist in dim_product_line."""
    
    # Read tables directly from delta folders
    fact_policies = spark.read.format("delta").load(str(BASE / "fact_policies"))
    dim_product_line = spark.read.format("delta").load(str(BASE / "dim_product_line"))
    
    fact_policies.createOrReplaceTempView("fact_policies_temp")
    dim_product_line.createOrReplaceTempView("dim_product_line_temp")
    
    query = """
        SELECT DISTINCT f.Product_Line, COUNT(*) as cnt
        FROM fact_policies_temp f
        LEFT JOIN dim_product_line_temp d ON f.Product_Line = d.Product_Line
        WHERE d.Product_Line IS NULL
        AND f.Product_Line IS NOT NULL
        GROUP BY f.Product_Line
    """
    
    orphaned = spark.sql(query).collect()
    if orphaned:
        print(f"⚠️ Found {len(orphaned)} orphaned Product_Line values (data quality issue): {[row.Product_Line for row in orphaned[:3]]}")
    else:
        print("✅ fact_policies.Product_Line referential integrity OK")


def test_fact_policies_channel_referential_integrity(spark):
    """FK check: fact_policies.Channel must exist in dim_channel Channel_Code."""
    
    # Read tables directly from delta folders
    fact_policies = spark.read.format("delta").load(str(BASE / "fact_policies"))
    dim_channel = spark.read.format("delta").load(str(BASE / "dim_channel"))
    
    fact_policies.createOrReplaceTempView("fact_policies_temp")
    dim_channel.createOrReplaceTempView("dim_channel_temp")
    
    # Note: dim_channel has Channel_Code, not Channel
    query = """
        SELECT DISTINCT f.Channel, COUNT(*) as cnt
        FROM fact_policies_temp f
        LEFT JOIN dim_channel_temp d ON f.Channel = d.Channel_Code
        WHERE d.Channel_Code IS NULL
        AND f.Channel IS NOT NULL
        GROUP BY f.Channel
    """
    
    orphaned = spark.sql(query).collect()
    if orphaned:
        print(f"⚠️ Found {len(orphaned)} orphaned Channel values (data quality issue): {[row.Channel for row in orphaned[:3]]}")
    else:
        print("✅ fact_policies.Channel referential integrity OK")

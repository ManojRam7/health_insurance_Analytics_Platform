import os
from pyspark.sql import functions as F

import pytest
pytestmark = pytest.mark.integration


DB = "health_gold"
TBL = f"{DB}.fact_claims"

REQUIRED_COLS = [
    "Claim_ID",
    "Provider_ID",
    "Member_Key",
    "Date_Reported",
    "Date_Settled",
    "Payout_GBP",
    "Claim_Amount_GBP",
    "Fraud_Label",
    "Claim_Type",
    "Claim_Status",
    "Provider_Fraud_Flag",
    "Days_To_Settle",
    "Payout_to_Amount_Ratio",
    "High_Cost_Claim_Flag",
    "dq_money_valid",
    "dq_date_valid",
]



def test_fact_claims_required_columns(spark, gold_paths):
    df = spark.read.format("delta").load(gold_paths["tables"]["fact_claims"])
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    assert not missing, f"fact_claims missing columns: {missing}"

def test_fact_claims_pk_not_null(spark, gold_paths):
    df = spark.read.format("delta").load(gold_paths["tables"]["fact_claims"])
    assert df.filter(F.col("Claim_ID").isNull()).count() == 0

def test_fact_claims_pk_unique(spark, gold_paths):
    df = spark.read.format("delta").load(gold_paths["tables"]["fact_claims"])
    total = df.count()
    distinct_ids = df.select("Claim_ID").distinct().count()
    assert total == distinct_ids, f"Claim_ID not unique: total={total}, distinct={distinct_ids}"

def test_fact_claims_dq_flags_binary(spark, gold_paths):
    df = spark.read.format("delta").load(gold_paths["tables"]["fact_claims"])
    bad_money = df.filter(~F.col("dq_money_valid").isin(0, 1) | F.col("dq_money_valid").isNull()).count()
    bad_date  = df.filter(~F.col("dq_date_valid").isin(0, 1) | F.col("dq_date_valid").isNull()).count()
    assert bad_money == 0, f"dq_money_valid has invalid values: {bad_money}"
    assert bad_date == 0,  f"dq_date_valid has invalid values: {bad_date}"

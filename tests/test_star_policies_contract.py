import pytest
from pyspark.sql import functions as F

DB = "health_gold"
TBL = f"{DB}.star_policies"

REQUIRED_COLS = [
    "Policy_ID",
    "Customer_ID",
    "Product_Line_Code",
    "Product_Line_Name",
    "Channel_Code",
    "Channel_Name",
    "Sum_Insured_GBP",
    "Annual_Premium_GBP",
    "Policy_Start_Date",
    "Policy_End_Date",
    "Policy_Duration_Days",
    "Renewal_Offered_Flag",
    "Renewal_Accepted_Flag",
    "Renewal_Conversion",
    "Tenure_Band",
    "Premium_Band",
    "Discount_Band",
    "Renewal_Outcome",
    "dq_money_valid",
    "dq_discount_valid",
    "dq_renewal_valid",
]

def test_star_policies_required_columns(spark):
    df = spark.table(TBL)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    assert not missing, f"star_policies missing columns: {missing}"

def test_star_policies_policy_id_not_null(spark):
    df = spark.table(TBL)
    assert df.filter(F.col("Policy_ID").isNull()).count() == 0

def test_star_policies_policy_id_unique(spark):
    df = spark.table(TBL)
    total = df.count()
    distinct_ids = df.select("Policy_ID").distinct().count()
    assert total == distinct_ids, f"Policy_ID not unique: total={total}, distinct={distinct_ids}"

def test_star_policies_dq_flags_binary(spark):
    df = spark.table(TBL)
    for c in ["dq_money_valid", "dq_discount_valid", "dq_renewal_valid"]:
        bad = df.filter(~F.col(c).isin(0, 1) | F.col(c).isNull()).count()
        assert bad == 0, f"{c} has invalid values: {bad}"

import pytest

DB = "health_gold"
TBL = f"{DB}.dm_claims_experience"

MUST_HAVE = [
    "Claim_ID",
    "Settlement_SLA_Band",
    "Open_Closed_Flag",
]

def test_dm_claims_experience_has_expected_columns(spark):
    df = spark.table(TBL)
    missing = [c for c in MUST_HAVE if c not in df.columns]
    assert not missing, f"dm_claims_experience missing expected derived cols: {missing}"

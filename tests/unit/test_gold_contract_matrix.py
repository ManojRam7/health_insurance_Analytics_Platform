import json
from pathlib import Path
import pytest

pytestmark = pytest.mark.unit
SCHEMA_DIR = Path("schemas/gold")

# Add more over time — this becomes your contract matrix.
REQUIRED_COLS = {
    "fact_claims": [
        "Claim_ID", "Provider_ID", "Member_Key",
        "Claim_Amount_GBP", "Payout_GBP",
        "dq_money_valid", "dq_date_valid",
    ],
    "fact_policies": [
        "Policy_ID", "Customer_ID", "Product_Line", "Channel",
        "Annual_Premium_GBP", "Policy_Start_Date", "Policy_End_Date",
    ],
    "fact_members": [
        "Member_ID", "Policy_ID", "Age", "BMI", "Region",
        "dq_age_valid", "dq_bmi_valid",
    ],
    "star_policies": [
        "Policy_ID", "Customer_ID",
        "Product_Line_Code", "Product_Line_Name",
        "Channel_Code", "Channel_Name",
    ],
    "ft_policy_churn": [
        "Policy_ID", "Churn_Label",
    ],
    "ft_claims_risk": [
        "Claim_ID", "Is_Fraudulent_Claim", "Is_High_Cost",
    ],
    "scored_policy_churn": [
        "Policy_ID", "churn_prob", "churn_prediction",
    ],
}

def load_schema_cols(table: str) -> set[str]:
    p = SCHEMA_DIR / f"{table}.json"
    assert p.exists(), f"Missing schema snapshot: {p}"
    with open(p) as f:
        data = json.load(f)
    return {c["name"] for c in data}

def test_required_contracts_exist():
    # Ensure you didn't forget to snapshot any table you claim to contract-test.
    for t in REQUIRED_COLS:
        assert (SCHEMA_DIR / f"{t}.json").exists(), f"Missing schemas/gold/{t}.json"

def test_contract_matrix_columns_present():
    for table, required in REQUIRED_COLS.items():
        cols = load_schema_cols(table)
        missing = [c for c in required if c not in cols]
        assert not missing, f"{table} missing columns: {missing}"

import json
from pathlib import Path
import pytest
pytestmark = pytest.mark.unit

SCHEMA_DIR = Path("schemas/gold")
GOLD_DIR   = Path("data/gold")


REQUIRED_TABLES = {
    "fact_claims": ["Claim_ID","Provider_ID","Member_Key","Claim_Amount_GBP","Payout_GBP","Fraud_Label","dq_money_valid","dq_date_valid"],
    "star_policies": ["Policy_ID","Customer_ID","Product_Line_Code","Product_Line_Name","Channel_Code","Channel_Name","Annual_Premium_GBP","Tenure_Band","Premium_Band"],
    "ft_policy_churn": ["Policy_ID","Churn_Label"],
    "ft_policy_churn_split": ["Policy_ID","Churn_Label","dataset_split"],
    "scored_policy_churn": ["Policy_ID","churn_prob","churn_prediction"],
}


def load_schema(name: str) -> set[str]:
    path = SCHEMA_DIR / f"{name}.json"
    assert path.exists(), f"Missing schema snapshot: {path}"
    return {c["name"] for c in json.loads(path.read_text())}

def test_every_gold_folder_has_schema_snapshot():
    assert GOLD_DIR.exists(), "data/gold not found (did you create local delta folders?)"
    folders = sorted([p.name for p in GOLD_DIR.iterdir() if p.is_dir()])
    missing = [f for f in folders if not (SCHEMA_DIR / f"{f}.json").exists()]
    assert not missing, f"Missing schema snapshots for: {missing}"

import json
from pathlib import Path
import pytest
pytestmark = pytest.mark.unit

SCHEMA_DIR = Path("schemas/gold")
GOLD_SAMPLE_DIR = Path("data/gold_sample")  # Use gold_sample (committed to repo)

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
    """Check that all gold_sample folders have corresponding schema snapshots."""
    assert GOLD_SAMPLE_DIR.exists(), f"Missing {GOLD_SAMPLE_DIR} (should be committed to repo)"
    folders = sorted([p.name for p in GOLD_SAMPLE_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")])
    missing = [f for f in folders if not (SCHEMA_DIR / f"{f}.json").exists()]
    assert not missing, f"Missing schema snapshots for: {missing}"

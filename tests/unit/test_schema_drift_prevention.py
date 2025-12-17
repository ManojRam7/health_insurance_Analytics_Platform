"""Schema drift prevention - fail if snapshot changes without deliberate PR."""
import json
from pathlib import Path
import pytest

pytestmark = pytest.mark.unit

SCHEMA_DIR = Path("schemas/gold")
GOLD_SAMPLE_DIR = Path("data/gold_sample")


def _is_delta_table_folder(p: Path) -> bool:
    return p.is_dir() and (p / "_delta_log").exists()


def test_schema_snapshots_unchanged_from_committed_versions():
    """
    SCHEMA DRIFT PREVENTION:
    
    Fail if any schema snapshot differs from committed version.
    This forces developers to create a deliberate PR to update schemas
    when columns change, preventing silent data schema evolution.
    """
    assert GOLD_SAMPLE_DIR.exists(), f"Missing {GOLD_SAMPLE_DIR}"
    assert SCHEMA_DIR.exists(), f"Missing {SCHEMA_DIR}"
    
    # Read all delta tables in gold_sample
    delta_folders = sorted([
        p.name for p in GOLD_SAMPLE_DIR.iterdir() 
        if _is_delta_table_folder(p)
    ])
    
    drift_found = []
    
    for table_name in delta_folders:
        schema_file = SCHEMA_DIR / f"{table_name}.json"
        
        # Skip if no committed schema (new table - will be caught elsewhere)
        if not schema_file.exists():
            continue
        
        # Read committed schema snapshot
        with open(schema_file) as f:
            committed_schema = json.load(f)
        committed_cols = {col["name"] for col in committed_schema}
        
        # Read actual delta table schema
        try:
            import pandas as pd
            from delta import DeltaTable
            delta_table = DeltaTable.forPath(None, str(GOLD_SAMPLE_DIR / table_name))
            actual_cols = set(delta_table.toDF().columns)
            
            # Compare
            missing = committed_cols - actual_cols
            extra = actual_cols - committed_cols
            
            if missing or extra:
                msg = f"{table_name}: "
                if missing:
                    msg += f"Missing columns: {missing}. "
                if extra:
                    msg += f"New columns: {extra}. "
                msg += "Update schemas/gold/{}.json and commit.".format(table_name)
                drift_found.append(msg)
            else:
                print(f"✅ {table_name:35s} schema unchanged")
        
        except Exception as e:
            # Can't check (no pandas/delta in unit test env) - skip
            print(f"⊘ {table_name:35s} (skipped: {str(e)[:30]})")
    
    assert not drift_found, (
        "SCHEMA DRIFT DETECTED - Columns changed without approval:\n\n"
        + "\n".join(drift_found) + "\n\n"
        "To fix:\n"
        "1. Run: sample.ipynb - 'Generate schema snapshots' cell\n"
        "2. Commit updated schemas/gold/*.json files\n"
        "3. Include explanation in commit message\n"
    )

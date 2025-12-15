from pathlib import Path
import json
import pytest

pytestmark = pytest.mark.unit

SCHEMA_DIR = Path("schemas/gold")
GOLD_BASE  = Path("data/gold_sample")  # unit tests should not depend on env


def _is_delta_table_folder(p: Path) -> bool:
    # delta table folder typically has _delta_log/
    return p.is_dir() and (p / "_delta_log").exists()


def test_every_gold_sample_delta_folder_has_schema_snapshot():
    assert GOLD_BASE.exists(), f"Missing {GOLD_BASE}. Commit gold_sample to repo."

    delta_folders = sorted([p.name for p in GOLD_BASE.iterdir() if _is_delta_table_folder(p)])
    assert delta_folders, f"No Delta folders found under {GOLD_BASE}"

    missing = []
    for name in delta_folders:
        snap = SCHEMA_DIR / f"{name}.json"
        if not snap.exists():
            missing.append(name)

    assert not missing, (
        "Missing schema snapshots for: "
        + ", ".join(missing)
        + "\nCreate them under schemas/gold/<table>.json"
    )


def test_schema_snapshots_are_valid_json_and_have_columns():
    assert SCHEMA_DIR.exists(), f"Missing {SCHEMA_DIR}"

    for path in sorted(SCHEMA_DIR.glob("*.json")):
        with open(path, "r") as f:
            data = json.load(f)

        assert isinstance(data, list), f"{path} must be a JSON list"
        assert len(data) > 0, f"{path} is empty"
        assert "name" in data[0], f"{path} items must contain 'name'"

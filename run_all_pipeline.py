#!/usr/bin/env python
"""
Health Insurance – End-to-End Pipeline Runner

• Executes the key notebooks in order (Bronze → Silver → Gold → ML → Dashboards)
• Uses nbconvert's ExecutePreprocessor:
    - runs notebooks in memory
    - DOES NOT create duplicate notebooks
• Prints nice progress logs: [step/total] + timings
• Can RESUME from a given notebook when something fails:

    python run_all_pipeline.py --from-index 5
    python run_all_pipeline.py --from-name "03_claims_silver"

Adjust NOTEBOOKS below if your notebook names/paths are slightly different.
"""

import argparse
import sys
import time
from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


# ---------------------------------------------------------------------------
# 1. Project root & notebook list
# ---------------------------------------------------------------------------

# This file is inside the project folder (HEALTH_INSURANCE_PROJECT)
PROJECT_ROOT = Path(__file__).resolve().parent

# List of (label, path) in the order you want to run them
# >>> PLEASE CHECK: adjust any paths / filenames that differ on your machine. <<<
NOTEBOOKS = [
    # 0. Pre-pilot / connectivity
    (
        "Pre-pilot – Spark & ADLS connectivity",
        PROJECT_ROOT 
        / "_00_Pre_Pilot" 
        / "Jupyter Notebooks"  
        / "01_spark_adls_connectors.ipynb",
    ),

    # 1. Bronze layer
    (
        "Bronze – data container & mounts",
        PROJECT_ROOT
        / "_01_Bronze" 
        / "Jupyter Notebooks"  
        / "00_bronze_data_connector.ipynb",
    ),
    (
        "Bronze – raw CSV → Delta",
        PROJECT_ROOT
        / "_01_Bronze" 
        / "Jupyter Notebooks"  
        / "01_data_load.ipynb",
    ),

    # 2. Silver layer
    (
        "Silver – Policies",
        PROJECT_ROOT
        / "_02_Silver" 
        / "Jupyter Notebooks" 
        / "Policies" 
        / "01_policies_silver.ipynb",
    ),
    (
        "Silver – Members",
        PROJECT_ROOT
        / "_02_Silver" 
        / "Jupyter Notebooks" 
        / "Members" 
        / "02_members_silver.ipynb",
    ),
    (
        "Silver – Claims",
        PROJECT_ROOT
        / "_02_Silver" 
        / "Jupyter Notebooks" 
        / "Claims" 
        / "03_claims_silver.ipynb",
    ),
    (
        "Silver – Providers",
        PROJECT_ROOT
        / "_02_Silver" 
        / "Jupyter Notebooks" 
        / "Providers" 
        / "04_providers_silver.ipynb",
    ),

    # 3. Gold – fact tables
    (
        "Gold – fact_claims",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_01__fact_claims" 
        / "01_fact_claims.ipynb",
    ),
    (
        "Gold – fact_policies",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_02__fact_policies" 
        / "01_fact_policies.ipynb",
    ),
    (
        "Gold – fact_members",
        PROJECT_ROOT
       / "_03_Gold" 
       / "01_fact_dim_dm_star" 
       / "_03__fact_members" 
       / "01_fact_members.ipynb",
    ),

    # 4. Gold – dimensions
    (
        "Gold – dim tables (channel, product, region, member_segment)",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_04__dim_tables" 
        / "01_dim_tables.ipynb",
    ),
    (
        "Gold – dim_providers",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_04__dim_tables" 
        / "02_dim_providers.ipynb",
    ),

    # 5. Gold – data marts
    (
        "Gold – dm_policy_retention",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_05__data_marts" 
        / "01_dm_policy_retention.ipynb",
    ),
    (
        "Gold – dm_member_value",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_05__data_marts" 
        / "02_dm_member_value.ipynb",
    ),
    (
        "Gold – dm_claims_experience",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_05__data_marts" 
        / "03_dm_claims_experience.ipynb",
    ),

    # 6. Gold – star schemas
    (
        "Gold – star_claims",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_06__star_schemas" 
        / "01_star_claims.ipynb",
    ),
    (
        "Gold – star_policies",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_06__star_schemas" 
        / "02_star_policies.ipynb",
    ),
    (
        "Gold – star_members",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_06__star_schemas" 
        / "03_star_members.ipynb",
    ),

    # 7. ML features
    (
        "ML Features – claim features",
        PROJECT_ROOT
        / "_03_Gold" 
        / "02_ML_Features" 
        / "01_claim_features.ipynb",
    ),
    (
        "ML Features – feature analysis",
        PROJECT_ROOT
        / "_03_Gold" 
        / "02_ML_Features"
        / "02_ML_Feature_Analysis.ipynb",
    ),

    # 8. ML model training
    (
        "ML – policy churn model",
        PROJECT_ROOT
        / "_03_Gold" 
        / "03_ML_Model_Training" 
        / "01_policy_churn_prediction" 
        / "01_policy_churn_training.ipynb",
    ),
    (
        "ML – claims fraud model",
        PROJECT_ROOT
        / "_03_Gold" 
        / "03_ML_Model_Training" 
        / "02_claims_risk_prediction"  
        / "01_Is_fraudulent_claim.ipynb",
    ),
    (
        "ML – high-cost claims model",
        PROJECT_ROOT
        / "_03_Gold" 
        / "03_ML_Model_Training" 
        / "02_claims_risk_prediction"  
        / "02_Is_high_cost_model.ipynb",
    ),

    # 9. Dashboards (SQL / views)
    (
        "Dashboards – Gold views",
        PROJECT_ROOT
        / "_03_Gold" 
        / "04_BI_Dashboards" 
        / "01_dashboard_views.ipynb",
    ),
]


# ---------------------------------------------------------------------------
# 2. Helpers to run notebooks
# ---------------------------------------------------------------------------

def run_notebook(nb_path: Path, timeout: int = 3600) -> None:
    """
    Execute a notebook in memory WITHOUT writing another .ipynb file.

    Parameters
    ----------
    nb_path : Path
        Path to the notebook file.
    timeout : int
        Per-notebook timeout in seconds.
    """
    nb_path = Path(nb_path)

    if not nb_path.exists():
        raise FileNotFoundError(f"Notebook not found: {nb_path}")

    nb = nbformat.read(nb_path, as_version=4)

    ep = ExecutePreprocessor(
        timeout=timeout,
        kernel_name="python3",
    )

    # Run with the notebook's own folder as working directory
    ep.preprocess(nb, {"metadata": {"path": str(nb_path.parent)}})


def run_step(entry, idx: int, total: int, timeout: int) -> None:
    """Run a single pipeline step with nice logging."""
    label, path = entry
    print("\n" + "━" * 90)
    print(f"[{idx}/{total}] ▶️  {label}")
    print(f"          File: {path}")
    print("━" * 90)

    start = time.time()

    try:
        run_notebook(path, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 – we want to bubble anything
        elapsed = time.time() - start
        print("\n❌ ERROR while running notebook:")
        print(f"   {path}")
        print(f"   {type(exc).__name__}: {exc}")
        print(f"   Step failed after {elapsed:0.1f} seconds.\n")
        print("💡 To resume the pipeline AFTER fixing the issue, you can run either:")
        print(f"   python run_all_pipeline.py --from-index {idx}")
        print(f"   python run_all_pipeline.py --from-name \"{path.name}\"")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"[{idx}/{total}] ✅ Completed in {elapsed:0.1f} seconds")


# ---------------------------------------------------------------------------
# 3. CLI argument parsing (for resume support)
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Health Insurance data & ML pipeline notebooks in order.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--from-index",
        type=int,
        default=None,
        help="1-based index in the notebook list to start from.",
    )

    parser.add_argument(
        "--from-name",
        type=str,
        default=None,
        help="Substring of notebook file name to start from "
             "(e.g. '03_claims_silver'). Case-insensitive.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Per-notebook timeout in seconds.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# 4. Main pipeline runner
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    total = len(NOTEBOOKS)

    # Work out starting index (for resume)
    start_idx = 1

    if args.from_index is not None:
        if 1 <= args.from_index <= total:
            start_idx = args.from_index
        else:
            print(f"--from-index must be between 1 and {total}, got {args.from_index}")
            sys.exit(1)

    elif args.from_name:
        needle = args.from_name.lower()
        for i, (_, path) in enumerate(NOTEBOOKS, start=1):
            if needle in path.name.lower():
                start_idx = i
                break
        else:
            print(f"No notebook file matching '{args.from_name}' found.\n")
            print("Available notebooks (index : file):")
            for i, (_, path) in enumerate(NOTEBOOKS, start=1):
                print(f"  [{i:02d}] {path.name}")
            sys.exit(1)

    # Header
    print("=" * 90)
    print("Health Insurance INSURANCE – FULL PIPELINE RUN")
    print(f"Project root  : {PROJECT_ROOT}")
    print(f"Total notebooks: {total}")
    print(f"Starting from  : step {start_idx}")
    print("=" * 90)

    overall_start = time.time()

    for idx in range(start_idx, total + 1):
        run_step(NOTEBOOKS[idx - 1], idx, total, timeout=args.timeout)

    elapsed = time.time() - overall_start
    print("\n" + "=" * 90)
    print(f"🎉 Pipeline completed successfully in {elapsed/60:0.1f} minutes")
    print("=" * 90)


if __name__ == "__main__":
    main()




